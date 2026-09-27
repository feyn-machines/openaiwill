"""Offline tests for concurrent scheduling, failover, and progress rendering."""
import asyncio
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crawler import scheduler, accounts, progress, engine  # noqa: E402


def tweet_entry(post_id, when="Wed Sep 10 00:00:00 +0000 2026", handle="OpenAI", author_id="1"):
    return {"content": {"itemContent": {"tweet_results": {"result": {
        "rest_id": post_id, "legacy": {"created_at": when, "full_text": "x"},
        "views": {"count": "1"},
        "core": {"user_results": {"result": {
            "rest_id": author_id, "core": {"screen_name": handle},
            "legacy": {"screen_name": handle}}}}}}}}}


def timeline(entries, cursor=None):
    add = {"type": "TimelineAddEntries", "entries": list(entries)}
    if cursor is not None:
        add["entries"].append({"content": {"cursorType": "Bottom", "value": cursor}})
    return {"data": {"user": {"result": {"timeline_v2": {"timeline": {"instructions": [add]}}}}}}


def ok_page(handle, author_id):
    # single in-window post, no cursor => search_ended in one page
    return {"http_status": 200, "data": timeline([tweet_entry("1", handle=handle, author_id=author_id)], cursor=None)}


class Clock:
    def __init__(self):
        self.t = datetime(2026, 9, 14, tzinfo=timezone.utc)

    def now(self):
        return self.t

    def loop_time(self):
        return self.t.timestamp()

    async def sleep(self, seconds):
        self.t += timedelta(seconds=seconds)


def make_target(job_id, handle, author_id):
    return {"id": job_id, "handle": handle, "author_id": author_id,
            "window_start": "2026-09-01T00:00:00Z", "window_end": "2026-09-14T00:00:00Z"}


class FakeSession:
    def __init__(self, behavior, handle, author_id):
        self.behavior = behavior  # 'ok' | 'rate' | 'auth'
        self.handle, self.author_id = handle, author_id
        self.closed = False

    async def fetch_page(self, cursor):
        if self.behavior == "rate":
            return {"http_status": 429, "data": {}}
        if self.behavior == "auth":
            return {"http_status": 200, "data": {"errors": [{"code": 32}]}}
        return ok_page(self.handle, self.author_id)

    async def close(self):
        self.closed = True


def pool_with(labels, clock, status="usable"):
    accts = [{"label": l, "username": l, "auth_token": f"t-{l}", "ct0": None,
              "status": status, "cooldown_until": None, "last_used_at": None} for l in labels]
    return accounts.AccountPool(None, accts, {}, clock=clock.now)


class SchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_jobs_complete_concurrently(self):
        clock = Clock()
        jobs = [make_target(f"j{i}", f"H{i}", str(i)) for i in range(4)]
        pool = pool_with(["a", "b"], clock)

        async def factory(lease, target):
            return FakeSession("ok", target["handle"], target["author_id"])

        state, results = await scheduler.run_jobs(
            jobs, pool, factory, concurrency=2, pace=0, max_requests=100,
            timeout=1000, sleep=clock.sleep, loop_time=clock.loop_time)
        self.assertTrue(state["ok"])
        self.assertEqual(state["status"], "queries_exhausted")
        self.assertTrue(all(j["status"] == "search_ended" for j in state["jobs"].values()))
        self.assertEqual(len(results), 4)

    async def test_rate_limit_fails_over_to_other_account(self):
        clock = Clock()
        jobs = [make_target("j0", "H0", "0")]
        pool = pool_with(["bad", "good"], clock)
        seen = []

        async def factory(lease, target):
            seen.append(lease.label)
            return FakeSession("rate" if lease.label == "bad" else "ok", target["handle"], target["author_id"])

        state, results = await scheduler.run_jobs(
            jobs, pool, factory, concurrency=1, pace=0, max_requests=100,
            timeout=1000, sleep=clock.sleep, loop_time=clock.loop_time)
        self.assertTrue(state["ok"])
        self.assertEqual(state["jobs"]["j0"]["status"], "search_ended")
        self.assertGreaterEqual(len(state["failovers"]), 1)
        # 'bad' cooled down, job completed on 'good'
        self.assertEqual(pool.health_summary()["cooldown"], 1)
        self.assertIn("good", seen)

    async def test_auth_failure_retires_account(self):
        clock = Clock()
        jobs = [make_target("j0", "H0", "0")]
        pool = pool_with(["bad", "good"], clock)

        async def factory(lease, target):
            return FakeSession("auth" if lease.label == "bad" else "ok", target["handle"], target["author_id"])

        state, _ = await scheduler.run_jobs(
            jobs, pool, factory, concurrency=1, pace=0, max_requests=100,
            timeout=1000, sleep=clock.sleep, loop_time=clock.loop_time)
        self.assertTrue(state["ok"])
        self.assertEqual(pool.health_summary()["dead"], 1)

    async def test_exhausted_accounts_incomplete(self):
        clock = Clock()
        jobs = [make_target("j0", "H0", "0")]
        pool = pool_with(["only"], clock)

        async def factory(lease, target):
            return FakeSession("rate", target["handle"], target["author_id"])

        state, results = await scheduler.run_jobs(
            jobs, pool, factory, concurrency=1, pace=0, max_requests=100,
            timeout=1000, sleep=clock.sleep, loop_time=clock.loop_time, max_attempts=3)
        self.assertFalse(state["ok"])
        self.assertEqual(state["jobs"]["j0"]["status"], "incomplete")
        self.assertIn("j0", results)
        self.assertEqual(results["j0"]["accepted_count"], 0)

    async def test_transport_error_retries_same_account(self):
        clock = Clock()
        jobs = [make_target("j0", "H0", "0")]
        pool = pool_with(["only"], clock)
        state_holder = {"calls": 0}

        class Flaky:
            def __init__(self, handle, aid):
                self.handle, self.aid = handle, aid
                self.closed = False

            async def fetch_page(self, cursor):
                state_holder["calls"] += 1
                if state_holder["calls"] <= 2:
                    raise engine.TransportError("ConnectError")
                return ok_page(self.handle, self.aid)

            async def close(self):
                self.closed = True

        labels = []

        async def factory(lease, target):
            labels.append(lease.label)
            return Flaky(target["handle"], target["author_id"])

        state, _ = await scheduler.run_jobs(
            jobs, pool, factory, concurrency=1, pace=0, max_requests=100, timeout=1000,
            max_transient=8, transient_backoff=1, sleep=clock.sleep, loop_time=clock.loop_time)
        self.assertTrue(state["ok"])
        self.assertEqual(state["jobs"]["j0"]["status"], "search_ended")
        self.assertEqual(labels, ["only", "only", "only"])       # same account reused
        self.assertEqual(pool.health_summary()["dead"], 0)        # not retired
        self.assertEqual(pool.health_summary()["cooldown"], 0)    # not cooled
        self.assertEqual(state["jobs"]["j0"]["attempts"], 0)      # not an account failover

    async def test_transport_exhausted_incomplete(self):
        clock = Clock()
        jobs = [make_target("j0", "H0", "0")]
        pool = pool_with(["a", "b"], clock)

        class Always:
            def __init__(self):
                self.closed = False

            async def fetch_page(self, cursor):
                raise engine.TransportError("ConnectError")

            async def close(self):
                self.closed = True

        async def factory(lease, target):
            return Always()

        state, results = await scheduler.run_jobs(
            jobs, pool, factory, concurrency=1, pace=0, max_requests=100, timeout=1000,
            max_transient=3, transient_backoff=1, sleep=clock.sleep, loop_time=clock.loop_time)
        self.assertFalse(state["ok"])
        self.assertEqual(state["jobs"]["j0"]["stop_reason"], "transport_exhausted")
        self.assertEqual(pool.health_summary()["dead"], 0)

    async def test_sessions_are_closed(self):
        clock = Clock()
        jobs = [make_target("j0", "H0", "0")]
        pool = pool_with(["a"], clock)
        made = []

        async def factory(lease, target):
            s = FakeSession("ok", target["handle"], target["author_id"])
            made.append(s)
            return s

        await scheduler.run_jobs(jobs, pool, factory, concurrency=1, pace=0,
                                 max_requests=100, timeout=1000,
                                 sleep=clock.sleep, loop_time=clock.loop_time)
        self.assertTrue(all(s.closed for s in made))


