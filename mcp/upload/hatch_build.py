"""Build hook, run twice over: vendors the workspace's dev-only `../shared/src/_shared`
into this package as a namespaced `_shared/` subpackage (map #76's vendoring mechanism
— collision-proof, byte-identical, cannot drift), and copies the git-ignored
`../../schemas/upload/v17.effective.yaml` into the packaged `_specs/` resource home, so
the sdist/wheel carry what `specs.py` needs at runtime — the pattern the original
combined package established (commit 43cf320, now `mcp/combined/hatch_build.py`).

Runs during both sdist and wheel builds (including editable installs, so a checkout's
own `uv sync`/`pytest` run against the same vendored `_shared/` a published wheel would
carry — never a second, drifting copy). The `elif not dst.is_dir()/is_file(): raise`
branches are what make an sdist -> wheel rebuild self-contained: the sdist already
carries the copied files, so rebuilding the wheel from the sdist alone finds them
already present and falls through with no copy and no error instead of failing on the
now-absent `../shared` / `../../schemas`.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_VERSION = "v17"


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        root = Path(self.root)
        mcp_root = root.parent
        repo_root = mcp_root.parent

        shared_src = mcp_root / "shared" / "src" / "_shared"
        shared_dst = root / "src" / "gs1belu_mpm_upload" / "_shared"
        if shared_src.is_dir():
            shutil.rmtree(shared_dst, ignore_errors=True)
            shutil.copytree(shared_src, shared_dst)
        elif not shared_dst.is_dir():
            raise FileNotFoundError(f"shared source missing and none vendored: {shared_src}")

        spec_src = repo_root / "schemas" / "upload" / f"{_VERSION}.effective.yaml"
        spec_dst = root / "src" / "gs1belu_mpm_upload" / "_specs" / "upload" / f"{_VERSION}.effective.yaml"
        if spec_src.is_file():
            spec_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(spec_src, spec_dst)
        elif not spec_dst.is_file():
            raise FileNotFoundError(
                f"effective spec missing and none bundled: {spec_src} — run `just gen-schemas` first"
            )
