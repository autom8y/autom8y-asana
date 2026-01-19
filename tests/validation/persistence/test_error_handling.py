"""Part 3: Error Handling Validation Tests.

Tests error handling including partial failures, cascading failures,
and exception types.

Test Coverage:
- FR-ERROR-001: Commit successful, report failures
- FR-ERROR-002: SaveResult with succeeded/failed lists
- FR-ERROR-003: Attribute errors to specific entities
- FR-ERROR-004: PartialSaveError contains SaveResult
- FR-ERROR-006: DependencyResolutionError for cascading failures
- FR-ERROR-010: raise_on_failure() method
- ADR-0040: Partial failure handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.models import Task
from autom8_asana.models.common import NameGid
from autom8_asana.persistence import (
    EntityState,
    OperationType,
    SaveResult,
    SaveSession,
)
from autom8_asana.persistence.exceptions import (
    CyclicDependencyError,
    DependencyResolutionError,
    PartialSaveError,
    SaveOrchestrationError,
    SessionClosedError,
)
from autom8_asana.persistence.models import SaveError

from .conftest import (
    create_failure_result,
    create_mock_client,
    create_success_result,
)

# ---------------------------------------------------------------------------
# Partial Failure Tests
# ---------------------------------------------------------------------------


class TestPartialFailure:
    """Test partial failure handling (FR-ERROR-001, FR-ERROR-002)."""

    @pytest.mark.asyncio
    async def test_some_succeed_some_fail(self) -> None:
        """SaveResult contains both succeeded and failed (FR-ERROR-002)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                create_success_result(gid="1", request_index=0),
                create_failure_result(
                    message="Error", status_code=400, request_index=1
                ),
            ]
        )

        task1 = Task(gid="1", name="Task 1")
        task2 = Task(gid="2", name="Task 2")

        async with SaveSession(mock_client) as session:
            session.track(task1)
            session.track(task2)
            task1.name = "Modified 1"
            task2.name = "Modified 2"
            result = await session.commit_async()

        assert result.partial
        assert len(result.succeeded) == 1
        assert len(result.failed) == 1

    @pytest.mark.asyncio
    async def test_all_fail(self) -> None:
        """All operations failing returns failed result."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                create_failure_result(
                    message="Error 1", status_code=400, request_index=0
                ),
                create_failure_result(
                    message="Error 2", status_code=500, request_index=1
                ),
            ]
        )

        task1 = Task(gid="1", name="Task 1")
        task2 = Task(gid="2", name="Task 2")

        async with SaveSession(mock_client) as session:
            session.track(task1)
            session.track(task2)
            task1.name = "Modified 1"
            task2.name = "Modified 2"
            result = await session.commit_async()

        assert not result.success
        assert not result.partial
        assert len(result.succeeded) == 0
        assert len(result.failed) == 2

    @pytest.mark.asyncio
    async def test_save_error_contains_entity_info(self) -> None:
        """SaveError contains entity, operation, error, and payload (FR-ERROR-003)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                create_failure_result(message="API Error", status_code=400),
            ]
        )

        task = Task(gid="123", name="Test")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Modified"
            result = await session.commit_async()

        assert len(result.failed) == 1
        error = result.failed[0]

        assert isinstance(error, SaveError)
        assert error.entity is task
        assert error.operation == OperationType.UPDATE
        assert error.error is not None
        assert isinstance(error.payload, dict)

    @pytest.mark.asyncio
    async def test_cascading_dependency_failure(self) -> None:
        """Child fails with DependencyResolutionError when parent fails (FR-ERROR-006)."""
        mock_client = create_mock_client()
        # Parent fails
        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                create_failure_result(message="Parent failed", status_code=400),
            ]
        )

        parent = Task(gid="parent", name="Parent")
        child = Task(gid="child", name="Child", parent=NameGid(gid="parent"))

        async with SaveSession(mock_client) as session:
            session.track(parent)
            session.track(child)
            parent.name = "Modified Parent"
            child.name = "Modified Child"
            result = await session.commit_async()

        # Both should fail - parent directly, child cascading
        assert len(result.failed) == 2

        # Find the child's error
        child_error = None
        for err in result.failed:
            if err.entity is child:
                child_error = err
                break

        assert child_error is not None
        assert isinstance(child_error.error, DependencyResolutionError)

    @pytest.mark.asyncio
    async def test_partial_success_commits_succeeded_entities(self) -> None:
        """Successful entities are committed even when others fail (FR-ERROR-001)."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                create_success_result(gid="1", request_index=0),
                create_failure_result(
                    message="Error", status_code=400, request_index=1
                ),
            ]
        )

        task1 = Task(gid="1", name="Task 1")
        task2 = Task(gid="2", name="Task 2")

        async with SaveSession(mock_client) as session:
            session.track(task1)
            session.track(task2)
            task1.name = "Modified 1"
            task2.name = "Modified 2"
            result = await session.commit_async()

            # Successful entity should be marked clean
            states = [session.get_state(task1), session.get_state(task2)]
            # One should be CLEAN (succeeded), one should be MODIFIED (failed)
            assert EntityState.CLEAN in states

    @pytest.mark.asyncio
    async def test_multi_level_cascading_failure(self) -> None:
        """Cascading failure propagates through multiple levels."""
        mock_client = create_mock_client()
        # Root fails
        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                create_failure_result(message="Root failed", status_code=400),
            ]
        )

        root = Task(gid="root", name="Root")
        child = Task(gid="child", name="Child", parent=NameGid(gid="root"))
        grandchild = Task(gid="gc", name="Grandchild", parent=NameGid(gid="child"))

        async with SaveSession(mock_client) as session:
            session.track(root)
            session.track(child)
            session.track(grandchild)
            root.name = "Modified Root"
            child.name = "Modified Child"
            grandchild.name = "Modified GC"
            result = await session.commit_async()

        # All three should fail
        assert len(result.failed) == 3


# ---------------------------------------------------------------------------
# Exception Types Tests
# ---------------------------------------------------------------------------


class TestExceptionTypes:
    """Test exception types and hierarchy."""

    def test_session_closed_error(self) -> None:
        """Operations after context exit raise SessionClosedError."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            task = Task(gid="123", name="Test")
            session.track(task)

        # Session is now closed
        with pytest.raises(SessionClosedError):
            session.track(Task(gid="456", name="Another"))

    def test_session_closed_error_on_delete(self) -> None:
        """delete() on closed session raises SessionClosedError."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            pass

        with pytest.raises(SessionClosedError):
            session.delete(Task(gid="123", name="Test"))

    def test_session_closed_error_on_untrack(self) -> None:
        """untrack() on closed session raises SessionClosedError."""
        mock_client = create_mock_client()
        task = Task(gid="123", name="Test")

        with SaveSession(mock_client) as session:
            session.track(task)

        with pytest.raises(SessionClosedError):
            session.untrack(task)

    @pytest.mark.asyncio
    async def test_session_closed_error_on_commit(self) -> None:
        """commit_async() on closed session raises SessionClosedError."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            pass

        with pytest.raises(SessionClosedError):
            await session.commit_async()

    def test_partial_save_error_raised(self) -> None:
        """SaveResult.raise_on_failure() raises PartialSaveError (FR-ERROR-010)."""
        task = Task(gid="123", name="Test")
        result = SaveResult(
            succeeded=[],
            failed=[
                SaveError(
                    entity=task,
                    operation=OperationType.UPDATE,
                    error=Exception("API Error"),
                    payload={"name": "Test"},
                )
            ],
        )

        with pytest.raises(PartialSaveError) as exc_info:
            result.raise_on_failure()

        assert exc_info.value.result is result

    def test_partial_save_error_not_raised_on_success(self) -> None:
        """raise_on_failure() does not raise when all succeed."""
        task = Task(gid="123", name="Test")
        result = SaveResult(
            succeeded=[task],
            failed=[],
        )

        # Should not raise
        result.raise_on_failure()

    def test_partial_save_error_contains_counts(self) -> None:
        """PartialSaveError message contains failure counts."""
        tasks = [Task(gid=f"{i}", name=f"Task {i}") for i in range(3)]
        result = SaveResult(
            succeeded=[tasks[0]],
            failed=[
                SaveError(
                    entity=tasks[1],
                    operation=OperationType.UPDATE,
                    error=Exception("Error 1"),
                    payload={},
                ),
                SaveError(
                    entity=tasks[2],
                    operation=OperationType.UPDATE,
                    error=Exception("Error 2"),
                    payload={},
                ),
            ],
        )

        with pytest.raises(PartialSaveError) as exc_info:
            result.raise_on_failure()

        assert "2/3" in str(exc_info.value)

    def test_cyclic_dependency_error_has_cycle_list(self) -> None:
        """CyclicDependencyError contains list of cycle participants."""
        task_a = Task(gid="a", name="A")
        task_b = Task(gid="b", name="B")

        error = CyclicDependencyError([task_a, task_b])

        assert len(error.cycle) == 2
        assert task_a in error.cycle
        assert task_b in error.cycle
        assert "Cyclic dependency detected" in str(error)

    def test_dependency_resolution_error_has_context(self) -> None:
        """DependencyResolutionError contains entity and dependency info."""
        entity = Task(gid="child", name="Child")
        dependency = Task(gid="parent", name="Parent")
        cause = Exception("Parent failed")

        error = DependencyResolutionError(entity, dependency, cause)

        assert error.entity is entity
        assert error.dependency is dependency
        assert error.__cause__ is cause
        assert "child" in str(error)
        assert "parent" in str(error)

    def test_exception_hierarchy(self) -> None:
        """All save exceptions inherit from SaveOrchestrationError."""
        assert issubclass(SessionClosedError, SaveOrchestrationError)
        assert issubclass(CyclicDependencyError, SaveOrchestrationError)
        assert issubclass(DependencyResolutionError, SaveOrchestrationError)
        assert issubclass(PartialSaveError, SaveOrchestrationError)


