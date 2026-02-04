"""Tests for multi-entry loading helpers."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness import Freshness
from autom8_asana.cache.integration.loader import (
    load_batch_entries,
    load_task_entries,
    load_task_entry,
)


class TestLoadTaskEntry:
    """Tests for load_task_entry function."""

    @pytest.mark.asyncio
    async def test_cache_miss_fetches_data(self) -> None:
        """Test that cache miss triggers API fetch."""
        cache = EnhancedInMemoryCacheProvider()
        fetcher = AsyncMock(
            return_value={
                "gid": "123",
                "name": "Test Task",
                "modified_at": "2025-01-01T00:00:00Z",
            }
        )

        entry, hit = await load_task_entry(
            task_gid="123",
            entry_type=EntryType.TASK,
            cache=cache,
            fetcher=fetcher,
        )

        assert hit is False
        assert entry is not None
        assert entry.data["name"] == "Test Task"
        fetcher.assert_called_once_with("123")

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(self) -> None:
        """Test that cache hit returns cached entry without fetch."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(UTC)

        # Pre-populate cache
        cached_entry = CacheEntry(
            key="123",
            data={"gid": "123", "name": "Cached Task"},
            entry_type=EntryType.TASK,
            version=now,
            ttl=300,
        )
        cache.set_versioned("123", cached_entry)

        fetcher = AsyncMock()

        entry, hit = await load_task_entry(
            task_gid="123",
            entry_type=EntryType.TASK,
            cache=cache,
            fetcher=fetcher,
        )

        assert hit is True
        assert entry is not None
        assert entry.data["name"] == "Cached Task"
        fetcher.assert_not_called()

    @pytest.mark.asyncio
    async def test_stale_entry_refetches_strict_mode(self) -> None:
        """Test that stale entry triggers refetch in STRICT mode."""
        cache = EnhancedInMemoryCacheProvider()
        old_time = datetime.now(UTC) - timedelta(hours=1)
        new_time = datetime.now(UTC)

        # Pre-populate cache with old version
        cached_entry = CacheEntry(
            key="123",
            data={"gid": "123", "name": "Old Task"},
            entry_type=EntryType.TASK,
            version=old_time,
            ttl=300,
        )
        cache.set_versioned("123", cached_entry)

        fetcher = AsyncMock(
            return_value={
                "gid": "123",
                "name": "New Task",
                "modified_at": new_time.isoformat(),
            }
        )

        entry, hit = await load_task_entry(
            task_gid="123",
            entry_type=EntryType.TASK,
            cache=cache,
            fetcher=fetcher,
            current_modified_at=new_time.isoformat(),
            freshness=Freshness.STRICT,
        )

        assert hit is False
        assert entry is not None
        assert entry.data["name"] == "New Task"
        fetcher.assert_called_once()

    @pytest.mark.asyncio
    async def test_eventual_mode_ignores_version(self) -> None:
        """Test that EVENTUAL mode ignores version staleness."""
        cache = EnhancedInMemoryCacheProvider()
        old_time = datetime.now(UTC) - timedelta(hours=1)
        new_time = datetime.now(UTC)

        # Pre-populate cache with old version
        cached_entry = CacheEntry(
            key="123",
            data={"gid": "123", "name": "Cached Task"},
            entry_type=EntryType.TASK,
            version=old_time,
            cached_at=datetime.now(UTC),  # Recently cached
            ttl=300,
        )
        cache.set_versioned("123", cached_entry)

        fetcher = AsyncMock()

        entry, hit = await load_task_entry(
            task_gid="123",
            entry_type=EntryType.TASK,
            cache=cache,
            fetcher=fetcher,
            current_modified_at=new_time.isoformat(),
            freshness=Freshness.EVENTUAL,
        )

        assert hit is True
        assert entry is not None
        assert entry.data["name"] == "Cached Task"
        fetcher.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_fetch_returns_none(self) -> None:
        """Test that empty fetch result returns None."""
        cache = EnhancedInMemoryCacheProvider()
        fetcher = AsyncMock(return_value={})

        entry, hit = await load_task_entry(
            task_gid="123",
            entry_type=EntryType.TASK,
            cache=cache,
            fetcher=fetcher,
        )

        assert hit is False
        assert entry is None

    @pytest.mark.asyncio
    async def test_none_fetch_returns_none(self) -> None:
        """Test that None fetch result returns None."""
        cache = EnhancedInMemoryCacheProvider()
        fetcher = AsyncMock(return_value=None)

        entry, hit = await load_task_entry(
            task_gid="123",
            entry_type=EntryType.TASK,
            cache=cache,
            fetcher=fetcher,
        )

        assert hit is False
        assert entry is None

    @pytest.mark.asyncio
    async def test_caches_fetched_data(self) -> None:
        """Test that fetched data is cached."""
        cache = EnhancedInMemoryCacheProvider()
        fetcher = AsyncMock(
            return_value={
                "gid": "123",
                "name": "Test Task",
                "modified_at": "2025-01-01T00:00:00Z",
            }
        )

        await load_task_entry(
            task_gid="123",
            entry_type=EntryType.TASK,
            cache=cache,
            fetcher=fetcher,
        )

        # Verify cached
        cached = cache.get_versioned("123", EntryType.TASK)
        assert cached is not None
        assert cached.data["name"] == "Test Task"

    @pytest.mark.asyncio
    async def test_custom_ttl(self) -> None:
        """Test custom TTL is applied to cached entry."""
        cache = EnhancedInMemoryCacheProvider()
        fetcher = AsyncMock(
            return_value={
                "gid": "123",
                "name": "Test Task",
                "modified_at": "2025-01-01T00:00:00Z",
            }
        )

        entry, _ = await load_task_entry(
            task_gid="123",
            entry_type=EntryType.TASK,
            cache=cache,
            fetcher=fetcher,
            ttl=600,
        )

        assert entry is not None
        assert entry.ttl == 600

    @pytest.mark.asyncio
    async def test_project_gid_stored(self) -> None:
        """Test project_gid is stored in cache entry."""
        cache = EnhancedInMemoryCacheProvider()
        fetcher = AsyncMock(
            return_value={
                "gid": "123",
                "name": "Test Task",
                "modified_at": "2025-01-01T00:00:00Z",
            }
        )

        entry, _ = await load_task_entry(
            task_gid="123",
            entry_type=EntryType.DATAFRAME,
            cache=cache,
            fetcher=fetcher,
            project_gid="project_456",
        )

        assert entry is not None
        assert entry.project_gid == "project_456"

    @pytest.mark.asyncio
    async def test_version_extracted_from_data(self) -> None:
        """Test version is extracted from fetched data."""
        cache = EnhancedInMemoryCacheProvider()
        fetcher = AsyncMock(
            return_value={
                "gid": "123",
                "name": "Test Task",
                "modified_at": "2025-06-15T12:30:00Z",
            }
        )

        entry, _ = await load_task_entry(
            task_gid="123",
            entry_type=EntryType.TASK,
            cache=cache,
            fetcher=fetcher,
        )

        assert entry is not None
        assert entry.version == datetime(2025, 6, 15, 12, 30, 0, tzinfo=UTC)

    @pytest.mark.asyncio
    async def test_missing_modified_at_uses_now(self) -> None:
        """Test missing modified_at uses current time as version."""
        cache = EnhancedInMemoryCacheProvider()
        before = datetime.now(UTC)

        fetcher = AsyncMock(
            return_value={
                "gid": "123",
                "name": "Test Task",
                # No modified_at
            }
        )

        entry, _ = await load_task_entry(
            task_gid="123",
            entry_type=EntryType.TASK,
            cache=cache,
            fetcher=fetcher,
        )

        after = datetime.now(UTC)

        assert entry is not None
        assert before <= entry.version <= after


