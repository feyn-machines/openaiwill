"""Extract deduplicated events from the collection store into the event layer.

This is the data-flow seam between the raw collection store (collected_sources /
collected_captures, produced by the crawler) and the independent event layer
(extracted_events and friends). The model call lives in `deepseek.py`; this module
is the deterministic spine around it:

  load_candidates ->  select_candidates  (pure: drop reposts/replies, dedup)
                  ->  [deepseek.extract_events]  (the only non-deterministic step)
                  ->  assemble_extraction  (pure: model output -> immutable doc)
                  ->  build_extraction_rows (pure: doc -> event-layer rows)
                  ->  ingest_extraction     (idempotent DB write)

No market scope, weights, metrics or progress live here; those belong to a later
calculation batch that projects FROM this layer. Social metrics are never copied:
provenance points back into the collection store through extracted_event_sources.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from . import ontology_schema
from .pipeline import digest  # psycopg is imported lazily inside ingest_extraction

EXTRACTION_VERSION = "event-extraction-2"
# The kinds come from the schema, which is also what migration 006 projects
# its CHECK from; a literal set here would be a second, silently diverging list.
EVENT_KINDS = frozenset(ontology_schema.term_ids("event_kind"))
EVENT_KIND_VOCABULARY = ontology_schema.EVENT_KIND_VOCABULARY
OCCURRENCE = {"unknown", "scheduled", "occurred", "postponed", "cancelled"}
RELATION_KINDS = {"part_of", "follows", "supersedes", "refines", "duplicate_of"}
SOURCE_ROLES = {"primary", "corroborating", "context"}

# Organisations are ids, never free text (rule:org-must-be-id). The same company
# arrived under two spellings - 'xAI' on 9 events and 'xAI / SpaceXAI' on 14 - so
# every per-company aggregate was wrong and nothing said so. This table is both the
# alias index resolve_org uses and the seed for public.org_registry; a seeding
# script reads it as-is.
ROOT = Path(__file__).resolve().parents[2]


def _load_organizations():
    """The one organisation registry, read from datasets/ontology/data/organizations.json.

    There used to be two: this dict and the JSON file, hand-maintained in parallel.
    They had already diverged - each knew aliases the other did not - so an event
    naming an alias only the registry knew was silently dropped. That is precisely
    the failure rule:org-must-be-id exists to prevent, so there is now one file.
    """
    path = ROOT / "datasets/ontology/data/organizations.json"
    document = json.loads(path.read_text())
    return {
        org["org_id"]: {
            "canonical_name_en": org["name_en"],
            "canonical_name_zh_cn": org.get("name_zh_cn"),
            "aliases": list(org.get("aliases", [])),
        }
        for org in document["organizations"]
    }


ORGANIZATIONS = _load_organizations()


def _normalize_org(name):
    """Fold the spellings that differ only in punctuation or case into one key."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).split())


def _org_alias_index():
    index = {}
    for org_id, body in ORGANIZATIONS.items():
        for alias in [org_id, body["canonical_name_en"], body.get("canonical_name_zh_cn"),
                      *body.get("aliases", [])]:
            key = _normalize_org(alias)
            if not key:
                continue
            if index.get(key, org_id) != org_id:
                raise ValueError(f"Alias {alias!r} claimed by {index[key]} and {org_id}")
            index[key] = org_id
    return index


ORG_ALIASES = _org_alias_index()


def resolve_org(name):
    """Free-text organisation name -> org id, or None when it is not one we know.

    Never guesses. An unresolved name means the event is dropped and counted, which
    is recoverable (add the alias, re-extract); attaching it to the nearest-looking
    company would be a wrong aggregate that nobody notices.
    """
    return ORG_ALIASES.get(_normalize_org(name))


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def _hashable(row):
    """A JSON-serializable view of a row for record hashing (datetimes -> ISO)."""
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items()}


def _slug(text):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:120] or None


def dedup_key(primary_org_id, kind, subject_key):
    """Identity of one real event: (org, kind, subject), never its wording.

    Identity used to be slug(org + title). A title is natural language, so one
    announcement written four ways became four events - "Qwen3.8-Max-0902 tops
    CodeArena WebDev" split into 4, "Apsara Conference 2026" into 4.
    """
    key = _slug(f"{primary_org_id or 'unknown'}|{kind or 'unresolved'}|{subject_key}")
    return key or ("event-" + digest([primary_org_id, kind, subject_key])[:24])


