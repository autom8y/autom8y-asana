# Discovery: SaveSession Decomposition Analysis

**Status**: Complete
**Date**: 2025-12-19
**Analyst**: Requirements Analyst
**Source**: session.py (2193 lines, 50 methods)

---

## Executive Summary

SaveSession is a well-architected Unit of Work implementation with clear responsibility separation. The spike finding of 82% reduction potential is **VALIDATED** - most heavy lifting is already delegated to extracted components (ChangeTracker, DependencyGraph, SavePipeline, EventSystem, ActionExecutor, CascadeExecutor). The remaining 2193 lines in SaveSession itself are primarily:

1. **API Surface**: Public method wrappers that delegate to internal components (facade pattern)
2. **State Management**: Session lifecycle, configuration, internal queues
3. **Commit Orchestration**: Five-phase commit coordination with healing and automation
4. **Action Registration**: 18 action methods (add_tag, remove_tag, etc.)

**Key Finding**: The action methods (42% of code, 920 lines) are boilerplate-heavy with repeated patterns. This is the highest-value extraction target for code reduction.

---

## 1. Behavior Inventory

### 1.1 State Management (Lines 50-201)

| Behavior | Method/Property | State Touched | Must Preserve |
|----------|----------------|---------------|---------------|
| Session state machine | `SessionState` enum | `_state` | YES - OPEN/COMMITTED/CLOSED |
| Auto-heal configuration | `__init__` | `_auto_heal`, `_entity_heal_flags` | YES - opt-in healing |
| Automation configuration | `__init__` | `_automation_enabled` | YES - Phase 5 control |
| Name resolution caching | `name_resolver` property | `_name_cache`, `_name_resolver` | YES - per-session cache |
| Healing queue | `__init__`, `_queue_healing` | `_healing_queue` | YES - tuple list |

**State Invariants**:
- `_state` transitions: OPEN -> COMMITTED -> CLOSED (one-way)
- After CLOSED, all operations raise `SessionClosedError`
- `_pending_actions` cleared after successful commit (selective clearing for failures)
- `_cascade_operations` preserved on failure, cleared on success
- `_healing_queue` cleared after healing execution (success or failure)

### 1.2 Entity Registration (Lines 257-427)

| Behavior | Method | ChangeTracker Delegation | Must Preserve |
|----------|--------|--------------------------|---------------|
| Track entity | `track()` | `_tracker.track()` | YES - returns entity |
| Track with heal flag | `track(heal=...)` | Stores in `_entity_heal_flags` | YES - per-entity override |
| Recursive tracking | `_track_recursive()` | Calls `_tracker.track()` for descendants | YES - composite pattern |
| Untrack entity | `untrack()` | `_tracker.untrack()` | YES |
| Mark for deletion | `delete()` | `_tracker.mark_deleted()` | YES - validates real GID |

**Hidden Dependency**: `_track_recursive()` accesses private attributes (`_contacts`, `_units`, `_offers`, `_processes`) of BusinessEntity types.

### 1.3 Change Inspection (Lines 430-547)

| Behavior | Method | Delegation | Must Preserve |
|----------|--------|------------|---------------|
| Get field changes | `get_changes()` | `_tracker.get_changes()` | YES |
| Get entity state | `get_state()` | `_tracker.get_state()` | YES |
| Find by GID | `find_by_gid()` | `_tracker.find_by_gid()` | YES |
| Check if tracked | `is_tracked()` | `_tracker.is_tracked()` | YES |
| Get dependency order | `get_dependency_order()` | `_graph.build()`, `_graph.get_levels()` | YES |

### 1.4 Preview/Dry Run (Lines 549-591)

| Behavior | Method | Delegation | Must Preserve |
|----------|--------|------------|---------------|
| Preview CRUD operations | `preview()` | `_pipeline.preview()`, `_pipeline.validate_no_unsupported_modifications()` | YES |
| Return action operations | `preview()` | Copies `_pending_actions` | YES - tuple return |

### 1.5 Commit Orchestration (Lines 593-776)

**Five-Phase Commit** (Critical - must preserve exact ordering):

