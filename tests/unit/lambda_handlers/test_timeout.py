"""Dispatch tests for timeout Lambda utility module.

Per SCAN-asana-deep-triage Task 4: Cold-start dispatch validation for
timeout.py. Validates module importability, _should_exit_early behavior
across context states, and _self_invoke_continuation error propagation
(failure must never fail current invocation).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestTimeoutModuleInterface:
    """Module is importable and exposes expected interface."""

    def test_module_importable(self) -> None:
        import autom8_asana.lambda_handlers.timeout as mod

        assert mod is not None

    def test_should_exit_early_callable(self) -> None:
        from autom8_asana.lambda_handlers.timeout import _should_exit_early

        assert callable(_should_exit_early)

    def test_self_invoke_continuation_callable(self) -> None:
        from autom8_asana.lambda_handlers.timeout import _self_invoke_continuation

        assert callable(_self_invoke_continuation)

    def test_timeout_buffer_ms_exposed(self) -> None:
        from autom8_asana.lambda_handlers.timeout import TIMEOUT_BUFFER_MS

        # Must be positive and ≥ 60s (reasonable Lambda timeout buffer)
        assert isinstance(TIMEOUT_BUFFER_MS, int)
        assert TIMEOUT_BUFFER_MS >= 60_000

    def test_all_exports_present(self) -> None:
        from autom8_asana.lambda_handlers import timeout

        assert "TIMEOUT_BUFFER_MS" in timeout.__all__
        assert "_should_exit_early" in timeout.__all__
        assert "_self_invoke_continuation" in timeout.__all__


class TestShouldExitEarlyDispatch:
    """_should_exit_early correctly detects imminent Lambda timeout."""

    def test_returns_false_when_context_is_none(self) -> None:
        """No context (local/test environment) means no exit enforcement."""
        from autom8_asana.lambda_handlers.timeout import _should_exit_early

        assert _should_exit_early(None) is False

    def test_returns_false_when_time_is_ample(self) -> None:
        """Ample remaining time returns False."""
        from autom8_asana.lambda_handlers.timeout import (
            TIMEOUT_BUFFER_MS,
            _should_exit_early,
        )

        context = MagicMock()
        context.get_remaining_time_in_millis.return_value = TIMEOUT_BUFFER_MS + 60_000

        assert _should_exit_early(context) is False

    def test_returns_true_when_below_buffer(self) -> None:
        """Remaining time below TIMEOUT_BUFFER_MS returns True."""
        from autom8_asana.lambda_handlers.timeout import (
            TIMEOUT_BUFFER_MS,
            _should_exit_early,
        )

        context = MagicMock()
        context.get_remaining_time_in_millis.return_value = TIMEOUT_BUFFER_MS - 1

        assert _should_exit_early(context) is True

    def test_returns_false_when_exactly_at_buffer(self) -> None:
        """Exactly at TIMEOUT_BUFFER_MS (not below) returns False."""
        from autom8_asana.lambda_handlers.timeout import (
            TIMEOUT_BUFFER_MS,
            _should_exit_early,
        )

        context = MagicMock()
        context.get_remaining_time_in_millis.return_value = TIMEOUT_BUFFER_MS

        assert _should_exit_early(context) is False

    def test_returns_false_when_context_lacks_method(self) -> None:
        """Context without get_remaining_time_in_millis returns False gracefully."""
        from autom8_asana.lambda_handlers.timeout import _should_exit_early

        context = object()  # plain object with no methods
        assert _should_exit_early(context) is False


class TestSelfInvokeContinuationDispatch:
    """_self_invoke_continuation error propagation and no-op cases."""

    def test_noop_when_no_pending_entities(self) -> None:
        """Empty pending_entities list is a no-op (no Lambda invocation)."""
        from autom8_asana.lambda_handlers.timeout import _self_invoke_continuation

        context = MagicMock()
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123:function:warmer"

        with patch("boto3.client") as mock_boto3:
            _self_invoke_continuation(context, [], "inv-001")
            mock_boto3.assert_not_called()

    def test_noop_when_context_has_no_arn(self) -> None:
        """Context with no invoked_function_arn is a no-op."""
        from autom8_asana.lambda_handlers.timeout import _self_invoke_continuation

        context = MagicMock()
        del context.invoked_function_arn  # attribute does not exist

        with patch("boto3.client") as mock_boto3:
            _self_invoke_continuation(context, ["unit"], "inv-001")
            mock_boto3.assert_not_called()

    def test_boto3_error_does_not_propagate(self) -> None:
        """Lambda invocation failure must not raise — isolates current invocation."""
        from autom8_asana.lambda_handlers.timeout import _self_invoke_continuation

        context = MagicMock()
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123:function:warmer"

        mock_lambda_client = MagicMock()
        mock_lambda_client.invoke.side_effect = Exception("Lambda service unavailable")

        with (
            patch("boto3.client", return_value=mock_lambda_client),
            patch("autom8_asana.lambda_handlers.timeout.emit_metric"),
        ):
            # Must not raise — BROAD-CATCH: isolation per module docstring
            _self_invoke_continuation(context, ["unit", "contact"], "inv-001")

    def test_invokes_with_resume_from_checkpoint(self) -> None:
        """Self-invocation payload includes resume_from_checkpoint=True."""
        import json

        from autom8_asana.lambda_handlers.timeout import _self_invoke_continuation

        context = MagicMock()
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123:function:warmer"

        mock_lambda_client = MagicMock()

        with (
            patch("boto3.client", return_value=mock_lambda_client),
            patch("autom8_asana.lambda_handlers.timeout.emit_metric"),
        ):
            _self_invoke_continuation(context, ["contact"], "inv-001")

        mock_lambda_client.invoke.assert_called_once()
        call_kwargs = mock_lambda_client.invoke.call_args[1]
        payload = json.loads(call_kwargs["Payload"])
        assert payload["resume_from_checkpoint"] is True
        assert payload["entity_types"] == ["contact"]
        assert call_kwargs["InvocationType"] == "Event"
