# 人物来源首轮候选核验（2026-09-12）

后续已按公开名单扩容，当前完整人物范围见[AI 人物与 X 名单](ai-people-x-lists-2026-09-12.md)及[机器可读目录](../../datasets/ai-people-watchlist.json)。本文件保留最初 7 人的一手核验证据，不再代表全部候选人数。

本轮按 `research` 工作流核验 **7 位人物、5 个候选 X handle**，覆盖现有公司范围中的 OpenAI、Anthropic、Google、Microsoft、Tencent。全部记录保持 `enabled: false`；这不是全员名单，也不表示人物账号已经全部确认或可采集。

配套数据：[person-source-candidates-2026-09-12.json](../../datasets/person-source-candidates-2026-09-12.json)。

## 候选与官方依据

| 人物 | 现职及官方依据 | 候选 handle 与身份依据 | 尚未确认 |
| --- | --- | --- | --- |
| Sam Altman | OpenAI CEO；[当前组织结构页](https://openai.com/our-structure/) | `sama`；[个人博客](https://blog.samaltman.com/) HTML 有 `Follow @sama`，链接到 `https://twitter.com/sama` | 数字 ID、当前 profile 和可采集性 |
| Greg Brockman | OpenAI 总裁、联合创始人；[2026-08-13 公司文章](https://openai.com/index/dali-rajic-chief-revenue-officer/) | `gdb`；[个人主页](https://gregbrockman.com/) Contact 直接链接 `https://twitter.com/gdb` | 数字 ID、当前 profile 和可采集性 |
| Dario Amodei | Anthropic 联合创始人、CEO；[领导团队页](https://www.anthropic.com/company/leadership) | `unknown`；公司链接的[个人官网](https://darioamodei.com/)可作为文章/访谈来源 | 本轮未取得个人 X 直链，不猜测 handle |
| Demis Hassabis | Google DeepMind 主席、Alphabet 首席科学家；[官方职位变更公告](https://blog.google/company-news/inside-google/message-ceo/next-chapter-ai-momentum/)及[作者页](https://blog.google/authors/demis-hassabis/) | `demishassabis`；变更公告正文将其对外活动链接至该 handle 的 [X Article](https://x.com/demishassabis/article/2076957440109625718?lang=en)，仅读取官网 href | 数字 ID、当前 profile 和可采集性 |
| Satya Nadella | Microsoft 董事长、CEO；[当前高管页](https://news.microsoft.com/source/exec/satya-nadella/) | `satyanadella`；[Microsoft New England 公司博客](https://blogs.microsoft.com/newengland/2014/02/05/local-leaders-welcome-microsofts-new-ceo-satya-nadella/)直接关联姓名与账号链接 | 账号证据来自 2014 年；当前归属及数字 ID 必须再核 |
| Mustafa Suleyman | Microsoft AI CEO；[公司官网](https://microsoft.ai/) | `mustafasuleyman`；[个人官网](https://mustafa-suleyman.ai/) HTML 的 X 链接为 `https://x.com/mustafasuleyman` | 数字 ID、当前 profile 和可采集性 |
| 马化腾 / Pony Ma | 腾讯联合创始人、董事会主席兼 CEO；[公司人物页](https://www.tencent.com/team/ma-huateng-pony-ma/) | `unknown`；本轮人物页仅见 TencentGlobal 公司账号链接 | 未取得个人 X 直链，不能把公司账号当作个人账号 |

## 已处理的时效问题

Google 的[旧 about 页](https://deepmind.google/about/)仍写 Demis 为 CEO。明确的[变更公告](https://blog.google/company-news/inside-google/message-ceo/next-chapter-ai-momentum/)与已更新作者页支持新职位，因此本表采用新职位。公告 HTML 的 `datePublished` 为 `2026-08-05T16:00:00+00:00`，本表的 `as_of` 表示本轮核验日期。

同一公告说明 Jeff Dean 与 Sanjay Ghemawat 正创办独立公司。Jeff 的旧作者页虽仍保留 Google 首席科学家职位，本轮没有将其作为该职位的当前负责人候选；后续需要单独核验新组织与任职时间。

## 采集前剩余步骤

本轮没有打开 X 主页或帖子，也没有操作青果账户。五个 handle 可交给主采集流程，通过青果取得 profile 和数字用户 ID，再核对官网已关联身份。Dario 与马化腾继续保留无已核个人账号状态。

本轮公司来源采集触发 429 后，主流程已停止 X 请求。因此这 5 个候选 handle **本轮未做 numeric author ID 核验**，继续全部停用，不计入已启用人物来源。

`role_verification_status` 记录现职的一手依据；`identity_verification_status` 记录官网与候选账号的关联，后者不代表当前账号控制权已确认。`x_profile_verification_status` 为 `pending_qingguo` 或 `unknown`，`x_user_id` 均为空。缺证据时维持停用。

网站文章、公司具名引述、访谈和演讲提供了这批人物的公开表达入口；本轮未测量发帖频率，也未判定每次个人发言都代表公司。单条声明仍需记录原话、发言时间、场合和当时职位，并与正式公司公告区分。
