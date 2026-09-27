import type { Metadata } from "next";
import { getLocale } from "@/lib/i18n";
import {
  chainEvents,
  coverage,
  evidence,
  events,
  activityById,
  progress,
  snapshotExists,
} from "@/lib/snapshot";
import {
  Caveats,
  DataPageLinks,
  Missing,
  NoSnapshot,
  PageHeader,
  Provenance,
  Status,
  TableScroll,
  bilingual,
  dataStyles as d,
  formatNumber,
  isoDate,
} from "@/components/data-page";
import { Bar, Block, Head, Stat, blueprint as b } from "@/components/blueprint";
import { Screen } from "@/components/home/reveal";
import { UpdatesBrowser, type UpdateRow } from "./updates-browser";
import s from "./updates.module.css";

/**
 * What 581 updates turned out to be worth.
 *
 * The claim of this page is a ratio and a skew: we read 581 updates, 256 of them
 * bore on any work at all, and where they came from is nothing like even -
 * Google alone filed more than a quarter. Both are numbers, so both are drawn,
 * not described. The 325 that landed on nothing are listed WITH the rest,
 * because a feed filtered down to the productive half would imply a collection
 * far better than the one we ran.
 *
 * Every row is rendered here, on the server. The browser component adds search,
 * the publisher filter, the sort and the per-update readings on top of a list
 * that is already complete with JavaScript off.
 *
 * There is deliberately no `/updates/[id]`: a page of ours restating a post we
 * did not write adds a hop and a chance to distort, so the title is the link and
 * it leaves the site.
 */

const copy = bilingual({
  en: {
    eyebrow: "Updates",
    title: "AI updates",
    lead: "581 updates read; 256 of them bore on any work at all.",
    windowLabel: "Collection window",
    statRead: "Updates read",
    statLanded: "Landed on work",
    statSilent: "Landed on nothing",
    legendLanded: "{n} landed on work",
    legendRest: "{n} bore on no activity",
    fromEyebrow: "Where they came from",
    fromTitle: "The feed is not even",
    fromLead: "Pick a publisher to hold the table to it.",
    tableEyebrow: "Every update",
    tableTitle: "All 581, newest first",
    tableLead: "The ones that landed on nothing are listed too.",
    tableLabel: "Updates table",
    searchLabel: "Search titles and publishers",
    searchPlaceholder: "agent, robot, Gemini…",
    filterLabel: "Show",
    filterAll: "All",
    filterLanded: "Landed",
    filterSilent: "Landed on nothing",
    sortLabel: "Sort",
    sortTime: "Newest",
    sortReach: "Most work reached",
    showing: "{n} of {total} shown",
    empty: "No update matches this search, this publisher and this filter together. Widen one of them; nothing was hidden.",
    reset: "Clear",
    colWhen: "When",
    colUpdate: "Update",
    colFrom: "From",
    colLanded: "Landed on (activities / markets)",
    colTop: "Highest",
    runsEyebrow: "Provenance",
    runsTitle: "The runs that produced these rows",
    runsLead: "Every pass that read the collection, and whether it finished.",
    colRun: "Method",
    colStatus: "Status",
    colDecided: "Decided",
    colStarted: "Started",
    noDecided: "This run recorded no decision count.",
    openSource: "opens the original post",
    readingsOpen: "{n} readings",
    readingsClose: "Hide readings",
    noDate: "No publication time was recorded for this update.",
    noOrg: "No publisher was resolved for this update.",
    noSource: "No source URL was retained for this update.",
    noLevel: "none",
    capNote: "capped {cap}",
    empty0: "No updates are published in this snapshot.",
  },
  "zh-CN": {
    eyebrow: "更新",
    title: "AI 更新",
    lead: "读了 581 条更新，其中 256 条真的落到了某件工作上。",
    windowLabel: "采集窗口",
    statRead: "读过的更新",
    statLanded: "落到工作上",
    statSilent: "没落到",
    legendLanded: "{n} 条落到工作",
    legendRest: "{n} 条没落到任何活动",
    fromEyebrow: "来自哪里",
    fromTitle: "来源严重偏斜",
    fromLead: "点一个发布方，下面的表就只看它。",
    tableEyebrow: "全部更新",
    tableTitle: "581 条，最新在前",
    tableLead: "没落到工作上的也列在里面。",
    tableLabel: "更新表",
    searchLabel: "搜标题和发布方",
    searchPlaceholder: "智能体、机器人、Gemini…",
    filterLabel: "只看",
    filterAll: "全部",
    filterLanded: "落到工作",
    filterSilent: "没落到",
    sortLabel: "排序",
    sortTime: "最新",
    sortReach: "打到的工作最多",
    showing: "显示 {n} / {total}",
    empty: "这个搜索词、这个发布方、这个筛选三个条件同时满足的更新一条也没有。放宽其中一个；没有任何内容被隐藏。",
    reset: "清空",
    colWhen: "时间",
    colUpdate: "更新",
    colFrom: "来自",
    colLanded: "落到（活动 / 赛道）",
    colTop: "最高",
    runsEyebrow: "溯源",
    runsTitle: "产出这些行的运行",
    runsLead: "每一次读过采集的判断轮次，以及它有没有跑完。",
    colRun: "方法",
    colStatus: "状态",
    colDecided: "已判定",
    colStarted: "开始",
    noDecided: "这次运行没有记录判定数。",
    openSource: "打开原帖",
    readingsOpen: "{n} 条读数",
    readingsClose: "收起读数",
    noDate: "这条更新没有记录发布时间。",
    noOrg: "这条更新没有解析出发布方。",
    noSource: "这条更新没有保留源头链接。",
    noLevel: "无",
    capNote: "{cap} 封顶",
    empty0: "本次快照没有发布任何更新。",
  },
});

