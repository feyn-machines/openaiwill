-- Which O*NET task a market activity is the same work as.
--
-- The market side names work in its own words ("Check citations attachments and
-- filing formats"); the occupation side carries O*NET's originals. Same job,
-- written twice, with nothing joining them -- 614 items on one side, 18,838 on
-- the other, zero overlap. This is the join, and it turns those 614 from a
-- half-built parallel catalogue into a translation layer: the market keeps its
-- language and gains an authoritative task set underneath.
--
-- Like every machine-proposed edge: ai_proposed + candidate, with the judge
-- recorded, because a fallback that leaves no mark is how a permissive reading
-- and a strict one ended up indistinguishable once already.
--
-- An activity maps to several tasks and a task to several activities, so counts
-- per activity are correct and a sum across them is not.

CREATE TABLE IF NOT EXISTS public.activity_task_edges (
    ontology_version text        NOT NULL,
    activity_id      text        NOT NULL,
    task_id          text        NOT NULL,
    judge            text        NOT NULL,
    method           text        NOT NULL,
    status           text        NOT NULL,
    confidence       numeric,
    rationale        text        NOT NULL,
    judgment_run_id  text        NOT NULL,
    reviewed_by      text,
    reviewed_at      timestamptz,
    record_sha256    text        NOT NULL,
    PRIMARY KEY (ontology_version, activity_id, task_id),
    CONSTRAINT activity_task_edges_method_check
        CHECK (method IN ('ai_proposed', 'reviewed', 'imported')),
    CONSTRAINT activity_task_edges_status_check
        CHECK (status IN ('candidate', 'reviewed', 'rejected')),
    CONSTRAINT activity_task_edges_ai_cannot_assert
        CHECK (method <> 'ai_proposed' OR status IN ('candidate', 'rejected')),
    CONSTRAINT activity_task_edges_confidence_range
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    CONSTRAINT activity_task_edges_judge_check
        CHECK (judge IN ('typesafe', 'deepseek'))
);

CREATE INDEX IF NOT EXISTS activity_task_edges_by_task
    ON public.activity_task_edges (task_id);
CREATE INDEX IF NOT EXISTS activity_task_edges_by_run
    ON public.activity_task_edges (judgment_run_id);
CREATE INDEX IF NOT EXISTS activity_task_edges_by_judge
    ON public.activity_task_edges (judge);
