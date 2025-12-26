# PRD: Custom Field Property Descriptors (Initiative A)

## Metadata
- **PRD ID**: PRD-PATTERNS-A
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-16
- **Last Updated**: 2025-12-16
- **Stakeholders**: SDK Maintainers, Business Layer Consumers
- **Related PRDs**: PRD-HARDENING-C (Navigation Descriptors, pattern reference)
- **Discovery Document**: [DISCOVERY-PATTERNS-A-CUSTOM-FIELDS.md](/docs/discovery/DISCOVERY-PATTERNS-A-CUSTOM-FIELDS.md)
- **Reference ADR**: [ADR-0077-pydantic-descriptor-compatibility.md](/docs/decisions/ADR-0077-pydantic-descriptor-compatibility.md)

---

## Problem Statement

### What Problem Are We Solving?

The SDK's business layer contains **~800+ lines of repetitive custom field property boilerplate** across 5 business models. Each custom field requires 7-8 lines of code:

```python
# Current pattern for EACH of 108 fields:
@property
def company_id(self) -> str | None:
    """Company identifier (custom field)."""
    return self._get_text_field(self.Fields.COMPANY_ID)

@company_id.setter
def company_id(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.COMPANY_ID, value)
```

**Field Distribution Across Models**:

| Model | Text | Enum | Multi-Enum | Number | People | Total |
|-------|------|------|------------|--------|--------|-------|
| Business | 13 | 4 | 0 | 1 (int) | 1 | 19 |
| Contact | 16 | 3 | 0 | 0 | 0 | 19 |
| Unit | 13 | 8 | 3 | 8 (5 decimal, 3 int) | 1 | 31 |
| Offer | 20 | 5 | 2 | 8 (5 decimal, 3 int) | 1 | 39 |
| Process | 4 | 3 | 0 | 0 | 1 | 9 |
| **Total** | **66** | **23** | **5** | **17** | **4** | **117** |

**Note**: 117 total fields includes duplicates across models (e.g., `vertical` appears in 4 models). Unique field definitions: ~108.

### For Whom?

- **SDK Maintainers**: Developers who must add new custom fields or fix bugs across 5 files
- **Code Reviewers**: Anyone verifying that copy-pasted implementations are consistent
- **Business Layer Consumers**: Users who expect consistent behavior across all field types

### What Is the Impact of Not Solving It?

**Maintenance Burden (Severity: High)**:
1. **~800 lines of boilerplate**: 108 fields x 7-8 lines each
2. **5 duplicate helper method sets**: `_get_text_field`, `_get_enum_field`, etc. defined in each model
3. **Inconsistency risk**: Subtle variations in field handling across models
4. **New field friction**: Adding a custom field requires ~15 lines of code (Fields constant + property + setter)

**Type Safety Gaps (Severity: Medium)**:
1. **Date fields stored as text**: 8 date-like fields (e.g., `process_due_date`) return raw strings, not parsed dates
2. **No compile-time validation**: Field name typos only caught at runtime

**From Discovery** (Section 9):
> **Reduction Potential**: ~800 lines of boilerplate to ~110 declarative lines (80% reduction)

---

## Goals & Success Metrics

### Goals

| Goal | Measure |
|------|---------|
| **G1: Eliminate Custom Field Boilerplate** | 108 properties become 108 single-line descriptor declarations |
| **G2: Type-Safe Field Access** | Each descriptor type returns its declared return type |
| **G3: Auto-Generate Fields Constants** | `Fields` inner class auto-generated from descriptors |
| **G4: Integrate with Cascading Fields** | `cascading=True` parameter integrates with existing CascadingFieldDef system |
| **G5: Arrow Date Parsing** | DateField returns `Arrow` objects, not raw strings |
| **G6: Preserve External API** | All existing property names and behaviors unchanged |

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Lines of custom field code | Reduce by ~700 (80%) | LOC count before/after |
| Helper method implementations | Reduce from 25 to 0 | `grep _get_text_field` count |
| Descriptor type coverage | 100% of field types | All 7 types implemented |
| Type hint accuracy | 100% mypy clean | `mypy src/autom8_asana --strict` |
| Existing test pass rate | 100% | pytest suite |
| IDE autocomplete | Full support | Manual verification |

