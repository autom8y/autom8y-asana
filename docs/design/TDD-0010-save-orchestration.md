# TDD-0010: Save Orchestration Layer

## Metadata
- **TDD ID**: TDD-0010
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-10
- **Last Updated**: 2025-12-10
- **PRD Reference**: [PRD-0005](../requirements/PRD-0005-save-orchestration.md)
- **Related TDDs**:
  - [TDD-0005](TDD-0005-batch-api.md) - Batch API for Bulk Operations (BatchClient foundation)
  - [TDD-0001](TDD-0001-sdk-architecture.md) - SDK Architecture (foundation)
- **Related ADRs**:
  - [ADR-0035](../decisions/ADR-0035-unit-of-work-pattern.md) - Unit of Work Pattern for Save Orchestration
  - [ADR-0036](../decisions/ADR-0036-change-tracking-strategy.md) - Change Tracking via Snapshot Comparison
  - [ADR-0037](../decisions/ADR-0037-dependency-graph-algorithm.md) - Kahn's Algorithm for Dependency Ordering
  - [ADR-0038](../decisions/ADR-0038-save-concurrency-model.md) - Async-First Concurrency for Save Operations
  - [ADR-0039](../decisions/ADR-0039-batch-execution-strategy.md) - Fixed-Size Sequential Batch Execution
  - [ADR-0040](../decisions/ADR-0040-partial-failure-handling.md) - Commit and Report on Partial Failure
  - [ADR-0041](../decisions/ADR-0041-event-hook-system.md) - Synchronous Event Hooks with Async Support
  - [ADR-0002](../decisions/ADR-0002-sync-wrapper-strategy.md) - Sync/Async Wrapper Strategy
  - [ADR-0010](../decisions/ADR-0010-batch-chunking-strategy.md) - Sequential Chunk Execution

## Overview

This design introduces a Save Orchestration Layer for the autom8_asana SDK that implements the Unit of Work pattern for batched Asana API operations. The layer enables Django-ORM-style deferred saves where multiple model changes are collected and executed in optimized batches rather than immediately persisting each change. The architecture provides explicit entity registration via `SaveSession.track()`, snapshot-based dirty detection, dependency graph construction using Kahn's algorithm for topological sorting, automatic placeholder GID resolution, and partial failure handling with commit-and-report semantics. The design reuses the existing `BatchClient` infrastructure and follows the SDK's async-first pattern per ADR-0002.

## Requirements Summary

This design addresses [PRD-0005](../requirements/PRD-0005-save-orchestration.md) v1.0, which defines:

- **46 functional requirements** across Unit of Work (FR-UOW-*), Change Tracking (FR-CHANGE-*), Dependency Graph (FR-DEPEND-*), Batch Execution (FR-BATCH-*), Error Handling (FR-ERROR-*), Custom Fields (FR-FIELD-*), Event Hooks (FR-EVENT-*), and Dry Run (FR-DRY-*) domains
- **21 non-functional requirements** covering performance (NFR-PERF-*), compatibility (NFR-COMPAT-*), observability (NFR-OBSERVE-*), and reliability (NFR-REL-*)
- **Key constraints**: Opt-in tracking, snapshot comparison, commit-and-report on partial failure, Kahn's algorithm, fixed batch size of 10, async-first with sync wrappers

Key requirements driving this design:

| Requirement | Summary | Design Impact |
|-------------|---------|---------------|
| FR-UOW-001 | SaveSession as async context manager | SaveSession class with `__aenter__`, `__aexit__` |
| FR-UOW-002 | Explicit entity registration via `track()` | ChangeTracker with opt-in model |
| FR-CHANGE-001 | Dirty detection via `model_dump()` snapshot | ChangeTracker stores snapshots |
| FR-DEPEND-002 | Topological sort using Kahn's algorithm | DependencyGraph component |
| FR-BATCH-002 | Delegate to existing BatchClient | SavePipeline uses BatchClient |
| FR-ERROR-001 | Commit successful, report failures | Partial failure handling in SaveResult |

## System Context

The Save Orchestration Layer sits between SDK consumers and the existing BatchClient infrastructure, orchestrating multi-entity saves through dependency-aware batching.

```
+---------------------------------------------------------------------------+
|                              SYSTEM CONTEXT                                |
+---------------------------------------------------------------------------+

                            +------------------------+
                            |    SDK Consumers       |
                            |  (autom8, services)    |
                            +-----------+------------+
                                        |
                           async with SaveSession(client):
                               session.track(entity)
                               await session.commit()
                                        |
                                        v
+---------------------------------------------------------------------------+
|                         autom8_asana SDK                                   |
|                                                                            |
|  +----------------------------------------------------------------------+ |
|  |                    Save Orchestration Layer                          | |
|  |                                                                      | |
|  |  +----------------+  +----------------+  +----------------+          | |
|  |  |  SaveSession   |  | ChangeTracker  |  |DependencyGraph |          | |
|  |  | (entry point)  |  | (snapshots)    |  |  (Kahn's alg)  |          | |
|  |  +-------+--------+  +-------+--------+  +-------+--------+          | |
|  |          |                   |                   |                   | |
|  |          +-------------------+-------------------+                   | |
|  |                              |                                       | |
|  |                              v                                       | |
|  |              +---------------+---------------+                       | |
|  |              |         SavePipeline          |                       | |
|  |              | (validate->prepare->execute)  |                       | |
|  |              +---------------+---------------+                       | |
|  |                              |                                       | |
|  |                              v                                       | |
|  |              +---------------+---------------+                       | |
|  |              |        BatchExecutor          |                       | |
|  |              |  (chunk, delegate, correlate) |                       | |
|  |              +---------------+---------------+                       | |
|  |                              |                                       | |
|  +------------------------------+---------------------------------------+ |
|                                 |                                         |
|  +------------------------------+---------------------------------------+ |
|  |                              |                                       | |
|  |              +---------------+---------------+                       | |
|  |              |         BatchClient           |                       | |
|  |              |  (TDD-0005 implementation)    |                       | |
|  |              +---------------+---------------+                       | |
|  |                              |                                       | |
|  |                    Existing SDK Infrastructure                       | |
|  +----------------------------------------------------------------------+ |
|                                                                            |
+---------------------------------------------------------------------------+
                                        |
                                        v
                            +------------------------+
                            |    Infrastructure      |
                            |  (Asana Batch API)     |
                            +------------------------+
```

### Integration Points

| Integration Point | Interface | Direction | Notes |
|-------------------|-----------|-----------|-------|
| `AsanaResource` models | Pydantic model | Read/Write | Source entities; GID updated after create |
| `BatchClient` | SDK client | Write | Delegates batch execution |
| `BatchRequest` / `BatchResult` | Data classes | Read/Write | Request building and result parsing |
| `AsanaError` hierarchy | Exceptions | Read | Error classification and chaining |
| `sync_wrapper` | Decorator | Wrap | Sync API surface per ADR-0002 |

## Design

### Package Structure

```
src/autom8_asana/
+-- persistence/
|   +-- __init__.py              # Public exports: SaveSession, SaveResult, etc.
|   +-- session.py               # SaveSession class (Unit of Work entry point)
|   +-- tracker.py               # ChangeTracker class (snapshot storage, dirty detection)
|   +-- graph.py                 # DependencyGraph class (Kahn's algorithm)
|   +-- pipeline.py              # SavePipeline class (orchestration phases)
|   +-- executor.py              # BatchExecutor class (chunking, execution, correlation)
|   +-- events.py                # EventSystem and hook registration
|   +-- models.py                # SaveResult, PlannedOperation, SaveError, EntityState
|   +-- exceptions.py            # SaveOrchestrationError hierarchy
|
+-- ... (existing SDK structure)
```

### Component Architecture

