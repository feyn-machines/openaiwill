-- Which subjects a method has already decided, so a rerun does not pay twice.
--
-- Every pass here sweeps a fixed list of subjects -- 265 markets, 614 activities,
-- 581 events -- and asks a few hundred questions about each. Re-running one cost
-- the full sweep again, because the only record a pass left was the edges it
-- kept. That works until a subject keeps nothing: 325 of 581 events bore on no
-- activity at all, and a resume built on "has this subject any rows?" would ask
-- those 325 a second time. Silence is an answer and needs somewhere to live.
--
-- Keyed by method_version, not run_id, because that is the question a resume
-- actually asks: has this subject been decided under the method I am about to
-- use? Change the method and every subject is due again, which is the correct
-- invalidation and needs no cache to be cleared by hand.
--
-- A row is written only when the subject completed with no failed batch. A
-- partially answered subject stays absent and is asked again -- the failure mode
-- to avoid is not a wasted call, it is a subject marked done on half an answer.
--
-- Transaction controlled by the migration runner.

CREATE TABLE public.judgment_checkpoints (
    method_version text NOT NULL CHECK (method_version <> ''),
    subject_id text NOT NULL CHECK (subject_id <> ''),
    run_id text NOT NULL REFERENCES public.judgment_runs(run_id) ON DELETE CASCADE,
    -- 0 is the point of the table: it separates "asked, kept nothing" from
    -- "never asked", which the edge tables cannot do.
    kept integer NOT NULL CHECK (kept >= 0),
    questions_asked integer NOT NULL CHECK (questions_asked >= 0),
    decided_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (method_version, subject_id)
);

-- Dropping a bad run takes its checkpoints with it (ON DELETE CASCADE above);
-- this index is what makes that cascade, and per-run auditing, cheap.
CREATE INDEX judgment_checkpoints_run ON public.judgment_checkpoints (run_id);
