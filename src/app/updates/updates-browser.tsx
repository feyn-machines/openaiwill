"use client";

import { useMemo, useState, type CSSProperties } from "react";
import { Bar, Blank, Block } from "@/components/blueprint";
import { useSeen } from "@/components/home/reveal";
import s from "./updates.module.css";

/**
 * The 581 updates, as something a reader can work rather than scroll.
 *
 * Every row is rendered on the server, so the page is complete with JavaScript
 * off; search, the publisher chart, the landed/silent split and the sort are
 * enhancements on top of a list that is already there. Nothing here reads the
 * snapshot: `@/lib/snapshot` opens files, and a client component that imports it
 * takes `node:fs` into the browser bundle and fails the build. Everything this
 * component shows is resolved and localised on the server and handed down.
 */

/** One reading an update produced, already worded for the reader's language. */
export type ReadingRow = {
  activity: string;
  market: string | null;
  /** `L2 · <the ladder's own word>`, built from progress.levels. */
  level: string | null;
  /** `T3 → L2` when the evidence tier held the reading below the proposal. */
  cap: string | null;
};

export type UpdateRow = {
  id: string;
  title: string;
  /** Already `2026-09-14`; null when no publication time was recorded. */
  date: string | null;
  /** What the reader sees. */
  org: string | null;
  /** The publisher's registry name, which is what the chart filters on: the
      displayed name is localised and would never match an English chart row. */
  orgKey: string | null;
  url: string | null;
  activities: number;
  markets: number;
  /** `L2 · <word>`; null when the update bore on no activity. */
  level: string | null;
  readings: ReadingRow[];
};

export type BrowserCopy = {
  fromEyebrow: string;
  fromTitle: string;
  fromLead: string;
  tableEyebrow: string;
  tableTitle: string;
  tableLead: string;
  tableLabel: string;
  searchLabel: string;
  searchPlaceholder: string;
  filterLabel: string;
  filterAll: string;
  filterLanded: string;
  filterSilent: string;
  sortLabel: string;
  sortTime: string;
  sortReach: string;
  showing: string;
  empty: string;
  reset: string;
  colWhen: string;
  colUpdate: string;
  colFrom: string;
  colLanded: string;
  colTop: string;
  openSource: string;
  readingsOpen: string;
  readingsClose: string;
  noDate: string;
  noOrg: string;
  noSource: string;
  noLevel: string;
  capNote: string;
};

type Landed = "all" | "landed" | "silent";
type Sort = "time" | "reach";

const numbers = new Intl.NumberFormat("en-US");

