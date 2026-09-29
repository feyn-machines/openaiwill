"""Real PostgreSQL regressions for the evidence panel (migration 025).

Each test runs inside a transaction that is rolled back, so the live panel is
never touched. The draft here is two accounts: one insider, one evaluator.
"""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psycopg import errors

from data_pipeline import panel
from data_pipeline.db import connect, migrate

DRAFT = {
    "as_of": "2026-09-23",
    "accounts": [
        {"handle": "panel_test_insider", "name": "Test Insider", "account_kind": "person",
         "primary_role": "lab_insider", "use": "heat",
         "affiliations": [{"org": "Google DeepMind", "relation": "employee", "source_url": "https://example.org/a"},
                          {"org": "Meta (left 2025)", "relation": "employee"}],
         "identity_evidence_kind": "first_party_link", "identity_evidence_url": "https://example.org/me",
         "language": "en", "focus": "t"},
        {"handle": "panel_test_eval", "name": "Test Evals", "account_kind": "organization",
         "primary_role": "evaluator", "use": "verification", "affiliations": [],
         "identity_evidence_kind": "official_bio", "identity_evidence_url": None, "language": "en", "focus": "t"},
    ],
}


class PanelImport(unittest.TestCase):
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

    def test_import_is_idempotent(self):
        def body():
            first = panel.import_draft(self.conn, DRAFT, "test")
            before = self.conn.execute(
                "SELECT (SELECT count(*) FROM source_accounts) a, (SELECT count(*) FROM person_affiliations) f,"
                " (SELECT count(*) FROM source_account_checks) c").fetchone()
            panel.import_draft(self.conn, DRAFT, "test")
            after = self.conn.execute(
                "SELECT (SELECT count(*) FROM source_accounts) a, (SELECT count(*) FROM person_affiliations) f,"
                " (SELECT count(*) FROM source_account_checks) c").fetchone()
            self.assertEqual(before, after)
            self.assertEqual(first["accounts"], 2)
        self.run_rolled_back(body)

    def test_affiliations_resolve_and_departures_become_former(self):
        def body():
            panel.import_draft(self.conn, DRAFT, "test")
            rows = self.conn.execute(
                """SELECT org_name, org_id, relation FROM person_affiliations
                    WHERE person_id = %s ORDER BY org_name""",
                (panel.person_id_for({"name": "Test Insider"}),)).fetchall()
            self.assertEqual([(r["org_id"], r["relation"]) for r in rows],
                             [("org:google", "employee"), ("org:meta", "former")])
        self.run_rolled_back(body)

    def test_nothing_is_enabled_without_a_platform_id(self):
        def body():
            panel.import_draft(self.conn, DRAFT, "test")
            panel.refresh(self.conn, datetime(2026, 9, 23, tzinfo=timezone.utc))
            states = {r["handle"]: r["panel_state"] for r in self.conn.execute(
                "SELECT handle, panel_state FROM source_accounts WHERE handle LIKE 'panel_test_%'")}
            self.assertEqual(set(states.values()), {"candidate"})
        self.run_rolled_back(body)

    def test_the_schema_refuses_enabled_without_an_id(self):
        def body():
            panel.import_draft(self.conn, DRAFT, "test")
            with self.assertRaises(errors.CheckViolation):
                with self.conn.transaction():
                    self.conn.execute("UPDATE source_accounts SET panel_state = 'enabled' "
                                      "WHERE handle = 'panel_test_eval'")
        self.run_rolled_back(body)

    def test_an_unknown_role_is_refused_by_the_schema(self):
        def body():
            panel.import_draft(self.conn, DRAFT, "test")
            with self.assertRaises(errors.CheckViolation):
                with self.conn.transaction():
                    self.conn.execute("UPDATE source_accounts SET panel_role = 'influencer' "
                                      "WHERE handle = 'panel_test_eval'")
        self.run_rolled_back(body)



REGISTRY = Path(__file__).resolve().parents[2] / "datasets/official-x-accounts.json"


class OfficialImport(unittest.TestCase):
    """The official registry, imported for real and rolled back."""

    setUpClass = classmethod(PanelImport.setUpClass.__func__)
    run_rolled_back = PanelImport.run_rolled_back

    def test_the_database_targets_match_the_registry_file(self):
        """The crawler used to read the file; reading the table must plan the same jobs."""
        import json
        registry = json.loads(REGISTRY.read_text())
        expected = {(a["handle"], a["x_user_id"], a["company"]) for a in registry
                    if a.get("enabled") and a.get("verification_status") == "confirmed"}

        def body():
            panel.import_official(self.conn, registry, "test")
            panel.refresh(self.conn)
            got = {(r["handle"], r["x_user_id"], r["company"]) for r in panel.crawl_targets(self.conn, "official")}
            self.assertEqual(got, expected)
            panel_handles = {r["handle"] for r in panel.crawl_targets(self.conn, "panel")}
            self.assertFalse(panel_handles & {h for h, _, _ in expected})
        self.run_rolled_back(body)

    def test_reimport_is_idempotent(self):
        import json
        registry = json.loads(REGISTRY.read_text())

        def body():
            panel.import_official(self.conn, registry, "test")
            count = lambda: self.conn.execute(
                "SELECT (SELECT count(*) FROM source_accounts) a, (SELECT count(*) FROM source_account_checks) c"
            ).fetchone()
            before = count()
            panel.import_official(self.conn, registry, "test")
            self.assertEqual(before, count())
        self.run_rolled_back(body)

    def test_a_panel_account_is_not_relabelled_official(self):
        def body():
            panel.import_draft(self.conn, DRAFT, "test")
            clash = {"handle": "panel_test_eval", "company": "OpenAI", "enabled": True,
                     "verification_status": "confirmed", "x_user_id": "1"}
            with self.assertRaises(ValueError):
                panel.import_official(self.conn, [clash], "test")
        self.run_rolled_back(body)


if __name__ == "__main__":
    unittest.main()
