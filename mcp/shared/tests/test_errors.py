"""Pins the structured non-2xx error mapping (#46, per #11 §4) directly against
`raise_structured_error` — a `validationResult` 400 becomes `{status, details[]}`; RFC-
7807 `problemDetails` on 401/403/404 becomes `{title, status, detail}` — never an
opaque `raise_for_status()` string."""

import json

import httpx
import pytest
from fastmcp.exceptions import ToolError

from _shared.errors import raise_structured_error


async def test_2xx_is_a_noop():
    await raise_structured_error(httpx.Response(200, json={"ok": True}))


async def test_400_maps_to_validation_result_shape():
    response = httpx.Response(
        400,
        json={
            "status": 400,
            "details": [{"severity": "error", "code": "VR_FMCGB2C_0257", "message": "malformed request"}],
        },
    )

    with pytest.raises(ToolError) as exc_info:
        await raise_structured_error(response)

    assert json.loads(str(exc_info.value)) == {
        "status": 400,
        "details": [{"severity": "error", "code": "VR_FMCGB2C_0257", "message": "malformed request"}],
    }


async def test_401_maps_to_problem_details_shape():
    response = httpx.Response(
        401,
        json={"type": None, "title": "Unauthorized", "status": 401, "detail": "invalid or expired token", "instance": None},
    )

    with pytest.raises(ToolError) as exc_info:
        await raise_structured_error(response)

    assert json.loads(str(exc_info.value)) == {"title": "Unauthorized", "status": 401, "detail": "invalid or expired token"}


async def test_404_maps_to_problem_details_shape():
    response = httpx.Response(
        404,
        json={"type": None, "title": "Not Found", "status": 404, "detail": "no trade item for this GTIN", "instance": None},
    )

    with pytest.raises(ToolError) as exc_info:
        await raise_structured_error(response)

    assert json.loads(str(exc_info.value)) == {"title": "Not Found", "status": 404, "detail": "no trade item for this GTIN"}


async def test_non_json_body_surfaces_as_detail_text():
    response = httpx.Response(500, text="internal server error")

    with pytest.raises(ToolError) as exc_info:
        await raise_structured_error(response)

    payload = json.loads(str(exc_info.value))
    assert payload["status"] == 500
    assert payload["detail"] == "internal server error"
