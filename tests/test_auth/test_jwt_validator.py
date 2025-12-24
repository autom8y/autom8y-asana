"""Tests for jwt_validator.py SDK integration.

Per TDD-S2S-001 Section 12.1:
- SDK integration
- Service token validation
- Error handling for various failure modes

Note: These tests use the real autom8y-auth SDK since it's installed.
The SDK mocks its own JWKS client internally for testability.
"""

from __future__ import annotations

from typing import Generator

import pytest

from autom8_asana.auth.jwt_validator import reset_auth_client


@pytest.fixture(autouse=True)
def reset_client() -> Generator[None, None, None]:
    """Reset the auth client singleton before and after each test."""
    reset_auth_client()
    yield
    reset_auth_client()


class TestResetAuthClient:
    """Test auth client singleton reset."""

    def test_reset_clears_singleton(self) -> None:
        """Resetting client clears the singleton."""
        # This test verifies the reset function works without errors
        reset_auth_client()
        reset_auth_client()  # Should be idempotent
        # No assertion needed - just verify no error is raised

    def test_reset_is_idempotent(self) -> None:
        """Reset can be called multiple times safely."""
        for _ in range(5):
            reset_auth_client()
        # Should complete without error


class TestValidateServiceTokenIntegration:
    """Test JWT validation integration with SDK.

    Note: These tests require the autom8y-auth SDK to be installed.
    Full validation requires a JWKS endpoint, so these tests verify
    error handling when JWKS is not available.
    """

    @pytest.mark.asyncio
    async def test_validate_invalid_token_format(self) -> None:
        """Invalid token format raises error."""
        from autom8_asana.auth.jwt_validator import validate_service_token
        from autom8y_auth import AuthError

        # A token with 2 dots but invalid content should fail
        with pytest.raises(AuthError):
            await validate_service_token("not.a.jwt")

    @pytest.mark.asyncio
    async def test_validate_malformed_jwt(self) -> None:
        """Malformed JWT raises InvalidTokenError."""
        from autom8_asana.auth.jwt_validator import validate_service_token
        from autom8y_auth import InvalidTokenError

        # Base64-looking but invalid JWT
        with pytest.raises(InvalidTokenError):
            await validate_service_token("eyJhbGciOiJub25lIn0.notvalid.signature")
