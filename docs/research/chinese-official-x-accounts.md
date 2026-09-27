# 国内 AI 公司官方 X 账号核实

查询时间：**2026-09-11 22:58–23:00（UTC+8）／14:58–15:00 UTC**。范围为 Alibaba / Qwen、DeepSeek、Tencent / Hunyuan / Yuanbao、Zhipu / Z.ai / GLM、Moonshot / Kimi、MiniMax、ByteDance / Seed / Doubao / Agent TARS；按项目决定排除 Baidu / ERNIE。

本表用公司官网、官方开发文档、官方 GitHub 组织或仓库的确切出站链接确认账号关联。**官方链接核实、当前 X 用户身份解析、帖文内容完整性是三项独立检查。** 官方页面提到某个账号，不自动证明账号从未改名或转让，也不证明某条发布内容已经实际采集。

本轮重新读取官方网页 HTML 与官方仓库 README，保留 URL 中的原始大小写和下划线；没有通过搜索摘要认定官方身份。用途列表示按官方出处确定的采集范围，不表示已经验证该账号所有历史帖文的内容。

## 已确认官方出站链接的账号

| 公司／产品 | 账号与确切出站 URL | 用途／范围 | 本次一手证据 | 状态与限制 |
| --- | --- | --- | --- | --- |
| Alibaba / Qwen | [@Alibaba_Qwen](https://x.com/Alibaba_Qwen) | Qwen 模型、开发工具及相关产品公告；不直接覆盖 Alibaba 全部业务 | [Qwen 官方 GitHub 组织](https://github.com/QwenLM)简介写明 Alibaba Cloud 模型团队，并链接 `https://x.com/Alibaba_Qwen` | 官方出站链接已确认；本说明未记录该账号当前数字用户 ID |
| DeepSeek | [@deepseek_ai](https://twitter.com/deepseek_ai) | DeepSeek 模型、API 与产品公告 | [DeepSeek API 文档](https://api-docs.deepseek.com/)页脚 Community → Twitter 的实际链接为 `https://twitter.com/deepseek_ai` | 官方出站链接已确认；保留来源中的 `twitter.com` 原始形式 |
| Tencent / Hunyuan | [@TencentHunyuan](https://x.com/TencentHunyuan) | 混元模型与相关开源项目；不自动视为元宝专属账号 | 官方 [HunyuanImage-3.0 README](https://github.com/Tencent-Hunyuan/HunyuanImage-3.0/blob/main/README.md)与 [Hunyuan3D-2.1 README](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/README.md)均含 `https://x.com/TencentHunyuan` | 官方出站链接已确认；范围限混元 |
| Zhipu / Z.ai / GLM | [@Zai_org](https://x.com/Zai_org) | Z.ai / GLM 模型与开发平台公告 | [Z.ai 官方 GitHub 组织](https://github.com/zai-org)与 [Z.ai 开发文档](https://docs.z.ai/guides/overview/quick-start)均链接 `https://x.com/Zai_org` | 官方出站链接已确认；不据此自动收录同名员工或旧品牌账号 |
| Moonshot / Kimi | [@kimi_moonshot](https://twitter.com/kimi_moonshot) | Kimi 模型与产品公告 | 官方 [Kimi-K2 README](https://github.com/MoonshotAI/Kimi-K2/blob/main/README.md)写明 Moonshot AI 开发，并链接 `https://twitter.com/kimi_moonshot` | 官方出站链接已确认；保留来源中的原始 URL |
| MiniMax | [@MiniMax_AI](https://x.com/MiniMax_AI)，**一个下划线** | MiniMax 模型、API 和开发者相关公告 | [MiniMax 官方 GitHub 组织](https://github.com/MiniMax-AI)与 [MiniMax API 文档](https://platform.minimax.io/docs/guides/models-intro)的实际链接均为 `https://x.com/MiniMax_AI` | **可启用**：除官方链接外，本次经青果进行 X 只读身份解析，返回用户 ID `1875078099538423808`；仍保留双下划线链接冲突，详见下文 |
| ByteDance / Agent TARS | [@agent_tars](https://twitter.com/agent_tars) | Agent TARS 产品／开源代理项目公告 | ByteDance 官方 [UI-TARS-desktop 中文 README](https://github.com/bytedance/UI-TARS-desktop/blob/main/README.zh-CN.md)含 `https://twitter.com/agent_tars` | 官方出站链接已确认；这是产品账号，不能替代 Seed、Doubao 或 ByteDance 公司总账号 |

仓库证据同时通过对应 `raw.githubusercontent.com/<组织>/<仓库>/main/<README 文件>` 内容复查，所列 URL 均存在于返回正文中。随后完成的统一身份查询已取得上述 7 个启用账号的数字 ID，见[正式名单](../data/official-x-accounts.md)及[身份查询记录](../../datasets/evidence/x-account-profile-checks-2026-09-11.json)。

## MiniMax 单／双下划线的处理

| 候选账号 | 当前官方来源 | 2026-09-11 身份复核 | 正式名单建议 |
| --- | --- | --- | --- |
| [@MiniMax_AI](https://x.com/MiniMax_AI) | [官方 GitHub 组织](https://github.com/MiniMax-AI)和 [API 文档](https://platform.minimax.io/docs/guides/models-intro)均有实际超链接 | 14:59:39 UTC，经青果通道执行 X 只读 `UserByScreenName`；HTTP 200，返回类型 `User`，解析账号 `MiniMax_AI`，ID `1875078099538423808` | 启用，按数字 ID 绑定身份 |
| [@MiniMax__AI](https://x.com/MiniMax__AI) | [M2.1 官方文章](https://www.minimax.io/news/minimax-m21)在 Contact Us 明确写出 MiniMax X 并链接双下划线；[官网首页](https://www.minimax.io/)返回页面的数据中也含该 URL，但本次静态 HTML 未解析出对应 `<a>` | 14:59:40 UTC，经同一青果通道请求；HTTP 200，但未返回 `User`、数字 ID 或解析账号 | **默认禁用，保留冲突记录，不与单下划线合并** |

结论是：单下划线账号同时具备当前官方链接与本次可解析用户身份；双下划线仍有官网来源，但本次未解析成功。**不能把 HTTP 200 等同于用户存在，也不能由一次未解析就断言账号不存在、已注销、已迁移或是假账号。** 两个写法的历史关系仍未证实。上述身份解析经项目已有青果通道完成，公开结果不含代理配置或登录凭据。

另外读取了官方 MiniMax-M2.7、MiniMax-H3、MiniMax-Music3 仓库的当前英文 README，均未发现 X／Twitter 链接；这些缺失没有用于推断两个账号之间的关系。

## 暂不补入正式账号的缺口

| 公司／产品 | 本轮已检查的一手页面 | 观察结果 | 处理 |
| --- | --- | --- | --- |
| Tencent / Yuanbao | [元宝官网](https://yuanbao.tencent.com/) | 返回 HTML 中未发现 X／Twitter URL；浏览工具可读内容有限 | 专属账号待核实；不使用 Hunyuan 账号冒充元宝专属账号 |
| ByteDance / Seed | [Seed 英文官网](https://seed.bytedance.com/en/)、[ByteDance-Seed 官方 GitHub 组织](https://github.com/ByteDance-Seed)、[ByteDance 公司官网](https://www.bytedance.com/en/) | 返回页面中未发现能够确立 Seed 专属 X 账号的出站链接；Seed 官网的浏览工具文本提取为空，补查 HTML 仍未发现 X URL | 专属账号待核实；不接受仅有第三方提及的 `@ByteDanceSeed` 等猜测 |
| ByteDance / Doubao | [豆包官网](https://www.doubao.com/)（本次跳转到 [chat 页面](https://www.doubao.com/chat/)） | 返回 HTML 中未发现 X／Twitter URL，浏览工具未提取到正文 | 专属账号待核实；不推断不存在 |
| ByteDance 公司总账号 | [ByteDance 公司官网](https://www.bytedance.com/en/) | 本轮检查的页面未给出 X 账号链接 | 不用员工账号或 Agent TARS 产品账号替代公司总账号 |

“未找到链接”仅描述上述页面与本轮方法的结果，不能证明全站、所有官方渠道或 X 上均没有对应账号。国内公司在其他社交平台上的官方账号也不自动构成 X 账号证明。

## 沿用的历史帖文样本：本轮未重抓

下列 4 条记录来自本文件原有的 **2026-09-11 较早一轮**采集。当时 X 公共 oEmbed 返回了作者、日期及 HTML 摘录。本轮只重新核对官方账号链接并补入 MiniMax 身份复核，**没有重新请求这些帖文或 oEmbed**。保留样本用于后续核对，不能称为本轮最新发布、完整线程或持续监控结果。

| 原始帖子 | 原记录中的 X 显示日期／作者 URL | 原记录中的内容摘要 | 原记录的完整性限制 |
| --- | --- | --- | --- |
| [DeepSeek-R1](https://x.com/deepseek_ai/status/1881318130334814301) | 2025-01-20；`https://x.com/deepseek_ai` | 宣布 R1、模型／报告、MIT 许可及网页／API 可用性 | 摘录无明显截断标记，但自标为 1/n；其余线程与媒体未取回。性能比较属于厂商宣称 |
| [DeepSeek-V3-0324](https://x.com/deepseek_ai/status/1904526863604883661) | 2025-03-25；`https://x.com/deepseek_ai` | 宣布模型更新，描述推理、前端开发、工具使用改进 | 摘录出现省略号，不补写缺失句子 |
| [Hunyuan3D-PolyGen](https://x.com/TencentHunyuan/status/1942174221976981881) | 2025-07-07；`https://x.com/TencentHunyuan` | 宣布面向重拓扑与专业美术工作流的 3D 生成更新 | 摘录截断；日期来自当时 oEmbed 显示值 |
| [MiniMax M3](https://x.com/MiniMax_AI/status/2061266317815296322) | 2026-06-01；`https://x.com/MiniMax_AI` | 宣布 M3，并宣称编程、Agent 能力及采用稀疏注意力的百万 token 上下文 | 摘录截断；基准测试未独立复核；此样本本身不能证明账号迁移 |

原记录使用的请求形式是 `https://publish.twitter.com/oembed?url=<URL 编码后的原帖 URL>&omit_script=true&dnt=true`。它返回的是第一方嵌入摘录，不等于完整原帖、完整线程或时间线导出；帖子发现线索与实际返回正文的证据应分别记录。

## 数据使用边界

- 账号名单保留确切 handle、官方证据 URL、核实时间、适用产品、身份解析状态和已取得的数字用户 ID；handle 相似不构成同一账号的依据。
- 仅从被实际取回的原文做翻译和摘要，分别记录发布事实、可用性条件、厂商自报性能及编辑分析。
- 持续采集时保存原帖 URL、完整性／截断状态、线程和媒体信息、采集时间与通道；账号验证完成不代表采集管线已经完备。
- 本文不包含创业风险结论、商业替代评分或独立能力验证结果。
