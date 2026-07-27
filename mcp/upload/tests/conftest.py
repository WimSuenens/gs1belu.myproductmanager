"""Shared fixtures for the Upload MCP server's in-memory test suite (#75/#76 split of
the former combined `mcp/tests/conftest.py`) — one seam: `build_upload_server()`
driven through FastMCP's in-memory `Client`, with a fake `httpx` transport and a mocked
token endpoint injected under the server's `AsyncClient`. No network, no live GS1, no
subprocess.
"""

from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Callable

import httpx
import pytest
import yaml

from gs1belu_mpm_upload._shared.config import CredentialSet
from gs1belu_mpm_upload._shared.environment import Environment
from gs1belu_mpm_upload.config import ServerConfig
from gs1belu_mpm_upload.server import build_upload_server

REPO_ROOT = Path(__file__).resolve().parents[3]

Responder = httpx.Response | Callable[[httpx.Request], httpx.Response]


def _load_effective_spec(api: str) -> dict[str, Any]:
    path = REPO_ROOT / "schemas" / api / "v17.effective.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"{path} is missing — run `just gen` before the test suite.")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _route_key(method: str, path: str) -> tuple[str, str]:
    """Normalizes a request path (which carries the full `/myproductmanager/upload/v17`
    base prefix) down to a route key, collapsing the dynamic `{gtin}` segment of
    `/tradeitems/{gtin}` so tests can queue responses without knowing the exact GTIN a
    composite call will use."""
    segments = path.rstrip("/").split("/")
    if segments[-1] == "tradeitems":
        return (method.upper(), "/tradeitems")
    if len(segments) >= 2 and segments[-2] == "tradeitems":
        return (method.upper(), "/tradeitems/{gtin}")
    return (method.upper(), path)


class FakeTransport(httpx.AsyncBaseTransport):
    """Routes requests by (method, path): token-endpoint calls are counted and answered
    from `token_response`; everything else is popped off a per-route FIFO queue of
    canned responses set up via `queue()`. Once a route's queue is drained, the last
    response popped for it keeps being replayed (so a test doesn't have to predict
    exactly how many times a poll loop will call in)."""

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
def upload_spec() -> dict[str, Any]:
    return _load_effective_spec("upload")


@pytest.fixture
def server_config() -> ServerConfig:
    return ServerConfig(
        environment=Environment.UAT,
        api_version="v17",
        credentials=CredentialSet(
            client_id="upload-client",
            client_secret="upload-secret",
            subscription_key="upload-subscription-key",
        ),
    )


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport(token_host="login-uat.gs1belu.org")


@pytest.fixture
def server(upload_spec, server_config, transport):
    return build_upload_server(
        upload_spec=upload_spec,
        config=server_config,
        transport=transport,
        # Fast bounds in every test — no test needs to observe the real 2s/120s
        # production defaults, and the timeout test needs this small to run quickly.
        composite_poll_interval=0.01,
        composite_timeout=0.05,
    )


def validation_result(status: int, details: list[dict[str, str]]) -> httpx.Response:
    return httpx.Response(status, json={"status": status, "details": details})


def problem_details(status: int, title: str, detail: str) -> httpx.Response:
    return httpx.Response(status, json={"type": None, "title": title, "status": status, "detail": detail, "instance": None})


def trade_item_status(gtin: str, status: str, validation_results: list[dict[str, str]] | None = None) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "gtin": gtin,
            "isConsumerUnit": True,
            "unitDescriptorCode": "BASE_UNIT_OR_EACH",
            "informationProvider": {"gln": "1234567890128", "partyName": "Acme"},
            "countriesOfSale": ["BE"],
            "brandName": "Acme Brand",
            "tradeItemClassification": {"gpcCategoryCode": "10000000"},
            "metaData": {
                "modified": {"date": "2026-01-01T00:00:00Z"},
                "created": {"date": "2026-01-01T00:00:00Z"},
                "status": status,
                "validationResults": validation_results or [],
            },
        },
    )
