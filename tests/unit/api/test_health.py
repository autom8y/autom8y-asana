"""Tests for health check endpoints (three-tier platform contract).

Tests cover:
- GET /health returns 200 always (liveness probe, no I/O)
- GET /ready returns 200 or 503 based on cache warmth (readiness probe)
- GET /health/deps returns dependency probe with JWKS and PAT checks
- All responses use the standard contract envelope
- No authentication required on any health endpoint
- No retired status values appear (healthy, not_ready, ready, warming)

Health Contract Envelope:
    {
        "status": "ok" | "degraded" | "unavailable",
        "service": "asana",
        "version": "0.1.0",
        "timestamp": "2026-...",
        "checks": { ... } | null
    }
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.routes.health import (
    is_cache_ready,
    set_cache_ready,
)

# Retired status values that must NEVER appear in responses.
RETIRED_STATUSES = {"healthy", "not_ready", "ready", "warming"}
VALID_STATUSES = {"ok", "degraded", "unavailable"}


def _assert_contract_envelope(data: dict, *, expect_checks: bool = False) -> None:
    """Assert that the response matches the standard health contract envelope."""
    assert data["status"] in VALID_STATUSES, f"Unexpected status: {data['status']}"
    assert data["status"] not in RETIRED_STATUSES
    assert data["service"] == "asana"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data

    if expect_checks:
        assert data["checks"] is not None
        assert isinstance(data["checks"], dict)
    else:
        assert data.get("checks") is None


@pytest.fixture(autouse=True)
def reset_cache_ready():
    """Reset cache ready state before and after each test."""
    set_cache_ready(True)
    yield
    set_cache_ready(True)


# ---- /health (Liveness) ----


class TestLivenessEndpoint:
    """Tests for GET /health -- pure liveness probe."""

    def test_returns_200(self, client: TestClient) -> None:
        """Liveness probe always returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_contract_envelope(self, client: TestClient) -> None:
        """Response matches standard health contract envelope."""
        response = client.get("/health")
        _assert_contract_envelope(response.json(), expect_checks=False)

    def test_status_is_ok(self, client: TestClient) -> None:
        """Liveness status is always 'ok'."""
        response = client.get("/health")
        assert response.json()["status"] == "ok"

    def test_no_checks_field(self, client: TestClient) -> None:
        """Liveness probe has no checks (no I/O)."""
        response = client.get("/health")
        assert response.json()["checks"] is None

    def test_content_type_json(self, client: TestClient) -> None:
        """Response content type is application/json."""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"

    def test_version_semver(self, client: TestClient) -> None:
        """Version follows semver format X.Y.Z."""
        data = client.get("/health").json()
        parts = data["version"].split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    def test_no_auth_required(self, client: TestClient) -> None:
        """No authentication required."""
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/health", headers={"Authorization": "invalid"})
        assert response.status_code == 200

    def test_returns_200_when_cache_not_ready(self, client: TestClient) -> None:
        """Liveness returns 200 even during cache warmup."""
        set_cache_ready(False)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_stable_during_state_transitions(self, client: TestClient) -> None:
        """Liveness always returns 200 regardless of cache state transitions."""
        for state in [False, True, False]:
            set_cache_ready(state)
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    def test_no_retired_status_values(self, client: TestClient) -> None:
        """Ensure no retired status values appear."""
        for state in [True, False]:
            set_cache_ready(state)
            data = client.get("/health").json()
            assert data["status"] not in RETIRED_STATUSES

    def test_satellite_routes_removed(self, client: TestClient) -> None:
        """Old /satellite/health route no longer exists."""
        response = client.get(
            "/satellite/health",
            headers={"Authorization": "Bearer test.token"},
        )
        assert response.status_code == 404


# ---- /ready (Readiness) ----


