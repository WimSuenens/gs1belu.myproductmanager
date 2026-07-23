# MCP Landscape: Spec-Driven Server Framework & Distribution (2026)

Research for a spec-driven MCP server that derives its tools directly from the GS1 My Product
Manager OpenAPI docs (operations `get-tradeitems`, `upsert-tradeitem`, `get-tradeitem`), proxying
to the upstream API with an Azure APIM `Ocp-Apim-Subscription-Key` header. Primary sources only;
each claim is cited.

---

## 1. Framework

### 1.1 Python: FastMCP's OpenAPI import

**Existence & maturity.** `FastMCP.from_openapi()` exists and is a mature, current feature.
FastMCP is published on PyPI as `fastmcp`, currently at **v3.4.4** (107 releases to date), with a
summary of "The fast, Pythonic way to build MCP servers and clients."
[[PyPI: fastmcp]](https://pypi.org/project/fastmcp/) The `from_openapi()` capability was
introduced in FastMCP 2.0.0 and has received continuous enhancements through 2.5.0, 2.8.0 and
into the 3.x line (features are version-badged in the docs, e.g. `New in version: 3.0.0`).
[[gofastmcp.com/integrations/openapi]](https://gofastmcp.com/integrations/openapi)
[[gofastmcp.com/getting-started/welcome]](https://gofastmcp.com/getting-started/welcome)

**Lineage — important for provenance.** FastMCP 1.0 was incorporated into the **official MCP
Python SDK** in 2024 (it lives on today as `mcp.server.fastmcp` in
`modelcontextprotocol/python-sdk`). The standalone FastMCP project (PrefectHQ, gofastmcp.com)
continued to evolve independently past 1.0 and is where OpenAPI-import, proxying, and
composition features live — none of that is in the plain official SDK. Per FastMCP's own docs,
the standalone project is "downloaded a million times a day," and "some version of FastMCP powers
70% of MCP servers across all languages."
[[gofastmcp.com/getting-started/welcome]](https://gofastmcp.com/getting-started/welcome) FastMCP
is built on top of the official low-level SDK, so dropping down to the low-level API for
tricky cases remains possible.

**Multiple specs in one server.** `from_openapi()` itself takes exactly one OpenAPI document per
call — the docs' examples are all single-spec. There is **no native multi-spec parameter**.
[[gofastmcp.com/integrations/openapi]](https://gofastmcp.com/integrations/openapi) The documented
(and maintainer-observed) pattern for combining specs is **server composition**: build one
`FastMCP.from_openapi()` instance per spec, then combine them either via `mount()` (live,
dynamic delegation — a gateway pattern) or `import_server()` (static, one-time copy with
prefixing). A GitHub discussion shows a user manually pulling tools from a second
OpenAPI-derived server via `get_tools()` and re-adding them with `add_tool()`, calling it "a
little silly but it works"; no maintainer endorsed that specific hack, and by Feb 2026 the
original author's own guidance had shifted toward **not** wholesale-importing every endpoint from
multiple specs, instead recommending selectively hand-writing a few decorated tools when prompts
must span multiple APIs (due to lack of clean dependency/liveness management across
mounted sub-servers). [[GitHub: jlowin/fastmcp discussion #980]](https://github.com/jlowin/fastmcp/discussions/980)
For this project (two operations spanning what appears to be one GS1 API surface, likely one or
two OpenAPI docs — Upload + Download), the `mount`/`import_server` composition pattern is
sufficient and is a first-class, documented feature, not a hack.

**Tool naming.** Tools are named from the OpenAPI **`operationId`** field (behavior finalized
v2.5.0+): FastMCP takes the text before the first double-underscore (`__`) in the operationId,
slugifies it, caps it at 56 characters, and appends numeric suffixes to deduplicate collisions.
Custom names can override this via an `mcp_names: dict[operationId, name]` argument to
`from_openapi()`. [[gofastmcp.com/integrations/openapi]](https://gofastmcp.com/integrations/openapi)
This maps cleanly onto the target operations `get-tradeitems`, `upsert-tradeitem`,
`get-tradeitem` — assuming those strings are the literal `operationId` values in the schema, tool
names would derive automatically without needing `mcp_names` overrides.

**Parameter mapping.**
- *Query parameters*: only non-empty values are included; `None` and empty strings are filtered
  out before the request is sent.
- *Path parameters*: required ones are validated (missing → error); `None` values are filtered.
- *Array parameters*: query arrays honor the OpenAPI `explode` setting; path arrays are
  comma-joined.
- *Header parameters*: automatically stringified and attached to the outgoing HTTP request.
- *Request body*: mapped into the tool's structured input schema.
[[gofastmcp.com/integrations/openapi]](https://gofastmcp.com/integrations/openapi)

**Upstream auth / custom header injection.** Auth is configured once, at the transport level, on
the `httpx.AsyncClient` passed into `from_openapi()` — not per-tool. Example pattern from the
docs:

```python
api_client = httpx.AsyncClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
)
mcp = FastMCP.from_openapi(openapi_spec=spec, client=api_client)
```

The same mechanism injects **any** static header, so setting
`headers={"Ocp-Apim-Subscription-Key": "<key>"}` on the shared `httpx.AsyncClient` is the
documented way to attach the Azure APIM subscription key to every proxied call.
[[gofastmcp.com/integrations/openapi]](https://gofastmcp.com/integrations/openapi)

**Route-mapping / customization.**
- *Default behavior*: every OpenAPI operation becomes an MCP **Tool** by default.
- *`RouteMap` objects* (v2.0.0+): match routes by HTTP method, regex path pattern, and/or
  OpenAPI tags, and assign each match an MCP component type — `TOOL`, `RESOURCE`,
  `RESOURCE_TEMPLATE`, or `EXCLUDE`.
- *`MCPType.EXCLUDE`*: drops sensitive/internal routes from the generated server entirely.
- *`mcp_names`* (v2.5.0+): operationId → custom tool name overrides (see above).
- *Tags* (v2.8.0+): `mcp_tags` for RouteMap-level tags, a global `tags` parameter, and automatic
  passthrough of OpenAPI tags into component metadata.
- *`route_map_fn`* (v2.5.0+): a custom callable for mapping logic beyond what `RouteMap` covers.
- *`mcp_component_fn`* (v2.5.0+): post-creation in-place modification of generated components.
[[gofastmcp.com/integrations/openapi]](https://gofastmcp.com/integrations/openapi)

**Stated caveat (from the docs themselves).** FastMCP's own documentation warns: *"LLMs achieve
significantly better performance with well-designed and curated MCP servers than with
auto-converted OpenAPI servers."* Auto-generation is positioned as good for **bootstrapping and
prototyping**, not as a drop-in substitute for a hand-curated MCP surface mirroring the API 1:1.
[[gofastmcp.com/integrations/openapi]](https://gofastmcp.com/integrations/openapi) For a
3-operation surface this is a minor concern (little to curate), but worth flagging: the
`route_map_fn` / `mcp_component_fn` hooks exist precisely to add curation (better descriptions,
renamed params, filtered routes) on top of the raw auto-import without abandoning spec-driven
generation.

### 1.2 TypeScript path

**Official SDK (`modelcontextprotocol/typescript-sdk`).** The official TypeScript SDK's README
contains **no mention of OpenAPI integration, spec-driven code generation, operationId-based tool
naming, or automatic parameter extraction from an API spec.** Its documented surface is manual:
`server.registerTool()`, Standard Schema validation (Zod/Valibot/ArkType), runtime-specific
middleware, and example servers. OpenAPI-to-MCP is **absent from the official SDK** and is left
entirely to third-party tooling.
[[GitHub: modelcontextprotocol/typescript-sdk]](https://github.com/modelcontextprotocol/typescript-sdk)

**Third-party TypeScript OpenAPI→MCP generators** (none official/maintained by the MCP org):
- **`openapi-mcp-generator`** (npm) — code generator (not a runtime import), latest v3.1.4 as of
  research date; supports OpenAPI 3.0+, generates a full typed TS project with Zod validation,
  proxies to the REST API, supports API key/Bearer/Basic/OAuth2 auth, and multiple transports
  (stdio, SSE via Hono, StreamableHTTP).
- **`mcp-from-openapi`** (npm) — advertises "production-ready" TS output with validation and
  structured errors, ~80%+ test coverage claimed.
- **`@taskade/mcp-openapi-codegen`** — generates inspectable/committable TS rather than a live
  runtime import; includes response normalizers.
[[WebSearch: TypeScript OpenAPI to MCP server generator npm package 2026]](https://www.npmjs.com/package/openapi-mcp-generator)

**Key architectural difference vs. FastMCP:** these TS tools are **codegen** tools — they emit a
TypeScript project you commit and maintain, not a live `from_openapi()`-style runtime call that
re-reads the spec on every start. That is a materially different "spec-driven" story: with
FastMCP the OpenAPI doc *is* the source of truth at runtime; with the TS generators, the OpenAPI
doc produces a one-time source snapshot that then drifts from the spec unless regenerated and
recommitted. None of the surveyed TS tools are published or endorsed by
`github.com/modelcontextprotocol`, unlike FastMCP's SDK-adjacent status.

**Verdict for this project's "independent of any hand-written SDK" requirement:** Python/FastMCP
satisfies it directly (spec is read at runtime, no generated/committed code layer). The
TypeScript options available today would reintroduce a generated-and-maintained code layer,
working against the "no hand-written SDK" goal even though the generation step is automated.

---

## 2. Distribution

"Publishing an MCP server" in 2026 spans five largely orthogonal mechanisms; most real-world
servers combine two or three of them (e.g., npm/PyPI package + registry listing).

### 2.1 Official MCP Registry (`registry.modelcontextprotocol.io` / `github.com/modelcontextprotocol/registry`)

**What it is.** A centralized **metadata** directory — described in the FAQ ecosystem as an "app
store for MCP servers" for client-side discovery. **The registry hosts metadata only, never
artifacts.** [[modelcontextprotocol/registry docs/modelcontextprotocol-io/quickstart.mdx]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)

**Maturity.** Launched in preview Sept 8, 2025; entered **API freeze (v0.1)** Oct 24, 2025 (API
stable, no breaking changes for ≥1 month). As of the quickstart docs it is still explicitly
labeled **"currently in preview. Breaking changes or data resets may occur before general
availability."** [[modelcontextprotocol/registry quickstart.mdx]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)

**Pre-publication requirement — the artifact must already exist elsewhere.** Because the
registry stores only metadata, the workflow is strictly: **publish the package to npm/PyPI/
Docker/NuGet/Cargo first, then register it.** The quickstart states this explicitly for the
npm walkthrough: *"The MCP Registry only hosts metadata, not artifacts, so we must publish the
package to npm before publishing the server to the MCP Registry."*
[[modelcontextprotocol/registry quickstart.mdx]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)

**Ownership verification, per package type** (required by `official-registry-requirements.md`):
- **npm**: add an `mcpName` field to `package.json` *before* the first `npm publish` (adding it
  later forces a version bump just to fix metadata). The value must match the claimed registry
  namespace (e.g., must start with `io.github.<user>/` for GitHub-authenticated namespaces).
- **PyPI / NuGet**: add an `mcp-name: <server-name>` line (plain text or an HTML comment, so it
  can be hidden from rendered display) into the package **README**, since PyPI serves the README
  as the package description; the registry fetches
  `https://pypi.org/pypi/<package>/json` and checks the description text for that marker.
[[modelcontextprotocol/registry docs/reference/server-json/official-registry-requirements.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md)
[[quickstart.mdx]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)

**Namespace authentication (separate from package ownership).** Publishers authenticate as
themselves via GitHub OAuth (interactive), GitHub OIDC (CI/CD), or DNS/HTTP domain-ownership
verification. Publishing under `io.github.<user>/...` requires GitHub auth as that user;
publishing under a custom domain namespace (e.g. `com.example/...`) requires proving ownership of
`example.com`. [[modelcontextprotocol/registry official-registry-requirements.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md)

**Restricted registry base URLs (official registry only accepts these):**
npm → `registry.npmjs.org` only; PyPI → `pypi.org` only; NuGet → `api.nuget.org/v3/index.json`;
Cargo → `crates.io`; OCI/Docker → Docker Hub, GHCR, Quay.io, `*.pkg.dev`, `*.azurecr.io`,
`mcr.microsoft.com`; MCPB → GitHub Releases / GitLab Releases only. Private registries and
mirrors are explicitly disallowed.
[[official-registry-requirements.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md)

**`server.json` schema essentials.**
Required top level: `$schema`, `name` (reverse-DNS, e.g. `io.github.wimsuenens/gs1belu-mcp`),
`version`. Optional: `description`, `title`, `websiteUrl`, `repository`, `packages[]`,
`remotes[]`, `_meta`. Each `packages[]` entry requires `registryType` (`npm` | `pypi` | `cargo` |
`nuget` | `oci` | `mcpb`), `identifier`, `version`, `transport` (`stdio` | `streamable-http` |
`sse`); optional fields include `registryBaseUrl`, `runtimeHint` (`npx`/`uvx`/`dnx`),
`packageArguments`, `environmentVariables`, `runtimeArguments` (OCI), `fileSha256` (MCPB).
`_meta` on the official registry is restricted to the
`io.modelcontextprotocol.registry/publisher-provided` key only (4KB limit); other keys are
silently dropped. [[generic-server-json.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/generic-server-json.md)
[[official-registry-requirements.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md)

**Publishing mechanics.** CLI tool `mcp-publisher` (Go binary, installable via curl/Homebrew or
built from source with `make publisher`). Workflow: `mcp-publisher init` (scaffolds
`server.json` from the project) → edit → `mcp-publisher login` (GitHub OAuth/OIDC or DNS/HTTP) →
`mcp-publisher publish`. GitHub Actions-based auto-publish (OIDC, no stored secrets) is
documented separately (`github-actions.mdx`) for CI-driven releases.
[[quickstart.mdx]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)

### 2.2 PyPI or npm package (`uvx`/`npx`-launchable)

Standard language-registry distribution: `pip install`/`uvx <pkg>` or `npm install`/`npx <pkg>`.
This is the artifact tier the MCP Registry's `packages[]` entries point at — it is **required**,
not optional, if you want a registry listing with a runnable package rather than only a remote
URL entry. `runtimeHint: uvx` or `npx` in `server.json` tells clients how to launch it without a
prior manual install. For a Python/FastMCP server this is the natural, lowest-friction path:
`uvx gs1belu-mcp` (hypothetical) launches directly from PyPI with no separate install step for the
end user (assuming `uv`/`uvx` is present). This pairs directly with §2.1's PyPI ownership
verification (`mcp-name` marker in the README).

### 2.3 Docker image

Registry-recognized OCI sources: Docker Hub, GHCR, Quay.io, Google Artifact Registry, Azure
Container Registry, Microsoft Container Registry (`official-registry-requirements.md`, above).
Works equally for Python or TypeScript servers since it packages the whole runtime; heavier
distribution unit than a language package but sidesteps "does the user have `uv`/Node installed"
entirely, and is a natural fit if the server also needs to run as a long-lived
`streamable-http`/`sse` service (e.g., behind the org's own gateway) rather than being
`stdio`-launched per client. `transport` in `server.json` can be `streamable-http`/`sse` for this
mode, with `runtimeArguments` for container-specific flags.
[[generic-server-json.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/generic-server-json.md)

### 2.4 mcpb / DXT bundle (Desktop Extensions)

Open-sourced by Anthropic; repo moved to `github.com/modelcontextprotocol/mcpb` (a fork/successor
of `anthropics/mcpb`, itself the renamed DXT spec). An MCPB bundle is a **zip archive** containing
the full local server plus a `manifest.json`, enabling one-click install into desktop MCP hosts
(Claude for macOS/Windows and other compatible apps) without any package-manager step for the
end user. [[GitHub: modelcontextprotocol/mcpb README]](https://github.com/modelcontextprotocol/mcpb/blob/main/README.md)

Three runtime packaging strategies:
- **Node.js (recommended by the spec)** — bundle `node_modules` directly; since Node ships
  built into Claude for macOS/Windows, these bundles work with **zero additional runtime
  install** for the user. This is the mcpb spec's explicit sweet spot.
- **Python** — either (a) UV runtime mode (v0.4+): ship `pyproject.toml`, host manages the
  Python env automatically, or (b) traditional: vendor packages into `server/lib/` or bundle a
  full `server/venv/`.
- **Binary** — static-linked executables.
[[mcpb README]](https://github.com/modelcontextprotocol/mcpb/blob/main/README.md)

**Explicit limitation relevant to this project:** the spec states Python bundling **"cannot
portably bundle compiled dependencies (e.g., pydantic, which the MCP Python SDK requires)"** —
i.e., a naive vendored-`server/lib` Python MCPB bundle is fragile precisely because FastMCP/MCP
Python SDK depend on pydantic (a compiled/binary wheel dependency). The UV-runtime mode sidesteps
this by deferring to `uv` to resolve platform-correct wheels at install time, at the cost of
requiring the host to have (or fetch) `uv`. [[mcpb README]](https://github.com/modelcontextprotocol/mcpb/blob/main/README.md)
Only GitHub Releases and GitLab Releases are accepted as MCPB sources by the official registry
(§2.1). mcpb is a **desktop-install** distribution channel, independent of npm/PyPI — it does not
require prior publication there.

### 2.5 Hosted (FastMCP Cloud / "Prefect Horizon")

FastMCP's own managed hosting product — branded **FastMCP Cloud** at `cloud.fastmcp.com`, and
described in current gofastmcp.com deployment docs under the broader **Prefect Horizon** platform
(FastMCP's maintainer, PrefectHQ, packaging Deploy/Registry/Gateway/Agents as one integrated
system). [[gofastmcp.com/deployment/fastmcp-cloud]](https://gofastmcp.com/deployment/fastmcp-cloud)

- **Deployment flow**: connect GitHub → select repo → configure (name, description, entrypoint
  file, auth) → deploy; builds/deploys to a unique URL in roughly 60 seconds. Auto-detects Python
  deps from `requirements.txt`/`pyproject.toml`; auto-redeploys on push to `main`.
- **Pricing**: free personal tier for FastMCP users; enterprise governance/SSO/RBAC/audit-log
  tier for teams.
- **Scope**: explicitly a **Python/FastMCP-server** hosting product — no evidence in the docs of
  support for arbitrary/non-FastMCP or TypeScript servers. This is a strong lock-in signal: it is
  the easiest hosted path *specifically because* the server is FastMCP-based, reinforcing the
  Python/FastMCP framework choice if hosted deployment (vs. local `stdio` launch) is a goal.
[[gofastmcp.com/deployment/fastmcp-cloud]](https://gofastmcp.com/deployment/fastmcp-cloud)

This is a **remote/`streamable-http`** distribution model — no PyPI/npm package required at all,
since the client just points at a URL (`remotes[]` in `server.json`, not `packages[]`). It is the
odd one out among the five: it bypasses the "must exist on PyPI/npm first" constraint entirely
because there's no local package to launch — but it also means the server isn't independently
`uvx`-installable unless *also* published to PyPI.

### 2.6 Compatibility matrix

| Target | Requires PyPI/npm first? | Python (FastMCP) | TypeScript |
|---|---|---|---|
| MCP Registry (metadata only) | Yes — registry never hosts artifacts | Yes, via PyPI package entry | Yes, via npm package entry |
| PyPI/npm package (`uvx`/`npx`) | N/A (this *is* the artifact) | Natural fit (`uvx`) | Natural fit (`npx`) |
| Docker image | No | Yes | Yes |
| mcpb/DXT bundle | No | Yes, but pydantic/compiled-deps caveat unless UV-runtime mode | Yes — spec's recommended/friction-free case |
| Hosted (FastMCP Cloud) | No | Yes — product is FastMCP-specific | Not supported by this product |

---

## Sources

- [gofastmcp.com/integrations/openapi](https://gofastmcp.com/integrations/openapi)
- [gofastmcp.com/getting-started/welcome](https://gofastmcp.com/getting-started/welcome)
- [gofastmcp.com/deployment/fastmcp-cloud](https://gofastmcp.com/deployment/fastmcp-cloud)
- [PyPI: fastmcp](https://pypi.org/project/fastmcp/)
- [GitHub: jlowin/fastmcp discussion #980 — Multiple OpenAPI specs?](https://github.com/jlowin/fastmcp/discussions/980)
- [GitHub: modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk)
- [npm: openapi-mcp-generator](https://www.npmjs.com/package/openapi-mcp-generator)
- [GitHub: modelcontextprotocol/registry](https://github.com/modelcontextprotocol/registry)
- [modelcontextprotocol/registry: docs/modelcontextprotocol-io/quickstart.mdx](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)
- [modelcontextprotocol/registry: docs/reference/server-json/generic-server-json.md](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/generic-server-json.md)
- [modelcontextprotocol/registry: docs/reference/server-json/official-registry-requirements.md](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md)
- [GitHub: modelcontextprotocol/mcpb README](https://github.com/modelcontextprotocol/mcpb/blob/main/README.md)
