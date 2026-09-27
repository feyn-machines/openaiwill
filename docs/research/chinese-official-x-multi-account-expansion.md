# 国内 AI 公司官方 X 多账号增量核实

核查日期：**2026-09-11，约 23:03–23:11（UTC+8）／15:03–15:11 UTC**。

本文件补充 Alibaba、DeepSeek、Tencent、Zhipu / Z.ai、Moonshot / Kimi、MiniMax、ByteDance 七家公司的产品、云平台、开发者和研究相关账号。上一轮已确认的七个账号及 MiniMax 下划线冲突见 [原账号研究](./chinese-official-x-accounts.md)，此处只记录增量；Baidu / ERNIE 仍排除。

**本轮得到 10 个有一手网页身份依据的增量账号。** 核查对象包含公司官网、产品官网、官方文档、官方 GitHub 和页面实际加载的官方前端资源。普通静态链接、渲染后的导航链接和网站 `sameAs` 身份声明分别注明。X 用户 ID、组织关联标识和当前显示名由主任务通过青果复核；本子任务未直连 X，也未采集时间线。

## 新增账号及确切官方依据

| 公司／产品 | 原始 profile 链接 | 产品范围 | 官方账号链接证据 | 公司／产品归属依据及边界 |
| --- | --- | --- | --- | --- |
| Alibaba / Alibaba Cloud | [@alibaba_cloud](https://www.twitter.com/alibaba_cloud) | 阿里云、Model Studio、云端 AI 产品与开发者公告 | [Alibaba Cloud 英文首页](https://www.alibabacloud.com/en?_p_lc=1)页脚标题为 Twitter 的真实链接先进入本站 `security-notice-kfxbqr?forward=https://www.twitter.com/alibaba_cloud`，目标明确 | 阿里云自身官网；这是云平台账号，和 Qwen 模型团队账号可并行，不自动把全部云消息判成模型更新 |
| Alibaba / Wan | [@Alibaba_Wan](https://x.com/Alibaba_Wan) | Wan 图像／视频生成模型与产品 | [Wan 官方 GitHub 组织](https://github.com/Wan-Video)直接链接 `https://x.com/Alibaba_Wan`，同时链接 `https://wan.video` | 该组织简介明确写 Alibaba Cloud 的生成模型；Wan 的阿里云服务范围也见 [官方视频生成文档](https://www.alibabacloud.com/help/en/model-studio/use-video-generation) |
| Tencent / 公司 | [@TencentGlobal](https://twitter.com/TencentGlobal) | 腾讯公司层面公告；可包含 AI 业务动态 | [Tencent 官网](https://www.tencent.com/)返回 HTML 的真实 `<a>` 指向 `https://twitter.com/TencentGlobal` | 腾讯自身官网；不是 Hunyuan 或 Yuanbao 的专属产品账号 |
| Tencent / Tencent Cloud | [@tencentcloud](https://twitter.com/tencentcloud) | 腾讯云、AI 平台、API、模型服务及开发者公告 | [Tencent Cloud 官网](https://www.tencentcloud.com/)页面数据含目标地址；随后在浏览器渲染 DOM 中直接确认标题为 Twitter 的 `<a href="https://twitter.com/tencentcloud">` | 腾讯云自身官网；网页列有 TokenHub、HY、YouTu、语音与数字人等服务，不能据此将该账号改称这些单独产品的账号 |
| MiniMax / Hailuo | [@Hailuo_AI](https://x.com/Hailuo_AI) | Hailuo 视频／创作产品；当前 X 显示名的变化由主任务复核 | [Hailuo 官网](https://hailuoai.video/)结构化数据的 `sameAs` 明确列 `https://x.com/Hailuo_AI`，并将 `parentOrganization.name` 设为 MiniMax；页面还给出该账号原帖链接 | 官网直接声明 MiniMax 归属。主任务本日通过青果反馈其当前 X 显示名为 **MiniMax Design (H3)**，且组织关联指向已确认的 `MiniMax_AI`；保留 `Hailuo_AI` 这个实际 handle，不按显示名另造账号 |
| MiniMax / Talkie | [@talkie_ai](https://twitter.com/talkie_ai) | Talkie AI 角色聊天产品 | [Talkie 官网](https://www.talkie-ai.com/)结构化组织数据的 `sameAs` 明确列 `https://twitter.com/talkie_ai` | [MiniMax 官方 WaytoAGI 新闻](https://www.minimax.io/news/minimax-at-the-waytoagi-global-ai-conference)明确把 Talkie、MiniMax Agent、Hailuo、音频／音乐平台列为 MiniMax 产品矩阵；不将其当成基础模型研究账号 |
| ByteDance / Dreamina | [@dreamina_ai](https://x.com/dreamina_ai/) | Dreamina 创作平台，包含 Seedance／Seedream 产品入口 | [Dreamina 官网](https://dreamina.capcut.com/)真实 `<a>` 指向 `https://x.com/dreamina_ai/` | 官方 CapCut 产品子域；[Seedance 2.0 官方产品页](https://dreamina.capcut.com/tools/seedance-2-0)明确 Dreamina 是其创作入口。可覆盖 Dreamina 的 Seedance 动态，不能自动改称 Seed 团队或 Seedance 独立账号 |
| ByteDance / BytePlus | [@BytePlusGlobal](https://x.com/BytePlusGlobal) | BytePlus 企业 AI 云、ModelArk、Seedance／Seedream／语音等商业服务 | [BytePlus 官网](https://www.byteplus.com/en)页脚真实 `<a>` 指向 `https://x.com/BytePlusGlobal` | [BytePlus 官方 About](https://www.byteplus.com/en/about-us)明确其产品建立在 ByteDance 的技术、研究和工程基础上；这是企业平台账号，不代表每项模型都有独立账号 |
| ByteDance / Coze | [@CozeHQ](https://x.com/CozeHQ) | Coze / 扣子，Agent 构建和开发者生态 | [coze-dev 官方 GitHub 组织](https://github.com/coze-dev)简介直接链接 `https://x.com/CozeHQ`，同时链接 `coze.com` 与 `coze.cn` | [扣子官方注册文档](https://docs.coze.cn/coze_sign_up)明确写明扣子属于字节跳动，涵盖 AI 办公协作与 AI 编程平台。账号覆盖不能自动等同全球版／中国版每项能力及可用性完全一致 |
| ByteDance / TRAE | [@Trae_ai](https://x.com/Trae_ai) | TRAE、TraeCode、TraeWork、SOLO 等产品和开发者动态 | [TRAE 官网](https://www.trae.ai/)静态 HTML 未含链接；实际浏览、滚动加载后，在页脚 Connect 区确认真实链接 `https://x.com/Trae_ai` | [ByteDance 官方 GitHub 组织](https://github.com/bytedance)置顶 [trae-agent](https://github.com/bytedance/trae-agent)；[BytePlus 官方 AI 方案](https://www.byteplus.com/en/contact-us/ai-solution)也列 TRAE。仅把实际官网链接用于 X 账号身份，不用页面引用的用户好评当官方账号证据 |

表内所有 profile 链接均从上述官方出处读得，没有根据产品名称猜造 handle。`twitter.com`、`x.com`、尾随 `/` 和官方链接中的大小写均按来源保留；后续归档应按 X 实际返回的数字用户 ID 管理身份。

## 需要主任务经青果继续核验的 X 原始入口

上述十个 profile 均可交由主任务执行当前身份解析，并检查是否存在明确的组织关联或官方介绍。网页证据成立不代表本轮已经取回其全部 X 帖文。主任务反馈已完成的身份结果，以主名单保存的核查时间和数字 ID 为准，本文件不重复编造 ID。

Hailuo 官网还直接给出了这一条原帖，可供核验官方介绍或产品范围：[Hailuo 原帖](https://x.com/Hailuo_AI/status/1970086888951394483)。**本子任务未打开该帖，不声明其作者正文、日期、内容完整性或是否最新。**

## 未形成增量账号的产品与候选

| 范围 | 已检查的增量入口 | 本轮结果与处理 |
| --- | --- | --- |
| Alibaba / Tongyi 研究与 ModelScope | [Tongyi 官网](https://tongyi.aliyun.com/)、[Tongyi-MAI](https://github.com/Tongyi-MAI)、[Alibaba-DAMO-Academy](https://github.com/Alibaba-DAMO-Academy)、[ali-vilab](https://github.com/ali-vilab)、[ModelScope 官方组织](https://github.com/modelscope)、[ModelScope 官网](https://modelscope.ai/)、DeepResearch 与 ModelScope 官方 README；补查部分官网直接加载的脚本 | 尚未从这些一手入口确立额外账号。搜索曾出现 `Ali_TongyiLab` 的第三方帖子线索，但不能据此提升为官方账号。保留待核实，不由名称猜填 |
| Tencent / Yuanbao 和额外研究账号 | 上一轮 [元宝官网](https://yuanbao.tencent.com/)缺口；本轮补查 [Tencent GitHub](https://github.com/Tencent)、[TencentCloud GitHub](https://github.com/TencentCloud)、[AI Lab 官网](https://ai.tencent.com/ailab/en/) | 未确立 Yuanbao 或其他研究专属账号；本轮新增的 TencentGlobal、tencentcloud 与已存 Hunyuan 账号并行，互不替代 |
| MiniMax Audio / Music | [MiniMax Audio 官网](https://www.minimax.io/audio)及其直接加载的应用导航脚本 | 未找到独立音频／音乐账号。导航的 TWITTER 项实际仍链接双下划线 `MiniMax__AI`，属于上一轮保留的冲突，不能算新增账号，也不能据此启用 |
| ByteDance / Seed、Doubao、Seedance 独立账号 | 上一轮 Seed／Doubao 官网缺口；本轮增加 Dreamina 与 BytePlus 官方产品入口 | 本轮已确认 Dreamina、BytePlus 两个相关产品／平台账号，可补产品动态覆盖；仍未确立 Seed、Doubao 或 Seedance 独立 handle，不把 Dreamina 账号直接重命名为 Seedance |
| ByteDance / CapCut 独立账号 | [CapCut 官网](https://www.capcut.com/)当前返回 HTML | 未从该入口取得确切 X 链接，不据名称推定账号；Dreamina 的直接证据独立保留 |
| Moonshot / Kimi 的额外产品账号 | [Moonshot 开发文档入口](https://platform.moonshot.ai/docs)本次跳转至 [Kimi 开发文档](https://platform.kimi.ai/docs/overview)，另查 [Kimi 官网](https://www.kimi.com/) | 文档只给出已记录 handle 的大小写变体 `https://x.com/Kimi_Moonshot`，未形成新的增量账号 |
| Zhipu / GLM 的额外账号 | [BigModel](https://open.bigmodel.cn/)、[Z.ai](https://z.ai/)、[THUDM GitHub](https://github.com/THUDM) | 未确立新的公司／产品账号。THUDM 页面确有 `https://twitter.com/thukeg`，但那是关联学术团队的入口，不等于智谱公司控制的账号；不纳入公司名单 |
| DeepSeek 额外产品账号 | [DeepSeek Chat](https://chat.deepseek.com/) | 本次请求 HTTP 403；未取得额外账号证据，保留现有公司账号，不推断只有一个账号 |

MiniMax Audio 的具体一手脚本证据：[官网应用导航脚本](https://cdn.hailuo.ai/hailuo-voice-web/prod-en-0.1.43/_next/static/chunks/app/(pages)/layout-60e242100e29109f.js)。这是页面 HTML 实际引用的版本；其 TWITTER 组件的链接值是 `https://x.com/MiniMax__AI`。资源 URL 带版本号，未来可能更新，应保留本次核查时间。官网浏览器页面本次未正常展开，因此没有把脚本中的组件存在描述成已在该次页面上成功点击。

## 后续采集边界

- 同一公司可以并行采集模型团队、云平台、开发者、产品等多个账号；分别保存范围，不只保留一个公司主号。
- 优先以原始 X 公告为发布证据，用官网／文档／GitHub 或 X 的明确组织关联证明账号身份；普通蓝标、名称相似、员工转发和第三方介绍不足以单独证明公司归属。
- 用户 ID、当前 handle、显示名和产品范围分别保存。Hailuo 的当前显示名变化说明显示名与 handle 不能混用。
- 缺口只表示本轮尚未得到可接受的一手依据，不表示相应官方账号不存在。
- 本文件为研究增量记录，未修改主名单、UI、环境变量、代理设置或采集器。
