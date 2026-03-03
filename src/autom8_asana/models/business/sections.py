"""OfferSection: section GIDs for the Business Offers project.

Maps human-readable section names to their Asana GIDs. These are
hardcoded for Phase 1; dynamic resolution via Asana API is planned
for a future phase.
"""

from __future__ import annotations

from enum import StrEnum


class OfferSection(StrEnum):
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

    @classmethod
    def from_name(cls, name: str) -> OfferSection | None:
        """Look up a member by name (case-insensitive).

        Returns None if no member matches.

        Example:
            >>> OfferSection.from_name("active")
            <OfferSection.ACTIVE: '1143843662099256'>
        """
        upper = name.upper()
        for member in cls:
            if member.name == upper:
                return member
        return None
