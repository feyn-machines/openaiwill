"""Offline unit tests for the crawler foundation (no twikit, no network)."""
import asyncio
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crawler.core import accounts, errors  # noqa: E402
from crawler.x import parse as parser, timeline as engine  # noqa: E402


def tweet_entry(post_id, when="Thu Sep 10 18:35:32 +0000 2026", handle="OpenAI",
                author_id="4398626122", reply=False, repost_of=None, quote_of=None):
    legacy = {"created_at": when, "full_text": f"post {post_id}",
              "favorite_count": "5", "retweet_count": "1", "reply_count": "0",
              "quote_count": "0", "bookmark_count": "2", "conversation_id_str": "777"}
    if reply:
        legacy["in_reply_to_status_id_str"] = "999"
        legacy["in_reply_to_user_id_str"] = "4398626122"
    if repost_of:
        legacy["retweeted_status_result"] = {"result": {"rest_id": repost_of}}
    if quote_of:
        legacy["quoted_status_id_str"] = quote_of
    return {"content": {"itemContent": {"tweet_results": {"result": {
        "rest_id": post_id, "legacy": legacy, "views": {"count": "100"},
        "core": {"user_results": {"result": {
            "rest_id": author_id, "core": {"screen_name": handle},
            "legacy": {"screen_name": handle}}}}}}}}}


def timeline(entries, cursor="CURSOR"):
    add = {"type": "TimelineAddEntries", "entries": list(entries)}
    if cursor is not None:
        add["entries"].append({"content": {"cursorType": "Bottom", "value": cursor}})
    return {"data": {"user": {"result": {"timeline_v2": {"timeline": {"instructions": [add]}}}}}}


class RelationTests(unittest.TestCase):
    """Each post keeps the post it answers, quotes or reposts."""

    def parse(self, **kw):
        posts, _ = parser.parse_user_timeline_page(timeline([tweet_entry("1", **kw)]))
        return posts[0]

    def test_a_reply_names_its_parent_and_conversation(self):
        p = self.parse(reply=True)
        self.assertEqual((p["reply_to_post_id"], p["reply_to_user_id"], p["conversation_id"]),
                         ("999", "4398626122", "777"))

    def test_a_repost_names_the_post_it_carries(self):
        self.assertEqual(self.parse(repost_of="555")["repost_of_post_id"], "555")

    def test_a_repost_in_the_wrapped_shape(self):
        posts, _ = parser.parse_user_timeline_page(timeline([tweet_entry("1")]))
        legacy = {"retweeted_status_result": {"result": {"tweet": {"rest_id": "556"}}}}
        self.assertEqual(parser._reposted_id(legacy), "556")

    def test_a_quote_names_the_quoted_post(self):
        self.assertEqual(self.parse(quote_of="444")["quoted_post_id"], "444")

    def test_an_original_post_has_no_upstream(self):
        p = self.parse()
        self.assertIsNone(p["reply_to_post_id"])
        self.assertIsNone(p["repost_of_post_id"])


