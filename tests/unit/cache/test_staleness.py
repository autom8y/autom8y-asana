"""Tests for staleness detection helpers."""

from datetime import datetime, timedelta, timezone


from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.freshness import Freshness
from autom8_asana.cache.staleness import (
    check_batch_staleness,
    check_entry_staleness,
    partition_by_staleness,
)


class TestCheckEntryStaleness:
    """Tests for check_entry_staleness function."""

    def test_expired_entry_is_stale(self) -> None:
        """Test that expired entries are always stale."""
        # Entry with 1 second TTL, created 2 seconds ago
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc) - timedelta(seconds=2),
            ttl=1,
        )

        assert check_entry_staleness(entry, None, Freshness.EVENTUAL) is True
        assert check_entry_staleness(entry, None, Freshness.STRICT) is True

    def test_eventual_freshness_trusts_ttl(self) -> None:
        """Test that EVENTUAL freshness only checks TTL."""
        now = datetime.now(timezone.utc)
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=now - timedelta(hours=1),  # Old version
            cached_at=now,  # Recently cached
            ttl=300,
        )

        # Even with old version, EVENTUAL should not be stale if TTL valid
        newer_version = (now + timedelta(minutes=30)).isoformat()
        assert check_entry_staleness(entry, newer_version, Freshness.EVENTUAL) is False

    def test_strict_freshness_checks_version(self) -> None:
        """Test that STRICT freshness verifies version."""
        now = datetime.now(timezone.utc)
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=now - timedelta(hours=1),
            cached_at=now,
            ttl=300,
        )

        # Newer source version should be stale in STRICT mode
        newer_version = now.isoformat()
        assert check_entry_staleness(entry, newer_version, Freshness.STRICT) is True

    def test_strict_freshness_current_version(self) -> None:
        """Test that STRICT freshness accepts current version."""
        now = datetime.now(timezone.utc)
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=now,
            cached_at=now,
            ttl=300,
        )

        # Same or older source version is not stale
        same_version = now.isoformat()
        older_version = (now - timedelta(hours=1)).isoformat()

        assert check_entry_staleness(entry, same_version, Freshness.STRICT) is False
        assert check_entry_staleness(entry, older_version, Freshness.STRICT) is False

    def test_strict_without_current_version_is_stale(self) -> None:
        """Test that STRICT without current version treats as stale."""
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
            ttl=300,
        )

        # Cannot verify without current version in STRICT mode
        assert check_entry_staleness(entry, None, Freshness.STRICT) is True

    def test_version_string_with_z_suffix(self) -> None:
        """Test version comparison with Z suffix timestamp."""
        now = datetime.now(timezone.utc)
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=now,
            ttl=300,
        )

        # Z suffix should be handled correctly
        newer_version = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert check_entry_staleness(entry, newer_version, Freshness.STRICT) is True

    def test_no_ttl_not_expired(self) -> None:
        """Test that entries without TTL are not expired."""
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc) - timedelta(days=365),
            ttl=None,  # No expiration
        )

        assert check_entry_staleness(entry, None, Freshness.EVENTUAL) is False


class TestCheckBatchStaleness:
    """Tests for check_batch_staleness function."""

    def test_all_missing_entries(self) -> None:
        """Test that missing entries are marked stale."""
        cache = EnhancedInMemoryCacheProvider()

        result = check_batch_staleness(
            cache,
            ["123", "456", "789"],
            EntryType.TASK,
            {},
            Freshness.EVENTUAL,
        )

        assert result == {"123": True, "456": True, "789": True}

    def test_all_cached_entries_eventual(self) -> None:
        """Test cached entries in EVENTUAL mode."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        # Pre-populate cache
        for gid in ["123", "456", "789"]:
            cache.set_versioned(
                gid,
                CacheEntry(
                    key=gid,
                    data={"gid": gid},
                    entry_type=EntryType.TASK,
                    version=now,
                    ttl=300,
                ),
            )

        result = check_batch_staleness(
            cache,
            ["123", "456", "789"],
            EntryType.TASK,
            {"123": now.isoformat(), "456": now.isoformat(), "789": now.isoformat()},
            Freshness.EVENTUAL,
        )

        assert result == {"123": False, "456": False, "789": False}

    def test_mixed_cached_and_missing(self) -> None:
        """Test mix of cached and missing entries."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        # Only cache "123"
        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={"gid": "123"},
                entry_type=EntryType.TASK,
                version=now,
                ttl=300,
            ),
        )

        result = check_batch_staleness(
            cache,
            ["123", "456"],
            EntryType.TASK,
            {},
            Freshness.EVENTUAL,
        )

        assert result["123"] is False  # Cached
        assert result["456"] is True  # Missing

    def test_strict_mode_with_versions(self) -> None:
        """Test STRICT mode compares versions."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)
        older = now - timedelta(hours=1)

        # Cache with older version
        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={"gid": "123"},
                entry_type=EntryType.TASK,
                version=older,
                ttl=300,
            ),
        )

        result = check_batch_staleness(
            cache,
            ["123"],
            EntryType.TASK,
            {"123": now.isoformat()},  # Newer current version
            Freshness.STRICT,
        )

        assert result["123"] is True  # Stale because version is older

    def test_empty_gids_list(self) -> None:
        """Test with empty GIDs list."""
        cache = EnhancedInMemoryCacheProvider()

        result = check_batch_staleness(
            cache,
            [],
            EntryType.TASK,
            {},
            Freshness.EVENTUAL,
        )

        assert result == {}

    def test_different_entry_types(self) -> None:
        """Test that entry types are respected."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(timezone.utc)

        # Cache as TASK type
        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={"gid": "123"},
                entry_type=EntryType.TASK,
                ttl=300,
                version=now,
            ),
        )

        # Query as SUBTASKS type - should be stale (not found)
        result = check_batch_staleness(
            cache,
            ["123"],
            EntryType.SUBTASKS,
            {},
            Freshness.EVENTUAL,
        )

        assert result["123"] is True


class TestPartitionByStaleness:
    """Tests for partition_by_staleness function."""

    def test_all_stale(self) -> None:
        """Test partition with all stale entries."""
        staleness = {"123": True, "456": True, "789": True}
        stale, current = partition_by_staleness(staleness)

        assert sorted(stale) == ["123", "456", "789"]
        assert current == []

    def test_all_current(self) -> None:
        """Test partition with all current entries."""
        staleness = {"123": False, "456": False, "789": False}
        stale, current = partition_by_staleness(staleness)

        assert stale == []
        assert sorted(current) == ["123", "456", "789"]

    def test_mixed(self) -> None:
        """Test partition with mixed entries."""
        staleness = {"123": True, "456": False, "789": True, "000": False}
        stale, current = partition_by_staleness(staleness)

        assert sorted(stale) == ["123", "789"]
        assert sorted(current) == ["000", "456"]

    def test_empty(self) -> None:
        """Test partition with empty input."""
        stale, current = partition_by_staleness({})

        assert stale == []
        assert current == []

    def test_single_stale(self) -> None:
        """Test partition with single stale entry."""
        staleness = {"123": True}
        stale, current = partition_by_staleness(staleness)

        assert stale == ["123"]
        assert current == []

    def test_single_current(self) -> None:
        """Test partition with single current entry."""
        staleness = {"123": False}
        stale, current = partition_by_staleness(staleness)

        assert stale == []
        assert current == ["123"]
