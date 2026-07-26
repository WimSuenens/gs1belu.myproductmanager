"""Assert the release/publish configuration is internally consistent (#53).

This does NOT perform a release or talk to any registry — that cannot be
exercised in CI without actually publishing (see issue #53's "Testing
Decisions"). Instead it statically proves:

1. Tag-prefix equivalence — the core invariant. A mismatch here is the
   "green release-PR merge publishes nothing" failure mode.
2. release-please-config.json <-> .release-please-manifest.json parity.
3. Each component's real version source is wired (npm `package.json`, the C#
   `x-release-please-version` annotation + its `extra-files` binding, the MCP
   `pyproject.toml` + `server.json` extra-files).
4. Registry metadata presence (license/readme/disclaimer/server.json shape).
"""

from __future__ import annotations

import pytest

import release_config as rc

# ---------------------------------------------------------------------------
# 1. Tag-prefix equivalence
# ---------------------------------------------------------------------------


def test_every_component_has_exactly_one_matching_publish_workflow():
    tag_globs_by_workflow = rc.all_publish_tag_globs()
    all_globs = [glob for globs in tag_globs_by_workflow.values() for glob in globs]

    for package_path in rc.packages():
        component = rc.component_of(package_path)
        expected_glob = rc.component_tag_prefix(component) + "*"
        matches = [wf for wf, globs in tag_globs_by_workflow.items() if expected_glob in globs]
        assert matches, (
            f"component '{component}' (package '{package_path}') derives tag prefix "
            f"'{expected_glob}' but no publish workflow triggers on it — a release-PR "
            f"merge for this package would tag and publish nothing."
        )
        assert len(matches) == 1, (
            f"component '{component}' tag prefix '{expected_glob}' is claimed by more "
            f"than one publish workflow: {matches}"
        )
    assert all_globs, "no publish workflow declares any push-tag trigger."


def test_every_publish_workflow_glob_maps_back_to_a_declared_component():
    components = {rc.component_of(p) for p in rc.packages()}
    expected_prefixes = {rc.component_tag_prefix(c) + "*" for c in components}

    for workflow, globs in rc.all_publish_tag_globs().items():
        for glob in globs:
            assert glob in expected_prefixes, (
                f"{workflow} triggers on tag glob '{glob}' which does not match any "
                f"release-please component's derived tag prefix — an orphan trigger "
                f"that can never fire from a real release."
            )


# ---------------------------------------------------------------------------
# 2. Config <-> manifest parity
# ---------------------------------------------------------------------------


def test_config_and_manifest_declare_the_same_packages():
    config_paths = set(rc.packages().keys())
    manifest_paths = set(rc.load_manifest().keys())
    assert config_paths == manifest_paths, (
        f"release-please-config.json and .release-please-manifest.json disagree on "
        f"packages: only in config={config_paths - manifest_paths}, "
        f"only in manifest={manifest_paths - config_paths}"
    )


# ---------------------------------------------------------------------------
# 3. Version-source wiring
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("package_path", rc.NPM_PACKAGES)
def test_npm_version_source_wired(package_path):
    package_json = rc.npm_package_json(package_path)
    assert isinstance(package_json.get("version"), str) and package_json["version"], (
        f"{package_path}/package.json has no bump-targetable 'version' string."
    )


@pytest.mark.parametrize("package_path,csproj_filename", rc.CSHARP_PACKAGES)
def test_csharp_version_source_wired(package_path, csproj_filename):
    text = rc.csharp_csproj_text(package_path, csproj_filename)
    assert "<Version>" in text, f"{csproj_filename} has no <Version> element for release-please to bump."
    assert rc.has_generic_version_annotation(text), (
        f"{csproj_filename} is missing the 'x-release-please-version' annotation "
        f"the generic extra-files updater matches on."
    )

    config = rc.packages()[package_path]
    extra_files = config.get("extra-files", [])
    matching = [ef for ef in extra_files if ef.get("path") == csproj_filename]
    assert matching, (
        f"release-please-config.json's '{package_path}' package has no extra-files "
        f"entry targeting '{csproj_filename}' — the annotated <Version> would never "
        f"actually be bumped by a release."
    )
    assert matching[0].get("type") == "generic", (
        f"extra-files entry for '{csproj_filename}' should use type 'generic' to match "
        f"the comment-annotation convention actually present in the file."
    )


def test_mcp_pyproject_version_source_wired():
    pyproject = rc.mcp_pyproject()
    version = pyproject.get("project", {}).get("version")
    assert isinstance(version, str) and version, "mcp/pyproject.toml has no [project].version."


