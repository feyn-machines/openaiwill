# X 采集实现对比：openaiwill crawler 与 x-account-client

日期：2026-09-23（Asia/Taipei）。状态：**对比研究 / 设计输入**，不是已确认的实施计划。

> 2026-09-27 更新：用户确认**限流后换号**为项目规则，§4.3 与 §6 第 1 条的结论成立；原技能里"限流就停"的相反规则已随技能代码一并删除。P3 的按响应头冷却、P2 的最小版（`SchemaChanged` 停批）已在爬虫组件重组中实现，见 [运行手册](../../development/x-crawler.md)。P1 登录补号仍未采纳。

对比项目自有爬虫 `scripts/crawler/`（运行手册见 [x-crawler](../../development/x-crawler.md)，设计见 [爬虫子系统设计](2026-09-14-crawler-subsystem-design.md)）与外部独立仓库 `x-account-client`。目的是判断是否需要吸收其做法，以及哪些部分明确不采纳。本对比只做设计与证据层面对照，不执行真实登录、真实采集或网络探测。

## 1. 结论摘要

**不替换当前项目的采集内核。** 两者定位不同，不是同一层实现：

- 当前项目是**面向长期无人值守**的官方账号时间线采集：burner 账号池、并发 worker、按失败类型做失效转移、不可覆盖运行归档、已知公告 reconciliation、并已衔接入库。
- `x-account-client` 是**自有账号登录 + 只读 X Web 接口研究型客户端**：能自己登录生成会话，前端改版检测与错误分类细，但失败即停、不换号、不重试。

采纳建议分三档：

| 优先级 | 候选补件 | 解决的问题 |
| --- | --- | --- |
| P1 | 会话生成/补号能力（登录链路） | 当前池只消费 `auth_token`，账号耗尽后无法自愈 |
| P2 | 前端构建漂移检测（源码哈希 + 结构断言） | 当前 X 改版只得到笼统 `parse_error`，诊断力弱 |
| P3 | 严格 Cookie 校验、按服务器 header 计算冷却 | 提前拦截导入错误；冷却更准 |

明确不采纳：跨会话失效转移的移除、失败停批、无原始页留存、无已知公告对账、把空 `SIGN_BUILDS` 的 x-web 适配当作现成能力。

## 2. 对比对象与基线

| 项 | openaiwill | x-account-client |
| --- | --- | --- |
| 本地路径 | `scripts/crawler/` | `client/`、`login/`、`config/` |
| 基线 | 工作区 `f8f2333` 之上的未提交工作树 | `main` / `b75184d8ecde2ddbb9b649d7ca43355c360a96d1`（按其仓库研究报告） |
| 自述定位 | 项目自有并发 X 官方账号采集器，取代已退役技能 | X 账号登录、会话池管理和关注目标查询／采集 |
| 证据来源 | 源码、既有单测、2026-09-14 三周真实基准 | 源码、离线测试、其 `docs/validation.md`（自述无真实登录/采集） |

## 3. 能力对照

| 维度 | openaiwill `scripts/crawler/` | x-account-client `client/` |
| --- | --- | --- |
| HTTP/GraphQL 实现 | twikit 2.3.3 + httpx，本地 `x_compat.py` 补丁 | 手写 `XHTTP`，无 twikit；`operations.json` 白名单 6 个只读接口 |
| 接口发现 | 依赖 twikit 内部实现与补丁 | 运行时从 `main.js` 提取 queryId / 公开 Bearer / transaction，并与白名单比对 |
| 新前端（x-web） | 无 | 已写 `x_web_adapter.py`，但 `SIGN_BUILDS` 为空，请求前即 `TRANSACTION_UNVERIFIED` 停机 |
| 身份模型 | 池内 `auth_token`/`ct0`；无登录 | 自有账号密码 + TOTP，Jetfuel 登录生成会话 |
| 账号健康态 | usable/cooldown/dead/unverified，LRU 租借，即时落盘 | ready/cooldown/disabled/paused + cookie 池 |
| 并发 | N worker + 每账号独占连接（稳定出口 IP） | 线程池，一线程一会话，全局 `RequestGate` |
| 失败处理 | 跨账号失效转移（限流换号、认证标 dead、传输换新连接） | 不换号、不放回队列；受控错误停整批 |
| 挑战检测 | 认证类错误归 `AuthFailed`，无挑战识别 | Cloudflare/Arkose/登录表单细粒度检测 |
| 代理/TLS | 青果 https 隧道，仅代理握手放宽主机名 | 同款策略；`curl` 传输用 chrome 指纹 + HTTP/2 |
| 冷却 | 固定 900s | 尊重 `Retry-After` 与 `x-rate-limit-reset` |
| 原始页留存 | 逐页原始 JSON + SHA-256，存 `.pages/<jobid>/` | 默认只存规范化结果，`raw=True` 才带原始结构 |
| 覆盖判据 | `[start,end)` + 原生 cursor + `--expect-post` 对账 | `complete`/`stop_reason` + 不可用条目/游标记录，无对账 |
| 输出 | `data/` 下不可覆盖运行 JSON，可 `data:ingest:x` 入库 | `client/output/batch-v2-*.json` + `pool-state.v2.json` |
| 验证 | 离线单测 + 51 账号三周真实基准 | 101 + 55 离线测试，自述无真实登录/采集证据 |

