"""Tests for TasksClient."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.clients.tasks import TasksClient
from autom8_asana.config import AsanaConfig
from autom8_asana.exceptions import SyncInAsyncContextError
from autom8_asana.models import PageIterator, Task


class MockHTTPClient:
    """Mock HTTP client for testing TasksClient."""

    def __init__(self) -> None:
        self.get = AsyncMock()
        self.post = AsyncMock()
        self.put = AsyncMock()
        self.delete = AsyncMock()
        self.get_paginated = AsyncMock()


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
        client=None,  # P1 tests will mock SaveSession separately
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
        mock_http.get.return_value = {
            "gid": "123",
            "name": "Test Task",
            "notes": "Notes",
        }

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
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
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
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
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
        mock_http.post.return_value = {"gid": "5123", "name": "New Task"}

        result = await tasks_client.create_async(name="New Task", workspace="9123")

        assert isinstance(result, Task)
        assert result.gid == "5123"
        assert result.name == "New Task"
        mock_http.post.assert_called_once_with(
            "/tasks",
            json={"data": {"name": "New Task", "workspace": "9123"}},
        )

    async def test_create_async_raw_returns_dict(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async with raw=True returns dict."""
        mock_http.post.return_value = {"gid": "5123", "name": "New Task"}

        result = await tasks_client.create_async(
            name="New Task", workspace="9123", raw=True
        )

        assert isinstance(result, dict)
        assert result == {"gid": "5123", "name": "New Task"}

    async def test_create_async_with_projects(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async with projects includes projects in request."""
        mock_http.post.return_value = {"gid": "5456", "name": "Project Task"}

        result = await tasks_client.create_async(
            name="Project Task",
            projects=["proj1", "proj2"],
        )

        assert isinstance(result, Task)
        assert result.gid == "5456"
        assert result.name == "Project Task"
        mock_http.post.assert_called_once_with(
            "/tasks",
            json={"data": {"name": "Project Task", "projects": ["proj1", "proj2"]}},
        )

    async def test_create_async_with_parent(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async with parent creates subtask."""
        mock_http.post.return_value = {"gid": "5789", "name": "Subtask"}

        result = await tasks_client.create_async(
            name="Subtask",
            parent="5123",
        )

        assert isinstance(result, Task)
        assert result.gid == "5789"
        assert result.name == "Subtask"
        mock_http.post.assert_called_once_with(
            "/tasks",
            json={"data": {"name": "Subtask", "parent": "5123"}},
        )

    async def test_create_async_with_notes_and_kwargs(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async accepts notes and additional kwargs."""
        mock_http.post.return_value = {
            "gid": "8123",
            "name": "Full Task",
            "notes": "Task description",
            "due_on": "2024-12-31",
        }

        result = await tasks_client.create_async(
            name="Full Task",
            workspace="9123",
            notes="Task description",
            due_on="2024-12-31",
            custom_fields={"field1": "value1"},
        )

        assert isinstance(result, Task)
        assert result.gid == "8123"
        assert result.name == "Full Task"
        assert result.notes == "Task description"
        assert result.due_on == "2024-12-31"
        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        data = call_args[1]["json"]["data"]
        assert data["name"] == "Full Task"
        assert data["workspace"] == "9123"
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
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """create() sync wrapper returns Task model by default."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.post.return_value = {"gid": "7123", "name": "Sync Create"}

        result = client.create(name="Sync Create", workspace="ws")

        assert isinstance(result, Task)
        assert result.gid == "7123"
        assert result.name == "Sync Create"

    def test_create_sync_raw_returns_dict(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """create() sync wrapper with raw=True returns dict."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.post.return_value = {"gid": "7123", "name": "Sync Create"}

        result = client.create(name="Sync Create", workspace="ws", raw=True)

        assert isinstance(result, dict)
        assert result == {"gid": "7123", "name": "Sync Create"}

    def test_update_sync_returns_task_model(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """update() sync wrapper returns Task model by default."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.put.return_value = {"gid": "7456", "name": "Updated"}

        result = client.update("7456", name="Updated")

        assert isinstance(result, Task)
        assert result.gid == "7456"
        assert result.name == "Updated"

    def test_update_sync_raw_returns_dict(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """update() sync wrapper with raw=True returns dict."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.put.return_value = {"gid": "7456", "name": "Updated"}

        result = client.update("7456", raw=True, name="Updated")

        assert isinstance(result, dict)
        assert result == {"gid": "7456", "name": "Updated"}

    def test_delete_sync_works(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """delete() sync wrapper works outside async context."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.delete.return_value = {}

        # Should not raise
        client.delete("7789")

        mock_http.delete.assert_called_once_with("/tasks/7789")


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


class TestSubtasksAsync:
    """Tests for TasksClient.subtasks_async()."""

    async def test_subtasks_async_returns_page_iterator(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """subtasks_async returns PageIterator[Task]."""
        mock_http.get_paginated.return_value = (
            [
                {"gid": "sub1", "name": "Subtask 1"},
                {"gid": "sub2", "name": "Subtask 2"},
            ],
            None,
        )

        result = tasks_client.subtasks_async("5123")

        assert isinstance(result, PageIterator)

        # Collect results
        items = await result.collect()
        assert len(items) == 2
        assert all(isinstance(t, Task) for t in items)
        assert items[0].gid == "sub1"
        assert items[0].name == "Subtask 1"
        assert items[1].gid == "sub2"
        assert items[1].name == "Subtask 2"

    async def test_subtasks_async_empty_result(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """subtasks_async handles empty result (parent has no subtasks)."""
        mock_http.get_paginated.return_value = ([], None)

        result = tasks_client.subtasks_async("parent_no_children")

        items = await result.collect()
        assert items == []

    async def test_subtasks_async_with_opt_fields(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """subtasks_async passes opt_fields parameter correctly."""
        mock_http.get_paginated.return_value = (
            [{"gid": "sub1", "name": "Subtask 1", "notes": "Some notes"}],
            None,
        )

        result = tasks_client.subtasks_async("5123", opt_fields=["name", "notes"])

        items = await result.collect()
        assert len(items) == 1
        assert items[0].notes == "Some notes"

        # Verify opt_fields was passed in params
        mock_http.get_paginated.assert_called_once()
        call_args = mock_http.get_paginated.call_args
        assert call_args[1]["params"]["opt_fields"] == "name,notes"

    async def test_subtasks_async_with_limit(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """subtasks_async respects limit parameter."""
        mock_http.get_paginated.return_value = (
            [{"gid": "sub1", "name": "Subtask 1"}],
            None,
        )

        result = tasks_client.subtasks_async("5123", limit=50)

        await result.collect()

        # Verify limit was passed in params
        mock_http.get_paginated.assert_called_once()
        call_args = mock_http.get_paginated.call_args
        assert call_args[1]["params"]["limit"] == 50

    async def test_subtasks_async_limit_capped_at_100(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """subtasks_async caps limit at 100 (Asana API max)."""
        mock_http.get_paginated.return_value = (
            [{"gid": "sub1", "name": "Subtask 1"}],
            None,
        )

        result = tasks_client.subtasks_async("5123", limit=200)

        await result.collect()

        # Verify limit is capped at 100
        mock_http.get_paginated.assert_called_once()
        call_args = mock_http.get_paginated.call_args
        assert call_args[1]["params"]["limit"] == 100

    async def test_subtasks_async_pagination(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """subtasks_async handles multiple pages correctly."""
        # First call returns page 1 with offset for next page
        # Second call returns page 2 with no more pages
        mock_http.get_paginated.side_effect = [
            ([{"gid": "sub1", "name": "Subtask 1"}], "offset_token"),
            ([{"gid": "sub2", "name": "Subtask 2"}], None),
        ]

        result = tasks_client.subtasks_async("5123")

        items = await result.collect()

        assert len(items) == 2
        assert items[0].gid == "sub1"
        assert items[1].gid == "sub2"

        # Verify both pages were fetched
        assert mock_http.get_paginated.call_count == 2

        # First call should not have offset
        first_call = mock_http.get_paginated.call_args_list[0]
        assert "offset" not in first_call[1]["params"]

        # Second call should have offset from first response
        second_call = mock_http.get_paginated.call_args_list[1]
        assert second_call[1]["params"]["offset"] == "offset_token"

    async def test_subtasks_async_endpoint_verification(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """subtasks_async calls correct endpoint /tasks/{task_gid}/subtasks."""
        mock_http.get_paginated.return_value = (
            [{"gid": "sub1", "name": "Subtask 1"}],
            None,
        )

        result = tasks_client.subtasks_async("5123")

        await result.collect()

        # Verify the correct endpoint was called
        mock_http.get_paginated.assert_called_once()
        call_args = mock_http.get_paginated.call_args
        assert call_args[0][0] == "/tasks/5123/subtasks"

    async def test_subtasks_async_logs_operation(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient, logger: MockLogger
    ) -> None:
        """subtasks_async logs the operation."""
        mock_http.get_paginated.return_value = (
            [{"gid": "sub1", "name": "Subtask 1"}],
            None,
        )

        result = tasks_client.subtasks_async("5123")
        await result.collect()

        # Verify operation was logged
        debug_messages = [msg for level, msg in logger.messages if level == "debug"]
        assert any("subtasks_async" in msg for msg in debug_messages)


class TestP1DirectMethodsAddTag:
    """Tests for P1 Direct Methods: add_tag_async and add_tag."""

    async def test_add_tag_async_returns_updated_task(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """add_tag_async returns updated Task object."""
        from unittest.mock import AsyncMock, patch

        # Mock SaveSession
        mock_session = MagicMock()
        mock_session.add_tag = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {
                "gid": "5123",
                "name": "Test Task",
                "tags": [],
            }

            result = await tasks_client.add_tag_async("5123", "1456")

            assert isinstance(result, Task)
            assert result.gid == "5123"
            # Verify get was called to fetch task
            assert mock_http.get.called

    async def test_add_tag_async_uses_save_session(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """add_tag_async creates and uses SaveSession internally."""
        from unittest.mock import AsyncMock, patch

        mock_session = MagicMock()
        mock_session.add_tag = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {
                "gid": "5123",
                "name": "Test Task",
                "tags": [],
            }

            await tasks_client.add_tag_async("5123", "1456")

            # Verify SaveSession was created and used
            mock_save_session_class.assert_called_once()
            # Verify add_tag was called on the session
            mock_session.add_tag.assert_called_once()

    async def test_add_tag_async_raises_on_invalid_task(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """add_tag_async raises error if task doesn't exist."""
        from autom8_asana.exceptions import NotFoundError
        from unittest.mock import patch, AsyncMock

        mock_session = MagicMock()
        mock_session.add_tag = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            # Reset mock_http to avoid side effects from other tests
            mock_http.get.side_effect = NotFoundError("Not found")

            with pytest.raises(NotFoundError):
                await tasks_client.add_tag_async("5999", "1456")

    def test_add_tag_sync_delegates_to_async(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """add_tag sync wrapper delegates to add_tag_async."""
        from unittest.mock import AsyncMock, patch

        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            client=None,
        )

        mock_session = MagicMock()
        mock_session.add_tag = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {
                "gid": "5123",
                "name": "Test Task",
                "tags": [],
            }

            result = client.add_tag("5123", "1456")

            assert isinstance(result, Task)
            assert result.gid == "5123"


class TestP1DirectMethodsRemoveTag:
    """Tests for P1 Direct Methods: remove_tag_async and remove_tag."""

    async def test_remove_tag_async_returns_updated_task(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """remove_tag_async returns updated Task object."""
        from unittest.mock import AsyncMock, patch

        mock_session = MagicMock()
        mock_session.remove_tag = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {
                "gid": "5123",
                "name": "Test Task",
                "tags": [{"gid": "1456"}],
            }

            result = await tasks_client.remove_tag_async("5123", "1456")

            assert isinstance(result, Task)
            assert result.gid == "5123"
            assert mock_http.get.called

    def test_remove_tag_sync_delegates_to_async(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """remove_tag sync wrapper delegates to remove_tag_async."""
        from unittest.mock import AsyncMock, patch

        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            client=None,
        )

        mock_session = MagicMock()
        mock_session.remove_tag = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {
                "gid": "5123",
                "name": "Test Task",
                "tags": [{"gid": "1456"}],
            }

            result = client.remove_tag("5123", "1456")

            assert isinstance(result, Task)


class TestP1DirectMethodsMoveToSection:
    """Tests for P1 Direct Methods: move_to_section_async and move_to_section."""

    async def test_move_to_section_async_returns_updated_task(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """move_to_section_async returns updated Task object."""
        from unittest.mock import AsyncMock, patch

        mock_session = MagicMock()
        mock_session.move_to_section = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {
                "gid": "5123",
                "name": "Test Task",
                "section": {"gid": "3789"},
            }

            result = await tasks_client.move_to_section_async("5123", "3789", "2456")

            assert isinstance(result, Task)
            assert result.gid == "5123"
            assert mock_http.get.called

    def test_move_to_section_sync_delegates_to_async(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """move_to_section sync wrapper delegates to move_to_section_async."""
        from unittest.mock import AsyncMock, patch

        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            client=None,
        )

        mock_session = MagicMock()
        mock_session.move_to_section = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {
                "gid": "5123",
                "name": "Test Task",
                "section": {"gid": "3789"},
            }

            result = client.move_to_section("5123", "3789", "2456")

            assert isinstance(result, Task)


class TestP1DirectMethodsSetAssignee:
    """Tests for P1 Direct Methods: set_assignee_async and set_assignee."""

    async def test_set_assignee_async_returns_updated_task(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """set_assignee_async returns updated Task object."""
        mock_http.put.return_value = {
            "gid": "5123",
            "name": "Test Task",
            "assignee": {"gid": "6789"},
        }

        result = await tasks_client.set_assignee_async("5123", "6789")

        assert isinstance(result, Task)
        assert result.gid == "5123"
        mock_http.put.assert_called_once()

    async def test_set_assignee_async_sends_correct_payload(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """set_assignee_async sends assignee in correct API format."""
        mock_http.put.return_value = {
            "gid": "5123",
            "name": "Test Task",
            "assignee": {"gid": "6789"},
        }

        await tasks_client.set_assignee_async("5123", "6789")

        mock_http.put.assert_called_once_with(
            "/tasks/5123",
            json={"data": {"assignee": "6789"}},
        )

    def test_set_assignee_sync_delegates_to_async(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """set_assignee sync wrapper delegates to set_assignee_async."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.put.return_value = {
            "gid": "5123",
            "name": "Test Task",
            "assignee": {"gid": "6789"},
        }

        result = client.set_assignee("5123", "6789")

        assert isinstance(result, Task)
        assert result.gid == "5123"


class TestP1DirectMethodsAddToProject:
    """Tests for P1 Direct Methods: add_to_project_async and add_to_project."""

    async def test_add_to_project_async_returns_updated_task(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """add_to_project_async returns updated Task object."""
        from unittest.mock import AsyncMock, patch

        mock_session = MagicMock()
        mock_session.add_to_project = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {
                "gid": "5123",
                "name": "Test Task",
                "projects": [{"gid": "2456"}],
            }

            result = await tasks_client.add_to_project_async("5123", "2456")

            assert isinstance(result, Task)
            assert result.gid == "5123"
            assert mock_http.get.called

    async def test_add_to_project_async_with_section(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """add_to_project_async with section_gid parameter."""
        from unittest.mock import AsyncMock, patch

        mock_session = MagicMock()
        mock_session.add_to_project = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {
                "gid": "5123",
                "name": "Test Task",
                "projects": [{"gid": "2456"}],
                "section": {"gid": "3789"},
            }

            result = await tasks_client.add_to_project_async(
                "5123", "2456", section_gid="3789"
            )

            assert isinstance(result, Task)
            assert result.gid == "5123"

    def test_add_to_project_sync_delegates_to_async(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """add_to_project sync wrapper delegates to add_to_project_async."""
        from unittest.mock import AsyncMock, patch

        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            client=None,
        )

        mock_session = MagicMock()
        mock_session.add_to_project = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {
                "gid": "5123",
                "name": "Test Task",
                "projects": [{"gid": "2456"}],
            }

            result = client.add_to_project("5123", "2456")

            assert isinstance(result, Task)


class TestP1DirectMethodsRemoveFromProject:
    """Tests for P1 Direct Methods: remove_from_project_async and remove_from_project."""

    async def test_remove_from_project_async_returns_updated_task(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """remove_from_project_async returns updated Task object."""
        from unittest.mock import AsyncMock, patch

        mock_session = MagicMock()
        mock_session.remove_from_project = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {
                "gid": "5123",
                "name": "Test Task",
                "projects": [],
            }

            result = await tasks_client.remove_from_project_async("5123", "2456")

            assert isinstance(result, Task)
            assert result.gid == "5123"
            assert mock_http.get.called

    def test_remove_from_project_sync_delegates_to_async(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """remove_from_project sync wrapper delegates to remove_from_project_async."""
        from unittest.mock import AsyncMock, patch

        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            client=None,
        )

        mock_session = MagicMock()
        mock_session.remove_from_project = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {
                "gid": "5123",
                "name": "Test Task",
                "projects": [],
            }

            result = client.remove_from_project("5123", "2456")

            assert isinstance(result, Task)


class TestP1DirectMethodsSaveSessionError:
    """Tests for P1 Direct Methods: SaveSessionError on failure (Issue 5)."""

    async def test_add_tag_async_raises_save_session_error_on_failure(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """add_tag_async raises SaveSessionError when commit fails."""
        from unittest.mock import AsyncMock, patch
        from autom8_asana.persistence.exceptions import SaveSessionError
        from autom8_asana.persistence.models import (
            SaveResult,
            ActionResult,
            ActionOperation,
            ActionType,
        )
        from autom8_asana.models.common import NameGid

        # Create a failed SaveResult
        task = Task(gid="5123", name="Test Task")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="1999")
        )
        action_result = ActionResult(
            action=action, success=False, error=Exception("Tag not found")
        )
        failed_result = SaveResult(action_results=[action_result])

        mock_session = MagicMock()
        mock_session.add_tag = MagicMock()
        mock_session.commit_async = AsyncMock(return_value=failed_result)

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {"gid": "5123", "name": "Test Task"}

            with pytest.raises(SaveSessionError) as exc_info:
                await tasks_client.add_tag_async("5123", "1999")

            # Verify error has result attached
            assert exc_info.value.result is failed_result
            assert "SaveSession commit failed" in str(exc_info.value)

    async def test_remove_tag_async_raises_save_session_error_on_failure(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """remove_tag_async raises SaveSessionError when commit fails."""
        from unittest.mock import AsyncMock, patch
        from autom8_asana.persistence.exceptions import SaveSessionError
        from autom8_asana.persistence.models import (
            SaveResult,
            ActionResult,
            ActionOperation,
            ActionType,
        )
        from autom8_asana.models.common import NameGid

        task = Task(gid="5123", name="Test Task")
        action = ActionOperation(
            task=task, action=ActionType.REMOVE_TAG, target=NameGid(gid="1456")
        )
        action_result = ActionResult(
            action=action, success=False, error=Exception("Permission denied")
        )
        failed_result = SaveResult(action_results=[action_result])

        mock_session = MagicMock()
        mock_session.remove_tag = MagicMock()
        mock_session.commit_async = AsyncMock(return_value=failed_result)

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {"gid": "5123", "name": "Test Task"}

            with pytest.raises(SaveSessionError):
                await tasks_client.remove_tag_async("5123", "1456")

    async def test_move_to_section_async_raises_save_session_error_on_failure(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """move_to_section_async raises SaveSessionError when commit fails."""
        from unittest.mock import AsyncMock, patch
        from autom8_asana.persistence.exceptions import SaveSessionError
        from autom8_asana.persistence.models import (
            SaveResult,
            ActionResult,
            ActionOperation,
            ActionType,
        )
        from autom8_asana.models.common import NameGid

        task = Task(gid="5123", name="Test Task")
        action = ActionOperation(
            task=task, action=ActionType.MOVE_TO_SECTION, target=NameGid(gid="3789")
        )
        action_result = ActionResult(
            action=action, success=False, error=Exception("Section not found")
        )
        failed_result = SaveResult(action_results=[action_result])

        mock_session = MagicMock()
        mock_session.move_to_section = MagicMock()
        mock_session.commit_async = AsyncMock(return_value=failed_result)

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {"gid": "5123", "name": "Test Task"}

            with pytest.raises(SaveSessionError):
                await tasks_client.move_to_section_async("5123", "3789", "2456")

    async def test_add_to_project_async_raises_save_session_error_on_failure(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """add_to_project_async raises SaveSessionError when commit fails."""
        from unittest.mock import AsyncMock, patch
        from autom8_asana.persistence.exceptions import SaveSessionError
        from autom8_asana.persistence.models import (
            SaveResult,
            ActionResult,
            ActionOperation,
            ActionType,
        )
        from autom8_asana.models.common import NameGid

        task = Task(gid="5123", name="Test Task")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TO_PROJECT, target=NameGid(gid="2456")
        )
        action_result = ActionResult(
            action=action, success=False, error=Exception("Project not found")
        )
        failed_result = SaveResult(action_results=[action_result])

        mock_session = MagicMock()
        mock_session.add_to_project = MagicMock()
        mock_session.commit_async = AsyncMock(return_value=failed_result)

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {"gid": "5123", "name": "Test Task"}

            with pytest.raises(SaveSessionError):
                await tasks_client.add_to_project_async("5123", "2456")

    async def test_remove_from_project_async_raises_save_session_error_on_failure(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """remove_from_project_async raises SaveSessionError when commit fails."""
        from unittest.mock import AsyncMock, patch
        from autom8_asana.persistence.exceptions import SaveSessionError
        from autom8_asana.persistence.models import (
            SaveResult,
            ActionResult,
            ActionOperation,
            ActionType,
        )
        from autom8_asana.models.common import NameGid

        task = Task(gid="5123", name="Test Task")
        action = ActionOperation(
            task=task, action=ActionType.REMOVE_FROM_PROJECT, target=NameGid(gid="2456")
        )
        action_result = ActionResult(
            action=action, success=False, error=Exception("Not in project")
        )
        failed_result = SaveResult(action_results=[action_result])

        mock_session = MagicMock()
        mock_session.remove_from_project = MagicMock()
        mock_session.commit_async = AsyncMock(return_value=failed_result)

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {"gid": "5123", "name": "Test Task"}

            with pytest.raises(SaveSessionError):
                await tasks_client.remove_from_project_async("5123", "2456")


class TestP1DirectMethodsRefreshParameter:
    """Tests for P1 Direct Methods: refresh parameter behavior (Issue 2)."""

    async def test_add_tag_async_default_single_get(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """add_tag_async with default refresh=False makes only one GET call."""
        from unittest.mock import AsyncMock, patch
        from autom8_asana.persistence.models import SaveResult

        mock_session = MagicMock()
        mock_session.add_tag = MagicMock()
        mock_session.commit_async = AsyncMock(return_value=SaveResult())

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {"gid": "5123", "name": "Test Task"}

            result = await tasks_client.add_tag_async("5123", "1456")

            # Should be only 1 GET call (before commit), not 2
            assert mock_http.get.call_count == 1
            assert result.gid == "5123"

    async def test_add_tag_async_refresh_true_double_get(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """add_tag_async with refresh=True makes two GET calls."""
        from unittest.mock import AsyncMock, patch
        from autom8_asana.persistence.models import SaveResult

        mock_session = MagicMock()
        mock_session.add_tag = MagicMock()
        mock_session.commit_async = AsyncMock(return_value=SaveResult())

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {"gid": "5123", "name": "Test Task"}

            result = await tasks_client.add_tag_async("5123", "1456", refresh=True)

            # Should be 2 GET calls (before and after commit)
            assert mock_http.get.call_count == 2
            assert result.gid == "5123"

    async def test_remove_tag_async_refresh_parameter(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """remove_tag_async respects refresh parameter."""
        from unittest.mock import AsyncMock, patch
        from autom8_asana.persistence.models import SaveResult

        mock_session = MagicMock()
        mock_session.remove_tag = MagicMock()
        mock_session.commit_async = AsyncMock(return_value=SaveResult())

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {"gid": "5123", "name": "Test Task"}

            # Default (no refresh)
            await tasks_client.remove_tag_async("5123", "1456")
            assert mock_http.get.call_count == 1

            mock_http.get.reset_mock()

            # With refresh=True
            await tasks_client.remove_tag_async("5123", "1456", refresh=True)
            assert mock_http.get.call_count == 2

    async def test_move_to_section_async_refresh_parameter(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """move_to_section_async respects refresh parameter."""
        from unittest.mock import AsyncMock, patch
        from autom8_asana.persistence.models import SaveResult

        mock_session = MagicMock()
        mock_session.move_to_section = MagicMock()
        mock_session.commit_async = AsyncMock(return_value=SaveResult())

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {"gid": "5123", "name": "Test Task"}

            # Default (no refresh)
            await tasks_client.move_to_section_async("5123", "3789", "2456")
            assert mock_http.get.call_count == 1

            mock_http.get.reset_mock()

            # With refresh=True
            await tasks_client.move_to_section_async(
                "5123", "3789", "2456", refresh=True
            )
            assert mock_http.get.call_count == 2

    async def test_add_to_project_async_refresh_parameter(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """add_to_project_async respects refresh parameter."""
        from unittest.mock import AsyncMock, patch
        from autom8_asana.persistence.models import SaveResult

        mock_session = MagicMock()
        mock_session.add_to_project = MagicMock()
        mock_session.commit_async = AsyncMock(return_value=SaveResult())

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {"gid": "5123", "name": "Test Task"}

            # Default (no refresh)
            await tasks_client.add_to_project_async("5123", "2456")
            assert mock_http.get.call_count == 1

            mock_http.get.reset_mock()

            # With refresh=True
            await tasks_client.add_to_project_async("5123", "2456", refresh=True)
            assert mock_http.get.call_count == 2

    async def test_remove_from_project_async_refresh_parameter(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """remove_from_project_async respects refresh parameter."""
        from unittest.mock import AsyncMock, patch
        from autom8_asana.persistence.models import SaveResult

        mock_session = MagicMock()
        mock_session.remove_from_project = MagicMock()
        mock_session.commit_async = AsyncMock(return_value=SaveResult())

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {"gid": "5123", "name": "Test Task"}

            # Default (no refresh)
            await tasks_client.remove_from_project_async("5123", "2456")
            assert mock_http.get.call_count == 1

            mock_http.get.reset_mock()

            # With refresh=True
            await tasks_client.remove_from_project_async("5123", "2456", refresh=True)
            assert mock_http.get.call_count == 2


class TestP1DirectMethodsIntegration:
    """Integration tests for P1 Direct Methods."""

    async def test_all_direct_methods_exist_on_client(
        self, tasks_client: TasksClient
    ) -> None:
        """All 12 P1 direct methods exist on TasksClient."""
        # Async methods
        assert hasattr(tasks_client, "add_tag_async")
        assert hasattr(tasks_client, "remove_tag_async")
        assert hasattr(tasks_client, "move_to_section_async")
        assert hasattr(tasks_client, "set_assignee_async")
        assert hasattr(tasks_client, "add_to_project_async")
        assert hasattr(tasks_client, "remove_from_project_async")

        # Sync wrappers
        assert hasattr(tasks_client, "add_tag")
        assert hasattr(tasks_client, "remove_tag")
        assert hasattr(tasks_client, "move_to_section")
        assert hasattr(tasks_client, "set_assignee")
        assert hasattr(tasks_client, "add_to_project")
        assert hasattr(tasks_client, "remove_from_project")

    async def test_all_async_methods_are_callable(
        self, tasks_client: TasksClient
    ) -> None:
        """All async methods are callable."""
        assert callable(tasks_client.add_tag_async)
        assert callable(tasks_client.remove_tag_async)
        assert callable(tasks_client.move_to_section_async)
        assert callable(tasks_client.set_assignee_async)
        assert callable(tasks_client.add_to_project_async)
        assert callable(tasks_client.remove_from_project_async)

    def test_all_sync_methods_are_callable(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """All sync methods are callable."""
        client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        assert callable(client.add_tag)
        assert callable(client.remove_tag)
        assert callable(client.move_to_section)
        assert callable(client.set_assignee)
        assert callable(client.add_to_project)
        assert callable(client.remove_from_project)

    async def test_all_async_methods_have_correct_return_type(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """All async methods return Task objects."""
        from unittest.mock import AsyncMock, patch

        mock_session = MagicMock()
        mock_session.add_tag = MagicMock()
        mock_session.remove_tag = MagicMock()
        mock_session.move_to_section = MagicMock()
        mock_session.add_to_project = MagicMock()
        mock_session.remove_from_project = MagicMock()
        mock_session.commit_async = AsyncMock()

        with patch("autom8_asana.clients.tasks.SaveSession") as mock_save_session_class:
            mock_save_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_save_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_http.get.return_value = {"gid": "5123", "name": "Test Task"}
            mock_http.put.return_value = {"gid": "5123", "name": "Test Task"}

            # Test add_tag
            result = await tasks_client.add_tag_async("5123", "1456")
            assert isinstance(result, Task)

            # Test remove_tag
            result = await tasks_client.remove_tag_async("5123", "1456")
            assert isinstance(result, Task)

            # Test move_to_section
            result = await tasks_client.move_to_section_async("5123", "3789", "2456")
            assert isinstance(result, Task)

            # Test set_assignee
            result = await tasks_client.set_assignee_async("5123", "6789")
            assert isinstance(result, Task)

            # Test add_to_project
            result = await tasks_client.add_to_project_async("5123", "2456")
            assert isinstance(result, Task)

            # Test remove_from_project
            result = await tasks_client.remove_from_project_async("5123", "2456")
            assert isinstance(result, Task)
