"""Unit tests for MemoryTier.

Per TDD-DATAFRAME-CACHE-001: Tests for LRU eviction, heap-based limits,
and thread-safe access.
"""

from datetime import datetime, timedelta, timezone

import polars as pl

from autom8_asana.cache.dataframe_cache import CacheEntry
from autom8_asana.cache.dataframe.tiers.memory import MemoryTier


def make_entry(project_gid: str, rows: int = 10) -> CacheEntry:
    """Create a test CacheEntry."""
    df = pl.DataFrame({
        "gid": [f"gid-{i}" for i in range(rows)],
        "name": [f"name-{i}" for i in range(rows)],
    })

    return CacheEntry(
        project_gid=project_gid,
        entity_type="unit",
        dataframe=df,
        watermark=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        schema_version="1.0.0",
    )


class TestMemoryTier:
    """Tests for MemoryTier."""

    def test_put_and_get(self) -> None:
        """Basic put and get operations."""
        tier = MemoryTier(max_entries=10)
        entry = make_entry("proj-1")

        tier.put("key-1", entry)
        result = tier.get("key-1")

        assert result is not None
        assert result.project_gid == "proj-1"

    def test_get_nonexistent(self) -> None:
        """Get returns None for nonexistent key."""
        tier = MemoryTier(max_entries=10)

        result = tier.get("nonexistent")

        assert result is None

    def test_put_overwrites_existing(self) -> None:
        """Put overwrites existing entry with same key."""
        tier = MemoryTier(max_entries=10)

        tier.put("key-1", make_entry("proj-1"))
        tier.put("key-1", make_entry("proj-2"))

        result = tier.get("key-1")
        assert result is not None
        assert result.project_gid == "proj-2"

    def test_lru_eviction(self) -> None:
        """LRU eviction when at max_entries capacity."""
        tier = MemoryTier(max_entries=2)

        tier.put("key-1", make_entry("proj-1"))
        tier.put("key-2", make_entry("proj-2"))
        tier.get("key-1")  # Access key-1, making key-2 LRU
        tier.put("key-3", make_entry("proj-3"))

        assert tier.get("key-1") is not None
        assert tier.get("key-2") is None  # Evicted
        assert tier.get("key-3") is not None

    def test_lru_order_on_get(self) -> None:
        """Get moves entry to end of LRU list."""
        tier = MemoryTier(max_entries=3)

        tier.put("key-1", make_entry("proj-1"))
        tier.put("key-2", make_entry("proj-2"))
        tier.put("key-3", make_entry("proj-3"))

        # Access key-1, making it most recently used
        tier.get("key-1")

        # Add key-4 to trigger eviction
        tier.put("key-4", make_entry("proj-4"))

        # key-2 should be evicted (was least recently used)
        assert tier.get("key-1") is not None
        assert tier.get("key-2") is None
        assert tier.get("key-3") is not None
        assert tier.get("key-4") is not None

    def test_remove(self) -> None:
        """Remove deletes entry and returns True."""
        tier = MemoryTier(max_entries=10)

        tier.put("key-1", make_entry("proj-1"))
        result = tier.remove("key-1")

        assert result is True
        assert tier.get("key-1") is None

    def test_remove_nonexistent(self) -> None:
        """Remove returns False for nonexistent key."""
        tier = MemoryTier(max_entries=10)

        result = tier.remove("nonexistent")

        assert result is False

    def test_clear(self) -> None:
        """Clear removes all entries."""
        tier = MemoryTier(max_entries=10)

        tier.put("key-1", make_entry("proj-1"))
        tier.put("key-2", make_entry("proj-2"))
        tier.clear()

        assert tier.get("key-1") is None
        assert tier.get("key-2") is None
        assert len(tier) == 0

    def test_len(self) -> None:
        """Len returns number of entries."""
        tier = MemoryTier(max_entries=10)

        assert len(tier) == 0

        tier.put("key-1", make_entry("proj-1"))
        assert len(tier) == 1

        tier.put("key-2", make_entry("proj-2"))
        assert len(tier) == 2

        tier.remove("key-1")
        assert len(tier) == 1

    def test_evict_stale(self) -> None:
        """Evict stale removes entries older than max_age_seconds."""
        tier = MemoryTier(max_entries=10)

        # Create old entry
        old_df = pl.DataFrame({"gid": ["1"]})
        old_entry = CacheEntry(
            project_gid="proj-old",
            entity_type="unit",
            dataframe=old_df,
            watermark=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            schema_version="1.0.0",
        )

        # Create fresh entry
        fresh_entry = make_entry("proj-fresh")

        tier.put("old", old_entry)
        tier.put("fresh", fresh_entry)

        evicted = tier.evict_stale(max_age_seconds=3600)

        assert evicted == 1
        assert tier.get("old") is None
        assert tier.get("fresh") is not None

    def test_stats(self) -> None:
        """Stats track operations correctly."""
        tier = MemoryTier(max_entries=10)

        tier.put("key-1", make_entry("proj-1"))
        tier.put("key-2", make_entry("proj-2"))
        tier.get("key-1")
        tier.get("nonexistent")

        stats = tier.get_stats()

        assert stats["puts"] == 2
        assert stats["gets"] == 2
        assert stats["entry_count"] == 2
        assert stats["current_bytes"] > 0