def title_dedup_key(primary_org_id, title):
    """Fallback identity when the model could not name the subject of the event."""
    return _slug(f"{primary_org_id or 'unknown'}-{title}") or ("event-" + digest(title or "")[:24])


OCCURRENCE_WINDOW_DAYS = 14


def event_times(occurred, scheduled, published):
    """(occurred_at, scheduled_for) with an announcement of something still to come kept in the past.

    A post cannot report what has not happened yet: a date later than the newest
    source post is the date the thing is planned for. It becomes `scheduled_for`
    (unless one was given) and the event is dated by that post, so nothing is
    placed in the future."""
    latest = max((p for p in published if p), default=None)
    if occurred and latest and occurred > latest:
        return latest, scheduled or occurred
    return occurred, scheduled


def occurrence_suffix(key, occurred_at, known_occurrences):
    """Separate a recurring event from its earlier occurrences.

    rule:event-identity-is-triple makes identity (org, kind, subject). An annual
    conference keeps all three year after year, so without this the 2027 Apsara
    Conference merges into the 2026 one and the newer date silently disappears.
    Two sightings more than a fortnight apart are two occurrences, and the later
    one takes the year - the same convention the extraction prompt states.

    `known_occurrences` maps dedup_key to the dates already recorded for it. The
    caller supplies it, so assembly stays a pure function of its inputs.
    """
    if not occurred_at or not known_occurrences:
        return ""
    seen = known_occurrences.get(key) or []
    if not seen:
        return ""
    window = timedelta(days=OCCURRENCE_WINDOW_DAYS)
    if any(abs(occurred_at - earlier) <= window for earlier in seen):
        return ""
    return f"-{occurred_at.year}"


def event_identity(primary_org_id, kind, subject_key, title):
    """(dedup_key, identity_confidence) for one event.

    With a subject and a kind the identity is the triple and confidence is high.
    Without a subject the title slug is all that is left, so the row carries 'low'
    and says why any later duplicate is not our miscount but a missing subject_key.

    An unresolved kind never merges: two events we could not classify are not
    thereby the same event, and collapsing them would hide the gap instead of
    counting it. Such a row keeps the triple shape but is disambiguated by its
    title and marked 'low', so a later rubric fix produces one event per real one.
    """
    if not subject_key:
        return title_dedup_key(primary_org_id, title), "low"
    if kind is None:
        key = dedup_key(primary_org_id, kind, subject_key)
        return f"{key}-{digest(title or '')[:12]}", "low"
    return dedup_key(primary_org_id, kind, subject_key), "high"


def _subject_key(value):
    """Canonical subject slug: 'Wan 3.0' and 'wan-3.0' are the same thing."""
    return _slug(value) if isinstance(value, str) else None


def _kind_of(raw):
    """(kind, unresolved_reason) for one model event.

    There is no "other" bucket any more (rule:no-other-bucket): 23.7% of events
    used to land in it, which hid the missing categories instead of counting them.
    An undecided kind is null plus a reason, and the reason is never empty - the
    extracted_events CHECK rejects a null kind without one.
    """
    value = raw.get("kind")
    kind = value.strip() if isinstance(value, str) else None
    if kind in EVENT_KINDS:
        return kind, None
    model_reason = raw.get("unresolved_reason")
    model_reason = model_reason.strip() if isinstance(model_reason, str) else ""
    if value is None or kind == "":
        return None, model_reason or "model returned no kind and no unresolved_reason"
    return None, f"model returned unknown kind {value!r}"


def event_id_for(key):
    """Deterministic event id from the dedup key (same event -> same id across runs)."""
    return "ev-" + digest(key)[:40]


# --- candidate selection (pure) -------------------------------------------------

