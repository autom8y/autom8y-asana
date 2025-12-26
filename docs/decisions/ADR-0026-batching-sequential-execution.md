# ADR-0026: Batching and Sequential Execution

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0010, ADR-0015, ADR-0039
- **Related**: PRD-0001 (FR-SDK-030-034), PRD-0005 (FR-BATCH-001 through FR-BATCH-009), TDD-0005, TDD-0010

## Context

The Asana Batch API provides efficient bulk operations with a hard limit of 10 actions per request. When users submit more than 10 operations, the SDK must split them into multiple chunks and execute them. This decision addresses three key aspects of batch execution:

1. **Chunk size**: How many actions per batch request
2. **Execution strategy**: Sequential vs parallel chunk execution
3. **Request format**: How to structure batch requests for Asana API

**Forces at play**:
- Asana enforces 1500 requests/minute and 10 actions per batch
- Rate limiter naturally throttles request execution
- Dependent operations require ordering (create parent before child)
- Error handling is simpler with clear failure points
- Performance vs complexity tradeoff for parallel execution
- Consistency with established SDK patterns

## Decision

**Execute batch operations as fixed-size chunks of 10 actions, processed sequentially, with correct API envelope format.**

### Chunk Execution Strategy

When a user submits N > 10 batch requests:
1. Split into ceil(N/10) chunks of max 10 actions each
2. Execute chunk 1, wait for response
3. Execute chunk 2, wait for response
4. Continue sequentially until all chunks complete
5. Assemble results in original request order

```python
async def execute_batch(requests: list[Request]) -> list[Result]:
    """Execute batch in sequential chunks of 10."""
    chunks = [requests[i:i+10] for i in range(0, len(requests), 10)]
    results = []

    for chunk in chunks:
        # Execute one chunk at a time
        chunk_results = await self._batch_client.execute_async(chunk)
        results.extend(chunk_results)

    return results
```

### Request Format

All batch requests use the correct Asana API envelope:

```python
# Correct format
response = await self._http.request(
    "POST",
    "/batch",
    json={"data": {"actions": actions}},
)
```

The outer `"data"` wrapper is required by Asana's Batch API convention, matching the response format where all data is wrapped in `{"data": ...}`.

### Save Orchestration Application

