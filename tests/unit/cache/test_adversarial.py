"""Adversarial tests for the cache module.

These tests attempt to break the cache implementation through:
- Malformed data
- Edge case inputs
- Stress conditions
- Race conditions
- Unexpected sequences
"""

from __future__ import annotations

import gc
import json
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.cache.batch import (
    ModificationCheckCache,
    fetch_task_modifications,
    get_modification_cache,
    reset_modification_cache,
)
from autom8_asana.cache.entry import CacheEntry, EntryType, _parse_datetime
from autom8_asana.cache.freshness import Freshness
from autom8_asana.cache.metrics import CacheEvent, CacheMetrics
from autom8_asana.cache.settings import CacheSettings, OverflowSettings, TTLSettings
from autom8_asana.cache.staleness import check_entry_staleness, partition_by_staleness
from autom8_asana.cache.versioning import compare_versions, is_current, is_stale, parse_version


class TestMalformedDataEntry:
    """Tests for malformed data handling in CacheEntry."""

    def test_empty_data_dict(self) -> None:
        """Test CacheEntry with empty data dict."""
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
        )
        assert entry.data == {}
        assert not entry.is_expired()

    def test_none_values_in_data(self) -> None:
        """Test CacheEntry with None values in data."""
        entry = CacheEntry(
            key="123",
            data={"name": None, "gid": "123", "nested": {"value": None}},
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
        )
        assert entry.data["name"] is None
        assert entry.data["nested"]["value"] is None

    def test_deeply_nested_data(self) -> None:
        """Test CacheEntry with deeply nested data structure."""
        deep_data: dict[str, Any] = {"level0": {}}
        current = deep_data["level0"]
        for i in range(100):
            current["level" + str(i + 1)] = {}
            current = current["level" + str(i + 1)]
        current["value"] = "deep"

        entry = CacheEntry(
            key="123",
            data=deep_data,
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
        )
        assert "level0" in entry.data

    def test_unicode_in_data(self) -> None:
        """Test CacheEntry with various Unicode characters."""
        entry = CacheEntry(
            key="123",
            data={
                "emoji": "Task with emoji flag",
                "chinese": "Chinese characters",
                "arabic": "Arabic text",
                "special": "Tab\tNewline\nQuote\"Backslash\\",
            },
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
        )
        assert "emoji" in entry.data["emoji"]
        assert "\\n" not in entry.data["special"]  # Actual newline, not escaped

    def test_large_data_payload(self) -> None:
        """Test CacheEntry with large data payload."""
        # Create a 1MB payload
        large_string = "x" * (1024 * 1024)
        entry = CacheEntry(
            key="123",
            data={"large_field": large_string},
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
        )
        assert len(entry.data["large_field"]) == 1024 * 1024

    def test_list_with_many_items(self) -> None:
        """Test CacheEntry with list containing many items."""
        entry = CacheEntry(
            key="123",
            data={"items": list(range(10000))},
            entry_type=EntryType.SUBTASKS,
            version=datetime.now(timezone.utc),
        )
        assert len(entry.data["items"]) == 10000


