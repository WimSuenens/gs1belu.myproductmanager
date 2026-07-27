"""Build hook: copies the git-ignored `../../schemas/<api>/v17.effective.yaml` files
into the packaged `_specs/` resource home so the sdist/wheel carry what `specs.py`
needs at runtime (see the repo root `CONTEXT.md`'s "effective spec" — build artifact,
not source; this hook is the only thing allowed to smuggle a build artifact past
`.gitignore`, via `pyproject.toml`'s `artifacts` force-include).

This package is the deprecated combined server (#82) — relocated from `mcp/` to
`mcp/combined/` so `mcp/` could become the uv workspace root for the split Upload/
Download servers. `self.root` is now two levels below the repo root, not one.

Runs during both sdist and wheel builds. The `elif not dst.is_file(): raise` branch is
what makes an sdist -> wheel rebuild self-contained: the sdist already carries the
copied files (this hook ran while `../schemas` existed during the sdist build), so
rebuilding the wheel from the sdist alone finds `dst` already present, the `elif`
condition is false, and the loop body falls through with no copy and no error instead
of failing on the now-absent `../schemas`.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_APIS = ("upload", "download")
_VERSION = "v17"


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        pkg = Path(self.root) / "src" / "gs1belu_mpm_mcp" / "_specs"
        repo_schemas = Path(self.root).parent.parent / "schemas"

        for api in _APIS:
            src = repo_schemas / api / f"{_VERSION}.effective.yaml"
            dst = pkg / api / f"{_VERSION}.effective.yaml"

            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            elif not dst.is_file():
                raise FileNotFoundError(
                    f"effective spec missing and none bundled: {src} — run `just gen-schemas` first"
                )
