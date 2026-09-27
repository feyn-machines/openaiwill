-- A source's identity does not belong to a collection run; its snapshot does.
--
-- collected_sources was keyed (run_id, source_id), so every run that saw a post
-- wrote the post's identity again: 4,538 rows for 2,070 posts, one of them
-- stored seven times. Across all of those copies the number of sources whose
-- platform, URL, kind, handle or publication time differed between runs is
-- ZERO - they are byte-identical by construction, because those fields are what
-- makes it the same post.
--
-- collected_captures is the opposite and stays exactly as it is: 1,248 of the
-- 2,070 sources have genuinely different snapshots between runs, because the
-- metrics move. A capture per run is a time series. A source per run is a copy.
--
-- After this, "sources collected" means what a reader assumes it means. Before
-- it, any count of that table overstated the corpus by 2.2x.
--
-- Also drops the superseded extraction generation. The same collection window
-- was extracted twice: once under the free-form vocabulary that produced 755
-- events, then again under event_kind-2.0.0, which produced 581. Only the
-- second is published, nothing downstream references the first (no reading, no
-- gate state, no checkpoint), and keeping both makes every event count
-- ambiguous. coverage.event_generations recorded the split; it now records one
-- generation, which is the truth.
--
-- No BEGIN/COMMIT here: db.migrate already wraps each file in one transaction,
-- and a COMMIT inside it ends that transaction early, so the rest of the file
-- runs unprotected and a concurrent migration can see a half-applied schema.

-- 1. The superseded generation.
DELETE FROM public.extracted_event_relations
 WHERE from_event_id IN (SELECT event_id FROM public.extracted_events
                          WHERE kind_vocabulary <> 'event_kind-2.0.0')
    OR to_event_id IN (SELECT event_id FROM public.extracted_events
                        WHERE kind_vocabulary <> 'event_kind-2.0.0');

DELETE FROM public.extracted_event_sources
 WHERE event_id IN (SELECT event_id FROM public.extracted_events
                     WHERE kind_vocabulary <> 'event_kind-2.0.0');

DELETE FROM public.extracted_events WHERE kind_vocabulary <> 'event_kind-2.0.0';

-- 2. Re-key sources on identity alone.
ALTER TABLE public.collected_captures
    DROP CONSTRAINT IF EXISTS collected_captures_run_id_source_id_fkey;
ALTER TABLE public.extracted_event_sources
    DROP CONSTRAINT IF EXISTS extracted_event_sources_run_id_source_id_fkey;

-- The run that first saw each post is the one kept: earliest wins, so the
-- run_id column keeps meaning "first seen in" rather than "last overwritten by".
DELETE FROM public.collected_sources a
 USING public.collected_sources b
 WHERE a.source_id = b.source_id AND a.run_id > b.run_id;

ALTER TABLE public.collected_sources
    DROP CONSTRAINT collected_sources_pkey,
    ADD CONSTRAINT collected_sources_pkey PRIMARY KEY (source_id);

-- The children keep their own run_id: which run produced THIS capture, and
-- which run produced THIS event's source link, are both still facts. They
-- simply no longer have to agree with the run that first saw the post.
ALTER TABLE public.collected_captures
    ADD CONSTRAINT collected_captures_source_fkey
        FOREIGN KEY (source_id) REFERENCES public.collected_sources (source_id);
ALTER TABLE public.extracted_event_sources
    ADD CONSTRAINT extracted_event_sources_source_fkey
        FOREIGN KEY (source_id) REFERENCES public.collected_sources (source_id);
