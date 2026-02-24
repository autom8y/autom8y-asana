"""Integration tests for dual-mode authentication flow.

Per TDD-S2S-001 Section 12.2:
- Valid JWT from auth service accepted
- Invalid JWT returns 401
- PAT pass-through continues to work
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from autom8_asana.api.dependencies import (
    AuthContextDep,  # noqa: TC001 — FastAPI resolves at runtime
)
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def reset_singletons() -> Generator[None, None, None]:
    """Reset singletons before and after each test."""
    clear_bot_pat_cache()
    reset_auth_client()
    yield
    clear_bot_pat_cache()
    reset_auth_client()


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with auth dependency."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint(auth: AuthContextDep) -> dict:
        """Test endpoint that requires auth."""
        return {
            "mode": auth.mode.value,
            "caller_service": auth.caller_service,
            # Never return the PAT itself in a real endpoint
            "has_pat": len(auth.asana_pat) > 0,
        }

    # Add request_id to request.state (normally done by middleware)
    @app.middleware("http")
    async def add_request_id(request, call_next):
        request.state.request_id = "test-request-id"
        return await call_next(request)

    return app


class TestPATPassThrough:
    """Test PAT pass-through authentication (backward compatibility)."""

    def test_pat_accepted_and_passed_through(self, app: FastAPI) -> None:
        """PAT tokens are accepted and passed through unchanged."""
        # Arrange
        client = TestClient(app)
        pat_token = "0/1234567890abcdef1234567890"

        # Act
        response = client.get("/test", headers={"Authorization": f"Bearer {pat_token}"})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "pat"
        assert data["caller_service"] is None
        assert data["has_pat"] is True

    def test_pat_with_1_prefix_accepted(self, app: FastAPI) -> None:
        """PAT tokens with 1/ prefix are accepted."""
        # Arrange
        client = TestClient(app)
        pat_token = "1/abcdef1234567890abcdef1234"

        # Act
        response = client.get("/test", headers={"Authorization": f"Bearer {pat_token}"})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "pat"


class TestJWTMode:
    """Test JWT authentication (S2S mode)."""

    def test_valid_jwt_accepted(
        self, app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valid JWT tokens are accepted and bot PAT is used."""
        # Arrange
        client = TestClient(app)
        jwt_token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhdXRvbTh9.sig"
        bot_pat = "0/bot_pat_for_s2s_requests12345"

        monkeypatch.setenv("ASANA_PAT", bot_pat)
        clear_bot_pat_cache()

        mock_claims = MagicMock()
        mock_claims.service_name = "autom8_data"
        mock_claims.scope = "multi-tenant"

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            return_value=mock_claims,
        ):
            # Act
            response = client.get(
                "/test", headers={"Authorization": f"Bearer {jwt_token}"}
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "jwt"
        assert data["caller_service"] == "autom8_data"
        assert data["has_pat"] is True

    def test_expired_jwt_returns_401(
        self, app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Expired JWT tokens return 401."""
        # Arrange
        client = TestClient(app)
        jwt_token = "expired.jwt.token"

        from autom8y_auth import TokenExpiredError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=TokenExpiredError("Token has expired"),
        ):
            # Act
            response = client.get(
                "/test", headers={"Authorization": f"Bearer {jwt_token}"}
            )

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "TOKEN_EXPIRED"

    def test_invalid_signature_returns_401(
        self, app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """JWT with invalid signature returns 401."""
        # Arrange
        client = TestClient(app)
        jwt_token = "bad.signature.token"

        from autom8y_auth import InvalidSignatureError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=InvalidSignatureError("Signature verification failed"),
        ):
            # Act
            response = client.get(
                "/test", headers={"Authorization": f"Bearer {jwt_token}"}
            )

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "INVALID_SIGNATURE"

    def test_missing_bot_pat_returns_503(
        self, app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing bot PAT returns 503."""
        # Arrange
        client = TestClient(app)
        jwt_token = "valid.jwt.token"

        monkeypatch.delenv("ASANA_PAT", raising=False)
        clear_bot_pat_cache()

        mock_claims = MagicMock()
        mock_claims.service_name = "autom8_data"
        mock_claims.scope = None

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            return_value=mock_claims,
        ):
            # Act
            response = client.get(
                "/test", headers={"Authorization": f"Bearer {jwt_token}"}
            )

        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "S2S_NOT_CONFIGURED"


class TestMissingAuth:
    """Test missing or invalid Authorization headers."""

    def test_missing_auth_header_returns_401(self, app: FastAPI) -> None:
        """Missing Authorization header returns 401."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/test")

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "MISSING_AUTH"

    def test_wrong_scheme_returns_401(self, app: FastAPI) -> None:
        """Non-Bearer scheme returns 401."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/test", headers={"Authorization": "Basic dXNlcjpwYXNz"})

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "INVALID_SCHEME"

    def test_empty_token_returns_401(self, app: FastAPI) -> None:
        """Empty Bearer token returns 401."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/test", headers={"Authorization": "Bearer "})

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "MISSING_TOKEN"

    def test_short_token_returns_401(self, app: FastAPI) -> None:
        """Token shorter than 10 chars returns 401."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/test", headers={"Authorization": "Bearer short"})

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "INVALID_TOKEN"


