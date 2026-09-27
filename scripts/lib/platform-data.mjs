import Ajv2020 from "ajv/dist/2020.js";
import { createHash } from "node:crypto";
import { readFile, writeFile, mkdir, mkdtemp, rename, rm, readdir, lstat, open } from "node:fs/promises";
import { dirname, join, basename } from "node:path";
import { isDeepStrictEqual } from "node:util";
import { dataSchema, collections } from "./platform-schema.mjs";

const ajv = new Ajv2020({ allErrors: false, allowUnionTypes: true });
ajv.addFormat("date-time", (s) => /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(s) && Number.isFinite(Date.parse(s)));
ajv.addFormat("uri", (s) => { try { return ["http:", "https:"].includes(new URL(s).protocol); } catch { return false; } });
const schemaCheck = ajv.compile(dataSchema);
export const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
const fail = (message) => { throw new Error(message); };
const key = (...parts) => JSON.stringify(parts);
const group = (rows, getKey) => {
  const result = new Map();
  for (const r of rows) { const k = getKey(r); if (!result.has(k)) result.set(k, []); result.get(k).push(r); }
  return result;
};
function unique(rows, getKey, label) {
  const result = new Map();
  for (const r of rows) { const k = getKey(r); if (result.has(k)) fail(`duplicate ${label}: ${k}`); result.set(k, r); }
  return result;
}
const ref = (map, id, label) => { if (!map.has(id)) fail(`missing reference ${label}: ${id}`); };

