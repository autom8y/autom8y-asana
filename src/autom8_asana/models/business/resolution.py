"""Resolution types and strategies for cross-holder relationship resolution.

Per TDD-RESOLUTION: Enables AssetEdit entities to resolve their owning Unit
and Offer through configurable resolution strategies.

Per ADR-0071: Return first match in `entity` field when ambiguous; set
`ambiguous=True` with all matches in `candidates`.

Per ADR-0072: NO internal caching of resolution results.

Per ADR-0073: Batch operations implemented as module-level functions.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Generic, Sequence, TypeVar

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.asset_edit import AssetEdit
    from autom8_asana.models.business.base import BusinessEntity
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.offer import Offer
    from autom8_asana.models.business.unit import Unit

T = TypeVar("T", bound="BusinessEntity")

logger = logging.getLogger(__name__)


class ResolutionStrategy(str, Enum):
    """Available resolution strategies with priority ordering.

    Per FR-STRATEGY-001: Enum defining available strategies and priority order.

    Priority order (for AUTO mode):
    1. DEPENDENT_TASKS - Most reliable, domain-specific relationship
    2. CUSTOM_FIELD_MAPPING - Vertical field matching
    3. EXPLICIT_OFFER_ID - Direct ID reference

    AUTO executes strategies in priority order until one succeeds.

    Example:
        # Use specific strategy
        result = await asset_edit.resolve_unit_async(
            client,
            strategy=ResolutionStrategy.DEPENDENT_TASKS
        )

        # Use AUTO (default) - tries all in priority order
        result = await asset_edit.resolve_unit_async(client)
    """

    DEPENDENT_TASKS = "dependent_tasks"
    CUSTOM_FIELD_MAPPING = "custom_field_mapping"
    EXPLICIT_OFFER_ID = "explicit_offer_id"
    AUTO = "auto"

    @classmethod
    def priority_order(cls) -> list[ResolutionStrategy]:
        """Return strategies in priority order (for AUTO mode).

        Returns:
            List of strategies in order of reliability/preference.
        """
        return [
            cls.DEPENDENT_TASKS,
            cls.CUSTOM_FIELD_MAPPING,
            cls.EXPLICIT_OFFER_ID,
        ]


@dataclass
class ResolutionResult(Generic[T]):
    """Result of a resolution operation with strategy transparency.

    Per FR-RESOLVE-003: Provides full transparency about resolution path.
    Per ADR-0071: Ambiguous results return first match in entity field.

    Attributes:
        entity: Resolved entity or None if not found. If ambiguous, contains
               first match for convenience (caller can check candidates).
        strategy_used: Strategy that produced the result (None if all failed).
        strategies_tried: All strategies attempted in order.
        ambiguous: True if multiple matches were found.
        candidates: All matching entities (populated if ambiguous or for debugging).
        error: Error message if resolution failed.

    Properties:
        success: True if exactly one match found (entity set, not ambiguous).

    Example:
        result = await asset_edit.resolve_unit_async(client)

        if result.success:
            unit = result.entity
            print(f"Resolved via {result.strategy_used}")
        elif result.ambiguous:
            print(f"Multiple matches: {[u.name for u in result.candidates]}")
            # Can still use first match if acceptable
            unit = result.entity
        else:
            print(f"Resolution failed: {result.error}")
    """

    entity: T | None = None
    strategy_used: ResolutionStrategy | None = None
    strategies_tried: list[ResolutionStrategy] = field(default_factory=list)
    ambiguous: bool = False
    candidates: list[T] = field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        """True if resolution succeeded with exactly one match.

        Returns False if:
        - No entity found (entity is None)
        - Multiple matches found (ambiguous is True)
        """
        return self.entity is not None and not self.ambiguous


# --- Batch Resolution Functions (ADR-0073) ---


async def _ensure_units_hydrated(business: Business, client: AsanaClient) -> None:
    """Ensure Business has units hydrated for resolution.

    If units are already populated, this is a no-op.

    Args:
        business: Business to ensure units are hydrated on.
        client: AsanaClient for API calls.
    """
    # Check if units are already hydrated
    if business._unit_holder is not None and len(business.units) > 0:
        return

    # Fetch full hierarchy to populate units
    try:
        await business._fetch_holders_async(client)
    except Exception as e:
        logger.warning(
            "Failed to hydrate business units",
            extra={"business_gid": business.gid, "error": str(e)},
        )
        raise


async def resolve_units_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Unit]]:
    """Batch resolve multiple AssetEdits to Units.

    Per ADR-0073: Module-level function for batch resolution.

    Optimizes shared lookups - fetches Business.units once per unique Business,
    then resolves each AssetEdit using the pre-fetched data.

    Args:
        asset_edits: Sequence of AssetEdit entities to resolve.
        client: AsanaClient for API calls.
        strategy: Resolution strategy to use (default: AUTO).

    Returns:
        Dictionary mapping asset_edit.gid to ResolutionResult.
        Every input AssetEdit has an entry, even on failure.

    Example:
        results = await resolve_units_async(asset_edits, client)

        for asset_edit in asset_edits:
            result = results[asset_edit.gid]
            if result.success:
                print(f"{asset_edit.name} -> {result.entity.name}")
    """
    # Import here to avoid circular import at module load
    from autom8_asana.models.business.unit import Unit

    # 1. Handle empty input
    if not asset_edits:
        return {}

    # 2. Collect unique Businesses from input AssetEdits
    businesses: dict[str, Business] = {}
    for ae in asset_edits:
        if ae.business is not None and ae.business.gid not in businesses:
            businesses[ae.business.gid] = ae.business

    # 3. Ensure all Businesses have units hydrated (concurrent)
    # This is the key optimization - fetch once per Business, not per AssetEdit
    if businesses:
        hydration_tasks = [
            _ensure_units_hydrated(b, client) for b in businesses.values()
        ]
        # Use gather with return_exceptions to handle partial failures gracefully
        await asyncio.gather(*hydration_tasks, return_exceptions=True)

    # 4. Resolve each AssetEdit (delegates to instance method)
    results: dict[str, ResolutionResult[Unit]] = {}
    for ae in asset_edits:
        try:
            result = await ae.resolve_unit_async(client, strategy=strategy)
            results[ae.gid] = result
        except Exception as e:
            # Ensure every input has an entry, even on failure
            logger.warning(
                "AssetEdit resolution failed",
                extra={"asset_edit_gid": ae.gid, "error": str(e)},
            )
            results[ae.gid] = ResolutionResult[Unit](
                error=f"Resolution failed: {e}",
                strategies_tried=[strategy]
                if strategy != ResolutionStrategy.AUTO
                else [],
            )

    return results


async def resolve_offers_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Offer]]:
    """Batch resolve multiple AssetEdits to Offers.

    Per ADR-0073: Module-level function for batch resolution.

    Optimizes shared lookups - fetches Business.units once per unique Business,
    then resolves each AssetEdit using the pre-fetched data.

    Args:
        asset_edits: Sequence of AssetEdit entities to resolve.
        client: AsanaClient for API calls.
        strategy: Resolution strategy to use (default: AUTO).

    Returns:
        Dictionary mapping asset_edit.gid to ResolutionResult.
        Every input AssetEdit has an entry, even on failure.

    Example:
        results = await resolve_offers_async(asset_edits, client)

        for asset_edit in asset_edits:
            result = results[asset_edit.gid]
            if result.success:
                print(f"{asset_edit.name} -> {result.entity.name}")
    """
    # Import here to avoid circular import at module load
    from autom8_asana.models.business.offer import Offer

    # 1. Handle empty input
    if not asset_edits:
        return {}

    # 2. Collect unique Businesses from input AssetEdits
    businesses: dict[str, Business] = {}
    for ae in asset_edits:
        if ae.business is not None and ae.business.gid not in businesses:
            businesses[ae.business.gid] = ae.business

    # 3. Ensure all Businesses have units hydrated (concurrent)
    # This is the key optimization - fetch once per Business, not per AssetEdit
    if businesses:
        hydration_tasks = [
            _ensure_units_hydrated(b, client) for b in businesses.values()
        ]
        # Use gather with return_exceptions to handle partial failures gracefully
        await asyncio.gather(*hydration_tasks, return_exceptions=True)

    # 4. Resolve each AssetEdit to Offer (delegates to instance method)
    results: dict[str, ResolutionResult[Offer]] = {}
    for ae in asset_edits:
        try:
            result = await ae.resolve_offer_async(client, strategy=strategy)
            results[ae.gid] = result
        except Exception as e:
            # Ensure every input has an entry, even on failure
            logger.warning(
                "AssetEdit offer resolution failed",
                extra={"asset_edit_gid": ae.gid, "error": str(e)},
            )
            results[ae.gid] = ResolutionResult[Offer](
                error=f"Resolution failed: {e}",
                strategies_tried=[strategy]
                if strategy != ResolutionStrategy.AUTO
                else [],
            )

    return results


def resolve_units(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Unit]]:
    """Sync wrapper for resolve_units_async.

    Per ADR-0073: Sync wrapper using asyncio.run().

    Args:
        asset_edits: Sequence of AssetEdit entities to resolve.
        client: AsanaClient for API calls.
        strategy: Resolution strategy to use (default: AUTO).

    Returns:
        Dictionary mapping asset_edit.gid to ResolutionResult.

    Example:
        results = resolve_units(asset_edits, client)

        for asset_edit in asset_edits:
            result = results[asset_edit.gid]
            if result.success:
                print(f"{asset_edit.name} -> {result.entity.name}")
    """
    return asyncio.run(resolve_units_async(asset_edits, client, strategy=strategy))


def resolve_offers(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Offer]]:
    """Sync wrapper for resolve_offers_async.

    Per ADR-0073: Sync wrapper using asyncio.run().

    Args:
        asset_edits: Sequence of AssetEdit entities to resolve.
        client: AsanaClient for API calls.
        strategy: Resolution strategy to use (default: AUTO).

    Returns:
        Dictionary mapping asset_edit.gid to ResolutionResult.

    Example:
        results = resolve_offers(asset_edits, client)

        for asset_edit in asset_edits:
            result = results[asset_edit.gid]
            if result.success:
                print(f"{asset_edit.name} -> {result.entity.name}")
    """
    return asyncio.run(resolve_offers_async(asset_edits, client, strategy=strategy))
