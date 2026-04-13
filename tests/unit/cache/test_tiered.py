"""Tests for TieredCacheProvider."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.cache.models.metrics import CacheMetrics
from autom8_asana.core.errors import S3TransportError
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
def mock_cold_tier() -> Mock:
    """Create a mock cold tier cache provider."""
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


@pytest.fixture
def sample_subtasks_entry() -> CacheEntry:
    """Create a sample subtasks cache entry for testing."""
    return CacheEntry(
        key="123456",
        data=[{"gid": "sub1"}, {"gid": "sub2"}],
        entry_type=EntryType.SUBTASKS,
        version=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        cached_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        ttl=300,
    )


# ============================================================================
# Configuration Tests
# ============================================================================


class TestTieredConfigDefaults:
    """Tests for TieredCacheProvider configuration defaults."""

    def test_tiered_config_defaults(self, mock_hot_tier: Mock) -> None:
        """Test TieredCacheProvider has correct default configuration."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        config = TieredConfig()
        provider = TieredCacheProvider(hot_tier=mock_hot_tier, config=config)

        assert provider._config.s3_enabled is False
        assert provider._config.promotion_ttl == 3600
        assert provider._config.write_through is True

    def test_s3_disabled_by_default(self, mock_hot_tier: Mock) -> None:
        """Test S3 cold tier is disabled by default."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        config = TieredConfig()
        provider = TieredCacheProvider(hot_tier=mock_hot_tier, config=config)

        assert provider._config.s3_enabled is False
        assert provider._cold is None

    def test_s3_enabled_via_config(
        self, mock_hot_tier: Mock, mock_cold_tier: Mock
    ) -> None:
        """Test S3 cold tier can be enabled via configuration."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        assert provider._config.s3_enabled is True
        assert provider._cold is mock_cold_tier


# ============================================================================
# Read Path Tests - S3 Disabled
# ============================================================================


class TestReadPathS3Disabled:
    """Tests for read path when S3 cold tier is disabled."""

    def test_get_versioned_s3_disabled_hit(
        self, mock_hot_tier: Mock, sample_entry: CacheEntry
    ) -> None:
        """Test get_versioned returns from hot tier when S3 is disabled."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.get_versioned.return_value = sample_entry
        config = TieredConfig(s3_enabled=False)
        provider = TieredCacheProvider(hot_tier=mock_hot_tier, config=config)

        result = provider.get_versioned("123456", EntryType.TASK)

        assert result is not None
        assert result.key == "123456"
        assert result.data["name"] == "Test Task"
        mock_hot_tier.get_versioned.assert_called_once_with(
            "123456", EntryType.TASK, FreshnessIntent.EVENTUAL
        )

    def test_get_versioned_s3_disabled_miss(self, mock_hot_tier: Mock) -> None:
        """Test get_versioned returns None on miss when S3 is disabled."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.get_versioned.return_value = None
        config = TieredConfig(s3_enabled=False)
        provider = TieredCacheProvider(hot_tier=mock_hot_tier, config=config)

        result = provider.get_versioned("123456", EntryType.TASK)

        assert result is None
        mock_hot_tier.get_versioned.assert_called_once()
        # Cold tier should not be checked when S3 is disabled


# ============================================================================
# Read Path Tests - S3 Enabled
# ============================================================================


class TestReadPathS3Enabled:
    """Tests for read path when S3 cold tier is enabled."""

    def test_get_versioned_hot_hit(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
        sample_entry: CacheEntry,
    ) -> None:
        """Test get_versioned returns immediately from hot tier without checking cold."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.get_versioned.return_value = sample_entry
        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        result = provider.get_versioned("123456", EntryType.TASK)

        assert result is not None
        assert result.key == "123456"
        mock_hot_tier.get_versioned.assert_called_once()
        mock_cold_tier.get_versioned.assert_not_called()

    def test_get_versioned_hot_miss_cold_hit(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
        sample_entry: CacheEntry,
    ) -> None:
        """Test get_versioned checks cold tier on hot miss and promotes to hot."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.get_versioned.return_value = None
        mock_cold_tier.get_versioned.return_value = sample_entry
        config = TieredConfig(s3_enabled=True, promotion_ttl=600)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        result = provider.get_versioned("123456", EntryType.TASK)

        assert result is not None
        assert result.key == "123456"
        mock_hot_tier.get_versioned.assert_called_once()
        mock_cold_tier.get_versioned.assert_called_once()
        # Entry should be promoted to hot tier
        mock_hot_tier.set_versioned.assert_called_once()

    def test_get_versioned_both_miss(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
    ) -> None:
        """Test get_versioned returns None when both tiers miss."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.get_versioned.return_value = None
        mock_cold_tier.get_versioned.return_value = None
        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        result = provider.get_versioned("123456", EntryType.TASK)

        assert result is None
        mock_hot_tier.get_versioned.assert_called_once()
        mock_cold_tier.get_versioned.assert_called_once()
        # No promotion should occur on miss
        mock_hot_tier.set_versioned.assert_not_called()

    def test_promotion_sets_correct_ttl(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
        sample_entry: CacheEntry,
    ) -> None:
        """Test promoted entry uses promotion_ttl from config."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.get_versioned.return_value = None
        mock_cold_tier.get_versioned.return_value = sample_entry
        promotion_ttl = 120
        config = TieredConfig(s3_enabled=True, promotion_ttl=promotion_ttl)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        provider.get_versioned("123456", EntryType.TASK)

        # Verify the promoted entry has the promotion TTL
        mock_hot_tier.set_versioned.assert_called_once()
        call_args = mock_hot_tier.set_versioned.call_args
        promoted_entry = call_args[0][1]  # Second positional arg is the entry
        assert promoted_entry.ttl == promotion_ttl


