-- First-stage PostgreSQL 18 business schema. Transaction controlled by the migration runner.

CREATE DOMAIN public.sha256 AS text CHECK (VALUE ~ '^[0-9a-f]{64}$');

CREATE TABLE public.ontology_releases (
  version text PRIMARY KEY, schema_version text NOT NULL,
  manifest_sha256 public.sha256 NOT NULL UNIQUE,
  imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.ontology_concepts (
  ontology_version text NOT NULL REFERENCES public.ontology_releases(version),
  id text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('market_group','market','work','occupation_group','occupation')),
  label_en text NOT NULL, label_zh_cn text,
  origin text NOT NULL, translation_status text NOT NULL, scope_status text NOT NULL,
  definition jsonb CHECK (definition IS NULL OR jsonb_typeof(definition) = 'object'),
  record_sha256 public.sha256 NOT NULL,
  PRIMARY KEY (ontology_version,id)
);
CREATE TABLE public.ontology_relations (
  ontology_version text NOT NULL, id text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('has_market','has_work','has_occupation','has_task')),
  parent_id text NOT NULL, child_id text NOT NULL,
  view text NOT NULL CHECK (view IN ('markets','occupations')),
  display_order integer NOT NULL CHECK (display_order >= 0),
  PRIMARY KEY (ontology_version,id),
  UNIQUE (ontology_version,view,kind,parent_id,child_id),
  FOREIGN KEY (ontology_version,parent_id) REFERENCES public.ontology_concepts,
  FOREIGN KEY (ontology_version,child_id) REFERENCES public.ontology_concepts,
  CHECK (parent_id <> child_id)
);
CREATE INDEX relation_child ON public.ontology_relations(ontology_version,child_id);

CREATE TABLE public.config_releases (
  version text PRIMARY KEY,
  ontology_version text NOT NULL REFERENCES public.ontology_releases(version),
  manifest_sha256 public.sha256 NOT NULL UNIQUE,
  imported_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (version,ontology_version)
);
CREATE TABLE public.tags (
  config_version text NOT NULL REFERENCES public.config_releases(version),
  id text NOT NULL, label text NOT NULL, description text,
  PRIMARY KEY (config_version,id)
);
CREATE TABLE public.metric_definitions (
  config_version text NOT NULL REFERENCES public.config_releases(version),
  id text NOT NULL, label text NOT NULL, method_version text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('source_count','aggregate_count')),
  unit text NOT NULL CHECK (unit IN ('comments','reposts','interactions','posts','events','accounts')),
  rule jsonb NOT NULL CHECK (jsonb_typeof(rule) = 'object'),
  rule_sha256 public.sha256 NOT NULL,
  PRIMARY KEY (config_version,id)
);
CREATE TABLE public.progress_methods (
  config_version text NOT NULL REFERENCES public.config_releases(version),
  id text NOT NULL, label text NOT NULL, method_version text NOT NULL,
  spec jsonb NOT NULL CHECK (jsonb_typeof(spec) = 'object'),
  rule_sha256 public.sha256 NOT NULL,
  PRIMARY KEY (config_version,id)
);
CREATE TABLE public.relation_weights (
  config_version text NOT NULL, ontology_version text NOT NULL, relation_id text NOT NULL,
  weight numeric(12,10) CHECK (weight BETWEEN 0 AND 1),
  status text NOT NULL CHECK (status IN ('unknown','proposed','accepted')),
  method_version text, rationale text NOT NULL,
  PRIMARY KEY (config_version,relation_id),
  FOREIGN KEY (config_version,ontology_version) REFERENCES public.config_releases(version,ontology_version),
  FOREIGN KEY (ontology_version,relation_id) REFERENCES public.ontology_relations,
  CHECK ((status = 'unknown' AND weight IS NULL) OR
         (status IN ('proposed','accepted') AND weight IS NOT NULL AND method_version IS NOT NULL))
);

