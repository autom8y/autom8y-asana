# ADR-0075: Navigation Descriptor Pattern

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: SDK Maintainers, Business Layer Consumers
- **Related**: PRD-HARDENING-C, TDD-HARDENING-C, ADR-0052 (bidirectional caching), ADR-0076 (auto-invalidation)

---

## Context

The SDK's business layer contains approximately 800 lines of duplicated navigation code across 10 business entities. Each entity independently implements nearly identical patterns:

```python
# Pattern repeated 6+ times across entities
@property
def business(self) -> Business | None:
    """Navigate to containing Business (cached)."""
    if self._business is None and self._contact_holder is not None:
        self._business = self._contact_holder._business
    return self._business

@property
def contact_holder(self) -> ContactHolder | None:
    """Navigate to containing ContactHolder (cached)."""
    return self._contact_holder
```

From DISCOVERY-HARDENING-C:
- 6 nearly-identical `business` navigation properties
- 10 holder navigation properties
- ~150 lines of duplicated navigation code
- Minor variations in holder reference names

**Forces at play**:
1. **DRY Principle**: Duplicated code is a maintenance burden
2. **Type Safety**: IDE autocomplete and mypy must continue working
3. **Lazy Resolution**: Navigation must resolve via holder chain when direct ref is None
4. **Pydantic Compatibility**: Pattern must work with Pydantic's PrivateAttr
5. **Performance**: Property access must be near-instant (~100ns)
6. **Backward Compatibility**: Existing API must remain unchanged

---

## Decision

Implement a **single generic descriptor pattern** using Python's descriptor protocol with two classes:

1. **`ParentRef[T]`**: For upward navigation with optional lazy resolution via holder chain
2. **`HolderRef[T]`**: For direct holder property access without lazy resolution

Both descriptors use Generic type parameters with `@overload` decorators for IDE type inference.

### Implementation

```python
from typing import Generic, TypeVar, Any, overload

T = TypeVar("T")

class ParentRef(Generic[T]):
    """Descriptor for cached upward navigation with lazy resolution."""

    def __init__(
        self,
        holder_attr: str | None = None,
        target_attr: str = "_business",
        auto_invalidate: bool = True,
    ) -> None:
        self.holder_attr = holder_attr
        self.target_attr = target_attr
        self.auto_invalidate = auto_invalidate

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
        cached = getattr(obj, self.private_name, None)
        if cached is not None:
            return cached
        if self.holder_attr:
            holder = getattr(obj, self.holder_attr, None)
            if holder:
                resolved = getattr(holder, self.target_attr, None)
                if resolved:
                    setattr(obj, self.private_name, resolved)
                    return resolved
        return None

    def __set__(self, obj: Any, value: T | None) -> None:
        setattr(obj, self.private_name, value)
        if self.auto_invalidate and hasattr(obj, "_invalidate_refs"):
            obj._invalidate_refs(_exclude_attr=self.private_name)


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

### Usage Pattern

```python
class Contact(BusinessEntity):
    _business: Business | None = PrivateAttr(default=None)
    _contact_holder: ContactHolder | None = PrivateAttr(default=None)

    # Replaces 12-line property implementation
    business: Business | None = ParentRef[Business](holder_attr="_contact_holder")
    contact_holder: ContactHolder | None = HolderRef[ContactHolder]()
```

---

## Rationale

### Why Descriptors?

1. **Native Python Pattern**: Descriptors are Python's built-in mechanism for customizing attribute access
2. **Composable**: Same descriptor class works across all entities with different configuration
3. **Type-Safe**: Generic type parameters preserve IDE autocomplete
4. **Zero Runtime Overhead**: No function call overhead beyond standard attribute access
5. **Pydantic Compatible**: Works alongside PrivateAttr without conflict

### Why Single `ParentRef[T]` vs Multiple Types?

Considered having separate descriptor types:
- `BusinessRef` for Business navigation
- `HolderRef` for holder navigation
- `IntermediateRef` for unit navigation (Offer -> Unit)

**Rejected because**:
- All variations are handled by `ParentRef` configuration parameters
- `holder_attr` enables lazy resolution when needed
- `target_attr` allows resolving to different parent attributes
- Fewer classes = less code to maintain

### Why `@overload` for Type Safety?

The `@overload` decorator allows different return types based on how the descriptor is accessed:

```python
# Class access returns the descriptor itself
Contact.business  # type: ParentRef[Business]