```
+---------------------------------------------------------------------------+
|                        COMPONENT ARCHITECTURE                              |
+---------------------------------------------------------------------------+

+---------------------------------------------------------------------------+
|                              PUBLIC API                                    |
|                                                                            |
|    SaveSession (context manager)                                           |
|    +-- track(entity)           # Register entity for tracking             |
|    +-- untrack(entity)         # Remove entity from tracking              |
|    +-- delete(entity)          # Mark entity for deletion                 |
|    +-- get_changes(entity)     # Get field-level changes                  |
|    +-- get_state(entity)       # Get entity lifecycle state               |
|    +-- get_dependency_order()  # Get computed save order                  |
|    +-- preview()               # Dry run - returns PlannedOperation list  |
|    +-- commit_async()          # Execute all pending changes              |
|    +-- commit()                # Sync wrapper                             |
|                                                                            |
+---------------------------------+-----------------------------------------+
                                  |
                                  v
+---------------------------------------------------------------------------+
|                           INTERNAL COMPONENTS                              |
|                                                                            |
|  +------------------+    +------------------+    +------------------+      |
|  |  ChangeTracker   |    | DependencyGraph  |    |   EventSystem    |      |
|  |                  |    |                  |    |                  |      |
|  | - snapshots{}    |    | - adjacency{}    |    | - pre_save[]     |      |
|  | - states{}       |    | - in_degree{}    |    | - post_save[]    |      |
|  | - capture()      |    | - add_edge()     |    | - on_error[]     |      |
|  | - get_changes()  |    | - topological()  |    | - emit()         |      |
|  | - is_dirty()     |    | - get_levels()   |    |                  |      |
|  +--------+---------+    +--------+---------+    +--------+---------+      |
|           |                       |                       |                |
|           +-----------------------+-----------------------+                |
|                                   |                                        |
|                                   v                                        |
|                      +------------+------------+                           |
|                      |       SavePipeline      |                           |
|                      |                         |                           |
|                      | Phase 1: VALIDATE       |                           |
|                      |   - cycle detection     |                           |
|                      |   - required fields     |                           |
|                      |                         |                           |
|                      | Phase 2: PREPARE        |                           |
|                      |   - build requests      |                           |
|                      |   - assign temp GIDs    |                           |
|                      |                         |                           |
|                      | Phase 3: EXECUTE        |                           |
|                      |   - per-level batching  |                           |
|                      |   - delegate to executor|                           |
|                      |                         |                           |
|                      | Phase 4: CONFIRM        |                           |
|                      |   - resolve GIDs        |                           |
|                      |   - update entities     |                           |
|                      |   - clear dirty state   |                           |
|                      +------------+------------+                           |
|                                   |                                        |
|                                   v                                        |
|                      +------------+------------+                           |
|                      |     BatchExecutor       |                           |
|                      |                         |                           |
|                      | - chunk_operations()    |                           |
|                      | - execute_level()       |                           |
|                      | - correlate_results()   |                           |
|                      | - resolve_gids()        |                           |
|                      +------------+------------+                           |
|                                   |                                        |
+---------------------------------------------------------------------------+
                                    |
                                    v
                      +-------------+-------------+
                      |       BatchClient         |
                      |     (existing SDK)        |
                      +---------------------------+
```

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `SaveSession` | Unit of Work entry point; context manager; public API | `persistence/session.py` |
| `ChangeTracker` | Snapshot storage; dirty detection; state management | `persistence/tracker.py` |
| `DependencyGraph` | Graph construction; Kahn's algorithm; level grouping | `persistence/graph.py` |
| `SavePipeline` | Orchestration phases; validation; execution coordination | `persistence/pipeline.py` |
| `BatchExecutor` | Chunking; BatchClient delegation; result correlation | `persistence/executor.py` |
| `EventSystem` | Hook registration; event emission; async/sync handling | `persistence/events.py` |

### Data Model

#### Entity State Machine

```
                                +--------+
                                | (new)  |
                                +---+----+
                                    |
                     track() with no GID
                                    |
                                    v
+--------+      track()        +--------+
| (untracked) ---------------> |  NEW   |
+--------+                     +---+----+
    ^                              |
    |                         commit() succeeds
untrack()                          |
    |                              v
+---+----+                     +--------+
| CLEAN  | <------------------ | (saved)|
+---+----+   GID assigned      +--------+
    |
    | modify field
    |
    v
+--------+                     +--------+
|MODIFIED| ---- commit() ----> | CLEAN  |
+--------+                     +--------+
    |
    | delete()
    |
    v
+--------+                     +--------+
|DELETED | ---- commit() ----> |(removed)|
+--------+                     +--------+
```

#### Core Data Classes

```python
# autom8_asana/persistence/models.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


class EntityState(Enum):
    """Lifecycle state of a tracked entity.

    Per FR-UOW-008: Track entity lifecycle state.
    """
    NEW = "new"           # No GID or temp GID, will be created
    CLEAN = "clean"       # Tracked, unmodified since last save
    MODIFIED = "modified" # Has changes pending
    DELETED = "deleted"   # Marked for deletion


class OperationType(Enum):
    """Type of operation to perform.

    Per FR-BATCH-007: Build appropriate BatchRequest per type.
    """
    CREATE = "create"     # POST /tasks
    UPDATE = "update"     # PUT /tasks/{gid}
    DELETE = "delete"     # DELETE /tasks/{gid}


@dataclass(frozen=True)
class PlannedOperation:
    """A planned operation returned by preview().

    Per FR-DRY-002: Contains entity, operation type, and payload.
    """
    entity: "AsanaResource"
    operation: OperationType
    payload: dict[str, Any]
    dependency_level: int

    def __repr__(self) -> str:
        entity_repr = f"{type(self.entity).__name__}(gid={self.entity.gid})"
        return f"PlannedOperation({self.operation.value}, {entity_repr}, level={self.dependency_level})"


@dataclass
class SaveError:
    """Error information for a failed operation.

    Per FR-ERROR-003: Attribute errors to specific entities.
    """
    entity: "AsanaResource"
    operation: OperationType
    error: Exception
    payload: dict[str, Any]

    def __repr__(self) -> str:
        entity_repr = f"{type(self.entity).__name__}(gid={self.entity.gid})"
        return f"SaveError({self.operation.value}, {entity_repr}, {type(self.error).__name__})"


@dataclass
class SaveResult:
    """Result of a commit operation.

    Per FR-ERROR-002: Provides succeeded, failed, and aggregate info.
    """
    succeeded: list["AsanaResource"] = field(default_factory=list)
    failed: list[SaveError] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if all operations succeeded (FR-ERROR-002)."""
        return len(self.failed) == 0

    @property
    def partial(self) -> bool:
        """True if some but not all operations succeeded."""
        return len(self.succeeded) > 0 and len(self.failed) > 0

    @property
    def total_count(self) -> int:
        """Total number of operations attempted."""
        return len(self.succeeded) + len(self.failed)

    def raise_on_failure(self) -> None:
        """Raise PartialSaveError if any operations failed (FR-ERROR-010)."""
        if self.failed:
            from autom8_asana.persistence.exceptions import PartialSaveError
            raise PartialSaveError(self)

    def __repr__(self) -> str:
        return f"SaveResult(succeeded={len(self.succeeded)}, failed={len(self.failed)})"
```

#### Exception Hierarchy

```python
# autom8_asana/persistence/exceptions.py

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.exceptions import AsanaError

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.persistence.models import SaveResult


class SaveOrchestrationError(AsanaError):
    """Base exception for save orchestration errors.

    Per PRD Appendix B: All save-specific errors inherit from this.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class SessionClosedError(SaveOrchestrationError):
    """Raised when operating on a closed session.

    Per FR-UOW-006: Prevent re-use after commit or context exit.
    """

    def __init__(self) -> None:
        super().__init__(
            "Session is closed. Cannot perform operations on a closed session."
        )


class CyclicDependencyError(SaveOrchestrationError):
    """Raised when dependency graph contains cycles.

    Per FR-DEPEND-003: Clear message indicating cycle participants.
    """

    def __init__(self, cycle: list["AsanaResource"]) -> None:
        self.cycle = cycle
        entities = " -> ".join(
            f"{type(e).__name__}(gid={e.gid})" for e in cycle
        )
        super().__init__(f"Cyclic dependency detected: {entities}")


class DependencyResolutionError(SaveOrchestrationError):
    """Raised when a dependency cannot be resolved.

    Per FR-ERROR-006: Raised when dependent entity fails.
    """

    def __init__(
        self,
        entity: "AsanaResource",
        dependency: "AsanaResource",
        cause: Exception,
    ) -> None:
        self.entity = entity
        self.dependency = dependency
        self.__cause__ = cause
        super().__init__(
            f"Cannot save {type(entity).__name__}(gid={entity.gid}): "
            f"dependency {type(dependency).__name__}(gid={dependency.gid}) failed"
        )


class PartialSaveError(SaveOrchestrationError):
    """Raised when some operations in a commit fail.

    Per FR-ERROR-004: Contains SaveResult with full outcome.
    """

    def __init__(self, result: "SaveResult") -> None:
        self.result = result
        failed_count = len(result.failed)
        total = result.total_count
        super().__init__(
            f"Partial save: {failed_count}/{total} operations failed"
        )
```