CREATE TABLE public.data_batches (
  id text PRIMARY KEY, format_version text NOT NULL,
  ontology_version text NOT NULL, config_version text NOT NULL,
  manifest_sha256 public.sha256 NOT NULL,
  record_counts jsonb NOT NULL CHECK (jsonb_typeof(record_counts) = 'object'),
  generated_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'loading' CHECK (status IN ('loading','ready','failed')),
  ready_at timestamptz,
  FOREIGN KEY (config_version,ontology_version) REFERENCES public.config_releases(version,ontology_version),
  UNIQUE (id,ontology_version), UNIQUE (id,config_version),
  CHECK ((status = 'ready') = (ready_at IS NOT NULL))
);

CREATE TABLE public.people (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  name text NOT NULL, aliases text[] NOT NULL DEFAULT '{}', public_bio text,
  identity_status text NOT NULL CHECK (identity_status IN ('unknown','candidate','verified','disputed')),
  identity_evidence_urls text[] NOT NULL DEFAULT '{}',
  record_sha256 public.sha256 NOT NULL, PRIMARY KEY (batch_id,id)
);
CREATE TABLE public.organizations (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  name text NOT NULL, aliases text[] NOT NULL DEFAULT '{}', website_url text, group_id text,
  identity_evidence_urls text[] NOT NULL DEFAULT '{}',
  record_sha256 public.sha256 NOT NULL, PRIMARY KEY (batch_id,id),
  FOREIGN KEY (batch_id,group_id) REFERENCES public.organizations,
  CHECK (group_id IS NULL OR group_id <> id)
);
CREATE TABLE public.products (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  name text NOT NULL, aliases text[] NOT NULL DEFAULT '{}', organization_id text,
  website_url text, kind text NOT NULL CHECK (kind IN ('model','application','platform','hardware','other')),
  record_sha256 public.sha256 NOT NULL, PRIMARY KEY (batch_id,id),
  FOREIGN KEY (batch_id,organization_id) REFERENCES public.organizations
);
CREATE TABLE public.product_versions (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  product_id text NOT NULL, version_key text NOT NULL,
  announced_at timestamptz, available_at timestamptz, evidence_urls text[] NOT NULL DEFAULT '{}',
  record_sha256 public.sha256 NOT NULL, PRIMARY KEY (batch_id,id),
  UNIQUE (batch_id,product_id,version_key), UNIQUE (batch_id,product_id,id),
  FOREIGN KEY (batch_id,product_id) REFERENCES public.products
);
CREATE TABLE public.source_accounts (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  platform text NOT NULL, external_account_key text NOT NULL,
  key_status text NOT NULL CHECK (key_status IN ('stable','provisional')),
  handle text, profile_url text NOT NULL,
  person_id text, organization_id text, product_id text,
  account_role text NOT NULL CHECK (account_role IN ('personal','organization_official','product_official','community','unknown')),
  platform_badge text,
  identity_status text NOT NULL CHECK (identity_status IN ('unknown','candidate','verified','disputed')),
  collection_status text NOT NULL CHECK (collection_status IN ('candidate','enabled','paused','disabled')),
  checked_at timestamptz, identity_evidence_urls text[] NOT NULL DEFAULT '{}',
  record_sha256 public.sha256 NOT NULL, PRIMARY KEY (batch_id,id),
  UNIQUE (batch_id,platform,external_account_key), UNIQUE (batch_id,id,platform),
  FOREIGN KEY (batch_id,person_id) REFERENCES public.people,
  FOREIGN KEY (batch_id,organization_id) REFERENCES public.organizations,
  FOREIGN KEY (batch_id,product_id) REFERENCES public.products,
  CHECK (num_nonnulls(person_id,organization_id,product_id) <= 1),
  CHECK (account_role <> 'organization_official' OR organization_id IS NOT NULL),
  CHECK (account_role <> 'product_official' OR product_id IS NOT NULL),
  CHECK (account_role <> 'personal' OR person_id IS NOT NULL)
);
CREATE TABLE public.sources (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  platform text NOT NULL, external_key text NOT NULL, source_account_id text,
  canonical_url text NOT NULL, kind text NOT NULL,
  record_sha256 public.sha256 NOT NULL, PRIMARY KEY (batch_id,id),
  UNIQUE (batch_id,platform,external_key),
  FOREIGN KEY (batch_id,source_account_id,platform) REFERENCES public.source_accounts(batch_id,id,platform)
);
CREATE TABLE public.source_captures (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  source_id text NOT NULL, captured_at timestamptz NOT NULL,
  original_published_at timestamptz, content_sha256 public.sha256,
  public_excerpt text, language text,
  access_status text NOT NULL CHECK (access_status IN ('available','deleted','restricted','failed')),
  record_sha256 public.sha256 NOT NULL, PRIMARY KEY (batch_id,id),
  FOREIGN KEY (batch_id,source_id) REFERENCES public.sources
);
CREATE INDEX capture_source_time ON public.source_captures(batch_id,source_id,captured_at DESC);
CREATE TABLE public.person_affiliations (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  person_id text NOT NULL, organization_id text NOT NULL, role_name text NOT NULL,
  valid_from timestamptz, valid_until timestamptz, evidence_capture_id text NOT NULL,
  record_sha256 public.sha256 NOT NULL, PRIMARY KEY (batch_id,id),
  FOREIGN KEY (batch_id,person_id) REFERENCES public.people,
  FOREIGN KEY (batch_id,organization_id) REFERENCES public.organizations,
  FOREIGN KEY (batch_id,evidence_capture_id) REFERENCES public.source_captures,
  CHECK (valid_from IS NULL OR valid_until IS NULL OR valid_from < valid_until)
);
CREATE TABLE public.collection_coverage (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  platform text NOT NULL, source_account_id text,
  query jsonb NOT NULL CHECK (jsonb_typeof(query) = 'object'),
  window_start timestamptz NOT NULL, window_end timestamptz NOT NULL,
  checked_at timestamptz NOT NULL,
  status text NOT NULL CHECK (status IN ('complete','partial','failed','not_queried')),
  exhausted boolean, retrieved_count bigint CHECK (retrieved_count >= 0), gap_note text,
  record_sha256 public.sha256 NOT NULL, PRIMARY KEY (batch_id,id),
  FOREIGN KEY (batch_id,source_account_id,platform) REFERENCES public.source_accounts(batch_id,id,platform),
  CHECK (window_start < window_end),
  CHECK (status <> 'complete' OR (exhausted IS TRUE AND retrieved_count IS NOT NULL)),
  CHECK (status <> 'not_queried' OR (retrieved_count IS NULL AND exhausted IS NULL))
);

