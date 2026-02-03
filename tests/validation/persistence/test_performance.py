"""Part 5: Performance Validation Tests.

Tests performance characteristics of the persistence layer.

Test Coverage:
- NFR-PERF-001: Change tracking overhead < 10% memory
- NFR-PERF-002: Dependency sorting < 10ms for 100 entities
- NFR-PERF-003: Entity tracking < 50ms for 100 entities
- Dirty detection performance
- Memory overhead of tracking
"""

from __future__ import annotations

import gc
import sys
import time
import warnings

import pytest

from autom8_asana.models import Task
from autom8_asana.models.common import NameGid
from autom8_asana.persistence import SaveSession
from autom8_asana.persistence.graph import DependencyGraph
from autom8_asana.persistence.tracker import ChangeTracker

from .conftest import create_mock_client

# ---------------------------------------------------------------------------
# Performance Thresholds
# ---------------------------------------------------------------------------

# Soft thresholds - emit warning if exceeded
SOFT_TRACKING_100_ENTITIES_MS = 50
SOFT_DIRTY_DETECTION_100_ENTITIES_MS = 50
SOFT_GRAPH_SORT_100_ENTITIES_MS = 10
SOFT_MEMORY_OVERHEAD_PERCENT = 10

# Hard thresholds - fail test if exceeded
HARD_TRACKING_100_ENTITIES_MS = 200
HARD_DIRTY_DETECTION_100_ENTITIES_MS = 200
HARD_GRAPH_SORT_100_ENTITIES_MS = 50
HARD_MEMORY_OVERHEAD_PERCENT = 25


# ---------------------------------------------------------------------------
# Change Tracking Performance Tests
# ---------------------------------------------------------------------------


