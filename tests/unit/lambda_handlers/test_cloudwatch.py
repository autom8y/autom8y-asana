"""Dispatch tests for cloudwatch Lambda utility module.

Per SCAN-asana-deep-triage Task 4: Cold-start dispatch validation for
the cloudwatch.py module. Validates module importability, emit_metric
signature, graceful degradation on CloudWatch unavailability, and that
metric emission failures never propagate to callers.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestCloudwatchModuleInterface:
    """Module is importable and exposes expected interface."""

    def test_module_importable(self) -> None:
        import autom8_asana.lambda_handlers.cloudwatch as mod

        assert mod is not None

    def test_emit_metric_callable(self) -> None:
        from autom8_asana.lambda_handlers.cloudwatch import emit_metric

        assert callable(emit_metric)

    def test_get_cloudwatch_client_callable(self) -> None:
        from autom8_asana.lambda_handlers.cloudwatch import _get_cloudwatch_client

        assert callable(_get_cloudwatch_client)


class TestEmitMetricDispatch:
    """emit_metric dispatches to CloudWatch with correct arguments."""

    def test_emit_metric_calls_put_metric_data(self) -> None:
        """emit_metric calls CloudWatch put_metric_data with metric name and value."""
        mock_client = MagicMock()
        mock_settings = MagicMock()
        mock_settings.observability.cloudwatch_namespace = "TestNamespace"
        mock_settings.observability.environment = "test"

        with (
            patch(
                "autom8_asana.lambda_handlers.cloudwatch._get_cloudwatch_client",
                return_value=mock_client,
            ),
            patch(
                "autom8_asana.settings.get_settings",
                return_value=mock_settings,
            ),
        ):
            from autom8_asana.lambda_handlers.cloudwatch import emit_metric

            emit_metric("TestMetric", 1.0)

        mock_client.put_metric_data.assert_called_once()
        call_kwargs = mock_client.put_metric_data.call_args[1]
        assert call_kwargs["Namespace"] == "TestNamespace"
        metric_data = call_kwargs["MetricData"][0]
        assert metric_data["MetricName"] == "TestMetric"
        assert metric_data["Value"] == 1.0
        assert metric_data["Unit"] == "Count"

    def test_emit_metric_with_custom_unit(self) -> None:
        """emit_metric passes custom unit to CloudWatch."""
        mock_client = MagicMock()
        mock_settings = MagicMock()
        mock_settings.observability.cloudwatch_namespace = "TestNamespace"
        mock_settings.observability.environment = "test"

        with (
            patch(
                "autom8_asana.lambda_handlers.cloudwatch._get_cloudwatch_client",
                return_value=mock_client,
            ),
            patch(
                "autom8_asana.settings.get_settings",
                return_value=mock_settings,
            ),
        ):
            from autom8_asana.lambda_handlers.cloudwatch import emit_metric

            emit_metric("Latency", 42.5, unit="Milliseconds")

        metric_data = mock_client.put_metric_data.call_args[1]["MetricData"][0]
        assert metric_data["Unit"] == "Milliseconds"
        assert metric_data["Value"] == 42.5

    def test_emit_metric_with_namespace_override(self) -> None:
        """emit_metric uses the override namespace when provided."""
        mock_client = MagicMock()
        mock_settings = MagicMock()
        mock_settings.observability.cloudwatch_namespace = "DefaultNamespace"
        mock_settings.observability.environment = "test"

        with (
            patch(
                "autom8_asana.lambda_handlers.cloudwatch._get_cloudwatch_client",
                return_value=mock_client,
            ),
            patch(
                "autom8_asana.settings.get_settings",
                return_value=mock_settings,
            ),
        ):
            from autom8_asana.lambda_handlers.cloudwatch import emit_metric

            emit_metric("Metric", 1.0, namespace="OverrideNamespace")

        call_kwargs = mock_client.put_metric_data.call_args[1]
        assert call_kwargs["Namespace"] == "OverrideNamespace"

    def test_emit_metric_with_dimensions(self) -> None:
        """emit_metric includes extra dimensions in the CloudWatch request."""
        mock_client = MagicMock()
        mock_settings = MagicMock()
        mock_settings.observability.cloudwatch_namespace = "NS"
        mock_settings.observability.environment = "test"

        with (
            patch(
                "autom8_asana.lambda_handlers.cloudwatch._get_cloudwatch_client",
                return_value=mock_client,
            ),
            patch(
                "autom8_asana.settings.get_settings",
                return_value=mock_settings,
            ),
        ):
            from autom8_asana.lambda_handlers.cloudwatch import emit_metric

            emit_metric("Metric", 1.0, dimensions={"entity_type": "unit"})

        metric_data = mock_client.put_metric_data.call_args[1]["MetricData"][0]
        dim_names = {d["Name"] for d in metric_data["Dimensions"]}
        assert "entity_type" in dim_names
        assert "environment" in dim_names

    def test_emit_metric_swallows_cloudwatch_error(self) -> None:
        """emit_metric does not propagate CloudWatch API errors to callers."""
        mock_client = MagicMock()
        mock_client.put_metric_data.side_effect = Exception("CloudWatch unavailable")
        mock_settings = MagicMock()
        mock_settings.observability.cloudwatch_namespace = "NS"
        mock_settings.observability.environment = "test"

        with (
            patch(
                "autom8_asana.lambda_handlers.cloudwatch._get_cloudwatch_client",
                return_value=mock_client,
            ),
            patch(
                "autom8_asana.settings.get_settings",
                return_value=mock_settings,
            ),
        ):
            from autom8_asana.lambda_handlers.cloudwatch import emit_metric

            # Must not raise
            emit_metric("Metric", 1.0)

        mock_client.put_metric_data.assert_called_once()


class TestCloudwatchClientLazyInit:
    """CloudWatch client is lazily initialized and cached."""

    def test_client_initialized_on_first_call(self) -> None:
        """_get_cloudwatch_client initializes boto3 client on first call."""
        import autom8_asana.lambda_handlers.cloudwatch as mod

        original = mod._cloudwatch_client
        try:
            mod._cloudwatch_client = None
            with patch("boto3.client", return_value=MagicMock()) as mock_boto3:
                mod._get_cloudwatch_client()
                mock_boto3.assert_called_once_with("cloudwatch")
        finally:
            mod._cloudwatch_client = original
