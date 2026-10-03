import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { LEVEL_NAMES, TIER_NAMES, levelClass } from "@/components/home/sections/levels";
import s from "@/components/detail.module.css";
import { bilingual } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import { pageMetadata } from "@/lib/seo";
import { detailPages } from "@/lib/site-pages";
import { href, marketHref, updateHref, workHref, workSlug } from "@/lib/routes";
import { activities, activitiesOfMarket, evidenceForActivity, gatesOfActivity, gates as allGates, manifest } from "@/lib/snapshot";

/**
 * One kind of work: the level it stands at, and every update that put it
 * there. Only work some update bears on has a page.
 */
const copy = bilingual({
  en: {
    back: "← {market}",
    eyebrow: "WORK",
    say: "As of {date}, AI does this work at {level}. {n} updates bear on it. Strongest evidence: {tier}.",
    level: "Level",
    updates: "Updates",
    companies: "Companies",
    evidence: "Strongest evidence",
    here: "Stands here",
    listTitle: "What moved it",
    listSub: "Every update that bears on this work, newest first.",
    claimed: "Claimed L{c} · Accepted L{a}",
    accepted: "Accepted L{a}",
    source: "Source ↗",
    undated: "Undated",
    held: "Held by a non-technical condition:",
    heldNote: "The level above is what the evidence supports. Whether the work may be handed over is a separate question.",
    more: "More work in {market}",
    all: "All updates",
    market: "The whole market",
    meta: "openaiwill",
  },
  "zh-CN": {
    back: "← {market}",
    eyebrow: "工作",
    say: "截至 {date}，AI 把这项工作做到 {level}。{n} 条更新涉及它，最强的证据：{tier}。",
    level: "级别",
    updates: "更新",
    companies: "公司",
    evidence: "最强证据",
    here: "当前位置",
    listTitle: "是什么把它推到这里",
    listSub: "涉及这项工作的全部更新，最新的在前。",
    claimed: "宣称 L{c} · 采信 L{a}",
    accepted: "采信 L{a}",
    source: "来源 ↗",
    undated: "无日期",
    held: "受非技术条件限制：",
    heldNote: "上面的级别是证据支持的程度。这项工作能不能交出去，是另一个问题。",
    more: "{market} 里的其他工作",
    all: "全部更新",
    market: "整条赛道",
    meta: "openaiwill",
  },
});

type Props = { params: Promise<{ id: string }> };
const TIER_RANK: Record<string, number> = { T1: 0, T2: 1, T3: 2, T4: 3 };
const reached = () => activities.filter((a) => a.evidence_rows && a.level);
const find = (slug: string) => reached().find((a) => workSlug(a.activity_id) === slug);

export function generateStaticParams() {
  return detailPages.work().map((id) => ({ id }));
}

/** The server holds no snapshot, so an address outside this build is a 404, not a page to render. */
export const dynamicParams = false;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { language } = await getLocale();
  const id = (await params).id;
  const work = find(id);
  if (!work) return { title: copy[language].meta };
  const name = (language === "zh-CN" ? work.label_zh_cn : work.label_en) ?? work.label_en;
  const level = Math.round(work.level ?? 0);
  return pageMetadata({ language, path: `/work/${id}`, title: `${name} · L${level} ${LEVEL_NAMES[language][level]}` });
}

