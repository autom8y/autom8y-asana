# TDD-07: Navigation & Hydration Architecture

> Consolidated TDD for entity relationships, lazy loading, and navigation descriptors.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: TDD-0017 (Hierarchy Hydration), TDD-0021 (Navigation Descriptors), TDD-0024 (Holder Factory)
- **Related ADRs**: ADR-0053 (Descriptor Patterns)

---

## Overview

This document specifies the navigation and hydration architecture for the business model layer. The design addresses three interconnected concerns:

1. **Navigation Descriptors**: Type-safe, lazy-resolving property access for entity relationships
2. **Hierarchy Hydration**: Loading complete business hierarchies from any entry point
3. **Holder Factory**: Declarative holder definitions using `__init_subclass__`

The architecture eliminates approximately 1,100 lines of duplicated code while providing:
- Full hierarchy traversal (upward and downward)
- Lazy resolution of parent references
- Concurrent API fetching during hydration
- Partial failure handling with detailed results

---

## Navigation Descriptors

### Purpose

Replace ~800 lines of copy-paste property implementations across 10 business entities with two generic descriptors: `ParentRef[T]` and `HolderRef[T]`.

### Descriptor Types

```python
# descriptors.py
from typing import Generic, TypeVar, Any, overload
from pydantic import PrivateAttr

T = TypeVar("T")


class ParentRef(Generic[T]):
    """Descriptor for cached upward navigation with lazy resolution.

    Type Parameters:
        T: The type being navigated to (e.g., Business, ContactHolder)

    Args:
        holder_attr: PrivateAttr name to resolve from (e.g., "_contact_holder")
        target_attr: Attribute on holder to resolve to (default "_business")
        auto_invalidate: If True, setting triggers _invalidate_refs()

    Example:
        class Contact(BusinessEntity):
            _business: Business | None = PrivateAttr(default=None)
            _contact_holder: ContactHolder | None = PrivateAttr(default=None)

            business: Business | None = ParentRef[Business](
                holder_attr="_contact_holder"
            )
    """

    __slots__ = (
        "holder_attr",
        "target_attr",
        "auto_invalidate",
        "private_name",
        "public_name",
    )

    def __init__(
        self,
        holder_attr: str | None = None,
        target_attr: str = "_business",
        auto_invalidate: bool = True,
    ) -> None:
        self.holder_attr = holder_attr
        self.target_attr = target_attr
        self.auto_invalidate = auto_invalidate
        self.private_name: str = ""
        self.public_name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.public_name = name
        self.private_name = f"_{name}"

    @overload
    def __get__(self, obj: None, objtype: type) -> "ParentRef[T]": ...

    @overload
    def __get__(self, obj: Any, objtype: type | None) -> T | None: ...

    def __get__(
        self,
        obj: Any,
        objtype: type | None = None,
    ) -> T | None | "ParentRef[T]":
        if obj is None:
            return self  # Class access returns descriptor

        # Check cached value
        cached = getattr(obj, self.private_name, None)
        if cached is not None:
            return cached

        # Lazy resolution via holder chain
        if self.holder_attr:
            holder = getattr(obj, self.holder_attr, None)
            if holder is not None:
                resolved = getattr(holder, self.target_attr, None)
                if resolved is not None:
                    setattr(obj, self.private_name, resolved)
                    return resolved

        return None

    def __set__(self, obj: Any, value: T | None) -> None:
        old_value = getattr(obj, self.private_name, None)
        setattr(obj, self.private_name, value)

        # Auto-invalidate on actual change
        if (
            self.auto_invalidate
            and old_value is not value
            and hasattr(obj, "_invalidate_refs")
        ):
            obj._invalidate_refs(_exclude_attr=self.private_name)


class HolderRef(Generic[T]):
    """Descriptor for direct holder property access (no lazy resolution)."""

    __slots__ = ("private_name", "public_name")

    def __init__(self) -> None:
        self.private_name: str = ""
        self.public_name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.public_name = name
        self.private_name = f"_{name}"

    @overload
    def __get__(self, obj: None, objtype: type) -> "HolderRef[T]": ...

    @overload
    def __get__(self, obj: Any, objtype: type | None) -> T | None: ...

    def __get__(
        self,
        obj: Any,
        objtype: type | None = None,
    ) -> T | None | "HolderRef[T]":
        if obj is None:
            return self
        return getattr(obj, self.private_name, None)

    def __set__(self, obj: Any, value: T | None) -> None:
        old_value = getattr(obj, self.private_name, None)
        setattr(obj, self.private_name, value)

        if old_value is not value and hasattr(obj, "_invalidate_refs"):
            obj._invalidate_refs(_exclude_attr=self.private_name)
```

