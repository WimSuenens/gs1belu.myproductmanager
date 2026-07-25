# sdks/

Toolchain root for the two generated **My Product Manager** SDKs. Both are produced
by the pinned Kiota CLI from the git-ignored [effective specs](../CONTEXT.md#effective-spec)
under [`schemas/`](../schemas/) — one client per document, never merged.

Layout (populated by later specs — this root is scaffolding only):

- `dotnet/` — the C# SDK: `.sln` + `Directory.Build.props`, an Upload and a Download
  project. Published to NuGet. _(owned by the C# SDK spec — see map #1 / #8)_
- `typescript/` — the TypeScript SDK: a workspace `package.json` with
  `@gs1belu/mpm-upload` and `@gs1belu/mpm-download`. Published to npm. _(same spec)_

Generation and build run from the repo root via `just gen` / `just build`; see
[`CONTRIBUTING.md`](../CONTRIBUTING.md). Never hand-edit generated client code — fix
the schema via its `*.overlay.yaml`, then regenerate and commit.
