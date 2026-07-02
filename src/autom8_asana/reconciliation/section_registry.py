"""Section registry for reconciliation exclusion and classification.

Per REVIEW-reconciliation-deep-audit TC-2: This module is the single source
of truth for section exclusion constants. The name-based fallback MUST cover
all 4 excluded sections, not just the 1 in UNIT_CLASSIFIER.ignored.

W-REG (section-GID replacement): the live section GIDs are sourced from the
W-IRIS live ``GET /sections`` receipt (project 1201081073731555) and routed
into the excluded / unit frozensets by an import-time NAME join against a
vendored copy of the monolith ``BusinessUnits.SECTIONS`` taxonomy. Routing on
NAME (never on GID value) is what kills the silent-misroute class: a
GID-value divergence cannot land a section in the wrong bucket. The single
transcription surface is ``_RECEIPT_NAME_TO_GID``; ``EXCLUDED_SECTION_GIDS`` /
``UNIT_SECTION_GIDS`` / ``EXCLUDED_GID_TO_NAME`` all DERIVE from it.

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
# Asana GIDs are numeric strings, typically 16 digits. Real production GIDs are
# large integers assigned by Asana's distributed ID generator.
_ASANA_GID_PATTERN = re.compile(r"^\d{10,20}$")


def _validate_gid_set(gids: frozenset[str], registry_name: str) -> None:
    """Validate GID format and emit a startup error for malformed values.

    Every GID must match the Asana GID format (numeric, 10-20 digits). Called
    at module import time so a malformed registry surfaces at startup rather
    than silently producing wrong reconciliation results.
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


# =============================================================================
# Bucket taxonomy + dual-anchor join machinery
# =============================================================================
#
# Source-of-truth split (H-1, confirmed): the fix is a JOIN, not a GID-match.
# The monolith holds the ``name -> bucket`` taxonomy (no GIDs); live Asana holds
# the only real GIDs (the W-IRIS read, user-sovereign). The classic misroute
# defect was assuming the frozen placeholder GIDs equal the live GIDs and
# matching on GID; this join matches on NAME and carries the live GID through,
# so a GID-value divergence cannot misroute a section.

Bucket = Literal["active", "activating", "inactive", "ignore"]

# Buckets whose sections ARE processed as units (everything except "ignore").
_UNIT_BUCKETS: frozenset[Bucket] = frozenset({"active", "activating", "inactive"})


