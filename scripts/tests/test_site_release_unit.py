import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import site_release as release  # noqa: E402
from data_pipeline.pipeline import digest  # noqa: E402

PAYLOAD = {
    "chain": {"events": [{"event_id": "e1"}], "evidence": [], "activities": [], "gates": [], "gate_edges": []},
    "markets": [], "tasks": [], "events": [{"event_id": "e1"}], "models": [], "sources": [],
    "coverage": {"a": 1}, "progress": {"b": 2},
}


def write_snapshot(directory, payload=PAYLOAD, **manifest):
    counts = {
        **{f"chain.{k}": len(v) for k, v in payload["chain"].items()},
        **{k: len(v) for k, v in payload.items() if isinstance(v, list)},
        **{k: 1 for k, v in payload.items() if isinstance(v, dict) and k != "chain"},
    }
    body = {"generated_at": "2026-10-03T10:29:12.430661+00:00", "counts": counts,
            "content_sha256": digest(payload), **manifest}
    for name, value in payload.items():
        (directory / f"{name}.json").write_text(json.dumps(value))
    (directory / "manifest.json").write_text(json.dumps(body))


class ReleaseIdTest(unittest.TestCase):
    def test_id_is_generation_time_and_commit(self):
        self.assertEqual(release.release_id("2026-10-03T10:29:12.430661+00:00", "e2d4005", False),
                         "20261003T102912Z-e2d4005")

    def test_time_is_converted_to_utc(self):
        self.assertEqual(release.release_id("2026-10-03T18:29:12+08:00", "e2d4005", False),
                         "20261003T102912Z-e2d4005")

    def test_uncommitted_work_is_marked(self):
        self.assertTrue(release.release_id("2026-10-03T10:29:12+00:00", "e2d4005", True).endswith("-dirty"))


class VerifySnapshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_a_consistent_snapshot_passes(self):
        write_snapshot(self.dir)
        self.assertEqual(release.verify_snapshot(self.dir)["content_sha256"], digest(PAYLOAD))

    def test_a_missing_manifest_fails(self):
        with self.assertRaisesRegex(release.ReleaseError, "manifest"):
            release.verify_snapshot(self.dir)

    def test_an_edited_file_fails(self):
        write_snapshot(self.dir)
        (self.dir / "events.json").write_text(json.dumps([{"event_id": "e1"}, {"event_id": "e2"}]))
        with self.assertRaisesRegex(release.ReleaseError, "content_sha256|counts"):
            release.verify_snapshot(self.dir)

    def test_a_missing_file_fails(self):
        write_snapshot(self.dir)
        (self.dir / "tasks.json").unlink()
        with self.assertRaisesRegex(release.ReleaseError, "tasks.json"):
            release.verify_snapshot(self.dir)


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


class SwitchScriptTest(unittest.TestCase):
    target = {"DEPLOY_ROOT": "/opt/openaiwill", "DEPLOY_USER": "u"}
    new = "20261003T102912Z-aaaaaaa"
    old = "20261002T102912Z-bbbbbbb"

    def test_failure_restores_the_live_release_and_does_not_record_state_first(self):
        script = release.switch_script(self.target, self.new, self.old)
        self.assertIn(f"production restored to {self.old}", script)
        self.assertLess(script.index("exit 1"), script.index("/previous"))
        self.assertLess(script.index("exit 1"), script.rindex("/current"))

    def test_a_first_promote_stops_the_failed_release(self):
        script = release.switch_script(self.target, self.new, "")
        self.assertIn("no earlier release to restore; production slot stopped", script)
        self.assertIn("-p openaiwill down", script)
        self.assertLess(script.index("-p openaiwill down"), script.index("exit 1"))
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
