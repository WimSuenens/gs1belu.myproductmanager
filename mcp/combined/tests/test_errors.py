"""Pins the structured non-2xx error mapping (#46, per #11 §4): a `validationResult`
400 becomes `{status, details[]}`; RFC-7807 `problemDetails` on 401/403/404 becomes
`{title, status, detail}` — never an opaque `raise_for_status()` string.
"""

import json

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from conftest import problem_details, validation_result

TRADE_ITEM = {"gtin": "05412345678900"}


async def test_400_on_post_maps_to_validation_result_shape(server, upload_transport):
    upload_transport.queue(
        "POST",
        "/tradeitems",
        validation_result(400, [{"severity": "error", "code": "VR_FMCGB2C_0257", "message": "malformed request"}]),
    )

    async with Client(server) as client:
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool("upsert_and_await_validation", {"trade_item": TRADE_ITEM})

    payload = json.loads(str(exc_info.value))
    assert payload == {
        "status": 400,
        "details": [{"severity": "error", "code": "VR_FMCGB2C_0257", "message": "malformed request"}],
    }


async def test_401_on_get_maps_to_problem_details_shape(server, upload_transport):
    upload_transport.queue("GET", "/tradeitems/{gtin}", problem_details(401, "Unauthorized", "invalid or expired token"))

    async with Client(server) as client:
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool("get_trade_item_by_gtin", {"gtin": "05412345678900"})

    payload = json.loads(str(exc_info.value))
    assert payload == {"title": "Unauthorized", "status": 401, "detail": "invalid or expired token"}


async def test_404_on_get_maps_to_problem_details_shape(server, upload_transport):
    upload_transport.queue("GET", "/tradeitems/{gtin}", problem_details(404, "Not Found", "no trade item for this GTIN"))

    async with Client(server) as client:
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool("get_trade_item_by_gtin", {"gtin": "05412345678900"})

    payload = json.loads(str(exc_info.value))
    assert payload == {"title": "Not Found", "status": 404, "detail": "no trade item for this GTIN"}


async def test_403_on_search_maps_to_problem_details_shape(server, download_transport):
    download_transport.queue("GET", "/tradeitems", problem_details(403, "Forbidden", "subscription key not authorized"))

    async with Client(server) as client:
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool("search_trade_items", {})

    payload = json.loads(str(exc_info.value))
    assert payload == {"title": "Forbidden", "status": 403, "detail": "subscription key not authorized"}
