# TDD: Resolution Primitives

**Date**: 2026-02-11
**Status**: Design Complete
**Architect**: Moonshot Architect
**ADRs**: ADR-001, ADR-002, ADR-003, ADR-004, ADR-005
**Implements**: Workflow Resolution Platform -- Phase 1

---

## 1. Overview

This TDD defines the resolution system that enables workflows and actions to access entity data through the existing descriptor-based entity model. It replaces bespoke resolution code (like `ConversationAuditWorkflow._resolve_office_phone()`) with shared, typed, session-cached primitives.

### 1.1 Design Principles

1. **Entity-native access**: `business.office_phone` via descriptors, not string matching
2. **Automatic session caching**: No duplicate API calls within a single execution
3. **Lazy pull**: Fetch only what is needed, when it is needed
4. **Bounded API calls**: Maximum 8 API calls per resolution, fail after budget
5. **Structured results**: Every resolution returns success/partial/failed with diagnostics
6. **Shared primitives**: Actions and Workflows use the same resolution system

### 1.2 File Locations

New files:

| File | Purpose |
|------|---------|
| `src/autom8_asana/resolution/__init__.py` | Package exports |
| `src/autom8_asana/resolution/context.py` | ResolutionContext (session cache + convenience methods) |
| `src/autom8_asana/resolution/result.py` | ResolutionResult, ResolutionStatus |
| `src/autom8_asana/resolution/budget.py` | ApiBudget (call counting + enforcement) |
| `src/autom8_asana/resolution/strategies.py` | Strategy ABC + concrete strategies |
| `src/autom8_asana/resolution/selection.py` | SelectionPredicate, selection strategies |
| `src/autom8_asana/resolution/registry.py` | ResolutionStrategyRegistry |
| `tests/unit/resolution/` | Unit tests for all resolution modules |
| `tests/integration/resolution/` | Integration tests with mock Asana API |

Modified files:

| File | Change |
|------|--------|
| `src/autom8_asana/automation/workflows/conversation_audit.py` | Refactor to use ResolutionContext |

---

## 2. ResolutionResult

Every resolution operation returns a typed result, never raw entities or None.

```python
# src/autom8_asana/resolution/result.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Generic, TypeVar

from autom8_asana.models.business.base import BusinessEntity

T = TypeVar("T", bound=BusinessEntity)


class ResolutionStatus(str, Enum):
    """Outcome of a resolution attempt."""

    RESOLVED = "resolved"          # Entity found with full confidence
    PARTIAL = "partial"            # Entity found but data may be incomplete
    FAILED = "failed"              # All strategies exhausted
    BUDGET_EXHAUSTED = "budget_exhausted"  # API call budget reached


@dataclass(frozen=True)
class ResolutionResult(Generic[T]):
    """Structured result of entity resolution.

    Attributes:
        status: Resolution outcome.
        entity: Resolved entity (None if failed).
        api_calls_used: Number of API calls consumed.
        strategy_used: Name of the strategy that resolved (or last attempted).
        diagnostics: Human-readable explanation of resolution path.
    """

    status: ResolutionStatus
    entity: T | None = None
    api_calls_used: int = 0
    strategy_used: str = ""
    diagnostics: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if entity was resolved (RESOLVED or PARTIAL)."""
        return self.status in (ResolutionStatus.RESOLVED, ResolutionStatus.PARTIAL)

    @staticmethod
    def resolved(
        entity: T,
        api_calls: int = 0,
        strategy: str = "",
    ) -> ResolutionResult[T]:
        """Factory for successful resolution."""
        return ResolutionResult(
            status=ResolutionStatus.RESOLVED,
            entity=entity,
            api_calls_used=api_calls,
            strategy_used=strategy,
        )

    @staticmethod
    def failed(
        diagnostics: list[str],
        api_calls: int = 0,
        strategy: str = "",
    ) -> ResolutionResult:
        """Factory for failed resolution."""
        return ResolutionResult(
            status=ResolutionStatus.FAILED,
            api_calls_used=api_calls,
            strategy_used=strategy,
            diagnostics=diagnostics,
        )
```

---

## 3. ApiBudget

Prevents unbounded API call chains (legacy anti-pattern: 6-7 level resolution chains).

