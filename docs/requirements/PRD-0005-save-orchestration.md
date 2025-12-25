# PRD: Save Orchestration Layer

## Metadata
- **PRD ID**: PRD-0005
- **Status**: Implemented
- **Version**: 1.1
- **Author**: Requirements Analyst
- **Created**: 2025-12-10
- **Last Updated**: 2025-12-24
- **Stakeholders**: autom8 team, SDK consumers, API integrators
- **Related PRDs**:
  - [PRD-0001](PRD-0001-sdk-extraction.md) (SDK Extraction - prerequisite)
- **Related ADRs**:
  - [ADR-0002](../decisions/ADR-0002-sync-wrapper-strategy.md) (Sync/Async Wrapper Strategy)
  - [ADR-0010](../decisions/ADR-0010-batch-chunking-strategy.md) (Sequential Chunk Execution for Batch Operations)
  - [ADR-0095](../decisions/ADR-0095-self-healing-integration.md) (Self-Healing Integration with SaveSession)
  - [ADR-0139](../decisions/ADR-0139-self-healing-design.md) (Self-Healing Opt-In Design)
  - [ADR-0144](../decisions/ADR-0144-healingresult-consolidation.md) (HealingResult Type Consolidation)

## Problem Statement

The autom8_asana SDK currently uses **immediate persistence** where every API call executes immediately. When a developer modifies multiple tasks, each change triggers a separate API call, leading to inefficient API usage, potential rate limiting, and poor performance for bulk operations.

**Current State**:
```python
# Current pattern: immediate execution - 3 API calls
task = await client.tasks.get_async("123")
await client.tasks.update_async("123", {"name": "New Name"})  # API call 1
await client.tasks.update_async("123", {"notes": "Updated"})  # API call 2
await client.tasks.update_async("456", {"name": "Other"})     # API call 3
```

**Key Problems**:
1. **Inefficient API usage**: Multiple changes to the same or related resources trigger separate API calls instead of being batched
2. **No dependency awareness**: Parent tasks must exist before subtasks, but developers must manually sequence operations
3. **Fragmented error handling**: Partial failures across multiple calls are difficult to track and recover from
4. **Rate limit pressure**: High-volume operations quickly consume rate limit tokens (1500 req/min)

**Legacy Monolith Context**:
- The legacy autom8 monolith uses threading-based concurrency for bulk operations
- No formal Unit of Work pattern exists
- Developers manually sequence parent/child saves
- Bulk operations are ad-hoc and inconsistent

**Impact of Not Solving**:
1. SDK consumers hit Asana rate limits during bulk operations
2. Developers write error-prone manual sequencing code for hierarchical saves
3. Performance penalty of 10x for batch-eligible operations (100 updates = 100 calls vs 10 batched calls)
4. Inconsistent error handling makes debugging bulk failures difficult
5. Cannot offer Django-ORM-style ergonomics that developers expect from modern SDKs

## Goals & Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API call reduction | >= 70% reduction for batch-eligible operations | 100 independent saves --> <= 30 API calls |
| Orchestration overhead | < 10ms per tracked entity | Profiler measurement excluding API latency |
| Memory overhead | < 5% for change tracking | Memory profiler comparing tracked vs untracked |
| Error attribution | 100% of failures attributed to specific entities | Test with intentional partial failures |
| Developer ergonomics | Single context manager for bulk saves | API review |
| Backward compatibility | Zero breaking changes to existing API | Existing tests pass unchanged |

## Scope

### In Scope

**v1 Resource Types**:
All AsanaResource subclasses are supported:
- Task (including subtask hierarchies)
- Project
- Section
- Tag
- User (read-only references)
- Custom Fields (values on tasks)

