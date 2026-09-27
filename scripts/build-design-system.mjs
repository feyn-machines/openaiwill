import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const designDir = fileURLToPath(new URL("../design/system-v1/", import.meta.url));
export const appDir = fileURLToPath(new URL("../src/app/", import.meta.url));

const readTokens = () => JSON.parse(readFileSync(resolve(designDir, "tokens.json"), "utf8")).tokens;
const declarations = (tokens) => Object.entries(tokens).map(([key, value]) => `  --ah-${key}: ${value};`).join("\n");

export function designOutputs() {
  const tokens = readTokens();
  const c = (name) => tokens[`color-${name}`];
  const text = (x, y, value, color = "muted", size = 12, extra = "") =>
    `<text x="${x}" y="${y}" fill="${c(color)}" font-size="${size}" ${extra}>${value}</text>`;
  const rect = (x, y, width, height, fill, extra = "") =>
    `<rect x="${x}" y="${y}" width="${width}" height="${height}" fill="${fill}" ${extra}/>`;
  const shell = (id, w, h, title, desc, body) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" role="img" aria-labelledby="${id}-title ${id}-desc">
<title id="${id}-title">${title}</title><desc id="${id}-desc">${desc}</desc>
<g font-family="'AH JetBrains Mono','JetBrains Mono',monospace">${body}</g>
</svg>\n`;
  const grid = (id, width, height) => `<defs><pattern id="${id}-grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="${c("grid")}" stroke-width="1"/></pattern></defs>${rect(0, 0, width, height, c("bg"))}${rect(0, 0, width, height, `url(#${id}-grid)`)}`;

  // A fixed original composition: visual rhythm only, not a series of data points.
  const bars = Array.from({ length: 44 }, (_, i) => {
    const x = 18 + i * 18;
    const wave = 100 + Math.round(48 * Math.sin(i * 0.19) + 26 * Math.cos(i * 0.39));
    const segments = [
      rect(x, 20, 7, wave, i % 4 === 0 ? c("action") : c("signal")),
      rect(x, wave + 32, 7, 28 + (i % 6) * 7, c("sage")),
      rect(x, wave + 80 + (i % 6) * 7, 7, Math.max(12, 195 - wave - (i % 6) * 7), c("surface-active")),
    ];
    return `<g>${segments.join("")}</g>`;
  }).join("");
  const strips = shell("ah-strips", 816, 312, "openaiwill signal strip composition", "Decorative bands, not a data chart or a logo.", bars);

  const source = (x, y, id, title, subtitle) => `${rect(x, y, 218, 102, c("surface"), `stroke="${c("control")}"`)}${Array.from({ length: 11 }, (_, i) => rect(x + 3, y + 7 + i * 8, 3, 3, c("signal"))).join("")}${text(x + 20, y + 25, id, "signal", 11)}${text(x + 20, y + 51, title, "text", 14)}${text(x + 20, y + 77, subtitle, "subtle", 11)}`;
  const flow = shell("ah-flow", 980, 460, "From sources to an estimated capability state", "Illustrative pipeline. A source and adoption report feed an event record. A reviewed event may revise a modeled capability state. Values are fictional design examples, not verified facts.", `
    ${grid("ah-flow", 980, 460)}
    ${text(28, 34, "OPENAIWILL / EVIDENCE SYSTEM", "signal", 12)}
    ${text(744, 34, "SCHEMATIC · V1.0", "subtle", 11)}
    <g fill="none" stroke="${c("signal")}" stroke-width="1.5" class="signal-link">
      <path d="M246 145H294V224H348"/><path d="M246 309H294V224"/>
      <path d="M580 224H688" stroke-dasharray="5 5"/>
    </g>
    ${rect(290, 220, 8, 8, c("signal"))}${rect(630, 220, 8, 8, c("signal"))}
    ${source(28, 94, "SOURCE / 01", "Official announcement", "Identity + source claim")}
    ${source(28, 258, "SOURCE / 02", "Company adoption", "Pilot / production / plan")}
    ${rect(348, 162, 232, 124, c("surface-active"), `stroke="${c("signal")}"`)}
    <path d="M348 192H580" stroke="${c("control")}"/>
    ${text(362, 182, "EVENT RECORD", "signal", 12)}
    ${text(364, 219, "A single occurrence", "text", 14)}
    ${text(364, 245, "Multiple sources attached", "muted", 11)}
    ${text(364, 269, "Claims remain attributed", "subtle", 11)}
    ${text(600, 202, "REVIEW", "signal", 10)}
    ${rect(688, 94, 264, 266, "none", `stroke="${c("signal")}" stroke-dasharray="3 4"`)}
    ${rect(700, 107, 240, 240, c("surface-active"), `stroke="${c("signal")}"`)}
    ${rect(700, 107, 240, 32, c("signal"))}
    ${text(714, 128, "CAPABILITY STATE", "ink", 12)}
    ${text(720, 170, "CENTRAL ESTIMATE", "sage", 10)}
    ${text(716, 229, "46.0", "text", 54)}${text(862, 229, "/ 100", "muted", 13)}
    <path d="M720 262H920" stroke="${c("control")}"/>
    <path d="M784 262H844" stroke="${c("sage")}" stroke-width="4"/>
    ${rect(807, 257, 10, 10, c("sage"))}
    ${text(720, 291, "32 — 62  SCENARIO RANGE", "muted", 11)}
    ${text(720, 321, "ILLUSTRATIVE / NOT LIVE", "subtle", 10)}
    <path d="M28 393H952" stroke="${c("line")}"/>
    ${text(28, 422, "01 / OBSERVE", "subtle", 11)}${text(348, 422, "02 / ATTRIBUTE", "subtle", 11)}${text(700, 422, "03 / ESTIMATE", "subtle", 11)}
  `);
  const flowMobile = shell("ah-flow-mobile", 360, 704, "来源到能力估计：纵向流程样本", "两项来源材料汇入同一个事件，关系经评审后才可能更新估计。虚构中心值46，保守32，乐观62；不是实时业务数据。", `
    ${grid("ah-flow-mobile", 360, 704)}
    ${text(20, 30, "EVIDENCE / EXAMPLE", "signal", 16)}
    ${rect(20, 54, 320, 190, c("surface"), `stroke="${c("control")}"`)}
    ${text(36, 84, "01 / SOURCES", "signal", 16)}
    ${text(36, 119, "Official announcement", "text", 18)}
    ${text(36, 145, "Identity + source claim", "muted", 16)}
    <path d="M36 162H324" stroke="${c("line")}"/>
    ${text(36, 190, "Company adoption", "text", 18)}
    ${text(36, 216, "Pilot / production / plan", "muted", 16)}
    <path d="M180 244V288" fill="none" stroke="${c("signal")}" stroke-width="1.5" class="signal-link"/>
    ${rect(176, 262, 8, 8, c("signal"))}
    ${rect(20, 288, 320, 128, c("surface-active"), `stroke="${c("signal")}"`)}
    ${text(36, 318, "02 / EVENT RECORD", "signal", 16)}
    ${text(36, 354, "A single occurrence", "text", 18)}
    ${text(36, 389, "Claims remain attributed", "muted", 16)}
    <path d="M180 416V466" fill="none" stroke="${c("signal")}" stroke-width="1.5" stroke-dasharray="5 5" class="signal-link"/>
    ${text(196, 447, "REVIEW", "signal", 14)}
    ${rect(176, 437, 8, 8, c("signal"))}
    ${rect(20, 466, 320, 214, c("surface-active"), `stroke="${c("signal")}" stroke-dasharray="3 4"`)}
    ${rect(20, 466, 320, 38, c("signal"))}
    ${text(36, 491, "03 / ESTIMATED STATE", "ink", 16)}
    ${text(36, 562, "46.0", "text", 52)}${text(188, 562, "/ 100", "muted", 18)}
    ${text(36, 600, "32 — 62 / SCENARIOS", "sage", 16)}
    ${text(36, 632, "FICTIONAL VALUES", "muted", 16)}
    ${text(36, 658, "NOT A LIVE SCORE", "muted", 16)}
  `);
  const range = shell("ah-range", 720, 240, "Illustrative scenario range", "Fictional conservative 32, central 46, optimistic 62 on a 0–100 scale. A scenario range is not a confidence interval.", `
    ${rect(0, 0, 720, 240, c("bg"))}
    ${text(24, 30, "SCENARIO EXAMPLE / 0–100", "subtle", 12)}
    <path d="M40 126H680" stroke="${c("control")}"/>
    ${[0, 25, 50, 75, 100].map((v) => `<path d="M${40 + v * 6.4} 119v14" stroke="${c("control")}"/>${text(40 + v * 6.4, 161, String(v), "subtle", 12, 'text-anchor="middle"')}`).join("")}
    <path d="M244.8 126H436.8" stroke="${c("sage")}" stroke-width="6"/>
    ${rect(329.4, 121, 10, 10, c("signal"), 'id="range-cursor"')}
    ${text(244.8, 99, "32", "sage", 14, 'text-anchor="middle"')}${text(334.4, 71, "46", "text", 24, 'id="range-current" text-anchor="middle"')}${text(436.8, 99, "62", "sage", 14, 'text-anchor="middle"')}
    ${text(24, 212, "FICTIONAL VALUES · SCENARIO RANGE, NOT CONFIDENCE INTERVAL", "subtle", 11)}
  `);
  const rangeMobile = shell("ah-range-mobile", 360, 190, "情景区间样本", "虚构保守32，中心46，乐观62；统一0至100尺度。", `
    ${rect(0, 0, 360, 190, c("bg"))}
    ${text(20, 27, "SCENARIOS / EXAMPLE", "subtle", 16)}
    <path d="M20 116H340" stroke="${c("control")}"/>
    <path d="M122.4 116H218.4" stroke="${c("sage")}" stroke-width="5"/>
    ${rect(162.2, 111, 10, 10, c("signal"), 'id="range-cursor-mobile"')}
    ${text(167.2, 71, "46", "text", 24, 'id="range-current-mobile" text-anchor="middle"')}
    ${[0, 50, 100].map((v) => `<path d="M${20 + v * 3.2} 109v14" stroke="${c("control")}"/>${text(20 + v * 3.2, 151, String(v), "subtle", 16, 'text-anchor="middle"')}`).join("")}
  `);
  const css = `/* Generated by pnpm design:build. Edit tokens.json. */\n.ah-root {\n${declarations(tokens)}\n}\n`;
  const preview = readFileSync(resolve(designDir, "preview.template.html"), "utf8")
    .replace("{{EVIDENCE_FLOW}}", flow)
    .replace("{{EVIDENCE_FLOW_MOBILE}}", flowMobile)
    .replace("{{SCENARIO_RANGE}}", range)
    .replace("{{SCENARIO_RANGE_MOBILE}}", rangeMobile);
  return new Map([
    ["styles/tokens.css", css],
    ["assets/signal-strips.svg", strips],
    ["assets/evidence-flow.svg", flow],
    ["assets/evidence-flow-mobile.svg", flowMobile],
    ["assets/scenario-range.svg", range],
    ["assets/scenario-range-mobile.svg", rangeMobile],
    ["preview.html", preview],
  ]);
}

// The same values for the Next.js app. Custom properties paint nothing on their
// own, so the light marketing pages keep their own palette in globals.css and
// the dark `.ah-root` scope from the design system never enters the app.
export function appOutputs() {
  const tokens = readTokens();
  const css = `/* Generated by pnpm design:build from design/system-v1/tokens.json. Do not edit. */
/* Design system v1 values for the app. Declarations only: a token paints nothing
   until a rule uses it, so importing this file changes no existing page. The
   color tokens are the dark design-system palette; the light page palette and
   its components stay in globals.css. The design system's dark root scope and
   components.css are not loaded here, so they cannot reach the light pages. */
:root {
${declarations(tokens)}
}
`;
  return new Map([["design-tokens.css", css]]);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const written = [[designDir, designOutputs()], [appDir, appOutputs()]];
  let count = 0;
  for (const [baseDir, outputs] of written) {
    for (const [path, contents] of outputs) {
      const destination = resolve(baseDir, path);
      mkdirSync(dirname(destination), { recursive: true });
      writeFileSync(destination, contents);
      count += 1;
    }
  }
  console.log(`Built ${count} design resources from tokens.json.`);
}
