"""The evidence panel's rules, without a database.

Every rule here decides whether a post can move a level, so each one is pinned
by the case that motivated it: an insider praising their own lab's model, a
researcher who changed employers mid-window, an account that went quiet.
"""
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline import panel

NOW = datetime(2026, 9, 23, tzinfo=timezone.utc)


def check(kind, outcome, days_ago=0, **detail):
    return {"check_kind": kind, "outcome": outcome,
            "checked_at": NOW - timedelta(days=days_ago), "detail": detail}


def account(**kw):
    base = {"owner_kind": "person", "panel_role": "practitioner", "panel_state": "candidate",
            "identity_grade": "first_party_link", "platform_account_id": "123"}
    base.update(kw)
    return base


class IndependenceIsPerCompanyAndPerDate(unittest.TestCase):
    affs = [
        {"org_id": "org:openai", "relation": "employee", "started_on": date(2026, 7, 1), "ended_on": None},
        {"org_id": "org:meta", "relation": "employee", "started_on": None, "ended_on": date(2025, 11, 30)},
        {"org_id": "org:google", "relation": "former", "started_on": None, "ended_on": None},
    ]

    def test_not_independent_of_a_current_employer(self):
        self.assertFalse(panel.is_independent(self.affs, "org:openai", date(2026, 9, 1)))

    def test_independent_of_that_employer_before_joining(self):
        self.assertTrue(panel.is_independent(self.affs, "org:openai", date(2026, 6, 1)))

    def test_independent_after_leaving(self):
        self.assertTrue(panel.is_independent(self.affs, "org:meta", date(2026, 1, 1)))
        self.assertFalse(panel.is_independent(self.affs, "org:meta", date(2025, 6, 1)))

    def test_a_former_relation_never_breaks_independence(self):
        self.assertTrue(panel.is_independent(self.affs, "org:google", date(2026, 9, 1)))

    def test_independent_of_a_company_never_listed(self):
        self.assertTrue(panel.is_independent(self.affs, "org:anthropic", date(2026, 9, 1)))

    def test_every_breaking_relation_breaks(self):
        for relation in ("employee", "founder", "investor", "advisor", "partner", "academic"):
            with self.subTest(relation=relation):
                affs = [{"org_id": "org:x", "relation": relation, "started_on": None, "ended_on": None}]
                self.assertFalse(panel.is_independent(affs, "org:x", date(2026, 9, 1)))


class StateIsDerivedFromChecks(unittest.TestCase):
    fresh = [check("platform_id", "pass", 1), check("affiliation", "pass", 10)]

    def test_confirmed_and_current_is_enabled(self):
        self.assertEqual(panel.derive_state(account(), self.fresh, NOW), "enabled")

    def test_no_platform_id_stays_candidate(self):
        self.assertEqual(panel.derive_state(account(platform_account_id=None), [], NOW), "candidate")

    def test_a_third_party_list_is_not_identity(self):
        a = account(identity_grade="third_party_list")
        self.assertEqual(panel.derive_state(a, self.fresh, NOW), "candidate")

    def test_own_bio_is_enough(self):
        a = account(identity_grade="official_bio")
        self.assertEqual(panel.derive_state(a, self.fresh, NOW), "enabled")

    def test_excluded_accounts_are_never_enabled(self):
        a = account(excluded=True)
        self.assertEqual(panel.derive_state(a, self.fresh, NOW), "identity_confirmed")

    def test_the_role_does_not_decide_the_state(self):
        """Accounts are not sorted into uses; a relay with a confirmed identity is collected."""
        self.assertEqual(panel.derive_state(account(panel_role="relay"), self.fresh, NOW), "enabled")

    def test_a_stale_affiliation_check_holds_a_person_back(self):
        checks = [check("platform_id", "pass", 1), check("affiliation", "pass", 121)]
        self.assertEqual(panel.derive_state(account(), checks, NOW), "identity_confirmed")
        was_enabled = account(panel_state="enabled")
        self.assertEqual(panel.derive_state(was_enabled, checks, NOW), "suspended")

    def test_an_organisation_needs_no_affiliation_check(self):
        a = account(owner_kind="organization", panel_role="evaluator")
        self.assertEqual(panel.derive_state(a, [check("platform_id", "pass", 1)], NOW), "enabled")

    def test_ninety_quiet_days_suspend(self):
        checks = self.fresh + [check("activity", "pass", 0, last_post_at=(NOW - timedelta(days=91)).isoformat())]
        self.assertEqual(panel.derive_state(account(panel_state="enabled"), checks, NOW), "suspended")

    def test_no_activity_data_yet_does_not_suspend(self):
        self.assertEqual(panel.derive_state(account(), self.fresh, NOW), "enabled")

    def test_a_handle_now_pointing_elsewhere_suspends(self):
        checks = self.fresh + [check("platform_id", "changed", 0)]
        self.assertEqual(panel.derive_state(account(panel_state="enabled"), checks, NOW), "suspended")

    def test_two_failed_rechecks_retire(self):
        checks = [check("platform_id", "pass", 30), check("platform_id", "fail", 2), check("platform_id", "fail", 1)]
        self.assertEqual(panel.derive_state(account(panel_state="enabled"), checks, NOW), "retired")

    def test_suspension_lifts_when_the_condition_clears(self):
        checks = [check("platform_id", "pass", 1), check("affiliation", "pass", 200),
                  check("affiliation", "pass", 0)]
        self.assertEqual(panel.derive_state(account(panel_state="suspended"), checks, NOW), "enabled")


