# ADR-0041: SaveSession Dependency Ordering & Concurrency Model

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-10
- **Consolidated From**: ADR-0037, ADR-0038
- **Related**: [reference/SAVESESSION.md](/Users/tomtenuta/Code/autom8_asana/docs/decisions/reference/SAVESESSION.md), PRD-0005, TDD-0010

## Context

The Save Orchestration Layer must handle two critical concerns:

1. **Dependency Ordering**: When creating task hierarchies, parent tasks must be saved before subtasks because subtasks reference the parent's GID. The orchestrator must automatically determine correct save order and detect circular dependencies.

2. **Concurrency Model**: Batch operations involve multiple HTTP requests. The SDK needed a consistent concurrency pattern that works for both async and sync callers while enabling non-blocking I/O.

Forces at play:
- Correctness: Parents must save before children, always
- Cycle detection: Circular dependencies must be detected and rejected
- Performance: O(V+E) complexity target for dependency resolution
- Level grouping: Independent entities at same level can batch together
- Determinism: Same input should produce same order (testing/debugging)
- Consistency: Must align with SDK's async-first pattern (ADR-0002)
- Compatibility: Support both async and sync callers

## Decision

### Kahn's Algorithm for Dependency Ordering

Use Kahn's algorithm for topological sorting of the dependency graph:

```python
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

    # Cycle detection: if not all nodes processed, cycle exists
    if len(result) != len(self._entities):
        remaining = set(self._entities.keys()) - set(e.gid for e in result)
        raise CyclicDependencyError(
            f"Circular dependency detected among: {remaining}"
        )

    return result
```

**Algorithm Properties:**
- O(V+E) complexity (V = vertices/entities, E = edges/dependencies)
- Natural cycle detection (incomplete sort indicates cycle)
- BFS-based (iterative, no recursion stack limits)
- Deterministic with consistent queue ordering

**Dependency Detection:**
- **Parent Field**: `task.parent` creates edge parent → task
- **Project Field**: `task.projects` creates edge project → task (if project is new)
- **Section Field**: `task.memberships` creates edge section → task (if section is new)

### Async-First Concurrency with Sync Wrappers

Implement async-first pattern consistent with ADR-0002:

```python
class SaveSession:
    # Primary async implementation
    async def commit_async(self) -> SaveResult:
        """Commit tracked changes asynchronously."""
        # Dependency ordering
        entities = self._dependency_graph.topological_sort()

        # Execute via async BatchClient
        results = await self._batch_client.execute_async(operations)

        return SaveResult(succeeded=..., failed=...)

    # Sync wrapper
    @sync_wrapper
    def commit(self) -> SaveResult:
        """Commit tracked changes synchronously."""
        return self.commit_async()
```

**Concurrency Characteristics:**
- `commit_async()` is primary implementation
- `commit()` uses `@sync_wrapper` decorator
- Context manager supports both `async with` and `with`
- All internal batch operations use async BatchClient
- Non-blocking I/O for batch operations

### Level Grouping for Parallel Batching

Extend Kahn's algorithm to group entities by dependency level:

```python
def get_levels(self) -> list[list[Entity]]:
    """Group entities by dependency level for parallel execution.

    Returns:
        List of levels, where each level contains independent entities
    """
    levels = []
    in_degree = dict(self._in_degree)
    remaining = set(self._entities.keys())

    while remaining:
        # All nodes with current in-degree 0 are independent
        level = [gid for gid in remaining if in_degree[gid] == 0]
        levels.append([self._entities[gid] for gid in level])

        # Remove level and update in-degrees
        for gid in level:
            remaining.remove(gid)
            for dependent in self._adjacency[gid]:
                in_degree[dependent] -= 1

    return levels
```

**Level Properties:**
- Level 0: No dependencies (can execute immediately)
- Level 1: Depends only on Level 0 entities
- Level N: Depends on entities in levels 0 through N-1
- Entities within same level can batch together safely

## Rationale

### Why Kahn's Algorithm

1. **Optimal Complexity**: O(V+E) is optimal for this problem
2. **Natural Cycle Detection**: If not all nodes processed, cycle exists (no separate pass needed)
3. **Level Grouping**: Easy to extend for parallel batching (nodes at same level independent)
4. **BFS-Based**: Iterative implementation avoids recursion stack limits
5. **Deterministic**: With consistent queue ordering (sorted), output is deterministic
6. **Well-Known**: Standard algorithm, easy to verify correctness

**Rejected Alternative: DFS-Based Topological Sort**
- Requires tracking "visiting" vs "visited" states for cycle detection
- Returns reverse post-order (needs reversal)
- Recursion can hit stack limits for deep graphs
- More complex cycle detection (back edge detection)
- Level grouping less natural

### Why Async-First Pattern

1. **SDK Consistency**: Aligns with ADR-0002 established pattern
2. **Non-Blocking I/O**: Critical for batch operations with multiple HTTP requests
3. **Modern Python**: Asyncio is standard for I/O-bound operations
4. **Caller Flexibility**: Works for both async and sync callers via wrappers
5. **Natural Integration**: BatchClient is already async-first

**Rejected Alternative: Sync-First**
- Would force async callers to use separate API
- Blocking I/O poor for batch operations
- Inconsistent with SDK pattern
- Cannot efficiently batch multiple HTTP requests

## Alternatives Considered

### Alternative 1: Simple Dependency Resolution (No Graph)

**Description**: Save parents first by checking if `entity.parent` is in pending set.

