"""Simple endpoint implementations for DataServiceClient.

Private module holding get_appointments and get_leads functions extracted
from DataServiceClient.get_appointments_async and get_leads_async. These
endpoints share identical structure: feature check, circuit breaker, retry,
error handling, success parsing.

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


async def get_appointments(
    client: DataServiceClient,
    office_phone: str,
    *,
    days: int,
    limit: int,
) -> InsightsResponse:
    """Fetch appointment detail rows for a business.

    Per TDD-EXPORT-001 W04: Maps to GET /appointments on autom8_data.

    Args:
        client: DataServiceClient instance providing config, log, circuit breaker, etc.
        office_phone: E.164 formatted phone number.
        days: Lookback window in days.
        limit: Maximum rows to return.

    Returns:
        InsightsResponse with appointment detail rows.

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
        "appointments_request_started",
        office_phone=masked_phone,
        days=days,
        limit=limit,
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
    path = "/api/v1/appointments"
    params = {
        "office_phone": office_phone,
        "days": str(days),
        "limit": str(limit),
    }

    start_time = time.monotonic()

    _callbacks = _retry_mod.build_retry_callbacks(
        circuit_breaker=client._circuit_breaker,
        error_class=InsightsServiceError,
        timeout_message="Appointments request timed out",
        http_error_template="HTTP error during appointments fetch: {e}",
        error_kwargs={"request_id": request_id},
    )

    # Note: W3C traceparent is auto-injected by HTTPXClientInstrumentor.
    # X-Request-Id is kept for backwards compatibility.
    response, _attempt = await client._execute_with_retry(
        lambda: http_client.get(
            path,
            params=params,
            headers={"X-Request-Id": request_id},
        ),
        on_timeout_exhausted=_callbacks.on_timeout_exhausted,
        on_http_error=_callbacks.on_http_error,
    )

    elapsed_ms = (time.monotonic() - start_time) * 1000

    if response.status_code >= 400:
        cache_key = f"appointments:{masked_phone}"
        return await client._handle_error_response(
            response, request_id, cache_key, "appointments", elapsed_ms
        )

    insights_response = client._parse_success_response(response, request_id)
    await client._circuit_breaker.record_success()

    _client_mod.logger.info(
        "appointments_request_completed",
        office_phone=masked_phone,
        row_count=insights_response.metadata.row_count,
        duration_ms=elapsed_ms,
        request_id=request_id,
    )

    return insights_response


async def get_leads(
    client: DataServiceClient,
    office_phone: str,
    *,
    days: int,
    exclude_appointments: bool,
    limit: int,
) -> InsightsResponse:
    """Fetch lead detail rows for a business.

    Per TDD-EXPORT-001 W04: Maps to GET /leads on autom8_data.

    Args:
        client: DataServiceClient instance providing config, log, circuit breaker, etc.
        office_phone: E.164 formatted phone number.
        days: Lookback window in days.
        exclude_appointments: Exclude appointment leads.
        limit: Maximum rows to return.

    Returns:
        InsightsResponse with lead detail rows.

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
        "leads_request_started",
        office_phone=masked_phone,
        days=days,
        exclude_appointments=exclude_appointments,
        limit=limit,
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
    path = "/api/v1/leads"
    params: dict[str, str] = {
        "office_phone": office_phone,
        "days": str(days),
        "limit": str(limit),
    }
    if exclude_appointments:
        params["exclude_appointments"] = "true"

    start_time = time.monotonic()

    _callbacks = _retry_mod.build_retry_callbacks(
        circuit_breaker=client._circuit_breaker,
        error_class=InsightsServiceError,
        timeout_message="Leads request timed out",
        http_error_template="HTTP error during leads fetch: {e}",
        error_kwargs={"request_id": request_id},
    )

    # Note: W3C traceparent is auto-injected by HTTPXClientInstrumentor.
    # X-Request-Id is kept for backwards compatibility.
    response, _attempt = await client._execute_with_retry(
        lambda: http_client.get(
            path,
            params=params,
            headers={"X-Request-Id": request_id},
        ),
        on_timeout_exhausted=_callbacks.on_timeout_exhausted,
        on_http_error=_callbacks.on_http_error,
    )

    elapsed_ms = (time.monotonic() - start_time) * 1000

    if response.status_code >= 400:
        cache_key = f"leads:{masked_phone}"
        return await client._handle_error_response(
            response, request_id, cache_key, "leads", elapsed_ms
        )

    insights_response = client._parse_success_response(response, request_id)
    await client._circuit_breaker.record_success()

    _client_mod.logger.info(
        "leads_request_completed",
        office_phone=masked_phone,
        row_count=insights_response.metadata.row_count,
        duration_ms=elapsed_ms,
        request_id=request_id,
    )

    return insights_response
