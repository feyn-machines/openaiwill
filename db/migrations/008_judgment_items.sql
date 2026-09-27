-- Every decision a judge made, including the negative and the undecided ones.
-- concept_capability_edges only holds edges that exist; comparing two judges, or
-- measuring how often a judge refuses to decide, needs the rows where the answer
-- was no. Without them an A/B comparison can only see agreement, never the shape
-- of the disagreement.
--
-- Hand-written rather than generated: this table projects no controlled
-- vocabulary, so there is nothing here for the semantic layer to own.
--
-- Transaction controlled by the migration runner.

CREATE TABLE public.judgment_items (
    run_id text NOT NULL REFERENCES public.judgment_runs(run_id),
    subject_id text NOT NULL,
    object_id text NOT NULL,
    decision boolean,
    confidence numeric(4,3) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    centrality numeric(3,2) CHECK (centrality IS NULL OR centrality BETWEEN 0 AND 4),
    rationale text NOT NULL,
    unresolved_reason text,
    latency_ms integer CHECK (latency_ms IS NULL OR latency_ms >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, subject_id, object_id),
    -- rule:no-other-bucket - an undecided answer must say what it got stuck on,
    -- so the gap can be counted and the rubric fixed.
    CHECK (decision IS NOT NULL OR (unresolved_reason IS NOT NULL AND unresolved_reason <> ''))
);

CREATE INDEX judgment_items_subject ON public.judgment_items (subject_id, object_id);
CREATE INDEX judgment_items_object ON public.judgment_items (object_id, decision);