### Interface Specifications

#### SaveSession

```python
# autom8_asana/persistence/session.py

from __future__ import annotations

from typing import Any, Callable, TypeVar, TYPE_CHECKING, Coroutine

from autom8_asana.persistence.tracker import ChangeTracker
from autom8_asana.persistence.graph import DependencyGraph
from autom8_asana.persistence.pipeline import SavePipeline
from autom8_asana.persistence.events import EventSystem
from autom8_asana.persistence.models import (
    EntityState,
    OperationType,
    PlannedOperation,
    SaveResult,
)
from autom8_asana.persistence.exceptions import SessionClosedError
from autom8_asana.transport.sync import sync_wrapper

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.base import AsanaResource

T = TypeVar("T", bound="AsanaResource")


class SessionState:
    """Internal state machine for SaveSession."""
    OPEN = "open"
    COMMITTED = "committed"
    CLOSED = "closed"


class SaveSession:
    """Unit of Work pattern for batched Asana operations.

    Per FR-UOW-001: Async context manager for bulk saves.
    Per FR-UOW-004: Sync wrapper per ADR-0002.

    Usage (async):
        async with SaveSession(client) as session:
            session.track(task)
            task.name = "Updated"
            result = await session.commit_async()

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

        Per FR-UOW-005: Accept optional configuration.

        Args:
            client: AsanaClient instance for API calls
            batch_size: Maximum operations per batch (default: 10, Asana limit)
            max_concurrent: Maximum concurrent batch requests (default: 15)
        """
        self._client = client
        self._batch_size = batch_size
        self._max_concurrent = max_concurrent

        self._tracker = ChangeTracker()
        self._graph = DependencyGraph()
        self._events = EventSystem()
        self._pipeline = SavePipeline(
            tracker=self._tracker,
            graph=self._graph,
            events=self._events,
            batch_client=client.batch,
            batch_size=batch_size,
        )

        self._state = SessionState.OPEN
        self._log = getattr(client, "_log", None)

    # --- Context Manager Protocol ---

    async def __aenter__(self) -> "SaveSession":
        """Enter async context (FR-UOW-001)."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context (FR-UOW-001)."""
        self._state = SessionState.CLOSED

    def __enter__(self) -> "SaveSession":
        """Enter sync context (FR-UOW-004)."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit sync context (FR-UOW-004)."""
        self._state = SessionState.CLOSED

    # --- Entity Registration ---

    def track(self, entity: T) -> T:
        """Register entity for change tracking.

        Per FR-UOW-002: Explicit opt-in tracking.
        Per FR-CHANGE-001: Capture snapshot at track time.

        Args:
            entity: AsanaResource instance to track

        Returns:
            The same entity (for chaining)

        Raises:
            SessionClosedError: If session is closed
        """
        self._ensure_open()
        self._tracker.track(entity)

        if self._log:
            self._log.debug(
                "session_track",
                entity_type=type(entity).__name__,
                entity_gid=entity.gid,
            )

        return entity

    def untrack(self, entity: "AsanaResource") -> None:
        """Remove entity from change tracking.

        Per FR-CHANGE-008: Support untracking.

        Args:
            entity: Previously tracked entity
        """
        self._ensure_open()
        self._tracker.untrack(entity)

    def delete(self, entity: "AsanaResource") -> None:
        """Mark entity for deletion.

        Per FR-CHANGE-004: Mark for DELETE operation.

        Args:
            entity: Entity to delete (must have GID)

        Raises:
            ValueError: If entity has no GID
            SessionClosedError: If session is closed
        """
        self._ensure_open()

        if not entity.gid or entity.gid.startswith("temp_"):
            raise ValueError(
                f"Cannot delete entity without GID: {type(entity).__name__}"
            )

        self._tracker.mark_deleted(entity)

        if self._log:
            self._log.debug(
                "session_delete",
                entity_type=type(entity).__name__,
                entity_gid=entity.gid,
            )

    # --- Change Inspection ---

    def get_changes(
        self,
        entity: "AsanaResource",
    ) -> dict[str, tuple[Any, Any]]:
        """Get field-level changes for tracked entity.

        Per FR-CHANGE-002: Compute {field: (old, new)} changes.

        Args:
            entity: Tracked entity

        Returns:
            Dict of {field_name: (old_value, new_value)}
        """
        return self._tracker.get_changes(entity)

    def get_state(self, entity: "AsanaResource") -> EntityState:
        """Get lifecycle state of tracked entity.

        Per FR-UOW-008: Track entity lifecycle state.

        Args:
            entity: Tracked entity

        Returns:
            Current EntityState
        """
        return self._tracker.get_state(entity)

    def get_dependency_order(self) -> list[list["AsanaResource"]]:
        """Get entities grouped by dependency level.

        Per FR-DEPEND-009: Inspect computed order.

        Returns:
            List of lists, where index is dependency level.
            Level 0 has no dependencies, level 1 depends on level 0, etc.
        """
        self._graph.build(self._tracker.get_dirty_entities())
        return self._graph.get_levels()

    # --- Dry Run ---

    def preview(self) -> list[PlannedOperation]:
        """Preview planned operations without executing.

        Per FR-DRY-001: Return PlannedOperation list, no API calls.
        Per FR-DRY-003: Include dependency order.
        Per FR-DRY-004: Validate (cycle detection).
        Per FR-DRY-005: Do not modify session state.

        Returns:
            List of PlannedOperation in execution order

        Raises:
            CyclicDependencyError: If dependency cycle detected
        """
        return self._pipeline.preview(self._tracker.get_dirty_entities())

    # --- Commit ---

    async def commit_async(self) -> SaveResult:
        """Execute all pending changes (async).

        Per FR-UOW-003: Execute pending changes.
        Per FR-UOW-007: Support multiple commits within session.
        Per FR-CHANGE-009: Reset entity state after successful save.

        Returns:
            SaveResult with succeeded/failed lists

        Raises:
            SessionClosedError: If session is closed
            CyclicDependencyError: If dependency cycle detected
        """
        self._ensure_open()

        dirty_entities = self._tracker.get_dirty_entities()

        if not dirty_entities:
            if self._log:
                self._log.debug("session_commit_empty")
            return SaveResult()

        if self._log:
            self._log.info(
                "session_commit_start",
                entity_count=len(dirty_entities),
            )

        result = await self._pipeline.execute(dirty_entities)

        # Reset state for successful entities (FR-CHANGE-009)
        for entity in result.succeeded:
            self._tracker.mark_clean(entity)

        if self._log:
            self._log.info(
                "session_commit_complete",
                succeeded=len(result.succeeded),
                failed=len(result.failed),
            )

        return result

    def commit(self) -> SaveResult:
        """Execute all pending changes (sync wrapper).

        Per FR-UOW-004: Sync wrapper per ADR-0002.
        """
        return self._commit_sync()

    @sync_wrapper("commit_async")
    async def _commit_sync(self) -> SaveResult:
        """Internal sync wrapper implementation."""
        return await self.commit_async()

    # --- Event Hooks ---

    def on_pre_save(
        self,
        func: Callable[["AsanaResource", OperationType], None]
            | Callable[["AsanaResource", OperationType], Coroutine[Any, Any, None]],
    ) -> Callable:
        """Decorator for pre-save hook.

        Per FR-EVENT-001: Hook called before each entity save.
        Per FR-EVENT-005: Support both function and coroutine hooks.

        Args:
            func: Hook function receiving (entity, operation_type)

        Returns:
            The decorated function
        """
        return self._events.register_pre_save(func)

    def on_post_save(
        self,
        func: Callable[["AsanaResource", OperationType, Any], None]
            | Callable[["AsanaResource", OperationType, Any], Coroutine[Any, Any, None]],
    ) -> Callable:
        """Decorator for post-save hook.

        Per FR-EVENT-002: Hook called after successful entity save.
        """
        return self._events.register_post_save(func)

    def on_error(
        self,
        func: Callable[["AsanaResource", OperationType, Exception], None]
            | Callable[["AsanaResource", OperationType, Exception], Coroutine[Any, Any, None]],
    ) -> Callable:
        """Decorator for error hook.

        Per FR-EVENT-003: Hook called when entity save fails.
        """
        return self._events.register_error(func)

    # --- Internal ---

    def _ensure_open(self) -> None:
        """Ensure session is still open for operations."""
        if self._state == SessionState.CLOSED:
            raise SessionClosedError()
```

