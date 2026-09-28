"""The failure taxonomy every source reports in, and the scheduler acts on.

A source never decides account policy. It raises one of these and the scheduler
cools the account down, retires it, retries on a fresh connection, or stops the
batch. Anything else a source raises (a ValueError from a parser on one odd
record) fails that job only, without a retry: the same bytes would come back.
"""
from __future__ import annotations


class FetchError(Exception):
    """Base for classified fetch failures."""


class RateLimited(FetchError):
    """The account hit a rate limit. Cool it down and fail the job over.

    `reset_at` is the provider's own reset time (epoch seconds) when it gave
    one; the scheduler prefers it to a fixed cooldown.
    """

    def __init__(self, message="rate limited", reset_at=None):
        super().__init__(message)
        self.reset_at = reset_at


class AuthFailed(FetchError):
    """The credential was rejected. Retire the account and fail the job over."""


class TransportError(FetchError):
    """A connection/proxy/server failure not attributable to the account.

    Retried on a fresh connection (a new exit IP) of the same account.
    """


class SchemaChanged(FetchError):
    """The endpoint is gone or answers in a shape we do not recognise.

    Retrying or failing over would spend every account on the same answer, so
    the scheduler stops the whole batch and leaves the raw page for diagnosis.
    """


# X GraphQL error codes (in the response `errors` array).
_RATE_LIMIT_CODES = {88, 130}
_AUTH_CODES = {32, 89, 215, 353}


def classify_page(page):
    """Raise a typed FetchError for a non-usable X page; return None if usable.

    `page` carries http_status and the raw `data` (with an optional errors array).
    """
    status = page.get("http_status")
    data = page.get("data") or {}
    codes = {e.get("code") for e in data.get("errors", []) or []}
    shown = sorted(c for c in codes if c)
    if status == 429 or codes & _RATE_LIMIT_CODES:
        raise RateLimited(f"rate limited (http={status}, codes={shown})",
                          reset_at=(page.get("rate_limit") or {}).get("reset"))
    if status in (401, 403) or codes & _AUTH_CODES:
        raise AuthFailed(f"auth rejected (http={status}, codes={shown})")
    if status == 404:
        raise SchemaChanged("endpoint returned HTTP 404")
    if status != 200:
        raise TransportError(f"unexpected HTTP {status}")
    if codes and not data.get("data"):
        raise TransportError(f"GraphQL errors without data (codes={shown})")
    return None
