"""Tests for DataServiceClient batch insights endpoint.

Extracted from test_client.py as part of D-028 test file restructuring.
Maps to: DataServiceClient.get_insights_batch_async, _endpoints/batch.py
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig

from .conftest import (
    _make_disabled_settings_mock,
    make_batch_insights_response,
    make_insights_response,
)

# --- Story 2.4: Batch Insights Tests ---


@pytest.mark.usefixtures("enable_insights_feature")
class TestGetInsightsBatchAsync:
    """Tests for get_insights_batch_async method (Story 2.4)."""

    async def test_batch_success_all_pvps(self, sample_pvps: list) -> None:
        """Happy path - batch with 3 PVPs, all succeed in single request."""
        import respx

        from autom8_asana.clients.data.models import BatchInsightsResponse

        client = DataServiceClient()
        response_body, _status = make_batch_insights_response(sample_pvps, spend=100.0)

        with respx.mock:
            # Single batched response for all PVPs (IMP-20)
            route = respx.post("/api/v1/data-service/insights").respond(json=response_body)

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                )

        # Verify only 1 HTTP request was made (not N)
        assert route.call_count == 1

        assert isinstance(result, BatchInsightsResponse)
        assert result.total_count == 3
        assert result.success_count == 3
        assert result.failure_count == 0
        assert result.request_id is not None

        # All results should be present and successful
        for pvp in sample_pvps:
            batch_result = result.results.get(pvp.canonical_key)
            assert batch_result is not None
            assert batch_result.success is True
            assert batch_result.response is not None
            assert batch_result.error is None

    async def test_partial_failure_one_pvp_fails(self, sample_pvps: list) -> None:
        """Partial failure - 3 PVPs, 1 fails via HTTP 207 partial success."""
        import respx

        client = DataServiceClient()
        # First PVP fails, others succeed -- returned as HTTP 207
        response_body, status_code = make_batch_insights_response(sample_pvps, failed_indices=[0])

        with respx.mock:
            route = respx.post("/api/v1/data-service/insights").respond(
                status_code=207, json=response_body
            )

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                )

        # Verify only 1 HTTP request was made
        assert route.call_count == 1

        # Verify partial success/failure counts
        assert result.total_count == 3
        assert result.success_count == 2
        assert result.failure_count == 1

        # Verify failed results contain error message
        failed_results = result.failed_results()
        assert len(failed_results) == 1
        assert failed_results[0].error is not None
        assert failed_results[0].success is False
        assert failed_results[0].response is None

        # Verify successful results
        successful_results = result.successful_results()
        assert len(successful_results) == 2
        for success_result in successful_results:
            assert success_result.success is True
            assert success_result.response is not None

    async def test_batch_size_exceeds_max_raises_validation_error(self, sample_pvps: list) -> None:
        """Batch size validation - exceeds max_batch_size raises InsightsValidationError."""
        from autom8_asana.errors import InsightsValidationError

        # Create config with very small max_batch_size
        config = DataServiceConfig(
            base_url="https://test.example.com",
            max_batch_size=2,  # Smaller than our 3 PVPs
        )
        client = DataServiceClient(config=config)

        async with client:
            with pytest.raises(InsightsValidationError) as exc:
                await client.get_insights_batch_async(
                    pairs=sample_pvps,  # 3 PVPs, max is 2
                    factory="account",
                )

        assert "Batch size 3 exceeds maximum 2" in str(exc.value)
        assert exc.value.field == "pairs"
        assert exc.value.request_id is not None

    async def test_invalid_factory_raises_validation_error(self, sample_pvps: list) -> None:
        """Invalid factory - raises InsightsValidationError."""
        from autom8_asana.errors import InsightsValidationError

        client = DataServiceClient()

        async with client:
            with pytest.raises(InsightsValidationError) as exc:
                await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="not_a_valid_factory",
                )

        assert "Invalid factory" in str(exc.value)
        assert "not_a_valid_factory" in str(exc.value)
        assert exc.value.field == "factory"

    async def test_feature_flag_disabled_raises_service_error(self, sample_pvps: list) -> None:
        """Feature flag disabled - raises InsightsServiceError with reason='feature_disabled'.

        Per Story 2.7: Feature is now enabled by default. Must explicitly disable.
        """
        from autom8_asana.errors import InsightsServiceError

        client = DataServiceClient()

        # Per D-011: patch get_settings() directly since Settings is cached at import time.
        with patch(
            "autom8_asana.settings.get_settings",
            return_value=_make_disabled_settings_mock(),
        ):
            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_batch_async(
                        pairs=sample_pvps,
                        factory="account",
                    )

        assert exc.value.reason == "feature_disabled"
        assert "Insights integration is disabled" in str(exc.value)

    async def test_single_request_for_batch(self, sample_pvps: list) -> None:
        """IMP-20: Verify batch sends single HTTP request instead of N requests."""
        import json

        import respx

        client = DataServiceClient()
        response_body, _status = make_batch_insights_response(sample_pvps, spend=100.0)

        with respx.mock:
            route = respx.post("/api/v1/data-service/insights").respond(json=response_body)

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                )

        # IMP-20: exactly 1 HTTP request for 3 PVPs (was 3 requests before)
        assert route.call_count == 1

        # Verify the request body contains all 3 PVPs
        request_body = json.loads(route.calls.last.request.content)
        assert len(request_body["phone_vertical_pairs"]) == 3
        assert result.success_count == 3

    async def test_metrics_emission(self, sample_pvps: list) -> None:
        """Metrics emission - verify all 4 batch metrics emitted."""
        import respx

        client = DataServiceClient()
        emitted_metrics: list[tuple[str, float, dict]] = []

        original_emit = client._emit_metric

        def capture_metric(name: str, value: float, tags: dict) -> None:
            emitted_metrics.append((name, value, tags))
            original_emit(name, value, tags)

        with patch.object(client, "_emit_metric", side_effect=capture_metric):
            # HTTP 207 partial response: first PVP fails, others succeed
            response_body, _status = make_batch_insights_response(sample_pvps, failed_indices=[0])

            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=207, json=response_body
                )

                async with client:
                    await client.get_insights_batch_async(
                        pairs=sample_pvps,
                        factory="account",
                    )

        # Extract metric names
        metric_names = [m[0] for m in emitted_metrics]

        # Verify batch-specific metrics are emitted
        assert "insights_batch_total" in metric_names
        assert "insights_batch_size" in metric_names
        assert "insights_batch_success_count" in metric_names
        assert "insights_batch_failure_count" in metric_names

        # Verify metric values
        batch_total = next(m for m in emitted_metrics if m[0] == "insights_batch_total")
        assert batch_total[1] == 1
        assert batch_total[2]["factory"] == "account"

        batch_size = next(m for m in emitted_metrics if m[0] == "insights_batch_size")
        assert batch_size[1] == 3.0

        success_count = next(m for m in emitted_metrics if m[0] == "insights_batch_success_count")
        assert success_count[1] == 2.0

        failure_count = next(m for m in emitted_metrics if m[0] == "insights_batch_failure_count")
        assert failure_count[1] == 1.0

    async def test_empty_batch_graceful_handling(self) -> None:
        """Empty batch - verify graceful handling."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            async with client:
                result = await client.get_insights_batch_async(
                    pairs=[],
                    factory="account",
                )

        assert result.total_count == 0
        assert result.success_count == 0
        assert result.failure_count == 0
        assert result.results == {}
        assert result.request_id is not None

    async def test_batch_result_to_dataframe(self, sample_pvps: list) -> None:
        """Test that batch results can be converted to DataFrame."""
        import respx

        client = DataServiceClient()
        response_body, _status = make_batch_insights_response(sample_pvps, spend=150.0)

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(json=response_body)

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                )

        # Convert to DataFrame
        df = result.to_dataframe()
        assert len(df) == 3  # One row per successful PVP
        assert "spend" in df.columns
        assert "_pvp_key" in df.columns  # Added by to_dataframe

    async def test_batch_get_by_pvp(self, sample_pvps: list) -> None:
        """Test that results can be retrieved by PVP."""
        import respx

        client = DataServiceClient()
        response_body, _status = make_batch_insights_response(sample_pvps)

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(json=response_body)

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                )

        # Get result by PVP
        first_pvp = sample_pvps[0]
        batch_result = result.get(first_pvp)
        assert batch_result is not None
        assert batch_result.pvp == first_pvp
        assert batch_result.success is True

    async def test_factory_case_insensitive(self, sample_pvps: list) -> None:
        """Factory name is case-insensitive."""
        import respx

        client = DataServiceClient()
        response_body, _status = make_batch_insights_response(sample_pvps)

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(json=response_body)

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="ACCOUNT",  # Uppercase
                )

        assert result.success_count == 3

    async def test_batch_with_custom_period_and_refresh(self, sample_pvps: list) -> None:
        """Batch passes period and refresh parameters in single request."""
        import json

        import respx

        client = DataServiceClient()
        response_body, _status = make_batch_insights_response(sample_pvps)
        captured_bodies: list[dict] = []

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured_bodies.append(json.loads(request.content))
            return httpx.Response(200, json=response_body)

        with respx.mock:
            respx.post("/api/v1/data-service/insights").mock(side_effect=capture_request)

            async with client:
                await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                    period="t30",
                    refresh=True,
                )

        # IMP-20: Single request with all PVPs
        assert len(captured_bodies) == 1
        body = captured_bodies[0]
        assert body["period"] == "T30"  # Normalized to uppercase
        assert body["refresh"] is True
        assert len(body["phone_vertical_pairs"]) == 3

    async def test_request_body_contains_all_pvps(self, sample_pvps: list) -> None:
        """IMP-20: Verify request body has all PVPs with correct phone/vertical fields."""
        import json

        import respx

        client = DataServiceClient()
        response_body, _status = make_batch_insights_response(sample_pvps)
        captured_bodies: list[dict] = []

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured_bodies.append(json.loads(request.content))
            return httpx.Response(200, json=response_body)

        with respx.mock:
            respx.post("/api/v1/data-service/insights").mock(side_effect=capture_request)

            async with client:
                await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                )

        assert len(captured_bodies) == 1
        body = captured_bodies[0]
        pvp_list = body["phone_vertical_pairs"]

        # Verify each PVP has phone and vertical fields
        expected_pvps = {(pvp.office_phone, pvp.vertical) for pvp in sample_pvps}
        actual_pvps = {(p["phone"], p["vertical"]) for p in pvp_list}
        assert actual_pvps == expected_pvps

    async def test_total_server_error_marks_all_pvps_failed(self, sample_pvps: list) -> None:
        """IMP-20: HTTP 500 from server marks all PVPs as failed."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                status_code=500, json={"error": "Internal server error"}
            )

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                )

        assert result.total_count == 3
        assert result.success_count == 0
        assert result.failure_count == 3

        for pvp in sample_pvps:
            batch_result = result.results.get(pvp.canonical_key)
            assert batch_result is not None
            assert batch_result.success is False
            assert "Internal server error" in batch_result.error

    async def test_chunking_for_large_batches(self) -> None:
        """IMP-20: Batches exceeding chunk size are split into multiple requests."""
        import json
        from unittest.mock import patch

        import respx

        from autom8_asana.models.contracts import PhoneVerticalPair

        # Create 500 PVPs; patch chunk size to 200 so we get 3 chunks (200+200+100)
        large_pvps = [
            PhoneVerticalPair(office_phone=f"+1770575{i:04d}", vertical="chiropractic")
            for i in range(500)
        ]

        config = DataServiceConfig(base_url="https://test.example.com")
        client = DataServiceClient(config=config)
        request_count = 0

        def handle_request(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            body = json.loads(request.content)
            pvps_in_request = body["phone_vertical_pairs"]

            # Build response with all requested PVPs
            data = [
                {
                    "office_phone": p["phone"],
                    "vertical": p["vertical"],
                    "spend": 100.0,
                    "leads": 10,
                }
                for p in pvps_in_request
            ]
            return httpx.Response(
                200,
                json={
                    "data": data,
                    "metadata": {
                        "factory": "account",
                        "row_count": len(data),
                        "column_count": 4,
                        "columns": [
                            {"name": "office_phone", "dtype": "string"},
                            {"name": "vertical", "dtype": "string"},
                            {"name": "spend", "dtype": "float64"},
                            {"name": "leads", "dtype": "int64"},
                        ],
                        "cache_hit": False,
                        "duration_ms": 50.0,
                    },
                },
            )

        with (
            respx.mock,
            patch.object(
                DataServiceClient,
                "_AUTOM8Y_DATA_MAX_PVP_PER_REQUEST",
                200,
            ),
        ):
            respx.post("/api/v1/data-service/insights").mock(side_effect=handle_request)

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=large_pvps,
                    factory="account",
                )

        # 500 PVPs chunked at 200 → 3 requests (200+200+100)
        assert request_count == 3
        assert result.total_count == 500
        assert result.success_count == 500
        assert result.failure_count == 0

    async def test_circuit_breaker_open_marks_all_failed(self, sample_pvps: list) -> None:
        """IMP-20: Circuit breaker open marks all PVPs as failed without HTTP."""
        import respx

        client = DataServiceClient()

        # Force circuit breaker open by recording enough failures
        for _ in range(20):
            await client._circuit_breaker.record_failure(Exception("simulated failure"))

        with respx.mock:
            route = respx.post("/api/v1/data-service/insights").respond(
                json=make_insights_response()
            )

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                )

        # No HTTP request should have been made
        assert route.call_count == 0

        assert result.total_count == 3
        assert result.success_count == 0
        assert result.failure_count == 3

        for pvp in sample_pvps:
            batch_result = result.results.get(pvp.canonical_key)
            assert batch_result is not None
            assert "Circuit breaker open" in batch_result.error
