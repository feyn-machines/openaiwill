import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  validateData, aggregateProgress, nextVersion, sealRelease, verifyRelease,
  inferTaskWeights, classifyReleaseChange,
} from "../lib/platform-data.mjs";

function fixture() {
  return {
    nodes: [
      { id: "group", kind: "market_group", label_zh_cn: "法律", label_en: "Legal", origin: "editorial_ai", translation_status: "ai_translated", scope_status: "starter_catalog" },
      { id: "review", kind: "work", label_zh_cn: "审查", label_en: "Review", origin: "editorial_ai", translation_status: "ai_translated", scope_status: "defined" },
      { id: "draft", kind: "work", label_zh_cn: "起草", label_en: "Draft", origin: "editorial_ai", translation_status: "ai_translated", scope_status: "defined" },
    ],
    relations: [
      { id: "r1", view: "markets", parent_id: "group", child_id: "review", order: 0 },
      { id: "r2", view: "markets", parent_id: "group", child_id: "draft", order: 1 },
    ],
    weights: [
      { relation_id: "r1", value: 0.5, method: "ai_proposed", method_version: "0.0.1", basis_value: null, explanation: "Synthetic fixture", status: "draft" },
      { relation_id: "r2", value: 0.5, method: "ai_proposed", method_version: "0.0.1", basis_value: null, explanation: "Synthetic fixture", status: "draft" },
    ],
    sources: [{ id: "test-source", version: "1", url: "https://example.org/reference", license: "test_fixture", status: "reference" }],
    external_mappings: [],
    metric_definitions: [
      { id: "likes", label_zh_cn: "点赞数", value_type: "integer", unit: "count", role: "attention", allowed_values: [], minimum: 0, maximum: null },
    ],
    events: [],
    observations: [],
    progress_updates: [],
    progress: [
      { node_id: "group", view: "markets", value: null, status: "unassessed", as_of: null, update_id: null },
      { node_id: "review", view: "markets", value: null, status: "unassessed", as_of: null, update_id: null },
      { node_id: "draft", view: "markets", value: null, status: "unassessed", as_of: null, update_id: null },
    ],
    reference_occupations: [], reference_tasks: [], reference_activities: [],
    reference_task_activity_links: [], reference_taxonomy_codes: [], coverage: [],
  };
}

function eventFixture(id = "event") {
  return { id, title: "Synthetic test", summary: "Test fixture only", occurred_at: null, observed_at: "2026-09-12T00:00:00Z", source_urls: [`https://example.org/${id}`], topic_ids: ["review"], source_role: "independent_test", verification_status: "corroborated", dedup_key: id };
}

function assessedFixture() {
  const d = fixture();
  d.metric_definitions.push({ id: "benchmark", label_zh_cn: "测试通过率", value_type: "number", unit: "percent", role: "performance", allowed_values: [], minimum: 0, maximum: 100 });
  d.events.push(eventFixture());
  d.observations.push({ id: "obs", event_id: "event", metric_id: "benchmark", value: 50, observed_at: "2026-09-12T00:00:00Z", source_url: "https://example.org/event", scope_note: null, missing_reason: null });
  appendUpdate(d, { id: "u1", node_id: "review", view: "markets", previous_update_id: null, old_value: null, new_value: 20, event_ids: ["event"], observation_ids: ["obs"], method_id: "estimate", method_version: "0.0.1", reason: "Synthetic benchmark evidence", change_cause: "new_evidence", assessed_at: "2026-09-12T00:01:00Z" });
  return d;
}

function appendUpdate(d, update) {
  d.progress_updates.push(update);
  Object.assign(d.progress.find((p) => p.node_id === update.node_id && p.view === update.view), { value: update.new_value, status: "estimated", as_of: update.assessed_at, update_id: update.id });
}