class TestReadinessEndpoint:
    """Tests for GET /ready -- readiness probe, checks cache warmth."""

    def test_returns_200_when_cache_ready(self, client: TestClient) -> None:
        """Returns 200 when cache is warm."""
        set_cache_ready(True)
        response = client.get("/ready")
        assert response.status_code == 200

    def test_returns_503_when_cache_not_ready(self, client: TestClient) -> None:
        """Returns 503 during cache warmup."""
        set_cache_ready(False)
        response = client.get("/ready")
        assert response.status_code == 503

    def test_contract_envelope_when_ready(self, client: TestClient) -> None:
        """Response matches contract envelope when cache is ready."""
        set_cache_ready(True)
        _assert_contract_envelope(client.get("/ready").json(), expect_checks=True)

    def test_contract_envelope_when_not_ready(self, client: TestClient) -> None:
        """Response matches contract envelope during warmup."""
        set_cache_ready(False)
        _assert_contract_envelope(client.get("/ready").json(), expect_checks=True)

    def test_status_ok_or_degraded_when_cache_ready(self, client: TestClient) -> None:
        """Status is 'ok' or 'degraded' when cache is warm.

        After SP-L3-1 D4, /ready includes JWKS and bot_pat deep checks.
        In test environments without JWKS/PAT, those checks report degraded,
        so overall status is 'degraded'.  In production with real JWKS/PAT,
        status is 'ok'.  Either way, HTTP status is 200 (not 503).
        """
        set_cache_ready(True)
        data = client.get("/ready").json()
        assert data["status"] in ("ok", "degraded")

    def test_status_unavailable_when_not_ready(self, client: TestClient) -> None:
        """Status is 'unavailable' during cache warmup."""
        set_cache_ready(False)
        assert client.get("/ready").json()["status"] == "unavailable"

    def test_cache_check_present(self, client: TestClient) -> None:
        """Checks dict contains 'cache' key."""
        set_cache_ready(True)
        data = client.get("/ready").json()
        assert "cache" in data["checks"]

    def test_cache_check_ok_when_ready(self, client: TestClient) -> None:
        """Cache check status is 'ok' when cache is warm."""
        set_cache_ready(True)
        cache_check = client.get("/ready").json()["checks"]["cache"]
        assert cache_check["status"] == "ok"

    def test_cache_check_unavailable_when_not_ready(self, client: TestClient) -> None:
        """Cache check status is 'unavailable' during warmup."""
        set_cache_ready(False)
        cache_check = client.get("/ready").json()["checks"]["cache"]
        assert cache_check["status"] == "unavailable"

    def test_no_auth_required(self, client: TestClient) -> None:
        """No authentication required."""
        set_cache_ready(False)
        response = client.get("/ready")
        assert response.status_code == 503  # Not 401

        response = client.get("/ready", headers={"Authorization": "invalid"})
        assert response.status_code == 503

    def test_state_transition(self, client: TestClient) -> None:
        """Readiness status follows cache state transitions.

        After SP-L3-1 D4, /ready includes JWKS and bot_pat deep checks.
        When cache is ready, status may be 'ok' or 'degraded' depending
        on JWKS/PAT availability in the test environment.  Either way,
        HTTP 200 (not 503).  When cache is not ready -> 503 unavailable.
        """
        set_cache_ready(False)
        assert client.get("/ready").status_code == 503
        assert client.get("/ready").json()["status"] == "unavailable"

        set_cache_ready(True)
        assert client.get("/ready").status_code == 200
        assert client.get("/ready").json()["status"] in ("ok", "degraded")

        set_cache_ready(False)
        assert client.get("/ready").status_code == 503
        assert client.get("/ready").json()["status"] == "unavailable"

    def test_no_retired_status_values(self, client: TestClient) -> None:
        """Ensure no retired status values (warming, ready, etc.) appear."""
        for state in [True, False]:
            set_cache_ready(state)
            data = client.get("/ready").json()
            assert data["status"] not in RETIRED_STATUSES

    def test_satellite_ready_route_removed(self, client: TestClient) -> None:
        """Old /satellite/health/ready route no longer exists."""
        response = client.get(
            "/satellite/health/ready",
            headers={"Authorization": "Bearer test.token"},
        )
        assert response.status_code == 404


