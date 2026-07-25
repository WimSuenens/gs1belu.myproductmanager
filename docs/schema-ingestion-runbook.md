# Runbook — ingesting a new GS1 MPM API version

How to take up a new **My Product Manager** API version (e.g. v18) so that the SDKs and
MCP server can be regenerated from it. This is a **manual drop-in**: automating the
download of vendor specs from GS1 is out of scope — only the procedure is documented here.

For the vocabulary used below (*pristine vendor original*, *overlay*, *effective spec*,
*dead patch*), see [`CONTEXT.md`](../CONTEXT.md). For the rationale, see
[ADR 0001](adr/0001-schema-source-of-truth-and-overlay-preparation.md).

## Layout recap

```
schemas/
  download/
    v17.yaml            # pristine vendor original (byte-exact) — build INPUT
    v17.json            # pristine vendor original (reference only)
    v17.overlay.yaml    # committed corrections (OpenAPI Overlay 1.0)
    v17.effective.yaml  # generated, git-ignored — build OUTPUT (what generators read)
  upload/
    v17.yaml
    v17.json
    v17.overlay.yaml    # empty: upload has no defect in scope
    v17.effective.yaml  # generated, git-ignored
```

## Procedure

Assume the new version is **v18** and the previous is **v17**.

### 1. Drop the new pristine originals beside the previous version

Place the files GS1 delivered, **byte-exact and unmodified**, next to the existing ones —
never overwrite v17:

```
schemas/download/v18.yaml
schemas/download/v18.json
schemas/upload/v18.yaml
schemas/upload/v18.json
```

Because nothing is overwritten, the vendor history stays intact.

### 2. Diff v18 against v17 to see exactly what GS1 changed

```sh
diff schemas/download/v17.yaml schemas/download/v18.yaml
diff schemas/upload/v17.yaml   schemas/upload/v18.yaml
```

This clean diff is the whole reason the originals are kept pristine. Read it to learn:
what GS1 added/removed/renamed, and — crucially — **whether any defect the v17 overlay
patched has been fixed upstream**.

### 3. Seed the per-version overlay from the previous version

Copy the prior overlay so you start from the known set of corrections rather than from
scratch:

```sh
cp schemas/download/v17.overlay.yaml schemas/download/v18.overlay.yaml  # then adjust
cp schemas/upload/v17.overlay.yaml   schemas/upload/v18.overlay.yaml    # then adjust
```

Update each action's `target`
JSONPath if the node moved, and keep `x-assert-before` set to the value the node holds in
**v18**.

### 4. Regenerate the effective specs and let the build verify the overlay

```sh
just gen
```

The build applies each overlay action to the pristine original and, per action, asserts
the target still holds its `x-assert-before` value:

- **Build passes** → every seeded patch still applies; the effective specs are ready for
  the downstream generators.
- **Build fails with a dead-patch error** → the named action no longer matches (e.g. GS1
  fixed `limit` in v18). This is expected and healthy: **drop the dead action** from the
  v18 overlay, then re-run `just gen`. Do **not** work around the assertion — a dead patch
  means the correction is no longer needed.

Run `just test` to exercise the schema-prep suite against the new inputs.

### 5. Point the downstream generators at the v18 effective specs

Updating the Kiota / FastMCP generation to consume `v18.effective.yaml` (and any
parallel-majors publishing) is owned by the downstream SDK/MCP specs, not this runbook.

## Out of scope

- **Parallel-majors publishing policy** — whether v17 and v18 SDKs ship as concurrent
  majors is owned by the SDK-architecture and versioning decisions (#8 / #13), not here.
- **The contributor-facing "never hand-edit a schema" rule** — owned by the repo-wide
  CONTRIBUTING in the #14 monorepo-scaffold spec. Correct a schema via its overlay, never
  by editing a pristine original or an effective spec.
- **Automating vendor-spec download from GS1** — ingestion is a manual drop-in.
