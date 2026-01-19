"""Tests for ProjectsClient cache integration.

Per TDD-CACHE-UTILIZATION: Tests for cache hit/miss flows in ProjectsClient.
Per ADR-0119: Client cache pattern (inline check with helpers).
Per ADR-0127: Graceful degradation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.clients.projects import ProjectsClient
from autom8_asana.config import AsanaConfig
from autom8_asana.models.project import Project
from autom8_asana.persistence.exceptions import GidValidationError


class MockHTTPClient:
    """Mock HTTP client for testing ProjectsClient."""

    def __init__(self) -> None:
        self.get = AsyncMock()
        self.post = AsyncMock()
        self.put = AsyncMock()
        self.delete = AsyncMock()
        self.get_paginated = AsyncMock()


class MockAuthProvider:
    """Mock auth provider."""

    def get_secret(self, key: str) -> str:
        return "test-token"


class MockCacheProvider:
    """Mock cache provider for testing."""

    def __init__(self) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self.get_versioned_calls: list[tuple[str, EntryType]] = []
        self.set_versioned_calls: list[tuple[str, CacheEntry]] = []
        self.invalidate_calls: list[tuple[str, list[EntryType] | None]] = []

    def get_versioned(self, key: str, entry_type: EntryType) -> CacheEntry | None:
        """Get entry from cache."""
        self.get_versioned_calls.append((key, entry_type))
        return self._cache.get(f"{key}:{entry_type.value}")

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        """Store entry in cache."""
        self.set_versioned_calls.append((key, entry))
        self._cache[f"{key}:{entry.entry_type.value}"] = entry

    def invalidate(self, key: str, entry_types: list[EntryType] | None = None) -> None:
        """Invalidate cache entry."""
        self.invalidate_calls.append((key, entry_types))
        if entry_types:
            for entry_type in entry_types:
                self._cache.pop(f"{key}:{entry_type.value}", None)
        else:
            keys_to_remove = [k for k in self._cache if k.startswith(f"{key}:")]
            for k in keys_to_remove:
                del self._cache[k]


class FailingCacheProvider:
    """Cache provider that always fails (for graceful degradation tests)."""

    def get_versioned(self, key: str, entry_type: EntryType) -> CacheEntry | None:
        raise ConnectionError("Cache connection failed")

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        raise ConnectionError("Cache connection failed")

    def invalidate(self, key: str, entry_types: list[EntryType] | None = None) -> None:
        raise ConnectionError("Cache connection failed")


@pytest.fixture
def mock_http() -> MockHTTPClient:
    """Create mock HTTP client."""
    return MockHTTPClient()


@pytest.fixture
def config() -> AsanaConfig:
    """Default test configuration."""
    return AsanaConfig()


@pytest.fixture
def auth_provider() -> MockAuthProvider:
    """Mock auth provider."""
    return MockAuthProvider()


@pytest.fixture
def cache_provider() -> MockCacheProvider:
    """Mock cache provider."""
    return MockCacheProvider()


@pytest.fixture
def projects_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    cache_provider: MockCacheProvider,
) -> ProjectsClient:
    """Create ProjectsClient with mocked dependencies including cache."""
    return ProjectsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=cache_provider,
    )


@pytest.fixture
def projects_client_no_cache(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
) -> ProjectsClient:
    """Create ProjectsClient without cache provider."""
    return ProjectsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=None,
    )


def make_project_data(
    gid: str = "1234567890123",
    name: str = "Test Project",
    **extra: Any,
) -> dict[str, Any]:
    """Create mock project data."""
    data = {
        "gid": gid,
        "resource_type": "project",
        "name": name,
        "modified_at": "2025-01-01T12:00:00Z",
    }
    data.update(extra)
    return data


def make_cache_entry(
    gid: str = "1234567890123",
    name: str = "Cached Project",
    ttl: int = 900,
) -> CacheEntry:
    """Create a cache entry."""
    return CacheEntry(
        key=gid,
        data=make_project_data(gid=gid, name=name),
        entry_type=EntryType.PROJECT,
        version=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        cached_at=datetime.now(UTC),
        ttl=ttl,
    )


# Valid GIDs for testing (Asana GIDs are numeric strings)
PROJECT_GID = "1234567890123"
PROJECT_GID_2 = "9876543210987"


class TestCacheHitFlow:
    """Tests for cache hit scenarios (per ADR-0119)."""

    async def test_cache_hit_returns_cached_project_without_http(
        self,
        projects_client: ProjectsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache hit, return cached Project without HTTP call."""
        # Arrange: Pre-populate cache
        cache_entry = make_cache_entry(gid=PROJECT_GID, name="Cached Project")
        cache_provider._cache[f"{PROJECT_GID}:{EntryType.PROJECT.value}"] = cache_entry

        # Act
        result = await projects_client.get_async(PROJECT_GID)

        # Assert: Got cached data
        assert isinstance(result, Project)
        assert result.gid == PROJECT_GID
        assert result.name == "Cached Project"

        # Assert: No HTTP call was made
        mock_http.get.assert_not_called()

    async def test_cache_hit_raw_returns_cached_dict(
        self,
        projects_client: ProjectsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache hit with raw=True, return cached dict."""
        # Arrange
        cache_entry = make_cache_entry(gid=PROJECT_GID, name="Cached Project")
        cache_provider._cache[f"{PROJECT_GID}:{EntryType.PROJECT.value}"] = cache_entry

        # Act
        result = await projects_client.get_async(PROJECT_GID, raw=True)

        # Assert: Got dict, not Project model
        assert isinstance(result, dict)
        assert result["gid"] == PROJECT_GID
        assert result["name"] == "Cached Project"

        # Assert: No HTTP call was made
        mock_http.get.assert_not_called()


class TestCacheMissFlow:
    """Tests for cache miss scenarios (per ADR-0119)."""

    async def test_cache_miss_fetches_from_api(
        self,
        projects_client: ProjectsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache miss, fetch from API."""
        # Arrange: Empty cache, mock HTTP response
        mock_http.get.return_value = make_project_data(
            gid=PROJECT_GID, name="API Project"
        )

        # Act
        result = await projects_client.get_async(PROJECT_GID)

        # Assert: Got API data
        assert isinstance(result, Project)
        assert result.gid == PROJECT_GID
        assert result.name == "API Project"

        # Assert: HTTP was called
        mock_http.get.assert_called_once()
        assert f"/projects/{PROJECT_GID}" in str(mock_http.get.call_args)

    async def test_cache_miss_stores_result_in_cache(
        self,
        projects_client: ProjectsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """After cache miss, store API result in cache."""
        # Arrange
        mock_http.get.return_value = make_project_data(
            gid=PROJECT_GID, name="API Project"
        )

        # Act
        await projects_client.get_async(PROJECT_GID)

        # Assert: Cache was populated
        assert len(cache_provider.set_versioned_calls) == 1
        key, entry = cache_provider.set_versioned_calls[0]
        assert key == PROJECT_GID
        assert entry.data["name"] == "API Project"
        assert entry.entry_type == EntryType.PROJECT

    async def test_cache_miss_uses_correct_ttl(
        self,
        projects_client: ProjectsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss stores with 900s (15 min) TTL per TDD-CACHE-UTILIZATION."""
        # Arrange
        mock_http.get.return_value = make_project_data(
            gid=PROJECT_GID, name="API Project"
        )

        # Act
        await projects_client.get_async(PROJECT_GID)

        # Assert: Cache entry has correct TTL
        assert len(cache_provider.set_versioned_calls) == 1
        _, entry = cache_provider.set_versioned_calls[0]
        assert entry.ttl == 900  # 15 minutes

    async def test_cache_miss_raw_stores_and_returns_dict(
        self,
        projects_client: ProjectsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss with raw=True stores data and returns dict."""
        # Arrange
        mock_http.get.return_value = make_project_data(
            gid=PROJECT_GID, name="API Project"
        )

        # Act
        result = await projects_client.get_async(PROJECT_GID, raw=True)

        # Assert: Got dict
        assert isinstance(result, dict)
        assert result["gid"] == PROJECT_GID

        # Assert: Cache was populated
        assert len(cache_provider.set_versioned_calls) == 1


class TestCacheExpiration:
    """Tests for TTL expiration behavior."""

    async def test_expired_cache_entry_triggers_api_call(
        self,
        projects_client: ProjectsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Expired cache entry is treated as miss."""
        # Arrange: Expired entry (cached 1 hour ago, 900s TTL)
        expired_entry = CacheEntry(
            key=PROJECT_GID,
            data=make_project_data(gid=PROJECT_GID, name="Expired Project"),
            entry_type=EntryType.PROJECT,
            version=datetime.now(UTC),
            cached_at=datetime.now(UTC) - timedelta(hours=1),
            ttl=900,  # 15 min TTL, but cached 1 hour ago
        )
        cache_provider._cache[f"{PROJECT_GID}:{EntryType.PROJECT.value}"] = (
            expired_entry
        )

        mock_http.get.return_value = make_project_data(
            gid=PROJECT_GID, name="Fresh Project"
        )

        # Act
        result = await projects_client.get_async(PROJECT_GID)

        # Assert: Got fresh API data
        assert result.name == "Fresh Project"

        # Assert: HTTP was called
        mock_http.get.assert_called_once()


class TestNoCacheProvider:
    """Tests when no cache provider is configured."""

    async def test_no_cache_always_fetches_from_api(
        self,
        projects_client_no_cache: ProjectsClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Without cache provider, always fetch from API."""
        # Arrange
        mock_http.get.return_value = make_project_data(
            gid=PROJECT_GID, name="API Project"
        )

        # Act
        result = await projects_client_no_cache.get_async(PROJECT_GID)

        # Assert
        assert isinstance(result, Project)
        assert result.name == "API Project"
        mock_http.get.assert_called_once()


class TestGracefulDegradation:
    """Tests for graceful degradation on cache errors (ADR-0127)."""

    async def test_cache_get_failure_falls_back_to_api(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """When cache get fails, fall back to API."""
        # Arrange: Failing cache provider
        failing_cache = FailingCacheProvider()
        projects_client = ProjectsClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            cache_provider=failing_cache,  # type: ignore[arg-type]
        )

        mock_http.get.return_value = make_project_data(
            gid=PROJECT_GID, name="Fallback Project"
        )

        # Act: Should not raise, should fall back to API
        result = await projects_client.get_async(PROJECT_GID)

        # Assert: Got API data despite cache failure
        assert isinstance(result, Project)
        assert result.name == "Fallback Project"
        mock_http.get.assert_called_once()

    async def test_cache_set_failure_still_returns_result(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """When cache set fails, still return result."""
        # Arrange: Failing cache provider
        failing_cache = FailingCacheProvider()
        projects_client = ProjectsClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            cache_provider=failing_cache,  # type: ignore[arg-type]
        )

        mock_http.get.return_value = make_project_data(
            gid=PROJECT_GID, name="API Project"
        )

        # Act: Should not raise despite cache set failure
        result = await projects_client.get_async(PROJECT_GID)

        # Assert: Got result despite cache failure
        assert isinstance(result, Project)
        assert result.name == "API Project"


class TestGidValidation:
    """Tests for GID validation at method entry (per ADR-0119)."""

    async def test_invalid_gid_raises_validation_error(
        self,
        projects_client: ProjectsClient,
    ) -> None:
        """Invalid GID raises GidValidationError before cache/API call."""
        # Act & Assert
        with pytest.raises(GidValidationError) as exc_info:
            await projects_client.get_async("invalid-gid")

        assert "project_gid" in str(exc_info.value)

    async def test_empty_gid_raises_validation_error(
        self,
        projects_client: ProjectsClient,
    ) -> None:
        """Empty GID raises GidValidationError."""
        with pytest.raises(GidValidationError):
            await projects_client.get_async("")


class TestOptFields:
    """Tests for opt_fields parameter handling with cache."""

    async def test_cache_hit_ignores_opt_fields(
        self,
        projects_client: ProjectsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache hit returns cached data regardless of opt_fields."""
        # Arrange: Pre-populate cache
        cache_entry = make_cache_entry(gid=PROJECT_GID, name="Cached Project")
        cache_provider._cache[f"{PROJECT_GID}:{EntryType.PROJECT.value}"] = cache_entry

        # Act
        result = await projects_client.get_async(
            PROJECT_GID, opt_fields=["name", "notes"]
        )

        # Assert: Got cached data without HTTP call
        assert result.name == "Cached Project"
        mock_http.get.assert_not_called()

    async def test_cache_miss_passes_opt_fields_to_api(
        self,
        projects_client: ProjectsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss passes opt_fields to API."""
        # Arrange
        mock_http.get.return_value = make_project_data(
            gid=PROJECT_GID, name="API Project", notes="Some notes"
        )

        # Act
        await projects_client.get_async(PROJECT_GID, opt_fields=["name", "notes"])

        # Assert: opt_fields passed to HTTP
        mock_http.get.assert_called_once()
        call_args = mock_http.get.call_args
        assert "opt_fields" in call_args[1]["params"]
