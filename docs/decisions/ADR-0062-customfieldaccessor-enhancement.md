# ADR-0062: CustomFieldAccessor Enhancement vs. Wrapper Class

**Status:** Accepted
**Date:** 2025-12-12
**Context:** Session 3 Architecture Design (PRD-SDKUX, P2)

---

## Problem

Priority 2 requires dictionary-style access to custom fields: `task.custom_fields["Priority"] = "High"` instead of `task.get_custom_fields().set("Priority", "High")`.

Two approaches:

1. **Enhance CustomFieldAccessor Directly:** Add `__getitem__`, `__setitem__` methods to existing class
   ```python
   class CustomFieldAccessor:
       def __getitem__(self, name_or_gid: str) -> Any:
           ...
       def __setitem__(self, name_or_gid: str, value: Any) -> None:
           ...
   ```

2. **Create Wrapper Class:** New `CustomFieldDict` wraps CustomFieldAccessor
   ```python
   class CustomFieldDict:
       def __init__(self, accessor: CustomFieldAccessor):
           self._accessor = accessor

       def __getitem__(self, name_or_gid: str) -> Any:
           return self._accessor.get(name_or_gid)
       def __setitem__(self, name_or_gid: str, value: Any) -> None:
           self._accessor.set(name_or_gid, value)
   ```

## Decision

Enhance **CustomFieldAccessor directly** with `__getitem__`, `__setitem__`, `__delitem__` methods.

No wrapper class needed.

```python
class CustomFieldAccessor:
    def __getitem__(self, name_or_gid: str) -> Any:
        """Get field by dict syntax."""
        result = self.get(name_or_gid, default=_MISSING)
        if result is _MISSING:
            raise KeyError(name_or_gid)
        return result

    def __setitem__(self, name_or_gid: str, value: Any) -> None:
        """Set field by dict syntax."""
        self.set(name_or_gid, value)

    def __delitem__(self, name_or_gid: str) -> None:
        """Delete field by dict syntax."""
        self.remove(name_or_gid)
```

## Rationale

### 1. Simpler Codebase
Adding 3 methods to existing class is easier than creating new class with delegation.

- Fewer files (no new CustomFieldDict)
- Fewer imports (no CustomFieldDict import)
- Less maintenance burden
- Easier to understand: One class, standard Python magic methods

**Comparison:**

Direct enhancement:
```python
def __getitem__(self, name_or_gid: str) -> Any:
    result = self.get(name_or_gid, default=_MISSING)
    if result is _MISSING:
        raise KeyError(name_or_gid)
    return result
```

Wrapper class adds:
```python
class CustomFieldDict:
    def __init__(self, accessor: CustomFieldAccessor, on_change: callable):
        self._accessor = accessor
        self._on_change = on_change

    def __getitem__(self, name_or_gid: str) -> Any:
        return self._accessor.get(name_or_gid)
    # ... plus __setitem__, __delitem__, possibly __len__, __iter__, ...
```

### 2. No Indirection
Wrapper adds one level of indirection (CustomFieldDict → CustomFieldAccessor). Direct enhancement is more direct.

When debugging:
- Direct: User sees CustomFieldAccessor methods directly
- Wrapper: User must trace through CustomFieldDict → CustomFieldAccessor

### 3. Proven Class Already
CustomFieldAccessor is already mature:

**Discovery Evidence (Lines 420-548 in DISCOVERY-SDKUX-001):**
- Already has `get()`, `set()`, `remove()` methods
- Already tracks changes in `_modifications` dict
- Already has `has_changes()` method
- Already handles type preservation in `_extract_value()`
- Already formats for API in `_format_value_for_api()`

**Why wrapper?** No reason. The class already does everything needed.

### 4. Consistency with Existing Code
CustomFieldAccessor already exists; users already access via `task.get_custom_fields()`. Adding `__getitem__` is natural extension.

Not:
```python
task.custom_fields_dict["Priority"] = "High"
```

But:
```python
task.custom_fields["Priority"] = "High"
```

Where `custom_fields` property returns same CustomFieldAccessor (now with dict methods).

### 5. Same Change Tracking Works
Both approaches use same underlying `_modifications` dict. No difference in behavior.

**With direct enhancement:**
```python
def __setitem__(self, name_or_gid: str, value: Any) -> None:
    self.set(name_or_gid, value)  # Modifies _modifications
```

**With wrapper:**
```python
def __setitem__(self, name_or_gid: str, value: Any) -> None:
    self._accessor.set(name_or_gid, value)  # Still modifies _modifications
```

No functional difference.

## Consequences

### Positive
- Fewer classes to maintain
- Simpler codebase
- Direct magic method support on CustomFieldAccessor
- Users can use dict syntax: `accessor["field"]` or `accessor.get("field")`
- No wrapper overhead
- Backward compatible: existing `accessor.get()` calls unchanged

