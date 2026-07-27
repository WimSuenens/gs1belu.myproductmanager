"""Pins the 2-tool provider-role surface (#75, the Upload half of the former combined
server's #46 3-tool surface): exactly `upsert_and_await_validation`,
`get_trade_item_by_gtin` — the raw `upsert-tradeitem` (POST) must never surface as a
tool of its own, and no Download-role tool is present.
"""

from fastmcp import Client


async def test_exactly_the_two_intended_tools(server):
    async with Client(server) as client:
        tools = await client.list_tools()

    assert {t.name for t in tools} == {
        "upsert_and_await_validation",
        "get_trade_item_by_gtin",
    }


async def test_raw_post_is_absent(server):
    async with Client(server) as client:
        tools = await client.list_tools()

    names = {t.name for t in tools}
    assert "upsert-tradeitem" not in names
    assert "search_trade_items" not in names, "Download-role tool must never leak into the Upload server"
