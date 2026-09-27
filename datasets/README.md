# Official AI update sources

Official company and product X posts are the primary evidence for AI progress records. A company can have multiple company, model, product, developer, research, platform and newsroom accounts. Do not deduplicate accounts by company or impose a one-account-per-company limit.

Checked on 2026-09-11: **13 companies, 51 enabled accounts and 8 held records**. Google and Chinese companies are included; Baidu / ERNIE is excluded by project decision. This is an extensible verified set, not a complete global census.

The [2026-09-12 metadata reconfirmation](../docs/data/metadata-reconfirmation-2026-09-12.md) consolidates current counts, source versions and pending work. Its [machine audit](evidence/metadata-reconfirmation-2026-09-12.json) checks current dataset consistency separately from the legacy frontend metadata checker; it does not claim fresh X profile verification.

The later [work-reference collection](../docs/data/work-reference-collection-2026-09-12.md) adds the complete O*NET 31.0 archive (1,016 occupations, 18,838 tasks), all 20 O*NET industry exports and the complete ISIC Rev.5 structure with explanatory notes. [Reference metadata](work-reference.v1.json) records counts, versions, local paths and checksums. Full data stays under ignored `data/reference/work-taxonomy/2026-09-12/`. This collection does not replace the a16z nine-industry reference or constitute a finished delivery-scenario catalog.

- [Account registry](official-x-accounts.json): a collector-compatible array with identity, scope, status and sources.
- [Readable directory](../docs/data/official-x-accounts.md): all enabled accounts grouped by company.
- [Coverage gaps](official-x-account-gaps.json): five pending, one partially resolved and one resolved scope.
- [Profile observations](evidence/x-account-profile-checks-2026-09-11.json): includes discovery candidates and unsuccessful attempts; observations alone are not verification.
- [Official X relationships](evidence/x-account-relationships-2026-09-11.json): explicit product references and organizational affiliations.

An enabled account needs a matching current numeric X user ID plus a first-party outbound link, an explicit introduction by an already verified official X account, or an X organizational affiliation pointing to a verified parent account. [X documents organizational affiliations here](https://help.x.com/en/using-x/premium-business). Ordinary checkmarks, lookalike names, employee affiliation or mere mentions do not independently establish an official company/product account.

`official_link_unresolved` retains official identity evidence when the current user lookup did not resolve. `current_official_link_unverified` retains a candidate whose present official association is not established. Both are disabled. Discovery evidence is kept separate from identity evidence. Website references preserve exact observed URLs; main handles use X's returned spelling. IDs are strings to avoid integer precision loss.

The collector currently reads `handle` and `enabled` only. Match post author IDs against the registry before accepting normalized events. Report queried and missing coverage per account. Deduplicate repeated announcements at the event level while retaining every original official post as evidence. Current identity does not prove complete ownership history, the truth of every post, or collection completeness.

No credentials, private submissions or full social-media archives are included here. The earlier product-market directory is reference material, not an AI-progress percentage denominator.

V1 industry provenance follows [a16z-industry-reference.v1.json](a16z-industry-reference.v1.json): all nine original industry groups in the a16z GDPval chart are retained without splitting. Translations remain separate; no weights or capability scores are inferred from the chart. The [app-spending reference](a16z-market-reference.v1.json) preserves 50 ranks as separate product research and is not merged into the industry directory. See the [source baseline](../docs/data/a16z-source-baseline-v1.md). The 20 editorial product markets and 13/16 AI-proposed world groups are not original a16z classifications.

## Planned event knowledge base

The core output is a 0–100 estimate of progress toward AI independently completing major production and service work. The [simulation model](../docs/data/takeover-simulation-v0.3.md) and [v0.3 contract](takeover-simulation.v0.3.json) define 100 total weight points, AI-estimated three-scenario states and event-triggered updates. Initial AI estimates are allowed when labeled; no production world scope, weights or baseline has been generated yet.

The [observation framework](../docs/data/takeover-progress-framework-v1.md) and [v0.2 configuration](takeover-methodology.v0.2.json) remain the input layer for raw events, metrics and community signals. Company adoption adds its own linked records, with account badge, company identity, adoption stage and provider relationship kept distinct. The v0.1 manual four-dimension rubric remains superseded. No simulation or signal-scoring engine is running.

[Field verification](evidence/social-metric-field-probe-2026-09-12.json) records the earlier limited probe. The subsequent [collection pilot](../docs/data/collection-and-simulation-pilot-2026-09-12.md) fixes the local normalizer: X interactions are retained and Reddit missing counts remain null. All 57 retained X posts in that batch returned views; repeated metric freshness is still unverified.

The [v1 data design](../docs/data/ai-progress-knowledge-graph-v1.md) connects those states and changes to entities, events, attributed statements, evidence versions, availability and impact observations. It supports a progress graph and a [weekly WeChat brief](../docs/data/weekly-wechat-template.md) from the same reviewed records. Statements from important people require a separate verified source list; personal comments do not automatically become official company positions.

The proposed local store is SQLite with raw collection material under the ignored root `data/` directory. Work is forward-only; historical collection is not enabled. An event database, automatic inference engine, recurring collection, community intake and automatic publishing remain unimplemented.

## First collection and simulation pilot

The current [people watchlist](ai-people-watchlist.json) has expanded beyond the initial seven-person sample by importing and deduplicating existing public lists. See the [list sources and readable roster](../docs/research/ai-people-x-lists-2026-09-12.md). List discovery, first-party identity links and live numeric-ID checks remain separate statuses.

[2026-09-12 report](../docs/data/collection-and-simulation-pilot-2026-09-12.md): 57 official X posts and 30 Reddit posts retained; 48 of 51 account queries completed before a 429 stop. Thirteen relevant event groups and two adopter-confirmation records are linked to source metadata. The [initial seven-person sample](person-source-candidates-2026-09-12.json) remains a historical artifact; the current watchlist contains 157 candidate handles, all disabled pending numeric-ID verification.

The [historical AI-proposed scope and estimates](takeover-pilot-2026-09-12.scope-v2.json) produce [24.28, with scenarios 9.73–40.91](evidence/takeover-pilot-result-2026-09-12.scope-v2.json). This self-designed classification is superseded for v1 by the source-preserving policy above. The [revision ledger](evidence/takeover-scope-revision-2026-09-12.json) preserves the original 24.38 result. Both are unpublished, prior-dominated simulations, not a16z data or measured worldwide capability shares. Production scores remain null. [The calculator](../scripts/simulate-takeover-pilot.py) sums explicit estimates without automatic inference.
