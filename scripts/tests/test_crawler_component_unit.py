"""Offline tests for the crawler component's shared machinery (no twikit, no network)."""
import asyncio
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crawler import cli  # noqa: E402
from crawler.core import accounts, archive, errors, proxy  # noqa: E402
from crawler.x import timeline  # noqa: E402

START = datetime(2026, 9, 14, tzinfo=timezone.utc)


class Clock:
    def __init__(self):
        self.t = START

    def now(self):
        return self.t

    def loop_time(self):
        return self.t.timestamp()

    async def sleep(self, seconds):
        self.t += timedelta(seconds=seconds)
        await asyncio.sleep(0)  # yield like a real sleep, so other workers progress


def post(post_id, author_id, handle, when="Wed Sep 10 00:00:00 +0000 2026", legacy=True):
    result = {"rest_id": post_id, "views": {"count": "1"},
              "core": {"user_results": {"result": {"rest_id": author_id, "core": {"screen_name": handle}}}}}
    if legacy:
        result["legacy"] = {"created_at": when, "full_text": "x"}
    return {"content": {"itemContent": {"tweet_results": {"result": result}}}}


def page(entries, cursor=None, rate_limit=None, status=200):
    add = {"type": "TimelineAddEntries", "entries": list(entries)}
    if cursor:
        add["entries"].append({"content": {"cursorType": "Bottom", "value": cursor}})
    data = {"data": {"user": {"result": {"timeline_v2": {"timeline": {"instructions": [add]}}}}}}
    return {"http_status": status, "data": data, "rate_limit": rate_limit}


def target(job_id, handle="H", author_id="1"):
    return {"id": job_id, "handle": handle, "author_id": author_id,
            "window_start": "2026-09-01T00:00:00Z", "window_end": "2026-09-14T00:00:00Z"}


def pool_of(labels, clock):
    return accounts.AccountPool(None, [{"label": l, "auth_token": "t", "ct0": None, "status": "usable",
                                        "cooldown_until": None, "last_used_at": None} for l in labels],
                                {}, clock=clock.now)


class Scripted:
    """A session answering fetch_page from a list of pages/exceptions."""

    def __init__(self, script, log=None):
        self.script = list(script)
        self.log = log

    async def fetch_page(self, cursor):
        if self.log is not None:
            self.log.append("fetch")
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        await asyncio.sleep(0)
        return item

    async def close(self):
        pass


def run(jobs, pool, factory, clock, **kw):
    return timeline.run(jobs, pool, factory, pace=0, sleep=clock.sleep,
                        loop_time=clock.loop_time, timeout=10_000, **kw)


class ClassifyPage(unittest.TestCase):
    def test_a_429_carries_the_provider_reset(self):
        with self.assertRaises(errors.RateLimited) as ctx:
            errors.classify_page({"http_status": 429, "data": {}, "rate_limit": {"reset": 123}})
        self.assertEqual(ctx.exception.reset_at, 123)

    def test_a_404_is_a_schema_change_not_a_transport_error(self):
        with self.assertRaises(errors.SchemaChanged):
            errors.classify_page({"http_status": 404, "data": {}})

    def test_graphql_errors_without_data_are_transient(self):
        with self.assertRaises(errors.TransportError):
            errors.classify_page({"http_status": 200, "data": {"errors": [{"code": 0}]}})


class Engine(unittest.IsolatedAsyncioTestCase):
    async def test_a_spent_rate_budget_stops_before_x_answers_429(self):
        reset = int(START.timestamp()) + 300
        pages = [page([post("1", "1", "H")], cursor="C1",
                      rate_limit={"limit": 50, "remaining": 0, "reset": reset})]

        async def fetch(cursor):
            return pages.pop(0)
        with self.assertRaises(errors.RateLimited) as ctx:
            await timeline.crawl_target(target("j"), fetch, pace=0)
        self.assertEqual(ctx.exception.reset_at, reset)

    async def test_an_unrecognised_structure_is_a_schema_change(self):
        async def fetch(cursor):
            return {"http_status": 200, "data": {"data": {"user": {}}}}
        with self.assertRaises(errors.SchemaChanged):
            await timeline.crawl_target(target("j"), fetch, pace=0)


