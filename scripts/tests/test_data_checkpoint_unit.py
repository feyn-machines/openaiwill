"""Offline unit tests for resume: what a pass remembers when it kept nothing.

Dependency-free (no psycopg, no network) so it runs with the system python under
`pnpm data:test:unit`, driven by a fake connection that records every statement.
Only `checkpoint` is imported here: every pass that uses it pulls in psycopg, and
importing one would make this file silently need the virtualenv. The resume
queries themselves are tested against the real database instead, where they can
be run rather than only read.

The regression these guard is specific and was live. Resume used to ask "does
this subject have rows?", which is the same question as "was it decided" only
when every subject keeps something. It does not: 325 of 581 routed events bore
on no activity, 329 of 614 activities are held by no gate. A resume built on the
edge tables re-asks every one of them, at full price, forever. Silence has to be
recorded somewhere, and the assertions below are that it is.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_pipeline import checkpoint  # noqa: E402


def squeeze(sql):
    return " ".join(sql.split())


class FakeResult(list):
    def fetchall(self):
        return list(self)

    def fetchone(self):
        return self[0] if self else None


class FakeConn:
    """Exactly the surface these functions use: conn.execute() -> iterable rows."""

    def __init__(self, rows=()):
        self.rows = list(rows)
        self.statements = []

    def execute(self, sql, params=()):
        self.statements.append((squeeze(sql), params))
        return FakeResult(self.rows)

    def last(self):
        return self.statements[-1]


class CheckpointStore(unittest.TestCase):
    def test_done_reads_one_method_and_returns_ids(self):
        conn = FakeConn([{"subject_id": "a"}, {"subject_id": "b"}])
        self.assertEqual(checkpoint.done(conn, "m-1"), {"a", "b"})
        sql, params = conn.last()
        self.assertIn("FROM public.judgment_checkpoints", sql)
        self.assertIn("WHERE method_version = %s", sql)
        self.assertEqual(params, ("m-1",))

    def test_mark_records_a_subject_that_kept_nothing(self):
        # The whole reason the table exists: 0 must be storable and must not be
        # mistaken later for "never asked".
        conn = FakeConn()
        checkpoint.mark(conn, "m-1", "event-7", "run-1", kept=0, questions_asked=614)
        sql, params = conn.last()
        self.assertIn("INSERT INTO public.judgment_checkpoints", sql)
        self.assertIn("ON CONFLICT (method_version, subject_id) DO UPDATE", sql)
        self.assertEqual(params, ("m-1", "event-7", "run-1", 0, 614))

    def test_completed_is_false_when_a_batch_failed_meanwhile(self):
        self.assertTrue(checkpoint.completed(3, 3))
        self.assertFalse(checkpoint.completed(4, 3))


if __name__ == "__main__":
    unittest.main()
