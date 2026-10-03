# 网站部署手册

截至 2026-10-03 尚未执行首次发布。本文是操作说明，不记录已完成的部署。设计依据见[部署与 SEO/GEO 设计](../superpowers/specs/2026-10-03-seo-geo-deployment-design.md)，安全边界见 [SECURITY.md](../../SECURITY.md)。

## 1. 概览

- 在本机构建，只上传渲染好的页面。数据快照（`datasets/published/latest/`）不离开本机。发布目录由白名单组装，上传前再扫描一遍，含 `.env*`、密钥、数据库、`datasets/`、`data/`、`local/`、`docs/`、`scripts/` 等路径即中止。
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
- 磁盘：一个版本约 550 MB（含预渲染页面）。服务器保留最新 5 个加 `current`/`previous`，目录合计约 3 GB，另有 Docker 镜像。发布前检查：

```bash
ssh -i <密钥> <用户>@<地址> df -h /
```

预期：剩余空间明显大于 3 GB。

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

预期，依次发生：校验快照与 `manifest.json` 一致；运行 `pnpm check`（含构建）；组装 `.release/<id>/`；在本机端口 8399 起服务并跑冒烟检查；清除服务器上旧的 `candidate`；rsync 上传；以候选槽位启动并等待健康；最后打印预览命令。`release` 不碰正式服务。失败时终止并给出原因，常见的是快照不完整、`pnpm check` 失败、冒烟检查失败、发布目录含禁止文件。

按打印的命令开 SSH 隧道预览：

```bash
ssh -i <密钥> -N -L 8321:127.0.0.1:8321 <用户>@<地址>
```

预期：命令不返回（保持隧道）；浏览器打开 `http://localhost:8321`，英文和中文（`/zh-CN`）在桌面和手机宽度下各看一遍。

```bash
pnpm site:promote
```

预期：校验候选仍健康；把它启动为正式服务；成功后打印 `production is now <id>`，关闭候选，清理超出保留数的旧版本（保留最新 5 个，`current` 与 `previous` 受保护）；随后对 `https://openaiwill.com` 做公开冒烟检查（`/healthz` 报告新版本号、语言跳转、404、sitemap 中各类页面各一页、正式环境不带 `X-Robots-Tag`），通过后向 IndexNow 提交 sitemap 中的地址并打印状态码。

只想验证构建而不上传：

```bash
pnpm site:build
```

预期：以 `built <id> at .release/<id>` 结束。

### 失败时会发生什么

- `release` 从不改动正式服务。
- `promote` 若新版本没有变健康，会把原来在线的版本重新启动，并输出 `production restored to <id>`；`current` 不变。首次发布（此前没有在线版本）失败时没有可恢复的对象，输出 `there was no earlier release to restore`。
- `promote` 已切换但公开检查失败（常见原因：Tunnel 主机名尚未配好）：正式服务已在服务器上运行，命令报错并提示 `pnpm site:rollback`。若只是主机名未就绪，补好主机名即可，无需回滚；重新检查公开地址：

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
