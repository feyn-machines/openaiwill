import Link from "next/link";
import { bilingual, getLocale } from "@/lib/i18n";
import { type StageKey, type WorkGridCounts, apportion } from "@/components/work-grid-shape";
import {
  ChainScreens,
  type HomeActivity,
  type HomeEvent,
  type HomeRow,
} from "@/components/home/chain-screens";
import { GlobalGrid } from "@/components/home/global-grid";
import { GatesScreen, type GateBar } from "@/components/home/gates-screen";
import { Screen } from "@/components/home/reveal";
import { Stat, blueprint as bp } from "@/components/blueprint";
import {
  chainEvents,
  coverage,
  evidence,
  activities as allActivities,
  gates,
  gatesOfActivity,
  marketEdges,
  progress,
  snapshotExists,
} from "@/lib/snapshot";
import s from "@/components/home/home.module.css";

/**
 * Six screens, in the order the finding actually travels: an update happened,
 * it landed on some work, that work belongs to markets, those markets are
 * served by occupations, here is the whole catalogue for scale, and here is
 * what is holding the rest of it still.
 *
 * The page does not explain the method. Every "why is it counted this way"
 * belongs in the whitepaper and every "how" in the repository; a homepage that
 * argues for its own method has stopped showing the reader anything.
 */

// How many readings screen 2 draws per update. The fan is meant to be read at a
// glance; the full list of an update's readings lives on the market pages, and
// the row underneath says how many were left off rather than implying these are
// all of them.
const READINGS_SHOWN = 12;

const copy = bilingual({
  en: {
    eyebrow: "UPDATED {date}",
    headline: "How far AI has taken over the world",
    ask: "Will AI kill your idea? Replace what you do?",
    lead: "Every AI update could change your answer.",
    statLookedLabel: "Assessed",
    statLookedNote: "of every hundred pieces of catalogued work. {total} in the catalogue.",
    statAloneLabel: "Running with nobody",
    statAloneNote: "activities deliver alone in any setting. The top rung is published empty, because empty is the finding.",
    activitiesUnit: "activities",
    s5Eyebrow: "05 — The whole picture",
    s5Title: "All catalogued work, as a hundred squares",
    s5Note: "Every catalogued piece of work, in a hundred squares.",
    gridLabel: "All catalogued work as a hundred squares",
    assessed: "{n} of these 100 squares have been assessed.",
    bulk: "{n} of them AI produces the bulk of, leaving a person to check.",
    none5: "None runs anywhere with nobody.",
    blanks: "{unknown} unknown — no evidence either way. {untouched} never mentioned by any update we collected.",
    s6Eyebrow: "06 — Why it is still stuck",
    s6Title: "What does not lift when models improve",
    s6Note: "Conditions a model release does not move.",
    statGateLabel: "Held by a gate",
    statGateNote: "activities. {top} of them need a body in the room.",
    s6After: "A barrier does not lift when models improve. Work behind one can reach L3 at most.",
    gatesLabel: "Gates by the number of activities behind them",
    gateUnit: "activities",
    gateOpen: "Open a gate to see what it is and why it has not lifted.",
    gateHolds: "Still closed",
    gateNoReason: "No check has been recorded against this gate yet.",
    gateExamples: "For example",
    closing: "Machine-proposed, unconfirmed by a person · {first} → {last}",
    method: "Method and every wrong turn → Whitepaper",
    repo: "Source and data → GitHub",
    noSnapshot:
      "No snapshot has been exported to this site yet. This is an empty state, not a finding.",
  },
  "zh-CN": {
    eyebrow: "更新于 {date}",
    headline: "AI 接管世界的进度",
    ask: "AI 会杀死你的想法？取代你的工作能力？",
    lead: "每一次 AI 更新，都可能会挑战你的答案。",
    statLookedLabel: "已评估",
    statLookedNote: "每一百份已编目的工作里。目录共 {total} 份。",
    statAloneLabel: "无人运行",
    statAloneNote: "条活动能在任何场景下不用人。最高档公布为空，因为「空」本身就是结论。",
    activitiesUnit: "条活动",
    s5Eyebrow: "05 — 全局",
    s5Title: "已编目的全部工作，化为一百格",
    s5Note: "每一份已编目的工作，摊进一百格。",
    gridLabel: "已编目的全部工作，化为一百格",
    assessed: "这 100 格里，只有 {n} 格被评估过。",
    bulk: "其中 {n} 格 AI 已经出主体，人只做复核。",
    none5: "没有一格做到全场景无人。",
    blanks: "{unknown} 格未知——没有任何方向的证据。{untouched} 格从没被更新提到过。",
    s6Eyebrow: "06 — 为什么还卡着",
    s6Title: "模型变强也不会松动的东西",
    s6Note: "模型发布动不了的条件。",
    statGateLabel: "被闸门按住",
    statGateNote: "条活动。其中 {top} 条是人必须在场。",
    s6After: "非技术障碍不随模型变强而消失。被它挡住的工作，最高只能到 L3。",
    gatesLabel: "各道闸门按住的活动数",
    gateUnit: "项活动",
    gateOpen: "点开一道闸门，看它是什么、为什么还没松动。",
    gateHolds: "仍然关闭",
    gateNoReason: "还没有针对这道闸门记录过核查。",
    gateExamples: "例如",
    closing: "机器提议，未经人确认 · {first} → {last}",
    method: "方法与全部弯路 → 白皮书",
    repo: "源码与数据 → GitHub",
    noSnapshot: "还没有任何快照导出到本站。这是一个空状态，不是一个结论。",
  },
});

