"""Unit tests for DataFrameCache stats initialization and _ensure_stats.

Verifies that asset_edit is included in stats and that unknown entity types
get lazily initialized, preventing KeyError on stats access.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
from autom8_asana.cache.dataframe_cache import DataFrameCache


def _make_cache() -> DataFrameCache:
    progressive_tier = MagicMock()
    progressive_tier.get_async = AsyncMock(return_value=None)
    return DataFrameCache(
        memory_tier=MemoryTier(max_entries=100),
        progressive_tier=progressive_tier,
        coalescer=DataFrameCacheCoalescer(),
        circuit_breaker=CircuitBreaker(),
    )


class TestDataFrameCacheStats:
    """Tests for stats initialization including asset_edit."""

    def test_stats_includes_asset_edit(self) -> None:
        """asset_edit should be in _stats after __post_init__."""
        cache = _make_cache()
        assert "asset_edit" in cache._stats
        assert cache._stats["asset_edit"]["invalidations"] == 0

    def test_stats_includes_all_known_types(self) -> None:
        """All 5 known entity types should have stats initialized."""
        cache = _make_cache()
        expected = {"unit", "business", "offer", "contact", "asset_edit"}
        assert expected.issubset(set(cache._stats.keys()))

    def test_ensure_stats_lazy_init(self) -> None:
        """_ensure_stats should initialize stats for unknown entity types."""
        cache = _make_cache()
        assert "new_type" not in cache._stats
        cache._ensure_stats("new_type")
        assert "new_type" in cache._stats
        assert cache._stats["new_type"]["memory_hits"] == 0
        assert cache._stats["new_type"]["invalidations"] == 0

    def test_ensure_stats_idempotent(self) -> None:
        """_ensure_stats should not reset existing stats."""
        cache = _make_cache()
        cache._stats["unit"]["memory_hits"] = 42
        cache._ensure_stats("unit")
        assert cache._stats["unit"]["memory_hits"] == 42

    def test_invalidate_asset_edit_no_keyerror(self) -> None:
        """invalidate() for asset_edit should not raise KeyError."""
        cache = _make_cache()
        # Should not raise
        cache.invalidate("proj-123", "asset_edit")
        assert cache._stats["asset_edit"]["invalidations"] == 1

    def test_invalidate_all_includes_asset_edit(self) -> None:
        """invalidate(project_gid, None) should cover all 5 types including asset_edit."""
        cache = _make_cache()
        cache.invalidate("proj-123", None)
        assert cache._stats["asset_edit"]["invalidations"] == 1
        assert cache._stats["unit"]["invalidations"] == 1
        assert cache._stats["business"]["invalidations"] == 1
        assert cache._stats["offer"]["invalidations"] == 1
        assert cache._stats["contact"]["invalidations"] == 1

    @pytest.mark.asyncio
    async def test_get_async_unknown_type_no_keyerror(self) -> None:
        """get_async with unknown entity type should not raise KeyError on stats."""
        cache = _make_cache()
        # Circuit breaker not open, so it will proceed to stats access
        result = await cache.get_async("proj-123", "unknown_type")
        assert result is None
        assert "unknown_type" in cache._stats

    @pytest.mark.asyncio
    async def test_acquire_build_lock_unknown_type_no_keyerror(self) -> None:
        """acquire_build_lock_async with unknown type should not raise KeyError."""
        cache = _make_cache()
        acquired = await cache.acquire_build_lock_async("proj-123", "unknown_type")
        assert acquired is True
        assert cache._stats["unknown_type"]["builds_triggered"] == 1
