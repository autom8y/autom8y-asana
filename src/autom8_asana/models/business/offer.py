"""Offer and OfferHolder models.

Per TDD-BIZMODEL: Offer entity with 39 custom fields - the unit of work for ad status.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.
Per FR-MODEL-007: Offer.has_active_ads property for ad status determination.
Per FR-INHERIT-003: Offer inherits Vertical, Platforms from Unit.
Per ADR-0052: Cached upward references with explicit invalidation.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity, HolderMixin
from autom8_asana.models.business.descriptors import (
    EnumField,
    HolderRef,
    IntField,
    MultiEnumField,
    NumberField,
    PeopleField,
    TextField,
)
from autom8_asana.models.business.fields import InheritedFieldDef
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.unit import Unit


class Offer(BusinessEntity):
    """Offer entity within an OfferHolder.

    Per TDD-BIZMODEL: Offers represent individual ad campaigns/placements
    and are the unit of work for determining account status (are ads running).

    Hierarchy:
        Business
            +-- UnitHolder
                  +-- Unit
                        +-- OfferHolder
                              +-- Offer (this entity)

    Example:
        for offer in unit.offers:
            if offer.has_active_ads:
                print(f"Active: {offer.name} - ${offer.weekly_ad_spend}/week")
    """

    NAME_CONVENTION: ClassVar[str] = "[Offer Name]"

    # --- Private Cached References (ADR-0052) ---

    _business: Business | None = PrivateAttr(default=None)
    _unit: Unit | None = PrivateAttr(default=None)
    _offer_holder: OfferHolder | None = PrivateAttr(default=None)

    # Navigation descriptors (TDD-HARDENING-C, ADR-0075)
    # IMPORTANT: Declared WITHOUT type annotations to avoid Pydantic field creation
    # Note: Offer has intermediate refs (_unit) so uses HolderRef only
    offer_holder = HolderRef["OfferHolder"]()

    # Complex navigation kept as properties due to multi-hop resolution

    @property
    def unit(self) -> Unit | None:
        """Navigate to containing Unit (cached).

        Returns:
            Unit entity or None if not populated.
        """
        if self._unit is None and self._offer_holder is not None:
            self._unit = self._offer_holder._unit
        return self._unit

    @property
    def business(self) -> Business | None:
        """Navigate to containing Business (cached).

        Per FR-NAV-003: Offer provides upward navigation to Business.

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
        self._offer_holder = None

    # --- Custom Field Descriptors (ADR-0081, TDD-PATTERNS-A) ---
    # Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.
    # Per ADR-0082: Fields class is auto-generated from these descriptors.

    # Financial fields (5)
    mrr = NumberField(field_name="MRR")
    cost = NumberField()
    weekly_ad_spend = NumberField()
    voucher_value = NumberField()
    budget_allocation = NumberField()

    # Ad Platform ID fields (7)
    ad_id = TextField(field_name="Ad ID")
    ad_set_id = TextField(field_name="Ad Set ID")
    campaign_id = TextField(field_name="Campaign ID")
    asset_id = TextField(field_name="Asset ID")
    ad_account_url = TextField(field_name="Ad Account URL")
    active_ads_url = TextField(field_name="Active Ads URL")
    platforms = MultiEnumField()

    # Content fields (8)
    offer_headline = TextField()
    included_item_1 = TextField()
    included_item_2 = TextField()
    included_item_3 = TextField()
    landing_page_url = TextField(field_name="Landing Page URL")
    preview_link = TextField()
    lead_testing_link = TextField()
    num_ai_copies = IntField(field_name="Num AI Copies")

    # Configuration fields (9)
    form_id = TextField(field_name="Form ID")
    language = EnumField()
    specialty = EnumField()
    vertical = EnumField()
    targeting = TextField()
    targeting_strategies = MultiEnumField()
    optimize_for = EnumField()
    campaign_type = EnumField()
    office_phone = TextField()

    # Scheduling fields (4)
    appt_duration = IntField()
    calendar_duration = IntField()
    custom_cal_url = TextField(field_name="Custom Cal URL")
    offer_schedule_link = TextField()

    # Notes fields (2)
    internal_notes = TextField()
    external_notes = TextField()

    # Metadata fields (4)
    offer_id = TextField(field_name="Offer ID")
    algo_version = TextField()
    triggered_by = TextField()
    rep = PeopleField()

    # --- Inherited Field Definitions (ADR-0054) ---

    class InheritedFields:
        """Fields inherited from parent entities.

        Per FR-INHERIT-003: Offer inherits Vertical, Platforms from Unit.
        """

        VERTICAL = InheritedFieldDef(
            name="Vertical",
            inherit_from=["Unit", "Business"],
            allow_override=True,
        )

        PLATFORMS = InheritedFieldDef(
            name="Platforms",
            inherit_from=["Unit"],
            allow_override=True,
        )

        @classmethod
        def all(cls) -> list[InheritedFieldDef]:
            """Get all inherited field definitions."""
            return [cls.VERTICAL, cls.PLATFORMS]

    # --- Upward Traversal (TDD-HYDRATION Phase 2) ---

    async def to_business_async(
        self,
        client: AsanaClient,
        *,
        hydrate_full: bool = True,
        partial_ok: bool = False,
    ) -> Business:
        """Navigate to containing Business through hierarchy and optionally hydrate.

        Per ADR-0069: Instance method for upward navigation.
        Per FR-UP-002: Offer upward traversal.
        Per ADR-0070: partial_ok controls fail-fast vs partial success behavior.

        Path: Offer -> OfferHolder -> Unit -> UnitHolder -> Business (4 levels up)

        This method traverses the parent chain through the full hierarchy
        to find the Business root, then optionally hydrates the full Business
        hierarchy. After hydration, this Offer instance's references are
        updated to point to the hydrated hierarchy.

        Args:
            client: AsanaClient for API calls.
            hydrate_full: If True (default), hydrate full Business hierarchy
                after finding it. If False, only populates the path traversed.
            partial_ok: If True, continue on partial failures during hydration.
                If False (default), raise HydrationError on any failure.

        Returns:
            Business instance (fully hydrated if hydrate_full=True).

        Raises:
            HydrationError: If traversal fails (no parent, cycle detected,
                max depth exceeded) or if hydration fails and partial_ok=False.

        Example:
            offer = Offer.model_validate(task_data)
            business = await offer.to_business_async(client)

            # Business is fully hydrated
            print(f"Business: {business.name}")

            # Offer references are updated
            assert offer.business is business
            assert offer.unit is not None
        """
        from autom8_asana.exceptions import HydrationError
        from autom8_asana.models.business.hydration import _traverse_upward_async

        # Traverse upward to find Business
        business, path = await _traverse_upward_async(self, client)

        # Hydrate full hierarchy if requested
        if hydrate_full:
            try:
                await business._fetch_holders_async(client)
            except Exception as e:
                if partial_ok:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        "Hydration failed with partial_ok=True",
                        extra={"business_gid": business.gid, "error": str(e)},
                    )
                else:
                    if isinstance(e, HydrationError):
                        raise
                    raise HydrationError(
                        f"Downward hydration failed for Business {business.gid}: {e}",
                        entity_gid=business.gid,
                        entity_type="business",
                        phase="downward",
                        cause=e,
                    ) from e

        # Update this Offer's references to point to hydrated hierarchy
        # Walk the hydrated hierarchy to find the corresponding entities
        if business._unit_holder is not None:
            for unit in business._unit_holder.units:
                if unit._offer_holder is not None:
                    for offer in unit._offer_holder.offers:
                        if offer.gid == self.gid:
                            # Found this offer in the hydrated hierarchy
                            self._offer_holder = unit._offer_holder
                            self._unit = unit
                            self._business = business
                            break
                    if self._business is not None:
                        break

        return business

    # --- Ad Status Determination (FR-MODEL-007) ---

    @property
    def has_active_ads(self) -> bool:
        """Check if this offer has active ads.

        Per FR-MODEL-007: Determines if ads are running for this offer.

        Returns:
            True if offer has active ads (has active_ads_url or ad_id).
        """
        return bool(self.active_ads_url or self.ad_id)

