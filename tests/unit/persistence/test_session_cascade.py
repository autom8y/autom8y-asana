"""Tests for SaveSession cascade execution integration.

Per TDD-TRIAGE-FIXES Issue 11: Cascade operations must be executed during commit_async().
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.models import Task
from autom8_asana.persistence.cascade import CascadeOperation, CascadeResult
from autom8_asana.persistence.models import SaveResult
from autom8_asana.persistence.session import SaveSession


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

    # Add mock HTTP client for action executor
    mock_http = AsyncMock()
    mock_http.request = AsyncMock(return_value={"data": {}})
    mock_client._http = mock_http

    return mock_client


def create_mock_entity() -> MagicMock:
    """Create a mock BusinessEntity for cascade testing."""
    mock_entity = MagicMock()
    mock_entity.gid = "entity_123"
    return mock_entity


# ---------------------------------------------------------------------------
# Cascade Operation Queuing Tests
# ---------------------------------------------------------------------------


class TestCascadeOperationQueuing:
    """Tests for cascade_field() operation queuing."""

    def test_cascade_operations_queued_correctly(self) -> None:
        """cascade_field() adds operations to the internal list.

        Per TDD-TRIAGE-FIXES: cascade_field() should append to _cascade_operations.
        """
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        mock_entity = create_mock_entity()

        # Queue a cascade operation
        session.cascade_field(mock_entity, "Office Phone")

        # Verify operation was queued
        pending = session.get_pending_cascades()
        assert len(pending) == 1
        assert pending[0].source_entity is mock_entity
        assert pending[0].field_name == "Office Phone"

    def test_multiple_cascade_operations_queued(self) -> None:
        """Multiple cascade_field() calls queue multiple operations."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        mock_entity = create_mock_entity()

        # Queue multiple cascade operations
        session.cascade_field(mock_entity, "Office Phone")
        session.cascade_field(mock_entity, "Vertical")

        # Verify both were queued
        pending = session.get_pending_cascades()
        assert len(pending) == 2
        assert pending[0].field_name == "Office Phone"
        assert pending[1].field_name == "Vertical"

    def test_cascade_field_returns_session_for_chaining(self) -> None:
        """cascade_field() returns self for fluent chaining."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        mock_entity = create_mock_entity()

        result = session.cascade_field(mock_entity, "Office Phone")

        assert result is session

    def test_cascade_field_with_target_types(self) -> None:
        """cascade_field() accepts target_types parameter."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        mock_entity = create_mock_entity()

        # Queue with target_types
        session.cascade_field(mock_entity, "Vertical", target_types=(Task,))

        pending = session.get_pending_cascades()
        assert len(pending) == 1
        assert pending[0].target_types == (Task,)


# ---------------------------------------------------------------------------
# Cascade Execution During Commit Tests
# ---------------------------------------------------------------------------