# ---- /health/deps (Dependency Probe) ----


@pytest.mark.slow
class TestDepsEndpoint:
    """Tests for GET /health/deps -- dependency probe."""

    def test_returns_expected_check_keys(self, client: TestClient) -> None:
        """Response contains jwks and bot_pat checks."""
        data = client.get("/health/deps").json()
        _assert_contract_envelope(data, expect_checks=True)
        assert "jwks" in data["checks"]
        assert "bot_pat" in data["checks"]

    def test_no_auth_required(self, client: TestClient) -> None:
        """Does not require authentication."""
        response = client.get("/health/deps")
        assert response.status_code in (200, 503)

    def test_bot_pat_not_configured(self, client: TestClient) -> None:
        """Reports degraded when bot PAT is not configured."""
        with patch.dict(os.environ, {"ASANA_PAT": ""}, clear=False):
            data = client.get("/health/deps").json()
            pat_check = data["checks"]["bot_pat"]
            assert pat_check["status"] == "degraded"
            assert pat_check["detail"]["configured"] is False

    def test_bot_pat_configured(self, client: TestClient) -> None:
        """Reports ok when bot PAT is configured."""
        with patch.dict(os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False):
            data = client.get("/health/deps").json()
            pat_check = data["checks"]["bot_pat"]
            assert pat_check["status"] == "ok"
            assert pat_check["detail"]["configured"] is True

    def test_all_ok_returns_200(self, client: TestClient) -> None:
        """Returns 200 with status 'ok' when all dependencies healthy."""
        mock_response = httpx.Response(
            200,
            json={"keys": [{"kid": "test-key", "kty": "RSA"}]},
        )
        with patch.dict(os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False):
            with patch("autom8_asana.api.routes.health.Autom8yHttpClient") as mock_cls:
                mock_raw_client = AsyncMock()
                mock_raw_client.get = AsyncMock(return_value=mock_response)
                raw_ctx = AsyncMock()
                raw_ctx.__aenter__ = AsyncMock(return_value=mock_raw_client)
                raw_ctx.__aexit__ = AsyncMock(return_value=None)
                mock_http_client = AsyncMock()
                mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
                mock_http_client.__aexit__ = AsyncMock(return_value=None)
                mock_http_client.raw = MagicMock(return_value=raw_ctx)
                mock_cls.return_value = mock_http_client
                response = client.get("/health/deps")
                data = response.json()

                assert response.status_code == 200
                assert data["status"] == "ok"
                assert data["checks"]["jwks"]["status"] == "ok"
                assert data["checks"]["bot_pat"]["status"] == "ok"

    def test_jwks_timeout_returns_degraded(self, client: TestClient) -> None:
        """Returns 'degraded' when JWKS times out."""
        with patch.dict(os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False):
            with patch("autom8_asana.api.routes.health.Autom8yHttpClient") as mock_cls:
                mock_raw_client = AsyncMock()
                mock_raw_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
                raw_ctx = AsyncMock()
                raw_ctx.__aenter__ = AsyncMock(return_value=mock_raw_client)
                raw_ctx.__aexit__ = AsyncMock(return_value=None)
                mock_http_client = AsyncMock()
                mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
                mock_http_client.__aexit__ = AsyncMock(return_value=None)
                mock_http_client.raw = MagicMock(return_value=raw_ctx)
                mock_cls.return_value = mock_http_client
                response = client.get("/health/deps")
                data = response.json()

                assert response.status_code == 200  # degraded = 200
                assert data["status"] == "degraded"
                assert data["checks"]["jwks"]["status"] == "degraded"
                assert data["checks"]["jwks"]["detail"]["error"] == "timeout"

    def test_jwks_connection_error_returns_degraded(self, client: TestClient) -> None:
        """Returns 'degraded' when JWKS connection fails."""
        with patch.dict(os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False):
            with patch("autom8_asana.api.routes.health.Autom8yHttpClient") as mock_cls:
                mock_raw_client = AsyncMock()
                mock_raw_client.get = AsyncMock(side_effect=httpx.ConnectError("connection failed"))
                raw_ctx = AsyncMock()
                raw_ctx.__aenter__ = AsyncMock(return_value=mock_raw_client)
                raw_ctx.__aexit__ = AsyncMock(return_value=None)
                mock_http_client = AsyncMock()
                mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
                mock_http_client.__aexit__ = AsyncMock(return_value=None)
                mock_http_client.raw = MagicMock(return_value=raw_ctx)
                mock_cls.return_value = mock_http_client
                response = client.get("/health/deps")
                data = response.json()

                assert response.status_code == 200
                assert data["checks"]["jwks"]["status"] == "degraded"
                assert data["checks"]["jwks"]["detail"]["error"] == "connection_error"

    def test_jwks_invalid_response(self, client: TestClient) -> None:
        """Reports degraded when JWKS response is invalid."""
        mock_response = httpx.Response(200, json={"error": "not a jwks"})
        with patch.dict(os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False):
            with patch("autom8_asana.api.routes.health.Autom8yHttpClient") as mock_cls:
                mock_raw_client = AsyncMock()
                mock_raw_client.get = AsyncMock(return_value=mock_response)
                raw_ctx = AsyncMock()
                raw_ctx.__aenter__ = AsyncMock(return_value=mock_raw_client)
                raw_ctx.__aexit__ = AsyncMock(return_value=None)
                mock_http_client = AsyncMock()
                mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
                mock_http_client.__aexit__ = AsyncMock(return_value=None)
                mock_http_client.raw = MagicMock(return_value=raw_ctx)
                mock_cls.return_value = mock_http_client
                data = client.get("/health/deps").json()
                assert data["checks"]["jwks"]["status"] == "degraded"
                assert data["checks"]["jwks"]["detail"]["error"] == "invalid_response"

    def test_both_deps_failing_returns_degraded(self, client: TestClient) -> None:
        """Returns 'degraded' when both dependencies fail."""
        with patch.dict(os.environ, {"ASANA_PAT": ""}, clear=False):
            with patch("autom8_asana.api.routes.health.Autom8yHttpClient") as mock_cls:
                mock_raw_client = AsyncMock()
                mock_raw_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
                raw_ctx = AsyncMock()
                raw_ctx.__aenter__ = AsyncMock(return_value=mock_raw_client)
                raw_ctx.__aexit__ = AsyncMock(return_value=None)
                mock_http_client = AsyncMock()
                mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
                mock_http_client.__aexit__ = AsyncMock(return_value=None)
                mock_http_client.raw = MagicMock(return_value=raw_ctx)
                mock_cls.return_value = mock_http_client
                response = client.get("/health/deps")
                data = response.json()

                assert response.status_code == 200  # degraded = 200
                assert data["status"] == "degraded"

    def test_latency_reported_for_jwks(self, client: TestClient) -> None:
        """JWKS check includes latency_ms."""
        mock_response = httpx.Response(
            200,
            json={"keys": [{"kid": "test-key", "kty": "RSA"}]},
        )
        with patch("autom8_asana.api.routes.health.Autom8yHttpClient") as mock_cls:
            mock_raw_client = AsyncMock()
            mock_raw_client.get = AsyncMock(return_value=mock_response)
            raw_ctx = AsyncMock()
            raw_ctx.__aenter__ = AsyncMock(return_value=mock_raw_client)
            raw_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_http_client = AsyncMock()
            mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_http_client.__aexit__ = AsyncMock(return_value=None)
            mock_http_client.raw = MagicMock(return_value=raw_ctx)
            mock_cls.return_value = mock_http_client
            data = client.get("/health/deps").json()
            assert data["checks"]["jwks"]["latency_ms"] is not None
            assert isinstance(data["checks"]["jwks"]["latency_ms"], float)

    def test_no_retired_status_values(self, client: TestClient) -> None:
        """Ensure no retired status values appear in deps response."""
        data = client.get("/health/deps").json()
        assert data["status"] not in RETIRED_STATUSES
        for check in data["checks"].values():
            assert check["status"] not in RETIRED_STATUSES

    def test_satellite_s2s_route_removed(self, client: TestClient) -> None:
        """Old /satellite/health/s2s route no longer exists."""
        response = client.get(
            "/satellite/health/s2s",
            headers={"Authorization": "Bearer test.token"},
        )
        assert response.status_code == 404


