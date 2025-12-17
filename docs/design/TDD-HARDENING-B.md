# TDD: Custom Field Unification (Initiative B)

## Metadata
- **TDD ID**: TDD-HARDENING-B
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-16
- **Last Updated**: 2025-12-16
- **PRD Reference**: [PRD-HARDENING-B](/docs/requirements/PRD-HARDENING-B.md)
- **Discovery Reference**: [DISCOVERY-HARDENING-B](/docs/initiatives/DISCOVERY-HARDENING-B.md)
- **Related TDDs**: TDD-TRIAGE-FIXES (System 3 snapshot), TDD-0011 (SaveSession actions)
- **Related ADRs**: [ADR-0074](/docs/decisions/ADR-0074-unified-custom-field-tracking.md) (authoritative system), ADR-0067 (snapshot detection), ADR-0056 (API format)

## Overview

This TDD defines the technical design for unifying the three custom field change tracking systems into one authoritative system (CustomFieldAccessor), with proper reset behavior after successful SaveSession commit. The design introduces a coordinated reset mechanism where SaveSession orchestrates clearing accessor modifications and updating Task snapshots after each successful entity commit.

## Requirements Summary

From PRD-HARDENING-B:

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | Clear accessor `_modifications` after successful commit | Must |
| FR-002 | Update `_original_custom_fields` snapshot after commit | Must |
| FR-003 | Add `custom_fields_editor()` method alias | Must |
| FR-007 | No duplicate API calls on multiple commits | Must |
| FR-008 | Entity reused across sessions has clean state | Must |
| FR-009 | Reset only on success, not failure | Must |
| FR-010 | Business layer property setters continue working | Must |

## System Context

### Current Architecture (Three Systems)

```
                    +------------------+
                    |   SaveSession    |
                    +--------+---------+
                             |
              commit_async() |
                             v
                    +------------------+
                    |  ChangeTracker   |  <-- System 1: Snapshot comparison
                    +--------+---------+
                             |
                 mark_clean()|-- updates _snapshots[entity]
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
         X NOT CLEARED                           X NOT UPDATED
```

### Target Architecture (Unified Reset)

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

## Design

### Component Architecture

| Component | Responsibility | Changes |
|-----------|----------------|---------|
| **SaveSession** | Orchestrates commit and reset coordination | Add `_reset_custom_field_tracking()` call after successful commit |
| **Task** | Provides encapsulated reset method | Add `reset_custom_field_tracking()` and `custom_fields_editor()` |
| **CustomFieldAccessor** | Tracks modifications | No changes (already has `clear_changes()`) |
| **ChangeTracker** | Snapshot comparison | No changes |

### Component Details

#### 1. SaveSession Enhancements

**File**: `/src/autom8_asana/persistence/session.py`

**Change**: Add reset hook in the success loop after `mark_clean()`.

```python
async def commit_async(self) -> SaveResult:
    """Execute all pending changes (async)."""
    # ... existing code ...

    # Phase 1: Execute CRUD operations and actions
    crud_result, action_results = await self._pipeline.execute_with_actions(...)

    # ... existing action/cascade handling ...

    # Reset state for successful entities (FR-CHANGE-009)
    for entity in crud_result.succeeded:
        self._tracker.mark_clean(entity)  # System 1 reset (existing)
        self._reset_custom_field_tracking(entity)  # NEW: Systems 2 & 3 reset

    # ... rest of method ...
```

**New Method**:

```python
def _reset_custom_field_tracking(self, entity: AsanaResource) -> None:
    """Reset custom field tracking state after successful commit.

    Per ADR-0074: SaveSession coordinates reset across all tracking systems.

    Args:
        entity: Successfully committed entity.
    """
    # Only Task has custom fields
    if hasattr(entity, 'reset_custom_field_tracking'):
        entity.reset_custom_field_tracking()
```

**Design Rationale**:
- Uses `hasattr()` check instead of `isinstance()` for duck typing
- Allows future entity types with custom fields to participate
- Minimal coupling to Task internals

#### 2. Task Model Enhancements

