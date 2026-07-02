"""W-REG live-wiring proof: the receipt reproduces the exact 17-map, the join is
two-sided against a wrong-bucket defect, and the N2a fail-closed HALT fires on
the reachable live path.

Unlike the SYNTHETIC scaffold suites (test_section_registry_join.py,
test_section_registry_wreg_wrong_bucket.py), these tests exercise the REAL
live-wiring: the module's own ``_RECEIPT_NAME_TO_GID`` x vendored taxonomy join
and the ``_build_live_registry`` producer that yields ``EXCLUDED_SECTION_GIDS`` /
``UNIT_SECTION_GIDS`` (the constants ``reconciliation.processor`` imports).

Two-sided teeth (TDD §7; grandeur anchor):
  GREEN -- the live join reproduces the W-IRIS receipt's exact 17-map
           (4 excluded incl. Account Review / Account Error, 13 unit).
  RED   -- mutating the Tier-1 correction out (``_route_without_tier1_correction``)
           mis-buckets the monolith-absent local exclusions (Account Review /
           Account Error) into NEITHER set -> their live GID is absent from the
           excluded set (they would be PROCESSED under the denylist).

Gate-bite (N2a): an unknown live section makes the join ``blocks_live_wiring``
AND makes ``_build_live_registry`` RAISE -- proving the HALT sits on the same
producer the module calls at import, not on a proof-only join.

The expected partition below is transcribed INDEPENDENTLY from the W-IRIS receipt
(.ledge/reviews/W-IRIS-section-gid-receipt-2026-07-02.md §2/§4), grouped by
bucket, as a cross-check against the module's receipt-ordered map.

Test target: src/autom8_asana/reconciliation/section_registry.py
"""

from __future__ import annotations

import re

import pytest

import autom8_asana.reconciliation.section_registry as sr
from autom8_asana.reconciliation.section_registry import (
    EXCLUDED_GID_TO_NAME,
    EXCLUDED_SECTION_GIDS,
    UNIT_SECTION_GIDS,
    Bucket,
    SectionRegistryError,
    join_section_registry,
)

# ---------------------------------------------------------------------------
# Independently-transcribed expected partition (W-IRIS receipt §2/§4).
# Grouped by bucket (NOT receipt order) so a copy-paste transposition against the
# module's receipt-ordered map does not line up -- this is a cross-check.
# ---------------------------------------------------------------------------

_EXPECTED_EXCLUDED: dict[str, str] = {
    "Templates": "1201122816966634",
    "Next Steps": "1201081073731564",
    "Account Review": "1201081073731572",
    "Account Error": "1201081073731573",
}

_EXPECTED_UNIT: dict[str, str] = {
    "Month 1": "1201081073731570",
    "Consulting": "1201081073731568",
    "Active": "1201081073731571",
    "Onboarding": "1201081073731565",
    "Implementing": "1201081073731566",
    "Delayed": "1201081073731567",
    "Preview": "1201081073731569",
    "Engaged": "1201081073731561",
    "Scheduled": "1201081073731562",
    "Unengaged": "1201239149602679",
    "Paused": "1201081073731574",
    "Cancelled": "1201081073731575",
    "No Start": "1201087333420106",
}

_UNKNOWN_LIVE_NAME = "Brand New Live Section"
_UNKNOWN_LIVE_GID = "1209999999999999"  # never a real placeholder (…600-624)


def _route_without_tier1_correction(
    name_to_gid: dict[str, str],
    name_to_bucket: dict[str, Bucket],
) -> tuple[frozenset[str], frozenset[str]]:
    """Faithful reproduction of the PRE-FIX routing (the DEFECT variant).

    Mirrors the original scaffold loop where ``name in EXCLUDED_SECTION_NAMES``
    was checked only INSIDE the ``bucket is not None`` branch, so a
    monolith-absent excluded name (e.g. Account Review) fell through the
    ``bucket is None`` route-to-neither. Bites ONLY on the mis-bucketing defect.
    """
    unit_gids: set[str] = set()
    excluded_gids: set[str] = set()
    for name, gid in name_to_gid.items():
        bucket = name_to_bucket.get(name)
        if bucket is None:
            # DEFECT: routed to NEITHER before the EXCLUDED_SECTION_NAMES check.
            continue
        is_excluded = (bucket == "ignore") or (name in sr.EXCLUDED_SECTION_NAMES)
        is_unit_bucket = bucket in {"active", "activating", "inactive"}
        if is_excluded:
            excluded_gids.add(gid)
        elif is_unit_bucket:
            unit_gids.add(gid)
    return frozenset(unit_gids), frozenset(excluded_gids)


