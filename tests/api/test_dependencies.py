"""Tests for API dependency injection.

Tests cover:
- Error responses for invalid auth (via protected routes)
"""

import pytest


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
