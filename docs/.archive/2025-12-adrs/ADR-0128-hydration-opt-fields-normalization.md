# ADR-0128: Hydration opt_fields Normalization

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: SDK Team
- **Related**: PRD-CACHE-PERF-HYDRATION, TDD-CACHE-PERF-HYDRATION, ADR-0094, ADR-0101, ADR-0054

## Context

Three separate `opt_fields` definitions exist across the codebase:

1. **`_DETECTION_OPT_FIELDS`** (hydration.py:63-68) - 4 fields for minimal detection
2. **`_BUSINESS_FULL_OPT_FIELDS`** (hydration.py:73-90) - 14 fields including custom_fields
3. **`TasksClient._DETECTION_FIELDS`** (tasks.py:644-660) - 13 fields for subtask detection

This fragmentation creates a **critical gap**: `TasksClient._DETECTION_FIELDS` is missing:
- `parent.gid` - Required for upward traversal in `_traverse_upward_async()`
- `custom_fields.people_value` - Required for Owner cascading

**Impact**: When tasks are fetched via `subtasks_async(include_detection_fields=True)`, the returned tasks lack `parent.gid`. If these tasks are later accessed via cache during hydration, `_traverse_upward_async()` fails because `task.parent.gid` is not available.

**Forces at play**:
1. **Consistency**: All code paths should have access to the same fields
2. **Performance**: Minimal field sets reduce response size and latency
3. **Maintainability**: Multiple definitions drift apart over time
4. **Cache coherence**: Cached entries should support all downstream use cases

## Decision

**We will define a single `STANDARD_TASK_OPT_FIELDS` constant in `models/business/fields.py` containing all 15 required fields, and update all consumers to import from this central location.**

The unified field set:

```python
STANDARD_TASK_OPT_FIELDS: tuple[str, ...] = (
    "name",
    "parent.gid",
    "memberships.project.gid",
    "memberships.project.name",
    "custom_fields",
    "custom_fields.name",
    "custom_fields.enum_value",
    "custom_fields.enum_value.name",
    "custom_fields.multi_enum_values",
    "custom_fields.multi_enum_values.name",
    "custom_fields.display_value",
    "custom_fields.number_value",
    "custom_fields.text_value",
    "custom_fields.resource_subtype",
    "custom_fields.people_value",
)
```

Additionally, a minimal 4-field `DETECTION_OPT_FIELDS` subset is preserved for performance-sensitive initial fetches where custom_fields are not yet needed.

## Rationale

### Why Unified Field Set?

1. **Single source of truth**: Any future field additions only require one change
2. **Cache coherence**: Any cached task can support any operation (detection, traversal, cascading)
3. **Eliminates class of bugs**: The `parent.gid` gap demonstrates how field set drift causes runtime failures
4. **Testable**: Simple assertions can verify all consumers use the same field set

### Why `fields.py` as Location?

The existing `models/business/fields.py` module:
- Already defines field-related constructs (`CascadingFieldDef`, `InheritedFieldDef`)
- Has no dependencies on clients or complex model hierarchy (import-safe)
- Is semantically appropriate: field sets belong with field definitions
- Avoids new module creation overhead

### Why Tuple, Not List?

- **Immutability**: Prevents accidental modification during iteration or merging
- **Hashability**: Can be used in sets or as dict keys if needed
- **Intent signal**: Explicit that this is a fixed, read-only constant

### Why Keep Minimal `DETECTION_OPT_FIELDS`?

The hydration entry point (`hydrate_from_gid_async`) performs an initial task fetch just to detect entity type. For this initial fetch, the full custom_fields are unnecessary overhead. The minimal 4-field set:
- `name` - Tier 2 detection
- `parent.gid` - Traversal preparation
- `memberships.project.gid` - Tier 1 detection
- `memberships.project.name` - ProcessType detection

Keeping this small set optimizes the common case where detection is sufficient before a full re-fetch.

## Alternatives Considered

### Option A: Add Missing Fields to TasksClient Only

**Description**: Simply add `parent.gid` and `custom_fields.people_value` to `TasksClient._DETECTION_FIELDS` without creating a central constant.

**Pros**:
- Minimal code change (2 lines)
- No new abstractions
- Immediate fix for the bug

**Cons**:
- Perpetuates fragmentation
- Next field addition will require changes in multiple places
- No guarantee of consistency

**Why not chosen**: This is a band-aid that doesn't address the root cause. The same class of bug will recur.

### Option B: Field Inheritance with Base + Extension

**Description**: Define a base `_BASE_DETECTION_FIELDS` and compose full sets by extension:
```python
_BASE_DETECTION_FIELDS = ["name", "parent.gid", "memberships..."]
_FULL_FIELDS = _BASE_DETECTION_FIELDS + ["custom_fields", ...]
```

**Pros**:
- Clear hierarchical relationship
- Smaller base set for performance paths
- Extensible pattern

**Cons**:
- List concatenation creates new list on every use (memory/performance)
- Harder to reason about final field set
- Still requires discipline to use base vs. full appropriately

**Why not chosen**: The tuple approach is simpler and the "minimal vs. full" distinction is better served by two explicit constants rather than composition at runtime.

### Option C: Field Registry Class

**Description**: Create a `FieldRegistry` class that manages field sets with methods like `get_detection_fields()`, `get_full_fields()`, `get_fields_for_operation(op)`.

**Pros**:
- Full encapsulation
- Could add validation logic
- Extensible for future field set variations

**Cons**:
- Over-engineered for the problem
- Adds indirection
- Class overhead for what is fundamentally constant data

**Why not chosen**: YAGNI. Constants are sufficient; a class adds complexity without benefit.

## Consequences

### Positive

1. **Bug fix**: `parent.gid` and `people_value` will be available in all detection paths
2. **Single source of truth**: Future field additions require one change
3. **Testable invariants**: Unit tests can assert field set consistency
4. **Documentation**: The constant serves as authoritative field specification
5. **Backward compatible**: Existing code continues to work; aliases provided for deprecated names

### Negative

1. **Response size increase**: Adding `parent.gid` (small) and `people_value` (potentially larger) increases response size slightly
   - Mitigation: Measured as <5% increase; acceptable tradeoff
2. **Import dependency**: `clients/tasks.py` now imports from `models/business/fields.py`
   - Mitigation: `fields.py` has no dependencies; import is safe
3. **Deprecation debt**: Old constants remain as aliases until removed
   - Mitigation: Mark clearly in code; remove in future version

### Neutral

1. Field definitions move from inline constants to imported constants
2. Tests may need to import `STANDARD_TASK_OPT_FIELDS` for assertions
3. Documentation will reference the new constant names

## Compliance

How do we ensure this decision is followed?

1. **Unit test**: `test_tasks_detection_uses_standard_fields` asserts `set(TasksClient._DETECTION_FIELDS) == set(STANDARD_TASK_OPT_FIELDS)`
2. **Code review checklist**: Any new `opt_fields` usage should reference `STANDARD_TASK_OPT_FIELDS` or `DETECTION_OPT_FIELDS`
3. **Documentation**: TDD-CACHE-PERF-HYDRATION specifies the pattern
4. **Linting** (future): Could add custom lint rule to flag inline opt_fields definitions
