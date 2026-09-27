"""Real PostgreSQL regressions for crawler-run ingestion into the collection store."""
import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psycopg import sql

from data_pipeline.db import connect, migrate
from data_pipeline.collection_store import ingest_run


def post(pid, created_utc, handle="OpenAI", author_id="4398626122", reply=False, text="hello"):
    return {"id": pid, "source_type": "x", "author": handle, "author_id": author_id,
            "url": f"https://x.com/{handle}/status/{pid}",
            "created_at": "Wed Sep 10 00:00:00 +0000 2026", "created_utc": created_utc,
            "text": text, "text_source": "legacy.full_text", "is_reply": reply,
            "is_repost": False, "quoted_post_id": None,
            "metrics": {"likes": 5, "reposts": 1, "replies": None, "quotes": 0, "bookmarks": 2, "views": 100},
            "metrics_observed_at": "2026-09-12T00:00:00+00:00", "metrics_updated_at": None}


def run_doc(posts):
    pub = 1757462400.0
    return {"version": "crawler-run-1", "source": "x", "synthetic": False, "ok": True,
            "status": "queries_exhausted", "started_at": "2026-09-12T00:00:00+00:00",
            "finished_at": "2026-09-12T00:05:00+00:00", "concurrency": 2,
            "publication_window": {"start": "2026-09-08T00:00:00+00:00", "end": "2026-09-11T00:00:00+00:00"},
            "registry_sha256": "a" * 64, "implementation_sha256": {"engine.py": "b" * 64},
            "jobs": [{"id": "job1", "handle": "OpenAI", "company": "OpenAI", "status": "search_ended",
                      "stop_reason": "window_start_reached", "pages": 1,
                      "accepted_count": len(posts), "attempts": 0, "account_label": "scraper1",
                      "window_start": "2026-09-08T00:00:00+00:00", "window_end": "2026-09-11T00:00:00+00:00",
                      "posts": [post(p, pub + i * 10) for i, p in enumerate(posts)],
                      "quarantine": [], "next_cursor": None,
                      "requests": [{"page": 1, "raw_file": "00001.json", "raw_sha256": "c" * 64}]}]}


class CollectionStoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = "openaiwill_collection_test_" + uuid.uuid4().hex
        with connect() as admin:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cls.database)))
        cls.addClassCleanup(cls.remove_database)
        with connect(cls.database) as conn:
            migrate(conn)

    @classmethod
    def remove_database(cls):
        with connect() as admin:
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(cls.database)))

    def setUp(self):
        self.conn = connect(self.database)
        self.addCleanup(self.conn.close)

    def write(self, directory, stem, doc):
        path = Path(directory) / f"{stem}.json"
        path.write_text(json.dumps(doc))
        return path

    def count(self, table, run_id):
        return self.conn.execute(f"SELECT count(*) AS n FROM {table} WHERE run_id=%s", (run_id,)).fetchone()["n"]

    def sources_of(self, run_id):
        """Posts this run brought in, counted through the captures it wrote.

        collected_sources is keyed on the post now, so its run_id names the run
        that FIRST saw the post - which is what a later run counting its own
        rows there would miss.
        """
        return self.conn.execute(
            "SELECT count(DISTINCT source_id) AS n FROM collected_captures WHERE run_id=%s",
            (run_id,)).fetchone()["n"]

    def test_ingest_inserts_run_sources_captures_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "run-A-" + uuid.uuid4().hex, run_doc(["111", "222"]))
            result = ingest_run(self.conn, path)
            rid = result["run_id"]
            self.assertFalse(result["reused"])
            self.assertEqual(result["sources"], 2)
            self.assertEqual(self.sources_of(rid), 2)
            self.assertEqual(self.count("collected_captures", rid), 2)
            self.assertEqual(self.count("collection_gaps", rid), 1)
            row = self.conn.execute("SELECT canonical_url,is_reply FROM collected_sources WHERE source_id='111'").fetchone()
            self.assertEqual(row["canonical_url"], "https://x.com/OpenAI/status/111")
            gap = self.conn.execute("SELECT status FROM collection_gaps WHERE run_id=%s", (rid,)).fetchone()
            self.assertEqual(gap["status"], "complete")

    def test_null_metric_preserved_in_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "run-N-" + uuid.uuid4().hex, run_doc(["111"]))
            rid = ingest_run(self.conn, path)["run_id"]
            m = self.conn.execute("SELECT metrics FROM collected_captures WHERE run_id=%s AND capture_id='111'", (rid,)).fetchone()["metrics"]
            self.assertIsNone(m["replies"])
            self.assertEqual(m["views"], 100)

    def test_idempotent_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "run-R-" + uuid.uuid4().hex, run_doc(["111", "222"]))
            first = ingest_run(self.conn, path)
            second = ingest_run(self.conn, path)
            self.assertTrue(second["reused"])
            self.assertEqual(self.sources_of(first["run_id"]), 2)

    def test_same_run_id_different_content_rejected(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            stem = "run-C-" + uuid.uuid4().hex
            ingest_run(self.conn, self.write(a, stem, run_doc(["111"])))
            with self.assertRaises(ValueError):
                ingest_run(self.conn, self.write(b, stem, run_doc(["111", "222"])))

    def test_a_post_seen_twice_is_one_post_and_two_observations(self):
        """Identity is stored once; the observation is stored per run.

        The key used to be (run_id, source_id), so a post seen by seven runs
        was stored seven times - 4,538 rows for 2,070 posts, and the number of
        posts whose platform, URL, kind or publication time differed between
        those copies was zero. Captures are the opposite and stay per run:
        1,248 of the 2,070 have genuinely different snapshots, because the
        metrics move. A capture per run is a time series; a source per run is
        a copy.
        """
        with tempfile.TemporaryDirectory() as tmp:
            r1 = ingest_run(self.conn, self.write(tmp, "run-X1-" + uuid.uuid4().hex, run_doc(["111"])))["run_id"]
            r2 = ingest_run(self.conn, self.write(tmp, "run-X2-" + uuid.uuid4().hex, run_doc(["111", "333"])))["run_id"]
            rows = self.conn.execute(
                "SELECT count(*) AS n FROM collected_sources WHERE source_id = '111'").fetchone()["n"]
            self.assertEqual(rows, 1, "one post, one identity row")
            # And it is the run that FIRST saw it, not the one that saw it last.
            first = self.conn.execute(
                "SELECT run_id FROM collected_sources WHERE source_id = '111'").fetchone()["run_id"]
            self.assertEqual(first, r1)
            observations = self.conn.execute(
                "SELECT count(*) AS n FROM collected_captures WHERE source_id = '111' "
                "AND run_id IN (%s, %s)", (r1, r2)).fetchone()["n"]
            self.assertEqual(observations, 2, "each run's snapshot is kept")
            distinct = self.conn.execute(
                "SELECT count(DISTINCT source_id) AS n FROM collected_captures "
                "WHERE run_id IN (%s, %s)", (r1, r2)).fetchone()["n"]
            self.assertEqual(distinct, 2)  # 111 and 333

    def test_run_metadata_and_raw_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            rid = ingest_run(self.conn, self.write(tmp, "run-M-" + uuid.uuid4().hex, run_doc(["111"])))["run_id"]
            run = self.conn.execute("SELECT status,ok,source_count,raw_pages FROM collection_runs WHERE run_id=%s", (rid,)).fetchone()
            self.assertEqual(run["status"], "queries_exhausted")
            self.assertTrue(run["ok"])
            self.assertEqual(run["source_count"], 1)
            self.assertEqual(run["raw_pages"][0]["file"], "job1/00001.json")


if __name__ == "__main__":
    unittest.main()