export async function generateMetadata(): Promise<Metadata> {
  const { language } = await getLocale();
  const c = copy[language];
  return { title: c.title, description: c.lead };
}

/** Run status as words. A failed run must not read as one still in progress. */
const RUN_STATUS_NAMES: Record<string, Record<string, string>> = {
  en: { completed: "Completed", running: "Running", failed: "Failed" },
  "zh-CN": { completed: "已完成", running: "进行中", failed: "失败" },
};

/**
 * The marker shape per status, as a table rather than as a condition.
 *
 * `failed` gets `attention` and `running` gets `pending`: a broken pass and a
 * pass still writing are different facts, and drawing them the same turns a
 * broken pipeline into a wait nobody investigates.
 */
const RUN_STATUS_SHAPES: Record<string, "solid" | "pending" | "attention"> = {
  completed: "solid",
  running: "pending",
  failed: "attention",
};

export default async function UpdatesPage() {
  const { language } = await getLocale();
  const c = copy[language];
  if (!snapshotExists) {
    return (
      <div className={s.page}>
        <PageHeader eyebrow={c.eyebrow} title={c.title} lead={c.lead} />
        <NoSnapshot language={language} />
      </div>
    );
  }

  // The ladder's own words, read from the snapshot. Nothing in src/ restates
  // them: pnpm semantic:check fails the build if anything does.
  const words = progress?.levels ?? {};
  const caps = progress?.tier_caps ?? null;
  const rung = (level: number | null | undefined): string | null => {
    if (level === null || level === undefined) return null;
    const step = String(Math.floor(level));
    const word = words[step]?.[language];
    return word ? `L${step} · ${word}` : `L${step}`;
  };

  const landed = new Map(chainEvents.map((e) => [e.event_id, e]));
  const readingsByEvent = new Map<string, UpdateRow["readings"]>();
  for (const row of evidence) {
    const activity = activityById(row.activity_id);
    const list = readingsByEvent.get(row.event_id) ?? [];
    const tier = row.evidence_tier as keyof NonNullable<typeof caps>;
    const cap = caps?.[tier];
    list.push({
      activity:
        (language === "zh-CN" ? activity?.label_zh_cn : activity?.label_en) ??
        activity?.label_en ??
        row.activity_id,
      market: (language === "zh-CN" ? activity?.market_zh_cn : activity?.market_en) ?? null,
      level: rung(row.level),
      // Only when the tier actually held the reading down: a cap that did not
      // bite is machinery, and saying so on every row would be noise.
      cap:
        cap !== undefined &&
        row.observed_level !== null &&
        row.level !== null &&
        row.observed_level > row.level
          ? `${row.evidence_tier} → L${cap}`
          : null,
    });
    readingsByEvent.set(row.event_id, list);
  }

  const rows: UpdateRow[] = [...events]
    .sort((a, b) => (b.occurred_at ?? "").localeCompare(a.occurred_at ?? ""))
    .map((row) => {
      const hit = landed.get(row.event_id);
      return {
        id: row.event_id,
        title: row.title,
        date: isoDate(row.occurred_at),
        org: (language === "zh-CN" ? row.org_name_zh_cn : row.org_name) ?? row.org_name,
        orgKey: row.org_name,
        url: row.source_urls?.[0] ?? null,
        activities: hit?.activities ?? 0,
        markets: hit?.markets ?? 0,
        level: rung(hit?.top_level),
        readings: readingsByEvent.get(row.event_id) ?? [],
      };
    });

  // A snapshot exported while a run is still writing can arrive without these.
  // An absent array is an empty state with a reason, never a zero.
  const runs = coverage?.judgment_runs ?? [];
  const routed = coverage?.events_routed ?? rows.length;
  const bearing = coverage?.events_bearing_on_activity ?? landed.size;
  const silent = Math.max(routed - bearing, 0);
  const window = coverage?.collection_window;
  const windowTag =
    window?.first && window?.last
      ? `${isoDate(window.first)} → ${isoDate(window.last)}`
      : undefined;
  const share = (n: number) => (routed > 0 ? `${Math.round((n / routed) * 100)}%` : undefined);

  // coverage names publishers in the registry's English; the table shows the
  // reader's language. The chart keeps the key and shows the label.
  const orgLabels = new Map<string, string>();
  for (const row of events) {
    if (!row.org_name) continue;
    orgLabels.set(
      row.org_name,
      ((language === "zh-CN" ? row.org_name_zh_cn : row.org_name) ?? row.org_name) as string,
    );
  }
  const orgs = (coverage?.events_by_organisation ?? [])
    .filter((o) => o.events > 0)
    .map((o) => ({ ...o, label: orgLabels.get(o.org) ?? o.org }));
  const maxActivities = Math.max(1, ...rows.map((r) => r.activities));

  return (
    <div className={s.page}>
      <PageHeader eyebrow={c.eyebrow} title={c.title} lead={c.lead} />

      {/* The claim, as three numbers on one baseline. */}
      <Screen className={`${s.readout} ${b.canvas}`}>
        <Head label={c.windowLabel} tag={windowTag} tone="plain" />
        <div className={s.stats}>
          <Stat label={c.statRead} value={formatNumber(routed)} tone="plain" />
          <Stat
            label={c.statLanded}
            tag={share(bearing)}
            value={formatNumber(bearing)}
            tone="signal"
          />
          <Stat
            label={c.statSilent}
            tag={share(silent)}
            value={formatNumber(silent)}
            tone="correction"
          />
        </div>
        <div className={s.split}>
          <span className={s.track}>
            <Bar
              share={routed > 0 ? bearing / routed : 0}
              label={c.legendLanded.replace("{n}", formatNumber(bearing))}
            />
          </span>
          <p className={s.legend}>
            <span>{c.legendLanded.replace("{n}", formatNumber(bearing))}</span>
            <span className={s.legendRest}>
              {c.legendRest.replace("{n}", formatNumber(silent))}
            </span>
          </p>
        </div>
      </Screen>

      {rows.length === 0 ? (
        <p className={d.note}>{c.empty0}</p>
      ) : (
        <UpdatesBrowser
          rows={rows}
          orgs={orgs}
          maxActivities={maxActivities}
          copy={{
            fromEyebrow: c.fromEyebrow,
            fromTitle: c.fromTitle,
            fromLead: c.fromLead,
            tableEyebrow: c.tableEyebrow,
            tableTitle: c.tableTitle,
            tableLead: c.tableLead,
            tableLabel: c.tableLabel,
            searchLabel: c.searchLabel,
            searchPlaceholder: c.searchPlaceholder,
            filterLabel: c.filterLabel,
            filterAll: c.filterAll,
            filterLanded: c.filterLanded,
            filterSilent: c.filterSilent,
            sortLabel: c.sortLabel,
            sortTime: c.sortTime,
            sortReach: c.sortReach,
            showing: c.showing,
            empty: c.empty,
            reset: c.reset,
            colWhen: c.colWhen,
            colUpdate: c.colUpdate,
            colFrom: c.colFrom,
            colLanded: c.colLanded,
            colTop: c.colTop,
            openSource: c.openSource,
            readingsOpen: c.readingsOpen,
            readingsClose: c.readingsClose,
            noDate: c.noDate,
            noOrg: c.noOrg,
            noSource: c.noSource,
            noLevel: c.noLevel,
            capNote: c.capNote,
          }}
        />
      )}

      {/* The extraction runs that produced these updates.
          This lived on /about, which the user removed; the runs are the
          provenance of THIS page's rows, so they belong here rather than
          nowhere. The status is mapped to words because "failed" and
          "running" must never render as the same neutral token - a failed run
          that reads as in-progress turns a broken pipeline into a wait. */}
      {runs.length > 0 ? (
        <Block eyebrow={c.runsEyebrow} title={c.runsTitle} lead={c.runsLead}>
          <TableScroll label={c.runsTitle}>
            <thead>
              <tr>
                <th scope="col">{c.colRun}</th>
                <th scope="col">{c.colStatus}</th>
                <th scope="col" className="oaw-num">{c.colDecided}</th>
                <th scope="col">{c.colStarted}</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.run_id}>
                  <th scope="row" className={d.mono}>{run.method_version}</th>
                  <td>
                    <Status shape={RUN_STATUS_SHAPES[run.status] ?? "solid"}>
                      {RUN_STATUS_NAMES[language][run.status] ?? run.status}
                    </Status>
                  </td>
                  <td className="oaw-num">
                    {run.decided_count === null ? (
                      <Missing reason={c.noDecided} language={language} inline />
                    ) : (
                      formatNumber(run.decided_count)
                    )}
                  </td>
                  <td className={d.mono}>{isoDate(run.started_at) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </TableScroll>
        </Block>
      ) : null}

      <Provenance language={language} />
      <Caveats language={language} />
      <DataPageLinks language={language} current="updates" />
    </div>
  );
}
