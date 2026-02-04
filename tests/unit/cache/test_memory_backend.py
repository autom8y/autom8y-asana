"""Tests for EnhancedInMemoryCacheProvider and InMemoryCacheProvider."""

import time
from datetime import UTC, datetime

import pytest

from autom8_asana._defaults.cache import InMemoryCacheProvider, NullCacheProvider
from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.protocols.cache import WarmResult


class TestNullCacheProvider:
    """Tests for NullCacheProvider."""

    def test_get_returns_none(self) -> None:
        """Test get always returns None."""
        cache = NullCacheProvider()
        cache.set("key", {"data": "value"})

        assert cache.get("key") is None

    def test_set_does_nothing(self) -> None:
        """Test set doesn't store anything."""
        cache = NullCacheProvider()
        cache.set("key", {"data": "value"}, ttl=300)

        # No exception, just returns None
        assert cache.get("key") is None

    def test_delete_does_nothing(self) -> None:
        """Test delete doesn't raise."""
        cache = NullCacheProvider()
        cache.delete("nonexistent")  # Should not raise

    def test_get_versioned_returns_none(self) -> None:
        """Test get_versioned always returns None."""
        cache = NullCacheProvider()

        assert cache.get_versioned("key", EntryType.TASK) is None

    def test_set_versioned_does_nothing(self) -> None:
        """Test set_versioned doesn't store anything."""
        cache = NullCacheProvider()
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
        )
        cache.set_versioned("123", entry)

        assert cache.get_versioned("123", EntryType.TASK) is None

    def test_get_batch_returns_all_none(self) -> None:
        """Test get_batch returns all None."""
        cache = NullCacheProvider()
        result = cache.get_batch(["a", "b", "c"], EntryType.TASK)

        assert result == {"a": None, "b": None, "c": None}

    def test_warm_returns_all_skipped(self) -> None:
        """Test warm returns all skipped."""
        cache = NullCacheProvider()
        result = cache.warm(["1", "2", "3"])

        assert isinstance(result, WarmResult)
        assert result.skipped == 3
        assert result.warmed == 0

    def test_check_freshness_returns_false(self) -> None:
        """Test check_freshness always returns False."""
        cache = NullCacheProvider()

        assert cache.check_freshness("key", EntryType.TASK, datetime.now(UTC)) is False

    def test_is_healthy_returns_true(self) -> None:
        """Test is_healthy returns True."""
        cache = NullCacheProvider()

        assert cache.is_healthy() is True

    def test_get_metrics_returns_new_instance(self) -> None:
        """Test get_metrics returns a CacheMetrics instance."""
        cache = NullCacheProvider()
        metrics = cache.get_metrics()

        assert metrics.hits == 0
        assert metrics.misses == 0