For dependency-ordered saves (parent-child relationships):
1. Group entities by dependency level from DependencyGraph
2. For each level (in order):
   - Build BatchRequest objects for all entities at this level
   - Pass to BatchClient.execute_async() (handles chunking into 10s)
   - Correlate BatchResult back to entities
   - Update GID map for new entities (for next level's reference resolution)
   - Proceed to next level only after current level completes
3. Aggregate all results into SaveResult

## Rationale

### Why Sequential Over Parallel

**Simpler error handling**:
- If chunk 2 fails, we know chunk 1's results are stable
- No race conditions in result assembly
- Clear point of failure for user recovery

**Predictable ordering**:
- Actions execute in the order submitted
- Critical for dependent operations (create project, then add tasks)
- Matches user mental model

**Rate limit safety**:
- Existing rate limiter naturally throttles chunk execution
- No risk of burst that could trigger 429 errors
- Each chunk waits its turn in the rate limiter

**Consistency with SDK**:
- All other SDK operations are sequential
- Same patterns for error handling and logging
- No new concurrency primitives needed

**Sufficient performance**:
- 10 actions per request is already 10x more efficient than individual calls
- 100 actions = 10 requests, not 100
- Sub-second execution for typical batch sizes
- For 50 actions (5 chunks): ~500ms-1s total vs ~200ms theoretical parallel (still 10x better than 50 individual requests)

### Why Fixed Size of 10

**Asana hard limit**:
- Batch API enforces maximum 10 actions per request
- Not configurable by users
- Hard limit means no user configuration needed

**BatchClient delegation**:
- Existing chunking logic in BatchClient is proven
- Code reuse across direct batch operations and save orchestration
- Consistent execution path

**Predictability**:
- Always 10, never varies
- Easy to reason about performance characteristics

### Why Sequential Level Execution in Save Operations

**GID resolution requirements**:
- Level N+1 may reference GIDs created in level N
- Must know parent's real GID before creating subtask
- Cannot parallelize across levels

Example:
```
Level 0: parent_task (gid=None -> POST -> gid="123")
         gid_map["temp_999"] = "123"

Level 1: subtask (parent=temp_999)
         resolve: parent="123"
         POST with parent="123"
```

**Dependency ordering**:
- Entities at level N must complete before level N+1 starts
- Fundamental to dependency graph correctness
- Violations would fail at API level

### Why Correct Request Format

**API compliance**:
- Asana Batch API requires `{"data": {"actions": [...]}}`
- Without outer wrapper: HTTP 400 Bad Request
- Matches Asana's response format convention

**Asymmetry in HTTP client**:
- HTTP client automatically unwraps `"data"` from responses
- Does not automatically wrap request bodies
- This asymmetry requires explicit wrapping in batch operations

## Alternatives Considered

### Alternative 1: Parallel Chunk Execution

**Description**: Execute all chunks concurrently using `asyncio.gather()`.

**Pros**:
- Maximum throughput for large independent batches
- Better utilizes available rate limit capacity

**Cons**:
- Complex error handling (some chunks succeed, some fail)
- Result assembly requires tracking chunk origins
- No ordering guarantees
- Could spike rate limit usage
- Harder to debug and reason about

**Why not chosen**: Complexity outweighs benefits for typical use cases. Can add as opt-in later if demand warrants.

### Alternative 2: Configurable Batch Size

**Description**: Allow user to configure batch size (1-10).

**Pros**:
- Flexibility for debugging
- Rate limit management

**Cons**:
- Complexity with no clear benefit
- 10 is always optimal (fewer requests)
- Could confuse users

**Why not chosen**: YAGNI. 10 is always the correct answer per Asana's limit.

### Alternative 3: Parallel Level Execution in Saves

**Description**: Execute all dependency levels concurrently using `asyncio.gather()`.

**Pros**:
- Maximum throughput
- Better for independent operations

**Cons**:
- Cannot resolve GIDs across levels
- Violates dependency ordering
- Would fail for any parent-child relationship
- Fundamentally breaks save semantics

**Why not chosen**: Fundamentally incompatible with dependency ordering requirements.

### Alternative 4: Custom Batch Client for Saves

**Description**: Implement new batching logic specific to save orchestration.

**Pros**:
- Full control
- Could optimize for save patterns

**Cons**:
- Code duplication
- Different behavior than direct batch calls
- More maintenance

**Why not chosen**: Existing BatchClient is sufficient; delegation provides consistency.

## Consequences

### Positive

- **Simple, predictable execution**: Level-by-level, chunk-by-chunk mental model
- **Easy to debug**: Clear execution order aids troubleshooting
- **Consistent patterns**: Matches established SDK patterns
- **Safe default**: Works correctly for all use cases including dependent operations
- **Clear error recovery**: Retry from failed chunk or level
- **Code reuse**: Single BatchClient implementation serves all use cases
- **Correct API format**: No 400 errors from missing envelope

### Negative

- **Suboptimal throughput for large independent batches**: 100 independent actions = 10 sequential requests (~1s) vs theoretical ~200ms parallel
- **May underutilize rate limit capacity**: Sequential execution leaves capacity unused
- **Users wanting parallelism must implement themselves**: Or wait for future enhancement

### Neutral

- **Sequential execution time**: Total batch time = sum of chunk times
- **Batch size always 10**: Asana's limit, not configurable
- **Rate limiting transparent**: Handled by existing rate limiter
- **Result correlation**: Uses BatchResult's request_index

## Performance Characteristics

### Throughput

| Scenario | Individual Requests | Sequential Batching | Improvement |
|----------|---------------------|---------------------|-------------|
| 50 task updates | 50 requests (~5s) | 5 batch requests (~500ms) | 10x fewer requests |
| 100 staleness checks | 100 GET requests (~10s) | 10 batch requests (~1s) | 10x fewer requests |
| Parent + 50 subtasks | 51 requests (serial) | 1 + 5 batch requests (level-sequential) | 8.5x improvement |

### Latency

- Single batch (≤10 actions): ~100ms
- 50 actions (5 chunks): ~500ms
- 100 actions (10 chunks): ~1s
- Rate limiter may add throttling delay under heavy load

## Compliance

To ensure this decision is followed:

1. **Code Review**:
   - BatchClient implementation uses sequential execution
   - All batch requests use `{"data": {"actions": [...]}}` envelope
   - SavePipeline delegates to BatchClient.execute_async()
   - No parallel chunk execution without explicit ADR

2. **Unit Tests**:
   - Test chunks execute in order (mock HTTP client tracks call order)
   - Test batch request format includes outer `data` wrapper
   - Test GID resolution across dependency levels
   - Test result correlation to original request order

3. **Integration Tests**:
   - Verify batch operations with real Asana API
   - Validate parent-child creation scenarios
   - Confirm no 400 errors from request format

4. **Documentation**:
   - API docs explain sequential execution and ordering guarantees
   - Document performance characteristics (10x vs individual)
   - Explain dependency level execution for save operations

5. **Future Changes**:
   - Adding parallel mode requires new ADR and explicit opt-in parameter
   - Changing batch size requires ADR (though Asana limit makes this unlikely)

## Cross-References

- **ADR-0025**: Async-first pattern used for batch execution
- **ADR-0132**: Request coalescing uses batch API following this pattern
- **ADR-SUMMARY-SAVESESSION**: Save orchestration applies these batching principles
- **ADR-SUMMARY-CACHE**: Batch modification checking uses sequential batching
