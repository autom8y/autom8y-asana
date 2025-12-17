# TDD: Navigation Pattern Consolidation (Initiative C)

## Metadata
- **TDD ID**: TDD-HARDENING-C
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-16
- **Last Updated**: 2025-12-16
- **PRD Reference**: [PRD-HARDENING-C](/docs/requirements/PRD-HARDENING-C.md)
- **Discovery Reference**: [DISCOVERY-HARDENING-C](/docs/initiatives/DISCOVERY-HARDENING-C.md)
- **Related TDDs**: TDD-BIZMODEL (business entity foundation)
- **Related ADRs**: ADR-0050 (holder lazy loading), ADR-0052 (bidirectional caching), ADR-0075 (navigation descriptors), ADR-0076 (auto-invalidation)

---

## Overview

This design consolidates ~800 lines of duplicated navigation code across 10 business entities into a descriptor-based pattern. Two generic descriptors (`ParentRef[T]` and `HolderRef[T]`) replace copy-paste property implementations, while an enhanced `HolderMixin` provides a single `_populate_children()` implementation. Auto-invalidation on parent reference changes eliminates manual `_invalidate_refs()` calls.

---

## Requirements Summary

From PRD-HARDENING-C:

| Category | Key Requirements |
|----------|------------------|
| **Descriptors** | FR-DESC-001 through FR-DESC-006: Type-safe descriptors with lazy resolution |
| **Holder Consolidation** | FR-HOLD-001 through FR-HOLD-007: Single `_populate_children()` in HolderMixin |
| **Invalidation** | FR-INV-001 through FR-INV-006: Auto-discovery and auto-invalidation |
| **Naming** | FR-NAME-001 through FR-NAME-004: Singular naming standardization |
| **Compatibility** | FR-COMPAT-001 through FR-COMPAT-005: Backward compatibility preservation |

**Success Metrics**: ~500 lines removed (60%), 9 `_populate_children()` to 1, mypy clean, 100% test pass.

---

## System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                        Business Layer                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐     ┌──────────────────────────────────┐ │
│  │   descriptors.py │     │          HolderMixin             │ │
│  │                  │     │                                  │ │
│  │  ParentRef[T]    │────►│  _populate_children()           │ │
│  │  HolderRef[T]    │     │  _set_child_parent_ref()        │ │
│  │                  │     │  ClassVar configuration         │ │
│  └──────────────────┘     └──────────────────────────────────┘ │
│           │                            │                        │
│           │                            │                        │
│           ▼                            ▼                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   BusinessEntity                          │  │
│  │                                                           │  │
│  │  _CACHED_REF_ATTRS: ClassVar[tuple[str, ...]]            │  │
│  │  _invalidate_refs() - auto-discovery based               │  │
│  │  __init_subclass__() - discovers PrivateAttr refs        │  │
│  └──────────────────────────────────────────────────────────┘  │
│           │                                                     │
│           │ inherits                                            │
│           ▼                                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Concrete Entities                            │  │
│  │                                                           │  │
│  │  Contact, Unit, Offer, Process, Location, Hours,         │  │
│  │  DNA, Reconciliation, AssetEdit, Videography             │  │
│  │                                                           │  │
│  │  Using descriptors:                                       │  │
│  │    business = ParentRef[Business](holder_attr="...")     │  │
│  │    contact_holder = HolderRef[ContactHolder]()           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ inherits from
                              ▼
                    ┌──────────────────┐
                    │      Task        │
                    │  (SDK Layer)     │
                    └──────────────────┘
