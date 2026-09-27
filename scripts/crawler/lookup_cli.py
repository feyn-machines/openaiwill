"""Resolve X handles to user ids and public profiles through the account pool.

    pnpm crawl:lookup -- --handles-file data/panel/lookup-handles.txt \
        --output data/collection/lookups/<new-run>.json

The output is a new, immutable JSON file under data/ (0600); each raw response
is kept beside it under <output>.pages/ with its SHA-256. No secrets are
written: records carry only the pool account's non-secret label.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawler import lookup, proxy as proxy_mod  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def parser():
    p = argparse.ArgumentParser(description="Resolve X handles through the account pool")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--handles", help="Comma-separated handles")
    src.add_argument("--handles-file", type=Path, help="One handle per line")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--pool", type=Path, default=ROOT / "data/secrets/x-accounts/pool.json")
    p.add_argument("--pace", type=float, default=3.0)
    return p


def _handles(args):
    raw = args.handles.split(",") if args.handles else args.handles_file.read_text().split()
    return list(dict.fromkeys(h.strip().lstrip("@") for h in raw if h.strip()))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--"]:  # `pnpm crawl:lookup -- ...` passes the separator through
        argv = argv[1:]
    args = parser().parse_args(argv)
    if args.pace < 3.0:
        raise SystemExit("--pace must be at least 3 seconds")
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "data").resolve()) or output.suffix != ".json":
        raise SystemExit("Output must be a new JSON file under this project's data directory")
    if output.exists():
        raise SystemExit("Existing lookup runs are immutable; choose a new output filename")
    handles = _handles(args)
    proxy_mod.load_env(ROOT)
    from crawler import x_client  # imports twikit
    from crawler.accounts import AccountPool
    pool = AccountPool.load(args.pool)
    pages = output.parent / (output.stem + ".pages")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    started = datetime.now(timezone.utc)

    def report(handle, record):
        print(f"@{handle}: {record['status']}", file=sys.stderr)

    results = asyncio.run(lookup.run_lookups(
        handles, pool, x_client.lookup_session_factory(proxy_mod.proxy_url(), pages),
        pace=args.pace, on_result=report))
    counts = {}
    for r in results.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    doc = {"version": "lookup-1", "started_at": started.isoformat(),
           "finished_at": datetime.now(timezone.utc).isoformat(),
           "ok": counts.get("unresolved", 0) == 0, "counts": counts,
           "pool_health": pool.health_summary(), "results": results}
    output.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    os.chmod(output, 0o600)
    print(json.dumps({"output": str(output), "counts": counts, "pool": doc["pool_health"]}))
    return 0 if doc["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
