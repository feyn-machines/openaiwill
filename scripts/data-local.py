#!/usr/bin/env python3
"""Manage the workspace's loopback local infra (PostgreSQL + MLflow) and Python data runtime."""

import argparse
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = ROOT / "data/postgres/password"
PYTHON = ROOT / "data/runtime/venv/bin/python"
COMPOSE = ["docker", "compose", "--project-name", "openaiwill-data-local",
           "--project-directory", str(ROOT / "infra"),
           "--file", str(ROOT / "infra/docker-compose.yml")]


def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def private_password():
    run(["git", "check-ignore", "--quiet", str(PASSWORD)])
    if PASSWORD.is_symlink():
        raise RuntimeError("Refusing a password file symlink")
    PASSWORD.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    PASSWORD.parent.chmod(0o700)
    try:
        descriptor = os.open(PASSWORD, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if not PASSWORD.is_file() or not PASSWORD.read_text().strip():
            raise RuntimeError("Existing PostgreSQL password file is invalid") from None
        PASSWORD.chmod(0o600)
    else:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(secrets.token_urlsafe(48) + "\n")


def up():
    private_password()
    running = run(COMPOSE + ["ps", "--status", "running", "--quiet", "postgres"],
                  capture_output=True, text=True).stdout.strip()
    if not running:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", 7543))
            except OSError:
                raise RuntimeError("127.0.0.1:7543 is occupied; no containers were changed") from None
    run(COMPOSE + ["up", "--detach", "--wait", "--wait-timeout", "180"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "up", "status", "down", "psql"))
    parser.add_argument("psql_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.psql_args and args.command != "psql":
        parser.error("Additional arguments are accepted only for psql")
    if args.command == "setup":
        private_password()
        if not PYTHON.exists():
            venv.create(PYTHON.parents[1], with_pip=True)
        run([str(PYTHON), "-m", "pip", "install", "--disable-pip-version-check",
             "-r", str(ROOT / "requirements-data.txt")])
        up()
        run([str(PYTHON), "-c", "import sys; sys.path.insert(0, 'scripts'); "
             "from data_pipeline.db import connect, migrate; "
             "conn=connect(); print('Migrations applied:', migrate(conn)); conn.close()"])
    elif args.command == "up":
        up()
    elif args.command == "status":
        run(COMPOSE + ["ps"])
    elif args.command == "down":
        run(COMPOSE + ["down"])
        print("Local PostgreSQL stopped; its named data volume was retained.")
    else:
        extra = args.psql_args
        if extra[:1] == ["--"]:
            extra = extra[1:]
        terminal = [] if sys.stdin.isatty() and sys.stdout.isatty() else ["-T"]
        run(COMPOSE + ["exec"] + terminal + ["postgres", "psql", "-U", "openaiwill",
                                            "-d", "openaiwill_local"] + extra)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
        print(f"Local data runtime: {error}", file=sys.stderr)
        sys.exit(1)
