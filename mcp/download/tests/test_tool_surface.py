"""Pins the 1-tool recipient-role surface (#75, the Download half of the former
combined server's #46 3-tool surface): exactly `search_trade_items` — the raw
`get-tradeitems` (GET) must never surface as a tool of its own, and no Upload-role
tool is present.
"""

from fastmcp import Client


async def test_exactly_the_one_intended_tool(server):
    async with Client(server) as client:
        tools = await client.list_tools()

    assert {t.name for t in tools} == {"search_trade_items"}


async def test_raw_get_and_upload_tools_are_absent(server):
    async with Client(server) as client:
        tools = await client.list_tools()

    names = {t.name for t in tools}
    assert "get-tradeitems" not in names
    assert "upsert_and_await_validation" not in names, "Upload-role tool must never leak into the Download server"
    assert "get_trade_item_by_gtin" not in names
