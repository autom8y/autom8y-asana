"""OfferSection: section GIDs for the Business Offers project.

Maps human-readable section names to their Asana GIDs. These are
hardcoded for Phase 1; dynamic resolution via Asana API is planned
for a future phase.
"""

from __future__ import annotations

from enum import Enum


class OfferSection(str, Enum):
    """Section GIDs for the Business Offers project (1143843662099250).

    Maps human-readable section names to their Asana GIDs. These are
    hardcoded for Phase 1; dynamic resolution via Asana API is planned
    for a future phase.

    Usage:
        >>> from autom8_asana.models.business.sections import OfferSection
        >>> section_gid = OfferSection.ACTIVE.value
        >>> # "1143843662099256"
    """

    ACTIVE = "1143843662099256"
    # Future sections can be added as GIDs are identified:
    # PAUSED = "..."
    # CANCELLED = "..."
    # ONBOARDING = "..."
