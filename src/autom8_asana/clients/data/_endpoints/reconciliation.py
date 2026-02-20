"""Reconciliation endpoint implementation for DataServiceClient.

Private module holding get_reconciliation function extracted from
DataServiceClient.get_reconciliation_async. Posts to
POST /api/v1/insights/reconciliation/execute (InsightExecutor path).

This module is NOT part of the public API.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from autom8y_http import CircuitBreakerOpenError as SdkCircuitBreakerOpenError

from autom8_asana.clients.data import _retry as _retry_mod
from autom8_asana.clients.data.models import InsightsResponse
from autom8_asana.exceptions import InsightsServiceError

if TYPE_CHECKING:
    from autom8_asana.clients.data.client import DataServiceClient


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

    # Circuit breaker check
    try:
        await client._circuit_breaker.check()
    except SdkCircuitBreakerOpenError as e:
        raise InsightsServiceError(
            f"Circuit breaker open. Retry in {e.time_remaining:.1f}s.",
            request_id=request_id,
            reason="circuit_breaker",
        ) from e

    http_client = await client._get_client()
    path = "/api/v1/insights/reconciliation/execute"

    # Build request body per TDD Section 2.1
    body: dict[str, str | int | None] = {
        "business": office_phone,
        "vertical": vertical,
    }
    if period is not None:
        body["period"] = period
    if window_days is not None:
        body["window_days"] = window_days

    start_time = time.monotonic()

    _callbacks = _retry_mod.build_retry_callbacks(
        circuit_breaker=client._circuit_breaker,
        error_class=InsightsServiceError,
        timeout_message="Reconciliation request timed out",
        http_error_template="HTTP error during reconciliation fetch: {e}",
        error_kwargs={"request_id": request_id},
    )

    response, _attempt = await client._execute_with_retry(
        lambda: http_client.post(
            path,
            json=body,
            headers={"X-Request-Id": request_id},
        ),
        on_timeout_exhausted=_callbacks.on_timeout_exhausted,
        on_http_error=_callbacks.on_http_error,
    )

    elapsed_ms = (time.monotonic() - start_time) * 1000

    if response.status_code >= 400:
        cache_key = f"reconciliation:{masked_phone}"
        return await client._handle_error_response(
            response, request_id, cache_key, "reconciliation", elapsed_ms
        )

    insights_response = client._parse_success_response(response, request_id)
    await client._circuit_breaker.record_success()

    _client_mod.logger.info(
        "reconciliation_request_completed",
        office_phone=masked_phone,
        row_count=insights_response.metadata.row_count,
        window_days=window_days,
        duration_ms=elapsed_ms,
        request_id=request_id,
    )

    return insights_response
