# 真实数据入库与计算试算

计算于 2026-09-13（Asia/Taipei），材料采集于 2026-09-12。真实来源已写入本机 PostgreSQL 的 ready 批次，并完成重复导入和直接 SQL 回查。网页尚未接入。

**补充核查（2026-09-13）：本批材料漏掉了 OpenAI 9 月 10 日发布的 Agents API 和 ChatGPT for Financial Services。** 已定位查询截断和补抓游标跨窗口取值问题；以下 44/100 未纳入这些发布，不能代表重大更新已经覆盖。详见[漏采核查](collection-gap-openai-2026-09-13.md)。金融产品的三条官方 X 帖现已通过实时搜索补采保存，但未入新批次或重算；原冻结批次和数值保留。

**实数统计：2,707 条去重来源、2,721 份采集记录。工作进度试算：应用界面与业务开发 44/100，保守–积极情景 22–64。** 后者是 AI 对真实材料做出的主观状态判断及加权结果，不是从互动数推出的实测完成率。

## 真实观测

| 原帖发布时间窗口（Asia/Taipei） | 平台 | 去重帖子 | 最新回复／评论数合计 |
| --- | --- | ---: | ---: |
| 8 月 31 日—9 月 6 日 | X | 218 | 30,199 |
| 8 月 31 日—9 月 6 日 | Reddit | 1,290 | 15,996 |
| 9 月 7 日—9 月 12 日采集截止 | X | 206 | 10,236 |
| 9 月 7 日—9 月 12 日采集截止 | Reddit | 993 | 8,445 |

发布时间截止为 9 月 12 日 23:43:27，材料截止为 23:51:43。互动值使用截止前最新采集，X 字段为 replies，Reddit 为 comments；它们不是各周末的历史快照，也不是去重参与人数。2,707 条最新评论字段均有观测，其中 322 条是实际零值。保留 52 条原查询覆盖记录，全部汇总仍标为 partial；未取得材料不等于没有更新。两个窗口长度和采集深度不同，不计算热度增长率或能力环比。

## 事件整理与输入边界

从档案中阅读全文并选择 12 条与软件开发直接相关的来源：6 条官方 X、6 条 Reddit，归为 9 个事件组。其余来源已入库用于样本统计，尚未全部完成事件提取。工作相关性 accepted 不表示声明属实。

| 事件组 | 原帖 | 证据含义 |
| --- | --- | --- |
| Qwen WebDev 表现与 API 公告 | [阿里云帖一](https://x.com/alibaba_cloud/status/2095057521933496329)、[帖二](https://x.com/alibaba_cloud/status/2095061615418675631) | 同一厂商的两帖，归为一条声明；榜单数据未独立复测 |
| GPT-6 Astra 接入 Copilot | [GitHub](https://x.com/github/status/2095971389190885815)、[VS Code](https://x.com/code/status/2095976538764091516) | 同一集团一次接入，采用阶段 integrated；不等于两个独立客户或无人生产能力 |
| ChatGPT Sites 更新 | [ChatGPT](https://x.com/ChatGPT/status/2098457920291946894) | 官方功能与规模自述，站点数量未独立验证 |
| Meta SDK 文档与当前 API | [Meta for Developers](https://x.com/MetaforDevs/status/2095263385458008381) | 集成工具条件及过期 API 风险，不是实测成功率 |
| 用户应用迁移对照 | [社区原帖](https://reddit.com/r/AI_Agents/comments/1w72jrk/claude_code_vs_codex_37_min_but_working_ui_vs_27/) | 一次未复现的用户自述，含可运行产出和人工纠偏 |
| 带检查的自主开发流水线 | [社区原帖](https://reddit.com/r/AI_Agents/comments/1w5wj4x/i_let_an_agent_pick_its_own_task_every_morning/) | 未核验身份及任务记录；不将自报 19/41 换算成赛道完成率 |
| API 集成独立校验工具 | [作者原帖](https://reddit.com/r/AI_Agents/comments/1wcn7l8/i_built_an_opensource_api_verification_tool_for/) | 开发者自述，用作集成条件和验证缺口线索 |
| 重复的 RAG 后端经验陈述 | [原帖一](https://reddit.com/r/AI_Agents/comments/1w6ileb/why_multiagent_rag_pipelines_choke_on_production/)、[原帖二](https://reddit.com/r/AI_Agents/comments/1w7f2uy/why_multiagent_rag_pipelines_choke_on_production/) | 不同账号、相同全文、含商业推介；两来源一事件，不构成相互佐证 |
| 编码任务重试与成本讨论 | [社区原帖](https://reddit.com/r/LocalLLaMA/comments/1wbk85s/how_much_does_it_cost_to_run_an_ai_coding_agent_i/) | 自述次数与按标价估算的成本，未当作实际账单或通用成功率 |

这里只确认保存的帖子内容及其来源关系；能力、排名、采用效果和用户案例仍保留 self_reported。历史活动只作为当日声明的内容，不回填为本系统验证过的历史事件。

## 工作进度试算

| 工作 | 已整理事件 | 关联帖子 | 回复／评论 | 提议权重 | 保守 | 中央 | 积极 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 实现网页移动端与桌面界面 | 6 | 8 | 438 | 40% | 30 | 55 | 75 |
| 开发业务逻辑与服务接口 | 6 | 8 | 424 | 40% | 20 | 40 | 60 |
| 连接外部系统与数据接口 | 3 | 4 | 14 | 20% | 10 | 30 | 50 |
| **赛道加权结果** | — | — | — | **100%** | **22** | **44** | **64** |

同一来源可以关联多个工作，三行的事件、帖子和互动不能相加当作父级去重量。完整三个子项均保留，没有删去较弱的集成工作后重新归一化。

中央值计算为 `0.4 × 55 + 0.4 × 40 + 0.2 × 30 = 44`。情景与权重均含 AI 先验，未进行任务分布或概率校准。网页产品与用户迁移例子支持部分交付能力；移动端/桌面端、复杂业务约束、真实 API 合同和失败恢复缺乏充分证据，因此保留较宽情景。评论较多不会增加分值。完整判断者、理由、假设、限制和 20 处采集引用均保存在冻结输入中。

这是一次新方法下的局部初始化，不是全球进度、实际岗位替代率或生产基线，也没有足够依据给出上周到本周的能力增量。[方法说明](real-evidence-estimation-pilot-v1.md)给出范围、先验和复算规则。

## 本地验收

批次 `real:archive-2026-09-12:software-application-code:v1` 为 ready，配置 `real-archive-software-2026-09-12-v1`，本体 v1.0.0，引擎 `real-local-pipeline-1`。共保存 2,738 个指标值、4 个进度值及其输入关系。原五个合成批次保留原哈希与数值。

- 真实批次重新导入返回 reused=true，冻结报告及记录数不变。
- 八个日期窗口/平台指标与独立逐条复算一致，直接 SQL 结果与冻结报告一致。
- 51 项数据测试通过，涵盖真实 PostgreSQL；五批合成回归通过；pnpm check 全部通过（安全、平台/本体、11 项无数据库单元测试、设计、lint、类型和构建）。
- 独立代码与证据审阅均无未解决的阻断问题；已补充 integrated 以准确记录已接入状态。

运行命令与输入规则见[本地数据链路](../development/local-data-pipeline.md)。原始材料、完整输入和数据库输出只留在本机根目录 data/，未发布或上传。
