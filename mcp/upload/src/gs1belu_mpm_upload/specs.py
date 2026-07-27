"""Loads the upload effective spec (`upload/<version>.effective.yaml`) that `just gen`
produces from the pristine vendor original + overlay — the same artifact Kiota reads
for the SDKs (`CONTEXT.md`'s `effective spec`). No MCP-specific schema prep: this only
locates and parses the file, it never builds one.

Resolution order, override wins, then the packaged copy, then the dev checkout:
1. `path_override_env` — an explicit env var pointing at a spec file, always wins.
2. The packaged `_specs/` resource — copied into the wheel/sdist at build time by
   `hatch_build.py`, so a `uvx`/PyPI install needs no repo checkout at all.
3. `schemas/upload/<version>.effective.yaml` relative to a repo checkout — the
   git-ignored dev-loop path `just gen` writes to; only reached in an editable install
   (nothing under `_specs/` to find, since that's a build-time artifact).
"""

from __future__ import annotations

import os
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _default_spec_path(api: str, version: str) -> Path:
    return _REPO_ROOT / "schemas" / api / f"{version}.effective.yaml"


def _packaged_spec_text(api: str, version: str) -> str | None:
    try:
        resource = files("gs1belu_mpm_upload").joinpath("_specs", api, f"{version}.effective.yaml")
    except (ModuleNotFoundError, FileNotFoundError):
        return None

    with as_file(resource) as path:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")


def _load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Effective spec not found: {path}. Run `just gen` first to produce the "
            "git-ignored effective spec from the pristine vendor original + overlay."
        )
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_effective_spec(api: str, version: str, *, path_override_env: str | None = None) -> dict[str, Any]:
    override = os.environ.get(path_override_env) if path_override_env else None
    if override:
        return _load_yaml_file(Path(override))

    packaged_text = _packaged_spec_text(api, version)
    if packaged_text is not None:
        return yaml.safe_load(packaged_text)

    return _load_yaml_file(_default_spec_path(api, version))
