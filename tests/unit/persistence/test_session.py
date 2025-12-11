"""Tests for SaveSession.

Per TDD-0010: Verify Unit of Work pattern implementation.
Per TDD-0011: Verify action method support.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.models import Task, Tag, Project, Section
from autom8_asana.models.common import NameGid
from autom8_asana.models.user import User
from autom8_asana.persistence.exceptions import (
    SessionClosedError,
    UnsupportedOperationError,
    PositioningConflictError,
)
from autom8_asana.persistence.models import (
    EntityState,
    OperationType,
    PlannedOperation,
    SaveResult,
    ActionType,
    ActionOperation,
)
from autom8_asana.persistence.session import SaveSession, SessionState


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def create_mock_client() -> MagicMock:
    """Create a mock AsanaClient with mock batch client and http client."""
    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_batch.execute_async = AsyncMock(return_value=[])
    mock_client.batch = mock_batch
    mock_client._log = None

    # TDD-0011: Add mock HTTP client for action executor
    mock_http = AsyncMock()
    mock_http.request = AsyncMock(return_value={"data": {}})
    mock_client._http = mock_http

    return mock_client


def create_success_result(
    gid: str = "123",
    request_index: int = 0,
) -> BatchResult:
    """Create a successful BatchResult."""
    return BatchResult(
        status_code=200,
        body={"data": {"gid": gid, "name": "Test"}},
        request_index=request_index,
    )


def create_failure_result(
    message: str = "Error",
    status_code: int = 400,
    request_index: int = 0,
) -> BatchResult:
    """Create a failed BatchResult."""
    return BatchResult(
        status_code=status_code,
        body={"errors": [{"message": message}]},
        request_index=request_index,
    )


# ---------------------------------------------------------------------------
# Context Manager Tests
# ---------------------------------------------------------------------------


class TestContextManager:
    """Tests for context manager protocol."""

    @pytest.mark.asyncio
    async def test_context_manager_async(self) -> None:
        """SaveSession works as async context manager."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            assert session._state == SessionState.OPEN
            # Can track entities
            task = Task(gid="123", name="Test")
            session.track(task)

        # After exit, session is closed
        assert session._state == SessionState.CLOSED

    def test_context_manager_sync(self) -> None:
        """SaveSession works as sync context manager."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            assert session._state == SessionState.OPEN
            task = Task(gid="123", name="Test")
            session.track(task)

        assert session._state == SessionState.CLOSED

    @pytest.mark.asyncio
    async def test_async_context_closes_on_exception(self) -> None:
        """Async context manager closes session on exception."""
        mock_client = create_mock_client()

        with pytest.raises(ValueError):
            async with SaveSession(mock_client) as session:
                raise ValueError("Test error")

        assert session._state == SessionState.CLOSED

    def test_sync_context_closes_on_exception(self) -> None:
        """Sync context manager closes session on exception."""
        mock_client = create_mock_client()

        with pytest.raises(ValueError):
            with SaveSession(mock_client) as session:
                raise ValueError("Test error")

        assert session._state == SessionState.CLOSED


# ---------------------------------------------------------------------------
# Entity Registration Tests
# ---------------------------------------------------------------------------


class TestEntityRegistration:
    """Tests for entity registration operations."""

    def test_track_returns_entity(self) -> None:
        """track() returns the same entity for chaining."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")
        result = session.track(task)

        assert result is task

    def test_track_on_closed_session_raises(self) -> None:
        """track() raises SessionClosedError on closed session."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            pass  # Exit context

        with pytest.raises(SessionClosedError):
            session.track(Task(gid="123"))

    def test_untrack_removes_entity(self) -> None:
        """untrack() removes entity from tracking."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")
        session.track(task)
        session.untrack(task)

        with pytest.raises(ValueError):
            session.get_state(task)

    def test_untrack_on_closed_session_raises(self) -> None:
        """untrack() raises SessionClosedError on closed session."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            task = Task(gid="123")
            session.track(task)

        with pytest.raises(SessionClosedError):
            session.untrack(task)

    def test_delete_marks_for_deletion(self) -> None:
        """delete() marks entity for deletion."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")
        session.delete(task)

        state = session.get_state(task)
        assert state == EntityState.DELETED

    def test_delete_without_gid_raises(self) -> None:
        """delete() raises ValueError for entity without GID."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="temp_123", name="Test")

        with pytest.raises(ValueError, match="Cannot delete"):
            session.delete(task)

    def test_delete_on_closed_session_raises(self) -> None:
        """delete() raises SessionClosedError on closed session."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            pass

        with pytest.raises(SessionClosedError):
            session.delete(Task(gid="123"))


# ---------------------------------------------------------------------------
# Change Inspection Tests
# ---------------------------------------------------------------------------


