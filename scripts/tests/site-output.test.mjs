import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const APP = join(ROOT, ".next", "server", "app");
const HAS_SNAPSHOT = existsSync(join(ROOT, "datasets", "published", "latest", "manifest.json"));
const FIXED = ["", "/markets", "/occupations", "/updates", "/voices", "/whitepaper"];

const html = (language, path) => readFileSync(join(APP, `${language}${path}.html`), "utf8");
const anchors = (page) => [...page.matchAll(/<a\b[^>]*\shref="([^"]+)"/g)].map((m) => m[1]);
const internal = (hrefs) => hrefs.filter((h) => h.startsWith("/") && !h.startsWith("//"));

test("the build exists", () => {
  assert.ok(existsSync(APP), "run `pnpm build` first");
});

test("every fixed page is prerendered in both languages", () => {
  for (const language of ["en", "zh-CN"]) {
    for (const path of FIXED) {
      assert.match(html(language, path), new RegExp(`<html[^>]*lang="${language}"`), `${language}${path}`);
    }
  }
});

test("a Chinese page links only to Chinese pages, an English page only to unprefixed ones", () => {
  for (const path of FIXED) {
    for (const link of internal(anchors(html("zh-CN", path)))) {
      assert.ok(link === "/zh-CN" || link.startsWith("/zh-CN/"), `zh-CN${path} links to ${link}`);
    }
    for (const link of internal(anchors(html("en", path)))) {
      assert.ok(!/^\/(en|zh-CN)(\/|$)/.test(link), `en${path} links to ${link}`);
    }
  }
});

test("detail pages are prerendered when there is a snapshot", { skip: !HAS_SNAPSHOT }, () => {
  for (const section of ["markets", "occupations", "updates", "work"]) {
    for (const language of ["en", "zh-CN"]) {
      const pages = readdirSync(join(APP, language, section)).filter((name) => name.endsWith(".html"));
      assert.ok(pages.length > 0, `${language}/${section} has no prerendered pages`);
    }
  }
});

const SITE = "https://openaiwill.com";
// Next writes the site root without its trailing slash; the two spell the same address.
const publicUrl = (language, path) => `${SITE}${language === "en" ? path : `/zh-CN${path}`}`;
const tag = (page, pattern) => page.match(pattern)?.[1] ?? null;

test("each page names its own address and its counterpart in the other language", () => {
  for (const language of ["en", "zh-CN"]) {
    for (const path of FIXED) {
      const page = html(language, path);
      const where = `${language}${path}`;
      assert.equal(tag(page, /<link rel="canonical" href="([^"]+)"/), publicUrl(language, path), where);
      assert.equal(tag(page, /<link rel="alternate" hrefLang="en" href="([^"]+)"/), publicUrl("en", path), where);
      assert.equal(tag(page, /<link rel="alternate" hrefLang="zh-CN" href="([^"]+)"/), publicUrl("zh-CN", path), where);
      assert.equal(tag(page, /<link rel="alternate" hrefLang="x-default" href="([^"]+)"/), publicUrl("en", path), where);
      assert.equal(tag(page, /<meta property="og:url" content="([^"]+)"/), publicUrl(language, path), where);
      assert.equal(tag(page, /<meta property="og:image" content="([^"]+)"/), `${SITE}/og/${language}.png`, where);
      assert.ok(tag(page, /<meta name="description" content="([^"]+)"/), where);
      assert.equal(tag(page, /<meta name="twitter:site" content="([^"]+)"/), "@openaiwill", where);
    }
  }
});

test("every page links to the project's accounts in the header and in the footer", () => {
  for (const language of ["en", "zh-CN"]) {
    for (const path of FIXED) {
      const links = anchors(html(language, path));
      for (const url of ["https://x.com/openaiwill", "https://discord.gg/ArVHw2K9X", "https://github.com/feyn-machines/openaiwill"]) {
        assert.equal(links.filter((link) => link === url).length, 2, `${language}${path}: ${url} should appear in header and footer`);
      }
    }
  }
});

test("the default title is the confirmed headline, not the retired one", () => {
  assert.match(html("en", ""), /<title>How far AI has taken over the world<\/title>/);
  assert.match(html("zh-CN", ""), /<title>AI 接管世界的进度<\/title>/);
  for (const language of ["en", "zh-CN"]) {
    for (const path of FIXED) assert.doesNotMatch(html(language, path), /<title>[^<]*Kill Your Idea/);
  }
});

test("no page claims a replacement share, a probability or a reviewed score", () => {
  const banned = /replacement rate|% of jobs|probability of failure|verified score|替代率|失败概率|已审核/i;
  for (const language of ["en", "zh-CN"]) {
    for (const path of FIXED) {
      const page = html(language, path);
      assert.doesNotMatch(tag(page, /<title>([^<]*)<\/title>/) ?? "", banned);
      assert.doesNotMatch(tag(page, /<meta name="description" content="([^"]+)"/) ?? "", banned);
    }
  }
});

const body = (name) => readFileSync(join(APP, `${name}.body`), "utf8");

test("robots.txt allows everything, names the AI crawlers, and points at the sitemap", () => {
  const robots = body("robots.txt");
  assert.match(robots, /Sitemap: https:\/\/openaiwill\.com\/sitemap\.xml/);
  assert.doesNotMatch(robots, /Disallow: \/\S/);
  for (const bot of ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
    "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "CCBot", "Bytespider"]) {
    assert.match(robots, new RegExp(`User-Agent: ${bot}\\b`, "i"), bot);
  }
});

test("every sitemap address is a prerendered page, with its counterpart", () => {
  const xml = body("sitemap.xml");
  const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  assert.ok(locs.length >= FIXED.length * 2);
  assert.equal(new Set(locs).size, locs.length, "duplicate addresses");
  for (const loc of locs) {
    assert.ok(loc.startsWith(`${SITE}/`) || loc === SITE, loc);
    const path = decodeURI(loc.slice(SITE.length)).replace(/\/$/, "");
    const file = path.startsWith("/zh-CN") ? path.slice(1) : `en${path}`;
    assert.ok(existsSync(join(APP, `${file}.html`)), `${loc} is not a prerendered page`);
  }
  assert.match(xml, /hreflang="zh-CN"/);
  assert.match(xml, /hreflang="x-default"/);
});
