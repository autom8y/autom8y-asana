"""INT-001: Nested SaveSession edge cases and behavior documentation.

This integration test suite documents the expected behavior of SaveSession
in edge cases, particularly around nested sessions, reentrant operations,
and session lifecycle management.

Per UX Remediation Initiative Session 5: Documents real-world scenarios
and edge cases that users may encounter.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models import Task
from autom8_asana.persistence.exceptions import SessionClosedError
from autom8_asana.persistence.models import OperationType
from autom8_asana.persistence.session import SaveSession


def create_mock_client() -> MagicMock:
    """Create a mock AsanaClient with all necessary methods."""
    mock_client = MagicMock()

    # Mock batch client
    mock_batch = MagicMock()
    mock_batch.execute_async = AsyncMock(return_value=[])
    mock_client.batch = mock_batch

    # Mock http client
    mock_http = AsyncMock()
    mock_http.request = AsyncMock(return_value={"data": {}})
    mock_client._http = mock_http

    # Mock logger
    mock_client._log = None

    return mock_client


class TestNestedSessionBehavior:
    """Documents behavior when SaveSession is used in nested contexts.

    Note: Direct nesting of SaveSession context managers is not recommended.
    This test documents the current behavior for reference.
    """

    @pytest.mark.asyncio
    async def test_sequential_sessions_work(self) -> None:
        """Sequential (non-overlapping) SaveSession instances work correctly.

        DOCUMENTED BEHAVIOR:
        - Multiple SaveSession instances can be created sequentially
        - Each session maintains independent state
        - Operations from one session don't affect another
        """
        mock_client = create_mock_client()

        # First session
        async with SaveSession(mock_client) as session1:
            task1 = Task(gid="1000000001", name="Task 1")
            session1.track(task1)
            task1.name = "Task 1 Updated"
            # Note: Not committing, just verifying state

        # Second session (after first is closed)
        async with SaveSession(mock_client) as session2:
            task2 = Task(gid="1000000002", name="Task 2")
            session2.track(task2)
            task2.name = "Task 2 Updated"
            result = await session2.commit_async()

        assert result is not None
        # Second session should complete without interference from first

    @pytest.mark.asyncio
    async def test_same_entity_in_different_sessions(self) -> None:
        """Same entity can be tracked in different SaveSession instances.

        DOCUMENTED BEHAVIOR:
        - Entity identity is based on Python object id(), not GID
        - Same GID can be used in multiple sessions (different Task instances)
        - Each session's changes are independent
        """
        mock_client = create_mock_client()

        # Create task and use it in first session
        task_v1 = Task(gid="2000000001", name="Original Task")
        async with SaveSession(mock_client) as session1:
            session1.track(task_v1)
            task_v1.name = "Updated in Session 1"
            changes1 = session1.preview()

        # Create different Task instance with same GID
        task_v2 = Task(gid="2000000001", name="Original Task")
        async with SaveSession(mock_client) as session2:
            session2.track(task_v2)
            task_v2.name = "Updated in Session 2"
            changes2 = session2.preview()

        # Both sessions should see their own independent changes
        # preview() returns (crud_ops, action_ops)
        crud_ops1, action_ops1 = changes1
        crud_ops2, action_ops2 = changes2

        # Each session should have exactly 1 CRUD operation (UPDATE for the modified task)
        assert len(crud_ops1) == 1
        assert crud_ops1[0].entity.gid == "2000000001"
        assert crud_ops1[0].operation == OperationType.UPDATE

        assert len(crud_ops2) == 1
        assert crud_ops2[0].entity.gid == "2000000001"
        assert crud_ops2[0].operation == OperationType.UPDATE

        # No action operations queued in either session
        assert action_ops1 == []
        assert action_ops2 == []

    @pytest.mark.asyncio
    async def test_session_isolation_prevents_cross_contamination(self) -> None:
        """SaveSession isolation ensures operations don't cross contaminate.

        DOCUMENTED BEHAVIOR:
        - Session A's tracked entities and operations don't affect Session B
        - Session state is completely isolated between instances
        - Modifying an entity after session close doesn't affect session's saved state
        """
        mock_client = create_mock_client()

        task = Task(gid="3000000001", name="Test Task")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Modified in Session"
            # Session sees the modification
            crud_ops1, _ = session.preview()
            assert len(crud_ops1) == 1
            assert crud_ops1[0].operation == OperationType.UPDATE
            assert crud_ops1[0].entity.name == "Modified in Session"

        # After session closes, future modifications don't retroactively affect
        # what the session would have committed
        task.name = "Modified After Session Close"
        # This doesn't change what session would have committed

        # Verify with another session
        async with SaveSession(mock_client) as session2:
            session2.track(task)
            # session2 sees current state (Modified After Session Close)
            # but that's independent of first session -- preview should be empty
            # because the snapshot was taken at track() with the current name
            crud_ops2, _ = session2.preview()
            # No dirty entities because snapshot matches current state
            assert len(crud_ops2) == 0


class TestSessionAndAsyncInteraction:
    """Documents interaction between SaveSession and async operations.

    Per ADR-0053: SaveSession supports composite async operations.
    """

    @pytest.mark.asyncio
    async def test_session_commit_during_async_operations(self) -> None:
        """SaveSession.commit_async() works correctly during async operations.

        DOCUMENTED BEHAVIOR:
        - commit_async() is a proper async operation
        - Can be awaited alongside other async operations
        - Plays nicely with asyncio.gather() and other async utilities
        """
        mock_client = create_mock_client()

        async def create_task_in_session():
            async with SaveSession(mock_client) as session:
                task = Task(gid="4000000001", name="Async Task")
                session.track(task)
                return await session.commit_async()

        # Can be used in asyncio context
        result = await create_task_in_session()
        assert result is not None

    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(self) -> None:
        """Multiple SaveSession instances can run concurrently.

        DOCUMENTED BEHAVIOR:
        - Different SaveSession instances can be active simultaneously
        - Each maintains independent state
        - Track operations from one session don't interfere with another
        """
        mock_client = create_mock_client()

        async def session_operation(session_id: int):
            async with SaveSession(mock_client) as session:
                task = Task(gid=f"500000000{session_id}", name=f"Task {session_id}")
                session.track(task)
                task.name = f"Updated Task {session_id}"
                return await session.commit_async()

        # Run 3 sessions concurrently
        results = await asyncio.gather(
            session_operation(1),
            session_operation(2),
            session_operation(3),
        )

        assert len(results) == 3
        # All should complete successfully


class TestSessionStateTransitions:
    """Documents SaveSession state machine behavior.

    Tests verify the expected state transitions through session lifecycle.
    """

    @pytest.mark.asyncio
    async def test_session_transitions_from_empty_to_tracked(self) -> None:
        """SaveSession transitions from empty to tracked state correctly.

        DOCUMENTED BEHAVIOR:
        - Session starts empty (no entities tracked)
        - track() transitions to tracked state
        - preview() reflects tracked entities
        """
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            # Initially empty -- preview returns empty lists
            crud_ops_empty, action_ops_empty = session.preview()
            assert crud_ops_empty == []
            assert action_ops_empty == []

            task = Task(gid="6000000001", name="New Task")
            session.track(task)

            # After tracking, entity is CLEAN (no modifications yet) so still empty
            crud_ops_clean, _ = session.preview()
            assert crud_ops_clean == []

            # After modification, entity appears in preview
            task.name = "Modified"
            crud_ops_dirty, action_ops_dirty = session.preview()
            assert len(crud_ops_dirty) == 1
            assert crud_ops_dirty[0].entity.gid == "6000000001"
            assert crud_ops_dirty[0].operation == OperationType.UPDATE
            assert action_ops_dirty == []

    @pytest.mark.asyncio
    async def test_session_retracking_same_entity_is_idempotent(self) -> None:
        """Re-tracking the same entity (by Python id) is idempotent.

        DOCUMENTED BEHAVIOR:
        - Calling track(entity) multiple times on same Python object is safe
        - Only first track() captures snapshot
        - Subsequent track() calls have no effect
        """
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            task = Task(gid="7000000001", name="Task")

            # Track same object multiple times
            session.track(task)
            session.track(task)  # Idempotent - should not re-snapshot
            session.track(task)  # Idempotent - should not re-snapshot

            # Modify after all track() calls
            task.name = "Modified"

            # Should only see one operation (not 3) proving idempotency
            crud_ops, _ = session.preview()
            assert len(crud_ops) == 1
            assert crud_ops[0].entity.gid == "7000000001"
            assert crud_ops[0].operation == OperationType.UPDATE


class TestSessionErrorRecovery:
    """Documents SaveSession behavior when errors occur.

    Documents expected behavior for error conditions.
    """

    @pytest.mark.asyncio
    async def test_session_context_manager_cleanup_on_error(self) -> None:
        """SaveSession context manager cleans up properly even on error.

        DOCUMENTED BEHAVIOR:
        - Exiting session context manager cleans up resources
        - Error during track() or modification leaves session in valid state
        - Can create new session after error without interference
        """
        mock_client = create_mock_client()

        try:
            async with SaveSession(mock_client) as session:
                task = Task(gid="8000000001", name="Task")
                session.track(task)
                # Simulate some error condition
                raise ValueError("Simulated error during session")
        except ValueError:
            pass  # Expected

        # Verify session is closed after error exit via __aexit__
        assert session.state == "closed"
        # Further operations on the closed session should raise SessionClosedError
        with pytest.raises(SessionClosedError):
            session.track(Task(gid="8000000003", name="Should fail"))

        # Should be able to create new session without issues
        async with SaveSession(mock_client) as session2:
            task2 = Task(gid="8000000002", name="New Task")
            session2.track(task2)
            result = await session2.commit_async()
            assert result is not None


class TestSessionMixedOperations:
    """Documents behavior of SaveSession with mixed operation types.

    Tests complex scenarios with multiple operation types.
    """

    @pytest.mark.asyncio
    async def test_session_tracks_creates_and_modifications(self) -> None:
        """SaveSession correctly distinguishes between creates and modifications.

        DOCUMENTED BEHAVIOR:
        - Entities with GID are modifications
        - Entities without GID (or with temp_* GID) are creates
        - SaveSession.preview() shows correct operation types
        """
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            # Modification (has real GID)
            existing_task = Task(gid="9000000001", name="Existing")
            session.track(existing_task)
            existing_task.name = "Modified"

            # Create (with temp GID for new entity)
            new_task = Task(gid="temp_1", name="New Task")
            session.track(new_task)

            crud_ops, action_ops = session.preview()
            # Should have 2 CRUD operations: one UPDATE and one CREATE
            assert len(crud_ops) == 2

            # Build a lookup by operation type for order-independent assertions
            ops_by_type = {op.operation: op for op in crud_ops}
            assert OperationType.UPDATE in ops_by_type
            assert OperationType.CREATE in ops_by_type
            assert ops_by_type[OperationType.UPDATE].entity.gid == "9000000001"
            assert ops_by_type[OperationType.CREATE].entity.gid == "temp_1"

            # No action operations queued
            assert action_ops == []


# Integration documentation notes:
#
# These tests document known behavior patterns that users should understand:
#
# 1. Session Isolation: Each SaveSession is completely independent.
#    Don't rely on cross-session state management.
#
# 2. Entity Identity: Tracked by Python object id(), not GID.
#    Same GID in different Task instances = different entities.
#
# 3. Snapshot Timing: Snapshot captured at track() time, not commit() time.
#    Modifications between track() and commit() are included.
#
# 4. State Transitions: Entity moves from CLEAN (tracked) or NEW (no GID)
#    to DIRTY once modified, then back to CLEAN after commit().
#
# 5. Error Handling: Partial failures shown in SaveSessionError.result.failed.
#    All failures collected and reported together.
#
# 6. Cascading Operations: Modifications trigger cascades (tags, followers).
#    All cascades included in same SaveSession commit.
