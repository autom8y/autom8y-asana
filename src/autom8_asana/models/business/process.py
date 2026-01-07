"""Process and ProcessHolder models.

Per TDD-BIZMODEL: Process base model supporting all pipeline types.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.
Per FR-MODEL-008: Process.process_type property for subclass determination.
Per ADR-0052: Cached upward references with explicit invalidation.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.
Per TDD-PROCESS-PIPELINE: Pipeline state tracking and transition methods.
Per ADR-0116: Composition pattern with all pipeline fields on single Process class.
Per TDD-TECH-DEBT-REMEDIATION Phase 2: Pipeline-specific field accessors.

All pipeline fields are accessible on any Process instance. Accessing a
field that doesn't exist on the underlying Asana task returns None.
"""

from __future__ import annotations

from autom8y_log import get_logger
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.models.business.descriptors import (
    DateField,
    EnumField,
    HolderRef,
    IntField,
    MultiEnumField,
    NumberField,
    PeopleField,
    TextField,
)
from autom8_asana.models.business.holder_factory import HolderFactory
from autom8_asana.models.business.mixins import (
    FinancialFieldsMixin,
    SharedCascadingFieldsMixin,
    UnitNestedHolderMixin,
)
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.unit import Unit

logger = get_logger(__name__)


class ProcessType(str, Enum):
    """Process types representing workflow stages.

    Per TDD-PROCESS-PIPELINE/ADR-0096: ProcessType includes pipeline types
    and GENERIC fallback for backward compatibility.

    Pipeline types are stakeholder-aligned:
    - SALES: Sales pipeline opportunities
    - OUTREACH: Outreach campaigns
    - ONBOARDING: Customer onboarding
    - IMPLEMENTATION: Service implementation
    - RETENTION: Customer retention
    - REACTIVATION: Customer reactivation

    GENERIC is preserved for backward compatibility with existing code.
    """

    # Pipeline types (stakeholder-aligned)
    SALES = "sales"
    OUTREACH = "outreach"
    ONBOARDING = "onboarding"
    IMPLEMENTATION = "implementation"
    RETENTION = "retention"
    REACTIVATION = "reactivation"

    # Fallback (backward compatibility)
    GENERIC = "generic"


class ProcessSection(str, Enum):
    """Standard sections in process pipeline projects.

    Per TDD-PROCESS-PIPELINE/ADR-0097: State representation via section membership.

    These values correspond to standard section names in Asana pipeline projects:
    - OPPORTUNITY: Initial lead state
    - DELAYED: Temporarily paused
    - ACTIVE: Currently working
    - SCHEDULED: Future action planned
    - CONVERTED: Success outcome
    - DID_NOT_CONVERT: Failed outcome
    - OTHER: Fallback for unrecognized/custom sections
    """

    OPPORTUNITY = "opportunity"
    DELAYED = "delayed"
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    CONVERTED = "converted"
    DID_NOT_CONVERT = "did_not_convert"
    OTHER = "other"

    @classmethod
    def from_name(cls, name: str | None) -> ProcessSection | None:
        """Match section name case-insensitively.

        Per FR-SECTION-002/003/004: Graceful matching with OTHER fallback.

        Args:
            name: Section name from Asana (e.g., "Opportunity", "Did Not Convert").

        Returns:
            ProcessSection enum value, OTHER for unrecognized, None for None input.

        Examples:
            >>> ProcessSection.from_name("Opportunity")
            ProcessSection.OPPORTUNITY
            >>> ProcessSection.from_name("did not convert")
            ProcessSection.DID_NOT_CONVERT
            >>> ProcessSection.from_name("Custom Section")
            ProcessSection.OTHER
            >>> ProcessSection.from_name(None)
            None
        """
        if name is None:
            return None

        # Normalize: lowercase, replace spaces/hyphens with underscores
        normalized = name.lower().replace(" ", "_").replace("-", "_")

        # Direct enum lookup
        for member in cls:
            if member.value == normalized:
                return member

        # Aliases for common variations
        ALIASES: dict[str, ProcessSection] = {
            "did_not_convert": cls.DID_NOT_CONVERT,
            "didnt_convert": cls.DID_NOT_CONVERT,
            "didnotconvert": cls.DID_NOT_CONVERT,
            "not_converted": cls.DID_NOT_CONVERT,
            "lost": cls.DID_NOT_CONVERT,
            "dnc": cls.DID_NOT_CONVERT,
        }

        if normalized in ALIASES:
            return ALIASES[normalized]

        return cls.OTHER


