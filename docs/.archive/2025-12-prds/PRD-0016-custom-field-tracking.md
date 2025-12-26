# PRD: Custom Field Unification (Initiative B)

## Metadata
- **PRD ID**: PRD-HARDENING-B
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-16
- **Last Updated**: 2025-12-16
- **Stakeholders**: SDK Users, Business Layer Consumers, SaveSession Users
- **Related PRDs**: PRD-HARDENING-A (Foundation, prerequisite)
- **Discovery Document**: [DISCOVERY-HARDENING-B.md](/docs/initiatives/DISCOVERY-HARDENING-B.md)
- **Issues Addressed**: #2 (dual change tracking), #10 (naming confusion)

---

## Problem Statement

### What Problem Are We Solving?

The SDK currently has **three independent systems** tracking custom field changes on Task models, with no coordination between them:

| System | Mechanism | Location | Reset Behavior |
|--------|-----------|----------|----------------|
| **System 1** | ChangeTracker snapshot comparison | `persistence/tracker.py` | Reset via `mark_clean()` |
| **System 2** | CustomFieldAccessor `_modifications` dict | `models/custom_field_accessor.py` | **NOT reset after commit** |
| **System 3** | Task `_original_custom_fields` deepcopy | `models/task.py` | **NEVER reset** |

### For Whom?

- **SDK Users**: Developers using `SaveSession` to persist Task changes
- **Business Layer Consumers**: Code using entity models (Business, Contact, Unit, etc.) that modify custom fields via typed properties

### What Is the Impact of Not Solving It?

**Critical Bug (Severity: High)**: After a successful `commit_async()`, the accessor's `_modifications` dict is not cleared. This causes:

1. **Duplicate API calls**: Re-committing the same entity sends redundant updates
2. **Wasted API quota**: Each duplicate call counts against Asana rate limits
3. **Confusion**: Developers expect `commit()` to reset state

**Discovered Scenarios** (from Discovery):

```python
# Scenario 3: Re-Commit Same Entity
with SaveSession(client) as session:
    session.track(task)
    task.get_custom_fields().set("Priority", "High")
    await session.commit_async()  # Succeeds

    await session.commit_async()  # BUG: Sends same changes again!
```

```python
# Scenario 4: Multiple Sessions, Same Entity
with SaveSession(client) as s1:
    s1.track(task)
    task.get_custom_fields().set("Priority", "High")
    await s1.commit_async()

with SaveSession(client) as s2:
    s2.track(task)  # BUG: accessor still has old changes
    await s2.commit_async()  # Re-submits "Priority": "High"
```

**Secondary Issues**:
- Naming confusion: `get_custom_fields()` returns an accessor, not fields
- Direct list mutation (`task.custom_fields[0]["value"] = x`) bypasses accessor
- No-op changes (setting field to current value) still mark dirty

---

## Goals & Success Metrics

### Goals

| Goal | Measure |
|------|---------|
| **G1: Single Authoritative System** | CustomFieldAccessor is the only change tracking mechanism for custom fields |
| **G2: Correct Reset Behavior** | After successful commit, `accessor.has_changes()` returns `False` |
| **G3: Clear Naming Convention** | New method name clearly indicates accessor pattern |
| **G4: Graceful Deprecation** | Direct list mutation continues to work during transition, with warnings |

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Duplicate API calls after commit | 0 | Test: commit twice, verify single API call |
| `has_changes()` after commit | `False` | Unit test assertion |
| Deprecation warnings logged | 100% of direct mutations | Test with direct modification, verify warning |
| Test coverage for new behavior | >= 90% | pytest --cov |

---

## Scope

### In Scope

- **R1**: Establish CustomFieldAccessor as the authoritative system for custom field change tracking
- **R2**: Auto-clear accessor `_modifications` after successful commit
- **R3**: Deprecate direct list mutation (System 3) with warnings
- **R4**: Add `custom_fields_editor` alias method with deprecation of `get_custom_fields()`
- **R5**: Add no-op detection to avoid unnecessary dirty marking
- **R6**: Update `_original_custom_fields` snapshot on commit (System 3 sync)
- **R7**: Documentation updates for new patterns

### Out of Scope

