# Technical Debt Backlog - QA Findings

**Version**: 1.0
**Date**: 2024-12-12
**Author**: Requirements Analyst
**Status**: Tracked for v0.2.1+

---

## Overview

This document categorizes 14 medium and low severity issues identified in the QA Adversarial Review. These issues do not block the v0.2.0 release but should be addressed in future releases for improved code quality, user experience, and maintainability.

**Classification**:
- **P3**: High-value improvements (address in v0.2.1)
- **P4**: Standard improvements (address in v0.2.2)
- **P5**: Polish items (address when convenient)

---

## Summary Table

| ID | Title | Severity | Category | Effort | Priority |
|----|-------|----------|----------|--------|----------|
| 1 | No idempotency documentation | MEDIUM | Documentation | V.Low | P5 |
| 3 | Unused project_gid parameter | MEDIUM | API Design | Low | P4 |
| 4 | Sync wrapper pattern inconsistency | MEDIUM | Code Quality | High | P3 |
| 6 | commit() doesn't close session | MEDIUM | Semantics | Low | P4 |
| 7 | Empty commit warns too much | MEDIUM | Logging/UX | V.Low | P5 |
| 13 | refresh() accessor state issue | MEDIUM | State Management | Medium | P3 |
| 16 | Accessor caching across refresh | MEDIUM | State Management | Medium | P3 |
| 8 | Numeric field names as GIDs | LOW | Edge Case | Low | P5 |
| 9 | PositioningConflictError not exported | LOW | Documentation | V.Low | P5 |
| 12 | Inconsistent async/sync naming | LOW | API Design | Medium | P4 |
| 15 | Type hints vs runtime mismatch | LOW | Type Safety | Low | P4 |
| 17 | KeyError messages not helpful | LOW | UX | Low | P4 |
| 18 | Empty field names allowed | LOW | Validation | V.Low | P5 |
| 19 | set vs remove semantics unclear | LOW | Documentation | V.Low | P5 |

---

## Medium Severity Issues

### ISSUE 1: No Idempotency Documentation for add_tag_async()

**Severity**: MEDIUM | **Category**: Documentation | **Effort**: V.Low | **Priority**: P5

**Problem**: `add_tag_async()` allows calling multiple times with the same tag. Each call queues a separate action. If the first succeeds, the second will get a 422 error from Asana. Users familiar with idempotent APIs (Stripe, AWS) expect this to be safe.

**Fix Approach**: Document explicitly that P1 direct methods (add_tag, remove_tag, etc.) are NOT idempotent. Alternatively, implement deduplication by checking pending_actions before appending.

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` (docstrings)

---

### ISSUE 3: move_to_section() Unused project_gid Parameter

**Severity**: MEDIUM | **Category**: API Design | **Effort**: Low | **Priority**: P4

**Problem**: Method signature includes `project_gid` parameter but never uses it. This confuses users who provide it thinking it's needed for validation.

**Fix Approach**: Either remove the parameter entirely (breaking change) or validate that the section belongs to the specified project before execution.

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` lines 673-721

---

### ISSUE 4: Sync Wrapper Pattern Inconsistency

**Severity**: MEDIUM | **Category**: Code Quality | **Effort**: High | **Priority**: P3

**Problem**: Three different patterns exist for wrapping async methods as sync:
1. Task methods: `def save(self): return sync_wrapper('save_async')(self.save_async)()`
2. TasksClient methods: `def add_tag(self): return self._add_tag_sync(task_gid, tag_gid)`
3. SaveSession methods: `def commit(self): return self._commit_sync()`

**Fix Approach**: Standardize on one pattern across the codebase. The SaveSession pattern (intermediate `_method_sync` function) is clearest and most explicit.

**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`

---

### ISSUE 6: SaveSession.commit() Doesn't Fully Close Session

**Severity**: MEDIUM | **Category**: Semantics | **Effort**: Low | **Priority**: P4

**Problem**: After calling `commit()`, session state is COMMITTED but not CLOSED. New operations can still be tracked, which may confuse users expecting `commit()` to finalize the batch.

**Fix Approach**: Either document this behavior clearly (multiple commits are supported) OR transition to CLOSED after commit if single-commit semantics are preferred.

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` line 561

---

### ISSUE 7: Empty commit() Logs WARNING (Too Noisy)

**Severity**: MEDIUM | **Category**: Logging/UX | **Effort**: V.Low | **Priority**: P5

**Problem**: Calling `commit()` with no tracked entities logs a WARNING. This is too noisy for normal usage patterns where users create a session, maybe add items conditionally, and always commit.

**Fix Approach**: Log at DEBUG or INFO level instead of WARNING.

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` lines 532-537

---

### ISSUE 13: Task.refresh() Accessor Data Consistency Issue

**Severity**: MEDIUM | **Category**: State Management | **Effort**: Medium | **Priority**: P3

**Problem**: `refresh_async()` clears `_modifications` dict but doesn't reset `_data` or recreate the accessor. After refresh, the accessor has stale `_data` that doesn't match the task's refreshed custom_fields.

**Fix Approach**: Either reset entire accessor (`self._custom_fields_accessor = None`) forcing recreation, or update `_data` to match refreshed custom_fields.

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` lines 244-245

---

### ISSUE 16: CustomFieldAccessor Caching Across Refresh/Serialize

**Severity**: MEDIUM | **Category**: State Management | **Effort**: Medium | **Priority**: P3

**Problem**: `Task.get_custom_fields()` caches accessor in `_custom_fields_accessor`. After `refresh()` or serialization, this cache can be stale or lost, but the accessor instance persists with old data.

