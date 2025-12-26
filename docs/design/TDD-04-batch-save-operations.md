# TDD-04: Batch & Save Operations

> Consolidated Technical Design Document covering Batch API and SaveSession orchestration.

## Metadata

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025-12-25 |
| **Consolidated From** | TDD-0005, TDD-0010, TDD-0022 |
| **Related ADRs** | ADR-0040, ADR-0041, ADR-0042 |
| **Complexity Level** | SERVICE |

---

## Overview

The Batch & Save Operations system provides two complementary capabilities for the autom8_asana SDK:

1. **Batch API** (TDD-0005): Low-level client for Asana's `/batch` endpoint with automatic chunking, sequential execution, and partial failure handling.

2. **SaveSession Orchestration** (TDD-0010): High-level Unit of Work pattern for Django-ORM-style deferred saves with dependency ordering, change tracking, and batched execution.

3. **SaveSession Reliability** (TDD-0022): GID-based entity identity, retryable error classification, and entity lookup capabilities.

These layers compose naturally: SaveSession uses BatchClient internally to execute committed changes, while BatchClient handles the HTTP-level concerns of chunking and result correlation.

```
+-----------------------------------------------------------------+
|                        User Code                                 |
+-----------------------------------------------------------------+
           |                                    |
           | SaveSession (Unit of Work)         | BatchClient (Direct)
           v                                    v
+-----------------------------------------------------------------+
|                     SaveSession Layer                            |
|  - Explicit track() registration                                 |
|  - Snapshot-based dirty detection                                |
|  - Dependency graph (Kahn's algorithm)                           |
|  - GID-based entity identity                                     |
+-----------------------------------------------------------------+
                              |
                              v
+-----------------------------------------------------------------+
|                     BatchClient Layer                            |
|  - Auto-chunking (10 actions per request)                        |
|  - Sequential chunk execution                                    |
|  - Result correlation and partial failure handling               |
+-----------------------------------------------------------------+
                              |
                              v
+-----------------------------------------------------------------+
|                     Asana /batch Endpoint                        |
+-----------------------------------------------------------------+
```

---

## Batch API Design

### Purpose

The BatchClient wraps Asana's `/batch` endpoint to enable efficient bulk operations. It handles:

- Automatic chunking to respect Asana's 10-action limit
- Sequential chunk execution for rate limit compliance
- Partial failure handling where individual failures don't fail the entire batch
- Result correlation preserving original request order

### Data Models

#### BatchRequest

Immutable model representing a single action in a batch:

```python
@dataclass(frozen=True)
class BatchRequest:
    """Single request within a batch operation.

    Attributes:
        relative_path: API path relative to base URL (e.g., "/tasks", "/tasks/123")
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Request body for POST/PUT operations
        options: Query parameters (e.g., opt_fields)
    """
    relative_path: str
    method: str
    data: dict[str, Any] | None = None
    options: dict[str, Any] | None = None

    def to_action_dict(self) -> dict[str, Any]:
        """Convert to Asana batch action format."""
        action = {
            "relative_path": self.relative_path,
            "method": self.method.upper(),
        }
        if self.data is not None:
            action["data"] = self.data
        if self.options is not None:
            action["options"] = self.options
        return action
```

#### BatchResult

Result of a single action within a batch:

```python
@dataclass(frozen=True)
class BatchResult:
    """Result of a single action within a batch operation.

    Attributes:
        status_code: HTTP status code returned for this action
        body: Response body (parsed JSON) or None
        headers: Response headers dict or None
        request_index: Original index of the request in the batch
    """
    status_code: int
    body: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    request_index: int = 0

    @property
    def success(self) -> bool:
        """Whether the action succeeded (2xx status code)."""
        return 200 <= self.status_code < 300

    @property
    def data(self) -> dict[str, Any] | None:
        """Extract the 'data' field from successful responses."""
        if not self.success or not self.body:
            return None
        if isinstance(self.body, dict) and "data" in self.body:
            return self.body["data"]
        return self.body
```

#### BatchSummary

Aggregate statistics for batch operations:

```python
@dataclass
class BatchSummary:
    """Summary statistics for a batch operation."""
    results: list[BatchResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.success)

    @property
    def all_succeeded(self) -> bool:
        return all(r.success for r in self.results)
```

