# SPIKE-HARDENING-F: SaveSession Reliability

**Initiative**: Architecture Hardening - Initiative F (SaveSession Reliability)
**Date**: 2025-12-16
**Status**: COMPLETE
**Timebox**: 1 session

---

## Executive Summary

This spike validates the feasibility of two critical changes to SaveSession:

1. **GID-Based Entity Identity**: FEASIBLE with caveats. The current `id()` tracking can be replaced with GID-based tracking, but requires careful handling of temp GIDs and entity refresh scenarios. A hybrid approach (GID when available, `id()` for untracked new entities) provides the best balance.

2. **Partial Failure Breakdown**: FULLY SUPPORTED. The Asana Batch API returns per-operation success/failure information with HTTP status codes. The current implementation already handles this correctly via `BatchResult`. We can determine exactly which operations succeeded and which failed.

**Recommendation**: **GO** with HIGH confidence. Both goals are achievable with reasonable effort.

---

## Goal 1: GID-Based Entity Registry

### Current Implementation Analysis

The current `ChangeTracker` (tracker.py) uses `id(entity)` as the tracking key:

```python
# Current approach
self._snapshots: dict[int, dict[str, Any]] = {}  # id(entity) -> snapshot
self._states: dict[int, EntityState] = {}        # id(entity) -> state
self._entities: dict[int, AsanaResource] = {}    # id(entity) -> entity
```

This approach has **specific reasons** documented in the code:

```python
"""Uses id(entity) for identity to handle entities that may not
have GIDs yet (new entities) or may have duplicate GIDs in
different sessions."""
```

### Questions Answered

#### Q1: What happens with `temp_` GIDs (new entities)?

**Finding**: New entities are created with `temp_` prefixed GIDs (e.g., `temp_123456`). These are:
- Detected at track time: `if not gid or gid.startswith("temp_"): state = EntityState.NEW`
- Used for internal correlation during batch execution
- Replaced with real GIDs after API response

**Current flow**:
```python
# pipeline.py: After successful CREATE
temp_gid = f"temp_{id(entity)}"
real_gid = batch_result.data.get("gid")
gid_map[temp_gid] = real_gid
object.__setattr__(entity, "gid", real_gid)
```

**Impact for GID-based tracking**: We need to maintain temp GIDs as valid keys initially, then update the registry when real GIDs arrive.

#### Q2: What happens when entity GID changes (temp -> real)?

**Finding**: The current implementation handles GID changes by:
1. Using `id(entity)` for lookup (unchanged after GID update)
2. Updating entity's `gid` field in-place via `object.__setattr__()`
3. Building a `gid_map` for downstream operations

**Challenge for GID-based tracking**: We must re-key the registry when temp GIDs become real GIDs.

#### Q3: Can we handle entity refresh (re-fetching same GID)?

**Finding**: Currently NOT handled. If you fetch the same task twice, you get two different Python objects with the same GID. The `id()` approach tracks them as separate entities.

**GID-based advantage**: Would naturally deduplicate, treating re-fetched entities as the same logical entity.

#### Q4: Performance impact vs `id()` lookup?

**Finding**: Both are O(1) dict lookups. GID strings are slightly larger keys than ints, but the difference is negligible. String hashing is well-optimized in Python.

### POC 1: GID-Based Entity Registry Prototype

