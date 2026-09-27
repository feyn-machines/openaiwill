"""Real PostgreSQL regressions for extraction ingestion into the event layer."""
import json
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psycopg import sql
from psycopg.types.json import Jsonb

from data_pipeline import type_layer
from data_pipeline.db import connect, migrate
from data_pipeline.collection_store import ingest_run
from data_pipeline.event_extraction import (
    EVENT_KIND_VOCABULARY, assemble_extraction, dedup_key, event_id_for, ingest_extraction,
    resolve_org)


def seed_org_registry(conn):
    """extracted_events.primary_org_id is an FK, so the registry precedes ingestion.

    Projected from the same datasets/semantic/organizations.json that
    type_layer.seed reads, so the ids here cannot drift from the ones resolve_org
    returns. Only the organisations: the rest of the seed needs a full ontology
    release, which this file's subject - the event layer - does not touch.
    """
    for row in type_layer.org_rows():
        conn.execute(
            """INSERT INTO org_registry
               (org_id, canonical_name_en, canonical_name_zh_cn, aliases, record_sha256)
               VALUES (%(org_id)s,%(canonical_name_en)s,%(canonical_name_zh_cn)s,
                       %(aliases)s,%(record_sha256)s)
               ON CONFLICT (org_id) DO NOTHING""",
            {**row, "aliases": Jsonb(row["aliases"])})


def crawler_post(pid, created_utc):
    return {"id": pid, "source_type": "x", "author": "OpenAI", "author_id": "4398626122",
            "url": f"https://x.com/OpenAI/status/{pid}",
            "created_at": "Wed Sep 10 00:00:00 +0000 2026", "created_utc": created_utc,
            "text": f"post {pid}", "text_source": "legacy.full_text", "is_reply": False,
            "is_repost": False, "quoted_post_id": None,
            "metrics": {"likes": 1, "reposts": 0, "replies": None, "quotes": 0, "bookmarks": 0, "views": 10},
            "metrics_observed_at": "2026-09-12T00:00:00+00:00", "metrics_updated_at": None}


def crawler_run(posts, run_id):
    pub = 1757462400.0
    return {"version": "crawler-run-1", "source": "x", "synthetic": False, "ok": True,
            "status": "queries_exhausted", "started_at": "2026-09-12T00:00:00+00:00",
            "finished_at": "2026-09-12T00:05:00+00:00", "concurrency": 1,
            "publication_window": {"start": "2026-09-08T00:00:00+00:00", "end": "2026-09-11T00:00:00+00:00"},
            "registry_sha256": "a" * 64, "implementation_sha256": {"engine.py": "b" * 64},
            "jobs": [{"id": "job1", "handle": "OpenAI", "company": "OpenAI", "status": "search_ended",
                      "stop_reason": "window_start_reached", "pages": 1, "accepted_count": len(posts),
                      "attempts": 0, "account_label": "SECRET", "window_start": "2026-09-08T00:00:00+00:00",
                      "window_end": "2026-09-11T00:00:00+00:00",
                      "posts": [crawler_post(p, pub + i * 10) for i, p in enumerate(posts)],
                      "quarantine": [], "next_cursor": None,
                      "requests": [{"page": 1, "raw_file": "00001.json", "raw_sha256": "c" * 64}]}]}


def candidate(sid, run_id):
    return {"run_id": run_id, "source_id": sid, "platform": "x", "handle": "OpenAI",
            "company": "OpenAI", "url": f"https://x.com/OpenAI/status/{sid}",
            "published_at": datetime(2026, 9, 10, tzinfo=timezone.utc), "excerpt": "x", "metrics": {}}


def meta():
    return {"model": "deepseek-chat", "prompt_sha256": "d" * 64, "params": {"batch_size": 25},
            "window": None, "started_at": "2026-09-14T00:00:00+00:00",
            "finished_at": "2026-09-14T00:05:00+00:00", "status": "completed"}


class EventLayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = "openaiwill_events_test_" + uuid.uuid4().hex
        with connect() as admin:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cls.database)))
        cls.addClassCleanup(cls.remove_database)
        with connect(cls.database) as conn:
            migrate(conn)
            seed_org_registry(conn)

    @classmethod
    def remove_database(cls):
        with connect() as admin:
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(cls.database)))

    def setUp(self):
        self.conn = connect(self.database)
        self.addCleanup(self.conn.close)
        self.uid = uuid.uuid4().hex[:8]  # unique subjects: shared DB + deterministic event_id
        self.subject = f"gpt-x-{self.uid}"  # identity is (org, kind, subject), not the title
        self.seed = "seed-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"{self.seed}.json"
            path.write_text(json.dumps(crawler_run(["1", "2", "3"], self.seed)))
            ingest_run(self.conn, path)

    def write(self, directory, stem, doc):
        path = Path(directory) / f"{stem}.json"
        path.write_text(json.dumps(doc))
        return path

    def count(self, table, column="run_id", value=None):
        return self.conn.execute(f"SELECT count(*) AS n FROM {table} WHERE {column}=%s", (value,)).fetchone()["n"]

    def make_doc(self, source_ids, title=None, relations=None, kind="product_launch",
                 subject_key=None, **overrides):
        title = title or f"GPT-X {self.uid}"
        event = {"kind": kind, "title": title, "summary": "s", "primary_org": "OpenAI",
                 "subject_key": self.subject if subject_key is None else subject_key,
                 "occurred_at": "2026-09-10T00:00:00+00:00", "occurrence_status": "occurred",
                 "confidence": 0.9, "source_ids": source_ids}
        event.update(overrides)
        if relations:
            event["relations"] = relations
        cands = [candidate(s, self.seed) for s in source_ids]
        return assemble_extraction(cands, [{"events": [event]}], meta())

    def test_ingest_inserts_run_events_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = self.make_doc(["1", "2"])
            rid = ingest_extraction(self.conn, self.write(tmp, "extract-A-" + uuid.uuid4().hex, doc))["run_id"]
            self.assertEqual(self.count("extraction_runs", value=rid), 1)
            self.assertEqual(self.conn.execute(
                "SELECT event_count FROM extraction_runs WHERE run_id=%s", (rid,)).fetchone()["event_count"], 1)
            self.assertEqual(self.conn.execute(
                "SELECT count(*) AS n FROM extracted_event_sources WHERE event_id IN "
                "(SELECT event_id FROM extracted_events WHERE first_extraction_run_id=%s)", (rid,)).fetchone()["n"], 2)

    def test_idempotent_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "extract-R-" + uuid.uuid4().hex, self.make_doc(["1"]))
            first = ingest_extraction(self.conn, path)
            second = ingest_extraction(self.conn, path)
            self.assertFalse(first["reused"])
            self.assertTrue(second["reused"])

    def test_same_run_id_different_content_rejected(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            stem = "extract-C-" + uuid.uuid4().hex
            ingest_extraction(self.conn, self.write(a, stem, self.make_doc(["1"])))
            with self.assertRaises(ValueError):
                ingest_extraction(self.conn, self.write(b, stem, self.make_doc(["1", "2"])))

    def test_cross_run_same_event_dedups_to_one_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            r1 = ingest_extraction(self.conn, self.write(tmp, "extract-X1-" + uuid.uuid4().hex, self.make_doc(["1"])))
            r2 = ingest_extraction(self.conn, self.write(
                tmp, "extract-X2-" + uuid.uuid4().hex,
                self.make_doc(["2"], title=f"GPT-X is here {self.uid}")))
            # same (org, kind, subject) -> same dedup_key/event_id: one event row, two runs,
            # both source links. The title is display only and no longer part of identity.
            eid = event_id_for(dedup_key("org:openai", "product_launch", self.subject))
            self.assertEqual(self.conn.execute(
                "SELECT count(*) AS n FROM extracted_events WHERE event_id=%s", (eid,)).fetchone()["n"], 1)
            self.assertEqual(self.conn.execute(
                "SELECT count(*) AS n FROM extracted_event_sources WHERE event_id=%s", (eid,)).fetchone()["n"], 2)
            self.assertNotEqual(r1["run_id"], r2["run_id"])

    def test_relation_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            event_ga = {"kind": "availability_change", "title": f"Agents GA {self.uid}",
                        "primary_org": "OpenAI", "subject_key": f"agents-api-{self.uid}",
                        "occurrence_status": "occurred", "source_ids": ["1"],
                        "relations": [{"to_index": 1, "kind": "follows", "rationale": "GA follows beta"}]}
            event_beta = {"kind": "product_launch", "title": f"Agents beta {self.uid}",
                          "primary_org": "OpenAI", "subject_key": f"agents-api-beta-{self.uid}",
                          "occurrence_status": "occurred", "source_ids": ["2"]}
            doc = assemble_extraction([candidate("1", self.seed), candidate("2", self.seed)],
                                      [{"events": [event_ga, event_beta]}], meta())
            rid = ingest_extraction(self.conn, self.write(tmp, "extract-REL-" + uuid.uuid4().hex, doc))["run_id"]
            rel = self.conn.execute(
                "SELECT kind FROM extracted_event_relations WHERE extraction_run_id=%s", (rid,)).fetchone()
            self.assertEqual(rel["kind"], "follows")

    def test_new_vocabulary_columns_land_on_the_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            ingest_extraction(self.conn, self.write(tmp, "extract-V-" + uuid.uuid4().hex, self.make_doc(["1"])))
            row = self.conn.execute(
                "SELECT kind, kind_vocabulary, subject_key, identity_confidence, primary_org_id,"
                " unresolved_reason FROM extracted_events WHERE event_id=%s",
                (event_id_for(dedup_key("org:openai", "product_launch", self.subject)),)).fetchone()
            self.assertEqual(row, {"kind": "product_launch", "kind_vocabulary": EVENT_KIND_VOCABULARY,
                                   "subject_key": self.subject, "identity_confidence": "high",
                                   "primary_org_id": "org:openai", "unresolved_reason": None})

    def test_unresolved_kind_lands_as_null_plus_a_reason(self):
        """rule:no-other-bucket end to end: an unclassifiable event is counted, not bucketed."""
        with tempfile.TemporaryDirectory() as tmp:
            doc = self.make_doc(["1"], kind="launch")  # a term from the old free-text list
            rid = ingest_extraction(self.conn, self.write(tmp, "extract-U-" + uuid.uuid4().hex, doc))["run_id"]
            row = self.conn.execute(
                "SELECT kind, unresolved_reason, identity_confidence FROM extracted_events"
                " WHERE first_extraction_run_id=%s", (rid,)).fetchone()
            self.assertIsNone(row["kind"])
            self.assertIn("launch", row["unresolved_reason"])
            self.assertEqual(row["identity_confidence"], "low")  # never merged with another unknown

    def test_unresolvable_organisation_drops_the_event_before_the_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(resolve_org("Nonesuch Labs"))
            doc = self.make_doc(["1"], primary_org="Nonesuch Labs")
            result = ingest_extraction(self.conn, self.write(tmp, "extract-O-" + uuid.uuid4().hex, doc))
            self.assertEqual(doc["dropped"], {"unresolved_org": 1})
            self.assertEqual(doc["unresolved_orgs"], ["Nonesuch Labs"])
            self.assertEqual(result["events"], 0)
            self.assertEqual(self.conn.execute(
                "SELECT count(*) AS n FROM extracted_events WHERE first_extraction_run_id=%s",
                (result["run_id"],)).fetchone()["n"], 0)

    def test_source_must_exist_in_collection_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = self.make_doc(["999"])  # 999 was never collected
            with self.assertRaises(Exception):
                ingest_extraction(self.conn, self.write(tmp, "extract-FK-" + uuid.uuid4().hex, doc))

    def test_no_scraper_label_leaks(self):
        with tempfile.TemporaryDirectory() as tmp:
            rid = ingest_extraction(self.conn, self.write(tmp, "extract-L-" + uuid.uuid4().hex, self.make_doc(["1"])))["run_id"]
            blob = repr(self.conn.execute("SELECT * FROM extracted_events").fetchall())
            self.assertNotIn("SECRET", blob)


if __name__ == "__main__":
    unittest.main()