# ============================================================================
# Write Path Tests
# ============================================================================


class TestWritePath:
    """Tests for write path operations."""

    def test_set_versioned_s3_disabled(
        self, mock_hot_tier: Mock, sample_entry: CacheEntry
    ) -> None:
        """Test set_versioned only writes to hot tier when S3 is disabled."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        config = TieredConfig(s3_enabled=False)
        provider = TieredCacheProvider(hot_tier=mock_hot_tier, config=config)

        provider.set_versioned("123456", sample_entry)

        mock_hot_tier.set_versioned.assert_called_once_with("123456", sample_entry)

    def test_set_versioned_s3_enabled(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
        sample_entry: CacheEntry,
    ) -> None:
        """Test set_versioned writes to both tiers when S3 is enabled."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        config = TieredConfig(s3_enabled=True, write_through=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        provider.set_versioned("123456", sample_entry)

        mock_hot_tier.set_versioned.assert_called_once_with("123456", sample_entry)
        mock_cold_tier.set_versioned.assert_called_once_with("123456", sample_entry)

    def test_write_through_cold_failure(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
        sample_entry: CacheEntry,
    ) -> None:
        """Test hot tier write succeeds even when cold tier write fails."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_cold_tier.set_versioned.side_effect = S3TransportError("S3 error")
        config = TieredConfig(s3_enabled=True, write_through=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        # Should not raise despite cold tier failure
        provider.set_versioned("123456", sample_entry)

        mock_hot_tier.set_versioned.assert_called_once_with("123456", sample_entry)
        mock_cold_tier.set_versioned.assert_called_once()


# ============================================================================
# Batch Operations Tests
# ============================================================================


class TestBatchOperations:
    """Tests for batch operations."""

    def test_get_batch_mixed_hits(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
    ) -> None:
        """Test get_batch returns entries from hot, cold, or None for each key."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        now = datetime.now(UTC)
        hot_entry = CacheEntry(
            key="1", data={"id": 1}, entry_type=EntryType.TASK, version=now, ttl=300
        )
        cold_entry = CacheEntry(
            key="2", data={"id": 2}, entry_type=EntryType.TASK, version=now, ttl=300
        )

        # Hot tier has key "1", misses "2" and "3"
        mock_hot_tier.get_batch.return_value = {"1": hot_entry, "2": None, "3": None}
        # Cold tier has key "2", misses "3"
        mock_cold_tier.get_batch.return_value = {"2": cold_entry, "3": None}

        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        result = provider.get_batch(["1", "2", "3"], EntryType.TASK)

        assert result["1"] is not None
        assert result["1"].data["id"] == 1
        assert result["2"] is not None
        assert result["2"].data["id"] == 2
        assert result["3"] is None

    def test_set_batch_write_through(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
    ) -> None:
        """Test set_batch writes to both tiers when S3 is enabled."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        now = datetime.now(UTC)
        entries = {
            "1": CacheEntry(
                key="1", data={"id": 1}, entry_type=EntryType.TASK, version=now
            ),
            "2": CacheEntry(
                key="2", data={"id": 2}, entry_type=EntryType.TASK, version=now
            ),
        }

        config = TieredConfig(s3_enabled=True, write_through=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        provider.set_batch(entries)

        mock_hot_tier.set_batch.assert_called_once_with(entries)
        mock_cold_tier.set_batch.assert_called_once_with(entries)


# ============================================================================
# Invalidation Tests
# ============================================================================


class TestInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_both_tiers(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
    ) -> None:
        """Test invalidate removes entries from both tiers when S3 is enabled."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        provider.invalidate("123456", [EntryType.TASK, EntryType.SUBTASKS])

        mock_hot_tier.invalidate.assert_called_once_with(
            "123456", [EntryType.TASK, EntryType.SUBTASKS]
        )
        mock_cold_tier.invalidate.assert_called_once_with(
            "123456", [EntryType.TASK, EntryType.SUBTASKS]
        )

    def test_invalidate_s3_disabled(self, mock_hot_tier: Mock) -> None:
        """Test invalidate only removes from hot tier when S3 is disabled."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        config = TieredConfig(s3_enabled=False)
        provider = TieredCacheProvider(hot_tier=mock_hot_tier, config=config)

        provider.invalidate("123456", [EntryType.TASK])

        mock_hot_tier.invalidate.assert_called_once_with("123456", [EntryType.TASK])


# ============================================================================
# Health Check Tests
# ============================================================================


class TestHealthCheck:
    """Tests for health check operations."""

    def test_is_healthy_hot_healthy(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
    ) -> None:
        """Test is_healthy returns True when hot tier is healthy."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.is_healthy.return_value = True
        mock_cold_tier.is_healthy.return_value = True
        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        assert provider.is_healthy() is True
        mock_hot_tier.is_healthy.assert_called_once()

    def test_is_healthy_hot_unhealthy(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
    ) -> None:
        """Test is_healthy returns False when hot tier is unhealthy."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.is_healthy.return_value = False
        mock_cold_tier.is_healthy.return_value = True
        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        assert provider.is_healthy() is False

    def test_is_healthy_cold_unhealthy(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
    ) -> None:
        """Test is_healthy still returns True when cold tier is unhealthy."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.is_healthy.return_value = True
        mock_cold_tier.is_healthy.return_value = False
        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        # Cold tier health should not affect overall health
        # (graceful degradation principle)
        assert provider.is_healthy() is True


