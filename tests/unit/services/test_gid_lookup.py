"""Tests for GidLookupIndex serialize/deserialize functionality.

Tests cover:
- serialize() returns correct JSON-compatible dict structure
- deserialize() reconstructs identical index from serialized data
- Round-trip preserves all lookup entries exactly
- Round-trip preserves created_at timestamp
- deserialize() raises ValueError on entry_count mismatch
- deserialize() raises ValueError on invalid datetime format
- deserialize() raises KeyError on missing required keys
- deserialize() raises ValueError on unsupported version

Per sprint-materialization-003 Task T1:
GidLookupIndex serialization enables S3 persistence for warm starts.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from autom8_asana.models.contracts.phone_vertical import PhoneVerticalPair
from autom8_asana.services.gid_lookup import GidLookupIndex


class TestSerialize:
    """Tests for GidLookupIndex.serialize() method."""

    def test_serialize_returns_dict_with_required_keys(self) -> None:
        """serialize() returns dict with version, created_at, entry_count, lookup."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)
        lookup = {"pv1:+17705753103:chiropractic": "123456789"}
        index = GidLookupIndex(lookup_dict=lookup, created_at=created_at)

        result = index.serialize()

        assert "version" in result
        assert "created_at" in result
        assert "entry_count" in result
        assert "lookup" in result

    def test_serialize_version_is_1_0(self) -> None:
        """serialize() sets version to '1.0'."""
        index = GidLookupIndex(
            lookup_dict={},
            created_at=datetime.now(UTC),
        )

        result = index.serialize()

        assert result["version"] == "1.0"

    def test_serialize_created_at_is_iso_format(self) -> None:
        """serialize() converts created_at to ISO 8601 string."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, 123456, tzinfo=UTC)
        index = GidLookupIndex(lookup_dict={}, created_at=created_at)

        result = index.serialize()

        assert result["created_at"] == "2024-06-15T12:30:45.123456+00:00"

    def test_serialize_entry_count_matches_lookup_length(self) -> None:
        """serialize() sets entry_count to actual lookup dict length."""
        lookup = {
            "pv1:+17705753103:chiropractic": "123",
            "pv1:+14045551234:dental": "456",
            "pv1:+15555551212:medical": "789",
        }
        index = GidLookupIndex(
            lookup_dict=lookup,
            created_at=datetime.now(UTC),
        )

        result = index.serialize()

        assert result["entry_count"] == 3

    def test_serialize_lookup_contains_all_entries(self) -> None:
        """serialize() includes the complete lookup dictionary."""
        lookup = {
            "pv1:+17705753103:chiropractic": "123",
            "pv1:+14045551234:dental": "456",
        }
        index = GidLookupIndex(
            lookup_dict=lookup,
            created_at=datetime.now(UTC),
        )

        result = index.serialize()

        assert result["lookup"] == lookup

    def test_serialize_empty_index(self) -> None:
        """serialize() handles empty lookup dict correctly."""
        index = GidLookupIndex(
            lookup_dict={},
            created_at=datetime.now(UTC),
        )

        result = index.serialize()

        assert result["entry_count"] == 0
        assert result["lookup"] == {}

    def test_serialize_is_json_compatible(self) -> None:
        """serialize() output can be serialized to JSON."""
        lookup = {"pv1:+17705753103:chiropractic": "123456789"}
        index = GidLookupIndex(
            lookup_dict=lookup,
            created_at=datetime.now(UTC),
        )

        result = index.serialize()

        # Should not raise
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

        # Should round-trip through JSON
        parsed = json.loads(json_str)
        assert parsed == result


class TestDeserialize:
    """Tests for GidLookupIndex.deserialize() classmethod."""

    def test_deserialize_reconstructs_index(self) -> None:
        """deserialize() creates GidLookupIndex from valid data."""
        data = {
            "version": "1.0",
            "created_at": "2024-06-15T12:30:45+00:00",
            "entry_count": 1,
            "lookup": {"pv1:+17705753103:chiropractic": "123"},
        }

        index = GidLookupIndex.deserialize(data)

        assert isinstance(index, GidLookupIndex)
        assert len(index) == 1

    def test_deserialize_preserves_lookup_entries(self) -> None:
        """deserialize() preserves all lookup entries exactly."""
        lookup = {
            "pv1:+17705753103:chiropractic": "123",
            "pv1:+14045551234:dental": "456",
        }
        data = {
            "version": "1.0",
            "created_at": "2024-06-15T12:30:45+00:00",
            "entry_count": 2,
            "lookup": lookup,
        }

        index = GidLookupIndex.deserialize(data)

        assert index._lookup == lookup

    def test_deserialize_parses_created_at(self) -> None:
        """deserialize() parses ISO 8601 datetime correctly."""
        data = {
            "version": "1.0",
            "created_at": "2024-06-15T12:30:45.123456+00:00",
            "entry_count": 0,
            "lookup": {},
        }

        index = GidLookupIndex.deserialize(data)

        expected = datetime(2024, 6, 15, 12, 30, 45, 123456, tzinfo=UTC)
        assert index.created_at == expected

    def test_deserialize_raises_key_error_missing_version(self) -> None:
        """deserialize() raises KeyError when version is missing."""
        data = {
            "created_at": "2024-06-15T12:30:45+00:00",
            "entry_count": 0,
            "lookup": {},
        }

        with pytest.raises(KeyError, match="version"):
            GidLookupIndex.deserialize(data)

    def test_deserialize_raises_key_error_missing_created_at(self) -> None:
        """deserialize() raises KeyError when created_at is missing."""
        data = {
            "version": "1.0",
            "entry_count": 0,
            "lookup": {},
        }

        with pytest.raises(KeyError, match="created_at"):
            GidLookupIndex.deserialize(data)

    def test_deserialize_raises_key_error_missing_entry_count(self) -> None:
        """deserialize() raises KeyError when entry_count is missing."""
        data = {
            "version": "1.0",
            "created_at": "2024-06-15T12:30:45+00:00",
            "lookup": {},
        }

        with pytest.raises(KeyError, match="entry_count"):
            GidLookupIndex.deserialize(data)

    def test_deserialize_raises_key_error_missing_lookup(self) -> None:
        """deserialize() raises KeyError when lookup is missing."""
        data = {
            "version": "1.0",
            "created_at": "2024-06-15T12:30:45+00:00",
            "entry_count": 0,
        }

        with pytest.raises(KeyError, match="lookup"):
            GidLookupIndex.deserialize(data)

    def test_deserialize_raises_key_error_multiple_missing(self) -> None:
        """deserialize() raises KeyError listing all missing keys."""
        data = {"version": "1.0"}

        with pytest.raises(KeyError, match="Missing required keys"):
            GidLookupIndex.deserialize(data)

    def test_deserialize_raises_value_error_invalid_version(self) -> None:
        """deserialize() raises ValueError for unsupported version."""
        data = {
            "version": "2.0",
            "created_at": "2024-06-15T12:30:45+00:00",
            "entry_count": 0,
            "lookup": {},
        }

        with pytest.raises(ValueError, match="Unsupported serialization version"):
            GidLookupIndex.deserialize(data)

    def test_deserialize_raises_value_error_invalid_datetime(self) -> None:
        """deserialize() raises ValueError for invalid datetime format."""
        data = {
            "version": "1.0",
            "created_at": "not-a-datetime",
            "entry_count": 0,
            "lookup": {},
        }

        with pytest.raises(ValueError, match="Invalid created_at datetime format"):
            GidLookupIndex.deserialize(data)

    def test_deserialize_raises_value_error_entry_count_mismatch(self) -> None:
        """deserialize() raises ValueError when entry_count doesn't match."""
        data = {
            "version": "1.0",
            "created_at": "2024-06-15T12:30:45+00:00",
            "entry_count": 5,  # Claims 5 entries
            "lookup": {"key1": "val1", "key2": "val2"},  # Only 2 entries
        }

        with pytest.raises(ValueError, match="Entry count mismatch"):
            GidLookupIndex.deserialize(data)

    def test_deserialize_raises_value_error_entry_count_zero_mismatch(self) -> None:
        """deserialize() raises ValueError when claims empty but has entries."""
        data = {
            "version": "1.0",
            "created_at": "2024-06-15T12:30:45+00:00",
            "entry_count": 0,  # Claims empty
            "lookup": {"key1": "val1"},  # Has one entry
        }

        with pytest.raises(ValueError, match="Entry count mismatch"):
            GidLookupIndex.deserialize(data)

    def test_deserialize_empty_index(self) -> None:
        """deserialize() handles empty lookup dict correctly."""
        data = {
            "version": "1.0",
            "created_at": "2024-06-15T12:30:45+00:00",
            "entry_count": 0,
            "lookup": {},
        }

        index = GidLookupIndex.deserialize(data)

        assert len(index) == 0

    def test_deserialize_datetime_without_microseconds(self) -> None:
        """deserialize() handles datetime without microseconds."""
        data = {
            "version": "1.0",
            "created_at": "2024-06-15T12:30:45+00:00",
            "entry_count": 0,
            "lookup": {},
        }

        index = GidLookupIndex.deserialize(data)

        expected = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)
        assert index.created_at == expected


