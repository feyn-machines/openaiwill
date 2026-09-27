# “赛道 → 细分赛道 → 交付场景”通行数据来源核查

核查日期：2026-09-12。状态：来源研究与采集建议，不替换已冻结的 a16z 九行业参考，不初始化行业权重或能力分数。

## 结论与推荐

本轮核查的官方来源中，**没有发现一份同时提供完整行业树、完整细分行业、以及带输入/产出/验收条件的全行业交付场景库**。这是基于下述来源覆盖的研究判断，不是对所有可能数据库的穷尽证明。

本轮实际选择 **O*NET 31.0 工作内容底库 + O*NET OnLine 行业索引**，同时采集 ISIC Rev.5 完整行业树与说明作为细分参考。NAICS 2022 适合作为后续美国行业对照，GDPval 可补具有交付物的任务样本，ESCO 可补欧洲职业与技能口径。这样“完整”首先有可验证的含义：完整导入选定版本的源表，再明确哪些映射、交付条件仍待补充。已采集内容、数量和本地入口见[实际采集报告](../data/work-reference-collection-2026-09-12.md)。

**职业不是细分行业，技能/任务描述也不自动等于可验收场景。** 产品可以保留三级浏览体验，但底层应分别保存行业、职业、任务、场景及关系；不能通过改列名把外部数据伪装成原生三级标准。行业—职业关系也不等于行业—交付场景关系，不能把一个职业所有任务机械复制到其出现的每个行业。

## 来源比较

