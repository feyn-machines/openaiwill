"""The crawler's one command line.

    pnpm crawl timeline --start ... --end ... --output data/collection/official-x/<run>.json
    pnpm crawl lookup --output data/collection/lookups/<run>.json
    pnpm crawl doctor

Accounts come from public.source_accounts and a finished run is loaded into the
database (timeline -> collection store, lookup -> account checks) unless
--no-ingest; the run file under data/ is written first and stays the provenance.

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
    src = t.add_mutually_exclusive_group()
    src.add_argument("--targets", choices=("official", "panel", "all"), default="official",
                     help="Enabled accounts from source_accounts (default: official)")
    src.add_argument("--registry", type=Path, help="Read accounts from this registry file instead")
    t.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    t.add_argument("--handles", help="Comma-separated subset of already enabled accounts")
    t.add_argument("--no-ingest", action="store_true", help="Leave the run out of the collection store")
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
    src = lk.add_mutually_exclusive_group()
    src.add_argument("--handles", help="Comma-separated handles (default: source_accounts without an id)")
    src.add_argument("--handles-file", type=Path, help="One handle per line")
    src.add_argument("--all", action="store_true", help="Every live account in source_accounts (profile refresh)")
    lk.add_argument("--no-ingest", action="store_true", help="Leave the results out of the account checks")
    lk.add_argument("--output", type=Path, required=True, help="New JSON file under data/")
    lk.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    lk.add_argument("--concurrency", type=int, default=1)
    lk.add_argument("--max-requests", type=int, default=1000)
    lk.add_argument("--timeout", type=float, default=3600)
    lk.add_argument("--pace", type=float, default=MIN_PACE)

    d = sub.add_parser("doctor", help="Check proxy (TLS handshake only), account pool, database and runtime; never contacts X")
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


def timeline_accounts(args):
    """(accounts, provenance) from source_accounts, or from --registry when given."""
    if args.registry:
        return json.loads(args.registry.read_text()), {"source": str(args.registry)}
    from .core import store
    return store.timeline_targets(args.targets), {"source": "db:source_accounts", "set": args.targets}


def _ingest(label, ingest, *arg):
    try:
        result = ingest(*arg)
    except Exception as exc:  # noqa: BLE001 - the run file is safe; report and exit 2
        print(f"{label} failed; the run file is kept and can be ingested later: {exc}", file=sys.stderr)
        return False
    print(f"{label}: {json.dumps(result, default=str)}")
    return True


async def run_timeline(args, on_state):
    from .x import parse, timeline
    proxy_mod.load_env(ROOT)
    proxy_url = proxy_mod.proxy_url()
    accounts, provenance = timeline_accounts(args)
    jobs = parse.plan_timelines(accounts, args.start, args.end,
                                handles=args.handles.split(",") if args.handles else None)
    meta = {
        # The account list this run was planned from, whichever store it came from.
        "registry_sha256": hashlib.sha256(json.dumps(accounts, sort_keys=True, ensure_ascii=False)
                                          .encode()).hexdigest(),
        "targets": provenance,
        "proxy_transport": proxy_mod.transport(proxy_url),
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
    ingested = True
    if not args.no_ingest:
        from .core import store
        ingested = _ingest("Ingested into the collection store", store.ingest_timeline, output)
    return 0 if doc["ok"] and ingested else 2


async def run_lookup(args, on_state):
    from .x import lookup
    if args.handles or args.handles_file:
        raw = args.handles.split(",") if args.handles else args.handles_file.read_text().split()
    else:
        from .core import store
        raw = store.lookup_handles(missing_only=not args.all)
    handles = [j["handle"] for j in lookup.jobs_for(raw)]
    if not handles:
        print("Nothing to look up: every account already has a platform id (use --all to refresh profiles)")
        return 0
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
    doc["proxy_transport"] = proxy_mod.transport(proxy_url)
    archive.write_json(output, doc, indent=1)
    print(json.dumps({"output": str(output), "counts": doc["counts"], "pool": doc["pool_health"]}))
    ingested = True
    if not args.no_ingest:
        from .core import store
        ingested = _ingest("Recorded as account checks", store.ingest_lookup, doc)
    return 0 if doc["ok"] and ingested else 2


def doctor(args):
    """Readiness report. Touches only the proxy entry's TLS handshake, never X;
    prints labels and counts only, never secrets."""
    problems = []
    proxy_mod.load_env(ROOT)
    try:
        url = proxy_mod.proxy_url()
        scheme = proxy_mod.transport(url)
        cert = proxy_mod.entry_report(url)
        if not cert["ok"]:
            problems.append(f"proxy entry ({scheme}) failed: {cert['error']}")
            print(f"proxy      configured ({scheme}) · FAILED: {cert['error']}")
        else:
            print(f"proxy      configured (https) · certificate valid until {cert['not_after']} "
                  f"({cert['days_left']} days)" if cert["not_after"]
                  else f"proxy      configured ({scheme}) · {cert.get('note', 'ok')}; "
                       "proxy credential travels unencrypted")
            if cert["days_left"] is not None and cert["days_left"] < 7:
                problems.append(f"proxy certificate expires in {cert['days_left']} days")
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
        from .core import store
        official, panel_ = len(store.timeline_targets("official")), len(store.timeline_targets("panel"))
        print(f"database   {official} official + {panel_} panel accounts enabled for collection")
        if official == 0:
            problems.append("no official account is enabled; run `pnpm data:official:import`")
    except Exception as exc:  # noqa: BLE001 - report any reason the store is unreachable
        problems.append(f"database unavailable: {exc}")
        print("database   UNAVAILABLE")
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
