"""Location and LocationHolder models.

Per TDD-BIZMODEL Phase 3: Location entity with address fields.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.
Per FR-MODEL-007: LocationHolder containing Address (Location) and Hours children.
Per ADR-0052: Cached bidirectional references with explicit invalidation.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.
Per PRD-0024: Updated fields to match Asana reality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.models.business.descriptors import (
    EnumField,
    HolderRef,
    IntField,
    ParentRef,
    TextField,
)
from autom8_asana.models.business.holder_factory import HolderFactory
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.hours import Hours


class Location(BusinessEntity):
    """Location entity with address fields.

    Per TDD-BIZMODEL Phase 3: Represents a physical location for a Business.
    Per PRD-0024: Updated to match actual Asana project schema.

    Example:
        location = business.location_holder.primary_location
        if location:
            print(f"Address: {location.full_address}")
    """

    NAME_CONVENTION: ClassVar[str] = "{name}"

    # Per TDD-DETECTION: Primary project GID for entity type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1200836133305610"

    # Cached upward references (ADR-0052)
    _business: Business | None = PrivateAttr(default=None)
    _location_holder: LocationHolder | None = PrivateAttr(default=None)

    # Navigation descriptors (TDD-HARDENING-C, ADR-0075)
    # IMPORTANT: Declared WITHOUT type annotations to avoid Pydantic field creation
    business = ParentRef["Business"](holder_attr="_location_holder")
    location_holder = HolderRef["LocationHolder"]()

    # _invalidate_refs() inherited from BusinessEntity (ADR-0076)

    # --- Custom Field Descriptors (TDD-SPRINT-1, ADR-0081) ---
    # Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.
    # Per ADR-0082: Fields class is auto-generated from these descriptors.
    # Per PRD-0024: Field names match actual Asana project schema.

    # Address fields - TextField (5)
    street_name = TextField()
    city = TextField()
    state = TextField()
    zip_code = TextField()
    suite = TextField()

    # Address fields - IntField (3)
    street_number = IntField(field_name="Street #")
    min_radius = IntField()
    max_radius = IntField()

    # Address fields - EnumField (2)
    country = EnumField()  # Returns enum value like "US", "CA", "SE", "AU"
    time_zone = EnumField()

    # Additional text fields (2)
    neighborhood = TextField()
    office_location = TextField()

    # --- Computed Properties ---

    @property
    def full_address(self) -> str:
        """Formatted full address.

        Per TDD: Uses street_number + street_name instead of old street field.

        Returns:
            Formatted address string combining available fields.
        """
        parts: list[str] = []

        # Street line: "123 Main Street, Suite 100"
        street_parts: list[str] = []
        if self.street_number:
            street_parts.append(str(self.street_number))
        if self.street_name:
            street_parts.append(self.street_name)
        if street_parts:
            street_line = " ".join(street_parts)
            if self.suite:
                street_line += f", {self.suite}"
            parts.append(street_line)

        # City, State, Zip
        city_state_zip: list[str] = []
        if self.city:
            city_state_zip.append(self.city)
        if self.state:
            city_state_zip.append(self.state)
        if city_state_zip:
            line = ", ".join(city_state_zip)
            if self.zip_code:
                line += f" {self.zip_code}"
            parts.append(line)
        elif self.zip_code:
            parts.append(self.zip_code)

        # Country
        if self.country:
            parts.append(self.country)

        return ", ".join(parts)


class LocationHolder(
    HolderFactory,
    child_type="Location",
    parent_ref="_location_holder",
    children_attr="_locations",
    semantic_alias="locations",
):
    """Holder task containing Location children.

    Per FR-MODEL-007: LocationHolder contains Address (Location) and Hours siblings.
    Per TDD-SPRINT-1: Migrated to HolderFactory with override for Hours sibling logic.

    Note: Hours is a sibling to Location children within LocationHolder, requiring
    special population logic via _populate_children override.

    PRIMARY_PROJECT_GID Design (FR-DET-004):
        LocationHolder intentionally has no dedicated Asana project. It is a
        **container task** (subtask of Business) that groups Location and Hours
        children, but does not have custom fields or project membership of its own.

        Detection relies on:
        - **Tier 2**: Name pattern matching ("location", "address")
        - **Tier 3**: Parent inference from Business

        Note that Location *entities* (children of LocationHolder) DO have a
        PRIMARY_PROJECT_GID ("1200836133305610") for Tier 1 detection. This is
        only the *holder* that has no dedicated project.

        The None value is intentional and correct - LocationHolder is a structural
        container, not a project member.
    """

    # Per TDD-DETECTION/FR-DET-004: LocationHolder is a container task with no dedicated
    # project. Detection uses Tier 2 (name pattern) and Tier 3 (parent inference from
    # Business). See class docstring for full explanation.
    PRIMARY_PROJECT_GID: ClassVar[str | None] = None

    # Hours reference (sibling to locations) - not managed by HolderFactory
    _hours: Hours | None = PrivateAttr(default=None)

    @property
    def primary_location(self) -> Location | None:
        """Primary location (first in list).

        Returns:
            First Location or None if no locations.
        """
        locations = self.children
        return locations[0] if locations else None

    @property
    def hours(self) -> Hours | None:
        """Hours entity (sibling to locations).

        Returns:
            Hours entity or None if not populated.
        """
        return self._hours

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate locations and hours from fetched subtasks.

        Override of HolderFactory._populate_children because LocationHolder
        has special logic for Hours sibling detection. The generic implementation
        cannot handle the Hours/Location split.

        Per TDD-SPRINT-1: Preserves Hours sibling detection logic.
        Per FR-HOLDER-008: Converts Task instances to typed children.

        Args:
            subtasks: List of Task subtasks from API.
        """
        # Import here to avoid circular import
        from autom8_asana.models.business.hours import Hours as HoursEntity

        # Sort by created_at (oldest first), then by name for stability
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )

        locations: list[Location] = []
        self._hours = None

        for task in sorted_tasks:
            # Check if this is an Hours task (name starts with "Hours")
            task_name = task.name or ""
            if task_name.startswith("Hours") or task_name.startswith("hours"):
                hours = HoursEntity.model_validate(task, from_attributes=True)
                hours._location_holder = self
                hours._business = self._business
                self._hours = hours
            else:
                location = Location.model_validate(task, from_attributes=True)
                location._location_holder = self
                location._business = self._business
                locations.append(location)

        # Store in configured attribute (per HolderFactory pattern)
        setattr(self, self.CHILDREN_ATTR, locations)

    def invalidate_cache(self) -> None:
        """Invalidate locations and hours cache.

        Override to also clear Hours sibling reference.
        """
        setattr(self, self.CHILDREN_ATTR, [])
        self._hours = None
