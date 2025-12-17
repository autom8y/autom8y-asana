# PRD: Navigation Pattern Consolidation (Initiative C)

## Metadata
- **PRD ID**: PRD-HARDENING-C
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-16
- **Last Updated**: 2025-12-16
- **Stakeholders**: SDK Maintainers, Business Layer Consumers
- **Related PRDs**: PRD-HARDENING-A (Foundation, prerequisite), PRD-HARDENING-B (Custom Fields, prerequisite)
- **Discovery Document**: [DISCOVERY-HARDENING-C.md](/docs/initiatives/DISCOVERY-HARDENING-C.md)
- **Issues Addressed**: #4 (Manual reference invalidation), #6 (Copy-paste navigation), #7 (Inconsistent holder initialization)

---

## Problem Statement

### What Problem Are We Solving?

The SDK's business layer contains **~800+ lines of duplicated navigation code** across 10 business entities. Each entity independently implements nearly identical patterns for:

| Pattern | Occurrences | Lines Each | Total Duplicated |
|---------|-------------|------------|------------------|
| Navigation property (`business`) | 6 | 12 | ~72 |
| Navigation property (`holder`) | 10 | 8 | ~80 |
| `_invalidate_refs()` | 10 | 8 | ~80 |
| `_populate_children()` | 9 | 20 | ~180 |
| `_set_child_parent_ref()` | 9 | 6 | ~54 |
| Holder property accessor | 9 | 6 | ~54 |
| Custom field getter helpers | 10 | 15 | ~150 |
| Convenience shortcuts | 7 | 8 | ~56 |

### For Whom?

- **SDK Maintainers**: Developers who must update navigation logic across 10+ files when patterns change
- **Code Reviewers**: Anyone verifying that copy-pasted implementations remain synchronized
- **Business Layer Consumers**: Indirect impact via potential inconsistencies in navigation behavior

### What Is the Impact of Not Solving It?

**Maintenance Burden (Severity: High)**:
1. **Bug propagation risk**: Fix in one entity must be replicated to 9 others manually
2. **Inconsistency creep**: Subtle variations accumulate across entities (e.g., `_reconciliations_holder` plural naming)
3. **Code review fatigue**: Reviewers must verify 10 implementations remain synchronized
4. **Onboarding friction**: New contributors must understand pattern before touching any entity

**Stale Reference Risk (Severity: Medium)**:
1. `_invalidate_refs()` exists on all entities but is **never called automatically**
2. Manual invalidation is error-prone and easily forgotten
3. Hierarchy mutations can leave cached references pointing to stale objects

**From Discovery** (Section 4.2):
> **Critical Gap**: `_invalidate_refs()` is defined but rarely called automatically.
> - Call Sites Found: None in SaveSession, None in hydration code
> - Manual call required on parent changes

---

## Goals & Success Metrics

### Goals

| Goal | Measure |
|------|---------|
| **G1: Eliminate Navigation Code Duplication** | Single descriptor-based implementation replaces 6 navigation property implementations |
| **G2: Unify Holder Population Logic** | Single `HolderMixin._populate_children()` replaces 9 implementations |
| **G3: Enable Automatic Reference Invalidation** | `_invalidate_refs()` called automatically on hierarchy-changing operations |
| **G4: Fix Naming Inconsistencies** | All holder references use singular naming convention |
| **G5: Preserve Type Safety** | IDE autocomplete and type hints continue to work |

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Lines of navigation code | Reduce by ~500 (60%) | LOC count before/after |
| `_populate_children()` implementations | Reduce from 9 to 1 | grep count |
| `_invalidate_refs()` implementations | Reduce from 10 to 1 (base) | grep count |
| Auto-invalidation coverage | 100% of parent changes | Test coverage |
| Type hint accuracy | 100% mypy clean | `mypy src/autom8_asana --strict` |
| Existing test pass rate | 100% | pytest suite |

---

## Scope

### In Scope

