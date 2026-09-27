-- Record completed product integration separately from an ongoing integration
-- and from an independently evidenced production deployment. No score mapping.
ALTER TABLE public.adoptions DROP CONSTRAINT adoptions_stage_check;
ALTER TABLE public.adoptions ADD CONSTRAINT adoptions_stage_check
  CHECK (stage IN ('planned','pilot','integrating','integrated','production','stopped','unknown'));
