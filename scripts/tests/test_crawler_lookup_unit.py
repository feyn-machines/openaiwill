"""Offline tests for handle -> user lookup (no twikit, no network).

The lookup shares the timeline crawler's account policy: a rate limit cools the
account and moves on, a rejected credential retires it, a transport error gets a
fresh connection. What it must never do is turn a failed request into "this
account does not exist" - that would retire a real panel member.
"""
import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crawler import accounts, engine, lookup  # noqa: E402


def user_payload(rest_id="12497", handle="simonw", name="Simon Willison",
                 bio="Creator of Datasette", followers=100, schema="new"):
    legacy = {"description": bio, "followers_count": followers, "friends_count": 5,
              "statuses_count": 9, "created_at": "Wed Nov 07 00:00:00 +0000 2007"}
    result = {"__typename": "User", "rest_id": rest_id, "legacy": legacy}
    if schema == "new":
        result["core"] = {"screen_name": handle, "name": name}
    else:
        legacy.update({"screen_name": handle, "name": name})
    return {"data": {"user": {"result": result}}}


class ParseUser(unittest.TestCase):
    def test_found_in_the_current_schema(self):
        u = lookup.parse_user(user_payload(), "simonw")
        self.assertEqual((u["status"], u["user_id"], u["screen_name"]), ("found", "12497", "simonw"))
        self.assertEqual(u["description"], "Creator of Datasette")
        self.assertEqual(u["followers"], 100)

    def test_found_in_the_legacy_schema(self):
        u = lookup.parse_user(user_payload(schema="legacy"), "simonw")
        self.assertEqual((u["status"], u["screen_name"], u["name"]), ("found", "simonw", "Simon Willison"))

    def test_an_empty_answer_is_not_found(self):
        self.assertEqual(lookup.parse_user({"data": {}}, "gone")["status"], "not_found")

    def test_an_unavailable_user_says_why(self):
        data = {"data": {"user": {"result": {"__typename": "UserUnavailable", "reason": "Suspended"}}}}
        u = lookup.parse_user(data, "banned")
        self.assertEqual((u["status"], u["reason"]), ("unavailable", "Suspended"))

    def test_a_different_handle_in_the_answer_is_refused(self):
        with self.assertRaises(ValueError):
            lookup.parse_user(user_payload(handle="someone_else"), "simonw")

    def test_missing_counts_stay_missing(self):
        data = user_payload()
        del data["data"]["user"]["result"]["legacy"]["followers_count"]
        self.assertIsNone(lookup.parse_user(data, "simonw")["followers"])


class FakeSession:
    def __init__(self, script):
        self.script = script  # handle -> exception or payload
        self.closed = False

    async def lookup(self, handle):
        outcome = self.script[handle]
        if isinstance(outcome, Exception):
            raise outcome
        return 200, outcome

    async def close(self):
        self.closed = True


def pool(n):
    return accounts.AccountPool(None, [{"label": f"a{i}", "auth_token": "t", "ct0": None,
                                        "status": "usable"} for i in range(n)])


def run(handles, sessions, n_accounts=3):
    p = pool(n_accounts)
    made = iter(sessions)

    async def factory(lease):
        return next(made)

    async def nosleep(_):
        return None
    return asyncio.run(lookup.run_lookups(handles, p, factory, pace=0, sleep=nosleep)), p


class RunLookups(unittest.TestCase):
    def test_every_handle_gets_an_answer(self):
        s = FakeSession({"simonw": user_payload(), "gone": {"data": {}}})
        results, _ = run(["simonw", "gone"], [s])
        self.assertEqual(results["simonw"]["status"], "found")
        self.assertEqual(results["gone"]["status"], "not_found")
        self.assertTrue(s.closed)

    def test_a_rate_limit_cools_the_account_and_the_next_one_answers(self):
        first = FakeSession({"simonw": engine.RateLimited("429")})
        second = FakeSession({"simonw": user_payload()})
        results, p = run(["simonw"], [first, second])
        self.assertEqual(results["simonw"]["status"], "found")
        self.assertEqual(p.health_summary()["cooldown"], 1)

    def test_a_rejected_credential_retires_the_account(self):
        first = FakeSession({"simonw": engine.AuthFailed("401")})
        second = FakeSession({"simonw": user_payload()})
        results, p = run(["simonw"], [first, second])
        self.assertEqual(results["simonw"]["status"], "found")
        self.assertEqual(p.health_summary()["dead"], 1)

    def test_a_transport_error_retries_on_a_fresh_connection(self):
        flaky = FakeSession({"simonw": engine.TransportError("ConnectError")})
        fresh = FakeSession({"simonw": user_payload()})
        results, p = run(["simonw"], [flaky, fresh])
        self.assertEqual(results["simonw"]["status"], "found")
        self.assertEqual(p.health_summary()["dead"], 0)

    def test_an_endpoint_404_is_unresolved_not_missing(self):
        s = FakeSession({"simonw": ValueError("lookup endpoint returned 404")})
        results, _ = run(["simonw"], [s])
        self.assertEqual(results["simonw"]["status"], "unresolved")

    def test_when_no_account_can_answer_the_handle_is_unresolved_not_missing(self):
        """A failed request is never evidence that an account does not exist."""
        sessions = [FakeSession({"simonw": engine.RateLimited("429")}) for _ in range(3)]
        results, _ = run(["simonw"], sessions, n_accounts=3)
        self.assertEqual(results["simonw"]["status"], "unresolved")


if __name__ == "__main__":
    unittest.main()
