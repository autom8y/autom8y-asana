# ADR-0076: Auto-Invalidation Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: SDK Maintainers, Business Layer Consumers
- **Related**: PRD-HARDENING-C, TDD-HARDENING-C, ADR-0052 (bidirectional caching), ADR-0075 (navigation descriptors)

---

## Context

From DISCOVERY-HARDENING-C:

> **Critical Gap**: `_invalidate_refs()` is defined but rarely called automatically.
> - Call Sites Found: None in SaveSession, None in hydration code
> - Manual call required on parent changes
> - **Risk**: Stale references if hierarchy mutates without explicit invalidation.

All 10 business entities implement `_invalidate_refs()` to clear cached navigation references:

```python
# Pattern repeated across 10 entities
def _invalidate_refs(self) -> None:
    """Invalidate cached references on hierarchy change."""
    self._business = None
    self._contact_holder = None
```

**The problem**: This method exists but is never called automatically. When a parent reference changes, the developer must remember to call `_invalidate_refs()` manually:

```python
# Error-prone manual pattern
contact._contact_holder = new_holder
contact._invalidate_refs()  # Easy to forget!
```

**Forces at play**:
1. **Correctness**: Stale references lead to incorrect data access
2. **Developer Experience**: Manual invalidation is error-prone
3. **Performance**: Invalidation should not trigger on every access
4. **Configurability**: Some use cases may want to preserve cached values
5. **Inheritance**: Pattern must work across entity hierarchy

---

## Decision

Implement **automatic reference invalidation** via three mechanisms:

### 1. Descriptor-Triggered Invalidation

The `ParentRef[T]` and `HolderRef[T]` descriptors from ADR-0075 trigger invalidation in their `__set__` method when a reference changes:

```python
class ParentRef(Generic[T]):
    def __init__(
        self,
        holder_attr: str | None = None,
        target_attr: str = "_business",
        auto_invalidate: bool = True,  # Configurable
    ) -> None:
        self.auto_invalidate = auto_invalidate
        # ...

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
```

### 2. Auto-Discovery via `__init_subclass__`

`BusinessEntity` automatically discovers cached reference attributes at class definition time:

```python
class BusinessEntity(Task):
    _CACHED_REF_ATTRS: ClassVar[tuple[str, ...]] = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        ref_attrs: list[str] = []
        for name, annotation in getattr(cls, "__annotations__", {}).items():
            if not name.startswith("_"):
                continue
            ann_str = str(annotation)
            if "list[" in ann_str.lower():
                continue  # Skip children lists
            if "| None" in ann_str or "Optional" in ann_str:
                ref_attrs.append(name)

        parent_refs = getattr(cls.__bases__[0], "_CACHED_REF_ATTRS", ())
        cls._CACHED_REF_ATTRS = tuple(set(parent_refs) | set(ref_attrs))
```

### 3. Generic `_invalidate_refs()` Implementation

Base implementation clears all discovered refs, with `_exclude_attr` to prevent clearing the attr that triggered invalidation:

```python
def _invalidate_refs(self, _exclude_attr: str | None = None) -> None:
    """Invalidate all cached navigation references.

    Args:
        _exclude_attr: Attr to skip (used by descriptors to avoid
                      clearing the attr that triggered invalidation).
    """
    for attr in self._CACHED_REF_ATTRS:
        if attr != _exclude_attr and hasattr(self, attr):
            setattr(self, attr, None)
```

### Invalidation Scope

**Auto-invalidation triggers ONLY on**:
- Setting `_business` via `ParentRef` descriptor
- Setting holder refs (e.g., `_contact_holder`) via `HolderRef` descriptor

**Auto-invalidation does NOT trigger on**:
- Read access (`contact.business` returns cached without side effects)
- Setting non-descriptor private attrs directly
- Setting the same value (identity check: `old_value is not value`)

---

## Rationale

### Why Descriptor-Triggered?

The descriptor `__set__` method is the natural point to detect reference changes:

1. **Centralized**: Single location for invalidation logic
2. **Automatic**: No manual calls needed
3. **Selective**: Only triggers on actual writes, not reads
4. **Configurable**: `auto_invalidate=False` disables if needed

### Why Auto-Discovery?

Manual registration of refs is error-prone:

```python
# Manual (error-prone)
_CACHED_REF_ATTRS = ("_business", "_contact_holder")  # Easy to miss one

# Auto-discovery (robust)
# _CACHED_REF_ATTRS automatically populated from annotations
```

Auto-discovery via `__init_subclass__`:
- Runs once at class definition, not per-instance
- Works with inheritance (combines parent and child refs)
- Uses existing type annotations (no duplicate info)

### Why `_exclude_attr`?

When a descriptor triggers invalidation, we shouldn't clear the attr that was just set:

```python
contact._contact_holder = new_holder
# Descriptor calls: contact._invalidate_refs(_exclude_attr="_contact_holder")
# Result: _business=None, _contact_holder=new_holder (not cleared)
```

Without this, the new value would be immediately cleared.

### Why Only Parent/Holder Refs?

Invalidation scope is deliberately limited to parent navigation refs because:

