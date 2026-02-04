# TDD: Cache Invalidation Pipeline for REST Mutations

**TDD ID**: TDD-CACHE-INVALIDATION-001
**Version**: 1.0
**Date**: 2026-02-04
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: Architectural Opportunities Initiative, Sprint 1
**Spike References**: S0-001 (Cache Baseline), S0-004 (Stale-Data Analysis)

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Goals and Non-Goals](#goals-and-non-goals)
4. [Proposed Architecture](#proposed-architecture)
5. [Component Design: MutationInvalidator](#component-design-mutationinvalidator)
6. [FastAPI Integration](#fastapi-integration)
7. [Invalidation Cascade](#invalidation-cascade)
8. [Section Membership Lookup](#section-membership-lookup)
9. [Fire-and-Forget Pattern](#fire-and-forget-pattern)
10. [Implementation Phases](#implementation-phases)
11. [Interface Contracts](#interface-contracts)
12. [Data Flow Diagrams](#data-flow-diagrams)
13. [Non-Functional Considerations](#non-functional-considerations)
14. [Test Strategy](#test-strategy)
15. [Risk Assessment](#risk-assessment)
16. [ADRs](#adrs)
17. [Success Criteria](#success-criteria)

---

## Overview

This TDD specifies a `MutationInvalidator` service that closes the critical cache invalidation gap identified in spike S0-004. Currently, **zero** REST mutation endpoints trigger cache invalidation. Only `SaveSession.commit_async()` invalidates via `CacheInvalidator`. This design extracts the invalidation logic into a shared service injectable into FastAPI route handlers, ensuring that REST mutations immediately trigger cache invalidation across all affected tiers.

### Solution Summary

| Component | Purpose |
|-----------|---------|
| `MutationInvalidator` | Shared service that accepts mutation events and triggers invalidation across cache tiers |
| `get_mutation_invalidator()` | FastAPI dependency that provides `MutationInvalidator` to route handlers |
| `MutationEvent` | Dataclass describing what was mutated (entity type, GID, operation, project context) |
| Fire-and-forget dispatch | `asyncio.create_task` wrapper that logs errors without blocking the HTTP response |

---

## Problem Statement

### Current State

Per spike S0-004, all 20 REST mutation endpoints (10 task, 5 project, 5 section) execute write-through to the Asana API but never touch any cache tier afterward. The stale-data window ranges from minutes (Redis TTL 300s) to hours (SWR grace 3x) to permanent (orphaned S3 entries).

The existing `CacheInvalidator` in `persistence/cache_invalidator.py` handles invalidation correctly but is tightly coupled to the `SaveSession` commit flow. It requires `SaveResult` and `ActionResult` objects that do not exist in the REST API path.

### Impact

| Scenario | Stale Window | User Impact |
|----------|-------------|-------------|
| Task update via REST | Up to 15 min (300s TTL + SWR) | Dashboard shows old task name/status |
| Task creation via REST | Until next cache warm (hours) | New task invisible to resolver/query |
| Section move via REST | Until next cache warm (hours) | Task appears in wrong section |
| Section rename via REST | Until next cache warm (hours) | DataFrame shows stale section name |

### Why Not Just Fix CacheInvalidator?

The existing `CacheInvalidator` is designed for batch commit flows. It expects `SaveResult` and `ActionResult` objects, iterates over `succeeded` entities, and looks up memberships from entity objects. REST handlers have none of this context -- they have a GID, an operation type, and possibly a project GID from the request body. A new service with a simpler interface is needed, while sharing the underlying invalidation primitives.

---

## Goals and Non-Goals

### Goals

| ID | Goal | Gap Addressed |
|----|------|---------------|
| G1 | Task mutations (T1-T10) invalidate TASK, SUBTASKS, DETECTION entries in TieredCacheProvider | S0-004 G1 |
| G2 | Task mutations with known project context invalidate per-task DataFrame entries | S0-004 G1 |
| G3 | Task creation (T1) invalidates section-level DataFrameCache for the target project | S0-004 G4 |
| G4 | Section move (T7) invalidates DataFrameCache for both source and destination sections | S0-004 G5 |
| G5 | Section mutations (S1-S4) invalidate DataFrameCache for the section's parent project | S0-004 G2 |
| G6 | Invalidation is fire-and-forget; mutation response latency is unaffected | NFR |
| G7 | Service is injectable via FastAPI `Depends()` | Integration |

### Non-Goals (Phase 2 / Deferred)

| ID | What | Why Defer |
|----|------|-----------|
| NG1 | Project mutations (P1-P5) triggering invalidation | S0-004 G3 is LOW severity; project deletion is rare |
| NG2 | SaveSession enhancement (G6: membership data gap) | Architectural change; requires entity load changes |
| NG3 | Webhook-driven invalidation from Asana | Requires external infrastructure (webhook receiver) |
| NG4 | Cache warming after creation (putting new task into cache) | Invalidation is sufficient; next read will populate |
| NG5 | SectionPersistence (S3 parquet) invalidation | Rebuilds are handled by cache warmer Lambda; Sprint 2 |
| NG6 | Cross-tier freshness unification | Relates to A2 opportunity; separate initiative |

---

## Proposed Architecture

### System Context

```
                    ┌─────────────────────────────────────────────────────┐
                    │                  MUTATION SOURCES                    │
                    ├─────────────────────────────────────────────────────┤
                    │                                                     │
                    │  REST API Routes                 SDK SaveSession    │
                    │  (tasks.py, sections.py)         (session.py)       │
                    │       │                               │             │
                    │       │ NEW: fire-and-forget          │ EXISTING    │
                    │       │                               │             │
                    │       ▼                               ▼             │
                    │  MutationInvalidator            CacheInvalidator    │
                    │  (NEW service)                  (UNCHANGED)         │
                    │       │                               │             │
                    │       └───────────┬───────────────────┘             │
                    │                   │                                 │
                    │                   ▼                                 │
                    │       Shared Invalidation Primitives                │
                    │       (CacheProvider.invalidate,                    │
                    │        invalidate_task_dataframes)                  │
                    │                   │                                 │
                    └───────────────────┼─────────────────────────────────┘
                                        │
                    ┌───────────────────┼─────────────────────────────────┐
                    │                   ▼                                 │
                    │       Cache Tiers                                   │
                    │       - TieredCacheProvider (Redis + S3)            │
                    │       - DataFrameCache (memory + S3)               │
                    │       - UnifiedTaskStore (in-memory)               │
                    └────────────────────────────────────────────────────┘
```

### Key Design Decision

The `MutationInvalidator` does NOT wrap or extend `CacheInvalidator`. Instead, both services call the same underlying primitives:

- `CacheProvider.invalidate(gid, [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION])`
- `invalidate_task_dataframes(task_gid, project_gids, cache)`
- `DataFrameCache.invalidate_project(project_gid, entity_type)` (new method)

This avoids coupling to `SaveResult`/`ActionResult` while ensuring both paths use identical invalidation logic. See ADR-001 below for the alternatives analysis.

---

## Component Design: MutationInvalidator

### MutationEvent Dataclass

```python
# src/autom8_asana/cache/mutation_event.py

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class MutationType(str, Enum):
    """Type of mutation operation."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"          # Section move (affects two sections)
    ADD_MEMBER = "add"     # Add to project/section
    REMOVE_MEMBER = "remove"  # Remove from project/section


class EntityKind(str, Enum):
    """Kind of entity being mutated."""
    TASK = "task"
    SECTION = "section"
    PROJECT = "project"  # Phase 2


@dataclass(frozen=True)
class MutationEvent:
    """Describes a mutation that requires cache invalidation.

    Attributes:
        entity_kind: What was mutated (task, section, project).
        entity_gid: GID of the mutated entity.
        mutation_type: What operation was performed.
        project_gids: Project contexts affected (if known from request).
        section_gid: Section context (for section moves, add-to-section).
        source_section_gid: Source section (for section moves only).
    """
    entity_kind: EntityKind
    entity_gid: str
    mutation_type: MutationType
    project_gids: list[str] = field(default_factory=list)
    section_gid: str | None = None
    source_section_gid: str | None = None
```

### MutationInvalidator Service

```python
# src/autom8_asana/cache/mutation_invalidator.py

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.cache.entry import EntryType
from autom8_asana.cache.mutation_event import (
    EntityKind,
    MutationEvent,
    MutationType,
)

if TYPE_CHECKING:
    from autom8_asana.cache.dataframe_cache import DataFrameCache
    from autom8_asana.protocols.cache import CacheProvider

logger = get_logger(__name__)

# Entry types invalidated for task mutations
_TASK_ENTRY_TYPES = [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]


class MutationInvalidator:
    """Cache invalidation service for REST mutation endpoints.

    Stateless service that accepts MutationEvents and triggers
    invalidation across the appropriate cache tiers. Designed
    for fire-and-forget usage from route handlers.

    Thread Safety: Stateless after init. Safe for concurrent use.

    Attributes:
        _cache: TieredCacheProvider for entity-level invalidation.
        _dataframe_cache: DataFrameCache for project-level DataFrame invalidation.
    """

    def __init__(
        self,
        cache_provider: CacheProvider,
        dataframe_cache: DataFrameCache | None = None,
    ) -> None:
        self._cache = cache_provider
        self._dataframe_cache = dataframe_cache

    async def invalidate_async(self, event: MutationEvent) -> None:
        """Invalidate all cache tiers affected by a mutation.

        This is the primary entry point. Route handlers call this
        via fire_and_forget() to avoid blocking the response.

        Args:
            event: Description of the mutation that occurred.
        """
        try:
            if event.entity_kind == EntityKind.TASK:
                await self._handle_task_mutation(event)
            elif event.entity_kind == EntityKind.SECTION:
                await self._handle_section_mutation(event)
            else:
                logger.warning(
                    "mutation_invalidator_unsupported_kind",
                    extra={"entity_kind": event.entity_kind.value},
                )
        except Exception as exc:
            # Never propagate -- this runs in a background task
            logger.error(
                "mutation_invalidation_failed",
                extra={
                    "entity_kind": event.entity_kind.value,
                    "entity_gid": event.entity_gid,
                    "mutation_type": event.mutation_type.value,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )

    def fire_and_forget(self, event: MutationEvent) -> None:
        """Schedule invalidation as a background task.

        Does not block. Errors are logged, never propagated.
        Safe to call from within a route handler.

        Args:
            event: Description of the mutation that occurred.
        """
        task = asyncio.create_task(
            self.invalidate_async(event),
            name=f"invalidate:{event.entity_kind.value}:{event.entity_gid}",
        )
        task.add_done_callback(_log_task_exception)

    # --- Private: Task Mutations ---

    async def _handle_task_mutation(self, event: MutationEvent) -> None:
        """Handle task-level cache invalidation.

        Steps:
        1. Invalidate entity cache (TASK, SUBTASKS, DETECTION)
        2. Invalidate per-task DataFrame entries (if project context known)
        3. For section moves: invalidate DataFrameCache for both sections
        """
        gid = event.entity_gid

        # Step 1: Entity cache invalidation
        self._invalidate_entity_entries(gid)

        # Step 2: Per-task DataFrame invalidation (task_gid:project_gid keys)
        if event.project_gids:
            self._invalidate_per_task_dataframes(gid, event.project_gids)

        # Step 3: Project-level DataFrameCache invalidation
        # For creates, moves, and membership changes, the project's full
        # DataFrame is affected (row count changes, not just row content)
        if event.mutation_type in (
            MutationType.CREATE,
            MutationType.MOVE,
            MutationType.ADD_MEMBER,
            MutationType.REMOVE_MEMBER,
        ):
            await self._invalidate_project_dataframes(event.project_gids)

        # Step 4: Section move -- also invalidate source section's project
        if event.mutation_type == MutationType.MOVE and event.source_section_gid:
            # Source section's project DataFrame is also stale
            # project_gids should already include both source and dest projects
            # This is handled by the route providing both project GIDs
            pass

        logger.debug(
            "mutation_invalidation_complete",
            extra={
                "entity_gid": gid,
                "mutation_type": event.mutation_type.value,
                "project_count": len(event.project_gids),
            },
        )

    # --- Private: Section Mutations ---

    async def _handle_section_mutation(self, event: MutationEvent) -> None:
        """Handle section-level cache invalidation.

        Section mutations affect:
        1. SECTION entry type in entity cache
        2. DataFrameCache for the section's parent project
        3. For add-task-to-section: also invalidate the task's entity cache
        """
        gid = event.entity_gid

        # Step 1: Section entity cache
        try:
            self._cache.invalidate(gid, [EntryType.SECTION])
        except Exception as exc:
            logger.warning(
                "section_cache_invalidation_failed",
                extra={"gid": gid, "error": str(exc)},
            )

        # Step 2: Project-level DataFrame invalidation
        if event.project_gids:
            await self._invalidate_project_dataframes(event.project_gids)

        # Step 3: If a task was added to this section, invalidate the task too
        if (
            event.mutation_type == MutationType.ADD_MEMBER
            and event.section_gid  # reused as "task_gid added to section"
        ):
            self._invalidate_entity_entries(event.section_gid)

        logger.debug(
            "section_invalidation_complete",
            extra={
                "section_gid": gid,
                "mutation_type": event.mutation_type.value,
                "project_count": len(event.project_gids),
            },
        )

    # --- Private: Invalidation Primitives ---

    def _invalidate_entity_entries(self, gid: str) -> None:
        """Invalidate TASK, SUBTASKS, DETECTION entries for a GID."""
        try:
            self._cache.invalidate(gid, _TASK_ENTRY_TYPES)
        except Exception as exc:
            logger.warning(
                "entity_cache_invalidation_failed",
                extra={"gid": gid, "error": str(exc)},
            )

    def _invalidate_per_task_dataframes(
        self, task_gid: str, project_gids: list[str]
    ) -> None:
        """Invalidate per-task DataFrame entries (task_gid:project_gid keys)."""
        from autom8_asana.cache.dataframes import invalidate_task_dataframes

        try:
            invalidate_task_dataframes(task_gid, project_gids, self._cache)
        except Exception as exc:
            logger.warning(
                "per_task_dataframe_invalidation_failed",
                extra={
                    "task_gid": task_gid,
                    "project_count": len(project_gids),
                    "error": str(exc),
                },
            )

    async def _invalidate_project_dataframes(
        self, project_gids: list[str]
    ) -> None:
        """Invalidate DataFrameCache for entire projects.

        When a task is created, moved, or removed from a project,
        the project's full DataFrame is affected and must be invalidated.
        """
        if not self._dataframe_cache:
            return

        for project_gid in project_gids:
            try:
                self._dataframe_cache.invalidate_project(project_gid)
            except Exception as exc:
                logger.warning(
                    "project_dataframe_invalidation_failed",
                    extra={"project_gid": project_gid, "error": str(exc)},
                )


def _log_task_exception(task: asyncio.Task) -> None:
    """Callback for fire-and-forget tasks. Logs unhandled exceptions."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error(
            "background_invalidation_exception",
            extra={
                "task_name": task.get_name(),
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        )
```

### DataFrameCache.invalidate_project (New Method)

A new method is needed on `DataFrameCache` to invalidate all cached DataFrames for a given project. The existing `DataFrameCache` in `cache/dataframe_cache.py` has per-entity-type storage. The new method iterates over all entity types and removes the project's entry from the memory tier.

```python
# Addition to DataFrameCache in cache/dataframe_cache.py

def invalidate_project(self, project_gid: str) -> None:
    """Invalidate all cached DataFrames for a project across entity types.

    Called when a structural change affects a project's DataFrame
    (task creation, deletion, section move, section create/delete).

    Args:
        project_gid: Project GID whose DataFrames should be invalidated.
    """
    for entity_type in self._caches:
        cache_key = f"{project_gid}:{entity_type}"
        if cache_key in self._memory_tier:
            del self._memory_tier[cache_key]
            self._stats[entity_type]["invalidations"] += 1
            logger.debug(
                "dataframe_cache_project_invalidated",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                },
            )
```

---

## FastAPI Integration

### Dependency Provider

```python
# src/autom8_asana/api/dependencies.py (additions)

from autom8_asana.cache.mutation_invalidator import MutationInvalidator


def get_mutation_invalidator(request: Request) -> MutationInvalidator:
    """Get the shared MutationInvalidator from app state.

    The MutationInvalidator is created once during app startup and
    stored on app.state. This dependency provides access to it.

    Args:
        request: FastAPI request (for app state access).

    Returns:
        MutationInvalidator instance, or a no-op instance if not initialized.
    """
    invalidator = getattr(request.app.state, "mutation_invalidator", None)
    if invalidator is None:
        # Graceful degradation: return a no-op invalidator
        # This happens during testing or when cache is disabled
        logger.warning("mutation_invalidator_not_initialized")
        return MutationInvalidator(cache_provider=_null_cache_provider())
    return invalidator


# Type alias for route signatures
MutationInvalidatorDep = Annotated[
    MutationInvalidator, Depends(get_mutation_invalidator)
]
```

### App Startup Registration

```python
# Addition to app startup in api/main.py

from autom8_asana.cache.mutation_invalidator import MutationInvalidator

# During app startup, after cache_provider and dataframe_cache are initialized:
app.state.mutation_invalidator = MutationInvalidator(
    cache_provider=cache_provider,
    dataframe_cache=dataframe_cache,
)
```

### Route Handler Wiring Pattern

Each mutation endpoint receives `MutationInvalidatorDep` as a parameter and calls `fire_and_forget()` after the Asana API call succeeds. The pattern is identical across all endpoints:

```python
# Example: tasks.py update_task with invalidation

@router.put("/{gid}", summary="Update a task")
async def update_task(
    gid: str,
    body: UpdateTaskRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    invalidator: MutationInvalidatorDep,  # NEW
) -> SuccessResponse[dict[str, Any]]:
    # ... existing validation ...
    task = await client.tasks.update_async(gid, raw=True, **kwargs)

    # Fire-and-forget: invalidate cache without blocking response
    invalidator.fire_and_forget(MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid=gid,
        mutation_type=MutationType.UPDATE,
        project_gids=_extract_project_gids(task),  # from response
    ))

    return build_success_response(data=task, request_id=request_id)
```

### Project GID Extraction

Many Asana API responses include the task's project memberships. When available, we extract project GIDs from the response to inform DataFrame invalidation. When not available (e.g., `delete_task` returns no body), we skip DataFrame invalidation for that request -- the next cache read will detect staleness via TTL.

```python
# src/autom8_asana/cache/mutation_event.py

def extract_project_gids(task_data: dict[str, Any] | None) -> list[str]:
    """Extract project GIDs from an Asana task response.

    Looks for project membership in standard Asana response fields:
    - task.projects[].gid (common in full task responses)
    - task.memberships[].project.gid (SaveSession entity format)

    Args:
        task_data: Task dict from Asana API response, or None.

    Returns:
        List of project GIDs (may be empty if not available).
    """
    if not task_data:
        return []

    gids: list[str] = []

    # Try projects array (Asana REST response format)
    projects = task_data.get("projects")
    if projects and isinstance(projects, list):
        for p in projects:
            if isinstance(p, dict) and p.get("gid"):
                gids.append(p["gid"])

    # Try memberships array (entity/SaveSession format)
    if not gids:
        memberships = task_data.get("memberships")
        if memberships and isinstance(memberships, list):
            for m in memberships:
                if isinstance(m, dict):
                    project = m.get("project", {})
                    if isinstance(project, dict) and project.get("gid"):
                        gids.append(project["gid"])

    return gids
```

---

## Invalidation Cascade

### Task Mutation Cascade

When a task is mutated via REST, the following cache tiers are affected:

```
Task Mutation (update/delete/tag/assignee)
    │
    ├── Tier 1: Entity Cache (TieredCacheProvider)
    │   └── invalidate(gid, [TASK, SUBTASKS, DETECTION])
    │       - Removes from Redis hot tier
    │       - Removes from S3 cold tier (if write-through active)
    │       - Next read will fetch fresh from Asana API
    │
    ├── Tier 2: Per-Task DataFrame (cache/dataframes.py)
    │   └── invalidate_task_dataframes(gid, project_gids, cache)
    │       - For each project_gid: invalidate("gid:project_gid", [DATAFRAME])
    │       - Only fires if project_gids are known from response
    │
    └── Tier 3: Project DataFrameCache (only for structural changes)
        └── DataFrameCache.invalidate_project(project_gid)
            - Only for: CREATE, DELETE, MOVE, ADD_MEMBER, REMOVE_MEMBER
            - Not for: UPDATE (row content changes, not row count)
            - Removes from memory tier
            - Next read triggers progressive rebuild
```

### Section Move Cascade

Section moves are the most complex invalidation because they affect two sections:

```
Move Task to Section (T7: POST /tasks/{gid}/section)
    │
    │  Request body: { section_gid, project_gid }
    │  Response: updated task data (includes new memberships)
    │
    ├── Entity Cache: invalidate task GID
    │
    ├── Per-Task DataFrame: invalidate for project_gid
    │
    └── Project DataFrameCache: invalidate project_gid
        - Both source and destination sections share the same project
        - One project-level invalidation covers both
        - If cross-project move: need both project_gids
```

### Section Mutation Cascade

```
Section Create/Update/Delete (S1-S3)
    │
    ├── Entity Cache: invalidate section GID (EntryType.SECTION)
    │
    └── Project DataFrameCache: invalidate parent project
        - Section create: new section not in cached DataFrame
        - Section rename: DataFrame rows have stale section name
        - Section delete: DataFrame rows reference nonexistent section

Add Task to Section (S4: POST /sections/{gid}/tasks)
    │
    ├── Entity Cache: invalidate task GID (task changed sections)
    │
    └── Project DataFrameCache: invalidate parent project
        - Task's section membership changed
```

---

## Section Membership Lookup

### The Problem

When a task is updated via `PUT /tasks/{gid}`, we need to know which projects the task belongs to in order to invalidate the correct DataFrames. The existing `CacheInvalidator` solves this by reading `entity.memberships` from the SaveSession entity. REST routes do not have this context.

### Strategy: Extract from API Response

Most Asana task mutation endpoints return the updated task object, which includes the `projects` array when requested. The Asana API response from `update_async()` typically includes basic fields including project membership.

**When project_gids are available** (from the API response):
- Extract via `extract_project_gids()` helper
- Pass to `MutationEvent.project_gids`
- Both entity cache and DataFrame cache are invalidated

**When project_gids are NOT available** (e.g., `delete_task` returns 204 No Content):
- Entity cache is still invalidated (requires only the GID)
- DataFrame invalidation is skipped for this request
- TTL expiry or next cache warm will eventually correct the DataFrame
- This is an acceptable trade-off: delete operations are less frequent, and the stale DataFrame entry will reference a deleted task (harmless for reads)

### Why Not a Reverse Index?

A persistent task-to-project reverse index was considered but rejected:

| Approach | Pros | Cons |
|----------|------|------|
| Extract from API response | Zero additional infrastructure; response already has the data | Not available for DELETE (204) |
| Reverse index in Redis | Always available; O(1) lookup | Must maintain consistency; new infrastructure; writes on every mutation |
| Query UnifiedTaskStore | No new infrastructure | Task may not be in cache; creates circular dependency |

The API response approach is chosen because it handles the common cases (update, create, move, add/remove) with zero additional infrastructure. The DELETE gap is acceptable. See ADR-002.

---

## Fire-and-Forget Pattern

### Design

Route handlers must not block on cache invalidation. The pattern uses `asyncio.create_task()` to schedule invalidation as a concurrent coroutine:

```python
def fire_and_forget(self, event: MutationEvent) -> None:
    task = asyncio.create_task(
        self.invalidate_async(event),
        name=f"invalidate:{event.entity_kind.value}:{event.entity_gid}",
    )
    task.add_done_callback(_log_task_exception)
```

### Error Handling

The `_log_task_exception` callback ensures exceptions from background tasks are always logged. The `invalidate_async` method itself wraps all operations in try/except with structured logging, so the callback is a safety net.

### Lifecycle Considerations

- Background tasks created with `create_task()` are tracked by the event loop and will complete even after the HTTP response is sent.
- During graceful shutdown, the ASGI server will wait for in-flight requests to complete. Background tasks created during request handling will also complete because they share the event loop.
- If the process is killed (SIGKILL), in-flight invalidation tasks are lost. This is acceptable because the cache will self-correct via TTL expiry.

### Concurrency Bounds

There is no explicit semaphore on invalidation tasks. Each invalidation is lightweight (Redis DEL operations + in-memory dict removals). If this becomes a concern under high mutation throughput, a bounded queue can be added in Phase 2.

---

## Implementation Phases

### Phase 1: Sprint 1 Scope

**Target**: Wire MutationInvalidator into the 14 highest-impact endpoints.

| Priority | Endpoint | Gap | MutationEvent |
|----------|----------|-----|---------------|
| P0 | `PUT /tasks/{gid}` (T2) | G1 | TASK, UPDATE, project_gids from response |
| P0 | `DELETE /tasks/{gid}` (T3) | G1 | TASK, DELETE, no project_gids |
| P0 | `POST /tasks` (T1) | G4 | TASK, CREATE, project_gids from request body |
| P0 | `POST /tasks/{gid}/section` (T7) | G5 | TASK, MOVE, project_gid from request body |
| P1 | `PUT /tasks/{gid}/assignee` (T8) | G1 | TASK, UPDATE, project_gids from response |
| P1 | `POST /tasks/{gid}/duplicate` (T4) | G1 | TASK, CREATE, project_gids from response |
| P1 | `POST /tasks/{gid}/tags` (T5) | G1 | TASK, UPDATE, project_gids from response |
| P1 | `DELETE /tasks/{gid}/tags/{tag}` (T6) | G1 | TASK, UPDATE, project_gids from response |
| P1 | `POST /tasks/{gid}/projects` (T9) | G1 | TASK, ADD_MEMBER, project_gid from body |
| P1 | `DELETE /tasks/{gid}/projects/{proj}` (T10) | G1 | TASK, REMOVE_MEMBER, project_gid from path |
| P2 | `POST /sections` (S1) | G2 | SECTION, CREATE, project_gid from body |
| P2 | `PUT /sections/{gid}` (S2) | G2 | SECTION, UPDATE, project_gid (lookup needed) |
| P2 | `DELETE /sections/{gid}` (S3) | G2 | SECTION, DELETE, project_gid (lookup needed) |
| P2 | `POST /sections/{gid}/tasks` (S4) | G2 | SECTION, ADD_MEMBER, task_gid from body |

### Phase 2: Sprint 2+ Scope (Deferred)

| Item | Description | Dependency |
|------|-------------|------------|
| Project mutations (P2, P3) | Invalidate DataFrameCache on project update/delete | Low severity per S0-004 |
| SaveSession enhancement | Ensure memberships in opt_fields for DataFrame invalidation | Entity load refactor |
| SectionPersistence invalidation | Invalidate S3 parquet files when section content changes | S3 lifecycle design |
| Bounded invalidation queue | Semaphore or queue for high-throughput mutation scenarios | Load testing results |
| Invalidation metrics | CloudWatch metrics for invalidation latency and failure rates | Metrics layer (A2) |

---

## Interface Contracts

### MutationInvalidator

```python
class MutationInvalidator:
    def __init__(
        self,
        cache_provider: CacheProvider,
        dataframe_cache: DataFrameCache | None = None,
    ) -> None: ...

    async def invalidate_async(self, event: MutationEvent) -> None: ...
    def fire_and_forget(self, event: MutationEvent) -> None: ...
```

### MutationEvent

```python
@dataclass(frozen=True)
class MutationEvent:
    entity_kind: EntityKind       # TASK or SECTION
    entity_gid: str               # GID of the mutated entity
    mutation_type: MutationType   # CREATE, UPDATE, DELETE, MOVE, ADD_MEMBER, REMOVE_MEMBER
    project_gids: list[str]       # Project contexts (may be empty)
    section_gid: str | None       # Section context (moves, add-to-section)
    source_section_gid: str | None  # Source section (moves only)
```

### FastAPI Dependency

```python
MutationInvalidatorDep = Annotated[
    MutationInvalidator, Depends(get_mutation_invalidator)
]
```

### DataFrameCache Extension

```python
# New method on DataFrameCache
def invalidate_project(self, project_gid: str) -> None: ...
```

---

## Data Flow Diagrams

### Sequence: Task Update with Invalidation

```
Client          Route Handler       Asana API      MutationInvalidator     Redis/Cache
  │                  │                  │                  │                    │
  │  PUT /tasks/123  │                  │                  │                    │
  │─────────────────>│                  │                  │                    │
  │                  │  update_async()  │                  │                    │
  │                  │─────────────────>│                  │                    │
  │                  │   task_data      │                  │                    │
  │                  │<─────────────────│                  │                    │
  │                  │                  │                  │                    │
  │                  │  fire_and_forget(event)             │                    │
  │                  │────────────────────────────────────>│                    │
  │                  │                  │                  │                    │
  │  200 OK (task)   │                  │    (async)       │                    │
  │<─────────────────│                  │                  │                    │
  │                  │                  │                  │  DEL task:123:task │
  │                  │                  │                  │───────────────────>│
  │                  │                  │                  │  DEL task:123:sub  │
  │                  │                  │                  │───────────────────>│
  │                  │                  │                  │  DEL df:123:proj1  │
  │                  │                  │                  │───────────────────>│
  │                  │                  │                  │                    │
```

### Sequence: Task Creation with DataFrameCache Invalidation

```
Client          Route Handler       Asana API      MutationInvalidator    DataFrameCache
  │                  │                  │                  │                    │
  │  POST /tasks     │                  │                  │                    │
  │  {projects:[P1]} │                  │                  │                    │
  │─────────────────>│                  │                  │                    │
  │                  │  create_async()  │                  │                    │
  │                  │─────────────────>│                  │                    │
  │                  │   new_task_data  │                  │                    │
  │                  │<─────────────────│                  │                    │
  │                  │                  │                  │                    │
  │                  │  fire_and_forget(CREATE, P1)        │                    │
  │                  │────────────────────────────────────>│                    │
  │                  │                  │                  │                    │
  │  201 Created     │                  │    (async)       │                    │
  │<─────────────────│                  │                  │                    │
  │                  │                  │                  │  invalidate_project│
  │                  │                  │                  │───────────────────>│
  │                  │                  │                  │  (remove P1 DFs)   │
  │                  │                  │                  │                    │
```

---

## Non-Functional Considerations

### Latency Impact on Mutation Responses

**Target**: Zero additional latency on the mutation response path.

`fire_and_forget()` adds only the overhead of `asyncio.create_task()` (microseconds). The actual invalidation runs concurrently after the response is sent. Verify with timing instrumentation in the route handler.

### Invalidation Latency (Background)

**Target**: <50ms for entity cache invalidation (Redis DEL), <100ms including DataFrame invalidation.

Entity invalidation is a synchronous `cache.invalidate()` call that translates to Redis DEL commands. DataFrame invalidation is in-memory dict removal. Both are sub-millisecond for typical workloads.

### Failure Modes

| Failure | Impact | Mitigation |
|---------|--------|------------|
| Redis unavailable | Entity cache not invalidated | TTL expiry self-corrects; structured warning logged |
| DataFrameCache not initialized | Project DataFrames not invalidated | Graceful degradation; `_dataframe_cache is None` check |
| Background task exception | Invalidation skipped for one event | `_log_task_exception` callback logs error; TTL self-corrects |
| Event loop shutdown mid-invalidation | In-flight invalidation lost | TTL self-corrects; acceptable given graceful shutdown path |

### Observability

All invalidation operations emit structured log events:

| Event | Level | Fields |
|-------|-------|--------|
| `mutation_invalidation_complete` | DEBUG | entity_gid, mutation_type, project_count |
| `mutation_invalidation_failed` | ERROR | entity_gid, mutation_type, error, error_type |
| `entity_cache_invalidation_failed` | WARNING | gid, error |
| `per_task_dataframe_invalidation_failed` | WARNING | task_gid, project_count, error |
| `project_dataframe_invalidation_failed` | WARNING | project_gid, error |
| `background_invalidation_exception` | ERROR | task_name, error, error_type |
| `mutation_invalidator_not_initialized` | WARNING | (none) |

---

## Test Strategy

### Unit Tests

**MutationInvalidator in isolation** using mock CacheProvider and mock DataFrameCache:

1. **Task update event**: Verify `cache.invalidate()` called with correct GID and `[TASK, SUBTASKS, DETECTION]` entry types.
2. **Task update with project context**: Verify `invalidate_task_dataframes()` called with correct task_gid and project_gids.
3. **Task create event**: Verify both entity invalidation AND project DataFrame invalidation fire.
4. **Task move event**: Verify entity invalidation + DataFrame invalidation for project_gids.
5. **Section create/update/delete**: Verify SECTION entry type invalidation + project DataFrame invalidation.
6. **Missing DataFrameCache**: Verify graceful degradation when `dataframe_cache=None`.
7. **Cache provider failure**: Verify exception is caught, logged, and does not propagate.
8. **fire_and_forget**: Verify `asyncio.create_task` is called and exception callback is attached.

### Integration Tests

**MutationInvalidator with InMemoryCacheProvider**:

1. **Round-trip**: Put a task entry in cache, fire an update event, verify the entry is gone.
2. **DataFrame round-trip**: Put a per-task DataFrame entry, fire an update event with project_gid, verify the DataFrame entry is gone.
3. **Project DataFrame round-trip**: Populate DataFrameCache memory tier, fire a create event, verify the project's DataFrame is invalidated.
4. **Fire-and-forget timing**: Verify the mutation response returns before invalidation completes (by adding artificial delay to mock invalidation).

### Route Handler Tests

**Test each wired endpoint** with a mock MutationInvalidator injected via dependency override:

1. Verify that `fire_and_forget()` is called after each successful mutation.
2. Verify the `MutationEvent` has the correct `entity_kind`, `mutation_type`, and `project_gids`.
3. Verify that mutation response is returned even if invalidator raises (it should not, but defensive).
4. Verify that failed mutations (4xx, 5xx from Asana) do NOT trigger invalidation.

### Test File Organization

```
tests/
  unit/
    cache/
      test_mutation_invalidator.py        # Unit tests for MutationInvalidator
      test_mutation_event.py              # Tests for MutationEvent and extract_project_gids
  integration/
    cache/
      test_mutation_invalidation_flow.py  # Round-trip with InMemoryCacheProvider
  api/
    routes/
      test_tasks_invalidation.py          # Route handler integration tests
      test_sections_invalidation.py       # Section route handler tests
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Project GIDs not in Asana response** for some endpoints | Medium | DataFrame invalidation skipped | TTL self-corrects; verify response format for each endpoint during implementation |
| **High mutation throughput overwhelms Redis** with DEL commands | Low | Backpressure on Redis | Invalidation is O(1) per GID; Redis handles ~100k ops/sec; monitor via existing Redis metrics |
| **DataFrameCache.invalidate_project not thread-safe** | Low | Race condition on memory tier | DataFrameCache operations are async-safe (single event loop); no threading concern |
| **Background task leak** during shutdown | Low | Tasks not completing | ASGI server waits for event loop drain; add shutdown hook if needed |
| **Behavioral change** for existing consumers | Low | Tests fail | MutationInvalidator is additive; no existing behavior changes |

---

## ADRs

### ADR-001: MutationInvalidator as Sibling Service, Not CacheInvalidator Extension

**Status**: Accepted

**Context**: Two approaches were considered for providing cache invalidation to REST routes:

| Option | Description |
|--------|-------------|
| A. Extend CacheInvalidator | Add a new method `invalidate_for_mutation(gid, entry_types, project_gids)` to the existing `CacheInvalidator` |
| B. New MutationInvalidator service | Create a parallel service with a REST-friendly interface |

**Decision**: Option B -- new `MutationInvalidator` service.

**Rationale**:
1. **Interface mismatch**: `CacheInvalidator` accepts `SaveResult` and `ActionResult` (batch commit domain objects). REST handlers have `(gid, operation, project_context)`. Extending CacheInvalidator would require either (a) a parallel method with a different signature, creating interface schizophrenia, or (b) adapter objects that fake SaveResult, which is misleading.
2. **Single Responsibility**: `CacheInvalidator` is responsible for "invalidation after SaveSession commits." `MutationInvalidator` is responsible for "invalidation after REST mutations." Different triggers, different contexts, same underlying primitives.
3. **Shared primitives**: Both services call `CacheProvider.invalidate()` and `invalidate_task_dataframes()`. The actual invalidation logic is already factored into these primitive functions. The service layer is just routing.
4. **Independent evolution**: REST invalidation may need features that SaveSession does not (e.g., bounded queue, rate limiting, different entity types). Keeping them separate allows each to evolve independently.

**Consequences**:
- Two invalidation "entry points" to maintain (but shared primitives)
- If a new cache tier is added, both services need updating (mitigated by primitive functions being the single source of truth)

---

### ADR-002: Project GIDs from API Response, Not Reverse Index

**Status**: Accepted

**Context**: To invalidate per-task DataFrame entries, we need the project GIDs that contain the task. Three strategies were evaluated:

| Option | Description | Additional Infrastructure | Coverage |
|--------|-------------|--------------------------|----------|
| A. API response extraction | Parse project_gids from Asana API response body | None | All mutations except DELETE (204) |
| B. Redis reverse index | Maintain task_gid -> project_gids mapping in Redis | Redis hash/set + write path changes | 100% coverage |
| C. Cache lookup | Query UnifiedTaskStore for task's project memberships | None | Only if task is cached |

**Decision**: Option A -- extract from API response.

**Rationale**:
1. **Zero infrastructure**: No new Redis data structures, no write path changes, no consistency concerns.
2. **High coverage**: 9 of 10 task endpoints return task data with project membership. Only `DELETE` returns 204.
3. **DELETE gap is acceptable**: When a task is deleted, the stale DataFrame entry references a non-existent task. This is harmless -- the next DataFrame rebuild will exclude it. The entity cache entry IS invalidated (only needs GID).
4. **Simplicity**: The API response is already in hand. Parsing it is a pure function with no external dependencies.

**Consequences**:
- DELETE mutations skip DataFrame invalidation (acceptable per analysis above)
- If Asana API changes response format, `extract_project_gids()` must be updated
- Section endpoints (S2 update, S3 delete) need the parent project_gid; for S1 (create) it is in the request body, for S2/S3 it requires either the response or a separate lookup

---

### ADR-003: Fire-and-Forget via asyncio.create_task

**Status**: Accepted

**Context**: Invalidation must not block the mutation response. Options considered:

| Option | Description | Complexity |
|--------|-------------|------------|
| A. asyncio.create_task | Schedule as concurrent coroutine on the event loop | Low |
| B. Background worker queue | Push to asyncio.Queue, drain in background worker | Medium |
| C. External queue (SQS/Redis) | Push to external queue, Lambda/worker processes | High |

**Decision**: Option A -- `asyncio.create_task`.

**Rationale**:
1. **Simplest viable approach**: Invalidation is fast (<100ms). No queuing overhead needed.
2. **Same process**: No network hop, no serialization, no infrastructure.
3. **Natural lifecycle**: Task completes when the event loop processes it. ASGI server handles graceful shutdown.
4. **Upgradeable**: If load testing reveals need for backpressure, Option B can be retrofitted by adding a semaphore or queue inside `MutationInvalidator` without changing the caller interface.

**Consequences**:
- No backpressure under extreme mutation throughput (mitigated: Redis DEL is O(1))
- Background task exceptions require explicit handling (mitigated: done callback + try/except)
- No persistence of invalidation intent (mitigated: TTL self-corrects on miss)

---

## Success Criteria

| Criteria | Measurement | Target |
|----------|-------------|--------|
| Entity cache invalidated on task mutation | Unit test + integration test | All 10 task endpoints trigger invalidation |
| DataFrame cache invalidated when project context known | Unit test | project_gids extracted and passed for 9/10 endpoints |
| DataFrameCache invalidated on structural changes | Integration test | create, move, add/remove trigger project invalidation |
| Section mutations invalidate project DataFrames | Unit test | All 4 section endpoints trigger project invalidation |
| Mutation response latency unchanged | Timing comparison | <1ms added to p99 response time |
| Graceful degradation on cache failure | Unit test | Exceptions logged, response unaffected |
| Fire-and-forget correctly async | Integration test | Response sent before invalidation completes |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD-CACHE-INVALIDATION-001 | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-cache-invalidation-pipeline.md` | Yes (this document) |
| Spike S0-004 (input) | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/spike-S0-004-stale-data-analysis.md` | Read |
| Spike S0-001 (input) | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/spike-S0-001-cache-baseline.md` | Read |
| CacheInvalidator (existing) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/cache_invalidator.py` | Read |
| UnifiedTaskStore (existing) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py` | Read |
| cache/dataframes.py (existing) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframes.py` | Read |
| cache/entry.py (existing) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/entry.py` | Read |
| tasks.py routes (existing) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/tasks.py` | Read |
| sections.py routes (existing) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/sections.py` | Read |
| projects.py routes (existing) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/projects.py` | Read |
| dependencies.py (existing) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/dependencies.py` | Read |