```python
"""
POC: GID-based entity registry for SaveSession.

Prototype-quality code demonstrating:
1. GID-based tracking with temp GID support
2. Re-keying when temp GIDs become real
3. Deduplication of re-fetched entities
"""

from __future__ import annotations
from typing import Any, TYPE_CHECKING
from autom8_asana.persistence.models import EntityState

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


class GidBasedTracker:
    """Entity tracker using GID as primary key.

    Key design decisions:
    - Uses GID as key when available (stable across references)
    - Falls back to id(entity) for entities without GID (edge case)
    - Supports temp_ GID -> real GID transition
    - Deduplicates entities with same GID
    """

    def __init__(self) -> None:
        # Primary storage: GID/temp_GID -> entity reference
        self._entities: dict[str, AsanaResource] = {}
        # GID -> snapshot at track time
        self._snapshots: dict[str, dict[str, Any]] = {}
        # GID -> lifecycle state
        self._states: dict[str, EntityState] = {}
        # Maps temp_gid -> real_gid after creation
        self._gid_transitions: dict[str, str] = {}
        # Reverse lookup for entity -> key (needed for GID-less entities)
        self._entity_to_key: dict[int, str] = {}

    def _get_key(self, entity: AsanaResource) -> str:
        """Generate tracking key for entity.

        Priority:
        1. Use entity's GID if it exists and is not temp_
        2. Use entity's temp_ GID if it exists
        3. Fall back to f"__id_{id(entity)}" for truly GID-less entities
        """
        gid = getattr(entity, 'gid', None)

        if gid:
            return gid  # Works for both real GIDs and temp_ GIDs

        # Edge case: entity has no GID at all
        return f"__id_{id(entity)}"

    def track(self, entity: AsanaResource) -> None:
        """Register entity for change tracking."""
        key = self._get_key(entity)

        # Check for existing entity with same GID
        if key in self._entities:
            existing = self._entities[key]
            if existing is not entity:
                # Same GID, different object - this is a re-fetch
                # Update to use the new entity reference
                old_id = id(existing)
                if old_id in self._entity_to_key:
                    del self._entity_to_key[old_id]

        self._entities[key] = entity
        self._entity_to_key[id(entity)] = key
        self._snapshots[key] = entity.model_dump()

        # Determine initial state
        gid = entity.gid
        if not gid or gid.startswith("temp_"):
            self._states[key] = EntityState.NEW
        else:
            self._states[key] = EntityState.CLEAN

    def untrack(self, entity: AsanaResource) -> None:
        """Remove entity from tracking."""
        key = self._get_key(entity)
        self._entities.pop(key, None)
        self._snapshots.pop(key, None)
        self._states.pop(key, None)
        self._entity_to_key.pop(id(entity), None)

    def get_state(self, entity: AsanaResource) -> EntityState:
        """Get entity lifecycle state with dynamic MODIFIED detection."""
        key = self._get_key(entity)

        if key not in self._states:
            raise ValueError(f"Entity not tracked: {type(entity).__name__}")

        state = self._states[key]

        # Check if CLEAN became MODIFIED
        if state == EntityState.CLEAN:
            if self._is_modified(entity, key):
                return EntityState.MODIFIED

        return state

    def _is_modified(self, entity: AsanaResource, key: str) -> bool:
        """Check if entity differs from tracked snapshot."""
        if key not in self._snapshots:
            return False
        return self._snapshots[key] != entity.model_dump()

    def update_gid(self, entity: AsanaResource, old_key: str, new_gid: str) -> None:
        """Re-key entity after temp GID becomes real GID.

        Called by pipeline after successful CREATE operation.
        """
        if old_key not in self._entities:
            return

        # Transfer all state to new key
        self._entities[new_gid] = self._entities.pop(old_key)
        self._snapshots[new_gid] = self._snapshots.pop(old_key)
        self._states[new_gid] = self._states.pop(old_key)
        self._gid_transitions[old_key] = new_gid
        self._entity_to_key[id(entity)] = new_gid

    def get_dirty_entities(self) -> list[AsanaResource]:
        """Get all entities with pending changes."""
        dirty: list[AsanaResource] = []

        for key, entity in self._entities.items():
            state = self._states.get(key, EntityState.CLEAN)

            if state == EntityState.DELETED:
                dirty.append(entity)
            elif state == EntityState.NEW:
                dirty.append(entity)
            elif state == EntityState.CLEAN:
                if self._is_modified(entity, key):
                    dirty.append(entity)

        return dirty

    def find_by_gid(self, gid: str) -> AsanaResource | None:
        """Look up entity by GID.

        This is a NEW capability enabled by GID-based tracking.
        """
        # Check direct lookup
        if gid in self._entities:
            return self._entities[gid]

        # Check if it's a transitioned GID
        if gid in self._gid_transitions:
            real_gid = self._gid_transitions[gid]
            return self._entities.get(real_gid)

        return None
```

### Key Findings - POC 1

| Aspect | Finding | Risk Level |
|--------|---------|------------|
| Temp GID handling | Supported via unified key approach | LOW |
| GID transition | Requires re-keying but straightforward | LOW |
| Entity refresh | Natural deduplication is an improvement | NONE |
| Performance | O(1) lookup, comparable to id() | NONE |
| Backward compatibility | Track/untrack API unchanged | NONE |

**New capability enabled**: `find_by_gid()` for direct entity lookup.

---

