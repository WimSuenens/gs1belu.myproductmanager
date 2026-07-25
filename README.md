# gs1belu.myproductmanager

Generated C#/TypeScript SDKs and an MCP server for the **GS1 Belgium & Luxembourg
"My Product Manager"** REST APIs (Upload + Download, v17), built from the vendor
OpenAPI schemas under [`schemas/`](schemas/).

> [!IMPORTANT]
> **Unofficial.** This project is a community effort and is **not affiliated with,
> endorsed by, or supported by GS1** in any way. "GS1" and "My Product Manager" are
> the property of their respective owners. Use at your own risk.

## Artifacts

Three artifacts are generated from the same source schemas. None are published yet
— the links below are where each will land. Per-package READMEs carry the real
quickstart for each.

| Artifact | Language | Consume via | Source |
|---|---|---|---|
| **C# SDK** | .NET | NuGet — `dotnet add package …` _(coming soon)_ | [`sdks/`](sdks/) → `dotnet/` |
| **TypeScript SDK** | TS/JS | npm — `@gs1belu/mpm-upload`, `@gs1belu/mpm-download` _(coming soon)_ | [`sdks/`](sdks/) → `typescript/` |
| **MCP server** | Python | `uvx` / the MCP registry _(coming soon)_ | [`mcp/`](mcp/) |

The two SDKs are generated with [Kiota](https://learn.microsoft.com/openapi/kiota/)
(one client per API document, never merged). The MCP server builds its tools at
runtime with FastMCP — no code generation.

## Monorepo map

```
schemas/     Vendor OpenAPI specs + overlays — the single source of truth
  upload/    · download/   (each: v17.yaml vendor original, v17.json, v17.overlay.yaml)
sdks/        The two Kiota SDKs (dotnet/, typescript/)
mcp/         The FastMCP MCP server (Python)
scripts/     Schema-prep build + tests, driven by the justfile
docs/        ADRs, research, manuals, the schema-ingestion runbook
justfile     Task front door — `just gen` / `just build` / `just test`
```

The project's ubiquitous language (pristine vendor original, overlay, effective
spec, dead patch) is defined in [`CONTEXT.md`](CONTEXT.md); the decisions behind
the layout are in [`docs/adr/`](docs/adr/).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the toolchain prerequisites, the
schema-editing rule, and the PR flow. The one rule that must never be broken:
**never hand-edit a vendor schema or generated code — correct it through the
overlay and regenerate.**

## License

MIT.
