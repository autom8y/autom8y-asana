"""Tests for TasksClient."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.clients.tasks import TasksClient
from autom8_asana.config import AsanaConfig
from autom8_asana.exceptions import SyncInAsyncContextError
from autom8_asana.models import Task


class MockHTTPClient:
    """Mock HTTP client for testing TasksClient."""

    def __init__(self) -> None:
        self.get = AsyncMock()
        self.post = AsyncMock()
        self.put = AsyncMock()
        self.delete = AsyncMock()


class MockAuthProvider:
    """Mock auth provider."""

    def get_secret(self, key: str) -> str:
        return "test-token"


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
def mock_http() -> MockHTTPClient:
    """Create mock HTTP client."""
    return MockHTTPClient()


@pytest.fixture
def config() -> AsanaConfig:
    """Default test configuration."""
    return AsanaConfig()


@pytest.fixture
def auth_provider() -> MockAuthProvider:
    """Mock auth provider."""
    return MockAuthProvider()


@pytest.fixture
def logger() -> MockLogger:
    """Mock logger."""
    return MockLogger()


@pytest.fixture
def tasks_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> TasksClient:
    """Create TasksClient with mocked dependencies."""
    return TasksClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestGetAsync:
    """Tests for TasksClient.get_async()."""

    async def test_get_async_returns_task_model(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async returns Task model by default."""
        mock_http.get.return_value = {"gid": "123", "name": "Test Task"}

        result = await tasks_client.get_async("123")

        assert isinstance(result, Task)
        assert result.gid == "123"
        assert result.name == "Test Task"
        mock_http.get.assert_called_once_with("/tasks/123", params={})

    async def test_get_async_raw_returns_dict(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async with raw=True returns dict."""
        mock_http.get.return_value = {"gid": "123", "name": "Test Task"}

        result = await tasks_client.get_async("123", raw=True)

        assert isinstance(result, dict)
        assert result == {"gid": "123", "name": "Test Task"}
        mock_http.get.assert_called_once_with("/tasks/123", params={})

    async def test_get_async_with_opt_fields(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async passes opt_fields as comma-separated query param."""
        mock_http.get.return_value = {"gid": "123", "name": "Test Task", "notes": "Notes"}

        result = await tasks_client.get_async(
            "123", opt_fields=["name", "notes", "completed"]
        )

        assert isinstance(result, Task)
        assert result.gid == "123"
        assert result.name == "Test Task"
        assert result.notes == "Notes"
        mock_http.get.assert_called_once_with(
            "/tasks/123",
            params={"opt_fields": "name,notes,completed"},
        )


class TestGetSync:
    """Tests for TasksClient.get() sync wrapper."""

    def test_get_sync_returns_task_model(
        self, mock_http: MockHTTPClient, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """get() returns Task model by default outside async context."""
        # Create fresh client for sync test (avoids shared event loop issues)
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.get.return_value = {"gid": "456", "name": "Sync Task"}

        result = client.get("456")

        assert isinstance(result, Task)
        assert result.gid == "456"
        assert result.name == "Sync Task"
        mock_http.get.assert_called_once_with("/tasks/456", params={})

    def test_get_sync_raw_returns_dict(
        self, mock_http: MockHTTPClient, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """get() with raw=True returns dict outside async context."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.get.return_value = {"gid": "456", "name": "Sync Task"}

        result = client.get("456", raw=True)

        assert isinstance(result, dict)
        assert result == {"gid": "456", "name": "Sync Task"}

    async def test_get_sync_fails_in_async_context(
        self, tasks_client: TasksClient
    ) -> None:
        """get() raises SyncInAsyncContextError when called from async."""
        with pytest.raises(SyncInAsyncContextError) as exc_info:
            tasks_client.get("123")

        assert "get_async" in str(exc_info.value)
        assert "async context" in str(exc_info.value)


class TestCreateAsync:
    """Tests for TasksClient.create_async()."""

    async def test_create_async_returns_task_model(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async returns Task model by default."""
        mock_http.post.return_value = {"gid": "new123", "name": "New Task"}

        result = await tasks_client.create_async(name="New Task", workspace="workspace123")

        assert isinstance(result, Task)
        assert result.gid == "new123"
        assert result.name == "New Task"
        mock_http.post.assert_called_once_with(
            "/tasks",
            json={"data": {"name": "New Task", "workspace": "workspace123"}},
        )

    async def test_create_async_raw_returns_dict(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async with raw=True returns dict."""
        mock_http.post.return_value = {"gid": "new123", "name": "New Task"}

        result = await tasks_client.create_async(
            name="New Task", workspace="workspace123", raw=True
        )

        assert isinstance(result, dict)
        assert result == {"gid": "new123", "name": "New Task"}

    async def test_create_async_with_projects(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async with projects includes projects in request."""
        mock_http.post.return_value = {"gid": "new456", "name": "Project Task"}

        result = await tasks_client.create_async(
            name="Project Task",
            projects=["proj1", "proj2"],
        )

        assert isinstance(result, Task)
        assert result.gid == "new456"
        assert result.name == "Project Task"
        mock_http.post.assert_called_once_with(
            "/tasks",
            json={"data": {"name": "Project Task", "projects": ["proj1", "proj2"]}},
        )

    async def test_create_async_with_parent(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async with parent creates subtask."""
        mock_http.post.return_value = {"gid": "subtask789", "name": "Subtask"}

        result = await tasks_client.create_async(
            name="Subtask",
            parent="parent123",
        )

        assert isinstance(result, Task)
        assert result.gid == "subtask789"
        assert result.name == "Subtask"
        mock_http.post.assert_called_once_with(
            "/tasks",
            json={"data": {"name": "Subtask", "parent": "parent123"}},
        )

    async def test_create_async_with_notes_and_kwargs(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async accepts notes and additional kwargs."""
        mock_http.post.return_value = {
            "gid": "full123",
            "name": "Full Task",
            "notes": "Task description",
            "due_on": "2024-12-31",
        }

        result = await tasks_client.create_async(
            name="Full Task",
            workspace="ws123",
            notes="Task description",
            due_on="2024-12-31",
            custom_fields={"field1": "value1"},
        )

        assert isinstance(result, Task)
        assert result.gid == "full123"
        assert result.name == "Full Task"
        assert result.notes == "Task description"
        assert result.due_on == "2024-12-31"
        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        data = call_args[1]["json"]["data"]
        assert data["name"] == "Full Task"
        assert data["workspace"] == "ws123"
        assert data["notes"] == "Task description"
        assert data["due_on"] == "2024-12-31"
        assert data["custom_fields"] == {"field1": "value1"}


class TestUpdateAsync:
    """Tests for TasksClient.update_async()."""

    async def test_update_async_returns_task_model(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """update_async returns Task model by default."""
        mock_http.put.return_value = {"gid": "123", "name": "Updated Name"}

        result = await tasks_client.update_async("123", name="Updated Name")

        assert isinstance(result, Task)
        assert result.gid == "123"
        assert result.name == "Updated Name"
        mock_http.put.assert_called_once_with(
            "/tasks/123",
            json={"data": {"name": "Updated Name"}},
        )

    async def test_update_async_raw_returns_dict(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """update_async with raw=True returns dict."""
        mock_http.put.return_value = {"gid": "123", "name": "Updated Name"}

        result = await tasks_client.update_async("123", raw=True, name="Updated Name")

        assert isinstance(result, dict)
        assert result == {"gid": "123", "name": "Updated Name"}

    async def test_update_async_multiple_fields(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """update_async with multiple fields includes all in request."""
        mock_http.put.return_value = {
            "gid": "123",
            "name": "Multi Update",
            "completed": True,
            "due_on": "2024-12-31",
        }

        result = await tasks_client.update_async(
            "123",
            name="Multi Update",
            completed=True,
            due_on="2024-12-31",
        )

        assert isinstance(result, Task)
        assert result.gid == "123"
        assert result.completed is True
        assert result.due_on == "2024-12-31"
        mock_http.put.assert_called_once()
        call_args = mock_http.put.call_args
        data = call_args[1]["json"]["data"]
        assert data == {
            "name": "Multi Update",
            "completed": True,
            "due_on": "2024-12-31",
        }


class TestDeleteAsync:
    """Tests for TasksClient.delete_async()."""

    async def test_delete_async_success(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """delete_async sends DELETE request and returns None."""
        mock_http.delete.return_value = {}

        result = await tasks_client.delete_async("123")

        # delete_async returns None
        assert result is None
        mock_http.delete.assert_called_once_with("/tasks/123")


class TestSyncWrappers:
    """Test sync wrapper variants for all methods."""

    def test_create_sync_returns_task_model(
        self, mock_http: MockHTTPClient, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """create() sync wrapper returns Task model by default."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.post.return_value = {"gid": "sync123", "name": "Sync Create"}

        result = client.create(name="Sync Create", workspace="ws")

        assert isinstance(result, Task)
        assert result.gid == "sync123"
        assert result.name == "Sync Create"

    def test_create_sync_raw_returns_dict(
        self, mock_http: MockHTTPClient, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """create() sync wrapper with raw=True returns dict."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.post.return_value = {"gid": "sync123", "name": "Sync Create"}

        result = client.create(name="Sync Create", workspace="ws", raw=True)

        assert isinstance(result, dict)
        assert result == {"gid": "sync123", "name": "Sync Create"}

    def test_update_sync_returns_task_model(
        self, mock_http: MockHTTPClient, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """update() sync wrapper returns Task model by default."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.put.return_value = {"gid": "sync456", "name": "Updated"}

        result = client.update("sync456", name="Updated")

        assert isinstance(result, Task)
        assert result.gid == "sync456"
        assert result.name == "Updated"

    def test_update_sync_raw_returns_dict(
        self, mock_http: MockHTTPClient, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """update() sync wrapper with raw=True returns dict."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.put.return_value = {"gid": "sync456", "name": "Updated"}

        result = client.update("sync456", raw=True, name="Updated")

        assert isinstance(result, dict)
        assert result == {"gid": "sync456", "name": "Updated"}

    def test_delete_sync_works(
        self, mock_http: MockHTTPClient, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """delete() sync wrapper works outside async context."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.delete.return_value = {}

        # Should not raise
        client.delete("sync789")

        mock_http.delete.assert_called_once_with("/tasks/sync789")


class TestLogging:
    """Test that operations are logged correctly."""

    async def test_operations_are_logged(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient, logger: MockLogger
    ) -> None:
        """All operations log their invocation."""
        mock_http.get.return_value = {"gid": "123"}
        mock_http.post.return_value = {"gid": "456"}
        mock_http.put.return_value = {"gid": "123"}
        mock_http.delete.return_value = {}

        await tasks_client.get_async("123")
        await tasks_client.create_async(name="Test", workspace="ws")
        await tasks_client.update_async("123", name="Updated")
        await tasks_client.delete_async("123")

        # Check that operations were logged
        debug_messages = [msg for level, msg in logger.messages if level == "debug"]
        assert any("get_async" in msg for msg in debug_messages)
        assert any("create_async" in msg for msg in debug_messages)
        assert any("update_async" in msg for msg in debug_messages)
        assert any("delete_async" in msg for msg in debug_messages)
