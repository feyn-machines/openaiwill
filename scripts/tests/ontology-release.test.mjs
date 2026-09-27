import test, { before } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile, rm, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createHash } from "node:crypto";
import { projectOntology } from "../lib/ontology-data.mjs";
import { sealOntology, verifyOntology } from "../lib/ontology-release.mjs";

const sourceRoot = new URL("../../datasets/platform/releases/v0.0.1/", import.meta.url);
const sourceCollections = ["nodes", "relations", "external_mappings", "sources", "reference_occupations", "reference_tasks", "reference_activities", "reference_task_activity_links", "reference_taxonomy_codes", "coverage"];
let data, derivedFrom;
before(async () => {
  const original = Object.fromEntries(await Promise.all(sourceCollections.map(async (name) => {
    const text = await readFile(new URL(`${name}.jsonl`, sourceRoot), "utf8");
    return [name, text.trim() ? text.trimEnd().split("\n").map(JSON.parse) : []];
  })));
  data = projectOntology(original);
  derivedFrom = { package: "platform", version: "0.0.1", manifest_sha256: createHash("sha256").update(await readFile(new URL("manifest.json", sourceRoot))).digest("hex") };
});

async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), "openaiwill-ontology-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const outputDir = join(root, "release");
  await sealOntology({ data, outputDir, derivedFrom, attachments: { "README.md": "# 测试本体\n" } });
  return outputDir;
}

async function rewriteManifest(dir, mutate) {
  const manifest = JSON.parse(await readFile(join(dir, "manifest.json"), "utf8"));
  await mutate(manifest);
  const text = JSON.stringify(manifest, null, 2) + "\n";
  await writeFile(join(dir, "manifest.json"), text);
  await writeFile(join(dir, "manifest.sha256"), createHash("sha256").update(text).digest("hex") + "  manifest.json\n");
}

test("sealed ontology round-trips the full catalog and its source identity", async (t) => {
  const result = await verifyOntology(await fixture(t));
  assert.equal(result.manifest.package, "ontology");
  assert.equal(result.manifest.version, "1.0.0");
  assert.equal(result.counts.concepts, 20796);
  assert.equal(result.counts.relations, 20733);
  assert.equal(result.counts.reference_tasks, 18838);
  assert.deepEqual(result.manifest.derived_from, derivedFrom);
  assert.equal(result.data.concepts.find((row) => row.id === "oaw:occupation-group:11").label_zh_cn, "管理");
  assert.equal(result.data.events, undefined);
  assert.equal(result.data.progress, undefined);
});

test("refuses to overwrite a sealed release, preserving its manifest bytes", async (t) => {
  const dir = await fixture(t);
  const before = await readFile(join(dir, "manifest.json"), "utf8");
  await assert.rejects(sealOntology({ data, outputDir: dir, derivedFrom }), /exist|overwrite/i);
  assert.equal(await readFile(join(dir, "manifest.json"), "utf8"), before);
});

test("detects payload modification", async (t) => {
  const dir = await fixture(t);
  await writeFile(join(dir, "concepts.jsonl"), "{}\n");
  await assert.rejects(verifyOntology(dir), /hash|integrity/i);
});

test("detects unexpected files including accidentally exported runtime data", async (t) => {
  const dir = await fixture(t);
  await writeFile(join(dir, "progress.jsonl"), "{}\n");
  await assert.rejects(verifyOntology(dir), /inventory|unlisted/i);
});

test("rejects symbolic links in a release", async (t) => {
  const dir = await fixture(t);
  await rm(join(dir, "README.md"));
  await symlink("schema.json", join(dir, "README.md"));
  await assert.rejects(verifyOntology(dir), /regular|symlink/i);
});

test("checks row counts even when the manifest checksum is consistent", async (t) => {
  const dir = await fixture(t);
  await rewriteManifest(dir, (m) => { m.files.find((f) => f.path === "concepts.jsonl").rows = 1; });
  await assert.rejects(verifyOntology(dir), /row count/i);
});

test("checks summary counts against actual records", async (t) => {
  const dir = await fixture(t);
  await rewriteManifest(dir, (m) => { m.counts.concepts = 1; });
  await assert.rejects(verifyOntology(dir), /count/i);
});

test("does not accept an altered ontology model even with updated file hashes", async (t) => {
  const dir = await fixture(t);
  const altered = Buffer.from('{"anything":"allowed"}\n');
  await writeFile(join(dir, "model.json"), altered);
  await rewriteManifest(dir, (m) => {
    const f = m.files.find((f) => f.path === "model.json");
    f.sha256 = createHash("sha256").update(altered).digest("hex");
    f.bytes = altered.length;
  });
  await assert.rejects(verifyOntology(dir), /model|contract/i);
});

test("does not accept manifest paths outside the release directory", async (t) => {
  const dir = await fixture(t);
  await rewriteManifest(dir, (m) => { m.files.find((f) => f.path === "README.md").path = "../README.md"; });
  await assert.rejects(verifyOntology(dir), /path|inventory/i);
});

test("rejects attachments that masquerade as runtime collections", async (t) => {
  const root = await mkdtemp(join(tmpdir(), "openaiwill-ontology-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  await assert.rejects(sealOntology({ data, outputDir: join(root, "bad"), derivedFrom, attachments: { "events.jsonl": "" } }), /attachment/i);
});

test("source provenance requires scalar version and hash strings", async (t) => {
  const root = await mkdtemp(join(tmpdir(), "openaiwill-ontology-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  for (const field of ["version", "manifest_sha256"]) {
    await assert.rejects(sealOntology({ data, outputDir: join(root, field), derivedFrom: { ...derivedFrom, [field]: [derivedFrom[field]] } }), /provenance/i);
  }
});

test("concurrent builders cannot publish two releases to the same path", async (t) => {
  const root = await mkdtemp(join(tmpdir(), "openaiwill-ontology-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const outputDir = join(root, "release");
  const outcomes = await Promise.allSettled([
    sealOntology({ data, outputDir, derivedFrom }),
    sealOntology({ data, outputDir, derivedFrom }),
  ]);
  assert.equal(outcomes.filter((r) => r.status === "fulfilled").length, 1);
  assert.equal(outcomes.filter((r) => r.status === "rejected").length, 1);
  assert.equal((await verifyOntology(outputDir)).counts.concepts, 20796);
});
