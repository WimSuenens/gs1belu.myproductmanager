"""Pins the `Sunset` header (RFC 8594) observer (#67) directly against `warn_on_sunset`:
a warning is logged when the header is present, distinctly flagging an already-past
date, surfacing a malformed value's raw string rather than throwing, and staying
silent when the header is absent."""

import logging
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx

from _shared.sunset import warn_on_sunset

LOGGER_NAME = "_shared.sunset"


async def test_future_sunset_is_logged_with_the_parsed_timestamp(caplog):
    future = format_datetime(datetime.now(timezone.utc) + timedelta(days=30), usegmt=True)
    response = httpx.Response(200, json={}, headers={"Sunset": future})

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        await warn_on_sunset(response)

    assert any("Plan a version migration" in record.message for record in caplog.records)


async def test_absent_sunset_header_produces_no_warning(caplog):
    response = httpx.Response(200, json={})

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        await warn_on_sunset(response)

    assert caplog.records == []


async def test_past_sunset_is_flagged_as_already_sunset(caplog):
    past = format_datetime(datetime.now(timezone.utc) - timedelta(days=1), usegmt=True)
    response = httpx.Response(200, json={}, headers={"Sunset": past})

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        await warn_on_sunset(response)

    assert any("already in the past" in record.message for record in caplog.records)


async def test_malformed_sunset_surfaces_the_raw_value_without_throwing(caplog):
    response = httpx.Response(200, json={}, headers={"Sunset": "not-a-date"})

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        await warn_on_sunset(response)

    assert any("not-a-date" in record.message for record in caplog.records)
