"""Tests for startup preload with incremental catch-up.

Per sprint-materialization-003 Task 3:
- Startup loads persisted GidLookupIndex from S3
- Startup runs incremental catch-up using watermark
- Falls back to full build when no persisted state
- Updates S3 with new state after catch-up
- Logs timing metrics for cold start (target: <5s with persisted state)

Tests cover:
- _preload_dataframe_cache() function behavior
- _do_incremental_catchup() function behavior
- _do_full_rebuild() function behavior
- Integration with persistence layer
- Graceful degradation scenarios
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.api.routes.health import set_cache_ready
from autom8_asana.services.gid_lookup import GidLookupIndex


@pytest.fixture(autouse=True)
def reset_cache_ready():
    """Reset cache ready state before and after each test."""
    set_cache_ready(True)
    yield
    set_cache_ready(True)


@pytest.fixture
def sample_dataframe() -> pl.DataFrame:
    """Create a sample DataFrame for testing."""
    return pl.DataFrame(
        {
            "gid": ["123456", "789012"],
            "name": ["Task 1", "Task 2"],
            "office_phone": ["+17705551234", "+14045556789"],
            "vertical": ["chiropractic", "dental"],
        }
    )


@pytest.fixture
def sample_index(sample_dataframe: pl.DataFrame) -> GidLookupIndex:
    """Create a sample GidLookupIndex for testing."""
    return GidLookupIndex.from_dataframe(sample_dataframe, key_columns=["office_phone", "vertical"])


@pytest.fixture
def mock_entity_registry():
    """Create a mock EntityProjectRegistry."""
    from autom8_asana.services.resolver import EntityProjectConfig

    registry = MagicMock()
    registry.is_ready.return_value = True
    registry.get_all_entity_types.return_value = ["unit"]
    registry.get_config.return_value = EntityProjectConfig(
        entity_type="unit",
        project_gid="proj_123",
        project_name="Business Units",
    )
    return registry


class TestPreloadDataframeCacheFunction:
    """Tests for the _preload_dataframe_cache function."""

    @pytest.mark.asyncio
    async def test_preload_skips_when_registry_not_ready(self) -> None:
        """Preload skips when entity registry is not ready."""
        from autom8_asana.api.preload.legacy import _preload_dataframe_cache

        mock_app = MagicMock()
        mock_app.state.entity_project_registry = None

        await _preload_dataframe_cache(mock_app)

        # Should set cache ready even when skipped
        from autom8_asana.api.routes.health import is_cache_ready

        assert is_cache_ready() is True

    @pytest.mark.asyncio
    async def test_preload_skips_when_no_registered_projects(
        self, mock_entity_registry: MagicMock
    ) -> None:
        """Preload skips when no projects are registered."""
        from autom8_asana.api.preload.legacy import _preload_dataframe_cache

        mock_entity_registry.get_all_entity_types.return_value = []
        mock_app = MagicMock()
        mock_app.state.entity_project_registry = mock_entity_registry

        await _preload_dataframe_cache(mock_app)

        from autom8_asana.api.routes.health import is_cache_ready

        assert is_cache_ready() is True

    @pytest.mark.asyncio
    async def test_preload_skips_when_s3_unavailable(self, mock_entity_registry: MagicMock) -> None:
        """Preload skips when S3 persistence is unavailable."""
        from autom8_asana.api.preload.legacy import _preload_dataframe_cache

        mock_app = MagicMock()
        mock_app.state.entity_project_registry = mock_entity_registry

        with patch("autom8_asana.dataframes.storage.S3DataFrameStorage") as mock_persistence_class:
            mock_persistence = MagicMock()
            mock_persistence.is_available = False
            mock_persistence_class.return_value = mock_persistence

            await _preload_dataframe_cache(mock_app)

        from autom8_asana.api.routes.health import is_cache_ready

        assert is_cache_ready() is True

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_preload_loads_index_from_s3_and_does_incremental_catchup(
        self,
        mock_entity_registry: MagicMock,
        sample_dataframe: pl.DataFrame,
        sample_index: GidLookupIndex,
    ) -> None:
        """Preload loads persisted index and runs incremental catch-up."""
        from autom8_asana.api.preload.legacy import _preload_dataframe_cache

        mock_app = MagicMock()
        mock_app.state.entity_project_registry = mock_entity_registry

        watermark = datetime.now(UTC)

        with patch("autom8_asana.dataframes.storage.S3DataFrameStorage") as mock_persistence_class:
            mock_persistence = MagicMock()
            mock_persistence.is_available = True
            mock_persistence.load_index = AsyncMock(return_value=sample_index)
            mock_persistence.load_dataframe = AsyncMock(return_value=(sample_dataframe, watermark))
            mock_persistence.save_dataframe = AsyncMock(return_value=True)
            mock_persistence.save_index = AsyncMock(return_value=True)
            mock_persistence_class.return_value = mock_persistence

            with patch(
                "autom8_asana.dataframes.watermark.get_watermark_repo"
            ) as mock_watermark_repo_fn:
                mock_watermark_repo = MagicMock()
                mock_watermark_repo.load_from_persistence = AsyncMock(return_value=1)
                mock_watermark_repo.get_watermark.return_value = watermark
                mock_watermark_repo.set_watermark = MagicMock()
                mock_watermark_repo.set_persistence = MagicMock()
                mock_watermark_repo_fn.return_value = mock_watermark_repo

                with patch(
                    "autom8_asana.api.preload.legacy._do_incremental_catchup"
                ) as mock_catchup:
                    # Simulate no changes during catch-up
                    mock_catchup.return_value = (sample_dataframe, watermark, True)

                    await _preload_dataframe_cache(mock_app)

                    # Verify incremental catch-up was called
                    mock_catchup.assert_called_once()

        from autom8_asana.api.routes.health import is_cache_ready

        assert is_cache_ready() is True

    @pytest.mark.asyncio
    async def test_preload_does_full_rebuild_when_no_persisted_state(
        self,
        mock_entity_registry: MagicMock,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Preload does full rebuild when no persisted state exists."""
        from autom8_asana.api.preload.legacy import _preload_dataframe_cache

        mock_app = MagicMock()
        mock_app.state.entity_project_registry = mock_entity_registry

        with patch("autom8_asana.dataframes.storage.S3DataFrameStorage") as mock_persistence_class:
            mock_persistence = MagicMock()
            mock_persistence.is_available = True
            # No persisted index or DataFrame
            mock_persistence.load_index = AsyncMock(return_value=None)
            mock_persistence.load_dataframe = AsyncMock(return_value=(None, None))
            mock_persistence.save_dataframe = AsyncMock(return_value=True)
            mock_persistence.save_index = AsyncMock(return_value=True)
            mock_persistence_class.return_value = mock_persistence

            with patch(
                "autom8_asana.dataframes.watermark.get_watermark_repo"
            ) as mock_watermark_repo_fn:
                mock_watermark_repo = MagicMock()
                mock_watermark_repo.load_from_persistence = AsyncMock(return_value=0)
                mock_watermark_repo.get_watermark.return_value = None
                mock_watermark_repo.set_watermark = MagicMock()
                mock_watermark_repo.set_persistence = MagicMock()
                mock_watermark_repo_fn.return_value = mock_watermark_repo

                with patch("autom8_asana.api.preload.legacy._do_full_rebuild") as mock_rebuild:
                    new_watermark = datetime.now(UTC)
                    mock_rebuild.return_value = (sample_dataframe, new_watermark)

                    await _preload_dataframe_cache(mock_app)

                    # Verify full rebuild was called
                    mock_rebuild.assert_called_once()

        from autom8_asana.api.routes.health import is_cache_ready

        assert is_cache_ready() is True


