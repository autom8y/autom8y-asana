"""Tests for AsanaClient facade."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from autom8_asana.cache.models.metrics import CacheMetrics
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


class TestAsanaClientUnifiedStore:
    """Tests for AsanaClient.unified_store property."""

    def test_unified_store_lazy_init(self) -> None:
        """unified_store property lazily initializes UnifiedTaskStore."""
        from autom8_asana._defaults.cache import InMemoryCacheProvider
        from autom8_asana.cache.providers.unified import UnifiedTaskStore

        client = AsanaClient(token="test-token")

        # Access unified_store
        store = client.unified_store

        assert store is not None
        assert isinstance(store, UnifiedTaskStore)
        assert isinstance(store.cache, InMemoryCacheProvider)

    def test_unified_store_same_instance_on_repeated_calls(self) -> None:
        """Repeated calls to unified_store return same instance."""
        client = AsanaClient(token="test-token")

        store1 = client.unified_store
        store2 = client.unified_store

        assert store1 is store2

    def test_unified_store_none_when_cache_disabled(self) -> None:
        """unified_store returns None when cache is disabled."""
        from autom8_asana.config import AsanaConfig, CacheConfig

        config = AsanaConfig(cache=CacheConfig(enabled=False))
        client = AsanaClient(token="test-token", config=config)

        assert client.unified_store is None

    def test_unified_store_uses_batch_client(self) -> None:
        """unified_store is wired with client's batch client."""
        from autom8_asana.cache.providers.unified import UnifiedTaskStore

        client = AsanaClient(token="test-token")

        store = client.unified_store

        assert store is not None
        assert isinstance(store, UnifiedTaskStore)
        # Batch client is lazy-initialized, so access it first
        assert store.batch_client is client.batch

    def test_unified_store_thread_safe(self) -> None:
        """unified_store initialization is thread-safe."""
        import threading

        client = AsanaClient(token="test-token")
        stores = []

        def access_store() -> None:
            stores.append(client.unified_store)

        threads = [threading.Thread(target=access_store) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same instance
        assert len(stores) == 10
        assert all(s is stores[0] for s in stores)
