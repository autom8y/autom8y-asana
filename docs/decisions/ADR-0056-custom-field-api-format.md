# ADR-0056: Custom Field API Format Conversion

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-12
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-SDKDEMO, ADR-0030 (Custom Field Typing), ADR-0034 (Dynamic Custom Field Resolution)

## Context

BUG-2 identified that `CustomFieldAccessor.to_list()` produces a format incompatible with the Asana API for task updates.

### Current Output (BUG)

```python
# custom_field_accessor.py to_list() produces:
[{"gid": "123456", "value": "High"}, {"gid": "789012", "value": 1000}]
```

### API Required Format

```json
{"custom_fields": {"123456": "High", "789012": 1000}}
```

The Asana API expects custom field updates as a **dict mapping field GID to value**, not an array of objects.

### Data Flow Analysis

The bug manifests through this path:
1. `Task.model_dump()` calls `self._custom_fields_accessor.to_list()` when changes exist (task.py:155)
2. `SavePipeline._build_payload()` uses `entity.model_dump()` to build API payload (pipeline.py:355)
3. Payload sent to batch API with wrong format
4. API rejects or ignores the malformed custom_fields

### Type-Specific Value Requirements

The API expects different value formats per field type:

| Field Type | API Value Format | Example |
|------------|-----------------|---------|
| Text | string | `"High Priority"` |
| Number | number | `1000.50` |
| Enum | option GID string | `"1234567890"` |
| Multi-enum | array of option GIDs | `["111", "222"]` |
| People | array of user GIDs | `["333", "444"]` |
| Date | date object | `{"date": "2024-12-31"}` |

### Forces at Play

1. **Backward compatibility**: `to_list()` may be used elsewhere expecting array format
2. **Single responsibility**: CustomFieldAccessor should handle both reading and writing formats
3. **Minimal change**: Fix should be localized, not require widespread changes
4. **Type safety**: Values must be correctly formatted per field type
5. **Performance**: Avoid unnecessary conversions

## Decision

**Add a new `to_api_dict()` method to CustomFieldAccessor** that produces the correct API format. Modify `Task.model_dump()` to use this method instead of `to_list()`.

```python
# CustomFieldAccessor new method
def to_api_dict(self) -> dict[str, Any]:
    """Convert to API-compatible dict format for task updates.

    Per ADR-0056: API expects {"gid": value} mapping, not array.

    Returns:
        Dict mapping field GID to value: {"123456": "High", ...}
    """
    result: dict[str, Any] = {}
    for gid, value in self._modifications.items():
        result[gid] = self._normalize_value(value)
    return result
```

**Keep `to_list()` unchanged** for backward compatibility with any code that expects the array format.

## Rationale

### Why Not Modify `to_list()`?

Option A suggested modifying `to_list()` to return dict format. Rejected because:

1. **Breaking change**: Existing code may depend on array format
2. **Semantic confusion**: "to_list" implies returning a list, not dict
3. **Unpredictable impact**: May break dataframe, cache, or display code

### Why Not Convert in Pipeline?

Option C suggested converting format in pipeline/tracker layer. Rejected because:

1. **Wrong layer**: Pipeline shouldn't know about custom field internals
2. **Code duplication**: Same conversion logic would be needed anywhere custom fields are sent
3. **Harder to test**: Conversion logic buried in complex pipeline code

### Why a New Method?

1. **Clean separation**: `to_list()` for reading/display, `to_api_dict()` for writing
2. **Self-documenting**: Method name indicates purpose
3. **Testable**: Simple method with clear input/output
4. **Backward compatible**: No changes to existing `to_list()` callers

## Implementation Specification

### File: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py`

**Change 1**: Add `to_api_dict()` method after `to_list()` (around line 126)

