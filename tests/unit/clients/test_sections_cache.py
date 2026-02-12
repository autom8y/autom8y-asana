"""Tests for SectionsClient cache integration.

Per TDD-CACHE-UTILIZATION: Tests for cache hit/miss flows in SectionsClient.
Per ADR-0119: Client cache pattern (inline check with helpers).
Per ADR-0120: Batch cache population on list operations.
Per ADR-0127: Graceful degradation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.clients.sections import SectionsClient
from autom8_asana.config import AsanaConfig
from autom8_asana.core.exceptions import CacheConnectionError
from autom8_asana.models.section import Section
from autom8_asana.persistence.exceptions import GidValidationError


class FailingCacheProvider:
    """Cache provider that always fails (for graceful degradation tests)."""

    def get_versioned(self, key: str, entry_type: EntryType) -> CacheEntry | None:
        raise CacheConnectionError("Cache connection failed")

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        raise CacheConnectionError("Cache connection failed")

    def set_batch(self, entries: dict[str, CacheEntry]) -> None:
        raise CacheConnectionError("Cache connection failed")

    def invalidate(self, key: str, entry_types: list[EntryType] | None = None) -> None:
        raise CacheConnectionError("Cache connection failed")


@pytest.fixture
def sections_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    cache_provider: MockCacheProvider,
) -> SectionsClient:
    """Create SectionsClient with mocked dependencies including cache."""
    return SectionsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=cache_provider,
    )


@pytest.fixture
def sections_client_no_cache(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
) -> SectionsClient:
    """Create SectionsClient without cache provider."""
    return SectionsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=None,
    )


def make_section_data(
    gid: str = "1234567890123",
    name: str = "Test Section",
    **extra: Any,
) -> dict[str, Any]:
    """Create mock section data."""
    data = {
        "gid": gid,
        "resource_type": "section",
        "name": name,
        # Note: sections do NOT have modified_at field
    }
    data.update(extra)
    return data


def make_cache_entry(
    gid: str = "1234567890123",
    name: str = "Cached Section",
    ttl: int = 1800,
) -> CacheEntry:
    """Create a cache entry."""
    return CacheEntry(
        key=gid,
        data=make_section_data(gid=gid, name=name),
        entry_type=EntryType.SECTION,
        version=datetime.now(UTC),  # No modified_at for sections
        cached_at=datetime.now(UTC),
        ttl=ttl,
    )


# Valid GIDs for testing (Asana GIDs are numeric strings)
SECTION_GID = "1234567890123"
SECTION_GID_2 = "9876543210987"
PROJECT_GID = "5555555555555"


class TestCacheHitFlow:
    """Tests for cache hit scenarios (per ADR-0119)."""

    async def test_cache_hit_returns_cached_section_without_http(
        self,
        sections_client: SectionsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache hit, return cached Section without HTTP call."""
        # Arrange: Pre-populate cache
        cache_entry = make_cache_entry(gid=SECTION_GID, name="Cached Section")
        cache_provider._cache[f"{SECTION_GID}:{EntryType.SECTION.value}"] = cache_entry

        # Act
        result = await sections_client.get_async(SECTION_GID)

        # Assert: Got cached data
        assert isinstance(result, Section)
        assert result.gid == SECTION_GID
        assert result.name == "Cached Section"

        # Assert: No HTTP call was made
        mock_http.get.assert_not_called()

    async def test_cache_hit_raw_returns_cached_dict(
        self,
        sections_client: SectionsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache hit with raw=True, return cached dict."""
        # Arrange
        cache_entry = make_cache_entry(gid=SECTION_GID, name="Cached Section")
        cache_provider._cache[f"{SECTION_GID}:{EntryType.SECTION.value}"] = cache_entry

        # Act
        result = await sections_client.get_async(SECTION_GID, raw=True)

        # Assert: Got dict, not Section model
        assert isinstance(result, dict)
        assert result["gid"] == SECTION_GID
        assert result["name"] == "Cached Section"

        # Assert: No HTTP call was made
        mock_http.get.assert_not_called()


class TestCacheMissFlow:
    """Tests for cache miss scenarios (per ADR-0119)."""

    async def test_cache_miss_fetches_from_api(
        self,
        sections_client: SectionsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache miss, fetch from API."""
        # Arrange: Empty cache, mock HTTP response
        mock_http.get.return_value = make_section_data(
            gid=SECTION_GID, name="API Section"
        )

        # Act
        result = await sections_client.get_async(SECTION_GID)

        # Assert: Got API data
        assert isinstance(result, Section)
        assert result.gid == SECTION_GID
        assert result.name == "API Section"

        # Assert: HTTP was called
        mock_http.get.assert_called_once()
        assert f"/sections/{SECTION_GID}" in str(mock_http.get.call_args)

    async def test_cache_miss_stores_result_in_cache(
        self,
        sections_client: SectionsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """After cache miss, store API result in cache."""
        # Arrange
        mock_http.get.return_value = make_section_data(
            gid=SECTION_GID, name="API Section"
        )

        # Act
        await sections_client.get_async(SECTION_GID)

        # Assert: Cache was populated
        assert len(cache_provider.set_versioned_calls) == 1
        key, entry = cache_provider.set_versioned_calls[0]
        assert key == SECTION_GID
        assert entry.data["name"] == "API Section"
        assert entry.entry_type == EntryType.SECTION

    async def test_cache_miss_uses_correct_ttl(
        self,
        sections_client: SectionsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss stores with 1800s (30 min) TTL per TDD-CACHE-UTILIZATION."""
        # Arrange
        mock_http.get.return_value = make_section_data(
            gid=SECTION_GID, name="API Section"
        )

        # Act
        await sections_client.get_async(SECTION_GID)

        # Assert: Cache entry has correct TTL
        assert len(cache_provider.set_versioned_calls) == 1
        _, entry = cache_provider.set_versioned_calls[0]
        assert entry.ttl == 1800  # 30 minutes

    async def test_cache_miss_raw_stores_and_returns_dict(
        self,
        sections_client: SectionsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss with raw=True stores data and returns dict."""
        # Arrange
        mock_http.get.return_value = make_section_data(
            gid=SECTION_GID, name="API Section"
        )

        # Act
        result = await sections_client.get_async(SECTION_GID, raw=True)

        # Assert: Got dict
        assert isinstance(result, dict)
        assert result["gid"] == SECTION_GID

        # Assert: Cache was populated
        assert len(cache_provider.set_versioned_calls) == 1


class TestCacheExpiration:
    """Tests for TTL expiration behavior."""

    async def test_expired_cache_entry_triggers_api_call(
        self,
        sections_client: SectionsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Expired cache entry is treated as miss."""
        # Arrange: Expired entry (cached 1 hour ago, 1800s TTL)
        expired_entry = CacheEntry(
            key=SECTION_GID,
            data=make_section_data(gid=SECTION_GID, name="Expired Section"),
            entry_type=EntryType.SECTION,
            version=datetime.now(UTC),
            cached_at=datetime.now(UTC) - timedelta(hours=1),
            ttl=1800,  # 30 min TTL, but cached 1 hour ago
        )
        cache_provider._cache[f"{SECTION_GID}:{EntryType.SECTION.value}"] = (
            expired_entry
        )

        mock_http.get.return_value = make_section_data(
            gid=SECTION_GID, name="Fresh Section"
        )

        # Act
        result = await sections_client.get_async(SECTION_GID)

        # Assert: Got fresh API data
        assert result.name == "Fresh Section"

        # Assert: HTTP was called
        mock_http.get.assert_called_once()


class TestNoCacheProvider:
    """Tests when no cache provider is configured."""

    async def test_no_cache_always_fetches_from_api(
        self,
        sections_client_no_cache: SectionsClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Without cache provider, always fetch from API."""
        # Arrange
        mock_http.get.return_value = make_section_data(
            gid=SECTION_GID, name="API Section"
        )

        # Act
        result = await sections_client_no_cache.get_async(SECTION_GID)

        # Assert
        assert isinstance(result, Section)
        assert result.name == "API Section"
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
        sections_client = SectionsClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            cache_provider=failing_cache,  # type: ignore[arg-type]
        )

        mock_http.get.return_value = make_section_data(
            gid=SECTION_GID, name="Fallback Section"
        )

        # Act: Should not raise, should fall back to API
        result = await sections_client.get_async(SECTION_GID)

        # Assert: Got API data despite cache failure
        assert isinstance(result, Section)
        assert result.name == "Fallback Section"
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
        sections_client = SectionsClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            cache_provider=failing_cache,  # type: ignore[arg-type]
        )

        mock_http.get.return_value = make_section_data(
            gid=SECTION_GID, name="API Section"
        )

        # Act: Should not raise despite cache set failure
        result = await sections_client.get_async(SECTION_GID)

        # Assert: Got result despite cache failure
        assert isinstance(result, Section)
        assert result.name == "API Section"


class TestGidValidation:
    """Tests for GID validation at method entry (per ADR-0119)."""

    async def test_invalid_gid_raises_validation_error(
        self,
        sections_client: SectionsClient,
    ) -> None:
        """Invalid GID raises GidValidationError before cache/API call."""
        # Act & Assert
        with pytest.raises(GidValidationError) as exc_info:
            await sections_client.get_async("invalid-gid")

        assert "section_gid" in str(exc_info.value)

    async def test_empty_gid_raises_validation_error(
        self,
        sections_client: SectionsClient,
    ) -> None:
        """Empty GID raises GidValidationError."""
        with pytest.raises(GidValidationError):
            await sections_client.get_async("")


class TestBatchCachePopulation:
    """Tests for batch cache population in list_for_project_async (per ADR-0120)."""

    async def test_list_for_project_populates_cache(
        self,
        sections_client: SectionsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """list_for_project_async populates cache with set_batch."""
        # Arrange: Mock paginated response with multiple sections
        section1 = make_section_data(gid="111111111", name="Section 1")
        section2 = make_section_data(gid="222222222", name="Section 2")
        section3 = make_section_data(gid="333333333", name="Section 3")
        mock_http.get_paginated.return_value = ([section1, section2, section3], None)

        # Act: Collect all sections from iterator
        iterator = sections_client.list_for_project_async(PROJECT_GID)
        sections = await iterator.collect()

        # Assert: Got all sections
        assert len(sections) == 3
        assert sections[0].name == "Section 1"
        assert sections[1].name == "Section 2"
        assert sections[2].name == "Section 3"

        # Assert: set_batch was called
        assert len(cache_provider.set_batch_calls) == 1

        # Assert: All sections were cached
        batch_entries = cache_provider.set_batch_calls[0]
        assert len(batch_entries) == 3
        assert "111111111" in batch_entries
        assert "222222222" in batch_entries
        assert "333333333" in batch_entries

        # Assert: Entries have correct type and TTL
        for entry in batch_entries.values():
            assert entry.entry_type == EntryType.SECTION
            assert entry.ttl == 1800

    async def test_list_for_project_cache_entries_can_be_retrieved(
        self,
        sections_client: SectionsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cached entries from list can be retrieved by get_async."""
        # Arrange: Mock paginated response
        section1 = make_section_data(gid="111111111", name="Section 1")
        mock_http.get_paginated.return_value = ([section1], None)

        # Act: Collect sections (populates cache)
        iterator = sections_client.list_for_project_async(PROJECT_GID)
        await iterator.collect()

        # Now get the section individually - should hit cache
        mock_http.get.reset_mock()  # Reset to verify no new calls
        result = await sections_client.get_async("111111111")

        # Assert: Got cached data without HTTP call
        assert isinstance(result, Section)
        assert result.gid == "111111111"
        assert result.name == "Section 1"
        mock_http.get.assert_not_called()

    async def test_list_for_project_empty_page_no_batch_call(
        self,
        sections_client: SectionsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Empty page does not call set_batch."""
        # Arrange: Empty response
        mock_http.get_paginated.return_value = ([], None)

        # Act
        iterator = sections_client.list_for_project_async(PROJECT_GID)
        sections = await iterator.collect()

        # Assert: No sections
        assert len(sections) == 0

        # Assert: set_batch was NOT called
        assert len(cache_provider.set_batch_calls) == 0

    async def test_list_for_project_no_cache_still_works(
        self,
        sections_client_no_cache: SectionsClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """list_for_project_async works without cache provider."""
        # Arrange
        section1 = make_section_data(gid="111111111", name="Section 1")
        mock_http.get_paginated.return_value = ([section1], None)

        # Act
        iterator = sections_client_no_cache.list_for_project_async(PROJECT_GID)
        sections = await iterator.collect()

        # Assert: Got sections (no cache, just API)
        assert len(sections) == 1
        assert sections[0].name == "Section 1"

    async def test_list_for_project_cache_failure_still_returns_data(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """list_for_project_async returns data even if cache fails (graceful degradation)."""
        # Arrange: Failing cache provider
        failing_cache = FailingCacheProvider()
        sections_client = SectionsClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            cache_provider=failing_cache,  # type: ignore[arg-type]
        )

        section1 = make_section_data(gid="111111111", name="Section 1")
        mock_http.get_paginated.return_value = ([section1], None)

        # Act: Should not raise despite cache failure
        iterator = sections_client.list_for_project_async(PROJECT_GID)
        sections = await iterator.collect()

        # Assert: Got sections despite cache failure
        assert len(sections) == 1
        assert sections[0].name == "Section 1"


class TestOptFields:
    """Tests for opt_fields parameter handling with cache."""

    async def test_cache_hit_ignores_opt_fields(
        self,
        sections_client: SectionsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache hit returns cached data regardless of opt_fields."""
        # Arrange: Pre-populate cache
        cache_entry = make_cache_entry(gid=SECTION_GID, name="Cached Section")
        cache_provider._cache[f"{SECTION_GID}:{EntryType.SECTION.value}"] = cache_entry

        # Act
        result = await sections_client.get_async(SECTION_GID, opt_fields=["name"])

        # Assert: Got cached data without HTTP call
        assert result.name == "Cached Section"
        mock_http.get.assert_not_called()

    async def test_cache_miss_passes_opt_fields_to_api(
        self,
        sections_client: SectionsClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache miss passes opt_fields to API."""
        # Arrange
        mock_http.get.return_value = make_section_data(
            gid=SECTION_GID, name="API Section"
        )

        # Act
        await sections_client.get_async(SECTION_GID, opt_fields=["name"])

        # Assert: opt_fields passed to HTTP
        mock_http.get.assert_called_once()
        call_args = mock_http.get.call_args
        assert "opt_fields" in call_args[1]["params"]
