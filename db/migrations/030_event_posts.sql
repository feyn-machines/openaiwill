-- Which posts belong to which event, and how.
--
-- Derived, not collected: rebuilt in full from extracted_event_sources (the
-- event's own posts) and the upstream links on collected_sources (migration
-- 029). A post answering, quoting or reposting an event's post belongs to that
-- event, and so does whatever answers it in turn; a post with no upstream that
-- names the product within a week is a mention (rule:post-links-to-event).
--
-- Evidence is judged on these posts; attention counts them. Because the table
-- is rebuilt, a new collection run or a corrected relation needs no migration
-- of old rows - only a rebuild.
--
-- No BEGIN/COMMIT here: db.migrate wraps each file in one transaction.

CREATE TABLE IF NOT EXISTS public.event_posts (
    event_id        text        NOT NULL,
    source_id       text        NOT NULL,
    link            text        NOT NULL,
    depth           smallint    NOT NULL CHECK (depth >= 0),
    via_source_id   text,
    built_at        timestamptz NOT NULL,
    PRIMARY KEY (event_id, source_id),
    CONSTRAINT event_posts_link_check
        CHECK (link IN ('source', 'reply', 'quote', 'repost', 'mention')),
    CONSTRAINT event_posts_source_is_depth_zero
        CHECK ((link = 'source') = (depth = 0))
);
CREATE INDEX IF NOT EXISTS event_posts_by_source ON public.event_posts (source_id);