```

**Key Interactions**:
- Descriptors work with Pydantic `PrivateAttr` for cached reference storage
- `HolderMixin` provides population logic, used by all 9 holder classes
- `BusinessEntity.__init_subclass__` auto-discovers `_CACHED_REF_ATTRS`
- Auto-invalidation triggers in descriptor `__set__` method

---

## Design

### Component Architecture

```
models/business/
├── descriptors.py          # NEW: ParentRef[T], HolderRef[T] descriptors
├── base.py                 # MODIFIED: Enhanced HolderMixin, BusinessEntity
├── contact.py              # MODIFIED: Use descriptors
├── unit.py                 # MODIFIED: Use descriptors
├── offer.py                # MODIFIED: Use descriptors
├── process.py              # MODIFIED: Use descriptors
├── location.py             # MODIFIED: Use descriptors (special override)
├── hours.py                # MODIFIED: Use descriptors
├── business.py             # MODIFIED: Use descriptors, rename reconciliations_holder
└── [dna.py, etc.]          # MODIFIED: Use descriptors
```

| Component | Responsibility | Owner |
|-----------|---------------|-------|
| `descriptors.py` | Generic descriptor implementations with type safety | New file |
| `HolderMixin` | Consolidated `_populate_children()` logic | Enhanced base.py |
| `BusinessEntity` | Auto-discovery of refs, base `_invalidate_refs()` | Enhanced base.py |
| Entity classes | Declare descriptors, minimal configuration | All business entities |

### Data Model

#### Descriptor Types

```python
# descriptors.py

from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload
from pydantic import PrivateAttr

if TYPE_CHECKING:
    from autom8_asana.models.business.base import BusinessEntity

T = TypeVar("T")


