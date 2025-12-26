# TDD-06: Custom Fields Architecture

> Consolidated TDD for custom field resolution, tracking, descriptors, and remediation.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: TDD-0020, TDD-0023, TDD-CUSTOM-FIELD-REMEDIATION
- **Related ADRs**: ADR-0006 (Resolution), ADR-0007 (Accessors/Descriptors), ADR-0008 (API Format/Tracking), ADR-0009 (Cascading)

---

## Overview

Custom fields are the backbone of business entity typing in the SDK. This consolidated TDD covers the complete custom field architecture:

1. **Resolution Strategy** - How field names map to GIDs dynamically
2. **Accessor Pattern** - Infrastructure layer for field access and change tracking
3. **Descriptor Pattern** - Domain layer for typed business entity properties
4. **Change Tracking** - Three-system coordination for detecting and persisting modifications
5. **Remediation Patterns** - Correcting field type mismatches across models

### Design Philosophy

The architecture implements a **layered approach**:

```
Domain Layer (Consumer-Facing)
  CustomFieldDescriptor subclasses
    - TextField, EnumField, NumberField, DateField, etc.
    - Declarative: company_id = TextField()
    - Type transformation and IDE support
    - Auto-generated Fields class

  delegates internally to

Infrastructure Layer (Implementation)
  CustomFieldAccessor
    - obj.get_custom_fields().get/set()
    - obj.custom_fields["field_name"] (dictionary syntax)
    - Name-to-GID resolution (single source of truth)
    - Change tracking (_modifications dict)
    - API serialization (to_api_dict())
```

---

## Resolution Strategy

### Problem

Asana custom fields are identified by GIDs (globally unique identifiers), but users refer to them by names. GIDs vary across environments (production vs staging), making hardcoded GIDs non-portable.

### Solution: Dynamic Name-Based Resolution

**Use dynamic name-based resolution with session-level caching.** Field names are normalized to lowercase alphanumeric for case-insensitive matching. The name-to-GID index is built from task data already loaded by the API, requiring zero extra API calls.

#### Resolution Algorithm

```
1. Parse source prefix from schema:
   - "cf:Name" -> Resolve by name
   - "gid:123" -> Explicit GID (testing/override)
   - attribute path -> Not a custom field

2. For "cf:" sources:
   a. Normalize field name: lowercase, remove non-alphanumeric
   b. Look up in session-cached index
   c. Return GID if found, None if not

3. Use GID to find value in task.custom_fields
```

#### Name Normalization

Asana custom field names vary in format:
- "Weekly Ad Spend" (Title Case with spaces)
- "MRR" (ALL CAPS)
- "monthly-recurring-revenue" (hyphenated)

Normalization to lowercase alphanumeric enables matching regardless of naming convention.

#### Session-Cached Index

Built once per extraction session from the first task's `custom_fields`:
- O(1) lookups after initial build
- Thread-safe concurrent access (RLock protected)
- No repeated iteration over custom_fields per task
- Predictable performance characteristics

### Implementation

```python
# Self-documenting schema definition
ColumnDef(name="mrr", source="cf:MRR")           # Resolve by name
ColumnDef(name="mrr", source="gid:123456")       # Explicit GID
ColumnDef(name="created", source="created_at")   # Attribute path
```

---

## Descriptor Pattern

### Problem

108 business-specific custom fields across 5 models (Business, Contact, Unit, Offer, Process) required ~800 lines of repetitive boilerplate for properties and setters.

### Solution: Generic Descriptors

Declarative descriptors reduce 800+ lines to ~110 declarative lines (86% reduction).

```python
# Before: 7-8 lines per field x 108 fields = 800+ lines
class Business(Task):
    class Fields:
        COMPANY_ID = "Company ID"

    @property
    def company_id(self) -> str | None:
        return self.get_custom_fields().get(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)


# After: 1 line per field x 108 fields = ~110 lines
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
    +-- DateField          -> Arrow | None
```

### Base Descriptor Implementation

```python
class CustomFieldDescriptor(Generic[T]):
    """Base descriptor for custom field properties.

    Per ADR-0081: Single generic base with type-specific subclasses.
    Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.
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

        # Register for Fields class generation
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
```

### Type-Specific Descriptors

#### TextField

