-- Repair extracted_events_kind_check: it never rejected anything with a NULL
-- kind. In SQL, NULL IN (...) is NULL, not false, so the intended
-- "unclassified events must say why" rule evaluated to unknown and passed.
-- Every branch below now tests IS NULL / IS NOT NULL explicitly.
-- Generated from datasets/semantic/semantic-model.v2.json.
-- Transaction controlled by the migration runner.

ALTER TABLE public.extracted_events DROP CONSTRAINT extracted_events_kind_check;
ALTER TABLE public.extracted_events ADD CONSTRAINT extracted_events_kind_check CHECK (
    (kind_vocabulary = 'legacy-freeform'
        AND kind IS NOT NULL AND kind IN ('launch', 'release', 'update', 'pricing', 'availability', 'benchmark', 'partnership', 'deprecation', 'research', 'other'))
    OR (kind_vocabulary = 'event_kind-2.0.0' AND (
        (kind IS NOT NULL AND kind IN ('product_launch', 'version_release', 'availability_change', 'capability_update', 'pricing_change', 'benchmark_result', 'third_party_recognition', 'production_adoption', 'partnership', 'research_result', 'deprecation', 'personnel', 'event_announcement', 'incident', 'policy_statement'))
        OR (kind IS NULL AND unresolved_reason IS NOT NULL AND unresolved_reason <> '')
    ))
);

-- The same shape of hole in the two role constraints: a NULL role passed both.
ALTER TABLE public.event_people DROP CONSTRAINT event_people_role_check;
ALTER TABLE public.event_people ADD CONSTRAINT event_people_role_check CHECK (
    role_vocabulary = 'legacy-freeform'
    OR (role IS NOT NULL AND role IN ('announcer', 'spokesperson', 'researcher', 'third_party_evaluator', 'adopter_engineer', 'community_self_report'))
);

ALTER TABLE public.person_affiliations DROP CONSTRAINT person_affiliations_role_check;
ALTER TABLE public.person_affiliations ADD CONSTRAINT person_affiliations_role_check CHECK (
    role_vocabulary = 'legacy-freeform'
    OR (role_name IS NOT NULL AND role_name IN ('executive', 'board_member', 'researcher', 'engineer', 'communications', 'unknown'))
);

ALTER TABLE public.events DROP CONSTRAINT events_kind_check;
ALTER TABLE public.events ADD CONSTRAINT events_kind_check CHECK (
    kind_vocabulary = 'legacy-freeform'
    OR (kind IS NOT NULL AND kind IN ('product_launch', 'version_release', 'availability_change', 'capability_update', 'pricing_change', 'benchmark_result', 'third_party_recognition', 'production_adoption', 'partnership', 'research_result', 'deprecation', 'personnel', 'event_announcement', 'incident', 'policy_statement'))
);