class ParentRef(Generic[T]):
    """Descriptor for cached upward navigation with lazy resolution.

    Per ADR-0075: Single descriptor type handles all navigation patterns.

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

            # Descriptor declaration
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
        """Called when descriptor is assigned to class attribute.

        Per ADR-0075: Automatically derives private attribute name from public.
        """
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
        """Get cached value or lazy-resolve via holder.

        Per FR-DESC-002: Lazy resolution via holder_attr if cache is None.
        Per FR-DESC-005: Returns None (not AttributeError) when uninitialized.
        """
        if obj is None:
            # Class-level access returns descriptor itself
            return self

        # Check cached value in PrivateAttr
        cached = getattr(obj, self.private_name, None)
        if cached is not None:
            return cached

        # Lazy resolution via holder if configured
        if self.holder_attr:
            holder = getattr(obj, self.holder_attr, None)
            if holder is not None:
                resolved = getattr(holder, self.target_attr, None)
                if resolved is not None:
                    # Cache the resolved value
                    setattr(obj, self.private_name, resolved)
                    return resolved

        return None

    def __set__(self, obj: Any, value: T | None) -> None:
        """Set cached value and optionally trigger invalidation.

        Per ADR-0076: Auto-invalidation on parent reference change.
        Per FR-INV-003: Setting triggers _invalidate_refs() if configured.
        Per FR-INV-004: Only triggers on write, not read.
        """
        # Store current value to detect actual change
        old_value = getattr(obj, self.private_name, None)

        # Set the new value
        setattr(obj, self.private_name, value)

        # Auto-invalidate on actual change (not just re-assignment of same value)
        if (
            self.auto_invalidate
            and old_value is not value
            and hasattr(obj, "_invalidate_refs")
        ):
            # Don't re-invalidate the attr we just set
            obj._invalidate_refs(_exclude_attr=self.private_name)


class HolderRef(Generic[T]):
    """Descriptor for direct holder property access.

    Per ADR-0075: Simpler descriptor for holder references without lazy resolution.

    Type Parameters:
        T: The holder type (e.g., ContactHolder, UnitHolder)

    Example:
        class Contact(BusinessEntity):
            _contact_holder: ContactHolder | None = PrivateAttr(default=None)

            # Descriptor declaration
            contact_holder: ContactHolder | None = HolderRef[ContactHolder]()
    """

    __slots__ = ("private_name", "public_name")

    def __init__(self) -> None:
        self.private_name: str = ""
        self.public_name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        """Derive private attribute name from public."""
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
        """Get holder reference from PrivateAttr.

        Per FR-DESC-004: Direct holder access without lazy resolution.
        """
        if obj is None:
            return self
        return getattr(obj, self.private_name, None)

    def __set__(self, obj: Any, value: T | None) -> None:
        """Set holder reference.

        Per ADR-0076: Holder changes also trigger invalidation since
        they affect upward navigation.
        """
        old_value = getattr(obj, self.private_name, None)
        setattr(obj, self.private_name, value)

        # Holder change should invalidate other refs
        if old_value is not value and hasattr(obj, "_invalidate_refs"):
            obj._invalidate_refs(_exclude_attr=self.private_name)
```

#### Enhanced HolderMixin

```python
# base.py (enhanced)

from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

from pydantic import PrivateAttr

from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

T = TypeVar("T", bound=Task)


class HolderMixin(Generic[T]):
    """Mixin for holder tasks that contain typed children.

    Per FR-HOLD-001: Single _populate_children() implementation.
    Per FR-HOLD-002 through FR-HOLD-004: ClassVar configuration pattern.

    Configuration ClassVars (must be set by subclass):
        CHILD_TYPE: Type of child entities (e.g., Contact)
        PARENT_REF_NAME: PrivateAttr name on child for holder ref (e.g., "_contact_holder")
        BUSINESS_REF_NAME: PrivateAttr name on child for business ref (default "_business")
        CHILDREN_ATTR: PrivateAttr name for children list (e.g., "_contacts")

    Example:
        class ContactHolder(Task, HolderMixin[Contact]):
            CHILD_TYPE: ClassVar[type[Contact]] = Contact
            PARENT_REF_NAME: ClassVar[str] = "_contact_holder"
            CHILDREN_ATTR: ClassVar[str] = "_contacts"

            _contacts: list[Contact] = PrivateAttr(default_factory=list)
    """

    # Must be overridden by subclass
    CHILD_TYPE: ClassVar[type[Task]]
    PARENT_REF_NAME: ClassVar[str]
    CHILDREN_ATTR: ClassVar[str] = "_children"
    BUSINESS_REF_NAME: ClassVar[str] = "_business"

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate typed children from fetched subtasks.

        Per FR-HOLD-001: Base implementation handles sorting, typing, reference setting.
        Per FR-HOLD-007: Sort by (created_at, name) for stability.

        Subclasses may override for special logic (see LocationHolder for Hours).
        When overriding, call super()._populate_children() for standard children.

        Args:
            subtasks: List of Task subtasks from API.
        """
        # Sort by created_at (oldest first), then by name for stability
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )

        # Get configuration from class
        child_type = getattr(self.__class__, "CHILD_TYPE", Task)
        parent_ref_name = getattr(self.__class__, "PARENT_REF_NAME", "_parent")
        business_ref_name = getattr(self.__class__, "BUSINESS_REF_NAME", "_business")
        children_attr = getattr(self.__class__, "CHILDREN_ATTR", "_children")

        # Build children list
        children: list[T] = []
        for task in sorted_tasks:
            child = child_type.model_validate(task.model_dump())
            # Set parent reference (holder -> child)
            setattr(child, parent_ref_name, self)
            # Propagate business reference
            business_ref = getattr(self, business_ref_name, None)
            setattr(child, business_ref_name, business_ref)
            children.append(cast(T, child))

        # Store in children list
        setattr(self, children_attr, children)

    def _set_child_parent_ref(self, child: T) -> None:
        """Set parent references on a single child.

        Called when adding individual children outside _populate_children.

        Args:
            child: Child entity to set references on.
        """
        parent_ref_name = getattr(self.__class__, "PARENT_REF_NAME", "_parent")
        business_ref_name = getattr(self.__class__, "BUSINESS_REF_NAME", "_business")

        setattr(child, parent_ref_name, self)
        setattr(child, business_ref_name, getattr(self, business_ref_name, None))

    def invalidate_cache(self) -> None:
        """Invalidate children cache.

        Called when hierarchy changes and cache may be stale.
        Subclasses may override to clear additional state.
        """
        children_attr = getattr(self.__class__, "CHILDREN_ATTR", "_children")
        setattr(self, children_attr, [])
```

#### Enhanced BusinessEntity

```python
# base.py (enhanced)

