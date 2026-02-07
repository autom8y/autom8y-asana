"""Field mixins for shared custom field descriptors.

Per ADR-0119: Coarse-grained mixins for DRY field consolidation.
Per TDD-SPRINT-1 Phase 1: SharedCascadingFieldsMixin and FinancialFieldsMixin.
Per TDD-SPRINT-1 Phase 2: UpwardTraversalMixin for to_business_async.
Per TDD-SPRINT-5-CLEANUP/DRY-006: UnitNestedHolderMixin for business navigation.

Mixins provide descriptor-only definitions. CascadingFieldDef metadata
remains on entity classes since cascading behavior varies per entity.

Usage:
    class Unit(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin):
        # vertical, rep inherited from SharedCascadingFieldsMixin
        # booking_type, mrr, weekly_ad_spend inherited from FinancialFieldsMixin
        ...

    class Contact(BusinessEntity, UpwardTraversalMixin):
        # to_business_async inherited from UpwardTraversalMixin
        ...

    class OfferHolder(HolderFactory, UnitNestedHolderMixin, ...):
        # business property inherited from UnitNestedHolderMixin
        ...

Note on MRO:
    Mixins should come AFTER the primary base class in inheritance order.
    Python's MRO ensures BusinessEntity methods are found first, with mixin
    descriptors providing field access.

Note on Unused Fields:
    Some entities inherit fields they don't use (e.g., Business inherits
    mrr from FinancialFieldsMixin). This is harmless - the descriptor
    returns None if the Asana field doesn't exist on that task type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.models.business.descriptors import (
    EnumField,
    NumberField,
    PeopleField,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.business import Business


class SharedCascadingFieldsMixin:
    """Fields that commonly cascade through the entity hierarchy.

    Per FR-008: Provides vertical and rep descriptors.
    Per ADR-0119: Coarse-grained mixin grouping semantically related fields.

    Used by: Business, Unit, Offer, Process

    Note: Cascading behavior (CascadingFieldDef) is NOT defined here.
    Each entity defines its own cascading rules since target types
    and allow_override vary per entity.

    Fields:
        vertical: Enum field for business vertical (e.g., "Medical", "Dental")
        rep: People field for assigned sales representative
    """

    vertical = EnumField()
    rep = PeopleField()


class FinancialFieldsMixin:
    """Financial tracking fields.

    Per FR-009: Provides booking_type, mrr, weekly_ad_spend descriptors.
    Per ADR-0119: Coarse-grained mixin grouping semantically related fields.

    Used by:
    - Business: booking_type only (mrr, weekly_ad_spend return None)
    - Unit: all three
    - Offer: mrr, weekly_ad_spend only (booking_type returns None)
    - Process: all three

    Note: Entities that don't use all fields simply get None when accessing
    fields that don't exist on the underlying Asana task. This is by design -
    it allows a single mixin to serve multiple entity types without error.

    Fields:
        booking_type: Enum field for booking type classification
        mrr: Monthly Recurring Revenue (NumberField returning Decimal)
        weekly_ad_spend: Weekly advertising spend (NumberField returning Decimal)
    """

    booking_type = EnumField()
    mrr = NumberField(field_name="MRR")
    weekly_ad_spend = NumberField()


class UpwardTraversalMixin:
    """Provides common upward traversal logic to find Business ancestor.

    Per TDD-SPRINT-1 Phase 2: Extracted from Contact, Unit, Offer.
    Per ADR-0119: Opt-in mixin with hook pattern for entity-specific updates.

    Subclasses must implement:
        _update_refs_from_hydrated_business(business): Update entity-specific
            references after hydration completes.

    The mixin handles the common traversal + hydration + error handling pattern,
    while each entity defines how to update its own references.

    Usage:
        class Contact(BusinessEntity, UpwardTraversalMixin):
            def _update_refs_from_hydrated_business(self, business: Business) -> None:
                if business._contact_holder is not None:
                    self._contact_holder = business._contact_holder
                    self._business = business
    """

    # Subclass must have gid attribute (inherited from Task/BusinessEntity)
    gid: str

    async def to_business_async(
        self,
        client: AsanaClient,
        *,
        hydrate_full: bool = True,
        partial_ok: bool = False,
    ) -> Business:
        """Navigate to containing Business and optionally hydrate full hierarchy.

        Per ADR-0069: Instance method for upward navigation.
        Per TDD-SPRINT-1 Phase 2: Common implementation via mixin.
        Per ADR-0070: partial_ok controls fail-fast vs partial success behavior.

        Path varies by entity:
        - Contact: Contact -> ContactHolder -> Business (2 levels)
        - Unit: Unit -> UnitHolder -> Business (2 levels)
        - Offer: Offer -> OfferHolder -> Unit -> UnitHolder -> Business (4 levels)

        This method traverses the parent chain to find the Business root,
        then optionally hydrates the full Business hierarchy. After hydration,
        the entity's references are updated via _update_refs_from_hydrated_business().

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
            entity = Contact.model_validate(task_data)
            business = await entity.to_business_async(client)

            # Business is fully hydrated
            print(f"Business: {business.name}")

            # Entity references are updated
            assert entity.business is business
        """
        from autom8_asana.exceptions import HydrationError
        from autom8_asana.models.business.hydration import _traverse_upward_async

        # Traverse upward to find Business
        business, path = await _traverse_upward_async(self, client)  # type: ignore[arg-type]

        # Hydrate full hierarchy if requested
        if hydrate_full:
            try:
                await business._fetch_holders_async(client)
            except Exception as e:  # BROAD-CATCH: catch-all-and-degrade -- partial_ok catches any hydration failure
                if partial_ok:
                    from autom8y_log import get_logger

                    logger = get_logger(__name__)
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

        # Update entity-specific references via hook
        self._update_refs_from_hydrated_business(business)

        return business

    def _update_refs_from_hydrated_business(self, business: Business) -> None:
        """Update entity-specific references after hydration.

        Override this method in subclasses to update cached references
        to point to the hydrated Business hierarchy.

        Args:
            business: The hydrated Business instance.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement _update_refs_from_hydrated_business()"
        )


