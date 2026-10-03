"""The server side of the data release line: set up the database, connect to it over SSH.

Nothing here stores or prints a password. The passwords are generated on the server by
`setup_script`; a data release reads the writer's one from the server into memory and
uses it through an SSH forward to the database's loopback port.

No psycopg import at module level: the pure builders are unit-tested with the system python.
"""
from __future__ import annotations

import contextlib
import re
import socket
import subprocess
import time
from pathlib import Path

import site_release as site
from site_release import PRODUCTION, ReleaseError

ROOT = site.ROOT
DEPLOY_DB = ROOT / "deploy" / "db"
SCHEMA_SQL = ROOT / "db" / "published" / "001_kg.sql"

DB_PORT = 5434
DB_NAME = "openaiwill"
WRITER = "oaw_kg_writer"
SITE_ROLE = "oaw_site"
PASSWORD_PATTERN = re.compile(r"[0-9A-Za-z]{32,}")
WATCH_SECONDS = 60


def parse_env(text: str) -> dict[str, str]:
    """KEY=VALUE lines of an env file; blank lines and # comments are skipped."""
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def checked_password(value: str) -> str:
    """A password read from the server. A malformed one is refused without echoing any value."""
    value = value.strip()
    if not PASSWORD_PATTERN.fullmatch(value):
        raise ReleaseError("db.env on the server has no usable OAW_KG_WRITER_PASSWORD; run `pnpm db:setup` first")
    return value


def writer_password(env_text: str) -> str:
    """The data writer's password from the text of db.env."""
    return checked_password(parse_env(env_text).get("OAW_KG_WRITER_PASSWORD", ""))


def db_forward_argv(target: dict, local_port: int) -> list[str]:
    """ssh command forwarding a local port to the server database's loopback port."""
    return site.forward_argv(target, local_port, DB_PORT)


def heredoc(path: str, text: str, tag: str) -> str:
    """Shell that writes `text` to `path` byte for byte (quoted here-document)."""
    if not re.fullmatch(r"[A-Z_]+", tag):
        raise ValueError("bad here-document tag")
    if tag in text.splitlines():
        raise ReleaseError(f"{tag} occurs in the text being uploaded")
    return f"cat > {path} <<'{tag}'\n{text if text.endswith(chr(10)) else text + chr(10)}{tag}\n"