class TestChangeInspection:
    """Tests for change inspection operations."""

    def test_get_changes_delegates_to_tracker(self) -> None:
        """get_changes() returns changes from tracker."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Original")
        session.track(task)
        task.name = "Modified"

        changes = session.get_changes(task)

        assert "name" in changes
        assert changes["name"] == ("Original", "Modified")

    def test_get_state_delegates_to_tracker(self) -> None:
        """get_state() returns state from tracker."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")
        session.track(task)

        state = session.get_state(task)
        assert state == EntityState.CLEAN

        task.name = "Modified"
        state = session.get_state(task)
        assert state == EntityState.MODIFIED

    def test_get_dependency_order_returns_levels(self) -> None:
        """get_dependency_order() returns entity levels."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        # Use valid numeric GIDs for proper dependency resolution
        parent = Task(gid="111111111", name="Parent")
        child = Task(gid="222222222", name="Child", parent=NameGid(gid="111111111"))

        session.track(parent)
        session.track(child)
        # Mark modified so they're dirty
        parent.name = "Parent Modified"
        child.name = "Child Modified"

        levels = session.get_dependency_order()

        assert len(levels) == 2
        # Parent at level 0
        assert parent in levels[0]
        # Child at level 1
        assert child in levels[1]


# ---------------------------------------------------------------------------
# Preview Tests
# ---------------------------------------------------------------------------


class TestPreview:
    """Tests for preview operation."""

    def test_preview_returns_planned_operations(self) -> None:
        """preview() returns tuple of (PlannedOperations, ActionOperations)."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Original")
        session.track(task)
        task.name = "Modified"

        crud_ops, action_ops = session.preview()

        assert len(crud_ops) == 1
        assert isinstance(crud_ops[0], PlannedOperation)
        assert crud_ops[0].entity is task
        assert crud_ops[0].operation == OperationType.UPDATE
        assert action_ops == []

    def test_preview_empty_session(self) -> None:
        """preview() with no dirty entities returns empty tuple."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        crud_ops, action_ops = session.preview()

        assert crud_ops == []
        assert action_ops == []

    def test_preview_does_not_modify_state(self) -> None:
        """preview() does not modify session state."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Original")
        session.track(task)
        task.name = "Modified"

        session.preview()

        # Entity should still be dirty
        assert session.get_state(task) == EntityState.MODIFIED


# ---------------------------------------------------------------------------
# Preview Action Tests (FR-PREV-001, FR-PREV-002, FR-PREV-003)
# ---------------------------------------------------------------------------


