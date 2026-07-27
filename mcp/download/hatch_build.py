"""Build hook: vendors the workspace's dev-only `../shared/src/_shared` into this
package as a namespaced `_shared/` subpackage (map #76's vendoring mechanism —
collision-proof, byte-identical, cannot drift). Unlike the Upload sibling, this
package bundles no spec at all (#75): `from_openapi` generated zero tools on the
Download side, so there is nothing for it to do here.

Runs during both sdist and wheel builds (including editable installs, so a checkout's
own `uv sync`/`pytest` run against the same vendored `_shared/` a published wheel
would carry — never a second, drifting copy). The `elif not dst.is_dir(): raise`
branch is what makes an sdist -> wheel rebuild self-contained: the sdist already
carries the copied files, so rebuilding the wheel from the sdist alone finds them
already present and falls through with no copy and no error instead of failing on the
now-absent `../shared`.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        root = Path(self.root)
        mcp_root = root.parent

        shared_src = mcp_root / "shared" / "src" / "_shared"
        shared_dst = root / "src" / "gs1belu_mpm_download" / "_shared"
        if shared_src.is_dir():
            shutil.rmtree(shared_dst, ignore_errors=True)
            shutil.copytree(shared_src, shared_dst)
        elif not shared_dst.is_dir():
            raise FileNotFoundError(f"shared source missing and none vendored: {shared_src}")