class ProgressTests(unittest.TestCase):
    def _state(self):
        return {
            "started_at": (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat(),
            "requests": 12, "posts": 40,
            "jobs": {"a": {"status": "search_ended", "handle": "H"},
                     "b": {"status": "search_ended", "handle": "H"},
                     "c": {"status": "pending", "handle": "H"},
                     "d": {"status": "pending", "handle": "H"}},
            "workers": {0: {"phase": "crawling", "handle": "OpenAI", "page": 2, "label": "acc1"},
                        1: {"phase": "idle", "handle": None, "page": 0, "label": None}},
            "pool": {"usable": 3, "cooldown": 1, "dead": 0, "unverified": 0},
            "failovers": [{"handle": "OpenAI", "reason": "rate_limited", "account_label": "acc9"}],
            "status": "running",
        }

    def test_summary_and_eta(self):
        line = progress.summary_line(self._state())
        self.assertIn("jobs 2/4", line)
        self.assertIn("40 posts", line)
        self.assertIn("ETA", line)

    def test_block_shows_active_worker_and_pool(self):
        blk = progress.block(self._state())
        self.assertIn("@OpenAI p2 (acc1)", blk)
        self.assertIn("usable 3", blk)
        self.assertNotIn("w1", blk)  # idle worker not shown

    def test_final_summary(self):
        st = self._state()
        st["jobs"]["c"]["status"] = "incomplete"
        st["jobs"]["d"]["status"] = "search_ended"
        line = progress.final_summary(st)
        self.assertIn("3 complete, 1 incomplete of 4 jobs", line)


if __name__ == "__main__":
    unittest.main()


class AssembleOutputTests(unittest.TestCase):
    def _state(self, ok=True, jstatus="search_ended"):
        return {
            "ok": ok, "status": "queries_exhausted" if ok else "needs_attention",
            "started_at": "2026-09-14T00:00:00+00:00", "finished_at": "2026-09-14T00:05:00+00:00",
            "concurrency": 5, "budgets": {"max_pages": 10},
            "requests": 3,
            "jobs": {"j0": {"handle": "OpenAI", "company": "OpenAI", "status": jstatus,
                            "stop_reason": "window_start_reached", "pages": 2,
                            "accepted_count": 1, "attempts": 1, "account_label": "acc1"}},
            "workers": {}, "failovers": [], "pool": {"usable": 5, "cooldown": 0, "dead": 0},
        }

    def _results(self):
        return {"j0": {"handle": "OpenAI", "window_start": "2026-09-01T00:00:00+00:00",
                       "window_end": "2026-09-14T00:00:00+00:00",
                       "posts": [{"id": "111"}], "quarantine": [], "requests": [{"page": 1}],
                       "next_cursor": None}}

    def test_reconciliation_pass_and_no_secrets(self):
        from crawler import run
        doc = run.assemble_output(self._state(), self._results(), {}, ["111"])
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["reconciliation"]["status"], "passed")
        self.assertEqual(doc["total"], 1)
        self.assertNotIn("auth_token", json.dumps(doc))

    def test_missing_expected_fails_run(self):
        from crawler import run
        doc = run.assemble_output(self._state(), self._results(), {}, ["999"])
        self.assertFalse(doc["ok"])
        self.assertEqual(doc["reconciliation"]["status"], "missing")
        self.assertEqual(doc["reconciliation"]["missing_post_ids"], ["999"])

    def test_account_usage_labels_only(self):
        from crawler import run
        doc = run.assemble_output(self._state(), self._results(), {}, [])
        self.assertEqual(doc["account_usage"]["jobs"][0]["account_label"], "acc1")
        self.assertIn("pool_final", doc["account_usage"])
