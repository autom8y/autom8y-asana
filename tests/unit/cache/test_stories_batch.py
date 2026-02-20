"""Tests for pure-read story cache and batch story reads.

Per TDD-SECTION-TIMELINE-REMEDIATION: Tests for Gap 1 and Gap 4 primitives:
- read_cached_stories() hit returns list, miss returns None
- read_stories_batch() with empty input
- read_stories_batch() chunking (>500 keys)
- read_stories_batch() with mix of hits and misses
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from autom8y_cache.testing import MockCacheProvider as _SDKMockCacheProvider

from autom8_asana.cache.integration.stories import (
    read_cached_stories,
    read_stories_batch,
)
from autom8_asana.cache.models.entry import CacheEntry, EntryType


# ---------------------------------------------------------------------------
# Mock Cache Provider with get_batch support
# ---------------------------------------------------------------------------


class MockCacheProvider(_SDKMockCacheProvider):
    """Mock cache provider for story batch tests.

    Extends SDK MockCacheProvider with EntryType composite keys and
    get_batch() support for testing batch reads.
    """

    @property
    def _cache(self) -> dict[str, CacheEntry]:
        return self._versioned_store  # type: ignore[return-value]

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: object = None,
    ) -> CacheEntry | None:
        self.calls.append(
            (
                "get_versioned",
                {"key": key, "entry_type": entry_type, "freshness": freshness},
            )
        )
        cache_key = f"{entry_type.value}:{key}"
        return self._versioned_store.get(cache_key)

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        self.calls.append(("set_versioned", {"key": key, "entry": entry}))
        cache_key = f"{entry.entry_type.value}:{key}"
        self._versioned_store[cache_key] = entry

    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        """Batch get using individual lookups."""
        self.calls.append(
            ("get_batch", {"keys": keys, "entry_type": entry_type})
        )
        result: dict[str, CacheEntry | None] = {}
        for key in keys:
            cache_key = f"{entry_type.value}:{key}"
            result[key] = self._versioned_store.get(cache_key)
        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_story_entry(
    task_gid: str,
    stories: list[dict[str, Any]],
) -> CacheEntry:
    """Create a CacheEntry with stories data."""
    now = datetime.now(UTC)
    return CacheEntry(
        key=task_gid,
        data={"stories": stories},
        entry_type=EntryType.STORIES,
        version=now,
        cached_at=now,
        metadata={"last_fetched": now.isoformat()},
    )


def _populate_cache(
    cache: MockCacheProvider,
    task_gid: str,
    stories: list[dict[str, Any]],
) -> None:
    """Populate cache with story data for a task GID."""
    entry = _make_story_entry(task_gid, stories)
    cache._cache[f"{EntryType.STORIES.value}:{task_gid}"] = entry


# ---------------------------------------------------------------------------
# read_cached_stories (Gap 1)
# ---------------------------------------------------------------------------


class TestReadCachedStories:
    @pytest.fixture
    def cache(self) -> MockCacheProvider:
        return MockCacheProvider()

    def test_cache_hit_returns_list(self, cache: MockCacheProvider) -> None:
        """Cache hit returns the stored story list."""
        stories = [
            {"gid": "s1", "resource_subtype": "section_changed"},
            {"gid": "s2", "resource_subtype": "assignee_changed"},
        ]
        _populate_cache(cache, "task1", stories)

        result = read_cached_stories("task1", cache)
        assert result is not None
        assert result == stories

    def test_cache_miss_returns_none(self, cache: MockCacheProvider) -> None:
        """Empty cache returns None."""
        result = read_cached_stories("nonexistent", cache)
        assert result is None

    def test_does_not_modify_cache(self, cache: MockCacheProvider) -> None:
        """Pure-read: no set_versioned calls."""
        stories = [{"gid": "s1"}]
        _populate_cache(cache, "task1", stories)

        read_cached_stories("task1", cache)

        # Only get_versioned should be called, no set_versioned
        call_types = [call[0] for call in cache.calls]
        assert "set_versioned" not in call_types

    def test_empty_stories_list_returns_empty(
        self, cache: MockCacheProvider
    ) -> None:
        """Cached entry with empty stories list returns empty list (not None)."""
        _populate_cache(cache, "task1", [])
        result = read_cached_stories("task1", cache)
        assert result == []

    def test_does_not_call_asana_api(self, cache: MockCacheProvider) -> None:
        """Verify no network calls -- pure read only checks cache."""
        # This is structural: read_cached_stories has no fetcher parameter,
        # so it cannot make API calls by design.
        result = read_cached_stories("task1", cache)
        assert result is None


# ---------------------------------------------------------------------------
# read_stories_batch (Gap 4)
# ---------------------------------------------------------------------------


class TestReadStoriesBatch:
    @pytest.fixture
    def cache(self) -> MockCacheProvider:
        return MockCacheProvider()

    def test_empty_input_returns_empty(self, cache: MockCacheProvider) -> None:
        """Empty task_gids list returns empty dict."""
        result = read_stories_batch([], cache)
        assert result == {}

    def test_all_hits(self, cache: MockCacheProvider) -> None:
        """All task GIDs have cached stories."""
        _populate_cache(cache, "t1", [{"gid": "s1"}])
        _populate_cache(cache, "t2", [{"gid": "s2"}])

        result = read_stories_batch(["t1", "t2"], cache)
        assert result["t1"] == [{"gid": "s1"}]
        assert result["t2"] == [{"gid": "s2"}]

    def test_all_misses(self, cache: MockCacheProvider) -> None:
        """All task GIDs are cache misses."""
        result = read_stories_batch(["t1", "t2", "t3"], cache)
        assert result["t1"] is None
        assert result["t2"] is None
        assert result["t3"] is None

    def test_mix_of_hits_and_misses(self, cache: MockCacheProvider) -> None:
        """Mixed cache: some hits, some misses."""
        _populate_cache(cache, "t1", [{"gid": "s1"}])
        # t2 is not cached

        result = read_stories_batch(["t1", "t2"], cache)
        assert result["t1"] == [{"gid": "s1"}]
        assert result["t2"] is None

    def test_chunking_small_batch(self, cache: MockCacheProvider) -> None:
        """Batch smaller than chunk_size uses one get_batch call."""
        _populate_cache(cache, "t1", [{"gid": "s1"}])

        read_stories_batch(["t1"], cache, chunk_size=500)

        # Should be exactly one get_batch call
        batch_calls = [c for c in cache.calls if c[0] == "get_batch"]
        assert len(batch_calls) == 1

    def test_chunking_splits_large_batch(
        self, cache: MockCacheProvider
    ) -> None:
        """Batch larger than chunk_size is split into multiple get_batch calls."""
        # Create 7 tasks with chunk_size=3 -> should be 3 chunks (3+3+1)
        gids = [f"t{i}" for i in range(7)]
        for gid in gids:
            _populate_cache(cache, gid, [{"gid": f"s_{gid}"}])

        result = read_stories_batch(gids, cache, chunk_size=3)

        # All 7 should be returned
        assert len(result) == 7
        for gid in gids:
            assert result[gid] is not None

        # Should have 3 get_batch calls: [t0,t1,t2], [t3,t4,t5], [t6]
        batch_calls = [c for c in cache.calls if c[0] == "get_batch"]
        assert len(batch_calls) == 3

    def test_chunking_exact_boundary(self, cache: MockCacheProvider) -> None:
        """Batch size exactly equals chunk_size -> one get_batch call."""
        gids = [f"t{i}" for i in range(5)]
        for gid in gids:
            _populate_cache(cache, gid, [])

        read_stories_batch(gids, cache, chunk_size=5)

        batch_calls = [c for c in cache.calls if c[0] == "get_batch"]
        assert len(batch_calls) == 1

    def test_large_batch_over_500(self, cache: MockCacheProvider) -> None:
        """Default chunk_size=500: 600 keys -> 2 chunks."""
        gids = [f"t{i}" for i in range(600)]
        # Only populate first 10 to test mixed results
        for i in range(10):
            _populate_cache(cache, f"t{i}", [{"gid": f"s{i}"}])

        result = read_stories_batch(gids, cache)

        assert len(result) == 600
        # First 10 should be hits
        for i in range(10):
            assert result[f"t{i}"] is not None
        # Rest should be misses
        for i in range(10, 600):
            assert result[f"t{i}"] is None

        # Should be 2 chunks: [0..499] and [500..599]
        batch_calls = [c for c in cache.calls if c[0] == "get_batch"]
        assert len(batch_calls) == 2

    def test_returns_all_keys_from_input(
        self, cache: MockCacheProvider
    ) -> None:
        """Every key in the input appears in the output (hit or miss)."""
        gids = ["a", "b", "c"]
        _populate_cache(cache, "b", [{"gid": "s_b"}])

        result = read_stories_batch(gids, cache)

        assert set(result.keys()) == {"a", "b", "c"}
