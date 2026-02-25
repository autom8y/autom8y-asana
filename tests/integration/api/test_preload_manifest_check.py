"""Integration tests for preload manifest check branching in process_project.

Replaces the 3 simulation tests deleted during slop-chop P1 (RS-013/LS-008).
These tests call the real _preload_dataframe_cache_progressive function and
verify observable behavior through the three manifest-check branches:

1. Manifest exists: progressive build proceeds
2. No manifest + Lambda ARN: delegates to Lambda, skips local build
3. No manifest + no Lambda ARN: skips preload for that project

All external boundaries (S3, Asana API, Lambda, settings) are mocked at
their source modules because progressive.py uses lazy (in-body) imports.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.api.preload.progressive import (
    _preload_dataframe_cache_progressive,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _FakeEntityConfig:
    """Minimal stand-in for EntityProjectConfig."""

    entity_type: str
    project_gid: str
    project_name: str = "Test Project"
    schema_task_type: str | None = None


def _make_mock_app(project_configs: list[_FakeEntityConfig]) -> MagicMock:
    """Build a mock FastAPI app whose entity_project_registry yields *configs*."""
    registry = MagicMock()
    registry.is_ready.return_value = True
    registry.get_all_entity_types.return_value = [
        c.entity_type for c in project_configs
    ]
    registry.get_config.side_effect = lambda et: next(
        (c for c in project_configs if c.entity_type == et), None
    )

    app = MagicMock()
    app.state.entity_project_registry = registry
    return app


def _make_mock_settings(*, bucket: str = "test-bucket") -> MagicMock:
    """Build a mock Settings object with S3 config."""
    settings = MagicMock()
    settings.s3.bucket = bucket
    settings.s3.region = "us-east-1"
    settings.s3.endpoint_url = None
    return settings


def _make_mock_persistence(
    *,
    manifest: object | None = MagicMock(),
    is_available: bool = True,
) -> MagicMock:
    """Build a mock SectionPersistence.

    Args:
        manifest: Return value for get_manifest_async. Use MagicMock() to
            simulate manifest-exists; None to simulate no-manifest.
        is_available: Whether S3 persistence reports available.
    """
    persistence = MagicMock()
    persistence.is_available = is_available
    persistence.get_manifest_async = AsyncMock(return_value=manifest)
    persistence.__aenter__ = AsyncMock(return_value=persistence)
    persistence.__aexit__ = AsyncMock(return_value=False)
    return persistence


def _make_mock_df_storage(
    *,
    dataframe: object | None = None,
    watermark: datetime | None = None,
    is_available: bool = True,
) -> MagicMock:
    """Build a mock S3DataFrameStorage."""
    storage = MagicMock()
    storage.is_available = is_available
    storage.load_dataframe = AsyncMock(return_value=(dataframe, watermark))
    return storage


def _make_mock_builder_result(
    *,
    total_rows: int = 10,
    sections_succeeded: int = 2,
    sections_resumed: int = 1,
) -> MagicMock:
    """Build a mock BuildResult."""
    import polars as pl

    result = MagicMock()
    result.total_rows = total_rows
    result.sections_succeeded = sections_succeeded
    result.sections_resumed = sections_resumed
    result.watermark = datetime.now(UTC)
    result.dataframe = pl.DataFrame({"gid": ["1"] * total_rows})
    return result


# ---------------------------------------------------------------------------
# Patch targets at source modules (lazy imports inside the function body)
# ---------------------------------------------------------------------------

_PATCHES_COMMON = {
    "bot_pat": "autom8_asana.auth.bot_pat.get_bot_pat",
    "workspace": "autom8_asana.config.get_workspace_gid",
    "settings": "autom8_asana.settings.get_settings",
    "s3_storage_cls": "autom8_asana.dataframes.storage.S3DataFrameStorage",
    "s3_retry": "autom8_asana.dataframes.storage.create_s3_retry_orchestrator",
    "section_persist": "autom8_asana.dataframes.section_persistence.SectionPersistence",
    "watermark_repo": "autom8_asana.dataframes.watermark.get_watermark_repo",
    "df_cache": "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
    "set_ready": "autom8_asana.api.routes.health.set_cache_ready",
    "asana_client": "autom8_asana.AsanaClient",
    "builder_cls": "autom8_asana.dataframes.builders.progressive.ProgressiveProjectBuilder",
    "get_schema": "autom8_asana.dataframes.models.registry.get_schema",
    "resolver": "autom8_asana.dataframes.resolver.DefaultCustomFieldResolver",
    "cpf": "autom8_asana.cache.integration.factory.CacheProviderFactory",
    "cache_config": "autom8_asana.config.CacheConfig",
}

_PROGRESSIVE_MODULE = "autom8_asana.api.preload.progressive"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPreloadManifestCheckIntegration:
    """Integration tests that call the real _preload_dataframe_cache_progressive
    and verify manifest-check branching via observable side effects.
    """

    async def test_manifest_exists_proceeds_with_progressive_build(
        self,
    ) -> None:
        """Branch 1: manifest exists -- builder.build_progressive_async is called."""
        entity_config = _FakeEntityConfig(entity_type="unit", project_gid="proj-111")
        app = _make_mock_app([entity_config])
        mock_settings = _make_mock_settings()
        mock_persistence = _make_mock_persistence(manifest=MagicMock())
        mock_df_storage = _make_mock_df_storage(is_available=True)
        mock_build_result = _make_mock_builder_result()
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_progressive_async = AsyncMock(
            return_value=mock_build_result
        )

        with (
            patch(_PATCHES_COMMON["bot_pat"], return_value="fake-pat"),
            patch(_PATCHES_COMMON["workspace"], return_value="ws-001"),
            patch(_PATCHES_COMMON["settings"], return_value=mock_settings),
            patch(
                _PATCHES_COMMON["s3_storage_cls"],
                return_value=mock_df_storage,
            ),
            patch(_PATCHES_COMMON["s3_retry"]),
            patch(
                _PATCHES_COMMON["section_persist"],
                return_value=mock_persistence,
            ),
            patch(_PATCHES_COMMON["watermark_repo"]) as mock_wm_fn,
            patch(_PATCHES_COMMON["df_cache"]) as mock_cache_fn,
            patch(_PATCHES_COMMON["set_ready"]) as mock_set_ready,
            patch(_PATCHES_COMMON["asana_client"]) as MockClient,
            patch(
                _PATCHES_COMMON["builder_cls"],
                return_value=mock_builder_instance,
            ),
            patch(_PATCHES_COMMON["get_schema"]),
            patch(_PATCHES_COMMON["resolver"]),
            patch(_PATCHES_COMMON["cpf"]),
            patch(_PATCHES_COMMON["cache_config"]),
        ):
            # Wire async context manager for AsanaClient
            mock_client_cm = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_cm)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_wm_fn.return_value = MagicMock()
            mock_cache_fn.return_value = AsyncMock()

            await _preload_dataframe_cache_progressive(app)

            # Observable: build_progressive_async was called (manifest branch)
            mock_builder_instance.build_progressive_async.assert_awaited_once_with(
                resume=True,
            )

            # Observable: cache_ready set to True at end
            mock_set_ready.assert_called_with(True)

    async def test_no_manifest_with_lambda_arn_delegates_to_lambda(
        self,
    ) -> None:
        """Branch 2: no manifest + Lambda ARN -- delegates, skips local build."""
        entity_config = _FakeEntityConfig(entity_type="unit", project_gid="proj-222")
        app = _make_mock_app([entity_config])
        mock_settings = _make_mock_settings()
        mock_persistence = _make_mock_persistence(manifest=None)
        mock_df_storage = _make_mock_df_storage(
            dataframe=None, watermark=None, is_available=True
        )
        mock_builder_instance = AsyncMock()

        with (
            patch(_PATCHES_COMMON["bot_pat"], return_value="fake-pat"),
            patch(_PATCHES_COMMON["workspace"], return_value="ws-001"),
            patch(_PATCHES_COMMON["settings"], return_value=mock_settings),
            patch(
                _PATCHES_COMMON["s3_storage_cls"],
                return_value=mock_df_storage,
            ),
            patch(_PATCHES_COMMON["s3_retry"]),
            patch(
                _PATCHES_COMMON["section_persist"],
                return_value=mock_persistence,
            ),
            patch(_PATCHES_COMMON["watermark_repo"]) as mock_wm_fn,
            patch(_PATCHES_COMMON["df_cache"]) as mock_cache_fn,
            patch(_PATCHES_COMMON["set_ready"]) as mock_set_ready,
            patch(_PATCHES_COMMON["asana_client"]) as MockClient,
            patch(
                _PATCHES_COMMON["builder_cls"],
                return_value=mock_builder_instance,
            ),
            patch(_PATCHES_COMMON["get_schema"]),
            patch(_PATCHES_COMMON["resolver"]),
            patch(_PATCHES_COMMON["cpf"]),
            patch(_PATCHES_COMMON["cache_config"]),
            patch(
                f"{_PROGRESSIVE_MODULE}._invoke_cache_warmer_lambda_from_preload",
            ) as mock_invoke_lambda,
            patch.dict(
                os.environ,
                {
                    "CACHE_WARMER_LAMBDA_ARN": "arn:aws:lambda:us-east-1:123:function:warmer",
                },
            ),
        ):
            mock_client_cm = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_cm)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_wm_fn.return_value = MagicMock()
            mock_cache_fn.return_value = AsyncMock()

            await _preload_dataframe_cache_progressive(app)

            # Observable: builder was NOT called (no local build)
            mock_builder_instance.build_progressive_async.assert_not_awaited()

            # Observable: Lambda delegation invoked with entity type
            mock_invoke_lambda.assert_called_once_with(
                "arn:aws:lambda:us-east-1:123:function:warmer",
                ["unit"],
            )

            # Observable: cache_ready still set to True
            mock_set_ready.assert_called_with(True)

    async def test_no_manifest_no_lambda_arn_skips_preload(self) -> None:
        """Branch 3: no manifest + no Lambda ARN -- skips, logs warning."""
        entity_config = _FakeEntityConfig(entity_type="unit", project_gid="proj-333")
        app = _make_mock_app([entity_config])
        mock_settings = _make_mock_settings()
        mock_persistence = _make_mock_persistence(manifest=None)
        mock_df_storage = _make_mock_df_storage(
            dataframe=None, watermark=None, is_available=True
        )
        mock_builder_instance = AsyncMock()

        # Build an env dict that definitely lacks CACHE_WARMER_LAMBDA_ARN.
        env_without_lambda = {
            k: v for k, v in os.environ.items() if k != "CACHE_WARMER_LAMBDA_ARN"
        }

        with (
            patch(_PATCHES_COMMON["bot_pat"], return_value="fake-pat"),
            patch(_PATCHES_COMMON["workspace"], return_value="ws-001"),
            patch(_PATCHES_COMMON["settings"], return_value=mock_settings),
            patch(
                _PATCHES_COMMON["s3_storage_cls"],
                return_value=mock_df_storage,
            ),
            patch(_PATCHES_COMMON["s3_retry"]),
            patch(
                _PATCHES_COMMON["section_persist"],
                return_value=mock_persistence,
            ),
            patch(_PATCHES_COMMON["watermark_repo"]) as mock_wm_fn,
            patch(_PATCHES_COMMON["df_cache"]) as mock_cache_fn,
            patch(_PATCHES_COMMON["set_ready"]) as mock_set_ready,
            patch(_PATCHES_COMMON["asana_client"]) as MockClient,
            patch(
                _PATCHES_COMMON["builder_cls"],
                return_value=mock_builder_instance,
            ),
            patch(_PATCHES_COMMON["get_schema"]),
            patch(_PATCHES_COMMON["resolver"]),
            patch(_PATCHES_COMMON["cpf"]),
            patch(_PATCHES_COMMON["cache_config"]),
            patch(
                f"{_PROGRESSIVE_MODULE}._invoke_cache_warmer_lambda_from_preload",
            ) as mock_invoke_lambda,
            patch.dict(os.environ, env_without_lambda, clear=True),
            patch(f"{_PROGRESSIVE_MODULE}.logger") as mock_logger,
        ):
            mock_client_cm = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_cm)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_wm_fn.return_value = MagicMock()
            mock_cache_fn.return_value = AsyncMock()

            await _preload_dataframe_cache_progressive(app)

            # Observable: builder was NOT called
            mock_builder_instance.build_progressive_async.assert_not_awaited()

            # Observable: Lambda was NOT invoked (no ARN)
            mock_invoke_lambda.assert_not_called()

            # Observable: warning logged about no manifest and no Lambda
            warning_events = [
                call.args[0] for call in mock_logger.warning.call_args_list
            ]
            assert "progressive_preload_no_manifest_no_lambda" in warning_events

            # Observable: cache_ready still set to True
            mock_set_ready.assert_called_with(True)