export function validateData(data) {
  if (!schemaCheck(data)) fail(`schema: ${ajv.errorsText(schemaCheck.errors)}`);
  const by = {};
  for (const name of collections.filter((n) => !["relations", "weights", "progress", "reference_task_activity_links", "coverage"].includes(n))) by[name] = unique(data[name], (r) => r.id, name);
  by.relations = unique(data.relations, (r) => r.id, "relations");
  const weights = unique(data.weights, (r) => r.relation_id, "weights");
  unique(data.relations, (r) => key(r.view, r.parent_id, r.child_id), "relation edge");
  unique(data.relations, (r) => key(r.view, r.parent_id, r.order), "sibling order");
  const parents = group(data.relations, (r) => key(r.view, r.parent_id));
  const membership = new Set();
  for (const r of data.relations) {
    ref(by.nodes, r.parent_id, "parent"); ref(by.nodes, r.child_id, "child"); ref(weights, r.id, "weight");
    membership.add(key(r.parent_id, r.view)); membership.add(key(r.child_id, r.view));
  }
  for (const w of data.weights) ref(by.relations, w.relation_id, "weight relation");
  for (const [p, edges] of parents) {
    const sum = edges.reduce((s, r) => s + weights.get(r.id).value, 0);
    if (Math.abs(sum - 1) > 1e-8) fail(`weight sum for ${p}: ${sum}`);
  }
  const active = new Set(), done = new Set();
  function visit(node, view) {
    const k = key(view, node);
    if (active.has(k)) fail(`classification cycle: ${node}`);
    if (done.has(k)) return;
    active.add(k);
    for (const r of parents.get(k) ?? []) visit(r.child_id, view);
    active.delete(k); done.add(k);
  }
  for (const r of data.relations) visit(r.parent_id, r.view);

  for (const r of data.reference_occupations) ref(by.nodes, `oaw:occupation-group:${r.family_id.split(":").at(-1)}`, "occupation family node");
  for (const r of data.reference_tasks) ref(by.reference_occupations, r.occupation_id, "task occupation");
  for (const name of ["reference_activities", "reference_taxonomy_codes"]) for (const r of data[name]) if (r.parent_id !== null) ref(by[name], r.parent_id, `${name} parent`);
  unique(data.reference_task_activity_links, (r) => key(r.task_id, r.activity_id), "task activity link");
  for (const r of data.reference_task_activity_links) { ref(by.reference_tasks, r.task_id, "task activity task"); ref(by.reference_activities, r.activity_id, "task activity activity"); }
  const externalCodes = {
    onet_task: new Set(data.reference_tasks.map((r) => r.source_task_id)),
    onet_occupation: new Set(data.reference_occupations.map((r) => r.source_code)),
    onet_activity: new Set(data.reference_activities.map((r) => r.source_id)),
    onet_family: new Set(data.nodes.filter((r) => r.kind === "occupation_group").map((r) => r.id.split(":").at(-1))),
    isic_section: new Set(data.reference_taxonomy_codes.filter((r) => r.kind === "section").map((r) => r.source_code)),
  };
  unique(data.external_mappings, (r) => key(r.node_id, r.source_id, r.external_type, r.external_id, r.relation), "external mapping");
  for (const r of data.external_mappings) {
    ref(by.nodes, r.node_id, "mapping node"); ref(by.sources, r.source_id, "mapping source");
    ref(externalCodes[r.external_type], r.external_id, "external code");
    if (r.method === "ai_proposed" && r.status !== "candidate") fail(`AI mapping must remain candidate: ${r.id}`);
  }
  unique(data.coverage, (r) => r.isic_section, "coverage section");
  for (const r of data.coverage) {
    ref(externalCodes.isic_section, r.isic_section, "coverage section");
    for (const id of r.domain_ids) { ref(by.nodes, id, "coverage domain"); if (by.nodes.get(id).kind !== "market_group") fail(`coverage domain is not market_group: ${id}`); }
  }
  unique(data.events, (r) => r.dedup_key, "event dedup key");
  const normalizeText = (s) => s.normalize("NFC").trim().replace(/\s+/gu, " ");
  unique(data.events, (r) => key(
    [...new Set(r.source_urls.map((url) => new URL(url).href))].sort(),
    Date.parse(r.occurred_at ?? r.observed_at), normalizeText(r.title), normalizeText(r.summary),
  ), "event identity");
  for (const e of data.events) for (const id of e.topic_ids) ref(by.nodes, id, "event topic");
  for (const m of data.metric_definitions) {
    if (m.value_type === "enum" && !m.allowed_values.length) fail(`metric enum lacks values: ${m.id}`);
    if (m.minimum !== null && m.maximum !== null && m.minimum > m.maximum) fail(`metric bounds: ${m.id}`);
  }
  const observationIdentity = (r) => key(
    r.event_id, r.metric_id, Date.parse(r.observed_at), new URL(r.source_url).href,
    r.scope_note === null ? null : normalizeText(r.scope_note) || null,
  );
  unique(data.observations, observationIdentity, "metric observation");
  for (const o of data.observations) {
    ref(by.events, o.event_id, "observation event"); ref(by.metric_definitions, o.metric_id, "observation metric");
    const m = by.metric_definitions.get(o.metric_id), v = o.value;
    if (v === null) { if (!o.missing_reason) fail(`missing_reason required for ${o.id}`); continue; }
    if (o.missing_reason !== null) fail(`missing_reason on observed value: ${o.id}`);
    const valid = m.value_type === "integer" ? Number.isSafeInteger(v) : m.value_type === "enum" ? m.allowed_values.includes(v) : typeof v === m.value_type;
    if (!valid) fail(`metric type mismatch: ${o.id}`);
    if (typeof v === "number" && ((m.minimum !== null && v < m.minimum) || (m.maximum !== null && v > m.maximum))) fail(`metric range: ${o.id}`);
  }
  const observationIdentities = new Map(data.observations.map((r) => [r.id, observationIdentity(r)]));
  const last = new Map(), inputs = new Set();
  for (const u of data.progress_updates) {
    ref(by.nodes, u.node_id, "progress update node");
    const k = key(u.node_id, u.view), previous = last.get(k);
    if (!membership.has(k)) fail(`missing reference update view: ${k}`);
    if (u.previous_update_id !== (previous?.id ?? null) || u.old_value !== (previous?.new_value ?? null)) fail(`progress update chain mismatch: ${u.id}`);
    if (previous && Date.parse(u.assessed_at) < Date.parse(previous.assessed_at)) fail(`progress update time order: ${u.id}`);
    if (previous && (u.method_id !== previous.method_id || u.method_version !== previous.method_version) && u.change_cause !== "method_revision") fail(`changed estimation method requires method_revision: ${u.id}`);
    for (const id of u.event_ids) ref(by.events, id, "update event");
    const observedEvents = new Set();
    for (const id of u.observation_ids) {
      ref(by.observations, id, "update observation");
      const o = by.observations.get(id);
      observedEvents.add(o.event_id);
      if (!u.event_ids.includes(o.event_id)) fail(`update observation event mismatch: ${id}`);
      if (Date.parse(o.observed_at) > Date.parse(u.assessed_at)) fail(`future observation input: ${id}`);
    }
    if (u.event_ids.some((id) => !observedEvents.has(id))) fail(`update event lacks selected observation: ${u.id}`);
    if (!u.observation_ids.some((id) => { const o = by.observations.get(id); return o.value !== null && by.metric_definitions.get(o.metric_id).role !== "attention"; })) fail(`attention alone cannot produce capability progress: ${u.id}`);
    const fingerprint = key(u.node_id, u.view, u.method_id, u.method_version, u.observation_ids.map((id) => observationIdentities.get(id)).sort());
    if (inputs.has(fingerprint)) fail(`duplicate progress update inputs: ${u.id}`);
    inputs.add(fingerprint); last.set(k, u);
  }
  const progress = unique(data.progress, (r) => key(r.node_id, r.view), "progress");
  for (const p of data.progress) {
    ref(by.nodes, p.node_id, "progress node");
    if (!membership.has(key(p.node_id, p.view))) fail(`missing reference progress view: ${p.node_id}`);
    const u = last.get(key(p.node_id, p.view));
    if (p.status === "unassessed" && (p.value !== null || p.update_id !== null || p.as_of !== null)) fail(`unassessed progress must be null: ${p.node_id}`);
    if (p.status === "estimated" && (!u || p.update_id !== u.id || p.value !== u.new_value || p.as_of !== u.assessed_at)) fail(`progress does not match latest update: ${p.node_id}`);
    if (u && p.status !== "estimated") fail(`progress update missing from current estimate: ${p.node_id}`);
    if (p.status === "aggregate") {
      if (!(parents.get(key(p.view, p.node_id))?.length) || p.update_id !== null || p.value !== aggregateProgress(data, p.node_id, p.view)) fail(`aggregate progress mismatch: ${p.node_id}`);
    }
  }
  for (const k of membership) ref(progress, k, "node view progress");
  return { counts: Object.fromEntries(collections.map((n) => [n, data[n].length])) };
}

