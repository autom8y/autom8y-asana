"""Tests for ReconciliationBatchProcessor.

Per REVIEW-reconciliation-deep-audit TC-1, TC-2, TC-9:
- All DataFrame fixtures use canonical "section" column (NOT "section_name",
  which was a processor-local misnomer that masked production failures)
- Exclusion tests verify EXCLUDED_SECTION_NAMES (4 entries) is used,
  NOT UNIT_CLASSIFIER.ignored (1 entry)
- GID exclusion fires before name-based fallback

Module: tests/unit/reconciliation/test_processor.py
"""

from __future__ import annotations

import polars as pl
import pytest

from autom8_asana.reconciliation.processor import (
    ReconciliationBatchProcessor,
)
from autom8_asana.reconciliation.section_registry import (
    EXCLUDED_SECTION_GIDS,
    EXCLUDED_SECTION_NAMES,
)


class TestProcessorColumnContract:
    """P0-A: Verify processor uses "section" column, not "section_name"."""

    def test_process_with_section_column_succeeds(self, make_unit_df, make_offer_df) -> None:
        """Processor works correctly with canonical "section" column."""
        unit_df = make_unit_df(
            gids=["unit_1"],
            sections=["Active"],
        )
        offer_df = make_offer_df(gids=["offer_1"])

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.total_scanned == 1
        assert result.error_count == 0

    def test_process_without_section_column_excludes_all(self, make_offer_df) -> None:
        """Units without "section" column are all excluded via no-section path."""
        # DataFrame with NO section column at all
        unit_df = pl.DataFrame({
            "gid": ["unit_1", "unit_2"],
            "office_phone": ["+15551234567", "+15559876543"],
        })
        offer_df = make_offer_df(gids=["offer_1"])

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.total_scanned == 2
        # All excluded via no-section path
        assert result.excluded_count == 2
        assert result.skipped_no_section == 2

    def test_offer_df_uses_section_column(self, make_unit_df, make_offer_df) -> None:
        """Offer activity index is built from "section" column."""
        unit_df = make_unit_df(gids=["unit_1"])
        offer_df = make_offer_df(
            gids=["offer_1", "offer_2"],
            sections=["ACTIVE", "STAGING"],
        )

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        index = processor._build_offer_activity_index(offer_df)

        assert "offer_1" in index
        assert index["offer_1"] == "ACTIVE"
        assert "offer_2" in index
        assert index["offer_2"] == "STAGING"


class TestGidExclusion:
    """P0-B: GID-based exclusion fires first."""

    def test_excluded_by_gid(self, make_offer_df) -> None:
        """Units with excluded section GIDs are excluded regardless of name."""
        excluded_gid = next(iter(EXCLUDED_SECTION_GIDS))
        unit_df = pl.DataFrame({
            "gid": ["unit_1"],
            "section": ["SomeValidSection"],
            "section_gid": [excluded_gid],
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
        })
        offer_df = make_offer_df(gids=["offer_1"])

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.excluded_count == 1
        assert result.total_scanned == 1

    def test_non_excluded_gid_passes_through(self, make_offer_df) -> None:
        """Units with non-excluded GIDs are processed normally."""
        unit_df = pl.DataFrame({
            "gid": ["unit_1"],
            "section": ["Active"],
            "section_gid": ["9999999999999999"],  # Not in excluded set
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
        })
        offer_df = make_offer_df(gids=["offer_1"])

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.excluded_count == 0
        assert result.no_op_count == 1


