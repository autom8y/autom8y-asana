"""Tests for preload S3 parquet fallback when manifests are missing.

When Lambda warms the cache, it writes dataframe.parquet to S3 and deletes
the manifest. On container startup, preload should detect the missing manifest
and load dataframe.parquet directly into the in-memory cache instead of
delegating to Lambda again (which would leave the container with an empty cache).
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.api.routes.health import set_cache_ready


@pytest.fixture(autouse=True)
def reset_cache_ready():
    set_cache_ready(True)
    yield
    set_cache_ready(True)


def _make_mock_app_and_registry() -> tuple[MagicMock, MagicMock]:
    from autom8_asana.services.resolver import EntityProjectConfig

    registry = MagicMock()
    registry.is_ready.return_value = True
    registry.get_all_entity_types.return_value = ["offer"]
    registry.get_config.return_value = EntityProjectConfig(
        entity_type="offer",
        project_gid="proj_offer",
        project_name="Business Offers",
    )

    app = MagicMock()
    app.state.entity_project_registry = registry
    return app, registry


def _build_patch_stack(
    mock_persistence: MagicMock,
    mock_df_persistence: MagicMock,
    mock_dataframe_cache: MagicMock | None = None,
    mock_watermark_repo: MagicMock | None = None,
    env_overrides: dict[str, str] | None = None,
) -> contextlib.ExitStack:
    """Build patch stack for parquet fallback tests."""
    env = {
        "ASANA_WORKSPACE_GID": "workspace-123",
        "ASANA_BOT_PAT": "test-pat",
        "ASANA_CACHE_S3_BUCKET": "test-bucket",
        "ASANA_CACHE_S3_REGION": "us-east-1",
    }
    if env_overrides:
        env.update(env_overrides)

    if mock_dataframe_cache is None:
        mock_dataframe_cache = MagicMock()
        mock_dataframe_cache.put_async = AsyncMock()

    if mock_watermark_repo is None:
        mock_watermark_repo = MagicMock()
        mock_watermark_repo.set_watermark = MagicMock()

    stack = contextlib.ExitStack()
    stack.enter_context(patch.dict("os.environ", env))
    stack.enter_context(
        patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test-pat")
    )
    stack.enter_context(
        patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
            return_value=mock_dataframe_cache,
        )
    )
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.watermark.get_watermark_repo",
            return_value=mock_watermark_repo,
        )
    )
    stack.enter_context(patch("autom8_asana.dataframes.models.registry.SchemaRegistry"))
    stack.enter_context(
        patch("autom8_asana.dataframes.resolver.DefaultCustomFieldResolver")
    )
    stack.enter_context(patch("autom8_asana.cache.integration.factory.CacheProviderFactory"))
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.section_persistence.SectionPersistence",
            return_value=mock_persistence,
        )
    )
    # Patch S3DataFrameStorage so the progressive preload uses our mock for
    # the parquet fallback path (load_dataframe). The mock_df_persistence
    # serves as the storage instance with .load_dataframe() support.
    # Per TDD-UNIFIED-DF-PERSISTENCE-001 Phase 3: progressive preload now
    # creates S3DataFrameStorage and injects it into SectionPersistence.
    mock_storage_cls = MagicMock(return_value=mock_df_persistence)
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.storage.S3DataFrameStorage",
            mock_storage_cls,
        )
    )
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.storage.create_s3_retry_orchestrator",
            return_value=MagicMock(),
        )
    )
    # Mock settings so S3 bucket is configured (needed for df_storage creation)
    mock_settings = MagicMock()
    mock_settings.s3.bucket = "test-bucket"
    mock_settings.s3.region = "us-east-1"
    mock_settings.s3.endpoint_url = None
    stack.enter_context(
        patch(
            "autom8_asana.settings.get_settings",
            return_value=mock_settings,
        )
    )
    # Also patch the builder (won't be called when parquet fallback succeeds)
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.builders.progressive.ProgressiveProjectBuilder",
        )
    )

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_cls = stack.enter_context(patch("autom8_asana.AsanaClient"))
    mock_client_cls.return_value = mock_client

    return stack


class TestPreloadParquetFallback:
    """Tests for loading dataframe.parquet when manifest is missing."""

    @pytest.mark.asyncio
    async def test_loads_parquet_when_manifest_missing(self) -> None:
        """When manifest is None but dataframe.parquet exists, load it directly."""
        from autom8_asana.api.preload.progressive import _preload_dataframe_cache_progressive

        app, registry = _make_mock_app_and_registry()

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        # Simulate dataframe.parquet existing in S3
        s3_df = pl.DataFrame({"gid": [str(i) for i in range(100)]})
        s3_watermark = datetime.now(UTC) - timedelta(hours=2)
        mock_df_persistence = MagicMock()
        mock_df_persistence.load_dataframe = AsyncMock(
            return_value=(s3_df, s3_watermark)
        )

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        mock_watermark_repo = MagicMock()

        with _build_patch_stack(
            mock_persistence,
            mock_df_persistence,
            mock_dataframe_cache=mock_cache,
            mock_watermark_repo=mock_watermark_repo,
        ):
            await _preload_dataframe_cache_progressive(app)

        # Verify parquet was loaded into memory cache
        mock_cache.put_async.assert_called_once()
        call_args = mock_cache.put_async.call_args
        assert call_args[0][0] == "proj_offer"  # project_gid
        assert call_args[0][1] == "offer"  # entity_type
        assert len(call_args[0][2]) == 100  # DataFrame rows

        # Verify watermark was set
        mock_watermark_repo.set_watermark.assert_called_once_with(
            "proj_offer", s3_watermark
        )

    @pytest.mark.asyncio
    async def test_delegates_to_lambda_when_no_parquet_either(self) -> None:
        """When both manifest and parquet are missing, delegate to Lambda."""
        from autom8_asana.api.preload.progressive import _preload_dataframe_cache_progressive

        app, registry = _make_mock_app_and_registry()

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        # No parquet in S3
        mock_df_persistence = MagicMock()
        mock_df_persistence.load_dataframe = AsyncMock(return_value=(None, None))

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        with _build_patch_stack(
            mock_persistence,
            mock_df_persistence,
            mock_dataframe_cache=mock_cache,
            env_overrides={
                "CACHE_WARMER_LAMBDA_ARN": "arn:aws:lambda:us-east-1:123:function:warmer",
            },
        ):
            with patch("boto3.client") as mock_boto3:
                mock_lambda = MagicMock()
                mock_boto3.return_value = mock_lambda
                await _preload_dataframe_cache_progressive(app)

                # Lambda should be invoked
                mock_lambda.invoke.assert_called_once()

        # Cache should NOT have been populated
        mock_cache.put_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_empty_parquet(self) -> None:
        """When parquet exists but has 0 rows, delegate to Lambda."""
        from autom8_asana.api.preload.progressive import _preload_dataframe_cache_progressive

        app, registry = _make_mock_app_and_registry()

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        # Empty DataFrame
        mock_df_persistence = MagicMock()
        mock_df_persistence.load_dataframe = AsyncMock(
            return_value=(pl.DataFrame({"gid": []}), datetime.now(UTC))
        )

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        with _build_patch_stack(
            mock_persistence,
            mock_df_persistence,
            mock_dataframe_cache=mock_cache,
            env_overrides={
                "CACHE_WARMER_LAMBDA_ARN": "arn:aws:lambda:us-east-1:123:function:warmer",
            },
        ):
            with patch("boto3.client") as mock_boto3:
                mock_lambda = MagicMock()
                mock_boto3.return_value = mock_lambda
                await _preload_dataframe_cache_progressive(app)

                # Should delegate to Lambda since parquet is empty
                mock_lambda.invoke.assert_called_once()

        mock_cache.put_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_parquet_load_error_falls_through_to_lambda(self) -> None:
        """When parquet load raises an exception, delegate to Lambda."""
        from autom8_asana.api.preload.progressive import _preload_dataframe_cache_progressive

        app, registry = _make_mock_app_and_registry()

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        # load_dataframe returns (None, None) on error (its own error handling)
        mock_df_persistence = MagicMock()
        mock_df_persistence.load_dataframe = AsyncMock(return_value=(None, None))

        with _build_patch_stack(
            mock_persistence,
            mock_df_persistence,
            env_overrides={
                "CACHE_WARMER_LAMBDA_ARN": "arn:aws:lambda:us-east-1:123:function:warmer",
            },
        ):
            with patch("boto3.client") as mock_boto3:
                mock_lambda = MagicMock()
                mock_boto3.return_value = mock_lambda
                await _preload_dataframe_cache_progressive(app)

                mock_lambda.invoke.assert_called_once()
