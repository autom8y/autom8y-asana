"""AssetEdit entity for cross-holder relationship resolution.

Per TDD-RESOLUTION: AssetEdit extends Process with 11 typed field accessors
and resolution methods for finding owning Unit and Offer.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.

Per FR-PREREQ-001: AssetEdit entity with 11 typed field accessors.
Per FR-RESOLVE-001/002: resolve_unit_async() and resolve_offer_async() methods.
Per ADR-0052: Cached upward references with explicit invalidation.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import PrivateAttr

from autom8_asana.models.business.descriptors import HolderRef, ParentRef
from autom8_asana.models.business.process import Process
from autom8_asana.models.business.resolution import ResolutionResult, ResolutionStrategy

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.business import AssetEditHolder, Business
    from autom8_asana.models.business.offer import Offer
    from autom8_asana.models.business.unit import Unit

logger = logging.getLogger(__name__)


class AssetEdit(Process):
    """AssetEdit entity extending Process with 11 typed field accessors.

    Per TDD-RESOLUTION: AssetEdit is NOT in the Unit/Offer containment hierarchy.
    It must resolve to Unit/Offer via resolution strategies.

    Hierarchy:
        Business
            +-- AssetEditHolder
                  +-- AssetEdit (this entity)

    Resolution:
        AssetEdit is NOT in the Unit/Offer containment hierarchy.
        It must resolve to Unit/Offer via resolution strategies.

    Example:
        # Resolve to owning Unit
        result = await asset_edit.resolve_unit_async(client)
        if result.success:
            unit = result.entity
            print(f"Belongs to Unit: {unit.name}")

        # Access typed fields
        if asset_edit.score and asset_edit.score > Decimal("90"):
            print(f"High score: {asset_edit.score}")
    """

    NAME_CONVENTION: ClassVar[str] = "[AssetEdit Name]"

    # Private cached references (ADR-0052)
    _asset_edit_holder: AssetEditHolder | None = PrivateAttr(default=None)

    # Navigation descriptors (TDD-HARDENING-C, ADR-0075)
    # IMPORTANT: Declared WITHOUT type annotations to avoid Pydantic field creation
    # Note: AssetEdit is direct child of Business (not under Unit hierarchy)
    asset_edit_holder = HolderRef["AssetEditHolder"]()
    business = ParentRef["Business"](holder_attr="_asset_edit_holder")

    def _invalidate_refs(self) -> None:
        """Invalidate cached references on hierarchy change.

        Per FR-NAV-006: Clear cached navigation on hierarchy change.
        Override needed because AssetEdit has additional _asset_edit_holder ref.
        """
        super()._invalidate_refs()
        self._asset_edit_holder = None

    class Fields(Process.Fields):
        """Custom field name constants for IDE discoverability.

        Per FR-PREREQ-001: Inner Fields class with 11 custom field names.
        Inherits from Process.Fields to include parent fields.
        """

        # AssetEdit-specific fields (11 total)
        ASSET_APPROVAL = "Asset Approval"
        ASSET_ID = "Asset ID"
        EDITOR = "Editor"
        REVIEWER = "Reviewer"
        OFFER_ID = "Offer ID"
        RAW_ASSETS = "Raw Assets"
        REVIEW_ALL_ADS = "Review All Ads"
        SCORE = "Score"
        SPECIALTY = "Specialty"
        TEMPLATE_ID = "Template ID"
        VIDEOS_PAID = "Videos Paid"

    # --- Typed Field Accessors (11 fields) ---

    @property
    def asset_approval(self) -> str | None:
        """Asset approval status (enum custom field)."""
        return self._get_enum_field(self.Fields.ASSET_APPROVAL)

    @asset_approval.setter
    def asset_approval(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.ASSET_APPROVAL, value)

    @property
    def asset_id(self) -> str | None:
        """Asset identifier (text custom field)."""
        return self._get_text_field(self.Fields.ASSET_ID)

    @asset_id.setter
    def asset_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.ASSET_ID, value)

    @property
    def editor(self) -> list[dict[str, Any]]:
        """Editor users (people custom field)."""
        value: Any = self.get_custom_fields().get(self.Fields.EDITOR)
        return value if isinstance(value, list) else []

    @editor.setter
    def editor(self, value: list[dict[str, Any]] | None) -> None:
        self.get_custom_fields().set(self.Fields.EDITOR, value)

    @property
    def reviewer(self) -> list[dict[str, Any]]:
        """Reviewer users (people custom field)."""
        value: Any = self.get_custom_fields().get(self.Fields.REVIEWER)
        return value if isinstance(value, list) else []

    @reviewer.setter
    def reviewer(self, value: list[dict[str, Any]] | None) -> None:
        self.get_custom_fields().set(self.Fields.REVIEWER, value)

    @property
    def offer_id(self) -> str | None:
        """Explicit offer ID reference (text custom field).

        Key field for EXPLICIT_OFFER_ID resolution strategy.
        Contains the GID of the associated Offer task.
        """
        return self._get_text_field(self.Fields.OFFER_ID)

    @offer_id.setter
    def offer_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.OFFER_ID, value)

    @property
    def raw_assets(self) -> str | None:
        """Raw assets link/text (text custom field)."""
        return self._get_text_field(self.Fields.RAW_ASSETS)

    @raw_assets.setter
    def raw_assets(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.RAW_ASSETS, value)

    @property
    def review_all_ads(self) -> bool | None:
        """Review all ads flag (enum mapped to bool).

        Returns True if enum value is "Yes", False if "No", None otherwise.
        """
        value = self._get_enum_field(self.Fields.REVIEW_ALL_ADS)
        if value is None:
            return None
        return value.lower() == "yes"

    @review_all_ads.setter
    def review_all_ads(self, value: bool | None) -> None:
        # Convert bool to enum string
        if value is None:
            self.get_custom_fields().set(self.Fields.REVIEW_ALL_ADS, None)
        else:
            self.get_custom_fields().set(
                self.Fields.REVIEW_ALL_ADS, "Yes" if value else "No"
            )

    @property
    def score(self) -> Decimal | None:
        """Score value (number custom field)."""
        return self._get_number_field(self.Fields.SCORE)

    @score.setter
    def score(self, value: Decimal | None) -> None:
        self.get_custom_fields().set(
            self.Fields.SCORE,
            float(value) if value is not None else None,
        )

    @property
    def specialty(self) -> str | None:
        """Specialty type (enum custom field)."""
        return self._get_enum_field(self.Fields.SPECIALTY)

    @specialty.setter
    def specialty(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.SPECIALTY, value)

    @property
    def template_id(self) -> str | None:
        """Template identifier (text custom field)."""
        return self._get_text_field(self.Fields.TEMPLATE_ID)

    @template_id.setter
    def template_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.TEMPLATE_ID, value)

    @property
    def videos_paid(self) -> int | None:
        """Number of videos paid (number custom field)."""
        return self._get_int_field(self.Fields.VIDEOS_PAID)

    @videos_paid.setter
    def videos_paid(self, value: int | None) -> None:
        self.get_custom_fields().set(self.Fields.VIDEOS_PAID, value)

    # --- Helper for int fields ---

    def _get_int_field(self, field_name: str) -> int | None:
        """Get number custom field value as integer."""
        value: Any = self.get_custom_fields().get(field_name)
        if value is None:
            return None
        return int(value)

    def _get_number_field(self, field_name: str) -> Decimal | None:
        """Get number custom field value as Decimal."""
        value: Any = self.get_custom_fields().get(field_name)
        if value is None:
            return None
        return Decimal(str(value))

    # --- Resolution Methods ---

    async def resolve_unit_async(
        self,
        client: AsanaClient,
        *,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> ResolutionResult[Unit]:
        """Resolve to owning Unit using configured strategy.

        Per FR-RESOLVE-001: Executes specified strategy (or AUTO sequence).

        Args:
            client: AsanaClient for API calls.
            strategy: Resolution strategy to use (default: AUTO).

        Returns:
            ResolutionResult containing:
            - entity: Resolved Unit or None
            - strategy_used: Which strategy succeeded
            - ambiguous: True if multiple Units matched
            - candidates: All matching Units

        Raises:
            ResolutionError: On unrecoverable failures (not ambiguity).

        Example:
            result = await asset_edit.resolve_unit_async(client)
            if result.success:
                unit = result.entity
                print(f"Resolved via {result.strategy_used}")
            elif result.ambiguous:
                print(f"Multiple matches: {result.candidates}")
        """
        # Import here to avoid circular import
        from autom8_asana.models.business.unit import Unit

        logger.debug(
            "Starting resolution",
            extra={"asset_edit_gid": self.gid, "strategy": strategy.value},
        )

        if strategy == ResolutionStrategy.AUTO:
            return await self._resolve_unit_auto_async(client)
        elif strategy == ResolutionStrategy.DEPENDENT_TASKS:
            return await self._resolve_unit_via_dependents_async(client)
        elif strategy == ResolutionStrategy.CUSTOM_FIELD_MAPPING:
            return await self._resolve_unit_via_vertical_async(client)
        elif strategy == ResolutionStrategy.EXPLICIT_OFFER_ID:
            return await self._resolve_unit_via_offer_id_async(client)
        else:
            # Unknown strategy - return error result
            return ResolutionResult[Unit](
                error=f"Unknown strategy: {strategy}",
                strategies_tried=[strategy],
            )

    async def resolve_offer_async(
        self,
        client: AsanaClient,
        *,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> ResolutionResult[Offer]:
        """Resolve to owning Offer using configured strategy.

        Per FR-RESOLVE-002: First resolves to Unit, then matches Offer.
        For EXPLICIT_OFFER_ID strategy, fetches Offer directly.

        Args:
            client: AsanaClient for API calls.
            strategy: Resolution strategy to use (default: AUTO).

        Returns:
            ResolutionResult containing resolved Offer or None.

        Raises:
            ResolutionError: On unrecoverable failures.
        """
        # Import here to avoid circular import
        from autom8_asana.models.business.offer import Offer

        logger.debug(
            "Starting offer resolution",
            extra={"asset_edit_gid": self.gid, "strategy": strategy.value},
        )

        # For EXPLICIT_OFFER_ID, try to fetch Offer directly first
        if strategy in (
            ResolutionStrategy.EXPLICIT_OFFER_ID,
            ResolutionStrategy.AUTO,
        ):
            direct_result = await self._resolve_offer_directly_async(client)
            if direct_result.success:
                return direct_result
            # If AUTO and direct failed, continue with other strategies
            if strategy == ResolutionStrategy.EXPLICIT_OFFER_ID:
                return direct_result

        # Resolve Unit first, then find Offer within Unit
        unit_result = await self.resolve_unit_async(client, strategy=strategy)

        if not unit_result.entity:
            # Could not resolve to Unit - return error
            return ResolutionResult[Offer](
                error=f"Could not resolve to Unit: {unit_result.error}",
                strategies_tried=unit_result.strategies_tried,
                strategy_used=unit_result.strategy_used,
            )

        unit = unit_result.entity

        # Try to find Offer within Unit's offers
        # For now, return the Unit's first active offer or first offer
        if unit.active_offers:
            offer = unit.active_offers[0]
            return ResolutionResult[Offer](
                entity=offer,
                strategy_used=unit_result.strategy_used,
                strategies_tried=unit_result.strategies_tried,
                candidates=unit.offers if len(unit.offers) > 1 else [],
                ambiguous=len(unit.offers) > 1,
            )
        elif unit.offers:
            offer = unit.offers[0]
            return ResolutionResult[Offer](
                entity=offer,
                strategy_used=unit_result.strategy_used,
                strategies_tried=unit_result.strategies_tried,
                candidates=unit.offers if len(unit.offers) > 1 else [],
                ambiguous=len(unit.offers) > 1,
            )
        else:
            return ResolutionResult[Offer](
                error="Unit has no Offers",
                strategies_tried=unit_result.strategies_tried,
                strategy_used=unit_result.strategy_used,
            )

    # --- Private Resolution Strategy Implementations ---

    async def _resolve_unit_auto_async(
        self, client: AsanaClient
    ) -> ResolutionResult[Unit]:
        """Execute AUTO resolution: try strategies in priority order.

        Per FR-STRATEGY-005: Stops at first non-ambiguous success.
        If ambiguous found, continues seeking non-ambiguous result.
        """
        from autom8_asana.models.business.unit import Unit

        strategies_tried: list[ResolutionStrategy] = []
        ambiguous_result: ResolutionResult[Unit] | None = None

        for strategy in ResolutionStrategy.priority_order():
            logger.debug(
                "Trying strategy",
                extra={"strategy": strategy.value, "asset_edit_gid": self.gid},
            )

            try:
                if strategy == ResolutionStrategy.DEPENDENT_TASKS:
                    result = await self._resolve_unit_via_dependents_async(client)
                elif strategy == ResolutionStrategy.CUSTOM_FIELD_MAPPING:
                    result = await self._resolve_unit_via_vertical_async(client)
                elif strategy == ResolutionStrategy.EXPLICIT_OFFER_ID:
                    result = await self._resolve_unit_via_offer_id_async(client)
                else:
                    continue

                strategies_tried.append(strategy)
                result.strategies_tried = strategies_tried.copy()

                if result.success:
                    logger.info(
                        "Resolution succeeded",
                        extra={
                            "asset_edit_gid": self.gid,
                            "strategy_used": strategy.value,
                            "resolved_to": result.entity.gid if result.entity else None,
                        },
                    )
                    return result

                if result.ambiguous and ambiguous_result is None:
                    # Save first ambiguous result, continue seeking non-ambiguous
                    logger.info(
                        "Resolution ambiguous",
                        extra={
                            "asset_edit_gid": self.gid,
                            "candidate_count": len(result.candidates),
                            "candidates": [c.gid for c in result.candidates],
                        },
                    )
                    ambiguous_result = result
                    ambiguous_result.strategies_tried = strategies_tried.copy()

            except Exception as e:
                # Log and continue to next strategy
                logger.warning(
                    f"Strategy {strategy.value} failed with error",
                    extra={"asset_edit_gid": self.gid, "error": str(e)},
                )
                strategies_tried.append(strategy)
                continue

        # All strategies exhausted
        if ambiguous_result is not None:
            # Return ambiguous result (with first match per ADR-0071)
            ambiguous_result.strategies_tried = strategies_tried
            return ambiguous_result

        # No matches found
        logger.warning(
            "Resolution failed",
            extra={
                "asset_edit_gid": self.gid,
                "strategies_tried": [s.value for s in strategies_tried],
            },
        )
        return ResolutionResult[Unit](
            error="No matching Unit found",
            strategies_tried=strategies_tried,
        )

    async def _resolve_unit_via_dependents_async(
        self, client: AsanaClient
    ) -> ResolutionResult[Unit]:
        """DEPENDENT_TASKS strategy: Check task dependents for Unit.

        Per FR-STRATEGY-002:
        1. Call client.tasks.dependents_async(self.gid).collect()
        2. For each dependent, check if it's a Unit type task
        3. Return first Unit found, or mark ambiguous if multiple
        """
        from autom8_asana.models.business.unit import Unit

        dependents = await client.tasks.dependents_async(self.gid).collect()

        found_units: list[Unit] = []
        for dependent in dependents:
            # Check if dependent is a Unit (by checking if it has OfferHolder/ProcessHolder children)
            # For now, use name-based detection or type checking
            # In practice, would check custom field or name pattern
            if self._is_unit_task(dependent):
                unit = Unit.model_validate(dependent.model_dump())
                found_units.append(unit)

        if len(found_units) == 1:
            return ResolutionResult[Unit](
                entity=found_units[0],
                strategy_used=ResolutionStrategy.DEPENDENT_TASKS,
                strategies_tried=[ResolutionStrategy.DEPENDENT_TASKS],
            )
        elif len(found_units) > 1:
            return ResolutionResult[Unit](
                entity=found_units[0],  # First match per ADR-0071
                strategy_used=ResolutionStrategy.DEPENDENT_TASKS,
                strategies_tried=[ResolutionStrategy.DEPENDENT_TASKS],
                ambiguous=True,
                candidates=found_units,
            )
        else:
            return ResolutionResult[Unit](
                error="No Unit found in dependents",
                strategies_tried=[ResolutionStrategy.DEPENDENT_TASKS],
            )

    async def _resolve_unit_via_vertical_async(
        self, client: AsanaClient
    ) -> ResolutionResult[Unit]:
        """CUSTOM_FIELD_MAPPING strategy: Match vertical field to Unit.

        Per FR-STRATEGY-003:
        1. Read self.vertical (inherited from Process)
        2. Require Business context (self._business must be set)
        3. Iterate business.units, find matching vertical
        4. Handle multiple matches as ambiguous
        """
        from autom8_asana.models.business.unit import Unit

        # Check if we have a vertical to match
        my_vertical = self.vertical
        if not my_vertical:
            return ResolutionResult[Unit](
                error="AssetEdit has no vertical set",
                strategies_tried=[ResolutionStrategy.CUSTOM_FIELD_MAPPING],
            )

        # Require Business context
        business = self.business
        if business is None:
            return ResolutionResult[Unit](
                error="Business context required for CUSTOM_FIELD_MAPPING strategy",
                strategies_tried=[ResolutionStrategy.CUSTOM_FIELD_MAPPING],
            )

        # Find Units with matching vertical
        matching_units: list[Unit] = []
        for unit in business.units:
            if unit.vertical == my_vertical:
                matching_units.append(unit)

        if len(matching_units) == 1:
            return ResolutionResult[Unit](
                entity=matching_units[0],
                strategy_used=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
                strategies_tried=[ResolutionStrategy.CUSTOM_FIELD_MAPPING],
            )
        elif len(matching_units) > 1:
            return ResolutionResult[Unit](
                entity=matching_units[0],  # First match per ADR-0071
                strategy_used=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
                strategies_tried=[ResolutionStrategy.CUSTOM_FIELD_MAPPING],
                ambiguous=True,
                candidates=matching_units,
            )
        else:
            return ResolutionResult[Unit](
                error=f"No Unit found with vertical '{my_vertical}'",
                strategies_tried=[ResolutionStrategy.CUSTOM_FIELD_MAPPING],
            )

    async def _resolve_unit_via_offer_id_async(
        self, client: AsanaClient
    ) -> ResolutionResult[Unit]:
        """EXPLICIT_OFFER_ID strategy: Navigate via offer_id field.

        Per FR-STRATEGY-004:
        1. Read self.offer_id
        2. If set, fetch Offer via client.tasks.get_async(offer_id)
        3. Navigate to Unit via offer.unit
        4. Handle NotFoundError gracefully
        """
        from autom8_asana.exceptions import NotFoundError
        from autom8_asana.models.business.offer import Offer
        from autom8_asana.models.business.unit import Unit

        # Check if offer_id is set
        offer_gid = self.offer_id
        if not offer_gid:
            return ResolutionResult[Unit](
                error="AssetEdit has no offer_id set",
                strategies_tried=[ResolutionStrategy.EXPLICIT_OFFER_ID],
            )

        try:
            # Fetch Offer task
            task = await client.tasks.get_async(offer_gid)
            offer = Offer.model_validate(task.model_dump())

            # Navigate to Unit
            # If offer has unit cached, use it
            if offer.unit is not None:
                return ResolutionResult[Unit](
                    entity=offer.unit,
                    strategy_used=ResolutionStrategy.EXPLICIT_OFFER_ID,
                    strategies_tried=[ResolutionStrategy.EXPLICIT_OFFER_ID],
                )

            # Need to traverse upward to find Unit
            # Check if offer has parent that's an OfferHolder
            if offer.parent and offer.parent.gid:
                parent_task = await client.tasks.get_async(offer.parent.gid)
                # Check if parent's parent is a Unit
                if parent_task.parent and parent_task.parent.gid:
                    unit_task = await client.tasks.get_async(parent_task.parent.gid)
                    unit = Unit.model_validate(unit_task.model_dump())
                    return ResolutionResult[Unit](
                        entity=unit,
                        strategy_used=ResolutionStrategy.EXPLICIT_OFFER_ID,
                        strategies_tried=[ResolutionStrategy.EXPLICIT_OFFER_ID],
                    )

            return ResolutionResult[Unit](
                error="Could not navigate from Offer to Unit",
                strategies_tried=[ResolutionStrategy.EXPLICIT_OFFER_ID],
            )

        except NotFoundError:
            logger.warning(
                "offer_id refers to non-existent task",
                extra={"asset_edit_gid": self.gid, "offer_id": offer_gid},
            )
            return ResolutionResult[Unit](
                error=f"Offer with GID {offer_gid} not found",
                strategies_tried=[ResolutionStrategy.EXPLICIT_OFFER_ID],
            )

    async def _resolve_offer_directly_async(
        self, client: AsanaClient
    ) -> ResolutionResult[Offer]:
        """Fetch Offer directly via offer_id field."""
        from autom8_asana.exceptions import NotFoundError
        from autom8_asana.models.business.offer import Offer

        offer_gid = self.offer_id
        if not offer_gid:
            return ResolutionResult[Offer](
                error="AssetEdit has no offer_id set",
                strategies_tried=[ResolutionStrategy.EXPLICIT_OFFER_ID],
            )

        try:
            task = await client.tasks.get_async(offer_gid)
            offer = Offer.model_validate(task.model_dump())
            return ResolutionResult[Offer](
                entity=offer,
                strategy_used=ResolutionStrategy.EXPLICIT_OFFER_ID,
                strategies_tried=[ResolutionStrategy.EXPLICIT_OFFER_ID],
            )
        except NotFoundError:
            logger.warning(
                "offer_id refers to non-existent task",
                extra={"asset_edit_gid": self.gid, "offer_id": offer_gid},
            )
            return ResolutionResult[Offer](
                error=f"Offer with GID {offer_gid} not found",
                strategies_tried=[ResolutionStrategy.EXPLICIT_OFFER_ID],
            )

    def _is_unit_task(self, task: Any) -> bool:
        """Check if a task appears to be a Unit.

        Uses heuristics to identify Unit tasks:
        - Check for common Unit field names in custom fields
        - Check task name patterns

        Args:
            task: Task to check.

        Returns:
            True if task appears to be a Unit.
        """
        # Check if task has Unit-specific fields
        unit_field_names = {"MRR", "Ad Account ID", "Platforms", "Weekly Ad Spend"}

        if hasattr(task, "custom_fields") and task.custom_fields:
            for cf in task.custom_fields:
                if isinstance(cf, dict) and cf.get("name") in unit_field_names:
                    return True

        return False