export default async function WorkPage({ params }: Props) {
  const { language } = await getLocale();
  const c = copy[language];
  const work = find((await params).id);
  if (!work) notFound();

  const zh = language === "zh-CN";
  const name = (zh ? work.label_zh_cn : work.label_en) ?? work.label_en;
  const market = (zh ? work.market_zh_cn : work.market_en) ?? work.market_en;
  const level = Math.round(work.level ?? 0);
  const rows = evidenceForActivity(work.activity_id).filter((r) => r.level !== null);
  const tier = rows.map((r) => r.evidence_tier).sort((a, b) => (TIER_RANK[a] ?? 9) - (TIER_RANK[b] ?? 9))[0] ?? "T3";
  const companies = new Set(rows.map((r) => r.org_name).filter(Boolean));
  const gateById = new Map(allGates.map((g) => [g.gate_id, g]));
  const held = work.gated ? gatesOfActivity(work.activity_id).map((id) => gateById.get(id)).filter((g) => g !== undefined) : [];
  const siblings = activitiesOfMarket(work.market_id).filter((a) => a.activity_id !== work.activity_id && a.evidence_rows && a.level);
  const levelText = `L${level} ${LEVEL_NAMES[language][level]}`;

  return (
    <div className={s.page}>
      <Link className={s.back} href={marketHref(language, work.market_id)}>{c.back.replace("{market}", market)}</Link>
      <div className={s.eyebrow}>{c.eyebrow} · <Link href={marketHref(language, work.market_id)}>{market}</Link></div>
      <h1 className={s.title}>{name}</h1>
      <p className={s.say}>
        {c.say.replace("{date}", manifest?.generated_at.slice(0, 10) ?? "").replace("{n}", String(rows.length)).replace("{tier}", TIER_NAMES[language][tier] ?? tier).split("{level}")[0]}
        <b>{levelText}</b>
        {c.say.replace("{date}", "").replace("{n}", String(rows.length)).replace("{tier}", TIER_NAMES[language][tier] ?? tier).split("{level}")[1]}
      </p>

      <dl className={s.facts}>
        <div className={s.fact}><dt>{c.level}</dt><dd className={level >= 3 ? s.sig : ""}>L{level}<small>{LEVEL_NAMES[language][level]}</small></dd></div>
        <div className={s.fact}><dt>{c.updates}</dt><dd>{rows.length}</dd></div>
        <div className={s.fact}><dt>{c.companies}</dt><dd>{companies.size}<small>{[...companies].slice(0, 3).join(" · ")}</small></dd></div>
        <div className={s.fact}><dt>{c.evidence}</dt><dd>{tier}<small>{TIER_NAMES[language][tier] ?? tier}</small></dd></div>
      </dl>

      <div className={s.ruler} aria-label={`${c.here}: ${levelText}`}>
        {LEVEL_NAMES[language].map((label, l) => (
          <i key={l} className={l === level ? s.here : l < level ? s.below : ""}>L{l}<small>{label}</small></i>
        ))}
      </div>

      {held.length > 0 && (
        <p className={s.note}><b>{c.held}</b> {held.map((g) => (zh ? g.label_zh_cn : g.label_en) ?? g.label_en).join(" · ")}. {c.heldNote}</p>
      )}

      <h2 className={s.h2}>{c.listTitle}</h2>
      <p className={s.sub}>{c.listSub}</p>
      <ul className={s.list}>
        {rows.map((r) => (
          <li key={r.event_id} className={s.row}>
            <div className={s.when}><b>{r.occurred_at ? r.occurred_at.slice(0, 10) : c.undated}</b>{r.org_name}</div>
            <div className={s.what}>
              <Link className={s.name} href={updateHref(language, r.event_id)}>{r.title}</Link>
              <p>{r.summary}</p>
            </div>
            <div className={s.how}>
              <span className={`${s.tag} ${s[levelClass(r.level ?? 0)]}`}>L{r.level} {LEVEL_NAMES[language][r.level ?? 0]}</span>
              {(r.observed_level ?? 0) > (r.level ?? 0) && <span className={s.warn}>{c.claimed.replace("{c}", String(r.observed_level)).replace("{a}", String(r.level))}</span>}
              <span>{TIER_NAMES[language][r.evidence_tier] ?? r.evidence_tier}</span>
              {r.source_urls[0] && <a className={s.out} href={r.source_urls[0]} target="_blank" rel="nofollow noopener noreferrer">{c.source}</a>}
            </div>
          </li>
        ))}
      </ul>

      {siblings.length > 0 && (
        <>
          <h2 className={s.h2}>{c.more.replace("{market}", market)}</h2>
          <div className={s.links} style={{ marginTop: 18 }}>
            {siblings.map((a) => (
              <Link key={a.activity_id} className={s.chip} href={workHref(language, a.activity_id)}>
                {(zh ? a.label_zh_cn : a.label_en) ?? a.label_en}<small>L{Math.round(a.level ?? 0)}</small>
              </Link>
            ))}
          </div>
        </>
      )}

      <div className={s.cta}>
        <Link href={marketHref(language, work.market_id)}>{c.market}</Link>
        <Link href={href(language, "/updates")}>{c.all}</Link>
      </div>
    </div>
  );
}