1. **CRUD Operations** (Phase 1): `_pipeline.execute_with_actions()`
2. **Action Operations** (Phase 2): Executed within `execute_with_actions`
3. **Cascade Operations** (Phase 3): `_cascade_executor.execute()`
4. **Healing Operations** (Phase 4): `_execute_healing_async()`
5. **Automation** (Phase 5): `_client.automation.evaluate_async()`

| Behavior | Location | Must Preserve |
|----------|----------|---------------|
| Empty session warning | Line 641-648 | YES - logs if nothing to commit |
| Selective action clearing | `_clear_successful_actions()` | YES - ADR-0066 |
| Custom field tracking reset | `_reset_custom_field_tracking()` | YES - ADR-0074 order matters |
| Post-commit hooks | `_events.emit_post_commit()` | YES - TDD-AUTOMATION-LAYER |
| Automation isolation | Lines 713-726 | YES - failures don't fail commit |

**Critical Order**: DEF-001 FIX - Reset custom field tracking BEFORE snapshot capture (Lines 688-693).

### 1.6 Event Hooks (Lines 780-897)

| Behavior | Method | Delegation | Must Preserve |
|----------|--------|------------|---------------|
| Pre-save hook | `on_pre_save()` | `_events.register_pre_save()` | YES - decorator API |
| Post-save hook | `on_post_save()` | `_events.register_post_save()` | YES - decorator API |
| Error hook | `on_error()` | `_events.register_error()` | YES - decorator API |
| Post-commit hook | `on_post_commit()` | `_events.register_post_commit()` | YES - decorator API |

### 1.7 Action Operations (Lines 899-1884)

**18 Action Methods - HIGHEST EXTRACTION VALUE**:

| Method | ActionType | Target Type | Positioning | Lines |
|--------|------------|-------------|-------------|-------|
| `add_tag()` | ADD_TAG | Tag/str | No | 45 |
| `remove_tag()` | REMOVE_TAG | Tag/str | No | 45 |
| `add_to_project()` | ADD_TO_PROJECT | Project/str | Yes | 75 |
| `remove_from_project()` | REMOVE_FROM_PROJECT | Project/str | No | 45 |
| `add_dependency()` | ADD_DEPENDENCY | Task/str | No | 50 |
| `remove_dependency()` | REMOVE_DEPENDENCY | Task/str | No | 50 |
| `move_to_section()` | MOVE_TO_SECTION | Section/str | Yes | 75 |
| `add_follower()` | ADD_FOLLOWER | User/NameGid/str | No | 45 |
| `remove_follower()` | REMOVE_FOLLOWER | User/NameGid/str | No | 45 |
| `add_followers()` | ADD_FOLLOWER (batch) | list | No | 15 |
| `remove_followers()` | REMOVE_FOLLOWER (batch) | list | No | 15 |
| `add_dependent()` | ADD_DEPENDENT | Task/str | No | 50 |
| `remove_dependent()` | REMOVE_DEPENDENT | Task/str | No | 50 |
| `add_like()` | ADD_LIKE | None | No | 35 |
| `remove_like()` | REMOVE_LIKE | None | No | 35 |
| `add_comment()` | ADD_COMMENT | None | No | 70 |
| `set_parent()` | SET_PARENT | Task/str/None | Yes | 80 |
| `reorder_subtask()` | SET_PARENT | - | Yes | 35 |

**Pattern Observed**: All action methods follow identical structure:
1. `_ensure_open()` check
2. Build `NameGid` from input
3. Optional validation (GID, positioning conflict)
4. Create `ActionOperation`
5. Append to `_pending_actions`
6. Log if `_log` present
7. Return `self` for chaining

**Extraction Opportunity**: Replace 18 methods with decorator/factory + 3 base implementations (no-target, target-required, positioning-enabled).

### 1.8 Cascade Operations (Lines 1900-1973)

| Behavior | Method | Must Preserve |
|----------|--------|---------------|
| Queue cascade | `cascade_field()` | YES - fluent chaining |
| Get pending cascades | `get_pending_cascades()` | YES - inspection API |

### 1.9 Self-Healing (Lines 2028-2193)

| Behavior | Method | Must Preserve |
|----------|--------|---------------|
| Should heal check | `_should_heal()` | YES - tier logic |
| Queue healing | `_queue_healing()` | YES - deduplication |
| Execute healing | `_execute_healing_async()` | YES - non-blocking failures |

