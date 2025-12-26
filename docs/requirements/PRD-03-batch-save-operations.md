# PRD-03: Batch & Save Operations

> Consolidated PRD for Batch API and SaveSession orchestration requirements.

## Metadata

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025-12-25 |
| **Consolidated From** | PRD-0005, PRD-0006, PRD-0008, PRD-0018 |
| **Related TDD** | TDD-04-batch-save-operations |
| **Stakeholders** | autom8 team, SDK consumers, API integrators, workflow automation developers |

---

## Executive Summary

The Batch & Save Operations capability provides a Unit of Work pattern for the autom8_asana SDK, enabling developers to batch multiple Asana operations into optimized API calls with automatic dependency ordering, change tracking, and comprehensive error handling.

**Key capabilities**:

1. **SaveSession Context Manager**: Async-first Unit of Work pattern with sync wrapper support
2. **Change Tracking**: Snapshot-based dirty detection with minimal payload generation
3. **Dependency Graph**: Automatic parent-child ordering with topological sort
4. **Action Endpoints**: Fluent API for operations requiring dedicated endpoints (tags, projects, dependencies, sections)
5. **Parent/Subtask Operations**: Reparenting and reordering through SaveSession
6. **Reliability**: GID-based entity identity, retryable error classification, partial failure handling

**Performance target**: 70% or greater reduction in API calls for batch-eligible operations (100 updates in 10 API calls instead of 100).

---

## Problem Statement

### The Immediate Persistence Problem

The SDK currently uses immediate persistence where every API call executes immediately. When developers modify multiple tasks, each change triggers a separate API call:

```python
# Current pattern: 3 API calls for 3 changes
task = await client.tasks.get_async("123")
await client.tasks.update_async("123", {"name": "New Name"})    # Call 1
await client.tasks.update_async("123", {"notes": "Updated"})    # Call 2
await client.tasks.update_async("456", {"name": "Other"})       # Call 3
```

**Consequences**:
- Rate limit pressure (1500 req/min consumed quickly)
- 10x performance penalty for batch-eligible operations
- No dependency awareness (parent must exist before subtask)
- Fragmented error handling across multiple calls

### The Silent Failure Problem

Certain Asana fields require action endpoints rather than standard PUT requests. The SDK silently ignores modifications to these fields:

```python
async with SaveSession(client) as session:
    task.tags.append(NameGid(gid="tag_456", name="Priority"))
    result = await session.commit()  # Tag NOT added - silently ignored
```

**Affected fields**: `tags`, `projects`, `memberships`, `dependencies`

### The Entity Identity Problem

The ChangeTracker uses Python's `id()` for entity identity, causing bugs when the same Asana resource is fetched multiple times:

```python
task_a = await client.tasks.get_async("12345")
task_b = await client.tasks.get_async("12345")  # Same GID, different object

session.track(task_a)
session.track(task_b)  # Tracked SEPARATELY - race condition on commit
```

### The Parent/Subtask Gap

Users cannot reparent tasks or reorder subtasks through SaveSession, losing type safety and consistency:

```python
# Current workaround: exit SaveSession, make raw API call
await client.http._request(
    "POST",
    f"/tasks/{task.gid}/setParent",
    json={"data": {"parent": "new_parent_gid"}}
)
```

---

## Goals & Non-Goals

### Goals

| ID | Goal | Target |
|----|------|--------|
| G-1 | Reduce API calls for batch operations | >= 70% reduction |
| G-2 | Automatic dependency ordering | Parent saved before subtask without manual sequencing |
| G-3 | Explicit action endpoint support | Tags, projects, dependencies, sections via fluent API |
| G-4 | Parent/subtask operations in SaveSession | `set_parent()` and `reorder_subtask()` methods |
| G-5 | GID-based entity identity | Same GID tracked once regardless of Python object count |
| G-6 | Retryable error classification | Programmatic determination of error recoverability |
| G-7 | Backward compatibility | Zero breaking changes to existing API |

### Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG-1 | ACID transactions / rollback | Asana API does not support transactions |
| NG-2 | Automatic retry mechanism | Deferred to future initiative |
| NG-3 | Offline sync / persistent queue | Crash recovery out of scope |
| NG-4 | Parallel execution of dependency levels | v1 uses sequential execution |
| NG-5 | Automatic conversion of direct modifications | Too magical; explicit methods preferred |
| NG-6 | Batch support for action endpoints | Asana limitation - action endpoints not batch-eligible |

---

## Requirements

