# mcp/

Toolchain root for the **My Product Manager** MCP server — a standalone Python
package (FastMCP) that stands apart from the [`sdks/`](../sdks/) because it is a
different language and, per map #1, independent of the SDKs.

FastMCP builds its tools at runtime from the OpenAPI documents (`from_openapi()`),
so — unlike the SDKs — it needs no code generation step. It reads the git-ignored
[effective specs](../CONTEXT.md#effective-spec) under [`schemas/`](../schemas/)
directly. Distributed via `uvx` / the MCP registry.

Package contents (`pyproject.toml`, server code, tests) are populated by the MCP
spec — see map #1 / #11 / #12. This root is scaffolding only.