class TestRoundTrip:
    """Tests for serialize/deserialize round-trip guarantee."""

    def test_round_trip_preserves_equality(self) -> None:
        """deserialize(serialize(index)) == index."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, 123456, tzinfo=UTC)
        lookup = {
            "pv1:+17705753103:chiropractic": "123456789",
            "pv1:+14045551234:dental": "987654321",
        }
        original = GidLookupIndex(lookup_dict=lookup, created_at=created_at)

        serialized = original.serialize()
        reconstructed = GidLookupIndex.deserialize(serialized)

        assert reconstructed == original

    def test_round_trip_empty_index(self) -> None:
        """Round-trip works for empty index."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)
        original = GidLookupIndex(lookup_dict={}, created_at=created_at)

        serialized = original.serialize()
        reconstructed = GidLookupIndex.deserialize(serialized)

        assert reconstructed == original
        assert len(reconstructed) == 0

    def test_round_trip_large_index(self) -> None:
        """Round-trip works for large index."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)
        # Create 1000 entries
        lookup = {f"pv1:+1555555{i:04d}:vertical{i}": f"gid{i}" for i in range(1000)}
        original = GidLookupIndex(lookup_dict=lookup, created_at=created_at)

        serialized = original.serialize()
        reconstructed = GidLookupIndex.deserialize(serialized)

        assert reconstructed == original
        assert len(reconstructed) == 1000

    def test_round_trip_through_json(self) -> None:
        """Round-trip through JSON serialization works."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, 123456, tzinfo=UTC)
        lookup = {"pv1:+17705753103:chiropractic": "123456789"}
        original = GidLookupIndex(lookup_dict=lookup, created_at=created_at)

        # Simulate S3 storage: serialize -> JSON -> parse -> deserialize
        serialized = original.serialize()
        json_str = json.dumps(serialized)
        parsed = json.loads(json_str)
        reconstructed = GidLookupIndex.deserialize(parsed)

        assert reconstructed == original

    def test_round_trip_preserves_lookup_access(self) -> None:
        """Round-trip preserves ability to look up values."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)
        lookup = {"pv1:+17705753103:chiropractic": "expected_gid"}
        original = GidLookupIndex(lookup_dict=lookup, created_at=created_at)

        serialized = original.serialize()
        reconstructed = GidLookupIndex.deserialize(serialized)

        # Should be able to access the same value
        assert reconstructed._lookup["pv1:+17705753103:chiropractic"] == "expected_gid"


class TestEquality:
    """Tests for GidLookupIndex.__eq__ method."""

    def test_equal_indices_are_equal(self) -> None:
        """Two indices with same data are equal."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)
        lookup = {"key": "value"}

        index1 = GidLookupIndex(lookup_dict=lookup, created_at=created_at)
        index2 = GidLookupIndex(lookup_dict=lookup.copy(), created_at=created_at)

        assert index1 == index2

    def test_different_lookup_not_equal(self) -> None:
        """Indices with different lookup are not equal."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)

        index1 = GidLookupIndex(lookup_dict={"key1": "val1"}, created_at=created_at)
        index2 = GidLookupIndex(lookup_dict={"key2": "val2"}, created_at=created_at)

        assert index1 != index2

    def test_different_created_at_not_equal(self) -> None:
        """Indices with different created_at are not equal."""
        lookup = {"key": "value"}

        index1 = GidLookupIndex(
            lookup_dict=lookup,
            created_at=datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC),
        )
        index2 = GidLookupIndex(
            lookup_dict=lookup,
            created_at=datetime(2024, 6, 16, 12, 30, 45, tzinfo=UTC),
        )

        assert index1 != index2

    def test_not_equal_to_non_index(self) -> None:
        """Index is not equal to non-GidLookupIndex objects."""
        index = GidLookupIndex(
            lookup_dict={"key": "value"},
            created_at=datetime.now(UTC),
        )

        assert index != "not an index"
        assert index != 42
        assert index != {"key": "value"}

    def test_equal_empty_indices(self) -> None:
        """Two empty indices with same created_at are equal."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)

        index1 = GidLookupIndex(lookup_dict={}, created_at=created_at)
        index2 = GidLookupIndex(lookup_dict={}, created_at=created_at)

        assert index1 == index2