class UnitNavigableEntityMixin:
    """Mixin for entities that navigate to Business via self.unit.

    Per TDD-SPRINT-5-CLEANUP/DRY-006: Consolidates duplicate business property
    from Offer and Process entities.

    These entities are nested under Unit and access Business via the unit.business
    chain. The business property performs lazy navigation through the unit property.

    Usage:
        class Offer(BusinessEntity, UnitNavigableEntityMixin, ...):
            # business property inherited from mixin
            # unit property must be defined by the entity

    Requires:
        - _business: Business | None attribute (must be set by entity)
        - unit: property that returns Unit | None (must be defined by entity)
    """

    # Type stub for _business attribute that must exist on the class using this mixin
    # Note: Do NOT add type stub for 'unit' - it would shadow the entity's property
    _business: Business | None

    @property
    def business(self) -> Business | None:
        """Navigate to containing Business (cached).

        Per TDD-SPRINT-5-CLEANUP/DRY-006: Consolidated from Offer and Process.

        Returns:
            Business entity or None if not populated.
        """
        if self._business is None:
            unit = self.unit  # type: ignore[attr-defined]
            if unit is not None:
                self._business = unit.business
        return self._business


class UnitNestedHolderMixin:
    """Mixin for holders nested under Unit that navigate to Business via _unit.

    Per TDD-SPRINT-5-CLEANUP/DRY-006: Consolidates duplicate business property
    from OfferHolder and ProcessHolder.
    Per TDD-SPRINT-5-CLEANUP/DRY-007: Consolidates _populate_children override
    from OfferHolder and ProcessHolder.

    These holders have both _business and _unit references, where _unit is the
    intermediate reference in the hierarchy (Business -> UnitHolder -> Unit ->
    OfferHolder/ProcessHolder). The business property navigates via _unit when
    _business is not directly set.

    Usage:
        class OfferHolder(HolderFactory, UnitNestedHolderMixin, ...):
            _unit: Unit | None = PrivateAttr(default=None)
            # business property and _populate_children inherited from mixin

    Requires:
        - _business: Business | None attribute
        - _unit: Unit | None attribute (must be set by parent during population)
        - children: list attribute (from HolderFactory)
    """

    # Type stubs for attributes that must exist on the class using this mixin
    _business: Business | None
    _unit: Any  # Unit | None, but using Any to avoid circular import

    @property
    def business(self) -> Business | None:
        """Navigate to parent Business via _unit if _business not set.

        Per TDD-SPRINT-5-CLEANUP/DRY-006: Consolidated from OfferHolder and ProcessHolder.

        Returns:
            Business entity or None if not populated.
        """
        if self._business is None and self._unit is not None:
            self._business = self._unit.business
        return self._business

    def _populate_children(self, subtasks: list[Any]) -> None:
        """Populate children and propagate _unit reference.

        Per TDD-SPRINT-5-CLEANUP/DRY-007: Consolidated from OfferHolder and ProcessHolder.

        Override of HolderFactory._populate_children to propagate intermediate
        _unit reference to children. The generic implementation only handles
        holder ref and business ref.

        Args:
            subtasks: List of Task subtasks from API.
        """
        # Call parent implementation to populate children with standard refs
        super()._populate_children(subtasks)  # type: ignore[misc]

        # Propagate _unit reference to all children
        for child in self.children:  # type: ignore[attr-defined]
            child._unit = self._unit
