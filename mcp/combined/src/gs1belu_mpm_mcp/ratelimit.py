"""Sliding-window request pacing to stay under the API's confirmed 10 req/s cap
(`docs/research/gs1-api-facts.md` §3). Mirrors `RateLimitHandler.cs`: a request that
would exceed the cap waits until the oldest timestamp in the window ages out, rather
than firing and risking a throttle response — this is what keeps the composite's poll
loop (and any burst of tool calls) from tripping rate limiting.

Attached as an httpx `event_hooks={"request": [...]}` hook on each sub-server's shared
client, so it paces every outgoing request through that client uniformly.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Awaitable, Callable

import httpx


class RateLimiter:
    def __init__(
        self,
        *,
        max_requests: int = 10,
        window: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._max_requests = max_requests
        self._window = window
        self._clock = clock
        self._sleep = sleep
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = self._clock()
                while self._timestamps and now - self._timestamps[0] >= self._window:
                    self._timestamps.popleft()

                if len(self._timestamps) < self._max_requests:
                    self._timestamps.append(now)
                    return

                delay = self._window - (now - self._timestamps[0])

            if delay > 0:
                await self._sleep(delay)

    async def on_request(self, request: httpx.Request) -> None:
        await self.acquire()