# ---- Cache state helpers ----


class TestDeepReadinessChecks:
    """Verify /ready includes deep connectivity checks (SP-L3-1 D4).

    Tests that JWKS and bot_pat checks were promoted from /health/deps
    to /ready so that false-healthy scenarios are caught by the ALB
    readiness probe.
    """

    def test_ready_includes_jwks_check(self, client: TestClient) -> None:
        """JWKS check is now present in /ready (promoted from /health/deps)."""
        data = client.get("/ready").json()
        assert "jwks" in data["checks"], "JWKS check missing from /ready (SP-L3-1)"

    def test_ready_includes_bot_pat_check(self, client: TestClient) -> None:
        """Bot PAT check is now present in /ready (promoted from /health/deps)."""
        data = client.get("/ready").json()
        assert "bot_pat" in data["checks"], "bot_pat check missing from /ready (SP-L3-1)"

    def test_ready_bot_pat_degraded_when_missing(self, client: TestClient) -> None:
        """Bot PAT not configured -> degraded status in /ready."""
        with patch.dict(os.environ, {"ASANA_PAT": ""}, clear=False):
            data = client.get("/ready").json()
            assert data["checks"]["bot_pat"]["status"] == "degraded"
            assert data["checks"]["bot_pat"]["detail"]["configured"] is False

    def test_ready_bot_pat_ok_when_configured(self, client: TestClient) -> None:
        """Bot PAT configured -> ok status in /ready."""
        with patch.dict(os.environ, {"ASANA_PAT": "0/test_pat_value_long_enough"}, clear=False):
            data = client.get("/ready").json()
            assert data["checks"]["bot_pat"]["status"] == "ok"

    def test_ready_jwks_degraded_on_timeout(self, client: TestClient) -> None:
        """JWKS timeout -> degraded status in /ready."""
        with patch("autom8_asana.api.routes.health.Autom8yHttpClient") as mock_cls:
            mock_raw_client = AsyncMock()
            mock_raw_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            raw_ctx = AsyncMock()
            raw_ctx.__aenter__ = AsyncMock(return_value=mock_raw_client)
            raw_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_http_client = AsyncMock()
            mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_http_client.__aexit__ = AsyncMock(return_value=None)
            mock_http_client.raw = MagicMock(return_value=raw_ctx)
            mock_cls.return_value = mock_http_client
            data = client.get("/ready").json()
            assert data["checks"]["jwks"]["status"] == "degraded"

    def test_ready_returns_503_when_cache_not_ready_and_deps_degraded(
        self, client: TestClient
    ) -> None:
        """Cache unavailable dominates even when JWKS/PAT are degraded -> 503."""
        set_cache_ready(False)
        with patch.dict(os.environ, {"ASANA_PAT": ""}, clear=False):
            response = client.get("/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unavailable"


class TestCacheStateHelpers:
    """Tests for set_cache_ready() and is_cache_ready() helpers."""

    def test_set_and_get_state(self) -> None:
        """set_cache_ready() correctly updates and is_cache_ready() reads."""
        set_cache_ready(False)
        assert is_cache_ready() is False

        set_cache_ready(True)
        assert is_cache_ready() is True

        set_cache_ready(False)
        assert is_cache_ready() is False
