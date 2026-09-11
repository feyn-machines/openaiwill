# WillAI / AgentHowTo

**Will AI Kill Your Idea?**  
Every AI update could change your answer.  
每一次 AI 更新，都可能改变你的创业判断。

## Run locally

Requires Node.js 22+ and pnpm 10.28.2.

```sh
pnpm install
pnpm dev
```

Open http://localhost:3000.

```sh
pnpm lint
pnpm typecheck
pnpm build
pnpm start
```

## Current scope

Next.js App Router, TypeScript, plain responsive CSS. Routes: `/`, `/check`, `/updates`.
The checker and update feed are explicitly marked as not connected. No model calls, scraping, database, authentication, notifications, or deployment are configured.

## Product direction

Check an idea against evidence of shipped AI capabilities, then track official updates that change the assessment. Public brand: AgentHowTo. Intended hostname: `www.agenthowto.com` (DNS and deployment are not configured).

- Separate official announcements from editorial judgments.
- Assess a specific customer, task, and value proposition, not entire industries.
- Public verdicts must include sources, dates, scope, and a correction history.
- Idea submissions are private by default; do not publish them as SEO pages.
- Future content routes: `/ideas/[slug]`, `/updates/[slug]`, `/categories/[slug]`.
- Configure canonical URLs, sitemap and social metadata against the actual hostname before publishing. Do not invent live verdicts for placeholder content.

## Next steps

1. Define the update/evidence/idea data model and editorial workflow.
2. Connect official sources with deduplication and review.
3. Add private idea checks and evidence-backed assessments.
4. Add tracked ideas and meaningful-change notifications.

## Product scope

Track AI coverage of commercial tasks through official evidence. The first release focuses on domains and leading AI companies, including Google, OpenAI, Anthropic and Chinese companies. Model companies, products, tasks, coverage records and releases separately. The current UI is an initial scaffold; the domain/company catalog and detail pages remain to be implemented.

## Languages

English is the default. Current pages render on the server using the browser's `Accept-Language` preference, respecting quality weights. Chinese preferences receive Simplified Chinese; unsupported languages fall back to English. This does not infer physical location. The English product headline remains the brand signature. Separate indexable locale URLs, manual language selection, and Traditional Chinese are future work.

## Open source and security

Licensed under MIT. Local agent instructions, skills, environments, credentials and collected data are excluded, including from the initial public history. See [SECURITY.md](SECURITY.md). CI validates public paths, common credential patterns, lint, types and build. No credentials are required to run the current scaffold.