**Pros**: Very simple for shallow hierarchies

**Cons**:
- O(n²) worst case complexity
- Doesn't scale to complex dependency patterns
- No cycle detection
- No level grouping for parallel execution
- Breaks with multiple dependency types

**Why not chosen**: Poor scalability and no cycle detection violates requirements.

### Alternative 2: Tarjan's Strongly Connected Components

**Description**: Find SCCs, then topologically sort the component graph.

**Pros**: Handles more complex cycle structures, optimal complexity

**Cons**:
- Over-engineering for simple DAG requirement
- More complex implementation
- We only need to detect and reject cycles, not analyze them
- No benefit over Kahn's for acyclic graphs

**Why not chosen**: Unnecessary complexity when Kahn's provides simpler solution.

### Alternative 3: User-Specified Order

**Description**: Require user to pass entities in correct dependency order.

**Pros**: No algorithm needed, user has full control

**Cons**:
- Terrible developer experience
- Error-prone (easy to get order wrong)
- Defeats purpose of orchestration layer
- No cycle detection

**Why not chosen**: Violates "automatic dependency ordering" requirement.

### Alternative 4: Threading for Concurrency

**Description**: Use threads instead of async for parallel execution.

**Pros**: Familiar threading model, works with sync code

**Cons**:
- Inconsistent with ADR-0002 async-first pattern
- Thread overhead for I/O-bound operations
- GIL limitations in CPython
- More complex error handling
- Doesn't integrate with async ecosystem

**Why not chosen**: Async is better fit for I/O-bound batch operations.

### Alternative 5: Synchronous Only

**Description**: Only provide sync API, no async support.

**Pros**: Simpler implementation, one code path

**Cons**:
- Blocks on HTTP requests
- Poor performance for large batches
- Inconsistent with SDK pattern
- Forces async applications to use sync code

**Why not chosen**: Blocking I/O unacceptable for batch operations.

## Consequences

### Positive

- **Optimal Performance**: O(V+E) complexity meets performance requirements
- **Automatic Ordering**: Developers don't manually sort dependencies
- **Cycle Detection**: Circular dependencies caught and reported clearly
- **Parallel Batching**: Level grouping enables safe concurrent execution
- **Deterministic**: Same input produces same order (aids testing)
- **Non-Blocking**: Async I/O prevents blocking on batch operations
- **Caller Flexibility**: Works for both async and sync callers
- **SDK Consistency**: Aligns with established async-first pattern

### Negative

- **Graph Memory**: Explicit graph structure required (overhead for large batches)
- **Rebuild on Change**: Graph must rebuild if entities change between preview/commit
- **Generic Cycle Errors**: Complex cycles produce generic error (not detailed path)
- **Thread Unsafe**: SaveSession documented as single-thread/coroutine use
- **Learning Curve**: Developers must understand async patterns

### Neutral

- **Directed Edges**: Graph edges represent dependency → dependent relationship
- **Placeholder GIDs**: temp_xxx used for new entities in graph
- **Level Semantics**: Level 0 = no deps, Level N = depends on 0 through N-1
- **Async Primary**: Sync wrapper adds minimal overhead via event loop

## Compliance

### Enforcement

1. **Implementation**: DependencyGraph class uses Kahn's algorithm exclusively
2. **Code Review**: Algorithm changes require ADR update
3. **Type Checking**: mypy validates async/sync signatures
4. **Performance Benchmarks**: CI verifies O(V+E) scaling

### Testing

**Unit Tests Verify:**
- Empty graph handled correctly
- Single entity (no dependencies)
- Linear chain (A → B → C)
- Diamond structure (A → B, A → C, B → D, C → D)
- Cycle detection (A → B → A)
- Complex cycles (A → B → C → A)
- Level grouping accuracy

**Performance Tests:**
- 1000-entity graphs complete within target time
- Level grouping provides expected parallelism
- Memory usage scales linearly

**Concurrency Tests:**
- Async usage with async context manager
- Sync usage with sync context manager
- Mixed async/sync in application (not same session)

## Implementation Guidance

### Dependency Graph Usage

**Building Graph:**
```python
# Automatic graph construction during track()
session.track(parent_task)
session.track(child_task)  # child.parent = parent_task

# Graph automatically detects: parent → child edge
```

**Detecting Cycles:**
```python
try:
    result = await session.commit_async()
except CyclicDependencyError as e:
    # Handle circular dependency
    print(f"Cycle detected: {e}")
```

**Level Grouping:**
```python
# Internal usage for parallel batching
levels = dependency_graph.get_levels()
for level in levels:
    # Entities in this level can execute in parallel
    await batch_client.execute_async(level)
```

### Concurrency Patterns

**Async Usage (Recommended):**
```python
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    result = await session.commit_async()
```

**Sync Usage (Compatibility):**
```python
with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    result = session.commit()
```

**Mixed Application:**
```python
# Async route handler
async def update_tasks():
    async with SaveSession(client) as session:
        # ... async operations

# Sync CLI command
def update_tasks_cli():
    with SaveSession(client) as session:
        # ... sync operations
```

## Cross-References

**Related ADRs:**
- ADR-0040: Unit of Work Pattern (provides track/commit foundation)
- ADR-0042: Error Handling (handles dependency cascade failures)
- ADR-0043: Action Operations (uses level grouping for action execution)

**Related Documents:**
- PRD-0005: Save Orchestration Layer requirements
- TDD-0010: Save Orchestration technical design
- REF-batch-operations: Batch API integration details
