"""Real PostgreSQL tests for schema app, in a scratch database with a throwaway role.

The owner's working database and the real oaw_app role are never touched."""
import secrets
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg
from psycopg import errors, sql
from psycopg.rows import dict_row

import app_db
from data_pipeline import kg
from data_pipeline.db import connect


class AppBase(unittest.TestCase):
    def setUp(self):
        token = uuid.uuid4().hex[:12]
        self.database = "openaiwill_app_test_" + token
        self.role = "oaw_app_test_" + token
        self.password = secrets.token_hex(16)
        self.extra_roles = []
        self.admin = connect()
        self.addCleanup(self.admin.close)
        self.admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.database)))
        self.addCleanup(self.drop)
        self.admin_db = connect(self.database)
        self.addCleanup(self.admin_db.close)
        app_db.ensure_role_and_schema(self.admin_db, self.password, role=self.role)
        self.conn = psycopg.connect(
            host="127.0.0.1", port=7543, dbname=self.database, user=self.role, password=self.password,
            autocommit=True, row_factory=dict_row, options="-c timezone=UTC")
        self.addCleanup(self.conn.close)
        app_db.apply_schema(self.conn)

    def drop(self):
        self.conn.close()
        self.admin_db.close()
        self.admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(self.database)))
        for role in (self.role, *self.extra_roles):
            self.admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))

    def user(self, name="u1", email=None):
        self.conn.execute(
            'INSERT INTO app."user" (id, name, email, "emailVerified") VALUES (%s, %s, %s, true)',
            (name, name, email or f"{name}@example.com"))
        return name

    def submit(self, user, handle="openai", display=None, **extra):
        cols = {"user_id": user, "handle": handle, "display_handle": display or handle, "owner_kind": "organization", **extra}
        names = sql.SQL(", ").join(map(sql.Identifier, cols))
        marks = sql.SQL(", ").join(sql.Placeholder() * len(cols))
        return self.conn.execute(
            sql.SQL("INSERT INTO app.submissions ({}) VALUES ({}) RETURNING id").format(names, marks), list(cols.values())
        ).fetchone()["id"]

    def tables(self):
        return sorted(r["tablename"] for r in self.conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'app'"))


class Schema(AppBase):
    def test_apply_schema_twice_changes_nothing(self):
        before = self.tables()
        app_db.apply_schema(self.conn)
        self.assertEqual(self.tables(), before)
        self.assertEqual(before, ["account", "admins", "session", "submissions", "subscriptions", "user", "verification"])

    def test_tables_are_owned_by_the_app_role(self):
        owners = {r["tableowner"] for r in self.conn.execute("SELECT tableowner FROM pg_tables WHERE schemaname = 'app'")}
        self.assertEqual(owners, {self.role})


class Submissions(AppBase):
    def test_same_user_same_handle_twice_is_refused(self):
        user = self.user()
        self.submit(user)
        with self.assertRaises(errors.UniqueViolation):
            self.submit(user)

    def test_checks(self):
        user = self.user()
        cases = [
            dict(handle="OpenAI", display="OpenAI"),
            dict(handle="openai", display="Other"),
            dict(handle="openai", note="x" * 281),
            dict(handle="openai", status="rejected", decided_at="2026-10-04T00:00:00Z"),
            dict(handle="openai", imported_at="2026-10-04T00:00:00Z"),
        ]
        for case in cases:
            handle, display = case.pop("handle"), case.pop("display", None)
            with self.subTest(handle=handle, display=display, **case), self.assertRaises(errors.CheckViolation):
                self.submit(user, handle, display, **case)

    def decide(self, ident, status="approved", reason=None, by=None):
        return self.conn.execute(
            "UPDATE app.submissions SET status = %s, decision_reason = %s, decided_by = %s, decided_at = now() WHERE id = %s",
            (status, reason, by, ident))

    def test_decision_is_final(self):
        user, admin = self.user(), self.user("a1")
        ident = self.submit(user)
        self.decide(ident, by=admin)
        with self.assertRaises(errors.RaiseException):
            self.decide(ident, "rejected", "no", admin)

    def test_imported_at_is_set_once(self):
        user, admin = self.user(), self.user("a1")
        ident = self.submit(user)
        self.decide(ident, by=admin)
        self.conn.execute("UPDATE app.submissions SET imported_at = '2026-10-05T00:00:00Z' WHERE id = %s", (ident,))
        with self.assertRaises(errors.RaiseException):
            self.conn.execute("UPDATE app.submissions SET imported_at = '2026-10-06T00:00:00Z' WHERE id = %s", (ident,))

    def test_decided_row_cannot_change_display_handle_or_clear_imported_at(self):
        user, admin = self.user(), self.user("a1")
        ident = self.submit(user, "openai", "openai")
        self.decide(ident, by=admin)
        with self.assertRaises(errors.RaiseException):
            self.conn.execute("UPDATE app.submissions SET display_handle = 'OpenAI' WHERE id = %s", (ident,))
        self.conn.execute("UPDATE app.submissions SET imported_at = now() WHERE id = %s", (ident,))
        with self.assertRaises(errors.RaiseException):
            self.conn.execute("UPDATE app.submissions SET imported_at = NULL WHERE id = %s", (ident,))

    def test_decided_row_cannot_change_created_at_or_platform(self):
        user, admin = self.user(), self.user("a1")
        ident = self.submit(user)
        self.decide(ident, by=admin)
        with self.assertRaises(errors.RaiseException):
            self.conn.execute("UPDATE app.submissions SET created_at = created_at - interval '1 day' WHERE id = %s", (ident,))

    def test_reason_length_and_pending_without_decision_time(self):
        user = self.user()
        with self.assertRaises(errors.CheckViolation):
            self.submit(user, "a1", status="rejected", decision_reason="x" * 281, decided_at="2026-10-04T00:00:00Z")
        with self.assertRaises(errors.CheckViolation):
            self.submit(user, "a2", decided_at="2026-10-04T00:00:00Z")

    def test_deleting_the_deciding_user_keeps_the_submission(self):
        user, admin = self.user(), self.user("a1")
        ident = self.submit(user)
        self.decide(ident, by=admin)
        self.conn.execute('DELETE FROM app."user" WHERE id = %s', (admin,))
        row = self.conn.execute("SELECT status, decided_by FROM app.submissions WHERE id = %s", (ident,)).fetchone()
        self.assertEqual(row, {"status": "approved", "decided_by": None})

    def test_deleting_the_submitting_user_removes_their_rows(self):
        user = self.user()
        self.submit(user)
        self.conn.execute("INSERT INTO app.subscriptions (user_id, topic, language) VALUES (%s, 'updates', 'en')", (user,))
        self.conn.execute('DELETE FROM app."user" WHERE id = %s', (user,))
        self.assertEqual(self.conn.execute("SELECT count(*) AS n FROM app.submissions").fetchone()["n"], 0)
        self.assertEqual(self.conn.execute("SELECT count(*) AS n FROM app.subscriptions").fetchone()["n"], 0)


class Subscriptions(AppBase):
    def test_one_row_per_user_and_topic_and_known_topics(self):
        user = self.user()
        insert = "INSERT INTO app.subscriptions (user_id, topic, language) VALUES (%s, %s, 'en')"
        self.conn.execute(insert, (user, "updates"))
        with self.assertRaises(errors.UniqueViolation):
            self.conn.execute(insert, (user, "updates"))
        with self.assertRaises(errors.CheckViolation):
            self.conn.execute(insert, (user, "daily"))


class Isolation(AppBase):
    def test_app_role_cannot_read_kg(self):
        kg.ensure_schema(self.admin_db)
        with self.assertRaises(errors.InsufficientPrivilege):
            self.conn.execute("SELECT 1 FROM kg.releases")

    def test_a_role_without_grants_cannot_read_app(self):
        other = "oaw_other_test_" + uuid.uuid4().hex[:12]
        password = secrets.token_hex(16)
        self.admin.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(other), sql.Literal(password)))
        self.extra_roles.append(other)
        self.admin_db.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(self.database), sql.Identifier(other)))
        with psycopg.connect(host="127.0.0.1", port=7543, dbname=self.database, user=other, password=password, autocommit=True) as c:
            with self.assertRaises(errors.InsufficientPrivilege):
                c.execute("SELECT 1 FROM app.submissions")


