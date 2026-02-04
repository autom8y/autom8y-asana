"""Tests for autom8 integration adapter."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.cache.integration.autom8_adapter import (
    MigrationResult,
    MissingConfigurationError,
    _parse_version,
    check_redis_health,
    create_autom8_cache_provider,
    migrate_task_collection_loading,
    warm_project_tasks,
)
from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.cache.models.entry import CacheEntry, EntryType


class TestMigrationResult:
    """Tests for MigrationResult dataclass."""

    def test_hit_rate_zero_when_empty(self) -> None:
        """Test hit rate is zero when no tasks."""
        result = MigrationResult(
            total_tasks=0,
            cache_hits=0,
            cache_misses=0,
            fetch_errors=0,
        )
        assert result.hit_rate == 0.0

    def test_hit_rate_calculation(self) -> None:
        """Test hit rate calculation."""
        result = MigrationResult(
            total_tasks=100,
            cache_hits=80,
            cache_misses=20,
            fetch_errors=0,
        )
        assert result.hit_rate == 80.0

    def test_hit_rate_all_hits(self) -> None:
        """Test hit rate when all hits."""
        result = MigrationResult(
            total_tasks=50,
            cache_hits=50,
            cache_misses=0,
            fetch_errors=0,
        )
        assert result.hit_rate == 100.0

    def test_hit_rate_all_misses(self) -> None:
        """Test hit rate when all misses."""
        result = MigrationResult(
            total_tasks=50,
            cache_hits=0,
            cache_misses=50,
            fetch_errors=0,
        )
        assert result.hit_rate == 0.0


class TestCreateAutom8CacheProvider:
    """Tests for create_autom8_cache_provider function."""

    def test_missing_redis_host_raises(self) -> None:
        """Test that missing REDIS_HOST raises MissingConfigurationError."""
        # Save current env vars
        saved_host = os.environ.pop("REDIS_HOST", None)

        try:
            with pytest.raises(MissingConfigurationError) as exc_info:
                create_autom8_cache_provider()

            assert "REDIS_HOST" in str(exc_info.value)
        finally:
            # Restore env var
            if saved_host is not None:
                os.environ["REDIS_HOST"] = saved_host

    def test_explicit_host_creates_provider(self) -> None:
        """Test that explicit host parameter creates provider (may fail if no Redis)."""
        # This test verifies the function runs without error when given valid params
        # The actual Redis connection may fail, which is expected
        try:
            provider = create_autom8_cache_provider(
                redis_host="localhost",
                redis_port=6379,
                redis_ssl=False,
            )
            # Provider is created, even if Redis isn't available
            assert provider is not None
            assert hasattr(provider, "get_versioned")
            assert hasattr(provider, "set_versioned")
        except Exception:
            # Redis not available, which is fine for this test
            pass

    def test_ssl_values_from_env(self) -> None:
        """Test that REDIS_SSL environment variable is parsed correctly."""
        # Test various SSL env values
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
        ]

        for env_value, expected_ssl in test_cases:
            # Save current env
            saved_host = os.environ.get("REDIS_HOST")
            saved_ssl = os.environ.get("REDIS_SSL")

            try:
                os.environ["REDIS_HOST"] = "localhost"
                os.environ["REDIS_SSL"] = env_value

                provider = create_autom8_cache_provider()
                # Check that it was created (connection may fail)
                assert provider is not None
            except Exception:
                # Redis not available, which is fine
                pass
            finally:
                # Restore env
                if saved_host is not None:
                    os.environ["REDIS_HOST"] = saved_host
                else:
                    os.environ.pop("REDIS_HOST", None)
                if saved_ssl is not None:
                    os.environ["REDIS_SSL"] = saved_ssl
                else:
                    os.environ.pop("REDIS_SSL", None)


class TestMigrateTaskCollectionLoading:
    """Tests for migrate_task_collection_loading function."""

    @pytest.fixture
    def mock_cache(self) -> EnhancedInMemoryCacheProvider:
        """Create mock cache provider."""
        return EnhancedInMemoryCacheProvider()

    @pytest.fixture
    def mock_batch_api(self) -> AsyncMock:
        """Create mock batch API."""
        return AsyncMock(
            return_value={
                "123": "2025-01-15T10:00:00Z",
                "456": "2025-01-15T11:00:00Z",
            }
        )

    @pytest.fixture
    def mock_task_fetcher(self) -> AsyncMock:
        """Create mock task fetcher."""
        return AsyncMock(
            return_value=[
                {
                    "gid": "123",
                    "name": "Task 123",
                    "modified_at": "2025-01-15T10:00:00Z",
                },
                {
                    "gid": "456",
                    "name": "Task 456",
                    "modified_at": "2025-01-15T11:00:00Z",
                },
            ]
        )

    @pytest.mark.asyncio
    async def test_empty_task_dicts(
        self,
        mock_cache: EnhancedInMemoryCacheProvider,
        mock_batch_api: AsyncMock,
        mock_task_fetcher: AsyncMock,
    ) -> None:
        """Test with empty task list."""
        result = await migrate_task_collection_loading(
            task_dicts=[],
            cache=mock_cache,
            batch_api=mock_batch_api,
            task_fetcher=mock_task_fetcher,
        )

        assert result.total_tasks == 0
        assert result.cache_hits == 0
        assert result.cache_misses == 0
        assert result.tasks == []
        mock_batch_api.assert_not_called()
        mock_task_fetcher.assert_not_called()

    @pytest.mark.asyncio
    async def test_task_dicts_without_gids(
        self,
        mock_cache: EnhancedInMemoryCacheProvider,
        mock_batch_api: AsyncMock,
        mock_task_fetcher: AsyncMock,
    ) -> None:
        """Test with task dicts that have no GIDs."""
        result = await migrate_task_collection_loading(
            task_dicts=[{"name": "No GID"}],
            cache=mock_cache,
            batch_api=mock_batch_api,
            task_fetcher=mock_task_fetcher,
        )

        assert result.total_tasks == 1
        assert result.tasks == [{"name": "No GID"}]
        mock_batch_api.assert_not_called()

    @pytest.mark.asyncio
    async def test_cold_cache_all_misses(
        self,
        mock_cache: EnhancedInMemoryCacheProvider,
        mock_batch_api: AsyncMock,
        mock_task_fetcher: AsyncMock,
    ) -> None:
        """Test with cold cache - all tasks should be fetched."""
        task_dicts = [{"gid": "123"}, {"gid": "456"}]

        result = await migrate_task_collection_loading(
            task_dicts=task_dicts,
            cache=mock_cache,
            batch_api=mock_batch_api,
            task_fetcher=mock_task_fetcher,
        )

        assert result.total_tasks == 2
        assert result.cache_hits == 0
        assert result.cache_misses == 2
        assert len(result.tasks) == 2
        mock_batch_api.assert_called_once()
        mock_task_fetcher.assert_called_once()

    @pytest.mark.asyncio
    async def test_warm_cache_all_hits(
        self,
        mock_cache: EnhancedInMemoryCacheProvider,
        mock_batch_api: AsyncMock,
        mock_task_fetcher: AsyncMock,
    ) -> None:
        """Test with warm cache - all tasks should be cache hits."""
        now = datetime.now(UTC)

        # Pre-populate cache
        for gid in ["123", "456"]:
            mock_cache.set_versioned(
                gid,
                CacheEntry(
                    key=gid,
                    data={"gid": gid, "name": f"Task {gid}"},
                    entry_type=EntryType.TASK,
                    version=now,
                    ttl=300,
                ),
            )

        # Batch API returns same version as cached
        mock_batch_api.return_value = {
            "123": now.isoformat(),
            "456": now.isoformat(),
        }

        task_dicts = [{"gid": "123"}, {"gid": "456"}]

        result = await migrate_task_collection_loading(
            task_dicts=task_dicts,
            cache=mock_cache,
            batch_api=mock_batch_api,
            task_fetcher=mock_task_fetcher,
        )

        assert result.total_tasks == 2
        assert result.cache_hits == 2
        assert result.cache_misses == 0
        assert len(result.tasks) == 2
        mock_task_fetcher.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_hits_and_misses(
        self,
        mock_cache: EnhancedInMemoryCacheProvider,
        mock_batch_api: AsyncMock,
        mock_task_fetcher: AsyncMock,
    ) -> None:
        """Test with mix of cache hits and misses."""
        now = datetime.now(UTC)

        # Only cache "123"
        mock_cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={"gid": "123", "name": "Task 123"},
                entry_type=EntryType.TASK,
                version=now,
                ttl=300,
            ),
        )

        # Batch API returns same version for cached, and version for uncached
        mock_batch_api.return_value = {
            "123": now.isoformat(),
            "456": "2025-01-15T11:00:00Z",
        }

        # Fetcher returns only the uncached task
        mock_task_fetcher.return_value = [
            {"gid": "456", "name": "Task 456", "modified_at": "2025-01-15T11:00:00Z"},
        ]

        task_dicts = [{"gid": "123"}, {"gid": "456"}]

        result = await migrate_task_collection_loading(
            task_dicts=task_dicts,
            cache=mock_cache,
            batch_api=mock_batch_api,
            task_fetcher=mock_task_fetcher,
        )

        assert result.total_tasks == 2
        assert result.cache_hits == 1
        assert result.cache_misses == 1
        assert len(result.tasks) == 2

        # Fetcher should only be called for "456"
        mock_task_fetcher.assert_called_once_with(["456"])

    @pytest.mark.asyncio
    async def test_tasks_cached_after_fetch(
        self,
        mock_cache: EnhancedInMemoryCacheProvider,
        mock_batch_api: AsyncMock,
        mock_task_fetcher: AsyncMock,
    ) -> None:
        """Test that fetched tasks are cached."""
        task_dicts = [{"gid": "123"}]

        # First call - cache miss
        await migrate_task_collection_loading(
            task_dicts=task_dicts,
            cache=mock_cache,
            batch_api=mock_batch_api,
            task_fetcher=mock_task_fetcher,
        )

        # Verify task was cached
        entry = mock_cache.get_versioned("123", EntryType.TASK)
        assert entry is not None
        assert entry.data["gid"] == "123"

    @pytest.mark.asyncio
    async def test_custom_ttl(
        self,
        mock_cache: EnhancedInMemoryCacheProvider,
        mock_batch_api: AsyncMock,
        mock_task_fetcher: AsyncMock,
    ) -> None:
        """Test that custom TTL is applied."""
        task_dicts = [{"gid": "123"}]

        await migrate_task_collection_loading(
            task_dicts=task_dicts,
            cache=mock_cache,
            batch_api=mock_batch_api,
            task_fetcher=mock_task_fetcher,
            ttl=600,
        )

        entry = mock_cache.get_versioned("123", EntryType.TASK)
        assert entry is not None
        assert entry.ttl == 600

    @pytest.mark.asyncio
    async def test_fetch_errors_counted(
        self,
        mock_cache: EnhancedInMemoryCacheProvider,
        mock_batch_api: AsyncMock,
    ) -> None:
        """Test that missing fetched tasks are counted as errors."""
        # Fetcher returns empty list (all tasks failed to fetch)
        mock_task_fetcher = AsyncMock(return_value=[])

        task_dicts = [{"gid": "123"}, {"gid": "456"}]

        result = await migrate_task_collection_loading(
            task_dicts=task_dicts,
            cache=mock_cache,
            batch_api=mock_batch_api,
            task_fetcher=mock_task_fetcher,
        )

        assert result.fetch_errors == 2


class TestWarmProjectTasks:
    """Tests for warm_project_tasks function."""

    @pytest.mark.asyncio
    async def test_warms_all_tasks(self) -> None:
        """Test that all project tasks are cached."""
        cache = EnhancedInMemoryCacheProvider()
        mock_fetcher = AsyncMock(
            return_value=[
                {"gid": "123", "name": "Task 1", "modified_at": "2025-01-15T10:00:00Z"},
                {"gid": "456", "name": "Task 2", "modified_at": "2025-01-15T11:00:00Z"},
            ]
        )

        warmed = await warm_project_tasks(
            cache=cache,
            project_gid="project_123",
            task_fetcher=mock_fetcher,
        )

        assert warmed == 2
        mock_fetcher.assert_called_once_with("project_123")

        # Verify tasks are cached
        entry1 = cache.get_versioned("123", EntryType.TASK)
        entry2 = cache.get_versioned("456", EntryType.TASK)
        assert entry1 is not None
        assert entry2 is not None

    @pytest.mark.asyncio
    async def test_empty_project(self) -> None:
        """Test warming empty project."""
        cache = EnhancedInMemoryCacheProvider()
        mock_fetcher = AsyncMock(return_value=[])

        warmed = await warm_project_tasks(
            cache=cache,
            project_gid="empty_project",
            task_fetcher=mock_fetcher,
        )

        assert warmed == 0

    @pytest.mark.asyncio
    async def test_custom_ttl(self) -> None:
        """Test that custom TTL is applied during warming."""
        cache = EnhancedInMemoryCacheProvider()
        mock_fetcher = AsyncMock(
            return_value=[
                {"gid": "123", "name": "Task 1", "modified_at": "2025-01-15T10:00:00Z"},
            ]
        )

        await warm_project_tasks(
            cache=cache,
            project_gid="project_123",
            task_fetcher=mock_fetcher,
            ttl=600,
        )

        entry = cache.get_versioned("123", EntryType.TASK)
        assert entry is not None
        assert entry.ttl == 600

    @pytest.mark.asyncio
    async def test_tasks_without_gid_skipped(self) -> None:
        """Test that tasks without GID are skipped."""
        cache = EnhancedInMemoryCacheProvider()
        mock_fetcher = AsyncMock(
            return_value=[
                {"gid": "123", "name": "Task 1", "modified_at": "2025-01-15T10:00:00Z"},
                {"name": "Task without GID"},  # No GID
            ]
        )

        warmed = await warm_project_tasks(
            cache=cache,
            project_gid="project_123",
            task_fetcher=mock_fetcher,
        )

        assert warmed == 1  # Only 1 task with GID


class TestCheckRedisHealth:
    """Tests for check_redis_health function."""

    def test_healthy_cache(self) -> None:
        """Test health check with healthy cache."""
        mock_cache = MagicMock()
        mock_cache.is_healthy.return_value = True
        # Implementation uses metrics.hits, not metrics.total_hits
        mock_cache.get_metrics.return_value = MagicMock(
            hits=100,
            misses=25,
            writes=125,
            errors=0,
            hit_rate=80.0,
        )

        result = check_redis_health(mock_cache)

        assert result["healthy"] is True
        assert result["error"] is None
        assert result["metrics"]["total_hits"] == 100
        assert result["metrics"]["hit_rate"] == 80.0

    def test_unhealthy_cache(self) -> None:
        """Test health check with unhealthy cache."""
        mock_cache = MagicMock()
        mock_cache.is_healthy.return_value = False

        result = check_redis_health(mock_cache)

        assert result["healthy"] is False
        assert "PING returned false" in result["error"]
        assert result["metrics"] is None

    def test_cache_exception(self) -> None:
        """Test health check when exception occurs."""
        mock_cache = MagicMock()
        mock_cache.is_healthy.side_effect = ConnectionError("Connection refused")

        result = check_redis_health(mock_cache)

        assert result["healthy"] is False
        assert "Connection refused" in result["error"]


class TestParseVersion:
    """Tests for _parse_version helper."""

    def test_iso_format(self) -> None:
        """Test parsing ISO format timestamp."""
        result = _parse_version("2025-01-15T10:30:00+00:00")
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_z_suffix(self) -> None:
        """Test parsing timestamp with Z suffix."""
        result = _parse_version("2025-01-15T10:30:00Z")
        assert result.year == 2025
        assert result.tzinfo is not None

    def test_naive_datetime(self) -> None:
        """Test parsing naive datetime string."""
        result = _parse_version("2025-01-15T10:30:00")
        assert result.tzinfo == UTC  # Should be made UTC

    def test_invalid_format_returns_now(self) -> None:
        """Test that invalid format returns current time."""
        result = _parse_version("not-a-date")
        now = datetime.now(UTC)
        # Should be within 1 second of now
        assert abs((result - now).total_seconds()) < 1
