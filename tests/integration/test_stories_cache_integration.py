"""Integration tests for stories cache incremental behavior.

Per TDD-CACHE-PERF-STORIES Section 12.3:
Tests that verify end-to-end cache flow, persistence across calls,
incremental merge behavior, and sync wrapper integration.

Test Strategy:
- Uses EnhancedInMemoryCacheProvider for realistic caching behavior
- Mocks HTTP client for deterministic API responses
- Validates metrics recording for incremental vs full fetches
- Tests complete data flow from client through cache to model
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.cache.models.entry import EntryType
from autom8_asana.clients.stories import StoriesClient
from autom8_asana.config import AsanaConfig
from autom8_asana.models.story import Story


class MockHTTPClient:
    """Mock HTTP client for integration testing."""

    def __init__(self) -> None:
        self.get = AsyncMock()
        self.post = AsyncMock()
        self.put = AsyncMock()
        self.delete = AsyncMock()
        self.get_paginated = AsyncMock()
        self.call_history: list[tuple[str, dict[str, Any]]] = []

    def track_call(self, endpoint: str, params: dict[str, Any]) -> None:
        """Track API calls for assertion."""
        self.call_history.append((endpoint, params.copy()))


class MockAuthProvider:
    """Mock auth provider for testing."""

    def get_secret(self, key: str) -> str:
        return "test-token"


def make_story_data(
    gid: str,
    text: str = "Test story",
    created_at: str = "2025-01-01T10:00:00Z",
    resource_subtype: str = "comment_added",
    **extra: Any,
) -> dict[str, Any]:
    """Create mock story data."""
    data = {
        "gid": gid,
        "resource_type": "story",
        "resource_subtype": resource_subtype,
        "text": text,
        "created_at": created_at,
    }
    data.update(extra)
    return data


TASK_GID = "integration_task_123"


@pytest.fixture
def cache_provider() -> EnhancedInMemoryCacheProvider:
    """Create real in-memory cache provider for integration tests."""
    return EnhancedInMemoryCacheProvider(default_ttl=300, max_size=1000)


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
def stories_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    cache_provider: EnhancedInMemoryCacheProvider,
) -> StoriesClient:
    """Create StoriesClient with real cache provider."""
    return StoriesClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=cache_provider,
    )


class TestEndToEndCacheFlow:
    """Test complete cache flow with EnhancedInMemoryCacheProvider."""

    @pytest.mark.asyncio
    async def test_first_call_populates_cache(
        self,
        stories_client: StoriesClient,
        cache_provider: EnhancedInMemoryCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """First call should perform full fetch and populate cache.

        Verifies:
        - Full fetch occurs (no 'since' parameter)
        - Cache entry is created with stories data
        - Cache entry includes last_fetched metadata
        """
        # Arrange: Initial stories from API
        initial_stories = [
            make_story_data("s1", created_at="2025-01-01T10:00:00Z"),
            make_story_data("s2", created_at="2025-01-01T11:00:00Z"),
            make_story_data("s3", created_at="2025-01-01T12:00:00Z"),
        ]
        mock_http.get_paginated.return_value = (initial_stories, None)

        # Act: First call
        result = await stories_client.list_for_task_cached_async(TASK_GID)

        # Assert: Got all stories as Story models
        assert len(result) == 3
        assert all(isinstance(s, Story) for s in result)
        assert [s.gid for s in result] == ["s1", "s2", "s3"]

        # Assert: HTTP was called without 'since' parameter
        mock_http.get_paginated.assert_called_once()
        call_args = mock_http.get_paginated.call_args
        assert f"/tasks/{TASK_GID}/stories" in call_args[0][0]
        assert "since" not in call_args[1].get("params", {})

        # Assert: Cache entry was created
        cache_entry = cache_provider.get_versioned(TASK_GID, EntryType.STORIES)
        assert cache_entry is not None
        assert "stories" in cache_entry.data
        assert len(cache_entry.data["stories"]) == 3
        assert "last_fetched" in cache_entry.metadata

    @pytest.mark.asyncio
    async def test_second_call_uses_incremental_fetch(
        self,
        stories_client: StoriesClient,
        cache_provider: EnhancedInMemoryCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Second call should use incremental fetch with 'since' parameter.

        Verifies:
        - First call populates cache
        - Second call includes 'since' parameter
        - New stories are merged with cached stories
        """
        # Arrange: First call with initial stories
        initial_stories = [
            make_story_data("s1", created_at="2025-01-01T10:00:00Z"),
        ]
        mock_http.get_paginated.return_value = (initial_stories, None)

        await stories_client.list_for_task_cached_async(TASK_GID)

        # Get last_fetched from cache for verification
        cache_entry = cache_provider.get_versioned(TASK_GID, EntryType.STORIES)
        assert cache_entry is not None
        last_fetched = cache_entry.metadata.get("last_fetched")
        assert last_fetched is not None

        # Arrange: Second call returns new story
        new_stories = [
            make_story_data("s2", created_at="2025-01-01T13:00:00Z"),
        ]
        mock_http.get_paginated.reset_mock()
        mock_http.get_paginated.return_value = (new_stories, None)

        # Act: Second call
        result = await stories_client.list_for_task_cached_async(TASK_GID)

        # Assert: Merged result (cached + new)
        assert len(result) == 2
        assert result[0].gid == "s1"  # Original (sorted by created_at)
        assert result[1].gid == "s2"  # New

        # Assert: HTTP was called WITH 'since' parameter
        mock_http.get_paginated.assert_called_once()
        call_args = mock_http.get_paginated.call_args
        assert call_args[1]["params"]["since"] == last_fetched