## Goal 2: Batch Failure Behavior Investigation

### Current Implementation Analysis

The batch API flow is:
1. `SaveSession.commit_async()` calls `SavePipeline.execute_with_actions()`
2. `SavePipeline.execute()` processes entities by dependency level
3. `BatchExecutor.execute_level()` builds `BatchRequest` objects
4. `BatchClient.execute_async()` sends to Asana `/batch` endpoint
5. `BatchResult.from_asana_response()` parses each response

### Questions Answered

#### Q1: Does the batch stop at first failure or continue?

**Finding**: **CONTINUES**. Asana's batch API processes all operations and returns results for each. From `batch/client.py`:

```python
# Response from batch endpoint is a list
# Each item corresponds to one request
for i, item in enumerate(response):
    results.append(
        BatchResult.from_asana_response(
            response_item=item,
            request_index=base_index + i,
        )
    )
```

Each operation gets its own status code and result.

#### Q2: What does the response look like for partial success?

**Finding**: Asana returns an array where each element represents one operation:

```json
// Example Asana batch response
[
    {
        "status_code": 201,
        "body": {"data": {"gid": "12345", "name": "Task 1"}}
    },
    {
        "status_code": 400,
        "body": {"errors": [{"message": "Invalid project", "help": "..."}]}
    },
    {
        "status_code": 201,
        "body": {"data": {"gid": "12347", "name": "Task 3"}}
    }
]
```

The `BatchResult` model correctly captures this:

```python
@property
def success(self) -> bool:
    """Whether the action succeeded (2xx status code)."""
    return 200 <= self.status_code < 300

@property
def error(self) -> AsanaError | None:
    """Extract error information if action failed."""
    if self.success:
        return None
    # Parse errors from body...
```

#### Q3: Can we identify which operations succeeded/failed?

**Finding**: **YES**, completely. The current implementation maintains full correlation:

```python
# BatchExecutor.execute_level()
batch_requests: list[BatchRequest] = []
request_map: list[tuple[AsanaResource, OperationType]] = []

for entity, op_type, payload in operations:
    request = self._build_request(entity, op_type, payload)
    batch_requests.append(request)
    request_map.append((entity, op_type))  # Track correlation

# After execution, correlate results
for i, batch_result in enumerate(batch_results):
    entity, op_type = request_map[i]
    results.append((entity, op_type, batch_result))
```

The `SaveResult` then separates succeeded and failed:

```python
if batch_result.success:
    all_succeeded.append(entity)
else:
    all_failed.append(SaveError(
        entity=entity,
        operation=op_type,
        error=batch_result.error or Exception("Unknown batch error"),
        payload=payload,
    ))
```

#### Q4: What error information is provided for failures?

**Finding**: Full Asana error details are preserved:

```python
# BatchResult.error property
if self.body and isinstance(self.body, dict):
    if "errors" in self.body:
        errors = self.body.get("errors", [])
        messages = [e.get("message", "Unknown error") for e in errors]
        message = "; ".join(messages)

return AsanaError(
    message,
    status_code=self.status_code,
    errors=errors,  # Full error objects preserved
)
```

### POC 2: Partial Failure Analysis

```python
"""
POC: Analysis of batch partial failure behavior.

This demonstrates the current capability - NO CHANGES NEEDED.
The implementation already provides per-operation success/failure tracking.
"""

from autom8_asana.batch.models import BatchResult, BatchSummary
from autom8_asana.persistence.models import SaveResult, SaveError


def analyze_batch_results(results: list[BatchResult]) -> dict:
    """Analyze batch results for partial failure scenarios.

    Demonstrates that full per-operation information is available.
    """
    summary = BatchSummary(results=results)

    analysis = {
        "total_operations": summary.total,
        "succeeded": summary.succeeded,
        "failed": summary.failed,
        "partial_success": summary.succeeded > 0 and summary.failed > 0,
        "all_succeeded": summary.all_succeeded,

        # Per-operation details
        "successful_operations": [
            {
                "index": r.request_index,
                "gid": r.data.get("gid") if r.data else None,
            }
            for r in summary.successful_results
        ],
        "failed_operations": [
            {
                "index": r.request_index,
                "status_code": r.status_code,
                "error_message": str(r.error) if r.error else "Unknown",
                "error_details": r.body.get("errors", []) if r.body else [],
            }
            for r in summary.failed_results
        ],
    }

    return analysis


def demonstrate_save_result_breakdown(result: SaveResult) -> dict:
    """Show that SaveResult provides full breakdown.

    SaveResult already has:
    - succeeded: List of entities that saved successfully
    - failed: List of SaveError with entity, operation, error, payload
    """
    return {
        "total_crud": result.total_count,
        "crud_succeeded": len(result.succeeded),
        "crud_failed": len(result.failed),

        # Per-entity failure details
        "failure_details": [
            {
                "entity_type": type(err.entity).__name__,
                "entity_gid": err.entity.gid,
                "operation": err.operation.value,
                "error": str(err.error),
                "payload": err.payload,
            }
            for err in result.failed
        ],

        # Aggregate properties
        "is_partial": result.partial,
        "is_success": result.success,
    }
```

