# ADR-0007: Custom Field Accessors and Descriptors

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0051, ADR-0062, ADR-0081, ADR-0117
- **Related**: reference/CUSTOM-FIELDS.md

## Context

The SDK needs typed access to 108 business-specific custom fields across 5 models (Business, Contact, Unit, Offer, Process). Users expect both programmatic access via properties with type hints AND dictionary-style syntax for ad-hoc queries.

The evolution proceeded through three phases:

1. **Phase 1 (ADR-0051)**: Typed property accessors delegating to CustomFieldAccessor
2. **Phase 2 (ADR-0062)**: Dictionary-style access via `__getitem__`/`__setitem__`
3. **Phase 3 (ADR-0081)**: Descriptor pattern to eliminate 800+ lines of boilerplate

Two patterns emerged that appeared to create duality but are actually properly layered:
- **CustomFieldAccessor** (infrastructure): name-to-GID resolution, change tracking, API serialization
- **CustomFieldDescriptor subclasses** (domain): typed properties, transformation, auto-generated Fields class

## Decision

**Implement a layered architecture where CustomFieldDescriptor subclasses (domain layer) wrap CustomFieldAccessor infrastructure (implementation layer). The accessor provides dictionary-style access and is the single source of truth for field resolution.**

### Architecture

```
Domain Layer (Consumer-Facing)
  CustomFieldDescriptor subclasses
    - TextField, EnumField, NumberField, DateField, etc.
    - Declarative: company_id = TextField()
    - Type transformation
    - Auto-generated Fields class

  delegates internally to

Infrastructure Layer (Implementation)
  CustomFieldAccessor
    - obj.get_custom_fields().get/set()
    - obj.custom_fields["field_name"] (dictionary syntax)
    - Name-to-GID resolution
    - Change tracking (_modifications dict)
    - API serialization (to_api_dict())
```

### Descriptor Pattern

```python
# Before: 7-8 lines per field × 108 fields = 800+ lines
class Business(Task):
    class Fields:
        COMPANY_ID = "Company ID"

    @property
    def company_id(self) -> str | None:
        return self.get_custom_fields().get(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)


# After: 1 line per field × 108 fields = ~110 lines (86% reduction)
class Business(Task):
    company_id = TextField()
    mrr = NumberField()
    vertical = EnumField()
```

### Descriptor Hierarchy

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

Key design elements:
1. **Generic Type Parameter**: `CustomFieldDescriptor[T]` carries return type for IDE inference
2. **`__set_name__` Hook**: Auto-derives Asana field name from property name
3. **`@overload` Decorators**: Provides correct type hints for class vs instance access
4. **Pydantic Compatibility**: Added to `ignored_types` per ADR-0077

### Dictionary-Style Access

CustomFieldAccessor enhanced with `__getitem__` and `__setitem__` for natural syntax:

```python
# Method calls (original API)
task.get_custom_fields().set("Priority", "High")
value = task.get_custom_fields().get("Priority")

# Dictionary syntax (ADR-0062)
task.custom_fields["Priority"] = "High"
value = task.custom_fields["Priority"]
```

Implementation:
```python
_MISSING = object()  # Sentinel for missing values

def __getitem__(self, name_or_gid: str) -> Any:
    """Get custom field value using dictionary syntax."""
    result = self.get(name_or_gid, default=_MISSING)
    if result is _MISSING:
        raise KeyError(name_or_gid)
    return result

def __setitem__(self, name_or_gid: str, value: Any) -> None:
    """Set custom field value using dictionary syntax."""
    self.set(name_or_gid, value)
```

### Usage Guidance

| Use Case | Pattern | Example |
|----------|---------|---------|
| Business entity field access | Descriptor property | `business.vertical` |
| Generic Task field access | Accessor method | `task.custom_fields_editor().get("Status")` |
| Dictionary-style access | Dictionary syntax | `task.custom_fields["Priority"]` |
| Cascade/inheritance metadata | CascadingFieldDef | See ADR-0009 |
| Raw API serialization | Accessor method | `accessor.to_api_dict()` |

## Rationale

### Why Layered Architecture?

The CustomFieldAccessor and CustomFieldDescriptor patterns serve different purposes:

**CustomFieldAccessor** (Infrastructure):
- Generic Task field access
- Name-to-GID resolution (single source of truth)
- Change tracking via `_modifications` dict
- API format conversion (`to_api_dict()`)
- Dictionary-style access for ad-hoc queries

**CustomFieldDescriptor** (Domain):
- Business entity typed properties
- Type-specific transformations (e.g., Decimal for MRR)
- Auto-derives field names from property names
- IDE autocomplete and type hints
- Delegates to accessor for actual storage/retrieval

This layering is correct as-designed. Field resolution is centralized in `CustomFieldAccessor._resolve_gid()`. Zero breaking changes required.

### Why Descriptors for Business Models?

**Problem**: 800+ lines of repetitive boilerplate across 5 models

**Solution**: Generic descriptors reduce to ~110 declarative lines (86% reduction)

Advantages:
1. **Code Maintainability**: Single definition per field instead of 7-8 lines
2. **Consistency**: All field access through uniform descriptor pattern
3. **Type Safety**: Generic type parameters provide IDE autocomplete and mypy checking
4. **Pattern Consistency**: Matches proven navigation descriptor approach (ADR-0075)
5. **Extensibility**: New field types can be added by subclassing

### Why Dictionary Syntax on Accessor?

