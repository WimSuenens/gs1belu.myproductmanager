"""Assembles the parent FastMCP server: one `from_openapi()` sub-server per effective
spec, mounted prefix-less onto a parent (server composition, never a merged document —
CONTEXT.md's "two documents, never merged" structural rule). The 3-tool
composite-only surface (#46, per #11 §1):

- `upsert_and_await_validation` — hand-written, upload sub-server.
- `get_trade_item_by_gtin` — generated (upload `get-tradeitem`), renamed via `mcp_names`.
- `search_trade_items` — hand-written, download sub-server.

The raw `POST /tradeitems` (`upsert-tradeitem`) is excluded via `RouteMap` so the
fire-and-forget write (`201` with no validation verdict) never reaches the agent. The
raw `GET /tradeitems` (`get-tradeitems`) is excluded too since its HAL envelope is
replaced by `search_trade_items`'s bounded `{tradeItems, nextCursor}` shape rather than
a literal rename. `validate_output=False` on both sub-servers: the upload spec's
`tradeItem` response schema doesn't declare the `metaData` field the real API returns
(a known spec/manual gap — see `docs/research/gs1-api-facts.md` §5), so strict output
validation would fight reality rather than reflect it.

`composite_poll_interval`/`composite_timeout` are `build_server()`-level seams (not
part of `upsert_and_await_validation`'s own tool schema — the issue's tool signature is
just `upsert_and_await_validation(tradeItem)`), so tests can pin a tiny bound instead of
waiting out the real default timeout.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, RouteMap

from .clients import build_upstream_client
from .composite import DEFAULT_POLL_INTERVAL_SECONDS, DEFAULT_TIMEOUT_SECONDS, upsert_and_await_validation
from .config import ServerConfig
from .search import search_trade_items

PARENT_SERVER_NAME = "gs1belu-mpm"

_EXCLUDE_UPLOAD_POST = RouteMap(methods=["POST"], pattern=r"^/tradeitems$", mcp_type=MCPType.EXCLUDE)
_EXCLUDE_DOWNLOAD_GET = RouteMap(methods=["GET"], pattern=r"^/tradeitems$", mcp_type=MCPType.EXCLUDE)


def build_server(
    *,
    upload_spec: dict[str, Any],
    download_spec: dict[str, Any],
    config: ServerConfig,
    upload_transport: httpx.AsyncBaseTransport | None = None,
    download_transport: httpx.AsyncBaseTransport | None = None,
    composite_poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    composite_timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> FastMCP:
    upload_client = build_upstream_client(
        environment=config.environment,
        api_segment="upload",
        api_version=config.api_version,
        credentials=config.upload_credentials,
        transport=upload_transport,
    )
    download_client = build_upstream_client(
        environment=config.environment,
        api_segment="download",
        api_version=config.api_version,
        credentials=config.download_credentials,
        transport=download_transport,
    )

    upload_server = FastMCP.from_openapi(
        upload_spec,
        client=upload_client,
        route_maps=[_EXCLUDE_UPLOAD_POST],
        mcp_names={"get-tradeitem": "get_trade_item_by_gtin"},
        validate_output=False,
    )

    @upload_server.tool(name="upsert_and_await_validation")
    async def _upsert_and_await_validation(trade_item: dict[str, Any]) -> dict[str, Any]:
        """Submit a trade item and poll until GS1 settles its validation verdict.

        `trade_item` is the full GS1 tradeItem payload (must include `gtin`,
        `isConsumerUnit`, `unitDescriptorCode`, `informationProvider`,
        `tradeItemClassification`, `countriesOfSale`, `brandName`, per the Upload
        OpenAPI spec). The raw POST always answers `201` with no body regardless of
        data errors — this tool is the only way to learn whether GS1 actually accepted
        the item, returning `{gtin, status, validationResults}` once `metaData.status`
        leaves `pendingValidation`.
        """
        return await upsert_and_await_validation(
            upload_client, trade_item, poll_interval=composite_poll_interval, timeout=composite_timeout
        )

    download_server = FastMCP.from_openapi(
        download_spec,
        client=download_client,
        route_maps=[_EXCLUDE_DOWNLOAD_GET],
        validate_output=False,
    )

    @download_server.tool(name="search_trade_items")
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
            download_client,
            information_provider_gln=informationProviderGLN,
            since=since,
            gtin=gtin,
            brand_owner_default=brandOwnerDefault,
            is_discontinued=isDiscontinued,
            countries_of_sale=countriesOfSale,
            cursor=cursor,
            limit=limit,
        )

    parent = FastMCP(PARENT_SERVER_NAME)
    parent.mount(upload_server)
    parent.mount(download_server)
    return parent
