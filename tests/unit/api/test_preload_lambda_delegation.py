"""Tests for preload Lambda delegation when S3 manifests are missing.

When S3 data has been purged (e.g., after force_full_rebuild), the container
startup preload must delegate to Lambda instead of building in-process to
avoid OOM (exit 137).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from autom8_asana.api.preload.progressive import (
    _invoke_cache_warmer_lambda_from_preload,
)


class TestInvokeCacheWarmerLambdaFromPreload:
    """Tests for _invoke_cache_warmer_lambda_from_preload helper."""

    @patch("boto3.client")
    def test_invokes_lambda_with_correct_payload(self, mock_boto3_client: MagicMock) -> None:
        """Lambda is invoked asynchronously with entity types."""
        mock_lambda = MagicMock()
        mock_boto3_client.return_value = mock_lambda

        _invoke_cache_warmer_lambda_from_preload(
            "arn:aws:lambda:us-east-1:123:function:warmer",
            ["unit", "contact"],
        )

        mock_boto3_client.assert_called_once_with("lambda")
        mock_lambda.invoke.assert_called_once()
        call_kwargs = mock_lambda.invoke.call_args[1]
        assert call_kwargs["FunctionName"] == "arn:aws:lambda:us-east-1:123:function:warmer"
        assert call_kwargs["InvocationType"] == "Event"

        import json

        payload = json.loads(call_kwargs["Payload"])
        assert payload["entity_types"] == ["unit", "contact"]
        assert payload["strict"] is False
        assert payload["resume_from_checkpoint"] is False

    @patch("boto3.client")
    def test_handles_invoke_error_gracefully(self, mock_boto3_client: MagicMock) -> None:
        """Errors during Lambda invocation are logged, not raised."""
        mock_lambda = MagicMock()
        mock_lambda.invoke.side_effect = Exception("AccessDenied")
        mock_boto3_client.return_value = mock_lambda

        # Should not raise
        _invoke_cache_warmer_lambda_from_preload(
            "arn:aws:lambda:us-east-1:123:function:warmer",
            ["unit"],
        )


class TestPreloadManifestCheck:
    """Tests for manifest check in process_project.

    The three manifest-branch simulation tests that were previously here
    (test_skips_build_when_no_manifest_and_lambda_available,
    test_proceeds_normally_when_manifest_exists,
    test_skips_without_lambda_arn_when_no_manifest)
    replicated production logic inline rather than calling the real function.

    They have been replaced by integration tests that call the actual
    _preload_dataframe_cache_progressive function:
        tests/integration/api/test_preload_manifest_check.py
            - test_manifest_exists_proceeds_with_progressive_build
            - test_no_manifest_with_lambda_arn_delegates_to_lambda
            - test_no_manifest_no_lambda_arn_skips_preload

    See: RS-013/LS-008 (slop-chop P1)
    """

    @patch("boto3.client")
    def test_lambda_invoked_with_all_delegated_entities(self, mock_boto3_client: MagicMock) -> None:
        """Lambda is invoked once with all entity types that had missing manifests."""
        mock_lambda = MagicMock()
        mock_boto3_client.return_value = mock_lambda

        # Simulate multiple entities needing Lambda
        _invoke_cache_warmer_lambda_from_preload(
            "arn:aws:lambda:us-east-1:123:function:warmer",
            ["unit", "contact", "business"],
        )

        import json

        payload = json.loads(mock_lambda.invoke.call_args[1]["Payload"])
        assert payload["entity_types"] == ["unit", "contact", "business"]