class TestCascadeExecutionDuringCommit:
    """Tests for cascade execution during commit_async()."""

    @pytest.mark.asyncio
    async def test_cascades_executed_during_commit(self) -> None:
        """Cascade executor is called with pending cascades during commit.

        Per TDD-TRIAGE-FIXES: commit_async() must invoke CascadeExecutor.execute().
        """
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        mock_entity = create_mock_entity()

        # Queue a cascade operation
        session.cascade_field(mock_entity, "Office Phone")

        # Mock the cascade executor
        mock_result = CascadeResult(
            operations_queued=1,
            operations_succeeded=1,
            operations_failed=0,
        )
        session._cascade_executor.execute = AsyncMock(return_value=mock_result)

        # Commit
        result = await session.commit_async()

        # Verify executor was called
        session._cascade_executor.execute.assert_called_once()
        call_args = session._cascade_executor.execute.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0].field_name == "Office Phone"

    @pytest.mark.asyncio
    async def test_cascades_cleared_on_success(self) -> None:
        """Successful cascades are cleared from pending list.

        Per TDD-TRIAGE-FIXES: After successful cascade, get_pending_cascades() returns empty.
        """
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        mock_entity = create_mock_entity()

        # Queue a cascade operation
        session.cascade_field(mock_entity, "Office Phone")

        # Mock successful cascade result
        mock_result = CascadeResult(
            operations_queued=1,
            operations_succeeded=1,
            operations_failed=0,
        )
        session._cascade_executor.execute = AsyncMock(return_value=mock_result)

        # Commit
        await session.commit_async()

        # Verify cascades were cleared
        pending = session.get_pending_cascades()
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_cascades_preserved_on_failure(self) -> None:
        """Failed cascades remain in pending list for retry.

        Per TDD-TRIAGE-FIXES: Failed cascades are NOT cleared.
        """
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        mock_entity = create_mock_entity()

        # Queue a cascade operation
        session.cascade_field(mock_entity, "Office Phone")

        # Mock failed cascade result
        mock_result = CascadeResult(
            operations_queued=1,
            operations_succeeded=0,
            operations_failed=1,
            errors=["Failed to cascade"],
        )
        session._cascade_executor.execute = AsyncMock(return_value=mock_result)

        # Commit
        await session.commit_async()

        # Verify cascades were NOT cleared
        pending = session.get_pending_cascades()
        assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_cascade_result_in_save_result(self) -> None:
        """SaveResult.cascade_results is populated after commit.

        Per TDD-TRIAGE-FIXES: result.cascade_results contains execution results.
        """
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        mock_entity = create_mock_entity()

        # Queue a cascade operation
        session.cascade_field(mock_entity, "Office Phone")

        # Mock cascade result
        mock_result = CascadeResult(
            operations_queued=1,
            operations_succeeded=1,
            operations_failed=0,
        )
        session._cascade_executor.execute = AsyncMock(return_value=mock_result)

        # Commit
        result = await session.commit_async()

        # Verify cascade_results is populated
        assert len(result.cascade_results) == 1
        assert result.cascade_results[0] is mock_result

    @pytest.mark.asyncio
    async def test_save_result_success_includes_cascades(self) -> None:
        """SaveResult.success is False when cascade fails.

        Per TDD-TRIAGE-FIXES: success property must include cascade status.
        """
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        mock_entity = create_mock_entity()

        # Queue a cascade operation
        session.cascade_field(mock_entity, "Office Phone")

        # Mock failed cascade result
        mock_result = CascadeResult(
            operations_queued=1,
            operations_succeeded=0,
            operations_failed=1,
        )
        session._cascade_executor.execute = AsyncMock(return_value=mock_result)

        # Commit
        result = await session.commit_async()

        # Verify success is False due to cascade failure
        assert result.success is False

    @pytest.mark.asyncio
    async def test_no_cascades_results_in_empty_cascade_results(self) -> None:
        """When no cascades queued, cascade_results is empty list."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        # Track a task (no cascades)
        task = Task(gid="123", name="Test")
        session.track(task)

        # Commit
        result = await session.commit_async()

        # Verify empty cascade_results
        assert result.cascade_results == []


# ---------------------------------------------------------------------------
# SaveResult Cascade Properties Tests
# ---------------------------------------------------------------------------


class TestSaveResultCascadeProperties:
    """Tests for SaveResult cascade-related properties."""

    def test_cascade_succeeded_count(self) -> None:
        """cascade_succeeded property counts successful cascades."""
        result = SaveResult(
            cascade_results=[
                CascadeResult(operations_succeeded=1, operations_failed=0),
                CascadeResult(operations_succeeded=1, operations_failed=0),
            ]
        )

        assert result.cascade_succeeded == 2

    def test_cascade_failed_count(self) -> None:
        """cascade_failed property counts failed cascades."""
        result = SaveResult(
            cascade_results=[
                CascadeResult(operations_succeeded=0, operations_failed=1),
                CascadeResult(operations_succeeded=1, operations_failed=0),
            ]
        )

        assert result.cascade_failed == 1

    def test_success_with_all_cascade_success(self) -> None:
        """success is True when all cascades succeed."""
        result = SaveResult(
            cascade_results=[
                CascadeResult(operations_succeeded=1, operations_failed=0),
            ]
        )

        assert result.success is True

    def test_success_with_cascade_failure(self) -> None:
        """success is False when any cascade fails."""
        result = SaveResult(
            cascade_results=[
                CascadeResult(operations_succeeded=0, operations_failed=1),
            ]
        )

        assert result.success is False

    def test_success_with_empty_cascade_results(self) -> None:
        """success is True when no cascades (empty list)."""
        result = SaveResult(cascade_results=[])

        assert result.success is True


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestCascadeIntegration:
    """Integration tests for cascade execution flow."""

    @pytest.mark.asyncio
    async def test_cascades_only_commit_executes_cascades(self) -> None:
        """Commit with only cascades (no CRUD/actions) executes successfully."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        mock_entity = create_mock_entity()

        # Queue only cascade operations (no track)
        session.cascade_field(mock_entity, "Office Phone")

        # Mock cascade result
        mock_result = CascadeResult(
            operations_queued=1,
            operations_succeeded=1,
            operations_failed=0,
        )
        session._cascade_executor.execute = AsyncMock(return_value=mock_result)

        # Commit should succeed
        result = await session.commit_async()

        assert result.success is True
        assert len(result.cascade_results) == 1

    @pytest.mark.asyncio
    async def test_cascade_executor_initialized_in_init(self) -> None:
        """CascadeExecutor is initialized in SaveSession.__init__.

        Per TDD-TRIAGE-FIXES: Executor must be pre-initialized.
        """
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        # Verify executor exists
        assert hasattr(session, "_cascade_executor")
        assert session._cascade_executor is not None

    @pytest.mark.asyncio
    async def test_cascade_operations_list_initialized_in_init(self) -> None:
        """_cascade_operations list is initialized in SaveSession.__init__.

        Per TDD-TRIAGE-FIXES: List must be pre-initialized, not lazy.
        """
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        # Verify list exists without calling cascade_field
        assert hasattr(session, "_cascade_operations")
        assert session._cascade_operations == []