def test_mcp_server_json_version_fields_wired_via_extra_files():
    config = rc.packages()[rc.MCP_PACKAGE]
    extra_files = config.get("extra-files", [])
    jsonpaths = {ef.get("jsonpath") for ef in extra_files if ef.get("path") == "server.json"}
    assert jsonpaths == {"$.version", "$.packages[0].version"}, (
        f"release-please-config.json's 'mcp' package must bump both server.json "
        f"version fields via extra-files (got jsonpaths={jsonpaths}), or a release "
        f"would leave server.json claiming a stale version."
    )

    server_json = rc.mcp_server_json()
    assert isinstance(server_json.get("version"), str)
    assert isinstance(server_json.get("packages", [{}])[0].get("version"), str)


# ---------------------------------------------------------------------------
# 4. Registry metadata presence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("package_path", rc.NPM_PACKAGES)
def test_npm_registry_metadata_present(package_path):
    package_json = rc.npm_package_json(package_path)
    assert package_json.get("publishConfig", {}).get("access") == "public", (
        f"{package_path}/package.json must set publishConfig.access=public — a scoped "
        f"package (@gs1belu/...) defaults to private publish otherwise."
    )
    assert "dist" in package_json.get("files", []), (
        f"{package_path}/package.json's 'files' allowlist must ship 'dist' (build output), "
        f"not the src/generated/ sources."
    )
    assert package_json.get("repository", {}).get("directory") == package_path, (
        f"{package_path}/package.json's repository.directory must point back at its own "
        f"subtree so the registry links to the right monorepo path."
    )
    assert not package_json.get("private"), f"{package_path}/package.json must not set private:true."


def test_csharp_quality_bundle_present():
    props = rc.directory_build_props_text()
    for required in (
        "<PackageLicenseExpression>MIT</PackageLicenseExpression>",
        "<PackageReadmeFile>",
        "<RepositoryUrl>",
        "<PackageProjectUrl>",
        "<IncludeSymbols>true</IncludeSymbols>",
        "<SymbolPackageFormat>snupkg</SymbolPackageFormat>",
        "<Deterministic>true</Deterministic>",
        "Microsoft.SourceLink.GitHub",
    ):
        assert required in props, f"Directory.Build.props is missing required quality-bundle property: {required!r}"


@pytest.mark.parametrize("package_path,csproj_filename", rc.CSHARP_PACKAGES)
def test_csharp_package_ships_its_own_readme(package_path, csproj_filename):
    text = rc.csharp_csproj_text(package_path, csproj_filename)
    assert 'Include="README.md"' in text and 'Pack="true"' in text, (
        f"{csproj_filename} must pack its own README.md into the nupkg (PackageReadmeFile "
        f"in Directory.Build.props only sets the *filename*; each project packs its own file)."
    )


def test_mcp_server_json_shape():
    server_json = rc.mcp_server_json()
    assert server_json.get("name") == "io.github.WimSuenens/gs1belu-mpm"
    assert server_json.get("description")
    assert server_json.get("version")

    packages_list = server_json.get("packages")
    assert isinstance(packages_list, list) and packages_list, "server.json must declare at least one package."
    entry = packages_list[0]
    assert entry.get("registryType") == "pypi"
    assert entry.get("identifier") == "gs1belu-mpm-mcp"
    assert entry.get("runtimeHint") == "uvx"
    assert entry.get("transport", {}).get("type") == "stdio"


def test_mcp_name_marker_present_in_pypi_facing_readme():
    assert rc.MCP_NAME_MARKER in rc.mcp_readme_text(), (
        "mcp/README.md (the README pyproject.toml ships to PyPI) must carry the "
        f"'{rc.MCP_NAME_MARKER}' marker from the first publish, or MCP-registry "
        f"ownership validation fails without a throwaway version bump to fix it."
    )


@pytest.mark.parametrize("readme_path", rc.PACKAGE_READMES)
def test_disclaimer_present_in_every_package_readme(readme_path):
    text = rc.normalize_markdown_whitespace(rc.package_readme_text(readme_path))
    assert rc.DISCLAIMER_SNIPPET in text, (
        f"{readme_path} is missing the 'unofficial / not affiliated with GS1' disclaimer "
        f"required on every registry-facing package README."
    )


def test_repo_root_mit_license_present():
    license_text = (rc.REPO_ROOT / "LICENSE").read_text()
    assert "MIT License" in license_text
