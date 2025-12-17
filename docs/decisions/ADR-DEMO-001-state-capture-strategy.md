# ADR-DEMO-001: State Capture Strategy for Demo Restoration

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-12
- **Deciders**: SDK Team
- **Related**: PRD-SDKDEMO, TDD-SDKDEMO

## Context

The SDK Demonstration Suite (PRD-SDKDEMO) requires that all demo operations be reversible. After demonstrating each SDK capability (tag operations, custom fields, subtask manipulation, etc.), the demo must restore entities to their initial state.

**Forces at play**:

1. **Completeness**: We must capture enough state to fully restore entities
2. **Performance**: State capture should not add significant latency
3. **Memory**: State snapshots should not consume excessive memory
4. **Complexity**: State management code should remain maintainable
5. **Reliability**: Restoration must work even after multiple operations

**Key challenge**: Entities have deep references (tags, projects, sections, parent tasks, custom fields) that could be captured either by value (deep copy) or by reference (GID only).

## Decision

**Implement shallow copy state capture with GID references.**

State capture captures:
- Scalar fields by value (name, notes, completed, etc.)
- Custom field values by value (with GID keys)
- Relationships as GID references only (tags, parent, memberships, dependencies)

```python
@dataclass
class EntityState:
    """Captured state of an entity for restoration."""
    gid: str
    notes: str | None
    custom_fields: dict[str, Any]  # {field_gid: value}

@dataclass
class MembershipState:
    """Task membership state."""
    project_gid: str
    section_gid: str | None

@dataclass
class TaskSnapshot:
    """Complete snapshot of a task for restoration."""
    entity_state: EntityState
    tag_gids: list[str]
    parent_gid: str | None
    memberships: list[MembershipState]
    dependency_gids: list[str]
    dependent_gids: list[str]
```

**Restoration uses SDK action operations** to re-establish relationships:
- `session.add_tag()` / `session.remove_tag()` for tags
- `session.set_parent()` for parent restoration
- `session.move_to_section()` for section restoration
- `session.add_dependency()` / `session.remove_dependency()` for dependencies

## Rationale

1. **Shallow copy is sufficient**: We only need GIDs to restore relationships. The actual Tag/Project/Section objects still exist in Asana.

2. **GID-based restoration is idempotent**: Adding a tag that already exists is a no-op. This makes partial restoration safe.

3. **Memory efficient**: Storing GID strings (16-20 bytes each) vs. full objects (potentially KB each).

4. **Aligns with SDK patterns**: SaveSession's action operations already work with GIDs. We don't need to fetch full objects.

5. **Enables differential restoration**: We can compare initial vs. current GID sets to determine exactly what changed.

## Alternatives Considered

### Alternative 1: Deep Copy State Capture

- **Description**: Store complete serialized copies of all related entities
- **Pros**: Complete state, no need to re-fetch anything
- **Cons**:
  - Memory intensive (each tag, project, section fully serialized)
  - Stale data if related entities change during demo
  - Complex serialization/deserialization
- **Why not chosen**: Overkill for restoration needs. We only need to re-establish relationships, not recreate entities.

### Alternative 2: No State Capture (Re-fetch Before Restore)

- **Description**: Fetch current state from API at restoration time, compute diff
- **Pros**: Always accurate, minimal memory
- **Cons**:
  - Additional API calls at restore time
  - Cannot determine original state if multiple changes made
  - Network failures during restore are more impactful
- **Why not chosen**: Cannot restore to initial state without knowing initial state.

### Alternative 3: Full Entity Tracking via SaveSession

- **Description**: Use SaveSession's internal ChangeTracker for state management
- **Pros**: Leverages existing infrastructure
- **Cons**:
  - ChangeTracker designed for change detection, not multi-operation rollback
  - Would require significant modification to SaveSession
  - Couples demo scripts to SDK internals
- **Why not chosen**: Demo state management has different lifecycle than SaveSession operations.

## Consequences

### Positive
- **Simple implementation**: Dataclasses with GID lists are straightforward
- **Efficient memory**: Only strings and dicts, no full objects
- **Reliable restoration**: GID-based operations are idempotent
- **Testable**: State snapshots are easily compared in tests

### Negative
- **Related entity changes not detected**: If a tag is renamed during demo, we restore the GID (which is correct) but won't notice the name change
- **Requires action operations**: Restoration depends on SDK action operations working correctly
- **Manual state tracking**: Demo must explicitly update current state after each operation

### Neutral
- **State update discipline required**: Developer must call `update_current()` after successful operations
- **Two-phase restoration**: First restore fields (CRUD), then restore relationships (actions)

## Compliance

Ensure this decision is followed by:
- Code review checklist: "State capture uses GID references, not deep copies"
- Unit tests verify EntityState contains only GIDs for relationships
- Integration tests verify restoration produces identical API responses