class TestMalformedVersions:
    """Tests for malformed version handling."""

    def test_version_string_with_z_suffix(self) -> None:
        """Test parsing version with Z suffix."""
        result = parse_version("2025-01-15T10:30:00Z")
        assert result.tzinfo is not None
        assert result.year == 2025

    def test_version_string_without_timezone(self) -> None:
        """Test parsing version without timezone assumes UTC."""
        result = parse_version("2025-01-15T10:30:00")
        assert result.tzinfo == timezone.utc

    def test_version_string_with_microseconds(self) -> None:
        """Test parsing version with microseconds."""
        result = parse_version("2025-01-15T10:30:00.123456+00:00")
        assert result.microsecond == 123456

    def test_version_string_with_offset(self) -> None:
        """Test parsing version with non-UTC offset."""
        result = parse_version("2025-01-15T10:30:00+05:30")
        assert result.tzinfo is not None

    def test_invalid_version_string_raises(self) -> None:
        """Test that completely invalid version raises error."""
        with pytest.raises(ValueError):
            parse_version("not a date at all")

    def test_partial_date_string(self) -> None:
        """Test parsing date-only string."""
        result = parse_version("2025-01-15")
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_compare_mixed_types(self) -> None:
        """Test comparing datetime with string version."""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = compare_versions(dt, "2025-01-15T10:30:00+00:00")
        assert result == 0  # Equal

    def test_compare_naive_datetime(self) -> None:
        """Test comparing naive datetime (no timezone)."""
        naive_dt = datetime(2025, 1, 15, 10, 30, 0)
        aware_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = compare_versions(naive_dt, aware_dt)
        assert result == 0  # Should be equal after UTC assumption


class TestTTLEdgeCases:
    """Tests for TTL boundary conditions."""

    def test_ttl_exactly_at_boundary(self) -> None:
        """Test entry at exact TTL boundary."""
        cached_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_at,
            cached_at=cached_at,
            ttl=300,
        )

        # Exactly at 300 seconds - should NOT be expired (boundary is exclusive)
        now = cached_at + timedelta(seconds=300)
        assert not entry.is_expired(now)

    def test_ttl_one_millisecond_before(self) -> None:
        """Test entry one millisecond before TTL."""
        cached_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_at,
            cached_at=cached_at,
            ttl=300,
        )

        # 1ms before expiration
        now = cached_at + timedelta(seconds=299, milliseconds=999)
        assert not entry.is_expired(now)

    def test_ttl_one_millisecond_after(self) -> None:
        """Test entry one millisecond after TTL."""
        cached_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_at,
            cached_at=cached_at,
            ttl=300,
        )

        # 1ms after expiration
        now = cached_at + timedelta(seconds=300, milliseconds=1)
        assert entry.is_expired(now)

    def test_ttl_zero(self) -> None:
        """Test entry with TTL=0 expires immediately."""
        cached_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_at,
            cached_at=cached_at,
            ttl=0,
        )

        # Even 1ms later should be expired
        now = cached_at + timedelta(milliseconds=1)
        assert entry.is_expired(now)

    def test_ttl_none_never_expires(self) -> None:
        """Test entry with TTL=None never expires."""
        cached_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_at,
            cached_at=cached_at,
            ttl=None,
        )

        # Even years later should not be expired
        now = cached_at + timedelta(days=365 * 10)
        assert not entry.is_expired(now)

    def test_negative_ttl_treated_as_expired(self) -> None:
        """Test behavior with negative TTL (shouldn't happen, but test anyway)."""
        # Note: Real implementation should validate this
        cached_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_at,
            cached_at=cached_at,
            ttl=-1,  # Invalid, but test behavior
        )

        # With negative TTL, any positive elapsed time will be > TTL
        now = cached_at + timedelta(seconds=1)
        # Behavior: elapsed (1) > ttl (-1) is True, so expired
        assert entry.is_expired(now)


