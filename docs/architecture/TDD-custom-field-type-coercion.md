# TDD: Centralized Custom Field Type Coercion

## Overview

This design introduces a centralized type coercion layer that transforms raw Asana API custom field values into schema-compatible types. The coercion is schema-aware, using the target `dtype` from `ColumnDef` to determine the appropriate transformation. This eliminates scattered, field-specific fixes in extractors and ensures consistent type handling across all custom field types.

## Metadata

| Field | Value |
|-------|-------|
| Artifact ID | TDD-custom-field-type-coercion |
| Status | Draft |
| Author | Architect |
| Created | 2026-01-02 |
| PRD | N/A (Bug fix with architectural improvement) |
| Complexity | Medium |

---

## Context

### Problem Statement

A bug was discovered where the `specialty` custom field (configured as `multi_enum` in Asana) returns `[]` when unset, but the `UnitRow` model expects `str | None`. This caused a Pydantic validation error:

```
ValidationError: 1 validation error for UnitRow
specialty
  Input should be a valid string [type=string_type, input_value=[], input_type=list]
```

A quick fix was applied in `UnitExtractor._create_row()`:

```python
# Handle specialty field - may come back as list from multi_enum
specialty = data.get("specialty")
if isinstance(specialty, list):
    data["specialty"] = ", ".join(specialty) if specialty else None

# Handle vertical field - same potential issue
vertical = data.get("vertical")
if isinstance(vertical, list):
    data["vertical"] = ", ".join(vertical) if vertical else None
```

This band-aid is problematic because:

1. **Scattered Logic**: Each extractor must know about type mismatches
2. **Incomplete Coverage**: Only handles `specialty` and `vertical`, not other fields
3. **No Schema Awareness**: The fix is hardcoded, not driven by schema metadata
4. **Violates DRY**: Same pattern would be repeated in other extractors

### Root Cause Analysis

The type mismatch occurs because:

1. **Asana API Behavior**: `multi_enum` fields always return a list (empty `[]` when unset)
2. **Schema Definition**: Some `multi_enum` fields are mapped to `Utf8` (string) in the schema for display purposes
3. **No Coercion Layer**: `DefaultCustomFieldResolver._extract_raw_value()` returns raw API types without considering the target schema dtype

**Type Mapping Table**:

| Asana Field Type | Raw API Return | Schema dtype Options | Coercion Needed |
|------------------|----------------|----------------------|-----------------|
| `text` | `str \| None` | `Utf8` | No |
| `number` | `Decimal \| None` | `Decimal`, `Float64`, `Int64` | Sometimes |
| `enum` | `str \| None` | `Utf8` | No |
| `multi_enum` | `list[str]` (always) | `List[Utf8]` or `Utf8` | Yes (list to string) |
| `date` | `str \| None` | `Date` | Already handled |
| `people` | `list[str]` (GIDs) | `List[Utf8]` | No |

The critical gap: **`multi_enum` to `Utf8` coercion is missing**.

### Existing Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Current Data Flow                                 │
└──────────────────────────────────────────────────────────────────────────┘

   Asana API                    Resolver                  Extractor
      │                            │                          │
      │ custom_fields[]            │                          │
      ▼                            │                          │
  ┌─────────┐                      │                          │
  │ Task    │                      │                          │
  │ {       │                      │                          │
  │   cf:   │   get_value(task,    │                          │
  │   [...]│   "cf:specialty")    │                          │
  │ }       │ ─────────────────────▶                          │
  └─────────┘                      │                          │
                                   ▼                          │
                           ┌──────────────┐                   │
                           │ _extract_    │                   │
                           │ raw_value()  │                   │
                           │              │   raw list[]      │
                           │ multi_enum   │ ─────────────────▶│
                           │   → list[]   │                   │
                           └──────────────┘                   ▼
                                                       ┌──────────────┐
                                                       │ _create_row()│
                                                       │              │
                                                       │ *** BUG ***  │
                                                       │ UnitRow      │
                                                       │ expects str  │
                                                       └──────────────┘