### Negative
- CustomFieldAccessor gains 3 methods (minor responsibility increase)
- CustomFieldAccessor is now both accessor AND dict-like (but that's fine; it IS a dict-like interface)

### Neutral
- Same change tracking behavior
- Same error handling (KeyError for missing fields)
- Same type preservation

## Implementation

```python
class CustomFieldAccessor:
    """Access custom fields by name or GID, with dict-like interface."""

    def __init__(self, data: list[dict[str, Any]] | None = None, ...):
        self._data: list[dict[str, Any]] = list(data) if data else []
        self._modifications: dict[str, Any] = {}
        self._name_to_gid: dict[str, str] = {}
        self._build_index()

    # Existing methods (no changes)
    def get(self, name_or_gid: str, default: Any = None) -> Any:
        """Get field value by name or GID."""
        ...

    def set(self, name_or_gid: str, value: Any) -> None:
        """Set field value by name or GID."""
        self._modifications[gid] = value

    def remove(self, name_or_gid: str) -> None:
        """Remove field."""
        ...

    # New magic methods (added for dict syntax)
    def __getitem__(self, name_or_gid: str) -> Any:
        """Get field value using dict syntax: accessor["Priority"]

        Args:
            name_or_gid: Field name or GID

        Returns:
            Field value (type preserved: enum dict, number, text, date, etc.)

        Raises:
            KeyError: If field doesn't exist (consistent with dict behavior)

        Example:
            >>> value = accessor["Priority"]
            >>> if value is None:
            ...     # Handle optional field
        """
        result = self.get(name_or_gid, default=_MISSING)
        if result is _MISSING:
            raise KeyError(name_or_gid)
        return result

    def __setitem__(self, name_or_gid: str, value: Any) -> None:
        """Set field value using dict syntax: accessor["Priority"] = "High"

        Args:
            name_or_gid: Field name or GID
            value: New value (any type; accessor handles serialization)

        Example:
            >>> accessor["Priority"] = "High"  # Marks task dirty
            >>> accessor["Budget"] = 10000.0
        """
        self.set(name_or_gid, value)

    def __delitem__(self, name_or_gid: str) -> None:
        """Delete field using dict syntax: del accessor["Priority"]

        Args:
            name_or_gid: Field name or GID

        Raises:
            KeyError: If field doesn't exist
        """
        if self._resolve_gid(name_or_gid) is None:
            raise KeyError(name_or_gid)
        self.remove(name_or_gid)

    # Existing methods continued...
```

## Task Integration

In `Task` model, `custom_fields` property returns CustomFieldAccessor:

```python
class Task(AsanaResource):
    custom_fields: list[dict[str, Any]] | None = None
    _custom_fields_accessor: CustomFieldAccessor | None = PrivateAttr(default=None)

    @property
    def custom_fields(self) -> CustomFieldAccessor:
        """Dictionary-style access to custom fields.

        Returns CustomFieldAccessor with dict-like interface.

        Example:
            >>> task.custom_fields["Priority"]  # get
            >>> task.custom_fields["Priority"] = "High"  # set (marks dirty)
            >>> del task.custom_fields["Priority"]  # delete
        """
        if self._custom_fields_accessor is None:
            self._custom_fields_accessor = CustomFieldAccessor(self.custom_fields)
        return self._custom_fields_accessor
```

## Alternatives Considered

### Alternative A: Wrapper Class (CustomFieldDict)
```python
class CustomFieldDict:
    def __init__(self, accessor: CustomFieldAccessor):
        self._accessor = accessor

    def __getitem__(self, ...):
        return self._accessor.get(...)
```

**Rejected:** Unnecessary indirection. CustomFieldAccessor already does what's needed.

### Alternative B: No Dict Syntax Support
Keep current API:
```python
cf = task.get_custom_fields()
cf.set("Priority", "High")
```

**Rejected:** Doesn't meet P2 requirement. Users want `["Priority"] = "High"` syntax.

### Alternative C: Both (Support Both Syntaxes)
```python
# Old way (still works)
cf = task.get_custom_fields()
cf.set("Priority", "High")

# New way (also works)
task.custom_fields["Priority"] = "High"
```

**Chosen:** This is what direct enhancement provides. Both syntaxes work!

## Backward Compatibility

**Zero breaking changes:**
- `task.get_custom_fields()` still exists, works same
- `accessor.get("Priority")` still exists, works same
- `accessor.set("Priority", "High")` still exists, works same
- All existing code continues to work

**New syntax (addition):**
- `task.custom_fields["Priority"]` works (new)
- `accessor["Priority"]` works (new)

## Testing Strategy

### Get via Dict Syntax
```python
def test_getitem_returns_value():
    accessor = CustomFieldAccessor([
        {"gid": "1", "name": "Priority", "text_value": "High"}
    ])
    assert accessor["Priority"] == "High"

def test_getitem_missing_raises_key_error():
    accessor = CustomFieldAccessor([...])
    with pytest.raises(KeyError, match="NonexistentField"):
        accessor["NonexistentField"]
```

### Set via Dict Syntax
```python
def test_setitem_records_modification():
    accessor = CustomFieldAccessor([...])
    accessor["Priority"] = "Low"

    assert accessor._modifications[gid_for_priority] == "Low"
    assert accessor.has_changes()

def test_setitem_type_preservation():
    accessor = CustomFieldAccessor([...])

    # Enum
    accessor["Status"] = {"gid": "123", "name": "Done"}
    assert accessor["Status"]["name"] == "Done"

    # Number
    accessor["Budget"] = 10000.0
    assert accessor["Budget"] == 10000.0
```

### Delete via Dict Syntax
```python
def test_delitem_removes_field():
    accessor = CustomFieldAccessor([...])
    del accessor["Priority"]

    assert accessor.has_changes()
```

### Backward Compatibility
```python
def test_old_api_still_works():
    accessor = CustomFieldAccessor([...])

    # Old way
    value = accessor.get("Priority")
    accessor.set("Priority", "High")

    # New way
    value = accessor["Priority"]
    accessor["Priority"] = "High"

    # Both should work identically
```

## Decision Log

- **2025-12-12:** Architect chose direct enhancement for simplicity while maintaining backward compatibility
- **Blocking questions:** None (CustomFieldAccessor already proven in codebase per DISCOVERY-SDKUX-001)

---
