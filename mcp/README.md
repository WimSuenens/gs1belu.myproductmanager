# mcp/

<!-- mcp-name: io.github.wimsuenens/gs1belu-mpm -->

> [!IMPORTANT]
> **Unofficial.** This project is a community effort and is not affiliated with,
> endorsed by, or supported by GS1 in any way. "GS1" and "My Product Manager" are
> the property of their respective owners. Use at your own risk.

The **My Product Manager** MCP server — a standalone Python package (FastMCP,
PrefectHQ v3.x) that stands apart from [`sdks/`](../sdks/) because it is a different
language and, per map [#1](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/1),
independent of the SDKs.

It assembles its tools **at runtime** from the same git-ignored
[effective specs](../CONTEXT.md#effective-spec) under [`schemas/`](../schemas/) that
Kiota reads for the SDKs, via `FastMCP.from_openapi()` — one sub-server per document,
mounted on a parent (server composition, never a merged document). Unlike the SDKs,
this needs **no code-generation step**: `just gen` step 1 (the schema-prep build) is
the only prerequisite.

## The 3-tool composite-only surface

The full API is 3 operations (`upsert-tradeitem`, `get-tradeitem`, `get-tradeitems`),
but the MCP surface is deliberately **not** a 1:1 map — a naive tool-per-operation
mapping is actively dangerous for an agent (see the "Sharp edges" section below):

| Tool | Origin | Behavior |
|---|---|---|
| `upsert_and_await_validation(trade_item)` | hand-written composite | `POST /tradeitems` -> poll `GET /tradeitems/{gtin}` until settled -> returns the **validation verdict** |
| `get_trade_item_by_gtin(gtin)` | generated (upload `get-tradeitem`), renamed via `mcp_names` | standalone single-item read |
| `search_trade_items(filters..., cursor?, limit?)` | hand-written | **single page + `nextCursor`** — never auto-paginates |

The raw `POST /tradeitems` is excluded from `from_openapi()` via a `RouteMap` so the
fire-and-forget write (always `201`, never a verdict) never reaches the agent. The raw
`GET /tradeitems` (search) is excluded too: its HAL envelope (`_links`/`_embedded`) is
replaced by `search_trade_items`'s flat `{tradeItems, nextCursor}` shape rather than a
literal rename, so the pagination token is a field an agent can read directly instead
of something it has to parse out of a URL.

### Sharp edges this surface removes

- **The write is fire-and-forget by shape.** `POST /tradeitems` returns `201` with an
  empty body — no validation verdict. The true accept/reject signal only arrives by
  polling `GET /tradeitems/{gtin}` until `metaData.status` leaves `pendingValidation`
  (see `docs/research/gs1-api-facts.md` §5). A raw POST tool would let an agent report
  success it never actually confirmed.
- **The list read can flood the context window.** A broad Download filter can match up
  to 1000 items server-side (§4). `search_trade_items` never auto-follows HAL's
  `_links.next` — it returns one bounded page plus an opaque `nextCursor` the agent
  can choose to follow.
- **Errors are opaque unless parsed.** Non-2xx bodies carry field-level signal
  (`validationResult` on 400, RFC-7807 `problemDetails` on 401/403/404) that a bare
  `raise_for_status()` throws away. Every tool surfaces these as a structured
  `ToolError` instead (see below).

## Auth — the Python leg of the two-layer design

Each sub-server's `httpx.AsyncClient` carries one `Gs1BeluAuth` (`httpx.Auth`)
implementing both credential layers this project's SDKs already ship in C#/TS:

- **OAuth2 client-credentials Bearer token** — fetched from the environment's token
  endpoint, cached in memory, and proactively refreshed on a skew margin (default 60s)
  before the token's runtime `expires_in` elapses — never a hardcoded 12h/24h figure,
  since the GS1 manuals disagree on which of those it is. Concurrent callers coalesce
  onto a single fetch via double-checked locking.
- **`Ocp-Apim-Subscription-Key` header** — stamped on every request, **header only**;
  the spec's query-param alternative is never used, so the key never lands in a URL or
  log.

Credentials are single-tenant, loaded from environment variables, **one full
credential set per sub-server** (Upload and Download are never assumed to share a
key — see `docs/research/gs1-api-facts.md` §1/§6):

| Variable | Required | Meaning |
|---|---|---|
| `GS1BELU_ENVIRONMENT` | yes | `uat` or `prod` — the only knob; it derives the API host, token host, and OAuth `audience` (trailing slash baked in). There is no raw base-URL setting anywhere. |
| `GS1BELU_API_VERSION` | no (default `v17`) | the contract version segment in the API path. |
| `GS1BELU_UPLOAD_CLIENT_ID` / `_CLIENT_SECRET` / `_SUBSCRIPTION_KEY` | yes | Upload API credential set. |
| `GS1BELU_DOWNLOAD_CLIENT_ID` / `_CLIENT_SECRET` / `_SUBSCRIPTION_KEY` | yes | Download API credential set. |

A `RateLimiter` (sliding window, 10 req/s) is attached to the same client alongside the
auth and structured-error hooks, so every request — generated tools and the
hand-written composite/search tools alike — stays under the confirmed rate cap
(`docs/research/gs1-api-facts.md` §3).

## Running locally

```sh
just gen                # builds the git-ignored effective specs (step 1 only needed)
export GS1BELU_ENVIRONMENT=uat
export GS1BELU_UPLOAD_CLIENT_ID=... GS1BELU_UPLOAD_CLIENT_SECRET=... GS1BELU_UPLOAD_SUBSCRIPTION_KEY=...
export GS1BELU_DOWNLOAD_CLIENT_ID=... GS1BELU_DOWNLOAD_CLIENT_SECRET=... GS1BELU_DOWNLOAD_SUBSCRIPTION_KEY=...
just run-mcp             # launches the composed server over stdio
```

Or point an MCP-capable client (Claude Desktop, an agent framework, etc.) at
`uv run --project mcp gs1belu-mpm-mcp` with the same environment variables set.

### Trying it interactively against live UAT

`just test-mcp` (below) never touches the network — it's a fake-transport suite. To
call the three tools for real against GS1's UAT environment, use the
[MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```sh
just gen                                              # if not already built
cp mcp/.env.example mcp/.env                          # fill in real UAT credentials
npx @modelcontextprotocol/inspector uv run --project mcp --env-file mcp/.env gs1belu-mpm-mcp
```

This opens a browser UI listing `upsert_and_await_validation`, `get_trade_item_by_gtin`,
and `search_trade_items`, with a form to call each one and inspect the raw response —
useful for confirming real-world behavior the mocked suite only asserts against canned
fixtures (e.g. that polling actually settles out of `pendingValidation`).

## Testing

`just test-mcp` drives the assembled parent server through FastMCP's **in-memory
`Client`**, with a fake `httpx` transport and a mocked token endpoint injected under
each sub-server's `AsyncClient` — no network, no live GS1, no subprocess (the direct
Python analog of the SDKs' fake-transport seam). See `mcp/tests/`:

- `test_tool_surface.py` — pins the exact 3-tool list; the raw POST/search operations
  are absent.
- `test_auth.py` — both auth headers present on outgoing requests, subscription key
  never in a URL, a burst of concurrent calls triggers exactly one token fetch, a
  cached token is reused until the skew margin then re-fetched.
- `test_composite.py` — the settled verdict is returned once `metaData.status` leaves
  `pendingValidation`, polling stops immediately, and the bounded timeout is honored.
- `test_search.py` — one page + `nextCursor`, no auto-pagination, a follow-up call
  with the cursor advances.
- `test_errors.py` — canned 400/401/403/404 responses assert the exact structured
  `ToolError` shapes.

## Layout

- `pyproject.toml` — `gs1belu-mpm-mcp`, `fastmcp`/`httpx`/`PyYAML` deps, `pytest`/
  `pytest-asyncio` dev group, `gs1belu-mpm-mcp` console entry point.
- `src/gs1belu_mpm_mcp/`
  - `environment.py` / `config.py` — host/audience derivation and env-var credential
    loading (no raw base-URL knob).
  - `auth.py` / `ratelimit.py` / `errors.py` — the two-layer `httpx.Auth`, the sliding-
    window rate limiter, and the structured non-2xx -> `ToolError` mapping.
  - `clients.py` — wires the three into one authenticated `httpx.AsyncClient` per
    sub-server; `transport` is the one testability seam, never exposed publicly.
  - `composite.py` / `search.py` — the two hand-written tools as plain, independently
    testable async functions.
  - `server.py` — assembles the parent server (`build_server()`): RouteMap exclusion,
    `mcp_names` renaming, mounting.
  - `specs.py` — locates and parses the git-ignored effective specs.
  - `cli.py` — the `gs1belu-mpm-mcp` console entry point.
- `tests/` — the in-memory `Client` + fake-transport suite described above.

## Publishing

Release-and-publish machinery — `server.json`, the `mcp-name` README marker above,
`publish-mcp.yml`'s PyPI + MCP-registry OIDC publish, and the release-please version
bump — is configured per [#53](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/53).
That spec stops **below the first live publish**: registering the PyPI pending
publisher, the GitHub App, and the MCP registry namespace are human-run,
prerequisite-gated steps, not something this repo's CI performs on its own.
