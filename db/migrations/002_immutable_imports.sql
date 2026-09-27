-- A release is open only for its initial import, then sealed exactly once.
ALTER TABLE public.ontology_releases ADD COLUMN sealed_at timestamptz;
ALTER TABLE public.config_releases ADD COLUMN sealed_at timestamptz;

CREATE FUNCTION public.guard_release() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NEW.sealed_at IS NOT NULL THEN
      RAISE EXCEPTION 'Release must start unsealed' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
  END IF;
  IF TG_OP = 'UPDATE' AND OLD.sealed_at IS NULL AND NEW.sealed_at IS NOT NULL
     AND (to_jsonb(OLD) - 'sealed_at') = (to_jsonb(NEW) - 'sealed_at') THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'Release metadata is immutable; only its initial seal is allowed'
    USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER immutable_release BEFORE INSERT OR UPDATE OR DELETE ON public.ontology_releases
  FOR EACH ROW EXECUTE FUNCTION public.guard_release();
CREATE TRIGGER immutable_release BEFORE INSERT OR UPDATE OR DELETE ON public.config_releases
  FOR EACH ROW EXECUTE FUNCTION public.guard_release();

CREATE FUNCTION public.guard_catalogue_content() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  release_version text;
  release_sealed_at timestamptz;
BEGIN
  IF TG_OP <> 'INSERT' THEN
    RAISE EXCEPTION 'Catalogue records are immutable; import a new release'
      USING ERRCODE = '55000';
  END IF;
  release_version := to_jsonb(NEW) ->> TG_ARGV[1];
  -- FOR UPDATE conflicts with sealing the parent. A waiter sees its latest seal.
  EXECUTE format('SELECT sealed_at FROM public.%I WHERE version=$1 FOR UPDATE', TG_ARGV[0])
    INTO release_sealed_at USING release_version;
  IF release_sealed_at IS NOT NULL THEN
    RAISE EXCEPTION 'Cannot append records to sealed release %', release_version
      USING ERRCODE = '55000';
  END IF;
  RETURN NEW;
END;
$$;

CREATE FUNCTION public.guard_data_batch() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NEW.status <> 'loading' THEN
      RAISE EXCEPTION 'Data batch must start loading' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
  END IF;
  IF OLD.status <> 'loading' THEN
    RAISE EXCEPTION 'Completed data batch % is immutable', OLD.id USING ERRCODE = '55000';
  END IF;
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  IF NEW.status = 'ready' AND (
    NOT EXISTS (SELECT 1 FROM public.ontology_releases
                WHERE version=NEW.ontology_version AND sealed_at IS NOT NULL)
    OR NOT EXISTS (SELECT 1 FROM public.config_releases
                   WHERE version=NEW.config_version AND sealed_at IS NOT NULL)
  ) THEN
    RAISE EXCEPTION 'Ready data batch requires sealed ontology and configuration'
      USING ERRCODE = '55000';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER immutable_batch BEFORE INSERT OR UPDATE OR DELETE ON public.data_batches
  FOR EACH ROW EXECUTE FUNCTION public.guard_data_batch();

CREATE FUNCTION public.guard_batch_content() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  batch_ids text[];
  batch_key text;
  batch_status text;
BEGIN
  IF TG_OP = 'INSERT' THEN
    batch_ids := ARRAY[NEW.batch_id];
  ELSIF TG_OP = 'DELETE' THEN
    batch_ids := ARRAY[OLD.batch_id];
  ELSE
    batch_ids := ARRAY[OLD.batch_id, NEW.batch_id];
  END IF;
  -- Check both ends when a row moves. Stable lock order prevents opposite moves
  -- deadlocking; the lock also serializes writes with loading -> ready/failed.
  FOR batch_key IN SELECT DISTINCT value FROM unnest(batch_ids) AS ids(value) ORDER BY value LOOP
    SELECT status INTO batch_status FROM public.data_batches WHERE id=batch_key FOR UPDATE;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'Unknown data batch %', batch_key USING ERRCODE = '23503';
    END IF;
    IF batch_status <> 'loading' THEN
      RAISE EXCEPTION 'Data batch % is not loading; its records are immutable', batch_key
        USING ERRCODE = '55000';
    END IF;
  END LOOP;
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END;
$$;

-- TRUNCATE skips row triggers, so reject that bypass for all business tables.
CREATE FUNCTION public.reject_business_truncate() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'Business history cannot be truncated' USING ERRCODE = '55000';
END;
$$;

DO $$
DECLARE
  target_table text;
BEGIN
  FOREACH target_table IN ARRAY ARRAY['ontology_concepts','ontology_relations'] LOOP
    EXECUTE format('CREATE TRIGGER immutable_catalogue BEFORE INSERT OR UPDATE OR DELETE ON public.%I
      FOR EACH ROW EXECUTE FUNCTION public.guard_catalogue_content(%L,%L)',
      target_table, 'ontology_releases', 'ontology_version');
  END LOOP;
  FOREACH target_table IN ARRAY ARRAY['tags','metric_definitions','progress_methods','relation_weights'] LOOP
    EXECUTE format('CREATE TRIGGER immutable_catalogue BEFORE INSERT OR UPDATE OR DELETE ON public.%I
      FOR EACH ROW EXECUTE FUNCTION public.guard_catalogue_content(%L,%L)',
      target_table, 'config_releases', 'config_version');
  END LOOP;
  FOR target_table IN SELECT table_name FROM information_schema.columns
      WHERE table_schema='public' AND column_name='batch_id' LOOP
    EXECUTE format('CREATE TRIGGER immutable_batch_content BEFORE INSERT OR UPDATE OR DELETE ON public.%I
      FOR EACH ROW EXECUTE FUNCTION public.guard_batch_content()', target_table);
  END LOOP;
  FOR target_table IN SELECT tablename FROM pg_tables
      WHERE schemaname='public' AND tablename <> 'schema_migrations' LOOP
    EXECUTE format('CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON public.%I
      FOR EACH STATEMENT EXECUTE FUNCTION public.reject_business_truncate()', target_table);
  END LOOP;
END;
$$;
