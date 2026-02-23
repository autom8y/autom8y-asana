"""Tests for dataframe cache integration.

Per TDD-0008 Session 4 Phase 4: Comprehensive tests for CachedRow,
DataFrameCacheIntegration, and builder cache integration.

Coverage targets:
- TestCachedRow: CachedRow dataclass methods
- TestDataFrameCacheIntegration: Async cache operations, staleness, errors
- TestBuilderWithCache: Builder integration, sync/async
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from autom8_asana._defaults.cache import InMemoryCacheProvider, NullCacheProvider
from autom8_asana.dataframes import (
    CachedRow,
    DataFrameCacheIntegration,
)
from autom8_asana.dataframes.resolver import MockCustomFieldResolver
from autom8_asana.models.task import Task

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def now() -> datetime:
    """Current UTC datetime."""
    return datetime.now(UTC)


@pytest.fixture
def one_hour_ago(now: datetime) -> datetime:
    """One hour ago."""
    return now - timedelta(hours=1)


@pytest.fixture
def in_memory_cache() -> InMemoryCacheProvider:
    """Fresh in-memory cache provider."""
    return InMemoryCacheProvider(default_ttl=300, max_size=1000)


@pytest.fixture
def null_cache() -> NullCacheProvider:
    """Null cache provider (no-op)."""
    return NullCacheProvider()


@pytest.fixture
def cache_integration(
    in_memory_cache: InMemoryCacheProvider,
) -> DataFrameCacheIntegration:
    """Cache integration with in-memory backend."""
    return DataFrameCacheIntegration(cache=in_memory_cache, default_ttl=300)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Mock log provider."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.error = MagicMock()
    logger.log_cache_event = MagicMock()
    return logger


@pytest.fixture
def minimal_task(now: datetime) -> Task:
    """Minimal task for testing."""
    return Task(
        gid="task123",
        name="Test Task",
        resource_subtype="default_task",
        completed=False,
        created_at=now.isoformat(),
        modified_at=now.isoformat(),
    )


@pytest.fixture
def task_with_project(now: datetime) -> Task:
    """Task with project membership."""
    return Task(
        gid="task456",
        name="Task With Project",
        resource_subtype="default_task",
        completed=False,
        created_at=now.isoformat(),
        modified_at=now.isoformat(),
        memberships=[
            {
                "project": {"gid": "proj123", "name": "Test Project"},
                "section": {"gid": "sec456", "name": "Active"},
            }
        ],
    )


@pytest.fixture
def unit_resolver() -> MockCustomFieldResolver:
    """Mock resolver for Unit tasks."""
    from decimal import Decimal

    return MockCustomFieldResolver(
        {
            "mrr": Decimal("5000.00"),
            "weekly_ad_spend": Decimal("1500.50"),
            "products": ["Product A"],
            "languages": ["English"],
            "discount": Decimal("10.5"),
            "vertical": "Healthcare",
            "specialty": "Dental",
        }
    )


@pytest.fixture
def mock_project(task_with_project: Task) -> MagicMock:
    """Mock project with tasks."""
    project = MagicMock()
    project.gid = "proj123"
    project.tasks = [task_with_project]
    return project


# =============================================================================
# TestCachedRow
# =============================================================================


class TestCachedRow:
    """Tests for CachedRow dataclass."""

    def test_cache_key_composition(self, now: datetime) -> None:
        """Test cache_key property combines task_gid and project_gid."""
        row = CachedRow(
            task_gid="task123",
            project_gid="proj456",
            data={"gid": "task123"},
            schema_version="1.0.0",
            cached_at=now,
            version=now,
        )

        assert row.cache_key == "task123:proj456"

    def test_is_schema_current_matches(self, now: datetime) -> None:
        """Test is_schema_current returns True when versions match."""
        row = CachedRow(
            task_gid="task123",
            project_gid="proj456",
            data={},
            schema_version="1.0.0",
            cached_at=now,
            version=now,
        )

        assert row.is_schema_current("1.0.0") is True

    def test_is_schema_current_mismatch(self, now: datetime) -> None:
        """Test is_schema_current returns False when versions differ."""
        row = CachedRow(
            task_gid="task123",
            project_gid="proj456",
            data={},
            schema_version="1.0.0",
            cached_at=now,
            version=now,
        )

        assert row.is_schema_current("2.0.0") is False

    def test_is_version_current_with_datetime(
        self,
        now: datetime,
        one_hour_ago: datetime,
    ) -> None:
        """Test is_version_current with datetime argument."""
        row = CachedRow(
            task_gid="task123",
            project_gid="proj456",
            data={},
            schema_version="1.0.0",
            cached_at=now,
            version=now,
        )

        # Cached now, checking against one hour ago - should be current
        assert row.is_version_current(one_hour_ago) is True

        # Cached one hour ago, checking against now - should be stale
        stale_row = CachedRow(
            task_gid="task123",
            project_gid="proj456",
            data={},
            schema_version="1.0.0",
            cached_at=one_hour_ago,
            version=one_hour_ago,
        )
        assert stale_row.is_version_current(now) is False

    def test_is_version_current_with_string(self, now: datetime) -> None:
        """Test is_version_current with ISO string argument."""
        row = CachedRow(
            task_gid="task123",
            project_gid="proj456",
            data={},
            schema_version="1.0.0",
            cached_at=now,
            version=now,
        )

        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        assert row.is_version_current(one_hour_ago) is True

    def test_frozen_dataclass(self, now: datetime) -> None:
        """Test CachedRow is immutable."""
        row = CachedRow(
            task_gid="task123",
            project_gid="proj456",
            data={"key": "value"},
            schema_version="1.0.0",
            cached_at=now,
            version=now,
        )

        with pytest.raises(FrozenInstanceError):
            row.task_gid = "changed"  # type: ignore[misc]


# =============================================================================
# TestDataFrameCacheIntegration
# =============================================================================


class TestDataFrameCacheIntegration:
    """Tests for DataFrameCacheIntegration class."""

    def test_init_with_cache_provider(
        self,
        in_memory_cache: InMemoryCacheProvider,
    ) -> None:
        """Test initialization with cache provider."""
        integration = DataFrameCacheIntegration(
            cache=in_memory_cache,
            default_ttl=600,
        )

        assert integration.cache is in_memory_cache

    def test_init_with_logger(
        self,
        in_memory_cache: InMemoryCacheProvider,
        mock_logger: MagicMock,
    ) -> None:
        """Test initialization with log provider."""
        integration = DataFrameCacheIntegration(
            cache=in_memory_cache,
            logger=mock_logger,
        )

        assert integration._logger is mock_logger

    # -------------------------------------------------------------------------
    # Async Cache Operations
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_cached_row_async_miss(
        self,
        cache_integration: DataFrameCacheIntegration,
    ) -> None:
        """Test cache miss returns None."""
        result = await cache_integration.get_cached_row_async(
            task_gid="nonexistent",
            project_gid="proj123",
            schema_version="1.0.0",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_row_async_then_get(
        self,
        cache_integration: DataFrameCacheIntegration,
        now: datetime,
    ) -> None:
        """Test caching a row and retrieving it."""
        data = {"gid": "task123", "name": "Test Task"}

        # Cache the row
        success = await cache_integration.cache_row_async(
            task_gid="task123",
            project_gid="proj456",
            data=data,
            schema_version="1.0.0",
            version=now,
        )
        assert success is True

        # Retrieve the row
        cached = await cache_integration.get_cached_row_async(
            task_gid="task123",
            project_gid="proj456",
            schema_version="1.0.0",
        )

        assert cached is not None
        assert cached.task_gid == "task123"
        assert cached.project_gid == "proj456"
        assert cached.data == data
        assert cached.schema_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_cached_row_async_schema_mismatch_invalidates(
        self,
        cache_integration: DataFrameCacheIntegration,
        now: datetime,
    ) -> None:
        """Test schema version mismatch invalidates cached entry."""
        data = {"gid": "task123", "name": "Test Task"}

        # Cache with schema version 1.0.0
        await cache_integration.cache_row_async(
            task_gid="task123",
            project_gid="proj456",
            data=data,
            schema_version="1.0.0",
            version=now,
        )

        # Request with different schema version
        cached = await cache_integration.get_cached_row_async(
            task_gid="task123",
            project_gid="proj456",
            schema_version="2.0.0",  # Different!
        )

        # Should return None and invalidate
        assert cached is None

        # Should also be gone for original schema version (invalidated)
        cached_again = await cache_integration.get_cached_row_async(
            task_gid="task123",
            project_gid="proj456",
            schema_version="1.0.0",
        )
        assert cached_again is None

    @pytest.mark.asyncio
    async def test_get_cached_row_async_stale_version_invalidates(
        self,
        cache_integration: DataFrameCacheIntegration,
        now: datetime,
        one_hour_ago: datetime,
    ) -> None:
        """Test stale data version invalidates cached entry."""
        data = {"gid": "task123", "name": "Test Task"}

        # Cache with old version
        await cache_integration.cache_row_async(
            task_gid="task123",
            project_gid="proj456",
            data=data,
            schema_version="1.0.0",
            version=one_hour_ago,
        )

        # Request with newer current_modified_at
        cached = await cache_integration.get_cached_row_async(
            task_gid="task123",
            project_gid="proj456",
            schema_version="1.0.0",
            current_modified_at=now,  # Newer than cached version
        )

        # Should return None (stale)
        assert cached is None

    @pytest.mark.asyncio
    async def test_get_cached_row_async_fresh_version(
        self,
        cache_integration: DataFrameCacheIntegration,
        now: datetime,
        one_hour_ago: datetime,
    ) -> None:
        """Test fresh data version returns cached entry."""
        data = {"gid": "task123", "name": "Test Task"}

        # Cache with current version
        await cache_integration.cache_row_async(
            task_gid="task123",
            project_gid="proj456",
            data=data,
            schema_version="1.0.0",
            version=now,
        )

        # Request with older current_modified_at
        cached = await cache_integration.get_cached_row_async(
            task_gid="task123",
            project_gid="proj456",
            schema_version="1.0.0",
            current_modified_at=one_hour_ago,  # Older than cached
        )

        # Should return cached entry (still fresh)
        assert cached is not None
        assert cached.data == data

    @pytest.mark.asyncio
    async def test_get_cached_batch_async(
        self,
        cache_integration: DataFrameCacheIntegration,
        now: datetime,
    ) -> None:
        """Test batch retrieval."""
        # Cache two rows
        await cache_integration.cache_row_async(
            task_gid="task1",
            project_gid="proj1",
            data={"gid": "task1"},
            schema_version="1.0.0",
            version=now,
        )
        await cache_integration.cache_row_async(
            task_gid="task2",
            project_gid="proj1",
            data={"gid": "task2"},
            schema_version="1.0.0",
            version=now,
        )

        # Batch get
        results = await cache_integration.get_cached_batch_async(
            task_project_pairs=[
                ("task1", "proj1"),
                ("task2", "proj1"),
                ("task3", "proj1"),
            ],
            schema_version="1.0.0",
        )

        assert len(results) == 3
        assert results["task1:proj1"] is not None
        assert results["task2:proj1"] is not None
        assert results["task3:proj1"] is None  # Not cached

    @pytest.mark.asyncio
    async def test_cache_batch_async(
        self,
        cache_integration: DataFrameCacheIntegration,
        now: datetime,
    ) -> None:
        """Test batch caching."""
        rows = [
            ("task1", "proj1", {"gid": "task1"}, now.isoformat()),
            ("task2", "proj1", {"gid": "task2"}, now.isoformat()),
        ]

        count = await cache_integration.cache_batch_async(
            rows=rows,
            schema_version="1.0.0",
        )

        assert count == 2

        # Verify both are cached
        cached1 = await cache_integration.get_cached_row_async(
            task_gid="task1",
            project_gid="proj1",
            schema_version="1.0.0",
        )
        cached2 = await cache_integration.get_cached_row_async(
            task_gid="task2",
            project_gid="proj1",
            schema_version="1.0.0",
        )

        assert cached1 is not None
        assert cached2 is not None

    @pytest.mark.asyncio
    async def test_invalidate_async(
        self,
        cache_integration: DataFrameCacheIntegration,
        now: datetime,
    ) -> None:
        """Test explicit invalidation."""
        # Cache a row
        await cache_integration.cache_row_async(
            task_gid="task123",
            project_gid="proj456",
            data={"gid": "task123"},
            schema_version="1.0.0",
            version=now,
        )

        # Verify it's cached
        cached = await cache_integration.get_cached_row_async(
            task_gid="task123",
            project_gid="proj456",
            schema_version="1.0.0",
        )
        assert cached is not None

        # Invalidate
        success = await cache_integration.invalidate_async(
            task_gid="task123",
            project_gid="proj456",
        )
        assert success is True

        # Verify it's gone
        cached_after = await cache_integration.get_cached_row_async(
            task_gid="task123",
            project_gid="proj456",
            schema_version="1.0.0",
        )
        assert cached_after is None

    # -------------------------------------------------------------------------
    # Sync Wrappers
    # -------------------------------------------------------------------------

    def test_cache_row_sync_wrapper(
        self,
        cache_integration: DataFrameCacheIntegration,
        now: datetime,
    ) -> None:
        """Test sync cache_row wrapper."""
        success = cache_integration.cache_row(
            task_gid="task123",
            project_gid="proj456",
            data={"gid": "task123"},
            schema_version="1.0.0",
            version=now,
        )

        assert success is True

    def test_get_cached_row_sync_wrapper(
        self,
        cache_integration: DataFrameCacheIntegration,
        now: datetime,
    ) -> None:
        """Test sync get_cached_row wrapper."""
        # Cache first
        cache_integration.cache_row(
            task_gid="task123",
            project_gid="proj456",
            data={"gid": "task123"},
            schema_version="1.0.0",
            version=now,
        )

        # Get sync
        cached = cache_integration.get_cached_row(
            task_gid="task123",
            project_gid="proj456",
            schema_version="1.0.0",
        )

        assert cached is not None
        assert cached.task_gid == "task123"

    def test_invalidate_sync_wrapper(
        self,
        cache_integration: DataFrameCacheIntegration,
        now: datetime,
    ) -> None:
        """Test sync invalidate wrapper."""
        # Cache first
        cache_integration.cache_row(
            task_gid="task123",
            project_gid="proj456",
            data={"gid": "task123"},
            schema_version="1.0.0",
            version=now,
        )

        # Invalidate sync
        success = cache_integration.invalidate(
            task_gid="task123",
            project_gid="proj456",
        )

        assert success is True

        # Verify gone
        cached = cache_integration.get_cached_row(
            task_gid="task123",
            project_gid="proj456",
            schema_version="1.0.0",
        )
        assert cached is None

    # -------------------------------------------------------------------------
    # Error Handling (FR-CACHE-008)
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_cached_row_graceful_degradation(
        self,
        mock_logger: MagicMock,
    ) -> None:
        """Test graceful degradation on cache errors."""
        # Create a failing cache
        failing_cache = MagicMock()
        failing_cache.get_versioned = MagicMock(
            side_effect=ConnectionError("Redis down")
        )

        integration = DataFrameCacheIntegration(
            cache=failing_cache,
            logger=mock_logger,
        )

        # Should not raise, should return None
        result = await integration.get_cached_row_async(
            task_gid="task123",
            project_gid="proj456",
            schema_version="1.0.0",
        )

        assert result is None
        # Should have logged error
        mock_logger.log_cache_event.assert_called()

    @pytest.mark.asyncio
    async def test_cache_row_graceful_degradation(
        self,
        mock_logger: MagicMock,
        now: datetime,
    ) -> None:
        """Test graceful degradation on cache write errors."""
        failing_cache = MagicMock()
        failing_cache.set_versioned = MagicMock(
            side_effect=ConnectionError("Redis down")
        )

        integration = DataFrameCacheIntegration(
            cache=failing_cache,
            logger=mock_logger,
        )

        # Should not raise, should return False
        success = await integration.cache_row_async(
            task_gid="task123",
            project_gid="proj456",
            data={"gid": "task123"},
            schema_version="1.0.0",
            version=now,
        )

        assert success is False

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_logging_with_cache_logging_provider(
        self,
        in_memory_cache: InMemoryCacheProvider,
        mock_logger: MagicMock,
        now: datetime,
    ) -> None:
        """Test logging uses log_cache_event when available."""
        integration = DataFrameCacheIntegration(
            cache=in_memory_cache,
            logger=mock_logger,
        )

        # Cache miss
        await integration.get_cached_row_async(
            task_gid="task123",
            project_gid="proj456",
            schema_version="1.0.0",
        )

        # Should have called log_cache_event
        mock_logger.log_cache_event.assert_called_with(
            event_type="miss",
            key="task123:proj456",
            entry_type="dataframe",
            metadata=None,
        )


class TestCacheIntegrationErrorHandling:
    """Tests for error handling paths."""

    @pytest.mark.asyncio
    async def test_cache_batch_graceful_degradation(
        self,
        mock_logger: MagicMock,
        now: datetime,
    ) -> None:
        """Test cache_batch handles exceptions gracefully."""
        failing_cache = MagicMock()
        failing_cache.set_batch = MagicMock(side_effect=ConnectionError("Redis down"))

        integration = DataFrameCacheIntegration(
            cache=failing_cache,
            logger=mock_logger,
        )

        rows = [("task1", "proj1", {"gid": "task1"}, now)]

        # Should not raise, should return 0
        count = await integration.cache_batch_async(
            rows=rows,
            schema_version="1.0.0",
        )

        assert count == 0
        mock_logger.log_cache_event.assert_called()

    @pytest.mark.asyncio
    async def test_warm_struc_graceful_degradation(
        self,
        mock_logger: MagicMock,
    ) -> None:
        """Test warm_struc handles exceptions gracefully."""
        failing_cache = MagicMock()
        failing_cache.warm = MagicMock(side_effect=ConnectionError("Redis down"))

        integration = DataFrameCacheIntegration(
            cache=failing_cache,
            logger=mock_logger,
        )

        # Should not raise, should return 0
        count = await integration.warm_struc_async(
            [
                ("task1", "proj1"),
            ]
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_invalidate_graceful_degradation(
        self,
        mock_logger: MagicMock,
    ) -> None:
        """Test invalidate handles exceptions gracefully."""
        failing_cache = MagicMock()
        failing_cache.invalidate = MagicMock(side_effect=ConnectionError("Redis down"))

        integration = DataFrameCacheIntegration(
            cache=failing_cache,
            logger=mock_logger,
        )

        # Should not raise, should return False
        success = await integration.invalidate_async(
            task_gid="task123",
            project_gid="proj456",
        )

        assert success is False


class TestCacheIntegrationLogging:
    """Tests for logging edge cases."""

    @pytest.mark.asyncio
    async def test_logging_without_log_cache_event_method(
        self,
        in_memory_cache: InMemoryCacheProvider,
        now: datetime,
    ) -> None:
        """Test logging falls back to standard logging when log_cache_event unavailable."""
        # Create a logger without log_cache_event method
        basic_logger = MagicMock()
        basic_logger.debug = MagicMock()
        basic_logger.error = MagicMock()
        # Ensure no log_cache_event method
        del basic_logger.log_cache_event

        integration = DataFrameCacheIntegration(
            cache=in_memory_cache,
            logger=basic_logger,
        )

        # Cache operation should use fallback logging
        await integration.cache_row_async(
            task_gid="task123",
            project_gid="proj456",
            data={"gid": "task123"},
            schema_version="1.0.0",
            version=now,
        )

        # Should have called debug for write event
        basic_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_logging_error_event_uses_error_level(
        self,
        mock_logger: MagicMock,
    ) -> None:
        """Test error events use error log level in fallback logging."""
        # Create a logger without log_cache_event method
        basic_logger = MagicMock()
        basic_logger.debug = MagicMock()
        basic_logger.error = MagicMock()
        del basic_logger.log_cache_event

        failing_cache = MagicMock()
        failing_cache.get_versioned = MagicMock(side_effect=ConnectionError("Error"))

        integration = DataFrameCacheIntegration(
            cache=failing_cache,
            logger=basic_logger,
        )

        # Trigger error logging
        await integration.get_cached_row_async(
            task_gid="task123",
            project_gid="proj456",
            schema_version="1.0.0",
        )

        # Should have called error for error event
        basic_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_staleness_check_with_naive_datetimes(
        self,
        in_memory_cache: InMemoryCacheProvider,
    ) -> None:
        """Test _check_staleness handles naive datetimes."""
        integration = DataFrameCacheIntegration(cache=in_memory_cache)

        # Test with naive datetimes
        cached_version = datetime(2025, 1, 15, 10, 30, 0)  # No timezone
        current_version = datetime(2025, 1, 15, 10, 0, 0)  # No timezone, earlier

        # Should work - cached is newer
        result = integration._check_staleness(cached_version, current_version)
        assert result is True

        # Test stale case
        stale_result = integration._check_staleness(current_version, cached_version)
        assert stale_result is False