```

**Key Files**:

| File | Role |
|------|------|
| `resolver/default.py` | Extracts raw values from custom fields |
| `resolver/protocol.py` | Defines `CustomFieldResolver` protocol |
| `models/schema.py` | `ColumnDef` with `dtype` and `source` |
| `extractors/base.py` | Calls resolver, creates rows |
| `extractors/unit.py` | Contains the band-aid fix |

### Constraints

1. **Backward Compatible**: Existing code using resolvers must continue to work
2. **Schema-Driven**: Coercion logic must use `ColumnDef.dtype`, not hardcoded field names
3. **Testable**: Clear contract with unit-testable coercion functions
4. **Single Responsibility**: Coercion should be a distinct, composable component
5. **No Breaking API Changes**: `CustomFieldResolver` protocol unchanged

---

## System Design

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      Proposed Data Flow                                   │
└──────────────────────────────────────────────────────────────────────────┘

   Asana API          Resolver            Coercer           Extractor
      │                  │                   │                  │
      │ custom_fields[]  │                   │                  │
      ▼                  │                   │                  │
  ┌─────────┐            │                   │                  │
  │ Task    │            │                   │                  │
  │ {cf:[]} │            │                   │                  │
  └─────────┘            │                   │                  │
      │   get_value()    │                   │                  │
      │ ──────────────────▶                  │                  │
      │                  ▼                   │                  │
      │          ┌──────────────┐            │                  │
      │          │ _extract_    │            │                  │
      │          │ raw_value()  │            │                  │
      │          └──────────────┘            │                  │
      │                  │ raw value         │                  │
      │                  ▼                   │                  │
      │          ┌──────────────┐            │                  │
      │          │ _coerce()    │   ◀────────│ [uses coercer]   │
      │          │ [ENHANCED]   │            │                  │
      │          └──────────────┘            │                  │
      │                  │ coerced value     │                  │
      │                  ▼                   │                  │
      │          Return to caller ───────────────────────────────▶
      │                                                         │
      │                                                         ▼
      │                                                 ┌──────────────┐
      │                                                 │ _create_row()│
      │                                                 │              │
      │                                                 │ No fix       │
      │                                                 │ needed!      │
      │                                                 └──────────────┘
```

### Component Overview

The solution introduces a **TypeCoercer** module that provides schema-aware type conversion:

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `TypeCoercer` | Stateless coercion functions for each Asana field type | `resolver/coercer.py` (NEW) |
| `DefaultCustomFieldResolver` | Enhanced to accept optional `ColumnDef` for coercion | `resolver/default.py` (MODIFIED) |
| `BaseExtractor._extract_column()` | Passes `ColumnDef` to resolver for schema-aware coercion | `extractors/base.py` (MODIFIED) |
| `UnitExtractor._create_row()` | Remove band-aid fix | `extractors/unit.py` (MODIFIED) |

### Design Decision: Where to Put Coercion Logic

**Options Considered**:

| Option | Location | Pros | Cons |
|--------|----------|------|------|
| A | New `coercer.py` module | SRP, testable, reusable | Extra module |
| B | Inline in `DefaultCustomFieldResolver._coerce()` | Minimal change | Already getting complex |
| C | In `BaseExtractor._extract_column()` | Close to usage | Couples extraction to coercion |
| D | Post-extraction in `_create_row()` | Quick fix | Current band-aid approach, doesn't scale |

**Decision**: **Option A + B Hybrid**

- Create `TypeCoercer` class in `resolver/coercer.py` with pure coercion functions
- Enhance `DefaultCustomFieldResolver._coerce()` to use `TypeCoercer`
- Pass `ColumnDef` to resolver via enhanced `get_value()` signature

**Rationale**:
- Keeps coercion logic testable and isolated
- Minimal API change (optional parameter)
- Resolver remains the single point of custom field extraction
- Coercer is reusable for other type conversion needs

---

## Component Specifications

### FR-001: TypeCoercer Class

**Location**: `src/autom8_asana/dataframes/resolver/coercer.py`

