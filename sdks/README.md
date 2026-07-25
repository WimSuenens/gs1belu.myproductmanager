# sdks/

Toolchain root for the two generated **My Product Manager** SDKs. Both are produced
by the pinned Kiota CLI from the git-ignored [effective specs](../CONTEXT.md#effective-spec)
under [`schemas/`](../schemas/) — one client per document, never merged.

## Layout

- `kiota.version` — the pinned Kiota CLI version, installed identically locally and
  in CI (`dotnet tool install --global Microsoft.OpenApi.Kiota --version $(cat sdks/kiota.version)`).
- `kiota-clients.json` — declares the four clients (Upload + Download x C# + TypeScript)
  as data: which effective spec, which language, which class/namespace, which output
  directory. `scripts/generate_clients.py` reads it and drives `kiota generate`.
  **Not** a native Kiota `workspace.json` — see [Why not a native Kiota workspace](#why-not-a-native-kiota-workspace) below.
- `dotnet/` — the C# SDK: `Gs1Belu.MyProductManager.sln` + a root `Directory.Build.props`
  (shared `netstandard2.0;net8.0` multi-target, the `Kiota.Bundle` >= 2.0.0 pin), and two
  projects, `Gs1Belu.MyProductManager.Upload` / `.Download` (NuGet id = root namespace =
  project name), each wrapping its own committed `generated/` client. No shared `-core`
  project — each owns its own Kiota-duplicated models.
- `typescript/` — the TypeScript SDK: an ESM-only npm workspace (`"type": "module"`,
  `NodeNext`) declaring two packages, `@gs1belu/mpm-upload` / `@gs1belu/mpm-download`,
  each with a committed `generated/` client and its own `tsconfig.generated.json` —
  a quarantined, relaxed compiler config (kept *outside* `generated/` itself, since
  Kiota's `--clean-output` wipes that directory on every regeneration) that contains
  the Experimental-Kiota `@ts-ignore` noise. The package's own `tsconfig.json` is the
  strict config a future hand-written surface will use; it references the generated
  project via TS project references.

Generated `generated/` trees, `kiota-lock.json` files, `kiota-clients.json`, and
`kiota.version` are all committed. **Never hand-edit anything under `generated/`** —
corrections flow through the schema's `*.overlay.yaml` (see the [schema-prep ADR](../docs/adr/0001-schema-source-of-truth-and-overlay-preparation.md))
or a `kiota-clients.json` change, then `just gen` regenerates and you commit the diff.
This is what makes the `regen-sync` CI check trustworthy: it re-derives `generated/`
from committed inputs and fails on any divergence, so a stray hand-edit is caught,
not silently carried forward.

## The hand-written ergonomic surface

On top of each committed `generated/` client, a **strict hand-written surface** (#36) adds
authentication and a thin set of ergonomic helpers — the layer the `generated/` quarantine was
built to protect. It lives beside `generated/` (e.g. `dotnet/Gs1Belu.MyProductManager.Upload/*.cs`
outside the `generated/` subtree, `typescript/packages/mpm-upload/src/`) and is never touched by
regeneration.

- **Public entry point** — `Gs1BeluUploadClient` / `Gs1BeluDownloadClient` per package. The public
  constructor takes only `environment` (`uat`/`prod`) + an `apiVersion` (default `v17`) + a
  **credential set** (`{ clientId, clientSecret, subscriptionKey }`, one per API — Upload and
  Download credentials are never shared). The base URL, OAuth token host, and OAuth `audience` are
  all *derived* from `environment`; there is no public `baseUrl` knob.
- **Access-token provider** — a hand-written `IAccessTokenProvider` (C#) / `AccessTokenProvider`
  (TS) plugged into Kiota's `BaseBearerTokenAuthenticationProvider`. It caches the Bearer token in
  memory, refreshes it proactively on a skew margin before the runtime `expires_in` elapses, and
  coalesces concurrent callers onto a single in-flight fetch. A pipeline handler/middleware stamps
  the static `Ocp-Apim-Subscription-Key` header separately — Kiota's request adapter accepts only
  one `IAuthenticationProvider`, so the two credentials live in different layers.
- **Ergonomic helpers** — `uploadAndAwaitValidation` (Upload: submits, then polls `GET {gtin}`
  until `metaData.status` leaves `pendingValidation`, bounded by a timeout), `listAllTradeItems`
  (Download: an iterator that auto-follows HAL `_links.next`), and `assertValidGtin`/`assertValidGln`
  (pure format checks restoring the `pattern` constraints Kiota drops from generated models).
- **Testability** sits *below* the public constructor: tests build the Kiota request adapter
  directly against a fake HTTP transport and a mocked token endpoint — a seam consumers never see.
  See each package's `*.Tests` project (C#) / `src/__tests__` (TypeScript).

Run `just test-sdks` to build and run both languages' test suites locally (separate from `just
test`, which is the schema-prep suite `schema-assert` runs — that CI job has no dotnet/node
toolchain installed).

## Generation and build

Both run from the repo root; see [`CONTRIBUTING.md`](../CONTRIBUTING.md).

- `just gen` — step 1 builds the effective specs (schema-prep), step 2 runs the pinned
  Kiota CLI to (re)generate the four clients into their `generated/` subtrees.
- `just build` — `dotnet build` over the C# solution, then `npm ci` + `tsc -b` (via
  each package's `build` script) over the TypeScript workspace.

## Why not a native Kiota workspace

The SDK generation spec ([#31](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/31))
originally called for a native Kiota `workspace.json` (declaring all four clients,
managed by `kiota workspace`/`kiota client` subcommands) as the generation seam. The
pinned CLI (`kiota.version`) ships **no such subcommands** — only `kiota generate`
and `kiota update` against explicit flags; `kiota workspace`/`kiota client` are not
present in this release. `kiota-clients.json` + `scripts/generate_clients.py`
substitute for that: the four clients are still declared as data in one file (so
adding a fifth client is a one-line edit, not a new script), but the file is
hand-authored and consumed by our own script, not parsed by Kiota itself.
