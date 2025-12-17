# ADR-0062: CustomFieldAccessor Enhancement vs. Wrapper

**Date:** 2025-12-12
**Status:** Approved
**Context:** SDK Usability Overhaul - Custom Fields (P2, Session 3)
**References:** PRD-SDKUX, DISCOVERY-SDKUX-001 (lines 420-548)

---

## Context and Problem

P2 (Custom Field Access) requires dictionary-style access to custom fields:

```python
# Desired
task.custom_fields["Priority"] = "High"
value = task.custom_fields["Priority"]
```

Currently, users must use method calls:

```python
# Current
task.get_custom_fields().set("Priority", "High")
value = task.get_custom_fields().get("Priority")
```

**Problem:** How should we implement dictionary syntax? Two Options:

1. **Enhance Existing CustomFieldAccessor**: Add `__getitem__()`, `__setitem__()` methods
2. **Create Wrapper Class**: New CustomFieldDict class wrapping CustomFieldAccessor

---

## Decision

**Enhance CustomFieldAccessor** - Add `__getitem__()` and `__setitem__()` methods directly.

### Implementation

```python
# In CustomFieldAccessor class
_MISSING = object()  # Sentinel for missing values

def __getitem__(self, name_or_gid: str) -> Any:
    """Get custom field value using dictionary syntax.

    Args:
        name_or_gid: Field name or GID

    Returns:
        Field value (type varies by field type)

    Raises:
        KeyError: If field doesn't exist (consistent with dict behavior)

    Example:
        >>> task.custom_fields["Priority"]
        "High"
    """
    result = self.get(name_or_gid, default=_MISSING)
    if result is _MISSING:
        raise KeyError(name_or_gid)
    return result

def __setitem__(self, name_or_gid: str, value: Any) -> None:
    """Set custom field value using dictionary syntax.

    Args:
        name_or_gid: Field name or GID
        value: New value (type depends on field type)

    Example:
        >>> task.custom_fields["Priority"] = "High"

    Side Effects:
        Marks CustomFieldAccessor as having changes (tracked by has_changes())
    """
    self.set(name_or_gid, value)
```

---

## Rationale

### Why Enhance (not wrap)?

1. **Simpler Design**
   - No new class to maintain
   - Existing CustomFieldAccessor has .get(), .set(), .remove()
   - Just add dict-like methods to same class

2. **Single Instance Model**
   - Currently: `task.get_custom_fields()` returns CustomFieldAccessor
   - Proposal: Same instance, now with dict methods
   - Simpler than: Creating new wrapper every call

3. **Backward Compatible**
   - Existing .get(), .set() unchanged
   - New __getitem__, __setitem__ are additions
   - Users can mix old and new: `.get("Priority")` and `["Priority"]`

4. **No Duplication**
   - Wrapper would duplicate logic
   - Enhancement delegates to existing methods

5. **Type Preservation Automatic**
   - Existing _extract_value() handles types
   - No new logic needed for dict access

6. **Change Tracking Works**
   - Existing _modifications dict tracks changes
   - __setitem__ calls .set(), which updates _modifications
   - No new tracking logic

### Why Not Wrapper?

1. **Duplication**
   ```python
   # Wrapper would duplicate all logic
   class CustomFieldDict:
       def __init__(self, accessor: CustomFieldAccessor):
           self._accessor = accessor

       def __getitem__(self, name):
           return self._accessor.get(name)

       def __setitem__(self, name, value):
           self._accessor.set(name, value)
   ```

2. **Multiple Instances**
   ```python
   # Every call creates new wrapper?
   task.custom_fields["Priority"] = "High"  # Which wrapper?
   ```

3. **Inheritance Complexity**
   - If we want CustomFieldDict to inherit from dict: Must override all dict methods
   - Better: Just enhance CustomFieldAccessor

4. **Not Necessary**
   - CustomFieldAccessor already exists with methods
   - Just add dunder methods

---

## Consequences

### Positive

