"""Regression + contract tests for SCAR-IDEM-001: finalize-failure handling.

SCAR-IDEM-001 (origin): The dispatch() handler's ``try/except`` around
``store.finalize()`` swallowed all exceptions silently. The first remediation
(commit 944a0e7) promoted the exception to ``logger.exception`` with an
``impact`` field, making the failure *observable* but NOT *propagated*.

W-IDEM contract (this file, RED-first two-sided): the architect's O2
500-propagation contract. Two facts drive the design (verified at HEAD):

  F-1  ``finalize()`` never raises; it returns ``bool``. The real
       ``DynamoDBIdempotencyStore.finalize()`` swallows internally
       (``except Exception: ... return False``) and ``InMemoryIdempotencyStore``
       returns ``False`` when the key is absent. So the middleware's old
       ``try/except`` was effectively dead for the store's own DynamoDB
       failures -- the failure signal exists (``finalize() -> False``) but the
       middleware DISCARDED the ``bool`` return value entirely.

  F-2  the response body is buffered (drained from ``body_iterator``) BEFORE
       finalize runs and BEFORE the response is returned. So at the finalize
       decision point the 2xx has NOT yet been sent to the client -- a
       buffered-response retraction (500) is mechanically sound.

The contract (architect O2, strict-once-gated by ``caller_service`` presence):

  R-IDEM-1  ``finalize() -> False`` emits an ``IdempotencyFinalizeFailure``
            error metric (operator-visible).
  R-IDEM-2  (HARD) a strict-once S2S caller (``caller_service`` present, i.e.
            ``service_name != _DEFAULT_SERVICE``) MUST receive a non-2xx
            (500 ``IDEMPOTENCY_KEY_NOT_PERSISTED``) -- never a 2xx with an
            unpersisted key.
  R-IDEM-4  a PAT/human caller (``caller_service`` absent) keeps current
            behavior: the handler response is returned, failure is metric+log
            observable only -- no spurious 500.
  R-IDEM-5  the historical "double-execution risk is real" characterization
            test flips from CHARACTERIZATION to GUARD.

Regression test for: src/autom8_asana/api/middleware/idempotency.py
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from autom8_asana.api.dependencies import AuthContext, AuthMode
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
_METRIC_PATCH_PATH = "autom8_asana.api.middleware.idempotency.emit_metric"

# A strict-once S2S caller is discriminated by JWT service_name presence.
_S2S_SERVICE = "autom8y-data"


class _ExecutionCounter:
    """Counts handler invocations to prove (non-)re-execution across retries."""

    def __init__(self) -> None:
        self.count = 0


def _create_app(
    store: InMemoryIdempotencyStore,
    *,
    caller_service: str | None = None,
    counter: _ExecutionCounter | None = None,
) -> FastAPI:
    """Build an app whose /v1/intake/business handler is idempotency-wrapped.

    If ``caller_service`` is provided, an inner middleware injects an
    ``AuthContext`` onto ``request.state`` so the idempotency middleware's
    ``_get_service_name`` returns that service (S2S strict-once). When ``None``,
    no auth_context is set -> ``_get_service_name`` returns ``_DEFAULT_SERVICE``
    (PAT/human, non-strict-once).
    """
    app = FastAPI()

    @app.post("/v1/intake/business")
    async def create_business(request: Request) -> JSONResponse:
        if counter is not None:
            counter.count += 1
        body = await request.json()
        return JSONResponse(
            status_code=201,
            content={
                "business_gid": "1234567890123456",
                "name": body.get("name", "unknown"),
            },
        )

    app.add_middleware(IdempotencyMiddleware, store=store)

    if caller_service is not None:
        # Outermost: sets auth_context BEFORE the idempotency middleware reads it.
        @app.middleware("http")
        async def _inject_auth_context(request: Request, call_next: Any) -> Any:
            request.state.auth_context = AuthContext(
                mode=AuthMode.JWT,
                asana_pat="pat-test",
                caller_service=caller_service,
            )
            return await call_next(request)

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


async def _returns_false_finalize(*args: Any, **kwargs: Any) -> bool:
    """Mimic the REAL store: finalize fails by RETURNING False, not raising.

    This is the architect's F-1 fact -- the production stores swallow DynamoDB
    failures internally and surface them as a ``bool`` return. The old
    middleware discarded this signal.
    """
    return False


# ===========================================================================
# W-IDEM-RED/GREEN: strict-once S2S caller MUST observe non-2xx (R-IDEM-2)
# ===========================================================================


@pytest.mark.scar
class TestStrictOnceFinalizeFailurePropagation:
    """R-IDEM-2 (HARD): finalize() -> False for an S2S caller surfaces 500.

    RED leg (against HEAD): with the old metric-only/observability behavior,
    a strict-once caller receives a 2xx and a retry RE-EXECUTES the handler.
    GREEN leg (with the O2 fix): the strict-once caller receives a 500
    IDEMPOTENCY_KEY_NOT_PERSISTED and the IdempotencyFinalizeFailure metric
    is emitted.
    """

    async def test_strict_once_caller_receives_500_not_persisted(self) -> None:
        """finalize() -> False + S2S caller -> 500 IDEMPOTENCY_KEY_NOT_PERSISTED.

        RED against HEAD: HEAD returns the buffered 201 (handler response)
        regardless of the finalize bool. GREEN after fix: 500 with the typed
        error body and the X-Idempotent-Not-Persisted header.
        """
        store = InMemoryIdempotencyStore()
        app = _create_app(store, caller_service=_S2S_SERVICE)
        store.finalize = _returns_false_finalize  # type: ignore[assignment]

        with patch(_METRIC_PATCH_PATH, create=True):
            resp = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert resp.status_code == 500, (
            f"R-IDEM-2: strict-once S2S caller must receive 500 when the "
            f"idempotency key was not persisted; got {resp.status_code}. A 2xx "
            f"here means the caller will blind-retry into a double-execution."
        )
        body = resp.json()
        assert body["error"] == "IDEMPOTENCY_KEY_NOT_PERSISTED", (
            f"Expected typed error IDEMPOTENCY_KEY_NOT_PERSISTED; got {body!r}"
        )
        assert resp.headers.get("x-idempotent-not-persisted") == "true", (
            "X-Idempotent-Not-Persisted header must signal the unpersisted key."
        )
        assert resp.headers.get("idempotency-key") == _VALID_KEY

    async def test_strict_once_finalize_failure_emits_metric(self) -> None:
        """R-IDEM-1: finalize() -> False emits IdempotencyFinalizeFailure metric."""
        store = InMemoryIdempotencyStore()
        app = _create_app(store, caller_service=_S2S_SERVICE)
        store.finalize = _returns_false_finalize  # type: ignore[assignment]

        with patch(_METRIC_PATCH_PATH, create=True) as mock_emit:
            await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert mock_emit.called, (
            "R-IDEM-1: IdempotencyFinalizeFailure metric must be emitted on finalize() -> False."
        )
        metric_name = mock_emit.call_args[0][0]
        assert metric_name == "IdempotencyFinalizeFailure", (
            f"Expected IdempotencyFinalizeFailure metric; got {metric_name!r}"
        )
        dims = mock_emit.call_args[1].get("dimensions", {})
        assert dims.get("service_name") == _S2S_SERVICE, (
            f"Metric must carry the caller service_name dimension; got {dims!r}"
        )

    async def test_strict_once_retry_after_failure_does_not_re_execute(self) -> None:
        """R-IDEM-5 GUARD: after a 500, the caller is told to reconcile.

        The historical characterization ("a retry RE-EXECUTES, double-execution
        is real") flips to a guard: the strict-once caller that received the
        500 MUST NOT have silently committed a replayable success. A fresh-key
        retry hitting the in-flight sentinel returns 409 (back off), proving the
        sentinel is intact and the caller is not handed a misleading 2xx.
        """
        store = InMemoryIdempotencyStore()
        counter = _ExecutionCounter()
        app = _create_app(store, caller_service=_S2S_SERVICE, counter=counter)
        store.finalize = _returns_false_finalize  # type: ignore[assignment]

        with patch(_METRIC_PATCH_PATH, create=True):
            resp1 = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)
            assert resp1.status_code == 500
            assert counter.count == 1, "Handler executed exactly once on first call."

            # A retry while the processing sentinel is fresh -> 409 in-flight,
            # NOT a second handler execution.
            resp2 = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert resp2.status_code == 409, (
            f"R-IDEM-5: retry after a not-persisted 500 must hit the in-flight "
            f"409 (sentinel intact), not re-execute; got {resp2.status_code}."
        )
        assert resp2.json()["error"] == "IDEMPOTENCY_KEY_IN_FLIGHT"
        assert counter.count == 1, (
            f"R-IDEM-5 GUARD: the handler must NOT have re-executed on the "
            f"sentinel-blocked retry; execution count={counter.count}."
        )


# ===========================================================================
# W-IDEM no-defect GREEN: happy path stays green (two-sided teeth)
# ===========================================================================


@pytest.mark.scar
class TestFinalizeSuccessUnchanged:
    """finalize() -> True: 2xx returned unchanged, no metric, replay works.

    This is the no-defect side of the two-sided teeth: the fix must not
    perturb the success path.
    """

    async def test_success_returns_2xx_no_metric(self) -> None:
        store = InMemoryIdempotencyStore()
        app = _create_app(store, caller_service=_S2S_SERVICE)

        with patch(_METRIC_PATCH_PATH, create=True) as mock_emit:
            resp = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert resp.status_code == 201, (
            f"finalize success must return the handler 2xx; got {resp.status_code}"
        )
        assert resp.json()["business_gid"] == "1234567890123456"
        assert not mock_emit.called, "No IdempotencyFinalizeFailure metric on the success path."

    async def test_success_then_retry_replays(self) -> None:
        """After a successful finalize, a retry with the same key replays."""
        store = InMemoryIdempotencyStore()
        counter = _ExecutionCounter()
        app = _create_app(store, caller_service=_S2S_SERVICE, counter=counter)

        with patch(_METRIC_PATCH_PATH, create=True):
            resp1 = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)
            assert resp1.status_code == 201
            resp2 = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert resp2.status_code == 201
        assert resp2.headers.get("x-idempotent-replayed") == "true", (
            "Second request with same key must be a replay, not a re-execution."
        )
        assert counter.count == 1, (
            f"Handler must execute exactly once across replayed retries; got {counter.count}."
        )


# ===========================================================================
# W-IDEM R-IDEM-4: PAT/human (non-strict-once) keeps current behavior
# ===========================================================================


@pytest.mark.scar
class TestNonStrictOnceFinalizeFailure:
    """R-IDEM-4: PAT/human callers (caller_service absent) keep current behavior.

    finalize() -> False for a non-strict-once caller: the handler response is
    still returned (no spurious 500), but the metric is still emitted.
    """

    async def test_pat_caller_finalize_failure_returns_handler_response(self) -> None:
        """No auth_context (PAT) + finalize() -> False -> 201, NOT 500."""
        store = InMemoryIdempotencyStore()
        app = _create_app(store, caller_service=None)
        store.finalize = _returns_false_finalize  # type: ignore[assignment]

        with patch(_METRIC_PATCH_PATH, create=True):
            resp = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert resp.status_code == 201, (
            f"R-IDEM-4: PAT/human caller (non-strict-once) must keep the current "
            f"behavior (handler response returned), not a 500; got {resp.status_code}."
        )
        assert resp.json()["business_gid"] == "1234567890123456"
        assert resp.headers.get("idempotency-key") == _VALID_KEY

    async def test_pat_caller_finalize_failure_still_emits_metric(self) -> None:
        """R-IDEM-1 holds for PAT too: the failure metric is still emitted."""
        store = InMemoryIdempotencyStore()
        app = _create_app(store, caller_service=None)
        store.finalize = _returns_false_finalize  # type: ignore[assignment]

        with patch(_METRIC_PATCH_PATH, create=True) as mock_emit:
            await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert mock_emit.called, (
            "R-IDEM-1: the failure metric is emitted regardless of caller class."
        )
        assert mock_emit.call_args[0][0] == "IdempotencyFinalizeFailure"
        dims = mock_emit.call_args[1].get("dimensions", {})
        # PAT caller resolves to the default "unknown" service.
        assert dims.get("service_name") == "unknown", (
            f"PAT caller metric should carry the default service dimension; got {dims!r}"
        )


# ===========================================================================
# W-IDEM EC-2: concurrent contract intact (second request hits 409 in-flight)
# ===========================================================================


@pytest.mark.scar
class TestConcurrentClaimContractIntact:
    """EC-2: the existing concurrent-claim contract must not regress.

    When the first request's finalize fails (returns False), the processing
    sentinel from claim() remains. A concurrent/sequential retry hitting that
    sentinel returns 409 in-flight -- not a second mutation.
    """

    async def test_concurrent_retry_hits_in_flight_409(self) -> None:
        store = InMemoryIdempotencyStore()
        counter = _ExecutionCounter()
        app = _create_app(store, caller_service=_S2S_SERVICE, counter=counter)
        store.finalize = _returns_false_finalize  # type: ignore[assignment]

        with patch(_METRIC_PATCH_PATH, create=True):
            resp1 = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)
            assert resp1.status_code == 500
            # Sentinel still 'processing' after finalize-fail.
            stored = await store.get(
                f"{_S2S_SERVICE}#{_VALID_KEY}",
                "POST#/v1/intake/business",
            )
            assert stored is not None
            assert stored.status == "processing", (
                f"Sentinel must remain 'processing' after finalize-fail; got {stored.status!r}"
            )
            resp2 = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        assert resp2.status_code == 409
        assert counter.count == 1, (
            f"EC-2: concurrent contract intact -- exactly one mutation; got {counter.count}."
        )


# ===========================================================================
# SCAR-IDEM-001 (preserved): legacy raise-based observability still holds
# ===========================================================================


@pytest.mark.scar
class TestLegacyRaiseFinalizeObservability:
    """The original SCAR fix (finalize RAISES -> logger surfaces it) is preserved.

    The O2 contract reads the bool return, but a store that RAISES (rather than
    returning False) must still be surfaced rather than crashing the request.
    This guards the defensive try/except that wraps finalize.
    """

    async def test_finalize_raise_is_surfaced_not_propagated(self) -> None:
        store = InMemoryIdempotencyStore()
        app = _create_app(store, caller_service=None)

        async def raising_finalize(*args: Any, **kwargs: Any) -> bool:
            raise OSError("DynamoDB write failed")

        store.finalize = raising_finalize  # type: ignore[assignment]

        mock_logger = MagicMock()
        with patch(_MIDDLEWARE_LOGGER_PATH, mock_logger), patch(_METRIC_PATCH_PATH, create=True):
            resp = await _post(app, key=_VALID_KEY, body=_BUSINESS_BODY)

        # PAT caller: a raised finalize must not crash the request; the handler
        # response is still returned and the failure is surfaced via logging.
        assert resp.status_code == 201, (
            f"A raised finalize must be caught (not propagated as 500 for a PAT "
            f"caller); got {resp.status_code}."
        )
        assert mock_logger.error.called or mock_logger.exception.called, (
            "A raised finalize must be surfaced via logger.error/exception."
        )