class BusinessEntity(Task):
    """Base class for business model entities.

    Per FR-INV-001: Auto-discovery of cached ref attrs via __init_subclass__.
    Per FR-INV-002: Base _invalidate_refs() clears discovered refs.

    Class Attributes:
        _CACHED_REF_ATTRS: Auto-discovered tuple of PrivateAttr names holding refs.
                          Populated by __init_subclass__.
    """

    # Auto-discovered by __init_subclass__
    _CACHED_REF_ATTRS: ClassVar[tuple[str, ...]] = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-discover cached reference attributes from PrivateAttr annotations.

        Per FR-INV-001: Discovers attrs matching pattern:
        - Starts with underscore
        - Annotation contains optional type (T | None)
        - Not a list type (those are children, not refs)

        IMPORTANT: Works correctly with Pydantic models because Pydantic
        also uses __init_subclass__ and this runs after class creation.
        """
        super().__init_subclass__(**kwargs)

        # Collect PrivateAttrs that look like references
        ref_attrs: list[str] = []

        # Check annotations for this class (not inherited)
        for name, annotation in getattr(cls, "__annotations__", {}).items():
            if not name.startswith("_"):
                continue

            # Convert annotation to string for pattern matching
            ann_str = str(annotation)

            # Skip list types (children storage, not references)
            if "list[" in ann_str.lower():
                continue

            # Look for optional types (T | None pattern)
            if "| None" in ann_str or "Optional" in ann_str:
                ref_attrs.append(name)

        # Combine with parent's refs (for inheritance)
        parent_refs = getattr(cls.__bases__[0], "_CACHED_REF_ATTRS", ())
        cls._CACHED_REF_ATTRS = tuple(set(parent_refs) | set(ref_attrs))

    def _invalidate_refs(self, _exclude_attr: str | None = None) -> None:
        """Invalidate all cached navigation references.

        Per FR-INV-001: Base implementation clears all discovered refs.
        Per FR-INV-002: Subclasses may override for additional logic.

        Args:
            _exclude_attr: Attr to skip (used by descriptors to avoid
                          clearing the attr that triggered invalidation).
        """
        for attr in self._CACHED_REF_ATTRS:
            if attr != _exclude_attr and hasattr(self, attr):
                setattr(self, attr, None)
```

### API Contracts

#### Descriptor Usage Pattern

```python
# Entity migration pattern (Contact example)

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

    # Descriptors provide property behavior
    business: Business | None = ParentRef[Business](holder_attr="_contact_holder")
    contact_holder: ContactHolder | None = HolderRef[ContactHolder]()

    # _invalidate_refs() inherited from BusinessEntity (auto-discovery)
```

#### Holder Migration Pattern

```python
# BEFORE: ~20 lines per holder
class ContactHolder(Task, HolderMixin[Contact]):
    CHILD_TYPE: ClassVar[type[Contact]] = Contact
    _contacts: list[Contact] = PrivateAttr(default_factory=list)
    _business: Business | None = PrivateAttr(default=None)

    def _populate_children(self, subtasks: list[Task]) -> None:
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )
        self._contacts = []
        for task in sorted_tasks:
            contact = Contact.model_validate(task.model_dump())
            contact._contact_holder = self
            contact._business = self._business
            self._contacts.append(contact)


# AFTER: ~5 lines per holder
class ContactHolder(Task, HolderMixin[Contact]):
    CHILD_TYPE: ClassVar[type[Contact]] = Contact
    PARENT_REF_NAME: ClassVar[str] = "_contact_holder"
    CHILDREN_ATTR: ClassVar[str] = "_contacts"

    _contacts: list[Contact] = PrivateAttr(default_factory=list)
    _business: Business | None = PrivateAttr(default=None)

    # _populate_children() inherited from HolderMixin
```

#### LocationHolder Override Pattern

```python
class LocationHolder(Task, HolderMixin[Location]):
    """Special holder that contains both Location children and Hours sibling.

    Per FR-HOLD-006: Override _populate_children for Hours detection.
    """

    CHILD_TYPE: ClassVar[type[Location]] = Location
    PARENT_REF_NAME: ClassVar[str] = "_location_holder"
    CHILDREN_ATTR: ClassVar[str] = "_locations"

    _locations: list[Location] = PrivateAttr(default_factory=list)
    _hours: Hours | None = PrivateAttr(default=None)
    _business: Business | None = PrivateAttr(default=None)

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Override to separate Hours from Location children.

        Per FR-HOLD-006: Override for Hours sibling handling.

        Strategy:
        1. Identify Hours task by name pattern
        2. Process Hours separately with its own references
        3. Delegate remaining tasks to super() for Location processing
        """
        from autom8_asana.models.business.hours import Hours

        location_tasks: list[Task] = []

        for task in subtasks:
            task_name = task.name or ""
            if task_name.lower().startswith("hours"):
                # Process Hours separately
                hours = Hours.model_validate(task.model_dump())
                hours._location_holder = self
                hours._business = self._business
                self._hours = hours
            else:
                # Collect for standard processing
                location_tasks.append(task)

        # Delegate Location processing to base implementation
        super()._populate_children(location_tasks)

    def invalidate_cache(self) -> None:
        """Override to also clear Hours reference."""
        super().invalidate_cache()
        self._hours = None