- **R1**: Create `ParentRef` descriptor for upward navigation properties
- **R2**: Create `HolderRef` descriptor for holder property access
- **R3**: Consolidate `_populate_children()` into `HolderMixin` base class
- **R4**: Consolidate `_invalidate_refs()` logic with auto-discovery
- **R5**: Add automatic invalidation on parent reference changes
- **R6**: Rename `_reconciliations_holder` to `_reconciliation_holder` (singular)
- **R7**: Update `HOLDER_KEY_MAP` to use singular key name
- **R8**: Migrate all 10 business entities to use descriptors
- **R9**: Migrate all 9 holders to use consolidated `_populate_children()`

### Out of Scope

- **OS-1**: SDK core entities (Task, Project, etc.) - they use `NameGid` static references, no navigation patterns
- **OS-2**: `__getattr__` magic for holder access - explicit properties are intentional for type safety (per Discovery Section 3.3)
- **OS-3**: Emoji-based holder detection - fallback not implemented, name matching sufficient
- **OS-4**: Performance optimization of navigation (addressed if needed in future initiative)
- **OS-5**: Changes to `HOLDER_KEY_MAP` structure - only key renaming
- **OS-6**: Circular import restructuring - runtime imports remain acceptable

---

## Requirements

### Functional Requirements: Descriptors (FR-DESC)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-DESC-001** | `ParentRef` descriptor MUST provide cached upward navigation | Must | `contact.business` returns cached `Business` instance via descriptor |
| **FR-DESC-002** | `ParentRef` descriptor MUST support lazy resolution via holder | Must | If `_business` is `None`, resolves via `_contact_holder._business` |
| **FR-DESC-003** | `ParentRef` descriptor MUST be type-safe with Generic[T] | Must | `mypy` reports no errors; IDE shows correct type hints |
| **FR-DESC-004** | `HolderRef` descriptor MUST provide direct holder access | Must | `business.contact_holder` returns `ContactHolder` via descriptor |
| **FR-DESC-005** | Descriptors MUST support `None` return for uninitialized references | Must | `contact.business` returns `None` when not populated (not AttributeError) |
| **FR-DESC-006** | Descriptors MUST preserve docstrings for IDE documentation | Should | Descriptor `__doc__` populated; shows in IDE hover |

### Functional Requirements: Holder Consolidation (FR-HOLD)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-HOLD-001** | `HolderMixin._populate_children()` MUST be implemented in base class | Must | Base method handles sorting, typing, reference setting |
| **FR-HOLD-002** | `HolderMixin` MUST use `CHILD_TYPE` ClassVar for child type resolution | Must | `ContactHolder.CHILD_TYPE == Contact` |
| **FR-HOLD-003** | `HolderMixin` MUST use `PARENT_REF_NAME` ClassVar for holder reference | Must | `ContactHolder.PARENT_REF_NAME == "_contact_holder"` |
| **FR-HOLD-004** | `HolderMixin` MUST use `BUSINESS_REF_NAME` ClassVar for business reference | Must | Defaults to `"_business"` |
| **FR-HOLD-005** | All 9 holder classes MUST inherit consolidated `_populate_children()` | Must | No entity-specific implementations remain |
| **FR-HOLD-006** | `LocationHolder._populate_children()` MAY override for Hours sibling handling | Should | Override documents reason; calls `super()` for Location children |
| **FR-HOLD-007** | Child sorting MUST remain stable (created_at, then name) | Must | `sorted(subtasks, key=lambda t: (t.created_at or "", t.name or ""))` |

