"""Contract tests for IdempotencyMiddleware (ID-01 through ID-11).

Per ADR-omniscience-idempotency and the omniscience-contract-test-report,
these tests validate the RFC 8791 idempotency protocol for four mutating
S2S endpoints.

Test app setup:
    A minimal FastAPI app with the IdempotencyMiddleware installed and
    two routes (one eligible POST, one ineligible GET) is used. Tests
    exercise the middleware via httpx.AsyncClient with ASGITransport.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from autom8_asana.api.middleware.idempotency import (
    DEFAULT_TTL_SECONDS,
    IDEMPOTENT_ENDPOINTS,
    IdempotencyMiddleware,
    InMemoryIdempotencyStore,
    StoredResponse,
    _is_eligible,
    _validate_key,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _create_test_app(
    store: InMemoryIdempotencyStore | None = None,
) -> tuple[FastAPI, InMemoryIdempotencyStore]:
    """Create a minimal FastAPI app with IdempotencyMiddleware.

    Returns the app and the store instance for test assertions.
    """
    app = FastAPI()
    idempotency_store = store or InMemoryIdempotencyStore()

    # Eligible endpoint: POST /v1/intake/business
    @app.post("/v1/intake/business")
    async def create_business(request: Request) -> JSONResponse:
        body = await request.json()
        return JSONResponse(
            status_code=201,
            content={
                "business_gid": "1234567890123456",
                "name": body.get("name", "unknown"),
            },
        )

    # Eligible endpoint: POST /v1/intake/route
    @app.post("/v1/intake/route")
    async def route_intake(request: Request) -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={"process_gid": "9876543210", "is_new": True},
        )

    # Eligible endpoint: POST /v1/tasks/{task_gid}/custom-fields
    @app.post("/v1/tasks/{task_gid}/custom-fields")
    async def write_custom_fields(task_gid: str, request: Request) -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={"task_gid": task_gid, "fields_written": 3},
        )

    # Eligible endpoint: PATCH /api/v1/entity/{entity_type}/{gid}
    @app.patch("/api/v1/entity/{entity_type}/{gid}")
    async def write_entity_fields(
        entity_type: str, gid: str, request: Request
    ) -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={"entity_type": entity_type, "gid": gid, "fields_written": 2},
        )

    # Non-eligible endpoint: GET /health
    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse(status_code=200, content={"status": "ok"})

    # Non-eligible endpoint: DELETE /v1/intake/business (not in eligible set)
    @app.delete("/v1/intake/business")
    async def delete_business() -> JSONResponse:
        return JSONResponse(status_code=204, content=None)

    app.add_middleware(IdempotencyMiddleware, store=idempotency_store)

    return app, idempotency_store


@pytest.fixture
def store() -> InMemoryIdempotencyStore:
    return InMemoryIdempotencyStore()


@pytest.fixture
def app_and_store(
    store: InMemoryIdempotencyStore,
) -> tuple[FastAPI, InMemoryIdempotencyStore]:
    return _create_test_app(store)


@pytest.fixture
def app(app_and_store: tuple[FastAPI, InMemoryIdempotencyStore]) -> FastAPI:
    return app_and_store[0]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_BUSINESS_BODY = json.dumps({"name": "Acme Dental", "vertical": "dental"}).encode()
_VALID_KEY = "test-key-12345678"


async def _make_request(
    app: FastAPI,
    method: str = "POST",
    path: str = "/v1/intake/business",
    headers: dict[str, str] | None = None,
    content: bytes | None = None,
) -> httpx.Response:
    """Send a request to the test app via httpx AsyncClient."""
    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(
            method=method,
            url=path,
            headers=headers or {},
            content=content,
        )


# ===========================================================================
# ID-01: Request without Idempotency-Key passes through unchanged
# ===========================================================================


class TestID01Passthrough:
    """ID-01: R-006 compliance -- requests without the header behave identically
    to current production behavior. No store interaction.
    """

    async def test_post_without_key_passes_through(self, app: FastAPI) -> None:
        """POST to eligible endpoint without Idempotency-Key executes normally."""
        resp = await _make_request(app, content=_BUSINESS_BODY)
        assert resp.status_code == 201
        data = resp.json()
        assert data["business_gid"] == "1234567890123456"
        # No idempotency headers on the response
        assert "x-idempotent-replayed" not in resp.headers

    async def test_passthrough_does_not_write_to_store(
        self, app: FastAPI, store: InMemoryIdempotencyStore
    ) -> None:
        """Store remains empty after request without Idempotency-Key."""
        await _make_request(app, content=_BUSINESS_BODY)
        assert len(store._store) == 0


# ===========================================================================
# ID-02: First request with key executes normally and stores response
# ===========================================================================


class TestID02FirstRequest:
    """ID-02: Valid key on first request executes the handler and stores
    the response for future replay.
    """

    async def test_first_request_executes_and_stores(
        self, app: FastAPI, store: InMemoryIdempotencyStore
    ) -> None:
        """First request with key returns normal response and populates store."""
        headers = {"Idempotency-Key": _VALID_KEY}
        resp = await _make_request(app, headers=headers, content=_BUSINESS_BODY)

        assert resp.status_code == 201
        data = resp.json()
        assert data["business_gid"] == "1234567890123456"

        # Verify Idempotency-Key is echoed
        assert resp.headers.get("idempotency-key") == _VALID_KEY

        # Verify store contains the response
        assert len(store._store) == 1

    async def test_stored_response_is_complete(
        self, app: FastAPI, store: InMemoryIdempotencyStore
    ) -> None:
        """Stored response has status 'complete' with correct fingerprint."""
        headers = {"Idempotency-Key": _VALID_KEY}
        await _make_request(app, headers=headers, content=_BUSINESS_BODY)

        # Find the stored entry
        stored = list(store._store.values())[0]
        assert stored.status == "complete"
        assert stored.response_status == 201
        expected_fingerprint = hashlib.sha256(_BUSINESS_BODY).hexdigest()
        assert stored.request_fingerprint == expected_fingerprint


# ===========================================================================
# ID-03: Second request with same key returns stored response
# ===========================================================================


class TestID03Replay:
    """ID-03: Replay returns stored response with X-Idempotent-Replayed: true.
    Route handler is NOT invoked on replay.
    """

    async def test_replay_returns_stored_response(self, app: FastAPI) -> None:
        """Second request with same key + same body returns stored 201."""
        headers = {"Idempotency-Key": _VALID_KEY}

        # First request
        resp1 = await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        assert resp1.status_code == 201

        # Second request (replay)
        resp2 = await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        assert resp2.status_code == 201
        assert resp2.json()["business_gid"] == "1234567890123456"

    async def test_replay_has_replayed_header(self, app: FastAPI) -> None:
        """Replayed response includes X-Idempotent-Replayed: true."""
        headers = {"Idempotency-Key": _VALID_KEY}

        await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        resp2 = await _make_request(app, headers=headers, content=_BUSINESS_BODY)

        assert resp2.headers.get("x-idempotent-replayed") == "true"
        assert resp2.headers.get("idempotency-key") == _VALID_KEY

    async def test_replay_includes_original_time(self, app: FastAPI) -> None:
        """Replayed response includes X-Idempotent-Original-Time header."""
        headers = {"Idempotency-Key": _VALID_KEY}

        await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        resp2 = await _make_request(app, headers=headers, content=_BUSINESS_BODY)

        assert "x-idempotent-original-time" in resp2.headers


# ===========================================================================
# ID-04: Different key for same endpoint executes independently
# ===========================================================================


class TestID04DifferentKeys:
    """ID-04: Different idempotency keys for the same endpoint execute
    independently. Each key has its own stored response.
    """

    async def test_different_keys_execute_independently(
        self, app: FastAPI, store: InMemoryIdempotencyStore
    ) -> None:
        """Two requests with different keys both execute the handler."""
        body = _BUSINESS_BODY

        resp1 = await _make_request(
            app, headers={"Idempotency-Key": "key-aaaaaaaa"}, content=body
        )
        resp2 = await _make_request(
            app, headers={"Idempotency-Key": "key-bbbbbbbb"}, content=body
        )

        assert resp1.status_code == 201
        assert resp2.status_code == 201
        # Both stored independently
        assert len(store._store) == 2


# ===========================================================================
# ID-05: Key validation (empty, too short, too long, invalid chars)
# ===========================================================================


class TestID05KeyValidation:
    """ID-05: Invalid key formats are rejected with 400 INVALID_IDEMPOTENCY_KEY."""

    async def test_empty_key_rejected(self, app: FastAPI) -> None:
        """Empty Idempotency-Key header returns 400."""
        headers = {"Idempotency-Key": ""}
        resp = await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_IDEMPOTENCY_KEY"

    async def test_too_short_key_rejected(self, app: FastAPI) -> None:
        """Key shorter than 8 characters returns 400."""
        headers = {"Idempotency-Key": "short"}
        resp = await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_IDEMPOTENCY_KEY"
        assert "at least 8" in resp.json()["message"]

    async def test_too_long_key_rejected(self, app: FastAPI) -> None:
        """Key longer than 256 characters returns 400."""
        headers = {"Idempotency-Key": "x" * 257}
        resp = await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_IDEMPOTENCY_KEY"
        assert "256" in resp.json()["message"]

    async def test_invalid_chars_rejected(self, app: FastAPI) -> None:
        """Key with special characters (spaces, slashes) returns 400."""
        headers = {"Idempotency-Key": "key with spaces!!"}
        resp = await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_IDEMPOTENCY_KEY"

    async def test_valid_uuid_key_accepted(self, app: FastAPI) -> None:
        """UUID v4 format key is accepted."""
        headers = {"Idempotency-Key": "550e8400-e29b-41d4-a716-446655440000"}
        resp = await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        assert resp.status_code == 201

    async def test_valid_dotted_key_accepted(self, app: FastAPI) -> None:
        """Key with dots and underscores is accepted."""
        headers = {"Idempotency-Key": "service_a.request.12345678"}
        resp = await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        assert resp.status_code == 201


# ===========================================================================
# ID-06: Fingerprint mismatch returns 422
# ===========================================================================


class TestID06FingerprintMismatch:
    """ID-06: Same idempotency key with different request body returns 422
    IDEMPOTENCY_KEY_MISMATCH.
    """

    async def test_same_key_different_body_returns_422(self, app: FastAPI) -> None:
        """Using the same key with a different body is rejected."""
        headers = {"Idempotency-Key": _VALID_KEY}

        # First request with body A
        body_a = json.dumps({"name": "Acme Dental"}).encode()
        resp1 = await _make_request(app, headers=headers, content=body_a)
        assert resp1.status_code == 201

        # Second request with body B (different content, same key)
        body_b = json.dumps({"name": "Beta Dental"}).encode()
        resp2 = await _make_request(app, headers=headers, content=body_b)
        assert resp2.status_code == 422
        assert resp2.json()["error"] == "IDEMPOTENCY_KEY_MISMATCH"


# ===========================================================================
# ID-07: Non-idempotent methods (GET, DELETE) skip middleware
# ===========================================================================


class TestID07NonIdempotentMethods:
    """ID-07: GET, DELETE, and other non-eligible methods pass through
    even if the Idempotency-Key header is present.
    """

    async def test_get_with_key_passes_through(self, app: FastAPI) -> None:
        """GET /health with Idempotency-Key passes through unchanged."""
        headers = {"Idempotency-Key": _VALID_KEY}
        resp = await _make_request(app, method="GET", path="/health", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        # No idempotency headers echoed
        assert "idempotency-key" not in resp.headers

    async def test_delete_with_key_passes_through(
        self, app: FastAPI, store: InMemoryIdempotencyStore
    ) -> None:
        """DELETE /v1/intake/business with key passes through (DELETE not eligible)."""
        headers = {"Idempotency-Key": _VALID_KEY}
        resp = await _make_request(
            app, method="DELETE", path="/v1/intake/business", headers=headers
        )
        assert resp.status_code == 204
        # Nothing stored
        assert len(store._store) == 0


# ===========================================================================
# ID-08: Store unavailability triggers graceful degradation
# ===========================================================================


class TestID08StoreDegradation:
    """ID-08: When the store raises an exception, the middleware falls through
    to the handler and adds X-Idempotent-Degraded: true header.
    """

    async def test_store_claim_failure_degrades_gracefully(self) -> None:
        """Store exception on claim -> handler executes with degraded header."""
        store = InMemoryIdempotencyStore()
        app, _ = _create_test_app(store)

        # Make the store's claim method raise
        original_claim = store.claim

        async def failing_claim(*args: Any, **kwargs: Any) -> bool:
            raise ConnectionError("DynamoDB unavailable")

        store.claim = failing_claim  # type: ignore[assignment]

        headers = {"Idempotency-Key": _VALID_KEY}
        resp = await _make_request(app, headers=headers, content=_BUSINESS_BODY)

        assert resp.status_code == 201
        assert resp.headers.get("x-idempotent-degraded") == "true"
        assert resp.headers.get("idempotency-key") == _VALID_KEY

    async def test_store_get_failure_degrades_gracefully(self) -> None:
        """Store exception on get (after claim returns False) -> degraded."""
        store = InMemoryIdempotencyStore()
        app, _ = _create_test_app(store)

        # Pre-populate the store so claim returns False
        headers = {"Idempotency-Key": _VALID_KEY}
        await _make_request(app, headers=headers, content=_BUSINESS_BODY)

        # Now make get fail
        async def failing_get(*args: Any, **kwargs: Any) -> None:
            raise ConnectionError("DynamoDB unavailable")

        store.get = failing_get  # type: ignore[assignment]

        resp = await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        assert resp.status_code == 201
        assert resp.headers.get("x-idempotent-degraded") == "true"


# ===========================================================================
# ID-09: TTL-expired keys allow re-execution
# ===========================================================================


class TestID09TTLExpiry:
    """ID-09: After TTL expiration, the same key triggers a fresh execution
    (not a replay of the original response).
    """

    async def test_expired_key_allows_re_execution(self) -> None:
        """Key expired via TTL is treated as new request."""
        # Use a very short TTL for testing
        store = InMemoryIdempotencyStore(ttl_seconds=1)
        app, _ = _create_test_app(store)

        headers = {"Idempotency-Key": _VALID_KEY}

        # First request
        resp1 = await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        assert resp1.status_code == 201

        # Simulate TTL expiry by backdating the timestamp
        for key in store._timestamps:
            store._timestamps[key] = time.time() - 2  # 2 seconds ago, TTL is 1s

        # Second request after expiry -- should execute fresh, not replay
        resp2 = await _make_request(app, headers=headers, content=_BUSINESS_BODY)
        assert resp2.status_code == 201
        # No replay header since this was a fresh execution
        assert "x-idempotent-replayed" not in resp2.headers


# ===========================================================================
# ID-10: Concurrent requests -- second sees "processing" sentinel
# ===========================================================================


class TestID10ConcurrentRequests:
    """ID-10: When two concurrent requests use the same key, the second
    one receives 409 with Retry-After because the first has claimed the
    key with status "processing".
    """

    async def test_concurrent_request_returns_409(self) -> None:
        """Second concurrent request with same key gets 409 IDEMPOTENCY_KEY_IN_FLIGHT."""
        store = InMemoryIdempotencyStore()
        app, _ = _create_test_app(store)

        # Pre-populate store with a "processing" sentinel to simulate
        # a concurrent request that has claimed but not yet finalized.
        pk = f"unknown#{_VALID_KEY}"
        sk = "POST#/v1/intake/business"
        fingerprint = hashlib.sha256(_BUSINESS_BODY).hexdigest()
        await store.claim(pk, sk, fingerprint)

        # The stored entry should be in "processing" state
        entry = await store.get(pk, sk)
        assert entry is not None
        assert entry.status == "processing"

        # Now send a request with the same key -- should get 409
        headers = {"Idempotency-Key": _VALID_KEY}
        resp = await _make_request(app, headers=headers, content=_BUSINESS_BODY)

        assert resp.status_code == 409
        assert resp.json()["error"] == "IDEMPOTENCY_KEY_IN_FLIGHT"
        assert resp.headers.get("retry-after") == "1"


# ===========================================================================
# ID-11: Middleware position verification
# ===========================================================================


class TestID11MiddlewarePosition:
    """ID-11: Verify that IdempotencyMiddleware is correctly positioned
    in the middleware stack and that non-eligible endpoints are not affected.
    """

    async def test_eligible_endpoints_are_comprehensive(self) -> None:
        """All four ADR-specified endpoints are in IDEMPOTENT_ENDPOINTS."""
        expected = {
            ("POST", "/v1/intake/business"),
            ("POST", "/v1/intake/route"),
            ("POST", "/v1/tasks/{task_gid}/custom-fields"),
            ("PATCH", "/api/v1/entity/{entity_type}/{gid}"),
        }
        assert expected == IDEMPOTENT_ENDPOINTS

    async def test_path_matching_with_parameters(self, app: FastAPI) -> None:
        """Path parameter endpoints correctly match via regex."""
        # POST /v1/tasks/123/custom-fields should be eligible
        headers = {"Idempotency-Key": _VALID_KEY}
        body = json.dumps({"fields": {"status": "active"}}).encode()
        resp = await _make_request(
            app,
            method="POST",
            path="/v1/tasks/1234567890/custom-fields",
            headers=headers,
            content=body,
        )
        assert resp.status_code == 200
        assert resp.headers.get("idempotency-key") == _VALID_KEY

    async def test_patch_entity_eligible(self, app: FastAPI) -> None:
        """PATCH /api/v1/entity/{type}/{gid} is eligible for idempotency."""
        headers = {"Idempotency-Key": _VALID_KEY}
        body = json.dumps({"fields": {"status": "active"}}).encode()
        resp = await _make_request(
            app,
            method="PATCH",
            path="/api/v1/entity/business/1234567890",
            headers=headers,
            content=body,
        )
        assert resp.status_code == 200
        assert resp.headers.get("idempotency-key") == _VALID_KEY

    async def test_middleware_in_create_app(self) -> None:
        """Verify IdempotencyMiddleware is registered in create_app().

        Checks that the middleware class appears in the app's user_middleware
        list and is positioned correctly relative to SlowAPI and RequestLogging.
        """
        with patch(
            "autom8_asana.api.lifespan._discover_entity_projects",
            new_callable=AsyncMock,
        ):
            from autom8_asana.api.main import create_app

            test_app = create_app()
            # Starlette stores middleware in user_middleware (reverse execution order)
            middleware_names = [mw.cls.__name__ for mw in test_app.user_middleware]

            assert "IdempotencyMiddleware" in middleware_names, (
                f"IdempotencyMiddleware not found in middleware stack: {middleware_names}"
            )

            # Verify position: Idempotency should execute BEFORE SlowAPI
            # In user_middleware (addition order), IdempotencyMiddleware appears
            # AFTER SlowAPIMiddleware because Starlette reverses execution order.
            idem_idx = middleware_names.index("IdempotencyMiddleware")
            slow_idx = middleware_names.index("SlowAPIMiddleware")
            assert idem_idx > slow_idx, (
                f"IdempotencyMiddleware (idx={idem_idx}) should be added after "
                f"SlowAPIMiddleware (idx={slow_idx}) for correct execution order"
            )


# ===========================================================================
# Unit tests for helper functions
# ===========================================================================


class TestValidateKey:
    """Unit tests for the _validate_key helper."""

    def test_valid_uuid(self) -> None:
        assert _validate_key("550e8400-e29b-41d4-a716-446655440000") is None

    def test_valid_alphanumeric(self) -> None:
        assert _validate_key("mykey12345678") is None

    def test_empty_string(self) -> None:
        assert _validate_key("") is not None

    def test_too_short(self) -> None:
        assert _validate_key("abcdefg") is not None  # 7 chars

    def test_exactly_min_length(self) -> None:
        assert _validate_key("abcdefgh") is None  # 8 chars

    def test_too_long(self) -> None:
        assert _validate_key("a" * 257) is not None

    def test_exactly_max_length(self) -> None:
        assert _validate_key("a" * 256) is None

    def test_special_chars(self) -> None:
        assert _validate_key("key@#$%^&*()") is not None


class TestIsEligible:
    """Unit tests for the _is_eligible helper."""

    def test_post_intake_business(self) -> None:
        assert _is_eligible("POST", "/v1/intake/business") is not None

    def test_post_intake_route(self) -> None:
        assert _is_eligible("POST", "/v1/intake/route") is not None

    def test_post_custom_fields(self) -> None:
        assert _is_eligible("POST", "/v1/tasks/123/custom-fields") is not None

    def test_patch_entity(self) -> None:
        assert _is_eligible("PATCH", "/api/v1/entity/business/456") is not None

    def test_get_not_eligible(self) -> None:
        assert _is_eligible("GET", "/v1/intake/business") is None

    def test_unmatched_path(self) -> None:
        assert _is_eligible("POST", "/v1/some/other/path") is None