export function UpdatesBrowser({
  rows,
  orgs,
  copy,
  maxActivities,
}: {
  rows: UpdateRow[];
  orgs: { org: string; label: string; events: number }[];
  copy: BrowserCopy;
  maxActivities: number;
}) {
  const [query, setQuery] = useState("");
  const [landed, setLanded] = useState<Landed>("all");
  const [org, setOrg] = useState<string | null>(null);
  const [sort, setSort] = useState<Sort>("time");
  const [open, setOpen] = useState<string | null>(null);

  const { ref: chartRef, seen: chartSeen } = useSeen<HTMLDivElement>();
  const topOrg = orgs[0]?.events ?? 1;

  const landedCount = useMemo(() => rows.filter((r) => r.activities > 0).length, [rows]);

  // Search is over the title and the publisher, which is what a reader has in
  // mind when they come looking for one update they remember.
  const haystack = useMemo(
    () =>
      new Map(
        rows.map((r) => [r.id, `${r.title} ${r.org ?? ""} ${r.orgKey ?? ""}`.toLowerCase()]),
      ),
    [rows],
  );

  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = rows.filter((row) => {
      if (landed === "landed" && row.activities === 0) return false;
      if (landed === "silent" && row.activities > 0) return false;
      if (org && row.orgKey !== org) return false;
      if (needle && !(haystack.get(row.id) ?? "").includes(needle)) return false;
      return true;
    });
    const byDate = (a: UpdateRow, b: UpdateRow) => (b.date ?? "").localeCompare(a.date ?? "");
    return sort === "time"
      ? [...filtered].sort(byDate)
      : [...filtered].sort((a, b) => b.activities - a.activities || byDate(a, b));
  }, [rows, haystack, query, landed, org, sort]);

  // Re-mounting the body on a filter change is what gives the rows their
  // transition; typing narrows the list fast, so the cost stays small.
  const signature = `${query}|${landed}|${org ?? ""}|${sort}`;
  const filtered = query !== "" || landed !== "all" || org !== null;

  return (
    <>
      <Block
        eyebrow={copy.fromEyebrow}
        title={copy.fromTitle}
        lead={copy.fromLead}
        id="from"
      >
        <div className={s.chart} ref={chartRef} data-seen={chartSeen ? "true" : undefined}>
          <ol className={s.orgs}>
            {orgs.map((row, i) => {
              const current = org === row.org;
              return (
                <li key={row.org}>
                  <button
                    type="button"
                    className={`${s.orgButton} ${current ? s.orgCurrent : ""}`}
                    style={{ "--i": i } as CSSProperties}
                    aria-pressed={current}
                    onClick={() => setOrg(current ? null : row.org)}
                  >
                    <span className={s.orgName}>{row.label}</span>
                    <span className={s.track}>
                      <Bar share={row.events / topOrg} label={`${row.label} ${row.events}`} />
                    </span>
                    <span className={s.orgCount}>{numbers.format(row.events)}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
      </Block>

      <Block
        eyebrow={copy.tableEyebrow}
        title={copy.tableTitle}
        lead={copy.tableLead}
        id="all"
      >
        <div className={s.controls}>
          <div className={s.search}>
            <label className={s.fieldLabel} htmlFor="updates-search">
              {copy.searchLabel}
            </label>
            <input
              id="updates-search"
              className={s.searchInput}
              type="search"
              value={query}
              placeholder={copy.searchPlaceholder}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>

          <div className={s.row}>
            <span className={s.fieldLabel}>{copy.filterLabel}</span>
            <div className={s.chips}>
              {(
                [
                  ["all", copy.filterAll, rows.length],
                  ["landed", copy.filterLanded, landedCount],
                  ["silent", copy.filterSilent, rows.length - landedCount],
                ] as [Landed, string, number][]
              ).map(([key, label, count]) => (
                <button
                  key={key}
                  type="button"
                  className={`${s.chip} ${landed === key ? s.chipCurrent : ""}`}
                  aria-pressed={landed === key}
                  onClick={() => setLanded(key)}
                >
                  <span className={s.chipMark} aria-hidden="true" />
                  {label}
                  <span className={s.chipCount}>{numbers.format(count)}</span>
                </button>
              ))}
            </div>
          </div>

          <div className={s.row}>
            <span className={s.fieldLabel}>{copy.sortLabel}</span>
            <div className={s.chips}>
              {(
                [
                  ["time", copy.sortTime],
                  ["reach", copy.sortReach],
                ] as [Sort, string][]
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  className={`${s.chip} ${sort === key ? s.chipCurrent : ""}`}
                  aria-pressed={sort === key}
                  onClick={() => setSort(key)}
                >
                  <span className={s.chipMark} aria-hidden="true" />
                  {label}
                </button>
              ))}
            </div>
            {filtered ? (
              <button
                type="button"
                className={s.chip}
                onClick={() => {
                  setQuery("");
                  setLanded("all");
                  setOrg(null);
                }}
              >
                {copy.reset}
              </button>
            ) : null}
          </div>

          <p className={s.result} aria-live="polite">
            {copy.showing
              .replace("{n}", numbers.format(shown.length))
              .replace("{total}", numbers.format(rows.length))}
            {org ? ` · ${orgs.find((o) => o.org === org)?.label ?? org}` : ""}
          </p>
        </div>

        {shown.length === 0 ? (
          <p className={s.empty}>{copy.empty}</p>
        ) : (
          <div
            className={`oaw-table-wrap ${s.tableWrap}`}
            role="region"
            aria-label={copy.tableLabel}
            tabIndex={0}
          >
            <table className="oaw-table">
              <thead>
                <tr>
                  <th scope="col">{copy.colWhen}</th>
                  <th scope="col">{copy.colUpdate}</th>
                  <th scope="col">{copy.colFrom}</th>
                  <th scope="col">{copy.colLanded}</th>
                  <th scope="col">{copy.colTop}</th>
                </tr>
              </thead>
              <tbody key={signature} className={s.rows}>
                {shown.map((row) => {
                  const isOpen = open === row.id;
                  return [
                    <tr key={row.id}>
                      <td className={s.cellWhen}>{row.date ?? <Blank reason={copy.noDate} />}</td>
                      <th scope="row">
                        {row.url ? (
                          <a
                            className={s.title}
                            href={row.url}
                            rel="nofollow noopener noreferrer"
                            target="_blank"
                          >
                            {row.title} <span aria-hidden="true">↗</span>
                            <span className="oaw-sr-only"> {copy.openSource}</span>
                          </a>
                        ) : (
                          <span className={s.title}>
                            {row.title} <Blank reason={copy.noSource} />
                          </span>
                        )}
                        {row.readings.length > 0 ? (
                          <button
                            type="button"
                            className={`${s.expand} ${isOpen ? s.expandOpen : ""}`}
                            aria-expanded={isOpen}
                            aria-controls={`readings-${row.id}`}
                            onClick={() => setOpen(isOpen ? null : row.id)}
                          >
                            <span className={s.expandMark} aria-hidden="true" />
                            {(isOpen ? copy.readingsClose : copy.readingsOpen).replace(
                              "{n}",
                              numbers.format(row.readings.length),
                            )}
                          </button>
                        ) : null}
                      </th>
                      <td>{row.org ?? <Blank reason={copy.noOrg} />}</td>
                      <td>
                        <span className={s.cellLanded}>
                          {row.activities > 0 ? (
                            <span className={s.cellBar}>
                              <Bar
                                share={row.activities / maxActivities}
                                label={`${row.activities} / ${row.markets}`}
                              />
                            </span>
                          ) : null}
                          <span
                            className={`${s.cellCount} ${row.activities === 0 ? s.cellZero : ""}`}
                          >
                            {row.activities} / {row.markets}
                          </span>
                        </span>
                      </td>
                      <td>
                        {row.level ? (
                          <span className={s.level}>{row.level}</span>
                        ) : (
                          <span className={s.levelNone}>{copy.noLevel}</span>
                        )}
                      </td>
                    </tr>,
                    isOpen ? (
                      <tr key={`${row.id}-readings`} className={s.detailRow}>
                        <td colSpan={5} id={`readings-${row.id}`}>
                          <ul className={s.readings}>
                            {row.readings.map((reading, i) => (
                              <li key={`${reading.activity}-${i}`} className={s.reading}>
                                <span className={s.readingName}>
                                  {reading.activity}
                                  {reading.market ? (
                                    <span className={s.readingMarket}>{reading.market}</span>
                                  ) : null}
                                </span>
                                <span className={s.readingRight}>
                                  {reading.level ? (
                                    <span className={s.level}>{reading.level}</span>
                                  ) : (
                                    <Blank reason={copy.noLevel} />
                                  )}
                                  {reading.cap ? (
                                    <span className={s.cap}>
                                      {copy.capNote.replace("{cap}", reading.cap)}
                                    </span>
                                  ) : null}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </td>
                      </tr>
                    ) : null,
                  ];
                })}
              </tbody>
            </table>
          </div>
        )}
      </Block>
    </>
  );
}
