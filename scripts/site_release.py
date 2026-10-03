#!/usr/bin/env python3
"""Build openaiwill locally and ship the build to the server over SSH.

  build     verify the snapshot, build, assemble .release/<id>/ and smoke-test it locally
  release   build, upload, and start the release as the candidate on the server
  promote   make the candidate the production service
  rollback  make the previous production release the production service again
  status    show what the server is running

The snapshot never leaves this machine: pages are rendered here and only the
rendered build is uploaded.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_pipeline.pipeline import digest  # noqa: E402

SNAPSHOT = ROOT / "datasets" / "published" / "latest"
STAGING = ROOT / ".release"
SITE_URL = "https://openaiwill.com"
SNAPSHOT_FILES = ["chain", "markets", "tasks", "events", "models", "sources", "coverage", "progress"]
PRODUCTION = {"project": "openaiwill", "port": 8320, "env": "production"}
CANDIDATE = {"project": "openaiwill-next", "port": 8321, "env": "preview"}
LOCAL_PORT = 8399
KEEP = 5
RELEASE_ID = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{7,40}(-dirty)?$")


class ReleaseError(Exception):
    pass


def release_id(generated_at: str, commit: str, dirty: bool) -> str:
    moment = datetime.fromisoformat(generated_at.replace("Z", "+00:00")).astimezone(timezone.utc)
    return f"{moment:%Y%m%dT%H%M%SZ}-{commit}{'-dirty' if dirty else ''}"


def checked_id(value: str) -> str:
    """Every id that comes from the server, or goes into a remote command, passes through here."""
    value = value.strip()
    if not RELEASE_ID.match(value):
        raise ReleaseError(f"not a release id: {value!r}")
    return value


def valid_ids(names: list[str]) -> list[str]:
    return [name for name in names if RELEASE_ID.match(name)]


def verify_snapshot(directory: Path) -> dict:
    """The manifest must describe the files beside it; a half-written snapshot is not built."""
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise ReleaseError(f"no manifest at {manifest_path}; run `pnpm data:publish:snapshot`")
    manifest = json.loads(manifest_path.read_text())
    payload = {}
    for name in SNAPSHOT_FILES:
        path = directory / f"{name}.json"
        if not path.is_file():
            raise ReleaseError(f"snapshot file missing: {name}.json")
        payload[name] = json.loads(path.read_text())
    counts = {
        **{f"chain.{key}": len(value) for key, value in payload["chain"].items()},
        **{key: len(value) for key, value in payload.items() if isinstance(value, list)},
        **{key: 1 for key, value in payload.items() if isinstance(value, dict) and key != "chain"},
    }
    if counts != manifest.get("counts"):
        raise ReleaseError("snapshot counts do not match its manifest")
    if digest(payload) != manifest.get("content_sha256"):
        raise ReleaseError("snapshot content_sha256 does not match its files")
    return manifest


FORBIDDEN_DIRS = {"datasets", "data", "local", "docs", "design", "db", "scripts", ".git", ".claude", ".agents", ".codex"}
FORBIDDEN_NAME = re.compile(r"^\.env|\.pem$|\.key$|\.sqlite3?$|\.db$|cookies|storage[-_]state|^credentials", re.I)


def forbidden_entries(release_dir: Path) -> list[str]:
    """Paths that must never be uploaded. The release is assembled from an allow-list; this is the second check."""
    found = []
    for path in sorted(release_dir.rglob("*")):
        relative = path.relative_to(release_dir)
        parts = relative.parts
        if "node_modules" in parts:
            continue
        # `app/<dir>/...`: a private directory copied next to the server.
        private_dir = len(parts) > 1 and parts[0] == "app" and parts[1] in FORBIDDEN_DIRS
        if path.is_file() and (private_dir or FORBIDDEN_NAME.search(path.name)):
            found.append(str(relative))
    return found


def to_prune(ids: list[str], keep: int, protected: set[str]) -> list[str]:
    ids = valid_ids(ids)
    old = sorted(ids)[:-keep] if len(ids) > keep else []
    return [name for name in old if name not in protected]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch(url: str, cookie: str | None = None, headers: dict | None = None):
    opener = urllib.request.build_opener(NoRedirect)
    sent = {**(headers or {}), **({"Cookie": cookie} if cookie else {})}
    request = urllib.request.Request(url, headers=sent)
    try:
        with opener.open(request, timeout=15) as response:
            return response.status, response.headers, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read().decode("utf-8", "replace")
    except (urllib.error.URLError, ConnectionError, TimeoutError) as error:
        raise ReleaseError(f"{url}: no answer ({error})") from error


def smoke(base: str, release: str | None) -> list[str]:
    """Requests a reader or a crawler would make. Returns the failures."""
    failures = []

    def expect(path, status, location=None, contains=None, cookie=None, headers=None):
        code, headers, body = fetch(base + path, cookie, headers)
        where = headers.get("Location")
        if code != status:
            failures.append(f"{path}: status {code}, expected {status}")
        if location is not None and where != location:
            failures.append(f"{path}: Location {where!r}, expected {location!r}")
        if contains is not None and contains not in body:
            failures.append(f"{path}: body lacks {contains!r}")
        return body

    health = expect("/healthz", 200)
    if release and release not in health:
        failures.append(f"/healthz does not report {release}")
    expect("/", 200, contains='lang="en"')
    expect("/zh-CN", 200, contains='lang="zh-CN"')
    expect("/markets", 200, contains='lang="en"')
    expect("/zh-CN/occupations", 200, contains='lang="zh-CN"')
    expect("/robots.txt", 200, contains="Sitemap:")
    expect("/llms.txt", 200, contains="# openaiwill")
    expect("/og/en.png", 200)
    sitemap = expect("/sitemap.xml", 200, contains="<urlset")
    # Redirects are relative: the origin is behind a tunnel and must not name a scheme or host.
    expect("/markets?lang=zh-CN", 307, location="/zh-CN/markets")
    expect("/zh-CN/markets?lang=en", 307, location="/markets")
    expect("/en/markets", 308, location="/markets")
    expect("/ZH-cn/markets", 308, location="/zh-CN/markets")
    expect("/markets", 307, location="/zh-CN/markets", cookie="openaiwill_language=zh-CN")
    # The proxy's internal marker must not be forgeable by a client.
    forged = {"x-openaiwill-rewritten": "1"}
    expect("/en/markets", 308, location="/markets", headers=forged)
    expect("/markets", 200, headers=forged)
    expect("/markets/no-such-market", 404)
    expect("/zh-CN/updates/no-such-update", 404)
    expect("/no-such-page", 404)
    # One real page of each kind, taken from the sitemap. Occupation addresses contain a dot
    # (the group pages /occupations/g/11 do not), so each of those is requested on its own.
    wanted = {
        "market": rf"/markets/[^<]+",
        "dotted occupation": r"/occupations/\d[^<]*\.[^<]+",
        "occupation group": r"/occupations/g/[^<]+",
        "update": r"/updates/[^<]+",
        "work": r"/work/[^<]+",
        "Chinese dotted occupation": r"/zh-CN/occupations/\d[^<]*\.[^<]+",
    }
    for label, pattern in wanted.items():
        match = re.search(rf"<loc>{re.escape(SITE_URL)}({pattern})</loc>", sitemap)
        if match:
            expect(match.group(1), 200)
        else:
            failures.append(f"sitemap lists no {label} page")
    return failures


def run(command, **kwargs):
    print("$", command if isinstance(command, str) else " ".join(map(str, command)), flush=True)
    return subprocess.run(command, check=True, cwd=ROOT, **kwargs)


def git(*args) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def load_target() -> dict:
    path = ROOT / ".env.deploy"
    if not path.is_file():
        raise ReleaseError("no .env.deploy; copy deploy/deploy.env.example to .env.deploy and fill it in")
    values = dict(line.split("=", 1) for line in path.read_text().splitlines()
                  if "=" in line and not line.lstrip().startswith("#"))
    for key in ("DEPLOY_HOST", "DEPLOY_USER", "DEPLOY_SSH_KEY", "DEPLOY_ROOT"):
        if not values.get(key, "").strip():
            raise ReleaseError(f".env.deploy lacks {key}")
    return {key: value.strip() for key, value in values.items()}


def ssh_base(target: dict) -> list[str]:
    return ["ssh", "-i", os.path.expanduser(target["DEPLOY_SSH_KEY"]), "-o", "IdentitiesOnly=yes",
            "-o", "BatchMode=yes", f"{target['DEPLOY_USER']}@{target['DEPLOY_HOST']}"]


def remote(target: dict, script: str, capture: bool = False) -> str:
    result = subprocess.run([*ssh_base(target), "bash", "-euo", "pipefail", "-c", shlex.quote(script)],
                            check=True, text=True, capture_output=capture)
    return result.stdout.strip() if capture else ""


def compose(slot: dict, release: str, action: str) -> str:
    return (f"sudo RELEASE_ID={shlex.quote(checked_id(release))} HOST_PORT={slot['port']} SITE_ENV={slot['env']} "
            f"docker compose -p {slot['project']} {action}")


def rpath(target: dict, *parts: str) -> str:
    """A quoted path under the deploy root."""
    return shlex.quote("/".join([target["DEPLOY_ROOT"], *parts]))


def healthy(slot: dict, release: str) -> str:
    """Shell test: the slot answers /healthz and names this release. No early pipe close under pipefail."""
    return f"curl -fsS http://127.0.0.1:{slot['port']}/healthz | grep {shlex.quote(release)} >/dev/null"


def remote_id(target: dict, name: str) -> str:
    """The release id stored in a state file on the server ('' when the file is absent)."""
    value = remote(target, f"cat {rpath(target, name)} 2>/dev/null || true", capture=True)
    return checked_id(value) if value.strip() else ""


def build() -> str:
    manifest = verify_snapshot(SNAPSHOT)
    # Untracked files do not change what is built from the commit, so only edits to tracked files mark a release dirty.
    release = release_id(manifest["generated_at"], git("rev-parse", "--short", "HEAD"),
                         bool(git("status", "--porcelain", "--untracked-files=no")))
    if release.endswith("-dirty"):
        print("warning: uncommitted changes; this release cannot be reproduced from a commit", file=sys.stderr)
    run(["pnpm", "check"], env={**os.environ, "RELEASE_ID": release})

    staged = STAGING / release
    shutil.rmtree(STAGING, ignore_errors=True)
    app = staged / "app"
    # `next build` copies the project's .env and .env.production into the standalone
    # directory whatever the tracing config says. They hold local keys and the server
    # reads none of them (the container gets SITE_ENV from compose), so they stay behind.
    shutil.copytree(ROOT / ".next" / "standalone", app, symlinks=True, ignore=shutil.ignore_patterns(".env*"))
    shutil.copytree(ROOT / ".next" / "static", app / ".next" / "static")
    shutil.copytree(ROOT / "public", app / "public")
    shutil.copy(ROOT / "deploy" / "Dockerfile", staged / "Dockerfile")
    shutil.copy(ROOT / "deploy" / "compose.yml", staged / "compose.yml")
    (staged / "release.json").write_text(json.dumps({
        "release": release,
        "commit": git("rev-parse", "HEAD"),
        "snapshot_generated_at": manifest["generated_at"],
        "snapshot_sha256": manifest["content_sha256"],
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2) + "\n")

    found = forbidden_entries(staged)
    if found:
        raise ReleaseError("release contains files that must not be uploaded:\n  " + "\n  ".join(found[:20]))

    server = subprocess.Popen(["node", "server.js"], cwd=app,
                              env={**os.environ, "PORT": str(LOCAL_PORT), "HOSTNAME": "127.0.0.1", "SITE_ENV": "preview"})
    try:
        base = f"http://127.0.0.1:{LOCAL_PORT}"
        for _ in range(30):
            try:
                fetch(base + "/healthz")
                break
            except ReleaseError:
                time.sleep(0.5)
        else:
            raise ReleaseError(f"the local server never answered at {base}")
        failures = smoke(base, release)
        if fetch(base + "/markets")[1].get("X-Robots-Tag") != "noindex":
            failures.append("a non-production server did not send X-Robots-Tag: noindex")
    finally:
        server.terminate()
        server.wait()
    if failures:
        raise ReleaseError("smoke test failed:\n  " + "\n  ".join(failures))
    print(f"built {release} at {staged.relative_to(ROOT)}")
    return release


def release_command() -> None:
    target = load_target()
    release = build()
    user = shlex.quote(target["DEPLOY_USER"])
    # A failed release must not leave an earlier candidate for `promote` to pick up.
    remote(target, f"sudo install -d -o {user} -g {user} {rpath(target)} {rpath(target, 'releases')}"
                   f" && rm -f {rpath(target, 'candidate')}")
    key = shlex.quote(os.path.expanduser(target["DEPLOY_SSH_KEY"]))
    run(["rsync", "-az", "--delete", "-e", f"ssh -i {key} -o IdentitiesOnly=yes -o BatchMode=yes",
         f"{STAGING / release}/",
         f"{target['DEPLOY_USER']}@{target['DEPLOY_HOST']}:{target['DEPLOY_ROOT']}/releases/{release}/"])
    remote(target, f"cd {rpath(target, 'releases', release)} && {compose(CANDIDATE, release, 'up -d --build --wait')} "
                   f"&& {healthy(CANDIDATE, release)} && echo {shlex.quote(release)} > {rpath(target, 'candidate')}")
    print(f"\ncandidate {release} is running on the server.\n"
          f"preview:  ssh -i {target['DEPLOY_SSH_KEY']} -N -L 8321:127.0.0.1:{CANDIDATE['port']} "
          f"{target['DEPLOY_USER']}@{target['DEPLOY_HOST']}   then open http://localhost:8321\n"
          f"go live:  pnpm site:promote")


def switch_script(target: dict, release: str, live: str) -> str:
    """Start `release` as production. If it does not come up healthy, put `live` back."""
    release_dir = rpath(target, "releases", release)
    if live:
        live_dir = rpath(target, "releases", live)
        restore = (f"if [ -d {live_dir} ]; then cd {live_dir} && {compose(PRODUCTION, live, 'up -d --wait')}; "
                   f"echo 'production restored to {live}' >&2; "
                   f"else echo 'production could not be restored: {live} is gone' >&2; fi")
        remember = f"echo {shlex.quote(live)} > {rpath(target, 'previous')}" if live != release else ":"
    else:
        restore = "echo 'there was no earlier release to restore' >&2"
        remember = ":"
    return f"""