### Usage Pattern

```python
# BEFORE: ~30 lines per entity
class Contact(BusinessEntity):
    _business: Business | None = PrivateAttr(default=None)
    _contact_holder: ContactHolder | None = PrivateAttr(default=None)

    @property
    def business(self) -> Business | None:
        if self._business is None and self._contact_holder is not None:
            self._business = self._contact_holder._business
        return self._business

    @property
    def contact_holder(self) -> ContactHolder | None:
        return self._contact_holder

    def _invalidate_refs(self) -> None:
        self._business = None
        self._contact_holder = None


# AFTER: ~5 lines per entity
class Contact(BusinessEntity):
    _business: Business | None = PrivateAttr(default=None)
    _contact_holder: ContactHolder | None = PrivateAttr(default=None)

    business: Business | None = ParentRef[Business](holder_attr="_contact_holder")
    contact_holder: ContactHolder | None = HolderRef[ContactHolder]()

    # _invalidate_refs() inherited from BusinessEntity (auto-discovery)
```

### Auto-Discovery of Cached References

```python
class BusinessEntity(Task):
    """Base class for business model entities."""

    _CACHED_REF_ATTRS: ClassVar[tuple[str, ...]] = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        # Discover PrivateAttrs that look like references
        ref_attrs: list[str] = []
        for name, annotation in getattr(cls, "__annotations__", {}).items():
            if not name.startswith("_"):
                continue
            ann_str = str(annotation)
            if "list[" in ann_str.lower():
                continue  # Skip children lists
            if "| None" in ann_str or "Optional" in ann_str:
                ref_attrs.append(name)

        # Combine with parent's refs
        parent_refs = getattr(cls.__bases__[0], "_CACHED_REF_ATTRS", ())
        cls._CACHED_REF_ATTRS = tuple(set(parent_refs) | set(ref_attrs))

    def _invalidate_refs(self, _exclude_attr: str | None = None) -> None:
        """Invalidate all cached navigation references."""
        for attr in self._CACHED_REF_ATTRS:
            if attr != _exclude_attr and hasattr(self, attr):
                setattr(self, attr, None)
```

### Entity Reference Mapping

| Entity | Cached Reference Attributes |
|--------|---------------------------|
| Contact | `_business`, `_contact_holder` |
| Unit | `_business`, `_unit_holder`, `_offer_holder`, `_process_holder` |
| Offer | `_business`, `_unit`, `_offer_holder` |
| Process | `_business`, `_unit`, `_process_holder` |
| Location | `_business`, `_location_holder` |
| Hours | `_business`, `_location_holder` |
| DNA | `_business`, `_dna_holder` |
| Reconciliation | `_business`, `_reconciliation_holder` |
| AssetEdit | `_business`, `_asset_edit_holder` |
| Videography | `_business`, `_videography_holder` |

---

## Hierarchy Hydration

### Purpose

Enable loading complete Business hierarchies from any entry point (Business GID, Contact, Offer, etc.) with support for:
- Downward hydration from Business root
- Upward traversal to find Business
- Combined hydration from any entry point
- Partial failure handling

### Data Model