---

## Scope

### In Scope

**Part 1: Descriptor Types**
- **R1**: `TextField` descriptor for string fields (56 fields)
- **R2**: `EnumField` descriptor extracting name from dict (21 fields)
- **R3**: `MultiEnumField` descriptor returning `list[str]` (7 fields)
- **R4**: `NumberField` descriptor returning `Decimal | None` (8 fields)
- **R5**: `IntField` descriptor returning `int | None` (4 fields)
- **R6**: `PeopleField` descriptor returning `list[dict[str, Any]]` (4 fields)
- **R7**: `DateField` descriptor with Arrow parsing (8 fields)

**Part 2: Base Infrastructure**
- **R8**: `CustomFieldDescriptor[T]` generic base class
- **R9**: Pydantic v2 compatibility via `ignored_types` (per ADR-0077)

**Part 3: Fields Class Auto-Generation**
- **R10**: Auto-generate `Fields` inner class from descriptor declarations
- **R11**: Support explicit `field_name` override for non-standard names

**Part 4: Cascading Field Integration**
- **R12**: `cascading=True` parameter for field descriptors
- **R13**: Integration with existing `CascadingFieldDef` system

**Part 5: Model Migration**
- **R14**: Migrate Business model (19 fields)
- **R15**: Migrate Contact model (19 fields)
- **R16**: Migrate Unit model (31 fields)
- **R17**: Migrate Offer model (39 fields)
- **R18**: Migrate Process model (9 fields)

### Out of Scope

- **OS-1**: Navigation descriptors (already implemented in PRD-HARDENING-C)
- **OS-2**: SDK core entities (Task, Project, etc.) - no custom field properties
- **OS-3**: Custom field validation beyond type coercion - validation handled by CustomFieldAccessor
- **OS-4**: Breaking API changes - all existing property names preserved
- **OS-5**: Multi-value type coercion on set (e.g., accepting `datetime` for DateField setter)
- **OS-6**: Enum value validation against allowed options - deferred to future initiative

---

## Requirements

### Functional Requirements: Base Descriptor (FR-BASE)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-BASE-001** | `CustomFieldDescriptor[T]` MUST be a generic base class | Must | `TextField(CustomFieldDescriptor[str])` compiles; mypy clean |
| **FR-BASE-002** | Base descriptor MUST implement `__set_name__` for field name derivation | Must | `company_id = TextField()` derives field name `"Company ID"` |
| **FR-BASE-003** | Base descriptor MUST support explicit `field_name` parameter | Must | `mrr = NumberField(field_name="MRR")` uses `"MRR"` not `"M R R"` |
| **FR-BASE-004** | Base descriptor MUST use `get_custom_fields().get()` for reads | Must | Dirty tracking integration preserved |
| **FR-BASE-005** | Base descriptor MUST use `get_custom_fields().set()` for writes | Must | Dirty tracking triggered on set |
| **FR-BASE-006** | Descriptors MUST be declared WITHOUT type annotations | Must | Per ADR-0077; avoids Pydantic field creation |
| **FR-BASE-007** | Descriptors MUST support `@overload` for type inference | Must | IDE shows `str | None` for TextField, not `TextField` |

### Functional Requirements: TextField (FR-TEXT)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-TEXT-001** | `TextField.__get__` MUST return `str | None` | Must | `business.company_id` returns string or None |
| **FR-TEXT-002** | `TextField` MUST coerce non-string values to string | Must | If accessor returns `123`, descriptor returns `"123"` |
| **FR-TEXT-003** | `TextField` MUST return `None` for null values | Must | `None` passthrough, not `"None"` |
| **FR-TEXT-004** | `TextField` MUST return empty string as-is | Must | `""` returns `""`, not `None` |
| **FR-TEXT-005** | `TextField.__set__` MUST accept `str | None` | Must | Setter signature matches return type |

