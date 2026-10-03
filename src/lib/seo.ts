import type { Metadata } from "next";
import { LANGUAGES, bilingual, localizedPath, type Language } from "./i18n";
import { manifest as dataManifest } from "./snapshot";

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

/**
 * The full public address of `path` (written without a language prefix) in
 * `language`. The English home is the bare site address, the spelling Next
 * writes into each page's canonical link, so the sitemap and the page agree.
 */
export function absoluteUrl(language: Language, path: string): string {
  const local = localizedPath(language, path);
  return local === "/" ? SITE_URL : `${SITE_URL}${local}`;
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

const CONTEXT = "https://schema.org";

const organization = {
  "@type": "Organization",
  name: SITE_NAME,
  url: SITE_URL,
  logo: `${SITE_URL}/icon.svg`,
  sameAs: [X_URL, DISCORD_URL, GITHUB_URL],
} as const;

export function siteLd(language: Language): object[] {
  return [
    { "@context": CONTEXT, ...organization },
    {
      "@context": CONTEXT,
      "@type": "WebSite",
      name: SITE_NAME,
      url: absoluteUrl(language, "/"),
      inLanguage: language,
      description: siteCopy[language].description,
      publisher: organization,
    },
  ];
}

export function breadcrumbLd(language: Language, trail: { name: string; path: string }[]): object {
  return {
    "@context": CONTEXT,
    "@type": "BreadcrumbList",
    itemListElement: trail.map((step, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: step.name,
      item: absoluteUrl(language, step.path),
    })),
  };
}

/**
 * Written for machines, so the interface does not have to carry the sentence:
 * every reading in a snapshot is proposed by a model and no person has reviewed
 * it. An engine that quotes a number takes the status with it.
 */
const DATA_STATUS: Record<Language, string> = {
  en: "Machine-proposed, not reviewed by a person",
  "zh-CN": "由机器提出，尚未经人审核",
};

export function datasetLd(language: Language, page: { name: string; description: string; path: string }): object | null {
  const manifest = dataManifest();
  if (!manifest) return null;
  return {
    "@context": CONTEXT,
    "@type": "Dataset",
    name: page.name,
    description: page.description,
    url: absoluteUrl(language, page.path),
    inLanguage: language,
    creator: organization,
    version: `${manifest.method_version} / ontology ${manifest.schema_version}`,
    dateModified: manifest.generated_at,
    creativeWorkStatus: DATA_STATUS[language],
  };
}

export function articleLd(
  language: Language,
  page: { headline: string; description?: string; path: string; datePublished?: string | null; basedOn?: string[] },
): object {
  return {
    "@context": CONTEXT,
    "@type": "Article",
    headline: page.headline,
    ...(page.description ? { description: page.description } : {}),
    url: absoluteUrl(language, page.path),
    inLanguage: language,
    publisher: organization,
    ...(page.datePublished ? { datePublished: page.datePublished } : {}),
    ...(page.basedOn?.length ? { isBasedOn: page.basedOn } : {}),
  };
}
