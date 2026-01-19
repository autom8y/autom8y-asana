"""Unit tests for CacheWarmer.

Per TDD-DATAFRAME-CACHE-001: Tests for priority-based pre-warming
for Lambda deployment.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.cache.dataframe.warmer import (
    CacheWarmer,
    WarmResult,
    WarmStatus,
)


class TestWarmStatus:
    """Tests for WarmStatus dataclass."""

    def test_create_success_status(self) -> None:
        """Create a success status with all fields."""
        status = WarmStatus(
            entity_type="unit",
            result=WarmResult.SUCCESS,
            project_gid="1234567890",
            row_count=5000,
            duration_ms=2500.0,
        )

        assert status.entity_type == "unit"
        assert status.result == WarmResult.SUCCESS
        assert status.project_gid == "1234567890"
        assert status.row_count == 5000
        assert status.duration_ms == 2500.0
        assert status.error is None

    def test_create_failure_status(self) -> None:
        """Create a failure status with error message."""
        status = WarmStatus(
            entity_type="offer",
            result=WarmResult.FAILURE,
            project_gid="9876543210",
            error="Connection timeout",
        )

        assert status.entity_type == "offer"
        assert status.result == WarmResult.FAILURE
        assert status.error == "Connection timeout"
        assert status.row_count == 0

    def test_create_skipped_status(self) -> None:
        """Create a skipped status."""
        status = WarmStatus(
            entity_type="contact",
            result=WarmResult.SKIPPED,
            error="No project GID configured",
        )

        assert status.result == WarmResult.SKIPPED
        assert status.project_gid is None

    def test_to_dict(self) -> None:
        """Convert status to dictionary for JSON serialization."""
        status = WarmStatus(
            entity_type="unit",
            result=WarmResult.SUCCESS,
            project_gid="1234567890",
            row_count=5000,
            duration_ms=2500.0,
        )

        result = status.to_dict()

        assert result["entity_type"] == "unit"
        assert result["result"] == "success"
        assert result["project_gid"] == "1234567890"
        assert result["row_count"] == 5000
        assert result["duration_ms"] == 2500.0
        assert result["error"] is None


class TestWarmResult:
    """Tests for WarmResult enum."""

    def test_success_value(self) -> None:
        """SUCCESS has correct string value."""
        assert WarmResult.SUCCESS.value == "success"

    def test_failure_value(self) -> None:
        """FAILURE has correct string value."""
        assert WarmResult.FAILURE.value == "failure"

    def test_skipped_value(self) -> None:
        """SKIPPED has correct string value."""
        assert WarmResult.SKIPPED.value == "skipped"


class TestCacheWarmer:
    """Tests for CacheWarmer class."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create a mock DataFrameCache."""
        cache = MagicMock()
        cache.put_async = AsyncMock()
        return cache

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock AsanaClient."""
        return MagicMock()

    @pytest.fixture
    def sample_dataframe(self) -> pl.DataFrame:
        """Create a sample DataFrame for testing."""
        return pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["Task A", "Task B", "Task C"],
            }
        )

    def test_default_priority(self, mock_cache: MagicMock) -> None:
        """Default priority includes core entity types in expected order."""
        warmer = CacheWarmer(cache=mock_cache)

        # Core entity types must be present (don't hardcode full list)
        assert "offer" in warmer.priority
        assert "unit" in warmer.priority
        assert "business" in warmer.priority
        assert "contact" in warmer.priority

        # Offer should be first (highest priority)
        assert warmer.priority[0] == "offer"

        # Priority list should not be empty
        assert len(warmer.priority) >= 4

    def test_custom_priority(self, mock_cache: MagicMock) -> None:
        """Custom priority can be specified."""
        warmer = CacheWarmer(
            cache=mock_cache,
            priority=["unit", "offer"],
        )

        assert warmer.priority == ["unit", "offer"]

    def test_strict_mode_default(self, mock_cache: MagicMock) -> None:
        """Strict mode is enabled by default."""
        warmer = CacheWarmer(cache=mock_cache)

        assert warmer.strict is True

    def test_non_strict_mode(self, mock_cache: MagicMock) -> None:
        """Strict mode can be disabled."""
        warmer = CacheWarmer(cache=mock_cache, strict=False)

        assert warmer.strict is False

    def test_initial_stats(self, mock_cache: MagicMock) -> None:
        """Statistics are initialized to zero."""
        warmer = CacheWarmer(cache=mock_cache)
        stats = warmer.get_stats()

        assert stats["warm_attempts"] == 0
        assert stats["warm_successes"] == 0
        assert stats["warm_failures"] == 0
        assert stats["warm_skipped"] == 0
        assert stats["total_rows_warmed"] == 0

    @pytest.mark.asyncio
    async def test_warm_all_skipped_no_project(
        self,
        mock_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """All entity types skipped when no project GIDs configured."""
        warmer = CacheWarmer(
            cache=mock_cache,
            priority=["unit"],
            strict=False,
        )

        # Provider returns None for all entity types
        results = await warmer.warm_all_async(
            client=mock_client,
            project_gid_provider=lambda et: None,
        )

        assert len(results) == 1
        assert results[0].entity_type == "unit"
        assert results[0].result == WarmResult.SKIPPED
        assert results[0].error == "No project GID configured"

    @pytest.mark.asyncio
    async def test_warm_all_success(
        self,
        mock_cache: MagicMock,
        mock_client: MagicMock,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Successful warming of all entity types."""
        warmer = CacheWarmer(
            cache=mock_cache,
            priority=["unit"],
        )

        # Mock the strategy
        mock_strategy = MagicMock()
        mock_strategy._build_dataframe = AsyncMock(
            return_value=(sample_dataframe, datetime.now(UTC))
        )

        with patch.object(
            warmer,
            "_get_strategy_instance",
            return_value=mock_strategy,
        ):
            results = await warmer.warm_all_async(
                client=mock_client,
                project_gid_provider=lambda et: "project-123",
            )

        assert len(results) == 1
        assert results[0].result == WarmResult.SUCCESS
        assert results[0].row_count == 3
        assert results[0].project_gid == "project-123"

        # Verify cache.put_async was called
        mock_cache.put_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_warm_all_failure_strict_mode(
        self,
        mock_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """Failure in strict mode raises RuntimeError."""
        warmer = CacheWarmer(
            cache=mock_cache,
            priority=["unit", "offer"],
            strict=True,
        )

        # Mock strategy that fails
        mock_strategy = MagicMock()
        mock_strategy._build_dataframe = AsyncMock(
            side_effect=Exception("Build failed")
        )

        with patch.object(
            warmer,
            "_get_strategy_instance",
            return_value=mock_strategy,
        ):
            with pytest.raises(RuntimeError) as exc_info:
                await warmer.warm_all_async(
                    client=mock_client,
                    project_gid_provider=lambda et: "project-123",
                )

        assert "Cache warm failed for unit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_warm_all_failure_non_strict_mode(
        self,
        mock_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """Failure in non-strict mode continues to next entity type."""
        warmer = CacheWarmer(
            cache=mock_cache,
            priority=["unit", "offer"],
            strict=False,
        )

        # Mock strategy that fails for unit but succeeds for offer
        call_count = 0

        async def build_side_effect(project_gid: str, client: Any) -> tuple:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Build failed")
            return (
                pl.DataFrame({"gid": ["1"], "name": ["Task"]}),
                datetime.now(UTC),
            )

        mock_strategy = MagicMock()
        mock_strategy._build_dataframe = AsyncMock(side_effect=build_side_effect)

        with patch.object(
            warmer,
            "_get_strategy_instance",
            return_value=mock_strategy,
        ):
            results = await warmer.warm_all_async(
                client=mock_client,
                project_gid_provider=lambda et: "project-123",
            )

        assert len(results) == 2
        assert results[0].result == WarmResult.FAILURE
        assert results[1].result == WarmResult.SUCCESS

    @pytest.mark.asyncio
    async def test_warm_entity_single(
        self,
        mock_cache: MagicMock,
        mock_client: MagicMock,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Warm a single entity type."""
        warmer = CacheWarmer(cache=mock_cache)

        mock_strategy = MagicMock()
        mock_strategy._build_dataframe = AsyncMock(
            return_value=(sample_dataframe, datetime.now(UTC))
        )

        with patch.object(
            warmer,
            "_get_strategy_instance",
            return_value=mock_strategy,
        ):
            status = await warmer.warm_entity_async(
                entity_type="unit",
                client=mock_client,
                project_gid_provider=lambda et: "project-123",
            )

        assert status.result == WarmResult.SUCCESS
        assert status.entity_type == "unit"
        assert status.row_count == 3

    @pytest.mark.asyncio
    async def test_warm_entity_no_project(
        self,
        mock_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """Warm entity returns SKIPPED when no project configured."""
        warmer = CacheWarmer(cache=mock_cache)

        status = await warmer.warm_entity_async(
            entity_type="unit",
            client=mock_client,
            project_gid_provider=lambda et: None,
        )

        assert status.result == WarmResult.SKIPPED
        assert status.error == "No project GID configured"

    def test_get_strategy_instance_unit(self, mock_cache: MagicMock) -> None:
        """Get UniversalResolutionStrategy instance for unit entity type."""
        warmer = CacheWarmer(cache=mock_cache)

        # Mock is_entity_resolvable to return True for unit
        with patch(
            "autom8_asana.services.resolver.is_entity_resolvable",
            return_value=True,
        ):
            strategy = warmer._get_strategy_instance("unit")

        # Should return a valid strategy
        assert strategy is not None
        # Strategy should be for the unit entity type
        assert strategy.entity_type == "unit"

    def test_get_strategy_instance_unknown(self, mock_cache: MagicMock) -> None:
        """Get None for unknown entity type."""
        warmer = CacheWarmer(cache=mock_cache)

        strategy = warmer._get_strategy_instance("unknown")

        assert strategy is None

    @pytest.mark.asyncio
    async def test_warm_all_no_strategy(
        self,
        mock_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """Handle missing strategy gracefully."""
        warmer = CacheWarmer(
            cache=mock_cache,
            priority=["unit"],
            strict=False,
        )

        with patch.object(
            warmer,
            "_get_strategy_instance",
            return_value=None,
        ):
            results = await warmer.warm_all_async(
                client=mock_client,
                project_gid_provider=lambda et: "project-123",
            )

        assert len(results) == 1
        assert results[0].result == WarmResult.FAILURE
        assert "No resolution strategy registered" in results[0].error

    @pytest.mark.asyncio
    async def test_warm_all_no_build_method(
        self,
        mock_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """Handle strategy without _build_dataframe method."""
        warmer = CacheWarmer(
            cache=mock_cache,
            priority=["unit"],
            strict=False,
        )

        # Strategy without _build_dataframe
        mock_strategy = MagicMock(spec=[])

        with patch.object(
            warmer,
            "_get_strategy_instance",
            return_value=mock_strategy,
        ):
            results = await warmer.warm_all_async(
                client=mock_client,
                project_gid_provider=lambda et: "project-123",
            )

        assert len(results) == 1
        assert results[0].result == WarmResult.FAILURE
        assert "no _build_dataframe method" in results[0].error

    @pytest.mark.asyncio
    async def test_warm_all_dataframe_returns_none(
        self,
        mock_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """Handle strategy that returns None DataFrame."""
        warmer = CacheWarmer(
            cache=mock_cache,
            priority=["unit"],
            strict=False,
        )

        mock_strategy = MagicMock()
        mock_strategy._build_dataframe = AsyncMock(
            return_value=(None, datetime.now(UTC))
        )

        with patch.object(
            warmer,
            "_get_strategy_instance",
            return_value=mock_strategy,
        ):
            results = await warmer.warm_all_async(
                client=mock_client,
                project_gid_provider=lambda et: "project-123",
            )

        assert len(results) == 1
        assert results[0].result == WarmResult.FAILURE
        assert "DataFrame build returned None" in results[0].error

    def test_stats_reset(self, mock_cache: MagicMock) -> None:
        """Reset statistics to zero."""
        warmer = CacheWarmer(cache=mock_cache)

        # Manually set some stats
        warmer._stats["warm_attempts"] = 10
        warmer._stats["warm_successes"] = 5

        warmer.reset_stats()
        stats = warmer.get_stats()

        assert stats["warm_attempts"] == 0
        assert stats["warm_successes"] == 0

    @pytest.mark.asyncio
    async def test_warm_all_updates_stats(
        self,
        mock_cache: MagicMock,
        mock_client: MagicMock,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Warming updates statistics correctly."""
        warmer = CacheWarmer(
            cache=mock_cache,
            priority=["unit", "offer"],
            strict=False,
        )

        # First succeeds, second fails
        call_count = 0

        async def build_side_effect(project_gid: str, client: Any) -> tuple:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Build failed")
            return (sample_dataframe, datetime.now(UTC))

        mock_strategy = MagicMock()
        mock_strategy._build_dataframe = AsyncMock(side_effect=build_side_effect)

        with patch.object(
            warmer,
            "_get_strategy_instance",
            return_value=mock_strategy,
        ):
            await warmer.warm_all_async(
                client=mock_client,
                project_gid_provider=lambda et: "project-123",
            )

        stats = warmer.get_stats()
        assert stats["warm_attempts"] == 2
        assert stats["warm_successes"] == 1
        assert stats["warm_failures"] == 1
        assert stats["total_rows_warmed"] == 3