```python
    def to_api_dict(self) -> dict[str, Any]:
        """Convert modifications to API-compatible dict format.

        Per ADR-0056: Asana API expects custom_fields as a dict mapping
        field GID to value, not an array of objects.

        Only includes modified fields (not unchanged fields from original data).

        Returns:
            Dict of {field_gid: value} for API payload.

        Example:
            >>> accessor.set("Priority", "High")  # GID: 123456
            >>> accessor.set("MRR", 1000)         # GID: 789012
            >>> accessor.to_api_dict()
            {"123456": "High", "789012": 1000}
        """
        result: dict[str, Any] = {}
        for gid, value in self._modifications.items():
            result[gid] = self._normalize_value_for_api(value)
        return result

    def _normalize_value_for_api(self, value: Any) -> Any:
        """Normalize a value for API submission.

        Per ADR-0056: Handles type-specific value formatting.

        Args:
            value: The value to normalize.

        Returns:
            API-compatible value.
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

        # Text, number, date: return as-is
        return value
```

### File: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`

**Change 1**: Modify `model_dump()` to use `to_api_dict()` (around line 155)

Replace:
```python
            data["custom_fields"] = self._custom_fields_accessor.to_list()
```

With:
```python
            data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
```

### Method Signatures

**New method** in `CustomFieldAccessor`:
```python
def to_api_dict(self) -> dict[str, Any]:
    """Convert modifications to API-compatible dict format."""

def _normalize_value_for_api(self, value: Any) -> Any:
    """Normalize a value for API submission."""
```

**Unchanged method**:
```python
def to_list(self) -> list[dict[str, Any]]:
    """Convert to array format (unchanged for backward compatibility)."""
```

## Alternatives Considered

### Alternative A: Modify to_list() Return Type

**Description**: Change `to_list()` to return dict instead of list

**Pros**:
- Single method
- No new API surface

**Cons**:
- Breaking change to existing callers
- Method name becomes misleading ("to_list" returns dict)
- Requires audit of all to_list() usages

**Why not chosen**: Breaking change risk outweighs simplicity benefit

### Alternative B: Add Format Parameter

**Description**: `to_list(format="list"|"dict")` parameter

**Pros**:
- Single method with flexibility
- Backward compatible default

**Cons**:
- Awkward API ("to_list" can return dict)
- Runtime format switching adds complexity
- Harder to type hint correctly

**Why not chosen**: Separate methods are cleaner than format parameter

### Alternative C: Convert in Pipeline

**Description**: Pipeline converts `to_list()` output to dict format

**Pros**:
- No changes to CustomFieldAccessor
- Centralized conversion

**Cons**:
- Wrong abstraction layer
- Pipeline shouldn't know custom field internals
- Duplicated if custom fields used elsewhere
- Harder to unit test

**Why not chosen**: Violates separation of concerns

## Consequences

### Positive

1. **Correct API format**: Custom field updates will work correctly
2. **Backward compatible**: `to_list()` unchanged for existing callers
3. **Self-documenting**: Clear method names indicate purpose
4. **Type-aware**: Handles enum GID extraction automatically

### Negative

1. **Two methods**: Developers must know when to use which
2. **Additional code**: New method adds to class size

### Neutral

1. **Only modifications sent**: `to_api_dict()` only includes modified fields, which is correct for minimal payloads
2. **No change to reading**: Getting field values unchanged

## Test Verification

After implementation, verify:

1. **Dict format**: `to_api_dict()` returns `{gid: value}` dict, not array
2. **Text fields**: String value passed through unchanged
3. **Number fields**: Numeric value passed through unchanged
4. **Enum fields**: If value is `{"gid": "123", "name": "High"}`, returns `"123"`
5. **Multi-enum fields**: If value is `[{"gid": "1"}, {"gid": "2"}]`, returns `["1", "2"]`
6. **People fields**: If value is list of user dicts, returns list of GIDs
7. **Null/removal**: `None` value passed through as `None`
8. **model_dump integration**: `Task.model_dump()` produces correct format when custom fields modified
9. **to_list unchanged**: `to_list()` still returns array format

## Compliance

### Enforcement

- **Unit tests**: Test `to_api_dict()` output format for all field types
- **Integration test**: Demo script should successfully update custom fields
- **Type checking**: mypy validates return type `dict[str, Any]`

### Documentation

- Add docstring explaining when to use `to_api_dict()` vs `to_list()`
- Update any examples showing custom field updates
