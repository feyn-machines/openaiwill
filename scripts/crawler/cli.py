"""CLI entry for the X crawler. `pnpm crawl:x -- --start ... --end ... --output ...`."""
from __future__ import annotations

import argparse
import asyncio
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from crawler import run, progress  # noqa: E402


def parser():
    p = argparse.ArgumentParser(description="Concurrent X official-account crawler")
    p.add_argument("--start", required=True, help="Inclusive publication time, with timezone")
    p.add_argument("--end", required=True, help="Exclusive publication time, with timezone")
    p.add_argument("--output", type=Path, required=True, help="New JSON file under data/")
    p.add_argument("--registry", type=Path, default=ROOT / "datasets/official-x-accounts.json")
    p.add_argument("--pool", type=Path, default=ROOT / "data/secrets/x-accounts/pool.json")
    p.add_argument("--handles", help="Comma-separated subset of already enabled accounts")
    p.add_argument("--expect-post", action="append", default=[], help="Known announcement ID; missing IDs fail the run")
    p.add_argument("--concurrency", type=int, default=5)
    p.add_argument("--count", type=int, default=40, help="Tweets requested per page")
    p.add_argument("--max-pages", type=int, default=10)
    p.add_argument("--max-requests", type=int, default=1000)
    p.add_argument("--timeout", type=float, default=3600)
    p.add_argument("--pace", type=float, default=3)
    p.add_argument("--plan-only", action="store_true")
    return p


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


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    args = parser().parse_args(arguments)
    import os
    os.umask(0o077)
    if (args.concurrency < 1 or args.max_pages < 1 or args.max_requests < 1
            or not math.isfinite(args.timeout) or args.timeout <= 0
            or not math.isfinite(args.pace) or args.pace < 3):
        print("Positive budgets and at least 3 seconds between requests are required", file=sys.stderr)
        return 1
    if any(not str(v).isdigit() for v in args.expect_post):
        print("Expected posts must be numeric X post IDs", file=sys.stderr)
        return 1

    reporter = Reporter()
    try:
        code, doc = asyncio.run(run.execute(args, on_state=reporter))
    except (ValueError, OSError) as exc:
        print(f"Crawler setup rejected: {exc}", file=sys.stderr)
        return 1
    if doc is None:
        print(f"Planned run written to {args.output}")
        return 0
    print(f"Saved {doc['total']} posts across {len(doc['jobs'])} jobs; "
          f"reconciliation={doc['reconciliation']['status']}; ok={doc['ok']}; {args.output}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
