import semanticLabelsJson from "@/content/semantic-labels.json";
import type { Language } from "@/lib/i18n";

/**
 * Display names for the controlled vocabularies, read from the published
 * semantic labels file. A term that is not in the vocabulary is never given an
 * invented name: the caller is told so and prints the raw value instead, which
 * is how a superseded vocabulary stays visible rather than being smoothed over.
 */
export type SemanticTerm = {
  en?: string;
  "zh-CN"?: string;
  definition?: { en?: string; "zh-CN"?: string } | null;
  stage_cap?: number;
  can_demonstrate_capability?: boolean;
  implies_tier?: string;
};

type Vocabulary = {
  label: { en: string; "zh-CN": string };
  terms: Record<string, SemanticTerm>;
};

type SemanticLabels = {
  semantic_version: string;
  generated_from: string;
  vocabularies: Record<string, Vocabulary>;
};

const labels = semanticLabelsJson as unknown as SemanticLabels;

export const semanticVersion = labels.semantic_version;

export type VocabularyName =
  | "event_kind"
  | "evidence_tier"
  | "autonomy_stage"
  | "person_event_role"
  | "org_affiliation_role"
  | "gate_type"
  | "relation_method"
  | "relation_status"
  | "lifecycle"
  | "judge"
  | "judgment_task";

function vocabulary(name: VocabularyName): Vocabulary | undefined {
  return labels.vocabularies[name];
}

/** The vocabulary's own name, e.g. "Evidence tier" / "证据层级". */
export function vocabularyLabel(name: VocabularyName, language: Language): string {
  return vocabulary(name)?.label[language] ?? name;
}

/** Every term of a vocabulary, in published order. */
export function vocabularyTerms(name: VocabularyName): [string, SemanticTerm][] {
  return Object.entries(vocabulary(name)?.terms ?? {});
}

export function semanticTerm(name: VocabularyName, key: string | null | undefined): SemanticTerm | null {
  if (!key) return null;
  return vocabulary(name)?.terms[key] ?? null;
}

/** The display name, or `null` when the value is not part of this vocabulary. */
export function termName(
  name: VocabularyName,
  key: string | null | undefined,
  language: Language,
): string | null {
  const term = semanticTerm(name, key);
  if (!term) return null;
  return term[language] ?? term.en ?? key ?? null;
}

/** The display name, falling back to the raw stored value verbatim. */
export function termNameOrRaw(
  name: VocabularyName,
  key: string | null | undefined,
  language: Language,
): string {
  return termName(name, key, language) ?? key ?? "";
}

/**
 * A term's definition plus the language it is actually written in. Several
 * vocabularies publish Chinese-only definitions in semantic model 2.0.0, so the
 * page marks the original language instead of pretending a translation exists.
 */
export function termDefinition(
  name: VocabularyName,
  key: string | null | undefined,
  language: Language,
): { text: string; language: Language } | null {
  const definition = semanticTerm(name, key)?.definition;
  if (!definition) return null;
  const preferred = definition[language];
  if (preferred) return { text: preferred, language };
  const other: Language = language === "en" ? "zh-CN" : "en";
  const fallback = definition[other];
  return fallback ? { text: fallback, language: other } : null;
}