- **OS-1**: Removal of `get_custom_fields()` method (deprecation only, removal in future major version)
- **OS-2**: Changes to ChangeTracker core architecture (System 1 remains unchanged)
- **OS-3**: Accessor synchronization when `task.custom_fields` is reassigned (document as limitation)
- **OS-4**: Custom field type validation beyond current behavior
- **OS-5**: Performance optimization of snapshot comparison (addressed in Initiative C)

---

## Requirements

### Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **FR-001** | CustomFieldAccessor `_modifications` MUST be cleared after successful `SaveSession.commit_async()` | Must | After commit, `accessor.has_changes()` returns `False`. Verified by unit test. |
| **FR-002** | Task `_original_custom_fields` snapshot MUST be updated after successful commit | Must | After commit, `task._has_direct_custom_field_changes()` returns `False`. |
| **FR-003** | `Task.custom_fields_editor()` method MUST be added as alias for `get_custom_fields()` | Must | Method exists, returns same `CustomFieldAccessor` instance. |
| **FR-004** | `Task.get_custom_fields()` MUST emit deprecation warning when called | Should | `DeprecationWarning` logged with migration message. Warning includes "use custom_fields_editor() instead". |
| **FR-005** | Direct mutation of `task.custom_fields` list MUST emit deprecation warning on commit | Should | When `_has_direct_custom_field_changes()` is True and accessor has no changes, log warning at commit time. |
| **FR-006** | `CustomFieldAccessor.set()` SHOULD skip modification when value equals current value | Should | `set("field", current_value)` does not add to `_modifications`. `has_changes()` remains `False`. |
| **FR-007** | Multiple commits of same entity within session MUST NOT send duplicate API calls | Must | Second `commit_async()` detects no changes, returns success without API call. |
| **FR-008** | Entity reused across sessions MUST have clean state in new session | Must | Task tracked in Session 2 after Session 1 commit has `accessor.has_changes() == False`. |
| **FR-009** | Reset MUST occur only on successful commit, not on failure | Must | If commit fails (API error), `accessor.has_changes()` remains `True`. |
| **FR-010** | Business layer property setters continue to work without changes | Must | `contact.priority = "High"` via property still records change correctly. |

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| **NFR-001** | Reset operation latency | < 1ms per entity | Benchmark test |
| **NFR-002** | No memory leaks from accessor lifecycle | 0 leaked accessors | Memory profiler test |
| **NFR-003** | Backward compatibility during deprecation | 100% existing tests pass | pytest suite |
| **NFR-004** | Type safety maintained | mypy clean | `mypy src/autom8_asana --strict` |

---

## User Stories / Use Cases

### UC-1: Standard Custom Field Modification Flow

```python
# Current pattern - continues to work
async with SaveSession(client) as session:
    task = await client.tasks.get_async("123")
    session.track(task)

    # Use new name (preferred)
    task.custom_fields_editor().set("Priority", "High")

    result = await session.commit_async()
    assert result.success

    # NEW: accessor is now clean
    assert not task.custom_fields_editor().has_changes()
```

### UC-2: Re-Commit Same Entity (Previously Buggy)

```python
async with SaveSession(client) as session:
    task = await client.tasks.get_async("123")
    session.track(task)

    task.custom_fields_editor().set("Priority", "High")
    await session.commit_async()  # First commit - API called

    # Make another change
    task.custom_fields_editor().set("Status", "Done")
    await session.commit_async()  # Second commit - only Status sent

    # No change
    await session.commit_async()  # Third commit - NO API call (no changes)
```

### UC-3: Entity Across Multiple Sessions

```python
task = await client.tasks.get_async("123")

# Session 1
async with SaveSession(client) as s1:
    s1.track(task)
    task.custom_fields_editor().set("Priority", "High")
    await s1.commit_async()

# Session 2 - task is clean
async with SaveSession(client) as s2:
    s2.track(task)
    # accessor.has_changes() is False - no duplicate commit
    await s2.commit_async()  # No API call needed
```

### UC-4: Business Layer Usage (Unchanged)

```python
# Business layer continues to work identically
async with SaveSession(client) as session:
    contact = await Contact.from_gid_async(client, "456")
    session.track(contact)

    # Property setters use accessor internally
    contact.priority = "High"  # Calls get_custom_fields().set()
    contact.status = "Active"

    await session.commit_async()

    # Contact's accessor is also reset
    assert not contact.custom_fields_editor().has_changes()
```

### UC-5: Deprecation Warning for Legacy Pattern

