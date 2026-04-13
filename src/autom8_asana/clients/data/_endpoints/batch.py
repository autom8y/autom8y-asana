"""Batch insights endpoint implementation for DataServiceClient.

Private module holding the execute_batch_request and build_entity_response
functions extracted from DataServiceClient. The class methods become thin
delegation wrappers.

Per WS-DSC: S2-S8 orchestration delegated to DefaultEndpointPolicy.

This module is NOT part of the public API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.clients.data import _normalize as _normalize_mod
from autom8_asana.clients.data import _retry as _retry_mod
from autom8_asana.clients.data._pii import mask_pii_in_string as _mask_pii_in_string
from autom8_asana.clients.data._policy import (
    BatchRequestDescriptor,
    DefaultEndpointPolicy,
)
from autom8_asana.clients.data.models import (
    BatchInsightsResult,
    InsightsResponse,
)
from autom8_asana.errors import InsightsError, InsightsServiceError

if TYPE_CHECKING:
    from autom8y_http import CircuitBreakerOpenError, Response

    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.models.contracts import PhoneVerticalPair


# ---------------------------------------------------------------------------
# Pluggable behaviors for batch endpoint
# ---------------------------------------------------------------------------


def _cb_error_factory(
    e: CircuitBreakerOpenError, request: BatchRequestDescriptor
) -> dict[str, BatchInsightsResult]:
    """Return error dict for all PVPs when CB is open (non-raising)."""
    error_msg = (
        f"Circuit breaker open. Service appears degraded. "
        f"Retry in {e.time_remaining:.1f}s."
    )
    results: dict[str, BatchInsightsResult] = {}
    for pvp in request.pvp_list:
        results[pvp.canonical_key] = BatchInsightsResult(
            pvp=pvp,
            error=error_msg,
        )
    return results


def _request_builder(http_client: Any, request: BatchRequestDescriptor) -> Any:
    """Build the make_request lambda for batch POST."""
    return lambda: http_client.post(
        request.path,
        json=request.request_body,
        headers={"X-Request-Id": request.request_id},
    )


def _make_pre_execute_error_handler(
    pvp_list: list[PhoneVerticalPair],
) -> Any:
    """Build the total-failure handler for batch.

    When execute_with_retry raises InsightsServiceError or InsightsError,
    mark all PVPs as errored (instead of re-raising).
    """

    def handler(
        exc: Exception, request: BatchRequestDescriptor
    ) -> dict[str, BatchInsightsResult] | None:
        if isinstance(exc, (InsightsServiceError, InsightsError)):
            sanitized_error = _mask_pii_in_string(str(exc))
            results: dict[str, BatchInsightsResult] = {}
            for pvp in pvp_list:
                results[pvp.canonical_key] = BatchInsightsResult(
                    pvp=pvp,
                    error=sanitized_error,
                )
            return results
        return None

    return handler


async def _error_handler(
    response: Response,
    request: BatchRequestDescriptor,
    elapsed_ms: float,
    *,
    client: DataServiceClient,
) -> dict[str, BatchInsightsResult]:
    """Handle HTTP error responses for batch (4xx/5xx, NOT 207)."""
    results: dict[str, BatchInsightsResult] = {}

    # HTTP 207 is partial success, not an error -- handled in success path
    if response.status_code == 207:
        # This should not happen because 207 < 400 would go to success_handler
        # but handle defensively
        return await _success_handler(response, request, elapsed_ms, client=client)

    error_msg = f"autom8_data API error (HTTP {response.status_code})"
    try:
        body = response.json()
        if "error" in body:
            error_msg = str(body["error"])
        elif "detail" in body:
            error_msg = str(body["detail"])
    except (ValueError, KeyError):
        pass

    # Sanitize error message to redact PII echoed by upstream (XR-003)
    error_msg = _mask_pii_in_string(error_msg)

    if response.status_code >= 500:
        error = InsightsServiceError(
            error_msg,
            request_id=request.request_id,
            status_code=response.status_code,
            reason="server_error",
        )
        await client._circuit_breaker.record_failure(error)

    for pvp in request.pvp_list:
        results[pvp.canonical_key] = BatchInsightsResult(
            pvp=pvp,
            error=error_msg,
        )
    return results


async def _success_handler(
    response: Response,
    request: BatchRequestDescriptor,
    elapsed_ms: float,
    *,
    client: DataServiceClient,
) -> dict[str, BatchInsightsResult]:
    """Parse successful / partial (207) batch response."""
    results: dict[str, BatchInsightsResult] = {}

    await client._circuit_breaker.record_success()

    try:
        body = response.json()
    except ValueError as e:
        error_msg = _mask_pii_in_string(f"Failed to parse response JSON: {e}")
        for pvp in request.pvp_list:
            results[pvp.canonical_key] = BatchInsightsResult(
                pvp=pvp,
                error=error_msg,
            )
        return results

    # Parse successful entity data from response
    data_list: list[dict[str, Any]] = body.get("data", [])
    response_metadata = body.get("metadata", {})
    warnings = body.get("warnings", [])

    # Group data rows by canonical key (supports multiple rows per PVP)
    rows_by_key: dict[str, list[dict[str, Any]]] = {}
    for row in data_list:
        row_phone = row.get("office_phone", "")
        row_vertical = row.get("vertical", "")
        canonical_key = f"pv1:{row_phone}:{row_vertical.lower()}"

        if canonical_key not in request.pvp_by_key:
            # Response contained a PVP we didn't request -- skip
            continue

        rows_by_key.setdefault(canonical_key, []).append(row)

    # Build per-PVP InsightsResponse from grouped rows
    for canonical_key, rows in rows_by_key.items():
        pvp = request.pvp_by_key[canonical_key]
        entity_response = build_entity_response(
            rows, response_metadata, request.request_id, warnings
        )
        results[canonical_key] = BatchInsightsResult(
            pvp=pvp,
            response=entity_response,
        )

    # Parse per-entity errors from response (HTTP 207 partial failures)
    errors_list: list[dict[str, Any]] = body.get("errors", [])
    for error_entry in errors_list:
        error_phone = error_entry.get("office_phone", "")
        error_vertical = error_entry.get("vertical", "")
        error_msg = _mask_pii_in_string(error_entry.get("error", "Unknown error"))
        canonical_key = f"pv1:{error_phone}:{error_vertical.lower()}"

        error_pvp = request.pvp_by_key.get(canonical_key)
        if error_pvp is not None and canonical_key not in results:
            results[canonical_key] = BatchInsightsResult(
                pvp=error_pvp,
                error=error_msg,
            )

    # Mark any remaining PVPs (not in data or errors) as failed
    for pvp in request.pvp_list:
        if pvp.canonical_key not in results:
            results[pvp.canonical_key] = BatchInsightsResult(
                pvp=pvp,
                error="No data returned for this PVP",
            )

    if client._log:
        client._log.info(
            "insights_batch_request_completed",
            extra={
                "request_id": request.request_id,
                "batch_size": len(request.pvp_list),
                "data_count": len(data_list),
                "error_count": len(errors_list),
                "duration_ms": elapsed_ms,
            },
        )

    return results


# ---------------------------------------------------------------------------
# Public endpoint functions
# ---------------------------------------------------------------------------


async def execute_batch_request(
    client: DataServiceClient,
    pvp_list: list[PhoneVerticalPair],
    factory: str,
    period: str,
    refresh: bool,
    request_id: str,
) -> dict[str, BatchInsightsResult]:
    """Execute a single batched HTTP POST with multiple PVPs.

    Per IMP-20: Sends all PVPs in one HTTP request to autom8_data's
    POST /api/v1/data-service/insights endpoint.

    autom8_data returns:
    - HTTP 200: All PVPs succeeded. Response body has ``data`` list
      with per-entity results containing ``office_phone`` and ``vertical``.
    - HTTP 207: Partial success. Response body has both ``data`` (successes)
      and ``errors`` (per-PVP error details).
    - HTTP 4xx/5xx: Total failure for the entire chunk.

    Args:
        client: DataServiceClient instance providing config, log, circuit breaker, etc.
        pvp_list: PVPs to include in this request (max 1000).
        factory: Validated, normalized factory name.
        period: Period preset (e.g., "lifetime").
        refresh: Whether to force cache refresh.
        request_id: Batch request correlation ID.

    Returns:
        Dict mapping canonical_key to BatchInsightsResult for each PVP.
    """
    import time

    # S1: Pre-flight -- build PVP lookup and request body
    pvp_by_key: dict[str, PhoneVerticalPair] = {
        pvp.canonical_key: pvp for pvp in pvp_list
    }

    path = "/api/v1/data-service/insights"

    # Map factory to frame_type
    frame_type = client.FACTORY_TO_FRAME_TYPE[factory]

    # Normalize period to autom8_data format
    normalized_period = _normalize_mod.normalize_period(period)

    # Build request body with all PVPs (IMP-20: multi-PVP batch)
    request_body: dict[str, Any] = {
        "frame_type": frame_type,
        "phone_vertical_pairs": [
            {"phone": pvp.office_phone, "vertical": pvp.vertical} for pvp in pvp_list
        ],
        "period": normalized_period,
    }

    if refresh:
        request_body["refresh"] = refresh

    # Start timing for latency metrics (Story 1.9)
    start_time = time.monotonic()

    # Build retry callbacks
    _callbacks = _retry_mod.build_retry_callbacks(
        circuit_breaker=client._circuit_breaker,
        error_class=InsightsServiceError,
        timeout_message="Batch request to autom8_data timed out",
        http_error_template="HTTP error communicating with autom8_data: {e}",
        error_kwargs={"request_id": request_id},
        log=client._log,
        log_event_retry="insights_batch_request_retry",
        log_event_fail="insights_batch_request_failed",
        max_retries=client._config.retry.max_retries,
        extra_log_context={"batch_size": len(pvp_list)},
        start_time=start_time,
    )

    # Build request descriptor
    descriptor = BatchRequestDescriptor(
        path=path,
        request_body=request_body,
        request_id=request_id,
        pvp_list=pvp_list,
        pvp_by_key=pvp_by_key,
        retry_callbacks=_callbacks,
    )

    # S2-S8: Execute via policy
    policy: DefaultEndpointPolicy[
        BatchRequestDescriptor, dict[str, BatchInsightsResult]
    ] = DefaultEndpointPolicy(
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
        pre_execute_error_handler=_make_pre_execute_error_handler(pvp_list),
    )

    return await policy.execute(descriptor)


def build_entity_response(
    rows: list[dict[str, Any]],
    response_metadata: dict[str, Any],
    request_id: str,
    warnings: list[str],
) -> InsightsResponse:
    """Build an InsightsResponse for a single PVP from batch response data.

    Groups all data rows belonging to one PVP into a single response.
    The metadata is shared across the batch but adapted per entity.

    Args:
        rows: List of data row dicts for this PVP.
        response_metadata: Shared metadata from the batch response.
        request_id: Request correlation ID.
        warnings: Shared warnings from the batch response.

    Returns:
        InsightsResponse for the single PVP.
    """
    from autom8_asana.clients.data.models import (
        ColumnInfo,
        InsightsMetadata,
    )

    columns = [ColumnInfo(**col) for col in response_metadata.get("columns", [])]

    metadata = InsightsMetadata(
        factory=response_metadata.get("factory", "unknown"),
        frame_type=response_metadata.get("frame_type"),
        insights_period=response_metadata.get("insights_period"),
        row_count=len(rows),
        column_count=len(columns) if columns else (len(rows[0]) if rows else 0),
        columns=columns,
        cache_hit=response_metadata.get("cache_hit", False),
        duration_ms=response_metadata.get("duration_ms", 0.0),
        sort_history=response_metadata.get("sort_history"),
        is_stale=response_metadata.get("is_stale", False),
        cached_at=response_metadata.get("cached_at"),
    )

    return InsightsResponse(
        data=rows,
        metadata=metadata,
        request_id=request_id,
        warnings=warnings,
    )
