"""`upsert_and_await_validation` — the hand-written composite (#46, per #11 solution).

`POST /tradeitems` always answers `201` with an empty body regardless of data errors;
the true accept/reject signal only arrives via the follow-up `GET /tradeitems/{gtin}`
once `metaData.status` leaves `pendingValidation`
(`docs/research/gs1-api-facts.md` §5). This composite runs that POST -> poll loop and
returns the settled verdict, so an agent never has to interpret a bare `201`.

The poll is bounded on both axes: `poll_interval` paces individual polls (well under
the 10 req/s cap the shared client's `RateLimiter` already enforces), and `timeout`
caps the overall wait so a stuck validation can never hang the tool forever.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

import httpx
from fastmcp.exceptions import ToolError

DEFAULT_POLL_INTERVAL_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 120.0

PENDING_STATUS = "pendingValidation"


async def upsert_and_await_validation(
    client: httpx.AsyncClient,
    trade_item: dict[str, Any],
    *,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> dict[str, Any]:
    gtin = trade_item.get("gtin")
    if not gtin:
        raise ToolError("tradeItem.gtin is required.")

    await client.post("/tradeitems", json=trade_item)

    deadline = clock() + timeout
    while True:
        response = await client.get(f"/tradeitems/{gtin}")
        body = response.json()
        meta_data = body.get("metaData") or {}
        status = meta_data.get("status")

        if status != PENDING_STATUS:
            return {
                "gtin": gtin,
                "status": status,
                "validationResults": meta_data.get("validationResults", []),
            }

        if clock() >= deadline:
            raise ToolError(
                f"Validation for GTIN '{gtin}' did not leave {PENDING_STATUS!r} within {timeout}s."
            )

        await sleep(poll_interval)
