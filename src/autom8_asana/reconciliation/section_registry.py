"""Section registry for reconciliation exclusion and classification.

Per REVIEW-reconciliation-deep-audit TC-2: This module is the single source
of truth for section exclusion constants. The name-based fallback MUST cover
all 4 excluded sections, not just the 1 in UNIT_CLASSIFIER.ignored.

Module: src/autom8_asana/reconciliation/section_registry.py
"""

from __future__ import annotations

import re

from autom8y_log import get_logger

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
