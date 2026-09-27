import { LANGUAGES, bilingual, getLocale, getRequestUrl, languageHref, languageName, type Language } from "@/lib/i18n";

const copy = bilingual({
  en: {
    switchLabel: "Language",
    currentLanguage: "Current language",
    toEnglish: "Switch to English",
    toChinese: "Switch to Simplified Chinese",
  },
  "zh-CN": {
    switchLabel: "语言",
    currentLanguage: "当前语言",
    toEnglish: "切换到英文",
    toChinese: "切换到简体中文",
  },
});

/** Which sentence offers an option, said in the language the reader is reading. */
const SWITCH_KEY: Record<Language, "toEnglish" | "toChinese"> = {
  en: "toEnglish",
  "zh-CN": "toChinese",
};

/**
 * Language switch for the header. Plain anchors: no login, no JavaScript, and
 * no prefetching, so following one always reaches the server that saves the
 * choice. The current path and query are preserved.
 */
export async function LanguageSwitch() {
  const [{ language }, url] = await Promise.all([getLocale(), getRequestUrl()]);
  const c = copy[language];
  return (
    <nav className="oaw-lang" aria-label={c.switchLabel}>
      {LANGUAGES.map((option) => {
        const current = option === language;
        return (
          <a
            key={option}
            className={current ? "oaw-lang-option oaw-lang-option-current" : "oaw-lang-option"}
            href={languageHref(url, option)}
            hrefLang={option}
            lang={option}
            aria-current={current ? "true" : undefined}
          >
            {languageName(option)}
            <span className="oaw-sr-only" lang={language}>
              {" "}
              {current ? c.currentLanguage : c[SWITCH_KEY[option]]}
            </span>
          </a>
        );
      })}
    </nav>
  );
}
