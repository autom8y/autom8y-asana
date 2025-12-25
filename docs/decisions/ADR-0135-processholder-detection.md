# ADR-0135: ProcessHolder Detection Strategy

## Metadata

- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-19
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-TECH-DEBT-REMEDIATION (FR-DET-003), ADR-0093, ADR-0094, TDD-TECH-DEBT-REMEDIATION

## Context

ProcessHolder entities currently have `PRIMARY_PROJECT_GID = None`, causing detection to rely on Tier 2 name patterns ("processes") or Tier 3 parent inference from Unit. This raises a critical design question:

**OQ-1 from PRD: Should ProcessHolder have a dedicated Asana project?**

### Current State Analysis

1. **ProcessHolder structure**: ProcessHolder is a subtask of Unit, containing Process children
2. **Hierarchy position**: `Business > UnitHolder > Unit > ProcessHolder > Process`
3. **Detection behavior**: Falls back to Tier 2 (name pattern "processes") or Tier 3 (child of Unit)
4. **Parallel holders**: OfferHolder (under Unit) has `PRIMARY_PROJECT_GID = "1210679066066870"`

### Forces

1. **Tier 1 preference**: O(1) project membership detection is deterministic and fast
2. **Consistency**: Similar holders (OfferHolder) have dedicated projects
3. **Operational reality**: ProcessHolder is a container task, not a business entity with custom fields
4. **Name decoration risk**: Tier 2 may fail if ProcessHolder is renamed/decorated
5. **Parent inference reliability**: Tier 3 is 80% confidence when parent type is known

## Decision

**ProcessHolder SHALL NOT have a dedicated Asana project.** Detection will rely on Tier 2 (name pattern) as primary fallback, with Tier 3 (parent inference from Unit) as secondary fallback.

### Rationale for No Project

1. **Container purpose**: ProcessHolder exists solely to group Process entities; it has no custom fields and no business data
2. **Operational practice**: Team does not manage ProcessHolders in a project view; they are navigation containers
3. **Symmetry with similar holders**: LocationHolder and UnitHolder also have `PRIMARY_PROJECT_GID = None`
4. **Detection reliability**: Tier 3 inference from Unit parent is highly reliable (Unit.ProcessHolder is predictable)

### Detection Strategy

```
ProcessHolder Detection Chain:
1. Tier 1: Project membership -> None (no project)
2. Tier 2: Name pattern "processes" -> EntityType.PROCESS_HOLDER (60% confidence)
3. Tier 3: Parent is Unit -> EntityType.PROCESS_HOLDER (80% confidence)
4. Tier 5: Unknown fallback
```

### Implementation

1. **Confirm None is correct**: Document in `ProcessHolder` docstring that `PRIMARY_PROJECT_GID = None` is intentional
2. **Strengthen Tier 2**: Enhance pattern matching for decorated names (ADR-0117)
3. **Prefer Tier 3**: When hydrating from Unit, always provide `parent_type=EntityType.UNIT`

### Code Changes

```python
class ProcessHolder(Task, HolderMixin["Process"]):
    """Holder task containing Process children.

    PRIMARY_PROJECT_GID is intentionally None because ProcessHolder
    is a container task that exists only to group Process entities
    under a Unit. It has no custom fields and is not managed as a
    project member. Detection relies on:
    - Tier 2: Name pattern "processes"
    - Tier 3: Parent inference from Unit

    This is consistent with LocationHolder and UnitHolder, which
    also lack dedicated projects.
    """

    PRIMARY_PROJECT_GID: ClassVar[str | None] = None  # Intentional - see docstring
```

## Alternatives Considered

### Alternative A: Create Dedicated ProcessHolders Project

- **Description**: Create an Asana project to hold ProcessHolder tasks for Tier 1 detection
- **Pros**: Deterministic O(1) detection; consistent with OfferHolder pattern
- **Cons**: Operational overhead; project would serve no business purpose; team doesn't manage holders in project views
- **Why not chosen**: ProcessHolder is purely structural; creating a project for detection alone is unnecessary complexity

### Alternative B: Treat ProcessHolder Like OfferHolder (Has Project)

- **Description**: Assume ProcessHolder should have a project and mark as DEBT
- **Pros**: Symmetry with OfferHolder
- **Cons**: OfferHolder's project serves business purposes (offer management); ProcessHolder has no such need
- **Why not chosen**: False symmetry; holders serve different operational purposes

### Alternative C: Remove ProcessHolder from Hierarchy

- **Description**: Flatten Process entities directly under Unit
- **Pros**: Eliminates detection problem entirely
- **Cons**: Major architectural change; breaks existing hierarchy patterns; would affect all Process access
- **Why not chosen**: ProcessHolder serves valuable grouping purpose; change is too disruptive

## Consequences

### Positive

- **No operational change**: Team continues existing workflow without new project
- **Consistency**: Aligns with LocationHolder and UnitHolder (both None)
- **Documentation**: Clear rationale captured for future maintainers
- **Simpler architecture**: No artificial project just for detection

### Negative

- **Tier 2 reliance**: Name pattern detection is 60% confidence (mitigated by Tier 3)
- **Decorated name risk**: If ProcessHolder name is decorated, Tier 2 fails (mitigated by ADR-0117 pattern improvements)

### Neutral

- `ProcessHolder.PRIMARY_PROJECT_GID` remains None
- Detection strategy documented in entity docstring
- Tier 3 becomes the preferred path during hydration

## Compliance

- ProcessHolder docstring MUST document intentional None for PRIMARY_PROJECT_GID
- Hydration code MUST pass `parent_type=EntityType.UNIT` when detecting ProcessHolder children of Unit
- Integration tests MUST verify ProcessHolder detection via both Tier 2 and Tier 3
- ADR-0117 MUST address decorated name handling for Tier 2 reliability