class TestPreviewActions:
    """Tests for preview() with action operations."""

    def test_preview_includes_pending_actions(self) -> None:
        """FR-PREV-001: preview() includes queued action operations."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")
        session.add_tag(task, "tag_gid")

        crud_ops, action_ops = session.preview()

        assert len(action_ops) == 1
        assert action_ops[0].action == ActionType.ADD_TAG
        assert action_ops[0].target_gid == "tag_gid"

    def test_preview_actions_after_crud(self) -> None:
        """FR-PREV-002: Actions returned separately from CRUD operations."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")
        session.track(task)
        task.name = "Modified"  # CRUD update
        session.add_tag(task, "tag_gid")  # Action

        crud_ops, action_ops = session.preview()

        # CRUD ops in first list, actions in second
        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.UPDATE
        assert len(action_ops) == 1
        assert action_ops[0].action == ActionType.ADD_TAG

    def test_preview_multiple_actions(self) -> None:
        """preview() includes all pending actions in order."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")
        session.add_tag(task, "tag_1")
        session.add_tag(task, "tag_2")
        session.move_to_section(task, "section_1")

        crud_ops, action_ops = session.preview()

        assert len(action_ops) == 3
        assert action_ops[0].action == ActionType.ADD_TAG
        assert action_ops[0].target_gid == "tag_1"
        assert action_ops[1].action == ActionType.ADD_TAG
        assert action_ops[1].target_gid == "tag_2"
        assert action_ops[2].action == ActionType.MOVE_TO_SECTION
        assert action_ops[2].target_gid == "section_1"

    def test_preview_detects_unsupported_tag_modifications(self) -> None:
        """FR-PREV-003: preview() raises UnsupportedOperationError for tags."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        # Create task with tags (needs to be tracked with tags in original state)
        task = Task(gid="123", name="Test", tags=[])
        session.track(task)

        # Simulate direct tag modification by modifying the snapshot
        # The tracker compares current state to snapshot
        # We need to modify the task's tags field directly
        task.tags = [Tag(gid="tag_1", name="Tag")]

        with pytest.raises(UnsupportedOperationError) as exc:
            session.preview()

        assert exc.value.field_name == "tags"
        assert "add_tag()" in exc.value.suggested_methods

    def test_preview_detects_unsupported_project_modifications(self) -> None:
        """FR-PREV-003: preview() raises UnsupportedOperationError for projects."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test", projects=[])
        session.track(task)
        task.projects = [Project(gid="proj_1", name="Project")]

        with pytest.raises(UnsupportedOperationError) as exc:
            session.preview()

        assert exc.value.field_name == "projects"
        assert "add_to_project()" in exc.value.suggested_methods

    def test_preview_detects_unsupported_membership_modifications(self) -> None:
        """FR-PREV-003: preview() raises UnsupportedOperationError for memberships."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test", memberships=[])
        session.track(task)
        task.memberships = [{"project": {"gid": "proj_1"}, "section": {"gid": "sect_1"}}]

        with pytest.raises(UnsupportedOperationError) as exc:
            session.preview()

        assert exc.value.field_name == "memberships"
        assert "add_to_project()" in exc.value.suggested_methods

    def test_preview_returns_copy_of_actions(self) -> None:
        """preview() returns a copy of actions, not the internal list."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")
        session.add_tag(task, "tag_1")

        _, action_ops_1 = session.preview()
        _, action_ops_2 = session.preview()

        assert action_ops_1 is not action_ops_2
        assert action_ops_1 == action_ops_2

    def test_preview_with_only_actions_no_crud(self) -> None:
        """preview() works with only actions and no CRUD operations."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")  # Not tracked
        session.add_tag(task, "tag_1")

        crud_ops, action_ops = session.preview()

        assert crud_ops == []
        assert len(action_ops) == 1

    def test_preview_validation_only_on_dirty_entities(self) -> None:
        """preview() validation only applies to dirty entities."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        # Only add actions, no CRUD operations (no dirty entities)
        task = Task(gid="123", name="Test")  # Not tracked
        session.add_tag(task, "tag_1")

        # Should not raise even though task has no modifications
        # because task is not tracked (no dirty entities)
        crud_ops, action_ops = session.preview()

        assert crud_ops == []
        assert len(action_ops) == 1


# ---------------------------------------------------------------------------
# Commit Tests
# ---------------------------------------------------------------------------


class TestCommit:
    """Tests for commit operations."""

    @pytest.mark.asyncio
    async def test_commit_async_executes_pipeline(self) -> None:
        """commit_async() executes pipeline and returns result."""
        mock_client = create_mock_client()
        success = create_success_result(gid="123")
        mock_client.batch.execute_async = AsyncMock(return_value=[success])

        session = SaveSession(mock_client)
        task = Task(gid="123", name="Original")
        session.track(task)
        task.name = "Modified"

        result = await session.commit_async()

        assert isinstance(result, SaveResult)
        assert len(result.succeeded) == 1
        assert result.success

    @pytest.mark.asyncio
    async def test_commit_async_marks_succeeded_clean(self) -> None:
        """commit_async() marks succeeded entities as clean."""
        mock_client = create_mock_client()
        success = create_success_result(gid="123")
        mock_client.batch.execute_async = AsyncMock(return_value=[success])

        session = SaveSession(mock_client)
        task = Task(gid="123", name="Original")
        session.track(task)
        task.name = "Modified"

        assert session.get_state(task) == EntityState.MODIFIED

        await session.commit_async()

        assert session.get_state(task) == EntityState.CLEAN

    @pytest.mark.asyncio
    async def test_commit_async_empty_session(self) -> None:
        """commit_async() with no dirty entities returns empty result."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        result = await session.commit_async()

        assert result.success
        assert result.succeeded == []
        assert result.failed == []

    @pytest.mark.asyncio
    async def test_commit_async_on_closed_raises(self) -> None:
        """commit_async() raises on closed session."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            pass

        with pytest.raises(SessionClosedError):
            await session.commit_async()

    def test_commit_sync_wrapper(self) -> None:
        """commit() is sync wrapper for commit_async()."""
        mock_client = create_mock_client()
        success = create_success_result(gid="123")
        mock_client.batch.execute_async = AsyncMock(return_value=[success])

        session = SaveSession(mock_client)
        task = Task(gid="123", name="Original")
        session.track(task)
        task.name = "Modified"

        result = session.commit()

        assert isinstance(result, SaveResult)
        assert result.success

    @pytest.mark.asyncio
    async def test_commit_multiple_times(self) -> None:
        """Multiple commits within same session work."""
        mock_client = create_mock_client()
        success = create_success_result(gid="123")
        mock_client.batch.execute_async = AsyncMock(return_value=[success])

        async with SaveSession(mock_client) as session:
            task = Task(gid="123", name="Original")
            session.track(task)

            # First commit
            task.name = "First Update"
            result1 = await session.commit_async()
            assert result1.success

            # Second commit (same entity, new changes)
            task.name = "Second Update"
            result2 = await session.commit_async()
            assert result2.success


# ---------------------------------------------------------------------------
# Event Hook Tests
# ---------------------------------------------------------------------------


class TestEventHooks:
    """Tests for event hook registration."""

    def test_on_pre_save_registers_hook(self) -> None:
        """on_pre_save() registers hook with EventSystem."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        called = []

        @session.on_pre_save
        def hook(entity: Task, op: OperationType) -> None:
            called.append((entity, op))

        assert len(session._events._pre_save_hooks) == 1

    def test_on_post_save_registers_hook(self) -> None:
        """on_post_save() registers hook with EventSystem."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        called = []

        @session.on_post_save
        def hook(entity: Task, op: OperationType, data: Any) -> None:
            called.append((entity, op, data))

        assert len(session._events._post_save_hooks) == 1

    def test_on_error_registers_hook(self) -> None:
        """on_error() registers hook with EventSystem."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        called = []

        @session.on_error
        def hook(entity: Task, op: OperationType, err: Exception) -> None:
            called.append((entity, op, err))

        assert len(session._events._error_hooks) == 1

    @pytest.mark.asyncio
    async def test_hooks_called_during_commit(self) -> None:
        """Hooks are called during commit execution."""
        mock_client = create_mock_client()
        success = create_success_result(gid="123")
        mock_client.batch.execute_async = AsyncMock(return_value=[success])

        session = SaveSession(mock_client)
        pre_save_calls: list[tuple[Task, OperationType]] = []
        post_save_calls: list[tuple[Task, OperationType, Any]] = []

        @session.on_pre_save
        def pre_hook(entity: Task, op: OperationType) -> None:
            pre_save_calls.append((entity, op))

        @session.on_post_save
        def post_hook(entity: Task, op: OperationType, data: Any) -> None:
            post_save_calls.append((entity, op, data))

        task = Task(gid="123", name="Test")
        session.track(task)
        task.name = "Modified"

        await session.commit_async()

        assert len(pre_save_calls) == 1
        assert len(post_save_calls) == 1


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases."""

    def test_track_same_entity_twice(self) -> None:
        """Tracking same entity twice is idempotent."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Original")
        session.track(task)
        task.name = "Modified"
        session.track(task)  # Second track

        # Changes should still be detected from original snapshot
        changes = session.get_changes(task)
        assert "name" in changes
        assert changes["name"] == ("Original", "Modified")

    @pytest.mark.asyncio
    async def test_commit_updates_gid_for_new_entities(self) -> None:
        """commit() updates GID for new entities after creation."""
        mock_client = create_mock_client()
        success = create_success_result(gid="real_gid_123")
        mock_client.batch.execute_async = AsyncMock(return_value=[success])

        session = SaveSession(mock_client)
        task = Task(gid="temp_123", name="New Task")
        session.track(task)

        await session.commit_async()

        assert task.gid == "real_gid_123"

    def test_session_with_logging(self) -> None:
        """Session with client logging works correctly."""
        mock_client = create_mock_client()
        mock_log = MagicMock()
        mock_client._log = mock_log

        session = SaveSession(mock_client)
        task = Task(gid="123", name="Test")
        session.track(task)

        # Verify logging was called
        mock_log.debug.assert_called()

    @pytest.mark.asyncio
    async def test_partial_failure_handling(self) -> None:
        """Session handles partial failures correctly."""
        mock_client = create_mock_client()
        # Both results - one success, one failure
        results = [
            create_success_result(gid="111", request_index=0),
            create_failure_result("Error", 400, request_index=1),
        ]
        mock_client.batch.execute_async = AsyncMock(return_value=results)

        session = SaveSession(mock_client)
        task1 = Task(gid="111", name="Task 1")
        task2 = Task(gid="222", name="Task 2")

        session.track(task1)
        session.track(task2)
        task1.name = "Modified 1"
        task2.name = "Modified 2"

        result = await session.commit_async()

        assert result.partial
        assert len(result.succeeded) == 1
        assert len(result.failed) == 1

        # Check states - one should be CLEAN (succeeded), one MODIFIED (failed)
        # Note: Order depends on graph internals, so check both possibilities
        states = [session.get_state(task1), session.get_state(task2)]
        assert EntityState.CLEAN in states, "One entity should be CLEAN after success"
        assert EntityState.MODIFIED in states, "One entity should remain MODIFIED after failure"


