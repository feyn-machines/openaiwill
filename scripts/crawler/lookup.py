"""Handle -> user lookup over the account pool.

Resolves an X handle to its stable user id, and records the public profile
(name, bio, counts) at the same time: the panel uses the id to plan timeline
jobs and the bio to notice an affiliation change. It is the timeline crawler's
sibling and shares its account policy (see scheduler.py): a rate limit cools
the account and another one answers, a rejected credential retires it, a
transport error gets a fresh connection (a new exit IP) on the same account.

A handle that no account could answer is `unresolved`, never `not_found`:
failing to ask is not evidence that the account does not exist.

Network access lives in x_client.XLookupSession; this module is pure policy and
parsing so it can be tested without twikit.
"""
from __future__ import annotations

import asyncio

from . import engine


def _int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_user(data, handle):
    """One UserByScreenName response -> a flat, non-secret record.

    Raises ValueError when X answers with a different account than asked for:
    that is a routing or schema problem, not a fact about the handle.
    """
    result = (((data or {}).get("data") or {}).get("user") or {}).get("result")
    if not result:
        return {"status": "not_found", "handle": handle}
    if result.get("__typename") == "UserUnavailable":
        return {"status": "unavailable", "handle": handle, "reason": result.get("reason")}
    legacy = result.get("legacy") or {}
    core = result.get("core") or {}
    screen_name = core.get("screen_name") or legacy.get("screen_name")
    if not screen_name or screen_name.lower() != handle.lower().lstrip("@"):
        raise ValueError(f"asked for @{handle}, X answered @{screen_name}")
    return {
        "status": "found",
        "handle": handle,
        "user_id": str(result.get("rest_id")),
        "screen_name": screen_name,
        "name": core.get("name") or legacy.get("name"),
        "description": legacy.get("description"),
        "followers": _int(legacy.get("followers_count")),
        "following": _int(legacy.get("friends_count")),
        "posts": _int(legacy.get("statuses_count")),
        "created_at": core.get("created_at") or legacy.get("created_at"),
        "protected": (result.get("privacy") or {}).get("protected", legacy.get("protected")),
        "verified": result.get("is_blue_verified"),
    }


async def run_lookups(handles, pool, session_factory, *, pace=3.0, max_attempts=4,
                      cooldown_seconds=900, max_transient=6, sleep=asyncio.sleep,
                      on_result=lambda handle, record: None):
    """Look up each handle in turn on one leased account at a time."""
    results = {}
    lease, session = None, None

    async def drop():
        nonlocal session
        if session is not None:
            await session.close()
            session = None

    for handle in handles:
        tried, attempts, transient = set(), 0, 0
        while True:
            if lease is None:
                lease = pool.acquire(exclude=tried)
                if lease is None:
                    results[handle] = {"status": "unresolved", "handle": handle,
                                       "reason": "no account available"}
                    break
            if session is None:
                session = await session_factory(lease)
            try:
                status, data = await session.lookup(handle)
                engine.classify_page({"http_status": status, "data": data})
                record = parse_user(data, handle)
                record["account_label"] = lease.label
                record.update(getattr(session, "last_raw", None) or {})
                results[handle] = record
                break
            except engine.RateLimited as exc:
                pool.mark_cooldown(lease.label, cooldown_seconds)
                reason = f"rate limited: {exc}"
            except engine.AuthFailed as exc:
                pool.mark_dead(lease.label, str(exc))
                reason = f"auth failed: {exc}"
            except engine.TransportError as exc:
                transient += 1
                await drop()  # same account, fresh connection
                if transient > max_transient:
                    results[handle] = {"status": "unresolved", "handle": handle,
                                       "reason": f"transport: {exc}"}
                    break
                continue
            except ValueError as exc:
                results[handle] = {"status": "unresolved", "handle": handle, "reason": f"schema: {exc}"}
                break
            # Account-level failure: move to another account for this handle.
            tried.add(lease.label)
            await drop()
            lease = None
            attempts += 1
            if attempts >= max_attempts:
                results[handle] = {"status": "unresolved", "handle": handle, "reason": reason}
                break
        on_result(handle, results[handle])
        await sleep(pace)
    await drop()
    return results
