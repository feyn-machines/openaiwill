"""Account-agnostic fetch engine: page one target's timeline.

The engine is handed a `fetch_page(cursor) -> page` coroutine (bound by the
caller to one account's session/connection) and one target. It knows nothing
about which account, proxy, or IP it is using. It applies the single-job window
and identity rules and classifies failures so the scheduler can cool down, retire
or retry the account without the engine deciding policy.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta

from . import parser


class FetchError(Exception):
    """Base for classified fetch failures."""


class RateLimited(FetchError):
    """The account/IP hit a rate limit; cool it down and retry the job elsewhere."""


class AuthFailed(FetchError):
    """The account credential was rejected; retire it and retry the job elsewhere."""


class TransportError(FetchError):
    """A connection/proxy/HTTP failure not attributable to the account."""


# X GraphQL error codes (in the response `errors` array).
_RATE_LIMIT_CODES = {88, 130}
_AUTH_CODES = {32, 89, 215, 353}


def classify_page(page):
    """Raise a typed FetchError for a non-usable page; return None if it is OK.

    `page` carries http_status and the raw `data` (with an optional errors array).
    """
    status = page.get("http_status")
    codes = {e.get("code") for e in (page.get("data") or {}).get("errors", []) or []}
    if status == 429 or codes & _RATE_LIMIT_CODES:
        raise RateLimited(f"rate limited (http={status}, codes={sorted(c for c in codes if c)})")
    if status in (401, 403) or codes & _AUTH_CODES:
        raise AuthFailed(f"auth rejected (http={status}, codes={sorted(c for c in codes if c)})")
    if status != 200:
        raise TransportError(f"unexpected HTTP {status}")
    return None


async def crawl_target(target, fetch_page, *, max_pages=10, pace=3.0,
                       sleep=asyncio.sleep, on_page=None):
    """Page one user-timeline target to the window start.

    Returns a dict describing the outcome. Raises a FetchError (leaving the
    partial result attached to the exception as `.partial`) so the scheduler can
    apply account policy and requeue the job.
    """
    start = parser.parse_time(target["window_start"])
    end = parser.parse_time(target["window_end"])
    handle_lc = target["handle"].lower()
    author_id = target["author_id"]

    accepted, quarantine, requests = {}, [], []
    cursor, cursors_seen = None, set()
    status, stop_reason = "pending", None

    def result():
        return {
            "id": target["id"], "handle": target["handle"], "author_id": author_id,
            "company": target.get("company"),
            "window_start": target["window_start"], "window_end": target["window_end"],
            "posts": list(accepted.values()), "quarantine": quarantine,
            "requests": requests, "pages": len(requests),
            "accepted_count": len(accepted), "next_cursor": cursor,
            "status": status, "stop_reason": stop_reason,
        }

    for page_no in range(max_pages):
        record = {"page": page_no + 1, "cursor_in": cursor, "cursor_out": None,
                  "http_status": None, "returned": 0, "accepted": 0}
        requests.append(record)
        try:
            page = await fetch_page(cursor)
        except FetchError as exc:
            status, stop_reason = "error", type(exc).__name__
            exc.partial = result()
            raise
        record["http_status"] = page.get("http_status")
        for key in ("raw_file", "raw_sha256"):
            if key in page:
                record[key] = page[key]
        try:
            classify_page(page)
            posts, next_cursor = parser.parse_user_timeline_page(page["data"])
        except FetchError as exc:
            status, stop_reason = "error", type(exc).__name__
            exc.partial = result()
            raise
        except ValueError as exc:
            status, stop_reason = "error", "parse_error"
            err = TransportError(str(exc))
            err.partial = result()
            raise err from exc

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
        if pace:
            await sleep(pace)

    if status == "pending":
        status, stop_reason = "incomplete", "page_budget"
    return result()
