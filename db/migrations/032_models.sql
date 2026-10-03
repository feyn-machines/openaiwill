-- Which model an update is about.
--
-- Migration 020 dropped products/product_versions with the capability layer and
-- left updates with subject_key alone: a free-text slug written for
-- deduplication, where one model appears under a different key in almost every
-- update. These tables give the model its own field. Products stay out: a
-- product is never a row here.
--
-- Registry rows are machine-proposed. A model enters as a candidate from a
-- mention and is confirmed when its owner's own release update names it
-- (model_identification.confirm).
--
-- No BEGIN/COMMIT here: db.migrate wraps each file in one transaction.

ALTER TABLE public.judgment_runs DROP CONSTRAINT judgment_runs_task_check;
ALTER TABLE public.judgment_runs ADD CONSTRAINT judgment_runs_task_check
    CHECK (task IN ('requires', 'blocked_by', 'demonstrates', 'event_kind', 'gate_state', 'serves_market',
                    'verification', 'model_identification'));

CREATE TABLE IF NOT EXISTS public.models (
    model_id            text        PRIMARY KEY CHECK (model_id ~ '^model:[a-z0-9-]+:[a-z0-9-]+$'),
    org_id              text        REFERENCES public.org_registry(org_id),
    -- The owner as the post writes it, for an owner outside the registry.
    owner_name          text,
    level               text        NOT NULL CHECK (level IN ('family', 'release')),
    parent_model_id     text        REFERENCES public.models(model_id),
    name                text        NOT NULL CHECK (name <> ''),
    version             text,
    variant             text,
    released_at         timestamptz,
    status              text        NOT NULL CHECK (status IN ('candidate', 'confirmed')),
    first_seen_event_id text        NOT NULL,
    created_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT models_family_has_no_parent CHECK (level = 'release' OR parent_model_id IS NULL),
    CONSTRAINT models_family_has_no_version CHECK (level = 'release' OR (version IS NULL AND variant IS NULL))
);
CREATE INDEX IF NOT EXISTS models_by_parent ON public.models (parent_model_id);

-- One normalised surface form resolves to one model.
CREATE TABLE IF NOT EXISTS public.model_aliases (
    alias    text PRIMARY KEY CHECK (alias <> ''),
    model_id text NOT NULL REFERENCES public.models(model_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS model_aliases_by_model ON public.model_aliases (model_id);

-- The model field of an update.
CREATE TABLE IF NOT EXISTS public.event_models (
    event_id   text         NOT NULL REFERENCES public.extracted_events(event_id) ON DELETE CASCADE,
    model_id   text         NOT NULL REFERENCES public.models(model_id) ON DELETE CASCADE,
    role       text         NOT NULL CHECK (role IN ('subject', 'adopted', 'distributed', 'compared')),
    mention    text         NOT NULL CHECK (mention <> ''),
    confidence numeric(4,3) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    run_id     text         NOT NULL REFERENCES public.judgment_runs(run_id),
    PRIMARY KEY (event_id, model_id, role)
);
CREATE INDEX IF NOT EXISTS event_models_by_model ON public.event_models (model_id);

-- An update that was read and names no model has a row here and none in
-- event_models; an update with no row here has not been read yet.
CREATE TABLE IF NOT EXISTS public.event_model_checks (
    event_id       text        PRIMARY KEY REFERENCES public.extracted_events(event_id) ON DELETE CASCADE,
    run_id         text        NOT NULL REFERENCES public.judgment_runs(run_id),
    method_version text        NOT NULL,
    mentions       integer     NOT NULL CHECK (mentions >= 0),
    checked_at     timestamptz NOT NULL
);
