import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import ts from "typescript";

// `src/lib/i18n.ts` keeps no static `next/*` imports, so the real source can be
// type-stripped and loaded here. Node 22.17 cannot import `.ts` directly.
const SOURCE_PATH = fileURLToPath(new URL("../../src/lib/i18n.ts", import.meta.url));
const source = readFileSync(SOURCE_PATH, "utf8");
// Comments are dropped so the guard below reads the code, not the prose about it.
const javascript = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022, removeComments: true },
}).outputText;
const {
  DEFAULT_LANGUAGE,
  LANGUAGES,
  LANGUAGE_PARAM,
  languageHref,
  normalizeLanguage,
  resolveLanguage,
  urlLanguage,
} = await import(`data:text/javascript;charset=utf-8,${encodeURIComponent(javascript)}`);

const CHINESE_BROWSER = "zh-CN,zh;q=0.9,en;q=0.8";

test("the default language is English", () => {
  assert.equal(DEFAULT_LANGUAGE, "en");
  assert.deepEqual([...LANGUAGES], ["en", "zh-CN"]);
  assert.equal(resolveLanguage(), "en");
  assert.equal(resolveLanguage({}), "en");
  assert.equal(resolveLanguage({ urlLanguage: null, savedLanguage: null }), "en");
});

test("an explicit URL language beats a saved choice", () => {
  assert.equal(resolveLanguage({ urlLanguage: "zh-CN", savedLanguage: "en" }), "zh-CN");
  assert.equal(resolveLanguage({ urlLanguage: "en", savedLanguage: "zh-CN" }), "en");
});

test("a saved choice beats the default", () => {
  assert.equal(resolveLanguage({ savedLanguage: "zh-CN" }), "zh-CN");
  assert.equal(resolveLanguage({ urlLanguage: null, savedLanguage: "zh-CN" }), "zh-CN");
});

test("the browser language never decides", () => {
  // Accept-Language is not an input at all: a Chinese browser still gets English.
  assert.equal(resolveLanguage({ acceptLanguage: CHINESE_BROWSER }), "en");
  assert.equal(resolveLanguage({ savedLanguage: "en", acceptLanguage: CHINESE_BROWSER }), "en");
  assert.doesNotMatch(javascript.toLowerCase(), /accept-language|acceptlanguage/, "i18n.ts must not read Accept-Language");
  assert.doesNotMatch(javascript, /\bq=/, "i18n.ts must not parse Accept-Language quality values");
});

test("an unusable ?lang= value falls back instead of throwing", () => {
  for (const value of ["", " ", "de", "zh-TW", "en-US", "klingon", "zh-CN,en", "../../etc", "%%%", null, undefined, 7, {}, []]) {
    assert.equal(normalizeLanguage(value), null, `${JSON.stringify(value)} must not normalize`);
    assert.equal(resolveLanguage({ urlLanguage: value }), "en");
    assert.equal(resolveLanguage({ urlLanguage: value, savedLanguage: "zh-CN" }), "zh-CN");
  }
  assert.equal(resolveLanguage({ urlLanguage: "en", savedLanguage: "nonsense" }), "en");
  assert.equal(resolveLanguage({ savedLanguage: "nonsense" }), "en");
});

test("known tags are accepted whatever their case or padding", () => {
  for (const value of ["en", "EN", " en ", "\ten\n"]) assert.equal(normalizeLanguage(value), "en");
  for (const value of ["zh-CN", "zh-cn", "ZH-CN", " zh-CN "]) assert.equal(normalizeLanguage(value), "zh-CN");
});

test("the URL language is read from a full URL, a path or a bare query", () => {
  assert.equal(urlLanguage("https://openaiwill.com/domains?lang=zh-CN"), "zh-CN");
  assert.equal(urlLanguage("/domains?lang=en&group=health"), "en");
  assert.equal(urlLanguage("?lang=zh-CN"), "zh-CN");
  assert.equal(urlLanguage("lang=zh-CN"), "zh-CN");
  assert.equal(urlLanguage("/domains?lang=zh-CN#sources"), "zh-CN");
  assert.equal(urlLanguage("/domains"), null);
  assert.equal(urlLanguage("/domains?lang="), null);
  assert.equal(urlLanguage("/domains?lang=de"), null);
  assert.equal(urlLanguage("/domains?language=zh-CN"), null);
  assert.equal(urlLanguage(""), null);
  assert.equal(urlLanguage(null), null);
  assert.equal(urlLanguage(undefined), null);
  assert.equal(LANGUAGE_PARAM, "lang");
});

test("switching keeps the current path and its other parameters", () => {
  assert.equal(languageHref("/domains?group=health", "zh-CN"), "/domains?group=health&lang=zh-CN");
  assert.equal(languageHref("/domains?lang=en", "zh-CN"), "/domains?lang=zh-CN");
  assert.equal(languageHref("/", "zh-CN"), "/?lang=zh-CN");
  assert.equal(languageHref("/domains/health-ai", "en"), "/domains/health-ai?lang=en");
  // Without a known path, a relative href still keeps the reader on this page.
  assert.equal(languageHref(null, "zh-CN"), "?lang=zh-CN");
  assert.equal(languageHref("", "en"), "?lang=en");
});
