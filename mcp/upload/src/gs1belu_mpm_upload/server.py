"""Assembles the standalone Upload MCP server: `FastMCP.from_openapi()` over the
upload effective spec, `RouteMap`-excluding the raw `POST /tradeitems` so the
fire-and-forget write (`201` with no validation verdict) never reaches the agent, plus
the hand-written `upsert_and_await_validation` composite tool. The 2-tool provider-role
surface (#75, the Upload half of the former combined server's #46 3-tool surface):

- `upsert_and_await_validation` — hand-written composite.
- `get_trade_item_by_gtin` — generated (upload `get-tradeitem`), renamed via `mcp_names`.

`validate_output=False` is load-bearing, not vestigial: the upload spec's `tradeItem`
response schema omits the `metaData` field the real API returns (the known spec/manual
gap, `docs/research/gs1-api-facts.md` §5), so strict output validation would fight
reality.

`composite_poll_interval`/`composite_timeout` are `build_upload_server()`-level test
seams (not part of `upsert_and_await_validation`'s own tool schema), so tests can pin a
tiny bound instead of waiting out the real default timeout.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, RouteMap

from ._shared.clients import build_upstream_client
from .composite import DEFAULT_POLL_INTERVAL_SECONDS, DEFAULT_TIMEOUT_SECONDS, upsert_and_await_validation
from .config import ServerConfig

SERVER_NAME = "gs1belu-mpm-upload"

_EXCLUDE_UPLOAD_POST = RouteMap(methods=["POST"], pattern=r"^/tradeitems$", mcp_type=MCPType.EXCLUDE)


def build_upload_server(
    *,
    upload_spec: dict[str, Any],
    config: ServerConfig,
    transport: httpx.AsyncBaseTransport | None = None,
    composite_poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    composite_timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> FastMCP:
    client = build_upstream_client(
        environment=config.environment,
        api_segment="upload",
        api_version=config.api_version,
        credentials=config.credentials,
        transport=transport,
    )

    server = FastMCP.from_openapi(
        upload_spec,
        client=client,
        route_maps=[_EXCLUDE_UPLOAD_POST],
        mcp_names={"get-tradeitem": "get_trade_item_by_gtin"},
        validate_output=False,
        name=SERVER_NAME,
    )

    @server.tool(name="upsert_and_await_validation")
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
            client, trade_item, poll_interval=composite_poll_interval, timeout=composite_timeout
        )

    return server
