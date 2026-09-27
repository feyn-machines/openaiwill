# openaiwill 白皮书写法参考

研究日期：2026-09-13（Asia/Taipei）

## 结论先行

openaiwill 最适合采用三层文档，而不是把倡议、方法和每期数据全部塞进一篇长白皮书：

1. **短倡议主稿**：用 **Will AI Kill Your Idea? / Every AI update could change your answer.** 引出读者的判断问题，说明 openaiwill 为什么存在、为谁服务、坚持什么。
2. **独立方法附件**：定义“独立完成主要生产与服务工作”、覆盖范围、证据层级、指标、计算、不确定性和版本规则。
3. **定期证据报告**：每期回答“发生了什么、判断为什么改变、证据有多强、还不知道什么”。

这种组合分别吸收倡议型写作、指标方法报告和证据综述的长处，同时保留 openaiwill 的身份：它是一项倡议，网站承载成果，测量和证据是建立可信度的方法。

## 八份主要参考

### 1. Mozilla Manifesto：先让倡议能被一页读懂

- **官方文件**：[Mozilla Manifesto](https://www.mozilla.org/en-US/about/manifesto/)
- **日期 / 版本**：初版 2007；2017 增补。
- **可借用的精确写法**：现实发生了什么 → 为什么需要一个社区 → Manifesto 的目的 → 编号原则 → 组织承诺 → 邀请参与。正文即使离开技术附件，也能独立传播。
- **不要照搬**：宽泛的价值口号和只用 `should` 表达的愿望。openaiwill 每一项原则都应能落到证据、行为或修订规则。
- **映射到 openaiwill**：`封面与公开钩子`、`为什么存在`、`倡议与价值观`、`社区如何参与`。适合把现有身份、主线、价值观压缩成一页；方法和评分另放。

### 2. NIST AI Risk Management Framework 1.0：把抽象原则写成可重复的过程

- **官方文件**：[AI RMF 1.0 发布页](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)、[AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- **日期 / 版本**：2023-01-26，v1.0；截至本次核查，NIST 明示 v1.0 正在修订，尚未用草案替代正式版。
- **可借用的精确写法**：先定义目的、对象、读者和适用边界，再用 `Govern → Map → Measure → Manage` 组织循环；把 Profiles、Playbook 和版本记录从核心正文拆开。
- **不要照搬**：合规框架语气、企业控制清单或“采用框架即可信”的暗示。openaiwill 不是企业治理产品。
- **映射到 openaiwill**：`范围与术语` → `证据治理` → `来源与工作映射` → `测量与不确定性` → `发布、纠错与修订`。可借其循环结构，不必借其风险分类。

### 3. OpenAI Preparedness Framework v2：把“什么证据会改变判断”写清楚

- **官方文件**：[更新说明](https://openai.com/index/updating-our-preparedness-framework/)、[Preparedness Framework v2 PDF](https://cdn.openai.com/pdf/18a02b5d-6b67-4cec-ab64-68cdfbddebcd/preparedness-framework-v2.pdf)
- **日期 / 版本**：v2，最后更新 2025-04-15；官方将其称为持续更新的 living document。
- **可借用的精确写法**：严格限定跟踪范围 → 区分“已跟踪类别”和“仍在研究的类别” → 说明如何测量 → 设置触发进一步判断的门槛 → 说明评估保障、外部参与和变更记录。
- **不要照搬**：实验室自评的权威口吻、未经 openaiwill 数据校准的硬阈值，或把风险部署决策当成项目职责。
- **映射到 openaiwill**：`候选信号` → `已核实事件` → `足以改变进度判断的证据` → `新判断及区间` → `重新评估条件`。Sam Altman 的最新承诺应按“公开承诺 / 已实施访问 / 独立报告”三个状态记录。

### 4. OECD AI Capability Indicators：用读者版与技术卷分离“看懂”和“复核”

- **官方文件**：[介绍与读者版](https://oecd.ai/en/ai-publications/introducing-the-oecd-ai-capability-indicators)、[读者版 PDF](https://www.oecd.org/content/dam/oecd/en/publications/reports/2025/06/introducing-the-oecd-ai-capability-indicators_7c0731f0/be745f04-en.pdf)、[技术报告 PDF](https://www.oecd.org/content/dam/oecd/en/publications/reports/2025/11/oecd-ai-capability-indicators-technical-report_d3762d1a/9cdb3dd1-en.pdf)
- **日期 / 版本**：beta 指标于 2025-06-03 发布；读者版与后续技术报告均为 2025 年版本。读者版明确称当前评级在 2024-11 定稿，并计划持续修订。
- **可借用的精确写法**：先给好指标的标准（易懂、与决策相关、覆盖充分、可持续更新），再展示少量分级量表；每个领域固定写“级别描述、当前判断、依据、剩余挑战”。局限和下一步单列。
- **不要照搬**：把“完全人类等价”设成唯一终点，或直接复制五级量表。openaiwill 测的是在具体条件下独立完成工作的程度，不是抽象认知能力总榜；目前也没有生产总分。
- **映射到 openaiwill**：主稿只解释进度概念、维度和读者用途；技术附件容纳工作本体、O*NET 映射、权重、计算、验证与版本。每个行业 / 任务页使用相同判断模板。

### 5. METR Time Horizon 1.1：把一个指标的定义、版本变化和测量上限同时交代

- **官方文件**：[Time Horizon 1.1](https://metr.org/blog/2026-1-29-time-horizon-1-1/)、[持续更新的 Time Horizons 页面](https://metr.org/time-horizons/)
- **日期 / 版本**：TH1.1 于 2026-01-29 发布；在线测量页标注最后更新 2026-05-08，并将 TH1.1 标为当前版本。
- **可借用的精确写法**：先用一句话定义直观单位；紧接着交代任务分布、人类基准、成功概率和置信区间；版本更新逐项列任务新增 / 删除 / 修改、基础设施变化、估计移动原因和仍然存在的宽区间。
- **不要照搬**：把软件任务的 time horizon 外推成所有工作的“接管进度”，把人类完成时间当作经济权重，或把 50% 成功写成稳定可用。METR 自己也说明任务干净、范围偏软件且高时长区间不可靠。
- **映射到 openaiwill**：每个指标固定写 `定义｜分母与覆盖｜任务条件｜模型/工具｜人工介入｜验收规则｜样本量｜点估计与区间｜适用边界｜相较上版为何变化`。

### 6. Anthropic Economic Index: Cadences：先说明现实变了，方法为何必须跟着变

- **官方文件**：[Anthropic Economic Index report: Cadences](https://www.anthropic.com/research/economic-index-june-2026-report)
- **日期 / 版本**：2026-06-26，当期 Economic Index 报告。
- **可借用的精确写法**：开头不急着报结论，而是先说明使用方式从对话转向长时 Agent 任务，旧数据已不能完整表示现实；随后列出本版采样、分类器和数据粒度的变化，再预告各章发现。单项分析采用“观察 → 可能解释 → 稳健性检查 / 替代解释 → 仍不能排除什么”。
- **不要照搬**：把单一厂商用户当作整个经济，把对话或产物当作任务成功，或把用户自述当作独立验证。openaiwill 仍需记录验收、失败、重试和人工修改。
- **映射到 openaiwill**：`本版方法变化`、`真实使用与采用`、`单项证据分析`、`样本偏差`。每次数据管线或分类规则变化，应在结果之前解释它会让哪些数值失去直接可比性。

### 7. Stanford AI Index Report 2026：为不同阅读深度建立入口

- **官方文件**：[2026 AI Index 报告页](https://hai.stanford.edu/ai-index/2026-ai-index-report)、[完整 PDF](https://hai.stanford.edu/assets/files/ai_index_report_2026.pdf)
- **日期 / 版本**：2026 年度报告，2026-04 发布。
- **可借用的精确写法**：首页先给少量 `Top Takeaways`，每条使用“可判断的完整句子 + 关键数字 / 边界 + 回链章节”；正文按稳定领域展开，图表连接来源和方法，完整方法与公开数据放附录。
- **不要照搬**：近四百页的百科全书规模，或把来源、口径和时间不同的指标强行相加成总分。Top Takeaway 也不能只写戏剧性数字而不带口径。
- **映射到 openaiwill**：定期报告采用 `本期最重要变化` → `为什么判断改变` → `行业 / 任务章节` → `证据和方法链接`。首页、行业页和白皮书应回到同一份版本化判断记录。

### 8. International AI Safety Report 2026：把不确定性写进主结构，而不是埋在免责声明里

- **官方文件**：[International AI Safety Report 2026](https://internationalaisafetyreport.org/publication/international-ai-safety-report-2026)、[完整 PDF](https://internationalaisafetyreport.org/sites/default/files/2026-02/international-ai-safety-report-2026.pdf)
- **日期 / 版本**：2026-02-03，第二份年度报告；研究证据截止 2025-12。
- **可借用的精确写法**：先交代 scope、聚焦原因、作者与评审过程；围绕少数中心问题组织全文；各主题重复呈现“关键认识 → 自上版以来的变化 → 证据质量 / 分歧 → evidence gaps → 决策挑战”。结论明确共同认识、仍有分歧和当前无法可靠断言的部分。
- **不要照搬**：安全监管定位、全球共识口吻或借专家人数代替证据质量。openaiwill 的主线仍是工作完成进度及其对行业和想法的意义。
- **映射到 openaiwill**：`证据如何成为判断`和`限制与证据缺口`的首要范本。每项重要判断同时列：已知事实、证据角色与质量、反证或相冲突结果、未知项、下一次更新条件。

## 建议的 openaiwill 主稿目录

1. **一页倡议**：首页钩子、认知缺口、项目主张、为谁服务、邀请参与。
2. **范围与定义**：何谓“独立完成主要工作”；区分能力、真实采用和经济影响。
3. **我们帮助读者回答什么**：整体进度、行业变化、创业假设、实际失败点。
4. **目前能说什么**：只写已有证据支持的判断和变化，不初始化虚构总分。
5. **如何测量**：工作范围、任务条件、人工介入、验收、可靠性、可用性、权重和区间。
6. **证据如何改变判断**：来源角色、核验状态、反证、缺失值、版本和变更门槛。
7. **限制与证据缺口**：覆盖缺口、选择偏差、厂商自报、基准与现实工作的差距。
8. **社区共建与修订**：如何补充、纠错、归因、保护私有材料和处理争议。
9. **版本与 change log**：本版改变了什么、哪些历史结果不可直接比较、下次更新条件。
10. **技术附件入口**：本体、数据字段、映射、计算、验证、公开数据和复现说明。

## 可直接采用的段落模板

单项进度判断可以统一写成：

> **判断：** 在〔明确工作范围〕与〔模型、工具、环境条件〕下，AI 已能以〔成功率 / 验收结果〕完成〔任务〕，仍需要〔人工介入〕。本次判断主要依据〔独立评估 / 厂商评估 / 真实案例〕；相较上一版改变，是因为〔新增证据〕。该证据不能证明〔外推边界〕。下一次重估需要〔补充样本、反证或新的独立报告〕。

这个模板把传播所需的结论和复核所需的边界放在同一段中，适合用于白皮书摘要、行业页和定期报告。