async function sealedFixture(t, data = fixture(), extraMeta = {}) {
  const root = await mkdtemp(join(tmpdir(), "oaw-data-test-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const previousDir = join(root, "v0.0.1");
  await sealRelease({ data, outputDir: previousDir, meta: { version: "0.0.1", schema_version: "0.0.1", created_at: "2026-09-12T00:00:00Z", previous_version: null, previous_manifest_sha256: null, change_types: ["initial"], summary: "Synthetic fixture", ...extraMeta } });
  const previous = await verifyRelease(previousDir);
  return { data, root, previousDir, meta: { ...previous.manifest, version: "0.0.2", previous_version: "0.0.1", previous_manifest_sha256: previous.manifest_sha256, change_types: ["correction"] } };
}

test("events require a stable deduplication key", () => {
  const d = fixture(), event = eventFixture();
  delete event.dedup_key;
  d.events.push(event);
  assert.throws(() => validateData(d), /dedup_key/);
});

test("the same event cannot bypass deduplication with a new ID and key", () => {
  const d = fixture(), event = eventFixture();
  event.source_urls.push("https://example.org/second-source");
  d.events.push(event, { ...event, id: "duplicate", dedup_key: "another-key", source_urls: [...event.source_urls].reverse(), observed_at: "2026-09-12T08:00:00+08:00", summary: " Test  fixture only " });
  assert.throws(() => validateData(d), /duplicate.*event identity/i);
  d.events[1] = { ...eventFixture("other"), dedup_key: event.dedup_key };
  assert.throws(() => validateData(d), /duplicate.*event dedup key/i);
});

test("an unused event cannot make the same observations count twice", () => {
  const d = assessedFixture();
  assert.doesNotThrow(() => validateData(d));
  d.events.push(eventFixture("other"));
  appendUpdate(d, { ...d.progress_updates[0], id: "u2", previous_update_id: "u1", old_value: 20, new_value: 40, event_ids: ["event", "other"], assessed_at: "2026-09-12T00:02:00Z" });
  assert.throws(() => validateData(d), /event.*observation|observation.*event/i);
  d.progress_updates[1].event_ids = ["event"];
  assert.throws(() => validateData(d), /duplicate progress update inputs/i);
  d.observations.push({ ...d.observations[0], id: "other-obs", event_id: "other", source_url: "https://example.org/other" });
  d.progress_updates[1].event_ids.push("other");
  d.progress_updates[1].observation_ids = ["obs", "other-obs"];
  assert.doesNotThrow(() => validateData(d));
});

test("equivalent observation times and scope whitespace cannot create a second progress input", () => {
  const cases = [
    { scope: "Contract clause review", duplicateScope: "Contract clause review", observed_at: "2026-09-12T08:00:00+08:00" },
    { scope: "Contract clause review", duplicateScope: "  Contract\tclause\nreview  ", observed_at: "2026-09-12T00:00:00Z" },
    { scope: null, duplicateScope: " \t ", observed_at: "2026-09-12T08:00:00+08:00" },
  ];
  for (const { scope, duplicateScope, observed_at } of cases) {
    const d = assessedFixture();
    d.observations[0].scope_note = scope;
    d.observations.push({ ...d.observations[0], id: "alias-obs", observed_at, scope_note: duplicateScope });
    appendUpdate(d, { ...d.progress_updates[0], id: "u2", previous_update_id: "u1", old_value: 20, new_value: 40, observation_ids: ["alias-obs"], assessed_at: "2026-09-12T00:02:00Z" });
    assert.throws(() => validateData(d), /duplicate metric observation/i);
    d.observations[1].scope_note = "A distinct benchmark cohort";
    assert.doesNotThrow(() => validateData(d));
  }
});

test("a changed estimation method must be recorded as a method revision", () => {
  for (const change of [{ method_version: "0.1.0" }, { method_id: "replacement-estimator" }]) {
    const d = assessedFixture();
    appendUpdate(d, { ...d.progress_updates[0], ...change, id: "u2", previous_update_id: "u1", old_value: 20, new_value: 40, assessed_at: "2026-09-12T00:02:00Z" });
    assert.throws(() => validateData(d), /method.*revision/i);
    d.progress_updates[1].change_cause = "method_revision";
    assert.doesNotThrow(() => validateData(d));
  }
});

test("unknown child is not silently converted to zero or renormalized away", () => {
  const d = fixture();
  d.progress.find((r) => r.node_id === "review").value = 80;
  assert.equal(aggregateProgress(d, "group", "markets"), null);
});

test("zero is a real observation and participates in weighted aggregation", () => {
  const d = fixture();
  d.progress.find((r) => r.node_id === "review").value = 80;
  d.progress.find((r) => r.node_id === "draft").value = 0;
  assert.equal(aggregateProgress(d, "group", "markets"), 40);
});

test("valid shared nodes can have distinct parent weights in another view", () => {
  const d = fixture();
  d.nodes.push({ ...d.nodes[0], id: "lawyer", kind: "occupation" });
  d.relations.push({ id: "r3", view: "occupations", parent_id: "lawyer", child_id: "review", order: 0 });
  d.weights.push({ ...d.weights[0], relation_id: "r3", value: 1 });
  d.progress.push(
    { ...d.progress[0], node_id: "lawyer", view: "occupations" },
    { ...d.progress[0], node_id: "review", view: "occupations" },
  );
  assert.doesNotThrow(() => validateData(d));
});

test("multiple external targets on the same node are permitted", () => {
  const d = fixture();
  for (const code of ["A", "B"]) {
    d.reference_taxonomy_codes.push({ id: "isic:" + code, source_code: code, kind: "section", parent_id: null });
    d.external_mappings.push({
      id: "mapping:" + code, node_id: "review", source_id: "test-source",
      external_type: "isic_section", external_id: code, relation: "related",
      method: "ai_proposed", status: "candidate",
    });
  }
  assert.doesNotThrow(() => validateData(d));
});

test("duplicate IDs and dangling references are rejected", () => {
  const d = fixture();
  d.nodes.push({ ...d.nodes[0] });
  assert.throws(() => validateData(d), /duplicate/i);
  d.nodes.pop();
  d.relations[0].child_id = "missing";
  assert.throws(() => validateData(d), /reference|missing/i);
});

test("a classification cycle cannot enter a snapshot", () => {
  const d = fixture();
  d.relations.push({ id: "back", view: "markets", parent_id: "review", child_id: "group", order: 0 });
  d.weights.push({ ...d.weights[0], relation_id: "back", value: 1 });
  assert.throws(() => validateData(d), /cycle/i);
});

test("wrong parent weight total is rejected", () => {
  const d = fixture();
  d.weights[0].value = 0.8;
  assert.throws(() => validateData(d), /weight.*sum/i);
});

test("progress outside 0–100 is rejected even if aggregate is unknown", () => {
  const d = fixture();
  d.progress[1].value = 101;
  assert.throws(() => validateData(d), /progress|schema/i);
});

test("metric definition type and null reason are enforced", () => {
  const d = fixture();
  d.events.push(eventFixture());
  d.observations.push({ id: "obs", event_id: "event", metric_id: "likes", value: "many", observed_at: "2026-09-12T00:00:00Z", source_url: "https://example.org/event", scope_note: null, missing_reason: null });
  assert.throws(() => validateData(d), /metric.*type/i);
  d.observations[0].value = null;
  assert.throws(() => validateData(d), /missing_reason/i);
  d.observations[0].missing_reason = "not_returned";
  assert.doesNotThrow(() => validateData(d));
});

test("importance fallback works when the whole occupation lacks ratings", () => {
  const tasks = [
    { id: "a", importance: null }, { id: "b", importance: { value: 4, suppress: true } },
  ];
  const w = inferTaskWeights(tasks);
  assert.deepEqual(w.map((r) => r.value), [0.5, 0.5]);
  assert.ok(w.every((r) => r.method === "equal_no_reliable_ratings"));
});

test("missing task importance uses the occupation mean, without modifying source data", () => {
  const tasks = [{ id: "a", importance: { value: 2, suppress: false } }, { id: "b", importance: { value: 4, suppress: false } }, { id: "c", importance: null }];
  const w = inferTaskWeights(tasks);
  assert.deepEqual(w.map((r) => r.basis_value), [2, 4, 3]);
  assert.equal(w[2].method, "imputed_occupation_mean");
  assert.ok(Math.abs(w.reduce((sum, r) => sum + r.value, 0) - 1) < 1e-10);
  assert.equal(tasks[2].importance, null);
});

test("version bumps reset lower components and reject malformed versions", () => {
  assert.equal(nextVersion("0.0.1", "patch"), "0.0.2");
  assert.equal(nextVersion("0.0.1", "minor"), "0.1.0");
  assert.equal(nextVersion("0.0.1", "major"), "1.0.0");
  assert.throws(() => nextVersion("0.01.1", "minor"), /version/i);
});

test("scope and method revisions cannot masquerade as a routine event patch", () => {
  assert.equal(classifyReleaseChange(["event_added", "estimate_updated"]), "patch");
  assert.equal(classifyReleaseChange(["weight_method_changed"]), "minor");
  assert.equal(classifyReleaseChange(["node_identity_changed", "event_added"]), "major");
});

test("actual weight changes require at least a minor release despite a correction label", async (t) => {
  const previous = await sealedFixture(t);
  for (const change of ["value", "method", "method_version"]) {
    const data = structuredClone(previous.data);
    if (change === "value") { data.weights[0].value = 0.1; data.weights[1].value = 0.9; }
    if (change === "method") data.weights[0].method = "equal_occupation_prior";
    if (change === "method_version") data.weights[0].method_version = "0.1.0";
    await assert.rejects(sealRelease({ ...previous, data, outputDir: join(previous.root, `${change}-patch`) }), /actual changes require at least minor/i);
    await assert.doesNotReject(sealRelease({ ...previous, data, outputDir: join(previous.root, `${change}-minor`), meta: { ...previous.meta, version: "0.1.0", change_types: ["weight_values_changed"] } }));
  }
});

test("node identity and scoring meaning changes require a major release", async (t) => {
  const previous = await sealedFixture(t);
  const cases = {
    node_removed(data) {
      data.nodes = data.nodes.filter((r) => r.id !== "draft");
      data.relations = data.relations.filter((r) => r.child_id !== "draft");
      data.weights = data.weights.filter((r) => r.relation_id !== "r2");
      data.weights[0].value = 1;
      data.progress = data.progress.filter((r) => r.node_id !== "draft");
    },
    node_kind(data) { data.nodes[1].kind = "market"; },
    node_origin(data) { data.nodes[1].origin = "onet_projection"; },
    relation_identity(data) { data.relations[0].child_id = "draft"; data.relations[1].child_id = "review"; },
    metric_meaning(data) { data.metric_definitions[0].role = "performance"; },
  };
  for (const [name, mutate] of Object.entries(cases)) {
    const data = structuredClone(previous.data);
    mutate(data);
    await assert.rejects(sealRelease({ ...previous, data, outputDir: join(previous.root, `${name}-minor`), meta: { ...previous.meta, version: "0.1.0", change_types: ["catalog_extended"] } }), /actual changes require at least major/i);
    await assert.doesNotReject(sealRelease({ ...previous, data, outputDir: join(previous.root, `${name}-major`), meta: { ...previous.meta, version: "1.0.0", change_types: ["scoring_meaning_changed"] } }));
  }
});

test("changing or deleting an established node scope requires major, while defining it requires minor", async (t) => {
  const scoped = fixture();
  scoped.nodes[1].scope_note = "Review contract clauses only";
  const previous = await sealedFixture(t, scoped);
  for (const [name, scope] of [["changed", "All legal services including court appearances"], ["deleted", undefined]]) {
    const data = structuredClone(previous.data);
    if (scope === undefined) delete data.nodes[1].scope_note;
    else data.nodes[1].scope_note = scope;
    await assert.rejects(sealRelease({ ...previous, data, outputDir: join(previous.root, `${name}-scope-patch`) }), /actual changes require at least major/i);
    await assert.doesNotReject(sealRelease({ ...previous, data, outputDir: join(previous.root, `${name}-scope-major`), meta: { ...previous.meta, version: "1.0.0", change_types: ["scoring_meaning_changed"] } }));
  }
  const unscoped = await sealedFixture(t), data = structuredClone(unscoped.data);
  data.nodes[1].scope_note = "Review contract clauses only";
  await assert.rejects(sealRelease({ ...unscoped, data, outputDir: join(unscoped.root, "new-scope-patch") }), /actual changes require at least minor/i);
  await assert.doesNotReject(sealRelease({ ...unscoped, data, outputDir: join(unscoped.root, "new-scope-minor"), meta: { ...unscoped.meta, version: "0.1.0", change_types: ["catalog_extended"] } }));
});

test("compatible catalog and mapping additions require minor but permit an explicit major release", async (t) => {
  const previous = await sealedFixture(t);
  const cases = {
    node_added(data) { data.nodes.push({ ...data.nodes[1], id: "new-work" }); },
    mapping_added(data) {
      data.reference_taxonomy_codes.push({ id: "isic:A", source_code: "A", kind: "section", parent_id: null });
      data.external_mappings.push({ id: "mapping:A", node_id: "review", source_id: "test-source", external_type: "isic_section", external_id: "A", relation: "related", method: "ai_proposed", status: "candidate" });
    },
    metric_added(data) { data.metric_definitions.push({ ...data.metric_definitions[0], id: "views" }); },
  };
  for (const [name, mutate] of Object.entries(cases)) {
    const data = structuredClone(previous.data);
    mutate(data);
    await assert.rejects(sealRelease({ ...previous, data, outputDir: join(previous.root, `${name}-patch`) }), /actual changes require at least minor/i);
    for (const [version, change_types] of [["0.1.0", ["catalog_extended"]], ["1.0.0", ["scoring_meaning_changed"]]]) {
      await assert.doesNotReject(sealRelease({ ...previous, data, outputDir: join(previous.root, `${name}-${version}`), meta: { ...previous.meta, version, change_types } }));
    }
  }
  const data = structuredClone(previous.data);
  data.nodes[1].label_zh_cn = "审阅";
  await assert.doesNotReject(sealRelease({ ...previous, data, outputDir: join(previous.root, "translation-patch") }));
});

test("estimator and manifest method revisions require a minor release", async (t) => {
  const previous = await sealedFixture(t, assessedFixture(), { method_versions: { task_weight: "importance-prior/0.0.1", capability_estimator: "estimate/0.0.1" } });
  const data = structuredClone(previous.data);
  appendUpdate(data, { ...data.progress_updates[0], id: "u2", previous_update_id: "u1", old_value: 20, new_value: 40, method_version: "0.1.0", change_cause: "method_revision", assessed_at: "2026-09-12T00:02:00Z" });
  const revisions = [
    { data, meta: previous.meta },
    { data: previous.data, meta: { ...previous.meta, method_versions: { ...previous.meta.method_versions, task_weight: "importance-prior/0.1.0" } } },
  ];
  for (const [i, revision] of revisions.entries()) {
    await assert.rejects(sealRelease({ ...previous, ...revision, outputDir: join(previous.root, `method-${i}-patch`) }), /actual changes require at least minor/i);
    await assert.doesNotReject(sealRelease({ ...previous, ...revision, outputDir: join(previous.root, `method-${i}-minor`), meta: { ...revision.meta, version: "0.1.0", change_types: ["estimate_method_changed"] } }));
  }
  const meta = { ...previous.meta, method_versions: { capability_estimator: "estimate/0.0.1", task_weight: "importance-prior/0.0.1" } };
  await assert.doesNotReject(sealRelease({ ...previous, meta, outputDir: join(previous.root, "reordered-method-keys") }));
});

test("published progress updates and observations are append-only across releases", async (t) => {
  const baseline = assessedFixture();
  baseline.observations.push({ ...baseline.observations[0], id: "unused-obs", metric_id: "likes", value: 10 });
  const previous = await sealedFixture(t, baseline);
  const cases = {
    update_method(data) { data.progress_updates[0].method_version = "0.1.0"; },
    update_reason(data) { data.progress_updates[0].reason = "Silently rewritten reasoning"; },
    update_deleted(data) {
      data.progress_updates = [];
      Object.assign(data.progress[1], { value: null, status: "unassessed", as_of: null, update_id: null });
    },
    observation_value(data) { data.observations[0].value = 90; },
    observation_time(data) { data.observations[0].observed_at = "2026-09-12T08:00:00+08:00"; },
    observation_source(data) { data.observations[0].source_url = "https://example.org/replacement-source"; },
    observation_deleted(data) { data.observations.pop(); },
  };
  for (const [name, mutate] of Object.entries(cases)) {
    const data = structuredClone(previous.data);
    mutate(data);
    await assert.rejects(sealRelease({ ...previous, data, outputDir: join(previous.root, name), meta: { ...previous.meta, version: "1.0.0", change_types: ["scoring_meaning_changed"] } }), /append-only.*(?:progress_updates|observations)/i);
  }
  const data = structuredClone(previous.data);
  data.progress_updates[0] = Object.fromEntries(Object.entries(data.progress_updates[0]).reverse());
  data.events[0].verification_status = "disputed";
  data.events[0].source_urls.push("https://example.org/correction");
  data.observations.push({ ...data.observations[0], id: "corrected-obs", value: 55, observed_at: "2026-09-12T00:01:00Z" });
  appendUpdate(data, { ...data.progress_updates[0], id: "u2", previous_update_id: "u1", old_value: 20, new_value: 22, observation_ids: ["corrected-obs"], change_cause: "evidence_correction", assessed_at: "2026-09-12T00:02:00Z" });
  await assert.doesNotReject(sealRelease({ ...previous, data, outputDir: join(previous.root, "appended-correction") }));
});

test("release lineage rejects downgrades and a wrong predecessor hash or version", async (t) => {
  const previous = await sealedFixture(t);
  await assert.rejects(sealRelease({ ...previous, outputDir: join(previous.root, "downgrade"), meta: { ...previous.meta, version: "0.0.0" } }), /version/i);
  await assert.rejects(sealRelease({ ...previous, outputDir: join(previous.root, "wrong-hash"), meta: { ...previous.meta, previous_manifest_sha256: "f".repeat(64) } }), /lineage mismatch/i);
  await assert.rejects(sealRelease({ ...previous, outputDir: join(previous.root, "wrong-predecessor"), meta: { ...previous.meta, previous_version: "0.0.2", version: "0.0.3" } }), /lineage mismatch/i);
});

test("an unlisted file invalidates both verification and successor sealing", async (t) => {
  const previous = await sealedFixture(t);
  await writeFile(join(previous.previousDir, "unlisted.txt"), "Synthetic unlisted content\n");
  await assert.rejects(verifyRelease(previous.previousDir), /unlisted/i);
  await assert.rejects(sealRelease({ ...previous, outputDir: join(previous.root, "successor") }), /unlisted/i);
});

test("a sealed release can be verified, cannot be overwritten, and detects tampering", async (t) => {
  const root = await mkdtemp(join(tmpdir(), "oaw-data-test-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const out = join(root, "v0.0.1");
  const d = fixture();
  await sealRelease({ data: d, outputDir: out, meta: { version: "0.0.1", schema_version: "0.0.1", created_at: "2026-09-12T00:00:00Z", previous_version: null, previous_manifest_sha256: null, change_types: ["initial"], summary: "Synthetic fixture" } });
  const result = await verifyRelease(out);
  assert.equal(result.counts.nodes, 3);
  const before = await readFile(join(out, "manifest.json"), "utf8");
  await assert.rejects(sealRelease({ data: d, outputDir: out, meta: { version: "0.0.1" } }), /exists|overwrite/i);
  assert.equal(await readFile(join(out, "manifest.json"), "utf8"), before);
  await writeFile(join(out, "nodes.jsonl"), "{}\n");
  await assert.rejects(verifyRelease(out), /hash|integrity/i);
});
