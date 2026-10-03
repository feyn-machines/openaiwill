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
