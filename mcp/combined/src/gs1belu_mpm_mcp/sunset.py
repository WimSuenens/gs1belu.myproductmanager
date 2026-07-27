"""Observes the `Sunset` header (RFC 8594) GS1 uses to announce that an API version will
stop responding (issue #67, per the Download manual's documented best practice: "monitor
this header" and "prepare to process dates in the past"). Purely observational — it
never alters, retries, or fails a request. Attached as an httpx `event_hooks={"response":
[warn_on_sunset]}` hook on each sub-server's shared `httpx.AsyncClient` in `clients.py`,
ordered before `raise_structured_error` so a sunset is still surfaced even on an
error response.

Reports through the standard library `logging` module — this package's existing default
logger, and the idiomatic Python analog of the SDKs' dependency-free callback seam
(`LoggingHandler`/`LoggingMiddleware`). The structured fields land in `LogRecord.__dict__`
via `extra`, so an operator can wire real monitoring with a `logging.Handler`/filter
instead of only scraping the formatted message.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SunsetNotice:
    raw: str
    parsed_at: datetime | None
    is_past: bool


def _parse(raw: str) -> datetime | None:
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _format_message(notice: SunsetNotice) -> str:
    if notice.parsed_at is None:
        return f'Sunset: GS1 announced an API-version sunset but the header value could not be parsed as an HTTP-date: "{notice.raw}".'

    if notice.is_past:
        return (
            f"Sunset: this API version's announced sunset ({notice.parsed_at.isoformat()}) "
            "is already in the past — it may stop responding at any time."
        )

    days = (notice.parsed_at - datetime.now(timezone.utc)).days
    return (
        f"Sunset: GS1 announced this API version will stop responding at "
        f"{notice.parsed_at.isoformat()} (in {days} days). Plan a version migration."
    )


async def warn_on_sunset(response: httpx.Response) -> None:
    """httpx response hook: logs a warning when a `Sunset` header is present. A response
    without the header costs nothing beyond the lookup."""
    raw = response.headers.get("sunset")
    if raw is None:
        return

    parsed_at = _parse(raw)
    is_past = parsed_at is not None and parsed_at <= datetime.now(timezone.utc)
    notice = SunsetNotice(raw=raw, parsed_at=parsed_at, is_past=is_past)

    logger.warning(
        _format_message(notice),
        extra={
            "sunset_raw": notice.raw,
            "sunset_parsed_at": notice.parsed_at.isoformat() if notice.parsed_at else None,
            "sunset_is_past": notice.is_past,
        },
    )
