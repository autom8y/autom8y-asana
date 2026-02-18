"""Tests for DataServiceClient observability: logging and metrics.

Extracted from test_client.py as part of D-028 test file restructuring.
Maps to: _metrics.py, _emit_metric, structured logging in _execute_insights_request
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig


# --- Story 1.9: Observability (Full Metrics) Tests ---


class TestMetricsHook:
    """Tests for metrics hook integration (Story 1.9)."""

    def test_accepts_metrics_hook_parameter(self) -> None:
        """DataServiceClient accepts metrics_hook parameter."""
        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(metrics_hook=mock_hook)

        assert client._metrics_hook is mock_hook
        assert client.has_metrics is True

    def test_has_metrics_false_when_no_hook(self) -> None:
        """has_metrics returns False when no metrics_hook provided."""
        client = DataServiceClient()

        assert client.has_metrics is False

    def test_emit_metric_calls_hook(self) -> None:
        """_emit_metric calls the configured hook."""
        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(metrics_hook=mock_hook)

        client._emit_metric("test_metric", 42.5, {"factory": "account"})

        assert len(metrics_calls) == 1
        assert metrics_calls[0] == ("test_metric", 42.5, {"factory": "account"})

    def test_emit_metric_no_op_without_hook(self) -> None:
        """_emit_metric does nothing when no hook is configured."""
        client = DataServiceClient()

        # Should not raise
        client._emit_metric("test_metric", 1.0, {"tag": "value"})

    def test_emit_metric_catches_hook_errors(self) -> None:
        """_emit_metric catches and logs errors from hook."""

        def failing_hook(name: str, value: float, tags: dict[str, str]) -> None:
            raise RuntimeError("Hook failed")

        mock_logger = MagicMock()
        client = DataServiceClient(metrics_hook=failing_hook, logger=mock_logger)

        # Should not raise despite hook failure
        client._emit_metric("test_metric", 1.0, {"tag": "value"})

        # Warning should be logged
        mock_logger.warning.assert_called_once()


@pytest.mark.usefixtures("enable_insights_feature")
class TestObservabilityLogging:
    """Tests for structured logging (Story 1.9)."""

    @pytest.mark.asyncio
    async def test_request_started_log_emitted(self) -> None:
        """insights_request_started log is emitted at request start."""
        import respx

        mock_logger = MagicMock()
        client = DataServiceClient(logger=mock_logger)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    json={
                        "data": [{"spend": 100.0}],
                        "metadata": {
                            "factory": "account",
                            "row_count": 1,
                            "column_count": 1,
                            "columns": [{"name": "spend", "dtype": "float64"}],
                            "cache_hit": False,
                            "duration_ms": 50.0,
                        },
                    }
                )

                async with client:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                        period="t30",
                    )

        # Check for request started log
        info_calls = [call for call in mock_logger.info.call_args_list]
        assert len(info_calls) >= 1

        # First info call should be request started
        first_call = info_calls[0]
        assert first_call[0][0] == "insights_request_started"
        extra = first_call[1]["extra"]
        assert extra["factory"] == "account"
        assert extra["period"] == "T30"  # Normalized to uppercase
        assert extra["frame_type"] == "business"  # Now includes frame_type
        assert "request_id" in extra

    @pytest.mark.asyncio
    async def test_request_completed_log_emitted(self) -> None:
        """insights_request_completed log is emitted on success."""
        import respx

        mock_logger = MagicMock()
        client = DataServiceClient(logger=mock_logger)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    json={
                        "data": [{"spend": 100.0}],
                        "metadata": {
                            "factory": "account",
                            "row_count": 1,
                            "column_count": 1,
                            "columns": [{"name": "spend", "dtype": "float64"}],
                            "cache_hit": True,
                            "duration_ms": 50.0,
                        },
                    }
                )

                async with client:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # Check for request completed log
        info_calls = [call for call in mock_logger.info.call_args_list]
        assert len(info_calls) >= 2

        # Second info call should be request completed
        completed_call = info_calls[1]
        assert completed_call[0][0] == "insights_request_completed"
        extra = completed_call[1]["extra"]
        assert extra["row_count"] == 1
        assert extra["cache_hit"] is True
        assert "duration_ms" in extra
        assert "request_id" in extra

    @pytest.mark.asyncio
    async def test_request_failed_log_emitted_on_error(self) -> None:
        """insights_request_failed log is emitted on error."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        mock_logger = MagicMock()
        client = DataServiceClient(logger=mock_logger)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=500,
                    json={"error": "Internal server error"},
                )

                async with client:
                    with pytest.raises(InsightsServiceError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

        # Check for request failed log
        error_calls = [call for call in mock_logger.error.call_args_list]
        assert len(error_calls) >= 1

        # Should have insights_request_failed log
        failed_call = error_calls[0]
        assert failed_call[0][0] == "insights_request_failed"
        extra = failed_call[1]["extra"]
        assert extra["status_code"] == 500
        assert extra["error_type"] == "server_error"
        assert "request_id" in extra
        assert "duration_ms" in extra

    @pytest.mark.asyncio
    async def test_phone_is_masked_in_logs(self) -> None:
        """Phone number is masked in pvp_canonical_key log field."""
        import respx

        mock_logger = MagicMock()
        client = DataServiceClient(logger=mock_logger)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
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
                    }
                )

                async with client:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # Check that phone is masked in request started log
        info_calls = [call for call in mock_logger.info.call_args_list]
        request_started_call = info_calls[0]
        extra = request_started_call[1]["extra"]
        pvp_key = extra["pvp_canonical_key"]

        # Phone should be masked
        assert "+17705753103" not in pvp_key
        assert "+1770***3103" in pvp_key