CREATE TABLE public.events (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  dedup_key text NOT NULL, kind text NOT NULL, title text NOT NULL, summary text NOT NULL,
  announced_at timestamptz, occurred_at timestamptz, scheduled_for timestamptz,
  occurrence_status text NOT NULL CHECK (occurrence_status IN ('unknown','scheduled','occurred','postponed','cancelled')),
  venue text, availability jsonb NOT NULL CHECK (jsonb_typeof(availability) = 'object'),
  record_sha256 public.sha256 NOT NULL, PRIMARY KEY (batch_id,id),
  UNIQUE (batch_id,dedup_key)
);
CREATE INDEX event_time ON public.events(batch_id,occurred_at DESC);
CREATE TABLE public.event_sources (
  batch_id text NOT NULL, event_id text NOT NULL, capture_id text NOT NULL, source_role text NOT NULL,
  PRIMARY KEY (batch_id,event_id,capture_id,source_role),
  FOREIGN KEY (batch_id,event_id) REFERENCES public.events,
  FOREIGN KEY (batch_id,capture_id) REFERENCES public.source_captures
);
CREATE INDEX event_source_reverse ON public.event_sources(batch_id,capture_id);
CREATE TABLE public.event_people (
  batch_id text NOT NULL, event_id text NOT NULL, person_id text NOT NULL, role text NOT NULL,
  PRIMARY KEY (batch_id,event_id,person_id,role),
  FOREIGN KEY (batch_id,event_id) REFERENCES public.events,
  FOREIGN KEY (batch_id,person_id) REFERENCES public.people
);
CREATE TABLE public.event_organizations (
  batch_id text NOT NULL, event_id text NOT NULL, organization_id text NOT NULL, role text NOT NULL,
  PRIMARY KEY (batch_id,event_id,organization_id,role),
  FOREIGN KEY (batch_id,event_id) REFERENCES public.events,
  FOREIGN KEY (batch_id,organization_id) REFERENCES public.organizations
);
CREATE INDEX person_events ON public.event_people(batch_id,person_id,event_id);
CREATE INDEX organization_events ON public.event_organizations(batch_id,organization_id,event_id);
CREATE TABLE public.event_products (
  batch_id text NOT NULL, id text NOT NULL,
  event_id text NOT NULL, product_id text NOT NULL, version_id text, role text NOT NULL,
  PRIMARY KEY (batch_id,id),
  UNIQUE NULLS NOT DISTINCT (batch_id,event_id,product_id,version_id,role),
  FOREIGN KEY (batch_id,event_id) REFERENCES public.events,
  FOREIGN KEY (batch_id,product_id) REFERENCES public.products,
  FOREIGN KEY (batch_id,product_id,version_id) REFERENCES public.product_versions(batch_id,product_id,id)
);
CREATE TABLE public.claims (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  event_id text NOT NULL, capture_id text NOT NULL, statement text NOT NULL,
  speaker_person_id text, speaker_organization_id text,
  verification_status text NOT NULL CHECK (verification_status IN ('unassessed','self_reported','corroborated','disputed','refuted')),
  verification_note text NOT NULL,
  record_sha256 public.sha256 NOT NULL, PRIMARY KEY (batch_id,id),
  FOREIGN KEY (batch_id,event_id) REFERENCES public.events,
  FOREIGN KEY (batch_id,capture_id) REFERENCES public.source_captures,
  FOREIGN KEY (batch_id,speaker_person_id) REFERENCES public.people,
  FOREIGN KEY (batch_id,speaker_organization_id) REFERENCES public.organizations,
  CHECK (num_nonnulls(speaker_person_id,speaker_organization_id) <= 1)
);
CREATE TABLE public.claim_evidence (
  batch_id text NOT NULL, claim_id text NOT NULL, capture_id text NOT NULL,
  stance text NOT NULL CHECK (stance IN ('supports','contradicts','context')),
  PRIMARY KEY (batch_id,claim_id,capture_id,stance),
  FOREIGN KEY (batch_id,claim_id) REFERENCES public.claims,
  FOREIGN KEY (batch_id,capture_id) REFERENCES public.source_captures
);
CREATE TABLE public.adoptions (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  event_id text NOT NULL, adopter_organization_id text NOT NULL,
  product_id text NOT NULL, version_id text, workflow text NOT NULL,
  stage text NOT NULL CHECK (stage IN ('planned','pilot','integrating','production','stopped','unknown')),
  capture_id text NOT NULL, source_role text NOT NULL,
  record_sha256 public.sha256 NOT NULL, PRIMARY KEY (batch_id,id),
  FOREIGN KEY (batch_id,event_id) REFERENCES public.events,
  FOREIGN KEY (batch_id,adopter_organization_id) REFERENCES public.organizations,
  FOREIGN KEY (batch_id,product_id) REFERENCES public.products,
  FOREIGN KEY (batch_id,product_id,version_id) REFERENCES public.product_versions(batch_id,product_id,id),
  FOREIGN KEY (batch_id,capture_id) REFERENCES public.source_captures
);
CREATE TABLE public.event_concepts (
  batch_id text NOT NULL, event_id text NOT NULL, ontology_version text NOT NULL, concept_id text NOT NULL,
  status text NOT NULL CHECK (status IN ('candidate','accepted','rejected')), rationale text NOT NULL,
  PRIMARY KEY (batch_id,event_id,concept_id),
  FOREIGN KEY (batch_id,event_id) REFERENCES public.events,
  FOREIGN KEY (batch_id,ontology_version) REFERENCES public.data_batches(id,ontology_version),
  FOREIGN KEY (ontology_version,concept_id) REFERENCES public.ontology_concepts
);
CREATE INDEX concept_events ON public.event_concepts(batch_id,concept_id,status);
CREATE TABLE public.event_tags (
  batch_id text NOT NULL, event_id text NOT NULL, config_version text NOT NULL, tag_id text NOT NULL,
  assignment_method text NOT NULL, rationale text NOT NULL,
  PRIMARY KEY (batch_id,event_id,tag_id),
  FOREIGN KEY (batch_id,event_id) REFERENCES public.events,
  FOREIGN KEY (batch_id,config_version) REFERENCES public.data_batches(id,config_version),
  FOREIGN KEY (config_version,tag_id) REFERENCES public.tags
);
CREATE INDEX tag_events ON public.event_tags(batch_id,tag_id);
CREATE TABLE public.source_tags (
  batch_id text NOT NULL, capture_id text NOT NULL, config_version text NOT NULL, tag_id text NOT NULL,
  assignment_method text NOT NULL, rationale text NOT NULL,
  PRIMARY KEY (batch_id,capture_id,tag_id),
  FOREIGN KEY (batch_id,capture_id) REFERENCES public.source_captures,
  FOREIGN KEY (batch_id,config_version) REFERENCES public.data_batches(id,config_version),
  FOREIGN KEY (config_version,tag_id) REFERENCES public.tags
);
CREATE INDEX tag_captures ON public.source_tags(batch_id,tag_id);