### SaveSession Core (FR-UOW-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-UOW-001 | `SaveSession` as async context manager | Must |
| FR-UOW-002 | Explicit entity registration via `session.track(model)` | Must |
| FR-UOW-003 | `commit()` executes all pending changes | Must |
| FR-UOW-004 | Sync wrapper per ADR-0002 pattern | Must |
| FR-UOW-005 | Configurable batch size and concurrency | Should |
| FR-UOW-006 | Prevent re-use after commit or context exit | Must |
| FR-UOW-007 | Multiple commits within single context | Should |
| FR-UOW-008 | Entity lifecycle state tracking (new, modified, deleted, clean) | Must |

### Change Tracking (FR-CHANGE-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-CHANGE-001 | Snapshot comparison via `model_dump()` | Must |
| FR-CHANGE-002 | Field-level change sets | Must |
| FR-CHANGE-003 | New entity detection (missing/placeholder GID) | Must |
| FR-CHANGE-004 | `session.delete(model)` for deletion marking | Must |
| FR-CHANGE-005 | Skip clean entities during commit | Must |
| FR-CHANGE-006 | Minimal payloads (changed fields only) | Should |
| FR-CHANGE-007 | Nested object change detection | Must |
| FR-CHANGE-008 | `session.untrack(model)` support | Should |
| FR-CHANGE-009 | Reset entity state after successful save | Must |

### Dependency Graph (FR-DEPEND-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-DEPEND-001 | Auto-detect parent-child from `parent` field | Must |
| FR-DEPEND-002 | Topological sort via Kahn's algorithm | Must |
| FR-DEPEND-003 | `CyclicDependencyError` for cycles | Must |
| FR-DEPEND-004 | Placeholder GID resolution after parent creation | Must |
| FR-DEPEND-005 | Project-task dependencies for new tasks | Should |
| FR-DEPEND-006 | Section-task dependencies | Should |
| FR-DEPEND-007 | Group independent entities for batching | Must |

### Batch Execution (FR-BATCH-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-BATCH-001 | Group operations by dependency level | Must |
| FR-BATCH-002 | Delegate to existing `BatchClient` | Must |
| FR-BATCH-003 | Sequential chunk execution per ADR-0010 | Must |
| FR-BATCH-004 | Response correlation to entities | Must |
| FR-BATCH-005 | Update entity GIDs after creation | Must |
| FR-BATCH-006 | Respect Asana 10 actions/batch limit | Must |
| FR-BATCH-007 | Build appropriate BatchRequest per operation | Must |
| FR-BATCH-008 | Include custom field values in payloads | Must |
| FR-BATCH-009 | Handle rate limiting via TokenBucketRateLimiter | Must |

### Action Endpoints (FR-ACTION-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ACTION-001 | `session.add_tag(task, tag)` | Must |
| FR-ACTION-002 | `session.remove_tag(task, tag)` | Must |
| FR-ACTION-003 | `session.add_to_project(task, project)` | Must |
| FR-ACTION-004 | `session.remove_from_project(task, project)` | Must |
| FR-ACTION-005 | `session.add_dependency(task, depends_on)` | Must |
| FR-ACTION-006 | `session.remove_dependency(task, depends_on)` | Must |
| FR-ACTION-007 | `session.move_to_section(task, section)` | Must |
| FR-ACTION-008 | Accept entity objects or GID strings | Must |
| FR-ACTION-009 | Return self for fluent chaining | Should |
| FR-ACTION-010 | Queue operations until commit | Must |
| FR-ACTION-011 | Execute after standard CRUD operations | Must |
| FR-ACTION-012 | Support temp GID resolution | Must |

### Unsupported Operation Detection (FR-UNSUP-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-UNSUP-001 | Detect direct modifications to `task.tags` | Must |
| FR-UNSUP-002 | Detect direct modifications to `task.projects` | Must |
| FR-UNSUP-003 | Detect direct modifications to `task.memberships` | Must |
| FR-UNSUP-004 | Detect direct modifications to `task.dependencies` | Should |
| FR-UNSUP-005 | Detection during pre-save validation | Must |
| FR-UNSUP-006 | `UnsupportedOperationError` includes field name | Must |
| FR-UNSUP-007 | Error includes correct API guidance | Must |

### Parent/Subtask Operations (FR-PAR-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-PAR-001 | `set_parent(task, parent)` accepts task and parent | Must |
| FR-PAR-002 | `set_parent(task, None)` promotes subtask | Must |
| FR-PAR-003 | `insert_before` positioning parameter | Must |
| FR-PAR-004 | `insert_after` positioning parameter | Must |
| FR-PAR-005 | `PositioningConflictError` when both specified | Must |
| FR-PAR-006 | `reorder_subtask()` within current parent | Must |
| FR-PAR-007 | `reorder_subtask()` raises ValueError if no parent | Must |
| FR-PAR-008 | `SET_PARENT` ActionType added to enum | Must |
| FR-PAR-009 | Correct `POST /tasks/{gid}/setParent` generation | Must |
| FR-PAR-010 | Deferred execution until commit | Must |

