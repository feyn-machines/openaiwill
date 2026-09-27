-- Third-party verification of vendor claims, from panel posts.
--
-- A vendor's own claim is held at L2 (evidence_tier T3). The only thing that can
-- lift it is someone else confirming it, and that confirmation is a different
-- piece of evidence from a different source: it does not overwrite the vendor
-- reading on activity_evidence, it sits beside it. The activity level takes the
-- best of both, each capped by its own tier.
--
-- The judge only names what a post is (post_nature) and what level it shows.
-- Whether that becomes evidence, and at which tier, is derived from the
-- account's role and its independence of the company on the day of the post
-- (rule:verification-tier), and written here already derived - so a query can
-- trust the tier without re-running the rule.
--
-- No BEGIN/COMMIT here: db.migrate wraps each file in one transaction.

ALTER TABLE public.judgment_runs DROP CONSTRAINT judgment_runs_task_check;
ALTER TABLE public.judgment_runs ADD CONSTRAINT judgment_runs_task_check
    CHECK (task IN ('requires', 'blocked_by', 'demonstrates', 'event_kind', 'gate_state', 'serves_market', 'verification'));

CREATE TABLE IF NOT EXISTS public.verification_evidence (
    event_id         text        NOT NULL,
    activity_id      text        NOT NULL,
    source_id        text        NOT NULL,
    account_key      text        NOT NULL REFERENCES public.source_accounts(account_key),
    ontology_version text        NOT NULL,
    post_nature      text        NOT NULL,
    -- The level the post shows on this activity, as a category. Null when the
    -- post confirms the product works but says nothing about how far.
    observed_level   smallint,
    -- Null when the rule gives no evidence (not independent, opinion, relay,
    -- unrelated); such rows are kept so a lookup's yield can be counted.
    evidence_tier    text,
    independent      boolean     NOT NULL,
    status           text        NOT NULL,
    rationale        text        NOT NULL,
    judgment_run_id  text        NOT NULL REFERENCES public.judgment_runs(run_id),
    record_sha256    public.sha256 NOT NULL,
    PRIMARY KEY (event_id, activity_id, source_id),
    CONSTRAINT verification_evidence_post_nature_check
        CHECK (post_nature IN ('hands_on_test', 'independent_evaluation', 'own_production_use', 'expert_assessment', 'opinion', 'relay', 'unrelated')),
    CONSTRAINT verification_evidence_evidence_tier_check
        CHECK (evidence_tier IS NULL OR evidence_tier IN ('T1', 'T2', 'T3', 'T4')),
    CONSTRAINT verification_evidence_status_check
        CHECK (status IN ('source_reference', 'candidate', 'reviewed', 'rejected')),
    CONSTRAINT verification_evidence_level_range
        CHECK (observed_level IS NULL OR observed_level BETWEEN 0 AND 5),
    -- A post from an account tied to the company is never third-party evidence.
    CONSTRAINT verification_evidence_dependent_is_not_evidence
        CHECK (independent OR evidence_tier IS NULL)
);
CREATE INDEX IF NOT EXISTS verification_evidence_by_activity ON public.verification_evidence (activity_id);
CREATE INDEX IF NOT EXISTS verification_evidence_by_account ON public.verification_evidence (account_key);
