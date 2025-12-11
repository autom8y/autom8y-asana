# ADR-0037: Kahn's Algorithm for Dependency Ordering

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0005 (FR-DEPEND-001 through FR-DEPEND-009), TDD-0010

## Context

The Save Orchestration Layer must save entities in dependency order. When creating a task hierarchy, parent tasks must be saved before subtasks because subtasks reference the parent's GID. The orchestrator must automatically determine this order.

**Forces at play:**

1. **Correctness**: Parents must save before children, always
2. **Cycle Detection**: Circular dependencies must be detected and rejected
3. **Performance**: O(V+E) complexity target per NFR-PERF-005
4. **Level Grouping**: Independent entities at same level can batch together
5. **Determinism**: Same input should produce same order (for testing/debugging)
6. **Simplicity**: Algorithm should be well-understood and maintainable

**Problem**: Which algorithm should we use for topological sorting with cycle detection?

## Decision

Use **Kahn's algorithm** for topological sorting of the dependency graph.

Kahn's algorithm:
1. Calculate in-degree (number of incoming edges) for each node
2. Add all nodes with in-degree 0 to a queue
3. While queue is not empty:
   - Remove node from queue, add to result
   - For each neighbor, decrement in-degree
   - If neighbor's in-degree becomes 0, add to queue
4. If result contains all nodes, order is valid; otherwise, cycle exists

```python
def topological_sort(self) -> list[Entity]:
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

    if len(result) != len(self._entities):
        raise CyclicDependencyError(...)

    return result
```

## Rationale

### Why Kahn's Algorithm

1. **O(V+E) Complexity**: Optimal for this problem
2. **Natural Cycle Detection**: If not all nodes processed, cycle exists
3. **Level Grouping**: Easy to extend for parallel batching (nodes with same in-degree can batch)
4. **BFS-Based**: Iterative, no recursion stack limits
5. **Deterministic**: With consistent queue ordering (e.g., sorted), output is deterministic
6. **Well-Known**: Standard algorithm, easy to verify correctness

### Why Not DFS-Based Topological Sort

DFS-based topological sort:
- Requires tracking "visiting" vs "visited" states for cycle detection
- Returns reverse post-order (needs reversal)
- Recursion can hit stack limits for deep graphs
- Cycle detection is more complex (back edge detection)

Kahn's is simpler and provides cycle detection as a natural byproduct.

### Level Grouping Extension

Kahn's algorithm naturally supports grouping by dependency level:

```python
def get_levels(self) -> list[list[Entity]]:
    levels = []
    remaining = set(self._entities.keys())

    while remaining:
        # All nodes with current in-degree 0
        level = [gid for gid in remaining if in_degree[gid] == 0]
        levels.append([self._entities[gid] for gid in level])

        # Remove and update in-degrees
        for gid in level:
            remaining.remove(gid)
            for dependent in self._adjacency[gid]:
                in_degree[dependent] -= 1

    return levels
```

This enables FR-DEPEND-007: grouping independent entities for parallel batching.

### Dependency Detection

The graph is built by inspecting entity relationships:

1. **Parent Field** (FR-DEPEND-001): `task.parent` creates edge parent -> task
2. **Project Field** (FR-DEPEND-005): `task.projects` creates edge project -> task (if project is new)
3. **Section Field** (FR-DEPEND-006): `task.memberships` creates edge section -> task (if section is new)

For v1, we focus on parent-child relationships as the hard constraint.

## Alternatives Considered

### Alternative 1: DFS-Based Topological Sort

- **Description**: Use depth-first search with post-order collection
- **Pros**: Equally optimal O(V+E), well-known
- **Cons**:
  - Cycle detection requires additional state (visiting/visited)
  - Recursive implementation can hit stack limits
  - Level grouping less natural
  - Output is reverse order (needs reversal)
- **Why not chosen**: More complex cycle detection; Kahn's is cleaner

### Alternative 2: Tarjan's Strongly Connected Components

- **Description**: Find SCCs, then topologically sort the component graph
- **Pros**: Handles more complex cycle structures, optimal complexity
- **Cons**:
  - Over-engineering for simple DAG
  - More complex implementation
  - We only need to reject cycles, not analyze them
- **Why not chosen**: Unnecessary complexity; we just need to detect and reject cycles

### Alternative 3: Simple Dependency Resolution (No Graph)

- **Description**: Save parents first by checking if `entity.parent` is in pending set
- **Pros**: Very simple for shallow hierarchies
- **Cons**:
  - O(n^2) worst case
  - Doesn't scale to complex dependency patterns
  - No cycle detection
  - No level grouping
- **Why not chosen**: Poor scalability; no cycle detection

### Alternative 4: User-Specified Order

- **Description**: Require user to pass entities in correct order
- **Pros**: No algorithm needed, user has full control
- **Cons**:
  - Terrible developer experience
  - Error-prone
  - Defeats purpose of orchestration layer
- **Why not chosen**: Violates "automatic dependency ordering" requirement

## Consequences

### Positive
- O(V+E) complexity meets performance requirements
- Cycle detection built-in (no separate pass needed)
- Natural extension to level grouping for batching
- Well-understood algorithm, easy to verify and maintain
- Deterministic ordering aids testing and debugging

### Negative
- Requires building explicit graph structure (memory overhead)
- Graph must be rebuilt if entities change between preview() and commit()
- Complex cycles produce generic "cycle detected" error (not detailed path)

### Neutral
- Graph edges are directed: dependency -> dependent
- Placeholder GIDs (temp_xxx) used for new entities in graph
- Level 0 entities have no dependencies, level 1 depends on level 0, etc.

## Compliance

How do we ensure this decision is followed?

1. **Implementation**: DependencyGraph class uses Kahn's algorithm exclusively
2. **Unit Tests**: Test cases for:
   - Empty graph
   - Single entity
   - Linear chain (A -> B -> C)
   - Diamond (A -> B, A -> C, B -> D, C -> D)
   - Cycle detection (A -> B -> A)
   - Complex cycles (A -> B -> C -> A)
3. **Performance Tests**: Benchmark 1000-entity graphs to verify O(V+E)
4. **Code Review**: Algorithm changes require ADR update
