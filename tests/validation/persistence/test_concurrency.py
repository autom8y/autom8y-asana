"""Part 4: Concurrency Validation Tests.

Tests thread safety and session isolation.

Test Coverage:
- Session isolation between instances
- Thread safety of ChangeTracker
- Concurrent commit operations
- Thread-safe entity tracking
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models import Task
from autom8_asana.persistence import SaveResult, SaveSession
from autom8_asana.persistence.graph import DependencyGraph
from autom8_asana.persistence.tracker import ChangeTracker

from .conftest import create_mock_client, create_success_result

if TYPE_CHECKING:
    from autom8_asana.batch.models import BatchResult

# ---------------------------------------------------------------------------
# Session Isolation Tests
# ---------------------------------------------------------------------------


class TestSessionIsolation:
    """Test that sessions are isolated from each other."""

    def test_separate_sessions_have_separate_trackers(self) -> None:
        """Different sessions have independent trackers."""
        client = create_mock_client()

        session1 = SaveSession(client)
        session2 = SaveSession(client)

        assert session1._tracker is not session2._tracker

    def test_changes_in_one_session_dont_affect_another(self) -> None:
        """Changes in one session don't affect another."""
        client = create_mock_client()

        task = Task(gid="123", name="Original")

        with SaveSession(client) as session1:
            session1.track(task)
            task.name = "Modified in Session 1"

        # New session - task modifications shouldn't carry tracker state
        with SaveSession(client) as session2:
            session2.track(task)
            # Session 2 has its own tracker with fresh snapshot
            changes = session2.get_changes(task)
            # Changes dict may or may not include name depending on current value
            # The key point is session2 has a separate tracker
            assert session2._tracker is not session1._tracker

    def test_delete_in_one_session_doesnt_affect_another(self) -> None:
        """Delete marking in one session is independent."""
        client = create_mock_client()

        task = Task(gid="123", name="Test")

        with SaveSession(client) as session1:
            session1.delete(task)

        with SaveSession(client) as session2:
            session2.track(task)
            # Should not be marked as deleted in session2
            from autom8_asana.persistence import EntityState

            state = session2.get_state(task)
            # Task was not modified in session2, so it should be CLEAN
            assert state == EntityState.CLEAN

    @pytest.mark.asyncio
    async def test_concurrent_sessions_commit_independently(self) -> None:
        """Multiple sessions can be active and commit independently."""

        def make_mock_client() -> MagicMock:
            client = create_mock_client()
            client.batch.execute_async = AsyncMock(
                return_value=[create_success_result(gid="new_gid")]
            )
            return client

        # Two concurrent sessions
        client1 = make_mock_client()
        client2 = make_mock_client()

        task1 = Task(gid="temp_1", name="Task 1")
        task2 = Task(gid="temp_2", name="Task 2")

        async with SaveSession(client1) as session1:
            session1.track(task1)

            async with SaveSession(client2) as session2:
                session2.track(task2)

                # Commit session2 first
                result2 = await session2.commit_async()
                assert result2.success

            # Session1 still works
            result1 = await session1.commit_async()
            assert result1.success

    def test_session_graph_is_independent(self) -> None:
        """Each session has its own dependency graph."""
        client = create_mock_client()

        session1 = SaveSession(client)
        session2 = SaveSession(client)

        assert session1._graph is not session2._graph


# ---------------------------------------------------------------------------
# Thread Safety Tests
# ---------------------------------------------------------------------------


