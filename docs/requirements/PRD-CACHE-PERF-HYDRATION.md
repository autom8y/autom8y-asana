---
status: superseded
superseded_by: /docs/reference/REF-cache-patterns.md
superseded_date: 2025-12-24
---

# PRD: Hydration Field Normalization

## Metadata
- **PRD ID**: PRD-CACHE-PERF-HYDRATION
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **Stakeholders**: SDK consumers, autom8 platform team
- **Related PRDs**: PRD-CACHE-PERF-DETECTION, PRD-CACHE-INTEGRATION, PRD-0013-hierarchy-hydration
- **Discovery Document**: [hydration-cache-opt-fields-analysis.md](/docs/analysis/hydration-cache-opt-fields-analysis.md)
- **Parent Initiative**: [PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md](/docs/initiatives/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md)

---

## Problem Statement

### What Problem Are We Solving?

Three separate `opt_fields` definitions exist across the codebase (`_DETECTION_OPT_FIELDS`, `_BUSINESS_FULL_OPT_FIELDS`, `TasksClient._DETECTION_FIELDS`), creating a **critical gap** where `parent.gid` is missing from `TasksClient._DETECTION_FIELDS`. This causes potential failures when cached task data lacks fields required for upward traversal in `hydrate_from_gid_async()`.

### For Whom?

SDK consumers performing:
- Business hierarchy hydration via `hydrate_from_gid_async()`
- Upward traversal operations via `_traverse_upward_async()`
- Any code path that relies on `parent.gid` being present on Task objects

### Root Cause (from Discovery)

1. **Field set fragmentation**: Three independent field definitions with no single source of truth
2. **Missing `parent.gid`**: `TasksClient._DETECTION_FIELDS` lacks `parent.gid` (required for traversal)
3. **Missing `custom_fields.people_value`**: `TasksClient._DETECTION_FIELDS` lacks people field (required for Owner cascading)
4. **No field validation on cache retrieval**: Cache returns ignore `opt_fields` parameter - cached data returned regardless of what fields were requested

### Impact of Not Solving

- **Runtime Errors**: Upward traversal fails with `NoneType` error when `parent.gid` missing from cached task
- **Data Gaps**: People field values unavailable in cached entries, breaking Owner cascading
- **Maintenance Burden**: Three field definitions to maintain, easy to introduce inconsistencies
- **Unpredictable Behavior**: Same task returns different fields depending on how it was first fetched

---

## Goals & Success Metrics

### Primary Goal

Define a single **Unified Standard Field Set** that satisfies all detection, traversal, and cascading use cases, then implement it consistently across all field definitions.

### Success Metrics

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| Field set definitions | 3 independent | 1 unified | Code review: single source of truth |
| `parent.gid` in all fetch paths | Missing from TasksClient | Always present | Unit test: field presence validation |
| `people_value` in all fetch paths | Missing from TasksClient | Always present | Unit test: field presence validation |
| Traversal success rate | Potential failures | 100% | Integration test: traversal completes |
| Cached vs fresh field parity | Inconsistent | Identical | Integration test: field comparison |

---

## Scope

### In Scope

- Define `STANDARD_TASK_OPT_FIELDS` constant (15 fields) in central location
- Update `_DETECTION_OPT_FIELDS` to import from standard set
- Update `_BUSINESS_FULL_OPT_FIELDS` to import from standard set
- Update `TasksClient._DETECTION_FIELDS` to import from standard set
- Add `parent.gid` to all field sets
- Add `custom_fields.people_value` to TasksClient field set
- Ensure all hydration and detection paths use consistent fields

### Out of Scope

- Cache key changes (not needed - GID-based keys are correct)
- New cache entry types (detection caching is separate initiative)
- Detection caching changes (covered by PRD-CACHE-PERF-DETECTION)
- Field-aware cache validation (checking if cached entry has requested fields)
- Changes to cache TTL or versioning strategy
- Modifications to `subtasks_async()` caching behavior

---

## Requirements

### Functional Requirements

