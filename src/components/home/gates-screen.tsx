"use client";

import { useState } from "react";
import type { Language } from "@/lib/i18n";
import { useSeen } from "./reveal";
import s from "./home.module.css";

/**
 * Screen 6: the conditions that do not lift when models improve.
 *
 * The only place on the site that answers "why are these numbers so low", and
 * the answer is a reason rather than an excuse: 285 of 614 activities are held
 * by at least one gate, 254 of them because somebody has to be in the room.
 *
 * Each bar opens. The gate's definition and the reason it is still closed were
 * already in the snapshot and had never been rendered anywhere - a bar chart of
 * ten words was asking the reader to take "physical presence" on trust. The
 * closed reason is the useful half: it says the gate was checked against twelve
 * published policy statements and none of them moved it, which is the
 * difference between a finding and an assumption.
 *
 * Gates with no activities behind them are drawn at zero. A gate that matched
 * nothing is a result about that gate.
 */

export type GateBar = {
  id: string;
  label: string;
  type: string;
  typeLabel: string;
  definition: string | null;
  status: string | null;
  reason: string | null;
  examples: string[];
  activities: number;
};

export function GatesScreen({
  bars,
  language,
  lines,
}: {
  bars: GateBar[];
  language: Language;
  lines: {
    label: string;
    unit: string;
    open: string;
    holds: string;
    noReason: string;
    examples: string;
  };
}) {
  const [openId, setOpenId] = useState<string | null>(null);
  const { ref, seen } = useSeen<HTMLDivElement>();
  const top = Math.max(1, ...bars.map((b) => b.activities));

  return (
    <div ref={ref} data-seen={seen ? "true" : undefined}>
      <ol className={s.gates} aria-label={lines.label}>
        {bars.map((bar, i) => {
          const on = openId === bar.id;
          return (
            <li key={bar.id} className={s.gateItem} style={{ ["--i" as string]: i }}>
              <button
                type="button"
                className={s.gateRow}
                aria-expanded={on}
                onClick={() => setOpenId(on ? null : bar.id)}
              >
                <span className={s.gateName}>
                  <span className={s.gateCaret} aria-hidden="true">
                    {on ? "−" : "+"}
                  </span>
                  {bar.label}
                </span>
                <span className={s.gateTrack} aria-hidden="true">
                  <span
                    className={s.gateBar}
                    style={{ ["--w" as string]: `${(bar.activities / top) * 100}%` }}
                  />
                </span>
                <span className={s.gateValue}>
                  {bar.activities}
                  <span className={s.gateUnit}> {lines.unit}</span>
                </span>
              </button>

              {/* Rendered only when open, but the button always says what it
                  will reveal, so the row is readable with no JavaScript. */}
              {on ? (
                <div className={s.gateOpen}>
                  {bar.definition ? <p className={s.gateDef}>{bar.definition}</p> : null}
                  <p className={s.gateReason}>
                    <span className={s.gateReasonLabel}>{lines.holds}</span>{" "}
                    {bar.reason ?? lines.noReason}
                  </p>
                  {bar.examples.length > 0 ? (
                    <p className={s.gateExamples}>
                      <span className={s.gateReasonLabel}>{lines.examples}</span>{" "}
                      {bar.examples.join(" · ")}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>
      <p className={s.gateHint} lang={language === "zh-CN" ? "zh-CN" : "en"}>
        {lines.open}
      </p>
    </div>
  );
}
