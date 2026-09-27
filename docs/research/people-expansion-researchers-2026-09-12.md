# AI 研究者 X 账号清单补充（2026-09-12）

按最新要求，先找现成公开名单，再补少量关键个人官网链路。此文件保留最初指定的 18 人；主任务合并更大名单。它不是 X 账号存活或身份认证报告。

共 18 人：官网关联 7 人，公开名单候选 6 人，账号未知 5 人；13 人有候选 handle。全部 `enabled:false`、`x_user_id:null`。

## 可复用的现成清单

- [Awesome AI X Influencers](https://github.com/codeman008/awesome-ai-x-influencers/blob/main/README.md)：研究者、公司人物、工程和机器人等分类。
- [Follow the AI Leaders](https://github.com/mattnigh/follow-the-ai-leaders/blob/main/README.md)：研究、安全、教育等人物分类，含 X 出站链接。
- [AI Engineer Handbook](https://github.com/DataExpert-io/ai-engineer-handbook/blob/main/README.md)：Social Media Accounts 下有 X 人物表。
- [Awesome Tech Twitter Accounts](https://github.com/shanmukh05/awesome-tech-twitter-accounts)：ML/AI Research 分类；机器人部分也含机构，合并时须过滤。
- [Prometheans 100+](https://prometheusroot.com/prometheans-100/)：本轮页面自报 153 人，支持 Researcher / Robotics 等分类；目录身份和现职描述仍只是目录说法。

## 18 人结果

| 人物 | 候选 handle | 关联层级 | 证据 |
|---|---|---|---|
| Andrej Karpathy | @karpathy | 官网直接关联 | [来源](https://karpathy.ai/) |
| Yann LeCun | @ylecun | 清单候选 | [来源](https://github.com/codeman008/awesome-ai-x-influencers/blob/main/README.md#L41) |
| Andrew Ng | @AndrewYNg | 清单候选 | [来源](https://github.com/codeman008/awesome-ai-x-influencers/blob/main/README.md#L66) |
| Yoshua Bengio | @Yoshua_Bengio | 官网直接关联 | [来源](https://yoshuabengio.org/en) |
| Geoffrey Hinton | @geoffreyhinton | 清单候选 | [来源](https://github.com/codeman008/awesome-ai-x-influencers/blob/main/README.md#L43) |
| Fei-Fei Li | @drfeifei | 清单候选 | [来源](https://github.com/codeman008/awesome-ai-x-influencers/blob/main/README.md#L67) |
| Daphne Koller | unknown | unknown | [来源](https://ai.stanford.edu/~koller/) |
| Pieter Abbeel | unknown | unknown | [来源](https://people.eecs.berkeley.edu/~pabbeel/) |
| Sergey Levine | @svlevine | 官网直接关联 | [来源](https://people.eecs.berkeley.edu/~svlevine/) |
| Chelsea Finn | @chelseabfinn | 官网直接关联 | [来源](https://ai.stanford.edu/~cbfinn/) |
| Percy Liang | unknown | unknown | [来源](https://cs.stanford.edu/~pliang/) |
| Christopher Manning | @chrmanning | 官网直接关联 | [来源](https://nlp.stanford.edu/~manning/) |
| François Chollet | @fchollet | 清单候选 | [来源](https://github.com/codeman008/awesome-ai-x-influencers/blob/main/README.md#L45) |
| David Ha | @hardmaru | 清单候选 | [来源](https://github.com/mattnigh/follow-the-ai-leaders/blob/main/README.md#L281) |
| Richard Sutton | unknown | unknown | [来源](http://incompleteideas.net/) |
| Jim Fan | @DrJimFan | 官网直接关联 | [来源](https://jimfan.me/) |
| Yuke Zhu | @yukez | 官网直接关联 | [来源](https://www.cs.utexas.edu/~yukez/) |
| Kaiming He | unknown | unknown | [来源](https://people.csail.mit.edu/kaiming/) |

## 合并时保留的区别

- Bengio 官网导航与 Person sameAs 都指向 `@Yoshua_Bengio`。官网另列 `@Mila_Quebec` 机构账号，不能混用。[官网](https://yoshuabengio.org/en)
- Jim Fan 个人主页指向 `@DrJimFan`；codeman 名单的机器人部分写 `@JimFan`。采用官网实际链接。[个人主页](https://jimfan.me/) · [冲突清单行](https://github.com/codeman008/awesome-ai-x-influencers/blob/main/README.md#L127)
- Percy Liang 主页提取到的 X 链接属于学生 Ahmed Ahmed；不能把 `@AhmedSQRD` 关联到 Percy Liang。[主页](https://cs.stanford.edu/~pliang/)
- Manning 的个人账号来自联系表中的 `@chrmanning`；主页另有 Stanford NLP 和论文获奖推文链接。[主页](https://nlp.stanford.edu/~manning/)
- Yuke Zhu 的大学个人地址跳转至姓名匹配的个人主页，后者链接 `@yukez`。[大学页](https://www.cs.utexas.edu/~yukez/) · [个人页](https://yukezhu.me)
- David Ha 保留 `@hardmaru` 候选。博客确有 hardmaru 链接，但本轮没有补齐姓名与博客的一手关联，所以仍标清单候选。[博客](https://blog.otoro.net/) · [研究者清单](https://github.com/mattnigh/follow-the-ai-leaders/blob/main/README.md#L281)
- 额外发现清单文字与链接不一致：mattnigh 中 Chris Olah 的显示文字是 `@ChrisOlah`，实际 href 是 `/ch402`；DataExpert 中 Sebastian Raschka 的显示文字拼错，实际 href 是 `/rasbt`。批量导入应提取 href，保留冲突待核，不应只抄显示文字。[mattnigh](https://github.com/mattnigh/follow-the-ai-leaders/blob/main/README.md#L274) · [DataExpert](https://github.com/DataExpert-io/ai-engineer-handbook/blob/main/README.md#L224)

## 字段与限制

`identity_evidence.url` 是证据来源页，`observed_url` 是在该页实际看到的出站 URL；没有取得链接时为 null。`first_party_linked` 只表示一手网页直接关联，`curated_list_candidate` 表示名单提供线索，二者均不代表 X 实时验证。

没有访问 X 域名、X API 或青果接口，没有重试上轮被限流的采集任务。研究方向仅作筛选上下文，精确现职、账号存活性、X 用户 ID 和活跃度均未核查。官网入口没有发现个人链接，只表示本轮未取得证据，不能推断该人没有个人账号。

数据文件：`datasets/people-expansion-researchers-2026-09-12.json`。
