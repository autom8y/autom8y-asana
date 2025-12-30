#!/usr/bin/env python3
"""Benchmark tests for DataServiceClient performance.

Per Story 3.2: Performance benchmarking to validate P95 < 500ms target.

This module measures client-side overhead excluding network latency:
- Request serialization
- Response deserialization
- DataFrame conversion
- Batch coordination overhead

Usage:
    pytest tests/benchmarks/test_insights_benchmark.py -v --tb=short
    pytest tests/benchmarks/test_insights_benchmark.py -v -k single
    pytest tests/benchmarks/test_insights_benchmark.py -v -k batch

Target: P95 overhead < 50ms (excluding network latency)
"""

from __future__ import annotations

import asyncio
import statistics
import time
from typing import NamedTuple

import httpx
import pytest
import respx

from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig
from autom8_asana.models.contracts import PhoneVerticalPair


class BenchmarkResult(NamedTuple):
    """Result of a benchmark run."""

    operation: str
    iterations: int
    total_time_ms: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float


def calculate_percentile(sorted_latencies: list[float], percentile: float) -> float:
    """Calculate percentile from sorted latencies.

    Args:
        sorted_latencies: Latencies sorted in ascending order.
        percentile: Percentile to calculate (0-100).

    Returns:
        Latency value at the given percentile.
    """
    if not sorted_latencies:
        return 0.0
    index = int(len(sorted_latencies) * percentile / 100)
    index = min(index, len(sorted_latencies) - 1)
    return sorted_latencies[index]


def format_benchmark_result(result: BenchmarkResult) -> str:
    """Format benchmark result for output.

    Args:
        result: BenchmarkResult to format.

    Returns:
        Formatted string with benchmark statistics.
    """
    lines = [
        f"{'=' * 60}",
        f"Benchmark: {result.operation}",
        f"{'=' * 60}",
        f"Iterations:      {result.iterations}",
        f"Total Time:      {result.total_time_ms:.2f} ms",
        f"Avg Latency:     {result.avg_latency_ms:.3f} ms",
        f"P50 Latency:     {result.p50_latency_ms:.3f} ms",
        f"P95 Latency:     {result.p95_latency_ms:.3f} ms",
        f"P99 Latency:     {result.p99_latency_ms:.3f} ms",
        f"Min Latency:     {result.min_latency_ms:.3f} ms",
        f"Max Latency:     {result.max_latency_ms:.3f} ms",
    ]
    return "\n".join(lines)


def build_mock_response(factory: str, row_count: int = 10) -> dict:
    """Build a realistic mock InsightsResponse.

    Args:
        factory: Factory name for the response.
        row_count: Number of rows to include in the response.

    Returns:
        Dictionary representing an InsightsResponse.
    """
    # Build realistic data rows with various dtypes
    data = [
        {
            "date": "2024-01-15",
            "spend": 100.50 + i * 10,
            "impressions": 5000 + i * 500,
            "clicks": 150 + i * 15,
            "leads": 10 + i,
            "cpl": 10.05 + i * 0.5,
            "ctr": 0.03 + i * 0.001,
            "campaign_name": f"Campaign {i}",
            "adset_name": f"AdSet {i}",
        }
        for i in range(row_count)
    ]

    return {
        "data": data,
        "metadata": {
            "factory": factory,
            "frame_type": f"{factory.title()}InsightsFrame",
            "insights_period": "t30",
            "row_count": row_count,
            "column_count": 9,
            "columns": [
                {"name": "date", "dtype": "date", "nullable": False},
                {"name": "spend", "dtype": "float64", "nullable": True},
                {"name": "impressions", "dtype": "int64", "nullable": True},
                {"name": "clicks", "dtype": "int64", "nullable": True},
                {"name": "leads", "dtype": "int64", "nullable": True},
                {"name": "cpl", "dtype": "float64", "nullable": True},
                {"name": "ctr", "dtype": "float64", "nullable": True},
                {"name": "campaign_name", "dtype": "string", "nullable": True},
                {"name": "adset_name", "dtype": "string", "nullable": True},
            ],
            "cache_hit": True,
            "duration_ms": 5.0,  # Simulated server-side duration
            "sort_history": ["date"],
            "is_stale": False,
            "cached_at": None,
        },
        "warnings": [],
    }


