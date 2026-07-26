"""Read-only helpers over the release/publish configuration (#53).

These load `release-please-config.json`, `.release-please-manifest.json`, the three
publish workflows, and each package's registry-facing metadata, and expose them as
plain Python data for `scripts/tests/test_release_assert.py` to assert against.

Nothing here mutates anything or talks to a registry — the whole point of
`release-assert` is to prove the *configuration* is internally consistent (the
tag-prefix contract above all) without performing a real release. See the
"Testing Decisions" section of issue #53 for what is and isn't in scope here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

REPO_ROOT = Path(__file__).resolve().parents[1]

RELEASE_PLEASE_CONFIG = REPO_ROOT / "release-please-config.json"
RELEASE_PLEASE_MANIFEST = REPO_ROOT / ".release-please-manifest.json"

WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
PUBLISH_WORKFLOWS = ("publish-npm.yml", "publish-csharp.yml", "publish-mcp.yml")

# The five packages release-please manages, as (package-path, kind) — kind drives
# which version-source/metadata check applies. Kept as one table so a sixth
# package is a one-line addition here plus a `packages` entry in the config.
NPM_PACKAGES = (
    "sdks/typescript/packages/mpm-upload",
    "sdks/typescript/packages/mpm-download",
)
CSHARP_PACKAGES = (
    ("sdks/dotnet/Gs1Belu.MyProductManager.Upload", "Gs1Belu.MyProductManager.Upload.csproj"),
    ("sdks/dotnet/Gs1Belu.MyProductManager.Download", "Gs1Belu.MyProductManager.Download.csproj"),
)
MCP_PACKAGE = "mcp"

# Every package README a registry will render — the disclaimer must be in all five.
PACKAGE_READMES = (
    "sdks/dotnet/Gs1Belu.MyProductManager.Upload/README.md",
    "sdks/dotnet/Gs1Belu.MyProductManager.Download/README.md",
    "sdks/typescript/packages/mpm-upload/README.md",
    "sdks/typescript/packages/mpm-download/README.md",
    "mcp/README.md",
)

DISCLAIMER_SNIPPET = "not affiliated with, endorsed by, or supported by GS1"
MCP_NAME_MARKER = "mcp-name: io.github.wimsuenens/gs1belu-mpm"

_yaml = YAML(typ="safe")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def load_toml(path: Path) -> Any:
    return tomllib.loads(path.read_text())


def load_release_please_config() -> dict[str, Any]:
    return load_json(RELEASE_PLEASE_CONFIG)


def load_manifest() -> dict[str, str]:
    return load_json(RELEASE_PLEASE_MANIFEST)


def packages() -> dict[str, dict[str, Any]]:
    """`{package-path: package-config}` from release-please-config.json."""
    return load_release_please_config().get("packages", {})


def component_of(package_path: str) -> str:
    config = packages()[package_path]
    # release-please falls back to the package path itself when `component` is
    # omitted; every package here sets it explicitly, but stay honest about the
    # fallback rather than assuming.
    return config.get("component", package_path)


def component_tag_prefix(component: str) -> str:
    """The tag prefix release-please derives for a component (`include-component-in-tag`)."""
    return f"{component}-v"


def load_workflow_tag_globs(workflow_filename: str) -> list[str]:
    """The `on.push.tags` glob list a publish workflow triggers on.

    PyYAML/ruamel's YAML-1.1 resolver treats a bare top-level `on:` key as the
    boolean `True` unless quoted — the well-known GitHub Actions YAML gotcha —
    so this checks both the string and boolean keys rather than assuming one.
    """
    data = _yaml.load((WORKFLOWS_DIR / workflow_filename).read_text())
    on_section = data.get("on", data.get(True, {}))
    push = on_section.get("push", {}) if isinstance(on_section, dict) else {}
    return list(push.get("tags", []))


def all_publish_tag_globs() -> dict[str, list[str]]:
    """`{workflow_filename: [tag globs]}` for every publish workflow."""
    return {wf: load_workflow_tag_globs(wf) for wf in PUBLISH_WORKFLOWS}


def npm_package_json(package_path: str) -> dict[str, Any]:
    return load_json(REPO_ROOT / package_path / "package.json")


def csharp_csproj_text(package_path: str, csproj_filename: str) -> str:
    return (REPO_ROOT / package_path / csproj_filename).read_text()


def directory_build_props_text() -> str:
    return (REPO_ROOT / "sdks" / "dotnet" / "Directory.Build.props").read_text()


def mcp_pyproject() -> dict[str, Any]:
    return load_toml(REPO_ROOT / "mcp" / "pyproject.toml")


def mcp_server_json() -> dict[str, Any]:
    return load_json(REPO_ROOT / "mcp" / "server.json")


def mcp_readme_text() -> str:
    return (REPO_ROOT / "mcp" / "README.md").read_text()


def package_readme_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text()


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_markdown_whitespace(text: str) -> str:
    """Collapse markdown blockquote line-wrapping (`> line one\\n> line two`) and
    any run of whitespace to single spaces, so a substring check for prose that
    happens to wrap across `>`-prefixed lines doesn't false-negative."""
    return _WHITESPACE_RE.sub(" ", text.replace(">", " ")).strip()


GENERIC_ANNOTATION_RE = re.compile(r"x-release-please-version\b")


def has_generic_version_annotation(text: str) -> bool:
    """Whether `text` carries the `x-release-please-version` annotation the
    `generic` extra-files updater looks for (see release-please's
    `src/updaters/generic.ts`: matched as a plain substring, comment-delimiter
    agnostic)."""
    return bool(GENERIC_ANNOTATION_RE.search(text))
