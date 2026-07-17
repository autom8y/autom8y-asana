"""C3 / R2: cold-frame 503 -> retryable cache-warming, NEVER classified as auth.

The load-bearing contract is the STRUCTURED classification (``kind`` + ``retryable``),
not message substrings. Indeed the honest messages deliberately cross-reference the
other class ("this is NOT an auth failure" / "NOT a cache-warming condition") — that
disambiguation is a FEATURE, so the assertions below test ``kind``/``retryable`` and
assert the two classes are DISJOINT (the query503 scar this taxonomy prevents).
"""

from __future__ import annotations

import httpx
import pytest

from asana_mcp.errors import McpToolError, map_http_error
from asana_mcp.schemas import RowsArgs
from asana_mcp.tools.query import query_rows_handler


def test_503_is_classified_warming_not_auth():
    err = map_http_error(httpx.Response(503, json={"error": {"code": "CACHE_NOT_WARMED"},
                                                   "details": {"retry_after_seconds": 30}}))
    assert err.kind == "warming"        # classified as warming, NOT auth
    assert err.kind != "auth"
    assert err.retryable is True
    assert err.status == 503
    assert err.retry_after == 30.0
    assert "warming" in err.message.lower()   # names the true cause


def test_401_is_classified_auth_not_warming():
    err = map_http_error(httpx.Response(401, json={"error": {"code": "SERVICE_TOKEN_REQUIRED"}}))
    assert err.kind == "auth"
    assert err.kind != "warming"
    assert err.retryable is False
    assert "authentic" in err.message.lower() or "authoriz" in err.message.lower()


def test_warming_and_auth_are_disjoint_classes():
    warming = map_http_error(httpx.Response(503, json={}))
    auth = map_http_error(httpx.Response(401, json={}))
    assert warming.kind != auth.kind
    assert warming.retryable is True and auth.retryable is False


async def test_endpoint_cold_frame_503_is_warming(endpoint_warming_ctx):
    with pytest.raises(McpToolError) as ei:
        await query_rows_handler(endpoint_warming_ctx, "offer", RowsArgs())
    assert ei.value.kind == "warming"
    assert ei.value.kind != "auth"
    assert ei.value.retryable is True


async def test_endpoint_401_is_auth(auth_fail_ctx):
    with pytest.raises(McpToolError) as ei:
        await query_rows_handler(auth_fail_ctx, "offer", RowsArgs())
    assert ei.value.kind == "auth"
    assert ei.value.retryable is False
