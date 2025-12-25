# Batch Operation Patterns

## Metadata
- **Document Type**: Reference
- **Status**: Active
- **Created**: 2025-12-24
- **Last Updated**: 2025-12-24
- **Purpose**: Canonical reference for batch operation patterns (chunking, parallelization, error handling)

## Overview

Batch operations enable efficient bulk processing of Asana API operations. This document defines standard patterns for chunking, parallelization, error handling, and performance optimization used throughout the autom8_asana SDK.

## Chunking Strategy

### Chunk Size Determination

**Default**: 10 operations per chunk (Asana Batch API limit: 10 actions per request)

**Rationale**:
- Asana Batch API enforces 10-action limit per `/batch` request
- Sequential chunk execution maintains rate limit compliance
- Fixed size simplifies correlation of results to requests

**Algorithm**:
```python
def chunk_operations(operations: list, chunk_size: int = 10) -> list[list]:
    """
    Split operations into fixed-size chunks.

    Args:
        operations: List of operations to chunk
        chunk_size: Max operations per chunk (default 10)

    Returns:
        List of operation chunks
    """
    return [
        operations[i:i + chunk_size]
        for i in range(0, len(operations), chunk_size)
    ]
```

**Example**:
```python
# 25 operations → 3 chunks: [10, 10, 5]
operations = list(range(25))
chunks = chunk_operations(operations, chunk_size=10)

print(len(chunks))  # 3
print([len(chunk) for chunk in chunks])  # [10, 10, 5]
```

**References**:
- [ADR-0010: Batch Chunking Strategy](../decisions/ADR-0010-batch-chunking-strategy.md)

---

## Execution Strategy

### Sequential Execution (Default)

**Pattern**: Execute chunks one at a time in sequence.

**Rationale**:
- Maintains rate limit compliance
- Predictable resource usage
- Easier debugging and error correlation

**Implementation**:
```python
async def execute_sequential(chunks: list[list[BatchRequest]]) -> list[BatchResult]:
    """
    Execute chunks sequentially.

    Each chunk waits for previous chunk to complete before starting.
    """
    results = []

    for chunk in chunks:
        chunk_results = await batch_client.execute_chunk(chunk)
        results.extend(chunk_results)

    return results
```

**Performance**: O(C) where C = number of chunks. Total time = C × chunk_execution_time.

**References**:
- [ADR-0039: Batch Execution Strategy](../decisions/ADR-0039-batch-execution-strategy.md)

---

## Parallelization

### Concurrency Limits

**Default**: Sequential execution (concurrency = 1)

**Rationale**: Asana rate limits are per-workspace. Parallel execution risks exceeding rate limits.

**Advanced Pattern** (use with caution):
```python
import asyncio
from asyncio import Semaphore

async def execute_with_concurrency(
    chunks: list[list[BatchRequest]],
    max_concurrent: int = 3,
) -> list[BatchResult]:
    """
    Execute chunks with controlled concurrency.

    WARNING: Monitor rate limits carefully when using concurrency > 1.
    """
    semaphore = Semaphore(max_concurrent)
    results = []

    async def execute_chunk_with_semaphore(chunk):
        async with semaphore:
            return await batch_client.execute_chunk(chunk)

    tasks = [execute_chunk_with_semaphore(chunk) for chunk in chunks]
    chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in chunk_results:
        if isinstance(result, Exception):
            # Handle exception
            pass
        else:
            results.extend(result)

    return results
```

**When to Use**:
- Multiple workspaces (rate limits are per-workspace)
- Low request volume per workspace
- Monitoring shows headroom under rate limits

**When NOT to Use**:
- Single workspace with high volume
- Unknown rate limit headroom
- Default choice should always be sequential

---

## Error Handling

### Partial Failure Strategy

**Pattern**: Commit successful operations, report failures.

**Rationale**:
- Asana Batch API allows individual actions to fail
- No rollback needed (operations are idempotent or additive)
- Applications can decide how to handle failures

