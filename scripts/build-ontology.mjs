import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";
import { verifyRelease } from "./lib/platform-data.mjs";
import { projectOntology, validateOntology } from "./lib/ontology-data.mjs";
import { digest, ontologyVersion, sealOntology, verifyOntology } from "./lib/ontology-release.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const args = new Map();
for (const arg of process.argv.slice(2)) {
  const match = /^--(source|out)=(.+)$/.exec(arg);
  if (!match || args.has(match[1])) throw new Error("Usage: pnpm ontology:build [--source=path] [--out=path]");
  args.set(match[1], match[2]);
}
const source = resolve(args.get("source") ?? join(root, "datasets/platform/releases/v0.0.1"));
const out = resolve(args.get("out") ?? join(root, `datasets/ontology/releases/v${ontologyVersion}`));
const upstream = await verifyRelease(source);
const legacy = {};
for (const file of upstream.manifest.files.filter((file) => file.path.endsWith(".jsonl"))) {
  const bytes = await readFile(join(source, file.path));
  if (digest(bytes) !== file.sha256) throw new Error(`Source changed after verification: ${file.path}`);
  const text = bytes.toString("utf8");
  legacy[file.path.slice(0, -6)] = text ? text.slice(0, -1).split("\n").map((line) => JSON.parse(line)) : [];
}
const data = projectOntology(legacy);
const { counts } = validateOntology(data);
const sameIds = (before, after) => isDeepStrictEqual(before.map((r) => r.id).sort(), after.map((r) => r.id).sort());
if (!sameIds(legacy.nodes, data.concepts) || !sameIds(legacy.relations, data.relations) || !sameIds(legacy.external_mappings, data.external_mappings)) throw new Error("Ontology projection lost or changed existing identities");
for (const name of ["reference_occupations", "reference_tasks", "reference_activities", "reference_task_activity_links", "reference_taxonomy_codes", "coverage"]) {
  if (legacy[name].length !== data[name].length) throw new Error(`Ontology projection lost reference coverage: ${name}`);
}
const kinds = Object.fromEntries(["market_group", "market", "work", "occupation_group", "occupation"].map((kind) => [kind, data.concepts.filter((n) => n.kind === kind).length]));
const expected = { market_group: 40, market: 265, work: 19452, occupation_group: 23, occupation: 1016 };
if (upstream.manifest.version === "0.0.1" && !isDeepStrictEqual(kinds, expected)) throw new Error("Initial ontology must retain the full reference catalog");

