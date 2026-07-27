"""Structured non-2xx error mapping (issue #46, per #11 §4).

A non-2xx upstream response is parsed into a `fastmcp.exceptions.ToolError` carrying a
JSON-encoded structured payload, instead of an opaque `raise_for_status()` string — the
signal an agent needs to self-correct:

- `validationResult` shape (`{severity, code, message}` details) -> `{status, details[]}`.
- RFC-7807 `problemDetails` shape -> `{title, status, detail}`.

Attached as an httpx `event_hooks={"response": [raise_structured_error]}` hook on each
server's shared `httpx.AsyncClient`, so every call through that client — generated
tools and the hand-written composite/search tools alike — gets the same mapping. The
hook raises before `response.raise_for_status()` ever runs inside FastMCP's generated
`OpenAPITool.run()`, so the structured `ToolError` reaches the agent verbatim rather
than being flattened into a generic HTTP error string.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from fastmcp.exceptions import ToolError


def _is_validation_result(body: Any) -> bool:
    """Shape-sniff the `validationResult` schema: `{status, details: [{severity, code, message}]}`."""
    return isinstance(body, dict) and isinstance(body.get("details"), list)


def _validation_result_payload(status_code: int, body: dict) -> dict:
    return {
        "status": body.get("status", status_code),
        "details": [
            {
                "severity": detail.get("severity"),
                "code": detail.get("code"),
                "message": detail.get("message"),
            }
            for detail in body.get("details", [])
            if isinstance(detail, dict)
        ],
    }


def _problem_details_payload(status_code: int, body: dict | None) -> dict:
    body = body or {}
    return {
        "title": body.get("title"),
        "status": body.get("status", status_code),
        "detail": body.get("detail"),
    }


async def raise_structured_error(response: httpx.Response) -> None:
    """httpx response hook: raise a structured `ToolError` for any non-2xx response."""
    if response.status_code < 400:
        return

    await response.aread()
    try:
        body = response.json()
    except ValueError:
        body = None

    if _is_validation_result(body):
        payload = _validation_result_payload(response.status_code, body)
    else:
        payload = _problem_details_payload(response.status_code, body if isinstance(body, dict) else None)
        if body is None and response.text:
            payload["detail"] = payload["detail"] or response.text

    raise ToolError(json.dumps(payload))
