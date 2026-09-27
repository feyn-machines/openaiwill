-- Profile snapshots join the account check log.
--
-- A lookup returns the account's public profile along with its id. Keeping it
-- as a check (append-only, like every other check) lets a changed bio send the
-- account's affiliation back for review - the signal that would have caught a
-- move like Karpathy's to Anthropic without anyone reading the news.
--
-- No BEGIN/COMMIT here: db.migrate wraps each file in one transaction.

ALTER TABLE public.source_account_checks DROP CONSTRAINT source_account_checks_check_kind_check;
ALTER TABLE public.source_account_checks ADD CONSTRAINT source_account_checks_check_kind_check
    CHECK (check_kind IN ('identity', 'platform_id', 'affiliation', 'activity', 'yield', 'profile'));
ALTER TABLE public.source_account_checks DROP CONSTRAINT source_account_checks_method_check;
ALTER TABLE public.source_account_checks ADD CONSTRAINT source_account_checks_method_check
    CHECK (method IN ('imported', 'collector', 'crawler', 'web', 'judge'));
