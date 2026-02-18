"""Insights endpoint implementation for DataServiceClient.

Private module holding the execute_insights_request function extracted
from DataServiceClient._execute_insights_request. The class method becomes
a thin delegation wrapper.

This module is NOT part of the public API.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from autom8y_http import CircuitBreakerOpenError as SdkCircuitBreakerOpenError

from autom8_asana.clients.data import _normalize as _normalize_mod
from autom8_asana.clients.data import _retry as _retry_mod
from autom8_asana.clients.data.models import InsightsResponse
from autom8_asana.exceptions import InsightsServiceError

if TYPE_CHECKING:
    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.clients.data.models import InsightsRequest


async def execute_insights_request(
    client: DataServiceClient,
    factory: str,
    request: InsightsRequest,
    request_id: str,
    cache_key: str,
) -> InsightsResponse:
    """Execute HTTP POST to insights factory endpoint with cache support.

    Per TDD-INSIGHTS-001 Section 5.1: HTTP execution with error mapping.
    Per Story 1.8: Cache successful responses and fall back to stale cache
    on service errors.
    Per Story 1.9: Full observability with structured logging and metrics.
    Per Story 2.2: Retry with exponential backoff on transient failures.
    Per Story 2.3: Circuit breaker integration for cascade failure prevention.

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
    from autom8_asana.clients.data.client import _mask_canonical_key

    # --- Circuit Breaker Check (Story 2.3) ---
    # Fast-fail if circuit is open to prevent cascade failures
    try:
        await client._circuit_breaker.check()
    except SdkCircuitBreakerOpenError as e:
        # Convert SDK error to domain error (autom8y-http >= 0.3.0)
        raise InsightsServiceError(
            f"Circuit breaker open. Service appears degraded. "
            f"Retry in {e.time_remaining:.1f}s.",
            request_id=request_id,
            reason="circuit_breaker",
        ) from e

    http_client = await client._get_client()
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

    # Start timing for latency metrics (Story 1.9)
    start_time = time.monotonic()

    # --- Request Logging (Story 1.9) ---
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

    # --- Retry Callbacks ---
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

    # --- Retry Loop with Stale Fallback (Story 2.2, Story 1.8) ---
    # Note: W3C traceparent is auto-injected by HTTPXClientInstrumentor.
    # X-Request-Id is kept for backwards compatibility with autom8y-data's
    # RequestIDMiddleware, which uses it for non-OTEL correlation.
    try:
        response, attempt = await client._execute_with_retry(
            lambda: http_client.post(
                path,
                json=request_body,
                headers={"X-Request-Id": request_id},
            ),
            on_retry=_callbacks.on_retry,
            on_timeout_exhausted=_callbacks.on_timeout_exhausted,
            on_http_error=_callbacks.on_http_error,
        )
    except InsightsServiceError:
        # Try stale cache fallback on service errors (Story 1.8)
        stale_response = client._get_stale_response(cache_key, request_id)
        if stale_response is not None:
            return stale_response
        raise

    # Calculate elapsed time
    elapsed_ms = (time.monotonic() - start_time) * 1000

    # Handle error responses (if we got here after retries exhausted or non-retryable error)
    if response is not None and response.status_code >= 400:
        return await client._handle_error_response(
            response, request_id, cache_key, factory, elapsed_ms
        )

    # Parse successful response
    insights_response = client._parse_success_response(response, request_id)

    # --- Response Logging (Story 1.9) ---
    if client._log:
        client._log.info(
            "insights_request_completed",
            extra={
                "request_id": request_id,
                "row_count": insights_response.metadata.row_count,
                "cache_hit": insights_response.metadata.cache_hit,
                "is_stale": insights_response.metadata.is_stale,
                "duration_ms": elapsed_ms,
                "attempt": attempt + 1,
            },
        )

    # --- Success Metrics (Story 1.9) ---
    client._emit_metric(
        "insights_request_total",
        1,
        {"factory": factory, "status": "success"},
    )
    client._emit_metric(
        "insights_request_latency_ms",
        elapsed_ms,
        {"factory": factory, "status": "success"},
    )

    # --- Circuit Breaker Record Success (Story 2.3) ---
    await client._circuit_breaker.record_success()

    # Cache successful response (Story 1.8)
    client._cache_response(cache_key, insights_response)

    return insights_response