export function aggregateProgress(data, nodeId, view) {
  const children = group(data.relations.filter((r) => r.view === view), (r) => r.parent_id);
  const w = new Map(data.weights.map((r) => [r.relation_id, r.value]));
  const p = new Map(data.progress.filter((r) => r.view === view).map((r) => [r.node_id, r.value]));
  const stack = new Set(), cache = new Map();
  function calc(id) {
    if (stack.has(id)) fail(`cycle: ${id}`);
    if (cache.has(id)) return cache.get(id);
    const edges = children.get(id);
    if (!edges?.length) return p.get(id) ?? null;
    stack.add(id); let sum = 0, unknown = false;
    for (const r of edges) { const value = calc(r.child_id); if (value === null) unknown = true; else sum += value * w.get(r.id); }
    stack.delete(id); const result = unknown ? null : Number(sum.toFixed(10)); cache.set(id, result); return result;
  }
  return calc(nodeId);
}

export function inferTaskWeights(tasks) {
  if (!tasks.length) return [];
  const values = tasks.map((t) => t.importance && !t.importance.suppress && Number.isFinite(t.importance.value) && t.importance.value > 0 ? t.importance.value : null);
  const reliable = values.filter((v) => v !== null);
  const mean = reliable.length ? reliable.reduce((a, b) => a + b, 0) / reliable.length : null;
  const bases = values.map((v) => v ?? mean ?? 1), sum = bases.reduce((a, b) => a + b, 0);
  return tasks.map((t, i) => ({ task_id: t.id, value: bases[i] / sum, basis_value: mean === null ? null : bases[i], method: mean === null ? "equal_no_reliable_ratings" : values[i] === null ? "imputed_occupation_mean" : "source_importance_normalized" }));
}
function parseVersion(version) {
  if (!/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(version)) fail(`invalid version: ${version}`);
  const parts = version.split(".").map(Number);
  if (!parts.every(Number.isSafeInteger)) fail(`unsafe version: ${version}`);
  return parts;
}
export function nextVersion(version, bump) {
  const p = parseVersion(version), i = { major: 0, minor: 1, patch: 2 }[bump];
  if (i === undefined) fail(`invalid version bump: ${bump}`);
  p[i]++; for (let j = i + 1; j < 3; j++) p[j] = 0;
  return p.join(".");
}
const changeLevels = { event_added: 2, observation_added: 2, estimate_updated: 2, correction: 2, catalog_extended: 1, mapping_added: 1, optional_field_added: 1, weight_method_changed: 1, weight_values_changed: 1, estimate_method_changed: 1, node_identity_changed: 0, required_schema_changed: 0, scoring_meaning_changed: 0 };
export function classifyReleaseChange(types) {
  if (!types.length) fail("empty change types");
  const values = types.map((t) => { if (!(t in changeLevels)) fail(`unknown change type: ${t}`); return changeLevels[t]; });
  return ["major", "minor", "patch"][Math.min(...values)];
}
const bumpLevels = { major: 0, minor: 1, patch: 2 };
function validateAppendOnlyEvidence(previous, current) {
  for (const collection of ["progress_updates", "observations"]) {
    const next = new Map(current[collection].map((r) => [r.id, r]));
    for (const old of previous[collection]) {
      if (!isDeepStrictEqual(old, next.get(old.id))) fail(`append-only ${collection}: cannot remove or rewrite ${old.id}`);
    }
  }
}
function actualReleaseChange(previous, current, previousMeta, currentMeta) {
  const changes = new Set(["correction"]);
  const meaningFields = {
    nodes: ["kind", "origin"],
    relations: ["view", "parent_id", "child_id"],
    metric_definitions: ["value_type", "unit", "role", "minimum", "maximum", "allowed_values"],
  };
  for (const [collection, fields] of Object.entries(meaningFields)) {
    const next = new Map(current[collection].map((r) => [r.id, r]));
    const oldIds = new Set(previous[collection].map((r) => r.id));
    if (current[collection].some((r) => !oldIds.has(r.id))) changes.add("catalog_extended");
    if (previous[collection].some((old) => {
      const row = next.get(old.id);
      return !row || fields.some((field) => JSON.stringify(old[field]) !== JSON.stringify(row[field]));
    })) changes.add("scoring_meaning_changed");
  }
  const currentNodes = new Map(current.nodes.map((r) => [r.id, r]));
  for (const old of previous.nodes) {
    const row = currentNodes.get(old.id);
    if (old.scope_note !== undefined && old.scope_note !== row?.scope_note) changes.add("scoring_meaning_changed");
    if (old.scope_note === undefined && row?.scope_note !== undefined) changes.add("catalog_extended");
  }
  const oldWeights = new Map(previous.weights.map((r) => [r.relation_id, r]));
  if (previous.weights.length !== current.weights.length || current.weights.some((r) => {
    const old = oldWeights.get(r.relation_id);
    return !old || ["value", "method", "method_version"].some((field) => old[field] !== r[field]);
  })) changes.add("weight_values_changed");
  const oldMappings = new Map(previous.external_mappings.map((r) => [r.id, r]));
  if (previous.external_mappings.length !== current.external_mappings.length || current.external_mappings.some((r) => {
    const old = oldMappings.get(r.id);
    return !old || ["node_id", "source_id", "external_type", "external_id", "relation", "method", "status"].some((field) => old[field] !== r[field]);
  })) changes.add("mapping_added");
  const oldUpdates = new Map(previous.progress_updates.map((r) => [r.id, r]));
  const oldMethods = new Map(previous.progress_updates.map((r) => [key(r.node_id, r.view), key(r.method_id, r.method_version)]));
  const currentMethods = new Map(current.progress_updates.map((r) => [key(r.node_id, r.view), key(r.method_id, r.method_version)]));
  if (current.progress_updates.some((r) => {
    const old = oldUpdates.get(r.id);
    return old ? old.method_id !== r.method_id || old.method_version !== r.method_version : r.change_cause === "method_revision";
  }) || [...oldMethods].some(([nodeView, method]) => currentMethods.has(nodeView) && currentMethods.get(nodeView) !== method)) changes.add("estimate_method_changed");
  const oldVersions = previousMeta.method_versions ?? {}, newVersions = currentMeta.method_versions ?? {};
  if ([...new Set([...Object.keys(oldVersions), ...Object.keys(newVersions)])].some((name) => oldVersions[name] !== newVersions[name])) changes.add("estimate_method_changed");
  return classifyReleaseChange([...changes]);
}
function validateMeta(meta) {
  parseVersion(meta.version); parseVersion(meta.schema_version);
  if (meta.schema_version !== "0.0.1") fail(`unsupported schema version: ${meta.schema_version}`);
  if (!Number.isFinite(Date.parse(meta.created_at)) || !meta.summary) fail("manifest requires created_at and summary");
  if (meta.previous_version === null) {
    if (meta.version !== "0.0.1" || meta.previous_manifest_sha256 !== null || JSON.stringify(meta.change_types) !== '["initial"]') fail("initial version must be 0.0.1 without predecessor");
  } else {
    parseVersion(meta.previous_version);
    if (!/^[a-f0-9]{64}$/.test(meta.previous_manifest_sha256)) fail("previous manifest hash required");
    const expected = nextVersion(meta.previous_version, classifyReleaseChange(meta.change_types));
    if (meta.version !== expected) fail(`version must be ${expected}; downgrade or wrong bump rejected`);
  }
}

