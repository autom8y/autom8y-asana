"""Tests for incremental story loading."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.stories import (
    DEFAULT_STORY_TYPES,
    _extract_stories_list,
    _merge_stories,
    filter_relevant_stories,
    get_latest_story_timestamp,
    load_stories_incremental,
)


class MockCacheProvider:
    """Mock cache provider for testing."""

    def __init__(self) -> None:
        self._cache: dict[str, CacheEntry] = {}

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: Any = None,
    ) -> CacheEntry | None:
        cache_key = f"{entry_type.value}:{key}"
        return self._cache.get(cache_key)

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        cache_key = f"{entry.entry_type.value}:{key}"
        self._cache[cache_key] = entry


class TestLoadStoriesIncremental:
    """Tests for load_stories_incremental function."""

    @pytest.fixture
    def cache(self) -> MockCacheProvider:
        """Create a mock cache provider."""
        return MockCacheProvider()

    @pytest.fixture
    def fetcher(self) -> AsyncMock:
        """Create a mock fetcher function."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_full_fetch_when_no_cache(
        self, cache: MockCacheProvider, fetcher: AsyncMock
    ) -> None:
        """Test full fetch when cache is empty."""
        stories = [
            {"gid": "s1", "created_at": "2025-01-01T10:00:00Z", "text": "Story 1"},
            {"gid": "s2", "created_at": "2025-01-01T11:00:00Z", "text": "Story 2"},
        ]
        fetcher.return_value = stories

        result, entry, was_incremental = await load_stories_incremental(
            task_gid="task123",
            cache=cache,
            fetcher=fetcher,
        )

        # Should do full fetch (since=None)
        fetcher.assert_called_once_with("task123", None)
        assert result == stories
        assert entry is not None
        assert not was_incremental

    @pytest.mark.asyncio
    async def test_full_fetch_when_cache_corrupted(
        self, cache: MockCacheProvider, fetcher: AsyncMock
    ) -> None:
        """Test full fetch when cache lacks last_fetched metadata."""
        # Cache entry without last_fetched metadata
        corrupted_entry = CacheEntry(
            key="task123",
            data={"stories": [{"gid": "old"}]},
            entry_type=EntryType.STORIES,
            version=datetime.now(UTC),
            metadata={},  # Missing last_fetched
        )
        cache._cache["stories:task123"] = corrupted_entry

        stories = [{"gid": "s1", "created_at": "2025-01-01T10:00:00Z"}]
        fetcher.return_value = stories

        result, entry, was_incremental = await load_stories_incremental(
            task_gid="task123",
            cache=cache,
            fetcher=fetcher,
        )

        # Should do full fetch
        fetcher.assert_called_once_with("task123", None)
        assert not was_incremental

    @pytest.mark.asyncio
    async def test_incremental_fetch_with_cache(
        self, cache: MockCacheProvider, fetcher: AsyncMock
    ) -> None:
        """Test incremental fetch when cache exists."""
        # Pre-populate cache
        last_fetched = "2025-01-01T12:00:00+00:00"
        cached_entry = CacheEntry(
            key="task123",
            data={
                "stories": [
                    {"gid": "s1", "created_at": "2025-01-01T10:00:00Z"},
                ]
            },
            entry_type=EntryType.STORIES,
            version=datetime.now(UTC),
            metadata={"last_fetched": last_fetched},
        )
        cache._cache["stories:task123"] = cached_entry

        # New stories from incremental fetch
        new_stories = [
            {"gid": "s2", "created_at": "2025-01-01T13:00:00Z"},
        ]
        fetcher.return_value = new_stories

        result, entry, was_incremental = await load_stories_incremental(
            task_gid="task123",
            cache=cache,
            fetcher=fetcher,
        )

        # Should do incremental fetch with since parameter
        fetcher.assert_called_once_with("task123", last_fetched)
        assert was_incremental
        # Should have merged stories
        assert len(result) == 2
        assert result[0]["gid"] == "s1"
        assert result[1]["gid"] == "s2"

    @pytest.mark.asyncio
    async def test_merge_dedupes_by_gid(
        self, cache: MockCacheProvider, fetcher: AsyncMock
    ) -> None:
        """Test that merge deduplicates stories by GID."""
        # Pre-populate cache
        cached_entry = CacheEntry(
            key="task123",
            data={
                "stories": [
                    {"gid": "s1", "created_at": "2025-01-01T10:00:00Z", "text": "Old"},
                ]
            },
            entry_type=EntryType.STORIES,
            version=datetime.now(UTC),
            metadata={"last_fetched": "2025-01-01T12:00:00+00:00"},
        )
        cache._cache["stories:task123"] = cached_entry

        # New stories include an update to s1
        new_stories = [
            {"gid": "s1", "created_at": "2025-01-01T10:00:00Z", "text": "Updated"},
        ]
        fetcher.return_value = new_stories

        result, _, _ = await load_stories_incremental(
            task_gid="task123",
            cache=cache,
            fetcher=fetcher,
        )

        # Should have only one s1, with updated text
        assert len(result) == 1
        assert result[0]["text"] == "Updated"

    @pytest.mark.asyncio
    async def test_cache_entry_has_last_fetched(
        self, cache: MockCacheProvider, fetcher: AsyncMock
    ) -> None:
        """Test that new cache entry has last_fetched metadata."""
        fetcher.return_value = []

        _, entry, _ = await load_stories_incremental(
            task_gid="task123",
            cache=cache,
            fetcher=fetcher,
        )

        assert entry is not None
        assert "last_fetched" in entry.metadata
        # last_fetched should be a valid ISO timestamp
        datetime.fromisoformat(entry.metadata["last_fetched"].replace("Z", "+00:00"))


