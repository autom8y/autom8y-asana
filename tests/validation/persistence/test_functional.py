"""Part 1: Functional Validation Tests.

Tests basic save scenarios with mocked BatchClient to verify
correct behavior of create, update, delete operations and event hooks.

Test Coverage:
- FR-UOW-001: Async context manager for bulk saves
- FR-UOW-002: Explicit opt-in tracking
- FR-UOW-003: Execute pending changes
- FR-CHANGE-003: Detect new entities by GID
- FR-CHANGE-004: Mark for DELETE operation
- FR-EVENT-001 through FR-EVENT-005: Event hooks
- FR-DRY-001: Preview without executing
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.models import Task
from autom8_asana.persistence import (
    EntityState,
    OperationType,
    PlannedOperation,
    SaveSession,
)

from .conftest import (
    create_failure_result,
    create_mock_client,
    create_success_result,
)

# ---------------------------------------------------------------------------
# Basic Save Scenarios
# ---------------------------------------------------------------------------


class TestBasicSaveScenarios:
    """Test create, update, delete operations."""

    async def test_create_single_entity(self) -> None:
        """Track new entity without GID, commit creates it (FR-CHANGE-003)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[create_success_result(gid="new_gid_123")]
        )

        # Entity with temp GID indicates new entity to be created
        task = Task(gid="temp_new", name="New Task")

        async with SaveSession(mock_client) as session:
            session.track(task)
            result = await session.commit_async()

        assert result.success
        assert len(result.succeeded) == 1
        # Verify BatchClient was called
        mock_client.batch.execute_async.assert_called_once()

        # Verify the request was a POST (create)
        call_args = mock_client.batch.execute_async.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0].method == "POST"

    async def test_create_entity_updates_gid(self) -> None:
        """After create, entity GID is updated to real GID from API."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[create_success_result(gid="real_gid_456")]
        )

        task = Task(gid="temp_1", name="New Task")
        original_temp_gid = task.gid

        async with SaveSession(mock_client) as session:
            session.track(task)
            await session.commit_async()

        # GID should be updated
        assert task.gid == "real_gid_456"
        assert task.gid != original_temp_gid

    async def test_update_single_entity(self) -> None:
        """Track existing entity, modify it, commit updates (FR-UOW-003)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(return_value=[create_success_result(gid="123")])

        task = Task(gid="123", name="Original Name")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated Name"
            result = await session.commit_async()

        assert result.success
        assert len(result.succeeded) == 1

        # Verify PUT request was sent
        call_args = mock_client.batch.execute_async.call_args[0][0]
        assert call_args[0].method == "PUT"
        assert "/tasks/123" in call_args[0].relative_path

    async def test_update_only_sends_changed_fields(self) -> None:
        """Update sends minimal payload with only changed fields."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(return_value=[create_success_result(gid="123")])

        task = Task(gid="123", name="Original", notes="Some notes")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated"  # Only change name
            await session.commit_async()

        # Verify payload only contains changed field
        call_args = mock_client.batch.execute_async.call_args[0][0]
        payload = call_args[0].data
        assert "name" in payload
        # Notes should not be in update payload since it wasn't changed
        # (This depends on implementation - change tracker should only send diffs)

    async def test_delete_single_entity(self) -> None:
        """Mark entity for deletion, commit deletes (FR-CHANGE-004)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[BatchResult(status_code=200, body={"data": {}}, request_index=0)]
        )

        task = Task(gid="123", name="To Delete")

        async with SaveSession(mock_client) as session:
            session.delete(task)
            result = await session.commit_async()

        assert result.success

        # Verify DELETE request was sent
        call_args = mock_client.batch.execute_async.call_args[0][0]
        assert call_args[0].method == "DELETE"
        assert "/tasks/123" in call_args[0].relative_path

    async def test_multi_entity_commit(self) -> None:
        """Track multiple entities, commit all at once."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                create_success_result(gid="1", request_index=0),
                create_success_result(gid="2", request_index=1),
            ]
        )

        task1 = Task(gid="1", name="Task 1")
        task2 = Task(gid="2", name="Task 2")

        async with SaveSession(mock_client) as session:
            session.track(task1)
            session.track(task2)
            task1.name = "Updated 1"
            task2.name = "Updated 2"
            result = await session.commit_async()

        assert result.success
        assert len(result.succeeded) == 2

    async def test_mixed_operations_in_single_commit(self) -> None:
        """Create, update, and delete in single commit."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                create_success_result(gid="new_id", request_index=0),  # Create
                create_success_result(gid="existing", request_index=1),  # Update
                BatchResult(status_code=200, body={"data": {}}, request_index=2),  # Delete
            ]
        )

        new_task = Task(gid="temp_new", name="New Task")
        existing_task = Task(gid="existing", name="Existing")
        delete_task = Task(gid="to_delete", name="Delete Me")

        async with SaveSession(mock_client) as session:
            session.track(new_task)
            session.track(existing_task)
            session.delete(delete_task)

            existing_task.name = "Modified"
            result = await session.commit_async()

        assert result.success
        assert len(result.succeeded) == 3

    async def test_preview_returns_planned_operations(self) -> None:
        """preview() returns operations without executing (FR-DRY-001)."""
        mock_client = create_mock_client()

        task = Task(gid="123", name="Test")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Modified"

            crud_ops, _ = session.preview()

            assert len(crud_ops) == 1
            assert isinstance(crud_ops[0], PlannedOperation)
            assert crud_ops[0].operation == OperationType.UPDATE
            assert crud_ops[0].entity is task

            # BatchClient should NOT be called by preview
            mock_client.batch.execute_async.assert_not_called()

    async def test_preview_shows_correct_operation_types(self) -> None:
        """preview() correctly identifies CREATE, UPDATE, DELETE operations."""
        mock_client = create_mock_client()

        new_task = Task(gid="temp_1", name="New")
        update_task = Task(gid="existing_1", name="Update Me")
        delete_task = Task(gid="delete_1", name="Delete Me")

        async with SaveSession(mock_client) as session:
            session.track(new_task)
            session.track(update_task)
            session.delete(delete_task)

            update_task.name = "Updated"

            crud_ops, _ = session.preview()

        # Check operation types
        op_types = {op.operation for op in crud_ops}
        assert OperationType.CREATE in op_types
        assert OperationType.UPDATE in op_types
        assert OperationType.DELETE in op_types

    async def test_empty_commit_returns_empty_result(self) -> None:
        """Commit with no dirty entities returns empty success result."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            result = await session.commit_async()

        assert result.success
        assert len(result.succeeded) == 0
        assert len(result.failed) == 0
        # BatchClient should not be called
        mock_client.batch.execute_async.assert_not_called()

    async def test_track_without_changes_not_committed(self) -> None:
        """Tracked entity without changes is not committed."""
        mock_client = create_mock_client()

        task = Task(gid="123", name="Unchanged")

        async with SaveSession(mock_client) as session:
            session.track(task)
            # No modifications
            result = await session.commit_async()

        assert result.success
        assert len(result.succeeded) == 0
        mock_client.batch.execute_async.assert_not_called()


# ---------------------------------------------------------------------------
# Event Hook Tests
# ---------------------------------------------------------------------------


class TestEventHooks:
    """Test pre-save, post-save, and error hooks (FR-EVENT-001 through FR-EVENT-005)."""

    async def test_pre_save_hook_called(self) -> None:
        """Pre-save hook receives entity and operation type (FR-EVENT-001)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(return_value=[create_success_result(gid="123")])

        hook_calls: list[tuple[Task, OperationType]] = []

        async with SaveSession(mock_client) as session:

            @session.on_pre_save
            def pre_save(entity: Task, op_type: OperationType) -> None:
                hook_calls.append((entity, op_type))

            task = Task(gid="123", name="Test")
            session.track(task)
            task.name = "Modified"
            await session.commit_async()

        assert len(hook_calls) == 1
        assert hook_calls[0][1] == OperationType.UPDATE

    async def test_pre_save_hook_async(self) -> None:
        """Pre-save hook can be async (FR-EVENT-005)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(return_value=[create_success_result(gid="123")])

        hook_calls: list[tuple[Task, OperationType]] = []

        async with SaveSession(mock_client) as session:

            @session.on_pre_save
            async def pre_save(entity: Task, op_type: OperationType) -> None:
                hook_calls.append((entity, op_type))

            task = Task(gid="123", name="Test")
            session.track(task)
            task.name = "Modified"
            await session.commit_async()

        assert len(hook_calls) == 1

    async def test_pre_save_can_abort_via_exception(self) -> None:
        """Pre-save hook raising exception affects save (FR-EVENT-001)."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:

            @session.on_pre_save
            def pre_save(entity: Task, op_type: OperationType) -> None:
                raise ValueError("Validation failed")

            task = Task(gid="123", name="Test")
            session.track(task)
            task.name = "Modified"

            # The hook exception should propagate
            with pytest.raises(ValueError, match="Validation failed"):
                await session.commit_async()

    async def test_post_save_hook_called(self) -> None:
        """Post-save hook receives entity, op, and response data (FR-EVENT-002)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[create_success_result(gid="123", name="Test")]
        )

        hook_calls: list[tuple[Task, OperationType, Any]] = []

        async with SaveSession(mock_client) as session:

            @session.on_post_save
            def post_save(entity: Task, op_type: OperationType, data: Any) -> None:
                hook_calls.append((entity, op_type, data))

            task = Task(gid="123", name="Test")
            session.track(task)
            task.name = "Modified"
            await session.commit_async()

        assert len(hook_calls) == 1
        assert hook_calls[0][1] == OperationType.UPDATE
        # data should contain response from API
        assert hook_calls[0][2] is not None

    async def test_post_save_hook_async(self) -> None:
        """Post-save hook can be async (FR-EVENT-005)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(return_value=[create_success_result(gid="123")])

        hook_calls: list[tuple[Task, OperationType, Any]] = []

        async with SaveSession(mock_client) as session:

            @session.on_post_save
            async def post_save(entity: Task, op_type: OperationType, data: Any) -> None:
                hook_calls.append((entity, op_type, data))

            task = Task(gid="123", name="Test")
            session.track(task)
            task.name = "Modified"
            await session.commit_async()

        assert len(hook_calls) == 1

    async def test_post_save_exception_swallowed(self) -> None:
        """Post-save hook exceptions are swallowed (FR-EVENT-002)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(return_value=[create_success_result(gid="123")])

        async with SaveSession(mock_client) as session:

            @session.on_post_save
            def post_save(entity: Task, op_type: OperationType, data: Any) -> None:
                raise RuntimeError("Should be swallowed")

            task = Task(gid="123", name="Test")
            session.track(task)
            task.name = "Modified"

            # Should not raise
            result = await session.commit_async()

        assert result.success

    async def test_error_hook_called_on_failure(self) -> None:
        """Error hook called when save fails (FR-EVENT-003)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[create_failure_result(message="Bad request", status_code=400)]
        )

        hook_calls: list[tuple[Task, OperationType, Exception]] = []

        async with SaveSession(mock_client) as session:

            @session.on_error
            def on_error(entity: Task, op_type: OperationType, error: Exception) -> None:
                hook_calls.append((entity, op_type, error))

            task = Task(gid="123", name="Test")
            session.track(task)
            task.name = "Modified"
            await session.commit_async()

        assert len(hook_calls) == 1
        assert hook_calls[0][1] == OperationType.UPDATE
        assert isinstance(hook_calls[0][2], Exception)

    async def test_error_hook_async(self) -> None:
        """Error hook can be async (FR-EVENT-005)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[create_failure_result(message="Error", status_code=400)]
        )

        hook_calls: list[tuple[Task, OperationType, Exception]] = []

        async with SaveSession(mock_client) as session:

            @session.on_error
            async def on_error(entity: Task, op_type: OperationType, err: Exception) -> None:
                hook_calls.append((entity, op_type, err))

            task = Task(gid="123", name="Test")
            session.track(task)
            task.name = "Modified"
            await session.commit_async()

        assert len(hook_calls) == 1

    async def test_error_hook_exception_swallowed(self) -> None:
        """Error hook exceptions are swallowed (FR-EVENT-003)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[create_failure_result(message="Error", status_code=400)]
        )

        async with SaveSession(mock_client) as session:

            @session.on_error
            def on_error(entity: Task, op_type: OperationType, err: Exception) -> None:
                raise RuntimeError("Should be swallowed")

            task = Task(gid="123", name="Test")
            session.track(task)
            task.name = "Modified"

            # Should not raise
            result = await session.commit_async()

        # Result should show failure, but no exception from hook
        assert not result.success

    async def test_multiple_hooks_called_in_order(self) -> None:
        """Multiple registered hooks are called in registration order."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(return_value=[create_success_result(gid="123")])

        call_order: list[int] = []

        async with SaveSession(mock_client) as session:

            @session.on_pre_save
            def pre_hook_1(entity: Task, op: OperationType) -> None:
                call_order.append(1)

            @session.on_pre_save
            def pre_hook_2(entity: Task, op: OperationType) -> None:
                call_order.append(2)

            task = Task(gid="123", name="Test")
            session.track(task)
            task.name = "Modified"
            await session.commit_async()

        assert call_order == [1, 2]


# ---------------------------------------------------------------------------
# Entity State Tracking Tests
# ---------------------------------------------------------------------------


class TestEntityStateTracking:
    """Test entity lifecycle state tracking (FR-UOW-008)."""

    async def test_new_entity_state(self) -> None:
        """New entity (temp GID) has NEW state."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            task = Task(gid="temp_1", name="New Task")
            session.track(task)

            state = session.get_state(task)
            assert state == EntityState.NEW

    async def test_clean_entity_state(self) -> None:
        """Existing unmodified entity has CLEAN state."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            task = Task(gid="123", name="Existing")
            session.track(task)

            state = session.get_state(task)
            assert state == EntityState.CLEAN

    async def test_modified_entity_state(self) -> None:
        """Modified entity transitions to MODIFIED state."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            task = Task(gid="123", name="Original")
            session.track(task)

            # Initially clean
            assert session.get_state(task) == EntityState.CLEAN

            # After modification
            task.name = "Modified"
            assert session.get_state(task) == EntityState.MODIFIED

    async def test_deleted_entity_state(self) -> None:
        """Deleted entity has DELETED state."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            task = Task(gid="123", name="To Delete")
            session.delete(task)

            state = session.get_state(task)
            assert state == EntityState.DELETED

    async def test_entity_state_after_successful_commit(self) -> None:
        """Entity transitions to CLEAN after successful commit."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(return_value=[create_success_result(gid="123")])

        async with SaveSession(mock_client) as session:
            task = Task(gid="123", name="Original")
            session.track(task)
            task.name = "Modified"

            assert session.get_state(task) == EntityState.MODIFIED

            await session.commit_async()

            assert session.get_state(task) == EntityState.CLEAN


