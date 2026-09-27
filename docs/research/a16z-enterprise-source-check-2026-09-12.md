# a16z 企业 AI 采用报告：原始清单核验

核验日期：2026-09-12。只核对指定报告及其官方原图；不新增或重组分类。

## 来源身份

- 原文：[Where Enterprises are Actually Adopting AI](https://a16z.com/where-enterprises-are-actually-adopting-ai/)
- 作者：Kimberly Tan；页面发布日期：2026-04-08。
- 数据性质：a16z 企业采用与初创企业收入分析，另引用 GDPval 模型能力结果。
- 可获取内容：公开文章与 5 张原图。本页未提供完整底层企业样本、逐家公司收入数据或分类 CSV 下载。

## 核验结论

**可以完整照录某一张原图的分类，但不能称这篇文章发布了一套统一、完整的行业分类。** 文中的不同图使用不同清单、数量和标签。若第一版采用本来源，必须固定具体图名、版本日期和原始标签，不把各图拼接成自定义分类。

### 1. 产品市场匹配图：6 项，原图自带两组

图名：**Where Enterprise AI Has Product-Market Fit**。

| 原分组 | 完整原始标签，按图中从左到右顺序 |
| --- | --- |
| Use Cases | Code; Support; Search |
| Industries | Tech; Legal; Healthcare |

这是原图的完整 6 项，两个分组也是源图已有结构。正文分别使用 Coding 和 Technology；若以图为数据源，应保留图上的 Code 和 Tech，不静默替换。[官方原图](https://d1lamhf6l6yk6d.cloudfront.net/uploads/2026/04/Where-Enterprise-AI-Has-Product-Market-Fit-r4.png)

### 2. 收入图：10 项

图名：**Where the Money’s Flowing in Enterprise AI**。指标为年化收入，单位百万美元。以下按横轴从左到右完整照录：

| 序号 | 原始标签 |
| --- | --- |
| 1 | Accounting |
| 2 | Nursing |
| 3 | Financial/Investment Analysts |
| 4 | Real Estate |
| 5 | Writing/Editing |
| 6 | Search |
| 7 | Medical/Health Admin |
| 8 | Support |
| 9 | Legal |
| 10 | Coding |

原图的收入数值经过取整。类别同时包含职业、用途和领域，不宜统一改称“10 个行业”。[官方原图](https://d1lamhf6l6yk6d.cloudfront.net/uploads/2026/04/Where-the-Moneys-Flowing-r6.png)

### 3. 能力与收入散点图：11 项

图名：**What’s Working in Enterprise AI**。横轴为模型相对人类专家的胜率，纵轴为初创企业收入合计。原图的全部点标签为：

`Accounting`、`Coding`、`Compliance`、`Finance`、`Legal`、`Medical/Health Admin`、`Nursing`、`Real Estate`、`Search`、`Support`、`Writing/Editing`。

以上为便于核对按字母排列，散点图本身没有清单排名。与收入图相比，散点图多出 Compliance，且使用 Finance，不能未经说明就与 Financial/Investment Analysts 合并。[官方原图](https://d1lamhf6l6yk6d.cloudfront.net/uploads/2026/04/Whats-Working-in-Enterprise-AI-r6.png)

### 4. GDPval 能力变化图：9 个分组，44 个可见职业条目

图名：**The Models Are Improving Quickly But Unevenly**。原图比较 2025 年 9 月与 2026 年 4 月的模型胜率。以下只登记原行业分组和可见职业条目数，不将其混入采用分类：

| 原图分组，按从上到下顺序 | 可见职业条目数 |
| --- | ---: |
| Real Estate and Rental and Leasing | 5 |
| Manufacturing | 5 |
| Professional, Scientific, and Technical Services | 5 |
| Government | 5 |
| Health Care and Social Assistance | 5 |
| Finance and Insurance | 5 |
| Retail Trade | 4 |
| Wholesale Trade | 5 |
| Information | 5 |
| 合计 | 44 |

这里的 44 是对本张公开原图的逐组计数，不是对 GDPval 完整数据集规模的声明；不能为凑齐其他来源的数量自行补职业。该图属于任务能力基准，不是企业采用率，也不是职业被替代的比例。[官方原图](https://d1lamhf6l6yk6d.cloudfront.net/uploads/2026/04/The-Models-are-Improving-Fast-v3-scaled.png)

### 5. 企业采用率图：两个企业榜单总体

图名：**Enterprise AI Startup Penetration**。图中为 Fortune 500 的 29% 与 Global 2000 的 18.5%；正文将后一数字近似表述为约 19%。这是榜单总体采用率，不是行业分类。[官方原图](https://d1lamhf6l6yk6d.cloudfront.net/uploads/2026/04/Fortune-500-Adoption-r5.png)

## 样本与解释边界

原文统计的采用要求企业已签署组织级合同、试点转化并正式上线付费。资料来自参与初创企业提供的私有数据、公开资料及匿名化访谈分析；页面没有披露精确初创企业样本量或统一观测截止日。收入分析聚焦独立企业 AI 初创公司，排除长尾、部分成熟厂商及模型公司的内含收入，以及以消费者或专业个人用户为主的业务。因此它不能代表整个企业 AI 市场的完整收入或分类覆盖。[原文方法与分析说明](https://a16z.com/where-enterprises-are-actually-adopting-ai/)

## 第一版的可追溯要求

- 每份清单单独保留 `source_url`、`chart_url`、`source_published_at=2026-04-08`、`verified_at=2026-09-12`、图名和原始标签。
- 中文译名只能是展示字段；原始英文名及原图分组应保留。
- 不跨图补项、删项或合并同义词；不要把这份报告标为 a16z 消费应用榜单或企业 AI 支出 Top 50。
- 已核验的是公开原图的条目完整性；底层企业数据的可复现性尚不具备。