**File**: `/src/autom8_asana/models/task.py`

**New Methods**:

```python
def custom_fields_editor(self) -> CustomFieldAccessor:
    """Get custom fields editor for reading and writing field values.

    Returns accessor for fluent API access to custom fields.
    Preferred over deprecated get_custom_fields() method.

    Returns:
        CustomFieldAccessor instance (cached for this task).

    Example:
        editor = task.custom_fields_editor()
        editor.set("Priority", "High")
        value = editor.get("Status")
    """
    return self._get_or_create_accessor()

def get_custom_fields(self) -> CustomFieldAccessor:
    """Get custom fields accessor.

    .. deprecated:: 1.0
        Use :meth:`custom_fields_editor` instead. This method will be
        removed in a future major version.
    """
    import warnings
    warnings.warn(
        "get_custom_fields() is deprecated. Use custom_fields_editor() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return self._get_or_create_accessor()

def _get_or_create_accessor(self) -> CustomFieldAccessor:
    """Internal: Get or create accessor instance."""
    if self._custom_fields_accessor is None:
        self._custom_fields_accessor = CustomFieldAccessor(
            self.custom_fields, strict=False
        )
    return self._custom_fields_accessor

def reset_custom_field_tracking(self) -> None:
    """Reset custom field tracking state after successful commit.

    Per ADR-0074: Called by SaveSession after successful entity commit.
    Clears accessor modifications (System 2) and updates snapshot (System 3).

    This method is idempotent - safe to call multiple times.
    """
    # System 2: Clear accessor modifications
    if self._custom_fields_accessor is not None:
        self._custom_fields_accessor.clear_changes()

    # System 3: Update snapshot to current state
    self._update_custom_fields_snapshot()

def _update_custom_fields_snapshot(self) -> None:
    """Update the custom fields snapshot to current state.

    Per FR-002: Synchronize System 3 snapshot after commit.
    """
    import copy
    if self.custom_fields is not None:
        self._original_custom_fields = copy.deepcopy(self.custom_fields)
    else:
        self._original_custom_fields = None
```

**Design Rationale**:
- `reset_custom_field_tracking()` is public for testability and explicit intent
- Internal methods prefixed with `_` for implementation details
- Idempotent design - safe for repeated calls
- Separate `_update_custom_fields_snapshot()` allows future reuse

#### 3. CustomFieldAccessor (No Changes)

The accessor already has `clear_changes()` method:

```python
def clear_changes(self) -> None:
    """Clear all pending modifications."""
    self._modifications.clear()
```

No changes required. This method is called by `Task.reset_custom_field_tracking()`.

### Data Flow

#### Sequence Diagram: Successful Commit

```
User             SaveSession        ChangeTracker      Task           Accessor
  |                  |                   |              |                |
  | commit_async()   |                   |              |                |
  |----------------->|                   |              |                |
  |                  | execute_with_actions()           |                |
  |                  |--------------------              |                |
  |                  |<-------------------              |                |
  |                  |                   |              |                |
  |                  | [FOR EACH SUCCESS]|              |                |
  |                  |                   |              |                |
  |                  | mark_clean(task)  |              |                |
  |                  |------------------>|              |                |
  |                  |                   | update snapshot              |
  |                  |                   |------------->|                |
  |                  |                   |              |                |
  |                  | _reset_custom_field_tracking(task)               |
  |                  |------------------------------>|                |
  |                  |                   |              |                |
  |                  |                   | reset_custom_field_tracking()|
  |                  |                   |              |                |
  |                  |                   |              | clear_changes()|
  |                  |                   |              |--------------->|
  |                  |                   |              |                |
  |                  |                   |              | _update_snapshot()
  |                  |                   |              |----            |
  |                  |                   |              |<---            |
  |                  |                   |              |                |
  | SaveResult       |                   |              |                |
  |<-----------------|                   |              |                |
```

#### Sequence Diagram: Cross-Session Flow (FR-008)

