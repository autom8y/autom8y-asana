# ADR-0082: Fields Class Auto-Generation Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-PATTERNS-A, TDD-PATTERNS-A, ADR-0081 (Custom Field Descriptor Pattern), ADR-0076 (Auto-Invalidation)

## Context

Each business model contains an inner `Fields` class with constants mapping property names to Asana custom field names:

```python
class Business(BusinessEntity):
    class Fields:
        COMPANY_ID = "Company ID"
        FACEBOOK_PAGE_ID = "Facebook Page ID"
        VERTICAL = "Vertical"
        # ... 16 more
```

These constants serve two purposes:
1. **IDE discoverability**: `business.Fields.COMPANY_ID` for autocomplete
2. **Indirection layer**: Property implementations reference constants, not literal strings

With the custom field descriptor pattern (ADR-0081), field names are already captured in descriptors:

```python
company_id = TextField()  # Derives "Company ID" from property name
```

We need a mechanism to auto-generate the `Fields` class from descriptor declarations to avoid maintaining duplicate information.

### Forces at Play

1. **DRY Principle**: Field names should not be declared twice (descriptor + Fields constant)
2. **IDE Support**: `Model.Fields.CONSTANT` pattern is useful for IDE autocomplete
3. **Pydantic Compatibility**: Must work with Pydantic's metaclass and `__init_subclass__`
4. **Existing Pattern**: ADR-0076 already uses `__init_subclass__` for `_CACHED_REF_ATTRS` discovery
5. **Explicit Override**: Some field names need explicit specification (e.g., "MRR" not "M R R")
6. **Backward Compatibility**: Existing explicit `Fields` classes should continue to work

## Decision

Use a two-phase registration approach:
1. **Phase 1 (`__set_name__`)**: Each descriptor registers its field constant when assigned to a class attribute
2. **Phase 2 (`__init_subclass__`)**: BusinessEntity collects registrations and generates/extends the Fields class

### Implementation Pattern

```python
# Module-level registry for pending field registrations
# Uses class id() as key since class object may not be fully constructed during __set_name__
_pending_fields: dict[int, dict[str, str]] = {}  # owner_id -> {CONSTANT_NAME: "Field Name"}


def _register_custom_field(owner: type[Any], descriptor: CustomFieldDescriptor[Any]) -> None:
    """Called during descriptor.__set_name__() to register field for Fields generation."""
    owner_id = id(owner)
    if owner_id not in _pending_fields:
        _pending_fields[owner_id] = {}
    _pending_fields[owner_id][descriptor._constant_name] = descriptor.field_name


class BusinessEntity(Task):
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        # Existing: _CACHED_REF_ATTRS discovery (ADR-0076)

        # NEW: Fields class generation from registered descriptors
        owner_id = id(cls)
        if owner_id in _pending_fields:
            field_constants = _pending_fields.pop(owner_id)

            if field_constants:
                existing_fields = getattr(cls, "Fields", None)

                if existing_fields is not None:
                    # Extend existing Fields class (preserves manual constants)
                    new_constants = {
                        k: v for k, v in field_constants.items()
                        if not hasattr(existing_fields, k)
                    }
                    if new_constants:
                        fields_cls = type("Fields", (existing_fields,), new_constants)
                        cls.Fields = fields_cls
                else:
                    # Create new Fields class
                    fields_cls = type("Fields", (), field_constants)
                    cls.Fields = fields_cls
```

### Field Name Derivation

```python
class CustomFieldDescriptor(Generic[T]):
    ABBREVIATIONS: ClassVar[frozenset[str]] = frozenset({
        "mrr", "ai", "url", "id", "num", "cal", "vca", "sms", "ad"
    })

    def _derive_field_name(self, name: str) -> str:
        """Derive 'Title Case' field name from snake_case property.

        Examples:
            company_id -> "Company ID"
            mrr -> "MRR"
            num_ai_copies -> "Num AI Copies"
        """
        parts = name.split("_")
        result = []
        for part in parts:
            if part.lower() in self.ABBREVIATIONS:
                result.append(part.upper())
            else:
                result.append(part.capitalize())
        return " ".join(result)
```

### Explicit Override

For non-standard field names, use explicit `field_name` parameter:

```python
mrr = NumberField(field_name="MRR")           # Not "M R R"
google_cal_id = TextField(field_name="Google Cal ID")  # Preserves "Cal"
vca_status = EnumField(field_name="VCA Status")        # Preserves "VCA"
```

## Rationale

### Why `__set_name__` + `__init_subclass__`?