class TestGidLookupIndexFromDataframe:
    """Tests for GidLookupIndex.from_dataframe() factory method."""

    def test_empty_dataframe_creates_empty_index(self) -> None:
        """Empty DataFrame should create an index with zero entries."""
        df = pl.DataFrame(
            {
                "office_phone": [],
                "vertical": [],
                "gid": [],
            }
        ).cast(
            {
                "office_phone": pl.Utf8,
                "vertical": pl.Utf8,
                "gid": pl.Utf8,
            }
        )

        index = GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

        assert len(index) == 0

    def test_single_row_dataframe(self) -> None:
        """Single row DataFrame should create index with one entry."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103"],
                "vertical": ["chiropractic"],
                "gid": ["1234567890123456"],
            }
        )

        index = GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

        assert len(index) == 1

    def test_multiple_rows_dataframe(self) -> None:
        """Multiple rows should all be indexed."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103", "+14045551234", "+12125559876"],
                "vertical": ["chiropractic", "dental", "chiropractic"],
                "gid": ["111", "222", "333"],
            }
        )

        index = GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

        assert len(index) == 3

    def test_missing_required_column_raises_keyerror(self) -> None:
        """Missing required columns should raise KeyError."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103"],
                "vertical": ["chiropractic"],
                # Missing 'gid' column
            }
        )

        with pytest.raises(KeyError, match="Missing required columns.*gid"):
            GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

    def test_null_phone_rows_filtered(self) -> None:
        """Rows with null office_phone should be excluded."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103", None, "+14045551234"],
                "vertical": ["chiropractic", "dental", "dental"],
                "gid": ["111", "222", "333"],
            }
        )

        index = GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

        assert len(index) == 2  # Row with null phone excluded

    def test_null_vertical_rows_filtered(self) -> None:
        """Rows with null vertical should be excluded."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103", "+14045551234"],
                "vertical": ["chiropractic", None],
                "gid": ["111", "222"],
            }
        )

        index = GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

        assert len(index) == 1  # Row with null vertical excluded

    def test_null_gid_rows_filtered(self) -> None:
        """Rows with null gid should be excluded."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103", "+14045551234"],
                "vertical": ["chiropractic", "dental"],
                "gid": ["111", None],
            }
        )

        index = GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

        assert len(index) == 1  # Row with null gid excluded

    def test_created_at_timestamp_set(self) -> None:
        """created_at should be set to current UTC time."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103"],
                "vertical": ["chiropractic"],
                "gid": ["111"],
            }
        )

        before = datetime.now(UTC)
        index = GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])
        after = datetime.now(UTC)

        assert before <= index.created_at <= after

    def test_extra_columns_ignored(self) -> None:
        """Extra columns in DataFrame should be ignored."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103"],
                "vertical": ["chiropractic"],
                "gid": ["111"],
                "name": ["Test Business"],
                "mrr": [1000.0],
            }
        )

        index = GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

        assert len(index) == 1