---

## 2. State Transition Diagram

```
                                  SaveSession State Machine
                                  ========================

     ┌────────────────────────────────────────────────────────────────────┐
     │                           SessionState                            │
     │                                                                    │
     │   ┌──────────┐     commit_async()    ┌───────────┐                │
     │   │   OPEN   │ ──────────────────> │ COMMITTED  │                │
     │   │          │                       │            │                │
     │   └────┬─────┘                       └─────┬──────┘                │
     │        │                                   │                       │
     │        │ __aexit__() or __exit__()        │ __aexit__() or       │
     │        │                                   │ __exit__()           │
     │        │                                   │                       │
     │        ▼                                   ▼                       │
     │   ┌─────────────────────────────────────────────────┐             │
     │   │                    CLOSED                        │             │
     │   │                                                  │             │
     │   │  ALL operations raise SessionClosedError         │             │
     │   └─────────────────────────────────────────────────┘             │
     └────────────────────────────────────────────────────────────────────┘

                            Commit Phases (within OPEN/COMMITTED)
                            =====================================

    ┌─────────────────────────────────────────────────────────────────────┐
    │  commit_async()                                                     │
    │                                                                     │
    │  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐ │
    │  │  Phase 1   │   │  Phase 2   │   │  Phase 3   │   │  Phase 4   │ │
    │  │   CRUD +   │──>│  Cascade   │──>│  Healing   │──>│ Automation │ │
    │  │  Actions   │   │  Execute   │   │  Execute   │   │  Evaluate  │ │
    │  └────────────┘   └────────────┘   └────────────┘   └────────────┘ │
    │        │                │                │                │        │
    │        ▼                ▼                ▼                ▼        │
    │  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐ │
    │  │SaveResult  │   │CascadeRslt │   │HealingRept │   │AutomtnRslt │ │
    │  │.succeeded  │   │.success    │   │.succeeded  │   │.success    │ │
    │  │.failed     │   │.failed     │   │.failed     │   │.failed     │ │
    │  │action_rslts│   │            │   │            │   │            │ │
    │  └────────────┘   └────────────┘   └────────────┘   └────────────┘ │
    │                                                                     │
    │  Guards:                                                            │
    │  - _ensure_open() called at entry                                   │
    │  - Empty session returns early with warning                         │
    │  - Failed phases continue (non-blocking)                            │
    │  - Automation failures isolated (exception swallowed)               │
    │                                                                     │
    │  Post-commit:                                                       │
    │  - _events.emit_post_commit(result) always called                   │
    │  - State transitions to COMMITTED                                   │
    └─────────────────────────────────────────────────────────────────────┘

                           Entity State Transitions
                           ========================

    ┌────────────────────────────────────────────────────────────────────┐
    │  EntityState (managed by ChangeTracker, queried by SaveSession)    │
    │                                                                    │
    │       track(entity)                                                │
    │            │                                                       │
    │            ▼                                                       │
    │  ┌──────────────────┐                                              │
    │  │ gid=None or temp_│────> NEW                                     │
    │  │ gid=real         │────> CLEAN                                   │
    │  └──────────────────┘                                              │
    │            │                                                       │
    │            ▼                                                       │
    │  ┌──────────────┐    modify fields    ┌──────────────┐            │
    │  │    CLEAN     │ ───────────────────>│   MODIFIED   │            │
    │  │              │<────────────────────│              │            │
    │  └──────────────┘   mark_clean()      └──────────────┘            │
    │                       (commit success)                             │
    │                                                                    │
    │  ┌──────────────┐                                                  │
    │  │   DELETED    │<──── delete() [requires real GID]               │
    │  └──────────────┘                                                  │
    └────────────────────────────────────────────────────────────────────┘
```

---

## 3. Test Coverage Map

### 3.1 Test Files and Scope

| Test File | Line Count | Focus Area | Coverage Quality |
|-----------|------------|------------|------------------|
| `test_session.py` | 2112 | Core session, actions, positioning, custom field reset | COMPREHENSIVE |
| `test_session_cascade.py` | 394 | Cascade queuing and execution | GOOD |
| `test_session_business.py` | 250 | Recursive tracking, BusinessEntity | GOOD |
| `test_session_healing.py` | 760 | Auto-heal, HealingResult, HealingReport | COMPREHENSIVE |

