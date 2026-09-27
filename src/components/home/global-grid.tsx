"use client";

import { cellsFor, type WorkGridCounts } from "@/components/work-grid-shape";
import { useScrub } from "./reveal";
import s from "./home.module.css";

/**
 * Screen 5: the whole catalogue as a hundred squares, filling as you scroll.
 *
 * Scrub rather than play-once because the content of this screen IS "how much
 * has been filled in" - tying it to the scrollbar makes the reader measure it
 * with their own hand. It is one of exactly two places DESIGN.md permits this.
 *
 * The count beside it is read off the same apportionment the squares are drawn
 * from, never a second rounding of the same shares: rounding twice lands on 99
 * or 101 often enough that the sentence and the picture would disagree in front
 * of the reader.
 */

export function GlobalGrid({
  counts,
  assessed,
  bulk,
  unknown,
  untouched,
  lines,
}: {
  counts: WorkGridCounts;
  assessed: number;
  bulk: number;
  unknown: number;
  untouched: number;
  lines: { assessed: string; bulk: string; none5: string; blanks: string; label: string };
}) {
  const { ref, progress } = useScrub<HTMLDivElement>();

  const cells = cellsFor(counts);
  const filled = Math.round(progress * cells.length);

  return (
    <div ref={ref} className={s.globalWrap}>
      <p className={s.finding}>
        {lines.assessed.replace("{n}", String(assessed))}{" "}
        {lines.bulk.replace("{n}", String(bulk))} <strong>{lines.none5}</strong>
      </p>

      <div className={s.globalGrid} role="img" aria-label={lines.label}>
        {cells.map((key, i) => (
          <span
            key={i}
            className={`${s.gcell} ${s[`stage${key}`]}`}
            // Content is the square; the scrub only decides whether it has been
            // painted yet. With no JavaScript `progress` stays 1 and every
            // square is painted on first render.
            data-off={i < filled ? undefined : "true"}
            aria-hidden="true"
          />
        ))}
      </div>

      <p className={s.blanks}>
        {lines.blanks
          .replace("{unknown}", String(unknown))
          .replace("{untouched}", String(untouched))}
      </p>
    </div>
  );
}
