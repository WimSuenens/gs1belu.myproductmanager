"""Server configuration loaded from environment variables — no raw base-URL knob.

Per-sub-server credential sets (Upload, Download) are never assumed shared (#9's
`credential set`), and `environment` is the only knob that selects host + derives
`audience` (see :mod:`gs1belu_mpm_mcp.environment`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from .environment import DEFAULT_API_VERSION, Environment


class ConfigError(RuntimeError):
    """A required environment variable is missing or holds an invalid value."""


@dataclass(frozen=True)
class CredentialSet:
    client_id: str
    client_secret: str
    subscription_key: str


@dataclass(frozen=True)
class ServerConfig:
    environment: Environment
    api_version: str
    upload_credentials: CredentialSet
    download_credentials: CredentialSet

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ServerConfig":
        source = os.environ if env is None else env

        def require(name: str) -> str:
            value = source.get(name)
            if not value:
                raise ConfigError(f"Missing required environment variable: {name}")
            return value

        raw_environment = require("GS1BELU_ENVIRONMENT").strip().lower()
        try:
            environment = Environment(raw_environment)
        except ValueError as exc:
            valid = ", ".join(e.value for e in Environment)
            raise ConfigError(f"GS1BELU_ENVIRONMENT={raw_environment!r} is not one of: {valid}") from exc

        api_version = source.get("GS1BELU_API_VERSION") or DEFAULT_API_VERSION

        return cls(
            environment=environment,
            api_version=api_version,
            upload_credentials=CredentialSet(
                client_id=require("GS1BELU_UPLOAD_CLIENT_ID"),
                client_secret=require("GS1BELU_UPLOAD_CLIENT_SECRET"),
                subscription_key=require("GS1BELU_UPLOAD_SUBSCRIPTION_KEY"),
            ),
            download_credentials=CredentialSet(
                client_id=require("GS1BELU_DOWNLOAD_CLIENT_ID"),
                client_secret=require("GS1BELU_DOWNLOAD_CLIENT_SECRET"),
                subscription_key=require("GS1BELU_DOWNLOAD_SUBSCRIPTION_KEY"),
            ),
        )
