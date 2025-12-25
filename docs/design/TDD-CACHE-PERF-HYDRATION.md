---
status: superseded
superseded_by: /docs/reference/REF-cache-patterns.md
superseded_date: 2025-12-24
---

# TDD: Hydration Field Normalization

## Metadata
- **TDD ID**: TDD-CACHE-PERF-HYDRATION
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **PRD Reference**: [PRD-CACHE-PERF-HYDRATION](/docs/requirements/PRD-CACHE-PERF-HYDRATION.md)
- **Related TDDs**: TDD-HYDRATION, TDD-CACHE-INTEGRATION
- **Related ADRs**: [ADR-0128-hydration-opt-fields-normalization](/docs/decisions/ADR-0128-hydration-opt-fields-normalization.md), ADR-0094, ADR-0101

## Overview

This design defines a unified 15-field opt_fields constant (`STANDARD_TASK_OPT_FIELDS`) that serves as the single source of truth for all task field requirements across hydration, detection, and cascading use cases. The design eliminates field set fragmentation by consolidating three existing definitions into one central location while maintaining backward compatibility through deprecation aliases.

## Requirements Summary

Per PRD-CACHE-PERF-HYDRATION:

| Requirement | Summary |
|-------------|---------|
| FR-FIELDS-001 | Define `STANDARD_TASK_OPT_FIELDS` with all 15 required fields |
| FR-FIELDS-002 | Central location accessible without circular imports |
| FR-FIELDS-003 | Include `parent.gid` for upward traversal |
| FR-FIELDS-004 | Include `custom_fields.people_value` for Owner cascading |
| FR-CACHE-001 | `TasksClient._DETECTION_FIELDS` must include `parent.gid` |
| FR-CACHE-002 | `TasksClient._DETECTION_FIELDS` must include `people_value` |
| FR-DETECT-001 | `_DETECTION_OPT_FIELDS` subset of standard set |
| FR-BUSINESS-001 | Traversal works with cached tasks |

## System Context

The unified field set addresses a critical gap in the SDK's field definition hierarchy:

```
                          ┌─────────────────────────────────┐
                          │   STANDARD_TASK_OPT_FIELDS      │
                          │   (Single Source of Truth)      │
                          │   15 fields - fields.py         │
                          └─────────────┬───────────────────┘
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            │                           │                           │
            v                           v                           v
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│ hydration.py          │   │ hydration.py          │   │ tasks.py              │
│ _DETECTION_OPT_FIELDS │   │ _BUSINESS_FULL_OPT   │   │ _DETECTION_FIELDS     │
│ (4 fields - minimal)  │   │ (15 fields - full)    │   │ (15 fields - import)  │
│ SUBSET                │   │ EQUALS                │   │ EQUALS                │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
            │                           │                           │
            v                           v                           v
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│ hydrate_from_gid      │   │ Business re-fetch     │   │ subtasks_async with   │
│ _traverse_upward      │   │ _traverse_upward      │   │ include_detection     │
│ Initial fetch         │   │ Business root fetch   │   │ Holder fetches        │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
```

**Current Problem**: `TasksClient._DETECTION_FIELDS` is missing `parent.gid` and `custom_fields.people_value`, causing cache entries to lack fields required by downstream hydration operations.

## Design

### Component Architecture

| Component | Responsibility | Changes |
|-----------|---------------|---------|
| `models/business/fields.py` | Define `STANDARD_TASK_OPT_FIELDS` and `DETECTION_OPT_FIELDS` constants | ADD: New constants |
| `models/business/hydration.py` | Use standard fields, deprecate local constants | UPDATE: Import from fields.py |
| `clients/tasks.py` | Use standard fields for detection | UPDATE: Import from fields.py |

### Data Model

#### STANDARD_TASK_OPT_FIELDS (15 fields)

