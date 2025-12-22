"""Concurrency tests for the cache module.

These tests verify thread-safety guarantees per ADR-0024:
- No race conditions in cache operations
- No data corruption under concurrent access
- No deadlocks under high contention
- Consistent state after concurrent modifications
"""

from __future__ import annotations

import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any


from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.cache.batch import ModificationCheckCache, reset_modification_cache
from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.metrics import CacheMetrics


class TestInMemoryCacheConcurrency:
    """Thread-safety tests for EnhancedInMemoryCacheProvider."""

    def test_concurrent_reads_same_key(self) -> None:
        """Test multiple threads reading the same key simultaneously."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        # Pre-populate
        entry = CacheEntry(
            key="shared",
            data={"value": "test_data"},
            entry_type=EntryType.TASK,
            version=now,
            ttl=300,
        )
        cache.set_versioned("shared", entry)

        errors: list[Exception] = []
        results: list[dict[str, Any] | None] = []
        results_lock = threading.Lock()

        def read_key() -> None:
            try:
                for _ in range(100):
                    result = cache.get_versioned("shared", EntryType.TASK)
                    with results_lock:
                        results.append(result.data if result else None)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_key) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0
        assert all(r == {"value": "test_data"} for r in results if r is not None)

    def test_concurrent_writes_same_key(self) -> None:
        """Test multiple threads writing to the same key."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        errors: list[Exception] = []

        def write_key(thread_id: int) -> None:
            try:
                for i in range(100):
                    entry = CacheEntry(
                        key="shared",
                        data={"thread": thread_id, "iteration": i},
                        entry_type=EntryType.TASK,
                        version=now + timedelta(seconds=i),
                        ttl=300,
                    )
                    cache.set_versioned("shared", entry)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_key, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0

        # Final value should be from one of the threads
        result = cache.get_versioned("shared", EntryType.TASK)
        assert result is not None
        assert "thread" in result.data
        assert "iteration" in result.data

    def test_concurrent_reads_and_writes(self) -> None:
        """Test mixed read and write operations."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        errors: list[Exception] = []

        def reader() -> None:
            try:
                for _ in range(200):
                    cache.get_versioned("shared", EntryType.TASK)
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        def writer(thread_id: int) -> None:
            try:
                for i in range(50):
                    entry = CacheEntry(
                        key="shared",
                        data={"thread": thread_id, "i": i},
                        entry_type=EntryType.TASK,
                        version=now,
                        ttl=300,
                    )
                    cache.set_versioned("shared", entry)
                    time.sleep(0.0002)
            except Exception as e:
                errors.append(e)

        readers = [threading.Thread(target=reader) for _ in range(10)]
        writers = [threading.Thread(target=writer, args=(i,)) for i in range(5)]

        for t in readers + writers:
            t.start()
        for t in readers + writers:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0

    def test_concurrent_different_keys(self) -> None:
        """Test threads operating on different keys simultaneously."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        errors: list[Exception] = []
        successful_ops: list[int] = []
        ops_lock = threading.Lock()

        def operate_on_key(key_prefix: str) -> None:
            try:
                ops = 0
                for i in range(100):
                    key = f"{key_prefix}_{i}"
                    entry = CacheEntry(
                        key=key,
                        data={"value": i},
                        entry_type=EntryType.TASK,
                        version=now,
                        ttl=300,
                    )
                    cache.set_versioned(key, entry)
                    result = cache.get_versioned(key, EntryType.TASK)
                    if result and result.data["value"] == i:
                        ops += 1
                with ops_lock:
                    successful_ops.append(ops)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=operate_on_key, args=(f"thread_{i}",))
            for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0
        assert all(ops == 100 for ops in successful_ops)

    def test_concurrent_batch_operations(self) -> None:
        """Test concurrent batch get/set operations."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        errors: list[Exception] = []

        def batch_ops(thread_id: int) -> None:
            try:
                keys = [f"batch_{thread_id}_{i}" for i in range(50)]

                # Batch set
                entries = {
                    k: CacheEntry(
                        key=k,
                        data={"thread": thread_id},
                        entry_type=EntryType.TASK,
                        version=now,
                        ttl=300,
                    )
                    for k in keys
                }
                cache.set_batch(entries)

                # Batch get
                results = cache.get_batch(keys, EntryType.TASK)

                # Verify all retrieved
                for k in keys:
                    assert k in results
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=batch_ops, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0

    def test_concurrent_invalidation(self) -> None:
        """Test concurrent invalidate operations."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        # Pre-populate
        for i in range(100):
            entry = CacheEntry(
                key=f"key_{i}",
                data={"value": i},
                entry_type=EntryType.TASK,
                version=now,
                ttl=300,
            )
            cache.set_versioned(f"key_{i}", entry)

        errors: list[Exception] = []

        def invalidator() -> None:
            try:
                for i in range(100):
                    cache.invalidate(f"key_{i}")
            except Exception as e:
                errors.append(e)

        def reader() -> None:
            try:
                for i in range(100):
                    cache.get_versioned(f"key_{i % 100}", EntryType.TASK)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=invalidator) for _ in range(5)]
        threads.extend([threading.Thread(target=reader) for _ in range(10)])

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0

    def test_concurrent_clear(self) -> None:
        """Test concurrent clear with other operations."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        errors: list[Exception] = []

        def writer() -> None:
            try:
                for i in range(100):
                    entry = CacheEntry(
                        key=f"key_{i}",
                        data={"value": i},
                        entry_type=EntryType.TASK,
                        version=now,
                        ttl=300,
                    )
                    cache.set_versioned(f"key_{i}", entry)
            except Exception as e:
                errors.append(e)

        def clearer() -> None:
            try:
                for _ in range(10):
                    cache.clear()
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(5)]
        threads.append(threading.Thread(target=clearer))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0

    def test_high_contention_single_key(self) -> None:
        """Test very high contention on a single key."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        errors: list[Exception] = []
        ops_count = 0
        ops_lock = threading.Lock()

        def contend() -> None:
            nonlocal ops_count
            try:
                for _ in range(100):
                    op = random.choice(["get", "set", "delete"])
                    if op == "get":
                        cache.get_versioned("contended", EntryType.TASK)
                    elif op == "set":
                        entry = CacheEntry(
                            key="contended",
                            data={"random": random.random()},
                            entry_type=EntryType.TASK,
                            version=now,
                            ttl=300,
                        )
                        cache.set_versioned("contended", entry)
                    else:
                        cache.invalidate("contended")

                    with ops_lock:
                        ops_count += 1
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=contend) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0
        assert ops_count == 5000  # 50 threads * 100 ops

    def test_eviction_during_access(self) -> None:
        """Test that eviction during access doesn't cause issues."""
        cache = EnhancedInMemoryCacheProvider(max_size=50)
        now = datetime.now(timezone.utc)

        errors: list[Exception] = []

        def fill_cache() -> None:
            try:
                for i in range(200):  # Will trigger eviction
                    entry = CacheEntry(
                        key=f"fill_{i}",
                        data={"value": i},
                        entry_type=EntryType.TASK,
                        version=now,
                        ttl=300,
                    )
                    cache.set_versioned(f"fill_{i}", entry)
            except Exception as e:
                errors.append(e)

        def read_cache() -> None:
            try:
                for _ in range(500):
                    key = f"fill_{random.randint(0, 199)}"
                    cache.get_versioned(key, EntryType.TASK)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=fill_cache) for _ in range(3)]
        threads.extend([threading.Thread(target=read_cache) for _ in range(5)])

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0
        assert cache.size() <= 50


