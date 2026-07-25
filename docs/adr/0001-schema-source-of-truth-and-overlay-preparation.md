# ADR 0001 — Schema source-of-truth & overlay-driven preparation

- **Status:** Accepted
- **Date:** 2026-07-25
- **Deciders:** WimSuenens
- **Context specs:** #7 (schema source-of-truth & preparation strategy), #17 / #18–#20
  (execution). Monorepo layout — where `schemas/` sits and how it is git-ignored — is
  decided in #14; this ADR references that decision rather than restating it.

## Context

We generate two C#/TypeScript SDKs and an MCP server from the GS1 Belgium & Luxembourg
**My Product Manager v17** OpenAPI schemas. The vendor `download` spec contains one real
defect: the `limit` page-size query parameter is typed `type: number` even though its own
description reads `Format - int32.` and a sibling parameter in the same document is already
`integer`/`int32`. Fed raw to the generators, this leaks a `double?` (C#) / `number` (TS)
page size onto a public surface and into the MCP tool schema.

We must correct that one wart **without** losing provenance. Two other `type: number`
fields in the same download document (the measurement-unit and currency `value` fields)
are legitimately decimal and must be left alone. And a future v18 drop must be ingestable
without silently carrying a patch GS1 may have already fixed.

Options considered:

1. **Hand-edit the vendor file.** Rejected: destroys the clean `v17 → v18` diff against
   what GS1 actually shipped, and turns "keep the fix in sync across versions" into a
   fragile human-memory task.
2. **A patch script that mutates the schema imperatively.** Rejected: the intent of the
   change is buried in code; not self-documenting; still easy to carry silently.
3. **A declarative OpenAPI Overlay applied at build time.** Chosen (below).

## Decision

- **Keep pristine vendor originals byte-exact.** `schemas/<api>/<version>.yaml` (and the
  reference `.json`) stay exactly as GS1 delivered them. The build only ever reads them.
- **Two separate documents, never merged.** `upload` and `download` remain independent
  source-of-truth trees, one per downstream consumer. Merging is rejected.
- **Express corrections as a committed OpenAPI Overlay 1.0 document** at
  `schemas/<api>/<version>.overlay.yaml`, targeting nodes by JSONPath. The **download**
  overlay carries exactly one action: align the `limit` parameter schema to
  `type: integer`, `format: int32`. The **upload** overlay is empty (no defect in scope).
- **Emit a git-ignored effective spec** at `schemas/<api>/<version>.effective.yaml`
  (hidden by a `*.effective.yaml` glob). It is the only schema the generators read; it is
  a regenerable build artifact, never committed. (The git-ignore glob and the top-level
  `schemas/` location are #14's monorepo-layout decision.)
- **Make the build self-verifying (dead-patch guard).** Each overlay action records the
  expected pre-patch value in an `x-assert-before` extension; the build asserts the target
  still holds it before patching, and fails with a non-zero exit naming the action
  otherwise. This is what makes a v18 overlay seeded from v17 safe.
- **YAML is the canonical build input.** The overlay's JSONPath targets are expressed
  against the YAML original; the `.json` is retained as a delivered reference, not built
  from.

The build step is a Python helper under `scripts/`, run through the root `justfile`'s
`just gen` recipe (`uv`-managed environment). It is the repo's first test seam; its tests
assert the produced artifact and the build's failure behaviour, treating the overlay /
JSONPath / YAML libraries as vendor.

## Consequences

- **Positive:** provenance is intact (pristine originals give a clean vendor diff); the
  delta is isolated in one small, auditable overlay; the git-ignored effective sibling
  prevents a drifting second copy; the dead-patch guard keeps the delta honest across
  versions; the pipeline is uniform across APIs even when there is nothing to patch.
- **Negative / cost:** generation now has a mandatory pre-step (`just gen`) and a build
  dependency on `uv` + the overlay tooling; contributors must understand that the
  effective spec is generated, not edited.
- **Follow-on:** the CI aggregation of the dead-patch guard (`schema-assert` → `ci-gate`),
  branch protection, and the repo-wide README/CONTRIBUTING (including the
  "never hand-edit a schema" contributor rule) are owned by the #14 scaffold spec.

See the [glossary](../../CONTEXT.md) for the terms *pristine vendor original*, *overlay*,
*effective spec*, and *dead patch*, and the
[ingestion runbook](../schema-ingestion-runbook.md) for the version-uptake procedure.
