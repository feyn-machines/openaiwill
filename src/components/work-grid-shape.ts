/**
 * The shape of the hundred-square grid, with no data source attached.
 *
 * Split out of work-grid.tsx because that component reads the published
 * snapshot for the ladder's wording, and the snapshot reader opens files. Any
 * client component that wanted only `apportion` or `DRAW_ORDER` used to drag
 * `node:fs` into the browser bundle through that import, which fails the build
 * with an error naming the chunker rather than the import that caused it.
 *
 * Everything here is pure: same input, same squares, no I/O.
 */

export type StageKey =
  | "0" | "1" | "2" | "3" | "4" | "5" | "unknown" | "untouched";

/** Lowest first. Both blanks sit at the end, in order of how little is known. */
export const STAGE_KEYS: StageKey[] = [
  "0", "1", "2", "3", "4", "5", "unknown", "untouched",
];

/** Highest level first: the eye lands on how far it got, then reads down. */
export const DRAW_ORDER: StageKey[] = ["5", "4", "3", "2", "1", "0", "unknown", "untouched"];

export type WorkGridCounts = Partial<Record<StageKey, number>>;

/**
 * Largest remainder, so the squares always total exactly `squares`.
 *
 * Rounding each share on its own happens to land on 100 for today's numbers and
 * would silently produce 99 or 101 for tomorrow's. The chart must not depend on
 * that luck.
 */
export function apportion(counts: WorkGridCounts, squares: number): Record<StageKey, number> {
  const total = STAGE_KEYS.reduce((sum, key) => sum + (counts[key] ?? 0), 0);
  const out = Object.fromEntries(STAGE_KEYS.map((k) => [k, 0])) as Record<StageKey, number>;
  if (total <= 0) return out;

  const exact = STAGE_KEYS.map((key) => ((counts[key] ?? 0) / total) * squares);
  const floors = exact.map(Math.floor);
  let remaining = squares - floors.reduce((a, b) => a + b, 0);

  const order = STAGE_KEYS.map((key, i) => ({ key, i, frac: exact[i] - floors[i] }))
    // A tie goes to the larger bucket, so the order never depends on key order.
    .sort((a, b) => b.frac - a.frac || (counts[b.key] ?? 0) - (counts[a.key] ?? 0));

  STAGE_KEYS.forEach((key, i) => { out[key] = floors[i]; });
  for (const entry of order) {
    if (remaining <= 0) break;
    out[entry.key] += 1;
    remaining -= 1;
  }
  return out;
}

/** The cells to draw, in DRAW_ORDER, always a hundred of them. */
export function cellsFor(counts: WorkGridCounts, squares = 100): StageKey[] {
  const drawn = apportion(counts, squares);
  const cells: StageKey[] = [];
  for (const key of DRAW_ORDER) {
    for (let i = 0; i < drawn[key]; i += 1) cells.push(key);
  }
  return cells;
}