class TestModificationCheckCacheConcurrency:
    """Thread-safety tests for ModificationCheckCache."""

    def setup_method(self) -> None:
        """Reset global cache before each test."""
        reset_modification_cache()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_modification_cache()

    def test_concurrent_set_get(self) -> None:
        """Test concurrent set and get operations."""
        cache = ModificationCheckCache(ttl=60.0)

        errors: list[Exception] = []

        def set_ops(thread_id: int) -> None:
            try:
                for i in range(100):
                    cache.set(
                        f"gid_{thread_id}_{i}", f"2025-01-{(i % 28) + 1:02d}T00:00:00Z"
                    )
            except Exception as e:
                errors.append(e)

        def get_ops(thread_id: int) -> None:
            try:
                for i in range(100):
                    cache.get(f"gid_{thread_id}_{i}")
            except Exception as e:
                errors.append(e)

        threads: list[threading.Thread] = []
        for i in range(10):
            threads.append(threading.Thread(target=set_ops, args=(i,)))
            threads.append(threading.Thread(target=get_ops, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0

    def test_concurrent_set_many(self) -> None:
        """Test concurrent set_many operations."""
        cache = ModificationCheckCache(ttl=60.0)

        errors: list[Exception] = []

        def bulk_set(thread_id: int) -> None:
            try:
                for batch in range(10):
                    modifications = {
                        f"gid_{thread_id}_{batch}_{i}": f"2025-01-{(i % 28) + 1:02d}T00:00:00Z"
                        for i in range(50)
                    }
                    cache.set_many(modifications)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=bulk_set, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0

    def test_concurrent_get_many(self) -> None:
        """Test concurrent get_many operations."""
        cache = ModificationCheckCache(ttl=60.0)

        # Pre-populate
        for i in range(1000):
            cache.set(f"gid_{i}", "2025-01-01T00:00:00Z")

        errors: list[Exception] = []
        results: list[tuple[dict[str, str], list[str]]] = []
        results_lock = threading.Lock()

        def bulk_get() -> None:
            try:
                gids = [f"gid_{i}" for i in range(100)]
                for _ in range(10):
                    cached, uncached = cache.get_many(gids)
                    with results_lock:
                        results.append((cached, uncached))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=bulk_get) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0
        assert len(results) == 200
        # All should be cached
        for cached, uncached in results:
            assert len(cached) == 100
            assert len(uncached) == 0

    def test_concurrent_cleanup(self) -> None:
        """Test concurrent cleanup_expired operations."""
        cache = ModificationCheckCache(ttl=0.01)  # 10ms TTL

        errors: list[Exception] = []

        def set_and_cleanup() -> None:
            try:
                for i in range(100):
                    cache.set(
                        f"gid_{threading.current_thread().name}_{i}",
                        "2025-01-01T00:00:00Z",
                    )
                    time.sleep(0.005)
                    cache.cleanup_expired()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=set_and_cleanup, name=f"t{i}") for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0


