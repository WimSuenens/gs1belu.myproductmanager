## Summary
<what changed and why>

## Affected artifacts
- [ ] C# SDK (Upload / Download)
- [ ] TypeScript SDK
- [ ] MCP server
- [ ] Schemas / overlays
- [ ] Tooling / CI

## Checklist
- [ ] Ran `just gen` if schemas or SDK generation changed (CI `regen-sync` verifies)
- [ ] Tests pass locally (`just test`)
- [ ] Added a release entry per the release process (see CONTRIBUTING) — if user-facing
- [ ] Public API/docs updated if the surface changed
