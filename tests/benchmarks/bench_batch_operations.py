#!/usr/bin/env python3
"""Benchmark script for batch cache operations.

Measures latency and throughput of batch staleness checking
and batch cache operations.

Usage:
    python -m tests.benchmarks.bench_batch_operations

Output:
    Timing data for batch operations at various sizes.
"""

from __future__ import annotations

import asyncio
import statistics
import time
from datetime import datetime, timezone
from typing import NamedTuple

from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.cache.batch import (
    ModificationCheckCache,
    fetch_task_modifications,
    reset_modification_cache,
)
from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.staleness import check_batch_staleness


class BatchBenchmarkResult(NamedTuple):
    """Result of a batch benchmark run."""

    operation: str
    batch_size: int
    iterations: int
    total_time_ms: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_batches_per_sec: float
    items_per_sec: float


def benchmark_batch_get(
    cache: EnhancedInMemoryCacheProvider,
    batch_size: int,
    iterations: int = 100,
) -> BatchBenchmarkResult:
    """Benchmark batch get operations."""
    now = datetime.now(timezone.utc)

    # Pre-populate cache
    for i in range(batch_size):
        entry = CacheEntry(
            key=f"batch_key_{i}",
            data={"field": f"value_{i}"},
            entry_type=EntryType.TASK,
            version=now,
            ttl=3600,
        )
        cache.set_versioned(f"batch_key_{i}", entry)

    keys = [f"batch_key_{i}" for i in range(batch_size)]
    latencies_ms: list[float] = []

    for _ in range(iterations):
        start = time.perf_counter_ns()
        cache.get_batch(keys, EntryType.TASK)
        end = time.perf_counter_ns()
        latencies_ms.append((end - start) / 1_000_000)

    total_time_ms = sum(latencies_ms)

    return BatchBenchmarkResult(
        operation="batch_get",
        batch_size=batch_size,
        iterations=iterations,
        total_time_ms=total_time_ms,
        avg_latency_ms=statistics.mean(latencies_ms),
        p50_latency_ms=statistics.median(latencies_ms),
        p95_latency_ms=sorted(latencies_ms)[int(iterations * 0.95)],
        p99_latency_ms=sorted(latencies_ms)[int(iterations * 0.99)],
        throughput_batches_per_sec=iterations / (total_time_ms / 1000),
        items_per_sec=(iterations * batch_size) / (total_time_ms / 1000),
    )


def benchmark_batch_set(
    cache: EnhancedInMemoryCacheProvider,
    batch_size: int,
    iterations: int = 100,
) -> BatchBenchmarkResult:
    """Benchmark batch set operations."""
    now = datetime.now(timezone.utc)

    latencies_ms: list[float] = []

    for iter_num in range(iterations):
        entries = {
            f"batch_set_{iter_num}_{i}": CacheEntry(
                key=f"batch_set_{iter_num}_{i}",
                data={"field": f"value_{i}"},
                entry_type=EntryType.TASK,
                version=now,
                ttl=3600,
            )
            for i in range(batch_size)
        }

        start = time.perf_counter_ns()
        cache.set_batch(entries)
        end = time.perf_counter_ns()
        latencies_ms.append((end - start) / 1_000_000)

    total_time_ms = sum(latencies_ms)

    return BatchBenchmarkResult(
        operation="batch_set",
        batch_size=batch_size,
        iterations=iterations,
        total_time_ms=total_time_ms,
        avg_latency_ms=statistics.mean(latencies_ms),
        p50_latency_ms=statistics.median(latencies_ms),
        p95_latency_ms=sorted(latencies_ms)[int(iterations * 0.95)],
        p99_latency_ms=sorted(latencies_ms)[int(iterations * 0.99)],
        throughput_batches_per_sec=iterations / (total_time_ms / 1000),
        items_per_sec=(iterations * batch_size) / (total_time_ms / 1000),
    )