def setup_script(target: dict, compose_text: str, roles_sql: str, schema_sql: str, grants_sql: str) -> str:
    """The one script `pnpm db:setup` runs on the server (sent on stdin). Repeatable.

    Passwords are generated here, only when db.env does not exist, written with umask 077, and
    handed to psql through `docker exec --env-file` so they never appear on a command line.

    Recovery from a lost db.env while the database volume exists: delete site.env too and run this again.
    Everything here reaches PostgreSQL as the superuser through the container's local socket (trusted, no
    password), and roles.sql then sets all three role passwords, the superuser's included, to the newly
    generated ones. No step needs the old superuser password, and no data is touched.
    Every command that could read the script from stdin has its own redirect."""
    root = site.rpath(target)
    db = site.rpath(target, "db")
    env_file = site.rpath(target, "db", "db.env")
    site_env = site.site_env_file(target)

    def put(name: str, text: str, tag: str) -> str:
        return heredoc(site.rpath(target, "db", name), text, tag)

    psql = f"sudo docker exec -i --env-file {env_file} openaiwill-db psql -X -q -v ON_ERROR_STOP=1"
    # The stock image trusts 127.0.0.1 and the socket, so the passwords are only enforced on the container's own
    # network address: that is where the checks connect, with the password taken from the env file inside the
    # container (never on a command line).
    address = 'ip=$(hostname -i); ip=${{ip%% *}}; '  # doubled braces: str.format below
    check = ('sudo docker exec -i --env-file {env} openaiwill-db sh -c '
             "'" + address + 'PGPASSWORD="{password}" psql -X -h "$ip" -U {role} -d {db} -tAc "{sql}"\' </dev/null')
    wrong = check.format(env="db.env", password="not-the-password", role=SITE_ROLE, db=DB_NAME, sql="SELECT 1")
    return f"""umask 077
sudo install -d -m 755 -o "$(id -un)" -g "$(id -gn)" {root} {db} </dev/null
sudo docker network inspect openaiwill >/dev/null 2>&1 </dev/null || sudo docker network create openaiwill >/dev/null </dev/null
newpw() {{ local p; p=$(openssl rand -hex 24); [ "${{#p}}" -eq 48 ] || {{ echo 'could not generate a password' >&2; exit 1; }}; echo "$p"; }}
if [ ! -f {env_file} ]; then
  if [ -f {site_env} ]; then echo 'site.env exists but db/db.env does not; refusing to invent new passwords' >&2; exit 1; fi
  a=$(newpw); b=$(newpw); c=$(newpw)
  printf 'POSTGRES_PASSWORD=%s\\nOAW_KG_WRITER_PASSWORD=%s\\nOAW_SITE_PASSWORD=%s\\n' "$a" "$b" "$c" > {env_file}
  echo 'generated the database passwords on the server'
fi
chmod 600 {env_file}
if [ ! -f {site_env} ]; then
  pw=$(sed -n 's/^OAW_SITE_PASSWORD=//p' {env_file})
  [ -n "$pw" ] || {{ echo 'db.env has no OAW_SITE_PASSWORD' >&2; exit 1; }}
  printf 'DATABASE_URL=postgres://{SITE_ROLE}:%s@openaiwill-db:5432/{DB_NAME}\\n' "$pw" > {site_env}
  echo 'wrote site.env'
fi
chmod 600 {site_env}
{put('compose.yml', compose_text, 'OPENAIWILL_COMPOSE_EOF')}{put('roles.sql', roles_sql, 'OPENAIWILL_ROLES_EOF')}{put('001_kg.sql', schema_sql, 'OPENAIWILL_SCHEMA_EOF')}{put('grants.sql', grants_sql, 'OPENAIWILL_GRANTS_EOF')}cd {db}
sudo docker compose -p openaiwill-db --env-file db.env up -d --wait --wait-timeout 180 </dev/null
{psql} -U postgres -d postgres < roles.sql
{psql} -U {WRITER} -d {DB_NAME} < 001_kg.sql
{psql} -U {WRITER} -d {DB_NAME} < grants.sql
{check.format(env='db.env', password='$OAW_KG_WRITER_PASSWORD', role=WRITER, db=DB_NAME, sql='SELECT count(*) FROM kg.releases')} >/dev/null
n=$({check.format(env='db.env', password='$OAW_SITE_PASSWORD', role=SITE_ROLE, db=DB_NAME, sql='SELECT count(*) FROM kg.releases')})
if {wrong} >/dev/null 2>&1; then echo 'password authentication is not being enforced on the container network' >&2; exit 1; fi
echo "both roles authenticate with their passwords over the container network and a wrong password is refused; releases in kg: $n"
echo 'database ready (127.0.0.1:{DB_PORT} on the server, network openaiwill)'
"""


def port_probe_script(port: int) -> str:
    """Prints `listening` or `none`: whether something accepts connections on the server's loopback port."""
    return (f"if (exec 3<>/dev/tcp/127.0.0.1/{int(port)}) 2>/dev/null; then echo listening; else echo none; fi")


def remote_stdin(target: dict, script: str) -> None:
    """Run a script on the server by sending it on stdin; its output is shown as it comes."""
    subprocess.run([*site.ssh_base(target), "bash", "-euo", "pipefail", "-s"], input=script, text=True, check=True)


