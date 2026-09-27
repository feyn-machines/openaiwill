"""Dynamic X account pool — lease, cooldown, failover, persistence.

Account data is project-local and lives at data/collection/x-accounts/pool.json
(ignored by Git). This module is account-independent code operating over that
data; it never logs or returns secrets — only the non-secret `label`.

Health states:
  unverified  never liveness-checked
  usable      lease-eligible
  cooldown    hit a rate limit; not leased until cooldown_until passes
  dead        auth failed / suspended; never leased
An `active` legacy status (the account migrated from env) is treated as usable.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

LEASABLE = {"usable", "unverified", "active"}


def _now():
    return datetime.now(timezone.utc)


class Lease:
    """A borrowed account: cookie pair for the engine plus a non-secret label."""

    __slots__ = ("label", "auth_token", "ct0")

    def __init__(self, label, auth_token, ct0):
        self.label = label
        self.auth_token = auth_token
        self.ct0 = ct0  # None => the engine synthesizes a ct0

    def cookies(self):
        return {"auth_token": self.auth_token, "ct0": self.ct0}

    def __repr__(self):  # never expose secrets
        return f"Lease(label={self.label!r}, ct0={'set' if self.ct0 else 'synthesize'})"


class AccountPool:
    """In-memory pool backed by a JSON file. Not thread-safe; drive from one
    asyncio loop. State changes persist immediately so an interrupted run leaves
    each account's latest health on disk."""

    def __init__(self, path, accounts, meta=None, clock=_now):
        self.path = Path(path) if path else None
        self.accounts = accounts
        self.meta = meta or {}
        self._clock = clock
        self._by_label = {a["label"]: a for a in accounts}

    @classmethod
    def load(cls, path, clock=_now):
        data = json.loads(Path(path).read_text())
        accounts = data.get("accounts", [])
        for a in accounts:
            a.setdefault("label", a.get("username"))
            a.setdefault("status", "unverified")
            a.setdefault("cooldown_until", None)
            a.setdefault("last_used_at", None)
            a.setdefault("ct0", None)
        meta = {k: v for k, v in data.items() if k != "accounts"}
        return cls(path, accounts, meta, clock)

    def _leasable(self, account):
        if account["status"] not in LEASABLE:
            return False
        if not account.get("auth_token"):
            return False
        until = account.get("cooldown_until")
        if until and self._clock() < datetime.fromisoformat(until):
            return False
        return True

    def available_count(self):
        return sum(1 for a in self.accounts if self._leasable(a))

    def has_leasable_untried(self, exclude=()):
        """Any not-excluded account that could ever be leased (ignoring current
        cooldown timing). Distinguishes 'wait for cooldown' from 'give up'."""
        for a in self.accounts:
            if a["label"] in exclude:
                continue
            if a["status"] in LEASABLE and a.get("auth_token"):
                return True
        return False

    def next_cooldown_seconds(self, exclude=()):
        """Seconds until the soonest cooling, not-excluded account is leasable."""
        now = self._clock()
        soonest = None
        for a in self.accounts:
            if a["label"] in exclude:
                continue
            if a["status"] not in LEASABLE or not a.get("auth_token"):
                continue
            until = a.get("cooldown_until")
            if not until:
                continue
            delta = (datetime.fromisoformat(until) - now).total_seconds()
            if delta > 0 and (soonest is None or delta < soonest):
                soonest = delta
        return soonest

    def acquire(self, exclude=()):
        """Lease the least-recently-used leasable account, or None if none free."""
        candidates = [a for a in self.accounts
                      if self._leasable(a) and a["label"] not in exclude]
        if not candidates:
            return None
        candidates.sort(key=lambda a: a.get("last_used_at") or "")
        account = candidates[0]
        account["last_used_at"] = self._clock().isoformat()
        self._persist()
        return Lease(account["label"], account["auth_token"], account.get("ct0"))

    def _set(self, label, **fields):
        account = self._by_label[label]
        account.update(fields)
        self._persist()

    def mark_usable(self, label):
        self._set(label, status="usable", cooldown_until=None)

    def mark_cooldown(self, label, seconds):
        until = datetime.fromtimestamp(self._clock().timestamp() + seconds, timezone.utc)
        self._set(label, status="usable", cooldown_until=until.isoformat())

    def mark_dead(self, label, reason=None):
        self._set(label, status="dead", dead_reason=reason)

    def health_summary(self):
        summary = {"usable": 0, "cooldown": 0, "dead": 0, "unverified": 0, "active": 0, "other": 0}
        now = self._clock()
        for a in self.accounts:
            status = a["status"]
            until = a.get("cooldown_until")
            if status in LEASABLE and until and now < datetime.fromisoformat(until):
                summary["cooldown"] += 1
            elif status in summary:
                summary[status] += 1
            else:
                summary["other"] += 1
        return summary

    def _persist(self):
        if not self.path:
            return
        payload = {**self.meta, "accounts": self.accounts,
                   "updated_at": self._clock().isoformat(), "count": len(self.accounts)}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)