#### ChangeTracker

```python
# autom8_asana/persistence/tracker.py

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from autom8_asana.persistence.models import EntityState

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


class ChangeTracker:
    """Tracks entity changes via snapshot comparison.

    Per ADR-0036: Snapshot-based dirty detection using model_dump().

    Responsibilities:
    - Store snapshots at track() time
    - Detect dirty entities by comparing current state to snapshot
    - Compute field-level change sets
    - Track entity lifecycle states
    """

    def __init__(self) -> None:
        # id(entity) -> snapshot dict
        self._snapshots: dict[int, dict[str, Any]] = {}
        # id(entity) -> EntityState
        self._states: dict[int, EntityState] = {}
        # id(entity) -> entity (for retrieval)
        self._entities: dict[int, "AsanaResource"] = {}

    def track(self, entity: "AsanaResource") -> None:
        """Register entity and capture snapshot.

        Per FR-CHANGE-001: Capture original state at track time.
        Per FR-CHANGE-003: Detect new entities by GID.
        Per NFR-REL-002: Re-tracking same entity is idempotent.
        """
        entity_id = id(entity)

        # Idempotent: if already tracked, don't re-capture
        if entity_id in self._entities:
            return

        self._entities[entity_id] = entity
        self._snapshots[entity_id] = entity.model_dump()

        # Determine initial state based on GID
        if not entity.gid or entity.gid.startswith("temp_"):
            self._states[entity_id] = EntityState.NEW
        else:
            self._states[entity_id] = EntityState.CLEAN

    def untrack(self, entity: "AsanaResource") -> None:
        """Remove entity from tracking.

        Per FR-CHANGE-008: Support untracking.
        """
        entity_id = id(entity)
        self._snapshots.pop(entity_id, None)
        self._states.pop(entity_id, None)
        self._entities.pop(entity_id, None)

    def mark_deleted(self, entity: "AsanaResource") -> None:
        """Mark entity for deletion.

        Per FR-CHANGE-004: Set state to DELETED.
        """
        entity_id = id(entity)

        # If not tracked, track it first
        if entity_id not in self._entities:
            self.track(entity)

        self._states[entity_id] = EntityState.DELETED

    def mark_clean(self, entity: "AsanaResource") -> None:
        """Mark entity as clean (unmodified) and update snapshot.

        Per FR-CHANGE-009: Reset state after successful save.
        """
        entity_id = id(entity)

        if entity_id in self._entities:
            # Update snapshot to current state
            self._snapshots[entity_id] = entity.model_dump()
            self._states[entity_id] = EntityState.CLEAN

    def get_state(self, entity: "AsanaResource") -> EntityState:
        """Get entity lifecycle state.

        Per FR-UOW-008: Track entity lifecycle state.
        """
        entity_id = id(entity)

        if entity_id not in self._states:
            raise ValueError(f"Entity not tracked: {type(entity).__name__}")

        state = self._states[entity_id]

        # CLEAN might have become MODIFIED
        if state == EntityState.CLEAN and self._is_modified(entity):
            return EntityState.MODIFIED

        return state

    def get_changes(
        self,
        entity: "AsanaResource",
    ) -> dict[str, tuple[Any, Any]]:
        """Compute field-level changes.

        Per FR-CHANGE-002: Return {field: (old, new)} dict.
        """
        entity_id = id(entity)

        if entity_id not in self._snapshots:
            return {}

        original = self._snapshots[entity_id]
        current = entity.model_dump()

        changes: dict[str, tuple[Any, Any]] = {}

        # Check all fields from both dicts
        all_keys = set(original.keys()) | set(current.keys())

        for key in all_keys:
            old_val = original.get(key)
            new_val = current.get(key)

            if old_val != new_val:
                changes[key] = (old_val, new_val)

        return changes

    def get_dirty_entities(self) -> list["AsanaResource"]:
        """Get all entities with pending changes.

        Per FR-CHANGE-005: Skip clean (unmodified) entities.

        Returns:
            List of entities that need to be saved (NEW, MODIFIED, DELETED)
        """
        dirty: list["AsanaResource"] = []

        for entity_id, entity in self._entities.items():
            state = self._states[entity_id]

            if state == EntityState.DELETED:
                dirty.append(entity)
            elif state == EntityState.NEW:
                dirty.append(entity)
            elif state == EntityState.CLEAN:
                # Check if actually modified
                if self._is_modified(entity):
                    dirty.append(entity)

        return dirty

    def get_changed_fields(
        self,
        entity: "AsanaResource",
    ) -> dict[str, Any]:
        """Get only the changed field values for minimal payload.

        Per FR-CHANGE-006: Generate minimal payloads.
        """
        changes = self.get_changes(entity)
        return {field: new_val for field, (old_val, new_val) in changes.items()}

    def _is_modified(self, entity: "AsanaResource") -> bool:
        """Check if entity has changes since snapshot."""
        entity_id = id(entity)

        if entity_id not in self._snapshots:
            return False

        original = self._snapshots[entity_id]
        current = entity.model_dump()

        return original != current
```

#### DependencyGraph

```python
# autom8_asana/persistence/graph.py

from __future__ import annotations

from collections import defaultdict, deque
from typing import TYPE_CHECKING

from autom8_asana.persistence.exceptions import CyclicDependencyError

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


class DependencyGraph:
    """Dependency graph with Kahn's algorithm for topological sort.

    Per ADR-0037: Use Kahn's algorithm for O(V+E) dependency ordering.

    Responsibilities:
    - Build graph from entity relationships (parent field)
    - Detect cycles before save
    - Produce topologically sorted levels for batch execution
    """

    def __init__(self) -> None:
        # gid -> entity
        self._entities: dict[str, "AsanaResource"] = {}
        # gid -> set of dependent gids (edges: dependency -> dependent)
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        # gid -> number of dependencies
        self._in_degree: dict[str, int] = defaultdict(int)

    def build(self, entities: list["AsanaResource"]) -> None:
        """Build dependency graph from entities.

        Per FR-DEPEND-001: Detect parent-child relationships from parent field.
        Per FR-DEPEND-005: Detect project-task dependencies (future).
        Per FR-DEPEND-006: Detect section-task dependencies (future).

        Args:
            entities: List of entities to include in graph
        """
        self._entities.clear()
        self._adjacency.clear()
        self._in_degree.clear()

        # Index entities by GID (including temp GIDs)
        for entity in entities:
            gid = self._get_gid(entity)
            self._entities[gid] = entity
            self._in_degree[gid] = 0

        # Build edges based on parent field
        for entity in entities:
            child_gid = self._get_gid(entity)

            # Check for parent dependency
            parent_ref = getattr(entity, "parent", None)
            if parent_ref is not None:
                parent_gid = self._resolve_parent_gid(parent_ref, entities)

                if parent_gid and parent_gid in self._entities:
                    # Edge: parent -> child (parent must be saved first)
                    self._adjacency[parent_gid].add(child_gid)
                    self._in_degree[child_gid] += 1

    def topological_sort(self) -> list["AsanaResource"]:
        """Perform topological sort using Kahn's algorithm.

        Per FR-DEPEND-002: Use Kahn's algorithm with O(V+E) complexity.
        Per FR-DEPEND-003: Raise CyclicDependencyError if cycle detected.

        Returns:
            Entities in dependency order (dependencies first)

        Raises:
            CyclicDependencyError: If graph contains cycles
        """
        # Copy in_degree for modification
        in_degree = dict(self._in_degree)

        # Start with nodes that have no dependencies
        queue = deque(
            gid for gid, degree in in_degree.items() if degree == 0
        )

        result: list["AsanaResource"] = []

        while queue:
            gid = queue.popleft()
            result.append(self._entities[gid])

            # Reduce in-degree of dependents
            for dependent_gid in self._adjacency.get(gid, []):
                in_degree[dependent_gid] -= 1
                if in_degree[dependent_gid] == 0:
                    queue.append(dependent_gid)

        # If not all nodes processed, there's a cycle
        if len(result) != len(self._entities):
            cycle = self._find_cycle(in_degree)
            raise CyclicDependencyError(cycle)

        return result

    def get_levels(self) -> list[list["AsanaResource"]]:
        """Get entities grouped by dependency level.

        Per FR-DEPEND-007: Group independent entities for parallel batching.
        Per FR-BATCH-001: Group operations by dependency level.

        Returns:
            List of lists where index is dependency level.
            Level 0 entities have no dependencies.
        """
        # Copy in_degree for modification
        in_degree = dict(self._in_degree)

        levels: list[list["AsanaResource"]] = []
        remaining = set(self._entities.keys())

        while remaining:
            # Find all nodes with in_degree 0 among remaining
            level_gids = [
                gid for gid in remaining
                if in_degree.get(gid, 0) == 0
            ]

            if not level_gids:
                # Cycle detected
                cycle = self._find_cycle(in_degree)
                raise CyclicDependencyError(cycle)

            # Add level
            levels.append([self._entities[gid] for gid in level_gids])

            # Remove from remaining and update in_degrees
            for gid in level_gids:
                remaining.discard(gid)
                for dependent_gid in self._adjacency.get(gid, []):
                    in_degree[dependent_gid] -= 1

        return levels

    def add_explicit_dependency(
        self,
        dependent: "AsanaResource",
        dependency: "AsanaResource",
    ) -> None:
        """Add explicit dependency between entities.

        Per FR-DEPEND-008: Support explicit dependency declaration.

        Args:
            dependent: Entity that depends on another
            dependency: Entity that must be saved first
        """
        dependent_gid = self._get_gid(dependent)
        dependency_gid = self._get_gid(dependency)

        if dependent_gid in self._entities and dependency_gid in self._entities:
            self._adjacency[dependency_gid].add(dependent_gid)
            self._in_degree[dependent_gid] += 1

    def _get_gid(self, entity: "AsanaResource") -> str:
        """Get or generate GID for entity."""
        if entity.gid:
            return entity.gid
        # Generate temporary GID for new entities
        return f"temp_{id(entity)}"

    def _resolve_parent_gid(
        self,
        parent_ref: Any,
        entities: list["AsanaResource"],
    ) -> str | None:
        """Resolve parent reference to GID.

        Parent can be:
        - String GID
        - NameGid object with .gid attribute
        - Another AsanaResource entity
        """
        if isinstance(parent_ref, str):
            return parent_ref

        if hasattr(parent_ref, "gid"):
            # Could be NameGid or AsanaResource
            gid = parent_ref.gid
            if gid:
                return gid
            # If no GID, check if it's a tracked entity
            for entity in entities:
                if entity is parent_ref:
                    return self._get_gid(entity)

        return None

    def _find_cycle(
        self,
        in_degree: dict[str, int],
    ) -> list["AsanaResource"]:
        """Find entities involved in a cycle for error reporting."""
        # Simple approach: return entities that couldn't be sorted
        cycle_gids = [gid for gid, deg in in_degree.items() if deg > 0]
        return [self._entities[gid] for gid in cycle_gids[:5]]  # Limit for message
```