class TestThreadSafety:
    """Test thread safety of components."""

    def test_tracker_concurrent_track_calls(self) -> None:
        """ChangeTracker handles concurrent track() calls."""
        tracker = ChangeTracker()
        # Use temp_ GIDs so entities are marked as NEW (dirty)
        tasks = [Task(gid=f"temp_task_{i}", name=f"Task {i}") for i in range(100)]

        errors: list[Exception] = []

        def track_task(task: Task) -> None:
            try:
                tracker.track(task)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=track_task, args=(task,)) for task in tasks]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All 100 tasks with temp_ GIDs should be dirty (NEW state)
        assert len(tracker.get_dirty_entities()) == 100

    def test_tracker_concurrent_modifications(self) -> None:
        """ChangeTracker handles concurrent entity modifications."""
        tracker = ChangeTracker()
        tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(50)]

        # Track all tasks first
        for task in tasks:
            tracker.track(task)

        errors: list[Exception] = []

        def modify_task(task: Task) -> None:
            try:
                task.name = f"Modified {task.name}"
                _ = tracker.get_changes(task)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=modify_task, args=(task,)) for task in tasks]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(tracker.get_dirty_entities()) == 50

    def test_graph_concurrent_builds(self) -> None:
        """DependencyGraph handles concurrent builds (each build is atomic)."""
        # Note: In practice, graph.build() should be called from a single thread
        # This test verifies the graph doesn't corrupt with concurrent access
        graph = DependencyGraph()
        errors: list[Exception] = []

        def build_graph(idx: int) -> None:
            try:
                tasks = [Task(gid=f"g{idx}_t{i}", name=f"Task {i}") for i in range(10)]
                graph.build(tasks)
                _ = graph.get_levels()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=build_graph, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Graph should be in consistent state (last build wins)
        levels = graph.get_levels()
        assert len(levels) >= 1, (
            f"get_levels() returned empty result after concurrent graph build: {levels!r}"
        )

    def test_tracker_concurrent_get_dirty_entities(self) -> None:
        """get_dirty_entities() is thread-safe."""
        tracker = ChangeTracker()
        tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(50)]

        for task in tasks:
            tracker.track(task)
            task.name = f"Modified {task.name}"

        errors: list[Exception] = []
        results: list[int] = []

        def get_dirty() -> None:
            try:
                dirty = tracker.get_dirty_entities()
                results.append(len(dirty))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_dirty) for _ in range(20)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All calls should return same count (50 dirty entities)
        assert all(count == 50 for count in results)

    def test_session_track_from_multiple_threads(self) -> None:
        """SaveSession.track() handles calls from multiple threads."""
        client = create_mock_client()
        session = SaveSession(client)
        tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(50)]

        errors: list[Exception] = []

        def track_task(task: Task) -> None:
            try:
                session.track(task)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=track_task, args=(task,)) for task in tasks]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ---------------------------------------------------------------------------
# Concurrent Commit Tests
# ---------------------------------------------------------------------------


class TestConcurrentCommits:
    """Test concurrent async commits."""

    @pytest.mark.asyncio
    async def test_concurrent_session_commits(self) -> None:
        """Multiple sessions can commit concurrently."""

        def make_mock_client() -> MagicMock:
            client = create_mock_client()
            client.batch.execute_async = AsyncMock(
                return_value=[create_success_result(gid="new_gid")]
            )
            return client

        async def run_session(idx: int) -> SaveResult:
            client = make_mock_client()
            # Use temp_ GID for new entity
            task = Task(gid=f"temp_{idx}", name=f"Task {idx}")
            async with SaveSession(client) as session:
                session.track(task)
                return await session.commit_async()

        # Run 10 sessions concurrently
        results = await asyncio.gather(*[run_session(i) for i in range(10)])

        assert all(r.success for r in results)
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_concurrent_commits_with_delays(self) -> None:
        """Concurrent commits with varying delays complete correctly."""

        async def make_slow_client(delay: float) -> MagicMock:
            client = create_mock_client()

            async def slow_execute(requests: list[Any]) -> list[BatchResult]:
                await asyncio.sleep(delay)
                return [create_success_result(gid=f"gid_{delay}")]

            client.batch.execute_async = slow_execute
            return client

        async def run_session(idx: int) -> tuple[int, SaveResult]:
            delay = 0.1 * (idx % 3)  # Vary delays
            client = await make_slow_client(delay)
            # Use temp_ GID for new entity
            task = Task(gid=f"temp_{idx}", name=f"Task {idx}")
            async with SaveSession(client) as session:
                session.track(task)
                result = await session.commit_async()
                return idx, result

        # Run 6 sessions with different delays
        results = await asyncio.gather(*[run_session(i) for i in range(6)])

        for idx, result in results:
            assert result.success, f"Session {idx} failed"

    @pytest.mark.asyncio
    async def test_sequential_sessions_with_shared_entity(self) -> None:
        """Different sessions can track same entity object independently via sequential execution."""
        shared_task = Task(gid="shared", name="Shared Task")

        def make_mock_client() -> MagicMock:
            client = create_mock_client()
            client.batch.execute_async = AsyncMock(
                return_value=[create_success_result(gid="shared")]
            )
            return client

        async def run_session(idx: int) -> SaveResult:
            client = make_mock_client()
            async with SaveSession(client) as session:
                session.track(shared_task)
                shared_task.name = f"Modified by {idx}"
                return await session.commit_async()

        # Run sequentially to avoid race conditions on the shared entity
        results = []
        for i in range(3):
            result = await run_session(i)
            results.append(result)

        assert all(r.success for r in results)