#### FR-FIELDS: Unified Field Set Definition

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-FIELDS-001 | The system SHALL define a constant `STANDARD_TASK_OPT_FIELDS` containing all 15 required fields. | Must | **GIVEN** the fields module **WHEN** `STANDARD_TASK_OPT_FIELDS` is accessed **THEN** it contains exactly: `name`, `parent.gid`, `memberships.project.gid`, `memberships.project.name`, `custom_fields`, `custom_fields.name`, `custom_fields.enum_value`, `custom_fields.enum_value.name`, `custom_fields.multi_enum_values`, `custom_fields.multi_enum_values.name`, `custom_fields.display_value`, `custom_fields.number_value`, `custom_fields.text_value`, `custom_fields.resource_subtype`, `custom_fields.people_value`. |
| FR-FIELDS-002 | `STANDARD_TASK_OPT_FIELDS` SHALL be defined in a central location accessible to all consumers. | Must | **GIVEN** `autom8_asana/models/business/fields.py` exists **WHEN** other modules import `STANDARD_TASK_OPT_FIELDS` **THEN** import succeeds without circular dependencies. |
| FR-FIELDS-003 | The field set SHALL include `parent.gid` for upward traversal support. | Must | **GIVEN** `STANDARD_TASK_OPT_FIELDS` **WHEN** inspected **THEN** `"parent.gid"` is present in the list. |
| FR-FIELDS-004 | The field set SHALL include `custom_fields.people_value` for Owner cascading support. | Must | **GIVEN** `STANDARD_TASK_OPT_FIELDS` **WHEN** inspected **THEN** `"custom_fields.people_value"` is present in the list. |
| FR-FIELDS-005 | The field set SHALL include all Tier 1 detection fields (`memberships.project.gid`, `memberships.project.name`). | Must | **GIVEN** `STANDARD_TASK_OPT_FIELDS` **WHEN** inspected **THEN** both `"memberships.project.gid"` and `"memberships.project.name"` are present. |
| FR-FIELDS-006 | The field set SHALL be immutable (tuple, not list) to prevent accidental modification. | Should | **GIVEN** `STANDARD_TASK_OPT_FIELDS` **WHEN** `type()` is called **THEN** result is `tuple`. |

#### FR-CACHE: Cache Field Consistency

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-001 | `TasksClient._DETECTION_FIELDS` SHALL include `parent.gid`. | Must | **GIVEN** `TasksClient._DETECTION_FIELDS` **WHEN** inspected **THEN** `"parent.gid"` is present in the list. |
| FR-CACHE-002 | `TasksClient._DETECTION_FIELDS` SHALL include `custom_fields.people_value`. | Must | **GIVEN** `TasksClient._DETECTION_FIELDS` **WHEN** inspected **THEN** `"custom_fields.people_value"` is present in the list. |
| FR-CACHE-003 | `TasksClient._DETECTION_FIELDS` SHALL be derived from or equal to `STANDARD_TASK_OPT_FIELDS`. | Should | **GIVEN** both field sets **WHEN** compared **THEN** `set(TasksClient._DETECTION_FIELDS) == set(STANDARD_TASK_OPT_FIELDS)`. |
| FR-CACHE-004 | Tasks fetched via `subtasks_async(include_detection_fields=True)` SHALL have `parent.gid` populated. | Must | **GIVEN** a subtask fetch with `include_detection_fields=True` **WHEN** task is returned **THEN** `task.parent` is not None and `task.parent.gid` is present (for non-root tasks). |

#### FR-DETECT: Detection Field Alignment

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DETECT-001 | `hydration._DETECTION_OPT_FIELDS` SHALL be a subset of `STANDARD_TASK_OPT_FIELDS`. | Must | **GIVEN** both field sets **WHEN** compared **THEN** `set(_DETECTION_OPT_FIELDS).issubset(set(STANDARD_TASK_OPT_FIELDS))` is True. |
| FR-DETECT-002 | `hydration._BUSINESS_FULL_OPT_FIELDS` SHALL equal `STANDARD_TASK_OPT_FIELDS`. | Should | **GIVEN** both field sets **WHEN** compared **THEN** `set(_BUSINESS_FULL_OPT_FIELDS) == set(STANDARD_TASK_OPT_FIELDS)`. |
| FR-DETECT-003 | Detection operations SHALL continue to use minimal fields where appropriate for performance. | Should | **GIVEN** hydration entry point **WHEN** initial task fetch occurs **THEN** only detection fields are requested (not full custom_fields unless Business re-fetch). |