```python
# src/autom8_asana/resolution/budget.py

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ApiBudget:
    """Tracks and enforces API call budget for a resolution chain.

    Attributes:
        max_calls: Maximum API calls allowed.
        used: Number of API calls consumed so far.
    """

    max_calls: int = 8
    used: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.max_calls - self.used)

    @property
    def exhausted(self) -> bool:
        return self.used >= self.max_calls

    def consume(self, count: int = 1) -> None:
        """Record API calls consumed.

        Args:
            count: Number of API calls to record.

        Raises:
            BudgetExhaustedError: If budget is already exhausted.
        """
        if self.exhausted:
            raise BudgetExhaustedError(
                f"API budget exhausted: {self.used}/{self.max_calls} calls used"
            )
        self.used += count


class BudgetExhaustedError(Exception):
    """Raised when API call budget is exhausted."""
```

---

## 4. Resolution Strategies

### 4.1 Strategy ABC

```python
# src/autom8_asana/resolution/strategies.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.resolution.budget import ApiBudget
from autom8_asana.resolution.result import ResolutionResult

if TYPE_CHECKING:
    from autom8_asana.resolution.context import ResolutionContext

T = TypeVar("T", bound=BusinessEntity)


class ResolutionStrategy(ABC):
    """Base class for entity resolution strategies.

    Each strategy attempts one approach to resolving an entity.
    Returns ResolutionResult if successful, None to pass to next strategy.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name for diagnostics."""
        ...

    @abstractmethod
    async def resolve_async(
        self,
        target_type: type[T],
        context: ResolutionContext,
        *,
        from_entity: BusinessEntity,
        budget: ApiBudget,
    ) -> ResolutionResult[T] | None:
        """Attempt to resolve entity.

        Args:
            target_type: Type of entity to resolve.
            context: Resolution context with client and session cache.
            from_entity: Starting entity for traversal.
            budget: API call budget tracker.

        Returns:
            ResolutionResult if resolved, None to try next strategy.
        """
        ...
```

### 4.2 Concrete Strategies

#### SessionCacheStrategy

Zero API calls. Checks the session cache for a previously resolved entity.

```python
class SessionCacheStrategy(ResolutionStrategy):
    """Check session cache for previously resolved entity."""

    @property
    def name(self) -> str:
        return "session_cache"

    async def resolve_async(
        self,
        target_type: type[T],
        context: ResolutionContext,
        *,
        from_entity: BusinessEntity,
        budget: ApiBudget,
    ) -> ResolutionResult[T] | None:
        cached = context.get_cached(target_type, from_entity)
        if cached is not None:
            return ResolutionResult.resolved(
                entity=cached,
                api_calls=0,
                strategy=self.name,
            )
        return None
```

#### NavigationRefStrategy

Zero API calls. Uses existing in-memory navigation references (e.g., `process._unit`, `contact._business`).

```python
class NavigationRefStrategy(ResolutionStrategy):
    """Use existing in-memory navigation references."""

    @property
    def name(self) -> str:
        return "navigation_ref"

    async def resolve_async(
        self,
        target_type: type[T],
        context: ResolutionContext,
        *,
        from_entity: BusinessEntity,
        budget: ApiBudget,
    ) -> ResolutionResult[T] | None:
        # Walk known navigation paths
        resolved = self._walk_refs(from_entity, target_type)
        if resolved is not None:
            context.cache_entity(resolved)
            return ResolutionResult.resolved(
                entity=resolved,
                api_calls=0,
                strategy=self.name,
            )
        return None

    def _walk_refs(
        self,
        entity: BusinessEntity,
        target_type: type[T],
    ) -> T | None:
        """Walk in-memory references to find target type."""
        if isinstance(entity, target_type):
            return entity

        # Walk upward references
        for attr_name in entity._CACHED_REF_ATTRS:
            ref = getattr(entity, attr_name, None)
            if ref is not None and isinstance(ref, target_type):
                return ref

        return None
```

#### DependencyShortcutStrategy

2 API calls. Fetches dependencies/dependents and checks if target entity is linked.

```python
class DependencyShortcutStrategy(ResolutionStrategy):
    """Resolve via Asana dependency links (2 API calls)."""

    @property
    def name(self) -> str:
        return "dependency_shortcut"

    async def resolve_async(
        self,
        target_type: type[T],
        context: ResolutionContext,
        *,
        from_entity: BusinessEntity,
        budget: ApiBudget,
    ) -> ResolutionResult[T] | None:
        if budget.remaining < 2:
            return None

        # Fetch dependencies for the source entity
        deps = await context.client.tasks.dependencies_async(
            from_entity.gid
        ).collect()
        budget.consume(1)

        # Check each dependency for target type match
        for dep in deps:
            dep_task = await context.client.tasks.get_async(dep.gid)
            budget.consume(1)

            entity = self._try_cast(dep_task, target_type)
            if entity is not None:
                context.cache_entity(entity)
                return ResolutionResult.resolved(
                    entity=entity,
                    api_calls=2,
                    strategy=self.name,
                )

            if budget.exhausted:
                return None

        return None
```