### Entity Identity (FR-EID-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-EID-001 | Use GID as primary key (not Python `id()`) | Must |
| FR-EID-002 | Fallback to `__id_{id(entity)}` for GID-less entities | Must |
| FR-EID-003 | Support `temp_*` prefixed GIDs | Must |
| FR-EID-004 | Re-key entity when temp GID becomes real | Must |
| FR-EID-005 | Maintain `_gid_transitions` map | Must |
| FR-EID-006 | Update reference when same GID tracked twice | Must |
| FR-EID-007 | Log warning on duplicate tracking | Should |

### Entity Lookup (FR-EL-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-EL-001 | `find_by_gid(gid)` method | Could |
| FR-EL-002 | Return entity for real GID | Could |
| FR-EL-003 | Return entity for transitioned temp GID | Could |
| FR-EL-004 | Return None for unknown GID | Could |
| FR-EL-005 | `is_tracked(gid)` method | Could |

### Failure Handling (FR-FH-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-FH-001 | `SaveError.is_retryable` property | Should |
| FR-FH-002 | `is_retryable=True` for 429 errors | Should |
| FR-FH-003 | `is_retryable=True` for 5xx errors | Should |
| FR-FH-004 | `is_retryable=False` for 4xx (except 429) | Should |
| FR-FH-005 | `SaveResult.get_failed_entities()` | Should |
| FR-FH-006 | `SaveResult.get_retryable_errors()` | Should |

### Error Handling (FR-ERROR-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ERROR-001 | Partial commit (successful ops saved, failures reported) | Must |
| FR-ERROR-002 | `SaveResult` with `succeeded`, `failed`, `errors` | Must |
| FR-ERROR-003 | Error attribution to specific entities | Must |
| FR-ERROR-004 | `PartialSaveError` for partial failures | Must |
| FR-ERROR-005 | `CyclicDependencyError` for cycles | Must |
| FR-ERROR-006 | `DependencyResolutionError` for unresolved deps | Must |
| FR-ERROR-007 | `SessionClosedError` for closed session ops | Must |
| FR-ERROR-008 | Preserve original Asana errors in chain | Must |
| FR-ERROR-009 | Mark dependents as failed when dependency fails | Should |
| FR-ERROR-010 | `result.raise_on_failure()` convenience | Should |

### Preview/Dry Run (FR-DRY-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-DRY-001 | `session.preview()` returns planned ops | Must |
| FR-DRY-002 | PlannedOperation contains entity, type, payload | Must |
| FR-DRY-003 | Preview includes dependency order | Must |
| FR-DRY-004 | Preview validates operations | Should |
| FR-DRY-005 | Preview does not modify session state | Must |

### Self-Healing (FR-HEALING-*)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-HEALING-001 | Opt-in via `auto_heal` parameter | Must |
| FR-HEALING-002 | Heal after normal save operations | Must |
| FR-HEALING-003 | Heal only entities with `needs_healing=True` | Must |
| FR-HEALING-004 | Add healed entities to expected projects | Must |
| FR-HEALING-005 | `heal_dry_run` for preview mode | Must |
| FR-HEALING-006 | Report healing outcomes in SaveResult | Must |

---

## User Stories

### US-001: Batch Multiple Task Updates

**As a** developer
**I want** to batch multiple task updates
**So that** I reduce API calls and improve performance

```python
async with SaveSession(client) as session:
    for task in tasks:  # 50 tasks
        session.track(task)
        task.completed = True
    result = await session.commit()
    # 5 API calls instead of 50
```

### US-002: Create Task Hierarchy

**As a** developer
**I want** automatic dependency ordering
**So that** parent tasks are created before subtasks

```python
async with SaveSession(client) as session:
    parent = Task(name="Parent")
    subtask = Task(name="Subtask", parent=parent)
    session.track(parent)
    session.track(subtask)
    await session.commit()
    # Parent created first, GID resolved, subtask created with correct parent
```

### US-003: Add Tags to Task

**As a** developer
**I want** to add tags through SaveSession
**So that** tagging operations are properly executed

```python
async with SaveSession(client) as session:
    session.add_tag(task, urgent_tag)
    session.add_tag(task, priority_tag)
    await session.commit()
    # POST /tasks/{gid}/addTag called for each
```

### US-004: Multi-Home Task Across Projects

**As a** developer
**I want** to add a task to multiple projects
**So that** the task appears in each project

```python
async with SaveSession(client) as session:
    session.add_to_project(task, project_b)
    session.add_to_project(task, project_c)
    await session.commit()
```

### US-005: Convert Task to Subtask

**As a** workflow automation developer
**I want** to convert a task to a subtask
**So that** I can organize tasks hierarchically

```python
async with SaveSession(client) as session:
    session.set_parent(task, parent_task)
    await session.commit()
    # POST /tasks/{gid}/setParent
```