```

### Data Flow

#### Navigation Property Access

```
User Code                Descriptor                 Entity
    │                        │                         │
    │  contact.business      │                         │
    │───────────────────────►│                         │
    │                        │  __get__(contact, ...)  │
    │                        │─────────────────────────►
    │                        │                         │
    │                        │  Check: contact._business
    │                        │  ◄─────────────────────│
    │                        │                         │
    │                        │  If None and holder_attr:
    │                        │    Get: contact._contact_holder
    │                        │    ◄───────────────────│
    │                        │                         │
    │                        │    If holder:
    │                        │      Get: holder._business
    │                        │      ◄─────────────────│
    │                        │                         │
    │                        │      Set: contact._business = resolved
    │                        │      ─────────────────►│
    │                        │                         │
    │  ◄──────Business──────│                         │
    │                        │                         │
```

#### Auto-Invalidation on Parent Change

```
User Code                Descriptor                 Entity
    │                        │                         │
    │  contact._contact_holder = new_holder            │
    │───────────────────────►│                         │
    │                        │  __set__(contact, new_holder)
    │                        │─────────────────────────►
    │                        │                         │
    │                        │  Store: contact._contact_holder = new_holder
    │                        │  ─────────────────────►│
    │                        │                         │
    │                        │  If auto_invalidate and changed:
    │                        │    Call: contact._invalidate_refs(
    │                        │           _exclude_attr="_contact_holder")
    │                        │  ─────────────────────►│
    │                        │                         │
    │                        │         For each attr in _CACHED_REF_ATTRS:
    │                        │           if attr != "_contact_holder":
    │                        │             contact.{attr} = None
    │                        │                         │
    │                        │         Result: contact._business = None
    │                        │                         │