### Functional Requirements: Invalidation (FR-INV)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-INV-001** | `BusinessEntity._invalidate_refs()` MUST auto-discover cached refs | Must | Base implementation clears all `PrivateAttr` starting with `_` that hold refs |
| **FR-INV-002** | Entity-specific `_invalidate_refs()` MAY call `super()` plus additional logic | Should | `Unit._invalidate_refs()` can clear nested holders after `super()` call |
| **FR-INV-003** | Auto-invalidation MUST trigger when parent reference changes | Must | Setting `contact._contact_holder = new_holder` triggers `_invalidate_refs()` |
| **FR-INV-004** | Auto-invalidation MUST NOT trigger on read access | Must | `_ = contact.business` does not call `_invalidate_refs()` |
| **FR-INV-005** | Auto-invalidation MUST be configurable per descriptor | Should | `ParentRef(auto_invalidate=False)` disables auto-invalidation |
| **FR-INV-006** | `invalidate_cache()` on holders MUST remain unchanged | Must | Clears children list, not parent refs |

### Functional Requirements: Naming (FR-NAME)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-NAME-001** | `_reconciliations_holder` MUST be renamed to `_reconciliation_holder` | Must | All occurrences updated: model, HOLDER_KEY_MAP key, tests |
| **FR-NAME-002** | `Business.HOLDER_KEY_MAP["reconciliations_holder"]` MUST become `"reconciliation_holder"` | Must | Key changed; value tuple unchanged |
| **FR-NAME-003** | Property `reconciliations_holder` MUST be renamed to `reconciliation_holder` | Must | Breaking change documented in migration guide |
| **FR-NAME-004** | Deprecation alias for `reconciliations_holder` SHOULD be provided | Should | Old property warns and delegates to new property |

### Functional Requirements: Backward Compatibility (FR-COMPAT)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-COMPAT-001** | All existing navigation properties MUST continue to work | Must | `contact.business`, `unit.offers`, etc. unchanged behavior |
| **FR-COMPAT-002** | All existing holder properties MUST continue to work | Must | `business.contact_holder`, `unit.offer_holder`, etc. unchanged |
| **FR-COMPAT-003** | `_populate_children()` signature MUST remain `(self, subtasks: list[Task]) -> None` | Must | No API change for callers |
| **FR-COMPAT-004** | `_invalidate_refs()` signature MUST remain `(self) -> None` | Must | No API change for callers |
| **FR-COMPAT-005** | `HOLDER_KEY_MAP` type signature MUST remain `dict[str, tuple[str, str]]` | Must | No structural change |

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| **NFR-001** | Navigation property access latency | < 100ns | Benchmark test |
| **NFR-002** | No memory overhead from descriptors | < 1% increase | Memory profiler |
| **NFR-003** | Type safety maintained | mypy clean | `mypy src/autom8_asana --strict` |
| **NFR-004** | Code reduction | >= 500 lines removed | LOC diff |
| **NFR-005** | Test coverage maintained | >= 90% | pytest --cov |

---

## User Stories / Use Cases

### UC-1: Navigation Property Usage (Unchanged Behavior)

```python
# Current usage continues to work identically
business = await Business.from_gid_async(client, "123")

for contact in business.contacts:
    # Upward navigation works via descriptor
    assert contact.business is business
    assert contact.contact_holder is business.contact_holder

for unit in business.units:
    for offer in unit.offers:
        # Multi-level navigation works
        assert offer.unit is unit
        assert offer.business is business
```

### UC-2: Automatic Invalidation on Parent Change

```python
# Before: Manual invalidation required (error-prone)
contact._contact_holder = new_holder
contact._invalidate_refs()  # Easy to forget!

# After: Auto-invalidation (descriptor handles it)
contact._contact_holder = new_holder
# _invalidate_refs() called automatically by descriptor __set__
assert contact._business is None  # Cleared automatically
```

### UC-3: Custom Holder Population (LocationHolder Override)

```python
class LocationHolder(Task, HolderMixin[Location]):
    """Override for Hours sibling handling."""

    def _populate_children(self, subtasks: list[Task]) -> None:
        # Hours detection logic specific to LocationHolder
        for task in subtasks:
            if self._is_hours_task(task):
                self._hours = Hours.model_validate(task.model_dump())
                self._hours._location_holder = self
            else:
                # Delegate Location children to base
                pass  # Use super() pattern

        # Let base handle Location children
        super()._populate_children([t for t in subtasks if not self._is_hours_task(t)])
```

