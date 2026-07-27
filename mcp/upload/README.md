# mcp/upload/

<!-- mcp-name: io.github.WimSuenens/gs1belu-mpm-upload -->

> [!IMPORTANT]
> **Unofficial.** This project is a community effort and is not affiliated with,
> endorsed by, or supported by GS1 in any way. "GS1" and "My Product Manager" are
> the property of their respective owners. Use at your own risk.

The **My Product Manager Upload** MCP server — a standalone Python package (FastMCP)
exposing only the provider-role half of the API. It is one of two independent
successors to the deprecated combined server (see
[`../combined/README.md`](../combined/README.md) for the migration guide); its sibling
is [`../download/`](../download/). A data-supplier integrator installs this package
alone and never has to configure or expose Download credentials/tools it has no
business holding — see issue
[#82](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/82).

It assembles its tools **at runtime** from the git-ignored
[effective spec](../../CONTEXT.md#effective-spec) under
[`schemas/upload/`](../../schemas/upload/) via `FastMCP.from_openapi()`. Unlike the
SDKs, this needs **no code-generation step**: `just gen` step 1 (the schema-prep
build) is the only prerequisite.

## The 2-tool provider-role surface

The Upload API is 2 operations (`upsert-tradeitem`, `get-tradeitem`), but the MCP
surface is deliberately **not** a 1:1 map — a raw `POST /tradeitems` tool would be
actively dangerous for an agent (see "Sharp edges" below):

| Tool | Origin | Behavior |
|---|---|---|
| `upsert_and_await_validation(trade_item)` | hand-written composite | `POST /tradeitems` -> poll `GET /tradeitems/{gtin}` until settled -> returns the **validation verdict** |
| `get_trade_item_by_gtin(gtin)` | generated (upload `get-tradeitem`), renamed via `mcp_names` | standalone single-item read |

The raw `POST /tradeitems` is excluded from `from_openapi()` via a `RouteMap` so the
fire-and-forget write (always `201`, never a verdict) never reaches the agent.

### Sharp edges this surface removes

- **The write is fire-and-forget by shape.** `POST /tradeitems` returns `201` with an
  empty body — no validation verdict. The true accept/reject signal only arrives by
  polling `GET /tradeitems/{gtin}` until `metaData.status` leaves `pendingValidation`
  (see `docs/research/gs1-api-facts.md` §5). A raw POST tool would let an agent report
  success it never actually confirmed.
- **Errors are opaque unless parsed.** Non-2xx bodies carry field-level signal
  (`validationResult` on 400, RFC-7807 `problemDetails` on 401/403/404) that a bare
  `raise_for_status()` throws away. Every tool surfaces these as a structured
  `ToolError` instead (see below).

## Auth — the Python leg of the two-layer design

The server's `httpx.AsyncClient` carries one `Gs1BeluAuth` (`httpx.Auth`), vendored
byte-identically from [`../shared/`](../shared/) (map #76 — the same class the
Download server uses, so a fix to this security-critical path is made once, not in two
hand-maintained copies that can drift):

- **OAuth2 client-credentials Bearer token** — fetched from the environment's token
  endpoint, cached in memory, and proactively refreshed on a skew margin (default 60s)
  before the token's runtime `expires_in` elapses. Concurrent callers coalesce onto a
  single fetch via double-checked locking.
- **`Ocp-Apim-Subscription-Key` header** — stamped on every request, **header only**;
  the spec's query-param alternative is never used, so the key never lands in a URL or
  log.

Credentials are single-tenant, loaded from environment variables, **one credential set
for this process** (never `GS1BELU_DOWNLOAD_*` — that's the sibling server's role):

| Variable | Required | Meaning |
|---|---|---|
| `GS1BELU_ENVIRONMENT` | yes | `uat` or `prod` — the only knob; it derives the API host, token host, and OAuth `audience` (trailing slash baked in). There is no raw base-URL setting anywhere. |
| `GS1BELU_API_VERSION` | no (default `v17`) | the contract version segment in the API path. |
| `GS1BELU_UPLOAD_CLIENT_ID` / `_CLIENT_SECRET` / `_SUBSCRIPTION_KEY` | yes | Upload API credential set. |

A `RateLimiter` (sliding window, 10 req/s), also vendored from `../shared/`, is
attached to the same client alongside the auth and structured-error hooks — this
process's own limiter, never shared with the Download server (#77).

## Sunset monitoring

GS1 can announce an API-version retirement in-band via the `Sunset` header (RFC
8594). `warn_on_sunset` (vendored from `../shared/`) is a response hook that logs a
`WARNING` through `logging.getLogger("gs1belu_mpm_upload._shared.sunset")` whenever a
response carries the header. It never alters, retries, or fails a request —
observation only.

## Quickstart

No clone, no build — the published wheel bundles the effective spec it needs at
runtime (see "Publishing" below). Point an MCP-capable client at
`uvx gs1belu-mpm-upload-mcp` with the documented env vars, e.g. in `.mcp.json`:

```json
{
  "mcpServers": {
    "gs1belu-mpm-upload": {
      "command": "uvx",
      "args": ["gs1belu-mpm-upload-mcp"],
      "env": {
        "GS1BELU_ENVIRONMENT": "uat",
        "GS1BELU_UPLOAD_CLIENT_ID": "...",
        "GS1BELU_UPLOAD_CLIENT_SECRET": "...",
        "GS1BELU_UPLOAD_SUBSCRIPTION_KEY": "..."
      }
    }
  }
}
```

### Running locally (for development)

Working in a checkout of this repo instead?

```sh
just gen                # builds the git-ignored effective specs (step 1 only needed)
export GS1BELU_ENVIRONMENT=uat
export GS1BELU_UPLOAD_CLIENT_ID=... GS1BELU_UPLOAD_CLIENT_SECRET=... GS1BELU_UPLOAD_SUBSCRIPTION_KEY=...
just run-mcp-upload      # launches the standalone Upload server over stdio
```

Or point an MCP-capable client at `uv run --project mcp/upload gs1belu-mpm-upload-mcp`
with the same environment variables set.

## Testing

`just test-mcp` drives `build_upload_server()` through FastMCP's **in-memory
`Client`**, with a fake `httpx` transport and a mocked token endpoint injected under
the server's `AsyncClient` — no network, no live GS1, no subprocess. See
[`tests/`](tests/):

- `test_tool_surface.py` — pins the exact 2-tool list; the raw POST is absent.
- `test_composite.py` — the settled verdict is returned once `metaData.status` leaves
  `pendingValidation`, polling stops immediately, and the bounded timeout is honored.
- `test_config.py` — loads only `GS1BELU_UPLOAD_*`; a stray `GS1BELU_DOWNLOAD_*` value
  is never read.
- `test_specs.py` — pins the packaged-resource spec-resolution path.

Auth/rate-limit/sunset/error-mapping behavior is verified **once**, directly against
`../shared/`'s own test suite — not duplicated here (#79's Testing Decisions).

## Layout

- `pyproject.toml` — `gs1belu-mpm-upload-mcp`, the `gs1belu-mpm-upload-mcp` console
  entry point, the custom build hook that vendors `../shared/` and bundles the upload
  effective spec.
- `hatch_build.py` — build hook: copies `../shared/src/_shared/` into
  `src/gs1belu_mpm_upload/_shared/` (map #76) and `../../schemas/upload/v17.effective.yaml`
  into the packaged `_specs/` resource home. Never hand-edit either — they're
  git-ignored build outputs this hook (re)populates.
- `src/gs1belu_mpm_upload/`
  - `config.py` — env-var credential loading for this role only, built on the shared
    `parse_environment()` + `CredentialSet.from_env()` seam.
  - `composite.py` — `upsert_and_await_validation` as a plain, independently testable
    async function.
  - `server.py` — assembles the server (`build_upload_server()`): RouteMap exclusion,
    `mcp_names` renaming, the composite tool.
  - `specs.py` — locates and parses the upload effective spec.
  - `cli.py` — the `gs1belu-mpm-upload-mcp` console entry point.
  - `_shared/` — vendored copy of [`../shared/src/_shared/`](../shared/src/_shared/);
    git-ignored, regenerated by the build hook.
- `tests/` — the in-memory `Client` + fake-transport suite described above.

## Publishing

Release-and-publish machinery — `server.json`, the `mcp-name` README marker above,
`publish-mcp.yml`'s PyPI + MCP-registry OIDC publish (parameterized across all three
`mcp*` packages, #82), and the release-please `mcp-upload` component/tag
(`mcp-upload-v*`) — is configured per
[#53](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/53) and
[#82](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/82). See
[`docs/release-execution-checklist.md`](../../docs/release-execution-checklist.md) for
the human-run, prerequisite-gated steps below the first live publish.
