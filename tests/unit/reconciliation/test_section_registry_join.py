"""W-REG scaffold tests: dual-anchor section-registry join (SYNTHETIC fixture).

rung: authored (NOT proven). BLOCKED-on-W-IRIS. These tests exercise the pure
``join_section_registry`` function against a SYNTHETIC ``name -> GID`` map
(fabricated GIDs, never live). The function is wired NOWHERE into the live
registry path; this scaffold proves the join LOGIC ahead of the user-sovereign
W-IRIS receipt that supplies the real ``name -> live GID`` map.

H-1 (confirmed): the fix is a JOIN, not a GID-match. The monolith holds the
``name -> bucket`` taxonomy (no GIDs); live Asana holds the only real GIDs.
The SCAR-REG-001 defect was assuming the frozen placeholder GIDs equal the live
GIDs and matching on GID -- so a GID-value divergence misrouted a section. The
join matches on NAME and carries the live GID through.

RED-first two-sided teeth (R-REG-3):
  RED leg  -- a GID-match approach (the SCAR-REG-001 defect) misroutes when a
              section's synthetic live GID differs from the frozen placeholder.
  GREEN leg -- join_section_registry routes by name, so the section lands in
              the correct set regardless of GID value, with the divergence
              surfaced as a finding.

Test target: src/autom8_asana/reconciliation/section_registry.py
"""

from __future__ import annotations

from autom8_asana.reconciliation.section_registry import (
    EXCLUDED_SECTION_GIDS,
    Bucket,
    RegistryFinding,
    SectionRegistryResult,
    join_section_registry,
)

# ---------------------------------------------------------------------------
# Synthetic fixtures -- FABRICATED names/GIDs, never live.
# ---------------------------------------------------------------------------

# Monolith name -> bucket taxonomy (fabricated names ok). "Account Review" is
# the double-membership probe: the monolith taxonomy classifies it as a unit
# bucket ("active") while the in-code EXCLUDED_SECTION_NAMES also lists it. This
# mirrors the confirmed live conflict (OQ-3): "Account Review" / "Account Error"
# appear in BOTH UNIT_SECTION_GIDS and EXCLUDED_SECTION_GIDS in the module. The
# join must surface the conflict and let exclusion win (LBC-004).
_SYNTHETIC_BUCKETS: dict[str, Bucket] = {
    "Active Accounts": "active",
    "Onboarding": "activating",
    "Churned": "inactive",
    "Templates": "ignore",
    "Account Review": "active",
}

# Synthetic name -> GID. FABRICATED, deliberately NON-sequential and distinct
# from the frozen placeholder GIDs in the module so a GID-match would misroute.
_SYNTHETIC_GIDS: dict[str, str] = {
    "Active Accounts": "9000000000000001",
    "Onboarding": "9000000000000002",
    "Churned": "9000000000000003",
    "Templates": "9000000000000004",
    "Account Review": "9000000000000005",
}


def _finding_kinds(result: SectionRegistryResult) -> set[str]:
    return {f.kind for f in result.findings}


def _findings_for(result: SectionRegistryResult, name: str) -> list[RegistryFinding]:
    return [f for f in result.findings if f.section_name == name]


# ===========================================================================
# RED leg: the GID-match defect misroutes when live GID != frozen placeholder
# ===========================================================================


class TestGidMatchMisroutesRed:
    """The SCAR-REG-001 GID-match approach misroutes on GID-value divergence.

    This characterizes the DEFECT the join replaces: routing a section by
    testing GID membership in the frozen placeholder sets. "Account Review"
    must be excluded, but its synthetic live GID (9000000000000005) is NOT in
    the frozen EXCLUDED_SECTION_GIDS placeholder set, so a GID-match wrongly
    treats it as not-excluded -- a silent misroute.
    """

    def test_gid_match_fails_to_exclude_account_review(self) -> None:
        live_gid = _SYNTHETIC_GIDS["Account Review"]

        # The defect: decide exclusion by GID membership in the frozen set.
        excluded_by_gid_match = live_gid in EXCLUDED_SECTION_GIDS

        assert excluded_by_gid_match is False, (
            "RED: the synthetic live GID for 'Account Review' is NOT in the "
            "frozen placeholder EXCLUDED_SECTION_GIDS, so a GID-match wrongly "
            "concludes it is not excluded -- this is the SCAR-REG-001 misroute. "
            "The name-based join (GREEN, below) is immune to this."
        )


# ===========================================================================
# GREEN leg: join_section_registry routes by NAME, immune to GID divergence
# ===========================================================================


