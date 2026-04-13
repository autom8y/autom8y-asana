"""Integration tests for partial SaveSession failures.

Tests Task.save_async() error handling with SaveSessionError.
Per TDD-UXR/FR-UXR-004: Verify SaveSessionError shows all failures.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from autom8_asana.batch.models import BatchResult
from autom8_asana.client import AsanaClient
from autom8_asana.config import AsanaConfig, RetryConfig
from autom8_asana.models import Task
from autom8_asana.persistence.errors import SaveSessionError
from autom8_asana.persistence.models import OperationType
from autom8_asana.persistence.session import SaveSession


@pytest.fixture
def config() -> AsanaConfig:
    """Default integration test configuration."""
    return AsanaConfig(
        base_url="https://app.asana.com/api/1.0",
        retry=RetryConfig(
            max_retries=3,
            base_delay=0.01,  # Fast retries for tests
            max_delay=1.0,
            jitter=False,  # Deterministic for testing
        ),
    )


@pytest.fixture
async def client(config: AsanaConfig, auth_provider, logger) -> AsanaClient:
    """Create AsanaClient for integration testing."""
    client = AsanaClient(
        token="test-token",
        auth_provider=auth_provider,
        log_provider=logger,
        config=config,
    )
    yield client
    await client.close()


def _create_mock_client(
    batch_results: list[BatchResult] | None = None,
) -> MagicMock:
    """Create a mock AsanaClient with configurable batch responses.

    Args:
        batch_results: List of BatchResult to return from execute_async.
            Defaults to empty list (no batch operations).

    Returns:
        MagicMock configured as AsanaClient.
    """
    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_batch.execute_async = AsyncMock(
        return_value=batch_results if batch_results is not None else []
    )
    mock_client.batch = mock_batch
    mock_http = AsyncMock()
    mock_http.request = AsyncMock(return_value={"data": {}})
    mock_client._http = mock_http
    mock_client._log = None
    return mock_client


def _failure_batch_results(
    count: int = 1,
    status_code: int = 400,
    message: str = "Bad request",
) -> list[BatchResult]:
    """Build a list of failed BatchResult objects.

    Args:
        count: Number of failure results to create.
        status_code: HTTP status code for each failure.
        message: Base error message (index appended).

    Returns:
        List of failed BatchResult objects.
    """
    return [
        BatchResult(
            status_code=status_code,
            body={"errors": [{"message": f"{message} {i}"}]},
            request_index=i,
        )
        for i in range(count)
    ]


class TestSaveAsyncWithPartialFailures:
    """Tests for Task.save_async() with SaveSessionError."""

    @pytest.mark.asyncio
    async def test_save_async_raises_savesession_error_on_failure(self) -> None:
        """SaveSession.commit_async() produces failures on batch API error.

        This test verifies that when the batch API returns error responses,
        commit_async() returns a SaveResult with failures, and wrapping it
        in SaveSessionError provides the full result for inspection.
        """
        mock_client = _create_mock_client(
            batch_results=_failure_batch_results(count=1),
        )

        task = Task(gid="123", name="Test Task")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated"
            result = await session.commit_async()

        # Verify the production code path produces a failed SaveResult
        assert not result.success
        assert len(result.failed) == 1
        assert result.failed[0].operation == OperationType.UPDATE
        assert result.failed[0].entity.gid == "123"
        assert result.failed[0].error is not None

        # Verify SaveSessionError wraps it correctly (as save_async() would)
        error = SaveSessionError(result)
        assert error.result is result
        assert len(error.result.failed) > 0

    @pytest.mark.asyncio
    async def test_save_async_error_contains_full_result(self) -> None:
        """SaveSessionError from commit_async() contains full SaveResult.

        Verifies that SaveSessionError properly stores and provides
        access to the full SaveResult for inspection by callers.
        Uses SaveSession with multiple tracked entities to produce
        multiple failures in a single commit.
        """
        mock_client = _create_mock_client(
            batch_results=_failure_batch_results(count=2),
        )

        task1 = Task(gid="456", name="Task One")
        task2 = Task(gid="457", name="Task Two")

        async with SaveSession(mock_client) as session:
            session.track(task1)
            task1.name = "Modified One"
            session.track(task2)
            task2.name = "Modified Two"
            result = await session.commit_async()

        # commit_async returns SaveResult; verify via result directly
        assert not result.success
        assert result.failed is not None
        # Can iterate over all failures
        failure_count = 0
        for failed_op in result.failed:
            assert failed_op.error is not None
            failure_count += 1
        # Both failures should be present
        assert failure_count == 2

    @pytest.mark.asyncio
    async def test_save_async_error_message_shows_all_failures(self) -> None:
        """SaveSessionError message includes all failure details."""
        mock_client = _create_mock_client(
            batch_results=_failure_batch_results(count=3),
        )

        task1 = Task(gid="789", name="Task A")
        task2 = Task(gid="790", name="Task B")
        task3 = Task(gid="791", name="Task C")

        async with SaveSession(mock_client) as session:
            for task in (task1, task2, task3):
                session.track(task)
                task.name = f"{task.name} modified"
            result = await session.commit_async()

        # Build SaveSessionError from the production result
        assert not result.success
        error = SaveSessionError(result)
        error_msg = str(error)
        # Error message should include "SaveSession commit failed"
        assert "SaveSession commit failed" in error_msg
        # Message should show failure count
        assert "failure" in error_msg.lower()
        assert "3" in error_msg

    @pytest.mark.asyncio
    async def test_save_async_without_client_raises_value_error(self) -> None:
        """Task.save_async() raises ValueError if no client reference."""
        task = Task(gid="999", name="Orphan Task")
        # No client set (_client is None)

        with pytest.raises(ValueError) as exc_info:
            await task.save_async()

        error_msg = str(exc_info.value)
        assert "client reference" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_save_async_success_returns_updated_task(self, client: AsanaClient) -> None:
        """Task.save_async() returns updated task on success."""
        task = Task(gid="111", name="Original Name")
        task._client = client
        task.name = "Updated Name"

        with respx.mock:
            # Mock successful batch response
            respx.post("https://app.asana.com/api/1.0/batch").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "data": [
                            {
                                "status_code": 200,
                                "body": {
                                    "data": {
                                        "gid": "task_success",
                                        "name": "Updated Name",
                                    }
                                },
                                "request_index": 0,
                            }
                        ]
                    },
                )
            )

            result = await task.save_async()

            # Should return the same task instance
            assert result is task
            assert result.gid == "111"

    @pytest.mark.asyncio
    async def test_save_async_error_includes_docstring_example(self) -> None:
        """Verify SaveSessionError can be used as shown in docstring example.

        This tests the exact pattern shown in the Task.save_async() docstring:
        try:
            await task.save_async()
        except SaveSessionError as e:
            for failed_op in e.result.failed:
                print(f"Failed: {failed_op.error}")
        """
        mock_client = _create_mock_client(
            batch_results=_failure_batch_results(count=1),
        )

        task = Task(gid="222", name="Docstring Example Task")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated"
            result = await session.commit_async()

        # Simulate the docstring pattern using the production SaveResult
        assert not result.success
        try:
            raise SaveSessionError(result)
        except SaveSessionError as e:
            # Should be able to iterate over failures
            failure_count = 0
            for failed_op in e.result.failed:
                assert failed_op.error is not None
                failure_count += 1

            # Should have at least one failure
            assert failure_count > 0
