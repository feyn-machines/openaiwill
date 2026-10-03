/** Level ruler v4. The one place the level names are written; pages and the snapshot reader both take them from here. */
export const LEVEL_NAMES = {
  en: ["Manual", "Assisted", "Partial automation", "Conditional automation", "High automation", "Full automation"],
  "zh-CN": ["人工", "辅助", "部分自动化", "有条件自动化", "高度自动化", "完全自动化"],
} as const;
