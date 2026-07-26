"""Pins the 3-tool composite-only surface (#46, per #11 §1): exactly
`upsert_and_await_validation`, `get_trade_item_by_gtin`, `search_trade_items` — the raw
`upsert-tradeitem` (POST) and `get-tradeitems` (GET) operations must never surface as
tools of their own.
"""

from fastmcp import Client


async def test_exactly_the_three_intended_tools(server):
    async with Client(server) as client:
        tools = await client.list_tools()

    assert {t.name for t in tools} == {
        "upsert_and_await_validation",
        "get_trade_item_by_gtin",
        "search_trade_items",
    }


async def test_raw_post_and_raw_search_are_absent(server):
    async with Client(server) as client:
        tools = await client.list_tools()

    names = {t.name for t in tools}
    assert "upsert-tradeitem" not in names
    assert "get-tradeitems" not in names