1. **These are the refs affected by hierarchy changes**
2. **Children lists have different lifecycle** (managed by holders)
3. **Minimizes unnecessary work** (don't clear unrelated state)

---

## Alternatives Considered

### Alternative 1: `__setattr__` Override on BusinessEntity

```python
class BusinessEntity(Task):
    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if name in self._HIERARCHY_CHANGING_ATTRS:
            self._invalidate_refs()
```

- **Pros**: Works without descriptors, catches all attribute sets
- **Cons**:
  - Triggers on every `__setattr__`, including internal Pydantic operations
  - Performance overhead on every attribute access
  - Conflicts with Pydantic's model initialization
- **Why not chosen**: Too broad, causes Pydantic conflicts

### Alternative 2: Event-Based Invalidation

```python
class BusinessEntity(Task):
    def on_hierarchy_change(self, event: HierarchyChangeEvent) -> None:
        self._invalidate_refs()
```

- **Pros**: Explicit events, clear causality
- **Cons**:
  - Requires event dispatch infrastructure
  - Caller still needs to emit events (same problem as manual calls)
  - Over-engineered for the use case
- **Why not chosen**: Events just move the manual step elsewhere

### Alternative 3: Eager Invalidation on All Writes

```python
def __set__(self, obj: Any, value: T | None) -> None:
    setattr(obj, self.private_name, value)
    obj._invalidate_refs()  # Always invalidate, no check
```

- **Pros**: Simple, always correct
- **Cons**:
  - Invalidates even when value unchanged
  - Invalidates even when explicitly re-assigning same object
  - Unnecessary work
- **Why not chosen**: Identity check (`old is not new`) is cheap and prevents unnecessary invalidation

### Alternative 4: No Auto-Invalidation (Manual Only)

Keep current pattern of manual `_invalidate_refs()` calls.

- **Pros**: Explicit, no magic
- **Cons**:
  - Discovery showed this is error-prone
  - Stale reference bugs are hard to diagnose
  - PRD explicitly requires auto-invalidation (FR-INV-003)
- **Why not chosen**: Violates PRD requirements, known to cause bugs

### Alternative 5: WeakRef-Based Invalidation

Use `weakref` to detect when parent objects are garbage collected.

- **Pros**: Automatic cleanup when parents are freed
- **Cons**:
  - Doesn't handle parent replacement (new holder, same old holder still alive)
  - WeakRefs add complexity to serialization
  - Pydantic models don't serialize weakrefs
- **Why not chosen**: Doesn't solve the actual problem (parent replacement)

---

## Consequences

### Positive

1. **Automatic correctness**
   - No more stale reference bugs from forgotten `_invalidate_refs()` calls
   - Hierarchy changes automatically clear dependent caches

2. **Reduced boilerplate**
   - 10 copies of `_invalidate_refs()` -> 1 base implementation
   - ~80 lines of duplicated code eliminated

3. **Configurable**
   - `auto_invalidate=False` available for special cases
   - Subclasses can override `_invalidate_refs()` for additional logic

4. **No performance regression**
   - Only triggers on write (not read)
   - Identity check prevents unnecessary invalidation
   - `_CACHED_REF_ATTRS` computed once at class definition

5. **Works with Pydantic**
   - `__init_subclass__` compatible with Pydantic's metaclass
   - PrivateAttr storage unchanged

### Negative

1. **Implicit behavior**
   - Developers may not realize invalidation is happening
   - Mitigation: Clear documentation, DEBUG logging

2. **`__init_subclass__` complexity**
   - Less familiar pattern than simple methods
   - Mitigation: Well-commented implementation

3. **Annotation parsing fragility**
   - String-based annotation matching (`"| None"`) could miss edge cases
   - Mitigation: Comprehensive tests for discovery

### Neutral

1. **Subclass override still supported**
   - `Unit._invalidate_refs()` can call `super()` then clear nested holders
   - Existing pattern preserved for complex cases

2. **Same invalidation semantics**
   - All refs cleared (except trigger), same as before
   - Just automatic instead of manual

---

## Compliance

Ensure this decision is followed:

1. **Code Review Checklist**:
   - [ ] No manual `_invalidate_refs()` calls in normal code paths
   - [ ] New ref attrs use `T | None` annotation (for auto-discovery)
   - [ ] Subclass overrides call `super()._invalidate_refs(_exclude_attr)`

2. **Testing**:
   - [ ] Test that setting holder clears business ref
   - [ ] Test that setting same value doesn't trigger invalidation
   - [ ] Test that `_exclude_attr` prevents self-clearing
   - [ ] Test `_CACHED_REF_ATTRS` discovery for each entity

3. **Logging**:
   - DEBUG log when auto-invalidation triggers
   - Format: `"Auto-invalidating refs for {entity_type}.{attr} change"`

4. **Documentation**:
   - Document auto-invalidation behavior in `BusinessEntity` docstring
   - Note configurable `auto_invalidate` parameter in descriptor docs

---

## Appendix: Entity-Specific `_CACHED_REF_ATTRS`

Expected auto-discovered values per entity:

| Entity | `_CACHED_REF_ATTRS` |
|--------|---------------------|
| Contact | `("_business", "_contact_holder")` |
| Unit | `("_business", "_unit_holder", "_offer_holder", "_process_holder")` |
| Offer | `("_business", "_unit", "_offer_holder")` |
| Process | `("_business", "_unit", "_process_holder")` |
| Location | `("_business", "_location_holder")` |
| Hours | `("_business", "_location_holder")` |
| DNA | `("_business", "_dna_holder")` |
| Reconciliation | `("_business", "_reconciliation_holder")` |
| AssetEdit | `("_business", "_asset_edit_holder")` |
| Videography | `("_business", "_videography_holder")` |

These should be verified by unit tests after implementation.