# ===========================================================================
# GREEN -- the live join reproduces the receipt's exact 17-map
# ===========================================================================


class TestLiveReceiptReproducesExact17Map:
    """The module's live wiring reproduces the W-IRIS receipt's exact partition."""

    def test_excluded_set_is_the_four_receipt_excluded(self) -> None:
        assert frozenset(_EXPECTED_EXCLUDED.values()) == EXCLUDED_SECTION_GIDS, (
            "live EXCLUDED_SECTION_GIDS must equal the 4 receipt-excluded live "
            f"GIDs; got {sorted(EXCLUDED_SECTION_GIDS)}"
        )

    def test_unit_set_is_the_thirteen_receipt_unit(self) -> None:
        assert frozenset(_EXPECTED_UNIT.values()) == UNIT_SECTION_GIDS, (
            "live UNIT_SECTION_GIDS must equal the 13 receipt-unit live GIDs; "
            f"got {sorted(UNIT_SECTION_GIDS)}"
        )

    def test_partition_cardinality(self) -> None:
        assert len(EXCLUDED_SECTION_GIDS) == 4
        assert len(UNIT_SECTION_GIDS) == 13

    def test_excluded_and_unit_are_disjoint(self) -> None:
        assert EXCLUDED_SECTION_GIDS.isdisjoint(UNIT_SECTION_GIDS)

    def test_account_review_and_error_collapse_to_excluded_not_unit(self) -> None:
        """Dual-membership collapse: each resolves to ONE live GID in excluded."""
        for name in ("Account Review", "Account Error"):
            gid = _EXPECTED_EXCLUDED[name]
            assert gid in EXCLUDED_SECTION_GIDS, f"{name} live GID must be excluded"
            assert gid not in UNIT_SECTION_GIDS, f"{name} must NOT be a unit"

    def test_excluded_gid_to_name_matches_receipt(self) -> None:
        assert {v: k for k, v in _EXPECTED_EXCLUDED.items()} == EXCLUDED_GID_TO_NAME

    def test_live_join_has_zero_blocking_and_three_divergence(self) -> None:
        result = join_section_registry(
            sr._RECEIPT_NAME_TO_GID,
            sr._VENDORED_NAME_TO_BUCKET,
            monolith_ignore_names=sr._VENDORED_MONOLITH_IGNORE_NAMES,
        )
        assert result.blocks_live_wiring is False
        divergence = {f.section_name for f in result.findings if f.kind == "taxonomy_divergence"}
        assert divergence == {"Next Steps", "Account Review", "Account Error"}, (
            f"R-REG-4 divergence must be the 3 in-code-only exclusions; got {divergence}"
        )
        # No other finding kinds on the fully-dispositioned live map.
        assert {f.kind for f in result.findings} == {"taxonomy_divergence"}


# ===========================================================================
# Two-sided wrong-BUCKET teeth on the REAL receipt map (RED-first -> GREEN)
# ===========================================================================


