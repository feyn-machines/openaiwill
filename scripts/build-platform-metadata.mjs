import { readFile, readdir } from "node:fs/promises";
import { resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
import { collections } from "./lib/platform-schema.mjs";
import { inferTaskWeights, sealRelease, verifyRelease, sha256 } from "./lib/platform-data.mjs";

const root = fileURLToPath(new URL("../", import.meta.url));
const args = process.argv.slice(2);
if (args.some((a) => !a.startsWith("--reference=") && !a.startsWith("--out="))) throw new Error("Usage: node scripts/build-platform-metadata.mjs [--reference=DIR] [--out=DIR]");
const reference = resolve(args.find((a) => a.startsWith("--reference="))?.slice(12) ?? join(root, "data/reference/work-taxonomy/2026-09-12"));
const out = resolve(args.find((a) => a.startsWith("--out="))?.slice(6) ?? join(root, "datasets/platform/releases/v0.0.1"));
const inputs = [];
async function input(path, name) {
  const raw = await readFile(path); inputs.push({ name, sha256: sha256(raw), bytes: raw.length }); return JSON.parse(raw);
}
const normalized = {};
for (const name of ["job-families", "occupations", "tasks", "work-activities", "task-activity-links", "isic-rev5"]) normalized[name] = await input(join(reference, "normalized", `${name}.json`), `${name}.json`);
const markets = await input(join(root, "datasets/platform/source/markets.v0.0.1.json"), "markets.v0.0.1.json");
const translations = await input(join(root, "datasets/platform/source/occupation-labels.zh-CN.v0.0.1.json"), "occupation-labels.zh-CN.v0.0.1.json");
const expectedCounts = { "job-families": 23, occupations: 1016, tasks: 18838, "work-activities": 2460, "task-activity-links": 24087, "isic-rev5": 830 };
for (const [name, count] of Object.entries(expectedCounts)) if (normalized[name].length !== count) throw new Error(`Full source coverage failed for ${name}: expected ${count}, got ${normalized[name].length}`);
for (const name of ["occupations", "tasks"]) if (normalized[name].some((r) => r.source_version !== "31.0")) throw new Error(`Unexpected source version in ${name}; this builder requires O*NET 31.0`);
if (translations.source_version !== "31.0" || translations.is_official_translation !== false || translations.translation_method !== "ai_translation") throw new Error("Translation provenance mismatch");
const labels = new Map(translations.labels.map((r) => [r.source_code, r]));
if (labels.size !== 1016 || translations.labels.length !== 1016) throw new Error("Exactly 1016 unique occupation translations required");
for (const o of normalized.occupations) {
  const t = labels.get(o.source_code);
  if (!t || t.label_en !== o.label_en || !/[\u3400-\u9fff]/.test(t.label_zh_cn)) throw new Error(`Missing or mismatched occupation translation: ${o.source_code}`);
}
if (markets.version !== "0.0.1" || markets.status !== "ai_proposed_catalog" || markets.domains.length < 22) throw new Error("Broad market catalog and AI provenance required");
const sections = normalized["isic-rev5"].filter((r) => r.kind === "section").map((r) => r.source_code).sort();
if (JSON.stringify(markets.coverage.map((r) => r.isic_section).sort()) !== JSON.stringify(sections)) throw new Error("Market coverage must include every ISIC Rev.5 section exactly once");
for (const d of markets.domains) if (!d.isic_sections?.length || new Set(d.isic_sections).size !== d.isic_sections.length || d.isic_sections.some((s) => !sections.includes(s))) throw new Error(`Invalid ISIC references in domain ${d.id}`);
for (const c of markets.coverage) {
  const actual = markets.domains.filter((d) => d.isic_sections.includes(c.isic_section)).map((d) => d.id).sort();
  if (JSON.stringify([...c.domain_ids].sort()) !== JSON.stringify(actual)) throw new Error(`Coverage disagrees with domain references: ${c.isic_section}`);
}
const data = Object.fromEntries(collections.map((n) => [n, []]));
data.reference_occupations = normalized.occupations;
data.reference_tasks = structuredClone(normalized.tasks);
for (const t of data.reference_tasks) for (const field of ["importance", "relevance"]) if (t[field]?.suppress) t[field].value = null;
data.reference_activities = normalized["work-activities"];
data.reference_task_activity_links = normalized["task-activity-links"];
data.reference_taxonomy_codes = normalized["isic-rev5"].map(({ id, source_code, kind, parent_id }) => ({ id, source_code, kind, parent_id }));
data.sources = [
  { id: "onet-31.0", version: "31.0", url: "https://www.onetcenter.org/database.html", license: "CC-BY-4.0", status: "reference", note: "O*NET 31.0; Chinese occupation labels and normalized weights are openaiwill adaptations, not official translations or employment/time shares. Low-precision IM/RT values withheld in this export; original local archives preserved." },
  { id: "isic-rev5", version: "5", url: "https://unstats.un.org/unsd/classifications/Econ/isic", license: "redistribution_not_confirmed_code_references_only", status: "reference", note: "Only classification codes, hierarchy identifiers and our own coverage notes included. Original descriptions are not redistributed." },
  { id: "openaiwill-editorial", version: "0.0.1", url: "https://openaiwill.com", license: "project_owned_draft", status: "editorial_draft", note: "AI-proposed market categories and sibling weights; no reviewed global denominator or capability baseline." },
  { id: "bls-ep-2025-35", version: "2025-35", url: "https://www.bls.gov/emp/data/occupational-data.htm", license: "US-government-data", status: "raw_not_integrated", note: "Three local XLSX archives passed ZIP/workbook-container checks. Employment cells have not been semantically validated or applied to this release's weights." },
];
const familyZh = { "11": "管理", "13": "商业与财务运营", "15": "计算机与数学", "17": "建筑与工程", "19": "生命、自然与社会科学", "21": "社区与社会服务", "23": "法律", "25": "教育教学与图书馆", "27": "艺术、设计、娱乐、体育与媒体", "29": "医疗专业与技术", "31": "医疗辅助", "33": "公共安全与保护服务", "35": "餐饮制作与服务", "37": "建筑与环境清洁维护", "39": "个人护理与生活服务", "41": "销售及相关工作", "43": "办公室与行政支持", "45": "农业、渔业与林业", "47": "施工与资源开采", "49": "安装、维护与修理", "51": "生产制造", "53": "运输与物料搬运", "55": "军事专门职业" };
const mapping = (node, type, code, source = "onet-31.0", method = "source_id") => data.external_mappings.push({ id: `mapping:${node}:${type}:${code}`, node_id: node, source_id: source, external_type: type, external_id: code, relation: method === "source_id" ? "source_projection" : "related", method, status: method === "source_id" ? "source_reference" : "candidate" });
const node = (id, kind, zh, en, origin, scope = "defined", scopeNote) => data.nodes.push({ id, kind, label_zh_cn: zh, label_en: en, origin, translation_status: zh === null ? "pending" : "ai_translated", scope_status: scope, ...(scopeNote ? { scope_note: scopeNote } : {}) });
function relation(view, parent, child, order, value, method, basis, explanation) {
  const id = `relation:${view}:${parent}:${child}`;
  data.relations.push({ id, view, parent_id: parent, child_id: child, order });
  data.weights.push({ relation_id: id, value, method, method_version: "0.0.1", basis_value: basis, explanation, status: "draft" });
}
const taskGroups = new Map();
for (const t of normalized.tasks) { if (!taskGroups.has(t.occupation_id)) taskGroups.set(t.occupation_id, []); taskGroups.get(t.occupation_id).push(t); }
for (const o of normalized.occupations) if ((taskGroups.get(o.id)?.length ?? 0) !== o.source_task_count) throw new Error(`Occupation task count mismatch: ${o.source_code}`);
const families = [...normalized["job-families"]].sort((a, b) => a.source_code.localeCompare(b.source_code));
const occupationPreview = ["# 职业目录 v0.0.1", "", "23 个职业大类、1,016 个职业；中文为 AI 翻译，完整职业任务见 nodes.jsonl 与 reference_tasks.jsonl。93 个职业没有 O*NET 任务，进度保持未知。", ""];
for (const f of families) {
  const fid = `oaw:occupation-group:${f.source_code}`;
  node(fid, "occupation_group", familyZh[f.source_code], f.label_en, "onet_projection"); mapping(fid, "onet_family", f.source_code);
  const occupations = normalized.occupations.filter((o) => o.family_id === f.id).sort((a, b) => a.source_code.localeCompare(b.source_code));
  occupationPreview.push(`## ${familyZh[f.source_code]} / ${f.label_en}（${occupations.length}）`, "");
  for (const [i, o] of occupations.entries()) {
    const oid = `oaw:occupation:${o.source_code}`, tasks = taskGroups.get(o.id) ?? [], zh = labels.get(o.source_code).label_zh_cn;
    node(oid, "occupation", zh, o.label_en, "onet_projection", tasks.length ? "defined" : "source_missing_tasks"); mapping(oid, "onet_occupation", o.source_code);
    relation("occupations", fid, oid, i, 1 / occupations.length, "equal_occupation_prior", null, "暂按本职业大类内职业等分；就业统计尚未应用，不代表职业规模。 ");
    occupationPreview.push(`- ${o.source_code} · ${zh} / ${o.label_en} · ${tasks.length} 条任务`);
    const weights = inferTaskWeights(tasks);
    for (const [j, t] of tasks.entries()) {
      const tid = `oaw:task:${t.source_task_id}`, w = weights[j];
      node(tid, "work", null, t.statement_en, "onet_projection"); mapping(tid, "onet_task", t.source_task_id);
      relation("occupations", oid, tid, j, w.value, w.method, w.basis_value,
        w.method === "source_importance_normalized" ? "本职业内有效任务重要性 IM 归一化；它是重要性代理，非工时或经济份额。" : w.method === "imputed_occupation_mean" ? "本任务缺失或低精度 IM，以本职业其他有效 IM 均值补值后归一化；原始缺值仍保留。" : "本职业没有可用 IM，暂按任务等分；不冒充来源测量。 ");
    }
  }
  occupationPreview.push("");
}
const marketPreview = ["# 赛道目录 v0.0.1", "", "自有编辑目录；关联 ISIC Rev.5 全部门类以检查覆盖。括号内为相对直接父节点的 AI 初始权重，不能跨父节点直接比较。顶层领域没有世界权重。", ""];
for (const d of markets.domains) {
  const did = `oaw:market:${d.id}`;
  node(did, "market_group", d.label_zh_cn, d.label_en, "editorial_ai", "starter_catalog", d.scope_note);
  for (const code of d.isic_sections) mapping(did, "isic_section", code, "isic-rev5", "ai_proposed");
  marketPreview.push(`## ${d.label_zh_cn} / ${d.label_en}`, "", `${d.scope_note}（ISIC 关联：${d.isic_sections.join("、")}）`, "");
  if (!d.children?.length) throw new Error(`Empty market domain ${d.id}`);
  for (const [i, m] of d.children.entries()) {
    const mid = `oaw:market:${m.id}`;
    node(mid, "market", m.label_zh_cn, m.label_en, "editorial_ai");
    relation("markets", did, mid, i, m.weight, "ai_proposed", null, m.weight_reason);
    marketPreview.push(`### ${m.label_zh_cn}（${(m.weight * 100).toFixed(1)}%）`, "");
    if (!m.children?.length) throw new Error(`Empty submarket ${m.id}`);
    for (const [j, w] of m.children.entries()) {
      const wid = `oaw:market:${w.id}`;
      node(wid, "work", w.label_zh_cn, w.label_en, "editorial_ai");
      relation("markets", mid, wid, j, w.weight, "ai_proposed", null, w.weight_reason);
      marketPreview.push(`- ${w.label_zh_cn} / ${w.label_en}（${(w.weight * 100).toFixed(1)}%）`);
    }
    marketPreview.push("");
  }
}
data.coverage = markets.coverage.map((r) => ({ ...r, domain_ids: r.domain_ids.map((id) => `oaw:market:${id}`) }));
const metric = (id, label, valueType, unit, role, allowed = [], minimum = null, maximum = null) => ({ id, label_zh_cn: label, value_type: valueType, unit, role, allowed_values: allowed, minimum, maximum });
data.metric_definitions = [
  metric("likes", "点赞数", "integer", "count", "attention", [], 0), metric("views", "浏览数", "integer", "count", "attention", [], 0),
  metric("reposts", "转发数", "integer", "count", "attention", [], 0), metric("replies", "回复数", "integer", "count", "attention", [], 0),
  metric("availability", "可用阶段", "enum", "stage", "availability", ["announced", "demo", "private_preview", "public_preview", "generally_available", "withdrawn"]),
  metric("adoption_stage", "采用阶段", "enum", "stage", "adoption", ["plan", "pilot", "integrated", "production", "discontinued"]),
  metric("success_rate", "给定测试范围内成功率", "number", "percent", "performance", [], 0, 100),
  metric("sample_size", "测试样本数", "integer", "count", "performance", [], 0),
  metric("human_minutes", "每次交付人工介入时间", "number", "minutes", "human_involvement", [], 0),
  metric("delivery_cost_usd", "每次交付成本", "number", "USD", "cost", [], 0),
];
const memberships = new Map();
for (const r of data.relations) for (const id of [r.parent_id, r.child_id]) memberships.set(JSON.stringify([id, r.view]), { node_id: id, view: r.view, value: null, status: "unassessed", as_of: null, update_id: null });
data.progress = [...memberships.values()];
const countKind = (kind, origin) => data.nodes.filter((n) => n.kind === kind && n.origin === origin).length;
const summary = {
  occupations: 1016, occupation_groups: 23, occupational_tasks: 18838,
  market_domains: countKind("market_group", "editorial_ai"), submarkets: countKind("market", "editorial_ai"), market_work_items: countKind("work", "editorial_ai"),
  isic_sections_covered: data.coverage.length, task_activity_links: data.reference_task_activity_links.length,
  occupations_without_tasks: data.nodes.filter((n) => n.scope_status === "source_missing_tasks").length,
  task_importance_missing: normalized.tasks.filter((t) => t.importance === null).length,
  task_importance_suppressed: normalized.tasks.filter((t) => t.importance?.suppress).length,
  weight_methods: Object.fromEntries([...new Set(data.weights.map((w) => w.method))].map((m) => [m, data.weights.filter((w) => w.method === m).length])),
  initial_estimates: 0, initial_events: 0, market_to_occupation_mappings_reviewed: 0,
};
// Record which BLS containers are present, without treating that as imported statistics.
const rawFiles = await readdir(join(reference, "raw"));
const blsContainers = [];
for (const name of ["matrix.xlsx", "nem-onet-to-soc-crosswalk.xlsx", "nem-industry-coverage.xlsx"]) if (rawFiles.includes(name)) {
  const raw = await readFile(join(reference, "raw", name));
  blsContainers.push({ name, sha256: sha256(raw), bytes: raw.length, status: "raw_not_integrated" });
}
const readme = `# openaiwill 平台元数据 v0.0.1\n\n本地数据草案，已封存，不代表网页已经接入或已生产发布。\n\n- 职业入口：23 个大类 → 1,016 个职业 → 18,838 条职业任务。\n- 赛道入口：${summary.market_domains} 个领域 → ${summary.submarkets} 个细分赛道 → ${summary.market_work_items} 个工作项。\n- ISIC Rev.5：22/22 门类均有覆盖说明；这不是对所有商业细分的穷尽声明。\n- 所有初始进度为 null；事件、观测和更新集合为空，10 个指标定义已就位。\n\n直接审阅 [赛道目录](market-catalog.md)、[职业目录](occupation-catalog.md)、[覆盖与缺口](coverage-report.json)。每行 JSONL 是一个记录；schema.json 包含字段合同。\n\nO*NET 是美国职业参考；其完整导入不等于全球或中国职业普查。职业中文名全部为 AI 翻译；职业任务目前保留完整英文，中文为空。O*NET 31.0 采用 CC BY 4.0，详见 sources.jsonl 和 [O*NET 许可](https://www.onetcenter.org/license_db.html)；翻译、重组与权重是本项目改编。ISIC 仅引用代码和层级，不转存许可尚未确认的原文。\n\n赛道权重为 AI 草案。职业任务使用有效 IM 重要性归一化，缺值用职业均值或等分；IM 不是工时、就业或经济份额。${summary.occupations_without_tasks} 个职业缺任务，${summary.task_importance_missing} 条任务缺 IM，${summary.task_importance_suppressed} 条 IM 被标记低精度。BLS 原工作簿已在本地，统计尚未应用。本版没有统一世界总分；两个入口也没有通过候选映射自动传递分数。\n\n冻结规则见 [版本规范](../../VERSIONING.md)。运行 \`pnpm platform:check\` 检查 Schema、引用、份额、进度语义与 SHA-256。manifest.sha256 是完整性校验，不是数字签名。\n`;
const manifest = await sealRelease({ data, outputDir: out, meta: {
  version: "0.0.1", schema_version: "0.0.1", created_at: new Date().toISOString(), previous_version: null, previous_manifest_sha256: null, change_types: ["initial"],
  summary: "Full O*NET occupation/task reference and broad AI-proposed market catalog; unknown initial progress.", status: "local_draft", source_inputs: inputs, unintegrated_inputs: blsContainers,
  method_versions: { task_weight: "importance-prior/0.0.1", market_weight: "ai-proposed/0.0.1", occupation_weight: "equal-prior/0.0.1", capability_estimator: null }, coverage_summary: summary,
}, attachments: { "README.md": readme, "market-catalog.md": marketPreview.join("\n") + "\n", "occupation-catalog.md": occupationPreview.join("\n") + "\n", "coverage-report.json": JSON.stringify(summary, null, 2) + "\n", "CHANGELOG.md": "# v0.0.1\n\n首版完整职业参考与广覆盖赛道草案；初始权重、指标合同、空事件和未知进度。没有前版，无能力变化可比较。\n" } });
const verified = await verifyRelease(out);
console.log(JSON.stringify({ output: out, version: manifest.version, ...summary, manifest_sha256: verified.manifest_sha256 }, null, 2));
