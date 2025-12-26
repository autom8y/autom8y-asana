# ADR-0033: Extension and Integration Architecture

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0102
- **Related**: TDD-AUTOMATION-LAYER, PRD-AUTOMATION-LAYER

## Context

The autom8_asana system must support extensibility beyond its core functionality. The EventSystem already provides pre_save, post_save, and error hooks at the entity level, but lacks session-level integration points. The Automation Layer requires a mechanism to evaluate rules and execute actions after SaveSession commits complete.

**Requirements**:
- FR-001: AutomationEngine evaluates rules after SaveSession commit
- FR-002: Post-commit hooks receive full SaveResult
- NFR-003: Automation failures do not fail primary commit

**Design question**: How should we extend SaveSession to support post-commit integration while maintaining:
- Consistency with existing hook patterns
- Extensibility for custom handlers beyond automation
- Testability independent of automation
- Separation of concerns

## Decision

We extend the **EventSystem with `on_post_commit` hook type**, consistent with existing pre/post_save patterns. The AutomationEngine integrates as a built-in consumer of this hook, but custom handlers are also supported.

### Post-Commit Hook Architecture

**Add session-level post-commit hooks to EventSystem**:

```python
# events.py
PostCommitHook = (
    Callable[[SaveResult], None]
    | Callable[[SaveResult], Coroutine[Any, Any, None]]
)

@dataclass
class EventSystem:
    """Event system for entity and session lifecycle hooks."""

    _pre_save_hooks: list[PreSaveHook] = field(default_factory=list)
    _post_save_hooks: list[PostSaveHook] = field(default_factory=list)
    _error_hooks: list[ErrorHook] = field(default_factory=list)
    _post_commit_hooks: list[PostCommitHook] = field(default_factory=list)  # NEW

    def register_post_commit(self, func: PostCommitHook) -> Callable[..., Any]:
        """Register a post-commit hook."""
        self._post_commit_hooks.append(func)
        return func

    async def emit_post_commit(self, result: SaveResult) -> None:
        """Emit post-commit event to all registered hooks.

        Post-commit hooks execute after SaveSession.commit_async() completes.
        Failures do not affect the primary commit.
        """
        for hook in self._post_commit_hooks:
            try:
                hook_result = hook(result)
                if asyncio.iscoroutine(hook_result):
                    await hook_result
            except Exception as e:
                # Post-commit hooks cannot fail the commit
                # Log the error but continue with other hooks
                logger.exception(f"Post-commit hook failed: {e}")
```

**SaveSession integration**:

```python
class SaveSession:
    async def commit_async(self) -> SaveResult:
        """Commit all changes and emit post-commit hooks."""
        # ... existing commit logic ...

        # Build SaveResult
        result = SaveResult(
            created=created_entities,
            updated=updated_entities,
            deleted=deleted_entities,
            errors=errors,
        )

        # Emit post-commit event (NEW)
        await self._client.events.emit_post_commit(result)

        return result
```

**AutomationEngine as built-in consumer**:

```python
# automation/engine.py
class AutomationEngine:
    """Evaluates automation rules after SaveSession commits."""

    def __init__(self, client: AsanaClient, rules: list[AutomationRule]) -> None:
        self._client = client
        self._rules = rules

        # Register as post-commit hook
        client.events.register_post_commit(self._evaluate_rules_async)

    async def _evaluate_rules_async(self, result: SaveResult) -> None:
        """Evaluate all rules against SaveResult entities."""
        for entity in result.created + result.updated:
            for rule in self._rules:
                if await rule.matches_async(entity):
                    try:
                        await rule.execute_async(entity, self._client)
                    except Exception as e:
                        # Rule failures logged but don't propagate
                        logger.exception(f"Rule {rule.name} failed: {e}")
```

**Custom handler registration**:

```python
# Example: Custom post-commit metric tracking
class MetricsTracker:
    async def track_commit_metrics(self, result: SaveResult) -> None:
        """Track commit metrics for observability."""
        metrics.increment("commits.total")
        metrics.increment("entities.created", len(result.created))
        metrics.increment("entities.updated", len(result.updated))

# Register custom handler
tracker = MetricsTracker()
client.events.register_post_commit(tracker.track_commit_metrics)
```

**Decorator pattern for hooks**:

