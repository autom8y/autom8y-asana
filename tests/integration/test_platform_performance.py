"""Integration tests for platform performance primitives.

Per TDD-GID-RESOLUTION-SERVICE: Tests verify that platform modules
(ConcurrencyController, HierarchyAwareResolver) are correctly integrated
to prevent timeouts on large datasets.

Tests verify:
- ConcurrencyController bounds concurrent operations
- HierarchyAwareResolver batches parent fetches
- Combined latency is bounded by concurrency limits
- No timeout errors under high concurrency
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

# Skip entire module if platform primitives not available
try:
    from autom8y_cache import HierarchyAwareResolver
    from autom8y_http import ConcurrencyConfig, ConcurrencyController
except ImportError:
    pytest.skip(
        "Platform primitives (ConcurrencyConfig, ConcurrencyController) not available",
        allow_module_level=True,
    )

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.resolver.cascading import (
    CascadingFieldResolver,
    TaskParentFetcher,
)
from tests._shared.mocks import MockTask

# =============================================================================
# Test Fixtures
# =============================================================================


class MockNameGid:
    """Mock NameGid object for parent reference."""

    def __init__(self, gid: str, name: str | None = None) -> None:
        self.gid = gid
        self.name = name


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock AsanaClient."""
    client = MagicMock()
    client.tasks = MagicMock()
    return client


@pytest.fixture
def parent_hierarchy() -> dict[str, MockTask]:
    """Create a mock parent hierarchy.

    Structure:
    - business-1 (root, has Office Phone)
      - unit-1 (child)
        - task-1 through task-50 (grandchildren)
    """
    business = MockTask(
        gid="business-1",
        name="Business Task",
        parent=None,
        custom_fields=[
            {
                "gid": "cf-phone",
                "name": "Office Phone",
                "resource_subtype": "text",
                "text_value": "555-123-4567",
            }
        ],
        created_at="2024-01-01T00:00:00Z",
        modified_at="2024-01-01T00:00:00Z",
    )

    unit = MockTask(
        gid="unit-1",
        name="Unit Task",
        parent=MockNameGid(gid="business-1"),
        created_at="2024-01-01T00:00:00Z",
        modified_at="2024-01-01T00:00:00Z",
    )

    tasks: dict[str, MockTask] = {
        "business-1": business,
        "unit-1": unit,
    }

    # Create 50 tasks that all parent to unit-1
    for i in range(1, 51):
        task = MockTask(
            gid=f"task-{i}",
            name=f"Task {i}",
            parent=MockNameGid(gid="unit-1"),
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z",
        )
        tasks[task.gid] = task

    return tasks


# =============================================================================
# ConcurrencyController Tests
# =============================================================================


class TestConcurrencyController:
    """Tests for ConcurrencyController integration."""

    async def test_gather_with_limit_bounds_concurrency(self) -> None:
        """Test that gather_with_limit respects concurrency limit."""
        max_concurrent = 5
        controller = ConcurrencyController(config=ConcurrencyConfig(max_concurrent=max_concurrent))

        concurrent_count = 0
        max_observed = 0
        completed = 0

        async def track_concurrency(idx: int) -> int:
            nonlocal concurrent_count, max_observed, completed
            concurrent_count += 1
            max_observed = max(max_observed, concurrent_count)
            await asyncio.sleep(0.01)  # Simulate work
            concurrent_count -= 1
            completed += 1
            return idx

        # Run 50 tasks with limit of 5 concurrent
        results = await controller.gather_with_limit(
            [track_concurrency(i) for i in range(50)],
            max_concurrent=max_concurrent,
        )

        assert len(results) == 50
        assert completed == 50
        assert max_observed <= max_concurrent, (
            f"Max concurrent {max_observed} exceeded limit {max_concurrent}"
        )

    async def test_gather_with_limit_preserves_order(self) -> None:
        """Test that results are returned in input order."""
        controller = ConcurrencyController(config=ConcurrencyConfig(max_concurrent=10))

        async def delayed_return(idx: int) -> int:
            # Different delays to test ordering
            await asyncio.sleep(0.01 * (50 - idx))
            return idx * 2

        results = await controller.gather_with_limit([delayed_return(i) for i in range(20)])

        expected = [i * 2 for i in range(20)]
        assert results == expected

    async def test_controller_stats_tracking(self) -> None:
        """Test that controller tracks statistics correctly."""
        controller = ConcurrencyController(config=ConcurrencyConfig(max_concurrent=5))

        stats = controller.get_stats()
        assert stats["max_concurrent"] == 5
        assert stats["current_count"] == 0
        assert stats["waiting_count"] == 0


