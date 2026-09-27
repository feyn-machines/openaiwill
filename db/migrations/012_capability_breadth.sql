-- How much of the judged work a capability reaches.
--
-- Why: the first full requires sweep put cap:attention-to-detail on 17,022 of
-- 19,452 judged work nodes - 87.5% of all work. The next capability down sits
-- at 28.7%, and every remaining one is below that. One capability behaves
-- categorically differently from the other forty-five.
--
-- That reading is not wrong; most work does require attention to detail. It is
-- useless. A capability present in almost all work cannot tell a reader which
-- work an AI update touches, which is the only question the graph exists to
-- answer. Left unmarked it would also dominate every occupation page by sheer
-- edge count.
--
-- The edges are not deleted. The judge answered what it was asked, and deleting
-- its answers would hide the finding rather than record it. What is recorded
-- here is the measurement that identifies such a capability, so the rule can be
-- applied in one place and shown to the reader with its number attached.
--
-- Numerator and denominator are stored, not the ratio: a stored ratio can
-- disagree with the counts it came from, and the counts are what an auditor
-- needs. The denominator is per capability, not the global judged set, because
-- a capability added late in a sweep has genuinely been asked about less often.
--
-- Transaction controlled by the migration runner.

ALTER TABLE public.capability_states
    ADD COLUMN work_nodes_requiring integer
        CHECK (work_nodes_requiring IS NULL OR work_nodes_requiring >= 0);

ALTER TABLE public.capability_states
    ADD COLUMN work_nodes_judged integer
        CHECK (work_nodes_judged IS NULL OR work_nodes_judged >= 0);

ALTER TABLE public.capability_states
    ADD CONSTRAINT capability_states_breadth_within_judged
        CHECK (work_nodes_requiring IS NULL
               OR work_nodes_judged IS NULL
               OR work_nodes_requiring <= work_nodes_judged);

COMMENT ON COLUMN public.capability_states.work_nodes_requiring IS
    'Distinct work nodes with a requires edge to this capability at compute time.';

COMMENT ON COLUMN public.capability_states.work_nodes_judged IS
    'Distinct work nodes a judge was actually asked about for this capability. '
    'The breadth threshold that decides whether a capability discriminates lives '
    'in the semantic model, not here, so there is one place to change it.';
