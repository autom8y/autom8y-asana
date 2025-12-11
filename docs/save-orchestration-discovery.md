# Save Orchestration Layer: Discovery Document

> Session 1 deliverable for PRD development. This document captures findings from exploration of the Asana Batch API capabilities and current SDK architecture to inform requirements definition in Session 2.

---

## 1. Executive Summary

This discovery document analyzes the feasibility of implementing a Save Orchestration Layer for the autom8_asana SDK. The layer would enable Django-ORM-style deferred saves where multiple model changes are collected and executed in optimized batches rather than immediately persisting each change.

Key findings indicate the SDK has a solid foundation for batch operations but lacks critical infrastructure for change tracking. The Asana Batch API supports up to 10 actions per request with per-action error handling, enabling partial success scenarios. The SDK's existing BatchClient already handles chunking, sequential execution, and result correlation. However, the Pydantic v2 models currently have no change tracking mechanism (no dirty flags, no original snapshots, no modified field detection). Implementing change tracking will require architectural decisions about whether to extend Pydantic's capabilities, wrap models, or maintain separate state.

The dependency ordering problem is significant: parent tasks must exist before subtasks can be created, and the save orchestrator must topologically sort operations to respect these constraints. The existing concurrency infrastructure (rate limiter, semaphores, retry handler) is fully reusable, but the orchestration logic representing the core intellectual challenge must be built from scratch.

---

## 2. Asana Batch API Capabilities

### 2.1 Endpoint Specification

| Attribute | Value |
|-----------|-------|
| Endpoint | `POST /batch` |
| Actions per batch | Maximum 10 |
| Request format | `{"data": {"actions": [...]}}` |
| Action schema | `{relative_path, method, data?, options?}` |
| Response format | Array of `{status_code, body, headers}` per action |
| Methods supported | GET, POST, PUT, DELETE |

Each action in a batch is independently processed and returns its own status code. A batch request itself can fail (e.g., malformed request), but individual actions within a successful batch request can independently succeed or fail.

### 2.2 Rate Limits and Concurrency

| Limit Type | Value | Notes |
|------------|-------|-------|
| Request rate | 1500 req/min | Applies to paid tier; each batch counts as 1 request |
| Concurrent GET | 50 | Soft limit enforced client-side |
| Concurrent write | 15 | Soft limit enforced client-side |
| Batch efficiency | 10x | 10 actions consume only 1 rate limit token |

**Rate limit violation behavior**: If the batch endpoint returns 429, the entire batch fails. Individual actions within a batch do not independently trigger rate limits - the batch as a whole is the rate-limited unit.

### 2.3 Partial Failure Semantics

The Asana Batch API supports partial success:

- **Batch-level success**: HTTP 200 with array of per-action results
- **Action-level failures**: Individual actions can fail (4xx, 5xx status in their result)
- **Atomic actions**: Each action is atomic; a failing action does not affect others
- **No rollback**: Successful actions in a batch are committed even if others fail

Example partial failure response:
```json
[
  {"status_code": 200, "body": {"data": {"gid": "123", "name": "Task 1"}}},
  {"status_code": 400, "body": {"errors": [{"message": "Invalid project GID"}]}},
  {"status_code": 200, "body": {"data": {"gid": "125", "name": "Task 3"}}}
]
```

### 2.4 Parent-Child Constraints

| Constraint | Type | Impact |
|------------|------|--------|
| Parent existence | Hard | Parent task must exist before subtask creation |
| `parent` field | Create-only | Cannot change parent after task creation |
| Project membership | Soft | Can add task to project before or after creation |
| Assignee existence | Soft | User must exist but can be set anytime |

**Critical ordering requirement**: When creating a task hierarchy (parent with subtasks), the parent must be created first, and the subtask creation must reference the parent's GID. This means:

1. Parent creation cannot be in the same batch as subtask creation (unless parent GID is pre-known)
2. If parent is newly created, its GID is unknown until the batch response
3. Save orchestrator must execute parent batch, extract GID, then execute subtask batch

---

## 3. Existing SDK Save Patterns

### 3.1 Current Persistence Model

The SDK currently uses **immediate persistence** - every API call executes immediately:

```python
# Current pattern: immediate execution
task = await client.tasks.get_async("123")
await client.tasks.update_async("123", {"name": "New Name"})  # Immediate API call
await client.tasks.update_async("123", {"notes": "Updated"})  # Another immediate call
```

