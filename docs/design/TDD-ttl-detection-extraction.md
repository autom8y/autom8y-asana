# TDD: TTL Detection Extraction (DRY Fix)

> Technical Design Document for extracting duplicated `_detect_entity_type()` utility.

## Metadata

| Field | Value |
|-------|-------|
| **Status** | Proposed |
| **Date** | 2026-01-04 |
| **Related ADRs** | ADR-0059 (SRP decomposition) |
| **Complexity Level** | SCRIPT |

---

## Overview

DRY violation: Two nearly identical `_detect_entity_type()` methods exist in:
1. `src/autom8_asana/clients/task_ttl.py:101-127`
2. `src/autom8_asana/dataframes/builders/task_cache.py:424-450`

Both perform the same operation:
- Accept `dict[str, Any]` task data
- Lazy-import `Task` model and `detect_entity_type` function (circular import avoidance)
- Create temporary `Task` via `model_validate()`
- Return `entity_type.value` string or `None` on any failure

---

## Target Module

**Location**: `src/autom8_asana/models/business/detection/facade.py`

**Rationale**:
- This module already contains `detect_entity_type()` which the utility wraps
- Adding the dict-based variant alongside the Task-based function maintains cohesion
- Avoids creating a new module for a single function

---

## Function Signature

```python
def detect_entity_type_from_dict(data: dict[str, Any]) -> str | None:
    """Detect entity type from raw task data dict.

    Convenience wrapper for TTL resolution and cache builders that work with
    raw dicts before Task model instantiation. Uses lazy imports to avoid
    circular dependencies.

    Args:
        data: Raw task data dict (as returned by Asana API).

    Returns:
        Entity type value string (e.g., "business", "contact") or None
        if detection fails or model validation fails.

    Example:
        >>> entity_type = detect_entity_type_from_dict({"gid": "123", "name": "Contacts"})
        >>> if entity_type:
        ...     ttl = DEFAULT_ENTITY_TTLS.get(entity_type.lower(), DEFAULT_TTL)
    """
```

---

## Before/After Contracts

### RF-001: TaskTTLResolver._detect_entity_type

**Before State** (`src/autom8_asana/clients/task_ttl.py:101-127`):
```python
def _detect_entity_type(self, data: dict[str, Any]) -> str | None:
    """Detect entity type from task data."""
    try:
        from autom8_asana.models import Task as TaskModel
        from autom8_asana.models.business.detection import detect_entity_type

        temp_task = TaskModel.model_validate(data)
        result = detect_entity_type(temp_task)
        if result and result.entity_type:
            return result.entity_type.value
        return None
    except ImportError:
        return None
    except Exception:
        return None
```

**After State**:
```python
def _detect_entity_type(self, data: dict[str, Any]) -> str | None:
    """Detect entity type from task data."""
    from autom8_asana.models.business.detection import detect_entity_type_from_dict
    return detect_entity_type_from_dict(data)
```

**Invariants**:
- Same return type: `str | None`
- Same error handling: returns `None` on any failure
- Same lazy import semantics (now delegated to shared function)

---

### RF-002: TaskCacheCoordinator._detect_entity_type

**Before State** (`src/autom8_asana/dataframes/builders/task_cache.py:424-450`):
```python
def _detect_entity_type(self, data: dict[str, Any]) -> str | None:
    """Detect entity type from task data."""
    try:
        from autom8_asana.models import Task as TaskModel
        from autom8_asana.models.business.detection import detect_entity_type

        temp_task = TaskModel.model_validate(data)
        result = detect_entity_type(temp_task)
        if result and result.entity_type:
            return result.entity_type.value
        return None
    except ImportError:
        return None
    except Exception:
        return None
```

**After State**:
```python
def _detect_entity_type(self, data: dict[str, Any]) -> str | None:
    """Detect entity type from task data."""
    from autom8_asana.models.business.detection import detect_entity_type_from_dict
    return detect_entity_type_from_dict(data)
```

**Invariants**:
- Same return type: `str | None`
- Same error handling: returns `None` on any failure
- Same lazy import semantics

---

## Migration Strategy

### Phase 1: Add Shared Utility (1 edit)

**File**: `src/autom8_asana/models/business/detection/facade.py`

**Action**: Add `detect_entity_type_from_dict()` function after line 60 (`__all__` declaration), include in `__all__` exports.

**Implementation**:
```python
def detect_entity_type_from_dict(data: dict[str, Any]) -> str | None:
    """Detect entity type from raw task data dict.

    Convenience wrapper for TTL resolution and cache builders that work with
    raw dicts before Task model instantiation. Uses lazy imports to avoid
    circular dependencies at module load time.

    Args:
        data: Raw task data dict (as returned by Asana API).

    Returns:
        Entity type value string (e.g., "business", "contact") or None
        if detection fails or model validation fails.
    """
    try:
        from autom8_asana.models import Task as TaskModel

        temp_task = TaskModel.model_validate(data)
        result = detect_entity_type(temp_task)
        if result and result.entity_type:
            return result.entity_type.value
        return None
    except ImportError:
        return None
    except Exception:
        return None
```

**Note**: Lazy import for `Task` model only; `detect_entity_type` is already in scope since we are inside `facade.py`.

### Phase 2: Update Callers (2 edits)

1. **File**: `src/autom8_asana/clients/task_ttl.py`
   - Replace `_detect_entity_type()` method body with delegation to `detect_entity_type_from_dict`

2. **File**: `src/autom8_asana/dataframes/builders/task_cache.py`
   - Replace `_detect_entity_type()` method body with delegation to `detect_entity_type_from_dict`

---

## Verification Criteria

1. **Unit Tests Pass**:
   ```bash
   pytest tests/unit/clients/test_task_ttl.py -v
   pytest tests/unit/dataframes/builders/test_task_cache.py -v
   ```

2. **Detection Tests Pass**:
   ```bash
   pytest tests/unit/models/business/detection/ -v
   ```

3. **No Import Errors**:
   ```bash
   python -c "from autom8_asana.clients.task_ttl import TaskTTLResolver"
   python -c "from autom8_asana.dataframes.builders.task_cache import TaskCacheCoordinator"
   ```

4. **Export Verification**:
   ```bash
   python -c "from autom8_asana.models.business.detection import detect_entity_type_from_dict; print('OK')"
   ```

---

## Rollback

Single commit for all three edits. Revert reverts everything.

If issues arise post-merge:
```bash
git revert <commit-sha>
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular import introduced | Low | High | Lazy import pattern preserved; same pattern as before |
| Behavior divergence | None | N/A | Exact same logic extracted, no semantic changes |
| Test coverage gap | Low | Medium | Existing tests cover both callers; add explicit test for shared function |

**Overall Risk**: LOW - Mechanical extraction with no semantic changes.
