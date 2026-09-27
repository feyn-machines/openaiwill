"""Real PostgreSQL regressions for what counts as one square on the grid.

A task and an activity are both `kind='work'`. The ontology tells them apart by
relation - a task is the child of a has_task edge, an activity the child of a
has_work edge - and nothing else does. Counting by kind alone put all 614
activities into the world of tasks, where no activity can ever cover them, so
the chart carried 614 squares that were permanently "untouched" and stood for no
work at all. 19,452 where 18,838 was the answer.

These read the live database because the claim is about what a query returns.
Nothing here writes.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline import activity_state, publish
from data_pipeline.db import connect, migrate

VERSION = "1.0.0"


class WorkIsTasksOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = connect()
        migrate(cls.conn)

    def scalar(self, sql, params=None):
        return self.conn.execute(sql, params).fetchone()["n"]

    def test_tasks_and_activities_partition_the_work_concepts(self):
        """The predicate is only exact because the two sets are disjoint and complete."""
        work = self.scalar(
            "SELECT count(*) AS n FROM public.ontology_concepts "
            "WHERE kind = 'work' AND ontology_version = %s", (VERSION,))
        tasks = self.scalar(
            "SELECT count(DISTINCT child_id) AS n FROM public.ontology_relations "
            "WHERE kind = 'has_task' AND ontology_version = %s", (VERSION,))
        activities = self.scalar(
            "SELECT count(DISTINCT child_id) AS n FROM public.ontology_relations "
            "WHERE kind = 'has_work' AND ontology_version = %s", (VERSION,))
        overlap = self.scalar(
            """SELECT count(*) AS n FROM (
                 SELECT child_id FROM public.ontology_relations
                  WHERE kind = 'has_task' AND ontology_version = %s
                 INTERSECT
                 SELECT child_id FROM public.ontology_relations
                  WHERE kind = 'has_work' AND ontology_version = %s) shared""",
            (VERSION, VERSION))
        self.assertEqual(overlap, 0, "a concept that is both would be counted twice")
        self.assertEqual(tasks + activities, work, "every work concept is one or the other")

    def test_the_grid_counts_tasks_and_not_activities(self):
        tasks = self.scalar(
            "SELECT count(DISTINCT child_id) AS n FROM public.ontology_relations "
            "WHERE kind = 'has_task' AND ontology_version = %s", (VERSION,))
        self.assertEqual(activity_state.summary(self.conn, VERSION)["work_items_total"], tasks)

    def test_no_activity_reaches_the_grid_as_untouched(self):
        """The failure mode was silent: activities showed up as ordinary blanks."""
        leaked = self.scalar(
            f"""SELECT count(*) AS n FROM public.ontology_concepts w
                 WHERE w.kind = 'work' AND w.ontology_version = %s
                   AND {activity_state.IS_TASK}
                   AND EXISTS (SELECT 1 FROM public.ontology_relations r
                                WHERE r.ontology_version = w.ontology_version
                                  AND r.child_id = w.id AND r.kind = 'has_work')""",
            (VERSION,))
        self.assertEqual(leaked, 0)

    def test_the_publisher_and_the_state_pass_agree(self):
        """Two copies of the same computation; they have to land on one number."""
        state = activity_state.summary(self.conn, VERSION)
        progress = publish.build(self.conn, VERSION)["progress"]
        self.assertEqual(progress["work_items_total"], state["work_items_total"])
        for key in ("assessed", "unknown", "untouched"):
            with self.subTest(state=key):
                self.assertEqual(progress[key], state[key])

    def test_the_three_states_account_for_every_task(self):
        state = activity_state.summary(self.conn, VERSION)
        self.assertEqual(state["assessed"] + state["unknown"] + state["untouched"],
                         state["work_items_total"])


if __name__ == "__main__":
    unittest.main()
