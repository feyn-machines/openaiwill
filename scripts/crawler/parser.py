"""Pure X response parsing and job planning — no twikit, no network.

Extracted from the former official_x_collection module. Parsing raw UserTweets
JSON directly (instead of Twikit's User constructor) keeps optional fields robust
and keeps this logic unit-testable offline.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

VERSION = "crawler-1"


def parse_time(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Publication windows require an explicit timezone")
    return result.astimezone(timezone.utc)


def select_accounts(accounts, handles=None):
    """Enabled, confirmed monitored accounts with valid, unique handle+user id."""
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


def plan_timelines(accounts, start, end, handles=None):
    """One independent user-timeline job per monitored account for [start, end)."""
    start, end = parse_time(start), parse_time(end)
    if start >= end:
        raise ValueError("Window start must precede end")
    result = []
    for account in select_accounts(accounts, handles):
        identity = f"timeline|{account['x_user_id']}|{start.isoformat()}|{end.isoformat()}"
        result.append({
            "id": hashlib.sha256(identity.encode()).hexdigest()[:24],
            "mode": "user_timeline",
            "handle": account["handle"],
            "author_id": account["x_user_id"],
            "company": account.get("company"),
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "query": f"user_timeline:{account['x_user_id']}:Tweets",
        })
    return result


def _reposted_id(legacy):
    """The id of the post a repost carries, in either result shape; None if not a repost."""
    result = (legacy.get("retweeted_status_result") or {}).get("result") or {}
    result = result.get("tweet", result)
    return result.get("rest_id") or (result.get("legacy") or {}).get("id_str")


def parse_user_timeline_page(data, observed_at=None):
    """Parse raw UserTweets JSON without Twikit's fragile User constructor.

    Returns (posts, next_cursor). Raises ValueError on unexpected schema or an
    unavailable post so the caller retains the raw page and stops that job
    rather than silently recording a gap as zero updates.
    """
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
            # Upstream links, so a post can be tied to the post it answers,
            # quotes or reposts - and through it to that post's event.
            "reply_to_post_id": legacy.get("in_reply_to_status_id_str"),
            "reply_to_user_id": legacy.get("in_reply_to_user_id_str"),
            "repost_of_post_id": _reposted_id(legacy),
            "conversation_id": legacy.get("conversation_id_str"),
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
