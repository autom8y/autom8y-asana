"""Export endpoint implementation for DataServiceClient.

Private module holding the get_export_csv function extracted from
DataServiceClient.get_export_csv_async. The class method becomes a thin
delegation wrapper.

Per WS-DSC: S2-S8 orchestration delegated to DefaultEndpointPolicy.

This module is NOT part of the public API.
"""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING, Any

from autom8_asana.clients.data import _retry as _retry_mod
from autom8_asana.clients.data._policy import (
    DefaultEndpointPolicy,
    ExportRequestDescriptor,
)
from autom8_asana.clients.data.models import ExportResult
from autom8_asana.exceptions import ExportError

if TYPE_CHECKING:
    from autom8y_http import CircuitBreakerOpenError, Response

    from autom8_asana.clients.data.client import DataServiceClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_content_disposition_filename(header: str) -> str | None:
    """Extract filename from Content-Disposition header.

    Args:
        header: Content-Disposition header value.

    Returns:
        Filename string or None if not parseable.
    """
    # Pattern: attachment; filename="conversations_17705753103_20260210.csv"
    match = re.search(r'filename="?([^";\s]+)"?', header)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Pluggable behaviors
# ---------------------------------------------------------------------------


def _cb_error_factory(
    e: CircuitBreakerOpenError, request: ExportRequestDescriptor
) -> Any:
    """Convert CB open error to ExportError (always raises)."""
    raise ExportError(
        f"Circuit breaker open for autom8_data. Retry in {e.time_remaining:.1f}s.",
        office_phone=request.masked_phone,
        reason="circuit_breaker",
    ) from e


def _request_builder(
    http_client: Any, request: ExportRequestDescriptor
) -> Any:
    """Build the make_request lambda for export GET."""
    return lambda: http_client.get(
        request.path,
        params=request.params,
        headers={"Accept": "text/csv"},
    )


async def _error_handler(
    response: Response,
    request: ExportRequestDescriptor,
    elapsed_ms: float,
    *,
    client: DataServiceClient,
) -> Any:
    """Handle error responses for export endpoint (custom, not shared)."""
    if response.status_code >= 500:
        error = ExportError(
            f"autom8_data export error (HTTP {response.status_code})",
            office_phone=request.masked_phone,
            reason="server_error",
        )
        await client._circuit_breaker.record_failure(error)
        raise error
    raise ExportError(
        f"autom8_data export error (HTTP {response.status_code})",
        office_phone=request.masked_phone,
        reason="client_error",
    )


async def _success_handler(
    response: Response,
    request: ExportRequestDescriptor,
    elapsed_ms: float,
    *,
    client: DataServiceClient,
    office_phone: str,
) -> ExportResult:
    """Parse export success response: CSV headers + record CB success."""
    await client._circuit_breaker.record_success()

    # Parse response headers
    row_count = int(response.headers.get("X-Export-Row-Count", "0"))
    truncated = (
        response.headers.get("X-Export-Truncated", "false").lower() == "true"
    )

    # Extract filename from Content-Disposition header
    content_disp = response.headers.get("Content-Disposition", "")
    filename = _parse_content_disposition_filename(content_disp)
    if not filename:
        # Fallback: generate filename
        phone_stripped = office_phone.lstrip("+")
        today_str = date.today().isoformat().replace("-", "")
        filename = f"conversations_{phone_stripped}_{today_str}.csv"

    if client._log:
        client._log.info(
            "export_request_completed",
            extra={
                "office_phone": request.masked_phone,
                "row_count": row_count,
                "truncated": truncated,
                "duration_ms": elapsed_ms,
                "filename": filename,
            },
        )

    return ExportResult(
        csv_content=response.content,
        row_count=row_count,
        truncated=truncated,
        office_phone=office_phone,
        filename=filename,
    )


# ---------------------------------------------------------------------------
# Public endpoint function
# ---------------------------------------------------------------------------


async def get_export_csv(
    client: DataServiceClient,
    office_phone: str,
    *,
    start_date: date | None,
    end_date: date | None,
) -> ExportResult:
    """Fetch conversation CSV export for a business phone number.

    Per TDD-CONV-AUDIT-001 Section 3.5: Calls GET /api/v1/messages/export
    on autom8_data. Returns raw CSV bytes with metadata from response headers.

    Args:
        client: DataServiceClient instance providing config, log, circuit breaker, etc.
        office_phone: E.164 formatted phone number (e.g., "+17705753103").
        start_date: Filter start date. Default: 30 days ago (autom8_data default).
        end_date: Filter end date. Default: today (autom8_data default).

    Returns:
        ExportResult containing CSV bytes, row count, truncation flag,
        phone echo, and filename from Content-Disposition header.

    Raises:
        ExportError: On HTTP errors, circuit breaker open, or timeout.
    """
    # Import here to avoid circular import at module level
    from autom8_asana.clients.data.client import mask_phone_number

    # S1: Pre-flight (PII masking, logging)
    masked_phone = mask_phone_number(office_phone)

    # Build query parameters
    params: dict[str, str] = {"office_phone": office_phone}
    if start_date is not None:
        params["start_date"] = start_date.isoformat()
    if end_date is not None:
        params["end_date"] = end_date.isoformat()

    if client._log:
        client._log.info(
            "export_request_started",
            extra={
                "office_phone": masked_phone,
                "path": "/api/v1/messages/export",
            },
        )

    # Build retry callbacks
    _callbacks = _retry_mod.build_retry_callbacks(
        circuit_breaker=client._circuit_breaker,
        error_class=ExportError,
        timeout_message="Export request timed out",
        http_error_template="HTTP error during export: {e}",
        error_kwargs={"office_phone": masked_phone},
    )

    # Build request descriptor
    descriptor = ExportRequestDescriptor(
        path="/api/v1/messages/export",
        params=params,
        masked_phone=masked_phone,
        retry_callbacks=_callbacks,
    )

    # S2-S8: Execute via policy
    policy: DefaultEndpointPolicy[ExportRequestDescriptor, ExportResult] = (
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
                resp, req, ms, client=client, office_phone=office_phone
            ),
        )
    )

    return await policy.execute(descriptor)
