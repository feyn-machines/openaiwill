"""X user-timeline job: page one account's timeline back to the window start.

The engine is handed a `fetch_page(cursor) -> page` coroutine (bound by the
scheduler to one account's connection) and one target. It applies the window
and identity rules and raises the core failure taxonomy; the scheduler decides
account policy.

The run document keeps the earlier guarantees: raw pages are retained with
SHA-256, `--expect-post` reconciles known announcements, and coverage means
only 'provider-visible timelines paged past the window start' — website
reconciliation stays separate. An account error that was failed over does not
fail the run.
"""
from __future__ import annotations

import asyncio

from ..core import errors, scheduler
from . import parse

VERSION = "crawler-run-1"
DONE = {"search_ended"}
COVERAGE_NOTE = ("Coverage describes provider-visible account timelines paged "
                 "past the window start; website reconciliation remains separate.")


async def crawl_target(target, fetch_page, *, max_pages=10, pace=3.0,
                       sleep=asyncio.sleep, on_page=None):
    """Page one user-timeline target to the window start. Returns its result.

    Raises a FetchError (with the partial result attached as `.partial`) so the
    scheduler can apply account policy. If the account's rate budget is spent
    while pages remain, it raises RateLimited before X has to answer 429.
    """
    start = parse.parse_time(target["window_start"])
    end = parse.parse_time(target["window_end"])
    handle_lc = target["handle"].lower()
    author_id = target["author_id"]

    accepted, quarantine, requests = {}, [], []
    cursor, cursors_seen, rate_limit = None, set(), None
    status, stop_reason = "pending", None

    def result():
        return {
            "id": target["id"], "handle": target["handle"], "author_id": author_id,
            "company": target.get("company"),
            "window_start": target["window_start"], "window_end": target["window_end"],
            "posts": list(accepted.values()), "quarantine": quarantine,
            "requests": requests, "pages": len(requests),
            "accepted_count": len(accepted), "next_cursor": cursor,
            "status": status, "stop_reason": stop_reason, "rate_limit": rate_limit,
        }

    def refuse(exc, reason):
        nonlocal status, stop_reason
        status, stop_reason = "error", reason
        exc.partial = result()
        return exc

    for page_no in range(max_pages):
        record = {"page": page_no + 1, "cursor_in": cursor, "cursor_out": None,
                  "http_status": None, "returned": 0, "accepted": 0}
        requests.append(record)
        try:
            page = await fetch_page(cursor)
        except errors.FetchError as exc:
            raise refuse(exc, type(exc).__name__)
        record["http_status"] = page.get("http_status")
        for key in ("raw_file", "raw_sha256", "rate_limit"):
            if page.get(key) is not None:
                record[key] = page[key]
        rate_limit = page.get("rate_limit") or rate_limit
        try:
            errors.classify_page(page)
            posts, next_cursor = parse.parse_user_timeline_page(page["data"])
        except errors.FetchError as exc:
            raise refuse(exc, type(exc).__name__)
        except ValueError as exc:
            raise refuse(exc, "parse_error")

        record["cursor_out"] = next_cursor
        record["returned"] = len(posts)
        if cursor is not None:
            cursors_seen.add(cursor)

        times = []
        for post in posts:
            times.append(post["created_utc"])
            if post["author"].lower() != handle_lc or post["author_id"] != author_id:
                quarantine.append({"post_id": post["id"], "reason": "author_identity_mismatch", "post": post})
                continue
            if not (start.timestamp() <= post["created_utc"] < end.timestamp()):
                continue  # user-timeline posts outside the window are simply skipped
            accepted[post["id"]] = post
            record["accepted"] += 1

        if on_page is not None:
            on_page(result())

        # Stop conditions for a single user-timeline job.
        if times and max(times) < start.timestamp():
            status, stop_reason = "search_ended", "window_start_reached"
            break
        if not next_cursor:
            status, stop_reason = "search_ended", "empty_page" if not posts else "no_cursor"
            break
        if not posts:
            status, stop_reason = "incomplete", "empty_page_with_cursor"
            break
        if next_cursor in cursors_seen:
            status, stop_reason = "incomplete", "cursor_cycle"
            break
        cursor = next_cursor
        if page_no + 1 >= max_pages:
            status, stop_reason = "incomplete", "page_budget"
            break
        if rate_limit and rate_limit.get("remaining") is not None and rate_limit["remaining"] <= 0:
            raise refuse(errors.RateLimited("rate budget spent before the window start",
                                            reset_at=rate_limit.get("reset")), "RateLimited")
        if pace:
            await sleep(pace)

    if status == "pending":
        status, stop_reason = "incomplete", "page_budget"
    return result()


