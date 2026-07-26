"""Loads the git-ignored effective specs (`schemas/<api>/<version>.effective.yaml`)
that `just gen` produces from the pristine vendor originals + overlay — the same
artifact Kiota reads for the SDKs (`CONTEXT.md`'s `effective spec`). No MCP-specific
schema prep: this only locates and parses the file, it never builds one.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _default_spec_path(api: str, version: str) -> Path:
    return _REPO_ROOT / "schemas" / api / f"{version}.effective.yaml"


def load_effective_spec(api: str, version: str, *, path_override_env: str | None = None) -> dict[str, Any]:
    override = os.environ.get(path_override_env) if path_override_env else None
    path = Path(override) if override else _default_spec_path(api, version)

    if not path.is_file():
        raise FileNotFoundError(
            f"Effective spec not found: {path}. Run `just gen` first to produce the "
            "git-ignored effective spec from the pristine vendor original + overlay."
        )

    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