```

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Descriptor pattern | Single `ParentRef[T]` with config | Fewer classes, full flexibility | ADR-0075 |
| Type safety approach | Generic descriptors + `@overload` | IDE support without runtime cost | ADR-0075 |
| Auto-invalidation trigger | Descriptor `__set__` | Centralized, automatic | ADR-0076 |
| Invalidation scope | Only parent/holder refs | Safe default, configurable | ADR-0076 |
| Ref discovery | `__init_subclass__` | Automatic, no manual registration | ADR-0076 |
| LocationHolder | Override `_populate_children` | Hours detection is location-specific | - |
| Naming fix | Singular with deprecation alias | Backward compatible transition | - |

---

## Complexity Assessment

**Level**: Module

**Justification**:
- Clear API surface (2 descriptor classes, enhanced mixin)
- Minimal external dependencies (Pydantic only)
- No network calls, no async requirements
- Changes are internal refactoring with stable external API
- Complexity is in type inference, which is compile-time not runtime

**Escalation Triggers (not present)**:
- No multiple consumers requiring different behavior
- No external API contract changes
- No independent deployment requirements

---

## Implementation Plan

### Phase 1: Descriptor Infrastructure (Non-Breaking)

**Deliverable**: New `descriptors.py` with `ParentRef[T]` and `HolderRef[T]`

**Tasks**:
1. Create `/src/autom8_asana/models/business/descriptors.py`
2. Implement `ParentRef[T]` with lazy resolution
3. Implement `HolderRef[T]` for direct access
4. Add comprehensive unit tests for descriptor behavior
5. Verify mypy passes with `--strict`

**Dependencies**: None
**Estimate**: 2 hours

### Phase 2: HolderMixin Enhancement (Non-Breaking)

**Deliverable**: Enhanced `HolderMixin` with ClassVar configuration

**Tasks**:
1. Add ClassVar configuration to `HolderMixin`
2. Implement generic `_populate_children()` using configuration
3. Update `_set_child_parent_ref()` to use configuration
4. Add tests for configurable population

**Dependencies**: Phase 1
**Estimate**: 1 hour

### Phase 3: BusinessEntity Enhancement (Non-Breaking)

**Deliverable**: Auto-discovery `_invalidate_refs()` in `BusinessEntity`

**Tasks**:
1. Add `__init_subclass__` for ref attr discovery
2. Implement generic `_invalidate_refs()` with `_exclude_attr`
3. Add `_CACHED_REF_ATTRS` ClassVar
4. Test discovery across inheritance hierarchy

**Dependencies**: Phase 1
**Estimate**: 1 hour

### Phase 4: Entity Migration (Non-Breaking)

**Deliverable**: All 10 entities using descriptors

**Migration Order** (one at a time, test after each):
1. `Contact` - Simplest case, validates pattern
2. `Unit` - Tests nested holders
3. `Offer` - Tests intermediate refs (`_unit`)
4. `Process` - Similar to Offer
5. `Location` - Simple pattern
6. `Hours` - No holder, simple navigation
7. `DNA` - Direct Business child
8. `AssetEdit` - Direct Business child
9. `Videography` - Direct Business child
10. `Reconciliation` - Includes naming fix

**Dependencies**: Phases 1-3
**Estimate**: 3 hours

### Phase 5: Holder Migration (Non-Breaking)

**Deliverable**: All 9 holders using base `_populate_children()`

**Migration Order**:
1. `ContactHolder` - Simplest case
2. `UnitHolder` - Standard pattern
3. `OfferHolder` - Standard pattern
4. `ProcessHolder` - Standard pattern
5. `DNAHolder` - Standard pattern
6. `ReconciliationsHolder` - Rename to singular
7. `AssetEditHolder` - Standard pattern
8. `VideographyHolder` - Standard pattern
9. `LocationHolder` - Override for Hours (last due to complexity)

**Dependencies**: Phase 4
**Estimate**: 2 hours

### Phase 6: Naming Standardization (Breaking with Deprecation)

**Deliverable**: Singular naming for `reconciliation_holder`

**Tasks**:
1. Rename `_reconciliations_holder` to `_reconciliation_holder`
2. Update `HOLDER_KEY_MAP` key
3. Add deprecated property alias `reconciliations_holder`
4. Update all tests

**Dependencies**: Phase 5
**Estimate**: 1 hour

### Migration Strategy

```
Current State                     Target State
─────────────                     ────────────
10 @property methods              2 descriptors
9 _populate_children() copies     1 base implementation
10 _invalidate_refs() copies      1 auto-discovery base
~800 lines duplicated             ~200 lines total
```

**Rollback Plan**: Each phase is independent and non-breaking. Revert single phase if issues arise.

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Type hint regression breaks IDE | Medium | Low | Comprehensive mypy testing; `@overload` coverage |
| Auto-invalidation performance | Low | Low | Only triggers on write; configurable per descriptor |
| `__init_subclass__` with Pydantic | High | Medium | Tested in Phase 3; fallback to manual registration |
| Circular imports in descriptors | Medium | Low | TYPE_CHECKING imports; runtime imports in methods |
| LocationHolder override breaks | Medium | Low | Explicit test coverage; `super()` call pattern |
| Migration introduces subtle bugs | High | Medium | One entity at a time; full test pass required |

---

## Observability

### Metrics
- Not applicable (internal refactoring, no runtime metrics)

### Logging
- Descriptor `__set__` logs at DEBUG level when auto-invalidation triggers
- Format: `"Auto-invalidating refs for {entity_type} after {attr} change"`

### Alerting
- Not applicable (no production behavior change)

---

## Testing Strategy

### Unit Tests

| Test Category | Coverage |
|---------------|----------|
| `ParentRef.__get__` | Returns cached; lazy resolves; handles None |
| `ParentRef.__set__` | Stores value; triggers invalidation; skips on same value |
| `HolderRef.__get__` | Returns cached; handles None |
| `HolderRef.__set__` | Stores value; triggers invalidation |
| `HolderMixin._populate_children` | Sorts correctly; types correctly; sets refs |
| `BusinessEntity._invalidate_refs` | Clears all refs; respects _exclude_attr |
| `BusinessEntity.__init_subclass__` | Discovers refs; inherits parent refs |

### Integration Tests

| Test Category | Coverage |
|---------------|----------|
| Contact navigation | `contact.business`, `contact.contact_holder` |
| Unit navigation | `unit.business`, `unit.offers`, `unit.processes` |
| Offer navigation | `offer.business`, `offer.unit`, `offer.offer_holder` |
| Auto-invalidation | Setting holder clears business ref |
| LocationHolder Hours | Both Location and Hours populated correctly |
| Full hierarchy hydration | Business -> Units -> Offers all linked |

### Regression Tests

| Test Category | Coverage |
|---------------|----------|
| Existing business entity tests | All pass unchanged |
| Existing holder tests | All pass unchanged |
| SaveSession integration | track/commit unchanged |
| Hydration flows | Full hierarchy hydration works |

### Type Safety Tests

| Test Category | Coverage |
|---------------|----------|
| mypy `--strict` | All files pass |
| IDE autocomplete | Manual verification of type hints |
| Generic inference | Tests verify `ParentRef[Business]` yields `Business | None` |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Does `__init_subclass__` ordering with Pydantic cause issues? | Engineer | Phase 3 | Test in implementation; Pydantic uses same pattern |
| Should descriptors support `__delete__`? | Architect | Phase 1 | No - deletion not a use case |
| Should we add runtime type checking in descriptors? | Architect | Phase 1 | No - adds overhead without benefit |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Architect | Initial draft |

---

## Appendix A: Pydantic PrivateAttr Interaction

**Question**: How do descriptors interact with Pydantic's `PrivateAttr`?

**Answer**: Descriptors and `PrivateAttr` work together without conflict:

1. `PrivateAttr` defines the storage slot on the model instance
2. Descriptors define the access pattern (get/set behavior)
3. Both can coexist because:
   - `PrivateAttr` creates `_business` attribute on instance
   - `ParentRef` descriptor defines `business` access pattern
   - Descriptor's `__get__/__set__` access `_business` via `getattr/setattr`

```python
class Contact(BusinessEntity):
    # PrivateAttr creates storage slot
    _business: Business | None = PrivateAttr(default=None)

    # Descriptor defines access pattern, uses storage slot
    business: Business | None = ParentRef[Business](holder_attr="_contact_holder")
