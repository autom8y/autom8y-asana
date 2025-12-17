# TDD: Custom Field Property Descriptors (Initiative A)

## Metadata
- **TDD ID**: TDD-PATTERNS-A
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-16
- **Last Updated**: 2025-12-16
- **PRD Reference**: [PRD-PATTERNS-A](/docs/requirements/PRD-PATTERNS-A.md)
- **Related TDDs**: TDD-HARDENING-C (Navigation Descriptors)
- **Related ADRs**: ADR-0075, ADR-0076, ADR-0077, ADR-0081, ADR-0082, ADR-0083

## Overview

This design introduces a declarative descriptor pattern for custom field properties, reducing ~800 lines of repetitive boilerplate across 5 business models to ~110 declarative lines (86% reduction). The pattern extends the proven navigation descriptor approach (ADR-0075) with type-specific custom field descriptors and automatic Fields class generation.

## Requirements Summary

From PRD-PATTERNS-A:
- **G1**: Eliminate boilerplate - 108 properties become single-line declarations
- **G2**: Type-safe access - each descriptor type returns declared return type
- **G3**: Auto-generate Fields class from descriptors
- **G4**: Integrate with CascadingFieldDef system
- **G5**: Arrow date parsing for DateField (returns `Arrow | None`)
- **G6**: Preserve external API - all property names and behaviors unchanged
- **G7**: Add `arrow>=1.3.0` dependency to pyproject.toml

## System Context

```
+------------------+     +-------------------+     +----------------------+
|  Business Model  |---->| CustomFieldDesc.  |---->| CustomFieldAccessor  |
|  (Business, Unit)|     | (TextField, etc.) |     | (get/set methods)    |
+------------------+     +-------------------+     +----------------------+
        |                        |                          |
        v                        v                          v
+------------------+     +-------------------+     +----------------------+
|  BusinessEntity  |     |  Fields Class     |     |  Dirty Tracking      |
|  (base.py)       |<----|  (auto-generated) |     |  (modifications)     |
+------------------+     +-------------------+     +----------------------+
```

**Integration Points**:
1. `CustomFieldAccessor.get()` - raw value retrieval with name resolution
2. `CustomFieldAccessor.set()` - value storage with type validation
3. `BusinessEntity.model_config` - Pydantic ignored_types configuration
4. `CascadingFieldDef` - existing cascade metadata system

## Design

### Component Architecture

```
src/autom8_asana/models/business/
    descriptors.py          # Add custom field descriptors
    base.py                 # Extend __init_subclass__ for Fields generation
    business.py             # Migrate 19 fields
    contact.py              # Migrate 19 fields
    unit.py                 # Migrate 31 fields
    offer.py                # Migrate 39 fields
    process.py              # Migrate 9 fields
```

| Component | Responsibility | Location |
|-----------|----------------|----------|
| `CustomFieldDescriptor[T]` | Base generic descriptor with field name derivation | `descriptors.py` |
| `TextField` | String field access with coercion | `descriptors.py` |
| `EnumField` | Extract name from dict value | `descriptors.py` |
| `MultiEnumField` | Extract names from list of dicts | `descriptors.py` |
| `NumberField` | Decimal conversion | `descriptors.py` |
| `IntField` | Integer conversion | `descriptors.py` |
| `PeopleField` | List of person dicts | `descriptors.py` |
| `DateField` | Arrow parsing/serialization | `descriptors.py` |
| `BusinessEntity.__init_subclass__` | Fields class auto-generation | `base.py` |

### Descriptor Class Hierarchy

```python
from typing import Generic, TypeVar, Any, overload
from decimal import Decimal

T = TypeVar("T")

class CustomFieldDescriptor(Generic[T]):
    """Base descriptor for custom field properties.

    Per ADR-0081: Single generic base with type-specific subclasses.
    Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.

    Attributes:
        field_name: Asana custom field name (derived or explicit).
        cascading: If True, field participates in cascading system.
        public_name: Property name on model (set by __set_name__).
    """

    __slots__ = ("field_name", "cascading", "public_name", "_constant_name")

    # Known abbreviations that should remain uppercase
    ABBREVIATIONS: ClassVar[frozenset[str]] = frozenset({
        "mrr", "ai", "url", "id", "num", "cal", "vca", "sms", "ad"
    })

    def __init__(
        self,
        field_name: str | None = None,
        cascading: bool = False,
    ) -> None:
        self.field_name = field_name
        self.cascading = cascading
        self.public_name: str = ""
        self._constant_name: str = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        """Called when descriptor assigned to class attribute."""
        self.public_name = name
        self._constant_name = name.upper()

        if self.field_name is None:
            self.field_name = self._derive_field_name(name)

        # Register for Fields class generation (via __init_subclass__)
        _register_custom_field(owner, self)

    def _derive_field_name(self, name: str) -> str:
        """Derive 'Title Case' field name from snake_case property."""
        parts = name.split("_")
        result = []
        for part in parts:
            if part.lower() in self.ABBREVIATIONS:
                result.append(part.upper())
            else:
                result.append(part.capitalize())
        return " ".join(result)

    @overload
    def __get__(self, obj: None, objtype: type[Any]) -> "CustomFieldDescriptor[T]": ...

    @overload
    def __get__(self, obj: Any, objtype: type[Any] | None) -> T: ...

    def __get__(
        self,
        obj: Any,
        objtype: type[Any] | None = None,
    ) -> T | "CustomFieldDescriptor[T]":
        if obj is None:
            return self
        return self._get_value(obj)

    def __set__(self, obj: Any, value: T | None) -> None:
        self._set_value(obj, value)

    def _get_value(self, obj: Any) -> T:
        """Get and transform value. Override in subclasses."""
        raise NotImplementedError

    def _set_value(self, obj: Any, value: T | None) -> None:
        """Set value. Override in subclasses for transformation."""
        obj.get_custom_fields().set(self.field_name, value)
```

