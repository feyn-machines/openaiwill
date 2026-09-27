"""Real PostgreSQL regressions for the local migration and immutability contract."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg
from psycopg import sql

from data_pipeline.db import connect, migrate


class DatabaseGuardsTest(unittest.TestCase):
    """The migration contract and the sealed catalogue, against a real server.

    This used to also cover the batch immutability contract - a data_batch that
    reached `ready` could not be edited, and its children were frozen with it.
    Those tables retired with migration 020; the catalogue guards did not, and
    they are the ones that matter now: the ontology release is the world every
    number on the site is counted against, and a sealed release that can be
    edited afterwards makes every published figure unreproducible.
    """

    @classmethod
    def setUpClass(cls):
        cls.database = "openaiwill_guard_test_" + uuid.uuid4().hex
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
        self.key = uuid.uuid4().hex
        self.conn.execute("INSERT INTO ontology_releases (version,schema_version,manifest_sha256) "
                          "VALUES (%s,'1',%s)", (self.key, self.key * 2))

    def seal(self):
        self.conn.execute("UPDATE ontology_releases SET sealed_at=now() "
                          "WHERE version=%s AND sealed_at IS NULL", (self.key,))

    def concept(self, concept_id="c1"):
        self.conn.execute(
            """INSERT INTO ontology_concepts
               (ontology_version,id,kind,label_en,origin,translation_status,scope_status,record_sha256)
               VALUES (%s,%s,'work','Original','test','not_translated','in_scope',%s)""",
            (self.key, concept_id, self.key * 2))

    def test_migration_replay_and_changed_hash_rejection(self):
        self.assertEqual(migrate(self.conn), [])
        with self.conn.transaction(force_rollback=True):
            self.conn.execute("UPDATE schema_migrations SET sha256=%s WHERE version="
                              "(SELECT min(version) FROM schema_migrations)", ("f" * 64,))
            with self.assertRaisesRegex(ValueError, "changed or is missing"):
                migrate(self.conn)

    def test_concurrent_initial_migrations_apply_once(self):
        database = "openaiwill_migration_test_" + uuid.uuid4().hex
        with connect() as admin:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
        barrier = threading.Barrier(2)

        def apply():
            with connect(database) as conn:
                barrier.wait(timeout=5)
                return migrate(conn)

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(apply) for _ in range(2)]
                results = [future.result(timeout=10) for future in futures]
            self.assertEqual(sum(bool(result) for result in results), 1)
            with connect(database) as conn:
                self.assertEqual(migrate(conn), [])
                # A table only the LAST migration creates, so a chain that
                # stopped halfway fails here instead of passing on a schema
                # that happens to be readable.
                self.assertIsNotNone(
                    conn.execute("SELECT to_regclass('public.judgment_checkpoints') AS last_table")
                    .fetchone()["last_table"])
        finally:
            with connect() as admin:
                admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))

    def test_catalogue_records_reject_edits_and_post_seal_appends(self):
        self.concept()
        for statement in (
            "UPDATE ontology_concepts SET label_en='Changed' WHERE ontology_version=%s",
            "DELETE FROM ontology_concepts WHERE ontology_version=%s",
        ):
            with self.subTest(statement=statement):
                with self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                    self.conn.execute(statement, (self.key,))
        self.seal()
        with self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
            self.concept("late")

    def test_every_catalogue_table_rejects_sealed_appends(self):
        self.seal()
        for table in ("ontology_concepts", "ontology_relations"):
            with self.subTest(table=table):
                with self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                    self.conn.execute(
                        sql.SQL("INSERT INTO {} (ontology_version) VALUES (%s)")
                        .format(sql.Identifier(table)), (self.key,))

    def test_release_only_allows_one_seal_with_unchanged_metadata(self):
        with self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
            self.conn.execute("UPDATE ontology_releases SET imported_at=now(),sealed_at=now() "
                              "WHERE version=%s", (self.key,))
        self.seal()
        for change in ("sealed_at=NULL", "sealed_at=now()", "version=version"):
            with self.subTest(change=change):
                with self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                    self.conn.execute(
                        sql.SQL("UPDATE ontology_releases SET " + change + " WHERE version=%s"),
                        (self.key,))

    def test_truncate_cannot_bypass_the_catalogue_guard(self):
        """An UPDATE guard that TRUNCATE walks around is not a guard."""
        self.concept()
        with self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
            self.conn.execute("TRUNCATE ontology_concepts CASCADE")


if __name__ == "__main__":
    unittest.main()