| 来源 | 官方版本、覆盖 | 可提供的层 | 下载与用途判断 |
| --- | --- | --- | --- |
| UN ISIC Rev.4 | 21 个 section、88 个 division、238 个 group、419 个 class；本轮读取官方结构文件复算，共 766 个节点 | 完整国际经济活动分类树 | 官方 TXT/CSV、PDF、Access；可作全球行业对照，交付场景需另建。[下载目录](https://unstats.un.org/unsd/classifications/Econ) |
| UN ISIC Rev.5 | 22 / 87 / 258 / 463，共 830 个节点；官网仍注明正式 UN publication 即将出版，结构与说明已提供 | 较新的完整国际行业树 | CSV 与 Excel 均有官方入口；应记录文件版本和“出版物尚待正式出版”的状态。[官方导言](https://unstats.un.org/unsd/classifications/Econ/Download/In%20Text/ISIC5_Intro_11Mar2024.pdf) |
| NAICS United States 2022 | 20 个 sector、96 个 subsector、308 个 industry group、689 个五位行业、1,012 个六位美国行业 | 完整北美/美国行业树；最细层有国家差异 | 官方 XLSX 与手册；适合与美国劳动数据衔接。不是全球行业目录。官网已开展 2027 修订意见征集，本轮选定完整 2022 版。[官方层级计数](https://www.census.gov/naics/federal_register_notices/notices/OMB_FRDOC_0001-0388.pdf)、[NAICS 首页](https://www.census.gov/naics/) |
| ESCO v1.2.1 | 2025-12-10 更新；官方描述 3,039 个职业、13,939 项技能，28 种语言 | 职业、技能及其关系；可补欧洲口径 | CSV、ODS、RDF、TTL、XML、JSON-LD 与 API。标准下载流程要求填写邮箱接收链接；本轮未提交个人信息或下载完整包。[官方简介](https://esco.ec.europa.eu/en/about-esco/what-esco)、[版本说明](https://esco.ec.europa.eu/en/about-esco/escopedia/escopedia/esco-v121)、[下载流程](https://esco.ec.europa.eu/en/use-esco/download) |
| APQC Cross-Industry PCF 8.0 | 2026-02-27 发布；企业流程分类，有跨行业版和行业专版 | 流程类别、流程及活动；并非行业树 | Excel/PDF 存在，但公开下载页面要求姓名、组织邮箱、行业与 CAPTCHA；官方也说明框架并不穷尽某组织所有流程。本轮只核查来源和条款，不采集正文。[8.0 页面](https://www.apqc.org/resource-library/resource-listing/apqc-process-classification-framework-pcf-cross-industry-excel-12)、[FAQ](https://www.apqc.org/process-frameworks/pcf-faqs) |
| OpenAI GDPval | 完整研究集 1,320 项任务；公开 gold 子集 220 项，覆盖 44 个职业和 9 个行业 | 明确的知识工作任务与交付物样本 | Hugging Face 有公开数据与参考文件；不可称已拿到全部 1,320 项，更不可称全行业交付场景目录。[官方说明](https://openai.com/index/gdpval/)、[官方数据集](https://huggingface.co/datasets/openai/gdpval) |

O*NET 31.0 的全量采集与 BLS 行业—职业表核查由同轮采集工作单独记录；此处不重复下载或写入未经实读的数量。其数据库内容有明确的 CC BY 4.0 许可，是优先使用的原因之一。[O*NET 31.0 数据库许可](https://www.onetcenter.org/license_db.html)

## 机器文件入口与实际访问结果

以下“成功读取”仅描述本研究工具的 HTTP 与解析结果，不代表已发布或已在本报告旁保存完整原件。

| 官方文件 | 本轮结果 | 采集注意点 |
| --- | --- | --- |
| [ISIC Rev.4 完整结构 TXT](https://unstats.un.org/unsd/classifications/Econ/Download/In%20Text/ISIC_Rev_4_english_structure.Txt) | HTTP 200，40,195 bytes，766 条数据行 | 实际为逗号分隔；UTF-8 可解码；代码必须保存为字符串以保留前导零 |
| [ISIC Rev.5 完整结构 CSV](https://unstats.un.org/unsd/classifications/Econ/Download/In%20Text/ISIC_Rev_5_english_structure.csv) | HTTP 200，45,481 bytes，830 条数据行 | 不是纯 UTF-8，含 `0xA0`；本轮用 Windows-1252 解码计数，需保留原始字节与转换说明 |
| [ISIC Rev.5 结构与说明 Excel](https://unstats.un.org/unsd/classifications/Econ/Download/In%20Text/ISIC5_Exp_Notes_11Mar2024.xlsx) | 官方页面列出，未在本研究分工中读取工作簿 | 文件名含 2024-03-11；不可把“下载日期”当源版本日期 |
| [ISIC Rev.4 → Rev.5 对照表](https://unstats.un.org/unsd/classifications/Econ/tables/ISIC/ISIC_Rev4_to_ISIC_Rev5_Correspondence_Table-17Jan2025.xlsx) | 官方页面列出，未实读行数 | 保留拆分、合并和部分对应，不假定一对一 |
| [NAICS 2022 完整结构 XLSX](https://www.census.gov/naics/2022NAICS/2022_NAICS_Structure.xlsx) | 官方链接已验证；网页检索器识别 XLSX，但本轮 urllib 返回 HTTP 403 | 文件存在与本地采集成功是两件事；不能记录为成功下载 |
| [ESCO → NACE Rev.2.1 对照表](https://esco.ec.europa.eu/system/files/2026-02/ESCO-NACE%20rev.%202.1%20crosswalk.xlsx) | 官方网页实际链接已提取，未实读工作簿 | 可作为欧洲行业—职业桥；关系不是测得的就业数量或权重 |
| [O*NET → ESCO 职业对照 CSV](https://esco.ec.europa.eu/system/files/2023-08/ONET_%28Occupations%29_0_updated.csv) | 官方网页实际链接已提取，未重复采集 | 文件路径年份不保证与最新两端版本兼容，必须读技术报告和表内版本 |
| [GDPval README](https://huggingface.co/datasets/openai/gdpval/raw/main/README.md) | HTTP 200，读取 1,477 bytes；仓库根目录 API 也可读取 | 当前 README 未标数据许可证；根目录未列 `LICENSE`，此观察不能扩展成不存在任何其他权利说明 |

上述 ISIC 文件入口均来自 [UNSD 下载页](https://unstats.un.org/unsd/classifications/Econ)，两份 ESCO crosswalk 均来自 [欧委会官方 Crosswalks 页](https://esco.ec.europa.eu/en/use-esco/other-crosswalks)。该页明确说明对照研究采用 AI 技术并进行评估；即使由官方发布，也需要保留映射方法与误差边界。

## 可用授权记录

这里只记录已读官方说明与本轮数据处理选择，不作法律判断。公开可访问、免费获取、允许重新发布是不同状态。

| 来源 | 官方说明 | 本轮处理选择 |
| --- | --- | --- |
| O*NET 31.0 数据库 | CC BY 4.0；要求注明数据库版本、USDOL/ETA 来源、许可链接和修改；其他工具/网站内容可能另有许可。[原文](https://www.onetcenter.org/license_db.html) | 可按该许可整理数据库文件；中文翻译、归类和场景补充标为 WillAI 修改 |
| Census / NAICS | Census DS027 说明：本机构员工创作的数据/作品通常不受美国版权保护，境外可能不同，外部人员创作内容也可能另有权利。[DS027，第 9 页](https://www2.census.gov/foia/ds_policies/ds027.pdf) | 记录官方来源和版本；不把这条有限说明扩写为“所有第三方内容全球任意使用” |
| ISIC / UN | 下载页面未发现明确针对 ISIC 结构文件的开放许可；其页脚链接的 UN 通用条款只授个人非商业下载使用，未授再分发或衍生作品一般权利。[UN Terms](https://www.un.org/en/about-us/terms-of-use) | 作为本地来源研究参考；完整外部发布的许可状态保留未确认，不擅自写成 CC BY |
| ESCO 数据 | ESCO 链接到欧委会法律声明：除另有注明，EU 所有内容适用 CC BY 4.0，需归属和标明改动。[法律声明](https://commission.europa.eu/legal-notice_en) | 可作为开放数据候选，仍记录具体下载包声明；不把 API 软件的 EUPL 1.2 误写为数据许可。[API 软件许可](https://esco.ec.europa.eu/en/use-esco/use-esco-services-api) |
| APQC PCF | 当前 Terms 限定内部流程改善用途；未经适用协议不得公开展示/再分发，并列明禁止自动脚本下载、用于创建/训练/测试 AI 系统。[Terms](https://www.apqc.org/terms-of-service) | 不纳入本轮自动采集或对外数据包，仅保留来源比较；本轮没有提交表单或申请协议 |
| GDPval | 官方称公开 gold 子集；当前 README 与根目录未检出明确的通用数据许可证，并含第三方参考说明。[数据说明](https://huggingface.co/datasets/openai/gdpval/blob/main/README.md) | 可保存研究来源、任务 ID 与本地研究材料；完整内容再分发状态留未确认，不自行补 MIT/CC BY |

## 映射限制与交付场景的缺口

下面是基于源结构的实施判断：

1. **行业版本不能混接。** ISIC Rev.4、Rev.5，NAICS 2017、2022，NACE Rev.2、Rev.2.1 应分别带版本。UN 当前页面列出的美国 NAICS 对照包含 2017 等旧版本，不能直接宣称已取得 NAICS 2022 → ISIC Rev.5 官方对应。
2. **九个 a16z 行业维持原貌。** 其 Government 不能无说明直接替换为某行业标准中的 Public Administration；来源树与产品映射分开保存，映射状态可以是候选、部分对应或待复核。现有九行业不是全球行业分母，见项目的 [来源基线](../data/a16z-source-baseline-v1.md)。
3. **任务原文先完整保留，场景另建。** 每个交付场景还需确定使用者、业务触发、输入、预期交付物、质量/时效条件、人工介入和物理环境。源表没给这些条件时保持缺失，不以 AI 自动补写冒充原始数据。
4. **来源完整度和产品完成度分别统计。** 可报告“完整读入某版源表 N 条”“已映射多少关系”“已定义多少可验收场景”；不能把导入任务条数当成覆盖全球工作的百分比，也不能把 GDPval 胜率当成行业自主完成度。

本轮选择的实践顺序是：完整采集可复用的工作底库与行业源表，冻结来源版本，保留原始分类；再建立明确标注的关系和场景记录。没有为凑齐三级而将职业、技能或流程名称重命名成细分行业/交付场景。
