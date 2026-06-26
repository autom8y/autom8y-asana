"""Tests for TieredCacheProvider (Redis-only after the S3 cold-tier retirement).

The S3 cold tier was the storage-topology census's *mask #1 — phantom S3 cold
tier* (wired nowhere; ``ASANA_CACHE_S3_ENABLED`` set nowhere) and is RETIRED. The
``s3_enabled`` flag, ``TieredConfig``, the optional ``cold_tier`` argument, the
promotion path, and ``get_cold_metrics`` are gone. ``TieredCacheProvider`` is now
an honest Redis-only passthrough.

These tests assert the SURVIVING behavior: every operation delegates to the hot
tier. The deleted tests exercised the retired cold-tier path (promotion, cold
hits, write-through to S3, cold-failure degradation, cold-tier metrics) — they
tested deleted behavior and were removed honestly (NOT weakened).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.cache.models.metrics import CacheMetrics
from autom8_asana.cache.providers.tiered import TieredCacheProvider
from autom8_asana.protocols.cache import CacheProvider, WarmResult

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_hot_tier() -> Mock:
    """Create a mock hot tier cache provider."""
    mock = Mock(spec=CacheProvider)
    mock.get_versioned.return_value = None
    mock.get_batch.return_value = {}
    mock.is_healthy.return_value = True
    mock.get_metrics.return_value = CacheMetrics()
    return mock


@pytest.fixture
def sample_entry() -> CacheEntry:
    """Create a sample cache entry for testing."""
    return CacheEntry(
        key="123456",
        data={"gid": "123456", "name": "Test Task"},
        entry_type=EntryType.TASK,
        version=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        cached_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        ttl=300,
    )


# ============================================================================
# Construction
# ============================================================================


class TestConstruction:
    """Tests for the Redis-only provider construction."""

    def test_constructs_over_a_single_hot_tier(self, mock_hot_tier: Mock) -> None:
        """The provider takes a single hot tier — there is no cold-tier argument."""
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)
        assert provider._hot is mock_hot_tier


# ============================================================================
# Read path (delegates to hot tier)
# ============================================================================


class TestReadPath:
    """Tests for the read path delegating to the hot tier."""

    def test_get_versioned_hit(self, mock_hot_tier: Mock, sample_entry: CacheEntry) -> None:
        """get_versioned returns the hot-tier entry."""
        mock_hot_tier.get_versioned.return_value = sample_entry
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        result = provider.get_versioned("123456", EntryType.TASK)

        assert result is sample_entry
        mock_hot_tier.get_versioned.assert_called_once()

    def test_get_versioned_miss(self, mock_hot_tier: Mock) -> None:
        """get_versioned returns None on a hot-tier miss (no cold tier to consult)."""
        mock_hot_tier.get_versioned.return_value = None
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        assert provider.get_versioned("123456", EntryType.TASK) is None


# ============================================================================
# Write path (delegates to hot tier)
# ============================================================================


class TestWritePath:
    """Tests for the write path delegating to the hot tier."""

    def test_set_versioned_delegates_to_hot(
        self, mock_hot_tier: Mock, sample_entry: CacheEntry
    ) -> None:
        """set_versioned writes to the hot tier only."""
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        provider.set_versioned("123456", sample_entry)

        mock_hot_tier.set_versioned.assert_called_once_with("123456", sample_entry)


# ============================================================================
# Batch operations (delegate to hot tier)
# ============================================================================


class TestBatchOperations:
    """Tests for batch operations."""

    def test_get_batch_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """get_batch returns the hot-tier results."""
        now = datetime.now(UTC)
        hot_entry = CacheEntry(
            key="1", data={"id": 1}, entry_type=EntryType.TASK, version=now, ttl=300
        )
        mock_hot_tier.get_batch.return_value = {"1": hot_entry, "2": None}
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        result = provider.get_batch(["1", "2"], EntryType.TASK)

        assert result["1"] is not None
        assert result["1"].data["id"] == 1
        assert result["2"] is None
        mock_hot_tier.get_batch.assert_called_once_with(["1", "2"], EntryType.TASK)

    def test_get_batch_empty_keys_short_circuits(self, mock_hot_tier: Mock) -> None:
        """get_batch with no keys returns {} without touching the hot tier."""
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        assert provider.get_batch([], EntryType.TASK) == {}
        mock_hot_tier.get_batch.assert_not_called()

    def test_set_batch_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """set_batch writes to the hot tier only."""
        now = datetime.now(UTC)
        entries = {
            "1": CacheEntry(key="1", data={"id": 1}, entry_type=EntryType.TASK, version=now),
            "2": CacheEntry(key="2", data={"id": 2}, entry_type=EntryType.TASK, version=now),
        }
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        provider.set_batch(entries)

        mock_hot_tier.set_batch.assert_called_once_with(entries)

    def test_set_batch_empty_short_circuits(self, mock_hot_tier: Mock) -> None:
        """set_batch with no entries is a no-op."""
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        provider.set_batch({})

        mock_hot_tier.set_batch.assert_not_called()


# ============================================================================
# Invalidation (delegates to hot tier)
# ============================================================================


class TestInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """invalidate removes entries from the hot tier only."""
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        provider.invalidate("123456", [EntryType.TASK])

        mock_hot_tier.invalidate.assert_called_once_with("123456", [EntryType.TASK])


# ============================================================================
# Health check
# ============================================================================


class TestHealthCheck:
    """Tests for health check operations."""

    def test_is_healthy_reflects_hot_tier(self, mock_hot_tier: Mock) -> None:
        """is_healthy mirrors the hot tier's health."""
        mock_hot_tier.is_healthy.return_value = True
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)
        assert provider.is_healthy() is True

        mock_hot_tier.is_healthy.return_value = False
        assert provider.is_healthy() is False