test -d {release_dir}
cd {release_dir}
if ! ( {compose(PRODUCTION, release, 'up -d --build --wait')} && {healthy(PRODUCTION, release)} ); then
  echo 'release {release} did not become healthy' >&2
  {restore}
  exit 1
fi
{remember}
echo {shlex.quote(release)} > {rpath(target, 'current')}
"""


def switch(target: dict, release: str) -> None:
    release = checked_id(release)
    remote(target, switch_script(target, release, remote_id(target, "current")))


def promote_command() -> None:
    target = load_target()
    release = remote_id(target, "candidate")
    if not release:
        raise ReleaseError("there is no candidate; run `pnpm site:release` first")
    remote(target, healthy(CANDIDATE, release))
    switch(target, release)
    remote(target, f"cd {rpath(target, 'releases', release)} && {compose(CANDIDATE, release, 'down')} "
                   f"&& rm -f {rpath(target, 'candidate')}")
    listing = remote(target, f"ls {rpath(target, 'releases')}", capture=True).split()
    protected = set(valid_ids(remote(target, f"cat {rpath(target, 'current')} {rpath(target, 'previous')} "
                                              "2>/dev/null || true", capture=True).split()))
    for old in to_prune(listing, KEEP, protected):
        remote(target, f"rm -rf {rpath(target, 'releases', old)}; "
                       f"sudo docker image rm -f {shlex.quote('openaiwill-web:' + old)} >/dev/null 2>&1 || true")
    print(f"production is now {release}")
    failures = smoke(SITE_URL, release)
    if fetch(SITE_URL + "/markets")[1].get("X-Robots-Tag"):
        failures.append("production sends X-Robots-Tag; it must be indexable")
    if failures:
        raise ReleaseError("production is switched but the public check failed (pnpm site:rollback to revert):\n  "
                           + "\n  ".join(failures))
    notify_indexnow()


def rollback_command() -> None:
    target = load_target()
    release = remote_id(target, "previous")
    if not release:
        raise ReleaseError("there is no previous release to roll back to")
    switch(target, release)
    print(f"production is back on {release}")


def status_command() -> None:
    target = load_target()
    print(remote(target, f"""
