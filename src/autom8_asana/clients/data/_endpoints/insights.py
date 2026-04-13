"""Insights endpoint implementation for DataServiceClient.

Private module holding the execute_insights_request function extracted
from DataServiceClient._execute_insights_request. The class method becomes
a thin delegation wrapper.

Per WS-DSC: S2-S8 orchestration delegated to DefaultEndpointPolicy.

This module is NOT part of the public API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.clients.data import _normalize as _normalize_mod
from autom8_asana.clients.data import _retry as _retry_mod
from autom8_asana.clients.data._policy import (
    DefaultEndpointPolicy,
    InsightsRequestDescriptor,
)
from autom8_asana.errors import InsightsServiceError

if TYPE_CHECKING:
    from autom8y_http import CircuitBreakerOpenError, Response

    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.clients.data.models import InsightsRequest, InsightsResponse


# ---------------------------------------------------------------------------
# Pluggable behaviors
# ---------------------------------------------------------------------------


def _cb_error_factory(
    e: CircuitBreakerOpenError, request: InsightsRequestDescriptor
) -> Any:
    """Convert CB open error to InsightsServiceError (always raises)."""
    raise InsightsServiceError(
        f"Circuit breaker open. Service appears degraded. "
        f"Retry in {e.time_remaining:.1f}s.",
        request_id=request.request_id,
        reason="circuit_breaker",
    ) from e


def _request_builder(http_client: Any, request: InsightsRequestDescriptor) -> Any:
    """Build the make_request lambda for insights POST."""
    return lambda: http_client.post(
        request.path,
        json=request.request_body,
        headers={"X-Request-Id": request.request_id},
    )


def _make_pre_execute_error_handler(
    client: DataServiceClient,
    cache_key: str,
    request_id: str,
) -> Any:
    """Build the stale-cache fallback handler for insights.

    Returns a callable: (Exception, InsightsRequestDescriptor) -> InsightsResponse | None
    """

    def handler(
        exc: Exception, request: InsightsRequestDescriptor
    ) -> InsightsResponse | None:
        if isinstance(exc, InsightsServiceError):
            stale_response = client._get_stale_response(cache_key, request_id)
            if stale_response is not None:
                return stale_response
        return None

    return handler


async def _error_handler(
    response: Response,
    request: InsightsRequestDescriptor,
    elapsed_ms: float,
    *,
    client: DataServiceClient,
) -> InsightsResponse:
    """Delegate to client._handle_error_response for insights."""
    return await client._handle_error_response(
        response,
        request.request_id,
        request.cache_key,
        request.factory,
        elapsed_ms,
    )


async def _success_handler(
    response: Response,
    request: InsightsRequestDescriptor,
    elapsed_ms: float,
    *,
    client: DataServiceClient,
    attempt: int = 0,
) -> InsightsResponse:
    """Parse success + record metrics + cache for insights endpoint."""
    insights_response = client._parse_success_response(response, request.request_id)

    # Response logging (Story 1.9)
    if client._log:
        client._log.info(
            "insights_request_completed",
            extra={
                "request_id": request.request_id,
                "row_count": insights_response.metadata.row_count,
                "cache_hit": insights_response.metadata.cache_hit,
                "is_stale": insights_response.metadata.is_stale,
                "duration_ms": elapsed_ms,
                "attempt": 1,  # Attempt count is internal to retry loop
            },
        )

    # Success metrics (Story 1.9)
    client._emit_metric(
        "insights_request_total",
        1,
        {"factory": request.factory, "status": "success"},
    )
    client._emit_metric(
        "insights_request_latency_ms",
        elapsed_ms,
        {"factory": request.factory, "status": "success"},
    )

    # Circuit breaker record success (Story 2.3)
    await client._circuit_breaker.record_success()

    # Cache successful response (Story 1.8)
    client._cache_response(request.cache_key, insights_response)

    return insights_response


# ---------------------------------------------------------------------------
# Public endpoint function
# ---------------------------------------------------------------------------


async def execute_insights_request(
    client: DataServiceClient,
    factory: str,
    request: InsightsRequest,
    request_id: str,
    cache_key: str,
) -> InsightsResponse:
    """Execute HTTP POST to insights factory endpoint with cache support.

    HTTP execution with error mapping, cache support, observability,
    retry with exponential backoff, and circuit breaker integration.

    Cache Flow:
    1. Check circuit breaker (fast-fail if open)
    2. Try HTTP request to autom8_data with retry on transient failures
    3. On success: record success, store in cache, return fresh response
    4. On InsightsServiceError: record failure, try stale cache fallback
    5. If stale entry exists: return with is_stale=True
    6. If no stale entry: re-raise original error

    Args:
        client: DataServiceClient instance providing config, log, circuit breaker, etc.
        factory: Validated factory name.
        request: InsightsRequest with validated parameters.
        request_id: UUID for request tracing.
        cache_key: Pre-built cache key for storage and fallback.

    Returns:
        InsightsResponse parsed from successful response, or stale cache fallback.

    Raises:
        InsightsValidationError: 400-level errors (no cache fallback).
        InsightsNotFoundError: 404 errors (no cache fallback).
        InsightsServiceError: 500-level errors if no stale cache available,
            or circuit breaker is open (reason="circuit_breaker").
    """
    # Import here to avoid circular import at module level
    from autom8_asana.clients.data._pii import mask_canonical_key as _mask_canonical_key

    # S1: Pre-flight (logging, body construction)
    path = "/api/v1/data-service/insights"

    # Build PII-safe canonical key for logging (Story 1.9)
    pvp_canonical_key = f"pv1:{request.office_phone}:{request.vertical}"
    masked_pvp_key = _mask_canonical_key(pvp_canonical_key)

    # Map factory to frame_type
    frame_type = client.FACTORY_TO_FRAME_TYPE[factory]

    # Normalize period to autom8_data format
    period = _normalize_mod.normalize_period(request.insights_period)

    # Transform request body to autom8_data format
    request_body: dict[str, Any] = {
        "frame_type": frame_type,
        "phone_vertical_pairs": [
            {
                "phone": request.office_phone,
                "vertical": request.vertical,
            }
        ],
        "period": period,
    }

    # Add optional parameters if present
    if request.start_date is not None:
        request_body["start_date"] = request.start_date.isoformat()
    if request.end_date is not None:
        request_body["end_date"] = request.end_date.isoformat()
    if request.metrics is not None:
        request_body["metrics"] = request.metrics
    if request.dimensions is not None:
        request_body["dimensions"] = request.dimensions
    if request.groups is not None:
        request_body["groups"] = request.groups
    if request.break_down is not None:
        request_body["break_down"] = request.break_down
    if request.refresh:
        request_body["refresh"] = request.refresh
    if request.filters:
        request_body["filters"] = request.filters
    if request.include_unused:
        request_body["include_unused"] = True

    # Request logging (Story 1.9)
    if client._log:
        client._log.info(
            "insights_request_started",
            extra={
                "factory": factory,
                "frame_type": frame_type,
                "period": period,
                "pvp_canonical_key": masked_pvp_key,
                "request_id": request_id,
            },
        )

    # Build retry callbacks
    # start_time is used by retry callbacks for their own elapsed_ms metrics
    import time

    start_time = time.monotonic()

    _callbacks = _retry_mod.build_retry_callbacks(
        circuit_breaker=client._circuit_breaker,
        error_class=InsightsServiceError,
        timeout_message="Request to autom8_data timed out",
        http_error_template="HTTP error communicating with autom8_data: {e}",
        error_kwargs={"request_id": request_id},
        log=client._log,
        log_event_retry="insights_request_retry",
        log_event_fail="insights_request_failed",
        max_retries=client._config.retry.max_retries,
        emit_metric=client._emit_metric,
        metric_tags={"factory": factory},
        start_time=start_time,
    )

    # Build request descriptor
    descriptor = InsightsRequestDescriptor(
        path=path,
        request_body=request_body,
        request_id=request_id,
        cache_key=cache_key,
        factory=factory,
        retry_callbacks=_callbacks,
    )

    # S2-S8: Execute via policy (with stale cache fallback)
    policy: DefaultEndpointPolicy[InsightsRequestDescriptor, InsightsResponse] = (
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
            pre_execute_error_handler=_make_pre_execute_error_handler(
                client, cache_key, request_id
            ),
        )
    )

    return await policy.execute(descriptor)