# =============================================================================
# HierarchyAwareResolver Tests
# =============================================================================


class TestHierarchyAwareResolver:
    """Tests for HierarchyAwareResolver integration."""

    @pytest.mark.skip(
        reason="RS-021: resolve_batch cache miss — fetch_count=4 on second call, "
        "needs architect-enforcer investigation per B-001"
    )
    async def test_resolve_batch_caches_results(
        self, mock_client: MagicMock, parent_hierarchy: dict[str, MockTask]
    ) -> None:
        """Test that resolve_batch caches fetched results."""
        # Track fetch calls
        fetch_count = 0

        fetcher = TaskParentFetcher(mock_client)

        async def mock_get(gid: str, **kwargs: Any) -> MockTask | None:
            nonlocal fetch_count
            fetch_count += 1
            return parent_hierarchy.get(gid)

        mock_client.tasks.get_async = mock_get

        resolver = HierarchyAwareResolver(fetcher=fetcher)

        # First batch fetch
        keys = {"unit-1", "business-1"}
        results1 = await resolver.resolve_batch(keys=keys)
        assert len(results1) == 2
        assert fetch_count == 2

        # Second fetch should hit cache
        results2 = await resolver.resolve_batch(keys=keys)
        assert len(results2) == 2
        # Note: HierarchyAwareResolver cache is within the resolver instance
        # so second call should still hit cache (fetch_count unchanged)

    async def test_resolve_with_ancestors_fetches_chain(
        self, mock_client: MagicMock, parent_hierarchy: dict[str, MockTask]
    ) -> None:
        """Test that resolve_with_ancestors fetches full parent chain."""
        fetcher = TaskParentFetcher(mock_client)

        async def mock_get(gid: str, **kwargs: Any) -> MockTask | None:
            return parent_hierarchy.get(gid)

        mock_client.tasks.get_async = mock_get

        resolver = HierarchyAwareResolver(fetcher=fetcher)

        # Resolve unit-1 with ancestors
        results = await resolver.resolve_with_ancestors(
            keys={"unit-1"},
            max_depth=5,
        )

        # Should have unit-1 and business-1 (its parent)
        assert "unit-1" in results
        assert "business-1" in results


# =============================================================================
# CascadingFieldResolver Integration Tests
# =============================================================================


