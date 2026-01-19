"""Unit tests for GidLookupIndex.

Tests cover:
- Empty DataFrame handling
- Single and batch lookups
- Stale detection with TTL
- Canonical key format handling
- Null value filtering
- Missing column validation
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from autom8_asana.models.contracts.phone_vertical import PhoneVerticalPair
from autom8_asana.services.gid_lookup import GidLookupIndex


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

        index = GidLookupIndex.from_dataframe(df)

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

        index = GidLookupIndex.from_dataframe(df)

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

        index = GidLookupIndex.from_dataframe(df)

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
            GidLookupIndex.from_dataframe(df)

    def test_null_phone_rows_filtered(self) -> None:
        """Rows with null office_phone should be excluded."""
        df = pl.DataFrame(
            {
                "office_phone": ["+17705753103", None, "+14045551234"],
                "vertical": ["chiropractic", "dental", "dental"],
                "gid": ["111", "222", "333"],
            }
        )

        index = GidLookupIndex.from_dataframe(df)

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

        index = GidLookupIndex.from_dataframe(df)

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

        index = GidLookupIndex.from_dataframe(df)

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

        before = datetime.now(timezone.utc)
        index = GidLookupIndex.from_dataframe(df)
        after = datetime.now(timezone.utc)

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

        index = GidLookupIndex.from_dataframe(df)

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
        return GidLookupIndex.from_dataframe(df)

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

    def test_get_gid_wrong_vertical_returns_none(
        self, sample_index: GidLookupIndex
    ) -> None:
        """Should return None when phone exists but vertical differs."""
        # Phone exists with 'chiropractic', not 'dental'
        pair = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="dental",
        )

        result = sample_index.get_gid(pair)

        assert result is None

    def test_get_gid_uses_canonical_key_format(
        self, sample_index: GidLookupIndex
    ) -> None:
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
        return GidLookupIndex.from_dataframe(df)

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

    def test_get_gids_mixed_found_and_not_found(
        self, sample_index: GidLookupIndex
    ) -> None:
        """Mix of found and not found should have None for missing."""
        pairs = [
            PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic"),
            PhoneVerticalPair(
                office_phone="+19995551111", vertical="dental"
            ),  # Not in index
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
        index = GidLookupIndex.from_dataframe(df)

        assert not index.is_stale(ttl_seconds=3600)

    def test_old_index_is_stale(self) -> None:
        """Index older than TTL should be stale."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        index = GidLookupIndex(
            lookup_dict={"pv1:+17705753103:chiropractic": "111"},
            created_at=old_time,
        )

        assert index.is_stale(ttl_seconds=3600)  # 1 hour TTL

    def test_exactly_at_ttl_not_stale(self) -> None:
        """Index at exactly TTL boundary should not be stale (> not >=)."""
        # Create index slightly before TTL boundary
        almost_stale_time = datetime.now(timezone.utc) - timedelta(seconds=3599)
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
        index = GidLookupIndex.from_dataframe(df)

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
        return GidLookupIndex.from_dataframe(df)

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
        index = GidLookupIndex.from_dataframe(df)

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
        index = GidLookupIndex.from_dataframe(df)

        assert len(index) == 2
