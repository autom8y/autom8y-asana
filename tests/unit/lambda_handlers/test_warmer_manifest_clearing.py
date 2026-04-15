"""Unit tests for Lambda warmer manifest preservation.

Originally tested manifest deletion after warm (TDD-cache-freshness-remediation
Fix 2). That behavior was removed because deleting manifests after Lambda warm
caused a fundamental flaw: ECS preload found no manifest, couldn't resume, and
either OOM'd or delegated to Lambda — leaving the container with an empty
in-memory cache (503). Manifests are now preserved; staleness is handled by
the watermark freshness check in the preload path (Fix 3).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.lambda_handlers.cache_warmer import (
    _warm_cache_async,
)


class MockLambdaContext:
    """Mock Lambda context for testing."""

    def __init__(self, remaining_time_ms: int = 600_000, request_id: str = "test-123"):
        self._remaining_time_ms = remaining_time_ms
        self.aws_request_id = request_id

    def get_remaining_time_in_millis(self) -> int:
        return self._remaining_time_ms


class TestWarmerManifestPreservation:
    """Tests that manifests are preserved (not deleted) after warm."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        cache = MagicMock()
        cache.put_async = AsyncMock()
        return cache

    @pytest.fixture
    def mock_checkpoint_manager(self) -> MagicMock:
        mgr = MagicMock()
        mgr.load_async = AsyncMock(return_value=None)
        mgr.save_async = AsyncMock(return_value=True)
        mgr.clear_async = AsyncMock(return_value=True)
        return mgr

    async def test_warmer_preserves_manifest_on_success(
        self,
        mock_cache: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Manifest is NOT deleted after successful warm (preserved for ECS preload)."""
        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True
        mock_registry.get_project_gid.return_value = "project-123"

        mock_warmer = MagicMock()
        mock_warm_status = MagicMock()
        mock_warm_status.result.name = "SUCCESS"
        mock_warm_status.row_count = 100
        mock_warm_status.error = None
        mock_warm_status.to_dict.return_value = {
            "entity_type": "offer",
            "result": "success",
            "row_count": 100,
        }
        mock_warmer.warm_entity_async = AsyncMock(return_value=mock_warm_status)

        mock_section_persistence = MagicMock()
        mock_section_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_section_persistence.__aenter__ = AsyncMock(return_value=mock_section_persistence)
        mock_section_persistence.__aexit__ = AsyncMock(return_value=None)

        context = MockLambdaContext(remaining_time_ms=600_000)

        with (
            patch.dict(
                "os.environ",
                {
                    "ASANA_WORKSPACE_GID": "workspace-123",
                    "ASANA_CACHE_S3_BUCKET": "test-bucket",
                },
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=mock_registry,
            ),
            patch(
                "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
                return_value=mock_checkpoint_manager,
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test-pat",
            ),
            patch(
                "autom8_asana.cache.dataframe.warmer.CacheWarmer",
                return_value=mock_warmer,
            ),
            patch(
                "autom8_asana.cache.dataframe.warmer.WarmResult",
            ) as mock_warm_result,
            patch("autom8_asana.AsanaClient"),
            patch("autom8_asana.lambda_handlers.cache_warmer.emit_metric"),
            patch(
                "autom8_asana.dataframes.section_persistence.SectionPersistence",
                return_value=mock_section_persistence,
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._push_gid_mappings_for_completed_entities",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._push_account_status_for_completed_entities",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._warm_story_caches_for_completed_entities",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._run_vertical_backfill",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._aggregate_pipeline_stages",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._run_reconciliation_shadow",
                new_callable=AsyncMock,
            ),
        ):
            mock_warm_result.SUCCESS = mock_warm_status.result

            response = await _warm_cache_async(
                entity_types=["offer"],
                resume_from_checkpoint=False,
                context=context,
            )

        # Manifest should NOT be deleted — preserved for ECS preload resumption
        mock_section_persistence.delete_manifest_async.assert_not_called()
        assert response.success is True

    async def test_warmer_does_not_touch_manifest_on_failure(
        self,
        mock_cache: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Manifest is not touched when entity warm fails."""
        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True
        mock_registry.get_project_gid.return_value = "project-123"

        mock_warmer = MagicMock()
        mock_warm_status = MagicMock()
        mock_warm_status.result.name = "FAILURE"
        mock_warm_status.row_count = 0
        mock_warm_status.error = "Some error"
        mock_warm_status.to_dict.return_value = {
            "entity_type": "offer",
            "result": "failure",
            "row_count": 0,
            "error": "Some error",
        }
        mock_warmer.warm_entity_async = AsyncMock(return_value=mock_warm_status)

        mock_section_persistence = MagicMock()
        mock_section_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_section_persistence.__aenter__ = AsyncMock(return_value=mock_section_persistence)
        mock_section_persistence.__aexit__ = AsyncMock(return_value=None)

        context = MockLambdaContext(remaining_time_ms=600_000)

        with (
            patch.dict(
                "os.environ",
                {
                    "ASANA_WORKSPACE_GID": "workspace-123",
                    "ASANA_CACHE_S3_BUCKET": "test-bucket",
                },
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=mock_registry,
            ),
            patch(
                "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
                return_value=mock_checkpoint_manager,
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test-pat",
            ),
            patch(
                "autom8_asana.cache.dataframe.warmer.CacheWarmer",
                return_value=mock_warmer,
            ),
            patch(
                "autom8_asana.cache.dataframe.warmer.WarmResult",
            ) as mock_warm_result,
            patch("autom8_asana.AsanaClient"),
            patch("autom8_asana.lambda_handlers.cache_warmer.emit_metric"),
            patch(
                "autom8_asana.dataframes.section_persistence.SectionPersistence",
                return_value=mock_section_persistence,
            ),
        ):
            mock_warm_result.SUCCESS = MagicMock()

            response = await _warm_cache_async(
                entity_types=["offer"],
                strict=False,
                resume_from_checkpoint=False,
                context=context,
            )

        # Manifest should NOT be deleted on failure either
        mock_section_persistence.delete_manifest_async.assert_not_called()