```python
"""Type coercion for Asana custom field values.

Per TDD-custom-field-type-coercion FR-001:
Schema-aware coercion of raw Asana API values to target dtypes.

The coercer handles the mismatch between Asana API return types
and schema-defined target types, particularly for multi_enum fields
that return lists but may be mapped to string columns.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar

__all__ = ["TypeCoercer"]

logger = logging.getLogger(__name__)


class TypeCoercer:
    """Stateless type coercion for custom field values.

    Per FR-001: Provides schema-aware coercion from raw Asana API values
    to target dtypes defined in ColumnDef.

    Coercion Rules:
        - list → str: Join with ", " separator (empty list → None)
        - str → list: Wrap in single-element list
        - Any → Decimal: Via str intermediate for precision
        - None: Preserved (nullable fields)

    Example:
        >>> coercer = TypeCoercer()
        >>> coercer.coerce(["A", "B"], "Utf8")
        'A, B'
        >>> coercer.coerce([], "Utf8")
        None
        >>> coercer.coerce("single", "List[Utf8]")
        ['single']
        >>> coercer.coerce("123.45", "Decimal")
        Decimal('123.45')

    Thread Safety:
        All methods are stateless and thread-safe.
    """

    # Separator for joining list values into strings
    LIST_SEPARATOR: ClassVar[str] = ", "

    # dtypes that represent list types
    LIST_DTYPES: ClassVar[frozenset[str]] = frozenset({
        "List[Utf8]",
        "List[String]",
    })

    # dtypes that represent string types
    STRING_DTYPES: ClassVar[frozenset[str]] = frozenset({
        "Utf8",
        "String",
    })

    # dtypes that represent numeric types
    NUMERIC_DTYPES: ClassVar[frozenset[str]] = frozenset({
        "Decimal",
        "Float64",
        "Int64",
        "Int32",
    })

    def coerce(
        self,
        value: Any,
        target_dtype: str,
        *,
        source_type: str | None = None,
    ) -> Any:
        """Coerce value to target dtype.

        Args:
            value: Raw value from Asana API
            target_dtype: Target dtype from ColumnDef (e.g., "Utf8", "List[Utf8]")
            source_type: Optional Asana field type hint (e.g., "multi_enum")

        Returns:
            Coerced value, or None if value is None or empty list

        Raises:
            No exceptions - logs warnings and returns best-effort result
        """
        if value is None:
            return None

        # Handle list → string coercion (multi_enum to Utf8)
        if isinstance(value, list) and target_dtype in self.STRING_DTYPES:
            return self._list_to_string(value)

        # Handle string → list coercion (single value to List[Utf8])
        if isinstance(value, str) and target_dtype in self.LIST_DTYPES:
            return self._string_to_list(value)

        # Handle numeric coercion
        if target_dtype in self.NUMERIC_DTYPES:
            return self._to_numeric(value, target_dtype)

        # Handle list passthrough (list to List[Utf8])
        if isinstance(value, list) and target_dtype in self.LIST_DTYPES:
            return value  # No coercion needed

        # Handle string passthrough
        if isinstance(value, str) and target_dtype in self.STRING_DTYPES:
            return value  # No coercion needed

        # Fallback: return as-is with debug log
        logger.debug(
            "type_coercion_passthrough",
            extra={
                "value_type": type(value).__name__,
                "target_dtype": target_dtype,
                "source_type": source_type,
            },
        )
        return value

    def _list_to_string(self, value: list[Any]) -> str | None:
        """Convert list to comma-separated string.

        Args:
            value: List of values (typically strings from multi_enum)

        Returns:
            Comma-separated string, or None if list is empty
        """
        if not value:
            return None

        # Filter None values and convert to strings
        str_values = [str(v) for v in value if v is not None]

        if not str_values:
            return None

        return self.LIST_SEPARATOR.join(str_values)

    def _string_to_list(self, value: str) -> list[str]:
        """Wrap string in a single-element list.

        Args:
            value: String value

        Returns:
            Single-element list containing the string
        """
        return [value]

    def _to_numeric(self, value: Any, target_dtype: str) -> Decimal | float | int | None:
        """Convert value to numeric type.

        Args:
            value: Value to convert
            target_dtype: Target numeric dtype

        Returns:
            Converted numeric value, or None on failure
        """
        if value is None:
            return None

        try:
            if target_dtype == "Decimal":
                if isinstance(value, Decimal):
                    return value
                return Decimal(str(value))

            if target_dtype == "Float64":
                return float(value)

            if target_dtype in {"Int64", "Int32"}:
                return int(float(value))  # Handle "123.0" → 123

        except (ValueError, TypeError, InvalidOperation) as e:
            logger.debug(
                "type_coercion_numeric_failed",
                extra={
                    "value": value,
                    "target_dtype": target_dtype,
                    "error": str(e),
                },
            )
            return None

        return value


# Module-level singleton for convenience
_coercer = TypeCoercer()


def coerce_value(
    value: Any,
    target_dtype: str,
    *,
    source_type: str | None = None,
) -> Any:
    """Module-level coercion function using singleton.

    See TypeCoercer.coerce() for details.
    """
    return _coercer.coerce(value, target_dtype, source_type=source_type)
```