### US-006: Handle Duplicate Fetches

**As a** developer
**I want** changes from multiple fetches merged
**So that** I don't lose data from different code paths

```python
async with SaveSession(client) as session:
    task_a = await client.tasks.get_async("12345")
    task_b = await client.tasks.get_async("12345")

    session.track(task_a)
    session.track(task_b)

    task_a.name = "Updated"
    task_b.notes = "Also updated"

    result = await session.commit()
    # Single UPDATE with both changes
```

### US-007: Handle Partial Failures

**As a** developer
**I want** clear error reporting on partial failures
**So that** I know which operations succeeded and which failed

```python
result = await session.commit()

if not result.success:
    retryable = result.get_retryable_errors()
    for error in retryable:
        print(f"Will retry: {error.entity.gid}")

    permanent = [e for e in result.failed if not e.is_retryable]
    for error in permanent:
        print(f"Cannot retry: {error.entity.gid}")
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API call reduction | >= 70% for batch ops | 100 entities in <= 30 calls |
| Orchestration overhead | < 10ms per entity | Profiler excluding API latency |
| Memory overhead | < 5% for change tracking | Memory profiler comparison |
| Error attribution | 100% failures attributed | Test with intentional failures |
| Backward compatibility | 0 breaking changes | Existing test suite passes |
| Action endpoint coverage | 100% | Integration tests per endpoint |
| Entity identity deduplication | 100% | Same GID tracked once |
| mypy compliance | 0 errors | CI mypy --strict |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| BatchClient | Complete | `src/autom8_asana/batch/client.py` |
| BatchRequest / BatchResult | Complete | `src/autom8_asana/batch/models.py` |
| AsanaResource base model | Complete | `src/autom8_asana/models/base.py` |
| TokenBucketRateLimiter | Complete | `src/autom8_asana/transport/rate_limiter.py` |
| sync_wrapper decorator | Complete | `src/autom8_asana/transport/sync.py` |
| DefaultCustomFieldResolver | Complete | Custom field name-to-GID resolution |
| Task model with parent field | Complete | `src/autom8_asana/models/task.py` |

---

## Appendix A: Exception Hierarchy

```python
class SaveOrchestrationError(AsanaError):
    """Base exception for save orchestration errors."""

class SessionClosedError(SaveOrchestrationError):
    """Raised when operating on a closed session."""

class CyclicDependencyError(SaveOrchestrationError):
    """Raised when dependency graph contains cycles."""

class DependencyResolutionError(SaveOrchestrationError):
    """Raised when a dependency cannot be resolved."""

class PartialSaveError(SaveOrchestrationError):
    """Raised when some operations in a commit fail."""

class UnsupportedOperationError(SaveOrchestrationError):
    """Raised when attempting unsupported direct modification."""
```

---

## Appendix B: Asana Action Endpoint Reference

| Operation | Endpoint | Batch-Eligible |
|-----------|----------|----------------|
| Add tag | `POST /tasks/{gid}/addTag` | No |
| Remove tag | `POST /tasks/{gid}/removeTag` | No |
| Add to project | `POST /tasks/{gid}/addProject` | No |
| Remove from project | `POST /tasks/{gid}/removeProject` | No |
| Add dependency | `POST /tasks/{gid}/addDependencies` | No |
| Remove dependency | `POST /tasks/{gid}/removeDependencies` | No |
| Move to section | `POST /sections/{gid}/addTask` | No |
| Set parent | `POST /tasks/{gid}/setParent` | No |

---

## Appendix C: Error Classification Reference

| HTTP Status | is_retryable | Reason |
|-------------|--------------|--------|
| 400 Bad Request | False | Client error - payload invalid |
| 401 Unauthorized | False | Auth error - needs credential fix |
| 403 Forbidden | False | Permission error - needs access |
| 404 Not Found | False | Resource doesn't exist |
| 409 Conflict | False | Conflict - manual resolution |
| 429 Too Many Requests | **True** | Rate limit - retry after delay |
| 500 Internal Server Error | **True** | Server error - transient |
| 502 Bad Gateway | **True** | Server error - transient |
| 503 Service Unavailable | **True** | Server error - transient |
| 504 Gateway Timeout | **True** | Server error - transient |

---

## Appendix D: Performance Comparison

| Scenario | Individual Calls | Batched | Improvement |
|----------|------------------|---------|-------------|
| 100 task updates | 100 | 10 | 10x |
| 50 creates + 50 updates | 100 | 10 | 10x |
| 10 parents + 100 subtasks | 110 | 12 | ~9x |
| 1000 creates | 1000 | 100 | 10x |
| 5-level hierarchy (10 each) | 50 | 5 | 10x |

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-25 | Consolidated from PRD-0005, PRD-0006, PRD-0008, PRD-0018 |
