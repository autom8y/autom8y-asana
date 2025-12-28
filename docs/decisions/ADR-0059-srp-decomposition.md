# ADR-0059: SRP Decomposition for Core Modules

## Metadata
- **Status**: Proposed
- **Date**: 2025-12-28
- **Sprint**: SRP Decomposition Sprint
- **Debt IDs**: DEBT-018, DEBT-019, DEBT-060
- **Related**: ADR-0045 (SaveSession Decomposition), TDD-04 (Batch & Save Operations)

## Context

Three core modules have grown beyond maintainable single-file sizes, violating the Single Responsibility Principle:

| Module | Current Lines | Target | Primary Issues |
|--------|--------------|--------|----------------|
| `persistence/session.py` | 1,651 | <500 | Mixed orchestration, action handling, cache invalidation, healing |
| `clients/tasks.py` | 1,397 | <400 | CRUD + convenience wrappers + TTL logic + detection logic |
| `clients/goals.py` | 1,124 | <400 | Repetitive sync/async boilerplate, subgoal/follower domains mixed |

### Responsibility Analysis

**session.py (1,651 lines, 50+ methods)**:
1. **Session Lifecycle**: Context management, state transitions (RLock-protected)
2. **Entity Tracking**: Registration, untracking, recursive tracking, GID-based identity
3. **Change Inspection**: get_changes, get_state, find_by_gid, is_tracked
4. **Dry Run / Preview**: preview() returning planned operations
5. **Commit Orchestration**: 5-phase execution (CRUD, cache, actions, cascades, healing, automation)
6. **Action Operations**: 14 ActionBuilder descriptors + custom methods (add_comment, set_parent)
7. **Cascade Operations**: cascade_field, get_pending_cascades
8. **Cache Invalidation**: _invalidate_cache_for_results (~100 lines)
9. **Event Hooks**: on_pre_save, on_post_save, on_error, on_post_commit

**tasks.py (1,397 lines)**:
1. **Core CRUD**: get/create/update/delete with async/sync pairs and overloads
2. **TTL Resolution**: Entity-type detection for cache TTL (~80 lines)
3. **Pagination**: list_async, subtasks_async, dependents_async returning PageIterator
4. **P1 Convenience Methods**: add_tag, remove_tag, move_to_section, etc. (~400 lines)
5. **Task Duplication**: duplicate_async/duplicate (~130 lines)

**goals.py (1,124 lines)**:
1. **Core CRUD**: get/create/update/delete with async/sync pairs and overloads
2. **List Operations**: list_async with filtering
3. **Subgoal Management**: list_subgoals, add_subgoal, remove_subgoal
4. **Supporting Work**: add/remove_supporting_work
5. **Follower Management**: add_followers, remove_followers

### Forces at Play

1. **ADR-0045 Precedent**: session.py already decomposed via ActionBuilder pattern (from 2,193 to 1,651 lines)
2. **Sync/Async Boilerplate**: Each method requires async version + sync wrapper + overloads (4-6x amplification)
3. **Import Path Stability**: `autom8_asana.clients.tasks.TasksClient` must remain unchanged
4. **Test Coverage**: 181 tests must continue passing without modification
5. **Thread Safety**: RLock patterns in session.py require careful extraction

## Decision

### 1. session.py Decomposition: Extract Commit Phases

Extract cache invalidation into a dedicated coordinator, reducing session.py complexity:

**New Module: `persistence/cache_invalidator.py` (~120 lines)**
```python
class CacheInvalidator:
    """Coordinates cache invalidation after SaveSession commits.

    Per FR-INVALIDATE-001 through FR-INVALIDATE-006.
    Handles TASK, SUBTASKS, DETECTION, and DataFrame cache entries.
    """

    def __init__(self, cache_provider: Any, log: Any | None = None):
        self._cache = cache_provider
        self._log = log

    async def invalidate_for_commit(
        self,
        crud_result: SaveResult,
        action_results: list[ActionResult],
        tracker: ChangeTracker,
    ) -> None:
        """Invalidate all cache entries affected by commit."""
        ...

    def _collect_affected_gids(
        self,
        crud_result: SaveResult,
        action_results: list[ActionResult],
    ) -> set[str]:
        """Collect GIDs of all entities requiring invalidation."""
        ...

    def _invalidate_dataframe_caches(
        self,
        gids: set[str],
        tracker: ChangeTracker,
        action_results: list[ActionResult],
    ) -> None:
        """Invalidate DataFrame caches for project contexts."""
        ...
```

**session.py Changes**:
- Replace 100-line `_invalidate_cache_for_results` with delegation to `CacheInvalidator`
- Keep commit orchestration in session.py (sequence matters, not volume)

**Line Impact**: session.py 1,651 -> ~1,550 lines (CacheInvalidator: ~120 lines)

### 2. tasks.py Decomposition: Extract Convenience Methods