| Approach | Pros | Cons |
|----------|------|------|
| Metaclass | Full control over class creation | Conflicts with Pydantic's metaclass |
| `__set_name__` only | Simple, one-phase | Class not fully constructed yet |
| **`__set_name__` + `__init_subclass__`** | Two-phase, works with Pydantic | Slight complexity |
| Post-class decorator | Explicit | Extra decoration step required |

The two-phase approach:
1. `__set_name__` fires for each descriptor as class is being created
2. `__init_subclass__` fires after class creation is complete, with access to all registrations

This matches the pattern already established in ADR-0076 for `_CACHED_REF_ATTRS`.

### Why Module-Level Registry?

During `__set_name__`, the class is still being constructed. We cannot reliably attach state to the class yet. A module-level registry keyed by `id(owner)` allows collecting registrations that are then consumed during `__init_subclass__`.

The registry is cleaned up (via `.pop()`) after processing, preventing memory leaks for classes that are garbage collected.

### Why Extend Existing Fields Class?

Some models may have manually-defined `Fields` classes with additional constants (e.g., for fields not yet converted to descriptors). Extending via inheritance preserves these while adding new descriptor-derived constants.

```python
class Unit(BusinessEntity):
    class Fields:
        LEGACY_FIELD = "Legacy Field"  # Preserved

    mrr = NumberField()  # Adds MRR constant to Fields
```

Result: `Unit.Fields.LEGACY_FIELD` and `Unit.Fields.MRR` both work.

## Alternatives Considered

### Alternative 1: Custom Metaclass

- **Description**: Create `BusinessEntityMeta` that generates Fields during class creation
- **Pros**: Full control, single-phase
- **Cons**: Conflicts with Pydantic's `ModelMetaclass`, complex inheritance
- **Why not chosen**: Pydantic v2 already uses its own metaclass; combining is fragile

### Alternative 2: Class Decorator

- **Description**: `@with_fields` decorator that introspects descriptors after class creation
- **Pros**: Explicit, no metaclass conflicts
- **Cons**: Extra decoration required on every model, easy to forget
- **Why not chosen**: Implicit via `__init_subclass__` is cleaner, consistent with ADR-0076

### Alternative 3: Explicit Fields Only

- **Description**: Require manual `Fields` class alongside descriptors
- **Pros**: Simple, explicit
- **Cons**: Duplicates information, defeats purpose of descriptors
- **Why not chosen**: Violates DRY principle

### Alternative 4: No Fields Class

- **Description**: Remove `Fields` pattern entirely; use property names directly
- **Pros**: Simplest approach
- **Cons**: Loses IDE discoverability for field constants, breaking change for code using `Model.Fields.X`
- **Why not chosen**: Backward compatibility requirement

## Consequences

### Positive

1. **DRY**: Field names declared once in descriptors
2. **Backward Compatible**: `Model.Fields.CONSTANT` continues to work
3. **IDE Support**: Auto-generated Fields class provides autocomplete
4. **Extensible**: Manual Fields constants preserved via inheritance
5. **Consistent Pattern**: Uses same `__init_subclass__` hook as ADR-0076

### Negative

1. **Implicit Generation**: Fields class created "magically" at class definition time
   - *Mitigation*: Well-documented, consistent with existing `_CACHED_REF_ATTRS` pattern
2. **Module-level State**: Registry is module-level
   - *Mitigation*: Cleaned up immediately after use; no persistent state
3. **Type Stubs May Be Needed**: IDE may not infer generated Fields class members
   - *Mitigation*: Monitor; add `.pyi` stubs if needed

### Neutral

1. **Runtime Cost**: Negligible - one-time at class definition
2. **Inheritance**: Works correctly - each subclass gets its own Fields class
3. **Testing**: Fields class existence/contents easily tested

## Compliance

### Code Review Checklist

- [ ] Descriptors without explicit `field_name` derive names correctly
- [ ] Abbreviations (MRR, VCA, URL, etc.) handled correctly
- [ ] Explicit `field_name` overrides used where needed
- [ ] Existing manual Fields constants preserved
- [ ] `Model.Fields.CONSTANT` access works for all fields

### Testing Requirements

- [ ] Field name derivation unit tests (standard, abbreviations, explicit override)
- [ ] Fields class generation verified for each model
- [ ] Inheritance case tested (manual + auto-generated constants)
- [ ] Cleanup verified (no stale registry entries)

### Migration Checklist

For each model migration:
- [ ] Remove explicit `Fields` class (or keep if has additional constants)
- [ ] Verify all `Model.Fields.CONSTANT` references still work
- [ ] Verify field names match previous constant values exactly