```
User             Session1           Session2           Task           Accessor
  |                  |                   |              |                |
  | [Session 1]      |                   |              |                |
  | track(task)      |                   |              |                |
  |----------------->|                   |              |                |
  |                  |                   |              |                |
  | set("Priority", "High")             |              |                |
  |--------------------------------------------->|--------------->|
  |                  |                   |              |                |
  | commit_async()   |                   |              |                |
  |----------------->|                   |              |                |
  |                  | [API call]        |              |                |
  |                  | [mark_clean]      |              |                |
  |                  | [_reset_custom_field_tracking]  |                |
  |                  |------------------------------>|--------------->|
  |                  |                   |              | clear_changes()|
  |                  |                   |              |<---------------|
  | SaveResult(ok)   |                   |              |                |
  |<-----------------|                   |              |                |
  |                  |                   |              |                |
  | [Session 2]      |                   |              |                |
  | track(task)      |                   |              |                |
  |---------------------------------->|              |                |
  |                  |                   | capture snapshot             |
  |                  |                   |------------->|                |
  |                  |                   |              |                |
  | commit_async()   |                   |              |                |
  |---------------------------------->|              |                |
  |                  |                   | get_dirty_entities()         |
  |                  |                   |------------->|                |
  |                  |                   |              | has_changes()? |
  |                  |                   |              |--------------->|
  |                  |                   |              |<------ False   |
  |                  |                   |<-- no dirty  |                |
  |                  |                   |              |                |
  | SaveResult(empty)|                   | NO API CALL  |                |
  |<----------------------------------|              |                |
```

#### Sequence Diagram: Partial Failure (FR-009)

```
User             SaveSession        Task1(ok)        Task2(fail)     Accessor1    Accessor2
  |                  |                   |              |                |             |
  | commit_async()   |                   |              |                |             |
  |----------------->|                   |              |                |             |
  |                  | batch execute     |              |                |             |
  |                  |------------------>|              |                |             |
  |                  |                   | API OK       |                |             |
  |                  |<------------------|              |                |             |
  |                  |                   |              |                |             |
  |                  |-------------------------------->|                |             |
  |                  |                   |              | API FAIL       |             |
  |                  |<--------------------------------|                |             |
  |                  |                   |              |                |             |
  |                  | [SUCCESS: Task1]  |              |                |             |
  |                  | mark_clean(task1) |              |                |             |
  |                  |------------------>|              |                |             |
  |                  | reset(task1)      |              |                |             |
  |                  |------------------>|--------------------->|             |
  |                  |                   |              |        clear() |             |
  |                  |                   |              |                |             |
  |                  | [FAIL: Task2]     |              |                |             |
  |                  | (NO reset)        |              |                |             |
  |                  |                   |              |                | RETAINS     |
  |                  |                   |              |                | _modifications
  |                  |                   |              |                |             |
  | SaveResult       |                   |              |                |             |
  | (partial=True)   |                   |              |                |             |
  |<-----------------|                   |              |                |             |
```

### API Contracts

#### Task Public Interface Additions

```python
class Task(AsanaResource):
    # New public method (FR-003)
    def custom_fields_editor(self) -> CustomFieldAccessor:
        """Get custom fields editor for reading and writing field values."""
        ...

    # Existing method - now deprecated
    def get_custom_fields(self) -> CustomFieldAccessor:
        """[DEPRECATED] Use custom_fields_editor() instead."""
        ...

    # New public method for reset coordination (ADR-0074)
    def reset_custom_field_tracking(self) -> None:
        """Reset custom field tracking state after successful commit."""
        ...
```

#### SaveSession Internal Interface

```python
class SaveSession:
    # New private method
    def _reset_custom_field_tracking(self, entity: AsanaResource) -> None:
        """Reset custom field tracking state after successful commit."""
        ...
```

### Error Handling

#### Partial Batch Failure

Per FR-009, reset occurs only for successful entities:

```python
# In SaveSession.commit_async()
for entity in crud_result.succeeded:  # Only iterate succeeded
    self._tracker.mark_clean(entity)
    self._reset_custom_field_tracking(entity)

# Failed entities retain their state
# crud_result.failed entities are NOT reset
```

