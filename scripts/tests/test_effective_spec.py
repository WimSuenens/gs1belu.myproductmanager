"""Behavioural tests for the schema-prep effective-spec build.

These assert the *external behaviour of the build*: given committed inputs, what
does the emitted effective spec contain, and does the build fail when it should.
They treat the overlay/JSONPath/YAML libraries as vendor and never test their
internals. This is the repo's first test seam; downstream specs (SDKs, MCP server)
follow the same philosophy — assert the produced artifact / observable behaviour.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from ruamel.yaml import YAML

import build_effective_spec as bes

REPO_ROOT = bes.REPO_ROOT
REAL_SCHEMAS = bes.DEFAULT_SCHEMAS_ROOT
VERSION = bes.DEFAULT_VERSION

_safe_yaml = YAML(typ="safe")


def _load(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return _safe_yaml.load(fh)


def _limit_schema(doc: dict) -> dict:
    params = doc["paths"]["/tradeitems"]["get"]["parameters"]
    (limit,) = [p for p in params if p["name"] == "limit"]
    return limit["schema"]


@pytest.fixture
def schemas_root(tmp_path: Path) -> Path:
    """An isolated copy of the pristine vendor specs + overlays to build against."""
    root = tmp_path / "schemas"
    for api in ("download", "upload"):
        dst = root / api
        dst.mkdir(parents=True)
        for name in (f"{VERSION}.yaml", f"{VERSION}.overlay.yaml"):
            src = REAL_SCHEMAS / api / name
            if src.is_file():
                shutil.copy2(src, dst / name)
    return root


# --- golden assertions on the emitted artifact -------------------------------


def test_download_limit_is_patched_to_int32(schemas_root: Path):
    bes.build_api("download", schemas_root=schemas_root)
    effective = _load(schemas_root / "download" / f"{VERSION}.effective.yaml")
    assert _limit_schema(effective) == {"type": "integer", "format": "int32"}


def test_download_decimal_values_are_preserved(schemas_root: Path):
    bes.build_api("download", schemas_root=schemas_root)
    effective = _load(schemas_root / "download" / f"{VERSION}.effective.yaml")
    schemas = effective["components"]["schemas"]
    assert schemas["measurement"]["properties"]["value"] == {"type": "number"}
    assert schemas["currency"]["properties"]["value"] == {"type": "number"}


def test_upload_is_a_semantic_no_op(schemas_root: Path):
    bes.build_api("upload", schemas_root=schemas_root)
    pristine = _load(schemas_root / "upload" / f"{VERSION}.yaml")
    effective = _load(schemas_root / "upload" / f"{VERSION}.effective.yaml")
    assert effective == pristine


def test_absent_upload_overlay_is_handled_gracefully(schemas_root: Path):
    # Remove the (empty) upload overlay entirely — the pipeline must still produce
    # an effective spec identical to the pristine original, with no failure.
    (schemas_root / "upload" / f"{VERSION}.overlay.yaml").unlink()
    result = bes.build_api("upload", schemas_root=schemas_root)
    assert result.applied == []
    pristine = _load(schemas_root / "upload" / f"{VERSION}.yaml")
    effective = _load(result.output)
    assert effective == pristine


def test_originals_are_untouched_by_the_build(schemas_root: Path):
    before = {
        api: (schemas_root / api / f"{VERSION}.yaml").read_bytes()
        for api in ("download", "upload")
    }
    bes.build_effective_specs(schemas_root)
    for api, original_bytes in before.items():
        after = (schemas_root / api / f"{VERSION}.yaml").read_bytes()
        assert after == original_bytes, f"{api} vendor original was modified by the build"


def test_build_is_idempotent(schemas_root: Path):
    bes.build_effective_specs(schemas_root)
    first = {
        api: (schemas_root / api / f"{VERSION}.effective.yaml").read_bytes()
        for api in ("download", "upload")
    }
    bes.build_effective_specs(schemas_root)
    for api, first_bytes in first.items():
        second = (schemas_root / api / f"{VERSION}.effective.yaml").read_bytes()
        assert second == first_bytes, f"{api} effective spec differs across identical builds"


# --- dead-patch guard --------------------------------------------------------


def _mutate_limit_to_integer(schemas_root: Path) -> None:
    """Simulate a v18 upstream fix: limit is already integer in the vendor file."""
    yaml = YAML()
    path = schemas_root / "download" / f"{VERSION}.yaml"
    with path.open("r", encoding="utf-8") as fh:
        doc = yaml.load(fh)
    schema = _limit_schema(doc)
    del schema["type"]
    schema["type"] = "integer"
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(doc, fh)


def test_dead_patch_guard_raises_when_target_already_fixed(schemas_root: Path):
    _mutate_limit_to_integer(schemas_root)
    with pytest.raises(bes.DeadPatchError) as excinfo:
        bes.build_api("download", schemas_root=schemas_root)
    # The failure names the dead overlay entry so the maintainer knows what to drop.
    assert "limit" in str(excinfo.value)


def test_cli_exits_nonzero_and_names_dead_entry(schemas_root: Path, capsys):
    _mutate_limit_to_integer(schemas_root)
    exit_code = bes.main(["--schemas-root", str(schemas_root), "--api", "download"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "Dead overlay entry" in err
    assert "limit" in err


def test_dead_patch_guard_leaves_no_effective_artifact(schemas_root: Path):
    _mutate_limit_to_integer(schemas_root)
    with pytest.raises(bes.DeadPatchError):
        bes.build_api("download", schemas_root=schemas_root)
    assert not (schemas_root / "download" / f"{VERSION}.effective.yaml").exists()


# --- repository invariant ----------------------------------------------------


def test_effective_specs_are_gitignored():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.effective.yaml" in gitignore