### UC-4: Naming Migration (Reconciliation)

```python
# Before (deprecated, warns)
holder = business.reconciliations_holder  # DeprecationWarning

# After (preferred)
holder = business.reconciliation_holder

# HOLDER_KEY_MAP updated
Business.HOLDER_KEY_MAP = {
    # ... other holders ...
    "reconciliation_holder": ("Reconciliations", "abacus"),  # Key singular
}
```

### UC-5: Descriptor Type Safety in IDE

```python
# IDE shows: business: Business | None
class Contact(BusinessEntity):
    # Descriptor with generic type
    business: Business | None = ParentRef[Business](holder_attr="_contact_holder")

# Usage - IDE autocomplete works
contact = Contact.model_validate(data)
if contact.business:  # IDE knows this is Business | None
    print(contact.business.name)  # IDE shows Business attributes
```

---

## Technical Approach

### R1/R2: Descriptor Implementation

**Approach**: Python descriptors with `__get__` and `__set__` protocols.

```python
from typing import Generic, TypeVar, Any, overload

T = TypeVar("T")

class ParentRef(Generic[T]):
    """Descriptor for cached upward navigation with lazy resolution.

    Args:
        holder_attr: PrivateAttr name to resolve from (e.g., "_contact_holder")
        business_attr: Business reference on holder (default "_business")
        auto_invalidate: If True, setting this ref calls _invalidate_refs()
    """

    def __init__(
        self,
        holder_attr: str | None = None,
        business_attr: str = "_business",
        auto_invalidate: bool = True,
    ):
        self.holder_attr = holder_attr
        self.business_attr = business_attr
        self.auto_invalidate = auto_invalidate
        self.private_name: str
        self.public_name: str

    def __set_name__(self, owner: type, name: str) -> None:
        self.public_name = name
        self.private_name = f"_{name}"

    @overload
    def __get__(self, obj: None, objtype: type) -> "ParentRef[T]": ...
    @overload
    def __get__(self, obj: Any, objtype: type | None) -> T | None: ...

    def __get__(self, obj: Any, objtype: type | None = None) -> T | None | "ParentRef[T]":
        if obj is None:
            return self

        # Check cached value
        cached = getattr(obj, self.private_name, None)
        if cached is not None:
            return cached

        # Lazy resolution via holder
        if self.holder_attr:
            holder = getattr(obj, self.holder_attr, None)
            if holder is not None:
                resolved = getattr(holder, self.business_attr, None)
                if resolved is not None:
                    setattr(obj, self.private_name, resolved)
                    return resolved

        return None

    def __set__(self, obj: Any, value: T | None) -> None:
        setattr(obj, self.private_name, value)

        # Auto-invalidation on hierarchy change
        if self.auto_invalidate and hasattr(obj, "_invalidate_refs"):
            obj._invalidate_refs()


class HolderRef(Generic[T]):
    """Descriptor for direct holder property access."""

    def __set_name__(self, owner: type, name: str) -> None:
        self.public_name = name
        self.private_name = f"_{name}"

    @overload
    def __get__(self, obj: None, objtype: type) -> "HolderRef[T]": ...
    @overload
    def __get__(self, obj: Any, objtype: type | None) -> T | None: ...

    def __get__(self, obj: Any, objtype: type | None = None) -> T | None | "HolderRef[T]":
        if obj is None:
            return self
        return getattr(obj, self.private_name, None)

    def __set__(self, obj: Any, value: T | None) -> None:
        setattr(obj, self.private_name, value)
```

**Impact**: Each entity's navigation properties become single-line declarations.

### R3: HolderMixin Consolidation

**Approach**: Move common logic to base class with ClassVar configuration.