class OrganisationNamesResolveByAlias(unittest.TestCase):
    registry = [{"org_id": "org:google", "aliases": ["Google", "Google DeepMind", "DeepMind"]},
                {"org_id": "org:meta", "aliases": ["Meta", "Meta AI"]}]

    def test_alias_inside_a_longer_name(self):
        self.assertEqual(panel.resolve_org("Google DeepMind (research scientist)", self.registry), "org:google")

    def test_word_boundaries_hold(self):
        self.assertIsNone(panel.resolve_org("Metaculus", self.registry))

    def test_unknown_stays_unknown(self):
        self.assertIsNone(panel.resolve_org("Wharton School", self.registry))


class RelationsFromDraftText(unittest.TestCase):
    def test_a_known_relation_passes_through(self):
        self.assertEqual(panel.relation_of({"relation": "founder", "org": "Ndea"}), "founder")

    def test_a_departed_organisation_is_former(self):
        self.assertEqual(panel.relation_of({"relation": "employee", "org": "Meta (left, announced 2025-11)"}), "former")
        self.assertEqual(panel.relation_of({"relation": "employee", "org": "OpenAI / Tesla (former)"}), "former")

    def test_an_unknown_relation_is_dropped_not_guessed(self):
        self.assertIsNone(panel.relation_of({"relation": "fan", "org": "OpenAI"}))



class ProbeFindings(unittest.TestCase):
    doc = {"hours": 720, "fetched_at": "2026-09-23T07:08:28+00:00", "posts": [
        {"author": "simonw", "author_id": "12497", "created_utc": 1790130936.0},
        {"author": "SimonW", "author_id": "12497", "created_utc": 1790000000.0},
        {"author": "someone_else", "author_id": "999", "created_utc": 1790130000.0},
    ]}

    def test_the_id_and_latest_post_come_from_the_accounts_own_posts(self):
        found = panel.probe_findings(self.doc, ["simonw", "quiet_one"])
        self.assertEqual(found["simonw"]["platform_account_id"], "12497")
        self.assertEqual(found["simonw"]["last_post_at"], "2026-09-23T02:35:36+00:00")

    def test_an_account_with_no_posts_in_the_window_resolves_nothing(self):
        found = panel.probe_findings(self.doc, ["simonw", "quiet_one"])
        self.assertIsNone(found["quiet_one"]["platform_account_id"])
        self.assertEqual(found["quiet_one"]["no_posts_in_hours"], 720)

    def test_a_handle_the_collector_never_queried_is_not_reported_at_all(self):
        """The collector stops at its account limit; unasked is not quiet."""
        doc = dict(self.doc, requests=[{"query": "from:simonw since:2026-08-24 until:2026-09-24"}])
        found = panel.probe_findings(doc, ["simonw", "quiet_one"])
        self.assertIn("simonw", found)
        self.assertNotIn("quiet_one", found)

    def test_two_ids_under_one_handle_is_a_conflict_not_a_pick(self):
        doc = {"hours": 720, "posts": [{"author": "x", "author_id": "1", "created_utc": 1.0},
                                       {"author": "x", "author_id": "2", "created_utc": 2.0}]}
        self.assertEqual(panel.probe_findings(doc, ["x"])["x"]["conflict"], ["1", "2"])



