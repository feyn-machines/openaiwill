/**
 * URL fragments, with no data source attached.
 *
 * Separate from snapshot.ts because that module opens files: importing a single
 * pure helper from it pulls `node:fs` into whatever imports it, and a client
 * component doing so fails the build with an error that names the chunker
 * rather than the import. Anything a client component needs and that does not
 * read data belongs here.
 */

/**
 * Fragment for one activity inside its market page.
 *
 * The activity id already begins with its market id, so the market prefix is
 * stripped: `oaw:market:legal-x-check-authority` on the page for
 * `oaw:market:legal-x` becomes `a-check-authority`.
 */
export function activityAnchor(activityId: string, marketId: string): string {
  const tail = activityId.startsWith(`${marketId}-`)
    ? activityId.slice(marketId.length + 1)
    : activityId.replace(/^oaw:market:/, "");
  return `a-${tail}`;
}