#### SavePipeline

```python
# autom8_asana/persistence/pipeline.py

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from autom8_asana.persistence.models import (
    EntityState,
    OperationType,
    PlannedOperation,
    SaveResult,
    SaveError,
)
from autom8_asana.persistence.exceptions import DependencyResolutionError
from autom8_asana.persistence.executor import BatchExecutor

if TYPE_CHECKING:
    from autom8_asana.batch.client import BatchClient
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.persistence.tracker import ChangeTracker
    from autom8_asana.persistence.graph import DependencyGraph
    from autom8_asana.persistence.events import EventSystem


class SavePipeline:
    """Orchestrates the save operation through phases.

    Per TDD component design: Four-phase execution.

    Phases:
    1. VALIDATE: Cycle detection, required field validation
    2. PREPARE: Build BatchRequests, assign temp GIDs
    3. EXECUTE: Execute batches per dependency level
    4. CONFIRM: Resolve GIDs, update entities, clear dirty state
    """

    def __init__(
        self,
        tracker: "ChangeTracker",
        graph: "DependencyGraph",
        events: "EventSystem",
        batch_client: "BatchClient",
        batch_size: int = 10,
    ) -> None:
        self._tracker = tracker
        self._graph = graph
        self._events = events
        self._executor = BatchExecutor(batch_client, batch_size)

    def preview(
        self,
        entities: list["AsanaResource"],
    ) -> list[PlannedOperation]:
        """Preview operations without executing.

        Per FR-DRY-001 through FR-DRY-005.
        """
        if not entities:
            return []

        # Build graph and validate (raises CyclicDependencyError)
        self._graph.build(entities)
        levels = self._graph.get_levels()

        operations: list[PlannedOperation] = []

        for level_idx, level_entities in enumerate(levels):
            for entity in level_entities:
                op_type = self._determine_operation(entity)
                payload = self._build_payload(entity, op_type)

                operations.append(
                    PlannedOperation(
                        entity=entity,
                        operation=op_type,
                        payload=payload,
                        dependency_level=level_idx,
                    )
                )

        return operations

    async def execute(
        self,
        entities: list["AsanaResource"],
    ) -> SaveResult:
        """Execute all pending changes.

        Per FR-BATCH-001 through FR-BATCH-009.
        Per FR-ERROR-001: Commit successful, report failures.
        """
        if not entities:
            return SaveResult()

        # Phase 1: VALIDATE
        self._graph.build(entities)
        levels = self._graph.get_levels()

        # Track overall results
        all_succeeded: list["AsanaResource"] = []
        all_failed: list[SaveError] = []

        # Track GID resolutions for placeholder replacement
        gid_map: dict[str, str] = {}  # temp_xxx -> real_gid

        # Track failed dependencies for cascading errors
        failed_gids: set[str] = set()

        # Phase 2-4: Process each level
        for level_idx, level_entities in enumerate(levels):
            # Filter out entities whose dependencies failed
            executable: list["AsanaResource"] = []

            for entity in level_entities:
                parent_gid = self._get_parent_gid(entity)

                if parent_gid and parent_gid in failed_gids:
                    # Dependency failed - mark as cascading failure
                    parent_entity = self._find_entity_by_gid(
                        parent_gid, entities
                    )
                    error = DependencyResolutionError(
                        entity=entity,
                        dependency=parent_entity,
                        cause=Exception("Parent save failed"),
                    )
                    all_failed.append(
                        SaveError(
                            entity=entity,
                            operation=self._determine_operation(entity),
                            error=error,
                            payload={},
                        )
                    )
                    failed_gids.add(self._get_entity_gid(entity))
                else:
                    executable.append(entity)

            if not executable:
                continue

            # Phase 2: PREPARE operations for this level
            operations = self._prepare_operations(executable, gid_map)

            # Emit pre-save hooks
            for entity, op_type, _ in operations:
                await self._events.emit_pre_save(entity, op_type)

            # Phase 3: EXECUTE
            level_result = await self._executor.execute_level(operations)

            # Phase 4: CONFIRM - process results
            for entity, op_type, batch_result in level_result:
                if batch_result.success:
                    all_succeeded.append(entity)

                    # Update GID map for new entities
                    if op_type == OperationType.CREATE:
                        temp_gid = f"temp_{id(entity)}"
                        real_gid = batch_result.data.get("gid")
                        if real_gid:
                            gid_map[temp_gid] = real_gid
                            # Update entity GID
                            entity.gid = real_gid

                    # Emit post-save hook
                    await self._events.emit_post_save(
                        entity, op_type, batch_result.data
                    )
                else:
                    error = batch_result.error or Exception("Unknown error")
                    all_failed.append(
                        SaveError(
                            entity=entity,
                            operation=op_type,
                            error=error,
                            payload=batch_result.request_data or {},
                        )
                    )
                    failed_gids.add(self._get_entity_gid(entity))

                    # Emit error hook
                    await self._events.emit_error(entity, op_type, error)

        return SaveResult(succeeded=all_succeeded, failed=all_failed)

    def _determine_operation(
        self,
        entity: "AsanaResource",
    ) -> OperationType:
        """Determine operation type for entity."""
        state = self._tracker.get_state(entity)

        if state == EntityState.NEW:
            return OperationType.CREATE
        elif state == EntityState.DELETED:
            return OperationType.DELETE
        else:
            return OperationType.UPDATE

    def _build_payload(
        self,
        entity: "AsanaResource",
        op_type: OperationType,
    ) -> dict[str, Any]:
        """Build API payload for entity.

        Per FR-CHANGE-006: Generate minimal payloads for updates.
        """
        if op_type == OperationType.DELETE:
            return {}

        if op_type == OperationType.CREATE:
            # Full payload for creates
            data = entity.model_dump(exclude_none=True, exclude={"gid", "resource_type"})
            return data

        # For updates, only changed fields
        return self._tracker.get_changed_fields(entity)

    def _prepare_operations(
        self,
        entities: list["AsanaResource"],
        gid_map: dict[str, str],
    ) -> list[tuple["AsanaResource", OperationType, dict[str, Any]]]:
        """Prepare operations with GID resolution.

        Per FR-DEPEND-004: Resolve placeholder GIDs.
        """
        operations: list[tuple["AsanaResource", OperationType, dict[str, Any]]] = []

        for entity in entities:
            op_type = self._determine_operation(entity)
            payload = self._build_payload(entity, op_type)

            # Resolve parent GID if it was a temp GID
            if "parent" in payload:
                parent_ref = payload["parent"]
                if isinstance(parent_ref, str) and parent_ref.startswith("temp_"):
                    if parent_ref in gid_map:
                        payload["parent"] = gid_map[parent_ref]

            operations.append((entity, op_type, payload))

        return operations

    def _get_parent_gid(self, entity: "AsanaResource") -> str | None:
        """Get parent GID from entity."""
        parent = getattr(entity, "parent", None)
        if parent is None:
            return None
        if isinstance(parent, str):
            return parent
        if hasattr(parent, "gid"):
            return parent.gid
        return None

    def _get_entity_gid(self, entity: "AsanaResource") -> str:
        """Get GID or temp GID for entity."""
        if entity.gid and not entity.gid.startswith("temp_"):
            return entity.gid
        return f"temp_{id(entity)}"

    def _find_entity_by_gid(
        self,
        gid: str,
        entities: list["AsanaResource"],
    ) -> "AsanaResource":
        """Find entity by GID or temp GID."""
        for entity in entities:
            if entity.gid == gid:
                return entity
            if f"temp_{id(entity)}" == gid:
                return entity
        return entities[0]  # Fallback
```