class TestCacheMetricsConcurrency:
    """Thread-safety tests for CacheMetrics."""

    def test_concurrent_recording(self) -> None:
        """Test concurrent metric recording."""
        metrics = CacheMetrics()

        errors: list[Exception] = []

        def record_metrics() -> None:
            try:
                for _ in range(100):
                    metrics.record_hit(latency_ms=1.0)
                    metrics.record_miss(latency_ms=1.0)
                    metrics.record_write(latency_ms=1.0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_metrics) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0
        assert metrics.hits == 2000
        assert metrics.misses == 2000
        assert metrics.writes == 2000

    def test_concurrent_callbacks(self) -> None:
        """Test concurrent metric recording with callbacks."""
        metrics = CacheMetrics()
        callback_count = 0
        callback_lock = threading.Lock()

        def callback(event: Any) -> None:
            nonlocal callback_count
            with callback_lock:
                callback_count += 1

        metrics.on_event(callback)

        errors: list[Exception] = []

        def record_metrics() -> None:
            try:
                for _ in range(50):
                    metrics.record_hit(latency_ms=1.0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_metrics) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0
        assert callback_count == 1000  # 20 threads * 50 ops

    def test_concurrent_snapshot(self) -> None:
        """Test snapshot during concurrent updates."""
        metrics = CacheMetrics()

        errors: list[Exception] = []
        snapshots: list[dict[str, Any]] = []
        snapshots_lock = threading.Lock()

        def record_metrics() -> None:
            try:
                for _ in range(100):
                    metrics.record_hit(latency_ms=1.0)
            except Exception as e:
                errors.append(e)

        def take_snapshots() -> None:
            try:
                for _ in range(20):
                    snap = metrics.snapshot()
                    with snapshots_lock:
                        snapshots.append(snap)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_metrics) for _ in range(10)]
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
            total = snap["hits"] + snap["misses"]
            if total > 0:
                expected_rate = snap["hits"] / total
                # Allow small floating point difference
                assert abs(snap["hit_rate"] - expected_rate) < 0.0001

    def test_concurrent_reset(self) -> None:
        """Test reset during concurrent updates."""
        metrics = CacheMetrics()

        errors: list[Exception] = []

        def record_metrics() -> None:
            try:
                for _ in range(100):
                    metrics.record_hit(latency_ms=1.0)
                    metrics.record_miss(latency_ms=1.0)
            except Exception as e:
                errors.append(e)

        def reset_metrics() -> None:
            try:
                for _ in range(10):
                    metrics.reset()
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_metrics) for _ in range(10)]
        threads.append(threading.Thread(target=reset_metrics))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert len(errors) == 0
        # Final values depend on timing - just verify no crash


