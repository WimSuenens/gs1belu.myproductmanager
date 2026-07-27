"""Assembles the standalone Download MCP server: a **plain `FastMCP`** (#75 — no
`from_openapi()` here; the raw `GET /tradeitems` is hand-written as
`search_trade_items` so `from_openapi` would generate zero tools on this side — the
raw operation is excluded, and the search tool is a flattened rename, not a literal
one). The 1-tool recipient-role surface: `search_trade_items(filters..., cursor?,
limit?)` — single bounded page plus an opaque `nextCursor`, never server-side
auto-pagination.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastmcp import FastMCP

from ._shared.clients import build_upstream_client
from .config import ServerConfig
from .search import search_trade_items

SERVER_NAME = "gs1belu-mpm-download"


def build_download_server(
    *,
    config: ServerConfig,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastMCP:
    client = build_upstream_client(
        environment=config.environment,
        api_segment="download",
        api_version=config.api_version,
        credentials=config.credentials,
        transport=transport,
    )

    server = FastMCP(SERVER_NAME)

    @server.tool(name="search_trade_items")
    async def _search_trade_items(
        informationProviderGLN: str | None = None,
        since: str | None = None,
        gtin: str | None = None,
        brandOwnerDefault: bool | None = None,
        isDiscontinued: bool | None = None,
        countriesOfSale: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Search trade items, returning one bounded page plus an opaque `nextCursor`.

        A broad filter can match up to 1000 items server-side; this tool never
        auto-paginates that into the caller's context. Re-call with `cursor` set to
        the previous response's `nextCursor` to continue; `nextCursor` is `null` on
        the last page.
        """
        return await search_trade_items(
            client,
            information_provider_gln=informationProviderGLN,
            since=since,
            gtin=gtin,
            brand_owner_default=brandOwnerDefault,
            is_discontinued=isDiscontinued,
            countries_of_sale=countriesOfSale,
            cursor=cursor,
            limit=limit,
        )

    return server