def benchmark_modification_check_cache(
    batch_size: int,
    iterations: int = 100,
) -> BatchBenchmarkResult:
    """Benchmark ModificationCheckCache get_many operations."""
    reset_modification_cache()
    cache = ModificationCheckCache(ttl=60.0)

    # Pre-populate
    for i in range(batch_size):
        cache.set(f"gid_{i}", f"2025-01-{(i % 28) + 1:02d}T00:00:00Z")

    gids = [f"gid_{i}" for i in range(batch_size)]
    latencies_ms: list[float] = []

    for _ in range(iterations):
        start = time.perf_counter_ns()
        cache.get_many(gids)
        end = time.perf_counter_ns()
        latencies_ms.append((end - start) / 1_000_000)

    total_time_ms = sum(latencies_ms)

    return BatchBenchmarkResult(
        operation="modification_check_get_many",
        batch_size=batch_size,
        iterations=iterations,
        total_time_ms=total_time_ms,
        avg_latency_ms=statistics.mean(latencies_ms),
        p50_latency_ms=statistics.median(latencies_ms),
        p95_latency_ms=sorted(latencies_ms)[int(iterations * 0.95)],
        p99_latency_ms=sorted(latencies_ms)[int(iterations * 0.99)],
        throughput_batches_per_sec=iterations / (total_time_ms / 1000),
        items_per_sec=(iterations * batch_size) / (total_time_ms / 1000),
    )


def benchmark_staleness_check(
    cache: EnhancedInMemoryCacheProvider,
    batch_size: int,
    iterations: int = 100,
) -> BatchBenchmarkResult:
    """Benchmark batch staleness checking."""
    now = datetime.now(timezone.utc)

    # Pre-populate cache
    for i in range(batch_size):
        entry = CacheEntry(
            key=f"stale_check_{i}",
            data={"field": f"value_{i}"},
            entry_type=EntryType.TASK,
            version=now,
            ttl=3600,
        )
        cache.set_versioned(f"stale_check_{i}", entry)

    gids = [f"stale_check_{i}" for i in range(batch_size)]
    current_versions = {gid: now.isoformat() for gid in gids}

    latencies_ms: list[float] = []

    for _ in range(iterations):
        start = time.perf_counter_ns()
        check_batch_staleness(cache, gids, EntryType.TASK, current_versions)
        end = time.perf_counter_ns()
        latencies_ms.append((end - start) / 1_000_000)

    total_time_ms = sum(latencies_ms)

    return BatchBenchmarkResult(
        operation="staleness_check",
        batch_size=batch_size,
        iterations=iterations,
        total_time_ms=total_time_ms,
        avg_latency_ms=statistics.mean(latencies_ms),
        p50_latency_ms=statistics.median(latencies_ms),
        p95_latency_ms=sorted(latencies_ms)[int(iterations * 0.95)],
        p99_latency_ms=sorted(latencies_ms)[int(iterations * 0.99)],
        throughput_batches_per_sec=iterations / (total_time_ms / 1000),
        items_per_sec=(iterations * batch_size) / (total_time_ms / 1000),
    )


async def benchmark_fetch_modifications(
    batch_size: int,
    iterations: int = 100,
) -> BatchBenchmarkResult:
    """Benchmark fetch_task_modifications with mock API."""
    reset_modification_cache()

    # Mock API that returns immediately
    async def mock_batch_api(gids: list[str]) -> dict[str, str]:
        return {gid: "2025-01-01T00:00:00Z" for gid in gids}

    gids = [f"gid_{i}" for i in range(batch_size)]
    latencies_ms: list[float] = []

    # First call to populate cache
    await fetch_task_modifications(gids, mock_batch_api)

    # Subsequent calls should hit cache
    for _ in range(iterations):
        start = time.perf_counter_ns()
        await fetch_task_modifications(gids, mock_batch_api)
        end = time.perf_counter_ns()
        latencies_ms.append((end - start) / 1_000_000)

    total_time_ms = sum(latencies_ms)

    return BatchBenchmarkResult(
        operation="fetch_modifications_cached",
        batch_size=batch_size,
        iterations=iterations,
        total_time_ms=total_time_ms,
        avg_latency_ms=statistics.mean(latencies_ms),
        p50_latency_ms=statistics.median(latencies_ms),
        p95_latency_ms=sorted(latencies_ms)[int(iterations * 0.95)],
        p99_latency_ms=sorted(latencies_ms)[int(iterations * 0.99)],
        throughput_batches_per_sec=iterations / (total_time_ms / 1000),
        items_per_sec=(iterations * batch_size) / (total_time_ms / 1000),
    )


