"""Location and LocationHolder models.

Per TDD-BIZMODEL Phase 3: Location entity with address fields.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.
Per FR-MODEL-007: LocationHolder containing Address (Location) and Hours children.
Per ADR-0052: Cached bidirectional references with explicit invalidation.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity, HolderMixin
from autom8_asana.models.business.descriptors import HolderRef, ParentRef
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.hours import Hours


class Location(BusinessEntity):
    """Location entity with address fields.

    Per TDD-BIZMODEL Phase 3: Represents a physical location for a Business.
    Contains address information (street, city, state, zip, country) and
    contact information (phone).

    Example:
        location = business.location_holder.primary_location
        if location:
            print(f"Address: {location.street}, {location.city}")
    """

    NAME_CONVENTION: ClassVar[str] = "{name}"

    # Cached upward references (ADR-0052)
    _business: Business | None = PrivateAttr(default=None)
    _location_holder: LocationHolder | None = PrivateAttr(default=None)

    # Navigation descriptors (TDD-HARDENING-C, ADR-0075)
    # IMPORTANT: Declared WITHOUT type annotations to avoid Pydantic field creation
    business = ParentRef["Business"](holder_attr="_location_holder")
    location_holder = HolderRef["LocationHolder"]()

    # _invalidate_refs() inherited from BusinessEntity (ADR-0076)

    # --- Field Constants ---

    class Fields:
        """Custom field name constants for IDE discoverability.

        Per FR-FIELD-001: Inner Fields class with field name constants.
        """

        STREET = "Street"
        CITY = "City"
        STATE = "State"
        ZIP_CODE = "Zip Code"
        COUNTRY = "Country"
        PHONE = "Phone"
        LATITUDE = "Latitude"
        LONGITUDE = "Longitude"

    # --- Custom Field Accessors ---

    def _get_text_field(self, field_name: str) -> str | None:
        """Get text custom field value with proper typing."""
        value: Any = self.get_custom_fields().get(field_name)
        if value is None or isinstance(value, str):
            return value
        return str(value)

    def _get_number_field(self, field_name: str) -> float | None:
        """Get number custom field value as float."""
        value: Any = self.get_custom_fields().get(field_name)
        if value is None:
            return None
        return float(value)

    # --- Address Fields ---

    @property
    def street(self) -> str | None:
        """Street address (custom field)."""
        return self._get_text_field(self.Fields.STREET)

    @street.setter
    def street(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.STREET, value)

    @property
    def city(self) -> str | None:
        """City (custom field)."""
        return self._get_text_field(self.Fields.CITY)

    @city.setter
    def city(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.CITY, value)

    @property
    def state(self) -> str | None:
        """State/province (custom field)."""
        return self._get_text_field(self.Fields.STATE)

    @state.setter
    def state(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.STATE, value)

    @property
    def zip_code(self) -> str | None:
        """ZIP/postal code (custom field)."""
        return self._get_text_field(self.Fields.ZIP_CODE)

    @zip_code.setter
    def zip_code(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.ZIP_CODE, value)

    @property
    def country(self) -> str | None:
        """Country (custom field)."""
        return self._get_text_field(self.Fields.COUNTRY)

    @country.setter
    def country(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COUNTRY, value)

    @property
    def phone(self) -> str | None:
        """Location phone number (custom field)."""
        return self._get_text_field(self.Fields.PHONE)

    @phone.setter
    def phone(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.PHONE, value)

    @property
    def latitude(self) -> float | None:
        """Latitude coordinate (custom field)."""
        return self._get_number_field(self.Fields.LATITUDE)

    @latitude.setter
    def latitude(self, value: float | None) -> None:
        self.get_custom_fields().set(self.Fields.LATITUDE, value)

    @property
    def longitude(self) -> float | None:
        """Longitude coordinate (custom field)."""
        return self._get_number_field(self.Fields.LONGITUDE)

    @longitude.setter
    def longitude(self, value: float | None) -> None:
        self.get_custom_fields().set(self.Fields.LONGITUDE, value)

    # --- Computed Properties ---

    @property
    def full_address(self) -> str:
        """Formatted full address.

        Returns:
            Formatted address string combining available fields.
        """
        parts: list[str] = []
        if self.street:
            parts.append(self.street)
        city_state_zip: list[str] = []
        if self.city:
            city_state_zip.append(self.city)
        if self.state:
            city_state_zip.append(self.state)
        if city_state_zip:
            parts.append(", ".join(city_state_zip))
        if self.zip_code:
            parts.append(self.zip_code)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts)


class LocationHolder(Task, HolderMixin[Location]):
    """Holder task containing Location children.

    Per FR-MODEL-007: LocationHolder contains Address (Location) and Hours siblings.
    Per TDD-HARDENING-C: KEEPS _populate_children override for Hours sibling logic.

    Note: Hours is a sibling to Location children within LocationHolder, requiring
    special population logic that cannot use the generic HolderMixin implementation.
    """

    # ClassVar configuration (TDD-HARDENING-C)
    CHILD_TYPE: ClassVar[type[Location]] = Location
    PARENT_REF_NAME: ClassVar[str] = "_location_holder"
    CHILDREN_ATTR: ClassVar[str] = "_locations"

    # Children storage
    _locations: list[Location] = PrivateAttr(default_factory=list)

    # Hours reference (sibling to locations)
    _hours: Hours | None = PrivateAttr(default=None)

    # Back-reference to parent Business (ADR-0052)
    _business: Business | None = PrivateAttr(default=None)

    # NOTE: _populate_children KEPT for Hours sibling detection (TDD-HARDENING-C)

    @property
    def locations(self) -> list[Location]:
        """All Location children.

        Returns:
            List of Location entities.
        """
        return self._locations

    @property
    def primary_location(self) -> Location | None:
        """Primary location (first in list).

        Returns:
            First Location or None if no locations.
        """
        return self._locations[0] if self._locations else None

    @property
    def hours(self) -> Hours | None:
        """Hours entity (sibling to locations).

        Returns:
            Hours entity or None if not populated.
        """
        return self._hours

    @property
    def business(self) -> Business | None:
        """Navigate to parent Business.

        Returns:
            Business entity or None if not populated.
        """
        return self._business

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate locations and hours from fetched subtasks.

        NOTE: This override is KEPT per TDD-HARDENING-C because LocationHolder
        has special logic for Hours sibling detection. The generic HolderMixin
        implementation cannot handle the Hours/Location split.

        Per FR-HOLDER-008: Converts Task instances to typed children.
        Detects Hours tasks by name pattern and separates from locations.

        Args:
            subtasks: List of Task subtasks from API.
        """
        # Import here to avoid circular import
        from autom8_asana.models.business.hours import Hours

        # Sort by created_at (oldest first), then by name for stability
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )

        self._locations = []
        self._hours = None

        for task in sorted_tasks:
            # Check if this is an Hours task (name starts with clock emoji or "Hours")
            task_name = task.name or ""
            if task_name.startswith("Hours") or task_name.startswith("hours"):
                hours = Hours.model_validate(task.model_dump())
                hours._location_holder = self
                hours._business = self._business
                self._hours = hours
            else:
                location = Location.model_validate(task.model_dump())
                location._location_holder = self
                location._business = self._business
                self._locations.append(location)

    def invalidate_cache(self) -> None:
        """Invalidate locations and hours cache.

        Override of HolderMixin.invalidate_cache() to also clear Hours.
        """
        self._locations = []
        self._hours = None