### Functional Requirements: EnumField (FR-ENUM)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-ENUM-001** | `EnumField.__get__` MUST return `str | None` | Must | Enum option name extracted from dict |
| **FR-ENUM-002** | `EnumField` MUST extract `name` from dict value | Must | `{"gid": "123", "name": "High"}` returns `"High"` |
| **FR-ENUM-003** | `EnumField` MUST handle string passthrough | Must | If value is already string, return as-is |
| **FR-ENUM-004** | `EnumField` MUST return `None` for missing/null | Must | No value returns `None` |
| **FR-ENUM-005** | `EnumField.__set__` MUST accept `str | None` | Must | Name or None; GID resolution by CustomFieldAccessor |

### Functional Requirements: MultiEnumField (FR-MULTI)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-MULTI-001** | `MultiEnumField.__get__` MUST return `list[str]` | Must | Never returns `None`; empty list for no selection |
| **FR-MULTI-002** | `MultiEnumField` MUST extract `name` from each dict | Must | `[{"gid": "1", "name": "A"}, {"gid": "2", "name": "B"}]` returns `["A", "B"]` |
| **FR-MULTI-003** | `MultiEnumField` MUST return `[]` for None/missing | Must | Empty list, not `None` |
| **FR-MULTI-004** | `MultiEnumField` MUST skip None items in list | Must | `[{"name": "A"}, None]` returns `["A"]` |
| **FR-MULTI-005** | `MultiEnumField.__set__` MUST accept `list[str] | None` | Must | None clears; list of names |

### Functional Requirements: NumberField (FR-NUM)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-NUM-001** | `NumberField.__get__` MUST return `Decimal | None` | Must | Precision preserved via Decimal |
| **FR-NUM-002** | `NumberField` MUST convert number to Decimal | Must | `123.45` returns `Decimal("123.45")` |
| **FR-NUM-003** | `NumberField` MUST return `None` for null values | Must | `None` passthrough |
| **FR-NUM-004** | `NumberField` MUST handle zero distinctly from None | Must | `0` returns `Decimal("0")`, not `None` |
| **FR-NUM-005** | `NumberField.__set__` MUST convert Decimal to float for API | Must | `Decimal("123.45")` sent as `float(123.45)` |

### Functional Requirements: IntField (FR-INT)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-INT-001** | `IntField.__get__` MUST return `int | None` | Must | Integer coercion |
| **FR-INT-002** | `IntField` MUST truncate to integer | Must | `123.7` returns `123` |
| **FR-INT-003** | `IntField` MUST return `None` for null values | Must | `None` passthrough |
| **FR-INT-004** | `IntField` MUST handle zero distinctly from None | Must | `0` returns `0`, not `None` |
| **FR-INT-005** | `IntField.__set__` MUST accept `int | None` | Must | Integer value or None |

### Functional Requirements: PeopleField (FR-PEOPLE)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-PEOPLE-001** | `PeopleField.__get__` MUST return `list[dict[str, Any]]` | Must | Full person dicts preserved |
| **FR-PEOPLE-002** | `PeopleField` MUST return `[]` for None/missing | Must | Empty list, not `None` |
| **FR-PEOPLE-003** | `PeopleField` MUST preserve dict structure | Must | `[{"gid": "123", "name": "John", "email": "..."}]` unchanged |
| **FR-PEOPLE-004** | `PeopleField.__set__` MUST accept `list[dict[str, Any]] | None` | Must | List of person dicts or None |

### Functional Requirements: DateField (FR-DATE)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-DATE-001** | `DateField.__get__` MUST return `Arrow | None` | Must | Arrow datetime object |
| **FR-DATE-002** | `DateField` MUST parse ISO 8601 date strings | Must | `"2025-12-16"` returns `Arrow` at start of day |
| **FR-DATE-003** | `DateField` MUST parse ISO 8601 datetime strings | Must | `"2025-12-16T10:30:00Z"` returns `Arrow` with time |
| **FR-DATE-004** | `DateField` MUST return `None` for null/empty | Must | `None` or `""` returns `None` |
| **FR-DATE-005** | `DateField` MUST handle invalid date strings gracefully | Should | Returns `None` on parse failure (logged warning) |
| **FR-DATE-006** | `DateField.__set__` MUST accept `Arrow | None` | Must | Arrow converted to ISO string on write |
| **FR-DATE-007** | `DateField.__set__` MUST convert Arrow to ISO string | Must | `Arrow` -> `"2025-12-16"` or full datetime |

