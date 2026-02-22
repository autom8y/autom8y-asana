"""Tests for TasksClient."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autom8_asana.clients.tasks import TasksClient
from autom8_asana.exceptions import SyncInAsyncContextError
from autom8_asana.models import PageIterator, Task

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig


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
        client=None,
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

        # Check that operations were logged (SDK MockLogger: .entries with .level/.event)
        # With @async_method, canonical method name is the base name (get, create, etc.)
        debug_events = [e.event for e in logger.get_events("debug")]
        assert any("TasksClient.get(" in ev for ev in debug_events)
        assert any("TasksClient.create(" in ev for ev in debug_events)
        assert any("TasksClient.update(" in ev for ev in debug_events)
        assert any("TasksClient.delete(" in ev for ev in debug_events)


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

        # Verify opt_fields was passed in params (parent.gid added automatically)
        mock_http.get_paginated.assert_called_once()
        call_args = mock_http.get_paginated.call_args
        opt_fields = set(call_args[1]["params"]["opt_fields"].split(","))
        assert {"name", "notes"}.issubset(opt_fields)

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

        # Verify operation was logged (SDK MockLogger: .entries with .level/.event)
        debug_events = [e.event for e in logger.get_events("debug")]
        assert any("subtasks_async" in ev for ev in debug_events)


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