class ParserTests(unittest.TestCase):
    def test_parses_posts_and_cursor(self):
        posts, cursor = parser.parse_user_timeline_page(timeline([tweet_entry("1")]))
        self.assertEqual(cursor, "CURSOR")
        self.assertEqual(len(posts), 1)
        p = posts[0]
        self.assertEqual(p["id"], "1")
        self.assertEqual(p["author"], "OpenAI")
        self.assertEqual(p["metrics"]["likes"], 5)
        self.assertEqual(p["metrics"]["views"], 100)
        self.assertFalse(p["is_reply"])

    def test_missing_metric_is_null_not_zero(self):
        entry = tweet_entry("1")
        del entry["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["reply_count"]
        posts, _ = parser.parse_user_timeline_page(timeline([entry]))
        self.assertIsNone(posts[0]["metrics"]["replies"])

    def test_errors_raise(self):
        with self.assertRaises(ValueError):
            parser.parse_user_timeline_page({"errors": [{"code": 88}]})

    def test_plan_timelines_one_job_per_account(self):
        acc = [{"handle": "OpenAI", "x_user_id": "4398626122", "enabled": True, "verification_status": "confirmed"},
               {"handle": "Anthropic", "x_user_id": "111", "enabled": True, "verification_status": "confirmed"}]
        jobs = parser.plan_timelines(acc, "2026-08-24T00:00:00Z", "2026-09-14T00:00:00Z")
        self.assertEqual(len(jobs), 2)
        self.assertEqual({j["mode"] for j in jobs}, {"user_timeline"})
        self.assertEqual(len({j["id"] for j in jobs}), 2)

    def test_unconfirmed_account_rejected(self):
        acc = [{"handle": "X", "x_user_id": "1", "enabled": True, "verification_status": "candidate"}]
        with self.assertRaises(ValueError):
            parser.plan_timelines(acc, "2026-08-24T00:00:00Z", "2026-09-14T00:00:00Z")


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def pool_file(tmp, accts):
    path = Path(tmp) / "pool.json"
    path.write_text(json.dumps({"schema": "x-account-pool/v1", "accounts": accts}))
    return path


class AccountPoolTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
        self.clock = Clock(self.now)

    def test_acquire_lru_and_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pool_file(tmp, [
                {"label": "a", "auth_token": "ta", "last_used_at": "2026-09-14T10:00:00+00:00"},
                {"label": "b", "auth_token": "tb", "last_used_at": None},
            ])
            pool = accounts.AccountPool.load(path, clock=self.clock)
            lease = pool.acquire()
            self.assertEqual(lease.label, "b")  # never-used first
            self.assertIsNone(lease.ct0)        # token-only => synthesize
            reloaded = json.loads(path.read_text())
            self.assertTrue(any(a["label"] == "b" and a["last_used_at"] for a in reloaded["accounts"]))

    def test_cooldown_excludes_until_expiry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pool_file(tmp, [{"label": "a", "auth_token": "t", "status": "usable"}])
            pool = accounts.AccountPool.load(path, clock=self.clock)
            pool.mark_cooldown("a", 300)
            self.assertIsNone(pool.acquire())
            self.assertEqual(pool.available_count(), 0)
            self.assertAlmostEqual(pool.next_cooldown_seconds(), 300, delta=1)
            self.clock.t = self.now + timedelta(seconds=301)
            self.assertIsNotNone(pool.acquire())

    def test_dead_never_leased(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pool_file(tmp, [{"label": "a", "auth_token": "t", "status": "usable"}])
            pool = accounts.AccountPool.load(path, clock=self.clock)
            pool.mark_dead("a", "suspended")
            self.assertIsNone(pool.acquire())
            self.assertEqual(pool.health_summary()["dead"], 1)

    def test_lease_repr_hides_secret(self):
        lease = accounts.Lease("a", "SECRET-TOKEN", None)
        self.assertNotIn("SECRET-TOKEN", repr(lease))


class EngineTests(unittest.IsolatedAsyncioTestCase):
    TARGET = {"id": "j1", "handle": "OpenAI", "author_id": "4398626122",
              "window_start": "2026-09-01T00:00:00Z", "window_end": "2026-09-14T00:00:00Z"}

    def _fetch(self, pages):
        calls = {"n": 0}

        async def fetch(cursor):
            page = pages[calls["n"]]
            calls["n"] += 1
            return page
        return fetch, calls

    async def test_window_filter_and_stop_at_start(self):
        in_window = timeline([tweet_entry("1", "Wed Sep 10 00:00:00 +0000 2026")], cursor="C2")
        before = timeline([tweet_entry("2", "Mon Aug 25 00:00:00 +0000 2026")], cursor="C3")
        fetch, calls = self._fetch([
            {"http_status": 200, "data": in_window},
            {"http_status": 200, "data": before},
        ])
        res = await engine.crawl_target(self.TARGET, fetch, pace=0, sleep=lambda s: asyncio.sleep(0))
        self.assertEqual(res["status"], "search_ended")
        self.assertEqual(res["stop_reason"], "window_start_reached")
        self.assertEqual(res["accepted_count"], 1)
        self.assertEqual(calls["n"], 2)

    async def test_identity_mismatch_quarantined(self):
        data = timeline([tweet_entry("1", "Wed Sep 10 00:00:00 +0000 2026", handle="Imposter", author_id="999")], cursor=None)
        fetch, _ = self._fetch([{"http_status": 200, "data": data}])
        res = await engine.crawl_target(self.TARGET, fetch, pace=0)
        self.assertEqual(res["accepted_count"], 0)
        self.assertEqual(res["quarantine"][0]["reason"], "author_identity_mismatch")

    async def test_cursor_cycle_incomplete(self):
        page = {"http_status": 200, "data": timeline([tweet_entry("1", "Wed Sep 10 00:00:00 +0000 2026")], cursor="SAME")}
        # same cursor returned twice
        fetch, _ = self._fetch([page, {"http_status": 200, "data": timeline([tweet_entry("1", "Wed Sep 10 00:00:00 +0000 2026")], cursor="SAME")}])
        res = await engine.crawl_target(self.TARGET, fetch, pace=0, sleep=lambda s: asyncio.sleep(0))
        self.assertEqual(res["stop_reason"], "cursor_cycle")

    async def test_rate_limit_raises_with_partial(self):
        fetch, _ = self._fetch([{"http_status": 429, "data": {}}])
        with self.assertRaises(errors.RateLimited) as ctx:
            await engine.crawl_target(self.TARGET, fetch, pace=0)
        self.assertIn("posts", ctx.exception.partial)

    async def test_auth_error_code_raises(self):
        fetch, _ = self._fetch([{"http_status": 200, "data": {"errors": [{"code": 32, "message": "bad token"}]}}])
        with self.assertRaises(errors.AuthFailed):
            await engine.crawl_target(self.TARGET, fetch, pace=0)


if __name__ == "__main__":
    unittest.main()