### Functional Requirements: Fields Auto-Generation (FR-FIELDS)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-FIELDS-001** | Descriptors MUST auto-register fields via `__set_name__` | Must | Each descriptor registers its field constant |
| **FR-FIELDS-002** | Fields class MUST be accessible as `Model.Fields` | Must | `Business.Fields.COMPANY_ID` works |
| **FR-FIELDS-003** | Field constant name MUST derive from property name | Must | `company_id` -> `COMPANY_ID` |
| **FR-FIELDS-004** | Field value MUST derive from property name or explicit override | Must | `company_id` -> `"Company ID"`; `mrr` -> `"MRR"` (override) |
| **FR-FIELDS-005** | Known abbreviations MUST be preserved | Must | `mrr` -> `"MRR"`, `ai` -> `"AI"`, `url` -> `"URL"` |
| **FR-FIELDS-006** | Explicit `field_name` MUST override derivation | Must | `TextField(field_name="Custom Name")` uses `"Custom Name"` |
| **FR-FIELDS-007** | Fields class MUST support IDE autocomplete | Should | Constant names visible in IDE |

### Functional Requirements: Cascading Integration (FR-CASCADE)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-CASCADE-001** | Descriptors MUST accept `cascading=True` parameter | Must | `office_phone = TextField(cascading=True)` |
| **FR-CASCADE-002** | Cascading descriptors MUST integrate with CascadingFieldDef | Must | Lookup in `CascadingFields` inner class |
| **FR-CASCADE-003** | `cascading=True` MUST NOT change get/set behavior | Must | Only metadata; cascade logic in SaveSession |
| **FR-CASCADE-004** | Non-cascading fields MUST work without CascadingFields class | Must | Default `cascading=False` requires no CascadingFields |

### Functional Requirements: Pydantic Compatibility (FR-PYDANTIC)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-PYDANTIC-001** | All descriptor types MUST be in `model_config.ignored_types` | Must | Pydantic ignores descriptor class attributes |
| **FR-PYDANTIC-002** | Descriptors MUST work with Pydantic's `__setattr__` | Must | Setter called via `extra="allow"` config |
| **FR-PYDANTIC-003** | Model serialization MUST exclude descriptors | Must | `model_dump()` excludes descriptor attributes |
| **FR-PYDANTIC-004** | Descriptors MUST NOT interfere with `PrivateAttr` | Must | Navigation refs continue to work |

### Functional Requirements: Backward Compatibility (FR-COMPAT)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-COMPAT-001** | All existing property names MUST be preserved | Must | `business.company_id`, `unit.mrr`, etc. unchanged |
| **FR-COMPAT-002** | All existing return types MUST be preserved | Must | Decimal stays Decimal, int stays int |
| **FR-COMPAT-003** | All existing setter signatures MUST be preserved | Must | Setter accepts same types as before |
| **FR-COMPAT-004** | Dirty tracking MUST continue to work | Must | `task.get_custom_fields().has_changes()` accurate |
| **FR-COMPAT-005** | SaveSession integration MUST be unchanged | Must | Commit workflow unaffected |

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| **NFR-001** | Property access latency | < 100ns overhead vs current | Benchmark test |
| **NFR-002** | Memory overhead per descriptor | < 100 bytes | Memory profiler |
| **NFR-003** | Type safety | 100% mypy clean | `mypy --strict` |
| **NFR-004** | Code reduction | >= 700 lines removed | LOC diff |
| **NFR-005** | Test coverage maintained | >= 90% | pytest --cov |
| **NFR-006** | IDE autocomplete | Full IntelliSense support | Manual verification |

---

## User Stories / Use Cases

### UC-1: Basic Field Access (Unchanged Behavior)

```python
# Current usage continues to work identically
business = await Business.from_gid_async(client, gid)

# Text field
assert business.company_id == "ACME-123"

# Enum field (extracts name from dict)
assert business.vertical == "Healthcare"

# Number field
assert unit.mrr == Decimal("5000.00")

# Multi-enum field
assert unit.platforms == ["Meta", "TikTok"]

# People field
assert business.rep == [{"gid": "123", "name": "John Doe"}]
```

### UC-2: DateField with Arrow Parsing

