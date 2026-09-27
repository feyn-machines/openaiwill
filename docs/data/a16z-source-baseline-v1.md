# 首版赛道来源：保留 a16z 原始口径

确认日期：2026-09-12。首版以来源可追溯为先：原图怎么分组就怎么保留，不自行拆分，不把不同报告拼成一份“a16z 官方分类”。

## 行业目录：固定一张原图的九个行业

首版行业参考采用 a16z [Where Enterprises are Actually Adopting AI](https://a16z.com/where-enterprises-are-actually-adopting-ai/) 中的 **The Models Are Improving Quickly But Unevenly** [原图](https://d1lamhf6l6yk6d.cloudfront.net/uploads/2026/04/The-Models-are-Improving-Fast-v3-scaled.png)。文章发布于 **2026-04-08**，作者 Kimberly Tan；图中比较的 GDPval 快照是 **2025 年 9 月与 2026 年 4 月**。

以下严格按原图从上到下保留。中文仅为显示翻译，英文原名和分组不改。

| 原始行业名 | 中文显示名 | 该图可见职业条目数 |
| --- | --- | ---: |
| Real Estate and Rental and Leasing | 房地产与租赁业 | 5 |
| Manufacturing | 制造业 | 5 |
| Professional, Scientific, and Technical Services | 专业、科学与技术服务业 | 5 |
| Government | 政府 | 5 |
| Health Care and Social Assistance | 医疗保健与社会援助 | 5 |
| Finance and Insurance | 金融与保险业 | 5 |
| Retail Trade | 零售业 | 4 |
| Wholesale Trade | 批发业 | 5 |
| Information | 信息业 | 5 |

**保留“专业、科学与技术服务业”这一原始大组，不再自行拆分。** 原图下含会计师与审计师、律师等职业；“金融与保险业”本来就是另一组。此前“法律、财务、咨询与科学研究服务”的中文组合是 AI 自拟范围，不是原图的准确名称，应以这里保存的原文为准。

机器数据：[a16z-industry-reference.v1.json](../../datasets/a16z-industry-reference.v1.json)。每项记录原名、次序、图中位置、原始链接；整份来源记录发布日期、统计快照日期、核验日期与图片哈希。已核对 9 个行业和该图可见的 44 个职业条目；44 仅是本图计数，不推称 GDPval 完整数据集规模，也不补造缺失职业。

这张图是任务能力基准比较，既不是完整全球行业标准，也不等于整行业已可自主运行。原文没有行业权重或全球接管完成度，数据中这些数值保持空值。后续 AI 推演仍须单独注明估计，不能把基准胜率直接当作现实行业完成度。

## 产品榜单：另存原始版本，不混入行业目录

a16z 的 [The AI Application Spending Report](https://a16z.com/the-ai-application-spending-report-where-startup-dollars-really-go/) 发布于 **2025-10-02**，统计期为 **2025 年 6–8 月**，基于 Mercury 客户经 Mercury 支付的交易样本。其公开榜单有 50 个排名，没有逐项支出金额或完整分类列。

[a16z-market-reference.v1.json](../../datasets/a16z-market-reference.v1.json) 保存完整 50 项排名、原图位置和来源版本，以及正文中的九个应用标签。正文明确归类的例子有 38 项，其余 12 项的分类留空。这九个应用标签只属于该支出报告，不能与上述九个行业混为一表；也不称为完整行业分类。

[消费 AI 榜单第六版](https://a16z.com/100-gen-ai-apps-6/) 发布于 2026-03-09，使用 2026 年 1 月的数据：网页榜按 Similarweb 独立月访问量，移动榜按 Sensor Tower 月活用户数。它保留为独立产品发现来源，不提供本版行业权重。

同篇企业报告也有 6 项产品市场匹配标签、10 项收入类别和 11 项能力／收入散点标签。它们没有被拼入行业目录。各张图的准确标题、原链及口径见[企业报告核验记录](../research/a16z-enterprise-source-check-2026-09-12.md)。

## 历史草案与当前状态

此前 20 个产品赛道是参考 a16z、YC 和产品网站后整理的编辑性目录；13／16 组世界范围是 AI 为试算设计的。它们均不作为首版原始来源分类。旧试算和真实采集材料保留供追溯，24.3 分不迁移成 a16z 数据。

来源本身的不一致也保留记录：支出报告的垂直公司比例与另一段数量不一致；消费榜正文和当前原图的 Midjourney 名次不同。按具体原图冻结版本，不自行“修正”成新的官方数据。

此轮只更新来源数据及方法约束。页面、定时采集与评分运行时尚未接入这份目录；没有新增推演分数。
