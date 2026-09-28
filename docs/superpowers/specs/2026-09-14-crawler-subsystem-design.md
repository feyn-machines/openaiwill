# 官方 X 采集爬虫子系统设计

日期：2026-09-14（Asia/Taipei）。状态：**已实现并本地烟囱验证**（见文末“实现状态”与 [运行手册](../../development/x-crawler.md)）。

> 2026-09-27：已重组为爬虫组件（`core/` 通用机制 + `x/` 数据源，统一入口 `pnpm crawl`），时间线与账号查询共用一个调度器；旧技能目录已删除，改为只做调度的 `crawler` 技能。下文的模块名（`engine`、`parser`、`run` 等）是重组前的，现行结构以运行手册为准。

把 X 官方账号采集从技能 `.agents/skills/social-qingguo-collector/` 里拉出来，重建为项目自有的并发爬虫子系统。技能是上一版的临时形态，项目将不再依赖它。本设计只覆盖采集与账号/并发；官网发布记录对账、事件抽取、入库与估计不在本设计内。

## 1. 背景与动机

当前项目入口 `scripts/collect-official-x.py` 把账号事务完全委托给技能：`sys.path` 插入 `.agents/skills/social-qingguo-collector/scripts` 后 `import fetch_x`、调用 `fetch_x.login_cookies()`。由此继承了技能的三条假设，都不适合项目的长期采集：

1. **账号选择与账号数据都长在技能里。** `login_cookies()` 直接读 `os.environ["X_ACCOUNTS"]`、只取第一个账号。账号是动态数据，不该嵌进可复用技能，也不该放 env。
2. **不并发。** 技能对多个 handle 串行公平翻页，单连接单出口 IP。有账号池却不用于并发，是浪费。
3. **遇错即停、不轮换。** 单账号一旦限流或出错，整次采集停止。缺乏失效转移。

设计目标：引擎与账号无关；账号是项目本地动态数据；用账号池做真实并发；单账号失效自动转移；长跑有可见进度；保留现有的运行不可覆盖、原始页留存、reconciliation、quarantine、凭据不外泄等约束。

## 2. 代理并发模型（已实测）

2026-09-14 对青果 `overseas.tunnel.qg.net:11404`（https 隧道）做了一次性探测，复用采集器现有的 TLS 处理（`ssl.create_default_context()`，对 `*.tunnel.qg.net` 关闭 `check_hostname`），请求 IP 回显服务：

| 场景 | 结果 | 结论 |
| --- | --- | --- |
| 串行、每次新连接 | 5 次 5 个不同出口 IP | 新连接 = 新出口 IP |
| 同一连接复用 4 次 | 全部同一 IP | 出口 IP 绑定在连接上，连接内不变 |
| 并发 3 条连接（两轮） | 每轮 3 个互异 IP，全 HTTP 200，无限流 | 并发连接得到独立 IP，并发有效 |

由此确定核心机制：**一个账号 = 一条独占持久连接 = 一个稳定出口 IP**，覆盖该账号的整个抓取会话（未来的登录取 cookie 与全部翻页都在同一 IP）。换账号即丢弃旧连接、开新连接，得到新 IP。青果套餐的并发上限未知（3 路已验证干净），故并发度可配、从保守值起步、遇代理错误退避。

探测脚本为一次性产物，不纳入代码库。

## 3. 范围

**本设计内**：X 官方账号时间线采集；账号池与健康管理；并发调度与失效转移；进度可见；不可覆盖的运行输出与 reconciliation。

**本设计外**：官网发布记录对账（另行设计的覆盖校验）；事件抽取与归并；数据库导入；能力估计；技能里的 Reddit 采集与关键词搜索深挖（事件驱动的定向深挖属于后续，依赖事件抽出后才有目标）。

## 4. 目录与组件

新建项目自有包 `scripts/crawler/`，与既有 `scripts/data_pipeline/`、`scripts/lib/` 同级：

```
scripts/crawler/
  x_client.py    # httpx 客户端 + 青果 TLS + X GraphQL 调用（从技能 fetch_x 抽出洗净）
  parser.py      # 时间线/搜索页解析（从 official_x_collection.extract_* 抽出）
  proxy.py       # 青果代理会话：每连接独立出口 IP，TLS 主机名例外
  accounts.py    # 账号池：读 JSON、出借/归还租约、健康态与冷却、落盘
  engine.py      # 账号无关抓取：给 (会话, 目标) → 翻页 → 原始页 + 解析记录
  scheduler.py   # 并发 worker 池：任务队列 + N worker + 退避 + 预算
  progress.py    # 进度渲染：只读状态 → 人类可读进度（TTY / 非 TTY）
  run.py         # 编排：plan → 并发跑 → 不可覆盖输出 + reconciliation + 覆盖报告
  cli.py         # argparse 入口
```

