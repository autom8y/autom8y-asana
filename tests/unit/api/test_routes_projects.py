"""Tests for projects endpoints.

Tests cover:
- GET /api/v1/projects?workspace={gid} - List projects by workspace (paginated)
- GET /api/v1/projects/{gid} - Get project by GID
- POST /api/v1/projects - Create project
- PUT /api/v1/projects/{gid} - Update project
- DELETE /api/v1/projects/{gid} - Delete project
- GET /api/v1/projects/{gid}/sections - List sections in project (paginated)
- POST /api/v1/projects/{gid}/members - Add members to project
- DELETE /api/v1/projects/{gid}/members - Remove members from project

Per TDD-ASANA-SATELLITE (FR-API-PROJ-001 through FR-API-PROJ-008).
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests.unit.api.conftest import (
    TEST_PROJECT_GID,
    TEST_SECTION_GID,
    TEST_TEAM_GID,
    TEST_USER_GID,
    TEST_WORKSPACE_GID,
)

# Sample project data matching Asana API response structure
SAMPLE_PROJECT = {
    "gid": TEST_PROJECT_GID,
    "name": "Test Project",
    "notes": "Project description",
    "workspace": {"gid": TEST_WORKSPACE_GID, "name": "Test Workspace"},
    "archived": False,
    "owner": {"gid": TEST_USER_GID, "name": "Test User"},
    "team": {"gid": TEST_TEAM_GID, "name": "Test Team"},
}

SAMPLE_PROJECT_2 = {
    "gid": "7777777777",
    "name": "Another Project",
    "notes": "Another description",
    "workspace": {"gid": TEST_WORKSPACE_GID, "name": "Test Workspace"},
    "archived": True,
    "owner": {"gid": TEST_USER_GID, "name": "Test User"},
}

SAMPLE_SECTION = {
    "gid": TEST_SECTION_GID,
    "name": "Backlog",
    "project": {"gid": TEST_PROJECT_GID, "name": "Test Project"},
}

SAMPLE_SECTION_2 = {
    "gid": "8888888888",
    "name": "In Progress",
    "project": {"gid": TEST_PROJECT_GID, "name": "Test Project"},
}


class TestListProjects:
    """Tests for GET /api/v1/projects endpoint."""

    def test_list_projects_success_empty(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns empty list when workspace has no projects."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/projects?workspace={TEST_WORKSPACE_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"] == []
        assert "meta" in data
        assert "request_id" in data["meta"]
        assert data["meta"]["pagination"]["has_more"] is False
        assert data["meta"]["pagination"]["next_offset"] is None

        mock_sdk._http.get_paginated.assert_called_once_with(
            "/projects",
            params={"workspace": TEST_WORKSPACE_GID, "limit": 100},
        )

    def test_list_projects_success_with_projects(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns list of projects."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = (
            [SAMPLE_PROJECT, SAMPLE_PROJECT_2],
            None,
        )

        response = client.get(
            f"/api/v1/projects?workspace={TEST_WORKSPACE_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data"]) == 2
        assert data["data"][0]["gid"] == TEST_PROJECT_GID
        assert data["data"][0]["name"] == "Test Project"
        assert data["data"][1]["gid"] == "7777777777"
        assert data["meta"]["pagination"]["has_more"] is False

    def test_list_projects_with_pagination(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns projects with pagination metadata."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = (
            [SAMPLE_PROJECT],
            "next_page_cursor",
        )

        response = client.get(
            f"/api/v1/projects?workspace={TEST_WORKSPACE_GID}&limit=1",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data"]) == 1
        assert data["meta"]["pagination"]["has_more"] is True
        assert data["meta"]["pagination"]["next_offset"] == "next_page_cursor"
        assert data["meta"]["pagination"]["limit"] == 1

        mock_sdk._http.get_paginated.assert_called_once_with(
            "/projects",
            params={"workspace": TEST_WORKSPACE_GID, "limit": 1},
        )

    def test_list_projects_with_offset(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully handles offset parameter for pagination."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([SAMPLE_PROJECT_2], None)

        response = client.get(
            f"/api/v1/projects?workspace={TEST_WORKSPACE_GID}&offset=cursor_abc",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data"]) == 1
        assert data["meta"]["pagination"]["has_more"] is False

        mock_sdk._http.get_paginated.assert_called_once_with(
            "/projects",
            params={
                "workspace": TEST_WORKSPACE_GID,
                "limit": 100,
                "offset": "cursor_abc",
            },
        )

    def test_list_projects_caps_limit_at_max(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Limit is capped at MAX_LIMIT (100)."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([], None)

        # Request limit of 200, should be capped to 100
        response = client.get(
            f"/api/v1/projects?workspace={TEST_WORKSPACE_GID}&limit=200",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        # FastAPI validation should reject limit > 100
        assert response.status_code == 422

    def test_list_projects_workspace_required(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """List projects without workspace returns 422."""
        client, _ = authed_client

        response = client.get(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 422

    def test_list_projects_invalid_limit(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """List projects with invalid limit returns 422."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/projects?workspace={TEST_WORKSPACE_GID}&limit=0",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 422


