-- questions_asked is unknown for checkpoints backfilled from finished runs.
--
-- The four index runs completed with zero failed batches before this table
-- existed, so their subjects are genuinely decided and must not be paid for
-- again -- but the per-subject question count was never recorded, only the
-- per-run total. Writing 0 there would say "asked nothing", which is the one
-- thing it did not do. NULL says "not recorded", and the distinction is the
-- whole reason this table separates silence from absence in the first place.
--
-- Transaction controlled by the migration runner.

ALTER TABLE public.judgment_checkpoints ALTER COLUMN questions_asked DROP NOT NULL;
