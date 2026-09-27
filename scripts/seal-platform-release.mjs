import { readFile } from "node:fs/promises";
import { resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";
import { nextVersion, classifyReleaseChange, sealRelease, verifyRelease } from "./lib/platform-data.mjs";

const args = process.argv.slice(2);
const inputArg = args.find((a) => a.startsWith("--input="));
if (!inputArg || args.some((a) => !a.startsWith("--input=") && !a.startsWith("--out-root="))) throw new Error("Usage: pnpm platform:seal --input=FILE [--out-root=DIR]");
const bundle = JSON.parse(await readFile(resolve(inputArg.slice(8)), "utf8"));
const releaseRoot = resolve(args.find((a) => a.startsWith("--out-root="))?.slice(11) ?? fileURLToPath(new URL("../datasets/platform/releases/", import.meta.url)));
// Iteration command requires a verified predecessor; initial creation has its own full-coverage builder.
if (typeof bundle.previous_version !== "string") throw new Error("previous_version is required for iteration");
nextVersion(bundle.previous_version, "patch"); // Validate before using a version in a filesystem path.
const previousDir = join(releaseRoot, `v${bundle.previous_version}`);
const previous = await verifyRelease(previousDir);
const inherited = (name, fallback) => Object.hasOwn(bundle, name) ? bundle[name] : previous.manifest[name] ?? fallback;
const isRecord = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const nonempty = (value) => typeof value === "string" && value.trim().length > 0;
function inputRecords(name) {
  const rows = inherited(name, []);
  if (!Array.isArray(rows)) throw new Error(`${name} must be an array`);
  const names = new Set();
  for (const row of rows) {
    if (!isRecord(row) || !nonempty(row.name) || typeof row.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(row.sha256) || !Number.isSafeInteger(row.bytes) || row.bytes < 0) throw new Error(`${name} requires name, SHA-256 and nonnegative integer bytes`);
    if (names.has(row.name)) throw new Error(`${name} has duplicate input name: ${row.name}`);
    names.add(row.name);
    if (name === "unintegrated_inputs" && row.status !== "raw_not_integrated") throw new Error("unintegrated_inputs requires raw_not_integrated status");
    for (const field of ["version", "source_version", "source_id"]) if (Object.hasOwn(row, field) && !nonempty(row[field])) throw new Error(`${name} has invalid ${field}`);
  }
  return rows;
}
const sourceInputs = inputRecords("source_inputs");
const unintegratedInputs = inputRecords("unintegrated_inputs");
const methodVersions = inherited("method_versions", {});
if (!isRecord(methodVersions) || Object.entries(methodVersions).some(([name, version]) => !nonempty(name) || (version !== null && !nonempty(version)))) throw new Error("method_versions must map nonempty method names to version strings or null");
const suppliedCoverage = inherited("coverage_summary", {});
if (!isRecord(suppliedCoverage)) throw new Error("coverage_summary must be an object");
if (Object.hasOwn(suppliedCoverage, "known_gaps") && (!Array.isArray(suppliedCoverage.known_gaps) || suppliedCoverage.known_gaps.some((gap) => !nonempty(gap)))) throw new Error("coverage_summary.known_gaps must be an array of nonempty descriptions");
const coverageSummary = { ...suppliedCoverage };
// Initial-only counters describe the first snapshot, not the current release.
delete coverageSummary.initial_events;
delete coverageSummary.initial_estimates;
const countKind = (kind, origin) => bundle.data.nodes.filter((node) => node.kind === kind && node.origin === origin).length;
const currentCounts = {
  occupations: countKind("occupation", "onet_projection"),
  occupation_groups: countKind("occupation_group", "onet_projection"),
  occupational_tasks: countKind("work", "onet_projection"),
  market_domains: countKind("market_group", "editorial_ai"),
  submarkets: countKind("market", "editorial_ai"),
  market_work_items: countKind("work", "editorial_ai"),
  isic_sections_covered: bundle.data.coverage.length,
  task_activity_links: bundle.data.reference_task_activity_links.length,
  occupations_without_tasks: bundle.data.nodes.filter((node) => node.scope_status === "source_missing_tasks").length,
  task_importance_missing: bundle.data.reference_tasks.filter((task) => task.importance === null).length,
  task_importance_suppressed: bundle.data.reference_tasks.filter((task) => task.importance?.suppress).length,
  weight_methods: Object.fromEntries([...new Set(bundle.data.weights.map((weight) => weight.method))].map((method) => [method, bundle.data.weights.filter((weight) => weight.method === method).length])),
  events: bundle.data.events.length,
  observations: bundle.data.observations.length,
  progress_updates: bundle.data.progress_updates.length,
  assessed_progress: bundle.data.progress.filter((progress) => progress.value !== null).length,
  market_to_occupation_mappings_reviewed: bundle.data.external_mappings.filter((mapping) => mapping.external_type === "onet_occupation" && mapping.status === "reviewed" && bundle.data.nodes.some((node) => node.id === mapping.node_id && node.origin === "editorial_ai")).length,
};
if (Object.hasOwn(bundle, "coverage_summary")) {
  for (const [name, actual] of Object.entries(currentCounts)) if (Object.hasOwn(suppliedCoverage, name) && !isDeepStrictEqual(suppliedCoverage[name], actual)) throw new Error(`coverage_summary.${name} disagrees with candidate data`);
  if (Object.hasOwn(suppliedCoverage, "initial_events") || Object.hasOwn(suppliedCoverage, "initial_estimates")) throw new Error("coverage_summary initial counters belong only to the initial release; use current events and assessed_progress");
}
Object.assign(coverageSummary, currentCounts);
const version = nextVersion(bundle.previous_version, classifyReleaseChange(bundle.change_types));
const outputDir = join(releaseRoot, `v${version}`);
await sealRelease({ data: bundle.data, attachments: bundle.attachments ?? {}, outputDir, previousDir, meta: {
  version, schema_version: bundle.schema_version ?? "0.0.1", created_at: new Date().toISOString(), previous_version: bundle.previous_version,
  previous_manifest_sha256: previous.manifest_sha256, change_types: bundle.change_types, summary: bundle.summary, status: "local_draft",
  source_inputs: sourceInputs, method_versions: methodVersions,
  unintegrated_inputs: unintegratedInputs, coverage_summary: coverageSummary,
} });
const result = await verifyRelease(outputDir);
console.log(JSON.stringify({ output: outputDir, version, manifest_sha256: result.manifest_sha256, counts: result.counts }, null, 2));
