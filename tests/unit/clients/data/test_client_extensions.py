"""Tests for DataServiceClient W04 extensions.

Per TDD-EXPORT-001 Section 9.2: Unit tests for get_appointments_async,
get_leads_async, _normalize_period extensions, and InsightsRequest
period validation for quarter/month/week.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from autom8_asana.clients.data.client import DataServiceClient, mask_phone_number
from autom8_asana.clients.data.config import DataServiceConfig
from autom8_asana.clients.data.models import InsightsRequest, InsightsResponse
from autom8_asana.exceptions import InsightsServiceError


def _make_client() -> DataServiceClient:
    """Create a DataServiceClient with default config for testing."""
    config = DataServiceConfig(base_url="https://test.example.com")
    return DataServiceClient(config=config)


def _make_insights_response(
    status_code: int = 200,
    row_count: int = 5,
) -> httpx.Response:
    """Create a mock httpx.Response that looks like an InsightsResponse."""
    body = {
        "data": [{"id": i, "name": f"row_{i}"} for i in range(row_count)],
        "metadata": {
            "factory": "appointments",
            "row_count": row_count,
            "column_count": 2,
            "columns": [
                {"name": "id", "dtype": "int64"},
                {"name": "name", "dtype": "string"},
            ],
            "cache_hit": False,
            "duration_ms": 25.0,
        },
        "request_id": "test-request-id",
        "warnings": [],
    }
    return httpx.Response(
        status_code=status_code,
        json=body,
        request=httpx.Request("GET", "https://test.example.com/api/v1/appointments"),
    )


# ---------------------------------------------------------------------------
# TestGetAppointmentsAsync
# ---------------------------------------------------------------------------


class TestGetAppointmentsAsync:
    """Tests for get_appointments_async (AC-W04.1, AC-W04.2, AC-W04.10)."""

    @pytest.mark.asyncio
    async def test_success_returns_insights_response(self) -> None:
        """Successful 200 returns InsightsResponse with appointment rows."""
        client = _make_client()
        mock_response = _make_insights_response(status_code=200, row_count=3)

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        result = await client.get_appointments_async("+17705753103")

        assert isinstance(result, InsightsResponse)
        assert result.metadata.row_count == 3
        assert len(result.data) == 3

    @pytest.mark.asyncio
    async def test_passes_correct_params(self) -> None:
        """GET /api/v1/appointments called with correct query params."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        await client.get_appointments_async("+17705753103", days=60, limit=50)

        call_kwargs = mock_http.get.call_args
        # Positional arg is the path
        assert call_kwargs[0][0] == "/api/v1/appointments"
        params = call_kwargs[1]["params"]
        assert params["office_phone"] == "+17705753103"
        assert params["days"] == "60"
        assert params["limit"] == "50"

    @pytest.mark.asyncio
    async def test_default_params(self) -> None:
        """Default days=90 and limit=100 are used."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        await client.get_appointments_async("+17705753103")

        call_kwargs = mock_http.get.call_args
        params = call_kwargs[1]["params"]
        assert params["days"] == "90"
        assert params["limit"] == "100"

    @pytest.mark.asyncio
    async def test_circuit_breaker_checked_before_request(self) -> None:
        """Circuit breaker check() is called before the HTTP request."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        mock_cb = AsyncMock()
        client._circuit_breaker = mock_cb

        await client.get_appointments_async("+17705753103")

        mock_cb.check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success(self) -> None:
        """Circuit breaker records success on 200 response."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        mock_cb = AsyncMock()
        client._circuit_breaker = mock_cb

        await client.get_appointments_async("+17705753103")

        mock_cb.record_success.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_raises(self) -> None:
        """Circuit breaker open raises InsightsServiceError."""
        from autom8y_http import CircuitBreakerOpenError as SdkCBOpen

        client = _make_client()
        mock_cb = AsyncMock()
        mock_cb.check = AsyncMock(
            side_effect=SdkCBOpen(time_remaining=30.0, message="CB open")
        )
        client._circuit_breaker = mock_cb

        with pytest.raises(InsightsServiceError) as exc_info:
            await client.get_appointments_async("+17705753103")

        assert exc_info.value.reason == "circuit_breaker"

    @pytest.mark.asyncio
    async def test_pii_masking_in_logs(self) -> None:
        """Phone number is masked in log output (AC-W04.10)."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        with patch("autom8_asana.clients.data.client.logger") as mock_logger:
            await client.get_appointments_async("+17705753103")

            # Find the started log call
            started_calls = [
                c
                for c in mock_logger.info.call_args_list
                if c[0][0] == "appointments_request_started"
            ]
            assert len(started_calls) >= 1
            call_kwargs = started_calls[0][1]
            # The office_phone kwarg should be the masked version
            assert call_kwargs["office_phone"] == "+1770***3103"
            assert "+17705753103" not in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_sends_request_id_header(self) -> None:
        """X-Request-Id header is sent with the GET request."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        await client.get_appointments_async("+17705753103")

        call_kwargs = mock_http.get.call_args
        headers = call_kwargs[1]["headers"]
        assert "X-Request-Id" in headers


# ---------------------------------------------------------------------------
# TestGetLeadsAsync
# ---------------------------------------------------------------------------


class TestGetLeadsAsync:
    """Tests for get_leads_async (AC-W04.3, AC-W04.4, AC-W04.10)."""

    @pytest.mark.asyncio
    async def test_success_returns_insights_response(self) -> None:
        """Successful 200 returns InsightsResponse with lead rows."""
        client = _make_client()
        mock_response = _make_insights_response(status_code=200, row_count=7)

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        result = await client.get_leads_async("+17705753103")

        assert isinstance(result, InsightsResponse)
        assert result.metadata.row_count == 7
        assert len(result.data) == 7

    @pytest.mark.asyncio
    async def test_exclude_appointments_true_by_default(self) -> None:
        """exclude_appointments=True adds param to request by default."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        await client.get_leads_async("+17705753103")

        call_kwargs = mock_http.get.call_args
        params = call_kwargs[1]["params"]
        assert params["exclude_appointments"] == "true"

    @pytest.mark.asyncio
    async def test_exclude_appointments_false(self) -> None:
        """exclude_appointments=False omits the param from request."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        await client.get_leads_async("+17705753103", exclude_appointments=False)

        call_kwargs = mock_http.get.call_args
        params = call_kwargs[1]["params"]
        assert "exclude_appointments" not in params

    @pytest.mark.asyncio
    async def test_passes_correct_path_and_params(self) -> None:
        """GET /api/v1/leads called with correct query params."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        await client.get_leads_async("+17705753103", days=14, limit=200)

        call_kwargs = mock_http.get.call_args
        assert call_kwargs[0][0] == "/api/v1/leads"
        params = call_kwargs[1]["params"]
        assert params["office_phone"] == "+17705753103"
        assert params["days"] == "14"
        assert params["limit"] == "200"

    @pytest.mark.asyncio
    async def test_default_params(self) -> None:
        """Default days=30 and limit=100 are used."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        await client.get_leads_async("+17705753103")

        call_kwargs = mock_http.get.call_args
        params = call_kwargs[1]["params"]
        assert params["days"] == "30"
        assert params["limit"] == "100"

    @pytest.mark.asyncio
    async def test_circuit_breaker_checked_before_request(self) -> None:
        """Circuit breaker check() is called before the HTTP request."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        mock_cb = AsyncMock()
        client._circuit_breaker = mock_cb

        await client.get_leads_async("+17705753103")

        mock_cb.check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success(self) -> None:
        """Circuit breaker records success on 200 response."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        mock_cb = AsyncMock()
        client._circuit_breaker = mock_cb

        await client.get_leads_async("+17705753103")

        mock_cb.record_success.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_raises(self) -> None:
        """Circuit breaker open raises InsightsServiceError."""
        from autom8y_http import CircuitBreakerOpenError as SdkCBOpen

        client = _make_client()
        mock_cb = AsyncMock()
        mock_cb.check = AsyncMock(
            side_effect=SdkCBOpen(time_remaining=15.0, message="CB open")
        )
        client._circuit_breaker = mock_cb

        with pytest.raises(InsightsServiceError) as exc_info:
            await client.get_leads_async("+17705753103")

        assert exc_info.value.reason == "circuit_breaker"

    @pytest.mark.asyncio
    async def test_pii_masking_in_logs(self) -> None:
        """Phone number is masked in log output (AC-W04.10)."""
        client = _make_client()
        mock_response = _make_insights_response()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        with patch("autom8_asana.clients.data.client.logger") as mock_logger:
            await client.get_leads_async("+17705753103")

            started_calls = [
                c
                for c in mock_logger.info.call_args_list
                if c[0][0] == "leads_request_started"
            ]
            assert len(started_calls) >= 1
            call_kwargs = started_calls[0][1]
            assert call_kwargs["office_phone"] == "+1770***3103"
            assert "+17705753103" not in str(call_kwargs)


# ---------------------------------------------------------------------------
# TestNormalizePeriod
# ---------------------------------------------------------------------------


class TestNormalizePeriod:
    """Tests for _normalize_period extensions (AC-W04.5 through AC-W04.8)."""

    def test_quarter_normalizes_to_QUARTER(self) -> None:
        """'quarter' -> 'QUARTER' (AC-W04.5)."""
        client = _make_client()
        assert client._normalize_period("quarter") == "QUARTER"

    def test_quarter_case_insensitive(self) -> None:
        """'QUARTER' -> 'QUARTER' (case-insensitive)."""
        client = _make_client()
        assert client._normalize_period("QUARTER") == "QUARTER"
        assert client._normalize_period("Quarter") == "QUARTER"

    def test_month_normalizes_to_MONTH(self) -> None:
        """'month' -> 'MONTH' (AC-W04.6)."""
        client = _make_client()
        assert client._normalize_period("month") == "MONTH"

    def test_month_case_insensitive(self) -> None:
        """'MONTH' -> 'MONTH' (case-insensitive)."""
        client = _make_client()
        assert client._normalize_period("MONTH") == "MONTH"
        assert client._normalize_period("Month") == "MONTH"

    def test_week_normalizes_to_WEEK(self) -> None:
        """'week' -> 'WEEK' (AC-W04.7)."""
        client = _make_client()
        assert client._normalize_period("week") == "WEEK"

    def test_week_case_insensitive(self) -> None:
        """'WEEK' -> 'WEEK' (case-insensitive)."""
        client = _make_client()
        assert client._normalize_period("WEEK") == "WEEK"
        assert client._normalize_period("Week") == "WEEK"

    def test_existing_lifetime_unchanged(self) -> None:
        """Existing 'lifetime' -> 'LIFETIME' still works (AC-W04.8)."""
        client = _make_client()
        assert client._normalize_period("lifetime") == "LIFETIME"
        assert client._normalize_period("LIFETIME") == "LIFETIME"

    def test_existing_t7_unchanged(self) -> None:
        """Existing 't7' -> 'T7' still works (AC-W04.8)."""
        client = _make_client()
        assert client._normalize_period("t7") == "T7"
        assert client._normalize_period("l7") == "T7"

    def test_existing_t14_unchanged(self) -> None:
        """Existing 't14' -> 'T14' still works (AC-W04.8)."""
        client = _make_client()
        assert client._normalize_period("t14") == "T14"
        assert client._normalize_period("l14") == "T14"

    def test_existing_t30_unchanged(self) -> None:
        """Existing 't30' -> 'T30' still works (AC-W04.8)."""
        client = _make_client()
        assert client._normalize_period("t30") == "T30"
        assert client._normalize_period("l30") == "T30"

    def test_none_returns_lifetime(self) -> None:
        """None -> 'LIFETIME' (default behavior preserved)."""
        client = _make_client()
        assert client._normalize_period(None) == "LIFETIME"

    def test_unknown_defaults_to_t30(self) -> None:
        """Unknown period -> 'T30' (backward compatibility preserved)."""
        client = _make_client()
        assert client._normalize_period("custom") == "T30"


# ---------------------------------------------------------------------------
# TestInsightsRequestValidation
# ---------------------------------------------------------------------------


class TestInsightsRequestValidation:
    """Tests for InsightsRequest.validate_period with new periods (AC-W04.9)."""

    def test_quarter_passes_validation(self) -> None:
        """InsightsRequest(insights_period='quarter') passes validation."""
        request = InsightsRequest(
            office_phone="+17705551234",
            vertical="dental",
            insights_period="quarter",
        )
        assert request.insights_period == "quarter"

    def test_month_passes_validation(self) -> None:
        """InsightsRequest(insights_period='month') passes validation."""
        request = InsightsRequest(
            office_phone="+17705551234",
            vertical="dental",
            insights_period="month",
        )
        assert request.insights_period == "month"

    def test_week_passes_validation(self) -> None:
        """InsightsRequest(insights_period='week') passes validation."""
        request = InsightsRequest(
            office_phone="+17705551234",
            vertical="dental",
            insights_period="week",
        )
        assert request.insights_period == "week"

    def test_existing_periods_still_valid(self) -> None:
        """Existing period values continue to work."""
        for period in ("lifetime", "t7", "t14", "t30"):
            request = InsightsRequest(
                office_phone="+17705551234",
                vertical="dental",
                insights_period=period,
            )
            assert request.insights_period == period