class Scheduler(unittest.IsolatedAsyncioTestCase):
    async def test_a_rate_limit_cools_until_the_provider_reset(self):
        clock = Clock()
        reset = int(START.timestamp()) + 120
        pool = pool_of(["bad", "good"], clock)

        async def factory(lease, job):
            if lease.label == "bad":
                return Scripted([errors.RateLimited("429", reset_at=reset)])
            return Scripted([page([post("1", "1", "H")])])
        state, _ = await run([target("j")], pool, factory, clock)
        self.assertTrue(state["ok"])
        until = datetime.fromisoformat(pool._by_label["bad"]["cooldown_until"])
        self.assertEqual(until.timestamp(), reset + accounts.COOLDOWN_MARGIN)

    async def test_a_schema_change_stops_the_batch_without_retrying(self):
        clock = Clock()
        pool = pool_of(["a", "b", "c"], clock)
        made = []

        async def factory(lease, job):
            made.append(job["id"])
            return Scripted([errors.SchemaChanged("endpoint returned 404")])
        state, results = await run([target("j0"), target("j1"), target("j2")], pool, factory, clock,
                                   concurrency=1)
        self.assertFalse(state["ok"])
        self.assertEqual(made, ["j0"])                         # nobody asked again
        self.assertEqual({j["stop_reason"] for j in state["jobs"].values()}, {"schema_changed"})
        self.assertEqual(state["schema_change"]["job_id"], "j0")
        self.assertEqual(pool.health_summary()["dead"], 0)     # not the accounts' fault
        self.assertEqual(set(results), {"j0", "j1", "j2"})

    async def test_one_refused_record_fails_only_its_job_without_retry(self):
        clock = Clock()
        pool = pool_of(["a"], clock)
        made = []

        async def factory(lease, job):
            made.append(job["id"])
            if job["id"] == "odd":
                return Scripted([page([post("1", "1", "H", legacy=False)])])
            return Scripted([page([post("2", "1", "H")])])
        state, _ = await run([target("odd"), target("fine")], pool, factory, clock, concurrency=1)
        self.assertEqual(made, ["odd", "fine"])
        self.assertEqual(state["jobs"]["odd"]["stop_reason"], "parse_error:ValueError")
        self.assertEqual(state["jobs"]["fine"]["status"], "search_ended")

    async def test_two_workers_never_share_one_account(self):
        clock = Clock()
        pool = pool_of(["only"], clock)
        active, overlap = set(), []

        class Tracked(Scripted):
            def __init__(self, label):
                super().__init__([page([post("1", "1", "H")])])
                self.label = label
                overlap.append(label in active)
                active.add(label)

            async def close(self):
                active.discard(self.label)

        async def factory(lease, job):
            return Tracked(lease.label)
        state, _ = await run([target("j0"), target("j1")], pool, factory, clock, concurrency=2)
        self.assertTrue(state["ok"])
        self.assertEqual(overlap, [False, False])

    async def test_a_spent_budget_after_the_last_page_rests_the_account(self):
        clock = Clock()
        reset = int(START.timestamp()) + 600
        pool = pool_of(["a"], clock)

        async def factory(lease, job):
            return Scripted([page([post("1", "1", "H")], rate_limit={"remaining": 0, "reset": reset})])
        state, _ = await run([target("j")], pool, factory, clock)
        self.assertTrue(state["ok"])
        self.assertEqual(pool.health_summary()["cooldown"], 1)

    async def test_an_absurd_reset_header_falls_back_to_the_fixed_cooldown(self):
        clock = Clock()
        pool = pool_of(["bad", "good"], clock)

        async def factory(lease, job):
            if lease.label == "bad":
                return Scripted([errors.RateLimited("429", reset_at=START.timestamp() + 10 ** 7)])
            return Scripted([page([post("1", "1", "H")])])
        await run([target("j")], pool, factory, clock, cooldown_seconds=900)
        until = datetime.fromisoformat(pool._by_label["bad"]["cooldown_until"])
        self.assertEqual(until - START, timedelta(seconds=900))


class Cli(unittest.TestCase):
    def test_the_pnpm_separator_is_dropped_before_or_after_the_subcommand(self):
        for argv in (["timeline", "--", "--start", "a", "--end", "b", "--output", "o.json"],
                     ["--", "timeline", "--start", "a", "--end", "b", "--output", "o.json"]):
            self.assertEqual(cli.parse_args(argv).command, "timeline")

    def test_requests_faster_than_three_seconds_are_refused(self):
        args = cli.parse_args(["lookup", "--handles", "a", "--output", "o.json", "--pace", "1"])
        self.assertIsNotNone(cli.validate(args))

    def test_expected_posts_must_be_ids(self):
        args = cli.parse_args(["timeline", "--start", "a", "--end", "b", "--output", "o.json",
                               "--expect-post", "abc"])
        self.assertIsNotNone(cli.validate(args))


class Config(unittest.TestCase):
    def test_the_proxy_is_read_from_the_project_env_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp, ".agents/skills/social-qingguo-collector")
            skill.mkdir(parents=True)
            (skill / ".env").write_text("CRAWLER_TEST_ONLY_KEY=from-skill\n")
            Path(tmp, ".env").write_text("CRAWLER_TEST_PROJECT_KEY=from-project\n")
            try:
                proxy.load_env(Path(tmp))
                self.assertEqual(os.environ.get("CRAWLER_TEST_PROJECT_KEY"), "from-project")
                self.assertIsNone(os.environ.get("CRAWLER_TEST_ONLY_KEY"))
            finally:
                os.environ.pop("CRAWLER_TEST_PROJECT_KEY", None)

    def test_implementation_hashes_cover_every_source_file(self):
        hashes = archive.implementation_hashes()
        for name in ("core/scheduler.py", "x/timeline.py", "x/client.py", "cli.py"):
            self.assertIn(name, hashes)

    def test_run_files_are_new_and_under_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "data").mkdir()
            out = archive.reserve(Path(tmp, "data/run.json"), root=Path(tmp))
            archive.write_json(out, {})
            with self.assertRaises(ValueError):
                archive.reserve(out, root=Path(tmp))
            with self.assertRaises(ValueError):
                archive.reserve(Path(tmp, "elsewhere.json"), root=Path(tmp))


if __name__ == "__main__":
    unittest.main()
