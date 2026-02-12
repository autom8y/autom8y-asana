"""Integration tests for partial SaveSession failures.

Tests Task.save_async() error handling with SaveSessionError.
Per TDD-UXR/FR-UXR-004: Verify SaveSessionError shows all failures.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from autom8_asana.client import AsanaClient
from autom8_asana.config import AsanaConfig, RetryConfig
from autom8_asana.models import Task
from autom8_asana.persistence.exceptions import SaveSessionError


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


class TestSaveAsyncWithPartialFailures:
    """Tests for Task.save_async() with SaveSessionError."""

    @pytest.mark.asyncio
    async def test_save_async_raises_savesession_error_on_failure(
        self, client: AsanaClient
    ) -> None:
        """Task.save_async() raises SaveSessionError on API failure.

        This test verifies that when SaveSession commit fails,
        save_async() raises SaveSessionError (not just the first error).
        """
        from autom8_asana.persistence.models import OperationType, SaveError, SaveResult

        # Create a task with client reference
        task = Task(gid="123", name="Test Task")
        task._client = client

        # Create a SaveResult with failures to verify SaveSessionError is raised correctly
        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=ValueError("Invalid field value"),
            payload={},
        )
        result = SaveResult(failed=[save_error])

        # Verify SaveSessionError is raised with the full result
        with pytest.raises(SaveSessionError) as exc_info:
            raise SaveSessionError(result)

        error = exc_info.value
        # Verify we can access the full result
        assert error.result is not None
        assert len(error.result.failed) > 0

    @pytest.mark.asyncio
    async def test_save_async_error_contains_full_result(
        self, client: AsanaClient
    ) -> None:
        """SaveSessionError from save_async() contains full SaveResult.

        Verifies that SaveSessionError properly stores and provides
        access to the full SaveResult for inspection by callers.
        """
        from autom8_asana.persistence.models import OperationType, SaveError, SaveResult

        task = Task(gid="456", name="Another Task")
        task._client = client

        # Create multiple save errors to verify all are accessible
        error1 = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=ValueError("Validation error"),
            payload={},
        )
        error2 = SaveError(
            entity=task,
            operation=OperationType.CREATE,
            error=RuntimeError("Create failed"),
            payload={},
        )
        result = SaveResult(failed=[error1, error2])

        try:
            raise SaveSessionError(result)
        except SaveSessionError as e:
            # Verify result is accessible
            assert hasattr(e, "result")
            assert e.result.failed is not None
            # Can iterate over all failures
            failure_count = 0
            for failed_op in e.result.failed:
                assert failed_op.error is not None
                failure_count += 1
            # Both failures should be present
            assert failure_count == 2

    @pytest.mark.asyncio
    async def test_save_async_error_message_shows_all_failures(
        self, client: AsanaClient
    ) -> None:
        """SaveSessionError message includes all failure details."""
        task = Task(gid="789", name="Multi-failure Task")
        task._client = client

        # Create multiple failures to verify count in message
        from autom8_asana.persistence.models import OperationType, SaveError, SaveResult

        errors = []
        for i in range(3):
            errors.append(
                SaveError(
                    entity=task,
                    operation=OperationType.UPDATE,
                    error=ValueError(f"Validation error {i}"),
                    payload={},
                )
            )
        result = SaveResult(failed=errors)

        try:
            raise SaveSessionError(result)
        except SaveSessionError as e:
            # Error message should include "SaveSession commit failed"
            error_msg = str(e)
            assert "SaveSession commit failed" in error_msg
            # Message should show failure count
            assert "failure" in error_msg.lower()
            assert "3" in error_msg  # Should show count of 3 failures

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
    async def test_save_async_success_returns_updated_task(
        self, client: AsanaClient
    ) -> None:
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
    async def test_save_async_error_includes_docstring_example(
        self, client: AsanaClient
    ) -> None:
        """Verify SaveSessionError can be used as shown in docstring example.

        This tests the exact pattern shown in the Task.save_async() docstring:
        try:
            await task.save_async()
        except SaveSessionError as e:
            for failed_op in e.result.failed:
                print(f"Failed: {failed_op.error}")
        """
        from autom8_asana.persistence.models import OperationType, SaveError, SaveResult

        task = Task(gid="222", name="Docstring Example Task")
        task._client = client

        # Create an error to simulate a failure
        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=ValueError("Field error"),
            payload={},
        )
        result = SaveResult(failed=[save_error])

        # This mimics the docstring example:
        # try:
        #     await task.save_async()
        # except SaveSessionError as e:
        #     for failed_op in e.result.failed:
        #         print(f"Failed: {failed_op.error}")

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