**Total Test Lines**: ~3516 (1.6x code coverage ratio)

### 3.2 Test Class Coverage

| Test Class | Lines | Behaviors Covered |
|------------|-------|-------------------|
| `TestContextManager` | 45 | Async/sync context, exception handling |
| `TestEntityRegistration` | 75 | track, untrack, delete |
| `TestChangeInspection` | 55 | get_changes, get_state, get_dependency_order |
| `TestPreview` | 40 | preview(), empty session, state preservation |
| `TestPreviewActions` | 95 | FR-PREV-001/002/003, unsupported modifications |
| `TestCommit` | 115 | commit_async, mark_clean, partial failure |
| `TestEventHooks` | 70 | on_pre_save, on_post_save, on_error, invocation |
| `TestEdgeCases` | 80 | Double track, GID update, logging, partial failure |
| `TestActionMethods` | 160 | All 18 action methods |
| `TestActionCommit` | 100 | Action execution, clearing, mixed CRUD+actions |
| `TestFollowerMethods` | 100 | add_follower, remove_follower, batch |
| `TestPositioning` | 120 | insert_before, insert_after, PositioningConflictError |
| `TestDependentMethods` | 60 | add_dependent, remove_dependent |
| `TestLikeMethods` | 70 | add_like, remove_like, no target |
| `TestCommentMethods` | 85 | add_comment, html_text, validation |
| `TestParentMethods` | 200 | set_parent, reorder_subtask, positioning |
| `TestSelectiveActionClearing` | 200 | ADR-0066, retry workflow |
| `TestCustomFieldTrackingReset` | 210 | ADR-0074, DEF-001 fix |
| `TestCascadeOperationQueuing` | 55 | cascade_field(), chaining |
| `TestCascadeExecutionDuringCommit` | 140 | Executor invocation, result propagation |
| `TestSaveResultCascadeProperties` | 50 | cascade_succeeded, cascade_failed |
| `TestCascadeIntegration` | 45 | Cascades-only commit |
| `TestHealingResultModel` | 60 | HealingResult immutability, repr |
| `TestHealingReportModel` | 60 | all_succeeded, counters |
| `TestAutoHealParameter` | 30 | auto_heal default, enabling |
| `TestShouldHeal` | 130 | Tier-based logic, overrides |
| `TestTrackWithHeal` | 75 | heal parameter, queue behavior |
| `TestHealingExecution` | 165 | commit healing, non-blocking failures |
| `TestSaveResultHealing` | 35 | healing_report population |
| `TestHealingEdgeCases` | 80 | Healing-only commit, mixed operations |
| `TestTrackExtendedSignature` | 40 | prefetch_holders, recursive params |
| `TestRecursiveTracking` | 135 | Holder hierarchy, empty/none holders |
| `TestTrackWithPlainTask` | 25 | recursive/prefetch on plain Task |

### 3.3 Coverage Gaps Identified

| Gap | Severity | Description |
|-----|----------|-------------|
| **Sync commit()** | LOW | Only tested via `test_commit_sync_wrapper`, no deep sync path testing |
| **GID transition map** | LOW | `_gid_transitions` in tracker not directly tested via session |
| **Concurrent commit** | MEDIUM | No thread-safety tests (asyncio safety assumed) |
| **Error hook exceptions** | LOW | Tested via EventSystem, not directly via session |
| **Automation result population** | MEDIUM | `automation_results` in SaveResult not fully tested |
| **Post-commit hook failure isolation** | LOW | Assumed from EventSystem tests |
| **NameResolver integration** | LOW | `name_resolver` property exists but no session-level tests |
| **max_concurrent parameter** | LOW | Reserved for future, no effect tested |

---

## 4. Hidden Dependencies

### 4.1 Internal Dependencies (Private API Usage)