class OfferHolder(Task, HolderMixin["Offer"]):
    """Holder task containing Offer children.

    Per FR-HOLDER-004: OfferHolder extends Task with _offers PrivateAttr.
    Per TDD-HARDENING-C: KEEPS _populate_children override for intermediate _unit ref.
    """

    # ClassVar configuration (TDD-HARDENING-C)
    CHILD_TYPE: ClassVar[type[Offer]] = Offer
    PARENT_REF_NAME: ClassVar[str] = "_offer_holder"
    CHILDREN_ATTR: ClassVar[str] = "_offers"

    # Children storage
    _offers: list[Offer] = PrivateAttr(default_factory=list)

    # Back-references (ADR-0052)
    _unit: Unit | None = PrivateAttr(default=None)
    _business: Business | None = PrivateAttr(default=None)

    # NOTE: _populate_children KEPT for intermediate _unit ref (TDD-HARDENING-C)

    @property
    def offers(self) -> list[Offer]:
        """All Offer children.

        Returns:
            List of Offer entities.
        """
        return self._offers

    @property
    def active_offers(self) -> list[Offer]:
        """Offers with active ads.

        Returns:
            List of Offer entities where has_active_ads is True.
        """
        return [o for o in self._offers if o.has_active_ads]

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
        """Populate offers from fetched subtasks.

        NOTE: Override KEPT because OfferHolder has intermediate _unit ref
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

        self._offers = []
        for task in sorted_tasks:
            offer = Offer.model_validate(task.model_dump())
            offer._offer_holder = self
            offer._unit = self._unit
            offer._business = self._business
            self._offers.append(offer)