**Implementation**:
```python
@dataclass
class BatchResult:
    """Result of a single batch operation."""
    success: bool
    status_code: int
    body: Optional[dict] = None
    error: Optional[str] = None

async def execute_batch(requests: list[BatchRequest]) -> list[BatchResult]:
    """
    Execute batch requests with partial failure handling.

    Returns:
        List of BatchResult objects (one per request).
        Failed operations have success=False and error message.
    """
    chunks = chunk_operations(requests)
    all_results = []

    for chunk in chunks:
        # Execute chunk
        response = await http_client.post("/batch", {"actions": chunk})

        # Parse results
        for action_result in response["data"]:
            if action_result["status_code"] in (200, 201):
                all_results.append(BatchResult(
                    success=True,
                    status_code=action_result["status_code"],
                    body=action_result["body"],
                ))
            else:
                all_results.append(BatchResult(
                    success=False,
                    status_code=action_result["status_code"],
                    error=action_result["body"].get("errors", [{}])[0].get("message"),
                ))

    return all_results
```

**Usage**:
```python
results = await execute_batch(requests)

successful = [r for r in results if r.success]
failed = [r for r in results if not r.success]

print(f"Successful: {len(successful)}")
print(f"Failed: {len(failed)}")

for result in failed:
    print(f"Error: {result.error}")
```

**References**:
- [ADR-0040: Partial Failure Handling](../decisions/ADR-0040-partial-failure-handling.md)

---

### Retry Logic

**Pattern**: Exponential backoff with jitter for transient errors.

**Transient Errors**:
- 429 (Rate Limit Exceeded)
- 500 (Internal Server Error)
- 502 (Bad Gateway)
- 503 (Service Unavailable)

**Non-Retryable Errors**:
- 400 (Bad Request)
- 401 (Unauthorized)
- 403 (Forbidden)
- 404 (Not Found)
- 422 (Unprocessable Entity)

**Implementation**:
```python
import asyncio
import random

MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds

async def execute_with_retry(request: BatchRequest) -> BatchResult:
    """
    Execute batch request with exponential backoff retry.

    Retries transient errors up to MAX_RETRIES times.
    """
    for attempt in range(MAX_RETRIES + 1):
        result = await execute_batch([request])

        if result[0].success:
            return result[0]

        # Check if retryable
        if result[0].status_code not in (429, 500, 502, 503):
            return result[0]  # Non-retryable

        if attempt < MAX_RETRIES:
            # Exponential backoff with jitter
            delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(delay)

    return result[0]  # Final attempt failed
```

---

## Request Deduplication

**Pattern**: Detect and eliminate duplicate requests within a batch.

**Algorithm**:
```python
from typing import Hashable

def deduplicate_requests(requests: list[BatchRequest]) -> list[BatchRequest]:
    """
    Remove duplicate requests based on (method, relative_path, data).

    Preserves first occurrence of each unique request.
    """
    seen = set()
    unique_requests = []

    for request in requests:
        # Create hashable key
        key = (request.method, request.relative_path, _freeze_dict(request.data))

        if key not in seen:
            seen.add(key)
            unique_requests.append(request)

    return unique_requests

def _freeze_dict(d: dict) -> Hashable:
    """Convert dict to hashable frozenset of items."""
    if d is None:
        return None
    return frozenset(
        (k, _freeze_dict(v) if isinstance(v, dict) else v)
        for k, v in d.items()
    )
```

**Usage**:
```python
# Remove duplicates before execution
requests = [...]  # May contain duplicates
unique_requests = deduplicate_requests(requests)

results = await execute_batch(unique_requests)
```

---

## Cache-Aware Batching

**Pattern**: Filter operations that can be satisfied from cache.

**Algorithm**:
```python
async def execute_with_cache(
    requests: list[BatchRequest],
    cache: Cache,
) -> list[BatchResult]:
    """
    Execute batch with cache lookup first.

    Only execute requests for cache misses.
    """
    results = []
    cache_misses = []
    cache_miss_indices = []

    for i, request in enumerate(requests):
        if request.method == "GET":
            # Check cache
            cache_key = f"{request.relative_path}:{request.options}"
            cached = await cache.get(cache_key)

            if cached:
                results.append(BatchResult(
                    success=True,
                    status_code=200,
                    body=cached,
                ))
            else:
                cache_misses.append(request)
                cache_miss_indices.append(i)
                results.append(None)  # Placeholder
        else:
            # Non-GET: always execute
            cache_misses.append(request)
            cache_miss_indices.append(i)
            results.append(None)  # Placeholder

    # Execute cache misses
    if cache_misses:
        miss_results = await execute_batch(cache_misses)

        # Insert results at correct indices
        for idx, result in zip(cache_miss_indices, miss_results):
            results[idx] = result

            # Cache successful GET responses
            if result.success and requests[idx].method == "GET":
                cache_key = f"{requests[idx].relative_path}:{requests[idx].options}"
                await cache.set(cache_key, result.body)

    return results
```