```python
class TextField(CustomFieldDescriptor[str | None]):
    """Descriptor for text custom fields. Returns str | None."""

    def _get_value(self, obj: Any) -> str | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        return str(value) if not isinstance(value, str) else value
```

#### EnumField

```python
class EnumField(CustomFieldDescriptor[str | None]):
    """Descriptor for enum custom fields.

    Extracts name from dict: {"gid": "123", "name": "Value"} -> "Value"
    """

    def _get_value(self, obj: Any) -> str | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        if isinstance(value, dict):
            name = value.get("name")
            return str(name) if name is not None else None
        return str(value) if isinstance(value, str) else str(value)
```

#### MultiEnumField

```python
class MultiEnumField(CustomFieldDescriptor[list[str]]):
    """Descriptor for multi-enum custom fields. Returns list[str], never None."""

    def _get_value(self, obj: Any) -> list[str]:
        value = obj.get_custom_fields().get(self.field_name)
        if not isinstance(value, list):
            return []

        result: list[str] = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("name")
                if name is not None:
                    result.append(str(name))
            elif isinstance(item, str):
                result.append(item)
        return result
```

#### NumberField

```python
class NumberField(CustomFieldDescriptor[Decimal | None]):
    """Descriptor for decimal number custom fields."""

    def _get_value(self, obj: Any) -> Decimal | None:
        value = obj.get_custom_fields().get(self.field_name)
        return Decimal(str(value)) if value is not None else None

    def _set_value(self, obj: Any, value: Decimal | None) -> None:
        api_value = float(value) if value is not None else None
        obj.get_custom_fields().set(self.field_name, api_value)
```

#### DateField

```python
class DateField(CustomFieldDescriptor[Arrow | None]):
    """Descriptor for date custom fields.

    Per ADR-0083: Uses Arrow library for rich date handling.
    Parses ISO 8601 date strings. Converts Arrow to ISO string on write.
    """

    def _get_value(self, obj: Any) -> Arrow | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None or value == "":
            return None
        if isinstance(value, Arrow):
            return value
        if isinstance(value, str):
            try:
                return arrow.get(value)
            except (ValueError, arrow.parser.ParserError):
                logger.warning("Invalid date value for field %s: %r", self.field_name, value)
                return None
        return None

    def _set_value(self, obj: Any, value: Arrow | None) -> None:
        api_value = value.format("YYYY-MM-DD") if value is not None else None
        obj.get_custom_fields().set(self.field_name, api_value)
```

### Fields Class Auto-Generation

The Fields class is auto-generated from descriptor registrations during `__set_name__` and `__init_subclass__`:

```python
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

        owner_id = id(cls)
        if owner_id in _pending_fields:
            field_constants = _pending_fields.pop(owner_id)

            if field_constants:
                fields_cls = type("Fields", (), field_constants)
                cls.Fields = fields_cls
```

This enables `Business.Fields.COMPANY_ID` to return `"Company ID"` without explicit declaration.

---

## Change Tracking

### The Three-System Problem

Three independent systems track custom field changes:

| System | Mechanism | Location | Purpose |
|--------|-----------|----------|---------|
| **System 1** | ChangeTracker snapshot comparison | `persistence/tracker.py` | Detect entity-level changes |
| **System 2** | CustomFieldAccessor `_modifications` dict | `models/custom_field_accessor.py` | Track accessor-based changes |
| **System 3** | Task `_original_custom_fields` deepcopy | `models/task.py` | Detect direct list mutations |

### Solution: Unified Reset Coordination

**SaveSession coordinates reset across all three systems after successful commit.**

#### Target Architecture

```
                    +------------------+
                    |   SaveSession    |
                    +--------+---------+
                             |
              commit_async() |
                             |
         FOR EACH SUCCESSFUL ENTITY:
                             |
                             v
                    +------------------+
                    |  ChangeTracker   |  <-- System 1
                    +--------+---------+
                             |
                 mark_clean()| (existing)
                             |
                             v
         _reset_custom_field_tracking()  <-- NEW HOOK
                             |
                             v
                    +------------------+
                    |      Task        |
                    +--------+---------+
                             |
         +-------------------+-------------------+
         |                                       |
         v                                       v
+------------------+                  +------------------+
| _custom_fields_  |                  | _original_       |
|    accessor      | <-- System 2     | custom_fields    | <-- System 3
| (_modifications) |                  | (deepcopy)       |
+------------------+                  +------------------+
         |                                       |
    CLEARED via                           UPDATED via
 clear_changes()                    _update_snapshot()
```