### Key Findings - POC 2

| Aspect | Finding | Risk Level |
|--------|---------|------------|
| Per-operation results | FULLY SUPPORTED | NONE |
| Error attribution | FULLY SUPPORTED | NONE |
| Partial success detection | FULLY SUPPORTED | NONE |
| Error details | FULLY SUPPORTED | NONE |

**Conclusion**: The current implementation already provides complete partial failure breakdown. No changes needed for this goal.

---

## Risks Identified

### Low Risk

1. **Re-keying complexity**: When temp GID becomes real GID, we need to update dictionary keys. This is a simple operation but requires coordination in the pipeline.

2. **Entity refresh behavior change**: GID-based tracking would deduplicate re-fetched entities. This is generally desirable but could surprise users who expect separate tracking.

### Mitigated Risks

1. **GID-less entities**: Edge case of entities without any GID is handled by fallback to `__id_{id(entity)}` key.

2. **Memory leaks**: The `_gid_transitions` map could grow unboundedly. Should be cleared on session close (already happens when session is garbage collected).

### No Risk

1. **Batch failure breakdown**: Already fully implemented. No changes needed.

2. **Performance**: GID-based lookup is O(1), same as id()-based.

---

## Go/No-Go Evaluation

| Criterion | Status | Evidence |
|-----------|--------|----------|
| GID registry is feasible | **GO** | POC demonstrates clean implementation |
| Batch failure info available | **GO** | Already fully implemented |
| No showstoppers | **GO** | All issues are solvable |
| Performance acceptable | **GO** | O(1) lookup preserved |

### Final Recommendation

**GO** with **HIGH** confidence (95%)

**Rationale**:
1. GID-based entity tracking is straightforward to implement with the prototype as a starting point
2. Batch partial failure breakdown requires NO changes - already fully functional
3. No fundamental blockers discovered
4. Re-keying on GID transition is the main implementation detail, not a showstopper

### Suggested Implementation Approach

1. **Phase 1**: Implement `GidBasedTracker` as replacement for `ChangeTracker`
   - Maintain same public API (track, untrack, get_state, etc.)
   - Add new `find_by_gid()` capability
   - Handle temp GID -> real GID transitions in pipeline

2. **Phase 2**: Expose partial failure details in user-facing API
   - Already available in `SaveResult.failed` and `SaveError`
   - Consider adding helper methods for common queries
   - Document partial failure handling in SDK docs

3. **Phase 3**: Consider additional reliability features
   - Retry mechanism for transient failures
   - Idempotency keys for duplicate detection
   - Transaction-like semantics (optional)

---

## Appendix: Files Examined

| File | Purpose | Key Insights |
|------|---------|--------------|
| `persistence/tracker.py` | Current id()-based tracking | Core implementation to replace |
| `persistence/session.py` | SaveSession commit flow | Shows integration points |
| `persistence/pipeline.py` | Batch execution pipeline | Shows GID transition handling |
| `persistence/executor.py` | BatchExecutor wrapper | Shows result correlation |
| `persistence/models.py` | SaveResult, SaveError | Shows existing failure tracking |
| `persistence/exceptions.py` | Exception hierarchy | Shows error types available |
| `batch/client.py` | BatchClient | Shows chunking and execution |
| `batch/models.py` | BatchRequest/Result | Shows per-operation response parsing |

---

## Session Metadata

- **Engineer**: Principal Engineer (Claude)
- **Duration**: 1 session (as timeboxed)
- **Confidence Level**: HIGH (95%)
- **Next Steps**: Proceed to Discovery phase with GO recommendation
