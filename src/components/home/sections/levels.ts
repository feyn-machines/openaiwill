import type { Language } from "@/lib/i18n";
import type { Both } from "@/lib/home-data";
import { LEVEL_NAMES as NAMES } from "@/lib/level-names";

/** L0-L5, level ruler v4. One source for every page. */
export const LEVEL_NAMES: Record<Language, readonly string[]> = NAMES;

export const TIER_NAMES: Record<Language, Record<string, string>> = {
  en: { T3: "From the publisher only", T2: "Confirmed by several sources", T1: "Independently confirmed" },
  "zh-CN": { T3: "仅来自发布方", T2: "多方印证", T1: "独立证实" },
};

export const pick = (both: Both, language: Language) => (language === "zh-CN" ? both.zh : both.en);

/** Fill for an accepted level: the same three steps on every module. */
export const levelClass = (level: number) => (level >= 3 ? "l3" : level === 2 ? "l2" : "l1");

export function isoDay(start: string, offset: number): string {
  const d = new Date(`${start}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + offset);
  return d.toISOString().slice(0, 10);
}

export const WEEKDAYS: Record<Language, string[]> = {
  en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
  "zh-CN": ["周日", "周一", "周二", "周三", "周四", "周五", "周六"],
};