# ---------------------------------------------------------------------------
# SaveResult Property Tests
# ---------------------------------------------------------------------------


class TestSaveResultProperties:
    """Test SaveResult properties and methods."""

    def test_success_property(self) -> None:
        """success property is True when no failures."""
        task = Task(gid="123", name="Test")

        # Empty result is success
        assert SaveResult().success

        # Succeeded only is success
        assert SaveResult(succeeded=[task], failed=[]).success

        # Failed only is not success
        error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=Exception("Error"),
            payload={},
        )
        assert not SaveResult(succeeded=[], failed=[error]).success

    def test_partial_property(self) -> None:
        """partial property is True when both succeeded and failed."""
        task1 = Task(gid="1", name="Task 1")
        task2 = Task(gid="2", name="Task 2")
        error = SaveError(
            entity=task2,
            operation=OperationType.UPDATE,
            error=Exception("Error"),
            payload={},
        )

        # Not partial if all succeeded
        assert not SaveResult(succeeded=[task1], failed=[]).partial

        # Not partial if all failed
        assert not SaveResult(succeeded=[], failed=[error]).partial

        # Partial if both
        assert SaveResult(succeeded=[task1], failed=[error]).partial

    def test_total_count_property(self) -> None:
        """total_count returns sum of succeeded and failed."""
        task1 = Task(gid="1", name="Task 1")
        task2 = Task(gid="2", name="Task 2")
        error = SaveError(
            entity=task2,
            operation=OperationType.UPDATE,
            error=Exception("Error"),
            payload={},
        )

        assert SaveResult().total_count == 0
        assert SaveResult(succeeded=[task1]).total_count == 1
        assert SaveResult(failed=[error]).total_count == 1
        assert SaveResult(succeeded=[task1], failed=[error]).total_count == 2


