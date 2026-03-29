"""Unit and UnitHolder models.

Per TDD-BIZMODEL: Unit entity with nested holders and 31 custom fields.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.
Per FR-MODEL-006: Unit.HOLDER_KEY_MAP for nested OfferHolder/ProcessHolder.
Per FR-CASCADE-003: Unit cascading fields (Platforms, Vertical, Booking Type).
Per FR-INHERIT-002: Unit inherited fields (Default Vertical from Business).
Per ADR-0052: Cached upward references with explicit invalidation.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.models.business.descriptors import (
    EnumField,
    HolderRef,
    IntField,
    MultiEnumField,
    NumberField,
    ParentRef,
    TextField,
)

# Note: PeopleField removed - rep field now inherited from SharedCascadingFieldsMixin
from autom8_asana.models.business.fields import CascadingFieldDef, InheritedFieldDef
from autom8_asana.models.business.holder_factory import HolderFactory
from autom8_asana.models.business.mixins import (
    FinancialFieldsMixin,
    SharedCascadingFieldsMixin,
    UpwardTraversalMixin,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.activity import AccountActivity
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.offer import Offer, OfferHolder
    from autom8_asana.models.business.process import Process, ProcessHolder
    from autom8_asana.models.task import Task


class Unit(
    BusinessEntity,
    SharedCascadingFieldsMixin,
    FinancialFieldsMixin,
    UpwardTraversalMixin,
):
    """Unit entity within a UnitHolder.

    Per TDD-BIZMODEL: Units represent service packages or product offerings.
    Each Unit can contain nested OfferHolder and ProcessHolder subtasks.
    Per TDD-SPRINT-1: Inherits shared fields from mixins.
    Per TDD-SPRINT-1 Phase 2: Uses UpwardTraversalMixin for to_business_async.
    Per TDD-SPRINT-5-CLEANUP: MRO documentation added for maintainability.

    Units are the key entity for determining account structure - each Unit
    typically represents a distinct service offering with its own Offers.

    MRO (Method Resolution Order):
        Unit -> BusinessEntity -> SharedCascadingFieldsMixin -> FinancialFieldsMixin
        -> UpwardTraversalMixin -> Task -> BaseModel

        - BusinessEntity: Core entity behavior (_invalidate_refs, gid, etc.)
        - SharedCascadingFieldsMixin: vertical, rep descriptors
        - FinancialFieldsMixin: booking_type, mrr, weekly_ad_spend descriptors
        - UpwardTraversalMixin: to_business_async implementation

        Mixins come AFTER BusinessEntity so entity methods take precedence.
        Field descriptors from mixins provide field access patterns.

    Example:
        for unit in business.units:
            print(f"{unit.vertical}: ${unit.mrr} MRR")
            for offer in unit.offers:
                print(f"  Offer: {offer.name}")
    """

    # Per TDD-DETECTION: Primary project GID for entity type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1201081073731555"

    # --- Nested Holder Detection (Composite Pattern) ---

    # Per FR-MODEL-006: Map property_name -> (task_name, emoji_indicator)
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "offer_holder": ("Offers", "gift"),
        "process_holder": ("Processes", "gear"),
    }

    # --- Private Cached References (ADR-0052) ---

    _business: Business | None = PrivateAttr(default=None)
    _unit_holder: UnitHolder | None = PrivateAttr(default=None)
    _offer_holder: OfferHolder | None = PrivateAttr(default=None)
    _process_holder: ProcessHolder | None = PrivateAttr(default=None)

    # Navigation descriptors (TDD-HARDENING-C, ADR-0075)
    # IMPORTANT: Declared WITHOUT type annotations to avoid Pydantic field creation
    business = ParentRef["Business"](holder_attr="_unit_holder")
    unit_holder = HolderRef["UnitHolder"]()
    offer_holder = HolderRef["OfferHolder"]()
    process_holder = HolderRef["ProcessHolder"]()

    # _invalidate_refs() inherited from BusinessEntity (ADR-0076)

    # --- Custom Field Descriptors (ADR-0081, TDD-PATTERNS-A) ---
    # Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.
    # Per ADR-0082: Fields class is auto-generated from these descriptors.
    # Per TDD-SPRINT-1: mrr, weekly_ad_spend, booking_type inherited from FinancialFieldsMixin
    # Per TDD-SPRINT-1: vertical, rep inherited from SharedCascadingFieldsMixin

    # Financial fields (5 - mrr, weekly_ad_spend, booking_type from mixin)
    discount = EnumField()  # Per PRD-0024: Enum with values like "10%", "20%", "None"
    meta_spend = NumberField()
    meta_spend_sub_id = TextField(field_name="Meta Spend Sub ID")
    tiktok_spend = NumberField()
    tiktok_spend_sub_id = TextField(field_name="Tiktok Spend Sub ID")
    solution_fee_sub_id = TextField(field_name="Solution Fee Sub ID")

    # Ad Account / Platform fields (3)
    ad_account_id = TextField(field_name="Ad Account ID")
    platforms = MultiEnumField()
    tiktok_profile = TextField()

    # Product / Service fields (3 - vertical, rep from mixins)
    products = MultiEnumField()
    languages = MultiEnumField()
    specialty = MultiEnumField()  # Per PRD-0024: Multi-enum for multiple specialties

    # Demographics / Targeting fields (8 - booking_type from mixin)
    currency = EnumField()
    radius = IntField()
    min_age = IntField()
    max_age = IntField()
    gender = MultiEnumField()  # Per PRD-0024: Multi-enum for gender targeting
    zip_code_list = TextField()
    zip_codes_radius = IntField()  # Per PRD-0024: Number field, not text
    excluded_zips = TextField()

    # Form / Lead Settings fields (8)
    form_questions = (
        MultiEnumField()
    )  # Per PRD-0024: Multi-enum for question selections
    disabled_questions = (
        MultiEnumField()
    )  # Per PRD-0024: Multi-enum for question selections
    disclaimers = MultiEnumField()  # Per PRD-0024: Multi-enum for disclaimer selections
    custom_disclaimer = TextField()
    internal_notes = TextField()  # Per PRD-0024: New field for internal notes
    sms_lead_verification = EnumField(field_name="Sms Lead Verification")
    work_email_verification = EnumField()
    filter_out_x = EnumField(field_name="Filter Out x%")  # Per PRD-0024: Enum field

    # --- Cascading Field Definitions (ADR-0054) ---

    class CascadingFields:
        """Fields that cascade from Unit to descendants (Offers, Processes).

        Per FR-CASCADE-003: Unit declares PLATFORMS, VERTICAL, BOOKING_TYPE.

        CRITICAL: allow_override=False is DEFAULT (parent always wins).
        Only PLATFORMS has allow_override=True.
        """

        PLATFORMS = CascadingFieldDef(
            name="Platforms",
            target_types={"Offer"},
            allow_override=True,  # EXPLICIT OPT-IN: Offers can keep their value
        )

        VERTICAL = CascadingFieldDef(
            name="Vertical",
            target_types={"Offer", "Process"},
            # allow_override=False is DEFAULT - Offers always get Unit's vertical
        )

        BOOKING_TYPE = CascadingFieldDef(
            name="Booking Type",
            target_types={"Offer"},
            # allow_override=False is DEFAULT
        )

        MRR = CascadingFieldDef(
            name="MRR",
            target_types={"Offer"},
            # allow_override=False is DEFAULT
        )

        WEEKLY_AD_SPEND = CascadingFieldDef(
            name="Weekly Ad Spend",
            target_types={"Offer"},
            # allow_override=False is DEFAULT
        )

        @classmethod
        def all(cls) -> list[CascadingFieldDef]:
            """Get all cascading field definitions."""
            return [
                cls.PLATFORMS,
                cls.VERTICAL,
                cls.BOOKING_TYPE,
                cls.MRR,
                cls.WEEKLY_AD_SPEND,
            ]

        @classmethod
        def get(cls, field_name: str) -> CascadingFieldDef | None:
            """Get cascading field definition by name."""
            for field_def in cls.all():
                if field_def.name == field_name:
                    return field_def
            return None

    # --- Inherited Field Definitions (ADR-0054) ---

    class InheritedFields:
        """Fields inherited from parent entities.

        Per FR-INHERIT-002: Unit inherits Default Vertical from Business.
        """

        DEFAULT_VERTICAL = InheritedFieldDef(
            name="Default Vertical",
            inherit_from=["Business"],
            allow_override=True,
            # Per truth audit: "General" does not exist as a Vertical enum option
            # in Asana. Removed invalid default. None means no fallback — the field
            # will be empty if Business has no Vertical set.
            default=None,
        )

        @classmethod
        def all(cls) -> list[InheritedFieldDef]:
            """Get all inherited field definitions."""
            return [cls.DEFAULT_VERTICAL]

    # --- Convenience Shortcuts ---

    @property
    def offers(self) -> list[Offer]:
        """All Offer children (via OfferHolder).

        Returns:
            List of Offer entities, empty if holder not populated.
        """
        if self._offer_holder is None:
            return []
        offers: list[Offer] = self._offer_holder.offers  # type: ignore[attr-defined]  # set by HolderFactory semantic_alias
        return offers

    @property
    def active_offers(self) -> list[Offer]:
        """Offers with active ads running.

        Returns:
            List of Offer entities where has_active_ads is True.
        """
        if self._offer_holder is None:
            return []
        offers: list[Offer] = self._offer_holder.offers  # type: ignore[attr-defined]  # set by HolderFactory semantic_alias
        return [o for o in offers if o.has_active_ads]

    @property
    def processes(self) -> list[Process]:
        """All Process children (via ProcessHolder).

        Returns:
            List of Process entities, empty if holder not populated.
        """
        if self._process_holder is None:
            return []
        procs: list[Process] = self._process_holder.processes  # type: ignore[attr-defined]  # set by HolderFactory semantic_alias
        return procs

    # --- Section Activity Classification (TDD-section-activity-classifier Phase 2) ---

    @property
    def account_activity(self) -> AccountActivity | None:
        """Classify this unit's section into an activity category.

        Uses UNIT_CLASSIFIER to map the unit's current section name
        to an AccountActivity value. Requires the task to have been
        fetched with memberships.section.name in opt_fields.

        Returns:
            AccountActivity or None if section is unknown or memberships
            not populated.
        """
        from autom8_asana.models.business.activity import (
            UNIT_CLASSIFIER,
            extract_section_name,
        )

        section_name = extract_section_name(self, project_gid=self.PRIMARY_PROJECT_GID)
        if section_name is None:
            return None
        return UNIT_CLASSIFIER.classify(section_name)

    # --- Upward Traversal (TDD-HYDRATION Phase 2, TDD-SPRINT-1 Phase 2) ---
    # to_business_async inherited from UpwardTraversalMixin

    def _update_refs_from_hydrated_business(self, business: Business) -> None:
        """Update Unit references to point to hydrated hierarchy.

        Per TDD-SPRINT-1 Phase 2: Hook for UpwardTraversalMixin.

        Args:
            business: The hydrated Business instance.
        """
        if business._unit_holder is not None:
            self._unit_holder = business._unit_holder
            self._business = business

    # --- Holder Population (Composite Pattern) ---

    def _populate_holders(self, subtasks: list[Task]) -> None:
        """Populate nested holder properties from fetched subtasks.

        Called by SaveSession after fetching Unit subtasks.
        Matches subtasks to holders via name and emoji indicators.

        Args:
            subtasks: List of Task subtasks from API.
        """
        # Import here to avoid circular import
        from autom8_asana.models.business.offer import OfferHolder
        from autom8_asana.models.business.process import ProcessHolder

        for subtask in subtasks:
            holder_key = self._identify_holder(subtask)
            if holder_key == "offer_holder":
                offer_holder = OfferHolder.model_validate(subtask, from_attributes=True)
                offer_holder._unit = self
                offer_holder._business = self._business
                self._offer_holder = offer_holder
            elif holder_key == "process_holder":
                process_holder = ProcessHolder.model_validate(
                    subtask, from_attributes=True
                )
                process_holder._unit = self
                process_holder._business = self._business
                self._process_holder = process_holder

    def _identify_holder(self, task: Task) -> str | None:
        """Identify which holder type a task is.

        Per TDD-SPRINT-1 Phase 2: Delegates to identify_holder_type utility.
        Per Architect Decision: Uses detection system first, falls back to
        legacy HOLDER_KEY_MAP matching with logged warning.

        Args:
            task: Task to identify.

        Returns:
            Holder key name (e.g., "offer_holder") or None if not a holder.
        """
        from autom8_asana.models.business.detection import identify_holder_type

        # filter_to_map=True ensures only Unit-level holders (offer_holder, process_holder)
        # are returned, filtering out Business-level holders
        return identify_holder_type(task, self.HOLDER_KEY_MAP, filter_to_map=True)

    async def _fetch_holders_async(self, client: AsanaClient) -> None:
        """Fetch and populate nested holder subtasks (OfferHolder, ProcessHolder).

        Per TDD-HYDRATION Phase 1: Implements downward hydration for Unit.

        Algorithm:
        1. Fetch Unit subtasks (OfferHolder, ProcessHolder)
        2. Identify and type each holder via _populate_holders()
        3. Concurrently fetch each holder's children (Offers, Processes)
        4. Set all bidirectional references

        Args:
            client: AsanaClient for API calls.

        Raises:
            HydrationError: If any fetch operation fails (fail-fast default).
        """
        import asyncio

        # Step 1: Fetch Unit subtasks (holder tasks)
        # Per ADR-0094: Include detection fields for Tier 1 project membership detection
        holder_tasks = await client.tasks.subtasks_async(
            self.gid, include_detection_fields=True
        ).collect()

        # Step 2: Populate typed holders from subtasks
        self._populate_holders(holder_tasks)

        # Step 3: Build list of concurrent fetch tasks for each holder's children
        fetch_tasks: list[asyncio.Task[None]] = []

        # OfferHolder children
        if self._offer_holder:
            fetch_tasks.append(
                asyncio.create_task(
                    self._fetch_holder_children_async(client, self._offer_holder)
                )
            )

        # ProcessHolder children
        if self._process_holder:
            fetch_tasks.append(
                asyncio.create_task(
                    self._fetch_holder_children_async(client, self._process_holder)
                )
            )

        # Step 4: Execute all holder child fetches concurrently
        if fetch_tasks:
            await asyncio.gather(*fetch_tasks)

    async def _fetch_holder_children_async(
        self,
        client: AsanaClient,
        holder: Task,
        children_attr: str = "_children",
    ) -> None:
        """Fetch children for a holder and populate them.

        Per TDD-SPRINT-5-CLEANUP/DRY-007: Signature matches Business version.

        Args:
            client: AsanaClient for API calls.
            holder: Holder task (OfferHolder or ProcessHolder) to fetch children for.
            children_attr: Fallback attribute name for holders without _populate_children.
        """
        subtasks = await client.tasks.subtasks_async(
            holder.gid, include_detection_fields=True
        ).collect()

        # Call _populate_children if available (typed holders)
        if hasattr(holder, "_populate_children"):
            holder._populate_children(subtasks)
        else:
            # Fallback for stub holders without _populate_children
            setattr(holder, children_attr, subtasks)


class UnitHolder(
    HolderFactory,
    child_type="Unit",
    parent_ref="_unit_holder",
    children_attr="_units",
    semantic_alias="units",
):
    """Holder task containing Unit children.

    Per FR-HOLDER-003: UnitHolder extends Task with _units PrivateAttr.
    Per TDD-SPRINT-1: Migrated to HolderFactory pattern.

    PRIMARY_PROJECT_GID Design (HOTFIX-entity-collision):
        UnitHolder has its own Asana project "Units" (GID 1204433992667196).
        This is REQUIRED to prevent entity resolution collision:

        Without PRIMARY_PROJECT_GID:
        - "Business Units" normalizes to entity_type "unit" -> Unit
        - "Units" also normalizes to entity_type "unit" -> overwrites Unit mapping
        - Result: Resolver returns UnitHolder GIDs instead of Unit GIDs

        With PRIMARY_PROJECT_GID:
        - Unit maps to "Business Units" (GID 1201081073731555)
        - UnitHolder maps to "Units" (GID 1204433992667196)
        - Each entity type has its own project, no collision

        Detection:
        - **Tier 1**: Project membership (PRIMARY_PROJECT_GID) - preferred
        - **Tier 2**: Name pattern matching (fallback)
        - **Tier 3**: Parent inference from Business (fallback)
    """

    # Per HOTFIX-entity-collision: UnitHolder DOES have a dedicated project ("Units",
    # GID 1204433992667196). Without this, "Units" normalizes to "unit" and collides
    # with "Business Units" (Unit entity), causing last-write-wins to return wrong GIDs.
    # Previous None value was incorrect - UnitHolder needs its own project mapping.
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1204433992667196"


# Self-register UnitHolder with HOLDER_REGISTRY (R-009)
from autom8_asana.core.registry import register_holder  # noqa: E402

register_holder("unit_holder", UnitHolder)