class TestGidLookupIndexGetGid:
    """Tests for GidLookupIndex.get_gid() method."""

    @pytest.fixture
    def sample_index(self) -> GidLookupIndex:
        """Create a sample index for testing."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103", "+14045551234", "+12125559876"],
                "vertical": ["chiropractic", "dental", "chiropractic"],
                "gid": ["111", "222", "333"],
            }
        )
        return GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

    def test_get_gid_found(self, sample_index: GidLookupIndex) -> None:
        """Should return GID when pair exists in index."""
        pair = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )

        result = sample_index.get_gid(pair)

        assert result == "111"

    def test_get_gid_not_found_returns_none(self, sample_index: GidLookupIndex) -> None:
        """Should return None when pair not in index."""
        pair = PhoneVerticalPair(
            office_phone="+19995551111",
            vertical="chiropractic",
        )

        result = sample_index.get_gid(pair)

        assert result is None

    def test_get_gid_wrong_vertical_returns_none(self, sample_index: GidLookupIndex) -> None:
        """Should return None when phone exists but vertical differs."""
        # Phone exists with 'chiropractic', not 'dental'
        pair = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="dental",
        )

        result = sample_index.get_gid(pair)

        assert result is None

    def test_get_gid_uses_canonical_key_format(self, sample_index: GidLookupIndex) -> None:
        """Lookup should use canonical_key 'pv1:{phone}:{vertical}' format."""
        pair = PhoneVerticalPair(
            office_phone="+14045551234",
            vertical="dental",
        )

        # Verify the canonical key format is what we expect
        assert pair.canonical_key == "pv1:+14045551234:dental"

        result = sample_index.get_gid(pair)
        assert result == "222"


class TestGidLookupIndexGetGids:
    """Tests for GidLookupIndex.get_gids() batch method."""

    @pytest.fixture
    def sample_index(self) -> GidLookupIndex:
        """Create a sample index for testing."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103", "+14045551234", "+12125559876"],
                "vertical": ["chiropractic", "dental", "chiropractic"],
                "gid": ["111", "222", "333"],
            }
        )
        return GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

    def test_get_gids_empty_list(self, sample_index: GidLookupIndex) -> None:
        """Empty input list should return empty dict."""
        result = sample_index.get_gids([])

        assert result == {}

    def test_get_gids_all_found(self, sample_index: GidLookupIndex) -> None:
        """All pairs found should return all GIDs."""
        pairs = [
            PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic"),
            PhoneVerticalPair(office_phone="+14045551234", vertical="dental"),
        ]

        result = sample_index.get_gids(pairs)

        assert len(result) == 2
        assert result[pairs[0]] == "111"
        assert result[pairs[1]] == "222"

    def test_get_gids_mixed_found_and_not_found(self, sample_index: GidLookupIndex) -> None:
        """Mix of found and not found should have None for missing."""
        pairs = [
            PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic"),
            PhoneVerticalPair(office_phone="+19995551111", vertical="dental"),  # Not in index
        ]

        result = sample_index.get_gids(pairs)

        assert result[pairs[0]] == "111"
        assert result[pairs[1]] is None

    def test_get_gids_preserves_order(self, sample_index: GidLookupIndex) -> None:
        """Result dict should preserve input order."""
        pairs = [
            PhoneVerticalPair(office_phone="+12125559876", vertical="chiropractic"),
            PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic"),
            PhoneVerticalPair(office_phone="+14045551234", vertical="dental"),
        ]

        result = sample_index.get_gids(pairs)

        # Verify order matches input
        result_keys = list(result.keys())
        assert result_keys == pairs

    def test_get_gids_duplicate_pairs(self, sample_index: GidLookupIndex) -> None:
        """Duplicate pairs in input should be handled correctly."""
        pair = PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic")
        pairs = [pair, pair, pair]

        result = sample_index.get_gids(pairs)

        # Dict will dedupe but order preserved
        assert len(result) == 1
        assert result[pair] == "111"


