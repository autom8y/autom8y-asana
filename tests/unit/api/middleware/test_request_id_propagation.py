"""Tests for request_id header propagation (F-09).

Validates:
- Asana RequestIDMiddleware reads inbound X-Request-ID header and uses it.
- Asana RequestIDMiddleware generates 16-char hex when header is absent.
- Asana RequestIDMiddleware generates 16-char hex when header is empty string.

Per ADR-request-id-format-contract:
- Canonical format: uuid4().hex[:16] (16-char lowercase hex)
- Header propagation: request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
"""

from __future__ import annotations

import re

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from autom8_asana.api.middleware.core import RequestIDMiddleware

_CANONICAL_RE = re.compile(r"^[0-9a-f]{16}$")


def _make_test_app() -> FastAPI:
    """Create a minimal FastAPI app with RequestIDMiddleware."""
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request) -> JSONResponse:
        return JSONResponse(
            content={"request_id": request.state.request_id},
        )

    return app


class TestRequestIdPropagation:
    """F-09: Asana reads X-Request-ID header before fallback generation."""

    async def test_header_present_uses_header(self) -> None:
        """When X-Request-ID header is present, middleware uses the provided value."""
        app = _make_test_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            supplied_id = "abcdef0123456789"
            response = await client.get("/test", headers={"X-Request-ID": supplied_id})

        assert response.status_code == 200
        body = response.json()
        assert body["request_id"] == supplied_id
        assert response.headers["x-request-id"] == supplied_id

    async def test_header_absent_generates_canonical(self) -> None:
        """When X-Request-ID header is absent, middleware generates 16-char hex."""
        app = _make_test_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/test")

        assert response.status_code == 200
        body = response.json()
        assert _CANONICAL_RE.match(body["request_id"]), (
            f"Generated request_id '{body['request_id']}' is not canonical 16-char hex"
        )
        assert response.headers["x-request-id"] == body["request_id"]

    async def test_empty_header_generates_canonical(self) -> None:
        """When X-Request-ID header is empty string, middleware generates 16-char hex.

        The `or` pattern ensures empty strings fall through to generation.
        """
        app = _make_test_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/test", headers={"X-Request-ID": ""})

        assert response.status_code == 200
        body = response.json()
        assert _CANONICAL_RE.match(body["request_id"]), (
            f"Empty-header fallback '{body['request_id']}' is not canonical 16-char hex"
        )

    async def test_noncanonical_header_propagated(self) -> None:
        """Non-canonical X-Request-ID values are still propagated (per ADR Phase 1 warn)."""
        app = _make_test_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 36-char UUID is non-canonical but should be propagated
            supplied_id = "550e8400-e29b-41d4-a716-446655440000"
            response = await client.get("/test", headers={"X-Request-ID": supplied_id})

        assert response.status_code == 200
        body = response.json()
        assert body["request_id"] == supplied_id
