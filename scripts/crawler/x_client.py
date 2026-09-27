"""Per-account X session over Qingguo — the one network-touching module.

Each account gets its own twikit Client bound to a single proxy connection, so
its exit IP stays stable for the whole crawl (verified 2026-09-14). A token-only
account (auth_token but no ct0) gets a synthesized 32-hex ct0; twikit sends it as
both the ct0 cookie and the x-csrf-token header, which X accepts for read
endpoints. Importing this module installs the twikit compatibility patches.

Raw response JSON is persisted per page (never headers, cookies, proxy or
request objects), and each page's SHA-256 is recorded.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

import httpx
from twikit import Client
from twikit import errors as twikit_errors

from . import x_compat  # noqa: F401  installs get_indices + search patches
from . import proxy as proxy_mod
from . import engine


def synthesize_ct0():
    return secrets.token_hex(16)  # 32 hex chars


def _write_page(pages_dir, index, data):
    path = Path(pages_dir) / f"{index:05d}.json"
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    path.write_bytes(payload)
    os.chmod(path, 0o600)
    return str(path), hashlib.sha256(payload).hexdigest()


class XSession:
    """One account's session. Provides fetch_page(cursor) for a user timeline."""

    def __init__(self, lease, target, proxy_url, pages_dir, count=40):
        self._lease = lease
        self._target = target
        self._proxy_url = proxy_url
        self._pages_dir = pages_dir
        self._count = count
        self._index = 0
        ctx = proxy_mod.proxy_ssl_context(proxy_url)
        # One connection per account => one stable exit IP for the whole crawl.
        limits = httpx.Limits(max_connections=1, max_keepalive_connections=1)
        self._client = Client(
            proxy=httpx.Proxy(proxy_url, ssl_context=ctx),
            timeout=30, trust_env=False, limits=limits)
        ct0 = lease.ct0 or synthesize_ct0()
        self._client.set_cookies({"ct0": ct0, "auth_token": lease.auth_token})

    async def fetch_page(self, cursor):
        # Translate network/twikit failures into the engine's typed taxonomy so
        # the scheduler can cool down / retire the account and fail the job over.
        # A ConnectError here is usually a bad proxy exit IP; a fresh connection
        # (new IP) on retry typically succeeds.
        try:
            data, response = await self._client.gql.user_tweets(
                self._target["author_id"], self._count, cursor)
        except twikit_errors.TooManyRequests as exc:
            raise engine.RateLimited(str(exc) or "twikit TooManyRequests") from exc
        except (twikit_errors.Unauthorized, twikit_errors.Forbidden,
                twikit_errors.AccountLocked, twikit_errors.AccountSuspended) as exc:
            raise engine.AuthFailed(f"{type(exc).__name__}: {exc}") from exc
        except httpx.HTTPError as exc:
            raise engine.TransportError(f"{type(exc).__name__}") from exc
        except twikit_errors.TwitterException as exc:
            raise engine.TransportError(f"twikit:{type(exc).__name__}") from exc
        self._index += 1
        raw_file, digest = _write_page(self._pages_dir, self._index, data)
        return {"http_status": response.status_code, "data": data,
                "raw_file": os.path.basename(raw_file), "raw_sha256": digest}

    async def close(self):
        await self._client.http.aclose()


class XLookupSession:
    """One account's session for handle -> user lookups (UserByScreenName).

    Same connection model as XSession: one proxy connection per account, so the
    exit IP is stable. Each raw response is written as <handle>.json with its
    SHA-256 kept on `last_raw` for the caller to record.
    """

    def __init__(self, lease, proxy_url, pages_dir):
        self._pages_dir = Path(pages_dir)
        self.last_raw = None
        ctx = proxy_mod.proxy_ssl_context(proxy_url)
        limits = httpx.Limits(max_connections=1, max_keepalive_connections=1)
        self._client = Client(
            proxy=httpx.Proxy(proxy_url, ssl_context=ctx),
            timeout=30, trust_env=False, limits=limits)
        self._client.set_cookies({"ct0": lease.ct0 or synthesize_ct0(), "auth_token": lease.auth_token})

    async def lookup(self, handle):
        try:
            data, response = await self._client.gql.user_by_screen_name(handle)
        except twikit_errors.TooManyRequests as exc:
            raise engine.RateLimited(str(exc) or "twikit TooManyRequests") from exc
        except (twikit_errors.Unauthorized, twikit_errors.Forbidden,
                twikit_errors.AccountLocked, twikit_errors.AccountSuspended) as exc:
            raise engine.AuthFailed(f"{type(exc).__name__}: {exc}") from exc
        except twikit_errors.NotFound as exc:
            # An unknown screen name comes back as 200 with an empty result and is
            # parsed as not_found. An HTTP 404 is the endpoint itself (the search
            # endpoint did this on 2026-09-23 while timelines stayed 200), so it
            # must never be read as "this account does not exist".
            raise ValueError(f"lookup endpoint returned 404: {exc}") from exc
        except httpx.HTTPError as exc:
            raise engine.TransportError(f"{type(exc).__name__}") from exc
        except twikit_errors.TwitterException as exc:
            raise engine.TransportError(f"twikit:{type(exc).__name__}") from exc
        path = self._pages_dir / f"{handle.lower()}.json"
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
        path.write_bytes(payload)
        os.chmod(path, 0o600)
        self.last_raw = {"raw_file": path.name, "raw_sha256": hashlib.sha256(payload).hexdigest()}
        return response.status_code, data

    async def close(self):
        await self._client.http.aclose()


def lookup_session_factory(proxy_url, pages_dir):
    async def make(lease):
        Path(pages_dir).mkdir(parents=True, exist_ok=True, mode=0o700)
        return XLookupSession(lease, proxy_url, pages_dir)
    return make


def session_factory(proxy_url, pages_root, count=40):
    """Build an async session_factory(lease, target) for the scheduler.

    The scheduler passes the leased account and the target it was assigned; each
    job's raw pages are written under pages_root/<job id>/.
    """
    async def make(lease, target):
        job_dir = Path(pages_root) / target["id"]
        job_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        return XSession(lease, target, proxy_url, job_dir, count=count)
    return make