def unfinished(target, js):
    """The result recorded for a job that never finished."""
    return {"id": target["id"], "handle": target["handle"], "author_id": target.get("author_id"),
            "company": target.get("company"),
            "window_start": target.get("window_start"), "window_end": target.get("window_end"),
            "posts": [], "quarantine": [], "requests": [], "pages": js["pages"],
            "accepted_count": 0, "status": js["status"], "stop_reason": js["stop_reason"],
            "next_cursor": None}


async def run(jobs, pool, session_factory, *, max_pages=10, pace=3.0, sleep=asyncio.sleep,
              **options):
    """Crawl every timeline job through the shared scheduler. Returns (state, results)."""
    async def work(target, session, on_request):
        return await crawl_target(target, session.fetch_page, max_pages=max_pages,
                                  pace=pace, sleep=sleep, on_page=on_request)

    return await scheduler.run_jobs(
        jobs, pool, session_factory, work, unfinished, done_statuses=DONE,
        budgets={"max_pages": max_pages, "pace_seconds": pace}, sleep=sleep, **options)


def assemble_output(state, results, meta, expected_posts):
    """Build the final run document. Pure: no network, no secrets."""
    jobs = []
    all_ids = set()
    for job_id, js in state["jobs"].items():
        result = results.get(job_id, {})
        for post in result.get("posts", []):
            all_ids.add(post["id"])
        jobs.append({
            "id": job_id, "handle": js["handle"], "company": js.get("company"),
            "status": js["status"], "stop_reason": js["stop_reason"],
            "pages": js["pages"], "accepted_count": js["accepted_count"],
            "attempts": js["attempts"], "account_label": js["account_label"],
            "window_start": result.get("window_start"), "window_end": result.get("window_end"),
            "posts": result.get("posts", []), "quarantine": result.get("quarantine", []),
            "requests": result.get("requests", []), "next_cursor": result.get("next_cursor"),
        })
    expected = list(dict.fromkeys(expected_posts or []))
    missing = [pid for pid in expected if pid not in all_ids]
    reconciliation = {
        "status": ("missing" if missing else "passed") if expected else "not_configured",
        "expected_post_ids": expected, "missing_post_ids": missing,
    }
    account_usage = {
        "jobs": [{"handle": j["handle"], "account_label": j["account_label"],
                  "pages": j["pages"], "attempts": j["attempts"], "status": j["status"]}
                 for j in jobs],
        "failovers": state["failovers"],
        "pool_final": state["pool"],
    }
    ok = state["ok"] and not missing
    return {
        "version": VERSION, "source": "x", "synthetic": False, "ok": ok,
        "status": "queries_exhausted" if ok else "needs_attention",
        "coverage_status": "provider_timelines", "coverage_note": COVERAGE_NOTE,
        "started_at": state["started_at"], "finished_at": state["finished_at"],
        "concurrency": state["concurrency"], "budgets": state["budgets"],
        "publication_window": meta.get("publication_window"),
        "total": len(all_ids), "requests": state["requests"],
        "schema_change": state.get("schema_change"),
        "jobs": jobs, "reconciliation": reconciliation, "account_usage": account_usage,
        "registry_sha256": meta.get("registry_sha256"),
        "implementation_sha256": meta.get("implementation_sha256"),
    }
