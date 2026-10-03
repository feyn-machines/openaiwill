# 网站部署手册

截至 2026-10-03 尚未执行首次发布。本文是操作说明，不记录已完成的部署。设计依据见[部署与 SEO/GEO 设计](../superpowers/specs/2026-10-03-seo-geo-deployment-design.md)，安全边界见 [SECURITY.md](../../SECURITY.md)。

## 1. 概览

- 在本机构建，只上传渲染好的页面。数据快照（`datasets/published/latest/`）不离开本机。发布目录由白名单组装，上传前再扫描一遍：发布目录 `app/` 下直接出现 `datasets`、`data`、`local`、`docs`、`design`、`db`、`scripts` 等私有目录，或任何位置出现 `.env*`、密钥、数据库、cookies 之类的私有文件名，即中止（`node_modules` 内不扫文件名）。另外，发布目录中出现 `sharp`/`@img` 这类为构建机编译的原生二进制也会中止；`next.config.ts` 已关闭图片优化器（没有页面使用它），避免 `/_next/image` 在服务器容器里报错。
- 服务器：Ubuntu 24.04 x86_64，装有 Docker；防火墙只放行 SSH，80/443 关闭；所有入站流量经现有的 Cloudflare Tunnel（`cloudflared`，令牌方式，路由在 Cloudflare 后台配置）。
- 服务器地址、用户、密钥文件只写在本机被忽略的 `.env.deploy`，不进任何受版本控制的文件。
- 服务器上每个版本一个目录：`<DEPLOY_ROOT>/releases/<id>/`（默认 `/opt/openaiwill`）。目录旁有状态文件 `current`、`previous`、`candidate`，各存一个版本号。
- 两个 Compose 项目，各自只绑定 `127.0.0.1`：

| 槽位 | Compose 项目 | 端口 | `SITE_ENV` | 说明 |
| --- | --- | --- | --- | --- |
| 正式 | `openaiwill` | 8320 | `production` | Tunnel 指向这里 |
| 候选 | `openaiwill-next` | 8321 | `preview` | 只能经 SSH 隧道预览，页面带 `X-Robots-Tag: noindex` |

- 版本号格式：`<快照 generated_at（UTC，YYYYMMDDTHHMMSSZ）>-<git 短哈希>`；跟踪文件有未提交修改时加 `-dirty`。要可复现的发布，先提交再发布。
- 正式地址（canonical）是 `https://openaiwill.com`，不带 www。
- 官方账号：X `https://x.com/openaiwill`，Discord `https://discord.gg/ArVHw2K9X`，GitHub `https://github.com/feyn-machines/openaiwill`。每个页面的页眉页脚和 `llms.txt` 已链接它们。

## 2. 首次准备

### 本机

```bash
cp deploy/deploy.env.example .env.deploy
```

编辑 `.env.deploy`，填 `DEPLOY_HOST`、`DEPLOY_USER`、`DEPLOY_SSH_KEY`（私钥路径，密钥本身留在 `~/.ssh`）、`DEPLOY_ROOT`。预期：`git status` 不列出 `.env.deploy`。

### 服务器要求

- 部署用户能无密码执行 `sudo docker`（脚本用 `sudo` 加环境变量调用）。
- `docker compose` 为 v2，并装有 `curl`。
- 磁盘：一个版本约 550 MB（含预渲染页面）。服务器上最多同时有 7 个版本目录（最新 5 个，加 `current` 和 `previous`），约 3.9 GB；Docker 镜像再占同样的量；另有构建缓存，以及失败或未提升的版本目录（`promote` 只清理超出保留数的旧目录，不清理它们）。预留 10 GB。发布前检查：

```bash
ssh -i <密钥> <用户>@<地址> df -h /
```

预期：剩余空间明显大于 10 GB。

例行清理（每次发布后或磁盘紧张时）：

```bash
ssh -i <密钥> <用户>@<地址> 'sudo docker builder prune -f'
```

没有被提升的版本目录（`release` 失败或候选被放弃）不会自动清理，确认它不是 `current`、`previous`、`candidate` 后手工删除，并删除对应镜像：

```bash
ssh -i <密钥> <用户>@<地址> 'rm -rf <DEPLOY_ROOT>/releases/<id>; sudo docker image rm -f openaiwill-web:<id>'
```

### 确认连通

```bash
pnpm site:status
```

