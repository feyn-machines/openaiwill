const str = { type: "string", minLength: 1 };
const nullable = (s) => ({ anyOf: [s, { type: "null" }] });
const en = (...values) => ({ enum: values });
const arr = (items) => ({ type: "array", items });
const obj = (properties, optional = []) => ({ type: "object", properties, required: Object.keys(properties).filter((k) => !optional.includes(k)), additionalProperties: false });
const date = { type: "string", format: "date-time" };
const url = { type: "string", format: "uri" };
const number = { type: "number" };
const score = nullable({ type: "number", minimum: 0, maximum: 100 });
const view = en("markets", "occupations");
const version = { type: "string", pattern: "^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$" };
const rating = nullable(obj({ value: nullable(number), n: nullable({ type: "integer", minimum: 0 }), suppress: { type: "boolean" } }));

export const rowSchemas = {
  nodes: obj({ id: str, kind: en("market_group", "market", "work", "occupation_group", "occupation"), label_zh_cn: nullable(str), label_en: str, origin: en("editorial_ai", "onet_projection"), translation_status: en("ai_translated", "pending", "source_original"), scope_status: en("starter_catalog", "defined", "source_missing_tasks"), scope_note: str }, ["scope_note"]),
  relations: obj({ id: str, view, parent_id: str, child_id: str, order: { type: "integer", minimum: 0 } }),
  weights: obj({ relation_id: str, value: { type: "number", minimum: 0, maximum: 1 }, method: en("ai_proposed", "equal_occupation_prior", "source_importance_normalized", "imputed_occupation_mean", "equal_no_reliable_ratings"), method_version: version, basis_value: nullable(number), explanation: str, status: en("draft", "reviewed") }),
  external_mappings: obj({ id: str, node_id: str, source_id: str, external_type: en("onet_occupation", "onet_task", "onet_activity", "onet_family", "isic_section"), external_id: str, relation: en("source_projection", "related", "broader", "narrower", "exact"), method: en("source_id", "ai_proposed", "reviewed"), status: en("source_reference", "candidate", "reviewed"), explanation: str }, ["explanation"]),
  metric_definitions: obj({ id: str, label_zh_cn: str, value_type: en("integer", "number", "boolean", "string", "enum"), unit: str, role: en("attention", "availability", "adoption", "performance", "cost", "human_involvement"), allowed_values: arr(str), minimum: nullable(number), maximum: nullable(number) }),
  events: obj({ id: str, title: str, summary: str, occurred_at: nullable(date), observed_at: date, source_urls: { ...arr(url), minItems: 1, uniqueItems: true }, topic_ids: { ...arr(str), minItems: 1, uniqueItems: true }, source_role: en("provider_claim", "adopter_report", "independent_test", "community_report", "official_record"), verification_status: en("unverified", "corroborated", "disputed", "retracted"), dedup_key: str, system_version: nullable(str) }, ["system_version"]),
  observations: obj({ id: str, event_id: str, metric_id: str, value: { type: ["string", "number", "boolean", "null"] }, observed_at: date, source_url: url, scope_note: nullable(str), missing_reason: nullable(str) }),
  progress_updates: obj({ id: str, node_id: str, view, previous_update_id: nullable(str), old_value: score, new_value: score, event_ids: { ...arr(str), minItems: 1, uniqueItems: true }, observation_ids: { ...arr(str), minItems: 1, uniqueItems: true }, method_id: str, method_version: version, reason: str, change_cause: en("new_evidence", "evidence_correction", "method_revision", "scope_revision", "weight_revision"), assessed_at: date }),
  progress: obj({ node_id: str, view, value: score, status: en("unassessed", "estimated", "aggregate"), as_of: nullable(date), update_id: nullable(str) }),
  sources: obj({ id: str, version: str, url, license: str, status: en("reference", "raw_not_integrated", "editorial_draft"), note: str }, ["note"]),
  reference_occupations: obj({ id: str, source_code: str, family_id: str, label_en: str, description_en: str, source_version: str, source_task_count: { type: "integer", minimum: 0 }, source_url: url }),
  reference_tasks: obj({ id: str, source_task_id: str, occupation_id: str, statement_en: str, task_type: nullable(str), incumbents_responding: nullable({ type: "integer", minimum: 0 }), importance: rating, relevance: rating, frequency: nullable({ type: "object", properties: Object.fromEntries([1, 2, 3, 4, 5, 6, 7].map((n) => [n, nullable(number)])), additionalProperties: false }), source_updated_month: str, domain_source: str, source_version: str, record_kind: str }),
  reference_activities: obj({ id: str, source_id: str, kind: en("GWA", "IWA", "DWA"), label_en: str, parent_id: nullable(str) }),
  reference_task_activity_links: obj({ task_id: str, activity_id: str, source_updated_month: str, domain_source: str }),
  reference_taxonomy_codes: obj({ id: str, source_code: str, kind: en("section", "division", "group", "class"), parent_id: nullable(str) }),
  coverage: obj({ isic_section: str, domain_ids: { ...arr(str), minItems: 1, uniqueItems: true }, coverage_note: str }),
};

export const dataSchema = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  $id: "https://openaiwill.com/schemas/platform/0.0.1/data.json",
  title: "openaiwill platform metadata 0.0.1",
  ...obj(Object.fromEntries(Object.entries(rowSchemas).map(([k, s]) => [k, arr(s)]))),
};
export const collections = Object.keys(rowSchemas);
