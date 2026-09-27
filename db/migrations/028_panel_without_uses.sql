-- Accounts are not sorted into uses any more; posts are judged for what they say.
--
-- panel_use grouped accounts into verification / corroboration / heat and
-- demoted an account after five updates it had not posted about. On the first
-- verification trial that demoted 139 of 166 verification accounts: not posting
-- about a given product is the normal case and says nothing about an account.
-- The user's direction (2026-09-23): no uses - look at the posts, and relate
-- each post to its event and its upstream post. What an account still carries
-- is who it is (identity) and who it works for (affiliations, for independence),
-- plus whether it was excluded as engagement bait.
--
-- The yield checks written by the trial belonged to the removed rule and are
-- dropped with it rather than left as facts nothing reads.
--
-- No BEGIN/COMMIT here: db.migrate wraps each file in one transaction.

DELETE FROM public.source_account_checks WHERE check_kind = 'yield';

ALTER TABLE public.source_account_checks DROP CONSTRAINT source_account_checks_check_kind_check;
ALTER TABLE public.source_account_checks ADD CONSTRAINT source_account_checks_check_kind_check
    CHECK (check_kind IN ('identity', 'platform_id', 'affiliation', 'activity', 'profile'));

ALTER TABLE public.source_accounts ADD COLUMN excluded boolean NOT NULL DEFAULT false;
UPDATE public.source_accounts SET excluded = (panel_use = 'exclude');
ALTER TABLE public.source_accounts DROP COLUMN panel_use;