```python
# Old pattern - still works but warns
import warnings

task = await client.tasks.get_async("123")

with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")

    # Deprecated method - emits warning
    accessor = task.get_custom_fields()

    assert len(w) == 1
    assert "get_custom_fields() is deprecated" in str(w[0].message)
    assert "use custom_fields_editor()" in str(w[0].message)
```

### UC-6: No-Op Detection

```python
task = await client.tasks.get_async("123")
# Assume task already has Priority = "High"

accessor = task.custom_fields_editor()
assert not accessor.has_changes()

# Set to same value - no-op
accessor.set("Priority", "High")

# Still no changes (optimization)
assert not accessor.has_changes()
```

---

## Technical Approach

### R1/R2: Unified Reset via SaveSession Hook

**Approach**: Add reset hook in `SaveSession._commit_entity()` after successful API call.

```python
# In SaveSession (simplified)
async def _commit_entity(self, entity: AsanaResource) -> ActionResult:
    # ... existing commit logic ...
    result = await self._pipeline.execute_save(entity)

    if result.success:
        self._reset_custom_field_state(entity)  # NEW
        self._tracker.mark_clean(entity)

    return result

def _reset_custom_field_state(self, entity: AsanaResource) -> None:
    """Reset custom field tracking state after successful commit."""
    if isinstance(entity, Task) and entity._custom_fields_accessor is not None:
        entity._custom_fields_accessor.clear_changes()
        entity._update_custom_fields_snapshot()  # NEW method
```

**Impact**: Centralizes reset logic in SaveSession, ensures all three systems synchronized.

### R3: Deprecate Direct List Mutation

**Approach**: Log warning during `model_dump()` when System 3 detects changes but System 2 does not.

```python
# In Task.model_dump()
if self._has_direct_custom_field_changes() and not self._accessor_has_changes():
    warnings.warn(
        "Direct modification of task.custom_fields is deprecated. "
        "Use task.custom_fields_editor().set() instead.",
        DeprecationWarning,
        stacklevel=2
    )
```

**Note**: Direct mutations continue to work during transition period. Warning alerts users to migrate.

### R4: Naming Convention

**Approach**: Add new method, deprecate old method.

```python
class Task(AsanaResource):
    def custom_fields_editor(self) -> CustomFieldAccessor:
        """Get the custom fields editor for reading and writing field values.

        Returns:
            CustomFieldAccessor: Editor instance for this task's custom fields.

        Example:
            editor = task.custom_fields_editor()
            editor.set("Priority", "High")
            value = editor.get("Status")
        """
        return self._get_or_create_accessor()

    def get_custom_fields(self) -> CustomFieldAccessor:
        """Deprecated: Use custom_fields_editor() instead."""
        warnings.warn(
            "get_custom_fields() is deprecated. Use custom_fields_editor() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self._get_or_create_accessor()
```

### R5: No-Op Detection

**Approach**: Compare values in `CustomFieldAccessor.set()` before recording modification.

```python
def set(self, name_or_gid: str, value: Any) -> None:
    gid = self._resolve_gid(name_or_gid)

    # Skip if setting to current value (no-op detection)
    current = self.get(name_or_gid)
    if self._values_equal(current, value):
        return

    self._modifications[gid] = value

def _values_equal(self, a: Any, b: Any) -> bool:
    """Compare values accounting for type variations."""
    # Handle None cases
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False

    # Handle numeric comparison (Decimal vs float)
    if isinstance(a, (int, float, Decimal)) and isinstance(b, (int, float, Decimal)):
        return float(a) == float(b)

    # Default comparison
    return a == b
```

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| **A1**: Business layer property setters use `get_custom_fields()` internally | Verified in Discovery - all setters follow this pattern |
| **A2**: Direct list mutation is rare in production code | Business layer uses accessor; direct mutation is legacy |
| **A3**: Users will see deprecation warnings | Standard Python warning mechanism; can be silenced if needed |
| **A4**: Float precision is acceptable for Decimal values | Matches Asana API behavior; per Orchestrator recommendation |
| **A5**: `_original_custom_fields` snapshot can be updated without breaking existing behavior | Snapshot is private implementation detail |

---

## Dependencies