class TestCachePersistenceAcrossCalls:
    """Test cache persistence and data integrity."""

    @pytest.mark.asyncio
    async def test_cache_survives_multiple_calls(
        self,
        stories_client: StoriesClient,
        cache_provider: EnhancedInMemoryCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Cache should persist data across multiple incremental calls.

        Verifies:
        - Multiple incremental fetches accumulate stories correctly
        - Cache always contains merged result
        - No duplicate stories by GID
        """
        # First call: 2 stories
        mock_http.get_paginated.return_value = (
            [
                make_story_data("s1", created_at="2025-01-01T10:00:00Z"),
                make_story_data("s2", created_at="2025-01-01T11:00:00Z"),
            ],
            None,
        )
        result1 = await stories_client.list_for_task_cached_async(TASK_GID)
        assert len(result1) == 2

        # Second call: 1 new story
        mock_http.get_paginated.return_value = (
            [make_story_data("s3", created_at="2025-01-01T12:00:00Z")],
            None,
        )
        result2 = await stories_client.list_for_task_cached_async(TASK_GID)
        assert len(result2) == 3

        # Third call: 2 new stories
        mock_http.get_paginated.return_value = (
            [
                make_story_data("s4", created_at="2025-01-01T13:00:00Z"),
                make_story_data("s5", created_at="2025-01-01T14:00:00Z"),
            ],
            None,
        )
        result3 = await stories_client.list_for_task_cached_async(TASK_GID)
        assert len(result3) == 5

        # Verify all stories are in cache
        cache_entry = cache_provider.get_versioned(TASK_GID, EntryType.STORIES)
        assert cache_entry is not None
        assert len(cache_entry.data["stories"]) == 5

        # Verify sorted by created_at
        gids = [s.gid for s in result3]
        assert gids == ["s1", "s2", "s3", "s4", "s5"]


class TestIncrementalMergeBehavior:
    """Test story merging and deduplication."""

    @pytest.mark.asyncio
    async def test_duplicate_stories_deduplicated(
        self,
        stories_client: StoriesClient,
        cache_provider: EnhancedInMemoryCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Duplicate story GIDs should be deduplicated (new takes precedence).

        Verifies:
        - Duplicate GIDs are merged correctly
        - New version of story replaces cached version
        - Final count is correct (no duplicates)
        """
        # First call: Initial story
        mock_http.get_paginated.return_value = (
            [
                make_story_data(
                    "s1", text="Original text", created_at="2025-01-01T10:00:00Z"
                )
            ],
            None,
        )
        await stories_client.list_for_task_cached_async(TASK_GID)

        # Second call: Same GID with updated text
        mock_http.get_paginated.return_value = (
            [
                make_story_data(
                    "s1", text="Updated text", created_at="2025-01-01T10:00:00Z"
                )
            ],
            None,
        )
        result = await stories_client.list_for_task_cached_async(TASK_GID)

        # Assert: Only one story, with updated text
        assert len(result) == 1
        assert result[0].gid == "s1"
        assert result[0].text == "Updated text"

    @pytest.mark.asyncio
    async def test_stories_sorted_by_created_at_after_merge(
        self,
        stories_client: StoriesClient,
        cache_provider: EnhancedInMemoryCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Merged stories should be sorted by created_at ascending.

        Note: First fetch returns stories in API order (no sorting).
        Sorting happens during merge (second+ fetch).

        Verifies:
        - Merge operation sorts all stories by created_at
        - Sort persists correctly after merge
        """
        # First call: Stories in arbitrary order (stored as-is)
        mock_http.get_paginated.return_value = (
            [
                make_story_data("s3", created_at="2025-01-01T12:00:00Z"),
                make_story_data("s1", created_at="2025-01-01T10:00:00Z"),
            ],
            None,
        )
        result1 = await stories_client.list_for_task_cached_async(TASK_GID)
        # First fetch preserves API order
        assert [s.gid for s in result1] == ["s3", "s1"]

        # Second call: New story triggers merge and sort
        mock_http.get_paginated.return_value = (
            [make_story_data("s2", created_at="2025-01-01T11:00:00Z")],
            None,
        )
        result2 = await stories_client.list_for_task_cached_async(TASK_GID)
        # After merge, stories are sorted by created_at
        assert [s.gid for s in result2] == ["s1", "s2", "s3"]


class TestSyncWrapperIntegration:
    """Test synchronous wrapper works with cache."""

    def test_sync_wrapper_uses_cache(
        self,
        stories_client: StoriesClient,
        cache_provider: EnhancedInMemoryCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Sync wrapper should use cache correctly.

        Verifies:
        - Sync method calls async method via wrapper
        - Cache is populated and used
        - Returns same type as async method
        """
        # Arrange: First call
        mock_http.get_paginated.return_value = (
            [make_story_data("s1", created_at="2025-01-01T10:00:00Z")],
            None,
        )

        # Act: First sync call
        result1 = stories_client.list_for_task_cached(TASK_GID)
        assert len(result1) == 1
        assert isinstance(result1[0], Story)

        # Verify cache populated
        cache_entry = cache_provider.get_versioned(TASK_GID, EntryType.STORIES)
        assert cache_entry is not None

        # Second call with new story
        mock_http.get_paginated.reset_mock()
        mock_http.get_paginated.return_value = (
            [make_story_data("s2", created_at="2025-01-01T11:00:00Z")],
            None,
        )

        # Act: Second sync call
        result2 = stories_client.list_for_task_cached(TASK_GID)
        assert len(result2) == 2

        # Verify incremental fetch used (since param present)
        call_args = mock_http.get_paginated.call_args
        assert "since" in call_args[1]["params"]


class TestMetricsIntegration:
    """Test that metrics are recorded correctly during cache operations."""

    @pytest.mark.asyncio
    async def test_full_fetch_recorded_on_cache_miss(
        self,
        stories_client: StoriesClient,
        cache_provider: EnhancedInMemoryCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Full fetch metric should be recorded on cache miss.

        Verifies:
        - full_fetches counter increments on first call
        - incremental_fetches stays at 0
        """
        mock_http.get_paginated.return_value = (
            [make_story_data("s1")],
            None,
        )

        # Act: First call (cache miss)
        await stories_client.list_for_task_cached_async(TASK_GID)

        # Assert: Check metrics
        metrics = cache_provider.get_metrics()
        assert metrics.full_fetches == 1
        assert metrics.incremental_fetches == 0

    @pytest.mark.asyncio
    async def test_incremental_fetch_recorded_on_cache_hit(
        self,
        stories_client: StoriesClient,
        cache_provider: EnhancedInMemoryCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Incremental fetch metric should be recorded on cache hit.

        Verifies:
        - First call records full_fetch
        - Second call records incremental_fetch
        """
        mock_http.get_paginated.return_value = ([make_story_data("s1")], None)

        # First call (cache miss)
        await stories_client.list_for_task_cached_async(TASK_GID)

        # Second call (cache hit)
        mock_http.get_paginated.return_value = ([], None)
        await stories_client.list_for_task_cached_async(TASK_GID)

        # Assert: Check metrics
        metrics = cache_provider.get_metrics()
        assert metrics.full_fetches == 1
        assert metrics.incremental_fetches == 1

    @pytest.mark.asyncio
    async def test_metrics_snapshot_includes_fetch_counts(
        self,
        stories_client: StoriesClient,
        cache_provider: EnhancedInMemoryCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Metrics snapshot should include fetch type counts and rate.

        Verifies:
        - snapshot() includes incremental_fetches
        - snapshot() includes full_fetches
        - snapshot() includes incremental_fetch_rate
        """
        mock_http.get_paginated.return_value = ([make_story_data("s1")], None)

        # Perform mixed operations
        await stories_client.list_for_task_cached_async(TASK_GID)  # full
        mock_http.get_paginated.return_value = ([], None)
        await stories_client.list_for_task_cached_async(TASK_GID)  # incremental
        await stories_client.list_for_task_cached_async(TASK_GID)  # incremental

        # Assert: Snapshot has expected fields
        snapshot = cache_provider.get_metrics().snapshot()
        assert "full_fetches" in snapshot
        assert "incremental_fetches" in snapshot
        assert "incremental_fetch_rate" in snapshot

        assert snapshot["full_fetches"] == 1
        assert snapshot["incremental_fetches"] == 2
        # Rate should be 2/3 = 0.666...
        assert 0.6 < snapshot["incremental_fetch_rate"] < 0.7


class TestOptFieldsPropagation:
    """Test that opt_fields are correctly propagated through cache path."""

    @pytest.mark.asyncio
    async def test_opt_fields_included_in_api_request(
        self,
        stories_client: StoriesClient,
        cache_provider: EnhancedInMemoryCacheProvider,
        mock_http: MockHTTPClient,
    ) -> None:
        """Custom opt_fields should be included in API request.

        Verifies:
        - opt_fields parameter reaches HTTP client
        - Format is correct (comma-separated)
        """
        mock_http.get_paginated.return_value = ([], None)

        # Act: Call with custom opt_fields
        await stories_client.list_for_task_cached_async(
            TASK_GID,
            opt_fields=["gid", "text", "created_at", "resource_subtype"],
        )

        # Assert: opt_fields in API request
        call_args = mock_http.get_paginated.call_args
        params = call_args[1]["params"]
        assert "opt_fields" in params
        assert "gid" in params["opt_fields"]
        assert "text" in params["opt_fields"]