```python
# Convenient decorator syntax
@client.events.register_post_commit
async def log_commit_summary(result: SaveResult) -> None:
    """Log summary of committed changes."""
    logger.info(
        f"Commit completed: {len(result.created)} created, "
        f"{len(result.updated)} updated, {len(result.deleted)} deleted"
    )
```

## Rationale

**Why extend EventSystem over direct SaveSession extension?**

| Approach | Pros | Cons |
|----------|------|------|
| **EventSystem hook** | Consistent pattern, extensible, testable | Slightly more abstraction |
| Direct SaveSession call | Simple, explicit | Hardcoded to automation, not extensible |
| Separate observer pattern | Clean separation | Duplicate event system, inconsistent |

EventSystem already handles entity lifecycle hooks (pre_save, post_save, error). Adding session-level post_commit hooks maintains consistency while enabling extensibility beyond automation.

**Why post-commit over pre-commit?**

Post-commit hooks receive the final SaveResult with actual GIDs (including temp-to-real transitions), committed entities, and error details. Pre-commit hooks would see pending state, not outcomes.

**Why exception suppression in emit_post_commit?**

Post-commit hooks execute after the primary commit completes. Hook failures should not roll back committed changes. Each hook runs independently; one failure doesn't prevent others.

**Why sync and async hook support?**

Hook signature allows both:
```python
PostCommitHook = (
    Callable[[SaveResult], None]           # Sync
    | Callable[[SaveResult], Coroutine]    # Async
)
```

This enables simple logging hooks (sync) and complex automation rules (async API calls).

## Consequences

### Positive

- **Consistency**: Same pattern as existing pre_save/post_save/error hooks; developers familiar with entity hooks understand post_commit immediately
- **Extensibility**: Consumers can add custom post-commit handlers (logging, metrics, notifications, external system integration)
- **Testability**: Hooks can be mocked/stubbed in tests independent of automation
- **Separation**: Automation becomes one of potentially many post-commit handlers
- **Graceful degradation**: Hook failures don't affect primary commit; each hook isolated
- **Flexible integration**: Supports both sync and async hooks
- **Decorator convenience**: Clean registration syntax with `@client.events.register_post_commit`

### Negative

- **Ordering**: Multiple post-commit hooks execute in registration order; no priority mechanism
- **Isolation**: Hooks cannot communicate or depend on each other's results
- **Error visibility**: Hook failures logged but not propagated to caller (by design)
- **Async overhead**: Async hooks add latency after commit (acceptable for non-critical operations)

### Neutral

- Commit latency increases by post-commit hook execution time (automation evaluations, logging)
- AutomationEngine registration happens at client initialization
- Hook execution is serial (one after another in registration order)
- No built-in retry mechanism for failed hooks

## Implementation Notes

### Hook Lifecycle

```
SaveSession.commit_async() called
    |
    +-> Phase 1: Prepare changes (existing)
    |
    +-> Phase 2: Execute actions (existing)
    |
    +-> Phase 3: Build SaveResult (existing)
    |
    +-> Phase 4: Emit post-commit hooks (NEW)
    |       |
    |       +-> Hook 1 (e.g., AutomationEngine)
    |       |       |
    |       |       +-> Evaluate rules
    |       |       +-> Execute matching rules
    |       |       +-> Log failures (don't propagate)
    |       |
    |       +-> Hook 2 (e.g., MetricsTracker)
    |       |       |
    |       |       +-> Increment counters
    |       |
    |       +-> Hook 3 (e.g., Custom logger)
    |               |
    |               +-> Log summary
    |
    +-> Return SaveResult to caller
```

### Error Handling Pattern

```python
async def emit_post_commit(self, result: SaveResult) -> None:
    """Emit post-commit event with isolated error handling."""
    for hook in self._post_commit_hooks:
        try:
            hook_result = hook(result)
            if asyncio.iscoroutine(hook_result):
                await hook_result
        except Exception as e:
            # Isolate hook failures
            # Each hook runs independently
            # One failure doesn't prevent others
            logger.exception(
                f"Post-commit hook {hook.__name__} failed: {e}",
                extra={"result": result, "hook": hook},
            )
            # Continue with next hook
```

### Testing Pattern

