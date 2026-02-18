"""Batch insights endpoint implementation for DataServiceClient.

Private module holding the execute_batch_request and build_entity_response
functions extracted from DataServiceClient. The class methods become thin
delegation wrappers.

This module is NOT part of the public API.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from autom8y_http import CircuitBreakerOpenError as SdkCircuitBreakerOpenError

from autom8_asana.clients.data import _normalize as _normalize_mod
from autom8_asana.clients.data import _retry as _retry_mod
from autom8_asana.clients.data._pii import mask_pii_in_string as _mask_pii_in_string
from autom8_asana.clients.data.models import (
    BatchInsightsResult,
    InsightsResponse,
)
from autom8_asana.exceptions import InsightsError, InsightsServiceError

if TYPE_CHECKING:
    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.models.contracts import PhoneVerticalPair


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
    # Build PVP lookup: canonical_key -> PhoneVerticalPair
    pvp_by_key: dict[str, PhoneVerticalPair] = {
        pvp.canonical_key: pvp for pvp in pvp_list
    }
    results: dict[str, BatchInsightsResult] = {}

    # --- Circuit Breaker Check (Story 2.3) ---
    try:
        await client._circuit_breaker.check()
    except SdkCircuitBreakerOpenError as e:
        # Mark all PVPs as failed due to circuit breaker
        error_msg = (
            f"Circuit breaker open. Service appears degraded. "
            f"Retry in {e.time_remaining:.1f}s."
        )
        for pvp in pvp_list:
            results[pvp.canonical_key] = BatchInsightsResult(
                pvp=pvp,
                error=error_msg,
            )
        return results

    http_client = await client._get_client()
    path = "/api/v1/data-service/insights"

    # Map factory to frame_type
    frame_type = client.FACTORY_TO_FRAME_TYPE[factory]

    # Normalize period to autom8_data format
    normalized_period = _normalize_mod.normalize_period(period)

    # Build request body with all PVPs (IMP-20: multi-PVP batch)
    request_body: dict[str, Any] = {
        "frame_type": frame_type,
        "phone_vertical_pairs": [
            {"phone": pvp.office_phone, "vertical": pvp.vertical}
            for pvp in pvp_list
        ],
        "period": normalized_period,
    }

    if refresh:
        request_body["refresh"] = refresh

    # Start timing for latency metrics (Story 1.9)
    start_time = time.monotonic()

    # --- Retry Callbacks ---
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

    # --- Execute HTTP request with retry ---
    # Note: W3C traceparent is auto-injected by HTTPXClientInstrumentor.
    # X-Request-Id is kept for backwards compatibility with autom8y-data's
    # RequestIDMiddleware, which uses it for non-OTEL correlation.
    try:
        response, _attempt = await client._execute_with_retry(
            lambda: http_client.post(
                path,
                json=request_body,
                headers={"X-Request-Id": request_id},
            ),
            on_retry=_callbacks.on_retry,
            on_timeout_exhausted=_callbacks.on_timeout_exhausted,
            on_http_error=_callbacks.on_http_error,
        )
    except (InsightsServiceError, InsightsError) as e:
        # Total failure for entire chunk -- mark all PVPs as errored
        # Sanitize error string to redact any PII echoed by upstream
        sanitized_error = _mask_pii_in_string(str(e))
        for pvp in pvp_list:
            results[pvp.canonical_key] = BatchInsightsResult(
                pvp=pvp,
                error=sanitized_error,
            )
        return results

    elapsed_ms = (time.monotonic() - start_time) * 1000

    # --- Handle total failure (4xx/5xx with no partial data) ---
    if response.status_code >= 400 and response.status_code != 207:
        error_msg = f"autom8_data API error (HTTP {response.status_code})"
        try:
            body = response.json()
            if "error" in body:
                error_msg = body["error"]
            elif "detail" in body:
                error_msg = body["detail"]
        except (ValueError, KeyError):
            pass

        # Sanitize error message to redact any PII echoed by upstream (XR-003)
        error_msg = _mask_pii_in_string(error_msg)

        if response.status_code >= 500:
            error = InsightsServiceError(
                error_msg,
                request_id=request_id,
                status_code=response.status_code,
                reason="server_error",
            )
            await client._circuit_breaker.record_failure(error)

        for pvp in pvp_list:
            results[pvp.canonical_key] = BatchInsightsResult(
                pvp=pvp,
                error=error_msg,
            )
        return results

    # --- Parse successful / partial response ---
    await client._circuit_breaker.record_success()

    try:
        body = response.json()
    except (ValueError, Exception) as e:
        error_msg = _mask_pii_in_string(f"Failed to parse response JSON: {e}")
        for pvp in pvp_list:
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
    # Each row in data has office_phone and vertical fields
    rows_by_key: dict[str, list[dict[str, Any]]] = {}
    for row in data_list:
        row_phone = row.get("office_phone", "")
        row_vertical = row.get("vertical", "")
        canonical_key = f"pv1:{row_phone}:{row_vertical.lower()}"

        if canonical_key not in pvp_by_key:
            # Response contained a PVP we didn't request -- skip
            continue

        rows_by_key.setdefault(canonical_key, []).append(row)

    # Build per-PVP InsightsResponse from grouped rows
    for canonical_key, rows in rows_by_key.items():
        pvp = pvp_by_key[canonical_key]
        entity_response = build_entity_response(
            rows, response_metadata, request_id, warnings
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

        error_pvp = pvp_by_key.get(canonical_key)
        if error_pvp is not None and canonical_key not in results:
            results[canonical_key] = BatchInsightsResult(
                pvp=error_pvp,
                error=error_msg,
            )

    # Mark any remaining PVPs (not in data or errors) as failed
    for pvp in pvp_list:
        if pvp.canonical_key not in results:
            results[pvp.canonical_key] = BatchInsightsResult(
                pvp=pvp,
                error="No data returned for this PVP",
            )

    if client._log:
        client._log.info(
            "insights_batch_request_completed",
            extra={
                "request_id": request_id,
                "batch_size": len(pvp_list),
                "data_count": len(data_list),
                "error_count": len(errors_list),
                "duration_ms": elapsed_ms,
            },
        )

    return results


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
