"""Unit tests for admin force_full_rebuild endpoint behavior.

Verifies the lightweight delete+Lambda pattern replaces the heavy
in-process builder, preventing OOM kills.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch targets match where imports are resolved in _perform_force_rebuild:
#   from autom8_asana.services.resolver import EntityProjectRegistry
#   from autom8_asana.cache.dataframe.factory import get_dataframe_cache
#   from autom8_asana.dataframes.section_persistence import SectionPersistence
_REGISTRY_PATCH = "autom8_asana.services.resolver.EntityProjectRegistry.get_instance"
_CACHE_PATCH = "autom8_asana.cache.dataframe.factory.get_dataframe_cache"
_PERSISTENCE_PATCH = "autom8_asana.dataframes.section_persistence.SectionPersistence"
_LAMBDA_PATCH = "autom8_asana.api.routes.admin._invoke_cache_warmer_lambda"


@pytest.fixture
def mock_registry():
    """Mock EntityProjectRegistry that maps entity types to project GIDs."""
    registry = MagicMock()
    registry.get_project_gid.side_effect = lambda et: {
        "unit": "proj-unit",
        "business": "proj-business",
        "offer": "proj-offer",
        "contact": "proj-contact",
        "asset_edit": "proj-asset-edit",
    }.get(et)
    return registry


@pytest.fixture
def mock_persistence():
    """Mock SectionPersistence with async context manager support."""
    persistence = MagicMock()
    persistence.delete_manifest_async = AsyncMock(return_value=True)
    persistence.delete_section_files_async = AsyncMock(return_value=True)
    persistence.storage.delete_dataframe = AsyncMock(return_value=True)
    persistence.__aenter__ = AsyncMock(return_value=persistence)
    persistence.__aexit__ = AsyncMock(return_value=False)
    return persistence


@pytest.fixture
def mock_dataframe_cache():
    """Mock DataFrameCache."""
    cache = MagicMock()
    cache.invalidate = MagicMock()
    return cache


class TestForceRebuildDeletesS3Data:
    """Verify force rebuild deletes both manifest and section files."""

    @pytest.mark.asyncio
    async def test_force_rebuild_deletes_manifest_and_sections(
        self, mock_registry, mock_persistence, mock_dataframe_cache
    ) -> None:
        """Both delete_manifest_async and delete_section_files_async should be called."""
        from autom8_asana.api.routes.admin import _perform_force_rebuild

        with (
            patch(_REGISTRY_PATCH, return_value=mock_registry),
            patch(_CACHE_PATCH, return_value=mock_dataframe_cache),
            patch(_PERSISTENCE_PATCH, return_value=mock_persistence),
            patch.dict("os.environ", {}, clear=False),
        ):
            await _perform_force_rebuild(["unit", "contact"], "test-refresh-id")

        # Should have called delete for each entity type
        assert mock_persistence.delete_manifest_async.call_count == 2
        assert mock_persistence.delete_section_files_async.call_count == 2

        # Verify correct project GIDs
        manifest_calls = [
            c.args[0] for c in mock_persistence.delete_manifest_async.call_args_list
        ]
        assert "proj-unit" in manifest_calls
        assert "proj-contact" in manifest_calls

    @pytest.mark.asyncio
    async def test_force_rebuild_invalidates_memory_cache(
        self, mock_registry, mock_persistence, mock_dataframe_cache
    ) -> None:
        """Memory cache should be invalidated for each entity type."""
        from autom8_asana.api.routes.admin import _perform_force_rebuild

        with (
            patch(_REGISTRY_PATCH, return_value=mock_registry),
            patch(_CACHE_PATCH, return_value=mock_dataframe_cache),
            patch(_PERSISTENCE_PATCH, return_value=mock_persistence),
            patch.dict("os.environ", {}, clear=False),
        ):
            await _perform_force_rebuild(["unit"], "test-refresh-id")

        mock_dataframe_cache.invalidate.assert_called_once_with("proj-unit", "unit")


class TestForceRebuildLambdaInvocation:
    """Verify Lambda cache warmer invocation behavior."""

    @pytest.mark.asyncio
    async def test_force_rebuild_invokes_lambda_when_arn_set(
        self, mock_registry, mock_persistence, mock_dataframe_cache
    ) -> None:
        """When CACHE_WARMER_LAMBDA_ARN is set, Lambda should be invoked."""
        from autom8_asana.api.routes.admin import _perform_force_rebuild

        mock_invoke = MagicMock()

        with (
            patch(_REGISTRY_PATCH, return_value=mock_registry),
            patch(_CACHE_PATCH, return_value=mock_dataframe_cache),
            patch(_PERSISTENCE_PATCH, return_value=mock_persistence),
            patch.dict(
                "os.environ",
                {
                    "CACHE_WARMER_LAMBDA_ARN": "arn:aws:lambda:us-east-1:123:function:cache-warmer"
                },
            ),
            patch(_LAMBDA_PATCH, mock_invoke),
        ):
            await _perform_force_rebuild(["unit", "contact"], "test-refresh-id")

        mock_invoke.assert_called_once_with(
            "arn:aws:lambda:us-east-1:123:function:cache-warmer",
            ["unit", "contact"],
            "test-refresh-id",
        )

    @pytest.mark.asyncio
    async def test_force_rebuild_no_lambda_when_arn_not_set(
        self, mock_registry, mock_persistence, mock_dataframe_cache
    ) -> None:
        """When CACHE_WARMER_LAMBDA_ARN is not set, no Lambda should be invoked."""
        from autom8_asana.api.routes.admin import _perform_force_rebuild

        mock_invoke = MagicMock()

        with (
            patch(_REGISTRY_PATCH, return_value=mock_registry),
            patch(_CACHE_PATCH, return_value=mock_dataframe_cache),
            patch(_PERSISTENCE_PATCH, return_value=mock_persistence),
            patch.dict("os.environ", {}, clear=False),
            patch(_LAMBDA_PATCH, mock_invoke),
        ):
            import os

            os.environ.pop("CACHE_WARMER_LAMBDA_ARN", None)
            await _perform_force_rebuild(["unit"], "test-refresh-id")

        mock_invoke.assert_not_called()


class TestInvokeCacheWarmerLambda:
    """Tests for the _invoke_cache_warmer_lambda helper."""

    def test_invoke_calls_boto3_with_correct_payload(self) -> None:
        """Lambda invoke should use Event invocation type with correct payload."""
        from autom8_asana.api.routes.admin import _invoke_cache_warmer_lambda

        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client):
            _invoke_cache_warmer_lambda(
                "arn:aws:lambda:us-east-1:123:function:cache-warmer",
                ["unit", "contact"],
                "test-refresh-id",
            )

        mock_client.invoke.assert_called_once()
        call_kwargs = mock_client.invoke.call_args.kwargs
        assert (
            call_kwargs["FunctionName"]
            == "arn:aws:lambda:us-east-1:123:function:cache-warmer"
        )
        assert call_kwargs["InvocationType"] == "Event"

        import json

        payload = json.loads(call_kwargs["Payload"])
        assert payload["entity_types"] == ["unit", "contact"]
        assert payload["strict"] is False
        assert payload["resume_from_checkpoint"] is False

    def test_invoke_handles_boto3_exception(self) -> None:
        """Lambda invoke failure should be logged, not raised."""
        from autom8_asana.api.routes.admin import _invoke_cache_warmer_lambda

        mock_client = MagicMock()
        mock_client.invoke.side_effect = Exception("Lambda unavailable")
        with patch("boto3.client", return_value=mock_client):
            # Should not raise
            _invoke_cache_warmer_lambda(
                "arn:aws:lambda:us-east-1:123:function:cache-warmer",
                ["unit"],
                "test-refresh-id",
            )


class TestForceRebuildNoInProcessBuilder:
    """Verify that force path does NOT instantiate ProgressiveProjectBuilder."""

    @pytest.mark.asyncio
    async def test_force_rebuild_no_in_process_builder(
        self, mock_registry, mock_persistence, mock_dataframe_cache
    ) -> None:
        """ProgressiveProjectBuilder should never be instantiated during force path."""
        from autom8_asana.api.routes.admin import _perform_force_rebuild

        with (
            patch(_REGISTRY_PATCH, return_value=mock_registry),
            patch(_CACHE_PATCH, return_value=mock_dataframe_cache),
            patch(_PERSISTENCE_PATCH, return_value=mock_persistence),
            patch.dict("os.environ", {}, clear=False),
        ):
            await _perform_force_rebuild(
                ["unit", "business", "offer", "contact", "asset_edit"],
                "test-refresh-id",
            )

        # The force rebuild path should not import or use ProgressiveProjectBuilder.
        import inspect

        source = inspect.getsource(_perform_force_rebuild)
        assert "ProgressiveProjectBuilder" not in source

    @pytest.mark.asyncio
    async def test_force_rebuild_skips_unknown_project_gid(
        self, mock_persistence, mock_dataframe_cache
    ) -> None:
        """Entity types with no project GID should be skipped gracefully."""
        from autom8_asana.api.routes.admin import _perform_force_rebuild

        registry = MagicMock()
        registry.get_project_gid.return_value = None

        with (
            patch(_REGISTRY_PATCH, return_value=registry),
            patch(_CACHE_PATCH, return_value=mock_dataframe_cache),
            patch(_PERSISTENCE_PATCH, return_value=mock_persistence),
            patch.dict("os.environ", {}, clear=False),
        ):
            # Should not raise
            await _perform_force_rebuild(["unknown_type"], "test-refresh-id")

        # No S3 operations should have been attempted
        mock_persistence.delete_manifest_async.assert_not_called()
        mock_persistence.delete_section_files_async.assert_not_called()


class TestForceRebuildDeletesMergedArtifacts:
    """Verify force rebuild deletes merged dataframe.parquet and watermark.json.

    Per ADR-HOTFIX-002: prevents ProgressiveTier from re-hydrating stale data.
    """

    @pytest.mark.asyncio
    async def test_force_rebuild_deletes_merged_artifacts(
        self, mock_registry, mock_persistence, mock_dataframe_cache
    ) -> None:
        """persistence.storage.delete_dataframe should be called for each entity."""
        from autom8_asana.api.routes.admin import _perform_force_rebuild

        with (
            patch(_REGISTRY_PATCH, return_value=mock_registry),
            patch(_CACHE_PATCH, return_value=mock_dataframe_cache),
            patch(_PERSISTENCE_PATCH, return_value=mock_persistence),
            patch.dict("os.environ", {}, clear=False),
        ):
            await _perform_force_rebuild(["unit", "contact"], "test-refresh-id")

        # Should have called delete_dataframe for each entity type
        assert mock_persistence.storage.delete_dataframe.call_count == 2

        # Verify correct project GIDs
        delete_calls = [
            c.args[0] for c in mock_persistence.storage.delete_dataframe.call_args_list
        ]
        assert "proj-unit" in delete_calls
        assert "proj-contact" in delete_calls
