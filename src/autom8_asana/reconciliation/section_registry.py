"""Section registry for reconciliation exclusion and classification.

Per REVIEW-reconciliation-deep-audit TC-2: This module is the single source
of truth for section exclusion constants. The name-based fallback MUST cover
all 4 excluded sections, not just the 1 in UNIT_CLASSIFIER.ignored.

Module: src/autom8_asana/reconciliation/section_registry.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from autom8y_log import get_logger

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger(__name__)

# =============================================================================
# GID format validation
# =============================================================================
# Asana GIDs are numeric strings, typically 16–18 digits.
# Real production GIDs are large, non-sequential integers assigned by Asana.
_ASANA_GID_PATTERN = re.compile(r"^\d{10,20}$")

# Sequential "placeholder" detection: if the last 4 digits form an ascending
# run across all GIDs in a set, they are almost certainly fabricated.
_SEQUENTIAL_SUFFIX_THRESHOLD = 4  # 4+ sequential GIDs with consecutive suffixes


def _looks_sequential(gids: frozenset[str]) -> bool:
    """Return True if the GID set looks like fabricated sequential placeholders.

    Heuristic: sort by integer value, then check whether every consecutive
    pair differs by exactly 1.  Real Asana GIDs are not sequential.
    """
    try:
        sorted_ints = sorted(int(g) for g in gids)
    except ValueError:
        return False
    if len(sorted_ints) < 2:
        return False
    diffs = [sorted_ints[i + 1] - sorted_ints[i] for i in range(len(sorted_ints) - 1)]
    sequential_diffs = sum(1 for d in diffs if d == 1)
    return sequential_diffs >= min(_SEQUENTIAL_SUFFIX_THRESHOLD, len(diffs))


def _validate_gid_set(gids: frozenset[str], registry_name: str) -> None:
    """Validate a set of GIDs and emit startup warnings for suspicious values.

    Checks:
    1. Every GID matches the Asana GID format (numeric, 10–20 digits).
    2. The set does not look like fabricated sequential placeholders.

    This function is called at module import time so that misconfigurations
    surface at startup rather than silently producing wrong results.

    VERIFY-BEFORE-PROD: Replace placeholder GIDs with actual Asana section
    GIDs verified against the live Asana API before deploying to production.
    See sprint exit criteria in SCAN-asana-deep-triage Task 3.
    """
    invalid: list[str] = [g for g in gids if not _ASANA_GID_PATTERN.match(g)]
    if invalid:
        logger.error(
            "section_registry_invalid_gid_format",
            extra={
                "registry": registry_name,
                "invalid_gids": sorted(invalid),
                "impact": "reconciliation_may_exclude_wrong_sections",
            },
        )

    if _looks_sequential(gids):
        logger.warning(
            "section_registry_gids_appear_fabricated",
            extra={
                "registry": registry_name,
                "gids": sorted(gids),
                "reason": "consecutive_integer_values_suggest_placeholder_gids",
                # VERIFY-BEFORE-PROD: confirm actual section GIDs via Asana API
                # GET /projects/{project_gid}/sections and map names to GIDs.
                # Project GID: 1201081073731555 (per module header comment).
                "action_required": "verify_gids_against_asana_api_before_production",
            },
        )


# =============================================================================
# Excluded Section GIDs (from Asana project 1201081073731555)
# =============================================================================
# These are the section-level GIDs (not project GIDs) for sections that must
# be excluded from reconciliation processing. They correspond 1:1 with
# EXCLUDED_SECTION_NAMES below.
#
# VERIFY-BEFORE-PROD (SCAR-REG-001): These GIDs have not been verified against
# the live Asana API. They are structurally valid 16-digit numeric strings but
# are sequential placeholders. Verify via:
#   GET /projects/1201081073731555/sections
# Map section names (Templates, Next Steps, Account Review, Account Error) to
# their actual GIDs before deploying to production.
EXCLUDED_SECTION_GIDS: frozenset[str] = frozenset(
    {
        "1201081073731600",  # Templates
        "1201081073731601",  # Next Steps
        "1201081073731602",  # Account Review
        "1201081073731603",  # Account Error
    }
)

# Per REVIEW-reconciliation-deep-audit, TC-2: DO NOT use UNIT_CLASSIFIER.ignored
# as the exclusion source. It contains only {"Templates"}, missing 3 of 4
# excluded sections. Using it would silently allow units in Next Steps,
# Account Review, and Account Error through the processor.
EXCLUDED_SECTION_NAMES: frozenset[str] = frozenset(
    {
        "Templates",
        "Next Steps",
        "Account Review",
        "Account Error",
    }
)

# =============================================================================
# Unit Section GIDs (active processing sections)
# =============================================================================
# Section GIDs for unit sections that ARE processed by reconciliation.
# These are the sections where units live during active lifecycle.
#
# VERIFY-BEFORE-PROD (SCAR-REG-001): These GIDs have not been verified against
# the live Asana API. They are sequential placeholders. Verify via:
#   GET /projects/1201081073731555/sections
# Map each section name to its actual GID before deploying to production.
UNIT_SECTION_GIDS: frozenset[str] = frozenset(
    {
        "1201081073731610",  # Month 1
        "1201081073731611",  # Consulting
        "1201081073731612",  # Active
        "1201081073731613",  # Onboarding
        "1201081073731614",  # Implementing
        "1201081073731615",  # Delayed
        "1201081073731616",  # Preview
        "1201081073731617",  # Engaged
        "1201081073731618",  # Scheduled
        "1201081073731619",  # Unengaged
        "1201081073731620",  # Paused
        "1201081073731621",  # Cancelled
        "1201081073731622",  # No Start
        "1201081073731623",  # Account Review
        "1201081073731624",  # Account Error
    }
)

# Mapping from excluded section GID -> section name for diagnostic logging.
EXCLUDED_GID_TO_NAME: dict[str, str] = {
    "1201081073731600": "Templates",
    "1201081073731601": "Next Steps",
    "1201081073731602": "Account Review",
    "1201081073731603": "Account Error",
}

# =============================================================================
# Startup validation
# =============================================================================
# Runs at module import time. Emits WARNING if GIDs appear to be sequential
# placeholders that have not been verified against the live Asana API.
_validate_gid_set(EXCLUDED_SECTION_GIDS, "EXCLUDED_SECTION_GIDS")
_validate_gid_set(UNIT_SECTION_GIDS, "UNIT_SECTION_GIDS")


# =============================================================================
# W-REG: dual-anchor GID join (SCAFFOLD ONLY -- BLOCKED-on-W-IRIS)
# =============================================================================
#
# rung: authored (NOT proven). This join function is wired NOWHERE into the
# live registry path. It ships as a tested pure function awaiting the W-IRIS
# ``name -> live GID`` receipt. ZERO live GIDs appear in this scaffold; the
# frozen placeholder GIDs above are unchanged (R-REG-6 stays OUT) and the
# W-IRIS read route is not built here (R-REG-7 stays OUT).
#
# Source-of-truth split (H-1, confirmed): the fix is a JOIN, not a GID-match.
# The monolith holds the ``name -> bucket`` taxonomy (no GIDs); live Asana
# holds the only real GIDs (the W-IRIS read, user-sovereign). The classic
# SCAR-REG-001 defect was assuming the frozen placeholder GIDs equal the live
# GIDs and matching on GID; this join matches on NAME and carries the live GID
# through, so a GID-value divergence cannot misroute a section.
#
# The VERIFY-BEFORE-PROD annotations at the frozen GID sets above remain in
# force until the live W-IRIS receipt lands and the join is wired into the
# live path under a separate (un-blocked) frame.

Bucket = Literal["active", "activating", "inactive", "ignore"]

# Buckets whose sections ARE processed as units (everything except "ignore").
_UNIT_BUCKETS: frozenset[Bucket] = frozenset({"active", "activating", "inactive"})


@dataclass(frozen=True)
class RegistryFinding:
    """A surfaced divergence between the live-Asana and monolith anchors.

    Findings are surfaced, never silently resolved. ``kind`` enumerates the
    divergence classes the join detects:

    - ``live_name_no_bucket``  (EC-REG-1): a live section name has no monolith
      taxonomy bucket. The GID is routed to NEITHER set (omitted, not
      default-routed) -- defaulting an unknown section is the SCAR-REG-001
      silent-misroute class.
    - ``bucket_name_no_live``  (EC-REG-2): a monolith taxonomy name has no live
      GID. No GID to place -> a recorded gap, no set membership change.
    - ``double_membership``    (EC-REG-3 / OQ-3): a name resolves to a unit
      bucket but ``ignore`` (exclusion) WINS per the documented precedence
      below.
    - ``taxonomy_divergence``  (R-REG-4): the monolith ``ignore`` set and the
      in-code ``EXCLUDED_SECTION_NAMES`` differ; surfaced per extra name, NOT
      auto-reconciled.
    """

    kind: Literal[
        "live_name_no_bucket",
        "bucket_name_no_live",
        "double_membership",
        "taxonomy_divergence",
    ]
    section_name: str
    detail: str


@dataclass(frozen=True)
class SectionRegistryResult:
    """Result of joining the live-Asana ``name -> GID`` map with the monolith
    ``name -> bucket`` taxonomy.

    Attributes:
        unit_section_gids: live GIDs for names in unit buckets
            ({active, activating, inactive}) that are NOT excluded.
        excluded_section_gids: live GIDs for names in the ``ignore`` bucket.
        findings: surfaced divergences (never silently resolved).
    """

    unit_section_gids: frozenset[str]
    excluded_section_gids: frozenset[str]
    findings: tuple[RegistryFinding, ...]


def join_section_registry(
    name_to_gid: Mapping[str, str],
    name_to_bucket: Mapping[str, Bucket],
    *,
    monolith_ignore_names: frozenset[str] | None = None,
) -> SectionRegistryResult:
    """Join live-Asana section GIDs with the monolith name->bucket taxonomy.

    Pure, deterministic, no I/O. Routes each live section's GID into the unit
    or excluded set BY NAME (never by GID value), so a GID-value divergence
    between the frozen placeholders and the live receipt cannot misroute a
    section (the SCAR-REG-001 defect class).

    Behavior under divergence (OQ-3 resolution -- decided here, applied live
    only after the W-IRIS receipt):

    - EC-REG-1 (live name, no monolith bucket): FAIL LOUD. Emit
      ``live_name_no_bucket``; the GID is routed to NEITHER set.
    - EC-REG-2 (monolith name, no live GID): emit ``bucket_name_no_live``;
      no-op on the sets (no GID to place), recorded as a gap.
    - EC-REG-3 (double membership): a name whose bucket is a unit bucket but
      which is ALSO an excluded name -> ``ignore`` (exclusion) WINS. The GID
      lands in ``excluded_section_gids`` and a ``double_membership`` finding is
      emitted. Rationale (LBC-004): exclusion is the stronger, safety-
      preserving assertion -- a section wrongly excluded under-counts; a
      section wrongly included as a unit pollutes account classification.
    - R-REG-4 (taxonomy divergence): when ``monolith_ignore_names`` is supplied,
      each name that differs between it and the in-code ``EXCLUDED_SECTION_NAMES``
      is surfaced as a ``taxonomy_divergence`` finding -- NOT auto-reconciled.

    Args:
        name_to_gid: live section-name -> GID (W-IRIS receipt; synthetic in
            the scaffold tests). The source of the only real GIDs.
        name_to_bucket: monolith section-name -> bucket taxonomy.
        monolith_ignore_names: optional monolith ``ignore`` name set, for the
            R-REG-4 divergence check against in-code ``EXCLUDED_SECTION_NAMES``.

    Returns:
        SectionRegistryResult with routed GID sets and surfaced findings.
    """
    unit_gids: set[str] = set()
    excluded_gids: set[str] = set()
    findings: list[RegistryFinding] = []

    # EC-REG-2: monolith names with no live GID -- recorded gaps.
    for name in name_to_bucket:
        if name not in name_to_gid:
            findings.append(
                RegistryFinding(
                    kind="bucket_name_no_live",
                    section_name=name,
                    detail=(
                        f"monolith taxonomy name {name!r} has no live Asana GID; "
                        "no section to route (recorded gap)"
                    ),
                )
            )

    # Route each live section by NAME -> bucket.
    for name, gid in name_to_gid.items():
        bucket = name_to_bucket.get(name)
        if bucket is None:
            # EC-REG-1: live name absent from monolith taxonomy. Route to
            # NEITHER set -- do not default-route an unknown section.
            findings.append(
                RegistryFinding(
                    kind="live_name_no_bucket",
                    section_name=name,
                    detail=(
                        f"live section {name!r} (gid={gid}) has no monolith "
                        "taxonomy bucket; omitted from both sets (not default-routed)"
                    ),
                )
            )
            continue

        is_excluded = (bucket == "ignore") or (name in EXCLUDED_SECTION_NAMES)
        is_unit_bucket = bucket in _UNIT_BUCKETS

        if is_excluded and is_unit_bucket:
            # EC-REG-3 / OQ-3: double membership -> ignore (exclusion) WINS.
            findings.append(
                RegistryFinding(
                    kind="double_membership",
                    section_name=name,
                    detail=(
                        f"section {name!r} maps to unit bucket {bucket!r} but is "
                        "also excluded; exclusion wins (LBC-004 conservative posture)"
                    ),
                )
            )
            excluded_gids.add(gid)
        elif is_excluded:
            excluded_gids.add(gid)
        elif is_unit_bucket:
            unit_gids.add(gid)
        # Any other (unknown) bucket value would have failed the Bucket Literal
        # at the type boundary; no silent default here.

    # R-REG-4: surface monolith-ignore vs in-code EXCLUDED_SECTION_NAMES drift.
    if monolith_ignore_names is not None:
        for name in monolith_ignore_names ^ EXCLUDED_SECTION_NAMES:
            side = (
                "monolith ignore-set"
                if name in monolith_ignore_names
                else "in-code EXCLUDED_SECTION_NAMES"
            )
            findings.append(
                RegistryFinding(
                    kind="taxonomy_divergence",
                    section_name=name,
                    detail=(
                        f"{name!r} present only in {side}; taxonomy sources "
                        "diverge (surfaced, not auto-reconciled)"
                    ),
                )
            )

    return SectionRegistryResult(
        unit_section_gids=frozenset(unit_gids),
        excluded_section_gids=frozenset(excluded_gids),
        findings=tuple(findings),
    )