There is no concept of:
- Deferred saves (unit of work pattern)
- Change accumulation
- Batch optimization of multiple changes to same resource
- Dependency-aware save ordering

### 3.2 BatchClient Architecture

Location: `src/autom8_asana/batch/client.py`

The BatchClient provides:

| Capability | Implementation |
|------------|----------------|
| Auto-chunking | Splits >10 actions into ceil(N/10) chunks |
| Sequential execution | Chunks execute one at a time (per ADR-0010) |
| Result correlation | Results indexed to match input request order |
| Partial failure handling | Per-action success/failure in BatchResult |
| Convenience methods | `create_tasks_async`, `update_tasks_async`, `delete_tasks_async` |

**Key code patterns**:
```python
# Chunk execution (from client.py lines 103-121)
for chunk_num, chunk in enumerate(chunks, 1):
    chunk_results = await self._execute_chunk(chunk, base_index)
    all_results.extend(chunk_results)
    base_index += len(chunk)
```

The BatchClient is a solid foundation but expects pre-built BatchRequest objects. It does not:
- Detect what has changed on models
- Build requests from model state
- Order requests by dependencies
- Merge multiple changes to the same resource

### 3.3 Sync/Async Pattern

Per ADR-0002, the SDK is async-first with sync wrappers:

| Pattern | Implementation |
|---------|----------------|
| Primary API | `async def method_async()` |
| Sync wrapper | `def method()` via `@sync_wrapper` decorator |
| Context detection | Fails fast if sync called from async context |
| Error message | Directs user to async variant |

The save orchestrator should follow this pattern:
- `async def save_async(models)` - primary implementation
- `def save(models)` - sync wrapper using `@sync_wrapper`

### 3.4 Error Handling

Location: `src/autom8_asana/exceptions.py`

Exception hierarchy:
```
AsanaError (base)
├── AuthenticationError (401)
├── ForbiddenError (403)
├── NotFoundError (404)
├── GoneError (410)
├── RateLimitError (429) - includes retry_after attribute
├── ServerError (5xx)
├── TimeoutError
└── ConfigurationError
```

Batch-specific error handling in `BatchResult`:
- `success` property: True if 200 <= status_code < 300
- `error` property: Returns `AsanaError` for failed actions
- `data` property: Unwraps successful response body

The save orchestrator will need additional error types:
- `DependencyError`: When dependent model save fails
- `PartialSaveError`: When some but not all models saved successfully
- `CyclicDependencyError`: When dependency graph has cycles

---

## 4. Pydantic Model Analysis

### 4.1 Current Architecture

Location: `src/autom8_asana/models/`

| Class | Lines | Purpose | Config |
|-------|-------|---------|--------|
| `AsanaResource` | 32 | Base for all resources | `extra="ignore"`, `populate_by_name=True` |
| `NameGid` | 60 | Immutable resource reference | `frozen=True`, hashable |
| `Task` | 112 | Task resource model | Inherits AsanaResource config |

Model configuration (per ADR-0005):
```python
model_config = ConfigDict(
    extra="ignore",           # Forward compatibility
    populate_by_name=True,    # Allow field aliases
    str_strip_whitespace=True,
)
```

### 4.2 Change Tracking Status

**Current state: NO change tracking exists.**

| Capability | Status | Notes |
|------------|--------|-------|
| Dirty flags | Not implemented | No `_is_dirty` attribute |
| Original snapshot | Not implemented | No `_original_data` stored |
| Modified field set | Not implemented | No `_modified_fields` tracking |
| Field-level tracking | Not implemented | No `__setattr__` override |
| Model comparison | Partial | Can compare via `model_dump()` |

The models are standard Pydantic v2 models with no change tracking extensions.

### 4.3 Feasibility Assessment

**Approaches to implement change tracking:**

| Approach | Complexity | Pros | Cons |
|----------|------------|------|------|
| 1. Pydantic validator hooks | Medium | Uses native Pydantic, no wrapper | Limited control over change detection |
| 2. Custom `__setattr__` | Medium | Fine-grained tracking | Must handle all edge cases |
| 3. Wrapper/proxy pattern | High | Separates concerns | Indirection complexity |
| 4. Snapshot comparison | Low | Simple, no model changes | O(n) comparison cost, no incremental |
| 5. External state manager | Medium | Clean separation | Must sync state with model |

