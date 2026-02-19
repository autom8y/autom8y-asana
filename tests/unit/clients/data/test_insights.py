"""Tests for insights endpoint (get_insights_async / get_insights).

Extracted from test_client.py as part of D-028 test file restructuring.
Maps to: DataServiceClient.get_insights_async, _execute_insights_request,
         _endpoints/insights.py
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig

# --- Story 1.6: get_insights_async Tests ---


@pytest.mark.usefixtures("enable_insights_feature")
class TestGetInsightsAsyncValidation:
    """Tests for get_insights_async input validation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "factory_name",
        [
            "account",
            "ads",
            "adsets",
            "campaigns",
            "spend",
            "leads",
            "appts",
            "assets",
            "targeting",
            "payments",
            "business_offers",
            "ad_questions",
            "ad_tests",
            "base",
        ],
    )
    async def test_all_14_factories_accepted(self, factory_name: str) -> None:
        """All 14 factory names are accepted by validation."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                json={
                    "data": [{"value": 100.0}],
                    "metadata": {
                        "factory": factory_name,
                        "row_count": 1,
                        "column_count": 1,
                        "columns": [{"name": "value", "dtype": "float64"}],
                        "cache_hit": False,
                        "duration_ms": 50.0,
                    },
                }
            )

            # Should not raise - all 14 factories are valid
            async with client:
                response = await client.get_insights_async(
                    factory=factory_name,
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )
                assert response.metadata.factory == factory_name

    @pytest.mark.asyncio
    async def test_rejects_invalid_factory(self) -> None:
        """Invalid factory names are rejected with helpful error listing valid factories."""
        from autom8_asana.exceptions import InsightsValidationError

        client = DataServiceClient()

        async with client:
            with pytest.raises(InsightsValidationError) as exc:
                await client.get_insights_async(
                    factory="not_a_factory",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

        error_msg = str(exc.value)
        assert "Invalid factory" in error_msg
        assert "not_a_factory" in error_msg
        # Error message should list valid factories
        assert "Valid factories:" in error_msg
        assert "account" in error_msg
        assert "ads" in error_msg
        assert "campaigns" in error_msg
        assert exc.value.field == "factory"
        assert exc.value.request_id is not None

    @pytest.mark.asyncio
    async def test_rejects_invalid_phone_format(self) -> None:
        """Invalid E.164 phone format is rejected."""
        from autom8_asana.exceptions import InsightsValidationError

        client = DataServiceClient()

        async with client:
            with pytest.raises(InsightsValidationError) as exc:
                await client.get_insights_async(
                    factory="account",
                    office_phone="555-123-4567",  # Invalid: not E.164
                    vertical="chiropractic",
                )

        assert "Invalid E.164 format" in str(exc.value)
        assert exc.value.field == "office_phone"

    @pytest.mark.asyncio
    async def test_validates_period_format(self) -> None:
        """Invalid period format raises error during request construction."""
        from pydantic import ValidationError

        from autom8_asana.clients.data.models import InsightsRequest

        # This tests the InsightsRequest validation directly
        with pytest.raises(ValidationError):
            InsightsRequest(
                office_phone="+17705753103",
                vertical="chiropractic",
                insights_period="invalid_period",
            )


@pytest.mark.usefixtures("enable_insights_feature")
class TestGetInsightsAsyncHTTPContract:
    """Contract tests for get_insights_async HTTP behavior using respx."""

    @pytest.mark.asyncio
    async def test_posts_to_correct_endpoint(self) -> None:
        """Request is POST to /api/v1/data-service/insights."""
        import respx

        client = DataServiceClient(
            config=DataServiceConfig(base_url="https://data.example.com")
        )

        with respx.mock:
            route = respx.post(
                "https://data.example.com/api/v1/data-service/insights"
            ).respond(
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                }
            )

            async with client:
                await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

            assert route.called

    @pytest.mark.asyncio
    async def test_includes_request_id_header(self) -> None:
        """Request includes X-Request-Id header."""
        import respx

        client = DataServiceClient()
        captured_headers: dict[str, str] = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            nonlocal captured_headers
            captured_headers = dict(request.headers)
            return httpx.Response(
                200,
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                },
            )

        with respx.mock:
            respx.post("/api/v1/data-service/insights").mock(
                side_effect=capture_request
            )

            async with client:
                await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

        assert "x-request-id" in captured_headers
        # Should be a valid UUID
        import uuid

        uuid.UUID(captured_headers["x-request-id"])

    @pytest.mark.asyncio
    async def test_sends_correct_request_body(self) -> None:
        """Request body matches InsightsRequest schema."""
        import respx

        client = DataServiceClient()
        captured_body: dict[str, Any] = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            import json

            captured_body = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                },
            )

        with respx.mock:
            respx.post("/api/v1/data-service/insights").mock(
                side_effect=capture_request
            )

            async with client:
                from datetime import date

                await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    period="t30",
                    start_date=date(2024, 1, 1),
                    metrics=["spend", "leads"],
                    refresh=True,
                )

        # Check new autom8_data request format
        assert captured_body["frame_type"] == "business"
        assert captured_body["phone_vertical_pairs"] == [
            {"phone": "+17705753103", "vertical": "chiropractic"}
        ]
        assert captured_body["period"] == "T30"
        assert captured_body["start_date"] == "2024-01-01"
        assert captured_body["metrics"] == ["spend", "leads"]
        assert captured_body["refresh"] is True

    @pytest.mark.asyncio
    async def test_excludes_none_values_from_body(self) -> None:
        """Request body excludes None values (exclude_none=True)."""
        import respx

        client = DataServiceClient()
        captured_body: dict[str, Any] = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            import json

            captured_body = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                },
            )

        with respx.mock:
            respx.post("/api/v1/data-service/insights").mock(
                side_effect=capture_request
            )

            async with client:
                await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    # metrics=None (default), should not be in body
                )

        # None values should not be present
        assert "metrics" not in captured_body
        assert "dimensions" not in captured_body
        assert "start_date" not in captured_body
        assert "end_date" not in captured_body


@pytest.mark.usefixtures("enable_insights_feature")
class TestGetInsightsAsyncErrorMapping:
    """Tests for HTTP error response mapping."""

    @pytest.mark.asyncio
    async def test_400_maps_to_validation_error(self) -> None:
        """HTTP 400 maps to InsightsValidationError."""
        import respx

        from autom8_asana.exceptions import InsightsValidationError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                status_code=400,
                json={"error": "Invalid phone format"},
            )

            async with client:
                with pytest.raises(InsightsValidationError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert "Invalid phone format" in str(exc.value)
        assert exc.value.request_id is not None

    @pytest.mark.asyncio
    async def test_404_maps_to_not_found_error(self) -> None:
        """HTTP 404 maps to InsightsNotFoundError."""
        import respx

        from autom8_asana.exceptions import InsightsNotFoundError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                status_code=404,
                json={"error": "No insights found for pv1:+17705753103:chiropractic"},
            )

            async with client:
                with pytest.raises(InsightsNotFoundError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert "No insights found" in str(exc.value)
        assert exc.value.request_id is not None

    @pytest.mark.asyncio
    async def test_500_maps_to_service_error(self) -> None:
        """HTTP 500 maps to InsightsServiceError."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                status_code=500,
                json={"error": "Internal server error"},
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert "Internal server error" in str(exc.value)
        assert exc.value.status_code == 500
        assert exc.value.reason == "server_error"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_502_maps_to_service_error(self) -> None:
        """HTTP 502 maps to InsightsServiceError."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                status_code=502,
                json={"error": "Bad gateway"},
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.status_code == 502
        assert exc.value.reason == "server_error"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_503_maps_to_service_error(self) -> None:
        """HTTP 503 maps to InsightsServiceError."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                status_code=503,
                json={"error": "Service unavailable"},
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.status_code == 503

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_504_maps_to_service_error(self) -> None:
        """HTTP 504 maps to InsightsServiceError."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                status_code=504,
                json={"error": "Gateway timeout"},
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.status_code == 504

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_timeout_maps_to_service_error(self) -> None:
        """Request timeout maps to InsightsServiceError."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").mock(
                side_effect=httpx.TimeoutException("Connection timed out")
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert "timed out" in str(exc.value)
        assert exc.value.reason == "timeout"

    @pytest.mark.asyncio
    async def test_http_error_maps_to_service_error(self) -> None:
        """Generic HTTP error maps to InsightsServiceError."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").mock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.reason == "http_error"

    @pytest.mark.asyncio
    async def test_error_includes_detail_field(self) -> None:
        """Error response with 'detail' field is extracted."""
        import respx

        from autom8_asana.exceptions import InsightsValidationError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                status_code=400,
                json={"detail": "Validation failed: missing required field"},
            )

            async with client:
                with pytest.raises(InsightsValidationError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert "Validation failed" in str(exc.value)


@pytest.mark.usefixtures("enable_insights_feature")
class TestGetInsightsAsyncSuccessResponse:
    """Tests for successful response parsing."""

    @pytest.mark.asyncio
    async def test_parses_successful_response(self) -> None:
        """Successful response is parsed to InsightsResponse."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                json={
                    "data": [
                        {"spend": 1500.00, "leads": 45, "cpl": 33.33},
                    ],
                    "metadata": {
                        "factory": "account",
                        "frame_type": "ACCOUNT_INSIGHTS",
                        "insights_period": "t30",
                        "row_count": 1,
                        "column_count": 3,
                        "columns": [
                            {"name": "spend", "dtype": "float64", "nullable": False},
                            {"name": "leads", "dtype": "int64", "nullable": False},
                            {"name": "cpl", "dtype": "float64", "nullable": True},
                        ],
                        "cache_hit": True,
                        "duration_ms": 45.2,
                        "sort_history": ["spend"],
                    },
                    "warnings": ["Some data may be incomplete"],
                }
            )

            async with client:
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    period="t30",
                )

        assert len(response.data) == 1
        assert response.data[0]["spend"] == 1500.00
        assert response.metadata.factory == "account"
        assert response.metadata.frame_type == "ACCOUNT_INSIGHTS"
        assert response.metadata.row_count == 1
        assert response.metadata.cache_hit is True
        assert response.metadata.duration_ms == 45.2
        assert response.warnings == ["Some data may be incomplete"]
        assert response.request_id is not None

    @pytest.mark.asyncio
    async def test_parses_empty_response(self) -> None:
        """Empty data response is handled correctly."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "row_count": 0,
                        "column_count": 3,
                        "columns": [
                            {"name": "spend", "dtype": "float64"},
                            {"name": "leads", "dtype": "int64"},
                            {"name": "cpl", "dtype": "float64"},
                        ],
                        "cache_hit": False,
                        "duration_ms": 25.0,
                    },
                }
            )

            async with client:
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

        assert response.data == []
        assert response.metadata.row_count == 0
        assert len(response.metadata.columns) == 3

    @pytest.mark.asyncio
    async def test_uses_client_request_id_not_server(self) -> None:
        """Response uses client-generated request_id, not server's."""
        import respx

        client = DataServiceClient()
        server_request_id = "server-generated-id"

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                    "request_id": server_request_id,  # Server sends this
                }
            )

            async with client:
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

        # Client generates its own request_id
        assert response.request_id != server_request_id
        # Should be a valid UUID
        import uuid

        uuid.UUID(response.request_id)


