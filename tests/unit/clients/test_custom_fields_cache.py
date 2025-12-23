"""Tests for CustomFieldsClient cache integration.

Per TDD-CACHE-UTILIZATION: Tests for cache hit/miss flows in CustomFieldsClient.
Per ADR-0119: Client cache pattern (inline check with helpers).
Per ADR-0127: Graceful degradation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.clients.custom_fields import CustomFieldsClient
from autom8_asana.config import AsanaConfig
from autom8_asana.models.custom_field import CustomField
from autom8_asana.persistence.exceptions import GidValidationError


class MockHTTPClient:
    """Mock HTTP client for testing CustomFieldsClient."""

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

    def invalidate(
        self, key: str, entry_types: list[EntryType] | None = None
    ) -> None:
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

    def invalidate(
        self, key: str, entry_types: list[EntryType] | None = None
    ) -> None:
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
def custom_fields_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    cache_provider: MockCacheProvider,
) -> CustomFieldsClient:
    """Create CustomFieldsClient with mocked dependencies including cache."""
    return CustomFieldsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=cache_provider,
    )


@pytest.fixture
def custom_fields_client_no_cache(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
) -> CustomFieldsClient:
    """Create CustomFieldsClient without cache provider."""
    return CustomFieldsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=None,
    )


def make_custom_field_data(
    gid: str = "1234567890123",
    name: str = "Test Field",
    resource_subtype: str = "text",
    **extra: Any,
) -> dict[str, Any]:
    """Create mock custom field data."""
    data = {
        "gid": gid,
        "resource_type": "custom_field",
        "name": name,
        "resource_subtype": resource_subtype,
    }
    data.update(extra)
    return data


def make_cache_entry(
    gid: str = "1234567890123",
    name: str = "Cached Field",
    ttl: int = 1800,
) -> CacheEntry:
    """Create a cache entry."""
    return CacheEntry(
        key=gid,
        data=make_custom_field_data(gid=gid, name=name),
        entry_type=EntryType.CUSTOM_FIELD,
        version=datetime.now(timezone.utc),
        cached_at=datetime.now(timezone.utc),
        ttl=ttl,
    )


# Valid GIDs for testing (Asana GIDs are numeric strings)
CUSTOM_FIELD_GID = "1234567890123"
CUSTOM_FIELD_GID_2 = "9876543210987"


class TestCacheHitFlow:
    """Tests for cache hit scenarios (per ADR-0119)."""

    async def test_cache_hit_returns_cached_custom_field_without_http(
        self,
        custom_fields_client: CustomFieldsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache hit, return cached CustomField without HTTP call."""
        # Arrange: Pre-populate cache
        cache_entry = make_cache_entry(gid=CUSTOM_FIELD_GID, name="Cached Field")
        cache_provider._cache[f"{CUSTOM_FIELD_GID}:{EntryType.CUSTOM_FIELD.value}"] = (
            cache_entry
        )

        # Act
        result = await custom_fields_client.get_async(CUSTOM_FIELD_GID)

        # Assert: Got cached data
        assert isinstance(result, CustomField)
        assert result.gid == CUSTOM_FIELD_GID
        assert result.name == "Cached Field"

        # Assert: No HTTP call was made
        mock_http.get.assert_not_called()

    async def test_cache_hit_raw_returns_cached_dict(
        self,
        custom_fields_client: CustomFieldsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache hit with raw=True, return cached dict."""
        # Arrange
        cache_entry = make_cache_entry(gid=CUSTOM_FIELD_GID, name="Cached Field")
        cache_provider._cache[f"{CUSTOM_FIELD_GID}:{EntryType.CUSTOM_FIELD.value}"] = (
            cache_entry
        )

        # Act
        result = await custom_fields_client.get_async(CUSTOM_FIELD_GID, raw=True)

        # Assert: Got dict, not CustomField model
        assert isinstance(result, dict)
        assert result["gid"] == CUSTOM_FIELD_GID
        assert result["name"] == "Cached Field"

        # Assert: No HTTP call was made
        mock_http.get.assert_not_called()


class TestCacheMissFlow:
    """Tests for cache miss scenarios (per ADR-0119)."""

    async def test_cache_miss_fetches_from_api(
        self,
        custom_fields_client: CustomFieldsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache miss, fetch from API."""
        # Arrange: Empty cache, mock HTTP response
        mock_http.get.return_value = make_custom_field_data(
            gid=CUSTOM_FIELD_GID, name="API Field"
        )

        # Act
        result = await custom_fields_client.get_async(CUSTOM_FIELD_GID)

        # Assert: Got API data
        assert isinstance(result, CustomField)
        assert result.gid == CUSTOM_FIELD_GID
        assert result.name == "API Field"

        # Assert: HTTP was called
        mock_http.get.assert_called_once()
        assert f"/custom_fields/{CUSTOM_FIELD_GID}" in str(mock_http.get.call_args)

    async def test_cache_miss_stores_result_in_cache(
        self,
        custom_fields_client: CustomFieldsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """After cache miss, store API result in cache."""
        # Arrange
        mock_http.get.return_value = make_custom_field_data(
            gid=CUSTOM_FIELD_GID, name="API Field"
        )

        # Act
        await custom_fields_client.get_async(CUSTOM_FIELD_GID)

        # Assert: Cache was populated
        assert len(cache_provider.set_versioned_calls) == 1
        key, entry = cache_provider.set_versioned_calls[0]
        assert key == CUSTOM_FIELD_GID
        assert entry.data["name"] == "API Field"
        assert entry.entry_type == EntryType.CUSTOM_FIELD

    async def test_cache_miss_uses_correct_ttl(
        self,
        custom_fields_client: CustomFieldsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss stores with 1800s (30 min) TTL per TDD-CACHE-UTILIZATION."""
        # Arrange
        mock_http.get.return_value = make_custom_field_data(
            gid=CUSTOM_FIELD_GID, name="API Field"
        )

        # Act
        await custom_fields_client.get_async(CUSTOM_FIELD_GID)

        # Assert: Cache entry has correct TTL
        assert len(cache_provider.set_versioned_calls) == 1
        _, entry = cache_provider.set_versioned_calls[0]
        assert entry.ttl == 1800  # 30 minutes

    async def test_cache_miss_raw_stores_and_returns_dict(
        self,
        custom_fields_client: CustomFieldsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss with raw=True stores data and returns dict."""
        # Arrange
        mock_http.get.return_value = make_custom_field_data(
            gid=CUSTOM_FIELD_GID, name="API Field"
        )

        # Act
        result = await custom_fields_client.get_async(CUSTOM_FIELD_GID, raw=True)

        # Assert: Got dict
        assert isinstance(result, dict)
        assert result["gid"] == CUSTOM_FIELD_GID

        # Assert: Cache was populated
        assert len(cache_provider.set_versioned_calls) == 1


class TestCacheExpiration:
    """Tests for TTL expiration behavior."""

    async def test_expired_cache_entry_triggers_api_call(
        self,
        custom_fields_client: CustomFieldsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Expired cache entry is treated as miss."""
        # Arrange: Expired entry (cached 1 hour ago, 1800s TTL)
        expired_entry = CacheEntry(
            key=CUSTOM_FIELD_GID,
            data=make_custom_field_data(gid=CUSTOM_FIELD_GID, name="Expired Field"),
            entry_type=EntryType.CUSTOM_FIELD,
            version=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc) - timedelta(hours=1),
            ttl=1800,  # 30 min TTL, but cached 1 hour ago
        )
        cache_provider._cache[f"{CUSTOM_FIELD_GID}:{EntryType.CUSTOM_FIELD.value}"] = (
            expired_entry
        )

        mock_http.get.return_value = make_custom_field_data(
            gid=CUSTOM_FIELD_GID, name="Fresh Field"
        )

        # Act
        result = await custom_fields_client.get_async(CUSTOM_FIELD_GID)

        # Assert: Got fresh API data
        assert result.name == "Fresh Field"

        # Assert: HTTP was called
        mock_http.get.assert_called_once()


class TestNoCacheProvider:
    """Tests when no cache provider is configured."""

    async def test_no_cache_always_fetches_from_api(
        self,
        custom_fields_client_no_cache: CustomFieldsClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Without cache provider, always fetch from API."""
        # Arrange
        mock_http.get.return_value = make_custom_field_data(
            gid=CUSTOM_FIELD_GID, name="API Field"
        )

        # Act
        result = await custom_fields_client_no_cache.get_async(CUSTOM_FIELD_GID)

        # Assert
        assert isinstance(result, CustomField)
        assert result.name == "API Field"
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
        custom_fields_client = CustomFieldsClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            cache_provider=failing_cache,  # type: ignore[arg-type]
        )

        mock_http.get.return_value = make_custom_field_data(
            gid=CUSTOM_FIELD_GID, name="Fallback Field"
        )

        # Act: Should not raise, should fall back to API
        result = await custom_fields_client.get_async(CUSTOM_FIELD_GID)

        # Assert: Got API data despite cache failure
        assert isinstance(result, CustomField)
        assert result.name == "Fallback Field"
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
        custom_fields_client = CustomFieldsClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            cache_provider=failing_cache,  # type: ignore[arg-type]
        )

        mock_http.get.return_value = make_custom_field_data(
            gid=CUSTOM_FIELD_GID, name="API Field"
        )

        # Act: Should not raise despite cache set failure
        result = await custom_fields_client.get_async(CUSTOM_FIELD_GID)

        # Assert: Got result despite cache failure
        assert isinstance(result, CustomField)
        assert result.name == "API Field"


class TestGidValidation:
    """Tests for GID validation at method entry (per ADR-0119)."""

    async def test_invalid_gid_raises_validation_error(
        self,
        custom_fields_client: CustomFieldsClient,
    ) -> None:
        """Invalid GID raises GidValidationError before cache/API call."""
        # Act & Assert
        with pytest.raises(GidValidationError) as exc_info:
            await custom_fields_client.get_async("invalid-gid")

        assert "custom_field_gid" in str(exc_info.value)

    async def test_empty_gid_raises_validation_error(
        self,
        custom_fields_client: CustomFieldsClient,
    ) -> None:
        """Empty GID raises GidValidationError."""
        with pytest.raises(GidValidationError):
            await custom_fields_client.get_async("")


class TestOptFields:
    """Tests for opt_fields parameter handling with cache."""

    async def test_cache_hit_ignores_opt_fields(
        self,
        custom_fields_client: CustomFieldsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache hit returns cached data regardless of opt_fields."""
        # Arrange: Pre-populate cache
        cache_entry = make_cache_entry(gid=CUSTOM_FIELD_GID, name="Cached Field")
        cache_provider._cache[f"{CUSTOM_FIELD_GID}:{EntryType.CUSTOM_FIELD.value}"] = (
            cache_entry
        )

        # Act
        result = await custom_fields_client.get_async(
            CUSTOM_FIELD_GID, opt_fields=["name", "description"]
        )

        # Assert: Got cached data without HTTP call
        assert result.name == "Cached Field"
        mock_http.get.assert_not_called()

    async def test_cache_miss_passes_opt_fields_to_api(
        self,
        custom_fields_client: CustomFieldsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss passes opt_fields to API."""
        # Arrange
        mock_http.get.return_value = make_custom_field_data(
            gid=CUSTOM_FIELD_GID, name="API Field", description="A custom field"
        )

        # Act
        await custom_fields_client.get_async(
            CUSTOM_FIELD_GID, opt_fields=["name", "description"]
        )

        # Assert: opt_fields passed to HTTP
        mock_http.get.assert_called_once()
        call_args = mock_http.get.call_args
        assert "opt_fields" in call_args[1]["params"]
