-- Retire the capability layer and the pre-activity pilot layer.
--
-- Two generations of tables sat beside the live one, and neither fed anything a
-- reader could see. Together they were 1,499,000 of the database's 1,580,000
-- rows: 95%, none of it reachable from a page.
--
-- THE CAPABILITY LAYER. A capability was meant to be the middle term between an
-- AI update and a piece of work: the update demonstrates a capability, the
-- capability is required by a task. Forty-one of the forty-six proposed
-- capabilities were judged to be required by more than half of ALL work they
-- were tested against, so the layer answered every question with the same
-- answer. "Which work does this update touch?" cannot be answered by a term
-- that touches everything. Market activities replaced it: an activity is what a
-- market actually does, an update lands on it directly, and the level is read
-- from what the update describes rather than inferred through a middle term.
--
-- judgment_items is the whole per-question log of that layer - 1,387,401 rows,
-- every one of them from the requires / blocked_by / demonstrates passes. The
-- mapping passes that replaced them record a checkpoint per subject decided
-- (judgment_checkpoints) and write their answers as edges, so silence is
-- recorded as kept = 0 rather than as a million rows nobody reads.
--
-- THE PILOT LAYER. sources / metrics / progress / claims / adoptions and the
-- five-batch synthetic simulation were the first end-to-end proof that a local
-- input could reach a calculated number. It worked and it is finished: the
-- collection store (collected_sources, collected_captures) and the extraction
-- layer (extracted_events) superseded it, the site never read a row of it, and
-- the old events table held 27 rows against extracted_events' 1,336.
--
-- Nothing here is migrated forward. No deployment has ever read this database,
-- so there is no history to preserve and no downstream to notify. Gates are NOT
-- dropped: a gate is not a weak capability but a condition that does not lift
-- when models improve, and it is what holds an activity at L0.
--
-- Dropped one layer per statement so PostgreSQL resolves the foreign keys among
-- them; no surviving table references anything below.

DROP TABLE IF EXISTS
    public.judgment_items,
    public.concept_capability_edges,
    public.concept_gate_edges,
    public.capability_evidence,
    public.capability_states,
    public.capabilities;

DROP TABLE IF EXISTS
    public.metric_inputs,
    public.metric_values,
    public.metric_coverage,
    public.metric_definitions,
    public.progress_inputs,
    public.progress_values,
    public.progress_methods,
    public.claim_evidence,
    public.claims,
    public.adoptions,
    public.event_products,
    public.event_people,
    public.event_organizations,
    public.event_concepts,
    public.event_tags,
    public.event_sources,
    public.events,
    public.source_tags,
    public.tags,
    public.product_versions,
    public.products,
    -- The pilot's own organisation table, batch-scoped. The live registry is
    -- org_registry, which extracted_events joins and this never fed.
    public.organizations,
    public.person_affiliations,
    public.people,
    public.source_captures,
    public.sources,
    public.source_accounts,
    public.collection_coverage,
    public.relation_weights,
    public.config_releases,
    public.data_batches;