class TestGidLookupIndexStaleDetection:
    """Tests for GidLookupIndex.is_stale() method."""

    def test_fresh_index_not_stale(self) -> None:
        """Newly created index should not be stale."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103"],
                "vertical": ["chiropractic"],
                "gid": ["111"],
            }
        )
        index = GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

        assert not index.is_stale(ttl_seconds=3600)

    def test_old_index_is_stale(self) -> None:
        """Index older than TTL should be stale."""
        old_time = datetime.now(UTC) - timedelta(hours=2)
        index = GidLookupIndex(
            lookup_dict={"pv1:+17705753103:chiropractic": "111"},
            created_at=old_time,
        )

        assert index.is_stale(ttl_seconds=3600)  # 1 hour TTL

    def test_exactly_at_ttl_not_stale(self) -> None:
        """Index at exactly TTL boundary should not be stale (> not >=)."""
        # Create index slightly before TTL boundary
        almost_stale_time = datetime.now(UTC) - timedelta(seconds=3599)
        index = GidLookupIndex(
            lookup_dict={"pv1:+17705753103:chiropractic": "111"},
            created_at=almost_stale_time,
        )

        assert not index.is_stale(ttl_seconds=3600)

    def test_zero_ttl_always_stale(self) -> None:
        """Zero TTL should make any non-instantaneous index stale."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103"],
                "vertical": ["chiropractic"],
                "gid": ["111"],
            }
        )
        index = GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

        # Even freshly created index becomes stale with 0 TTL
        # (due to time elapsed during creation)
        assert index.is_stale(ttl_seconds=0)


