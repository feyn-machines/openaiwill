"""The crawler's one door into the project database.

Which accounts to collect lives in public.source_accounts, and a finished run
belongs in the collection store; both are owned by data_pipeline, so this
module borrows its connection and functions instead of restating them. The run
file stays the provenance: it is written first and ingested from, never
replaced by the database rows.

data_pipeline (and psycopg) are imported lazily, so the rest of the crawler
and its offline tests need neither.
"""
from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def connect():
    from data_pipeline import db
    with db.connect() as conn:
        db.migrate(conn)
        yield conn


def timeline_targets(targets="official"):
    """Enabled X accounts to collect, in the registry shape the planner reads."""
    from data_pipeline import panel
    with connect() as conn:
        return panel.crawl_targets(conn, targets)


def lookup_handles(missing_only=True):
    """Handles to resolve: those without a platform id, or every live account."""
    from data_pipeline import panel
    with connect() as conn:
        return panel.lookup_plan(conn, missing_only=missing_only)


def ingest_timeline(run_path):
    """Idempotently load a finished timeline run into the collection store."""
    from data_pipeline.collection_store import ingest_run
    with connect() as conn:
        return ingest_run(conn, run_path)


def ingest_lookup(doc):
    """Record a lookup run as account checks, then re-derive account states."""
    from data_pipeline import panel
    with connect() as conn:
        with conn.transaction():
            counts = panel.record_lookup(conn, doc)
        with conn.transaction():
            changed = panel.refresh(conn)
        return {"lookup": counts, "state_changes": len(changed)}