| Consumer | Private API | Risk if Changed |
|----------|-------------|-----------------|
| `_track_recursive()` | `entity._contacts`, `_units`, `_offers`, `_processes` | HIGH - BusinessEntity coupling |
| `_should_heal()` | `entity._detection_result` | HIGH - Detection system coupling |
| `_queue_healing()` | `entity._detection_result.expected_project_gid` | HIGH |
| `_reset_custom_field_tracking()` | `entity.reset_custom_field_tracking()` | MEDIUM - duck typing |
| `commit_async()` | `_client._http`, `_client.automation`, `_client._config` | MEDIUM - client internals |

### 4.2 External Dependencies

| Dependency | Import Path | Used For |
|------------|-------------|----------|
| `ChangeTracker` | `persistence.tracker` | All entity tracking |
| `DependencyGraph` | `persistence.graph` | Dependency ordering |
| `SavePipeline` | `persistence.pipeline` | CRUD execution |
| `EventSystem` | `persistence.events` | Hook management |
| `ActionExecutor` | `persistence.action_executor` | Action execution |
| `CascadeExecutor` | `persistence.cascade` | Cascade execution |
| `NameResolver` | `clients.name_resolver` | Name-to-GID resolution |
| `sync_wrapper` | `transport.sync` | Sync API support |

### 4.3 Caller Dependencies (Who Uses SaveSession)

| Caller | Import Pattern | Uses |
|--------|---------------|------|
| `client.py` | Direct import | Factory method `save_session()` |
| `automation/engine.py` | Via persistence import | Automation rule execution |
| `automation/pipeline.py` | Via persistence import | Pipeline automation |
| `models/business/*.py` | TYPE_CHECKING import | Docstring examples |
| `tests/**` | Direct import | All test files |

---

## 5. Edge Cases Registry

### 5.1 Documented Expected Behaviors

| Edge Case | Expected Behavior | Test Location |
|-----------|-------------------|---------------|
| Empty commit | Warning log, returns empty SaveResult | `test_commit_async_empty_session` |
| Track same entity twice | Idempotent, preserves original snapshot | `test_track_same_entity_twice` |
| Delete without real GID | Raises ValueError | `test_delete_without_gid_raises` |
| Operations on closed session | Raises SessionClosedError | Multiple tests |
| Both insert_before and insert_after | Raises PositioningConflictError | `test_*_with_both_raises_positioning_conflict_error` |
| add_comment with empty text | Raises ValueError | `test_add_comment_empty_raises_value_error` |
| reorder_subtask without parent | Raises ValueError | `test_reorder_subtask_raises_for_task_without_parent` |
| Healing without detection_result | Not queued, no error | `test_should_heal_false_without_detection_result` |
| Healing at Tier 1 | Not queued (deterministic) | `test_should_heal_false_for_tier_1` |
| Cascade failure | Kept in queue for retry | `test_cascades_preserved_on_failure` |
| Action failure | Kept in pending for retry | `test_all_failure_keeps_all_actions` |
| Healing failure | Non-blocking, logged | `test_healing_failure_non_blocking` |
| Automation failure | Swallowed, logged | Lines 713-726 (no direct test) |

### 5.2 Undocumented Behaviors

| Behavior | Location | Risk |
|----------|----------|------|
| Multiple commits in session | Allowed after COMMITTED state | LOW - explicitly tested |
| Re-tracking different object with same GID | Updates reference, keeps snapshot | MEDIUM - implicit |
| Partial success action clearing | Identity-based matching | MEDIUM - complex logic |
| Custom field reset order | BEFORE snapshot capture | HIGH - DEF-001 fix |

---

## 6. Performance Baseline Requirements

### 6.1 Memory Considerations

| Component | Memory Impact | Benchmark Needed |
|-----------|--------------|------------------|
| `_snapshots` (ChangeTracker) | O(n) entity dumps | YES - large hierarchies |
| `_pending_actions` | O(a) action operations | NO - typically small |
| `_cascade_operations` | O(c) cascade ops | NO - typically small |
| `_healing_queue` | O(h) entity tuples | NO - typically small |
| `_name_cache` | O(r) resolved names | YES - long sessions |

### 6.2 Batch Size Constraints

| Constraint | Source | Value |
|------------|--------|-------|
| Max batch operations | Asana API limit | 10 |
| Max concurrent | Reserved config | 15 (unused) |
| Healing semaphore | healing.py | 5 |

### 6.3 Required Benchmarks (Pre-Decomposition)

