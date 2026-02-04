"""Tests for CacheEntry freshness_stamp extension.

Per TDD-CROSS-TIER-FRESHNESS-001: Backward compatibility tests ensuring
the new optional freshness_stamp field does not break existing behavior.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness_stamp import FreshnessStamp, VerificationSource


class TestCacheEntryFreshnessStamp:
    """Tests for CacheEntry.freshness_stamp field."""

    def test_cache_entry_default_stamp_is_none(self) -> None:
        """Backward compat: no stamp by default."""
        entry = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
        )
        assert entry.freshness_stamp is None

    def test_cache_entry_with_stamp(self) -> None:
        """Can construct with freshness_stamp."""
        stamp = FreshnessStamp(
            last_verified_at=datetime(2025, 6, 1, tzinfo=UTC),
            source=VerificationSource.API_FETCH,
        )
        entry = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            freshness_stamp=stamp,
        )
        assert entry.freshness_stamp is stamp
        assert entry.freshness_stamp.source == VerificationSource.API_FETCH

    def test_cache_entry_replace_preserves_stamp(self) -> None:
        """dataclasses.replace carries stamp through."""
        stamp = FreshnessStamp(
            last_verified_at=datetime(2025, 6, 1, tzinfo=UTC),
            source=VerificationSource.BATCH_CHECK,
        )
        original = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            freshness_stamp=stamp,
        )

        # Replace TTL but stamp should be preserved
        replaced = replace(original, ttl=600)
        assert replaced.ttl == 600
        assert replaced.freshness_stamp is stamp

    def test_cache_entry_replace_updates_stamp(self) -> None:
        """dataclasses.replace can update the stamp."""
        original_stamp = FreshnessStamp(
            last_verified_at=datetime(2025, 6, 1, tzinfo=UTC),
            source=VerificationSource.API_FETCH,
        )
        new_stamp = FreshnessStamp(
            last_verified_at=datetime(2025, 6, 2, tzinfo=UTC),
            source=VerificationSource.PROMOTION,
        )
        original = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            freshness_stamp=original_stamp,
        )

        replaced = replace(original, freshness_stamp=new_stamp)
        assert replaced.freshness_stamp is new_stamp
        assert replaced.freshness_stamp.source == VerificationSource.PROMOTION

    def test_cache_entry_existing_methods_unaffected(self) -> None:
        """Existing methods work regardless of stamp presence."""
        entry_with_stamp = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            cached_at=datetime(2025, 1, 1, tzinfo=UTC),
            ttl=300,
            freshness_stamp=FreshnessStamp.now(VerificationSource.API_FETCH),
        )
        entry_without_stamp = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            cached_at=datetime(2025, 1, 1, tzinfo=UTC),
            ttl=300,
        )

        # is_expired should work the same
        now = datetime(2025, 1, 1, 0, 1, 0, tzinfo=UTC)
        assert entry_with_stamp.is_expired(now) is False
        assert entry_without_stamp.is_expired(now) is False

        # is_current should work the same
        assert entry_with_stamp.is_current(datetime(2025, 1, 1, tzinfo=UTC)) is True
        assert entry_without_stamp.is_current(datetime(2025, 1, 1, tzinfo=UTC)) is True
