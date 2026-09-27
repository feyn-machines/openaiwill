# 平台元数据 v0.0.1 实施计划

> For agentic workers: 使用 superpowers:subagent-driven-development 执行独立任务；主任务完成集成、文件校验和最终复核。用户已授权构建，不在任务之间请求重复确认。

**Goal:** 构建可追溯、可校验、具备大中小版本规范的首版全量职业与广覆盖赛道数据包。

**Architecture:** 自有目录与外部参考分离；两种浏览视图；父子权重；事件指标到进度的追加记录。发布物是不可覆盖的 JSONL/Schema 快照，既有网页继续使用原数据。

**Tech Stack:** 本地 Python/Node.js、JSONL、JSON Schema 2020-12、SHA-256、node:test。

**Spec:** ../specs/2026-09-12-platform-metadata-v0.0.1-design.md

## Global Constraints

- 职业全量为 23 / 1,016 / 18,838；不得缩成四个领域示例。
- 赛道覆盖检查包含 ISIC Rev.5 全部 22 个门类，编辑标签与官方分类分别记录。
- 初始能力进度为空；权重可为 AI 提议或有说明的来源推导；二者不混用。
- 不覆盖历史版本，不纳入凭据、原始社交响应、未获准再分发的第三方原件。
- 工作目录已有大量无关修改，不暂存或提交他人的变更；按本次新增文件与精确小段修改集成。

## Task 1: 全领域赛道与职业中文名

- [x] 创建 datasets/platform/source/markets.v0.0.1.json：自有稳定 slug、中文名、英文名、范围、子层级、AI 权重理由、外部门类引用与完整覆盖说明。
- [x] 创建 datasets/platform/source/occupation-labels.zh-CN.v0.0.1.json：恰好全部 1,016 个源职业代码，AI 中文翻译和原始英文保留。
- [x] 运行 JSON 解析、唯一 ID、全量代码对应、同级份额、覆盖检查，并人工复核游戏/法律/实体产业细分。

## Task 2: 合同与行为校验

- [x] 先写 scripts/tests/platform-data.test.mjs，验证共享节点、多对多映射、权重归一、空值、环/悬空引用、版本升级、哈希篡改和拒绝覆盖。
- [x] 运行 node --test scripts/tests/platform-data.test.mjs，确认缺实现导致失败。
- [x] 实现 scripts/lib/platform-data.mjs 与 scripts/check-platform-data.mjs，提供 validateData、aggregateProgress、nextVersion、sealRelease、verifyRelease。
- [x] 写 JSON Schema 2020-12 并接入真实校验；用同一批行为测试验证实现。

## Task 3: 全量生成与封存

- [x] 实现 scripts/build-platform-metadata.mjs：读取本地已核对原始参考，导入全部职业/任务/评级，生成源身份与文件指纹。
- [x] 重要性归一化每个职业的任务权重；没有可用重要性时使用明确记录的均值或等分回退。
- [x] 集成全领域赛道树，保存候选外部关联；生成空事件/观测/更新集合和未知进度。
- [x] 生成中文目录预览、覆盖报告、变更记录和 manifest，校验后原子封存 v0.0.1。

## Task 4: 规范、集成与交付

- [x] 创建 datasets/platform/README.md 和 VERSIONING.md，写出 v0.0.2 / v0.1.0 / v1.0.0 的触发例子与重建命令。
- [x] 更新 CONTEXT.md 中已确认术语、CLAUDE.md 入口及旧 spec 的替代说明，保留旧文审计轨迹。
- [x] 接入 package.json 的 platform:check / platform:test，并运行 pnpm check。
- [x] 核查数据清单、来源/中文覆盖、真实权重、未知进度与哈希；独立复核本次新增实现。
- [x] 打开首版 README，让用户可以直接审阅目录与版本规则。

## 完成证据

- 已封存 `datasets/platform/releases/v0.0.1`：40 / 265 / 614 赛道树、23 / 1,016 / 18,838 职业树；共 20,796 节点、20,733 条父子关系，初始进度全部为空。
- 22/22 ISIC 门类的覆盖说明与领域映射双向一致。O*NET 原始参考逐项通过 Schema，全量职业代码及英文与中文翻译文件一致。
- 首版与独立候选重建的全部 22 个载荷文件哈希一致；构建时刻不同导致 manifest 自身哈希不同，未覆盖任何已封存版本。
- 首版 manifest SHA-256：`dc21d69c326a755d3cb79e63c4414788499710436cfaceb429ecee606c878f64`。
- `pnpm check` 通过：公开候选扫描、8项安全回归、旧目录验证、38项平台回归、快照校验、设计检查、lint、类型检查及生产构建。
- 独立目录语义复核及代码复核完成；修复版本级别低报、重复输入、跨版历史改写、观测时区去重及CLI元数据丢失。最终局部复核未发现新增关键问题。
- 范围决定：沿用用户当前共享目录并只集成本任务文件，保留已有变更；`scope_note`作为节点范围定义，改写已有定义按major，标签文字修订仍可patch。
- 边界：本地草案，网页未接入；赛道中文及权重是AI初稿，职业任务中文待补；BLS原工作簿尚未应用，无自动估计器及初始能力数字。
