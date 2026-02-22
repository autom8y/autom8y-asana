"""End-to-end integration tests for cache optimization.

Per TDD-CACHE-PERF-FETCH-PATH Phase 4 and FR-OBS-003:
Tests that validate the full cache lifecycle including:
1. Cold fetch (cache miss) - populates cache
2. Warm fetch (cache hit) - uses cache
3. Validates hit rate and performance metrics

Test Strategy:
- Uses EnhancedInMemoryCacheProvider for realistic caching behavior
- Mocks Asana HTTP client for deterministic API responses
- Validates cache hit rates and performance targets
- Skippable without live credentials (all mocked)

Performance Targets (NFR-LATENCY):
- Cold cache: <= baseline (no regression)
- Warm cache: < 1.0s with > 90% hit rate
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.config import AsanaConfig
from autom8_asana.dataframes.builders.task_cache import TaskCacheCoordinator
from autom8_asana.dataframes.models.schema import DataFrameSchema
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# --- Test Data Factories ---


def make_task_data(
    gid: str,
    name: str,
    section_gid: str = "section_001",
    project_gid: str = "project_001",
    completed: bool = False,
    modified_at: str = "2025-01-01T12:00:00Z",
    **extra: Any,
) -> dict[str, Any]:
    """Create mock task data dict."""
    data = {
        "gid": gid,
        "name": name,
        "resource_type": "task",
        "resource_subtype": "default_task",
        "completed": completed,
        "completed_at": None,
        "created_at": "2025-01-01T10:00:00Z",
        "modified_at": modified_at,
        "due_on": None,
        "tags": [],
        "memberships": [
            {
                "project": {"gid": project_gid},
                "section": {"gid": section_gid, "name": "Active"},
            }
        ],
    }
    data.update(extra)
    return data


def make_section_data(gid: str, name: str) -> dict[str, Any]:
    """Create mock section data dict."""
    return {
        "gid": gid,
        "name": name,
        "resource_type": "section",
    }


def make_task_model(data: dict[str, Any]) -> Task:
    """Create Task model from data dict."""
    return Task.model_validate(data)


# --- Test Fixtures ---


PROJECT_GID = "project_cache_test_001"


@pytest.fixture
def cache_provider() -> EnhancedInMemoryCacheProvider:
    """Create in-memory cache provider for integration tests."""
    return EnhancedInMemoryCacheProvider(default_ttl=300, max_size=1000)


@pytest.fixture
def mock_http() -> MagicMock:
    """Create mock HTTP client."""
    http = MagicMock()
    http.get = AsyncMock()
    http.post = AsyncMock()
    http.get_paginated = AsyncMock()
    return http


@pytest.fixture
def mock_auth() -> MagicMock:
    """Create mock auth provider."""
    auth = MagicMock()
    auth.get_secret = MagicMock(return_value="test-token")
    return auth


@pytest.fixture
def config() -> AsanaConfig:
    """Default test configuration."""
    return AsanaConfig()


@pytest.fixture
def sample_tasks() -> list[dict[str, Any]]:
    """Create sample task data for testing."""
    return [
        make_task_data("task_001", "Task Alpha"),
        make_task_data("task_002", "Task Beta"),
        make_task_data("task_003", "Task Gamma"),
        make_task_data("task_004", "Task Delta"),
        make_task_data("task_005", "Task Epsilon"),
    ]


@pytest.fixture
def sample_sections() -> list[dict[str, Any]]:
    """Create sample section data."""
    return [
        make_section_data("section_001", "Active"),
        make_section_data("section_002", "In Progress"),
    ]


@pytest.fixture
def base_schema() -> DataFrameSchema:
    """Create minimal schema for testing."""
    return DataFrameSchema(
        name="TestSchema",
        version="1.0.0",
        columns={
            "gid": {"type": "string", "nullable": False},
            "name": {"type": "string", "nullable": True},
            "completed": {"type": "boolean", "nullable": True},
        },
    )


# =============================================================================
# Test: Cold Cache -> Warm Cache Lifecycle
# =============================================================================


@pytest.mark.asyncio
class TestCacheColdToWarmLifecycle:
    """Test full cache lifecycle from cold to warm state."""

    async def test_cold_fetch_populates_cache(
        self,
        cache_provider: EnhancedInMemoryCacheProvider,
        sample_tasks: list[dict[str, Any]],
    ) -> None:
        """First fetch (cold cache) populates cache with tasks.

        Verifies:
        - Cold cache results in 0% hit rate
        - All tasks are fetched from API
        - Cache is populated after fetch
        """
        # Setup: TaskCacheCoordinator with real cache
        coordinator = TaskCacheCoordinator(cache_provider)

        # Simulate cold cache lookup
        task_gids = [t["gid"] for t in sample_tasks]
        cached_map = await coordinator.lookup_tasks_async(task_gids)

        # Assert: All misses (cold cache)
        assert all(v is None for v in cached_map.values())
        hits = sum(1 for v in cached_map.values() if v is not None)
        assert hits == 0

        # Simulate API fetch and cache population
        task_models = [make_task_model(t) for t in sample_tasks]
        populated_count = await coordinator.populate_tasks_async(task_models)

        # Assert: All tasks cached
        assert populated_count == len(sample_tasks)

        # Verify cache now contains tasks
        cached_map_after = await coordinator.lookup_tasks_async(task_gids)
        hits_after = sum(1 for v in cached_map_after.values() if v is not None)
        assert hits_after == len(sample_tasks)

    async def test_warm_fetch_uses_cache(
        self,
        cache_provider: EnhancedInMemoryCacheProvider,
        sample_tasks: list[dict[str, Any]],
    ) -> None:
        """Second fetch (warm cache) achieves high hit rate.

        Verifies:
        - Warm cache results in 100% hit rate
        - No API fetch needed
        - Cached tasks are returned correctly
        """
        # Setup: Populate cache first (simulate cold fetch)
        coordinator = TaskCacheCoordinator(cache_provider)
        task_models = [make_task_model(t) for t in sample_tasks]
        await coordinator.populate_tasks_async(task_models)

        # Act: Warm cache lookup
        task_gids = [t["gid"] for t in sample_tasks]
        cached_map = await coordinator.lookup_tasks_async(task_gids)

        # Assert: All hits (warm cache)
        hits = sum(1 for v in cached_map.values() if v is not None)
        hit_rate = hits / len(task_gids)

        assert hit_rate == 1.0, f"Expected 100% hit rate, got {hit_rate:.1%}"
        assert hits == len(sample_tasks)

        # Verify cached task data is correct
        for gid, task in cached_map.items():
            assert task is not None
            assert task.gid == gid

    async def test_cache_hit_rate_target_achieved(
        self,
        cache_provider: EnhancedInMemoryCacheProvider,
        sample_tasks: list[dict[str, Any]],
    ) -> None:
        """Warm cache achieves > 90% hit rate target.

        Per NFR-LATENCY: Target is > 90% hit rate on warm cache.
        """
        # Populate cache
        coordinator = TaskCacheCoordinator(cache_provider)
        task_models = [make_task_model(t) for t in sample_tasks]
        await coordinator.populate_tasks_async(task_models)

        # Merge results to get TaskCacheResult with metrics
        task_gids = [t["gid"] for t in sample_tasks]
        cached_map = await coordinator.lookup_tasks_async(task_gids)

        # Partition hits
        cached_tasks = {gid: t for gid, t in cached_map.items() if t is not None}
        fetched_tasks: list[Task] = []  # None needed for warm cache

        result = coordinator.merge_results(task_gids, cached_tasks, fetched_tasks)

        # Assert: Hit rate > 90%
        assert result.hit_rate > 0.90, (
            f"Hit rate {result.hit_rate:.1%} below 90% target"
        )
        assert result.cache_hits == len(sample_tasks)
        assert result.cache_misses == 0


# =============================================================================
# Test: Partial Cache Scenarios
# =============================================================================


@pytest.mark.asyncio
class TestPartialCacheScenarios:
    """Test mixed cache hit/miss scenarios."""

    async def test_partial_cache_merges_correctly(
        self,
        cache_provider: EnhancedInMemoryCacheProvider,
        sample_tasks: list[dict[str, Any]],
    ) -> None:
        """Partial cache hit correctly merges cached and fetched tasks.

        Verifies:
        - Cached tasks are returned from cache
        - Missing tasks are fetched from API
        - Merge preserves task order
        """
        coordinator = TaskCacheCoordinator(cache_provider)

        # Populate only first 3 tasks
        partial_models = [make_task_model(t) for t in sample_tasks[:3]]
        await coordinator.populate_tasks_async(partial_models)

        # Lookup all 5 tasks
        task_gids = [t["gid"] for t in sample_tasks]
        cached_map = await coordinator.lookup_tasks_async(task_gids)

        # Partition
        cached_tasks = {gid: t for gid, t in cached_map.items() if t is not None}
        miss_gids = [gid for gid, t in cached_map.items() if t is None]

        # Simulate fetching missing tasks
        fetched_models = [make_task_model(t) for t in sample_tasks[3:]]

        # Merge results
        result = coordinator.merge_results(task_gids, cached_tasks, fetched_models)

        # Assert: Correct counts
        assert result.cache_hits == 3
        assert result.cache_misses == 2
        assert len(result.all_tasks) == 5

        # Assert: Order preserved
        result_gids = [t.gid for t in result.all_tasks]
        expected_gids = [t["gid"] for t in sample_tasks]
        assert result_gids == expected_gids

    async def test_partial_cache_hit_rate_calculation(
        self,
        cache_provider: EnhancedInMemoryCacheProvider,
        sample_tasks: list[dict[str, Any]],
    ) -> None:
        """Hit rate is calculated correctly for partial cache."""
        coordinator = TaskCacheCoordinator(cache_provider)

        # Populate 4 of 5 tasks (80% in cache)
        partial_models = [make_task_model(t) for t in sample_tasks[:4]]
        await coordinator.populate_tasks_async(partial_models)

        # Lookup all
        task_gids = [t["gid"] for t in sample_tasks]
        cached_map = await coordinator.lookup_tasks_async(task_gids)

        cached_tasks = {gid: t for gid, t in cached_map.items() if t is not None}
        fetched_models = [make_task_model(sample_tasks[4])]

        result = coordinator.merge_results(task_gids, cached_tasks, fetched_models)

        # Assert: 80% hit rate
        assert result.hit_rate == pytest.approx(0.80, rel=0.01)
        assert result.cache_hits == 4
        assert result.cache_misses == 1


# =============================================================================
# Test: Cache Graceful Degradation
# =============================================================================


@pytest.mark.asyncio
class TestCacheGracefulDegradation:
    """Test graceful degradation on cache failures."""

    async def test_no_cache_provider_returns_all_misses(self) -> None:
        """When cache provider is None, all lookups return None (miss).

        Per FR-DEGRADE: Cache operations should never raise exceptions;
        missing cache is treated as cache miss.
        """
        coordinator = TaskCacheCoordinator(None)  # No cache

        task_gids = ["task_001", "task_002", "task_003"]
        result = await coordinator.lookup_tasks_async(task_gids)

        # Assert: All misses
        assert all(v is None for v in result.values())
        assert len(result) == len(task_gids)

    async def test_no_cache_provider_population_returns_zero(self) -> None:
        """When cache provider is None, population is a no-op.

        Per FR-DEGRADE: Should not fail, just skip caching.
        """
        coordinator = TaskCacheCoordinator(None)

        tasks = [make_task_model(make_task_data("t1", "Test"))]
        populated = await coordinator.populate_tasks_async(tasks)

        assert populated == 0


# =============================================================================
# Test: Performance Timing Validation
# =============================================================================


@pytest.mark.asyncio
class TestCachePerformanceTiming:
    """Test that cache operations meet performance targets."""

    async def test_cache_lookup_is_fast(
        self,
        cache_provider: EnhancedInMemoryCacheProvider,
        sample_tasks: list[dict[str, Any]],
    ) -> None:
        """Cache lookup completes in < 100ms for reasonable task counts.

        This validates that in-memory cache lookup is efficient.
        """
        coordinator = TaskCacheCoordinator(cache_provider)

        # Populate cache
        task_models = [make_task_model(t) for t in sample_tasks]
        await coordinator.populate_tasks_async(task_models)

        # Time the lookup
        task_gids = [t["gid"] for t in sample_tasks]
        start = time.perf_counter()
        await coordinator.lookup_tasks_async(task_gids)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Assert: Lookup is fast (< 100ms for 5 tasks)
        assert elapsed_ms < 100, (
            f"Cache lookup took {elapsed_ms:.2f}ms, expected < 100ms"
        )

    async def test_cache_population_is_fast(
        self,
        cache_provider: EnhancedInMemoryCacheProvider,
        sample_tasks: list[dict[str, Any]],
    ) -> None:
        """Cache population completes in < 100ms for reasonable task counts.

        This validates that in-memory cache population is efficient.
        """
        coordinator = TaskCacheCoordinator(cache_provider)
        task_models = [make_task_model(t) for t in sample_tasks]

        # Time the population
        start = time.perf_counter()
        await coordinator.populate_tasks_async(task_models)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Assert: Population is fast (< 100ms for 5 tasks)
        assert elapsed_ms < 100, (
            f"Cache population took {elapsed_ms:.2f}ms, expected < 100ms"
        )


# =============================================================================
# Test: TaskCacheResult Metrics
# =============================================================================


class TestTaskCacheResultMetrics:
    """Test TaskCacheResult metric calculations."""

    def test_hit_rate_100_percent(self) -> None:
        """Hit rate is 1.0 when all from cache."""
        from autom8_asana.dataframes.builders.task_cache import TaskCacheResult

        result = TaskCacheResult(
            cached_tasks=[make_task_model(make_task_data("t1", "Test"))],
            fetched_tasks=[],
            cache_hits=5,
            cache_misses=0,
            all_tasks=[],
        )

        assert result.hit_rate == 1.0

    def test_hit_rate_0_percent(self) -> None:
        """Hit rate is 0.0 when none from cache."""
        from autom8_asana.dataframes.builders.task_cache import TaskCacheResult

        result = TaskCacheResult(
            cached_tasks=[],
            fetched_tasks=[make_task_model(make_task_data("t1", "Test"))],
            cache_hits=0,
            cache_misses=5,
            all_tasks=[],
        )

        assert result.hit_rate == 0.0

    def test_hit_rate_50_percent(self) -> None:
        """Hit rate is 0.5 when half from cache."""
        from autom8_asana.dataframes.builders.task_cache import TaskCacheResult

        result = TaskCacheResult(
            cached_tasks=[],
            fetched_tasks=[],
            cache_hits=3,
            cache_misses=3,
            all_tasks=[],
        )

        assert result.hit_rate == pytest.approx(0.5)

    def test_hit_rate_empty(self) -> None:
        """Hit rate is 0.0 when no lookups performed."""
        from autom8_asana.dataframes.builders.task_cache import TaskCacheResult

        result = TaskCacheResult(
            cached_tasks=[],
            fetched_tasks=[],
            cache_hits=0,
            cache_misses=0,
            all_tasks=[],
        )

        assert result.hit_rate == 0.0

    def test_total_tasks_property(self) -> None:
        """total_tasks returns length of all_tasks."""
        from autom8_asana.dataframes.builders.task_cache import TaskCacheResult

        tasks = [
            make_task_model(make_task_data("t1", "Test 1")),
            make_task_model(make_task_data("t2", "Test 2")),
        ]

        result = TaskCacheResult(
            cached_tasks=[],
            fetched_tasks=[],
            cache_hits=0,
            cache_misses=0,
            all_tasks=tasks,
        )

        assert result.total_tasks == 2


# =============================================================================
# Test: Logging Observability
# =============================================================================


@pytest.mark.asyncio
class TestCacheLoggingObservability:
    """Test that cache operations produce structured log events.

    Per FR-OBS-001, FR-OBS-002: Cache operations should log
    structured events with metrics for observability.
    """

    async def test_lookup_logs_debug_events(
        self,
        cache_provider: EnhancedInMemoryCacheProvider,
        sample_tasks: list[dict[str, Any]],
        mocker: MockerFixture,
    ) -> None:
        """Cache lookup produces debug log events.

        Verifies that task_cache_lookup_started and task_cache_lookup_completed
        events are logged with appropriate data.
        """
        from unittest.mock import MagicMock

        mock_logger = MagicMock()
        mocker.patch("autom8_asana.dataframes.builders.task_cache.logger", mock_logger)

        coordinator = TaskCacheCoordinator(cache_provider)
        task_gids = [t["gid"] for t in sample_tasks]

        await coordinator.lookup_tasks_async(task_gids)

        # Check debug was called with expected event names
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("task_cache_lookup_started" in call for call in debug_calls)
        assert any("task_cache_lookup_completed" in call for call in debug_calls)

    async def test_population_logs_debug_events(
        self,
        cache_provider: EnhancedInMemoryCacheProvider,
        sample_tasks: list[dict[str, Any]],
        mocker: MockerFixture,
    ) -> None:
        """Cache population produces debug log events.

        Verifies that task_cache_population_started and
        task_cache_population_completed events are logged.
        """
        from unittest.mock import MagicMock

        mock_logger = MagicMock()
        mocker.patch("autom8_asana.dataframes.builders.task_cache.logger", mock_logger)

        coordinator = TaskCacheCoordinator(cache_provider)
        task_models = [make_task_model(t) for t in sample_tasks]

        await coordinator.populate_tasks_async(task_models)

        # Check debug was called with expected event names
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("task_cache_population_started" in call for call in debug_calls)
        assert any("task_cache_population_completed" in call for call in debug_calls)
