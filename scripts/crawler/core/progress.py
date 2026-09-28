"""Human-readable progress for a long, concurrent run.

Pure rendering over scheduler state, so it is unit-testable: feed a state dict,
assert the string. The CLI decides TTY (in-place multi-line block) vs non-TTY
(throttled single summary line plus milestone lines).
"""
from __future__ import annotations

from datetime import datetime, timezone


def _elapsed(state, now=None):
    now = now or datetime.now(timezone.utc)
    started = datetime.fromisoformat(state["started_at"])
    return max(0.0, (now - started).total_seconds())


def _fmt_dur(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"


def eta_seconds(state, now=None):
    jobs = state["jobs"].values()
    total = len(jobs)
    done = sum(1 for j in jobs if j["status"] != "pending")
    if done == 0 or done >= total:
        return None
    elapsed = _elapsed(state, now)
    rate = done / elapsed if elapsed > 0 else 0
    if rate <= 0:
        return None
    return (total - done) / rate


def summary_line(state, now=None):
    jobs = state["jobs"].values()
    total = len(jobs)
    done = sum(1 for j in jobs if j["status"] != "pending")
    eta = eta_seconds(state, now)
    eta_str = f"ETA ~{_fmt_dur(eta)}" if eta is not None else "ETA —"
    return (f"jobs {done}/{total} · {state['posts']} posts · "
            f"{state['requests']} reqs · {_fmt_dur(_elapsed(state, now))} · {eta_str}")


def block(state, now=None):
    """Multi-line status block for a TTY."""
    lines = [summary_line(state, now)]
    pool = state.get("pool", {})
    lines.append(f"  accounts  usable {pool.get('usable', 0)} · "
                 f"cooldown {pool.get('cooldown', 0)} · dead {pool.get('dead', 0)} · "
                 f"unverified {pool.get('unverified', 0)}")
    active = [(wid, w) for wid, w in sorted(state.get("workers", {}).items())
              if w.get("phase") in ("crawling", "waiting_cooldown")]
    for wid, w in active:
        if w["phase"] == "crawling":
            lines.append(f"  w{wid}  @{w['handle']} p{w['page']} ({w['label']})")
        else:
            lines.append(f"  w{wid}  waiting for cooldown ({w['handle']})")
    if state["failovers"]:
        last = state["failovers"][-1]
        lines.append(f"  last failover: @{last['handle']} {last['reason']} "
                     f"({last['account_label']})")
    return "\n".join(lines)


def final_summary(state, now=None):
    jobs = state["jobs"].values()
    incomplete = sum(1 for j in jobs if j["status"] in ("incomplete", "unresolved"))
    ended = sum(1 for j in jobs if j["status"] not in ("pending", "incomplete", "unresolved"))
    pool = state.get("pool", {})
    return (f"done: {ended} complete, {incomplete} incomplete of {len(jobs)} jobs · "
            f"{state['posts']} posts · {state['requests']} reqs · "
            f"{_fmt_dur(_elapsed(state, now))} · "
            f"accounts cooldown {pool.get('cooldown', 0)} dead {pool.get('dead', 0)} · "
            f"{len(state['failovers'])} failovers · status={state['status']}"
            + (f" · SCHEMA CHANGED: {state['schema_change']['detail']}"
               if state.get("schema_change") else ""))
