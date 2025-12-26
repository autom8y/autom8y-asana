# ADR-0053: Descriptor Patterns for Domain Layer

## Metadata
- **Status**: Accepted
- **Consolidated From**: ADR-0075 (Navigation Descriptor), ADR-0077 (Pydantic Compatibility), ADR-0081 (Custom Field Descriptor), ADR-0117 (Accessor/Descriptor Unification), ADR-0141 (Field Mixin Strategy)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Related**: [reference/PATTERNS.md](reference/PATTERNS.md)

---

## Context

The business layer contained approximately 950 lines of repetitive property code across 10 entities:
- **Navigation properties**: ~150 lines for upward traversal (Unit → Business) and holder access
- **Custom field properties**: ~800 lines for 108 custom fields (7-8 lines per field × 108)

Example of duplication:

```python
# Navigation (12 lines per entity)
@property
def business(self) -> Business | None:
    if self._business is None and self._contact_holder is not None:
        self._business = self._contact_holder._business
    return self._business

@property
def contact_holder(self) -> ContactHolder | None:
    return self._contact_holder

# Custom fields (7-8 lines per field)
@property
def company_id(self) -> str | None:
    return self._get_text_field(self.Fields.COMPANY_ID)

@company_id.setter
def company_id(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.COMPANY_ID, value)
```

**Forces at play**:
1. **DRY principle**: Duplication is maintenance burden
2. **Type safety**: IDE autocomplete and mypy must work
3. **Pydantic compatibility**: Descriptors must coexist with Pydantic v2
4. **Lazy resolution**: Navigation must traverse holder chain when direct ref is None
5. **Performance**: Property access must be near-instant (~100ns)
6. **Backward compatibility**: External API unchanged

---

## Decision

**Use Python descriptor protocol (`__get__`, `__set__`, `__set_name__`) with Generic type parameters for declarative attribute access.**

All entity property patterns consolidated into descriptor families:
1. **Navigation descriptors**: ParentRef[T], HolderRef[T]
2. **Custom field descriptors**: TextField, EnumField, NumberField, DateField, PeopleField, MultiEnumField, IntField
3. **Field mixins**: SharedCascadingFieldsMixin, FinancialFieldsMixin

### 1. Navigation Descriptor Pattern

**Purpose**: Eliminate navigation property boilerplate.

```python
# Before: 12 lines
@property
def business(self) -> Business | None:
    if self._business is None and self._contact_holder is not None:
        self._business = self._contact_holder._business
    return self._business

# After: 1 line
business: Business | None = ParentRef[Business](holder_attr="_contact_holder")
```

**Implementation**:

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
            return self  # Class access returns descriptor
        cached = getattr(obj, self.private_name, None)
        if cached is not None:
            return cached
        # Lazy resolution via holder chain
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
    """Descriptor for direct holder property access (no lazy resolution)."""

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

**Usage**:
```python
class Contact(BusinessEntity):
    _business: Business | None = PrivateAttr(default=None)
    _contact_holder: ContactHolder | None = PrivateAttr(default=None)

    business: Business | None = ParentRef[Business](holder_attr="_contact_holder")
    contact_holder: ContactHolder | None = HolderRef[ContactHolder]()
```

**Impact**: ~150 lines → ~50 lines (67% reduction).

### 2. Custom Field Descriptor Pattern

**Purpose**: Eliminate custom field property boilerplate.

```python
# Before: 7-8 lines per field
@property
def company_id(self) -> str | None:
    return self._get_text_field(self.Fields.COMPANY_ID)

@company_id.setter
def company_id(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

# After: 1 line per field
company_id = TextField()  # Field name auto-derived from property name
```

**Descriptor Hierarchy**:

```
CustomFieldDescriptor[T]  (Generic base)
    |
    +-- TextField          -> str | None
    +-- EnumField          -> str | None
    +-- MultiEnumField     -> list[str]
    +-- NumberField        -> Decimal | None
    +-- IntField           -> int | None
    +-- PeopleField        -> list[dict[str, Any]]
    +-- DateField          -> date | None
```

**Base Descriptor** (simplified):