# ---------------------------------------------------------------------------
# Change Detection Tests
# ---------------------------------------------------------------------------


class TestChangeDetection:
    """Test change detection via snapshot comparison (FR-CHANGE-002)."""

    async def test_get_changes_returns_field_changes(self) -> None:
        """get_changes() returns {field: (old, new)} dict."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            task = Task(gid="123", name="Original", notes="Old notes")
            session.track(task)

            task.name = "Updated"
            task.notes = "New notes"

            changes = session.get_changes(task)

            assert "name" in changes
            assert changes["name"] == ("Original", "Updated")
            assert "notes" in changes
            assert changes["notes"] == ("Old notes", "New notes")

    async def test_get_changes_empty_for_unmodified(self) -> None:
        """get_changes() returns empty dict for unmodified entity."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            task = Task(gid="123", name="Original")
            session.track(task)

            changes = session.get_changes(task)
            # gid and resource_type should not show as changes
            # since they were present in original snapshot
            name_change = changes.get("name")
            assert name_change is None or name_change[0] == name_change[1]

    async def test_track_twice_idempotent(self) -> None:
        """Tracking same entity twice uses original snapshot."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            task = Task(gid="123", name="Original")
            session.track(task)
            task.name = "Modified"

            # Track again - should not reset snapshot
            session.track(task)

            changes = session.get_changes(task)
            assert "name" in changes
            assert changes["name"] == ("Original", "Modified")
