import type { MetadataRoute } from "next";
import { LANGUAGES } from "@/lib/i18n";
import { absoluteUrl } from "@/lib/seo";
import { FIXED_PATHS, detailPages } from "@/lib/site-pages";
import { manifest } from "@/lib/snapshot";

type Page = { path: string; lastModified?: string };

/**
 * One entry per page per language, each naming its counterpart. The list is
 * the one the routes prerender from, so nothing here can be a 404.
 *
 * `lastModified` is when the data behind a page was produced: the snapshot's
 * generation time, or for an update the time it happened. It is left out
 * rather than invented when there is no snapshot.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const built = manifest?.generated_at;
  const pages: Page[] = [
    ...FIXED_PATHS.map((path) => ({ path, lastModified: built })),
    ...detailPages.markets().map((id) => ({ path: `/markets/${id}`, lastModified: built })),
    ...detailPages.occupationGroups().map((id) => ({ path: `/occupations/g/${id}`, lastModified: built })),
    ...detailPages.occupations().map((code) => ({ path: `/occupations/${code}`, lastModified: built })),
    ...detailPages.work().map((id) => ({ path: `/work/${id}`, lastModified: built })),
    ...detailPages.updates().map(({ id, occurredAt }) => ({ path: `/updates/${id}`, lastModified: occurredAt ?? built })),
  ];
  return pages.flatMap(({ path, lastModified }) =>
    LANGUAGES.map((language) => ({
      url: absoluteUrl(language, path),
      ...(lastModified ? { lastModified } : {}),
      alternates: {
        languages: {
          ...Object.fromEntries(LANGUAGES.map((l) => [l, absoluteUrl(l, path)])),
          "x-default": absoluteUrl("en", path),
        },
      },
    })),
  );
}