class TestCacheThrashing:
    """Tests for rapid cache operations (thrashing)."""

    def test_rapid_set_get_cycles(self) -> None:
        """Test rapid set/get cycles don't cause issues."""
        cache = EnhancedInMemoryCacheProvider(max_size=100)
        now = datetime.now(timezone.utc)

        for i in range(1000):
            entry = CacheEntry(
                key=f"key_{i % 10}",  # Cycle through 10 keys
                data={"iteration": i},
                entry_type=EntryType.TASK,
                version=now,
                ttl=300,
            )
            cache.set_versioned(f"key_{i % 10}", entry)
            result = cache.get_versioned(f"key_{i % 10}", EntryType.TASK)
            assert result is not None
            assert result.data["iteration"] == i

    def test_rapid_set_delete_cycles(self) -> None:
        """Test rapid set/delete cycles don't cause memory leak."""
        cache = EnhancedInMemoryCacheProvider(max_size=100)
        now = datetime.now(timezone.utc)

        for i in range(1000):
            key = f"key_{i}"
            entry = CacheEntry(
                key=key,
                data={"data": "x" * 1000},  # 1KB each
                entry_type=EntryType.TASK,
                version=now,
                ttl=300,
            )
            cache.set_versioned(key, entry)
            cache.invalidate(key)

        # After all operations, cache should be empty or nearly so
        assert cache.size() <= 10  # Some stragglers possible

    def test_eviction_under_pressure(self) -> None:
        """Test that eviction works under memory pressure."""
        cache = EnhancedInMemoryCacheProvider(max_size=50)
        now = datetime.now(timezone.utc)

        # Add more entries than max_size
        for i in range(100):
            entry = CacheEntry(
                key=f"key_{i}",
                data={"index": i},
                entry_type=EntryType.TASK,
                version=now,
                ttl=300,
            )
            cache.set_versioned(f"key_{i}", entry)

        # Size should not exceed max
        assert cache.size() <= 50


class TestModificationCacheAdversarial:
    """Adversarial tests for ModificationCheckCache."""

    def setup_method(self) -> None:
        """Reset global cache before each test."""
        reset_modification_cache()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_modification_cache()

    def test_concurrent_set_same_gid(self) -> None:
        """Test concurrent sets to the same GID."""
        cache = ModificationCheckCache(ttl=10.0)
        errors: list[Exception] = []
        results: list[str] = []

        def set_modification(thread_id: int) -> None:
            try:
                for i in range(100):
                    cache.set("shared_gid", f"2025-01-01T{thread_id:02d}:{i:02d}:00Z")
                check = cache.get("shared_gid")
                if check:
                    results.append(check.modified_at)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=set_modification, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0
        # All threads should have gotten some result
        assert len(results) == 10

    def test_get_during_clear(self) -> None:
        """Test get operations during clear."""
        cache = ModificationCheckCache(ttl=10.0)

        # Pre-populate
        for i in range(100):
            cache.set(f"gid_{i}", f"2025-01-01T00:00:00Z")

        errors: list[Exception] = []

        def do_gets() -> None:
            try:
                for i in range(100):
                    cache.get(f"gid_{i % 100}")
            except Exception as e:
                errors.append(e)

        def do_clear() -> None:
            try:
                for _ in range(10):
                    cache.clear()
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=do_gets) for _ in range(5)]
        threads.append(threading.Thread(target=do_clear))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0

    def test_expired_cleanup_during_access(self) -> None:
        """Test cleanup_expired during concurrent access."""
        cache = ModificationCheckCache(ttl=0.01)  # 10ms TTL

        errors: list[Exception] = []

        def set_and_cleanup() -> None:
            try:
                for i in range(100):
                    cache.set(f"gid_{i}", "2025-01-01T00:00:00Z")
                    time.sleep(0.001)
                    cache.cleanup_expired()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=set_and_cleanup) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0


