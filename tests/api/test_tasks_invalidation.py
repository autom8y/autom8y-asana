"""Tests for task route handler cache invalidation wiring.

Per TDD-CACHE-INVALIDATION-001 Test Strategy: Verify that each wired
task endpoint calls fire_and_forget() with the correct MutationEvent
after successful mutation.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from autom8_asana.cache.integration.mutation_invalidator import MutationInvalidator
from autom8_asana.cache.models.mutation_event import EntityKind, MutationType
from tests.api.conftest import (
    TEST_PROJECT_GID,
    TEST_SECTION_GID,
    TEST_TAG_GID,
    TEST_TASK_GID,
)

AUTH_HEADER = {"Authorization": "Bearer test_pat_token_12345"}


@pytest.fixture
def mock_invalidator() -> MagicMock:
    """Create a mock MutationInvalidator."""
    inv = MagicMock(spec=MutationInvalidator)
    inv.fire_and_forget = MagicMock()
    return inv


@pytest.fixture
def authed_client_with_invalidator(
    app, mock_asana_client: MagicMock, mock_invalidator: MagicMock
) -> Generator[tuple[TestClient, MagicMock, MagicMock], None, None]:
    """Test client with both AsanaClient and MutationInvalidator mocked."""
    from autom8_asana.api.dependencies import (
        get_asana_client_from_context,
        get_mutation_invalidator,
    )

    async def mock_get_client() -> AsyncGenerator[MagicMock, None]:
        yield mock_asana_client

    app.dependency_overrides[get_asana_client_from_context] = mock_get_client
    app.dependency_overrides[get_mutation_invalidator] = lambda: mock_invalidator

    try:
        with TestClient(app) as test_client:
            yield test_client, mock_asana_client, mock_invalidator
    finally:
        app.dependency_overrides.clear()


class TestTaskCreateInvalidation:
    """T1: POST /tasks triggers CREATE invalidation."""

    def test_create_task_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Create task fires invalidation with CREATE type and project GIDs."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        mock_sdk.tasks.create_async.return_value = {
            "gid": "new_task_1",
            "name": "New Task",
            "projects": [{"gid": TEST_PROJECT_GID, "name": "P1"}],
        }

        response = client.post(
            "/api/v1/tasks",
            json={"name": "New Task", "projects": [TEST_PROJECT_GID]},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 201
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.entity_kind == EntityKind.TASK
        assert event.entity_gid == "new_task_1"
        assert event.mutation_type == MutationType.CREATE
        assert TEST_PROJECT_GID in event.project_gids


class TestTaskUpdateInvalidation:
    """T2: PUT /tasks/{gid} triggers UPDATE invalidation."""

    def test_update_task_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Update task fires invalidation with UPDATE type."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        mock_sdk.tasks.update_async.return_value = {
            "gid": TEST_TASK_GID,
            "name": "Updated Task",
            "projects": [{"gid": TEST_PROJECT_GID}],
        }

        response = client.put(
            f"/api/v1/tasks/{TEST_TASK_GID}",
            json={"name": "Updated Task"},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 200
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.entity_kind == EntityKind.TASK
        assert event.entity_gid == TEST_TASK_GID
        assert event.mutation_type == MutationType.UPDATE
        assert event.project_gids == [TEST_PROJECT_GID]


class TestTaskDeleteInvalidation:
    """T3: DELETE /tasks/{gid} triggers DELETE invalidation."""

    def test_delete_task_fires_invalidation_without_project_gids(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Delete task fires invalidation with no project GIDs (204 response)."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        mock_sdk.tasks.delete_async.return_value = None

        response = client.delete(
            f"/api/v1/tasks/{TEST_TASK_GID}",
            headers=AUTH_HEADER,
        )

        assert response.status_code == 204
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.entity_kind == EntityKind.TASK
        assert event.entity_gid == TEST_TASK_GID
        assert event.mutation_type == MutationType.DELETE
        assert event.project_gids == []


class TestDuplicateTaskInvalidation:
    """T4: POST /tasks/{gid}/duplicate triggers CREATE invalidation."""

    def test_duplicate_task_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Duplicate task fires invalidation for new task with CREATE type."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        mock_sdk.tasks.duplicate_async.return_value = {
            "gid": "dup_task_1",
            "name": "Copy of Task",
            "projects": [{"gid": TEST_PROJECT_GID}],
        }

        response = client.post(
            f"/api/v1/tasks/{TEST_TASK_GID}/duplicate",
            json={"name": "Copy of Task"},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 201
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.entity_kind == EntityKind.TASK
        assert event.entity_gid == "dup_task_1"
        assert event.mutation_type == MutationType.CREATE


class TestAddTagInvalidation:
    """T5: POST /tasks/{gid}/tags triggers UPDATE invalidation."""

    def test_add_tag_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Add tag fires invalidation with UPDATE type."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        task_model = MagicMock()
        task_model.model_dump.return_value = {
            "gid": TEST_TASK_GID,
            "name": "Task",
            "projects": [{"gid": TEST_PROJECT_GID}],
        }
        mock_sdk.tasks.add_tag_async.return_value = task_model

        response = client.post(
            f"/api/v1/tasks/{TEST_TASK_GID}/tags",
            json={"tag_gid": TEST_TAG_GID},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 200
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.entity_kind == EntityKind.TASK
        assert event.entity_gid == TEST_TASK_GID
        assert event.mutation_type == MutationType.UPDATE


class TestRemoveTagInvalidation:
    """T6: DELETE /tasks/{gid}/tags/{tag_gid} triggers UPDATE invalidation."""

    def test_remove_tag_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Remove tag fires invalidation with UPDATE type."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        task_model = MagicMock()
        task_model.model_dump.return_value = {
            "gid": TEST_TASK_GID,
            "name": "Task",
        }
        mock_sdk.tasks.remove_tag_async.return_value = task_model

        response = client.delete(
            f"/api/v1/tasks/{TEST_TASK_GID}/tags/{TEST_TAG_GID}",
            headers=AUTH_HEADER,
        )

        assert response.status_code == 200
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.mutation_type == MutationType.UPDATE


class TestMoveToSectionInvalidation:
    """T7: POST /tasks/{gid}/section triggers MOVE invalidation."""

    def test_move_to_section_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Move to section fires invalidation with MOVE type and section context."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        task_model = MagicMock()
        task_model.model_dump.return_value = {
            "gid": TEST_TASK_GID,
            "name": "Task",
            "projects": [{"gid": TEST_PROJECT_GID}],
        }
        mock_sdk.tasks.move_to_section_async.return_value = task_model

        response = client.post(
            f"/api/v1/tasks/{TEST_TASK_GID}/section",
            json={
                "section_gid": TEST_SECTION_GID,
                "project_gid": TEST_PROJECT_GID,
            },
            headers=AUTH_HEADER,
        )

        assert response.status_code == 200
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.entity_kind == EntityKind.TASK
        assert event.entity_gid == TEST_TASK_GID
        assert event.mutation_type == MutationType.MOVE
        assert event.section_gid == TEST_SECTION_GID
        assert TEST_PROJECT_GID in event.project_gids


class TestSetAssigneeInvalidation:
    """T8: PUT /tasks/{gid}/assignee triggers UPDATE invalidation."""

    def test_set_assignee_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Set assignee fires invalidation with UPDATE type."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        task_model = MagicMock()
        task_model.model_dump.return_value = {
            "gid": TEST_TASK_GID,
            "name": "Task",
            "projects": [{"gid": TEST_PROJECT_GID}],
        }
        mock_sdk.tasks.set_assignee_async.return_value = task_model

        response = client.put(
            f"/api/v1/tasks/{TEST_TASK_GID}/assignee",
            json={"assignee_gid": "user123"},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 200
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.mutation_type == MutationType.UPDATE

    def test_clear_assignee_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Clear assignee (null) fires invalidation with UPDATE type."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        mock_sdk.tasks.update_async.return_value = {
            "gid": TEST_TASK_GID,
            "name": "Task",
        }

        response = client.put(
            f"/api/v1/tasks/{TEST_TASK_GID}/assignee",
            json={"assignee_gid": None},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 200
        mock_inv.fire_and_forget.assert_called_once()


class TestAddToProjectInvalidation:
    """T9: POST /tasks/{gid}/projects triggers ADD_MEMBER invalidation."""

    def test_add_to_project_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Add to project fires invalidation with ADD_MEMBER type."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        task_model = MagicMock()
        task_model.model_dump.return_value = {
            "gid": TEST_TASK_GID,
            "name": "Task",
        }
        mock_sdk.tasks.add_to_project_async.return_value = task_model

        response = client.post(
            f"/api/v1/tasks/{TEST_TASK_GID}/projects",
            json={"project_gid": TEST_PROJECT_GID},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 200
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.mutation_type == MutationType.ADD_MEMBER
        assert event.project_gids == [TEST_PROJECT_GID]


class TestRemoveFromProjectInvalidation:
    """T10: DELETE /tasks/{gid}/projects/{project_gid} triggers REMOVE_MEMBER."""

    def test_remove_from_project_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Remove from project fires invalidation with REMOVE_MEMBER type."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        task_model = MagicMock()
        task_model.model_dump.return_value = {
            "gid": TEST_TASK_GID,
            "name": "Task",
        }
        mock_sdk.tasks.remove_from_project_async.return_value = task_model

        response = client.delete(
            f"/api/v1/tasks/{TEST_TASK_GID}/projects/{TEST_PROJECT_GID}",
            headers=AUTH_HEADER,
        )

        assert response.status_code == 200
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.mutation_type == MutationType.REMOVE_MEMBER
        assert event.project_gids == [TEST_PROJECT_GID]


class TestFailedMutationNoInvalidation:
    """Verify failed mutations do NOT trigger invalidation."""

    def test_failed_update_no_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """400 error (no fields) does not trigger invalidation."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        response = client.put(
            f"/api/v1/tasks/{TEST_TASK_GID}",
            json={},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 400
        mock_inv.fire_and_forget.assert_not_called()
