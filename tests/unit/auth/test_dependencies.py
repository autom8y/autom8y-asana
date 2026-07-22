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
from autom8y_auth import ServiceClaims
from pydantic import ValidationError

from autom8_asana.api.dependencies import (
    AuthContext,
    _extract_bearer_token,
    get_auth_context,
)
from autom8_asana.api.exception_types import ApiAuthError, ApiServiceUnavailableError
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

    async def test_extract_valid_token(self) -> None:
        """Extracts token from valid Bearer header."""
        # Arrange
        auth_header = "Bearer 0/1234567890abcdef1234567890"

        # Act
        result = await _extract_bearer_token(authorization=auth_header)

        # Assert
        assert result == "0/1234567890abcdef1234567890"

    async def test_missing_header_raises_401(self) -> None:
        """Raises ApiAuthError when Authorization header is missing."""
        # Act & Assert
        with pytest.raises(ApiAuthError) as exc_info:
            await _extract_bearer_token(authorization=None)

        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "MISSING_AUTH"

    async def test_wrong_scheme_raises_401(self) -> None:
        """Raises ApiAuthError when scheme is not Bearer."""
        # Act & Assert
        with pytest.raises(ApiAuthError) as exc_info:
            await _extract_bearer_token(authorization="Basic dXNlcjpwYXNz")

        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "INVALID_SCHEME"

    async def test_empty_token_raises_401(self) -> None:
        """Raises ApiAuthError when token is empty."""
        # Act & Assert
        with pytest.raises(ApiAuthError) as exc_info:
            await _extract_bearer_token(authorization="Bearer ")

        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "MISSING_TOKEN"

    async def test_short_token_raises_401(self) -> None:
        """Raises ApiAuthError when token is too short."""
        # Act & Assert
        with pytest.raises(ApiAuthError) as exc_info:
            await _extract_bearer_token(authorization="Bearer short")

        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "INVALID_TOKEN"


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

    async def test_jwt_validated_and_bot_pat_used(self, monkeypatch: pytest.MonkeyPatch) -> None:
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

    async def test_jwt_validation_failure_returns_401(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invalid JWT returns 401 ApiAuthError."""
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
            with pytest.raises(ApiAuthError) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 401
            assert exc_info.value.code == "TOKEN_EXPIRED"

    async def test_missing_bot_pat_returns_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing bot PAT returns 503 ApiServiceUnavailableError."""
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
            with pytest.raises(ApiServiceUnavailableError) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 503
            assert exc_info.value.code == "S2S_NOT_CONFIGURED"


class TestGetAuthContextCircuitOpen:
    """Test CircuitOpenError handling in get_auth_context."""

    async def test_circuit_open_returns_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CircuitOpenError maps to ApiServiceUnavailableError (503)."""
        mock_request = MagicMock()
        mock_request.state.request_id = "test-circuit-open"
        jwt_token = "header.payload.signature"

        from autom8y_auth import CircuitOpenError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=CircuitOpenError("Circuit breaker is open (failed 5 times)"),
        ):
            with pytest.raises(ApiServiceUnavailableError) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 503
            assert exc_info.value.code == "CIRCUIT_OPEN"

    async def test_jwks_fetch_error_returns_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """JWKSFetchError (transient) maps to ApiServiceUnavailableError (503)."""
        mock_request = MagicMock()
        mock_request.state.request_id = "test-jwks-fetch-error"
        jwt_token = "header.payload.signature"

        from autom8y_auth import JWKSFetchError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=JWKSFetchError("JWKS endpoint unreachable"),
        ):
            with pytest.raises(ApiServiceUnavailableError) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 503
            assert exc_info.value.code == "JWKS_FETCH_ERROR"

    async def test_permanent_error_returns_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """PermanentAuthError subclasses map to ApiAuthError (401)."""
        mock_request = MagicMock()
        mock_request.state.request_id = "test-permanent-error"
        jwt_token = "header.payload.signature"

        from autom8y_auth import InvalidSignatureError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=InvalidSignatureError("Signature verification failed"),
        ):
            with pytest.raises(ApiAuthError) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 401
            assert exc_info.value.code == "INVALID_SIGNATURE"


class TestBotPatNeverLogged:
    """Test that bot PAT values never appear in logs or errors."""

    async def test_pat_not_in_error_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
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
            except ApiServiceUnavailableError as e:
                error_code = e.code
                error_message = e.message

        # Assert - error message should not contain PAT format
        assert "0/" not in error_message
        assert "1/" not in error_message
        # But should contain helpful error info
        assert error_code == "S2S_NOT_CONFIGURED"


class TestGetAuthContextClaimsValidationError:
    """Fail-clean on an unrecognized/malformed token species (operator ruling R21, Lane-1).

    A JWT can clear JWKS/signature/expiry/audience yet carry claims that do not
    fit the SDK's ``ServiceClaims`` model (an unrecognized species whose
    ``scope`` claim is the wrong type). ``autom8y_auth`` then raises a pydantic
    ``ValidationError`` from ``ServiceClaims.model_validate`` — a ``ValueError``,
    NOT an ``autom8y_auth.AuthError``. Before this fix that exception escaped the
    except chain in ``get_auth_context`` and surfaced as a 500 via the generic
    handler. It must now be refused cleanly as a 401, WITHOUT widening what is
    accepted (the recognized-service path stays byte-behavior-identical).
    """

    @staticmethod
    def _claims_validation_error() -> ValidationError:
        """Reproduce the exact pydantic ValidationError the SDK raises.

        Mirrors ``ServiceClaims.model_validate`` on an unrecognized species: a
        payload whose ``scope`` claim is a list instead of the declared
        ``str | None``. Building the real SDK error (rather than a synthetic
        stand-in) gives the test teeth — it fails if the SDK ever stops raising
        here or if the guard stops catching pydantic errors.
        """
        try:
            ServiceClaims.model_validate(
                {
                    "sub": "svc",
                    "iss": "https://auth.autom8y.io",
                    "exp": 9999999999,
                    "iat": 1000000000,
                    "scope": ["not", "a", "string"],
                }
            )
        except ValidationError as exc:
            return exc
        raise AssertionError(  # pragma: no cover - guards the fixture premise
            "ServiceClaims.model_validate did not raise on a list-typed scope"
        )

    async def test_unrecognized_species_returns_401_logged_as_auth_failure(self) -> None:
        """Malformed-claims JWT -> clean 401 auth refusal, never an escaped 500.

        Two-sided reject leg: asserts the pydantic ``ValidationError`` is
        converted to ``ApiAuthError`` (401 + ``WWW-Authenticate: Bearer``) and
        that it never propagates as a raw ``ValidationError`` (which FastAPI's
        generic handler would render as a 500). Also asserts the refusal is
        logged as an auth failure (``s2s_jwt_validation_failed``), not a server
        error (``logger.exception``).
        """
        # Arrange
        mock_request = MagicMock()
        mock_request.state.request_id = "test-claims-mismatch"
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=self._claims_validation_error(),
        ):
            with patch("autom8_asana.api.dependencies.logger") as mock_logger:
                # Act & Assert - refused as a typed 401, not an escaped 500
                with pytest.raises(ApiAuthError) as exc_info:
                    await get_auth_context(request=mock_request, token=jwt_token)

        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "INVALID_TOKEN"
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

        # Logged as an auth failure, not a server error.
        warning_events = [call.args[0] for call in mock_logger.warning.call_args_list if call.args]
        assert "s2s_jwt_validation_failed" in warning_events
        mock_logger.exception.assert_not_called()

    async def test_recognized_service_token_still_validates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FENCE: the fail-clean guard must NOT change what is accepted.

        Two-sided accept leg: a recognized service token continues to validate
        and yields JWT-mode ``AuthContext`` backed by the bot PAT — identical to
        behavior before the guard was added.
        """
        # Arrange
        mock_request = MagicMock()
        mock_request.state.request_id = "test-recognized-service"
        jwt_token = "header.payload.signature"
        bot_pat = "0/bot_pat_from_env_here123456"

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
            result = await get_auth_context(request=mock_request, token=jwt_token)

        # Assert - accepted path unchanged
        assert result.mode == AuthMode.JWT
        assert result.asana_pat == bot_pat
        assert result.caller_service == "autom8_data"