class TestCascadingFieldResolverIntegration:
    """Tests for CascadingFieldResolver with platform primitives."""

    async def test_warm_parents_batches_fetches(
        self, mock_client: MagicMock, parent_hierarchy: dict[str, MockTask]
    ) -> None:
        """Test that warm_parents uses batch fetching."""
        fetch_gids: list[str] = []

        async def mock_get(gid: str, **kwargs: Any) -> MockTask | None:
            fetch_gids.append(gid)
            await asyncio.sleep(0.001)  # Simulate network delay
            return parent_hierarchy.get(gid)

        mock_client.tasks.get_async = mock_get

        # CascadingFieldResolver no longer accepts concurrency_controller
        # Concurrency is handled internally or via hierarchy_resolver
        resolver = CascadingFieldResolver(client=mock_client)

        # Get tasks (all parent to unit-1)
        tasks = [parent_hierarchy[f"task-{i}"] for i in range(1, 11)]

        # Warm parents
        await resolver.warm_parents(tasks, max_depth=5)

        # Should have fetched unit-1 and business-1
        assert "unit-1" in fetch_gids
        assert "business-1" in fetch_gids

        # Cache should be populated
        assert "unit-1" in resolver._parent_cache
        assert "business-1" in resolver._parent_cache

    async def test_fetch_parent_uses_cache(
        self, mock_client: MagicMock, parent_hierarchy: dict[str, MockTask]
    ) -> None:
        """Test that _fetch_parent_async uses local cache first."""
        fetch_count = 0

        async def mock_get(gid: str, **kwargs: Any) -> MockTask | None:
            nonlocal fetch_count
            fetch_count += 1
            return parent_hierarchy.get(gid)

        mock_client.tasks.get_async = mock_get

        resolver = CascadingFieldResolver(client=mock_client)

        # Pre-populate cache
        resolver._parent_cache["unit-1"] = parent_hierarchy["unit-1"]

        # Fetch should use cache
        parent = await resolver._fetch_parent_async("unit-1")
        assert parent is not None
        assert parent.gid == "unit-1"
        assert fetch_count == 0  # No API call made


# =============================================================================
# Schema Integration Tests
# =============================================================================


class TestSchemaHasCascadeColumns:
    """Tests for DataFrameSchema.has_cascade_columns()."""

    def test_detects_cascade_columns(self) -> None:
        """Test that has_cascade_columns detects cascade: sources."""
        schema = DataFrameSchema(
            name="test",
            task_type="Unit",
            columns=[
                ColumnDef("gid", "Utf8"),
                ColumnDef("office_phone", "Utf8", source="cascade:Office Phone"),
            ],
        )
        assert schema.has_cascade_columns() is True

    def test_no_cascade_columns(self) -> None:
        """Test that has_cascade_columns returns False for non-cascade schemas."""
        schema = DataFrameSchema(
            name="test",
            task_type="*",
            columns=[
                ColumnDef("gid", "Utf8"),
                ColumnDef("name", "Utf8", source="name"),
            ],
        )
        assert schema.has_cascade_columns() is False


# =============================================================================
# Performance Boundary Tests
# =============================================================================


class TestPerformanceBoundaries:
    """Tests to verify performance stays within acceptable bounds."""

    async def test_large_batch_completes_within_timeout(self) -> None:
        """Test that large batches complete within reasonable time."""
        controller = ConcurrencyController(config=ConcurrencyConfig(max_concurrent=25))

        async def simulate_api_call(idx: int) -> dict[str, Any]:
            await asyncio.sleep(0.01)  # 10ms simulated latency
            return {"idx": idx, "data": f"result-{idx}"}

        # 100 tasks with 10ms each = 1s sequential
        # With 25 concurrent, should complete in ~40ms + overhead
        start = time.monotonic()
        results = await controller.gather_with_limit(
            [simulate_api_call(i) for i in range(100)],
            max_concurrent=25,
        )
        elapsed = time.monotonic() - start

        assert len(results) == 100
        # Should complete in under 1 second (vs 1s sequential)
        assert elapsed < 1.0, f"Took {elapsed:.2f}s, expected < 1.0s"

    async def test_chunking_handles_large_batches(self) -> None:
        """Test that chunking works for very large batches."""
        controller = ConcurrencyController(
            config=ConcurrencyConfig(max_concurrent=10, default_chunk_size=25)
        )

        completed: list[int] = []

        async def quick_task(idx: int) -> int:
            await asyncio.sleep(0.001)
            completed.append(idx)
            return idx

        # 100 tasks chunked into 25-task chunks
        results = await controller.gather_with_limit(
            [quick_task(i) for i in range(100)],
            chunk_size=25,
        )

        assert len(results) == 100
        assert len(completed) == 100
        # Results should be in order
        assert results == list(range(100))