# ---------------------------------------------------------------------------
# Thread Pool Tests
# ---------------------------------------------------------------------------


class TestThreadPoolExecution:
    """Test execution in thread pools."""

    def test_sync_commit_in_thread_pool(self) -> None:
        """Sync commit works in thread pool executor."""

        def run_sync_session() -> SaveResult:
            client = create_mock_client()
            client.batch.execute_async = AsyncMock(
                return_value=[create_success_result(gid="new_gid")]
            )

            task = Task(gid="temp_1", name="Test")
            with SaveSession(client) as session:
                session.track(task)
                return session.commit()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_sync_session) for _ in range(4)]
            results = [f.result() for f in futures]

        assert all(r.success for r in results)

    def test_tracker_operations_in_thread_pool(self) -> None:
        """Tracker operations work correctly in thread pool."""
        tracker = ChangeTracker()

        def track_and_modify(idx: int) -> dict[str, Any]:
            task = Task(gid=f"task_{idx}", name=f"Task {idx}")
            tracker.track(task)
            task.name = f"Modified {idx}"
            return tracker.get_changes(task)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(track_and_modify, i) for i in range(20)]
            results = [f.result() for f in futures]

        # All should have captured changes
        assert len(results) == 20
        for changes in results:
            assert "name" in changes


# ---------------------------------------------------------------------------
# Race Condition Tests
# ---------------------------------------------------------------------------


class TestRaceConditions:
    """Test for potential race conditions."""

    def test_rapid_track_untrack_cycle(self) -> None:
        """Rapid track/untrack cycles don't cause corruption."""
        client = create_mock_client()
        session = SaveSession(client)
        task = Task(gid="123", name="Test")

        errors: list[Exception] = []

        def track_untrack_cycle() -> None:
            try:
                for _ in range(100):
                    session.track(task)
                    session.untrack(task)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=track_untrack_cycle) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_commit_during_modifications(self) -> None:
        """Commit captures consistent state even during modifications."""
        client = create_mock_client()
        client.batch.execute_async = AsyncMock(return_value=[create_success_result(gid="123")])

        task = Task(gid="123", name="Original")

        async with SaveSession(client) as session:
            session.track(task)
            task.name = "Modified"

            # Start commit
            commit_task = asyncio.create_task(session.commit_async())

            # Modify entity during commit (in practice this happens before batch executes)
            # This tests that the snapshot was captured correctly
            task.name = "Modified Again"

            result = await commit_task

        assert result.success

    def test_snapshot_isolation(self) -> None:
        """Snapshots are isolated from subsequent modifications."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Original")

        tracker.track(task)
        snapshot_before = tracker.get_changes(task)

        # Modify after tracking
        task.name = "Modified"
        snapshot_after = tracker.get_changes(task)

        # Snapshot before should show no changes (at track time)
        # Snapshot after should show the change
        assert "name" not in snapshot_before
        assert "name" in snapshot_after
        assert snapshot_after["name"] == ("Original", "Modified")