@pytest.mark.usefixtures("enable_insights_feature")
class TestObservabilityMetrics:
    """Tests for metrics emission (Story 1.9)."""

    @pytest.mark.asyncio
    async def test_success_metrics_emitted(self) -> None:
        """Success metrics are emitted on successful request."""
        import respx

        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(metrics_hook=mock_hook)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    json={
                        "data": [{"spend": 100.0}],
                        "metadata": {
                            "factory": "account",
                            "row_count": 1,
                            "column_count": 1,
                            "columns": [{"name": "spend", "dtype": "float64"}],
                            "cache_hit": False,
                            "duration_ms": 50.0,
                        },
                    }
                )

                async with client:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # Should have emitted insights_request_total and insights_request_latency_ms
        metric_names = [call[0] for call in metrics_calls]
        assert "insights_request_total" in metric_names
        assert "insights_request_latency_ms" in metric_names

        # Check insights_request_total
        total_call = next(c for c in metrics_calls if c[0] == "insights_request_total")
        assert total_call[1] == 1
        assert total_call[2]["factory"] == "account"
        assert total_call[2]["status"] == "success"

        # Check insights_request_latency_ms has positive duration
        latency_call = next(
            c for c in metrics_calls if c[0] == "insights_request_latency_ms"
        )
        assert latency_call[1] > 0
        assert latency_call[2]["factory"] == "account"

    @pytest.mark.asyncio
    async def test_error_metrics_emitted_on_500(self) -> None:
        """Error metrics are emitted on 500 error."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(metrics_hook=mock_hook)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=500,
                    json={"error": "Internal server error"},
                )

                async with client:
                    with pytest.raises(InsightsServiceError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

        # Should have emitted error metrics
        metric_names = [call[0] for call in metrics_calls]
        assert "insights_request_error_total" in metric_names
        assert "insights_request_total" in metric_names
        assert "insights_request_latency_ms" in metric_names

        # Check error_total metric
        error_call = next(
            c for c in metrics_calls if c[0] == "insights_request_error_total"
        )
        assert error_call[1] == 1
        assert error_call[2]["factory"] == "account"
        assert error_call[2]["error_type"] == "server_error"
        assert error_call[2]["status_code"] == "500"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_error_metrics_emitted_on_timeout(self) -> None:
        """Error metrics are emitted on timeout."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(metrics_hook=mock_hook)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").mock(
                    side_effect=httpx.TimeoutException("Timeout")
                )

                async with client:
                    with pytest.raises(InsightsServiceError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

        # Should have emitted error metrics with timeout type
        error_call = next(
            c for c in metrics_calls if c[0] == "insights_request_error_total"
        )
        assert error_call[2]["error_type"] == "timeout"

    @pytest.mark.asyncio
    async def test_latency_metric_has_positive_value(self) -> None:
        """Latency metric has a positive value reflecting actual duration."""
        import respx

        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(metrics_hook=mock_hook)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
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
                    }
                )

                async with client:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        latency_call = next(
            c for c in metrics_calls if c[0] == "insights_request_latency_ms"
        )
        # Should be a positive number (request took some time)
        assert latency_call[1] > 0
        # Should be in milliseconds (unlikely to exceed 10 seconds in test)
        assert latency_call[1] < 10000


@pytest.mark.usefixtures("enable_insights_feature")
class TestObservabilityIntegration:
    """Integration tests for full observability stack (Story 1.9)."""

    @pytest.mark.asyncio
    async def test_full_observability_on_success(self) -> None:
        """Full observability: logging + metrics on successful request."""
        import respx

        mock_logger = MagicMock()
        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(logger=mock_logger, metrics_hook=mock_hook)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    json={
                        "data": [{"spend": 100.0}],
                        "metadata": {
                            "factory": "account",
                            "row_count": 1,
                            "column_count": 1,
                            "columns": [{"name": "spend", "dtype": "float64"}],
                            "cache_hit": False,
                            "duration_ms": 50.0,
                        },
                    }
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                        period="t30",
                    )

        # Response should be valid
        assert response.data == [{"spend": 100.0}]

        # Logging should have happened
        assert mock_logger.info.call_count >= 2  # started + completed
        info_msgs = [call[0][0] for call in mock_logger.info.call_args_list]
        assert "insights_request_started" in info_msgs
        assert "insights_request_completed" in info_msgs

        # Metrics should have been emitted
        assert len(metrics_calls) >= 2
        metric_names = [call[0] for call in metrics_calls]
        assert "insights_request_total" in metric_names
        assert "insights_request_latency_ms" in metric_names

    @pytest.mark.asyncio
    async def test_full_observability_on_error(self) -> None:
        """Full observability: logging + metrics on error."""
        import respx

        from autom8_asana.exceptions import InsightsValidationError

        mock_logger = MagicMock()
        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(logger=mock_logger, metrics_hook=mock_hook)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=400,
                    json={"error": "Invalid request"},
                )

                async with client:
                    with pytest.raises(InsightsValidationError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

        # Error logging should have happened
        assert mock_logger.error.call_count >= 1
        error_msgs = [call[0][0] for call in mock_logger.error.call_args_list]
        assert "insights_request_failed" in error_msgs

        # Error metrics should have been emitted
        metric_names = [call[0] for call in metrics_calls]
        assert "insights_request_error_total" in metric_names
