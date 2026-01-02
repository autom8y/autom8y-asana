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
from datetime import datetime, timezone

import pytest

from autom8_asana.services.gid_lookup import GidLookupIndex


class TestSerialize:
    """Tests for GidLookupIndex.serialize() method."""

    def test_serialize_returns_dict_with_required_keys(self) -> None:
        """serialize() returns dict with version, created_at, entry_count, lookup."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc)
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
            created_at=datetime.now(timezone.utc),
        )

        result = index.serialize()

        assert result["version"] == "1.0"

    def test_serialize_created_at_is_iso_format(self) -> None:
        """serialize() converts created_at to ISO 8601 string."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, 123456, tzinfo=timezone.utc)
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
            created_at=datetime.now(timezone.utc),
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
            created_at=datetime.now(timezone.utc),
        )

        result = index.serialize()

        assert result["lookup"] == lookup

    def test_serialize_empty_index(self) -> None:
        """serialize() handles empty lookup dict correctly."""
        index = GidLookupIndex(
            lookup_dict={},
            created_at=datetime.now(timezone.utc),
        )

        result = index.serialize()

        assert result["entry_count"] == 0
        assert result["lookup"] == {}

    def test_serialize_is_json_compatible(self) -> None:
        """serialize() output can be serialized to JSON."""
        lookup = {"pv1:+17705753103:chiropractic": "123456789"}
        index = GidLookupIndex(
            lookup_dict=lookup,
            created_at=datetime.now(timezone.utc),
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

        expected = datetime(2024, 6, 15, 12, 30, 45, 123456, tzinfo=timezone.utc)
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

        expected = datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc)
        assert index.created_at == expected


class TestRoundTrip:
    """Tests for serialize/deserialize round-trip guarantee."""

    def test_round_trip_preserves_equality(self) -> None:
        """deserialize(serialize(index)) == index."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, 123456, tzinfo=timezone.utc)
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
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc)
        original = GidLookupIndex(lookup_dict={}, created_at=created_at)

        serialized = original.serialize()
        reconstructed = GidLookupIndex.deserialize(serialized)

        assert reconstructed == original
        assert len(reconstructed) == 0

    def test_round_trip_large_index(self) -> None:
        """Round-trip works for large index."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc)
        # Create 1000 entries
        lookup = {
            f"pv1:+1555555{i:04d}:vertical{i}": f"gid{i}"
            for i in range(1000)
        }
        original = GidLookupIndex(lookup_dict=lookup, created_at=created_at)

        serialized = original.serialize()
        reconstructed = GidLookupIndex.deserialize(serialized)

        assert reconstructed == original
        assert len(reconstructed) == 1000

    def test_round_trip_through_json(self) -> None:
        """Round-trip through JSON serialization works."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, 123456, tzinfo=timezone.utc)
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
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc)
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
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc)
        lookup = {"key": "value"}

        index1 = GidLookupIndex(lookup_dict=lookup, created_at=created_at)
        index2 = GidLookupIndex(lookup_dict=lookup.copy(), created_at=created_at)

        assert index1 == index2

    def test_different_lookup_not_equal(self) -> None:
        """Indices with different lookup are not equal."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc)

        index1 = GidLookupIndex(lookup_dict={"key1": "val1"}, created_at=created_at)
        index2 = GidLookupIndex(lookup_dict={"key2": "val2"}, created_at=created_at)

        assert index1 != index2

    def test_different_created_at_not_equal(self) -> None:
        """Indices with different created_at are not equal."""
        lookup = {"key": "value"}

        index1 = GidLookupIndex(
            lookup_dict=lookup,
            created_at=datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc),
        )
        index2 = GidLookupIndex(
            lookup_dict=lookup,
            created_at=datetime(2024, 6, 16, 12, 30, 45, tzinfo=timezone.utc),
        )

        assert index1 != index2

    def test_not_equal_to_non_index(self) -> None:
        """Index is not equal to non-GidLookupIndex objects."""
        index = GidLookupIndex(
            lookup_dict={"key": "value"},
            created_at=datetime.now(timezone.utc),
        )

        assert index != "not an index"
        assert index != 42
        assert index != {"key": "value"}

    def test_equal_empty_indices(self) -> None:
        """Two empty indices with same created_at are equal."""
        created_at = datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc)

        index1 = GidLookupIndex(lookup_dict={}, created_at=created_at)
        index2 = GidLookupIndex(lookup_dict={}, created_at=created_at)

        assert index1 == index2