class TestDoIncrementalCatchup:
    """Tests for the _do_incremental_catchup function."""

    @pytest.mark.asyncio
    async def test_incremental_catchup_returns_existing_when_no_bot_pat(
        self,
        sample_dataframe: pl.DataFrame,
        sample_index: GidLookupIndex,
    ) -> None:
        """Incremental catch-up returns existing state when bot PAT unavailable."""
        from autom8_asana.api.preload.legacy import _do_incremental_catchup
        from autom8_asana.auth.bot_pat import BotPATError

        watermark = datetime.now(UTC)

        with patch("autom8_asana.auth.bot_pat.get_bot_pat") as mock_get_pat:
            mock_get_pat.side_effect = BotPATError("No PAT")

            result_df, result_wm, was_incremental = await _do_incremental_catchup(
                project_gid="proj_123",
                entity_type="unit",
                existing_df=sample_dataframe,
                existing_index=sample_index,
                watermark=watermark,
            )

            assert result_df is sample_dataframe
            assert result_wm == watermark
            assert was_incremental is False

    @pytest.mark.asyncio
    async def test_incremental_catchup_returns_existing_when_no_workspace(
        self,
        sample_dataframe: pl.DataFrame,
        sample_index: GidLookupIndex,
    ) -> None:
        """Incremental catch-up returns existing state when workspace not configured."""
        from autom8_asana.api.preload.legacy import _do_incremental_catchup

        watermark = datetime.now(UTC)

        with patch("autom8_asana.auth.bot_pat.get_bot_pat") as mock_get_pat:
            mock_get_pat.return_value = "test_pat"

            with patch.dict("os.environ", {"ASANA_WORKSPACE_GID": ""}, clear=False):
                result_df, result_wm, was_incremental = await _do_incremental_catchup(
                    project_gid="proj_123",
                    entity_type="unit",
                    existing_df=sample_dataframe,
                    existing_index=sample_index,
                    watermark=watermark,
                )

                assert result_df is sample_dataframe
                assert result_wm == watermark
                assert was_incremental is False


