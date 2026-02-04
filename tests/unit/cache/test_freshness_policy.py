"""Tests for FreshnessPolicy evaluator.

Per TDD-CROSS-TIER-FRESHNESS-001: Unit tests for freshness classification
using EntityRegistry TTLs and the three-state classification model.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.policies.freshness_policy import FreshnessPolicy
from autom8_asana.cache.models.freshness_stamp import (
    FreshnessClassification,
    FreshnessStamp,
    VerificationSource,
)


# ============================================================================
# Fixtures
# ============================================================================


def _make_entry(
    stamp: FreshnessStamp | None = None,
    ttl: int = 300,
    metadata: dict | None = None,
) -> CacheEntry:
    """Helper to create a CacheEntry with optional stamp."""
    return CacheEntry(
        key="test-123",
        data={"gid": "test-123", "name": "Test"},
        entry_type=EntryType.TASK,
        version=datetime(2025, 1, 1, tzinfo=UTC),
        cached_at=datetime(2025, 1, 1, tzinfo=UTC),
        ttl=ttl,
        freshness_stamp=stamp,
        metadata=metadata or {},
    )


# ============================================================================
# Classification Tests
# ============================================================================


class TestFreshnessPolicyEvaluate:
    """Tests for FreshnessPolicy.evaluate()."""

    def test_evaluate_fresh(self) -> None:
        """Entry within TTL classified as FRESH."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(
            last_verified_at=now - timedelta(seconds=100),
            source=VerificationSource.API_FETCH,
        )
        entry = _make_entry(stamp=stamp, ttl=300)
        policy = FreshnessPolicy()

        result = policy.evaluate(entry, now=now)
        assert result == FreshnessClassification.FRESH

    def test_evaluate_approaching_stale(self) -> None:
        """Entry at 76% of TTL classified as APPROACHING_STALE."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        # 76% of 300s = 228s age
        stamp = FreshnessStamp(
            last_verified_at=now - timedelta(seconds=228),
            source=VerificationSource.API_FETCH,
        )
        entry = _make_entry(stamp=stamp, ttl=300)
        policy = FreshnessPolicy()

        result = policy.evaluate(entry, now=now)
        assert result == FreshnessClassification.APPROACHING_STALE

    def test_evaluate_stale_beyond_ttl(self) -> None:
        """Entry past TTL classified as STALE."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(
            last_verified_at=now - timedelta(seconds=400),
            source=VerificationSource.API_FETCH,
        )
        entry = _make_entry(stamp=stamp, ttl=300)
        policy = FreshnessPolicy()

        result = policy.evaluate(entry, now=now)
        assert result == FreshnessClassification.STALE

    def test_evaluate_no_stamp_is_stale(self) -> None:
        """Entry with freshness_stamp=None classified as STALE."""
        entry = _make_entry(stamp=None)
        policy = FreshnessPolicy()

        result = policy.evaluate(entry)
        assert result == FreshnessClassification.STALE

    def test_evaluate_soft_invalidated_is_stale(self) -> None:
        """Entry with staleness_hint classified as STALE regardless of age."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(
            last_verified_at=now - timedelta(seconds=10),  # very fresh
            source=VerificationSource.API_FETCH,
            staleness_hint="mutation:task:update:123",
        )
        entry = _make_entry(stamp=stamp, ttl=300)
        policy = FreshnessPolicy()

        result = policy.evaluate(entry, now=now)
        assert result == FreshnessClassification.STALE


class TestFreshnessPolicyRegistryTTL:
    """Tests for TTL resolution from EntityRegistry."""

    def test_evaluate_uses_registry_ttl(self) -> None:
        """TTL resolved from EntityRegistry via entity_type."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        # "business" entity has 3600s TTL in EntityRegistry
        # 100s age should be FRESH for a 3600s TTL
        stamp = FreshnessStamp(
            last_verified_at=now - timedelta(seconds=100),
            source=VerificationSource.API_FETCH,
        )
        entry = _make_entry(stamp=stamp, ttl=300)
        policy = FreshnessPolicy()

        result = policy.evaluate(entry, entity_type="business", now=now)
        assert result == FreshnessClassification.FRESH

    def test_evaluate_fallback_ttl(self) -> None:
        """Unknown entity uses entry TTL or DEFAULT_TTL."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(
            last_verified_at=now - timedelta(seconds=100),
            source=VerificationSource.API_FETCH,
        )
        entry = _make_entry(stamp=stamp, ttl=200)
        policy = FreshnessPolicy()

        # Unknown entity type falls back to entry TTL (200)
        # 100s / 200s = 50% -> FRESH
        result = policy.evaluate(
            entry, entity_type="nonexistent_entity_xyz", now=now
        )
        assert result == FreshnessClassification.FRESH

    def test_evaluate_metadata_entity_type(self) -> None:
        """Entity type resolved from entry metadata."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(
            last_verified_at=now - timedelta(seconds=100),
            source=VerificationSource.API_FETCH,
        )
        # "business" has 3600s TTL, 100s is well within FRESH
        entry = _make_entry(
            stamp=stamp, ttl=300, metadata={"entity_type": "business"}
        )
        policy = FreshnessPolicy()

        result = policy.evaluate(entry, now=now)
        assert result == FreshnessClassification.FRESH


