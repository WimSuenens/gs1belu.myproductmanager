"""Pins `upsert_and_await_validation`'s contract (#46, user stories 3-5): submits the
item, polls until `metaData.status` leaves `pendingValidation`, returns the settled
verdict, and honors a bounded overall timeout rather than spinning forever.
"""

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from conftest import trade_item_status

TRADE_ITEM = {
    "gtin": "05412345678900",
    "isConsumerUnit": True,
    "unitDescriptorCode": "BASE_UNIT_OR_EACH",
    "informationProvider": {"gln": "1234567890128", "partyName": "Acme"},
    "countriesOfSale": ["BE"],
    "brandName": "Acme Brand",
    "tradeItemClassification": {"gpcCategoryCode": "10000000"},
}


async def test_returns_the_settled_verdict_once_validation_leaves_pending(server, upload_transport):
    upload_transport.queue("POST", "/tradeitems", httpx.Response(201, headers={"Location": "/tradeitems/05412345678900"}))
    upload_transport.queue("GET", "/tradeitems/{gtin}", trade_item_status(TRADE_ITEM["gtin"], "pendingValidation"))
    upload_transport.queue("GET", "/tradeitems/{gtin}", trade_item_status(TRADE_ITEM["gtin"], "pendingValidation"))
    upload_transport.queue(
        "GET",
        "/tradeitems/{gtin}",
        trade_item_status(
            TRADE_ITEM["gtin"],
            "active",
            [{"severity": "warning", "code": "VR_FMCGB2C_0315", "message": "no image is provided"}],
        ),
    )

    async with Client(server) as client:
        result = await client.call_tool("upsert_and_await_validation", {"trade_item": TRADE_ITEM})

    assert result.structured_content == {
        "gtin": TRADE_ITEM["gtin"],
        "status": "active",
        "validationResults": [{"severity": "warning", "code": "VR_FMCGB2C_0315", "message": "no image is provided"}],
    }

    get_calls = [r for r in upload_transport.requests if r.method == "GET"]
    assert len(get_calls) == 3, "must stop polling as soon as status leaves pendingValidation"


async def test_incomplete_verdict_is_returned_not_raised(server, upload_transport):
    upload_transport.queue("POST", "/tradeitems", httpx.Response(201))
    upload_transport.queue(
        "GET",
        "/tradeitems/{gtin}",
        trade_item_status(
            TRADE_ITEM["gtin"],
            "incomplete",
            [{"severity": "error", "code": "VR_FMCGB2C_0257", "message": "no image is provided"}],
        ),
    )

    async with Client(server) as client:
        result = await client.call_tool("upsert_and_await_validation", {"trade_item": TRADE_ITEM})

    assert result.structured_content["status"] == "incomplete"


async def test_bounded_timeout_stops_an_unbounded_spin(server, upload_transport):
    # The `server` fixture wires a 0.05s composite_timeout / 0.01s composite_poll_interval
    # (see conftest.py) so this observes the bound without waiting out the 120s default.
    upload_transport.queue("POST", "/tradeitems", httpx.Response(201))
    upload_transport.queue("GET", "/tradeitems/{gtin}", trade_item_status(TRADE_ITEM["gtin"], "pendingValidation"))

    async with Client(server) as client:
        with pytest.raises(ToolError, match="pendingValidation"):
            await client.call_tool("upsert_and_await_validation", {"trade_item": TRADE_ITEM})
