"""Resolution context for session-scoped entity resolution.

Per TDD: Resolution Primitives -- ResolutionContext and ResolutionError.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from autom8y_log import get_logger

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.resolution.budget import ApiBudget
from autom8_asana.resolution.result import ResolutionResult, ResolutionStatus
from autom8_asana.resolution.selection import SelectionPredicate
from autom8_asana.resolution.strategies import (
    BUSINESS_CHAIN,
    DEFAULT_CHAIN,
    ResolutionStrategy,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.contact import Contact
    from autom8_asana.models.business.offer import Offer
    from autom8_asana.models.business.process import Process
    from autom8_asana.models.business.unit import Unit

logger = get_logger(__name__)

T = TypeVar("T", bound=BusinessEntity)


class ResolutionContext:
    """Session-scoped context for entity resolution.

    Manages:
    - Session cache (in-memory, per execution)
    - Strategy chain dispatch
    - API budget tracking
    - Convenience methods for common resolution patterns

    Usage:
        async with ResolutionContext(client, trigger_entity=process) as ctx:
            business = await ctx.business_async()
            phone = business.office_phone  # descriptor access

            contact = await ctx.contact_async(
                predicate=FieldPredicate("position", "Owner")
            )
            email = contact.email

    Args:
        client: AsanaClient for API operations.
        trigger_entity: The entity that triggered the workflow/action.
        business_gid: Optional Business GID if known (avoids traversal).
        max_api_calls: Maximum API calls per resolution chain (default: 8).
    """

    def __init__(
        self,
        client: AsanaClient,
        trigger_entity: BusinessEntity | None = None,
        business_gid: str | None = None,
        max_api_calls: int = 8,
    ) -> None:
        self._client = client
        self._trigger_entity = trigger_entity
        self._business_gid = business_gid
        self._max_api_calls = max_api_calls

        # Session cache: GID -> entity
        self._session_cache: dict[str, BusinessEntity] = {}
        # Track whether Business subtasks have been fetched
        self._holders_fetched: bool = False

    @property
    def client(self) -> AsanaClient:
        """AsanaClient for API operations."""
        return self._client

    async def __aenter__(self) -> ResolutionContext:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Clear session cache on exit
        self._session_cache.clear()

    # --- Session Cache ---

    def cache_entity(self, entity: BusinessEntity) -> None:
        """Store entity in session cache."""
        self._session_cache[entity.gid] = entity

    def get_cached(
        self,
        target_type: type[T],
    ) -> T | None:
        """Get cached entity by type.

        Simple lookup: iterate cache for matching type.
        For small cache sizes (< 20 entities), linear scan is fine.
        """
        for entity in self._session_cache.values():
            if isinstance(entity, target_type):
                return entity
        return None

    def get_cached_business(self) -> Business | None:
        """Get cached Business (convenience)."""
        from autom8_asana.models.business.business import Business

        return self.get_cached(Business)

    # --- Low-Level Resolution (Layer 1) ---

    async def resolve_entity_async(
        self,
        target_type: type[T],
        *,
        from_entity: BusinessEntity | None = None,
        predicate: SelectionPredicate | None = None,
        chain: list[ResolutionStrategy] | None = None,
    ) -> ResolutionResult[T]:
        """Resolve entity using strategy chain.

        Args:
            target_type: Type of entity to resolve.
            from_entity: Starting entity for traversal. Defaults to trigger_entity.
            predicate: Selection criteria for choosing among siblings.
            chain: Override strategy chain. Defaults to type-appropriate chain.

        Returns:
            ResolutionResult with resolved entity or failure diagnostics.
        """
        from autom8_asana.models.business.business import Business

        source = from_entity or self._trigger_entity
        if source is None:
            return ResolutionResult.failed(
                diagnostics=["No source entity for resolution"],
            )

        strategies = chain or (
            BUSINESS_CHAIN if target_type is Business else DEFAULT_CHAIN
        )
        budget = ApiBudget(max_calls=self._max_api_calls)
        diagnostics: list[str] = []

        for strategy in strategies:
            if budget.exhausted:
                return ResolutionResult(
                    status=ResolutionStatus.BUDGET_EXHAUSTED,
                    api_calls_used=budget.used,
                    diagnostics=diagnostics
                    + [f"Budget exhausted after {budget.used} API calls"],
                )

            result = await strategy.resolve_async(
                target_type,
                context=self,
                from_entity=source,
                budget=budget,
            )

            if result is not None:
                return result

            diagnostics.append(f"{strategy.name}: no result")

        return ResolutionResult.failed(
            diagnostics=diagnostics,
            api_calls=budget.used,
        )

    # --- High-Level Convenience Methods (Layer 2) ---

    async def business_async(self) -> Business:
        """Resolve and cache Business entity.

        Returns:
            Business entity.

        Raises:
            ResolutionError: If Business cannot be resolved.
        """
        from autom8_asana.models.business.business import Business

        # Fast path: direct GID
        if self._business_gid:
            cached = self._session_cache.get(self._business_gid)
            if cached is not None:
                return cached  # type: ignore[return-value]  # cache stores BusinessEntity, caller expects Business subtype

            business = await Business.from_gid_async(
                self._client, self._business_gid, hydrate=False
            )
            self.cache_entity(business)
            return business

        # Resolution path
        result = await self.resolve_entity_async(Business)
        if result.success and result.entity is not None:
            return result.entity

        raise ResolutionError(f"Cannot resolve Business: {result.diagnostics}")

    async def unit_async(
        self,
        predicate: SelectionPredicate | None = None,
    ) -> Unit:
        """Resolve and cache Unit entity.

        Args:
            predicate: Selection criteria (e.g., vertical match).

        Returns:
            Unit entity.

        Raises:
            ResolutionError: If Unit cannot be resolved.
        """
        from autom8_asana.models.business.unit import Unit

        result = await self.resolve_entity_async(Unit, predicate=predicate)
        if result.success and result.entity is not None:
            return result.entity

        raise ResolutionError(f"Cannot resolve Unit: {result.diagnostics}")

    async def contact_async(
        self,
        predicate: SelectionPredicate | None = None,
    ) -> Contact:
        """Resolve and cache Contact entity.

        Args:
            predicate: Selection criteria (e.g., position="Owner").

        Returns:
            Contact entity.

        Raises:
            ResolutionError: If Contact cannot be resolved.
        """
        from autom8_asana.models.business.contact import Contact

        result = await self.resolve_entity_async(Contact, predicate=predicate)
        if result.success and result.entity is not None:
            return result.entity

        raise ResolutionError(f"Cannot resolve Contact: {result.diagnostics}")

    async def offer_async(
        self,
        predicate: SelectionPredicate | None = None,
    ) -> Offer:
        """Resolve and cache Offer entity.

        Args:
            predicate: Selection criteria (e.g., offer_id match).

        Returns:
            Offer entity.

        Raises:
            ResolutionError: If Offer cannot be resolved.
        """
        from autom8_asana.models.business.offer import Offer

        result = await self.resolve_entity_async(Offer, predicate=predicate)
        if result.success and result.entity is not None:
            return result.entity

        raise ResolutionError(f"Cannot resolve Offer: {result.diagnostics}")

    async def process_async(self) -> Process:
        """Resolve current active Process.

        Returns:
            Process entity.

        Raises:
            ResolutionError: If Process cannot be resolved.
        """
        from autom8_asana.models.business.process import Process

        result = await self.resolve_entity_async(Process)
        if result.success and result.entity is not None:
            return result.entity

        raise ResolutionError(f"Cannot resolve Process: {result.diagnostics}")

    # --- Holder Resolution (Layer 2) ---

    async def resolve_holder_async(
        self,
        holder_type: type[T],
        parent_gid: str | None = None,
    ) -> T | None:
        """Resolve a holder entity (ProcessHolder, DNAHolder, etc.) from parent subtasks.

        Fetches the subtasks of the parent entity (typically a Business) and
        matches them against the holder_type's PRIMARY_PROJECT_GID. Results
        are cached in the session cache for subsequent lookups.

        This method consumes 1 API call (subtask listing). The budget is
        checked before making the call.

        Args:
            holder_type: The holder class to resolve (e.g., ProcessHolder, DNAHolder).
                Must have a PRIMARY_PROJECT_GID class variable.
            parent_gid: GID of the parent entity to search under.
                If None, uses the business_gid from context.

        Returns:
            The resolved holder entity, or None if not found.
        """
        from pydantic import ValidationError

        # Check session cache first
        cached = self.get_cached(holder_type)
        if cached is not None:
            return cached

        # Determine parent GID
        effective_parent_gid = parent_gid or self._business_gid
        if effective_parent_gid is None:
            # Try to get parent GID from trigger entity's parent
            if self._trigger_entity is not None:
                parent_attr = getattr(self._trigger_entity, "parent", None)
                if parent_attr is not None:
                    effective_parent_gid = getattr(parent_attr, "gid", None)

        if effective_parent_gid is None:
            logger.warning(
                "resolve_holder_no_parent_gid",
                holder_type=holder_type.__name__,
            )
            return None

        # Check API budget (need at least 1 call for subtask listing)
        budget = ApiBudget(max_calls=self._max_api_calls)
        if budget.exhausted:
            logger.warning(
                "resolve_holder_budget_exhausted",
                holder_type=holder_type.__name__,
                parent_gid=effective_parent_gid,
            )
            return None

        # Get holder's PRIMARY_PROJECT_GID for matching
        holder_project_gid: str | None = getattr(
            holder_type, "PRIMARY_PROJECT_GID", None
        )
        if holder_project_gid is None:
            logger.warning(
                "resolve_holder_no_project_gid",
                holder_type=holder_type.__name__,
            )
            return None

        # Fetch subtasks of parent (1 API call)
        subtasks = await self._client.tasks.subtasks_async(
            effective_parent_gid, include_detection_fields=True
        ).collect()
        budget.consume(1)

        # Match subtasks against holder_type's PRIMARY_PROJECT_GID
        for subtask in subtasks:
            # Check projects list for matching GID
            projects = getattr(subtask, "projects", None) or []
            for project in projects:
                project_gid = getattr(project, "gid", None)
                if project_gid == holder_project_gid:
                    # Found matching subtask -- cast to holder type
                    try:
                        holder = holder_type.model_validate(subtask.model_dump())
                        self.cache_entity(holder)
                        logger.info(
                            "resolve_holder_found",
                            holder_type=holder_type.__name__,
                            holder_gid=holder.gid,
                            parent_gid=effective_parent_gid,
                        )
                        return holder
                    except (ValueError, ValidationError):
                        logger.debug(
                            "resolve_holder_cast_failed",
                            holder_type=holder_type.__name__,
                            subtask_gid=subtask.gid,
                        )
                        continue

        logger.warning(
            "resolve_holder_not_found",
            holder_type=holder_type.__name__,
            parent_gid=effective_parent_gid,
            subtask_count=len(subtasks),
        )
        return None

    # --- Branch Hydration (ADR-005) ---

    async def hydrate_branch_async(
        self,
        business: Business,
        holder_key: str,
    ) -> None:
        """Hydrate a single holder branch on a Business.

        Fetches Business subtasks (once) then populates the specific holder
        and its children. This is 2-3 API calls vs 15-25 for full hydration.

        Args:
            business: Business entity (hydrate=False).
            holder_key: Holder property name (e.g., "contact_holder").
        """
        # Step 1: Fetch holders if not yet done (1 API call, cached)
        if not self._holders_fetched:
            holder_tasks = await self._client.tasks.subtasks_async(
                business.gid, include_detection_fields=True
            ).collect()
            business._populate_holders(holder_tasks)
            self._holders_fetched = True

        # Step 2: Fetch children for the specific holder (1 API call)
        holder = getattr(business, f"_{holder_key}", None)
        if holder is not None and not getattr(holder, "_children_cache", None):
            # Determine children attribute based on holder type
            children_attr = getattr(
                holder.__class__, "CHILDREN_ATTR", "_children_cache"
            )
            await business._fetch_holder_children_async(
                self._client, holder, children_attr
            )


class ResolutionError(Exception):
    """Raised when entity resolution fails."""
