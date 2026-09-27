# GPT-6 Astra / Claude Fable 5.1：发布事实与 AGI 声明核验

核验日期：2026-09-12（Asia/Taipei）。范围：指定官方发布页、产品页、官方日期补证，以及一轮原始讲话线索检索。可用性记录的是官方页面口径，未逐账户实测。

## 可核的发布事件

| 模型 | 首发日期 | 日期证据与命名 |
| --- | --- | --- |
| GPT-6 Astra | 2026-09-03 | [官方安全公告](https://openai.com/index/safety-overview-gpt-6-astra/) 标注当天日期并称当天发布；[官方 RSS](https://openai.com/news/rss.xml) 中主发布条目的 `pubDate` 为 `Thu, 03 Sep 2026 11:00:00 GMT`。 |
| Claude Fable 5.1 / Claude Mythos 5.1 | 2026-09-01 | [Fable 产品页](https://www.anthropic.com/claude/fable) 的 Announcements 将 Fable 5.1 标为 `Sep 1, 2026`，链接至[联合发布页](https://www.anthropic.com/claude-fable-and-mythos-5-1)。联合页仅显示月份；产品页补足日级精度，未确认发布时刻。 |

官方拼写是 **Fable**，不是 FABEL。OpenAI RSS 另有 9 月 9 日的[面向工作的 Astra 文章](https://openai.com/index/gpt-6-astra-next-generation-work)，不应据此覆盖 9 月 3 日首发事件。

## 可用性边界

- **Astra：**[发布页](https://openai.com/index/gpt-6-astra/) 说明先向部分组织开放，随后扩至 ChatGPT Plus、Pro、Business、Enterprise，以及 OpenAI API、Azure、AWS Bedrock；API 名称为 `gpt-6-astra`。Astra Pro 面向 Pro、Business、Enterprise；Enterprise 默认关闭，需管理员启用。[官方 Academy](https://academy.openai.com/en/pages/chatgpt-5-6-champion-launch-resources-tzoyyc) 同样说明 9 月 3 日起分批开放。不能仅按发布日期推定任意账户均已可用。
- **Fable 5.1：**[产品页](https://www.anthropic.com/claude/fable) 列出 Pro、Max、Team、Enterprise 与 Claude Platform、AWS、Google Cloud、Microsoft Foundry；API 名称 `claude-fable-5-1`。触发网络安全或生物学防护的请求会转给较低能力模型。默认有 30 天安全监测数据保留；合资格客户在 EFS 可用前可使用零数据保留。
- **Mythos 5.1：**[联合发布页](https://www.anthropic.com/claude-fable-and-mythos-5-1) 说明它与 Fable 5.1 是同一模型、采用不同防护，只向受审核的网络安全与生命科学用户开放；当时限部分美国组织。EFS 为秋季分阶段推出计划，不能标成全面上线。

## AGI：尚不能作为两家公司共同确认的事实

对[OpenAI 主发布页](https://openai.com/index/gpt-6-astra/)的核验只发现 ARC-AGI 基准名称及成绩，没有明确宣布已实现 AGI；“基准上的人类水平”也不能自动转换为通用能力结论。对[Anthropic 联合发布页](https://www.anthropic.com/claude-fable-and-mythos-5-1)检索 `AGI` 无匹配，未找到 Dario Amodei 或公司在该页宣布 AGI 已实现。这里的结论仅覆盖本轮核验材料，不声称证明所有场合均无相关讲话。

**待核讲话线索：**Greg Brockman；2026-09-03；闭门媒体简报；“Welcome to the AGI era.” [VentureBeat 线索](https://venturebeat.com/technology/welcome-to-the-agi-era-openai-launches-gpt-6-astra)、[Axios 线索](https://www.axios.com/2026/09/03/openai-astra-gpt-6-agi-brockman)。

本轮没有取得该场合的公开原视频、完整逐字稿或本人原帖；VentureBeat 内嵌视频入口未成功读取。因此原话、上下文、限定语与准确场合仍待原始材料核验，不能归给 Sam Altman，也不进入已核事实。未定位与 Fable 5.1 对应的具名 AGI 原话。

## 给后续原帖采集的线索

本轮未直连 X。下列 URL 只定位候选记录，正文、时间和与 AGI 的关联均需经项目青果链路取得原帖后验证：

| 候选 | 线索来源 | 待核内容 |
| --- | --- | --- |
| [Greg Brockman 候选原帖](https://x.com/gdb/status/2096721633876771094) | [WBN 节目索引](https://music.amazon.ca/podcasts/0e869da1-d571-456e-92f0-c09e4d3102cd/episodes/202d2abe-8b49-40a2-b5cf-b1132b2abe8e/wbn-ai-%E3%83%86%E3%82%AF%E3%83%8E%E3%83%AD%E3%82%B8%E3%83%BC-%E3%82%B9%E3%82%BF%E3%83%BC%E3%83%88%E3%82%A2%E3%83%83%E3%83%97%E3%81%AB%E7%89%B9%E5%8C%96%E3%81%97%E3%81%9F%E3%83%A9%E3%82%A4%E3%83%96%E3%83%8B%E3%83%A5%E3%83%BC%E3%82%B9%E7%95%AA%E7%B5%84-nvidia-%E3%82%B8%E3%82%A7%E3%83%B3%E3%82%B9%E3%83%B3%E3%83%BB%E3%83%95%E3%82%A2%E3%83%B3%E3%80%8Cagi%E3%81%AF%E5%88%B0%E6%9D%A5%E3%81%97%E3%81%9F%E3%80%8Dgpt-6-astra%E3%81%8C%E5%85%A8%E5%93%A1%E3%81%AB%E5%85%AC%E9%96%8B%E3%80%81%E3%81%82%E3%82%8F%E3%81%9B%E3%81%A6openai%E7%A0%94%E7%A9%B6%E3%83%88%E3%83%83%E3%83%97%E3%81%AF%E3%80%8Cai%E9%96%8B%E7%99%BA%E3%81%AE%E6%B8%9B%E9%80%9F%E3%80%8D%E3%82%92%E6%8F%90%E8%A8%80) 检索摘要列出该 URL | 可能与 Astra 后续开放有关；不能作为 AGI 引语证据。 |

建议有界检索：`from:gdb (Astra OR AGI) since:2026-09-02 until:2026-09-08`；Fable 线索可检索 `from:AnthropicAI (Fable OR Mythos) since:2026-08-31 until:2026-09-03`。若仍无公开原始讲话材料，维持“媒体线索／原始材料待核”，无需填补。

入库时可先收录两条官方发布事件，并分别关联模型、厂商、可用性与来源。AGI 保留为具名声明的待核候选；“这两次发布是重要里程碑”属于编辑判断，需与发布事实分开。
