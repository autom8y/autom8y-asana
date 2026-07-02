"""W-REG wrong-BUCKET teeth: three-tier fail-closed precedence (SYNTHETIC).

rung: authored (NOT proven). BLOCKED-on-W-IRIS. These tests exercise the pure
``join_section_registry`` with a SYNTHETIC ``name -> GID`` map (fabricated GIDs,
never live). They prove the §6.4 three-tier precedence correction and its
downstream consequence, per TDD §7.

The SCAR-REG-001 sub-defect this closes (TDD §6.4): a live section name that is
in the local ``EXCLUDED_SECTION_NAMES`` but ABSENT from the monolith taxonomy
(e.g. "Account Review", "Next Steps") hits the ``bucket is None`` branch FIRST
and routes to NEITHER set — so under the verified DENYLIST processor it is
silently PROCESSED. The fix hoists the ``EXCLUDED_SECTION_NAMES`` check ahead of
the bucket-None route-to-neither (Tier-1), so local-only exclusions fail closed
toward exclusion; only a name unknown to BOTH sources reaches Tier-3, which
BLOCKS live-wiring instead of silently processing or excluding.

RED-first two-sided teeth (TDD §7.1/§7.2):
  DEFECT variant  -- the pre-fix routing (no Tier-1 correction) mis-buckets the
                     must-be-excluded name into NEITHER set -> its GID is absent
                     from excluded_section_gids -> RED; downstream the unit is
                     PROCESSED (excluded_count does not increment) -> RED.
  NO-DEFECT variant -- join_section_registry (with Tier-1) routes it to
                       excluded_section_gids -> GREEN; downstream the unit is
                       excluded (excluded_count increments) -> GREEN.

Test target: src/autom8_asana/reconciliation/section_registry.py
"""

from __future__ import annotations

import polars as pl

from autom8_asana.reconciliation.processor import ReconciliationBatchProcessor
from autom8_asana.reconciliation.section_registry import (
    EXCLUDED_SECTION_NAMES,
    Bucket,
    join_section_registry,
)

# ---------------------------------------------------------------------------
# Synthetic fixtures -- FABRICATED names/GIDs, never live (all GIDs start "9").
# ---------------------------------------------------------------------------

# The name that reproduces the §6.4 defect: it IS a local authoritative
# exclusion but is ABSENT from the monolith taxonomy.
EXCLUDED_MONOLITH_ABSENT_NAME = "Account Review"

# A genuinely-unknown live name -- in NEITHER EXCLUDED_SECTION_NAMES NOR the
# monolith taxonomy. This is the Tier-3 BLOCKING case.
UNKNOWN_NAME = "Brand New Live Section"

GID_ACCOUNT_REVIEW = "9000000000000005"
GID_MONTH_1 = "9000000000000010"
GID_ONBOARDING = "9000000000000011"
GID_UNENGAGED = "9000000000000012"
GID_TEMPLATES = "9000000000000013"
GID_UNKNOWN = "9000000000000099"

# Monolith name -> bucket taxonomy. Deliberately DOES NOT contain
# "Account Review" (a local-only exclusion) or the unknown name.
_MONOLITH_BUCKETS: dict[str, Bucket] = {
    "Month 1": "active",
    "Onboarding": "activating",
    "Unengaged": "inactive",
    "Templates": "ignore",
}

# Live receipt (synthetic): includes the monolith-absent excluded name.
_LIVE_GIDS: dict[str, str] = {
    EXCLUDED_MONOLITH_ABSENT_NAME: GID_ACCOUNT_REVIEW,
    "Month 1": GID_MONTH_1,
    "Onboarding": GID_ONBOARDING,
    "Unengaged": GID_UNENGAGED,
    "Templates": GID_TEMPLATES,
}


def _route_without_tier1_correction(
    name_to_gid: dict[str, str],
    name_to_bucket: dict[str, Bucket],
) -> tuple[frozenset[str], frozenset[str]]:
    """Faithful reproduction of the PRE-FIX scaffold routing (the DEFECT).

    Mirrors the original loop where ``name in EXCLUDED_SECTION_NAMES`` was
    checked only INSIDE the ``bucket is not None`` branch, so a monolith-absent
    excluded name fell through the ``bucket is None`` route-to-neither. This is
    the two-sided defect reference: it bites ONLY on the mis-bucketing defect.
    """
    unit_gids: set[str] = set()
    excluded_gids: set[str] = set()
    for name, gid in name_to_gid.items():
        bucket = name_to_bucket.get(name)
        if bucket is None:
            # DEFECT: routed to NEITHER before the EXCLUDED_SECTION_NAMES check.
            continue
        is_excluded = (bucket == "ignore") or (name in EXCLUDED_SECTION_NAMES)
        is_unit_bucket = bucket in {"active", "activating", "inactive"}
        if is_excluded:
            excluded_gids.add(gid)
        elif is_unit_bucket:
            unit_gids.add(gid)
    return frozenset(unit_gids), frozenset(excluded_gids)


def test_fixture_precondition_account_review_is_local_only_exclusion() -> None:
    """Guard: the probe name must be a local exclusion absent from the monolith."""
    assert EXCLUDED_MONOLITH_ABSENT_NAME in EXCLUDED_SECTION_NAMES
    assert EXCLUDED_MONOLITH_ABSENT_NAME not in _MONOLITH_BUCKETS
    assert UNKNOWN_NAME not in EXCLUDED_SECTION_NAMES
    assert UNKNOWN_NAME not in _MONOLITH_BUCKETS


# ===========================================================================
# §7.1 — join-level wrong-BUCKET teeth (two-sided)
# ===========================================================================


