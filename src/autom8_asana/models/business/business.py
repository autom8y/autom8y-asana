"""Business model - root entity of the business hierarchy.

Per TDD-BIZMODEL: Business model with 7 holder properties and 19 custom fields.
Per FR-MODEL-001: HOLDER_KEY_MAP defining 7 holder types.
Per FR-MODEL-002: Holder properties returning typed or stub holders.
Per FR-MODEL-003: Convenience shortcuts (contacts, units, address, hours).
Per FR-CASCADE-002: Cascading field definitions.
Per ADR-0050: Holder lazy loading with prefetch support.
Per TDD-PATTERNS-C: Stub holders migrated to HolderFactory pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import PrivateAttr

from autom8_asana.exceptions import InsightsValidationError
from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.models.business.contact import Contact, ContactHolder
from autom8_asana.models.business.descriptors import (
    EnumField,
    IntField,
    TextField,
)
from autom8_asana.models.business.fields import CascadingFieldDef
from autom8_asana.models.business.holder_factory import HolderFactory
from autom8_asana.models.business.mixins import (
    FinancialFieldsMixin,
    SharedCascadingFieldsMixin,
)
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.data import DataServiceClient
    from autom8_asana.clients.data.models import InsightsResponse
    from autom8_asana.models.business.activity import AccountActivity
    from autom8_asana.models.business.hours import Hours
    from autom8_asana.models.business.location import Location, LocationHolder
    from autom8_asana.models.business.unit import Unit, UnitHolder


# --- Stub Holder Classes (TDD-PATTERNS-C: Migrated to HolderFactory) ---


class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
    """Holder task containing DNA children.

    Per TDD-PATTERNS-C: Migrated to HolderFactory pattern.
    Per TDD-HARDENING-A/FR-STUB-004: Returns typed DNA children.
    Per FR-STUB-007: CHILD_TYPE set to DNA at runtime.
    Per FR-STUB-008: Bidirectional navigation refs set during _populate_children.
    """

    # Per TDD-DETECTION: Primary project GID for holder type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1167650840134033"


class ReconciliationHolder(
    HolderFactory,
    child_type="Reconciliation",
    parent_ref="_reconciliation_holder",
    semantic_alias="reconciliations",
):
    """Holder task containing Reconciliation children.

    Per TDD-PATTERNS-C: Migrated to HolderFactory pattern.
    Per TDD-HARDENING-A/FR-STUB-005: Returns typed Reconciliation children.
    Per TDD-HARDENING-C: Renamed from ReconciliationsHolder.
    Per FR-STUB-007: CHILD_TYPE set to Reconciliation at runtime.
    Per FR-STUB-008: Bidirectional navigation refs set during _populate_children.
    """

    # Per TDD-DETECTION: Primary project GID for holder type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1203404998225231"


class AssetEditHolder(
    HolderFactory,
    child_type="AssetEdit",
    parent_ref="_asset_edit_holder",
    children_attr="_asset_edits",
    semantic_alias="asset_edits",
):
    """Holder task containing AssetEdit children.

    Per TDD-PATTERNS-C: Migrated to HolderFactory pattern.
    Per FR-PREREQ-002: Returns typed AssetEdit children.
    Per TDD-RESOLUTION Appendix: AssetEditHolder returns typed AssetEdit children.
    """

    # Per TDD-DETECTION: Primary project GID for holder type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1203992664400125"


class VideographyHolder(
    HolderFactory,
    child_type="Videography",
    parent_ref="_videography_holder",
    semantic_alias="videography",
):
    """Holder task containing Videography children.

    Per TDD-PATTERNS-C: Migrated to HolderFactory pattern.
    Per TDD-HARDENING-A/FR-STUB-006: Returns typed Videography children.
    Per FR-STUB-007: CHILD_TYPE set to Videography at runtime.
    Per FR-STUB-008: Bidirectional navigation refs set during _populate_children.
    """

    # Per TDD-DETECTION: Primary project GID for holder type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1207984018149338"


class Business(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin):
    """Business entity - root of the holder hierarchy.

    Per TDD-BIZMODEL: A Business task contains 7 holder subtasks,
    each managing a collection of domain-specific child tasks.

    Per TDD-HYDRATION: Business.from_gid_async() supports full hierarchy hydration.
    Per TDD-SPRINT-1: Inherits shared fields from mixins (vertical, rep, booking_type).

    Only ContactHolder is fully typed in Phase 1. Other holders
    (Unit, Location, DNA, etc.) are deferred to Phase 2/3.

    Example:
        # Load fully hydrated Business
        business = await Business.from_gid_async(client, gid)

        # Navigate hydrated hierarchy
        for contact in business.contacts:
            print(f"Contact: {contact.full_name}")
        for unit in business.units:
            for offer in unit.offers:
                print(f"Offer: {offer.name}")

        # Load Business without hydration (metadata only)
        business = await Business.from_gid_async(client, gid, hydrate=False)
    """

    # Per TDD-DETECTION: Primary project GID for entity type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1200653012566782"

    @classmethod
    async def from_gid_async(
        cls,
        client: AsanaClient,
        gid: str,
        *,
        hydrate: bool = True,
        partial_ok: bool = False,
    ) -> Business:
        """Load Business from GID with optional hierarchy hydration.

        Per TDD-HYDRATION: Enhanced factory method with full downward hydration.
        Per TDD-HYDRATION Phase 3: Supports partial_ok for graceful failure handling.
        Per ADR-0069: Factory method is the primary API for Business loading.
        Per ADR-0070: partial_ok controls fail-fast vs partial success behavior.

        Args:
            client: AsanaClient for API calls.
            gid: Business task GID.
            hydrate: If True (default), load full hierarchy including all holders
                and their children (Contacts, Units, Offers, Processes, etc.).
                If False, only load the Business task metadata.
            partial_ok: If True, continue on partial failures during hydration
                (branches that fail will be skipped, but Business is still returned).
                If False (default), raise HydrationError on any failure.
                Note: partial_ok only affects hydration, not the initial task fetch.

        Returns:
            Business instance. If hydrate=True, all holders and children are
            populated with proper bidirectional references. If partial_ok=True
            and some branches failed, those holders will remain None.

        Raises:
            HydrationError: If hydration fails and partial_ok=False.
            NotFoundError: If Business GID does not exist.

        Example:
            # Full hydration (default - fail-fast)
            business = await Business.from_gid_async(client, gid)
            assert business.contact_holder is not None
            assert len(business.contacts) > 0

            # Skip hydration
            business = await Business.from_gid_async(client, gid, hydrate=False)
            assert business.contact_holder is None  # Not populated

            # Partial failure tolerance
            business = await Business.from_gid_async(
                client, gid, partial_ok=True
            )
            # Business returned even if some holders failed to hydrate
        """
        from autom8_asana.exceptions import HydrationError

        # Fetch Business task
        task_data = await client.tasks.get_async(gid)
        business = cls.model_validate(task_data, from_attributes=True)

        # Hydrate full hierarchy if requested
        if hydrate:
            try:
                await business._fetch_holders_async(client)
            except Exception as e:  # BROAD-CATCH: catch-all-and-degrade -- partial_ok catches any hydration failure
                if partial_ok:
                    # Log and continue with partially hydrated business
                    from autom8y_log import get_logger

                    logger = get_logger(__name__)
                    logger.warning(
                        "Hydration failed with partial_ok=True",
                        extra={"business_gid": gid, "error": str(e)},
                    )
                else:
                    # Re-raise as HydrationError if not already
                    if isinstance(e, HydrationError):
                        raise
                    raise HydrationError(
                        f"Downward hydration failed for Business {gid}: {e}",
                        entity_gid=gid,
                        entity_type="business",
                        phase="downward",
                        cause=e,
                    ) from e

        return business

    # --- Holder Detection Map ---

    # Per FR-MODEL-001: Map property_name -> (task_name, emoji_indicator)
    # Per TDD-HARDENING-C Phase 6: reconciliation_holder (singular, was reconciliations_holder)
    # DEPRECATED: Use detection system (EntityTypeInfo) for new code.
    # This map is kept for fallback when detection fails.
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "contact_holder": ("Contacts", "busts_in_silhouette"),
        "unit_holder": ("Business Units", "package"),  # Fixed: was "Units"
        "location_holder": ("Location", "round_pushpin"),
        "dna_holder": ("DNA", "dna"),
        "reconciliation_holder": ("Reconciliations", "abacus"),
        "asset_edit_holder": ("Asset Edits", "art"),  # Fixed: was "Asset Edit"
        "videography_holder": ("Videography", "video_camera"),
    }

    # --- Private Cached Holder References (ADR-0050) ---

    _contact_holder: ContactHolder | None = PrivateAttr(default=None)
    _unit_holder: UnitHolder | None = PrivateAttr(default=None)
    _location_holder: LocationHolder | None = PrivateAttr(default=None)
    _dna_holder: DNAHolder | None = PrivateAttr(default=None)
    _reconciliation_holder: ReconciliationHolder | None = PrivateAttr(default=None)
    _asset_edit_holder: AssetEditHolder | None = PrivateAttr(default=None)
    _videography_holder: VideographyHolder | None = PrivateAttr(default=None)

    # --- Custom Field Descriptors (ADR-0081, TDD-PATTERNS-A) ---
    # Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.
    # Per ADR-0082: Fields class is auto-generated from these descriptors.

    # Text fields (13)
    company_id = TextField()
    facebook_page_id = TextField()
    fallback_page_id = TextField()
    google_cal_id = TextField()
    office_phone = TextField(cascading=True)
    owner_name = TextField()
    owner_nickname = TextField()
    review_1 = TextField()
    review_2 = TextField()
    reviews_link = TextField()
    stripe_id = TextField()
    stripe_link = TextField()
    twilio_phone_num = TextField()

    # Number fields (1)
    num_reviews = IntField()

    # Enum fields (2) - vertical, booking_type inherited from mixins
    aggression_level = EnumField()
    vca_status = EnumField()

    # People fields - rep inherited from SharedCascadingFieldsMixin

    # --- Cascading Field Definitions (ADR-0054) ---

    class CascadingFields:
        """Fields that cascade from Business to descendants.

        Per FR-CASCADE-002: Business declares OFFICE_PHONE, COMPANY_ID,
        BUSINESS_NAME, PRIMARY_CONTACT_PHONE cascading definitions.

        All use allow_override=False (DEFAULT) - descendant values are
        ALWAYS overwritten during cascade.
        """

        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={"Unit", "Offer", "Process", "Contact"},
            # allow_override=False is DEFAULT - no local overrides
        )

        COMPANY_ID = CascadingFieldDef(
            name="Company ID",
            target_types=None,  # None = all descendants
            # allow_override=False is DEFAULT
        )

        BUSINESS_NAME = CascadingFieldDef(
            name="Business Name",
            target_types={"Unit", "Offer"},
            source_field="name",  # Maps from Task.name
            # allow_override=False is DEFAULT
        )

        PRIMARY_CONTACT_PHONE = CascadingFieldDef(
            name="Primary Contact Phone",
            target_types={"Unit", "Offer", "Process"},
            # allow_override=False is DEFAULT
        )

        @classmethod
        def all(cls) -> list[CascadingFieldDef]:
            """Get all cascading field definitions."""
            return [
                cls.OFFICE_PHONE,
                cls.COMPANY_ID,
                cls.BUSINESS_NAME,
                cls.PRIMARY_CONTACT_PHONE,
            ]

        @classmethod
        def get(cls, field_name: str) -> CascadingFieldDef | None:
            """Get cascading field definition by name."""
            for field_def in cls.all():
                if field_def.name == field_name:
                    return field_def
            return None

    # --- Holder Properties (FR-MODEL-002) ---

    @property
    def contact_holder(self) -> ContactHolder | None:
        """ContactHolder subtask containing Contact children.

        Returns:
            ContactHolder or None if not populated.
        """
        return self._contact_holder

    @property
    def unit_holder(self) -> UnitHolder | None:
        """UnitHolder subtask containing Unit children.

        Returns:
            UnitHolder or None if not populated.
        """
        return self._unit_holder

    @property
    def location_holder(self) -> LocationHolder | None:
        """LocationHolder subtask containing Location and Hours children.

        Per Phase 3: Returns typed LocationHolder.

        Returns:
            LocationHolder or None if not populated.
        """
        return self._location_holder

    @property
    def dna_holder(self) -> DNAHolder | None:
        """DNAHolder subtask containing DNA children.

        Per FR-HOLDER-007: Returns typed stub holder.

        Returns:
            DNAHolder or None if not populated.
        """
        return self._dna_holder

    @property
    def reconciliation_holder(self) -> ReconciliationHolder | None:
        """ReconciliationHolder subtask containing Reconciliation children.

        Per TDD-HARDENING-C Phase 6: Renamed from reconciliations_holder.

        Returns:
            ReconciliationHolder or None if not populated.
        """
        return self._reconciliation_holder

    @property
    def asset_edit_holder(self) -> AssetEditHolder | None:
        """AssetEditHolder subtask containing Asset Edit children.

        Returns:
            AssetEditHolder or None if not populated.
        """
        return self._asset_edit_holder

    @property
    def videography_holder(self) -> VideographyHolder | None:
        """VideographyHolder subtask containing Videography children.

        Returns:
            VideographyHolder or None if not populated.
        """
        return self._videography_holder

    # --- Convenience Shortcuts (FR-MODEL-003) ---

    @property
    def contacts(self) -> list[Contact]:
        """All Contact children (via ContactHolder).

        Returns:
            List of Contact entities, empty if holder not populated.
        """
        if self._contact_holder is None:
            return []
        contacts: list[Contact] = self._contact_holder.contacts  # type: ignore[attr-defined]
        return contacts

    @property
    def units(self) -> list[Unit]:
        """All Unit children (via UnitHolder).

        Returns:
            List of Unit entities, empty if holder not populated.
        """
        if self._unit_holder is None:
            return []
        units: list[Unit] = self._unit_holder.units  # type: ignore[attr-defined]
        return units

    # --- Section Activity Classification (TDD-section-activity-classifier Phase 2) ---

    @property
    def max_unit_activity(self) -> AccountActivity | None:
        """Highest activity level across all child Units.

        Uses UNIT_CLASSIFIER to classify each Unit's section, then returns
        the highest-priority activity per ACTIVITY_PRIORITY ordering
        (ACTIVE > ACTIVATING > INACTIVE > IGNORED).

        Requires the Business to be hydrated (unit_holder populated) and
        Units to have been fetched with memberships.section.name in opt_fields.

        Returns:
            AccountActivity or None if no units or no units have classifiable
            sections.
        """
        from autom8_asana.models.business.activity import ACTIVITY_PRIORITY

        units = self.units  # Uses existing convenience property
        if not units:
            return None

        activities = []
        for unit in units:
            activity = unit.account_activity
            if activity is not None:
                activities.append(activity)

        if not activities:
            return None

        # Return highest priority (lowest index in ACTIVITY_PRIORITY)
        return min(activities, key=lambda a: ACTIVITY_PRIORITY.index(a))

    @property
    def max_unit_activity(self) -> AccountActivity | None:
        """Highest activity level across all child Units.

        Uses ACTIVITY_PRIORITY ordering: ACTIVE > ACTIVATING > INACTIVE > IGNORED.
        Returns None if no units or all units have unknown sections.

        Returns:
            AccountActivity or None.
        """
        from autom8_asana.models.business.activity import ACTIVITY_PRIORITY

        activities = [
            u.account_activity for u in self.units if u.account_activity is not None
        ]
        if not activities:
            return None
        return min(activities, key=lambda a: ACTIVITY_PRIORITY.index(a))

    @property
    def address(self) -> Location | None:
        """Primary business address (via LocationHolder).

        Per Phase 3: Returns typed Location from LocationHolder.

        Returns:
            Primary Location or None if not populated.
        """
        if self._location_holder is None:
            return None
        return self._location_holder.primary_location

    @property
    def locations(self) -> list[Location]:
        """All business locations (via LocationHolder).

        Returns:
            List of Location entities, empty if holder not populated.
        """
        if self._location_holder is None:
            return []
        locs: list[Location] = self._location_holder.locations  # type: ignore[attr-defined]
        return locs

    @property
    def hours(self) -> Hours | None:
        """Business hours (via LocationHolder).

        Per Phase 3: Returns typed Hours from LocationHolder.

        Returns:
            Hours entity or None if not populated.
        """
        if self._location_holder is None:
            return None
        return self._location_holder.hours

    # --- Holder Population (ADR-0050) ---

    def _populate_holders(self, subtasks: list[Task]) -> None:
        """Populate holder properties from fetched subtasks.

        Called by SaveSession after fetching Business subtasks.
        Matches subtasks to holders via name and emoji indicators.

        Per FR-HOLDER-009: Uses name match first, emoji fallback second.

        Args:
            subtasks: List of Task subtasks from API.
        """
        for subtask in subtasks:
            holder_key = self._identify_holder(subtask)
            if holder_key:
                holder = self._create_typed_holder(holder_key, subtask)
                setattr(self, f"_{holder_key}", holder)

    def _identify_holder(self, task: Task) -> str | None:
        """Identify which holder type a task is.

        Per TDD-SPRINT-1 Phase 2: Delegates to identify_holder_type utility.
        Per Architect Decision: Uses detection system first, falls back to
        legacy HOLDER_KEY_MAP matching with logged warning.

        Args:
            task: Task to identify.

        Returns:
            Holder key name (e.g., "contact_holder") or None if not a holder.
        """
        from autom8_asana.models.business.detection import identify_holder_type

        return identify_holder_type(task, self.HOLDER_KEY_MAP, filter_to_map=False)

    def _create_typed_holder(self, holder_key: str, task: Task) -> Task:
        """Create typed holder from generic Task.

        Args:
            holder_key: Holder property name.
            task: Task to convert.

        Returns:
            Typed holder instance.
        """
        if holder_key == "contact_holder":
            holder = ContactHolder.model_validate(task, from_attributes=True)
            holder._business = self
            return holder
        elif holder_key == "unit_holder":
            # Import here to avoid circular import at module load time
            from autom8_asana.models.business.unit import UnitHolder as UH

            unit_holder = UH.model_validate(task, from_attributes=True)
            unit_holder._business = self
            return unit_holder
        elif holder_key == "location_holder":
            # Import here to avoid circular import at module load time
            from autom8_asana.models.business.location import (
                LocationHolder as LH,
            )

            location_holder = LH.model_validate(task, from_attributes=True)
            location_holder._business = self
            return location_holder
        elif holder_key == "dna_holder":
            dna_holder = DNAHolder.model_validate(task, from_attributes=True)
            dna_holder._business = self
            return dna_holder
        elif holder_key == "reconciliation_holder":
            recon_holder = ReconciliationHolder.model_validate(
                task, from_attributes=True
            )
            recon_holder._business = self
            return recon_holder
        elif holder_key == "asset_edit_holder":
            asset_holder = AssetEditHolder.model_validate(task, from_attributes=True)
            asset_holder._business = self
            return asset_holder
        elif holder_key == "videography_holder":
            video_holder = VideographyHolder.model_validate(task, from_attributes=True)
            video_holder._business = self
            return video_holder
        # Fallback: return as plain Task (should not reach here)
        return task

    async def _fetch_holders_async(self, client: AsanaClient) -> None:
        """Fetch and populate all holder subtasks with their children.

        Per TDD-HYDRATION Phase 1: Implements downward hydration for Business.

        Algorithm:
        1. Fetch Business subtasks (holders)
        2. Identify and type each holder via _populate_holders()
        3. Concurrently fetch each holder's children
        4. For Unit children, recursively fetch nested holders (OfferHolder, ProcessHolder)
        5. Set all bidirectional references

        Args:
            client: AsanaClient for API calls.

        Raises:
            HydrationError: If any fetch operation fails (fail-fast default).
        """
        import asyncio

        # Step 1: Fetch Business subtasks (holder tasks)
        # Per ADR-0094: Include detection fields for Tier 1 project membership detection
        holder_tasks = await client.tasks.subtasks_async(
            self.gid, include_detection_fields=True
        ).collect()

        # Step 2: Populate typed holders from subtasks
        self._populate_holders(holder_tasks)

        # Step 3: Build list of concurrent fetch tasks for each holder's children
        fetch_tasks: list[asyncio.Task[None]] = []

        # ContactHolder children
        if self._contact_holder:
            fetch_tasks.append(
                asyncio.create_task(
                    self._fetch_holder_children_async(
                        client, self._contact_holder, "_contacts"
                    )
                )
            )

        # UnitHolder children (special: recursive fetch for Unit nested holders)
        if self._unit_holder:
            fetch_tasks.append(
                asyncio.create_task(self._fetch_unit_holder_children_async(client))
            )

        # LocationHolder children
        if self._location_holder:
            fetch_tasks.append(
                asyncio.create_task(
                    self._fetch_holder_children_async(
                        client, self._location_holder, "_children"
                    )
                )
            )

        # Stub holders (DNA, Reconciliation, Asset Edit, Videography)
        stub_holders = [
            (self._dna_holder, "_children"),
            (self._reconciliation_holder, "_children"),
            (self._asset_edit_holder, "_asset_edits"),
            (self._videography_holder, "_children"),
        ]
        for holder, attr in stub_holders:
            if holder:
                fetch_tasks.append(
                    asyncio.create_task(
                        self._fetch_holder_children_async(client, holder, attr)
                    )
                )

        # Step 4: Execute all holder child fetches concurrently
        if fetch_tasks:
            await asyncio.gather(*fetch_tasks)

    async def _fetch_unit_holder_children_async(self, client: AsanaClient) -> None:
        """Fetch Units and their nested holders (OfferHolder, ProcessHolder).

        Per FR-DOWN-004: Units populated by UnitHolder must have their holders fetched.

        Args:
            client: AsanaClient for API calls.
        """
        import asyncio

        if not self._unit_holder:
            return

        # Fetch Unit subtasks with detection fields for type identification
        unit_tasks = await client.tasks.subtasks_async(
            self._unit_holder.gid, include_detection_fields=True
        ).collect()
        self._unit_holder._populate_children(unit_tasks)

        # Recursively fetch each Unit's holders (OfferHolder, ProcessHolder)
        unit_fetch_tasks = [
            asyncio.create_task(unit._fetch_holders_async(client))
            for unit in self._unit_holder.units  # type: ignore[attr-defined]
        ]

        if unit_fetch_tasks:
            await asyncio.gather(*unit_fetch_tasks)

    async def _fetch_holder_children_async(
        self,
        client: AsanaClient,
        holder: Task,
        children_attr: str,
    ) -> None:
        """Fetch children for a holder and populate them.

        Args:
            client: AsanaClient for API calls.
            holder: Holder task to fetch children for.
            children_attr: Name of the children attribute on the holder
                (e.g., "_contacts", "_children").
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

    # --- Insights API Integration (Story 3.1) ---

    async def get_insights_async(
        self,
        client: DataServiceClient,
        factory: str = "account",
        period: str | None = None,
        **kwargs: Any,
    ) -> InsightsResponse:
        """Fetch analytics insights for this business.

        Convenience method that wraps DataServiceClient.get_insights_async,
        automatically using this business's office_phone and vertical.

        Args:
            client: DataServiceClient instance for API calls.
            factory: InsightsFactory name (default: "account").
                Valid: account, ads, adsets, campaigns, etc.
            period: Time period preset (e.g., "lifetime", "t30", "l7").
                If None, uses client default ("lifetime").
            **kwargs: Additional arguments passed to client.get_insights_async
                (metrics, dimensions, groups, break_down, refresh, filters, etc.).

        Returns:
            InsightsResponse with data, metadata, and DataFrame conversion methods.

        Raises:
            InsightsValidationError: If office_phone or vertical is missing or empty.
            InsightsNotFoundError: No data for the PhoneVerticalPair.
            InsightsServiceError: Upstream service failure.

        Example:
            >>> async with DataServiceClient() as data_client:
            ...     business = await Business.from_gid_async(asana_client, gid)
            ...     insights = await business.get_insights_async(
            ...         data_client,
            ...         factory="account",
            ...         period="t30",
            ...     )
            ...     print(f"Total spend: {insights.data}")
        """
        # Validate required fields
        if not self.office_phone:
            raise InsightsValidationError(
                "Business office_phone is required to fetch insights",
                field="office_phone",
            )
        if not self.vertical:
            raise InsightsValidationError(
                "Business vertical is required to fetch insights",
                field="vertical",
            )

        # Build request kwargs
        request_kwargs: dict[str, Any] = {
            "factory": factory,
            "office_phone": self.office_phone,
            "vertical": self.vertical,
            **kwargs,
        }
        if period is not None:
            request_kwargs["period"] = period

        return await client.get_insights_async(**request_kwargs)
