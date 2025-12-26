# ADR-0044: SaveSession Lifecycle & System Integration

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-11 through 2025-12-22
- **Consolidated From**: ADR-0053, ADR-0061, ADR-0064, ADR-0100, ADR-0104, ADR-0107, ADR-0110, ADR-0111, ADR-0125
- **Related**: [reference/SAVESESSION.md](/Users/tomtenuta/Code/autom8_asana/docs/decisions/reference/SAVESESSION.md), PRD-0005, PRD-SDKUX, PRD-CACHE-INTEGRATION

## Context

As SaveSession evolved from basic batch operations to sophisticated orchestration, several integration and lifecycle concerns emerged:

1. **Composite Entities**: Should tracking a Business automatically track child entities (contacts, units)?
2. **Implicit vs Explicit Lifecycle**: How should direct methods (`task.save()`) create SaveSession internally?
3. **Dirty Detection Leverage**: How should Task models use SaveSession's ChangeTracker?
4. **State Transitions**: How should Process entities move between pipeline states?
5. **Automation Integration**: How to prevent infinite loops when automation rules trigger other rules?
6. **NameGid Preservation**: How to preserve name information in action targets for automation matching?
7. **Task Duplication**: How to efficiently duplicate tasks with subtask hierarchies?
8. **Cache Integration**: How to invalidate cache entries after successful saves?

