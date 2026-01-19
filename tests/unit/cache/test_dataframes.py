"""Tests for dataframe caching."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from autom8_asana.cache.dataframes import (
    invalidate_dataframe,
    invalidate_task_dataframes,
    load_batch_dataframes_cached,
    load_dataframe_cached,
    make_dataframe_key,
    parse_dataframe_key,
)
from autom8_asana.cache.entry import CacheEntry, EntryType


class MockCacheProvider:
    """Mock cache provider for testing."""

    def __init__(self) -> None:
        self._cache: dict[str, CacheEntry] = {}

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: Any = None,
    ) -> CacheEntry | None:
        cache_key = f"{entry_type.value}:{key}"
        return self._cache.get(cache_key)

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        cache_key = f"{entry.entry_type.value}:{key}"
        self._cache[cache_key] = entry

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        if entry_types is None:
            entry_types = list(EntryType)
        for et in entry_types:
            cache_key = f"{et.value}:{key}"
            self._cache.pop(cache_key, None)


class TestMakeDataframeKey:
    """Tests for make_dataframe_key function."""

    def test_creates_composite_key(self) -> None:
        """Test that key combines task and project GID."""
        key = make_dataframe_key("task123", "project456")
        assert key == "task123:project456"

    def test_handles_empty_gids(self) -> None:
        """Test with empty GIDs."""
        key = make_dataframe_key("", "")
        assert key == ":"

    def test_handles_special_characters(self) -> None:
        """Test with special characters in GIDs."""
        key = make_dataframe_key("task-123", "project_456")
        assert key == "task-123:project_456"


class TestParseDataframeKey:
    """Tests for parse_dataframe_key function."""

    def test_parses_valid_key(self) -> None:
        """Test parsing a valid dataframe key."""
        result = parse_dataframe_key("task123:project456")
        assert result == ("task123", "project456")

    def test_returns_none_for_invalid_key(self) -> None:
        """Test that invalid keys return None."""
        assert parse_dataframe_key("invalid") is None
        assert parse_dataframe_key("") is None

    def test_handles_multiple_colons(self) -> None:
        """Test key with multiple colons."""
        # Only split on first colon
        result = parse_dataframe_key("task:project:extra")
        assert result == ("task", "project:extra")

    def test_roundtrip(self) -> None:
        """Test make_dataframe_key -> parse_dataframe_key roundtrip."""
        task_gid = "task123"
        project_gid = "project456"
        key = make_dataframe_key(task_gid, project_gid)
        result = parse_dataframe_key(key)
        assert result == (task_gid, project_gid)


class TestLoadDataframeCached:
    """Tests for load_dataframe_cached function."""

    @pytest.fixture
    def cache(self) -> MockCacheProvider:
        """Create a mock cache provider."""
        return MockCacheProvider()

    @pytest.fixture
    def compute_fn(self) -> AsyncMock:
        """Create a mock compute function."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_cache_miss_computes_and_caches(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test that cache miss triggers compute and caches result."""
        dataframe = {"field1": "value1", "field2": 42}
        compute_fn.return_value = dataframe

        result, entry, was_hit = await load_dataframe_cached(
            task_gid="task123",
            project_gid="project456",
            cache=cache,
            compute_fn=compute_fn,
        )

        compute_fn.assert_called_once_with("task123", "project456")
        assert result == dataframe
        assert entry is not None
        assert not was_hit
        # Verify cached
        assert (
            cache.get_versioned("task123:project456", EntryType.DATAFRAME) is not None
        )

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test that cache hit returns cached value without computing."""
        # Pre-populate cache
        cached_dataframe = {"cached": True}
        entry = CacheEntry(
            key="task123:project456",
            data=cached_dataframe,
            entry_type=EntryType.DATAFRAME,
            version=datetime.now(UTC),
            project_gid="project456",
        )
        cache._cache["dataframe:task123:project456"] = entry

        result, returned_entry, was_hit = await load_dataframe_cached(
            task_gid="task123",
            project_gid="project456",
            cache=cache,
            compute_fn=compute_fn,
        )

        compute_fn.assert_not_called()
        assert result == cached_dataframe
        assert was_hit

    @pytest.mark.asyncio
    async def test_stale_cache_recomputes(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test that stale cache triggers recompute."""
        # Pre-populate cache with old version
        old_version = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        entry = CacheEntry(
            key="task123:project456",
            data={"cached": True},
            entry_type=EntryType.DATAFRAME,
            version=old_version,
            project_gid="project456",
        )
        cache._cache["dataframe:task123:project456"] = entry

        # Current modified_at is newer
        new_dataframe = {"recomputed": True}
        compute_fn.return_value = new_dataframe
        current_modified_at = "2025-01-01T12:00:00+00:00"

        result, _, was_hit = await load_dataframe_cached(
            task_gid="task123",
            project_gid="project456",
            cache=cache,
            compute_fn=compute_fn,
            current_modified_at=current_modified_at,
        )

        compute_fn.assert_called_once()
        assert result == new_dataframe
        assert not was_hit

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test that force_refresh bypasses cache even if fresh."""
        # Pre-populate cache
        entry = CacheEntry(
            key="task123:project456",
            data={"cached": True},
            entry_type=EntryType.DATAFRAME,
            version=datetime.now(UTC),
            project_gid="project456",
        )
        cache._cache["dataframe:task123:project456"] = entry

        new_dataframe = {"forced": True}
        compute_fn.return_value = new_dataframe

        result, _, was_hit = await load_dataframe_cached(
            task_gid="task123",
            project_gid="project456",
            cache=cache,
            compute_fn=compute_fn,
            force_refresh=True,
        )

        compute_fn.assert_called_once()
        assert result == new_dataframe
        assert not was_hit

    @pytest.mark.asyncio
    async def test_entry_has_project_gid(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test that cache entry includes project_gid."""
        compute_fn.return_value = {"field": "value"}

        _, entry, _ = await load_dataframe_cached(
            task_gid="task123",
            project_gid="project456",
            cache=cache,
            compute_fn=compute_fn,
        )

        assert entry is not None
        assert entry.project_gid == "project456"

    @pytest.mark.asyncio
    async def test_version_from_modified_at(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test that entry version comes from modified_at when provided."""
        compute_fn.return_value = {"field": "value"}
        modified_at = "2025-01-15T10:30:00+00:00"

        _, entry, _ = await load_dataframe_cached(
            task_gid="task123",
            project_gid="project456",
            cache=cache,
            compute_fn=compute_fn,
            current_modified_at=modified_at,
        )

        assert entry is not None
        assert entry.version.year == 2025
        assert entry.version.month == 1
        assert entry.version.day == 15


class TestInvalidateDataframe:
    """Tests for invalidate_dataframe function."""

    def test_invalidates_dataframe_entry(self) -> None:
        """Test that invalidate removes dataframe from cache."""
        cache = MockCacheProvider()

        # Pre-populate cache
        entry = CacheEntry(
            key="task123:project456",
            data={"field": "value"},
            entry_type=EntryType.DATAFRAME,
            version=datetime.now(UTC),
        )
        cache._cache["dataframe:task123:project456"] = entry

        invalidate_dataframe("task123", "project456", cache)

        assert cache.get_versioned("task123:project456", EntryType.DATAFRAME) is None

    def test_invalidate_nonexistent_is_safe(self) -> None:
        """Test that invalidating nonexistent entry is safe."""
        cache = MockCacheProvider()

        # Should not raise
        invalidate_dataframe("nonexistent", "project", cache)


class TestInvalidateTaskDataframes:
    """Tests for invalidate_task_dataframes function."""

    def test_invalidates_all_projects(self) -> None:
        """Test invalidating dataframe across multiple projects."""
        cache = MockCacheProvider()

        # Pre-populate cache with entries for multiple projects
        for project_gid in ["p1", "p2", "p3"]:
            entry = CacheEntry(
                key=f"task123:{project_gid}",
                data={"project": project_gid},
                entry_type=EntryType.DATAFRAME,
                version=datetime.now(UTC),
            )
            cache._cache[f"dataframe:task123:{project_gid}"] = entry

        invalidate_task_dataframes("task123", ["p1", "p2", "p3"], cache)

        assert cache.get_versioned("task123:p1", EntryType.DATAFRAME) is None
        assert cache.get_versioned("task123:p2", EntryType.DATAFRAME) is None
        assert cache.get_versioned("task123:p3", EntryType.DATAFRAME) is None

    def test_invalidates_subset_of_projects(self) -> None:
        """Test invalidating only specified projects."""
        cache = MockCacheProvider()

        # Pre-populate cache
        for project_gid in ["p1", "p2", "p3"]:
            entry = CacheEntry(
                key=f"task123:{project_gid}",
                data={"project": project_gid},
                entry_type=EntryType.DATAFRAME,
                version=datetime.now(UTC),
            )
            cache._cache[f"dataframe:task123:{project_gid}"] = entry

        # Only invalidate p1 and p2
        invalidate_task_dataframes("task123", ["p1", "p2"], cache)

        assert cache.get_versioned("task123:p1", EntryType.DATAFRAME) is None
        assert cache.get_versioned("task123:p2", EntryType.DATAFRAME) is None
        # p3 should still be cached
        assert cache.get_versioned("task123:p3", EntryType.DATAFRAME) is not None


class TestLoadBatchDataframesCached:
    """Tests for load_batch_dataframes_cached function."""

    @pytest.fixture
    def cache(self) -> MockCacheProvider:
        """Create a mock cache provider."""
        return MockCacheProvider()

    @pytest.fixture
    def compute_fn(self) -> AsyncMock:
        """Create a mock compute function."""

        async def compute(task_gid: str, project_gid: str) -> dict[str, Any]:
            return {"task": task_gid, "project": project_gid}

        return AsyncMock(side_effect=compute)

    @pytest.mark.asyncio
    async def test_batch_load_all_misses(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test batch load with all cache misses."""
        pairs = [
            ("task1", "project1"),
            ("task2", "project2"),
        ]

        results = await load_batch_dataframes_cached(
            task_project_pairs=pairs,
            cache=cache,
            compute_fn=compute_fn,
        )

        assert len(results) == 2
        assert "task1:project1" in results
        assert "task2:project2" in results
        # All should be misses
        assert results["task1:project1"][1] is False
        assert results["task2:project2"][1] is False

    @pytest.mark.asyncio
    async def test_batch_load_with_hits(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test batch load with some cache hits."""
        # Pre-populate cache for task1
        entry = CacheEntry(
            key="task1:project1",
            data={"cached": True},
            entry_type=EntryType.DATAFRAME,
            version=datetime.now(UTC),
        )
        cache._cache["dataframe:task1:project1"] = entry

        pairs = [
            ("task1", "project1"),
            ("task2", "project2"),
        ]

        results = await load_batch_dataframes_cached(
            task_project_pairs=pairs,
            cache=cache,
            compute_fn=compute_fn,
        )

        # task1 should be hit (compute_fn not called for it)
        assert results["task1:project1"][1] is True
        assert results["task1:project1"][0] == {"cached": True}
        # task2 should be miss
        assert results["task2:project2"][1] is False

    @pytest.mark.asyncio
    async def test_batch_load_with_modifications(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test batch load with modification timestamps."""
        # Pre-populate cache with old version
        old_version = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        entry = CacheEntry(
            key="task1:project1",
            data={"old": True},
            entry_type=EntryType.DATAFRAME,
            version=old_version,
        )
        cache._cache["dataframe:task1:project1"] = entry

        pairs = [("task1", "project1")]
        modifications = {"task1": "2025-01-01T12:00:00+00:00"}  # Newer

        results = await load_batch_dataframes_cached(
            task_project_pairs=pairs,
            cache=cache,
            compute_fn=compute_fn,
            modifications=modifications,
        )

        # Should recompute due to staleness
        assert results["task1:project1"][1] is False

    @pytest.mark.asyncio
    async def test_batch_load_force_refresh(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test batch load with force refresh."""
        # Pre-populate cache
        entry = CacheEntry(
            key="task1:project1",
            data={"cached": True},
            entry_type=EntryType.DATAFRAME,
            version=datetime.now(UTC),
        )
        cache._cache["dataframe:task1:project1"] = entry

        pairs = [("task1", "project1")]

        results = await load_batch_dataframes_cached(
            task_project_pairs=pairs,
            cache=cache,
            compute_fn=compute_fn,
            force_refresh=True,
        )

        # Should recompute despite cache hit
        assert results["task1:project1"][1] is False
        compute_fn.assert_called_once()
