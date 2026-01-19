"""Tests for dual_mode.py token detection.

Per TDD-S2S-001 Section 12.1:
- Token detection for various formats
- JWT detection (exactly 2 dots)
- PAT detection (0 dots, Asana format)
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from autom8_asana.auth.dual_mode import AuthMode, detect_token_type, get_auth_mode


class TestDetectTokenType:
    """Test token type detection via dot counting."""

    def test_detect_jwt_with_two_dots(self) -> None:
        """JWT tokens have exactly 2 dots (header.payload.signature)."""
        # Arrange
        jwt_token = (
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature"
        )

        # Act
        result = detect_token_type(jwt_token)

        # Assert
        assert result == AuthMode.JWT

    def test_detect_pat_with_zero_dots(self) -> None:
        """Asana PATs have 0 dots (format: 0/xxxxxxxx or 1/xxxxxxxx)."""
        # Arrange
        pat_token = "0/1234567890abcdef1234567890abcdef"

        # Act
        result = detect_token_type(pat_token)

        # Assert
        assert result == AuthMode.PAT

    def test_detect_pat_with_slash_prefix_1(self) -> None:
        """Asana PATs with 1/ prefix are detected as PAT."""
        # Arrange
        pat_token = "1/abcdef1234567890abcdef1234567890"

        # Act
        result = detect_token_type(pat_token)

        # Assert
        assert result == AuthMode.PAT

    def test_detect_pat_with_one_dot(self) -> None:
        """Tokens with 1 dot are treated as PAT (not a valid JWT)."""
        # Arrange
        malformed_token = "header.payload"

        # Act
        result = detect_token_type(malformed_token)

        # Assert
        assert result == AuthMode.PAT

    def test_detect_pat_with_three_dots(self) -> None:
        """Tokens with 3+ dots are treated as PAT (not a valid JWT)."""
        # Arrange
        malformed_token = "a.b.c.d"

        # Act
        result = detect_token_type(malformed_token)

        # Assert
        assert result == AuthMode.PAT

    def test_detect_pat_empty_string(self) -> None:
        """Empty tokens are treated as PAT (will fail validation later)."""
        # Arrange
        empty_token = ""

        # Act
        result = detect_token_type(empty_token)

        # Assert
        assert result == AuthMode.PAT

    def test_detect_jwt_minimal(self) -> None:
        """Minimal JWT format with exactly 2 dots is detected as JWT."""
        # Arrange
        minimal_jwt = "a.b.c"

        # Act
        result = detect_token_type(minimal_jwt)

        # Assert
        assert result == AuthMode.JWT

    def test_detect_jwt_with_empty_signature(self) -> None:
        """JWT with empty signature (2 dots) is still detected as JWT."""
        # Arrange
        jwt_no_sig = "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxMjM0NTY3ODkwIn0."

        # Act
        result = detect_token_type(jwt_no_sig)

        # Assert
        assert result == AuthMode.JWT


class TestAuthMode:
    """Test AuthMode enum values."""

    def test_jwt_value(self) -> None:
        """AuthMode.JWT has string value 'jwt'."""
        assert AuthMode.JWT.value == "jwt"

    def test_pat_value(self) -> None:
        """AuthMode.PAT has string value 'pat'."""
        assert AuthMode.PAT.value == "pat"

    def test_auth_mode_is_string_enum(self) -> None:
        """AuthMode values can be used as strings."""
        assert AuthMode.JWT == "jwt"
        assert AuthMode.PAT == "pat"


class TestGetAuthMode:
    """Tests for get_auth_mode() header extraction and validation."""

    @pytest.mark.asyncio
    async def test_missing_authorization_header_raises_401(self) -> None:
        """Missing Authorization header should raise 401 MISSING_AUTH."""
        with pytest.raises(HTTPException) as exc_info:
            await get_auth_mode(authorization=None)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "MISSING_AUTH"
        assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.asyncio
    async def test_invalid_scheme_raises_401(self) -> None:
        """Non-Bearer scheme should raise 401 INVALID_SCHEME."""
        with pytest.raises(HTTPException) as exc_info:
            await get_auth_mode(authorization="Basic dXNlcjpwYXNz")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "INVALID_SCHEME"
        assert "Bearer scheme required" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_token_too_short_raises_401(self) -> None:
        """Token shorter than 10 characters should raise 401 INVALID_TOKEN."""
        with pytest.raises(HTTPException) as exc_info:
            await get_auth_mode(authorization="Bearer abc")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "INVALID_TOKEN"
        assert "too short" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_valid_jwt_returns_jwt_mode(self) -> None:
        """Valid JWT token should return (AuthMode.JWT, token)."""
        jwt_token = (
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature"
        )
        auth_mode, token = await get_auth_mode(authorization=f"Bearer {jwt_token}")

        assert auth_mode == AuthMode.JWT
        assert token == jwt_token

    @pytest.mark.asyncio
    async def test_valid_pat_returns_pat_mode(self) -> None:
        """Valid PAT token should return (AuthMode.PAT, token)."""
        pat_token = "0/1234567890abcdef1234567890abcdef"
        auth_mode, token = await get_auth_mode(authorization=f"Bearer {pat_token}")

        assert auth_mode == AuthMode.PAT
        assert token == pat_token

    @pytest.mark.asyncio
    async def test_bearer_case_sensitive(self) -> None:
        """Bearer prefix must be exact case (Bearer, not bearer)."""
        with pytest.raises(HTTPException) as exc_info:
            await get_auth_mode(authorization="bearer 0/1234567890abcdef")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "INVALID_SCHEME"

    @pytest.mark.asyncio
    async def test_token_extraction_removes_bearer_prefix(self) -> None:
        """Token extraction should remove exactly 'Bearer ' (7 chars)."""
        pat_token = "0/1234567890abcdef1234567890"
        _, token = await get_auth_mode(authorization=f"Bearer {pat_token}")

        assert token == pat_token
        assert not token.startswith("Bearer")

    @pytest.mark.asyncio
    async def test_minimum_valid_token_length(self) -> None:
        """Token of exactly 10 characters should be accepted."""
        min_token = "0123456789"  # Exactly 10 chars
        auth_mode, token = await get_auth_mode(authorization=f"Bearer {min_token}")

        assert auth_mode == AuthMode.PAT  # No dots = PAT
        assert token == min_token
