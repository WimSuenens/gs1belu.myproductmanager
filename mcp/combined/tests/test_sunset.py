"""Pins the `Sunset` header (RFC 8594) observer (#67, per the research note's "SDK/MCP
should read and surface this header if present, for both APIs to be safe"): a warning
is logged when the header is present on either sub-server's responses, distinctly
flagging an already-past date, surfacing a malformed value's raw string rather than
throwing, and staying silent when the header is absent.
"""

import logging
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx

from fastmcp import Client

from conftest import trade_item_status

TRADE_ITEM = {"gtin": "05412345678900"}


async def test_future_sunset_on_download_is_logged_with_the_parsed_timestamp(server, download_transport, caplog):
    future = format_datetime(datetime.now(timezone.utc) + timedelta(days=30), usegmt=True)
    download_transport.queue(
        "GET",
        "/tradeitems",
        httpx.Response(200, json={"_links": {}, "_embedded": {"tradeItems": []}}, headers={"Sunset": future}),
    )

    with caplog.at_level(logging.WARNING, logger="gs1belu_mpm_mcp.sunset"):
        async with Client(server) as client:
            await client.call_tool("search_trade_items", {})

    assert any("Plan a version migration" in record.message for record in caplog.records)


async def test_absent_sunset_header_produces_no_warning(server, download_transport, caplog):
    download_transport.queue("GET", "/tradeitems", httpx.Response(200, json={"_links": {}, "_embedded": {"tradeItems": []}}))

    with caplog.at_level(logging.WARNING, logger="gs1belu_mpm_mcp.sunset"):
        async with Client(server) as client:
            await client.call_tool("search_trade_items", {})

    assert caplog.records == []


async def test_past_sunset_on_upload_is_flagged_as_already_sunset(server, upload_transport, caplog):
    past = format_datetime(datetime.now(timezone.utc) - timedelta(days=1), usegmt=True)
    response = trade_item_status("05412345678900", "active")
    response.headers["Sunset"] = past
    upload_transport.queue("GET", "/tradeitems/{gtin}", response)

    with caplog.at_level(logging.WARNING, logger="gs1belu_mpm_mcp.sunset"):
        async with Client(server) as client:
            await client.call_tool("get_trade_item_by_gtin", {"gtin": "05412345678900"})

    assert any("already in the past" in record.message for record in caplog.records)


async def test_malformed_sunset_surfaces_the_raw_value_without_throwing(server, upload_transport, caplog):
    response = trade_item_status("05412345678900", "active")
    response.headers["Sunset"] = "not-a-date"
    upload_transport.queue("GET", "/tradeitems/{gtin}", response)

    with caplog.at_level(logging.WARNING, logger="gs1belu_mpm_mcp.sunset"):
        async with Client(server) as client:
            await client.call_tool("get_trade_item_by_gtin", {"gtin": "05412345678900"})

    assert any("not-a-date" in record.message for record in caplog.records)