**Recommended approach for Session 2 evaluation**: Snapshot comparison for v1 (simplest), with option to add `__setattr__` tracking in v2 for performance optimization.

Pydantic v2 capabilities that support change tracking:
- `model_dump()`: Serialize to dict for comparison
- `model_copy(deep=True)`: Create snapshot
- `model_fields`: Introspect field names
- `model_validate`: Reconstruct from dict

---

## 5. Dependency Scenarios

| Dependency Type | Constraint | Hard/Soft | Save Order Impact |
|-----------------|------------|-----------|-------------------|
| Parent task -> Subtask | Subtask requires parent GID | Hard | Parent must save first; subtask batch waits for GID |
| Project -> Task | Task can reference project | Soft | Can save in any order; project should exist |
| User -> Assignee | Task can reference user | Soft | User must exist but typically pre-exists |
| Section -> Task membership | Task added to section | Soft | Section should exist; can retry if missing |
| Tag -> Task | Task can have tags | Soft | Tags should exist but typically pre-exist |
| Custom field -> Task | Task has custom field values | Soft | Custom field definition must exist |
| Dependency task -> Dependent | Task depends on another task | Soft | Both tasks should exist; order flexible |

**Hard constraints** require strict ordering. **Soft constraints** allow retry or graceful failure.

**Dependency detection sources**:
- `parent` field: Explicit subtask relationship
- `projects` list: Project membership (usually pre-existing)
- `assignee` field: User reference (usually pre-existing)
- `memberships` list: Section placement
- `dependencies` relationship: Task dependencies (separate API)

---

## 6. Concurrency Model Analysis

### 6.1 Current Infrastructure

Location: `src/autom8_asana/transport/`

| Component | File | Purpose |
|-----------|------|---------|
| `TokenBucketRateLimiter` | rate_limiter.py | 1500 tokens / 60s refill |
| `RetryHandler` | retry.py | Exponential backoff with jitter |
| `AsyncHTTPClient` | http.py | Connection pooling, semaphores |
| Semaphores | http.py | 50 read, 15 write concurrent |
| asyncio.Lock | http.py, rate_limiter.py | Thread-safe client initialization |

Rate limiter implementation:
```python
class TokenBucketRateLimiter:
    max_tokens: int = 1500
    refill_period: float = 60.0  # 25 tokens/sec refill rate
```

### 6.2 Reusability Assessment

| Component | Reusable for Save Orchestrator | Notes |
|-----------|-------------------------------|-------|
| TokenBucketRateLimiter | Yes, fully | Batch requests already rate-limited |
| RetryHandler | Yes, fully | Can retry failed batches |
| Write semaphore | Yes, fully | Limits concurrent batch executions |
| asyncio.Lock | Pattern reusable | May need locks for dependency state |
| BatchClient | Yes, fully | Core execution engine |

**New components needed**:
- Dependency graph builder
- Topological sort for save ordering
- Pending GID resolution (placeholder -> actual)
- Save session state manager

---

## 7. Performance Baseline (Estimated)

### 7.1 Naive Approach

Saving 100 tasks individually:
```
100 tasks * 1 API call each = 100 API calls
100 calls / 25 tokens/sec = 4 seconds minimum (rate limit bound)
100 calls * 100ms avg latency = 10 seconds (latency bound)
```

**Estimated time**: 4-10 seconds depending on rate limit headroom

### 7.2 Batched Approach

Saving 100 tasks with batch optimization:
```
100 tasks / 10 per batch = 10 batches
10 batches * 1 API call each = 10 API calls
10 calls / 25 tokens/sec = 0.4 seconds (rate limit)
10 calls * 100ms latency * sequential = 1 second
```

**Estimated time**: 1-2 seconds

### 7.3 Optimization Potential

| Scenario | Naive | Batched | Improvement |
|----------|-------|---------|-------------|
| 100 independent creates | 10s | 1s | 10x |
| 50 updates + 50 creates | 10s | 1s | 10x |
| 10 parent + 100 subtasks | 11s | 1.2s | ~9x (2 batch phases) |
| 1000 independent creates | 100s | 10s | 10x |

**Batch efficiency ceiling**: 10x improvement (10 actions per batch).

**Dependency overhead**: Each hard dependency level adds one sequential batch round. A 3-level hierarchy (grandparent -> parent -> child) requires 3 sequential batch rounds minimum.