| Metric | How to Measure |
|--------|----------------|
| Track + commit 100 entities | `time.perf_counter()` |
| Track + commit with 50 actions | `time.perf_counter()` |
| Recursive track of deep hierarchy (5 levels) | `time.perf_counter()` |
| Memory after tracking 1000 entities | `sys.getsizeof()` or tracemalloc |

---

## 7. Backward Compatibility Requirements

### 7.1 Public API (Must Not Change)

| Method/Property | Signature | Contract |
|-----------------|-----------|----------|
| `__init__` | `(client, batch_size=10, max_concurrent=15, auto_heal=False, automation_enabled=None)` | All kwargs optional |
| `__aenter__/__aexit__` | Standard async context | Returns self, closes on exit |
| `__enter__/__exit__` | Standard sync context | Returns self, closes on exit |
| `track` | `(entity, *, prefetch_holders=False, recursive=False, heal=None) -> T` | Returns same entity |
| `untrack` | `(entity) -> None` | |
| `delete` | `(entity) -> None` | Raises ValueError for temp GID |
| `get_changes` | `(entity) -> dict[str, tuple[Any, Any]]` | Field: (old, new) |
| `get_state` | `(entity) -> EntityState` | Raises ValueError if not tracked |
| `find_by_gid` | `(gid) -> AsanaResource | None` | |
| `is_tracked` | `(gid) -> bool` | |
| `get_dependency_order` | `() -> list[list[AsanaResource]]` | |
| `preview` | `() -> tuple[list[PlannedOperation], list[ActionOperation]]` | |
| `commit_async` | `() -> SaveResult` | |
| `commit` | `() -> SaveResult` | Sync wrapper |
| `on_pre_save` | `(func) -> Callable` | Decorator |
| `on_post_save` | `(func) -> Callable` | Decorator |
| `on_error` | `(func) -> Callable` | Decorator |
| `on_post_commit` | `(func) -> Callable` | Decorator |
| `add_tag` | `(task, tag) -> SaveSession` | Fluent |
| `remove_tag` | `(task, tag) -> SaveSession` | Fluent |
| `add_to_project` | `(task, project, *, insert_before=None, insert_after=None) -> SaveSession` | Fluent |
| `remove_from_project` | `(task, project) -> SaveSession` | Fluent |
| `add_dependency` | `(task, depends_on) -> SaveSession` | Fluent |
| `remove_dependency` | `(task, depends_on) -> SaveSession` | Fluent |
| `move_to_section` | `(task, section, *, insert_before=None, insert_after=None) -> SaveSession` | Fluent |
| `add_follower` | `(task, user) -> SaveSession` | Fluent |
| `remove_follower` | `(task, user) -> SaveSession` | Fluent |
| `add_followers` | `(task, users) -> SaveSession` | Fluent |
| `remove_followers` | `(task, users) -> SaveSession` | Fluent |
| `add_dependent` | `(task, dependent_task) -> SaveSession` | Fluent |
| `remove_dependent` | `(task, dependent_task) -> SaveSession` | Fluent |
| `add_like` | `(task) -> SaveSession` | Fluent |
| `remove_like` | `(task) -> SaveSession` | Fluent |
| `add_comment` | `(task, text, *, html_text=None) -> SaveSession` | Fluent |
| `set_parent` | `(task, parent, *, insert_before=None, insert_after=None) -> SaveSession` | Fluent |
| `reorder_subtask` | `(task, *, insert_before=None, insert_after=None) -> SaveSession` | Fluent |
| `get_pending_actions` | `() -> list[ActionOperation]` | Copy of list |
| `cascade_field` | `(entity, field_name, *, target_types=None) -> SaveSession` | Fluent |
| `get_pending_cascades` | `() -> list[CascadeOperation]` | Copy of list |
| `name_resolver` | Property | `NameResolver` instance |

### 7.2 Private API Used by Tests

| Private API | Test Usage | Change Impact |
|-------------|------------|---------------|
| `_state` | Direct state inspection | LOW - refactor to property |
| `_pending_actions` | Direct list access | LOW - use get_pending_actions() |
| `_cascade_operations` | Direct list access | LOW - use get_pending_cascades() |
| `_healing_queue` | Direct queue access | MEDIUM - no getter exists |
| `_entity_heal_flags` | Direct dict access | MEDIUM - no getter exists |
| `_auto_heal` | Direct flag access | LOW - refactor to property |
| `_events._pre_save_hooks` | Hook count verification | LOW - add len property |

