"""Schema `app` (user data): applying it, setting it up locally, pulling approved submissions.

The schema belongs to role oaw_app. The role and the schema itself are created by a superuser
(here for the local database; by deploy/db/roles.sql on the server); the tables are created by oaw_app.
Passwords are passed as query parameters or through the environment, never formatted into SQL text.

No psycopg import at module level: the pure helpers are unit-tested with the system python."""
from __future__ import annotations

import os
import re
import secrets
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_ROLE = "oaw_app"
APP_SQL = sorted((ROOT / "db/app").glob("*.sql"))
PASSWORD_FILE = ROOT / "data/postgres/app-password"
ENV_FILES = (ROOT / ".env", ROOT / ".env.local")
LOCAL_DATABASE = "openaiwill_local"


class AppError(Exception):
    """A problem the operator can act on; the command line prints it as one line."""


def apply_schema(conn) -> None:
    """Apply db/app/*.sql in one transaction. `conn` is a connection as the schema's owner."""
    with conn.transaction():
        for path in APP_SQL:
            conn.execute(path.read_text())


def ensure_role_and_schema(admin_conn, password: str, role: str = APP_ROLE) -> None:
    """Create the role if absent, set its password and limits, and create schema app owned by it."""
    from psycopg import sql

    name = sql.Identifier(role)
    exists = admin_conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
    if not exists:
        admin_conn.execute(sql.SQL("CREATE ROLE {} LOGIN").format(name))
    admin_conn.execute(sql.SQL("ALTER ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}").format(
        name, sql.Literal(password)))
    admin_conn.execute(sql.SQL("ALTER ROLE {} SET search_path = app").format(name))
    database = admin_conn.execute("SELECT current_database() AS name").fetchone()["name"]
    admin_conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), name))
    admin_conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS app AUTHORIZATION {}").format(name))
    admin_conn.execute(sql.SQL("ALTER SCHEMA app OWNER TO {}").format(name))


def _write_atomic(path: Path, text: str) -> None:
    """Write `text` to `path` through a mode-0600 temp file in the same directory, then replace."""
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def local_password(path: Path | None = None) -> str:
    """The local oaw_app password, created on first use in an ignored file with mode 0600."""
    path = PASSWORD_FILE if path is None else Path(path)
    if not path.is_symlink() and not path.exists():
        _write_atomic(path, secrets.token_hex(24))
    if path.is_symlink() or not path.is_file():
        raise AppError("The local app password file must be a regular file, not a link")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise AppError("The local app password file must have mode 0600")
    value = path.read_text().strip()
    if not value:
        raise AppError("The local app password file is empty")
    return value


def connect_app(database: str | None = None):
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(
        host="127.0.0.1", port=7543, dbname=LOCAL_DATABASE if database is None else database,
        user=APP_ROLE, password=local_password(), autocommit=True, row_factory=dict_row,
        connect_timeout=5, application_name="openaiwill-app", options="-c timezone=UTC")


def _env_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    key, value = line.split("=", 1)
    return key.strip(), value.strip()


def read_env_value(key: str, paths=ENV_FILES) -> str | None:
    """The value of one KEY in the given env files (later file wins), scanning line by line.
    A value wrapped in matching quotes loses them. Nothing else is kept in memory."""
    found = None
    for path in paths:
        if not Path(path).is_file():
            continue
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                pair = _env_line(line)
                if pair and pair[0] == key:
                    value = pair[1]
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                        value = value[1:-1]
                    found = value
    return found


def read_admin_emails(paths=ENV_FILES) -> list[str]:
    """Administrator addresses from ADMIN_EMAILS: trimmed, lower-cased, de-duplicated, without '@'-less entries."""
    emails: list[str] = []
    for entry in (read_env_value("ADMIN_EMAILS", paths) or "").split(","):
        entry = entry.strip().lower()
        if "@" in entry[1:] and entry not in emails:
            emails.append(entry)
    return emails


def sync_admins(conn, emails: list[str]) -> tuple[int, int]:
    """Make app.admins equal to `emails` in one transaction; return (added, removed)."""
    wanted = sorted({e.strip().lower() for e in emails if e.strip()})
    if not wanted:
        raise AppError("ADMIN_EMAILS is empty; the administrator list was left unchanged")
    with conn.transaction():
        removed = conn.execute("DELETE FROM app.admins WHERE email <> ALL(%s) RETURNING email", (wanted,)).fetchall()
        added = conn.execute(
            "INSERT INTO app.admins (email) SELECT unnest(%s::text[]) ON CONFLICT DO NOTHING RETURNING email",
            (wanted,)).fetchall()
    return len(added), len(removed)


def write_env_local(values: dict[str, str], path: Path | None = None) -> None:
    """Replace KEY= lines in place, append missing keys, keep every other line, mode 0600."""
    path = ROOT / ".env.local" if path is None else Path(path)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pending = dict(values)
    for index, line in enumerate(lines):
        exported = line.lstrip().startswith("export ")
        pair = _env_line(line.lstrip()[7:] if exported else line)
        if pair and pair[0] in pending:
            lines[index] = f"{'export ' if exported else ''}{pair[0]}={pending.pop(pair[0])}"
    lines.extend(f"{key}={value}" for key, value in pending.items())
    _write_atomic(path, "\n".join(lines) + "\n")


def setup_local() -> None:
    """Create role and schema in the local working database, apply the tables, sync administrators, update .env.local."""
    from data_pipeline.db import connect

    password = local_password()
    with connect() as admin:
        ensure_role_and_schema(admin, password)
    with connect_app() as conn:
        apply_schema(conn)
        emails = read_admin_emails()
        if emails:
            added, removed = sync_admins(conn, emails)
            print(f"administrators: {len(emails)} on the list (+{added}, -{removed})")
        else:
            print("administrators: ADMIN_EMAILS is empty; the list in the database was left unchanged")
    values = {
        "APP_DATABASE_URL": f"postgres://{APP_ROLE}:{password}@127.0.0.1:7543/{LOCAL_DATABASE}",
        "BETTER_AUTH_URL": "http://localhost:3456",
    }
    if not read_env_value("BETTER_AUTH_SECRET", (ROOT / ".env.local",)):
        values["BETTER_AUTH_SECRET"] = secrets.token_hex(32)
    write_env_local(values)
    print("app schema ready in the local database; .env.local updated (values not shown)")