class TestMetricsAdversarial:
    """Adversarial tests for CacheMetrics."""

    def test_callback_that_raises(self) -> None:
        """Test that callback exceptions don't break metrics."""
        metrics = CacheMetrics()

        def bad_callback(event: CacheEvent) -> None:
            raise RuntimeError("Callback error!")

        metrics.on_event(bad_callback)

        # This should not raise
        metrics.record_hit(latency_ms=1.0)
        metrics.record_miss(latency_ms=1.0)
        metrics.record_write(latency_ms=1.0)

        assert metrics.hits == 1
        assert metrics.misses == 1
        assert metrics.writes == 1

    def test_slow_callback_doesnt_block(self) -> None:
        """Test that slow callbacks don't cause issues."""
        metrics = CacheMetrics()
        callback_count = 0

        def slow_callback(event: CacheEvent) -> None:
            nonlocal callback_count
            time.sleep(0.01)  # 10ms delay
            callback_count += 1

        metrics.on_event(slow_callback)

        start = time.time()
        for _ in range(10):
            metrics.record_hit(latency_ms=1.0)
        elapsed = time.time() - start

        # 10 callbacks * 10ms = ~100ms minimum
        assert elapsed >= 0.1
        assert callback_count == 10

    def test_concurrent_metric_updates(self) -> None:
        """Test concurrent updates to all metric types."""
        metrics = CacheMetrics()
        errors: list[Exception] = []

        def update_metrics() -> None:
            try:
                for _ in range(100):
                    metrics.record_hit(latency_ms=1.0)
                    metrics.record_miss(latency_ms=1.0)
                    metrics.record_write(latency_ms=1.0)
                    metrics.record_eviction()
                    metrics.record_error()
                    metrics.record_overflow_skip("task")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=update_metrics) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0
        assert metrics.hits == 1000
        assert metrics.misses == 1000
        assert metrics.writes == 1000
        assert metrics.evictions == 1000
        assert metrics.errors == 1000

    def test_snapshot_during_updates(self) -> None:
        """Test snapshot during concurrent updates."""
        metrics = CacheMetrics()
        errors: list[Exception] = []
        snapshots: list[dict[str, Any]] = []

        def update_metrics() -> None:
            try:
                for _ in range(100):
                    metrics.record_hit(latency_ms=1.0)
            except Exception as e:
                errors.append(e)

        def take_snapshots() -> None:
            try:
                for _ in range(20):
                    snapshots.append(metrics.snapshot())
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=update_metrics) for _ in range(5)]
        threads.append(threading.Thread(target=take_snapshots))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0
        assert len(snapshots) == 20
        # Each snapshot should be internally consistent
        for snap in snapshots:
            assert "hits" in snap
            assert "misses" in snap


class TestSettingsAdversarial:
    """Adversarial tests for cache settings."""

    def test_get_ttl_with_none_project(self) -> None:
        """Test TTL resolution with None project GID."""
        settings = TTLSettings(default_ttl=300, project_ttls={"123": 60})
        ttl = settings.get_ttl(project_gid=None)
        assert ttl == 300

    def test_get_ttl_with_empty_project(self) -> None:
        """Test TTL resolution with empty string project GID."""
        settings = TTLSettings(default_ttl=300, project_ttls={"123": 60})
        ttl = settings.get_ttl(project_gid="")
        assert ttl == 300  # Empty string not in project_ttls

    def test_overflow_settings_zero_threshold(self) -> None:
        """Test overflow settings with zero threshold."""
        settings = OverflowSettings(subtasks=0)
        # Zero means no subtasks allowed before overflow
        assert settings.subtasks == 0

    def test_cache_settings_all_defaults(self) -> None:
        """Test CacheSettings with all defaults."""
        settings = CacheSettings()
        assert settings.enabled is True
        assert settings.ttl.default_ttl == 300
        assert settings.overflow.subtasks == 40


class TestVersionComparisonEdgeCases:
    """Edge cases for version comparison."""

    def test_same_instant_different_timezones(self) -> None:
        """Test comparing same instant in different timezones."""
        # These represent the same instant
        utc_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        offset_time_str = "2025-01-15T17:30:00+05:30"  # Same instant

        # Parse the offset time
        offset_dt = parse_version(offset_time_str)

        # They should be equal when comparing
        result = compare_versions(utc_time, offset_dt)
        assert result == 0

    def test_microsecond_precision(self) -> None:
        """Test version comparison at microsecond precision."""
        v1 = datetime(2025, 1, 15, 12, 0, 0, 123456, tzinfo=timezone.utc)
        v2 = datetime(2025, 1, 15, 12, 0, 0, 123457, tzinfo=timezone.utc)

        assert is_stale(v1, v2)  # v1 is 1 microsecond older
        assert is_current(v2, v1)  # v2 is newer

    def test_is_current_with_future_cached(self) -> None:
        """Test is_current when cached version is in future (edge case)."""
        cached = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Cached is "from the future" - should be considered current
        assert is_current(cached, current)


