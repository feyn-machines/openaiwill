#!/usr/bin/env python3
"""Collect the enabled official registry, with independent account/day pagination.

Use the social skill's Python runtime for live collection; --plan-only is stdlib.
No database changes, account login, automatic retries, or publication occur here.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import ssl
import sys
from urllib.parse import urlsplit

import official_x_collection as policy

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/social-qingguo-collector/scripts"


def write_json(path, value):
    content = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    temp = path.with_name(path.name + ".tmp")
    with temp.open("wb") as stream:
        stream.write(content)
    temp.chmod(0o600)
    temp.replace(path)
    return hashlib.sha256(content).hexdigest()


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--start", required=True, help="Inclusive publication time, with timezone")
    result.add_argument("--end", required=True, help="Exclusive publication time, with timezone")
    result.add_argument("--registry", type=Path, default=ROOT / "datasets/official-x-accounts.json")
    result.add_argument("--handles", help="Comma-separated subset of already enabled accounts")
    result.add_argument("--expect-post", action="append", default=[], help="Known announcement ID; missing IDs fail the run")
    result.add_argument("--output", type=Path, required=True, help="New result file under this project's private data directory")
    result.add_argument("--max-pages", type=int, default=10)
    result.add_argument("--max-requests", type=int, default=500)
    result.add_argument("--timeout", type=float, default=1800)
    result.add_argument("--pace", type=float, default=3)
    result.add_argument("--plan-only", action="store_true")
    return result


async def run_live(args, jobs, metadata, output):
    sys.path.insert(0, str(SKILL))
    import collect_social as runtime
    import fetch_x
    import httpx
    from diagnostics import diagnose

    runtime.load_runtime_env()
    # Reuse the installed skill's credential selection, proxy routing and parser.
    # The only proxy TLS exception is its existing Qingguo hostname mismatch.
    proxy = runtime.proxy_url()
    cookies = fetch_x.login_cookies()
    context = ssl.create_default_context()
    host = urlsplit(proxy).hostname or ""
    if host.endswith(".tunnel.qg.net") or host == "tunnel.qg.net":
        context.check_hostname = False
    client = fetch_x.Client(proxy=httpx.Proxy(proxy, ssl_context=context), timeout=25, trust_env=False)
    client.set_cookies(cookies)
    pages = output.parent / (output.stem + ".pages")
    pages.mkdir(mode=0o700)
    request_number = 0
    jobs_by_query = {job["query"]: job for job in jobs}

    async def fetch(query, cursor):
        nonlocal request_number
        request_number += 1
        job = jobs_by_query[query]
        if job["mode"] == "user_timeline":
            data, response = await client.gql.user_tweets(job["author_id"], 40, cursor)
        else:
            data, response = await client.gql.search_timeline(query, "Latest", 20, cursor)
        path = pages / f"{request_number:05d}.json"
        # Store response data only; never headers, cookies, proxy or request objects.
        digest = write_json(path, data)
        response.raise_for_status()
        if job["mode"] == "user_timeline":
            posts, following = policy.extract_user_timeline_page(data)
        else:
            posts, following = fetch_x.extract_page(data)
        return {"posts": posts, "next_cursor": following, "http_status": response.status_code,
                "raw_file": str(path.relative_to(output.parent)), "raw_sha256": digest}

    def save(state):
        write_json(output, {**state, **metadata})
        done = sum(j["status"] == "search_ended" for j in state["queries"])
        print(f"X: {len(state['requests'])} requests; {state['total']} posts; {done}/{len(jobs)} queries ended; {state['status']}", flush=True)

    def describe_error(exc):
        return {"type": type(exc).__name__, "error": runtime.safe_error(exc),
                "diagnostic": diagnose(exc, "x_api", runtime.safe_error)}

    try:
        return await policy.collect(jobs, fetch, max_pages=args.max_pages, max_requests=args.max_requests,
                                    timeout=args.timeout, pace=args.pace, expected_posts=args.expect_post,
                                    save=save, describe_error=describe_error)
    finally:
        await client.http.aclose()


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    # pnpm preserves the conventional separator for this script command.
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    args = parser().parse_args(arguments)
    os.umask(0o077)
    output = args.output.resolve()
    try:
        if not output.is_relative_to((ROOT / "data").resolve()) or output.suffix != ".json":
            raise ValueError("Output must be a new JSON file in this project's private data directory")
        if (args.max_pages < 1 or args.max_requests < 1
                or not math.isfinite(args.timeout) or args.timeout <= 0
                or not math.isfinite(args.pace) or args.pace < 3):
            raise ValueError("Positive budgets and at least 3 seconds between X requests are required")
        accounts = json.loads(args.registry.read_text())
        jobs = policy.plan_timelines(accounts, args.start, args.end,
                                     handles=args.handles.split(",") if args.handles else None)
        if any(not value.isdigit() for value in args.expect_post):
            raise ValueError("Expected posts must be numeric X post IDs")
        metadata = {
            "registry_sha256": hashlib.sha256(args.registry.read_bytes()).hexdigest(),
            "implementation_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in (Path(__file__), Path(policy.__file__))},
            "publication_window": {"start": policy.parse_time(args.start).isoformat(), "end": policy.parse_time(args.end).isoformat()},
        }
        if output.exists() or output.with_suffix(".lock").exists():
            raise ValueError("Existing collection runs are immutable; choose a new output filename")
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with output.with_suffix(".lock").open("x") as lock:
            lock.write("Reserved collection run; do not overwrite.\n")
        plan = {"version": policy.VERSION, "status": "planned", "ok": False,
                "queries": jobs, "expected_post_ids": args.expect_post, **metadata}
        write_json(output, plan)
        if args.plan_only:
            print(f"Planned {len(jobs)} independent account timeline jobs: {output}")
            return 0
        try:
            result = asyncio.run(run_live(args, jobs, metadata, output))
        except Exception as exc:
            # Preflight failures may happen before safe_error is available. Never
            # expose an unredacted third-party exception or overwrite saved pages.
            saved = json.loads(output.read_text())
            saved.update(status="error", ok=False, preflight_error=type(exc).__name__)
            write_json(output, saved)
            print(f"Collection failed ({type(exc).__name__}); partial state preserved at {output}", file=sys.stderr)
            return 1
        print(f"Saved {result['total']} posts; reconciliation={result['reconciliation']['status']}; {output}")
        return 0 if result["ok"] else 2
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Collection setup rejected: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