```python
class HolderMixin(Generic[T]):
    """Mixin providing holder population logic."""

    CHILD_TYPE: ClassVar[type[Task]]
    PARENT_REF_NAME: ClassVar[str]
    BUSINESS_REF_NAME: ClassVar[str] = "_business"
    CHILDREN_ATTR: ClassVar[str] = "_children"

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate typed children from fetched subtasks.

        Default implementation:
        1. Sort by (created_at, name)
        2. Convert each Task to CHILD_TYPE
        3. Set parent and business references
        4. Store in children list
        """
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )

        children = []
        for task in sorted_tasks:
            child = self.CHILD_TYPE.model_validate(task.model_dump())
            setattr(child, self.PARENT_REF_NAME, self)
            setattr(child, self.BUSINESS_REF_NAME, getattr(self, self.BUSINESS_REF_NAME, None))
            children.append(child)

        setattr(self, self.CHILDREN_ATTR, children)

    def _set_child_parent_ref(self, child: T) -> None:
        """Set parent reference on a single child."""
        setattr(child, self.PARENT_REF_NAME, self)
        setattr(child, self.BUSINESS_REF_NAME, getattr(self, self.BUSINESS_REF_NAME, None))
```

**Impact**: 9 nearly-identical implementations become 1.

### R4: Auto-Discovery Invalidation

**Approach**: Base class discovers refs via introspection.

```python
class BusinessEntity(Task):
    """Base for business layer entities."""

    # List of PrivateAttr names that hold cached references
    # Auto-discovered from class annotations or explicit list
    _CACHED_REF_ATTRS: ClassVar[tuple[str, ...]] = ()

    def _invalidate_refs(self) -> None:
        """Invalidate all cached references.

        Default implementation clears all attrs in _CACHED_REF_ATTRS.
        Subclasses may override to add additional logic.
        """
        for attr in self._CACHED_REF_ATTRS:
            if hasattr(self, attr):
                setattr(self, attr, None)

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-discover cached ref attrs from PrivateAttr annotations."""
        super().__init_subclass__(**kwargs)

        # Collect PrivateAttrs that look like refs
        ref_attrs = []
        for name, annotation in cls.__annotations__.items():
            if name.startswith("_") and "| None" in str(annotation):
                ref_attrs.append(name)

        cls._CACHED_REF_ATTRS = tuple(ref_attrs)
```

### R5/R6/R7: Naming Standardization

**Approach**: Rename with deprecation alias.

```python
class Business(BusinessEntity):
    # Updated HOLDER_KEY_MAP
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "contact_holder": ("Contacts", "busts_in_silhouette"),
        "unit_holder": ("Units", "package"),
        "location_holder": ("Location", "round_pushpin"),
        "dna_holder": ("DNA", "dna"),
        "reconciliation_holder": ("Reconciliations", "abacus"),  # Singular key
        "asset_edit_holder": ("Asset Edit", "art"),
        "videography_holder": ("Videography", "video_camera"),
    }

    # New property (singular)
    @property
    def reconciliation_holder(self) -> ReconciliationHolder | None:
        return self._reconciliation_holder

    # Deprecated alias (plural)
    @property
    def reconciliations_holder(self) -> ReconciliationHolder | None:
        warnings.warn(
            "reconciliations_holder is deprecated. Use reconciliation_holder instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self._reconciliation_holder
```

---

## Design Decisions

### DD-1: Single `ParentRef` Descriptor vs Multiple Types

**Decision**: Single `ParentRef[T]` with configuration parameters.

**Rationale**:
- Generic type parameter provides type safety
- Configuration via constructor handles all variations
- Simpler than multiple descriptor classes
- IDE support via `@overload` type hints

**Alternatives Considered**:
- `BusinessRef`, `HolderRef`, `IntermediateRef` - More specific but more code
- Protocol-based - Over-engineered for current needs

### DD-2: Type Safety Approach

**Decision**: Generic descriptors with `@overload` for IDE support.

**Rationale**:
- Python descriptors naturally support generic types
- `@overload` provides correct IDE inference
- No runtime overhead from type checking
- mypy validates at static analysis time

### DD-3: Invalidation Triggers