## 4. 逐项分析

### 4.1 依赖与接口发现

当前项目依赖 twikit，并通过 `x_compat.py` 打两处补丁（transaction 索引、search timeline）。优点是开发快、覆用了成熟的 GraphQL 调用；代价是**对 twikit 内部结构敏感**，失败时只能得到一个分类（`engine.TransportError` / `parse_error`），无法区分"接口改版"还是"数据异常"。

`x-account-client` 在运行时核验前端构建（queryId、Bearer、transaction 模块的源码哈希与结构），不认识就明确停机并给出 `BUILD_CHANGED` / `FEATURES_CHANGED` / `TRANSACTION_UNVERIFIED` 等分类。这是当前项目缺失的诊断层次。

### 4.2 身份模型（最本质差异）

当前项目的 `data/secrets/x-accounts/pool.json` 里虽有 `password`/`totp_secret`/`email`，但爬虫只消费 `auth_token`（`accounts.py` 的 `Lease`）。也就是说**账号池是消耗品，没有补号能力**：一旦账号被限流到 `dead` 或封号，池只会变小。

`x-account-client` 的 `login/scripts/x_login_http.py` + `login/http-runtime/sdk.mjs` 实现了完整登录链路：Python 走 HTTP/Jetfuel 流程，Node SDK 只接收公开页面元数据并计算 Castle token、Prelude signals 与 transaction ID；服务端要求 TOTP 时本地用账号文件里的 Base32 密钥生成；成功后先写 `session-pending.json`，`/home` 交叉验证通过才写 `session.json`。这是当前项目**唯一结构性缺口**。

### 4.3 并发与失效转移

当前项目的 `scheduler.py` 是核心资产：任务队列 + N worker，限流 → 账号冷却并换号、认证失败 → 标 dead 并换号、传输错误 → 同账号换新连接（新出口 IP）重试；单账号错误被转移消化后不影响整次 `ok`。

`x-account-client` 明确选择"任务固定绑定会话、失败不放回队列、任何受控错误停整批"（其 v2 设计约束 3；`docs/proxy-and-batch.md`）。这只适合小批、短时、自检式采集，对当前项目的长期采集是**倒退**，不采纳。

代理模型两者一致且都经过实测：青果隧道新连接换出口 IP、连接内 IP 稳定；`x-account-client` 额外验证了并发 3 连接各得独立 IP。

### 4.4 失败分类与挑战检测

`x-account-client` 的 `inspect_bootstrap_response` 区分：Cloudflare challenge（响应头 `cf-mitigated`、challenge DOM、challenge 脚本）、登录/账号验证表单、新版 `entry-client` 入口、缺失 `main.js`；并区分被动 JSD 注入与真实挑战（只有响应头或实际 DOM/脚本类型才判挑战）。还区分 401/403/429/重定向/未知构建并分别停机。

当前项目把 HTTP 401/403、GraphQL 错误码、429 在 `engine.classify_page` 归类为 RateLimited / AuthFailed / TransportError 三档，粒度更粗，但配合失效转移已足够。挑战检测是 P2 可借鉴点，用于提升诊断而非改变控制流。

### 4.5 代理与 TLS

两者策略相同：只对 `*.tunnel.qg.net` 的代理握手放宽主机名校验，目标站（x.com）保持完整验证，不使用全局 `verify=False`。`x-account-client` 的 `http_transport.py` 另用 `curl_cffi` chrome 指纹 + HTTP/2，并区分 HTTP 与 curl 传输在 https 青果隧道下的代理证书校验能力。当前项目用 httpx + 每账号 `max_connections=1` 达到同样的"稳定出口 IP"目标。此维度无缺口。

### 4.6 输出、溯源与覆盖判据

当前项目：输出必须是 `data/` 下尚不存在的 JSON；逐页原始响应 + SHA-256 存 `data/collection/official-x/<run>.pages/<jobid>/`；`--expect-post` 做已知公告 reconciliation；`coverage_status=provider_timelines` 明确"只表示翻过窗口起点，不代表重大发布收齐"；并已通过 `data:ingest:x` 幂等入库。

`x-account-client`：默认只存规范化结果，原始结构可选；没有已知公告对账；没有入库。**当前项目在此维度全面领先，不采纳其做法。**

