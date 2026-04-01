---
domain: feat/batch-api-client
generated_at: "2026-04-01T18:00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/batch/**/*.py"
  - "./src/autom8_asana/persistence/executor.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# Asana Batch API Client

## Purpose and Design Rationale

Thin orchestration layer over Asana's `/batch` endpoint (up to 10 actions per request). Driven by two use cases: `SaveSession` entity mutations (via `BatchExecutor`) and action operations like tag add/remove (via `ActionExecutor`). Also exposed directly via `AsanaClient.batch` for SDK consumers.

**Sequential chunk design (ADR-0010)**: Chunks beyond 10 issued as separate calls, processed sequentially (not concurrent) to respect rate limits.

**Partial failure contract**: Individual action failures captured as `BatchResult.error`, not raised. Only `/batch` endpoint failures propagate as `AsanaError`. A batch with 9 successes and 1 failure does not roll back the 9.

## Conceptual Model

### Three-Tier Structure

```
BatchRequest (frozen)     -- relative_path, method, data, options, to_action_dict()
BatchClient (BaseClient)  -- execute_async (core), convenience methods, chunking
BatchResult (frozen)      -- status_code, body, success property, error property, request_index
BatchSummary (mutable)    -- results list, total/succeeded/failed counts
```

**Chunking invariants**: `BATCH_SIZE_LIMIT = 10`, `base_index` accumulates across chunks for 1:1 correlation to input positions.

### Dual Consumer Pattern

1. **`BatchExecutor`** (`persistence/executor.py`): CRUD operations for `SaveSession`. Maps `OperationType` -> HTTP method, `resource_type` -> plural API path.
2. **`ActionExecutor`** (`persistence/action_executor.py`): Routes action-endpoint operations (tags, project membership, dependencies) through batch via `action_to_batch_request()`.

### Request Lifecycle Through SaveSession

SaveSession -> SavePipeline -> DependencyGraph levels -> BatchExecutor.execute_level() -> BatchClient.execute_async() -> _execute_chunk() (POST /batch) -> BatchResult correlation -> SavePipeline CONFIRM phase (GID resolution from successful creates).

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/batch/__init__.py` | Exports: BatchClient, BatchRequest, BatchResult, BatchSummary |
| `src/autom8_asana/batch/client.py` | BatchClient (extends BaseClient); chunking helpers; BATCH_SIZE_LIMIT=10 |
| `src/autom8_asana/batch/models.py` | BatchRequest, BatchResult, BatchSummary dataclasses |
| `src/autom8_asana/persistence/executor.py` | BatchExecutor; wraps BatchClient; _resource_to_path lookup |
| `src/autom8_asana/persistence/action_executor.py` | action_to_batch_request(); batch_result_to_action_result() |
| `src/autom8_asana/client.py:602-640` | AsanaClient.batch property (thread-safe lazy init) |

**Response format handling**: `/batch` returns either raw list or dict-wrapped list (Asana inconsistency). `_execute_chunk` handles both via `isinstance` check.

**Sync wrapper**: Uses `@sync_wrapper` from `transport/sync.py` (not `@async_method`).

## Boundaries and Failure Modes

### Owns

- Chunking requests into <=10 slices
- Sequential chunk execution
- Deserializing per-action responses into BatchResult
- Logging chunk progress and summary counts

### Does Not Own

- Building BatchRequest from entity state (BatchExecutor)
- GID resolution after creation (SavePipeline CONFIRM)
- Cache invalidation (CacheInvalidator)
- Dependency ordering (DependencyGraph)

### Known Failure Modes

1. **Silent result truncation**: No length assertion comparing `len(chunk)` to `len(response)`. If Asana truncates, results misalign silently.
2. **Dict response wrapping**: Fallback path wraps single-item dict as one-element list -- could produce 1 result for 10-item chunk.
3. **`_resource_to_path` default pluralization**: Falls back to appending "s" for unmapped types (irregular plurals would fail).
4. **No explicit retry on `/batch` 5xx**: Relies on transport layer's circuit breaker.
5. **`batch_size` parameter in BatchExecutor is vestigial**: Accepted but never passed to BatchClient.
6. **No PATCH support**: Validated against {GET, POST, PUT, DELETE} only.

### Layer Compliance

`batch/` imports from `clients/base.py`, `transport/sync.py`, `exceptions.py` (Infrastructure). `persistence/executor.py` imports from `batch/models.py`. Dependency arrow: persistence -> batch -> clients/transport (consistent with layer model).

## Knowledge Gaps

1. `@sync_wrapper` behavior vs `@async_method` (SyncInAsyncContextError guard) not verified.
2. Transport retry/circuit-breaker interaction with batch POST not traced.
3. `ActionExecutor` full routing logic only partially read.
4. No test files for `batch/` located or read.
5. `clients/data/_endpoints/batch.py` (separate module) relationship not investigated.
