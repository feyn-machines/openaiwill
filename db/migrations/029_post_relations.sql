-- Posts keep their upstream: what they answer, quote or repost, and their thread.
--
-- The user's direction (2026-09-23): look at the posts and relate each one to
-- its event and its upstream post. quoted_source_id was already kept; replies
-- and reposts only kept a flag. These are facts in the raw page, not
-- judgements, so they are stored beside the post and backfilled from the raw
-- pages already on disk rather than re-collected.
--
-- The target ids are plain text, not foreign keys: an upstream post is often
-- one we never collected (a reply to someone outside every list), and the link
-- is still true.
--
-- full_text: public_excerpt is the first 280 characters, which cut long posts
-- in half before the judge ever saw them. The capture keeps the whole text.
--
-- No BEGIN/COMMIT here: db.migrate wraps each file in one transaction.

ALTER TABLE public.collected_sources
    ADD COLUMN reply_to_source_id text,
    ADD COLUMN reply_to_user_id text,
    ADD COLUMN repost_of_source_id text,
    ADD COLUMN conversation_id text;

CREATE INDEX IF NOT EXISTS collected_sources_by_reply_to ON public.collected_sources (reply_to_source_id);
CREATE INDEX IF NOT EXISTS collected_sources_by_quote_of ON public.collected_sources (quoted_source_id);
CREATE INDEX IF NOT EXISTS collected_sources_by_repost_of ON public.collected_sources (repost_of_source_id);
CREATE INDEX IF NOT EXISTS collected_sources_by_conversation ON public.collected_sources (conversation_id);

ALTER TABLE public.collected_captures ADD COLUMN full_text text;
