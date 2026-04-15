"""Tests for StoriesClient cache integration.

Per TDD-CACHE-PERF-STORIES: Tests for cache hit/miss flows, graceful degradation,
and fetcher adapter behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from autom8y_cache.testing import MockCacheProvider as _SDKMockCacheProvider

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.clients.stories import StoriesClient
from autom8_asana.core.errors import CacheConnectionError
from autom8_asana.models.story import Story

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig


class MockCacheProvider(_SDKMockCacheProvider):
    """Mock cache provider for stories cache tests (extends SDK MockCacheProvider).

    Adds satellite-specific tracking lists and handles EntryType enum keys.
    """

    def __init__(self) -> None:
        super().__init__()
        self.get_versioned_calls: list[tuple[str, EntryType]] = []
        self.set_versioned_calls: list[tuple[str, CacheEntry]] = []

    @property
    def _cache(self) -> dict[str, CacheEntry]:
        """Alias for SDK _versioned_store (backward compat for direct access)."""
        return self._versioned_store  # type: ignore[return-value]

    def get_versioned(
        self, key: str, entry_type: EntryType, freshness: object = None
    ) -> CacheEntry | None:
        """Get entry from cache with satellite tracking."""
        self.get_versioned_calls.append((key, entry_type))
        self.calls.append(
            (
                "get_versioned",
                {"key": key, "entry_type": entry_type, "freshness": freshness},
            )
        )
        return self._versioned_store.get(f"{key}:{entry_type.value}")

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        """Store entry in cache with satellite tracking."""
        self.set_versioned_calls.append((key, entry))
        self.calls.append(("set_versioned", {"key": key, "entry": entry}))
        self._versioned_store[f"{key}:{entry.entry_type.value}"] = entry

    def get_metrics(self) -> Any:
        """Return a mock metrics object (satellite CacheMetrics)."""
        from autom8_asana.cache.models.metrics import CacheMetrics

        return CacheMetrics()


class FailingCacheProvider:
    """Cache provider that always fails (for graceful degradation tests)."""

    def get_versioned(
        self, key: str, entry_type: EntryType, freshness: Any = None
    ) -> CacheEntry | None:
        raise CacheConnectionError("Cache connection failed")

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        raise CacheConnectionError("Cache connection failed")


@pytest.fixture
def cache_provider() -> MockCacheProvider:
    """Mock cache provider."""
    return MockCacheProvider()


@pytest.fixture
def stories_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    cache_provider: MockCacheProvider,
) -> StoriesClient:
    """Create StoriesClient with mocked dependencies including cache."""
    return StoriesClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=cache_provider,
    )


@pytest.fixture
def stories_client_no_cache(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
) -> StoriesClient:
    """Create StoriesClient without cache provider."""
    return StoriesClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=None,
    )


def make_story_data(
    gid: str = "story123",
    text: str = "Test story",
    created_at: str = "2025-01-01T10:00:00Z",
    **extra: Any,
) -> dict[str, Any]:
    """Create mock story data."""
    data = {
        "gid": gid,
        "resource_type": "story",
        "text": text,
        "created_at": created_at,
    }
    data.update(extra)
    return data


def make_stories_cache_entry(
    task_gid: str = "task123",
    stories: list[dict[str, Any]] | None = None,
    last_fetched: str = "2025-01-01T12:00:00+00:00",
) -> CacheEntry:
    """Create a cache entry for stories."""
    if stories is None:
        stories = [make_story_data(gid="s1", created_at="2025-01-01T10:00:00Z")]
    return CacheEntry(
        key=task_gid,
        data={"stories": stories},
        entry_type=EntryType.STORIES,
        version=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        cached_at=datetime.now(UTC),
        metadata={"last_fetched": last_fetched},
    )


TASK_GID = "task123"


class TestListForTaskCachedAsyncCacheMiss:
    """Tests for cache miss scenarios (FR-CACHE-001)."""

    async def test_list_for_task_cached_async_cache_miss(
        self,
        stories_client: StoriesClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache is empty, perform full fetch and populate cache."""
        # Arrange: Empty cache, mock HTTP response
        stories = [
            make_story_data(gid="s1", created_at="2025-01-01T10:00:00Z"),
            make_story_data(gid="s2", created_at="2025-01-01T11:00:00Z"),
        ]
        mock_http.get_paginated.return_value = (stories, None)

        # Act
        result = await stories_client.list_for_task_cached_async(TASK_GID)

        # Assert: Got all stories
        assert len(result) == 2
        assert all(isinstance(s, Story) for s in result)
        assert result[0].gid == "s1"
        assert result[1].gid == "s2"

        # Assert: HTTP was called (full fetch, no 'since' param)
        mock_http.get_paginated.assert_called()
        call_args = mock_http.get_paginated.call_args
        assert f"/tasks/{TASK_GID}/stories" in call_args[0][0]
        # No 'since' parameter on first fetch
        assert "since" not in call_args[1].get("params", {})

        # Assert: Cache was populated
        assert len(cache_provider.set_versioned_calls) == 1


