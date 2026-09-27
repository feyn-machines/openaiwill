/**
 * Language selection for the bilingual site.
 *
 * Precedence, per CLAUDE.md / DESIGN.md: an explicit language in the URL wins,
 * then a saved user choice, then English. The browser `Accept-Language` header
 * is deliberately never consulted, so a Chinese browser still opens the English
 * default until the reader chooses otherwise.
 *
 * This module has no static `next/*` imports on purpose: `src/proxy.ts` (edge)
 * and `scripts/tests/test_i18n_unit.mjs` (plain node) both import the pure
 * resolver, and `next/headers` cannot be loaded outside a server render.
 */

export const LANGUAGES = ["en", "zh-CN"] as const;
export type Language = (typeof LANGUAGES)[number];

/** Shown first when nobody has chosen a language. */
export const DEFAULT_LANGUAGE: Language = "en";

/** Query parameter that carries an explicit language in a shared link. */
export const LANGUAGE_PARAM = "lang";

/** Cookie holding the saved choice. Readable by the browser; no login needed. */
export const LANGUAGE_COOKIE = "openaiwill_language";

/** One year, refreshed on every explicit choice. */
export const LANGUAGE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

/** Request header the proxy uses to hand the validated URL language to the render. */
export const LANGUAGE_HEADER = "x-openaiwill-language";

/** Request header the proxy uses to hand the current path + query to the render. */
export const REQUEST_URL_HEADER = "x-openaiwill-url";

const LANGUAGE_NAMES: Record<Language, string> = { en: "EN", "zh-CN": "中文" };

/** The label for a language, written in that language. */
export function languageName(language: Language): string {
  return LANGUAGE_NAMES[language];
}

/**
 * Accepts only the two published tags, case-insensitively. Anything else —
 * an unknown tag, an empty string, a repeated parameter, `null` — returns
 * `null` so the caller falls back instead of throwing.
 */
export function normalizeLanguage(value: unknown): Language | null {
  if (typeof value !== "string") return null;
  const tag = value.trim().toLowerCase();
  return LANGUAGES.find((language) => language.toLowerCase() === tag) ?? null;
}

export type LanguageRequest = {
  /** Raw `?lang=` value from the request URL, if the reader supplied one. */
  urlLanguage?: string | null;
  /** Raw saved choice, normally the language cookie. */
  savedLanguage?: string | null;
};

/** URL language, then saved choice, then English. Never the browser preference. */
export function resolveLanguage(request: LanguageRequest = {}): Language {
  return normalizeLanguage(request.urlLanguage)
    ?? normalizeLanguage(request.savedLanguage)
    ?? DEFAULT_LANGUAGE;
}

/**
 * Reads `?lang=` out of a full URL, a path with a query, or a bare query
 * string. Unparseable or unknown values return `null` rather than throwing.
 */
export function urlLanguage(url: string | null | undefined): Language | null {
  if (!url) return null;
  const withoutHash = url.split("#")[0];
  const mark = withoutHash.indexOf("?");
  const query = mark === -1 ? withoutHash : withoutHash.slice(mark + 1);
  return normalizeLanguage(new URLSearchParams(query).get(LANGUAGE_PARAM));
}

/** The same path and query with the language parameter set to `language`. */
export function languageHref(url: string | null | undefined, language: Language): string {
  const fallback = `?${LANGUAGE_PARAM}=${language}`;
  if (!url) return fallback;
  try {
    const target = new URL(url, "http://openaiwill.invalid");
    target.searchParams.set(LANGUAGE_PARAM, language);
    return `${target.pathname}${target.search}`;
  } catch {
    return fallback;
  }
}

/**
 * Both languages, enforced by the type: a block of copy cannot be written in
 * one language only, because the Chinese record must carry every English key.
 *
 * It lives here rather than beside the data-page components so that any page
 * can declare its copy without importing from one.
 */
export function bilingual<T extends Record<string, string>>(copy: {
  en: T;
  "zh-CN": Record<keyof T, string>;
}): Record<Language, Record<keyof T, string>> {
  return copy;
}

/**
 * The current request language. Server Components only: reading the request
 * opts the route into dynamic rendering.
 */
export async function getLocale(): Promise<{ language: Language }> {
  const { cookies, headers } = await import("next/headers");
  const [cookieStore, requestHeaders] = await Promise.all([cookies(), headers()]);
  const language = resolveLanguage({
    urlLanguage: requestHeaders.get(LANGUAGE_HEADER),
    savedLanguage: cookieStore.get(LANGUAGE_COOKIE)?.value,
  });
  return { language };
}

/** The current path and query, as handed over by the proxy. */
export async function getRequestUrl(): Promise<string | null> {
  const { headers } = await import("next/headers");
  return (await headers()).get(REQUEST_URL_HEADER);
}