---

### FR-002: Enhanced CustomFieldResolver Protocol

**Location**: `src/autom8_asana/dataframes/resolver/protocol.py`

The protocol gains an optional `column_def` parameter for schema-aware coercion:

```python
def get_value(
    self,
    task: Task,
    field_name: str,
    expected_type: type | None = None,
    *,
    column_def: ColumnDef | None = None,  # NEW
) -> Any:
    """Extract custom field value from task.

    Args:
        task: Task to extract value from
        field_name: Schema field name (with optional prefix)
        expected_type: Optional type for value coercion (deprecated, use column_def)
        column_def: Optional column definition for schema-aware coercion

    Returns:
        Extracted and optionally coerced value, or None if:
        - Field cannot be resolved
        - Field not present on task
        - Value is null

    Note:
        When column_def is provided, its dtype is used for coercion.
        The expected_type parameter is deprecated in favor of column_def.
    """
    ...
```

**Backward Compatibility**: The `column_def` parameter is optional with `None` default. Existing callers using `expected_type` continue to work unchanged.

---

### FR-003: Enhanced DefaultCustomFieldResolver

**Location**: `src/autom8_asana/dataframes/resolver/default.py`

Modify `get_value()` and `_coerce()` to use schema-aware coercion:

```python
def get_value(
    self,
    task: Task,
    field_name: str,
    expected_type: type | None = None,
    *,
    column_def: ColumnDef | None = None,
) -> Any:
    """Extract custom field value from task.

    Args:
        task: Task to extract from
        field_name: Schema field name (with optional prefix)
        expected_type: Optional type for coercion (deprecated)
        column_def: Optional column definition for schema-aware coercion

    Returns:
        Extracted and optionally coerced value, or None

    Raises:
        KeyError: If strict mode and field not found
    """
    gid = self.resolve(field_name)

    if gid is None:
        if self._strict:
            raise KeyError(f"Cannot resolve custom field: {field_name}")
        return None

    # Find custom field in task by GID
    for cf_data in task.custom_fields or []:
        cf_gid = (
            cf_data.get("gid")
            if isinstance(cf_data, dict)
            else getattr(cf_data, "gid", None)
        )
        if cf_gid == gid:
            raw_value = self._extract_raw_value(cf_data)

            # Schema-aware coercion takes precedence
            if column_def is not None:
                return self._coerce_with_schema(raw_value, column_def, cf_data)

            # Fallback to legacy type-based coercion
            if expected_type is not None and raw_value is not None:
                return self._coerce(raw_value, expected_type)

            return raw_value

    return None


def _coerce_with_schema(
    self,
    value: Any,
    column_def: ColumnDef,
    cf_data: dict[str, Any] | Any,
) -> Any:
    """Coerce value using schema dtype.

    Args:
        value: Raw value from Asana API
        column_def: Column definition with target dtype
        cf_data: Custom field data for source type info

    Returns:
        Coerced value
    """
    from autom8_asana.dataframes.resolver.coercer import coerce_value

    # Get source type from custom field data
    source_type = (
        cf_data.get("resource_subtype")
        if isinstance(cf_data, dict)
        else getattr(cf_data, "resource_subtype", None)
    )

    return coerce_value(
        value,
        column_def.dtype,
        source_type=source_type,
    )
```

