# Real local collection calculation plan

Goal: import the existing 2,707 real social sources into the local PostgreSQL pipeline, calculate source metrics and a clearly experimental, evidence-reviewed capability estimate for one complete ontology market.

Spec: CLAUDE.md, CONTEXT.md, docs/development/local-data-pipeline.md, docs/data/model-and-storage-boundary.md. Existing permission covers local processing, DB import and calculation. No publication or external reporting.

Architecture: reuse transactional run_batch, immutable catalogs/batches and existing tables. Retain local-input-1 and its synthetic behavior byte-for-byte for existing replay. Add real-local-input-1 plus an explicit real-evidence-review method; actual AI assessment records are input judgments, never direct metric/progress table writes. Source-count operations run in PostgreSQL. A local archive adapter verifies normalized manifest/file hashes and preserves collector identities/times/nulls. Root prepares an evidence review from full saved post text. No live crawling is necessary for the saved-data calculation.

Global constraints: preserve all prior dirty work and sealed releases; no commits/push; do not overwrite raw archive or five synthetic ready batches; no auth/report intake/weekly publication; no score per like, event or adoption stage; partial coverage stays partial, source-field zero is not missing. Current observation snapshots do not reconstruct historical week-end metrics or capability deltas. Score only one market with every child retained; no global index. All detailed input/output stays in ignored data/; docs contain sanitized findings.

## Task 1: real input, archive adapter and calculation engine

- [x] Extend scripts/data_pipeline/pipeline.py and add scripts/data_pipeline/real_archive.py; add focused unit and PG integration tests under scripts/tests/test_data_*.
- [x] Write tests first and witness rejection/failure before implementation.
- [x] real-local-input-1 uses old TOP_FIELDS plus provenance, assessments. synthetic must be false. Preserve real records and their table constraints. Provenance names archive manifests and SHA256 hashes. Assessments per work: concept_id, scenarios (three values or null), event_ids, evidence (capture_id/content_sha256), estimator, assessed_at, rationale, assumptions, limitations. Dates, finite ordered range 0..100, precision, unique works and nonempty explanations validated. Numeric judgments require current accessible cutoff-bounded mapped events and exact cited content hashes. Missing judgments produce null, never fabricated zero. Real source kinds/platforms cannot be fixtures and real mode cannot invoke synthetic stages; synthetic mode cannot invoke reviewed real inference.
- [x] Config uses existing keys plus periods (real only), with explicit period id/start/end and source scope. Real progress op is reviewed_evidence_scenarios, experimental=true, aggregation=all_children_weighted, missing=null, disclaimer text and explicit estimator separation from observations; assessment values are batch inputs, not method config. All current market children/weights are retained.
- [x] Keep old metric definitions; add archive_post_count and archive_comment_sum in real config with independently versioned rules. Calculate aggregate metrics per platform and declared publication-period window using latest cutoff-bounded captures; missing fields remain null, known subtotals/missing counts in parameters; counts are observed sample sizes, coverage partial. Store row-level metric_inputs and applicable original collection_coverage links. Work-tagged event/post/comment metrics remain separate. Include aggregate values in batch_summary without breaking old consumers.
- [x] Real coverage retains original query JSON and multiple request records; reject unsupported complete claims. Each coverage row must fall in overall window and cutoff, and use in-scope platform/accounts. Do not fabricate per-account exhaustion from grouped X queries. Explicit source scopes account:null is a platform-wide query coverage record, not a replacement identity for known authors.
- [x] Adapter function load_archive(path) verifies top and period manifests, every consumed JSONL hash/row count, synthetic=false, input references/time windows, duplicate conflicts. Return merged tables/comments and metadata/post text needed for root event annotation. Prefix coverage IDs with period to avoid cross-period query-ID clashes; preserve all other IDs. Do not mutate raw archive. CLI is scripts/calculate-real-data.py --archive PATH --review PATH --output PATH; root provides review containing config, semantic tables and assessments. Merge then run_batch and save frozen normalized input/config/report JSON. Generated timestamp should be stable in review for idempotence. No external inference API or crawler invocation.
- [x] Tests cover real/synthetic separation; latest snapshot dedup; real zero/missing; period boundaries; no aggregate inflation across recaptures; partial sample counts; mismatched archive hashes/path traversal; unsupported numeric inference and dangling/changed evidence; score independence from comment changes; missing child no parent renormalization; same input replay; transactional failure.

## Task 2: inspect evidence and prepare real review

- [x] Read relevant full official and community posts from both archived periods; document source identity vs self-report and avoid promoting demo/marketing to verification.
- [x] Select oaw:market:software-application-code and all three children; use proposed weights .4/.4/.2 for frontend/backend/integration with explicit rationale.
- [x] Consolidate related posts into real announcement/availability/community-report events; preserve source roles, claim verification and IDs. Map specific evidence to work nodes with rationale. No automatic keyword count as verified event count.
- [x] Write timestamped local review with coarse three-scenario AI estimates, scope, assumptions, limitations and exact input captures/content hashes. No retrospective progress estimate from current metrics.

## Task 3: run, review and deliver

- [x] Run real import, replay, direct DB checks and query resulting source/metric/event/progress counts; retain input/config/review/output and source hash manifest locally.
- [x] Independent review of changed importer and calculations; fix actionable findings and rerun focused tests.
- [x] Run pnpm data:setup, pnpm data:test, pnpm data:simulate and pnpm check; preserve five old batch results.
- [x] Update runbook/current status and sanitized real-data report. Report actual counts, pilot score/scenarios and evidence limits; no claim of production baseline or full global progress.
