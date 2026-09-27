# 赛道、细分与工作任务：全量参考数据采集

采集日期：2026-09-12。**本轮选用 O*NET® 31.0 作为主要工作任务底库，已完整下载并解析其全部 45 张 CSV 表。** 同时采集 O*NET OnLine 全部 20 个行业索引，以及联合国 ISIC Rev.5 的完整行业结构和逐项说明。

这是本地可用的来源数据包。完整度指选定版本的源表完整，而非已经定义所有商业交付场景。现有 a16z 九行业原表、前端目录和进度分数未被替换。

## 为什么选这套

O*NET 由美国劳工部就业与培训管理局支持，记录职业、具体任务、工作活动及其关系；任务有稳定 ID、所属职业、核心/补充属性、更新时间和资料来源。它覆盖数字工作与实体工作，适合回答“AI 究竟能完成哪些具体工作”。31.0 版于 2026 年 8 月发布，数据库采用 CC BY 4.0。[版本入口](https://www.onetcenter.org/db_releases.html)、[任务字典](https://www.onetcenter.org/dictionary/31.0/csv/task_statements.html)、[许可](https://www.onetcenter.org/license_db.html)

行业细分另取 ISIC Rev.5。它提供国际经济活动分类，以及各类包含、不包含哪些活动的说明，适合约束“赛道”的边界。当前官方页面提供完整结构和说明，正式 UN 出版物仍标为 forthcoming；本包保留具体文件链接和哈希。[UNSD 官方入口](https://unstats.un.org/unsd/classifications/Econ)

未找到一份原生、完整的“行业 → 细分行业 → 带输入和验收条件的交付场景”通行库。当前最实用的选择是采用上述来源底库，再明确场景转换规则。各候选源的版本、下载与使用条件见[来源比较](../research/work-taxonomy-source-comparison-2026-09-12.md)。

## 实际采集规模

以下数量均由本地文件重新计算，不使用搜索摘要的旧版计数。

| 数据 | 已采集数量 | 含义 |
| --- | ---: | --- |
| O*NET 31.0 数据库 | 45 张 CSV 表 | 全量压缩包已保存、逐表解析，并核对 ZIP CRC |
| 职业大类 | 23 | 包含军事职业大类；不是 23 个行业 |
| 职业条目 | 1,016 | 保留原始职业代码、标题与描述 |
| 有任务记录的职业 | 923 | 其余 93 个职业在此源表中没有任务；不补造 |
| 具体工作任务 | 18,838 | 完整任务表，18,838 个唯一 Task ID |
| 通用工作活动 GWA | 41 | 跨职业的活动分类上层 |
| 中层工作活动 IWA | 332 | 每项有唯一上级 GWA |
| 详细工作活动 DWA | 2,087 | 每项有唯一上级 IWA |
| 任务—详细活动关系 | 24,087 | 全部任务均能找到活动关系；一个任务可关联多个活动 |
| O*NET 行业索引 | 20 | 官方网站全部行业选项，完整导出 1,922 行 |
| 可连接的行业—职业关系 | 1,902 | 涉及 992 个不同职业，允许同一职业出现在多个行业 |
| 行业索引待解记录 | 20 | 源 CSV 未给职业代码，单独完整保留 |
| ISIC Rev.5 行业节点 | 830 | 22 个门类 → 87 个大类 → 258 个中类 → 463 个小类 |
| ISIC 分类说明 | 830 行 | 逐码与结构表对应；保留包含、还包括、排除等字段及原始缺值 |

机器清单：[work-reference.v1.json](../../datasets/work-reference.v1.json)。其中记录输出路径、条数和校验值。

## 对我们三级结构的用途

| 产品概念 | 目前可用的来源材料 | 转换边界 |
| --- | --- | --- |
| 赛道 | 原有 a16z 九行业；新增 O*NET 20 行业索引与 ISIC 22 门类参考 | 各自保留来源版本，尚未合并成一个新产品目录 |
| 细分赛道 | ISIC 的 87 大类、258 中类、463 小类，含范围说明 | 可按业务粒度选层级；职业作为关联实体，不直接改名为细分行业 |
| 交付场景 | 18,838 条职业任务、2,087 项详细工作活动 | 可作为场景素材；业务输入、预期交付物、适用条件尚需明确 |

已经存在两套来源内部完整关联：**职业大类 → 职业 → 任务**，以及 **通用工作活动 → 中层工作活动 → 详细工作活动**。两套结构通过任务—活动关系连接。

另有 **行业 ↔ 职业** 的就业关联。它支持按行业发现相关工作，但不能证明某职业的每一项任务都适用于该行业。**ISIC 与 O*NET 之间尚未建立逐项映射，也尚未生成正式交付场景目录。**

## 可直接讨论的真实任务示例

以下中文为 WillAI 翻译，英文原文和稳定 ID 均保存在数据中。这里展示源任务，不表示已确认 AI 能独立完成。

| 所属职业 | Task ID | 原始任务的中文表达 |
| --- | --- | --- |
| 律师 `23-1011.00` | `3774` | 为个人和企业解释法律、判决与法规 |
| 软件开发人员 `15-1252.00` | `21662` | 分析用户需求和软件要求，评估在时间与成本约束下的设计可行性 |
| 会计师与审计师 `13-2011.00` | `21533` | 处理待付款发票 |
| 检验、测试等工作人员 `51-9061.00` | `12480` | 用尺、卡尺、量规或千分尺测量产品尺寸，检查是否符合规格 |
| 人工货物及物料搬运人员 `53-7062.00` | `10781` | 徒手或借助设备，在仓储、生产区域、装卸平台及运输工具之间搬运货物与物料 |

工作活动树中也有明确的三级路径，例如：**分析数据或信息 → 评估法规或政策的特征与影响 → 分析法律或监管变化的影响**。对应原始 ID 为 `4.A.2.a.4` → `4.A.2.a.4.i` → `4.A.2.a.4.i.3`。[官方层级说明](https://www.onetcenter.org/dictionary/31.0/csv/gwas_to_iwas_to_dwas.html)

## 数据入口

完整本地资料包：[README 与文件目录](../../data/reference/work-taxonomy/2026-09-12/README.md)。

| 文件 | 用途 |
| --- | --- |
| [职业](../../data/reference/work-taxonomy/2026-09-12/normalized/occupations.json) | 职业代码、名称、描述、所属职业大类、任务条数 |
| [任务](../../data/reference/work-taxonomy/2026-09-12/normalized/tasks.json) | 全部 18,838 条原始工作任务 |
| [三级工作活动](../../data/reference/work-taxonomy/2026-09-12/normalized/work-activities.json) | 2,460 个活动节点，包含类型和父级 ID |
| [任务与活动关联](../../data/reference/work-taxonomy/2026-09-12/normalized/task-activity-links.json) | 连接职业任务与通用活动树 |
| [行业索引](../../data/reference/work-taxonomy/2026-09-12/normalized/industries.json) | 20 个原始行业及逐项导出来源 |
| [行业与职业关联](../../data/reference/work-taxonomy/2026-09-12/normalized/industry-occupation-links.json) | 1,902 条就业关联 |
| [未解行业记录](../../data/reference/work-taxonomy/2026-09-12/normalized/industry-unresolved-rows.json) | 20 条缺代码记录的原始行和来源位置 |
| [ISIC 全量分类及说明](../../data/reference/work-taxonomy/2026-09-12/normalized/isic-rev5.json) | 完整国际行业树、业务范围与排除项 |

这些文件位于被 Git 忽略的根目录 `data/`，属于本地研究数据。公开候选目录 `datasets/` 仅增加来源元数据清单；未上传网站。

## 数据边界与缺口

- **美国职业资料与国际行业分类口径不同。** O*NET 不能直接代表中国或全球全部工作，也不提供全球行业权重。
- **行业索引有 10% 的收录门槛。** 只有某职业至少 10% 的从业者在该行业任职时，才进入该行业列表。百分比的分母是该职业从业者，不是行业总人数，更不是 AI 完成度。20 份导出齐全，也不等于完整 BLS 行业—职业矩阵。[索引规则](https://www.onetonline.org/help/online/browse_ind)
- **就业统计版本单独保留。** 这批行业索引沿用 BLS 2024–2034 资料，O*NET 官网标注更新于 2025-09-16；不能因为本次抓取日期是 2026-09-12 就标成最新 BLS 2025–2035 数据。细分职业显示的就业比例可能来自上层 SOC 汇总，不能相加为独立份额。[外部来源说明](https://www.onetonline.org/help/online/datasources)
- **93 个职业无任务记录，418 条任务未标 Core/Supplemental。** 前者保留来源覆盖状态，后者保存为 `null`。923 个有任务的职业中，3 个未连接到当前行业索引；这些任务仍保留在任务库中。
- **本轮未取得最新完整 BLS 矩阵及其对照表。** 三个官方 XLSX 的本地下载返回 403；缺口保存在采集清单。NAICS 结构表的实际访问状态见来源比较，不计入已下载数据量。
- **未导入任何能力分数。** 职业任务、工作活动、真实采用和 AI 能力估计分别保存；场景适用性及输入/输出信息未由模型补造。

## 校验与复现

采集脚本：[collect-work-reference.py](../../scripts/collect-work-reference.py)。只使用 Python 标准库；下载后用 SHA-256 验证本地缓存，可离线复建。

```bash
python3 scripts/collect-work-reference.py --batch 2026-09-12 --offline
```

本轮通过 5,829 项数据断言，覆盖全部 CSV 解析、源表条数、ID 唯一性、父级一致性、引用完整性、任务全覆盖、行业原始行完整留存，以及 ISIC 结构/说明一致性。[校验报告](../../data/reference/work-taxonomy/2026-09-12/validation.json)

项目的 `pnpm check` 同样通过；其中原有 `metadata:check` 仍只负责旧页面目录，本轮数据由上述独立校验覆盖。

## 来源署名与转换

职业、任务和工作活动信息来自 **O*NET® 31.0 Database，U.S. Department of Labor, Employment and Training Administration（USDOL/ETA）**，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 整理。O*NET® 是 USDOL/ETA 的商标。WillAI 添加了 ID 命名空间、关系字段和本报告中的中文翻译；这些修改未经 USDOL/ETA 批准、背书或测试。[原始许可说明](https://www.onetcenter.org/license_db.html)

行业就业索引保留 O*NET OnLine 与 BLS 双重来源。它是 O*NET 网站注明的外部数据，不能笼统沿用 O*NET 数据库许可。[BLS 对自身公开数据的说明](https://www.bls.gov/opub/copyright-information.htm)

ISIC 原始 CSV 采用 Windows-1252 解码；Excel 中 `_x000D_` 转为换行，分类代码保留前导零，原始文件字节不改。ISIC 完整内容的对外再分发许可状态未确认，本轮仅保存为本地研究参考。