---

## 8. Capability Gap Analysis

### 8.1 Missing Capabilities (Prioritized)

| Priority | Capability | Effort | Dependency |
|----------|------------|--------|------------|
| P0 | Change tracking mechanism | Medium | None |
| P0 | Dependency graph builder | Medium | Change tracking |
| P0 | Topological sort for save order | Low | Dependency graph |
| P0 | GID placeholder resolution | Medium | Batch execution |
| P1 | Save session manager | Medium | Change tracking |
| P1 | Partial failure recovery | Medium | Batch execution |
| P1 | New exception types | Low | None |
| P2 | Change merging (multiple updates to same resource) | Medium | Change tracking |
| P2 | Optimistic concurrency (version conflicts) | High | Model extension |
| P3 | Parallel dependency-level execution | High | Dependency graph |

### 8.2 Existing Patterns to Reuse

| Component | Reuse Strategy |
|-----------|----------------|
| BatchClient | Use directly for batch execution |
| BatchRequest/BatchResult | Use for request building and result parsing |
| TokenBucketRateLimiter | Automatic via HTTP client |
| RetryHandler | Automatic via HTTP client |
| AsanaError hierarchy | Extend for save-specific errors |
| @sync_wrapper | Apply to save orchestrator methods |
| PageIterator pattern | Inspire chunked save iteration |

---

## 9. Open Questions for Session 2

**Architecture decisions needed**:
- [ ] Should change tracking be opt-in (explicit) or automatic (transparent)?
- [ ] Should the save orchestrator be a separate class or integrated into the client?
- [ ] How should placeholder GIDs be represented (string prefix, sentinel type, etc.)?
- [ ] Should we support "dry run" mode to preview batch operations without executing?

**Scope decisions needed**:
- [ ] Which resource types need save orchestration in v1? (Tasks only? Projects? All?)
- [ ] Should v1 support update coalescing (multiple updates to same resource merged)?
- [ ] What is the maximum batch size the orchestrator should handle before warning?
- [ ] Should dependency detection be automatic (introspect models) or explicit (user declares)?

**Error handling decisions needed**:
- [ ] On partial failure, should successful saves be committed or rolled back (if possible)?
- [ ] How should cyclic dependencies be handled (error? break cycle? user choice)?
- [ ] Should retries be automatic for transient failures or expose to user?

**Performance decisions needed**:
- [ ] Should dependency levels execute in parallel where independent?
- [ ] What is acceptable latency overhead for the orchestration logic itself?
- [ ] Should we provide progress callbacks for large save operations?

---

## 10. References

### Files Analyzed
- `/src/autom8_asana/models/base.py` - AsanaResource base class (32 lines)
- `/src/autom8_asana/models/common.py` - NameGid and PageIterator (187 lines)
- `/src/autom8_asana/models/task.py` - Task model (112 lines)
- `/src/autom8_asana/batch/client.py` - BatchClient implementation (440 lines)
- `/src/autom8_asana/batch/models.py` - BatchRequest/BatchResult (236 lines)
- `/src/autom8_asana/transport/http.py` - AsyncHTTPClient (498 lines)
- `/src/autom8_asana/transport/rate_limiter.py` - TokenBucketRateLimiter (124 lines)
- `/src/autom8_asana/transport/retry.py` - RetryHandler (93 lines)
- `/src/autom8_asana/transport/sync.py` - sync_wrapper (67 lines)
- `/src/autom8_asana/exceptions.py` - Exception hierarchy (198 lines)
- `/src/autom8_asana/config.py` - Configuration dataclasses (180 lines)
- `/src/autom8_asana/clients/base.py` - BaseClient (68 lines)

### ADRs Referenced
- ADR-0002: Sync/Async Wrapper Strategy - fail-fast pattern
- ADR-0005: Pydantic v2 with extra="ignore" - forward compatibility
- ADR-0006: NameGid as Standalone Frozen Model - immutable references
- ADR-0010: Sequential Chunk Execution for Batch Operations - ordering guarantees

### External Documentation
- Asana API Batch Endpoint: `POST /batch` with 10 action limit
- Asana Rate Limits: 1500 req/min for paid tier
- Pydantic v2 Documentation: ConfigDict, model_dump, model_copy

---

*Document Version: 1.0*
*Created: 2025-12-10*
*Status: Complete - Ready for Session 2 PRD Development*