const byId = new Map(data.concepts.map((n) => [n.id, n]));
const children = new Map();
for (const edge of data.relations) {
  const key = JSON.stringify([edge.view, edge.parent_id]);
  if (!children.has(key)) children.set(key, []);
  children.get(key).push(edge);
}
for (const edges of children.values()) edges.sort((a, b) => a.order - b.order);
const label = (n) => n.label_zh_cn ? `${n.label_zh_cn} / ${n.label_en}` : n.label_en;
function catalog(view, rootKind, title) {
  const lines = [`# ${title}`, "", "本目录从本体 JSONL 生成。ID 固定；名称可修订。目录中的关联只表达分类和工作关系。", ""];
  for (const group of data.concepts.filter((n) => n.kind === rootKind)) {
    lines.push(`## ${label(group)}`, "", `ID：\`${group.id}\``, "");
    if (group.definition) lines.push(group.definition.text, "");
    for (const relation of children.get(JSON.stringify([view, group.id])) ?? []) {
      const node = byId.get(relation.child_id);
      lines.push(`### ${label(node)}`, "", `ID：\`${node.id}\``, "");
      if (node.definition) lines.push(node.definition.text, "");
      const workEdges = children.get(JSON.stringify([view, node.id])) ?? [];
      for (const edge of workEdges) {
        const work = byId.get(edge.child_id);
        lines.push(`- ${label(work)} — \`${work.id}\``);
      }
      if (!workEdges.length) lines.push("来源未提供任务条目。");
      lines.push("");
    }
  }
  return lines.join("\n") + "\n";
}
const definitionCoverage = Object.fromEntries(Object.keys(kinds).map((kind) => {
  const rows = data.concepts.filter((n) => n.kind === kind);
  return [kind, { total: rows.length, with_definition: rows.filter((n) => n.definition !== null).length, label_only: rows.filter((n) => n.definition === null).length }];
}));
const coverage = {
  package: "ontology", version: ontologyVersion, counts, concept_kinds: kinds,
  work_origins: { onet_projection: data.concepts.filter((n) => n.kind === "work" && n.origin === "onet_projection").length, editorial_ai: data.concepts.filter((n) => n.kind === "work" && n.origin === "editorial_ai").length },
  definition_coverage: definitionCoverage,
  known_gaps: [
    "O*NET 31.0 是美国职业参考；完整导入不是全球职业普查。",
    "职业中文名称为 AI 翻译；职业任务仍保留英文原文，中文名称尚未提供。",
    "自定义工作与职业任务分别保留；尚未裁决二者之间的等价/交叉映射。",
    "定义为空的条目目前只有名称和分类位置，不能宣称范围已经完整定义。",
    "ISIC 关联为编辑候选覆盖，且仅保存代码层级，不再分发受限原文。",
  ],
};
const readme = `# openaiwill 本体 v${ontologyVersion}\n\n本地本体草案；结构版本不表示语义已穷尽或已生产发布。\n\n- 职业：${kinds.occupation_group} 个大类、${kinds.occupation} 个职业、${coverage.work_origins.onet_projection} 条任务。\n- 赛道：${kinds.market_group} 个领域、${kinds.market} 个赛道、${coverage.work_origins.editorial_ai} 项工作。\n- 共 ${counts.concepts} 个概念、${counts.relations} 条有类型的关系；沿用全部原有 ID。\n\n## 阅读顺序\n\n1. [model.json](model.json)：五种概念与四种关系的定义。\n2. [schema.json](schema.json)：标准 JSON Schema 2020-12。\n3. [赛道目录](market-catalog.md)与[职业及全部任务目录](occupation-catalog.md)。\n4. [覆盖与定义缺口](coverage-report.json)。\n\n概念在 concepts.jsonl，父子关联在 relations.jsonl，外部映射在 external_mappings.jsonl；reference_* 是来源定义和代码引用。指标、事件、进度值和权重不属于本包。\n\n本包由 platform/v${upstream.manifest.version} 提取，原包保留。manifest.json 记录来源根哈希及所有文件哈希；manifest.sha256 用于完整性检查，不是身份签名。\n\nO*NET 来源采用 CC BY 4.0；中文职业译名和编辑目录为改编/自有草案。ISIC 仅含代码和层级。详情见 sources.jsonl。\n`;
await sealOntology({ data, outputDir: out, derivedFrom: { package: "platform", version: upstream.manifest.version, manifest_sha256: upstream.manifest_sha256 }, attachments: {
  "README.md": readme,
  "market-catalog.md": catalog("markets", "market_group", "赛道与工作目录"),
  "occupation-catalog.md": catalog("occupations", "occupation_group", "职业与任务目录"),
  "coverage-report.json": JSON.stringify(coverage, null, 2) + "\n",
  "CHANGELOG.md": `# v${ontologyVersion}\n\n从 platform/v${upstream.manifest.version} 拆出独立本体合同；保留全部概念/关系 ID，新增关系类型及来源定义，排除运行模型、权重和来源统计值。\n`,
} });
const verified = await verifyOntology(out);
console.log(JSON.stringify({ output: out, version: ontologyVersion, counts, concept_kinds: kinds, definition_coverage: definitionCoverage, manifest_sha256: verified.manifest_sha256 }, null, 2));
