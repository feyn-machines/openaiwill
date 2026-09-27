# infra — local infrastructure (Docker)

All local infrastructure for openaiwill, in one Compose file: `docker-compose.yml`
(PostgreSQL + MLflow). Everything binds to `127.0.0.1` only and keeps its data under
the gitignored `data/` tree; nothing leaves the machine. Managed by
`scripts/data-local.py`:

```sh
pnpm data:up        # start Postgres + MLflow (first run builds the MLflow image)
pnpm data:status    # Postgres status
pnpm data:down      # stop both (never removes volumes)
```

All persistence is bind-mounted under `infra/data/` (gitignored) so the data is a
visible, portable directory you control — not an opaque Docker-managed volume:
`infra/data/postgres` (PGDATA) and `infra/data/mlflow/` (MLflow sqlite + artifacts).
The PostgreSQL password secret stays at the repo-root `data/postgres/password`.

- **PostgreSQL** — `127.0.0.1:7543`, db `openaiwill_local`; data at `infra/data/postgres`.
- **MLflow** — experiment tracking for the scoring / progress method. Dashboard at
  **http://127.0.0.1:7545**; sqlite + artifacts under `infra/data/mlflow/`.
  Each scoring iteration logs one run (params = method config, note = what changed,
  metrics = loss + supporting), so progress is watchable without reading code changes.
  Clients log with `MLFLOW_TRACKING_URI=http://127.0.0.1:7545`. Telemetry disabled; no account.

`mlflow/Dockerfile` pins the MLflow server build.
