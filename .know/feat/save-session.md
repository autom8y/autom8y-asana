---
domain: feat/save-session
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/persistence/"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.95
format_version: "1.0"
---

# SaveSession Unit of Work Pattern

## Purpose and Design Rationale

`SaveSession` (`src/autom8_asana/persistence/session.py`) implements the Unit of Work pattern for Asana API writes, per FR-UOW-001 through FR-UOW-008 and ADR-0035. Callers register entity mutations inside a context manager and then commit in a single dependency-ordered, batch-optimized operation.

**Problem it solves**: Asana has no transaction API. Writing a composite entity (e.g. a Business with contacts, units, offers, and processes) requires sequenced POST/PUT/DELETE calls where later calls depend on GIDs returned by earlier ones. Without a session abstraction, every caller must manage ordering, GID resolution, partial failure handling, cache invalidation, and post-commit side effects — all error-prone.

**Design decisions with rationale**:

- **Unit of Work / deferred-save** (ADR-0035): Changes collected at `track()` time; snapshot captured; API calls deferred to `commit_async()`. Prevents interleaved partial writes.
- **Kahn's topological sort** (ADR-0037 / `graph.py:1-3`): O(V+E) dependency ordering for level-based batch execution.
- **Temp GID two-phase resolution** (pipeline.py:235, 585): New entities assigned `temp_{id(entity)}` at track time; real GIDs returned from Asana after CREATE are patched back via `object.__setattr__(entity, "gid", real_gid)`. This is a permanent architectural constraint — Asana cannot pre-allocate GIDs.
- **threading.RLock** (TDD-DEBT-003): All state mutations protected by reentrant lock. Rationale: callers may call `track()` from multiple threads concurrently on the same session.
- **`_require_open()` context manager** (SCAR-010/010b fix): TOCTOU-safe guard that acquires the lock and verifies session is not CLOSED before performing operations.
- **No rollback**: Per ADR-0040, partial failures commit successful operations and report failures. Asana has no server-side transaction support, making rollback semantically impossible.
- **No auto-commit on context exit**: Per FR-UOW-001, uncommitted changes are silently discarded. Callers must call `commit_async()` or `commit()` explicitly.
- **BROAD-CATCH isolation on automation phase** (NFR-003): `except (ConnectionError, TimeoutError, OSError, RuntimeError, TypeError)` at `session.py:1028-1034`. Automation failures must never fail commit — the phase is advisory.
- **Chunk-level fallback to sequential in action batch**: Resilience pattern in `action_executor.py`.

**Tradeoffs accepted**:
- No rollback means partial failures leave the system in an inconsistent state; callers must inspect `SaveResult.failed` and decide on retry.
- Temp GID two-phase resolution is a structural coupling: `SavePipeline` and `ActionExecutor` must both resolve temp GIDs from the same `gid_map`.

