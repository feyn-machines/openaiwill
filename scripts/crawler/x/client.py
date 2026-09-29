"""Per-account X session over Qingguo — the one network-touching module.

Each account gets its own twikit Client bound to a single proxy connection, so
its exit IP stays stable for the whole session (verified 2026-09-14). A
token-only account (auth_token but no ct0) gets a synthesized 32-hex ct0;
twikit sends it as both the ct0 cookie and the x-csrf-token header, which X
accepts for read endpoints. Importing this module installs the twikit
compatibility patches.

Raw response JSON is persisted per request (never headers, cookies, proxy or
request objects) with its SHA-256. The non-secret rate-limit headers are
returned beside it so the scheduler can rest an account before X answers 429.
"""
from __future__ import annotations

import secrets
from pathlib import Path

import httpx
from twikit import Client
from twikit import errors as twikit_errors

from . import compat  # noqa: F401  installs get_indices + search patches
from ..core import archive, errors, proxy as proxy_mod


def synthesize_ct0():
    return secrets.token_hex(16)  # 32 hex chars


def rate_limit(response):
    """The non-secret x-rate-limit-* headers as ints (None when absent)."""
    def number(name):
        try:
            return int(response.headers.get(name))
        except (TypeError, ValueError):
            return None
    return {"limit": number("x-rate-limit-limit"), "remaining": number("x-rate-limit-remaining"),
            "reset": number("x-rate-limit-reset")}


class _Session:
    """One account, one proxy connection, one stable exit IP."""

    def __init__(self, lease, proxy_url, pages_dir):
        self._pages_dir = Path(pages_dir)
        # A TLS context applies only to an https:// proxy entry; httpx refuses one for http.
        ctx = (proxy_mod.proxy_ssl_context(proxy_url)
               if proxy_mod.transport(proxy_url) == "https" else None)
        limits = httpx.Limits(max_connections=1, max_keepalive_connections=1)
        self._client = Client(
            proxy=httpx.Proxy(proxy_url, ssl_context=ctx),
            timeout=30, trust_env=False, limits=limits)
        self._client.set_cookies({"ct0": lease.ct0 or synthesize_ct0(), "auth_token": lease.auth_token})

    async def _call(self, request):
        """Run one GraphQL call, translating failures into the core taxonomy."""
        try:
            return await request()
        except twikit_errors.TooManyRequests as exc:
            raise errors.RateLimited(str(exc) or "twikit TooManyRequests",
                                     reset_at=getattr(exc, "rate_limit_reset", None)) from exc
        except (twikit_errors.Unauthorized, twikit_errors.Forbidden,
                twikit_errors.AccountLocked, twikit_errors.AccountSuspended) as exc:
            raise errors.AuthFailed(f"{type(exc).__name__}: {exc}") from exc
        except twikit_errors.NotFound as exc:
            # An HTTP 404 is the endpoint itself (the search endpoint did this on
            # 2026-09-23 while timelines stayed 200), never a fact about an account.
            raise errors.SchemaChanged(f"endpoint returned 404: {exc}") from exc
        except httpx.HTTPError as exc:
            raise errors.TransportError(type(exc).__name__) from exc
        except twikit_errors.TwitterException as exc:
            raise errors.TransportError(f"twikit:{type(exc).__name__}") from exc

    async def close(self):
        await self._client.http.aclose()


class TimelineSession(_Session):
    """Provides fetch_page(cursor) for one user timeline."""

    def __init__(self, lease, target, proxy_url, pages_dir, count=40):
        super().__init__(lease, proxy_url, pages_dir)
        self._target = target
        self._count = count
        self._index = 0

    async def fetch_page(self, cursor):
        data, response = await self._call(lambda: self._client.gql.user_tweets(
            self._target["author_id"], self._count, cursor))
        self._index += 1
        raw_file, digest = archive.write_raw(self._pages_dir, f"{self._index:05d}.json", data)
        return {"http_status": response.status_code, "data": data, "raw_file": raw_file,
                "raw_sha256": digest, "rate_limit": rate_limit(response)}


class LookupSession(_Session):
    """Provides lookup(handle) -> (status, data) for UserByScreenName."""

    def __init__(self, lease, proxy_url, pages_dir):
        super().__init__(lease, proxy_url, pages_dir)
        self.last_raw = None

    async def lookup(self, handle):
        data, response = await self._call(lambda: self._client.gql.user_by_screen_name(handle))
        raw_file, digest = archive.write_raw(self._pages_dir, f"{handle.lower()}.json", data)
        self.last_raw = {"raw_file": raw_file, "raw_sha256": digest}
        return response.status_code, data


def timeline_session_factory(proxy_url, pages_root, count=40):
    """session_factory(lease, target) for timeline jobs; raw pages go to pages_root/<job id>/."""
    async def make(lease, target):
        job_dir = Path(pages_root) / target["id"]
        job_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        return TimelineSession(lease, target, proxy_url, job_dir, count=count)
    return make


def lookup_session_factory(proxy_url, pages_dir):
    """session_factory(lease) for lookups; raw responses go to pages_dir/<handle>.json."""
    async def make(lease):
        Path(pages_dir).mkdir(parents=True, exist_ok=True, mode=0o700)
        return LookupSession(lease, proxy_url, pages_dir)
    return make
