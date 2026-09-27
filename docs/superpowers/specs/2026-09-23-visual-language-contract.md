# 视觉语言契约（所有页面）

状态：执行中　日期：2026-09-23

已确认方向是**技术制图**，不是深色仪表盘。参考（必须先看）：
`design/reference/tensorlake-2026-09-12/user-reference/confirmed-direction.png`
`design/reference/tensorlake-2026-09-12/previews/06-stats-2160p.jpg`

## 一、只用共享组件

`src/components/blueprint.tsx`：`Head` `Stat` `Block` `Bar`，样式在 `blueprint.module.css`。
**不要新建自己的区块头、数字字号或说明块。** 需要新图元时先加到 blueprint，再用。

```
■ LABEL ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ [ TAG ]      ← Head
6 / 100   │ 两行等宽小字                  ← Stat
```

## 二、文案

**一句话。** 每个区块最多一行 `lead`，绝不写两段灰色说明。图表自己解释自己。

- 坏：「按证据触及的深度排序。右侧没有任何读数的赛道，是采集到的更新里没有一条谈到它；这是关于采集的陈述，不是关于这份工作的陈述。」
- 好：「赛道是空的，只说明没采集到它。」

英文同样规则。产品语言不是说明文；读者第一次看到就要懂。

术语一律从快照读，不在组件里写死：`progress.levels` / `progress.level_definitions`。
`pnpm semantic:check` 会拦截把梯级文案抄进 `src/` 的行为。

## 三、数字

- 一页至少有一个 `Stat`，用 `--ah-text-data` 档。表格不是首要表达。
- 等宽 + `tabular-nums`，单位单独一格。
- 0 和缺失不同：实测 0 写 `0`；未采集写 `—` 并说明原因（用 `Missing`）。
- 「为空即结论」的 0 用 `tone="correction"`。

## 四、颜色

`--ah-*` 语义变量，禁止新增同义色。绿色 `signal` 是数据；`action` 是当前选中；
`correction` 是「空本身是结论」；`warning` 是封顶/受限。颜色不单独表达状态，必须配文字或形状。

## 五、验收（子 agent 自查）

1. `pnpm typecheck` 通过。
2. **截图自己看**：
   ```
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
     --screenshot=out.png --window-size=1440,1400 --hide-scrollbars "http://localhost:PORT/路径?lang=zh-CN"
   ```
   中英各一张。看不到就等于没做。
3. 站内链接只能指向真实路由（`typedRoutes` 已开，假链接会 typecheck 失败）。
   现存路由：`/` `/markets` `/markets/[id]` `/occupations` `/occupations/[code]`
   `/occupations/g/[id]` `/updates` `/whitepaper`。**`/about` 已删除，不要链接。**
4. 客户端组件不得 import `@/lib/snapshot`（它读 `node:fs`，会炸构建）。
   纯工具放 `@/lib/anchors`、`@/components/work-grid-shape`。

---

# 六、每个模块必须有的四件事（2026-09-23 用户补充）

换皮不算完成。**每个模块都要增加展示、交互、动效和主题**。逐条对照：

## 6.1 展示密度

每个模块至少要有**一个图**，不能只有表。表是兜底，不是主要表达。
可用：`Bar`（共享）、`WorkGrid` 百格、`ProgressCompare` 小倍数、时间轴、分布直方图。
一个模块如果只有「标题 + 一句话 + 表格」，视为未完成。

## 6.2 操作

列表页**必须**有：
- **搜索**（输入即筛，不要提交按钮）
- **筛选**（按组 / 按状态 / 按有无读数）
- **排序**（至少两个可切换的维度，当前排序要可见）

详情页**必须**有：
- **展开**（点一行看它下一层：任务 → 覆盖它的活动；活动 → 它的读数）
- 当前选中/锚定状态可见

交互一律用真实控件：`<button>` 做动作，`<a>`/`<Link>` 做跳转，输入框有 `<label>`。
键盘可达，焦点可见（`--ah-color-focus`）。

## 6.3 动效

- 进入播一次，向上滚不回放。用 `src/components/home/reveal.tsx` 的 `useSeen` / `Screen`。
- 时长只取 token：`--ah-motion-feedback/transition/reveal/sequence` + `--ah-ease-out`。
- 筛选和排序后，行要有位置或透明度过渡，不要瞬变。
- `prefers-reduced-motion` 下全部呈现为终态。**内容先于动画存在**：关掉 JS 页面依然完整。

## 6.4 主题（这个模块到底在讲什么）

每个模块要有一个**能一句话说清的主张**，并且页面上看得见它：

| 页面 | 主题 |
| --- | --- |
| `/occupations` | 找到你自己的职业——所以搜索是主操作，不是装饰 |
| `/occupations/[code]` | 你这份工作里，AI 碰过哪几件、还有哪几件没人看过 |
| `/occupations/g/[id]` | 这个领域内部差距有多大 |
| `/markets` | 证据真正落在哪些工作上，以及绝大多数赛道是空的 |
| `/markets/[id]` | 这个赛道的每条活动到了第几级，凭哪条更新 |
| `/updates` | 读了 581 条，只有 256 条落到工作上；而且来源严重偏斜 |

主张要用数字表达（`Stat`），不要只写成句子。

## 6.5 文案

- 每个区块最多一行 lead。
- 术语必须自解释：读者第一次看到「L2」就要知道是什么，标签从 `progress.levels` 读。
- 空状态要说**为什么空**，不是「暂无数据」。