**Decision**: Auto-invalidate only on parent/holder reference changes via descriptor `__set__`.

**Rationale**:
- Covers primary use case (hierarchy mutations)
- Configurable via `auto_invalidate` parameter
- No performance regression on read access
- Explicit is better than implicit for other cases

**Not Included**:
- Auto-invalidation on `parent` Task property change (SDK layer, not business layer)
- Auto-invalidation on subtask addition/removal (out of scope)

### DD-4: Scope Limitation

**Decision**: Business entities only; SDK entities unchanged.

**Rationale**:
- SDK entities use `NameGid` - no navigation patterns exist
- Adding navigation to SDK entities is a different initiative
- Keeps scope focused and deliverable

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| **A1**: Explicit properties are preferred over `__getattr__` magic | Discovery Section 3.3 confirms this is intentional for type safety |
| **A2**: Sorting by (created_at, name) is correct for all holders | All 9 implementations use this; no variation |
| **A3**: `_reconciliations_holder` plural naming is a bug, not intentional | All other holders use singular; inconsistency noted in Discovery |
| **A4**: Descriptor overhead is negligible | Standard Python pattern; well-optimized |
| **A5**: Auto-invalidation on reference change is always safe | No known case where stale refs are intentionally preserved |

---

## Dependencies

| Dependency | Owner | Status | Impact |
|------------|-------|--------|--------|
| **Initiative A (Foundation)** | Architecture Hardening | Complete | Prerequisite - must be done first |
| **Initiative B (Custom Fields)** | Architecture Hardening | Complete | Prerequisite - B must complete first |
| **Pydantic PrivateAttr** | Pydantic Library | Stable | Descriptors work with PrivateAttr |
| **Python 3.10+ Generics** | Python | Stable | Generic[T] descriptor support |
| **Business layer entities** | SDK Models | Stable | All 10 entities must migrate |

### Blocks

| Blocked Initiative | Reason |
|--------------------|--------|
| **Initiative D (Resolution)** | Clean navigation patterns required before resolution enhancements |
| **Initiative E (Hydration)** | Consistent holder population required for hydration |
| **Initiative F (SaveSession)** | Reference invalidation must work before reliability improvements |

---

## Migration Guide

### Phase 1: Descriptor Infrastructure (Non-Breaking)

1. Add `ParentRef` and `HolderRef` descriptor classes to `models/business/descriptors.py`
2. Add `HolderMixin` enhancements to `models/business/base.py`
3. Add `_CACHED_REF_ATTRS` auto-discovery to `BusinessEntity`

### Phase 2: Entity Migration (Non-Breaking)

Migrate each entity one at a time:

```python
# Before (Contact)
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

# After (Contact)
class Contact(BusinessEntity):
    _business: Business | None = PrivateAttr(default=None)
    _contact_holder: ContactHolder | None = PrivateAttr(default=None)

    # Descriptors replace property implementations
    business: Business | None = ParentRef[Business](holder_attr="_contact_holder")
    contact_holder: ContactHolder | None = HolderRef[ContactHolder]()

    # _invalidate_refs() inherited from BusinessEntity via auto-discovery
```

### Phase 3: Holder Migration (Non-Breaking)

```python
# Before (ContactHolder)
class ContactHolder(Task, HolderMixin[Contact]):
    CHILD_TYPE = Contact
    _contacts: list[Contact] = PrivateAttr(default_factory=list)

    def _populate_children(self, subtasks: list[Task]) -> None:
        sorted_tasks = sorted(subtasks, key=lambda t: (t.created_at or "", t.name or ""))
        self._contacts = []
        for task in sorted_tasks:
            contact = Contact.model_validate(task.model_dump())
            contact._contact_holder = self
            contact._business = self._business
            self._contacts.append(contact)

# After (ContactHolder)
class ContactHolder(Task, HolderMixin[Contact]):
    CHILD_TYPE: ClassVar[type[Contact]] = Contact
    PARENT_REF_NAME: ClassVar[str] = "_contact_holder"
    CHILDREN_ATTR: ClassVar[str] = "_contacts"

    _contacts: list[Contact] = PrivateAttr(default_factory=list)

    # _populate_children() inherited from HolderMixin
```