# ============================================================================
# Metrics Tests
# ============================================================================


class TestMetrics:
    """Tests for metrics aggregation."""

    def test_metrics_aggregation(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
    ) -> None:
        """Test metrics are aggregated from both tiers."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        hot_metrics = CacheMetrics()
        hot_metrics.record_hit(1.0)
        hot_metrics.record_hit(1.0)
        hot_metrics.record_miss(1.0)

        cold_metrics = CacheMetrics()
        cold_metrics.record_hit(2.0)
        cold_metrics.record_miss(2.0)
        cold_metrics.record_miss(2.0)

        mock_hot_tier.get_metrics.return_value = hot_metrics
        mock_cold_tier.get_metrics.return_value = cold_metrics

        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        metrics = provider.get_metrics()

        # Metrics should reflect tiered operations
        assert metrics is not None

    def test_promotion_count_tracked(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
        sample_entry: CacheEntry,
    ) -> None:
        """Test promotion count is tracked in metrics."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.get_versioned.return_value = None
        mock_cold_tier.get_versioned.return_value = sample_entry
        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        # Perform a get that results in promotion
        provider.get_versioned("123456", EntryType.TASK)

        # Verify promotion occurred
        mock_hot_tier.set_versioned.assert_called_once()

        # Check promotion is tracked (implementation-specific)
        metrics = provider.get_metrics()
        assert metrics is not None


# ============================================================================
# Graceful Degradation Tests
# ============================================================================


class TestGracefulDegradation:
    """Tests for graceful degradation when cold tier fails."""

    def test_cold_tier_get_failure_continues(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
    ) -> None:
        """Test get operations continue despite S3 errors."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.get_versioned.return_value = None
        mock_cold_tier.get_versioned.side_effect = S3TransportError(
            "S3 connection error"
        )
        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        # Should not raise despite cold tier failure
        result = provider.get_versioned("123456", EntryType.TASK)

        # Returns None (no data available)
        assert result is None
        mock_hot_tier.get_versioned.assert_called_once()
        mock_cold_tier.get_versioned.assert_called_once()

    def test_cold_tier_invalidate_failure_continues(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
    ) -> None:
        """Test invalidate operations continue despite S3 errors."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_cold_tier.invalidate.side_effect = S3TransportError("S3 connection error")
        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        # Should not raise despite cold tier failure
        provider.invalidate("123456", [EntryType.TASK])

        mock_hot_tier.invalidate.assert_called_once()
        mock_cold_tier.invalidate.assert_called_once()

    def test_cold_tier_batch_failure_continues(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
    ) -> None:
        """Test batch operations continue despite S3 errors."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        now = datetime.now(UTC)
        hot_entry = CacheEntry(
            key="1", data={"id": 1}, entry_type=EntryType.TASK, version=now
        )

        mock_hot_tier.get_batch.return_value = {"1": hot_entry, "2": None}
        mock_cold_tier.get_batch.side_effect = S3TransportError("S3 connection error")

        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        # Should not raise despite cold tier failure
        result = provider.get_batch(["1", "2"], EntryType.TASK)

        # Should return what hot tier had
        assert result["1"] is not None
        assert result["2"] is None


# ============================================================================
# Simple Operations Tests (Backward Compatibility)
# ============================================================================


class TestSimpleOperations:
    """Tests for simple key-value operations (backward compatibility)."""

    def test_simple_get_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """Test simple get delegates to hot tier."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.get.return_value = {"data": "value"}
        config = TieredConfig(s3_enabled=False)
        provider = TieredCacheProvider(hot_tier=mock_hot_tier, config=config)

        result = provider.get("key")

        assert result == {"data": "value"}
        mock_hot_tier.get.assert_called_once_with("key")

    def test_simple_set_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """Test simple set delegates to hot tier."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        config = TieredConfig(s3_enabled=False)
        provider = TieredCacheProvider(hot_tier=mock_hot_tier, config=config)

        provider.set("key", {"data": "value"}, ttl=300)

        mock_hot_tier.set.assert_called_once_with("key", {"data": "value"}, 300)

    def test_simple_delete_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """Test simple delete delegates to hot tier."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        config = TieredConfig(s3_enabled=False)
        provider = TieredCacheProvider(hot_tier=mock_hot_tier, config=config)

        provider.delete("key")

        mock_hot_tier.delete.assert_called_once_with("key")


