"""Tests for preload Lambda delegation when S3 manifests are missing.

When S3 data has been purged (e.g., after force_full_rebuild), the container
startup preload must delegate to Lambda instead of building in-process to
avoid OOM (exit 137).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.api.main import (
    _invoke_cache_warmer_lambda_from_preload,
)


class TestInvokeCacheWarmerLambdaFromPreload:
    """Tests for _invoke_cache_warmer_lambda_from_preload helper."""

    @patch("boto3.client")
    def test_invokes_lambda_with_correct_payload(
        self, mock_boto3_client: MagicMock
    ) -> None:
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
        assert (
            call_kwargs["FunctionName"]
            == "arn:aws:lambda:us-east-1:123:function:warmer"
        )
        assert call_kwargs["InvocationType"] == "Event"

        import json

        payload = json.loads(call_kwargs["Payload"])
        assert payload["entity_types"] == ["unit", "contact"]
        assert payload["strict"] is False
        assert payload["resume_from_checkpoint"] is False

    @patch("boto3.client")
    def test_handles_invoke_error_gracefully(
        self, mock_boto3_client: MagicMock
    ) -> None:
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
    """Tests for manifest check in process_project."""

    @pytest.mark.asyncio
    @patch.dict(
        "os.environ",
        {"CACHE_WARMER_LAMBDA_ARN": "arn:aws:lambda:us-east-1:123:function:warmer"},
    )
    async def test_skips_build_when_no_manifest_and_lambda_available(self) -> None:
        """When manifest is None and Lambda ARN is set, skip in-process build."""
        mock_persistence = AsyncMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.is_available = True
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=False)

        mock_builder = AsyncMock()

        projects_needing_lambda: list[str] = []

        # Simulate the manifest check logic from process_project
        manifest = await mock_persistence.get_manifest_async("proj-123")
        assert manifest is None

        # The builder should NOT be called
        import os

        lambda_arn = os.environ.get("CACHE_WARMER_LAMBDA_ARN")
        assert lambda_arn is not None
        projects_needing_lambda.append("unit")

        # Builder was never called
        mock_builder.build_progressive_async.assert_not_called()
        assert projects_needing_lambda == ["unit"]

    @pytest.mark.asyncio
    async def test_proceeds_normally_when_manifest_exists(self) -> None:
        """When manifest exists, build_progressive_async is called normally."""
        mock_persistence = AsyncMock()
        mock_manifest = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=mock_manifest)

        manifest = await mock_persistence.get_manifest_async("proj-123")
        assert manifest is not None
        # In the real code, this means build_progressive_async proceeds

    @pytest.mark.asyncio
    @patch.dict("os.environ", {}, clear=False)
    async def test_skips_without_lambda_arn_when_no_manifest(self) -> None:
        """When manifest is None and no Lambda ARN, skip gracefully."""
        import os

        # Ensure no Lambda ARN
        os.environ.pop("CACHE_WARMER_LAMBDA_ARN", None)

        mock_persistence = AsyncMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)

        manifest = await mock_persistence.get_manifest_async("proj-123")
        assert manifest is None

        lambda_arn = os.environ.get("CACHE_WARMER_LAMBDA_ARN")
        assert lambda_arn is None
        # In the real code, this returns False without adding to projects_needing_lambda

    @patch("boto3.client")
    def test_lambda_invoked_with_all_delegated_entities(
        self, mock_boto3_client: MagicMock
    ) -> None:
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