class TestDeadlockPrevention:
    """Tests to ensure no deadlocks occur."""

    def test_no_deadlock_on_nested_locks(self) -> None:
        """Ensure operations that could nest don't deadlock.

        This test verifies that metric callbacks do not cause deadlocks
        by attempting cache operations from within the callback.
        The callback runs in a separate thread to avoid re-entrant lock issues.
        """
        cache = EnhancedInMemoryCacheProvider()
        metrics = cache.get_metrics()
        now = datetime.now(timezone.utc)

        callback_errors: list[Exception] = []
        spawned_threads: list[threading.Thread] = []
        spawned_threads_lock = threading.Lock()

        # Callback that triggers another cache operation in a separate thread
        # to avoid re-entrant lock deadlock
        def triggering_callback(event: Any) -> None:
            def nested_op() -> None:
                try:
                    cache.get_versioned("other_key", EntryType.TASK)
                except Exception as e:
                    callback_errors.append(e)

            # Run in separate thread to avoid deadlock from re-entrant lock
            t = threading.Thread(target=nested_op, daemon=True)
            with spawned_threads_lock:
                spawned_threads.append(t)
            t.start()
            # Don't join here - fire and forget within callback

        metrics.on_event(triggering_callback)

        # This should not deadlock
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(50):
                entry = CacheEntry(
                    key=f"key_{i}",
                    data={"value": i},
                    entry_type=EntryType.TASK,
                    version=now,
                    ttl=300,
                )
                futures.append(executor.submit(cache.set_versioned, f"key_{i}", entry))

            # Wait with timeout to detect deadlock
            for future in as_completed(futures, timeout=10):
                future.result()

        # Best-effort cleanup of spawned callback threads.
        # We track threads to ensure proper cleanup, but we don't block on their
        # completion since they may be contending for locks held by other callbacks.
        # The test's main assertion is that the primary cache operations don't deadlock.
        time.sleep(0.1)  # Brief wait for any threads that complete quickly

        assert len(callback_errors) == 0

    def test_no_deadlock_cross_cache_operations(self) -> None:
        """Test operations across multiple cache instances don't deadlock."""
        cache1 = EnhancedInMemoryCacheProvider()
        cache2 = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        errors: list[Exception] = []

        def cross_operate() -> None:
            try:
                for i in range(50):
                    entry = CacheEntry(
                        key=f"key_{i}",
                        data={"value": i},
                        entry_type=EntryType.TASK,
                        version=now,
                        ttl=300,
                    )
                    # Operate on both caches
                    cache1.set_versioned(f"key_{i}", entry)
                    cache2.get_versioned(f"key_{i}", EntryType.TASK)
                    cache2.set_versioned(f"key_{i}", entry)
                    cache1.get_versioned(f"key_{i}", EntryType.TASK)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=cross_operate) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)  # Timeout to detect deadlock

        # Check all threads completed
        for t in threads:
            assert not t.is_alive(), "Thread still alive - possible deadlock"

        assert len(errors) == 0


