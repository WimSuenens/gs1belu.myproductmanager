"""`search_trade_items` — single bounded page + `nextCursor`, no server-side
auto-pagination (#46, per #11 §3). A broad Download filter can match up to 1000 items
server-side (`docs/research/gs1-api-facts.md` §4); this tool never auto-follows the
HAL `_links.next.href` into a flood of context — it returns the page GS1 sent back plus
the opaque `cursor` extracted from that href, so an agent pages only as far as it needs.

Hand-written rather than a literal `from_openapi()` rename: the raw HAL envelope
(`_links`/`_embedded`) is flattened into `{tradeItems, nextCursor}` so the pagination
token is a first-class field instead of something the agent must parse out of a URL.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx


def _extract_next_cursor(links: dict[str, Any] | None) -> str | None:
    if not links:
        return None
    next_href = (links.get("next") or {}).get("href")
    if not next_href:
        return None
    query = parse_qs(urlparse(next_href).query)
    values = query.get("cursor")
    return values[0] if values else None


async def search_trade_items(
    client: httpx.AsyncClient,
    *,
    information_provider_gln: str | None = None,
    since: str | None = None,
    gtin: str | None = None,
    brand_owner_default: bool | None = None,
    is_discontinued: bool | None = None,
    countries_of_sale: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if information_provider_gln is not None:
        params["informationProviderGLN"] = information_provider_gln
    if since is not None:
        params["since"] = since
    if gtin is not None:
        params["gtin"] = gtin
    if brand_owner_default is not None:
        params["brandOwnerDefault"] = brand_owner_default
    if is_discontinued is not None:
        params["isDiscontinued"] = is_discontinued
    if countries_of_sale is not None:
        params["countriesOfSale"] = countries_of_sale
    if cursor is not None:
        params["cursor"] = cursor
    if limit is not None:
        params["limit"] = limit

    response = await client.get("/tradeitems", params=params)
    body = response.json()

    return {
        "tradeItems": (body.get("_embedded") or {}).get("tradeItems", []),
        "nextCursor": _extract_next_cursor(body.get("_links")),
    }
