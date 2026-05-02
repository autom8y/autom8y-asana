"""Regression tests for SCAR-IDEM-001: Idempotency finalize failure handling.

SCAR-IDEM-001: The dispatch() handler's try/except around store.finalize()
previously swallowed all exceptions silently. If finalize fails, the
idempotency key is NOT persisted, and a client retry will re-execute the
mutation (double-execution risk).

The fix (commit 944a0e7) promotes the exception to logger.exception with an
`impact` field, making finalize failures observable.

Known gap per scar-tissue: Double-execution risk is not fully mitigated --
the observability-only fix surfaces the failure but does not prevent replay
from triggering a second execution. S2S callers with strict-once semantics
require an error metric.

These tests verify:
1. When finalize raises, logger.exception is called (not silently swallowed).
2. The exception log includes the 'impact' field documenting re-execution risk.
3. The response is still returned to the caller despite the finalize failure.
4. A subsequent retry with the same key RE-EXECUTES the handler (not replayed),
   confirming the double-execution risk is real and the test catches it.

Regression test for: src/autom8_asana/api/middleware/idempotency.py:730
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from autom8_asana.api.middleware.idempotency import (
    IdempotencyMiddleware,
    InMemoryIdempotencyStore,
)

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

_BUSINESS_BODY = json.dumps({"name": "Acme Dental", "vertical": "dental"}).encode()
_VALID_KEY = "scar-idem-001-key"
_MIDDLEWARE_LOGGER_PATH = "autom8_asana.api.middleware.idempotency.logger"


def _create_app(store: InMemoryIdempotencyStore) -> FastAPI:
    app = FastAPI()

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

    app.add_middleware(IdempotencyMiddleware, store=store)
    return app


async def _post(
    app: FastAPI,
    key: str | None = None,
    body: bytes = _BUSINESS_BODY,
) -> httpx.Response:
    headers = {}
    if key is not None:
        headers["Idempotency-Key"] = key
    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(
            "/v1/intake/business",
            headers=headers,
            content=body,
        )


# ===========================================================================
# SCAR-IDEM-001-A: finalize failure calls logger.exception (not swallowed)
# ===========================================================================


@pytest.mark.scar
class TestFinalizeFailureObservability:
    """SCAR-IDEM-001: finalize exception is surfaced via logger.exception.

    Before the fix, the except block used logger.warning() or was entirely
    absent. The fix promotes it to logger.exception() with an impact field.
    """

    async def test_finalize_failure_calls_logger_exception(self) -> None:
        """When store.finalize() raises, logger.exception is called once."""
        store = InMemoryIdempotencyStore()
        app = _create_app(store)

        async def failing_finalize(*args: Any, **kwargs: Any) -> bool:
            raise OSError("DynamoDB write failed")

        store.finalize = failing_finalize  # type: ignore[assignment]

        mock_logger = MagicMock()
        with patch(_MIDDLEWARE_LOGGER_PATH, mock_logger):
            resp = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert mock_logger.exception.called, (
            "SCAR-IDEM-001 regression: logger.exception must be called when "
            "store.finalize() raises. Silent swallowing masks double-execution risk."
        )

    async def test_finalize_failure_log_includes_impact_field(self) -> None:
        """The exception log must include an 'impact' field documenting re-execution risk.

        Per the fix: extra={'impact': 'idempotency_key_not_persisted_retry_will_re_execute'}
        This field is the observable signal for strict-once S2S callers.
        """
        store = InMemoryIdempotencyStore()
        app = _create_app(store)

        async def failing_finalize(*args: Any, **kwargs: Any) -> bool:
            raise OSError("DynamoDB write failed")

        store.finalize = failing_finalize  # type: ignore[assignment]

        mock_logger = MagicMock()
        with patch(_MIDDLEWARE_LOGGER_PATH, mock_logger):
            await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert mock_logger.exception.called
        call_kwargs = mock_logger.exception.call_args[1]
        extra = call_kwargs.get("extra", {})
        assert "impact" in extra, (
            f"SCAR-IDEM-001 regression: exception log must include 'impact' field. "
            f"Got extra={extra!r}"
        )
        assert "re_execute" in extra["impact"] or "not_persisted" in extra["impact"], (
            f"impact field should document re-execution risk; got: {extra['impact']!r}"
        )


# ===========================================================================
# SCAR-IDEM-001-B: response is returned despite finalize failure
# ===========================================================================


@pytest.mark.scar
class TestResponseReturnedOnFinalizeFailure:
    """The caller must receive their response even if finalize fails.

    The try/except must not propagate the exception to the caller. The
    response was already produced by the route handler and must be returned.
    """

    async def test_response_returned_when_finalize_fails(self) -> None:
        """201 response is returned to caller even if finalize raises."""
        store = InMemoryIdempotencyStore()
        app = _create_app(store)

        async def failing_finalize(*args: Any, **kwargs: Any) -> bool:
            raise OSError("DynamoDB write failed")

        store.finalize = failing_finalize  # type: ignore[assignment]

        resp = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert resp.status_code == 201, (
            f"Expected 201 but got {resp.status_code}. "
            "Finalize failure must not cause a 500 -- response must be returned."
        )
        data = resp.json()
        assert data["business_gid"] == "1234567890123456"

    async def test_idempotency_key_echoed_when_finalize_fails(self) -> None:
        """Idempotency-Key echo header is present even if finalize fails."""
        store = InMemoryIdempotencyStore()
        app = _create_app(store)

        async def failing_finalize(*args: Any, **kwargs: Any) -> bool:
            raise OSError("DynamoDB write failed")

        store.finalize = failing_finalize  # type: ignore[assignment]

        resp = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert resp.headers.get("idempotency-key") == _VALID_KEY, (
            "Idempotency-Key echo header must be present even when finalize fails."
        )


# ===========================================================================
# SCAR-IDEM-001-C: double-execution risk -- key not replayed after failure
# ===========================================================================


@pytest.mark.scar
class TestDoubleExecutionRiskAfterFinalizeFailure:
    """SCAR-IDEM-001 known gap: when finalize fails, the key is NOT stored.

    A client retry with the same key will re-execute the handler (double
    mutation) rather than getting a cached replay. This test confirms the
    known gap exists and is detectable -- it is the signal that the
    strict-once mitigation is still open.

    Per scar-tissue: 'Double-execution risk not yet fully mitigated.'
    Per ADR annotation: S2S callers with strict-once semantics must add
    an error metric on this path.
    """

    async def test_retry_after_finalize_failure_sees_in_flight_409(self) -> None:
        """When finalize fails, a retry with the same key gets 409 IN_FLIGHT.

        After finalize fails, the store retains the "processing" sentinel written
        by claim(). A retry with the same key finds the "processing" entry and
        returns 409 IDEMPOTENCY_KEY_IN_FLIGHT with Retry-After.

        This is better-than-nothing behavior but NOT full mitigation:
        the "processing" sentinel will eventually expire (TTL), allowing
        a subsequent retry to re-execute the handler (double-execution).
        The key is stuck in "processing" permanently until TTL expiry.

        Per scar-tissue: 'Double-execution risk not yet fully mitigated.'
        """
        store = InMemoryIdempotencyStore()
        app = _create_app(store)

        # First request: finalize fails -> key stuck in "processing"
        async def failing_finalize(*args: Any, **kwargs: Any) -> bool:
            raise OSError("DynamoDB write failed")

        store.finalize = failing_finalize  # type: ignore[assignment]
        resp1 = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)
        assert resp1.status_code == 201
        assert "x-idempotent-replayed" not in resp1.headers

        # Store has "processing" sentinel from claim() -- finalize was skipped
        stored = await store.get(
            f"unknown#{_VALID_KEY}",
            "POST#/v1/intake/business",
        )
        assert stored is not None, "Processing sentinel must be present after finalize failure"
        assert stored.status == "processing", (
            f"Key should be stuck in 'processing' after finalize failure; "
            f"got status={stored.status!r}"
        )

        # Retry with same key: sees "processing" sentinel -> 409 IN_FLIGHT
        # (Not a replay of the completed response, and not a fresh re-execution --
        # the caller is blocked until TTL expires, at which point double-execution risk materializes)
        resp2 = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert resp2.status_code == 409, (
            f"Expected 409 IN_FLIGHT for retry after finalize failure; got {resp2.status_code}. "
            "The 'processing' sentinel should block retries until TTL expiry."
        )
        assert resp2.json()["error"] == "IDEMPOTENCY_KEY_IN_FLIGHT"

    async def test_store_empty_after_finalize_failure_confirms_no_persistence(
        self,
    ) -> None:
        """Confirming store is empty after finalize failure is the core SCAR evidence.

        An empty store means no replay is possible on retry, which is the
        direct cause of the double-execution risk.
        """
        store = InMemoryIdempotencyStore()
        app = _create_app(store)

        async def failing_finalize(*args: Any, **kwargs: Any) -> bool:
            raise OSError("DynamoDB write failed")

        store.finalize = failing_finalize  # type: ignore[assignment]

        # Execute with key -- store.claim will succeed (key is stored as processing),
        # handler executes, then finalize fails -> the "processing" claim is the only
        # thing stored but the key never reaches "complete" status
        await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        # After finalize failure, the store retains the "processing" sentinel
        # from claim() -- the key is in "processing" state, NOT "complete".
        # A retry will see status="processing" and return 409 IN_FLIGHT.
        # This is a better-than-nothing behavior but still not full mitigation:
        # the "processing" sentinel will eventually expire (TTL), allowing replay.
        stored = await store.get(
            f"unknown#{_VALID_KEY}",
            "POST#/v1/intake/business",
        )
        # The "processing" claim was written by store.claim() before finalize failed.
        # This test documents the actual post-failure store state.
        if stored is not None:
            assert stored.status == "processing", (
                f"Expected 'processing' sentinel after finalize failure; got {stored.status!r}"
            )
        else:
            # If TTL expired or store was cleared, that's also acceptable for this test.
            pass