---

### FR-004: Enhanced BaseExtractor

**Location**: `src/autom8_asana/dataframes/extractors/base.py`

Modify `_extract_column()` to pass `ColumnDef` to resolver:

```python
def _extract_column(
    self,
    task: Task,
    col: ColumnDef,
    project_gid: str | None = None,
) -> Any:
    """Extract a single column value from a task.

    Per TDD-0009 custom field extraction logic:
    - source is None: Derived field, delegate to _extract_{name} method
    - source starts with "cf:" or "gid:": Custom field via resolver
    - Otherwise: Direct attribute access

    Args:
        task: Task to extract from
        col: Column definition specifying source
        project_gid: Optional project GID for section extraction

    Returns:
        Extracted and optionally coerced value

    Raises:
        ValueError: If resolver required but not provided
    """
    if col.source is None:
        # Derived field - delegate to subclass method
        method_name = f"_extract_{col.name}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if col.name == "section":
                return method(task, project_gid)
            return method(task)
        return None

    if col.source.startswith("cf:") or col.source.startswith("gid:"):
        # Custom field extraction via resolver with schema-aware coercion
        if self._resolver is None:
            raise ValueError(
                f"Resolver required for custom field extraction: {col.source}"
            )
        # Pass column_def for schema-aware coercion
        return self._resolver.get_value(task, col.source, column_def=col)

    # Direct attribute access with dtype-aware parsing
    return self._extract_attribute(task, col.source, col)
```

---

### FR-005: Remove Band-Aid Fix

**Location**: `src/autom8_asana/dataframes/extractors/unit.py`

Remove the hardcoded fixes in `_create_row()`:

```python
def _create_row(self, data: dict[str, Any]) -> UnitRow:
    """Create UnitRow from extracted data.

    Args:
        data: Dict of column_name -> extracted value

    Returns:
        UnitRow instance with all 23 fields
    """
    # Ensure type is set correctly
    data["type"] = "Unit"

    # Convert None lists to empty lists for list fields
    if data.get("tags") is None:
        data["tags"] = []
    if data.get("products") is None:
        data["products"] = []
    if data.get("languages") is None:
        data["languages"] = []

    # REMOVED: Band-aid fixes for specialty and vertical
    # These are now handled by TypeCoercer in the resolver layer

    return UnitRow.model_validate(data)
```

---

## Sequence Diagram

### Custom Field Extraction with Coercion

```
BaseExtractor                 DefaultCustomFieldResolver      TypeCoercer
     │                                   │                        │
     │ _extract_column(task, col)        │                        │
     │ where col.source = "cf:specialty" │                        │
     │ and col.dtype = "Utf8"            │                        │
     │                                   │                        │
     │ get_value(task, "cf:specialty",   │                        │
     │           column_def=col)         │                        │
     │ ─────────────────────────────────▶│                        │
     │                                   │                        │
     │                                   │ _extract_raw_value()   │
     │                                   │ → ["Value1", "Value2"] │
     │                                   │                        │
     │                                   │ _coerce_with_schema()  │
     │                                   │ ───────────────────────▶│
     │                                   │                        │
     │                                   │         coerce_value(  │
     │                                   │           ["Value1",   │
     │                                   │            "Value2"],  │
     │                                   │           "Utf8")      │
     │                                   │                        │
     │                                   │                        │ list detected
     │                                   │                        │ target is Utf8
     │                                   │                        │ → _list_to_string()
     │                                   │                        │
     │                                   │        "Value1, Value2"│
     │                                   │ ◀───────────────────────│
     │                                   │                        │
     │       "Value1, Value2"            │                        │
     │ ◀─────────────────────────────────│                        │
     │                                   │                        │
```

### Empty List Handling

```
Scenario: multi_enum field with no values selected

API returns: specialty = []

Flow:
  1. _extract_raw_value() → []
  2. _coerce_with_schema([], "Utf8")
  3. coerce_value([], "Utf8")
  4. _list_to_string([]) → None

Result: specialty = None (valid for UnitRow.specialty: str | None)
```

