# X 采集爬虫运行手册

项目自有的并发 X 官方账号采集器，位于 `scripts/crawler/`。取代原技能 `social-qingguo-collector`（已退役，目录保留为历史，项目不再 `import` 它）。设计见 [爬虫子系统设计](../superpowers/specs/2026-09-14-crawler-subsystem-design.md)。

数据流分三段独立：**采集**(本手册,`scripts/crawler`)→ **入库到采集库**(`data:ingest:x`,见下)→ **市场范围计算批次**(现有 `run_batch`,单独一步,本手册不含)。采集只产运行归档、不知道市场/指标;入库把归档幂等落进独立的采集库(不带市场/权重/指标/进度);计算阶段再从采集库按范围选证据。**不做**官网发布记录对账、事件抽取或估计。

## 前置

- 代理：`X_PROXY`（或 `QINGGUO_PROXY_URL` / `SOCIAL_PROXY_URL`）在 `.env`，青果 https 隧道。代理是基础设施凭据，留在 env。
- 账号池：`data/secrets/x-accounts/pool.json`（gitignore、0600）。字段 `username,password,totp_secret,email,email_password,auth_token,ct0,status,cooldown_until,last_used_at,label`。仅 token（有 `auth_token`、`ct0` 为 null）的账号可用——引擎会合成 32 位 ct0（cookie 与 `x-csrf-token` 同值，X 读接口接受），已于 2026-09-14 实机验证。
- venv：`data/runtime/crawler-venv`。首次或依赖变更后 `pnpm crawl:setup`（装 `requirements-crawler.txt`：twikit 2.3.3、httpx 0.28.1）。

## 运行

```sh
# 只看计划、不访问 X
pnpm crawl:x -- --start 2026-08-24T00:00:00Z --end 2026-09-14T00:00:00Z \
  --plan-only --output data/collection/official-x/plan.json

# 三周基准（默认并发 5）
pnpm crawl:x -- --start 2026-08-24T00:00:00Z --end 2026-09-14T00:00:00Z \
  --concurrency 5 --output data/collection/official-x/three-week-baseline.json

# 定向账号 + 已知公告验收
pnpm crawl:x -- --start ... --end ... --handles OpenAI \
  --expect-post <postid> --output data/collection/official-x/openai.json
```

窗口用 `[start, end)`，需带时区。输出必须是 `data/` 下尚不存在的 `.json`（运行不可覆盖）；原始页写入同名 `.pages/<jobid>/` 目录，逐页 SHA-256。参数：`--concurrency`、`--count`（每页请求数，默认 40）、`--max-pages`、`--max-requests`、`--timeout`、`--pace`（≥3s）。账号自动按健康态从池中挑选，无需指定。

## 进度

运行时向 stderr 打印进度。TTY 下是原地刷新的多行块（总体 + 每个活跃 worker `@handle 第N页 (账号label)` + 账号池 usable/cooldown/dead）；重定向到日志时是节流的单行汇总加 failover 里程碑行。收尾打印一行总结：完成/incomplete 数、总帖数、请求数、用时、账号冷却/失效数、reconciliation 状态。

## 入库到采集库（data:ingest:x）

把一次爬虫运行归档幂等地落进 Postgres 里独立的采集库（migration `004_collection_store.sql`：`collection_runs / collected_sources / collected_captures / collection_gaps`）。这层不带市场范围、权重、指标或进度——那属于后续的计算批次。

```sh
pnpm data:ingest:x -- data/collection/official-x/<run>.json
```

`run_id` 取运行文件名(stem)。同一 `run_id` 内容相同再 ingest 是空操作(`reused:true`);同 `run_id` 内容不同会被拒绝。同一帖跨多次运行出现 = 多条 capture(按时间的观测),查询时按 `(platform, source_id)` 去重。凭据不入库,只存被监控账号的公开身份;原始页留磁盘,采集库按 SHA-256 在 `collection_runs.raw_pages` 引用。走 `data/runtime/venv`(psycopg),需本地 PG 已 `pnpm data:up`。

