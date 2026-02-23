"""Tests for FreshnessStamp dataclass.

Per TDD-CROSS-TIER-FRESHNESS-001: Unit tests for freshness metadata
creation, age calculation, soft invalidation, and immutability.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from autom8_asana.cache.models.freshness_stamp import (
    FreshnessStamp,
    VerificationSource,
)
from autom8_asana.cache.models.freshness_unified import FreshnessState


class TestFreshnessStampAgeSeconds:
    """Tests for age_seconds() method."""

    def test_stamp_age_seconds(self) -> None:
        """age_seconds() returns correct elapsed time."""
        verified_at = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
        now = datetime(2025, 6, 1, 12, 5, 0, tzinfo=UTC)
        stamp = FreshnessStamp(
            last_verified_at=verified_at,
            source=VerificationSource.API_FETCH,
        )
        assert stamp.age_seconds(now) == 300.0

    def test_stamp_age_seconds_with_explicit_now(self) -> None:
        """Deterministic testing with explicit now parameter."""
        verified_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        now = datetime(2025, 1, 1, 1, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(last_verified_at=verified_at)
        assert stamp.age_seconds(now) == 3600.0

    def test_stamp_age_seconds_zero(self) -> None:
        """age_seconds() returns zero when now equals verified_at."""
        t = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
        stamp = FreshnessStamp(last_verified_at=t)
        assert stamp.age_seconds(t) == 0.0


class TestFreshnessStampSoftInvalidation:
    """Tests for soft invalidation (staleness_hint)."""

    def test_stamp_is_soft_invalidated_false(self) -> None:
        """Default stamp has no staleness hint."""
        stamp = FreshnessStamp(
            last_verified_at=datetime.now(UTC),
            source=VerificationSource.API_FETCH,
        )
        assert stamp.is_soft_invalidated() is False
        assert stamp.staleness_hint is None

    def test_stamp_is_soft_invalidated_true(self) -> None:
        """Stamp with hint returns True."""
        stamp = FreshnessStamp(
            last_verified_at=datetime.now(UTC),
            staleness_hint="mutation:task:update:123",
        )
        assert stamp.is_soft_invalidated() is True

    def test_stamp_with_staleness_hint(self) -> None:
        """with_staleness_hint creates new stamp, does not mutate original."""
        original = FreshnessStamp(
            last_verified_at=datetime(2025, 1, 1, tzinfo=UTC),
            source=VerificationSource.BATCH_CHECK,
        )
        marked = original.with_staleness_hint("mutation:task:update:456")

        # Original is unchanged
        assert original.staleness_hint is None
        assert original.is_soft_invalidated() is False

        # New stamp has the hint
        assert marked.staleness_hint == "mutation:task:update:456"
        assert marked.is_soft_invalidated() is True
        assert marked.last_verified_at == original.last_verified_at
        assert marked.source == original.source


class TestFreshnessStampFactory:
    """Tests for the now() factory method."""

    def test_stamp_now_factory(self) -> None:
        """FreshnessStamp.now() creates stamp verified at current time."""
        before = datetime.now(UTC)
        stamp = FreshnessStamp.now(source=VerificationSource.API_FETCH)
        after = datetime.now(UTC)

        assert before <= stamp.last_verified_at <= after
        assert stamp.source == VerificationSource.API_FETCH
        assert stamp.staleness_hint is None

    def test_stamp_now_default_source(self) -> None:
        """now() defaults to UNKNOWN source."""
        stamp = FreshnessStamp.now()
        assert stamp.source == VerificationSource.UNKNOWN


class TestFreshnessStampImmutability:
    """Tests for frozen dataclass behavior."""

    def test_stamp_frozen(self) -> None:
        """Cannot mutate fields after creation."""
        stamp = FreshnessStamp(
            last_verified_at=datetime.now(UTC),
            source=VerificationSource.API_FETCH,
        )
        with pytest.raises(AttributeError):
            stamp.last_verified_at = datetime.now(UTC)  # type: ignore[misc]
        with pytest.raises(AttributeError):
            stamp.source = VerificationSource.BATCH_CHECK  # type: ignore[misc]
        with pytest.raises(AttributeError):
            stamp.staleness_hint = "test"  # type: ignore[misc]


class TestFreshnessStampTimezoneNormalization:
    """Tests for timezone handling."""

    def test_stamp_timezone_normalization_naive(self) -> None:
        """Handles naive datetimes by treating them as UTC."""
        naive = datetime(2025, 1, 1, 12, 0, 0)  # no tzinfo
        now = datetime(2025, 1, 1, 12, 5, 0, tzinfo=UTC)
        stamp = FreshnessStamp(last_verified_at=naive)
        # Should normalize naive to UTC for comparison
        assert stamp.age_seconds(now) == 300.0

    def test_stamp_timezone_normalization_aware(self) -> None:
        """Handles aware datetimes correctly."""
        aware = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        now = datetime(2025, 1, 1, 12, 10, 0, tzinfo=UTC)
        stamp = FreshnessStamp(last_verified_at=aware)
        assert stamp.age_seconds(now) == 600.0


class TestVerificationSourceEnum:
    """Tests for VerificationSource enum values."""

    def test_all_sources_are_strings(self) -> None:
        """All VerificationSource values are strings for JSON serialization."""
        for source in VerificationSource:
            assert isinstance(source.value, str)

    def test_source_values(self) -> None:
        """Verify expected source values exist."""
        expected = {
            "api_fetch",
            "batch_check",
            "mutation_event",
            "cache_warm",
            "promotion",
            "unknown",
        }
        actual = {s.value for s in VerificationSource}
        assert actual == expected


class TestFreshnessStateEnum:
    """Tests for FreshnessState enum values."""

    def test_state_values(self) -> None:
        """Verify all six freshness states exist with correct values."""
        assert len(FreshnessState) == 6
        assert FreshnessState.FRESH.value == "fresh"
        assert FreshnessState.APPROACHING_STALE.value == "approaching_stale"
        assert FreshnessState.STALE.value == "stale"
        assert FreshnessState.SCHEMA_INVALID.value == "schema_invalid"
        assert FreshnessState.WATERMARK_BEHIND.value == "watermark_behind"
        assert FreshnessState.CIRCUIT_FALLBACK.value == "circuit_fallback"
