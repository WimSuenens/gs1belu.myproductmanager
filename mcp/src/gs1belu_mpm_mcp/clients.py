"""Builds the one authenticated `httpx.AsyncClient` each sub-server (and its
hand-written tools) shares — base URL derived from `environment`, `Gs1BeluAuth` for
both credential layers, `RateLimiter` for the 10 req/s cap, and the structured-error
response hook. `transport` is the one testability seam: omit it for real network use,
inject an `httpx.MockTransport` in tests so both the upstream API host and the token
host route through the same fake — it is never exposed on the server's public config.
"""

from __future__ import annotations

import httpx

from .auth import Gs1BeluAuth
from .config import CredentialSet
from .environment import Environment, audience, base_url, token_endpoint
from .errors import raise_structured_error
from .ratelimit import RateLimiter


def build_upstream_client(
    *,
    environment: Environment,
    api_segment: str,
    api_version: str,
    credentials: CredentialSet,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    auth = Gs1BeluAuth(
        credentials=credentials,
        token_endpoint=token_endpoint(environment),
        audience=audience(environment),
        transport=transport,
    )
    rate_limiter = RateLimiter()

    return httpx.AsyncClient(
        base_url=base_url(environment, api_segment, api_version),
        auth=auth,
        transport=transport,
        event_hooks={
            "request": [rate_limiter.on_request],
            "response": [raise_structured_error],
        },
    )