#### BatchExecutor

```python
# autom8_asana/persistence/executor.py

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from autom8_asana.batch.models import BatchRequest, BatchResult
from autom8_asana.persistence.models import OperationType

if TYPE_CHECKING:
    from autom8_asana.batch.client import BatchClient
    from autom8_asana.models.base import AsanaResource


class BatchExecutor:
    """Executes batched operations via BatchClient.

    Per FR-BATCH-002: Delegate to existing BatchClient.
    Per FR-BATCH-003: Execute chunks sequentially per ADR-0010.
    Per FR-BATCH-006: Respect 10-action batch limit.

    Responsibilities:
    - Chunk operations into batches of 10
    - Build BatchRequest objects per operation type
    - Correlate BatchResult back to entities
    """

    def __init__(
        self,
        batch_client: "BatchClient",
        batch_size: int = 10,
    ) -> None:
        self._client = batch_client
        self._batch_size = batch_size

    async def execute_level(
        self,
        operations: list[tuple["AsanaResource", OperationType, dict[str, Any]]],
    ) -> list[tuple["AsanaResource", OperationType, BatchResult]]:
        """Execute all operations for a dependency level.

        Per FR-BATCH-004: Correlate responses to entities.
        Per FR-BATCH-005: Update entity GIDs after creation.

        Args:
            operations: List of (entity, operation_type, payload) tuples

        Returns:
            List of (entity, operation_type, batch_result) tuples
        """
        if not operations:
            return []

        # Build BatchRequests
        batch_requests: list[BatchRequest] = []
        request_map: list[tuple["AsanaResource", OperationType]] = []

        for entity, op_type, payload in operations:
            request = self._build_request(entity, op_type, payload)
            batch_requests.append(request)
            request_map.append((entity, op_type))

        # Execute via BatchClient (handles chunking per ADR-0010)
        batch_results = await self._client.execute_async(batch_requests)

        # Correlate results
        results: list[tuple["AsanaResource", OperationType, BatchResult]] = []

        for i, batch_result in enumerate(batch_results):
            entity, op_type = request_map[i]
            results.append((entity, op_type, batch_result))

        return results

    def _build_request(
        self,
        entity: "AsanaResource",
        op_type: OperationType,
        payload: dict[str, Any],
    ) -> BatchRequest:
        """Build BatchRequest for entity operation.

        Per FR-BATCH-007: Map operation types to HTTP methods.
        Per FR-BATCH-008: Include custom field values in payload.
        """
        resource_type = getattr(entity, "resource_type", "tasks") or "tasks"

        # Normalize resource type to API path
        resource_path = self._resource_to_path(resource_type)

        if op_type == OperationType.CREATE:
            return BatchRequest(
                relative_path=f"/{resource_path}",
                method="POST",
                data=payload,
            )
        elif op_type == OperationType.UPDATE:
            return BatchRequest(
                relative_path=f"/{resource_path}/{entity.gid}",
                method="PUT",
                data=payload,
            )
        else:  # DELETE
            return BatchRequest(
                relative_path=f"/{resource_path}/{entity.gid}",
                method="DELETE",
            )

    def _resource_to_path(self, resource_type: str) -> str:
        """Convert resource_type to API path."""
        # Handle common cases
        mapping = {
            "task": "tasks",
            "project": "projects",
            "section": "sections",
            "tag": "tags",
            "user": "users",
        }
        return mapping.get(resource_type.lower(), resource_type.lower() + "s")
```

#### EventSystem

```python
# autom8_asana/persistence/events.py

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, TYPE_CHECKING

from autom8_asana.persistence.models import OperationType

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


class EventSystem:
    """Event hook registration and emission.

    Per FR-EVENT-001 through FR-EVENT-005.
    Per ADR-0041: Synchronous event hooks with async support.

    Responsibilities:
    - Register pre_save, post_save, and error hooks
    - Support both sync functions and async coroutines
    - Invoke hooks at appropriate times during save pipeline
    """

    def __init__(self) -> None:
        self._pre_save_hooks: list[
            Callable[["AsanaResource", OperationType], None]
            | Callable[["AsanaResource", OperationType], Coroutine[Any, Any, None]]
        ] = []
        self._post_save_hooks: list[
            Callable[["AsanaResource", OperationType, Any], None]
            | Callable[["AsanaResource", OperationType, Any], Coroutine[Any, Any, None]]
        ] = []
        self._error_hooks: list[
            Callable[["AsanaResource", OperationType, Exception], None]
            | Callable[["AsanaResource", OperationType, Exception], Coroutine[Any, Any, None]]
        ] = []

    def register_pre_save(
        self,
        func: Callable[["AsanaResource", OperationType], None]
            | Callable[["AsanaResource", OperationType], Coroutine[Any, Any, None]],
    ) -> Callable:
        """Register pre-save hook.

        Per FR-EVENT-001: Hook can raise to abort save.
        Per FR-EVENT-004: Receives entity and operation context.
        """
        self._pre_save_hooks.append(func)
        return func

    def register_post_save(
        self,
        func: Callable[["AsanaResource", OperationType, Any], None]
            | Callable[["AsanaResource", OperationType, Any], Coroutine[Any, Any, None]],
    ) -> Callable:
        """Register post-save hook.

        Per FR-EVENT-002: Called after successful save with result.
        """
        self._post_save_hooks.append(func)
        return func

    def register_error(
        self,
        func: Callable[["AsanaResource", OperationType, Exception], None]
            | Callable[["AsanaResource", OperationType, Exception], Coroutine[Any, Any, None]],
    ) -> Callable:
        """Register error hook.

        Per FR-EVENT-003: Called when save fails.
        """
        self._error_hooks.append(func)
        return func

    async def emit_pre_save(
        self,
        entity: "AsanaResource",
        operation: OperationType,
    ) -> None:
        """Emit pre-save event to all registered hooks.

        Per FR-EVENT-005: Handle both sync and async hooks.
        """
        for hook in self._pre_save_hooks:
            result = hook(entity, operation)
            if asyncio.iscoroutine(result):
                await result

    async def emit_post_save(
        self,
        entity: "AsanaResource",
        operation: OperationType,
        data: Any,
    ) -> None:
        """Emit post-save event to all registered hooks."""
        for hook in self._post_save_hooks:
            try:
                result = hook(entity, operation, data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                # Post-save hooks should not fail the operation
                pass

    async def emit_error(
        self,
        entity: "AsanaResource",
        operation: OperationType,
        error: Exception,
    ) -> None:
        """Emit error event to all registered hooks."""
        for hook in self._error_hooks:
            try:
                result = hook(entity, operation, error)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                # Error hooks should not fail the operation
                pass
```

### Data Flow

#### Commit Flow Sequence