### Type-Specific Descriptor Implementations

#### TextField

```python
class TextField(CustomFieldDescriptor[str | None]):
    """Descriptor for text custom fields.

    Returns str | None. Coerces non-string values to string.
    """

    def _get_value(self, obj: Any) -> str | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return str(value)
```

#### EnumField

```python
class EnumField(CustomFieldDescriptor[str | None]):
    """Descriptor for enum custom fields.

    Extracts name from dict: {"gid": "123", "name": "Value"} -> "Value"
    Handles string passthrough for already-extracted values.
    """

    def _get_value(self, obj: Any) -> str | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        if isinstance(value, dict):
            name = value.get("name")
            return str(name) if name is not None else None
        if isinstance(value, str):
            return value
        return str(value)
```

#### MultiEnumField

```python
class MultiEnumField(CustomFieldDescriptor[list[str]]):
    """Descriptor for multi-enum custom fields.

    Returns list[str], never None. Extracts names from list of dicts.
    """

    def _get_value(self, obj: Any) -> list[str]:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return []
        if not isinstance(value, list):
            return []

        result: list[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, dict):
                name = item.get("name")
                if name is not None:
                    result.append(str(name))
            elif isinstance(item, str):
                result.append(item)
        return result

    def _set_value(self, obj: Any, value: list[str] | None) -> None:
        obj.get_custom_fields().set(self.field_name, value)
```

#### NumberField

```python
class NumberField(CustomFieldDescriptor[Decimal | None]):
    """Descriptor for decimal number custom fields.

    Returns Decimal for precision. Converts to float on write for API.
    """

    def _get_value(self, obj: Any) -> Decimal | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        return Decimal(str(value))

    def _set_value(self, obj: Any, value: Decimal | None) -> None:
        api_value = float(value) if value is not None else None
        obj.get_custom_fields().set(self.field_name, api_value)
```

#### IntField

```python
class IntField(CustomFieldDescriptor[int | None]):
    """Descriptor for integer number custom fields.

    Truncates to integer on read.
    """

    def _get_value(self, obj: Any) -> int | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        return int(value)
```

#### PeopleField

```python
class PeopleField(CustomFieldDescriptor[list[dict[str, Any]]]):
    """Descriptor for people custom fields.

    Returns list of person dicts, never None.
    """

    def _get_value(self, obj: Any) -> list[dict[str, Any]]:
        value = obj.get_custom_fields().get(self.field_name)
        if isinstance(value, list):
            return value
        return []

    def _set_value(self, obj: Any, value: list[dict[str, Any]] | None) -> None:
        obj.get_custom_fields().set(self.field_name, value)
```

#### DateField

```python
import arrow
from arrow import Arrow

class DateField(CustomFieldDescriptor[Arrow | None]):
    """Descriptor for date custom fields.

    Per ADR-0083: Uses Arrow library for rich date handling.
    Parses ISO 8601 date strings. Converts Arrow to ISO string on write.

    Arrow provides:
    - Timezone-aware datetime handling
    - Human-readable formatting ("2 hours ago")
    - Flexible parsing of various date formats
    - Rich comparison and arithmetic operations
    """

    def _get_value(self, obj: Any) -> Arrow | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None or value == "":
            return None
        if isinstance(value, Arrow):
            return value
        if isinstance(value, str):
            try:
                # Arrow handles ISO 8601 dates and datetimes
                return arrow.get(value)
            except (ValueError, arrow.parser.ParserError):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Invalid date value for field %s: %r",
                    self.field_name, value
                )
                return None
        return None

    def _set_value(self, obj: Any, value: Arrow | None) -> None:
        if value is None:
            api_value = None
        else:
            # Serialize to ISO 8601 date format for Asana
            api_value = value.format("YYYY-MM-DD")
        obj.get_custom_fields().set(self.field_name, api_value)
```

