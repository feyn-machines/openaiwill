"use client";

import { useMemo, useState } from "react";
import { bilingual, type Language } from "@/lib/i18n";
import type { HomeData } from "@/lib/home-data";
import { levelClass, pick } from "./levels";
import frame from "./section.module.css";
import s from "./companies-section.module.css";

/**
 * Module 03. Who is moving where: companies down the side, domains across the
 * top. A cell is the work one company's updates bear on in one domain - the
 * number is how many kinds of work, the fill is the highest level accepted from
 * that company's own updates. Nothing is drawn where a company has no update.
 */
const copy = bilingual({
  en: {
    eyebrow: "COVERAGE BY COMPANY",
    title: "Updates from {n} companies bear on specific work. {top} reaches the most markets: {k}",
    lead: "{tracked} tracked. {n} already reaching specific work. Point at a cell to see the markets.",
    note: "Number: kinds of work · Colour: highest accepted level · Point at a cell for its markets",
    company: "Company",
    updates: "updates",
    markets: "markets",
    most: "Most",
    hint: "Point at a cell to see the markets behind it.",
    cell: "{works} kinds of work in {markets} markets · highest accepted L{level}",
    legend: "Highest accepted",
  },
  "zh-CN": {
    eyebrow: "各公司的覆盖",
    title: "{n} 家公司的更新涉及具体工作，{top} 涉及的赛道最多：{k}",
    lead: "观测 {tracked} 家，{n} 家已进入具体工作。指向一格，看它进了哪些赛道。",
    note: "数字：涉及的工作项数 · 颜色：最高采信级别 · 指向一格查看赛道",
    company: "公司",
    updates: "条更新",
    markets: "条赛道",
    most: "涉及最多",
    hint: "指向一格，查看它背后的赛道。",
    cell: "{markets} 条赛道、{works} 项工作 · 最高采信 L{level}",
    legend: "最高采信级别",
  },
});

type Cell = { works: Set<string>; level: number };
type Company = { org: string; updates: Set<string>; markets: Map<string, Set<string>>; cells: Map<string, Cell> };