class Administrators(AppBase):
    def rows(self):
        return [r["email"] for r in self.conn.execute("SELECT email FROM app.admins ORDER BY email")]

    def test_sync_adds_removes_and_is_a_no_op_when_equal(self):
        self.assertEqual(app_db.sync_admins(self.conn, ["a@example.com", "b@example.com"]), (2, 0))
        self.assertEqual(app_db.sync_admins(self.conn, ["a@example.com", "b@example.com"]), (0, 0))
        self.assertEqual(app_db.sync_admins(self.conn, ["b@example.com", "c@example.com"]), (1, 1))
        self.assertEqual(self.rows(), ["b@example.com", "c@example.com"])

    def test_sync_stores_lower_case(self):
        app_db.sync_admins(self.conn, ["Mixed@Example.COM"])
        self.assertEqual(self.rows(), ["mixed@example.com"])

    def test_sync_refuses_an_empty_list_and_keeps_the_table(self):
        app_db.sync_admins(self.conn, ["a@example.com"])
        with self.assertRaises(app_db.AppError):
            app_db.sync_admins(self.conn, [])
        self.assertEqual(self.rows(), ["a@example.com"])

    def test_table_refuses_unnormalized_addresses(self):
        for value in ("Upper@example.com", " a@example.com", "no-at"):
            with self.subTest(value), self.assertRaises(errors.CheckViolation):
                self.conn.execute("INSERT INTO app.admins (email) VALUES (%s)", (value,))