class Process(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin):
    """Process entity supporting all pipeline types.

    Per TDD-BIZMODEL: Process entities represent workflow items in pipeline projects.
    Per ADR-0116: Composition pattern - all pipeline fields on single class.
    Per TDD-TECH-DEBT-REMEDIATION Phase 2: Pipeline-specific field accessors.
    Per TDD-SPRINT-1: Inherits shared fields from mixins.
    Per TDD-SPRINT-5-CLEANUP: MRO documentation added for maintainability.

    Hierarchy:
        Business
            +-- UnitHolder
                  +-- Unit
                        +-- ProcessHolder
                              +-- Process (this entity)

    MRO (Method Resolution Order):
        Process -> BusinessEntity -> SharedCascadingFieldsMixin -> FinancialFieldsMixin
        -> Task -> BaseModel

        - BusinessEntity: Core entity behavior (_invalidate_refs, gid, etc.)
        - SharedCascadingFieldsMixin: vertical, rep descriptors
        - FinancialFieldsMixin: booking_type, mrr, weekly_ad_spend descriptors

        Note: Process does NOT use UpwardTraversalMixin (unlike Offer/Unit) because
        it has different navigation requirements (via process_holder -> unit -> business).
        Mixins come AFTER BusinessEntity so entity methods take precedence.

    Field Organization:
        Fields are organized into groups by pipeline type. All fields are
        accessible on any Process instance. Accessing a field that doesn't
        exist on the underlying Asana task returns None (graceful degradation).

        - COMMON FIELDS: Available on all process types (8 fields)
        - SALES PIPELINE FIELDS: Specific to Sales pipeline (54+ fields)
        - ONBOARDING PIPELINE FIELDS: Specific to Onboarding pipeline (33+ fields)
        - IMPLEMENTATION PIPELINE FIELDS: Specific to Implementation pipeline (28+ fields)

    PRIMARY_PROJECT_GID Design (FR-DET-002):
        Process entities belong to **dynamic pipeline projects** (Sales, Onboarding,
        Retention, etc.) rather than a single static project. Detection uses:

        1. **WorkspaceProjectRegistry**: Discovers pipeline projects at runtime
        2. **Async Tier 1**: `_detect_tier1_project_membership_async()` triggers
           lazy discovery when a task's project GID is not in the static registry
        3. **ProcessType**: Determined from project membership (e.g., Sales Pipeline
           project -> ProcessType.SALES)

        The None value here is intentional - it signals that Process detection
        should use the dynamic WorkspaceProjectRegistry lookup rather than a
        static PRIMARY_PROJECT_GID comparison.

    Example:
        for process in unit.processes:
            print(f"Process: {process.name} ({process.process_type})")

            # Access pipeline-specific fields based on type
            if process.process_type == ProcessType.SALES:
                print(f"  Deal Value: {process.deal_value}")
                print(f"  Close Date: {process.close_date}")
            elif process.process_type == ProcessType.ONBOARDING:
                print(f"  Go Live: {process.go_live_date}")
    """

    NAME_CONVENTION: ClassVar[str] = "[Process Name]"

    # Per TDD-DETECTION/FR-DET-002: Process entities belong to dynamic pipeline projects
    # (Sales, Onboarding, etc.). Detection uses WorkspaceProjectRegistry for runtime
    # discovery. See class docstring for full explanation.
    PRIMARY_PROJECT_GID: ClassVar[str | None] = None

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

    def _invalidate_refs(self, _exclude_attr: str | None = None) -> None:
        """Invalidate cached references on hierarchy change.

        Per FR-NAV-006: Clear cached navigation on hierarchy change.
        Per TDD-SPRINT-5-CLEANUP/LSK-001: Signature matches base class for LSP compliance.

        Args:
            _exclude_attr: Ignored. Clears all refs unconditionally.
        """
        self._business = None
        self._unit = None
        self._process_holder = None

    # ==========================================================================
    # COMMON FIELDS (7 fields - vertical from mixin)
    # Per ADR-0116: Fields that exist on ALL process types
    # Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.
    # Per ADR-0082: Fields class is auto-generated from these descriptors.
    # Per TDD-SPRINT-1: vertical inherited from SharedCascadingFieldsMixin
    # ==========================================================================

    # Text fields (4)
    # Note: Some field names differ from Task properties to avoid shadowing:
    # - process_completed_at (custom field) vs Task.completed_at (property)
    # - process_notes (custom field) vs Task.notes (property)
    started_at = TextField()
    process_completed_at = TextField(field_name="Process Completed At")
    process_notes = TextField(field_name="Process Notes")

    # Enum fields (2 - vertical from mixin)
    status = EnumField()
    priority = EnumField()

    # Text field - Due Date (returns string for compatibility)
    process_due_date = TextField(field_name="Due Date")

    # People field (1)
    assigned_to = PeopleField()

    # ==========================================================================
    # SALES PIPELINE FIELDS (51+ fields - mrr, weekly_ad_spend, booking_type, rep from mixins)
    # Per ADR-0116/FR-PROC-001: Sales-specific field accessors
    # Per CUSTOM-FIELD-REALITY-AUDIT.md: Field names from Sales project
    # Per TDD-SPRINT-1: mrr, weekly_ad_spend, booking_type from FinancialFieldsMixin
    # Per TDD-SPRINT-1: rep from SharedCascadingFieldsMixin
    # ==========================================================================

    # -- Sales: Financial Fields (3 - mrr, weekly_ad_spend from mixin) --
    deal_value = NumberField()
    discount = EnumField()
    solution_fee = NumberField()

    # -- Sales: People/Assignment (2 - rep from mixin) --
    closer = PeopleField()
    setter = PeopleField()

    # -- Sales: Date Fields --
    close_date = DateField()
    appt_date = DateField()
    last_outreach = DateField()
    next_outreach = DateField()
    lead_created_at = DateField()

    # -- Sales: Stage/Status Tracking (6 - booking_type from mixin) --
    score = EnumField()
    disposition = EnumField()
    delayed_reason = EnumField()
    no_show = EnumField()
    lead_trigger = EnumField()
    opportunity_type = EnumField()

    # -- Sales: Lead Information --
    lead_name = TextField()
    lead_email = TextField()
    lead_phone = TextField()
    lead_notes = TextField()

    # -- Sales: UTM/Source Tracking --
    campaign = TextField()
    source = TextField()
    medium = TextField()
    content = TextField()
    term = TextField()

    # -- Sales: Links/URLs --
    scheduling_link = TextField()
    tracking_link = TextField()

    # -- Sales: Form/ID Fields --
    form_id = TextField(field_name="Form ID")

    # -- Sales: Count/Metrics --
    outreach_count = IntField()

    # -- Sales: Business Info --
    specialty = EnumField()
    time_zone = EnumField()

    # ==========================================================================
    # ONBOARDING PIPELINE FIELDS (33+ fields)
    # Per ADR-0116/FR-PROC-002: Onboarding-specific field accessors
    # Per CUSTOM-FIELD-REALITY-AUDIT.md: Field names from Onboarding project
    # ==========================================================================

    # -- Onboarding: Status/Stage --
    onboarding_status = EnumField()
    onboarding_stage = EnumField()
    kickoff_completed = EnumField()
    account_setup_complete = EnumField()
    training_complete = EnumField()
    training_completed = EnumField()
    integration_status = EnumField()

    # -- Onboarding: Dates --
    go_live_date = DateField()
    kickoff_date = DateField()

    # -- Onboarding: People/Assignment --
    onboarding_specialist = PeopleField()
    onboarding_rep = PeopleField()

    # -- Onboarding: Notes --
    onboarding_notes = TextField()

    # ==========================================================================
    # IMPLEMENTATION PIPELINE FIELDS (28+ fields)
    # Per ADR-0116/FR-PROC-003: Implementation-specific field accessors
    # Per CUSTOM-FIELD-REALITY-AUDIT.md: Field names from Implementation project
    # ==========================================================================

    # -- Implementation: Status/Stage --
    implementation_status = EnumField()
    implementation_stage = EnumField()
    build_status = EnumField()
    creative_status = EnumField()

    # -- Implementation: Dates --
    delivery_date = DateField()
    launch_date = DateField()

    # -- Implementation: People/Assignment --
    implementation_lead = PeopleField()

    # -- Implementation: Technical --
    technical_requirements = TextField()
    integration_points = MultiEnumField()

    # --- Pipeline State (ADR-0101) ---

    @property
    def pipeline_state(self) -> ProcessSection | None:
        """Get current pipeline state from section membership.

        Per ADR-0101: Extract from canonical project membership.

        Returns:
            ProcessSection or None if not in a project with a section.
        """
        if not self.memberships:
            return None

        for membership in self.memberships:
            section_name = membership.get("section", {}).get("name")
            if section_name:
                return ProcessSection.from_name(section_name)

        return None

    # --- Process Type Detection (ADR-0101) ---

    @property
    def process_type(self) -> ProcessType:
        """Derive process type from canonical project name.

        Per ADR-0101: Match project name to ProcessType enum.

        Returns:
            ProcessType based on project name matching.
            GENERIC if no project or no matching type.
        """
        if not self.memberships:
            return ProcessType.GENERIC

        for membership in self.memberships:
            project_name = membership.get("project", {}).get("name", "").lower()

            for pt in ProcessType:
                if pt != ProcessType.GENERIC and pt.value in project_name:
                    return pt

        return ProcessType.GENERIC