class TestWrongBucketJoinLevel:
    def test_defect_variant_misbuckets_excluded_name_red(self) -> None:
        """DEFECT (no Tier-1): the must-be-excluded name lands in NEITHER set."""
        _unit, excluded = _route_without_tier1_correction(_LIVE_GIDS, _MONOLITH_BUCKETS)
        assert GID_ACCOUNT_REVIEW not in excluded, (
            "RED: without the Tier-1 precedence correction, a monolith-absent "
            "EXCLUDED_SECTION_NAMES entry is mis-bucketed out of the excluded "
            "set (routed to neither -> processed downstream)."
        )

    def test_fixed_join_routes_excluded_name_to_excluded_green(self) -> None:
        """NO-DEFECT (Tier-1): the name routes to excluded, never to unit."""
        result = join_section_registry(_LIVE_GIDS, _MONOLITH_BUCKETS)
        assert GID_ACCOUNT_REVIEW in result.excluded_section_gids, (
            "GREEN: Tier-1 checks EXCLUDED_SECTION_NAMES first, so the live GID "
            "for a monolith-absent local exclusion lands in excluded_section_gids."
        )
        assert GID_ACCOUNT_REVIEW not in result.unit_section_gids

    def test_unit_bucket_names_still_route_to_unit(self) -> None:
        """Tier-2: genuine unit-bucket names remain in the unit set (no regress)."""
        result = join_section_registry(_LIVE_GIDS, _MONOLITH_BUCKETS)
        assert GID_MONTH_1 in result.unit_section_gids
        assert GID_ONBOARDING in result.unit_section_gids
        assert GID_UNENGAGED in result.unit_section_gids
        assert GID_TEMPLATES in result.excluded_section_gids  # ignore bucket


# ===========================================================================
# §6.4 point 2 — Tier-3 genuine-unknown BLOCKS live-wiring (surface AND halt)
# ===========================================================================


class TestTier3BlockingUnknown:
    def test_genuine_unknown_blocks_live_wiring_red(self) -> None:
        """A name unknown to BOTH sources routes to neither, emits
        live_name_no_bucket, AND flags the result as blocking live-wiring."""
        live = dict(_LIVE_GIDS)
        live[UNKNOWN_NAME] = GID_UNKNOWN
        result = join_section_registry(live, _MONOLITH_BUCKETS)

        assert GID_UNKNOWN not in result.unit_section_gids
        assert GID_UNKNOWN not in result.excluded_section_gids
        blocking = [f for f in result.blocking_findings if f.section_name == UNKNOWN_NAME]
        assert blocking and blocking[0].kind == "live_name_no_bucket"
        assert result.blocks_live_wiring is True, (
            "Tier-3 is BLOCKING, not advisory: a live section unknown to both "
            "sources must halt live-wiring (surface AND halt), never silently "
            "process or exclude."
        )

    def test_fully_dispositioned_join_does_not_block_green(self) -> None:
        """When every live name is dispositioned, live-wiring is not blocked."""
        result = join_section_registry(_LIVE_GIDS, _MONOLITH_BUCKETS)
        assert result.blocks_live_wiring is False
        assert result.blocking_findings == ()


# ===========================================================================
# §7.2 — processor-level consequence (proves the downstream harm)
# ===========================================================================


class TestProcessorConsequence:
    """Drive the DENYLIST processor with the join's excluded set to prove the
    wrong-bucket routing decision actually processes-vs-excludes a real unit."""

    @staticmethod
    def _account_review_unit_df() -> pl.DataFrame:
        # A single unit sitting in "Account Review" with its live section GID.
        return pl.DataFrame(
            {
                "gid": ["unit_ar"],
                "section": [EXCLUDED_MONOLITH_ABSENT_NAME],
                "section_gid": [GID_ACCOUNT_REVIEW],
                "office_phone": ["+15551234567"],
                "vertical": ["dental"],
            }
        )

    def test_defect_excluded_set_processes_the_unit_red(self, make_offer_df) -> None:
        """DEFECT: the AR GID is absent from the excluded set, so the unit is
        NOT excluded (falls through to processing) -> excluded_count == 0."""
        _unit, defect_excluded = _route_without_tier1_correction(_LIVE_GIDS, _MONOLITH_BUCKETS)
        processor = ReconciliationBatchProcessor(
            self._account_review_unit_df(),
            make_offer_df(gids=["offer_1"]),
            excluded_section_gids=defect_excluded,
        )
        result = processor.process()
        assert result.total_scanned == 1
        assert result.excluded_count == 0, (
            "RED: the mis-bucketed 'Account Review' unit is PROCESSED (not "
            "excluded) — the SCAR-REG-001 silent-misroute harm."
        )

    def test_fixed_excluded_set_excludes_the_unit_green(self, make_offer_df) -> None:
        """NO-DEFECT: the join's excluded set contains the AR GID, so the unit
        is excluded via GID -> excluded_count == 1."""
        result_join = join_section_registry(_LIVE_GIDS, _MONOLITH_BUCKETS)
        processor = ReconciliationBatchProcessor(
            self._account_review_unit_df(),
            make_offer_df(gids=["offer_1"]),
            excluded_section_gids=result_join.excluded_section_gids,
        )
        result = processor.process()
        assert result.total_scanned == 1
        assert result.excluded_count == 1, (
            "GREEN: with Tier-1 correction the 'Account Review' live GID is in "
            "the excluded set, so the unit is correctly excluded."
        )


# ===========================================================================
# Fixture hygiene fence: synthetic GIDs only (never live placeholders).
# ===========================================================================


def test_scaffold_uses_only_synthetic_gids() -> None:
    assert all(g.startswith("9") for g in _LIVE_GIDS.values())
    assert GID_UNKNOWN.startswith("9")