# ---------------------------------------------------------------------------
# Edge Cases and Boundary Conditions
# ---------------------------------------------------------------------------


class TestErrorEdgeCases:
    """Test error handling edge cases."""

    @pytest.mark.asyncio
    async def test_delete_without_gid_raises_value_error(self) -> None:
        """delete() on entity without GID raises ValueError."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            task = Task(gid="temp_123", name="Temp Task")

            with pytest.raises(ValueError, match="Cannot delete"):
                session.delete(task)

    @pytest.mark.asyncio
    async def test_delete_empty_gid_raises_value_error(self) -> None:
        """delete() on entity with empty string GID raises ValueError.

        Note: Task model requires gid, so we test with empty string instead of None.
        """
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            # Empty string GID should still fail
            task = Task(gid="", name="Empty GID Task")

            # Empty string gid should fail (same as no gid)
            with pytest.raises(ValueError, match="Cannot delete"):
                session.delete(task)

    def test_get_state_untracked_raises_value_error(self) -> None:
        """get_state() on untracked entity raises ValueError."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Not tracked")

        with pytest.raises(ValueError, match="not tracked"):
            session.get_state(task)

    @pytest.mark.asyncio
    async def test_batch_result_with_empty_body(self) -> None:
        """Handle batch result with empty body gracefully."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[BatchResult(status_code=200, body=None, request_index=0)]
        )

        task = Task(gid="123", name="Test")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Modified"
            result = await session.commit_async()

        # Should handle gracefully
        assert result.success

    @pytest.mark.asyncio
    async def test_batch_result_with_missing_data_field(self) -> None:
        """Handle batch result without data field."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                BatchResult(status_code=200, body={"other": "field"}, request_index=0)
            ]
        )

        task = Task(gid="123", name="Test")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Modified"
            result = await session.commit_async()

        # Should handle gracefully
        assert result.success

    @pytest.mark.asyncio
    async def test_5xx_error_code_handling(self) -> None:
        """Server errors (5xx) are properly captured."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                create_failure_result(message="Internal Server Error", status_code=500),
            ]
        )

        task = Task(gid="123", name="Test")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Modified"
            result = await session.commit_async()

        assert not result.success
        assert len(result.failed) == 1

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self) -> None:
        """Rate limit errors (429) are captured."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                create_failure_result(message="Rate limited", status_code=429),
            ]
        )

        task = Task(gid="123", name="Test")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Modified"
            result = await session.commit_async()

        assert not result.success

    @pytest.mark.asyncio
    async def test_auth_error_handling(self) -> None:
        """Authentication errors (401, 403) are captured."""
        mock_client = create_mock_client()
        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                create_failure_result(message="Unauthorized", status_code=401),
            ]
        )

        task = Task(gid="123", name="Test")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Modified"
            result = await session.commit_async()

        assert not result.success
