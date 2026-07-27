"""Pure derivation of API host, OAuth token host, and OAuth ``audience`` from an
:class:`Environment` + API segment (``upload``/``download``), plus the env-var parse
that turns ``GS1BELU_ENVIRONMENT`` into that enum.

There is no caller-supplied host or base URL anywhere in the public config surface: a
fumbled ``audience`` is exactly the GS1 manuals' ``access_denied`` failure, so every
host is derived here, once, instead of being a value a consumer can get wrong. Mirrors
``Gs1BeluEnvironmentResolver`` in the C#/TS SDKs (#9/#36) — the same *derive-not-accept*
contract, re-expressed for Python.

Vendored byte-identically into each of the Upload/Download servers' wheels as
``_shared`` (map #76) — this is the safety-critical single-sourcing #77 calls for: the
``GS1BELU_ENVIRONMENT`` -> OAuth-``audience`` parse can never drift between the two
servers because both build from this one copy.
"""

from __future__ import annotations

import enum
from typing import Mapping

DEFAULT_API_VERSION = "v17"


class ConfigError(RuntimeError):
    """A required environment variable is missing or holds an invalid value."""


class Environment(enum.Enum):
    UAT = "uat"
    PROD = "prod"


_API_HOSTS = {
    Environment.UAT: "api-uat.gs1belu.org",
    Environment.PROD: "api.gs1belu.org",
}

_TOKEN_HOSTS = {
    Environment.UAT: "login-uat.gs1belu.org",
    Environment.PROD: "login.gs1belu.org",
}


def api_host(environment: Environment) -> str:
    return _API_HOSTS[environment]


def token_host(environment: Environment) -> str:
    return _TOKEN_HOSTS[environment]


def audience(environment: Environment) -> str:
    """The OAuth ``audience`` claim, with the mandatory trailing slash baked in."""
    return f"https://{api_host(environment)}/"


def token_endpoint(environment: Environment) -> str:
    return f"https://{token_host(environment)}/oauth/token"


def base_url(environment: Environment, api_segment: str, api_version: str = DEFAULT_API_VERSION) -> str:
    return f"https://{api_host(environment)}/myproductmanager/{api_segment}/{api_version}"


def parse_environment(source: Mapping[str, str]) -> Environment:
    """Require + validate ``GS1BELU_ENVIRONMENT`` from an env-var-shaped mapping."""
    raw = source.get("GS1BELU_ENVIRONMENT")
    if not raw:
        raise ConfigError("Missing required environment variable: GS1BELU_ENVIRONMENT")

    raw = raw.strip().lower()
    try:
        return Environment(raw)
    except ValueError as exc:
        valid = ", ".join(e.value for e in Environment)
        raise ConfigError(f"GS1BELU_ENVIRONMENT={raw!r} is not one of: {valid}") from exc