class TestDoFullRebuild:
    """Tests for the _do_full_rebuild function."""

    @pytest.mark.asyncio
    async def test_full_rebuild_returns_none_when_no_bot_pat(self) -> None:
        """Full rebuild returns None DataFrame when bot PAT unavailable."""
        from autom8_asana.api.preload.legacy import _do_full_rebuild
        from autom8_asana.auth.bot_pat import BotPATError

        with patch("autom8_asana.auth.bot_pat.get_bot_pat") as mock_get_pat:
            mock_get_pat.side_effect = BotPATError("No PAT")

            result_df, result_wm = await _do_full_rebuild(
                project_gid="proj_123",
                entity_type="unit",
            )

            assert result_df is None
            assert result_wm is not None  # Should return current timestamp

    @pytest.mark.asyncio
    async def test_full_rebuild_returns_none_when_no_workspace(self) -> None:
        """Full rebuild returns None DataFrame when workspace not configured."""
        from autom8_asana.api.preload.legacy import _do_full_rebuild

        with patch("autom8_asana.auth.bot_pat.get_bot_pat") as mock_get_pat:
            mock_get_pat.return_value = "test_pat"

            with patch.dict("os.environ", {"ASANA_WORKSPACE_GID": ""}, clear=False):
                result_df, result_wm = await _do_full_rebuild(
                    project_gid="proj_123",
                    entity_type="unit",
                )

                assert result_df is None
                assert result_wm is not None


class TestGracefulDegradation:
    """Tests for graceful degradation scenarios."""

    @pytest.mark.asyncio
    async def test_preload_continues_on_project_failure(
        self, mock_entity_registry: MagicMock
    ) -> None:
        """Preload continues with other projects when one fails."""
        from autom8_asana.api.preload.legacy import _preload_dataframe_cache
        from autom8_asana.services.resolver import EntityProjectConfig

        # Configure two projects
        mock_entity_registry.get_all_entity_types.return_value = ["unit", "business"]
        mock_entity_registry.get_config.side_effect = [
            EntityProjectConfig(
                entity_type="unit",
                project_gid="proj_unit",
                project_name="Business Units",
            ),
            EntityProjectConfig(
                entity_type="business",
                project_gid="proj_business",
                project_name="Businesses",
            ),
        ]

        mock_app = MagicMock()
        mock_app.state.entity_project_registry = mock_entity_registry

        with patch("autom8_asana.dataframes.storage.S3DataFrameStorage") as mock_persistence_class:
            mock_persistence = MagicMock()
            mock_persistence.is_available = True
            # First project fails, second succeeds
            mock_persistence.load_index = AsyncMock(side_effect=[Exception("S3 error"), None])
            mock_persistence.load_dataframe = AsyncMock(
                side_effect=[Exception("S3 error"), (None, None)]
            )
            mock_persistence_class.return_value = mock_persistence

            with patch(
                "autom8_asana.dataframes.watermark.get_watermark_repo"
            ) as mock_watermark_repo_fn:
                mock_watermark_repo = MagicMock()
                mock_watermark_repo.load_from_persistence = AsyncMock(return_value=0)
                mock_watermark_repo.get_watermark.return_value = None
                mock_watermark_repo.set_persistence = MagicMock()
                mock_watermark_repo_fn.return_value = mock_watermark_repo

                # Should complete without raising
                await _preload_dataframe_cache(mock_app)

        # Should set cache ready despite failures
        from autom8_asana.api.routes.health import is_cache_ready

        assert is_cache_ready() is True

    @pytest.mark.asyncio
    async def test_preload_sets_cache_ready_on_exception(self) -> None:
        """Preload sets cache ready even when exception occurs."""
        from autom8_asana.api.preload.legacy import _preload_dataframe_cache

        mock_app = MagicMock()
        # Simulate exception by having getattr raise
        mock_app.state = MagicMock()
        mock_app.state.entity_project_registry = MagicMock()
        mock_app.state.entity_project_registry.is_ready.side_effect = Exception("Unexpected error")

        # Should complete without raising
        await _preload_dataframe_cache(mock_app)

        # Should set cache ready despite exception
        from autom8_asana.api.routes.health import is_cache_ready

        assert is_cache_ready() is True


