"""Offline tests for the server side of the data release line: the setup script, env-file parsing,
the forward and the production poll. Nothing here contacts a server.

Dependency-free (no psycopg): runs under `pnpm data:test:unit` with the system python.
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server_db  # noqa: E402
import site_release  # noqa: E402

TARGET = {"DEPLOY_HOST": "h.example", "DEPLOY_USER": "u", "DEPLOY_SSH_KEY": "/k/key", "DEPLOY_ROOT": "/opt/openaiwill"}
GOOD = "a" * 48


def build(target=TARGET, compose="services: {}\n", roles="SELECT 1;\n", schema="SELECT 2;\n", grants="SELECT 3;\n"):
    return server_db.setup_script(target, compose, roles, schema, grants)


class EnvFileTest(unittest.TestCase):
    def test_parse_skips_comments_and_blank_lines(self):
        self.assertEqual(server_db.parse_env("# c\n\nA=1\n B = x=y \nnoequals\n"), {"A": "1", "B": "x=y"})

    def test_the_writer_password_is_read(self):
        text = f"POSTGRES_PASSWORD={'b' * 48}\nOAW_KG_WRITER_PASSWORD={GOOD}\nOAW_SITE_PASSWORD={'c' * 48}\n"
        self.assertEqual(server_db.writer_password(text), GOOD)

    def test_a_missing_or_malformed_password_is_refused_without_echoing_anything(self):
        for text in ("", "OAW_KG_WRITER_PASSWORD=\n", "OAW_KG_WRITER_PASSWORD=short\n",
                     "OAW_KG_WRITER_PASSWORD=" + "a b" * 20 + "\n", "OAW_KG_WRITER_PASSWORD=" + "x;" * 30 + "\n"):
            with self.assertRaises(site_release.ReleaseError) as raised:
                server_db.writer_password(text)
            self.assertNotIn("short", str(raised.exception))
            self.assertNotIn("x;", str(raised.exception))


class ForwardTest(unittest.TestCase):
    def test_the_forward_targets_the_database_loopback_port(self):
        argv = server_db.db_forward_argv(TARGET, 50111)
        self.assertEqual(argv[argv.index("-L") + 1], "50111:127.0.0.1:5434")
        self.assertIn("ExitOnForwardFailure=yes", argv)
        self.assertEqual(argv[-1], "u@h.example")

    def test_the_probe_checks_only_the_given_loopback_port(self):
        script = server_db.port_probe_script(8320)
        self.assertIn("/dev/tcp/127.0.0.1/8320", script)
        self.assertEqual(subprocess.run(["bash", "-c", server_db.port_probe_script(1)],
                                        capture_output=True, text=True).stdout.strip(), "none")


class HeredocTest(unittest.TestCase):
    def test_the_text_is_written_byte_for_byte(self):
        script = server_db.heredoc("/x/f", "a $b `c` 'd'\n", "TAG_EOF")
        done = subprocess.run(["bash", "-c", script.replace("/x/f", "/dev/stdout")], capture_output=True, text=True)
        self.assertEqual(done.stdout, "a $b `c` 'd'\n")

    def test_a_text_containing_the_tag_is_refused(self):
        with self.assertRaises(site_release.ReleaseError):
            server_db.heredoc("/x/f", "a\nTAG_EOF\nb\n", "TAG_EOF")


class SetupScriptTest(unittest.TestCase):
    def test_it_is_valid_shell(self):
        done = subprocess.run(["bash", "-n"], input=build(schema=server_db.SCHEMA_SQL.read_text(),
                                                           compose=(server_db.DEPLOY_DB / "compose.yml").read_text(),
                                                           roles=(server_db.DEPLOY_DB / "roles.sql").read_text(),
                                                           grants=(server_db.DEPLOY_DB / "grants.sql").read_text()),
                              text=True, capture_output=True)
        self.assertEqual((done.returncode, done.stderr), (0, ""))

    def test_passwords_are_generated_only_when_db_env_is_absent(self):
        script = build()
        guard = script.index("if [ ! -f /opt/openaiwill/db/db.env ]; then")
        self.assertLess(guard, script.index("a=$(newpw)"))
        self.assertLess(script.index("a=$(newpw)"), script.index("fi\nchmod 600 /opt/openaiwill/db/db.env"))
        self.assertEqual(script.count("newpw)"), 3)
        self.assertEqual(script.count("openssl rand"), 1)

    def test_secret_files_are_written_with_umask_077_and_mode_600(self):
        script = build()
        self.assertTrue(script.startswith("umask 077\n"))
        self.assertIn("chmod 600 /opt/openaiwill/db/db.env", script)
        self.assertIn("chmod 600 /opt/openaiwill/site.env", script)

    def test_site_env_holds_the_site_roles_url_on_the_docker_name(self):
        self.assertIn("DATABASE_URL=postgres://oaw_site:%s@openaiwill-db:5432/openaiwill", build())

    def test_site_env_is_never_rewritten_and_never_made_without_db_env(self):
        script = build()
        self.assertIn("if [ ! -f /opt/openaiwill/site.env ]; then", script)
        self.assertIn("site.env exists but db/db.env does not", script)

    def test_no_password_is_ever_printed_or_put_on_a_command_line(self):
        script = build()
        for name in ("$a", "$b", "$c", "$pw"):
            for line in script.splitlines():
                if name in line:
                    self.assertTrue(line.lstrip().startswith(("a=", "printf", "pw=", "[ -n")) or "> /opt" in line, line)
        self.assertNotIn("echo \"$", script.replace('echo "$p"', ""))
        self.assertNotRegex(script, r"PGPASSWORD=[^\"]")
        self.assertNotIn("set -x", script)
        self.assertNotIn(" -e PGPASSWORD", script)
        self.assertEqual(script.count("--env-file"), 6)

    def test_every_remote_value_is_quoted_from_the_deploy_root(self):
        script = build({**TARGET, "DEPLOY_ROOT": "/opt/my site"})
        self.assertIn("'/opt/my site/db/db.env'", script)
        self.assertNotRegex(script, r"(?<!')/opt/my site")

    def test_the_network_is_created_only_when_absent(self):
        self.assertIn("docker network inspect openaiwill >/dev/null 2>&1 || sudo docker network create openaiwill",
                      build())

    def test_the_schema_is_applied_as_the_writer_and_grants_follow(self):
        script = build()
        tail = script[script.index("up -d --wait"):]
        steps = re.findall(r"-U (\w+) -d (\w+) < (\S+)", tail)
        self.assertEqual(steps, [("postgres", "postgres", "roles.sql"), ("oaw_kg_writer", "openaiwill", "001_kg.sql"),
                                 ("oaw_kg_writer", "openaiwill", "grants.sql")])

    def test_the_four_files_are_uploaded_before_the_database_starts(self):
        script = build()
        for name in ("compose.yml", "roles.sql", "001_kg.sql", "grants.sql"):
            self.assertLess(script.index(f"cat > /opt/openaiwill/db/{name} <<"), script.index("up -d --wait"))

    def test_both_roles_are_checked_with_their_passwords_at_the_end(self):
        script = build()
        self.assertIn('PGPASSWORD="$OAW_KG_WRITER_PASSWORD" psql -X -h 127.0.0.1 -U oaw_kg_writer', script)
        self.assertIn('PGPASSWORD="$OAW_SITE_PASSWORD" psql -X -h 127.0.0.1 -U oaw_site', script)

    def test_a_here_document_does_not_leave_the_script_without_its_stdin_commands(self):
        # Every command that could read the script from stdin has its own redirect.
        for line in build().splitlines():
            if "docker exec" in line or "docker compose" in line and "up" in line:
                self.assertTrue("<" in line or "docker compose" in line, line)


class DeployFilesTest(unittest.TestCase):
    compose = (server_db.DEPLOY_DB / "compose.yml").read_text()
    roles = (server_db.DEPLOY_DB / "roles.sql").read_text()
    grants = (server_db.DEPLOY_DB / "grants.sql").read_text()

    def test_the_database_binds_loopback_only_on_5434_and_joins_the_network(self):
        self.assertIn('"127.0.0.1:5434:5432"', self.compose)
        self.assertIn("postgres:16-alpine", self.compose)
        self.assertIn("container_name: openaiwill-db", self.compose)
        self.assertIn("restart: unless-stopped", self.compose)
        self.assertIn("pg_isready", self.compose)
        self.assertRegex(self.compose, r"networks:\n  openaiwill:\n    external: true")

    def test_no_credential_is_written_in_the_files(self):
        self.assertIn("${POSTGRES_PASSWORD:?", self.compose)
        self.assertNotRegex(self.compose + self.roles + self.grants, r"(?i)password\s*[:=]\s*['\"]?[a-z0-9]{16,}")

    def test_roles_are_created_idempotently_and_the_site_role_is_minimal(self):
        self.assertIn("WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'oaw_kg_writer')", self.roles)
        self.assertIn("WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'openaiwill')", self.roles)
        self.assertIn("OWNER oaw_kg_writer", self.roles)
        self.assertIn("REVOKE ALL ON DATABASE openaiwill FROM PUBLIC", self.roles)
        self.assertIn("GRANT CONNECT ON DATABASE openaiwill TO oaw_site", self.roles)
        self.assertNotIn("SUPERUSER ", self.roles.replace("NOSUPERUSER ", ""))

    def test_site_role_may_only_read_kg_now_and_later(self):
        self.assertIn("GRANT USAGE ON SCHEMA kg TO oaw_site", self.grants)
        self.assertIn("GRANT SELECT ON ALL TABLES IN SCHEMA kg TO oaw_site", self.grants)
        self.assertIn("ALTER DEFAULT PRIVILEGES FOR ROLE oaw_kg_writer IN SCHEMA kg GRANT SELECT ON TABLES TO oaw_site",
                      self.grants)
        for verb in ("INSERT", "UPDATE", "DELETE", "ALL PRIVILEGES"):
            self.assertNotIn(verb, self.grants)

    def test_the_site_compose_requires_the_database_and_the_network(self):
        compose = (site_release.ROOT / "deploy" / "compose.yml").read_text()
        self.assertIn('SITE_REQUIRE_DATABASE: "1"', compose)
        self.assertIn("env_file: ${SITE_ENV_FILE", compose)
        self.assertRegex(compose, r"networks:\n  openaiwill:\n    external: true")


class PollTest(unittest.TestCase):
    def run_poll(self, bodies, expected="D2", seconds=9, interval=3):
        clock = {"t": 0.0}
        calls = iter(bodies)

        def read():
            item = next(calls)
            if item is None:
                raise site_release.ReleaseError("no answer")
            return item

        def sleep(n):
            clock["t"] += n

        result = server_db.poll_release(read, expected, seconds, interval, sleep, lambda: clock["t"])
        return result, clock["t"]

    @staticmethod
    def body(release):
        return '{"data": {"releaseId": "%s", "source": "database"}}' % release

    def test_it_stops_as_soon_as_the_site_serves_the_release(self):
        (matched, last), waited = self.run_poll([self.body("D1"), self.body("D2")])
        self.assertEqual((matched, last, waited), (True, "D2", 3))

    def test_it_gives_up_after_the_deadline_and_reports_what_it_saw(self):
        (matched, last), waited = self.run_poll([self.body("D1")] * 10)
        self.assertEqual((matched, last), (False, "D1"))
        self.assertGreaterEqual(waited, 9)

    def test_a_site_that_never_answers_is_reported_as_nothing_seen(self):
        (matched, last), _ = self.run_poll([None] * 10)
        self.assertEqual((matched, last), (False, ""))

    def test_a_failed_read_does_not_end_the_wait(self):
        (matched, _), _ = self.run_poll([None, self.body("D2")])
        self.assertTrue(matched)


if __name__ == "__main__":
    unittest.main()
