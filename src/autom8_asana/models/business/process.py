"""Process and ProcessHolder models.

Per TDD-BIZMODEL: Process base model (forward-compatible for Phase 2 subclasses).
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.
Per FR-MODEL-008: Process.process_type property for subclass determination.
Per ADR-0052: Cached upward references with explicit invalidation.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.

Phase 2 will expand ProcessType enum and add specialized subclasses
(Audit, Build, Creative, etc.) with their own typed field accessors.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity, HolderMixin
from autom8_asana.models.business.descriptors import (
    EnumField,
    HolderRef,
    PeopleField,
    TextField,
)
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.unit import Unit


class ProcessType(str, Enum):
    """Process subtype enum (expanded in Phase 2).

    Per TDD-BIZMODEL: Forward-compatible enum for Process subclasses.

    Phase 2 additions will include:
    - AUDIT = "audit"
    - BUILD = "build"
    - CREATIVE = "creative"
    - ONBOARDING = "onboarding"
    - ... 24+ more
    """

    GENERIC = "generic"

    # Phase 2 subclass types (placeholders)
    # These will be enabled when subclasses are implemented
    # AUDIT = "audit"
    # BUILD = "build"
    # CREATIVE = "creative"
    # DELIVERY = "delivery"
    # ONBOARDING = "onboarding"
    # OPTIMIZATION = "optimization"
    # QA = "qa"
    # REPORTING = "reporting"
    # RESEARCH = "research"
    # SETUP = "setup"
    # STRATEGY = "strategy"
    # SUPPORT = "support"
    # TRAINING = "training"


class Process(BusinessEntity):
    """Process entity within a ProcessHolder.

    Per TDD-BIZMODEL: Base type for Phase 2 subclasses (Audit, Build, etc.).

    Hierarchy:
        Business
            +-- UnitHolder
                  +-- Unit
                        +-- ProcessHolder
                              +-- Process (this entity)

    Phase 1: All processes return as generic Process type.
    Phase 2: Subclasses (Audit, Build, Creative, etc.) with specialized fields.

    Example:
        for process in unit.processes:
            print(f"Process: {process.name} ({process.process_type})")
            if process.process_type == ProcessType.GENERIC:
                print("  (Generic process - Phase 2 will add specific types)")
    """

    NAME_CONVENTION: ClassVar[str] = "[Process Name]"

    # --- Private Cached References (ADR-0052) ---

    _business: Business | None = PrivateAttr(default=None)
    _unit: Unit | None = PrivateAttr(default=None)
    _process_holder: ProcessHolder | None = PrivateAttr(default=None)

    # Navigation descriptors (TDD-HARDENING-C, ADR-0075)
    # IMPORTANT: Declared WITHOUT type annotations to avoid Pydantic field creation
    # Note: Process has intermediate refs (_unit) so uses HolderRef only
    process_holder = HolderRef["ProcessHolder"]()

    # Complex navigation kept as properties due to multi-hop resolution

    @property
    def unit(self) -> Unit | None:
        """Navigate to containing Unit (cached).

        Returns:
            Unit entity or None if not populated.
        """
        if self._unit is None and self._process_holder is not None:
            self._unit = self._process_holder._unit
        return self._unit

    @property
    def business(self) -> Business | None:
        """Navigate to containing Business (cached).

        Per FR-NAV-004: Process provides upward navigation to Business.

        Returns:
            Business entity or None if not populated.
        """
        if self._business is None:
            unit = self.unit
            if unit is not None:
                self._business = unit.business
        return self._business

    def _invalidate_refs(self) -> None:
        """Invalidate cached references on hierarchy change.

        Per FR-NAV-006: Clear cached navigation on hierarchy change.
        """
        self._business = None
        self._unit = None
        self._process_holder = None

    # --- Custom Field Descriptors (ADR-0081, TDD-PATTERNS-A) ---
    # Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.
    # Per ADR-0082: Fields class is auto-generated from these descriptors.

    # Text fields (4)
    # Note: Some field names differ from Task properties to avoid shadowing:
    # - process_completed_at (custom field) vs Task.completed_at (property)
    # - process_notes (custom field) vs Task.notes (property)
    started_at = TextField()
    process_completed_at = TextField(field_name="Process Completed At")
    process_notes = TextField(field_name="Process Notes")

    # Enum fields (3)
    status = EnumField()
    priority = EnumField()
    vertical = EnumField()

    # Text field - Due Date (returns string for compatibility)
    process_due_date = TextField(field_name="Due Date")

    # People field (1)
    assigned_to = PeopleField()

    # --- Process Type Detection (Forward Compatible) ---

    @property
    def process_type(self) -> ProcessType:
        """Determine process type from task name or custom field.

        Per FR-MODEL-008: Forward-compatible type detection.

        Phase 1: All processes are generic.
        Phase 2: Will inspect custom field or name pattern for type.

        Returns:
            ProcessType enum value.
        """
        # Phase 1: All processes are generic
        # Phase 2: Check custom field or name pattern
        # type_field = self.get_custom_fields().get(self.Fields.PROCESS_TYPE)
        # if type_field and isinstance(type_field, dict):
        #     type_name = type_field.get("name", "").lower()
        #     try:
        #         return ProcessType(type_name)
        #     except ValueError:
        #         pass
        return ProcessType.GENERIC

class ProcessHolder(Task, HolderMixin["Process"]):
    """Holder task containing Process children.

    Per FR-HOLDER-005: ProcessHolder extends Task with _processes PrivateAttr.
    Per TDD-HARDENING-C: KEEPS _populate_children override for intermediate _unit ref.
    """

    # ClassVar configuration (TDD-HARDENING-C)
    CHILD_TYPE: ClassVar[type[Process]] = Process
    PARENT_REF_NAME: ClassVar[str] = "_process_holder"
    CHILDREN_ATTR: ClassVar[str] = "_processes"

    # Children storage
    _processes: list[Process] = PrivateAttr(default_factory=list)

    # Back-references (ADR-0052)
    _unit: Unit | None = PrivateAttr(default=None)
    _business: Business | None = PrivateAttr(default=None)

    # NOTE: _populate_children KEPT for intermediate _unit ref (TDD-HARDENING-C)

    @property
    def processes(self) -> list[Process]:
        """All Process children.

        Returns:
            List of Process entities.
        """
        return self._processes

    @property
    def unit(self) -> Unit | None:
        """Navigate to parent Unit.

        Returns:
            Unit entity or None if not populated.
        """
        return self._unit

    @property
    def business(self) -> Business | None:
        """Navigate to parent Business.

        Returns:
            Business entity or None if not populated.
        """
        if self._business is None and self._unit is not None:
            self._business = self._unit.business
        return self._business

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate processes from fetched subtasks.

        NOTE: Override KEPT because ProcessHolder has intermediate _unit ref
        that must be propagated to children. Generic HolderMixin only handles
        holder ref and business ref.

        Args:
            subtasks: List of Task subtasks from API.
        """
        # Sort by created_at (oldest first), then by name for stability
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )

        self._processes = []
        for task in sorted_tasks:
            process = Process.model_validate(task.model_dump())
            process._process_holder = self
            process._unit = self._unit
            process._business = self._business
            self._processes.append(process)