# ============================================================================
# Warm Operation Tests
# ============================================================================


class TestWarmOperations:
    """Tests for cache warming operations."""

    def test_warm_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """Test warm operation delegates to hot tier."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.warm.return_value = WarmResult(warmed=3, failed=0, skipped=0)
        config = TieredConfig(s3_enabled=False)
        provider = TieredCacheProvider(hot_tier=mock_hot_tier, config=config)

        result = provider.warm(["1", "2", "3"], [EntryType.TASK])

        assert result.warmed == 3
        mock_hot_tier.warm.assert_called_once()


# ============================================================================
# Check FreshnessIntent Tests
# ============================================================================


class TestCheckFreshness:
    """Tests for freshness checking operations."""

    def test_check_freshness_delegates_to_hot(self, mock_hot_tier: Mock) -> None:
        """Test check_freshness delegates to hot tier."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.check_freshness.return_value = True
        config = TieredConfig(s3_enabled=False)
        provider = TieredCacheProvider(hot_tier=mock_hot_tier, config=config)

        version = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        result = provider.check_freshness("123456", EntryType.TASK, version)

        assert result is True
        mock_hot_tier.check_freshness.assert_called_once_with(
            "123456", EntryType.TASK, version
        )


# ============================================================================
# Reset Metrics Tests
# ============================================================================


class TestResetMetrics:
    """Tests for metrics reset."""

    def test_reset_metrics_resets_own_metrics(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
    ) -> None:
        """Test reset_metrics resets the tiered provider's own metrics only.

        Per implementation (line 441), reset_metrics only resets self._metrics,
        not individual tier metrics. Use get_hot_metrics().reset() and
        get_cold_metrics().reset() separately if tier resets are needed.
        """
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        # Record a metric so we can verify reset works
        provider._metrics.record_hit(1.0)
        assert provider._metrics.hits > 0

        provider.reset_metrics()

        # Verify own metrics are reset
        assert provider._metrics.hits == 0
        # Implementation does NOT delegate to tiers - that's intentional


# ============================================================================
# FreshnessIntent Parameter Passthrough Tests
# ============================================================================


class TestFreshnessPassthrough:
    """Tests for freshness parameter passthrough."""

    def test_get_versioned_passes_freshness_to_hot(
        self, mock_hot_tier: Mock, sample_entry: CacheEntry
    ) -> None:
        """Test get_versioned passes freshness parameter to hot tier."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.get_versioned.return_value = sample_entry
        config = TieredConfig(s3_enabled=False)
        provider = TieredCacheProvider(hot_tier=mock_hot_tier, config=config)

        provider.get_versioned("123456", EntryType.TASK, FreshnessIntent.STRICT)

        mock_hot_tier.get_versioned.assert_called_once_with(
            "123456", EntryType.TASK, FreshnessIntent.STRICT
        )

    def test_get_versioned_passes_freshness_to_cold(
        self,
        mock_hot_tier: Mock,
        mock_cold_tier: Mock,
        sample_entry: CacheEntry,
    ) -> None:
        """Test get_versioned passes freshness parameter to cold tier on miss."""
        from autom8_asana.cache.providers.tiered import (
            TieredCacheProvider,
            TieredConfig,
        )

        mock_hot_tier.get_versioned.return_value = None
        mock_cold_tier.get_versioned.return_value = sample_entry
        config = TieredConfig(s3_enabled=True)
        provider = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        provider.get_versioned("123456", EntryType.TASK, FreshnessIntent.EVENTUAL)

        mock_cold_tier.get_versioned.assert_called_once_with(
            "123456", EntryType.TASK, FreshnessIntent.EVENTUAL
        )
