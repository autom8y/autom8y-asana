"""Tests for dataframe (struc) caching."""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from autom8_asana.cache.dataframes import (
    invalidate_struc,
    invalidate_task_strucs,
    load_batch_strucs_cached,
    load_struc_cached,
    make_struc_key,
    parse_struc_key,
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


class TestMakeStrucKey:
    """Tests for make_struc_key function."""

    def test_creates_composite_key(self) -> None:
        """Test that key combines task and project GID."""
        key = make_struc_key("task123", "project456")
        assert key == "task123:project456"

    def test_handles_empty_gids(self) -> None:
        """Test with empty GIDs."""
        key = make_struc_key("", "")
        assert key == ":"

    def test_handles_special_characters(self) -> None:
        """Test with special characters in GIDs."""
        key = make_struc_key("task-123", "project_456")
        assert key == "task-123:project_456"


class TestParseStrucKey:
    """Tests for parse_struc_key function."""

    def test_parses_valid_key(self) -> None:
        """Test parsing a valid struc key."""
        result = parse_struc_key("task123:project456")
        assert result == ("task123", "project456")

    def test_returns_none_for_invalid_key(self) -> None:
        """Test that invalid keys return None."""
        assert parse_struc_key("invalid") is None
        assert parse_struc_key("") is None

    def test_handles_multiple_colons(self) -> None:
        """Test key with multiple colons."""
        # Only split on first colon
        result = parse_struc_key("task:project:extra")
        assert result == ("task", "project:extra")

    def test_roundtrip(self) -> None:
        """Test make_struc_key -> parse_struc_key roundtrip."""
        task_gid = "task123"
        project_gid = "project456"
        key = make_struc_key(task_gid, project_gid)
        result = parse_struc_key(key)
        assert result == (task_gid, project_gid)


class TestLoadStrucCached:
    """Tests for load_struc_cached function."""

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
        struc = {"field1": "value1", "field2": 42}
        compute_fn.return_value = struc

        result, entry, was_hit = await load_struc_cached(
            task_gid="task123",
            project_gid="project456",
            cache=cache,
            compute_fn=compute_fn,
        )

        compute_fn.assert_called_once_with("task123", "project456")
        assert result == struc
        assert entry is not None
        assert not was_hit
        # Verify cached
        assert cache.get_versioned("task123:project456", EntryType.STRUC) is not None

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test that cache hit returns cached value without computing."""
        # Pre-populate cache
        cached_struc = {"cached": True}
        entry = CacheEntry(
            key="task123:project456",
            data=cached_struc,
            entry_type=EntryType.STRUC,
            version=datetime.now(timezone.utc),
            project_gid="project456",
        )
        cache._cache["struc:task123:project456"] = entry

        result, returned_entry, was_hit = await load_struc_cached(
            task_gid="task123",
            project_gid="project456",
            cache=cache,
            compute_fn=compute_fn,
        )

        compute_fn.assert_not_called()
        assert result == cached_struc
        assert was_hit

    @pytest.mark.asyncio
    async def test_stale_cache_recomputes(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test that stale cache triggers recompute."""
        # Pre-populate cache with old version
        old_version = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        entry = CacheEntry(
            key="task123:project456",
            data={"cached": True},
            entry_type=EntryType.STRUC,
            version=old_version,
            project_gid="project456",
        )
        cache._cache["struc:task123:project456"] = entry

        # Current modified_at is newer
        new_struc = {"recomputed": True}
        compute_fn.return_value = new_struc
        current_modified_at = "2025-01-01T12:00:00+00:00"

        result, _, was_hit = await load_struc_cached(
            task_gid="task123",
            project_gid="project456",
            cache=cache,
            compute_fn=compute_fn,
            current_modified_at=current_modified_at,
        )

        compute_fn.assert_called_once()
        assert result == new_struc
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
            entry_type=EntryType.STRUC,
            version=datetime.now(timezone.utc),
            project_gid="project456",
        )
        cache._cache["struc:task123:project456"] = entry

        new_struc = {"forced": True}
        compute_fn.return_value = new_struc

        result, _, was_hit = await load_struc_cached(
            task_gid="task123",
            project_gid="project456",
            cache=cache,
            compute_fn=compute_fn,
            force_refresh=True,
        )

        compute_fn.assert_called_once()
        assert result == new_struc
        assert not was_hit

    @pytest.mark.asyncio
    async def test_entry_has_project_gid(
        self, cache: MockCacheProvider, compute_fn: AsyncMock
    ) -> None:
        """Test that cache entry includes project_gid."""
        compute_fn.return_value = {"field": "value"}

        _, entry, _ = await load_struc_cached(
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

        _, entry, _ = await load_struc_cached(
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


class TestInvalidateStruc:
    """Tests for invalidate_struc function."""

    def test_invalidates_struc_entry(self) -> None:
        """Test that invalidate removes struc from cache."""
        cache = MockCacheProvider()

        # Pre-populate cache
        entry = CacheEntry(
            key="task123:project456",
            data={"field": "value"},
            entry_type=EntryType.STRUC,
            version=datetime.now(timezone.utc),
        )
        cache._cache["struc:task123:project456"] = entry

        invalidate_struc("task123", "project456", cache)

        assert cache.get_versioned("task123:project456", EntryType.STRUC) is None

    def test_invalidate_nonexistent_is_safe(self) -> None:
        """Test that invalidating nonexistent entry is safe."""
        cache = MockCacheProvider()

        # Should not raise
        invalidate_struc("nonexistent", "project", cache)


class TestInvalidateTaskStrucs:
    """Tests for invalidate_task_strucs function."""

    def test_invalidates_all_projects(self) -> None:
        """Test invalidating struc across multiple projects."""
        cache = MockCacheProvider()

        # Pre-populate cache with entries for multiple projects
        for project_gid in ["p1", "p2", "p3"]:
            entry = CacheEntry(
                key=f"task123:{project_gid}",
                data={"project": project_gid},
                entry_type=EntryType.STRUC,
                version=datetime.now(timezone.utc),
            )
            cache._cache[f"struc:task123:{project_gid}"] = entry

        invalidate_task_strucs("task123", ["p1", "p2", "p3"], cache)

        assert cache.get_versioned("task123:p1", EntryType.STRUC) is None
        assert cache.get_versioned("task123:p2", EntryType.STRUC) is None
        assert cache.get_versioned("task123:p3", EntryType.STRUC) is None

    def test_invalidates_subset_of_projects(self) -> None:
        """Test invalidating only specified projects."""
        cache = MockCacheProvider()

        # Pre-populate cache
        for project_gid in ["p1", "p2", "p3"]:
            entry = CacheEntry(
                key=f"task123:{project_gid}",
                data={"project": project_gid},
                entry_type=EntryType.STRUC,
                version=datetime.now(timezone.utc),
            )
            cache._cache[f"struc:task123:{project_gid}"] = entry

        # Only invalidate p1 and p2
        invalidate_task_strucs("task123", ["p1", "p2"], cache)

        assert cache.get_versioned("task123:p1", EntryType.STRUC) is None
        assert cache.get_versioned("task123:p2", EntryType.STRUC) is None
        # p3 should still be cached
        assert cache.get_versioned("task123:p3", EntryType.STRUC) is not None


class TestLoadBatchStrucsCached:
    """Tests for load_batch_strucs_cached function."""

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

        results = await load_batch_strucs_cached(
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
            entry_type=EntryType.STRUC,
            version=datetime.now(timezone.utc),
        )
        cache._cache["struc:task1:project1"] = entry

        pairs = [
            ("task1", "project1"),
            ("task2", "project2"),
        ]

        results = await load_batch_strucs_cached(
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
        old_version = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        entry = CacheEntry(
            key="task1:project1",
            data={"old": True},
            entry_type=EntryType.STRUC,
            version=old_version,
        )
        cache._cache["struc:task1:project1"] = entry

        pairs = [("task1", "project1")]
        modifications = {"task1": "2025-01-01T12:00:00+00:00"}  # Newer

        results = await load_batch_strucs_cached(
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
            entry_type=EntryType.STRUC,
            version=datetime.now(timezone.utc),
        )
        cache._cache["struc:task1:project1"] = entry

        pairs = [("task1", "project1")]

        results = await load_batch_strucs_cached(
            task_project_pairs=pairs,
            cache=cache,
            compute_fn=compute_fn,
            force_refresh=True,
        )

        # Should recompute despite cache hit
        assert results["task1:project1"][1] is False
        compute_fn.assert_called_once()
