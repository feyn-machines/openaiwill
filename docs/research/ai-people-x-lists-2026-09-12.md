# AI 人物与 X 名单（2026-09-12）

按“直接找现成列表”的要求，先合并公开人物目录，再做账号去重和明显错链剔除。原先 7 人只是最初核验样本，不再作为完整人物范围。

当前收录 **157 位带 X 候选账号的人物**：113 位优先观察，44 位扩展观察；另有 5 位待确认个人账号。保留了 **12 位的官网关联证据**。这里的‘优先’是本项目的采集顺序，不是全球影响力排名。

## 直接找到的现成列表

| 名单 | 本轮读到的内容 | 用法 |
| --- | --- | --- |
| [AI/TLDR — Top AI Influencers](https://ai-tldr.dev/influencers/) | 页面标注 116 人；实际提取 62 条明确 X/Twitter 链接 | 创始人、研究者、工程与开源人物；不将 YouTube handle 直接当 X |
| [Awesome AI X Influencers](https://github.com/codeman008/awesome-ai-x-influencers) | 从姓名表格提取 65 行 X 关联，含公司和社区 | 补研究、工具、中国 AI 圈；剔除公司与社区账号 |
| [Follow the AI Leaders](https://github.com/mattnigh/follow-the-ai-leaders) | Twitter/X 人物表提取 31 行 | 补模型研究和安全方向，采用实际 href |
| [Prometheans 100+](https://prometheusroot.com/prometheans-100/) | 页面 153 张人物卡，其中 127 张有格式有效的 X 链接 | 仅挑选补缺的公司、研究和机器人人物，不整表照搬 |
| [AI Engineering Handbook](https://github.com/DataExpert-io/ai-engineer-handbook) | 包含 AI 人物与 Twitter 入口 | 交叉检查部分研究者账号 |

提取量不是去重后人数，也不是身份核验数量。比如有目录把 Jensen Huang 链到 NVIDIA 公司账号，还有目录给 Greg Brockman 的链接与其官网不符；这些关联没有导入个人账号。Jim Fan 的候选采用其个人官网指向的 `DrJimFan`。候选发现不需要等完整职位研究完成。

机器可读名单：[ai-people-watchlist.json](../../datasets/ai-people-watchlist.json)。每人保留名单来源、X 链接、优先级和身份状态。职位变化不从第三方目录自动升级为事实。先前的[7 人核验表](people-source-readiness-2026-09-12.md)及[研究者补充核验](people-expansion-researchers-2026-09-12.md)作为证据保留。

本轮查的是现成名单与官网链接，没有调用 X API；上一轮限流后尚未续跑。名单已选入后续采集队列，运行启用状态仍为 false。下一次有界采集获取数字作者身份时，再把对应记录升级为已核验。

## 优先观察人物

| 人物 | X 候选 | 身份依据 |
| --- | --- | --- |
| AI Jason | [@AIJasonZ](https://x.com/AIJasonZ) | 公开名单候选 |
| Aidan Gomez | [@aidangomez](https://x.com/aidangomez) | 公开名单候选 |
| AK | [@_akhaliq](https://x.com/_akhaliq) | 公开名单候选 |
| Alec Radford | [@AlecRad](https://x.com/AlecRad) | 公开名单候选 |
| Alex Albert | [@alexalbert__](https://x.com/alexalbert__) | 公开名单候选 |
| Alex J. Champandard | [@alexjc](https://x.com/alexjc) | 公开名单候选 |
| Alexandr Wang | [@alexandr_wang](https://x.com/alexandr_wang) | 公开名单候选 |
| Amanda Askell | [@AmandaAskell](https://x.com/AmandaAskell) | 公开名单候选 |
| Amjad Masad | [@amasad](https://x.com/amasad) | 公开名单候选 |
| Andrej Karpathy | [@karpathy](https://x.com/karpathy) | 官网关联已找到；数字ID待核 |
| Andrew Ng | [@AndrewYNg](https://x.com/AndrewYNg) | 公开名单候选 |
| Aravind Srinivas | [@AravSrinivas](https://x.com/AravSrinivas) | 公开名单候选 |
| Arthur Mensch | [@arthurmensch](https://x.com/arthurmensch) | 公开名单候选 |
| Arvind Narayanan | [@random_walker](https://x.com/random_walker) | 公开名单候选 |
| Ashish Vaswani | [@ashVaswani](https://x.com/ashVaswani) | 公开名单候选 |
| Barry Zhang | [@barry_zyj](https://x.com/barry_zyj) | 公开名单候选 |
| Blake Richards | [@tyrell_turing](https://x.com/tyrell_turing) | 公开名单候选 |
| Boris Cherny | [@bcherny](https://x.com/bcherny) | 公开名单候选 |
| Chelsea Finn | [@chelseabfinn](https://x.com/chelseabfinn) | 官网关联已找到；数字ID待核 |
| Chris Olah | [@ch402](https://x.com/ch402) | 公开名单候选 |
| Christopher Manning | [@chrmanning](https://x.com/chrmanning) | 官网关联已找到；数字ID待核 |
| Clément Delangue | [@ClementDelangue](https://x.com/ClementDelangue) | 公开名单候选 |
| Connor Leahy | [@NPCollapse](https://x.com/NPCollapse) | 公开名单候选 |
| Cristóbal Valenzuela | [@c_valenzuelab](https://x.com/c_valenzuelab) | 公开名单候选 |
| Dan Hendrycks | [@DanHendrycks](https://x.com/DanHendrycks) | 公开名单候选 |
| Daniela Amodei | [@DanielaAmodei](https://x.com/DanielaAmodei) | 公开名单候选 |
| Daphne Koller | [@DaphneKoller](https://x.com/DaphneKoller) | 公开名单候选 |
| Dario Amodei | [@DarioAmodei](https://x.com/DarioAmodei) | 公开名单候选 |
| David Ha | [@hardmaru](https://x.com/hardmaru) | 公开名单候选 |
| David Holz | [@DavidSHolz](https://x.com/DavidSHolz) | 公开名单候选 |
| Demis Hassabis | [@demishassabis](https://x.com/demishassabis) | 官网关联已找到；数字ID待核 |
| Eliezer Yudkowsky | [@ESYudkowsky](https://x.com/ESYudkowsky) | 公开名单候选 |
| Elon Musk | [@elonmusk](https://x.com/elonmusk) | 公开名单候选 |
| Elvis Saravia | [@omarsar0](https://x.com/omarsar0) | 公开名单候选 |
| Emad Mostaque | [@EMostaque](https://x.com/EMostaque) | 公开名单候选 |
| Eric Hartford | [@erhartford](https://x.com/erhartford) | 公开名单候选 |
| Erik Brynjolfsson | [@erikbryn](https://x.com/erikbryn) | 公开名单候选 |
| Ethan Mollick | [@emollick](https://x.com/emollick) | 公开名单候选 |
| Fei-Fei Li | [@drfeifei](https://x.com/drfeifei) | 公开名单候选 |
| Frank Willett | [@WillettNeuro](https://x.com/WillettNeuro) | 公开名单候选 |
| François Chollet | [@fchollet](https://x.com/fchollet) | 公开名单候选 |
| Geoffrey Hinton | [@geoffreyhinton](https://x.com/geoffreyhinton) | 公开名单候选 |
| George Hotz | [@realGeorgeHotz](https://x.com/realGeorgeHotz) | 公开名单候选 |
| Georgi Gerganov | [@ggerganov](https://x.com/ggerganov) | 公开名单候选 |
| Greg Brockman | [@gdb](https://x.com/gdb) | 官网关联已找到；数字ID待核 |
| Guillaume Lample | [@GuillaumeLample](https://x.com/GuillaumeLample) | 公开名单候选 |
| Guillermo Rauch | [@rauchg](https://x.com/rauchg) | 公开名单候选 |
| Harrison Chase | [@hwchase17](https://x.com/hwchase17) | 公开名单候选 |
| Horace He | [@cHHillee](https://x.com/cHHillee) | 公开名单候选 |
| Ian Goodfellow | [@goodfellow_ian](https://x.com/goodfellow_ian) | 公开名单候选 |
| Ilya Sutskever | [@ilyasut](https://x.com/ilyasut) | 公开名单候选 |
| Jack Clark | [@jackclarkSF](https://x.com/jackclarkSF) | 公开名单候选 |
| James Briggs | [@jamescalam](https://x.com/jamescalam) | 公开名单候选 |
| James Manyika | [@JamesManyika](https://x.com/JamesManyika) | 公开名单候选 |
| Jan Leike | [@janleike](https://x.com/janleike) | 公开名单候选 |
| Jason Wei | [@_jasonwei](https://x.com/_jasonwei) | 公开名单候选 |
| Jeff Dean | [@JeffDean](https://x.com/JeffDean) | 公开名单候选 |
| Jeremy Howard | [@jeremyphoward](https://x.com/jeremyphoward) | 公开名单候选 |
| Jim Fan | [@DrJimFan](https://x.com/DrJimFan) | 官网关联已找到；数字ID待核 |
| Joanne Jang | [@joannejang](https://x.com/joannejang) | 公开名单候选 |
| John Carmack | [@ID_AA_Carmack](https://x.com/ID_AA_Carmack) | 公开名单候选 |
| Jürgen Schmidhuber | [@SchmidhuberAI](https://x.com/SchmidhuberAI) | 公开名单候选 |
| Karina Nguyen | [@KarinaHNguyen](https://x.com/KarinaHNguyen) | 公开名单候选 |
| Karol Hausman | [@hausman_k](https://x.com/hausman_k) | 公开名单候选 |
| Kevin Scott | [@kevin_scott](https://x.com/kevin_scott) | 公开名单候选 |
| Lila Ibrahim | [@lilaibrahim](https://x.com/lilaibrahim) | 公开名单候选 |
| Lilian Weng | [@lilianweng](https://x.com/lilianweng) | 公开名单候选 |
| Lisa Su | [@LisaSu](https://x.com/LisaSu) | 公开名单候选 |
| Logan Kilpatrick | [@OfficialLoganK](https://x.com/OfficialLoganK) | 公开名单候选 |
| Lukas Biewald | [@l2k](https://x.com/l2k) | 公开名单候选 |
| Luyu Zhang | [@goocarlos](https://x.com/goocarlos) | 公开名单候选 |
| Margaret Mitchell | [@m_mitchell_ml](https://x.com/m_mitchell_ml) | 公开名单候选 |
| Mark Chen | [@markchen90](https://x.com/markchen90) | 公开名单候选 |
| Mati Staniszewski | [@matistanis](https://x.com/matistanis) | 公开名单候选 |
| Matt Shumer | [@mattshumer_](https://x.com/mattshumer_) | 公开名单候选 |
| Maxime Labonne | [@maximelabonne](https://x.com/maximelabonne) | 公开名单候选 |
| Mike Krieger | [@mikeyk](https://x.com/mikeyk) | 公开名单候选 |
| Mira Murati | [@miramurati](https://x.com/miramurati) | 公开名单候选 |
| Mustafa Suleyman | [@mustafasuleyman](https://x.com/mustafasuleyman) | 官网关联已找到；数字ID待核 |
| Nat Friedman | [@natfriedman](https://x.com/natfriedman) | 公开名单候选 |
| Noam Shazeer | [@NoamShazeer](https://x.com/NoamShazeer) | 公开名单候选 |
| Oriol Vinyals | [@oriolvinyalsml](https://x.com/oriolvinyalsml) | 公开名单候选 |
| Paul Christiano | [@paulfchristiano](https://x.com/paulfchristiano) | 公开名单候选 |
| Percy Liang | [@percyliang](https://x.com/percyliang) | 公开名单候选 |
| Peter Steinberger | [@steipete](https://x.com/steipete) | 公开名单候选 |
| Pieter Abbeel | [@pabbeel](https://x.com/pabbeel) | 公开名单候选 |
| Pranav Rajpurkar | [@pranavrajpurkar](https://x.com/pranavrajpurkar) | 公开名单候选 |
| Quoc Le | [@quocleix](https://x.com/quocleix) | 公开名单候选 |
| Rachel Thomas | [@math_rachel](https://x.com/math_rachel) | 公开名单候选 |
| Raquel Urtasun | [@RaquelUrtasun](https://x.com/RaquelUrtasun) | 公开名单候选 |
| Richard Ngo | [@RichardMCNgo](https://x.com/RichardMCNgo) | 公开名单候选 |
| Richard Socher | [@richardsocher](https://x.com/richardsocher) | 公开名单候选 |
| Riley Goodside | [@goodside](https://x.com/goodside) | 公开名单候选 |
| Rob Bensinger | [@robbensinger](https://x.com/robbensinger) | 公开名单候选 |
| Russ Salakhutdinov | [@rsalakhu](https://x.com/rsalakhu) | 公开名单候选 |
| Sam Altman | [@sama](https://x.com/sama) | 官网关联已找到；数字ID待核 |
| Sam Witteveen | [@samwitteveen](https://x.com/samwitteveen) | 公开名单候选 |
| Santiago Valdarrama | [@svpino](https://x.com/svpino) | 公开名单候选 |
| Satya Nadella | [@satyanadella](https://x.com/satyanadella) | 官网关联已找到；数字ID待核 |
| Sebastian Raschka | [@rasbt](https://x.com/rasbt) | 公开名单候选 |
| Sergey Levine | [@svlevine](https://x.com/svlevine) | 官网关联已找到；数字ID待核 |
| Shawn Wang (swyx) | [@swyx](https://x.com/swyx) | 公开名单候选 |
| Simon Willison | [@simonw](https://x.com/simonw) | 公开名单候选 |
| Soumith Chintala | [@soumithchintala](https://x.com/soumithchintala) | 公开名单候选 |
| Stella Biderman | [@BlancheMinerva](https://x.com/BlancheMinerva) | 公开名单候选 |
| Sundar Pichai | [@sundarpichai](https://x.com/sundarpichai) | 公开名单候选 |
| Thomas Wolf | [@Thomwolf](https://x.com/Thomwolf) | 公开名单候选 |
| Timnit Gebru | [@timnitGebru](https://x.com/timnitGebru) | 公开名单候选 |
| Tri Dao | [@tri_dao](https://x.com/tri_dao) | 公开名单候选 |
| Yann LeCun | [@ylecun](https://x.com/ylecun) | 公开名单候选 |
| Yoshua Bengio | [@Yoshua_Bengio](https://x.com/Yoshua_Bengio) | 官网关联已找到；数字ID待核 |
| Yuke Zhu | [@yukez](https://x.com/yukez) | 官网关联已找到；数字ID待核 |
| 李开复 | [@kaifulee](https://x.com/kaifulee) | 公开名单候选 |

## 扩展观察人物

主要用于产品体验、评论、传播与社区线索，不一律称为 AI 世界领袖。

| 人物 | X 候选 | 身份依据 |
| --- | --- | --- |
| Abhishek Thakur | [@abhi1thakur](https://x.com/abhi1thakur) | 公开名单候选 |
| Aleksa Gordić | [@gordic_aleksa](https://x.com/gordic_aleksa) | 公开名单候选 |
| Alex Finn | [@AlexFinn](https://x.com/AlexFinn) | 公开名单候选 |
| Allie K. Miller | [@alliekmiller](https://x.com/alliekmiller) | 公开名单候选 |
| Axton | [@AxtonLiu](https://x.com/AxtonLiu) | 公开名单候选 |
| Casey Newton | [@CaseyNewton](https://x.com/CaseyNewton) | 公开名单候选 |
| Codie Sanchez | [@Codie_Sanchez](https://x.com/Codie_Sanchez) | 公开名单候选 |
| Craig S. Smith | [@craigss](https://x.com/craigss) | 公开名单候选 |
| CuiMao | [@CuiMao](https://x.com/CuiMao) | 公开名单候选 |
| David Shapiro | [@DavidShapiro](https://x.com/DavidShapiro) | 公开名单候选 |
| Elad Gil | [@eladgil](https://x.com/eladgil) | 公开名单候选 |
| Eric Topol | [@EricTopol](https://x.com/EricTopol) | 公开名单候选 |
| Fireship | [@fireship_dev](https://x.com/fireship_dev) | 公开名单候选 |
| Gary Marcus | [@GaryMarcus](https://x.com/GaryMarcus) | 公开名单候选 |
| Gorden Sun | [@Gorden_Sun](https://x.com/Gorden_Sun) | 公开名单候选 |
| Greg Isenberg | [@gregisenberg](https://x.com/gregisenberg) | 公开名单候选 |
| Jay Alammar | [@JayAlammar](https://x.com/JayAlammar) | 公开名单候选 |
| JimmyWong | [@thinkingjimmy](https://x.com/thinkingjimmy) | 公开名单候选 |
| Kevin Roose | [@kevinroose](https://x.com/kevinroose) | 公开名单候选 |
| Kirk Borne | [@KirkDBorne](https://x.com/KirkDBorne) | 公开名单候选 |
| levelsio | [@levelsio](https://x.com/levelsio) | 公开名单候选 |
| Lex Fridman | [@lexfridman](https://x.com/lexfridman) | 公开名单候选 |
| Lior | [@LiorOnAI](https://x.com/LiorOnAI) | 公开名单候选 |
| Matthew Berman | [@matthewberman](https://x.com/matthewberman) | 公开名单候选 |
| meng shao | [@shao__meng](https://x.com/shao__meng) | 公开名单候选 |
| Nathaniel Whittemore | [@nlw](https://x.com/nlw) | 公开名单候选 |
| Orange AI | [@oran_ge](https://x.com/oran_ge) | 公开名单候选 |
| Peter Yang | [@petergyang](https://x.com/petergyang) | 公开名单候选 |
| Robert Scoble | [@Scobleizer](https://x.com/Scobleizer) | 公开名单候选 |
| Ronald van Loon | [@Ronald_vanLoon](https://x.com/Ronald_vanLoon) | 公开名单候选 |
| Rowan Cheung | [@rowancheung](https://x.com/rowancheung) | 公开名单候选 |
| Sarah Guo | [@saranormous](https://x.com/saranormous) | 公开名单候选 |
| sentdex | [@Sentdex](https://x.com/Sentdex) | 公开名单候选 |
| Theo | [@theo](https://x.com/theo) | 公开名单候选 |
| Tina Huang | [@TinaHuang1](https://x.com/TinaHuang1) | 公开名单候选 |
| Vikhyat | [@vikhyatk](https://x.com/vikhyatk) | 公开名单候选 |
| Wes Roth | [@WesRoth](https://x.com/WesRoth) | 公开名单候选 |
| Yannic Kilcher | [@ykilcher](https://x.com/ykilcher) | 公开名单候选 |
| Yohei Nakajima | [@yoheinakajima](https://x.com/yoheinakajima) | 公开名单候选 |
| 向阳乔木 | [@vista8](https://x.com/vista8) | 公开名单候选 |
| 宝玉 | [@dotey](https://x.com/dotey) | 公开名单候选 |
| 小互 | [@xiaohu](https://x.com/xiaohu) | 公开名单候选 |
| 李继刚 | [@lijigang](https://x.com/lijigang) | 公开名单候选 |
| 歸藏 | [@op7418](https://x.com/op7418) | 公开名单候选 |

## 尚缺个人账号

- 马化腾 / Pony Ma：此前官网只有公司账号；本轮不把公司账号当个人。
- Jensen Huang：Prometheans目录将其X指向nvidia公司账号，拒绝当个人账号。
- Mark Zuckerberg：两份人物目录所给账号不一致且无一手支持，保留待查。
- Richard Sutton：本轮学术主页未找到个人X链接；不影响其他人物名单入库。
- Kaiming He：本轮学术主页未找到个人X链接；不影响其他人物名单入库。
