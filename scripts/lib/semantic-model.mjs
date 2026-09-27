// Loader and validator for the semantic layer. The semantic model is the single
// source of truth: SQL CHECK constraints, extraction prompts, judgment rubrics
// and site labels are all projected from it. Nothing here reads the database.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
export const semanticModelPath = join(root, "datasets", "semantic", "semantic-model.v2.json");

export const semanticModel = JSON.parse(readFileSync(semanticModelPath, "utf8"));

/** Gate definitions, which are instances and live outside the model. */
export const gatesPath = join(root, "datasets", "semantic", "gates.v1.json");
export const gates = JSON.parse(readFileSync(gatesPath, "utf8"));

/** Term ids of a vocabulary, in declaration order, whatever shape it uses. */
export function termIds(name) {
  const vocabulary = semanticModel.vocabularies[name];
  if (!vocabulary) throw new Error(`Unknown vocabulary: ${name}`);
  const terms = vocabulary.terms;
  if (Array.isArray(terms)) return [...terms];
  if (terms && typeof terms === "object") return Object.keys(terms);
  throw new Error(`Vocabulary ${name} has no terms`);
}

/** Term body, or an empty object for list-shaped vocabularies. */
export function term(name, id) {
  const terms = semanticModel.vocabularies[name].terms;
  if (Array.isArray(terms)) return terms.includes(id) ? {} : undefined;
  return terms[id];
}

/** Columns the semantic layer governs, so a checker can compare CHECK lists. */
export const governedColumns = {
  "extracted_events.kind": "event_kind",
  "activity_evidence.evidence_tier": "evidence_tier",
  "activity_evidence.method": "relation_method",
  "activity_evidence.status": "relation_status",
  "activity_task_edges.method": "relation_method",
  "activity_task_edges.status": "relation_status",
  "activity_gate_edges.method": "relation_method",
  "activity_gate_edges.status": "relation_status",
  "market_occupation_edges.method": "relation_method",
  "market_occupation_edges.status": "relation_status",
  "gates.gate_type": "gate_type",
  "gates.lifecycle": "lifecycle",
  "source_accounts.panel_role": "panel_role",
  "source_accounts.panel_state": "panel_state",
  "source_accounts.identity_grade": "identity_evidence_grade",
  "person_affiliations.relation": "affiliation_relation",
  "source_account_checks.check_kind": "account_check_kind",
  "verification_evidence.post_nature": "post_nature",
  "verification_evidence.evidence_tier": "evidence_tier",
  "verification_evidence.status": "relation_status",
  "event_posts.link": "post_link",
};

const SQL_IDENT = /^[a-z][a-z0-9_]*$/;

/** Vocabularies whose term ids are numbers on a scale rather than tokens. */
const NUMERIC_TERMS = new Set(["autonomy_stage", "activity_level"]);

