import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import site_release as release  # noqa: E402

class ReleaseIdTest(unittest.TestCase):
    def test_id_is_build_time_and_commit(self):
        built = datetime(2026, 10, 3, 10, 29, 12, 430661, tzinfo=timezone.utc)
        self.assertEqual(release.release_id(built, "e2d4005", False), "20261003T102912Z-e2d4005")

    def test_time_is_converted_to_utc(self):
        built = datetime(2026, 10, 3, 18, 29, 12, tzinfo=timezone(timedelta(hours=8)))
        self.assertEqual(release.release_id(built, "e2d4005", False), "20261003T102912Z-e2d4005")

    def test_uncommitted_work_is_marked(self):
        built = datetime(2026, 10, 3, 10, 29, 12, tzinfo=timezone.utc)
        self.assertTrue(release.release_id(built, "e2d4005", True).endswith("-dirty"))

    def test_every_id_passes_the_validation_that_guards_remote_commands(self):
        built = datetime.now(timezone.utc)
        for dirty in (False, True):
            self.assertEqual(release.checked_id(release.release_id(built, "abcdef0", dirty)),
                             release.release_id(built, "abcdef0", dirty))


class ForbiddenEntriesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def put(self, relative, text="x"):
        path = self.dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_a_clean_release_has_none(self):
        self.put("app/server.js")
        self.put("app/.next/static/chunk.js")
        self.put("app/public/og/en.png")
        self.put("release.json", "{}")
        self.assertEqual(release.forbidden_entries(self.dir), [])

    def test_snapshot_secrets_and_local_data_are_caught(self):
        for relative in ["app/datasets/published/latest/events.json", "app/.env.local", "app/.env.deploy",
                         "app/data/runtime/x.db", "app/local/x-crawler/crawler/a.py", "app/key.pem",
                         "app/docs/whitepaper.md", "app/cookies.json"]:
            self.put(relative)
        found = release.forbidden_entries(self.dir)
        self.assertEqual(len(found), 8, found)


class PruneTest(unittest.TestCase):
    def test_keeps_the_newest_and_whatever_is_live(self):
        ids = [f"2026100{n}T000000Z-aaaaaaa" for n in range(1, 8)]
        self.assertEqual(release.to_prune(ids, keep=5, protected={ids[0]}), [ids[1]])

    def test_nothing_to_prune_below_the_limit(self):
        self.assertEqual(release.to_prune(["a", "b"], keep=5, protected=set()), [])


class CheckedIdTest(unittest.TestCase):
    def test_valid_ids_pass(self):
        for value in ["20261003T102912Z-e2d4005", "20261003T102912Z-e2d4005-dirty", " 20261003T102912Z-e2d4005\n"]:
            self.assertEqual(release.checked_id(value), value.strip())

    def test_anything_else_is_refused(self):
        for value in ["", "   ", "*", "../x", "a b", "20261003T102912Z-e2d4005;rm -rf /", "20261003T102912Z-e2d4005 x"]:
            with self.assertRaisesRegex(release.ReleaseError, "not a release id"):
                release.checked_id(value)

    def test_a_trailing_newline_is_not_part_of_an_id(self):
        self.assertIsNone(release.RELEASE_ID.fullmatch("20261003T102912Z-e2d4005\n"))
        self.assertEqual(release.valid_ids(["20261003T102912Z-e2d4005\n"]), [])

    def test_prune_never_returns_junk(self):
        ids = [f"2026100{n}T000000Z-aaaaaaa" for n in range(1, 8)]
        junk = ["*", "../x", "a b", "x;y", ".", ""]
        found = release.to_prune(junk + ids, keep=5, protected=set())
        self.assertEqual(found, ids[:2])
        self.assertEqual(release.to_prune(junk, keep=0, protected=set()), [])


class ForeignBinariesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_a_release_without_the_image_optimizer_has_none(self):
        (self.dir / "app" / "node_modules" / "next").mkdir(parents=True)
        self.assertEqual(release.foreign_binaries(self.dir), [])

    def test_sharp_and_its_binaries_are_found(self):
        for relative in ["app/node_modules/.pnpm/@img+sharp-darwin-arm64@0.34.5/node_modules/@img/sharp-darwin-arm64",
                         "app/node_modules/sharp", "app/node_modules/@img"]:
            (self.dir / relative).mkdir(parents=True)
        found = release.foreign_binaries(self.dir)
        self.assertIn("app/node_modules/sharp", found)
        self.assertIn("app/node_modules/@img", found)
        self.assertTrue(any("@img+sharp-darwin-arm64" in path for path in found), found)


