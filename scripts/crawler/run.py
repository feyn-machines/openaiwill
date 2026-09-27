"""Orchestration: plan → concurrent crawl → immutable, credential-free output.

Preserves the earlier guarantees: output is a new JSON file under data/, raw
pages are retained with SHA-256, reconciliation checks known announcements, and
coverage means only 'provider-visible timelines paged past the window start' —
website reconciliation stays separate. New: an account_usage log (labels only,
no secrets) and the improved success rule (a single account error that is failed
over does not fail the run).
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from . import parser, proxy as proxy_mod, scheduler

VERSION = "crawler-run-1"
COVERAGE_NOTE = ("Coverage describes provider-visible account timelines paged "
                 "past the window start; website reconciliation remains separate.")


def _write_json(path, data):
    payload = json.dumps(data, ensure_ascii=False, indent=2).encode()
    path.write_bytes(payload)
    os.chmod(path, 0o600)


def assemble_output(state, results, meta, expected_posts):
    """Build the final result document. Pure: no network, no secrets."""
    jobs = []
    all_ids = set()
    for job_id, js in state["jobs"].items():
        result = results.get(job_id, {})
        for post in result.get("posts", []):
            all_ids.add(post["id"])
        jobs.append({
            "id": job_id, "handle": js["handle"], "company": js.get("company"),
            "status": js["status"], "stop_reason": js["stop_reason"],
            "pages": js["pages"], "accepted_count": js["accepted_count"],
            "attempts": js["attempts"], "account_label": js["account_label"],
            "window_start": result.get("window_start"), "window_end": result.get("window_end"),
            "posts": result.get("posts", []), "quarantine": result.get("quarantine", []),
            "requests": result.get("requests", []), "next_cursor": result.get("next_cursor"),
        })
    expected = list(dict.fromkeys(expected_posts or []))
    missing = [pid for pid in expected if pid not in all_ids]
    reconciliation = {
        "status": ("missing" if missing else "passed") if expected else "not_configured",
        "expected_post_ids": expected, "missing_post_ids": missing,
    }
    account_usage = {
        "jobs": [{"handle": j["handle"], "account_label": j["account_label"],
                  "pages": j["pages"], "attempts": j["attempts"], "status": j["status"]}
                 for j in jobs],
        "failovers": state["failovers"],
        "pool_final": state["pool"],
    }
    # A failed-over account error must not fail the run; require every job ended.
    ok = state["ok"] and not missing
    return {
        "version": VERSION, "source": "x", "synthetic": False, "ok": ok,
        "status": "queries_exhausted" if ok else "needs_attention",
        "coverage_status": "provider_timelines", "coverage_note": COVERAGE_NOTE,
        "started_at": state["started_at"], "finished_at": state["finished_at"],
        "concurrency": state["concurrency"], "budgets": state["budgets"],
        "publication_window": meta.get("publication_window"),
        "total": len(all_ids), "requests": state["requests"],
        "jobs": jobs, "reconciliation": reconciliation, "account_usage": account_usage,
        "registry_sha256": meta.get("registry_sha256"),
        "implementation_sha256": meta.get("implementation_sha256"),
    }


def _impl_hashes():
    here = Path(__file__).resolve().parent
    files = ["parser.py", "engine.py", "scheduler.py", "accounts.py",
             "x_client.py", "proxy.py", "run.py"]
    return {name: hashlib.sha256((here / name).read_bytes()).hexdigest() for name in files}


def prepare(output, registry_path, start, end, handles):
    """Validate paths, plan jobs, reserve the immutable output. Returns (jobs, meta)."""
    root = Path(__file__).resolve().parents[2]
    output = Path(output).resolve()
    if not output.is_relative_to((root / "data").resolve()) or output.suffix != ".json":
        raise ValueError("Output must be a new JSON file under this project's private data directory")
    if output.exists() or output.with_suffix(".lock").exists():
        raise ValueError("Existing collection runs are immutable; choose a new output filename")
    registry = json.loads(Path(registry_path).read_text())
    jobs = parser.plan_timelines(registry, start, end,
                                 handles=handles.split(",") if handles else None)
    meta = {
        "registry_sha256": hashlib.sha256(Path(registry_path).read_bytes()).hexdigest(),
        "implementation_sha256": _impl_hashes(),
        "publication_window": {"start": parser.parse_time(start).isoformat(),
                               "end": parser.parse_time(end).isoformat()},
    }
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with output.with_suffix(".lock").open("x") as lock:
        lock.write("Reserved crawler run; do not overwrite.\n")
    _write_json(output, {"version": VERSION, "status": "planned", "ok": False,
                         "jobs": jobs, "expected_post_ids": [], **meta})
    return jobs, meta, output


async def execute(args, on_state=lambda s: None):
    """Full run: plan, crawl concurrently, write immutable output."""
    from . import x_client  # imports twikit; only needed for a live run
    root = Path(__file__).resolve().parents[2]
    proxy_mod.load_env(root)
    proxy_url = proxy_mod.proxy_url()

    jobs, meta, output = prepare(args.output, args.registry, args.start, args.end, args.handles)
    if args.plan_only:
        _write_json(output, {"version": VERSION, "status": "planned", "ok": False,
                             "jobs": jobs, "expected_post_ids": args.expect_post, **meta})
        return 0, None

    from .accounts import AccountPool
    pool = AccountPool.load(args.pool)
    pages_root = output.parent / (output.stem + ".pages")
    pages_root.mkdir(mode=0o700, exist_ok=True)
    factory = x_client.session_factory(proxy_url, pages_root, count=args.count)

    state, results = await scheduler.run_jobs(
        jobs, pool, factory, concurrency=args.concurrency, max_pages=args.max_pages,
        pace=args.pace, max_requests=args.max_requests, timeout=args.timeout,
        on_state=on_state)

    output_doc = assemble_output(state, results, meta, args.expect_post)
    _write_json(output, output_doc)
    return (0 if output_doc["ok"] else 2), output_doc
