# ADR-0010: Sequential Chunk Execution for Batch Operations

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0001 (FR-SDK-030-034), TDD-0005

## Context

The autom8_asana SDK needs to implement batch operations per PRD-0001 requirements FR-SDK-030 through FR-SDK-034. The Asana Batch API (`POST /batch`) has a hard limit of 10 actions per request. When users submit more than 10 actions, the SDK must split them into multiple API calls.

The question is: how should these chunks be executed?

**Forces at play:**
1. **Rate Limiting**: Asana enforces 1500 requests/minute. Each batch counts as one request regardless of action count.
2. **Error Handling**: If a chunk fails mid-execution, partial state exists. Users need to know which actions succeeded.
3. **Ordering Guarantees**: Users may expect actions to execute in order (e.g., create parent before child).
4. **Throughput**: Parallel execution would be faster for large batches.
5. **Complexity**: Parallel execution requires more sophisticated error handling and result assembly.
6. **Existing Patterns**: The SDK uses sequential execution for all other operations.

## Decision

Execute batch chunks **sequentially** (one at a time), not in parallel.

When a user submits N > 10 batch requests:
1. Split into ceil(N/10) chunks
2. Execute chunk 1, wait for response
3. Execute chunk 2, wait for response
4. ... continue until all chunks complete
5. Assemble results in original request order

## Rationale

### Why Sequential Over Parallel

1. **Simpler Error Handling**
   - If chunk 2 fails, we know chunks 1's results are stable
   - No race conditions in result assembly
   - Clear point of failure for user recovery

2. **Predictable Ordering**
   - Actions execute in the order submitted
   - Critical for dependent operations (create project, then add tasks)
   - Matches user mental model

3. **Rate Limit Safety**
   - Existing rate limiter naturally throttles chunk execution
   - No risk of burst that could trigger 429s
   - Each chunk waits its turn in the rate limiter

4. **Consistency with SDK**
   - All other SDK operations are sequential
   - Same patterns for error handling and logging
   - No new concurrency primitives needed

5. **Sufficient Performance**
   - 10 actions per request is already 10x more efficient than individual calls
   - 100 actions = 10 requests, not 100
   - Sub-second execution for typical batch sizes

### When Parallel Might Be Better

Parallel would outperform sequential when:
- Actions are completely independent (no ordering requirements)
- Batch sizes are very large (1000+ actions)
- Rate limit headroom is abundant
- User explicitly opts into parallel mode

These scenarios are uncommon for the initial use cases. We can add an optional `parallel=True` parameter in a future version if demand warrants.

## Alternatives Considered

### Alternative 1: Parallel Chunk Execution

- **Description**: Execute all chunks concurrently using asyncio.gather()
- **Pros**:
  - Maximum throughput
  - Better for very large batches
  - Utilizes available rate limit capacity
- **Cons**:
  - Complex error handling (some chunks succeed, some fail)
  - Result assembly requires tracking chunk origins
  - No ordering guarantees
  - Could spike rate limit usage
  - Harder to debug and reason about
- **Why not chosen**: Complexity outweighs benefits for typical use cases; can add as opt-in later

### Alternative 2: Configurable Strategy

- **Description**: Let users choose between sequential and parallel via a parameter
- **Pros**:
  - Maximum flexibility
  - Users can optimize for their use case
- **Cons**:
  - More API surface to maintain
  - More documentation needed
  - Users must understand tradeoffs
  - Premature optimization
- **Why not chosen**: YAGNI - start simple, add complexity when proven necessary

### Alternative 3: Smart Batching (Dependency Analysis)

- **Description**: Analyze actions for dependencies, parallelize independent chunks
- **Pros**:
  - Best of both worlds
  - Optimal performance with safety
- **Cons**:
  - Very complex to implement
  - Dependency detection is imperfect (SDK can't know semantic dependencies)
  - Significant maintenance burden
- **Why not chosen**: Over-engineering for the problem at hand

## Consequences

### Positive
- Simple, predictable execution model
- Easy to debug and reason about
- Consistent with existing SDK patterns
- Safe default for all use cases
- Clear error recovery path (retry from failed chunk)

### Negative
- Suboptimal throughput for large, independent batches
- May underutilize rate limit capacity
- Users wanting parallelism must implement it themselves (or wait for future enhancement)

### Neutral
- Sequential execution means total batch time = sum of chunk times
- For 50 actions (5 chunks), expect ~500ms-1s total (vs ~200ms parallel)
- This is still 10x better than 50 individual requests

## Compliance

How do we ensure this decision is followed?

1. **Code Review**: BatchClient implementation must use sequential execution
2. **Unit Test**: Test that chunks execute in order (mock HTTP client tracks call order)
3. **Documentation**: API docs explain sequential execution and ordering guarantees
4. **Future Changes**: Adding parallel mode requires new ADR and explicit opt-in parameter