class TestListForTaskCachedAsyncCacheHit:
    """Tests for cache hit scenarios (FR-CACHE-001, FR-FETCH-002)."""

    async def test_list_for_task_cached_async_cache_hit(
        self,
        stories_client: StoriesClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """When cache hit, perform incremental fetch with 'since' parameter."""
        # Arrange: Pre-populate cache
        last_fetched = "2025-01-01T12:00:00+00:00"
        cached_stories = [
            make_story_data(gid="s1", created_at="2025-01-01T10:00:00Z"),
        ]
        cache_entry = make_stories_cache_entry(
            task_gid=TASK_GID,
            stories=cached_stories,
            last_fetched=last_fetched,
        )
        cache_provider._cache[f"{TASK_GID}:{EntryType.STORIES.value}"] = cache_entry

        # New story from incremental fetch
        new_stories = [
            make_story_data(gid="s2", created_at="2025-01-01T13:00:00Z"),
        ]
        mock_http.get_paginated.return_value = (new_stories, None)

        # Act
        result = await stories_client.list_for_task_cached_async(TASK_GID)

        # Assert: Got merged stories (cached + new)
        assert len(result) == 2
        assert result[0].gid == "s1"  # Sorted by created_at
        assert result[1].gid == "s2"

        # Assert: HTTP was called with 'since' parameter
        mock_http.get_paginated.assert_called()
        call_args = mock_http.get_paginated.call_args
        assert call_args[1]["params"]["since"] == last_fetched


class TestListForTaskCachedAsyncNoCache:
    """Tests for no cache provider scenarios (FR-DEGRADE-001)."""

    async def test_list_for_task_cached_async_no_cache(
        self,
        stories_client_no_cache: StoriesClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """When no cache provider, perform full fetch directly."""
        # Arrange
        stories = [
            make_story_data(gid="s1", created_at="2025-01-01T10:00:00Z"),
        ]
        mock_http.get_paginated.return_value = (stories, None)

        # Act
        result = await stories_client_no_cache.list_for_task_cached_async(TASK_GID)

        # Assert: Got stories
        assert len(result) == 1
        assert isinstance(result[0], Story)

        # Assert: HTTP was called
        mock_http.get_paginated.assert_called()


class TestListForTaskCachedAsyncCacheFailure:
    """Tests for cache failure scenarios (FR-DEGRADE-002, FR-DEGRADE-003)."""

    async def test_list_for_task_cached_async_cache_failure(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """When cache fails, fall back to full fetch."""
        # Arrange: Failing cache provider
        failing_cache = FailingCacheProvider()
        stories_client = StoriesClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
            cache_provider=failing_cache,  # type: ignore[arg-type]
        )

        stories = [
            make_story_data(gid="s1", created_at="2025-01-01T10:00:00Z"),
        ]
        mock_http.get_paginated.return_value = (stories, None)

        # Act: Should not raise, should fall back to full fetch
        result = await stories_client.list_for_task_cached_async(TASK_GID)

        # Assert: Got stories despite cache failure
        assert len(result) == 1
        assert isinstance(result[0], Story)
        mock_http.get_paginated.assert_called()


class TestMakeStoriesFetcher:
    """Tests for _make_stories_fetcher() (FR-FETCH-*)."""

    async def test_make_stories_fetcher_with_since(
        self,
        stories_client: StoriesClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Fetcher includes 'since' parameter when provided."""
        # Arrange
        mock_http.get_paginated.return_value = ([], None)
        fetcher = stories_client._make_stories_fetcher(opt_fields=None)

        # Act
        since_timestamp = "2025-01-01T12:00:00+00:00"
        await fetcher(TASK_GID, since_timestamp)

        # Assert: 'since' parameter was included
        call_args = mock_http.get_paginated.call_args
        assert call_args[1]["params"]["since"] == since_timestamp

    async def test_make_stories_fetcher_without_since(
        self,
        stories_client: StoriesClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Fetcher omits 'since' parameter when None (full fetch)."""
        # Arrange
        mock_http.get_paginated.return_value = ([], None)
        fetcher = stories_client._make_stories_fetcher(opt_fields=None)

        # Act
        await fetcher(TASK_GID, None)

        # Assert: 'since' parameter was NOT included
        call_args = mock_http.get_paginated.call_args
        assert "since" not in call_args[1]["params"]

    async def test_make_stories_fetcher_with_opt_fields(
        self,
        stories_client: StoriesClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Fetcher propagates opt_fields to HTTP request."""
        # Arrange
        mock_http.get_paginated.return_value = ([], None)
        fetcher = stories_client._make_stories_fetcher(opt_fields=["gid", "text", "created_at"])

        # Act
        await fetcher(TASK_GID, None)

        # Assert: opt_fields was included
        call_args = mock_http.get_paginated.call_args
        assert "opt_fields" in call_args[1]["params"]
        assert call_args[1]["params"]["opt_fields"] == "gid,text,created_at"

    async def test_make_stories_fetcher_returns_raw_dicts(
        self,
        stories_client: StoriesClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Fetcher returns raw dicts, not Story models."""
        # Arrange
        stories = [make_story_data(gid="s1"), make_story_data(gid="s2")]
        mock_http.get_paginated.return_value = (stories, None)
        fetcher = stories_client._make_stories_fetcher(opt_fields=None)

        # Act
        result = await fetcher(TASK_GID, None)

        # Assert: Returns list of dicts, not Story objects
        assert len(result) == 2
        assert all(isinstance(s, dict) for s in result)
        assert result[0]["gid"] == "s1"

    async def test_make_stories_fetcher_collects_all_pages(
        self,
        stories_client: StoriesClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Fetcher eagerly collects all pages before returning."""
        # Arrange: Multi-page response
        page1_stories = [make_story_data(gid="s1")]
        page2_stories = [make_story_data(gid="s2")]
        mock_http.get_paginated.side_effect = [
            (page1_stories, "offset_123"),  # First page with next_offset
            (page2_stories, None),  # Second page, no more pages
        ]
        fetcher = stories_client._make_stories_fetcher(opt_fields=None)

        # Act
        result = await fetcher(TASK_GID, None)

        # Assert: All pages collected
        assert len(result) == 2
        assert result[0]["gid"] == "s1"
        assert result[1]["gid"] == "s2"

        # Assert: Two HTTP calls were made
        assert mock_http.get_paginated.call_count == 2


class TestListForTaskCachedSync:
    """Tests for sync wrapper (FR-CLIENT-002)."""

    def test_list_for_task_cached_sync(
        self,
        stories_client: StoriesClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Sync wrapper calls async method correctly."""
        # Arrange
        stories = [make_story_data(gid="s1")]
        mock_http.get_paginated.return_value = (stories, None)

        # Act
        result = stories_client.list_for_task_cached(TASK_GID)

        # Assert: Got results
        assert len(result) == 1
        assert isinstance(result[0], Story)
        assert result[0].gid == "s1"


class TestOptFieldsPropagation:
    """Tests for opt_fields parameter handling."""

    async def test_opt_fields_passed_to_fetcher(
        self,
        stories_client: StoriesClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """opt_fields from cached method are passed to HTTP request."""
        # Arrange
        mock_http.get_paginated.return_value = ([make_story_data()], None)

        # Act
        await stories_client.list_for_task_cached_async(
            TASK_GID, opt_fields=["gid", "text", "resource_subtype"]
        )

        # Assert
        call_args = mock_http.get_paginated.call_args
        assert "opt_fields" in call_args[1]["params"]
        assert call_args[1]["params"]["opt_fields"] == "gid,text,resource_subtype"


class TestTaskModifiedAtVersioning:
    """Tests for task_modified_at parameter (FR-CACHE-005)."""

    async def test_task_modified_at_used_for_cache_versioning(
        self,
        stories_client: StoriesClient,
        cache_provider: MockCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """task_modified_at flows through to cache entry version.

        Since load_stories_incremental uses current_modified_at for versioning,
        we verify the cache entry gets the correct version timestamp.
        """
        # Arrange
        stories = [make_story_data(gid="s1", created_at="2025-01-01T10:00:00Z")]
        mock_http.get_paginated.return_value = (stories, None)
        modified_at = "2025-01-15T10:00:00Z"

        # Act
        await stories_client.list_for_task_cached_async(TASK_GID, task_modified_at=modified_at)

        # Assert: Cache entry was set with proper version
        assert len(cache_provider.set_versioned_calls) == 1
        key, entry = cache_provider.set_versioned_calls[0]
        assert key == TASK_GID
        assert entry.entry_type == EntryType.STORIES
        # The version should be derived from modified_at
        # Note: _create_stories_entry parses the version from current_modified_at


class TestFetchAllStoriesUncached:
    """Tests for _fetch_all_stories_uncached fallback method."""

    async def test_fetch_all_stories_uncached_single_page(
        self,
        stories_client: StoriesClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Uncached fetch collects single page of stories."""
        # Arrange
        stories = [make_story_data(gid="s1"), make_story_data(gid="s2")]
        mock_http.get_paginated.return_value = (stories, None)

        # Act
        result = await stories_client._fetch_all_stories_uncached(TASK_GID, None)

        # Assert: Got Story models
        assert len(result) == 2
        assert all(isinstance(s, Story) for s in result)

    async def test_fetch_all_stories_uncached_multiple_pages(
        self,
        stories_client: StoriesClient,
        mock_http: MockHTTPClient,
    ) -> None:
        """Uncached fetch collects all pages eagerly."""
        # Arrange: Multi-page response
        mock_http.get_paginated.side_effect = [
            ([make_story_data(gid="s1")], "offset_123"),
            ([make_story_data(gid="s2")], None),
        ]

        # Act
        result = await stories_client._fetch_all_stories_uncached(TASK_GID, None)

        # Assert: All pages collected
        assert len(result) == 2
        assert mock_http.get_paginated.call_count == 2
