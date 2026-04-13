"""Tests for workspaces endpoints.

Tests cover:
- GET /api/v1/workspaces - list all workspaces
- GET /api/v1/workspaces/{gid} - get workspace by GID
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests.unit.api.conftest import TEST_WORKSPACE_GID


class TestListWorkspaces:
    """Tests for GET /api/v1/workspaces endpoint."""

    def test_list_workspaces_success(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """Successfully lists all accessible workspaces."""
        client, mock_sdk = authed_client

        # Configure mock for paginated response
        mock_sdk._http.get_paginated.return_value = (
            [
                {"gid": "ws1", "name": "Workspace One", "is_organization": False},
                {"gid": "ws2", "name": "Workspace Two", "is_organization": True},
            ],
            None,  # No next_offset
        )

        response = client.get(
            "/api/v1/workspaces",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify envelope structure
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 2

        # Verify pagination metadata
        assert "pagination" in data["meta"]
        assert data["meta"]["pagination"]["has_more"] is False

    def test_list_workspaces_with_pagination(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """List workspaces returns pagination metadata when more pages exist."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = (
            [{"gid": "ws1", "name": "Workspace One"}],
            "next_cursor_token",  # Has more pages
        )

        response = client.get(
            "/api/v1/workspaces?limit=1",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        pagination = response.json()["meta"]["pagination"]

        assert pagination["has_more"] is True
        assert pagination["next_offset"] == "next_cursor_token"
        assert pagination["limit"] == 1

    def test_list_workspaces_with_offset(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """List workspaces passes offset parameter to SDK."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            "/api/v1/workspaces?offset=cursor123",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

        # Verify offset was passed to SDK
        call_args = mock_sdk._http.get_paginated.call_args
        assert call_args[1]["params"]["offset"] == "cursor123"

    def test_list_workspaces_default_limit(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """List workspaces uses default limit of 100."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            "/api/v1/workspaces",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

        # Verify default limit was used
        call_args = mock_sdk._http.get_paginated.call_args
        assert call_args[1]["params"]["limit"] == 100


class TestGetWorkspaceByGid:
    """Tests for GET /api/v1/workspaces/{gid} endpoint."""

    def test_get_workspace_by_gid_success(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns workspace by GID."""
        client, mock_sdk = authed_client

        mock_sdk.workspaces.get_async.return_value = {
            "gid": TEST_WORKSPACE_GID,
            "name": "Test Workspace",
            "is_organization": True,
            "email_domains": ["example.com"],
        }

        response = client.get(
            f"/api/v1/workspaces/{TEST_WORKSPACE_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify envelope structure
        assert "data" in data
        assert "meta" in data
        assert "request_id" in data["meta"]

        # Verify SDK was called with correct GID
        mock_sdk.workspaces.get_async.assert_called_once_with(TEST_WORKSPACE_GID, raw=True)

    def test_get_workspace_response_data(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """Workspace response contains expected fields."""
        client, mock_sdk = authed_client

        mock_sdk.workspaces.get_async.return_value = {
            "gid": TEST_WORKSPACE_GID,
            "name": "My Organization",
            "is_organization": True,
            "email_domains": ["company.com", "corp.com"],
        }

        response = client.get(
            f"/api/v1/workspaces/{TEST_WORKSPACE_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        workspace_data = response.json()["data"]
        assert workspace_data["gid"] == TEST_WORKSPACE_GID
        assert workspace_data["name"] == "My Organization"
        assert workspace_data["is_organization"] is True
        assert "company.com" in workspace_data["email_domains"]