def select_candidates(rows, window=None):
    """Filter joined source+capture rows down to extraction candidates.

    Drops reposts and replies (not original updates), keeps the latest capture per
    (platform, source_id), and optionally restricts to a [start, end) publish window.
    `rows` are dicts with source and capture fields already joined.
    """
    start = _iso(window["start"]) if window and window.get("start") else None
    end = _iso(window["end"]) if window and window.get("end") else None
    best = {}
    for row in rows:
        if row.get("is_repost") or row.get("is_reply"):
            continue
        published = _iso(row["published_at"])
        if start and published < start:
            continue
        if end and published >= end:
            continue
        key = (row.get("platform", "x"), row["source_id"])
        captured = _iso(row.get("captured_at"))
        current = best.get(key)
        if current is None or (captured and captured > current["_captured"]):
            best[key] = {
                "run_id": row["run_id"], "source_id": row["source_id"],
                "platform": row.get("platform", "x"), "handle": row.get("account_handle"),
                "company": row.get("company"), "url": row.get("canonical_url"),
                "published_at": published, "excerpt": row.get("public_excerpt") or "",
                "metrics": row.get("metrics") or {}, "_captured": captured,
            }
    candidates = [{k: v for k, v in c.items() if k != "_captured"} for c in best.values()]
    candidates.sort(key=lambda c: (c["published_at"], c["source_id"]))
    return candidates


