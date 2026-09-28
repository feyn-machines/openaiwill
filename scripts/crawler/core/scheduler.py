"""Concurrent worker pool with account failover — the crawler's one scheduler.

Every job kind (a user timeline, a handle lookup, ...) runs through here. A
queue of jobs is drained by N workers. Each worker leases an account, opens a
session on it (one connection = one stable exit IP), runs the job's `work`, and
reacts to the classified failure it raises:

  RateLimited     cool the account (until the provider's reset when given) and
                  fail the job over to another account
  AuthFailed      retire the account and fail the job over
  TransportError  retry the job on a fresh connection of the same account
  SchemaChanged   stop the batch: every account would get the same answer
  other           fail this job only, no retry (a parser refused one record)

Failing over on a rate limit is a confirmed project rule (2026-09-27). A job
whose last response said the account's rate budget is spent also cools that
account, so the next job does not have to hit a 429 to find out.

The scheduler knows nothing about X. No credentials enter the state or logs —
only account labels.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from . import errors

MAX_PROVIDER_COOLDOWN = 3600  # never trust a reset header further out than this


def _now():
    return datetime.now(timezone.utc)


def new_state(jobs, *, concurrency, budgets):
    return {
        "status": "running", "ok": False,
        "started_at": _now().isoformat(), "finished_at": None,
        "concurrency": concurrency, "budgets": budgets,
        "requests": 0, "posts": 0, "schema_change": None,
        "jobs": {j["id"]: {"id": j["id"], "handle": j.get("handle"), "company": j.get("company"),
                           "status": "pending", "stop_reason": None, "pages": 0,
                           "accepted_count": 0, "attempts": 0, "transient": 0,
                           "tried_labels": [], "account_label": None} for j in jobs},
        "workers": {}, "failovers": [], "pool": {},
    }


async def run_jobs(jobs, pool, session_factory, work, unfinished, *, done_statuses,
                   concurrency=5, max_requests=1000, timeout=3600.0, max_attempts=4,
                   cooldown_seconds=900, max_transient=8, transient_backoff=5.0,
                   sticky=False, budgets=None, sleep=asyncio.sleep, loop_time=None,
                   on_state=lambda s: None):
    """Drain `jobs` concurrently with account failover. Returns (state, results).

    session_factory(lease, job) -> session with async close().
    work(job, session, on_request) -> result dict with at least status and
        stop_reason; it calls on_request(snapshot) once per provider request.
    unfinished(job, job_state) -> the result recorded for a job that never
        finished (no account left, budget, schema change).
    done_statuses: result statuses that count as a finished job for `ok`.
    sticky: a worker keeps its account and connection for its next job after a
        success (cheap one-request jobs such as lookups); otherwise every job
        leases afresh so load spreads across the pool.
    """
    loop_time = loop_time or asyncio.get_event_loop().time
    budgets = {**(budgets or {}), "max_requests": max_requests, "timeout_seconds": timeout,
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

    def emit():
        state["pool"] = pool.health_summary()
        on_state(state)

    def fail(job_id, stop_reason):
        js = state["jobs"][job_id]
        js.update(status="incomplete", stop_reason=stop_reason)
        results[job_id] = unfinished(targets[job_id], js)

    def cool(label, reset_at):
        now = pool.now().timestamp()
        if reset_at is not None and now < float(reset_at) <= now + MAX_PROVIDER_COOLDOWN:
            pool.mark_cooldown(label, until=reset_at)
        else:
            pool.mark_cooldown(label, cooldown_seconds)

    def failover(js, job_id, label, reason):
        js["attempts"] += 1
        if label not in js["tried_labels"]:
            js["tried_labels"].append(label)
        state["failovers"].append({"job_id": job_id, "handle": js["handle"],
                                   "account_label": label, "reason": reason})
        if js["attempts"] >= max_attempts:
            fail(job_id, f"exhausted_accounts:{reason}")
            return False
        js.update(status="pending", stop_reason=None)
        queue.put_nowait(job_id)
        return True

    def transient_retry(js, job_id, label):
        js["transient"] += 1
        state["failovers"].append({"job_id": job_id, "handle": js["handle"],
                                   "account_label": label, "reason": "transport_error"})
        if js["transient"] >= max_transient:
            fail(job_id, "transport_exhausted")
            return False
        js.update(status="pending", stop_reason=None)
        queue.put_nowait(job_id)
        return True

    async def worker(wid):
        ws = state["workers"][wid] = {"phase": "idle", "handle": None, "page": 0, "label": None}
        lease, session = None, None

        async def drop():
            nonlocal lease, session
            if session is not None:
                await session.close()
                session = None
            if lease is not None:
                pool.release(lease.label)
                lease = None

        while not stop.is_set():
            if loop_time() >= deadline or state["requests"] >= max_requests:
                stop.set()
                break
            try:
                job_id = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            js = state["jobs"][job_id]
            if lease is not None and lease.label in js["tried_labels"]:
                await drop()
            if lease is None:
                lease = pool.acquire(exclude=js["tried_labels"])
            if lease is None:
                queue.task_done()
                if not pool.has_leasable_untried(js["tried_labels"]):
                    fail(job_id, "no_accounts_available")
                    emit()
                    continue
                # An untried account is cooling or held by another worker; wait.
                wait = pool.next_cooldown_seconds(exclude=js["tried_labels"]) or 15
                ws.update(phase="waiting_cooldown", handle=js["handle"])
                emit()
                await sleep(min(wait, 15))
                queue.put_nowait(job_id)
                continue

            ws.update(phase="crawling", handle=js["handle"], page=0, label=lease.label)
            js["account_label"] = lease.label
            emit()
            if session is None:
                session = await session_factory(lease, targets[job_id])

            def on_request(snapshot, _ws=ws, _js=js):
                _ws["page"] = _js["pages"] = snapshot.get("pages", _ws["page"] + 1)
                state["requests"] += 1  # every provider request counts against the budget
                emit()

            keep = False
            try:
                result = await work(targets[job_id], session, on_request)
                js.update(status=result["status"], stop_reason=result.get("stop_reason"),
                          pages=result.get("pages", js["pages"]),
                          accepted_count=result.get("accepted_count", 0))
                results[job_id] = result
                state["posts"] = sum(r.get("accepted_count", 0) for r in results.values())
                limit = result.get("rate_limit") or {}
                if limit.get("remaining") is not None and limit["remaining"] <= 0:
                    cool(lease.label, limit.get("reset"))  # spent: rest it before the next job
                else:
                    pool.mark_usable(lease.label)
                    keep = sticky
            except errors.RateLimited as exc:
                cool(lease.label, exc.reset_at)
                failover(js, job_id, lease.label, "rate_limited")
            except errors.AuthFailed:
                pool.mark_dead(lease.label, "auth_failed")
                failover(js, job_id, lease.label, "auth_failed")
            except errors.TransportError:
                # Usually a bad exit IP: a fresh connection is a new IP. Neither
                # retires the account nor counts against max_attempts.
                if transient_retry(js, job_id, lease.label):
                    await drop()
                    await sleep(min(transient_backoff, timeout))
            except errors.SchemaChanged as exc:
                state["schema_change"] = {"job_id": job_id, "handle": js["handle"],
                                          "account_label": lease.label, "detail": str(exc)}
                fail(job_id, "schema_changed")
                stop.set()
            except Exception as exc:  # noqa: BLE001 - one record refused by a parser
                fail(job_id, f"parse_error:{type(exc).__name__}")
                pool.mark_usable(lease.label)
                keep = sticky
            finally:
                queue.task_done()
                if not keep:
                    await drop()
                ws.update(phase="idle", handle=None, page=0)
                emit()
        await drop()
        ws["phase"] = "stopped"

    emit()
    await asyncio.gather(*[worker(i) for i in range(concurrency)])

    reason = ("schema_changed" if state["schema_change"]
              else "request_budget" if state["requests"] >= max_requests else "interrupted")
    for job_id, js in state["jobs"].items():
        if js["status"] == "pending":
            fail(job_id, reason)

    state["ok"] = all(js["status"] in done_statuses for js in state["jobs"].values())
    state["status"] = "queries_exhausted" if state["ok"] else "needs_attention"
    state["finished_at"] = _now().isoformat()
    emit()
    return state, results
