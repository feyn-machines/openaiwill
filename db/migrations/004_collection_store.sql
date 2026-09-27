-- Independent collection store: a raw evidence landing zone for the standalone
-- crawler, decoupled from the market-scoped calculation batches (data_batches).
-- Versioned by collection run; append-only per run; carries no market scope,
-- weights, metrics or progress. Later calculation batches select FROM here.
-- Credentials are never stored: only the monitored (public) account identity,
-- and raw response pages stay on disk, referenced here by SHA-256.

CREATE TABLE public.collection_runs (
  run_id text PRIMARY KEY,
  tool text NOT NULL,
  tool_sha256 jsonb CHECK (tool_sha256 IS NULL OR jsonb_typeof(tool_sha256) = 'object'),
  registry_sha256 public.sha256,
  window_start timestamptz NOT NULL,
  window_end timestamptz NOT NULL,
  started_at timestamptz NOT NULL,
  finished_at timestamptz,
  status text NOT NULL CHECK (status IN ('queries_exhausted','needs_attention')),
  ok boolean NOT NULL,
  concurrency integer CHECK (concurrency IS NULL OR concurrency >= 1),
  source_count bigint NOT NULL CHECK (source_count >= 0),
  capture_count bigint NOT NULL CHECK (capture_count >= 0),
  raw_pages jsonb NOT NULL CHECK (jsonb_typeof(raw_pages) = 'array'),
  run_sha256 public.sha256 NOT NULL,
  ingested_at timestamptz NOT NULL DEFAULT now(),
  CHECK (window_start < window_end),
  CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE TABLE public.collected_sources (
  run_id text NOT NULL REFERENCES public.collection_runs(run_id),
  source_id text NOT NULL,
  platform text NOT NULL,
  account_handle text NOT NULL,
  account_external_id text NOT NULL,
  company text,
  canonical_url text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('post')),
  is_reply boolean NOT NULL,
  is_repost boolean NOT NULL,
  quoted_source_id text,
  published_at timestamptz NOT NULL,
  record_sha256 public.sha256 NOT NULL,
  PRIMARY KEY (run_id, source_id),
  UNIQUE (run_id, platform, source_id)
);
-- The same post seen in several runs is intentionally several rows (observation
-- over time); this index supports cross-run dedup at query time.
CREATE INDEX collected_sources_identity ON public.collected_sources(platform, source_id);
CREATE INDEX collected_sources_account ON public.collected_sources(account_external_id, published_at DESC);

CREATE TABLE public.collected_captures (
  run_id text NOT NULL,
  capture_id text NOT NULL,
  source_id text NOT NULL,
  captured_at timestamptz NOT NULL,
  original_published_at timestamptz NOT NULL,
  text_sha256 public.sha256 NOT NULL,
  public_excerpt text,
  language text,
  metrics jsonb NOT NULL CHECK (jsonb_typeof(metrics) = 'object'),
  record_sha256 public.sha256 NOT NULL,
  PRIMARY KEY (run_id, capture_id),
  FOREIGN KEY (run_id, source_id) REFERENCES public.collected_sources(run_id, source_id),
  CHECK (original_published_at <= captured_at)
);
CREATE INDEX collected_captures_source ON public.collected_captures(run_id, source_id, captured_at DESC);

CREATE TABLE public.collection_gaps (
  run_id text NOT NULL REFERENCES public.collection_runs(run_id),
  id text NOT NULL,
  platform text NOT NULL,
  account_handle text,
  account_external_id text,
  window_start timestamptz NOT NULL,
  window_end timestamptz NOT NULL,
  checked_at timestamptz NOT NULL,
  status text NOT NULL CHECK (status IN ('complete','partial','failed')),
  retrieved_count bigint CHECK (retrieved_count IS NULL OR retrieved_count >= 0),
  attempts integer CHECK (attempts IS NULL OR attempts >= 0),
  stop_reason text,
  gap_note text,
  PRIMARY KEY (run_id, id),
  CHECK (window_start < window_end)
);