class TestLoadTaskEntries:
    """Tests for load_task_entries function."""

    @pytest.mark.asyncio
    async def test_loads_multiple_types_concurrently(self) -> None:
        """Test loading multiple entry types concurrently."""
        cache = EnhancedInMemoryCacheProvider()

        task_fetcher = AsyncMock(
            return_value={
                "gid": "123",
                "name": "Task",
                "modified_at": "2025-01-01T00:00:00Z",
            }
        )
        subtasks_fetcher = AsyncMock(
            return_value={
                "subtasks": [],
                "modified_at": "2025-01-01T00:00:00Z",
            }
        )

        results = await load_task_entries(
            task_gid="123",
            entry_types=[EntryType.TASK, EntryType.SUBTASKS],
            cache=cache,
            fetchers={
                EntryType.TASK: task_fetcher,
                EntryType.SUBTASKS: subtasks_fetcher,
            },
        )

        assert EntryType.TASK in results
        assert EntryType.SUBTASKS in results

        task_entry, task_hit = results[EntryType.TASK]
        assert task_hit is False
        assert task_entry is not None
        assert task_entry.data["name"] == "Task"

        subtasks_entry, subtasks_hit = results[EntryType.SUBTASKS]
        assert subtasks_hit is False
        assert subtasks_entry is not None

    @pytest.mark.asyncio
    async def test_partial_cache_hit(self) -> None:
        """Test mix of cache hits and misses."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(UTC)

        # Pre-cache TASK entry
        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={"gid": "123", "name": "Cached Task"},
                entry_type=EntryType.TASK,
                version=now,
                ttl=300,
            ),
        )

        task_fetcher = AsyncMock()
        subtasks_fetcher = AsyncMock(
            return_value={
                "subtasks": [],
                "modified_at": now.isoformat(),
            }
        )

        results = await load_task_entries(
            task_gid="123",
            entry_types=[EntryType.TASK, EntryType.SUBTASKS],
            cache=cache,
            fetchers={
                EntryType.TASK: task_fetcher,
                EntryType.SUBTASKS: subtasks_fetcher,
            },
        )

        task_entry, task_hit = results[EntryType.TASK]
        assert task_hit is True
        task_fetcher.assert_not_called()

        subtasks_entry, subtasks_hit = results[EntryType.SUBTASKS]
        assert subtasks_hit is False
        subtasks_fetcher.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_fetcher_returns_none(self) -> None:
        """Test missing fetcher returns None for that type."""
        cache = EnhancedInMemoryCacheProvider()

        task_fetcher = AsyncMock(
            return_value={
                "gid": "123",
                "modified_at": "2025-01-01T00:00:00Z",
            }
        )

        results = await load_task_entries(
            task_gid="123",
            entry_types=[EntryType.TASK, EntryType.SUBTASKS],
            cache=cache,
            fetchers={
                EntryType.TASK: task_fetcher,
                # No SUBTASKS fetcher
            },
        )

        assert EntryType.TASK in results
        assert EntryType.SUBTASKS in results

        subtasks_entry, subtasks_hit = results[EntryType.SUBTASKS]
        assert subtasks_entry is None
        assert subtasks_hit is False

    @pytest.mark.asyncio
    async def test_fetcher_exception_continues_others(self) -> None:
        """Test that one fetcher exception doesn't stop others."""
        cache = EnhancedInMemoryCacheProvider()

        task_fetcher = AsyncMock(side_effect=ConnectionError("API Error"))
        subtasks_fetcher = AsyncMock(
            return_value={
                "subtasks": [],
                "modified_at": "2025-01-01T00:00:00Z",
            }
        )

        results = await load_task_entries(
            task_gid="123",
            entry_types=[EntryType.TASK, EntryType.SUBTASKS],
            cache=cache,
            fetchers={
                EntryType.TASK: task_fetcher,
                EntryType.SUBTASKS: subtasks_fetcher,
            },
        )

        # TASK failed, should not be in results
        assert EntryType.TASK not in results

        # SUBTASKS should succeed
        assert EntryType.SUBTASKS in results
        subtasks_entry, _ = results[EntryType.SUBTASKS]
        assert subtasks_entry is not None

    @pytest.mark.asyncio
    async def test_empty_entry_types_list(self) -> None:
        """Test with empty entry types list."""
        cache = EnhancedInMemoryCacheProvider()

        results = await load_task_entries(
            task_gid="123",
            entry_types=[],
            cache=cache,
            fetchers={},
        )

        assert results == {}


