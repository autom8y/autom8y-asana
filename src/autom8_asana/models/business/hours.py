"""Hours model for business operating hours.

Per TDD-BIZMODEL Phase 3: Hours entity for business operating hours.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.
Per FR-MODEL-007: Hours is a sibling to Location within LocationHolder.
Per ADR-0052: Cached bidirectional references with explicit invalidation.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.
Per ADR-0114: Hours backward compatibility with deprecated aliases.
Per PRD-0024: Field names corrected to match Asana reality.
Per TDD-SPRINT-5-CLEANUP/INH-005: Deprecated aliases consolidated via decorator.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, Callable, ClassVar

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


def _deprecated_alias(old_name: str, new_name: str) -> Callable[[type], type]:
    """Decorator to add a deprecated property alias to a class.

    Per TDD-SPRINT-5-CLEANUP/INH-005: Reduces boilerplate for deprecated aliases.

    Creates a property with `old_name` that delegates to `new_name`, emitting
    a DeprecationWarning on access.

    Args:
        old_name: Name of the deprecated property to create.
        new_name: Name of the new property to delegate to.

    Returns:
        Class decorator that adds the deprecated property.

    Example:
        @_deprecated_alias("monday_hours", "monday")
        class Hours(BusinessEntity):
            monday = MultiEnumField()
            # monday_hours property is auto-generated
    """

    def decorator(cls: type) -> type:
        def getter(self: Any) -> Any:
            warnings.warn(
                f"{old_name} is deprecated, use {new_name} instead",
                DeprecationWarning,
                stacklevel=2,
            )
            return getattr(self, new_name)

        def setter(self: Any, value: Any) -> None:
            warnings.warn(
                f"{old_name} is deprecated, use {new_name} instead",
                DeprecationWarning,
                stacklevel=2,
            )
            setattr(self, new_name, value)

        prop = property(getter, setter, doc=f"Deprecated: Use .{new_name} instead.")
        setattr(cls, old_name, prop)
        return cls

    return decorator


@_deprecated_alias("monday_hours", "monday")
@_deprecated_alias("tuesday_hours", "tuesday")
@_deprecated_alias("wednesday_hours", "wednesday")
@_deprecated_alias("thursday_hours", "thursday")
@_deprecated_alias("friday_hours", "friday")
@_deprecated_alias("saturday_hours", "saturday")
class Hours(BusinessEntity):
    """Operating hours for a Business location.

    Per TDD-BIZMODEL Phase 3: Represents business operating hours.
    Per PRD-0024: Field names are "Monday", "Tuesday", etc. (not "Monday Hours").
    Per PRD-0024: Fields are multi_enum type containing time strings.
    Per TDD-SPRINT-5-CLEANUP/INH-005: Deprecated aliases via _deprecated_alias decorator.

    Example:
        hours = business.location_holder.hours
        if hours:
            print(f"Monday: {hours.monday}")  # Returns ["08:00:00", "17:00:00"]
            if hours.is_open_on("monday"):
                print("Open on Monday!")

    Deprecated Aliases (ADR-0114):
        The following aliases emit DeprecationWarning and delegate to new names:
        - monday_hours -> monday
        - tuesday_hours -> tuesday
        - wednesday_hours -> wednesday
        - thursday_hours -> thursday
        - friday_hours -> friday
        - saturday_hours -> saturday
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

    # --- Helper Properties (Optional Enhancement per TDD) ---

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

    # Deprecated aliases (monday_hours, etc.) are generated by @_deprecated_alias decorators
    # on the class definition - see class docstring for list.

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