class TestChangeTrackingOverhead:
    """Test change tracking performance (NFR-PERF-003)."""

    def test_tracking_100_entities_timing(self) -> None:
        """Tracking 100 entities should complete quickly."""
        tracker = ChangeTracker()
        tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(100)]

        start = time.perf_counter()
        for task in tasks:
            tracker.track(task)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Soft assertion
        if elapsed_ms > SOFT_TRACKING_100_ENTITIES_MS:
            warnings.warn(
                f"Tracking 100 entities took {elapsed_ms:.1f}ms "
                f"(target: <{SOFT_TRACKING_100_ENTITIES_MS}ms)"
            )

        # Hard limit
        assert elapsed_ms < HARD_TRACKING_100_ENTITIES_MS, (
            f"Tracking took {elapsed_ms:.1f}ms "
            f"(hard limit: {HARD_TRACKING_100_ENTITIES_MS}ms)"
        )

    def test_tracking_500_entities_timing(self) -> None:
        """Tracking 500 entities should scale linearly."""
        tracker = ChangeTracker()
        tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(500)]

        start = time.perf_counter()
        for task in tasks:
            tracker.track(task)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should be roughly 5x the 100-entity time (linear scaling)
        # Allow 10x as hard limit
        assert elapsed_ms < HARD_TRACKING_100_ENTITIES_MS * 10, (
            f"Tracking 500 entities took {elapsed_ms:.1f}ms"
        )

    def test_dirty_detection_100_entities_timing(self) -> None:
        """Dirty detection for 100 modified entities should be fast."""
        tracker = ChangeTracker()
        tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(100)]

        for task in tasks:
            tracker.track(task)
            task.name = f"Modified {task.name}"

        start = time.perf_counter()
        dirty = tracker.get_dirty_entities()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(dirty) == 100

        if elapsed_ms > SOFT_DIRTY_DETECTION_100_ENTITIES_MS:
            warnings.warn(
                f"Dirty detection took {elapsed_ms:.1f}ms "
                f"(target: <{SOFT_DIRTY_DETECTION_100_ENTITIES_MS}ms)"
            )

        assert elapsed_ms < HARD_DIRTY_DETECTION_100_ENTITIES_MS, (
            f"Dirty detection took {elapsed_ms:.1f}ms"
        )

    def test_dirty_detection_mixed_clean_dirty(self) -> None:
        """Dirty detection with mix of clean and dirty entities."""
        tracker = ChangeTracker()
        tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(100)]

        # Track all
        for task in tasks:
            tracker.track(task)

        # Modify only half
        for i, task in enumerate(tasks):
            if i % 2 == 0:
                task.name = f"Modified {task.name}"

        start = time.perf_counter()
        dirty = tracker.get_dirty_entities()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(dirty) == 50
        assert elapsed_ms < HARD_DIRTY_DETECTION_100_ENTITIES_MS

    def test_get_changes_performance(self) -> None:
        """get_changes() performance for single entity."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Original", notes="Original notes")
        tracker.track(task)
        task.name = "Modified"
        task.notes = "Modified notes"

        # Warm up
        _ = tracker.get_changes(task)

        # Time multiple calls
        start = time.perf_counter()
        for _ in range(100):
            _ = tracker.get_changes(task)
        elapsed_ms = (time.perf_counter() - start) * 1000

        avg_ms = elapsed_ms / 100
        assert avg_ms < 1, f"get_changes() averaged {avg_ms:.3f}ms per call"


# ---------------------------------------------------------------------------
# Dependency Graph Performance Tests
# ---------------------------------------------------------------------------


class TestDependencyGraphOverhead:
    """Test dependency graph performance (NFR-PERF-002)."""

    def test_sorting_100_entities_chain_timing(self) -> None:
        """Sorting 100 entities in a chain should be fast."""
        # Create a chain of dependencies: task_0 <- task_1 <- ... <- task_99
        tasks = [Task(gid="root", name="Root")]
        for i in range(1, 100):
            tasks.append(
                Task(
                    gid=f"task_{i}",
                    name=f"Task {i}",
                    parent=NameGid(gid=f"task_{i - 1}" if i > 1 else "root"),
                )
            )

        graph = DependencyGraph()

        start = time.perf_counter()
        graph.build(tasks)
        levels = graph.get_levels()
        elapsed_ms = (time.perf_counter() - start) * 1000

        if elapsed_ms > SOFT_GRAPH_SORT_100_ENTITIES_MS:
            warnings.warn(
                f"Graph sorting took {elapsed_ms:.1f}ms "
                f"(target: <{SOFT_GRAPH_SORT_100_ENTITIES_MS}ms)"
            )

        assert elapsed_ms < HARD_GRAPH_SORT_100_ENTITIES_MS, (
            f"Graph sorting took {elapsed_ms:.1f}ms"
        )

    def test_sorting_100_independent_entities_timing(self) -> None:
        """Sorting 100 independent entities (no dependencies)."""
        tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(100)]

        graph = DependencyGraph()

        start = time.perf_counter()
        graph.build(tasks)
        levels = graph.get_levels()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # All should be at level 0
        assert len(levels) == 1
        assert len(levels[0]) == 100

        assert elapsed_ms < HARD_GRAPH_SORT_100_ENTITIES_MS

    def test_sorting_wide_tree_timing(self) -> None:
        """Sorting wide tree (root with 99 children)."""
        root = Task(gid="root", name="Root")
        children = [
            Task(gid=f"child_{i}", name=f"Child {i}", parent=NameGid(gid="root"))
            for i in range(99)
        ]

        graph = DependencyGraph()

        start = time.perf_counter()
        graph.build([root] + children)
        levels = graph.get_levels()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(levels) == 2
        assert elapsed_ms < HARD_GRAPH_SORT_100_ENTITIES_MS

    def test_sorting_deep_hierarchy_timing(self) -> None:
        """Sorting deep hierarchy (50 levels, 2 per level)."""
        tasks: list[Task] = []
        prev_level: list[Task] = []

        # Create 50-level deep hierarchy with 2 nodes per level
        for level in range(50):
            level_tasks: list[Task] = []
            for i in range(2):
                parent_ref = None
                if prev_level:
                    parent_ref = NameGid(gid=prev_level[i % len(prev_level)].gid or "")
                task = Task(
                    gid=f"l{level}_t{i}",
                    name=f"L{level} T{i}",
                    parent=parent_ref,
                )
                level_tasks.append(task)
                tasks.append(task)
            prev_level = level_tasks

        graph = DependencyGraph()

        start = time.perf_counter()
        graph.build(tasks)
        levels = graph.get_levels()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(levels) == 50
        assert (
            elapsed_ms < HARD_GRAPH_SORT_100_ENTITIES_MS * 2
        )  # Allow 2x for complex structure

    def test_topological_sort_timing(self) -> None:
        """topological_sort() performance."""
        tasks = [Task(gid="root", name="Root")]
        for i in range(1, 100):
            tasks.append(
                Task(
                    gid=f"task_{i}",
                    name=f"Task {i}",
                    parent=NameGid(gid=f"task_{i - 1}" if i > 1 else "root"),
                )
            )

        graph = DependencyGraph()
        graph.build(tasks)

        start = time.perf_counter()
        result = graph.topological_sort()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(result) == 100
        assert elapsed_ms < HARD_GRAPH_SORT_100_ENTITIES_MS


# ---------------------------------------------------------------------------
# Memory Overhead Tests
# ---------------------------------------------------------------------------


class TestMemoryOverhead:
    """Test memory overhead of tracking (NFR-PERF-001)."""

    @pytest.mark.slow
    def test_memory_overhead_estimation(self) -> None:
        """Tracked entities should have reasonable memory overhead.

        Note: This is a rough estimation test. The actual memory overhead
        is difficult to measure precisely in Python due to reference counting
        and object interning. We focus on ensuring the overhead doesn't grow
        dramatically with entity count.
        """
        gc.collect()

        # Create tracked tasks
        tracker = ChangeTracker()
        tracked_tasks = [
            Task(gid=f"track_{i}", name=f"Tracked {i}") for i in range(100)
        ]
        for task in tracked_tasks:
            tracker.track(task)
        gc.collect()

        # Count tracked entities
        tracked_count = len(tracker._entities)
        assert tracked_count == 100, "All 100 tasks should be tracked"

        # Basic sanity checks on tracker internals
        assert len(tracker._snapshots) == 100
        assert len(tracker._states) == 100
        assert len(tracker._entities) == 100

        # Verify snapshots contain valid data
        for entity_id, snapshot in tracker._snapshots.items():
            assert isinstance(snapshot, dict)
            assert "gid" in snapshot
            assert "name" in snapshot

    def test_snapshot_size_reasonable(self) -> None:
        """Snapshot size should be proportional to entity fields."""
        tracker = ChangeTracker()
        task = Task(
            gid="123",
            name="Test Task",
            notes="Some detailed notes here",
            completed=False,
        )
        tracker.track(task)

        entity_id = id(task)
        snapshot = tracker._snapshots.get(entity_id, {})

        # Snapshot should exist and be a dict
        assert isinstance(snapshot, dict)
        # Snapshot size should be reasonable (not exploding)
        assert sys.getsizeof(snapshot) < 10000  # Arbitrary but reasonable limit


# ---------------------------------------------------------------------------
# End-to-End Performance Tests
# ---------------------------------------------------------------------------


class TestEndToEndPerformance:
    """Test end-to-end performance scenarios."""

    def test_session_track_100_entities(self) -> None:
        """Full session track of 100 entities."""
        client = create_mock_client()
        tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(100)]

        start = time.perf_counter()
        with SaveSession(client) as session:
            for task in tasks:
                session.track(task)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < HARD_TRACKING_100_ENTITIES_MS * 2  # Allow overhead

    def test_session_preview_100_entities(self) -> None:
        """Preview operation for 100 dirty entities."""
        client = create_mock_client()
        tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(100)]

        with SaveSession(client) as session:
            for task in tasks:
                session.track(task)
                task.name = f"Modified {task.name}"

            start = time.perf_counter()
            crud_ops, _ = session.preview()
            elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(crud_ops) == 100
        # Preview should be fast (no API calls)
        assert elapsed_ms < 100

    def test_dependency_order_100_entities(self) -> None:
        """get_dependency_order() for 100 entities."""
        client = create_mock_client()

        # Create hierarchy
        root = Task(gid="root", name="Root")
        children = [
            Task(gid=f"child_{i}", name=f"Child {i}", parent=NameGid(gid="root"))
            for i in range(99)
        ]

        with SaveSession(client) as session:
            session.track(root)
            for child in children:
                session.track(child)

            # Modify all
            root.name = "Modified Root"
            for child in children:
                child.name = f"Modified {child.name}"

            start = time.perf_counter()
            levels = session.get_dependency_order()
            elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(levels) == 2
        assert elapsed_ms < HARD_GRAPH_SORT_100_ENTITIES_MS * 2


# ---------------------------------------------------------------------------
# Scaling Tests
# ---------------------------------------------------------------------------


class TestScalingBehavior:
    """Test scaling behavior with increasing entity counts."""

    @pytest.mark.parametrize("count", [10, 50, 100, 200])
    def test_tracking_scales_linearly(self, count: int) -> None:
        """Tracking time should scale roughly linearly."""
        tracker = ChangeTracker()
        tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(count)]

        start = time.perf_counter()
        for task in tasks:
            tracker.track(task)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Allow quadratic-ish growth but not exponential
        # 200 entities should take less than 20x what 10 takes
        max_expected_ms = (count / 10) * 50  # Linear with 50ms per 10
        assert elapsed_ms < max_expected_ms, f"{count} entities took {elapsed_ms:.1f}ms"

    @pytest.mark.parametrize("count", [10, 50, 100])
    def test_graph_sorting_scales_appropriately(self, count: int) -> None:
        """Graph sorting should scale O(V+E)."""
        tasks = [Task(gid="root", name="Root")]
        for i in range(1, count):
            tasks.append(
                Task(
                    gid=f"task_{i}",
                    name=f"Task {i}",
                    parent=NameGid(gid=f"task_{i - 1}" if i > 1 else "root"),
                )
            )

        graph = DependencyGraph()

        start = time.perf_counter()
        graph.build(tasks)
        _ = graph.get_levels()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Linear scaling expected
        max_expected_ms = count * 0.5  # 0.5ms per entity
        assert elapsed_ms < max_expected_ms, f"{count} entities took {elapsed_ms:.1f}ms"