def setup_db() -> None:
    target = site.load_target()
    script = setup_script(target, (DEPLOY_DB / "compose.yml").read_text(), (DEPLOY_DB / "roles.sql").read_text(),
                          SCHEMA_SQL.read_text(), (DEPLOY_DB / "grants.sql").read_text())
    remote_stdin(target, script)


def read_writer_password(target: dict) -> str:
    try:
        # Only the writer's value is fetched, and without sudo: the deploy user owns the file (mode 600).
        value = site.remote(target, f"sed -n 's/^OAW_KG_WRITER_PASSWORD=//p' {site.rpath(target, 'db', 'db.env')}",
                            capture=True)
    except subprocess.CalledProcessError as error:
        raise ReleaseError(f"could not read the database credentials on the server (status {error.returncode}); "
                           "has `pnpm db:setup` run?") from None
    return checked_password(value)


def wait_for_listener(port: int, process: subprocess.Popen, seconds: float = 15) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ReleaseError(f"the SSH forward exited with status {process.returncode}")
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.3)
    raise ReleaseError("the SSH forward to the server database did not open")


@contextlib.contextmanager
def server_connection():
    """A psycopg connection to the server database as the data writer, through an SSH forward that is
    always closed. The password lives in this process's memory only."""
    import psycopg
    from psycopg.rows import dict_row

    target = site.load_target()
    password = read_writer_password(target)
    port = site.free_port()
    forward = subprocess.Popen(db_forward_argv(target, port), stdin=subprocess.DEVNULL)
    try:
        wait_for_listener(port, forward)
        conn = psycopg.connect(host="127.0.0.1", port=port, dbname=DB_NAME, user=WRITER, password=password,
                               autocommit=True, row_factory=dict_row, connect_timeout=10,
                               application_name="openaiwill-data-release", options="-c timezone=UTC -c search_path=public")
        try:
            yield conn
        finally:
            conn.close()
    finally:
        forward.terminate()
        forward.wait()


def poll_release(read_body, expected: str, seconds: float = WATCH_SECONDS, interval: float = 3,
                 sleep=time.sleep, clock=time.monotonic) -> tuple[bool, str]:
    """Poll until the site reports data release `expected`. read_body() returns the /healthz body or raises
    ReleaseError. Returns (matched, the release last reported, or '' when it never answered)."""
    deadline = clock() + seconds
    last = ""
    while True:
        try:
            last = site.health_data(read_body()).get("releaseId") or ""
        except ReleaseError:
            pass
        if last == expected:
            return True, last
        if clock() >= deadline:
            return False, last
        sleep(interval)


def report_production(expected: str | None = None) -> None:
    """Say what the production site serves. With `expected`, wait up to 60 s for it to serve that release.
    Never fails the command: the database change has already been made."""
    try:
        _report_production(expected)
    except (ReleaseError, subprocess.SubprocessError, OSError) as error:
        print(f"could not check the production site ({' '.join(str(error).split())}); the database change is done")


def _report_production(expected: str | None) -> None:
    target = site.load_target()
    probe = site.remote(target, port_probe_script(PRODUCTION["port"]), capture=True)
    if probe != "listening":
        print("no production site is running yet")
        return
    port = site.free_port()
    forward = subprocess.Popen(site.forward_argv(target, port, PRODUCTION["port"]), stdin=subprocess.DEVNULL)
    try:
        wait_for_listener(port, forward)
        base = f"http://127.0.0.1:{port}"
        read_body = lambda: site.fetch(base + "/healthz")[2]  # noqa: E731
        if expected is None:
            print(f"production site: {site.describe_health(read_body())}")
            return
        matched, last = poll_release(read_body, expected)
        if matched:
            print(f"production site now serves data release {expected}")
        else:
            print(f"WARNING: production site still reports data release {last or 'none'} after {WATCH_SECONDS} s "
                  "(it re-checks every 30 s); run `pnpm site:status` to look again")
    except ReleaseError as error:
        print(f"could not read the production site: {error}")
    finally:
        forward.terminate()
        forward.wait()