class RegistryForTheCrawler(unittest.TestCase):
    rows = [{"handle": "simonw", "platform_account_id": "12497", "panel_role": "practitioner",
             "org_name": None, "person_name": "Simon Willison"},
            {"handle": "arcprize", "platform_account_id": "177", "panel_role": "evaluator",
             "org_name": "ARC Prize", "person_name": None}]

    def test_rows_have_the_shape_the_crawler_requires(self):
        registry = panel.registry_rows(self.rows)
        for row in registry:
            self.assertTrue(row["enabled"])
            self.assertEqual(row["verification_status"], "confirmed")
            self.assertTrue(row["x_user_id"].isdigit())
        self.assertEqual(registry[0]["company"], "Simon Willison")
        self.assertEqual(registry[1]["company"], "ARC Prize")

    def test_an_account_without_an_id_is_left_out(self):
        rows = self.rows + [{"handle": "noid", "platform_account_id": None, "panel_role": "practitioner",
                             "org_name": None, "person_name": "N"}]
        self.assertEqual(len(panel.registry_rows(rows)), 2)


class LookupBecomesChecks(unittest.TestCase):
    found = {"status": "found", "user_id": "12497", "name": "Simon Willison",
             "description": "Creator of Datasette", "followers": 100, "following": 5, "posts": 9,
             "verified": False, "protected": False}

    def kinds(self, checks):
        return [(c[0], c[1]) for c in checks]

    def test_a_first_lookup_resolves_the_id_and_keeps_a_profile(self):
        new_id, checks = panel.lookup_checks(None, None, self.found)
        self.assertEqual(new_id, "12497")
        self.assertEqual(self.kinds(checks), [("platform_id", "pass"), ("profile", "pass")])

    def test_a_different_id_under_the_handle_is_a_change(self):
        new_id, checks = panel.lookup_checks("999", None, self.found)
        self.assertIsNone(new_id)
        self.assertEqual(self.kinds(checks), [("platform_id", "changed")])

    def test_a_changed_bio_sends_the_affiliation_back_for_review(self):
        before = {"description": "Founder, Eureka Labs"}
        after = dict(self.found, description="Pre-training @AnthropicAI")
        _, checks = panel.lookup_checks("12497", before, after)
        self.assertIn(("affiliation", "unknown"), self.kinds(checks))

    def test_an_unchanged_bio_changes_nothing_else(self):
        _, checks = panel.lookup_checks("12497", {"description": "Creator of Datasette"}, self.found)
        self.assertNotIn("affiliation", [c[0] for c in checks])

    def test_gone_or_suspended_is_a_failed_id_check(self):
        for status in ("not_found", "unavailable"):
            with self.subTest(status=status):
                _, checks = panel.lookup_checks("12497", None, {"status": status})
                self.assertEqual(self.kinds(checks), [("platform_id", "fail")])

    def test_unresolved_records_nothing(self):
        self.assertEqual(panel.lookup_checks("12497", None, {"status": "unresolved"}), (None, []))

    def test_a_pending_affiliation_review_suspends_an_enabled_account(self):
        checks = [check("platform_id", "pass", 1), check("affiliation", "pass", 10),
                  check("affiliation", "unknown", 0)]
        self.assertEqual(panel.derive_state(account(panel_state="enabled"), checks, NOW), "suspended")


class IdentityFromOwnProfile(unittest.TestCase):
    """rule:identity-from-profile: the account's own bio can establish who it is."""
    orgs = ["Wharton School", "Generative AI Labs"]

    def test_name_and_an_affiliation_in_the_bio_is_own_bio_evidence(self):
        profile = {"name": "Ethan Mollick", "description": "Professor at The Wharton School. Author of Co-Intelligence"}
        self.assertTrue(panel.profile_confirms_identity(profile, "Ethan Mollick", self.orgs))

    def test_a_matching_name_alone_is_not_enough(self):
        profile = {"name": "Ethan Mollick", "description": "Fan account. Not affiliated."}
        self.assertFalse(panel.profile_confirms_identity(profile, "Ethan Mollick", self.orgs))

    def test_an_affiliation_under_another_name_is_not_enough(self):
        profile = {"name": "AI News Daily", "description": "Wharton School updates"}
        self.assertFalse(panel.profile_confirms_identity(profile, "Ethan Mollick", self.orgs))

    def test_name_matching_ignores_case_accents_and_titles(self):
        profile = {"name": "Dr. Fei-Fei Li", "description": "Stanford HAI co-director"}
        self.assertTrue(panel.profile_confirms_identity(profile, "Fei-Fei Li", ["Stanford HAI"]))

    def test_an_organisation_account_needs_its_own_name(self):
        profile = {"name": "METR", "description": "Model Evaluation & Threat Research"}
        self.assertTrue(panel.profile_confirms_identity(profile, "METR", [], owner_kind="organization"))

    def test_a_person_with_no_recorded_affiliation_cannot_be_confirmed_by_name(self):
        profile = {"name": "Ethan Mollick", "description": "Professor at The Wharton School"}
        self.assertFalse(panel.profile_confirms_identity(profile, "Ethan Mollick", []))

if __name__ == "__main__":
    unittest.main()
