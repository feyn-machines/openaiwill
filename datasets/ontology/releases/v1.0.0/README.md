# openaiwill 本体 v1.0.0

本地本体草案；结构版本不表示语义已穷尽或已生产发布。

- 职业：23 个大类、1016 个职业、18838 条任务。
- 赛道：40 个领域、265 个赛道、614 项工作。
- 共 20796 个概念、20733 条有类型的关系；沿用全部原有 ID。

## 阅读顺序

1. [model.json](model.json)：五种概念与四种关系的定义。
2. [schema.json](schema.json)：标准 JSON Schema 2020-12。
3. [赛道目录](market-catalog.md)与[职业及全部任务目录](occupation-catalog.md)。
4. [覆盖与定义缺口](coverage-report.json)。

概念在 concepts.jsonl，父子关联在 relations.jsonl，外部映射在 external_mappings.jsonl；reference_* 是来源定义和代码引用。指标、事件、进度值和权重不属于本包。

本包由 platform/v0.0.1 提取，原包保留。manifest.json 记录来源根哈希及所有文件哈希；manifest.sha256 用于完整性检查，不是身份签名。

O*NET 来源采用 CC BY 4.0；中文职业译名和编辑目录为改编/自有草案。ISIC 仅含代码和层级。详情见 sources.jsonl。
