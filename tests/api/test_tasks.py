"""Tests for tasks endpoints.

Tests cover:
- GET /api/v1/tasks?project={gid} - list tasks by project
- GET /api/v1/tasks?section={gid} - list tasks by section
- GET /api/v1/tasks/{gid} - get task by GID
- POST /api/v1/tasks - create task
- PUT /api/v1/tasks/{gid} - update task
- DELETE /api/v1/tasks/{gid} - delete task
- GET /api/v1/tasks/{gid}/subtasks - list subtasks
- POST /api/v1/tasks/{gid}/duplicate - duplicate task
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests.api.conftest import (
    TEST_PROJECT_GID,
    TEST_SECTION_GID,
    TEST_TAG_GID,
    TEST_TASK_GID,
    TEST_WORKSPACE_GID,
)


class TestListTasks:
    """Tests for GET /api/v1/tasks endpoint."""

    def test_list_tasks_requires_project_or_section(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """List tasks without project or section returns 400."""
        client, _ = authed_client

        response = client.get(
            "/api/v1/tasks",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 400
        assert "project" in response.json()["detail"].lower()

    def test_list_tasks_rejects_both_project_and_section(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """List tasks with both project and section returns 400."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/tasks?project={TEST_PROJECT_GID}&section={TEST_SECTION_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 400
        assert "only one" in response.json()["detail"].lower()

    def test_list_tasks_by_project_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully lists tasks by project."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = (
            [
                {"gid": "task1", "name": "Task One"},
                {"gid": "task2", "name": "Task Two"},
            ],
            None,
        )

        response = client.get(
            f"/api/v1/tasks?project={TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["data"], list)
        assert len(data["data"]) == 2

        # Verify correct endpoint was called
        call_args = mock_sdk._http.get_paginated.call_args
        assert f"/projects/{TEST_PROJECT_GID}/tasks" in call_args[0][0]

    def test_list_tasks_by_section_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully lists tasks by section."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = (
            [{"gid": "task1", "name": "Task One"}],
            None,
        )

        response = client.get(
            f"/api/v1/tasks?section={TEST_SECTION_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

        # Verify correct endpoint was called
        call_args = mock_sdk._http.get_paginated.call_args
        assert f"/sections/{TEST_SECTION_GID}/tasks" in call_args[0][0]

    def test_list_tasks_with_pagination(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """List tasks returns pagination metadata when more pages exist."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = (
            [{"gid": "task1", "name": "Task One"}],
            "next_cursor",
        )

        response = client.get(
            f"/api/v1/tasks?project={TEST_PROJECT_GID}&limit=1",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        pagination = response.json()["meta"]["pagination"]

        assert pagination["has_more"] is True
        assert pagination["next_offset"] == "next_cursor"


class TestGetTask:
    """Tests for GET /api/v1/tasks/{gid} endpoint."""

    def test_get_task_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns task by GID."""
        client, mock_sdk = authed_client

        mock_sdk.tasks.get_async.return_value = {
            "gid": TEST_TASK_GID,
            "name": "Test Task",
            "notes": "Task description",
            "completed": False,
        }

        response = client.get(
            f"/api/v1/tasks/{TEST_TASK_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["gid"] == TEST_TASK_GID
        assert data["data"]["name"] == "Test Task"

        mock_sdk.tasks.get_async.assert_called_once_with(
            TEST_TASK_GID, opt_fields=None, raw=True
        )

    def test_get_task_with_opt_fields(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Get task with specific fields using opt_fields parameter."""
        client, mock_sdk = authed_client

        mock_sdk.tasks.get_async.return_value = {
            "gid": TEST_TASK_GID,
            "name": "Test Task",
            "due_on": "2024-12-31",
        }

        response = client.get(
            f"/api/v1/tasks/{TEST_TASK_GID}?opt_fields=name,due_on",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

        # Verify opt_fields was parsed and passed
        mock_sdk.tasks.get_async.assert_called_once_with(
            TEST_TASK_GID, opt_fields=["name", "due_on"], raw=True
        )


class TestCreateTask:
    """Tests for POST /api/v1/tasks endpoint."""

    def test_create_task_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully creates a new task."""
        client, mock_sdk = authed_client

        mock_sdk.tasks.create_async.return_value = {
            "gid": "new_task_gid",
            "name": "New Task",
        }

        response = client.post(
            "/api/v1/tasks",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={
                "name": "New Task",
                "projects": [TEST_PROJECT_GID],
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["data"]["name"] == "New Task"
        mock_sdk.tasks.create_async.assert_called_once()

    def test_create_task_requires_project_or_workspace(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Create task without projects or workspace returns 400."""
        client, _ = authed_client

        response = client.post(
            "/api/v1/tasks",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"name": "New Task"},
        )

        assert response.status_code == 400
        assert "projects" in response.json()["detail"].lower()

    def test_create_task_with_workspace(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Create task with workspace instead of projects."""
        client, mock_sdk = authed_client

        mock_sdk.tasks.create_async.return_value = {
            "gid": "new_task_gid",
            "name": "New Task",
        }

        response = client.post(
            "/api/v1/tasks",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={
                "name": "New Task",
                "workspace": TEST_WORKSPACE_GID,
            },
        )

        assert response.status_code == 201

    def test_create_task_with_all_fields(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Create task with all optional fields."""
        client, mock_sdk = authed_client

        mock_sdk.tasks.create_async.return_value = {
            "gid": "new_task_gid",
            "name": "Full Task",
        }

        response = client.post(
            "/api/v1/tasks",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={
                "name": "Full Task",
                "projects": [TEST_PROJECT_GID],
                "notes": "Task notes",
                "assignee": "user_gid",
                "due_on": "2024-12-31",
            },
        )

        assert response.status_code == 201

        # Verify all fields were passed
        call_kwargs = mock_sdk.tasks.create_async.call_args[1]
        assert call_kwargs["notes"] == "Task notes"
        assert call_kwargs["assignee"] == "user_gid"
        assert call_kwargs["due_on"] == "2024-12-31"

    def test_create_task_name_required(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Create task without name returns 422."""
        client, _ = authed_client

        response = client.post(
            "/api/v1/tasks",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"projects": [TEST_PROJECT_GID]},
        )

        assert response.status_code == 422


class TestUpdateTask:
    """Tests for PUT /api/v1/tasks/{gid} endpoint."""

    def test_update_task_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully updates a task."""
        client, mock_sdk = authed_client

        mock_sdk.tasks.update_async.return_value = {
            "gid": TEST_TASK_GID,
            "name": "Updated Task",
            "completed": True,
        }

        response = client.put(
            f"/api/v1/tasks/{TEST_TASK_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"name": "Updated Task", "completed": True},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["name"] == "Updated Task"
        assert data["data"]["completed"] is True

    def test_update_task_requires_at_least_one_field(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Update task without any fields returns 400."""
        client, _ = authed_client

        response = client.put(
            f"/api/v1/tasks/{TEST_TASK_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={},
        )

        assert response.status_code == 400
        assert "at least one field" in response.json()["detail"].lower()

    def test_update_task_partial(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Update task with only some fields."""
        client, mock_sdk = authed_client

        mock_sdk.tasks.update_async.return_value = {
            "gid": TEST_TASK_GID,
            "notes": "New notes",
        }

        response = client.put(
            f"/api/v1/tasks/{TEST_TASK_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"notes": "New notes"},
        )

        assert response.status_code == 200

        # Verify only notes was passed
        call_kwargs = mock_sdk.tasks.update_async.call_args[1]
        assert call_kwargs["notes"] == "New notes"
        assert "name" not in call_kwargs
        assert "completed" not in call_kwargs


class TestDeleteTask:
    """Tests for DELETE /api/v1/tasks/{gid} endpoint."""

    def test_delete_task_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully deletes a task."""
        client, mock_sdk = authed_client

        response = client.delete(
            f"/api/v1/tasks/{TEST_TASK_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 204
        mock_sdk.tasks.delete_async.assert_called_once_with(TEST_TASK_GID)


class TestListSubtasks:
    """Tests for GET /api/v1/tasks/{gid}/subtasks endpoint."""

    def test_list_subtasks_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully lists subtasks of a task."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = (
            [
                {"gid": "subtask1", "name": "Subtask One"},
                {"gid": "subtask2", "name": "Subtask Two"},
            ],
            None,
        )

        response = client.get(
            f"/api/v1/tasks/{TEST_TASK_GID}/subtasks",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["data"], list)
        assert len(data["data"]) == 2

        # Verify correct endpoint was called
        call_args = mock_sdk._http.get_paginated.call_args
        assert f"/tasks/{TEST_TASK_GID}/subtasks" in call_args[0][0]


class TestDuplicateTask:
    """Tests for POST /api/v1/tasks/{gid}/duplicate endpoint."""

    def test_duplicate_task_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully duplicates a task."""
        client, mock_sdk = authed_client

        mock_sdk.tasks.duplicate_async.return_value = {
            "gid": "duplicated_task_gid",
            "name": "Copy of Task",
        }

        response = client.post(
            f"/api/v1/tasks/{TEST_TASK_GID}/duplicate",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"name": "Copy of Task"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["data"]["name"] == "Copy of Task"
        mock_sdk.tasks.duplicate_async.assert_called_once_with(
            TEST_TASK_GID, name="Copy of Task", raw=True
        )

    def test_duplicate_task_name_required(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Duplicate task without name returns 422."""
        client, _ = authed_client

        response = client.post(
            f"/api/v1/tasks/{TEST_TASK_GID}/duplicate",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={},
        )

        assert response.status_code == 422


class TestTaskTags:
    """Tests for task tag operations."""

    def test_add_tag_success(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """Successfully adds a tag to a task."""
        client, mock_sdk = authed_client

        response = client.post(
            f"/api/v1/tasks/{TEST_TASK_GID}/tags",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"tag_gid": TEST_TAG_GID},
        )

        assert response.status_code == 200
        mock_sdk.tasks.add_tag_async.assert_called_once_with(
            TEST_TASK_GID, TEST_TAG_GID
        )

    def test_remove_tag_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully removes a tag from a task."""
        client, mock_sdk = authed_client

        response = client.delete(
            f"/api/v1/tasks/{TEST_TASK_GID}/tags/{TEST_TAG_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        mock_sdk.tasks.remove_tag_async.assert_called_once_with(
            TEST_TASK_GID, TEST_TAG_GID
        )


class TestTaskMembership:
    """Tests for task project/section membership operations."""

    def test_move_to_section_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully moves a task to a section."""
        client, mock_sdk = authed_client

        response = client.post(
            f"/api/v1/tasks/{TEST_TASK_GID}/section",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={
                "section_gid": TEST_SECTION_GID,
                "project_gid": TEST_PROJECT_GID,
            },
        )

        assert response.status_code == 200
        mock_sdk.tasks.move_to_section_async.assert_called_once_with(
            TEST_TASK_GID, TEST_SECTION_GID, TEST_PROJECT_GID
        )

    def test_add_to_project_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully adds a task to a project."""
        client, mock_sdk = authed_client

        response = client.post(
            f"/api/v1/tasks/{TEST_TASK_GID}/projects",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"project_gid": TEST_PROJECT_GID},
        )

        assert response.status_code == 200
        mock_sdk.tasks.add_to_project_async.assert_called_once_with(
            TEST_TASK_GID, TEST_PROJECT_GID
        )

    def test_remove_from_project_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully removes a task from a project."""
        client, mock_sdk = authed_client

        response = client.delete(
            f"/api/v1/tasks/{TEST_TASK_GID}/projects/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        mock_sdk.tasks.remove_from_project_async.assert_called_once_with(
            TEST_TASK_GID, TEST_PROJECT_GID
        )
