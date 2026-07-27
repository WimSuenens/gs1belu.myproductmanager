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

# Run the MCP servers' test suites (#82's split): shared/'s own unit tests, then each
# server's assembled-server suite driven through FastMCP's in-memory Client against a
# fake httpx transport (no network, no live GS1). Separate `uv run` invocations, not
# one combined pytest call, because same-named test modules across mcp/*/tests/ (e.g.
# test_config.py) collide under a single pytest collection root. Needs the git-ignored
# effective specs from `just gen` step 1 to exist first.
test-mcp:
    uv run --project mcp/shared pytest mcp/shared/tests -q
    uv run --project mcp/upload pytest mcp/upload/tests -q
    uv run --project mcp/download pytest mcp/download/tests -q
    uv run --project mcp/combined pytest mcp/combined/tests -q

# Launch the Upload MCP server locally over stdio. Needs `just gen` to have run first
# and GS1BELU_ENVIRONMENT + GS1BELU_UPLOAD_* set (see mcp/upload/README.md) — there is
# no live-network smoke test in CI, this is for local/manual use.
run-mcp-upload:
    uv run --project mcp/upload gs1belu-mpm-upload-mcp

# Launch the Download MCP server locally over stdio. Needs GS1BELU_ENVIRONMENT +
# GS1BELU_DOWNLOAD_* set (see mcp/download/README.md).
run-mcp-download:
    uv run --project mcp/download gs1belu-mpm-download-mcp

# Launch the deprecated combined MCP server locally over stdio (mcp/combined/) — kept
# only until its final 0.4.0 deprecation release ships (#82). New integrations should
# use run-mcp-upload / run-mcp-download instead.
run-mcp-combined:
    uv run --project mcp/combined gs1belu-mpm-mcp