export async function sealRelease({ data, outputDir, meta, attachments = {}, previousDir }) {
  // Refuse overwrite before doing any writes, including for invalid replacement input.
  if (await lstat(outputDir).then(() => true, (e) => { if (e.code === "ENOENT") return false; throw e; })) fail(`release already exists; refusing overwrite: ${outputDir}`);
  validateMeta(meta); validateData(data);
  if (meta.previous_version !== null) {
    if (!previousDir) fail("previousDir required to verify version lineage");
    const { data: previousData, verification: previous } = await readRelease(previousDir);
    if (previous.manifest.version !== meta.previous_version || previous.manifest_sha256 !== meta.previous_manifest_sha256) fail("previous release lineage mismatch");
    validateAppendOnlyEvidence(previousData, data);
    const required = actualReleaseChange(previousData, data, previous.manifest, meta);
    if (bumpLevels[classifyReleaseChange(meta.change_types)] > bumpLevels[required]) fail(`actual changes require at least ${required} release`);
  }
  await mkdir(dirname(outputDir), { recursive: true });
  const lockPath = `${outputDir}.lock`, lock = await open(lockPath, "wx");
  let temp;
  try {
    if (await lstat(outputDir).then(() => true, () => false)) fail("release exists; refusing overwrite");
    temp = await mkdtemp(join(dirname(outputDir), `.${basename(outputDir)}-`));
    const files = [];
    const add = async (path, content, rows = null) => {
      if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(path) || ["manifest.json", "manifest.sha256"].includes(path)) fail(`invalid attachment path: ${path}`);
      const bytes = Buffer.from(content);
      await writeFile(join(temp, path), bytes, { flag: "wx" });
      files.push({ path, bytes: bytes.length, rows, sha256: sha256(bytes) });
    };
    for (const name of collections) await add(`${name}.jsonl`, data[name].map((r) => JSON.stringify(r) + "\n").join(""), data[name].length);
    await add("schema.json", JSON.stringify(dataSchema, null, 2) + "\n");
    for (const [name, content] of Object.entries(attachments)) await add(name, content);
    files.sort((a, b) => a.path.localeCompare(b.path));
    const manifest = { ...meta, files };
    const json = JSON.stringify(manifest, null, 2) + "\n";
    await writeFile(join(temp, "manifest.json"), json, { flag: "wx" });
    await writeFile(join(temp, "manifest.sha256"), sha256(json) + "  manifest.json\n", { flag: "wx" });
    await verifyRelease(temp);
    await rename(temp, outputDir); temp = null;
    return manifest;
  } finally { if (temp) await rm(temp, { recursive: true, force: true }); await lock.close(); await rm(lockPath, { force: true }); }
}

