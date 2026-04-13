"""Tests for sections endpoints.

Tests cover:
- GET /api/v1/sections/{gid} - Get section by GID
- POST /api/v1/sections - Create section in project
- PUT /api/v1/sections/{gid} - Update section (rename)
- DELETE /api/v1/sections/{gid} - Delete section
- POST /api/v1/sections/{gid}/tasks - Add task to section
- POST /api/v1/sections/{gid}/reorder - Reorder section within project
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests.unit.api.conftest import (
    TEST_PROJECT_GID,
    TEST_SECTION_GID,
    TEST_TASK_GID,
)


class TestGetSection:
    """Tests for GET /api/v1/sections/{gid} endpoint."""

    def test_get_section_success(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """Successfully returns section by GID."""
        client, mock_sdk = authed_client

        mock_sdk.sections.get_async.return_value = {
            "gid": TEST_SECTION_GID,
            "name": "Backlog",
            "project": {"gid": TEST_PROJECT_GID, "name": "Test Project"},
        }

        response = client.get(
            f"/api/v1/sections/{TEST_SECTION_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["gid"] == TEST_SECTION_GID
        assert data["data"]["name"] == "Backlog"
        assert "meta" in data
        assert "request_id" in data["meta"]

        mock_sdk.sections.get_async.assert_called_once_with(TEST_SECTION_GID, raw=True)


class TestCreateSection:
    """Tests for POST /api/v1/sections endpoint."""

    def test_create_section_success(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """Successfully creates a new section."""
        client, mock_sdk = authed_client

        mock_sdk.sections.create_async.return_value = {
            "gid": "new_section_gid",
            "name": "New Section",
            "project": {"gid": TEST_PROJECT_GID, "name": "Test Project"},
        }

        response = client.post(
            "/api/v1/sections",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={
                "name": "New Section",
                "project": TEST_PROJECT_GID,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["data"]["name"] == "New Section"
        assert "meta" in data

        mock_sdk.sections.create_async.assert_called_once_with(
            name="New Section",
            project=TEST_PROJECT_GID,
            raw=True,
        )

    def test_create_section_name_required(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Create section without name returns 422."""
        client, _ = authed_client

        response = client.post(
            "/api/v1/sections",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"project": TEST_PROJECT_GID},
        )

        assert response.status_code == 422

    def test_create_section_project_required(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Create section without project returns 422."""
        client, _ = authed_client

        response = client.post(
            "/api/v1/sections",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"name": "New Section"},
        )

        assert response.status_code == 422


class TestUpdateSection:
    """Tests for PUT /api/v1/sections/{gid} endpoint."""

    def test_update_section_success(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """Successfully updates a section."""
        client, mock_sdk = authed_client

        mock_sdk.sections.update_async.return_value = {
            "gid": TEST_SECTION_GID,
            "name": "Renamed Section",
        }

        response = client.put(
            f"/api/v1/sections/{TEST_SECTION_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"name": "Renamed Section"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["name"] == "Renamed Section"

        mock_sdk.sections.update_async.assert_called_once_with(
            TEST_SECTION_GID, raw=True, name="Renamed Section"
        )

    def test_update_section_name_required(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Update section without name returns 422."""
        client, _ = authed_client

        response = client.put(
            f"/api/v1/sections/{TEST_SECTION_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={},
        )

        assert response.status_code == 422


class TestDeleteSection:
    """Tests for DELETE /api/v1/sections/{gid} endpoint."""

    def test_delete_section_success(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """Successfully deletes a section."""
        client, mock_sdk = authed_client

        response = client.delete(
            f"/api/v1/sections/{TEST_SECTION_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 204
        mock_sdk.sections.delete_async.assert_called_once_with(TEST_SECTION_GID)


class TestAddTaskToSection:
    """Tests for POST /api/v1/sections/{gid}/tasks endpoint."""

    def test_add_task_to_section_success(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """Successfully adds a task to a section."""
        client, mock_sdk = authed_client

        response = client.post(
            f"/api/v1/sections/{TEST_SECTION_GID}/tasks",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"task_gid": TEST_TASK_GID},
        )

        assert response.status_code == 204
        mock_sdk.sections.add_task_async.assert_called_once_with(
            TEST_SECTION_GID, task=TEST_TASK_GID
        )

    def test_add_task_to_section_task_gid_required(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Add task without task_gid returns 422."""
        client, _ = authed_client

        response = client.post(
            f"/api/v1/sections/{TEST_SECTION_GID}/tasks",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={},
        )

        assert response.status_code == 422


class TestReorderSection:
    """Tests for POST /api/v1/sections/{gid}/reorder endpoint."""

    def test_reorder_section_with_before_section(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully reorders section using before_section."""
        client, mock_sdk = authed_client

        other_section_gid = "5555555555"

        response = client.post(
            f"/api/v1/sections/{TEST_SECTION_GID}/reorder",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={
                "project_gid": TEST_PROJECT_GID,
                "before_section": other_section_gid,
            },
        )

        assert response.status_code == 204
        mock_sdk.sections.insert_section_async.assert_called_once_with(
            TEST_PROJECT_GID,
            section=TEST_SECTION_GID,
            before_section=other_section_gid,
            after_section=None,
        )

    def test_reorder_section_with_after_section(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully reorders section using after_section."""
        client, mock_sdk = authed_client

        other_section_gid = "5555555555"

        response = client.post(
            f"/api/v1/sections/{TEST_SECTION_GID}/reorder",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={
                "project_gid": TEST_PROJECT_GID,
                "after_section": other_section_gid,
            },
        )

        assert response.status_code == 204
        mock_sdk.sections.insert_section_async.assert_called_once_with(
            TEST_PROJECT_GID,
            section=TEST_SECTION_GID,
            before_section=None,
            after_section=other_section_gid,
        )

    def test_reorder_section_requires_position(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Reorder without before_section or after_section returns 400."""
        client, _ = authed_client

        response = client.post(
            f"/api/v1/sections/{TEST_SECTION_GID}/reorder",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"project_gid": TEST_PROJECT_GID},
        )

        assert response.status_code == 400

    def test_reorder_section_rejects_both_positions(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Reorder with both before_section and after_section returns 400."""
        client, _ = authed_client

        response = client.post(
            f"/api/v1/sections/{TEST_SECTION_GID}/reorder",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={
                "project_gid": TEST_PROJECT_GID,
                "before_section": "5555555555",
                "after_section": "6666666666",
            },
        )

        assert response.status_code == 400

    def test_reorder_section_project_gid_required(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Reorder without project_gid returns 422."""
        client, _ = authed_client

        response = client.post(
            f"/api/v1/sections/{TEST_SECTION_GID}/reorder",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"before_section": "5555555555"},
        )

        assert response.status_code == 422