```python
class CustomFieldDescriptor(Generic[T]):
    """Base descriptor for custom field access."""

    def __init__(self, field_name: str | None = None) -> None:
        self._field_name = field_name
        self._public_name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        self._public_name = name
        # Auto-derive Asana field name: "company_id" → "Company ID"
        if self._field_name is None:
            self._field_name = name.replace("_", " ").title()

    @property
    def field_name(self) -> str:
        return self._field_name

    @overload
    def __get__(self, obj: None, objtype: type) -> "CustomFieldDescriptor[T]": ...
    @overload
    def __get__(self, obj: Any, objtype: type | None) -> T: ...

    def __get__(self, obj: Any, objtype: type | None = None) -> T | "CustomFieldDescriptor[T]":
        if obj is None:
            return self
        return self._get_value(obj)

    def __set__(self, obj: Any, value: T) -> None:
        self._set_value(obj, value)

    def _get_value(self, obj: Any) -> T:
        """Subclass implements type-specific retrieval."""
        raise NotImplementedError

    def _set_value(self, obj: Any, value: T) -> None:
        """Subclass implements type-specific storage."""
        raise NotImplementedError
```

**Type-Specific Subclasses**:

```python
class TextField(CustomFieldDescriptor[str | None]):
    """Descriptor for text custom fields."""

    def _get_value(self, obj: Any) -> str | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None or isinstance(value, str):
            return value
        return str(value)

    def _set_value(self, obj: Any, value: str | None) -> None:
        obj.get_custom_fields().set(self.field_name, value)


class EnumField(CustomFieldDescriptor[str | None]):
    """Descriptor for enum custom fields."""

    def _get_value(self, obj: Any) -> str | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        # Extract name from {"gid": "...", "name": "..."} dict
        if isinstance(value, dict):
            return value.get("name")
        return str(value)

    def _set_value(self, obj: Any, value: str | None) -> None:
        obj.get_custom_fields().set(self.field_name, value)


class NumberField(CustomFieldDescriptor[Decimal | None]):
    """Descriptor for number custom fields."""

    def _get_value(self, obj: Any) -> Decimal | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    def _set_value(self, obj: Any, value: Decimal | None) -> None:
        obj.get_custom_fields().set(self.field_name, value)
```

**Impact**: ~800 lines → ~110 declarative lines (86% reduction).

### 3. Layered Architecture: Descriptors + Accessor

**Key insight**: Descriptors are domain layer; they delegate to infrastructure layer.

```
Domain Layer (Consumer-Facing)
+--------------------------------------------------+
|  CustomFieldDescriptor subclasses                |
|  - TextField, EnumField, NumberField, DateField  |
|  - Declarative: `company_id = TextField()`       |
|  - Type transformation (enum->str, date->Arrow)  |
+--------------------------------------------------+
                        |
                        | calls internally
                        v
+--------------------------------------------------+
|  CustomFieldAccessor                             |
|  - obj.get_custom_fields().get/set()            |
|  - Name-to-GID resolution                        |
|  - Type validation                               |
|  - Change tracking for SaveSession               |
|  - API serialization                             |
+--------------------------------------------------+
Infrastructure Layer (Implementation Detail)
```

**Usage guidance**:

| Use Case | Pattern | Example |
|----------|---------|---------|
| Business entity field access | Descriptor property | `business.vertical` |
| Business entity field mutation | Descriptor property | `business.mrr = Decimal("1000")` |
| Generic Task field access | Accessor via method | `task.custom_fields_editor().get("Status")` |
| Raw API serialization | Accessor method | `accessor.to_api_dict()` |

### 4. Field Mixin Strategy

**Purpose**: Share common field descriptors across entities.

**Problem**: 17 duplicate field declarations across Business, Unit, Offer, Process.

**Solution**: Two coarse-grained mixins:

```python
class SharedCascadingFieldsMixin:
    """Fields that cascade through entity hierarchy."""
    vertical = EnumField()
    rep = PeopleField()


class FinancialFieldsMixin:
    """Financial tracking fields."""
    booking_type = EnumField()
    mrr = NumberField(field_name="MRR")
    weekly_ad_spend = NumberField()
```

**Usage**:

```python
class Unit(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin):
    # Inherits: vertical, rep, booking_type, mrr, weekly_ad_spend
    # Plus entity-specific fields:
    market = TextField()
```

