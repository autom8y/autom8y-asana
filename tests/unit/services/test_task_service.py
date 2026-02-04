"""Tests for TaskService -- task CRUD with mock dependencies.

Verifies:
- All CRUD operations call correct SDK methods
- MutationEvent construction for each operation type
- fire_and_forget called with correct event parameters
- InvalidParameterError for validation failures
- No HTTP fixtures needed (pure unit tests with mocks)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.cache.models.mutation_event import (
    EntityKind,
    MutationType,
)
from autom8_asana.services.errors import InvalidParameterError
from autom8_asana.services.task_service import (
    CreateTaskParams,
    ServiceListResult,
    TaskService,
    UpdateTaskParams,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_invalidator() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_client() -> AsyncMock:
    client = AsyncMock()
    client._http = AsyncMock()
    client.tasks = AsyncMock()
    return client


@pytest.fixture()
def service(mock_invalidator: MagicMock) -> TaskService:
    return TaskService(invalidator=mock_invalidator)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _last_event(mock_invalidator: MagicMock):
    """Get the last MutationEvent passed to fire_and_forget."""
    mock_invalidator.fire_and_forget.assert_called()
    return mock_invalidator.fire_and_forget.call_args[0][0]


# ---------------------------------------------------------------------------
# Tests: list_tasks
# ---------------------------------------------------------------------------


class TestListTasks:
    @pytest.mark.asyncio()
    async def test_list_by_project(
        self, service: TaskService, mock_client: AsyncMock
    ) -> None:
        mock_client._http.get_paginated.return_value = (
            [{"gid": "1"}, {"gid": "2"}],
            "next-cursor",
        )

        result = await service.list_tasks(mock_client, project="proj-1")

        assert isinstance(result, ServiceListResult)
        assert len(result.data) == 2
        assert result.has_more is True
        assert result.next_offset == "next-cursor"
        mock_client._http.get_paginated.assert_called_once_with(
            "/projects/proj-1/tasks", params={"limit": 100}
        )

    @pytest.mark.asyncio()
    async def test_list_by_section(
        self, service: TaskService, mock_client: AsyncMock
    ) -> None:
        mock_client._http.get_paginated.return_value = ([], None)

        result = await service.list_tasks(mock_client, section="sec-1")

        assert result.has_more is False
        assert result.next_offset is None
        mock_client._http.get_paginated.assert_called_once_with(
            "/sections/sec-1/tasks", params={"limit": 100}
        )

    @pytest.mark.asyncio()
    async def test_neither_project_nor_section_raises(
        self, service: TaskService, mock_client: AsyncMock
    ) -> None:
        with pytest.raises(InvalidParameterError, match="project.*section"):
            await service.list_tasks(mock_client)

    @pytest.mark.asyncio()
    async def test_both_project_and_section_raises(
        self, service: TaskService, mock_client: AsyncMock
    ) -> None:
        with pytest.raises(InvalidParameterError, match="Only one"):
            await service.list_tasks(
                mock_client, project="p", section="s"
            )

    @pytest.mark.asyncio()
    async def test_limit_and_offset(
        self, service: TaskService, mock_client: AsyncMock
    ) -> None:
        mock_client._http.get_paginated.return_value = ([], None)

        await service.list_tasks(
            mock_client, project="p", limit=50, offset="cursor"
        )

        mock_client._http.get_paginated.assert_called_once_with(
            "/projects/p/tasks", params={"limit": 50, "offset": "cursor"}
        )


# ---------------------------------------------------------------------------
# Tests: get_task
# ---------------------------------------------------------------------------


class TestGetTask:
    @pytest.mark.asyncio()
    async def test_get_task(
        self, service: TaskService, mock_client: AsyncMock
    ) -> None:
        mock_client.tasks.get_async.return_value = {"gid": "123", "name": "Test"}

        result = await service.get_task(mock_client, "123")

        assert result["gid"] == "123"
        mock_client.tasks.get_async.assert_called_once_with(
            "123", opt_fields=None, raw=True
        )

    @pytest.mark.asyncio()
    async def test_get_task_with_opt_fields(
        self, service: TaskService, mock_client: AsyncMock
    ) -> None:
        mock_client.tasks.get_async.return_value = {"gid": "123"}

        await service.get_task(mock_client, "123", opt_fields=["name", "notes"])

        mock_client.tasks.get_async.assert_called_once_with(
            "123", opt_fields=["name", "notes"], raw=True
        )


# ---------------------------------------------------------------------------
# Tests: create_task (T1)
# ---------------------------------------------------------------------------


class TestCreateTask:
    @pytest.mark.asyncio()
    async def test_create_fires_invalidation(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_client.tasks.create_async.return_value = {
            "gid": "123",
            "memberships": [{"project": {"gid": "proj-1"}}],
        }

        result = await service.create_task(
            mock_client,
            CreateTaskParams(name="Test", projects=["proj-1"]),
        )

        assert result["gid"] == "123"
        event = _last_event(mock_invalidator)
        assert event.entity_kind == EntityKind.TASK
        assert event.entity_gid == "123"
        assert event.mutation_type == MutationType.CREATE
        assert "proj-1" in event.project_gids

    @pytest.mark.asyncio()
    async def test_create_without_projects_or_workspace_raises(
        self, service: TaskService, mock_client: AsyncMock
    ) -> None:
        with pytest.raises(InvalidParameterError, match="projects.*workspace"):
            await service.create_task(
                mock_client, CreateTaskParams(name="Test")
            )

    @pytest.mark.asyncio()
    async def test_create_with_optional_fields(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_client.tasks.create_async.return_value = {"gid": "456"}

        await service.create_task(
            mock_client,
            CreateTaskParams(
                name="Full",
                projects=["p1"],
                notes="note",
                assignee="user-1",
                due_on="2026-03-01",
            ),
        )

        call_kwargs = mock_client.tasks.create_async.call_args
        assert call_kwargs.kwargs.get("notes") == "note"
        assert call_kwargs.kwargs.get("assignee") == "user-1"
        assert call_kwargs.kwargs.get("due_on") == "2026-03-01"

    @pytest.mark.asyncio()
    async def test_create_with_workspace(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_client.tasks.create_async.return_value = {"gid": "789"}

        await service.create_task(
            mock_client,
            CreateTaskParams(name="WS Task", workspace="ws-1"),
        )

        call_kwargs = mock_client.tasks.create_async.call_args
        assert call_kwargs.kwargs.get("workspace") == "ws-1"


# ---------------------------------------------------------------------------
# Tests: update_task (T2)
# ---------------------------------------------------------------------------


class TestUpdateTask:
    @pytest.mark.asyncio()
    async def test_update_fires_invalidation(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_client.tasks.update_async.return_value = {
            "gid": "123",
            "memberships": [{"project": {"gid": "proj-1"}}],
        }

        result = await service.update_task(
            mock_client, "123", UpdateTaskParams(name="Updated")
        )

        assert result["gid"] == "123"
        event = _last_event(mock_invalidator)
        assert event.mutation_type == MutationType.UPDATE
        assert event.entity_gid == "123"

    @pytest.mark.asyncio()
    async def test_update_no_fields_raises(
        self, service: TaskService, mock_client: AsyncMock
    ) -> None:
        with pytest.raises(InvalidParameterError, match="At least one field"):
            await service.update_task(
                mock_client, "123", UpdateTaskParams()
            )


# ---------------------------------------------------------------------------
# Tests: delete_task (T3)
# ---------------------------------------------------------------------------


class TestDeleteTask:
    @pytest.mark.asyncio()
    async def test_delete_fires_invalidation(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        await service.delete_task(mock_client, "123")

        mock_client.tasks.delete_async.assert_called_once_with("123")
        event = _last_event(mock_invalidator)
        assert event.mutation_type == MutationType.DELETE
        assert event.entity_gid == "123"
        assert event.project_gids == []


# ---------------------------------------------------------------------------
# Tests: duplicate_task (T4)
# ---------------------------------------------------------------------------


class TestDuplicateTask:
    @pytest.mark.asyncio()
    async def test_duplicate_fires_create_event(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_client.tasks.duplicate_async.return_value = {
            "gid": "456",
            "projects": [{"gid": "proj-1"}],
        }

        result = await service.duplicate_task(mock_client, "123", "Copy")

        assert result["gid"] == "456"
        event = _last_event(mock_invalidator)
        assert event.mutation_type == MutationType.CREATE
        assert event.entity_gid == "456"
        assert "proj-1" in event.project_gids


# ---------------------------------------------------------------------------
# Tests: Tag operations (T5, T6)
# ---------------------------------------------------------------------------


class TestTagOperations:
    @pytest.mark.asyncio()
    async def test_add_tag(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_task = MagicMock()
        mock_task.model_dump.return_value = {"gid": "123"}
        mock_client.tasks.add_tag_async.return_value = mock_task

        result = await service.add_tag(mock_client, "123", "tag-1")

        assert result["gid"] == "123"
        event = _last_event(mock_invalidator)
        assert event.mutation_type == MutationType.UPDATE

    @pytest.mark.asyncio()
    async def test_remove_tag(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_task = MagicMock()
        mock_task.model_dump.return_value = {"gid": "123"}
        mock_client.tasks.remove_tag_async.return_value = mock_task

        result = await service.remove_tag(mock_client, "123", "tag-1")

        assert result["gid"] == "123"
        event = _last_event(mock_invalidator)
        assert event.mutation_type == MutationType.UPDATE


# ---------------------------------------------------------------------------
# Tests: Membership operations (T7, T8, T9, T10)
# ---------------------------------------------------------------------------


class TestMembershipOperations:
    @pytest.mark.asyncio()
    async def test_move_to_section(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_task = MagicMock()
        mock_task.model_dump.return_value = {"gid": "123"}
        mock_client.tasks.move_to_section_async.return_value = mock_task

        result = await service.move_to_section(
            mock_client, "123", "sec-1", "proj-1"
        )

        assert result["gid"] == "123"
        event = _last_event(mock_invalidator)
        assert event.mutation_type == MutationType.MOVE
        assert event.section_gid == "sec-1"
        # Falls back to provided project_gid since model_dump has no memberships
        assert "proj-1" in event.project_gids

    @pytest.mark.asyncio()
    async def test_set_assignee(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_task = MagicMock()
        mock_task.model_dump.return_value = {"gid": "123"}
        mock_client.tasks.set_assignee_async.return_value = mock_task

        result = await service.set_assignee(mock_client, "123", "user-1")

        assert result["gid"] == "123"
        event = _last_event(mock_invalidator)
        assert event.mutation_type == MutationType.UPDATE

    @pytest.mark.asyncio()
    async def test_unset_assignee(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_client.tasks.update_async.return_value = {"gid": "123"}

        result = await service.set_assignee(mock_client, "123", None)

        assert result["gid"] == "123"
        mock_client.tasks.update_async.assert_called_once_with(
            "123", raw=True, assignee=None
        )

    @pytest.mark.asyncio()
    async def test_add_to_project(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_task = MagicMock()
        mock_task.model_dump.return_value = {"gid": "123"}
        mock_client.tasks.add_to_project_async.return_value = mock_task

        result = await service.add_to_project(mock_client, "123", "proj-2")

        assert result["gid"] == "123"
        event = _last_event(mock_invalidator)
        assert event.mutation_type == MutationType.ADD_MEMBER
        assert event.project_gids == ["proj-2"]

    @pytest.mark.asyncio()
    async def test_remove_from_project(
        self,
        service: TaskService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_task = MagicMock()
        mock_task.model_dump.return_value = {"gid": "123"}
        mock_client.tasks.remove_from_project_async.return_value = mock_task

        result = await service.remove_from_project(
            mock_client, "123", "proj-2"
        )

        assert result["gid"] == "123"
        event = _last_event(mock_invalidator)
        assert event.mutation_type == MutationType.REMOVE_MEMBER
        assert event.project_gids == ["proj-2"]


# ---------------------------------------------------------------------------
# Tests: Subtasks / Dependents
# ---------------------------------------------------------------------------


class TestSubtasksAndDependents:
    @pytest.mark.asyncio()
    async def test_list_subtasks(
        self, service: TaskService, mock_client: AsyncMock
    ) -> None:
        mock_client._http.get_paginated.return_value = (
            [{"gid": "sub-1"}],
            None,
        )

        result = await service.list_subtasks(mock_client, "123")

        assert len(result.data) == 1
        assert result.has_more is False
        mock_client._http.get_paginated.assert_called_once_with(
            "/tasks/123/subtasks", params={"limit": 100}
        )

    @pytest.mark.asyncio()
    async def test_list_dependents(
        self, service: TaskService, mock_client: AsyncMock
    ) -> None:
        mock_client._http.get_paginated.return_value = (
            [{"gid": "dep-1"}],
            "next",
        )

        result = await service.list_dependents(
            mock_client, "123", limit=25, offset="prev"
        )

        assert result.has_more is True
        mock_client._http.get_paginated.assert_called_once_with(
            "/tasks/123/dependents",
            params={"limit": 25, "offset": "prev"},
        )


# ---------------------------------------------------------------------------
# Tests: No HTTP coupling
# ---------------------------------------------------------------------------


class TestNoHTTPCoupling:
    def test_no_http_exception_in_module(self) -> None:
        import autom8_asana.services.task_service as mod

        source = mod.__file__
        assert source is not None
        with open(source) as f:
            content = f.read()
        assert "HTTPException" not in content
