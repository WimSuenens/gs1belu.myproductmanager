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

# Run the schema-prep test suite.
test:
    uv run --project scripts pytest scripts/tests -q
