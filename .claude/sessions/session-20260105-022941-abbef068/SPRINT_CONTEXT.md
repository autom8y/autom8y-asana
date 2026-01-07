---
sprint_id: sprint-sdk-cascade-fix-20260105
session_id: session-20260105-022941-abbef068
sprint_name: SDK Cascade Resolution Fix
sprint_goal: Fix office_phone cascade for Units by fixing SDK list_async() opt_fields propagation; generalize for all cascade users (Unit, Offer, Process, Contact)
initiative: SDK Cascade Resolution Fix
complexity: MODULE
active_team: 10x-dev-pack
workflow: sequential
status: active
created_at: 2026-01-05T02:31:15Z
parent_session: session-20260105-022941-abbef068
schema_version: "1.0"
tasks:
  - id: task-001
    name: Architect updates TDD with SDK hydration fix design
    status: completed
    complexity: MODULE
    artifacts:
      - docs/design/TDD-sdk-cascade-resolution.md
    completed_at: 2026-01-05T02:45:00Z
  - id: task-002
    name: Investigate unified_store parent chain caching requirements
    status: completed
    complexity: MODULE
    artifacts:
      - docs/design/TDD-sdk-cascade-resolution.md
    completed_at: 2026-01-05T02:45:00Z
    notes: "Architecture is production-ready. CascadeViewPlugin pattern exists. HierarchyIndex handles parent-child. get_parent_chain_async() already implemented. No gaps found."
  - id: task-003
    name: Engineer fixes list_async() opt_fields propagation in SDK
    status: completed
    complexity: MODULE
    artifacts:
      - src/autom8_asana/asana_sdk/asana.py
    completed_at: 2026-01-05T07:30:00Z
    notes: "Added _MINIMUM_OPT_FIELDS constant with parent.gid; Added _resolve_opt_fields() helper; Updated list_async(), subtasks_async(), dependents_async(); All 485 unit tests pass"
  - id: task-004
    name: Engineer adds iterative parent fetching with cache/TTL
    status: superseded
    complexity: MODULE
    artifacts: []
    notes: "SUPERSEDED by ADR-hierarchy-registration-architecture: Architecture decision established storage-layer eager warming approach. Original iterative parent fetching approach no longer needed."
  - id: task-005
    name: Engineer updates CascadingFieldDef with max_depth config
    status: superseded
    complexity: MODULE
    artifacts: []
    notes: "SUPERSEDED by ADR-hierarchy-registration-architecture: max_depth config replaced by HierarchyWarmer recursive approach with configurable max_depth in warmer component."
  - id: task-006
    name: QA creates mock-based unit tests for cascade resolution
    status: pending
    complexity: MODULE
    artifacts: []
  - id: task-007
    name: QA validates 5 random Units with Business parents
    status: pending
    complexity: MODULE
    artifacts: []
  - id: task-008
    name: QA runs integration test POST /v1/resolve/unit
    status: pending
    complexity: MODULE
    artifacts: []
  - id: task-009
    name: Implement HierarchyWarmer component
    status: pending
    complexity: MODULE
    artifacts: []
    notes: "Create HierarchyWarmer dataclass in autom8_asana/cache/hierarchy_warmer.py per ADR-hierarchy-registration-architecture. Implements recursive parent fetching with cycle detection and max_depth=5."
  - id: task-010
    name: Add warm_hierarchy parameter to put_batch_async()
    status: pending
    complexity: MODULE
    artifacts: []
    notes: "Augment UnifiedTaskStore.put_batch_async() with tasks_client and warm_hierarchy parameters. Add _warm_hierarchy_batch_async() method for batch parent warming."
  - id: task-011
    name: Wire warming in ProjectDataFrameBuilder
    status: pending
    complexity: MODULE
    artifacts: []
    notes: "Update ProjectDataFrameBuilder._build_with_unified_store_async() to pass tasks_client and enable warm_hierarchy=True for automatic cascade resolution."
completed_tasks: 3
total_tasks: 11
---

# Sprint: SDK Cascade Resolution Fix

## Sprint Overview

This sprint addresses cascade field resolution issues in the SDK, specifically fixing `office_phone` cascade for Units and generalizing the solution for all cascade users.

## Sprint Goal

Fix office_phone cascade for Units by fixing SDK list_async() opt_fields propagation; generalize for all cascade users (Unit, Offer, Process, Contact).

## Tasks Breakdown

### Phase 1: Design & Investigation (Tasks 001-002)
- **task-001**: Architect updates TDD with SDK hydration fix design
  - Review existing TDD-ttl-detection-extraction.md
  - Design SDK list_async() opt_fields propagation mechanism
  - Define unified_store caching strategy

- **task-002**: Investigate unified_store parent chain caching requirements
  - Analyze parent entity fetching patterns
  - Design cache/TTL requirements
  - Document cache invalidation strategy

### Phase 2: Implementation (Tasks 003-005)
- **task-003**: Engineer fixes list_async() opt_fields propagation in SDK
  - Modify SDK list_async() to propagate opt_fields
  - Ensure compatibility with existing cascade resolution

- **task-004**: Engineer adds iterative parent fetching with cache/TTL
  - Implement unified_store parent chain caching
  - Add TTL-based cache invalidation
  - Support iterative parent fetching