Extract P1 convenience methods and TTL logic into focused modules:

**New Module: `clients/task_operations.py` (~300 lines)**
```python
class TaskOperations:
    """P1 convenience methods for common task operations.

    Wraps SaveSession internally for single-action operations.
    Per TDD-SDKUX Section 2C.
    """

    def __init__(self, tasks_client: TasksClient):
        self._client = tasks_client._client
        self._http = tasks_client._http
        self._tasks = tasks_client

    async def add_tag_async(
        self, task_gid: str, tag_gid: str, *, refresh: bool = False
    ) -> Task:
        """Add tag to task without explicit SaveSession."""
        ...

    async def remove_tag_async(
        self, task_gid: str, tag_gid: str, *, refresh: bool = False
    ) -> Task:
        """Remove tag from task without explicit SaveSession."""
        ...

    # ... move_to_section, set_assignee, add_to_project, remove_from_project
    # Each with async + sync variants
```

**New Module: `clients/task_ttl.py` (~100 lines)**
```python
class TaskTTLResolver:
    """Resolves cache TTL based on entity type detection.

    Per FR-TTL-001 through FR-TTL-007.
    """

    def __init__(self, config: Any):
        self._config = config

    def resolve(self, data: dict[str, Any]) -> int:
        """Resolve TTL based on entity type detection."""
        entity_type = self._detect_entity_type(data)
        return self._get_ttl_for_type(entity_type)

    def _detect_entity_type(self, data: dict[str, Any]) -> str | None:
        """Detect entity type from task data."""
        ...

    def _get_ttl_for_type(self, entity_type: str | None) -> int:
        """Get TTL for detected entity type."""
        ...
```

**tasks.py Changes**:
- Core CRUD remains in TasksClient (~600 lines)
- TaskOperations handles P1 methods via composition
- TasksClient exposes operations via property: `self.ops = TaskOperations(self)`
- Backward compatibility: Direct method access still works via delegation

**Line Impact**: tasks.py 1,397 -> ~600 lines (TaskOperations: ~300, TaskTTLResolver: ~100)

### 3. goals.py Decomposition: Extract Relationship Operations

Extract subgoal, supporting work, and follower management into focused modules:

**New Module: `clients/goal_relationships.py` (~350 lines)**
```python
class GoalRelationships:
    """Manages goal hierarchies and supporting work relationships.

    Handles subgoals, supporting work (projects/portfolios), and positioning.
    """

    def __init__(self, goals_client: GoalsClient):
        self._http = goals_client._http
        self._log_operation = goals_client._log_operation

    # Subgoal operations
    def list_subgoals_async(self, goal_gid: str, ...) -> PageIterator[Goal]:
        ...

    async def add_subgoal_async(self, goal_gid: str, *, subgoal: str, ...) -> Goal:
        ...

    async def remove_subgoal_async(self, goal_gid: str, *, subgoal: str) -> None:
        ...

    # Supporting work operations
    async def add_supporting_work_async(
        self, goal_gid: str, *, supporting_resource: str, ...
    ) -> Goal:
        ...

    async def remove_supporting_work_async(
        self, goal_gid: str, *, supporting_resource: str
    ) -> None:
        ...
```

**New Module: `clients/goal_followers.py` (~200 lines)**
```python
class GoalFollowers:
    """Manages goal follower relationships.

    Handles adding and removing followers from goals.
    """

    def __init__(self, goals_client: GoalsClient):
        self._http = goals_client._http
        self._log_operation = goals_client._log_operation

    async def add_followers_async(
        self, goal_gid: str, *, followers: list[str], ...
    ) -> Goal:
        ...

    async def remove_followers_async(
        self, goal_gid: str, *, followers: list[str], ...
    ) -> Goal:
        ...
```

**goals.py Changes**:
- Core CRUD remains in GoalsClient (~450 lines)
- GoalRelationships handles hierarchies via composition
- GoalFollowers handles followers via composition
- GoalsClient exposes via properties: `self.relationships`, `self.followers`
- Backward compatibility: Direct method access delegated

**Line Impact**: goals.py 1,124 -> ~450 lines (GoalRelationships: ~350, GoalFollowers: ~200)

### Backward Compatibility Strategy

All decompositions use **delegation pattern** to maintain API stability:

```python
# In tasks.py
class TasksClient(BaseClient):
    def __init__(self, ...):
        super().__init__(...)
        self._operations = TaskOperations(self)
        self._ttl_resolver = TaskTTLResolver(self._config)

    # Delegation for backward compatibility
    async def add_tag_async(self, task_gid: str, tag_gid: str, **kwargs) -> Task:
        return await self._operations.add_tag_async(task_gid, tag_gid, **kwargs)

    def add_tag(self, task_gid: str, tag_gid: str, **kwargs) -> Task:
        return self._operations.add_tag(task_gid, tag_gid, **kwargs)
```

