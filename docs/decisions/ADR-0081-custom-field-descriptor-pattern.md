# ADR-0081: Custom Field Descriptor Pattern

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-PATTERNS-A, TDD-PATTERNS-A, ADR-0075 (Navigation Descriptors), ADR-0077 (Pydantic Compatibility)

## Context

The SDK's business layer contains ~800 lines of repetitive custom field property boilerplate across 5 models (Business, Contact, Unit, Offer, Process). Each of the 108 custom fields requires:

1. A constant in the `Fields` inner class
2. A private helper method (`_get_text_field`, `_get_enum_field`, etc.)
3. A `@property` getter
4. A `@property.setter`

Example of current pattern (7-8 lines per field):

```python
class Business(BusinessEntity):
    class Fields:
        COMPANY_ID = "Company ID"

    def _get_text_field(self, field_name: str) -> str | None:
        value = self.get_custom_fields().get(field_name)
        if value is None or isinstance(value, str):
            return value
        return str(value)

    @property
    def company_id(self) -> str | None:
        return self._get_text_field(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)
```

### Forces at Play

1. **Code Maintainability**: 800+ lines of near-identical boilerplate increases maintenance burden
2. **Consistency**: Helper methods duplicated in each model create inconsistency risk
3. **Type Safety**: Current pattern provides correct types but through manual repetition
4. **Proven Pattern**: Navigation descriptors (ADR-0075) successfully reduced ~150 lines with the same approach
5. **Pydantic Compatibility**: Must work with existing Pydantic v2 model infrastructure (ADR-0077)
6. **IDE Support**: Developers expect autocomplete for field names and types

## Decision

Implement custom field access using generic descriptors, following the same pattern established for navigation properties in ADR-0075.

### Pattern

```python
# Before: 7-8 lines per field
@property
def company_id(self) -> str | None:
    return self._get_text_field(self.Fields.COMPANY_ID)

@company_id.setter
def company_id(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.COMPANY_ID, value)


# After: 1 line per field
company_id = TextField()
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

### Key Design Elements

1. **Generic Type Parameter**: `CustomFieldDescriptor[T]` carries return type for IDE inference
2. **`__set_name__` Hook**: Auto-derives Asana field name from property name
3. **`@overload` Decorators**: Provides correct type hints for class vs instance access
4. **Pydantic Compatibility**: Added to `ignored_types` per ADR-0077

## Rationale

### Why Descriptors?

| Approach | Pros | Cons |
|----------|------|------|
| Current (properties) | Explicit, familiar | 800+ lines boilerplate, duplication |
| Code generation | No runtime overhead | Build step, harder to debug |
| Metaclass magic | Centralized logic | Complex, hard to understand |
| **Descriptors** | Declarative, Pythonic, proven | Learning curve (mitigated by ADR-0075 precedent) |

Descriptors are the natural Python mechanism for customizing attribute access. ADR-0075 proved this approach works in our codebase with Pydantic v2.

### Why Generic Base Class?

A single `CustomFieldDescriptor[T]` base with type-specific subclasses provides:

1. **Shared Logic**: Field name derivation, registration, `__get__`/`__set__` protocol in one place
2. **Type Safety**: Generic type parameter `T` flows through to IDE and mypy
3. **Extensibility**: New field types can be added by subclassing
4. **Consistency**: Mirrors `ParentRef[T]` / `HolderRef[T]` pattern from ADR-0075

### Why Type-Specific Subclasses?

Each field type needs specific transformation logic:

| Type | Transform |
|------|-----------|
| TextField | Coerce to string |
| EnumField | Extract `name` from `{"gid": "...", "name": "..."}` dict |
| NumberField | Convert to `Decimal` for precision |
| DateField | Parse ISO string to `date` object |

Putting all logic in the base class would require type dispatching; subclasses are cleaner.

## Alternatives Considered

### Alternative 1: Keep Current Pattern

- **Description**: Continue with explicit properties and helper methods
- **Pros**: No changes needed, familiar to team
- **Cons**: 800+ lines boilerplate, inconsistency risk, high maintenance burden
- **Why not chosen**: Does not address the problem

### Alternative 2: Single Universal Descriptor

- **Description**: One `CustomField(type="text")` descriptor with type parameter
- **Pros**: Fewer classes to maintain
- **Cons**: Less type safety, runtime type checking, IDE hints less precise
- **Why not chosen**: Type-specific subclasses provide better IDE support and compile-time type checking

### Alternative 3: Code Generation

- **Description**: Generate property code from schema at build time
- **Pros**: No runtime overhead, explicit generated code
- **Cons**: Build step complexity, generated code harder to debug, schema drift risk
- **Why not chosen**: Runtime descriptors are simpler and match existing ADR-0075 pattern

### Alternative 4: `__getattr__` / `__setattr__` Override

- **Description**: Intercept all attribute access in base class
- **Pros**: Centralized logic
- **Cons**: Conflicts with Pydantic's `__getattr__`, performance overhead, less explicit
- **Why not chosen**: Pydantic compatibility issues, less declarative

## Consequences

### Positive

1. **~86% code reduction**: 800+ lines to ~110 declarative lines
2. **Consistency**: All field access through uniform descriptor pattern
3. **Type Safety**: Generic type parameters provide IDE autocomplete and mypy checking
4. **Maintainability**: Adding new field requires one line, not 7-8
5. **Pattern Consistency**: Matches proven navigation descriptor approach (ADR-0075)

### Negative

1. **Learning curve**: Developers must understand descriptor protocol
   - *Mitigation*: ADR-0075 already introduced this; team is familiar
2. **Debugging indirection**: Stack traces go through descriptor `__get__`
   - *Mitigation*: Clear error messages, consistent pattern is learnable
3. **Extra classes**: 7 new descriptor classes to maintain
   - *Mitigation*: Each class is <20 lines; total is less than replaced boilerplate

### Neutral

1. **Runtime behavior unchanged**: External API identical (same property names, types)
2. **Performance**: Negligible overhead from descriptor protocol (< 100ns per access)
3. **Dirty tracking**: Works through existing `CustomFieldAccessor.set()` mechanism

## Compliance

### Code Review Checklist

- [ ] Custom field descriptors declared WITHOUT type annotations (per ADR-0077)
- [ ] All descriptor types in `BusinessEntity.model_config.ignored_types`
- [ ] Field name derivation correct (abbreviations preserved)
- [ ] Setter calls `get_custom_fields().set()` for dirty tracking

### Testing Requirements

- [ ] Each descriptor type has unit tests for get/set
- [ ] Field name derivation tested for edge cases
- [ ] mypy --strict passes
- [ ] All existing business model tests pass unchanged

### Migration Verification

- [ ] External API unchanged (property names, return types)
- [ ] `Fields.CONSTANT` access still works
- [ ] Dirty tracking functions correctly