#### Retry Scenarios

When a failed commit is retried:

1. **Accessor state preserved**: `_modifications` still contains pending changes
2. **Snapshot state preserved**: `_original_custom_fields` unchanged
3. **ChangeTracker state**: Entity still shows as MODIFIED (not reset)
4. **Retry works**: Same changes will be detected and sent

```python
# Example: Retry after failure
result1 = await session.commit_async()  # Fails for task1
assert result1.partial

# Task1 still has changes
assert task1.custom_fields_editor().has_changes()  # True

# Retry (or fix issue and retry)
result2 = await session.commit_async()  # Succeeds this time
assert result2.success

# Now task1 is clean
assert not task1.custom_fields_editor().has_changes()  # False
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Authoritative system | CustomFieldAccessor | Intended public API; explicit change tracking | ADR-0074 |
| Reset coordination | SaveSession | Knows success/failure; existing reset point | ADR-0074 |
| Access pattern | Public method on Task | Encapsulation; testability | ADR-0074 |
| Reset timing | Per-entity in success loop | Handles partial failure correctly | ADR-0074 |
| Method detection | `hasattr()` check | Duck typing; extensible | - |
| Deprecation approach | Warning, not removal | Backward compatibility; PRD requirement | - |

## Complexity Assessment

**Level**: Module

**Justification**:
- Changes span 2 files (SaveSession, Task)
- No new components or services
- Simple method additions
- Clear API surface
- No infrastructure changes
- Low risk of cascading effects

This is NOT Script-level because:
- Multiple files involved
- Interface contract changes
- Deprecation concerns

This is NOT Service-level because:
- No new services
- No external dependencies
- No operational concerns

## Implementation Plan

### Phase 1: Core Reset Mechanism (Must Have)

| Step | Deliverable | Dependencies | Estimate |
|------|-------------|--------------|----------|
| 1.1 | `Task.reset_custom_field_tracking()` method | None | 15 min |
| 1.2 | `Task._update_custom_fields_snapshot()` method | 1.1 | 10 min |
| 1.3 | `SaveSession._reset_custom_field_tracking()` method | 1.1 | 10 min |
| 1.4 | Hook in `SaveSession.commit_async()` success loop | 1.3 | 10 min |
| 1.5 | Unit tests for reset behavior | 1.1-1.4 | 30 min |

### Phase 2: Naming Convention (Must Have)

| Step | Deliverable | Dependencies | Estimate |
|------|-------------|--------------|----------|
| 2.1 | `Task._get_or_create_accessor()` extraction | None | 10 min |
| 2.2 | `Task.custom_fields_editor()` method | 2.1 | 10 min |
| 2.3 | Deprecation warning in `get_custom_fields()` | 2.1, 2.2 | 10 min |
| 2.4 | Unit tests for new method and deprecation | 2.2, 2.3 | 20 min |

### Phase 3: Integration Testing

| Step | Deliverable | Dependencies | Estimate |
|------|-------------|--------------|----------|
| 3.1 | Test: No duplicate API calls | 1.* | 20 min |
| 3.2 | Test: Cross-session clean state | 1.* | 20 min |
| 3.3 | Test: Partial failure preserves state | 1.* | 20 min |
| 3.4 | Test: Business layer unaffected | 2.* | 15 min |

**Total Estimate**: ~3 hours

### Migration Strategy

No migration required. Changes are additive and backward-compatible:

1. `get_custom_fields()` continues to work (with deprecation warning)
2. Existing code using accessor is unaffected
3. Business layer property setters use accessor internally - no changes needed
4. Direct mutation (`task.custom_fields[0]["value"] = x`) continues to work

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing accessor usage | High | Low | `get_custom_fields()` still works; deprecation, not removal |
| Incomplete reset in edge cases | Medium | Low | Comprehensive test coverage; idempotent design |
| Performance regression from additional method calls | Low | Low | O(1) operations; negligible overhead |
| Business layer regression | High | Low | Property setters don't call `get_custom_fields()` directly |

### Risk Deep-Dive: Business Layer Compatibility

Business layer entities (Contact, Unit, Business, etc.) use this pattern:

```python
# In business entity property setter
@property
def priority(self) -> str | None:
    return self.get_custom_fields().get(self.Fields.PRIORITY)

