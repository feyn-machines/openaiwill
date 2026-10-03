# Model identification — design

Date: 2026-10-03. Status: proposed, not implemented.

## What the user asked for

- Collection and enrichment lack identification of the model and its version.
- The model is its own field, separate from products, because it is special.
- The field must answer three questions: which model and version moved a piece of work; what a model's release went on to reach; how the vendors' models compare over time.
- Data is to be supplemented from 2026-08-22 up to 2026-10-03 00:00, covering re-collection, extraction and model identification.
- Identification runs as a separate step after extraction (approach A below).

Assumed, not stated by the user: the cut-off is 00:00 Beijing time (2026-10-02T16:00Z).

## Why it is missing today

- `products`, `product_versions` and `event_products` were dropped by migration 020 with the capability layer.
- An update now carries only `subject_key`, a free-text slug the extraction model writes for deduplication.
- In the current snapshot 544 updates carry 511 distinct keys, 487 of them used once. GPT-6 Astra appears as `gpt-6-astra`, `gpt-6-astra-codex`, `gpt-6-astra-devin` and `gpt-6-astra-challenge-producthunt`.
- The site therefore cannot say which model an update is about, nor which work a model's release bears on.

## Scope

In scope: a model registry, a model field on every update, identification for new updates, backfill of the existing ones, snapshot export, and supplementing collection and extraction for 2026-08-22 to 2026-10-03.

Out of scope:

- Products (Codex, Copilot Cowork, Gemini Enterprise). They stay in `subject_key`. A product is never written to the model field.
- Any change to `subject_key`, `dedup_key` or event identity.
- Site pages. They follow once the data has been checked.
- Benchmarks scores, pricing and context sizes.

## Data model

Registry rows are instances and live in PostgreSQL, not in the ontology or semantic schema files.

`models`

| column | meaning |
| --- | --- |
| `model_id` | `model:<org>:<slug>`, e.g. `model:google:gemini-3-8-flash` |
| `org_id` | owner, references `org_registry`; null for an owner outside the registry |
| `owner_name` | the owner as the post writes it; filled when `org_id` is null |
| `level` | `family` (Gemini) or `release` (Gemini 3.8 Flash) |
| `parent_model_id` | the family of a release; null for a family |
| `name` | display name as the owner writes it |
| `version` | `3.8`; null for a family or when the owner gives none |
| `variant` | `Flash`, `Pro`, `mini`; null when there is none |
| `released_at` | from the owner's own release post; null when not observed |
| `status` | `candidate` or `confirmed` |
| `first_seen_event_id` | the update that introduced the row |

`model_aliases`: `alias` (normalised surface form), `model_id`. One alias resolves to one model.

`event_models`: the model field of an update. An update can name several models, so it is a table; the snapshot exports it as one `models` field per update.

| column | meaning |
| --- | --- |
| `event_id`, `model_id` | the pair |
| `role` | `subject`, `adopted`, `distributed`, `compared` |
| `mention` | the name exactly as the post wrote it |
| `confidence` | 0..1 from the identification pass |
| `run_id` | the identification run, with method version and prompt hash |

Roles:

- `subject`: the update releases or changes this model.
- `adopted`: someone else builds on or uses it.
- `distributed`: it becomes available on another platform.
- `compared`: it is named in a benchmark or comparison.

A post that says only "Gemini" links to the family row. The version is never guessed.

## Identification

A separate pipeline step, `scripts/data_pipeline/model_identification.py`, run after extraction. It does not touch the extraction prompt, so event identity and the recorded prompt hash stay as they are.

1. **Mention.** For each update the judge reads the title, summary and the full text of its source posts, and returns every model name verbatim with a role. It returns names only; it does not choose a registry row.
2. **Resolve.** A deterministic resolver normalises the mention and looks it up in `model_aliases`.
3. **Unmatched.** A mention with no alias creates a `candidate` model and alias. It is linked, and marked as candidate in the export.
4. **Confirm.** A candidate becomes `confirmed` when an update of kind `version_release` or `product_launch` from the owning organisation names it as `subject`. `released_at` is taken from that update.

Every row is machine-proposed and unreviewed, as the rest of the snapshot is.

Backfill: the same step run over the 581 stored updates from stored text. No collection is needed.

## Snapshot export

- `models.json`: the registry with status, owner, family, version, variant and release date.
- Each update in `events.json` gains `models: [{model_id, role, status}]`. An update that names no model carries an empty list, which is distinct from an update not yet processed (`models: null`).

## Checks

- Unit tests for the resolver (normalisation, alias collisions, family-only mentions, product names rejected). Dependency-free, part of `pnpm check`.
- PostgreSQL tests for the migration, idempotent re-runs and the confirmation rule, part of `pnpm data:test`.
- After backfill, a hand check of 50 sampled updates, and a report of: updates with at least one model, mentions resolved against existing aliases, candidates created, and distinct models per family.

## Approaches considered

- **A. Separate step after extraction (chosen).** Event identity and the stored events are untouched; identification can be re-run alone.
- **B. Inside the extraction prompt.** One call fewer, but every stored event must be re-extracted and downstream readings recomputed.
- **C. Alias matching only.** Cheap and reproducible, but gives no role and finds no model that is not yet registered. It is kept as the resolver inside A.

## Decisions

- Models owned by organisations outside the tracked registry are recorded, as candidates. `org_id` is null and the owner's name is kept as written.
- A dated build of a model (`grok-2026-09-03`) is an alias of its release, not a release of its own.
- A name that does not split cleanly into version and variant keeps both null and fills `name` only.

## Supplementing 2026-08-22 to 2026-10-03

State of the local store on 2026-10-03:

- Collected posts are continuous from 08-22 to 09-22; 09-23 is partial and nothing useful follows.
- 65 of 374 account windows between 08-22 and 09-29 did not complete (interrupted, page budget, request error, transport exhausted).
- Events are extracted up to 09-20.

Steps, in order. Steps 1 and 2 run in parallel.

1. **Collect.** Run the existing crawler, unchanged, for the window 09-23 to the cut-off: once for `official`, once for `panel`. Re-run the 65 incomplete account windows. On a rate limit the crawler fails over to another account. Windows still incomplete afterwards stay recorded as gaps; a gap is never read as "no updates".
2. **Build identification.** Migration 032, the step, the resolver and their tests. Run it over the 581 stored events and hand check 50 before going further.
3. **Ingest and extract.** Ingest the new runs. Extract events for 09-21 onwards, and for older posts recovered by the gap retries; existing deduplication keeps recovered posts from forming duplicate events.
4. **Identify.** Run the step over the new events.
5. **Recompute.** Route, judge, verify against the panel, recompute activity and gate states, publish the local snapshot.
6. **Accept.** Posts and events per day show no break after 09-22; the identification report (see Checks) is produced; `pnpm data:test` and `pnpm check` pass.

Readings on the site will move once two more weeks of updates are judged. That is the expected result of step 5.