class TestGetProject:
    """Tests for GET /api/v1/projects/{gid} endpoint."""

    def test_get_project_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns project by GID."""
        client, mock_sdk = authed_client

        mock_sdk.projects.get_async.return_value = SAMPLE_PROJECT

        response = client.get(
            f"/api/v1/projects/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["gid"] == TEST_PROJECT_GID
        assert data["data"]["name"] == "Test Project"
        assert data["data"]["notes"] == "Project description"
        assert "meta" in data
        assert "request_id" in data["meta"]

        mock_sdk.projects.get_async.assert_called_once_with(
            TEST_PROJECT_GID, opt_fields=None, raw=True
        )

    def test_get_project_with_opt_fields(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns project with specified opt_fields."""
        client, mock_sdk = authed_client

        mock_sdk.projects.get_async.return_value = {
            "gid": TEST_PROJECT_GID,
            "name": "Test Project",
            "owner": {"gid": TEST_USER_GID, "name": "Test User"},
        }

        response = client.get(
            f"/api/v1/projects/{TEST_PROJECT_GID}?opt_fields=name,owner",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["gid"] == TEST_PROJECT_GID
        assert data["data"]["name"] == "Test Project"
        assert data["data"]["owner"]["gid"] == TEST_USER_GID

        mock_sdk.projects.get_async.assert_called_once_with(
            TEST_PROJECT_GID, opt_fields=["name", "owner"], raw=True
        )

    def test_get_project_with_opt_fields_whitespace(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully handles opt_fields with whitespace."""
        client, mock_sdk = authed_client

        mock_sdk.projects.get_async.return_value = SAMPLE_PROJECT

        response = client.get(
            f"/api/v1/projects/{TEST_PROJECT_GID}?opt_fields=name, notes, owner",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

        mock_sdk.projects.get_async.assert_called_once_with(
            TEST_PROJECT_GID, opt_fields=["name", "notes", "owner"], raw=True
        )


class TestCreateProject:
    """Tests for POST /api/v1/projects endpoint."""

    def test_create_project_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully creates a new project."""
        client, mock_sdk = authed_client

        mock_sdk.projects.create_async.return_value = SAMPLE_PROJECT

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={
                "name": "Test Project",
                "workspace": TEST_WORKSPACE_GID,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["data"]["gid"] == TEST_PROJECT_GID
        assert data["data"]["name"] == "Test Project"
        assert "meta" in data

        mock_sdk.projects.create_async.assert_called_once_with(
            name="Test Project",
            workspace=TEST_WORKSPACE_GID,
            raw=True,
        )

    def test_create_project_with_team(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully creates a project with team."""
        client, mock_sdk = authed_client

        mock_sdk.projects.create_async.return_value = SAMPLE_PROJECT

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={
                "name": "Test Project",
                "workspace": TEST_WORKSPACE_GID,
                "team": TEST_TEAM_GID,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["data"]["gid"] == TEST_PROJECT_GID

        mock_sdk.projects.create_async.assert_called_once_with(
            name="Test Project",
            workspace=TEST_WORKSPACE_GID,
            raw=True,
            team=TEST_TEAM_GID,
        )

    def test_create_project_name_required(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Create project without name returns 422."""
        client, _ = authed_client

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"workspace": TEST_WORKSPACE_GID},
        )

        assert response.status_code == 422

    def test_create_project_workspace_required(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Create project without workspace returns 422."""
        client, _ = authed_client

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"name": "Test Project"},
        )

        assert response.status_code == 422

    def test_create_project_empty_name_returns_422(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Create project with empty name returns 422."""
        client, _ = authed_client

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"name": "", "workspace": TEST_WORKSPACE_GID},
        )

        assert response.status_code == 422

    def test_create_project_empty_workspace_returns_422(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Create project with empty workspace returns 422."""
        client, _ = authed_client

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"name": "Test Project", "workspace": ""},
        )

        assert response.status_code == 422

    def test_create_project_rejects_extra_fields(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Create project with extra fields returns 422."""
        client, _ = authed_client

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={
                "name": "Test Project",
                "workspace": TEST_WORKSPACE_GID,
                "extra_field": "not_allowed",
            },
        )

        assert response.status_code == 422


class TestUpdateProject:
    """Tests for PUT /api/v1/projects/{gid} endpoint."""

    def test_update_project_name_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully updates project name."""
        client, mock_sdk = authed_client

        mock_sdk.projects.update_async.return_value = {
            **SAMPLE_PROJECT,
            "name": "Updated Project Name",
        }

        response = client.put(
            f"/api/v1/projects/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"name": "Updated Project Name"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["name"] == "Updated Project Name"

        mock_sdk.projects.update_async.assert_called_once_with(
            TEST_PROJECT_GID, raw=True, name="Updated Project Name"
        )

    def test_update_project_notes_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully updates project notes."""
        client, mock_sdk = authed_client

        mock_sdk.projects.update_async.return_value = {
            **SAMPLE_PROJECT,
            "notes": "Updated notes",
        }

        response = client.put(
            f"/api/v1/projects/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"notes": "Updated notes"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["notes"] == "Updated notes"

        mock_sdk.projects.update_async.assert_called_once_with(
            TEST_PROJECT_GID, raw=True, notes="Updated notes"
        )

    def test_update_project_archived_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully updates project archived status."""
        client, mock_sdk = authed_client

        mock_sdk.projects.update_async.return_value = {
            **SAMPLE_PROJECT,
            "archived": True,
        }

        response = client.put(
            f"/api/v1/projects/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"archived": True},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["archived"] is True

        mock_sdk.projects.update_async.assert_called_once_with(
            TEST_PROJECT_GID, raw=True, archived=True
        )

    def test_update_project_multiple_fields(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully updates multiple fields at once."""
        client, mock_sdk = authed_client

        mock_sdk.projects.update_async.return_value = {
            **SAMPLE_PROJECT,
            "name": "New Name",
            "notes": "New notes",
            "archived": True,
        }

        response = client.put(
            f"/api/v1/projects/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"name": "New Name", "notes": "New notes", "archived": True},
        )

        assert response.status_code == 200

        mock_sdk.projects.update_async.assert_called_once_with(
            TEST_PROJECT_GID,
            raw=True,
            name="New Name",
            notes="New notes",
            archived=True,
        )

    def test_update_project_no_fields_returns_400(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Update project without any fields returns 400."""
        client, _ = authed_client

        response = client.put(
            f"/api/v1/projects/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={},
        )

        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "INVALID_PARAMETER"
        assert "at least one field" in body["error"]["message"].lower()

    def test_update_project_empty_name_returns_422(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Update project with empty name returns 422."""
        client, _ = authed_client

        response = client.put(
            f"/api/v1/projects/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"name": ""},
        )

        assert response.status_code == 422

    def test_update_project_rejects_extra_fields(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Update project with extra fields returns 422."""
        client, _ = authed_client

        response = client.put(
            f"/api/v1/projects/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"name": "New Name", "workspace": TEST_WORKSPACE_GID},
        )

        assert response.status_code == 422


class TestDeleteProject:
    """Tests for DELETE /api/v1/projects/{gid} endpoint."""

    def test_delete_project_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully deletes a project."""
        client, mock_sdk = authed_client

        response = client.delete(
            f"/api/v1/projects/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 204
        mock_sdk.projects.delete_async.assert_called_once_with(TEST_PROJECT_GID)


class TestListProjectSections:
    """Tests for GET /api/v1/projects/{gid}/sections endpoint."""

    def test_list_sections_success_empty(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns empty list when project has no sections."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/projects/{TEST_PROJECT_GID}/sections",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"] == []
        assert data["meta"]["pagination"]["has_more"] is False
        assert data["meta"]["pagination"]["next_offset"] is None

        mock_sdk._http.get_paginated.assert_called_once_with(
            f"/projects/{TEST_PROJECT_GID}/sections",
            params={"limit": 100},
        )

    def test_list_sections_success_with_sections(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns list of sections."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = (
            [SAMPLE_SECTION, SAMPLE_SECTION_2],
            None,
        )

        response = client.get(
            f"/api/v1/projects/{TEST_PROJECT_GID}/sections",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data"]) == 2
        assert data["data"][0]["gid"] == TEST_SECTION_GID
        assert data["data"][0]["name"] == "Backlog"
        assert data["data"][1]["name"] == "In Progress"

    def test_list_sections_with_pagination(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns sections with pagination metadata."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = (
            [SAMPLE_SECTION],
            "section_cursor",
        )

        response = client.get(
            f"/api/v1/projects/{TEST_PROJECT_GID}/sections?limit=1",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["pagination"]["has_more"] is True
        assert data["meta"]["pagination"]["next_offset"] == "section_cursor"
        assert data["meta"]["pagination"]["limit"] == 1

    def test_list_sections_with_offset(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully handles offset parameter for pagination."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([SAMPLE_SECTION_2], None)

        response = client.get(
            f"/api/v1/projects/{TEST_PROJECT_GID}/sections?offset=cursor_xyz",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

        mock_sdk._http.get_paginated.assert_called_once_with(
            f"/projects/{TEST_PROJECT_GID}/sections",
            params={"limit": 100, "offset": "cursor_xyz"},
        )

    def test_list_sections_invalid_limit(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """List sections with invalid limit returns 422."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/projects/{TEST_PROJECT_GID}/sections?limit=0",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 422

    def test_list_sections_limit_over_max_returns_422(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """List sections with limit over max returns 422."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/projects/{TEST_PROJECT_GID}/sections?limit=101",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 422


class TestAddMembers:
    """Tests for POST /api/v1/projects/{gid}/members endpoint."""

    def test_add_members_success_single(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully adds a single member to project."""
        client, mock_sdk = authed_client

        mock_sdk.projects.add_members_async.return_value = SAMPLE_PROJECT

        response = client.post(
            f"/api/v1/projects/{TEST_PROJECT_GID}/members",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"members": [TEST_USER_GID]},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["gid"] == TEST_PROJECT_GID
        assert "meta" in data

        mock_sdk.projects.add_members_async.assert_called_once_with(
            TEST_PROJECT_GID, members=[TEST_USER_GID], raw=True
        )

    def test_add_members_success_multiple(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully adds multiple members to project."""
        client, mock_sdk = authed_client

        mock_sdk.projects.add_members_async.return_value = SAMPLE_PROJECT

        user_gids = [TEST_USER_GID, "9999999999", "8888888888"]

        response = client.post(
            f"/api/v1/projects/{TEST_PROJECT_GID}/members",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"members": user_gids},
        )

        assert response.status_code == 200

        mock_sdk.projects.add_members_async.assert_called_once_with(
            TEST_PROJECT_GID, members=user_gids, raw=True
        )

    def test_add_members_empty_list_returns_422(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Add members with empty list returns 422."""
        client, _ = authed_client

        response = client.post(
            f"/api/v1/projects/{TEST_PROJECT_GID}/members",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"members": []},
        )

        assert response.status_code == 422

    def test_add_members_missing_field_returns_422(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Add members without members field returns 422."""
        client, _ = authed_client

        response = client.post(
            f"/api/v1/projects/{TEST_PROJECT_GID}/members",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={},
        )

        assert response.status_code == 422

    def test_add_members_rejects_extra_fields(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Add members with extra fields returns 422."""
        client, _ = authed_client

        response = client.post(
            f"/api/v1/projects/{TEST_PROJECT_GID}/members",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"members": [TEST_USER_GID], "role": "admin"},
        )

        assert response.status_code == 422


class TestRemoveMembers:
    """Tests for DELETE /api/v1/projects/{gid}/members endpoint."""

    def test_remove_members_success_single(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully removes a single member from project."""
        client, mock_sdk = authed_client

        mock_sdk.projects.remove_members_async.return_value = SAMPLE_PROJECT

        response = client.request(
            "DELETE",
            f"/api/v1/projects/{TEST_PROJECT_GID}/members",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"members": [TEST_USER_GID]},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["gid"] == TEST_PROJECT_GID

        mock_sdk.projects.remove_members_async.assert_called_once_with(
            TEST_PROJECT_GID, members=[TEST_USER_GID], raw=True
        )

    def test_remove_members_success_multiple(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully removes multiple members from project."""
        client, mock_sdk = authed_client

        mock_sdk.projects.remove_members_async.return_value = SAMPLE_PROJECT

        user_gids = [TEST_USER_GID, "9999999999"]

        response = client.request(
            "DELETE",
            f"/api/v1/projects/{TEST_PROJECT_GID}/members",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"members": user_gids},
        )

        assert response.status_code == 200

        mock_sdk.projects.remove_members_async.assert_called_once_with(
            TEST_PROJECT_GID, members=user_gids, raw=True
        )

    def test_remove_members_empty_list_returns_422(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Remove members with empty list returns 422."""
        client, _ = authed_client

        response = client.request(
            "DELETE",
            f"/api/v1/projects/{TEST_PROJECT_GID}/members",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"members": []},
        )

        assert response.status_code == 422

    def test_remove_members_missing_field_returns_422(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Remove members without members field returns 422."""
        client, _ = authed_client

        response = client.request(
            "DELETE",
            f"/api/v1/projects/{TEST_PROJECT_GID}/members",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={},
        )

        assert response.status_code == 422

    def test_remove_members_rejects_extra_fields(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Remove members with extra fields returns 422."""
        client, _ = authed_client

        response = client.request(
            "DELETE",
            f"/api/v1/projects/{TEST_PROJECT_GID}/members",
            headers={"Authorization": "Bearer test_pat_token_12345"},
            json={"members": [TEST_USER_GID], "force": True},
        )

        assert response.status_code == 422
