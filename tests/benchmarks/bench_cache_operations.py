#!/usr/bin/env python3
"""Benchmark script for cache operations.

Measures latency and throughput of basic cache operations.

Usage:
    python -m tests.benchmarks.bench_cache_operations

Output:
    Timing data for cache hit, miss, and write operations.
"""

from __future__ import annotations

import statistics
import time
from datetime import datetime, timezone
from typing import NamedTuple

from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.cache.entry import CacheEntry, EntryType


class BenchmarkResult(NamedTuple):
    """Result of a benchmark run."""

    operation: str
    iterations: int
    total_time_ms: float
    avg_latency_us: float
    p50_latency_us: float
    p95_latency_us: float
    p99_latency_us: float
    throughput_ops_per_sec: float


def benchmark_cache_hit(
    cache: EnhancedInMemoryCacheProvider, iterations: int = 10000
) -> BenchmarkResult:
    """Benchmark cache hit latency.

    Pre-populates cache, then measures read latency.
    """
    now = datetime.now(timezone.utc)

    # Pre-populate
    entry = CacheEntry(
        key="benchmark_key",
        data={"field1": "value1", "field2": 12345, "nested": {"a": 1, "b": 2}},
        entry_type=EntryType.TASK,
        version=now,
        ttl=3600,
    )
    cache.set_versioned("benchmark_key", entry)

    latencies_us: list[float] = []

    for _ in range(iterations):
        start = time.perf_counter_ns()
        cache.get_versioned("benchmark_key", EntryType.TASK)
        end = time.perf_counter_ns()
        latencies_us.append((end - start) / 1000)  # Convert to microseconds

    total_time_ms = sum(latencies_us) / 1000

    return BenchmarkResult(
        operation="cache_hit",
        iterations=iterations,
        total_time_ms=total_time_ms,
        avg_latency_us=statistics.mean(latencies_us),
        p50_latency_us=statistics.median(latencies_us),
        p95_latency_us=sorted(latencies_us)[int(iterations * 0.95)],
        p99_latency_us=sorted(latencies_us)[int(iterations * 0.99)],
        throughput_ops_per_sec=iterations / (total_time_ms / 1000),
    )


def benchmark_cache_miss(
    cache: EnhancedInMemoryCacheProvider, iterations: int = 10000
) -> BenchmarkResult:
    """Benchmark cache miss latency.

    Measures read latency for non-existent keys.
    """
    latencies_us: list[float] = []

    for i in range(iterations):
        start = time.perf_counter_ns()
        cache.get_versioned(f"nonexistent_key_{i}", EntryType.TASK)
        end = time.perf_counter_ns()
        latencies_us.append((end - start) / 1000)

    total_time_ms = sum(latencies_us) / 1000

    return BenchmarkResult(
        operation="cache_miss",
        iterations=iterations,
        total_time_ms=total_time_ms,
        avg_latency_us=statistics.mean(latencies_us),
        p50_latency_us=statistics.median(latencies_us),
        p95_latency_us=sorted(latencies_us)[int(iterations * 0.95)],
        p99_latency_us=sorted(latencies_us)[int(iterations * 0.99)],
        throughput_ops_per_sec=iterations / (total_time_ms / 1000),
    )


def benchmark_cache_write(
    cache: EnhancedInMemoryCacheProvider, iterations: int = 10000
) -> BenchmarkResult:
    """Benchmark cache write latency.

    Measures write latency for new entries.
    """
    now = datetime.now(timezone.utc)
    latencies_us: list[float] = []

    for i in range(iterations):
        entry = CacheEntry(
            key=f"write_key_{i}",
            data={"field1": "value1", "field2": i, "nested": {"a": 1, "b": 2}},
            entry_type=EntryType.TASK,
            version=now,
            ttl=3600,
        )

        start = time.perf_counter_ns()
        cache.set_versioned(f"write_key_{i}", entry)
        end = time.perf_counter_ns()
        latencies_us.append((end - start) / 1000)

    total_time_ms = sum(latencies_us) / 1000

    return BenchmarkResult(
        operation="cache_write",
        iterations=iterations,
        total_time_ms=total_time_ms,
        avg_latency_us=statistics.mean(latencies_us),
        p50_latency_us=statistics.median(latencies_us),
        p95_latency_us=sorted(latencies_us)[int(iterations * 0.95)],
        p99_latency_us=sorted(latencies_us)[int(iterations * 0.99)],
        throughput_ops_per_sec=iterations / (total_time_ms / 1000),
    )


