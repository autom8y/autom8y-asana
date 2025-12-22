"""Tests for API dependency injection.

Tests cover:
- PAT extraction from Authorization header
- Token validation (format, length)
- Error responses for invalid auth
"""

import pytest

from autom8_asana.api.dependencies import get_asana_pat


class TestGetAsanaPat:
    """Tests for the get_asana_pat dependency."""

    @pytest.mark.asyncio
    async def test_valid_bearer_token(self) -> None:
        """Valid Bearer token is extracted correctly."""
        token = await get_asana_pat("Bearer test_token_12345")
        assert token == "test_token_12345"

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self) -> None:
        """Missing Authorization header raises 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_asana_pat(None)

        assert exc_info.value.status_code == 401
        assert "Authorization header required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_scheme_basic(self) -> None:
        """Non-Bearer scheme raises 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_asana_pat("Basic dXNlcjpwYXNz")

        assert exc_info.value.status_code == 401
        assert "Invalid authorization scheme" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_scheme_no_space(self) -> None:
        """Bearer without space raises 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_asana_pat("BearerTokenWithoutSpace")

        assert exc_info.value.status_code == 401
        assert "Invalid authorization scheme" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_empty_token(self) -> None:
        """Bearer with empty token raises 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_asana_pat("Bearer ")

        assert exc_info.value.status_code == 401
        assert "Token is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_short_token(self) -> None:
        """Token shorter than 10 characters raises 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_asana_pat("Bearer short")

        assert exc_info.value.status_code == 401
        assert "Invalid token format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_minimum_valid_token_length(self) -> None:
        """Token with exactly 10 characters is accepted."""
        token = await get_asana_pat("Bearer 0123456789")
        assert token == "0123456789"

    @pytest.mark.asyncio
    async def test_www_authenticate_header(self) -> None:
        """401 responses include WWW-Authenticate header."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_asana_pat(None)

        assert exc_info.value.headers is not None
        assert exc_info.value.headers.get("WWW-Authenticate") == "Bearer"


class TestAuthenticationIntegration:
    """Integration tests for authentication through API routes."""

    def test_protected_route_without_auth(self, client) -> None:
        """Protected route returns 401 without Authorization header."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    def test_protected_route_with_invalid_token(self, client) -> None:
        """Protected route returns 401 with invalid token."""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer short"},
        )
        assert response.status_code == 401

    def test_protected_route_with_basic_auth(self, client) -> None:
        """Protected route returns 401 with Basic auth instead of Bearer."""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert response.status_code == 401