### 4.7 登录能力

见 4.2。补充细节：

- 批量登录为每个账号建立独立的 Python 会话、Node SDK 进程和输出子目录，全部成功后才生成批次 cookie 池。
- Cookie 文件解析（`load_cookie_records`）严格校验域限 `x.com`、路径 `i/api/` 或 `/`、过期、同名冲突、把请求头对象误当 Cookie 导出等，并归一化到 `.x.com`。
- 会话状态文件 `pool-state.v2.json` 在启动时拦截冷却/暂停会话，而非当作全新可用池。

这三条都是当前项目可以直接吸收的工程细节。

### 4.8 验证状态

当前项目有真实基准：2026-09-14 全 51 账号、窗口 `[2026-08-24, 2026-09-14)`、并发 5，51/51 complete、1625 帖、6 次传输重试自愈，并已入库。

`x-account-client` 自述三次提交同日、无跨版本/跨时间运行证据，新前端适配整体被空白名单阻断。**不能把其代码视为已证明线上可用。**

## 5. 建议采纳

### P1：会话生成 / 补号

把 `x-account-client` 的登录链路作为参考，为当前账号池补上"从 `password` + `totp_secret` 生成 `auth_token`/`ct0`"的能力。落地时的边界：

- 只在本地运行，产物仍是 `data/secrets/x-accounts/pool.json` 里的 `auth_token`/`ct0`，不引入新的凭据存储。
- 复用其"先写 pending、验证成功才落盘"和"每个账号独立会话/进程/目录"的做法。
- 适配层需把其会话格式映射到当前池字段（`label`、`status`、`auth_token`、`ct0`），不改动现有 `Lease`/`AccountPool` 契约。
- 登录与采集分离，采集路径不因登录代码而增加新依赖或改变现有失败分类含义。

### P2：前端构建漂移检测

在当前 `x_client.py` 的错误分类里增加构建级诊断：记录当前 X/前端构建标识、把"接口结构变化"与"数据异常"区分开。目的是让改版事故有一条可定位的错误，而不是笼统 `parse_error`。不改变 `engine`/`scheduler` 的控制流。

### P3：Cookie 校验与冷却精度

- 采用其 Cookie 域/路径/冲突/过期校验，提前拦截导入错误，避免到 401 才发现。
- 冷却时间优先读取 `Retry-After` 与 `x-rate-limit-reset`，无值再回退 900s，替换当前固定 900s。

## 6. 明确不采纳

1. 移除跨会话失效转移或改为失败停批——对长期采集是倒退。
2. 取消原始页留存或去掉 `--expect-post`/reconciliation——正是为修"遗漏重大公告"事故而保留。
3. 引入其空 `SIGN_BUILDS` 的 x-web 适配作为采集路径——当前不可发送请求。
4. 用其 `client/output` 结果格式替代当前不可覆盖运行归档与入库衔接。
5. 把账号管理迁移到 env 或把池逻辑并入可复用技能——已明确账号是项目本地动态数据。

## 7. 与第一阶段约束的一致性

- 采纳项全部留在**本地**：登录、会话生成、原始页、重试状态都不上服务器。
- 不引入网站数据库、Agent 上报、API key 或公开用户体系；不触发官网对账、事件抽取或估计。
- 不新增线上爬虫部署或分布式调度。
- 凭据仍只留在忽略的 `data/` 下、权限 0600、不进入 Git/日志/输出，对外只用 `label`。
- 若采纳 P1，需要同步更新 [x-crawler 运行手册](../../development/x-crawler.md) 的"前置/尚未完成"，并补充离线与本地真实登录验证；真实登录属于本地运行状态，其验证证据按既有规则留在本地 `data/`。

## 8. 验收（若决定实施）

1. 离线单测：登录产物的字段映射、pending→session 落盘、`AccountPool` 契约不变、凭据不外泄；前端构建漂移的分类；Cookie 校验与冷却 header 解析。
2. 本地真实登录 1 个账号，成功生成 `auth_token`/`ct0` 并可被现有 `Lease` 消费；失败路径不覆盖已有会话。
3. 回归：`pnpm crawl:test:unit` 与既有 51 账号基准路径不受影响；`pnpm check` 通过。
4. 报告实际执行的检查与仍有限制，不把离线通过表述为线上可用。

## 9. 参考

- [官方 X 采集爬虫子系统设计](2026-09-14-crawler-subsystem-design.md)
- [X 采集爬虫运行手册](../../development/x-crawler.md)
- [官方 X 账号采集（已被取代的旧入口）](../../development/official-x-monitoring.md)
- 外部：`x-account-client` 的 `client/x_tweet_client.py`、`client/x_tweet_client_v2.py`、`client/x_web_adapter.py`、`login/scripts/x_login_http.py`、`docs/validation.md`
