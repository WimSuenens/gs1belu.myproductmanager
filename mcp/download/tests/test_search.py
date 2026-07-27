"""Pins `search_trade_items`'s context-safety contract (#46, user stories 7-9, carried
verbatim through the #82 split): one bounded page plus an opaque `nextCursor`, never
server-side auto-pagination — even against a canned multi-page HAL response that has
further pages available.
"""

import httpx

from fastmcp import Client

HAL_PAGE_ONE = {
    "_links": {"next": {"href": "https://api-uat.gs1belu.org/myproductmanager/download/v17/tradeitems?cursor=5d1e3dba81020c1bb4e47c87&limit=10"}},
    "_embedded": {
        "tradeItems": [
            {"gtin": "05412345678900", "metaData": {"status": "active"}},
            {"gtin": "05412345678917", "metaData": {"status": "active"}},
        ]
    },
}

HAL_LAST_PAGE = {
    "_links": {},
    "_embedded": {"tradeItems": [{"gtin": "05412345678924", "metaData": {"status": "active"}}]},
}


async def test_returns_one_page_plus_next_cursor_without_auto_pagination(server, transport):
    transport.queue("GET", "/tradeitems", httpx.Response(200, json=HAL_PAGE_ONE))

    async with Client(server) as client:
        result = await client.call_tool("search_trade_items", {"informationProviderGLN": "1234567890128"})

    assert result.structured_content == {
        "tradeItems": HAL_PAGE_ONE["_embedded"]["tradeItems"],
        "nextCursor": "5d1e3dba81020c1bb4e47c87",
    }
    api_requests = [r for r in transport.requests if r.url.host != transport.token_host]
    assert len(api_requests) == 1, "must not auto-follow _links.next itself"


async def test_next_cursor_is_null_on_the_last_page(server, transport):
    transport.queue("GET", "/tradeitems", httpx.Response(200, json=HAL_LAST_PAGE))

    async with Client(server) as client:
        result = await client.call_tool("search_trade_items", {})

    assert result.structured_content["nextCursor"] is None


async def test_a_follow_up_call_with_the_cursor_advances(server, transport):
    transport.queue("GET", "/tradeitems", httpx.Response(200, json=HAL_PAGE_ONE))
    transport.queue("GET", "/tradeitems", httpx.Response(200, json=HAL_LAST_PAGE))

    async with Client(server) as client:
        first = await client.call_tool("search_trade_items", {})
        second = await client.call_tool("search_trade_items", {"cursor": first.structured_content["nextCursor"]})

    assert second.structured_content["nextCursor"] is None
    second_request = transport.requests[-1]
    assert second_request.url.params["cursor"] == "5d1e3dba81020c1bb4e47c87"
