"""Verifies the two-layer auth (#9's design, Python leg) directly against `Gs1BeluAuth`
with a bare `httpx.AsyncClient` — no FastMCP server needed now that this is verified
once here rather than duplicated per server (#79's Testing Decisions: shared-module
tests run once at the workspace root against `shared/`)."""

import asyncio

import httpx
import pytest

from _shared.auth import Gs1BeluAuth
from _shared.config import CredentialSet

CREDENTIALS = CredentialSet(client_id="a-client", client_secret="a-secret", subscription_key="a-subscription-key")
TOKEN_ENDPOINT = "https://login-uat.gs1belu.org/oauth/token"
AUDIENCE = "https://api-uat.gs1belu.org/"
TOKEN_HOST = "login-uat.gs1belu.org"


class _FakeTransport(httpx.AsyncBaseTransport):
    def __init__(self) -> None:
        self.token_response = httpx.Response(200, json={"access_token": "token-0", "expires_in": 3600})
        self.token_call_count = 0
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.host == TOKEN_HOST:
            self.token_call_count += 1
            return self.token_response
        return httpx.Response(200, json={"ok": True})


def _api_requests(transport: _FakeTransport) -> list[httpx.Request]:
    return [r for r in transport.requests if r.url.host != TOKEN_HOST]


@pytest.fixture
def transport() -> _FakeTransport:
    return _FakeTransport()


@pytest.fixture
def auth(transport: _FakeTransport) -> Gs1BeluAuth:
    return Gs1BeluAuth(CREDENTIALS, TOKEN_ENDPOINT, AUDIENCE, transport=transport)


async def test_both_auth_layers_present_on_upstream_requests(auth, transport):
    async with httpx.AsyncClient(auth=auth, transport=transport) as client:
        await client.get("https://api-uat.gs1belu.org/tradeitems/05412345678900")

    [request] = _api_requests(transport)
    assert request.headers["Authorization"] == "Bearer token-0"
    assert request.headers["Ocp-Apim-Subscription-Key"] == "a-subscription-key"


async def test_subscription_key_never_appears_in_the_url(auth, transport):
    async with httpx.AsyncClient(auth=auth, transport=transport) as client:
        await client.get("https://api-uat.gs1belu.org/tradeitems/05412345678900")

    [request] = _api_requests(transport)
    assert "a-subscription-key" not in str(request.url)


async def test_burst_of_concurrent_calls_triggers_exactly_one_token_fetch(auth, transport):
    async with httpx.AsyncClient(auth=auth, transport=transport) as client:
        await asyncio.gather(*[client.get("https://api-uat.gs1belu.org/x") for _ in range(5)])

    assert transport.token_call_count == 1


async def test_cached_token_is_reused_within_the_skew_window(auth, transport):
    transport.token_response = httpx.Response(200, json={"access_token": "long-lived-token", "expires_in": 3600})

    async with httpx.AsyncClient(auth=auth, transport=transport) as client:
        await client.get("https://api-uat.gs1belu.org/x")
        await client.get("https://api-uat.gs1belu.org/x")

    assert transport.token_call_count == 1


async def test_token_within_the_skew_margin_of_expiry_is_refetched(auth, transport):
    # expires_in (30s) is inside the default 60s skew margin, so the very next call
    # must already consider the cached token stale and re-fetch.
    transport.token_response = httpx.Response(200, json={"access_token": "short-lived-token", "expires_in": 30})

    async with httpx.AsyncClient(auth=auth, transport=transport) as client:
        await client.get("https://api-uat.gs1belu.org/x")
        await client.get("https://api-uat.gs1belu.org/x")

    assert transport.token_call_count == 2