**Impact**: 17 duplicate declarations → 5 mixin definitions (12 fewer declarations).

**Mixin Application**:

| Entity | SharedCascading | Financial | Fields Used | Fields Ignored |
|--------|----------------|-----------|-------------|----------------|
| Business | YES | YES | vertical, rep, booking_type | mrr, weekly_ad_spend |
| Unit | YES | YES | ALL | - |
| Offer | YES | YES | vertical, rep, mrr, weekly_ad_spend | booking_type |
| Process | YES | YES | ALL | - |

### 5. Pydantic v2 Compatibility

**Configuration**:

```python
class BusinessEntity(Task):
    model_config = ConfigDict(
        ignored_types=(
            ParentRef, HolderRef,  # Navigation descriptors
            TextField, EnumField, NumberField, DateField,  # Custom field descriptors
            PeopleField, MultiEnumField, IntField,
        ),
        extra="allow",  # Allow descriptor __set__ delegation
    )
```

**Rationale**: `ignored_types` tells Pydantic to skip descriptor instances during model validation. Descriptors operate alongside Pydantic PrivateAttr without conflict.

---

## Rationale

### Why Descriptors?

| Approach | Pros | Cons |
|----------|------|------|
| Current (properties) | Explicit, familiar | 950 lines boilerplate, duplication |
| Code generation | No runtime overhead | Build step, harder to debug |
| Metaclass magic | Centralized logic | Complex, hard to understand |
| **Descriptors** | **Declarative, Pythonic, proven** | Learning curve (mitigated by precedent) |

Descriptors are Python's native mechanism for customizing attribute access. Used by:
- `@property`
- `@classmethod`, `@staticmethod`
- Django ORM fields
- SQLAlchemy columns
- Pydantic computed fields

### Why Generic Type Parameters?

```python
business: Business | None = ParentRef[Business](...)
vertical = EnumField()  # Returns str | None
```

Generic type parameter `T` flows through to IDE and mypy:
- Autocomplete works: `contact.business.` shows Business methods
- Type checking works: `mypy` infers `contact.business` is `Business | None`
- No runtime cost: Generics are erased at runtime

### Why @overload for Type Safety?

```python
@overload
def __get__(self, obj: None, objtype: type) -> "ParentRef[T]": ...  # Class access

@overload
def __get__(self, obj: Any, objtype: type | None) -> T | None: ...  # Instance access

def __get__(self, obj: Any, objtype: type | None = None) -> T | None | "ParentRef[T]":
    # Implementation handles both
```