class ForwardTest(unittest.TestCase):
    target = {"DEPLOY_HOST": "h.example", "DEPLOY_USER": "u", "DEPLOY_SSH_KEY": "/k/key"}

    def test_the_free_port_is_a_usable_port(self):
        port = release.free_port()
        self.assertTrue(1024 <= port <= 65535)

    def test_the_forward_can_reach_any_remote_port(self):
        argv = release.forward_argv(self.target, 51234, 5434)
        self.assertEqual(argv[argv.index("-L") + 1], "51234:127.0.0.1:5434")
        self.assertIn("ExitOnForwardFailure=yes", argv)

    def test_the_forward_reaches_the_candidate_slot_and_fails_loudly(self):
        argv = release.forward_argv(self.target, 51234)
        self.assertEqual(argv[0], "ssh")
        self.assertIn("ExitOnForwardFailure=yes", argv)
        self.assertIn("-N", argv)
        self.assertEqual(argv[argv.index("-L") + 1], "51234:127.0.0.1:8321")
        self.assertEqual(argv[-1], "u@h.example")
        self.assertEqual(argv[argv.index("-i") + 1], "/k/key")
        self.assertIn("BatchMode=yes", argv)

    def test_the_plain_ssh_command_is_unchanged(self):
        self.assertEqual(release.ssh_base(self.target)[-1], "u@h.example")
        self.assertNotIn("-L", release.ssh_base(self.target))


class FetchAndSmokeTest(unittest.TestCase):
    def test_the_default_user_agent_names_the_release_script(self):
        seen = {}

        class Opener:
            def open(self, request, timeout):
                seen.update(request.header_items())
                raise OSError("stop")

        original = release.urllib.request.build_opener
        release.urllib.request.build_opener = lambda *a: Opener()
        try:
            with self.assertRaises(release.ReleaseError):
                release.fetch("http://x.invalid/", headers={"RSC": "1"})
        finally:
            release.urllib.request.build_opener = original
        self.assertTrue(seen["User-agent"].startswith("openaiwill-release/1.0"))
        self.assertEqual(seen["Rsc"], "1")

    def test_an_unreachable_host_is_one_listed_failure(self):
        failures = release.smoke("http://127.0.0.1:1", None)
        self.assertEqual(len(failures), 1)
        self.assertIn("http://127.0.0.1:1 is not reachable", failures[0])


class RscRequestTest(unittest.TestCase):
    def test_the_request_is_the_one_the_router_sends(self):
        path, headers = release.rsc_request("/markets")
        # The hash Next 16 expects for exactly these headers (taken from its own 307 Location).
        self.assertEqual(path, "/markets?_rsc=OxBCQ2sR9P8GlKR3")
        self.assertEqual(headers["RSC"], "1")
        self.assertEqual(headers["Sec-Fetch-Dest"], "empty")


class PublicCheckMessageTest(unittest.TestCase):
    new = "20261003T102912Z-aaaaaaa"

    def test_a_reachability_failure_does_not_tell_the_operator_to_roll_back(self):
        message = release.public_check_message(self.new, ["https://openaiwill.com is not reachable: no answer (dns)"])
        self.assertIn("production IS switched", message)
        self.assertIn("pnpm site:indexnow", message)
        self.assertIn("Tunnel/DNS", message)
        self.assertNotIn("pnpm site:rollback", message)

    def test_a_page_failure_names_the_rollback(self):
        message = release.public_check_message(self.new, ["/markets: status 500, expected 200"])
        self.assertIn("pnpm site:rollback", message)
        self.assertIn("production IS switched", message)


class SmokeSelectionTest(unittest.TestCase):
    def test_without_data_no_detail_page_is_asked_for(self):
        self.assertEqual(release.detail_patterns(False), {})

    def test_with_data_every_kind_of_detail_page_is_asked_for(self):
        self.assertEqual(set(release.detail_patterns(True)),
                         {"market", "dotted occupation", "occupation group", "update", "work",
                          "Chinese dotted occupation"})

    def test_the_selection_is_a_copy(self):
        release.detail_patterns(True).clear()
        self.assertTrue(release.detail_patterns(True))


class LocalServerEnvTest(unittest.TestCase):
    base = {"PATH": "/bin", "DATABASE_URL": "postgres://x", "SITE_REQUIRE_DATABASE": "1", "SNAPSHOT_DIR": "/old"}

    def test_a_database_never_leaks_into_the_smoke_server(self):
        env = release.local_server_env("preview", None, self.base)
        for name in ("DATABASE_URL", "SITE_REQUIRE_DATABASE", "SNAPSHOT_DIR"):
            self.assertNotIn(name, env)
        self.assertEqual((env["SITE_ENV"], env["PATH"], env["PORT"]), ("preview", "/bin", str(release.LOCAL_PORT)))

    def test_the_release_id_reaches_healthz_and_is_validated(self):
        self.assertEqual(release.local_server_env("preview", None, self.base, "20261003T102912Z-aaaaaaa")["RELEASE_ID"],
                         "20261003T102912Z-aaaaaaa")
        with self.assertRaises(release.ReleaseError):
            release.local_server_env("preview", None, self.base, "x;y")

    def test_files_mode_points_at_the_snapshot_directory(self):
        env = release.local_server_env("production", Path("/snap"), self.base)
        self.assertEqual(env["SNAPSHOT_DIR"], "/snap")
        self.assertNotIn("SITE_REQUIRE_DATABASE", env)


