"""Tests for health check endpoint.

Tests cover:
- GET /health returns 200 with status and version
- No authentication required
- Response format matches expected structure
"""

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health check returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client: TestClient) -> None:
        """Health check returns expected JSON structure."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert data["status"] == "healthy"

    def test_health_version_format(self, client: TestClient) -> None:
        """Health check version follows semver format."""
        response = client.get("/health")
        data = response.json()

        version = data["version"]
        # Should be semver-like: X.Y.Z
        parts = version.split(".")
        assert len(parts) == 3
        # Each part should be numeric
        for part in parts:
            assert part.isdigit()

    def test_health_no_auth_required(self, client: TestClient) -> None:
        """Health check does not require authentication.

        Per FR-API-HEALTH-002: This endpoint does NOT require authentication.
        """
        # No Authorization header
        response = client.get("/health")
        assert response.status_code == 200

        # Even with invalid header, should still work
        response = client.get("/health", headers={"Authorization": "invalid"})
        assert response.status_code == 200

    def test_health_content_type(self, client: TestClient) -> None:
        """Health check returns JSON content type."""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"
