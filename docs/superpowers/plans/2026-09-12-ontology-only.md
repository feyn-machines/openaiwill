# Ontology-only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver an immutable ontology-only package containing the full existing catalog, typed relations and reference mappings.

**Architecture:** A read-only projection consumes the verified legacy package. An independent JSON Schema and semantic validator define ontology data; a separate release module seals and verifies it.

**Tech Stack:** Node.js, JSON Schema 2020-12, existing AJV, node:test.

**Spec:** `docs/superpowers/specs/2026-09-12-ontology-only-design.md`

## Global Constraints

- Preserve all source concept and relation IDs, sealed platform data and unrelated working changes.
- No Compose, PG, application integration, metrics, progress or weights implementation.
- Complete catalog, not examples; no unsupported new definitions or equivalence claims.
- Work in the current shared directory because the input catalog and prior authorized implementation are still uncommitted here. Do not commit unrelated files.

## Task 1: Ontology contract and projection

Files: create `scripts/lib/ontology-schema.mjs`, `scripts/lib/ontology-data.mjs`, `scripts/tests/ontology-data.test.mjs`.

Interfaces: schema module exports `ontologyModel`, `ontologySchema`, `ontologyCollections`; data module exports `projectOntology(legacyData)` and `validateOntology(data)`. Validator returns at least `{counts}` and throws on invalid data.

- [x] Write small literal-fixture tests that fail when identity is rewritten, runtime/statistical fields leak, invalid kind/view edges are accepted, references are missing or duplicated, source mappings are falsely verified, or a valid shared work is rejected.
- [x] Run `node --test scripts/tests/ontology-data.test.mjs` and observe missing-feature failures.
- [x] Implement the projection, strict schemas and semantic checks. Model relation definitions provide the endpoint/view rules used by validation.
- [x] Run focused tests and project the complete legacy fixture as a read-only check.

## Task 2: Sealed artifact, entry points and whole verification

Files: create `scripts/lib/ontology-release.mjs`, `scripts/build-ontology.mjs`, `scripts/check-ontology.mjs`, `scripts/tests/ontology-release.test.mjs`, `datasets/ontology/README.md`, `datasets/ontology/VERSIONING.md`; add ontology-only commands/gates to `package.json` and CI; update ontology-related guidance only.

Interfaces: `sealOntology({data, outputDir, derivedFrom, attachments})` and `verifyOntology(dir)`; verifier returns validated data, counts, manifest and manifest hash. Derived provenance has package `platform`, version `0.0.1` and verified source manifest hash.

- [x] Write literal-fixture release tests for valid round-trip, refusing overwrite, payload tampering, unexpected files and manifest row/count mismatches; run the tests before implementing the writer.
- [x] Write a lock-protected temporary-directory builder, strict file inventory/hash/schema verification and atomic final rename. Copy no arbitrary files from the old bundle.
- [x] Build read-only from `datasets/platform/releases/v0.0.1/`, after its existing verifier succeeds; output the new ontology version, model/schema, full JSONL and readable catalogs without weights or runtime values.
- [x] Run `pnpm ontology:test`, `pnpm ontology:check`, review the complete generated counts and ID preservation, then run `pnpm check` and resolve failures attributable to this work.
- [x] Review the full implementation, record concrete verification and open the new ontology entry point. Leave the old data and other subsystems unchanged.

## Rulings and progress

- Ruling: the standalone ontology uses `1.0.0` with explicit derivation from platform `0.0.1`; this signals the changed contract without overwriting the mixed snapshot.
- Ruling: documentation is supplemented by actual JSON/JSONL and executable validators, not treated as the implementation.

## Completion evidence

- Full ontology sealed at `datasets/ontology/releases/v1.0.0/`; 18 payload files, 29,174,431 bytes.
- 20,796 concepts; 20,733 typed relations; 19,924 external mappings; all original identities retained.
- 19,894 concepts have existing source/scope definitions; 902 remain explicitly null.
- Manifest SHA-256: `f89f583fd5c8ec76abddf978284631cdb5e65ce0ce2f9ba36c42707dd734df76`.
- Final payload hashes match the independently reviewed candidate.
- 86 ontology tests passed; full `pnpm check` passed, including existing platform tests/integrity, security, design, lint, typecheck and build.
- Independent read-only review found no blocking issue. No Docker/PG or runtime model implementation was changed.