# ---------------------------------------------------------------------------
# TDD-0011: Action Method Tests
# ---------------------------------------------------------------------------


class TestActionMethods:
    """Tests for action methods (add_tag, remove_tag, etc.)."""

    def test_add_tag_with_object(self) -> None:
        """add_tag() registers action with tag object."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        tag = Tag(gid="tag_456", name="Important")

        result = session.add_tag(task, tag)

        assert result is session  # Fluent chaining
        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.ADD_TAG
        assert actions[0].task is task
        assert actions[0].target_gid == "tag_456"

    def test_add_tag_with_string(self) -> None:
        """add_tag() registers action with string GID."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.add_tag(task, "tag_456")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].target_gid == "tag_456"

    def test_remove_tag(self) -> None:
        """remove_tag() registers REMOVE_TAG action."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.remove_tag(task, "tag_456")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.REMOVE_TAG

    def test_add_to_project(self) -> None:
        """add_to_project() registers ADD_TO_PROJECT action."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        project = Project(gid="project_789", name="My Project")

        session.add_to_project(task, project)

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.ADD_TO_PROJECT
        assert actions[0].target_gid == "project_789"

    def test_remove_from_project(self) -> None:
        """remove_from_project() registers REMOVE_FROM_PROJECT action."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.remove_from_project(task, "project_789")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.REMOVE_FROM_PROJECT

    def test_add_dependency(self) -> None:
        """add_dependency() registers ADD_DEPENDENCY action."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        depends_on = Task(gid="task_456")

        session.add_dependency(task, depends_on)

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.ADD_DEPENDENCY
        assert actions[0].target_gid == "task_456"

    def test_remove_dependency(self) -> None:
        """remove_dependency() registers REMOVE_DEPENDENCY action."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.remove_dependency(task, "task_456")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.REMOVE_DEPENDENCY

    def test_move_to_section(self) -> None:
        """move_to_section() registers MOVE_TO_SECTION action."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        section = Section(gid="section_789", name="Done")

        session.move_to_section(task, section)

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.MOVE_TO_SECTION
        assert actions[0].target_gid == "section_789"

    def test_fluent_chaining(self) -> None:
        """Action methods support fluent chaining."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        # Chain multiple actions
        session.add_tag(task, "tag_1").add_tag(task, "tag_2").move_to_section(
            task, "section_1"
        )

        actions = session.get_pending_actions()
        assert len(actions) == 3

    def test_action_methods_require_open_session(self) -> None:
        """Action methods raise SessionClosedError when session closed."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            pass  # Session closed after exit

        task = Task(gid="task_123")

        with pytest.raises(SessionClosedError):
            session.add_tag(task, "tag_456")

    def test_get_pending_actions_returns_copy(self) -> None:
        """get_pending_actions() returns a copy, not the original."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        session.add_tag(task, "tag_456")

        actions1 = session.get_pending_actions()
        actions2 = session.get_pending_actions()

        assert actions1 is not actions2
        assert actions1 == actions2


class TestActionCommit:
    """Tests for commit with actions."""

    @pytest.mark.asyncio
    async def test_commit_actions_only(self) -> None:
        """commit_async() executes pending actions."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        session.add_tag(task, "tag_456")

        result = await session.commit_async()

        assert result.success
        # HTTP request should have been made for action
        mock_client._http.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit_clears_pending_actions(self) -> None:
        """commit_async() clears pending actions after commit."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        session.add_tag(task, "tag_456")

        await session.commit_async()

        assert session.get_pending_actions() == []

    @pytest.mark.asyncio
    async def test_commit_crud_and_actions(self) -> None:
        """commit_async() handles both CRUD and actions."""
        mock_client = create_mock_client()
        success = create_success_result(gid="123")
        mock_client.batch.execute_async = AsyncMock(return_value=[success])

        session = SaveSession(mock_client)

        # CRUD operation
        task = Task(gid="123", name="Original")
        session.track(task)
        task.name = "Modified"

        # Action operation
        session.add_tag(task, "tag_456")

        result = await session.commit_async()

        assert result.success
        # Batch should be called for CRUD
        mock_client.batch.execute_async.assert_called()
        # HTTP should be called for action
        mock_client._http.request.assert_called()

    @pytest.mark.asyncio
    async def test_commit_empty_with_actions(self) -> None:
        """commit_async() with actions but no CRUD entities."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")  # Not tracked
        session.add_tag(task, "tag_456")

        result = await session.commit_async()

        assert result.success
        # HTTP should be called for action
        mock_client._http.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_commits_with_actions(self) -> None:
        """Multiple commits with actions work independently."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        # First commit with actions
        session.add_tag(task, "tag_1")
        await session.commit_async()
        assert mock_client._http.request.call_count == 1

        # Second commit with new actions
        session.add_tag(task, "tag_2")
        await session.commit_async()
        assert mock_client._http.request.call_count == 2


# ---------------------------------------------------------------------------
# TDD-0012: Follower Method Tests
# ---------------------------------------------------------------------------


class TestFollowerMethods:
    """Tests for follower methods (add_follower, remove_follower, etc.)."""

    def test_add_follower_creates_action_operation(self) -> None:
        """add_follower() creates ActionOperation with ADD_FOLLOWER type."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        user = User(gid="user_456", name="Test User")

        result = session.add_follower(task, user)

        assert result is session  # Fluent chaining
        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.ADD_FOLLOWER
        assert actions[0].task is task
        assert actions[0].target_gid == "user_456"

    def test_add_follower_with_string_gid(self) -> None:
        """add_follower() accepts string GID."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.add_follower(task, "user_456")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].target_gid == "user_456"

    def test_add_follower_with_namegid(self) -> None:
        """add_follower() accepts NameGid reference."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        user_ref = NameGid(gid="user_456", name="Test User")

        session.add_follower(task, user_ref)

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].target_gid == "user_456"

    def test_remove_follower_creates_action_operation(self) -> None:
        """remove_follower() creates ActionOperation with REMOVE_FOLLOWER type."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        user = User(gid="user_456", name="Test User")

        result = session.remove_follower(task, user)

        assert result is session  # Fluent chaining
        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.REMOVE_FOLLOWER
        assert actions[0].target_gid == "user_456"

    def test_add_followers_creates_multiple_operations(self) -> None:
        """add_followers() creates multiple ActionOperations."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        user1 = User(gid="user_1", name="User 1")
        user2 = User(gid="user_2", name="User 2")

        result = session.add_followers(task, [user1, user2, "user_3"])

        assert result is session  # Fluent chaining
        actions = session.get_pending_actions()
        assert len(actions) == 3
        assert all(a.action == ActionType.ADD_FOLLOWER for a in actions)
        assert actions[0].target_gid == "user_1"
        assert actions[1].target_gid == "user_2"
        assert actions[2].target_gid == "user_3"

    def test_remove_followers_creates_multiple_operations(self) -> None:
        """remove_followers() creates multiple ActionOperations."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        user1 = User(gid="user_1", name="User 1")
        user2 = User(gid="user_2", name="User 2")

        result = session.remove_followers(task, [user1, user2])

        assert result is session  # Fluent chaining
        actions = session.get_pending_actions()
        assert len(actions) == 2
        assert all(a.action == ActionType.REMOVE_FOLLOWER for a in actions)

    def test_follower_methods_require_open_session(self) -> None:
        """Follower methods raise SessionClosedError when session closed."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            pass  # Session closed after exit

        task = Task(gid="task_123")

        with pytest.raises(SessionClosedError):
            session.add_follower(task, "user_456")


