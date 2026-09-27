"""Which gates hold a market activity in place.

A gate is a condition that does not lift when models improve: a licensed
clinician must sign, a person must be physically present, someone must carry
payment authority. It says nothing about capability, which is why it survives
the removal of the capability layer — and why it is the thing that stops a
physical job from reading as automated because part of it involves talking.

Attached to the 614 activities rather than swept across 17,237 tasks. A gate
holds a kind of work, not one sentence of task text, and the sweep drops from
17,237 calls to 614. Eleven gates fit in one request, so it is one call each.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from secrets import token_hex

from psycopg.types.json import Jsonb

from .activity_mapping import activities
from . import checkpoint
from .classify import Classifier, Option
from .pipeline import digest

METHOD_VERSION = checkpoint.ACTIVITY_GATE

SELECT_ABOVE = 0.6

QUESTION = (
    "Does this condition hold this activity in place — so that even software "
    "that could do the work perfectly would still need a person?"
)
CRITERIA = {
    "true": "The condition governs the output of this activity itself.",
    "false": "The condition does not govern this activity, or merely shares its setting.",
}


def gates(conn) -> list[Option]:
    rows = conn.execute(
        """SELECT gate_id, label_en, definition_en FROM public.gates
            WHERE lifecycle = 'active' ORDER BY gate_id"""
    ).fetchall()
    # The definition carries what the label cannot: a gate named "tool use" only
    # means something once you read that it is about a person operating a tool.
    return [
        Option(row["gate_id"], f"{row['label_en']} — {row['definition_en']}")
        for row in rows
    ]


def run(conn, *, ontology_version: str = "1.0.0", limit: int | None = None,
        resume: bool = True, note: str = "", progress=None) -> dict:
    rows = activities(conn, ontology_version)
    options = gates(conn)
    if not rows or not options:
        raise ValueError("No activities or no active gates; nothing to map")
    # A new gate is the reason to re-sweep, and adding one changes METHOD_VERSION;
    # short of that, an activity already asked about these gates is settled.
    already = checkpoint.done(conn, METHOD_VERSION) if resume else set()
    skipped = sum(1 for row in rows if row["activity_id"] in already)
    rows = [row for row in rows if row["activity_id"] not in already]
    if limit:
        rows = rows[:limit]
    if not rows:
        return {"run_id": None, "activities": 0, "activities_skipped": skipped,
                "gates": len(options), "questions_asked": 0, "edges": 0,
                "activities_incomplete": 0, "fallback_batches": 0,
                "failed_batches": 0, "elapsed_seconds": 0.0}

    step = Classifier(QUESTION, CRITERIA, "activity", "condition")
    run_id = f"map-activity-gate-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{token_hex(3)}"
    started = datetime.now(timezone.utc)
    conn.execute(
        """INSERT INTO public.judgment_runs
           (run_id, judge, model, task, prompt_sha256, rubric_sha256, method_version,
            params, started_at, status, item_count, decided_count, run_sha256)
           VALUES (%s, 'typesafe', %s, 'blocked_by', %s, %s, %s, %s, %s, 'running', %s, 0, %s)""",
        (run_id, step.primary.model,
         digest({"question": QUESTION, "criteria": CRITERIA}),
         digest({"select_above": SELECT_ABOVE}), METHOD_VERSION,
         Jsonb({"note": note, "select_above": SELECT_ABOVE,
                "activities": len(rows), "gates": len(options),
                "activities_skipped": skipped, "resume": resume}),
         started, len(rows) * len(options),
         digest({"activities": [r["activity_id"] for r in rows],
                 "method_version": METHOD_VERSION})),
    )

    asked = blocked = incomplete = 0
    for position, row in enumerate(rows, 1):
        failures_before = step.failed_batches
        here = 0
        state = {"activity": row["activity"], "market": row["market"]}
        readings = step.classify(state, options, progress)
        asked += len(options)
        for reading in readings:
            if reading.value <= SELECT_ABOVE:
                continue
            edge = {
                "ontology_version": ontology_version,
                "activity_id": row["activity_id"],
                "gate_id": reading.option_id,
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
                f"""INSERT INTO public.activity_gate_edges ({', '.join(columns)})
                    VALUES ({', '.join(['%s'] * len(columns))})
                    ON CONFLICT (ontology_version, activity_id, gate_id) DO NOTHING""",
                [edge[c] for c in columns],
            )
            blocked += 1
            here += 1

        if checkpoint.completed(step.failed_batches, failures_before):
            checkpoint.mark(conn, METHOD_VERSION, row["activity_id"], run_id,
                            here, len(options))
        else:
            incomplete += 1

        if progress and position % 50 == 0:
            progress(f"  {position}/{len(rows)} activities, {blocked} gate edges")

    failed = step.failed_batches
    conn.execute(
        """UPDATE public.judgment_runs
              SET status = %s, finished_at = %s, decided_count = %s, params = params || %s
            WHERE run_id = %s""",
        ("completed" if failed == 0 and incomplete == 0 else "completed_with_failures",
         datetime.now(timezone.utc), asked,
         Jsonb({"fallback_batches": step.fallback_batches, "failed_batches": failed,
                "activities_incomplete": incomplete}), run_id),
    )
    return {
        "run_id": run_id, "activities": len(rows), "activities_skipped": skipped,
        "activities_incomplete": incomplete, "gates": len(options),
        "questions_asked": asked, "edges": blocked,
        "fallback_batches": step.fallback_batches, "failed_batches": failed,
        "elapsed_seconds": round(time.time() - started.timestamp(), 1),
    }
