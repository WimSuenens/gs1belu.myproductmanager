# GS1 BeLu MPM — build front door.
#
# `just gen` is the single entry point that turns the pristine vendor schemas
# into generator-ready artifacts. Step 1 is the schema-prep effective-spec build;
# step 2 runs the pinned Kiota CLI against those effective specs to (re)generate
# the four SDK clients. The FastMCP server generation step lands with its own
# spec as a further step of this same recipe.

# Show available recipes.
default:
    @just --list

# Turn pristine vendor schemas into generator-ready clients.
#   Step 1 — schema prep: apply the committed overlays to the pristine vendor
#            originals and (re)generate the git-ignored effective specs.
#   Step 2 — Kiota generation: regenerate the four SDK clients (Upload +
#            Download x C# + TypeScript) from those effective specs into their
#            packages' quarantined generated/ subtrees. Never hand-edit
#            generated/ output — fix the schema overlay or a Kiota config
#            change, then regenerate.
gen:
    uv run --project scripts python scripts/build_effective_spec.py
    uv run --project scripts python scripts/generate_clients.py

# Build the SDKs from the generated clients.
#   dotnet build — the C# solution (sdks/dotnet/), multi-targeted netstandard2.0;net8.0.
#   tsc          — the TypeScript workspace (sdks/typescript/), ESM-only, per package.
# The MCP server (mcp/) lands its own build step with its spec.
build:
    dotnet build sdks/dotnet/Gs1Belu.MyProductManager.sln
    npm --prefix sdks/typescript ci
    npm --prefix sdks/typescript run build

# Run the schema-prep test suite.
test:
    uv run --project scripts pytest scripts/tests -q