# ---------------------------------------------------------------------------
# TDD-0012: Positioning Tests
# ---------------------------------------------------------------------------


class TestPositioning:
    """Tests for positioning parameters in add_to_project and move_to_section."""

    def test_add_to_project_with_insert_before(self) -> None:
        """add_to_project() accepts insert_before parameter."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.add_to_project(task, "project_456", insert_before="other_task_gid")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.ADD_TO_PROJECT
        assert actions[0].extra_params == {"insert_before": "other_task_gid"}

    def test_add_to_project_with_insert_after(self) -> None:
        """add_to_project() accepts insert_after parameter."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.add_to_project(task, "project_456", insert_after="other_task_gid")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].extra_params == {"insert_after": "other_task_gid"}

    def test_add_to_project_with_both_raises_positioning_conflict_error(self) -> None:
        """add_to_project() raises PositioningConflictError when both params given."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        with pytest.raises(PositioningConflictError) as exc:
            session.add_to_project(
                task,
                "project_456",
                insert_before="task_a",
                insert_after="task_b",
            )

        assert exc.value.insert_before == "task_a"
        assert exc.value.insert_after == "task_b"

    def test_add_to_project_without_positioning(self) -> None:
        """add_to_project() works without positioning (backward compatible)."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.add_to_project(task, "project_456")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].extra_params == {}

    def test_move_to_section_with_insert_before(self) -> None:
        """move_to_section() accepts insert_before parameter."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.move_to_section(task, "section_456", insert_before="other_task_gid")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.MOVE_TO_SECTION
        assert actions[0].extra_params == {"insert_before": "other_task_gid"}

    def test_move_to_section_with_insert_after(self) -> None:
        """move_to_section() accepts insert_after parameter."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.move_to_section(task, "section_456", insert_after="other_task_gid")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].extra_params == {"insert_after": "other_task_gid"}

    def test_move_to_section_with_both_raises_positioning_conflict_error(self) -> None:
        """move_to_section() raises PositioningConflictError when both params given."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        with pytest.raises(PositioningConflictError) as exc:
            session.move_to_section(
                task,
                "section_456",
                insert_before="task_a",
                insert_after="task_b",
            )

        assert exc.value.insert_before == "task_a"
        assert exc.value.insert_after == "task_b"

    def test_move_to_section_without_positioning(self) -> None:
        """move_to_section() works without positioning (backward compatible)."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.move_to_section(task, "section_456")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].extra_params == {}


