-- Put the activity layer under the same controlled vocabularies as everything else.
--
-- Migrations 013-017 created the activity tables by hand rather than by
-- projecting the semantic model, and three things drifted:
--
--   1. activity_evidence.evidence_tier had NO check at all. It is the column the
--      tier cap reads - T1 supports L5, T4 supports L1 - so an unrecognised
--      value there produces a NULL cap, and LEAST(level, NULL) is NULL: the
--      reading silently disappears instead of failing.
--
--   2. method enumerated ('ai_proposed', 'reviewed', 'imported'). The
--      relation_method vocabulary is ('source_id', 'ai_proposed', 'reviewed').
--      `imported` is not a term in it - it was invented at the keyboard - and
--      `source_id`, which marks an edge that came from the source data rather
--      than from a judge, was dropped. No row uses `imported`.
--
--   3. status enumerated ('candidate', 'reviewed', 'rejected'), missing
--      `source_reference` for the same reason.
--
-- The point of a controlled vocabulary is that a column equals it rather than
-- merely overlapping it: a value the vocabulary does not contain cannot be
-- explained to a reader, and a term the column rejects cannot be recorded.
-- scripts/check-semantic-model.mjs now holds these four tables to that, so this
-- cannot drift again without failing `pnpm check`.

ALTER TABLE public.activity_evidence
    DROP CONSTRAINT IF EXISTS activity_evidence_method_check,
    DROP CONSTRAINT IF EXISTS activity_evidence_status_check,
    ADD CONSTRAINT activity_evidence_tier_check
        CHECK (evidence_tier IN ('T1', 'T2', 'T3', 'T4')),
    ADD CONSTRAINT activity_evidence_method_check
        CHECK (method IN ('source_id', 'ai_proposed', 'reviewed')),
    ADD CONSTRAINT activity_evidence_status_check
        CHECK (status IN ('source_reference', 'candidate', 'reviewed', 'rejected'));

ALTER TABLE public.activity_task_edges
    DROP CONSTRAINT IF EXISTS activity_task_edges_method_check,
    DROP CONSTRAINT IF EXISTS activity_task_edges_status_check,
    ADD CONSTRAINT activity_task_edges_method_check
        CHECK (method IN ('source_id', 'ai_proposed', 'reviewed')),
    ADD CONSTRAINT activity_task_edges_status_check
        CHECK (status IN ('source_reference', 'candidate', 'reviewed', 'rejected'));

ALTER TABLE public.activity_gate_edges
    DROP CONSTRAINT IF EXISTS activity_gate_edges_method_check,
    DROP CONSTRAINT IF EXISTS activity_gate_edges_status_check,
    ADD CONSTRAINT activity_gate_edges_method_check
        CHECK (method IN ('source_id', 'ai_proposed', 'reviewed')),
    ADD CONSTRAINT activity_gate_edges_status_check
        CHECK (status IN ('source_reference', 'candidate', 'reviewed', 'rejected'));

ALTER TABLE public.market_occupation_edges
    DROP CONSTRAINT IF EXISTS market_occupation_edges_method_check,
    DROP CONSTRAINT IF EXISTS market_occupation_edges_status_check,
    ADD CONSTRAINT market_occupation_edges_method_check
        CHECK (method IN ('source_id', 'ai_proposed', 'reviewed')),
    ADD CONSTRAINT market_occupation_edges_status_check
        CHECK (status IN ('source_reference', 'candidate', 'reviewed', 'rejected'));
