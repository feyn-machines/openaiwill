/**
 * Guards on text the reader sees, checked against the data that actually
 * reaches the site.
 *
 * These exist because three separate bugs shipped past a green typecheck: a
 * count key the publisher emits and the label map did not define, so the site
 * printed `gate_tasks` at readers in both languages; a provenance marker that
 * told Chinese readers "only Chinese was published" over English text; and a
 * root layout whose metadata was English for everyone. None of them is a type
 * error, and none is visible without comparing source against snapshot.
 */
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const root = new URL("../../", import.meta.url);
const read = (path) => readFileSync(fileURLToPath(new URL(path, root)), "utf8");
const manifest = JSON.parse(read("datasets/published/latest/manifest.json"));

/** Every page that exists, so deleting a route never fails a test by name. */
function pages(dir = "src/app") {
  const out = [];
  for (const entry of readdirSync(fileURLToPath(new URL(dir, root)), { withFileTypes: true })) {
    const next = `${dir}/${entry.name}`;
    if (entry.isDirectory()) out.push(...pages(next));
    else if (entry.name === "page.tsx") out.push(next);
  }
  return out;
}

test("every count the publisher emits has a label in both languages", () => {
  const source = read("src/components/data-page.tsx");
  const block = source.slice(source.indexOf("const countLabels = bilingual({"));
  const english = block.slice(block.indexOf("en: {"), block.indexOf('"zh-CN": {'));
  const chinese = block.slice(block.indexOf('"zh-CN": {'), block.indexOf("});"));
  for (const key of Object.keys(manifest.counts)) {
    // A dotted key ("chain.events") is not a valid bare identifier, so it is
    // written quoted. Both spellings are the same label.
    const spellings = [`${key}:`, `"${key}":`];
    assert.ok(spellings.some((form) => english.includes(form)),
      `no English label for manifest count "${key}"`);
    assert.ok(spellings.some((form) => chinese.includes(form)),
      `no Chinese label for manifest count "${key}"`);
  }
});

test("the original-language marker names the language it is actually showing", () => {
  const source = read("src/components/data-page.tsx");
  const block = source.slice(source.indexOf("export function OriginalLanguage"));
  // Reading an English page that fell back to Chinese, and the reverse. The bug
  // this replaces had one sentence for both directions, so one of them lied.
  assert.match(block, /shown === "zh-CN"[\s\S]{0,200}Published in Chinese only/);
  assert.match(block, /Published in English only/);
  assert.match(block, /shown === "en"[\s\S]{0,200}只发布了英文/);
  assert.match(block, /只发布了中文/);
  // And it says nothing at all when the text is in the reader's own language.
  assert.match(block, /if \(shown === reading\) return null;/);
});

test("no page states a language marker of its own", () => {
  // The per-page `originalZh` strings were what made the inversion possible:
  // six copies of one sentence, each assuming the fallback direction.
  for (const path of pages()) {
    assert.ok(!read(path).includes("originalZh"), `${path} still carries its own marker`);
  }
});

test("the root layout resolves metadata per reader rather than statically", () => {
  const source = read("src/app/layout.tsx");
  assert.ok(
    source.includes("export async function generateMetadata"),
    "a static `metadata` object cannot see the reader's language",
  );
  assert.ok(!/export const metadata/.test(source), "static metadata is still exported");
  assert.ok(source.includes("每一次 AI 更新"), "no Chinese description");
  // The confirmed English headline stays the default title in both languages.
  assert.ok(source.includes('default: "Will AI Kill Your Idea?"'));
});

test("run status is mapped to words, and failure does not read as in progress", () => {
  const found = pages().filter((path) => read(path).includes("RUN_STATUS_NAMES"));
  assert.equal(found.length, 1, "exactly one page should map run status");
  const source = read(found[0]);
  assert.match(source, /RUN_STATUS_NAMES\[language\]\[run\.status\]/);
  assert.match(source, /failed: "Failed"/);
  assert.match(source, /failed: "失败"/);
  assert.match(source, /failed: "attention"/);
});
