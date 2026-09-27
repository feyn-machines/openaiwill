import { readdir } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { verifyRelease } from "./lib/platform-data.mjs";
const base = fileURLToPath(new URL("../datasets/platform/releases/", import.meta.url));
const dirs = (await readdir(base, { withFileTypes: true })).filter((d) => d.isDirectory() && /^v\d+\.\d+\.\d+$/.test(d.name));
if (!dirs.length) throw new Error("No sealed platform releases found");
const releases = new Map();
for (const d of dirs) {
  const result = await verifyRelease(join(base, d.name));
  if (d.name !== `v${result.manifest.version}`) throw new Error(`Version directory mismatch: ${d.name}`);
  releases.set(result.manifest.version, result);
}
for (const [version, r] of releases) {
  if (r.manifest.previous_version !== null) {
    const previous = releases.get(r.manifest.previous_version);
    if (!previous || previous.manifest_sha256 !== r.manifest.previous_manifest_sha256) throw new Error(`Broken release lineage: ${version}`);
  }
  console.log(`platform v${version}: ${r.counts.nodes} nodes, ${r.counts.relations} relations, ${r.counts.progress} progress rows; schema, references, weights and hashes valid`);
}