Forces at play:
- Explicit better than implicit (Python Zen)
- Memory control for large object graphs
- Clear session lifetime boundaries
- Leverage existing infrastructure (don't duplicate)
- Domain-specific operations belong in domain models
- Prevent infinite automation loops
- Preserve metadata for automation rules
- Efficient bulk operations
- Cache consistency after mutations

## Decision

### Composite Entities: Optional Recursive Tracking

Provide opt-in recursive tracking via `track(entity, recursive=True)`:

```python
# Save entire hierarchy
async with SaveSession(client) as session:
    session.track(business, recursive=True)
    # Automatically tracks: business, contact_holder, unit_holder,
    # all contacts, all units

# Save only specific entities
async with SaveSession(client) as session:
    session.track(business)  # Just business
    session.track(contact)   # Specific contact

# Save business + contacts, not units
async with SaveSession(client) as session:
    session.track(business)
    session.track(business.contact_holder, recursive=True)
```

**Default: `recursive=False`** (explicit opt-in)

**Rationale:**
- Explicit is better than implicit (Python Zen)
- Memory control (developer opts into large footprint)
- Debug-ability (preview shows exactly what's tracked)
- DependencyGraph handles ordering once entities tracked
- Flexibility for specific branches

### Implicit Lifecycle: Method-Scoped Sessions

Create and destroy SaveSession within method scope:

```python
async def save_async(self) -> Task:
    """Save this task using implicit SaveSession.

    Session created within method scope and destroyed on exit.
    """
    async with SaveSession(self._client) as session:
        session.track(self)
        result = await session.commit_async()
        if not result.success:
            raise result.failed[0].error
        return self
```

**Characteristics:**
- Clear scope (session lifetime = method invocation)
- No nesting issues (can't accidentally nest contexts)
- Simple error handling (failure immediate and unambiguous)
- Consistent with P1 direct methods pattern

**Not Ambient Session:**
- Don't reuse existing sessions
- Don't check for active session context
- Each method creates own session

### Dirty Detection: Leverage SaveSession ChangeTracker

Task models use SaveSession's existing snapshot comparison:

```python
class Task(AsanaResource):
    def is_dirty(self) -> bool:
        """Check if task has unsaved changes.

        Uses SaveSession ChangeTracker for consistency with
        save operation dirty detection.
        """
        tracker = ChangeTracker()
        tracker.track(self)
        # Immediately dirty because no baseline
        # Would need to track at fetch time for real usage
        return tracker.is_dirty(self)
```

**Rationale:**
- Reuse existing, tested snapshot comparison logic
- Consistent behavior between dirty detection and save
- No duplication of change tracking logic
- Single source of truth

### State Transitions: Composition over Extension

Compose state transitions via `Process.move_to_state()` helper:

```python
# In Process model
def move_to_state(
    self,
    session: SaveSession,
    target_state: ProcessSection
) -> SaveSession:
    """Move this process to target pipeline state.

    Args:
        session: Active SaveSession to queue operation
        target_state: Target ProcessSection (OPPORTUNITY, ACTIVE, etc.)

    Returns:
        session for method chaining
    """
    section_gid = ProcessProjectRegistry.get_section_gid(
        self.process_type,
        target_state
    )
    return session.move_to_section(self, section_gid)

# Usage
async with SaveSession(client) as session:
    process.move_to_state(session, ProcessSection.ACTIVE)
    result = await session.commit_async()
```

**Rationale:**
- SaveSession remains entity-agnostic (no Process-specific logic)
- `Process.move_to_state()` is domain-appropriate
- Reuses existing `move_to_section()` implementation
- Fast section lookup via configuration (ProcessProjectRegistry)

**NOT Adding to SaveSession:**
```python
# REJECTED: Domain logic in infrastructure layer
session.move_process_to_state(process, ProcessSection.ACTIVE)
```

### Automation Loop Prevention: Dual Protection

Use depth limit AND visited set tracking:

```python
@dataclass
class AutomationContext:
    """Context for automation rule execution to prevent loops.

    Dual protection:
    1. Depth limit: Prevent unbounded cascade chains
    2. Visited set: Prevent true cycles
    """
    depth: int = 0
    visited: set[tuple[str, str]] = field(default_factory=set)
    config: AutomationConfig = field(default_factory=AutomationConfig)

    def can_continue(self, entity_gid: str, rule_id: str) -> bool:
        """Check if rule can execute on entity.

        Args:
            entity_gid: Entity GID
            rule_id: Automation rule ID

        Returns:
            False if depth exceeded or cycle detected
        """
        if self.depth >= self.config.max_cascade_depth:
            logger.warning(f"Depth limit reached: {self.depth}")
            return False

        if (entity_gid, rule_id) in self.visited:
            logger.warning(f"Cycle detected: {entity_gid} + {rule_id}")
            return False

        return True

    def mark_visited(self, entity_gid: str, rule_id: str) -> None:
        """Mark entity+rule pair as visited."""
        self.visited.add((entity_gid, rule_id))

    def increment_depth(self) -> "AutomationContext":
        """Create child context with incremented depth."""
        return AutomationContext(
            depth=self.depth + 1,
            visited=self.visited.copy(),
            config=self.config
        )
```

**Dual Protection:**
- **Depth limit**: Prevents A→B→C→D→... unbounded chains
- **Visited set**: Prevents A→B→A true cycles
- **Clear skip reasons**: Logged for debugging

### NameGid for Action Targets: Preserve Identity

Use NameGid dataclass for action operation targets:

```python
@dataclass(frozen=True)
class NameGid:
    """Entity identity with preserved name for automation matching.

    Attributes:
        gid: Asana GID
        name: Entity name (preserved for matching rules)
    """
    gid: str
    name: str | None = None

# ActionOperation uses NameGid
@dataclass(frozen=True)
class ActionOperation:
    task: AsanaResource
    action: ActionType
    target: NameGid | None = None  # NameGid preserves name
    extra_params: dict[str, Any] = field(default_factory=dict)

# Usage in automation
if action.target and action.target.name == "Converted":
    # Trigger conversion automation
    ...
```

**Rationale:**
- Preserves name information without loss
- Consistent with SDK resource references (assignee, projects, sections)
- Enables automation matching on names (e.g., "Converted" section)
- Frozen/immutable like ActionOperation
- Optional name field (GID always present)

### Task Duplication: Use duplicate_async()

Use Asana's native duplication endpoint for template copying:

```python
async def duplicate_async(
    task_gid: str,
    include_subtasks: bool = True
) -> Task:
    """Duplicate task using Asana's duplication endpoint.

    Args:
        task_gid: Source task GID
        include_subtasks: Whether to include subtasks

    Returns:
        Newly created task (with subtasks if requested)
    """
    response = await client.post(
        f"/tasks/{task_gid}/duplicate",
        data={"include": "subtasks" if include_subtasks else None}
    )
    return Task(**response["data"])
```

**Subtask Wait Strategy** (poll until ready):

```python
async def wait_for_subtasks_async(
    task_gid: str,
    expected_count: int,
    timeout: float = 2.0,
    poll_interval: float = 0.2,
) -> bool:
    """Poll until subtask count matches expected.

    Args:
        task_gid: Task GID to check
        expected_count: Expected subtask count
        timeout: Maximum wait time
        poll_interval: Time between polls

    Returns:
        True if subtasks ready, False if timeout
    """
    start = time.time()
    while time.time() - start < timeout:
        task = await client.tasks.get_async(task_gid, opt_fields="num_subtasks")
        if task.num_subtasks >= expected_count:
            return True
        await asyncio.sleep(poll_interval)
    return False
```

**Rationale:**
- Atomic operation (parent + all subtasks in one request)
- Hierarchy preservation (nested subtasks copied automatically)
- Template evolution (changes automatically apply)
- Single API call vs N+1 manual creation
- Asana handles GID assignment and relationships

**NOT Manual Creation:**
```python
# REJECTED: Manual subtask creation
parent = await client.tasks.create_async(...)
for subtask_data in template.subtasks:
    child = await client.tasks.create_async(..., parent=parent.gid)
```

### Cache Integration: Post-Commit Invalidation

Invalidate cache entries after successful commit:

```python
async def commit_async(self) -> SaveResult:
    """Commit tracked changes with cache invalidation.

    Phase 1: Execute CRUD and actions
    Phase 1.5: Cache invalidation
    Phase 2-5: Continue normal flow
    """
    # Phase 1: Execute operations
    crud_result, action_results = await self._pipeline.execute_with_actions(...)

    # Phase 1.5: Invalidate cache for modified entities
    await self._invalidate_cache_for_results(crud_result, action_results)

    # Phase 2-5: Clear actions, return result, etc.
    ...

async def _invalidate_cache_for_results(
    self,
    crud_result: SaveResult,
    action_results: list[ActionResult]
) -> None:
    """Invalidate cache entries for all modified entities.

    Args:
        crud_result: CRUD operation results
        action_results: Action operation results
    """
    if not self._client.cache:
        return

    # Collect all modified GIDs
    gids_to_invalidate: set[str] = set()

    # CRUD successes
    for entity in crud_result.succeeded:
        if entity.gid:
            gids_to_invalidate.add(entity.gid)

    # Action successes (invalidate task)
    for result in action_results:
        if result.success and result.action.task.gid:
            gids_to_invalidate.add(result.action.task.gid)

    # Batch invalidate
    if gids_to_invalidate:
        try:
            await self._client.cache.invalidate_many(gids_to_invalidate)
        except Exception as e:
            # Log but don't fail commit on cache errors
            logger.warning(f"Cache invalidation failed: {e}")
```

**Rationale:**
- Clean separation (invalidation logic isolated)
- Batch efficiency (O(n) invalidations via set deduplication)
- Comprehensive (covers CRUD and action operations)
- Resilient (failures logged, not propagated)
- Phase 1.5 placement (after commit, before result construction)

## Rationale

### Why Optional Recursive Tracking

**Alternative: Automatic Recursive Tracking**
- Would snapshot entire object graph automatically
- Memory explosion risk
- Unexpected save behavior
- Violates "explicit is better than implicit"

**Chosen Approach:**
- Developer explicitly opts in via `recursive=True`
- Clear memory implications
- Preview shows exactly what will save
- Can track specific branches selectively

### Why Method-Scoped Sessions

**Alternative: Ambient Session Detection**
```python
# REJECTED: Check for active session
if hasattr(self, '_current_session'):
    self._current_session.track(self)
else:
    # Create new session
```

**Problems:**
- Hidden state management
- Nesting confusion
- Thread-safety issues
- Unclear session ownership

**Chosen Approach:**
- Each method creates own session
- Clear scope boundaries
- No hidden state
- Simple error handling

### Why Composition for State Transitions

**Alternative: Extend SaveSession**
```python
# REJECTED: Domain logic in infrastructure
class SaveSession:
    def move_process_to_state(self, process, state):
        ...
```

**Problems:**
- SaveSession coupled to Process domain
- Can't unit test without Process
- Violates separation of concerns

**Chosen Approach:**
- SaveSession provides generic `move_to_section()`
- Process provides domain-specific `move_to_state()`
- Clean separation of infrastructure and domain

### Why Dual Loop Prevention

**Alternative: Depth Limit Only**
- Can't detect true cycles (A→B→A at low depth)

**Alternative: Visited Set Only**
- Can't prevent unbounded chains (A→B→C→D→E...)

**Chosen Approach:**
- Both protections working together
- Defense in depth
- Clear skip reasons for debugging

## Alternatives Considered

### Alternative 1: Automatic Recursive Tracking

**Description**: Tracking any entity automatically tracks all reachable children.

**Pros**: Magical, no explicit recursive flag needed

**Cons**:
- Memory explosion for large graphs
- Unexpected saves (forgot entity was reachable)
- No control over partial tracking
- Performance surprises

**Why not chosen**: Violates explicit opt-in principle.

### Alternative 2: Global Ambient Session

**Description**: Thread-local or context-var session reused across method calls.

**Pros**: No session creation overhead

**Cons**:
- Complex state management
- Thread-safety issues
- Nesting confusion
- Unclear session ownership
- Hard to debug

**Why not chosen**: Clear scope boundaries more important than minor overhead.

### Alternative 3: Separate Dirty Tracker

**Description**: Implement new dirty tracking logic in Task models.

**Pros**: Independence from SaveSession

**Cons**:
- Duplicates snapshot comparison logic
- Potential inconsistency with save behavior
- More code to maintain

**Why not chosen**: Reuse existing tested logic.

### Alternative 4: SaveSession Process Methods

**Description**: Add `session.move_process_to_state()` to SaveSession.

**Pros**: Single place for all session operations

**Cons**:
- Couples infrastructure to domain
- Can't add methods for every domain type
- Violates separation of concerns

**Why not chosen**: Composition better than extension for domain operations.

### Alternative 5: Manual Task Creation Instead of Duplication

**Description**: Create parent then create each subtask individually.

**Pros**: Full control over each field

**Cons**:
- N+1 API calls
- Complex GID management
- Error handling complexity
- Doesn't capture nested hierarchies

**Why not chosen**: Asana's duplicate endpoint is atomic and efficient.

## Consequences

### Positive

- **Explicit Control**: Developers choose recursive tracking explicitly
- **Clear Scope**: Method-scoped sessions have obvious lifetime
- **Code Reuse**: ChangeTracker used for both save and dirty detection
- **Clean Separation**: Domain logic in domain models, infrastructure agnostic
- **Loop Prevention**: Dual protection catches both cycles and unbounded chains
- **Name Preservation**: Automation rules can match on entity names
- **Efficient Duplication**: Single API call for task+subtask hierarchies
- **Cache Consistency**: Modified entities invalidated automatically

### Negative

- **Explicit Boilerplate**: Must specify `recursive=True`
- **Session Creation Overhead**: Each P1 method creates session (minimal)
- **No Ambient Session**: Can't accumulate operations across methods
- **Composition Complexity**: State transitions require understanding both layers
- **Wait Polling**: Subtask availability requires polling (Asana limitation)
- **Cache Coupling**: SaveSession depends on cache implementation

### Neutral

- **Default Non-Recursive**: Explicit opt-in for safety
- **Method Isolation**: Each method independent
- **ChangeTracker API**: Same snapshot comparison throughout
- **Process Helpers**: Convenience methods for common patterns
- **AutomationContext**: Passed through cascade chain
- **NameGid Optional**: name field can be None

## Compliance

### Enforcement

1. **Default Tracking**: `track()` default `recursive=False`
2. **Method Scope**: All P1 methods create session in method body
3. **ChangeTracker Usage**: Task dirty detection uses SaveSession logic
4. **Composition Pattern**: No domain-specific methods on SaveSession
5. **Loop Detection**: AutomationContext required for cascade operations
6. **NameGid Type**: Action targets use NameGid (not plain strings)
7. **Duplication**: Template copying uses `duplicate_async()`
8. **Cache Invalidation**: `commit_async()` calls `_invalidate_cache_for_results()`

### Testing

**Unit Tests Verify:**
- Recursive tracking includes expected entities
- Non-recursive tracking only includes root
- Method-scoped sessions created and destroyed
- ChangeTracker produces same results as save dirty detection
- Process.move_to_state() calls session.move_to_section()
- AutomationContext depth limit enforced
- AutomationContext cycle detection works
- NameGid preserves name information
- duplicate_async() creates task with subtasks
- wait_for_subtasks_async() polls until ready
- Cache invalidation called on successful commit

**Integration Tests Verify:**
- Composite entity save works end-to-end
- P1 methods work without external session
- State transitions execute correctly
- Automation doesn't infinite loop
- Task duplication preserves hierarchy
- Cache cleared after saves

## Implementation Guidance

### Recursive Tracking Patterns

**Full Hierarchy:**
```python
async with SaveSession(client) as session:
    session.track(business, recursive=True)
    # Modifies business, contacts, units
    result = await session.commit_async()
```

**Selective Branches:**
```python
async with SaveSession(client) as session:
    session.track(business)  # Just business
    session.track(business.contact_holder, recursive=True)  # + contacts
    # Does NOT include units
    result = await session.commit_async()
```

### P1 Method Usage

**Simple Save:**
```python
task.name = "Updated"
await task.save_async()  # Session created internally
```

**Direct Method:**
```python
task = await client.tasks.add_tag_async(task_gid, tag_gid)
# Session created, operation executed, session destroyed
```

### State Transition Patterns

**In Workflow:**
```python
async with SaveSession(client) as session:
    # Move to Active state
    process.move_to_state(session, ProcessSection.ACTIVE)

    # Modify process
    process.assigned_to = user_gid

    # Commit together
    result = await session.commit_async()
```

### Automation with Loop Prevention

**Rule Execution:**
```python
async def execute_rule(
    entity: AsanaResource,
    rule: AutomationRule,
    context: AutomationContext
) -> None:
    """Execute automation rule with loop prevention."""
    if not context.can_continue(entity.gid, rule.id):
        logger.info(f"Skipping {rule.id} on {entity.gid} (depth/cycle)")
        return

    # Mark visited
    context.mark_visited(entity.gid, rule.id)

    # Execute rule actions
    async with SaveSession(client) as session:
        rule.apply(entity, session)
        result = await session.commit_async()

    # Trigger dependent rules with incremented depth
    child_context = context.increment_depth()
    for dependent_rule in rule.dependent_rules:
        await execute_rule(entity, dependent_rule, child_context)
```

### Task Duplication with Wait

**Template Duplication:**
```python
# Duplicate template task
template_gid = "template_task_123"
new_task = await duplicate_async(template_gid, include_subtasks=True)

# Wait for subtasks to be ready
expected_count = 5  # Known template subtask count
ready = await wait_for_subtasks_async(
    new_task.gid,
    expected_count,
    timeout=2.0
)

if ready:
    # Proceed with modifications
    ...
else:
    logger.warning("Subtasks not ready within timeout")
```

## Cross-References

**Related ADRs:**
- ADR-0040: Unit of Work Pattern (provides track/commit foundation)
- ADR-0041: Dependency Ordering (handles composite entity ordering)
- ADR-0042: Error Handling (P1 method exception raising)
- ADR-0043: Action Operations (NameGid usage, action execution)

**Related Documents:**
- PRD-0005: Save Orchestration requirements
- PRD-SDKUX: SDK usability improvements
- PRD-CACHE-INTEGRATION: Cache invalidation requirements
- REF-savesession-lifecycle: Session state machine
- REF-entity-lifecycle: Entity lifecycle from creation to persistence