Users expect natural dictionary access for custom fields:

1. **Intuitive**: `task.custom_fields["Priority"]` reads naturally
2. **Backward Compatible**: Existing `.get()`/`.set()` still work
3. **Change Tracking**: Automatic via existing `_modifications` dict
4. **No Duplication**: Delegates to existing methods
5. **Type Preservation**: Automatic via existing `_extract_value()` logic

### Why Not Merge Accessor and Descriptor?

Attempting to unify these patterns would create confusion because they serve different consumers:
- **Accessor**: Generic access for any Task (framework layer)
- **Descriptor**: Typed access for business entities (application layer)

Merging would violate single responsibility and reduce flexibility.

## Alternatives Considered

### Alternative 1: Keep Property Boilerplate

**Description**: Continue with explicit properties and helper methods

**Pros**:
- No changes needed
- Familiar to team

**Cons**:
- 800+ lines boilerplate
- Inconsistency risk across models
- High maintenance burden
- Adding new field requires 7-8 lines

**Why not chosen**: Does not address the maintenance problem.

### Alternative 2: Wrapper Class for Dictionary Access

**Description**: New CustomFieldDict class wrapping CustomFieldAccessor

```python
class CustomFieldDict:
    def __init__(self, accessor: CustomFieldAccessor):
        self._accessor = accessor

    def __getitem__(self, name):
        return self._accessor.get(name)
```

**Pros**:
- Separates concerns

**Cons**:
- Unnecessary duplication
- Creates new instance every access
- More complex to maintain
- No clear benefit over enhancing accessor

**Why not chosen**: Enhancement is simpler and avoids duplication.

### Alternative 3: Single Universal Descriptor

**Description**: One `CustomField(type="text")` descriptor with type parameter

**Pros**:
- Fewer classes to maintain

**Cons**:
- Less type safety
- Runtime type checking
- IDE hints less precise
- Type-specific logic becomes conditional

**Why not chosen**: Type-specific subclasses provide better IDE support and compile-time checking.

### Alternative 4: Code Generation

**Description**: Generate property code from schema at build time

**Pros**:
- No runtime overhead
- Explicit generated code

**Cons**:
- Build step complexity
- Generated code harder to debug
- Schema drift risk
- Doesn't match existing patterns

**Why not chosen**: Runtime descriptors are simpler and match existing ADR-0075 pattern.

### Alternative 5: Merge Accessor and Descriptor into Single System

**Description**: Attempt to unify the two patterns

**Pros**:
- Appears simpler on surface

**Cons**:
- Violates layering principle
- Mixes infrastructure and domain concerns
- Reduces flexibility for generic Task access
- Breaking change to existing code

**Why not chosen**: The patterns are properly layered, not competing. Analysis (ADR-0117) confirmed architecture is correct as-designed.

## Consequences

### Positive

1. **~86% code reduction**: 800+ lines to ~110 declarative lines
2. **Type safety**: IDE autocomplete and mypy checking work correctly
3. **Consistency**: Uniform descriptor pattern across all business models
4. **Dictionary syntax**: Natural access pattern for ad-hoc queries
5. **Proper layering**: Infrastructure (accessor) separated from domain (descriptors)
6. **Single source of truth**: Field resolution centralized in `CustomFieldAccessor._resolve_gid()`
7. **Change tracking**: Works through existing `CustomFieldAccessor.set()` mechanism
8. **Backward compatible**: Both old and new syntax work

### Negative

1. **Learning curve**: Developers must understand descriptor protocol
   - *Mitigation*: ADR-0075 already introduced this; team is familiar
2. **Mixed styles**: Users can write both `.get("X")` and `["X"]`
   - *Mitigation*: Document preferred style in integration guide
3. **Debugging indirection**: Stack traces go through descriptor `__get__`
   - *Mitigation*: Clear error messages, consistent pattern is learnable
4. **Not full dict interface**: Missing `__delitem__`, `keys()`, `values()`
   - *Mitigation*: Can add in future if needed

### Neutral

1. **Runtime behavior unchanged**: External API identical
2. **Performance**: Negligible overhead from descriptor protocol (< 100ns per access)
3. **Two access patterns coexist**: Properties for business models, methods/dict for generic Task

## Compliance

### How This Decision Is Enforced

1. **Code review checklist**:
   - [ ] Custom field descriptors declared WITHOUT type annotations (per ADR-0077)
   - [ ] All descriptor types in `BusinessEntity.model_config.ignored_types`
   - [ ] Field name derivation correct (abbreviations preserved)
   - [ ] Setter calls `get_custom_fields().set()` for dirty tracking
   - [ ] Dictionary access uses `__getitem__`/`__setitem__` (not wrapper)

2. **Testing requirements**:
   - [ ] Each descriptor type has unit tests for get/set
   - [ ] Field name derivation tested for edge cases
   - [ ] Dictionary syntax tested (get/set/KeyError)
   - [ ] mypy --strict passes
   - [ ] All existing business model tests pass unchanged

3. **Linting rules**:
   ```python
   # Deprecated
   @property
   def company_id(self) -> str | None:
       return self._get_text_field(self.Fields.COMPANY_ID)

   # Preferred
   company_id = TextField()
   ```

4. **Documentation**:
   - [ ] Usage guide explains when to use properties vs dictionary syntax
   - [ ] Layering architecture documented
   - [ ] Migration guide for business models
   - [ ] Examples showing all access patterns
