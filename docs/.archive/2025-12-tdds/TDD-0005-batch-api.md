# TDD: Batch API for Bulk Operations

## Metadata
- **TDD ID**: TDD-0005
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-08
- **Last Updated**: 2025-12-08
- **PRD Reference**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md) (FR-SDK-030 through FR-SDK-034)
- **Related TDDs**: [TDD-0001](TDD-0001-sdk-architecture.md) (SDK architecture)
- **Related ADRs**:
  - [ADR-0010](../decisions/ADR-0010-batch-chunking-strategy.md) - Sequential chunk execution for batch operations

## Overview

The Batch API provides bulk operation capabilities for the autom8_asana SDK, wrapping Asana's `/batch` endpoint. The design enables efficient bulk create and update operations with automatic chunking to respect Asana's 10-action-per-request limit, sequential chunk execution to maintain rate limit compliance, and graceful handling of partial failures where individual action failures don't fail the entire batch.

## Requirements Summary

From [PRD-0001](../requirements/PRD-0001-sdk-extraction.md), Batch API requirements:

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-SDK-030 | Support Asana Batch API for bulk operations | Must |
| FR-SDK-031 | Automatically chunk batch requests to Asana limits | Must |
| FR-SDK-032 | Support batch create operations | Must |
| FR-SDK-033 | Support batch update operations | Must |
| FR-SDK-034 | Handle partial batch failures gracefully | Must |

## System Context

The BatchClient integrates with the existing SDK architecture as a specialized client that wraps the `/batch` endpoint:

```
+-------------------+
|   User Code       |
+--------+----------+
         |
         | BatchRequest[]
         v
+-------------------+       +-------------------+
|   BatchClient     |------>|   AsyncHTTPClient |
|                   |       +--------+----------+
| - Chunking logic  |                |
| - Result assembly |                |
| - Failure mapping |                v
+-------------------+       +-------------------+
                            |   Asana /batch    |
                            +-------------------+
```

