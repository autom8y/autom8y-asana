"""Tests for H-01: asyncio.gather exception objects logged in phase_results loop.

Verifies that when asyncio.gather(..., return_exceptions=True) returns exception
objects in phase_results, the progressive preload logs a warning rather than
silently discarding them.
"""

from __future__ import annotations

import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.api.routes.health import set_cache_ready

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_cache_ready():
    set_cache_ready(True)
    yield
    set_cache_ready(True)


# ---------------------------------------------------------------------------
# Helpers (trimmed from test_progressive_cascade.py)
# ---------------------------------------------------------------------------


def _make_entity_registry(
    *,
    entity_types: list[tuple[str, str, str]] | None = None,
) -> MagicMock:
    from autom8_asana.services.resolver import EntityProjectConfig

    if entity_types is None:
        entity_types = [("business", "proj_biz", "Business")]

    registry = MagicMock()
    registry.is_ready.return_value = True
    registry.get_all_entity_types.return_value = [et[0] for et in entity_types]

    def _get_config(etype: str) -> EntityProjectConfig | None:
        for et, gid, name in entity_types:
            if et == etype:
                return EntityProjectConfig(
                    entity_type=et, project_gid=gid, project_name=name
                )
        return None

    registry.get_config.side_effect = _get_config
    return registry


def _build_patch_stack(
    mock_persistence: MagicMock,
    mock_df_persistence: MagicMock,
) -> contextlib.ExitStack:
    """Minimal patch stack for preload — only patches needed to reach the
    phase_results loop."""
    env = {
        "ASANA_WORKSPACE_GID": "workspace-123",
        "ASANA_BOT_PAT": "test-pat",
        "ASANA_CACHE_S3_BUCKET": "test-bucket",
        "ASANA_CACHE_S3_REGION": "us-east-1",
    }

    mock_dataframe_cache = MagicMock()
    mock_dataframe_cache.put_async = AsyncMock()

    mock_watermark_repo = MagicMock()
    mock_watermark_repo.set_watermark = MagicMock()

    mock_shared_store = MagicMock()
    mock_shared_store.put_batch_async = AsyncMock(return_value=0)

    schema = MagicMock()
    schema.has_cascade_columns.return_value = False

    stack = contextlib.ExitStack()
    stack.enter_context(patch.dict("os.environ", env))

    stack.enter_context(
        patch(
            "autom8_asana.dataframes.cascade_utils.is_cascade_provider",
            side_effect=lambda et: et == "business",
        )
    )
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.cascade_utils.cascade_provider_field_mapping",
            return_value={},
        )
    )
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.cascade_utils.cascade_warm_phases",
            return_value=[["business"]],
        )
    )
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
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.models.registry.get_schema",
            return_value=schema,
        )
    )
    stack.enter_context(
        patch("autom8_asana.dataframes.resolver.DefaultCustomFieldResolver")
    )

    mock_factory = MagicMock()
    mock_factory.create_unified_store.return_value = mock_shared_store
    stack.enter_context(
        patch(
            "autom8_asana.cache.integration.factory.CacheProviderFactory",
            mock_factory,
        )
    )
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.section_persistence.SectionPersistence",
            return_value=mock_persistence,
        )
    )

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

    mock_settings = MagicMock()
    mock_settings.s3.bucket = "test-bucket"
    mock_settings.s3.region = "us-east-1"
    mock_settings.s3.endpoint_url = None
    mock_settings.is_production = False
    stack.enter_context(
        patch(
            "autom8_asana.settings.get_settings",
            return_value=mock_settings,
        )
    )

    stack.enter_context(
        patch(
            "autom8_asana.dataframes.builders.progressive.ProgressiveProjectBuilder",
        )
    )

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    stack.enter_context(patch("autom8_asana.AsanaClient", return_value=mock_client))

    return stack


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPreloadPhaseExceptionLogging:
    """H-01: asyncio.gather exception objects must be logged, not silently discarded."""

    @pytest.mark.asyncio
    async def test_exception_in_phase_results_is_logged(self) -> None:
        """When asyncio.gather returns an exception object, logger.warning is called
        with 'preload_phase_exception_discarded'."""
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        registry = _make_entity_registry()
        app = MagicMock()
        app.state.entity_project_registry = registry

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        mock_df_storage = MagicMock()
        mock_df_storage.load_dataframe = AsyncMock(return_value=(None, None))

        injected_exc = RuntimeError("simulated preload failure")

        # Wrap asyncio.gather so it returns our exception object
        real_gather = __import__("asyncio").gather

        async def fake_gather(*coros, return_exceptions=False):
            # Consume the coroutines to avoid warnings
            for c in coros:
                c.close()
            return [injected_exc]

        with _build_patch_stack(mock_persistence, mock_df_storage):
            with patch(
                "asyncio.gather",
                side_effect=fake_gather,
            ):
                with patch(
                    "autom8_asana.api.preload.progressive.logger"
                ) as mock_logger:
                    await _preload_dataframe_cache_progressive(app)

        # Verify the warning was logged
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c[0][0] == "preload_phase_exception_discarded"
        ]
        assert len(warning_calls) == 1
        extra = warning_calls[0][1]["extra"]
        assert extra["phase"] == 0
        assert extra["exc_type"] == "RuntimeError"
        assert "simulated preload failure" in extra["exc_detail"]

    @pytest.mark.asyncio
    async def test_cancelled_error_is_detected_as_base_exception(self) -> None:
        """asyncio.CancelledError (a BaseException subclass) is also caught."""
        import asyncio as _asyncio

        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        registry = _make_entity_registry()
        app = MagicMock()
        app.state.entity_project_registry = registry

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        mock_df_storage = MagicMock()
        mock_df_storage.load_dataframe = AsyncMock(return_value=(None, None))

        injected_exc = _asyncio.CancelledError()

        async def fake_gather(*coros, return_exceptions=False):
            for c in coros:
                c.close()
            return [injected_exc]

        with _build_patch_stack(mock_persistence, mock_df_storage):
            with patch("asyncio.gather", side_effect=fake_gather):
                with patch(
                    "autom8_asana.api.preload.progressive.logger"
                ) as mock_logger:
                    await _preload_dataframe_cache_progressive(app)

        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c[0][0] == "preload_phase_exception_discarded"
        ]
        assert len(warning_calls) == 1
        assert warning_calls[0][1]["extra"]["exc_type"] == "CancelledError"

    @pytest.mark.asyncio
    async def test_bool_false_is_not_logged_as_exception(self) -> None:
        """False results (normal failure returns) should NOT trigger the warning."""
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        registry = _make_entity_registry()
        app = MagicMock()
        app.state.entity_project_registry = registry

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        mock_df_storage = MagicMock()
        mock_df_storage.load_dataframe = AsyncMock(return_value=(None, None))

        async def fake_gather(*coros, return_exceptions=False):
            for c in coros:
                c.close()
            return [False]

        with _build_patch_stack(mock_persistence, mock_df_storage):
            with patch("asyncio.gather", side_effect=fake_gather):
                with patch(
                    "autom8_asana.api.preload.progressive.logger"
                ) as mock_logger:
                    await _preload_dataframe_cache_progressive(app)

        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c[0][0] == "preload_phase_exception_discarded"
        ]
        assert len(warning_calls) == 0
