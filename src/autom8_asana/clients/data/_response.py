"""Response parsing and error handling for DataServiceClient.

Private module extracted from client.py to separate response concerns from
the main client class. Functions are module-level to enable independent
testing and reduce class surface area.

These functions are NOT part of the public API -- they are imported and
used by DataServiceClient internally.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.clients.data.models import (
    ColumnInfo,
    InsightsMetadata,
    InsightsResponse,
)
from autom8_asana.errors import (
    InsightsNotFoundError,
    InsightsServiceError,
    InsightsValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from autom8y_http import Response

    from autom8_asana.protocols.log import LogProvider

logger = get_logger(__name__)


def validate_factory(factory: str, request_id: str, valid_factories: frozenset[str]) -> None:
    """Validate factory name against allowed set.

    Args:
        factory: Normalized (lowercase) factory name to validate.
        request_id: Request ID for error context.
        valid_factories: Set of valid factory names.

    Raises:
        InsightsValidationError: If factory name is not valid.
    """
    if factory not in valid_factories:
        raise InsightsValidationError(
            f"Invalid factory: '{factory}'. Valid factories: {', '.join(sorted(valid_factories))}",
            field="factory",
            request_id=request_id,
        )


async def handle_error_response(
    response: Response,
    request_id: str,
    cache_key: str,
    factory: str,
    elapsed_ms: float,
    *,
    log: LogProvider | Any | None,
    emit_metric: Callable[[str, float, dict[str, str]], None],
    record_circuit_failure: Callable[[Exception], Awaitable[None]],
    get_stale_response: Callable[[str, str], InsightsResponse | None],
) -> InsightsResponse:
    """Map HTTP error response to appropriate exception.

    Error response mapping with stale cache fallback for 5xx errors,
    structured logging, and circuit breaker failure recording.

    Args:
        response: HTTP response with status >= 400.
        request_id: Request ID for error context.
        cache_key: Cache key for stale fallback on 5xx errors.
        factory: Factory name for metrics tags.
        elapsed_ms: Request duration in milliseconds.
        log: Logger instance for structured logging.
        emit_metric: Callback to emit metrics.
        record_circuit_failure: Async callback to record circuit breaker failure.
        get_stale_response: Callback to retrieve stale cache response.

    Returns:
        InsightsResponse from stale cache fallback (only for 5xx errors).

    Raises:
        InsightsValidationError: 400 errors (no cache fallback).
        InsightsNotFoundError: 404 errors (no cache fallback).
        InsightsServiceError: 500-level errors if no stale cache available.

    Note: For 4xx errors, this function always raises (no cache fallback).
    """
    status = response.status_code
    message = f"autom8_data API error (HTTP {status})"

    # Try to extract error message from response body
    try:
        body = response.json()
        if "error" in body:
            message = body["error"]
        elif "detail" in body:
            message = body["detail"]
    except (ValueError, KeyError, json.JSONDecodeError):
        # Use default message if body parsing fails
        logger.debug("Response body parsing failed", exc_info=True)

    # Determine error type for logging/metrics
    if status == 400:
        error_type = "validation_error"
        reason = "validation_error"
    elif status == 404:
        error_type = "not_found"
        reason = "not_found"
    elif status >= 500:
        error_type = "server_error"
        reason = "server_error"
    else:
        error_type = "client_error"
        reason = "client_error"

    # --- Error Logging (Story 1.9) ---
    if log:
        log.error(
            "insights_request_failed",
            extra={
                "request_id": request_id,
                "status_code": status,
                "error_type": error_type,
                "reason": reason,
                "duration_ms": elapsed_ms,
            },
        )

    # --- Error Metrics (Story 1.9) ---
    emit_metric(
        "insights_request_error_total",
        1,
        {"factory": factory, "error_type": error_type, "status_code": str(status)},
    )
    emit_metric(
        "insights_request_total",
        1,
        {"factory": factory, "status": "error"},
    )
    emit_metric(
        "insights_request_latency_ms",
        elapsed_ms,
        {"factory": factory, "status": "error"},
    )

    # Map status code to exception type
    if status == 400:
        # No cache fallback for validation errors
        raise InsightsValidationError(
            message,
            request_id=request_id,
        )
    elif status == 404:
        # No cache fallback for not found errors
        raise InsightsNotFoundError(
            message,
            request_id=request_id,
        )
    else:
        # 500, 502, 503, 504 and any other 5xx - try stale cache fallback
        if status >= 500:
            # --- Circuit Breaker Record Failure (Story 2.3) ---
            # Create an exception to pass to the circuit breaker
            error = InsightsServiceError(
                message,
                request_id=request_id,
                status_code=status,
                reason=reason,
            )
            await record_circuit_failure(error)

            stale_response = get_stale_response(cache_key, request_id)
            if stale_response is not None:
                return stale_response

            raise error

        raise InsightsServiceError(
            message,
            request_id=request_id,
            status_code=status,
            reason=reason,
        )


def parse_success_response(
    response: Response,
    request_id: str,
    log: LogProvider | Any | None,
) -> InsightsResponse:
    """Parse successful HTTP response to InsightsResponse.

    Per TDD-INSIGHTS-001 Section 4.3: Response parsing.

    Args:
        response: HTTP response with status 2xx.
        request_id: Request ID for response correlation.
        log: Logger instance for structured logging.

    Returns:
        InsightsResponse with data, metadata, and warnings.

    Raises:
        InsightsServiceError: If response body cannot be parsed.
    """
    try:
        body = response.json()
    except (ValueError, json.JSONDecodeError) as e:
        raise InsightsServiceError(
            f"Failed to parse response JSON: {e}",
            request_id=request_id,
            reason="parse_error",
        ) from e

    try:
        # Parse metadata
        metadata_dict = body.get("metadata", {})
        columns = [ColumnInfo(**col) for col in metadata_dict.get("columns", [])]

        metadata = InsightsMetadata(
            factory=metadata_dict.get("factory", "unknown"),
            frame_type=metadata_dict.get("frame_type"),
            insights_period=metadata_dict.get("insights_period"),
            row_count=metadata_dict.get("row_count", 0),
            column_count=metadata_dict.get("column_count", 0),
            columns=columns,
            cache_hit=metadata_dict.get("cache_hit", False),
            duration_ms=metadata_dict.get("duration_ms", 0.0),
            sort_history=metadata_dict.get("sort_history"),
            is_stale=metadata_dict.get("is_stale", False),
            cached_at=metadata_dict.get("cached_at"),
        )

        insights_response = InsightsResponse(
            data=body.get("data", []),
            metadata=metadata,
            request_id=request_id,
            warnings=body.get("warnings", []),
        )

        if log:
            log.debug(
                "DataServiceClient: Response parsed successfully",
                extra={
                    "request_id": request_id,
                    "row_count": metadata.row_count,
                    "cache_hit": metadata.cache_hit,
                    "duration_ms": metadata.duration_ms,
                },
            )

        return insights_response

    except (ValueError, KeyError, TypeError) as e:
        raise InsightsServiceError(
            f"Failed to parse response structure: {e}",
            request_id=request_id,
            reason="parse_error",
        ) from e
