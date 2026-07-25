# GS1 BeLu MPM — build front door.
#
# `just gen` is the single entry point that turns the pristine vendor schemas
# into generator-ready artifacts. Today it runs step 1 only — the schema-prep
# effective-spec build. Downstream steps (Kiota SDKs, FastMCP server) are added
# by later specs as further steps of this same recipe.

# Show available recipes.
default:
    @just --list

# Step 1 — schema prep: apply the committed overlays to the pristine vendor
# originals and (re)generate the git-ignored effective specs.
gen:
    uv run --project scripts python scripts/build_effective_spec.py

# Front-door placeholder: the per-dir toolchains (dotnet / tsc / uv) land with the
# SDK and MCP specs (map #1 / #8, #11, #12). Until then this recipe is a documented
# no-op so the front-door index is complete and `just --list` shows it beside
# `gen`/`test`. Each later spec appends its own step here, delegating to the native
# command in its `sdks/` or `mcp/` root.

# Build the artifacts (SDKs, MCP server) from the generated specs.
build:
    @echo "just build — no artifacts to build yet."
    @echo "  The dotnet / typescript SDKs (sdks/) and the MCP server (mcp/) land with"
    @echo "  their specs and will append their build steps to this recipe."

# Run the schema-prep test suite.
test:
    uv run --project scripts pytest scripts/tests -q
