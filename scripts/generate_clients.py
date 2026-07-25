"""Generate the four Kiota clients (`just gen` step 2) from the committed effective specs.

Reads `sdks/kiota-clients.json` — a declared manifest of the four clients (Upload +
Download x C# + TypeScript), each bound to exactly one API's effective spec, per the
"two documents, never merged" rule — and, for each entry, invokes the pinned Kiota
CLI (`sdks/kiota.version`) to (re)generate that client into its package's quarantined
`generated/` subtree.

This is not a native Kiota `workspace.json` consumed by a `kiota workspace`/`client`
command: the pinned CLI ships no such subcommands (only `generate`/`update` against
explicit flags). The manifest plays the role the spec envisioned for workspace.json
— the four clients declared as data, one place to edit to add a fifth — without
claiming Kiota-native tooling it doesn't have. See sdks/README.md.

Regeneration is driven with `--clean-output` so a stale file from a previous
generation (e.g. after a model is removed from the schema) cannot survive
undetected — this is what makes `regen-sync` a trustworthy drift guard.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "sdks" / "kiota-clients.json"
DEFAULT_VERSION_FILE = REPO_ROOT / "sdks" / "kiota.version"


class KiotaVersionMismatch(RuntimeError):
    """The `kiota` CLI on PATH does not match the pinned version."""


class GenerationError(RuntimeError):
    """A `kiota generate` invocation failed."""


@dataclass
class ClientSpec:
    id: str
    spec: Path
    language: str
    class_name: str
    namespace_name: str
    output: Path


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path)


def load_pinned_version(version_file: Path = DEFAULT_VERSION_FILE) -> str:
    return version_file.read_text(encoding="utf-8").strip()


def load_manifest(manifest_path: Path = DEFAULT_MANIFEST) -> list[ClientSpec]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [
        ClientSpec(
            id=entry["id"],
            spec=REPO_ROOT / entry["spec"],
            language=entry["language"],
            class_name=entry["className"],
            namespace_name=entry["namespaceName"],
            output=REPO_ROOT / entry["output"],
        )
        for entry in data["clients"]
    ]


def check_kiota_version(pinned: str) -> str:
    """Return the installed `kiota` version, raising if it doesn't match `pinned`."""
    try:
        result = subprocess.run(
            ["kiota", "--version"], capture_output=True, text=True, check=True
        )
    except FileNotFoundError as exc:
        raise KiotaVersionMismatch(
            "kiota CLI not found on PATH. Install the pinned version "
            f"({pinned}) so generation is reproducible."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise KiotaVersionMismatch(
            f"kiota --version exited {exc.returncode}: {exc.stderr}"
        ) from exc
    match = re.search(r"\d+\.\d+\.\d+", result.stdout)
    installed = match.group(0) if match else result.stdout.strip()
    if installed != pinned:
        raise KiotaVersionMismatch(
            f"kiota CLI on PATH is {installed!r}, but sdks/kiota.version pins "
            f"{pinned!r}. Install the pinned version so generation is reproducible."
        )
    return installed


def generate_client(client: ClientSpec) -> None:
    if not client.spec.is_file():
        raise FileNotFoundError(
            f"{client.id}: effective spec not found: {_rel(client.spec)} "
            "(run `just gen` step 1 first)."
        )
    client.output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "kiota",
        "generate",
        "--openapi",
        str(client.spec),
        "--language",
        client.language,
        "--class-name",
        client.class_name,
        "--namespace-name",
        client.namespace_name,
        "--output",
        str(client.output),
        "--clean-output",
        "--exclude-backward-compatible",
        "--log-level",
        "Warning",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GenerationError(
            f"{client.id}: kiota generate failed (exit {result.returncode}).\n"
            f"{result.stdout}\n{result.stderr}"
        )


def generate_clients(
    manifest_path: Path = DEFAULT_MANIFEST,
    version_file: Path = DEFAULT_VERSION_FILE,
) -> list[ClientSpec]:
    pinned = load_pinned_version(version_file)
    check_kiota_version(pinned)
    clients = load_manifest(manifest_path)
    for client in clients:
        generate_client(client)
    return clients


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--version-file", type=Path, default=DEFAULT_VERSION_FILE)
    args = parser.parse_args(argv)

    try:
        clients = generate_clients(args.manifest, args.version_file)
    except (KiotaVersionMismatch, GenerationError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for client in clients:
        print(f"✓ {client.id}: generated {client.language} client into {_rel(client.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