export default async function Home() {
  const { language } = await getLocale();
  const c = copy[language];

  if (!snapshotExists || !progress) {
    return (
      <section className="hero market-hero">
        <h1>{c.headline}</h1>
        <p className="hero-ask">{c.ask}</p>
        <p className="lead">{c.lead}</p>
        <p className={s.note}>{c.noSnapshot}</p>
      </section>
    );
  }

  // --- screen 5: the whole catalogue ---------------------------------------
  const counts: WorkGridCounts = {};
  for (const row of progress.global ?? []) {
    // A blank square carries which kind of blank it is: asked and unresolved,
    // or never asked at all. They are different findings and never merge.
    const key: StageKey =
      row.stage === null ? (row.coverage as StageKey) : (String(row.stage) as StageKey);
    counts[key] = (counts[key] ?? 0) + row.work_items;
  }
  const squares = apportion(counts, 100);
  const assessedSquares = (["0", "1", "2", "3", "4", "5"] as StageKey[]).reduce(
    (n, k) => n + squares[k],
    0,
  );
  const bulkSquares = (["2", "3", "4", "5"] as StageKey[]).reduce((n, k) => n + squares[k], 0);

  // --- screens 1-4: the chain ----------------------------------------------
  //
  // Every join the four screens need is done once, here, and shipped resolved.
  // Doing them in the browser would mean sending the whole chain so the client
  // could rebuild what the server already knows.
  const occupationGroup = new Map(
    Object.entries(progress.occupations ?? {}).map(([id, entry]) => [id, entry.group_id]),
  );
  const marketToGroups = new Map<string, Set<string>>();
  for (const edge of marketEdges) {
    const group = occupationGroup.get(edge.occupation_id);
    if (!group) continue;
    const found = marketToGroups.get(edge.market_id);
    if (found) found.add(group);
    else marketToGroups.set(edge.market_id, new Set([group]));
  }

  const activityIndex = new Map(allActivities.map((a) => [a.activity_id, a]));
  const gateLabel = new Map(
    gates.map((g) => [
      g.gate_id,
      (language === "zh-CN" ? g.label_zh_cn : g.label_en) ?? g.label_en,
    ]),
  );
  const readingsByEvent = new Map<string, typeof evidence>();
  for (const row of evidence) {
    const found = readingsByEvent.get(row.event_id);
    if (found) found.push(row);
    else readingsByEvent.set(row.event_id, [row]);
  }

  const homeEvents: HomeEvent[] = chainEvents.map((event) => {
    const rows = (readingsByEvent.get(event.event_id) ?? [])
      .slice()
      .sort((a, b) => (b.level ?? -1) - (a.level ?? -1));
    const marketIds: string[] = [];
    const groupIds = new Set<string>();
    for (const row of rows) {
      const market = activityIndex.get(row.activity_id)?.market_id;
      if (!market) continue;
      if (!marketIds.includes(market)) marketIds.push(market);
      for (const group of marketToGroups.get(market) ?? []) groupIds.add(group);
    }
    return {
      id: event.event_id,
      title: event.title,
      date: event.occurred_at,
      org: event.org_name,
      activities: event.activities,
      markets: event.markets,
      top: event.top_level,
      tier: event.best_tier,
      urls: event.source_urls,
      marketIds,
      groupIds: [...groupIds],
      readings: rows.slice(0, READINGS_SHOWN).map((row) => ({
        id: row.activity_id,
        level: row.level,
        judged: row.observed_level,
        tier: row.evidence_tier,
      })),
    };
  });

  // One entry per activity the screens can show, not one per reading: the same
  // 130 activities carry all 710 readings, and sending their labels per reading
  // is the payload's single largest avoidable cost.
  const homeActivities: Record<string, HomeActivity> = {};
  for (const event of homeEvents) {
    for (const row of event.readings) {
      if (homeActivities[row.id]) continue;
      const activity = activityIndex.get(row.id);
      homeActivities[row.id] = {
        en: activity?.label_en ?? row.id,
        zh: activity?.label_zh_cn ?? null,
        market: activity?.market_id ?? null,
        tasks: activity?.tasks ?? 0,
        gates: gatesOfActivity(row.id).map((id) => gateLabel.get(id) ?? id),
      };
    }
  }

  const marketRows: Record<string, HomeRow<`/markets/${string}`>> = {};
  for (const [id, entry] of Object.entries(progress.markets ?? {})) {
    marketRows[id] = {
      id,
      label: (language === "zh-CN" ? entry.label_zh_cn : entry.label_en) ?? entry.label_en ?? id,
      tasks: entry.tasks,
      counts: entry.by_stage,
      href: `/markets/${id.replace(/^oaw:market:/, "")}` as const,
    };
  }

  const groupRows: HomeRow<`/occupations/g/${string}`>[] = Object.entries(progress.groups ?? {}).map(([id, group]) => ({
    id,
    label: (language === "zh-CN" ? group.label_zh_cn : group.label_en) ?? group.label_en ?? id,
    tasks: group.tasks,
    counts: group.by_stage,
    href: `/occupations/g/${id.replace(/^oaw:occupation-group:/, "")}` as const,
  }));

  // --- screen 6: the gates -------------------------------------------------
  // Which activities each gate actually holds, so a bar can name three of them
  // instead of asking the reader to take the count on trust.
  const gateExamples = new Map<string, string[]>();
  for (const activity of allActivities) {
    if ((activity.gates ?? 0) === 0) continue;
    for (const gate of gatesOfActivity(activity.activity_id)) {
      const found = gateExamples.get(gate) ?? [];
      if (found.length >= 3) continue;
      found.push(
        (language === "zh-CN" ? activity.label_zh_cn : activity.label_en) ?? activity.label_en,
      );
      gateExamples.set(gate, found);
    }
  }

  const bars: GateBar[] = gates
    .map((gate) => ({
      id: gate.gate_id,
      label: (language === "zh-CN" ? gate.label_zh_cn : gate.label_en) ?? gate.label_en,
      type: gate.gate_type,
      typeLabel: gate.gate_type,
      definition:
        (language === "zh-CN" ? gate.definition_zh_cn : gate.definition_en) ??
        gate.definition_en ??
        null,
      status: gate.status,
      reason: gate.state_rationale,
      examples: gateExamples.get(gate.gate_id) ?? [],
      activities: (gate.candidate_activities ?? 0) + (gate.reviewed_activities ?? 0),
    }))
    .sort((a, b) => b.activities - a.activities);
  const held = allActivities.filter((a) => (a.gates ?? 0) > 0).length;
  const presence = bars
    .filter((b) => b.type === "physical_presence")
    .reduce((n, b) => Math.max(n, b.activities), 0);

  const window = coverage?.collection_window;
  const windowTag =
    window?.first && window?.last
      ? `${window.first.slice(0, 10)} → ${window.last.slice(5, 10)}`
      : undefined;
  const total = progress.work_items_total ?? 0;
  const latest = chainEvents.at(-1)?.occurred_at ?? null;

  return (
    <>
      <section className={`${s.hero} ${bp.canvas}`}>
        {latest ? (
          <p className="eyebrow">
            <span className="dot" />
            {c.eyebrow.replace("{date}", latest.slice(0, 10))}
          </p>
        ) : null}
        <h1 className={s.heroTitle}>{c.headline}</h1>
        <p className={s.heroAsk}>{c.ask}</p>
        <p className={s.heroLead}>{c.lead}</p>

        {/* The two numbers worth a display size. Everything else on this page
            is a way of getting to one of them. */}
        <div className={s.heroStats}>
          <Stat
            label={c.statLookedLabel}
            tag={windowTag}
            value={assessedSquares}
            unit="/ 100"
            note={
              <p>
                {c.statLookedNote.replace("{total}", new Intl.NumberFormat("en-US").format(total))}
              </p>
            }
          />
          <Stat
            label={c.statAloneLabel}
            tag={`${new Intl.NumberFormat("en-US").format(allActivities.length)} ${c.activitiesUnit}`}
            value={0}
            tone="correction"
            note={<p>{c.statAloneNote}</p>}
          />
        </div>
      </section>

      <ChainScreens
        events={homeEvents}
        activities={homeActivities}
        markets={marketRows}
        groups={groupRows}
        levels={progress.levels ?? {}}
        tierCaps={progress.tier_caps ?? {}}
        language={language}
        updatesTotal={coverage?.events_routed ?? chainEvents.length}
        marketsTotal={Object.keys(progress.markets ?? {}).length}
      />

      <Screen id="global" className={`${s.screen} ${bp.canvas}`}>
        <p className={s.eyebrow}>{c.s5Eyebrow}</p>
        <h2 className={s.h2}>{c.s5Title}</h2>
        <p className={s.note}>{c.s5Note}</p>
        <GlobalGrid
          counts={counts}
          assessed={assessedSquares}
          bulk={bulkSquares}
          unknown={squares.unknown}
          untouched={squares.untouched}
          lines={{
            assessed: c.assessed,
            bulk: c.bulk,
            none5: c.none5,
            blanks: c.blanks,
            label: c.gridLabel,
          }}
        />
      </Screen>

      <Screen id="gates" className={`${s.screen} ${bp.canvas}`}>
        <p className={s.eyebrow}>{c.s6Eyebrow}</p>
        <h2 className={s.h2}>{c.s6Title}</h2>
        <p className={s.note}>{c.s6Note}</p>
        <Stat
          label={c.statGateLabel}
          tag={`${allActivities.length} ${c.activitiesUnit}`}
          value={held}
          tone="warning"
          note={<p>{c.statGateNote.replace("{top}", String(presence))}</p>}
        />
        <GatesScreen
          bars={bars}
          language={language}
          lines={{
            label: c.gatesLabel,
            unit: c.gateUnit,
            open: c.gateOpen,
            holds: c.gateHolds,
            noReason: c.gateNoReason,
            examples: c.gateExamples,
          }}
        />
        <p className={s.capNote}>{c.s6After}</p>
      </Screen>

      <section className={s.screen}>
        <p className={s.note}>
          {c.closing
            .replace("{first}", window?.first?.slice(0, 10) ?? "")
            .replace("{last}", window?.last?.slice(0, 10) ?? "")}
        </p>
        <p className={s.exit}>
          <Link className="text-link" href="/whitepaper">
            {c.method}
          </Link>
        </p>
      </section>
    </>
  );
}