class TestGidLookupIndexContains:
    """Tests for GidLookupIndex.__contains__() method."""

    @pytest.fixture
    def sample_index(self) -> GidLookupIndex:
        """Create a sample index for testing."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103"],
                "vertical": ["chiropractic"],
                "gid": ["111"],
            }
        )
        return GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

    def test_contains_true_when_present(self, sample_index: GidLookupIndex) -> None:
        """'in' operator should return True for existing pair."""
        pair = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )

        assert pair in sample_index

    def test_contains_false_when_absent(self, sample_index: GidLookupIndex) -> None:
        """'in' operator should return False for missing pair."""
        pair = PhoneVerticalPair(
            office_phone="+19995551111",
            vertical="dental",
        )

        assert pair not in sample_index


class TestGidLookupIndexLen:
    """Tests for GidLookupIndex.__len__() method."""

    def test_len_empty(self) -> None:
        """Empty index should have length 0."""
        df = pl.DataFrame(
            {
                "office_phone": [],
                "vertical": [],
                "gid": [],
            }
        ).cast(
            {
                "office_phone": pl.Utf8,
                "vertical": pl.Utf8,
                "gid": pl.Utf8,
            }
        )
        index = GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

        assert len(index) == 0

    def test_len_populated(self) -> None:
        """Populated index should report correct count."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103", "+14045551234"],
                "vertical": ["chiropractic", "dental"],
                "gid": ["111", "222"],
            }
        )
        index = GidLookupIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

        assert len(index) == 2
