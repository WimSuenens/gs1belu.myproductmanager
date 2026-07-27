"""Server configuration loaded from environment variables — no raw base-URL knob.

One credential set per process (#77's split): this server reads only
`GS1BELU_UPLOAD_*`, never `GS1BELU_DOWNLOAD_*` — a data-supplier integrator
configures exactly the credentials their role holds. `parse_environment()` and
`CredentialSet` are single-sourced in `_shared/` so this server and its Download
sibling can never drift on host derivation or credential-field shape.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from ._shared.config import CredentialSet
from ._shared.environment import DEFAULT_API_VERSION, ConfigError, Environment, parse_environment

CREDENTIAL_PREFIX = "GS1BELU_UPLOAD"

__all__ = ["ConfigError", "CredentialSet", "Environment", "ServerConfig"]


@dataclass(frozen=True)
class ServerConfig:
    environment: Environment
    api_version: str
    credentials: CredentialSet

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ServerConfig":
        source = os.environ if env is None else env

        environment = parse_environment(source)
        api_version = source.get("GS1BELU_API_VERSION") or DEFAULT_API_VERSION
        credentials = CredentialSet.from_env(source, CREDENTIAL_PREFIX)

        return cls(environment=environment, api_version=api_version, credentials=credentials)
