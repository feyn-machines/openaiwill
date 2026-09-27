"""Concurrent worker pool with account failover — the core crawler behaviour.

A queue of user-timeline jobs is drained by N workers. Each worker leases an
account from the pool, opens a dedicated session (one connection = one stable
exit IP), crawls one target via the account-agnostic engine, then returns the
account. A rate limit cools the account down and requeues the job onto another
account; an auth failure retires the account. This replaces the old
stop-on-first-error behaviour. Accounts run in parallel; each account paces its
own requests. No credentials enter the state or logs — only account labels.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from . import engine


def _now():
    return datetime.now(timezone.utc)


def new_state(jobs, *, concurrency, budgets):
    return {
        "status": "running", "ok": False,
        "started_at": _now().isoformat(), "finished_at": None,
        "concurrency": concurrency, "budgets": budgets,
        "requests": 0, "posts": 0,
        "jobs": {j["id"]: {"id": j["id"], "handle": j["handle"], "company": j.get("company"),
                           "status": "pending", "stop_reason": None, "pages": 0,
                           "accepted_count": 0, "attempts": 0, "transient": 0,
                           "tried_labels": [], "account_label": None} for j in jobs},
        "workers": {}, "failovers": [], "pool": {},
    }


async def run_jobs(jobs, pool, session_factory, *, concurrency=5, max_pages=10,
                   pace=3.0, max_requests=1000, timeout=3600.0, max_attempts=4,
                   cooldown_seconds=900, max_transient=8, transient_backoff=5.0,
                   sleep=asyncio.sleep, loop_time=None, on_state=lambda s: None):
    """Drain `jobs` concurrently with account failover. Returns the final state.

    session_factory(lease) -> session, where session has async fetch_page(cursor)
    and async close(). Results are stored per job. The run never aborts on a
    single account's error; it aborts only on timeout or when no account can
    serve remaining jobs.
    """
    loop_time = loop_time or asyncio.get_event_loop().time
    budgets = {"max_pages": max_pages, "max_requests": max_requests,
               "pace_seconds": pace, "timeout_seconds": timeout,
               "max_attempts": max_attempts, "cooldown_seconds": cooldown_seconds,
               "max_transient": max_transient}
    state = new_state(jobs, concurrency=concurrency, budgets=budgets)
    targets = {j["id"]: j for j in jobs}
    results = {}
    queue = asyncio.Queue()
    for j in jobs:
        queue.put_nowait(j["id"])
    deadline = loop_time() + timeout
    stop = asyncio.Event()

    def refresh_pool():
        state["pool"] = pool.health_summary()

    def emit():
        refresh_pool()
        on_state(state)

    def finish_job(job_id, result, label):
        js = state["jobs"][job_id]
        js.update(status=result["status"], stop_reason=result["stop_reason"],
                  pages=result["pages"], accepted_count=result["accepted_count"],
                  account_label=label)
        results[job_id] = result
        state["posts"] = sum(r["accepted_count"] for r in results.values())

    async def worker(wid):
        state["workers"][wid] = {"phase": "idle", "handle": None, "page": 0, "label": None}
        ws = state["workers"][wid]
        while not stop.is_set():
            if loop_time() >= deadline:
                stop.set()
                break
            if state["requests"] >= max_requests:
                stop.set()
                break
            try:
                job_id = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            js = state["jobs"][job_id]
            lease = pool.acquire(exclude=js["tried_labels"])
            if lease is None:
                if not pool.has_leasable_untried(js["tried_labels"]):
                    # No untried account can ever serve this job.
                    js.update(status="incomplete", stop_reason="no_accounts_available")
                    _record_unfinished(results, targets[job_id], js)
                    emit()
                    queue.task_done()
                    continue
                # An untried account is merely cooling; wait briefly and retry.
                cd = pool.next_cooldown_seconds(exclude=js["tried_labels"]) or 15
                ws.update(phase="waiting_cooldown", handle=js["handle"])
                emit()
                queue.task_done()
                await sleep(min(cd, 15))
                queue.put_nowait(job_id)
                continue

            ws.update(phase="crawling", handle=js["handle"], page=0, label=lease.label)
            js["account_label"] = lease.label
            emit()
            session = await session_factory(lease, targets[job_id])

            def on_page(snapshot, _ws=ws):
                _ws["page"] = snapshot["pages"]
                state["requests"] += 1  # count each page request against the global budget
                emit()

            requeued = False
            try:
                result = await engine.crawl_target(
                    targets[job_id], session.fetch_page,
                    max_pages=max_pages, pace=pace, sleep=sleep, on_page=on_page)
                pool.mark_usable(lease.label)
                finish_job(job_id, result, lease.label)
                emit()
            except engine.RateLimited:
                pool.mark_cooldown(lease.label, cooldown_seconds)
                requeued = _failover(state, js, job_id, queue, lease.label, "rate_limited",
                                     max_attempts, results, targets)
                emit()
            except engine.AuthFailed:
                pool.mark_dead(lease.label, "auth_failed")
                requeued = _failover(state, js, job_id, queue, lease.label, "auth_failed",
                                     max_attempts, results, targets)
                emit()
            except engine.TransportError:
                # Not the account's fault (usually a bad proxy exit IP). Retry the
                # same job on a fresh connection/new IP under a separate bound;
                # do not consume an account slot or retire the account.
                requeued = _transient_retry(state, js, job_id, queue, lease.label,
                                            max_transient, results, targets)
                emit()
                if requeued:
                    await sleep(min(transient_backoff, timeout))
            finally:
                await session.close()
                queue.task_done()
                if not requeued:
                    ws.update(phase="idle", handle=None, page=0, label=None)
        state["workers"][wid]["phase"] = "stopped"

    emit()
    await asyncio.gather(*[worker(i) for i in range(concurrency)])

    # Any job never finished is incomplete.
    for job_id, js in state["jobs"].items():
        if js["status"] in ("pending",):
            js.update(status="incomplete", stop_reason="request_budget" if state["requests"] >= max_requests else "interrupted")
            if job_id not in results:
                results[job_id] = {**targets[job_id], "posts": [], "quarantine": [], "requests": [],
                                   "pages": js["pages"], "accepted_count": 0,
                                   "status": js["status"], "stop_reason": js["stop_reason"], "next_cursor": None}

    incomplete = [j for j in state["jobs"].values() if j["status"] != "search_ended"]
    state["ok"] = not incomplete
    state["status"] = "queries_exhausted" if state["ok"] else "needs_attention"
    state["finished_at"] = _now().isoformat()
    emit()
    return state, results


def _record_unfinished(results, target, js):
    results.setdefault(target["id"], {
        "id": target["id"], "handle": target["handle"], "author_id": target.get("author_id"),
        "company": target.get("company"),
        "window_start": target.get("window_start"), "window_end": target.get("window_end"),
        "posts": [], "quarantine": [], "requests": [], "pages": js["pages"],
        "accepted_count": 0, "status": js["status"], "stop_reason": js["stop_reason"],
        "next_cursor": None})


def _failover(state, js, job_id, queue, label, reason, max_attempts, results, targets):
    """A rate-limit/auth failure: retire this account for the job and fail over
    to a different one. Counts against max_attempts. Returns True if requeued."""
    js["attempts"] += 1
    if label not in js["tried_labels"]:
        js["tried_labels"].append(label)
    state["failovers"].append({"job_id": job_id, "handle": js["handle"],
                               "account_label": label, "reason": reason})
    if js["attempts"] >= max_attempts:
        js.update(status="incomplete", stop_reason=f"exhausted_accounts:{reason}")
        _record_unfinished(results, targets[job_id], js)
        return False
    js.update(status="pending", stop_reason=None)
    queue.put_nowait(job_id)
    return True


def _transient_retry(state, js, job_id, queue, label, max_transient, results, targets):
    """A transport failure (usually a bad proxy exit IP): retry the same job on a
    fresh connection/IP under a separate bound. Does not retire the account or
    count against max_attempts. Returns True if requeued."""
    js["transient"] += 1
    state["failovers"].append({"job_id": job_id, "handle": js["handle"],
                               "account_label": label, "reason": "transport_error"})
    if js["transient"] >= max_transient:
        js.update(status="incomplete", stop_reason="transport_exhausted")
        _record_unfinished(results, targets[job_id], js)
        return False
    js.update(status="pending", stop_reason=None)
    queue.put_nowait(job_id)
    return True
