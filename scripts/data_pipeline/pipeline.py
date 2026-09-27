"""Shared primitives: canonical hashing, row insertion, and the ontology import.

This was the five-batch input importer - normalize a bundle, insert it under a
data_batch, compute metrics, compute a progress value. Those tables retired with
migration 020; what every surviving module actually imported from here was
`digest` and `import_ontology`, so that is what is left.
"""

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE_VERSION = 'local-pipeline-1'
def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be an ISO string with timezone')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timestamp timezone is required')
    return dt.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def deduplicate(rows, keys):
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Each row must be an object')
        key = tuple(row[k] for k in keys)
        if any(not isinstance(k, str) or not k for k in key):
            raise ValueError('Identity fields must be nonempty strings')
        if key in result and result[key] != row:
            raise ValueError(f'Conflicting duplicate identity: {key}')
        result[key] = row
    return [result[k] for k in sorted(result)]


def insert_rows(conn, table, rows):
    from psycopg import sql
    from psycopg.types.json import Jsonb
    for row in rows:
        query = sql.SQL('INSERT INTO public.{} ({}) VALUES ({})').format(
            sql.Identifier(table), sql.SQL(',').join(map(sql.Identifier, row)),
            sql.SQL(',').join(sql.Placeholder() for _ in row))
        conn.execute(query, [Jsonb(v) if isinstance(v, dict) else v for v in row.values()])


def import_ontology(conn, path=None):
    from psycopg.types.json import Jsonb
    path = Path(path or ROOT / 'datasets/ontology/releases/v1.0.0').resolve()
    # Use the sealed package's existing semantic validator, then hash the actual bytes we import.
    result = subprocess.run(['node', '--input-type=module', '-e',
        "import {verifyOntology} from './scripts/lib/ontology-release.mjs'; console.log(JSON.stringify(await verifyOntology(process.argv[1])));", str(path)],
        cwd=ROOT, text=True, capture_output=True, check=True)
    verified = json.loads(result.stdout)
    raw_manifest = (path / 'manifest.json').read_bytes()
    sha = hashlib.sha256(raw_manifest).hexdigest()
    if sha != verified['manifest_sha256']:
        raise ValueError('Ontology changed during validation')
    manifest = json.loads(raw_manifest)
    records = {}
    for name in ('concepts', 'relations'):
        raw = (path / f'{name}.jsonl').read_bytes()
        expected = next(f['sha256'] for f in manifest['files'] if f['path'] == f'{name}.jsonl')
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Ontology content changed after validation')
        records[name] = [json.loads(line) for line in raw.splitlines() if line]
    version = manifest['version']
    with conn.transaction():
        conn.execute('SELECT pg_advisory_xact_lock(7543001)')
        old = conn.execute('SELECT * FROM ontology_releases WHERE version=%s', (version,)).fetchone()
        if old:
            if old['manifest_sha256'] != sha or old['sealed_at'] is None:
                raise ValueError('Conflicting or unsealed ontology version')
            return {'version': version, 'reused': True, 'concepts': len(records['concepts']), 'relations': len(records['relations'])}
        insert_rows(conn, 'ontology_releases', [{'version': version, 'schema_version': manifest['schema_version'], 'manifest_sha256': sha}])
        with conn.cursor().copy('COPY ontology_concepts (ontology_version,id,kind,label_en,label_zh_cn,origin,translation_status,scope_status,definition,record_sha256) FROM STDIN') as copier:
            for r in records['concepts']:
                copier.write_row((version, r['id'], r['kind'], r['label_en'], r['label_zh_cn'], r['origin'], r['translation_status'], r['scope_status'], Jsonb(r['definition']) if r['definition'] is not None else None, digest(r)))
        with conn.cursor().copy('COPY ontology_relations (ontology_version,id,kind,parent_id,child_id,view,display_order) FROM STDIN') as copier:
            for r in records['relations']:
                copier.write_row((version, r['id'], r['kind'], r['parent_id'], r['child_id'], r['view'], r['order']))
        conn.execute('UPDATE ontology_releases SET sealed_at=now() WHERE version=%s', (version,))
    return {'version': version, 'reused': False, 'concepts': len(records['concepts']), 'relations': len(records['relations'])}