```python
# Test post-commit hook invocation
async def test_post_commit_hook_receives_result():
    """Post-commit hooks receive SaveResult."""
    called_with = None

    @client.events.register_post_commit
    async def test_hook(result: SaveResult) -> None:
        nonlocal called_with
        called_with = result

    async with SaveSession(client) as session:
        task = Task(name="Test")
        session.track(task)
        result = await session.commit_async()

    assert called_with is result
    assert len(called_with.created) == 1

# Test hook isolation
async def test_post_commit_hook_failure_isolated():
    """Hook failures don't affect commit or other hooks."""
    hook1_called = False
    hook2_called = False

    @client.events.register_post_commit
    async def failing_hook(result: SaveResult) -> None:
        nonlocal hook1_called
        hook1_called = True
        raise ValueError("Hook failure")

    @client.events.register_post_commit
    async def successful_hook(result: SaveResult) -> None:
        nonlocal hook2_called
        hook2_called = True

    async with SaveSession(client) as session:
        task = Task(name="Test")
        session.track(task)
        result = await session.commit_async()

    # Commit succeeded despite hook failure
    assert len(result.created) == 1
    # Both hooks executed
    assert hook1_called
    assert hook2_called
```

## Compliance

### Implementation Requirements

- **EventSystem extension**:
  - [ ] `PostCommitHook` type alias defined
  - [ ] `_post_commit_hooks` list added to EventSystem
  - [ ] `register_post_commit()` method implemented
  - [ ] `emit_post_commit()` method with exception suppression

- **SaveSession integration**:
  - [ ] `commit_async()` emits post-commit event after building SaveResult
  - [ ] Post-commit failures don't affect SaveResult
  - [ ] Sync wrapper `commit()` also triggers post-commit hooks

- **AutomationEngine integration**:
  - [ ] AutomationEngine registers as post-commit hook at initialization
  - [ ] Rule evaluation receives full SaveResult
  - [ ] Rule failures logged but don't propagate

### Testing Requirements

- [ ] Unit tests for EventSystem.register_post_commit()
- [ ] Unit tests for EventSystem.emit_post_commit()
- [ ] Integration tests for SaveSession emitting post-commit
- [ ] Tests verifying hook isolation (failure doesn't affect others)
- [ ] Tests verifying hook receives correct SaveResult
- [ ] Tests for both sync and async hooks

### Documentation Requirements

- [ ] Post-commit hook pattern documented in SDK guide
- [ ] AutomationEngine integration documented
- [ ] Custom hook registration examples provided
- [ ] Hook ordering and isolation behavior documented

## Related Decisions

**Foundation**: See ADR-0029 for EventSystem's role in SDK extensibility architecture.

**Patterns**: See ADR-SUMMARY-PATTERNS for event hook patterns and observer patterns.

**Automation**: See TDD-AUTOMATION-LAYER for AutomationEngine design that consumes post-commit hooks.

**Persistence**: See ADR-SUMMARY-PERSISTENCE for SaveSession lifecycle and commit phases.

## References

**Original ADRs**:
- ADR-0102: Post-Commit Hook Architecture (2025-12-17)

**Technical Design**:
- TDD-AUTOMATION-LAYER: Automation engine integration
- ADR-0041: Event Hook System (existing entity-level hook patterns)

**Requirements**:
- PRD-AUTOMATION-LAYER
  - FR-001: AutomationEngine evaluates rules after SaveSession commit
  - FR-002: Post-commit hooks receive full SaveResult
  - NFR-003: Automation failures do not fail primary commit
- DISCOVERY-AUTOMATION-LAYER: Section 1 (SaveSession Extension Points)

## Future Considerations

**Priority mechanism**: If hook ordering becomes critical, consider:
```python
def register_post_commit(self, func: PostCommitHook, priority: int = 0) -> None:
    """Register hook with priority (higher executes first)."""
    self._post_commit_hooks.append((priority, func))
    self._post_commit_hooks.sort(key=lambda x: x[0], reverse=True)
```

**Hook communication**: If hooks need to share data:
```python
@dataclass
class PostCommitContext:
    """Shared context for post-commit hooks."""
    result: SaveResult
    metadata: dict[str, Any]  # Hooks can add metadata
```

**Async batching**: If many hooks create latency:
```python
# Execute hooks concurrently
await asyncio.gather(*[hook(result) for hook in self._post_commit_hooks])
```

These are deferred until demonstrated need.