def benchmark_cache_overwrite(
    cache: EnhancedInMemoryCacheProvider, iterations: int = 10000
) -> BenchmarkResult:
    """Benchmark cache overwrite latency.

    Measures write latency when overwriting existing entries.
    """
    now = datetime.now(timezone.utc)

    # Pre-populate
    entry = CacheEntry(
        key="overwrite_key",
        data={"field1": "initial"},
        entry_type=EntryType.TASK,
        version=now,
        ttl=3600,
    )
    cache.set_versioned("overwrite_key", entry)

    latencies_us: list[float] = []

    for i in range(iterations):
        entry = CacheEntry(
            key="overwrite_key",
            data={"field1": f"value_{i}", "iteration": i},
            entry_type=EntryType.TASK,
            version=now,
            ttl=3600,
        )

        start = time.perf_counter_ns()
        cache.set_versioned("overwrite_key", entry)
        end = time.perf_counter_ns()
        latencies_us.append((end - start) / 1000)

    total_time_ms = sum(latencies_us) / 1000

    return BenchmarkResult(
        operation="cache_overwrite",
        iterations=iterations,
        total_time_ms=total_time_ms,
        avg_latency_us=statistics.mean(latencies_us),
        p50_latency_us=statistics.median(latencies_us),
        p95_latency_us=sorted(latencies_us)[int(iterations * 0.95)],
        p99_latency_us=sorted(latencies_us)[int(iterations * 0.99)],
        throughput_ops_per_sec=iterations / (total_time_ms / 1000),
    )


def benchmark_invalidation(
    cache: EnhancedInMemoryCacheProvider, iterations: int = 10000
) -> BenchmarkResult:
    """Benchmark cache invalidation latency."""
    now = datetime.now(timezone.utc)

    # Pre-populate
    for i in range(iterations):
        entry = CacheEntry(
            key=f"invalidate_key_{i}",
            data={"value": i},
            entry_type=EntryType.TASK,
            version=now,
            ttl=3600,
        )
        cache.set_versioned(f"invalidate_key_{i}", entry)

    latencies_us: list[float] = []

    for i in range(iterations):
        start = time.perf_counter_ns()
        cache.invalidate(f"invalidate_key_{i}")
        end = time.perf_counter_ns()
        latencies_us.append((end - start) / 1000)

    total_time_ms = sum(latencies_us) / 1000

    return BenchmarkResult(
        operation="invalidation",
        iterations=iterations,
        total_time_ms=total_time_ms,
        avg_latency_us=statistics.mean(latencies_us),
        p50_latency_us=statistics.median(latencies_us),
        p95_latency_us=sorted(latencies_us)[int(iterations * 0.95)],
        p99_latency_us=sorted(latencies_us)[int(iterations * 0.99)],
        throughput_ops_per_sec=iterations / (total_time_ms / 1000),
    )


def print_result(result: BenchmarkResult) -> None:
    """Print benchmark result in readable format."""
    print(f"\n{'=' * 60}")
    print(f"Operation: {result.operation}")
    print(f"{'=' * 60}")
    print(f"Iterations:        {result.iterations:,}")
    print(f"Total Time:        {result.total_time_ms:.2f} ms")
    print(f"Avg Latency:       {result.avg_latency_us:.2f} us")
    print(f"P50 Latency:       {result.p50_latency_us:.2f} us")
    print(f"P95 Latency:       {result.p95_latency_us:.2f} us")
    print(f"P99 Latency:       {result.p99_latency_us:.2f} us")
    print(f"Throughput:        {result.throughput_ops_per_sec:,.0f} ops/sec")

    # Check against targets
    avg_latency_ms = result.avg_latency_us / 1000
    if result.operation == "cache_hit":
        target = 1.0  # < 1ms target
        status = "PASS" if avg_latency_ms < target else "FAIL"
        print(f"Target (< 1ms):    {status} ({avg_latency_ms:.4f} ms)")
    elif result.operation == "cache_write":
        target = 1.0  # < 1ms target for in-memory
        status = "PASS" if avg_latency_ms < target else "FAIL"
        print(f"Target (< 1ms):    {status} ({avg_latency_ms:.4f} ms)")


def main() -> None:
    """Run all cache operation benchmarks."""
    print("\n" + "=" * 60)
    print("CACHE OPERATIONS BENCHMARK")
    print("=" * 60)
    print("Backend: EnhancedInMemoryCacheProvider")
    print(f"Time: {datetime.now().isoformat()}")

    # Create cache with large capacity to avoid eviction during benchmarks
    cache = EnhancedInMemoryCacheProvider(max_size=100000)

    # Warmup
    print("\nWarming up...")
    warmup_result = benchmark_cache_hit(cache, iterations=1000)
    cache.clear()

    # Run benchmarks
    print("\nRunning benchmarks...")

    results = [
        benchmark_cache_hit(cache, iterations=10000),
        benchmark_cache_miss(cache, iterations=10000),
        benchmark_cache_write(cache, iterations=10000),
        benchmark_cache_overwrite(cache, iterations=10000),
        benchmark_invalidation(cache, iterations=10000),
    ]

    for result in results:
        print_result(result)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for result in results:
        avg_ms = result.avg_latency_us / 1000
        print(
            f"{result.operation:20s}: {avg_ms:.4f} ms avg, {result.throughput_ops_per_sec:,.0f} ops/sec"
        )


if __name__ == "__main__":
    main()
