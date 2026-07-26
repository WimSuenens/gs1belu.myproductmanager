"""Verifies the two-layer auth (#9's design, Python leg) *through* the server, by
counting token-endpoint hits and inspecting emitted headers on the shared fake
transport — never the `Gs1BeluAuth` instance's private cache state (per the issue's
Testing Decisions: treat the auth layer as verified through observable behavior at the
FastMCP seam).
"""

import asyncio

import httpx
from fastmcp import Client

from conftest import trade_item_status


def _api_requests(transport):
    """Requests that went to the upstream API host, excluding the token endpoint."""
    return [r for r in transport.requests if r.url.host != transport.token_host]


async def test_both_auth_layers_present_on_upstream_requests(server, upload_transport):
    upload_transport.queue("GET", "/tradeitems/{gtin}", trade_item_status("05412345678900", "active"))

    async with Client(server) as client:
        await client.call_tool("get_trade_item_by_gtin", {"gtin": "05412345678900"})

    [request] = _api_requests(upload_transport)
    assert request.headers["Authorization"] == "Bearer token-0"
    assert request.headers["Ocp-Apim-Subscription-Key"] == "upload-subscription-key"


async def test_subscription_key_never_appears_in_the_url(server, upload_transport):
    upload_transport.queue("GET", "/tradeitems/{gtin}", trade_item_status("05412345678900", "active"))

    async with Client(server) as client:
        await client.call_tool("get_trade_item_by_gtin", {"gtin": "05412345678900"})

    [request] = _api_requests(upload_transport)
    assert "upload-subscription-key" not in str(request.url)


async def test_burst_of_concurrent_calls_triggers_exactly_one_token_fetch(server, upload_transport):
    for _ in range(5):
        upload_transport.queue("GET", "/tradeitems/{gtin}", trade_item_status("05412345678900", "active"))

    async with Client(server) as client:
        await asyncio.gather(
            *[client.call_tool("get_trade_item_by_gtin", {"gtin": "05412345678900"}) for _ in range(5)]
        )

    assert upload_transport.token_call_count == 1


async def test_cached_token_is_reused_within_the_skew_window(server, upload_transport):
    upload_transport.token_response = httpx.Response(200, json={"access_token": "long-lived-token", "expires_in": 3600})
    for _ in range(2):
        upload_transport.queue("GET", "/tradeitems/{gtin}", trade_item_status("05412345678900", "active"))

    async with Client(server) as client:
        await client.call_tool("get_trade_item_by_gtin", {"gtin": "05412345678900"})
        await client.call_tool("get_trade_item_by_gtin", {"gtin": "05412345678900"})

    assert upload_transport.token_call_count == 1


async def test_token_within_the_skew_margin_of_expiry_is_refetched(server, upload_transport):
    # expires_in (30s) is inside the default 60s skew margin, so the very next call
    # must already consider the cached token stale and re-fetch — pinning "expiry
    # taken from the mocked expires_in" without needing to sleep out a real window.
    upload_transport.token_response = httpx.Response(200, json={"access_token": "short-lived-token", "expires_in": 30})
    for _ in range(2):
        upload_transport.queue("GET", "/tradeitems/{gtin}", trade_item_status("05412345678900", "active"))

    async with Client(server) as client:
        await client.call_tool("get_trade_item_by_gtin", {"gtin": "05412345678900"})
        await client.call_tool("get_trade_item_by_gtin", {"gtin": "05412345678900"})

    assert upload_transport.token_call_count == 2
