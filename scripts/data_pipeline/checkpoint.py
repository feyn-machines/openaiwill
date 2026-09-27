"""Remember which subjects a method already decided, so a rerun asks only what is new.

Every pass sweeps a fixed list of subjects and asks a few hundred questions about
each one. Without this, the only trace a pass left was the edges it kept — and a
subject that keeps nothing leaves no trace at all. 325 of 581 routed events bore
on no activity, so a resume that looks for rows would re-ask more than half the
work it had already paid for.

Two rules make it safe to trust:

  1. A checkpoint is written **after** the subject is fully decided, never before.
  2. A subject whose batch failed is not checkpointed, so it comes back around.

The second is why `completed` exists: the classifier counts failures for the whole
run, so a pass has to compare before and after to know whether *this* subject got
a complete answer rather than a partial one.
"""
from __future__ import annotations


def done(conn, method_version: str) -> set[str]:
    """Subject ids already decided under this method."""
    return {
        row["subject_id"]
        for row in conn.execute(
            "SELECT subject_id FROM public.judgment_checkpoints WHERE method_version = %s",
            (method_version,),
        )
    }


def mark(conn, method_version: str, subject_id: str, run_id: str,
         kept: int, questions_asked: int) -> None:
    """Record that this subject is decided. Re-deciding overwrites the record."""
    conn.execute(
        """INSERT INTO public.judgment_checkpoints
           (method_version, subject_id, run_id, kept, questions_asked)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (method_version, subject_id) DO UPDATE
             SET run_id = EXCLUDED.run_id, kept = EXCLUDED.kept,
                 questions_asked = EXCLUDED.questions_asked, decided_at = now()""",
        (method_version, subject_id, run_id, kept, questions_asked),
    )


def completed(failures_now: int, failures_before: int) -> bool:
    """True when no batch failed while this subject was being decided.

    Counts rather than a classifier, because a pass may run two of them and a
    subject is complete only when neither lost a batch.

    A subject that lost a batch is left uncheckpointed on purpose: the cost of
    asking it again is one sweep, and the cost of marking it done on half an
    answer is a permanent hole nothing will ever revisit.
    """
    return failures_now == failures_before


# The method version each pass checkpoints under. They live here rather than in
# each pass because the publisher needs to read one of them, and importing a
# pass to reach a string drags psycopg into the dependency-free unit tests -
# which is exactly how `pnpm check` broke the last time a constant was fetched
# from the module that happened to own it.
EVENT_ROUTING = "event-activity-1"
ACTIVITY_TASK = "activity-task-1"
ACTIVITY_GATE = "activity-gate-1"
MARKET_OCCUPATION = "market-occupation-2"
