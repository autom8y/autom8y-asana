"""Tests for incremental story loading."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from autom8y_cache.testing import MockCacheProvider as _SDKMockCacheProvider

from autom8_asana.cache.integration.stories import (
    DEFAULT_STORY_TYPES,
    _extract_stories_list,
    _merge_stories,
    filter_relevant_stories,
    get_latest_story_timestamp,
    load_stories_incremental,
)
from autom8_asana.cache.models.entry import CacheEntry, EntryType


class MockCacheProvider(_SDKMockCacheProvider):
    """Mock cache provider for story tests (extends SDK MockCacheProvider).

    Overrides versioned ops to handle EntryType enum composite keys.
    """

    @property
    def _cache(self) -> dict[str, CacheEntry]:
        """Alias for SDK _versioned_store (backward compat for direct access)."""
        return self._versioned_store  # type: ignore[return-value]

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: object = None,
    ) -> CacheEntry | None:
        """Get entry from cache using EntryType enum."""
        self.calls.append(
            (
                "get_versioned",
                {"key": key, "entry_type": entry_type, "freshness": freshness},
            )
        )
        cache_key = f"{entry_type.value}:{key}"
        return self._versioned_store.get(cache_key)

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        """Store entry in cache using EntryType enum."""
        self.calls.append(("set_versioned", {"key": key, "entry": entry}))
        cache_key = f"{entry.entry_type.value}:{key}"
        self._versioned_store[cache_key] = entry


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
    async def test_merge_dedupes_by_gid(self, cache: MockCacheProvider, fetcher: AsyncMock) -> None:
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


class TestModifiedAtFreshnessProbe:
    """Tests for the modified_at freshness probe in load_stories_incremental.

    Per R2-revised: when current_modified_at indicates staleness, the
    max_cache_age_seconds short-circuit is bypassed so that an incremental
    fetch picks up mutations. The 'since' cursor is always preserved.
    """

    @pytest.fixture
    def cache(self) -> MockCacheProvider:
        return MockCacheProvider()

    @pytest.fixture
    def fetcher(self) -> AsyncMock:
        return AsyncMock()

    def _seed_cache(
        self,
        cache: MockCacheProvider,
        *,
        version: datetime,
        cached_at: datetime | None = None,
        last_fetched: str = "2025-06-01T12:00:00+00:00",
    ) -> None:
        """Seed a valid story cache entry for task123."""
        entry = CacheEntry(
            key="task123",
            data={"stories": [{"gid": "s1", "created_at": "2025-06-01T10:00:00Z"}]},
            entry_type=EntryType.STORIES,
            version=version,
            cached_at=cached_at or datetime.now(UTC),
            metadata={"last_fetched": last_fetched},
        )
        cache._cache["stories:task123"] = entry

    @pytest.mark.asyncio
    async def test_modified_at_probe_bypasses_max_age_when_stale(
        self, cache: MockCacheProvider, fetcher: AsyncMock
    ) -> None:
        """Stale entry triggers incremental fetch even when max_cache_age_seconds would skip."""
        # Cache entry versioned at T=10:00, very recently cached (age < max_age)
        self._seed_cache(
            cache,
            version=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
            cached_at=datetime.now(UTC),  # fresh cache
        )

        fetcher.return_value = [{"gid": "s2", "created_at": "2025-06-01T14:00:00Z"}]

        result, entry, was_incremental = await load_stories_incremental(
            task_gid="task123",
            cache=cache,
            fetcher=fetcher,
            # Task was modified at T=13:00, newer than cached version T=10:00 -> stale
            current_modified_at="2025-06-01T13:00:00+00:00",
            max_cache_age_seconds=3600,  # Would normally skip (cache is fresh)
        )

        # Should have done incremental fetch despite fresh cache age
        fetcher.assert_called_once_with("task123", "2025-06-01T12:00:00+00:00")
        assert was_incremental
        # Merged result includes both old cached story and new fetched story
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_modified_at_probe_no_change_when_none(
        self, cache: MockCacheProvider, fetcher: AsyncMock
    ) -> None:
        """current_modified_at=None preserves existing max_cache_age_seconds behavior."""
        self._seed_cache(
            cache,
            version=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
            cached_at=datetime.now(UTC),  # fresh cache
        )

        result, entry, was_incremental = await load_stories_incremental(
            task_gid="task123",
            cache=cache,
            fetcher=fetcher,
            current_modified_at=None,  # No version info -> skip probe
            max_cache_age_seconds=3600,
        )

        # Should short-circuit via max_cache_age_seconds (no API call)
        fetcher.assert_not_called()
        assert was_incremental  # Returns True because cache hit
        assert len(result) == 1
        assert result[0]["gid"] == "s1"

    @pytest.mark.asyncio
    async def test_modified_at_probe_allows_age_skip_when_current(
        self, cache: MockCacheProvider, fetcher: AsyncMock
    ) -> None:
        """When entry is current (not stale), max_cache_age_seconds skip works normally."""
        cached_version = datetime(2025, 6, 1, 10, 0, tzinfo=UTC)
        self._seed_cache(
            cache,
            version=cached_version,
            cached_at=datetime.now(UTC),  # fresh cache
        )

        result, entry, was_incremental = await load_stories_incremental(
            task_gid="task123",
            cache=cache,
            fetcher=fetcher,
            # Same version as cached -> not stale
            current_modified_at="2025-06-01T10:00:00+00:00",
            max_cache_age_seconds=3600,
        )

        # Should short-circuit (entry is current + cache is fresh)
        fetcher.assert_not_called()
        assert was_incremental
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_incremental_fetch_uses_since_cursor(
        self, cache: MockCacheProvider, fetcher: AsyncMock
    ) -> None:
        """After probe triggers, fetcher is called with since=last_fetched (not None)."""
        last_fetched_ts = "2025-06-01T12:00:00+00:00"
        self._seed_cache(
            cache,
            version=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
            last_fetched=last_fetched_ts,
            cached_at=datetime.now(UTC),
        )

        fetcher.return_value = []

        await load_stories_incremental(
            task_gid="task123",
            cache=cache,
            fetcher=fetcher,
            # Newer version -> stale -> bypasses age check
            current_modified_at="2025-06-01T15:00:00+00:00",
            max_cache_age_seconds=3600,
        )

        # Fetcher called with the since cursor, NOT None (preserves incremental)
        fetcher.assert_called_once_with("task123", last_fetched_ts)


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
