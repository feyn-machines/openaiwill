"""Real PostgreSQL regressions for resume (migrations 018-019).

Read against the live database because the claim under test is about what a
query returns, not what it says. The old resume asked "does this subject have
rows in the edge table?" -- which answers the right question only if every
subject keeps something. It does not: 325 of 581 routed events bore on no
activity and 329 of 614 activities are held by no gate, so a resume built that
way re-asks the majority of a sweep at full price.

The rows here are stubs under a throwaway method_version; the real checkpoints
are left untouched, since they are the record of work already paid for.
"""
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psycopg import errors

from data_pipeline import checkpoint, event_routing
from data_pipeline.db import connect, migrate

METHOD = "checkpoint-test-method"
RUN_ID = "checkpoint-test-run"


class ResumeAgainstPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = connect()
        migrate(cls.conn)
        cls.conn.execute(
            """INSERT INTO public.judgment_runs
               (run_id, judge, model, task, prompt_sha256, rubric_sha256,
                method_version, params, started_at, status, item_count,
                decided_count, run_sha256)
               VALUES (%s, 'typesafe', 'test', 'demonstrates', %s, %s, %s,
                       '{}'::jsonb, now(), 'completed', 0, 0, %s)
               ON CONFLICT (run_id) DO NOTHING""",
            (RUN_ID, "0" * 64, "0" * 64, METHOD, "0" * 64))

    @classmethod
    def tearDownClass(cls):
        # The run cascades its checkpoints away; the real methods keep theirs.
        cls.conn.execute("DELETE FROM public.judgment_runs WHERE run_id = %s", (RUN_ID,))
        cls.conn.close()

    def mark(self, subject, kept):
        checkpoint.mark(self.conn, METHOD, subject, RUN_ID, kept, None)

    def test_a_subject_that_kept_nothing_is_still_remembered(self):
        silent = f"silent-{uuid.uuid4().hex[:8]}"
        self.mark(silent, 0)
        self.assertIn(silent, checkpoint.done(self.conn, METHOD))

    def test_checkpoints_do_not_leak_across_methods(self):
        subject = f"scoped-{uuid.uuid4().hex[:8]}"
        self.mark(subject, 3)
        self.assertNotIn(subject, checkpoint.done(self.conn, "some-other-method"))

    def test_deciding_again_overwrites_rather_than_duplicating(self):
        subject = f"twice-{uuid.uuid4().hex[:8]}"
        self.mark(subject, 1)
        self.mark(subject, 7)
        rows = self.conn.execute(
            """SELECT kept FROM public.judgment_checkpoints
                WHERE method_version = %s AND subject_id = %s""",
            (METHOD, subject)).fetchall()
        self.assertEqual([row["kept"] for row in rows], [7])

    def test_kept_cannot_go_negative(self):
        with self.assertRaises(errors.CheckViolation):
            with self.conn.transaction():
                self.mark(f"bad-{uuid.uuid4().hex[:8]}", -1)

    def test_excluded_events_are_dropped_from_the_routing_input(self):
        rows = event_routing.events(self.conn, limit=3)
        if not rows:
            self.skipTest("no events under the controlled vocabulary")
        dropped = rows[0]["event_id"]
        remaining = event_routing.events(self.conn, exclude={dropped})
        self.assertNotIn(dropped, [row["event_id"] for row in remaining])
        self.assertIn(dropped, [row["event_id"] for row in event_routing.events(self.conn)])

    def test_real_routing_checkpoints_cover_the_events_that_kept_nothing(self):
        """The bug, measured on the live data rather than asserted in the abstract."""
        counts = self.conn.execute(
            """SELECT count(*) AS decided,
                      count(*) FILTER (WHERE kept = 0) AS kept_nothing
                 FROM public.judgment_checkpoints
                WHERE method_version = 'event-activity-1'""").fetchone()
        if not counts["decided"]:
            self.skipTest("event routing has not run yet")
        self.assertGreater(counts["kept_nothing"], 0,
                           "silence is the majority case; a resume that cannot "
                           "record it re-asks most of the sweep")


if __name__ == "__main__":
    unittest.main()
