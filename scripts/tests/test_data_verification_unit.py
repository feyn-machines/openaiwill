"""Third-party verification: when to look, where, and what a post can count as.

rule:verification-trigger and rule:verification-tier. The cases: the vendor's
own engineer praising the launch, an evaluator posting a benchmark, a
commentator's hot take, and an update nobody claimed anything big about.
"""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline import verification


class TierIsDerivedNotJudged(unittest.TestCase):
    """The post and its author's independence decide; the account's role does not."""

    def test_hands_on_evaluation_and_production_use_are_third_party(self):
        for nature in ("hands_on_test", "independent_evaluation", "own_production_use"):
            with self.subTest(nature=nature):
                self.assertEqual(verification.tier_for(nature, True), "T1")

    def test_expert_assessment_is_corroboration(self):
        self.assertEqual(verification.tier_for("expert_assessment", True), "T2")

    def test_nothing_from_an_author_tied_to_the_company(self):
        self.assertIsNone(verification.tier_for("hands_on_test", False))

    def test_opinions_and_relays_are_not_evidence(self):
        for nature in ("opinion", "relay", "unrelated"):
            with self.subTest(nature=nature):
                self.assertIsNone(verification.tier_for(nature, True))


class WhenToLook(unittest.TestCase):
    rows = [
        {"event_id": "a", "kind": "version_release", "capped": True, "percentile": 0.1},
        {"event_id": "b", "kind": "partnership", "capped": True, "percentile": 0.95},
        {"event_id": "c", "kind": "partnership", "capped": True, "percentile": 0.5},
        {"event_id": "d", "kind": "version_release", "capped": False, "percentile": 1.0},
        {"event_id": "e", "kind": "version_release", "capped": True, "percentile": 1.0, "provisional": True},
    ]

    def test_waits_for_day_seven_before_looking(self):
        """Heat is final and the reaction window closed at day 7; not before."""
        self.assertNotIn("e", verification.select_triggers(self.rows))

    def test_needs_a_held_down_claim_and_importance(self):
        self.assertEqual(verification.select_triggers(self.rows), ["a", "b"])


class WhereToLook(unittest.TestCase):
    def test_subject_key_becomes_search_words(self):
        self.assertEqual(verification.subject_terms("gpt-6-astra"), "gpt 6 astra")
        self.assertIsNone(verification.subject_terms(None))

    def test_a_post_mentions_the_product_when_every_word_is_there(self):
        self.assertTrue(verification.mentions("Tried GPT-6 Astra on our repo today", "gpt 6 astra"))
        self.assertTrue(verification.mentions("astra is strong; gpt-6 changed a lot", "gpt 6 astra"))
        self.assertFalse(verification.mentions("GPT-6 is out", "gpt 6 astra"))

    def test_word_boundaries_hold(self):
        self.assertFalse(verification.mentions("astrophysics with gpt 6", "gpt 6 astra"))

    def test_only_posts_in_the_seven_days_after_count(self):
        occurred = datetime(2026, 9, 4, 20, tzinfo=timezone.utc)
        inside = datetime(2026, 9, 11, 19, tzinfo=timezone.utc).timestamp()
        before = datetime(2026, 9, 4, 19, tzinfo=timezone.utc).timestamp()
        after = datetime(2026, 9, 11, 21, tzinfo=timezone.utc).timestamp()
        self.assertTrue(verification.in_window(inside, occurred))
        self.assertFalse(verification.in_window(before, occurred))
        self.assertFalse(verification.in_window(after, occurred))


class JudgeAnswers(unittest.TestCase):
    def test_a_level_choice_is_an_integer_category(self):
        self.assertEqual(verification.level_from_choice("L3"), 3)
        self.assertIsNone(verification.level_from_choice("not_shown"))
        self.assertIsNone(verification.level_from_choice(None))


if __name__ == "__main__":
    unittest.main()
