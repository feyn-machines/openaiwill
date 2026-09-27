"""Offline regressions for missed official announcements and honest coverage."""
import asyncio
import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import official_x_collection as collection


ACCOUNTS = [
    {"handle": "OpenAI", "company": "OpenAI", "x_user_id": "4398626122", "enabled": True, "verification_status": "confirmed"},
    {"handle": "OpenAIDevs", "company": "OpenAI", "x_user_id": "1", "enabled": True, "verification_status": "confirmed"},
]


def post(post_id, when="2026-09-10T18:35:32+00:00", handle="OpenAI", author_id="4398626122"):
    return {"id": post_id, "author": handle, "author_id": author_id,
            "created_utc": datetime.fromisoformat(when).timestamp(),
            "text": "Announcement", "metrics": {"replies": 0, "views": None}}


def timeline_result(post_id, when="Thu Sep 10 18:35:32 +0000 2026", *, nested=False):
    result = {"rest_id": post_id, "legacy": {"id_str": post_id, "created_at": when,
              "full_text": "Financial announcement", "favorite_count": 0,
              "retweet_count": 2, "reply_count": 3, "quote_count": 1,
              "bookmark_count": None, "in_reply_to_status_id_str": None},
              "core": {"user_results": {"result": {"rest_id": "4398626122",
                       "legacy": {"screen_name": "OpenAI"}}}}, "views": {"count": "99"}}
    item = {"itemContent": {"tweet_results": {"result": result}}}
    if nested:
        return {"entryId": "profile-conversation-1", "content": {"items": [{"item": item}]}}
    return {"entryId": "tweet-" + post_id, "content": item}


def timeline_page(*entries, cursor="next"):
    values = list(entries)
    if cursor is not None:
        values.append({"entryId": "cursor-bottom-1", "content": {"cursorType": "Bottom", "value": cursor}})
    return {"data": {"user": {"result": {"timeline_v2": {"timeline": {"instructions": [
        {"type": "TimelineClearCache"}, {"type": "TimelineAddEntries", "entries": values}
    ]}}}}}}


class Search:
    """Network boundary: responses are keyed by the actual query and cursor."""
    def __init__(self, responses):
        self.responses = responses

    async def __call__(self, query, cursor):
        value = self.responses[(query, cursor)]
        if isinstance(value, Exception):
            raise value
        posts, next_cursor = value
        return {"posts": posts, "next_cursor": next_cursor, "http_status": 200}