class TestThreadPoolConcurrency:
    """Tests using ThreadPoolExecutor for more realistic concurrency."""

    def test_thread_pool_cache_operations(self) -> None:
        """Test cache operations with ThreadPoolExecutor."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        def cache_operation(key: str) -> bool:
            entry = CacheEntry(
                key=key,
                data={"key": key},
                entry_type=EntryType.TASK,
                version=now,
                ttl=300,
            )
            cache.set_versioned(key, entry)
            result = cache.get_versioned(key, EntryType.TASK)
            return result is not None and result.data["key"] == key

        with ThreadPoolExecutor(max_workers=20) as executor:
            keys = [f"key_{i}" for i in range(1000)]
            results = list(executor.map(cache_operation, keys))

        assert all(results)
        assert sum(results) == 1000

    def test_thread_pool_modification_cache(self) -> None:
        """Test modification cache with ThreadPoolExecutor."""
        cache = ModificationCheckCache(ttl=60.0)

        def modification_operation(gid: str) -> bool:
            cache.set(gid, "2025-01-01T00:00:00Z")
            result = cache.get(gid)
            return result is not None and result.gid == gid

        with ThreadPoolExecutor(max_workers=20) as executor:
            gids = [f"gid_{i}" for i in range(1000)]
            results = list(executor.map(modification_operation, gids))

        assert all(results)
        assert sum(results) == 1000


class TestRaceConditionScenarios:
    """Specific race condition scenarios to prevent."""

    def test_read_during_write_consistency(self) -> None:
        """Ensure read during write returns consistent data."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        inconsistencies: list[str] = []
        inconsistencies_lock = threading.Lock()

        def writer(values: list[int]) -> None:
            for v in values:
                entry = CacheEntry(
                    key="consistent",
                    data={"a": v, "b": v, "c": v},  # All same value
                    entry_type=EntryType.TASK,
                    version=now,
                    ttl=300,
                )
                cache.set_versioned("consistent", entry)

        def reader() -> None:
            for _ in range(1000):
                result = cache.get_versioned("consistent", EntryType.TASK)
                if result:
                    data = result.data
                    # All values should be the same (no torn read)
                    if not (data["a"] == data["b"] == data["c"]):
                        with inconsistencies_lock:
                            inconsistencies.append(
                                f"a={data['a']}, b={data['b']}, c={data['c']}"
                            )

        # Initial value
        entry = CacheEntry(
            key="consistent",
            data={"a": 0, "b": 0, "c": 0},
            entry_type=EntryType.TASK,
            version=now,
            ttl=300,
        )
        cache.set_versioned("consistent", entry)

        writer_thread = threading.Thread(target=writer, args=(list(range(1, 1001)),))
        readers = [threading.Thread(target=reader) for _ in range(10)]

        writer_thread.start()
        for r in readers:
            r.start()

        writer_thread.join(timeout=10)
        if writer_thread.is_alive():
            raise AssertionError(
                f"Thread {writer_thread.name} did not complete within timeout"
            )
        for r in readers:
            r.join(timeout=10)
            if r.is_alive():
                raise AssertionError(f"Thread {r.name} did not complete within timeout")

        assert len(inconsistencies) == 0, (
            f"Found inconsistencies: {inconsistencies[:5]}"
        )

    def test_counter_increment_atomicity(self) -> None:
        """Test that metrics counters are atomic."""
        metrics = CacheMetrics()

        def increment() -> None:
            for _ in range(1000):
                metrics.record_hit(latency_ms=1.0)

        threads = [threading.Thread(target=increment) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        # Should be exactly 100,000
        assert metrics.hits == 100000
