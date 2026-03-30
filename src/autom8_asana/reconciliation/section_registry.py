"""Section registry for reconciliation exclusion and classification.

Per REVIEW-reconciliation-deep-audit TC-2: This module is the single source
of truth for section exclusion constants. The name-based fallback MUST cover
all 4 excluded sections, not just the 1 in UNIT_CLASSIFIER.ignored.

Module: src/autom8_asana/reconciliation/section_registry.py
"""

from __future__ import annotations

# =============================================================================
# Excluded Section GIDs (from Asana project 1201081073731555)
# =============================================================================
# These are the section-level GIDs (not project GIDs) for sections that must
# be excluded from reconciliation processing. They correspond 1:1 with
# EXCLUDED_SECTION_NAMES below.
#
# TODO: Replace placeholder GIDs with actual Asana section GIDs once verified
# against the live Asana API. The placeholders are structurally valid 16-digit
# GID strings but are not real section identifiers.
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
# TODO: Replace placeholder GIDs with actual Asana section GIDs once verified
# against the live Asana API.
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
