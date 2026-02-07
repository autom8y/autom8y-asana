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

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.models.business.descriptors import (
    EnumField,
    HolderRef,
    IntField,
    MultiEnumField,
    NumberField,
    TextField,
)
from autom8_asana.models.business.fields import InheritedFieldDef

# Note: PeopleField removed - rep field now inherited from SharedCascadingFieldsMixin
from autom8_asana.models.business.holder_factory import HolderFactory
from autom8_asana.models.business.mixins import (
    FinancialFieldsMixin,
    SharedCascadingFieldsMixin,
    UnitNavigableEntityMixin,
    UnitNestedHolderMixin,
    UpwardTraversalMixin,
)
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.unit import Unit


class Offer(
    BusinessEntity,
    UnitNavigableEntityMixin,
    SharedCascadingFieldsMixin,
    FinancialFieldsMixin,
    UpwardTraversalMixin,
):
    """Offer entity within an OfferHolder.

    Per TDD-BIZMODEL: Offers represent individual ad campaigns/placements
    and are the unit of work for determining account status (are ads running).
    Per TDD-SPRINT-1: Inherits shared fields from mixins.
    Per TDD-SPRINT-1 Phase 2: Uses UpwardTraversalMixin for to_business_async.
    Per TDD-SPRINT-5-CLEANUP: MRO documentation added for maintainability.

    Hierarchy:
        Business
            +-- UnitHolder
                  +-- Unit
                        +-- OfferHolder
                              +-- Offer (this entity)

    MRO (Method Resolution Order):
        Offer -> BusinessEntity -> SharedCascadingFieldsMixin -> FinancialFieldsMixin
        -> UpwardTraversalMixin -> Task -> BaseModel

        - BusinessEntity: Core entity behavior (_invalidate_refs, gid, etc.)
        - SharedCascadingFieldsMixin: vertical, rep descriptors
        - FinancialFieldsMixin: booking_type, mrr, weekly_ad_spend descriptors
        - UpwardTraversalMixin: to_business_async implementation

        Mixins come AFTER BusinessEntity so entity methods take precedence.

    Example:
        for offer in unit.offers:
            if offer.has_active_ads:
                print(f"Active: {offer.name} - ${offer.weekly_ad_spend}/week")
    """

    NAME_CONVENTION: ClassVar[str] = "[Offer Name]"

    # Per TDD-DETECTION: Primary project GID for entity type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1143843662099250"

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

    # business property inherited from UnitNavigableEntityMixin (DRY-006)

    def _invalidate_refs(self, _exclude_attr: str | None = None) -> None:
        """Invalidate cached references on hierarchy change.

        Per FR-NAV-006: Clear cached navigation on hierarchy change.
        Per TDD-SPRINT-5-CLEANUP/LSK-001: Signature matches base class for LSP compliance.

        Args:
            _exclude_attr: Ignored. Clears all refs unconditionally.
        """
        self._business = None
        self._unit = None
        self._offer_holder = None

    # --- Custom Field Descriptors (ADR-0081, TDD-PATTERNS-A) ---
    # Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.
    # Per ADR-0082: Fields class is auto-generated from these descriptors.
    # Per TDD-SPRINT-1: mrr, weekly_ad_spend inherited from FinancialFieldsMixin
    # Per TDD-SPRINT-1: vertical, rep inherited from SharedCascadingFieldsMixin
    # Note: booking_type inherited from mixin but not used by Offer (returns None)

    # Financial fields (3 - mrr, weekly_ad_spend from mixin)
    cost = NumberField()
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

    # Configuration fields (8 - vertical from mixin)
    form_id = TextField(field_name="Form ID")
    language = EnumField()
    specialty = EnumField()
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

    # Metadata fields (3 - rep from mixin)
    offer_id = TextField(field_name="Offer ID")
    algo_version = TextField()
    triggered_by = TextField()

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

    # --- Upward Traversal (TDD-HYDRATION Phase 2, TDD-SPRINT-1 Phase 2) ---
    # to_business_async inherited from UpwardTraversalMixin

    def _update_refs_from_hydrated_business(self, business: Business) -> None:
        """Update Offer references to point to hydrated hierarchy.

        Per TDD-SPRINT-1 Phase 2: Hook for UpwardTraversalMixin.

        Offer is 4 levels deep, so we must walk the hierarchy to find
        this specific Offer and update all intermediate references.

        Args:
            business: The hydrated Business instance.
        """
        # Walk the hydrated hierarchy to find the corresponding entities
        if business._unit_holder is not None:
            for unit in business._unit_holder.units:  # type: ignore[attr-defined]
                if unit._offer_holder is not None:
                    for offer in unit._offer_holder.offers:
                        if offer.gid == self.gid:
                            # Found this offer in the hydrated hierarchy
                            self._offer_holder = unit._offer_holder
                            self._unit = unit
                            self._business = business
                            return
                    if self._business is not None:
                        return

    # --- Ad Status Determination (FR-MODEL-007) ---

    @property
    def has_active_ads(self) -> bool:
        """Check if this offer has active ads.

        Per FR-MODEL-007: Determines if ads are running for this offer.

        Returns:
            True if offer has active ads (has active_ads_url or ad_id).
        """
        return bool(self.active_ads_url or self.ad_id)


class OfferHolder(
    UnitNestedHolderMixin,
    HolderFactory,
    child_type="Offer",
    parent_ref="_offer_holder",
    children_attr="_offers",
    semantic_alias="offers",
):
    """Holder task containing Offer children.

    Per FR-HOLDER-004: OfferHolder extends Task with _offers PrivateAttr.
    Per TDD-SPRINT-1: Migrated to HolderFactory with override for _unit ref propagation.
    Per TDD-SPRINT-5-CLEANUP/DRY-006: Uses UnitNestedHolderMixin for business navigation.

    MRO Note:
        UnitNestedHolderMixin must come before HolderFactory in the base class
        list so its business property overrides HolderFactory.business. The mixin's
        property navigates via _unit when _business is not directly set.
    """

    # Per TDD-DETECTION: Primary project GID for holder type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1210679066066870"

    # Intermediate reference for propagation to children
    _unit: Unit | None = PrivateAttr(default=None)

    @property
    def active_offers(self) -> list[Offer]:
        """Offers with active ads.

        Returns:
            List of Offer entities where has_active_ads is True.
        """
        return [o for o in self.children if o.has_active_ads]

    @property
    def unit(self) -> Unit | None:
        """Navigate to parent Unit.

        Returns:
            Unit entity or None if not populated.
        """
        return self._unit

    # business property inherited from UnitNestedHolderMixin (DRY-006)
    # _populate_children inherited from UnitNestedHolderMixin (DRY-007)