CREATE TABLE public.metric_values (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  config_version text NOT NULL, metric_id text NOT NULL,
  scope_kind text NOT NULL CHECK (scope_kind IN ('capture','event','concept','aggregate')),
  capture_id text, event_id text, ontology_version text NOT NULL, concept_id text,
  parameters jsonb NOT NULL CHECK (jsonb_typeof(parameters) = 'object'),
  window_start timestamptz, window_end timestamptz,
  observed_at timestamptz NOT NULL, provider_updated_at timestamptz, evidence_cutoff_at timestamptz NOT NULL,
  value numeric(24,6), value_status text NOT NULL CHECK (value_status IN ('observed','missing')),
  coverage_status text NOT NULL CHECK (coverage_status IN ('complete','partial','unknown')),
  missing_reason text, input_sha256 public.sha256 NOT NULL, record_sha256 public.sha256 NOT NULL,
  PRIMARY KEY (batch_id,id),
  FOREIGN KEY (batch_id,config_version) REFERENCES public.data_batches(id,config_version),
  FOREIGN KEY (config_version,metric_id) REFERENCES public.metric_definitions,
  FOREIGN KEY (batch_id,ontology_version) REFERENCES public.data_batches(id,ontology_version),
  FOREIGN KEY (ontology_version,concept_id) REFERENCES public.ontology_concepts,
  FOREIGN KEY (batch_id,capture_id) REFERENCES public.source_captures,
  FOREIGN KEY (batch_id,event_id) REFERENCES public.events,
  CHECK ((scope_kind = 'capture' AND capture_id IS NOT NULL AND event_id IS NULL AND concept_id IS NULL)
      OR (scope_kind = 'event' AND event_id IS NOT NULL AND capture_id IS NULL AND concept_id IS NULL)
      OR (scope_kind = 'concept' AND concept_id IS NOT NULL AND event_id IS NULL AND capture_id IS NULL)
      OR (scope_kind = 'aggregate' AND num_nonnulls(capture_id,event_id,concept_id) = 0)),
  CHECK ((window_start IS NULL AND window_end IS NULL) OR
         (window_start IS NOT NULL AND window_end IS NOT NULL AND window_start < window_end)),
  CHECK ((value_status = 'observed' AND value IS NOT NULL AND value >= 0 AND value < 'Infinity'::numeric AND missing_reason IS NULL)
      OR (value_status = 'missing' AND value IS NULL AND missing_reason IS NOT NULL))
);
CREATE INDEX metric_series ON public.metric_values(batch_id,metric_id,observed_at DESC);
CREATE TABLE public.metric_inputs (
  batch_id text NOT NULL, id text NOT NULL, metric_value_id text NOT NULL, input_batch_id text NOT NULL,
  PRIMARY KEY (batch_id,id),
  capture_id text, event_id text, metric_input_id text,
  CHECK (num_nonnulls(capture_id,event_id,metric_input_id) = 1),
  UNIQUE NULLS NOT DISTINCT (batch_id,metric_value_id,input_batch_id,capture_id,event_id,metric_input_id),
  FOREIGN KEY (batch_id,metric_value_id) REFERENCES public.metric_values,
  FOREIGN KEY (input_batch_id,capture_id) REFERENCES public.source_captures,
  FOREIGN KEY (input_batch_id,event_id) REFERENCES public.events,
  FOREIGN KEY (input_batch_id,metric_input_id) REFERENCES public.metric_values,
  CHECK (metric_input_id IS NULL OR batch_id <> input_batch_id OR metric_value_id <> metric_input_id)
);
CREATE TABLE public.metric_coverage (
  batch_id text NOT NULL, metric_value_id text NOT NULL, coverage_id text NOT NULL,
  PRIMARY KEY (batch_id,metric_value_id,coverage_id),
  FOREIGN KEY (batch_id,metric_value_id) REFERENCES public.metric_values,
  FOREIGN KEY (batch_id,coverage_id) REFERENCES public.collection_coverage
);
CREATE TABLE public.progress_values (
  batch_id text NOT NULL REFERENCES public.data_batches(id), id text NOT NULL,
  ontology_version text NOT NULL, concept_id text NOT NULL,
  view text NOT NULL CHECK (view IN ('markets','occupations')),
  config_version text NOT NULL, method_id text,
  estimated_at timestamptz NOT NULL,
  conservative numeric(6,3) CHECK (conservative BETWEEN 0 AND 100),
  central numeric(6,3) CHECK (central BETWEEN 0 AND 100),
  optimistic numeric(6,3) CHECK (optimistic BETWEEN 0 AND 100),
  status text NOT NULL CHECK (status IN ('uninitialized','estimated','partial','insufficient_evidence')),
  change_cause text NOT NULL CHECK (change_cause IN ('initialization','evidence','data_correction','scope_revision','weight_revision','method_revision')),
  previous_batch_id text, previous_value_id text,
  assumptions jsonb NOT NULL CHECK (jsonb_typeof(assumptions) = 'object'),
  rationale text NOT NULL, input_sha256 public.sha256 NOT NULL, record_sha256 public.sha256 NOT NULL,
  PRIMARY KEY (batch_id,id),
  UNIQUE (batch_id,concept_id,view,estimated_at),
  FOREIGN KEY (batch_id,ontology_version) REFERENCES public.data_batches(id,ontology_version),
  FOREIGN KEY (ontology_version,concept_id) REFERENCES public.ontology_concepts,
  FOREIGN KEY (batch_id,config_version) REFERENCES public.data_batches(id,config_version),
  FOREIGN KEY (config_version,method_id) REFERENCES public.progress_methods,
  FOREIGN KEY (previous_batch_id,previous_value_id) REFERENCES public.progress_values MATCH FULL,
  CHECK (conservative <= central), CHECK (central <= optimistic), CHECK (conservative <= optimistic),
  CHECK ((status IN ('uninitialized','insufficient_evidence') AND num_nonnulls(conservative,central,optimistic) = 0)
      OR (status = 'estimated' AND num_nonnulls(conservative,central,optimistic) = 3 AND method_id IS NOT NULL)
      OR (status = 'partial' AND num_nonnulls(conservative,central,optimistic) BETWEEN 1 AND 2 AND method_id IS NOT NULL)),
  CHECK (previous_value_id IS NULL OR previous_batch_id <> batch_id OR previous_value_id <> id)
);
CREATE INDEX progress_history ON public.progress_values(batch_id,concept_id,view,estimated_at DESC);
CREATE TABLE public.progress_inputs (
  batch_id text NOT NULL, id text NOT NULL, progress_value_id text NOT NULL, input_batch_id text NOT NULL,
  PRIMARY KEY (batch_id,id),
  event_id text, metric_value_id text, child_progress_id text,
  CHECK (num_nonnulls(event_id,metric_value_id,child_progress_id) = 1),
  UNIQUE NULLS NOT DISTINCT (batch_id,progress_value_id,input_batch_id,event_id,metric_value_id,child_progress_id),
  FOREIGN KEY (batch_id,progress_value_id) REFERENCES public.progress_values,
  FOREIGN KEY (input_batch_id,event_id) REFERENCES public.events,
  FOREIGN KEY (input_batch_id,metric_value_id) REFERENCES public.metric_values,
  FOREIGN KEY (input_batch_id,child_progress_id) REFERENCES public.progress_values,
  CHECK (child_progress_id IS NULL OR batch_id <> input_batch_id OR progress_value_id <> child_progress_id)
);

-- Consumers explicitly select a ready data batch for queries or computation.
-- This schema has no weekly editions, publication channel or activation workflow.
-- Service validation complements the immutability guards in migration 002.