**Core Capabilities**:
- `SaveSession` as async context manager for Unit of Work pattern
- Explicit entity registration via `session.track(model)` (opt-in tracking)
- `session.commit()` executes all pending changes as optimized batches
- `session.delete(model)` marks entity for deletion
- Automatic dirty detection via snapshot comparison
- Dependency graph construction from parent-child relationships
- Topological sort for dependency-safe save ordering (Kahn's algorithm)
- Placeholder GID resolution for newly created entities
- Partial failure handling: commit successful operations, report failures
- `session.preview()` dry-run mode to inspect planned operations without execution
- Sync wrapper following ADR-0002 pattern

**Public API**:
```python
# Async usage (primary)
async with SaveSession(client) as session:
    task = await client.tasks.get_async("123")
    session.track(task)
    task.name = "Updated Name"

    new_subtask = Task(name="Subtask", parent=task)
    session.track(new_subtask)

    result = await session.commit()
    # result.succeeded: list of saved entities
    # result.failed: list of (entity, error) tuples

# Sync usage (wrapper)
with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    result = session.commit()

# Dry run preview
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    operations = session.preview()
    # Returns list of PlannedOperation without executing
```

### Out of Scope

**v1 Exclusions**:
- ACID transactions (Asana API does not support rollback)
- Offline sync / persistent queue (crash recovery)
- Optimistic concurrency / version conflict detection
- Parallel execution of independent dependency levels
- Update coalescing (multiple updates to same field merged)
- Undo/redo capabilities
- Real-time collaboration conflict resolution

**Explicitly Not Supported**:
- Rollback of committed operations (Asana limitation)
- Cross-workspace transactions
- Webhook-triggered saves
- Background/scheduled saves

---

## Requirements

### Functional Requirements

#### Unit of Work Requirements (FR-UOW-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-UOW-001 | SDK shall provide `SaveSession` class as async context manager | Must | `async with SaveSession(client) as session:` enters/exits cleanly |
| FR-UOW-002 | SaveSession shall support explicit entity registration via `session.track(model)` | Must | Only tracked entities are considered for save; untracked modifications ignored |
| FR-UOW-003 | SaveSession shall provide `commit()` method that executes all pending changes | Must | `await session.commit()` returns SaveResult with succeeded/failed lists |
| FR-UOW-004 | SaveSession shall provide sync wrapper per ADR-0002 | Must | `with SaveSession(client) as session:` and `session.commit()` work synchronously |
| FR-UOW-005 | SaveSession shall accept optional configuration for batch size and concurrency | Should | `SaveSession(client, batch_size=10, max_concurrent=15)` |
| FR-UOW-006 | SaveSession shall prevent re-use after commit or context exit | Must | Calling `commit()` twice or after `__aexit__` raises `SessionClosedError` |
| FR-UOW-007 | SaveSession shall support multiple commit calls within single context (incremental saves) | Should | Each `commit()` saves current pending changes; session remains open |
| FR-UOW-008 | SaveSession shall track entity lifecycle state (new, modified, deleted, clean) | Must | Internal state machine per tracked entity |

#### Change Tracking Requirements (FR-CHANGE-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CHANGE-001 | SDK shall detect modified entities via snapshot comparison using `model_dump()` | Must | Original state captured at `track()` time; current state compared at `commit()` |
| FR-CHANGE-002 | SDK shall compute field-level change sets showing which fields were modified | Must | `session.get_changes(entity)` returns dict of `{field: (old, new)}` |
| FR-CHANGE-003 | SDK shall detect new entities by checking for missing or placeholder GID | Must | Entity with `gid is None` or `gid.startswith("temp_")` treated as create |
| FR-CHANGE-004 | SDK shall provide `session.delete(model)` to mark entity for deletion | Must | Deleted entities included in commit as DELETE operations |
| FR-CHANGE-005 | SDK shall skip clean (unmodified) entities during commit | Must | Tracked but unmodified entities do not generate API calls |
| FR-CHANGE-006 | SDK shall generate minimal payloads containing only changed fields | Should | Update payloads exclude unchanged fields to reduce request size |
| FR-CHANGE-007 | SDK shall handle nested object changes (e.g., custom_fields list) | Must | Changes to nested structures detected and included in payload |
| FR-CHANGE-008 | SDK shall support `session.untrack(model)` to remove entity from tracking | Should | Untracked entities ignored in subsequent commits |
| FR-CHANGE-009 | SDK shall reset entity state to clean after successful save | Must | Successful save clears dirty state; entity becomes unmodified |

#### Dependency Graph Requirements (FR-DEPEND-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DEPEND-001 | SDK shall automatically detect parent-child relationships from `parent` field | Must | Task with `parent` set depends on parent entity being saved first |
| FR-DEPEND-002 | SDK shall perform topological sort using Kahn's algorithm for save ordering | Must | Entities sorted so dependencies are satisfied before dependents |
| FR-DEPEND-003 | SDK shall raise `CyclicDependencyError` when dependency graph has cycles | Must | Circular references detected before commit attempt with clear error message |
| FR-DEPEND-004 | SDK shall resolve placeholder GIDs after parent creation | Must | `temp_123` in subtask.parent replaced with real GID after parent saved |
| FR-DEPEND-005 | SDK shall detect project-task dependencies for new tasks | Should | New task in new project: project saved before task |
| FR-DEPEND-006 | SDK shall detect section-task dependencies for section membership | Should | Task membership in new section: section saved before task |
| FR-DEPEND-007 | SDK shall group independent entities for parallel batching | Must | Entities at same dependency level batched together |
| FR-DEPEND-008 | SDK shall support explicit dependency declaration via `session.depends_on(child, parent)` | Could | Manual override for complex dependency scenarios |
| FR-DEPEND-009 | SDK shall provide `session.get_dependency_order()` to inspect computed order | Should | Returns list of entity lists representing dependency levels |

#### Batch Execution Requirements (FR-BATCH-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-BATCH-001 | SDK shall group operations by dependency level for batched execution | Must | Level 0 entities batched together, then level 1, etc. |
| FR-BATCH-002 | SDK shall delegate batch execution to existing `BatchClient` | Must | Reuse `BatchClient.execute_async()` for actual API calls |
| FR-BATCH-003 | SDK shall execute chunks sequentially per ADR-0010 | Must | Within a dependency level, chunks execute in order |
| FR-BATCH-004 | SDK shall correlate batch responses back to tracked entities | Must | Each response mapped to its originating entity for result/error attribution |
| FR-BATCH-005 | SDK shall update entity GIDs after successful creation | Must | Created entities have `gid` updated with server-assigned value |
| FR-BATCH-006 | SDK shall respect Asana batch limit of 10 actions per request | Must | Batches auto-chunked at 10 operations maximum |
| FR-BATCH-007 | SDK shall build appropriate BatchRequest for each operation type | Must | Create/Update/Delete mapped to POST/PUT/DELETE methods |
| FR-BATCH-008 | SDK shall include custom field values in save payloads | Must | Custom field changes serialized correctly in batch request |
| FR-BATCH-009 | SDK shall handle rate limiting via existing TokenBucketRateLimiter | Must | Rate limits respected; retries handled transparently |

#### Error Handling Requirements (FR-ERROR-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-ERROR-001 | SDK shall commit successful operations and report failures (partial commit) | Must | Failed entities do not prevent successful entities from saving |
| FR-ERROR-002 | SDK shall provide `SaveResult` dataclass with `succeeded`, `failed`, `errors` | Must | Result object contains complete outcome information |
| FR-ERROR-003 | SDK shall attribute errors to specific entities with operation context | Must | Each error includes entity, operation type, API error, and request payload |
| FR-ERROR-004 | SDK shall define `PartialSaveError` for when some operations fail | Must | Exception raised if any operations fail; contains SaveResult |
| FR-ERROR-005 | SDK shall define `CyclicDependencyError` for circular references | Must | Clear message indicating cycle participants |
| FR-ERROR-006 | SDK shall define `DependencyResolutionError` for unresolved dependencies | Must | Raised when dependent entity fails and blocks dependents |
| FR-ERROR-007 | SDK shall define `SessionClosedError` for operations on closed session | Must | Raised when calling methods on closed/committed session |
| FR-ERROR-008 | SDK shall preserve original Asana API errors in error chain | Must | `__cause__` attribute contains underlying AsanaError |
| FR-ERROR-009 | SDK shall mark dependent entities as failed when dependency fails | Should | If parent fails, subtasks marked as `DependencyResolutionError` |
| FR-ERROR-010 | SDK shall provide `result.raise_on_failure()` convenience method | Should | Raises `PartialSaveError` only if failures exist |

#### Custom Field Requirements (FR-FIELD-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-FIELD-001 | SDK shall include custom field values in save payloads | Must | Custom fields serialized as `custom_fields` array in request |
| FR-FIELD-002 | SDK shall reuse `DefaultCustomFieldResolver` for name-to-GID resolution | Must | Custom field names resolved to GIDs before API call |
| FR-FIELD-003 | SDK shall handle all custom field types (text, number, enum, multi-enum, date) | Must | Each field type serialized correctly per Asana API spec |
| FR-FIELD-004 | SDK shall detect changes to custom field values | Must | Modified custom fields included in change set |
| FR-FIELD-005 | SDK shall handle custom field removal (setting to null) | Should | Null values included in payload to clear fields |

#### Event Hook Requirements (FR-EVENT-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-EVENT-001 | SDK shall support `@session.on_pre_save` decorator for validation/transformation | Should | Hook called before each entity save; can raise to abort |
| FR-EVENT-002 | SDK shall support `@session.on_post_save` decorator for notification/logging | Should | Hook called after successful entity save with result |
| FR-EVENT-003 | SDK shall support `@session.on_error` decorator for error handling | Should | Hook called when entity save fails with error context |
| FR-EVENT-004 | SDK shall pass entity and operation context to all hooks | Should | Hooks receive entity, operation type, and session reference |
| FR-EVENT-005 | SDK shall support both function and coroutine hooks | Should | Sync and async hooks supported transparently |

#### Dry Run Requirements (FR-DRY-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DRY-001 | SDK shall provide `session.preview()` returning planned operations without executing | Must | Returns list of PlannedOperation; no API calls made |
| FR-DRY-002 | PlannedOperation shall contain entity, operation type, and serialized payload | Must | Sufficient information to understand what would happen |
| FR-DRY-003 | Preview shall include computed dependency order | Must | Operations listed in execution order with dependency levels indicated |
| FR-DRY-004 | Preview shall validate all operations (e.g., cycle detection) | Should | Errors that would occur at commit time raised during preview |
| FR-DRY-005 | Preview shall not modify session state | Must | Session remains usable after preview; can still commit or preview again |

#### Self-Healing Requirements (FR-HEALING-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-HEALING-001 | SaveSession shall support opt-in self-healing via `auto_heal` parameter | Must | `SaveSession(client, auto_heal=True)` enables healing during commit |
| FR-HEALING-002 | SaveSession shall heal entities after normal save operations complete | Must | Healing executes only after all tracked entity saves succeed/fail |
| FR-HEALING-003 | SaveSession shall heal only entities with `needs_healing=True` detection flag | Must | Entities without healing flag are skipped |
| FR-HEALING-004 | SaveSession shall add healed entities to expected projects via `add_to_project` API | Must | Healing calls `client.tasks.add_to_project_async(entity_gid, project_gid)` |
| FR-HEALING-005 | SaveSession shall provide `heal_dry_run` parameter for preview mode | Must | `SaveSession(auto_heal=True, heal_dry_run=True)` returns healing plan without execution |
| FR-HEALING-006 | SaveSession shall report healing outcomes in `SaveResult.healed_entities` and `SaveResult.healing_failures` | Must | SaveResult includes lists of successfully healed and failed healing attempts |
| FR-HEALING-007 | SDK shall provide standalone `heal_entity_async()` function for on-demand healing | Must | Function heals single entity with detection result outside SaveSession |
| FR-HEALING-008 | SDK shall provide `heal_entities_async()` for batch healing with concurrency control | Should | Function heals multiple entities with configurable max_concurrent limit |
| FR-HEALING-009 | Standalone healing functions shall validate detection result before healing | Must | Raise ValueError if entity lacks detection result or doesn't need healing |
| FR-HEALING-010 | All healing operations shall return `HealingResult` with outcome details | Must | Result contains entity_gid, project_gid, success, dry_run, error |
| FR-HEALING-011 | HealingResult shall use unified type from `persistence.models` | Must | Single HealingResult dataclass supports all healing contexts (per ADR-0144) |
| FR-HEALING-012 | Detection functions shall NOT trigger healing automatically | Must | `detect_entity_type()` and `detect_entity_type_async()` remain side-effect-free (per ADR-0139) |
| FR-HEALING-013 | Healing operations shall be logged with structured logging | Should | Log entity_gid, project_gid, outcome at INFO level |
| FR-HEALING-014 | Healing failures shall not abort SaveSession commit | Must | Failed healing recorded in SaveResult; successful saves preserved |
| FR-HEALING-015 | Batch healing shall respect concurrency limits via semaphore | Must | Default max_concurrent=5; configurable per call |

---

### Non-Functional Requirements

#### Performance Requirements (NFR-PERF-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-PERF-001 | API call reduction | >= 70% (100 entities --> <= 30 calls) | Benchmark batch vs individual saves |
| NFR-PERF-002 | Orchestration overhead per entity | < 10ms excluding API latency | Profiler isolating orchestration code |
| NFR-PERF-003 | Memory overhead for change tracking | < 5% of entity memory footprint | Memory profiler comparing tracked vs untracked |
| NFR-PERF-004 | Dependency graph construction | < 100ms for 1000 entities | Profiler on graph building |
| NFR-PERF-005 | Topological sort | O(V + E) complexity | Algorithm analysis and benchmark |
| NFR-PERF-006 | Snapshot creation | < 1ms per entity | Profiler on model_dump() call |
| NFR-PERF-007 | Large batch support | 10,000 entities without OOM | Memory test with large batch |
| NFR-PERF-008 | Preview latency | < 50ms for 1000 entities | Profiler on preview() |

#### Compatibility Requirements (NFR-COMPAT-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-COMPAT-001 | Backward compatibility | Zero breaking changes to existing client API | Existing test suite passes |
| NFR-COMPAT-002 | Async-first with sync wrapper | Per ADR-0002 pattern | API review |
| NFR-COMPAT-003 | Support all AsanaResource subclasses | Task, Project, Section, Tag, etc. | Integration tests per resource type |
| NFR-COMPAT-004 | Python version support | 3.12+ | CI matrix testing |
| NFR-COMPAT-005 | Pydantic v2 compatibility | Works with existing model infrastructure | Integration tests |
| NFR-COMPAT-006 | BatchClient compatibility | Uses existing BatchClient without modification | Code review |

#### Observability Requirements (NFR-OBSERVE-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-OBSERVE-001 | DEBUG logging for save operations | All significant operations logged | Log audit |
| NFR-OBSERVE-002 | Metric: batch_count | Number of batch requests per commit | LogProvider integration |
| NFR-OBSERVE-003 | Metric: success_rate | Percentage of operations succeeding | LogProvider integration |
| NFR-OBSERVE-004 | Metric: dependency_depth | Maximum dependency tree depth | LogProvider integration |
| NFR-OBSERVE-005 | Metric: entities_per_commit | Count of entities per commit | LogProvider integration |
| NFR-OBSERVE-006 | Error logging with context | Failed operations logged with full context | Log audit |
| NFR-OBSERVE-007 | Correlation ID propagation | Link save events to originating request | Context propagation |

#### Reliability Requirements (NFR-REL-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-REL-001 | Thread safety | Zero race conditions | Concurrent test suite |
| NFR-REL-002 | Idempotent tracking | Re-tracking same entity is safe | Unit test |
| NFR-REL-003 | Resource cleanup | No connection/memory leaks | 24-hour stability test |
| NFR-REL-004 | Error isolation | Single entity failure doesn't corrupt session | Fault injection test |
| NFR-REL-005 | Graceful degradation | Session usable after partial failure | Recovery test |

---

## User Stories / Use Cases

### US-001: Batch Multiple Task Updates

As a developer, I want to batch multiple task updates so that I reduce API calls and improve performance.

**Scenario**:
1. Developer has 50 tasks to update with different changes
2. Developer creates SaveSession and tracks all tasks
3. Developer modifies task properties
4. Developer calls `commit()`
5. SDK batches updates into 5 API calls (50 / 10 per batch)
6. Developer receives SaveResult with all 50 succeeded

**Acceptance**: 50 updates execute in 5 API calls, not 50.

### US-002: Create Task Hierarchy

As a developer, I want automatic dependency ordering so that parent tasks are created before subtasks without manual sequencing.

**Scenario**:
1. Developer creates new parent task (no GID)
2. Developer creates 3 subtasks referencing parent
3. Developer tracks all 4 tasks
4. Developer calls `commit()`
5. SDK automatically saves parent first
6. SDK resolves parent's new GID into subtask.parent references
7. SDK saves subtasks in second batch

**Acceptance**: Parent created before subtasks without developer specifying order.

### US-003: Handle Partial Failures

As a developer, I want clear error reporting on partial failures so that I know exactly which operations succeeded and which failed.

**Scenario**:
1. Developer tracks 10 tasks for update
2. 2 tasks have invalid data (e.g., invalid assignee GID)
3. Developer calls `commit()`
4. SDK saves 8 tasks successfully
5. SDK returns SaveResult with 8 succeeded, 2 failed
6. Each failure includes entity reference, operation type, and error

**Acceptance**: Successful saves committed; failures clearly attributed.

### US-004: Preview Operations Before Commit

As a developer, I want to preview planned operations before committing so that I can validate the batch before execution.

**Scenario**:
1. Developer tracks multiple entities with various changes
2. Developer calls `session.preview()`
3. SDK returns list of PlannedOperation without making API calls
4. Developer inspects operations and dependency order
5. Developer decides to proceed and calls `commit()`

**Acceptance**: `preview()` returns operation plan; no API calls until `commit()`.

### US-005: Delete Multiple Entities

As a developer, I want to batch delete multiple tasks so that cleanup operations are efficient.

**Scenario**:
1. Developer has 20 tasks to delete
2. Developer calls `session.delete(task)` for each
3. Developer calls `commit()`
4. SDK batches deletes into 2 API calls
5. All tasks deleted successfully

**Acceptance**: 20 deletes execute in 2 API calls.

### US-006: Handle Dependency Failures

As a developer, I want dependent entities marked as failed when their dependency fails so that I understand the cascade effect.

**Scenario**:
1. Developer creates parent task and 5 subtasks
2. Parent task has invalid data
3. Developer calls `commit()`
4. Parent fails to create
5. All 5 subtasks marked as `DependencyResolutionError`
6. SaveResult shows 0 succeeded, 6 failed

**Acceptance**: Dependent failures clearly attributed to dependency failure.

### US-007: Self-Heal Entities During Save

As a developer, I want entities to be automatically healed during save so that project membership issues are corrected without manual intervention.

**Scenario**:
1. Developer detects 20 tasks needing healing (missing from expected projects)
2. Developer creates SaveSession with `auto_heal=True`
3. Developer tracks all 20 tasks
4. Developer calls `commit()`
5. SDK saves task changes (if any)
6. SDK automatically adds tasks to their expected projects
7. SaveResult shows healed entities and any healing failures

**Acceptance**: Tasks automatically added to expected projects during commit; healing outcomes reported separately from save operations.

---

## Design Decisions

### Decision 1: Opt-in Change Tracking

**Decision**: Change tracking is opt-in via explicit `session.track(model)` calls.

**Rationale**:

| Approach | Pros | Cons |
|----------|------|------|
| **Opt-in (chosen)** | No hidden magic; clear intent; predictable performance | Requires explicit tracking calls |
| **Automatic (transparent)** | Less boilerplate; feels like Django ORM | Hidden behavior; performance surprises; model modification required |
| **Hybrid** | Flexibility | Complexity; confusing defaults |

Opt-in tracking aligns with Python's "explicit is better than implicit" philosophy. Developers control exactly which entities participate in the save session, avoiding surprises from accidentally modified objects.

### Decision 2: Partial Commit on Failure

**Decision**: On partial failure, commit successful operations and report failures (commit + report).

**Rationale**:

| Approach | Pros | Cons |
|----------|------|------|
| **Commit + Report (chosen)** | No wasted work; successful saves preserved | Partial state may need cleanup |
| **Fail All** | Atomic semantics | Wasted work; Asana can't rollback anyway |
| **Retry Failed** | Maximum success rate | Complexity; infinite retry risk |

Asana's API does not support transactions or rollback. Once a batch succeeds, those changes are committed permanently. Therefore, failing all operations when some succeed provides no benefit and wastes successful work. Commit + Report gives developers maximum information and preserves valid changes.

### Decision 3: Snapshot-Based Dirty Detection

**Decision**: Use `model_dump()` snapshot comparison for dirty detection.

**Rationale**:

| Approach | Pros | Cons |
|----------|------|------|
| **Snapshot (chosen)** | Simple; no model modification; works with existing Pydantic models | O(n) comparison cost |
| **`__setattr__` override** | Immediate tracking; O(1) dirty check | Requires model changes; complexity |
| **Explicit dirty marking** | Full developer control | Boilerplate; error-prone |

Snapshot comparison is the simplest approach that requires no changes to existing Pydantic models. The O(n) comparison cost is negligible compared to network latency. This choice enables the save session to work with all existing models immediately.

### Decision 4: Kahn's Algorithm for Topological Sort

**Decision**: Use Kahn's algorithm for dependency ordering.

**Rationale**: Kahn's algorithm provides O(V + E) complexity, detects cycles, and produces a deterministic order. It's well-understood and easy to implement correctly. Alternative DFS-based approaches offer similar complexity but cycle detection is more complex.

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| Asana Batch API supports up to 10 actions per request | Asana API documentation; verified in discovery |
| Individual batch actions can fail independently | Asana API returns per-action status codes |
| Parent-child is the primary hard dependency | Discovery analysis of Asana data model |
| Existing BatchClient handles chunking and rate limiting | Code review of BatchClient implementation |
| Pydantic v2 `model_dump()` provides reliable serialization | Pydantic documentation; existing usage |
| Rate limiter infrastructure is reusable | TokenBucketRateLimiter already integrated |
| Sync wrapper pattern (ADR-0002) is established | ADR-0002 accepted and implemented |

---

## Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| BatchClient | autom8 team | Complete | `src/autom8_asana/batch/client.py` |
| BatchRequest / BatchResult | autom8 team | Complete | `src/autom8_asana/batch/models.py` |
| AsanaResource base model | autom8 team | Complete | `src/autom8_asana/models/base.py` |
| TokenBucketRateLimiter | autom8 team | Complete | `src/autom8_asana/transport/rate_limiter.py` |
| sync_wrapper decorator | autom8 team | Complete | `src/autom8_asana/transport/sync.py` |
| DefaultCustomFieldResolver | autom8 team | Complete | Custom field name-to-GID resolution |
| Discovery Document | autom8 team | Complete | `docs/save-orchestration-discovery.md` |

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| R-001: Asana rate limits throttle large batches | Performance degradation | Medium | Existing TokenBucketRateLimiter handles throttling; batch size configurable |
| R-002: Deep dependency hierarchies increase latency | Slow saves for nested structures | Low | Topological grouping minimizes sequential rounds; document limits |
| R-003: Placeholder GID resolution adds complexity | Implementation bugs | Medium | Clear state machine; comprehensive tests; preview mode for validation |
| R-004: Partial failures leave inconsistent state | Developer confusion | Medium | Clear SaveResult documentation; suggest cleanup patterns |
| R-005: Cycle detection misses edge cases | CyclicDependencyError not raised | Low | Use proven Kahn's algorithm; exhaustive cycle tests |
| R-006: Memory pressure from large snapshots | OOM for large batches | Low | Lazy snapshot creation; document batch size recommendations |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Maximum recommended batch size before warning? | Architect | TDD phase | Document performance characteristics |
| Should preview() validate custom field GIDs? | Architect | TDD phase | Design decision during TDD |

### Resolved Questions (User Decisions)

| Question | Resolution | Date |
|----------|------------|------|
| Opt-in vs automatic change tracking? | **Opt-in** - explicit `track()` calls | 2025-12-10 |
| Which resource types in v1? | **All resources** - Task, Project, Section, etc. | 2025-12-10 |
| Partial failure handling? | **Commit + Report** - save successful, report failures | 2025-12-10 |
| Include dry run mode in v1? | **Yes** - `session.preview()` included | 2025-12-10 |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-10 | Requirements Analyst | Initial draft with 8 FR categories (46 requirements), 4 NFR categories (21 requirements), 6 user stories, 4 design decisions |
| 1.1 | 2025-12-24 | Tech Writer | Added FR-HEALING-* requirements (15 requirements), US-007 (self-healing user story), updated status to Implemented, added ADR-0095/0139/0144 references |

---

## Appendix A: SaveSession API Draft

```python
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar
from enum import Enum

T = TypeVar("T", bound="AsanaResource")


class EntityState(Enum):
    """Lifecycle state of a tracked entity."""
    NEW = "new"           # No GID, will be created
    CLEAN = "clean"       # Tracked but unmodified
    MODIFIED = "modified" # Has changes pending
    DELETED = "deleted"   # Marked for deletion


class OperationType(Enum):
    """Type of operation to perform."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class PlannedOperation:
    """A planned operation returned by preview()."""
    entity: "AsanaResource"
    operation: OperationType
    payload: dict[str, Any]
    dependency_level: int


@dataclass
class SaveError:
    """Error information for a failed operation."""
    entity: "AsanaResource"
    operation: OperationType
    error: Exception
    payload: dict[str, Any]


@dataclass
class SaveResult:
    """Result of a commit operation."""
    succeeded: list["AsanaResource"]
    failed: list[SaveError]

    @property
    def success(self) -> bool:
        """True if all operations succeeded."""
        return len(self.failed) == 0

    @property
    def partial(self) -> bool:
        """True if some but not all operations succeeded."""
        return len(self.succeeded) > 0 and len(self.failed) > 0

    def raise_on_failure(self) -> None:
        """Raise PartialSaveError if any operations failed."""
        if self.failed:
            raise PartialSaveError(self)


class SaveSession:
    """
    Unit of Work pattern for batched Asana operations.

    Usage (async):
        async with SaveSession(client) as session:
            session.track(task)
            task.name = "Updated"
            result = await session.commit()

    Usage (sync):
        with SaveSession(client) as session:
            session.track(task)
            task.name = "Updated"
            result = session.commit()
    """

    def __init__(
        self,
        client: "AsanaClient",
        batch_size: int = 10,
        max_concurrent: int = 15,
    ) -> None:
        """Initialize save session.

        Args:
            client: AsanaClient instance for API calls
            batch_size: Maximum operations per batch (default: 10, Asana limit)
            max_concurrent: Maximum concurrent batch requests (default: 15)
        """
        ...

    async def __aenter__(self) -> "SaveSession":
        """Enter async context."""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        ...

    def __enter__(self) -> "SaveSession":
        """Enter sync context (wrapper)."""
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit sync context (wrapper)."""
        ...

    def track(self, entity: T) -> T:
        """Register entity for change tracking.

        Args:
            entity: AsanaResource instance to track

        Returns:
            The same entity (for chaining)

        Raises:
            SessionClosedError: If session is closed
        """
        ...

    def untrack(self, entity: "AsanaResource") -> None:
        """Remove entity from change tracking.

        Args:
            entity: Previously tracked entity
        """
        ...

    def delete(self, entity: "AsanaResource") -> None:
        """Mark entity for deletion.

        Args:
            entity: Entity to delete (must have GID)

        Raises:
            ValueError: If entity has no GID
        """
        ...

    def get_changes(self, entity: "AsanaResource") -> dict[str, tuple[Any, Any]]:
        """Get field-level changes for tracked entity.

        Args:
            entity: Tracked entity

        Returns:
            Dict of {field_name: (old_value, new_value)}
        """
        ...

    def get_state(self, entity: "AsanaResource") -> EntityState:
        """Get lifecycle state of tracked entity.

        Args:
            entity: Tracked entity

        Returns:
            Current EntityState
        """
        ...

    def get_dependency_order(self) -> list[list["AsanaResource"]]:
        """Get entities grouped by dependency level.

        Returns:
            List of lists, where index is dependency level
        """
        ...

    def preview(self) -> list[PlannedOperation]:
        """Preview planned operations without executing.

        Returns:
            List of PlannedOperation in execution order

        Raises:
            CyclicDependencyError: If dependency cycle detected
        """
        ...

    async def commit_async(self) -> SaveResult:
        """Execute all pending changes (async).

        Returns:
            SaveResult with succeeded/failed lists

        Raises:
            SessionClosedError: If session is closed
            CyclicDependencyError: If dependency cycle detected
        """
        ...

    def commit(self) -> SaveResult:
        """Execute all pending changes (sync wrapper).

        Returns:
            SaveResult with succeeded/failed lists
        """
        ...

    # Event hooks
    def on_pre_save(
        self,
        func: Callable[["AsanaResource", OperationType], None]
    ) -> Callable:
        """Decorator for pre-save hook."""
        ...

    def on_post_save(
        self,
        func: Callable[["AsanaResource", OperationType, Any], None]
    ) -> Callable:
        """Decorator for post-save hook."""
        ...

    def on_error(
        self,
        func: Callable[["AsanaResource", OperationType, Exception], None]
    ) -> Callable:
        """Decorator for error hook."""
        ...
```

## Appendix B: Exception Hierarchy

```python
class SaveOrchestrationError(AsanaError):
    """Base exception for save orchestration errors."""
    pass


class SessionClosedError(SaveOrchestrationError):
    """Raised when operating on a closed session."""
    pass


class CyclicDependencyError(SaveOrchestrationError):
    """Raised when dependency graph contains cycles."""

    def __init__(self, cycle: list["AsanaResource"]):
        self.cycle = cycle
        entities = " -> ".join(str(e) for e in cycle)
        super().__init__(f"Cyclic dependency detected: {entities}")


class DependencyResolutionError(SaveOrchestrationError):
    """Raised when a dependency cannot be resolved."""

    def __init__(
        self,
        entity: "AsanaResource",
        dependency: "AsanaResource",
        cause: Exception
    ):
        self.entity = entity
        self.dependency = dependency
        self.cause = cause
        super().__init__(
            f"Cannot save {entity}: dependency {dependency} failed"
        )


class PartialSaveError(SaveOrchestrationError):
    """Raised when some operations in a commit fail."""

    def __init__(self, result: "SaveResult"):
        self.result = result
        failed_count = len(result.failed)
        total = len(result.succeeded) + failed_count
        super().__init__(
            f"Partial save: {failed_count}/{total} operations failed"
        )
```

## Appendix C: Dependency Resolution Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEPENDENCY RESOLUTION FLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

1. GRAPH CONSTRUCTION
   ┌──────────────┐
   │ Tracked      │    For each entity:
   │ Entities     │──► - Check parent field
   │              │    - Check project field (new entities)
   └──────────────┘    - Check section field (new entities)
                       - Build adjacency list
                               │
                               ▼
2. CYCLE DETECTION (Kahn's Algorithm)
   ┌──────────────┐
   │ In-degree    │    - Count incoming edges per node
   │ Calculation  │    - If all nodes have in-degree > 0: CYCLE
   └──────────────┘              │
                                 ▼
3. TOPOLOGICAL SORT
   ┌──────────────┐
   │ Level        │    Level 0: Entities with no dependencies
   │ Assignment   │    Level 1: Entities depending only on Level 0
   └──────────────┘    Level N: Entities depending on Level N-1
                               │
                               ▼
4. BATCH GROUPING
   ┌──────────────┐
   │ Operations   │    Group by level, then by operation type
   │ by Level     │    Chunk into batches of 10
   └──────────────┘              │
                                 ▼
5. SEQUENTIAL EXECUTION
   ┌──────────────┐    Level 0 batches execute
   │ Level 0      │──► Extract GIDs from responses
   │ Batches      │    Update placeholder references
   └──────────────┘              │
                                 ▼
   ┌──────────────┐    Level 1 batches execute
   │ Level 1      │    (now have resolved GIDs from Level 0)
   │ Batches      │
   └──────────────┘              │
                                 ▼
                            ... repeat ...
                                 │
                                 ▼
6. RESULT AGGREGATION
   ┌──────────────┐
   │ SaveResult   │    - Collect succeeded entities
   │ Assembly     │    - Collect failed entities with errors
   └──────────────┘    - Return to caller
```

## Appendix D: Performance Comparison

| Scenario | Individual Calls | Batched (SaveSession) | Improvement |
|----------|------------------|----------------------|-------------|
| 100 independent task updates | 100 API calls | 10 API calls | 10x |
| 50 creates + 50 updates | 100 API calls | 10 API calls | 10x |
| 10 parents + 100 subtasks | 110 API calls | 12 API calls (2 levels) | ~9x |
| 1000 independent creates | 1000 API calls | 100 API calls | 10x |
| 5-level hierarchy (10 each) | 50 API calls | 5 API calls | 10x |

**Note**: Improvement is bounded by Asana's 10 actions/batch limit and dependency depth. Deep hierarchies (many levels) approach 1:1 ratio in worst case.

## Appendix E: Requirement Traceability

| Success Criterion | Requirement IDs |
|-------------------|-----------------|
| 70% API call reduction | NFR-PERF-001, FR-BATCH-001, FR-BATCH-006 |
| Automatic dependency ordering | FR-DEPEND-001, FR-DEPEND-002, FR-DEPEND-004 |
| Clear error reporting | FR-ERROR-001, FR-ERROR-002, FR-ERROR-003 |
| Dry run capability | FR-DRY-001, FR-DRY-002, FR-DRY-003 |
| Backward compatibility | NFR-COMPAT-001, NFR-COMPAT-006 |
| Async-first with sync wrapper | FR-UOW-004, NFR-COMPAT-002 |
| Observable operations | NFR-OBSERVE-001 through NFR-OBSERVE-007 |
