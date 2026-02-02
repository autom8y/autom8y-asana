"""Unit tests for preload freshness validation.

Per TDD-cache-freshness-remediation Fix 3: Tests for watermark age check
after progressive preload that triggers incremental catch-up.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.api.routes.health import set_cache_ready
from autom8_asana.dataframes.builders.progressive import ProgressiveBuildResult


@pytest.fixture(autouse=True)
def reset_cache_ready():
    """Reset cache ready state before and after each test."""
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
    """Create a ProgressiveBuildResult with specified watermark age."""
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
    """Create mock app and entity registry."""
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


class TestPreloadFreshnessValidation:
    """Tests for preload freshness validation with catch-up."""

    @pytest.mark.asyncio
    async def test_preload_triggers_catchup_for_stale_data(self) -> None:
        """Stale watermark with sections_resumed > 0 triggers catch-up."""
        from autom8_asana.api.main import _preload_dataframe_cache_progressive

        app, registry = _make_mock_app_and_registry()

        # Build result with stale watermark (10 hours > 8 hour threshold)
        stale_result = _make_build_result(
            watermark_age_hours=10, sections_resumed=3
        )
        catchup_df = pl.DataFrame({"gid": ["1", "2", "3"]})

        mock_builder = MagicMock()
        mock_builder.build_progressive_async = AsyncMock(return_value=stale_result)
        mock_builder.build_with_parallel_fetch_async = AsyncMock(
            return_value=catchup_df
        )

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        with (
            patch.dict(
                "os.environ",
                {
                    "ASANA_WORKSPACE_GID": "workspace-123",
                    "ASANA_BOT_PAT": "test-pat",
                },
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test-pat",
            ),
            patch(
                "autom8_asana.dataframes.section_persistence.SectionPersistence",
                return_value=mock_persistence,
            ),
            patch(
                "autom8_asana.dataframes.builders.progressive.ProgressiveProjectBuilder",
                return_value=mock_builder,
            ),
            patch("autom8_asana.cache.dataframe.factory.get_dataframe_cache"),
            patch("autom8_asana.dataframes.watermark.get_watermark_repo"),
            patch("autom8_asana.AsanaClient") as mock_client_cls,
            patch("autom8_asana.dataframes.models.registry.SchemaRegistry"),
            patch("autom8_asana.dataframes.resolver.DefaultCustomFieldResolver"),
            patch("autom8_asana.cache.factory.CacheProviderFactory"),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            await _preload_dataframe_cache_progressive(app)

        # Verify catch-up was triggered
        mock_builder.build_with_parallel_fetch_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_preload_skips_catchup_for_fresh_data(self) -> None:
        """Fresh watermark does not trigger catch-up."""
        from autom8_asana.api.main import _preload_dataframe_cache_progressive

        app, registry = _make_mock_app_and_registry()

        # Build result with fresh watermark (2 hours < 8 hour threshold)
        fresh_result = _make_build_result(
            watermark_age_hours=2, sections_resumed=3
        )

        mock_builder = MagicMock()
        mock_builder.build_progressive_async = AsyncMock(return_value=fresh_result)
        mock_builder.build_with_parallel_fetch_async = AsyncMock()

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        with (
            patch.dict(
                "os.environ",
                {
                    "ASANA_WORKSPACE_GID": "workspace-123",
                    "ASANA_BOT_PAT": "test-pat",
                },
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test-pat",
            ),
            patch(
                "autom8_asana.dataframes.section_persistence.SectionPersistence",
                return_value=mock_persistence,
            ),
            patch(
                "autom8_asana.dataframes.builders.progressive.ProgressiveProjectBuilder",
                return_value=mock_builder,
            ),
            patch("autom8_asana.cache.dataframe.factory.get_dataframe_cache"),
            patch("autom8_asana.dataframes.watermark.get_watermark_repo"),
            patch("autom8_asana.AsanaClient") as mock_client_cls,
            patch("autom8_asana.dataframes.models.registry.SchemaRegistry"),
            patch("autom8_asana.dataframes.resolver.DefaultCustomFieldResolver"),
            patch("autom8_asana.cache.factory.CacheProviderFactory"),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            await _preload_dataframe_cache_progressive(app)

        # Catch-up should NOT be triggered
        mock_builder.build_with_parallel_fetch_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_preload_skips_catchup_when_no_resume(self) -> None:
        """Stale watermark with sections_resumed == 0 does not trigger catch-up."""
        from autom8_asana.api.main import _preload_dataframe_cache_progressive

        app, registry = _make_mock_app_and_registry()

        # Build result with stale watermark but no sections resumed
        # (all sections were freshly fetched)
        result = _make_build_result(
            watermark_age_hours=10, sections_resumed=0, sections_fetched=5
        )

        mock_builder = MagicMock()
        mock_builder.build_progressive_async = AsyncMock(return_value=result)
        mock_builder.build_with_parallel_fetch_async = AsyncMock()

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        with (
            patch.dict(
                "os.environ",
                {
                    "ASANA_WORKSPACE_GID": "workspace-123",
                    "ASANA_BOT_PAT": "test-pat",
                },
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test-pat",
            ),
            patch(
                "autom8_asana.dataframes.section_persistence.SectionPersistence",
                return_value=mock_persistence,
            ),
            patch(
                "autom8_asana.dataframes.builders.progressive.ProgressiveProjectBuilder",
                return_value=mock_builder,
            ),
            patch("autom8_asana.cache.dataframe.factory.get_dataframe_cache"),
            patch("autom8_asana.dataframes.watermark.get_watermark_repo"),
            patch("autom8_asana.AsanaClient") as mock_client_cls,
            patch("autom8_asana.dataframes.models.registry.SchemaRegistry"),
            patch("autom8_asana.dataframes.resolver.DefaultCustomFieldResolver"),
            patch("autom8_asana.cache.factory.CacheProviderFactory"),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            await _preload_dataframe_cache_progressive(app)

        # Catch-up should NOT be triggered (sections_resumed == 0)
        mock_builder.build_with_parallel_fetch_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_preload_graceful_on_catchup_failure(self) -> None:
        """Preload completes with stale data when catch-up fails."""
        from autom8_asana.api.main import _preload_dataframe_cache_progressive

        app, registry = _make_mock_app_and_registry()

        stale_result = _make_build_result(
            watermark_age_hours=10, sections_resumed=3
        )

        mock_builder = MagicMock()
        mock_builder.build_progressive_async = AsyncMock(return_value=stale_result)
        # Catch-up raises exception
        mock_builder.build_with_parallel_fetch_async = AsyncMock(
            side_effect=Exception("API rate limited")
        )

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        mock_dataframe_cache = MagicMock()
        mock_dataframe_cache.put_async = AsyncMock()

        mock_watermark_repo = MagicMock()
        mock_watermark_repo.set_watermark = MagicMock()

        with (
            patch.dict(
                "os.environ",
                {
                    "ASANA_WORKSPACE_GID": "workspace-123",
                    "ASANA_BOT_PAT": "test-pat",
                },
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test-pat",
            ),
            patch(
                "autom8_asana.dataframes.section_persistence.SectionPersistence",
                return_value=mock_persistence,
            ),
            patch(
                "autom8_asana.dataframes.builders.progressive.ProgressiveProjectBuilder",
                return_value=mock_builder,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_dataframe_cache,
            ),
            patch(
                "autom8_asana.dataframes.watermark.get_watermark_repo",
                return_value=mock_watermark_repo,
            ),
            patch("autom8_asana.AsanaClient") as mock_client_cls,
            patch("autom8_asana.dataframes.models.registry.SchemaRegistry"),
            patch("autom8_asana.dataframes.resolver.DefaultCustomFieldResolver"),
            patch("autom8_asana.cache.factory.CacheProviderFactory"),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            # Should not raise
            await _preload_dataframe_cache_progressive(app)

        # Cache should still be set ready
        from autom8_asana.api.routes.health import is_cache_ready

        assert is_cache_ready() is True

        # Stale data should still be stored (graceful fallback)
        mock_watermark_repo.set_watermark.assert_called()