class Pull(AppBase):
    def setUp(self):
        super().setUp()
        import tempfile
        self.out = tempfile.TemporaryDirectory()
        self.addCleanup(self.out.cleanup)
        self.dir = Path(self.out.name) / "submissions"
        self.admin_user = self.user("admin1")

    def decide(self, ident, status="approved", reason=None):
        self.conn.execute(
            "UPDATE app.submissions SET status = %s, decision_reason = %s, decided_by = %s, decided_at = now() WHERE id = %s",
            (status, reason, self.admin_user, ident))

    def approved(self, user, handle, display=None, kind="organization", note=None):
        ident = self.submit(self.user(user), handle, display, owner_kind=kind, note=note)
        self.decide(ident)
        return ident

    def files(self):
        return sorted(self.dir.glob("approved-*.json")) if self.dir.exists() else []

    def run_pull(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            path = app_db.pull_from(self.conn, self.dir)
        return path, out.getvalue()

    def test_requests_are_grouped_by_account_and_the_earliest_display_form_is_kept(self):
        import json
        self.approved("u1", "openai", "OpenAI", note="first note")
        self.approved("u2", "openai", "openai", note=None)
        self.approved("u3", "anthropicai", "AnthropicAI", kind="organization", note="second")
        path, out = self.run_pull()
        data = json.loads(path.read_text())
        self.assertEqual(sorted(data), ["accounts", "pulled_at"])
        accounts = {a["handle"]: a for a in data["accounts"]}
        self.assertEqual(sorted(accounts), ["AnthropicAI", "OpenAI"])
        self.assertEqual((accounts["OpenAI"]["requests"], accounts["AnthropicAI"]["requests"]), (2, 1))
        self.assertEqual(accounts["OpenAI"]["notes"], ["first note"])
        self.assertEqual(accounts["OpenAI"]["account_kind"], "organization")
        for account in accounts.values():
            self.assertEqual(sorted(account), ["account_kind", "approved_at", "handle", "notes", "requests"])
        self.assertIn("2", out)
        self.assertIn("pnpm data:panel:import", out)

    def test_the_same_handle_as_person_and_organization_are_two_accounts(self):
        import json
        self.approved("u1", "openai", kind="organization")
        self.approved("u2", "openai", kind="person")
        path, _ = self.run_pull()
        kinds = sorted(a["account_kind"] for a in json.loads(path.read_text())["accounts"])
        self.assertEqual(kinds, ["organization", "person"])

    def test_a_second_run_writes_nothing(self):
        self.approved("u1", "openai")
        self.run_pull()
        path, out = self.run_pull()
        self.assertIsNone(path)
        self.assertEqual(out.strip(), "no approved submissions waiting")
        self.assertEqual(len(self.files()), 1)

    def test_pending_and_rejected_rows_are_never_included_nor_marked(self):
        import json
        self.approved("u1", "openai")
        self.submit(self.user("u2"), "pendingone")
        rejected = self.submit(self.user("u3"), "rejectedone")
        self.decide(rejected, "rejected", "no")
        path, _ = self.run_pull()
        self.assertEqual([a["handle"] for a in json.loads(path.read_text())["accounts"]], ["openai"])
        rows = self.conn.execute("SELECT handle, imported_at IS NOT NULL AS imported FROM app.submissions ORDER BY handle").fetchall()
        self.assertEqual({r["handle"]: r["imported"] for r in rows}, {"openai": True, "pendingone": False, "rejectedone": False})

    def test_a_later_approval_of_a_known_handle_is_pulled_again_as_a_new_request(self):
        import json
        self.approved("u1", "openai")
        self.run_pull()
        self.approved("u2", "openai")
        path, _ = self.run_pull()
        self.assertEqual(json.loads(path.read_text())["accounts"][0]["requests"], 1)

    def test_the_file_holds_no_requester_identity_and_is_private(self):
        import stat
        self.approved("u1", "openai", note="why")
        path, _ = self.run_pull()
        text = path.read_text()
        self.assertNotIn("@", text)
        self.assertNotIn("u1", text)
        self.assertNotIn("user_id", text)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertRegex(path.name, r"^approved-\d{8}T\d{6}Z\.json$")

    def test_a_failed_write_rolls_the_database_back(self):
        self.approved("u1", "openai")
        self.dir.parent.mkdir(exist_ok=True)
        self.dir.write_text("a file where the directory should be")
        with self.assertRaises(OSError):
            app_db.pull_from(self.conn, self.dir)
        self.assertEqual(self.conn.execute("SELECT count(*) AS n FROM app.submissions WHERE imported_at IS NOT NULL").fetchone()["n"], 0)

    def test_a_failed_update_removes_the_file_again(self):
        self.approved("u1", "openai")
        self.conn.execute("CREATE OR REPLACE FUNCTION app.refuse() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN "
                          "IF NEW.imported_at IS NOT NULL AND OLD.imported_at IS NULL THEN RAISE EXCEPTION 'no'; END IF; "
                          "RETURN NEW; END $$")
        self.conn.execute("CREATE TRIGGER refuse BEFORE UPDATE ON app.submissions FOR EACH ROW EXECUTE FUNCTION app.refuse()")
        with self.assertRaises(errors.RaiseException):
            app_db.pull_from(self.conn, self.dir)
        self.assertEqual(self.files(), [])
        self.assertEqual(self.conn.execute("SELECT count(*) AS n FROM app.submissions WHERE imported_at IS NOT NULL").fetchone()["n"], 0)


if __name__ == "__main__":
    unittest.main()
