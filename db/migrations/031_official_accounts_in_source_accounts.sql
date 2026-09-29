-- Official accounts join the one table of accounts the crawler collects from.
--
-- Until now the crawler read official accounts from datasets/official-x-accounts.json
-- and panel accounts from a file exported out of this table, so every run passed
-- through a file written for the occasion. The user's direction (2026-09-28):
-- accounts live in the database and the crawler reads them there. Official
-- accounts become panel_role 'official' (vocabulary panel_role), owned by their
-- organisation (owner_kind 'organization', org_id set), so rule:panel-independence
-- keeps an organisation's own account from confirming that organisation's claims.
--
-- No BEGIN/COMMIT here: db.migrate wraps each file in one transaction.

ALTER TABLE public.source_accounts DROP CONSTRAINT source_accounts_panel_role_check;
ALTER TABLE public.source_accounts ADD CONSTRAINT source_accounts_panel_role_check
    CHECK (panel_role IN ('evaluator', 'practitioner', 'adopter', 'researcher', 'commentator', 'executive', 'lab_insider', 'relay', 'official'));
