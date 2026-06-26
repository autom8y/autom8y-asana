"""Unit value-population floor proof (FPC Phase-1, pillar C4).

C3 extended ``post_build_population_receipt._VALUE_COLUMNS_BY_ENTITY`` with
``"unit": ("mrr",)`` so a present-but-null ``mrr`` on the ACTIVE-classified unit
subset fires the ``population_receipt_below_floor`` WARN (the same degraded-warm
observability the offer floor already provides). These tests prove the floor
entry is behaviorally ACTIVE -- not inert config:

  - a null-mrr active unit subset -> ``below_floor is True`` (the RED signal), and
  - a fully-populated active unit subset -> ``below_floor is False`` (no
    false-positive).

G-DENOM is asserted directly: the receipt assesses ONLY ``mrr`` for units.
``weekly_ad_spend`` and ``discount`` are LegitimatelySparse for units and MUST
NOT be in the assessed value-column set (including them would manufacture false
WARNs -- the $8,775/7-row null-fossil anti-precedent). The receipt remains
WARN-first: it never raises and never changes build status.
"""

from __future__ import annotations

import polars as pl

from autom8_asana.dataframes.builders.post_build_population_receipt import (
    POPULATION_WARN_THRESHOLD,
    post_build_population_receipt,
)
from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA

# The unit-canonical project GID (Unit.PRIMARY_PROJECT_GID); log/span context only.
UNIT_PROJECT = "1201081073731555"


def _unit_frame(rows: int, *, mrr_value: float | None) -> pl.DataFrame:
    """An active unit frame: ``rows`` active units with a uniform ``mrr``.

    ``section="Active"`` lowercases into UNIT_CLASSIFIER.billable_sections(), so
    every row lands in the active-classified subset the receipt scopes to.
    """
    return pl.DataFrame(
        {
            "gid": [f"unit_{i}" for i in range(rows)],
            "section": ["Active"] * rows,
            "is_completed": [False] * rows,
            "mrr": [mrr_value] * rows,
        }
    )


class TestUnitPopulationFloor:
    """Proves the ``unit:('mrr',)`` floor entry (C3) is behaviorally active."""

    def test_present_but_null_unit_mrr_fires_below_floor(self) -> None:
        """RED: an active unit subset with all-null mrr -> below_floor receipt.

        Proves the floor entry is NOT inert: without C3, ``unit`` would have an
        empty value-column set and this frame would skip silently (assessed=False).
        """
        df = _unit_frame(10, mrr_value=None)
        receipt = post_build_population_receipt(
            merged_df=df, schema=UNIT_SCHEMA, entity_type="unit", project_gid=UNIT_PROJECT
        )
        assert receipt.assessed is True, (
            "unit floor inert: the receipt did not assess unit.mrr -- C3's "
            "_VALUE_COLUMNS_BY_ENTITY['unit'] entry is not wired"
        )
        assert receipt.below_floor is True, (
            "present-but-null unit mrr did not fire below_floor (the RED signal)"
        )
        assert receipt.min_rate == 0.0

    def test_fully_populated_unit_mrr_does_not_fire(self) -> None:
        """GREEN: a fully-populated active unit subset stays below_floor=False.

        The no-false-positive control: a healthy warm must NOT WARN.
        """
        df = _unit_frame(10, mrr_value=2500.0)
        receipt = post_build_population_receipt(
            merged_df=df, schema=UNIT_SCHEMA, entity_type="unit", project_gid=UNIT_PROJECT
        )
        assert receipt.assessed is True
        assert receipt.below_floor is False
        assert receipt.min_rate == 1.0

    def test_partial_null_below_threshold_fires(self) -> None:
        """RED: a sub-threshold mrr population rate fires below_floor.

        4 of 10 active units carry mrr (0.40 < 0.80 floor) -> WARN.
        """
        df = pl.DataFrame(
            {
                "gid": [f"unit_{i}" for i in range(10)],
                "section": ["Active"] * 10,
                "is_completed": [False] * 10,
                "mrr": [100.0 if i < 4 else None for i in range(10)],
            }
        )
        receipt = post_build_population_receipt(
            merged_df=df, schema=UNIT_SCHEMA, entity_type="unit", project_gid=UNIT_PROJECT
        )
        assert receipt.below_floor is True
        assert receipt.column_nonnull_rates["mrr"] < POPULATION_WARN_THRESHOLD

    def test_g_denom_only_mrr_is_assessed_for_units(self) -> None:
        """G-DENOM: the unit floor assesses ONLY mrr -- never weekly_ad_spend/discount.

        weekly_ad_spend and discount are LegitimatelySparse for units. Even when a
        unit frame carries those columns entirely null, the receipt must not
        assess them (doing so would manufacture false WARNs). Only ``mrr`` appears
        in the per-column rates.
        """
        df = pl.DataFrame(
            {
                "gid": [f"unit_{i}" for i in range(10)],
                "section": ["Active"] * 10,
                "is_completed": [False] * 10,
                "mrr": [2500.0] * 10,  # healthy
                "weekly_ad_spend": [None] * 10,  # legitimately sparse
                "discount": [None] * 10,  # legitimately sparse
            }
        )
        receipt = post_build_population_receipt(
            merged_df=df, schema=UNIT_SCHEMA, entity_type="unit", project_gid=UNIT_PROJECT
        )
        assert set(receipt.column_nonnull_rates) == {"mrr"}, (
            "G-DENOM violated: the unit floor assessed columns beyond mrr -- "
            f"got {sorted(receipt.column_nonnull_rates)}"
        )
        assert receipt.below_floor is False, (
            "sparse weekly_ad_spend/discount dragged the unit rate below floor -- "
            "they must not be assessed (false-WARN / null-fossil anti-precedent)"
        )

    def test_inactive_unit_rows_excluded_from_subset(self) -> None:
        """Inactive units (null mrr) do not drag the active subset's rate down."""
        active = _unit_frame(10, mrr_value=2500.0)
        inactive = pl.DataFrame(
            {
                "gid": [f"unit_inactive_{i}" for i in range(40)],
                "section": ["Cancelled"] * 40,  # UNIT_CLASSIFIER inactive
                "is_completed": [False] * 40,
                "mrr": [None] * 40,
            }
        )
        df = pl.concat([active, inactive])
        receipt = post_build_population_receipt(
            merged_df=df, schema=UNIT_SCHEMA, entity_type="unit", project_gid=UNIT_PROJECT
        )
        assert receipt.active_rows == 10
        assert receipt.below_floor is False

    def test_receipt_never_raises_on_unit_frame_missing_section(self) -> None:
        """WARN-first: a unit frame without a ``section`` column degrades, never raises."""
        df = pl.DataFrame({"gid": ["u0"], "mrr": [None]})  # no 'section'
        receipt = post_build_population_receipt(
            merged_df=df, schema=UNIT_SCHEMA, entity_type="unit", project_gid=UNIT_PROJECT
        )
        # Cannot determine the active subset -> skip (assessed=False), not WARN/raise.
        assert receipt.assessed is False
        assert receipt.below_floor is False