```python
# Date fields now return Arrow objects
process = await Process.from_gid_async(client, gid)

# Before: string
# process.process_due_date == "2025-12-20"

# After: Arrow
due_date = process.process_due_date
assert isinstance(due_date, Arrow)
assert due_date.format("YYYY-MM-DD") == "2025-12-20"

# Setting accepts Arrow
process.process_due_date = arrow.now().shift(days=7)
```

### UC-3: Declarative Field Definition

```python
# Before: ~15 lines per field
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
        """Company identifier."""
        return self._get_text_field(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)


# After: 1 line per field (Fields auto-generated)
class Business(BusinessEntity):
    company_id = TextField()
    mrr = NumberField(field_name="MRR")  # Override for abbreviation
    vertical = EnumField()
    rep = PeopleField()
```

### UC-4: Cascading Field Declaration

```python
class Business(BusinessEntity):
    # Cascading field - integrates with CascadingFields
    office_phone = TextField(cascading=True)

    class CascadingFields:
        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={"Unit", "Offer", "Process"},
        )
```

### UC-5: Fields Class Auto-Access

```python
# Fields class auto-generated from descriptors
class Business(BusinessEntity):
    company_id = TextField()
    vertical = EnumField()

# Auto-generated equivalent:
# class Fields:
#     COMPANY_ID = "Company ID"
#     VERTICAL = "Vertical"

# Usage
assert Business.Fields.COMPANY_ID == "Company ID"
assert Business.Fields.VERTICAL == "Vertical"
```

### UC-6: Type Safety in IDE

```python
# IDE shows correct types via @overload
business = Business.model_validate(data)

# IDE knows: company_id: str | None
if business.company_id:
    print(business.company_id.upper())  # IDE autocomplete works

# IDE knows: mrr: Decimal | None
if business.mrr:
    print(business.mrr + Decimal("100"))  # Correct type inference

# IDE knows: platforms: list[str]
for platform in unit.platforms:  # IDE knows platform: str
    print(platform.lower())
```

---

## Technical Approach

### R1-R7: Descriptor Implementation

**Base Class Pattern** (per ADR-0077):

```python
from typing import Generic, TypeVar, Any, overload
from decimal import Decimal

T = TypeVar("T")

class CustomFieldDescriptor(Generic[T]):
    """Base descriptor for custom field properties.

    Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.

    Args:
        field_name: Explicit field name override. If None, derived from property name.
        cascading: If True, field participates in cascading field system.
    """

    __slots__ = ("field_name", "cascading", "public_name", "_field_constant")

    def __init__(
        self,
        field_name: str | None = None,
        cascading: bool = False,
    ) -> None:
        self.field_name = field_name
        self.cascading = cascading
        self.public_name: str = ""
        self._field_constant: str = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        """Called when descriptor is assigned to class attribute.

        Derives field name from property name if not explicitly provided.
        Registers field in owner's Fields class.
        """
        self.public_name = name
        self._field_constant = self._derive_constant_name(name)

        if self.field_name is None:
            self.field_name = self._derive_field_name(name)

        # Register in Fields class
        self._register_field(owner)

    def _derive_constant_name(self, name: str) -> str:
        """Derive SCREAMING_SNAKE_CASE constant from property name."""
        return name.upper()

    def _derive_field_name(self, name: str) -> str:
        """Derive 'Title Case With Spaces' field name from property name.

        Handles known abbreviations: mrr -> MRR, ai -> AI, url -> URL
        """
        ABBREVIATIONS = {"mrr", "ai", "url", "id", "num", "cal", "vca", "sms"}

        parts = name.split("_")
        result = []
        for part in parts:
            if part.lower() in ABBREVIATIONS:
                result.append(part.upper())
            else:
                result.append(part.capitalize())
        return " ".join(result)

    def _register_field(self, owner: type[Any]) -> None:
        """Register field constant in owner's Fields class."""
        # Implementation via metaclass or __init_subclass__
        pass

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
        """Get and transform value from custom fields. Override in subclasses."""
        raise NotImplementedError

    def _set_value(self, obj: Any, value: T | None) -> None:
        """Set value in custom fields. Override in subclasses."""
        obj.get_custom_fields().set(self.field_name, value)
```

**TextField Implementation**:

