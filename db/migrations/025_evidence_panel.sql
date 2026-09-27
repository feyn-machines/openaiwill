-- The evidence panel: people, their affiliations, their accounts, and every
-- check made against them.
--
-- 690 of the 710 readings are vendors describing their own products, and none
-- is a third-party verification. The panel is the set of accounts whose posts
-- can be something else. Which of them count, and for what, is not typed in by
-- hand: an account's state is derived from the checks logged against it
-- (rule:panel-lifecycle), its use from its role (panel_role.use), and whether
-- its post about a company is independent from its affiliations at the time of
-- the post (rule:panel-independence).
--
-- These are the tables sketched in section 6 of the business schema design and
-- never built. organizations/products stay unbuilt: affiliations name an
-- organisation in text and resolve to org_registry where it is a vendor we
-- track, which is the only case independence turns on.
--
-- No BEGIN/COMMIT here: db.migrate wraps each file in one transaction.

CREATE TABLE IF NOT EXISTS public.people (
    person_id       text        PRIMARY KEY,
    name            text        NOT NULL,
    aliases         jsonb       NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(aliases) = 'array'),
    identity_url    text,
    record_sha256   public.sha256 NOT NULL
);

-- One row per relation with one organisation over one period. A person who
-- leaves and returns has two rows. Unknown start stays null (missing is not
-- "always"); an open end means current.
CREATE TABLE IF NOT EXISTS public.person_affiliations (
    affiliation_id  text        PRIMARY KEY,
    person_id       text        NOT NULL REFERENCES public.people(person_id),
    org_name        text        NOT NULL,
    -- Set when the organisation is one we track as a vendor; independence is
    -- only ever decided against these.
    org_id          text        REFERENCES public.org_registry(org_id),
    relation        text        NOT NULL,
    role_title      text,
    started_on      date,
    ended_on        date,
    observed_on     date        NOT NULL,
    source_url      text,
    record_sha256   public.sha256 NOT NULL,
    CONSTRAINT person_affiliations_relation_check
        CHECK (relation IN ('employee', 'founder', 'investor', 'advisor', 'partner', 'academic', 'former')),
    CONSTRAINT person_affiliations_period_order
        CHECK (ended_on IS NULL OR started_on IS NULL OR ended_on >= started_on)
);
CREATE INDEX IF NOT EXISTS person_affiliations_by_person ON public.person_affiliations (person_id);
CREATE INDEX IF NOT EXISTS person_affiliations_by_org ON public.person_affiliations (org_id);

-- An account is keyed by platform and handle until its stable platform id is
-- resolved; the id, once known, is unique per platform. Handles change, ids do
-- not, so a handle that later points at a different id is a failed identity
-- check, not an update.
CREATE TABLE IF NOT EXISTS public.source_accounts (
    account_key         text        PRIMARY KEY,
    platform            text        NOT NULL CHECK (platform IN ('x')),
    handle              text        NOT NULL,
    platform_account_id text,
    owner_kind          text        NOT NULL CHECK (owner_kind IN ('person', 'organization')),
    person_id           text        REFERENCES public.people(person_id),
    org_name            text,
    org_id              text        REFERENCES public.org_registry(org_id),
    panel_role          text        NOT NULL,
    panel_use           text        NOT NULL,
    panel_state         text        NOT NULL,
    identity_grade      text        NOT NULL,
    identity_url        text,
    language            text        CHECK (language IN ('en', 'zh', 'both')),
    focus               text,
    added_from          text        NOT NULL,
    state_changed_at    timestamptz NOT NULL,
    record_sha256       public.sha256 NOT NULL,
    CONSTRAINT source_accounts_panel_role_check
        CHECK (panel_role IN ('evaluator', 'practitioner', 'adopter', 'researcher', 'commentator', 'executive', 'lab_insider', 'relay')),
    CONSTRAINT source_accounts_panel_use_check
        CHECK (panel_use IN ('verification', 'corroboration', 'heat', 'exclude')),
    CONSTRAINT source_accounts_panel_state_check
        CHECK (panel_state IN ('candidate', 'identity_confirmed', 'enabled', 'suspended', 'retired')),
    CONSTRAINT source_accounts_identity_grade_check
        CHECK (identity_grade IN ('first_party_link', 'official_bio', 'third_party_list')),
    CONSTRAINT source_accounts_owner_is_one
        CHECK ((owner_kind = 'person' AND person_id IS NOT NULL)
            OR (owner_kind = 'organization' AND person_id IS NULL AND org_name IS NOT NULL)),
    -- Nothing reaches enabled without a resolved platform id.
    CONSTRAINT source_accounts_enabled_needs_id
        CHECK (panel_state NOT IN ('identity_confirmed', 'enabled') OR platform_account_id IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS source_accounts_platform_id
    ON public.source_accounts (platform, platform_account_id) WHERE platform_account_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS source_accounts_platform_handle
    ON public.source_accounts (platform, lower(handle));

-- Append-only. State is derived from this, so a correction is a new check,
-- never an edit of an old one.
CREATE TABLE IF NOT EXISTS public.source_account_checks (
    check_id        text        PRIMARY KEY,
    account_key     text        NOT NULL REFERENCES public.source_accounts(account_key),
    check_kind      text        NOT NULL,
    checked_at      timestamptz NOT NULL,
    outcome         text        NOT NULL CHECK (outcome IN ('pass', 'fail', 'changed', 'unknown')),
    method          text        NOT NULL CHECK (method IN ('imported', 'collector', 'web', 'judge')),
    detail          jsonb       NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(detail) = 'object'),
    source_url      text,
    record_sha256   public.sha256 NOT NULL,
    CONSTRAINT source_account_checks_check_kind_check
        CHECK (check_kind IN ('identity', 'platform_id', 'affiliation', 'activity', 'yield'))
);
CREATE INDEX IF NOT EXISTS source_account_checks_by_account
    ON public.source_account_checks (account_key, check_kind, checked_at DESC);