```

**Verification**: This pattern is used by Pydantic's own `computed_field` which operates similarly.

---

## Appendix B: Import Order for Circular Dependencies

```python
# descriptors.py - TYPE_CHECKING avoids circular imports

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

if TYPE_CHECKING:
    # These are only imported for type hints, not at runtime
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.contact import Contact, ContactHolder

T = TypeVar("T")

class ParentRef(Generic[T]):
    # Generic[T] provides type parameter
    # Actual type checking happens via annotations, not runtime imports
    ...
```

**Import order** (no circular deps):
1. `descriptors.py` - no business imports at runtime
2. `base.py` - imports descriptors
3. `contact.py` - imports base, descriptors
4. `business.py` - imports all entities

---

## Appendix C: Entity Reference Mapping

| Entity | _CACHED_REF_ATTRS (auto-discovered) |
|--------|-------------------------------------|
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

## Quality Gate Checklist

- [x] Traces to approved PRD (PRD-HARDENING-C)
- [x] All significant decisions have ADRs (ADR-0075, ADR-0076)
- [x] Component responsibilities are clear (descriptors, mixin, base)
- [x] Interfaces are defined (descriptor protocols, mixin ClassVars)
- [x] Complexity level is justified (Module - internal refactoring)
- [x] Risks identified with mitigations (6 risks documented)
- [x] Implementation plan is actionable (6 phases with estimates)