```python
from dataclasses import dataclass, field
from typing import Literal
from enum import Enum


class EntityType(Enum):
    """Types of entities in the business model hierarchy."""
    BUSINESS = "business"
    CONTACT_HOLDER = "contact_holder"
    UNIT_HOLDER = "unit_holder"
    LOCATION_HOLDER = "location_holder"
    DNA_HOLDER = "dna_holder"
    RECONCILIATIONS_HOLDER = "reconciliations_holder"
    ASSET_EDIT_HOLDER = "asset_edit_holder"
    VIDEOGRAPHY_HOLDER = "videography_holder"
    UNIT = "unit"
    OFFER_HOLDER = "offer_holder"
    PROCESS_HOLDER = "process_holder"
    CONTACT = "contact"
    OFFER = "offer"
    PROCESS = "process"
    LOCATION = "location"
    HOURS = "hours"
    UNKNOWN = "unknown"


@dataclass
class HydrationBranch:
    """A successfully hydrated branch."""
    holder_type: str
    holder_gid: str
    child_count: int


@dataclass
class HydrationFailure:
    """A branch that failed to hydrate."""
    holder_type: str
    holder_gid: str | None
    phase: Literal["downward", "upward"]
    error: Exception
    recoverable: bool


@dataclass
class HydrationResult:
    """Complete result of hydration operation."""
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
        """True if hydration completed with no failures."""
        return len(self.failed) == 0
```

### API Contracts

#### Downward Hydration: Business.from_gid_async

```python
class Business(BusinessEntity):
    @classmethod
    async def from_gid_async(
        cls,
        client: AsanaClient,
        gid: str,
        *,
        hydrate: bool = True,
        partial_ok: bool = False,
    ) -> Business | HydrationResult:
        """Load Business from GID with optional hierarchy hydration.

        Args:
            client: AsanaClient for API calls.
            gid: Business task GID.
            hydrate: If True (default), load full hierarchy.
            partial_ok: If True, return HydrationResult even on partial failure.

        Returns:
            Business if partial_ok=False and successful.
            HydrationResult if partial_ok=True.

        Raises:
            HydrationError: If hydration fails and partial_ok=False.
            NotFoundError: If Business GID does not exist.
        """
```

#### Upward Traversal: Entity.to_business_async

```python
class Contact(BusinessEntity):
    async def to_business_async(
        self,
        client: AsanaClient,
        *,
        hydrate_full: bool = True,
        partial_ok: bool = False,
    ) -> Business | HydrationResult:
        """Navigate to containing Business and hydrate.

        Path: Contact -> ContactHolder -> Business

        Args:
            client: AsanaClient for API calls.
            hydrate_full: If True, hydrate full Business hierarchy.
            partial_ok: If True, return HydrationResult on partial failure.

        Returns:
            Business or HydrationResult depending on partial_ok.
        """


class Offer(BusinessEntity):
    async def to_business_async(
        self,
        client: AsanaClient,
        *,
        hydrate_full: bool = True,
        partial_ok: bool = False,
    ) -> Business | HydrationResult:
        """Navigate to containing Business and hydrate.

        Path: Offer -> OfferHolder -> Unit -> UnitHolder -> Business
        """
```

#### Generic Entry: hydrate_from_gid_async

```python
async def hydrate_from_gid_async(
    client: AsanaClient,
    gid: str,
    *,
    hydrate_full: bool = True,
    partial_ok: bool = False,
) -> HydrationResult:
    """Hydrate business hierarchy from any task GID.

    Detects entity type, traverses upward to Business if needed,
    then optionally hydrates full hierarchy downward.

    Args:
        client: AsanaClient for API calls.
        gid: Any task GID in the business hierarchy.
        hydrate_full: If True, hydrate full hierarchy after finding Business.
        partial_ok: If True, continue on partial failures.

    Returns:
        HydrationResult with business and metadata.
    """
```

### Downward Hydration Algorithm

```python
async def _fetch_holders_async(self, client: AsanaClient) -> None:
    """Fetch and populate all holder subtasks with their children.

    Algorithm:
    1. Fetch Business subtasks (holders)
    2. Identify and type each holder
    3. Concurrently fetch each holder's children
    4. For Unit children, recursively fetch nested holders
    5. Set all bidirectional references
    """
    # Step 1: Fetch Business subtasks
    holder_tasks = await client.tasks.subtasks_async(self.gid).collect()

    # Step 2: Populate typed holders
    self._populate_holders(holder_tasks)

    # Step 3: Concurrent child fetching for each populated holder
    fetch_tasks = []

    if self._contact_holder:
        fetch_tasks.append(self._fetch_holder_children(
            client, self._contact_holder, "_contacts"
        ))

    if self._unit_holder:
        fetch_tasks.append(self._fetch_unit_holder_children(client))

    if self._location_holder:
        fetch_tasks.append(self._fetch_holder_children(
            client, self._location_holder, "_children"
        ))

    # Stub holders (DNA, Reconciliations, etc.)
    for holder in [self._dna_holder, self._reconciliations_holder,
                   self._asset_edit_holder, self._videography_holder]:
        if holder:
            fetch_tasks.append(self._fetch_holder_children(
                client, holder, "_children"
            ))

    # Execute all fetches concurrently
    await asyncio.gather(*fetch_tasks)
```