**Fix Approach**: Clear accessor cache in `refresh_async()`, or make accessor creation idempotent by re-reading from current custom_fields.

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` lines 137-139

**Note**: Issues 13 and 16 are related and should be fixed together.

---

## Low Severity Issues

### ISSUE 8: Numeric Field Names Misinterpreted as GIDs

**Severity**: LOW | **Category**: Edge Case | **Effort**: Low | **Priority**: P5

**Problem**: `CustomFieldAccessor._resolve_gid()` checks `if name_or_gid.isdigit()` to detect GIDs. A field named "2024" (a year) would be misinterpreted as a GID.

**Fix Approach**: Use a longer numeric pattern (e.g., `len(name_or_gid) >= 12 and name_or_gid.isdigit()`) to better distinguish GIDs from field names. Asana GIDs are 15-19 digits.

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py` line 255

---

### ISSUE 9: PositioningConflictError Not Exported

**Severity**: LOW | **Category**: Documentation | **Effort**: V.Low | **Priority**: P5

**Problem**: `add_to_project()` and `move_to_section()` can raise `PositioningConflictError`, but it's not in the main exceptions module exports. Users won't know this exception exists without reading source.

**Fix Approach**: Export in `__all__` of exceptions module or re-export from main package.

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py` (add to `__all__`)

---

### ISSUE 12: Inconsistent Async/Sync Method Naming

**Severity**: LOW | **Category**: API Design | **Effort**: Medium | **Priority**: P4

**Problem**: Task has `save()` / `save_async()` but no `update()` / `update_async()`. TasksClient has both for every operation. Inconsistent API surface.

**Fix Approach**: If Task is meant to be mutable, consider adding `update()` / `update_async()` methods for consistency with client. Or document why the asymmetry exists.

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`

---

### ISSUE 15: Type Hints vs. Runtime Validation Mismatch

**Severity**: LOW | **Category**: Type Safety | **Effort**: Low | **Priority**: P4

**Problem**: Task model hints `projects: list[NameGid]` but accepts raw GID strings in initialization (from API responses). Type hint is aspirational but doesn't match actual behavior.

**Fix Approach**: Use `coerce=True` Pydantic config to automatically convert string GIDs to NameGid objects, or update type hint to `list[NameGid | str]`.

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` line 63

---

### ISSUE 17: KeyError Messages Not Helpful

**Severity**: LOW | **Category**: UX | **Effort**: Low | **Priority**: P4

**Problem**: `CustomFieldAccessor.__getitem__()` raises `KeyError(key)` with just the field name. Doesn't suggest available fields or help debugging.

**Fix Approach**: Include available field names in error message, or suggest using `.get()` method.

```python
raise KeyError(
    f"Custom field '{key}' not found. "
    f"Available fields: {', '.join(self._name_to_gid.keys())}"
)
```

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py` line 119

---

### ISSUE 18: Empty Field Names Allowed

**Severity**: LOW | **Category**: Validation | **Effort**: V.Low | **Priority**: P5

**Problem**: CustomFieldAccessor allows fields with empty names `""`. No validation prevents this edge case.

**Fix Approach**: Validate that field names are non-empty in `_build_index()`.

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py` lines 50-57

---

### ISSUE 19: Custom Field set() vs remove() Semantics Unclear

**Severity**: LOW | **Category**: Documentation | **Effort**: V.Low | **Priority**: P5

**Problem**: `set("Field", None)` and `remove("Field")` have identical behavior but different semantics. Documentation doesn't clarify the difference.

**Fix Approach**: Document which to use when in docstrings. Or merge into single method with `value=UNSET` sentinel for explicit removal.

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py` lines 59-99

---

## Priority Groupings

### P3 - Address in v0.2.1 (High Value)

| Issue | Title | Effort | Rationale |
|-------|-------|--------|-----------|
| 4 | Sync wrapper inconsistency | High | Code quality, maintainability |
| 13 | refresh() accessor state | Medium | Data consistency |
| 16 | Accessor caching | Medium | Data consistency (related to 13) |

**Total P3 Effort**: High (8-12 hours)

### P4 - Address in v0.2.2 (Standard)

| Issue | Title | Effort | Rationale |
|-------|-------|--------|-----------|
| 3 | Unused project_gid | Low | API clarity |
| 6 | commit() session state | Low | Semantic clarity |
| 12 | Async/sync naming | Medium | API consistency |
| 15 | Type hints mismatch | Low | Type safety |
| 17 | KeyError messages | Low | Developer UX |

**Total P4 Effort**: Medium (4-6 hours)

### P5 - Address When Convenient (Polish)

| Issue | Title | Effort | Rationale |
|-------|-------|--------|-----------|
| 1 | Idempotency docs | V.Low | Documentation |
| 7 | Empty commit warning | V.Low | Logging UX |
| 8 | Numeric field names | Low | Edge case |
| 9 | Error not exported | V.Low | Documentation |
| 18 | Empty field names | V.Low | Validation |
| 19 | set vs remove docs | V.Low | Documentation |

**Total P5 Effort**: Low (2-4 hours)

---

## Tracking

Issues will be tracked in the project's issue tracker with labels:
- `tech-debt`
- `qa-findings`
- Priority label (`P3`, `P4`, `P5`)
- Category label (`docs`, `api-design`, `code-quality`, etc.)

---

## Related Documents

- [QA Adversarial Review](/docs/validation/QA-ADVERSARIAL-REVIEW.md)
- [Triage Fixes Requirements](/docs/requirements/TRIAGE-FIXES-REQUIREMENTS.md)
- [Prompt 0](/docs/initiatives/qa-findings-triage-prompt-0.md)
