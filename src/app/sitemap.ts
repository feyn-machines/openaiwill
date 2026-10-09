import type { MetadataRoute } from "next";
import { LANGUAGES, type Language } from "@/lib/i18n";
import { absoluteUrl } from "@/lib/seo";
import { FIXED_PATHS, UPDATE_LANGUAGES, detailPages } from "@/lib/site-pages";
import { manifest } from "@/lib/snapshot";
import publishedArticles from "@/content/articles.json";

export const dynamic = "force-dynamic";

type Page = { path: string; lastModified?: string; languages?: readonly Language[] };

/**
 * One entry per page per language, each naming its counterpart. The detail
 * addresses come from the release the routes answer from, so nothing here can
 * be a 404.
 *
 * `lastModified` is when the data behind a page was produced: the snapshot's
 * generation time, or for an update the time it happened. It is left out
 * rather than invented when there is no snapshot.
 *
 * Only pages with something of their own are listed: an occupation no update
 * has reached is left out (its page asks not to be indexed), and an update is
 * listed once because its words are the same in every language.
 */
let kept: { key: string; entries: MetadataRoute.Sitemap } | null = null;

export default function sitemap(): MetadataRoute.Sitemap {
  const built = manifest()?.generated_at;
  // The list changes only when another data release is loaded.
  const key = built ?? "";
  if (kept?.key !== key) kept = { key, entries: entries(built) };
  return kept.entries;
}

function entries(built: string | undefined): MetadataRoute.Sitemap {
  const pages: Page[] = [
    ...FIXED_PATHS.map((path) => ({ path, lastModified: built })),
    ...detailPages.markets().map((id) => ({ path: `/markets/${id}`, lastModified: built })),
    ...detailPages.occupationGroups().map((id) => ({ path: `/occupations/g/${id}`, lastModified: built })),
    ...detailPages.reachedOccupations().map((code) => ({ path: `/occupations/${code}`, lastModified: built })),
    ...detailPages.work().map((id) => ({ path: `/work/${id}`, lastModified: built })),
    ...detailPages.topics().map(({ slug, latest }) => ({ path: `/topics/${slug}`, lastModified: latest ?? built })),
    ...detailPages.updates().map(({ id, occurredAt }) => ({ path: `/updates/${id}`, lastModified: occurredAt ?? built, languages: UPDATE_LANGUAGES })),
    // The article pages are built ahead from documents the server does not carry,
    // so the list comes from the index written beside the build.
    ...publishedArticles.map((item) => ({ path: `/articles/${item.slug}`, lastModified: item.date })),
  ];
  return pages.flatMap(({ path, lastModified, languages = LANGUAGES }) =>
    languages.map((language) => ({
      url: absoluteUrl(language, path),
      ...(lastModified ? { lastModified: toTheSecond(lastModified) } : {}),
      alternates: {
        languages: {
          ...Object.fromEntries(languages.map((l) => [l, absoluteUrl(l, path)])),
          "x-default": absoluteUrl("en", path),
        },
      },
    })),
  );
}

// The data carries times to the microsecond; a sitemap reader expects a date or a time to the second.
function toTheSecond(time: string): string {
  return time.replace(/(T\d{2}:\d{2}:\d{2})\.\d+/, "$1");
}
