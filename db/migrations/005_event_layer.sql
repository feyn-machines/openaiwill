-- Independent event layer: deduplicated real-world AI updates extracted from the
-- collection store, decoupled from the market-scoped calculation batches
-- (data_batches). Versioned by extraction run; carries no batch scope, weights,
-- metrics or progress (those belong to a later calculation batch that projects
-- FROM here). Provenance points back into the collection store; social metrics
-- are never copied — they stay on collected_captures and are reached through
-- extracted_event_sources. The `extracted_*` prefix mirrors the `collected_*`
-- collection store and keeps these tables distinct from the batch-scoped
-- events / event_sources of the (deferred) stage-3 scoring schema.

CREATE TABLE public.extraction_runs (
  run_id text PRIMARY KEY,
  collection_run_ids jsonb NOT NULL CHECK (jsonb_typeof(collection_run_ids) = 'array'),
  model text NOT NULL,
  prompt_sha256 public.sha256 NOT NULL,
  params jsonb NOT NULL CHECK (jsonb_typeof(params) = 'object'),
  window_start timestamptz,
  window_end timestamptz,
  started_at timestamptz NOT NULL,
  finished_at timestamptz,
  status text NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
  run_sha256 public.sha256 NOT NULL,
  candidate_count integer CHECK (candidate_count IS NULL OR candidate_count >= 0),
  event_count integer CHECK (event_count IS NULL OR event_count >= 0),
  ingested_at timestamptz NOT NULL DEFAULT now(),
  CHECK (window_start IS NULL OR window_end IS NULL OR window_start < window_end),
  CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE TABLE public.extracted_events (
  event_id text PRIMARY KEY,
  dedup_key text NOT NULL UNIQUE,
  kind text NOT NULL CHECK (kind IN
    ('launch', 'release', 'update', 'pricing', 'availability',
     'benchmark', 'partnership', 'deprecation', 'research', 'other')),
  title text NOT NULL,
  summary text NOT NULL,
  primary_org text,
  announced_at timestamptz,
  occurred_at timestamptz,
  scheduled_for timestamptz,
  occurrence_status text NOT NULL CHECK (occurrence_status IN
    ('unknown', 'scheduled', 'occurred', 'postponed', 'cancelled')),
  first_extraction_run_id text NOT NULL REFERENCES public.extraction_runs(run_id),
  confidence numeric(4,3) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
  record_sha256 public.sha256 NOT NULL
);
CREATE INDEX extracted_event_time ON public.extracted_events(occurred_at DESC);

CREATE TABLE public.extracted_event_sources (
  event_id text NOT NULL REFERENCES public.extracted_events(event_id),
  run_id text NOT NULL,
  source_id text NOT NULL,
  source_role text NOT NULL CHECK (source_role IN ('primary', 'corroborating', 'context')),
  PRIMARY KEY (event_id, run_id, source_id, source_role),
  FOREIGN KEY (run_id, source_id) REFERENCES public.collected_sources(run_id, source_id)
);
CREATE INDEX extracted_event_source_reverse ON public.extracted_event_sources(run_id, source_id);

CREATE TABLE public.extracted_event_relations (
  from_event_id text NOT NULL REFERENCES public.extracted_events(event_id),
  to_event_id text NOT NULL REFERENCES public.extracted_events(event_id),
  kind text NOT NULL CHECK (kind IN
    ('part_of', 'follows', 'supersedes', 'refines', 'duplicate_of')),
  rationale text NOT NULL,
  confidence numeric(4,3) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
  extraction_run_id text NOT NULL REFERENCES public.extraction_runs(run_id),
  PRIMARY KEY (from_event_id, to_event_id, kind),
  CHECK (from_event_id <> to_event_id)
);
CREATE INDEX extracted_event_relation_to ON public.extracted_event_relations(to_event_id);

CREATE TABLE public.extracted_event_categories (
  event_id text NOT NULL REFERENCES public.extracted_events(event_id),
  taxonomy text NOT NULL CHECK (taxonomy IN ('ontology', 'platform')),
  taxonomy_version text NOT NULL,
  category_id text NOT NULL,
  method text NOT NULL CHECK (method IN ('ai_deepseek', 'rule', 'manual')),
  confidence numeric(4,3) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
  rationale text NOT NULL,
  extraction_run_id text NOT NULL REFERENCES public.extraction_runs(run_id),
  PRIMARY KEY (event_id, taxonomy, taxonomy_version, category_id)
);
CREATE INDEX extracted_category_events ON public.extracted_event_categories(taxonomy, taxonomy_version, category_id);
