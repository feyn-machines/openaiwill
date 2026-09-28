"""X handle lookup job: resolve a handle to its user id and public profile.

The panel uses the id to plan timeline jobs and the bio to notice an
affiliation change. It runs on the shared scheduler, so it has the same account
policy as timelines (core/scheduler.py). A worker keeps its account and
connection between handles (`sticky`), because each lookup is one request.

A handle that no account could answer is `unresolved`, never `not_found`:
failing to ask is not evidence that the account does not exist.

Network access lives in x/client.py; this module is pure policy and parsing so
it can be tested without twikit.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from ..core import errors, scheduler

VERSION = "lookup-1"
DONE = {"found", "not_found", "unavailable"}


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


def unfinished(job, js):
    return {"status": "unresolved", "handle": job["handle"],
            "reason": js["stop_reason"], "account_label": js.get("account_label")}


def jobs_for(handles):
    return [{"id": h, "handle": h} for h in dict.fromkeys(h.strip().lstrip("@") for h in handles if h.strip())]


async def run(handles, pool, session_factory, *, pace=3.0, concurrency=1,
              sleep=asyncio.sleep, on_result=lambda handle, record: None, **options):
    """Look up every handle through the shared scheduler. Returns (state, {handle: record}).

    session_factory(lease) -> session with async lookup(handle) -> (status, data).
    """
    async def work(job, session, on_request):
        status, data = await session.lookup(job["handle"])
        on_request({})
        errors.classify_page({"http_status": status, "data": data})
        try:
            record = parse_user(data, job["handle"])
        except ValueError as exc:  # X answered for another account: not an answer
            record = {"status": "unresolved", "handle": job["handle"], "reason": f"identity: {exc}"}
        record.update(getattr(session, "last_raw", None) or {})
        on_result(job["handle"], record)
        if pace:
            await sleep(pace)
        return record

    async def factory(lease, job):
        return await session_factory(lease)

    def settle(job, js):
        record = unfinished(job, js)
        on_result(job["handle"], record)
        return record

    state, results = await scheduler.run_jobs(
        jobs_for(handles), pool, factory, work, settle, done_statuses=DONE,
        concurrency=concurrency, sticky=True, sleep=sleep, **options)
    for job_id, record in results.items():
        record.setdefault("account_label", state["jobs"][job_id]["account_label"])
    return state, results


async def run_lookups(handles, pool, session_factory, **options):
    """Like run(), returning only {handle: record}."""
    return (await run(handles, pool, session_factory, **options))[1]


def assemble_output(results, started, pool_health, state=None):
    counts = {}
    for r in results.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"version": VERSION, "started_at": started.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "ok": counts.get("unresolved", 0) == 0, "counts": counts,
            "pool_health": pool_health,
            "failovers": (state or {}).get("failovers", []),
            "schema_change": (state or {}).get("schema_change"),
            "results": results}