# ---------------------------------------------------------------------------
# TDD-0012 Phase 2: Dependent Method Tests
# ---------------------------------------------------------------------------


class TestDependentMethods:
    """Tests for dependent methods (add_dependent, remove_dependent)."""

    def test_add_dependent_creates_action_operation(self) -> None:
        """add_dependent() creates ActionOperation with ADD_DEPENDENT type."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        dependent = Task(gid="dependent_456")

        result = session.add_dependent(task, dependent)

        assert result is session  # Fluent chaining
        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.ADD_DEPENDENT
        assert actions[0].task is task
        assert actions[0].target_gid == "dependent_456"

    def test_remove_dependent_creates_action_operation(self) -> None:
        """remove_dependent() creates ActionOperation with REMOVE_DEPENDENT type."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        dependent = Task(gid="dependent_456")

        result = session.remove_dependent(task, dependent)

        assert result is session  # Fluent chaining
        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.REMOVE_DEPENDENT
        assert actions[0].target_gid == "dependent_456"

    def test_add_dependent_with_string_gid(self) -> None:
        """add_dependent() accepts string GID."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.add_dependent(task, "dependent_456")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].target_gid == "dependent_456"

    def test_dependent_methods_require_open_session(self) -> None:
        """Dependent methods raise SessionClosedError when session closed."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            pass  # Session closed after exit

        task = Task(gid="task_123")

        with pytest.raises(SessionClosedError):
            session.add_dependent(task, "dependent_456")


