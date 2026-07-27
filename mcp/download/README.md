# mcp/download/

<!-- mcp-name: io.github.WimSuenens/gs1belu-mpm-download -->

> [!IMPORTANT]
> **Unofficial.** This project is a community effort and is not affiliated with,
> endorsed by, or supported by GS1 in any way. "GS1" and "My Product Manager" are
> the property of their respective owners. Use at your own risk.

The **My Product Manager Download** MCP server — a standalone Python package (FastMCP)
exposing only the recipient-role half of the API. It is one of two independent
successors to the deprecated combined server (see
[`../combined/README.md`](../combined/README.md) for the migration guide); its sibling
is [`../upload/`](../upload/). A data-recipient integrator installs this package alone
and its agent never sees a destructive write tool (`upsert_and_await_validation`) in
its tool list — see issue
[#82](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/82).

Unlike its Upload sibling, this server builds **no tools from an OpenAPI spec** — the
raw `GET /tradeitems` is entirely replaced by the hand-written `search_trade_items`
below, so there is nothing for `FastMCP.from_openapi()` to generate here (#75). It is
a plain `FastMCP` server with one tool.

## The 1-tool recipient-role surface

| Tool | Origin | Behavior |
|---|---|---|
| `search_trade_items(filters..., cursor?, limit?)` | hand-written | **single page + `nextCursor`** — never auto-paginates |

The raw `GET /tradeitems` HAL envelope (`_links`/`_embedded`) is replaced by
`search_trade_items`'s flat `{tradeItems, nextCursor}` shape rather than a literal
rename, so the pagination token is a field an agent can read directly instead of
something it has to parse out of a URL.

### The sharp edge this surface removes

**The list read can flood the context window.** A broad filter can match up to 1000
items server-side (`docs/research/gs1-api-facts.md` §4). `search_trade_items` never
auto-follows HAL's `_links.next` — it returns one bounded page plus an opaque
`nextCursor` the agent can choose to follow. Non-2xx responses (401/403/404) also
surface as a structured `ToolError` (`{title, status, detail}`) instead of an opaque
`raise_for_status()` string.

## Auth — the Python leg of the two-layer design

The server's `httpx.AsyncClient` carries one `Gs1BeluAuth` (`httpx.Auth`), vendored
byte-identically from [`../shared/`](../shared/) (map #76 — the same class the
Upload server uses, so a fix to this security-critical path is made once, not in two
hand-maintained copies that can drift):

- **OAuth2 client-credentials Bearer token** — fetched from the environment's token
  endpoint, cached in memory, and proactively refreshed on a skew margin (default 60s)
  before the token's runtime `expires_in` elapses. Concurrent callers coalesce onto a
  single fetch via double-checked locking.
- **`Ocp-Apim-Subscription-Key` header** — stamped on every request, **header only**;
  the spec's query-param alternative is never used, so the key never lands in a URL or
  log.

Credentials are single-tenant, loaded from environment variables, **one credential set
for this process** (never `GS1BELU_UPLOAD_*` — that's the sibling server's role):

| Variable | Required | Meaning |
|---|---|---|
| `GS1BELU_ENVIRONMENT` | yes | `uat` or `prod` — the only knob; it derives the API host, token host, and OAuth `audience` (trailing slash baked in). There is no raw base-URL setting anywhere. |
| `GS1BELU_API_VERSION` | no (default `v17`) | the contract version segment in the API path. |
| `GS1BELU_DOWNLOAD_CLIENT_ID` / `_CLIENT_SECRET` / `_SUBSCRIPTION_KEY` | yes | Download API credential set. |

A `RateLimiter` (sliding window, 10 req/s), also vendored from `../shared/`, is
attached to the same client alongside the auth and structured-error hooks — this
process's own limiter, never shared with the Upload server (#77).

## Sunset monitoring

GS1 can announce an API-version retirement in-band via the `Sunset` header (RFC
8594) — the Download manual documents monitoring it as best practice.
`warn_on_sunset` (vendored from `../shared/`) is a response hook that logs a `WARNING`
through `logging.getLogger("gs1belu_mpm_download._shared.sunset")` whenever a response
carries the header. It never alters, retries, or fails a request — observation only.

## Quickstart

No clone, no build. Point an MCP-capable client at `uvx gs1belu-mpm-download-mcp`
with the documented env vars, e.g. in `.mcp.json`:

```json
{
  "mcpServers": {
    "gs1belu-mpm-download": {
      "command": "uvx",
      "args": ["gs1belu-mpm-download-mcp"],
      "env": {
        "GS1BELU_ENVIRONMENT": "uat",
        "GS1BELU_DOWNLOAD_CLIENT_ID": "...",
        "GS1BELU_DOWNLOAD_CLIENT_SECRET": "...",
        "GS1BELU_DOWNLOAD_SUBSCRIPTION_KEY": "..."
      }
    }
  }
}
```

### Running locally (for development)

```sh
export GS1BELU_ENVIRONMENT=uat
export GS1BELU_DOWNLOAD_CLIENT_ID=... GS1BELU_DOWNLOAD_CLIENT_SECRET=... GS1BELU_DOWNLOAD_SUBSCRIPTION_KEY=...
just run-mcp-download     # launches the standalone Download server over stdio
```

Or point an MCP-capable client at
`uv run --project mcp/download gs1belu-mpm-download-mcp` with the same environment
variables set.

## Testing

`just test-mcp` drives `build_download_server()` through FastMCP's **in-memory
`Client`**, with a fake `httpx` transport and a mocked token endpoint injected under
the server's `AsyncClient` — no network, no live GS1, no subprocess. See
[`tests/`](tests/):

- `test_tool_surface.py` — pins the exact 1-tool list; the raw `get-tradeitems` and
  any Upload-role tool are absent.
- `test_search.py` — one page + `nextCursor`, no auto-pagination, a follow-up call
  with the cursor advances.
- `test_config.py` — loads only `GS1BELU_DOWNLOAD_*`; a stray `GS1BELU_UPLOAD_*` value
  is never read.

Auth/rate-limit/sunset/error-mapping behavior is verified **once**, directly against
`../shared/`'s own test suite — not duplicated here (#79's Testing Decisions).

## Layout

- `pyproject.toml` — `gs1belu-mpm-download-mcp`, the `gs1belu-mpm-download-mcp`
  console entry point, the custom build hook that vendors `../shared/`. No spec
  bundling (#75) — this package's wheel carries no schema artifact.
- `hatch_build.py` — build hook: copies `../shared/src/_shared/` into
  `src/gs1belu_mpm_download/_shared/` (map #76). Never hand-edit it — it's a
  git-ignored build output this hook (re)populates.
- `src/gs1belu_mpm_download/`
  - `config.py` — env-var credential loading for this role only, built on the shared
    `parse_environment()` + `CredentialSet.from_env()` seam.
  - `search.py` — `search_trade_items` as a plain, independently testable async
    function.
  - `server.py` — assembles the server (`build_download_server()`): a plain `FastMCP`
    carrying the one hand-written tool.
  - `cli.py` — the `gs1belu-mpm-download-mcp` console entry point.
  - `_shared/` — vendored copy of [`../shared/src/_shared/`](../shared/src/_shared/);
    git-ignored, regenerated by the build hook.
- `tests/` — the in-memory `Client` + fake-transport suite described above.

## Publishing

Release-and-publish machinery — `server.json`, the `mcp-name` README marker above,
`publish-mcp.yml`'s PyPI + MCP-registry OIDC publish (parameterized across all three
`mcp*` packages, #82), and the release-please `mcp-download` component/tag
(`mcp-download-v*`) — is configured per
[#53](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/53) and
[#82](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/82). See
[`docs/release-execution-checklist.md`](../../docs/release-execution-checklist.md) for
the human-run, prerequisite-gated steps below the first live publish.