class TestStalenessEdgeCases:
    """Edge cases for staleness detection."""

    def test_check_entry_staleness_strict_no_version(self) -> None:
        """Test STRICT freshness with no current version provided."""
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
            ttl=300,
        )

        # STRICT mode with no current version should be stale
        is_stale_result = check_entry_staleness(entry, None, Freshness.STRICT)
        assert is_stale_result is True

    def test_check_entry_staleness_eventual_no_version(self) -> None:
        """Test EVENTUAL freshness with no current version provided."""
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
            ttl=300,
        )

        # EVENTUAL mode should not be stale if not expired
        is_stale_result = check_entry_staleness(entry, None, Freshness.EVENTUAL)
        assert is_stale_result is False

    def test_partition_empty_dict(self) -> None:
        """Test partition with empty staleness dict."""
        stale, current = partition_by_staleness({})
        assert stale == []
        assert current == []

    def test_partition_all_stale(self) -> None:
        """Test partition when all are stale."""
        staleness = {"a": True, "b": True, "c": True}
        stale, current = partition_by_staleness(staleness)
        assert set(stale) == {"a", "b", "c"}
        assert current == []

    def test_partition_all_current(self) -> None:
        """Test partition when all are current."""
        staleness = {"a": False, "b": False, "c": False}
        stale, current = partition_by_staleness(staleness)
        assert stale == []
        assert set(current) == {"a", "b", "c"}


class TestInMemoryCacheAdversarial:
    """Adversarial tests for EnhancedInMemoryCacheProvider."""

    def test_get_nonexistent_key(self) -> None:
        """Test get with key that doesn't exist."""
        cache = EnhancedInMemoryCacheProvider()
        result = cache.get("nonexistent_key_that_surely_does_not_exist")
        assert result is None

    def test_get_versioned_wrong_type(self) -> None:
        """Test get_versioned with wrong entry type."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        entry = CacheEntry(
            key="123",
            data={"type": "task"},
            entry_type=EntryType.TASK,
            version=now,
        )
        cache.set_versioned("123", entry)

        # Try to get as SUBTASKS
        result = cache.get_versioned("123", EntryType.SUBTASKS)
        assert result is None  # Different entry type

    def test_delete_nonexistent_key(self) -> None:
        """Test delete with nonexistent key doesn't raise."""
        cache = EnhancedInMemoryCacheProvider()
        cache.delete("nonexistent")  # Should not raise

    def test_invalidate_nonexistent_key(self) -> None:
        """Test invalidate with nonexistent key doesn't raise."""
        cache = EnhancedInMemoryCacheProvider()
        cache.invalidate("nonexistent")  # Should not raise

    def test_clear_empty_cache(self) -> None:
        """Test clear on empty cache doesn't raise."""
        cache = EnhancedInMemoryCacheProvider()
        cache.clear()  # Should not raise
        assert cache.size() == 0

    def test_size_after_expiration(self) -> None:
        """Test size includes expired entries until cleaned."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        # Add entry with very short TTL
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=now,
            ttl=0,  # Expires immediately
        )
        cache.set_versioned("123", entry)

        # Size may include it until get triggers cleanup
        initial_size = cache.size()

        # Wait and access to trigger cleanup
        time.sleep(0.1)
        cache.get_versioned("123", EntryType.TASK)  # Should trigger cleanup

        # Entry should be gone now
        result = cache.get_versioned("123", EntryType.TASK)
        assert result is None

    def test_batch_operations_empty_list(self) -> None:
        """Test batch operations with empty lists."""
        cache = EnhancedInMemoryCacheProvider()

        # get_batch with empty list
        result = cache.get_batch([], EntryType.TASK)
        assert result == {}

        # set_batch with empty dict
        cache.set_batch({})  # Should not raise

    def test_special_characters_in_key(self) -> None:
        """Test handling of special characters in cache keys."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        special_keys = [
            "key with spaces",
            "key:with:colons",
            "key/with/slashes",
            "key\\with\\backslashes",
            "key\twith\ttabs",
            "key\nwith\nnewlines",
        ]

        for key in special_keys:
            entry = CacheEntry(
                key=key,
                data={"key": key},
                entry_type=EntryType.TASK,
                version=now,
            )
            cache.set_versioned(key, entry)
            result = cache.get_versioned(key, EntryType.TASK)
            assert result is not None
            assert result.data["key"] == key