#### FR-BUSINESS: Business Hydration Support

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-BUSINESS-001 | `_traverse_upward_async()` SHALL successfully traverse when tasks have `parent.gid` from cache. | Must | **GIVEN** a cached task with `parent.gid` populated **WHEN** `_traverse_upward_async()` accesses `current.parent.gid` **THEN** no AttributeError is raised. |
| FR-BUSINESS-002 | `hydrate_from_gid_async()` SHALL complete successfully regardless of prior cache population path. | Must | **GIVEN** a task previously fetched via `subtasks_async()` **WHEN** `hydrate_from_gid_async()` is called for that task **THEN** hydration completes without field-related errors. |
| FR-BUSINESS-003 | Business entities SHALL have `custom_fields.people_value` available for Owner cascading. | Must | **GIVEN** a Business fetched with standard fields **WHEN** custom_fields are accessed **THEN** `people_value` is available on fields that have it. |

### Non-Functional Requirements

#### NFR-PERF: Performance Targets

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|-------------------|
| NFR-PERF-001 | Cached task lookup SHALL complete in under 5 milliseconds. | <5ms | Benchmark: `time(cache_get) < 5ms` |
| NFR-PERF-002 | Full upward traversal (5 levels, all cached) SHALL complete in under 50 milliseconds. | <50ms | Benchmark: `time(_traverse_upward_async with warm cache) < 50ms` |
| NFR-PERF-003 | Response size increase from adding 2 fields SHALL not exceed 5% of typical response. | <5% increase | Benchmark: compare response sizes before/after |
| NFR-PERF-004 | No additional API calls SHALL be required due to field normalization. | 0 additional | Code review: same number of fetches |

#### NFR-OBS: Observability

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|-------------------|
| NFR-OBS-001 | Field set used for API requests SHALL be logged at DEBUG level. | Logged | Log inspection: `opt_fields` visible in request logs |
| NFR-OBS-002 | Cache hits SHALL continue to be logged with existing patterns. | Logged | Log inspection: cache hit events visible |
| NFR-OBS-003 | Traversal operations SHALL log parent GID at each level. | Logged | Log inspection: `parent_gid` in traversal debug logs |

#### NFR-COMPAT: Backward Compatibility

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|-------------------|
| NFR-COMPAT-001 | `hydrate_from_gid_async()` function signature SHALL remain unchanged. | No changes | Code review: signature unchanged |
| NFR-COMPAT-002 | `subtasks_async()` function signature and behavior SHALL remain unchanged. | No changes | Code review: signature unchanged |
| NFR-COMPAT-003 | Existing tests SHALL continue to pass without modification. | 100% pass | CI: all tests green |
| NFR-COMPAT-004 | Tasks fetched without `include_detection_fields` SHALL continue to work as before. | No regression | Integration test: non-detection fetch paths |

---

## User Stories / Use Cases

### UC-1: Upward Traversal from Cached Task

**As a** SDK consumer,
**I want** upward traversal to work even when the task was previously fetched via subtasks,
**So that** hydration operations complete successfully regardless of cache state.

**Scenario**:
1. `subtasks_async(parent_gid, include_detection_fields=True)` fetches child tasks
2. Child tasks are returned with all standard fields including `parent.gid`
3. Later, `hydrate_from_gid_async(child_gid)` is called
4. Traversal accesses `task.parent.gid` and succeeds (previously would fail)

### UC-2: Owner Cascading with People Fields

**As a** business automation,
**I want** Owner (people_value) fields available on all fetched tasks,
**So that** cascading logic can propagate Owner assignments through the hierarchy.

**Scenario**:
1. Business is fetched with standard fields
2. Business has Owner field populated via `custom_fields.people_value`
3. Cascading logic reads Owner from Business
4. Owner is propagated to child Units and Offers

### UC-3: Consistent Field Availability

**As a** SDK developer,
**I want** a single source of truth for required fields,
**So that** I don't have to maintain multiple field definitions that can drift apart.

**Scenario**:
1. Developer needs to add a new field requirement
2. Developer updates `STANDARD_TASK_OPT_FIELDS` in one location
3. All consumers (hydration, detection, TasksClient) automatically get the new field
4. No risk of forgetting to update one of the definitions

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| Adding 2 fields (`parent.gid`, `people_value`) has minimal response size impact | Fields are small; parent.gid is already returned for subtask endpoints |
| No consumers rely on specific fields being absent | Fields are additive; presence doesn't break existing code |
| `parent.gid` is returned by Asana API when requested | Standard Asana field behavior |
| Circular import can be avoided with proper module structure | Fields module has no dependencies on other business modules |

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| `TasksClient._DETECTION_FIELDS` modifiable | SDK Team | Available |
| `hydration._DETECTION_OPT_FIELDS` modifiable | SDK Team | Available |
| `hydration._BUSINESS_FULL_OPT_FIELDS` modifiable | SDK Team | Available |
| New `fields.py` module can be created | SDK Team | Available |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should minimal detection path use fewer fields for performance? | Architect | TDD Session | Recommend: Keep minimal for entry fetch, full for traversal |
| Should we validate field presence on cache retrieval? | Architect | TDD Session | Out of scope for this PRD; potential future enhancement |