def load_known_occurrences(conn):
    """Dates already recorded against each event identity.

    Feeds assemble_extraction's occurrence window so a recurring event is not
    merged into its own earlier instance. Read here rather than inside assembly,
    which stays a pure function of what it is given.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """SELECT dedup_key, occurred_at FROM public.extracted_events
               WHERE occurred_at IS NOT NULL""")
        known = {}
        for row in cursor.fetchall():
            known.setdefault(row["dedup_key"], []).append(row["occurred_at"])
    return known


def load_candidates(conn, window=None, collection_run_ids=None, limit=None):
    """Read extraction candidates from the collection store (latest capture per post)."""
    clauses, params = ["NOT s.is_repost", "NOT s.is_reply"], {}
    if collection_run_ids:
        clauses.append("s.run_id = ANY(%(runs)s)")
        params["runs"] = list(collection_run_ids)
    if window and window.get("start"):
        clauses.append("s.published_at >= %(start)s")
        params["start"] = _iso(window["start"])
    if window and window.get("end"):
        clauses.append("s.published_at < %(end)s")
        params["end"] = _iso(window["end"])
    sql = f"""
        SELECT s.run_id, s.source_id, s.platform, s.account_handle, s.company,
               s.canonical_url, s.is_reply, s.is_repost, s.published_at,
               c.captured_at, c.public_excerpt, c.metrics
        FROM collected_sources s
        JOIN collected_captures c ON c.run_id = s.run_id AND c.source_id = s.source_id
        WHERE {' AND '.join(clauses)}
        ORDER BY s.published_at
    """
    rows = conn.execute(sql, params).fetchall()
    candidates = select_candidates(rows, window)
    return candidates[:limit] if limit else candidates


# --- assembly (pure): model output + candidates -> immutable extraction doc -----

def assemble_extraction(candidates, batches, meta, known_occurrences=None):
    """Turn per-batch model output into one immutable, deterministic extraction doc.

    `batches` is a list of {"events": [...]} objects (one per model call). Each model
    event references candidate posts by `source_ids` and may reference sibling events
    in the same batch by `relations: [{to_index, kind, ...}]`. Events are deduped
    across the whole doc by dedup_key, which is now the identity triple rather than
    the title; the first occurrence wins.

    Events that cannot be landed - no title, no collected source, no resolvable
    organisation - are dropped and counted in doc["dropped"], never repaired by
    guessing. doc["unresolved_orgs"] lists the names that need an alias.

    `known_occurrences` maps dedup_key to dates already recorded for that identity,
    so a recurring event more than a fortnight after its last sighting becomes a
    new occurrence rather than merging into the old one. Passing it in rather than
    querying keeps this function pure and testable.
    """
    by_source = {c["source_id"]: c for c in candidates}
    events, index = [], {}
    dropped, unresolved_orgs = {}, set()

    def drop(reason):
        dropped[reason] = dropped.get(reason, 0) + 1

    for batch in batches:
        local = []
        for raw in batch.get("events", []):
            title = (raw.get("title") or "").strip()
            if not title:
                drop("no_title")
                continue
            sources = []
            for sid in raw.get("source_ids", []):
                cand = by_source.get(str(sid))
                if cand:
                    sources.append({"run_id": cand["run_id"], "source_id": cand["source_id"],
                                    "role": "primary"})
            if not sources:
                drop("no_known_source")  # every event must trace to a collected post
                continue
            org = (raw.get("primary_org") or "").strip() or None
            org_id = resolve_org(org)
            if org_id is None:
                # An event is identified by its organisation, so a wrong one is a
                # wrong per-company aggregate. Dropping it is recoverable: add the
                # alias to ORGANIZATIONS and re-extract.
                if org:
                    unresolved_orgs.add(org)
                    drop("unresolved_org")
                else:
                    drop("missing_org")
                continue
            kind, unresolved_reason = _kind_of(raw)
            subject_key = _subject_key(raw.get("subject_key"))
            key, identity_confidence = event_identity(org_id, kind, subject_key, title)
            occurred, scheduled = event_times(
                _iso(raw.get("occurred_at")), _iso(raw.get("scheduled_for")),
                [by_source[src["source_id"]]["published_at"] for src in sources])
            key += occurrence_suffix(key, occurred, known_occurrences)
            eid = event_id_for(key)
            status = raw.get("occurrence_status") if raw.get("occurrence_status") in OCCURRENCE else "occurred"
            event = {
                "event_id": eid, "dedup_key": key, "kind": kind,
                "kind_vocabulary": EVENT_KIND_VOCABULARY, "unresolved_reason": unresolved_reason,
                "subject_key": subject_key, "identity_confidence": identity_confidence,
                "title": title,
                "summary": (raw.get("summary") or title).strip(),
                "primary_org": org, "primary_org_id": org_id,
                "announced_at": _iso(raw.get("announced_at")).isoformat() if raw.get("announced_at") else None,
                "occurred_at": occurred.isoformat() if occurred else None,
                "scheduled_for": scheduled.isoformat() if scheduled else None,
                "occurrence_status": status,
                "confidence": _confidence(raw.get("confidence")),
                "sources": sources, "categories": _categories(raw.get("categories")),
                "relations": [], "_raw_relations": raw.get("relations", []),
            }
            local.append(event)
            if key not in index:
                index[key] = event
                events.append(event)
            else:
                _merge_sources(index[key], event["sources"])
                for cat in event["categories"]:
                    if cat not in index[key]["categories"]:
                        index[key]["categories"].append(cat)
        # resolve within-batch relations by local index -> dedup_key
        for pos, event in enumerate(local):
            for rel in event.pop("_raw_relations", []):
                target = _relation_target(rel, local, pos)
                if target and rel.get("kind") in RELATION_KINDS and target["dedup_key"] != event["dedup_key"]:
                    index[event["dedup_key"]]["relations"].append({
                        "to_event_id": target["event_id"], "kind": rel["kind"],
                        "rationale": (rel.get("rationale") or "").strip() or "model-proposed",
                        "confidence": _confidence(rel.get("confidence"))})
    for event in events:
        event.pop("_raw_relations", None)

    doc = {
        "version": EXTRACTION_VERSION, "model": meta["model"],
        "prompt_sha256": meta["prompt_sha256"], "params": meta.get("params", {}),
        # Which rubric produced these classifications; a boundary edited in the
        # semantic layer changes this hash, so two runs are comparable or visibly not.
        "schema_version": ontology_schema.SCHEMA_VERSION,
        "rubric_sha256": ontology_schema.rubric_sha256(),
        "kind_vocabulary": EVENT_KIND_VOCABULARY,
        "collection_run_ids": sorted({c["run_id"] for c in candidates}),
        "window": meta.get("window"), "started_at": meta["started_at"],
        "finished_at": meta.get("finished_at"), "status": meta.get("status", "completed"),
        "candidate_count": len(candidates), "events": events,
        "dropped": dropped, "unresolved_orgs": sorted(unresolved_orgs),
    }
    return doc


def _confidence(value):
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, num))


def _categories(items):
    out = []
    for item in items or []:
        cid = str(item.get("category_id") or "").strip()
        taxonomy = item.get("taxonomy")
        version = str(item.get("taxonomy_version") or "").strip()
        if not cid or taxonomy not in ("ontology", "platform") or not version:
            continue
        out.append({"taxonomy": taxonomy, "taxonomy_version": version, "category_id": cid,
                    "confidence": _confidence(item.get("confidence")),
                    "rationale": (item.get("rationale") or "").strip() or "model-proposed"})
    return out


def _merge_sources(event, new_sources):
    seen = {(s["run_id"], s["source_id"], s["role"]) for s in event["sources"]}
    for src in new_sources:
        key = (src["run_id"], src["source_id"], src["role"])
        if key not in seen:
            seen.add(key)
            event["sources"].append(src)


def _relation_target(rel, local, pos):
    idx = rel.get("to_index")
    if isinstance(idx, int) and 0 <= idx < len(local) and idx != pos:
        return local[idx]
    return None


# --- row building (pure): extraction doc -> event-layer DB rows -----------------

def _check_ingestible(row):
    """Fail here, naming the event, rather than at the CHECK constraint.

    Both conditions are impossible for a doc this module assembled; a hand-edited
    or foreign document is what this catches.
    """
    if row["kind_vocabulary"] != EVENT_KIND_VOCABULARY:
        return  # a legacy-vocabulary row keeps its old values untouched
    if row["kind"] is None and not (row["unresolved_reason"] or "").strip():
        raise ValueError(f"Event {row['event_id']} has no kind and no unresolved_reason")
    if row["kind"] is not None and row["kind"] not in EVENT_KINDS:
        raise ValueError(f"Event {row['event_id']} has kind {row['kind']!r}, not a controlled term")
    if not row["primary_org_id"]:
        raise ValueError(f"Event {row['event_id']} has no primary_org_id")


def build_extraction_rows(doc, run_id):
    """Pure: turn an extraction document into event-layer rows. No I/O."""
    if not isinstance(doc, dict) or doc.get("version") != EXTRACTION_VERSION:
        raise ValueError("Not an event-extraction document")
    if doc.get("status") not in ("completed", "failed") or "events" not in doc:
        raise ValueError("Only a finished extraction can be ingested")

    run = {
        "run_id": run_id,
        "collection_run_ids": doc.get("collection_run_ids", []),
        "model": doc["model"], "prompt_sha256": doc["prompt_sha256"],
        "params": doc.get("params", {}),
        "window_start": _iso(doc["window"]["start"]) if doc.get("window") and doc["window"].get("start") else None,
        "window_end": _iso(doc["window"]["end"]) if doc.get("window") and doc["window"].get("end") else None,
        "started_at": _iso(doc["started_at"]),
        "finished_at": _iso(doc["finished_at"]) if doc.get("finished_at") else None,
        "status": doc["status"], "candidate_count": doc.get("candidate_count"),
        "event_count": len(doc["events"]), "run_sha256": digest(doc),
    }

    events, sources, relations, categories = [], [], [], []
    seen_events, seen_source, seen_rel, seen_cat = set(), set(), set(), set()
    for ev in doc["events"]:
        eid = ev["event_id"]
        if eid not in seen_events:
            seen_events.add(eid)
            row = {
                "event_id": eid, "dedup_key": ev["dedup_key"], "kind": ev["kind"],
                "kind_vocabulary": ev.get("kind_vocabulary") or EVENT_KIND_VOCABULARY,
                "unresolved_reason": ev.get("unresolved_reason"),
                "subject_key": ev.get("subject_key"),
                "identity_confidence": ev.get("identity_confidence"),
                "title": ev["title"], "summary": ev["summary"],
                "primary_org": ev.get("primary_org"), "primary_org_id": ev.get("primary_org_id"),
                "announced_at": _iso(ev.get("announced_at")), "occurred_at": _iso(ev.get("occurred_at")),
                "scheduled_for": _iso(ev.get("scheduled_for")), "occurrence_status": ev["occurrence_status"],
                "first_extraction_run_id": run_id, "confidence": ev.get("confidence"),
            }
            _check_ingestible(row)
            row["record_sha256"] = digest(_hashable(row))
            events.append(row)
        for src in ev.get("sources", []):
            role = src.get("role", "primary")
            role = role if role in SOURCE_ROLES else "primary"
            pk = (eid, src["run_id"], src["source_id"], role)
            if pk in seen_source:
                continue
            seen_source.add(pk)
            sources.append({"event_id": eid, "run_id": src["run_id"],
                            "source_id": src["source_id"], "source_role": role})
        for rel in ev.get("relations", []):
            pk = (eid, rel["to_event_id"], rel["kind"])
            if pk in seen_rel or rel["to_event_id"] == eid:
                continue
            seen_rel.add(pk)
            relations.append({"from_event_id": eid, "to_event_id": rel["to_event_id"],
                              "kind": rel["kind"], "rationale": rel["rationale"],
                              "confidence": rel.get("confidence"), "extraction_run_id": run_id})
        for cat in ev.get("categories", []):
            pk = (eid, cat["taxonomy"], cat["taxonomy_version"], cat["category_id"])
            if pk in seen_cat:
                continue
            seen_cat.add(pk)
            categories.append({"event_id": eid, "taxonomy": cat["taxonomy"],
                               "taxonomy_version": cat["taxonomy_version"], "category_id": cat["category_id"],
                               "method": "ai_deepseek", "confidence": cat.get("confidence"),
                               "rationale": cat["rationale"], "extraction_run_id": run_id})
    return run, events, sources, relations, categories


def ingest_extraction(conn, extraction_path):
    """Idempotently ingest one extraction document into the event layer.

    Re-ingesting the same run (same run_id and identical content) is a no-op; the
    same run_id with different content is rejected. Events already present from an
    earlier run (same event_id) are kept, and only new provenance links are added.
    """
    from psycopg.types.json import Jsonb

    extraction_path = Path(extraction_path)
    doc = json.loads(extraction_path.read_text())
    run_id = extraction_path.stem
    run, events, sources, relations, categories = build_extraction_rows(doc, run_id)

    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(7543005)")
        old = conn.execute("SELECT run_sha256 FROM extraction_runs WHERE run_id=%s", (run_id,)).fetchone()
        if old:
            if old["run_sha256"] != run["run_sha256"]:
                raise ValueError(f"Extraction run {run_id} already ingested with different content")
            return {"run_id": run_id, "reused": True, "events": run["event_count"],
                    "sources": len(sources), "relations": len(relations), "categories": len(categories)}
        conn.execute(
            """INSERT INTO extraction_runs
               (run_id,collection_run_ids,model,prompt_sha256,params,window_start,window_end,
                started_at,finished_at,status,run_sha256,candidate_count,event_count)
               VALUES (%(run_id)s,%(collection_run_ids)s,%(model)s,%(prompt_sha256)s,%(params)s,
                %(window_start)s,%(window_end)s,%(started_at)s,%(finished_at)s,%(status)s,
                %(run_sha256)s,%(candidate_count)s,%(event_count)s)""",
            {**run, "collection_run_ids": Jsonb(run["collection_run_ids"]), "params": Jsonb(run["params"])})
        for e in events:
            conn.execute(
                """INSERT INTO extracted_events
                   (event_id,dedup_key,kind,kind_vocabulary,unresolved_reason,subject_key,
                    identity_confidence,title,summary,primary_org,primary_org_id,announced_at,
                    occurred_at,scheduled_for,occurrence_status,first_extraction_run_id,
                    confidence,record_sha256)
                   VALUES (%(event_id)s,%(dedup_key)s,%(kind)s,%(kind_vocabulary)s,
                    %(unresolved_reason)s,%(subject_key)s,%(identity_confidence)s,%(title)s,
                    %(summary)s,%(primary_org)s,%(primary_org_id)s,%(announced_at)s,
                    %(occurred_at)s,%(scheduled_for)s,%(occurrence_status)s,
                    %(first_extraction_run_id)s,%(confidence)s,%(record_sha256)s)
                   ON CONFLICT (event_id) DO NOTHING""", e)
        for s in sources:
            conn.execute(
                """INSERT INTO extracted_event_sources (event_id,run_id,source_id,source_role)
                   VALUES (%(event_id)s,%(run_id)s,%(source_id)s,%(source_role)s)
                   ON CONFLICT DO NOTHING""", s)
        for r in relations:
            conn.execute(
                """INSERT INTO extracted_event_relations
                   (from_event_id,to_event_id,kind,rationale,confidence,extraction_run_id)
                   VALUES (%(from_event_id)s,%(to_event_id)s,%(kind)s,%(rationale)s,%(confidence)s,%(extraction_run_id)s)
                   ON CONFLICT DO NOTHING""", r)
        for c in categories:
            conn.execute(
                """INSERT INTO extracted_event_categories
                   (event_id,taxonomy,taxonomy_version,category_id,method,confidence,rationale,extraction_run_id)
                   VALUES (%(event_id)s,%(taxonomy)s,%(taxonomy_version)s,%(category_id)s,%(method)s,
                    %(confidence)s,%(rationale)s,%(extraction_run_id)s)
                   ON CONFLICT DO NOTHING""", c)
    return {"run_id": run_id, "reused": False, "events": run["event_count"],
            "sources": len(sources), "relations": len(relations), "categories": len(categories)}
