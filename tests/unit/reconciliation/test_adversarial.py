"""Adversarial tests for reconciliation exclusion parity.

Per REVIEW-reconciliation-deep-audit TC-2, TC-9:
These tests guard against the most dangerous defect: someone updating
EXCLUDED_SECTION_GIDS without updating EXCLUDED_SECTION_NAMES (or vice
versa), which would silently allow units in excluded sections through
the processor.

Also tests the critical invariant: EXCLUDED_SECTION_NAMES must contain
exactly {"Templates", "Next Steps", "Account Review", "Account Error"},
NOT just {"Templates"} (which is what UNIT_CLASSIFIER.ignored contains).

Module: tests/unit/reconciliation/test_adversarial.py
"""

from __future__ import annotations

import polars as pl
import pytest

from autom8_asana.reconciliation.processor import ReconciliationBatchProcessor
from autom8_asana.reconciliation.section_registry import (
    EXCLUDED_GID_TO_NAME,
    EXCLUDED_SECTION_GIDS,
    EXCLUDED_SECTION_NAMES,
)


class TestExclusionParityAssertion:
    """Parity tests prevent divergence between GID and name exclusion sets.

    Per REVIEW-reconciliation-deep-audit TC-2: The fix-path trap is that
    UNIT_CLASSIFIER.ignored has only {"Templates"}, while 4 sections must
    be excluded. These tests ensure the name and GID sets stay in sync.
    """

    def test_excluded_gids_has_exactly_4_entries(self) -> None:
        """EXCLUDED_SECTION_GIDS must have exactly 4 entries.

        One for each excluded section: Templates, Next Steps,
        Account Review, Account Error.
        """
        assert len(EXCLUDED_SECTION_GIDS) == 4, (
            f"Expected exactly 4 excluded GIDs, got {len(EXCLUDED_SECTION_GIDS)}. "
            f"GIDs: {EXCLUDED_SECTION_GIDS}"
        )

    def test_excluded_gids_map_to_known_sections(self) -> None:
        """Every excluded GID maps to a known section name in the GID-to-name mapping."""
        for gid in EXCLUDED_SECTION_GIDS:
            assert gid in EXCLUDED_GID_TO_NAME, (
                f"Excluded GID {gid} has no entry in EXCLUDED_GID_TO_NAME. "
                "Every excluded GID must map to a known section name."
            )

    def test_registry_excluded_gids_match_gid_to_name_keys(self) -> None:
        """EXCLUDED_SECTION_GIDS and EXCLUDED_GID_TO_NAME keys are identical sets."""
        assert frozenset(EXCLUDED_GID_TO_NAME.keys()) == EXCLUDED_SECTION_GIDS, (
            "EXCLUDED_SECTION_GIDS and EXCLUDED_GID_TO_NAME.keys() must be identical. "
            f"GIDs: {EXCLUDED_SECTION_GIDS}, "
            f"Mapping keys: {set(EXCLUDED_GID_TO_NAME.keys())}"
        )

    def test_excluded_names_has_exactly_4_entries(self) -> None:
        """EXCLUDED_SECTION_NAMES must have exactly 4 entries.

        This guards against accidentally using UNIT_CLASSIFIER.ignored
        (which has only 1 entry: "Templates").
        """
        assert len(EXCLUDED_SECTION_NAMES) == 4, (
            f"Expected exactly 4 excluded names, got {len(EXCLUDED_SECTION_NAMES)}. "
            f"Names: {EXCLUDED_SECTION_NAMES}"
        )

    def test_excluded_names_match_expected_set(self) -> None:
        """EXCLUDED_SECTION_NAMES contains exactly the 4 expected sections.

        Per REVIEW-reconciliation-deep-audit TC-2: These are the sections
        that must be excluded, regardless of how UNIT_CLASSIFIER.ignored
        is configured.
        """
        expected = frozenset(
            {
                "Templates",
                "Next Steps",
                "Account Review",
                "Account Error",
            }
        )
        assert expected == EXCLUDED_SECTION_NAMES, (
            f"Expected {expected}, got {EXCLUDED_SECTION_NAMES}. "
            "Per REVIEW-reconciliation-deep-audit TC-2: Do NOT use "
            "UNIT_CLASSIFIER.ignored (only has 'Templates')."
        )

    def test_excluded_names_count_matches_gids_count(self) -> None:
        """GID set and name set have the same cardinality.

        A mismatch means someone added a GID without a corresponding name
        (or vice versa), breaking the 1:1 correspondence.
        """
        assert len(EXCLUDED_SECTION_GIDS) == len(EXCLUDED_SECTION_NAMES), (
            f"GID count ({len(EXCLUDED_SECTION_GIDS)}) != "
            f"name count ({len(EXCLUDED_SECTION_NAMES)}). "
            "Every excluded section must have both a GID and a name."
        )