#### HierarchyTraversalStrategy

3-5 API calls. Traverses up to Business, then down to target holder and entity.

```python
class HierarchyTraversalStrategy(ResolutionStrategy):
    """Resolve via parent chain traversal (3-5 API calls)."""

    @property
    def name(self) -> str:
        return "hierarchy_traversal"

    async def resolve_async(
        self,
        target_type: type[T],
        context: ResolutionContext,
        *,
        from_entity: BusinessEntity,
        budget: ApiBudget,
    ) -> ResolutionResult[T] | None:
        if budget.remaining < 3:
            return None

        from autom8_asana.models.business.business import Business

        # Step 1: Traverse up to Business
        business = await self._traverse_to_business_async(
            from_entity, context, budget
        )
        if business is None:
            return None

        # Step 2: If target IS Business, we are done
        if target_type is Business:
            return ResolutionResult.resolved(
                entity=business,
                api_calls=budget.used,
                strategy=self.name,
            )

        # Step 3: Hydrate the specific branch needed
        holder_key = self._get_holder_key(target_type)
        if holder_key is None:
            return None

        await context.hydrate_branch_async(business, holder_key)
        budget.consume(2)  # holder subtasks + holder children

        # Step 4: Find target entity in hydrated branch
        entity = self._find_in_branch(business, target_type, holder_key)
        if entity is not None:
            context.cache_entity(entity)
            return ResolutionResult.resolved(
                entity=entity,
                api_calls=budget.used,
                strategy=self.name,
            )

        return None

    async def _traverse_to_business_async(
        self,
        entity: BusinessEntity,
        context: ResolutionContext,
        budget: ApiBudget,
    ) -> Business | None:
        """Walk parent chain to reach Business."""
        from autom8_asana.models.business.business import Business

        # Check session cache first
        cached_business = context.get_cached_business()
        if cached_business is not None:
            return cached_business

        current = entity
        depth = 0
        max_depth = 5  # Business -> UnitHolder -> Unit -> ProcessHolder -> Process

        while depth < max_depth:
            if isinstance(current, Business):
                context.cache_entity(current)
                return current

            if budget.exhausted:
                return None

            # Fetch parent
            parent_task = await context.client.tasks.get_async(
                current.gid, opt_fields=["parent", "parent.gid"]
            )
            budget.consume(1)

            if parent_task.parent is None or parent_task.parent.gid is None:
                return None

            parent = await context.client.tasks.get_async(parent_task.parent.gid)
            budget.consume(1)

            # Try to cast parent to Business
            try:
                business = Business.model_validate(parent.model_dump())
                context.cache_entity(business)
                return business
            except Exception:
                pass

            current = parent
            depth += 1

        return None
```

### 4.3 Default Strategy Chains

```python
# Default chain for most entity types
DEFAULT_CHAIN = [
    SessionCacheStrategy(),
    NavigationRefStrategy(),
    DependencyShortcutStrategy(),
    HierarchyTraversalStrategy(),
]

# Chain for Business (simpler -- no dependency shortcut needed)
BUSINESS_CHAIN = [
    SessionCacheStrategy(),
    NavigationRefStrategy(),
    HierarchyTraversalStrategy(),
]
```

---

## 5. Entity Selection

### 5.1 SelectionPredicate