---

## Non-Functional Considerations

### Performance

| Metric | Target | Implementation Approach |
|--------|--------|------------------------|
| Coercion overhead | <1ms per field | Stateless, O(1) type checks |
| Memory allocation | Minimal | Reuse singleton coercer |
| No regex | Required | Simple type checks only |

**Coercion is negligible**: The coercer performs simple type checks and string operations. The bottleneck remains the Asana API, not local processing.

### Testability

The design is highly testable:

1. **TypeCoercer is pure**: No external dependencies, fully unit-testable
2. **Coercer is stateless**: No setup required between tests
3. **Clear contract**: Input type + target dtype = output type
4. **Module function for convenience**: `coerce_value()` simplifies test code

### Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid numeric conversion | Log warning, return `None` |
| Unknown dtype | Log debug, return value unchanged |
| `None` input | Return `None` (passthrough) |
| Empty list to string | Return `None` |

No exceptions are raised from coercion. The philosophy is "best effort" with logging for debugging.

### Observability

Structured log events:

| Event | Level | When |
|-------|-------|------|
| `type_coercion_passthrough` | DEBUG | Value passed through unchanged |
| `type_coercion_numeric_failed` | DEBUG | Numeric conversion failed |

These events help debug unexpected type behavior in production.

---

## Implementation Guidance

### File Organization

```
src/autom8_asana/
    dataframes/
        resolver/
            __init__.py          # MODIFY: Export TypeCoercer
            coercer.py           # NEW: TypeCoercer class
            default.py           # MODIFY: Add _coerce_with_schema()
            protocol.py          # MODIFY: Add column_def parameter
        extractors/
            base.py              # MODIFY: Pass column_def to resolver
            unit.py              # MODIFY: Remove band-aid fix
```

### Implementation Order

1. **Step 1**: Create `coercer.py` with `TypeCoercer` class and unit tests
2. **Step 2**: Update `protocol.py` with optional `column_def` parameter
3. **Step 3**: Implement `_coerce_with_schema()` in `default.py`
4. **Step 4**: Update `BaseExtractor._extract_column()` to pass `column_def`
5. **Step 5**: Remove band-aid fix from `UnitExtractor._create_row()`
6. **Step 6**: Run full test suite to verify no regressions

### Migration Path

**Phase 1 (This TDD)**:
- Add `TypeCoercer` as opt-in via `column_def` parameter
- Remove band-aid fix (coercer now handles it)
- Legacy `expected_type` parameter continues to work

**Phase 2 (Future)**:
- Deprecate `expected_type` parameter
- Consider adding `asana_field_type` to `ColumnDef` for source hints

### Backward Compatibility

All changes are additive:

1. `column_def` parameter has `None` default
2. Existing calls without `column_def` work via legacy `expected_type` path
3. `TypeCoercer` is an internal implementation detail

---

## Test Strategy

### Unit Tests for TypeCoercer

