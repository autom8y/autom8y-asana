"""Integration tests for full CRUD lifecycle using mocked Asana API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
import respx

from autom8_asana.clients.tasks import TasksClient
from autom8_asana.config import AsanaConfig, RetryConfig
from autom8_asana.exceptions import ServerError, SyncInAsyncContextError
from autom8_asana.models import Task
from autom8_asana.transport.http import AsyncHTTPClient


class MockAuthProvider:
    """Mock auth provider for integration testing."""

    def get_secret(self, key: str) -> str:
        return "integration-test-token"


class MockLogger:
    """Mock logger that records calls."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("debug", msg))

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("info", msg))

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("warning", msg))

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("error", msg))

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("exception", msg))


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
def auth_provider() -> MockAuthProvider:
    """Mock auth provider."""
    return MockAuthProvider()


@pytest.fixture
def logger() -> MockLogger:
    """Mock logger."""
    return MockLogger()


@pytest.fixture
async def http_client(
    config: AsanaConfig, auth_provider: MockAuthProvider, logger: MockLogger
) -> AsyncHTTPClient:
    """Create HTTP client for integration testing."""
    client = AsyncHTTPClient(config, auth_provider, logger)
    yield client
    await client.close()


@pytest.fixture
def tasks_client(
    http_client: AsyncHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> TasksClient:
    """Create TasksClient with real HTTP client (mocked at network level)."""
    return TasksClient(
        http=http_client,
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestFullCRUDLifecycle:
    """Test complete Create -> Read -> Update -> Delete lifecycle."""

    @respx.mock
    async def test_full_crud_lifecycle(
        self, tasks_client: TasksClient, http_client: AsyncHTTPClient
    ) -> None:
        """Full CRUD lifecycle: create -> get -> update -> delete."""
        task_gid = "lifecycle123"
        workspace_gid = "workspace456"

        # 1. CREATE
        respx.post("https://app.asana.com/api/1.0/tasks").mock(
            return_value=httpx.Response(
                201,
                json={
                    "data": {
                        "gid": task_gid,
                        "name": "Lifecycle Test Task",
                        "notes": "",
                        "completed": False,
                    }
                },
            )
        )

        created = await tasks_client.create_async(
            name="Lifecycle Test Task",
            workspace=workspace_gid,
        )

        assert isinstance(created, Task)
        assert created.gid == task_gid
        assert created.name == "Lifecycle Test Task"
        assert created.completed is False

        # 2. READ
        respx.get(f"https://app.asana.com/api/1.0/tasks/{task_gid}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "gid": task_gid,
                        "name": "Lifecycle Test Task",
                        "notes": "",
                        "completed": False,
                    }
                },
            )
        )

        fetched = await tasks_client.get_async(task_gid)

        assert isinstance(fetched, Task)
        assert fetched.gid == task_gid
        assert fetched.name == "Lifecycle Test Task"

        # 3. UPDATE
        respx.put(f"https://app.asana.com/api/1.0/tasks/{task_gid}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "gid": task_gid,
                        "name": "Updated Task Name",
                        "notes": "Added notes",
                        "completed": True,
                    }
                },
            )
        )

        updated = await tasks_client.update_async(
            task_gid,
            name="Updated Task Name",
            notes="Added notes",
            completed=True,
        )

        assert isinstance(updated, Task)
        assert updated.name == "Updated Task Name"
        assert updated.notes == "Added notes"
        assert updated.completed is True

        # 4. DELETE
        respx.delete(f"https://app.asana.com/api/1.0/tasks/{task_gid}").mock(
            return_value=httpx.Response(200, json={"data": {}})
        )

        await tasks_client.delete_async(task_gid)

        # Verify all routes were called
        assert respx.calls.call_count == 4


