"""The crawler's one command line.

    pnpm crawl timeline --start ... --end ... --output data/collection/official-x/<run>.json
    pnpm crawl lookup --handles-file ... --output data/collection/lookups/<run>.json
    pnpm crawl doctor

`pnpm crawl:x` and `pnpm crawl:lookup` are aliases for the first two. Exit
codes: 0 finished, 2 finished but needs attention, 1 setup rejected.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .core import archive, progress, proxy as proxy_mod
from .core.accounts import AccountPool

ROOT = archive.ROOT
DEFAULT_POOL = ROOT / "data/secrets/x-accounts/pool.json"
MIN_PACE = 3.0


def build_parser():
    p = argparse.ArgumentParser(prog="crawl", description="openaiwill local crawler")
    sub = p.add_subparsers(dest="command", required=True)

    t = sub.add_parser("timeline", help="Collect X account timelines for a publication window")
    t.add_argument("--start", required=True, help="Inclusive publication time, with timezone")
    t.add_argument("--end", required=True, help="Exclusive publication time, with timezone")
    t.add_argument("--output", type=Path, required=True, help="New JSON file under data/")
    t.add_argument("--registry", type=Path, default=ROOT / "datasets/official-x-accounts.json")
    t.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    t.add_argument("--handles", help="Comma-separated subset of already enabled accounts")
    t.add_argument("--expect-post", action="append", default=[],
                   help="Known announcement ID; missing IDs fail the run")
    t.add_argument("--concurrency", type=int, default=5)
    t.add_argument("--count", type=int, default=40, help="Posts requested per page")
    t.add_argument("--max-pages", type=int, default=10)
    t.add_argument("--max-requests", type=int, default=1000)
    t.add_argument("--timeout", type=float, default=3600)
    t.add_argument("--pace", type=float, default=MIN_PACE)
    t.add_argument("--plan-only", action="store_true")

    lk = sub.add_parser("lookup", help="Resolve X handles to user ids and public profiles")
    src = lk.add_mutually_exclusive_group(required=True)
    src.add_argument("--handles", help="Comma-separated handles")
    src.add_argument("--handles-file", type=Path, help="One handle per line")
    lk.add_argument("--output", type=Path, required=True, help="New JSON file under data/")
    lk.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    lk.add_argument("--concurrency", type=int, default=1)
    lk.add_argument("--max-requests", type=int, default=1000)
    lk.add_argument("--timeout", type=float, default=3600)
    lk.add_argument("--pace", type=float, default=MIN_PACE)

    d = sub.add_parser("doctor", help="Offline check of proxy config, account pool and runtime")
    d.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    return p


def parse_args(argv):
    # `pnpm crawl:x -- --start ...` passes the separator through; drop it
    # wherever it lands before or right after the subcommand.
    argv = list(argv)
    for i in (0, 1):
        if i < len(argv) and argv[i] == "--":
            del argv[i]
            break
    return build_parser().parse_args(argv)


def validate(args):
    """Return an error message for unsafe budgets, or None."""
    if args.command == "doctor":
        return None
    if (args.concurrency < 1 or args.max_requests < 1
            or not math.isfinite(args.timeout) or args.timeout <= 0
            or not math.isfinite(args.pace) or args.pace < MIN_PACE):
        return f"Positive budgets and at least {MIN_PACE:g} seconds between requests are required"
    if args.command == "timeline":
        if args.max_pages < 1:
            return "Positive budgets are required"
        if any(not str(v).isdigit() for v in args.expect_post):
            return "Expected posts must be numeric X post IDs"
    return None


class Reporter:
    """Throttled progress printer: TTY block redraw, else summary + milestones."""

    def __init__(self, interval=1.0):
        self.interval = interval
        self.is_tty = sys.stderr.isatty()
        self._last = 0.0
        self._last_lines = 0
        self._seen_failovers = 0
        self._final_done = False

    def __call__(self, state):
        completed = state["status"] != "running"
        now = time.monotonic()
        if not completed and now - self._last < self.interval:
            return
        self._last = now
        if self.is_tty:
            self._redraw(progress.block(state))
        else:
            for fo in state["failovers"][self._seen_failovers:]:
                print(f"  failover: @{fo['handle']} {fo['reason']} ({fo['account_label']})",
                      file=sys.stderr, flush=True)
            self._seen_failovers = len(state["failovers"])
            print(progress.summary_line(state), file=sys.stderr, flush=True)
        if completed and not self._final_done:
            self._final_done = True
            print(progress.final_summary(state), file=sys.stderr, flush=True)

    def _redraw(self, text):
        if self._last_lines:
            sys.stderr.write(f"\033[{self._last_lines}A\033[J")
        sys.stderr.write(text + "\n")
        sys.stderr.flush()
        self._last_lines = text.count("\n") + 1


async def run_timeline(args, on_state):
    from .x import parse, timeline
    proxy_mod.load_env(ROOT)
    proxy_url = proxy_mod.proxy_url()
    registry = json.loads(args.registry.read_text())
    jobs = parse.plan_timelines(registry, args.start, args.end,
                                handles=args.handles.split(",") if args.handles else None)
    meta = {
        "registry_sha256": hashlib.sha256(args.registry.read_bytes()).hexdigest(),
        "implementation_sha256": archive.implementation_hashes(),
        "publication_window": {"start": parse.parse_time(args.start).isoformat(),
                               "end": parse.parse_time(args.end).isoformat()},
    }
    output = archive.reserve(args.output)
    archive.write_json(output, {"version": timeline.VERSION, "status": "planned", "ok": False,
                                "jobs": jobs, "expected_post_ids": args.expect_post, **meta})
    if args.plan_only:
        print(f"Planned run written to {output}")
        return 0

    from .x import client  # imports twikit; only needed for a live run
    pool = AccountPool.load(args.pool)
    factory = client.timeline_session_factory(proxy_url, archive.pages_dir(output), count=args.count)
    state, results = await timeline.run(
        jobs, pool, factory, concurrency=args.concurrency, max_pages=args.max_pages,
        pace=args.pace, max_requests=args.max_requests, timeout=args.timeout, on_state=on_state)
    doc = timeline.assemble_output(state, results, meta, args.expect_post)
    archive.write_json(output, doc)
    print(f"Saved {doc['total']} posts across {len(doc['jobs'])} jobs; "
          f"reconciliation={doc['reconciliation']['status']}; ok={doc['ok']}; {output}")
    return 0 if doc["ok"] else 2


async def run_lookup(args, on_state):
    from .x import lookup
    raw = args.handles.split(",") if args.handles else args.handles_file.read_text().split()
    handles = [j["handle"] for j in lookup.jobs_for(raw)]
    if not handles:
        raise ValueError("No handles to look up")
    proxy_mod.load_env(ROOT)
    proxy_url = proxy_mod.proxy_url()
    output = archive.reserve(args.output)
    from .x import client  # imports twikit
    pool = AccountPool.load(args.pool)
    started = datetime.now(timezone.utc)

    def report(handle, record):
        print(f"@{handle}: {record['status']}", file=sys.stderr, flush=True)

    state, results = await lookup.run(
        handles, pool, client.lookup_session_factory(proxy_url, archive.pages_dir(output)),
        pace=args.pace, concurrency=args.concurrency, max_requests=args.max_requests,
        timeout=args.timeout, on_result=report, on_state=on_state)
    doc = lookup.assemble_output(results, started, pool.health_summary(), state)
    archive.write_json(output, doc, indent=1)
    print(json.dumps({"output": str(output), "counts": doc["counts"], "pool": doc["pool_health"]}))
    return 0 if doc["ok"] else 2


def doctor(args):
    """Offline readiness report. Prints labels and counts only, never secrets."""
    problems = []
    proxy_mod.load_env(ROOT)
    try:
        proxy_mod.proxy_url()
        print("proxy      configured")
    except RuntimeError as exc:
        problems.append(str(exc))
        print(f"proxy      MISSING: {exc}")
    if args.pool.exists():
        mode = args.pool.stat().st_mode & 0o777
        pool = AccountPool.load(args.pool)
        no_token = sum(1 for a in pool.accounts if not a.get("auth_token"))
        print(f"pool       {len(pool.accounts)} accounts · {pool.health_summary()} · "
              f"{no_token} without auth_token · mode {oct(mode)}")
        if mode & 0o077:
            problems.append(f"pool file is readable by others (mode {oct(mode)}); chmod 600")
        if pool.available_count() == 0:
            problems.append("no account can be leased right now")
    else:
        problems.append(f"pool file not found: {args.pool}")
        print("pool       MISSING")
    try:
        import twikit  # noqa: F401
        print(f"runtime    twikit {getattr(twikit, '__version__', '?')}")
    except ImportError:
        problems.append("twikit is not installed; run `pnpm crawl:setup`")
        print("runtime    twikit MISSING")
    for p in problems:
        print(f"problem: {p}", file=sys.stderr)
    return 1 if problems else 0


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    os.umask(0o077)
    error = validate(args)
    if error:
        print(error, file=sys.stderr)
        return 1
    if args.command == "doctor":
        return doctor(args)
    runner = run_timeline if args.command == "timeline" else run_lookup
    try:
        return asyncio.run(runner(args, Reporter()))
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Crawler setup rejected: {exc}", file=sys.stderr)
        return 1
