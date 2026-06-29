"""Unit tests for PerBusinessTokenProvider (anti-IDOR single-token provider)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.auth.per_business_provider import PerBusinessTokenProvider

if TYPE_CHECKING:
    from autom8_asana.protocols.auth import AuthProvider


def test_returns_wrapped_token_regardless_of_key() -> None:
    provider = PerBusinessTokenProvider("per-business-jwt")
    assert provider.get_secret("AUTOM8Y_DATA_API_KEY") == "per-business-jwt"
    assert provider.get_secret("anything") == "per-business-jwt"


def test_satisfies_auth_provider_protocol() -> None:
    provider: AuthProvider = PerBusinessTokenProvider("jwt")
    assert provider.get_secret("k") == "jwt"


def test_close_is_noop() -> None:
    provider = PerBusinessTokenProvider("jwt")
    assert provider.close() is None