**Decision records**: ADR-0035 (Unit of Work), ADR-0037 (Kahn's algorithm), ADR-0040 (partial failure semantics), ADR-0050 (prefetch_holders), ADR-0053 (recursive tracking), ADR-0059 (cache invalidation SRP), ADR-0060 (per-session name resolver cache), ADR-0066 (selective action clearing), ADR-0074 (snapshot ordering), ADR-0078 (GID deduplication), ADR-0079 (retryable error classification), ADR-0095 (self-healing), ADR-0107 (action identity).

---

## Conceptual Model

### Session State Machine

`SessionState` (defined at `session.py:55-66`) has three states:

```
OPEN ──commit_async()──> COMMITTED ──commit_async()──> COMMITTED (repeatable)
OPEN ──__aexit__()──────> CLOSED
COMMITTED ──__aexit__()─> CLOSED
CLOSED ──any operation──> raises SessionClosedError
```

`OPEN` accepts `track()`, `untrack()`, action methods, and `commit_async()`.
`COMMITTED` is a post-commit marker; the session remains usable (supports multiple commits per FR-UOW-007).
`CLOSED` is terminal; raised by `_require_open()` on any further access.

### The Six Commit Phases

`commit_async()` (`session.py:726`) orchestrates up to six phases:

| Phase | Name | What Happens | Key Component | Condition |
|-------|------|-------------|---------------|-----------|
| 0 | ENSURE_HOLDERS | Detect and construct missing holder subtasks | `HolderEnsurer`, `HolderConcurrencyManager` | `auto_create_holders=True` (default) |
| 1 | CRUD + ACTIONS | Topologically sorted CRUD via `BatchExecutor`, then action operations via `ActionExecutor` | `SavePipeline.execute_with_actions()` | Always (if dirty entities or pending actions) |
| 1.5 | CACHE INVALIDATION | TASK, SUBTASKS, DETECTION + DataFrame cache invalidated | `CacheInvalidator` | If `_cache_invalidator` wired |
| 2 | CASCADE | Field propagation from source to descendants | `CascadeExecutor` | If `_cascade_operations` non-empty |
| 3 | HEALING | Missing project memberships repaired | `HealingManager` | If `_healing_manager.queue` non-empty |
| 5 | AUTOMATION | Rule evaluation against `SaveResult` | `client.automation.evaluate_async()` | `automation_enabled=True` |

Phase 4 in the original 4-phase pipeline (`pipeline.py:1-14`) is the CONFIRM step embedded within `SavePipeline.execute()` — it resolves GIDs and updates entities. The automation phase is numbered 5 in TDD-AUTOMATION-LAYER, with 4 unused in session-level numbering.

### Temp GID Resolution Chain

1. New entities enter with `gid` starting with `"temp_"` (or assigned by caller as `temp_{id(entity)}`).
2. `DependencyGraph.build()` indexes these entities into the topology.
3. `SavePipeline._prepare_operations()` resolves parent fields by looking up `gid_map`.
4. After CREATE at phase 3 (EXECUTE), `batch_result.data["gid"]` returns the real GID.
5. `object.__setattr__(entity, "gid", real_gid)` patches the entity in-place (`pipeline.py:240`).
6. `ActionExecutor._resolve_temp_gids()` applies the same `gid_map` to action targets (`action_executor.py:338`).

This two-phase resolution is a **permanent architectural constraint** — see TENSION-011/LB-004 in prior scar documentation (now superseded by design-constraints.md entries).

### Inter-Feature Relationships

- **Provides to**: `clients/task_operations.py` — 5 convenience methods raise `SaveSessionError` wrapping `SaveResult` on failure; `models/task.py:415-426` — `Task.save_async()` convenience method.
- **Consumes from**: `batch/client.py` (`BatchClient`) — batch API execution; `cache/dataframe/factory.py` — `get_dataframe_cache()` for invalidation; `automation/` — `client.automation.evaluate_async()` for Phase 5.
- **Held by**: `client.py` (`AsanaClient` facade) — `SaveSession` is instantiated per-use, not a singleton.

---

## Implementation Map

### Package: `src/autom8_asana/persistence/` (20 files)

| File | Purpose | Key Types |
|------|---------|-----------|
| `session.py` (~1820 lines) | User-facing entry point; orchestrates all phases | `SaveSession`, `SessionState` |
| `pipeline.py` | 4/5-phase CRUD orchestration | `SavePipeline`, `UNSUPPORTED_FIELDS` |
| `tracker.py` | Snapshot capture + dirty detection | `ChangeTracker` |
| `graph.py` | Kahn's topological sort | `DependencyGraph` |
| `executor.py` | BatchClient wrapper per level | `BatchExecutor` |
| `action_executor.py` | Action operation execution + temp GID resolution | `ActionExecutor` |
| `action_ordering.py` | Action dependency ordering | — |
| `actions.py` | Action operation builder | `ActionBuilder` |
| `cascade.py` | Field propagation to descendants | `CascadeExecutor`, `CascadeResult`, `CascadeOperation` |
| `healing.py` | Project membership repair | `HealingManager` |
| `holder_concurrency.py` | asyncio.Lock keyed by (parent_gid, holder_type) — prevents duplicate holder creation | `HolderConcurrencyManager` |
| `holder_construction.py` | Holder subtask construction logic | — |
| `holder_ensurer.py` | Phase 0 — detects missing holders | `HolderEnsurer` |
| `cache_invalidator.py` | Cache invalidation coordinator (ADR-0059) | `CacheInvalidator` |
| `validation.py` | Field validation utilities | — |
| `events.py` | Pre/post save hooks, post-commit event | `EventSystem` |
| `reorder.py` | LIS-based section reorder planning | `ReorderPlan` |
| `models.py` | Domain models for save operations | `SaveResult`, `SaveError`, `ActionOperation`, `ActionResult`, `ActionType`, `EntityState`, `OperationType`, `PlannedOperation`, `HealingReport`, `AutomationResult` |
| `errors.py` | Exception hierarchy | `SaveOrchestrationError`, `SessionClosedError`, `CyclicDependencyError`, `DependencyResolutionError`, `PartialSaveError`, `UnsupportedOperationError`, `PositioningConflictError`, `GidValidationError`, `SaveSessionError` |
| `__init__.py` | Module exports | — |

### Key Entry Points

**`SaveSession.__init__`** (`session.py:136`): Constructor wires `ChangeTracker`, `DependencyGraph`, `EventSystem`, `SavePipeline`, `ActionExecutor`, `CascadeExecutor`, `NameResolver`, `HealingManager`, `CacheInvalidator`, and optionally `HolderConcurrencyManager`.

**`SaveSession.track()`** (`session.py:381`): Registers entity under `_require_open()` lock; captures snapshot via `ChangeTracker.track()`; optionally queues healing.

**`SaveSession.commit_async()`** (`session.py:726`): Main execution entry. Lock held during state check + state capture (`_capture_commit_state()`); released during I/O; re-acquired for post-commit state update.

**`SaveSession.commit()`** (`session.py:1092`): Sync wrapper via `sync_wrapper` (ADR-0002 pattern from `transport/sync.py`).

**`SavePipeline.execute_with_actions()`** (`pipeline.py:547`): 5-phase method called from session Phase 1. Runs VALIDATE → CRUD execute → ACTION execute → return combined result.

**`session.py:995-1001`** (SCAR-008 / DEF-001 fix): Order-critical block — `_reset_custom_field_tracking(entity)` MUST precede `_tracker.mark_clean(entity)` to avoid stale custom field state in snapshot.

### Data Flow: Primary Commit Path

```
SaveSession.commit_async()
  → _capture_commit_state()            [lock: snapshot dirty entities + pending work]
  → _execute_ensure_holders()          [Phase 0: HolderEnsurer if auto_create_holders]
  → _execute_crud_and_actions()        [Phase 1: SavePipeline.execute_with_actions()]
      → SavePipeline.validate_no_unsupported_modifications()
      → SavePipeline.execute()         [VALIDATE → PREPARE → EXECUTE → CONFIRM per level]
          → DependencyGraph.build() + get_levels()
          → _prepare_operations() [temp GID resolution via gid_map]
          → BatchExecutor.execute_level()  [Asana HTTP]
          → GID patching: object.__setattr__(entity, "gid", real_gid)
      → ActionExecutor.execute_async() [action ops with gid_map]
      → CacheInvalidator.invalidate_for_commit()  [Phase 1.5]
  → _execute_cascades()                [Phase 2: CascadeExecutor]
  → _execute_healing()                 [Phase 3: HealingManager]
  → _update_post_commit_state()        [lock: _reset_custom_field_tracking + mark_clean]
  → _execute_automation()              [Phase 5: BROAD-CATCH isolated]
  → _finalize_commit()                 [post-commit event emission]
```

### Public API Surface

Consumed by: `clients/task_operations.py` (5 methods), `models/task.py` (Task.save_async), `client.py` (AsanaClient facade).

Key exported types from `persistence/__init__.py`: `SaveSession`, `SaveResult`, `SessionClosedError`, `PartialSaveError`, `SaveSessionError`.

### Test Coverage

28+ test files in `tests/unit/persistence/`:

| File | Coverage Focus |
|------|---------------|
| `test_session_concurrency.py` | 19 tests: SCAR-010/010b RLock safety, `_require_open()`, `TestAC001-006`, `TestActionMethodThreadSafety`, `TestRLockReentrance`, `TestConcurrencyEdgeCases` |
| `test_session.py` | Core session lifecycle, track/untrack, commit semantics |
| `test_session_business.py` | Business entity tracking + recursive |
| `test_session_cascade.py` | Cascade phase integration |
| `test_session_healing.py` | Healing phase |
| `test_session_invalidation.py` | Cache invalidation wiring |
| `test_session_dataframe_invalidation.py` | DataFrame cache invalidation |
| `test_session_detection_invalidation.py` | Detection cache invalidation |
| `test_pipeline.py` | SavePipeline phases |
| `test_graph.py` | DependencyGraph / Kahn's sort |
| `test_executor.py` | BatchExecutor |
| `test_action_executor.py` | ActionExecutor + temp GID resolution |
| `test_action_ordering.py` | Action dependency ordering |
| `test_action_batch_adversarial.py` | Adversarial action batch scenarios |
| `test_cascade.py` | CascadeExecutor |
| `test_healing.py` | HealingManager |
| `test_holder_ensurer.py` | Phase 0 holder detection |
| `test_holder_construction.py` | Holder creation |
| `test_cache_invalidator.py` | CacheInvalidator |
| `test_custom_field_persistence.py` | Custom field tracking + DEF-001 ordering |
| `test_events.py` | EventSystem hooks |
| `test_exceptions.py` | Error hierarchy |
| `test_tracker.py` | ChangeTracker snapshots |
| `test_models.py` | SaveResult, ActionOperation models |
| `test_reorder.py` | LIS-based reorder |
| `test_reorder_adversarial.py` | Adversarial reorder scenarios |
| `test_boundary_conditions.py` | Edge cases |
| `test_hardening_a.py` | Hardening scenarios |

**Performance budget (PERF-BUDGET-REGRESSION-001)**: `test_lock_overhead_under_contention` budget is `< 2ms` per operation under contention (widened from 1ms at `f37802f2`, B-3 recalibration for slower CI runners). Non-contention budgets unchanged: `< 1ms` for track, `< 100μs` for state read.

---

## Boundaries and Failure Modes

### What SaveSession Does NOT Do

- **No rollback**: Successful operations already committed to Asana cannot be undone. Callers inspect `SaveResult.failed`.
- **No auto-commit**: Context exit (`__aexit__`) sets state to CLOSED but does NOT commit. Uncommitted changes are silently discarded.
- **No direct field updates for UNSUPPORTED_FIELDS**: `tags`, `projects`, `memberships`, `dependencies`, `dependents`, `followers` raise `UnsupportedOperationError` if modified directly — callers must use action methods (`add_tag()`, `add_to_project()`, etc.). Defined at `pipeline.py:48-55`.
- **No GID pre-allocation**: Asana cannot assign GIDs before resource creation. New entities always start with `temp_` GIDs.
- **No cross-session coordination**: Sessions are independent; concurrent sessions from different callers may conflict at the Asana API level.

### Active Scars

| SCAR | Description | Fix Location | Test Coverage |
|------|-------------|-------------|---------------|
| **SCAR-008 / DEF-001** | `SaveSession` previously cleared snapshot before accessor reset — caused stale custom field state surviving into next commit snapshot | `session.py:995-1001` (accessor cleared BEFORE `mark_clean()`) | No isolated regression test — gap confirmed in `.know/scar-tissue.md` |
| **SCAR-010 / SCAR-010b** | Session state mutation race + `_require_open()` contract bypass | `threading.RLock` + `_require_open()` context manager at `session.py:1683-1723` | `test_session_concurrency.py` (19 tests, classes AC001-006) |
| **TENSION-011 / LB-004** | Temp GID two-phase resolution is a permanent architectural constraint — `SavePipeline` and `ActionExecutor` share `gid_map` coupling | `pipeline.py:235,585`, `action_executor.py:193,338` | Implicit via `test_pipeline.py`, `test_action_executor.py` |

### Error Hierarchy (rooted at `SaveOrchestrationError`)

```
AsanaError (top-level)
  └── SaveOrchestrationError   [persistence/errors.py:18]
        ├── SessionClosedError        [raised by _require_open()]
        ├── CyclicDependencyError     [raised by DependencyGraph on cycle]
        ├── DependencyResolutionError [raised on cascading parent failure]
        ├── PartialSaveError          [raised by SaveResult.raise_if_failed()]
        ├── UnsupportedOperationError [raised on direct UNSUPPORTED_FIELDS modification]
        ├── PositioningConflictError  [raised on conflicting insert_before/after]
        ├── GidValidationError        [raised on malformed GID]
        └── SaveSessionError          [used by clients/task_operations.py convenience wrappers]
```

`PartialSaveError` exposes `.is_retryable`, `.retryable_count`, `.non_retryable_count` (ADR-0079).

### Interaction Points with Other Features

- **`clients/task_operations.py`** (boundary consumer): 5 convenience methods (`add_tag`, `remove_tag`, `add_to_project`, `remove_from_project`, `add_follower`) construct a `SaveSession` internally, commit, and raise `SaveSessionError` on failure. These are the primary external callers outside of direct session use.
- **`models/task.py`** (boundary consumer): `Task.save_async()` at `task.py:393-426` wraps `SaveSession` for single-task saves.
- **`cache/`** (downstream): `CacheInvalidator` calls `get_dataframe_cache()` via lazy import at `session.py:229` — tight coupling to cache subsystem initialization order at startup.
- **`automation/`** (downstream): `client.automation.evaluate_async()` called in Phase 5. Failure is isolated via BROAD-CATCH at `session.py:1028-1034`.
- **`persistence/holder_concurrency.py`**: `HolderConcurrencyManager` uses `asyncio.Lock` (NOT `threading.RLock`) — coroutine-safe but NOT thread-safe. The session's Phase 0 is async-only.

### Configuration Boundaries

| Parameter | Default | Effect |
|-----------|---------|--------|
| `batch_size` | 10 | Asana max batch size — do not exceed |
| `max_concurrent` | 15 | Reserved for future optimization (not currently enforced) |
| `auto_heal` | False | Enables Phase 3 healing via `HealingManager` |
| `automation_enabled` | None → client config | Phase 5 automation; `None` reads `client._config.automation.enabled` |
| `auto_create_holders` | True | Enables Phase 0 `HolderEnsurer`; set False to match pre-GAP-01 behavior |

### Known Gaps

1. **SCAR-008 regression test absent**: No isolated test for snapshot ordering at `session.py:995-1001`. Only `test_custom_field_persistence.py` covers the symptom indirectly.
2. **`PartialSaveError` catch sites partially traced**: `clients/task_operations.py` raises `SaveSessionError` wrapping `SaveResult`; route/service catch boundaries outside `persistence/` not fully mapped.
3. **Automation phase BROAD-CATCH too broad**: `except (ConnectionError, TimeoutError, OSError, RuntimeError, TypeError)` at `session.py:1028` — `TypeError` included to handle mock/plugin config issues (explicit comment). Any automation that raises `ValueError` or `AttributeError` would propagate and fail commit.
4. **`max_concurrent=15`** constructor parameter: documented as "Reserved for future optimization" — not enforced in current `BatchExecutor` implementation.

```metadata
domain: feat/save-session
source_hash: "8980bcd7"
generated_at: "2026-05-08T00:00Z"
confidence: 0.95
criteria_grades:
  purpose_and_design_rationale:
    grade: A
    pct: 95
    weight: 0.30
  conceptual_model:
    grade: A
    pct: 93
    weight: 0.25
  implementation_map:
    grade: A
    pct: 95
    weight: 0.25
  boundaries_and_failure_modes:
    grade: B
    pct: 88
    weight: 0.20
overall_grade: A
overall_pct: 93
notes: >
  Refreshed from source_hash c213958 (2026-04-01) to 8980bcd7 (2026-05-08).
  Key deltas: PERF-BUDGET-REGRESSION-001 (lock contention budget 1ms->2ms,
  commit f37802f2), architecture.md updated to note 20 files in persistence/
  (vs ~16 previously documented). session.py confirmed 1820 lines.
  Phase numbering clarified (6 phases including 1.5 cache invalidation).
  Error hierarchy expanded: SaveSessionError, GidValidationError added.
  PartialSaveError catch sites partially traced to clients/task_operations.py
  (5 sites) and models/task.py (1 site). ActionBuilder descriptor now confirmed
  in actions.py (gap from prior revision resolved).
  Remaining gaps: SCAR-008 regression test absent; automation BROAD-CATCH
  TypeError inclusion noted; max_concurrent=15 not enforced.
```