class TestLiveTwoSidedWrongBucket:
    """Mutate the Tier-1 correction out on the REAL receipt map -> RED; the real
    join -> GREEN. Real live GIDs (never the removed …600-624 placeholders)."""

    def test_defect_route_misbuckets_local_exclusions_red(self) -> None:
        """DEFECT: without Tier-1, Account Review / Account Error (monolith-absent
        local exclusions) route to NEITHER set -> absent from excluded -> RED."""
        _unit, defect_excluded = _route_without_tier1_correction(
            dict(sr._RECEIPT_NAME_TO_GID), dict(sr._VENDORED_NAME_TO_BUCKET)
        )
        for name in ("Account Review", "Account Error"):
            gid = _EXPECTED_EXCLUDED[name]
            assert gid not in defect_excluded, (
                f"RED: without the Tier-1 correction, {name}'s live GID is "
                "mis-bucketed out of the excluded set (routed to neither -> "
                "processed downstream)."
            )

    def test_real_join_routes_local_exclusions_to_excluded_green(self) -> None:
        """NO-DEFECT: the real join routes them to excluded, never to unit."""
        result = join_section_registry(
            sr._RECEIPT_NAME_TO_GID,
            sr._VENDORED_NAME_TO_BUCKET,
            monolith_ignore_names=sr._VENDORED_MONOLITH_IGNORE_NAMES,
        )
        for name in ("Account Review", "Account Error"):
            gid = _EXPECTED_EXCLUDED[name]
            assert gid in result.excluded_section_gids, f"GREEN: {name} -> excluded"
            assert gid not in result.unit_section_gids

    def test_defect_and_fix_disagree_on_the_same_input(self) -> None:
        """The two sides genuinely differ on the identical real input (teeth)."""
        _u, defect_excluded = _route_without_tier1_correction(
            dict(sr._RECEIPT_NAME_TO_GID), dict(sr._VENDORED_NAME_TO_BUCKET)
        )
        fixed = join_section_registry(
            sr._RECEIPT_NAME_TO_GID,
            sr._VENDORED_NAME_TO_BUCKET,
            monolith_ignore_names=sr._VENDORED_MONOLITH_IGNORE_NAMES,
        )
        assert defect_excluded != fixed.excluded_section_gids, (
            "defect and fix must produce different excluded sets on the same "
            "input, or the fixture has no teeth"
        )


# ===========================================================================
# Gate-bite (N2a): the HALT fires on the reachable live producer
# ===========================================================================


class TestGateBiteN2aHaltFires:
    """An unknown live section blocks live-wiring AND makes _build_live_registry
    -- the same producer the module calls at import -- RAISE fail-closed."""

    def test_unknown_section_flags_blocks_live_wiring(self) -> None:
        live = dict(sr._RECEIPT_NAME_TO_GID)
        live[_UNKNOWN_LIVE_NAME] = _UNKNOWN_LIVE_GID
        result = join_section_registry(
            live,
            sr._VENDORED_NAME_TO_BUCKET,
            monolith_ignore_names=sr._VENDORED_MONOLITH_IGNORE_NAMES,
        )
        assert result.blocks_live_wiring is True
        assert _UNKNOWN_LIVE_GID not in result.unit_section_gids
        assert _UNKNOWN_LIVE_GID not in result.excluded_section_gids
        blocking = [f for f in result.blocking_findings if f.section_name == _UNKNOWN_LIVE_NAME]
        assert blocking and blocking[0].kind == "live_name_no_bucket"

    def test_build_live_registry_raises_on_unknown_section_red(self) -> None:
        """The N2a HALT: the live producer raises rather than omit-and-process."""
        live = dict(sr._RECEIPT_NAME_TO_GID)
        live[_UNKNOWN_LIVE_NAME] = _UNKNOWN_LIVE_GID
        with pytest.raises(SectionRegistryError) as exc_info:
            sr._build_live_registry(
                live,
                sr._VENDORED_NAME_TO_BUCKET,
                sr._VENDORED_MONOLITH_IGNORE_NAMES,
            )
        assert _UNKNOWN_LIVE_NAME in str(exc_info.value)

    def test_build_live_registry_green_on_real_receipt(self) -> None:
        """GREEN: the real receipt disposition is complete -> no raise."""
        excluded, unit = sr._build_live_registry(
            sr._RECEIPT_NAME_TO_GID,
            sr._VENDORED_NAME_TO_BUCKET,
            sr._VENDORED_MONOLITH_IGNORE_NAMES,
        )
        assert excluded == EXCLUDED_SECTION_GIDS
        assert unit == UNIT_SECTION_GIDS


# ===========================================================================
# Fence: no removed placeholder GID (…600-624) reappears in this fixture
# ===========================================================================


def test_no_fabricated_placeholder_gid_reintroduced() -> None:
    placeholder = re.compile(r"^12010810737316[0-2][0-9]$")
    all_gids = set(_EXPECTED_EXCLUDED.values()) | set(_EXPECTED_UNIT.values()) | {_UNKNOWN_LIVE_GID}
    offenders = {g for g in all_gids if placeholder.match(g)}
    assert not offenders, f"removed placeholder GIDs must not reappear: {offenders}"
