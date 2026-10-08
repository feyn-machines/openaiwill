import {
  activities,
  chainEvents,
  groupSlug,
  markets,
  marketSlug,
  occupationSlug,
  occupations,
  progress,
} from "./snapshot";
import { workSlug } from "./routes";

/** Pages that exist whatever the snapshot holds. */
export const FIXED_PATHS = ["/", "/markets", "/occupations", "/updates", "/voices", "/articles", "/whitepaper", "/privacy", "/terms"] as const;

/**
 * The detail pages of the loaded data release. Each detail route looks its
 * entity up in the same release and answers 404 when it is absent, and the
 * sitemap lists exactly this list, so the sitemap cannot name a page that does
 * not exist.
 */
export const detailPages = {
  markets: () => markets().map((market) => marketSlug(market.id)),
  occupations: () => occupations().map((row) => occupationSlug(row.occupation_id)),
  /** Occupations an update has reached: the ones a search engine is told about. */
  reachedOccupations: () => occupations().filter((row) => row.assessed > 0).map((row) => occupationSlug(row.occupation_id)),
  occupationGroups: () => Object.keys(progress()?.groups ?? {}).map(groupSlug),
  /** Only work an update has reached has a page of its own. */
  work: () => activities().filter((a) => a.evidence_rows && a.level).map((a) => workSlug(a.activity_id)),
  updates: () => chainEvents().map((e) => ({ id: e.event_id, occurredAt: e.occurred_at ?? null })),
};

/** An update keeps its original words in every language, so it is listed once. */
export const UPDATE_LANGUAGES = ["en"] as const;