### Fields Class Auto-Generation

Per ADR-0082: Use descriptor registration during `__set_name__` combined with `__init_subclass__` for Fields class creation.

```python
# Module-level registry for pending field registrations
_pending_fields: dict[int, dict[str, str]] = {}  # owner_id -> {CONSTANT: "Field Name"}

def _register_custom_field(owner: type[Any], descriptor: CustomFieldDescriptor[Any]) -> None:
    """Register a custom field descriptor for Fields class generation."""
    owner_id = id(owner)
    if owner_id not in _pending_fields:
        _pending_fields[owner_id] = {}
    _pending_fields[owner_id][descriptor._constant_name] = descriptor.field_name


class BusinessEntity(Task):
    """Base class for business model entities."""

    model_config = ConfigDict(
        ignored_types=(
            ParentRef, HolderRef,
            TextField, EnumField, MultiEnumField,
            NumberField, IntField, PeopleField, DateField,
        ),
        extra="allow",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        # Existing: Auto-discover cached reference attributes
        # (from ADR-0076)

        # NEW: Generate Fields class from registered descriptors
        owner_id = id(cls)
        if owner_id in _pending_fields:
            field_constants = _pending_fields.pop(owner_id)

            if field_constants:
                # Get or create Fields inner class
                existing_fields = getattr(cls, "Fields", None)

                if existing_fields is not None:
                    # Check if we need to add new constants
                    new_constants = {}
                    for const_name, field_name in field_constants.items():
                        if not hasattr(existing_fields, const_name):
                            new_constants[const_name] = field_name

                    if new_constants:
                        # Create subclass with new constants
                        fields_cls = type("Fields", (existing_fields,), new_constants)
                        cls.Fields = fields_cls
                else:
                    # Create new Fields class
                    fields_cls = type("Fields", (), field_constants)
                    cls.Fields = fields_cls
```

### Data Flow: Property Access

```
business.company_id
    |
    v
TextField.__get__(business, Business)
    |
    v
TextField._get_value(business)
    |
    v
business.get_custom_fields().get("Company ID")
    |
    v
CustomFieldAccessor._resolve_gid("Company ID") -> "123456"
    |
    v
CustomFieldAccessor._extract_value(field_dict) -> "ACME-001"
    |
    v
TextField coerces to str -> "ACME-001"
```

### Data Flow: Property Assignment

```
business.mrr = Decimal("5000.00")
    |
    v
NumberField.__set__(business, Decimal("5000.00"))
    |
    v
NumberField._set_value(business, Decimal("5000.00"))
    |
    v
float(Decimal("5000.00")) -> 5000.0
    |
    v
business.get_custom_fields().set("MRR", 5000.0)
    |
    v
CustomFieldAccessor._modifications["gid_123"] = 5000.0
```

### Cascading Field Integration

Per FR-CASCADE requirements, `cascading=True` marks a field for integration with the existing CascadingFieldDef system:

```python
class Business(BusinessEntity):
    # Cascading field declaration
    office_phone = TextField(cascading=True)

    class CascadingFields:
        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={"Unit", "Offer", "Process", "Contact"},
        )
```

**Design Decision**: The `cascading` parameter is metadata only - it does NOT change get/set behavior. Cascade propagation remains in SaveSession's `_apply_cascade()` method, which reads from `CascadingFields.all()`.

The `cascading=True` flag serves two purposes:
1. **Documentation**: Indicates to developers that this field participates in cascading
2. **Future automation**: Enables potential future auto-generation of CascadingFieldDef entries

### Pydantic Compatibility

Per ADR-0077:
1. All descriptor types added to `ignored_types` tuple
2. Descriptors declared WITHOUT type annotations
3. `extra="allow"` permits descriptor `__set__` to be called

