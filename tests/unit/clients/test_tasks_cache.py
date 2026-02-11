"""Tests for TasksClient cache integration.

Per TDD-CACHE-INTEGRATION Section 4.5: Tests for cache hit/miss flows.
Per ADR-0124: Client cache pattern (inline check with helpers).
Per ADR-0127: Graceful degradation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import pytest

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.clients.tasks import TasksClient
from autom8_asana.config import AsanaConfig
from autom8_asana.core.exceptions import CacheConnectionError
from autom8_asana.models import Task


class FailingCacheProvider:
    """Cache provider that always fails (for graceful degradation tests)."""

    def get_versioned(self, key: str, entry_type: EntryType) -> CacheEntry | None:
        raise CacheConnectionError("Cache connection failed")

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        raise CacheConnectionError("Cache connection failed")

    def invalidate(self, key: str, entry_types: list[EntryType] | None = None) -> None:
        raise CacheConnectionError("Cache connection failed")


@pytest.fixture
def tasks_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    cache_provider: MockCacheProvider,
) -> TasksClient:
    """Create TasksClient with mocked dependencies including cache."""
    return TasksClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=cache_provider,
        client=None,
    )


@pytest.fixture
def tasks_client_no_cache(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
) -> TasksClient:
    """Create TasksClient without cache provider."""
    return TasksClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=None,
        client=None,
    )


def make_task_data(
    gid: str = "1234567890123",
    name: str = "Test Task",
    **extra: Any,
) -> dict[str, Any]:
    """Create mock task data."""
    data = {
        "gid": gid,
        "resource_type": "task",
        "name": name,
        "modified_at": "2025-01-01T12:00:00Z",
    }
    data.update(extra)
    return data


def make_cache_entry(
    gid: str = "1234567890123",
    name: str = "Cached Task",
    ttl: int = 300,
) -> CacheEntry:
    """Create a cache entry."""
    return CacheEntry(
        key=gid,
        data=make_task_data(gid=gid, name=name),
        entry_type=EntryType.TASK,
        version=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        cached_at=datetime.now(UTC),
        ttl=ttl,
    )


# Valid GIDs for testing (Asana GIDs are numeric strings)
TASK_GID = "1234567890123"
TASK_GID_2 = "9876543210987"


class TestCacheHitFlow:
    """Tests for cache hit scenarios (FR-CLIENT-001)."""

    async def test_cache_hit_returns_cached_task_without_http(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache hit, return cached Task without HTTP call."""
        # Arrange: Pre-populate cache
        cache_entry = make_cache_entry(gid=TASK_GID, name="Cached Task")
        cache_provider._cache[f"{TASK_GID}:{EntryType.TASK.value}"] = cache_entry

        # Act
        result = await tasks_client.get_async(TASK_GID)

        # Assert: Got cached data
        assert isinstance(result, Task)
        assert result.gid == TASK_GID
        assert result.name == "Cached Task"

        # Assert: No HTTP call was made
        mock_http.get.assert_not_called()

    async def test_cache_hit_raw_returns_cached_dict(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache hit with raw=True, return cached dict (FR-CLIENT-007)."""
        # Arrange
        cache_entry = make_cache_entry(gid=TASK_GID, name="Cached Task")
        cache_provider._cache[f"{TASK_GID}:{EntryType.TASK.value}"] = cache_entry

        # Act
        result = await tasks_client.get_async(TASK_GID, raw=True)

        # Assert: Got dict, not Task model
        assert isinstance(result, dict)
        assert result["gid"] == TASK_GID
        assert result["name"] == "Cached Task"

        # Assert: No HTTP call was made
        mock_http.get.assert_not_called()


class TestCacheMissFlow:
    """Tests for cache miss scenarios (FR-CLIENT-001, FR-CLIENT-003)."""

    async def test_cache_miss_fetches_from_api(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache miss, fetch from API."""
        # Arrange: Empty cache, mock HTTP response
        mock_http.get.return_value = make_task_data(gid=TASK_GID, name="API Task")

        # Act
        result = await tasks_client.get_async(TASK_GID)

        # Assert: Got API data
        assert isinstance(result, Task)
        assert result.gid == TASK_GID
        assert result.name == "API Task"

        # Assert: HTTP was called
        mock_http.get.assert_called_once()
        assert f"/tasks/{TASK_GID}" in str(mock_http.get.call_args)

    async def test_cache_miss_stores_result_in_cache(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """After cache miss, store API result in cache (FR-CLIENT-003)."""
        # Arrange
        mock_http.get.return_value = make_task_data(gid=TASK_GID, name="API Task")

        # Act
        await tasks_client.get_async(TASK_GID)

        # Assert: Cache was populated
        assert len(cache_provider.set_versioned_calls) == 1
        key, entry = cache_provider.set_versioned_calls[0]
        assert key == TASK_GID
        assert entry.data["name"] == "API Task"
        assert entry.entry_type == EntryType.TASK

    async def test_cache_miss_raw_stores_and_returns_dict(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss with raw=True stores data and returns dict."""
        # Arrange
        mock_http.get.return_value = make_task_data(gid=TASK_GID, name="API Task")

        # Act
        result = await tasks_client.get_async(TASK_GID, raw=True)

        # Assert: Got dict
        assert isinstance(result, dict)
        assert result["gid"] == TASK_GID

        # Assert: Cache was populated
        assert len(cache_provider.set_versioned_calls) == 1


class TestCacheExpiration:
    """Tests for TTL expiration behavior (FR-CLIENT-004)."""

    async def test_expired_cache_entry_triggers_api_call(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Expired cache entry is treated as miss (FR-CLIENT-004)."""
        # Arrange: Expired entry (ttl=0 means already expired)
        from datetime import timedelta

        expired_entry = CacheEntry(
            key=TASK_GID,
            data=make_task_data(gid=TASK_GID, name="Expired Task"),
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
            cached_at=datetime.now(UTC) - timedelta(hours=1),
            ttl=60,  # 60 seconds TTL, but cached 1 hour ago
        )
        cache_provider._cache[f"{TASK_GID}:{EntryType.TASK.value}"] = expired_entry

        mock_http.get.return_value = make_task_data(gid=TASK_GID, name="Fresh Task")

        # Act
        result = await tasks_client.get_async(TASK_GID)

        # Assert: Got fresh API data
        assert result.name == "Fresh Task"

        # Assert: HTTP was called
        mock_http.get.assert_called_once()


class TestNoCacheProvider:
    """Tests when no cache provider is configured."""

    async def test_no_cache_always_fetches_from_api(
        self,
        tasks_client_no_cache: TasksClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Without cache provider, always fetch from API."""
        # Arrange
        mock_http.get.return_value = make_task_data(gid=TASK_GID, name="API Task")

        # Act
        result = await tasks_client_no_cache.get_async(TASK_GID)

        # Assert
        assert isinstance(result, Task)
        assert result.name == "API Task"
        mock_http.get.assert_called_once()


class TestGracefulDegradation:
    """Tests for graceful degradation on cache errors (ADR-0127)."""

    async def test_cache_get_failure_falls_back_to_api(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """When cache get fails, fall back to API (NFR-DEGRADE-001)."""
        # Arrange: Failing cache provider
        failing_cache = FailingCacheProvider()
        tasks_client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            cache_provider=failing_cache,  # type: ignore[arg-type]
            client=None,
        )

        mock_http.get.return_value = make_task_data(gid=TASK_GID, name="Fallback Task")

        # Act: Should not raise, should fall back to API
        result = await tasks_client.get_async(TASK_GID)

        # Assert: Got API data despite cache failure
        assert isinstance(result, Task)
        assert result.name == "Fallback Task"
        mock_http.get.assert_called_once()

    async def test_cache_set_failure_still_returns_result(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """When cache set fails, still return result (NFR-DEGRADE-004)."""
        # Arrange: Failing cache provider
        failing_cache = FailingCacheProvider()
        tasks_client = TasksClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            cache_provider=failing_cache,  # type: ignore[arg-type]
            client=None,
        )

        mock_http.get.return_value = make_task_data(gid=TASK_GID, name="API Task")

        # Act: Should not raise despite cache set failure
        result = await tasks_client.get_async(TASK_GID)

        # Assert: Got result despite cache failure
        assert isinstance(result, Task)
        assert result.name == "API Task"


class TestEntityTypeTTL:
    """Tests for entity-type-specific TTL resolution (FR-TTL-*)."""

    async def test_default_ttl_for_generic_task(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Generic tasks get 300s TTL by default (FR-TTL-005)."""
        # Arrange: Task without business entity markers
        mock_http.get.return_value = make_task_data(gid=TASK_GID, name="Generic Task")

        # Act
        await tasks_client.get_async(TASK_GID)

        # Assert: Cache entry has default TTL
        assert len(cache_provider.set_versioned_calls) == 1
        _, entry = cache_provider.set_versioned_calls[0]
        assert entry.ttl == 300  # Default TTL


class TestEntityTypeTTLFromConfig:
    """Tests for entity-type-specific TTL from CacheConfig (FR-TTL-006)."""

    async def test_resolve_ttl_uses_cache_config_entity_ttls(
        self,
        mock_http: MockHTTPClient,
        auth_provider: MockAuthProvider,
        cache_provider: MockCacheProvider,
    ) -> None:
        """_resolve_entity_ttl uses CacheConfig.get_entity_ttl()."""
        from autom8_asana.config import AsanaConfig, CacheConfig

        # Configure custom entity TTLs
        cache_config = CacheConfig(
            entity_ttls={
                "business": 7200,  # Custom 2 hours
                "contact": 1800,  # Custom 30 minutes
            }
        )
        config = AsanaConfig(cache=cache_config)

        tasks_client = TasksClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,
            cache_provider=cache_provider,
            client=None,
        )

        # Test the TTL resolution method directly
        # For a generic task (no entity type detection)
        task_data = make_task_data(gid=TASK_GID, name="Generic Task")
        ttl = tasks_client._resolve_entity_ttl(task_data)

        # Without entity detection, should use default
        assert ttl == 300

    async def test_resolve_ttl_fallback_without_cache_config(
        self,
        mock_http: MockHTTPClient,
        auth_provider: MockAuthProvider,
        cache_provider: MockCacheProvider,
    ) -> None:
        """_resolve_entity_ttl falls back to hardcoded defaults without CacheConfig."""

        # Create a minimal config without CacheConfig
        class MinimalConfig:
            cache = None

        tasks_client = TasksClient(
            http=mock_http,
            config=MinimalConfig(),  # type: ignore[arg-type]
            auth_provider=auth_provider,
            cache_provider=cache_provider,
            client=None,
        )

        # Test the TTL resolution method directly
        task_data = make_task_data(gid=TASK_GID, name="Generic Task")
        ttl = tasks_client._resolve_entity_ttl(task_data)

        # Should use hardcoded default
        assert ttl == 300


class TestOptFields:
    """Tests for opt_fields parameter handling with cache."""

    async def test_cache_hit_ignores_opt_fields(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache hit returns cached data regardless of opt_fields."""
        # Arrange: Pre-populate cache
        cache_entry = make_cache_entry(gid=TASK_GID, name="Cached Task")
        cache_provider._cache[f"{TASK_GID}:{EntryType.TASK.value}"] = cache_entry

        # Act
        result = await tasks_client.get_async(TASK_GID, opt_fields=["name", "notes"])

        # Assert: Got cached data without HTTP call
        assert result.name == "Cached Task"
        mock_http.get.assert_not_called()

    async def test_cache_miss_passes_opt_fields_to_api(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss passes opt_fields to API."""
        # Arrange
        mock_http.get.return_value = make_task_data(
            gid=TASK_GID, name="API Task", notes="Some notes"
        )

        # Act
        await tasks_client.get_async(TASK_GID, opt_fields=["name", "notes"])

        # Assert: opt_fields passed to HTTP
        mock_http.get.assert_called_once()
        call_args = mock_http.get.call_args
        assert "opt_fields" in call_args[1]["params"]
