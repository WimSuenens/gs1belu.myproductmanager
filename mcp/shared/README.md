# mcp/shared/

Dev-only Python package holding the OAuth / rate-limit / sunset / structured-error
code shared by [`../upload/`](../upload/) and [`../download/`](../download/) (map
[#76](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/76), part of
[#82](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/82)'s split of the
former combined server). **Never published** — this is a `uv` workspace member only,
not a `[project]` release-please tracks.

## Why vendored, not published

The combined server this replaced already carried ~400 lines of hand-written,
security-critical auth/rate-limit/sunset/error code. Duplicating it across two
packages would mean two hand-maintained copies that can drift; publishing a third
"core" PyPI package would mean a consumer of either server transitively depends on an
extra package they never asked for, and a fourth thing to version. Instead:

- `src/_shared/` is real, tested Python source, checked in here.
- Each of `../upload/`'s and `../download/`'s own `hatch_build.py` **copies this
  directory byte-identically** into its own package at build time (`src/gs1belu_mpm_upload/_shared/`
  / `src/gs1belu_mpm_download/_shared/`) — collision-proof, cannot drift, reuses the
  same vendoring technique the repo already established for bundling effective specs
  into the MCP wheel (`hatch_build.py`, commit `43cf320`).
- The vendored copy is git-ignored inside each server's own package; never hand-edit
  it there — fix it here and rebuild.

A fix to, say, the OAuth token-refresh skew margin is made once, in `src/_shared/auth.py`,
and lands in both servers' next build.

## What's here

- `src/_shared/environment.py` — API/token host derivation from an `Environment`
  (`uat`/`prod`), plus `parse_environment()`: the safety-critical
  `GS1BELU_ENVIRONMENT` → OAuth-`audience` parse, single-sourced so neither server can
  drift on which host it talks to.
- `src/_shared/config.py` — the `CredentialSet` shape (`client_id`/`client_secret`/`subscription_key`)
  and its `from_env(source, prefix)` loader. *Which* prefix (`GS1BELU_UPLOAD_*` vs
  `GS1BELU_DOWNLOAD_*`) is each server's own `config.py`'s call — see
  [`../upload/src/gs1belu_mpm_upload/config.py`](../upload/src/gs1belu_mpm_upload/config.py) /
  [`../download/src/gs1belu_mpm_download/config.py`](../download/src/gs1belu_mpm_download/config.py).
- `src/_shared/auth.py` — `Gs1BeluAuth`, the two-layer `httpx.Auth` (Bearer token +
  subscription-key header).
- `src/_shared/ratelimit.py` — `RateLimiter`, a sliding-window pacer for the API's
  10 req/s cap. Each server process gets its own instance — never shared across the
  two servers.
- `src/_shared/sunset.py` — `warn_on_sunset`, the `Sunset` (RFC 8594) response-header
  observer.
- `src/_shared/errors.py` — `raise_structured_error`, the non-2xx -> structured
  `ToolError` mapping.
- `src/_shared/clients.py` — `build_upstream_client()`, wiring the above four into one
  authenticated `httpx.AsyncClient`.

## Testing

Each module above is tested **once, here** — directly, not through a FastMCP server —
rather than duplicated per server (#82's Testing Decisions). See [`tests/`](tests/):
`test_environment.py`, `test_auth.py`, `test_errors.py`, `test_sunset.py`. Run via
`just test-mcp` (part of the full four-package MCP suite) or standalone:

```sh
uv run --project mcp/shared pytest mcp/shared/tests -q
```