```python
# src/autom8_asana/resolution/selection.py

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from autom8_asana.models.business.base import BusinessEntity


class SelectionPredicate(ABC):
    """Predicate for selecting entities within a holder."""

    @abstractmethod
    def matches(self, entity: BusinessEntity) -> bool:
        """Return True if entity matches this predicate."""
        ...


@dataclass(frozen=True)
class FieldPredicate(SelectionPredicate):
    """Match entity by custom field value.

    Example:
        FieldPredicate("position", "Owner")  # Contact where position == "Owner"
    """

    field_name: str
    expected_value: Any

    def matches(self, entity: BusinessEntity) -> bool:
        actual = entity.get_custom_fields().get(self.field_name)
        if isinstance(actual, dict):
            actual = actual.get("name", actual.get("display_value"))
        return actual == self.expected_value


@dataclass(frozen=True)
class CompoundPredicate(SelectionPredicate):
    """AND/OR composition of predicates.

    Example:
        CompoundPredicate(
            operator="and",
            predicates=[
                FieldPredicate("position", "Owner"),
                FieldPredicate("status", "Active"),
            ],
        )
    """

    operator: str  # "and" | "or"
    predicates: list[SelectionPredicate]

    def matches(self, entity: BusinessEntity) -> bool:
        if self.operator == "and":
            return all(p.matches(entity) for p in self.predicates)
        return any(p.matches(entity) for p in self.predicates)


@dataclass(frozen=True)
class NewestActivePredicate(SelectionPredicate):
    """Select newest non-completed entity, or newest overall.

    Business rule: If newer entity is completed and older is incomplete,
    the incomplete one wins (represents active work).

    Used for ProcessHolder selection (most complex case).
    """

    process_type: str | None = None  # Filter by ProcessType if set

    def matches(self, entity: BusinessEntity) -> bool:
        # This predicate is used by selection strategies, not for filtering
        # The selection strategy handles ordering logic
        return True
```

### 5.2 Selection Strategies

```python
class EntitySelector:
    """Selects entity from holder children based on predicate.

    Implements selection strategies per holder type:
    - ContactHolder: top-level default, custom field override
    - ProcessHolder: newest-active with ProcessType filter
    - OfferHolder: offer_id match, top-level fallback
    - LocationHolder: type-based (Location vs Hours)
    """

    def select(
        self,
        children: list[BusinessEntity],
        predicate: SelectionPredicate | None = None,
    ) -> BusinessEntity | None:
        """Select single entity from children.

        Args:
            children: List of holder children.
            predicate: Selection criteria. If None, returns first child.

        Returns:
            Selected entity, or None if no match.
        """
        if not children:
            return None

        if predicate is None:
            return children[0]  # top-level default

        matching = [c for c in children if predicate.matches(c)]
        return matching[0] if matching else None

    def select_all(
        self,
        children: list[BusinessEntity],
        predicate: SelectionPredicate | None = None,
    ) -> list[BusinessEntity]:
        """Select all matching entities from children.

        For multi-result selection (e.g., "all contacts except Owner").

        Args:
            children: List of holder children.
            predicate: Selection criteria. If None, returns all.

        Returns:
            List of matching entities.
        """
        if predicate is None:
            return list(children)
        return [c for c in children if predicate.matches(c)]


class ProcessSelector:
    """Specialized selection for ProcessHolder children.

    Handles the most complex selection: newest created_at with
    completion-status override (incomplete beats newer completed).
    """

    def select_current(
        self,
        processes: list[Process],
        process_type: ProcessType | None = None,
    ) -> Process | None:
        """Select current active process.

        Algorithm:
        1. Filter by process_type if specified
        2. Sort by created_at descending (newest first)
        3. If newest is completed and older is incomplete, prefer incomplete
        """
        candidates = processes
        if process_type is not None:
            candidates = [p for p in candidates if p.process_type == process_type]

        if not candidates:
            return None

        # Sort newest first
        sorted_procs = sorted(
            candidates,
            key=lambda p: p.created_at or "",
            reverse=True,
        )

        # Check completion status: incomplete beats newer completed
        newest = sorted_procs[0]
        if newest.completed and len(sorted_procs) > 1:
            for older in sorted_procs[1:]:
                if not older.completed:
                    return older

        return newest
```

---

## 6. ResolutionContext

The primary API for workflows and actions.