### BatchClient Interface

```python
class BatchClient(BaseClient):
    """Client for Asana Batch API operations.

    Enables efficient bulk operations by batching multiple requests
    into single API calls with automatic chunking.
    """

    async def execute_async(
        self,
        requests: list[BatchRequest],
    ) -> list[BatchResult]:
        """Execute batch of requests with auto-chunking.

        Processes requests in chunks of 10 (Asana's limit), executing
        chunks sequentially to respect rate limits.

        Args:
            requests: List of BatchRequest objects to execute

        Returns:
            List of BatchResult objects, one per request, in order
        """
        ...

    async def create_tasks_async(
        self,
        tasks: list[dict[str, Any]],
        *,
        opt_fields: list[str] | None = None,
    ) -> list[BatchResult]:
        """Batch create multiple tasks."""
        ...

    async def update_tasks_async(
        self,
        updates: list[tuple[str, dict[str, Any]]],
        *,
        opt_fields: list[str] | None = None,
    ) -> list[BatchResult]:
        """Batch update multiple tasks."""
        ...
```

### Auto-Chunking Algorithm

Requests are split into chunks of 10 (Asana's limit) and executed sequentially:

```python
BATCH_SIZE_LIMIT = 10

def _chunk_requests(requests: list[BatchRequest]) -> list[list[BatchRequest]]:
    """Split requests into chunks of BATCH_SIZE_LIMIT."""
    if not requests:
        return []
    return [
        requests[i:i + BATCH_SIZE_LIMIT]
        for i in range(0, len(requests), BATCH_SIZE_LIMIT)
    ]
```

**Design Decisions:**
- Sequential execution (not parallel) for rate limit compliance
- Each chunk is a single HTTP request
- Results assembled in original request order
- Individual action failures don't fail the batch

---

## SaveSession Architecture

### Purpose

SaveSession implements the Unit of Work pattern for batched Asana API operations. It provides:

- Django-ORM-style deferred saves
- Explicit entity registration via `track()`
- Snapshot-based dirty detection
- Dependency graph construction and topological sorting
- Automatic placeholder GID resolution
- Partial failure handling with commit-and-report semantics

### Component Architecture

```
+-----------------------------------------------------------------+
|                         SaveSession                              |
|  - Entry point for Unit of Work pattern                          |
|  - Context manager (async with / with)                           |
|  - track(), untrack(), commit_async(), preview()                 |
+-----------------------------------------------------------------+
         |                    |                    |
         v                    v                    v
+----------------+   +----------------+   +------------------+
| ChangeTracker  |   |DependencyGraph |   |   SavePipeline   |
| - Snapshots    |   | - Kahn's algo  |   | - Validate       |
| - Dirty detect |   | - Cycle detect |   | - Prepare        |
| - GID identity |   | - Level group  |   | - Execute        |
+----------------+   +----------------+   +------------------+
                                                    |
                                                    v
                                          +------------------+
                                          |  BatchExecutor   |
                                          | - Chunk requests |
                                          | - Delegate batch |
                                          | - Correlate      |
                                          +------------------+
                                                    |
                                                    v
                                          +------------------+
                                          |   BatchClient    |
                                          | (from TDD-0005)  |
                                          +------------------+
```

### SaveSession Interface

```python
class SaveSession:
    """Unit of Work for batched Asana operations.

    Provides Django-ORM-style deferred saves where multiple model changes
    are collected and executed in optimized batches.

    Example:
        async with SaveSession(client) as session:
            session.track(task)
            task.name = "Updated"
            result = await session.commit_async()
    """

    async def __aenter__(self) -> "SaveSession":
        """Async context manager entry."""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        ...

    def track(self, entity: AsanaResource) -> None:
        """Register entity for change tracking.

        Captures snapshot at track time for later dirty detection.
        Uses GID-based identity for deduplication.
        """
        ...

    def untrack(self, entity: AsanaResource) -> None:
        """Remove entity from tracking."""
        ...

    async def commit_async(self) -> SaveResult:
        """Commit all tracked changes.

        1. Detect dirty entities via snapshot comparison
        2. Build dependency graph
        3. Topologically sort for correct save order
        4. Execute via BatchClient
        5. Return SaveResult with success/failure details
        """
        ...

    def preview(self) -> tuple[list[PlannedOperation], list[BatchAction]]:
        """Preview what would be committed without executing."""
        ...

    def find_by_gid(self, gid: str) -> AsanaResource | None:
        """Look up entity by GID (real or temp)."""
        ...

    def is_tracked(self, gid: str) -> bool:
        """Check if GID is currently tracked."""
        ...
```

### Change Tracking

ChangeTracker uses snapshot comparison for dirty detection:

```python
class ChangeTracker:
    """Tracks entity changes via snapshot comparison.

    Uses GID as primary key for identity, with fallback to __id_{id()}
    for entities without GIDs.
    """

    def __init__(self) -> None:
        self._entities: dict[str, AsanaResource] = {}
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._states: dict[str, EntityState] = {}
        self._gid_transitions: dict[str, str] = {}
        self._entity_to_key: dict[int, str] = {}

    def _get_key(self, entity: AsanaResource) -> str:
        """Generate tracking key for entity."""
        gid = getattr(entity, 'gid', None)
        if gid:
            return gid  # Works for both real and temp_ GIDs
        return f"__id_{id(entity)}"

    def track(self, entity: AsanaResource) -> None:
        """Register entity for change tracking."""
        key = self._get_key(entity)

        # Deduplicate by GID
        if key in self._entities:
            existing = self._entities[key]
            if existing is not entity:
                # Same GID, different object - update reference
                del self._entity_to_key[id(existing)]
            else:
                return  # Already tracked, idempotent

        self._entities[key] = entity
        self._entity_to_key[id(entity)] = key

        # Capture snapshot on first track
        if key not in self._snapshots:
            self._snapshots[key] = entity.model_dump()

        # Set initial state based on GID
        gid = entity.gid
        if not gid or gid.startswith("temp_"):
            self._states[key] = EntityState.NEW
        else:
            self._states[key] = EntityState.CLEAN

    def is_dirty(self, entity: AsanaResource) -> bool:
        """Check if entity has changed since tracking."""
        key = self._get_key(entity)
        return self._snapshots.get(key) != entity.model_dump()

    def get_changes(self, entity: AsanaResource) -> dict[str, tuple[Any, Any]]:
        """Get field-level changes for entity."""
        key = self._get_key(entity)
        original = self._snapshots.get(key, {})
        current = entity.model_dump()
        return {k: (original.get(k), current[k])
                for k in current if original.get(k) != current[k]}
```

### Dependency Graph

Uses Kahn's algorithm for topological sorting with O(V+E) complexity:

```python
class DependencyGraph:
    """Directed graph for dependency ordering.

    Uses Kahn's algorithm for topological sort with built-in
    cycle detection and level grouping.
    """

    def topological_sort(self) -> list[Entity]:
        """Sort entities in dependency order using Kahn's algorithm.

        Returns:
            Entities in save order (dependencies before dependents)

        Raises:
            CyclicDependencyError: If circular dependencies detected
        """
        in_degree = dict(self._in_degree)
        queue = deque(gid for gid, deg in in_degree.items() if deg == 0)
        result = []

        while queue:
            gid = queue.popleft()
            result.append(self._entities[gid])

            for dependent in self._adjacency[gid]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Cycle detection
        if len(result) != len(self._entities):
            remaining = set(self._entities.keys()) - set(e.gid for e in result)
            raise CyclicDependencyError(
                f"Circular dependency detected among: {remaining}"
            )

        return result

    def get_levels(self) -> list[list[Entity]]:
        """Group entities by dependency level for parallel execution.

        Returns:
            List of levels, where each level contains independent entities
        """
        ...
```

**Dependency Detection:**
- `task.parent` creates edge: parent -> task
- `task.projects` creates edge: project -> task (if project is new)
- `task.memberships` creates edge: section -> task (if section is new)

---

## Reliability Patterns

### GID-Based Entity Identity

Entities are identified by GID rather than Python object `id()`:

```python
def _get_key(self, entity: AsanaResource) -> str:
    """Generate tracking key for entity.

    Priority:
    1. Use entity's GID if it exists (works for real and temp_ GIDs)
    2. Fall back to f"__id_{id(entity)}" for truly GID-less entities
    """
    gid = getattr(entity, 'gid', None)
    if gid:
        return gid
    return f"__id_{id(entity)}"
```

**Benefits:**
- Same Asana resource tracked once regardless of Python object instances
- Eliminates duplicate operations and data loss from re-fetching
- Temp GIDs (`temp_*`) work seamlessly

**GID Transition on CREATE:**
```python
def update_gid(self, entity: AsanaResource, old_key: str, new_gid: str) -> None:
    """Re-key entity after temp GID becomes real GID."""
    if old_key not in self._entities:
        return

    # Transfer all state to new key
    self._entities[new_gid] = self._entities.pop(old_key)
    self._snapshots[new_gid] = self._snapshots.pop(old_key)
    self._states[new_gid] = self._states.pop(old_key)

    # Record transition for lookup
    self._gid_transitions[old_key] = new_gid
    self._entity_to_key[id(entity)] = new_gid
```

### Retryable Error Classification

SaveError provides `is_retryable` property based on HTTP status codes:

```python
@property
def is_retryable(self) -> bool:
    """Determine if this error is potentially retryable.

    Classification:
    - 429 (Rate Limit): Retryable after delay
    - 5xx (Server Error): Retryable (transient)
    - 4xx (Client Error): Not retryable (bad request)
    """
    status_code = self._extract_status_code()
    if status_code is None:
        return False

    if status_code == 429:
        return True
    if 500 <= status_code < 600:
        return True
    return False
```

**Error Classification Table:**

| HTTP Status | Retryable | Reason |
|-------------|-----------|--------|
| 400 Bad Request | No | Client error - payload invalid |
| 401 Unauthorized | No | Auth error - needs credential fix |
| 403 Forbidden | No | Permission error - needs access grant |
| 404 Not Found | No | Resource doesn't exist |
| **429 Too Many Requests** | **Yes** | Rate limit - retry after delay |
| **500 Internal Server Error** | **Yes** | Transient server error |
| **502 Bad Gateway** | **Yes** | Transient server error |
| **503 Service Unavailable** | **Yes** | Transient server error |

---

## Error Handling

### Partial Failure Philosophy

**Commit and Report:**
1. Successful operations are preserved (already committed to Asana)
2. Failed operations returned in `SaveResult.failed` with full context
3. Dependent entities marked as failed with `DependencyResolutionError`
4. No exception by default - caller decides handling strategy

**Why Not Rollback:**
- Asana has no transaction support
- No rollback capability for successful operations
- Partial progress is valuable (better than losing work)

### SaveResult Structure

```python
@dataclass
class SaveResult:
    succeeded: list[AsanaResource]
    failed: list[SaveError]
    action_results: list[ActionResult]

    @property
    def success(self) -> bool:
        """True if all operations succeeded."""
        return len(self.failed) == 0

    @property
    def partial(self) -> bool:
        """True if some succeeded and some failed."""
        return len(self.succeeded) > 0 and len(self.failed) > 0

    @property
    def failed_count(self) -> int:
        """Number of failed operations."""
        return len(self.failed)

    def get_failed_entities(self) -> list[AsanaResource]:
        """Get entities that failed to save."""
        return [error.entity for error in self.failed]

    def get_retryable_errors(self) -> list[SaveError]:
        """Get errors that may be retried."""
        return [error for error in self.failed if error.is_retryable]

    def raise_on_failure(self) -> None:
        """Raise PartialSaveError if any failures exist."""
        if not self.success:
            raise PartialSaveError(self)
```

### Error Handling Patterns

**Batch Operations (check result):**
```python
result = await session.commit_async()

if result.success:
    print(f"Saved {len(result.succeeded)} entities")
elif result.partial:
    print(f"{len(result.succeeded)} succeeded, {len(result.failed)} failed")
    for error in result.failed:
        print(f"  {error.entity.gid}: {error.error}")
else:
    print(f"All operations failed")

# Optional: raise if any failures
result.raise_on_failure()
```

**P1 Methods (single operations raise exceptions):**
```python
try:
    await task.save_async()
except SaveSessionError as e:
    print(f"Save failed: {e}")
    # Access SaveResult for details
    for error in e.save_result.failed:
        print(f"  {error.entity.gid}: {error.error}")
```

**Retry on Partial Failure:**
```python
result = await session.commit_async()
if not result.success:
    # Failed actions remain in pending queue
    pending = session.get_pending_actions()

    # Fix issues, then retry
    result2 = await session.commit_async()
```

### Selective Action Clearing

After commit, only successful actions are cleared:

```python
def _clear_successful_actions(self, action_results: list[ActionResult]) -> None:
    """Remove only successful actions from pending list.

    Failed actions remain for retry capability.
    """
    successful_identities = {
        (r.action.task.gid, r.action.action, r.action.target_gid)
        for r in action_results if r.success
    }

    self._pending_actions = [
        action for action in self._pending_actions
        if (action.task.gid, action.action, action.target_gid)
        not in successful_identities
    ]
```

---

## Testing Strategy

### Unit Testing (Target: 95% coverage)

**BatchClient Tests:**
- `BatchRequest` validation (invalid method, missing path)
- `BatchRequest.to_action_dict()` serialization
- `BatchResult.success`, `.error`, `.data` properties
- `BatchResult.from_asana_response()` parsing
- `BatchSummary` statistics
- `_chunk_requests()` edge cases (empty, exact multiple, remainder)

**SaveSession Tests:**
- Context manager lifecycle (`__aenter__`, `__aexit__`)
- Explicit tracking behavior (only tracked entities participate)
- Snapshot comparison accuracy (all field types detected)
- GID-based identity deduplication
- Temp GID transitions
- Dependency graph construction
- Topological sort with cycle detection

**Reliability Tests:**
- `is_retryable` for 429, 5xx, 4xx
- `find_by_gid()` real and temp GIDs
- Selective action clearing
- Error classification

### Integration Testing (Target: 90% coverage)

**Batch Operations:**
- Execute with mock HTTP returning success for all
- Execute with mock HTTP returning partial failures
- Execute with > 10 requests (verify chunking)
- Execute with empty list (return empty)

**SaveSession Operations:**
- Batch operations execute correctly
- Multiple sessions can coexist
- Resource cleanup on exceptions
- Dependency cascade failures attributed correctly
- Failed operations can be retried

### Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Empty request list | Return empty list immediately |
| Exactly 10 requests | Single chunk, no splitting |
| 11 requests | Two chunks: 10 + 1 |
| All actions fail | Return all results with errors |
| Batch endpoint 500 | Raise AsanaError (not BatchResult) |
| Same GID tracked twice | Update reference, preserve snapshot |
| Circular dependency | Raise CyclicDependencyError |
| Parent CREATE fails | Child marked as DependencyResolutionError |

---

## Cross-References

### Related ADRs

| ADR | Topic |
|-----|-------|
| ADR-0040 | SaveSession Unit of Work Pattern & Change Tracking |
| ADR-0041 | Dependency Ordering & Concurrency Model |
| ADR-0042 | Error Handling & Partial Failures |
| ADR-0043 | Action Operations Architecture |
| ADR-0044 | SaveSession Lifecycle Integration |
| ADR-0045 | SaveSession Decomposition |

### Related Documents

| Document | Description |
|----------|-------------|
| PRD-0005 | Save Orchestration Layer requirements |
| TDD-0005 | Batch API for Bulk Operations (source) |
| TDD-0010 | Save Orchestration Layer (source) |
| TDD-0022 | SaveSession Reliability (source) |

### Package Structure

```
autom8_asana/
  batch/
    __init__.py          # BatchClient, BatchRequest, BatchResult exports
    client.py            # BatchClient implementation
    models.py            # BatchRequest, BatchResult, BatchSummary

  persistence/
    __init__.py          # SaveSession, SaveResult exports
    session.py           # SaveSession implementation
    tracker.py           # ChangeTracker (snapshot, dirty detection)
    graph.py             # DependencyGraph (Kahn's algorithm)
    pipeline.py          # SavePipeline (validate, prepare, execute)
    executor.py          # BatchExecutor (delegates to BatchClient)
    models.py            # SaveResult, SaveError, EntityState
    events.py            # EventSystem (hooks)
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Tech Writer | Consolidated from TDD-0005, TDD-0010, TDD-0022 |
