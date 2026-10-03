# 网站部署手册

截至 2026-10-03 尚未执行首次发布。本文是操作说明，不记录已完成的部署。设计依据见[服务器数据库与数据发布设计](../superpowers/specs/2026-10-03-server-database-and-data-releases-design.md)（取代 [SEO、GEO 与部署设计](../superpowers/specs/2026-10-03-seo-geo-deployment-design.md) 中"数据不离开本机、全站预生成"的部分），安全边界见 [SECURITY.md](../../SECURITY.md)。

## 1. 概览

发布分两条独立的线，各有各的命令、版本号和回滚：

| | 发布代码 | 发布数据 |
| --- | --- | --- |
| 发布什么 | 网站程序（不含任何数据） | `datasets/published/latest/` 里处理好的快照，作为数据库中的一个不可变版本 |
| 命令 | `pnpm site:release` → `pnpm site:promote` | `pnpm data:release` → `pnpm data:promote` |
| 回滚 | `pnpm site:rollback` | `pnpm data:rollback` |
| 查看 | `pnpm site:status` | `pnpm data:releases` |
| 版本号 | `<构建时间 UTC，YYYYMMDDTHHMMSSZ>-<git 短哈希>`；跟踪文件有未提交修改时加 `-dirty` | `<快照生成时间 UTC>-<内容哈希前 8 位>` |
| 生效方式 | 候选容器通过检查后切换正式容器 | 写入数据库的生效指针；网站每 30 秒查一次，不需要重新发布代码 |

网站启动时从数据库读取当前生效的数据版本，数据库里没有已生效的数据版本，网站不会启动（两个槽位都带 `SITE_REQUIRE_DATABASE=1`）。所以首次上线必须先发布数据，再发布代码。

### 服务器上有什么、没有什么

- 有：网站的代码发布目录（几十 MB，不含数据）、PostgreSQL 数据库（只放已发布的数据，schema `kg`）、两个环境文件（口令）。
- 没有：原始抓取档案、采集程序及其登录/代理状态、重试状态、本机处理过程中的中间数据、本机数据库。采集和处理一直在本机运行；`pnpm data:release` 只把处理好的发布快照写进服务器数据库。
- 以后的用户数据（账号、API Key、Agent 上报）放在单独的 schema，只通过 `kg.entities` 的稳定标识引用知识数据；数据发布永远不写它。这次没有建。

### 服务器与槽位

- 服务器：Ubuntu 24.04 x86_64，装有 Docker Compose v2；防火墙只放行 SSH，80/443 关闭；所有入站流量经现有的 Cloudflare Tunnel（`cloudflared`，令牌方式，路由在 Cloudflare 后台配置）。
- 服务器地址、用户、密钥文件只写在本机被忽略的 `.env.deploy`，不进任何受版本控制的文件。口令不在本机任何位置。
- 服务器上每个代码版本一个目录：`<DEPLOY_ROOT>/releases/<id>/`（默认 `/opt/openaiwill`）。目录旁有状态文件 `current`、`previous`、`candidate`，各存一个版本号。
- 网站容器和数据库容器在同一个 Docker 网络 `openaiwill` 里，网站用名字 `openaiwill-db` 访问数据库。
- 三个 Compose 项目，各自只绑定 `127.0.0.1`：

| 项目 | Compose 项目 | 端口 | `SITE_ENV` | 说明 |
| --- | --- | --- | --- | --- |
| 正式站 | `openaiwill` | 8320 | `production` | Tunnel 指向这里 |
| 候选站 | `openaiwill-next` | 8321 | `preview` | 只能经 SSH 隧道预览，页面带 `X-Robots-Tag: noindex` |
| 数据库 | `openaiwill-db` | 5434 | 无 | 只能经 SSH 转发访问 |

- 正式地址（canonical）是 `https://openaiwill.com`，不带 www。
- 官方账号：X `https://x.com/openaiwill`，Discord `https://discord.gg/ArVHw2K9X`，GitHub `https://github.com/feyn-machines/openaiwill`。每个页面的页眉页脚和 `llms.txt` 已链接它们。

## 2. 首次准备

### 本机

```bash
cp deploy/deploy.env.example .env.deploy
```