This pattern (used by Pydantic's `computed_field`) provides correct types:
- `Contact.business` → `ParentRef[Business]` (descriptor itself)
- `contact.business` → `Business | None` (resolved value)

### Why Coarse-Grained Mixins?

**Alternative**: 5 single-field mixins (VerticalFieldMixin, RepFieldMixin, etc.)

**Trade-off**:

| Factor | Coarse (2) | Fine (5) |
|--------|------------|----------|
| MRO complexity | Simple | Complex (5 bases) |
| Maintenance | Edit 1 file | Edit specific mixin |
| Unused fields | Harmless (return None) | None |

**Decision**: Coarse-grained wins. Unused descriptors cause no harm—they just return `None` if field doesn't exist in Asana.

### Why Descriptors Delegate to Accessor?

**Separation of concerns**:
- **Descriptors** (domain layer): Provide property syntax, type transformation
- **Accessor** (infrastructure layer): Name-to-GID resolution, dirty tracking, API serialization

This layering enables:
- Generic Task access via accessor (no descriptors needed)
- Business entity access via descriptors (domain-specific properties)
- Single source of truth for field resolution (`CustomFieldAccessor._resolve_gid()`)

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
- **Cons**: Breaks IDE autocomplete, mypy cannot infer types, `__getattr__` is fallback
- **Why not chosen**: Type safety hard requirement

### Alternative 2: Protocol-Based Approach

```python
class Navigable(Protocol[T]):
    @property
    def business(self) -> Business | None: ...
```

- **Pros**: Clean interface, good for testing
- **Cons**: Still requires property implementations, doesn't reduce duplication
- **Why not chosen**: Protocols define interface, not behavior

### Alternative 3: Code Generation

- **Description**: Generate properties at build time from schema
- **Pros**: No runtime overhead, explicit generated code
- **Cons**: Build step complexity, schema drift risk, generated code harder to debug
- **Why not chosen**: Runtime descriptors simpler, match existing patterns

### Alternative 4: Multiple Descriptor Types

```python
class BusinessRef(Generic[T]): ...  # For Business navigation
class HolderRef(Generic[T]): ...    # For holder navigation
class IntermediateRef(Generic[T]): ...  # For Unit navigation
```

- **Pros**: More specific types, clearer intent
- **Cons**: More classes to maintain, overlapping functionality
- **Why not chosen**: Single `ParentRef[T]` with configuration handles all cases

---

## Consequences

### Positive

1. **~800 lines eliminated**: 950 → ~110 declarative lines total
2. **Type safety preserved**: mypy passes `--strict`, IDE autocomplete works
3. **Lazy resolution maintained**: Holder chain traversal via `holder_attr`
4. **Backward compatible**: All existing `contact.business` calls work unchanged
5. **Pattern consistency**: All descriptors follow same design
6. **Foundation for auto-generation**: `__set_name__` enables Fields class auto-generation
7. **Mixin reuse**: Shared fields defined once

### Negative

1. **Learning curve**: Developers must understand descriptor protocol
   - *Mitigation*: Pattern is well-documented, precedent in Django/SQLAlchemy
2. **Debugging indirection**: Stack traces include descriptor `__get__/__set__`
   - *Mitigation*: Clear error messages, consistent pattern is learnable
3. **Two locations for type hints**: PrivateAttr for storage, descriptor for access
   - *Mitigation*: Consistent convention makes this predictable
4. **Unused fields on some entities**: Business has `mrr` descriptor but no Asana field
   - *Mitigation*: Returns `None`, no error—acceptable

### Neutral

1. **Performance**: Descriptor access equivalent to property access (~100ns)
2. **Pydantic integration**: Works via `ignored_types`, no conflicts
3. **Generic type erasure**: Runtime types are non-generic, but IDE support works

---

## Compliance

### How This Decision Will Be Enforced

1. **Code review checklist**:
   - [ ] New navigation properties use `ParentRef[T]` or `HolderRef[T]`
   - [ ] New custom fields use descriptor subclass (TextField, EnumField, etc.)
   - [ ] Shared fields added to appropriate mixin
   - [ ] Generic type parameter matches PrivateAttr type
   - [ ] Descriptors in `model_config.ignored_types`

2. **Linting**:
   - `mypy --strict` enforces type annotations
   - Custom rule: warn on `@property` with pattern `if self._x is None and self._y` (navigation duplication)

3. **Documentation**:
   - Business entities document descriptor usage in module docstring
   - Pattern examples in contributor guide

4. **Tests**:
   - Unit tests for descriptor behavior
   - Integration tests for navigation across entity boundaries
   - Type inference tests (`reveal_type()` assertions)

---

## Pattern Catalog

**When you need to...**

| Need | Descriptor | Example |
|------|-----------|---------|
| Navigate to parent entity | ParentRef[T] | `business: Business \| None = ParentRef[Business](holder_attr="_contact_holder")` |
| Access direct holder | HolderRef[T] | `contact_holder: ContactHolder \| None = HolderRef[ContactHolder]()` |
| Text custom field | TextField | `company_id = TextField()` |
| Enum custom field | EnumField | `vertical = EnumField()` |
| Number custom field | NumberField | `mrr = NumberField(field_name="MRR")` |
| Date custom field | DateField | `start_date = DateField()` |
| People custom field | PeopleField | `rep = PeopleField()` |
| Share fields across entities | Mixin | `class Unit(..., SharedCascadingFieldsMixin): ...` |

---

**Related**: ADR-SUMMARY-CUSTOM-FIELDS (field resolution), ADR-SUMMARY-DATA-MODEL (entity hierarchy), reference/PATTERNS.md (full catalog)

**Supersedes**: Individual ADRs ADR-0075, ADR-0077, ADR-0081, ADR-0117, ADR-0141