class TestInMemoryCacheProvider:
    """Tests for InMemoryCacheProvider (from _defaults)."""

    def test_basic_get_set(self) -> None:
        """Test basic get/set operations."""
        cache = InMemoryCacheProvider()
        cache.set("key", {"data": "value"})

        assert cache.get("key") == {"data": "value"}

    def test_get_miss(self) -> None:
        """Test get returns None for missing key."""
        cache = InMemoryCacheProvider()

        assert cache.get("nonexistent") is None

    @pytest.mark.slow
    def test_ttl_expiration(self) -> None:
        """Test entries expire after TTL."""
        cache = InMemoryCacheProvider(default_ttl=1)
        cache.set("key", {"data": "value"})

        assert cache.get("key") == {"data": "value"}
        time.sleep(1.1)
        assert cache.get("key") is None

    @pytest.mark.slow
    def test_explicit_ttl_override(self) -> None:
        """Test explicit TTL overrides default."""
        cache = InMemoryCacheProvider(default_ttl=100)
        cache.set("key", {"data": "value"}, ttl=1)

        assert cache.get("key") == {"data": "value"}
        time.sleep(1.1)
        assert cache.get("key") is None

    def test_delete(self) -> None:
        """Test delete removes entry."""
        cache = InMemoryCacheProvider()
        cache.set("key", {"data": "value"})
        cache.delete("key")

        assert cache.get("key") is None

    def test_versioned_operations(self) -> None:
        """Test versioned get/set operations."""
        cache = InMemoryCacheProvider()
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
            ttl=300,
        )

        cache.set_versioned("123", entry)
        result = cache.get_versioned("123", EntryType.TASK)

        assert result is not None
        assert result.data["name"] == "Test"
        assert result.entry_type == EntryType.TASK

    def test_versioned_different_types(self) -> None:
        """Test versioned entries are separate by type."""
        cache = InMemoryCacheProvider()
        now = datetime.now(UTC)

        task_entry = CacheEntry(
            key="123",
            data={"type": "task"},
            entry_type=EntryType.TASK,
            version=now,
        )
        subtasks_entry = CacheEntry(
            key="123",
            data={"type": "subtasks"},
            entry_type=EntryType.SUBTASKS,
            version=now,
        )

        cache.set_versioned("123", task_entry)
        cache.set_versioned("123", subtasks_entry)

        task_result = cache.get_versioned("123", EntryType.TASK)
        subtasks_result = cache.get_versioned("123", EntryType.SUBTASKS)

        assert task_result is not None
        assert task_result.data["type"] == "task"
        assert subtasks_result is not None
        assert subtasks_result.data["type"] == "subtasks"

    def test_check_freshness(self) -> None:
        """Test check_freshness compares versions."""
        cache = InMemoryCacheProvider()
        cached_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_time,
        )
        cache.set_versioned("123", entry)

        # Same version should be fresh
        assert cache.check_freshness("123", EntryType.TASK, cached_time) is True

        # Older version should be fresh
        older = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        assert cache.check_freshness("123", EntryType.TASK, older) is True

        # Newer version should be stale
        newer = datetime(2025, 1, 1, 14, 0, 0, tzinfo=UTC)
        assert cache.check_freshness("123", EntryType.TASK, newer) is False

    def test_invalidate_single_type(self) -> None:
        """Test invalidate removes specific entry type."""
        cache = InMemoryCacheProvider()
        now = datetime.now(UTC)

        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={},
                entry_type=EntryType.TASK,
                version=now,
            ),
        )
        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={},
                entry_type=EntryType.SUBTASKS,
                version=now,
            ),
        )

        cache.invalidate("123", [EntryType.TASK])

        assert cache.get_versioned("123", EntryType.TASK) is None
        assert cache.get_versioned("123", EntryType.SUBTASKS) is not None

    def test_invalidate_all_types(self) -> None:
        """Test invalidate removes all entry types."""
        cache = InMemoryCacheProvider()
        now = datetime.now(UTC)

        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={},
                entry_type=EntryType.TASK,
                version=now,
            ),
        )
        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={},
                entry_type=EntryType.SUBTASKS,
                version=now,
            ),
        )

        cache.invalidate("123")

        assert cache.get_versioned("123", EntryType.TASK) is None
        assert cache.get_versioned("123", EntryType.SUBTASKS) is None

    def test_get_batch(self) -> None:
        """Test get_batch retrieves multiple entries."""
        cache = InMemoryCacheProvider()
        now = datetime.now(UTC)

        cache.set_versioned(
            "1",
            CacheEntry(
                key="1",
                data={"id": 1},
                entry_type=EntryType.TASK,
                version=now,
            ),
        )
        cache.set_versioned(
            "2",
            CacheEntry(
                key="2",
                data={"id": 2},
                entry_type=EntryType.TASK,
                version=now,
            ),
        )

        result = cache.get_batch(["1", "2", "3"], EntryType.TASK)

        assert result["1"] is not None
        assert result["1"].data["id"] == 1
        assert result["2"] is not None
        assert result["2"].data["id"] == 2
        assert result["3"] is None

    def test_set_batch(self) -> None:
        """Test set_batch stores multiple entries."""
        cache = InMemoryCacheProvider()
        now = datetime.now(UTC)

        entries = {
            "1": CacheEntry(
                key="1", data={"id": 1}, entry_type=EntryType.TASK, version=now
            ),
            "2": CacheEntry(
                key="2", data={"id": 2}, entry_type=EntryType.TASK, version=now
            ),
        }

        cache.set_batch(entries)

        assert cache.get_versioned("1", EntryType.TASK) is not None
        assert cache.get_versioned("2", EntryType.TASK) is not None

    def test_is_healthy(self) -> None:
        """Test is_healthy returns True."""
        cache = InMemoryCacheProvider()
        assert cache.is_healthy() is True

    def test_get_metrics(self) -> None:
        """Test get_metrics returns CacheMetrics."""
        cache = InMemoryCacheProvider()
        metrics = cache.get_metrics()

        assert metrics is not None
        assert metrics.hits == 0