export async function verifyRelease(dir) {
  return (await readRelease(dir)).verification;
}

async function readRelease(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  for (const e of entries) if (!e.isFile()) fail(`release integrity: non-regular file ${e.name}`);
  const raw = await readFile(join(dir, "manifest.json"));
  const hash = sha256(raw), expected = (await readFile(join(dir, "manifest.sha256"), "utf8")).trim();
  if (expected !== `${hash}  manifest.json`) fail("manifest hash integrity mismatch");
  const manifest = JSON.parse(raw); validateMeta(manifest);
  if (!Array.isArray(manifest.files)) fail("manifest file inventory missing");
  const files = unique(manifest.files, (r) => r.path, "manifest file");
  const listed = [...files.keys(), "manifest.json", "manifest.sha256"].sort();
  if (JSON.stringify(entries.map((r) => r.name).sort()) !== JSON.stringify(listed)) fail("release integrity: unlisted or missing file");
  const data = {};
  for (const f of manifest.files) {
    if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(f.path) || ["manifest.json", "manifest.sha256"].includes(f.path)) fail(`unsafe manifest path: ${f.path}`);
    const bytes = await readFile(join(dir, f.path));
    if (sha256(bytes) !== f.sha256 || bytes.length !== f.bytes) fail(`hash integrity mismatch: ${f.path}`);
    const name = f.path.replace(/\.jsonl$/, "");
    if (collections.includes(name) && f.path.endsWith(".jsonl")) {
      const content = bytes.toString("utf8");
      if (content && !content.endsWith("\n")) fail(`JSONL missing newline: ${f.path}`);
      data[name] = content ? content.slice(0, -1).split("\n").map((s) => JSON.parse(s)) : [];
      if (f.rows !== data[name].length) fail(`row count integrity: ${f.path}`);
    }
  }
  if (JSON.stringify(JSON.parse(await readFile(join(dir, "schema.json"), "utf8"))) !== JSON.stringify(dataSchema)) fail("unsupported or altered schema");
  const result = validateData(data);
  return { data, verification: { ...result, manifest, manifest_sha256: hash } };
}
