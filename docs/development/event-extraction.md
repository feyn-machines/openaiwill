# 事件抽取运行手册(事件层)

把采集库里的原帖抽成**去重后的事件**,落进独立的**事件层**(migration `005`)。位于 `scripts/data_pipeline/event_extraction.py`(确定性主干)+ `scripts/data_pipeline/deepseek.py`(唯一的模型调用)。

数据流的第三段(在采集、入库之后):**采集库 → 抽取 → 事件层**。事件层**市场无关**、不带 batch/权重/指标/进度 —— 那些属于以后的段 3 计算批次(会从事件层投影)。设计定稿见本文「表结构」与「设计决定」。

## 三段之间的位置

```
collected_captures(采集库, 原帖+互动指标)
  └─抽取(DeepSeek)→ extracted_events(去重事件, 挂原帖) ← 页面读这里
                      └─段3(以后)→ metric_values → progress_values
```

`extracted_*` 前缀与采集库的 `collected_*` 对称,并与段 3 那套 batch 范围的 `events`/`event_sources` 区分开:名字即层。

## 表结构(005_event_layer.sql,市场无关)

- `extraction_runs` — 一次抽取过程:输入的采集运行、模型、`prompt_sha256`、参数、窗口、状态、`run_sha256`(幂等)。对标 `collection_runs`。
- `extracted_events` — 事件:`dedup_key`(UNIQUE,同一事只一行)、kind、title、summary、primary_org、announced/occurred/scheduled 时间、occurrence_status、抽取出处、confidence、record_sha256。`event_id` 由 `dedup_key` 确定性派生。
- `extracted_event_sources` — 事件 ↔ 原帖:**硬 FK 指回** `collected_sources(run_id, source_id)`,证据可追;互动指标不复制,留采集库。
- `extracted_event_relations` — 事件 ↔ 事件:`part_of`(树)/`follows`·`supersedes`·`refines`(前后链)/`duplicate_of`(去重)。
- `extracted_event_categories` — 事件 ↔ 赛道分类:指向**已有版本化词表**(`taxonomy` = ontology/platform + `taxonomy_version` + `category_id`),不重造词表。

## 前置

- DeepSeek key:`.env` 里 `DEEPSEEK_API_KEY`(基础设施凭据,gitignore、不进 skill、不提交、不 `NEXT_PUBLIC`)。可选 `DEEPSEEK_MODEL`(默认 `deepseek-chat`)、`DEEPSEEK_BASE_URL`(默认 `https://api.deepseek.com`)。
- 本地 PG 已 `pnpm data:up`;走 `data/runtime/venv`(psycopg,stdlib 调 DeepSeek,无新依赖)。
- 采集库里已有采集运行(先 `pnpm data:ingest:x`)。

## 运行

参数是纯 flag,**不要加 `--`**(`--` 只给带位置参数的命令如 `data:ingest:x`)。

```sh
# 只看候选、不调用模型(过滤转推/回复、按 (platform,source_id) 取最新 capture)
pnpm data:extract:events --collection-run baseline-3wk --plan-only \
  --output data/extraction/plan.json

# 抽取并入库(调用 DeepSeek)
pnpm data:extract:events --collection-run baseline-3wk \
  --output data/extraction/baseline-events.json

# 常用可选:--window-start / --window-end(ISO,[start,end))、--limit N、--batch-size 25
# 重新入库一个已存在的归档(纯 DB)
pnpm data:ingest:events data/extraction/baseline-events.json
```

输出必须是 `data/` 下尚不存在的 `.json`(抽取归档不可覆盖)。`run_id` 取文件名 stem。归档记录模型/提示词哈希/输入采集运行/全部事件,可复现、可版本对比。

## 幂等与去重

- 同一归档再 ingest = 空操作(`reused:true`);同 `run_id` 内容不同会被拒绝。
- 跨抽取运行的同一事件(同 `dedup_key` → 同 `event_id`)只保留一行(`ON CONFLICT DO NOTHING`),仅补新的证据链接。一次抽取内多帖同事件也会合并证据。
- 每个事件至少挂一条采集库里的原帖;`source_id` 不在采集库会被 FK 拒绝。

## 验证

- 离线单测:`pnpm data:test:unit`(候选筛选、文档组装、去重、关系解析、行构建、`run_sha256`、凭据不外泄、DeepSeek 配置),已并入 `pnpm check`。
- 真实 PG 集成:`pnpm data:test`(seed 采集库 → 抽取入库 → 事件/证据/关系/分类、幂等、拒绝改写、跨运行去重、FK 溯源)。
- 实机(2026-09-14):baseline-3wk 计划态 **880 候选**(1625 − 435 转推 − 310 回复);烟囱 25 候选 → 3 事件,其中 Wan3.0 一条合并 18 帖证据。

## 尚未完成 / 已知边界

- **分类**:模型现未接词表 → `extracted_event_categories` 暂空;接入 ontology/platform 赛道词表后按版本引用即可开。
- **primary_org** 取发布方,可能≠模型作者(如 @alibaba_cloud 发的第三方模型);提示词层可收紧。
- 公司/产品/人物实体解析、availability/adoption 阶段、claims 核实链:v1 未做。
- **段 3**(事件层 → 市场范围计算批次的投影与打分)、官网对账、页面:另行进行。
- 全文只用采集库的 280 字 `public_excerpt`(全文在磁盘原始页);够抽标题级事件,深度抽取以后可取全文。
