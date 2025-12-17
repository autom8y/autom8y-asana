"""Hours model for business operating hours.

Per TDD-BIZMODEL Phase 3: Hours entity for business operating hours.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.
Per FR-MODEL-007: Hours is a sibling to Location within LocationHolder.
Per ADR-0052: Cached bidirectional references with explicit invalidation.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.models.business.descriptors import HolderRef, ParentRef

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.location import LocationHolder


class Hours(BusinessEntity):
    """Operating hours for a Business location.

    Per TDD-BIZMODEL Phase 3: Represents business operating hours.
    Contains hours for each day of the week.

    Example:
        hours = business.location_holder.hours
        if hours:
            print(f"Monday: {hours.monday_hours}")
            print(f"Sunday: {hours.sunday_hours}")
    """

    NAME_CONVENTION: ClassVar[str] = "Hours"

    # Cached upward references (ADR-0052)
    _business: Business | None = PrivateAttr(default=None)
    _location_holder: LocationHolder | None = PrivateAttr(default=None)

    # Navigation descriptors (TDD-HARDENING-C, ADR-0075)
    # IMPORTANT: Declared WITHOUT type annotations to avoid Pydantic field creation
    # Note: Hours doesn't have a holder, it's a sibling to Location in LocationHolder
    business = ParentRef["Business"](holder_attr="_location_holder")
    location_holder = HolderRef["LocationHolder"]()

    # _invalidate_refs() inherited from BusinessEntity (ADR-0076)

    # --- Field Constants ---

    class Fields:
        """Custom field name constants for IDE discoverability.

        Per FR-FIELD-001: Inner Fields class with field name constants.
        """

        MONDAY_HOURS = "Monday Hours"
        TUESDAY_HOURS = "Tuesday Hours"
        WEDNESDAY_HOURS = "Wednesday Hours"
        THURSDAY_HOURS = "Thursday Hours"
        FRIDAY_HOURS = "Friday Hours"
        SATURDAY_HOURS = "Saturday Hours"
        SUNDAY_HOURS = "Sunday Hours"
        TIMEZONE = "Timezone"
        NOTES = "Hours Notes"

    # --- Custom Field Accessors ---

    def _get_text_field(self, field_name: str) -> str | None:
        """Get text custom field value with proper typing."""
        value: Any = self.get_custom_fields().get(field_name)
        if value is None or isinstance(value, str):
            return value
        return str(value)

    # --- Hours Fields (7 days) ---

    @property
    def monday_hours(self) -> str | None:
        """Monday operating hours (custom field)."""
        return self._get_text_field(self.Fields.MONDAY_HOURS)

    @monday_hours.setter
    def monday_hours(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.MONDAY_HOURS, value)

    @property
    def tuesday_hours(self) -> str | None:
        """Tuesday operating hours (custom field)."""
        return self._get_text_field(self.Fields.TUESDAY_HOURS)

    @tuesday_hours.setter
    def tuesday_hours(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.TUESDAY_HOURS, value)

    @property
    def wednesday_hours(self) -> str | None:
        """Wednesday operating hours (custom field)."""
        return self._get_text_field(self.Fields.WEDNESDAY_HOURS)

    @wednesday_hours.setter
    def wednesday_hours(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.WEDNESDAY_HOURS, value)

    @property
    def thursday_hours(self) -> str | None:
        """Thursday operating hours (custom field)."""
        return self._get_text_field(self.Fields.THURSDAY_HOURS)

    @thursday_hours.setter
    def thursday_hours(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.THURSDAY_HOURS, value)

    @property
    def friday_hours(self) -> str | None:
        """Friday operating hours (custom field)."""
        return self._get_text_field(self.Fields.FRIDAY_HOURS)

    @friday_hours.setter
    def friday_hours(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.FRIDAY_HOURS, value)

    @property
    def saturday_hours(self) -> str | None:
        """Saturday operating hours (custom field)."""
        return self._get_text_field(self.Fields.SATURDAY_HOURS)

    @saturday_hours.setter
    def saturday_hours(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.SATURDAY_HOURS, value)

    @property
    def sunday_hours(self) -> str | None:
        """Sunday operating hours (custom field)."""
        return self._get_text_field(self.Fields.SUNDAY_HOURS)

    @sunday_hours.setter
    def sunday_hours(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.SUNDAY_HOURS, value)

    # --- Additional Fields ---

    @property
    def timezone(self) -> str | None:
        """Business timezone (custom field)."""
        return self._get_text_field(self.Fields.TIMEZONE)

    @timezone.setter
    def timezone(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.TIMEZONE, value)

    @property
    def hours_notes(self) -> str | None:
        """Additional notes about hours (custom field)."""
        return self._get_text_field(self.Fields.NOTES)

    @hours_notes.setter
    def hours_notes(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.NOTES, value)

    # --- Computed Properties ---

    @property
    def weekday_hours(self) -> dict[str, str | None]:
        """All weekday hours as a dictionary.

        Returns:
            Dict mapping day names to hours strings.
        """
        return {
            "monday": self.monday_hours,
            "tuesday": self.tuesday_hours,
            "wednesday": self.wednesday_hours,
            "thursday": self.thursday_hours,
            "friday": self.friday_hours,
        }

    @property
    def weekend_hours(self) -> dict[str, str | None]:
        """Weekend hours as a dictionary.

        Returns:
            Dict mapping day names to hours strings.
        """
        return {
            "saturday": self.saturday_hours,
            "sunday": self.sunday_hours,
        }

    @property
    def all_hours(self) -> dict[str, str | None]:
        """All hours as a dictionary.

        Returns:
            Dict mapping day names to hours strings.
        """
        return {
            "monday": self.monday_hours,
            "tuesday": self.tuesday_hours,
            "wednesday": self.wednesday_hours,
            "thursday": self.thursday_hours,
            "friday": self.friday_hours,
            "saturday": self.saturday_hours,
            "sunday": self.sunday_hours,
        }

    def is_open_on(self, day: str) -> bool:
        """Check if business is open on a given day.

        Args:
            day: Day name (lowercase, e.g., "monday").

        Returns:
            True if hours are set for that day, False otherwise.
        """
        hours = self.all_hours.get(day.lower())
        if hours is None:
            return False
        # Check for closed indicators
        closed_indicators = {"closed", "n/a", "none", ""}
        return hours.lower().strip() not in closed_indicators