def print_result(result: BatchBenchmarkResult) -> None:
    """Print benchmark result in readable format."""
    print(f"\n{'-' * 60}")
    print(f"Operation: {result.operation}, Batch Size: {result.batch_size}")
    print(f"{'-' * 60}")
    print(f"Iterations:        {result.iterations}")
    print(f"Total Time:        {result.total_time_ms:.2f} ms")
    print(f"Avg Latency:       {result.avg_latency_ms:.3f} ms")
    print(f"P50 Latency:       {result.p50_latency_ms:.3f} ms")
    print(f"P95 Latency:       {result.p95_latency_ms:.3f} ms")
    print(f"P99 Latency:       {result.p99_latency_ms:.3f} ms")
    print(f"Batches/sec:       {result.throughput_batches_per_sec:,.0f}")
    print(f"Items/sec:         {result.items_per_sec:,.0f}")


def check_targets(results: list[BatchBenchmarkResult]) -> None:
    """Check results against NFR targets."""
    print("\n" + "=" * 60)
    print("TARGET VALIDATION")
    print("=" * 60)

    # NFR-PERF-004: Batch modification check < 500ms for 100 GIDs
    for result in results:
        if result.operation == "staleness_check" and result.batch_size == 100:
            status = "PASS" if result.avg_latency_ms < 500 else "FAIL"
            print(f"NFR-PERF-004 (100 GIDs < 500ms): {status} ({result.avg_latency_ms:.3f} ms)")

        if result.operation == "staleness_check" and result.batch_size == 1000:
            status = "PASS" if result.avg_latency_ms < 5000 else "FAIL"
            print(f"Batch check 1000 GIDs < 5s:      {status} ({result.avg_latency_ms:.3f} ms)")


def main() -> None:
    """Run all batch operation benchmarks."""
    print("\n" + "=" * 60)
    print("BATCH OPERATIONS BENCHMARK")
    print("=" * 60)
    print(f"Backend: EnhancedInMemoryCacheProvider")
    print(f"Time: {datetime.now().isoformat()}")

    cache = EnhancedInMemoryCacheProvider(max_size=100000)
    all_results: list[BatchBenchmarkResult] = []

    # Batch sizes to test
    batch_sizes = [10, 50, 100, 500, 1000]

    print("\n" + "=" * 60)
    print("BATCH GET BENCHMARKS")
    print("=" * 60)
    for size in batch_sizes:
        result = benchmark_batch_get(cache, size)
        print_result(result)
        all_results.append(result)
        cache.clear()

    print("\n" + "=" * 60)
    print("BATCH SET BENCHMARKS")
    print("=" * 60)
    for size in batch_sizes:
        result = benchmark_batch_set(cache, size)
        print_result(result)
        all_results.append(result)
        cache.clear()

    print("\n" + "=" * 60)
    print("MODIFICATION CHECK CACHE BENCHMARKS")
    print("=" * 60)
    for size in batch_sizes:
        result = benchmark_modification_check_cache(size)
        print_result(result)
        all_results.append(result)
        reset_modification_cache()

    print("\n" + "=" * 60)
    print("STALENESS CHECK BENCHMARKS")
    print("=" * 60)
    for size in batch_sizes:
        result = benchmark_staleness_check(cache, size)
        print_result(result)
        all_results.append(result)
        cache.clear()

    print("\n" + "=" * 60)
    print("ASYNC FETCH MODIFICATIONS BENCHMARKS")
    print("=" * 60)
    for size in [10, 50, 100]:  # Smaller sizes for async
        result = asyncio.run(benchmark_fetch_modifications(size))
        print_result(result)
        all_results.append(result)
        reset_modification_cache()

    # Check against targets
    check_targets(all_results)

    # Summary table
    print("\n" + "=" * 60)
    print("SUMMARY TABLE")
    print("=" * 60)
    print(f"{'Operation':<30} {'Size':>6} {'Avg(ms)':>10} {'P99(ms)':>10} {'Items/s':>12}")
    print("-" * 70)
    for result in all_results:
        print(
            f"{result.operation:<30} {result.batch_size:>6} "
            f"{result.avg_latency_ms:>10.3f} {result.p99_latency_ms:>10.3f} "
            f"{result.items_per_sec:>12,.0f}"
        )


if __name__ == "__main__":
    main()
