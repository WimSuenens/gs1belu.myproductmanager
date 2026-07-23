# Can Kiota generate C# and TypeScript SDKs for the GS1 BELU My Product Manager APIs?

Research date: 2026-07-23. All facts below are sourced from Microsoft's official Kiota documentation (learn.microsoft.com/en-us/openapi/kiota) and the `microsoft/kiota` / `microsoft/kiota-typescript` / `microsoft/kiota-dotnet` GitHub repositories (primary sources only). Each claim is cited.

Grounding: this analysis is based on the two schemas in this repo:
- `docs/schemas/upload/v17.yaml` — `POST /tradeitems` (`upsert-tradeitem`), `GET /tradeitems/{gtin}` (`get-tradeitem`)
- `docs/schemas/download/v17.yaml` — `GET /tradeitems` (`get-tradeitems`), HAL-paginated, with `limit`, `cursor`, `since`, `gtin`, `informationProviderGLN`, etc. as query params

---

## 1. Maturity/support for C# vs. TypeScript, and runtime dependencies

**C# is Stable; TypeScript is Experimental.** This is the single biggest fact governing this decision.

The official `kiota info` maturity table:

```
Language    Maturity Level
CSharp      Stable
Go          Stable
Java        Preview
PHP         Stable
Python      Stable
Ruby        Experimental
Swift       Experimental
TypeScript  Experimental
```
Source: [Using the Kiota tool — Language information](https://learn.microsoft.com/en-us/openapi/kiota/using#language-information)

Microsoft's own definitions of these levels (from the releases/support page):

- **Stable**: "Kiota provides full functionality for the language and is used to generate production API clients."
- **Experimental**: "Kiota provides some functionality for the language but is still in early stages. Some features might not work correctly or at all."

Source: [Releases and support for Kiota — Maturity level](https://learn.microsoft.com/en-us/openapi/kiota/support)

The GitHub README's support matrix (as of the current repo state) similarly lists TypeScript/JavaScript with a "preview" marker, not the same tier as C#/Go/Java/PHP/Python which are marked stable. Source: [github.com/microsoft/kiota](https://github.com/microsoft/kiota) (README support table).

Also notable: breaking changes to **Stable** languages force a Kiota major version bump; **Experimental** languages carry no such guarantee, so TypeScript client output can change shape between Kiota releases without a major-version signal. Source: [Releases and support for Kiota](https://learn.microsoft.com/en-us/openapi/kiota/support).

### Runtime dependencies

**C# (NuGet)** — from `kiota info -l CSharp`:
```
Microsoft.Kiota.Abstractions
Microsoft.Kiota.Http.HttpClientLibrary
Microsoft.Kiota.Serialization.Form
Microsoft.Kiota.Serialization.Json
Microsoft.Kiota.Authentication.Azure   (only needed for Entra auth; not needed for our apiKey scheme)
Microsoft.Kiota.Serialization.Text
Microsoft.Kiota.Serialization.Multipart
Microsoft.Kiota.Bundle   (optional convenience package bundling abstractions+serialization+http)
```
Source: [Using the Kiota tool — `kiota info -l CSharp`](https://learn.microsoft.com/en-us/openapi/kiota/using#example---with-language)

**TypeScript (npm)** — from the dependencies matrix:
```
@microsoft/kiota-abstractions
@microsoft/kiota-http-fetchlibrary        (relies on nothing extra; fetch-based)
@microsoft/kiota-serialization-json
@microsoft/kiota-serialization-text
@microsoft/kiota-serialization-form
@microsoft/kiota-serialization-multipart
@microsoft/kiota-authentication-azure     (only for Entra auth; relies on @azure/identity — not needed here)
@microsoft/kiota-bundle                   (optional bundle package, same idea as C#)
```
Source: [Managing dependencies of Kiota API clients](https://learn.microsoft.com/en-us/openapi/kiota/dependencies)

The official TypeScript quickstart uses just the bundle package (`npm install @microsoft/kiota-bundle`) plus specific TS project settings kiota requires: `esModuleInterop: true`, `forceConsistentCasingInFileNames: true`, `module`/`moduleResolution: NodeNext`, `target: es2020+`, and `package.json` `"type": "module"`. Source: [Build API clients for TypeScript — quickstart](https://learn.microsoft.com/en-us/openapi/kiota/quickstarts/typescript).

---

## 2. Auth: apiKey security scheme support (our `Ocp-Apim-Subscription-Key` header / `subscription-key` query)

Both specs declare:
```yaml
securitySchemes:
  apiKeyHeader:
    type: apiKey
    name: Ocp-Apim-Subscription-Key
    in: header
  apiKeyQuery:
    type: apiKey
    name: subscription-key
    in: query
security:
  - apiKeyHeader: []
  - apiKeyQuery: []
```

Kiota's abstractions libraries ship a dedicated **`ApiKeyAuthenticationProvider`** for exactly this scenario, in both languages, per the official authentication doc:

> "Some APIs simply rely on an API key for authentication in the request query parameters or in the request headers. For this scenario, the abstractions packages provide an `ApiKeyAuthenticationProvider`. This provider allows you to: Set the name of the request header/query parameter... Set the value... Choose whether the provided name and value are used for a request header or for a query parameter."

Source: [Authentication with Kiota API clients — API key authentication provider](https://learn.microsoft.com/en-us/openapi/kiota/authentication)

**C# constructor** (from `microsoft/kiota-dotnet` source):
```csharp
public ApiKeyAuthenticationProvider(string apiKey, string parameterName,
    KeyLocation keyLocation, params string[] allowedHosts)

public enum KeyLocation { QueryParameter, Header }
```
Query mode appends `?<parameterName>=<apiKey>` (or `&...` if a query string already exists); header mode calls `request.Headers.Add(ParameterName, ApiKey)`. The provider validates the target host against `allowedHosts` and enforces HTTPS (throws if not HTTPS).
Source: [kiota-dotnet — `ApiKeyAuthenticationProvider.cs`](https://github.com/microsoft/kiota-dotnet/blob/main/src/abstractions/authentication/ApiKeyAuthenticationProvider.cs)

**TypeScript constructor** (from `microsoft/kiota-typescript` source):
```typescript
public constructor(
  private readonly apiKey: string,
  private readonly parameterName: string,
  private readonly location: ApiKeyLocation,
  validHosts?: Set<string>,
)

export enum ApiKeyLocation { QueryParameter, Header }
```
Same behavior: appends to URL for query mode, `request.headers.add(...)` for header mode.
Source: [kiota-typescript — `apiKeyAuthenticationProvider.ts`](https://github.com/microsoft/kiota-typescript/blob/main/packages/abstractions/src/authentication/apiKeyAuthenticationProvider.ts)

**Key supplied at construction time**: the API key string is passed directly into the `ApiKeyAuthenticationProvider` constructor by application code (not generated from the OpenAPI doc — Kiota does not auto-wire the `securitySchemes` block into a specific provider instance). The generated client's constructor instead takes an `IRequestAdapter` (C#) / `RequestAdapter` (TS), which itself is constructed with the chosen `IAuthenticationProvider`. So the wiring is: app code picks `ApiKeyAuthenticationProvider`, feeds it the key + header/query name + location, wraps it in the HTTP-client-library's request adapter, and passes that adapter into the generated `ApiClient`. This is manual glue code you write once per client; Kiota does **not** generate it from the `securitySchemes` section automatically. This matches a documented open issue about wanting Kiota to auto-select the right auth object from the security scheme (still open as of research date): [microsoft/kiota#5070 — "If the security scheme is provided, Kiota should use it to create the right auth object"](https://github.com/microsoft/kiota/issues/5070).

Note: the doc explicitly warns the provider does **not** encode/escape the key or value — not an issue for a raw subscription-key string, but worth knowing if the key ever contains reserved URL characters for the query-param variant.

**Verdict**: apiKey-header and apiKey-query are both first-class, well-documented scenarios in Kiota with an out-of-the-box provider class in both C# and TypeScript. This is a strong fit for our auth model.

---

## 3. Multiple OpenAPI descriptions (Upload + Download) in one repo

Our two specs are separate documents with different `servers.url`, different `operationId`s, but overlapping component schema names (`tradeItem`, `party`, `description200`, `problemDetails`, etc. are duplicated verbatim in both files).

**Kiota's model is one generated client per OpenAPI description** — there is no "merge two OpenAPI docs into one client" feature. The GitHub README describes Kiota's mission as generating "an API client to call any OpenAPI described API you are interested in," implying a 1:1 mapping between description and client; no merge/combine capability is documented. Source: [github.com/microsoft/kiota README](https://github.com/microsoft/kiota).

To manage *multiple* clients in a single repo/project, Kiota provides the **workspace model**, formalized in `workspace.json` (the design doc for it lives in-repo):

- A single `workspace.json` can register multiple named clients, each with its own OpenAPI description location, output directory, include/exclude path filters, target language, and — critically — its own `clientClassName` / `clientNamespaceName`, so two clients generated into the same project don't collide on type names.
- Example shape:
  ```json
  {
    "clients": {
      "GraphClient": { /* description location, language, output dir, className, namespaceName, ... */ },
      "businessCentral": { /* ... */ }
    }
  }
  ```
- Workspace-aware CLI verbs: `kiota workspace init`, `kiota client add`, `kiota client generate`, `kiota client edit`, `kiota client remove`.

Source: [microsoft/kiota — `specs/scenarios/kiota-workspace.md`](https://github.com/microsoft/kiota/blob/main/specs/scenarios/kiota-workspace.md)

**Practical implication for us**: generate two independent clients — e.g. `UploadClient` in namespace `Gs1Belu.MyProductManager.Upload` and `DownloadClient` in namespace `Gs1Belu.MyProductManager.Download` (analogous package names for TS) — each with its own `--output` directory and its own `kiota-lock.json`. Because the two specs both define a schema literally named `tradeItem` (and `party`, `problemDetails`, etc.) with **identical shape**, per-client namespacing avoids type collisions automatically — you will end up with two structurally-identical-but-distinct `TradeItem` model classes (one per client/namespace), not a shared one. There is no supported dedup/sharing mechanism across separately generated clients; if a single shared `TradeItem` type is wanted across upload/download, that has to be hand-rolled (e.g., a thin mapping layer), since Kiota has no cross-description schema-merging feature.

---

## 4. Friction points against our specific specs

### (a) `limit` query param typed `type: number` (download spec, line 32-36)
```yaml
- name: limit
  in: query
  description: Format - int32. The number of tradeitems shown in the next page.
  schema:
    type: number
```
This has **no `format` set** (just bare `type: number`), so it won't even trip Kiota's `InconsistentTypeFormat` validation rule (that rule fires specifically when *type and format are mismatched*, e.g. `type: string` + `format: int32`). Source: [Using the Kiota tool — `--disable-validation-rules`](https://learn.microsoft.com/en-us/openapi/kiota/using#disable-validation-rules---dvr) (rule list, `InconsistentTypeFormat` and `KnownAndNotSupportedFormats` defined there). Practically, `type: number` without a format maps to a floating-point type in both target languages (`double` in C#, `number` in TS) — it will generate cleanly, but callers get a `double`/floating `limit` parameter instead of the semantically-correct integer, because the description text ("int32") isn't a machine-readable signal Kiota can use. This is a spec quality issue, not a Kiota bug — but it means the generated method signature (`double? limit` in C#) doesn't match author intent and should ideally be fixed upstream in the OpenAPI doc (`type: integer, format: int32`) before generation, if the spec authors can be persuaded, or accepted as a wart.

### (b) HAL envelope `_links` / `_embedded` (download spec `tradeItemResponse` schema)
```yaml
tradeItemResponse:
  type: object
  properties:
    _links:
      type: object
      properties:
        next: { type: object, properties: { href: { type: string } }, additionalProperties: false }
      additionalProperties: false
    _embedded:
      type: object
      properties:
        tradeItems: { type: array, items: { $ref: '#/components/schemas/tradeItem' } }
      additionalProperties: false
  additionalProperties: false
```
This is a plain nested-object OpenAPI schema (no `oneOf`/discriminator/dynamic keys) — structurally nothing exotic. It generates as ordinary nested model classes. The only twist is the **`_`-prefixed property names** (`_links`, `_embedded`), which are not valid/idiomatic identifiers in either target language as-is; Kiota's standard sanitizer will need to produce a valid member name (e.g. `Links`/`links`, `Embedded`/`embedded`) and use serialization attributes/annotations to keep the JSON wire name as `_links`/`_embedded`. This is Kiota's normal, well-exercised name-sanitization path (used throughout Microsoft Graph's SDKs, which have far gnarlier names) — not flagged as a known issue in any GitHub issue found during this research. A related `additionalProperties: false` bug (missing properties when `additionalProperties: false` is set on a schema) was found, but it was **Python-specific** and was fixed by Kiota v1.17: [microsoft/kiota#5037](https://github.com/microsoft/kiota/issues/5037). No open equivalent bug was found for C# or TypeScript. Treat as low risk, but verify the generated field names/wire names once you actually run generation.

### (c) Regex `pattern` on strings (`gtin`, `gln`, `languageCode`)
Our specs use `pattern` extensively:
- `gtin`: `pattern: '[0-9]([0-1]|[3-9])([0-9]{12})'`
- `gln`: `pattern: '[0-9]{13}'`
- `languageCode`: `pattern: '[a-z]{2}-[A-Z]{2}'` (repeated across every `description*` schema)

**Kiota does not enforce OpenAPI `pattern` constraints in generated code.** It generates the property as a plain `string` and silently drops the regex constraint — there is no client-side validation emitted. This is confirmed by an open community ask for the feature (a proposal to have `pattern` generate a reference/validated type in the SDK), indicating the capability doesn't exist today: search results around Kiota's GitHub issues consistently describe this as a gap, not a supported feature. In short: **treat `pattern` as documentation only** — GTIN/GLN format checking has to be done in your own code (or server-side, which the API already does via its 400/`validationResult` response), not relied upon from the generated client.

### (d) `problemDetails` (RFC 7807) and `validationResult` error bodies
Both are ordinary flat OpenAPI object schemas (no polymorphism), so they generate as normal model classes with no special handling needed:
```yaml
problemDetails: { type, title, status, detail, instance, extensions } # all nullable
validationResult: { status: integer, details: [{ severity, code, message }] }
```
One nuance: on the **download** spec, `problemDetails` also carries a top-level `additionalProperties: { type: object }` (open/free-form extension bag) alongside its fixed properties, and the **upload** spec's `problemDetails.extensions` field also models an open bag via `additionalProperties`. Kiota generates these as an "AdditionalData"-style dictionary property (`IDictionary<string,object>` in C#, an `additionalData` map in TS) — this is Kiota's standard, well-supported mechanism (`--additional-data` flag, on by default) for schemas with `additionalProperties`. Because 400/401/403/404 error responses across both specs consistently return `problemDetails` (except upload's 400 which is `validationResult` instead — note the **asymmetry**: upload returns `validationResult` on 400 but `problemDetails` on 401/403; download returns `problemDetails` on 400/401/403), error handling code will need to branch on status code to know which body type to deserialize — that's just how the spec is written and Kiota will faithfully reflect it (each response-status-to-schema mapping generates its own typed exception/response path), not a generation limitation.

### (e) `operationId`s present: `upsert-tradeitem`, `get-tradeitem`, `get-tradeitems`
Kiota **does not use `operationId` for naming generated methods.** It deliberately builds a path-segment-based fluent API instead, regardless of `operationId` values. A Kiota maintainer (Sebastien Levert) confirmed this design choice directly:

> "We made architecture decisions to respect the rules of the path and think that consistency among all generated clients is a clear benefit to our users."

Source: [microsoft/kiota Discussion #4420 — "OperationId's as client methods"](https://github.com/microsoft/kiota/discussions/4420)

Practical effect on our API: `GET /tradeitems/{gtin}` becomes fluent-style `client.tradeitems.byGtin(gtin).get()` (or similar, exact casing/segment naming depends on Kiota's path-segment sanitizer), **not** a flat method called `getTradeitem()`. `POST /tradeitems` becomes `client.tradeitems.post(tradeItem)`. This is Kiota's core, well-established design (same pattern Microsoft Graph SDKs use) — the presence of our `operationId`s is essentially inert; they don't need to be "fixed" or removed, Kiota simply ignores them for naming purposes.

**One extra wrinkle worth flagging**: the download API's `GET /tradeitems` and upload API's `POST /tradeitems` / `GET /tradeitems/{gtin}` are on the *same path shape* but in *separate documents/servers*, so this isn't the "two methods competing over the same path" problem described in [microsoft/kiota#7292 — "Required query params can break other operations on the same path"](https://github.com/microsoft/kiota/issues/7292); that only matters within a single OpenAPI document. Since Upload and Download are separate descriptions generating separate clients, this is a non-issue for us.

---

## 5. CLI model for repeatable CI regeneration

### `kiota generate` — key flags for our use case
```
kiota generate (--openapi | -d) <path>
               (--language | -l) <language>       # csharp | typescript | ...
               [(--output | -o) <path>]
               [(--class-name | -c) <name>]        # default: ApiClient
               [(--namespace-name | -n) <name>]    # default: ApiSdk
               [--backing-store | -b]
               [--exclude-backward-compatible | --ebc]
               [--additional-data | --ad]          # default true
               [(--serializer | -s) <classes>]
               [(--deserializer | --ds) <classes>]
               [--clean-output | --co]
               [(--structured-mime-types | -m) <mime-types>]
               [(--include-path | -i) <glob>] [(--exclude-path | -e) <glob>]
               [(--disable-validation-rules | --dvr) <rule name>]
               [(--type-access-modifier | --tam) <modifier>]   # CSharp only
```
Source: [Using the Kiota tool — Client generation](https://learn.microsoft.com/en-us/openapi/kiota/using#client-generation)

Two example invocations for our repo:
```bash
kiota generate -d docs/schemas/upload/v17.yaml   -l csharp     -c UploadClient   -n GS1Belu.MyProductManager.Upload   -o ./clients/csharp/upload
kiota generate -d docs/schemas/download/v17.yaml -l typescript -c DownloadClient -n gs1belu.myproductmanager.download -o ./clients/ts/download
```
(Repeat for the remaining language × description combinations — 4 invocations total for the full C#+TS × Upload+Download matrix.)

### Lock files
Each `--output` directory gets a **`kiota-lock.json`** containing all generation parameters plus a hash of the source description.

> "On subsequent generations, including updates, the generation will be skipped if the description and the parameters have not changed and if clean-output is **false**. The lock file is meant to be committed to the source control with the generated sources."

Source: [Using the Kiota tool — Client generation](https://learn.microsoft.com/en-us/openapi/kiota/using#client-generation)

This gives idempotent regeneration in CI for free: run `kiota generate` (or `kiota update`, which scans for all `kiota-lock.json` files under an output path and regenerates each) and it no-ops unless the spec YAML or generation params actually changed. `kiota update` accepts `--clean-output`/`--clear-cache`/`-o`/`--log-level`. Source: [Using the Kiota tool — Client update](https://learn.microsoft.com/en-us/openapi/kiota/using#client-update).

### `kiota-config.json` / workspace model
For multi-client repos (our Upload+Download × C#+TS = 4 clients), the newer **workspace** model (`workspace.json`, `kiota client add/generate/edit/remove`, `kiota workspace init`) is the documented path to registering all four client configs once and regenerating them together in CI, rather than hand-maintaining four separate `kiota generate` invocations. See §3 above for details and source.

### CI recommendations
- Pin the Kiota CLI version in CI (Kiota follows semver; minor releases ship monthly on "the first Tuesday of every month" — Source: [Releases and support for Kiota](https://learn.microsoft.com/en-us/openapi/kiota/support)) to avoid drift, especially since TypeScript is Experimental and has no breaking-change guardrail.
- Commit `kiota-lock.json` files so regeneration is a no-op unless the spec changes — makes "regenerate and diff" a cheap CI check.
- Always run `kiota info -l <language> --json` (or check against the dependencies table) after regenerating, to catch cases where the required NuGet/npm package versions drifted.

---

## Summary verdict

| Dimension | C# | TypeScript |
|---|---|---|
| Maturity | **Stable** (production-ready) | **Experimental** ("some features might not work correctly or at all") |
| apiKey header+query auth | Full support via `ApiKeyAuthenticationProvider` | Full support via `ApiKeyAuthenticationProvider` (same design) |
| Multi-description (Upload+Download) | One client per description; workspace model manages both | Same |
| `limit: type: number` | Generates as `double?`, no validation error, but wrong semantic type | Same (`number`) |
| HAL `_links`/`_embedded` | Plain nested objects, sanitized names — low risk | Same |
| `pattern` on gtin/gln/languageCode | Silently ignored, not enforced client-side | Same |
| problemDetails/validationResult | Generates cleanly as flat models + AdditionalData bag | Same |
| operationId | Ignored by design; fluent path-based naming used instead | Same |

**Bottom line**: Kiota can generate both an Upload and a Download client, in both C# and TypeScript, from these two specs without needing to patch the YAML — nothing here is a hard blocker. The main red flag is that **TypeScript generation sits at Kiota's "Experimental" maturity tier**, Microsoft's own lowest support tier, explicitly not recommended for production clients and with no breaking-change protection between releases — this is the primary risk to flag before committing to Kiota for the TypeScript SDK. C# generation is Stable and low-risk. Secondary, non-blocking items to handle in glue code / expectations: the `limit` param will come out as a floating type instead of integer; `pattern` constraints (gtin/gln/languageCode) are not enforced by the generated client and must be validated separately; and the two clients will produce two independent, non-shared `TradeItem`/`Party`/etc. model types since Kiota has no schema-sharing across separately generated clients.

---

## Sources index

- [Kiota documentation home](https://learn.microsoft.com/en-us/openapi/kiota/)
- [Using the Kiota tool (CLI reference, flags, lock files, validation rules)](https://learn.microsoft.com/en-us/openapi/kiota/using)
- [Releases and support for Kiota (maturity levels, semver cadence)](https://learn.microsoft.com/en-us/openapi/kiota/support)
- [Authentication with Kiota API clients (ApiKeyAuthenticationProvider)](https://learn.microsoft.com/en-us/openapi/kiota/authentication)
- [Managing dependencies of Kiota API clients (package tables per language)](https://learn.microsoft.com/en-us/openapi/kiota/dependencies)
- [Build API clients for TypeScript (quickstart, tsconfig requirements, bundle package)](https://learn.microsoft.com/en-us/openapi/kiota/quickstarts/typescript)
- [github.com/microsoft/kiota (README, support matrix)](https://github.com/microsoft/kiota)
- [microsoft/kiota — kiota-workspace.md design doc](https://github.com/microsoft/kiota/blob/main/specs/scenarios/kiota-workspace.md)
- [microsoft/kiota-dotnet — ApiKeyAuthenticationProvider.cs](https://github.com/microsoft/kiota-dotnet/blob/main/src/abstractions/authentication/ApiKeyAuthenticationProvider.cs)
- [microsoft/kiota-typescript — apiKeyAuthenticationProvider.ts](https://github.com/microsoft/kiota-typescript/blob/main/packages/abstractions/src/authentication/apiKeyAuthenticationProvider.ts)
- [microsoft/kiota Discussion #4420 — OperationId's as client methods](https://github.com/microsoft/kiota/discussions/4420)
- [microsoft/kiota Issue #5070 — security scheme should drive auth object creation (open)](https://github.com/microsoft/kiota/issues/5070)
- [microsoft/kiota Issue #7292 — required query params can break other operations on the same path](https://github.com/microsoft/kiota/issues/7292)
- [microsoft/kiota Issue #5037 — additionalProperties:false / missing properties (Python, fixed in v1.17)](https://github.com/microsoft/kiota/issues/5037)