class TestLoadBatchEntries:
    """Tests for load_batch_entries function."""

    @pytest.mark.asyncio
    async def test_fetches_all_on_empty_cache(self) -> None:
        """Test all GIDs are fetched when cache is empty."""
        cache = EnhancedInMemoryCacheProvider()

        batch_fetcher = AsyncMock(
            return_value={
                "123": {
                    "gid": "123",
                    "name": "Task 1",
                    "modified_at": "2025-01-01T00:00:00Z",
                },
                "456": {
                    "gid": "456",
                    "name": "Task 2",
                    "modified_at": "2025-01-01T00:00:00Z",
                },
            }
        )

        results = await load_batch_entries(
            task_gids=["123", "456"],
            entry_type=EntryType.TASK,
            cache=cache,
            batch_fetcher=batch_fetcher,
        )

        assert len(results) == 2

        entry1, hit1 = results["123"]
        assert hit1 is False
        assert entry1 is not None
        assert entry1.data["name"] == "Task 1"

        entry2, hit2 = results["456"]
        assert hit2 is False
        assert entry2 is not None
        assert entry2.data["name"] == "Task 2"

        batch_fetcher.assert_called_once_with(["123", "456"])

    @pytest.mark.asyncio
    async def test_uses_cache_for_cached_gids(self) -> None:
        """Test cached GIDs are not refetched."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(UTC)

        # Pre-cache one entry
        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={"gid": "123", "name": "Cached Task"},
                entry_type=EntryType.TASK,
                version=now,
                ttl=300,
            ),
        )

        batch_fetcher = AsyncMock(
            return_value={
                "456": {
                    "gid": "456",
                    "name": "Fetched Task",
                    "modified_at": now.isoformat(),
                },
            }
        )

        results = await load_batch_entries(
            task_gids=["123", "456"],
            entry_type=EntryType.TASK,
            cache=cache,
            batch_fetcher=batch_fetcher,
        )

        entry1, hit1 = results["123"]
        assert hit1 is True
        assert entry1 is not None
        assert entry1.data["name"] == "Cached Task"

        entry2, hit2 = results["456"]
        assert hit2 is False
        assert entry2 is not None
        assert entry2.data["name"] == "Fetched Task"

        # Only uncached should be fetched
        batch_fetcher.assert_called_once_with(["456"])

    @pytest.mark.asyncio
    async def test_no_api_call_when_all_cached(self) -> None:
        """Test no API call when all GIDs are cached."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(UTC)

        # Pre-cache all entries
        for gid in ["123", "456"]:
            cache.set_versioned(
                gid,
                CacheEntry(
                    key=gid,
                    data={"gid": gid, "name": f"Task {gid}"},
                    entry_type=EntryType.TASK,
                    version=now,
                    ttl=300,
                ),
            )

        batch_fetcher = AsyncMock()

        results = await load_batch_entries(
            task_gids=["123", "456"],
            entry_type=EntryType.TASK,
            cache=cache,
            batch_fetcher=batch_fetcher,
        )

        assert len(results) == 2
        assert results["123"][1] is True  # Cache hit
        assert results["456"][1] is True  # Cache hit

        batch_fetcher.assert_not_called()

    @pytest.mark.asyncio
    async def test_strict_mode_refetches_stale(self) -> None:
        """Test STRICT mode refetches stale entries."""
        cache = EnhancedInMemoryCacheProvider()
        old_time = datetime.now(UTC) - timedelta(hours=1)
        new_time = datetime.now(UTC)

        # Pre-cache with old version
        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={"gid": "123", "name": "Old Task"},
                entry_type=EntryType.TASK,
                version=old_time,
                ttl=300,
            ),
        )

        batch_fetcher = AsyncMock(
            return_value={
                "123": {
                    "gid": "123",
                    "name": "New Task",
                    "modified_at": new_time.isoformat(),
                },
            }
        )

        results = await load_batch_entries(
            task_gids=["123"],
            entry_type=EntryType.TASK,
            cache=cache,
            batch_fetcher=batch_fetcher,
            current_versions={"123": new_time.isoformat()},
            freshness=Freshness.STRICT,
        )

        entry, hit = results["123"]
        assert hit is False
        assert entry is not None
        assert entry.data["name"] == "New Task"

    @pytest.mark.asyncio
    async def test_caches_fetched_entries(self) -> None:
        """Test fetched entries are batch cached."""
        cache = EnhancedInMemoryCacheProvider()

        batch_fetcher = AsyncMock(
            return_value={
                "123": {
                    "gid": "123",
                    "name": "Task 1",
                    "modified_at": "2025-01-01T00:00:00Z",
                },
                "456": {
                    "gid": "456",
                    "name": "Task 2",
                    "modified_at": "2025-01-01T00:00:00Z",
                },
            }
        )

        await load_batch_entries(
            task_gids=["123", "456"],
            entry_type=EntryType.TASK,
            cache=cache,
            batch_fetcher=batch_fetcher,
        )

        # Verify both are cached
        assert cache.get_versioned("123", EntryType.TASK) is not None
        assert cache.get_versioned("456", EntryType.TASK) is not None

    @pytest.mark.asyncio
    async def test_missing_gid_in_fetch_returns_none(self) -> None:
        """Test GIDs not returned by fetcher have None entries."""
        cache = EnhancedInMemoryCacheProvider()

        batch_fetcher = AsyncMock(
            return_value={
                "123": {
                    "gid": "123",
                    "name": "Task 1",
                    "modified_at": "2025-01-01T00:00:00Z",
                },
                # "456" not returned
            }
        )

        results = await load_batch_entries(
            task_gids=["123", "456"],
            entry_type=EntryType.TASK,
            cache=cache,
            batch_fetcher=batch_fetcher,
        )

        entry1, hit1 = results["123"]
        assert entry1 is not None

        entry2, hit2 = results["456"]
        assert entry2 is None
        assert hit2 is False

    @pytest.mark.asyncio
    async def test_empty_gids_list(self) -> None:
        """Test with empty GIDs list."""
        cache = EnhancedInMemoryCacheProvider()
        batch_fetcher = AsyncMock()

        results = await load_batch_entries(
            task_gids=[],
            entry_type=EntryType.TASK,
            cache=cache,
            batch_fetcher=batch_fetcher,
        )

        assert results == {}
        batch_fetcher.assert_not_called()

    @pytest.mark.asyncio
    async def test_custom_ttl(self) -> None:
        """Test custom TTL is applied to cached entries."""
        cache = EnhancedInMemoryCacheProvider()

        batch_fetcher = AsyncMock(
            return_value={
                "123": {
                    "gid": "123",
                    "name": "Task 1",
                    "modified_at": "2025-01-01T00:00:00Z",
                },
            }
        )

        results = await load_batch_entries(
            task_gids=["123"],
            entry_type=EntryType.TASK,
            cache=cache,
            batch_fetcher=batch_fetcher,
            ttl=600,
        )

        entry, _ = results["123"]
        assert entry is not None
        assert entry.ttl == 600

    @pytest.mark.asyncio
    async def test_handles_100_plus_gids(self) -> None:
        """Test handling 100+ GIDs efficiently."""
        cache = EnhancedInMemoryCacheProvider()
        gids = [str(i) for i in range(150)]

        batch_fetcher = AsyncMock(
            return_value={
                gid: {
                    "gid": gid,
                    "name": f"Task {gid}",
                    "modified_at": "2025-01-01T00:00:00Z",
                }
                for gid in gids
            }
        )

        results = await load_batch_entries(
            task_gids=gids,
            entry_type=EntryType.TASK,
            cache=cache,
            batch_fetcher=batch_fetcher,
        )

        assert len(results) == 150
        batch_fetcher.assert_called_once_with(gids)

    @pytest.mark.asyncio
    async def test_partial_cache_with_large_batch(self) -> None:
        """Test partial cache hit with large batch."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(UTC)

        # Pre-cache first 50
        for i in range(50):
            cache.set_versioned(
                str(i),
                CacheEntry(
                    key=str(i),
                    data={"gid": str(i), "name": f"Cached {i}"},
                    entry_type=EntryType.TASK,
                    version=now,
                    ttl=300,
                ),
            )

        gids = [str(i) for i in range(150)]

        batch_fetcher = AsyncMock(
            return_value={
                str(i): {
                    "gid": str(i),
                    "name": f"Fetched {i}",
                    "modified_at": now.isoformat(),
                }
                for i in range(50, 150)
            }
        )

        results = await load_batch_entries(
            task_gids=gids,
            entry_type=EntryType.TASK,
            cache=cache,
            batch_fetcher=batch_fetcher,
        )

        assert len(results) == 150

        # First 50 should be cache hits
        for i in range(50):
            entry, hit = results[str(i)]
            assert hit is True
            assert entry is not None
            assert entry.data["name"] == f"Cached {i}"

        # Rest should be fetched
        for i in range(50, 150):
            entry, hit = results[str(i)]
            assert hit is False
            assert entry is not None
            assert entry.data["name"] == f"Fetched {i}"

        # Only uncached should be fetched
        batch_fetcher.assert_called_once()
        fetched_gids = batch_fetcher.call_args[0][0]
        assert len(fetched_gids) == 100
