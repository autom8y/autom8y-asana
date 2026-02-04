"""Tests for cache warmer Lambda self-continuation on timeout.

When the Lambda hits the timeout buffer, it saves a checkpoint and
self-invokes with remaining entities so processing continues without
waiting for the next scheduled run.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from autom8_asana.lambda_handlers.cache_warmer import _self_invoke_continuation


class TestSelfInvokeContinuation:
    """Tests for _self_invoke_continuation helper."""

    @patch("boto3.client")
    @patch("autom8_asana.lambda_handlers.cache_warmer._emit_metric")
    def test_invokes_with_pending_entities(
        self, mock_metric: MagicMock, mock_boto3_client: MagicMock
    ) -> None:
        """Self-invokes Lambda with remaining entities."""
        mock_lambda = MagicMock()
        mock_boto3_client.return_value = mock_lambda

        context = MagicMock()
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123:function:warmer"

        _self_invoke_continuation(context, ["contact", "offer"], "inv-001")

        mock_boto3_client.assert_called_once_with("lambda")
        mock_lambda.invoke.assert_called_once()

        import json

        call_kwargs = mock_lambda.invoke.call_args[1]
        assert (
            call_kwargs["FunctionName"]
            == "arn:aws:lambda:us-east-1:123:function:warmer"
        )
        assert call_kwargs["InvocationType"] == "Event"

        payload = json.loads(call_kwargs["Payload"])
        assert payload["entity_types"] == ["contact", "offer"]
        assert payload["strict"] is False
        assert payload["resume_from_checkpoint"] is True

    @patch("boto3.client")
    @patch("autom8_asana.lambda_handlers.cache_warmer._emit_metric")
    def test_emits_metric_on_success(
        self, mock_metric: MagicMock, mock_boto3_client: MagicMock
    ) -> None:
        """Emits SelfContinuationInvoked metric."""
        mock_boto3_client.return_value = MagicMock()

        context = MagicMock()
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123:function:warmer"

        _self_invoke_continuation(context, ["contact"], "inv-001")

        mock_metric.assert_called_once_with("SelfContinuationInvoked", 1)

    def test_no_invoke_when_no_pending(self) -> None:
        """Does nothing when pending_entities is empty."""
        context = MagicMock()
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123:function:warmer"

        # Should return immediately without importing boto3
        _self_invoke_continuation(context, [], "inv-001")

    def test_no_arn_logs_warning(self) -> None:
        """Logs warning when context has no invoked_function_arn."""
        context = MagicMock(spec=[])  # No attributes

        # Should not raise
        _self_invoke_continuation(context, ["contact"], "inv-001")

    @patch("boto3.client")
    @patch("autom8_asana.lambda_handlers.cache_warmer._emit_metric")
    def test_handles_invoke_error_gracefully(
        self, mock_metric: MagicMock, mock_boto3_client: MagicMock
    ) -> None:
        """Errors during self-invocation are logged, not raised."""
        mock_lambda = MagicMock()
        mock_lambda.invoke.side_effect = Exception("Throttled")
        mock_boto3_client.return_value = mock_lambda

        context = MagicMock()
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123:function:warmer"

        # Should not raise
        _self_invoke_continuation(context, ["contact"], "inv-001")

        # Metric should NOT be emitted on failure
        mock_metric.assert_not_called()

    @patch("boto3.client")
    @patch("autom8_asana.lambda_handlers.cache_warmer._emit_metric")
    def test_uses_context_arn(
        self, mock_metric: MagicMock, mock_boto3_client: MagicMock
    ) -> None:
        """Uses context.invoked_function_arn as the function name."""
        mock_lambda = MagicMock()
        mock_boto3_client.return_value = mock_lambda

        custom_arn = "arn:aws:lambda:eu-west-1:456:function:custom-warmer"
        context = MagicMock()
        context.invoked_function_arn = custom_arn

        _self_invoke_continuation(context, ["unit"], "inv-002")

        call_kwargs = mock_lambda.invoke.call_args[1]
        assert call_kwargs["FunctionName"] == custom_arn