编辑 `.env.deploy`，填 `DEPLOY_HOST`、`DEPLOY_USER`、`DEPLOY_SSH_KEY`（私钥路径，密钥本身留在 `~/.ssh`）、`DEPLOY_ROOT`。预期：`git status` 不列出 `.env.deploy`。本机还需要 `rsync` 和已执行过 `pnpm data:setup`（数据发布用本机的 Python 环境）。

### 服务器要求

- 部署用户能无密码执行 `sudo`（脚本用 `sudo` 调用 Docker）。
- `docker compose` 为 v2，并装有 `curl` 和 `openssl`。
- 端口 8320、8321、5434 空闲。
- 磁盘：一个代码版本目录约几十 MB；服务器上最多同时有 7 个版本目录（最新 5 个，加 `current` 和 `previous`），Docker 镜像再占数倍；另有构建缓存，以及失败或未提升的版本目录（`promote` 只清理超出保留数的旧目录，不清理它们）。数据库占用见第 7 节。预留 5 GB。发布前检查：

```bash
ssh -i <密钥> <用户>@<地址> df -h /
```

预期：剩余空间明显大于 5 GB。

例行清理（每次发布后或磁盘紧张时）：

```bash
ssh -i <密钥> <用户>@<地址> 'sudo docker builder prune -f'
```

没有被提升的版本目录（`release` 失败或候选被放弃）不会自动清理，确认它不是 `current`、`previous`、`candidate` 后手工删除，并删除对应镜像：

```bash
ssh -i <密钥> <用户>@<地址> 'rm -rf <DEPLOY_ROOT>/releases/<id>; sudo docker image rm -f openaiwill-web:<id>'
```

### Cloudflare（需要本人在后台操作，脚本不做）

服务器 80/443 关闭，把域名用 A 记录指向服务器 IP 不会生效。地址必须是 Tunnel 的公开主机名。

1. 确认 `openaiwill.com` 的 DNS 托管在运行这条 Tunnel 的同一个 Cloudflare 账号下；不在则先把域名的 NS 改过去。
2. 在 Tunnel 中添加公开主机名 `openaiwill.com` → `http://localhost:8320`，以及 `www.openaiwill.com` → 同一地址。Cloudflare 自动建立 CNAME，不要手工加 A 记录。（服务器上的 Tunnel 已按此配置；这一步只在重建时需要。）
3. 加重定向规则：`www.openaiwill.com` 永久（301）跳转到 `https://openaiwill.com`。
4. 关闭"阻止 AI 爬虫"（Block AI bots）和托管的 `robots.txt`。开着会覆盖站点自己的爬虫规则，GEO 部分的工作等于白做。
5. 不缓存 HTML：不要开启"Cache Everything"。语言跳转依赖源站响应，页面按请求渲染，数据发布后约 30 秒内变化；被边缘缓存的 HTML 无法即时更新。只缓存 `/_next/static/`（默认如此）。

## 3. 首次上线顺序

数据库和数据必须先于网站：候选站启动时就要从数据库读到一个已生效的数据版本。

```bash
pnpm db:setup
```

预期：在服务器上建目录 `<DEPLOY_ROOT>/db`，建 Docker 网络 `openaiwill`，首次生成三个口令并写入两个环境文件（输出 `generated the database passwords on the server` 和 `wrote site.env`，不显示口令），启动数据库，建两个角色、数据库 `openaiwill` 和 schema `kg`，最后以两个角色的口令各连一次，打印 `both roles connect with their passwords; releases in kg: 0` 和 `database ready`。可重复执行：环境文件已存在时不会重新生成口令。

```bash
pnpm data:publish:snapshot
pnpm data:release
pnpm data:promote
```

预期：`data:release` 打印 `release <id> imported and verified`、与当前生效版本相比各集合的新增/变化/移除行数（首次是 `nothing (no active release)`）和 `not live yet`；`data:promote` 打印 `active release: <id>`，随后因为服务器上还没有网站，打印 `no production site is running yet`。

```bash
pnpm site:release
```

预期：见第 4 节；候选读到刚生效的数据版本并通过检查。然后按打印的命令预览（`ssh -N -L 8321:127.0.0.1:8321 ...`，打开 `http://localhost:8321`，英文和中文在桌面和手机宽度下各看一遍），再：