#### SaveSession Reset Hook

```python
async def commit_async(self) -> SaveResult:
    """Execute all pending changes (async)."""
    crud_result, action_results = await self._pipeline.execute_with_actions(...)

    # Reset state for successful entities only
    for entity in crud_result.succeeded:
        self._tracker.mark_clean(entity)  # System 1 reset
        self._reset_custom_field_tracking(entity)  # Systems 2 & 3 reset

    # ... rest of method ...


def _reset_custom_field_tracking(self, entity: AsanaResource) -> None:
    """Reset custom field tracking state after successful commit."""
    if hasattr(entity, 'reset_custom_field_tracking'):
        entity.reset_custom_field_tracking()
```

#### Task Reset Method

```python
def reset_custom_field_tracking(self) -> None:
    """Reset custom field tracking state after successful commit.

    Per ADR-0074: Called by SaveSession after successful entity commit.
    Clears accessor modifications (System 2) and updates snapshot (System 3).
    """
    # System 2: Clear accessor modifications
    if self._custom_fields_accessor is not None:
        self._custom_fields_accessor.clear_changes()

    # System 3: Update snapshot to current state
    self._update_custom_fields_snapshot()


def _update_custom_fields_snapshot(self) -> None:
    """Update the custom fields snapshot to current state."""
    import copy
    if self.custom_fields is not None:
        self._original_custom_fields = copy.deepcopy(self.custom_fields)
    else:
        self._original_custom_fields = None
```

### API Format Conversion

Asana API expects a different format than the internal representation:

```python
# Internal (to_list() produces):
[{"gid": "123456", "value": "High"}, {"gid": "789012", "value": 1000}]

# API requires:
{"custom_fields": {"123456": "High", "789012": 1000}}
```

The `to_api_dict()` method produces the correct format:

```python
def to_api_dict(self) -> dict[str, Any]:
    """Convert modifications to API-compatible dict format."""
    result: dict[str, Any] = {}
    for gid, value in self._modifications.items():
        result[gid] = self._normalize_value_for_api(value)
    return result


def _normalize_value_for_api(self, value: Any) -> Any:
    """Normalize a value for API submission.

    Handles type-specific formatting:
    - Enum: Extract GID from {"gid": "...", "name": "..."} dict
    - Multi-enum/People: Extract GIDs from list of dicts
    - Text/number/date: Return as-is
    """
    if value is None:
        return None

    # Enum values: if dict with 'gid', extract the GID
    if isinstance(value, dict) and "gid" in value:
        return value["gid"]

    # Multi-enum/People: if list of dicts with 'gid', extract GIDs
    if isinstance(value, list):
        if all(isinstance(item, dict) and "gid" in item for item in value):
            return [item["gid"] for item in value]
        return value

    return value
```

### Partial Failure Handling

Reset occurs only for successful entities:

```python
for entity in crud_result.succeeded:  # Only iterate succeeded
    self._tracker.mark_clean(entity)
    self._reset_custom_field_tracking(entity)

# Failed entities retain their state for retry
# crud_result.failed entities are NOT reset
```

---

## Remediation Patterns

### Overview

Field type mismatches occur when SDK model definitions don't match actual Asana custom field types. This section covers patterns for correcting these mismatches.

### Common Type Changes

| Original Type | Target Type | Example Fields |
|---------------|-------------|----------------|
| `EnumField` | `MultiEnumField` | specialty, gender |
| `NumberField` | `EnumField` | discount |
| `TextField` | `IntField` | zip_codes_radius, template_id |
| `TextField` | `MultiEnumField` | form_questions, disclaimers |

### Unit Model Remediation Example

```python
# BEFORE                          # AFTER
specialty = EnumField()           specialty = MultiEnumField()
gender = EnumField()              gender = MultiEnumField()
discount = NumberField()          discount = EnumField()
zip_codes_radius = TextField()    zip_codes_radius = IntField()
filter_out_x = TextField()        filter_out_x = EnumField(field_name="Filter Out x%")
form_questions = TextField()      form_questions = MultiEnumField()
disabled_questions = TextField()  disabled_questions = MultiEnumField()
disclaimers = TextField()         disclaimers = MultiEnumField()
```