The BatchClient:
- Receives a list of `BatchRequest` objects from user code
- Automatically chunks into groups of 10 (Asana's limit)
- Executes chunks sequentially via `AsyncHTTPClient`
- Assembles `BatchResult` objects preserving original request order
- Maps individual action failures without failing the entire batch

## Design

### Component Architecture

```
autom8_asana/batch/
|
+-- __init__.py          # Public exports: BatchClient, BatchRequest, BatchResult
+-- client.py            # BatchClient implementation
+-- models.py            # BatchRequest, BatchResult, BatchAction models
```

| Component | Responsibility |
|-----------|----------------|
| `BatchClient` | Orchestrates batch execution: chunking, HTTP calls, result assembly |
| `BatchRequest` | Immutable model representing a single action in a batch |
| `BatchResult` | Immutable model representing result of a single action |
| `BatchAction` | Internal model for Asana API batch action format |

### Data Model

#### BatchRequest

```python
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class BatchRequest:
    """Single request within a batch operation.

    Represents one action to be executed in an Asana batch request.
    Immutable to ensure batch contents can't change during execution.

    Attributes:
        relative_path: API path relative to base URL (e.g., "/tasks", "/tasks/123")
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Request body for POST/PUT operations
        options: Query parameters (e.g., opt_fields)

    Example:
        # Create a task
        BatchRequest(
            relative_path="/tasks",
            method="POST",
            data={"name": "New Task", "projects": ["12345"]},
        )

        # Update a task
        BatchRequest(
            relative_path="/tasks/67890",
            method="PUT",
            data={"completed": True},
        )

        # Get a task with specific fields
        BatchRequest(
            relative_path="/tasks/67890",
            method="GET",
            options={"opt_fields": "name,completed,assignee"},
        )
    """
    relative_path: str
    method: str
    data: dict[str, Any] | None = None
    options: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate request configuration."""
        valid_methods = {"GET", "POST", "PUT", "DELETE"}
        if self.method.upper() not in valid_methods:
            raise ValueError(f"method must be one of {valid_methods}, got '{self.method}'")
        if not self.relative_path.startswith("/"):
            raise ValueError(f"relative_path must start with '/', got '{self.relative_path}'")

    def to_action_dict(self) -> dict[str, Any]:
        """Convert to Asana batch action format.

        Returns:
            Dict matching Asana's batch action schema:
            {
                "relative_path": "/tasks",
                "method": "POST",
                "data": {...},      # optional
                "options": {...}    # optional
            }
        """
        action: dict[str, Any] = {
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

```python
from dataclasses import dataclass
from typing import Any

from autom8_asana.exceptions import AsanaError

@dataclass(frozen=True)
class BatchResult:
    """Result of a single action within a batch operation.

    Each BatchResult corresponds to one BatchRequest, preserving order.
    Check the `success` property to determine if the action succeeded.

    Attributes:
        status_code: HTTP status code returned for this action
        body: Response body (parsed JSON) or None
        headers: Response headers dict or None
        request_index: Original index of the request in the batch (for correlation)

    Example:
        results = await client.batch.execute_async(requests)

        for i, result in enumerate(results):
            if result.success:
                print(f"Action {i} succeeded: {result.body}")
            else:
                print(f"Action {i} failed: {result.error}")
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
    def error(self) -> AsanaError | None:
        """Extract error information if action failed.

        Returns:
            AsanaError with details if failed, None if succeeded.
        """
        if self.success:
            return None

        message = "Batch action failed"
        errors: list[dict[str, Any]] = []

        if self.body and isinstance(self.body, dict):
            if "errors" in self.body:
                errors = self.body.get("errors", [])
                messages = [e.get("message", "Unknown error") for e in errors]
                message = "; ".join(messages) if messages else message

        return AsanaError(
            message,
            status_code=self.status_code,
            errors=errors,
        )

    @property
    def data(self) -> dict[str, Any] | None:
        """Extract the 'data' field from successful responses.

        Asana wraps responses in {"data": ...}. This property
        unwraps for convenience.

        Returns:
            The unwrapped data dict, or None if not present/failed.
        """
        if not self.success or not self.body:
            return None
        if isinstance(self.body, dict) and "data" in self.body:
            return self.body["data"]
        return self.body

    @classmethod
    def from_asana_response(
        cls,
        response_item: dict[str, Any],
        request_index: int,
    ) -> "BatchResult":
        """Create BatchResult from Asana batch response item.

        Args:
            response_item: Single item from Asana batch response array
            request_index: Original index for correlation

        Returns:
            BatchResult instance
        """
        return cls(
            status_code=response_item.get("status_code", 500),
            body=response_item.get("body"),
            headers=response_item.get("headers"),
            request_index=request_index,
        )
```

#### BatchSummary (Helper class for result aggregation)

```python
from dataclasses import dataclass, field

@dataclass
class BatchSummary:
    """Summary statistics for a batch operation.

    Provides convenient access to aggregate information about
    batch execution results.

    Attributes:
        total: Total number of actions executed
        succeeded: Number of successful actions
        failed: Number of failed actions
        results: All BatchResult objects in original order
    """
    results: list[BatchResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total number of actions."""
        return len(self.results)

    @property
    def succeeded(self) -> int:
        """Number of successful actions."""
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        """Number of failed actions."""
        return sum(1 for r in self.results if not r.success)

    @property
    def all_succeeded(self) -> bool:
        """Whether all actions succeeded."""
        return all(r.success for r in self.results)

    @property
    def successful_results(self) -> list[BatchResult]:
        """Filter to only successful results."""
        return [r for r in self.results if r.success]

    @property
    def failed_results(self) -> list[BatchResult]:
        """Filter to only failed results."""
        return [r for r in self.results if not r.success]
```

### API Contracts

#### BatchClient

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.batch.models import BatchRequest, BatchResult, BatchSummary
from autom8_asana.clients.base import BaseClient
from autom8_asana.transport.sync import sync_wrapper

if TYPE_CHECKING:
    from autom8_asana.models.task import Task

# Asana batch API limit
BATCH_SIZE_LIMIT = 10


class BatchClient(BaseClient):
    """Client for Asana Batch API operations.

    Enables efficient bulk operations by batching multiple requests
    into single API calls. Automatically handles:
    - Chunking requests into groups of 10 (Asana's limit)
    - Sequential chunk execution for rate limit compliance
    - Partial failure handling (one failure doesn't fail the batch)
    - Result correlation with original request order

    Example - Basic batch execution:
        requests = [
            BatchRequest("/tasks", "POST", data={"name": "Task 1", "projects": ["123"]}),
            BatchRequest("/tasks", "POST", data={"name": "Task 2", "projects": ["123"]}),
            BatchRequest("/tasks/456", "PUT", data={"completed": True}),
        ]

        results = await client.batch.execute_async(requests)

        for i, result in enumerate(results):
            if result.success:
                print(f"Request {i} succeeded: {result.data}")
            else:
                print(f"Request {i} failed: {result.error}")

    Example - Convenience methods:
        # Batch create tasks
        tasks_data = [
            {"name": "Task 1", "projects": ["123"]},
            {"name": "Task 2", "projects": ["123"], "assignee": "456"},
        ]
        results = await client.batch.create_tasks_async(tasks_data)

        # Batch update tasks
        updates = [
            ("task_gid_1", {"completed": True}),
            ("task_gid_2", {"assignee": "789"}),
        ]
        results = await client.batch.update_tasks_async(updates)
    """

    # --- Core Async Methods ---

    async def execute_async(
        self,
        requests: list[BatchRequest],
    ) -> list[BatchResult]:
        """Execute batch of requests with auto-chunking.

        Processes requests in chunks of 10 (Asana's limit), executing
        chunks sequentially to respect rate limits. Results are returned
        in the same order as input requests.

        Args:
            requests: List of BatchRequest objects to execute

        Returns:
            List of BatchResult objects, one per request, in order

        Raises:
            AsanaError: If the batch endpoint itself fails (not individual actions)

        Note:
            Individual action failures are captured in BatchResult.error,
            not raised as exceptions. This allows partial success.
        """
        ...

    async def execute_with_summary_async(
        self,
        requests: list[BatchRequest],
    ) -> BatchSummary:
        """Execute batch and return summary with aggregate statistics.

        Same as execute_async but returns a BatchSummary with
        convenience methods for analyzing results.

        Args:
            requests: List of BatchRequest objects to execute

        Returns:
            BatchSummary with results and statistics
        """
        ...

    # --- Task-Specific Convenience Methods ---

    async def create_tasks_async(
        self,
        tasks: list[dict[str, Any]],
        *,
        opt_fields: list[str] | None = None,
    ) -> list[BatchResult]:
        """Batch create multiple tasks.

        Convenience method that builds BatchRequest objects for
        task creation. Equivalent to calling execute_async with
        POST /tasks requests.

        Args:
            tasks: List of task data dicts, each containing:
                - name (required): Task name
                - projects: List of project GIDs
                - assignee: Assignee user GID
                - notes: Task description
                - due_on: Due date (YYYY-MM-DD)
                - parent: Parent task GID (for subtasks)
                - custom_fields: Dict of custom field GID -> value
                - ... (any other valid task fields)
            opt_fields: Fields to include in response

        Returns:
            List of BatchResult objects for each create operation

        Example:
            results = await client.batch.create_tasks_async([
                {"name": "Task 1", "projects": ["123"]},
                {"name": "Task 2", "projects": ["123"], "due_on": "2024-01-15"},
            ])

            created_gids = [
                r.data["gid"] for r in results if r.success
            ]
        """
        ...

    async def update_tasks_async(
        self,
        updates: list[tuple[str, dict[str, Any]]],
        *,
        opt_fields: list[str] | None = None,
    ) -> list[BatchResult]:
        """Batch update multiple tasks.

        Convenience method that builds BatchRequest objects for
        task updates. Each update is a tuple of (task_gid, data).

        Args:
            updates: List of (task_gid, update_data) tuples where:
                - task_gid: GID of task to update
                - update_data: Dict of fields to update:
                    - name: New task name
                    - completed: Completion status
                    - assignee: New assignee GID
                    - due_on: New due date
                    - ... (any updatable task fields)
            opt_fields: Fields to include in response

        Returns:
            List of BatchResult objects for each update operation

        Example:
            results = await client.batch.update_tasks_async([
                ("task_gid_1", {"completed": True}),
                ("task_gid_2", {"assignee": "user_gid"}),
                ("task_gid_3", {"name": "Renamed Task"}),
            ])

            failed = [r for r in results if not r.success]
            if failed:
                print(f"{len(failed)} updates failed")
        """
        ...

    async def delete_tasks_async(
        self,
        task_gids: list[str],
    ) -> list[BatchResult]:
        """Batch delete multiple tasks.

        Args:
            task_gids: List of task GIDs to delete

        Returns:
            List of BatchResult objects for each delete operation
        """
        ...

    # --- Sync Wrappers ---

    def execute(self, requests: list[BatchRequest]) -> list[BatchResult]:
        """Sync wrapper for execute_async."""
        ...

    def execute_with_summary(self, requests: list[BatchRequest]) -> BatchSummary:
        """Sync wrapper for execute_with_summary_async."""
        ...

    def create_tasks(
        self,
        tasks: list[dict[str, Any]],
        *,
        opt_fields: list[str] | None = None,
    ) -> list[BatchResult]:
        """Sync wrapper for create_tasks_async."""
        ...

    def update_tasks(
        self,
        updates: list[tuple[str, dict[str, Any]]],
        *,
        opt_fields: list[str] | None = None,
    ) -> list[BatchResult]:
        """Sync wrapper for update_tasks_async."""
        ...

    def delete_tasks(self, task_gids: list[str]) -> list[BatchResult]:
        """Sync wrapper for delete_tasks_async."""
        ...
```

### Data Flow

#### Batch Execute Flow

```
User Code                  BatchClient                 AsyncHTTPClient        Asana /batch
    |                           |                            |                     |
    | execute_async([req1..15]) |                            |                     |
    |-------------------------->|                            |                     |
    |                           |                            |                     |
    |                           | _chunk_requests()          |                     |
    |                           | chunks = [[r1..r10],       |                     |
    |                           |           [r11..r15]]      |                     |
    |                           |                            |                     |
    |                           | --- Chunk 1 (10 items) ----|                     |
    |                           |                            |                     |
    |                           | POST /batch                |                     |
    |                           | {"actions": [a1..a10]}     |                     |
    |                           |--------------------------->|                     |
    |                           |                            | POST /batch         |
    |                           |                            |-------------------->|
    |                           |                            |                     |
    |                           |                            | [result1..result10] |
    |                           |                            |<--------------------|
    |                           |                            |                     |
    |                           | _parse_chunk_results()     |                     |
    |                           |<---------------------------|                     |
    |                           |                            |                     |
    |                           | --- Chunk 2 (5 items) -----|                     |
    |                           |                            |                     |
    |                           | POST /batch                |                     |
    |                           | {"actions": [a11..a15]}    |                     |
    |                           |--------------------------->|                     |
    |                           |                            | POST /batch         |
    |                           |                            |-------------------->|
    |                           |                            |                     |
    |                           |                            | [result11..15]      |
    |                           |                            |<--------------------|
    |                           |                            |                     |
    |                           | _parse_chunk_results()     |                     |
    |                           |<---------------------------|                     |
    |                           |                            |                     |
    |                           | _assemble_results()        |                     |
    |                           | all_results = [r1..r15]    |                     |
    |                           |                            |                     |
    | [BatchResult x 15]        |                            |                     |
    |<--------------------------|                            |                     |
```

#### Partial Failure Handling

```
BatchClient                              Asana /batch Response
    |                                           |
    | POST {"actions": [create1, update2]}      |
    |------------------------------------------>|
    |                                           |
    | Response: [                               |
    |   {"status_code": 201, "body": {...}},    |  <-- create1 succeeded
    |   {"status_code": 404, "body": {...}}     |  <-- update2 failed (not found)
    | ]                                         |
    |<------------------------------------------|
    |                                           |
    | Results:                                  |
    | [                                         |
    |   BatchResult(201, success=True),         |
    |   BatchResult(404, success=False,         |
    |              error=NotFoundError)         |
    | ]                                         |
```

### Auto-Chunking Algorithm

Per [ADR-0010](../decisions/ADR-0010-batch-chunking-strategy.md):

```python
BATCH_SIZE_LIMIT = 10

def _chunk_requests(
    requests: list[BatchRequest],
) -> list[list[BatchRequest]]:
    """Split requests into chunks of BATCH_SIZE_LIMIT.

    Args:
        requests: All requests to chunk

    Returns:
        List of chunks, each with at most BATCH_SIZE_LIMIT requests

    Example:
        >>> _chunk_requests([r1, r2, ..., r25])
        [[r1..r10], [r11..r20], [r21..r25]]
    """
    if not requests:
        return []

    return [
        requests[i:i + BATCH_SIZE_LIMIT]
        for i in range(0, len(requests), BATCH_SIZE_LIMIT)
    ]


async def _execute_chunk(
    self,
    chunk: list[BatchRequest],
    base_index: int,
) -> list[BatchResult]:
    """Execute a single chunk of requests.

    Args:
        chunk: List of requests (max 10)
        base_index: Starting index for result correlation

    Returns:
        List of BatchResult objects with correct request_index values
    """
    actions = [req.to_action_dict() for req in chunk]

    # POST to /batch endpoint
    response = await self._http.post(
        "/batch",
        json={"actions": actions},
    )

    # Parse results, preserving order
    results: list[BatchResult] = []
    for i, item in enumerate(response):
        results.append(
            BatchResult.from_asana_response(
                response_item=item,
                request_index=base_index + i,
            )
        )

    return results
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Chunk execution strategy | Sequential | Rate limit compliance; simpler error handling; matches existing SDK patterns | [ADR-0010](../decisions/ADR-0010-batch-chunking-strategy.md) |
| Request model | Immutable dataclass | Prevents modification during execution; hashable for deduplication | - |
| Partial failure handling | Per-result errors, no exception | Matches Asana's behavior; enables partial success processing | - |
| Result correlation | request_index field | Maintains original order even with failures | - |

## Complexity Assessment

**Level**: MODULE

**Justification**:
- Single-purpose component (batch operations)
- Clean API surface with clear boundaries
- Internal structure (chunking, parsing) is minimal
- Integrates with existing transport layer without modification
- No new cross-cutting concerns introduced

This complexity level is appropriate because:
1. BatchClient is a specialized wrapper around existing HTTP transport
2. The chunking logic is straightforward (split into groups of 10)
3. No new infrastructure or patterns required
4. Testing is tractable with mock HTTP responses

## Implementation Plan

### Phase 1: Core Models (2 hours)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `BatchRequest` dataclass | None | 30m |
| `BatchResult` dataclass | `AsanaError` | 45m |
| `BatchSummary` helper | `BatchResult` | 30m |
| Unit tests for models | Models | 15m |

**Exit Criteria**: All models validate correctly, serialize to Asana format, parse responses.

### Phase 2: BatchClient Core (3 hours)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `_chunk_requests()` helper | None | 30m |
| `_execute_chunk()` method | `AsyncHTTPClient` | 45m |
| `execute_async()` implementation | Chunk methods | 45m |
| `execute_with_summary_async()` | `execute_async` | 15m |
| Sync wrappers | Async methods | 30m |
| Unit tests | All methods | 30m |

**Exit Criteria**: Can execute batch requests with auto-chunking; results returned in order.

### Phase 3: Convenience Methods (1.5 hours)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `create_tasks_async()` | `execute_async` | 30m |
| `update_tasks_async()` | `execute_async` | 30m |
| `delete_tasks_async()` | `execute_async` | 15m |
| Unit tests for convenience methods | All methods | 15m |

**Exit Criteria**: All convenience methods work; properly build BatchRequest objects.

### Phase 4: Integration (1.5 hours)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Add `batch` property to `AsanaClient` | `BatchClient` | 15m |
| Export from `batch/__init__.py` | All models | 15m |
| Integration tests with mock server | All components | 45m |
| Documentation | All components | 15m |

**Exit Criteria**: `client.batch.execute_async()` works end-to-end.

**Total Estimate**: 8 hours

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Asana changes batch limit from 10 | Low | Low | Make `BATCH_SIZE_LIMIT` configurable; detect and log if API rejects |
| Large batches cause memory issues | Medium | Low | Results are processed per-chunk; don't accumulate entire response in memory |
| Chunk failures leave partial state | Medium | Medium | Document that batch operations are not atomic; provide failed indices for retry |
| Rate limiting during chunk execution | Low | Low | Sequential execution respects existing rate limiter; Asana counts batch as single request |

## Observability

### Logging
- **DEBUG**: Chunk boundaries, per-action status codes
- **INFO**: Batch started (total count), batch completed (success/fail counts)
- **WARNING**: Partial failures (X of Y actions failed)
- **ERROR**: Batch endpoint failure (not individual action failures)

Example log output:
```
INFO  BatchClient.execute: Starting batch of 25 requests in 3 chunks
DEBUG BatchClient.execute: Chunk 1/3: 10 actions
DEBUG BatchClient.execute: Chunk 1/3 complete: 10 succeeded, 0 failed
DEBUG BatchClient.execute: Chunk 2/3: 10 actions
DEBUG BatchClient.execute: Chunk 2/3 complete: 9 succeeded, 1 failed
DEBUG BatchClient.execute: Chunk 3/3: 5 actions
DEBUG BatchClient.execute: Chunk 3/3 complete: 5 succeeded, 0 failed
INFO  BatchClient.execute: Batch complete: 24/25 succeeded
```

### Metrics
- `asana_batch_requests_total` (counter, labels: operation_type)
- `asana_batch_actions_total` (counter, labels: status=success|failure)
- `asana_batch_chunk_count` (histogram)
- `asana_batch_duration_seconds` (histogram)

## Testing Strategy

### Unit Testing (Target: 95% coverage)
- `BatchRequest` validation (invalid method, missing path)
- `BatchRequest.to_action_dict()` serialization
- `BatchResult.success`, `.error`, `.data` properties
- `BatchResult.from_asana_response()` parsing
- `BatchSummary` statistics
- `_chunk_requests()` edge cases (empty, exact multiple, remainder)
- Sync wrapper behavior in async context (should raise)

### Integration Testing (Target: 90% coverage)
- Execute with mock HTTP returning success for all
- Execute with mock HTTP returning partial failures
- Execute with > 10 requests (verify chunking)
- Execute with empty list (should return empty)
- Task convenience methods build correct requests
- Error propagation when batch endpoint fails

### Edge Cases
| Case | Expected Behavior |
|------|-------------------|
| Empty request list | Return empty list immediately |
| Exactly 10 requests | Single chunk, no splitting |
| 11 requests | Two chunks: 10 + 1 |
| All actions fail | Return all results with errors |
| Batch endpoint 500 | Raise AsanaError (not BatchResult) |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should we support parallel chunk execution for users who want max throughput? | Architect | Before v1.1 | Defer to future enhancement; sequential is safer default |
| Should batch operations bypass the rate limiter (since Asana counts them as 1 request)? | Engineer | Implementation | No - batch still consumes rate limit capacity |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-08 | Architect | Initial design |