# ---------------------------------------------------------------------------
# TDD-0012 Phase 2: Like Method Tests
# ---------------------------------------------------------------------------


class TestLikeMethods:
    """Tests for like methods (add_like, remove_like)."""

    def test_add_like_creates_action_operation(self) -> None:
        """add_like() creates ActionOperation with ADD_LIKE type."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        result = session.add_like(task)

        assert result is session  # Fluent chaining
        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.ADD_LIKE
        assert actions[0].task is task

    def test_remove_like_creates_action_operation(self) -> None:
        """remove_like() creates ActionOperation with REMOVE_LIKE type."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        result = session.remove_like(task)

        assert result is session  # Fluent chaining
        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.REMOVE_LIKE

    def test_add_like_has_no_target_gid(self) -> None:
        """add_like() creates ActionOperation with target_gid=None (ADR-0045)."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.add_like(task)

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].target_gid is None

    def test_remove_like_has_no_target_gid(self) -> None:
        """remove_like() creates ActionOperation with target_gid=None (ADR-0045)."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.remove_like(task)

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].target_gid is None

    def test_like_methods_require_open_session(self) -> None:
        """Like methods raise SessionClosedError when session closed."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            pass  # Session closed after exit

        task = Task(gid="task_123")

        with pytest.raises(SessionClosedError):
            session.add_like(task)

        with pytest.raises(SessionClosedError):
            session.remove_like(task)


# ---------------------------------------------------------------------------
# TDD-0012 Phase 2: Comment Method Tests
# ---------------------------------------------------------------------------


class TestCommentMethods:
    """Tests for comment methods (add_comment)."""

    def test_add_comment_creates_action_operation(self) -> None:
        """add_comment() creates ActionOperation with ADD_COMMENT type."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        result = session.add_comment(task, "This is a comment")

        assert result is session  # Fluent chaining
        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.ADD_COMMENT
        assert actions[0].task is task

    def test_add_comment_with_html_text(self) -> None:
        """add_comment() accepts optional html_text parameter."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.add_comment(
            task,
            "Plain text",
            html_text="<body>Rich <strong>HTML</strong> text</body>",
        )

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].extra_params["text"] == "Plain text"
        assert actions[0].extra_params["html_text"] == "<body>Rich <strong>HTML</strong> text</body>"

    def test_add_comment_stores_text_in_extra_params(self) -> None:
        """add_comment() stores text in extra_params per ADR-0046."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.add_comment(task, "Test comment text")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].extra_params == {"text": "Test comment text"}
        assert actions[0].target_gid is None  # Comments don't need target_gid

    def test_add_comment_empty_raises_value_error(self) -> None:
        """add_comment() raises ValueError if both text and html_text are empty."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        with pytest.raises(ValueError, match="requires either text or html_text"):
            session.add_comment(task, "")

    def test_add_comment_requires_open_session(self) -> None:
        """add_comment() raises SessionClosedError when session closed."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            pass  # Session closed after exit

        task = Task(gid="task_123")

        with pytest.raises(SessionClosedError):
            session.add_comment(task, "Comment")

    def test_add_comment_with_only_html_text(self) -> None:
        """add_comment() works with only html_text (empty text allowed if html provided)."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        # Empty text but html_text provided should work
        session.add_comment(task, "", html_text="<body>HTML only</body>")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].extra_params["text"] == ""
        assert actions[0].extra_params["html_text"] == "<body>HTML only</body>"


# ---------------------------------------------------------------------------
# TDD-0013: Parent Method Tests (PRD-0008)
# ---------------------------------------------------------------------------


class TestParentMethods:
    """Tests for set_parent and reorder_subtask methods (PRD-0008)."""

    def test_set_parent_creates_action_operation(self) -> None:
        """Test set_parent creates correct ActionOperation."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        parent = Task(gid="parent_456")

        result = session.set_parent(task, parent)

        assert result is session  # Fluent chaining
        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.SET_PARENT
        assert actions[0].task is task
        assert actions[0].target_gid is None
        assert actions[0].extra_params["parent"] == "parent_456"

    def test_set_parent_with_none_promotes_to_top_level(self) -> None:
        """Test set_parent(task, None) promotes subtask to top-level."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.set_parent(task, None)

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].extra_params["parent"] is None

    def test_set_parent_with_string_gid(self) -> None:
        """Test set_parent accepts string GID for parent."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")

        session.set_parent(task, "parent_456")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].extra_params["parent"] == "parent_456"

    def test_set_parent_with_insert_before(self) -> None:
        """Test set_parent with insert_before positioning."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        parent = Task(gid="parent_456")
        sibling = Task(gid="sibling_789")

        session.set_parent(task, parent, insert_before=sibling)

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].extra_params["insert_before"] == "sibling_789"
        assert "insert_after" not in actions[0].extra_params

    def test_set_parent_with_insert_after(self) -> None:
        """Test set_parent with insert_after positioning."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        parent = Task(gid="parent_456")

        session.set_parent(task, parent, insert_after="sibling_abc")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].extra_params["insert_after"] == "sibling_abc"
        assert "insert_before" not in actions[0].extra_params

    def test_set_parent_with_both_positioning_raises(self) -> None:
        """Test set_parent raises PositioningConflictError when both specified."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        parent = Task(gid="parent_456")

        with pytest.raises(PositioningConflictError) as exc:
            session.set_parent(task, parent, insert_before="a", insert_after="b")

        assert exc.value.insert_before == "a"
        assert exc.value.insert_after == "b"

    def test_set_parent_requires_open_session(self) -> None:
        """Test set_parent raises SessionClosedError when session is closed."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            pass  # Session closed after exit

        task = Task(gid="task_123")

        with pytest.raises(SessionClosedError):
            session.set_parent(task, None)

    def test_set_parent_returns_self_for_chaining(self) -> None:
        """Test set_parent returns self for fluent chaining."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task1 = Task(gid="task_1")
        task2 = Task(gid="task_2")
        parent = Task(gid="parent")

        # Chain multiple set_parent calls
        session.set_parent(task1, parent).set_parent(task2, parent)

        actions = session.get_pending_actions()
        assert len(actions) == 2

    def test_reorder_subtask_calls_set_parent(self) -> None:
        """Test reorder_subtask delegates to set_parent with current parent."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        parent_ref = NameGid(gid="parent_456", name="Parent Task")
        task = Task(gid="task_123", parent=parent_ref)
        sibling = Task(gid="sibling_789")

        session.reorder_subtask(task, insert_after=sibling)

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].action == ActionType.SET_PARENT
        assert actions[0].extra_params["parent"] == "parent_456"
        assert actions[0].extra_params["insert_after"] == "sibling_789"

    def test_reorder_subtask_raises_for_task_without_parent(self) -> None:
        """Test reorder_subtask raises ValueError if task has no parent."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123", parent=None)

        with pytest.raises(ValueError, match="has no parent"):
            session.reorder_subtask(task, insert_after="sibling")

    def test_reorder_subtask_with_insert_before(self) -> None:
        """Test reorder_subtask with insert_before positioning."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        parent_ref = NameGid(gid="parent_456", name="Parent Task")
        task = Task(gid="task_123", parent=parent_ref)

        session.reorder_subtask(task, insert_before="first_sibling")

        actions = session.get_pending_actions()
        assert len(actions) == 1
        assert actions[0].extra_params["insert_before"] == "first_sibling"

    def test_reorder_subtask_raises_positioning_conflict(self) -> None:
        """Test reorder_subtask raises PositioningConflictError when both specified."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        parent_ref = NameGid(gid="parent_456", name="Parent Task")
        task = Task(gid="task_123", parent=parent_ref)

        with pytest.raises(PositioningConflictError):
            session.reorder_subtask(task, insert_before="a", insert_after="b")

    def test_reorder_subtask_requires_open_session(self) -> None:
        """Test reorder_subtask raises SessionClosedError when session is closed."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            pass  # Session closed after exit

        parent_ref = NameGid(gid="parent_456", name="Parent Task")
        task = Task(gid="task_123", parent=parent_ref)

        with pytest.raises(SessionClosedError):
            session.reorder_subtask(task, insert_after="sibling")

    def test_set_parent_with_object_positioning(self) -> None:
        """Test set_parent accepts Task objects for positioning."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="task_123")
        parent = Task(gid="parent_456")
        sibling_before = Task(gid="sibling_before")

        session.set_parent(task, parent, insert_before=sibling_before)

        actions = session.get_pending_actions()
        assert actions[0].extra_params["insert_before"] == "sibling_before"
