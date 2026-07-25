# Contributing

Thanks for helping out. This repo generates three artifacts (two SDKs + an MCP
server) from a single set of vendor OpenAPI schemas. A few rules keep that
generation honest and the provenance clean — please read the schema-editing rule
below before touching anything under `schemas/`.

Terminology (*pristine vendor original*, *overlay*, *effective spec*, *dead patch*)
is defined once in [`CONTEXT.md`](CONTEXT.md); this document uses those terms exactly.

## Toolchain prerequisites

| Tool | Used for | Notes |
|---|---|---|
| [`just`](https://github.com/casey/just) | Task front door (`gen` / `build` / `test`) | 1.x |
| [`uv`](https://docs.astral.sh/uv/) | Runs the Python schema-prep + MCP toolchains | Manages its own Python; no separate install needed |
| [.NET SDK](https://dotnet.microsoft.com/download) | Builds/tests the C# SDK | 8.x+ _(needed once `sdks/dotnet/` lands)_ |
| [Node.js](https://nodejs.org/) | Builds/tests the TypeScript SDK | LTS _(needed once `sdks/typescript/` lands)_ |
| Pinned [Kiota](https://learn.microsoft.com/openapi/kiota/) CLI | Regenerates the SDK clients | Version is pinned by the SDK workspace (`kiota-lock.json`), so every contributor and CI generate byte-identical output. Lands with the SDK spec. |

Only `just` + `uv` are required for the work that exists today (schema prep). The
.NET / Node / Kiota tools become prerequisites as those roots are populated.

## `just` command reference

`just` is the single front door — run these from the repo root:

| Command | What it does |
|---|---|
| `just gen` | Apply the committed overlays to the pristine vendor originals and (re)generate the git-ignored effective specs. Later grows the Kiota SDK regeneration step. |
| `just build` | Build the artifacts (SDKs, MCP server). A documented placeholder today; each SDK/MCP spec appends its native build step. |
| `just test` | Run the schema-prep test suite (`scripts/tests`) — asserts the overlays still apply cleanly and the effective specs are correct. This is the exact seam CI's `schema-assert` job runs. |

## The schema-editing rule (never break this)

**Never hand-edit a pristine vendor original or generated code.** The vendor files
(`schemas/<api>/v17.yaml` / `.json`) are kept byte-exact so the `vN → vN+1` diff and
the provenance stay truthful.

To correct a defect in a vendor schema:

1. Add or amend an action in the API's `schemas/<api>/v17.overlay.yaml`. Give each
   action an `x-assert-before` recording the value the target currently holds, so the
   build fails loudly (a **dead patch**) if a future vendor version fixes the defect
   upstream instead of silently carrying a no-op.
2. Run `just gen` to regenerate the effective spec (a git-ignored build artifact —
   don't commit it).
3. Run `just test` and commit the overlay change.

Generated SDK client code follows the same rule: fix the schema via its overlay and
regenerate — never patch the generated output by hand. (A future `regen-sync` CI job
will re-run generation and fail on any drift.)

## PR flow

The repo is PR-only; nothing lands on `main` except a CI-green PR (the maintainer
included — direct pushes are blocked). The path:

1. Branch off `main`.
2. Open a PR. Fill in the PR template (declare which artifacts you touched).
3. Wait for **`ci-gate`** to go green. `ci-gate` is the single required check; it
   aggregates the path-filtered jobs (today just `schema-assert`) and passes when
   each needed job **succeeded or was skipped**.
4. Make sure your branch is up to date with `main` (required before merge).
5. Self-merge. Add a release entry per the release process if the change is
   user-facing (the release tooling is owned by a later spec; this document will
   point at it once it exists).

## Branch protection (recorded so it is reproducible)

`main` is protected to match the solo-maintainer model. The settings are applied
via `gh api` (not just clicked once) so they can be re-applied after a fork or if the
config is ever lost. Applying them requires a **repo-admin token**; on GitHub Free,
branch protection also requires the repository to be public.

Exact call — re-run it to (re)apply the protection:

```bash
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  repos/WimSuenens/gs1belu.myproductmanager/branches/main/protection \
  --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": ["ci-gate"] },
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

What each field realises (from the layout decision, §4):

- `required_status_checks.strict: true` — branches must be up to date with `main`
  before merge, so `ci-gate` is always evaluated against the latest `main`.
- `required_status_checks.contexts: ["ci-gate"]` — **exactly one** required check.
  Individual jobs are path-filtered and may be skipped; only the `ci-gate` aggregator
  is required, which avoids the required-check-plus-path-filter deadlock.
- `enforce_admins: true` — the maintainer cannot bypass the gate with a direct push.
- `required_pull_request_reviews.required_approving_review_count: 0` — honest solo
  model: every change goes through a PR, but no fake self-approval. Flip to `1` if a
  second maintainer ever joins.
- `required_linear_history: true` — the published-from branch stays linear.
- `allow_force_pushes: false`, `allow_deletions: false` — `main` can never be
  force-pushed or deleted under a release.

Read the current protection back with:

```bash
gh api repos/WimSuenens/gs1belu.myproductmanager/branches/main/protection
```