# ============================================================================
# clear_all_tasks
# ============================================================================


class TestClearAllTasks:
    """Tests for clear_all_tasks."""

    def test_clear_all_tasks_reports_redis_and_zero_s3(self, mock_hot_tier: Mock) -> None:
        """clear_all_tasks clears the hot tier; the s3 count is always 0 (no cold tier)."""
        mock_hot_tier.clear_all_tasks.return_value = 42
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        result = provider.clear_all_tasks()

        assert result == {"redis": 42, "s3": 0}
        mock_hot_tier.clear_all_tasks.assert_called_once()


# ============================================================================
# Metrics
# ============================================================================


class TestMetrics:
    """Tests for metrics."""

    def test_get_metrics_returns_own_metrics(self, mock_hot_tier: Mock) -> None:
        """get_metrics returns the provider's own metrics instance."""
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)
        assert provider.get_metrics() is not None

    def test_get_hot_metrics_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """get_hot_metrics returns the hot tier's metrics."""
        hot_metrics = CacheMetrics()
        mock_hot_tier.get_metrics.return_value = hot_metrics
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        assert provider.get_hot_metrics() is hot_metrics

    def test_reset_metrics_resets_own_metrics(self, mock_hot_tier: Mock) -> None:
        """reset_metrics resets the provider's own metrics only."""
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)
        provider._metrics.record_hit(1.0)
        assert provider._metrics.hits > 0

        provider.reset_metrics()

        assert provider._metrics.hits == 0


# ============================================================================
# Simple operations (backward compatibility)
# ============================================================================


class TestSimpleOperations:
    """Tests for simple key-value operations."""

    def test_simple_get_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """Simple get delegates to the hot tier."""
        mock_hot_tier.get.return_value = {"data": "value"}
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        result = provider.get("key")

        assert result == {"data": "value"}
        mock_hot_tier.get.assert_called_once_with("key")

    def test_simple_set_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """Simple set delegates to the hot tier."""
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        provider.set("key", {"data": "value"}, ttl=300)

        mock_hot_tier.set.assert_called_once_with("key", {"data": "value"}, 300)

    def test_simple_delete_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """Simple delete delegates to the hot tier."""
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        provider.delete("key")

        mock_hot_tier.delete.assert_called_once_with("key")


# ============================================================================
# Warm operations
# ============================================================================


class TestWarmOperations:
    """Tests for cache warming operations."""

    def test_warm_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """warm delegates to the hot tier."""
        mock_hot_tier.warm.return_value = WarmResult(warmed=3, failed=0, skipped=0)
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        result = provider.warm(["1", "2", "3"], [EntryType.TASK])

        assert result.warmed == 3
        mock_hot_tier.warm.assert_called_once()


# ============================================================================
# Freshness
# ============================================================================


class TestCheckFreshness:
    """Tests for freshness checking operations."""

    def test_check_freshness_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """check_freshness delegates to the hot tier."""
        mock_hot_tier.check_freshness.return_value = True
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        version = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        result = provider.check_freshness("123456", EntryType.TASK, version)

        assert result is True
        mock_hot_tier.check_freshness.assert_called_once_with("123456", EntryType.TASK, version)


class TestFreshnessPassthrough:
    """Tests for freshness parameter passthrough."""

    def test_get_versioned_passes_freshness_to_hot(
        self, mock_hot_tier: Mock, sample_entry: CacheEntry
    ) -> None:
        """get_versioned passes the freshness parameter to the hot tier."""
        mock_hot_tier.get_versioned.return_value = sample_entry
        provider = TieredCacheProvider(hot_tier=mock_hot_tier)

        provider.get_versioned("123456", EntryType.TASK, FreshnessIntent.STRICT)

        mock_hot_tier.get_versioned.assert_called_once_with(
            "123456", EntryType.TASK, FreshnessIntent.STRICT
        )
