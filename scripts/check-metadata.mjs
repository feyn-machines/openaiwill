import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

export function validateCatalog(catalog) {
  const localized = (value, label) => {
    assert.ok(value && typeof value === "object", label);
    assert.deepEqual(Object.keys(value).sort(), ["en", "zh-CN"], `${label}: translations`);
    for (const locale of ["en", "zh-CN"]) assert.ok(typeof value[locale] === "string" && value[locale].trim(), `${label}: ${locale}`);
  };
  const index = (items, label) => {
    assert.ok(Array.isArray(items) && items.length, `${label}: empty`);
    const result = new Map();
    for (const item of items) {
      assert.match(item.id, /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/, `${label}: ID`);
      assert.ok(!result.has(item.id), `${label}: duplicate ID`);
      result.set(item.id, item);
    }
    return result;
  };
  assert.equal(catalog.kind, "startup-market-directory");
  assert.equal(catalog.coverageEvidencePolicy, "official-x-only");
  assert.equal(catalog.defaultLocale, "en");
  assert.deepEqual(catalog.locales, ["en", "zh-CN"]);
  assert.ok(!Object.hasOwn(catalog, "tasks"), "Occupational tasks are not the market directory");
  const sources = index(catalog.sources, "sources");
  const groups = index(catalog.groups, "groups");
  const markets = index(catalog.markets, "markets");
  for (const source of sources.values()) {
    const url = new URL(source.url);
    assert.equal(url.protocol, "https:");
    assert.equal(url.username + url.password, "", "No URL credentials");
    assert.ok(source.title && source.publisher);
    assert.ok(["market-report", "startup-profile", "product-website"].includes(source.kind));
    assert.match(source.accessedOn, /^\d{4}-\d{2}-\d{2}$/);
  }
  for (const group of groups.values()) {
    localized(group.name, group.id);
    assert.ok(catalog.markets.some((market) => market.groupId === group.id), `Empty group: ${group.id}`);
  }
  const names = new Set();
  for (const market of markets.values()) {
    assert.ok(groups.has(market.groupId), `${market.id}: unknown group`);
    for (const field of ["name", "summary", "question"]) localized(market[field], `${market.id}.${field}`);
    const name = market.name.en.toLowerCase();
    assert.ok(!names.has(name), `${market.id}: duplicate name`);
    names.add(name);
    assert.equal(market.classification, "editorial-market-category");
    assert.ok(Array.isArray(market.sourceIds) && market.sourceIds.length);
    for (const source of market.sourceIds) assert.ok(sources.has(source), `${market.id}: missing source`);
    assert.ok(Array.isArray(market.examples) && market.examples.length, `${market.id}: real product required`);
    for (const example of market.examples) {
      assert.ok(typeof example.name === "string" && example.name.trim());
      assert.ok(sources.has(example.sourceId), `${market.id}: example lacks evidence`);
      assert.ok(market.sourceIds.includes(example.sourceId), `${market.id}: source not linked`);
    }
    assert.ok(market.watchQuestions.length > 0);
    for (const question of market.watchQuestions) localized(question, `${market.id}: watch question`);
    // No X-post/event dataset exists yet. Do not invent assessments from directory sources.
    assert.deepEqual(market.officialUpdateIds, [], `${market.id}: X evidence must be implemented before linking updates`);
    assert.equal(market.assessment, null, `${market.id}: unsupported replacement verdict`);
  }
  return { groups: groups.size, markets: markets.size, sources: sources.size, coverageAssessments: 0 };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const data = JSON.parse(await readFile(new URL("../src/content/markets.json", import.meta.url), "utf8"));
  console.log(JSON.stringify(validateCatalog(data), null, 2));
}