1. **Simpler**: No new class, no duplication
2. **Backward Compatible**: Old .get/.set still work
3. **Intuitive**: Users can use either syntax: `.get("X")` or `["X"]`
4. **Type Safe**: Type preservation automatic
5. **Change Tracking**: Automatic via existing _modifications
6. **Natural**: Follows Python convention (dicts are always enhanceable)

### Negative

1. **Mixed Styles**: Users can write both `.get("X")` and `["X"]`
   - Mitigation: Document preferred style in integration guide
   - Not a breaking issue, just style preference

2. **Not Full Dict Interface**: Missing `__delitem__`, keys(), values(), etc.
   - Mitigation: Can add in future (P2.1)
   - MVP focus: get/set (read/write)

---

## Implementation Details

### File: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py`

1. **Add sentinel**
   ```python
   _MISSING = object()
   ```

2. **Add __getitem__** (~8 lines)
   - Call self.get(name_or_gid, default=_MISSING)
   - Raise KeyError if _MISSING returned

3. **Add __setitem__** (~4 lines)
   - Call self.set(name_or_gid, value)

**No other changes needed** - existing change tracking, type preservation work automatically

### Integration with Task

No changes to Task model - CustomFieldAccessor enhancement is transparent:

```python
task = await client.tasks.get(task_gid)
task.custom_fields["Priority"] = "High"  # Uses new __setitem__
value = task.custom_fields["Priority"]   # Uses new __getitem__
await task.save_async()  # P4 feature persists changes
```

### Type Preservation Chain

1. Asana API stores in type-specific keys (text_value, number_value, enum_value)
2. CustomFieldAccessor._extract_value() reads appropriate key
3. __getitem__ returns extracted value (preserving type)
4. __setitem__ delegates to .set() which updates _modifications
5. Task.save_async() includes modifications via SaveSession

---

## Verification

### Tests Required

1. **__getitem__**
   - Returns value for existing field
   - Raises KeyError for missing field
   - Type preservation (enum, number, date)

2. **__setitem__**
   - Sets value and marks dirty
   - Works with name or GID
   - Type preserved on round-trip

3. **Backward Compatibility**
   - Existing .get() still works
   - Existing .set() still works
   - Mixed usage: `.get()` and `["X"]` in same code

4. **Integration with Save**
   - Custom field changes via __setitem__ persisted in save
   - Changes detected by SaveSession.ChangeTracker

---

## Alternatives Considered

### Alternative 1: Wrapper Class

```python
# NOT CHOSEN
class CustomFieldDict:
    def __init__(self, accessor: CustomFieldAccessor):
        self._accessor = accessor

    def __getitem__(self, name):
        result = self._accessor.get(name, default=object())
        if result is object():
            raise KeyError(name)
        return result

    def __setitem__(self, name, value):
        self._accessor.set(name, value)
```

**Rejected because:**
- Unnecessary duplication
- Creates new instance every access: `task.custom_fields["Priority"]`
  - Creates wrapper → accesses _accessor → returns value
- More complex to maintain

### Alternative 2: Separate Dict Property

```python
# NOT CHOSEN
class Task(AsanaResource):
    @property
    def custom_fields_dict(self) -> CustomFieldDict:
        return CustomFieldDict(self.custom_fields)

# Usage
task.custom_fields_dict["Priority"] = "High"
```

**Rejected because:**
- Adds new property
- Users confused: two ways to access custom fields
- Still requires new wrapper class

---

## Decision Record

**Decision:** Enhance CustomFieldAccessor with __getitem__ and __setitem__

**Decided by:** Architect (Session 3)

**Rationale:** Simplest design, backward compatible, leverages existing infrastructure

**Implementation Timeline:** Session 5a (P2 Priority)

**Future Extensions:** Can add __delitem__, keys(), values() in P2.1 if needed

---

## Related ADRs

- ADR-0061: Implicit SaveSession Lifecycle (Task.save_async uses custom field changes)
- ADR-0059: Direct Methods vs SaveSession Actions (Custom fields flow through save)

---