class TestCircuitOpenError:
    """Test CircuitOpenError in JWT path returns 503."""

    def test_circuit_open_returns_503(
        self, app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CircuitOpenError returns 503, not 401."""
        client = TestClient(app)
        jwt_token = "header.payload.signature"

        from autom8y_auth import CircuitOpenError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=CircuitOpenError("Circuit breaker is open"),
        ):
            response = client.get(
                "/test", headers={"Authorization": f"Bearer {jwt_token}"}
            )

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "CIRCUIT_OPEN"

    def test_pat_unaffected_by_circuit_state(self, app: FastAPI) -> None:
        """PAT tokens work regardless of circuit breaker state.

        This test verifies the critical invariant: CircuitOpenError
        can never surface in the PAT path.
        """
        client = TestClient(app)
        pat_token = "0/1234567890abcdef1234567890"

        # Even if we could hypothetically set the circuit to open,
        # PAT path never touches the SDK, so it always succeeds.
        response = client.get("/test", headers={"Authorization": f"Bearer {pat_token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "pat"


class TestTransientVsPermanentErrors:
    """Test that transient errors return 503 and permanent errors return 401."""

    def test_jwks_fetch_error_returns_503(
        self, app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """JWKSFetchError (transient) returns 503."""
        client = TestClient(app)
        jwt_token = "header.payload.signature"

        from autom8y_auth import JWKSFetchError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=JWKSFetchError("JWKS endpoint unreachable"),
        ):
            response = client.get(
                "/test", headers={"Authorization": f"Bearer {jwt_token}"}
            )

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "JWKS_FETCH_ERROR"

    def test_expired_token_returns_401(
        self, app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TokenExpiredError (permanent) returns 401."""
        client = TestClient(app)
        jwt_token = "header.payload.signature"

        from autom8y_auth import TokenExpiredError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=TokenExpiredError("Token has expired"),
        ):
            response = client.get(
                "/test", headers={"Authorization": f"Bearer {jwt_token}"}
            )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "TOKEN_EXPIRED"


class TestBotPatSecurity:
    """Test that bot PAT is never exposed."""

    def test_bot_pat_not_in_response(
        self, app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bot PAT value never appears in response body."""
        # Arrange
        client = TestClient(app)
        jwt_token = "valid.jwt.token"
        bot_pat = "0/secret_bot_pat_12345678901234"

        monkeypatch.setenv("ASANA_PAT", bot_pat)
        clear_bot_pat_cache()

        mock_claims = MagicMock()
        mock_claims.service_name = "autom8_data"
        mock_claims.scope = None

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            return_value=mock_claims,
        ):
            # Act
            response = client.get(
                "/test", headers={"Authorization": f"Bearer {jwt_token}"}
            )

        # Assert
        assert response.status_code == 200
        response_text = response.text
        # Bot PAT should never appear in response
        assert bot_pat not in response_text
        assert "secret_bot_pat" not in response_text

    def test_bot_pat_not_in_error_response(
        self, app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bot PAT value never appears in error responses."""
        # Arrange
        client = TestClient(app)
        jwt_token = "valid.jwt.token"

        # Ensure bot PAT is not set
        monkeypatch.delenv("ASANA_PAT", raising=False)
        clear_bot_pat_cache()

        mock_claims = MagicMock()
        mock_claims.service_name = "autom8_data"
        mock_claims.scope = None

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            return_value=mock_claims,
        ):
            # Act
            response = client.get(
                "/test", headers={"Authorization": f"Bearer {jwt_token}"}
            )

        # Assert
        assert response.status_code == 503
        response_text = response.text
        # No credential patterns should appear
        assert "0/" not in response_text
        assert "1/" not in response_text
