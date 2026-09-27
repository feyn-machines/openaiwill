"""Which occupations do the work of a market.

The two halves of the ontology never met: 614 work items hang off 265 markets,
18,838 tasks hang off 923 occupations, and the two sets do not overlap at all. A
market therefore had two to five work items under it and no real denominator.
This is the bridge, and it is what lets a market carry a percentage.

Narrowed through the SOC major groups rather than asking every occupation about
every market. Flat, that is 265 x 1,016 = 269,240 questions; through the groups
it is about 24,000 — the same number of calls, 84-93% of the tokens saved.

The cost of narrowing is recall: an occupation in a group the first step missed
is never asked. The group step therefore uses a deliberately low bar, because it
is a filter, not a finding.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from secrets import token_hex

from psycopg.types.json import Jsonb

from . import checkpoint
from .classify import Classifier, Option
from .pipeline import digest

METHOD_VERSION = checkpoint.MARKET_OCCUPATION

# Jev's noul is the certainty itself: 0.5 is the undecided midpoint.
# The group step is a filter, so it keeps anything not clearly rejected; the
# occupation step is the finding, so it asks for a real majority.
GROUP_ABOVE = 0.4
OCCUPATION_ABOVE = 0.6

GROUP_QUESTION = (
    "Could any occupation in this major group do the work described by this "
    "activity as a recognised part of the job?"
)
GROUP_CRITERIA = {
    "true": "At least one occupation in this group plausibly does this work.",
    "false": "No occupation in this group does this work.",
}

OCCUPATION_QUESTION = (
    "Do people in this occupation do the work described by this activity, "
    "as a recognised part of their job?"
)
OCCUPATION_CRITERIA = {
    "true": "This occupation routinely does this work as part of the job.",
    "false": "This occupation does not do this work, or only shares vocabulary with it.",
}


def markets(conn, ontology_version: str) -> list[dict]:
    """Every market, with the work items that say what it actually covers.

    A market label is terse ("Contract review"); the work items under it are the
    only thing that says what that involves, so both go to the judge.
    """
    return conn.execute(
        """SELECT m.id AS market_id, m.label_en, m.label_zh_cn,
                  array_remove(array_agg(w.label_en ORDER BY w.id), NULL) AS activities
             FROM public.ontology_concepts m
             LEFT JOIN public.ontology_relations r
                    ON r.parent_id = m.id AND r.kind = 'has_work'
                   AND r.ontology_version = m.ontology_version
             LEFT JOIN public.ontology_concepts w
                    ON w.id = r.child_id AND w.ontology_version = m.ontology_version
            WHERE m.kind = 'market' AND m.ontology_version = %s
            GROUP BY m.id, m.label_en, m.label_zh_cn
            ORDER BY m.id""",
        (ontology_version,),
    ).fetchall()


def groups_with_members(conn, ontology_version: str) -> dict[str, dict]:
    """SOC major groups, each carrying its occupations."""
    rows = conn.execute(
        """SELECT g.id AS group_id, g.label_en AS group_label,
                  o.id AS occupation_id, o.label_en AS occupation_label
             FROM public.ontology_concepts g
             JOIN public.ontology_relations r
               ON r.parent_id = g.id AND r.kind = 'has_occupation'
              AND r.ontology_version = g.ontology_version
             JOIN public.ontology_concepts o
               ON o.id = r.child_id AND o.ontology_version = g.ontology_version
            WHERE g.kind = 'occupation_group' AND g.ontology_version = %s
            ORDER BY g.id, o.id""",
        (ontology_version,),
    ).fetchall()
    out: dict[str, dict] = {}
    for row in rows:
        entry = out.setdefault(row["group_id"], {"label": row["group_label"], "members": []})
        entry["members"].append(Option(row["occupation_id"], row["occupation_label"]))
    return out


def _state(market: dict) -> dict:
    return {
        "market": market["label_en"],
        **({"activities": list(market["activities"])} if market["activities"] else {}),
    }


def run(conn, *, ontology_version: str | None = None, limit: int | None = None,
        resume: bool = True, note: str = "", progress=None) -> dict:
    if ontology_version is None:
        found = conn.execute(
            "SELECT version FROM public.ontology_releases ORDER BY version DESC LIMIT 1"
        ).fetchone()
        if not found:
            raise ValueError("No ontology release imported; run the ontology import first")
        ontology_version = found["version"]

    all_markets = markets(conn, ontology_version)
    groups = groups_with_members(conn, ontology_version)
    if not all_markets or not groups:
        raise ValueError("No markets or no occupation groups; nothing to map")
    # Filter before limiting, so limit=5 on a resumed run means five markets that
    # have not been decided rather than five that probably have.
    already = checkpoint.done(conn, METHOD_VERSION) if resume else set()
    skipped = sum(1 for m in all_markets if m["market_id"] in already)
    all_markets = [m for m in all_markets if m["market_id"] not in already]
    if limit:
        all_markets = all_markets[:limit]
    if not all_markets:
        return {"run_id": None, "markets": 0, "markets_skipped": skipped,
                "questions_asked": 0, "edges": 0, "markets_incomplete": 0,
                "fallback_batches": 0, "failed_batches": 0, "elapsed_seconds": 0.0}

    group_options = [Option(gid, body["label"]) for gid, body in groups.items()]
    group_step = Classifier(GROUP_QUESTION, GROUP_CRITERIA, "market", "major_group")
    occupation_step = Classifier(OCCUPATION_QUESTION, OCCUPATION_CRITERIA, "market", "occupation")

    run_id = f"map-market-occupation-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{token_hex(3)}"
    started = datetime.now(timezone.utc)
    conn.execute(
        """INSERT INTO public.judgment_runs
           (run_id, judge, model, task, prompt_sha256, rubric_sha256, method_version,
            params, started_at, status, item_count, decided_count, run_sha256)
           VALUES (%s, 'typesafe', %s, 'serves_market', %s, %s, %s, %s, %s, 'running', %s, 0, %s)""",
        (run_id, group_step.primary.model,
         digest({"group": GROUP_QUESTION, "occupation": OCCUPATION_QUESTION}),
         digest({"group_above": GROUP_ABOVE, "occupation_above": OCCUPATION_ABOVE}),
         METHOD_VERSION,
         Jsonb({"note": note, "group_above": GROUP_ABOVE,
                "occupation_above": OCCUPATION_ABOVE,
                "groups": len(group_options), "markets": len(all_markets),
                "markets_skipped": skipped, "resume": resume}),
         started, len(all_markets),
         # Identity of what this run was asked to do. The edge set it produces is
         # hashed separately when the run finishes.
         digest({"markets": [m["market_id"] for m in all_markets],
                 "method_version": METHOD_VERSION})),
    )

    asked = selected = incomplete = 0
    groups_hit: list[int] = []
    for position, market in enumerate(all_markets, 1):
        # Both classifiers count separately; a market is complete only if neither
        # lost a batch while it was being decided.
        failures_before = group_step.failed_batches + occupation_step.failed_batches
        here = 0
        state = _state(market)
        shortlist = [
            reading.option_id
            for reading in group_step.classify(state, group_options, progress)
            if reading.value > GROUP_ABOVE
        ]
        asked += len(group_options)
        groups_hit.append(len(shortlist))

        candidates = [option for gid in shortlist for option in groups[gid]["members"]]
        readings = occupation_step.classify(state, candidates, progress) if candidates else []
        asked += len(candidates)

        for reading in readings:
            if reading.value <= OCCUPATION_ABOVE:
                continue
            row = {
                "ontology_version": ontology_version,
                "market_id": market["market_id"],
                "occupation_id": reading.option_id,
                "judge": reading.judge,
                "method": "ai_proposed",
                "status": "candidate",
                "confidence": round(reading.value, 3),
                "rationale": f"noul={reading.value:.3f} for «{market['label_en']}»",
                "judgment_run_id": run_id,
                "reviewed_by": None,
                "reviewed_at": None,
            }
            row["record_sha256"] = digest(row)
            columns = list(row)
            conn.execute(
                f"""INSERT INTO public.market_occupation_edges ({', '.join(columns)})
                    VALUES ({', '.join(['%s'] * len(columns))})
                    ON CONFLICT (ontology_version, market_id, occupation_id) DO NOTHING""",
                [row[c] for c in columns],
            )
            selected += 1
            here += 1

        if checkpoint.completed(
                group_step.failed_batches + occupation_step.failed_batches,
                failures_before):
            checkpoint.mark(conn, METHOD_VERSION, market["market_id"], run_id,
                            here, len(group_options) + len(candidates))
        else:
            incomplete += 1

        if progress and position % 10 == 0:
            progress(f"  {position}/{len(all_markets)} markets, {selected} edges, "
                     f"{asked:,} questions asked")

    fallback = group_step.fallback_batches + occupation_step.fallback_batches
    failed = group_step.failed_batches + occupation_step.failed_batches
    conn.execute(
        """UPDATE public.judgment_runs
              SET status = %s, finished_at = %s, decided_count = %s,
                  params = params || %s
            WHERE run_id = %s""",
        ("completed" if failed == 0 and incomplete == 0 else "completed_with_failures",
         datetime.now(timezone.utc), asked,
         Jsonb({"fallback_batches": fallback, "failed_batches": failed,
                "markets_incomplete": incomplete}), run_id),
    )
    return {
        "run_id": run_id,
        "markets": len(all_markets),
        "markets_skipped": skipped,
        "markets_incomplete": incomplete,
        "questions_asked": asked,
        "edges": selected,
        "groups_per_market": round(sum(groups_hit) / len(groups_hit), 1) if groups_hit else 0,
        "fallback_batches": fallback,
        "failed_batches": failed,
        "elapsed_seconds": round(time.time() - started.timestamp(), 1),
    }
