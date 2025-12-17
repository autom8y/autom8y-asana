# ADR-0074: Unified Custom Field Tracking via CustomFieldAccessor

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-HARDENING-B, TDD-HARDENING-B, ADR-0067, ADR-0056

## Context

The SDK currently has **three independent systems** tracking custom field changes on Task models:

| System | Mechanism | Location | Reset After Commit |
|--------|-----------|----------|-------------------|
| **System 1** | ChangeTracker snapshot comparison via `model_dump()` | `persistence/tracker.py` | Yes (via `mark_clean()`) |
| **System 2** | CustomFieldAccessor `_modifications` dict | `models/custom_field_accessor.py` | **NO** |
| **System 3** | Task `_original_custom_fields` deepcopy for direct mutation detection | `models/task.py` | **NO** |

### The Problem

After a successful `SaveSession.commit_async()`:

1. **System 1 (ChangeTracker)** correctly updates its snapshot via `mark_clean(entity)`
2. **System 2 (CustomFieldAccessor)** retains `_modifications` - `has_changes()` still returns `True`
3. **System 3 (Task snapshot)** retains `_original_custom_fields` - `_has_direct_custom_field_changes()` still returns `True`

This causes:

- **Duplicate API calls**: Re-committing sends redundant updates (FR-007 violation)
- **Cross-session pollution**: Entity tracked in Session 2 after Session 1 commit still appears dirty (FR-008 violation)
- **Unexpected behavior**: Developers expect `commit()` to reset change tracking state

### Forces at Play

1. **Accessor is the intended public API**: `get_custom_fields().set()` is the recommended pattern
2. **Direct mutation exists for backward compatibility**: Some code mutates `task.custom_fields` directly
3. **ChangeTracker is a general-purpose system**: Works for all entity types, not custom-field-aware
4. **Task-specific logic needed**: Only Task has custom fields; generic solutions don't fit
5. **Reset timing matters**: Must reset after success, not on failure (FR-009)

## Decision

**Make CustomFieldAccessor (`_modifications`) the authoritative system for custom field change tracking, with SaveSession responsible for coordinating reset across all three systems after successful commit.**

Specifically:

1. **SaveSession owns reset coordination**: After successful entity commit, SaveSession calls a new Task method to reset custom field state
2. **Task provides reset encapsulation**: New `reset_custom_field_tracking()` method clears accessor modifications AND updates the snapshot
3. **System 3 becomes a fallback**: Direct mutation detection remains for backward compatibility but resets alongside accessor

## Rationale

### Why SaveSession Owns Reset Coordination

| Option | Pros | Cons |
|--------|------|------|
| **ChangeTracker.mark_clean()** | Centralized in existing reset point | ChangeTracker is generic; adding Task-specific logic violates SRP |
| **Task.model_dump()** side effect | No changes to SaveSession | Side effects in serialization are surprising and hard to debug |
| **SaveSession._commit_entity()** | Clear ownership; success-aware | Requires SaveSession to know about Task internals |

**Decision**: SaveSession owns coordination because:
- It already calls `mark_clean()` for System 1
- It knows success/failure state (FR-009)
- Encapsulation via Task method minimizes coupling

### Why a New Task Method (Not Direct Access)

| Option | Pros | Cons |
|--------|------|------|
| **Direct attribute access** (`task._custom_fields_accessor._modifications.clear()`) | Simple | Violates encapsulation; tight coupling |
| **Protocol/interface pattern** | Formal contract | Overhead for single implementation |
| **New public method** (`task.reset_custom_field_tracking()`) | Clear intent; encapsulated | Adds API surface |

**Decision**: New public method because:
- Encapsulates both accessor reset AND snapshot update
- Single responsibility: "reset custom field tracking state"
- Can be documented and tested independently
- SaveSession doesn't need to know accessor internals

### Why Per-Entity Reset (Not Batch)

| Option | Pros | Cons |
|--------|------|------|
| **Batch reset after all commits** | Single pass | Failed entities would be reset (violates FR-009) |
| **Per-entity in success loop** | Respects partial failure | More calls (negligible overhead) |

**Decision**: Per-entity reset in the success loop because:
- Only successful entities should be reset
- Aligns with existing `mark_clean()` pattern
- Handles partial batch failures correctly

## Alternatives Considered

### Alternative 1: Make ChangeTracker Custom-Field-Aware

- **Description**: Modify ChangeTracker to call accessor reset in `mark_clean()`
- **Pros**: Centralized change tracking
- **Cons**: Violates single responsibility; ChangeTracker becomes Task-aware; complicates future entity types
- **Why not chosen**: ChangeTracker should remain a generic snapshot comparison system

### Alternative 2: Auto-Reset in model_dump()

- **Description**: Clear accessor modifications when `model_dump()` is called (after serialization)
- **Pros**: No SaveSession changes
- **Cons**: Side effects in serialization are surprising; breaks read-only expectation of serialization; timing issues
- **Why not chosen**: Serialization should be pure and predictable

### Alternative 3: Deprecate System 3 (Direct Mutation)

- **Description**: Remove `_original_custom_fields` snapshot; only support accessor changes
- **Pros**: Simpler system (two systems, not three)
- **Cons**: Breaking change for code that mutates `task.custom_fields` directly; business layer compatibility
- **Why not chosen**: Too aggressive; PRD specifies graceful deprecation path, not removal

### Alternative 4: Event-Based Reset

- **Description**: CustomFieldAccessor subscribes to SaveSession events and resets on post-save
- **Pros**: Decoupled
- **Cons**: Complex wiring; accessor would need SaveSession reference; event ordering issues
- **Why not chosen**: Over-engineered for the problem; simple method call is sufficient

## Consequences

### Positive

1. **Correct behavior**: `has_changes()` returns `False` after successful commit (FR-001, FR-002)
2. **No duplicate API calls**: Re-commit detects no changes (FR-007)
3. **Cross-session clean state**: Entity tracked in new session has no stale modifications (FR-008)
4. **Encapsulated reset logic**: Task owns its reset behavior; SaveSession just calls the method
5. **Partial failure safety**: Failed entities retain their modifications for retry (FR-009)

### Negative

1. **SaveSession-Task coupling**: SaveSession must know to call Task-specific method
2. **API surface increase**: New public method on Task
3. **isinstance check**: SaveSession needs `isinstance(entity, Task)` check

### Neutral

1. **System 3 remains**: Direct mutation detection still works; reset is coordinated
2. **Business layer unaffected**: Property setters use accessor internally; behavior unchanged (FR-010)
3. **Deprecation path enabled**: `get_custom_fields()` can emit warning without breaking functionality

## Compliance

To ensure this decision is followed:

1. **Unit test**: `test_accessor_cleared_after_commit()` - verify `has_changes() == False` post-commit
2. **Unit test**: `test_snapshot_updated_after_commit()` - verify `_has_direct_custom_field_changes() == False`
3. **Integration test**: `test_no_duplicate_api_calls()` - verify second commit makes no API call
4. **Integration test**: `test_cross_session_clean_state()` - verify entity clean in new session
5. **Code review checklist**: Any new entity type with custom fields must implement reset method