```python
# src/autom8_asana/resolution/context.py

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
    from autom8_asana.models.business.contact import Contact, ContactHolder
    from autom8_asana.models.business.offer import Offer
    from autom8_asana.models.business.process import Process
    from autom8_asana.models.business.unit import Unit
    from autom8_asana.models.task import Task

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
        from_entity: BusinessEntity | None = None,
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
                    diagnostics=diagnostics + [
                        f"Budget exhausted after {budget.used} API calls"
                    ],
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
                return cached

            business = await Business.from_gid_async(
                self._client, self._business_gid, hydrate=False
            )
            self.cache_entity(business)
            return business

        # Resolution path
        result = await self.resolve_entity_async(Business)
        if result.success and result.entity is not None:
            return result.entity

        raise ResolutionError(
            f"Cannot resolve Business: {result.diagnostics}"
        )

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

        raise ResolutionError(
            f"Cannot resolve Unit: {result.diagnostics}"
        )

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

        raise ResolutionError(
            f"Cannot resolve Contact: {result.diagnostics}"
        )

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

        raise ResolutionError(
            f"Cannot resolve Offer: {result.diagnostics}"
        )

    async def process_async(
        self,
        process_type: ProcessType | None = None,
    ) -> Process:
        """Resolve current active Process.

        Args:
            process_type: Filter by ProcessType (e.g., SALES, ONBOARDING).

        Returns:
            Process entity.

        Raises:
            ResolutionError: If Process cannot be resolved.
        """
        from autom8_asana.models.business.process import Process

        result = await self.resolve_entity_async(Process)
        if result.success and result.entity is not None:
            return result.entity

        raise ResolutionError(
            f"Cannot resolve Process: {result.diagnostics}"
        )

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
        if holder is not None and not holder.children:
            await business._fetch_holder_children_async(
                self._client, holder, holder.CHILDREN_ATTR
            )


class ResolutionError(Exception):
    """Raised when entity resolution fails."""
```

---

## 7. ConversationAuditWorkflow Refactoring Plan

### 7.1 Current Implementation (The Smell)

```python
# BEFORE: 25 lines of bespoke resolution code
async def _resolve_office_phone(self, holder_gid: str) -> str | None:
    holder_task = await self._asana_client.tasks.get_async(
        holder_gid, opt_fields=["parent", "parent.gid"]
    )
    parent_ref = holder_task.parent
    if not parent_ref or not parent_ref.gid:
        return None
    parent_task = await self._asana_client.tasks.get_async(
        parent_ref.gid,
        opt_fields=["custom_fields", "custom_fields.name", "custom_fields.display_value"],
    )
    if parent_task.custom_fields:
        for cf in parent_task.custom_fields:
            cf_dict = cf if isinstance(cf, dict) else cf.model_dump()
            if cf_dict.get("name") == "Office Phone":
                return cf_dict.get("display_value") or cf_dict.get("text_value")
    return None
```

### 7.2 Refactored Implementation

```python
# AFTER: 6 lines using resolution primitives
async def _resolve_office_phone(self, holder_gid: str) -> str | None:
    holder_task = await self._asana_client.tasks.get_async(
        holder_gid, opt_fields=["parent", "parent.gid"]
    )
    if not holder_task.parent or not holder_task.parent.gid:
        return None

    async with ResolutionContext(
        self._asana_client,
        business_gid=holder_task.parent.gid,
    ) as ctx:
        business = await ctx.business_async()
        return business.office_phone  # Descriptor access
```

### 7.3 What Changes

| Aspect | Before | After |
|--------|--------|-------|
| Field access | `cf_dict.get("name") == "Office Phone"` | `business.office_phone` |
| Type safety | None (string matching) | `str \| None` from TextField descriptor |
| API calls | 2 per holder (same) | 2 per holder (1 parent lookup + 1 Business fetch) |
| Caching | None | Session cache (Business cached across holders) |
| Error handling | Returns None silently | Returns None (same behavior, but resolution diagnostics available) |

### 7.4 Optimization: Shared Business Cache

The current implementation creates 2 API calls per holder. With N holders, that is 2N calls. But many holders share the same Business parent.

With ResolutionContext:

```python
async def execute_async(self, params: dict[str, Any]) -> WorkflowResult:
    # Create ONE resolution context shared across all holders
    holders = await self._enumerate_contact_holders()

    # Group holders by parent Business GID
    # (all ContactHolders in the same Business share the same parent)
    business_gid = holders[0]["parent"]["gid"] if holders else None

    async with ResolutionContext(
        self._asana_client,
        business_gid=business_gid,
    ) as ctx:
        # Business is fetched ONCE, then cached for all holders
        for holder in holders:
            await self._process_holder(holder, ctx)
```

This reduces API calls from 2N to N+1 (1 Business fetch + N holder fetches).

### 7.5 Test Impact

**Existing tests continue to pass**: The refactoring does not change the public API of `ConversationAuditWorkflow`. The `execute_async` method still returns `WorkflowResult`. The `_resolve_office_phone` method signature is unchanged.

