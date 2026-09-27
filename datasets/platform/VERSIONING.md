# 数据版本规范

版本格式为 **v主.次.修订**，机器字段不带 `v`。本项目采用 [SemVer 的三段版本和发布后不可改写原则](https://semver.org/lang/zh-CN/)，并将严格升级规则用于 `0.x` 草案。SemVer 允许初始开发阶段更自由地变化；以下是 openaiwill 自己的更严格约定。

| 级别 | 升级示例 | 适用变更 |
| --- | --- | --- |
| 小版本 / patch | `0.0.1 → 0.0.2` | 同一目录合同与同一方法下新增事件、补充指标、更新进度，或不改变结构和方法的来源/普通标签文字修正 |
| 中版本 / minor | `0.0.2 → 0.1.0` | 兼容地增加目录节点/外部映射/可选字段；首次为节点增加 `scope_note`；调整权重值、权重规则或估计方法 |
| 大版本 / major | `0.1.0 → 1.0.0` | 删除或改变节点身份，改写或删除已有范围定义 `scope_note`，改变必填字段或字段类型，改变计分含义等不兼容变化 |

一次包含多种变更时采用最高级别。升级 major 或 minor 后，其右侧数字归零。大版本是兼容性信号，不代表能力成熟度；`1.0.0` 也不自动意味着生产发布。

## 不混淆的版本

- **数据包版本**：一次完整、可追溯的快照，例如 `0.0.1`。
- **格式版本 `schema_version`**：机器字段合同。首版校验器支持 `0.0.1`；合同升级需要同时提供新 Schema 与验证逻辑。
- **来源版本**：例如 O*NET `31.0`、ISIC `5`，不能用本项目版本覆盖。
- **权重方法和估计方法版本**：每条权重、每次估计各自记录，允许查明改变的是证据还是计算方法。

来源/目录/权重/方法改变造成的进度变化，不得伪装成 AI 新能力。进度更新的 `change_cause` 区分 `new_evidence`、`evidence_correction`、`method_revision`、`scope_revision`、`weight_revision`。

`scope_note` 定义节点包含哪些工作，与普通 `label_zh_cn` / `label_en` 显示文字不同。即使节点 ID 没变，改写或删除已有范围说明也按 major 处理；首次补充范围说明至少 minor。仅修正显示标签且不改变范围、身份和方法时可用 patch。

## 每个版本必须包含

1. `version`、`schema_version`、`created_at`、`summary`、`change_types`。
2. `previous_version` 和 `previous_manifest_sha256`；首版两者为 `null`。
3. 来源输入版本/哈希、方法版本及已知缺口。
4. 全部 JSONL、Schema 和说明文件的文件名、字节数、行数与 SHA-256。
5. `manifest.sha256`，保存 `manifest.json` 自身的哈希，避免循环引用。

文件在临时目录完成写入和验证后原子移动到最终版本目录。最终目录已存在时拒绝覆盖；不使用 `--force` 修改旧版本。校验器还会拒绝未列入清单的文件、符号链接、悬空引用、权重总和错误、版本倒退和断裂的前版哈希链。SHA-256 证明所核对文件的完整性，不提供作者身份签名；生产激活和签名发布另行实现。

## 迭代操作

在本地 `data/` 中准备一个完整的候选 bundle JSON：

```json
{
  "previous_version": "0.0.1",
  "schema_version": "0.0.1",
  "change_types": ["event_added", "observation_added", "estimate_updated"],
  "summary": "概述本次新增证据与估计变化",
  "data": { "...": "这里放全部集合，包括未变化的数据；不得用省略号实际运行" },
  "attachments": { "CHANGELOG.md": "具体变更与已知限制" }
}
```

命令自动校验前版、计算版本号、封存和复核。它检查实际前后变化要求的最低级别，不能把权重或目录变化仅标为 `correction` 来偷用小版本。

省略 `source_inputs`、`method_versions`、`unintegrated_inputs` 或 `coverage_summary` 时继承前版。只新增事件且方法未变时，不需要复制方法版本，命令不会把省略字段当成清空。显式提供字段表示替换该字段的完整值，不是逐项合并；`null` 不合法。来源或方法有变化时，应提供更新后的完整清单，方法变化仍须使用 minor 或更高版本。

- `source_inputs` 是输入文件清单，每项必须有非空 `name`、64 位小写十六进制 `sha256` 和非负整数 `bytes`，文件名不得重复；附带的 `version`、`source_version`、`source_id` 必须是非空字符串。
- `unintegrated_inputs` 使用相同的文件字段，并标记 `status: "raw_not_integrated"`。明确提供 `[]` 可清空该清单；省略则保留前版尚未整合的来源。
- `method_versions` 是方法名称到版本字符串或 `null` 的对象；`null` 表示该方法尚未初始化。对象是完整替换值，不应为了表示“未变化”而填写 `{}`。
- `coverage_summary` 中的目录、任务、权重方法、事件、观测和进度数量按候选 `data` 重算。显式提供这些计数时必须与数据一致，否则拒绝封存。说明性缺口可存为 `known_gaps` 字符串数组；省略整个字段时保留旧说明，显式提供时须包含仍然有效的说明。

后续版本使用 `events`、`observations`、`progress_updates` 和 `assessed_progress` 记录当前数量；其中 `assessed_progress` 是按视图计数的非空进度记录数。首版的 `initial_events` / `initial_estimates` 不带入后续摘要，也不接受作为后续版本的显式计数。摘要不能替代完整来源或事件记录。

```sh
pnpm platform:seal --input=data/platform-candidate.json
pnpm platform:check
```

支持的变更分类：

| 分类 | 最低升级 |
| --- | --- |
| `event_added`、`observation_added`、`estimate_updated`、`correction` | patch |
| `catalog_extended`、`mapping_added`、`optional_field_added`、`weight_method_changed`、`weight_values_changed`、`estimate_method_changed` | minor |
| `node_identity_changed`、`required_schema_changed`、`scoring_meaning_changed` | major |

观测与进度更新按记录追加，旧值必须接续前次新值，当前进度必须指向最后一次更新。跨版本已有的 `observations` 和 `progress_updates` 记录不得删除或改写；纠正测量时新增观测时刻和 ID，再追加进度更新。范围调整和方法重算也通过追加记录说明，升级到 major 不能改写旧账。相同指标输入不可反复形成新增量，等价时区写法或改 ID 也不算新观测，估计方法变化必须说明。事件的稳定 `dedup_key` 代表同一次发生事项；同事件多个来源留在 `source_urls`，不拆成多个能力增量。语义上相似却文字不同的新闻仍需要归并审阅，结构校验器不能替代事件语义识别。

旧版本始终保留。网站读取哪个版本、怎样上传/激活/回滚，遵守项目上传批次规则；本轮数据封存不执行上传、部署或生产激活。
