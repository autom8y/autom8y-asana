"""Unit tests for DynamicIndex components.

Per TDD-DYNAMIC-RESOLVER-001 / FR-003:
Tests for DynamicIndexKey, DynamicIndex, and DynamicIndexCache.

Coverage:
- Single column index
- Multi-column composite key
- Case-insensitive lookup
- Multi-match (same key, multiple GIDs)
- Empty DataFrame handling
- Missing column validation
- Cache hit/miss/eviction
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import polars as pl
import pytest

from autom8_asana.services.dynamic_index import (
    DynamicIndex,
    DynamicIndexCache,
    DynamicIndexKey,
    IndexCacheKey,
)


class TestDynamicIndexKey:
    """Tests for DynamicIndexKey."""

    def test_cache_key_format(self) -> None:
        """Cache key has versioned format with idx1 prefix."""
        key = DynamicIndexKey(
            columns=("office_phone", "vertical"),
            values=("+15551234567", "dental"),
        )

        assert key.cache_key == "idx1:office_phone=+15551234567:vertical=dental"

    def test_cache_key_single_column(self) -> None:
        """Cache key works with single column."""
        key = DynamicIndexKey(
            columns=("email",),
            values=("test@example.com",),
        )

        assert key.cache_key == "idx1:email=test@example.com"

    def test_cache_key_sorted_columns(self) -> None:
        """Cache key sorts columns for consistency."""
        key1 = DynamicIndexKey.from_criterion(
            {"vertical": "dental", "office_phone": "+15551234567"}
        )
        key2 = DynamicIndexKey.from_criterion(
            {"office_phone": "+15551234567", "vertical": "dental"}
        )

        # Both should produce same cache key regardless of input order
        assert key1.cache_key == key2.cache_key
        # Columns should be sorted alphabetically
        assert key1.columns == ("office_phone", "vertical")

    def test_from_criterion_normalizes_case(self) -> None:
        """from_criterion lowercases string values by default."""
        key = DynamicIndexKey.from_criterion({"email": "Test@EXAMPLE.com", "name": "John DOE"})

        assert key.values == ("test@example.com", "john doe")

    def test_from_criterion_no_normalize(self) -> None:
        """from_criterion preserves case when normalize=False."""
        key = DynamicIndexKey.from_criterion(
            {"email": "Test@EXAMPLE.com"},
            normalize=False,
        )

        assert key.values == ("Test@EXAMPLE.com",)

    def test_from_criterion_non_string_values(self) -> None:
        """from_criterion handles non-string values."""
        key = DynamicIndexKey.from_criterion({"count": 42, "active": True})

        # Non-strings are converted to string but not lowercased
        assert key.values == ("True", "42")

    def test_frozen_dataclass(self) -> None:
        """DynamicIndexKey is immutable (frozen)."""
        key = DynamicIndexKey(
            columns=("email",),
            values=("test@example.com",),
        )

        with pytest.raises(AttributeError):
            key.columns = ("other",)  # type: ignore[misc]


class TestDynamicIndex:
    """Tests for DynamicIndex."""

    def test_from_dataframe_single_column(self) -> None:
        """Build index from single column."""
        df = pl.DataFrame(
            {
                "email": ["a@test.com", "b@test.com"],
                "gid": ["123", "456"],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["email"])

        assert len(index) == 2
        assert index.lookup({"email": "a@test.com"}) == ["123"]
        assert index.lookup({"email": "b@test.com"}) == ["456"]

    def test_from_dataframe_multi_column(self) -> None:
        """Build index from multiple columns (composite key)."""
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567", "+15559876543", "+15551234567"],
                "vertical": ["dental", "medical", "chiropractic"],
                "gid": ["123", "456", "789"],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["office_phone", "vertical"])

        # Lookup with composite key
        result = index.lookup(
            {
                "office_phone": "+15551234567",
                "vertical": "dental",
            }
        )
        assert result == ["123"]

        # Different vertical, same phone
        result = index.lookup(
            {
                "office_phone": "+15551234567",
                "vertical": "chiropractic",
            }
        )
        assert result == ["789"]

    def test_case_insensitive_lookup(self) -> None:
        """Lookup is case-insensitive."""
        df = pl.DataFrame(
            {
                "vertical": ["Dental", "MEDICAL"],
                "gid": ["123", "456"],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["vertical"])

        # All case variations should work
        assert index.lookup({"vertical": "dental"}) == ["123"]
        assert index.lookup({"vertical": "DENTAL"}) == ["123"]
        assert index.lookup({"vertical": "Dental"}) == ["123"]
        assert index.lookup({"vertical": "medical"}) == ["456"]
        assert index.lookup({"vertical": "MEDICAL"}) == ["456"]

    def test_multi_match_returns_all_gids(self) -> None:
        """Multiple matches return all GIDs."""
        df = pl.DataFrame(
            {
                "email": ["same@test.com", "same@test.com", "other@test.com"],
                "gid": ["123", "456", "789"],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["email"])
        result = index.lookup({"email": "same@test.com"})

        # Should return both GIDs for same email
        assert sorted(result) == ["123", "456"]

    def test_lookup_not_found_returns_empty_list(self) -> None:
        """Lookup for non-existent key returns empty list."""
        df = pl.DataFrame(
            {
                "email": ["exists@test.com"],
                "gid": ["123"],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["email"])
        result = index.lookup({"email": "notfound@test.com"})

        assert result == []

    def test_lookup_single_returns_first(self) -> None:
        """lookup_single returns first match for backwards compatibility."""
        df = pl.DataFrame(
            {
                "email": ["same@test.com", "same@test.com"],
                "gid": ["123", "456"],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["email"])

        # lookup_single returns first (order may vary based on DataFrame order)
        result = index.lookup_single({"email": "same@test.com"})
        assert result in ["123", "456"]

    def test_lookup_single_not_found_returns_none(self) -> None:
        """lookup_single returns None when not found."""
        df = pl.DataFrame(
            {
                "email": ["exists@test.com"],
                "gid": ["123"],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["email"])
        result = index.lookup_single({"email": "notfound@test.com"})

        assert result is None

    def test_contains_returns_boolean(self) -> None:
        """contains() returns True/False for existence check."""
        df = pl.DataFrame(
            {
                "email": ["exists@test.com"],
                "gid": ["123"],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["email"])

        assert index.contains({"email": "exists@test.com"}) is True
        assert index.contains({"email": "notfound@test.com"}) is False

    def test_available_columns_returns_key_columns(self) -> None:
        """available_columns() returns the indexed columns."""
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567"],
                "vertical": ["dental"],
                "gid": ["123"],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["office_phone", "vertical"])

        # Columns are sorted
        assert index.available_columns() == ["office_phone", "vertical"]

    def test_empty_dataframe_creates_empty_index(self) -> None:
        """Empty DataFrame creates valid but empty index."""
        df = pl.DataFrame(
            {
                "email": [],
                "gid": [],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["email"])

        assert len(index) == 0
        assert index.lookup({"email": "any@test.com"}) == []

    def test_null_values_filtered_out(self) -> None:
        """Rows with null key or value columns are filtered out."""
        df = pl.DataFrame(
            {
                "email": ["a@test.com", None, "c@test.com", "d@test.com"],
                "gid": ["123", "456", None, "789"],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["email"])

        # Only "a@test.com" -> "123" and "d@test.com" -> "789" should be indexed
        assert len(index) == 2
        assert index.lookup({"email": "a@test.com"}) == ["123"]
        assert index.lookup({"email": "d@test.com"}) == ["789"]
        # c@test.com has null gid, should not be indexed
        assert index.lookup({"email": "c@test.com"}) == []

    def test_missing_key_column_raises_keyerror(self) -> None:
        """Missing key columns raise KeyError with helpful message."""
        df = pl.DataFrame(
            {
                "email": ["a@test.com"],
                "gid": ["123"],
            }
        )

        with pytest.raises(KeyError, match="Missing required columns"):
            DynamicIndex.from_dataframe(df, ["nonexistent_column"])

    def test_missing_value_column_raises_keyerror(self) -> None:
        """Missing value column raises KeyError."""
        df = pl.DataFrame(
            {
                "email": ["a@test.com"],
                "id": ["123"],  # Not "gid"
            }
        )

        with pytest.raises(KeyError, match="Missing required columns"):
            DynamicIndex.from_dataframe(df, ["email"], value_column="gid")

    def test_custom_value_column(self) -> None:
        """Can specify custom value column name."""
        df = pl.DataFrame(
            {
                "email": ["a@test.com"],
                "entity_id": ["123"],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["email"], value_column="entity_id")

        assert index.lookup({"email": "a@test.com"}) == ["123"]
        assert index.value_column == "entity_id"

    def test_entry_count_property(self) -> None:
        """entry_count returns number of unique keys."""
        df = pl.DataFrame(
            {
                "email": ["a@test.com", "a@test.com", "b@test.com"],
                "gid": ["123", "456", "789"],
            }
        )

        index = DynamicIndex.from_dataframe(df, ["email"])

        # Two unique emails
        assert index.entry_count == 2
        assert len(index) == 2

    def test_created_at_timestamp(self) -> None:
        """Index has created_at timestamp."""
        df = pl.DataFrame(
            {
                "email": ["a@test.com"],
                "gid": ["123"],
            }
        )

        before = datetime.now(UTC)
        index = DynamicIndex.from_dataframe(df, ["email"])
        after = datetime.now(UTC)

        assert before <= index.created_at <= after


class TestIndexCacheKey:
    """Tests for IndexCacheKey."""

    def test_equality_independent_of_column_order(self) -> None:
        """IndexCacheKey equality ignores column order (uses frozenset)."""
        key1 = IndexCacheKey(
            entity_type="unit",
            columns=frozenset(["a", "b", "c"]),
        )
        key2 = IndexCacheKey(
            entity_type="unit",
            columns=frozenset(["c", "b", "a"]),
        )

        assert key1 == key2
        assert hash(key1) == hash(key2)

    def test_different_entity_types_not_equal(self) -> None:
        """Different entity types produce different keys."""
        key1 = IndexCacheKey(
            entity_type="unit",
            columns=frozenset(["email"]),
        )
        key2 = IndexCacheKey(
            entity_type="contact",
            columns=frozenset(["email"]),
        )

        assert key1 != key2


class TestDynamicIndexCache:
    """Tests for DynamicIndexCache."""

    def _make_index(
        self,
        key_columns: list[str] | None = None,
        data: dict | None = None,
    ) -> DynamicIndex:
        """Helper to create a test index."""
        if data is None:
            data = {"col": ["a"], "gid": ["123"]}
        if key_columns is None:
            key_columns = ["col"]

        df = pl.DataFrame(data)
        return DynamicIndex.from_dataframe(df, key_columns)

    def test_cache_miss_returns_none(self) -> None:
        """Cache miss returns None and increments miss counter."""
        cache = DynamicIndexCache()

        result = cache.get("unit", ["email"])

        assert result is None
        assert cache.get_stats()["misses"] == 1

    def test_cache_hit_returns_index(self) -> None:
        """Cache hit returns stored index and increments hit counter."""
        cache = DynamicIndexCache()
        index = self._make_index()

        cache.put("unit", ["col"], index)
        result = cache.get("unit", ["col"])

        assert result is index
        assert cache.get_stats()["hits"] == 1

    def test_cache_column_order_independence(self) -> None:
        """Cache lookup ignores column order."""
        cache = DynamicIndexCache()
        index = self._make_index(["a", "b"], {"a": ["x"], "b": ["y"], "gid": ["123"]})

        # Put with one order
        cache.put("unit", ["a", "b"], index)

        # Get with different order
        result = cache.get("unit", ["b", "a"])

        assert result is index

    def test_lru_eviction_at_capacity(self) -> None:
        """LRU eviction when entity exceeds max_per_entity."""
        cache = DynamicIndexCache(max_per_entity=2)

        # Add 3 indexes for same entity
        for i in range(3):
            data = {f"col{i}": ["a"], "gid": ["123"]}
            index = self._make_index([f"col{i}"], data)
            cache.put("unit", [f"col{i}"], index)

        # First should be evicted (LRU)
        assert cache.get("unit", ["col0"]) is None
        assert cache.get("unit", ["col1"]) is not None
        assert cache.get("unit", ["col2"]) is not None

        stats = cache.get_stats()
        assert stats["evictions_lru"] == 1

    def test_lru_access_updates_order(self) -> None:
        """Accessing cache entry moves it to end of LRU."""
        cache = DynamicIndexCache(max_per_entity=2)

        # Add col0 and col1
        for i in range(2):
            data = {f"col{i}": ["a"], "gid": ["123"]}
            index = self._make_index([f"col{i}"], data)
            cache.put("unit", [f"col{i}"], index)

        # Access col0 (moves it to end)
        cache.get("unit", ["col0"])

        # Add col2 - should evict col1 (now LRU), not col0
        data = {"col2": ["a"], "gid": ["123"]}
        index = self._make_index(["col2"], data)
        cache.put("unit", ["col2"], index)

        # col0 should still be present (was accessed recently)
        assert cache.get("unit", ["col0"]) is not None
        # col1 should be evicted
        assert cache.get("unit", ["col1"]) is None

    def test_ttl_expiration(self) -> None:
        """Expired entries are evicted on access."""
        cache = DynamicIndexCache(ttl_seconds=60)
        index = self._make_index()

        cache.put("unit", ["col"], index)

        # Mock time to be past TTL
        expired_time = datetime.now(UTC) + timedelta(seconds=61)
        with patch("autom8_asana.services.dynamic_index.datetime") as mock_datetime:
            mock_datetime.now.return_value = expired_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = cache.get("unit", ["col"])

        assert result is None
        assert cache.get_stats()["evictions_ttl"] == 1

    def test_invalidate_all(self) -> None:
        """invalidate() with no args clears entire cache."""
        cache = DynamicIndexCache()

        # Add entries for multiple entities
        for entity in ["unit", "contact"]:
            for i in range(2):
                data = {f"col{i}": ["a"], "gid": ["123"]}
                index = self._make_index([f"col{i}"], data)
                cache.put(entity, [f"col{i}"], index)

        count = cache.invalidate()

        assert count == 4
        assert cache.get_stats()["total_entries"] == 0

    def test_invalidate_by_entity_type(self) -> None:
        """invalidate(entity_type) clears only that entity."""
        cache = DynamicIndexCache()

        # Add entries for multiple entities
        for entity in ["unit", "contact"]:
            index = self._make_index()
            cache.put(entity, ["col"], index)

        count = cache.invalidate(entity_type="unit")

        assert count == 1
        assert cache.get("unit", ["col"]) is None
        assert cache.get("contact", ["col"]) is not None

    def test_invalidate_specific_entry(self) -> None:
        """invalidate(entity_type, key_columns) clears specific entry."""
        cache = DynamicIndexCache()

        # Add multiple indexes for same entity
        for i in range(2):
            data = {f"col{i}": ["a"], "gid": ["123"]}
            index = self._make_index([f"col{i}"], data)
            cache.put("unit", [f"col{i}"], index)

        count = cache.invalidate(entity_type="unit", key_columns=["col0"])

        assert count == 1
        assert cache.get("unit", ["col0"]) is None
        assert cache.get("unit", ["col1"]) is not None

    def test_invalidate_nonexistent_returns_zero(self) -> None:
        """Invalidating non-existent entry returns 0."""
        cache = DynamicIndexCache()

        count = cache.invalidate(entity_type="nonexistent", key_columns=["col"])

        assert count == 0

    def test_get_or_build_cache_hit(self) -> None:
        """get_or_build returns cached index on hit."""
        cache = DynamicIndexCache()
        df = pl.DataFrame({"email": ["a@test.com"], "gid": ["123"]})

        # First call builds and caches
        index1 = cache.get_or_build("unit", ["email"], df)

        # Second call returns cached
        index2 = cache.get_or_build("unit", ["email"], df)

        assert index1 is index2
        assert cache.get_stats()["hits"] == 1
        assert cache.get_stats()["misses"] == 1

    def test_get_or_build_cache_miss(self) -> None:
        """get_or_build builds new index on miss."""
        cache = DynamicIndexCache()
        df = pl.DataFrame({"email": ["a@test.com"], "gid": ["123"]})

        index = cache.get_or_build("unit", ["email"], df)

        assert index.lookup({"email": "a@test.com"}) == ["123"]
        assert cache.get_stats()["misses"] == 1

    def test_get_stats(self) -> None:
        """get_stats returns comprehensive statistics."""
        cache = DynamicIndexCache()
        index = self._make_index()

        cache.put("unit", ["col"], index)
        cache.get("unit", ["col"])  # Hit
        cache.get("unit", ["other"])  # Miss

        stats = cache.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_entries"] == 1
        assert stats["entity_types"] == 1

    def test_thread_safety_lock(self) -> None:
        """Cache operations are thread-safe via RLock."""
        cache = DynamicIndexCache()

        # Verify lock exists and has RLock methods (acquire, release, etc.)
        # Note: threading.RLock is a factory function, not a type, so we check
        # for the presence of RLock-specific methods
        assert hasattr(cache._lock, "acquire")
        assert hasattr(cache._lock, "release")
        assert hasattr(cache._lock, "_is_owned")  # RLock-specific attribute

    def test_put_replaces_existing(self) -> None:
        """Putting same key replaces existing entry."""
        cache = DynamicIndexCache()

        index1 = self._make_index(data={"col": ["a"], "gid": ["111"]})
        index2 = self._make_index(data={"col": ["b"], "gid": ["222"]})

        cache.put("unit", ["col"], index1)
        cache.put("unit", ["col"], index2)

        result = cache.get("unit", ["col"])

        assert result is index2
        assert cache.get_stats()["total_entries"] == 1

    def test_separate_entity_counts(self) -> None:
        """Different entity types have separate eviction limits."""
        cache = DynamicIndexCache(max_per_entity=2)

        # Add 2 indexes each for unit and contact
        for entity in ["unit", "contact"]:
            for i in range(2):
                data = {f"col{i}": ["a"], "gid": ["123"]}
                index = self._make_index([f"col{i}"], data)
                cache.put(entity, [f"col{i}"], index)

        # All 4 should be present (2 per entity, within limit)
        assert cache.get("unit", ["col0"]) is not None
        assert cache.get("unit", ["col1"]) is not None
        assert cache.get("contact", ["col0"]) is not None
        assert cache.get("contact", ["col1"]) is not None
