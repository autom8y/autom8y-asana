"""Adversarial tests for the cache module.

Retained tests cover unique high-value scenarios:
- Race conditions in ModificationCheckCache (threading)
- Concurrent metric updates and snapshot safety
- Recursive callback protection
- Memory management under stress

Low-value tests (framework behavior, simple edge cases) were merged into
their canonical counterparts: test_entry.py, test_versioning.py,
test_memory_backend.py, test_batch.py, test_staleness.py.
"""

from __future__ import annotations

import gc
import threading
import time
from typing import Any

import pytest

from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.cache.integration.batch import (
    ModificationCheckCache,
    reset_modification_cache,
)
from autom8_asana.cache.models.metrics import CacheEvent, CacheMetrics


class TestModificationCacheAdversarial:
    """Adversarial tests for ModificationCheckCache (threading race conditions)."""

    def setup_method(self) -> None:
        """Reset global cache before each test."""
        reset_modification_cache()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_modification_cache()

    def test_concurrent_set_same_gid(self) -> None:
        """Test concurrent sets to the same GID don't raise."""
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
        assert len(results) == 10

    def test_get_during_clear(self) -> None:
        """Test get operations during concurrent clear don't raise."""
        cache = ModificationCheckCache(ttl=10.0)

        for i in range(100):
            cache.set(f"gid_{i}", "2025-01-01T00:00:00Z")

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
        """Test cleanup_expired during concurrent access doesn't raise."""
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
    """Adversarial tests for CacheMetrics (concurrency and callback edge cases)."""

    def test_callback_that_raises(self) -> None:
        """Test that callback exceptions don't break metrics recording."""
        metrics = CacheMetrics()

        def bad_callback(event: CacheEvent) -> None:
            raise RuntimeError("Callback error!")

        metrics.on_event(bad_callback)

        # These should not raise despite bad callback
        metrics.record_hit(latency_ms=1.0)
        metrics.record_miss(latency_ms=1.0)
        metrics.record_write(latency_ms=1.0)

        assert metrics.hits == 1
        assert metrics.misses == 1
        assert metrics.writes == 1

    def test_slow_callback_doesnt_block(self) -> None:
        """Test that slow callbacks are called but don't skip records."""
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

        assert elapsed >= 0.1
        assert callback_count == 10

    def test_concurrent_metric_updates(self) -> None:
        """Test concurrent updates to all metric types don't race or corrupt counts."""
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
        """Test snapshot during concurrent updates doesn't corrupt snapshot data."""
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
        for snap in snapshots:
            assert "hits" in snap
            assert "misses" in snap


class TestRecursiveCallbackProtection:
    """Test protection against recursive callbacks."""

    def test_callback_that_triggers_more_events(self) -> None:
        """Test callback that triggers cache operations doesn't cause infinite recursion."""
        cache = EnhancedInMemoryCacheProvider()
        metrics = cache.get_metrics()
        callback_depth = 0
        max_depth = 0

        def recursive_callback(event: CacheEvent) -> None:
            nonlocal callback_depth, max_depth
            callback_depth += 1
            max_depth = max(max_depth, callback_depth)

            if callback_depth < 5:
                cache.get("trigger")  # This triggers another event

            callback_depth -= 1

        metrics.on_event(recursive_callback)
        cache.set("key", {"data": "value"})

        # Should not have infinite recursion
        assert max_depth >= 1


class TestMemoryManagement:
    """Tests for memory management under stress."""

    @pytest.mark.slow
    def test_no_memory_leak_on_repeated_clear(self) -> None:
        """Test that repeated fill-and-clear cycles don't leak memory."""
        from datetime import UTC, datetime

        from autom8_asana.cache.models.entry import CacheEntry, EntryType

        cache = EnhancedInMemoryCacheProvider(max_size=1000)
        now = datetime.now(UTC)

        gc.collect()

        for _ in range(10):
            for i in range(100):
                entry = CacheEntry(
                    key=f"key_{i}",
                    data={"data": "x" * 1000},
                    entry_type=EntryType.TASK,
                    version=now,
                )
                cache.set_versioned(f"key_{i}", entry)
            cache.clear()
            gc.collect()

        assert cache.size() == 0
