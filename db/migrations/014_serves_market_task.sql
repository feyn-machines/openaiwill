-- Add serves_market to the judgment task vocabulary. Generated from
-- datasets/semantic/semantic-model.v2.json; do not edit the term list here.
--
-- serves_market asks whether an occupation does the work a market describes.
-- It is what gives a market a denominator: the 614 work items on the market
-- side of the ontology do not overlap the 18,838 occupation tasks at all, so
-- without this mapping a market has two to five items under it and no share to
-- report.
-- Transaction controlled by the migration runner.

ALTER TABLE public.judgment_runs DROP CONSTRAINT judgment_runs_task_check;
ALTER TABLE public.judgment_runs ADD CONSTRAINT judgment_runs_task_check
    CHECK (task IN ('requires', 'blocked_by', 'demonstrates', 'event_kind', 'gate_state', 'serves_market'));