class TestEnhancedInMemoryCacheProvider:
    """Tests for EnhancedInMemoryCacheProvider (from cache.backends)."""

    def test_basic_operations(self) -> None:
        """Test basic get/set/delete operations."""
        cache = EnhancedInMemoryCacheProvider()
        cache.set("key", {"data": "value"})

        assert cache.get("key") == {"data": "value"}

        cache.delete("key")
        assert cache.get("key") is None

    def test_versioned_operations(self) -> None:
        """Test versioned get/set operations."""
        cache = EnhancedInMemoryCacheProvider()
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
        )

        cache.set_versioned("123", entry)
        result = cache.get_versioned("123", EntryType.TASK)

        assert result is not None
        assert result.data["name"] == "Test"

    def test_metrics_recording(self) -> None:
        """Test metrics are recorded for operations."""
        cache = EnhancedInMemoryCacheProvider()

        # Generate some hits and misses
        cache.set("key", {"data": "value"})
        cache.get("key")  # Hit
        cache.get("missing")  # Miss

        metrics = cache.get_metrics()
        assert metrics.hits >= 1
        assert metrics.misses >= 1

    def test_eviction_at_capacity(self) -> None:
        """Test eviction when max_size is reached."""
        cache = EnhancedInMemoryCacheProvider(max_size=10)

        # Fill beyond capacity
        for i in range(15):
            cache.set(f"key_{i}", {"data": i})

        # Some early entries should be evicted
        assert cache.size() <= 10

    def test_clear(self) -> None:
        """Test clear removes all entries."""
        cache = EnhancedInMemoryCacheProvider()
        cache.set("key1", {"data": 1})
        cache.set("key2", {"data": 2})
        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={},
                entry_type=EntryType.TASK,
                version=datetime.now(UTC),
            ),
        )

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get_versioned("123", EntryType.TASK) is None
        assert cache.size() == 0

    def test_size(self) -> None:
        """Test size returns correct count."""
        cache = EnhancedInMemoryCacheProvider()
        assert cache.size() == 0

        cache.set("key1", {"data": 1})
        assert cache.size() == 1

        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={},
                entry_type=EntryType.TASK,
                version=datetime.now(UTC),
            ),
        )
        assert cache.size() == 2

    def test_reset_metrics(self) -> None:
        """Test reset_metrics clears all counters."""
        cache = EnhancedInMemoryCacheProvider()
        cache.set("key", {"data": "value"})
        cache.get("key")
        cache.get("missing")

        cache.reset_metrics()
        metrics = cache.get_metrics()

        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.writes == 0

    @pytest.mark.slow
    def test_versioned_ttl_expiration(self) -> None:
        """Test versioned entries expire based on TTL."""
        cache = EnhancedInMemoryCacheProvider()

        # Create entry with 1 second TTL
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
            ttl=1,
        )
        cache.set_versioned("123", entry)

        # Should be present immediately
        assert cache.get_versioned("123", EntryType.TASK) is not None

        # Should expire after TTL
        time.sleep(1.1)
        assert cache.get_versioned("123", EntryType.TASK) is None

    def test_warm_returns_placeholder(self) -> None:
        """Test warm returns placeholder result."""
        cache = EnhancedInMemoryCacheProvider()
        result = cache.warm(["1", "2", "3"])

        assert isinstance(result, WarmResult)
        assert result.skipped == 3