class ProcessHolder(
    UnitNestedHolderMixin,
    HolderFactory,
    child_type="Process",
    parent_ref="_process_holder",
    children_attr="_processes",
    semantic_alias="processes",
):
    """Holder task containing Process children.

    Per FR-HOLDER-005: ProcessHolder extends Task with _processes PrivateAttr.
    Per TDD-SPRINT-1: Migrated to HolderFactory with override for _unit ref propagation.
    Per TDD-SPRINT-5-CLEANUP/DRY-006: Uses UnitNestedHolderMixin for business navigation.

    MRO Note:
        UnitNestedHolderMixin must come before HolderFactory in the base class
        list so its business property overrides HolderFactory.business. The mixin's
        property navigates via _unit when _business is not directly set.

    PRIMARY_PROJECT_GID Design (FR-DET-003, ADR-0115):
        ProcessHolder intentionally has no dedicated Asana project. It is a
        **container task** (subtask of Unit) that groups Process children, but
        does not have custom fields or project membership of its own.

        Detection relies on:
        - **Tier 2**: Name pattern matching ("processes", "process")
        - **Tier 3**: Parent inference from Unit (Unit's child with holder pattern)

        This is different from Process entities themselves, which DO belong to
        pipeline projects (Sales, Onboarding, etc.) and use WorkspaceProjectRegistry.

        The None value is intentional and correct - ProcessHolder is not a
        project member, it's a structural container within the Unit hierarchy.
    """

    # Per TDD-DETECTION/FR-DET-003/ADR-0115: ProcessHolder is a container task with no
    # dedicated project. Detection uses Tier 2 (name pattern) and Tier 3 (parent
    # inference from Unit). See class docstring for full explanation.
    PRIMARY_PROJECT_GID: ClassVar[str | None] = None

    # Intermediate reference for propagation to children
    _unit: Unit | None = PrivateAttr(default=None)

    @property
    def unit(self) -> Unit | None:
        """Navigate to parent Unit.

        Returns:
            Unit entity or None if not populated.
        """
        return self._unit

    # business property inherited from UnitNestedHolderMixin (DRY-006)

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate processes from fetched subtasks.

        Override of HolderFactory._populate_children to propagate intermediate
        _unit reference to children. The generic implementation only handles
        holder ref and business ref.

        Per TDD-SPRINT-1: Preserves _unit propagation behavior.

        Args:
            subtasks: List of Task subtasks from API.
        """
        # Call parent implementation to populate children with standard refs
        super()._populate_children(subtasks)

        # Propagate _unit reference to all children
        for process in self.children:
            process._unit = self._unit