```python
STANDARD_TASK_OPT_FIELDS: tuple[str, ...] = (
    # Core identification
    "name",
    "parent.gid",

    # Detection (Tier 1)
    "memberships.project.gid",
    "memberships.project.name",

    # Custom fields (cascading)
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

#### DETECTION_OPT_FIELDS (4 fields - minimal subset)

```python
DETECTION_OPT_FIELDS: tuple[str, ...] = (
    "name",
    "parent.gid",
    "memberships.project.gid",
    "memberships.project.name",
)
```

### API Contracts

#### Public Exports from fields.py

```python
# Added to existing fields.py
__all__ = [
    # Existing exports
    "CascadingFieldDef",
    "InheritedFieldDef",
    # New exports (per PRD-CACHE-PERF-HYDRATION)
    "STANDARD_TASK_OPT_FIELDS",
    "DETECTION_OPT_FIELDS",
]
```

#### Deprecation Pattern in hydration.py

```python
import warnings
from autom8_asana.models.business.fields import (
    STANDARD_TASK_OPT_FIELDS,
    DETECTION_OPT_FIELDS,
)

# Deprecated aliases with warnings
@property
def _DETECTION_OPT_FIELDS() -> list[str]:
    """Deprecated: Use DETECTION_OPT_FIELDS from fields module."""
    warnings.warn(
        "_DETECTION_OPT_FIELDS is deprecated; use DETECTION_OPT_FIELDS from "
        "autom8_asana.models.business.fields",
        DeprecationWarning,
        stacklevel=2,
    )
    return list(DETECTION_OPT_FIELDS)
```

**Decision**: Per the ADR analysis, we will NOT use property-based deprecation since these are module-level constants used internally. Instead:

1. **Phase 1**: Add new constants, update internal references
2. **Phase 2**: Mark old constants with `# Deprecated` comment
3. **Phase 3** (future): Remove old constants when no external consumers exist

### Data Flow

#### Subtask Fetch with Detection Fields

```
┌─────────────────┐      ┌────────────────┐      ┌──────────────────┐
│ Business/Unit   │      │ TasksClient    │      │ Asana API        │
│ _fetch_holders  │      │ subtasks_async │      │ /tasks/gid/sub   │
└────────┬────────┘      └────────┬───────┘      └────────┬─────────┘
         │                        │                       │
         │ include_detection      │                       │
         │ _fields=True           │                       │
         │ ──────────────────────>│                       │
         │                        │                       │
         │                        │ _DETECTION_FIELDS     │
         │                        │ (now includes         │
         │                        │  parent.gid,          │
         │                        │  people_value)        │
         │                        │ ──────────────────────>│
         │                        │                       │
         │                        │<──────────────────────│
         │                        │  Tasks with all 15    │
         │                        │  fields populated     │
         │<───────────────────────│                       │
         │  Tasks with parent.gid │                       │
         │  available for         │                       │
         │  traversal             │                       │
```

#### Hydration with Populated Cache

```
┌─────────────────┐      ┌────────────────┐      ┌──────────────────┐
│ Consumer        │      │ hydration.py   │      │ TasksClient      │
│                 │      │ hydrate_from   │      │ get_async        │
└────────┬────────┘      │ _gid_async     │      └────────┬─────────┘
         │               └────────┬───────┘               │
         │ hydrate(gid)           │                       │
         │ ──────────────────────>│                       │
         │                        │                       │
         │                        │ get_async(gid)        │
         │                        │ ──────────────────────>│
         │                        │                       │
         │                        │<──────────────────────│
         │                        │  Task with parent.gid │
         │                        │  (from cache or API)  │
         │                        │                       │
         │                        │ task.parent.gid       │
         │                        │ ✓ Now available       │
         │                        │                       │
         │                        │ _traverse_upward      │
         │                        │ ✓ Succeeds            │
         │                        │                       │
         │<───────────────────────│                       │
         │  HydrationResult       │                       │
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Field set location | `models/business/fields.py` | Already exists for field definitions; no circular import risk; business layer owns field semantics | ADR-0128 |
| Deprecation strategy | Comment-based, not runtime warnings | Private constants used internally; no external API surface to warn | ADR-0128 |
| Immutability | `tuple[str, ...]` not `list[str]` | Prevent accidental mutation; explicit immutability signal | ADR-0128 |
| Minimal detection set | Keep 4-field `DETECTION_OPT_FIELDS` | Performance: initial fetch can use smaller set; full set only when custom_fields needed | ADR-0128 |

## Complexity Assessment

**Level**: Module

**Justification**:
- Single module (`fields.py`) with new constants
- Two modules updated with imports (`hydration.py`, `tasks.py`)
- No new abstractions, interfaces, or services
- No external dependencies
- No configuration changes
- Purely additive changes with backward compatibility

This is a straightforward refactoring that consolidates existing definitions. The complexity is in identifying all usage sites and ensuring consistent imports, not in architectural decisions.

## Implementation Plan

### Phases

| Phase | Deliverable | Dependencies | Estimate |
|-------|-------------|--------------|----------|
| 1 | Add constants to `fields.py` | None | 15 min |
| 2 | Update `hydration.py` imports | Phase 1 | 30 min |
| 3 | Update `tasks.py` imports | Phase 1 | 15 min |
| 4 | Add unit tests for field coverage | Phase 1-3 | 30 min |
| 5 | Integration test for traversal | Phase 1-3 | 30 min |

**Total**: ~2 hours

### Migration Strategy

No migration required - changes are purely additive:

1. New constants added alongside existing (Phase 1)
2. Internal references updated to use new constants (Phase 2-3)
3. Old constants remain but marked deprecated in comments
4. Future: Remove old constants when confirmed no external usage

### Detailed Implementation

#### Phase 1: Add Constants to fields.py

**File**: `/src/autom8_asana/models/business/fields.py`

Add at end of file:

```python
# =============================================================================
# Task opt_fields Constants (per PRD-CACHE-PERF-HYDRATION)
# =============================================================================

