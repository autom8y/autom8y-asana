"""Tests for DataServiceClient.get_export_csv_async.

Per TDD-CONV-AUDIT-001 Section 10.1: Unit tests for the export CSV method
including success, header parsing, circuit breaker, retry, and error scenarios.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from autom8_asana.clients.data.client import (
    DataServiceClient,
    _parse_content_disposition_filename,
)
from autom8_asana.clients.data.config import DataServiceConfig
from autom8_asana.clients.data.models import ExportResult
from autom8_asana.exceptions import ExportError


def _make_client() -> DataServiceClient:
    """Create a DataServiceClient with default config for testing."""
    config = DataServiceConfig(base_url="https://test.example.com")
    return DataServiceClient(config=config)


def _make_response(
    status_code: int = 200,
    content: bytes = b"date,direction,body\n2026-02-01,inbound,Hello\n",
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Create a mock httpx.Response."""
    default_headers = {
        "X-Export-Row-Count": "1",
        "X-Export-Truncated": "false",
        "Content-Disposition": 'attachment; filename="conversations_17705753103_20260210.csv"',
        "Content-Type": "text/csv",
    }
    if headers:
        default_headers.update(headers)

    response = httpx.Response(
        status_code=status_code,
        content=content,
        headers=default_headers,
        request=httpx.Request("GET", "https://test.example.com/api/v1/messages/export"),
    )
    return response


# --- _parse_content_disposition_filename Tests ---


class TestParseContentDispositionFilename:
    """Tests for the filename extraction helper."""

    def test_quoted_filename(self) -> None:
        header = 'attachment; filename="conversations_17705753103_20260210.csv"'
        assert _parse_content_disposition_filename(header) == "conversations_17705753103_20260210.csv"

    def test_unquoted_filename(self) -> None:
        header = "attachment; filename=conversations_17705753103_20260210.csv"
        assert _parse_content_disposition_filename(header) == "conversations_17705753103_20260210.csv"

    def test_empty_header(self) -> None:
        assert _parse_content_disposition_filename("") is None

    def test_no_filename(self) -> None:
        assert _parse_content_disposition_filename("attachment") is None


# --- get_export_csv_async Tests ---


class TestGetExportCsvAsyncSuccess:
    """Tests for successful export requests."""

    @pytest.mark.asyncio
    async def test_success_with_headers(self) -> None:
        """Successful 200 with CSV body and expected headers."""
        client = _make_client()
        mock_response = _make_response(
            status_code=200,
            content=b"date,direction,body\n2026-02-01,inbound,Hello\n",
            headers={
                "X-Export-Row-Count": "42",
                "X-Export-Truncated": "false",
                "Content-Disposition": 'attachment; filename="conversations_17705753103_20260210.csv"',
            },
        )

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        result = await client.get_export_csv_async("+17705753103")

        assert isinstance(result, ExportResult)
        assert result.row_count == 42
        assert result.truncated is False
        assert result.office_phone == "+17705753103"
        assert result.filename == "conversations_17705753103_20260210.csv"
        assert result.csv_content == b"date,direction,body\n2026-02-01,inbound,Hello\n"

    @pytest.mark.asyncio
    async def test_truncated_header_true(self) -> None:
        """Parse X-Export-Truncated=true from headers."""
        client = _make_client()
        mock_response = _make_response(
            headers={
                "X-Export-Row-Count": "10000",
                "X-Export-Truncated": "true",
            },
        )

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        result = await client.get_export_csv_async("+17705753103")

        assert result.truncated is True
        assert result.row_count == 10000

    @pytest.mark.asyncio
    async def test_fallback_filename_when_no_content_disposition(self) -> None:
        """Generate fallback filename when Content-Disposition is missing."""
        client = _make_client()
        mock_response = _make_response(
            headers={
                "X-Export-Row-Count": "5",
                "X-Export-Truncated": "false",
                "Content-Disposition": "",
            },
        )

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        result = await client.get_export_csv_async("+17705753103")

        # Fallback filename should contain phone and today's date
        assert result.filename.startswith("conversations_17705753103_")
        assert result.filename.endswith(".csv")

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success(self) -> None:
        """Circuit breaker records success on 200."""
        client = _make_client()
        mock_response = _make_response(status_code=200)

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        mock_cb = AsyncMock()
        client._circuit_breaker = mock_cb

        await client.get_export_csv_async("+17705753103")

        mock_cb.record_success.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_checked_before_request(self) -> None:
        """Circuit breaker check called before request."""
        client = _make_client()
        mock_response = _make_response(status_code=200)

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        mock_cb = AsyncMock()
        client._circuit_breaker = mock_cb

        await client.get_export_csv_async("+17705753103")

        mock_cb.check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_custom_date_range(self) -> None:
        """Pass start_date and end_date as query params."""
        client = _make_client()
        mock_response = _make_response(status_code=200)

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        await client.get_export_csv_async(
            "+17705753103",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 10),
        )

        call_kwargs = mock_http.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["start_date"] == "2026-01-01"
        assert params["end_date"] == "2026-02-10"


class TestGetExportCsvAsyncErrors:
    """Tests for error scenarios."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_open(self) -> None:
        """Circuit breaker open -> ExportError with reason=circuit_breaker."""
        from autom8y_http import CircuitBreakerOpenError as SdkCBOpen

        client = _make_client()
        mock_cb = AsyncMock()
        mock_cb.check = AsyncMock(
            side_effect=SdkCBOpen(time_remaining=30.0, message="CB open")
        )
        client._circuit_breaker = mock_cb

        with pytest.raises(ExportError) as exc_info:
            await client.get_export_csv_async("+17705753103")

        assert exc_info.value.reason == "circuit_breaker"

    @pytest.mark.asyncio
    async def test_4xx_error(self) -> None:
        """4xx response -> ExportError with reason=client_error."""
        client = _make_client()
        mock_response = _make_response(status_code=400)

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        with pytest.raises(ExportError) as exc_info:
            await client.get_export_csv_async("+17705753103")

        assert exc_info.value.reason == "client_error"

    @pytest.mark.asyncio
    async def test_5xx_error_records_failure(self) -> None:
        """5xx response -> ExportError, circuit breaker records failure."""
        client = _make_client()
        mock_response = _make_response(status_code=500)

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        mock_cb = AsyncMock()
        client._circuit_breaker = mock_cb

        with pytest.raises(ExportError) as exc_info:
            await client.get_export_csv_async("+17705753103")

        assert exc_info.value.reason == "server_error"
        mock_cb.record_failure.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_timeout_with_retry_exhausted(self) -> None:
        """Timeout -> retry, then ExportError with reason=timeout."""
        from dataclasses import replace as dc_replace

        from autom8_asana.clients.data.config import RetryConfig

        client = _make_client()
        # Create a new config with 0 retries (RetryConfig is frozen)
        client._config = dc_replace(
            client._config,
            retry=dc_replace(client._config.retry, max_retries=0),
        )

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))
        client._client = mock_http

        mock_cb = AsyncMock()
        client._circuit_breaker = mock_cb

        with pytest.raises(ExportError) as exc_info:
            await client.get_export_csv_async("+17705753103")

        assert exc_info.value.reason == "timeout"

    @pytest.mark.asyncio
    async def test_http_error(self) -> None:
        """Generic HTTP error -> ExportError with reason=http_error."""
        client = _make_client()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        client._client = mock_http

        with pytest.raises(ExportError) as exc_info:
            await client.get_export_csv_async("+17705753103")

        assert exc_info.value.reason == "http_error"
