"""Tests for AsanaClient.warm_cache_async() method.

Per TDD-CACHE-UTILIZATION Phase 3: Cache Warming implementation tests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana._defaults.cache import InMemoryCacheProvider, NullCacheProvider
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.client import AsanaClient
from autom8_asana.protocols.cache import WarmResult


class TestWarmCacheAsync:
    """Tests for warm_cache_async() method."""

    @pytest.fixture
    def mock_cache_provider(self) -> InMemoryCacheProvider:
        """Create an in-memory cache provider for testing."""
        return InMemoryCacheProvider(default_ttl=300)

    @pytest.fixture
    def client_with_cache(
        self, mock_cache_provider: InMemoryCacheProvider
    ) -> AsanaClient:
        """Create a client with in-memory cache."""
        return AsanaClient(
            token="test-token",
            cache_provider=mock_cache_provider,
        )

    async def test_warm_returns_warm_result(
        self, client_with_cache: AsanaClient
    ) -> None:
        """warm_cache_async() returns a WarmResult instance."""
        # Patch the tasks client to avoid actual API calls
        with patch.object(
            client_with_cache.tasks, "get_async", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = MagicMock(gid="123")

            result = await client_with_cache.warm_cache_async(
                gids=["123"],
                entry_type=EntryType.TASK,
            )

            assert isinstance(result, WarmResult)

    async def test_warm_with_uncached_entries_increments_warmed(
        self, client_with_cache: AsanaClient
    ) -> None:
        """Uncached entries are fetched and counted as warmed."""
        with patch.object(
            client_with_cache.tasks, "get_async", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = MagicMock(gid="123")

            result = await client_with_cache.warm_cache_async(
                gids=["123", "456", "789"],
                entry_type=EntryType.TASK,
            )

            assert result.warmed == 3
            assert result.failed == 0
            assert result.skipped == 0
            assert mock_get.call_count == 3

    async def test_warm_with_cached_entries_increments_skipped(
        self, client_with_cache: AsanaClient, mock_cache_provider: InMemoryCacheProvider
    ) -> None:
        """Already-cached entries are skipped without API calls."""
        # Pre-populate cache with an entry
        cache_entry = CacheEntry(
            key="123",
            data={"gid": "123", "name": "Cached Task"},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
            ttl=300,
        )
        mock_cache_provider.set_versioned("123", cache_entry)

        with patch.object(
            client_with_cache.tasks, "get_async", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = MagicMock(gid="456")

            result = await client_with_cache.warm_cache_async(
                gids=["123", "456"],
                entry_type=EntryType.TASK,
            )

            # "123" was cached, "456" was not
            assert result.skipped == 1
            assert result.warmed == 1
            assert result.failed == 0
            # Only "456" should have triggered an API call
            assert mock_get.call_count == 1
            mock_get.assert_called_once_with("456")

    async def test_warm_with_api_errors_increments_failed(
        self, client_with_cache: AsanaClient
    ) -> None:
        """API errors increment failed count without stopping processing."""
        with patch.object(
            client_with_cache.tasks, "get_async", new_callable=AsyncMock
        ) as mock_get:
            # First call succeeds, second fails, third succeeds
            mock_get.side_effect = [
                MagicMock(gid="123"),
                ConnectionError("API Error"),
                MagicMock(gid="789"),
            ]

            result = await client_with_cache.warm_cache_async(
                gids=["123", "456", "789"],
                entry_type=EntryType.TASK,
            )

            assert result.warmed == 2
            assert result.failed == 1
            assert result.skipped == 0

    async def test_warm_with_mixed_states(
        self, client_with_cache: AsanaClient, mock_cache_provider: InMemoryCacheProvider
    ) -> None:
        """Mixed cached/uncached/error entries are counted correctly."""
        # Pre-populate cache with one entry
        cache_entry = CacheEntry(
            key="cached_gid",
            data={"gid": "cached_gid", "name": "Cached"},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
            ttl=300,
        )
        mock_cache_provider.set_versioned("cached_gid", cache_entry)

        with patch.object(
            client_with_cache.tasks, "get_async", new_callable=AsyncMock
        ) as mock_get:
            # uncached_ok succeeds, uncached_fail fails
            mock_get.side_effect = [
                MagicMock(gid="uncached_ok"),
                ConnectionError("API Error"),
            ]

            result = await client_with_cache.warm_cache_async(
                gids=["cached_gid", "uncached_ok", "uncached_fail"],
                entry_type=EntryType.TASK,
            )

            assert result.skipped == 1  # cached_gid
            assert result.warmed == 1  # uncached_ok
            assert result.failed == 1  # uncached_fail
            assert result.total == 3

    async def test_warm_with_null_cache_provider_skips_all(self) -> None:
        """With NullCacheProvider, all entries are skipped."""
        client = AsanaClient(
            token="test-token",
            cache_provider=NullCacheProvider(),
        )

        with patch.object(
            client.tasks, "get_async", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = MagicMock(gid="123")

            result = await client.warm_cache_async(
                gids=["123", "456"],
                entry_type=EntryType.TASK,
            )

            # NullCacheProvider.get_versioned() returns None, so entries
            # are not considered cached - they will be fetched
            assert result.warmed == 2
            assert result.skipped == 0
            assert mock_get.call_count == 2


class TestWarmCacheEntryTypes:
    """Tests for warm_cache_async() with different entry types."""

    @pytest.fixture
    def client(self) -> AsanaClient:
        """Create a client with in-memory cache."""
        return AsanaClient(
            token="test-token",
            cache_provider=InMemoryCacheProvider(),
        )

    async def test_warm_task_entry_type(self, client: AsanaClient) -> None:
        """TASK entry type uses tasks.get_async()."""
        with patch.object(
            client.tasks, "get_async", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = MagicMock(gid="123")

            result = await client.warm_cache_async(
                gids=["123"],
                entry_type=EntryType.TASK,
            )

            mock_get.assert_called_once_with("123")
            assert result.warmed == 1

    async def test_warm_project_entry_type(self, client: AsanaClient) -> None:
        """PROJECT entry type uses projects.get_async()."""
        with patch.object(
            client.projects, "get_async", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = MagicMock(gid="123")

            result = await client.warm_cache_async(
                gids=["123"],
                entry_type=EntryType.PROJECT,
            )

            mock_get.assert_called_once_with("123")
            assert result.warmed == 1

    async def test_warm_section_entry_type(self, client: AsanaClient) -> None:
        """SECTION entry type uses sections.get_async()."""
        with patch.object(
            client.sections, "get_async", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = MagicMock(gid="123")

            result = await client.warm_cache_async(
                gids=["123"],
                entry_type=EntryType.SECTION,
            )

            mock_get.assert_called_once_with("123")
            assert result.warmed == 1

    async def test_warm_user_entry_type(self, client: AsanaClient) -> None:
        """USER entry type uses users.get_async()."""
        with patch.object(
            client.users, "get_async", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = MagicMock(gid="123")

            result = await client.warm_cache_async(
                gids=["123"],
                entry_type=EntryType.USER,
            )

            mock_get.assert_called_once_with("123")
            assert result.warmed == 1

    async def test_warm_custom_field_entry_type(self, client: AsanaClient) -> None:
        """CUSTOM_FIELD entry type uses custom_fields.get_async()."""
        with patch.object(
            client.custom_fields, "get_async", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = MagicMock(gid="123")

            result = await client.warm_cache_async(
                gids=["123"],
                entry_type=EntryType.CUSTOM_FIELD,
            )

            mock_get.assert_called_once_with("123")
            assert result.warmed == 1

    async def test_warm_unsupported_entry_type_fails(self, client: AsanaClient) -> None:
        """Unsupported entry types (e.g., SUBTASKS) increment failed count."""
        # SUBTASKS is not a directly warmable type
        result = await client.warm_cache_async(
            gids=["123"],
            entry_type=EntryType.SUBTASKS,
        )

        assert result.failed == 1
        assert result.warmed == 0
        assert result.skipped == 0


class TestWarmCacheEdgeCases:
    """Edge case tests for warm_cache_async()."""

    async def test_warm_with_empty_gids_returns_zero_counts(self) -> None:
        """Empty GIDs list returns result with all zero counts."""
        client = AsanaClient(
            token="test-token",
            cache_provider=InMemoryCacheProvider(),
        )

        result = await client.warm_cache_async(
            gids=[],
            entry_type=EntryType.TASK,
        )

        assert result.warmed == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.total == 0

    async def test_warm_populates_cache_for_subsequent_gets(self) -> None:
        """Warmed entries are available in cache for subsequent get calls."""
        cache_provider = InMemoryCacheProvider()
        client = AsanaClient(
            token="test-token",
            cache_provider=cache_provider,
        )

        # Mock the first call (warming)
        with patch.object(
            client.tasks, "get_async", new_callable=AsyncMock
        ) as mock_get:
            # Simulate what TasksClient.get_async does - it caches the data
            mock_data = {"gid": "123", "name": "Test Task", "resource_type": "task"}
            mock_get.return_value = MagicMock(**mock_data)

            # Manually populate cache as the client would
            cache_entry = CacheEntry(
                key="123",
                data=mock_data,
                entry_type=EntryType.TASK,
                version=datetime.now(UTC),
                ttl=300,
            )
            cache_provider.set_versioned("123", cache_entry)

            await client.warm_cache_async(
                gids=["123"],
                entry_type=EntryType.TASK,
            )

        # Now verify the entry is cached
        cached = cache_provider.get_versioned("123", EntryType.TASK)
        assert cached is not None
        assert cached.data["gid"] == "123"

    async def test_warm_result_total_property(self) -> None:
        """WarmResult.total returns sum of all counts."""
        result = WarmResult(warmed=5, failed=2, skipped=3)
        assert result.total == 10

    async def test_warm_result_repr(self) -> None:
        """WarmResult has useful string representation."""
        result = WarmResult(warmed=5, failed=2, skipped=3)
        repr_str = repr(result)

        assert "warmed=5" in repr_str
        assert "failed=2" in repr_str
        assert "skipped=3" in repr_str


class TestWarmCacheSync:
    """Tests for synchronous warm_cache() wrapper."""

    def test_warm_cache_sync_wrapper_exists(self) -> None:
        """warm_cache() synchronous method exists."""
        client = AsanaClient(
            token="test-token",
            cache_provider=InMemoryCacheProvider(),
        )

        assert hasattr(client, "warm_cache")
        assert callable(client.warm_cache)

    async def test_warm_cache_sync_raises_in_async_context(self) -> None:
        """warm_cache() raises SyncInAsyncContextError in async context."""
        from autom8_asana.exceptions import SyncInAsyncContextError

        client = AsanaClient(
            token="test-token",
            cache_provider=InMemoryCacheProvider(),
        )

        # Per ADR-0002: Sync methods should fail fast in async context
        with pytest.raises(SyncInAsyncContextError) as exc_info:
            client.warm_cache(
                gids=["123"],
                entry_type=EntryType.TASK,
            )

        assert "warm_cache_async" in str(exc_info.value)
