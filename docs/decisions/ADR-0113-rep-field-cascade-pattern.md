# ADR-0113: Rep Field Cascade Pattern

## Metadata
- **Status**: Accepted
- **Author**: Architect (Claude)
- **Date**: 2025-12-18
- **Deciders**: Engineering Team
- **Related**: [PRD-PIPELINE-AUTOMATION-ENHANCEMENT](../requirements/PRD-PIPELINE-AUTOMATION-ENHANCEMENT.md), [TDD-PIPELINE-AUTOMATION-ENHANCEMENT](../design/TDD-PIPELINE-AUTOMATION-ENHANCEMENT.md)

## Context

When a new Process is created through pipeline conversion, it needs an assignee. The assignee should be the representative (rep) responsible for that business at the target stage. The SDK has `PeopleField` descriptors for accessing rep information:

- `Unit.rep` - The rep assigned at the unit level
- `Business.rep` - The rep assigned at the business level

Both fields return `list[dict[str, Any]]` containing user objects with GIDs:
```python
[
    {"gid": "123456789", "name": "John Smith", "resource_type": "user"},
]
```

The question is: how should we resolve which rep to use as the assignee for the new Process?

**Forces at play**:
- Some Units have their own rep (e.g., different account manager per location)
- Many Units inherit the rep from their parent Business
- The rep field may be empty on either or both entities
- We want deterministic, predictable behavior
- Different ProcessTypes might have different rep requirements (Sales Rep vs Implementation Rep), but per discovery, there's only one `rep` field on each entity

## Decision

**Use a cascade pattern: prefer Unit.rep, fall back to Business.rep, skip assignee if both are empty.**

Specifically:
```python
def resolve_rep(
    unit: Unit | None,
    business: Business | None,
) -> str | None:
    """Resolve rep GID for assignee assignment.

    Per ADR-0113: Unit.rep takes precedence over Business.rep.

    Args:
        unit: Unit entity (may be None).
        business: Business entity (may be None).

    Returns:
        User GID for assignee, or None if no rep found.
    """
    # Try Unit.rep first
    if unit is not None:
        rep_users = unit.rep
        if rep_users and len(rep_users) > 0:
            return rep_users[0]["gid"]

    # Fall back to Business.rep
    if business is not None:
        rep_users = business.rep
        if rep_users and len(rep_users) > 0:
            return rep_users[0]["gid"]

    # No rep found
    return None
```

When `None` is returned, log a warning and leave the new Process unassigned.

## Rationale

The Unit-first cascade pattern is correct because:

1. **Specificity Principle**: Unit is more specific than Business. If a Unit has its own rep, that's an intentional override of the business-level default.

2. **Data Model Alignment**: The Business > Unit hierarchy implies Unit-level attributes should take precedence when present.

3. **Operational Reality**: Per discovery with the user, Units sometimes have dedicated account managers while the Business has a different overall rep. The Unit's rep is the right person for that specific location's processes.

4. **Graceful Fallback**: If Unit.rep is empty (common case), we naturally fall back to Business.rep without additional logic.

5. **Existing Pattern**: This mirrors how other cascading fields work in the SDK (e.g., Unit inherits fields from Business when not explicitly set).

## Alternatives Considered

### Alternative 1: Business.rep Only

- **Description**: Always use Business.rep, ignore Unit.rep entirely.
- **Pros**:
  - Simpler implementation
  - Consistent across all Units of a Business
- **Cons**:
  - Ignores Unit-level rep assignments
  - Wrong assignee for Units with dedicated account managers
  - Wastes the Unit.rep field
- **Why not chosen**: Ignores valid data and operational reality of unit-level assignments.

### Alternative 2: Unit.rep Only (No Fallback)

- **Description**: Only use Unit.rep; if empty, don't set assignee.
- **Pros**:
  - Simple, single source
  - Clear responsibility: populate Unit.rep if you want assignee
- **Cons**:
  - Many Units don't have explicit rep (inherit from Business)
  - Would leave most new Processes unassigned
  - Violates "assignee assignment rate = 90%+" target
- **Why not chosen**: Too restrictive; ignores valid fallback data.

### Alternative 3: ProcessType-Based Rep Field

- **Description**: Different ProcessTypes use different rep fields (e.g., Sales uses `sales_rep`, Onboarding uses `implementation_rep`).
- **Pros**:
  - Fine-grained control per pipeline stage
  - Allows different specialists at each stage
- **Cons**:
  - Per discovery, these fields don't exist (only `rep` on Unit and Business)
  - Would require schema changes to add stage-specific fields
  - Added complexity for questionable benefit
- **Why not chosen**: The fields don't exist, and the current `rep` field is sufficient for the use case.

### Alternative 4: Source Process Assignee Carry-Through

- **Description**: Use the source process's assignee as the new process's assignee.
- **Pros**:
  - Continuity of ownership across pipeline
  - No hierarchy lookup needed
- **Cons**:
  - Source assignee may not be responsible for target stage
  - Sales rep shouldn't be assigned Onboarding tasks
  - Violates separation of concerns
- **Why not chosen**: The rep at one stage is typically not the owner at the next stage.

### Alternative 5: Configurable Cascade Order

- **Description**: Allow configuration of cascade order (Unit-first or Business-first).
- **Pros**:
  - Maximum flexibility
  - Different deployments can choose
- **Cons**:
  - YAGNI: no expressed need for Business-first order
  - Configuration complexity
  - Harder to reason about behavior
- **Why not chosen**: Unit-first is the universally correct order given the hierarchy. Configuration adds complexity without benefit.

## Consequences

### Positive
- **Correct Assignee**: Unit-level reps get their processes; Business-level rep is the default.
- **Predictable Behavior**: Clear precedence order is easy to reason about.
- **Graceful Degradation**: Empty rep doesn't fail conversion, just leaves assignee unset.
- **Simple Implementation**: Two-step cascade is straightforward.

### Negative
- **Implicit Inheritance**: Users must understand that empty Unit.rep means Business.rep is used. This could be surprising if they expect explicit assignment.
- **First Rep Only**: If multiple users are in the rep field, only the first is used. (This is acceptable per assumption A6 in PRD.)

### Neutral
- **Logging**: Warning is logged when no rep is found, aiding debugging.
- **Consistent with SDK**: Mirrors field inheritance patterns used elsewhere.

## Compliance

- [ ] `resolve_rep()` checks Unit.rep before Business.rep
- [ ] Empty rep results in warning log, not error
- [ ] First user in rep list is used as assignee (rep[0]["gid"])
- [ ] Unit tests cover: Unit.rep set, Unit.rep empty with Business.rep set, both empty
- [ ] Assignee assignment failure doesn't fail conversion (per FR-ASSIGN-006)