Delegation methods are minimal (2-3 lines each) and ensure:
- Import paths unchanged
- Type signatures preserved
- IDE autocomplete works
- Tests pass without modification

## Rationale

### Why Delegation Over Package Extraction?

| Factor | Package Approach | Delegation Approach | Winner |
|--------|-----------------|---------------------|--------|
| Import stability | Requires `__init__.py` facade | Unchanged | **Delegation** |
| Test disruption | Tests need import updates | Tests unchanged | **Delegation** |
| IDE discoverability | Methods hidden in submodules | Methods visible on client | **Delegation** |
| Rollback risk | Delete package, restore files | Revert individual files | **Delegation** |
| Incremental adoption | All-or-nothing | One module at a time | **Delegation** |

### Why Not Extract More from session.py?

ADR-0045 already performed significant extraction (2,193 -> 1,651):
- ActionBuilder pattern eliminated 770 lines
- HealingManager consolidated healing logic

Current 1,651 lines includes:
- Extensive docstrings (per project conventions)
- Type annotations and overloads
- Event hook infrastructure

Further extraction risks:
- Breaking RLock coordination between phases
- Fragmenting commit orchestration logic
- Introducing indirection without simplification

Extracting cache invalidation is safe because:
- Self-contained logic (~100 lines)
- No RLock state dependencies
- Clear input/output contract

### Why Separate TaskOperations from TasksClient?

TaskOperations methods share a pattern:
1. Validate GIDs
2. Create SaveSession internally
3. Perform single action
4. Optionally refresh

This is fundamentally different from TasksClient core responsibilities:
1. Direct HTTP operations
2. Model validation
3. Cache coordination

Separation enables:
- Testing convenience methods without HTTP mocks
- Future extension of convenience patterns
- Clearer mental model for SDK users

## Alternatives Considered

### Alternative 1: Mixin Classes

```python
class TaskOperationsMixin:
    async def add_tag_async(self, ...): ...

class TasksClient(BaseClient, TaskOperationsMixin):
    ...
```

**Rejected Because**:
- Multiple inheritance MRO complexity
- Mixins share instance state (tight coupling)
- Doesn't reduce line count in primary file
- Harder to test in isolation

### Alternative 2: Full Package Extraction

```
clients/
  tasks/
    __init__.py  # Facade re-exporting TasksClient
    client.py    # Core CRUD
    operations.py
    ttl.py
```

**Rejected Because**:
- Changes import paths or requires facade
- Higher test disruption risk
- Over-engineering for current scale
- Makes finding TasksClient harder

### Alternative 3: Code Generation for Sync Wrappers

Generate sync methods from async signatures automatically.

**Rejected Because**:
- Build step complexity
- Generated code harder to debug
- Merges create conflicts
- Type hints need manual handling

## Consequences

### Positive

- **Single Responsibility**: Each module has ONE clear purpose
- **Testability**: Extracted modules can be tested in isolation
- **Maintainability**: Smaller files easier to navigate and modify
- **Extensibility**: New operations can extend dedicated modules
- **Zero Breaking Changes**: All public APIs unchanged

### Negative

- **Additional Files**: +5 new files across packages
- **Indirection**: Delegation adds one call level
- **Learning Curve**: Team must understand new structure
- **Documentation**: README updates needed for new modules

### Neutral

- **Line Count**: Redistributed, not eliminated (boilerplate inherent to pattern)
- **Test Coverage**: Unchanged; same tests pass via delegation

## Compliance

### Verification Checklist

After implementation:

```bash
# Verify line counts
wc -l src/autom8_asana/persistence/session.py     # Should be <500
wc -l src/autom8_asana/clients/tasks.py           # Should be <400
wc -l src/autom8_asana/clients/goals.py           # Should be <400

# Verify import paths unchanged
python -c "from autom8_asana.clients.tasks import TasksClient"
python -c "from autom8_asana.clients.goals import GoalsClient"
python -c "from autom8_asana.persistence.session import SaveSession"

# Verify all tests pass
pytest tests/ -v --tb=short
```

### Enforcement

1. **Code Review**: New convenience methods must go in operations modules
2. **Line Count Gate**: Primary files must stay under targets
3. **Import Validation**: No direct imports from internal modules

## Cross-References

**Related ADRs**:
- ADR-0045: SaveSession Decomposition (ActionBuilder pattern precedent)
- ADR-0040: Unit of Work Pattern
- ADR-0043: Action Operations Architecture

**Related TDDs**:
- TDD-04: Batch & Save Operations
- TDD-SRP-DECOMPOSITION: This sprint's technical design

**Debt Tickets**:
- DEBT-018: session.py exceeds 500-line target
- DEBT-019: tasks.py exceeds 400-line target
- DEBT-060: goals.py exceeds 400-line target