```python
class TextField(CustomFieldDescriptor[str | None]):
    """Descriptor for text custom fields."""

    def _get_value(self, obj: Any) -> str | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None or isinstance(value, str):
            return value
        return str(value)
```

**EnumField Implementation**:

```python
class EnumField(CustomFieldDescriptor[str | None]):
    """Descriptor for enum custom fields.

    Extracts name from dict: {"gid": "123", "name": "Value"} -> "Value"
    """

    def _get_value(self, obj: Any) -> str | None:
        value = obj.get_custom_fields().get(self.field_name)
        if isinstance(value, dict):
            name = value.get("name")
            return str(name) if name is not None else None
        if value is None or isinstance(value, str):
            return value
        return str(value)
```

**NumberField Implementation**:

```python
class NumberField(CustomFieldDescriptor[Decimal | None]):
    """Descriptor for decimal number custom fields."""

    def _get_value(self, obj: Any) -> Decimal | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        return Decimal(str(value))

    def _set_value(self, obj: Any, value: Decimal | None) -> None:
        # Convert Decimal to float for API
        api_value = float(value) if value is not None else None
        obj.get_custom_fields().set(self.field_name, api_value)
```

**DateField Implementation**:

```python
import arrow
from arrow import Arrow

class DateField(CustomFieldDescriptor[Arrow | None]):
    """Descriptor for date custom fields with Arrow parsing."""

    def _get_value(self, obj: Any) -> Arrow | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None or value == "":
            return None
        try:
            return arrow.get(value)
        except Exception:
            # Log warning, return None for invalid dates
            return None

    def _set_value(self, obj: Any, value: Arrow | None) -> None:
        # Convert Arrow to ISO string for API
        api_value = value.isoformat() if value is not None else None
        obj.get_custom_fields().set(self.field_name, api_value)
```

### R10-R11: Fields Class Auto-Generation

**Approach**: Use `__init_subclass__` to collect field constants from descriptors.

```python
class BusinessEntity(Task):
    """Base class with Fields auto-generation."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        # Collect field descriptors
        field_constants: dict[str, str] = {}

        for name, attr in cls.__dict__.items():
            if isinstance(attr, CustomFieldDescriptor):
                constant_name = attr._field_constant
                field_value = attr.field_name
                field_constants[constant_name] = field_value

        # Create or update Fields inner class
        if field_constants:
            existing_fields = getattr(cls, "Fields", None)
            if existing_fields is None:
                # Create new Fields class
                fields_cls = type("Fields", (), field_constants)
            else:
                # Extend existing Fields class
                fields_cls = type("Fields", (existing_fields,), field_constants)
            cls.Fields = fields_cls
```

### R12-R13: Cascading Integration

**Approach**: `cascading=True` is metadata only; actual cascading handled by SaveSession.

```python
class TextField(CustomFieldDescriptor[str | None]):
    def __init__(
        self,
        field_name: str | None = None,
        cascading: bool = False,
    ) -> None:
        super().__init__(field_name=field_name, cascading=cascading)

# Usage in model
class Business(BusinessEntity):
    office_phone = TextField(cascading=True)

    class CascadingFields:
        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={"Unit", "Offer"},
        )
```

---

## Design Decisions

### DD-1: Generic Base Class vs. Separate Implementations

**Decision**: Single `CustomFieldDescriptor[T]` base with type-specific subclasses.

**Rationale**:
- Generic type parameter provides type safety
- Common logic (field name derivation, registration) in base
- Subclasses only implement `_get_value` and `_set_value`
- Consistent with navigation descriptors pattern (PRD-HARDENING-C)

### DD-2: Return Type for List Fields

**Decision**: `MultiEnumField` and `PeopleField` return `list[...]`, never `None`.

**Rationale**:
- Current implementation returns `[]` for missing values
- Simplifies consumer code (no None checks before iteration)
- Consistent with Python list semantics

### DD-3: Date Handling with Arrow

**Decision**: `DateField` returns `Arrow | None`, not `str | None`.

**Rationale**:
- Arrow is already a project dependency
- Type-safe date manipulation
- ISO string handling automatic
- Current string-based dates are error-prone

**Migration**: Existing date fields (stored as Text) convert to DateField.