class TestMergeStories:
    """Tests for _merge_stories function."""

    def test_merge_empty_lists(self) -> None:
        """Test merging two empty lists."""
        result = _merge_stories([], [])
        assert result == []

    def test_merge_with_empty_existing(self) -> None:
        """Test merging when existing is empty."""
        new = [{"gid": "s1", "created_at": "2025-01-01T10:00:00Z"}]
        result = _merge_stories([], new)
        assert result == new

    def test_merge_with_empty_new(self) -> None:
        """Test merging when new is empty."""
        existing = [{"gid": "s1", "created_at": "2025-01-01T10:00:00Z"}]
        result = _merge_stories(existing, [])
        assert result == existing

    def test_merge_no_overlap(self) -> None:
        """Test merging lists with no overlap."""
        existing = [{"gid": "s1", "created_at": "2025-01-01T10:00:00Z"}]
        new = [{"gid": "s2", "created_at": "2025-01-01T11:00:00Z"}]

        result = _merge_stories(existing, new)

        assert len(result) == 2
        assert result[0]["gid"] == "s1"
        assert result[1]["gid"] == "s2"

    def test_merge_with_overlap(self) -> None:
        """Test merging lists with overlapping GIDs."""
        existing = [
            {"gid": "s1", "created_at": "2025-01-01T10:00:00Z", "version": 1},
        ]
        new = [
            {"gid": "s1", "created_at": "2025-01-01T10:00:00Z", "version": 2},
        ]

        result = _merge_stories(existing, new)

        # New version should take precedence
        assert len(result) == 1
        assert result[0]["version"] == 2

    def test_merge_sorts_by_created_at(self) -> None:
        """Test that merge sorts by created_at ascending."""
        existing = [{"gid": "s2", "created_at": "2025-01-01T12:00:00Z"}]
        new = [
            {"gid": "s1", "created_at": "2025-01-01T10:00:00Z"},
            {"gid": "s3", "created_at": "2025-01-01T14:00:00Z"},
        ]

        result = _merge_stories(existing, new)

        assert result[0]["gid"] == "s1"
        assert result[1]["gid"] == "s2"
        assert result[2]["gid"] == "s3"

    def test_merge_handles_missing_gid(self) -> None:
        """Test that merge handles stories without GID."""
        existing = [{"gid": "s1", "created_at": "2025-01-01T10:00:00Z"}]
        new = [{"created_at": "2025-01-01T11:00:00Z"}]  # No GID

        result = _merge_stories(existing, new)

        # Story without GID should be ignored
        assert len(result) == 1
        assert result[0]["gid"] == "s1"


