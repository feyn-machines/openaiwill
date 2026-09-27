-- What an AI update shows about a kind of work.
--
-- This replaces the capability layer as the place evidence lands. The old chain
-- was event -> capability -> work, and the middle term was lossy in both
-- directions: forty-one of forty-six capabilities were work traits that matched
-- everything, so a flagship legal product demonstrated nothing while a personal
-- side tool moved three edges.
--
-- Now an update points straight at the activity it bears on, and carries the
-- level it shows there. One judgment answers both "what did it show" and "how
-- far", so demonstrates and requires both disappear.
--
-- observed_level is L0-L5. It is what THIS update shows, not a verdict on the
-- activity: the activity's level is the best evidence standing behind it, which
-- is computed, not stored here.

CREATE TABLE IF NOT EXISTS public.activity_evidence (
    event_id        text        NOT NULL,
    activity_id     text        NOT NULL,
    ontology_version text       NOT NULL,
    evidence_tier   text        NOT NULL,
    evidence_sign   text        NOT NULL,
    -- Null when the update shows the activity is being done but says nothing
    -- about how much a person still did. Missing is not zero and not five.
    observed_level  numeric,
    confidence      numeric,
    judge           text        NOT NULL,
    method          text        NOT NULL,
    status          text        NOT NULL,
    rationale       text        NOT NULL,
    judgment_run_id text        NOT NULL,
    reviewed_by     text,
    reviewed_at     timestamptz,
    record_sha256   text        NOT NULL,
    PRIMARY KEY (event_id, activity_id),
    CONSTRAINT activity_evidence_sign_check
        CHECK (evidence_sign IN ('positive', 'negative')),
    CONSTRAINT activity_evidence_level_range
        CHECK (observed_level IS NULL OR (observed_level >= 0 AND observed_level <= 5)),
    CONSTRAINT activity_evidence_confidence_range
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    CONSTRAINT activity_evidence_method_check
        CHECK (method IN ('ai_proposed', 'reviewed', 'imported')),
    CONSTRAINT activity_evidence_status_check
        CHECK (status IN ('candidate', 'reviewed', 'rejected')),
    CONSTRAINT activity_evidence_ai_cannot_assert
        CHECK (method <> 'ai_proposed' OR status IN ('candidate', 'rejected')),
    CONSTRAINT activity_evidence_judge_check
        CHECK (judge IN ('typesafe', 'deepseek'))
);

CREATE INDEX IF NOT EXISTS activity_evidence_by_activity
    ON public.activity_evidence (activity_id);
CREATE INDEX IF NOT EXISTS activity_evidence_by_run
    ON public.activity_evidence (judgment_run_id);