### 7.3 Exception Compatibility

All exceptions must continue to be raised with same types:
- `SessionClosedError` - operations on closed session
- `PositioningConflictError` - both positioning params
- `ValueError` - invalid inputs (delete temp GID, reorder without parent, empty comment)
- `CyclicDependencyError` - from DependencyGraph
- `UnsupportedOperationError` - from SavePipeline

---

## 8. Answers to Discovery Questions

### Q1: Are there behaviors NOT tested?

**Yes, identified gaps:**
1. `max_concurrent` parameter has no functional test (reserved for future)
2. Automation result population in SaveResult not directly tested
3. GID transition map in tracker not tested through session
4. Thread safety not tested (assumed single-threaded asyncio)

### Q2: Are there callers depending on private implementation?

**Yes:**
1. Tests access `_state`, `_pending_actions`, `_cascade_operations` directly
2. `_track_recursive()` depends on BusinessEntity private attributes
3. `_should_heal()` depends on `_detection_result` private attribute

**Mitigation**: Add properties/getters for commonly accessed private state.

### Q3: How do 18 action methods relate to ActionExecutor?

**Relationship**:
- SaveSession action methods create `ActionOperation` objects
- Operations stored in `_pending_actions` list
- At commit time, `_pipeline.execute_with_actions()` passes to `ActionExecutor.execute_async()`
- ActionExecutor makes HTTP calls, returns `ActionResult` list
- SaveSession clears successful actions via `_clear_successful_actions()`

**Key Point**: ActionExecutor only executes; SaveSession manages registration, queuing, and result handling.

### Q4: How does persistence/healing.py relate to SaveSession's healing queue?

**Relationship**:
- `persistence/healing.py` provides **standalone** healing utilities (`heal_entity_async`, `heal_entities_async`)
- SaveSession has **embedded** healing via `_execute_healing_async()`
- Both use same logic: call `_client._http.request("POST", "/tasks/{gid}/addProject")`
- SaveSession's healing is integrated into commit flow (Phase 4)
- Standalone utilities are for ad-hoc healing outside SaveSession

**Key Point**: Two parallel healing paths - SaveSession for commit-integrated, standalone for explicit calls.

### Q5: Any thread-safety considerations?

**Analysis**:
- SaveSession is designed for asyncio (single-threaded cooperative)
- No explicit locks or thread-safety mechanisms
- Shared mutable state: `_pending_actions`, `_cascade_operations`, `_healing_queue`
- `ChangeTracker` uses dict-based storage (not thread-safe)

**Recommendation**: Document as "not thread-safe, designed for asyncio context".

---

## 9. Extraction Priority Recommendations

### High Priority (High Value, Low Risk)

1. **Action Method Factory** (920 lines -> ~150 lines)
   - Replace 18 boilerplate methods with decorator/factory pattern
   - Single base implementation with action-type configuration
   - Preserve exact API signatures

2. **State Manager Extraction** (~100 lines)
   - Extract `SessionState`, `_ensure_open()`, context managers
   - Clear separation of lifecycle from operations

### Medium Priority (Medium Value, Medium Risk)

3. **Healing Manager Extraction** (~165 lines)
   - Extract `_should_heal()`, `_queue_healing()`, `_execute_healing_async()`
   - Parallels existing `persistence/healing.py` utilities

4. **Commit Orchestrator Extraction** (~160 lines)
   - Extract five-phase coordination logic
   - Preserve exact ordering and error handling

### Low Priority (Low Value, High Risk)

5. **Recursive Tracking** (~25 lines)
   - Tightly coupled to BusinessEntity internals
   - Wait for BusinessEntity refactoring

---

## 10. Next Steps

1. **Create benchmarks** for performance baseline before refactoring
2. **Add missing getters** for private state accessed by tests
3. **Document thread-safety** limitations in docstring
4. **Design action factory** pattern for 18 action methods
5. **Plan extraction order** based on priority matrix above

---

**Document Version**: 1.0
**Last Updated**: 2025-12-19
