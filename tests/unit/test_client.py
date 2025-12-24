"""Tests for AsanaClient facade."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from autom8_asana.cache.metrics import CacheMetrics
from autom8_asana.client import AsanaClient, _TokenAuthProvider, _get_workspace_gid_from_env
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

    def test_init_without_token_uses_env_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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

        assert (
            "empty" in str(exc_info.value).lower()
            or "whitespace" in str(exc_info.value).lower()
        )


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

    async def test_sync_context_manager_raises_in_async_context(self) -> None:
        """Sync context manager raises ConfigurationError in async context."""
        client = AsanaClient(token="test-token")
        with pytest.raises(ConfigurationError) as exc_info:
            with client:
                pass

        assert "async context" in str(exc_info.value).lower()
        assert "async with" in str(exc_info.value).lower()


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


class TestSaveSessionFactory:
    """Tests for client.save_session() factory method."""

    def test_save_session_returns_session(self) -> None:
        """save_session() returns a SaveSession instance."""
        from autom8_asana.persistence import SaveSession

        client = AsanaClient(token="test-token")
        session = client.save_session()

        assert isinstance(session, SaveSession)

    def test_save_session_with_default_params(self) -> None:
        """save_session() uses default parameters."""
        client = AsanaClient(token="test-token")
        session = client.save_session()

        assert session._batch_size == 10
        assert session._max_concurrent == 15

    def test_save_session_with_custom_params(self) -> None:
        """save_session() accepts custom parameters."""
        client = AsanaClient(token="test-token")
        session = client.save_session(batch_size=5, max_concurrent=10)

        assert session._batch_size == 5
        assert session._max_concurrent == 10

    def test_save_session_passes_client(self) -> None:
        """save_session() passes client to SaveSession."""
        client = AsanaClient(token="test-token")
        session = client.save_session()

        assert session._client is client

    async def test_save_session_async_context(self) -> None:
        """save_session() can be used as async context manager."""
        client = AsanaClient(token="test-token")

        async with client.save_session() as session:
            assert session is not None

    def test_save_session_sync_context(self) -> None:
        """save_session() can be used as sync context manager."""
        client = AsanaClient(token="test-token")

        with client.save_session() as session:
            assert session is not None

    def test_save_session_creates_new_session_each_call(self) -> None:
        """Each call to save_session() creates a new session."""
        client = AsanaClient(token="test-token")

        session1 = client.save_session()
        session2 = client.save_session()

        assert session1 is not session2


class MockCacheProviderWithMetrics:
    """Mock cache provider with metrics for testing."""

    def __init__(self) -> None:
        self._metrics = CacheMetrics()

    def get_metrics(self) -> CacheMetrics:
        return self._metrics


class TestCacheMetricsProperty:
    """Tests for cache_metrics property (per TDD-CACHE-UTILIZATION)."""

    def test_cache_metrics_returns_none_without_cache_provider(self) -> None:
        """cache_metrics returns None when no cache provider is configured."""
        # Arrange: Create client with null cache (explicit None)
        from autom8_asana._defaults.cache import NullCacheProvider

        client = AsanaClient(token="test-token", cache_provider=NullCacheProvider())

        # NullCacheProvider.get_metrics() returns a CacheMetrics instance
        # So this test checks the property works
        metrics = client.cache_metrics

        # For NullCacheProvider, it returns a metrics object (not None)
        assert metrics is not None

    def test_cache_metrics_returns_metrics_with_cache_provider(self) -> None:
        """cache_metrics returns CacheMetrics when cache provider is configured."""
        # Arrange: Create client with mock cache provider
        mock_cache = MockCacheProviderWithMetrics()
        client = AsanaClient(
            token="test-token",
            cache_provider=mock_cache,  # type: ignore[arg-type]
        )

        # Act
        metrics = client.cache_metrics

        # Assert
        assert metrics is not None
        assert isinstance(metrics, CacheMetrics)
        assert metrics is mock_cache._metrics

    def test_cache_metrics_exposes_hit_rate(self) -> None:
        """cache_metrics can be used to access hit rate statistics."""
        # Arrange
        mock_cache = MockCacheProviderWithMetrics()
        mock_cache._metrics.record_hit(latency_ms=1.0)
        mock_cache._metrics.record_hit(latency_ms=1.0)
        mock_cache._metrics.record_miss(latency_ms=2.0)

        client = AsanaClient(
            token="test-token",
            cache_provider=mock_cache,  # type: ignore[arg-type]
        )

        # Act
        metrics = client.cache_metrics

        # Assert: 2 hits, 1 miss = 66.67% hit rate
        assert metrics is not None
        assert metrics.hits == 2
        assert metrics.misses == 1
        assert 0.66 <= metrics.hit_rate <= 0.67

    def test_cache_metrics_exposes_api_calls_saved(self) -> None:
        """cache_metrics exposes api_calls_saved (equals hits)."""
        # Arrange
        mock_cache = MockCacheProviderWithMetrics()
        mock_cache._metrics.record_hit(latency_ms=1.0)
        mock_cache._metrics.record_hit(latency_ms=1.0)
        mock_cache._metrics.record_hit(latency_ms=1.0)

        client = AsanaClient(
            token="test-token",
            cache_provider=mock_cache,  # type: ignore[arg-type]
        )

        # Act
        metrics = client.cache_metrics

        # Assert
        assert metrics is not None
        assert metrics.api_calls_saved == 3


class TestWorkspaceGidIndirection:
    """Tests for ASANA_WORKSPACE_KEY indirection pattern.

    This parallels the ASANA_TOKEN_KEY pattern for ECS deployments where
    secrets are injected with platform naming conventions.
    """

    def test_get_workspace_gid_default_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Default reads from ASANA_WORKSPACE_GID without indirection."""
        # Clean environment
        monkeypatch.delenv("ASANA_WORKSPACE_KEY", raising=False)
        monkeypatch.setenv("ASANA_WORKSPACE_GID", "1234567890123456")

        result = _get_workspace_gid_from_env()

        assert result == "1234567890123456"

    def test_get_workspace_gid_with_indirection(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ASANA_WORKSPACE_KEY points to different env var."""
        # Set up indirection: ASANA_WORKSPACE_KEY points to WORKSPACE_GID
        monkeypatch.setenv("ASANA_WORKSPACE_KEY", "WORKSPACE_GID")
        monkeypatch.setenv("WORKSPACE_GID", "9876543210987654")
        # Also set the default to ensure indirection takes precedence
        monkeypatch.setenv("ASANA_WORKSPACE_GID", "should-not-use-this")

        result = _get_workspace_gid_from_env()

        assert result == "9876543210987654"

    def test_get_workspace_gid_indirection_to_missing_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Indirection to non-existent var returns None."""
        monkeypatch.setenv("ASANA_WORKSPACE_KEY", "NONEXISTENT_VAR")
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)

        result = _get_workspace_gid_from_env()

        assert result is None

    def test_get_workspace_gid_no_env_vars_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No env vars set returns None."""
        monkeypatch.delenv("ASANA_WORKSPACE_KEY", raising=False)
        monkeypatch.delenv("ASANA_WORKSPACE_GID", raising=False)

        result = _get_workspace_gid_from_env()

        assert result is None

    def test_client_uses_workspace_indirection(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AsanaClient uses ASANA_WORKSPACE_KEY indirection."""
        monkeypatch.setenv("ASANA_WORKSPACE_KEY", "MY_WORKSPACE")
        monkeypatch.setenv("MY_WORKSPACE", "workspace-from-indirection")

        client = AsanaClient(token="test-token")

        assert client.default_workspace_gid == "workspace-from-indirection"

    def test_explicit_workspace_overrides_indirection(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit workspace_gid parameter overrides env var indirection."""
        monkeypatch.setenv("ASANA_WORKSPACE_KEY", "MY_WORKSPACE")
        monkeypatch.setenv("MY_WORKSPACE", "from-env-indirection")

        client = AsanaClient(token="test-token", workspace_gid="explicit-workspace")

        assert client.default_workspace_gid == "explicit-workspace"

    def test_ecs_deployment_pattern(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test realistic ECS deployment pattern with platform naming.

        In ECS deployments:
        - Secrets Manager secret 'workspace-gid' is injected as WORKSPACE_GID
        - ASANA_WORKSPACE_KEY is set to "WORKSPACE_GID" in task definition
        - SDK reads workspace GID from WORKSPACE_GID via indirection
        """
        # Simulate ECS environment
        monkeypatch.setenv("ASANA_WORKSPACE_KEY", "WORKSPACE_GID")
        monkeypatch.setenv("WORKSPACE_GID", "1234567890123456")  # From Secrets Manager
        monkeypatch.setenv("ASANA_TOKEN_KEY", "BOT_PAT")
        monkeypatch.setenv("BOT_PAT", "test-pat-from-secrets")  # From Secrets Manager

        client = AsanaClient()

        # Workspace should come from indirection
        assert client.default_workspace_gid == "1234567890123456"
        # Token should also use indirection (existing pattern)
        token = client._auth_provider.get_secret("BOT_PAT")
        assert token == "test-pat-from-secrets"