/** Fails loudly rather than projecting a malformed model into SQL or prompts. */
export function validateSemanticModel(model = semanticModel) {
  const problems = [];
  const add = (message) => problems.push(message);

  if (model.version !== "2.0.0") add(`version must be 2.0.0, found ${model.version}`);
  if (!["review", "active"].includes(model.status)) add(`status must be review or active, found ${model.status}`);

  for (const name of Object.keys(model.vocabularies)) {
    if (!SQL_IDENT.test(name)) add(`vocabulary ${name} is not a usable SQL identifier`);
    let ids;
    try {
      ids = termIds(name);
    } catch (error) {
      add(error.message);
      continue;
    }
    if (ids.length === 0) add(`vocabulary ${name} is empty`);
    for (const id of ids) {
      // Both level scales use numeric ids; everything else must be a SQL-safe token.
      if (!NUMERIC_TERMS.has(name) && name !== "evidence_tier" && !SQL_IDENT.test(id)) {
        add(`term ${name}.${id} is not a usable SQL identifier`);
      }
      if (id === "other") add(`vocabulary ${name} still has an "other" bucket (rule:no-other-bucket)`);
      if (id.includes("'")) add(`term ${name}.${id} would break a SQL literal`);
    }
    if (new Set(ids).size !== ids.length) add(`vocabulary ${name} has duplicate terms`);
  }

  // event_kind is the vocabulary whose missing definitions caused the observed
  // drift, so it is held to a stricter shape than the rest.
  const shape = model.vocabularies.event_kind.term_shape ?? [];
  for (const id of termIds("event_kind")) {
    const body = term("event_kind", id);
    if (!body || typeof body !== "object") {
      add(`event_kind.${id} has no definition body`);
      continue;
    }
    for (const field of shape) {
      if (body[field] === undefined) add(`event_kind.${id} is missing ${field}`);
    }
  }

  for (const [id, body] of Object.entries(model.vocabularies.person_event_role.terms)) {
    const tier = body.implies_tier;
    if (!termIds("evidence_tier").includes(tier)) {
      add(`person_event_role.${id} implies unknown tier ${tier}`);
    }
  }

  // Each tier carries one cap per scale. They are NOT the same numbers - T2 caps
  // at 3 on the retired 0-4 stage scale and at 4 on the 0-5 level scale - and
  // only T3 agreeing at 2 in both is why the divergence went unnoticed while the
  // level caps lived in Python. Both are range-checked against their own scale.
  const levelIds = termIds("activity_level").map(Number);
  const topLevel = Math.max(...levelIds);
  for (const [id, body] of Object.entries(model.vocabularies.evidence_tier.terms)) {
    const stageCap = body.stage_cap;
    if (!Number.isInteger(stageCap) || stageCap < 0 || stageCap > 4) {
      add(`evidence_tier.${id} has an out-of-range stage_cap`);
    }
    const levelCap = body.level_cap;
    if (!Number.isInteger(levelCap) || levelCap < 0 || levelCap > topLevel) {
      add(`evidence_tier.${id} has an out-of-range level_cap (0-${topLevel})`);
    }
  }

  // The level scale is an ordered ladder: the ids ARE the values, and the judge is
  // shown them in this order, so a gap or a reorder silently changes every reading.
  const expectedLevels = levelIds.map((_, i) => i);
  if (levelIds.join() !== expectedLevels.join()) {
    add(`activity_level must be contiguous integers from 0, found ${levelIds.join(", ")}`);
  }
  for (const id of termIds("activity_level")) {
    const body = term("activity_level", id) ?? {};
    for (const field of ["label", "definition"]) {
      for (const language of ["en", "zh-CN"]) {
        if (!body[field]?.[language]) add(`activity_level.${id} is missing ${field}.${language}`);
      }
    }
  }
  const capped = model.vocabularies.activity_level.capped_by ?? {};
  if (capped.vocabulary !== "evidence_tier" || capped.field !== "level_cap") {
    add("activity_level must declare capped_by evidence_tier.level_cap (rule:tier-caps-level)");
  }

  for (const [kind, body] of Object.entries(model.node_kinds)) {
    if (body.layer === "type" && body.stateful) add(`node kind ${kind} is a type but declares state (rule:type-layer-has-no-state)`);
  }

  for (const [kind, body] of Object.entries(model.edge_kinds)) {
    for (const endpoint of [...(body.from ?? []), ...(body.to ?? [])]) {
      const known = endpoint in model.node_kinds || endpoint === "extracted_event";
      if (!known) add(`edge kind ${kind} points at unknown node kind ${endpoint}`);
    }
  }

  // rule:blocked-by-needs-source-task retired with the capability layer: gates
  // now attach to activities directly (activity_gate_edges) and no longer have
  // to reach a gate claim through some task's text.
  for (const gate of gates.gates) {
    if (!termIds("gate_type").includes(gate.gate_type)) add(`gate ${gate.id} has unknown gate_type ${gate.gate_type}`);
    if (gate.status === "reviewed" && gate.method !== "reviewed") {
      add(`gate ${gate.id} claims reviewed status without a reviewed method`);
    }
  }

  return problems;
}

/** `'a', 'b', 'c'` for embedding in a generated CHECK constraint. */
export function sqlValueList(name) {
  return termIds(name).map((id) => `'${id}'`).join(", ");
}
