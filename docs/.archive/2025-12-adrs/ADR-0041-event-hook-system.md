# ADR-0041: Synchronous Event Hooks with Async Support

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0005 (FR-EVENT-001 through FR-EVENT-005), TDD-0010

## Context

The Save Orchestration Layer should provide hooks for validation, notification, and error handling at key points in the save lifecycle. PRD-0005 defines three hook types: pre_save, post_save, and on_error.

**Forces at play:**

1. **Flexibility**: Support both sync and async hook implementations
2. **Simplicity**: Simple registration and invocation model
3. **Control**: Pre-save hooks should be able to abort operations
4. **Safety**: Post-save and error hooks should not break the save
5. **SDK Consistency**: Follow async-first pattern but support sync callers

**Problem**: How should the event hook system be designed?

## Decision

Implement **synchronous invocation with async support**: hooks are invoked sequentially, but can be either sync functions or async coroutines.

Registration via decorators:
```python
async with SaveSession(client) as session:
    @session.on_pre_save
    def validate_task(entity, operation):
        if operation == OperationType.CREATE and not entity.name:
            raise ValueError("Task name required")

    @session.on_post_save
    async def notify_created(entity, operation, result):
        await notification_service.send(f"Created {entity.gid}")

    @session.on_error
    def log_error(entity, operation, error):
        logger.error(f"Failed to {operation} {entity}: {error}")
```

Invocation behavior:
- **Pre-save**: Called before each entity save; exceptions abort the entity's save
- **Post-save**: Called after successful save; exceptions logged but don't fail
- **On-error**: Called when save fails; exceptions logged but don't compound

Implementation:
```python
async def emit_pre_save(self, entity, operation):
    for hook in self._pre_save_hooks:
        result = hook(entity, operation)
        if asyncio.iscoroutine(result):
            await result

async def emit_post_save(self, entity, operation, data):
    for hook in self._post_save_hooks:
        try:
            result = hook(entity, operation, data)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            pass  # Log but don't fail
```

## Rationale

### Why Synchronous Invocation Model

1. **Predictable Order**: Hooks execute in registration order
2. **Simple Mental Model**: No concurrent hook execution to reason about
3. **Abort Semantics**: Pre-save can abort by raising exception
4. **Deterministic**: Same order every time

### Why Support Both Sync and Async Hooks

1. **Flexibility**: Some hooks are simple (logging), others need I/O (notifications)
2. **User Choice**: Don't force async on simple validation
3. **Runtime Detection**: `asyncio.iscoroutine(result)` detects async
4. **Minimal Friction**: Both patterns work naturally

### Why Pre-Save Can Abort

Pre-save hooks are for validation/transformation:
- Check required fields before create
- Validate business rules
- Transform data
- Abort if invalid

Raising an exception:
- Prevents entity from being saved
- Entity added to SaveResult.failed
- Provides clear feedback

### Why Post-Save/Error Are Fault-Tolerant

Post-save and error hooks are for notification/logging:
- Send notifications
- Update caches
- Log events

These shouldn't fail the operation:
- Entity is already saved (can't undo)
- Notification failure != save failure
- Log failures silently, don't compound errors

### Why Decorator Pattern

Decorators are Pythonic for event registration:
```python
@session.on_pre_save
def my_hook(entity, operation):
    ...
```

Benefits:
- Clean syntax
- Self-documenting
- Familiar pattern (Flask routes, pytest fixtures)
- Easy to see what hooks are registered

Alternative (explicit registration) also supported:
```python
session.on_pre_save(my_hook)
```

## Alternatives Considered

### Alternative 1: Callback Registration (No Decorators)

- **Description**: `session.add_pre_save_hook(func)`
- **Pros**: Explicit, familiar from observer pattern
- **Cons**:
  - More verbose
  - Less Pythonic
  - Function must be defined before registration
- **Why not chosen**: Decorators are cleaner; explicit still supported

### Alternative 2: Event Emitter Pattern

- **Description**: Full event emitter with namespaced events: `session.on('pre_save:Task', ...)`
- **Pros**: Flexible event filtering, familiar from Node.js
- **Cons**:
  - Over-engineering for three event types
  - String-based event names are error-prone
  - More complex API
- **Why not chosen**: Only three hook types needed; simpler is better

### Alternative 3: Async-Only Hooks

- **Description**: All hooks must be async coroutines
- **Pros**: Consistent model, always await
- **Cons**:
  - Forces async on simple sync operations
  - More boilerplate for simple cases
  - Friction for sync codebases
- **Why not chosen**: Unnecessary constraint; runtime detection is easy

### Alternative 4: Sync-Only Hooks

- **Description**: All hooks must be synchronous functions
- **Pros**: Simple invocation, no async complexity
- **Cons**:
  - Cannot do async work (notifications, external calls)
  - Limits usefulness
  - Inconsistent with async-first SDK
- **Why not chosen**: Too limiting; async hooks are valuable

### Alternative 5: Parallel Hook Execution

- **Description**: Execute all hooks concurrently via asyncio.gather()
- **Pros**: Faster for many hooks
- **Cons**:
  - Non-deterministic order
  - Pre-save abort semantics unclear
  - Harder to debug
  - Overkill for typical 1-3 hooks
- **Why not chosen**: Determinism more valuable than parallelism

### Alternative 6: Middleware Chain

- **Description**: Hooks as middleware that wrap each other
- **Pros**: Each hook can wrap the operation
- **Cons**:
  - Complex mental model
  - Hard to understand execution order
  - Over-engineering
- **Why not chosen**: Simple before/after hooks sufficient

## Consequences

### Positive
- Simple, predictable invocation order
- Supports both sync and async hooks transparently
- Pre-save hooks can validate/abort
- Post-save/error hooks don't compound failures
- Clean decorator syntax

### Negative
- Sequential execution (no parallel hooks)
- Must check asyncio.iscoroutine() at runtime
- Post-save exceptions silently swallowed (by design, but could hide bugs)

### Neutral
- Hooks registered per-session (not global)
- Hooks receive entity, operation, and context-specific data
- No built-in hook timeout (hooks can hang if poorly written)

## Compliance

How do we ensure this decision is followed?

1. **API Design**: Only three hook types (pre_save, post_save, on_error)
2. **Implementation**: EventSystem handles async detection
3. **Tests**: Test both sync and async hooks
4. **Documentation**: Show examples of both patterns
5. **Error Handling**: Post-save/error exceptions logged, not raised