---

## Constraints

### Technical Constraints

1. **Must avoid circular imports** - Fields module must be low-level with no business model dependencies
2. **Must preserve minimal fetch path** - Entry point detection can use subset for speed
3. **Must be backward compatible** - No breaking changes to public APIs
4. **Field list must be valid Asana opt_fields** - All fields must be recognized by Asana API

### Business Constraints

1. **No additional API calls** - Field normalization must not increase API usage
2. **Minimal response size increase** - Two additional fields should have negligible impact
3. **No test modifications required** - Existing tests should pass as-is

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular import when creating fields module | Low | Medium | Place fields.py at leaf of import tree with no dependencies |
| Response size increase affects performance | Low | Low | Two small fields; benchmark to confirm |
| Some consumer relies on field absence | Very Low | Low | Fields are additive; presence doesn't break logic |
| Asana API rejects people_value on some endpoints | Low | Medium | Test with real API; fallback to endpoint-specific sets if needed |

---

## Implementation Notes

### Standard Field Set Definition

```python
# autom8_asana/models/business/fields.py

"""Standard field sets for task API requests.

Per PRD-CACHE-PERF-HYDRATION: Single source of truth for opt_fields.
"""

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

# Minimal fields for detection-only operations (subset of standard)
DETECTION_OPT_FIELDS: tuple[str, ...] = (
    "name",
    "parent.gid",
    "memberships.project.gid",
    "memberships.project.name",
)
```

### Files to Modify

| File | Change |
|------|--------|
| `src/autom8_asana/models/business/fields.py` | NEW: Create with field constants |
| `src/autom8_asana/models/business/hydration.py` | Update: Import from fields.py |
| `src/autom8_asana/clients/tasks.py` | Update: Import from fields.py or add missing fields |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Requirements Analyst | Initial draft based on Discovery analysis |

---

## Appendix A: Field Comparison Matrix

| Field | Detection (hydration) | Business Full | TasksClient Detection | Standard Set |
|-------|:--------------------:|:-------------:|:--------------------:|:------------:|
| `name` | Y | Y | Y | Y |
| `parent.gid` | Y | Y | **N** (gap) | Y |
| `memberships.project.gid` | Y | Y | Y | Y |
| `memberships.project.name` | Y | Y | Y | Y |
| `custom_fields` | N | Y | Y | Y |
| `custom_fields.name` | N | Y | Y | Y |
| `custom_fields.enum_value` | N | Y | Y | Y |
| `custom_fields.enum_value.name` | N | Y | Y | Y |
| `custom_fields.multi_enum_values` | N | Y | Y | Y |
| `custom_fields.multi_enum_values.name` | N | Y | Y | Y |
| `custom_fields.display_value` | N | Y | Y | Y |
| `custom_fields.number_value` | N | Y | Y | Y |
| `custom_fields.text_value` | N | Y | Y | Y |
| `custom_fields.resource_subtype` | N | Y | Y | Y |
| `custom_fields.people_value` | N | Y | **N** (gap) | Y |

---

## Appendix B: Acceptance Criteria Verification Matrix

| Requirement | Test Type | Automation |
|-------------|-----------|------------|
| FR-FIELDS-001 | Unit | Assert exact field list contents |
| FR-FIELDS-003 | Unit | Assert `"parent.gid" in STANDARD_TASK_OPT_FIELDS` |
| FR-FIELDS-004 | Unit | Assert `"custom_fields.people_value" in STANDARD_TASK_OPT_FIELDS` |
| FR-CACHE-001 | Unit | Assert `"parent.gid" in TasksClient._DETECTION_FIELDS` |
| FR-CACHE-004 | Integration | Fetch subtasks, assert parent.gid present |
| FR-BUSINESS-001 | Integration | Mock cached task with parent.gid, traverse |
| FR-BUSINESS-002 | Integration | Pre-populate cache via subtasks, then hydrate |
| NFR-PERF-001 | Benchmark | Timed cache lookup |
| NFR-PERF-002 | Benchmark | Timed traversal with warm cache |
| NFR-COMPAT-003 | CI | All existing tests pass |