### Phase 4: Naming Fix (Breaking with Deprecation)

```python
# Update Business.HOLDER_KEY_MAP
# Update Reconciliation._reconciliation_holder (singular)
# Add deprecated reconciliations_holder property alias
```

### Migration Order

1. **Contact/ContactHolder** - Simplest case, validation
2. **Unit/UnitHolder** - Tests nested holders
3. **Offer/OfferHolder** - Tests intermediate refs
4. **Process/ProcessHolder** - Similar to Offer
5. **Location/LocationHolder** - Override for Hours handling
6. **Hours** - No holder, simple navigation
7. **DNA/DNAHolder** - Direct child of Business
8. **AssetEdit/AssetEditHolder** - Direct child
9. **Videography/VideographyHolder** - Direct child
10. **Reconciliation** - Includes naming fix

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should SDK entities eventually get navigation descriptors? | Architect | TBD | Deferred - future initiative if needed |
| Should emoji fallback for holder detection be removed or implemented? | Architect | TBD | Deferred - name matching sufficient |
| Can circular imports be restructured to avoid runtime imports? | Architect | TBD | Deferred - runtime imports acceptable |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Type hint regression | Low | Medium | Extensive mypy testing; @overload coverage |
| Auto-invalidation causes performance regression | Low | Low | Configurable; only triggers on write |
| Migration introduces subtle bugs | Medium | High | Migrate one entity at a time; full test pass required |
| `reconciliations_holder` rename breaks code | Medium | Low | Deprecation alias provided |
| Descriptor complexity confuses maintainers | Low | Medium | Document patterns; code comments |

---

## Test Strategy

### Unit Tests

| Test Category | Coverage |
|---------------|----------|
| `ParentRef.__get__` | Returns cached value; lazy resolution; None handling |
| `ParentRef.__set__` | Sets value; triggers invalidation |
| `HolderRef.__get__` | Returns cached value; None handling |
| `HolderMixin._populate_children` | Sorting; typing; reference setting |
| `BusinessEntity._invalidate_refs` | Auto-discovery; clears all refs |
| `_CACHED_REF_ATTRS` discovery | Collects correct attrs |

### Integration Tests

| Test Category | Coverage |
|---------------|----------|
| Contact navigation | `contact.business`, `contact.contact_holder` |
| Unit navigation | `unit.business`, `unit.offers`, `unit.processes` |
| Offer navigation | `offer.business`, `offer.unit`, `offer.offer_holder` |
| Auto-invalidation | Setting holder clears business ref |
| Holder population | All 9 holders populate correctly |

### Regression Tests

| Test Category | Coverage |
|---------------|----------|
| All existing business entity tests pass | No regressions |
| All existing holder tests pass | No regressions |
| SaveSession with business entities | Commit/track unchanged |
| Hydration flows | Full hierarchy hydration works |

### Type Safety Tests

| Test Category | Coverage |
|---------------|----------|
| mypy strict mode | All files pass |
| IDE autocomplete | Manual verification |
| Generic type inference | Tests verify correct types |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Requirements Analyst | Initial draft based on DISCOVERY-HARDENING-C |

---

## Quality Gate Checklist

- [x] Problem statement is clear and compelling (~800 lines duplicated code, maintenance burden)
- [x] Scope explicitly defines in/out (9 in-scope, 6 out-of-scope items)
- [x] All requirements are specific and testable (FR-DESC-001 through FR-COMPAT-005)
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented (A1-A5)
- [x] Open questions documented with owners (3 questions, deferred)
- [x] Dependencies identified (A, B prerequisites; blocks D, E, F)
- [x] Design decisions documented (DD-1 through DD-4)
- [x] Migration guide provided (4 phases)
- [x] Risk assessment completed
- [x] Test strategy defined
