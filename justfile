# GS1 BeLu MPM — build front door.
#
# `just gen` is the single entry point that turns the pristine vendor schemas
# into generator-ready artifacts. Step 1 is the schema-prep effective-spec build;
# step 2 runs the pinned Kiota CLI against those effective specs to (re)generate
# the four SDK clients. The MCP server (mcp/) reads the same effective specs at
# runtime via FastMCP's `from_openapi()` — no generation step of its own, so it
# has no step here; it only needs `just gen`'s step 1 to have run first.

# Show available recipes.
default:
    @just --list

# Step 1 alone: apply the committed overlays to the pristine vendor originals and
# (re)generate the git-ignored effective specs. Broken out of `gen` so the MCP CI job
# can build just the specs it needs without installing dotnet/Kiota for step 2.
gen-schemas:
    uv run --project scripts python scripts/build_effective_spec.py

# Turn pristine vendor schemas into generator-ready clients.
#   Step 1 — schema prep (see `gen-schemas`).
#   Step 2 — Kiota generation: regenerate the four SDK clients (Upload +
#            Download x C# + TypeScript) from those effective specs into their
#            packages' quarantined generated/ subtrees. Never hand-edit
#            generated/ output — fix the schema overlay or a Kiota config
#            change, then regenerate.
gen: gen-schemas
    uv run --project scripts python scripts/generate_clients.py

# Build the SDKs from the generated clients.
#   dotnet build — the C# solution (sdks/dotnet/), multi-targeted netstandard2.0;net8.0.
#   tsc          — the TypeScript workspace (sdks/typescript/), ESM-only, per package.
# The MCP server (mcp/) needs no build step: FastMCP assembles its tools at import time.
build:
    dotnet build sdks/dotnet/Gs1Belu.MyProductManager.sln
    npm --prefix sdks/typescript ci
    npm --prefix sdks/typescript run build

# Run the schema-prep test suite.
test:
    uv run --project scripts pytest scripts/tests -q

# Assert the release/publish configuration is internally consistent (#53) — the
# tag-prefix contract binding release-please's components to the three publish
# workflows, config<->manifest parity, version-source wiring, and registry
# metadata presence. Reused verbatim by the `release-assert` CI job so CI and
# local can never disagree about what "the release config is consistent" means.
release-assert:
    uv run --project scripts pytest scripts/tests/test_release_assert.py -q

# Run the SDK auth + ergonomic-surface test suites (C# + TypeScript). Kept separate from `test`
# (schema-assert's CI job only installs uv/just, not dotnet/node) rather than folded into it.
test-sdks:
    dotnet test sdks/dotnet/Gs1Belu.MyProductManager.sln
    npm --prefix sdks/typescript ci
    npm --prefix sdks/typescript run build
    npm --prefix sdks/typescript run test

# Run the MCP server's test suite: the assembled server driven through FastMCP's
# in-memory Client against a fake httpx transport (no network, no live GS1). Needs the
# git-ignored effective specs from `just gen` step 1 to exist first.
test-mcp:
    uv run --project mcp pytest mcp/tests -q

# Launch the MCP server locally over stdio. Needs `just gen` to have run first and the
# GS1BELU_* credential env vars set (see mcp/README.md) — there is no live-network smoke
# test in CI, this is for local/manual use.
run-mcp:
    uv run --project mcp gs1belu-mpm-mcp