预期：首次为 `current: none`，`previous: none`，`candidate: none`，没有名称含 `openaiwill` 的容器。

### Cloudflare（需要本人在后台操作，脚本不做）

服务器 80/443 关闭，把域名用 A 记录指向服务器 IP 不会生效。地址必须是 Tunnel 的公开主机名。

1. 确认 `openaiwill.com` 的 DNS 托管在运行这条 Tunnel 的同一个 Cloudflare 账号下；不在则先把域名的 NS 改过去。
2. 在 Tunnel 中添加公开主机名 `openaiwill.com` → `http://localhost:8320`，以及 `www.openaiwill.com` → 同一地址。Cloudflare 自动建立 CNAME，不要手工加 A 记录。
3. 加重定向规则：`www.openaiwill.com` 永久（301）跳转到 `https://openaiwill.com`。
4. 关闭"阻止 AI 爬虫"（Block AI bots）和托管的 `robots.txt`。开着会覆盖站点自己的爬虫规则，GEO 部分的工作等于白做。
5. 不缓存 HTML：不要开启"Cache Everything"。语言跳转和新版本生效都依赖源站响应；源站对预渲染的 HTML 发很长的 `s-maxage`，被边缘缓存后无法即时更新。只缓存 `/_next/static/`（默认如此）。

## 3. 发布

```bash
pnpm data:publish:snapshot
```

预期：写出 `datasets/published/latest/`。数据有更新时才需要重做。

```bash
pnpm site:release
```

预期，依次发生：校验快照与 `manifest.json` 一致；运行 `pnpm check`（含构建）；组装 `.release/<id>/`；确认发布目录不含 `sharp`/`@img` 和禁止文件；在本机端口 8399 先以 `SITE_ENV=preview` 起服务，跑冒烟检查并确认页面带 `X-Robots-Tag: noindex`，再以 `SITE_ENV=production` 起一次，确认 `/markets` 返回 200 且没有 `X-Robots-Tag`（上线前就证明正式环境可被索引）；清除服务器上旧的 `candidate`；rsync 上传；以候选槽位启动并等待健康；随后开一条 SSH 本地转发（本机空闲端口 → 服务器 `127.0.0.1:8321`），对候选跑同一套冒烟检查并确认带 `noindex`，通过后才写入 `candidate` 文件并关闭转发；最后打印预览命令。`release` 不碰正式服务。候选冒烟失败时，不写 `candidate`（`promote` 因而拒绝它），候选容器留在服务器上供检查，命令列出失败项。其他常见失败：快照不完整、`pnpm check` 失败、本机冒烟失败、发布目录含禁止文件或原生二进制。

按打印的命令开 SSH 隧道预览：

```bash
ssh -i <密钥> -N -L 8321:127.0.0.1:8321 <用户>@<地址>
```

预期：命令不返回（保持隧道）；浏览器打开 `http://localhost:8321`，英文和中文（`/zh-CN`）在桌面和手机宽度下各看一遍。

```bash
pnpm site:promote
```

预期：校验候选仍健康；把它启动为正式服务并确认健康；成功后记录 `previous` 和 `current`，打印 `production is now <id>`，关闭候选，清理超出保留数的旧版本（保留最新 5 个，`current` 与 `previous` 受保护）；随后对 `https://openaiwill.com` 做公开冒烟检查（请求带 `User-Agent: openaiwill-release/1.0`；`/healthz` 报告新版本号、语言跳转、客户端导航请求、IndexNow 密钥文件、404、sitemap 中各类页面各一页、正式环境不带 `X-Robots-Tag`），通过后向 IndexNow 提交 sitemap 中的地址并打印状态码。公开地址解析不到或连不上时，检查结果只列出一行 `<地址> is not reachable: <原因>`。

只想验证构建而不上传：

```bash
pnpm site:build
```

预期：以 `built <id> at .release/<id>` 结束。

### 失败时会发生什么

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

## 4. 回滚与状态

```bash
pnpm site:rollback
```

预期：把 `previous` 记录的版本重新作为正式服务启动，打印 `production is back on <id>`。新版本没有变健康时同样会恢复回滚前的版本。没有 `previous` 时报 `there is no previous release to roll back to`。

```bash
pnpm site:status
```

预期：打印 `current`、`previous`、`candidate`、服务器上的版本目录列表，以及名称含 `openaiwill` 的容器。

## 5. 上线后

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

## 6. 每月检查

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
