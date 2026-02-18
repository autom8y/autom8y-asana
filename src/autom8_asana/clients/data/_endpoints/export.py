"""Export endpoint implementation for DataServiceClient.

Private module holding the get_export_csv function extracted from
DataServiceClient.get_export_csv_async. The class method becomes a thin
delegation wrapper.

This module is NOT part of the public API.
"""

from __future__ import annotations

import re
import time
from datetime import date
from typing import TYPE_CHECKING

from autom8y_http import CircuitBreakerOpenError as SdkCircuitBreakerOpenError

from autom8_asana.clients.data import _retry as _retry_mod
from autom8_asana.clients.data.models import ExportResult
from autom8_asana.exceptions import ExportError

if TYPE_CHECKING:
    from autom8_asana.clients.data.client import DataServiceClient


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

    # Check circuit breaker
    try:
        await client._circuit_breaker.check()
    except SdkCircuitBreakerOpenError as e:
        raise ExportError(
            f"Circuit breaker open for autom8_data. "
            f"Retry in {e.time_remaining:.1f}s.",
            office_phone=office_phone,
            reason="circuit_breaker",
        ) from e

    http_client = await client._get_client()
    path = "/api/v1/messages/export"

    # Build query parameters
    params: dict[str, str] = {"office_phone": office_phone}
    if start_date is not None:
        params["start_date"] = start_date.isoformat()
    if end_date is not None:
        params["end_date"] = end_date.isoformat()

    # PII-safe logging
    masked_phone = mask_phone_number(office_phone)

    if client._log:
        client._log.info(
            "export_request_started",
            extra={
                "office_phone": masked_phone,
                "path": path,
            },
        )

    start_time = time.monotonic()

    _callbacks = _retry_mod.build_retry_callbacks(
        circuit_breaker=client._circuit_breaker,
        error_class=ExportError,
        timeout_message="Export request timed out",
        http_error_template="HTTP error during export: {e}",
        error_kwargs={"office_phone": office_phone},
    )

    response, _attempt = await client._execute_with_retry(
        lambda: http_client.get(
            path,
            params=params,
            headers={"Accept": "text/csv"},
        ),
        on_timeout_exhausted=_callbacks.on_timeout_exhausted,
        on_http_error=_callbacks.on_http_error,
    )

    elapsed_ms = (time.monotonic() - start_time) * 1000

    # Handle error responses
    if response.status_code >= 400:
        if response.status_code >= 500:
            error = ExportError(
                f"autom8_data export error (HTTP {response.status_code})",
                office_phone=office_phone,
                reason="server_error",
            )
            await client._circuit_breaker.record_failure(error)
            raise error
        raise ExportError(
            f"autom8_data export error (HTTP {response.status_code})",
            office_phone=office_phone,
            reason="client_error",
        )

    # Record success with circuit breaker
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
                "office_phone": masked_phone,
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
