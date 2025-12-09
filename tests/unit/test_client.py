"""Tests for AsanaClient facade."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.client import AsanaClient, _TokenAuthProvider
from autom8_asana.clients.tasks import TasksClient
from autom8_asana.config import AsanaConfig
from autom8_asana.exceptions import AuthenticationError, ConfigurationError


class MockAuthProvider:
    """Mock auth provider for testing."""

    def get_secret(self, key: str) -> str:
        return "test-token-from-provider"


class TestAsanaClientInit:
    """Tests for AsanaClient initialization."""

    def test_init_with_explicit_token(self) -> None:
        """AsanaClient accepts explicit token parameter."""
        client = AsanaClient(token="explicit-test-token")

        # Verify the token is used via the internal auth provider
        token = client._auth_provider.get_secret("ASANA_PAT")
        assert token == "explicit-test-token"

    def test_init_with_custom_auth_provider(self) -> None:
        """Custom auth_provider overrides token parameter."""
        custom_provider = MockAuthProvider()
        client = AsanaClient(
            token="should-be-ignored",
            auth_provider=custom_provider,
        )

        assert client._auth_provider is custom_provider
        assert client._auth_provider.get_secret("any-key") == "test-token-from-provider"

    def test_init_with_custom_config(self) -> None:
        """Custom config is used when provided."""
        custom_config = AsanaConfig(
            base_url="https://custom.asana.com/api/1.0",
            token_key="CUSTOM_TOKEN_KEY",
        )
        client = AsanaClient(token="test-token", config=custom_config)

        assert client._config is custom_config
        assert client._config.base_url == "https://custom.asana.com/api/1.0"
        assert client._config.token_key == "CUSTOM_TOKEN_KEY"

    def test_init_without_token_uses_env_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no token is provided, EnvAuthProvider is used."""
        monkeypatch.setenv("ASANA_PAT", "env-token-value")
        client = AsanaClient()

        # EnvAuthProvider should read from environment
        token = client._auth_provider.get_secret("ASANA_PAT")
        assert token == "env-token-value"

    def test_empty_token_raises_authentication_error(self) -> None:
        """Empty token raises AuthenticationError."""
        with pytest.raises(AuthenticationError) as exc_info:
            AsanaClient(token="")

        assert "empty" in str(exc_info.value).lower()

    def test_whitespace_token_raises_authentication_error(self) -> None:
        """Whitespace-only token raises AuthenticationError."""
        with pytest.raises(AuthenticationError) as exc_info:
            AsanaClient(token="   ")

        assert "empty" in str(exc_info.value).lower() or "whitespace" in str(exc_info.value).lower()


class TestTokenAuthProvider:
    """Tests for the internal _TokenAuthProvider class."""

    def test_returns_token_for_expected_key(self) -> None:
        """get_secret returns token when key matches."""
        provider = _TokenAuthProvider("my-token", "ASANA_PAT")

        assert provider.get_secret("ASANA_PAT") == "my-token"

    def test_raises_key_error_for_unknown_key(self) -> None:
        """get_secret raises KeyError for unknown keys."""
        provider = _TokenAuthProvider("my-token", "ASANA_PAT")

        with pytest.raises(KeyError) as exc_info:
            provider.get_secret("UNKNOWN_KEY")

        assert "UNKNOWN_KEY" in str(exc_info.value)

    def test_empty_token_rejected(self) -> None:
        """Empty token is rejected at construction."""
        with pytest.raises(AuthenticationError):
            _TokenAuthProvider("", "ASANA_PAT")

    def test_whitespace_token_rejected(self) -> None:
        """Whitespace-only token is rejected at construction."""
        with pytest.raises(AuthenticationError):
            _TokenAuthProvider("  \t\n  ", "ASANA_PAT")


class TestLazyTasksProperty:
    """Tests for lazy initialization of tasks property."""

    def test_tasks_property_returns_tasks_client(self) -> None:
        """tasks property returns TasksClient instance."""
        client = AsanaClient(token="test-token")

        tasks = client.tasks

        assert isinstance(tasks, TasksClient)

    def test_tasks_property_is_lazy(self) -> None:
        """tasks property creates TasksClient lazily on first access."""
        client = AsanaClient(token="test-token")

        # Before accessing, _tasks should be None
        assert client._tasks is None

        # Access triggers creation
        _ = client.tasks

        # Now it should be set
        assert client._tasks is not None

    def test_tasks_property_returns_same_instance(self) -> None:
        """Multiple accesses to tasks property return same instance."""
        client = AsanaClient(token="test-token")

        tasks1 = client.tasks
        tasks2 = client.tasks

        assert tasks1 is tasks2


class TestAsyncContextManager:
    """Tests for async context manager behavior."""

    async def test_async_context_manager_entry(self) -> None:
        """async with returns the client instance."""
        async with AsanaClient(token="test-token") as client:
            assert isinstance(client, AsanaClient)

    async def test_async_context_manager_closes_on_exit(self) -> None:
        """async with calls close() on exit."""
        client = AsanaClient(token="test-token")

        with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
            async with client:
                pass

            mock_close.assert_called_once()

    async def test_async_context_manager_closes_on_exception(self) -> None:
        """async with calls close() even when exception occurs."""
        client = AsanaClient(token="test-token")

        with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
            with pytest.raises(ValueError):
                async with client:
                    raise ValueError("Test exception")

            mock_close.assert_called_once()


class TestSyncContextManager:
    """Tests for sync context manager behavior."""

    def test_sync_context_manager_entry(self) -> None:
        """with returns the client instance (when not in async context)."""
        # This test runs outside async context
        with AsanaClient(token="test-token") as client:
            assert isinstance(client, AsanaClient)

    def test_sync_context_manager_raises_in_async_context(self) -> None:
        """Sync context manager raises ConfigurationError in async context."""
        # We need to test this from within an async context

        async def run_test() -> None:
            client = AsanaClient(token="test-token")
            with pytest.raises(ConfigurationError) as exc_info:
                with client:
                    pass

            assert "async context" in str(exc_info.value).lower()
            assert "async with" in str(exc_info.value).lower()

        asyncio.run(run_test())


class TestCloseMethod:
    """Tests for close/aclose methods."""

    async def test_close_closes_http_client(self) -> None:
        """close() closes the underlying HTTP client."""
        client = AsanaClient(token="test-token")

        with patch.object(client._http, "close", new_callable=AsyncMock) as mock_close:
            await client.close()

            mock_close.assert_called_once()

    async def test_aclose_is_alias_for_close(self) -> None:
        """aclose() is an alias for close()."""
        client = AsanaClient(token="test-token")

        with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
            await client.aclose()

            mock_close.assert_called_once()