| Dependency | Owner | Status | Impact |
|------------|-------|--------|--------|
| **Initiative A (Foundation)** | Architecture Hardening | Complete | Prerequisite - must be done first |
| **SaveSession implementation** | SDK Core | Stable | Reset hook location |
| **CustomFieldAccessor** | SDK Models | Stable | API additions (clear_changes exists) |
| **Task model** | SDK Models | Stable | Method additions |
| **Business layer entities** | SDK Models | Stable | Must continue working unchanged |

### Blocks

| Blocked Initiative | Reason |
|--------------------|--------|
| **Initiative F (SaveSession Reliability)** | Correct reset behavior required before reliability improvements |

---

## Migration Guide

### Phase 1: Immediate (With This Release)

1. **Update imports**: No change needed (same module paths)
2. **Update method calls**:
   - Replace `task.get_custom_fields()` with `task.custom_fields_editor()`
   - Old method continues to work with deprecation warning

```python
# Before
accessor = task.get_custom_fields()

# After (preferred)
editor = task.custom_fields_editor()
```

3. **Direct mutations**: Replace with accessor pattern

```python
# Before (deprecated, warns)
task.custom_fields[0]["text_value"] = "New"

# After
task.custom_fields_editor().set("FieldName", "New")
```

### Phase 2: Future Major Version

- `get_custom_fields()` method removed entirely
- Direct list mutation warning upgraded to error
- System 3 (`_original_custom_fields`) removed

### Business Layer

**No changes required.** Property setters internally call the accessor, which is automatically migrated.

```python
# This continues to work unchanged
contact.priority = "High"  # Internally uses accessor
```

### Suppressing Warnings (If Needed)

```python
import warnings

# Suppress deprecation warnings during migration
warnings.filterwarnings("ignore", category=DeprecationWarning, module="autom8_asana")
```

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| ~~Should commit auto-clear modifications?~~ | Orchestrator | 2025-12-16 | **Yes** - auto-clear after successful commit |
| ~~What naming for new method?~~ | Orchestrator | 2025-12-16 | **custom_fields_editor()** - clear intent |
| ~~Deprecate or remove direct mutation?~~ | Orchestrator | 2025-12-16 | **Deprecate** with warnings (cleaner long-term) |
| ~~Keep Decimal precision or convert to float?~~ | Orchestrator | 2025-12-16 | **Float** - matches Asana API |

*All open questions resolved by Orchestrator recommendations.*

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing code using `get_custom_fields()` | Low | Medium | Deprecation warning, not removal |
| Business layer regression | Low | High | Business layer uses accessor internally - unaffected |
| Performance regression from no-op detection | Low | Low | Simple comparison, negligible overhead |
| Users ignore deprecation warnings | Medium | Low | Warnings are informational; old code still works |

---

## Test Strategy

### Unit Tests

| Test Category | Coverage |
|---------------|----------|
| `CustomFieldAccessor.clear_changes()` | Clears `_modifications`, `has_changes()` returns `False` |
| `Task.custom_fields_editor()` | Returns accessor, same instance on repeat calls |
| `Task.get_custom_fields()` deprecation | Emits `DeprecationWarning` |
| No-op detection in `set()` | Same value does not add to `_modifications` |
| `_values_equal()` | Decimal/float comparison, None handling |

### Integration Tests

| Test Category | Coverage |
|---------------|----------|
| SaveSession commit reset | After commit, `has_changes()` is `False` |
| Multiple commits same entity | Second commit detects no changes |
| Cross-session entity reuse | Entity clean in second session |
| Business layer commit cycle | Property setter -> commit -> clean state |
| Direct mutation warning | Deprecation warning logged at commit |

### Regression Tests

| Test Category | Coverage |
|---------------|----------|
| All existing custom field tests pass | No regressions |
| Business layer entity tests pass | Property getters/setters work |
| SaveSession tests pass | Commit behavior unchanged (except reset) |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Requirements Analyst | Initial draft based on DISCOVERY-HARDENING-B |

---

## Quality Gate Checklist

- [x] Problem statement is clear and compelling (duplicate API calls, wasted quota)
- [x] Scope explicitly defines in/out (7 in-scope, 5 out-of-scope items)
- [x] All requirements are specific and testable (FR-001 through FR-010)
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented (A1-A5)
- [x] No open questions blocking design (all resolved by Orchestrator)
- [x] Dependencies identified (Initiative A prerequisite, blocks Initiative F)
- [x] Migration guide provided
