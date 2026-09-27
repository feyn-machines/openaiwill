"""Account/window-isolated X collection policy, independent of credentials and HTTP.

Search exhaustion is an observable provider state, never a claim of full timelines.
The private social skill supplies authentication, transport and response parsing.
"""
from __future__ import annotations

import asyncio
import hashlib
import math
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

VERSION = "official-x-collection-1"


def parse_time(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Publication windows require an explicit timezone")
    return result.astimezone(timezone.utc)


def select_accounts(accounts, handles=None):
    enabled = [a for a in accounts if a.get("enabled") is True]
    requested = {h.lower().lstrip("@") for h in handles} if handles is not None else None
    if requested is not None:
        if not requested or requested - {a.get("handle", "").lower() for a in enabled}:
            raise ValueError("Requested accounts must already be enabled in the registry")
        enabled = [a for a in enabled if a.get("handle", "").lower() in requested]
    if not enabled:
        raise ValueError("No enabled official accounts")
    seen_handles, seen_ids = set(), set()
    for account in enabled:
        handle, user_id = account.get("handle", ""), account.get("x_user_id")
        if (not re.fullmatch(r"[A-Za-z0-9_]{1,15}", handle)
                or not isinstance(user_id, str) or not user_id.isdigit()
                or account.get("verification_status") != "confirmed"):
            raise ValueError("Enabled accounts require a confirmed handle and numeric X user ID")
        if handle.lower() in seen_handles or user_id in seen_ids:
            raise ValueError("Duplicate enabled account identity")
        seen_handles.add(handle.lower())
        seen_ids.add(user_id)
    return enabled


def plan_queries(accounts, start, end, handles=None):
    start, end = parse_time(start), parse_time(end)
    if start >= end:
        raise ValueError("Window start must precede end")
    enabled = select_accounts(accounts, handles)
    result = []
    current = start
    while current < end:
        midnight = current.replace(hour=0, minute=0, second=0, microsecond=0)
        following = min(midnight + timedelta(days=1), end)
        # Each query encloses one exact, nonoverlapping interval within a UTC day.
        query_end = midnight + timedelta(days=1)
        for account in enabled:
            handle = account["handle"]
            identity = f"{account['x_user_id']}|{current.isoformat()}|{following.isoformat()}"
            result.append({
                "id": hashlib.sha256(identity.encode()).hexdigest()[:24],
                "mode": "search",
                "handle": handle, "author_id": account["x_user_id"], "company": account.get("company"),
                "window_start": current.isoformat(), "window_end": following.isoformat(),
                "query": f"(from:{handle}) since:{midnight:%Y-%m-%d} until:{query_end:%Y-%m-%d}",
            })
        current = following
    return result


def plan_timelines(accounts, start, end, handles=None):
    start, end = parse_time(start), parse_time(end)
    if start >= end:
        raise ValueError("Window start must precede end")
    result = []
    for account in select_accounts(accounts, handles):
        identity = f"timeline|{account['x_user_id']}|{start.isoformat()}|{end.isoformat()}"
        result.append({
            "id": hashlib.sha256(identity.encode()).hexdigest()[:24],
            "mode": "user_timeline", "handle": account["handle"],
            "author_id": account["x_user_id"], "company": account.get("company"),
            "window_start": start.isoformat(), "window_end": end.isoformat(),
            "query": f"user_timeline:{account['x_user_id']}:Tweets",
        })
    return result


def extract_user_timeline_page(data, observed_at=None):
    """Parse raw UserTweets JSON without Twikit's fragile User constructor."""
    if not isinstance(data, dict) or data.get("errors"):
        raise ValueError("X user timeline returned errors")
    try:
        user = data["data"]["user"]["result"]
        timeline = (user.get("timeline_v2") or user.get("timeline"))["timeline"]
        instructions = timeline["instructions"]
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Unexpected X user timeline schema") from exc
    observed_at = observed_at or datetime.now(timezone.utc).isoformat()
    item_contents, cursor = [], None
    for instruction in instructions:
        if instruction.get("type") != "TimelineAddEntries":
            continue
        for entry in instruction.get("entries", []):
            content = entry.get("content", {})
            if content.get("cursorType") == "Bottom":
                cursor = content.get("value")
            if isinstance(content.get("itemContent"), dict):
                item_contents.append(content["itemContent"])
            for nested in content.get("items", []):
                item = nested.get("item", {})
                if isinstance(item.get("itemContent"), dict):
                    item_contents.append(item["itemContent"])
    posts = []
    seen = set()
    for content in item_contents:
        if "tweet_results" not in content:
            continue
        result = content.get("tweet_results", {}).get("result")
        if not isinstance(result, dict):
            raise ValueError("X user timeline tweet result is missing")
        result = result.get("tweet", result)
        legacy = result.get("legacy")
        post_id = result.get("rest_id") or (legacy or {}).get("id_str")
        if not post_id or not isinstance(legacy, dict):
            raise ValueError("X user timeline contains an unavailable post; raw page retained")
        user_result = result.get("core", {}).get("user_results", {}).get("result", {})
        user_result = user_result.get("result", user_result)
        user_legacy = user_result.get("legacy", {})
        handle = user_result.get("core", {}).get("screen_name") or user_legacy.get("screen_name")
        author_id = user_result.get("rest_id")
        created_at = legacy.get("created_at")
        if not isinstance(post_id, str) or not handle or not isinstance(author_id, str) or not created_at:
            raise ValueError("X user timeline post lacks identity or publication time")
        try:
            created_utc = parsedate_to_datetime(created_at).timestamp()
        except (TypeError, ValueError) as exc:
            raise ValueError("X user timeline post has invalid publication time") from exc
        note = result.get("note_tweet", {}).get("note_tweet_results", {}).get("result", {})
        view_value = (result.get("views") or {}).get("count")
        try:
            views = int(view_value) if view_value is not None else None
        except (TypeError, ValueError) as exc:
            raise ValueError("X user timeline post has invalid view count") from exc
        if post_id in seen:
            continue
        seen.add(post_id)
        posts.append({
            "id": post_id, "source_type": "x", "author": handle,
            "author_id": author_id, "url": f"https://x.com/{handle}/status/{post_id}",
            "created_at": created_at, "created_utc": created_utc,
            "text": note.get("text") or legacy.get("full_text") or "",
            "text_source": "note_tweet" if note.get("text") else "legacy.full_text",
            "is_reply": bool(legacy.get("in_reply_to_status_id_str")),
            "is_repost": bool(legacy.get("retweeted_status_result")),
            "quoted_post_id": legacy.get("quoted_status_id_str"),
            "metrics": {
                **{name: int(legacy[field]) if legacy.get(field) is not None else None
                   for name, field in (("likes", "favorite_count"), ("reposts", "retweet_count"),
                                       ("replies", "reply_count"), ("quotes", "quote_count"),
                                       ("bookmarks", "bookmark_count"))},
                "views": views,
            },
            "metrics_observed_at": observed_at, "metrics_updated_at": None,
        })
    if cursor is not None and not isinstance(cursor, str):
        raise ValueError("X user timeline cursor is invalid")
    return posts, cursor


async def collect(jobs, fetch_page, *, max_pages=10, max_requests=500, pace=3,
                  timeout=1800, expected_posts=(), save=lambda state: None,
                  describe_error=lambda exc: {"type": type(exc).__name__}):
    """Run pages fairly; each cursor belongs to exactly one account/window query.

    fetch_page(query, cursor) returns posts, next_cursor, http_status and optional
    raw_file/raw_sha256. No retries or account switching occur after an error.
    """
    if (not jobs or max_pages < 1 or max_requests < 1 or not math.isfinite(pace)
            or pace < 0 or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError("Invalid collection plan or budgets")
    expected_posts = list(dict.fromkeys(expected_posts))
    if any(not isinstance(p, str) or not p.isdigit() for p in expected_posts):
        raise ValueError("Expected posts must be numeric X post IDs")
    if len({j["id"] for j in jobs}) != len(jobs):
        raise ValueError("Duplicate query identity")
    state = {
        "version": VERSION, "source": "x", "synthetic": False, "ok": False,
        "status": "running", "coverage_status": "partial_search",
        "coverage_note": "Coverage describes provider-visible account timelines or bounded search; website reconciliation remains separate.",
        "started_at": datetime.now(timezone.utc).isoformat(), "finished_at": None,
        "budgets": {"max_pages_per_query": max_pages, "max_requests": max_requests, "pace_seconds": pace, "timeout_seconds": timeout},
        "queries": [{**j, "status": "pending", "stop_reason": None, "pages": 0,
                     "next_cursor": None, "returned_count": 0, "accepted_count": 0} for j in jobs],
        "posts": [], "requests": [], "quarantine": [], "errors": [],
        "reconciliation": {"status": "pending" if expected_posts else "not_configured",
                           "expected_post_ids": expected_posts, "missing_post_ids": expected_posts[:]},
    }
    seen, cursors = {}, {j["id"]: set() for j in jobs}
    deadline = time.monotonic() + timeout
    stopped = False

    def persist():
        state["posts"] = list(seen.values())
        state["total"] = len(seen)
        save(state)

    persist()
    try:
        # A busy account cannot consume the entire budget before other first pages.
        for _ in range(max_pages):
            for job in state["queries"]:
                if job["status"] not in {"pending", "running"}:
                    continue
                if len(state["requests"]) >= max_requests:
                    stopped = True
                    break
                job["status"] = "running"
                cursor = job["next_cursor"]
                record = {"query_id": job["id"], "query": job["query"], "page": job["pages"] + 1,
                          "cursor_in": cursor, "cursor_out": None, "http_status": None,
                          "returned_post_ids": [], "accepted_post_ids": [],
                          "requested_at": datetime.now(timezone.utc).isoformat()}
                state["requests"].append(record)
                try:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError("Collection time budget exhausted")
                    response = await asyncio.wait_for(fetch_page(job["query"], cursor), timeout=remaining)
                    record["http_status"] = response["http_status"]
                    if response["http_status"] != 200:
                        raise RuntimeError(f"X returned HTTP {response['http_status']}")
                    posts, next_cursor = response["posts"], response["next_cursor"]
                    if not isinstance(posts, list) or (next_cursor is not None and not isinstance(next_cursor, str)):
                        raise ValueError("Invalid page structure")
                    record.update({k: response[k] for k in ("raw_file", "raw_sha256") if k in response})
                    record["cursor_out"] = next_cursor
                    job["next_cursor"] = next_cursor
                    job["pages"] += 1
                    job["returned_count"] += len(posts)
                    if cursor is not None:
                        cursors[job["id"]].add(cursor)
                    start, end = parse_time(job["window_start"]), parse_time(job["window_end"])
                    timeline_times = []
                    for post in posts:
                        post_id = post.get("id")
                        published = post.get("created_utc")
                        if (not isinstance(post_id, str) or not post_id.isdigit()
                                or not isinstance(published, (float, int)) or isinstance(published, bool)
                                or not math.isfinite(published)):
                            raise ValueError("X post lacks a valid ID or publication timestamp")
                        timeline_times.append(published)
                        record["returned_post_ids"].append(post_id)
                        reason = None
                        if post.get("author", "").lower() != job["handle"].lower() or post.get("author_id") != job["author_id"]:
                            reason = "author_identity_mismatch"
                        elif not start.timestamp() <= published < end.timestamp():
                            if job.get("mode") == "user_timeline":
                                continue
                            day_start = start.replace(hour=0, minute=0, second=0, microsecond=0)
                            reason = "outside_exact_window" if day_start.timestamp() <= published < (day_start + timedelta(days=1)).timestamp() else "outside_query_window"
                        if reason:
                            state["quarantine"].append({"query_id": job["id"], "post_id": post_id,
                                                       "reason": reason, "post": post})
                            continue
                        seen[post_id] = post
                        record["accepted_post_ids"].append(post_id)
                        job["accepted_count"] += 1
                    reached_start = (job.get("mode") == "user_timeline" and timeline_times
                                     and max(timeline_times) < start.timestamp())
                    if reached_start:
                        job.update(status="search_ended", stop_reason="window_start_reached")
                    elif not posts and next_cursor:
                        job.update(status="incomplete", stop_reason="empty_page_with_cursor")
                    elif not next_cursor:
                        job.update(status="search_ended", stop_reason="empty_page" if not posts else "no_cursor")
                    elif next_cursor in cursors[job["id"]]:
                        job.update(status="incomplete", stop_reason="cursor_cycle")
                    elif job["pages"] >= max_pages:
                        job.update(status="incomplete", stop_reason="page_budget")
                    persist()
                except Exception as exc:
                    job.update(status="error", stop_reason="timeout" if isinstance(exc, TimeoutError) else "request_error")
                    error = {"query_id": job["id"], **describe_error(exc)}
                    state["errors"].append(error)
                    record["error"] = error
                    stopped = True
                    persist()
                    break
                if pace:
                    remaining = deadline - time.monotonic()
                    await asyncio.sleep(min(pace, max(0, remaining)))
            if stopped or all(j["status"] not in {"pending", "running"} for j in state["queries"]):
                break
    finally:
        for job in state["queries"]:
            if job["status"] in {"pending", "running"}:
                reason = "interrupted" if state["errors"] else "request_budget"
                job.update(status="incomplete", stop_reason=reason)
        missing = [post_id for post_id in expected_posts if post_id not in seen]
        state["reconciliation"].update(missing_post_ids=missing,
            status=("missing" if missing else "passed") if expected_posts else "not_configured")
        provider_gaps = any(p["reason"] in {"author_identity_mismatch", "outside_query_window"} for p in state["quarantine"])
        state["ok"] = not missing and not provider_gaps and not state["errors"] and all(j["status"] == "search_ended" for j in state["queries"])
        state["status"] = "queries_exhausted" if state["ok"] else "needs_attention"
        state["finished_at"] = datetime.now(timezone.utc).isoformat()
        persist()
    return state