### Type Detection Algorithm

```python
HOLDER_NAME_MAP: dict[str, EntityType] = {
    "contacts": EntityType.CONTACT_HOLDER,
    "units": EntityType.UNIT_HOLDER,
    "offers": EntityType.OFFER_HOLDER,
    "processes": EntityType.PROCESS_HOLDER,
    "location": EntityType.LOCATION_HOLDER,
    "dna": EntityType.DNA_HOLDER,
    "reconciliations": EntityType.RECONCILIATIONS_HOLDER,
    "asset edit": EntityType.ASSET_EDIT_HOLDER,
    "videography": EntityType.VIDEOGRAPHY_HOLDER,
}


def detect_by_name(name: str | None) -> EntityType | None:
    """Detect entity type by name (sync, no API call)."""
    if name is None:
        return None
    name_lower = name.lower().strip()
    if name_lower in HOLDER_NAME_MAP:
        return HOLDER_NAME_MAP[name_lower]
    return None


async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
) -> EntityType:
    """Detect entity type with structure fallback.

    1. Try name-based detection (fast path)
    2. Fall back to structure inspection (fetch subtasks)
    """
    # Fast path: name detection
    if detected := detect_by_name(task.name):
        return detected

    # Slow path: structure inspection
    subtasks = await client.tasks.subtasks_async(task.gid).collect()
    subtask_names = {s.name.lower() for s in subtasks if s.name}

    # Business has holder subtasks
    business_indicators = {"contacts", "units", "location"}
    if subtask_names & business_indicators:
        return EntityType.BUSINESS

    # Unit has offer/process holder subtasks
    unit_indicators = {"offers", "processes"}
    if subtask_names & unit_indicators:
        return EntityType.UNIT

    return EntityType.UNKNOWN
```

### Hierarchy Depth Reference

```
Business (Level 0)
  |
  +-- ContactHolder (Level 1)
  |     +-- Contact (Level 2)
  |
  +-- UnitHolder (Level 1)
  |     +-- Unit (Level 2)
  |           +-- OfferHolder (Level 3)
  |           |     +-- Offer (Level 4)
  |           +-- ProcessHolder (Level 3)
  |                 +-- Process (Level 4)
  |
  +-- LocationHolder (Level 1)
  |     +-- Location (Level 2)
  |     +-- Hours (Level 2)
  |
  +-- DNAHolder (Level 1)
  +-- ReconciliationsHolder (Level 1)
  +-- AssetEditHolder (Level 1)
  +-- VideographyHolder (Level 1)

Maximum downward depth: 4 levels (Business -> UnitHolder -> Unit -> OfferHolder -> Offer)
Maximum upward depth: 4 levels (Offer -> OfferHolder -> Unit -> UnitHolder -> Business)
```

### API Call Analysis

| Operation | Typical Calls | Description |
|-----------|---------------|-------------|
| Downward hydration | ~19 | 1 get + 1 subtasks(business) + 7 holder subtasks + 3 unit subtasks + 6 nested |
| Upward traversal (Offer) | ~6 | 4 parent gets + 2 detection subtasks |
| Combined (Offer entry) | ~25 | Upward traversal + downward hydration |

---

## Holder Factory Pattern

### Purpose

Consolidate ~300 lines of duplicated code across 4 stub holders into a single reusable base class using `__init_subclass__`.

### HolderFactory Base Class