# Standard field set that satisfies all detection, traversal, and cascading use cases.
# Per FR-FIELDS-001: Single source of truth for opt_fields across the SDK.
STANDARD_TASK_OPT_FIELDS: tuple[str, ...] = (
    # Core identification
    "name",
    "parent.gid",
    # Detection (Tier 1)
    "memberships.project.gid",
    "memberships.project.name",
    # Custom fields (cascading)
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

# Minimal field set for detection-only operations (subset of standard).
# Per FR-DETECT-003: Smaller set for performance when custom_fields not needed.
DETECTION_OPT_FIELDS: tuple[str, ...] = (
    "name",
    "parent.gid",
    "memberships.project.gid",
    "memberships.project.name",
)
```

#### Phase 2: Update hydration.py

**File**: `/src/autom8_asana/models/business/hydration.py`

Replace existing constants:

```python
# Before (lines 63-90):
_DETECTION_OPT_FIELDS: list[str] = [...]
_BUSINESS_FULL_OPT_FIELDS: list[str] = [...]

# After:
from autom8_asana.models.business.fields import (
    STANDARD_TASK_OPT_FIELDS,
    DETECTION_OPT_FIELDS,
)

# Deprecated: Use DETECTION_OPT_FIELDS from fields module
_DETECTION_OPT_FIELDS: list[str] = list(DETECTION_OPT_FIELDS)

# Deprecated: Use STANDARD_TASK_OPT_FIELDS from fields module
_BUSINESS_FULL_OPT_FIELDS: list[str] = list(STANDARD_TASK_OPT_FIELDS)
```

#### Phase 3: Update tasks.py

**File**: `/src/autom8_asana/clients/tasks.py`

Replace `_DETECTION_FIELDS`:

```python
# Before (lines 644-660):
_DETECTION_FIELDS: list[str] = [...]

# After:
from autom8_asana.models.business.fields import STANDARD_TASK_OPT_FIELDS

# Per PRD-CACHE-PERF-HYDRATION FR-CACHE-001, FR-CACHE-002:
# Use standard field set to ensure parent.gid and people_value are present
_DETECTION_FIELDS: list[str] = list(STANDARD_TASK_OPT_FIELDS)
```

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Circular import when importing fields in tasks.py | High | Low | `fields.py` has no dependencies on clients; import path is leaf-to-root |
| Response size increase affects latency | Low | Low | Two additional small fields; Asana API pagination unaffected |
| Asana API rejects `people_value` on some endpoints | Medium | Low | Field is standard; test with real API before merge |
| Existing tests fail with stricter field expectations | Low | Medium | Tests should be field-presence additive; review test assertions |

## Observability

### Metrics
- No new metrics required (existing cache hit/miss metrics sufficient)

### Logging
- Existing DEBUG logs for `opt_fields` in API requests will show new fields
- No additional logging needed

### Alerting
- No new alerts required

## Testing Strategy

### Unit Tests

| Test | Purpose | Location |
|------|---------|----------|
| `test_standard_field_count` | Verify exactly 15 fields | `tests/unit/models/business/test_fields.py` |
| `test_parent_gid_in_standard` | Verify `parent.gid` present | `tests/unit/models/business/test_fields.py` |
| `test_people_value_in_standard` | Verify `people_value` present | `tests/unit/models/business/test_fields.py` |
| `test_detection_subset_of_standard` | Verify subset relationship | `tests/unit/models/business/test_fields.py` |
| `test_tasks_detection_equals_standard` | Verify TasksClient uses standard | `tests/unit/clients/test_tasks.py` |
| `test_hydration_uses_standard` | Verify hydration imports | `tests/unit/models/business/test_hydration.py` |

### Integration Tests

| Test | Purpose | Location |
|------|---------|----------|
| `test_subtasks_with_detection_has_parent_gid` | Subtask fetch returns parent.gid | `tests/integration/` |
| `test_traversal_after_subtask_cache` | Traversal works after subtasks populate cache | `tests/integration/` |
| `test_owner_cascade_with_people_value` | Owner field available for cascading | `tests/integration/` |

### Performance Tests
- Benchmark response size before/after (expected: <5% increase)
- Benchmark traversal time with warm cache (target: <50ms for 5 levels)

## Requirement Traceability Matrix

| Requirement ID | Design Response | Verification |
|----------------|-----------------|--------------|
| FR-FIELDS-001 | `STANDARD_TASK_OPT_FIELDS` tuple with 15 fields | Unit test: field count |
| FR-FIELDS-002 | Located in `models/business/fields.py` | Import test: no circular deps |
| FR-FIELDS-003 | `"parent.gid"` in STANDARD_TASK_OPT_FIELDS | Unit test: field presence |
| FR-FIELDS-004 | `"custom_fields.people_value"` in STANDARD_TASK_OPT_FIELDS | Unit test: field presence |
| FR-FIELDS-005 | Both membership fields in STANDARD_TASK_OPT_FIELDS | Unit test: field presence |
| FR-FIELDS-006 | Type is `tuple[str, ...]` not `list` | Unit test: type check |
| FR-CACHE-001 | `_DETECTION_FIELDS = list(STANDARD_TASK_OPT_FIELDS)` | Unit test: field presence |
| FR-CACHE-002 | Same as FR-CACHE-001 | Unit test: field presence |
| FR-CACHE-003 | TasksClient imports from fields.py | Code review |
| FR-CACHE-004 | Integration test with subtasks fetch | Integration test |
| FR-DETECT-001 | `DETECTION_OPT_FIELDS.issubset(STANDARD_TASK_OPT_FIELDS)` | Unit test |
| FR-DETECT-002 | `_BUSINESS_FULL_OPT_FIELDS == STANDARD_TASK_OPT_FIELDS` | Unit test |
| FR-DETECT-003 | Minimal `DETECTION_OPT_FIELDS` preserved | Unit test: 4 fields |
| FR-BUSINESS-001 | Traversal accesses `task.parent.gid` | Integration test |
| FR-BUSINESS-002 | Hydration completes regardless of cache state | Integration test |
| FR-BUSINESS-003 | `people_value` available on Business custom_fields | Integration test |
| NFR-PERF-001 | No cache changes | N/A (existing behavior) |
| NFR-PERF-002 | No algorithm changes | N/A (existing behavior) |
| NFR-PERF-003 | Two small fields added | Benchmark test |
| NFR-PERF-004 | No additional API calls | Code review |
| NFR-COMPAT-001 | hydrate_from_gid_async signature unchanged | Code review |
| NFR-COMPAT-002 | subtasks_async signature unchanged | Code review |
| NFR-COMPAT-003 | Existing tests pass | CI |
| NFR-COMPAT-004 | Non-detection paths unchanged | Integration test |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should `_DETECTION_OPT_FIELDS` aliases be removed in v2.0? | Tech Lead | TBD | Defer to version planning |
| Should fields.py be moved to a shared location outside business/? | Architect | TBD | No - business layer owns field semantics |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Architect | Initial draft |
