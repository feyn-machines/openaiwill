-- Record how autonomously the ability was actually used, separately from what
-- kind of evidence the update is and from how trustworthy its source is.
--
-- Why: production_adoption was mapped flat to autonomy stage 4, and it produced
-- a stage 4 that does not survive reading the evidence. "Venice AI uses Wan 3.0
-- in real creative workflow ... iterative prototyping from 360p to 1080p" is
-- genuine production use, and it is also a person iterating on every output -
-- stage 2 behaviour. Production use establishes that something is deployed; it
-- says nothing on its own about how much of the work the person still does.
--
-- Three independent caps now apply: the kind of evidence, the tier of the
-- source, and the autonomy actually described. The stage is the lowest of them.
--
-- Transaction controlled by the migration runner.

ALTER TABLE public.capability_evidence
    ADD COLUMN observed_stage numeric(2,1)
        CHECK (observed_stage IS NULL
               OR (observed_stage BETWEEN 0 AND 4 AND observed_stage * 2 = floor(observed_stage * 2)));

ALTER TABLE public.capability_evidence
    ADD COLUMN observed_stage_rationale text;

ALTER TABLE public.capability_states
    ADD COLUMN limiting_factor text
        CHECK (limiting_factor IS NULL
               OR limiting_factor IN ('evidence_kind', 'evidence_tier', 'observed_autonomy', 'negative_evidence'));

COMMENT ON COLUMN public.capability_states.limiting_factor IS
    'Which of the three caps actually held the stage down. A reader can tell a weak '
    'capability from weak evidence from a capable tool that people still supervise.';