```python
class HolderFactory(Task, HolderMixin[Task]):
    """Base class for holder tasks using __init_subclass__ pattern.

    Usage:
        class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
            '''Holder for DNA children.'''
            pass

    This generates:
    - CHILD_TYPE, PARENT_REF_NAME, CHILDREN_ATTR class vars
    - _children PrivateAttr
    - _business PrivateAttr
    - children property
    - business property
    - Optional semantic alias property
    - _populate_children method
    """

    CHILD_TYPE: ClassVar[type[Task]] = Task
    PARENT_REF_NAME: ClassVar[str] = ""
    CHILDREN_ATTR: ClassVar[str] = "_children"
    _CHILD_MODULE: ClassVar[str] = ""
    _CHILD_CLASS_NAME: ClassVar[str] = ""

    _children: list[Any] = PrivateAttr(default_factory=list)
    _business: Business | None = PrivateAttr(default=None)

    def __init_subclass__(
        cls,
        *,
        child_type: str | None = None,
        parent_ref: str | None = None,
        children_attr: str = "_children",
        semantic_alias: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)

        if child_type is None:
            return

        cls._CHILD_CLASS_NAME = child_type
        cls._CHILD_MODULE = f"autom8_asana.models.business.{child_type.lower()}"
        cls.PARENT_REF_NAME = parent_ref or f"_{child_type.lower()}_holder"
        cls.CHILDREN_ATTR = children_attr

        if semantic_alias and semantic_alias != "children":
            setattr(
                cls,
                semantic_alias,
                property(lambda self: self.children),
            )

    @property
    def children(self) -> list[Any]:
        return getattr(self, self.CHILDREN_ATTR, [])

    @property
    def business(self) -> Business | None:
        return self._business
```

### Migrated Holder Definitions

```python
class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
    """Holder task containing DNA children."""
    pass


class ReconciliationHolder(
    HolderFactory,
    child_type="Reconciliation",
    parent_ref="_reconciliation_holder",
    semantic_alias="reconciliations",
):
    """Holder task containing Reconciliation children."""
    pass


class AssetEditHolder(
    HolderFactory,
    child_type="AssetEdit",
    parent_ref="_asset_edit_holder",
    children_attr="_asset_edits",
    semantic_alias="asset_edits",
):
    """Holder task containing AssetEdit children."""
    pass


class VideographyHolder(
    HolderFactory,
    child_type="Videography",
    parent_ref="_videography_holder",
    semantic_alias="videography",
):
    """Holder task containing Videography children."""
    pass
```

### Code Reduction

| Component | Before | After |
|-----------|--------|-------|
| DNAHolder | 64 lines | 4 lines |
| ReconciliationHolder | 73 lines | 8 lines |
| AssetEditHolder | 70 lines | 9 lines |
| VideographyHolder | 73 lines | 8 lines |
| HolderFactory base | 0 lines | ~90 lines |
| **Total** | 295 lines | 134 lines |

**Net reduction**: ~161 lines (55%)

---

## Lazy Loading Strategy

### Design Principles

1. **Cache on first access**: Store resolved values in PrivateAttr
2. **Invalidate on change**: Auto-clear cached refs when parent changes
3. **Fail gracefully**: Return None when resolution not possible
4. **No implicit API calls**: Lazy resolution uses already-loaded data only

### Data Flow: Navigation Property Access

```
User Code                Descriptor                 Entity
    |                        |                         |
    |  contact.business      |                         |
    |----------------------->|                         |
    |                        |  __get__(contact, ...)  |
    |                        |------------------------>|
    |                        |                         |
    |                        |  Check: contact._business
    |                        |  <----------------------|
    |                        |                         |
    |                        |  If None and holder_attr:
    |                        |    Get: contact._contact_holder
    |                        |    <---------------------|
    |                        |                         |
    |                        |    If holder:
    |                        |      Get: holder._business
    |                        |      <-------------------|
    |                        |                         |
    |                        |      Set: contact._business = resolved
    |                        |      -------------------->|
    |                        |                         |
    |  <-------Business------|                         |
```

### Data Flow: Auto-Invalidation on Parent Change