```bash
pnpm site:promote
```

最后做公网检查和通知搜索引擎（第 8 节）。

## 4. 发布代码

```bash
pnpm site:release
```

预期，依次发生：运行 `pnpm check`（含构建）；组装 `.release/<id>/`（不含数据）；确认发布目录不含 `sharp`/`@img` 和禁止文件；在本机端口 8399 先以 `SITE_ENV=preview` 起服务跑冒烟检查并确认页面带 `X-Robots-Tag: noindex`——本机有快照目录（`datasets/published/latest/`）时服务以文件模式读它（`SNAPSHOT_DIR`，数据留在发布目录之外）并跑完整检查，没有快照时只跑不需要数据的子集（固定页面、跳转、404、`robots.txt`、`llms.txt`）——再以 `SITE_ENV=production` 起一次，确认 `/markets` 返回 200 且没有 `X-Robots-Tag`（上线前就证明正式环境可被索引）；这两次都不带数据库；清除服务器上旧的 `candidate`；rsync 上传；以候选槽位启动并等待健康；随后开一条 SSH 本地转发（本机空闲端口 → 服务器 `127.0.0.1:8321`），对候选跑完整冒烟检查，并要求 `/healthz` 报告 `data.source` 为 `database` 且有数据版本号、页面带 `noindex`，通过后写入 `candidate` 文件、关闭转发，打印候选正在使用的数据版本和预览命令。`release` 不碰正式服务。

候选没有变健康：脚本取回候选的 `/healthz` 内容；如果显示没有加载任何数据版本，报 `publish data first: pnpm data:release && pnpm data:promote`——先发布数据，再重新运行 `pnpm site:release`。候选冒烟失败时，不写 `candidate`（`promote` 因而拒绝它），候选容器留在服务器上供检查，命令列出失败项。其他常见失败：`pnpm check` 失败、本机冒烟失败、发布目录含禁止文件或原生二进制。

```bash
pnpm site:promote
```

预期：校验候选仍健康；把它启动为正式服务并确认健康；成功后记录 `previous` 和 `current`，打印 `production is now <id>`，关闭候选，清理超出保留数的旧版本（保留最新 5 个，`current` 与 `previous` 受保护）；随后对 `https://openaiwill.com` 做公开冒烟检查（请求带 `User-Agent: openaiwill-release/1.0`；`/healthz` 报告新版本号、语言跳转、客户端导航请求、IndexNow 密钥文件、404、sitemap 中各类页面各一页、正式环境不带 `X-Robots-Tag`），通过后向 IndexNow 提交 sitemap 中的地址并打印状态码。公开地址解析不到或连不上时，检查结果只列出一行 `<地址> is not reachable: <原因>`。

只想验证构建而不上传：

```bash
pnpm site:build
```

预期：以 `built <id> at .release/<id>` 结束。

```bash
pnpm site:status
```

预期：打印 `current`、`previous`、`candidate`、服务器上的版本目录列表、名称含 `openaiwill` 的容器，以及两行 `production slot (:8320): code <id>, data <数据版本> (database)` 和 `candidate slot (:8321): ...`；槽位没有运行时为 `not running`。

### 发布代码失败时会发生什么

- `release` 从不改动正式服务。
- `promote` 若新版本没有变健康：`current` 不变，并按情况输出：
  - 此前有在线版本：重新启动它并输出 `production restored to <id>`；重启也失败则输出 `RESTORE FAILED: production is down`（此时正式服务已停，需要立即处理）；原版本目录已不存在则输出 `RESTORE FAILED: production is down; <id> is gone`。
  - 要提升的版本就是当前在线版本：输出 `<id> did not become healthy; it is still the current release`，不输出 restored。
  - 首次发布（此前没有在线版本）：先停掉这个不健康的版本占用的正式槽位，再输出 `no earlier release to restore; production slot stopped`，避免它带着 `restart: unless-stopped` 一直占着端口。
- `promote` 已切换但公开检查失败（常见原因：Tunnel 主机名或 DNS 尚未配好）：报错信息以 `production IS switched to <id> and healthy on the server` 开头并列出失败项。纯连通性失败时提示修好 Tunnel/DNS 后运行 `pnpm site:indexnow`，不要回滚；若失败项是页面内容问题，才考虑 `pnpm site:rollback`。IndexNow 在检查失败时不会被调用，修好后单独运行：

