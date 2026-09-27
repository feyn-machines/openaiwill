"""Which O*NET tasks a market activity corresponds to.

The market side of the ontology describes work in its own words — "Check
citations attachments and filing formats" — while the occupation side carries
O*NET's originals — "Gather and analyze research data, such as statutes,
decisions…". The same job, written twice, with no link between them.

This is that link. It turns the 614 market work items from a half-built parallel
catalogue into a translation layer: they keep the market's language and gain the
authoritative task set underneath.

The candidate pool is whatever the market→occupation map already narrowed to, so
an activity is only matched against tasks from occupations that actually do that
market's work. Without that step the pool would be all 18,838 tasks and would not
fit in a request.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from secrets import token_hex

from psycopg.types.json import Jsonb

from . import checkpoint
from .classify import Classifier, Option
from .pipeline import digest

METHOD_VERSION = checkpoint.ACTIVITY_TASK

# A correspondence is a stronger claim than "this group might contain someone",
# so it needs a clear majority rather than a filter's benefit of the doubt.
SELECT_ABOVE = 0.6

QUESTION = (
    "Is this O*NET task the same work as the activity, or part of it? "
    "Answer on the work itself, not on shared vocabulary."
)
CRITERIA = {
    "true": "Doing this task is doing the activity, or a recognised part of it.",
    "false": "Different work, even if some words are shared.",
}


def activities(conn, ontology_version: str, only: list[str] | None = None) -> list[dict]:
    """Market work items, each with its market and that market's occupations.

    A market activity carries no definition of its own — the label is all there
    is — so the market label rides along as context.
    """
    clause = " AND m.id = ANY(%s)" if only else ""
    params: list = [ontology_version]
    if only:
        params.append(only)
    return conn.execute(
        f"""SELECT w.id AS activity_id, w.label_en AS activity, w.label_zh_cn,
                   m.id AS market_id, m.label_en AS market
              FROM public.ontology_relations r
              JOIN public.ontology_concepts w
                ON w.id = r.child_id AND w.ontology_version = r.ontology_version
              JOIN public.ontology_concepts m
                ON m.id = r.parent_id AND m.ontology_version = r.ontology_version
             WHERE r.kind = 'has_work' AND r.ontology_version = %s{clause}
             ORDER BY m.id, w.id""",
        params,
    ).fetchall()


def candidate_tasks(conn, ontology_version: str, market_id: str) -> list[Option]:
    """Tasks of the occupations this market was mapped to."""
    rows = conn.execute(
        """SELECT DISTINCT t.child_id AS task_id, w.label_en
             FROM public.market_occupation_edges mo
             JOIN public.ontology_relations t
               ON t.parent_id = mo.occupation_id AND t.kind = 'has_task'
              AND t.ontology_version = mo.ontology_version
             JOIN public.ontology_concepts w
               ON w.id = t.child_id AND w.ontology_version = t.ontology_version
            WHERE mo.market_id = %s AND mo.ontology_version = %s
              AND mo.status = 'candidate'
            ORDER BY w.label_en""",
        (market_id, ontology_version),
    ).fetchall()
    return [Option(row["task_id"], row["label_en"]) for row in rows]


def markets_with_pool(conn, ontology_version: str) -> set[str]:
    """Markets whose mapped occupations actually carry tasks.

    Asked before the loop rather than inside it, so an activity with nothing to
    match against never opens a run. Twenty-three activities sit behind markets
    that mapped to no occupation, and a daily rerun should be silent about them
    rather than leaving an empty run row each time.
    """
    return {
        row["market_id"]
        for row in conn.execute(
            """SELECT DISTINCT mo.market_id
                 FROM public.market_occupation_edges mo
                 JOIN public.ontology_relations t
                   ON t.parent_id = mo.occupation_id AND t.kind = 'has_task'
                  AND t.ontology_version = mo.ontology_version
                WHERE mo.ontology_version = %s AND mo.status = 'candidate'""",
            (ontology_version,),
        )
    }


def run(conn, *, ontology_version: str = "1.0.0", only_markets: list[str] | None = None,
        limit: int | None = None, resume: bool = True, note: str = "",
        progress=None) -> dict:
    rows = activities(conn, ontology_version, only_markets)
    if not rows:
        raise ValueError("No market activities; nothing to map")
    pooled = markets_with_pool(conn, ontology_version)
    empty_pool = sum(1 for row in rows if row["market_id"] not in pooled)
    rows = [row for row in rows if row["market_id"] in pooled]
    # Filter before limiting: limit on a resumed run should mean new activities.
    already = checkpoint.done(conn, METHOD_VERSION) if resume else set()
    skipped = sum(1 for row in rows if row["activity_id"] in already)
    rows = [row for row in rows if row["activity_id"] not in already]
    if limit:
        rows = rows[:limit]
    if not rows:
        return {"run_id": None, "activities": 0, "activities_skipped": skipped,
                "questions_asked": 0, "matches": 0, "activities_without_pool": empty_pool,
                "activities_incomplete": 0, "fallback_batches": 0,
                "failed_batches": 0, "elapsed_seconds": 0.0}

    step = Classifier(QUESTION, CRITERIA, "activity", "task")
    run_id = f"map-activity-task-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{token_hex(3)}"
    started = datetime.now(timezone.utc)
    conn.execute(
        """INSERT INTO public.judgment_runs
           (run_id, judge, model, task, prompt_sha256, rubric_sha256, method_version,
            params, started_at, status, item_count, decided_count, run_sha256)
           VALUES (%s, 'typesafe', %s, 'serves_market', %s, %s, %s, %s, %s, 'running', %s, 0, %s)""",
        (run_id, step.primary.model,
         digest({"question": QUESTION, "criteria": CRITERIA}),
         digest({"select_above": SELECT_ABOVE}), METHOD_VERSION,
         Jsonb({"note": note, "select_above": SELECT_ABOVE, "activities": len(rows),
                "activities_skipped": skipped, "resume": resume}),
         started, len(rows),
         digest({"activities": [r["activity_id"] for r in rows],
                 "method_version": METHOD_VERSION})),
    )

    asked = matched = incomplete = 0
    for position, row in enumerate(rows, 1):
        failures_before = step.failed_batches
        here = 0
        options = candidate_tasks(conn, ontology_version, row["market_id"])
        state = {"activity": row["activity"], "market": row["market"]}
        readings = step.classify(state, options, progress)
        asked += len(options)
        for reading in readings:
            if reading.value <= SELECT_ABOVE:
                continue
            edge = {
                "ontology_version": ontology_version,
                "activity_id": row["activity_id"],
                "task_id": reading.option_id,
                "judge": reading.judge,
                "method": "ai_proposed",
                "status": "candidate",
                "confidence": round(reading.value, 3),
                "rationale": f"noul={reading.value:.3f} for «{row['activity']}»",
                "judgment_run_id": run_id,
                "reviewed_by": None,
                "reviewed_at": None,
            }
            edge["record_sha256"] = digest(edge)
            columns = list(edge)
            conn.execute(
                f"""INSERT INTO public.activity_task_edges ({', '.join(columns)})
                    VALUES ({', '.join(['%s'] * len(columns))})
                    ON CONFLICT (ontology_version, activity_id, task_id) DO NOTHING""",
                [edge[c] for c in columns],
            )
            matched += 1
            here += 1

        if checkpoint.completed(step.failed_batches, failures_before):
            checkpoint.mark(conn, METHOD_VERSION, row["activity_id"], run_id,
                            here, len(options))
        else:
            incomplete += 1

        if progress and position % 25 == 0:
            progress(f"  {position}/{len(rows)} activities, {matched} matches, "
                     f"{asked:,} questions asked")

    failed = step.failed_batches
    conn.execute(
        """UPDATE public.judgment_runs
              SET status = %s, finished_at = %s, decided_count = %s, params = params || %s
            WHERE run_id = %s""",
        ("completed" if failed == 0 and incomplete == 0 else "completed_with_failures",
         datetime.now(timezone.utc), asked,
         Jsonb({"fallback_batches": step.fallback_batches, "failed_batches": failed,
                "empty_pool": empty_pool, "activities_incomplete": incomplete}), run_id),
    )
    return {
        "run_id": run_id, "activities": len(rows), "activities_skipped": skipped,
        "activities_incomplete": incomplete, "questions_asked": asked,
        "matches": matched, "activities_without_pool": empty_pool,
        "fallback_batches": step.fallback_batches, "failed_batches": failed,
        "elapsed_seconds": round(time.time() - started.timestamp(), 1),
    }
