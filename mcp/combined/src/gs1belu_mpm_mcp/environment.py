"""Pure derivation of API host, OAuth token host, and OAuth ``audience`` from an
:class:`Environment` + API segment (``upload``/``download``).

There is no caller-supplied host or base URL anywhere in the public config surface
(see :mod:`gs1belu_mpm_mcp.config`): a fumbled ``audience`` is exactly the GS1 manuals'
``access_denied`` failure, so every host is derived here, once, instead of being a
value a consumer can get wrong. Mirrors ``Gs1BeluEnvironmentResolver`` in the C#/TS
SDKs (#9/#36) — the same *derive-not-accept* contract, re-expressed for Python.
"""

from __future__ import annotations

import enum

DEFAULT_API_VERSION = "v17"


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
