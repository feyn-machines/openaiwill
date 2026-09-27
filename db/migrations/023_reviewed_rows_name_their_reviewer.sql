-- A reviewed row has to name who reviewed it and when.
--
-- Migration 006 put this on the capability edges: `method <> 'reviewed' OR
-- (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)`. The activity tables
-- were written by hand and never got it, so a row could claim method='reviewed'
-- with both columns null.
--
-- That matters more here than anywhere else on the site. Every number published
-- is qualified by "nothing has been reviewed by a person", and `reviewed` is
-- the one status that would lift that qualification. A reviewed row with no
-- reviewer is an unattributable claim to the only authority the project has.
-- The count is zero today and must stay honestly zero.
--
-- The reverse direction (status='reviewed' requires method='reviewed') is
-- already present on these tables; this adds the half that was missing.

ALTER TABLE public.activity_task_edges
    ADD CONSTRAINT activity_task_edges_reviewer_named
        CHECK (method <> 'reviewed' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL));

ALTER TABLE public.activity_gate_edges
    ADD CONSTRAINT activity_gate_edges_reviewer_named
        CHECK (method <> 'reviewed' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL));

ALTER TABLE public.market_occupation_edges
    ADD CONSTRAINT market_occupation_edges_reviewer_named
        CHECK (method <> 'reviewed' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL));

ALTER TABLE public.activity_evidence
    ADD CONSTRAINT activity_evidence_reviewer_named
        CHECK (method <> 'reviewed' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL));