### DD-4: Fields Class Generation Strategy

**Decision**: Auto-generate via `__init_subclass__`, not metaclass.

**Rationale**:
- Simpler than custom metaclass
- Works with Pydantic's metaclass
- Consistent with PRD-HARDENING-C's `_CACHED_REF_ATTRS` pattern
- IDE support via type stubs if needed

### DD-5: Abbreviation Handling

**Decision**: Dictionary of known abbreviations for field name derivation.

**Rationale**:
- `mrr` should become `"MRR"`, not `"M R R"`
- Explicit dictionary is maintainable
- Explicit `field_name` override as escape hatch

**Known Abbreviations**: `mrr`, `ai`, `url`, `id`, `num`, `cal`, `vca`, `sms`

### DD-6: Cascading Parameter Scope

**Decision**: `cascading=True` is metadata only; does not change get/set behavior.

**Rationale**:
- Cascade logic lives in SaveSession
- Descriptors remain single-responsibility
- Integration point is field registration, not access

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| **A1**: Arrow library is available as dependency | Already used elsewhere in codebase |
| **A2**: All date fields use ISO 8601 format | Asana API uses ISO 8601 |
| **A3**: Abbreviations list covers all current fields | Discovery Section 6.3 documents edge cases |
| **A4**: Fields class access pattern is `Model.Fields.CONSTANT` | Current pattern in all 5 models |
| **A5**: Decimal for money fields, int for count fields | Current pattern; no float returns |
| **A6**: Pydantic `ignored_types` pattern from ADR-0077 applies | Navigation descriptors use same pattern |

---

## Dependencies

| Dependency | Owner | Status | Impact |
|------------|-------|--------|--------|
| **Arrow library** | PyPI | Stable | DateField parsing |
| **Pydantic v2** | PyPI | Stable | Model compatibility |
| **ADR-0077 pattern** | Architecture | Accepted | Pydantic descriptor compatibility |
| **CustomFieldAccessor** | SDK Core | Stable | get/set integration |
| **CascadingFieldDef** | Business Layer | Stable | Cascading integration |

### Blocks

| Blocked Initiative | Reason |
|--------------------|--------|
| None | This initiative is foundational for new features |

---

## Migration Guide

### Phase 1: Descriptor Infrastructure (Non-Breaking)

1. Add descriptor classes to `models/business/descriptors.py`:
   - `CustomFieldDescriptor[T]` base class
   - `TextField`, `EnumField`, `MultiEnumField`
   - `NumberField`, `IntField`
   - `PeopleField`, `DateField`

2. Update `BusinessEntity.model_config` with all descriptor types:
   ```python
   model_config = ConfigDict(
       ignored_types=(
           ParentRef, HolderRef,  # Existing
           TextField, EnumField, MultiEnumField,  # New
           NumberField, IntField, PeopleField, DateField,
       ),
       extra="allow",
   )
   ```

3. Add Fields auto-generation to `BusinessEntity.__init_subclass__`

### Phase 2: Model Migration (Non-Breaking)

Migrate each model one at a time, maintaining backward compatibility:

```python
# Before (Business)
class Business(BusinessEntity):
    class Fields:
        COMPANY_ID = "Company ID"
        VERTICAL = "Vertical"
        NUM_REVIEWS = "Num Reviews"
        REP = "Rep"

    def _get_text_field(self, field_name: str) -> str | None: ...
    def _get_enum_field(self, field_name: str) -> str | None: ...

    @property
    def company_id(self) -> str | None:
        return self._get_text_field(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

    @property
    def vertical(self) -> str | None:
        return self._get_enum_field(self.Fields.VERTICAL)

    # ... 17 more properties


# After (Business)
class Business(BusinessEntity):
    # Descriptors - Fields class auto-generated
    company_id = TextField()
    facebook_page_id = TextField()
    fallback_page_id = TextField()
    google_cal_id = TextField(field_name="Google Cal ID")
    office_phone = TextField(cascading=True)
    owner_name = TextField()
    owner_nickname = TextField()
    review_1 = TextField()
    review_2 = TextField()
    reviews_link = TextField()
    stripe_id = TextField(field_name="Stripe ID")
    stripe_link = TextField()
    twilio_phone_num = TextField()

    num_reviews = IntField()

    aggression_level = EnumField()
    booking_type = EnumField()
    vca_status = TextField(field_name="VCA Status")
    vertical = EnumField()

    rep = PeopleField()

    # Helper methods removed - no longer needed
    # Fields class auto-generated from descriptors
```

