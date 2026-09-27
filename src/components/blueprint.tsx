import type { ReactNode } from "react";
import s from "./blueprint.module.css";

/**
 * The confirmed visual language as components.
 *
 * Read design/reference/tensorlake-2026-09-12/user-reference/confirmed-direction.png
 * before changing any of this. The direction is a technical drawing: ruled
 * canvas, filled square bullets, mono uppercase labels, dashed leaders to
 * bracketed tags, numbers at display size. Pages compose these; they do not
 * invent their own head or their own number size.
 *
 * Copy rule, enforced by review rather than by code: one line of lead per
 * section, never two paragraphs. The chart is the explanation.
 */

export type Tone = "signal" | "plain" | "correction" | "warning";

const BULLET: Record<Tone, string> = {
  signal: s.bulletSignal,
  plain: s.bulletPlain,
  correction: s.bulletCorrection,
  warning: s.bulletWarning,
};

/** `■ LABEL ┄┄┄┄┄┄┄┄┄┄ [ TAG ]` */
export function Head({
  label,
  tag,
  tone = "signal",
}: {
  label: string;
  tag?: string;
  tone?: Tone;
}) {
  return (
    <p className={s.head}>
      <span className={`${s.bullet} ${BULLET[tone]}`} aria-hidden="true" />
      <span className={s.label}>{label}</span>
      <span className={s.leader} aria-hidden="true" />
      {tag ? <span className={s.tag}>{tag}</span> : null}
    </p>
  );
}

/** A head, then the number at display size with its rule and note beside it. */
export function Stat({
  label,
  tag,
  value,
  unit,
  note,
  tone = "signal",
}: {
  label: string;
  tag?: string;
  value: ReactNode;
  unit?: string;
  note?: ReactNode;
  tone?: Tone;
}) {
  return (
    <div className={s.stat}>
      <Head label={label} tag={tag} tone={tone} />
      <div className={s.statBody}>
        <p className={`${s.value} ${tone === "correction" ? s.valueCorrection : ""}`}>
          {value}
          {unit ? <span className={s.unit}>{unit}</span> : null}
        </p>
        {note ? (
          <div className={`${s.note} ${tone === "correction" ? s.noteCorrection : ""}`}>
            {note}
          </div>
        ) : null}
      </div>
    </div>
  );
}

/** A page section: eyebrow, heading, ONE line of lead, then the content. */
export function Block({
  eyebrow,
  title,
  lead,
  id,
  children,
}: {
  eyebrow?: string;
  title: string;
  lead?: string;
  id?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className={s.section}>
      {eyebrow ? <p className={s.eyebrow}>{eyebrow}</p> : null}
      <h2 className={s.h2}>{title}</h2>
      {lead ? <p className={s.lead}>{lead}</p> : null}
      {children}
    </section>
  );
}

/**
 * An absent value: the dash, plus the reason there is no number.
 *
 * `Missing` in data-page.tsx says the same thing, but that module reads the
 * snapshot from disk and so cannot cross into a client component. The rule it
 * enforces - a measured zero is `0`, an uncollected one is `—` with a reason -
 * has to hold in an interactive list too, so the primitive lives here as well.
 */
export function Blank({ reason }: { reason: string }) {
  return (
    <span className={s.blank} title={reason}>
      <span aria-hidden="true">—</span>
      <span className="oaw-sr-only">{reason}</span>
    </span>
  );
}

/** A measure against a shared baseline. `share` is 0-1. */
export function Bar({ share, label }: { share: number; label?: string }) {
  return (
    <span className={s.barTrack} role={label ? "img" : undefined} aria-label={label}>
      <span
        className={s.bar}
        style={{ ["--w" as string]: `${Math.max(0, Math.min(1, share)) * 100}%` }}
        aria-hidden="true"
      />
    </span>
  );
}

export { s as blueprint };
