"""Two-layer `httpx.Auth` — the Python leg of #9's auth design (already shipped in
C#/TS by #36; this re-expresses the same contract once, in Python).

On every request it (a) stamps the static `Ocp-Apim-Subscription-Key` **header**
(never the spec's query-param alternative, so the secret never lands in a URL or log)
and (b) stamps a cached OAuth2 client-credentials **Bearer** token, fetched from the
token endpoint and proactively refreshed on a skew margin before the token's runtime
`expires_in` elapses — never a hardcoded 12h/24h figure, since the GS1 manuals
themselves disagree on which of those it is.

Concurrent callers coalesce onto a single token fetch via double-checked locking: every
caller re-checks the cache after acquiring the lock, so a burst that arrives before the
first fetch completes finds the now-populated cache and never re-fetches.
"""

from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator, Callable

import httpx

from .config import CredentialSet

DEFAULT_SKEW_MARGIN_SECONDS = 60.0


class Gs1BeluAuth(httpx.Auth):
    def __init__(
        self,
        credentials: CredentialSet,
        token_endpoint: str,
        audience: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        skew_margin: float = DEFAULT_SKEW_MARGIN_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._credentials = credentials
        self._token_endpoint = token_endpoint
        self._audience = audience
        self._skew_margin = skew_margin
        self._clock = clock
        self._token_client = httpx.AsyncClient(transport=transport)
        self._lock = asyncio.Lock()
        self._cached_token: str | None = None
        self._cached_expires_at: float = float("-inf")

    async def async_auth_flow(self, request: httpx.Request) -> AsyncIterator[httpx.Request]:
        token = await self._get_token()
        request.headers["Authorization"] = f"Bearer {token}"
        request.headers["Ocp-Apim-Subscription-Key"] = self._credentials.subscription_key
        yield request

    async def aclose(self) -> None:
        await self._token_client.aclose()

    def _is_cache_valid(self) -> bool:
        return self._cached_token is not None and self._clock() < self._cached_expires_at - self._skew_margin

    async def _get_token(self) -> str:
        if self._is_cache_valid():
            return self._cached_token  # type: ignore[return-value]

        async with self._lock:
            if self._is_cache_valid():
                return self._cached_token  # type: ignore[return-value]
            return await self._fetch_token()

    async def _fetch_token(self) -> str:
        response = await self._token_client.post(
            self._token_endpoint,
            data={
                "grant_type": "client_credentials",
                "client_id": self._credentials.client_id,
                "client_secret": self._credentials.client_secret,
                "audience": self._audience,
            },
        )
        response.raise_for_status()
        body = response.json()
        access_token = body.get("access_token")
        if not access_token:
            raise RuntimeError("The GS1 token endpoint returned no access_token.")

        self._cached_token = access_token
        self._cached_expires_at = self._clock() + float(body.get("expires_in", 0))
        return access_token