class SnapshotChoiceTest(unittest.TestCase):
    def test_only_a_directory_with_a_manifest_selects_files_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = release.SNAPSHOT
            try:
                release.SNAPSHOT = Path(tmp)
                self.assertIsNone(release.snapshot_dir_for_smoke())
                (Path(tmp) / "manifest.json").write_text("{}")
                self.assertEqual(release.snapshot_dir_for_smoke(), Path(tmp))
            finally:
                release.SNAPSHOT = original


class HealthTest(unittest.TestCase):
    loaded = json.dumps({"ok": True, "release": "R1", "data": {"releaseId": "D1", "source": "database", "loadedAt": "t"}})
    empty = json.dumps({"ok": False, "release": "R1", "data": {"releaseId": None, "source": "none", "loadedAt": None}})

    def test_a_database_release_passes(self):
        self.assertEqual(release.data_release_failures(self.loaded), [])

    def test_no_release_says_to_publish_data_first(self):
        for body in (self.empty, "", "not json", "[]", json.dumps({"data": None}),
                     json.dumps({"data": {"releaseId": "D1", "source": "files"}})):
            failures = release.data_release_failures(body)
            self.assertEqual(len(failures), 1, body)
            self.assertIn("publish data first: pnpm data:release && pnpm data:promote", failures[0])

    def test_status_line(self):
        self.assertEqual(release.describe_health(self.loaded), "code R1, data D1 (database)")
        self.assertEqual(release.describe_health(self.empty), "code R1, no data release loaded")
        self.assertEqual(release.describe_health(""), "not running")
        self.assertEqual(release.describe_health(None), "not running")
        self.assertIn("not with a /healthz body", release.describe_health("<html>"))

    def test_probe_output_is_parsed_by_slot(self):
        out = f"PRODUCTION:{self.loaded}\nCANDIDATE:\n"
        found = release.parse_probe(out)
        self.assertEqual(found["PRODUCTION"], self.loaded)
        self.assertEqual(found["CANDIDATE"], "")
        self.assertEqual(release.describe_health(found["CANDIDATE"]), "not running")


class CandidateScriptTest(unittest.TestCase):
    target = {"DEPLOY_ROOT": "/opt/openaiwill", "DEPLOY_USER": "u"}
    new = "20261003T102912Z-aaaaaaa"

    def test_the_script_starts_only_the_candidate_slot_with_the_site_env_file_and_a_bounded_wait(self):
        script = release.candidate_script(self.target, self.new)
        self.assertIn("-p openaiwill-next up -d --build --wait --wait-timeout 180", script)
        self.assertIn("SITE_ENV_FILE=/opt/openaiwill/site.env", script)
        self.assertNotIn("-p openaiwill up", script)

    def test_every_wait_in_every_script_is_bounded(self):
        scripts = [release.candidate_script(self.target, self.new),
                   release.switch_script(self.target, self.new, "20261002T102912Z-bbbbbbb"),
                   release.switch_script(self.target, self.new, self.new)]
        for script in scripts:
            ups = [line for line in script.splitlines() if " up -d" in line]
            self.assertTrue(ups)
            for line in ups:
                for part in line.split("docker compose")[1:]:
                    if " up -d" in part:
                        self.assertIn("--wait-timeout 180", part)

    def test_the_diagnosis_prints_the_body_and_40_log_lines(self):
        script = release.candidate_diagnosis_script()
        self.assertIn("curl -s --max-time 5 http://127.0.0.1:8321/healthz", script)
        self.assertIn("docker logs --tail 40", script)
        self.assertIn("label=com.docker.compose.project=openaiwill-next", script)
        subprocess_check = __import__("subprocess").run(["bash", "-n"], input=script, text=True, capture_output=True)
        self.assertEqual(subprocess_check.returncode, 0, subprocess_check.stderr)

    def test_publish_data_first_only_for_database_mode_without_a_release(self):
        publish = "publish data first: pnpm data:release && pnpm data:promote"
        none_loaded = json.dumps({"ok": False, "release": "R", "data": {"releaseId": None, "source": "database"}})
        loaded = json.dumps({"ok": True, "release": "R", "data": {"releaseId": "D1", "source": "database"}})
        self.assertIn(publish, release.candidate_start_failure(none_loaded))
        self.assertNotIn(publish, release.candidate_start_failure(loaded))
        self.assertNotIn(publish, release.candidate_start_failure(""))
        self.assertNotIn(publish, release.candidate_start_failure("<html>502</html>"))
        self.assertNotIn(publish, release.candidate_start_failure(json.dumps({"data": {"source": "files", "releaseId": None}})))
        self.assertEqual(release.candidate_start_failure(""), "the candidate did not become healthy; see the output above")

    def test_every_compose_call_names_the_env_file(self):
        command = release.compose(self.target, release.PRODUCTION, self.new, "up -d --wait")
        self.assertIn("SITE_ENV_FILE=/opt/openaiwill/site.env", command)
        self.assertIn("HOST_PORT=8320", command)

    def test_the_env_file_path_is_quoted(self):
        command = release.compose({"DEPLOY_ROOT": "/opt/my site"}, release.CANDIDATE, self.new, "down")
        self.assertIn("SITE_ENV_FILE='/opt/my site/site.env'", command)

    def test_production_switch_uses_the_env_file_too(self):
        script = release.switch_script(self.target, self.new, "20261002T102912Z-bbbbbbb")
        self.assertEqual(script.count("SITE_ENV_FILE=/opt/openaiwill/site.env"), 2)


