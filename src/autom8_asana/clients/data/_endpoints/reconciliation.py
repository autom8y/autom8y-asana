"""Reconciliation endpoint implementation for DataServiceClient.

Private module holding get_reconciliation function extracted from
DataServiceClient.get_reconciliation_async. Posts to
POST /api/v1/insights/reconciliation/execute (InsightExecutor path).

Per WS-DSC: S2-S8 orchestration delegated to DefaultEndpointPolicy.

This module is NOT part of the public API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.clients.data import _retry as _retry_mod
from autom8_asana.clients.data._policy import (
    DefaultEndpointPolicy,
    ReconciliationRequestDescriptor,
)
from autom8_asana.exceptions import InsightsServiceError

if TYPE_CHECKING:
    from autom8y_http import CircuitBreakerOpenError, Response

    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.clients.data.models import InsightsResponse


# ---------------------------------------------------------------------------
# Pluggable behaviors
# ---------------------------------------------------------------------------


def _cb_error_factory(
    e: CircuitBreakerOpenError, request: ReconciliationRequestDescriptor
) -> Any:
    """Convert CB open error to InsightsServiceError (always raises)."""
    raise InsightsServiceError(
        f"Circuit breaker open. Retry in {e.time_remaining:.1f}s.",
        request_id=request.request_id,
        reason="circuit_breaker",
    ) from e


def _request_builder(
    http_client: Any, request: ReconciliationRequestDescriptor
) -> Any:
    """Build the make_request lambda for reconciliation POST."""
    return lambda: http_client.post(
        request.path,
        json=request.body,
        headers={"X-Request-Id": request.request_id},
    )


async def _error_handler(
    response: Response,
    request: ReconciliationRequestDescriptor,
    elapsed_ms: float,
    *,
    client: DataServiceClient,
) -> InsightsResponse:
    """Delegate to client._handle_error_response."""
    return await client._handle_error_response(
        response,
        request.request_id,
        request.cache_key,
        request.factory_label,
        elapsed_ms,
    )


async def _success_handler(
    response: Response,
    request: ReconciliationRequestDescriptor,
    elapsed_ms: float,
    *,
    client: DataServiceClient,
) -> InsightsResponse:
    """Parse success response + record CB success."""
    insights_response = client._parse_success_response(
        response, request.request_id
    )
    await client._circuit_breaker.record_success()
    return insights_response


# ---------------------------------------------------------------------------
# Public endpoint function
# ---------------------------------------------------------------------------


async def get_reconciliation(
    client: DataServiceClient,
    office_phone: str,
    vertical: str,
    *,
    period: str | None = None,
    window_days: int | None = None,
) -> InsightsResponse:
    """Fetch reconciliation data via POST /insights/reconciliation/execute.

    Per TDD-WS5 Part 2 Section 2.1: Maps to the InsightExecutor path on
    autom8_data, NOT the InsightsService/FrameTypeMapper path.

    Args:
        client: DataServiceClient instance providing config, log, circuit breaker, etc.
        office_phone: E.164 formatted phone number.
        vertical: Business vertical.
        period: Time period preset. None = LIFETIME (all data).
        window_days: Window size in days for windowed output. None = flat.

    Returns:
        InsightsResponse with reconciliation data rows.

    Raises:
        InsightsServiceError: Upstream service failure.
        InsightsNotFoundError: No data found.
    """
    import uuid

    import autom8_asana.clients.data.client as _client_mod

    # S1: Pre-flight
    client._check_feature_enabled()

    request_id = str(uuid.uuid4())
    masked_phone = _client_mod.mask_phone_number(office_phone)

    _client_mod.logger.info(
        "reconciliation_request_started",
        office_phone=masked_phone,
        vertical=vertical,
        period=period,
        window_days=window_days,
        request_id=request_id,
    )

    # Build request body per TDD Section 2.1
    body: dict[str, str | int | None] = {
        "business": office_phone,
        "vertical": vertical,
    }
    if period is not None:
        body["period"] = period
    if window_days is not None:
        body["window_days"] = window_days

    # Build retry callbacks
    _callbacks = _retry_mod.build_retry_callbacks(
        circuit_breaker=client._circuit_breaker,
        error_class=InsightsServiceError,
        timeout_message="Reconciliation request timed out",
        http_error_template="HTTP error during reconciliation fetch: {e}",
        error_kwargs={"request_id": request_id},
    )

    # Build request descriptor
    descriptor = ReconciliationRequestDescriptor(
        path="/api/v1/insights/reconciliation/execute",
        body=body,
        request_id=request_id,
        cache_key=f"reconciliation:{masked_phone}",
        factory_label="reconciliation",
        retry_callbacks=_callbacks,
    )

    # S2-S8: Execute via policy
    policy: DefaultEndpointPolicy[ReconciliationRequestDescriptor, InsightsResponse] = (
        DefaultEndpointPolicy(
            circuit_breaker=client._circuit_breaker,
            get_client=client._get_client,
            execute_with_retry=client._execute_with_retry,
            cb_error_factory=_cb_error_factory,
            request_builder=_request_builder,
            error_handler=lambda resp, req, ms: _error_handler(
                resp, req, ms, client=client
            ),
            success_handler=lambda resp, req, ms: _success_handler(
                resp, req, ms, client=client
            ),
        )
    )

    insights_response = await policy.execute(descriptor)

    # Completion logging
    _client_mod.logger.info(
        "reconciliation_request_completed",
        office_phone=masked_phone,
        row_count=insights_response.metadata.row_count,
        window_days=window_days,
        duration_ms=0.0,
        request_id=request_id,
    )

    return insights_response
