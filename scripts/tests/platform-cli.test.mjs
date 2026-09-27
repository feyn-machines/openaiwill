import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { collections } from "../lib/platform-schema.mjs";
import { sealRelease, verifyRelease } from "../lib/platform-data.mjs";

const cli = fileURLToPath(new URL("../seal-platform-release.mjs", import.meta.url));

async function candidate(t) {
  const releaseRoot = await mkdtemp(join(tmpdir(), "oaw-platform-cli-"));
  t.after(() => rm(releaseRoot, { recursive: true, force: true }));
  const data = Object.fromEntries(collections.map((name) => [name, []]));
  data.nodes = [
    { id: "group", kind: "market_group", label_zh_cn: "示例领域", label_en: "Example group", origin: "editorial_ai", translation_status: "ai_translated", scope_status: "starter_catalog" },
    { id: "work", kind: "work", label_zh_cn: "示例工作", label_en: "Example work", origin: "editorial_ai", translation_status: "ai_translated", scope_status: "defined" },
  ];
  data.relations = [{ id: "r1", view: "markets", parent_id: "group", child_id: "work", order: 0 }];
  data.weights = [{ relation_id: "r1", value: 1, method: "ai_proposed", method_version: "0.0.1", basis_value: null, explanation: "Synthetic CLI fixture", status: "draft" }];
  data.progress = data.nodes.map((node) => ({ node_id: node.id, view: "markets", value: null, status: "unassessed", as_of: null, update_id: null }));
  const original = {
    version: "0.0.1", schema_version: "0.0.1", created_at: "2026-09-12T00:00:00Z", previous_version: null,
    previous_manifest_sha256: null, change_types: ["initial"], summary: "Synthetic CLI fixture",
    source_inputs: [{ name: "catalog.json", sha256: "a".repeat(64), bytes: 123 }],
    method_versions: { market_weight: "ai-proposed/0.0.1", capability_estimator: null },
    unintegrated_inputs: [{ name: "pending.xlsx", sha256: "b".repeat(64), bytes: 234, status: "raw_not_integrated" }],
    coverage_summary: { market_domains: 1, initial_events: 0, initial_estimates: 0, known_gaps: ["Employment statistics not applied"] },
  };
  await sealRelease({ data, outputDir: join(releaseRoot, "v0.0.1"), meta: original });
  data.events.push({ id: "event", title: "Example update", summary: "Synthetic event for CLI integration", occurred_at: null, observed_at: "2026-09-12T01:00:00Z", source_urls: ["https://example.org/update"], topic_ids: ["work"], source_role: "official_record", verification_status: "unverified", dedup_key: "example-update" });
  const bundle = { previous_version: "0.0.1", change_types: ["event_added"], summary: "Add one event", data };
  async function run(overrides = {}) {
    const input = join(releaseRoot, "candidate.json");
    await writeFile(input, JSON.stringify({ ...bundle, ...overrides }));
    return spawnSync(process.execPath, [cli, `--input=${input}`, `--out-root=${releaseRoot}`], { encoding: "utf8" });
  }
  return { releaseRoot, original, bundle, run };
}

test("event-only CLI iteration inherits provenance and methods while refreshing coverage counts", async (t) => {
  const { releaseRoot, original, run } = await candidate(t);
  const result = await run();
  assert.equal(result.status, 0, result.stderr);
  const { manifest } = await verifyRelease(join(releaseRoot, "v0.0.2"));
  assert.deepEqual(manifest.source_inputs, original.source_inputs);
  assert.deepEqual(manifest.method_versions, original.method_versions);
  assert.deepEqual(manifest.unintegrated_inputs, original.unintegrated_inputs);
  assert.deepEqual(manifest.coverage_summary.known_gaps, ["Employment statistics not applied"]);
  assert.equal(manifest.coverage_summary.events, 1);
  assert.equal(manifest.coverage_summary.observations, 0);
  assert.equal(manifest.coverage_summary.assessed_progress, 0);
  assert.equal(manifest.coverage_summary.market_domains, 1);
  assert.equal("initial_events" in manifest.coverage_summary, false);
  assert.equal("initial_estimates" in manifest.coverage_summary, false);
});

test("explicit metadata replaces inherited values and real method changes require minor releases", async (t) => {
  const { releaseRoot, run } = await candidate(t);
  const overrides = {
    source_inputs: [{ name: "revised-catalog.json", sha256: "c".repeat(64), bytes: 345 }],
    method_versions: { market_weight: "ai-proposed/0.0.2", capability_estimator: null },
    unintegrated_inputs: [],
    coverage_summary: { events: 1, known_gaps: ["Revised coverage note"] },
  };
  const patch = await run(overrides);
  assert.notEqual(patch.status, 0);
  assert.match(patch.stderr, /actual changes require at least minor/);
  const minor = await run({ ...overrides, change_types: ["event_added", "weight_method_changed"] });
  assert.equal(minor.status, 0, minor.stderr);
  const { manifest } = await verifyRelease(join(releaseRoot, "v0.1.0"));
  assert.deepEqual(manifest.source_inputs, overrides.source_inputs);
  assert.deepEqual(manifest.method_versions, overrides.method_versions);
  assert.deepEqual(manifest.unintegrated_inputs, []);
  assert.deepEqual(manifest.coverage_summary.known_gaps, ["Revised coverage note"]);
  assert.equal(manifest.coverage_summary.events, 1);
});

test("CLI rejects malformed explicit provenance and contradictory coverage", async (t) => {
  const cases = [
    ["source_inputs", [{ name: "bad.json", sha256: "not-a-hash", bytes: 1 }]],
    ["method_versions", { market_weight: 123 }],
    ["unintegrated_inputs", [{ name: "bad.xlsx", sha256: "d".repeat(64), bytes: -1, status: "raw_not_integrated" }]],
    ["coverage_summary", { events: 999 }],
    ...["source_inputs", "method_versions", "unintegrated_inputs", "coverage_summary"].map((field) => [field, null]),
  ];
  for (const [index, [field, value]] of cases.entries()) await t.test(`${index + 1}: invalid ${field}`, async (t) => {
    const { run } = await candidate(t);
    const result = await run({ [field]: value, change_types: ["estimate_method_changed"] });
    assert.notEqual(result.status, 0, `${field} must not be silently accepted`);
    assert.match(result.stderr, new RegExp(field));
  });
});