@priority.setter
def priority(self, value: str) -> None:
    self.get_custom_fields().set(self.Fields.PRIORITY, value)
```

**Analysis**:
- Deprecation warning will be triggered when property is accessed
- Functionality is unchanged
- Fix: Update business layer to use `custom_fields_editor()` in follow-up

**Mitigation**: Phase 2 ensures business layer continues working. Post-release, update business layer classes.

## Observability

### Logging

```python
# In SaveSession._reset_custom_field_tracking()
if self._log:
    self._log.debug(
        "reset_custom_field_tracking",
        entity_type=type(entity).__name__,
        entity_gid=entity.gid,
        had_accessor_changes=hasattr(entity, '_custom_fields_accessor')
            and entity._custom_fields_accessor is not None
            and entity._custom_fields_accessor.has_changes(),
    )
```

### Metrics

No new metrics required. Existing commit metrics provide visibility.

### Alerting

No new alerts. Failures will surface through existing error handling.

## Testing Strategy

### Unit Tests

| Test | Location | Coverage |
|------|----------|----------|
| `test_reset_clears_accessor_modifications` | `test_task.py` | FR-001 |
| `test_reset_updates_snapshot` | `test_task.py` | FR-002 |
| `test_custom_fields_editor_returns_accessor` | `test_task.py` | FR-003 |
| `test_get_custom_fields_emits_deprecation` | `test_task.py` | FR-004 |
| `test_reset_is_idempotent` | `test_task.py` | Robustness |
| `test_savesession_calls_reset_on_success` | `test_session.py` | ADR-0074 |

### Integration Tests

| Test | Location | Coverage |
|------|----------|----------|
| `test_no_duplicate_api_calls_on_recommit` | `test_session_integration.py` | FR-007 |
| `test_cross_session_clean_state` | `test_session_integration.py` | FR-008 |
| `test_partial_failure_preserves_state` | `test_session_integration.py` | FR-009 |
| `test_business_layer_commit_cycle` | `test_business_integration.py` | FR-010 |

### Regression Tests

All existing tests must pass:
- `tests/unit/models/test_custom_field_accessor.py`
- `tests/unit/models/test_task_custom_fields.py`
- `tests/unit/persistence/test_session.py`
- `tests/integration/test_crud_lifecycle.py`

## PRD Requirement Traceability

| PRD Requirement | TDD Component | Verification |
|-----------------|---------------|--------------|
| FR-001 | `Task.reset_custom_field_tracking()` calls `accessor.clear_changes()` | Unit test |
| FR-002 | `Task._update_custom_fields_snapshot()` | Unit test |
| FR-003 | `Task.custom_fields_editor()` method | Unit test |
| FR-004 | `DeprecationWarning` in `get_custom_fields()` | Unit test |
| FR-007 | Reset prevents ChangeTracker from detecting changes | Integration test |
| FR-008 | Fresh snapshot in new session sees no changes | Integration test |
| FR-009 | Reset in success loop only | Integration test |
| FR-010 | Business layer uses accessor (unchanged) | Regression test |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should `custom_fields_editor()` be a property instead of method? | Architect | - | Method - matches existing pattern; properties imply no side effects |
| Should we add `has_changes()` shortcut to Task? | Architect | - | Out of scope - accessor provides this already |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Architect | Initial draft |

---

## Quality Gate Checklist

- [x] Traces to approved PRD (PRD-HARDENING-B)
- [x] All significant decisions have ADRs (ADR-0074)
- [x] Component responsibilities are clear
- [x] Interfaces are defined (Task, SaveSession changes)
- [x] Complexity level is justified (Module)
- [x] Risks identified with mitigations
- [x] Implementation plan is actionable
- [x] Testing strategy defined
- [x] PRD requirement traceability complete
