# ADR-0039: Fixed-Size Sequential Batch Execution

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0005 (FR-BATCH-001 through FR-BATCH-009), TDD-0010, ADR-0010

## Context

The Save Orchestration Layer must execute batched operations via the Asana Batch API. ADR-0010 established sequential chunk execution for batch operations. PRD-0005 requires batching by dependency level with a maximum of 10 operations per batch (Asana's limit).

**Forces at play:**

1. **Asana Limit**: Hard limit of 10 actions per batch request
2. **ADR-0010 Compliance**: Chunks execute sequentially (not in parallel)
3. **Dependency Order**: Entities at level N must complete before level N+1 starts
4. **Rate Limiting**: Existing TokenBucketRateLimiter handles throttling
5. **Result Correlation**: Must map results back to originating entities
6. **BatchClient Reuse**: Existing BatchClient handles chunking and execution

**Problem**: How should SavePipeline execute batches across dependency levels?

## Decision

Use **fixed-size batches of 10, executed sequentially per dependency level**, delegating to existing BatchClient.

Execution strategy:
1. Group entities by dependency level (from DependencyGraph)
2. For each level (in order):
   a. Build BatchRequest objects for all entities at this level
   b. Pass to BatchClient.execute_async() (handles chunking into 10s)
   c. Correlate BatchResult back to entities
   d. Update GID map for new entities (for next level's reference resolution)
   e. Proceed to next level only after current level completes
3. Aggregate all results into SaveResult

```python
async def execute(self, entities: list[Entity]) -> SaveResult:
    levels = self._graph.get_levels()
    gid_map: dict[str, str] = {}  # temp_xxx -> real_gid

    for level in levels:
        # Build requests with GID resolution
        requests = [self._build_request(e, gid_map) for e in level]

        # BatchClient handles chunking (ADR-0010)
        results = await self._batch_client.execute_async(requests)

        # Correlate and update GID map
        for entity, result in zip(level, results):
            if result.success and is_create(entity):
                gid_map[f"temp_{id(entity)}"] = result.data["gid"]

    return aggregate_results(...)
```

## Rationale

### Why Fixed Batch Size of 10

1. **Asana Limit**: Batch API enforces maximum 10 actions per request
2. **BatchClient Handles It**: Existing chunking logic in BatchClient is proven
3. **No Configuration Needed**: Hard limit means no user configuration
4. **Predictable**: Always 10, never varies

### Why Sequential Per Level

1. **Dependency Order**: Level N+1 may reference GIDs created in level N
2. **GID Resolution**: Must know parent's real GID before creating subtask
3. **ADR-0010 Compliance**: Already established sequential pattern
4. **Simpler Error Handling**: Know exactly where failures occur

### Why Delegate to BatchClient

1. **Code Reuse**: BatchClient already implements chunking, execution, correlation
2. **Rate Limiting**: BatchClient integrates with TokenBucketRateLimiter
3. **Error Handling**: BatchClient's BatchResult model is proven
4. **Consistency**: Same execution path as direct batch operations

### GID Resolution Between Levels

When level 0 creates a parent and level 1 creates subtasks:

```
Level 0: parent_task (gid=None -> POST -> gid="123")
         gid_map["temp_999"] = "123"

Level 1: subtask (parent=temp_999)
         resolve: parent="123"
         POST with parent="123"
```

This requires sequential level execution - cannot parallelize across levels.

## Alternatives Considered

### Alternative 1: Parallel Level Execution

- **Description**: Execute all levels concurrently using asyncio.gather()
- **Pros**: Maximum throughput, better for independent operations
- **Cons**:
  - Cannot resolve GIDs across levels
  - Violates dependency ordering
  - Would fail for any parent-child relationship
- **Why not chosen**: Fundamentally breaks dependency ordering

### Alternative 2: Configurable Batch Size

- **Description**: Allow user to configure batch size (1-10)
- **Pros**: Flexibility for debugging, rate limit management
- **Cons**:
  - Complexity with no clear benefit
  - 10 is always optimal (fewer requests)
  - Could confuse users
- **Why not chosen**: YAGNI; 10 is always correct answer

### Alternative 3: Custom Batch Client

- **Description**: Implement new batching logic specific to save orchestration
- **Pros**: Full control, could optimize for save patterns
- **Cons**:
  - Code duplication
  - Different behavior than direct batch calls
  - More maintenance
- **Why not chosen**: Existing BatchClient is sufficient

### Alternative 4: Single Mega-Batch

- **Description**: Collect all operations across levels, execute as one batch sequence
- **Pros**: Simpler loop, single BatchClient call
- **Cons**:
  - Loses level boundaries
  - Cannot resolve GIDs between operations in same batch
  - Asana batch doesn't support cross-reference within batch
- **Why not chosen**: GID resolution requires sequential levels

### Alternative 5: Parallel Within Level, Sequential Across

- **Description**: Execute multiple batches within same level in parallel
- **Pros**: Better throughput for large levels (e.g., 100 independent tasks)
- **Cons**:
  - More complex error handling
  - ADR-0010 established sequential pattern
  - Rate limit concerns
  - Out of scope for v1 (PRD exclusions)
- **Why not chosen**: PRD explicitly excludes parallel level execution; can add later if needed

## Consequences

### Positive
- Leverages proven BatchClient implementation
- Correct GID resolution across dependency levels
- Consistent with ADR-0010 sequential pattern
- Simple mental model: level by level, batch by batch
- Predictable execution order aids debugging

### Negative
- Sequential execution slower than theoretical parallel maximum
- Large single levels (>10 entities) require multiple round trips
- Cannot optimize independent operations across levels

### Neutral
- Batch size is always 10 (Asana's limit)
- Rate limiting handled transparently by BatchClient
- Result correlation uses BatchResult's request_index

## Compliance

How do we ensure this decision is followed?

1. **Implementation**: BatchExecutor delegates to BatchClient.execute_async()
2. **Unit Tests**: Verify level-by-level execution order
3. **Integration Tests**: Verify GID resolution across levels
4. **No Parallelism**: Code review rejects concurrent level execution
5. **Documentation**: Explain sequential execution and performance characteristics