```
+---------------------------------------------------------------------------+
|                           COMMIT FLOW SEQUENCE                              |
+---------------------------------------------------------------------------+

  Client Code                                                       Asana API
       |                                                                |
       |  async with SaveSession(client) as session:                   |
       |      session.track(parent_task)                                |
       |      session.track(subtask)                                    |
       |      parent_task.name = "Updated"                              |
       |      await session.commit_async()                              |
       |                                                                |
       v                                                                |
  +----------+                                                          |
  |SaveSession|                                                         |
  +----+-----+                                                          |
       |                                                                |
       | 1. get_dirty_entities()                                        |
       v                                                                |
  +------------+                                                        |
  |ChangeTracker|                                                       |
  +-----+------+                                                        |
        |                                                               |
        | returns [parent_task, subtask]                                |
        v                                                               |
  +----------+                                                          |
  |SaveSession|                                                         |
  +----+-----+                                                          |
       |                                                                |
       | 2. pipeline.execute(entities)                                  |
       v                                                                |
  +------------+                                                        |
  |SavePipeline |                                                       |
  +-----+------+                                                        |
        |                                                               |
        | Phase 1: VALIDATE                                             |
        | 3. graph.build(entities)                                      |
        v                                                               |
  +---------------+                                                     |
  |DependencyGraph|                                                     |
  +-------+-------+                                                     |
          |                                                             |
          | Detects: subtask.parent = parent_task                       |
          | Builds: parent_task -> subtask edge                         |
          |                                                             |
          | 4. get_levels()                                             |
          | returns [[parent_task], [subtask]]                          |
          v                                                             |
  +------------+                                                        |
  |SavePipeline |                                                       |
  +-----+------+                                                        |
        |                                                               |
        | Phase 2-4: Per level                                          |
        |                                                               |
        | LEVEL 0: [parent_task]                                        |
        | 5. prepare_operations()                                       |
        | 6. executor.execute_level()                                   |
        v                                                               |
  +-------------+                                                       |
  |BatchExecutor|                                                       |
  +------+------+                                                       |
         |                                                              |
         | 7. build_request() -> BatchRequest(PUT /tasks/123)          |
         | 8. batch_client.execute_async()                              |
         v                                                              |
  +-----------+                                                         |
  |BatchClient |                                                        |
  +-----+-----+                                                         |
        |                                                               |
        | 9. POST /batch {actions: [{PUT /tasks/123, data}]}           |
        +-------------------------------------------------------------->|
        |                                                               |
        |<--------------------------------------------------------------+
        | 10. [{status: 200, body: {data: {gid: "123", ...}}}]         |
        v                                                               |
  +-------------+                                                       |
  |BatchExecutor|                                                       |
  +------+------+                                                       |
         |                                                              |
         | 11. correlate results                                        |
         v                                                              |
  +------------+                                                        |
  |SavePipeline |                                                       |
  +-----+------+                                                        |
        |                                                               |
        | LEVEL 1: [subtask]                                            |
        | 12. prepare_operations()                                      |
        | 13. resolve parent GID (if temp_xxx -> real GID)              |
        | 14. executor.execute_level()                                  |
        v                                                               |
  +-------------+                                                       |
  |BatchExecutor|                                                       |
  +------+------+                                                       |
         |                                                              |
         | 15. build_request() -> BatchRequest(POST /tasks)            |
         | 16. batch_client.execute_async()                             |
         +-------------------------------------------------------------->|
         |                                                              |
         |<--------------------------------------------------------------+
         | 17. [{status: 201, body: {data: {gid: "456", ...}}}]        |
         v                                                              |
  +------------+                                                        |
  |SavePipeline |                                                       |
  +-----+------+                                                        |
        |                                                               |
        | 18. Update subtask.gid = "456"                                |
        | 19. Build SaveResult(succeeded=[parent, subtask])             |
        v                                                               |
  +----------+                                                          |
  |SaveSession|                                                         |
  +----+-----+                                                          |
       |                                                                |
       | 20. tracker.mark_clean(parent_task)                            |
       | 21. tracker.mark_clean(subtask)                                |
       | 22. return SaveResult                                          |
       v                                                                |
  Client Code                                                           |
```

#### Placeholder GID Resolution Flow

```
+---------------------------------------------------------------------------+
|                    PLACEHOLDER GID RESOLUTION FLOW                         |
+---------------------------------------------------------------------------+

Initial State:
  parent_task = Task(gid=None, name="Parent")  # NEW
  subtask = Task(gid=None, parent=parent_task, name="Child")  # NEW

1. TRACK PHASE
   session.track(parent_task)
   --> temp_gid = "temp_1234567890"  (id(parent_task))
   --> ChangeTracker stores: {"temp_1234567890": parent_task}

   session.track(subtask)
   --> temp_gid = "temp_9876543210"  (id(subtask))
   --> ChangeTracker stores: {"temp_9876543210": subtask}

2. BUILD GRAPH
   DependencyGraph detects:
   --> subtask.parent = parent_task (object reference)
   --> Resolves to: subtask depends on temp_1234567890
   --> Edge: temp_1234567890 -> temp_9876543210

3. LEVEL 0 EXECUTION
   --> BatchRequest: POST /tasks {name: "Parent"}
   --> Response: {gid: "111222333", name: "Parent"}

   GID Map Updated:
   --> gid_map["temp_1234567890"] = "111222333"

   Entity Updated:
   --> parent_task.gid = "111222333"

4. LEVEL 1 PREPARATION
   Original subtask payload: {parent: "temp_1234567890", name: "Child"}

   GID Resolution:
   --> "temp_1234567890" found in gid_map
   --> Replaced with "111222333"

   Final payload: {parent: "111222333", name: "Child"}

5. LEVEL 1 EXECUTION
   --> BatchRequest: POST /tasks {parent: "111222333", name: "Child"}
   --> Response: {gid: "444555666", parent: {gid: "111222333"}}

   Entity Updated:
   --> subtask.gid = "444555666"

Final State:
  parent_task.gid = "111222333"
  subtask.gid = "444555666"
  subtask.parent correctly references parent
```

### Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Unit of Work pattern | SaveSession context manager | Familiar pattern, explicit scope, resource cleanup | [ADR-0035](../decisions/ADR-0035-unit-of-work-pattern.md) |
| Change tracking | Snapshot comparison via model_dump() | Simple, no model changes, works with existing Pydantic | [ADR-0036](../decisions/ADR-0036-change-tracking-strategy.md) |
| Dependency ordering | Kahn's algorithm | O(V+E), cycle detection, level grouping | [ADR-0037](../decisions/ADR-0037-dependency-graph-algorithm.md) |
| Concurrency model | Async-first with sync wrappers | Consistent with SDK pattern per ADR-0002 | [ADR-0038](../decisions/ADR-0038-save-concurrency-model.md) |
| Batch execution | Fixed 10, sequential chunks | Asana limit, per ADR-0010 | [ADR-0039](../decisions/ADR-0039-batch-execution-strategy.md) |
| Partial failure | Commit + Report | No rollback in Asana, preserve successful work | [ADR-0040](../decisions/ADR-0040-partial-failure-handling.md) |
| Event hooks | Sync-first with async support | Simple invocation, flexibility | [ADR-0041](../decisions/ADR-0041-event-hook-system.md) |

## Complexity Assessment

**Level**: SERVICE

**Justification**:

This feature adds significant complexity to the SDK but remains within the SERVICE level:

1. **Multiple interacting components**: SaveSession, ChangeTracker, DependencyGraph, SavePipeline, BatchExecutor, EventSystem
2. **State management complexity**: Entity lifecycle states, snapshot tracking, GID resolution
3. **Algorithm complexity**: Kahn's algorithm for topological sort, cycle detection
4. **Error handling complexity**: Partial failures, cascading dependency failures, error attribution
5. **Integration requirements**: BatchClient, Pydantic models, sync/async wrappers

**Not PLATFORM because**:
- Single SDK boundary (no multi-service orchestration)
- No infrastructure provisioning logic
- Batch execution delegated to existing BatchClient
- No deployment coordination required

## Implementation Plan

### Phase 1: Core Models and Exceptions (Session 4, ~2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `persistence/models.py` - EntityState, OperationType, PlannedOperation, SaveError, SaveResult | None | 1h |
| `persistence/exceptions.py` - Exception hierarchy | models.py | 0.5h |
| Unit tests for models and exceptions | Above | 0.5h |

**Exit Criteria**: All data classes pass mypy strict; unit tests cover serialization and edge cases.

### Phase 2: ChangeTracker (Session 4, ~2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `persistence/tracker.py` - ChangeTracker class | models.py | 1.5h |
| Unit tests for tracker | tracker.py | 0.5h |

