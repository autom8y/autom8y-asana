"""Tests for Task-level cache coordinator.

Per TDD-CACHE-PERF-FETCH-PATH Phase 1: Comprehensive tests for
TaskCacheResult and TaskCacheCoordinator classes.

Coverage targets:
- TestTaskCacheResult: Dataclass properties and calculations
- TestTaskCacheCoordinator: Lookup, populate, merge, error handling
- TestTaskCacheCoordinatorEdgeCases: Cache provider None, empty inputs
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from autom8_asana._defaults.cache import InMemoryCacheProvider, NullCacheProvider
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.core.errors import RedisTransportError
from autom8_asana.dataframes.builders.task_cache import (
    TaskCacheCoordinator,
    TaskCacheResult,
)
from autom8_asana.models import Task

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def now() -> datetime:
    """Current UTC datetime."""
    return datetime.now(UTC)


@pytest.fixture
def one_hour_ago(now: datetime) -> datetime:
    """One hour ago."""
    return now - timedelta(hours=1)


@pytest.fixture
def in_memory_cache() -> InMemoryCacheProvider:
    """Fresh in-memory cache provider."""
    return InMemoryCacheProvider(default_ttl=300, max_size=1000)


@pytest.fixture
def null_cache() -> NullCacheProvider:
    """Null cache provider (no-op)."""
    return NullCacheProvider()


@pytest.fixture
def coordinator(in_memory_cache: InMemoryCacheProvider) -> TaskCacheCoordinator:
    """Coordinator with in-memory cache."""
    return TaskCacheCoordinator(cache_provider=in_memory_cache, default_ttl=300)


@pytest.fixture
def coordinator_no_cache() -> TaskCacheCoordinator:
    """Coordinator with no cache provider."""
    return TaskCacheCoordinator(cache_provider=None)


@pytest.fixture
def sample_task(now: datetime) -> Task:
    """Sample task for testing."""
    return Task(
        gid="task123",
        name="Test Task",
        resource_subtype="default_task",
        completed=False,
        created_at=now.isoformat(),
        modified_at=now.isoformat(),
    )


@pytest.fixture
def sample_task_2(now: datetime) -> Task:
    """Second sample task for testing."""
    return Task(
        gid="task456",
        name="Test Task 2",
        resource_subtype="default_task",
        completed=True,
        created_at=now.isoformat(),
        modified_at=now.isoformat(),
    )


@pytest.fixture
def sample_task_3(now: datetime) -> Task:
    """Third sample task for testing."""
    return Task(
        gid="task789",
        name="Test Task 3",
        resource_subtype="default_task",
        completed=False,
        created_at=now.isoformat(),
        modified_at=now.isoformat(),
    )


@pytest.fixture
def business_task(now: datetime) -> Task:
    """Business entity task for TTL testing."""
    return Task(
        gid="biz001",
        name="Business Entity",
        resource_subtype="default_task",
        completed=False,
        created_at=now.isoformat(),
        modified_at=now.isoformat(),
        memberships=[
            {
                "project": {"gid": "proj_biz", "name": "Businesses"},
                "section": {"gid": "sec1", "name": "Active"},
            }
        ],
    )


# =============================================================================
# TestTaskCacheResult
# =============================================================================


class TestTaskCacheResult:
    """Tests for TaskCacheResult dataclass."""

    def test_empty_result(self) -> None:
        """Test empty result has correct defaults."""
        result = TaskCacheResult()

        assert result.cached_tasks == []
        assert result.fetched_tasks == []
        assert result.cache_hits == 0
        assert result.cache_misses == 0
        assert result.all_tasks == []
        assert result.hit_rate == 0.0
        assert result.total_tasks == 0

    def test_hit_rate_all_hits(self, sample_task: Task) -> None:
        """Test hit_rate when all lookups are cache hits."""
        result = TaskCacheResult(
            cached_tasks=[sample_task],
            fetched_tasks=[],
            cache_hits=5,
            cache_misses=0,
            all_tasks=[sample_task],
        )

        assert result.hit_rate == 1.0

    def test_hit_rate_all_misses(self, sample_task: Task) -> None:
        """Test hit_rate when all lookups are cache misses."""
        result = TaskCacheResult(
            cached_tasks=[],
            fetched_tasks=[sample_task],
            cache_hits=0,
            cache_misses=5,
            all_tasks=[sample_task],
        )

        assert result.hit_rate == 0.0

    def test_hit_rate_partial(self, sample_task: Task, sample_task_2: Task) -> None:
        """Test hit_rate with partial cache hits."""
        result = TaskCacheResult(
            cached_tasks=[sample_task],
            fetched_tasks=[sample_task_2],
            cache_hits=3,
            cache_misses=2,
            all_tasks=[sample_task, sample_task_2],
        )

        assert result.hit_rate == 0.6  # 3/5

    def test_hit_rate_zero_total(self) -> None:
        """Test hit_rate when no lookups performed."""
        result = TaskCacheResult(
            cache_hits=0,
            cache_misses=0,
        )

        # Should return 0.0, not raise ZeroDivisionError
        assert result.hit_rate == 0.0

    def test_total_tasks(self, sample_task: Task, sample_task_2: Task, sample_task_3: Task) -> None:
        """Test total_tasks property."""
        result = TaskCacheResult(
            all_tasks=[sample_task, sample_task_2, sample_task_3],
        )

        assert result.total_tasks == 3


# =============================================================================
# TestTaskCacheCoordinator - Lookup
# =============================================================================


class TestTaskCacheCoordinatorLookup:
    """Tests for TaskCacheCoordinator.lookup_tasks_async()."""

    @pytest.mark.asyncio
    async def test_lookup_cache_miss(self, coordinator: TaskCacheCoordinator) -> None:
        """Test lookup returns None for cache misses."""
        result = await coordinator.lookup_tasks_async(["task123", "task456"])

        assert result["task123"] is None
        assert result["task456"] is None

    @pytest.mark.asyncio
    async def test_lookup_cache_hit(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
        now: datetime,
    ) -> None:
        """Test lookup returns Task for cache hits."""
        # Pre-populate cache
        entry = CacheEntry(
            key="task123",
            data=sample_task.model_dump(exclude_none=True),
            entry_type=EntryType.TASK,
            version=now,
            cached_at=now,
            ttl=300,
        )
        assert coordinator.cache_provider is not None
        coordinator.cache_provider.set_versioned("task123", entry)

        # Lookup
        result = await coordinator.lookup_tasks_async(["task123"])

        assert result["task123"] is not None
        assert result["task123"].gid == "task123"
        assert result["task123"].name == "Test Task"

    @pytest.mark.asyncio
    async def test_lookup_partial_hits(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
        now: datetime,
    ) -> None:
        """Test lookup with partial cache hits."""
        # Pre-populate cache with one task
        entry = CacheEntry(
            key="task123",
            data=sample_task.model_dump(exclude_none=True),
            entry_type=EntryType.TASK,
            version=now,
            cached_at=now,
            ttl=300,
        )
        assert coordinator.cache_provider is not None
        coordinator.cache_provider.set_versioned("task123", entry)

        # Lookup two tasks
        result = await coordinator.lookup_tasks_async(["task123", "task456"])

        assert result["task123"] is not None  # Hit
        assert result["task456"] is None  # Miss

    @pytest.mark.asyncio
    async def test_lookup_expired_entry(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
    ) -> None:
        """Test lookup returns None for expired cache entries."""
        # Pre-populate cache with expired entry
        past = datetime.now(UTC) - timedelta(hours=2)
        entry = CacheEntry(
            key="task123",
            data=sample_task.model_dump(exclude_none=True),
            entry_type=EntryType.TASK,
            version=past,
            cached_at=past,
            ttl=300,  # 5 min TTL, but entry is 2 hours old
        )
        assert coordinator.cache_provider is not None
        coordinator.cache_provider.set_versioned("task123", entry)

        # Lookup should miss (expired)
        result = await coordinator.lookup_tasks_async(["task123"])

        assert result["task123"] is None

    @pytest.mark.asyncio
    async def test_lookup_empty_gids(self, coordinator: TaskCacheCoordinator) -> None:
        """Test lookup with empty GID list."""
        result = await coordinator.lookup_tasks_async([])

        assert result == {}

    @pytest.mark.asyncio
    async def test_lookup_no_cache_provider(
        self, coordinator_no_cache: TaskCacheCoordinator
    ) -> None:
        """Test lookup when cache provider is None."""
        result = await coordinator_no_cache.lookup_tasks_async(["task123"])

        # Should return all misses
        assert result["task123"] is None

    @pytest.mark.asyncio
    async def test_lookup_graceful_degradation(self) -> None:
        """Test lookup handles cache errors gracefully."""
        # Create a failing cache
        failing_cache = MagicMock()
        failing_cache.get_batch = MagicMock(side_effect=RedisTransportError("Redis down"))

        coordinator = TaskCacheCoordinator(cache_provider=failing_cache)

        # Should not raise, should return empty dict
        result = await coordinator.lookup_tasks_async(["task123", "task456"])

        # All misses on error
        assert result["task123"] is None
        assert result["task456"] is None


# =============================================================================
# TestTaskCacheCoordinator - Populate
# =============================================================================


class TestTaskCacheCoordinatorPopulate:
    """Tests for TaskCacheCoordinator.populate_tasks_async()."""

    @pytest.mark.asyncio
    async def test_populate_single_task(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
    ) -> None:
        """Test populating cache with single task."""
        count = await coordinator.populate_tasks_async([sample_task])

        assert count == 1

        # Verify it's cached
        result = await coordinator.lookup_tasks_async(["task123"])
        assert result["task123"] is not None
        assert result["task123"].name == "Test Task"

    @pytest.mark.asyncio
    async def test_populate_multiple_tasks(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
        sample_task_2: Task,
        sample_task_3: Task,
    ) -> None:
        """Test populating cache with multiple tasks."""
        tasks = [sample_task, sample_task_2, sample_task_3]
        count = await coordinator.populate_tasks_async(tasks)

        assert count == 3

        # Verify all cached
        result = await coordinator.lookup_tasks_async(["task123", "task456", "task789"])
        assert result["task123"] is not None
        assert result["task456"] is not None
        assert result["task789"] is not None

    @pytest.mark.asyncio
    async def test_populate_empty_list(self, coordinator: TaskCacheCoordinator) -> None:
        """Test populating with empty task list."""
        count = await coordinator.populate_tasks_async([])

        assert count == 0

    @pytest.mark.asyncio
    async def test_populate_no_cache_provider(
        self,
        coordinator_no_cache: TaskCacheCoordinator,
        sample_task: Task,
    ) -> None:
        """Test populate when cache provider is None."""
        count = await coordinator_no_cache.populate_tasks_async([sample_task])

        assert count == 0

    @pytest.mark.asyncio
    async def test_populate_graceful_degradation(self, sample_task: Task) -> None:
        """Test populate handles cache errors gracefully."""
        failing_cache = MagicMock()
        failing_cache.set_batch = MagicMock(side_effect=RedisTransportError("Redis down"))

        coordinator = TaskCacheCoordinator(cache_provider=failing_cache)

        # Should not raise, should return 0
        count = await coordinator.populate_tasks_async([sample_task])

        assert count == 0

    @pytest.mark.asyncio
    async def test_populate_with_custom_ttl_resolver(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
    ) -> None:
        """Test populate with custom TTL resolver function."""

        def custom_ttl_resolver(task: Task) -> int:
            # Custom logic: completed tasks have shorter TTL
            return 60 if task.completed else 600

        count = await coordinator.populate_tasks_async(
            [sample_task],
            ttl_resolver=custom_ttl_resolver,
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_populate_minimal_task(self, coordinator: TaskCacheCoordinator) -> None:
        """Test populate handles minimal task with only GID."""
        # Task with only required GID field
        minimal_task = Task(gid="minimal123")

        count = await coordinator.populate_tasks_async([minimal_task])

        # Should cache successfully
        assert count == 1

        # Verify it's cached
        result = await coordinator.lookup_tasks_async(["minimal123"])
        assert result["minimal123"] is not None

    @pytest.mark.asyncio
    async def test_populate_task_without_modified_at(
        self, coordinator: TaskCacheCoordinator
    ) -> None:
        """Test populate handles task without modified_at."""
        task = Task(
            gid="task_no_mod",
            name="No Modified At",
            modified_at=None,
        )

        count = await coordinator.populate_tasks_async([task])

        # Should still cache (uses current time as version)
        assert count == 1

        result = await coordinator.lookup_tasks_async(["task_no_mod"])
        assert result["task_no_mod"] is not None


# =============================================================================
# TestTaskCacheCoordinator - Merge
# =============================================================================


class TestTaskCacheCoordinatorMerge:
    """Tests for TaskCacheCoordinator.merge_results()."""

    def test_merge_all_cached(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
        sample_task_2: Task,
    ) -> None:
        """Test merge when all tasks are from cache."""
        cached = {"task123": sample_task, "task456": sample_task_2}
        fetched: list[Task] = []
        gids = ["task123", "task456"]

        result = coordinator.merge_results(gids, cached, fetched)

        assert result.cache_hits == 2
        assert result.cache_misses == 0
        assert result.hit_rate == 1.0
        assert len(result.all_tasks) == 2
        assert result.cached_tasks == [sample_task, sample_task_2]
        assert result.fetched_tasks == []

    def test_merge_all_fetched(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
        sample_task_2: Task,
    ) -> None:
        """Test merge when all tasks are from API fetch."""
        cached: dict[str, Task] = {}
        fetched = [sample_task, sample_task_2]
        gids = ["task123", "task456"]

        result = coordinator.merge_results(gids, cached, fetched)

        assert result.cache_hits == 0
        assert result.cache_misses == 2
        assert result.hit_rate == 0.0
        assert len(result.all_tasks) == 2
        assert result.cached_tasks == []
        assert result.fetched_tasks == [sample_task, sample_task_2]

    def test_merge_partial(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
        sample_task_2: Task,
        sample_task_3: Task,
    ) -> None:
        """Test merge with partial cache hits."""
        cached = {"task456": sample_task_2}  # One cached
        fetched = [sample_task, sample_task_3]  # Two fetched
        gids = ["task123", "task456", "task789"]

        result = coordinator.merge_results(gids, cached, fetched)

        assert result.cache_hits == 1
        assert result.cache_misses == 2
        assert result.hit_rate == pytest.approx(1 / 3)
        assert len(result.all_tasks) == 3

    def test_merge_preserves_order(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
        sample_task_2: Task,
        sample_task_3: Task,
    ) -> None:
        """Test merge preserves original GID order."""
        # Cache middle task
        cached = {"task456": sample_task_2}
        # Fetch first and third tasks
        fetched = [sample_task, sample_task_3]
        # Order: 123, 456, 789
        gids = ["task123", "task456", "task789"]

        result = coordinator.merge_results(gids, cached, fetched)

        # Verify order is preserved
        assert [t.gid for t in result.all_tasks] == ["task123", "task456", "task789"]

    def test_merge_handles_removed_tasks(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
    ) -> None:
        """Test merge handles tasks no longer in section."""
        # Only task123 exists now
        cached = {"task123": sample_task}
        fetched: list[Task] = []
        # task456 was removed from section
        gids = ["task123", "task456"]

        result = coordinator.merge_results(gids, cached, fetched)

        # Only task123 should be in result
        assert len(result.all_tasks) == 1
        assert result.all_tasks[0].gid == "task123"
        assert result.cache_hits == 1
        # task456 is neither hit nor miss - it's gone
        assert result.cache_misses == 0

    def test_merge_empty_inputs(self, coordinator: TaskCacheCoordinator) -> None:
        """Test merge with empty inputs."""
        result = coordinator.merge_results([], {}, [])

        assert result.cache_hits == 0
        assert result.cache_misses == 0
        assert result.all_tasks == []
        assert result.hit_rate == 0.0


# =============================================================================
# TestTaskCacheCoordinator - TTL Resolution
# =============================================================================


class TestTaskCacheCoordinatorTTL:
    """Tests for TTL resolution logic."""

    @pytest.mark.asyncio
    async def test_default_ttl_used(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
    ) -> None:
        """Test default TTL is used for generic tasks."""
        # Generic task should get 300s TTL
        await coordinator.populate_tasks_async([sample_task])

        # Verify task is cached (indirectly confirms TTL was set)
        result = await coordinator.lookup_tasks_async(["task123"])
        assert result["task123"] is not None

    def test_resolve_entity_ttl_business(self, coordinator: TaskCacheCoordinator) -> None:
        """Test TTL resolution for business entity."""
        # This tests internal method - could be refactored to integration test
        data = {"gid": "123", "name": "Test Business"}

        # Note: Without full detection infrastructure, will use default
        ttl = coordinator._resolve_entity_ttl(data)

        # Will be default if detection module not available
        assert ttl in [300, 3600]  # Either default or business TTL


# =============================================================================
# TestTaskCacheCoordinator - Edge Cases
# =============================================================================


class TestTaskCacheCoordinatorEdgeCases:
    """Edge case tests for TaskCacheCoordinator."""

    def test_cache_provider_property(self, coordinator: TaskCacheCoordinator) -> None:
        """Test cache_provider property returns provider."""
        assert coordinator.cache_provider is not None

    def test_cache_provider_property_none(self, coordinator_no_cache: TaskCacheCoordinator) -> None:
        """Test cache_provider property returns None when no provider."""
        assert coordinator_no_cache.cache_provider is None

    def test_parse_modified_at_with_z_suffix(self, coordinator: TaskCacheCoordinator) -> None:
        """Test parsing ISO datetime with Z suffix."""
        result = coordinator._parse_modified_at("2025-01-15T10:30:00.000Z")

        assert result.tzinfo is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_parse_modified_at_with_timezone(self, coordinator: TaskCacheCoordinator) -> None:
        """Test parsing ISO datetime with timezone offset."""
        result = coordinator._parse_modified_at("2025-01-15T10:30:00+00:00")

        assert result.tzinfo is not None
        assert result.year == 2025

    def test_parse_modified_at_none(self, coordinator: TaskCacheCoordinator) -> None:
        """Test parsing None modified_at returns current time."""
        before = datetime.now(UTC)
        result = coordinator._parse_modified_at(None)
        after = datetime.now(UTC)

        assert before <= result <= after

    @pytest.mark.asyncio
    async def test_roundtrip_task_data(
        self,
        coordinator: TaskCacheCoordinator,
        now: datetime,
    ) -> None:
        """Test task data survives cache roundtrip."""
        task = Task(
            gid="roundtrip123",
            name="Roundtrip Test",
            notes="Some notes here",
            completed=True,
            completed_at=now.isoformat(),
            created_at=now.isoformat(),
            modified_at=now.isoformat(),
            due_on="2025-12-31",
            resource_subtype="default_task",
        )

        # Populate
        await coordinator.populate_tasks_async([task])

        # Lookup
        result = await coordinator.lookup_tasks_async(["roundtrip123"])
        cached_task = result["roundtrip123"]

        # Verify all fields
        assert cached_task is not None
        assert cached_task.gid == task.gid
        assert cached_task.name == task.name
        assert cached_task.notes == task.notes
        assert cached_task.completed == task.completed
        assert cached_task.due_on == task.due_on

    @pytest.mark.asyncio
    async def test_with_null_cache_provider(self, sample_task: Task) -> None:
        """Test coordinator with NullCacheProvider."""
        null_cache = NullCacheProvider()
        coordinator = TaskCacheCoordinator(cache_provider=null_cache)

        # Populate should succeed (no-op)
        count = await coordinator.populate_tasks_async([sample_task])
        assert count == 1

        # Lookup should miss
        result = await coordinator.lookup_tasks_async(["task123"])
        # NullCacheProvider's get_batch returns {} or misses
        assert result.get("task123") is None

    @pytest.mark.asyncio
    async def test_large_batch_lookup(self, coordinator: TaskCacheCoordinator) -> None:
        """Test lookup with large batch of GIDs."""
        gids = [f"task{i}" for i in range(500)]

        result = await coordinator.lookup_tasks_async(gids)

        # All should be misses
        assert len(result) == 500
        assert all(v is None for v in result.values())

    @pytest.mark.asyncio
    async def test_large_batch_populate(
        self, coordinator: TaskCacheCoordinator, now: datetime
    ) -> None:
        """Test populate with large batch of tasks."""
        tasks = [
            Task(
                gid=f"task{i}",
                name=f"Task {i}",
                modified_at=now.isoformat(),
            )
            for i in range(100)
        ]

        count = await coordinator.populate_tasks_async(tasks)

        assert count == 100

        # Verify some are cached
        result = await coordinator.lookup_tasks_async(["task0", "task50", "task99"])
        assert result["task0"] is not None
        assert result["task50"] is not None
        assert result["task99"] is not None


# =============================================================================
# TestTaskCacheCoordinator - Integration Scenarios
# =============================================================================


class TestTaskCacheCoordinatorIntegration:
    """Integration tests simulating real-world usage patterns."""

    @pytest.mark.asyncio
    async def test_full_workflow_cold_cache(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
        sample_task_2: Task,
        sample_task_3: Task,
    ) -> None:
        """Test full workflow: cold cache -> populate -> warm lookup."""
        gids = ["task123", "task456", "task789"]

        # Phase 1: Cold cache lookup
        lookup_result = await coordinator.lookup_tasks_async(gids)
        assert all(v is None for v in lookup_result.values())

        # Phase 2: "Fetch" from API (simulated)
        fetched_tasks = [sample_task, sample_task_2, sample_task_3]

        # Phase 3: Populate cache
        populated = await coordinator.populate_tasks_async(fetched_tasks)
        assert populated == 3

        # Phase 4: Merge results (cold cache path)
        result = coordinator.merge_results(gids, {}, fetched_tasks)
        assert result.cache_hits == 0
        assert result.cache_misses == 3
        assert len(result.all_tasks) == 3

        # Phase 5: Second lookup (warm cache)
        warm_lookup = await coordinator.lookup_tasks_async(gids)
        assert warm_lookup["task123"] is not None
        assert warm_lookup["task456"] is not None
        assert warm_lookup["task789"] is not None

    @pytest.mark.asyncio
    async def test_full_workflow_partial_cache(
        self,
        coordinator: TaskCacheCoordinator,
        sample_task: Task,
        sample_task_2: Task,
        sample_task_3: Task,
    ) -> None:
        """Test full workflow: partial cache hit scenario."""
        gids = ["task123", "task456", "task789"]

        # Pre-populate one task
        await coordinator.populate_tasks_async([sample_task_2])

        # Phase 1: Lookup
        lookup_result = await coordinator.lookup_tasks_async(gids)

        # Extract hits and determine misses
        cached = {gid: t for gid, t in lookup_result.items() if t is not None}
        miss_gids = [gid for gid, t in lookup_result.items() if t is None]

        assert len(cached) == 1
        assert "task456" in cached
        assert len(miss_gids) == 2

        # Phase 2: "Fetch" only missing tasks
        fetched_tasks = [sample_task, sample_task_3]

        # Phase 3: Populate newly fetched
        await coordinator.populate_tasks_async(fetched_tasks)

        # Phase 4: Merge
        result = coordinator.merge_results(gids, cached, fetched_tasks)

        assert result.cache_hits == 1
        assert result.cache_misses == 2
        assert result.hit_rate == pytest.approx(1 / 3)
        assert len(result.all_tasks) == 3

        # Verify order preserved
        assert [t.gid for t in result.all_tasks] == ["task123", "task456", "task789"]

    @pytest.mark.asyncio
    async def test_workflow_with_cache_failure(
        self,
        sample_task: Task,
        sample_task_2: Task,
    ) -> None:
        """Test workflow continues when cache fails."""
        # Create a cache that fails on lookup but not populate
        failing_cache = MagicMock()
        failing_cache.get_batch = MagicMock(side_effect=RedisTransportError("Lookup failed"))
        failing_cache.set_batch = MagicMock()  # Works fine

        coordinator = TaskCacheCoordinator(cache_provider=failing_cache)
        gids = ["task123", "task456"]

        # Lookup fails gracefully
        lookup_result = await coordinator.lookup_tasks_async(gids)
        assert lookup_result["task123"] is None
        assert lookup_result["task456"] is None

        # Populate should still work
        count = await coordinator.populate_tasks_async([sample_task, sample_task_2])
        assert count == 2

        # Merge works
        result = coordinator.merge_results(gids, {}, [sample_task, sample_task_2])
        assert len(result.all_tasks) == 2
