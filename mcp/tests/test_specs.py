"""Pins the packaged-resource spec-resolution path (issue #70's regression test): a
future refactor that breaks bundling must fail loudly here, instead of silently
falling back to the `parents[3]` dev path on a machine where that happens to still
work by accident.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from gs1belu_mpm_mcp import specs

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGED_SPECS = Path(__file__).resolve().parents[1] / "src" / "gs1belu_mpm_mcp" / "_specs"


@pytest.fixture
def bundled_packaged_specs():
    """Reproduces what `hatch_build.py`'s `CustomBuildHook` does at build time — copies
    the effective specs into the packaged `_specs/` resource home — so this test can
    pin the packaged-resource branch without requiring a real `uv build`."""
    for api in ("upload", "download"):
        src = _REPO_ROOT / "schemas" / api / "v17.effective.yaml"
        dst = _PACKAGED_SPECS / api / "v17.effective.yaml"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    yield
    shutil.rmtree(_PACKAGED_SPECS, ignore_errors=True)


def test_resolves_packaged_spec_with_no_repo_checkout_on_path(monkeypatch, bundled_packaged_specs):
    # Simulates an installed-from-wheel environment: the repo-relative dev fallback
    # would raise FileNotFoundError if reached, so a passing result proves resolution
    # went through the packaged resource, not the dev fallback.
    monkeypatch.setattr(specs, "_REPO_ROOT", Path("/no-repo-checkout-here"))

    result = specs.load_effective_spec("upload", "v17")

    assert result["openapi"].startswith("3.")


def test_packaged_spec_still_defers_to_override_env(monkeypatch, bundled_packaged_specs, tmp_path):
    override = tmp_path / "override.effective.yaml"
    override.write_text("openapi: 3.1.0\ninfo:\n  title: override\n  version: v17\npaths: {}\n", encoding="utf-8")
    monkeypatch.setenv("GS1BELU_UPLOAD_SPEC_PATH_TEST", str(override))

    result = specs.load_effective_spec("upload", "v17", path_override_env="GS1BELU_UPLOAD_SPEC_PATH_TEST")

    assert result["info"]["title"] == "override"


def test_falls_back_to_repo_relative_path_when_not_packaged():
    # No bundled_packaged_specs fixture here — `_specs/` stays absent — and
    # `_REPO_ROOT` is untouched, so this exercises the real dev-checkout fallback.
    result = specs.load_effective_spec("download", "v17")

    assert result["openapi"].startswith("3.")
