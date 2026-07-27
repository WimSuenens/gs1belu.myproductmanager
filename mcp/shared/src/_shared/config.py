"""The ``credential set`` shape — shared across both servers (#77), while *which*
prefix gets loaded (``GS1BELU_UPLOAD_*`` vs ``GS1BELU_DOWNLOAD_*``) stays each server's
own `config.py`'s call. Per-sub-server credential sets are never assumed shared (#9's
`credential set`): a role-scoped process reads exactly one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .environment import ConfigError


@dataclass(frozen=True)
class CredentialSet:
    client_id: str
    client_secret: str
    subscription_key: str

    @classmethod
    def from_env(cls, source: Mapping[str, str], prefix: str) -> "CredentialSet":
        """Load a credential set from ``{prefix}_CLIENT_ID`` / ``_CLIENT_SECRET`` /
        ``_SUBSCRIPTION_KEY``. ``prefix`` is passed without its trailing underscore,
        e.g. ``"GS1BELU_UPLOAD"``."""

        def require(name: str) -> str:
            value = source.get(name)
            if not value:
                raise ConfigError(f"Missing required environment variable: {name}")
            return value

        return cls(
            client_id=require(f"{prefix}_CLIENT_ID"),
            client_secret=require(f"{prefix}_CLIENT_SECRET"),
            subscription_key=require(f"{prefix}_SUBSCRIPTION_KEY"),
        )