@pytest.mark.usefixtures("enable_insights_feature")
class TestGetInsightsAsyncIntegration:
    """Integration test for successful call pattern (mocked)."""

    @pytest.mark.asyncio
    async def test_full_successful_flow(self) -> None:
        """Full successful call flow: validate -> request -> parse -> return."""
        import respx

        from autom8_asana.clients.data.models import InsightsResponse

        config = DataServiceConfig(
            base_url="https://data.test.autom8.io",
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            respx.post(
                "https://data.test.autom8.io/api/v1/data-service/insights"
            ).respond(
                json={
                    "data": [
                        {"spend": 2500.00, "leads": 75, "cpl": 33.33, "roas": 3.5},
                    ],
                    "metadata": {
                        "factory": "account",
                        "frame_type": "ACCOUNT_INSIGHTS",
                        "insights_period": "t30",
                        "row_count": 1,
                        "column_count": 4,
                        "columns": [
                            {"name": "spend", "dtype": "float64", "nullable": False},
                            {"name": "leads", "dtype": "int64", "nullable": False},
                            {"name": "cpl", "dtype": "float64", "nullable": True},
                            {"name": "roas", "dtype": "float64", "nullable": True},
                        ],
                        "cache_hit": False,
                        "duration_ms": 125.5,
                    },
                }
            )

            async with client:
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    period="t30",
                    metrics=["spend", "leads", "cpl", "roas"],
                )

        # Verify response type and structure
        assert isinstance(response, InsightsResponse)
        assert response.metadata.factory == "account"
        assert response.metadata.row_count == 1
        assert response.data[0]["spend"] == 2500.00
        assert response.data[0]["leads"] == 75

        # Verify DataFrame conversion works
        df = response.to_dataframe()
        assert len(df) == 1
        assert "spend" in df.columns
        assert "leads" in df.columns

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "input_case,expected",
        [
            ("ACCOUNT", "account"),
            ("Account", "account"),
            ("aCcOuNt", "account"),
            ("ADS", "ads"),
            ("Campaigns", "campaigns"),
        ],
    )
    async def test_factory_case_insensitive(
        self, input_case: str, expected: str
    ) -> None:
        """Factory name validation is case-insensitive (e.g., ACCOUNT, Account work)."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                json={
                    "data": [],
                    "metadata": {
                        "factory": expected,
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                }
            )

            async with client:
                # Should work with any case
                response = await client.get_insights_async(
                    factory=input_case,
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )
                assert response is not None
                assert response.metadata.factory == expected

    @pytest.mark.asyncio
    async def test_with_all_optional_parameters(self) -> None:
        """Call with all optional parameters."""
        from datetime import date

        import respx

        client = DataServiceClient()
        captured_body: dict[str, Any] = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            import json

            captured_body = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                },
            )

        with respx.mock:
            respx.post("/api/v1/data-service/insights").mock(
                side_effect=capture_request
            )

            async with client:
                await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    period="t30",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    metrics=["spend", "leads"],
                    dimensions=["date"],
                    groups=["ad_account_id"],
                    break_down=["campaign_id"],
                    refresh=True,
                    filters={"ad_account_id": "123456"},
                )

        # Verify all parameters were sent in new autom8_data format
        assert captured_body["frame_type"] == "business"
        assert captured_body["phone_vertical_pairs"] == [
            {"phone": "+17705753103", "vertical": "chiropractic"}
        ]
        assert captured_body["period"] == "T30"
        assert captured_body["start_date"] == "2024-01-01"
        assert captured_body["end_date"] == "2024-12-31"
        assert captured_body["metrics"] == ["spend", "leads"]
        assert captured_body["dimensions"] == ["date"]
        assert captured_body["groups"] == ["ad_account_id"]
        assert captured_body["break_down"] == ["campaign_id"]
        assert captured_body["refresh"] is True
        assert captured_body["filters"] == {"ad_account_id": "123456"}


class TestEntryTypeInsights:
    """Tests for EntryType.INSIGHTS (Story 1.8)."""

    def test_insights_entry_type_exists(self) -> None:
        """EntryType.INSIGHTS is defined."""
        from autom8_asana.cache.models.entry import EntryType

        assert hasattr(EntryType, "INSIGHTS")
        assert EntryType.INSIGHTS.value == "insights"

    def test_insights_entry_type_is_string_enum(self) -> None:
        """EntryType.INSIGHTS is a string enum value."""
        from autom8_asana.cache.models.entry import EntryType

        assert isinstance(EntryType.INSIGHTS.value, str)
        assert EntryType.INSIGHTS == "insights"