```bash
pnpm site:indexnow
```

预期：打印 `IndexNow: <状态码> for <n> addresses`。要再次检查公开地址，可用：

```bash
python3 -c "import sys; sys.path.insert(0,'scripts'); import site_release as r; print(r.smoke(r.SITE_URL, None))"
```

预期：打印 `[]` 表示全部通过，否则列出失败项。

## 5. 发布数据

数据流：本机管线 → `pnpm data:publish:snapshot` → `pnpm data:release` → `pnpm data:promote`。三步都在本机运行；`release` 和 `promote` 经 SSH 转发（本机空闲端口 → 服务器 `127.0.0.1:5434`）连接数据库，转发每次用完关闭。数据库的写入角色口令从服务器的 `<DEPLOY_ROOT>/db/db.env` 读入内存，不显示、不写盘。

```bash
pnpm data:release
```

预期：把 `datasets/published/latest/` 在一个事务里导入为新版本，从数据库重新拼出整份数据并核对内容哈希，通过后标为 `verified`；打印新增文档数、与当前生效版本相比各集合的新增（`+`）、变化（`~`）、移除（`-`）行数，最后打印 `not live yet`。内容相同的快照再次发布是空操作（`already imported; nothing new`）。此时线上不变。

```bash
pnpm data:promote
```

预期：让最新的 `verified` 版本生效，打印 `active release: <id>`；随后通过 SSH 转发访问正式站 `/healthz`，最多等 60 秒，报告 `production site now serves data release <id>`（网站每 30 秒查一次生效指针，所以通常要等十几到三十秒）；超过 60 秒仍是旧版本则打印 `WARNING: ...`（数据库里已经生效，网站仍在重试读取，用 `pnpm site:status` 再看）；服务器上还没有正式站时打印 `no production site is running yet`，命令仍以状态 0 结束。

```bash
pnpm data:releases
```

预期：`active: <id>`，每个版本一行（`*` 标记生效版本、状态、行数、导入时间），并打印正式站当前加载的数据版本。

`pnpm data:local:release` 和 `pnpm data:local:promote` 对本机数据库做同样的事，用于开发和测试。

## 6. 回滚

### 代码

```bash
pnpm site:rollback
```

预期：把 `previous` 记录的版本重新作为正式服务启动，打印 `production is back on <id>`。新版本没有变健康时同样会恢复回滚前的版本。没有 `previous` 时报 `there is no previous release to roll back to`。回滚代码不影响数据版本。

### 数据

```bash
pnpm data:rollback
```

预期：让上一个生效过的数据版本重新生效，打印 `active release: <id>` 并等待正式站报告它；约 30 秒内网站读到。连续运行两次会回到原来的版本。回滚数据不影响代码版本，也不删除任何数据版本。

## 7. 数据库

- **位置**：服务器上的 Compose 项目 `openaiwill-db`，镜像 `postgres:16-alpine`，数据在命名卷里，只绑定服务器的 `127.0.0.1:5434`，加入 Docker 网络 `openaiwill`（容器名 `openaiwill-db`），`restart: unless-stopped`。文件在 `<DEPLOY_ROOT>/db/`（`compose.yml`、`roles.sql`、`001_kg.sql`、`grants.sql`、`db.env`），由 `pnpm db:setup` 从仓库的 `deploy/db/` 和 `db/published/001_kg.sql` 写入。
- **角色**：超级用户（容器默认的 `postgres`）只在 `pnpm db:setup` 里使用；`oaw_kg_writer` 是数据库 `openaiwill` 和 schema `kg` 的所有者，数据发布以它连接；`oaw_site` 只有 CONNECT、`kg` 的 USAGE 和 `kg` 内现有及以后新建的表与视图的 SELECT，没有别的权限。数据发布只写 `kg`。
- **口令在哪**：三个口令（超级用户、`oaw_kg_writer`、`oaw_site`）在服务器上生成，存在 `<DEPLOY_ROOT>/db/db.env`（权限 600）；`<DEPLOY_ROOT>/site.env`（权限 600）只含 `DATABASE_URL`（`oaw_site`，主机 `openaiwill-db`）。口令不进 Git，不在本机任何文件里，不在脚本输出里。丢失 `db.env` 而数据卷还在时，口令无法恢复；因为知识数据可以从本机重新发布，处理办法是在服务器上 `cd <DEPLOY_ROOT>/db && sudo docker compose -p openaiwill-db --env-file db.env down -v`（删除数据卷），删除 `db.env` 和 `site.env`，重新 `pnpm db:setup` 和 `pnpm data:release`/`pnpm data:promote`；用户数据出现之后这条路不再可用，需要先有备份。
- **备份**：知识数据可以从本机重新发布；用户数据出现之前不设定时备份。手动备份（超级用户经容器内的套接字连接，不需要口令；在本机运行，文件落在本机，注意它含全部已发布数据，不要提交）：

