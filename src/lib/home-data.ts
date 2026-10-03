import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { semanticTerm } from "@/components/semantic-labels";
import { activities, chainEvents, coverage, events, evidence, manifest } from "@/lib/snapshot";

/**
 * Everything the homepage draws, in one compact object the server builds once
 * and hands to the client modules. Every module reads this and nothing else, so
 * a module can be changed or replaced without touching the others.
 *
 * Only work that some update bears on is here: the catalogue total is a number
 * for the text, never a shape on the page.
 */
export type Both = { en: string; zh: string };

export type HomeWork = {
  id: string;
  name: Both;
  market: Both;
  marketId: string;
  /** The ontology `market_group` this work's market belongs to. */
  domainId: string;
  /** Accepted level, 1-5. Work with no accepted evidence is not in the list. */
  level: number;
};

export type HomeUpdate = {
  id: string;
  title: string;
  summary: string;
  org: string;
  /** Days since the window opened; undated updates carry `date: null`. */
  day: number;
  date: string | null;
  url: string | null;
  sources: number;
  kind: Both | null;
  /** The semantic `event_kind` id, e.g. `production_adoption`. */
  kindId: string | null;
  /** Views of the source posts at snapshot time; null when not collected. */
  views: number | null;
  likes: number | null;
};

/** One update bearing on one kind of work. */
export type HomeRow = {
  update: string;
  work: string;
  claimed: number;
  accepted: number;
  /** T3 publisher only, T2 several sources, T1 independent. */
  tier: string;
};

export type HomeData = {
  start: string;
  days: number;
  generatedAt: string;
  orgsTracked: number;
  catalogueWorks: number;
  catalogueDomains: number;
  domains: Record<string, Both>;
  works: HomeWork[];
  updates: HomeUpdate[];
  rows: HomeRow[];
};

const ONTOLOGY_DIR = join(process.cwd(), "datasets", "ontology", "releases", "v1.0.0");

type Concept = { id: string; kind: string; label_en: string; label_zh_cn: string | null };
type Relation = { kind: string; parent_id: string; child_id: string };

function jsonl<T>(name: string): T[] {
  const path = join(ONTOLOGY_DIR, name);
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8").split("\n").filter(Boolean).map((line) => JSON.parse(line) as T);
}

const DAY = 24 * 60 * 60 * 1000;
const dayOf = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));

/**
 * Null when there is no snapshot, or the snapshot has no dated window: the page
 * then says so instead of drawing an empty figure.
 */
export function buildHomeData(): HomeData | null {
  const first = coverage?.collection_window.first;
  const last = coverage?.collection_window.last;
  if (!manifest || !coverage || !first || !last) return null;

  // Domains are sealed ontology concepts, not a prefix cut from a market id.
  const groups = new Map<string, Both>();
  for (const c of jsonl<Concept>("concepts.jsonl")) {
    if (c.kind === "market_group") groups.set(c.id, { en: c.label_en, zh: c.label_zh_cn ?? c.label_en });
  }
  const groupOfMarket = new Map<string, string>();
  for (const r of jsonl<Relation>("relations.jsonl")) {
    if (r.kind === "has_market") groupOfMarket.set(r.child_id, r.parent_id);
  }

  const works: HomeWork[] = [];
  const domains: Record<string, Both> = {};
  for (const a of activities) {
    const domainId = groupOfMarket.get(a.market_id);
    if (!a.evidence_rows || !a.level || !domainId) continue;
    const domain = groups.get(domainId);
    if (!domain) continue;
    domains[domainId] = domain;
    works.push({
      id: a.activity_id,
      name: { en: a.label_en, zh: a.label_zh_cn ?? a.label_en },
      market: { en: a.market_en, zh: a.market_zh_cn ?? a.market_en },
      marketId: a.market_id,
      domainId,
      level: Math.round(a.level),
    });
  }
  const known = new Set(works.map((w) => w.id));

  const rows: HomeRow[] = [];
  const used = new Set<string>();
  for (const r of evidence) {
    if (r.level == null || r.observed_level == null || !known.has(r.activity_id)) continue;
    used.add(r.event_id);
    rows.push({ update: r.event_id, work: r.activity_id, claimed: r.observed_level, accepted: r.level, tier: r.evidence_tier });
  }

  const start = dayOf(first);
  const days = Math.round((dayOf(last) - start) / DAY) + 1;
  const detail = new Map(events.map((e) => [e.event_id, e]));
  const updates: HomeUpdate[] = [];
  for (const e of chainEvents) {
    if (!used.has(e.event_id)) continue;
    const more = detail.get(e.event_id);
    const term = semanticTerm("event_kind", more?.kind);
    const date = e.occurred_at ? e.occurred_at.slice(0, 10) : null;
    const day = date ? Math.min(days - 1, Math.max(0, Math.round((dayOf(date) - start) / DAY))) : days - 1;
    updates.push({
      id: e.event_id,
      title: e.title,
      summary: e.summary,
      org: e.org_name ?? "",
      day,
      date,
      url: e.source_urls[0] ?? null,
      sources: e.source_urls.length,
      kind: term?.en ? { en: term.en, zh: term["zh-CN"] ?? term.en } : null,
      kindId: more?.kind ?? null,
      views: more?.attention?.views ?? null,
      likes: more?.attention?.likes ?? null,
    });
  }

  return {
    start: first.slice(0, 10),
    days,
    generatedAt: manifest.generated_at.slice(0, 10),
    orgsTracked: coverage.events_by_organisation.length,
    catalogueWorks: coverage.activities_total,
    catalogueDomains: groups.size,
    domains,
    works,
    updates,
    rows,
  };
}