@pytest.fixture
def enable_insights_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable insights feature flag for testing."""
    monkeypatch.setenv("AUTOM8_DATA_INSIGHTS_ENABLED", "true")


@pytest.fixture
def client_config() -> DataServiceConfig:
    """Create client configuration for benchmarks."""
    return DataServiceConfig(
        base_url="https://data.example.com",
        cache_ttl=300,
    )


@pytest.fixture
def sample_pvps() -> list[PhoneVerticalPair]:
    """Generate sample PhoneVerticalPairs for batch testing."""
    verticals = ["chiropractic", "dental", "med_spa", "veterinary", "optometry"]
    pairs = []
    for i in range(100):  # Generate 100 pairs for flexibility
        phone = f"+1770575{3000 + i:04d}"
        vertical = verticals[i % len(verticals)]
        pairs.append(PhoneVerticalPair(office_phone=phone, vertical=vertical))
    return pairs


# --- Benchmark Marker ---

benchmark = pytest.mark.benchmark


# --- Single Request Benchmarks ---


@benchmark
@pytest.mark.asyncio
@pytest.mark.usefixtures("enable_insights_feature")
class TestSingleRequestBenchmark:
    """Benchmark tests for single get_insights_async request."""

    async def test_single_request_latency(
        self,
        client_config: DataServiceConfig,
    ) -> None:
        """Measure single request overhead with mocked HTTP.

        Target: P95 < 50ms for client-side processing.
        """
        mock_response = build_mock_response("account", row_count=50)
        iterations = 100
        latencies_ms: list[float] = []

        client = DataServiceClient(config=client_config)

        with respx.mock:
            # Mock returns instantly - we measure client overhead only
            respx.post("https://data.example.com/api/v1/factory/account").respond(
                json=mock_response
            )

            async with client:
                # Warm-up run
                await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

                # Benchmark runs
                for _ in range(iterations):
                    start = time.perf_counter_ns()

                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                        period="t30",
                    )

                    end = time.perf_counter_ns()
                    latencies_ms.append((end - start) / 1_000_000)

                    # Verify response is valid
                    assert response.metadata.row_count == 50

        # Calculate statistics
        sorted_latencies = sorted(latencies_ms)
        result = BenchmarkResult(
            operation="single_get_insights_async",
            iterations=iterations,
            total_time_ms=sum(latencies_ms),
            avg_latency_ms=statistics.mean(latencies_ms),
            p50_latency_ms=statistics.median(latencies_ms),
            p95_latency_ms=calculate_percentile(sorted_latencies, 95),
            p99_latency_ms=calculate_percentile(sorted_latencies, 99),
            min_latency_ms=min(latencies_ms),
            max_latency_ms=max(latencies_ms),
        )

        # Output results
        print(f"\n{format_benchmark_result(result)}")

        # Assert P95 target: < 50ms overhead
        assert result.p95_latency_ms < 50.0, (
            f"P95 latency {result.p95_latency_ms:.3f}ms exceeds 50ms target"
        )

    async def test_single_request_with_dataframe_conversion(
        self,
        client_config: DataServiceConfig,
    ) -> None:
        """Measure request + DataFrame conversion overhead.

        This tests the full path including to_dataframe() call.
        """
        mock_response = build_mock_response("account", row_count=100)
        iterations = 50
        latencies_ms: list[float] = []

        client = DataServiceClient(config=client_config)

        with respx.mock:
            respx.post("https://data.example.com/api/v1/factory/account").respond(
                json=mock_response
            )

            async with client:
                # Warm-up
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )
                _ = response.to_dataframe()

                # Benchmark runs
                for _ in range(iterations):
                    start = time.perf_counter_ns()

                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                        period="t30",
                    )
                    df = response.to_dataframe()

                    end = time.perf_counter_ns()
                    latencies_ms.append((end - start) / 1_000_000)

                    assert len(df) == 100

        sorted_latencies = sorted(latencies_ms)
        result = BenchmarkResult(
            operation="single_request_with_to_dataframe",
            iterations=iterations,
            total_time_ms=sum(latencies_ms),
            avg_latency_ms=statistics.mean(latencies_ms),
            p50_latency_ms=statistics.median(latencies_ms),
            p95_latency_ms=calculate_percentile(sorted_latencies, 95),
            p99_latency_ms=calculate_percentile(sorted_latencies, 99),
            min_latency_ms=min(latencies_ms),
            max_latency_ms=max(latencies_ms),
        )

        print(f"\n{format_benchmark_result(result)}")

        # More lenient target for full path including DataFrame conversion
        assert result.p95_latency_ms < 100.0, (
            f"P95 latency {result.p95_latency_ms:.3f}ms exceeds 100ms target"
        )


# --- Batch Request Benchmarks ---


@benchmark
@pytest.mark.asyncio
@pytest.mark.usefixtures("enable_insights_feature")
class TestBatchRequestBenchmark:
    """Benchmark tests for batch get_insights_batch_async requests."""

    async def test_batch_10_pvps_latency(
        self,
        client_config: DataServiceConfig,
        sample_pvps: list[PhoneVerticalPair],
    ) -> None:
        """Measure batch request overhead with 10 PVPs.

        Target: Batch coordination overhead < 100ms for 10 PVPs.
        """
        mock_response = build_mock_response("account", row_count=10)
        pairs = sample_pvps[:10]
        iterations = 20
        latencies_ms: list[float] = []

        client = DataServiceClient(config=client_config)

        with respx.mock:
            # Mock all possible endpoints
            respx.post(url__regex=r".*/api/v1/factory/account").respond(
                json=mock_response
            )

            async with client:
                # Warm-up
                await client.get_insights_batch_async(pairs[:2], factory="account")

                # Benchmark runs
                for _ in range(iterations):
                    start = time.perf_counter_ns()

                    batch_response = await client.get_insights_batch_async(
                        pairs,
                        factory="account",
                        period="t30",
                    )

                    end = time.perf_counter_ns()
                    latencies_ms.append((end - start) / 1_000_000)

                    assert batch_response.total_count == 10
                    assert batch_response.success_count == 10

        sorted_latencies = sorted(latencies_ms)
        result = BenchmarkResult(
            operation="batch_10_pvps",
            iterations=iterations,
            total_time_ms=sum(latencies_ms),
            avg_latency_ms=statistics.mean(latencies_ms),
            p50_latency_ms=statistics.median(latencies_ms),
            p95_latency_ms=calculate_percentile(sorted_latencies, 95),
            p99_latency_ms=calculate_percentile(sorted_latencies, 99),
            min_latency_ms=min(latencies_ms),
            max_latency_ms=max(latencies_ms),
        )

        print(f"\n{format_benchmark_result(result)}")

        # Assert P95 target for batch of 10
        assert result.p95_latency_ms < 200.0, (
            f"P95 latency {result.p95_latency_ms:.3f}ms exceeds 200ms target for 10 PVPs"
        )

    async def test_batch_50_pvps_latency(
        self,
        client_config: DataServiceConfig,
        sample_pvps: list[PhoneVerticalPair],
    ) -> None:
        """Measure batch request overhead with 50 PVPs.

        Target: P95 < 500ms for batch of 50 PVPs (including coordination).
        """
        mock_response = build_mock_response("account", row_count=10)
        pairs = sample_pvps[:50]
        iterations = 10
        latencies_ms: list[float] = []

        client = DataServiceClient(config=client_config)

        with respx.mock:
            respx.post(url__regex=r".*/api/v1/factory/account").respond(
                json=mock_response
            )

            async with client:
                # Warm-up
                await client.get_insights_batch_async(pairs[:5], factory="account")

                # Benchmark runs
                for _ in range(iterations):
                    start = time.perf_counter_ns()

                    batch_response = await client.get_insights_batch_async(
                        pairs,
                        factory="account",
                        period="t30",
                        max_concurrency=10,
                    )

                    end = time.perf_counter_ns()
                    latencies_ms.append((end - start) / 1_000_000)

                    assert batch_response.total_count == 50
                    assert batch_response.success_count == 50

        sorted_latencies = sorted(latencies_ms)
        result = BenchmarkResult(
            operation="batch_50_pvps",
            iterations=iterations,
            total_time_ms=sum(latencies_ms),
            avg_latency_ms=statistics.mean(latencies_ms),
            p50_latency_ms=statistics.median(latencies_ms),
            p95_latency_ms=calculate_percentile(sorted_latencies, 95),
            p99_latency_ms=calculate_percentile(sorted_latencies, 99),
            min_latency_ms=min(latencies_ms),
            max_latency_ms=max(latencies_ms),
        )

        print(f"\n{format_benchmark_result(result)}")

        # Assert P95 target for batch of 50
        assert result.p95_latency_ms < 500.0, (
            f"P95 latency {result.p95_latency_ms:.3f}ms exceeds 500ms target for 50 PVPs"
        )

    async def test_batch_with_dataframe_aggregation(
        self,
        client_config: DataServiceConfig,
        sample_pvps: list[PhoneVerticalPair],
    ) -> None:
        """Measure batch request + DataFrame aggregation overhead.

        Tests full path including to_dataframe() on BatchInsightsResponse.
        """
        mock_response = build_mock_response("account", row_count=20)
        pairs = sample_pvps[:25]
        iterations = 10
        latencies_ms: list[float] = []

        client = DataServiceClient(config=client_config)

        with respx.mock:
            respx.post(url__regex=r".*/api/v1/factory/account").respond(
                json=mock_response
            )

            async with client:
                # Warm-up
                batch = await client.get_insights_batch_async(pairs[:3], factory="account")
                _ = batch.to_dataframe()

                # Benchmark runs
                for _ in range(iterations):
                    start = time.perf_counter_ns()

                    batch_response = await client.get_insights_batch_async(
                        pairs,
                        factory="account",
                        period="t30",
                    )
                    df = batch_response.to_dataframe()

                    end = time.perf_counter_ns()
                    latencies_ms.append((end - start) / 1_000_000)

                    # 25 PVPs * 20 rows each = 500 rows total
                    assert len(df) == 500
                    assert "_pvp_key" in df.columns

        sorted_latencies = sorted(latencies_ms)
        result = BenchmarkResult(
            operation="batch_25_pvps_with_dataframe",
            iterations=iterations,
            total_time_ms=sum(latencies_ms),
            avg_latency_ms=statistics.mean(latencies_ms),
            p50_latency_ms=statistics.median(latencies_ms),
            p95_latency_ms=calculate_percentile(sorted_latencies, 95),
            p99_latency_ms=calculate_percentile(sorted_latencies, 99),
            min_latency_ms=min(latencies_ms),
            max_latency_ms=max(latencies_ms),
        )

        print(f"\n{format_benchmark_result(result)}")

        # More lenient for full path with DataFrame aggregation
        assert result.p95_latency_ms < 500.0, (
            f"P95 latency {result.p95_latency_ms:.3f}ms exceeds 500ms target"
        )


# --- Response Parsing Benchmarks ---


@benchmark
class TestResponseParsingBenchmark:
    """Benchmark tests for response deserialization and DataFrame conversion."""

    def test_response_deserialization(self) -> None:
        """Measure InsightsResponse model construction overhead."""
        from autom8_asana.clients.data.models import (
            ColumnInfo,
            InsightsMetadata,
            InsightsResponse,
        )

        # Build raw response data
        raw_response = build_mock_response("account", row_count=100)
        iterations = 1000
        latencies_ms: list[float] = []

        # Warm-up
        columns = [ColumnInfo(**col) for col in raw_response["metadata"]["columns"]]
        metadata = InsightsMetadata(
            factory=raw_response["metadata"]["factory"],
            row_count=raw_response["metadata"]["row_count"],
            column_count=raw_response["metadata"]["column_count"],
            columns=columns,
            cache_hit=raw_response["metadata"]["cache_hit"],
            duration_ms=raw_response["metadata"]["duration_ms"],
        )
        _ = InsightsResponse(
            data=raw_response["data"],
            metadata=metadata,
            request_id="bench-001",
        )

        # Benchmark runs
        for _ in range(iterations):
            start = time.perf_counter_ns()

            columns = [ColumnInfo(**col) for col in raw_response["metadata"]["columns"]]
            metadata = InsightsMetadata(
                factory=raw_response["metadata"]["factory"],
                row_count=raw_response["metadata"]["row_count"],
                column_count=raw_response["metadata"]["column_count"],
                columns=columns,
                cache_hit=raw_response["metadata"]["cache_hit"],
                duration_ms=raw_response["metadata"]["duration_ms"],
            )
            response = InsightsResponse(
                data=raw_response["data"],
                metadata=metadata,
                request_id="bench-001",
            )

            end = time.perf_counter_ns()
            latencies_ms.append((end - start) / 1_000_000)

            assert response.metadata.row_count == 100

        sorted_latencies = sorted(latencies_ms)
        result = BenchmarkResult(
            operation="response_deserialization",
            iterations=iterations,
            total_time_ms=sum(latencies_ms),
            avg_latency_ms=statistics.mean(latencies_ms),
            p50_latency_ms=statistics.median(latencies_ms),
            p95_latency_ms=calculate_percentile(sorted_latencies, 95),
            p99_latency_ms=calculate_percentile(sorted_latencies, 99),
            min_latency_ms=min(latencies_ms),
            max_latency_ms=max(latencies_ms),
        )

        print(f"\n{format_benchmark_result(result)}")

        # Very low target for just model construction
        assert result.p95_latency_ms < 5.0, (
            f"P95 latency {result.p95_latency_ms:.3f}ms exceeds 5ms target"
        )

    def test_dataframe_conversion_100_rows(self) -> None:
        """Measure to_dataframe() overhead for 100 rows."""
        from autom8_asana.clients.data.models import (
            ColumnInfo,
            InsightsMetadata,
            InsightsResponse,
        )

        raw_response = build_mock_response("account", row_count=100)
        iterations = 100
        latencies_ms: list[float] = []

        # Pre-build the response
        columns = [ColumnInfo(**col) for col in raw_response["metadata"]["columns"]]
        metadata = InsightsMetadata(
            factory=raw_response["metadata"]["factory"],
            row_count=raw_response["metadata"]["row_count"],
            column_count=raw_response["metadata"]["column_count"],
            columns=columns,
            cache_hit=raw_response["metadata"]["cache_hit"],
            duration_ms=raw_response["metadata"]["duration_ms"],
        )
        response = InsightsResponse(
            data=raw_response["data"],
            metadata=metadata,
            request_id="bench-001",
        )

        # Warm-up
        _ = response.to_dataframe()

        # Benchmark runs
        for _ in range(iterations):
            start = time.perf_counter_ns()

            df = response.to_dataframe()

            end = time.perf_counter_ns()
            latencies_ms.append((end - start) / 1_000_000)

            assert len(df) == 100

        sorted_latencies = sorted(latencies_ms)
        result = BenchmarkResult(
            operation="to_dataframe_100_rows",
            iterations=iterations,
            total_time_ms=sum(latencies_ms),
            avg_latency_ms=statistics.mean(latencies_ms),
            p50_latency_ms=statistics.median(latencies_ms),
            p95_latency_ms=calculate_percentile(sorted_latencies, 95),
            p99_latency_ms=calculate_percentile(sorted_latencies, 99),
            min_latency_ms=min(latencies_ms),
            max_latency_ms=max(latencies_ms),
        )

        print(f"\n{format_benchmark_result(result)}")

        # DataFrame conversion should be fast
        assert result.p95_latency_ms < 20.0, (
            f"P95 latency {result.p95_latency_ms:.3f}ms exceeds 20ms target"
        )

    def test_dataframe_conversion_1000_rows(self) -> None:
        """Measure to_dataframe() overhead for 1000 rows."""
        from autom8_asana.clients.data.models import (
            ColumnInfo,
            InsightsMetadata,
            InsightsResponse,
        )

        raw_response = build_mock_response("account", row_count=1000)
        iterations = 50
        latencies_ms: list[float] = []

        columns = [ColumnInfo(**col) for col in raw_response["metadata"]["columns"]]
        metadata = InsightsMetadata(
            factory=raw_response["metadata"]["factory"],
            row_count=raw_response["metadata"]["row_count"],
            column_count=raw_response["metadata"]["column_count"],
            columns=columns,
            cache_hit=raw_response["metadata"]["cache_hit"],
            duration_ms=raw_response["metadata"]["duration_ms"],
        )
        response = InsightsResponse(
            data=raw_response["data"],
            metadata=metadata,
            request_id="bench-001",
        )

        # Warm-up
        _ = response.to_dataframe()

        # Benchmark runs
        for _ in range(iterations):
            start = time.perf_counter_ns()

            df = response.to_dataframe()

            end = time.perf_counter_ns()
            latencies_ms.append((end - start) / 1_000_000)

            assert len(df) == 1000

        sorted_latencies = sorted(latencies_ms)
        result = BenchmarkResult(
            operation="to_dataframe_1000_rows",
            iterations=iterations,
            total_time_ms=sum(latencies_ms),
            avg_latency_ms=statistics.mean(latencies_ms),
            p50_latency_ms=statistics.median(latencies_ms),
            p95_latency_ms=calculate_percentile(sorted_latencies, 95),
            p99_latency_ms=calculate_percentile(sorted_latencies, 99),
            min_latency_ms=min(latencies_ms),
            max_latency_ms=max(latencies_ms),
        )

        print(f"\n{format_benchmark_result(result)}")

        # Larger dataset should still be reasonable
        assert result.p95_latency_ms < 100.0, (
            f"P95 latency {result.p95_latency_ms:.3f}ms exceeds 100ms target"
        )


# --- Performance Summary ---


def run_all_benchmarks_and_summarize() -> None:
    """Run all benchmarks and print summary.

    This function is for manual execution outside pytest.
    """
    print("\n" + "=" * 70)
    print("INSIGHTS CLIENT PERFORMANCE BENCHMARK SUMMARY")
    print("=" * 70)
    print("\nRun with: pytest tests/benchmarks/test_insights_benchmark.py -v -s")
    print("\nThis measures client-side overhead ONLY (mocked HTTP).")
    print("Network latency is excluded from these measurements.")
    print("\nTargets:")
    print("  - Single request P95:    < 50ms")
    print("  - Batch 10 PVPs P95:     < 200ms")
    print("  - Batch 50 PVPs P95:     < 500ms")
    print("  - DataFrame conv. P95:   < 20ms (100 rows)")
    print("=" * 70)


if __name__ == "__main__":
    run_all_benchmarks_and_summarize()
