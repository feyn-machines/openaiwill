"""Real PostgreSQL regressions for the model field of an update (migration 032).

Each test runs inside a transaction that is rolled back, so the live registry is
never touched.
"""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psycopg import errors

from data_pipeline import model_identification as mi
from data_pipeline.db import connect, migrate

RELEASED = datetime(2026, 9, 3, 18, tzinfo=timezone.utc)
SHA = "0" * 64


class ModelRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = connect()
        migrate(cls.conn)

    def run_rolled_back(self, body):
        class Rollback(Exception):
            pass
        try:
            with self.conn.transaction():
                body()
                raise Rollback
        except Rollback:
            pass

    def seed(self):
        run = self.conn.execute("SELECT run_id FROM extraction_runs LIMIT 1").fetchone()["run_id"]
        self.conn.execute(
            """INSERT INTO judgment_runs (run_id, judge, model, task, prompt_sha256, rubric_sha256,
                 method_version, params, started_at, status, run_sha256)
               VALUES ('t-models', 'deepseek', 't', 'model_identification', %s, %s, %s, '{}', now(), 'running', %s)""",
            (SHA, SHA, mi.METHOD_VERSION, SHA))
        for event_id, kind, org in (("t-ev-release", "version_release", "org:google"),
                                    ("t-ev-other", "version_release", "org:microsoft"),
                                    ("t-ev-adopt", "production_adoption", "org:google")):
            self.conn.execute(
                """INSERT INTO extracted_events (event_id, dedup_key, kind, title, summary, occurred_at,
                     occurrence_status, first_extraction_run_id, record_sha256, kind_vocabulary, primary_org_id)
                   VALUES (%s, %s, %s, 't', 't', %s, 'occurred', %s, %s, 'event_kind-2.0.0', %s)""",
                (event_id, event_id, kind, RELEASED, run, SHA, org))
        reg = mi.Registry()
        links = (mi.links_for(reg, "t-ev-release", [self.mention("Tgem 9 Flash", "subject")])
                 + mi.links_for(reg, "t-ev-other", [self.mention("Tgem 9 Pro", "subject")])
                 + mi.links_for(reg, "t-ev-adopt", [self.mention("Tgem 9 Ultra", "subject")]))
        for row in reg.new_models:
            self.conn.execute(
                """INSERT INTO models (model_id, org_id, owner_name, level, parent_model_id, name, version,
                     variant, status, first_seen_event_id)
                   VALUES (%(model_id)s, %(org_id)s, %(owner_name)s, %(level)s, %(parent_model_id)s, %(name)s,
                           %(version)s, %(variant)s, %(status)s, %(first_seen_event_id)s)""", row)
        for link in links:
            self.conn.execute(
                "INSERT INTO event_models (event_id, model_id, role, mention, confidence, run_id) "
                "VALUES (%(event_id)s, %(model_id)s, %(role)s, %(mention)s, %(confidence)s, 't-models')", link)

    @staticmethod
    def mention(name, role):
        return {"mention": name, "name": name, "family": "Tgem", "version": "9",
                "variant": name.split()[-1], "owner": "Google", "role": role, "confidence": 0.9}

    def status(self, slug):
        return self.conn.execute("SELECT status, released_at FROM models WHERE model_id = %s",
                                 (f"model:google:{slug}",)).fetchone()

    def test_the_owners_release_update_confirms_and_dates_a_model(self):
        def body():
            self.seed()
            mi.confirm(self.conn)
            self.assertEqual(self.status("tgem-9-flash"), {"status": "confirmed", "released_at": RELEASED})
            self.assertEqual(self.status("tgem")["status"], "confirmed")
        self.run_rolled_back(body)

    def test_another_companys_update_or_another_kind_confirms_nothing(self):
        def body():
            self.seed()
            mi.confirm(self.conn)
            self.assertEqual(self.status("tgem-9-pro"), {"status": "candidate", "released_at": None})
            self.assertEqual(self.status("tgem-9-ultra"), {"status": "candidate", "released_at": None})
        self.run_rolled_back(body)

    def test_a_family_carries_no_version(self):
        def body():
            self.seed()
            with self.assertRaises(errors.CheckViolation), self.conn.transaction():
                self.conn.execute("UPDATE models SET version = '9' WHERE model_id = 'model:google:tgem'")
        self.run_rolled_back(body)

    def test_an_unknown_role_is_refused(self):
        def body():
            self.seed()
            with self.assertRaises(errors.CheckViolation), self.conn.transaction():
                self.conn.execute(
                    "INSERT INTO event_models (event_id, model_id, role, mention, run_id) "
                    "VALUES ('t-ev-adopt', 'model:google:tgem', 'mentioned', 'Tgem', 't-models')")
        self.run_rolled_back(body)


if __name__ == "__main__":
    unittest.main()