**Exit Criteria**: Tracker correctly captures snapshots, detects dirty entities, computes changes.

### Phase 3: DependencyGraph (Session 4, ~2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `persistence/graph.py` - DependencyGraph with Kahn's algorithm | models.py | 1.5h |
| Unit tests for graph including cycle detection | graph.py | 0.5h |

**Exit Criteria**: Graph correctly builds from parent relationships; cycle detection works; levels grouped correctly.

### Phase 4: EventSystem (Session 4-5, ~1 hour)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `persistence/events.py` - EventSystem class | models.py | 0.5h |
| Unit tests for events | events.py | 0.5h |

**Exit Criteria**: Hooks registered and invoked correctly; async/sync both work.

### Phase 5: BatchExecutor (Session 5, ~2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `persistence/executor.py` - BatchExecutor class | models.py, BatchClient | 1.5h |
| Unit tests with mocked BatchClient | executor.py | 0.5h |

**Exit Criteria**: Requests built correctly; results correlated to entities.

### Phase 6: SavePipeline (Session 5, ~3 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `persistence/pipeline.py` - SavePipeline class | All internal components | 2h |
| Unit tests for pipeline phases | pipeline.py | 1h |

**Exit Criteria**: Four phases execute correctly; GID resolution works; partial failures handled.

### Phase 7: SaveSession (Session 5, ~2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `persistence/session.py` - SaveSession class | All components | 1.5h |
| `persistence/__init__.py` - Public exports | session.py | 0.25h |
| Unit tests for session | session.py | 0.25h |

**Exit Criteria**: Context manager works; public API complete; sync wrapper functions.

### Phase 8: Integration Testing (Session 5-6, ~4 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| End-to-end tests with mock BatchClient | All components | 2h |
| Edge case tests (cycles, cascading failures) | All components | 1h |
| Performance benchmarks | All components | 1h |

**Exit Criteria**: All integration tests pass; benchmarks meet NFR targets.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| R-001: Placeholder GID resolution edge cases | Medium | Medium | Comprehensive tests; explicit state machine; debug logging |
| R-002: Cycle detection misses complex cycles | High | Low | Use proven Kahn's algorithm; exhaustive cycle tests |
| R-003: Memory pressure from large snapshots | Medium | Low | Lazy snapshot creation; document batch size recommendations |
| R-004: Race conditions in concurrent tracking | High | Low | Document single-session usage; thread-safety tests |
| R-005: Hook exceptions abort saves incorrectly | Medium | Medium | Catch exceptions in post-save/error hooks; only pre-save can abort |
| R-006: Entity identity confusion (id() changes) | High | Low | Document object identity requirements; use GID where possible |

## Observability

### Metrics

All metrics emitted via SDK LogProvider:

| Metric | Type | Description |
|--------|------|-------------|
| `save_session_commit_count` | Counter | Number of commit operations |
| `save_session_commit_duration_ms` | Histogram | Time from commit start to complete |
| `save_session_entity_count` | Histogram | Entities per commit |
| `save_session_batch_count` | Histogram | Batches per commit |
| `save_session_success_rate` | Gauge | Percentage of entities succeeding |
| `save_session_dependency_depth` | Histogram | Maximum dependency tree depth |
| `save_session_cycle_errors` | Counter | Cyclic dependency errors detected |
| `save_session_partial_failures` | Counter | Commits with partial failures |

### Logging

| Level | Events |
|-------|--------|
| DEBUG | Entity tracked, entity state change, GID resolution, batch prepared |
| INFO | Session commit start, commit complete (with counts), preview executed |
| WARNING | Partial failure (with failure count), hook exception caught |
| ERROR | Cycle detected, dependency resolution failed, session closed error |

### Log Examples

```python
# DEBUG: Entity tracked
logger.debug(
    "session_track",
    entity_type="Task",
    entity_gid="temp_1234567890",
    initial_state="NEW",
)

# INFO: Commit start
logger.info(
    "session_commit_start",
    entity_count=15,
    new_count=10,
    modified_count=5,
    deleted_count=0,
)

# DEBUG: GID resolved
logger.debug(
    "gid_resolved",
    temp_gid="temp_1234567890",
    real_gid="111222333",
)

# INFO: Commit complete
logger.info(
    "session_commit_complete",
    succeeded=13,
    failed=2,
    duration_ms=1250,
    batch_count=2,
)

# WARNING: Partial failure
logger.warning(
    "session_partial_failure",
    succeeded=13,
    failed=2,
    failure_types=["NotFoundError", "ForbiddenError"],
)

# ERROR: Cycle detected
logger.error(
    "session_cycle_detected",
    cycle_entities=["Task(gid=123)", "Task(gid=456)"],
)
```

### Alerting Triggers

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Commit duration spike | p95 > 2x baseline for 5 min | Investigate batch execution |
| Partial failure rate | > 5% of commits for 15 min | Review error patterns |
| Cycle detection rate | > 1% of commits for 15 min | Audit dependency construction |
| Session closed errors | > 0 for 5 min | Review caller code patterns |

## Testing Strategy

### Unit Testing (Target: 90% coverage)

- **Models**: EntityState transitions, SaveResult properties, SaveError construction
- **Exceptions**: Exception messages, cause chaining
- **ChangeTracker**: Snapshot capture, dirty detection, state transitions
- **DependencyGraph**: Edge construction, Kahn's algorithm, cycle detection
- **EventSystem**: Hook registration, async/sync invocation
- **BatchExecutor**: Request building, result correlation
- **SavePipeline**: Phase execution, GID resolution, partial failure handling
- **SaveSession**: Context manager, public API, sync wrapper

### Integration Testing (Target: 80% coverage)

- **End-to-end flow**: Track -> Modify -> Commit -> Verify
- **Dependency ordering**: Parent-child hierarchy saves correctly
- **Partial failures**: Some entities fail, others succeed
- **Cascading failures**: Dependent entities fail when parent fails
- **Hook invocation**: Hooks called at correct times
- **GID resolution**: Placeholder GIDs resolved correctly

### Performance Testing

| Scenario | Target | Measurement |
|----------|--------|-------------|
| 10 independent entities | < 500ms | Time to SaveResult |
| 100 independent entities | < 2s | Time to SaveResult |
| 1000 independent entities | < 15s | Time to SaveResult |
| 3-level hierarchy (10 each) | < 1s | Time to SaveResult |
| Orchestration overhead per entity | < 10ms | Profile excluding API |
| Memory per 1000 tracked entities | < 50MB | Peak RSS |

### Security Testing

- No entity data in error messages (truncate/sanitize)
- No GIDs leaked in logs at INFO level
- Hook exceptions don't expose internal state

## Requirement Traceability

| Requirement Category | IDs | TDD Coverage |
|---------------------|-----|--------------|
| Unit of Work | FR-UOW-001 through FR-UOW-008 | SaveSession class, context manager, state machine |
| Change Tracking | FR-CHANGE-001 through FR-CHANGE-009 | ChangeTracker class, snapshot comparison |
| Dependency Graph | FR-DEPEND-001 through FR-DEPEND-009 | DependencyGraph class, Kahn's algorithm |
| Batch Execution | FR-BATCH-001 through FR-BATCH-009 | BatchExecutor class, SavePipeline integration |
| Error Handling | FR-ERROR-001 through FR-ERROR-010 | Exception hierarchy, SaveResult, partial failure |
| Custom Fields | FR-FIELD-001 through FR-FIELD-005 | Payload building in SavePipeline |
| Event Hooks | FR-EVENT-001 through FR-EVENT-005 | EventSystem class |
| Dry Run | FR-DRY-001 through FR-DRY-005 | SaveSession.preview(), SavePipeline.preview() |
| Performance | NFR-PERF-001 through NFR-PERF-008 | Implementation plan, performance testing |
| Compatibility | NFR-COMPAT-001 through NFR-COMPAT-006 | Async-first pattern, BatchClient reuse |
| Observability | NFR-OBSERVE-001 through NFR-OBSERVE-007 | Logging, metrics sections |
| Reliability | NFR-REL-001 through NFR-REL-005 | Thread safety, idempotent tracking |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Maximum recommended batch size before warning? | Engineer | Phase 8 | Document based on performance test results |
| Should preview() validate custom field GIDs? | Architect | Phase 6 | Yes, if resolver available; deferred otherwise |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-10 | Architect | Initial design with 6 components, 7 ADRs |
