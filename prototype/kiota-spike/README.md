# Kiota spike — generate both SDKs, confirm they build

> **PROTOTYPE — throwaway.** Wayfinder ticket [#6](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/6),
> de-risking SDK-architecture decision [#8](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/8).
> Not shipped code. The generated clients under `csharp/` and `typescript/` are evidence, not artifacts to keep.

## TL;DR

All **4 clients generate and build/compile with zero errors** — the empirical confirmation of research #2's
"no hard blockers" read. C# is production-solid; TS compiles but its "compiles" is weaker evidence than it looks
(every import is `// @ts-ignore`-suppressed and the language is Kiota-preview). **No schema patching was required.**

| Client | Generate | Build / type-check | Deps |
|---|---|---|---|
| C# · upload   | ✅ clean | ✅ `dotnet build` 0 err / 0 warn | `Microsoft.Kiota.Bundle` **2.0.0** |
| C# · download | ✅ clean | ✅ `dotnet build` 0 err / 0 warn | `Microsoft.Kiota.Bundle` **2.0.0** |
| TS · upload   | ⚠ "preview" warning | ✅ `tsc --noEmit` exit 0 | `@microsoft/kiota-bundle` **1.0.0-preview.103** |
| TS · download | ⚠ "preview" warning | ✅ `tsc --noEmit` exit 0 | `@microsoft/kiota-bundle` **1.0.0-preview.103** |

Toolchain used: kiota 1.34.1, dotnet 10.0.300 (`net10.0`), node v24, typescript ^5.6.

## Reproduce

```bash
# C# (per client dir)
dotnet build prototype/kiota-spike/csharp/upload/UploadSpike.csproj
dotnet build prototype/kiota-spike/csharp/download/DownloadSpike.csproj
# TypeScript
cd prototype/kiota-spike/typescript && npm install
npx tsc --project upload/tsconfig.json && npx tsc --project download/tsconfig.json
```

Regenerate (from repo root):

```bash
kiota generate -l CSharp     -d docs/schemas/upload/v17.yaml   -o .../csharp/upload      -n Gs1Belu.Mpm.Upload   -c UploadApiClient   --clean-output
kiota generate -l CSharp     -d docs/schemas/download/v17.yaml -o .../csharp/download    -n Gs1Belu.Mpm.Download -c DownloadApiClient --clean-output
kiota generate -l TypeScript -d docs/schemas/upload/v17.yaml   -o .../typescript/upload  -c UploadApiClient   --clean-output
kiota generate -l TypeScript -d docs/schemas/download/v17.yaml -o .../typescript/download -c DownloadApiClient --clean-output
```

## What worked

- **Generation is patch-free.** Both specs generate as-is. The `operationId`s (`get-tradeitems`, `upsert-tradeitem`,
  `get-tradeitem`) are ignored for naming (Kiota derives fluent path names), so their non-uniqueness across specs is a
  non-issue — each spec is its own client, so no collision.
- **Auth confirmed as an adapter-layer concern.** The generated client ctor is `new UploadApiClient(IRequestAdapter)`
  and defaults `BaseUrl` to the spec server (`https://api.gs1belu.org/myproductmanager/{upload|download}/v17`).
  The subscription key is **not** in the generated code — the caller wires `ApiKeyAuthenticationProvider`
  (header `Ocp-Apim-Subscription-Key` or query `subscription-key`) into the adapter. This matches research #2:
  the api-key layer is one-liner glue, but the OAuth2 Bearer layer (research #5) needs a **custom handler on top**
  and is out of what Kiota emits — a live input to auth decision #9.
- **Lean dependency footprint.** C# = one package (`Microsoft.Kiota.Bundle`, which rolls up abstractions +
  serialization + HTTP). TS = the bundle + 4 serialization packages it pulls in (12 npm packages total installed).
  The `...Authentication.Azure` package that `kiota info` also lists is **not needed** for our api-key scheme.
- **`--clean-output` + `kiota-lock.json`** make regeneration deterministic — the base for the workspace/lock approach
  research #2 picked for SDK-arch #8.

### Generated call surface (the three operations #6 asked about)

```csharp
// get-tradeitems (download) — all 8 filters are typed query params
var page = await download.Tradeitems.GetAsync(c => {
    c.QueryParameters.Gtin = "05412345678900";
    c.QueryParameters.Limit = 1000;            // ⚠ double? (see below)
    c.QueryParameters.BrandOwnerDefault = true;
    c.QueryParameters.Since = "2026-01-01T00:00:00Z";
});   // -> TradeItemResponse? (HAL: _links.next, _embedded.tradeItems)

// upsert-tradeitem (upload)
await upload.Tradeitems.PostAsync(tradeItem);   // -> Task (void: 201, no body)

// get-tradeitem (upload) — fluent indexer
var item = await upload.Tradeitems["05412345678900"].GetAsync();   // -> TradeItem?
```

## What needs patching / smells to weigh in #8

None of these block a build; they are ergonomics/risk inputs for the SDK-architecture decision.

1. **`limit` → `double?`, not `int`.** The download spec types `limit` as `number` (schema comment even says "int32"),
   so Kiota emits `double? Limit`. Callers pass `1000` fine, but the type is misleading and un-idiomatic.
   Fix options for #8: (a) patch the spec to `type: integer, format: int32` before generating, or
   (b) accept it and hide it behind a hand-written pager (research #2 kept an idiomatic wrapper as a live sub-question).
   The same `number` appears on `upsert`'s model fields — worth a spec-prep sweep.
2. **TypeScript "compiles" is soft evidence.** Every generated import carries `// @ts-ignore`, so `tsc` is *not*
   type-checking the client↔runtime boundary — a clean exit doesn't prove the preview runtime's types line up.
   Combined with Kiota's own "source breaking changes will happen" preview warning, this is the concrete form of
   research #2's **"TS Experimental" risk**. Recommend #8 pin exact preview versions and add a smoke test that
   actually *instantiates* a client (not just `tsc`), so a preview bump that breaks at runtime is caught.
3. **NuGet supply-chain gotcha.** `Microsoft.Kiota.Bundle` **< 2.0.0** transitively pulls
   `Microsoft.Kiota.Abstractions` with a **known high-severity advisory (GHSA-7j59-v9qr-6fq9, NU1903)**.
   Use **2.0.0** (what `kiota info` recommends) — it builds clean with no advisory. #10 (publishing) should turn
   NU1903 into a build error so this can't regress.
4. **Generated `[Obsolete]` config duplication.** Kiota still emits deprecated non-generic `...RequestConfiguration`
   classes alongside the generic ones (harmless, just noise). No action; noted so it isn't mistaken for a bug.

## Recommended packaging signal (input to SDK-arch #8)

- **Confirm "4 clients, no merge."** The spike validates research #2's shape empirically: 2 specs × 2 langs, each an
  independent client, no shared-schema merge needed. Shared model duplication (e.g. `TradeItem`, `ProblemDetails`)
  is real but cheap and did not cause conflicts.
- **C# packaging is low-risk.** One stable runtime dep, `net10.0` builds clean; a normal `net8.0;net10.0` multi-target
  and NuGet pack should be uneventful. Size: ~1.4–1.5k LoC across ~20 files per client (class-per-model).
- **TS packaging carries the preview tax.** ~0.9–1k LoC in 3–4 files (compact metadata/proxifier pattern), but the
  preview runtime + `@ts-ignore` boundary means npm consumers inherit "source breaking changes" risk. #8 should decide
  the guardrail: pin exact versions, add a runtime smoke test, and set consumer expectations (or reconsider whether TS
  ships on the same cadence as C#).
- **Graduate the fog:** this spike sharpens the "retry/rate-limit/logging middleware" and "OAuth2 token lifecycle"
  Not-yet-specified items — both are adapter/handler-layer concerns, confirmed to live *outside* generated code and
  therefore addable without regenerating.
