# Tensorlake 设计资源归档

采集日期：2026-09-12。用户已确认采用这套品牌视觉与网站风格，见[项目品牌方向](../../brand-direction.md)。

**可以下载公开发布的成品素材；本次没有取得整套可编辑设计工程。** 已下载并验证 7 段 MP4、7 张原始 PNG、3 份 SVG、2 份 CSS、7 个字体文件，以及 2 份网页源码快照，共 28 项。另有视频预览取帧、用户确认截图与提取的设计变量。

打开 [本地素材预览](index.html) 可以播放动效、浏览原图。逐项 URL、大小、SHA-256、媒体参数与状态见 [manifest.json](manifest.json)。初始页面资源发现记录见 [sources.json](sources.json)。

## 截图中的素材

- 中间的 Agent Runtime 流程：[04-hero-animation-1440p.mp4](motion/04-hero-animation-1440p.mp4)，2560 × 1440，60 fps，约 10.07 秒，包含音轨。已取帧检查对应的节点、连线与 Agent Harness。
- 左上方的文档与图表处理：[03-cards-2160p.mp4](motion/03-cards-2160p.mp4)，2160 × 2160，60 fps，约 2.82 秒。
- 数据指标动效：[06-stats-2160p.mp4](motion/06-stats-2160p.mp4)，2160 × 2160，60 fps，约 5.5 秒。

这些动效的文字、节点和图形已经合成进 MP4，不能像 Figma 图层或网页元素一样直接修改。替换为 AgentHowTo 的数据与文案时，需要取得工程文件或按已确认的视觉规则重建。

## 已归档资源

| 目录 | 内容 | 编辑能力 |
| --- | --- | --- |
| `motion/` | HEX 案例的 7 段直接 MP4；实际尺寸见 manifest，不能只按文件名推断 | 可以播放、剪辑；没有分层节点或文字 |
| `images/` | 7 张原始 PNG；6 张 8640 × 8640，1 张 17520 × 8640 | 合成位图，无分层工程 |
| `svg/` | 官网页尾条带、原品牌标志、版本关系图 | 矢量结构可检查；内联导出补充了命名空间，关系图包含对应原 CSS |
| `styles/` | 官网发布的 2 份原始 CSS，以及提取的 `tokens.original.json` | 可检查颜色、字阶、间距、圆角、组件与响应式规则 |
| `fonts/` | JetBrains Mono 变量字体，以及网站引用的 6 个 PP Neue Montreal 文件 | 字体文件已归档，使用权见下文；不是字体厂商的完整字体家族 |
| `snapshots/` | 官网与 HEX 案例的公开 HTML，保存为 `.html.txt` | 用于追溯出处，不作为可运行的网站镜像 |
| `previews/` | 从本地原视频提取的 7 张 JPEG 封面 | 仅用于快速查看；原始视频未改动 |
| `user-reference/` | 用户确认的截图 | 固定本次选择的视觉目标 |

大文件、原始字体和第三方素材通过本目录 `.gitignore` 保留在本机，不会随普通 Git 提交自动发布。没有把素材写入应用的 `public/` 或部署到外部站点。

## 仍未取得的资源

- 在已检查的官网和 HEX 案例中，没有发现公开的 Figma、Illustrator、AE 工程、完整品牌手册或品牌素材 ZIP 入口。
- HEX 另嵌入 [Vimeo showreel](https://vimeo.com/1181903687)，本次保留播放链接；未声称拿到了该片的原始工程或可下载母版。
- 原始品牌标志和成品插画的商业再使用授权未确认。当前是项目本地参考归档，不把公开可访问解释为开放授权。
- 已排除 HEX 页面中其他项目的视频、第三方客户标志与网站统计脚本。

## 字体

**JetBrains Mono**：字体官方说明采用 SIL Open Font License 1.1，可用于商业和非商业用途。来源：[JetBrains 官方字体页](https://www.jetbrains.com/lp/mono/)。

**PP Neue Montreal**：本目录保存的是 Tensorlake 公开网页引用的文件，并不转移 Tensorlake 的字体许可。厂商提供个人试用与商业许可，实际项目需要匹配用途的授权。来源：[字体产品页](https://pangrampangram.com/products/neue-montreal)、[厂商许可 FAQ](https://pangrampangram.com/pages/faq)。本次没有购买许可，也没有安装这些字体到系统。

## 验证与来源

- 所有下载文件记录了大小和 SHA-256；28 项无下载失败。
- MP4 使用 ffprobe 检查编码、尺寸、帧率和时长，并成功提取预览帧。
- PNG 检查文件签名、原始尺寸和每个数据块的 CRC；SVG 检查 XML；字体检查文件格式签名。
- 参考网页：[HEX Tensorlake 案例](https://www.hex.inc/work/tensorlake)、[Tensorlake 官网](https://www.tensorlake.ai/)。

后续按已确认的字体层级、色彩、网格、条带、方形端点和分步动效制作 AgentHowTo 的页面与数据图；产品文案、数据和名称使用本项目内容。
