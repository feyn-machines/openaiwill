import type { Language } from "@/lib/i18n";
import s from "./evidence-timeline.module.css";

/**
 * When the evidence arrived.
 *
 * The axis is real calendar days, not a list squeezed to fit: a week with
 * nothing in it has to look empty, because that is the finding. Collection
 * started on 2026-08-22 and the record grows forward from there — it is not a
 * history, and the axis says so by starting where the record starts.
 */

export type TimelineMark = {
  eventId: string;
  date: string;
  title: string;
  capabilities: string[];
  /** The announcement itself. A reader following a tick wants the source. */
  url?: string | null;
};

const DAY = 24 * 60 * 60 * 1000;

const COPY = {
  en: {
    empty: "No update in this window produced evidence here.",
    recent: "Most recent",
    andMore: "and {n} more",
    days: "{n} days recorded",
  },
  "zh-CN": {
    empty: "这段时间里没有更新在这里留下证据。",
    recent: "最近的",
    andMore: "另有 {n} 条",
    days: "已记录 {n} 天",
  },
} as const;

export function EvidenceTimeline({
  marks,
  language,
  limit = 6,
}: {
  marks: TimelineMark[];
  language: Language;
  limit?: number;
}) {
  const c = COPY[language];
  if (!marks.length) return <p className={s.empty}>{c.empty}</p>;

  const times = marks.map((m) => Date.parse(m.date)).filter(Number.isFinite);
  const first = Math.min(...times);
  const last = Math.max(...times);
  const span = Math.max(DAY, last - first);
  const days = Math.round(span / DAY) + 1;

  // One tick per day that carries anything, so repeat days stack rather than
  // overprint and a busy day reads as taller.
  const byDay = new Map<string, TimelineMark[]>();
  for (const mark of marks) {
    const key = mark.date.slice(0, 10);
    byDay.set(key, [...(byDay.get(key) ?? []), mark]);
  }
  const busiest = Math.max(...[...byDay.values()].map((v) => v.length));

  const recent = [...marks].sort((a, b) => b.date.localeCompare(a.date)).slice(0, limit);

  return (
    <div className={s.wrap}>
      <div className={s.axis} role="img" aria-label={c.days.replace("{n}", String(days))}>
        {[...byDay.entries()].map(([day, items]) => {
          const at = ((Date.parse(day) - first) / span) * 100;
          return (
            <span
              key={day}
              className={s.tick}
              style={{
                insetInlineStart: `${at}%`,
                blockSize: `${28 + (items.length / busiest) * 44}%`,
              }}
            />
          );
        })}
        <span className={s.baseline} />
      </div>

      <div className={s.scale}>
        <span>{new Date(first).toISOString().slice(0, 10)}</span>
        <span>{c.days.replace("{n}", String(days))}</span>
        <span>{new Date(last).toISOString().slice(0, 10)}</span>
      </div>

      <ol className={s.list}>
        {recent.map((mark) => (
          <li key={mark.eventId}>
            <span className={s.date}>{mark.date.slice(5, 10)}</span>
            {mark.url ? (
              <a className={s.title} href={mark.url} target="_blank" rel="noreferrer noopener">
                {mark.title}
              </a>
            ) : (
              <span className={s.title}>{mark.title}</span>
            )}
            <span className={s.caps}>{mark.capabilities.join(" · ")}</span>
          </li>
        ))}
      </ol>
      {marks.length > recent.length ? (
        <p className={s.more}>{c.andMore.replace("{n}", String(marks.length - recent.length))}</p>
      ) : null}
    </div>
  );
}
