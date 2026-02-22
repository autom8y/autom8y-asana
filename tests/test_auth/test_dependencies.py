"""Tests for api/dependencies.py dual-mode auth.

Per TDD-S2S-001 Section 12.1:
- AuthContext creation for both modes
- PAT pass-through behavior
- JWT validation and bot PAT activation
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from autom8_asana.api.dependencies import (
    AuthContext,
    _extract_bearer_token,
    get_auth_context,
)
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.dual_mode import AuthMode
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


class TestExtractBearerToken:
    """Test bearer token extraction from Authorization header."""

    @pytest.mark.asyncio
    async def test_extract_valid_token(self) -> None:
        """Extracts token from valid Bearer header."""
        # Arrange
        auth_header = "Bearer 0/1234567890abcdef1234567890"

        # Act
        result = await _extract_bearer_token(authorization=auth_header)

        # Assert
        assert result == "0/1234567890abcdef1234567890"

    @pytest.mark.asyncio
    async def test_missing_header_raises_401(self) -> None:
        """Raises 401 when Authorization header is missing."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await _extract_bearer_token(authorization=None)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "MISSING_AUTH"

    @pytest.mark.asyncio
    async def test_wrong_scheme_raises_401(self) -> None:
        """Raises 401 when scheme is not Bearer."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await _extract_bearer_token(authorization="Basic dXNlcjpwYXNz")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "INVALID_SCHEME"

    @pytest.mark.asyncio
    async def test_empty_token_raises_401(self) -> None:
        """Raises 401 when token is empty."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await _extract_bearer_token(authorization="Bearer ")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "MISSING_TOKEN"

    @pytest.mark.asyncio
    async def test_short_token_raises_401(self) -> None:
        """Raises 401 when token is too short."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await _extract_bearer_token(authorization="Bearer short")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "INVALID_TOKEN"


class TestAuthContext:
    """Test AuthContext class."""

    def test_auth_context_pat_mode(self) -> None:
        """AuthContext correctly stores PAT mode attributes."""
        # Arrange & Act
        ctx = AuthContext(
            mode=AuthMode.PAT,
            asana_pat="0/user_pat_token_here12345678",
        )

        # Assert
        assert ctx.mode == AuthMode.PAT
        assert ctx.asana_pat == "0/user_pat_token_here12345678"
        assert ctx.caller_service is None

    def test_auth_context_jwt_mode(self) -> None:
        """AuthContext correctly stores JWT mode attributes."""
        # Arrange & Act
        ctx = AuthContext(
            mode=AuthMode.JWT,
            asana_pat="0/bot_pat_token_here123456789",
            caller_service="autom8_data",
        )

        # Assert
        assert ctx.mode == AuthMode.JWT
        assert ctx.asana_pat == "0/bot_pat_token_here123456789"
        assert ctx.caller_service == "autom8_data"


class TestGetAuthContextPATMode:
    """Test get_auth_context with PAT tokens (pass-through mode)."""

    @pytest.mark.asyncio
    async def test_pat_passthrough(self) -> None:
        """PAT tokens are passed through unchanged."""
        # Arrange
        mock_request = MagicMock()
        mock_request.state.request_id = "test-request-123"
        pat_token = "0/1234567890abcdef1234567890"

        # Act
        result = await get_auth_context(request=mock_request, token=pat_token)

        # Assert
        assert result.mode == AuthMode.PAT
        assert result.asana_pat == pat_token
        assert result.caller_service is None

    @pytest.mark.asyncio
    async def test_pat_with_slash_prefix_1(self) -> None:
        """PAT with 1/ prefix is treated as PAT mode."""
        # Arrange
        mock_request = MagicMock()
        mock_request.state.request_id = "test-request-456"
        pat_token = "1/abcdef1234567890abcdef1234"

        # Act
        result = await get_auth_context(request=mock_request, token=pat_token)

        # Assert
        assert result.mode == AuthMode.PAT
        assert result.asana_pat == pat_token


class TestGetAuthContextJWTMode:
    """Test get_auth_context with JWT tokens (S2S mode)."""

    @pytest.mark.asyncio
    async def test_jwt_validated_and_bot_pat_used(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """JWT tokens are validated and bot PAT is returned."""
        # Arrange
        mock_request = MagicMock()
        mock_request.state.request_id = "test-request-789"
        jwt_token = "header.payload.signature"
        bot_pat = "0/bot_pat_from_env_here123456"

        monkeypatch.setenv("ASANA_PAT", bot_pat)
        clear_bot_pat_cache()

        mock_claims = MagicMock()
        mock_claims.service_name = "autom8_data"
        mock_claims.scope = "multi-tenant"

        # Patch the validate_service_token function where it's imported
        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            return_value=mock_claims,
        ) as mock_validate:
            # Act
            result = await get_auth_context(request=mock_request, token=jwt_token)

        # Assert
        assert result.mode == AuthMode.JWT
        assert result.asana_pat == bot_pat
        assert result.caller_service == "autom8_data"

    @pytest.mark.asyncio
    async def test_jwt_validation_failure_returns_401(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invalid JWT returns 401 error."""
        # Arrange
        mock_request = MagicMock()
        mock_request.state.request_id = "test-request-fail"
        jwt_token = "invalid.jwt.token"

        from autom8y_auth import TokenExpiredError

        # Create the error with code attribute
        error = TokenExpiredError("Token has expired")

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=error,
        ):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail["error"] == "TOKEN_EXPIRED"

    @pytest.mark.asyncio
    async def test_missing_bot_pat_returns_503(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing bot PAT returns 503 error."""
        # Arrange
        mock_request = MagicMock()
        mock_request.state.request_id = "test-request-nobot"
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
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["error"] == "S2S_NOT_CONFIGURED"


class TestGetAuthContextCircuitOpen:
    """Test CircuitOpenError handling in get_auth_context."""

    @pytest.mark.asyncio
    async def test_circuit_open_returns_503(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CircuitOpenError maps to HTTP 503."""
        mock_request = MagicMock()
        mock_request.state.request_id = "test-circuit-open"
        jwt_token = "header.payload.signature"

        from autom8y_auth import CircuitOpenError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=CircuitOpenError("Circuit breaker is open (failed 5 times)"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["error"] == "CIRCUIT_OPEN"

    @pytest.mark.asyncio
    async def test_jwks_fetch_error_returns_503(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """JWKSFetchError (transient) maps to HTTP 503."""
        mock_request = MagicMock()
        mock_request.state.request_id = "test-jwks-fetch-error"
        jwt_token = "header.payload.signature"

        from autom8y_auth import JWKSFetchError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=JWKSFetchError("JWKS endpoint unreachable"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["error"] == "JWKS_FETCH_ERROR"

    @pytest.mark.asyncio
    async def test_permanent_error_returns_401(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PermanentAuthError subclasses map to HTTP 401."""
        mock_request = MagicMock()
        mock_request.state.request_id = "test-permanent-error"
        jwt_token = "header.payload.signature"

        from autom8y_auth import InvalidSignatureError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=InvalidSignatureError("Signature verification failed"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail["error"] == "INVALID_SIGNATURE"


class TestBotPatNeverLogged:
    """Test that bot PAT values never appear in logs or errors."""

    @pytest.mark.asyncio
    async def test_pat_not_in_error_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bot PAT value does not appear in error messages."""
        # Arrange
        mock_request = MagicMock()
        mock_request.state.request_id = "test-request-error"
        jwt_token = "valid.jwt.token"

        # Set PAT and then clear to simulate misconfiguration
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
            try:
                await get_auth_context(request=mock_request, token=jwt_token)
            except HTTPException as e:
                error_detail = str(e.detail)

        # Assert - error message should not contain PAT format
        assert "0/" not in error_detail
        assert "1/" not in error_detail
        # But should contain helpful error info
        assert "S2S_NOT_CONFIGURED" in error_detail
