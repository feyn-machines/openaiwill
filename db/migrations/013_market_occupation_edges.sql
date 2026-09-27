-- Which occupations do the work of a market.
--
-- The two halves of the ontology never met: 614 work items hang off 265 markets
-- and 18,838 tasks hang off 923 occupations, with zero overlap between them. A
-- market therefore had two to five work items under it and no way to reach a
-- real denominator. This table is the bridge, and it is the reason a market can
-- carry a percentage at all.
--
-- It is a judgment, not a structural fact: the ontology keeps its five concept
-- kinds and four relations untouched, and every row here lands as ai_proposed +
-- candidate like every other edge a machine proposed.
--
-- Judged by TypeSafe Jev, not by the comparison model. On 177,771 pairs the two
-- agreed 97.5% of the time, but the disagreement runs about five to one toward
-- the comparison model saying yes. A looser judge on a multi-select question
-- selects more occupations, which dilutes the denominator and blurs one market
-- into the next -- the same failure that made forty-one work traits behave as
-- capabilities. Multi-select records only what was chosen, so nothing downstream
-- can detect over-selection after the fact.
--
-- An occupation belongs to many markets (a legal secretary serves both document
-- drafting and contract review), so market shares overlap. Counts per market are
-- correct; a sum across markets is not, and nothing should present one.

CREATE TABLE IF NOT EXISTS public.market_occupation_edges (
    ontology_version text        NOT NULL,
    market_id        text        NOT NULL,
    occupation_id    text        NOT NULL,
    -- Which judge produced this row. The last time a sweep ran, TypeSafe's
    -- credit ran out partway and the comparison model finished the job; nothing
    -- recorded the switch, so a permissive reading and a strict one sat in the
    -- same column indistinguishable. Never again: the fallback is allowed, but
    -- it has to leave a mark.
    judge            text        NOT NULL,
    method           text        NOT NULL,
    status           text        NOT NULL,
    -- Multi-select gives one answer for a whole list, so there is no per-option
    -- confidence to record. NULL here means "not applicable to this method",
    -- not "unknown", and the column exists so a later per-item method can fill it.
    confidence       numeric,
    rationale        text        NOT NULL,
    judgment_run_id  text        NOT NULL,
    reviewed_by      text,
    reviewed_at      timestamptz,
    record_sha256    text        NOT NULL,
    PRIMARY KEY (ontology_version, market_id, occupation_id),
    CONSTRAINT market_occupation_edges_method_check
        CHECK (method IN ('ai_proposed', 'reviewed', 'imported')),
    CONSTRAINT market_occupation_edges_status_check
        CHECK (status IN ('candidate', 'reviewed', 'rejected')),
    -- The same guard the capability edges carry: a machine proposal may never
    -- present itself as settled.
    CONSTRAINT market_occupation_edges_ai_cannot_assert
        CHECK (method <> 'ai_proposed' OR status IN ('candidate', 'rejected')),
    CONSTRAINT market_occupation_edges_confidence_range
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    CONSTRAINT market_occupation_edges_judge_check
        CHECK (judge IN ('typesafe', 'deepseek'))
);

CREATE INDEX IF NOT EXISTS market_occupation_edges_by_occupation
    ON public.market_occupation_edges (occupation_id);

CREATE INDEX IF NOT EXISTS market_occupation_edges_by_run
    ON public.market_occupation_edges (judgment_run_id);

-- So "how much of this mapping came from the fallback" is one query, not an
-- archaeology exercise.
CREATE INDEX IF NOT EXISTS market_occupation_edges_by_judge
    ON public.market_occupation_edges (judge);
