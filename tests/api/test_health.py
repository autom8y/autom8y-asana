"""Tests for health check endpoints.

Tests cover:
- GET /satellite/health returns 200 always (liveness probe for ALB)
- GET /satellite/health/ready returns 503 during warmup, 200 when ready (readiness probe)
- GET /satellite/health/s2s returns S2S connectivity status
- No authentication required
- Response format matches expected structure
- Cache readiness affects /satellite/health/ready status (FR-004)

Per PRD-S2S-001 NFR-OPS-002: Health check includes S2S connectivity status.
Per sprint-materialization-002 FR-004: Readiness returns 503 during cache warmup.

Health Check Architecture:
- /satellite/health: Liveness probe - always 200 if app is running (for ALB)
- /satellite/health/ready: Readiness probe - 503 during warmup, 200 when ready
- /satellite/health/s2s: S2S connectivity check
"""

import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.routes.health import (
    is_cache_ready,
    set_cache_ready,
)


@pytest.fixture(autouse=True)
def reset_cache_ready():
    """Reset cache ready state before and after each test.

    This ensures tests start with cache ready (for backward compatibility)
    and clean up after themselves.
    """
    # Set to ready by default for existing tests
    set_cache_ready(True)
    yield
    # Clean up
    set_cache_ready(True)