```bash
ssh -i <密钥> <用户>@<地址> 'sudo docker exec openaiwill-db pg_dump -U postgres -Fc openaiwill' > openaiwill-$(date +%Y%m%d).dump
```

预期：生成一个非空的 `.dump` 文件。恢复到一个已经执行过 `pnpm db:setup` 的数据库：

```bash
ssh -i <密钥> <用户>@<地址> 'sudo docker exec -i openaiwill-db pg_restore -U postgres -d openaiwill --clean --if-exists' < openaiwill-<日期>.dump
```

预期：无错误退出；`pnpm data:releases` 列出备份时的版本。恢复期间网站继续使用内存里已加载的版本。
- **占用**：

```bash
ssh -i <密钥> <用户>@<地址> 'sudo docker exec openaiwill-db psql -U postgres -d openaiwill -tAc "SELECT pg_size_pretty(pg_database_size(current_database()))"'
ssh -i <密钥> <用户>@<地址> 'sudo docker system df'
```

预期：第一条打印数据库大小。各版本共享相同内容的行，所以每次发布只增加新增或变化的行。
- **数据库不可用时**：网站启动时连不上数据库会启动失败，候选检查不通过，不会被切到正式；已经在运行的网站继续使用内存里已加载的版本。

## 8. 上线后

以下需要本人的账号。

1. Google Search Console：添加 `openaiwill.com` 域名资源，用 DNS TXT 记录验证；在"站点地图"提交 `https://openaiwill.com/sitemap.xml`。
2. Bing Webmaster Tools：同样用 DNS TXT 验证并提交该 sitemap。
3. 确认 AI 爬虫未被 Cloudflare 拦截：

```bash
curl -sI https://openaiwill.com/ | grep -i -E '^(HTTP|x-robots-tag)'
curl -sI 'https://openaiwill.com/markets?lang=zh-CN' | grep -i '^location'
curl -s -o /dev/null -w '%{http_code}\n' -A GPTBot https://openaiwill.com/
curl -s -o /dev/null -w '%{http_code}\n' -A ClaudeBot https://openaiwill.com/llms.txt
curl -s https://openaiwill.com/robots.txt | head -5
```

预期：依次为 `200` 且没有 `x-robots-tag`；`location: /zh-CN/markets`；`200`；`200`；本站生成的 `robots.txt`（含 `Sitemap:`），不是 Cloudflare 托管的版本。爬虫 UA 返回 403，或 `robots.txt` 不是本站的，说明 Cloudflare 的 AI 爬虫设置仍开着。
4. Google 富媒体结果测试：检查首页和一个更新页（`/updates/<id>`），预期结构化数据无错误。
5. 爬虫抓取量看 Cloudflare 后台的流量与机器人报表，不另外部署统计。

## 9. 每月检查

每月向 ChatGPT、Claude、Perplexity、Gemini 各问下面十个问题，记录 openaiwill 是否被引用、引用是否准确。这是起始清单，由负责人按需调整。

```
How far has AI come in doing accounting work on its own?
Which kinds of work can AI already complete without a person?
What can AI do today in a software developer's job, task by task?
Is there a site that tracks AI progress by occupation with sources?
What does "L3 conditional automation" mean for a kind of work?
AI 现在能独立完成哪些工作？
AI 对会计这个职业的各项任务做到了什么程度？
有没有按职业和任务追踪 AI 进展并给出来源的网站？
最近哪些 AI 更新改变了某类工作的自动化程度？
openaiwill 是什么？
```