class TestRetryChain:
    """Test retry behavior with multiple failures before success."""

    @respx.mock
    async def test_retry_chain_success(
        self, tasks_client: TasksClient, http_client: AsyncHTTPClient
    ) -> None:
        """Request succeeds after failing twice (third attempt succeeds)."""
        route = respx.get("https://app.asana.com/api/1.0/tasks/retry123")

        # Fail twice with 503, then succeed
        route.side_effect = [
            httpx.Response(503, json={"errors": [{"message": "Service unavailable"}]}),
            httpx.Response(503, json={"errors": [{"message": "Service unavailable"}]}),
            httpx.Response(200, json={"data": {"gid": "retry123", "name": "Retry Task"}}),
        ]

        result = await tasks_client.get_async("retry123")

        assert isinstance(result, Task)
        assert result.gid == "retry123"
        assert result.name == "Retry Task"
        assert route.call_count == 3  # 2 failures + 1 success

    @respx.mock
    async def test_retry_chain_exhausted(
        self, config: AsanaConfig, auth_provider: MockAuthProvider, logger: MockLogger
    ) -> None:
        """Request fails after exhausting all retries."""
        # Create client with limited retries
        limited_config = AsanaConfig(
            base_url=config.base_url,
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        http_client = AsyncHTTPClient(limited_config, auth_provider, logger)
        tasks_client = TasksClient(
            http=http_client,
            config=limited_config,
            auth_provider=auth_provider,
            log_provider=logger,
        )

        route = respx.get("https://app.asana.com/api/1.0/tasks/exhausted")

        # Fail all attempts (initial + 2 retries = 3 total)
        route.side_effect = [
            httpx.Response(503, json={"errors": [{"message": "Attempt 1"}]}),
            httpx.Response(503, json={"errors": [{"message": "Attempt 2"}]}),
            httpx.Response(503, json={"errors": [{"message": "Attempt 3"}]}),
        ]

        with pytest.raises(ServerError) as exc_info:
            await tasks_client.get_async("exhausted")

        assert exc_info.value.status_code == 503
        assert route.call_count == 3  # 1 initial + 2 retries
        await http_client.close()


class TestSyncAsyncMixedUsage:
    """Test that sync and async methods can be used appropriately."""

    @respx.mock
    async def test_sync_async_mixed_usage_async_context(
        self, tasks_client: TasksClient
    ) -> None:
        """In async context, async methods work but sync methods fail."""
        respx.get("https://app.asana.com/api/1.0/tasks/async123").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"gid": "async123", "name": "Async Task"}},
            )
        )

        # Async method should work
        result = await tasks_client.get_async("async123")
        assert isinstance(result, Task)
        assert result.gid == "async123"

        # Sync method should fail in async context
        with pytest.raises(SyncInAsyncContextError):
            tasks_client.get("sync123")

    @respx.mock
    def test_sync_async_mixed_usage_sync_context(
        self, config: AsanaConfig, auth_provider: MockAuthProvider, logger: MockLogger
    ) -> None:
        """In sync context, sync methods work correctly."""
        # Must create fresh client for sync test to avoid event loop issues
        http_client = AsyncHTTPClient(config, auth_provider, logger)
        tasks_client = TasksClient(
            http=http_client,
            config=config,
            auth_provider=auth_provider,
            log_provider=logger,
        )

        respx.get("https://app.asana.com/api/1.0/tasks/sync123").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"gid": "sync123", "name": "Sync Task"}},
            )
        )

        # Sync method should work outside async context
        result = tasks_client.get("sync123")
        assert isinstance(result, Task)
        assert result.gid == "sync123"
        assert result.name == "Sync Task"


class TestWithOptFields:
    """Test that opt_fields are passed correctly through the stack."""

    @respx.mock
    async def test_opt_fields_passed_through(
        self, tasks_client: TasksClient
    ) -> None:
        """opt_fields parameter reaches the API request."""
        route = respx.get("https://app.asana.com/api/1.0/tasks/fields123").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "gid": "fields123",
                        "name": "Task with Fields",
                        "completed": False,
                        "due_on": "2024-12-31",
                    }
                },
            )
        )

        result = await tasks_client.get_async(
            "fields123",
            opt_fields=["name", "completed", "due_on"],
        )

        assert isinstance(result, Task)
        assert result.gid == "fields123"
        assert result.name == "Task with Fields"
        assert result.completed is False
        assert result.due_on == "2024-12-31"

        # Verify the request included opt_fields
        assert route.call_count == 1
        request = route.calls[0].request
        assert "opt_fields=name%2Ccompleted%2Cdue_on" in str(request.url)


class TestConcurrentRequests:
    """Test concurrent request handling."""

    @respx.mock
    async def test_concurrent_reads(
        self, tasks_client: TasksClient
    ) -> None:
        """Multiple concurrent GET requests are handled correctly."""
        for i in range(5):
            respx.get(f"https://app.asana.com/api/1.0/tasks/task{i}").mock(
                return_value=httpx.Response(
                    200,
                    json={"data": {"gid": f"task{i}", "name": f"Task {i}"}},
                )
            )

        # Fire 5 concurrent requests
        tasks = [tasks_client.get_async(f"task{i}") for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for i, result in enumerate(results):
            assert isinstance(result, Task)
            assert result.gid == f"task{i}"
            assert result.name == f"Task {i}"
