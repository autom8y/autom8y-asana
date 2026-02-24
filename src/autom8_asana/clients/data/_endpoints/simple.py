"""Simple endpoint implementations for DataServiceClient.

Private module holding get_appointments and get_leads functions extracted
from DataServiceClient.get_appointments_async and get_leads_async. These
endpoints share identical structure: feature check, circuit breaker, retry,
error handling, success parsing.

Per WS-DSC: S2-S8 orchestration delegated to DefaultEndpointPolicy.

This module is NOT part of the public API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.clients.data import _retry as _retry_mod
from autom8_asana.clients.data._policy import (
    DefaultEndpointPolicy,
    SimpleRequestDescriptor,
)
from autom8_asana.exceptions import InsightsServiceError

if TYPE_CHECKING:
    from autom8y_http import CircuitBreakerOpenError, Response

    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.clients.data.models import InsightsResponse


# ---------------------------------------------------------------------------
# Shared pluggable behaviors for simple GET endpoints
# ---------------------------------------------------------------------------


def _cb_error_factory(
    e: CircuitBreakerOpenError, request: SimpleRequestDescriptor
) -> Any:
    """Convert CB open error to InsightsServiceError (always raises)."""
    raise InsightsServiceError(
        f"Circuit breaker open. Retry in {e.time_remaining:.1f}s.",
        request_id=request.request_id,
        reason="circuit_breaker",
    ) from e


def _request_builder(http_client: Any, request: SimpleRequestDescriptor) -> Any:
    """Build the make_request lambda for a simple GET endpoint."""
    return lambda: http_client.get(
        request.path,
        params=request.params,
        headers={"X-Request-Id": request.request_id},
    )


async def _error_handler(
    response: Response,
    request: SimpleRequestDescriptor,
    elapsed_ms: float,
    *,
    client: DataServiceClient,
) -> InsightsResponse:
    """Delegate to client._handle_error_response for simple endpoints."""
    return await client._handle_error_response(
        response,
        request.request_id,
        request.cache_key,
        request.factory_label,
        elapsed_ms,
    )


async def _success_handler(
    response: Response,
    request: SimpleRequestDescriptor,
    elapsed_ms: float,
    *,
    client: DataServiceClient,
) -> InsightsResponse:
    """Parse success response + record CB success for simple endpoints."""
    insights_response = client._parse_success_response(response, request.request_id)
    await client._circuit_breaker.record_success()
    return insights_response


# ---------------------------------------------------------------------------
# Public endpoint functions
# ---------------------------------------------------------------------------


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

    # S1: Pre-flight
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

    # Build retry callbacks (S4 input, built here per TDD ADR-DSC-005)
    _callbacks = _retry_mod.build_retry_callbacks(
        circuit_breaker=client._circuit_breaker,
        error_class=InsightsServiceError,
        timeout_message="Appointments request timed out",
        http_error_template="HTTP error during appointments fetch: {e}",
        error_kwargs={"request_id": request_id},
    )

    # Build request descriptor
    descriptor = SimpleRequestDescriptor(
        path="/api/v1/appointments",
        params={
            "office_phone": office_phone,
            "days": str(days),
            "limit": str(limit),
        },
        request_id=request_id,
        cache_key=f"appointments:{masked_phone}",
        factory_label="appointments",
        retry_callbacks=_callbacks,
    )

    # S2-S8: Execute via policy
    policy: DefaultEndpointPolicy[SimpleRequestDescriptor, InsightsResponse] = (
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

    # Completion logging (post S8)
    _client_mod.logger.info(
        "appointments_request_completed",
        office_phone=masked_phone,
        row_count=insights_response.metadata.row_count,
        duration_ms=0.0,  # Timing is internal to policy; log for tracing only
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

    # S1: Pre-flight
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

    # Build retry callbacks
    _callbacks = _retry_mod.build_retry_callbacks(
        circuit_breaker=client._circuit_breaker,
        error_class=InsightsServiceError,
        timeout_message="Leads request timed out",
        http_error_template="HTTP error during leads fetch: {e}",
        error_kwargs={"request_id": request_id},
    )

    # Build params
    params: dict[str, str] = {
        "office_phone": office_phone,
        "days": str(days),
        "limit": str(limit),
    }
    if exclude_appointments:
        params["exclude_appointments"] = "true"

    # Build request descriptor
    descriptor = SimpleRequestDescriptor(
        path="/api/v1/leads",
        params=params,
        request_id=request_id,
        cache_key=f"leads:{masked_phone}",
        factory_label="leads",
        retry_callbacks=_callbacks,
    )

    # S2-S8: Execute via policy
    policy: DefaultEndpointPolicy[SimpleRequestDescriptor, InsightsResponse] = (
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
        "leads_request_completed",
        office_phone=masked_phone,
        row_count=insights_response.metadata.row_count,
        duration_ms=0.0,
        request_id=request_id,
    )

    return insights_response