# Instance access returns the value
contact.business  # type: Business | None
```

This pattern is used by Pydantic's `computed_field` and is well-supported by mypy and IDEs.

---

## Alternatives Considered

### Alternative 1: Mixin with `__getattr__`

```python
class NavigationMixin:
    def __getattr__(self, name: str) -> Any:
        if name in self._NAVIGATION_MAP:
            return self._resolve_navigation(name)
        raise AttributeError(name)
```

- **Pros**: Very DRY, dynamic
- **Cons**:
  - Breaks IDE autocomplete (no static type info)
  - `__getattr__` is a fallback, harder to debug
  - mypy cannot infer types
- **Why not chosen**: Type safety is a hard requirement per PRD

### Alternative 2: Protocol-Based Approach

```python
class Navigable(Protocol[T]):
    @property
    def _holder(self) -> T | None: ...
    @property
    def business(self) -> Business | None: ...
```

- **Pros**: Clean interface definition, good for testing
- **Cons**:
  - Still requires property implementations
  - Doesn't reduce code duplication
  - Protocols define interface, not behavior
- **Why not chosen**: Protocols don't provide implementation, just contracts

### Alternative 3: Code Generation

Generate navigation properties at class definition time using metaclass or `__init_subclass__`.

- **Pros**: Maximum DRY, properties exist at class definition
- **Cons**:
  - Complex metaclass interaction with Pydantic
  - Generated code is harder to debug
  - IDE support varies
- **Why not chosen**: Descriptors achieve same goal with simpler, standard pattern

### Alternative 4: Multiple Descriptor Types

```python
class BusinessRef(Generic[T]): ...  # For Business navigation
class HolderRef(Generic[T]): ...    # For holder navigation
class IntermediateRef(Generic[T]): ...  # For Unit navigation
```

- **Pros**: More specific types, clearer intent
- **Cons**:
  - More classes to maintain
  - Overlapping functionality
  - Configuration via constructor is more flexible
- **Why not chosen**: Single `ParentRef[T]` with configuration handles all cases

---

## Consequences

### Positive

1. **~150 lines of navigation code reduced to ~50 lines**
   - 6 navigation properties -> 6 one-line declarations
   - 10 holder properties -> 10 one-line declarations

2. **Type safety maintained**
   - mypy passes with `--strict`
   - IDE autocomplete works correctly
   - `@overload` provides accurate type inference

3. **Lazy resolution preserved**
   - `holder_attr` parameter enables resolution via holder chain
   - Caching behavior unchanged

4. **Backward compatibility**
   - All existing code using `contact.business` continues to work
   - No API changes for consumers

5. **Foundation for auto-invalidation**
   - Descriptor `__set__` provides hook for ADR-0076

### Negative

1. **Learning curve**
   - Developers must understand descriptor protocol
   - Generic type parameters add complexity
   - Mitigation: Document pattern thoroughly

2. **Debugging indirection**
   - Stack traces go through descriptor `__get__/__set__`
   - Mitigation: Clear docstrings, logging in descriptors

3. **Two locations for type hints**
   - PrivateAttr still needed for storage
   - Descriptor declaration for access pattern
   - Mitigation: Consistent pattern makes this predictable

### Neutral

1. **Pydantic integration unchanged**
   - PrivateAttr continues to work
   - Descriptors complement, don't replace

2. **Performance unchanged**
   - Descriptor access is equivalent to property access
   - No measurable difference in benchmarks

---

## Compliance

Ensure this decision is followed:

1. **Code Review Checklist**:
   - [ ] New navigation properties use `ParentRef[T]` or `HolderRef[T]`
   - [ ] No new copy-paste navigation property implementations
   - [ ] Generic type parameter matches PrivateAttr type

2. **Linting**:
   - mypy `--strict` must pass (enforces type annotations)
   - Custom rule: warn on `@property` with pattern `if self._x is None and self._y`

3. **Documentation**:
   - All business entities document descriptor usage in module docstring
   - Migration guide in TDD-HARDENING-C

4. **Tests**:
   - Unit tests for descriptor behavior
   - Integration tests for navigation across entity boundaries
