# 一期本地入库与计算

本地处理文件 → PostgreSQL → 指标 → 实验进度 → 回查，已实现并在 PostgreSQL 18.6 上运行验证。已支持合成材料回归与本地真实采集档案；真实材料使用独立的证据审阅试算方法，正式能力估计仍未校准。网页尚未连接此数据库。

## 运行

需要 Docker Engine/Desktop、Docker Compose、Python 3.12+、Node.js 22+ 和仓库 pnpm 依赖。

```sh
pnpm install --frozen-lockfile
pnpm data:setup
pnpm data:test
pnpm data:simulate
```

`data:setup` 在根目录 `data/runtime/venv` 创建 Python 环境，安装固定版本 psycopg，启动专用 Compose 项目 `openaiwill-data-local` 并应用迁移。数据库只监听 `127.0.0.1:7543`，库名 `openaiwill_local`；用户名 `openaiwill` 是本地数据库连接账号，不是网站用户。

密码首次生成到 `data/postgres/password`，文件权限 0600；不会写入命令参数、公开环境文件或 Git。数据位于专用 Docker volume。固定镜像 digest 的运行版本已核对为 PostgreSQL 18.6。PG 18 镜像挂载位置采用 `/var/lib/postgresql`，与[官方镜像说明](https://hub.docker.com/_/postgres)一致；Python 驱动采用 [Psycopg 3 binary 安装方式](https://www.psycopg.org/psycopg3/docs/basic/install.html)。

```sh
pnpm data:status
pnpm data:down    # 停止此项目，保留数据库卷
pnpm data:up
pnpm data:migrate
```

`data:up` 启动已有环境；首次使用应运行 `data:setup`。不提供清空历史或删除卷命令。数据库连接程序固定使用上述本地地址；迁移工具不接受远程生产连接串。

## 输入和版本

- [合成输入](../../datasets/simulation/local-v1/baseline.json)包含人物、机构、产品/版本、账号、来源、采集版本、事件、声明、采用、标签、关联及覆盖记录。
- [独立配置](../../datasets/simulation/local-v1/config.json)固定本体、赛道/工作范围、来源平台/账号集合、标签、四种指标规则、实验方法和关系权重。
- [正式迁移](../../db/migrations/001_business_schema.sql)建立 34 张业务表；[封存保护迁移](../../db/migrations/002_immutable_imports.sql)补充 `sealed_at` 和保护触发器；[采用阶段迁移](../../db/migrations/003_integrated_adoption_stage.sql)增加 `integrated`（已接入），与 `integrating`（接入中）、`production`（明确生产使用）区分。阶段本身不决定分值。[语义判断层迁移](../../db/migrations/006_semantic_judgment_layer.sql)建立能力、闸门、判断运行、类型边与实例层证据/状态表，其中所有枚举 CHECK 由语义层生成；[判断者词表迁移](../../db/migrations/007_semantic_judge_vocabulary.sql)把 `judge` 与 `task` 两列也纳入受控词表；[判断项迁移](../../db/migrations/008_judgment_items.sql)保留每一次判断——包括否定与未决，否则两个判断者的对照只看得见一致，看不见分歧的形状；[空值修复迁移](../../db/migrations/009_kind_check_null_repair.sql)修正 006 生成的 CHECK 中`NULL IN (...)` 为 NULL 而非 false 导致约束从未生效的问题；[自主度观测迁移](../../db/migrations/010_observed_autonomy.sql)把「所描述的用法里人还做多少」与「是哪类证据」「来源多可信」分开记录；[闸门状态任务迁移](../../db/migrations/011_gate_state_task.sql)把 `gate_state` 加进判断运行的任务词表，此前闸门状态运行借用 `demonstrates`，导致证据查询把它选中、快照发布出 0 条证据；[能力覆盖面迁移](../../db/migrations/012_capability_breadth.sql)在能力状态上记录 `work_nodes_requiring` 与 `work_nodes_judged` 两个整数——不存比值，比值会和它的来源对不上。另有 `schema_migrations` 记录迁移哈希。
- 本体导入先调用现有封存包语义校验器，再验证实际读入字节哈希；导入完整 20,796 个概念和 20,733 条关系，保留既有 ID。外部参考目录仍由原封存包及其哈希追溯。

导入其他符合当前合同的本地合成处理包：

```sh
pnpm data:import --input=data/my-simulation/input.json --config=data/my-simulation/config.json
```

`local-input-1` 且 `synthetic=true` 保留原合成回归及哈希；真实材料使用 `real-local-input-1`、`synthetic=false` 以及单独的 `real-local-pipeline-1` 引擎版本。两种输入与方法不能混用。真实入口校验已保存的标准化采集档案，并接受明确编写的事件/声明及 AI 判断；尚未实现自动阅读全文提取事件或自动生成能力估计。

输入顶层字段、允许表和方法操作受程序约束；表字段通过正式迁移的列及约束校验。`batch_id`、本体/配置版本、记录哈希由导入器赋值；输入不能直接写入指标和进度表。时间必须带时区，统一为 UTC；相同身份的完全相同记录合并，内容冲突拒绝。关系权重须可精确存为 10 位小数，三情景值须可精确存为 3 位小数，避免数据库隐式舍入改变分母或汇总。来源自然键和采集时点冲突同样拒绝。

来源范围在配置中明确指定平台和账号；合成合同的覆盖记录必须与它们、工作/标签和统计窗口一致。真实合同保留多个原始查询及其窗口，不将部分来源查询重写为完整工作覆盖。缺失覆盖保留 unknown；部分覆盖的正计数是已观察到的部分数量。空输入只有在完整覆盖下才得到零，查询失败或覆盖缺失不生成零。覆盖记录不能宣称已完整查询其检查时间之后的窗口。

## 语义层与判断流

语义层[semantic-model.v2.json](../../datasets/semantic/semantic-model.v2.json)是唯一源头：
SQL 的枚举 CHECK、抽取 prompt、判断 rubric 与站点标签全部由它生成。
`pnpm semantic:build` 产出投影，`pnpm semantic:check` 校验模型本身，
并逐列比对 `db/migrations` 里实际生效的 CHECK 值表与词表是否逐字相等——
它的作用不是发现打字错误，而是保证不存在第二份真相。

```sh
pnpm data:discover:capabilities -- --output data/discovery/caps.json   # 从任务原文推导能力
pnpm data:classify:capabilities -- --input caps.json --output classified.json
pnpm data:seed:semantic                              # 能力、闸门、组织注册表与候选边落库
pnpm data:judge:requires -- --judge typesafe --occupation oaw:occupation:31-9094.00
pnpm data:judge:blocked -- --resume                  # 哪些闸门挡住哪些工作
pnpm data:judge:compare -- --run-a <run> --run-b <run>
pnpm data:judge:demonstrates -- --vocabulary event_kind-2.0.0
pnpm data:gate:state                                 # 有没有立场声明移动了闸门
pnpm data:capability:state                           # 证据 → 自主阶段
pnpm data:review:pending / pnpm data:review:record    # 人工评审
pnpm data:publish:snapshot                           # 网站读取的已发布快照
```

能力集从工作本身推导，不从厂商发布推导：按职业大类分层抽样任务原文，
让模型说出每条任务需要什么能力，**先按跨大类广度筛掉只出现在一个大类的名称**
（那是任务改写不是能力），再合并同义项。分类是独立的一遍——提议阶段问
「这项工作需要什么能力」，模型就会把闸门也说成能力：physical-presence 曾以
14 个职业大类成为覆盖面最广的一条「能力」，而它是最典型的闸门。

判断者可以换：`--judge typesafe` 或 `--judge deepseek`，每条边都记下是谁判的。
两者在 8,857 对重叠判断上一致率 93.8%，但分歧单向——一方比另一方严得多，
所以边不是判断者中立的，快照里按 `judge` 字段区分。

判断者额度会在跑到一半时用尽，这不是假设：一次全量扫描中途返回 HTTP 402，
后续 16,814 次「判断」其实是从未发生的请求。**这类行会被删除而不是记成未决**——
把「请求被拒绝」记成「判断者看过但决定不了」是两回事，后者会污染覆盖率统计。
三个判断运行器都带熔断：连续 3 个批次没有任何一条被判定就中止，而不是继续磨。运行中途失败时，该次运行标记为 `failed` 并在 `params` 里写明原因与被删除的行数；
它在失败前写入的边是有效的，保留。`--resume` 按 `judgment_items` 里已有的记录跳过，
而不是按运行状态，所以崩溃过的运行做过的事仍然算数。

`requires` 边是判断不是匹配：对 18,838 条任务原文做关键词匹配找「软件相关」命中 999 条，
抽样核对其中一个职业的 14 条命中全部是假阳性。因此每条边都带 `method` 与 `status`，
`ai_proposed` 在数据库层被强制只能是 `candidate` 或 `rejected`，且必须指向一次判断运行。

自主阶段由三道互相独立的封顶取最小值：证据的种类（基准证明不了自主性）、
来源的层级（厂商自证最多到 2）、以及所描述用法里人还做多少。
`capability_states.limiting_factor` 记录是哪一道在起作用，
读者因此能分清「能力弱」「证据弱」与「工具够强但人还在盯」。
没有证据的能力不给数字：`insufficient_evidence` 与阶段 0 是两种不同的陈述。

## 真实档案入口

新的官方 X 账号采集入口及覆盖语义见[官方 X 账号采集](official-x-monitoring.md)。它按注册账号读取原生时间线并逐页保存原始响应；当前输出尚未自动接入以下真实档案转换和计算入口。

在现有采集文件基础上执行：

```sh
pnpm data:setup
pnpm data:real --archive=data/collection/2026-09-12-two-weeks/normalized --review=data/real-calculation/2026-09-12/review.json --output=data/real-calculation/2026-09-12/run-v1
```

上述文件是本机已有档案，普通 Git clone 不包含这些原始材料。`--archive` 指向含顶层与日期窗口清单的标准化目录；转换器核对原始文件、JSONL 的哈希/数量、身份引用、发布时间、采集时点、全文与互动快照的一致性，保留原始来源和采集 ID。多个查询覆盖记录分别保留；不将 X 分组搜索变成逐账号完整覆盖，也不把 Reddit 社区写成帖子作者。

`--review` 明确提供批次 ID、生成时间、配置、语义记录及每个工作的三情景判断。判断带事件、当前采集 ID、内容哈希、判断者和理由；不能通过该入口覆盖采集器拥有的来源、采集、身份或覆盖记录。真实入口拒绝宣称已完整取尽这份部分档案。

`--output` 使用与归档分开的根目录 `data/` 子目录，保留规范化输入、原判断、配置、档案清单哈希和数据库查询结果。相同内容可以重放，已有的不同内容文件不能被覆盖。原始归档不改写。首次新口径判断是初始化，不回填过去的能力值。

本次实际结果见[真实数据计算记录](../data/real-data-calculation-2026-09-12.md)；方法及限制见[真实证据试算方法 v1](../data/real-evidence-estimation-pilot-v1.md)。

## 指标和实验进度

| 指标 | 当前口径 |
| --- | --- |
| `comments` | 每次采集的评论字段；缺失为 NULL，明确返回零为 0 |
| `event_count` | 接受关联且携带目标标签、已发生、发生时间在 `[start,end)` 的去重事件；截止前至少存在一条可用来源 |
| `post_count` | 对每个来源选择截止前最新采集，按帖子原发布时间落入窗口、来源标签和工作关联计数；不继承事件发生时间窗口 |
| `comment_sum` | 对上述选中帖子汇总评论；任一字段缺失时总值 NULL，同时保留已知小计和缺失来源数 |
| `archive_post_count` | 真实档案按平台/原帖发布时间窗口统计去重来源，选截止前最新可用采集；属于观察样本数 |
| `archive_comment_sum` | 对同一真实样本汇总最新回复/评论字段，保存缺失数、已知小计、输入与原查询覆盖；不视为历史窗口末的互动值 |

SQL 在数据库中选择事件/来源并聚合观测。计数保存定义、平台/账号集合、标签、窗口、截止时间、输入哈希和行级输入。原始发布时间、采集时间和平台指标更新时间分别记录；未知平台更新时间保持 NULL。

合成实验方法只接受带采用方角色、有效关联、当前可访问来源及合成核验状态的证据，事件计数仅作为覆盖与存在性门槛。示例试点阶段映射 `[10,20,30]`，生产阶段映射 `[60,70,80]`；这是为了检验程序的**任意测试值**，不主张采用阶段能测出独立完成能力。更多同阶段采用或评论上涨不会加分。

当前来源及支持材料均按截止前最新采集检查；新批次发现材料被删除时，不再用其旧可用状态作当前实验依据。旧批次和已保存的历史计算仍保留。对同一工作选合格阶段中央值最大的三情景；全部子工作有值才按关系权重汇总。缺失子项保留未知份额，赛道三值为空，不删除子项后重新归一化。没有世界总分。

真实方法 `reviewed_evidence_scenarios` 保存 AI 对三个工作节点的明确判断，再按固定关系权重加权。证据相关性、身份与事实核验分别保留；评论、事件数、采用阶段均不自动增加分数。未提供判断的子项保持未知，父级不删项重算。判断本身是冻结输入，因此程序复算可复现，重新让 AI 判断不保证得到同一组数字。

## 事务、重放和回查

导入器以事务级 advisory lock 串行化导入；配置、输入、计算和封存一次提交。处理中的 loading 批次仅在本事务内用于计算，全部成功后才成为可查询的 ready 批次。任一步失败整笔回滚，不留下可用的半批结果。

同一批次 ID 与规范化输入/配置/引擎版本哈希相同则复用结果；相同 ID 不同哈希拒绝。更正需要新批次 ID，引用旧批次；旧批次必须已封存且更早。每种方法的 ID + 方法版本不能换算法内容；范围、权重、方法修订分别记录原因，一次只更改一个口径维度。

数据库触发器拒绝已封存批次的追加、改写、删除和 TRUNCATE，也拒绝已封存目录的追加/改写。父记录锁使封存与并发写入相互排斥。本地开发连接是数据库所有者；这些保护防止正常 SQL 误改，不防所有者主动禁用触发器或删除表。未实现生产连接权限部署。

```sh
pnpm data:report sim:new-evidence
pnpm data:psql -- -c "SELECT id, status, config_version FROM data_batches ORDER BY generated_at;"
pnpm data:psql -- -c "SELECT batch_id, concept_id, central, change_cause, previous_batch_id FROM progress_values ORDER BY estimated_at, concept_id;"
```

每次 `data:simulate` 保存独立的 `data/simulation/runs/<UTC时间>/`，内含五批规范化输入、配置、JSON 查询结果和中文 Markdown 报告。全部运行产物保留本地，不进入 Git。

`pnpm data:test` 在独立临时数据库运行真实 PG 回归，测试后只删除本次生成的测试库；`pnpm check` 保留无需 Docker 的网站和静态数据检查，并包含输入单元测试。CI 另执行 setup、真实 PG 测试和模拟。完整验收需两组检查均通过。

## 人工评审

机器提议的边不经人确认不得进入任何结论。评审通道：

```sh
pnpm data:review:pending -- --capability cap:asr-longform --limit 20
pnpm data:review:record -- --file review.json --reviewer "姓名"
```

`review-pending` 按**距离确定性的远近**排序而不是按置信度：判断者最没把握的那些，
才是人的时间最值钱的地方。`review.json` 的形状：

```json
{"decisions": [
  {"edge_kind": "requires", "from": "oaw:task:9413", "to": "cap:asr-longform",
   "decision": "reviewed", "note": "任务原文就是长语音转写"},
  {"edge_kind": "requires", "from": "oaw:task:11275", "to": "cap:domain-text-editing",
   "decision": "rejected", "note": "查的是格式与排版错误，不是术语准确性"}
]}
```

被否决的边保留为 `status='rejected'` 而不是删除，下一轮判断因此不会把同一条边
当作没人看过再提一遍。`decision='rejected'` 不改 `method`——人没有提出这条边，
只是否决了它；只有确认才会把边变成 `method='reviewed'` 的断言。
已决定的边不会被重放的文件悄悄改写，重复评审会被报告而不是覆盖。