class OfficialCollectionTests(unittest.TestCase):
    def jobs(self, accounts=None, start="2026-09-10T00:00:00Z", end="2026-09-11T00:00:00Z"):
        return collection.plan_queries(accounts or ACCOUNTS[:1], start, end)

    def run_collection(self, jobs, responses, **kwargs):
        options = {"max_pages": 5, "max_requests": 30, "pace": 0, "timeout": 10}
        options.update(kwargs)
        return asyncio.run(collection.collect(jobs, Search(responses), **options))

    def test_query_windows_do_not_overlap_or_combine_accounts(self):
        jobs = self.jobs(ACCOUNTS, "2026-09-06T16:00:00Z", "2026-09-08T16:00:00Z")
        self.assertEqual(len(jobs), 6)
        own = [j for j in jobs if j["handle"] == "OpenAI"]
        self.assertEqual([(j["window_start"], j["window_end"]) for j in own], [
            ("2026-09-06T16:00:00+00:00", "2026-09-07T00:00:00+00:00"),
            ("2026-09-07T00:00:00+00:00", "2026-09-08T00:00:00+00:00"),
            ("2026-09-08T00:00:00+00:00", "2026-09-08T16:00:00+00:00"),
        ])
        self.assertEqual(own[1]["query"], "(from:OpenAI) since:2026-09-07 until:2026-09-08")
        self.assertEqual(len({j["id"] for j in jobs}), 6)

    def test_account_timeline_plan_has_one_job_per_account_for_full_window(self):
        jobs = collection.plan_timelines(ACCOUNTS, "2026-09-06T16:00:00Z", "2026-09-08T16:00:00Z")
        self.assertEqual(len(jobs), 2)
        self.assertEqual({j["mode"] for j in jobs}, {"user_timeline"})
        self.assertEqual({j["window_start"] for j in jobs}, {"2026-09-06T16:00:00+00:00"})
        self.assertEqual({j["window_end"] for j in jobs}, {"2026-09-08T16:00:00+00:00"})
        self.assertEqual({j["query"] for j in jobs}, {"user_timeline:4398626122:Tweets", "user_timeline:1:Tweets"})

    def test_raw_timeline_parser_handles_top_level_and_conversation_posts(self):
        payload = timeline_page(timeline_result("2098118191029624911"), timeline_result("2098118232133792050", nested=True))
        posts, cursor = collection.extract_user_timeline_page(payload, observed_at="2026-09-12T00:00:00+00:00")
        self.assertEqual([p["id"] for p in posts], ["2098118191029624911", "2098118232133792050"])
        self.assertEqual(cursor, "next")
        self.assertEqual(posts[0]["author"], "OpenAI")
        self.assertEqual(posts[0]["author_id"], "4398626122")
        self.assertEqual(posts[0]["metrics"], {"likes": 0, "reposts": 2, "replies": 3, "quotes": 1, "bookmarks": None, "views": 99})
        self.assertEqual(posts[0]["metrics_observed_at"], "2026-09-12T00:00:00+00:00")

    def test_timeline_stops_only_after_a_whole_page_is_before_start(self):
        jobs = collection.plan_timelines(ACCOUNTS[:1], "2026-09-10T00:00:00Z", "2026-09-11T00:00:00Z")
        result = self.run_collection(jobs, {
            (jobs[0]["query"], None): ([post("2098118191029624911"), post("9", "2026-09-09T23:59:59Z")], "older"),
            (jobs[0]["query"], "older"): ([post("8", "2026-09-09T22:00:00Z")], "even-older"),
        }, expected_posts=["2098118191029624911"])
        self.assertTrue(result["ok"])
        self.assertEqual([p["id"] for p in result["posts"]], ["2098118191029624911"])
        self.assertEqual(result["queries"][0]["stop_reason"], "window_start_reached")
        self.assertEqual(len(result["requests"]), 2)

    def test_raw_timeline_parser_rejects_unavailable_tweet_result(self):
        payload = timeline_page({"entryId": "tweet-unavailable", "content": {"itemContent": {"tweet_results": {"result": {"__typename": "TweetUnavailable"}}}}})
        with self.assertRaisesRegex(ValueError, "unavailable"):
            collection.extract_user_timeline_page(payload)

    def test_native_cursor_reaches_financial_announcement_without_other_window_contamination(self):
        jobs = self.jobs(start="2026-09-10T00:00:00Z", end="2026-09-12T00:00:00Z")
        first, second = jobs
        result = self.run_collection(jobs, {
            (first["query"], None): ([post("2098200000000000000", "2026-09-10T23:00:00Z")], "finance-next"),
            (second["query"], None): ([post("2098442365669409049", "2026-09-11T16:03:41Z")], None),
            (first["query"], "finance-next"): ([post("2098118191029624911")], None),
        }, expected_posts=["2098118191029624911"])
        self.assertTrue(result["ok"])
        self.assertIn("2098118191029624911", [p["id"] for p in result["posts"]])
        self.assertEqual(result["reconciliation"]["missing_post_ids"], [])
        self.assertEqual([r["cursor_in"] for r in result["requests"]], [None, None, "finance-next"])
        self.assertEqual(result["requests"][2]["accepted_post_ids"], ["2098118191029624911"])

    def test_each_account_gets_first_page_before_busy_account_continues(self):
        jobs = self.jobs(ACCOUNTS)
        main, dev = jobs
        result = self.run_collection(jobs, {
            (main["query"], None): ([post("10")], "main-next"),
            (dev["query"], None): ([post("20", handle="OpenAIDevs", author_id="1")], None),
            (main["query"], "main-next"): ([post("11")], None),
        }, max_requests=2)
        self.assertEqual({p["id"] for p in result["posts"]}, {"10", "20"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["queries"][0]["stop_reason"], "request_budget")
        self.assertEqual(result["queries"][1]["stop_reason"], "no_cursor")

    def test_full_first_page_with_cursor_is_not_completed_coverage(self):
        jobs = self.jobs()
        result = self.run_collection(jobs, {(jobs[0]["query"], None): ([post(str(i)) for i in range(20)], "next")}, max_pages=1)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["posts"]), 20)
        self.assertEqual(result["queries"][0]["stop_reason"], "page_budget")
        self.assertEqual(result["queries"][0]["next_cursor"], "next")

    def test_empty_page_with_cursor_is_an_explicit_gap(self):
        jobs = self.jobs()
        result = self.run_collection(
            jobs,
            {(jobs[0]["query"], None): ([], "next")},
            max_pages=1,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["queries"][0]["status"], "incomplete")
        self.assertEqual(result["queries"][0]["stop_reason"], "empty_page_with_cursor")
        self.assertEqual(result["queries"][0]["next_cursor"], "next")

    def test_missing_known_announcement_fails_even_when_search_ends(self):
        jobs = self.jobs()
        result = self.run_collection(jobs, {(jobs[0]["query"], None): ([post("10")], None)}, expected_posts=["2098118191029624911"])
        self.assertFalse(result["ok"])
        self.assertEqual(result["reconciliation"]["missing_post_ids"], ["2098118191029624911"])
        self.assertEqual(result["queries"][0]["status"], "search_ended")

    def test_author_identity_mismatch_is_quarantined_and_fails_coverage(self):
        jobs = self.jobs()
        result = self.run_collection(jobs, {(jobs[0]["query"], None): ([post("10", author_id="999")], None)})
        self.assertFalse(result["ok"])
        self.assertEqual(result["posts"], [])
        self.assertEqual(result["quarantine"][0]["reason"], "author_identity_mismatch")

    def test_time_window_is_half_open_and_keeps_zero_and_null(self):
        jobs = self.jobs(start="2026-09-10T16:00:00Z", end="2026-09-10T23:00:00Z")
        result = self.run_collection(jobs, {(jobs[0]["query"], None): ([post("10"), post("11", "2026-09-10T23:00:00Z")], None)})
        self.assertEqual([p["id"] for p in result["posts"]], ["10"])
        self.assertEqual(result["posts"][0]["metrics"], {"replies": 0, "views": None})
        self.assertEqual(result["quarantine"][0]["reason"], "outside_exact_window")

    def test_provider_returning_another_day_cannot_pass_coverage(self):
        jobs = self.jobs()
        result = self.run_collection(jobs, {(jobs[0]["query"], None): ([post("10", "2026-09-04T18:00:00Z")], None)})
        self.assertFalse(result["ok"])
        self.assertEqual(result["quarantine"][0]["reason"], "outside_query_window")

    def test_rate_limit_stops_all_queries_and_saves_partial_state(self):
        jobs = self.jobs(ACCOUNTS)
        snapshots = []
        result = self.run_collection(jobs, {
            (jobs[0]["query"], None): ([post("10")], "next"),
            (jobs[1]["query"], None): RuntimeError("rate limited: private credential"),
        }, save=lambda state: snapshots.append(json.loads(json.dumps(state))))
        self.assertFalse(result["ok"])
        self.assertEqual([p["id"] for p in result["posts"]], ["10"])
        self.assertEqual(len(result["requests"]), 2)
        self.assertNotIn("private credential", json.dumps(result))
        self.assertEqual(snapshots[-1], result)

    def test_cursor_cycle_is_a_gap_and_does_not_loop(self):
        jobs = self.jobs()
        result = self.run_collection(jobs, {
            (jobs[0]["query"], None): ([post("10")], "a"),
            (jobs[0]["query"], "a"): ([post("11")], "b"),
            (jobs[0]["query"], "b"): ([post("12")], "a"),
        })
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["requests"]), 3)
        self.assertEqual(result["queries"][0]["stop_reason"], "cursor_cycle")

    def test_disabled_unverified_and_unknown_accounts_cannot_be_collected(self):
        accounts = ACCOUNTS + [{"handle": "Disabled", "enabled": False}]
        self.assertEqual(len(self.jobs(accounts)), 2)
        with self.assertRaises(ValueError):
            collection.plan_queries(accounts, "2026-09-10T00:00:00Z", "2026-09-11T00:00:00Z", handles=["Disabled"])
        with self.assertRaises(ValueError):
            self.jobs([{**ACCOUNTS[0], "x_user_id": None}])


if __name__ == "__main__":
    unittest.main()
