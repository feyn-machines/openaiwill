# ThreeUI 与 X 设计灵感来源清单

日期：2026-09-12。用户指定：[ThreeUI](https://threeui.com/browse) 与 [Dzianis Kravchu 的 X 帖子](https://x.com/thedzianis/status/2098393545006891310)。用于 AgentHowTo 的前卫数据网站设计研究。

后续重点参考：[Tensorlake 品牌案例](https://www.inspora.design/posts/tensorlake-brand)。已追溯到 [HEX 原始设计案例](https://www.hex.inc/work/tensorlake)，并对照当前官网实看，详见 [Tensorlake 品牌语言拆解](tensorlake-brand-study-2026-09-12.md)。这份补充重点研究条带、网格、技术标注如何组成完整视觉系统。

## X 原帖实际内容

原帖作者为 Dzianis Kravchu，账号 `@thedzianis`；页面显示发布于 2026-09-11。内容是一份含 8 个网站的设计灵感清单。本次通过浏览器读到正文和全部展开链接；网页文本工具对 X 返回 403，但浏览器可读取。没有将帖子的宣传性效果评价当作验证事实。

| 网站 | 本次核实到的内容 | 在本项目中的用途 | 优先级／边界 |
| --- | --- | --- | --- |
| [GetLayers](https://www.getlayers.ai/) | 浏览器实看主页，包含网站模板、3D 场景、渐变、交互区块、背景等分类；以 prompt 为交付入口 | 与 ThreeUI 一起建立品牌母题；探索光场、空间深度、材料和局部构图 | 高。部分媒体初次加载显示无法播放；未验收完整动效、导出或 MCP。帖中素材数量未逐项核计 |
| [Supahero](https://supahero.io/) | 官网为 Hero section library，列有真实网站案例；当前注明已加入 screensdesign | 找一个适合“数据先出现”的首屏构图，比较标题与主视觉比例 | 中。只拿首屏构图，不把整站变成营销 Hero 堆叠 |
| [CTA Gallery](https://www.cta.gallery/) | 官网按按钮、下载、表单、弹窗、导航、newsletter 等分类 | 周报订阅、关注赛道和证据补充入口 | 后续。界面收录不证明实际转化率更高，原帖相关说法未独立验证 |
| [loadmo.re](https://loadmo.re/) | 官方定位为另类移动网站档案，提供 3D、动画、编辑、极简、字体等分类 | 检查移动端如何保留前卫感、触摸反馈和排版 | 中。不是数据表格可用性基准；本次核对目录和定位，未逐个测试收录网站 |
| [60fps](https://60fps.design/) | 官网提供应用与网页交互片段，按 Graph、Tabs、Tooltip、Search、Empty State、Bottom Sheet 等筛选 | 筛选反馈、图表提示、侧面详情到移动底部面板的变化、空状态 | 高。页面数量和“60fps”名称不代表本项目帧率测试或性能保证 |
| [Recent](https://recent.design/) | 官网含 Web、Interface、Branding、Typography、Motion、3D 等，以及 OG Images、App Screenshots 入口 | 检查字体、色彩、界面组合，补充不同气质的样本 | 中。本次核验分类，不据原帖断言全部内容每天更新 |
| [posts.design](https://posts.design/) | 官网收录社交发布视觉，条目附原始来源页说明 | 周报封面、事件分享图、社交传播卡片的视觉延展 | 后续。用于传播设计，不作为能力／事件核验源 |
| [Navbar Gallery](https://www.navbar.gallery/) | 官网分类包含 Static、Dropdown、Mega Menu、Side Bar、Search Bar、Breadcrumbs 等 | 顶栏＋左栏＋搜索的职责划分；赛道／事件详情的面包屑 | 高。优先工作台型导航，避免全屏菜单遮挡持续读取的数据 |

上述用途与优先级是本研究的设计判断。已核实的是各站公开内容或页面结构，不是模板质量、授权、转化效果或技术兼容性的全面审计。

## ThreeUI 的优先样本

1. [Predictive Arc](https://threeui.com/backgrounds/predictive-arc) / [Data Pixel Arc](https://threeui.com/backgrounds/predictive-arc/data-pixel)：像素弧场，适合品牌识别层。
2. [Structure Flow / Data Field](https://threeui.com/three-js/structure-flow/data-field)：结构化空间与细线层次，适合图谱构图参考。
3. [Diagnostics Panel](https://threeui.com/ui-elements/diagnostics-panel)：官方列出层叠平面、节点和网格，适合解释数据层次；本次该预览未完整加载。
4. [Performance Gauges](https://threeui.com/css/performance-gauges)：已看橙色精密仪表，借鉴数值与刻度层级。当前 v0.2 事件贡献没有自然满分，不直接搬用百分比仪表。
5. [Aureon Markets](https://threeui.com/hero/aureon-markets)：蓝紫空间的 Pro 公开预览，适合高表现力备选；完整源码和交互未核验。

## 建议组合

**ThreeUI / Layers 的视觉母题 → DefiLlama / Token Terminal 的数据布局 → Navbar Gallery 的导航 → 60fps 的交互细节 → posts.design 的分享图延展。**

每一层只选择一个统一方向，再用真实数据状态验证。收集时记录：来源链接、作者或产品、截图／观察日期、页面类型、可借鉴元素、适用位置、访问或授权边界。避免把不同站的卡片、渐变、按钮和字体随意拼在一起。

主方案、颜色、页面结构、移动端和语义边界见[完整设计风格研究](web3-design-direction-2026-09-12.md)。