- **task-005**: Engineer updates CascadingFieldDef with max_depth config
  - Add max_depth configuration option
  - Update cascade resolution logic
  - Document configuration usage

### Phase 3: Quality Assurance (Tasks 006-008)
- **task-006**: QA creates mock-based unit tests for cascade resolution
  - Write unit tests with mocked SDK responses
  - Cover edge cases (missing parents, deep nesting)
  - Validate max_depth enforcement

- **task-007**: QA validates 5 random Units with Business parents
  - Test real-world cascade resolution
  - Verify office_phone propagation
  - Document test results

- **task-008**: QA runs integration test POST /v1/resolve/unit
  - Execute integration test suite
  - Verify end-to-end cascade resolution
  - Confirm all entity types work correctly

## Success Criteria

1. SDK list_async() properly propagates opt_fields parameter
2. unified_store implements parent chain caching with TTL
3. CascadingFieldDef supports max_depth configuration
4. All cascade users (Unit, Offer, Process, Contact) resolve correctly
5. Integration tests pass for all entity types
6. Unit tests cover edge cases and error scenarios

## Dependencies

- Existing TDD: docs/design/TDD-ttl-detection-extraction.md
- SDK codebase access
- unified_store implementation
- CascadingFieldDef implementation

## Notes

- Sprint follows sequential workflow (design -> implement -> test)
- 1-week duration
- Focus on generalization across all cascade users
- Priority: Fix office_phone cascade for Units first, then generalize

## Phase 1 Completion (2026-01-05)

**Status**: COMPLETE

**Key Findings**:
1. **TDD Design**: 3-component architecture established
   - Component 1: SDK list_async() opt_fields propagation fix
   - Component 2: unified_store integration via CascadeViewPlugin
   - Component 3: max_depth configuration in CascadingFieldDef

2. **unified_store Investigation**: Architecture is production-ready
   - CascadeViewPlugin pattern exists and is recommended
   - HierarchyIndex handles parent-child relationships
   - get_parent_chain_async() already implemented
   - No architectural gaps identified

3. **Critical Insight**: The unified_store is NOT the problem
   - Only fix needed: SDK list_async() opt_fields propagation
   - Everything else already exists in production-ready form

**Next Phase**: Phase 2 Implementation (tasks 003-005)
- Task 003: Fix SDK list_async() opt_fields propagation
- Task 004: Integrate unified_store via CascadeViewPlugin pattern
- Task 005: Add max_depth config to CascadingFieldDef

## Phase 2 Completion (2026-01-05)

**Status**: COMPLETE (Minimal Fix Approach)

**Completed Tasks**:
1. **task-003**: SDK opt_fields propagation fix
   - Added `_MINIMUM_OPT_FIELDS = ["parent.gid"]` constant
   - Implemented `_resolve_opt_fields()` helper method
   - Updated `list_async()`, `subtasks_async()`, `dependents_async()`
   - All 485 unit tests pass
   - Artifact: `src/autom8_asana/asana_sdk/asana.py`

**Deferred Tasks**:
1. **task-004**: Parent fetching with cache/TTL
   - Reason: CascadeViewPlugin already handles parent chain caching
   - `get_parent_chain_async()` is production-ready via unified_store
   - No additional implementation needed
   - Will re-evaluate after validation

2. **task-005**: max_depth configuration
   - Reason: Validate minimal fix first
   - If opt_fields fix resolves cascade issues, max_depth may be unnecessary
   - Will re-evaluate based on Phase 3 validation results

**Key Decision**: Minimal fix approach
- Only fix SDK opt_fields propagation (task-003)
- Defer tasks 004-005 until validation proves necessity
- Reduces complexity, faster validation cycle

**Sprint Progress**: 3/8 tasks completed (37.5%), 2 deferred

**Next Phase**: Phase 3 Validation (tasks 006-008)
- Task 006: Mock-based unit tests for cascade resolution
- Task 007: Validate 5 random Units with Business parents
- Task 008: Integration test POST /v1/resolve/unit

## Architectural Decision (2026-01-05)

**Root Cause**: Non-transitive hierarchy registration
- SDK correctly fetches parent.gid via _BASE_OPT_FIELDS
- UnifiedTaskStore.put_batch_async() registers immediate parent relationships
- BUT parent's ancestors are never fetched or registered
- Result: get_ancestor_chain() returns partial chains, cascade resolution fails

**Decision**: Storage-layer eager hierarchy warming via HierarchyWarmer component
- Implement HierarchyWarmer for recursive parent fetching with cycle detection
- Augment put_batch_async() with warm_hierarchy=True parameter
- Wire into ProjectDataFrameBuilder for automatic cascade resolution
- Batch-optimize parent fetching to minimize API calls

**ADR**: docs/design/ADR-hierarchy-registration-architecture.md (Status: Proposed)

**Impact on Sprint**:
- Tasks 004-005 superseded by architectural decision
- New implementation path: HierarchyWarmer component (task-009) + storage integration (task-010) + builder wiring (task-011)
- Sprint progress: 3/11 tasks complete (27%)
- Architecture decision de-risks implementation phase

**Next Steps**: Implement HierarchyWarmer component (task-009)
