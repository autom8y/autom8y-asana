"""Tests for query/join.py: JoinSpec model and execute_join().

Test cases TC-J001 through TC-J005 (model) and TC-JE001 through TC-JE011
(execution) per TDD-hierarchy-index Sections 10.2-10.3.
"""

from __future__ import annotations

import polars as pl
import pytest
from pydantic import ValidationError

from autom8_asana.query.errors import JoinError
from autom8_asana.query.join import JoinSpec, execute_join


# ---------------------------------------------------------------------------
# JoinSpec Model Tests (TC-J001 through TC-J005)
# ---------------------------------------------------------------------------


class TestJoinSpecModel:
    """JoinSpec Pydantic model validation."""

    def test_tc_j001_valid_parsing(self) -> None:
        """TC-J001: Valid JoinSpec parses successfully."""
        spec = JoinSpec(entity_type="business", select=["booking_type"])
        assert spec.entity_type == "business"
        assert spec.select == ["booking_type"]
        assert spec.on is None

    def test_tc_j002_explicit_on_key(self) -> None:
        """TC-J002: JoinSpec with explicit on key."""
        spec = JoinSpec(
            entity_type="business",
            select=["booking_type"],
            on="office_phone",
        )
        assert spec.on == "office_phone"

    def test_tc_j003_empty_select_rejected(self) -> None:
        """TC-J003: JoinSpec with empty select raises validation error."""
        with pytest.raises(ValidationError):
            JoinSpec(entity_type="business", select=[])

    def test_tc_j004_over_max_select_rejected(self) -> None:
        """TC-J004: JoinSpec with >10 select columns rejected."""
        with pytest.raises(ValidationError):
            JoinSpec(
                entity_type="business",
                select=[f"col_{i}" for i in range(11)],
            )

    def test_tc_j005_extra_fields_rejected(self) -> None:
        """TC-J005: JoinSpec with extra fields rejected."""
        with pytest.raises(ValidationError):
            JoinSpec(
                entity_type="business",
                select=["booking_type"],
                unknown_field="bad",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# Fixtures for execute_join tests
# ---------------------------------------------------------------------------


@pytest.fixture
def primary_df() -> pl.DataFrame:
    """Primary entity DataFrame (offers)."""
    return pl.DataFrame(
        {
            "gid": ["o1", "o2", "o3", "o4"],
            "name": ["Offer A", "Offer B", "Offer C", "Offer D"],
            "office_phone": ["+1111", "+2222", "+3333", None],
        }
    )


@pytest.fixture
def target_df() -> pl.DataFrame:
    """Target entity DataFrame (businesses)."""
    return pl.DataFrame(
        {
            "gid": ["b1", "b2", "b3"],
            "name": ["Biz A", "Biz B", "Biz C"],
            "office_phone": ["+1111", "+2222", "+4444"],
            "booking_type": ["Online", "Phone", "Walk-in"],
            "stripe_id": ["str_1", "str_2", "str_3"],
        }
    )


# ---------------------------------------------------------------------------
# Join Execution Tests (TC-JE001 through TC-JE011)
# ---------------------------------------------------------------------------


class TestExecuteJoin:
    """Tests for execute_join()."""

    def test_tc_je001_basic_left_join(
        self, primary_df: pl.DataFrame, target_df: pl.DataFrame
    ) -> None:
        """TC-JE001: Basic left join enriches with prefixed columns."""
        result = execute_join(
            primary_df=primary_df,
            target_df=target_df,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        assert "business_booking_type" in result.df.columns
        assert result.join_key == "office_phone"
        # Rows with +1111 and +2222 match
        assert result.matched_count == 2
        assert result.unmatched_count == 2  # +3333 no match, None no match

    def test_tc_je002_null_join_key(
        self, primary_df: pl.DataFrame, target_df: pl.DataFrame
    ) -> None:
        """TC-JE002: Rows with null join key get null join columns."""
        result = execute_join(
            primary_df=primary_df,
            target_df=target_df,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        # Row with gid=o4 has null office_phone
        enriched = result.df.filter(pl.col("gid") == "o4")
        assert enriched["business_booking_type"][0] is None

    def test_tc_je003_no_matches(self, primary_df: pl.DataFrame) -> None:
        """TC-JE003: Join with no matches results in all null join columns."""
        no_match_target = pl.DataFrame(
            {
                "office_phone": ["+9999"],
                "booking_type": ["Unknown"],
            }
        )
        result = execute_join(
            primary_df=primary_df,
            target_df=no_match_target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        assert result.matched_count == 0
        assert result.unmatched_count == primary_df.height

    def test_tc_je004_all_matches(self) -> None:
        """TC-JE004: Join where all rows match."""
        primary = pl.DataFrame(
            {
                "gid": ["o1", "o2"],
                "office_phone": ["+1111", "+2222"],
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+1111", "+2222"],
                "booking_type": ["Online", "Phone"],
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        assert result.matched_count == 2
        assert result.unmatched_count == 0

    def test_tc_je005_join_key_missing_primary(self, target_df: pl.DataFrame) -> None:
        """TC-JE005: Join key missing from primary raises JoinError."""
        no_key_primary = pl.DataFrame({"gid": ["o1"], "name": ["Offer A"]})
        with pytest.raises(JoinError, match="not found in primary"):
            execute_join(
                primary_df=no_key_primary,
                target_df=target_df,
                join_key="office_phone",
                select_columns=["booking_type"],
                target_entity_type="business",
            )

    def test_tc_je006_join_key_missing_target(self, primary_df: pl.DataFrame) -> None:
        """TC-JE006: Join key missing from target raises JoinError."""
        no_key_target = pl.DataFrame({"gid": ["b1"], "booking_type": ["Online"]})
        with pytest.raises(JoinError, match="not found in target"):
            execute_join(
                primary_df=primary_df,
                target_df=no_key_target,
                join_key="office_phone",
                select_columns=["booking_type"],
                target_entity_type="business",
            )

    def test_tc_je007_select_column_missing_target(
        self, primary_df: pl.DataFrame, target_df: pl.DataFrame
    ) -> None:
        """TC-JE007: Select column missing from target raises JoinError."""
        with pytest.raises(JoinError, match="not found in target"):
            execute_join(
                primary_df=primary_df,
                target_df=target_df,
                join_key="office_phone",
                select_columns=["nonexistent_col"],
                target_entity_type="business",
            )

    def test_tc_je008_duplicate_join_key_dedup(self, primary_df: pl.DataFrame) -> None:
        """TC-JE008: Target with duplicate join keys deduplicates (first)."""
        dup_target = pl.DataFrame(
            {
                "office_phone": ["+1111", "+1111"],
                "booking_type": ["First", "Second"],
            }
        )
        result = execute_join(
            primary_df=primary_df,
            target_df=dup_target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        # Should take first occurrence
        matched_row = result.df.filter(pl.col("office_phone") == "+1111")
        assert matched_row["business_booking_type"][0] == "First"
        # Row count should not multiply
        assert result.df.height == primary_df.height

    def test_tc_je009_column_prefix_avoids_collision(
        self, primary_df: pl.DataFrame, target_df: pl.DataFrame
    ) -> None:
        """TC-JE009: Target columns prefixed with entity type."""
        result = execute_join(
            primary_df=primary_df,
            target_df=target_df,
            join_key="office_phone",
            select_columns=["booking_type", "stripe_id"],
            target_entity_type="business",
        )
        assert "business_booking_type" in result.df.columns
        assert "business_stripe_id" in result.df.columns
        # Original columns preserved
        assert "name" in result.df.columns
        assert "gid" in result.df.columns

    def test_tc_je010_empty_primary(self, target_df: pl.DataFrame) -> None:
        """TC-JE010: Empty primary DataFrame returns empty enriched DF."""
        empty_primary = pl.DataFrame(
            {
                "gid": pl.Series([], dtype=pl.Utf8),
                "office_phone": pl.Series([], dtype=pl.Utf8),
            }
        )
        result = execute_join(
            primary_df=empty_primary,
            target_df=target_df,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        assert result.df.height == 0
        assert "business_booking_type" in result.df.columns
        assert result.matched_count == 0
        assert result.unmatched_count == 0

    def test_tc_je011_empty_target(self, primary_df: pl.DataFrame) -> None:
        """TC-JE011: Empty target DataFrame results in all null join columns."""
        empty_target = pl.DataFrame(
            {
                "office_phone": pl.Series([], dtype=pl.Utf8),
                "booking_type": pl.Series([], dtype=pl.Utf8),
            }
        )
        result = execute_join(
            primary_df=primary_df,
            target_df=empty_target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        assert result.df.height == primary_df.height
        assert result.matched_count == 0
        assert result.unmatched_count == primary_df.height
