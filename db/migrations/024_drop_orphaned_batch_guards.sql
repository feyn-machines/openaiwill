-- Drop the guard functions whose tables are gone.
--
-- guard_data_batch and guard_batch_content enforced the batch immutability
-- contract: a data_batch that reached `ready` could not be edited, and its
-- children were frozen with it. Migration 020 dropped those tables, which took
-- their triggers; the functions stayed behind, callable and meaningless.
--
-- The catalogue guards are NOT dropped. guard_catalogue_content,
-- guard_release and reject_business_truncate still hold the sealed ontology
-- immutable - ontology_concepts, ontology_relations and ontology_releases carry
-- them - and that is the contract that matters now: the release is the world
-- every number on the site is counted against, so a sealed release that can be
-- edited afterwards makes every published figure unreproducible.

DROP FUNCTION IF EXISTS public.guard_data_batch();
DROP FUNCTION IF EXISTS public.guard_batch_content();
