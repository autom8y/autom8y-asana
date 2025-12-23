"""Tests for CredentialVaultAuthProvider.

These tests use mocks since the actual CredentialClient requires
the autom8y-auth package which is an optional dependency.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.exceptions import AuthenticationError

if TYPE_CHECKING:
    from autom8_asana._defaults.vault_auth import CredentialVaultAuthProvider


# Fixture to skip tests if vault extras not installed
@pytest.fixture
def vault_auth_class():
    """Import CredentialVaultAuthProvider, skip if not available."""
    try:
        from autom8_asana._defaults.vault_auth import CredentialVaultAuthProvider
        return CredentialVaultAuthProvider
    except ImportError:
        pytest.skip("vault extras not installed")


@pytest.fixture
def mock_credential():
    """Create a mock credential response."""
    cred = MagicMock()
    cred.access_token = "test_access_token_123"
    cred.token_type = "Bearer"
    cred.expires_at = datetime.utcnow() + timedelta(hours=1)
    cred.scopes = ["default"]
    cred.provider = "asana"
    cred.credential_id = "cred_123"
    return cred


@pytest.fixture
def mock_credential_client(mock_credential):
    """Create a mock CredentialClient."""
    client = MagicMock()
    client.get = AsyncMock(return_value=mock_credential)
    return client


class TestCredentialVaultAuthProviderInit:
    """Tests for CredentialVaultAuthProvider initialization."""

    def test_init_with_bot_identity(self, vault_auth_class, mock_credential_client):
        """Test initialization with bot identity type."""
        provider = vault_auth_class(
            credential_client=mock_credential_client,
            business_id="business-uuid-123",
            identity_type="bot",
        )

        assert provider.business_id == "business-uuid-123"
        assert provider.user_id is None
        assert provider.identity_type == "bot"

    def test_init_with_user_identity(self, vault_auth_class, mock_credential_client):
        """Test initialization with user identity type."""
        provider = vault_auth_class(
            credential_client=mock_credential_client,
            business_id="business-uuid-123",
            user_id="user-uuid-456",
            identity_type="user",
        )

        assert provider.business_id == "business-uuid-123"
        assert provider.user_id == "user-uuid-456"
        assert provider.identity_type == "user"

    def test_init_user_identity_requires_user_id(self, vault_auth_class, mock_credential_client):
        """Test that user identity type requires user_id."""
        with pytest.raises(ValueError, match="user_id is required"):
            vault_auth_class(
                credential_client=mock_credential_client,
                business_id="business-uuid-123",
                identity_type="user",
                # user_id not provided
            )

    def test_init_default_identity_type_is_bot(self, vault_auth_class, mock_credential_client):
        """Test that default identity_type is 'bot'."""
        provider = vault_auth_class(
            credential_client=mock_credential_client,
            business_id="business-uuid-123",
        )

        assert provider.identity_type == "bot"


class TestCredentialVaultAuthProviderAsync:
    """Tests for async credential retrieval."""

    @pytest.mark.asyncio
    async def test_get_secret_async_returns_token(
        self, vault_auth_class, mock_credential_client, mock_credential
    ):
        """Test that get_secret_async returns the access token."""
        provider = vault_auth_class(
            credential_client=mock_credential_client,
            business_id="business-uuid-123",
            identity_type="bot",
        )

        token = await provider.get_secret_async("ASANA_PAT")

        assert token == "test_access_token_123"
        mock_credential_client.get.assert_called_once_with(
            user_id=None,
            business_id="business-uuid-123",
            provider="asana",
            identity_type="bot",
        )

    @pytest.mark.asyncio
    async def test_get_secret_async_with_user_identity(
        self, vault_auth_class, mock_credential_client, mock_credential
    ):
        """Test get_secret_async with user identity."""
        provider = vault_auth_class(
            credential_client=mock_credential_client,
            business_id="business-uuid-123",
            user_id="user-uuid-456",
            identity_type="user",
        )

        await provider.get_secret_async("ASANA_PAT")

        mock_credential_client.get.assert_called_once_with(
            user_id="user-uuid-456",
            business_id="business-uuid-123",
            provider="asana",
            identity_type="user",
        )

    @pytest.mark.asyncio
    async def test_get_secret_async_caches_token(
        self, vault_auth_class, mock_credential_client, mock_credential
    ):
        """Test that the token is cached after retrieval."""
        provider = vault_auth_class(
            credential_client=mock_credential_client,
            business_id="business-uuid-123",
        )

        await provider.get_secret_async("ASANA_PAT")

        assert provider._cached_token == "test_access_token_123"

    @pytest.mark.asyncio
    async def test_get_secret_async_raises_on_error(
        self, vault_auth_class, mock_credential_client
    ):
        """Test that get_secret_async raises AuthenticationError on failure."""
        mock_credential_client.get = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        provider = vault_auth_class(
            credential_client=mock_credential_client,
            business_id="business-uuid-123",
        )

        with pytest.raises(AuthenticationError, match="Failed to retrieve"):
            await provider.get_secret_async("ASANA_PAT")


class TestCredentialVaultAuthProviderSync:
    """Tests for sync credential retrieval."""

    def test_get_secret_returns_token(
        self, vault_auth_class, mock_credential_client, mock_credential
    ):
        """Test that get_secret returns the access token (sync)."""
        provider = vault_auth_class(
            credential_client=mock_credential_client,
            business_id="business-uuid-123",
            identity_type="bot",
        )

        token = provider.get_secret("ASANA_PAT")

        assert token == "test_access_token_123"

    def test_get_secret_raises_on_error(
        self, vault_auth_class, mock_credential_client
    ):
        """Test that get_secret raises AuthenticationError on failure."""
        mock_credential_client.get = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        provider = vault_auth_class(
            credential_client=mock_credential_client,
            business_id="business-uuid-123",
        )

        with pytest.raises(AuthenticationError, match="Failed to retrieve"):
            provider.get_secret("ASANA_PAT")


class TestCredentialVaultAuthProviderCache:
    """Tests for cache management."""

    @pytest.mark.asyncio
    async def test_clear_cache_removes_token(
        self, vault_auth_class, mock_credential_client, mock_credential
    ):
        """Test that clear_cache removes the cached token."""
        provider = vault_auth_class(
            credential_client=mock_credential_client,
            business_id="business-uuid-123",
        )

        # First, populate the cache
        await provider.get_secret_async("ASANA_PAT")
        assert provider._cached_token == "test_access_token_123"

        # Clear the cache
        provider.clear_cache()

        assert provider._cached_token is None

    def test_clear_cache_when_empty(self, vault_auth_class, mock_credential_client):
        """Test that clear_cache works when cache is already empty."""
        provider = vault_auth_class(
            credential_client=mock_credential_client,
            business_id="business-uuid-123",
        )

        # Should not raise
        provider.clear_cache()
        assert provider._cached_token is None


class TestCredentialVaultAuthProviderProtocol:
    """Tests for AuthProvider protocol compliance."""

    def test_implements_auth_provider_protocol(
        self, vault_auth_class, mock_credential_client
    ):
        """Test that CredentialVaultAuthProvider has required methods."""
        provider = vault_auth_class(
            credential_client=mock_credential_client,
            business_id="business-uuid-123",
        )

        # AuthProvider protocol requires get_secret(key: str) -> str
        assert hasattr(provider, "get_secret")
        assert callable(provider.get_secret)
