import type { Metadata } from "next";
import { LANGUAGES, bilingual, localizedPath, type Language } from "./i18n";

/** The public address. Not a secret and not per-environment: a candidate build names the same canonical pages. */
export const SITE_URL = "https://openaiwill.com";
export const SITE_NAME = "openaiwill";
/** The project's own account on X (user-confirmed 2026-10-03). */
export const X_HANDLE = "@openaiwill";
export const X_URL = "https://x.com/openaiwill";
/** The project's community invite on Discord (user-confirmed 2026-10-03). */
export const DISCORD_URL = "https://discord.gg/ArVHw2K9X";
/** The public source repository (user-confirmed 2026-10-03). */
export const GITHUB_URL = "https://github.com/feyn-machines/openaiwill";

/** The project's own places elsewhere, in the order the footer shows them. */
export const SOCIAL_LINKS = [
  { label: "X", href: X_URL },
  { label: "Discord", href: DISCORD_URL },
  { label: "GitHub", href: GITHUB_URL },
] as const;

/**
 * The words confirmed for the first screen on 2026-09-22 (DESIGN.md): the
 * headline as the default title, the question and its supporting line as the
 * default description.
 */
export const siteCopy = bilingual({
  en: {
    title: "How far AI has taken over the world",
    description: "Will AI kill your idea? Replace what you do? Every AI update could change your answer.",
  },
  "zh-CN": {
    title: "AI 接管世界的进度",
    description: "AI 会杀死你的想法？取代你的工作能力？每一次 AI 更新，都可能会挑战你的答案。",
  },
});

const OG_LOCALE: Record<Language, string> = { en: "en_US", "zh-CN": "zh_CN" };

/** The full public address of `path` (written without a language prefix) in `language`. */
export function absoluteUrl(language: Language, path: string): string {
  return `${SITE_URL}${localizedPath(language, path)}`;
}

/**
 * Everything a page tells a search engine about itself: its own address, the
 * same page in the other language, and the share card. `path` is written
 * without a language prefix.
 */
export function pageMetadata(page: { language: Language; path: string; title?: string; description?: string }): Metadata {
  const { language, path } = page;
  const site = siteCopy[language];
  const description = page.description ?? site.description;
  const shareTitle = page.title ?? site.title;
  const url = absoluteUrl(language, path);
  const image = `/og/${language}.png`;
  return {
    ...(page.title ? { title: page.title } : {}),
    description,
    alternates: {
      canonical: url,
      languages: {
        ...Object.fromEntries(LANGUAGES.map((l) => [l, absoluteUrl(l, path)])),
        "x-default": absoluteUrl("en", path),
      },
    },
    openGraph: {
      type: "website",
      siteName: SITE_NAME,
      url,
      title: shareTitle,
      description,
      locale: OG_LOCALE[language],
      images: [{ url: image, width: 1200, height: 630, alt: site.title }],
    },
    twitter: { card: "summary_large_image", site: X_HANDLE, title: shareTitle, description, images: [image] },
  };
}