class DatabasePrecheckTest(unittest.TestCase):
    target = {"DEPLOY_ROOT": "/opt/openaiwill", "DEPLOY_USER": "u"}
    new = "20261003T102912Z-aaaaaaa"
    old = "20261002T102912Z-bbbbbbb"

    def test_production_is_touched_only_after_the_database_and_an_active_release_are_confirmed(self):
        for live in (self.old, "", self.new):
            script = release.switch_script(self.target, self.new, live)
            check = script.index("kg.active")
            self.assertLess(check, script.index("docker compose"))
            self.assertLess(script.index("production was not touched"), script.index("docker compose"))
            self.assertLess(script.index("no active data release") if "no active data release" in script
                            else script.index("has no active data release"), script.index("docker compose"))

    def test_the_check_runs_as_the_site_role_over_the_container_address(self):
        script = release.database_precheck(self.target)
        self.assertIn("-U oaw_site", script)
        self.assertIn('pg_isready -q -h "$ip"', script)
        self.assertIn('PGPASSWORD="$OAW_SITE_PASSWORD"', script)
        self.assertIn("SELECT release_id FROM kg.active", script)
        self.assertIn("--env-file /opt/openaiwill/db/db.env", script)
        self.assertNotIn("127.0.0.1", script)
        self.assertIn("</dev/null", script)

    def test_both_failures_stop_with_one_line_and_exit_1(self):
        script = release.database_precheck(self.target)
        self.assertIn("the database does not accept connections as oaw_site; production was not touched", script)
        self.assertIn("the database has no active data release (pnpm data:promote); production was not touched", script)
        self.assertEqual(script.count("exit 1"), 2)

    def test_the_precheck_is_valid_shell(self):
        done = __import__("subprocess").run(["bash", "-n"], input=release.switch_script(self.target, self.new, self.old),
                                            text=True, capture_output=True)
        self.assertEqual(done.returncode, 0, done.stderr)


class SwitchScriptTest(unittest.TestCase):
    target = {"DEPLOY_ROOT": "/opt/openaiwill", "DEPLOY_USER": "u"}
    new = "20261003T102912Z-aaaaaaa"
    old = "20261002T102912Z-bbbbbbb"

    def test_failure_restores_the_live_release_and_does_not_record_state_first(self):
        script = release.switch_script(self.target, self.new, self.old)
        self.assertIn(f"production restored to {self.old}", script)
        self.assertLess(script.index("production restored"), script.index("/previous"))
        self.assertLess(script.index("production restored"), script.rindex("/current"))

    def test_a_first_promote_stops_the_failed_release(self):
        script = release.switch_script(self.target, self.new, "")
        self.assertIn("no earlier release to restore; production slot stopped", script)
        self.assertIn("-p openaiwill down", script)
        self.assertLess(script.index("-p openaiwill down"), script.index("no earlier release to restore"))
        self.assertNotIn("production restored", script)
        self.assertNotIn("/previous", script)

    def test_a_failed_restore_says_production_is_down(self):
        script = release.switch_script(self.target, self.new, self.old)
        self.assertIn("|| { echo 'RESTORE FAILED: production is down' >&2; exit 1; }", script)
        self.assertIn(f"RESTORE FAILED: production is down; {self.old} is gone", script)

    def test_switching_to_the_live_release_does_not_claim_a_restore(self):
        script = release.switch_script(self.target, self.old, self.old)
        self.assertNotIn("production restored", script)
        self.assertIn(f"{self.old} did not become healthy; it is still the current release", script)


if __name__ == "__main__":
    unittest.main()
