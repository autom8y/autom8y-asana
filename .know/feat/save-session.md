---
domain: feat/save-session
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/persistence/**/*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# SaveSession Unit of Work Pattern

## Purpose and Design Rationale

`SaveSession` (`src/autom8_asana/persistence/session.py`) implements the Unit of Work pattern for Asana API writes. Callers register entity mutations inside a context manager, then commit in a single dependency-ordered, batch-optimized operation. The session manages ordering, GID resolution, partial failures, cache invalidation, and post-commit side effects.

Asana has no transaction API. Writing a composite entity requires sequenced POST/PUT/DELETE calls where later calls depend on GIDs returned by earlier ones. SaveSession internalizes all of this.

## Conceptual Model

### The Six Commit Phases

| Phase | What Happens | Key Component |
|-------|-------------|---------------|
| 0: ENSURE_HOLDERS | Missing holder subtasks detected and constructed | `HolderEnsurer`, `HolderConcurrencyManager` |
| 1: CRUD + ACTIONS | Topologically sorted operations via `BatchExecutor`, then actions via `ActionExecutor` | `SavePipeline`, `BatchExecutor` |
| 1.5: CACHE INVALIDATION | TASK, SUBTASKS, DETECTION + DataFrame cache invalidated | `CacheInvalidator` |
| 2: CASCADE | Field propagation from source to descendants | `CascadeExecutor` |
| 3: HEALING | Missing project memberships repaired | `HealingManager` |
| 5: AUTOMATION | Rule evaluation against `SaveResult` | `client.automation` |

### Temp GID Resolution Chain

New entities use `temp_xxx` GIDs. Resolution: `DependencyGraph` indexes temp GIDs -> `SavePipeline._prepare_operations()` resolves parent fields -> after CREATE, `object.__setattr__(entity, "gid", real_gid)` replaces temp.

## Implementation Map

20 files in `src/autom8_asana/persistence/`: session.py (~1650 lines), pipeline.py, tracker.py, graph.py (Kahn's topological sort), executor.py, action_executor.py, action_ordering.py, actions.py, models.py, exceptions.py, cascade.py, healing.py, cache_invalidator.py, holder_ensurer.py, holder_construction.py, holder_concurrency.py, validation.py, events.py, reorder.py (LIS-based), __init__.py.

### Key Defensive Patterns

- `threading.RLock()` on all state mutations (SCAR-010/010b fix)
- `_require_open()` context manager for TOCTOU-safe checks
- Snapshot before accessor clear ordering (SCAR-008/DEF-001 fix)
- BROAD-CATCH isolation on automation phase (NFR-003)
- Chunk-level fallback to sequential in action batch
- `HolderConcurrencyManager` asyncio.Lock prevents duplicate holder creation

## Boundaries and Failure Modes

- No rollback: partial failures leave successful operations committed
- No automatic commit on context exit: uncommitted changes silently discarded
- `UNSUPPORTED_FIELDS` (tags, projects, memberships, etc.) raise `UnsupportedOperationError`
- Exception hierarchy rooted at `SaveOrchestrationError`

### Active Scars

- **SCAR-008**: Snapshot ordering fix in `_update_post_commit_state()` -- no isolated regression test
- **SCAR-010/010b**: Thread safety via `RLock` + `_require_open()` context manager
- **TENSION-011/LB-004**: Temp GID two-phase resolution is a permanent architectural constraint

## Knowledge Gaps

1. **`actions.py` (ActionBuilder descriptor)** not fully read.
2. **`PartialSaveError` catch sites** at route/service boundaries not traced.
3. **SCAR-008 regression test gap** confirmed in scar-tissue.md.
