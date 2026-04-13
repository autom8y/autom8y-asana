"""Tests for users endpoints.

Tests cover:
- GET /api/v1/users/me - current user
- GET /api/v1/users/{gid} - get user by GID
- GET /api/v1/users?workspace={gid} - list users in workspace
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests.unit.api.conftest import TEST_USER_GID, TEST_WORKSPACE_GID


class TestGetCurrentUser:
    """Tests for GET /api/v1/users/me endpoint."""

    def test_get_current_user_success(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """Successfully returns current authenticated user."""
        client, mock_sdk = authed_client

        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify envelope structure
        assert "data" in data
        assert "meta" in data
        assert "request_id" in data["meta"]
        assert "timestamp" in data["meta"]

        # Verify SDK was called
        mock_sdk.users.me_async.assert_called_once_with(raw=True)

    def test_get_current_user_response_data(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Current user response contains expected fields."""
        client, mock_sdk = authed_client

        # Configure mock return value
        mock_sdk.users.me_async.return_value = {
            "gid": TEST_USER_GID,
            "name": "Test User",
            "email": "test@example.com",
        }

        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        user_data = response.json()["data"]

        assert user_data["gid"] == TEST_USER_GID
        assert user_data["name"] == "Test User"
        assert user_data["email"] == "test@example.com"


class TestGetUserByGid:
    """Tests for GET /api/v1/users/{gid} endpoint."""

    def test_get_user_by_gid_success(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """Successfully returns user by GID."""
        client, mock_sdk = authed_client

        response = client.get(
            f"/api/v1/users/{TEST_USER_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify envelope structure
        assert "data" in data
        assert "meta" in data

        # Verify SDK was called with correct GID
        mock_sdk.users.get_async.assert_called_once_with(TEST_USER_GID, raw=True)

    def test_get_user_by_gid_response_data(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """User response contains expected fields."""
        client, mock_sdk = authed_client

        mock_sdk.users.get_async.return_value = {
            "gid": TEST_USER_GID,
            "name": "Specific User",
            "email": "specific@example.com",
        }

        response = client.get(
            f"/api/v1/users/{TEST_USER_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        user_data = response.json()["data"]
        assert user_data["gid"] == TEST_USER_GID
        assert user_data["name"] == "Specific User"


class TestListUsers:
    """Tests for GET /api/v1/users?workspace={gid} endpoint."""

    def test_list_users_requires_workspace(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """List users without workspace parameter returns 422."""
        client, _ = authed_client

        response = client.get(
            "/api/v1/users",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        # FastAPI validation error for missing required param
        assert response.status_code == 422

    def test_list_users_success(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """Successfully lists users in workspace."""
        client, mock_sdk = authed_client

        # Configure mock for paginated response
        mock_sdk._http.get_paginated.return_value = (
            [
                {"gid": "user1", "name": "User One"},
                {"gid": "user2", "name": "User Two"},
            ],
            None,  # No next_offset
        )

        response = client.get(
            f"/api/v1/users?workspace={TEST_WORKSPACE_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify data is a list
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 2

        # Verify pagination metadata
        assert "pagination" in data["meta"]
        assert data["meta"]["pagination"]["has_more"] is False

    def test_list_users_with_pagination(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """List users returns pagination metadata when more pages exist."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = (
            [{"gid": "user1", "name": "User One"}],
            "next_cursor_token",  # Has more pages
        )

        response = client.get(
            f"/api/v1/users?workspace={TEST_WORKSPACE_GID}&limit=1",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        pagination = response.json()["meta"]["pagination"]

        assert pagination["has_more"] is True
        assert pagination["next_offset"] == "next_cursor_token"
        assert pagination["limit"] == 1

    def test_list_users_with_offset(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """List users passes offset parameter to SDK."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/users?workspace={TEST_WORKSPACE_GID}&offset=cursor123",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

        # Verify offset was passed to SDK
        call_args = mock_sdk._http.get_paginated.call_args
        assert call_args[1]["params"]["offset"] == "cursor123"

    def test_list_users_limit_bounds(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        """List users enforces limit bounds (1-100)."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([], None)

        # Test limit below minimum
        response = client.get(
            f"/api/v1/users?workspace={TEST_WORKSPACE_GID}&limit=0",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )
        assert response.status_code == 422

        # Test limit above maximum
        response = client.get(
            f"/api/v1/users?workspace={TEST_WORKSPACE_GID}&limit=101",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )
        assert response.status_code == 422