**New tests needed**:
- `tests/unit/resolution/test_context.py`: ResolutionContext session caching
- `tests/unit/resolution/test_strategies.py`: Each strategy in isolation
- `tests/unit/resolution/test_selection.py`: Predicate matching
- `tests/unit/resolution/test_budget.py`: Budget enforcement
- `tests/integration/resolution/test_conversation_audit_refactored.py`: End-to-end with mock API

---

## 8. Integration with Existing Systems

### 8.1 ActionExecutor Integration

ActionExecutor currently has no resolution support. With shared primitives:

```python
class ActionExecutor:
    async def execute_async(
        self,
        task_gid: str,
        action: ActionConfig,
    ) -> ActionResult:
        # Create resolution context for this action execution
        trigger_task = await self._client.tasks.get_async(task_gid)
        entity = BusinessEntity.model_validate(trigger_task.model_dump())

        async with ResolutionContext(
            self._client,
            trigger_entity=entity,
        ) as ctx:
            # Actions can now resolve entities as needed
            return await self._dispatch_action(task_gid, action, ctx)
```

### 8.2 Warm Cache Integration

The existing S3/Redis cache is leveraged through the hierarchy traversal strategy. When `HierarchyTraversalStrategy` fetches a Business or Unit, those entities may already be in the warm cache (TTL 3600s for Business, 900s for Unit).

The resolution system does NOT modify the warm cache. It reads from it when entities are fetched via the AsanaClient (which already checks cache). Session cache is strictly in-memory and per-execution.

### 8.3 Entity Registry Integration

The resolution strategy registry follows the same pattern as existing registries (EntityProjectRegistry, WorkspaceProjectRegistry):
- Explicit registration at bootstrap
- Reset method for test isolation
- Thread-safe (no concurrent modification during resolution)

---

## 9. Resolution Depth

### 9.1 Legacy Analysis

The legacy codebase has 6-7 step resolution chains for Process.unit and Process.offer. Each step involves isinstance dispatch and potentially triggers additional API calls.

### 9.2 First-Principles Redesign

The resolution system bounds depth via `ApiBudget` (default: 8 API calls) rather than step counting. This is more meaningful because:

- A 2-step resolution with 4 API calls per step (8 calls) is more expensive than a 4-step resolution with 1 API call per step (4 calls)
- Budget tracking is composable: strategies consume budget, the chain enforces the limit
- The maximum theoretical path is: Process -> ProcessHolder -> Unit -> UnitHolder -> Business -> target holder -> target entity = 7 hops, but with session caching, intermediate entities are cached on first traversal

### 9.3 Depth Limits

| Path | API Calls (Cold) | API Calls (Warm) |
|------|-----------------|-----------------|
| ContactHolder -> Business | 2 | 0 (session cache) |
| Process -> Business | 4-5 | 0-1 (partial cache) |
| Process -> Business -> ContactHolder -> Contact | 6-7 | 2-3 (Business cached) |
| AssetEdit -> Business -> LocationHolder -> Location | 6-8 | 2-3 (Business cached) |

---

## 10. Test Strategy

### 10.1 Unit Tests

| Test Module | Coverage |
|-------------|----------|
| `test_result.py` | ResolutionResult factories, status checks, properties |
| `test_budget.py` | Budget consumption, exhaustion, remaining |
| `test_strategies.py` | Each strategy with mock entities |
| `test_selection.py` | FieldPredicate, CompoundPredicate, NewestActivePredicate |
| `test_context.py` | Session cache, convenience methods, budget passing |
| `test_process_selector.py` | ProcessHolder selection with completion status logic |

### 10.2 Integration Tests

| Test Module | Coverage |
|-------------|----------|
| `test_resolution_chain.py` | Full chain execution with mock API responses |
| `test_conversation_audit_refactored.py` | ConversationAuditWorkflow using resolution |
| `test_branch_hydration.py` | Selective hydration vs full hydration API call count |

### 10.3 Existing Test Compatibility

The resolution system is a new module (`src/autom8_asana/resolution/`). It does not modify any existing entity model files. The only modification to existing code is the ConversationAuditWorkflow refactoring, which preserves the same public API and behavior.

---

## 11. Rollback Strategy

Resolution primitives are entirely additive. If issues are discovered:

1. **ConversationAuditWorkflow**: Revert `_resolve_office_phone` to the original implementation (the only modified file)
2. **Resolution module**: Delete `src/autom8_asana/resolution/` entirely
3. **Tests**: Delete `tests/unit/resolution/` and `tests/integration/resolution/`

No other code depends on the resolution module until it is explicitly adopted by other workflows.