class TestHealthEndpoint:
    """Tests for the /satellite/health endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health check returns 200 OK."""
        response = client.get("/satellite/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client: TestClient) -> None:
        """Health check returns expected JSON structure."""
        response = client.get("/satellite/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert data["status"] == "healthy"

    def test_health_version_format(self, client: TestClient) -> None:
        """Health check version follows semver format."""
        response = client.get("/satellite/health")
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
        response = client.get("/satellite/health")
        assert response.status_code == 200

        # Even with invalid header, should still work
        response = client.get("/satellite/health", headers={"Authorization": "invalid"})
        assert response.status_code == 200

    def test_health_content_type(self, client: TestClient) -> None:
        """Health check returns JSON content type."""
        response = client.get("/satellite/health")
        assert response.headers["content-type"] == "application/json"


@pytest.mark.slow
class TestS2SHealthEndpoint:
    """Tests for the /satellite/health/s2s endpoint.

    Per PRD-S2S-001 NFR-OPS-002: S2S health check verifies JWKS and bot PAT.
    """

    def test_s2s_health_returns_expected_fields(self, client: TestClient) -> None:
        """S2S health check returns expected JSON structure."""
        response = client.get("/satellite/health/s2s")
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
        response = client.get("/satellite/health/s2s")
        # Should not return 401
        assert response.status_code in (200, 503)

    def test_s2s_health_reports_bot_pat_not_configured(
        self, client: TestClient
    ) -> None:
        """S2S health reports when bot PAT is not configured."""
        # Clear ASANA_PAT if set
        with patch.dict(os.environ, {"ASANA_PAT": ""}, clear=False):
            response = client.get("/satellite/health/s2s")
            data = response.json()

            assert data["bot_pat_configured"] is False
            assert data["details"]["bot_pat_status"] == "not_configured"

    def test_s2s_health_reports_bot_pat_configured(self, client: TestClient) -> None:
        """S2S health reports when bot PAT is configured."""
        with patch.dict(
            os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False
        ):
            response = client.get("/satellite/health/s2s")
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

        with patch.dict(
            os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False
        ):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                response = client.get("/satellite/health/s2s")
                data = response.json()

                assert response.status_code == 200
                assert data["status"] == "healthy"
                assert data["s2s_connectivity"] is True

    def test_s2s_health_status_degraded_when_jwks_unreachable(
        self, client: TestClient
    ) -> None:
        """S2S health returns 503 when JWKS is unreachable."""
        with patch.dict(
            os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False
        ):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = httpx.TimeoutException("timeout")
                response = client.get("/satellite/health/s2s")
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
                response = client.get("/satellite/health/s2s")
                data = response.json()

                assert response.status_code == 503
                assert data["status"] == "degraded"
                assert data["bot_pat_configured"] is False
                assert data["s2s_connectivity"] is False

    def test_s2s_health_handles_invalid_jwks_response(self, client: TestClient) -> None:
        """S2S health handles JWKS response without keys array."""
        mock_response = httpx.Response(200, json={"error": "not a jwks"})

        with patch.dict(
            os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False
        ):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                response = client.get("/satellite/health/s2s")
                data = response.json()

                assert data["jwks_reachable"] is False
                assert data["details"]["jwks_status"] == "invalid_response"

    def test_s2s_health_handles_jwks_connection_error(self, client: TestClient) -> None:
        """S2S health handles JWKS connection errors."""
        with patch.dict(
            os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False
        ):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = httpx.ConnectError("connection failed")
                response = client.get("/satellite/health/s2s")
                data = response.json()

                assert data["jwks_reachable"] is False
                assert data["details"]["jwks_status"] == "connection_error"


class TestCacheReadiness:
    """Tests for cache readiness affecting health status.

    Per sprint-materialization-002 FR-004:
    - GET /satellite/health/ready returns 503 "warming" status during cache preload
    - GET /satellite/health/ready returns 200 "ready" status after cache is ready
    - GET /satellite/health always returns 200 (liveness probe for ALB)

    Architecture:
    - /satellite/health is the liveness probe - always 200 if app is running
    - /satellite/health/ready is the readiness probe - 503 during warmup
    """

    def test_health_returns_200_always_even_when_cache_not_ready(
        self, client: TestClient
    ) -> None:
        """Health (liveness) always returns 200, even during warmup.

        The /satellite/health endpoint is used by ALB health checks and must return
        200 to prevent container termination during cache warming.
        """
        set_cache_ready(False)

        response = client.get("/satellite/health")

        # Liveness probe always returns 200
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        # But includes cache_ready flag for observability
        assert data["cache_ready"] is False

    def test_health_includes_cache_ready_flag(self, client: TestClient) -> None:
        """Health check includes cache_ready flag for observability."""
        set_cache_ready(True)
        response = client.get("/satellite/health")
        assert response.json()["cache_ready"] is True

        set_cache_ready(False)
        response = client.get("/satellite/health")
        assert response.json()["cache_ready"] is False

    def test_readiness_returns_503_when_cache_not_ready(
        self, client: TestClient
    ) -> None:
        """Readiness check returns 503 when cache is not ready.

        Per FR-004: During cache preload, readiness endpoint returns 503 to
        signal service may have degraded performance.
        """
        set_cache_ready(False)

        response = client.get("/satellite/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "warming"
        assert "version" in data
        assert "message" in data
        assert "preload" in data["message"].lower()

    def test_readiness_returns_200_when_cache_ready(self, client: TestClient) -> None:
        """Readiness check returns 200 when cache is ready.

        Per FR-004: After cache preload completes, readiness returns 200.
        """
        set_cache_ready(True)

        response = client.get("/satellite/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_set_cache_ready_changes_state(self) -> None:
        """set_cache_ready() correctly updates the cache ready state."""
        # Start with not ready
        set_cache_ready(False)
        assert is_cache_ready() is False

        # Set to ready
        set_cache_ready(True)
        assert is_cache_ready() is True

        # Set back to not ready
        set_cache_ready(False)
        assert is_cache_ready() is False

    def test_is_cache_ready_returns_current_state(self) -> None:
        """is_cache_ready() returns the current cache ready state."""
        set_cache_ready(True)
        assert is_cache_ready() is True

        set_cache_ready(False)
        assert is_cache_ready() is False

    def test_health_always_includes_version(self, client: TestClient) -> None:
        """Health check always includes version regardless of cache state."""
        set_cache_ready(False)
        response = client.get("/satellite/health")
        data = response.json()
        version = data["version"]
        parts = version.split(".")
        assert len(parts) == 3

        set_cache_ready(True)
        response = client.get("/satellite/health")
        data = response.json()
        version = data["version"]
        parts = version.split(".")
        assert len(parts) == 3

    def test_readiness_warming_includes_version(self, client: TestClient) -> None:
        """Readiness check in warming state still includes version."""
        set_cache_ready(False)

        response = client.get("/satellite/health/ready")
        data = response.json()

        version = data["version"]
        parts = version.split(".")
        assert len(parts) == 3

    def test_health_warming_no_auth_required(self, client: TestClient) -> None:
        """Health and readiness checks never require authentication.

        Per FR-API-HEALTH-002: Health endpoint never requires authentication.
        """
        set_cache_ready(False)

        # /satellite/health - No Authorization header, should return 200
        response = client.get("/satellite/health")
        assert response.status_code == 200

        # Even with invalid header, should still work
        response = client.get("/satellite/health", headers={"Authorization": "invalid"})
        assert response.status_code == 200

        # /satellite/health/ready - should return 503, not 401
        response = client.get("/satellite/health/ready")
        assert response.status_code == 503

        response = client.get(
            "/satellite/health/ready", headers={"Authorization": "invalid"}
        )
        assert response.status_code == 503

    def test_readiness_state_transition(self, client: TestClient) -> None:
        """Readiness status changes as cache state transitions."""
        # Initially not ready
        set_cache_ready(False)
        response = client.get("/satellite/health/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "warming"

        # Transition to ready
        set_cache_ready(True)
        response = client.get("/satellite/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

        # Transition back to not ready (edge case)
        set_cache_ready(False)
        response = client.get("/satellite/health/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "warming"

    def test_liveness_stable_during_state_transitions(self, client: TestClient) -> None:
        """Liveness probe (/satellite/health) always returns 200 during transitions."""
        # Initially not ready
        set_cache_ready(False)
        response = client.get("/satellite/health")
        assert response.status_code == 200

        # Transition to ready
        set_cache_ready(True)
        response = client.get("/satellite/health")
        assert response.status_code == 200

        # Transition back
        set_cache_ready(False)
        response = client.get("/satellite/health")
        assert response.status_code == 200