class TestNameExclusion:
    """P0-B: Name-based exclusion fallback when GID unavailable."""

    @pytest.mark.parametrize("section_name", sorted(EXCLUDED_SECTION_NAMES))
    def test_all_four_excluded_names_are_excluded(
        self, section_name: str, make_offer_df
    ) -> None:
        """Each of the 4 EXCLUDED_SECTION_NAMES triggers exclusion.

        This test covers the TC-2 fix-path trap: UNIT_CLASSIFIER.ignored
        has only {"Templates"}, but EXCLUDED_SECTION_NAMES has all 4.
        """
        unit_df = pl.DataFrame({
            "gid": ["unit_1"],
            "section": [section_name],
            # No section_gid column -- forces name-based fallback
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
        })
        offer_df = make_offer_df(gids=["offer_1"])

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.excluded_count == 1, (
            f"Section '{section_name}' should be excluded but was not"
        )

    def test_name_exclusion_only_fires_when_gid_absent(self, make_offer_df) -> None:
        """Name fallback does NOT fire when section_gid is present."""
        unit_df = pl.DataFrame({
            "gid": ["unit_1"],
            "section": ["Templates"],
            "section_gid": ["9999999999999999"],  # Present but not in excluded GIDs
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
        })
        offer_df = make_offer_df(gids=["offer_1"])

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        # GID is present and NOT in excluded set, so name fallback should not fire
        assert result.excluded_count == 0
        assert result.no_op_count == 1

    def test_non_excluded_name_passes_through(self, make_offer_df) -> None:
        """Valid section names that are NOT in EXCLUDED_SECTION_NAMES pass through."""
        unit_df = pl.DataFrame({
            "gid": ["unit_1"],
            "section": ["Active"],
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
        })
        offer_df = make_offer_df(gids=["offer_1"])

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.excluded_count == 0
        assert result.no_op_count == 1


class TestNoSectionExclusion:
    """Units with no section are excluded via no-section path."""

    def test_none_section_excluded(self, make_unit_df, make_offer_df) -> None:
        """Rows with None section are excluded."""
        unit_df = make_unit_df(
            gids=["unit_1"],
            sections=[None],
        )
        offer_df = make_offer_df(gids=["offer_1"])

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.excluded_count == 1
        assert result.skipped_no_section == 1

    def test_mixed_sections_partial_exclusion(self, make_unit_df, make_offer_df) -> None:
        """Mix of valid and null sections produces correct counts."""
        unit_df = make_unit_df(
            gids=["unit_1", "unit_2", "unit_3"],
            sections=["Active", None, "Onboarding"],
        )
        offer_df = make_offer_df(gids=["offer_1"])

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.total_scanned == 3
        assert result.excluded_count == 1  # Only the None section
        assert result.no_op_count == 2  # Active + Onboarding


class TestSchemaEntryGuard:
    """P1-B: Schema entry guard warns on missing section column."""

    def test_warn_when_no_section_columns(self) -> None:
        """Guard warns when DataFrame has neither section nor section_name."""
        df = pl.DataFrame({"gid": ["unit_1"], "office_phone": ["+15551234567"]})
        offer_df = pl.DataFrame({"gid": ["offer_1"], "section": ["ACTIVE"]})

        # Should not raise, but should log warning internally
        processor = ReconciliationBatchProcessor(df, offer_df)
        result = processor.process()

        # All rows excluded via no-section path
        assert result.skipped_no_section == 1

    def test_no_warn_when_section_present(self, make_unit_df, make_offer_df) -> None:
        """No warning when canonical "section" column is present."""
        unit_df = make_unit_df(gids=["unit_1"])
        offer_df = make_offer_df(gids=["offer_1"])

        # Should not raise or warn
        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.error_count == 0


class TestEdgeCases:
    """Edge cases for processor robustness."""

    def test_empty_dataframes(self, make_unit_df, make_offer_df) -> None:
        """Empty DataFrames produce zero-count result."""
        unit_df = pl.DataFrame({"gid": [], "section": [], "office_phone": [], "vertical": []})
        offer_df = pl.DataFrame({"gid": [], "section": []})

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.total_scanned == 0
        assert result.excluded_count == 0
        assert result.no_op_count == 0

    def test_no_phone_is_no_op(self, make_offer_df) -> None:
        """Units without phone number are no-ops (cannot match to offers)."""
        unit_df = pl.DataFrame({
            "gid": ["unit_1"],
            "section": ["Active"],
            "office_phone": [None],
            "vertical": ["dental"],
        })
        offer_df = make_offer_df(gids=["offer_1"])

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.no_op_count == 1
        assert result.excluded_count == 0