```python
model_config = ConfigDict(
    ignored_types=(
        ParentRef, HolderRef,  # Existing (navigation)
        TextField, EnumField, MultiEnumField,  # NEW
        NumberField, IntField, PeopleField, DateField,  # NEW
    ),
    extra="allow",
)
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Descriptor pattern | Generic base + type subclasses | Consistent with ADR-0075 navigation pattern | ADR-0081 |
| Fields auto-generation | `__set_name__` + `__init_subclass__` | Simpler than metaclass, works with Pydantic | ADR-0082 |
| Date handling | Arrow library | User requirement; rich API with timezone, humanize, flexible parsing | ADR-0083 |
| Cascading parameter | Metadata only | Preserves separation of concerns; cascade logic stays in SaveSession | - |
| Type coercion | In descriptors | Consistent with current helper method behavior | - |

## Complexity Assessment

**Level**: Module

**Justification**:
- Single module addition (`descriptors.py` extension)
- Clear API surface (7 descriptor types + base)
- No external service dependencies
- No new async patterns
- Build on proven navigation descriptor pattern

**Escalation triggers not present**:
- No multiple consumers beyond business models
- No external API contracts
- No independent deployment needed

## Implementation Plan

### Phase 1: Descriptor Infrastructure (Est: 2 hours)

| Deliverable | Details |
|-------------|---------|
| Add custom field descriptors | `TextField`, `EnumField`, `MultiEnumField`, `NumberField`, `IntField`, `PeopleField`, `DateField` |
| Extend BusinessEntity | Add descriptor types to `ignored_types`, implement Fields generation |
| Unit tests | Descriptor behavior, field name derivation, Fields generation |

### Phase 2: Model Migration (Est: 4 hours)

| Model | Fields | Estimate |
|-------|--------|----------|
| Business | 19 | 30 min |
| Contact | 19 | 30 min |
| Process | 9 | 20 min |
| Unit | 31 | 45 min |
| Offer | 39 | 45 min |

Each migration:
1. Replace `class Fields:` with descriptor declarations
2. Remove `_get_*_field` helper methods
3. Remove property/setter pairs
4. Verify all existing tests pass
5. Verify mypy clean

### Phase 3: Cleanup (Est: 1 hour)

| Deliverable | Details |
|-------------|---------|
| Remove helper methods | `_get_text_field`, `_get_enum_field`, etc. |
| Remove explicit Fields classes | Now auto-generated |
| Documentation | Update docstrings, add migration notes |

### Migration Strategy

**Non-Breaking Approach**: Each model migrated independently. Tests run after each model migration to catch regressions immediately.

**Backward Compatibility**:
- All property names preserved (`business.company_id` still works)
- All return types preserved (`Decimal`, `int`, `list[str]`, etc.)
- All setter signatures preserved
- `Fields.CONSTANT` access preserved (auto-generated)

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Type hint regression | Medium | Low | Extensive mypy --strict testing; @overload coverage |
| Fields generation edge cases | Low | Medium | Explicit `field_name` override available; existing Fields preserved |
| Abbreviation dictionary incomplete | Low | Low | Easy to extend; explicit override escape hatch |
| IDE autocomplete for Fields | Medium | Medium | Type stubs if needed; generated class inherits from existing |
| Pydantic compatibility issues | High | Low | ADR-0077 pattern proven with navigation descriptors |

## Observability

### Logging

```python
logger = logging.getLogger(__name__)

# Warning on invalid date parsing
logger.warning("Invalid date value for field %s: %r", field_name, value)

# Debug on field registration (optional)
logger.debug("Registered custom field %s.%s -> %r", owner.__name__, name, field_name)
```

### Metrics (Future)

- Custom field access latency (if performance concerns arise)
- Field type distribution across models

## Testing Strategy

### Unit Tests

| Category | Tests |
|----------|-------|
| TextField | String return, None handling, coercion |
| EnumField | Dict extraction, string passthrough, None |
| MultiEnumField | List extraction, empty list, None items |
| NumberField | Decimal conversion, None, zero |
| IntField | Integer truncation, None, zero |
| PeopleField | List return, empty list |
| DateField | Arrow parsing, None, invalid string, ISO serialization, timezone handling |
| Field name derivation | Standard names, abbreviations, explicit override |
| Fields generation | Constants created, values correct, inheritance |

### Integration Tests

| Category | Tests |
|----------|-------|
| Business model | All 19 fields accessible via descriptors |
| Unit model | All 31 fields including Number/Int/MultiEnum |
| Dirty tracking | Changes tracked via descriptors |
| SaveSession | Fields save correctly through descriptors |

### Regression Tests

| Category | Tests |
|----------|-------|
| Existing business entity tests | All pass unchanged |
| Existing custom field tests | All pass unchanged |
| Type safety | mypy --strict clean |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should DateField support timezone-aware datetime? | Architect | TBD | Deferred - date-only for now (ADR-0083) |
| Should we validate enum values against allowed options? | Architect | TBD | Deferred - CustomFieldAccessor handles validation |
| IDE stubs for Fields class needed? | Engineer | TBD | Monitor IDE support; add if needed |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Architect | Initial draft |

## Quality Gate Checklist

- [x] Traces to approved PRD (PRD-PATTERNS-A)
- [x] All significant decisions have ADRs (ADR-0081, ADR-0082, ADR-0083)
- [x] Component responsibilities are clear
- [x] Interfaces are defined
- [x] Complexity level is justified (Module)
- [x] Risks identified with mitigations
- [x] Implementation plan is actionable
