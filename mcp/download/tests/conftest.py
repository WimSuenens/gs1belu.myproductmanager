"""Shared fixtures for the Download MCP server's in-memory test suite (#75/#76 split
of the former combined `mcp/tests/conftest.py`) — one seam: `build_download_server()`
driven through FastMCP's in-memory `Client`, with a fake `httpx` transport and a mocked
token endpoint injected under the server's `AsyncClient`. No network, no live GS1, no
subprocess.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Callable

import httpx
import pytest

from gs1belu_mpm_download._shared.config import CredentialSet
from gs1belu_mpm_download._shared.environment import Environment
from gs1belu_mpm_download.config import ServerConfig
from gs1belu_mpm_download.server import build_download_server

Responder = httpx.Response | Callable[[httpx.Request], httpx.Response]


def _route_key(method: str, path: str) -> tuple[str, str]:
    """Normalizes a request path (which carries the full
    `/myproductmanager/download/v17` base prefix) down to a route key."""
    if path.rstrip("/").split("/")[-1] == "tradeitems":
        return (method.upper(), "/tradeitems")
    return (method.upper(), path)


class FakeTransport(httpx.AsyncBaseTransport):
    """Routes requests by (method, path): token-endpoint calls are counted and answered
    from `token_response`; everything else is popped off a per-route FIFO queue of
    canned responses set up via `queue()`."""

    def __init__(self, *, token_host: str) -> None:
        self.token_host = token_host
        self.token_response = httpx.Response(200, json={"access_token": "token-0", "expires_in": 3600})
        self.token_call_count = 0
        self.requests: list[httpx.Request] = []
        self._queues: dict[tuple[str, str], deque[Responder]] = defaultdict(deque)
        self._last: dict[tuple[str, str], Responder] = {}

    def queue(self, method: str, path: str, response: Responder) -> None:
        self._queues[_route_key(method, path)].append(response)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)

        if request.url.host == self.token_host:
            self.token_call_count += 1
            return self.token_response

        key = _route_key(request.method, request.url.path)
        queue = self._queues.get(key)
        if queue:
            responder = queue.popleft()
            self._last[key] = responder
        else:
            responder = self._last.get(key)
            if responder is None:
                raise AssertionError(f"FakeTransport: no queued response for {key}")

        return responder(request) if callable(responder) else responder


@pytest.fixture
def server_config() -> ServerConfig:
    return ServerConfig(
        environment=Environment.UAT,
        api_version="v17",
        credentials=CredentialSet(
            client_id="download-client",
            client_secret="download-secret",
            subscription_key="download-subscription-key",
        ),
    )


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport(token_host="login-uat.gs1belu.org")


@pytest.fixture
def server(server_config, transport):
    return build_download_server(config=server_config, transport=transport)