class TestJoinRoutesByNameGreen:
    """join_section_registry routes by name -> bucket, carrying the live GID."""

    def test_double_membership_excluded_wins_with_finding(self) -> None:
        """EC-REG-3 / OQ-3: 'Account Review' -> excluded (ignore wins) + finding."""
        result = join_section_registry(_SYNTHETIC_GIDS, _SYNTHETIC_BUCKETS)

        ar_gid = _SYNTHETIC_GIDS["Account Review"]
        assert ar_gid in result.excluded_section_gids, (
            "GREEN: 'Account Review' must land in excluded_section_gids by NAME "
            "regardless of its GID value (immune to the SCAR-REG-001 misroute)."
        )
        assert ar_gid not in result.unit_section_gids, (
            "ignore (exclusion) must WIN over any unit bucket (LBC-004)."
        )
        ar_findings = _findings_for(result, "Account Review")
        assert any(f.kind == "double_membership" for f in ar_findings), (
            f"a double_membership finding must be surfaced; got {ar_findings!r}"
        )

    def test_unit_buckets_route_to_unit_set(self) -> None:
        """active / activating / inactive buckets route to unit_section_gids."""
        result = join_section_registry(_SYNTHETIC_GIDS, _SYNTHETIC_BUCKETS)

        for name in ("Active Accounts", "Onboarding", "Churned"):
            gid = _SYNTHETIC_GIDS[name]
            assert gid in result.unit_section_gids, (
                f"{name!r} ({gid}) is a unit bucket and must route to "
                f"unit_section_gids; got {sorted(result.unit_section_gids)}"
            )
            assert gid not in result.excluded_section_gids

    def test_ignore_bucket_routes_to_excluded(self) -> None:
        """A pure 'ignore' name (Templates) routes to excluded_section_gids."""
        result = join_section_registry(_SYNTHETIC_GIDS, _SYNTHETIC_BUCKETS)

        templates_gid = _SYNTHETIC_GIDS["Templates"]
        assert templates_gid in result.excluded_section_gids
        assert templates_gid not in result.unit_section_gids


# ===========================================================================
# Divergence findings: surfaced, never silently resolved (OQ-3 posture)
# ===========================================================================


class TestDivergenceFindingsSurfaced:
    def test_live_name_no_bucket_routed_to_neither_set(self) -> None:
        """EC-REG-1: a live name with no monolith bucket is omitted from both."""
        live = dict(_SYNTHETIC_GIDS)
        live["Mystery Section"] = "9000000000000099"  # no bucket in taxonomy

        result = join_section_registry(live, _SYNTHETIC_BUCKETS)

        mystery_gid = "9000000000000099"
        assert mystery_gid not in result.unit_section_gids, (
            "EC-REG-1: an unknown live section must NOT be default-routed into "
            "the unit set (the SCAR-REG-001 silent-misroute class)."
        )
        assert mystery_gid not in result.excluded_section_gids
        mystery_findings = _findings_for(result, "Mystery Section")
        assert any(f.kind == "live_name_no_bucket" for f in mystery_findings), (
            f"a live_name_no_bucket finding must be surfaced; got {mystery_findings!r}"
        )

    def test_bucket_name_no_live_gid_recorded_as_gap(self) -> None:
        """EC-REG-2: a monolith name with no live GID is a recorded gap, no-op."""
        buckets: dict[str, Bucket] = dict(_SYNTHETIC_BUCKETS)
        buckets["Orphan Bucket"] = "active"  # no live GID for this name

        result = join_section_registry(_SYNTHETIC_GIDS, buckets)

        assert "bucket_name_no_live" in _finding_kinds(result)
        orphan_findings = _findings_for(result, "Orphan Bucket")
        assert any(f.kind == "bucket_name_no_live" for f in orphan_findings)
        # No phantom GID introduced.
        assert len(result.unit_section_gids) == len(
            {
                _SYNTHETIC_GIDS["Active Accounts"],
                _SYNTHETIC_GIDS["Onboarding"],
                _SYNTHETIC_GIDS["Churned"],
            }
        )

    def test_taxonomy_divergence_surfaced_per_name(self) -> None:
        """R-REG-4: monolith ignore-set vs in-code EXCLUDED_SECTION_NAMES drift."""
        # Monolith ignore set = {Templates} only (the documented divergence:
        # in-code EXCLUDED_SECTION_NAMES also has Next Steps / Account Review /
        # Account Error).
        monolith_ignore = frozenset({"Templates"})

        result = join_section_registry(
            _SYNTHETIC_GIDS,
            _SYNTHETIC_BUCKETS,
            monolith_ignore_names=monolith_ignore,
        )

        divergence = [f for f in result.findings if f.kind == "taxonomy_divergence"]
        diverged_names = {f.section_name for f in divergence}
        # The three names present in-code but not in the monolith ignore set.
        assert {"Next Steps", "Account Review", "Account Error"} <= diverged_names, (
            f"R-REG-4: per-name taxonomy_divergence findings expected for the "
            f"in-code-only excluded names; got {sorted(diverged_names)}"
        )

    def test_no_divergence_check_when_monolith_ignore_omitted(self) -> None:
        """Without monolith_ignore_names, no taxonomy_divergence findings fire."""
        result = join_section_registry(_SYNTHETIC_GIDS, _SYNTHETIC_BUCKETS)
        assert "taxonomy_divergence" not in _finding_kinds(result)


# ===========================================================================
# Determinism / purity: same inputs -> identical result (no I/O, no live GIDs)
# ===========================================================================


class TestJoinPurity:
    def test_join_is_deterministic(self) -> None:
        r1 = join_section_registry(_SYNTHETIC_GIDS, _SYNTHETIC_BUCKETS)
        r2 = join_section_registry(_SYNTHETIC_GIDS, _SYNTHETIC_BUCKETS)
        assert r1.unit_section_gids == r2.unit_section_gids
        assert r1.excluded_section_gids == r2.excluded_section_gids
        assert {f.kind for f in r1.findings} == {f.kind for f in r2.findings}

    def test_scaffold_uses_no_live_gids(self) -> None:
        """Fence: every GID in the synthetic fixture is fabricated (9...)."""
        assert all(g.startswith("9") for g in _SYNTHETIC_GIDS.values()), (
            "scaffold must use only fabricated synthetic GIDs (never live)"
        )