```python
# tests/unit/test_type_coercer.py

import pytest
from decimal import Decimal
from autom8_asana.dataframes.resolver.coercer import TypeCoercer


class TestListToString:
    """Test multi_enum to Utf8 coercion."""

    def test_list_to_string_multiple_values(self):
        coercer = TypeCoercer()
        result = coercer.coerce(["A", "B", "C"], "Utf8")
        assert result == "A, B, C"

    def test_list_to_string_single_value(self):
        coercer = TypeCoercer()
        result = coercer.coerce(["Only"], "Utf8")
        assert result == "Only"

    def test_empty_list_to_string_returns_none(self):
        """FR-001: Empty list returns None, not empty string."""
        coercer = TypeCoercer()
        result = coercer.coerce([], "Utf8")
        assert result is None

    def test_list_with_none_values_filtered(self):
        coercer = TypeCoercer()
        result = coercer.coerce(["A", None, "B"], "Utf8")
        assert result == "A, B"


class TestListPassthrough:
    """Test list to List[Utf8] passthrough."""

    def test_list_to_list_passthrough(self):
        coercer = TypeCoercer()
        result = coercer.coerce(["A", "B"], "List[Utf8]")
        assert result == ["A", "B"]

    def test_empty_list_to_list_passthrough(self):
        coercer = TypeCoercer()
        result = coercer.coerce([], "List[Utf8]")
        assert result == []


class TestStringToList:
    """Test single value to list coercion."""

    def test_string_to_list(self):
        coercer = TypeCoercer()
        result = coercer.coerce("single", "List[Utf8]")
        assert result == ["single"]


class TestNumericCoercion:
    """Test numeric type coercion."""

    def test_string_to_decimal(self):
        coercer = TypeCoercer()
        result = coercer.coerce("123.45", "Decimal")
        assert result == Decimal("123.45")

    def test_float_to_decimal(self):
        coercer = TypeCoercer()
        result = coercer.coerce(123.45, "Decimal")
        assert result == Decimal("123.45")

    def test_invalid_numeric_returns_none(self):
        coercer = TypeCoercer()
        result = coercer.coerce("not-a-number", "Decimal")
        assert result is None


class TestNoneHandling:
    """Test None value handling."""

    def test_none_passthrough(self):
        coercer = TypeCoercer()
        for dtype in ["Utf8", "List[Utf8]", "Decimal", "Int64"]:
            assert coercer.coerce(None, dtype) is None
```

### Integration Tests

```python
# tests/integration/test_custom_field_coercion.py

def test_multi_enum_to_string_field(unit_task_with_specialty):
    """Verify multi_enum field coerces to string in UnitRow."""
    extractor = UnitExtractor(UNIT_SCHEMA, resolver)
    row = extractor.extract(unit_task_with_specialty)

    # specialty is multi_enum in Asana but Utf8 in schema
    assert isinstance(row.specialty, str)
    assert row.specialty == "Value1, Value2"


def test_empty_multi_enum_to_none(unit_task_without_specialty):
    """Verify empty multi_enum becomes None for string field."""
    extractor = UnitExtractor(UNIT_SCHEMA, resolver)
    row = extractor.extract(unit_task_without_specialty)

    assert row.specialty is None


def test_multi_enum_to_list_field(unit_task_with_products):
    """Verify multi_enum field stays as list when schema expects list."""
    extractor = UnitExtractor(UNIT_SCHEMA, resolver)
    row = extractor.extract(unit_task_with_products)

    # products is multi_enum and List[Utf8] in schema
    assert isinstance(row.products, list)
    assert row.products == ["Product A", "Product B"]
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing extraction | Low | High | Extensive unit tests, column_def is optional |
| Performance regression | Very Low | Low | Coercion is O(1), negligible overhead |
| Missing coercion case | Medium | Medium | Comprehensive test matrix, fallback passthrough |
| Schema/API type mismatch for new fields | Medium | Low | Log warnings, fail gracefully |

---

## ADRs

### ADR-0061: TypeCoercer as Stateless Service

**Status**: Proposed

**Context**: Need to centralize type coercion logic for custom field values that don't match schema expectations.

**Decision**: Implement `TypeCoercer` as a stateless class with a module-level singleton for convenience.

**Rationale**:
- Stateless design is inherently thread-safe
- Singleton avoids object creation overhead
- Class structure allows future extension (subclassing for custom coercion rules)
- Pure functions are easy to test

**Consequences**:
- Positive: Thread-safe, testable, single responsibility
- Negative: Another module to maintain (acceptable for SRP)

### ADR-0062: Schema-Aware Coercion via ColumnDef

**Status**: Proposed

**Context**: Coercion needs to know the target type, which is defined in the schema's `ColumnDef.dtype`.

**Decision**: Pass `ColumnDef` to resolver's `get_value()` as optional parameter.

**Rationale**:
- Schema is the source of truth for target types
- Avoids duplicating type information
- Backward compatible (optional parameter)
- Extractors already have access to `ColumnDef`

**Consequences**:
- Positive: Schema-driven, no hardcoded field names
- Negative: Slightly larger method signature (acceptable for clarity)

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/architecture/TDD-custom-field-type-coercion.md` | Pending |

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-02 | 1.0 | Architect | Initial TDD |