echo "current:   $(cat {rpath(target, 'current')} 2>/dev/null || echo none)"
echo "previous:  $(cat {rpath(target, 'previous')} 2>/dev/null || echo none)"
echo "candidate: $(cat {rpath(target, 'candidate')} 2>/dev/null || echo none)"
echo "releases:  $(ls {rpath(target, 'releases')} 2>/dev/null | tr '\\n' ' ')"
sudo docker ps --filter name=openaiwill --format '{{{{.Names}}}}  {{{{.Image}}}}  {{{{.Status}}}}  {{{{.Ports}}}}'
""", capture=True))


def notify_indexnow() -> None:
    """Tell IndexNow-fed engines (Bing, and through it ChatGPT search) which addresses exist now."""
    keys = [path for path in (ROOT / "public").glob("*.txt")
            if re.fullmatch(r"[0-9a-f]{32}", path.stem) and path.read_text().strip() == path.stem]
    if not keys:
        print("no IndexNow key in public/; skipped")
        return
    _, _, sitemap = fetch(SITE_URL + "/sitemap.xml")
    urls = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    body = json.dumps({"host": "openaiwill.com", "key": keys[0].stem,
                       "keyLocation": f"{SITE_URL}/{keys[0].name}", "urlList": urls}).encode()
    request = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                     headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"IndexNow: {response.status} for {len(urls)} addresses")
    except urllib.error.URLError as error:
        print(f"IndexNow not notified ({error}); the release itself is unaffected", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["build", "release", "promote", "rollback", "status"])
    command = parser.parse_args().command
    try:
        {"build": build, "release": release_command, "promote": promote_command,
         "rollback": rollback_command, "status": status_command}[command]()
    except ReleaseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"error: command failed with status {error.returncode}", file=sys.stderr)
        return error.returncode or 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
