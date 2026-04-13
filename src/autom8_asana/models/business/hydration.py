"""Hydration orchestration for business model hierarchy.

Per TDD-HYDRATION Phase 2: Upward traversal for finding Business root from any entity.
Per TDD-HYDRATION Phase 3: HydrationResult dataclasses and hydrate_from_gid_async.
Per ADR-0068: Type detection strategy using name-based heuristics with structure fallback.
Per ADR-0069: Hydration API design with both instance and factory methods.
Per ADR-0070: Partial failure handling with HydrationResult.

This module provides:
1. Core upward traversal algorithm for navigation from leaf entities to Business root
2. HydrationResult dataclasses for tracking hydration outcomes
3. hydrate_from_gid_async() generic entry point for any task GID

Example:
    # Traverse from Contact to Business
    business, path = await _traverse_upward_async(contact, client)

    # Generic entry point from any GID
    result = await hydrate_from_gid_async(client, any_gid)
    if result.is_complete:
        business = result.business
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from autom8y_log import get_logger

from autom8_asana.errors import HydrationError
from autom8_asana.models.business.detection import (
    EntityType,
    detect_entity_type_async,
)
from autom8_asana.models.business.fields import (
    STANDARD_TASK_OPT_FIELDS,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.base import BusinessEntity
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.task import Task

__all__ = [
    # Dataclasses (Phase 3)
    "HydrationResult",
    "HydrationBranch",
    "HydrationFailure",
    # Functions
    "hydrate_from_gid_async",
    "_traverse_upward_async",
    "_convert_to_typed_entity",
    "_is_recoverable",
]

logger = get_logger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Unified field set for all detection and traversal fetches.
# Per IMP-23: Use the full field set for initial fetch so that when Business is
# detected, no re-fetch is needed -- the task already has custom_fields populated
# for field cascading (Office Phone, Company ID, etc.).
_BUSINESS_FULL_OPT_FIELDS: list[str] = list(STANDARD_TASK_OPT_FIELDS)


# =============================================================================
# Dataclasses (Phase 3 - ADR-0070)
# =============================================================================


@dataclass
class HydrationBranch:
    """A successfully hydrated branch of the hierarchy.

    Per ADR-0070: Tracks successful hydration of a holder and its children.

    Attributes:
        holder_type: Type of holder that was hydrated (e.g., "contact_holder").
        holder_gid: GID of the holder task.
        child_count: Number of children populated in this branch.
    """

    holder_type: str
    holder_gid: str
    child_count: int


@dataclass
class HydrationFailure:
    """A branch that failed to hydrate.

    Per ADR-0070: Records failure details for partial hydration support.

    Attributes:
        holder_type: Type of holder that failed (e.g., "unit_holder").
        holder_gid: GID of the holder task (if known, may be None if fetch failed).
        phase: "downward" or "upward" indicating where failure occurred.
        error: The exception that caused the failure.
        recoverable: True if retry might succeed (transient error like rate limit).
    """

    holder_type: str
    holder_gid: str | None
    phase: Literal["downward", "upward"]
    error: Exception
    recoverable: bool


@dataclass
class HydrationResult:
    """Complete result of hydration operation.

    Per ADR-0070: Provides detailed tracking of hydration outcomes,
    supporting both fail-fast (default) and partial_ok modes.

    The `is_complete` property indicates whether hydration succeeded fully.
    When `partial_ok=True`, this result may contain both successful and
    failed branches, allowing callers to decide how to proceed.

    Attributes:
        business: The root Business entity (always populated, may be partial).
        entry_entity: The original entry entity for non-Business starts.
        entry_type: Detected type of the entry entity.
        path: Entities traversed during upward navigation (excluding Business).
        api_calls: Total API calls made during hydration.
        succeeded: List of successfully hydrated branches.
        failed: List of branches that failed to hydrate.
        warnings: Non-fatal issues encountered (e.g., empty holders).

    Example:
        result = await hydrate_from_gid_async(client, gid, partial_ok=True)
        if result.is_complete:
            # Full hydration succeeded
            process_business(result.business)
        else:
            # Partial hydration - check failures
            for failure in result.failed:
                logger.warning(f"Failed: {failure.holder_type}: {failure.error}")
            # Optionally still use partial result
            if any(f.recoverable for f in result.failed):
                # Could retry later
                pass
    """

    business: Business
    entry_entity: BusinessEntity | None = None
    entry_type: EntityType | None = None
    path: list[BusinessEntity] = field(default_factory=list)
    api_calls: int = 0
    succeeded: list[HydrationBranch] = field(default_factory=list)
    failed: list[HydrationFailure] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """True if hydration completed with no failures.

        When False, check the `failed` list for details about which
        branches failed and whether errors are recoverable.
        """
        return len(self.failed) == 0


def _is_recoverable(error: Exception) -> bool:
    """Classify error as transient (retry-worthy) or permanent.

    Per ADR-0070: Determines if an error might succeed on retry.

    Args:
        error: Exception to classify.

    Returns:
        True if error is likely transient (rate limit, timeout, server error).
        False if error is permanent (not found, forbidden, etc.).
    """
    from autom8_asana.errors import (
        ForbiddenError,
        NotFoundError,
        RateLimitError,
        ServerError,
        TimeoutError,
    )

    if isinstance(error, RateLimitError):
        return True
    if isinstance(error, TimeoutError):
        return True
    if isinstance(error, ServerError):
        return True  # 5xx errors may be transient
    if isinstance(error, NotFoundError):
        return False  # 404 = deleted, won't recover
    if isinstance(error, ForbiddenError):
        return False  # 403 = permission issue, won't recover
    return False  # Default: assume permanent


# =============================================================================
# Generic Entry Point (Phase 3 - ADR-0069)
# =============================================================================


async def hydrate_from_gid_async(
    client: AsanaClient,
    gid: str,
    *,
    hydrate_full: bool = True,
    partial_ok: bool = False,
) -> HydrationResult:
    """Hydrate business hierarchy from any task GID.

    Per TDD-HYDRATION Phase 3: Generic entry point for hydration from any
    entity in the hierarchy (Business, Contact, Offer, Unit, etc.).

    This function:
    1. Fetches the task by GID
    2. Detects its type using detect_entity_type_async()
    3. If Business, performs downward hydration via _fetch_holders_async()
    4. If other entity type, traverses upward to Business, then hydrates downward
    5. Returns HydrationResult with full metadata

    Args:
        client: AsanaClient for API calls.
        gid: Any task GID in the business hierarchy.
        hydrate_full: If True (default), hydrate full hierarchy after finding
            Business. If False, only locates the Business (useful for quick lookups).
        partial_ok: If True, continue on partial failures and return
            HydrationResult with failure details. If False (default), raise
            HydrationError on any failure (fail-fast behavior).

    Returns:
        HydrationResult containing:
        - business: The hydrated Business entity
        - entry_entity: The original entry entity (None if started at Business)
        - entry_type: Detected EntityType of the entry
        - path: Entities traversed during upward navigation
        - api_calls: Total API calls made
        - succeeded/failed: Branch-level success/failure details
        - is_complete: True if no failures occurred

    Raises:
        HydrationError: If hydration fails and partial_ok=False.
        NotFoundError: If the GID does not exist.

    Example:
        # From any GID, get full hydrated Business
        result = await hydrate_from_gid_async(client, offer_gid)
        business = result.business
        print(f"Business: {business.name}")
        print(f"API calls: {result.api_calls}")

        # With partial failure tolerance
        result = await hydrate_from_gid_async(client, gid, partial_ok=True)
        if not result.is_complete:
            for failure in result.failed:
                print(f"Warning: {failure.holder_type} failed: {failure.error}")
    """
    from autom8_asana.models.business.business import Business

    api_calls = 0
    path: list[BusinessEntity] = []
    entry_entity: BusinessEntity | None = None
    succeeded: list[HydrationBranch] = []
    failed: list[HydrationFailure] = []
    warnings: list[str] = []

    logger.info(
        "Starting hydration from GID",
        extra={"gid": gid, "hydrate_full": hydrate_full, "partial_ok": partial_ok},
    )

    # Step 1: Fetch the entry task with full fields
    # Per IMP-23: Use full field set upfront to avoid re-fetch when Business is detected.
    # Per ADR-0094: Include memberships.project.name for ProcessType detection.
    try:
        entry_task = await client.tasks.get_async(
            gid,
            opt_fields=_BUSINESS_FULL_OPT_FIELDS,
        )
        api_calls += 1
    except (
        Exception
    ) as e:  # BROAD-CATCH: boundary -- wraps diverse API+model failures into HydrationError
        # Cannot proceed without the entry task
        raise HydrationError(
            f"Failed to fetch entry task {gid}: {e}",
            entity_gid=gid,
            entity_type=None,
            phase="upward",
            cause=e,
        ) from e

    # Step 2: Detect entity type
    # Enable structure inspection to detect Business root from arbitrary GIDs
    detection_result = await detect_entity_type_async(
        entry_task, client, allow_structure_inspection=True
    )
    entry_type = detection_result.entity_type
    # Tier 4 structure inspection makes 1 API call (subtasks fetch)
    if detection_result.tier_used == 4:
        api_calls += 1

    logger.debug(
        "Detected entry type",
        extra={
            "gid": gid,
            "entry_type": entry_type.value,
            "task_name": entry_task.name,
            "detection_tier": detection_result.tier_used,
        },
    )

    # Step 3: Handle based on type
    if entry_type == EntityType.BUSINESS:
        # Already at Business root with full fields (per IMP-23: no re-fetch needed)
        business = Business.model_validate(entry_task, from_attributes=True)
        entry_entity = None  # Started at Business

        if hydrate_full:
            try:
                await business._fetch_holders_async(client)
                # Count API calls from hydration (estimate based on holders)
                api_calls += _estimate_hydration_calls(business)
                # Track successful branches
                succeeded.extend(_collect_success_branches(business))
            except Exception as e:  # BROAD-CATCH: catch-all-and-degrade -- partial_ok catches any hydration failure
                if partial_ok:
                    failed.append(
                        HydrationFailure(
                            holder_type="business_holders",
                            holder_gid=business.gid,
                            phase="downward",
                            error=e,
                            recoverable=_is_recoverable(e),
                        )
                    )
                    logger.warning(
                        "Hydration failed with partial_ok=True",
                        extra={"business_gid": business.gid, "error": str(e)},
                    )
                else:
                    raise HydrationError(
                        f"Downward hydration failed for Business {gid}: {e}",
                        entity_gid=gid,
                        entity_type="business",
                        phase="downward",
                        cause=e,
                    ) from e
    else:
        # Not at Business - need to traverse upward first
        typed_entry = _convert_to_typed_entity(entry_task, entry_type)
        entry_entity = typed_entry

        try:
            # Traverse upward to find Business
            business, path = await _traverse_upward_async(entry_task, client)
            # Estimate API calls for traversal (1 get per level + detection calls)
            api_calls += len(path) * 2 + 2
        except HydrationError:
            # Re-raise traversal errors - cannot continue without Business
            raise
        except (
            Exception
        ) as e:  # BROAD-CATCH: boundary -- wraps diverse traversal failures into HydrationError
            raise HydrationError(
                f"Upward traversal failed from {gid}: {e}",
                entity_gid=gid,
                entity_type=entry_type.value,
                phase="upward",
                cause=e,
            ) from e

        # Now hydrate the Business downward
        if hydrate_full:
            try:
                await business._fetch_holders_async(client)
                api_calls += _estimate_hydration_calls(business)
                succeeded.extend(_collect_success_branches(business))
            except Exception as e:  # BROAD-CATCH: catch-all-and-degrade -- partial_ok catches any hydration failure
                if partial_ok:
                    failed.append(
                        HydrationFailure(
                            holder_type="business_holders",
                            holder_gid=business.gid,
                            phase="downward",
                            error=e,
                            recoverable=_is_recoverable(e),
                        )
                    )
                    logger.warning(
                        "Hydration failed with partial_ok=True",
                        extra={"business_gid": business.gid, "error": str(e)},
                    )
                else:
                    raise HydrationError(
                        f"Downward hydration failed after traversal from {gid}: {e}",
                        entity_gid=gid,
                        entity_type=entry_type.value,
                        phase="downward",
                        partial_result=HydrationResult(
                            business=business,
                            entry_entity=entry_entity,
                            entry_type=entry_type,
                            path=path,
                            api_calls=api_calls,
                            succeeded=succeeded,
                            failed=failed,
                            warnings=warnings,
                        ),
                        cause=e,
                    ) from e

    # Build result
    result = HydrationResult(
        business=business,
        entry_entity=entry_entity,
        entry_type=entry_type,
        path=path,
        api_calls=api_calls,
        succeeded=succeeded,
        failed=failed,
        warnings=warnings,
    )

    logger.info(
        "Hydration complete",
        extra={
            "business_gid": business.gid,
            "business_name": business.name,
            "entry_type": entry_type.value,
            "api_calls": api_calls,
            "is_complete": result.is_complete,
            "succeeded_count": len(succeeded),
            "failed_count": len(failed),
        },
    )

    return result


def _estimate_hydration_calls(business: Business) -> int:
    """Estimate API calls made during hydration based on populated holders.

    This is an approximation - actual count depends on hierarchy depth.
    """
    calls = 1  # Initial subtasks call for business holders

    # Count populated holders
    holders = [
        business._contact_holder,
        business._unit_holder,
        business._location_holder,
        business._dna_holder,
        business._reconciliation_holder,
        business._asset_edit_holder,
        business._videography_holder,
    ]
    populated = sum(1 for h in holders if h is not None)
    calls += populated  # One subtasks call per holder

    # Count units and their nested holders
    if business._unit_holder is not None:
        for unit in business._unit_holder.units:  # type: ignore[attr-defined]
            calls += 1  # Unit subtasks call
            if unit._offer_holder is not None:
                calls += 1
            if unit._process_holder is not None:
                calls += 1

    return calls


def _collect_success_branches(business: Business) -> list[HydrationBranch]:
    """Collect HydrationBranch entries for successfully populated holders."""
    branches: list[HydrationBranch] = []

    if business._contact_holder is not None:
        branches.append(
            HydrationBranch(
                holder_type="contact_holder",
                holder_gid=business._contact_holder.gid,
                child_count=len(business._contact_holder.contacts),  # type: ignore[attr-defined]
            )
        )

    if business._unit_holder is not None:
        branches.append(
            HydrationBranch(
                holder_type="unit_holder",
                holder_gid=business._unit_holder.gid,
                child_count=len(business._unit_holder.units),  # type: ignore[attr-defined]
            )
        )
        # Also track nested holders
        for unit in business._unit_holder.units:  # type: ignore[attr-defined]
            if unit._offer_holder is not None:
                branches.append(
                    HydrationBranch(
                        holder_type="offer_holder",
                        holder_gid=unit._offer_holder.gid,
                        child_count=len(unit._offer_holder.offers),
                    )
                )
            if unit._process_holder is not None:
                branches.append(
                    HydrationBranch(
                        holder_type="process_holder",
                        holder_gid=unit._process_holder.gid,
                        child_count=len(unit._process_holder.processes),
                    )
                )

    if business._location_holder is not None:
        branches.append(
            HydrationBranch(
                holder_type="location_holder",
                holder_gid=business._location_holder.gid,
                child_count=len(business._location_holder.locations),  # type: ignore[attr-defined]
            )
        )

    if business._dna_holder is not None:
        branches.append(
            HydrationBranch(
                holder_type="dna_holder",
                holder_gid=business._dna_holder.gid,
                child_count=len(business._dna_holder.children),
            )
        )

    if business._reconciliation_holder is not None:
        branches.append(
            HydrationBranch(
                holder_type="reconciliations_holder",
                holder_gid=business._reconciliation_holder.gid,
                child_count=len(business._reconciliation_holder.children),
            )
        )

    if business._asset_edit_holder is not None:
        branches.append(
            HydrationBranch(
                holder_type="asset_edit_holder",
                holder_gid=business._asset_edit_holder.gid,
                child_count=len(business._asset_edit_holder.children),
            )
        )

    if business._videography_holder is not None:
        branches.append(
            HydrationBranch(
                holder_type="videography_holder",
                holder_gid=business._videography_holder.gid,
                child_count=len(business._videography_holder.children),
            )
        )

    return branches


# =============================================================================
# Upward Traversal (Phase 2)
# =============================================================================


async def _traverse_upward_async(
    entity: Task,
    client: AsanaClient,
    max_depth: int = 10,
) -> tuple[Business, list[BusinessEntity]]:
    """Walk parent chain to find Business root.

    Per TDD-HYDRATION: Upward Traversal Algorithm.

    This function implements the core upward traversal algorithm that:
    1. Starts with an entity (Contact, Offer, etc.)
    2. Follows parent references up the hierarchy
    3. Uses type detection to identify each parent
    4. Stops when Business is found
    5. Returns the Business and the path of entities traversed

    Algorithm:
        1. Start with entity, initialize visited set
        2. Get parent GID from entity.parent
        3. Fetch parent task
        4. Detect parent type
        5. If Business, return
        6. Otherwise, add to path and continue
        7. Safety: abort if depth > max_depth or cycle detected

    Args:
        entity: Starting entity (Task or BusinessEntity) with parent reference.
        client: AsanaClient for API calls.
        max_depth: Maximum traversal depth (default 10, actual hierarchy max is ~5).

    Returns:
        Tuple of (Business, path) where:
        - Business is the root entity found
        - path is list of BusinessEntity instances traversed (excluding Business)

    Raises:
        HydrationError: If:
            - Root reached without finding Business
            - Cycle detected in parent chain
            - Max depth exceeded
            - Parent reference is missing

    Example:
        # From Contact (depth 2 from Business)
        # Path: Contact -> ContactHolder -> Business
        business, path = await _traverse_upward_async(contact, client)
        assert len(path) == 1  # ContactHolder only

        # From Offer (depth 4 from Business)
        # Path: Offer -> OfferHolder -> Unit -> UnitHolder -> Business
        business, path = await _traverse_upward_async(offer, client)
        assert len(path) == 3  # OfferHolder, Unit, UnitHolder
    """
    visited: set[str] = {entity.gid}
    path: list[BusinessEntity] = []
    current: Task = entity
    depth = 0

    # Per NFR-OBS-001: Log traversal start at DEBUG level
    logger.debug(
        "Starting upward traversal",
        extra={"start_gid": entity.gid, "start_name": entity.name},
    )

    while depth < max_depth:
        # Check for parent reference
        if current.parent is None:
            raise HydrationError(
                f"Reached root without finding Business at task {current.gid} "
                f"(name: {current.name})",
                entity_gid=entity.gid,
                entity_type=None,
                phase="upward",
            )

        parent_gid = current.parent.gid

        # Cycle detection
        if parent_gid in visited:
            raise HydrationError(
                f"Cycle detected: GID {parent_gid} already visited. Visited: {visited}",
                entity_gid=entity.gid,
                entity_type=None,
                phase="upward",
            )
        visited.add(parent_gid)

        # Fetch parent task with full fields
        # Per IMP-23: Use full field set so no re-fetch is needed when Business is found.
        # Per ADR-0094: Include memberships.project.name for ProcessType detection.
        # Per NFR-OBS-001: Log parent fetch with gid, depth, field count at DEBUG level.
        logger.debug(
            "Fetching parent task",
            extra={
                "parent_gid": parent_gid,
                "depth": depth,
                "opt_fields_count": len(_BUSINESS_FULL_OPT_FIELDS),
            },
        )
        parent_task = await client.tasks.get_async(
            parent_gid,
            opt_fields=_BUSINESS_FULL_OPT_FIELDS,
        )

        # Detect type of parent
        # Enable structure inspection for traversal - we're already making API calls
        # and need full detection capability to find Business root
        detection_result = await detect_entity_type_async(
            parent_task, client, allow_structure_inspection=True
        )
        entity_type = detection_result.entity_type

        logger.debug(
            "Detected parent type",
            extra={
                "parent_gid": parent_gid,
                "parent_name": parent_task.name,
                "entity_type": entity_type.value,
                "detection_tier": detection_result.tier_used,
            },
        )

        if entity_type == EntityType.BUSINESS:
            # Found Business root - already has full fields (per IMP-23: no re-fetch needed)
            from autom8_asana.models.business.business import Business

            business = Business.model_validate(parent_task, from_attributes=True)

            # Per NFR-OBS-002: Log traversal completion with path length, business info at INFO level
            logger.info(
                "Upward traversal complete",
                extra={
                    "business_gid": business.gid,
                    "business_name": business.name,
                    "path_length": len(path),
                    "total_depth": depth + 1,
                    "path_gids": [e.gid for e in path],
                },
            )

            return business, path

        # Not Business - convert to typed entity and continue
        typed_entity = _convert_to_typed_entity(parent_task, entity_type)
        if typed_entity is not None:
            path.append(typed_entity)

        current = parent_task
        depth += 1

    # Max depth exceeded
    raise HydrationError(
        f"Max traversal depth ({max_depth}) exceeded. Path so far: {[e.gid for e in path]}",
        entity_gid=entity.gid,
        entity_type=None,
        phase="upward",
    )


def _convert_to_typed_entity(
    task: Task,
    entity_type: EntityType,
) -> BusinessEntity | None:
    """Convert a Task to its typed BusinessEntity based on detected type.

    Per FR-UP-004: Fetched parent Tasks are converted to typed entities.

    Args:
        task: Task to convert.
        entity_type: Detected type for the task.

    Returns:
        Typed BusinessEntity or None if type cannot be converted.
        Note: Returns BusinessEntity type for path tracking, though Holders
        technically inherit from Task with HolderMixin. The return value
        is used for path tracking and can be any Task subclass.
    """
    # Import here to avoid circular imports
    from autom8_asana.models.business.business import (
        AssetEditHolder,
        DNAHolder,
        ReconciliationHolder,
        VideographyHolder,
    )
    from autom8_asana.models.business.contact import Contact, ContactHolder
    from autom8_asana.models.business.hours import Hours
    from autom8_asana.models.business.location import Location, LocationHolder
    from autom8_asana.models.business.offer import Offer, OfferHolder
    from autom8_asana.models.business.process import Process, ProcessHolder
    from autom8_asana.models.business.unit import Unit, UnitHolder

    # Note: Holders inherit from Task with HolderMixin, not BusinessEntity.
    # We use type[Task] here to accommodate both BusinessEntity and Holder types.
    type_to_class: dict[EntityType, type[Task]] = {
        # Holders (Task + HolderMixin)  # noqa: ERA001
        EntityType.CONTACT_HOLDER: ContactHolder,
        EntityType.UNIT_HOLDER: UnitHolder,
        EntityType.OFFER_HOLDER: OfferHolder,
        EntityType.PROCESS_HOLDER: ProcessHolder,
        EntityType.LOCATION_HOLDER: LocationHolder,
        EntityType.DNA_HOLDER: DNAHolder,
        EntityType.RECONCILIATIONS_HOLDER: ReconciliationHolder,
        EntityType.ASSET_EDIT_HOLDER: AssetEditHolder,
        EntityType.VIDEOGRAPHY_HOLDER: VideographyHolder,
        # Entities (BusinessEntity -> Task)
        EntityType.UNIT: Unit,
        EntityType.CONTACT: Contact,
        EntityType.OFFER: Offer,
        EntityType.PROCESS: Process,
        EntityType.LOCATION: Location,
        EntityType.HOURS: Hours,
    }

    if entity_type in type_to_class:
        entity_class = type_to_class[entity_type]
        result = entity_class.model_validate(task, from_attributes=True)
        # Cast to BusinessEntity for return type - all these are Task subclasses
        # and are tracked in path for diagnostic purposes
        return result  # type: ignore[return-value]

    # UNKNOWN or BUSINESS (Business handled separately in traverse)
    logger.warning(
        "Cannot convert task to typed entity",
        extra={"task_gid": task.gid, "entity_type": entity_type.value},
    )
    return None