class TestNameExclusionCoverage:
    """Verify all 4 excluded section names are actually excluded at runtime."""

    @pytest.mark.parametrize("section_name", sorted(EXCLUDED_SECTION_NAMES))
    def test_each_excluded_name_triggers_exclusion(self, section_name: str) -> None:
        """Each EXCLUDED_SECTION_NAMES entry causes exclusion in processor.

        This is the runtime verification of the TC-2 fix: all 4 sections
        must actually be excluded, not just Templates.
        """
        unit_df = pl.DataFrame(
            {
                "gid": ["unit_1"],
                "section": [section_name],
                "office_phone": ["+15551234567"],
                "vertical": ["dental"],
            }
        )
        offer_df = pl.DataFrame(
            {
                "gid": ["offer_1"],
                "section": ["ACTIVE"],
            }
        )

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.excluded_count == 1, (
            f"Section '{section_name}' should be excluded by name fallback "
            f"but excluded_count was {result.excluded_count}"
        )

    def test_name_exclusion_does_not_affect_valid_sections(self) -> None:
        """Non-excluded section names pass through to processing."""
        valid_sections = ["Active", "Onboarding", "Month 1", "Unengaged", "Paused"]

        for section_name in valid_sections:
            unit_df = pl.DataFrame(
                {
                    "gid": ["unit_1"],
                    "section": [section_name],
                    "office_phone": ["+15551234567"],
                    "vertical": ["dental"],
                }
            )
            offer_df = pl.DataFrame(
                {
                    "gid": ["offer_1"],
                    "section": ["ACTIVE"],
                }
            )

            processor = ReconciliationBatchProcessor(unit_df, offer_df)
            result = processor.process()

            assert result.excluded_count == 0, (
                f"Section '{section_name}' should NOT be excluded but was"
            )


class TestNoneSectionEdgeCase:
    """Verify None section handling in exclusion path."""

    def test_none_section_excluded_via_no_section_path(self) -> None:
        """Unit with None section is excluded via skipped_no_section counter."""
        unit_df = pl.DataFrame(
            {
                "gid": ["unit_1"],
                "section": [None],
                "office_phone": ["+15551234567"],
                "vertical": ["dental"],
            }
        )
        offer_df = pl.DataFrame(
            {
                "gid": ["offer_1"],
                "section": ["ACTIVE"],
            }
        )

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        assert result.excluded_count == 1
        assert result.skipped_no_section == 1

    def test_empty_string_section_excluded_via_no_section_path(self) -> None:
        """Unit with empty string section is excluded via no-section path.

        Empty string is falsy, so it falls through the name check and
        hits the no-section exclusion.
        """
        unit_df = pl.DataFrame(
            {
                "gid": ["unit_1"],
                "section": [""],
                "office_phone": ["+15551234567"],
                "vertical": ["dental"],
            }
        )
        offer_df = pl.DataFrame(
            {
                "gid": ["offer_1"],
                "section": ["ACTIVE"],
            }
        )

        processor = ReconciliationBatchProcessor(unit_df, offer_df)
        result = processor.process()

        # Empty string section -> excluded via no-section path
        assert result.excluded_count == 1


class TestUnitClassifierIgnoredNotUsed:
    """Guard against accidental use of UNIT_CLASSIFIER.ignored."""

    def test_unit_classifier_ignored_has_only_templates(self) -> None:
        """Confirm UNIT_CLASSIFIER.ignored has only 1 entry.

        This test documents WHY we cannot use UNIT_CLASSIFIER.ignored:
        it only contains {"Templates"}, missing 3 of 4 excluded sections.
        """
        from autom8_asana.models.business.activity import UNIT_CLASSIFIER

        ignored = UNIT_CLASSIFIER.sections_for(
            __import__(
                "autom8_asana.models.business.activity", fromlist=["AccountActivity"]
            ).AccountActivity.IGNORED,
        )
        # UNIT_CLASSIFIER.ignored sections mapped via classify -> IGNORED
        assert "templates" in ignored, "UNIT_CLASSIFIER should classify 'Templates' as IGNORED"
        # Verify it does NOT include the other 3 excluded sections
        assert "next steps" not in ignored
        assert "account review" not in ignored
        assert "account error" not in ignored
