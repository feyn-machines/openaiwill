import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { appDir, appOutputs, designDir, designOutputs } from "./build-design-system.mjs";

const { tokens } = JSON.parse(readFileSync(resolve(designDir, "tokens.json"), "utf8"));
for (const [key, value] of Object.entries(tokens)) {
  assert.match(key, /^[a-z][a-z0-9-]+$/, `Invalid token name: ${key}`);
  assert.equal(typeof value, "string", `Token ${key} must be a CSS string`);
  assert(!/[;{}]/.test(value), `Unexpected CSS declaration in ${key}`);
}
for (const [file, expected] of designOutputs()) {
  assert.equal(readFileSync(resolve(designDir, file), "utf8"), expected, `${file} has drifted; run pnpm design:build`);
}
for (const [file, expected] of appOutputs()) {
  assert.equal(readFileSync(resolve(appDir, file), "utf8"), expected, `src/app/${file} has drifted; run pnpm design:build`);
  assert(!/\.ah-root\b/.test(expected), `src/app/${file} must not carry the dark .ah-root scope`);
  for (const key of Object.keys(tokens)) assert(expected.includes(`--ah-${key}:`), `src/app/${file} is missing --ah-${key}`);
}
const html = readFileSync(resolve(designDir, "preview.html"), "utf8");
assert(!html.includes("{{"), "Preview contains unresolved placeholders");
const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
assert.equal(ids.length, new Set(ids).size, "Preview has duplicate IDs");
for (const match of html.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
  const [path, anchor] = match[1].split("#");
  if (/^[a-z]+:/i.test(path)) continue;
  if (!path) assert(ids.includes(anchor), `Broken preview anchor: ${anchor}`);
  else assert(existsSync(resolve(designDir, decodeURIComponent(path))), `Missing resource: ${path}`);
}
for (const file of ["styles/tokens.css", "styles/fonts.css", "styles/components.css", "preview.css"]) {
  const css = readFileSync(resolve(designDir, file), "utf8");
  for (const [, key] of css.matchAll(/var\(--ah-([a-z0-9-]+)/g)) assert(key in tokens, `${file} uses undefined token ${key}`);
  for (const [, url] of css.matchAll(/url\(["']?([^"')]+)["']?\)/g)) {
    assert(!/^https?:/.test(url), `Runtime remote asset in ${file}`);
    assert(existsSync(resolve(designDir, dirname(file), url)), `Missing CSS asset: ${url}`);
  }
}
const fontFiles = JSON.parse(readFileSync(resolve(designDir, "fonts/manifest.json"), "utf8"));
for (const file of fontFiles) {
  const bytes = readFileSync(resolve(designDir, file.path));
  assert.equal(bytes.length, file.bytes, `${file.path}: size mismatch`);
  assert.equal(createHash("sha256").update(bytes).digest("hex"), file.sha256, `${file.path}: hash mismatch`);
  if (file.path.endsWith(".txt")) assert(bytes.toString().includes("SIL OPEN FONT LICENSE"), `${file.path}: missing license`);
}
const manifest = JSON.parse(readFileSync(resolve(designDir, "manifest.json"), "utf8"));
for (const { path } of manifest.resources) assert(existsSync(resolve(designDir, path)), `Manifest file missing: ${path}`);

const luminance = (hex) => {
  const rgb = hex.slice(1).match(/../g).map((part) => parseInt(part, 16) / 255)
    .map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
  return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
};
const pairs = [
  ...["text", "muted", "subtle", "signal", "estimate", "attention", "warning", "correction"].map((color) => [color, "bg", 4.5]),
  ["text", "surface", 4.5], ["muted", "surface-active", 4.5], ["subtle", "surface-active", 4.5],
  ["ink", "action", 4.5], ["ink", "signal", 4.5], ["ink", "paper", 4.5],
  ["control", "bg", 3], ["control", "surface", 3], ["focus", "bg", 3],
];
for (const [foreground, background, threshold] of pairs) {
  const a = luminance(tokens[`color-${foreground}`]);
  const b = luminance(tokens[`color-${background}`]);
  const ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
  assert(ratio >= threshold, `${foreground}/${background}: ${ratio.toFixed(2)}:1 below ${threshold}:1`);
  console.log(`Contrast ${foreground}/${background}: ${ratio.toFixed(2)}:1`);
}
console.log(`PASS: ${Object.keys(tokens).length} tokens, ${designOutputs().size + appOutputs().size} generated files, ${fontFiles.length} font/license hashes, ${pairs.length} contrast pairs and local resource references.`);