class TestExtractStoriesList:
    """Tests for _extract_stories_list helper."""

    def test_extract_from_dict_with_stories(self) -> None:
        """Test extracting stories from proper structure."""
        data = {"stories": [{"gid": "s1"}]}
        result = _extract_stories_list(data)
        assert result == [{"gid": "s1"}]

    def test_extract_from_dict_without_stories(self) -> None:
        """Test extracting from dict without stories key."""
        data = {"other": "value"}
        result = _extract_stories_list(data)
        assert result == []

    def test_extract_from_dict_with_non_list_stories(self) -> None:
        """Test extracting when stories is not a list."""
        data = {"stories": "not a list"}
        result = _extract_stories_list(data)
        assert result == []


class TestFilterRelevantStories:
    """Tests for filter_relevant_stories function."""

    def test_filter_with_default_types(self) -> None:
        """Test filtering with default story types."""
        stories = [
            {"gid": "s1", "resource_subtype": "comment_added"},
            {"gid": "s2", "resource_subtype": "assignee_changed"},
            {"gid": "s3", "resource_subtype": "due_date_changed"},
        ]

        result = filter_relevant_stories(stories)

        assert len(result) == 2
        subtypes = [s["resource_subtype"] for s in result]
        assert "assignee_changed" in subtypes
        assert "due_date_changed" in subtypes
        assert "comment_added" not in subtypes

    def test_filter_with_custom_types(self) -> None:
        """Test filtering with custom story types."""
        stories = [
            {"gid": "s1", "resource_subtype": "comment_added"},
            {"gid": "s2", "resource_subtype": "assignee_changed"},
        ]

        result = filter_relevant_stories(stories, include_types=["comment_added"])

        assert len(result) == 1
        assert result[0]["resource_subtype"] == "comment_added"

    def test_filter_empty_list(self) -> None:
        """Test filtering empty list."""
        result = filter_relevant_stories([])
        assert result == []

    def test_filter_all_excluded(self) -> None:
        """Test when all stories are excluded."""
        stories = [
            {"gid": "s1", "resource_subtype": "comment_added"},
            {"gid": "s2", "resource_subtype": "system_message"},
        ]

        result = filter_relevant_stories(stories)
        assert result == []

    def test_default_story_types_includes_expected(self) -> None:
        """Test DEFAULT_STORY_TYPES has expected values."""
        assert "assignee_changed" in DEFAULT_STORY_TYPES
        assert "due_date_changed" in DEFAULT_STORY_TYPES
        assert "section_changed" in DEFAULT_STORY_TYPES
        assert "marked_complete" in DEFAULT_STORY_TYPES
        assert "marked_incomplete" in DEFAULT_STORY_TYPES
        assert "enum_custom_field_changed" in DEFAULT_STORY_TYPES

    def test_filter_handles_missing_subtype(self) -> None:
        """Test filtering stories without resource_subtype."""
        stories = [
            {"gid": "s1"},  # No resource_subtype
            {"gid": "s2", "resource_subtype": "assignee_changed"},
        ]

        result = filter_relevant_stories(stories)

        assert len(result) == 1
        assert result[0]["gid"] == "s2"


class TestGetLatestStoryTimestamp:
    """Tests for get_latest_story_timestamp function."""

    def test_get_latest_from_stories(self) -> None:
        """Test getting latest timestamp."""
        stories = [
            {"gid": "s1", "created_at": "2025-01-01T10:00:00Z"},
            {"gid": "s2", "created_at": "2025-01-01T12:00:00Z"},
            {"gid": "s3", "created_at": "2025-01-01T11:00:00Z"},
        ]

        result = get_latest_story_timestamp(stories)

        assert result == "2025-01-01T12:00:00Z"

    def test_get_latest_empty_list(self) -> None:
        """Test getting latest from empty list."""
        result = get_latest_story_timestamp([])
        assert result is None

    def test_get_latest_handles_missing_created_at(self) -> None:
        """Test handling stories without created_at."""
        stories = [
            {"gid": "s1"},  # No created_at
            {"gid": "s2", "created_at": "2025-01-01T10:00:00Z"},
        ]

        result = get_latest_story_timestamp(stories)

        assert result == "2025-01-01T10:00:00Z"

    def test_get_latest_all_missing_created_at(self) -> None:
        """Test when all stories lack created_at."""
        stories = [{"gid": "s1"}, {"gid": "s2"}]

        result = get_latest_story_timestamp(stories)

        assert result is None
