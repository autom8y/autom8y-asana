"""Tests for dual_mode.py token detection.

Per TDD-S2S-001 Section 12.1:
- Token detection for various formats
- JWT detection (exactly 2 dots)
- PAT detection (0 dots, Asana format)
"""

from __future__ import annotations

import pytest

from autom8_asana.auth.dual_mode import AuthMode, detect_token_type


class TestDetectTokenType:
    """Test token type detection via dot counting."""

    def test_detect_jwt_with_two_dots(self) -> None:
        """JWT tokens have exactly 2 dots (header.payload.signature)."""
        # Arrange
        jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature"

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