每块单一职责、接口清晰、可独立测试。

### 4.1 抓取引擎 `engine.py`（账号无关）

- 输入：`session`（一个已开的独占连接客户端 + 该账号的 cookie 对）与 `target`（`handle`、`author_id`、`window_start`、`window_end`、`mode`）。
- 行为：串行翻页抓完这一个 handle 的时间线，使用 X 原生 cursor；每页保存原始 JSON 与 SHA-256；解析为规范化记录（沿用现有字段：原帖 ID、作者与用户 ID、发布时间、正文与来源、回复/转帖/引用标记、互动快照、观测时间；缺失互动值 `null`，实际零 `0`）。
- 单账号内部沿用现 `official_x_collection.collect()` 的**单 job** 逻辑：`[start, end)` 半开窗；作者身份（handle 与 author_id 同时匹配）不符入 quarantine；user_timeline 模式下整页早于起点则 `search_ended`；空页仍带 cursor 记 `incomplete`；cursor 重复记 `cursor_cycle`；无 cursor 结束。
- 引擎不读 env、不挑账号、不管并发、不写最终输出。它只把一个目标抓成结果对象返回给调度器。

### 4.2 账号池 `accounts.py`（动态数据）

- **位置**：账号池从技能目录搬到项目本地忽略区 `data/secrets/x-accounts/pool.json`（root `data/` 已被 `.gitignore` 覆盖）。技能目录内当前的 `x-account-pool.json` 迁移后删除。
- **Schema**（`x-account-pool/v1`，每账号）：`username`、`password`、`totp_secret`、`email`、`email_password`、`auth_token`、`ct0`、`source`、`status`、`cooldown_until`、`last_used_at`、`label`（非敏感短标识，用于日志与进度）。
- **健康态**：`unverified`（未验证）→ `usable`（liveness 通过）→ `cooldown(until)`（命中限流，到期前不出借）→ `dead`（认证失败/被封）。`active` 保留给当前 env 内账号。
- **出借/归还**：出借一个 `usable`/到期可用账号的租约（cookie 对 + label）；归还时写回 `last_used_at`；调度器报告限流则置 `cooldown_until`，报告认证失败则置 `dead`。池状态变更即时落盘（0600），使中断后可见各账号最新态。
- **ct0 处理**：那 30 个采购账号有 `auth_token` 无 `ct0`。按已定策略，账号层只管现成 cookie 对，ct0 的获取当外部输入：引擎在 cookie 缺 `ct0` 时合成一个 32-hex，令 cookie 的 `ct0` 与请求头 `x-csrf-token` 同值（X 多数只读 GraphQL 接口接受此约定）。**全量运行前必须先做一次 liveness 探针**（第 9 节），验证 auth_token + 合成 ct0 能真实读到时间线，再据结果把账号从 `unverified` 标为 `usable` 或 `dead`。
- 凭据（password、totp_secret、auth_token、ct0、email_password）**永不**写进任何运行输出、日志或进度；对外只用 `label`。

### 4.3 代理层 `proxy.py`

- 从 env 读代理端点（`X_PROXY` / `QINGGUO_PROXY_URL` / `SOCIAL_PROXY_URL`），沿用现有校验：`overseas.tunnel.qg.net` 必须 https；对 `*.tunnel.qg.net` 关闭代理 TLS 主机名校验，目标站点证书校验保持开启；非美前置路由不变；`trust_env=False`。代理端点是单个基础设施凭据、不是账号，留在 env。
- 为每个账号会话构造**独占连接**客户端：连接池上限设为 1（`max_connections=1`），确保该账号翻页期间不会另开连接换掉出口 IP。换账号即关旧客户端、开新客户端。

### 4.4 调度器 `scheduler.py`（并发 + 失效转移）