export function CompaniesSection({ data, language, index }: { data: HomeData; language: Language; index: string }) {
  const c = copy[language];
  const [at, setAt] = useState<{ org: string; dom: string } | null>(null);
  const [pinned, setPinned] = useState(false);

  const { companies, domains, workOf } = useMemo(() => {
    const workOf = new Map(data.works.map((w) => [w.id, w]));
    const orgOf = new Map(data.updates.map((u) => [u.id, u.org]));
    const by = new Map<string, Company>();
    const total = new Map<string, Set<string>>();
    for (const r of data.rows) {
      const org = orgOf.get(r.update), w = workOf.get(r.work);
      if (!org || !w) continue;
      const co = by.get(org) ?? by.set(org, { org, updates: new Set(), markets: new Map(), cells: new Map() }).get(org)!;
      co.updates.add(r.update);
      (co.markets.get(w.market.en) ?? co.markets.set(w.market.en, new Set()).get(w.market.en)!).add(w.id);
      const cell = co.cells.get(w.domainId) ?? co.cells.set(w.domainId, { works: new Set(), level: 0 }).get(w.domainId)!;
      cell.works.add(w.id);
      cell.level = Math.max(cell.level, r.accepted);
      (total.get(w.domainId) ?? total.set(w.domainId, new Set()).get(w.domainId)!).add(`${org}|${w.id}`);
    }
    return {
      workOf,
      companies: [...by.values()].sort((a, b) => b.markets.size - a.markets.size || b.updates.size - a.updates.size),
      domains: [...total.entries()].sort((a, b) => b[1].size - a[1].size).map(([id]) => id),
    };
  }, [data]);

  // "Most" is the market with the most kinds of work this company's updates bear on.
  const marketsIn = (co: Company, dom?: string) => {
    const list: { key: string; name: string; n: number }[] = [];
    for (const [key, ids] of co.markets) {
      const first = workOf.get([...ids][0])!;
      if (dom && first.domainId !== dom) continue;
      list.push({ key, name: pick(first.market, language), n: ids.size });
    }
    return list.sort((a, b) => b.n - a.n || (a.key < b.key ? -1 : 1));
  };

  const columns = { gridTemplateColumns: `150px repeat(${domains.length}, minmax(26px, 1fr)) minmax(190px, 250px)` };
  const top = companies[0];
  const here = at ? companies.find((co) => co.org === at.org) : undefined;
  const cellHere = here && at ? here.cells.get(at.dom) : undefined;
  const point = (org: string, dom: string) => { if (!pinned) setAt({ org, dom }); };

  if (!top) return null;
  const title = c.title.split(/\{n\}|\{top\}|\{k\}/);

  return (
    <section id="companies" className={frame.sec}>
      <div className={frame.eyebrow}>[ {index} ] &nbsp;{c.eyebrow}</div>
      <h2 className={frame.h2}>{title[0]}<b>{companies.length}</b>{title[1]}<b>{top.org}</b>{title[2]}<b>{top.markets.size}</b>{title[3]}</h2>
      <p className={frame.lead}>{c.lead.replace("{tracked}", String(data.orgsTracked)).replace("{n}", String(companies.length)).replace("{d}", String(domains.length))}</p>
      <p className={frame.note}>{c.note}</p>

      <div className={`${frame.stage} ${s.chart}`} onMouseLeave={() => { if (!pinned) setAt(null); }}>
        <div className={s.readout} aria-live="polite">
          {here && cellHere && at ? (
            <>
              <strong>{here.org}</strong>
              <span className={s.x}>×</span>
              <strong>{pick(data.domains[at.dom], language)}</strong>
              <span className={frame.mono}>{c.cell.replace("{works}", String(cellHere.works.size)).replace("{markets}", String(marketsIn(here, at.dom).length)).replace("{level}", String(cellHere.level))}</span>
              <span className={s.list}>{marketsIn(here, at.dom).map((m) => `${m.name} ${m.n}`).join(" · ")}</span>
            </>
          ) : (
            <>
              <span className={s.hint}>{c.hint}</span>
              <span className={`${s.legend} ${frame.mono}`}>{c.legend}{[1, 2, 3].map((l) => <span key={l}><i className={`${s.key} ${s[levelClass(l)]}`} />L{l}</span>)}</span>
            </>
          )}
        </div>

        <div className={s.scroll}>
          <div className={`${s.row} ${s.head}`} style={columns}>
            <div className={frame.mono}>{c.company}</div>
            {domains.map((d) => <div key={d} className={`${s.dom} ${at?.dom === d ? s.hot : ""}`}><span>{pick(data.domains[d], language)}</span></div>)}
            <div />
          </div>

          {companies.map((co) => {
            const most = marketsIn(co)[0];
            return (
              <div key={co.org} className={`${s.row} ${s.line} ${at?.org === co.org ? s.on : ""}`} style={columns}>
                <div className={s.name}>{co.org}<small className={frame.mono}>{co.updates.size} {c.updates}</small></div>
                {domains.map((d) => {
                  const cell = co.cells.get(d);
                  const active = at?.org === co.org && at.dom === d;
                  if (!cell) return <div key={d} className={`${s.slot} ${at?.dom === d ? s.col : ""}`} />;
                  return (
                    <div key={d} className={`${s.slot} ${at?.dom === d ? s.col : ""}`}>
                      <button
                        type="button"
                        className={`${s.sq} ${s[levelClass(cell.level)]} ${active ? s.active : ""}`}
                        onMouseEnter={() => point(co.org, d)}
                        onFocus={() => point(co.org, d)}
                        onClick={() => { const same = pinned && active; setPinned(!same); setAt(same ? null : { org: co.org, dom: d }); }}
                        aria-pressed={pinned && active}
                        aria-label={`${co.org} × ${pick(data.domains[d], language)}: ${c.cell.replace("{works}", String(cell.works.size)).replace("{markets}", String(marketsIn(co, d).length)).replace("{level}", String(cell.level))}`}
                      >{cell.works.size}</button>
                    </div>
                  );
                })}
                <div className={`${s.meta} ${frame.mono}`}><b>{co.markets.size}</b> {c.markets}<span>{c.most}: {most.name}</span></div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