class TestFreshnessPolicyEvaluateStamp:
    """Tests for FreshnessPolicy.evaluate_stamp()."""

    def test_evaluate_stamp_direct(self) -> None:
        """evaluate_stamp() works with explicit TTL."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(
            last_verified_at=now - timedelta(seconds=50),
            source=VerificationSource.BATCH_CHECK,
        )
        policy = FreshnessPolicy()

        result = policy.evaluate_stamp(stamp, ttl_seconds=300, now=now)
        assert result == FreshnessClassification.FRESH

    def test_evaluate_stamp_approaching(self) -> None:
        """evaluate_stamp() returns APPROACHING_STALE at threshold."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(
            last_verified_at=now - timedelta(seconds=240),
            source=VerificationSource.API_FETCH,
        )
        policy = FreshnessPolicy()

        # 240 / 300 = 80% > 75% threshold
        result = policy.evaluate_stamp(stamp, ttl_seconds=300, now=now)
        assert result == FreshnessClassification.APPROACHING_STALE

    def test_evaluate_stamp_stale(self) -> None:
        """evaluate_stamp() returns STALE beyond TTL."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(
            last_verified_at=now - timedelta(seconds=500),
            source=VerificationSource.API_FETCH,
        )
        policy = FreshnessPolicy()

        result = policy.evaluate_stamp(stamp, ttl_seconds=300, now=now)
        assert result == FreshnessClassification.STALE

    def test_evaluate_stamp_soft_invalidated(self) -> None:
        """evaluate_stamp() returns STALE for soft-invalidated stamp."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(
            last_verified_at=now,
            source=VerificationSource.API_FETCH,
            staleness_hint="test",
        )
        policy = FreshnessPolicy()

        result = policy.evaluate_stamp(stamp, ttl_seconds=300, now=now)
        assert result == FreshnessClassification.STALE


class TestFreshnessPolicyCustomThreshold:
    """Tests for custom approaching_threshold."""

    def test_custom_approaching_threshold(self) -> None:
        """Non-default threshold value works."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(
            last_verified_at=now - timedelta(seconds=160),
            source=VerificationSource.API_FETCH,
        )
        entry = _make_entry(stamp=stamp, ttl=300)

        # With 0.5 threshold: 160/300 = 53% > 50% -> APPROACHING_STALE
        policy = FreshnessPolicy(approaching_threshold=0.5)
        result = policy.evaluate(entry, now=now)
        assert result == FreshnessClassification.APPROACHING_STALE

        # With 0.9 threshold: 160/300 = 53% < 90% -> FRESH
        policy_high = FreshnessPolicy(approaching_threshold=0.9)
        result_high = policy_high.evaluate(entry, now=now)
        assert result_high == FreshnessClassification.FRESH
