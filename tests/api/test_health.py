"""Tests for health check endpoints.

Tests cover:
- GET /health returns 200 with status and version
- GET /health/s2s returns S2S connectivity status
- No authentication required
- Response format matches expected structure

Per PRD-S2S-001 NFR-OPS-002: Health check includes S2S connectivity status.
"""

import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest
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


class TestS2SHealthEndpoint:
    """Tests for the /health/s2s endpoint.

    Per PRD-S2S-001 NFR-OPS-002: S2S health check verifies JWKS and bot PAT.
    """

    def test_s2s_health_returns_expected_fields(self, client: TestClient) -> None:
        """S2S health check returns expected JSON structure."""
        response = client.get("/health/s2s")
        data = response.json()

        # Required fields
        assert "status" in data
        assert "version" in data
        assert "s2s_connectivity" in data
        assert "jwks_reachable" in data
        assert "bot_pat_configured" in data
        assert "details" in data

    def test_s2s_health_no_auth_required(self, client: TestClient) -> None:
        """S2S health check does not require authentication."""
        # No Authorization header
        response = client.get("/health/s2s")
        # Should not return 401
        assert response.status_code in (200, 503)

    def test_s2s_health_reports_bot_pat_not_configured(self, client: TestClient) -> None:
        """S2S health reports when bot PAT is not configured."""
        # Clear ASANA_PAT if set
        with patch.dict(os.environ, {"ASANA_PAT": ""}, clear=False):
            response = client.get("/health/s2s")
            data = response.json()

            assert data["bot_pat_configured"] is False
            assert data["details"]["bot_pat_status"] == "not_configured"

    def test_s2s_health_reports_bot_pat_configured(self, client: TestClient) -> None:
        """S2S health reports when bot PAT is configured."""
        with patch.dict(os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False):
            response = client.get("/health/s2s")
            data = response.json()

            assert data["bot_pat_configured"] is True
            assert data["details"]["bot_pat_status"] == "configured"

    def test_s2s_health_status_healthy_when_all_dependencies_ok(
        self, client: TestClient
    ) -> None:
        """S2S health returns 200 and healthy when all dependencies OK."""
        # Mock successful JWKS response
        mock_response = httpx.Response(
            200,
            json={"keys": [{"kid": "test-key", "kty": "RSA"}]},
        )

        with patch.dict(os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                response = client.get("/health/s2s")
                data = response.json()

                assert response.status_code == 200
                assert data["status"] == "healthy"
                assert data["s2s_connectivity"] is True

    def test_s2s_health_status_degraded_when_jwks_unreachable(
        self, client: TestClient
    ) -> None:
        """S2S health returns 503 when JWKS is unreachable."""
        with patch.dict(os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = httpx.TimeoutException("timeout")
                response = client.get("/health/s2s")
                data = response.json()

                assert response.status_code == 503
                assert data["status"] == "degraded"
                assert data["jwks_reachable"] is False
                assert data["s2s_connectivity"] is False
                assert data["details"]["jwks_status"] == "timeout"

    def test_s2s_health_status_degraded_when_bot_pat_missing(
        self, client: TestClient
    ) -> None:
        """S2S health returns 503 when bot PAT is not configured."""
        # Mock successful JWKS but no PAT
        mock_response = httpx.Response(
            200,
            json={"keys": [{"kid": "test-key", "kty": "RSA"}]},
        )

        with patch.dict(os.environ, {"ASANA_PAT": ""}, clear=False):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                response = client.get("/health/s2s")
                data = response.json()

                assert response.status_code == 503
                assert data["status"] == "degraded"
                assert data["bot_pat_configured"] is False
                assert data["s2s_connectivity"] is False

    def test_s2s_health_handles_invalid_jwks_response(
        self, client: TestClient
    ) -> None:
        """S2S health handles JWKS response without keys array."""
        mock_response = httpx.Response(200, json={"error": "not a jwks"})

        with patch.dict(os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                response = client.get("/health/s2s")
                data = response.json()

                assert data["jwks_reachable"] is False
                assert data["details"]["jwks_status"] == "invalid_response"

    def test_s2s_health_handles_jwks_connection_error(
        self, client: TestClient
    ) -> None:
        """S2S health handles JWKS connection errors."""
        with patch.dict(os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = httpx.ConnectError("connection failed")
                response = client.get("/health/s2s")
                data = response.json()

                assert data["jwks_reachable"] is False
                assert data["details"]["jwks_status"] == "connection_error"
