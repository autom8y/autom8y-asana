"""Tests for UsersClient cache integration.

Per TDD-CACHE-UTILIZATION: Tests for cache hit/miss flows in UsersClient.
Per ADR-0119: Client cache pattern (inline check with helpers).
Per ADR-0127: Graceful degradation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.clients.users import UsersClient
from autom8_asana.core.exceptions import CacheConnectionError
from autom8_asana.config import AsanaConfig
from autom8_asana.models.user import User
from autom8_asana.persistence.exceptions import GidValidationError


class MockHTTPClient:
    """Mock HTTP client for testing UsersClient."""

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
        raise CacheConnectionError("Cache connection failed")

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        raise CacheConnectionError("Cache connection failed")

    def invalidate(self, key: str, entry_types: list[EntryType] | None = None) -> None:
        raise CacheConnectionError("Cache connection failed")


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
def users_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    cache_provider: MockCacheProvider,
) -> UsersClient:
    """Create UsersClient with mocked dependencies including cache."""
    return UsersClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=cache_provider,
    )


@pytest.fixture
def users_client_no_cache(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
) -> UsersClient:
    """Create UsersClient without cache provider."""
    return UsersClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=None,
    )


def make_user_data(
    gid: str = "1234567890123",
    name: str = "Test User",
    email: str = "test@example.com",
    **extra: Any,
) -> dict[str, Any]:
    """Create mock user data."""
    data = {
        "gid": gid,
        "resource_type": "user",
        "name": name,
        "email": email,
    }
    data.update(extra)
    return data


def make_cache_entry(
    gid: str = "1234567890123",
    name: str = "Cached User",
    ttl: int = 3600,
) -> CacheEntry:
    """Create a cache entry."""
    return CacheEntry(
        key=gid,
        data=make_user_data(gid=gid, name=name),
        entry_type=EntryType.USER,
        version=datetime.now(UTC),
        cached_at=datetime.now(UTC),
        ttl=ttl,
    )


# Valid GIDs for testing (Asana GIDs are numeric strings)
USER_GID = "1234567890123"
USER_GID_2 = "9876543210987"


class TestCacheHitFlow:
    """Tests for cache hit scenarios (per ADR-0119)."""

    async def test_cache_hit_returns_cached_user_without_http(
        self,
        users_client: UsersClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache hit, return cached User without HTTP call."""
        # Arrange: Pre-populate cache
        cache_entry = make_cache_entry(gid=USER_GID, name="Cached User")
        cache_provider._cache[f"{USER_GID}:{EntryType.USER.value}"] = cache_entry

        # Act
        result = await users_client.get_async(USER_GID)

        # Assert: Got cached data
        assert isinstance(result, User)
        assert result.gid == USER_GID
        assert result.name == "Cached User"

        # Assert: No HTTP call was made
        mock_http.get.assert_not_called()

    async def test_cache_hit_raw_returns_cached_dict(
        self,
        users_client: UsersClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache hit with raw=True, return cached dict."""
        # Arrange
        cache_entry = make_cache_entry(gid=USER_GID, name="Cached User")
        cache_provider._cache[f"{USER_GID}:{EntryType.USER.value}"] = cache_entry

        # Act
        result = await users_client.get_async(USER_GID, raw=True)

        # Assert: Got dict, not User model
        assert isinstance(result, dict)
        assert result["gid"] == USER_GID
        assert result["name"] == "Cached User"

        # Assert: No HTTP call was made
        mock_http.get.assert_not_called()


class TestCacheMissFlow:
    """Tests for cache miss scenarios (per ADR-0119)."""

    async def test_cache_miss_fetches_from_api(
        self,
        users_client: UsersClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache miss, fetch from API."""
        # Arrange: Empty cache, mock HTTP response
        mock_http.get.return_value = make_user_data(gid=USER_GID, name="API User")

        # Act
        result = await users_client.get_async(USER_GID)

        # Assert: Got API data
        assert isinstance(result, User)
        assert result.gid == USER_GID
        assert result.name == "API User"

        # Assert: HTTP was called
        mock_http.get.assert_called_once()
        assert f"/users/{USER_GID}" in str(mock_http.get.call_args)

    async def test_cache_miss_stores_result_in_cache(
        self,
        users_client: UsersClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """After cache miss, store API result in cache."""
        # Arrange
        mock_http.get.return_value = make_user_data(gid=USER_GID, name="API User")

        # Act
        await users_client.get_async(USER_GID)

        # Assert: Cache was populated
        assert len(cache_provider.set_versioned_calls) == 1
        key, entry = cache_provider.set_versioned_calls[0]
        assert key == USER_GID
        assert entry.data["name"] == "API User"
        assert entry.entry_type == EntryType.USER

    async def test_cache_miss_uses_correct_ttl(
        self,
        users_client: UsersClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss stores with 3600s (1 hour) TTL per TDD-CACHE-UTILIZATION."""
        # Arrange
        mock_http.get.return_value = make_user_data(gid=USER_GID, name="API User")

        # Act
        await users_client.get_async(USER_GID)

        # Assert: Cache entry has correct TTL
        assert len(cache_provider.set_versioned_calls) == 1
        _, entry = cache_provider.set_versioned_calls[0]
        assert entry.ttl == 3600  # 1 hour

    async def test_cache_miss_raw_stores_and_returns_dict(
        self,
        users_client: UsersClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss with raw=True stores data and returns dict."""
        # Arrange
        mock_http.get.return_value = make_user_data(gid=USER_GID, name="API User")

        # Act
        result = await users_client.get_async(USER_GID, raw=True)

        # Assert: Got dict
        assert isinstance(result, dict)
        assert result["gid"] == USER_GID

        # Assert: Cache was populated
        assert len(cache_provider.set_versioned_calls) == 1


class TestCacheExpiration:
    """Tests for TTL expiration behavior."""

    async def test_expired_cache_entry_triggers_api_call(
        self,
        users_client: UsersClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Expired cache entry is treated as miss."""
        # Arrange: Expired entry (cached 2 hours ago, 3600s TTL)
        expired_entry = CacheEntry(
            key=USER_GID,
            data=make_user_data(gid=USER_GID, name="Expired User"),
            entry_type=EntryType.USER,
            version=datetime.now(UTC),
            cached_at=datetime.now(UTC) - timedelta(hours=2),
            ttl=3600,  # 1 hour TTL, but cached 2 hours ago
        )
        cache_provider._cache[f"{USER_GID}:{EntryType.USER.value}"] = expired_entry

        mock_http.get.return_value = make_user_data(gid=USER_GID, name="Fresh User")

        # Act
        result = await users_client.get_async(USER_GID)

        # Assert: Got fresh API data
        assert result.name == "Fresh User"

        # Assert: HTTP was called
        mock_http.get.assert_called_once()


class TestNoCacheProvider:
    """Tests when no cache provider is configured."""

    async def test_no_cache_always_fetches_from_api(
        self,
        users_client_no_cache: UsersClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Without cache provider, always fetch from API."""
        # Arrange
        mock_http.get.return_value = make_user_data(gid=USER_GID, name="API User")

        # Act
        result = await users_client_no_cache.get_async(USER_GID)

        # Assert
        assert isinstance(result, User)
        assert result.name == "API User"
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
        users_client = UsersClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            cache_provider=failing_cache,  # type: ignore[arg-type]
        )

        mock_http.get.return_value = make_user_data(gid=USER_GID, name="Fallback User")

        # Act: Should not raise, should fall back to API
        result = await users_client.get_async(USER_GID)

        # Assert: Got API data despite cache failure
        assert isinstance(result, User)
        assert result.name == "Fallback User"
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
        users_client = UsersClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            cache_provider=failing_cache,  # type: ignore[arg-type]
        )

        mock_http.get.return_value = make_user_data(gid=USER_GID, name="API User")

        # Act: Should not raise despite cache set failure
        result = await users_client.get_async(USER_GID)

        # Assert: Got result despite cache failure
        assert isinstance(result, User)
        assert result.name == "API User"


class TestGidValidation:
    """Tests for GID validation at method entry (per ADR-0119)."""

    async def test_invalid_gid_raises_validation_error(
        self,
        users_client: UsersClient,
    ) -> None:
        """Invalid GID raises GidValidationError before cache/API call."""
        # Act & Assert
        with pytest.raises(GidValidationError) as exc_info:
            await users_client.get_async("invalid-gid")

        assert "user_gid" in str(exc_info.value)

    async def test_empty_gid_raises_validation_error(
        self,
        users_client: UsersClient,
    ) -> None:
        """Empty GID raises GidValidationError."""
        with pytest.raises(GidValidationError):
            await users_client.get_async("")


class TestOptFields:
    """Tests for opt_fields parameter handling with cache."""

    async def test_cache_hit_ignores_opt_fields(
        self,
        users_client: UsersClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache hit returns cached data regardless of opt_fields."""
        # Arrange: Pre-populate cache
        cache_entry = make_cache_entry(gid=USER_GID, name="Cached User")
        cache_provider._cache[f"{USER_GID}:{EntryType.USER.value}"] = cache_entry

        # Act
        result = await users_client.get_async(USER_GID, opt_fields=["name", "email"])

        # Assert: Got cached data without HTTP call
        assert result.name == "Cached User"
        mock_http.get.assert_not_called()

    async def test_cache_miss_passes_opt_fields_to_api(
        self,
        users_client: UsersClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss passes opt_fields to API."""
        # Arrange
        mock_http.get.return_value = make_user_data(
            gid=USER_GID, name="API User", email="api@example.com"
        )

        # Act
        await users_client.get_async(USER_GID, opt_fields=["name", "email"])

        # Assert: opt_fields passed to HTTP
        mock_http.get.assert_called_once()
        call_args = mock_http.get.call_args
        assert "opt_fields" in call_args[1]["params"]
