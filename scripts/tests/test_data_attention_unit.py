"""Attention: how much notice an update drew, kept apart from what it showed.

rule:attention-baseline. The failure each test pins: a raw view count that is
really a big account's normal day, a snapshot taken two hours after posting
compared with one taken two weeks after, and a missing count read as zero.
"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline import attention

T0 = datetime(2026, 9, 4, 20, 0, tzinfo=timezone.utc)


def cap(hours, views, likes=0):
    return {"captured_at": T0 + timedelta(hours=hours), "metrics": {"views": views, "likes": likes}}


class PickTheComparableSnapshot(unittest.TestCase):
    """Two captures per post: when first seen, and the final one at day 7."""

    def test_prefers_the_day_seven_capture(self):
        chosen, age = attention.pick_capture([cap(1, 1), cap(80, 2), cap(170, 3), cap(400, 4)], T0)
        self.assertEqual(chosen["metrics"]["views"], 3)
        self.assertEqual(age, 170)

    def test_before_day_seven_the_latest_is_used_and_is_provisional(self):
        chosen, age = attention.pick_capture([cap(2, 1), cap(30, 9)], T0)
        self.assertEqual(chosen["metrics"]["views"], 9)
        self.assertTrue(attention.is_provisional(age))

    def test_a_day_seven_capture_is_final(self):
        self.assertFalse(attention.is_provisional(168))

    def test_no_capture_is_no_answer(self):
        self.assertEqual(attention.pick_capture([], T0), (None, None))


class RelativeToTheAccount(unittest.TestCase):
    def test_a_normal_day_for_a_big_account_is_one(self):
        posts = {"a": {"handle": "OpenAI", "views": 1_000_000},
                 "b": {"handle": "OpenAI", "views": 1_000_000},
                 "c": {"handle": "small", "views": 10_000},
                 "d": {"handle": "small", "views": 1_000}}
        ratios = attention.post_ratios(posts, field="views")
        self.assertEqual(ratios["a"], 1.0)
        self.assertGreater(ratios["c"], ratios["a"])

    def test_missing_views_stay_missing(self):
        posts = {"a": {"handle": "x", "views": None}, "b": {"handle": "x", "views": 100}}
        self.assertIsNone(attention.post_ratios(posts, field="views")["a"])

    def test_a_zero_baseline_gives_no_ratio_rather_than_infinity(self):
        posts = {"a": {"handle": "x", "views": 0}, "b": {"handle": "x", "views": 0}}
        self.assertIsNone(attention.post_ratios(posts, field="views")["a"])


class EventAttention(unittest.TestCase):
    def test_an_event_takes_its_most_engaged_post(self):
        posts = {"p1": {"handle": "h", "views": 900, "likes": 1, "engagement": 3, "age_hours": 70},
                 "p2": {"handle": "h", "views": 50, "likes": 5, "engagement": 40, "age_hours": 72}}
        ratios = {"p1": 0.5, "p2": 2.5}
        out = attention.event_attention({"e1": ["p1", "p2"]}, posts, ratios)
        self.assertEqual(out["e1"]["engagement"], 40)
        self.assertEqual(out["e1"]["views"], 50)
        self.assertEqual(out["e1"]["snapshot_age_hours"], 72)

    def test_views_bought_without_engagement_do_not_win(self):
        """The promoted-post case: millions of views, a handful of likes."""
        posts = {"ad": {"handle": "h", "views": 2_000_000, "likes": 3, "engagement": 5},
                 "real": {"handle": "h", "views": 90_000, "likes": 4_000, "engagement": 5_200}}
        out = attention.event_attention({"e": ["ad", "real"]}, posts, {})
        self.assertEqual(out["e"]["engagement"], 5_200)

    def test_engagement_sums_what_was_returned_and_keeps_missing_missing(self):
        self.assertEqual(attention.engagement({"likes": 3, "reposts": None, "quotes": 1, "replies": 0}), 4)
        self.assertIsNone(attention.engagement({"views": 10}))

    def test_an_event_with_no_measured_post_has_no_attention(self):
        out = attention.event_attention({"e1": ["p1"]}, {"p1": {"handle": "h", "engagement": None}}, {"p1": None})
        self.assertIsNone(out["e1"]["engagement"])

    def test_one_post_announcing_two_models_is_marked_as_shared(self):
        """'We're introducing Claude Fable 5.1 and Claude Mythos 5.1' is one post, two events."""
        rows = [{"source_id": "p", "account_handle": "AnthropicAI", "published_at": T0,
                 "captured_at": T0 + timedelta(hours=168), "metrics": {"likes": 80_000}}]
        links = [{"event_id": "fable", "source_id": "p"}, {"event_id": "mythos", "source_id": "p"}]
        out = attention.compute(rows, links)
        self.assertEqual(out["fable"]["source_id"], "p")
        self.assertEqual(out["fable"]["shared_by_events"], 2)
        self.assertEqual(out["mythos"]["shared_by_events"], 2)

    def test_percentiles_rank_only_measured_events(self):
        ranked = attention.percentiles({"a": 1.0, "b": 3.0, "c": None, "d": 2.0})
        self.assertEqual(ranked["b"], 1.0)
        self.assertEqual(ranked["a"], 0.0)
        self.assertIsNone(ranked["c"])


class SeriesBySubject(unittest.TestCase):
    def test_counts_updates_that_share_a_subject(self):
        events = [{"event_id": "1", "subject_key": "gpt-6-astra"},
                  {"event_id": "2", "subject_key": "gpt-6-astra"},
                  {"event_id": "3", "subject_key": None}]
        self.assertEqual(attention.series_sizes(events), {"gpt-6-astra": 2})


if __name__ == "__main__":
    unittest.main()