**References**:
- [REF-cache-architecture.md](./REF-cache-architecture.md)

---

## Watermark Strategy

**Pattern**: Resume interrupted batch operations using high-water marks.

**Use Case**: Large batch operations that may be interrupted (e.g., network failure, service restart).

**Implementation**:
```python
@dataclass
class BatchProgress:
    """Track progress of batch operation."""
    total: int
    completed: int
    watermark: int  # Index of last successfully processed chunk

    @property
    def remaining(self) -> int:
        return self.total - self.completed

async def execute_with_watermark(
    requests: list[BatchRequest],
    progress: Optional[BatchProgress] = None,
) -> tuple[list[BatchResult], BatchProgress]:
    """
    Execute batch with watermark for resumability.

    Args:
        requests: All requests to execute
        progress: Previous progress (if resuming)

    Returns:
        (results, progress)
    """
    if progress is None:
        progress = BatchProgress(total=len(requests), completed=0, watermark=0)

    chunks = chunk_operations(requests)
    all_results = []

    # Resume from watermark
    for i, chunk in enumerate(chunks[progress.watermark:], start=progress.watermark):
        try:
            chunk_results = await execute_batch(chunk)
            all_results.extend(chunk_results)

            # Update progress
            progress.completed += len(chunk)
            progress.watermark = i + 1

            # Persist progress (e.g., to database)
            await save_progress(progress)

        except Exception as e:
            # Save progress before raising
            await save_progress(progress)
            raise

    return all_results, progress
```

**Usage**:
```python
# Initial execution
try:
    results, progress = await execute_with_watermark(requests)
except NetworkError:
    # Save progress and retry later
    await save_progress(progress)

# Resume from watermark
loaded_progress = await load_progress()
results, progress = await execute_with_watermark(requests, progress=loaded_progress)
```

**References**:
- [TDD-WATERMARK-CACHE](../design/TDD-WATERMARK-CACHE.md)

---

## Performance Optimization

### Minimize Batch Count

**Pattern**: Batch related operations together.

**Example**:
```python
# ❌ BAD: Separate batches for creates and updates
create_results = await execute_batch(create_requests)
update_results = await execute_batch(update_requests)
# Cost: 2 batch API calls

# ✓ GOOD: Combined batch (if order doesn't matter)
combined = create_requests + update_requests
results = await execute_batch(combined)
# Cost: 1 batch API call (if ≤10 operations)
```

### Request Compression

**Pattern**: Use `opt_fields` to reduce response size.

**Example**:
```python
# Specify only needed fields
request = BatchRequest(
    relative_path="/tasks/123",
    method="GET",
    options={"opt_fields": "gid,name,custom_fields"}  # Only 3 fields
)

# vs. fetching all fields (larger payload)
request = BatchRequest(
    relative_path="/tasks/123",
    method="GET",
)
```

---

## Testing Recommendations

### Unit Tests

```python
def test_chunking():
    operations = list(range(25))
    chunks = chunk_operations(operations, chunk_size=10)

    assert len(chunks) == 3
    assert len(chunks[0]) == 10
    assert len(chunks[1]) == 10
    assert len(chunks[2]) == 5

def test_deduplication():
    requests = [
        BatchRequest("/tasks", "POST", {"name": "A"}),
        BatchRequest("/tasks", "POST", {"name": "A"}),  # Duplicate
        BatchRequest("/tasks", "POST", {"name": "B"}),
    ]

    unique = deduplicate_requests(requests)

    assert len(unique) == 2
```

### Integration Tests

```python
async def test_batch_execution(async_client):
    requests = [
        BatchRequest("/tasks", "POST", {"name": f"Task {i}"})
        for i in range(25)
    ]

    results = await async_client.batch.execute(requests)

    assert len(results) == 25
    assert all(r.success for r in results)
```

---

## See Also

- [REF-savesession-lifecycle.md](./REF-savesession-lifecycle.md) - SaveSession uses batch operations for commit
- [REF-cache-architecture.md](./REF-cache-architecture.md) - Cache-aware batching
- [TDD-0005: Batch API](../design/TDD-0005-batch-api.md)
- [ADR-0010: Batch Chunking Strategy](../decisions/ADR-0010-batch-chunking-strategy.md)
- [ADR-0039: Batch Execution Strategy](../decisions/ADR-0039-batch-execution-strategy.md)
- [ADR-0040: Partial Failure Handling](../decisions/ADR-0040-partial-failure-handling.md)