- **任务队列**：`plan` 阶段按启用且身份确认的账号 × 固定窗口生成 job（一个 handle 一个 job，独立 cursor，互不共享额度）。
- **worker 池**：默认并发 5，`--concurrency` 可配。每个 worker 循环：从池租一个账号 → 经代理层开独占连接 → 从队列取一个 job → 调引擎抓完 → 写结果、归还账号 → 取下一个 job。账号内按 `pace`（≥3s）串行，账号之间并发。
- **失效转移**（取代"遇错即停"）：job 抓取遇 429/403/限流或连接错误时，标记该账号 `cooldown`（或 `dead`），关连接，**该 job 重新入队**由其他 worker 换账号重试；记录一次 failover 事件。job 设最大重试次数（换账号上限），超过仍失败则该 job 标 `incomplete` 并记原因，不阻塞其余 job。
- **退避**：连续代理错误触发全局降并发与 sleep 退避；恢复后可回升。
- **预算**：`max_pages_per_job`、全局 `max_requests`、总 `timeout`、每账号 `pace`。到预算/超时后未完成 job 标 `incomplete`。

### 4.5 进度组件 `progress.py`

只读调度器状态渲染进度，不改状态，可喂 state 断言输出。

- **TTY**：多行原地刷新块——总体行 `已完成 job/总数 · 已采帖数 · 请求数 · 已用时 · ETA`；并发行 `活跃 worker · 使用中账号 · 冷却中 · 失效`；每个活跃 worker 一行 `@handle 第 N 页 (label)`。
- **非 TTY**（重定向日志）：节流追加行（每数秒一条带 UTC 时间戳），外加里程碑行——worker 开始某 handle、账号进冷却、job 完成或换账号重试。
- **ETA**：按已完成 job 速率估剩余时间；账号全在冷却等待时按 timer tick 刷新并显示"等待冷却 Xs"，不假死。
- **收尾总结**：总帖数、job 完成/incomplete 数、账号 使用/冷却/失效 数、用时、reconciliation 状态。

### 4.6 编排与输出 `run.py`

- 输出为 root `data/` 下一个尚不存在的新 JSON 文件；`.lock` 保留，运行不可覆盖；原始页存同名 `.pages/` 目录（0700），逐页 SHA-256。
- 保留 `reconciliation`（`--expect-post` 已知公告全命中才通过）、`quarantine`（身份/窗口不符）、`coverage_status`（provider 可见时间线的有界覆盖，官网对账另算）、`publication_window`、实现与注册表哈希。
- **新增**：`account_usage` 日志——每个 job 由哪个账号 label 抓取、页数、failover 记录（不含凭据）。
- **运行成败判据改进**：单账号出错不再判全局失败。`ok` 仅要求：无缺失的 expected 帖、无 provider 级 quarantine（身份不符/超查询窗）、所有 job 达到 `search_ended`。存在被 failover 消化的账号错误但 job 仍完成，不影响 `ok`。任一 job 换遍账号仍 `incomplete`，或 reconciliation 缺失，则 `needs_attention`。

## 5. 数据流

```
pool.json ──load──▶ accounts ──lease(cookie,label)──▶ scheduler
                                                        │  N workers 并发
env X_PROXY ──▶ proxy ──open(独占连接=稳定IP)──▶ session ┘
scheduler ──(session,target)──▶ engine ──翻页──▶ 原始页(.pages)+解析记录
engine ──结果──▶ scheduler ──▶ run.py ──▶ 不可覆盖运行 JSON + account_usage + reconciliation
scheduler.state ──(只读)──▶ progress ──▶ 终端进度 / 日志
错误 ──▶ accounts.cooldown/dead + job 重排(failover)
```

## 6. 启动

新增 pnpm 脚本 `crawl:x`（指向 `scripts/crawler/cli.py`）：

```sh
# 三周基准
pnpm crawl:x -- \
  --start 2026-08-24T00:00:00Z --end 2026-09-14T00:00:00Z \
  --concurrency 5 \
  --output data/collection/official-x/three-week-baseline.json

# 只看计划、不访问 X
pnpm crawl:x -- --start ... --end ... --plan-only --output data/collection/official-x/plan.json

# 定向单账号 + 已知公告验收
pnpm crawl:x -- --start ... --end ... --handles OpenAI \
  --expect-post <id> --output data/collection/official-x/openai.json
```

账号自动从 `data/secrets/x-accounts/pool.json` 按健康态挑选；代理从 env 读。输出必须是 `data/` 下的新 JSON。默认 `--pace 3`、`--max-pages`、`--max-requests`、`--timeout` 可配。