@dataclass(frozen=True)
class RegistryFinding:
    """A surfaced divergence between the live-Asana and monolith anchors.

    Findings are surfaced, never silently resolved. ``kind`` enumerates the
    divergence classes the join detects:

    - ``live_name_no_bucket``  (Tier-3 unknown): a live section name in NEITHER
      the local ``EXCLUDED_SECTION_NAMES`` NOR the monolith taxonomy. The GID is
      routed to NEITHER set (omitted, not default-routed) and this is a BLOCKING
      finding (see ``SectionRegistryResult.blocks_live_wiring``) -- defaulting an
      unknown section is the silent-misroute class.
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

    @property
    def blocking_findings(self) -> tuple[RegistryFinding, ...]:
        """Findings that MUST halt live-wiring (Tier-3 unknown sections).

        A ``live_name_no_bucket`` finding is a hard-stop: the section is known to
        NEITHER the local exclusion set NOR the monolith taxonomy, so under the
        DENYLIST processor (processes-by-default) it cannot be routed safely
        without an operator disposition. Surfacing alone is insufficient — the
        caller MUST NOT wire the result into the live registry while any
        blocking finding is present.
        """
        return tuple(f for f in self.findings if f.kind == "live_name_no_bucket")

    @property
    def blocks_live_wiring(self) -> bool:
        """True if any Tier-3 unknown-section finding forbids live-wiring."""
        return bool(self.blocking_findings)


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
    section (the silent-misroute defect class).

    Routing precedence (§6.4 three-tier fail-closed; OQ-3 resolution). Wired
    live at import via ``_build_live_registry`` below:

    - **Tier 1 (local authoritative exclusion):** ``name in
      EXCLUDED_SECTION_NAMES`` is checked FIRST, independent of monolith
      presence -> the live GID lands in ``excluded_section_gids``. This covers
      local-only exclusions (e.g. "Next Steps", "Account Review") that the
      monolith taxonomy never knew, which the previous scaffold routed to
      NEITHER set (and thus PROCESSED under the DENYLIST processor -- the
      silent-misroute class). If such a name ALSO carries a unit
      bucket in the monolith (EC-REG-3 double membership), exclusion still WINS
      and a ``double_membership`` finding is emitted (LBC-004: a section wrongly
      excluded under-counts; one wrongly processed as a unit pollutes account
      classification).
    - **Tier 2 (monolith bucket):** for names not excluded in Tier 1, the
      monolith ``ignore`` bucket -> excluded; a unit bucket
      (``active``/``activating``/``inactive``) -> ``unit_section_gids``.
    - **Tier 3 (genuine unknown):** a live name in NEITHER
      ``EXCLUDED_SECTION_NAMES`` NOR the monolith taxonomy -> routed to NEITHER
      set and surfaced as a ``live_name_no_bucket`` finding. This is a BLOCKING
      finding (see ``SectionRegistryResult.blocks_live_wiring``): surface AND
      halt -- the result MUST NOT be wired live until an operator dispositions
      the unknown section. Defaulting an unknown section is the
      silent-misroute class.
    - EC-REG-2 (monolith name, no live GID): emit ``bucket_name_no_live``;
      no-op on the sets (no GID to place), recorded as a gap.
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

    # Route each live section by NAME using the §6.4 three-tier fail-closed
    # precedence. Tier-1 (local authoritative exclusion) is checked FIRST,
    # independent of monolith presence, so a local-only exclusion (e.g.
    # "Next Steps" / "Account Review" -- present in EXCLUDED_SECTION_NAMES but
    # absent from the monolith taxonomy) fails closed toward exclusion instead
    # of falling through the bucket-None route-to-neither (the
    # silent-misroute class under the DENYLIST processor).
    for name, gid in name_to_gid.items():
        bucket = name_to_bucket.get(name)
        is_unit_bucket = bucket in _UNIT_BUCKETS

        # Tier 1: local authoritative exclusion -- checked before the monolith
        # bucket AND before the bucket-None route-to-neither.
        if name in EXCLUDED_SECTION_NAMES:
            excluded_gids.add(gid)
            if is_unit_bucket:
                # EC-REG-3 / OQ-3: the monolith classifies this excluded name as
                # a unit bucket -> double membership; exclusion still WINS
                # (LBC-004 conservative posture).
                findings.append(
                    RegistryFinding(
                        kind="double_membership",
                        section_name=name,
                        detail=(
                            f"section {name!r} maps to unit bucket {bucket!r} but "
                            "is also a local exclusion; exclusion wins (LBC-004)"
                        ),
                    )
                )
            continue

        # Tier 2: monolith bucket taxonomy.
        if bucket == "ignore":
            excluded_gids.add(gid)
        elif is_unit_bucket:
            unit_gids.add(gid)
        else:
            # Tier 3: genuine unknown -- a live name in NEITHER the local
            # exclusion set NOR the monolith taxonomy. Route to NEITHER set and
            # emit a BLOCKING live_name_no_bucket finding (surface AND halt): the
            # result MUST NOT be wired live until an operator dispositions it.
            findings.append(
                RegistryFinding(
                    kind="live_name_no_bucket",
                    section_name=name,
                    detail=(
                        f"live section {name!r} (gid={gid}) is in neither "
                        "EXCLUDED_SECTION_NAMES nor the monolith taxonomy; omitted "
                        "from both sets and BLOCKS live-wiring (not default-routed)"
                    ),
                )
            )

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


# =============================================================================
# Excluded Section NAMES (local authoritative exclusion set)
# =============================================================================
# Per REVIEW-reconciliation-deep-audit, TC-2: DO NOT use UNIT_CLASSIFIER.ignored
# as the exclusion source. It contains only {"Templates"}, missing 3 of 4
# excluded sections. Using it would silently allow units in Next Steps,
# Account Review, and Account Error through the processor.
#
# This is the Tier-1 authoritative exclusion set: it is checked FIRST in the
# join (independent of monolith presence), so local-only exclusions fail closed
# toward exclusion. It is the join key set, never a GID set.
EXCLUDED_SECTION_NAMES: frozenset[str] = frozenset(
    {
        "Templates",
        "Next Steps",
        "Account Review",
        "Account Error",
    }
)

# =============================================================================
# W-IRIS live receipt: section name -> live Asana GID (THE denominator)
# =============================================================================
# Transcribed char-for-char (matched on NAME, never on GID value) from the
# W-IRIS live GET /sections receipt for project 1201081073731555:
#   .ledge/reviews/W-IRIS-section-gid-receipt-2026-07-02.md §2 (all 17 sections)
#
# This is the ONLY place a live GID is transcribed. The excluded/unit frozensets
# and EXCLUDED_GID_TO_NAME all DERIVE from this map via the import-time join, so
# there is a single transposition surface. The 4-excluded / 13-unit partition
# and the Account Review / Account Error dual-membership collapse are enforced
# STRUCTURALLY by the Tier-1 join precedence, not by hand-maintained sets.
#
# Rows are in receipt §2 order (1..17) for a direct line-by-line diff against
# the on-disk receipt. The trailing bucket annotation is the join's Tier routing
# (excluded = Tier-1 local exclusion; the rest = Tier-2 monolith bucket).
_RECEIPT_NAME_TO_GID: dict[str, str] = {
    "Templates": "1201122816966634",  # §2 row 1  -> excluded (Tier-1)
    "Unengaged": "1201239149602679",  # §2 row 2  -> unit (inactive)
    "Engaged": "1201081073731561",  # §2 row 3  -> unit (inactive)
    "Scheduled": "1201081073731562",  # §2 row 4  -> unit (inactive)
    "Delayed": "1201081073731567",  # §2 row 5  -> unit (activating)
    "Next Steps": "1201081073731564",  # §2 row 6  -> excluded (Tier-1)
    "Onboarding": "1201081073731565",  # §2 row 7  -> unit (activating)
    "Implementing": "1201081073731566",  # §2 row 8  -> unit (activating)
    "Preview": "1201081073731569",  # §2 row 9  -> unit (activating)
    "Month 1": "1201081073731570",  # §2 row 10 -> unit (active)
    "Consulting": "1201081073731568",  # §2 row 11 -> unit (active)
    "Active": "1201081073731571",  # §2 row 12 -> unit (active)
    "Account Review": "1201081073731572",  # §2 row 13 -> excluded (Tier-1)
    "Account Error": "1201081073731573",  # §2 row 14 -> excluded (Tier-1)
    "Paused": "1201081073731574",  # §2 row 15 -> unit (inactive)
    "Cancelled": "1201081073731575",  # §2 row 16 -> unit (inactive)
    "No Start": "1201087333420106",  # §2 row 17 -> unit (inactive)
}

# =============================================================================
# Vendored monolith BusinessUnits.SECTIONS name->bucket taxonomy (READ-only)
# =============================================================================
# Vendored copy of the monolith behavioral source-of-truth for bucketing.
# Source (READ-only, NEVER live-imported at module-load -- the monolith is a
# cross-repo package that must not be a runtime import dependency):
#   autom8/apis/asana_api/objects/project/models/business_units/main.py:17-38
#
# Vendored verbatim in the monolith's bucket->names shape for a direct
# eyeball-diff against source. A drift between this copy and the live monolith
# surfaces as an R-REG-4 ``taxonomy_divergence`` finding (informational) -- it is
# NEVER auto-reconciled.
_VENDORED_MONOLITH_SECTIONS: dict[Bucket, frozenset[str]] = {
    "active": frozenset({"Month 1", "Consulting", "Active"}),
    "activating": frozenset({"Onboarding", "Implementing", "Delayed", "Preview"}),
    "inactive": frozenset({"Unengaged", "Engaged", "Scheduled", "Paused", "Cancelled", "No Start"}),
    "ignore": frozenset({"Templates"}),
}
_VENDORED_MONOLITH_IGNORE_NAMES: frozenset[str] = _VENDORED_MONOLITH_SECTIONS["ignore"]

# Inverted name -> bucket view (the shape the join consumes).
_VENDORED_NAME_TO_BUCKET: dict[str, Bucket] = {
    name: bucket for bucket, names in _VENDORED_MONOLITH_SECTIONS.items() for name in names
}


class SectionRegistryError(RuntimeError):
    """Fail-closed error raised when the live W-REG join cannot be safely wired.

    Raised at module import when the receipt x taxonomy join reports any Tier-3
    ``live_name_no_bucket`` blocking finding: a live section known to NEITHER the
    local exclusion set NOR the vendored monolith taxonomy cannot be routed
    without an operator disposition, and under the DENYLIST processor an omitted
    section is PROCESSED-by-default (the silent-misroute class). Failing import
    is fail-closed: the service will not start with a registry that would
    silently misroute a live section.
    """


def _build_live_registry(
    name_to_gid: Mapping[str, str],
    name_to_bucket: Mapping[str, Bucket],
    monolith_ignore_names: frozenset[str],
) -> tuple[frozenset[str], frozenset[str]]:
    """Produce the live ``(excluded, unit)`` GID frozensets from the receipt
    x vendored-taxonomy join.

    This is THE live-frozenset-producing path: the module-level
    ``EXCLUDED_SECTION_GIDS`` / ``UNIT_SECTION_GIDS`` are its return value and
    ``reconciliation.processor`` imports those constants, so the fail-closed
    guard placed here sits on the reachable live consumption path (not on a
    proof-only join). Routing is by NAME via ``join_section_registry``.

    Fail-closed (N2a): if the join reports ``blocks_live_wiring`` (any Tier-3
    ``live_name_no_bucket`` finding), raise ``SectionRegistryError`` so the
    module fails to import rather than shipping a registry that would silently
    process an undispositioned live section. Non-blocking findings (the R-REG-4
    ``taxonomy_divergence`` record) are surfaced at INFO, never auto-reconciled.

    Raises:
        SectionRegistryError: if the join yields any blocking finding.

    Returns:
        ``(excluded_section_gids, unit_section_gids)`` from the join result.
    """
    result = join_section_registry(
        name_to_gid,
        name_to_bucket,
        monolith_ignore_names=monolith_ignore_names,
    )

    if result.blocks_live_wiring:
        blocking_names = sorted(f.section_name for f in result.blocking_findings)
        logger.error(
            "section_registry_live_wiring_blocked",
            extra={
                "blocking_sections": blocking_names,
                "impact": "undispositioned_live_sections_would_be_processed_by_default",
            },
        )
        raise SectionRegistryError(
            f"Live section registry join is blocked by {len(blocking_names)} "
            f"unknown live section(s): {blocking_names}. A live section in neither "
            "EXCLUDED_SECTION_NAMES nor the vendored monolith taxonomy cannot be "
            "routed without an operator disposition; failing closed rather than "
            "silently processing it (the denylist processes by default)."
        )

    if result.findings:
        logger.info(
            "section_registry_join_findings_surfaced",
            extra={
                "finding_kinds": sorted({f.kind for f in result.findings}),
                "findings": [f"{f.kind}:{f.section_name}" for f in result.findings],
            },
        )

    return result.excluded_section_gids, result.unit_section_gids


# =============================================================================
# Live section-GID frozensets (derived from the W-IRIS receipt join)
# =============================================================================
# These are consumed by the DENYLIST processor. EXCLUDED_SECTION_GIDS is the
# section-level exclusion set (Templates, Next Steps, Account Review, Account
# Error). UNIT_SECTION_GIDS is the active-processing set (13 sections). Both are
# DERIVED from _RECEIPT_NAME_TO_GID x the vendored taxonomy -- no hand-typed GIDs.
EXCLUDED_SECTION_GIDS, UNIT_SECTION_GIDS = _build_live_registry(
    _RECEIPT_NAME_TO_GID,
    _VENDORED_NAME_TO_BUCKET,
    _VENDORED_MONOLITH_IGNORE_NAMES,
)

# Mapping from excluded section GID -> section name for diagnostic logging.
# Derived from EXCLUDED_SECTION_NAMES x the receipt so it cannot diverge from
# EXCLUDED_SECTION_GIDS (keys are exactly the excluded live GIDs).
EXCLUDED_GID_TO_NAME: dict[str, str] = {
    _RECEIPT_NAME_TO_GID[name]: name for name in EXCLUDED_SECTION_NAMES
}

# =============================================================================
# Startup validation
# =============================================================================
# Runs at module import time. Emits an ERROR if any derived GID is malformed
# (defensive: the live receipt GIDs are already Asana-format).
_validate_gid_set(EXCLUDED_SECTION_GIDS, "EXCLUDED_SECTION_GIDS")
_validate_gid_set(UNIT_SECTION_GIDS, "UNIT_SECTION_GIDS")