```
User Code                Descriptor                 Entity
    |                        |                         |
    |  contact._contact_holder = new_holder            |
    |----------------------->|                         |
    |                        |  __set__(contact, new_holder)
    |                        |------------------------>|
    |                        |                         |
    |                        |  Store value
    |                        |  ---------------------->|
    |                        |                         |
    |                        |  If auto_invalidate and changed:
    |                        |    Call: contact._invalidate_refs(
    |                        |           _exclude_attr="_contact_holder")
    |                        |  ---------------------->|
    |                        |                         |
    |                        |         For each attr in _CACHED_REF_ATTRS:
    |                        |           if attr != "_contact_holder":
    |                        |             contact.{attr} = None
    |                        |                         |
    |                        |         Result: contact._business = None
```

---

## Testing Strategy

### Unit Tests

| Component | Test Coverage |
|-----------|--------------|
| `ParentRef.__get__` | Returns cached; lazy resolves; handles None |
| `ParentRef.__set__` | Stores value; triggers invalidation; skips on same value |
| `HolderRef.__get__` | Returns cached; handles None |
| `HolderRef.__set__` | Stores value; triggers invalidation |
| `HolderMixin._populate_children` | Sorts correctly; types correctly; sets refs |
| `BusinessEntity._invalidate_refs` | Clears all refs; respects _exclude_attr |
| `BusinessEntity.__init_subclass__` | Discovers refs; inherits parent refs |
| `HolderFactory.__init_subclass__` | Configures ClassVars correctly |
| Type detection | Name-based; structure fallback; unknown handling |
| Hydration orchestration | Path tracking; API call counting; cycle detection |

### Integration Tests

| Scenario | Verification |
|----------|-------------|
| Contact navigation | `contact.business`, `contact.contact_holder` resolve correctly |
| Unit navigation | `unit.business`, `unit.offers`, `unit.processes` resolve correctly |
| Offer navigation | `offer.business`, `offer.unit`, `offer.offer_holder` resolve correctly |
| Auto-invalidation | Setting holder clears business ref |
| LocationHolder Hours | Both Location and Hours populated correctly |
| Full downward hydration | Business -> Units -> Offers all linked |
| Upward + downward | Start from Contact, verify full hierarchy |
| Partial failure | Mock one holder fetch to fail, verify others succeed |

### Performance Tests

- Benchmark hydration of typical Business (5 Contacts, 3 Units, 10 Offers)
- Target: < 30 API calls
- Target: < 5s total time with mocked latency
- Descriptor access: ~100ns (equivalent to @property)

---

## Cross-References

### Related Documentation

| Document | Relationship |
|----------|-------------|
| ADR-0053 | Descriptor patterns decision and rationale |
| TDD-01 | Foundation architecture (Task base class) |
| TDD-04 | SaveSession unit of work (entity tracking) |
| TDD-05 | Custom field architecture (field descriptors) |

### Component Dependencies

```
descriptors.py
    |
    +-- ParentRef[T], HolderRef[T]
    |
    v
base.py (BusinessEntity, HolderMixin)
    |
    +-- Auto-discovery (__init_subclass__)
    +-- _invalidate_refs()
    +-- _populate_children()
    |
    v
holder_factory.py (HolderFactory)
    |
    +-- Declarative holder definitions
    |
    v
business.py, contact.py, unit.py, etc.
    |
    +-- Entity implementations
    |
    v
hydration.py
    |
    +-- hydrate_from_gid_async()
    +-- HydrationResult
```

### Pydantic Compatibility

```python
class BusinessEntity(Task):
    model_config = ConfigDict(
        ignored_types=(
            ParentRef, HolderRef,
        ),
        extra="allow",
    )
```

The `ignored_types` configuration tells Pydantic to skip descriptor instances during model validation. Descriptors operate alongside Pydantic PrivateAttr without conflict.

---

## Quality Gate Checklist

- [x] Traces to source TDDs (TDD-0017, TDD-0021, TDD-0024)
- [x] Related ADRs documented (ADR-0053)
- [x] Component responsibilities are clear
- [x] Interfaces are defined (descriptor protocols, mixin ClassVars, hydration API)
- [x] Complexity level is Module (internal refactoring)
- [x] Testing strategy covers unit, integration, and performance
- [x] Cross-references to related documentation
