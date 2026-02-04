"""Tests for TieredCacheProvider freshness stamp propagation.

Per TDD-CROSS-TIER-FRESHNESS-001: Tests for stamp preservation and
source update during cold-to-hot promotion.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness_stamp import FreshnessStamp, VerificationSource
from autom8_asana.cache.models.metrics import CacheMetrics
from autom8_asana.cache.providers.tiered import TieredCacheProvider, TieredConfig
from autom8_asana.protocols.cache import CacheProvider


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


# ============================================================================
# Promotion Freshness Tests
# ============================================================================


class TestPromotePreservesStamp:
    """Tests for freshness stamp preservation during promotion."""

    def test_promote_preserves_stamp(
        self, mock_hot_tier: Mock, mock_cold_tier: Mock
    ) -> None:
        """Promoted entry has PROMOTION source with original verification time."""
        original_verified_at = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(
            last_verified_at=original_verified_at,
            source=VerificationSource.API_FETCH,
        )
        entry = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            cached_at=datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC),
            ttl=300,
            freshness_stamp=stamp,
        )

        config = TieredConfig(s3_enabled=True, promotion_ttl=3600)
        tiered = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        promoted = tiered._promote_entry(entry)

        # Source should be PROMOTION
        assert promoted.freshness_stamp is not None
        assert promoted.freshness_stamp.source == VerificationSource.PROMOTION

        # Original verification time is preserved
        assert promoted.freshness_stamp.last_verified_at == original_verified_at

        # TTL should be promotion_ttl
        assert promoted.ttl == 3600

    def test_promote_preserves_staleness_hint(
        self, mock_hot_tier: Mock, mock_cold_tier: Mock
    ) -> None:
        """Staleness hint survives promotion."""
        stamp = FreshnessStamp(
            last_verified_at=datetime(2025, 6, 1, tzinfo=UTC),
            source=VerificationSource.API_FETCH,
            staleness_hint="mutation:task:update:999",
        )
        entry = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            ttl=300,
            freshness_stamp=stamp,
        )

        config = TieredConfig(s3_enabled=True)
        tiered = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        promoted = tiered._promote_entry(entry)

        assert promoted.freshness_stamp is not None
        assert promoted.freshness_stamp.staleness_hint == "mutation:task:update:999"
        assert promoted.freshness_stamp.source == VerificationSource.PROMOTION

    def test_promote_without_stamp(
        self, mock_hot_tier: Mock, mock_cold_tier: Mock
    ) -> None:
        """Entry without stamp promotes with stamp=None (backward compat)."""
        entry = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            ttl=300,
        )

        config = TieredConfig(s3_enabled=True)
        tiered = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        promoted = tiered._promote_entry(entry)

        assert promoted.freshness_stamp is None
        assert promoted.ttl == config.promotion_ttl


class TestTieredGetVersionedFreshnessFlow:
    """Tests for full get_versioned flow with freshness stamps."""

    def test_cold_hit_promotes_with_freshness(
        self, mock_hot_tier: Mock, mock_cold_tier: Mock
    ) -> None:
        """Cold tier hit promotes entry with PROMOTION source stamp."""
        original_stamp = FreshnessStamp(
            last_verified_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
            source=VerificationSource.API_FETCH,
        )
        cold_entry = CacheEntry(
            key="456",
            data={"gid": "456"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            ttl=604800,
            freshness_stamp=original_stamp,
        )

        mock_hot_tier.get_versioned.return_value = None
        mock_cold_tier.get_versioned.return_value = cold_entry

        config = TieredConfig(s3_enabled=True, promotion_ttl=3600)
        tiered = TieredCacheProvider(
            hot_tier=mock_hot_tier,
            cold_tier=mock_cold_tier,
            config=config,
        )

        result = tiered.get_versioned("456", EntryType.TASK)

        # Result is the cold entry (not the promoted one)
        assert result is cold_entry
        assert result.freshness_stamp is original_stamp

        # But the promoted entry written to hot tier has PROMOTION source
        mock_hot_tier.set_versioned.assert_called_once()
        promoted_entry = mock_hot_tier.set_versioned.call_args[0][1]
        assert promoted_entry.freshness_stamp is not None
        assert promoted_entry.freshness_stamp.source == VerificationSource.PROMOTION
        assert (
            promoted_entry.freshness_stamp.last_verified_at
            == original_stamp.last_verified_at
        )