class TestFetchModificationsAdversarial:
    """Adversarial tests for fetch_task_modifications."""

    def setup_method(self) -> None:
        """Reset global cache before each test."""
        reset_modification_cache()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_modification_cache()

    @pytest.mark.asyncio
    async def test_empty_gids_list(self) -> None:
        """Test fetch with empty GID list."""
        call_count = 0

        async def mock_api(gids: list[str]) -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            return {}

        result = await fetch_task_modifications([], mock_api)
        assert result == {}
        assert call_count == 0  # No API call for empty list

    @pytest.mark.asyncio
    async def test_api_returns_partial(self) -> None:
        """Test handling when API returns fewer GIDs than requested."""
        async def mock_api(gids: list[str]) -> dict[str, str]:
            # Only return half
            return {gid: "2025-01-01T00:00:00Z" for gid in gids[: len(gids) // 2]}

        result = await fetch_task_modifications(["1", "2", "3", "4"], mock_api)
        # Should have results for what API returned
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_api_returns_extra(self) -> None:
        """Test handling when API returns more GIDs than requested."""
        async def mock_api(gids: list[str]) -> dict[str, str]:
            result = {gid: "2025-01-01T00:00:00Z" for gid in gids}
            result["extra_gid"] = "2025-01-01T00:00:00Z"  # Extra
            return result

        result = await fetch_task_modifications(["1", "2"], mock_api)
        # Should include the extra
        assert "extra_gid" in result


class TestRecursiveCallbackProtection:
    """Test protection against recursive callbacks."""

    def test_callback_that_triggers_more_events(self) -> None:
        """Test callback that triggers cache operations."""
        cache = EnhancedInMemoryCacheProvider()
        metrics = cache.get_metrics()
        callback_depth = 0
        max_depth = 0

        def recursive_callback(event: CacheEvent) -> None:
            nonlocal callback_depth, max_depth
            callback_depth += 1
            max_depth = max(max_depth, callback_depth)

            # This would cause infinite recursion without protection
            if callback_depth < 5:
                # Trigger another event
                cache.get("trigger")  # This triggers another event

            callback_depth -= 1

        metrics.on_event(recursive_callback)

        # Initial trigger
        cache.set("key", {"data": "value"})

        # Should not have infinite recursion
        # Max depth depends on implementation - just verify no crash
        assert max_depth >= 1


class TestMemoryManagement:
    """Tests for memory management under stress."""

    def test_no_memory_leak_on_repeated_clear(self) -> None:
        """Test that repeated clear doesn't leak memory."""
        cache = EnhancedInMemoryCacheProvider(max_size=1000)
        now = datetime.now(timezone.utc)

        # Get initial memory
        gc.collect()

        for cycle in range(10):
            # Fill cache
            for i in range(100):
                entry = CacheEntry(
                    key=f"key_{i}",
                    data={"data": "x" * 1000},
                    entry_type=EntryType.TASK,
                    version=now,
                )
                cache.set_versioned(f"key_{i}", entry)

            # Clear cache
            cache.clear()
            gc.collect()

        # After all cycles, cache should be empty
        assert cache.size() == 0
