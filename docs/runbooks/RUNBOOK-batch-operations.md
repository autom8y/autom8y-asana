# Batch Operations Troubleshooting Runbook

## Quick Diagnosis

| Symptom | Likely Cause | Jump To |
|---------|--------------|---------|
| Partial batch failures | Individual item validation, rate limiting, data issues | [Partial Failures](#problem-1-partial-batch-failures) |
| Entire batch fails | Auth issues, network errors, malformed requests | [Complete Failures](#problem-2-complete-batch-failures) |
| Rate limit errors (429) | Too many concurrent batches, batch size issues | [Rate Limiting](#problem-3-rate-limit-errors) |
| Slow batch execution | Sequential chunking, large payload size | [Performance Issues](#problem-4-slow-batch-execution) |
| Request/response mismatch | Index correlation errors, chunking bugs | [Index Correlation](#problem-5-requestresponse-index-mismatch) |

## Overview

The Batch API client (`autom8_asana.batch.BatchClient`) enables efficient bulk operations by batching multiple requests into single API calls. Key features:

- **Auto-chunking**: Splits requests into groups of 10 (Asana's limit)
- **Sequential execution**: Processes chunks one at a time for rate limit compliance
- **Partial failure handling**: Individual failures don't fail the entire batch
- **Result correlation**: Preserves request order using `request_index`

**When to use this runbook**: When batch operations produce unexpected results, failures, or performance issues.

**Related documentation**:
- `/src/autom8_asana/batch/client.py` - BatchClient implementation
- `/src/autom8_asana/batch/models.py` - BatchRequest, BatchResult, BatchSummary
- [TDD-0005: Batch API for Bulk Operations](../design/TDD-0005-batch-api.md)
- [ADR-0010: Sequential chunk execution](../decisions/ADR-0010-batch-sequential-chunks.md)

---

## Problem 1: Partial Batch Failures

### Symptoms
- `BatchSummary.all_succeeded` is `False`
- Some `BatchResult` items have `success=False`
- Logs show "X succeeded, Y failed" for batch chunks
- Error messages in `BatchResult.error`

### Investigation Steps

1. **Identify which requests failed**
   ```python
   results = await client.batch.execute_async(requests)

   for i, result in enumerate(results):
       if not result.success:
           print(f"Request {i} failed:")
           print(f"  Status: {result.status_code}")
           print(f"  Error: {result.error.message if result.error else 'Unknown'}")
           print(f"  Request: {requests[i].to_action_dict()}")
   ```

2. **Check error patterns**
   ```python
   # Group failures by status code
   from collections import Counter
   status_codes = Counter(
       r.status_code for r in results if not r.success
   )
   print(f"Failure patterns: {status_codes}")
   # Example output: {400: 5, 404: 2, 422: 1}
   ```

3. **Extract detailed error messages**
   ```python
   for result in results:
       if not result.success and result.error:
           print(f"Status {result.status_code}: {result.error.message}")
           # Check result.error.errors for full API error details
           if result.error.errors:
               for err in result.error.errors:
                   print(f"  - {err.get('message')}")
   ```

4. **Verify request payload**
   ```python
   # For failed requests, inspect what was sent
   failed_indices = [i for i, r in enumerate(results) if not r.success]
   for idx in failed_indices:
       action = requests[idx].to_action_dict()
       print(f"Failed action {idx}:")
       print(f"  Method: {action['method']}")
       print(f"  Path: {action['relative_path']}")
       print(f"  Data: {action.get('data', 'N/A')}")
   ```

### Resolution

**400 Bad Request failures**:
- **Cause**: Missing required fields, invalid field values
- **Fix**: Validate data before batching
  ```python
  # Required fields for task creation
  required = ["name", "projects"]
  for task_data in tasks:
      assert all(k in task_data for k in required), f"Missing required field: {task_data}"

  results = await client.batch.create_tasks_async(tasks)
  ```

**404 Not Found failures**:
- **Cause**: Task GIDs don't exist or were deleted
- **Fix**: Verify GIDs exist before batch update/delete
  ```python
  # Pre-validate GIDs (batch GET requests)
  verify_requests = [
      BatchRequest(f"/tasks/{gid}", "GET") for gid in task_gids
  ]
  verify_results = await client.batch.execute_async(verify_requests)

  valid_gids = [
      task_gids[i] for i, r in enumerate(verify_results) if r.success
  ]

  # Only update valid tasks
  updates = [(gid, data) for gid, data in updates if gid in valid_gids]
  ```

**422 Unprocessable Entity failures**:
- **Cause**: Business logic violations (e.g., circular dependencies, invalid custom field values)
- **Fix**: Check entity relationships and custom field constraints
  ```python
  # Common issues:
  # - Parent task cannot be descendant
  # - Custom field value not in enum options
  # - Project doesn't exist in workspace

  # Review API error details:
  for result in results:
      if result.status_code == 422:
          print(result.error.errors)  # Full validation details
  ```

**429 Rate Limit failures**:
- See [Problem 3: Rate Limit Errors](#problem-3-rate-limit-errors)

### Prevention
- Validate all request data before batching
- Use BatchSummary to track success/failure metrics
- Log failed operations for retry
- Implement pre-flight validation for critical operations

---

## Problem 2: Complete Batch Failures

### Symptoms
- Exception raised during `execute_async()` (not partial failures)
- No `BatchResult` objects returned
- Entire batch aborted mid-execution
- Network or authentication errors in logs

### Investigation Steps

1. **Check exception type**
   ```python
   try:
       results = await client.batch.execute_async(requests)
   except AsanaError as e:
       print(f"Batch endpoint failed: {e.status_code} - {e.message}")
       # 401: auth issue, 503: service unavailable, etc.
   except Exception as e:
       print(f"Unexpected error: {type(e).__name__} - {e}")
   ```

2. **Check authentication**
   ```python
   # Test with simple API call
   try:
       me = await client.users.me_async()
       print(f"Auth OK: {me.name}")
   except AuthenticationError:
       print("Auth token invalid or expired")
   ```

3. **Check network connectivity**
   ```bash
   # Test Asana API reachability
   curl -I https://app.asana.com/api/1.0/users/me \
     -H "Authorization: Bearer $ASANA_TOKEN"
   # Should return: HTTP/2 200
   ```

4. **Check request payload size**
   ```python
   import json
   payload = {"data": {"actions": [r.to_action_dict() for r in requests]}}
   size_bytes = len(json.dumps(payload).encode('utf-8'))
   print(f"Payload size: {size_bytes:,} bytes")

   # Asana limit: ~1MB per request
   if size_bytes > 900_000:  # 900KB safety margin
       print("WARNING: Payload too large, reduce batch size")
   ```

### Resolution

**401 Unauthorized**:
- **Cause**: Invalid or expired auth token
- **Fix**: Refresh authentication
  ```python
  # Verify token in environment
  import os
  token = os.getenv("ASANA_PERSONAL_ACCESS_TOKEN")
  assert token, "Token not set"

  # Recreate client with valid token
  client = AsanaClient(token=token)
  ```

**503 Service Unavailable**:
- **Cause**: Asana API temporarily down
- **Fix**: Implement retry with exponential backoff
  ```python
  import asyncio
  from autom8_asana.exceptions import ServerError

  max_retries = 3
  for attempt in range(max_retries):
      try:
          results = await client.batch.execute_async(requests)
          break
      except ServerError as e:
          if attempt < max_retries - 1:
              wait = 2 ** attempt  # Exponential backoff
              print(f"Server error, retrying in {wait}s...")
              await asyncio.sleep(wait)
          else:
              raise
  ```

**Payload too large**:
- **Cause**: Batch size or individual request data exceeds limits
- **Fix**: Reduce chunk size or split large payloads
  ```python
  # Reduce effective batch size (default is 10)
  SMALLER_CHUNK_SIZE = 5

  def chunk_smaller(requests, size=SMALLER_CHUNK_SIZE):
      return [requests[i:i+size] for i in range(0, len(requests), size)]

  all_results = []
  for chunk in chunk_smaller(requests):
      chunk_results = await client.batch.execute_async(chunk)
      all_results.extend(chunk_results)
  ```

**Network timeout**:
- **Cause**: Slow connection or large response
- **Fix**: Increase client timeout
  ```python
  from autom8_asana.config import AsanaConfig

  config = AsanaConfig(timeout=60.0)  # 60 second timeout
  client = AsanaClient(token=token, config=config)
  ```

### Prevention
- Monitor authentication token expiration
- Implement retry logic with backoff
- Validate payload size before sending
- Configure appropriate timeouts
- Add health checks before large batch operations

---

## Problem 3: Rate Limit Errors

### Symptoms
- 429 status code in results or exceptions
- "Rate limit exceeded" errors
- Batch operations slow down significantly
- Logs show repeated rate limit hits

### Investigation Steps

1. **Check if rate limit is per-batch or per-chunk**
   ```python
   # Rate limit can occur at two levels:
   # 1. Individual action within batch (429 in BatchResult)
   # 2. Batch endpoint itself (AsanaError 429)

   try:
       results = await client.batch.execute_async(requests)
       rate_limited = [r for r in results if r.status_code == 429]
       if rate_limited:
           print(f"{len(rate_limited)} actions rate-limited")
   except RateLimitError as e:
       print("Entire batch endpoint rate-limited")
   ```

2. **Check batch execution timing**
   ```python
   import time
   start = time.time()
   results = await client.batch.execute_async(requests)
   elapsed = time.time() - start

   # Sequential chunks: 10 actions/chunk, ~1s per API call
   expected_time = (len(requests) / 10) * 1.0
   print(f"Elapsed: {elapsed:.1f}s (expected ~{expected_time:.1f}s)")
   ```

3. **Check concurrent batch usage**
   ```python
   # Are multiple batches running concurrently?
   # This can trigger rate limits faster

   # DON'T DO THIS (concurrent batches):
   # tasks = [client.batch.execute_async(chunk) for chunk in chunks]
   # await asyncio.gather(*tasks)  # Can trigger rate limits

   # DO THIS (sequential batches):
   # for chunk in chunks:
   #     results = await client.batch.execute_async(chunk)
   ```

### Resolution

**Sequential batch execution**:
- **Cause**: Multiple concurrent batches hitting rate limits
- **Fix**: Execute batches sequentially
  ```python
  all_results = []
  for i, chunk in enumerate(request_chunks):
      print(f"Processing chunk {i+1}/{len(request_chunks)}")
      results = await client.batch.execute_async(chunk)
      all_results.extend(results)

      # Optional: small delay between chunks
      if i < len(request_chunks) - 1:
          await asyncio.sleep(0.5)  # 500ms between batches
  ```

**Respect rate limit headers**:
- **Cause**: Not honoring Asana rate limit indicators
- **Fix**: Check and respect rate limit headers
  ```python
  # Asana includes rate limit info in response headers
  # Check result.headers for:
  # - X-RateLimit-Limit: requests per minute
  # - X-RateLimit-Remaining: remaining requests
  # - X-RateLimit-Reset: timestamp when limit resets

  for result in results:
      if result.headers:
          remaining = result.headers.get('X-RateLimit-Remaining')
          if remaining and int(remaining) < 10:
              print(f"WARNING: Only {remaining} requests remaining")
              await asyncio.sleep(2)  # Back off
  ```

**Reduce batch frequency**:
- **Cause**: Too many batches in short time window
- **Fix**: Implement batch queuing
  ```python
  import asyncio
  from collections import deque

  batch_queue = deque(request_chunks)
  MIN_BATCH_INTERVAL = 1.0  # 1 second between batches

  all_results = []
  last_batch_time = 0

  while batch_queue:
      # Enforce minimum interval
      now = time.time()
      since_last = now - last_batch_time
      if since_last < MIN_BATCH_INTERVAL:
          await asyncio.sleep(MIN_BATCH_INTERVAL - since_last)

      chunk = batch_queue.popleft()
      results = await client.batch.execute_async(chunk)
      all_results.extend(results)
      last_batch_time = time.time()
  ```

### Prevention
- Never run concurrent batch operations
- Respect Asana's sequential chunk execution design
- Monitor rate limit headers proactively
- Implement batch queuing for high-volume operations
- Add delays between batches during off-peak processing

---

## Problem 4: Slow Batch Execution

### Symptoms
- Batch operations take much longer than expected
- Performance degraded compared to baseline
- Logs show long chunk processing times
- Users report timeout waiting for batch results

### Investigation Steps

1. **Profile batch execution**
   ```python
   import time

   start = time.time()
   results = await client.batch.execute_async(requests)
   total_time = time.time() - start

   print(f"Total time: {total_time:.2f}s")
   print(f"Requests: {len(requests)}")
   print(f"Chunks: {(len(requests) + 9) // 10}")
   print(f"Avg time per chunk: {total_time / ((len(requests) + 9) // 10):.2f}s")

   # Expected: ~1-2s per chunk (10 actions)
   # Slow: >5s per chunk
   ```

2. **Check payload size**
   ```python
   # Large payloads (complex task data, long notes, etc.) slow processing
   total_size = 0
   for req in requests:
       data_str = str(req.data or {})
       total_size += len(data_str)

   avg_size = total_size / len(requests)
   print(f"Average payload per request: {avg_size:.0f} chars")

   # Large: >10KB per request
   # Reduce by using opt_fields to limit response size
   ```

3. **Check opt_fields usage**
   ```python
   # Are you requesting too many fields in responses?
   for req in requests:
       if req.options:
           fields = req.options.get('opt_fields', '')
           print(f"Requesting fields: {fields}")

   # Minimize fields requested - only get what you need
   ```

4. **Check network latency**
   ```python
   # Test baseline API latency
   start = time.time()
   await client.tasks.get_async("some_task_gid")
   latency = time.time() - start
   print(f"Single API call latency: {latency:.2f}s")

   # High latency (>2s) indicates network issues
   ```

### Resolution

**Reduce payload size**:
- **Cause**: Large task data (notes, attachments metadata, custom fields)
- **Fix**: Limit response fields
  ```python
  # Only request essential fields
  essential_fields = ["gid", "name", "completed", "assignee"]

  results = await client.batch.create_tasks_async(
      tasks,
      opt_fields=essential_fields
  )

  # Saves bandwidth and processing time
  ```

**Optimize data preparation**:
- **Cause**: Inefficient pre-processing before batch
- **Fix**: Stream processing instead of loading all data
  ```python
  # DON'T: Load everything into memory
  # all_tasks = load_all_tasks_from_db()  # 10,000 tasks
  # results = await client.batch.create_tasks_async(all_tasks)

  # DO: Process in smaller batches
  BATCH_SIZE = 100
  offset = 0
  while True:
      batch_tasks = load_tasks_from_db(limit=BATCH_SIZE, offset=offset)
      if not batch_tasks:
          break

      results = await client.batch.create_tasks_async(batch_tasks)
      process_results(results)
      offset += BATCH_SIZE
  ```

**Parallel chunk execution (careful!)**:
- **Cause**: Sequential chunks too slow for very large batches
- **Fix**: Limited concurrency with rate limit awareness
  ```python
  import asyncio

  # ONLY use if you understand rate limit implications
  # Limit concurrency to 2-3 batches max
  MAX_CONCURRENT_BATCHES = 2

  async def process_batch_chunk(chunk):
      return await client.batch.execute_async(chunk)

  semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)

  async def limited_batch(chunk):
      async with semaphore:
          return await process_batch_chunk(chunk)

  chunks = [requests[i:i+10] for i in range(0, len(requests), 10)]
  results = await asyncio.gather(*[limited_batch(c) for c in chunks])
  all_results = [r for chunk_results in results for r in chunk_results]
  ```

### Prevention
- Profile batch operations to establish baselines
- Minimize response payload with opt_fields
- Process data in streaming fashion for large datasets
- Monitor chunk processing time
- Set realistic timeout expectations (1-2s per 10 actions)

---

## Problem 5: Request/Response Index Mismatch

### Symptoms
- BatchResult index doesn't match original request position
- Response data attributed to wrong request
- Index correlation errors in logs
- Unexpected data returned for operations

### Investigation Steps

1. **Verify request_index values**
   ```python
   results = await client.batch.execute_async(requests)

   for i, result in enumerate(results):
       assert result.request_index == i, \
           f"Index mismatch: expected {i}, got {result.request_index}"
   ```

2. **Check chunking boundary alignment**
   ```python
   # Verify chunks preserve order
   from autom8_asana.batch.client import _chunk_requests

   chunks = _chunk_requests(requests)
   print(f"Total requests: {len(requests)}")
   print(f"Chunks: {len(chunks)}")

   # Reconstruct and verify order
   reconstructed = []
   for chunk in chunks:
       reconstructed.extend(chunk)

   for i, req in enumerate(requests):
       assert reconstructed[i] is req, f"Order changed at {i}"
   ```

3. **Check for concurrent modification**
   ```python
   # Are requests being modified during execution?
   # This shouldn't happen (BatchRequest is frozen) but check:

   import copy
   original_requests = copy.deepcopy(requests)
   results = await client.batch.execute_async(requests)

   for i, (orig, current) in enumerate(zip(original_requests, requests)):
       if orig.to_action_dict() != current.to_action_dict():
           print(f"Request {i} was modified!")
   ```

### Resolution

**Order preservation issue**:
- **Cause**: Bug in chunking or result assembly
- **Fix**: This is a critical bug - report immediately
  ```python
  # Workaround: correlate by data payload
  for result in results:
      if result.success and result.data:
          # Match by response data to original request
          expected = requests[result.request_index]
          # Validate expected.relative_path matches operation
  ```

**Chunk boundary bug**:
- **Cause**: Off-by-one error in chunk processing
- **Fix**: Verify chunk base_index calculation
  ```python
  # Internal implementation check (for debugging):
  # base_index should increment by chunk size
  # Chunk 1: base_index=0, indices 0-9
  # Chunk 2: base_index=10, indices 10-19
  # etc.
  ```

### Prevention
- Always use request_index for correlation
- Never modify requests during execution
- Report any index mismatch as critical bug
- Add assertion checks in critical code paths

---

## Common Scenarios

### Scenario: Batch Create 100 Tasks

```python
from autom8_asana.batch import BatchClient

tasks_data = [
    {"name": f"Task {i}", "projects": ["project_gid"]}
    for i in range(100)
]

# Execute batch create
results = await client.batch.create_tasks_async(tasks_data)

# Check results
summary = BatchSummary(results=results)
print(f"Created: {summary.succeeded}/{summary.total}")

if not summary.all_succeeded:
    print(f"Failed: {summary.failed}")
    for result in summary.failed_results:
        print(f"  - {result.error.message if result.error else 'Unknown'}")

# Extract created task GIDs
created_gids = [
    r.data["gid"] for r in summary.successful_results
    if r.data
]
```

### Scenario: Batch Update with Partial Failures

```python
# Update 50 tasks - some may not exist
updates = [
    (f"task_gid_{i}", {"completed": True})
    for i in range(50)
]

results = await client.batch.update_tasks_async(updates)

# Separate successes and failures
succeeded = [r for r in results if r.success]
failed = [r for r in results if not r.success]

print(f"Updated: {len(succeeded)}")
print(f"Failed: {len(failed)}")

# Retry failures or log for manual review
for i, result in enumerate(failed):
    original_gid, update_data = updates[result.request_index]
    print(f"Failed to update {original_gid}: {result.status_code}")
```

### Scenario: Batch with Rate Limit Handling

```python
import asyncio

async def batch_with_retry(requests, max_retries=3):
    """Execute batch with automatic rate limit retry."""
    for attempt in range(max_retries):
        try:
            results = await client.batch.execute_async(requests)

            # Check for rate limit in results
            rate_limited = [r for r in results if r.status_code == 429]
            if rate_limited and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Rate limited, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue

            return results

        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Batch rate limited, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise

    return results

# Use it
results = await batch_with_retry(requests)
```

---

## Debugging Checklist

When troubleshooting batch operations, work through this checklist:

- [ ] Check individual request validity (required fields, valid GIDs)
- [ ] Verify authentication token is valid
- [ ] Confirm network connectivity to Asana API
- [ ] Check payload size (individual requests and total batch)
- [ ] Review opt_fields to minimize response size
- [ ] Verify sequential batch execution (no concurrent batches)
- [ ] Check rate limit headers in responses
- [ ] Validate request_index correlation
- [ ] Profile execution time per chunk
- [ ] Review error messages in BatchResult.error
- [ ] Check for 400, 404, 422, 429 patterns in failures
- [ ] Monitor chunk processing in logs
- [ ] Verify BatchSummary statistics match expectations

---

## Related Documentation

- [Batch API Client Implementation](/src/autom8_asana/batch/client.py)
- [Batch Models](/src/autom8_asana/batch/models.py)
- [Batch API Tests](/tests/unit/test_batch_adversarial.py)
- [REF-batch-operations](../reference/REF-batch-operations.md)
- [TDD-0005: Batch API Design](../design/TDD-0005-batch-api.md)
- [ADR-0010: Sequential Chunk Execution](../decisions/ADR-0010-batch-sequential-chunks.md)