## 7. 安全约束

- 凭据（账号密码/2FA/auth_token/ct0/邮箱密码、代理凭据）永不进 Git、运行输出、日志或进度；对外只用非敏感 label。池文件 0600、运行目录 0700。
- 账号池、原始归档、运行结果均在 root `data/`（忽略）；输出路径校验必须落在 `data/` 内且为新文件。
- 遵守 SECURITY.md 与青果技能的代理/TLS/非美前置规则；不因传输错误直接断言账号欠费或 Cookie 失效。

## 8. 与技能退役

- 采集所需的可复用部分（青果 TLS 处理、X GraphQL 调用、时间线/搜索解析）复制并清理进 `scripts/crawler/`；项目不再 `sys.path` 插入技能、不再 `import fetch_x`。
- 技能目录保留为历史，不再是运行依赖。旧入口 `scripts/collect-official-x.py` 与 `scripts/official_x_collection.py` 由新子系统取代（保留旧运行档案与文档记录，不回改已冻结批次）。
- 技能内账号池文件迁移到 `data/secrets/x-accounts/pool.json` 后从技能目录删除。

## 9. 实现顺序与验证

1. **ct0 liveness 探针**（先做）：拿池中一个 token-only 账号，经独占连接 + 合成 ct0 读一次官方时间线，确认 auth_token + 合成 ct0 可用。不通过则调整会话获取策略再继续。
2. 抽引擎与解析器、单账号跑通（等价于现有单 job 行为的回归）。
3. 账号池 + 代理独占连接 + 单 worker 串行跑通全部 handle。
4. 并发 worker 池 + 失效转移 + 退避。
5. 进度组件（TTY 与非 TTY）。
6. 编排、不可覆盖输出、reconciliation、account_usage。
7. 全量三周基准运行，用真实分页数校准并发与预算。

**测试**（沿用 `test_collector.py` mock 风格，不触网）：单 job cursor 完整性与窗口/身份 quarantine；并发公平（无 job 饿死）；单账号连接内 IP 稳定（连接不被换）；限流触发 job 重排换账号并使账号进冷却；冷却到期前不出借、`dead` 不出借；预算/超时后 job 标 incomplete；reconciliation 命中/缺失；输出不可覆盖；凭据不入输出/日志/进度；进度渲染对给定 state 的断言；改进后的 `ok` 判据。

## 10. 待办与后续

- 官网发布记录对账（覆盖校验）另行设计，用于验收"X 漏采"。
- 事件抽取、定向 Reddit/X 深挖、入库与估计为后续阶段。
- 青果并发上限、代理流量与长期成本在全量试跑后按实际分页数评估。

## 11. 实现状态（2026-09-14）

已实现于 `scripts/crawler/`（`parser`、`proxy`、`accounts`、`engine`、`scheduler`、`progress`、`run`、`cli`，twikit 仅由 `x_client`/`x_compat` 引入）。项目自有 venv `data/runtime/crawler-venv`（`requirements-crawler.txt`：twikit 2.3.3、httpx 0.28.1）。入口 `pnpm crawl:x`；离线单测 `pnpm crawl:test:unit`（27 项，已并入 `pnpm check`）。账号池迁至 `data/secrets/x-accounts/pool.json`（0600、忽略），技能目录旧池已删除，项目不再 `import` 技能代码。

**去风险与验证**：

- ct0 liveness 探针通过——token-only 账号 + 合成 ct0 成功读到真实时间线（HTTP 200、无 errors）。
- 代理模型实测——新连接换 IP、连接内 IP 稳定、并发连接得独立 IP（见第 2 节）。
- 实机烟囱（`@OpenAI`+`@AnthropicAI`，三天窗，并发 2）：两账号并行、各自合成 ct0，两个 job 均 `search_ended`，22 帖，reconciliation 命中三条 OpenAI 金融服务公告 ID（旧采集遗漏的那批），输出无凭据，原始页留存。
- `httpx.ConnectError` 分类修复：网络异常经 `x_client` 翻译为 `TransportError`，由调度器换新连接（新 IP）重试，不误判账号失效——单测覆盖。

**仍未做**（不在本子系统）：全部 51 账号真实三周基准运行、官网发布记录对账、定时调度、事件抽取、数据库新批次与估计。运行手册见 [x-crawler](../../development/x-crawler.md)。
