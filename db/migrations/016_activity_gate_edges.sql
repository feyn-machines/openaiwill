-- Which gates hold an activity in place.
--
-- A gate is a condition that does not lift when models improve: a licensed
-- clinician must sign, a person must be physically present, someone must hold
-- payment authority. It is not a statement about capability, which is why it
-- survives the removal of the capability layer.
--
-- Attached to the 614 market activities rather than swept across all 17,237
-- tasks: a gate holds a kind of work, not one sentence of task text, and the
-- sweep cost drops from 17,237 calls to 614.

CREATE TABLE IF NOT EXISTS public.activity_gate_edges (
    ontology_version text        NOT NULL,
    activity_id      text        NOT NULL,
    gate_id          text        NOT NULL,
    judge            text        NOT NULL,
    method           text        NOT NULL,
    status           text        NOT NULL,
    confidence       numeric,
    rationale        text        NOT NULL,
    judgment_run_id  text        NOT NULL,
    reviewed_by      text,
    reviewed_at      timestamptz,
    record_sha256    text        NOT NULL,
    PRIMARY KEY (ontology_version, activity_id, gate_id),
    CONSTRAINT activity_gate_edges_method_check
        CHECK (method IN ('ai_proposed', 'reviewed', 'imported')),
    CONSTRAINT activity_gate_edges_status_check
        CHECK (status IN ('candidate', 'reviewed', 'rejected')),
    CONSTRAINT activity_gate_edges_ai_cannot_assert
        CHECK (method <> 'ai_proposed' OR status IN ('candidate', 'rejected')),
    CONSTRAINT activity_gate_edges_confidence_range
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    CONSTRAINT activity_gate_edges_judge_check
        CHECK (judge IN ('typesafe', 'deepseek'))
);

CREATE INDEX IF NOT EXISTS activity_gate_edges_by_gate
    ON public.activity_gate_edges (gate_id);
CREATE INDEX IF NOT EXISTS activity_gate_edges_by_run
    ON public.activity_gate_edges (judgment_run_id);
