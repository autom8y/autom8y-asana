"""Adversarial edge case tests for preload freshness validation.

Per QA Adversary validation of TDD-cache-freshness-remediation Fix 3:
Tests boundary conditions and error paths for watermark age check.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.api.routes.health import set_cache_ready
from autom8_asana.dataframes.builders.progressive import ProgressiveBuildResult


@pytest.fixture(autouse=True)
def reset_cache_ready():
    set_cache_ready(True)
    yield
    set_cache_ready(True)


def _make_build_result(
    *,
    watermark_age_hours: float = 0,
    sections_resumed: int = 3,
    sections_fetched: int = 0,
    total_rows: int = 80,
) -> ProgressiveBuildResult:
    watermark = datetime.now(UTC) - timedelta(hours=watermark_age_hours)
    return ProgressiveBuildResult(
        df=pl.DataFrame({"gid": [str(i) for i in range(total_rows)]}),
        watermark=watermark,
        total_rows=total_rows,
        sections_fetched=sections_fetched,
        sections_resumed=sections_resumed,
        fetch_time_ms=100.0,
        total_time_ms=200.0,
    )


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
    mock_builder: MagicMock,
    mock_persistence: MagicMock,
    env_overrides: dict[str, str] | None = None,
) -> contextlib.ExitStack:
    """Build a contextlib.ExitStack with all the patches needed for preload tests."""
    env = {
        "ASANA_WORKSPACE_GID": "workspace-123",
        "ASANA_BOT_PAT": "test-pat",
    }
    if env_overrides:
        env.update(env_overrides)

    stack = contextlib.ExitStack()
    stack.enter_context(patch.dict("os.environ", env))
    stack.enter_context(
        patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test-pat")
    )
    stack.enter_context(
        patch("autom8_asana.cache.dataframe.factory.get_dataframe_cache")
    )
    stack.enter_context(patch("autom8_asana.dataframes.watermark.get_watermark_repo"))
    stack.enter_context(
        patch("autom8_asana.dataframes.models.registry.SchemaRegistry")
    )
    stack.enter_context(
        patch("autom8_asana.dataframes.resolver.DefaultCustomFieldResolver")
    )
    stack.enter_context(patch("autom8_asana.cache.factory.CacheProviderFactory"))
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.section_persistence.SectionPersistence",
            return_value=mock_persistence,
        )
    )
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.builders.progressive.ProgressiveProjectBuilder",
            return_value=mock_builder,
        )
    )

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_cls = stack.enter_context(patch("autom8_asana.AsanaClient"))
    mock_client_cls.return_value = mock_client

    return stack


class TestPreloadFreshnessEdgeCases:
    """Adversarial edge case tests for preload freshness validation."""

    @pytest.mark.asyncio
    async def test_preload_exactly_at_threshold_no_catchup(self) -> None:
        """Watermark age == threshold (8.0 hours) should NOT trigger catch-up.

        The code uses strict > (not >=).
        """
        from autom8_asana.api.main import _preload_dataframe_cache_progressive

        app, registry = _make_mock_app_and_registry()

        # 7.999 hours < 8 hours
        result = _make_build_result(watermark_age_hours=7.999, sections_resumed=3)

        mock_builder = MagicMock()
        mock_builder.build_progressive_async = AsyncMock(return_value=result)

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=MagicMock())
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        with _build_patch_stack(mock_builder, mock_persistence):
            await _preload_dataframe_cache_progressive(app)

        # No catch-up (only one call)
        assert mock_builder.build_progressive_async.call_count == 1

    @pytest.mark.asyncio
    async def test_preload_just_over_threshold_triggers_catchup(self) -> None:
        """Watermark age just over threshold (8.001 hours) triggers catch-up."""
        from autom8_asana.api.main import _preload_dataframe_cache_progressive

        app, registry = _make_mock_app_and_registry()

        stale_result = _make_build_result(watermark_age_hours=8.001, sections_resumed=3)
        fresh_result = _make_build_result(
            watermark_age_hours=0, sections_resumed=0, sections_fetched=3,
            total_rows=3,
        )

        mock_builder = MagicMock()
        # First call returns stale, second call (catch-up) returns fresh
        mock_builder.build_progressive_async = AsyncMock(
            side_effect=[stale_result, fresh_result]
        )

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=MagicMock())
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        with _build_patch_stack(mock_builder, mock_persistence):
            await _preload_dataframe_cache_progressive(app)

        # Catch-up was triggered (two calls)
        assert mock_builder.build_progressive_async.call_count == 2

    @pytest.mark.asyncio
    async def test_preload_freshness_invalid_env_var_falls_back(self) -> None:
        """Invalid PRELOAD_FRESHNESS_THRESHOLD_HOURS falls back to 8."""
        from autom8_asana.api.main import _preload_dataframe_cache_progressive

        app, registry = _make_mock_app_and_registry()

        # 7 hours < default 8 hours => no catchup
        result = _make_build_result(watermark_age_hours=7, sections_resumed=3)

        mock_builder = MagicMock()
        mock_builder.build_progressive_async = AsyncMock(return_value=result)

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=MagicMock())
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        with _build_patch_stack(
            mock_builder,
            mock_persistence,
            env_overrides={"PRELOAD_FRESHNESS_THRESHOLD_HOURS": "not_a_number"},
        ):
            # Should not raise
            await _preload_dataframe_cache_progressive(app)

        # With fallback to 8 hours, 7-hour-old data should NOT trigger catchup
        assert mock_builder.build_progressive_async.call_count == 1

    @pytest.mark.asyncio
    async def test_preload_zero_rows_result_still_catches_up(self) -> None:
        """Build result with 0 rows and stale watermark should not crash."""
        from autom8_asana.api.main import _preload_dataframe_cache_progressive

        app, registry = _make_mock_app_and_registry()

        stale_result = _make_build_result(
            watermark_age_hours=10, sections_resumed=3, total_rows=0
        )
        fresh_result = _make_build_result(
            watermark_age_hours=0, sections_resumed=0, total_rows=0,
        )

        mock_builder = MagicMock()
        mock_builder.build_progressive_async = AsyncMock(
            side_effect=[stale_result, fresh_result]
        )

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=MagicMock())
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        with _build_patch_stack(mock_builder, mock_persistence):
            # Should not raise even with 0-row stale result
            await _preload_dataframe_cache_progressive(app)

        # Catch-up should still be attempted (stale + sections_resumed > 0)
        assert mock_builder.build_progressive_async.call_count == 2
