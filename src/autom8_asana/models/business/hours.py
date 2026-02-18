"""Hours model for business operating hours.

Per TDD-BIZMODEL Phase 3: Hours entity for business operating hours.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.
Per FR-MODEL-007: Hours is a sibling to Location within LocationHolder.
Per ADR-0052: Cached bidirectional references with explicit invalidation.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.
Per PRD-0024: Field names corrected to match Asana reality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.models.business.descriptors import (
    HolderRef,
    MultiEnumField,
    ParentRef,
)

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.location import LocationHolder


class Hours(BusinessEntity):
    """Operating hours for a Business location.

    Per TDD-BIZMODEL Phase 3: Represents business operating hours.
    Per PRD-0024: Field names are "Monday", "Tuesday", etc. (not "Monday Hours").
    Per PRD-0024: Fields are multi_enum type containing time strings.

    Example:
        hours = business.location_holder.hours
        if hours:
            print(f"Monday: {hours.monday}")  # Returns ["08:00:00", "17:00:00"]
            if hours.is_open_on("monday"):
                print("Open on Monday!")
    """

    NAME_CONVENTION: ClassVar[str] = "Hours"

    # Per TDD-DETECTION: Primary project GID for entity type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1201614578074026"

    # Cached upward references (ADR-0052)
    _business: Business | None = PrivateAttr(default=None)
    _location_holder: LocationHolder | None = PrivateAttr(default=None)

    # Navigation descriptors (TDD-HARDENING-C, ADR-0075)
    # IMPORTANT: Declared WITHOUT type annotations to avoid Pydantic field creation
    # Note: Hours doesn't have a holder, it's a sibling to Location in LocationHolder
    business = ParentRef["Business"](holder_attr="_location_holder")
    location_holder = HolderRef["LocationHolder"]()

    # _invalidate_refs() inherited from BusinessEntity (ADR-0076)

    # --- Custom Field Descriptors (TDD-SPRINT-1, ADR-0081) ---
    # Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.
    # Per ADR-0082: Fields class is auto-generated from these descriptors.
    # Per PRD-0024: Field names are "Monday", "Tuesday", etc. (not "Monday Hours").
    # Per Audit: Fields are multi_enum type containing time strings like "08:00:00".
    # Note: Sunday not found in Asana project per audit.

    monday = MultiEnumField()
    tuesday = MultiEnumField()
    wednesday = MultiEnumField()
    thursday = MultiEnumField()
    friday = MultiEnumField()
    saturday = MultiEnumField()

    # --- Helper Properties ---

    @property
    def monday_open(self) -> str | None:
        """Monday opening time (first value from multi-enum)."""
        times = self.monday
        return times[0] if times else None

    @property
    def monday_close(self) -> str | None:
        """Monday closing time (last value from multi-enum)."""
        times = self.monday
        return times[-1] if times and len(times) > 1 else None

    # --- Computed Properties ---

    @property
    def weekday_hours(self) -> dict[str, list[str]]:
        """All weekday hours as a dictionary.

        Returns:
            Dict mapping day names to list of time strings.
        """
        return {
            "monday": self.monday,
            "tuesday": self.tuesday,
            "wednesday": self.wednesday,
            "thursday": self.thursday,
            "friday": self.friday,
        }

    @property
    def all_hours(self) -> dict[str, list[str]]:
        """All hours as a dictionary.

        Per PRD-0024: Sunday not included as field doesn't exist in Asana.

        Returns:
            Dict mapping day names to list of time strings.
        """
        return {
            "monday": self.monday,
            "tuesday": self.tuesday,
            "wednesday": self.wednesday,
            "thursday": self.thursday,
            "friday": self.friday,
            "saturday": self.saturday,
        }

    def is_open_on(self, day: str) -> bool:
        """Check if business is open on a given day.

        Args:
            day: Day name (lowercase, e.g., "monday").

        Returns:
            True if hours are set for that day (non-empty list).
        """
        hours = self.all_hours.get(day.lower())
        return bool(hours)  # Empty list = closed