### Migration Order

1. **Business** (19 fields) - Simplest model, validation
2. **Contact** (19 fields) - No Number fields, simple
3. **Process** (9 fields) - Includes DateField migration
4. **Unit** (31 fields) - Most diverse field types
5. **Offer** (39 fields) - Largest model, final validation

### Phase 3: Helper Method Cleanup (Non-Breaking)

After all models migrated, remove:
- `_get_text_field()` from each model
- `_get_enum_field()` from each model
- `_get_number_field()` from Unit, Offer
- `_get_int_field()` from Unit, Offer
- `_get_multi_enum_field()` from Unit, Offer

### Phase 4: Fields Class Cleanup (Non-Breaking)

Remove explicit `class Fields:` definitions after verifying auto-generation works correctly.

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should DateField support timezone configuration? | Architect | TBD | Default to UTC; timezone-aware via Arrow |
| Should we add validation for enum values against allowed options? | Architect | TBD | Deferred - CustomFieldAccessor handles validation |
| Should Fields class be a proper enum instead of namespace? | Architect | TBD | Deferred - current pattern works for IDE |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Type hint regression | Low | Medium | Extensive mypy testing; @overload coverage |
| DateField breaks existing date string handling | Medium | Medium | Phased migration; DateField optional initially |
| Fields auto-generation misses edge cases | Medium | Low | Explicit `field_name` override available |
| Abbreviation dictionary incomplete | Low | Low | Easy to extend; explicit override available |
| Pydantic compatibility issues | Low | High | ADR-0077 pattern proven with navigation descriptors |

---

## Test Strategy

### Unit Tests

| Test Category | Coverage |
|---------------|----------|
| `TextField.__get__` | String return; None handling; coercion |
| `TextField.__set__` | String value; None value |
| `EnumField.__get__` | Dict extraction; string passthrough; None |
| `MultiEnumField.__get__` | List extraction; empty list; None items |
| `NumberField.__get__` | Decimal conversion; None; zero |
| `NumberField.__set__` | Decimal to float conversion |
| `IntField.__get__` | Integer truncation; None; zero |
| `DateField.__get__` | Arrow parsing; None; invalid string |
| `DateField.__set__` | Arrow to ISO conversion |
| `PeopleField.__get__` | List return; empty list |
| Field name derivation | Standard names; abbreviations; overrides |
| Fields class generation | Constants created; values correct |

### Integration Tests

| Test Category | Coverage |
|---------------|----------|
| Business model fields | All 19 fields accessible |
| Contact model fields | All 19 fields accessible |
| Unit model fields | All 31 fields accessible |
| Offer model fields | All 39 fields accessible |
| Process model fields | All 9 fields with DateField |
| Dirty tracking | Changes tracked via descriptors |
| SaveSession commit | Fields save correctly |
| Cascading fields | Integration with CascadingFieldDef |

### Regression Tests

| Test Category | Coverage |
|---------------|----------|
| All existing business entity tests pass | No regressions |
| All existing custom field tests pass | No regressions |
| SaveSession with custom fields | Commit/track unchanged |

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
| 1.0 | 2025-12-16 | Requirements Analyst | Initial draft based on DISCOVERY-PATTERNS-A-CUSTOM-FIELDS |

---

## Quality Gate Checklist

- [x] Problem statement is clear and compelling (~800 lines boilerplate, 108 fields)
- [x] Scope explicitly defines in/out (18 in-scope, 6 out-of-scope items)
- [x] All requirements are specific and testable (FR-BASE through FR-COMPAT)
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented (A1-A6)
- [x] Open questions documented with owners (3 questions)
- [x] Dependencies identified (Arrow, Pydantic, ADR-0077)
- [x] Design decisions documented (DD-1 through DD-6)
- [x] Migration guide provided (4 phases)
- [x] Risk assessment completed
- [x] Test strategy defined