真实验证(2026-09-14):把 `smoke-2handle` 运行入库,得 22 sources / 22 captures / 2 gaps(OpenAI 17、AnthropicAI 5,均 complete),互动指标(含 null)如实保留,采集库无任何凭据列,重放 `reused:true`。

## 并发与代理模型

青果隧道**每条新连接换一个出口 IP，连接内 IP 稳定**。因此一个账号绑一条独占连接（`max_connections=1`）= 一个稳定 IP 覆盖其整个抓取；账号之间并发即天然把足迹摊到不同 IP。约 1/5–1/6 的连接会 `ConnectError`（坏出口 IP），按 transport 错误在新连接上重试，不判账号失效。青果套餐并发上限未知（3 路已验证干净），并发度从保守值起步、可配。

## 失效转移

- 限流（429 / X 错误码 88、130）：账号进冷却，该 job 换别的账号重试（计入 `--max-attempts`，默认 4）。
- 认证失败（401/403 / 码 32、89、215、353 / 账号锁定/封禁）：账号标 `dead`，job 换账号重试。
- 传输错误（`ConnectError`、超时等）：不判账号问题，同账号换新连接（新 IP）重试，另计 `max_transient`（默认 8）。
- 账号换遍仍不成 → 该 job `incomplete` 并记原因，不阻塞其余 job。单账号错误被转移消化后不影响整次 `ok`。

## 成败判据

`ok=True` 要求：所有 job 达到 `search_ended`（翻过窗口起点）、无缺失的 `--expect-post`。否则 `needs_attention`。`coverage_status=provider_timelines` 只表示 X 返回的时间线翻过了起点，**不代表重大发布已收齐**——官网对账仍需另行实现。

## 凭据安全

账号密码、2FA、auth_token、ct0、邮箱密码、代理凭据**绝不**进 Git、运行输出、日志或进度；对外只用 `label`。原始页只存响应体，不含请求头/cookie/代理。池与输出在忽略的 `data/` 下。

## 验证

- 离线单测：`pnpm crawl:test:unit`（解析、账号池冷却/失效/LRU、引擎窗口/身份/cursor/限流、并发调度、失效转移、传输重试、进度渲染、输出组装、凭据不外泄），已并入 `pnpm check`。
- 实机烟囱（2026-09-14）：`@OpenAI`+`@AnthropicAI` 三天窗、并发 2，两账号并行、各自合成 ct0，均 `search_ended`，reconciliation 命中三条 OpenAI 金融服务公告 ID（旧采集遗漏的那批）。

## 尚未完成

官网发布记录自动对账；回复/评论**正文**抓取（现仅采 `replies` 计数）；定时/增量重跑调度；事件抽取与定向 Reddit/X 深挖；**段 3**（采集库→市场范围计算批次的投影与估计，走现有 `run_batch`）。采集(段1)与入库到采集库(段2)已实现。旧手册 [official-x-monitoring](official-x-monitoring.md) 描述的是被取代的单账号入口。

**基准已建立(2026-09-14)**:全 51 账号、窗口 `[2026-08-24, 2026-09-14)`、并发 5、每账号 20 页，一次跑完 51/51 complete、0 incomplete、1625 帖(原创~880/转推435/回复310)、164 请求、3分06秒、0 冷却/失效、6 次传输重试自愈。已 `data:ingest:x` 入库为 `run_id=baseline-3wk`(1625 sources/captures、51 gap 全 complete)。早先 calib-3day(115)与 smoke-2handle(22)的帖被完整覆盖并再次观测,证明同一帖跨运行的多 capture 观测序列成立。运行文件 `data/collection/official-x/baseline-3wk.json`(gitignore 的 `data/` 下)。

## 相关

- 与外部实现 `x-account-client` 的对比及借鉴建议，见 [X 采集实现对比 spec](../superpowers/specs/2026-09-23-x-account-client-crawler-comparison.md)。