### Return Type Changes

| Field | Before | After |
|-------|--------|-------|
| `specialty` | `str \| None` | `list[str]` |
| `gender` | `str \| None` | `list[str]` |
| `discount` | `Decimal \| None` | `str \| None` |
| `zip_codes_radius` | `str \| None` | `int \| None` |

### Backward Compatibility: Deprecated Aliases

For breaking changes, provide deprecated aliases:

```python
@property
def monday_hours(self) -> list[str]:
    """Deprecated: Use .monday instead."""
    import warnings
    warnings.warn(
        "monday_hours is deprecated, use monday instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return self.monday
```

### Legacy Model Remediation (Non-Descriptor)

For models not using descriptors, update helper method calls:

```python
# BEFORE
@property
def specialty(self) -> str | None:
    return self._get_enum_field(self.Fields.SPECIALTY)

# AFTER
@property
def specialty(self) -> list[str]:
    return self._get_multi_enum_field(self.Fields.SPECIALTY)


def _get_multi_enum_field(self, field_name: str) -> list[str]:
    """Get multi-enum custom field value as list of strings."""
    value: Any = self.get_custom_fields().get(field_name)
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, dict):
            name = item.get("name")
            if name is not None:
                result.append(str(name))
        elif isinstance(item, str):
            result.append(item)
    return result
```

---

## Testing Strategy

### Unit Tests

| Category | Tests |
|----------|-------|
| **Resolution** | Name normalization, session caching, GID lookup |
| **TextField** | String return, None handling, coercion |
| **EnumField** | Dict extraction, string passthrough, None |
| **MultiEnumField** | List extraction, empty list, None items |
| **NumberField** | Decimal conversion, None, zero |
| **IntField** | Integer truncation, None, zero |
| **DateField** | Arrow parsing, None, invalid string, ISO serialization |
| **Field name derivation** | Standard names, abbreviations, explicit override |
| **Fields generation** | Constants created, values correct, inheritance |
| **Reset behavior** | Accessor cleared, snapshot updated, idempotent |

### Integration Tests

| Category | Tests |
|----------|-------|
| **No duplicate API calls** | Re-commit after success detects no changes |
| **Cross-session clean state** | Entity tracked in new session has no stale modifications |
| **Partial failure preserves state** | Failed entities retain modifications for retry |
| **Business layer unaffected** | Property setters use accessor internally |
| **Dirty tracking** | Changes tracked via descriptors |
| **SaveSession** | Fields save correctly through descriptors |

### Type Safety Tests

```python
def test_unit_specialty_returns_list():
    unit = Unit.model_validate(task_data)
    assert isinstance(unit.specialty, list)


def test_hours_monday_empty_when_unset():
    hours = Hours.model_validate(task_data_no_fields)
    assert hours.monday == []


def test_hours_monday_hours_deprecated():
    hours = Hours.model_validate(task_data)
    with pytest.warns(DeprecationWarning):
        _ = hours.monday_hours
```

---

## Cross-References

### Related ADRs

| ADR | Topic | Key Decisions |
|-----|-------|---------------|
| ADR-0006 | Custom Field Resolution | Dynamic name-based resolution, session caching |
| ADR-0007 | Accessors and Descriptors | Layered architecture, descriptor hierarchy |
| ADR-0008 | API Format and Change Tracking | `to_api_dict()`, snapshot detection, unified reset |
| ADR-0009 | Cascading Custom Fields | Denormalized storage, explicit cascade operations |

### Related TDDs

| TDD | Topic |
|-----|-------|
| TDD-01 | Foundation Architecture (base models) |
| TDD-03 | Resource Clients (custom field resolution in API calls) |
| TDD-04 | Batch/Save Operations (change tracking integration) |

### Key Files

| Component | Location |
|-----------|----------|
| CustomFieldAccessor | `src/autom8_asana/models/custom_field_accessor.py` |
| Custom Field Descriptors | `src/autom8_asana/models/business/descriptors.py` |
| Task Model | `src/autom8_asana/models/task.py` |
| SaveSession | `src/autom8_asana/persistence/session.py` |
| ChangeTracker | `src/autom8_asana/persistence/tracker.py` |
| Business Models | `src/autom8_asana/models/business/*.py` |
