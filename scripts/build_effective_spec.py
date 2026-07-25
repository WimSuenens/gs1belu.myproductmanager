"""Build generator-ready *effective specs* from pristine GS1 BeLu MPM vendor specs.

For each API (`download`, `upload`) this reads the pristine vendor original
`schemas/<api>/<version>.yaml`, applies the committed OpenAPI Overlay 1.0 patch
`schemas/<api>/<version>.overlay.yaml` (if present and non-empty), and writes the
git-ignored sibling `schemas/<api>/<version>.effective.yaml` that the downstream
generators (Kiota, FastMCP) consume.

The vendor originals are only ever *read* here, never written — that is what keeps
them byte-exact as GS1 delivered them.

Each overlay action is self-verifying: its `x-assert-before` records the value the
target node is expected to still hold *before* patching. If the target is missing
or no longer holds that value (e.g. a future vendor version fixed the defect
upstream), the build fails with a non-zero exit naming the dead action, forcing the
maintainer to drop the now-dead patch rather than carry a silent no-op.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from jsonpath_ng.ext import parse as jsonpath_parse
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMAS_ROOT = REPO_ROOT / "schemas"
DEFAULT_APIS = ("download", "upload")
DEFAULT_VERSION = "v17"

_GENERATED_BANNER = (
    "# GENERATED — do not edit. Regenerate with `just gen`.\n"
    "# Source: {src} + {overlay}\n"
    "# This effective spec is a build artifact (git-ignored). The vendor original\n"
    "# and the overlay are the source of truth.\n"
)


class DeadPatchError(RuntimeError):
    """An overlay action no longer applies to its target (a dead patch)."""


def _yaml() -> YAML:
    yaml = YAML()  # round-trip loader: preserves key order and untouched formatting
    yaml.preserve_quotes = True
    yaml.width = 4096  # don't reflow long description lines
    return yaml


def _to_plain(value):
    """Normalise ruamel round-trip types to plain dict/list/scalars for comparison."""
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    return value


def _deep_merge(target: dict, update: dict) -> None:
    """Merge `update` into `target` in place (Overlay `update` semantics)."""
    for key, new_value in update.items():
        if (
            key in target
            and isinstance(target[key], dict)
            and isinstance(new_value, dict)
        ):
            _deep_merge(target[key], new_value)
        else:
            target[key] = new_value


@dataclass
class BuildResult:
    api: str
    source: Path
    overlay: Path | None
    output: Path
    applied: list[str] = field(default_factory=list)


def apply_overlay(doc, overlay: dict | None) -> list[str]:
    """Apply an OpenAPI Overlay document to `doc` in place.

    Returns the list of applied action descriptions. Raises `DeadPatchError` if any
    action's target is missing or no longer holds its `x-assert-before` value.
    """
    if not overlay:
        return []
    actions = overlay.get("actions") or []
    applied: list[str] = []
    for action in actions:
        target = action["target"]
        label = action.get("description", target)
        matches = jsonpath_parse(target).find(doc)
        if not matches:
            raise DeadPatchError(
                f"Dead overlay entry: {label!r} — its target matched no node "
                f"(target: {target}). Drop this action or fix its target."
            )
        expected = action.get("x-assert-before")
        for match in matches:
            node = match.value
            if expected is not None and _to_plain(node) != _to_plain(expected):
                raise DeadPatchError(
                    f"Dead overlay entry: {label!r} — target no longer holds the "
                    f"expected pre-patch value.\n"
                    f"  target:   {target}\n"
                    f"  expected: {_to_plain(expected)}\n"
                    f"  found:    {_to_plain(node)}\n"
                    f"The upstream spec may already be fixed; drop this action."
                )
            update = action.get("update")
            if isinstance(update, dict) and isinstance(node, dict):
                _deep_merge(node, update)
            elif update is not None:
                # Scalar/whole-node replacement is not needed by our overlays, but
                # support it for completeness.
                match.full_path.update(doc, update)
        applied.append(label)
    return applied


def build_api(
    api: str,
    schemas_root: Path = DEFAULT_SCHEMAS_ROOT,
    version: str = DEFAULT_VERSION,
) -> BuildResult:
    api_dir = schemas_root / api
    source = api_dir / f"{version}.yaml"
    overlay_path = api_dir / f"{version}.overlay.yaml"
    output = api_dir / f"{version}.effective.yaml"

    if not source.is_file():
        raise FileNotFoundError(f"Pristine vendor spec not found: {source}")

    yaml = _yaml()
    with source.open("r", encoding="utf-8") as fh:
        doc = yaml.load(fh)

    overlay = None
    if overlay_path.is_file():
        with overlay_path.open("r", encoding="utf-8") as fh:
            overlay = yaml.load(fh)

    applied = apply_overlay(doc, overlay)

    banner = _GENERATED_BANNER.format(
        src=source.relative_to(REPO_ROOT) if source.is_relative_to(REPO_ROOT) else source.name,
        overlay=(
            overlay_path.relative_to(REPO_ROOT)
            if overlay_path.is_file() and overlay_path.is_relative_to(REPO_ROOT)
            else "(none)"
        ),
    )
    with output.open("w", encoding="utf-8") as fh:
        fh.write(banner)
        yaml.dump(doc, fh)

    return BuildResult(
        api=api,
        source=source,
        overlay=overlay_path if overlay_path.is_file() else None,
        output=output,
        applied=applied,
    )


def build_effective_specs(
    schemas_root: Path = DEFAULT_SCHEMAS_ROOT,
    apis: tuple[str, ...] = DEFAULT_APIS,
    version: str = DEFAULT_VERSION,
) -> list[BuildResult]:
    return [build_api(api, schemas_root=schemas_root, version=version) for api in apis]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schemas-root",
        type=Path,
        default=DEFAULT_SCHEMAS_ROOT,
        help="Root directory holding <api>/<version>.yaml (default: repo schemas/).",
    )
    parser.add_argument("--version", default=DEFAULT_VERSION, help="Schema version stem (default: v17).")
    parser.add_argument(
        "--api",
        dest="apis",
        action="append",
        help="API to build (repeatable). Default: download, upload.",
    )
    args = parser.parse_args(argv)
    apis = tuple(args.apis) if args.apis else DEFAULT_APIS

    try:
        results = build_effective_specs(args.schemas_root, apis=apis, version=args.version)
    except DeadPatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for r in results:
        rel = r.output.relative_to(REPO_ROOT) if r.output.is_relative_to(REPO_ROOT) else r.output
        if r.applied:
            print(f"✓ {r.api}: wrote {rel} ({len(r.applied)} patch(es) applied)")
            for label in r.applied:
                print(f"    · {label}")
        else:
            print(f"✓ {r.api}: wrote {rel} (no patches — effective == pristine)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