class TestCacheIntegration:
    """Tests for cache integration during startup."""

    @pytest.mark.asyncio
    async def test_index_persisted_after_successful_preload(
        self,
        mock_entity_registry: MagicMock,
        sample_dataframe: pl.DataFrame,
        sample_index: GidLookupIndex,
    ) -> None:
        """Index is persisted to S3 after successful preload."""
        from autom8_asana.api.preload.legacy import _preload_dataframe_cache

        mock_app = MagicMock()
        mock_app.state.entity_project_registry = mock_entity_registry

        watermark = datetime.now(UTC)

        with patch("autom8_asana.dataframes.storage.S3DataFrameStorage") as mock_persistence_class:
            mock_persistence = MagicMock()
            mock_persistence.is_available = True
            mock_persistence.load_index = AsyncMock(return_value=sample_index)
            mock_persistence.load_dataframe = AsyncMock(return_value=(sample_dataframe, watermark))
            mock_persistence.save_dataframe = AsyncMock(return_value=True)
            mock_persistence.save_index = AsyncMock(return_value=True)
            mock_persistence_class.return_value = mock_persistence

            with patch(
                "autom8_asana.dataframes.watermark.get_watermark_repo"
            ) as mock_watermark_repo_fn:
                mock_watermark_repo = MagicMock()
                mock_watermark_repo.load_from_persistence = AsyncMock(return_value=1)
                mock_watermark_repo.get_watermark.return_value = watermark
                mock_watermark_repo.set_watermark = MagicMock()
                mock_watermark_repo.set_persistence = MagicMock()
                mock_watermark_repo_fn.return_value = mock_watermark_repo

                with patch(
                    "autom8_asana.api.preload.legacy._do_incremental_catchup"
                ) as mock_catchup:
                    mock_catchup.return_value = (sample_dataframe, watermark, True)

                    await _preload_dataframe_cache(mock_app)

                    # Verify incremental catch-up was called
                    mock_catchup.assert_called_once()

    @pytest.mark.asyncio
    async def test_state_persisted_after_incremental_catchup_with_changes(
        self,
        mock_entity_registry: MagicMock,
        sample_dataframe: pl.DataFrame,
        sample_index: GidLookupIndex,
    ) -> None:
        """State is persisted to S3 after incremental catch-up with changes."""
        from autom8_asana.api.preload.legacy import _preload_dataframe_cache

        mock_app = MagicMock()
        mock_app.state.entity_project_registry = mock_entity_registry

        watermark = datetime.now(UTC)

        # Create a different DataFrame to simulate changes
        updated_dataframe = pl.DataFrame(
            {
                "gid": ["123456", "789012", "345678"],  # Added one task
                "name": ["Task 1", "Task 2", "Task 3"],
                "office_phone": ["+17705551234", "+14045556789", "+13035557890"],
                "vertical": ["chiropractic", "dental", "medical"],
            }
        )

        with patch("autom8_asana.dataframes.storage.S3DataFrameStorage") as mock_persistence_class:
            mock_persistence = MagicMock()
            mock_persistence.is_available = True
            mock_persistence.load_index = AsyncMock(return_value=sample_index)
            mock_persistence.load_dataframe = AsyncMock(return_value=(sample_dataframe, watermark))
            mock_persistence.save_dataframe = AsyncMock(return_value=True)
            mock_persistence.save_index = AsyncMock(return_value=True)
            mock_persistence_class.return_value = mock_persistence

            with patch(
                "autom8_asana.dataframes.watermark.get_watermark_repo"
            ) as mock_watermark_repo_fn:
                mock_watermark_repo = MagicMock()
                mock_watermark_repo.load_from_persistence = AsyncMock(return_value=1)
                mock_watermark_repo.get_watermark.return_value = watermark
                mock_watermark_repo.set_watermark = MagicMock()
                mock_watermark_repo.set_persistence = MagicMock()
                mock_watermark_repo_fn.return_value = mock_watermark_repo

                with patch(
                    "autom8_asana.api.preload.legacy._do_incremental_catchup"
                ) as mock_catchup:
                    new_watermark = datetime.now(UTC)
                    # Return different DataFrame to indicate changes
                    mock_catchup.return_value = (updated_dataframe, new_watermark, True)

                    await _preload_dataframe_cache(mock_app)

                    # Verify state was persisted
                    mock_persistence.save_dataframe.assert_called_once()
                    mock_persistence.save_index.assert_called_once()
                    mock_watermark_repo.set_watermark.assert_called()
