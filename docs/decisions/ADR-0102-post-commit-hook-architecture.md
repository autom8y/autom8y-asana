# ADR-0102: Post-Commit Hook Architecture

## Status

Accepted

## Context

The Automation Layer (TDD-AUTOMATION-LAYER) requires a mechanism to evaluate rules and execute actions after SaveSession commits complete. The SDK already has an EventSystem with pre_save, post_save, and error hooks at the entity level, but lacks a session-level post-commit hook that fires after all phases complete.

**Requirements**:
- FR-001: AutomationEngine evaluates rules after SaveSession commit
- FR-002: Post-commit hooks receive full SaveResult
- NFR-003: Automation failures do not fail primary commit

**Options Considered**:

1. **Option A: Direct SaveSession Extension** - Add automation call directly in commit_async() without hook infrastructure
2. **Option B: EventSystem Post-Commit Hook** - Extend EventSystem with session-level post-commit hooks
3. **Option C: Separate Observer Pattern** - New observer system independent of EventSystem

## Decision

**We will use Option B: EventSystem Post-Commit Hook.**

Add `on_post_commit` hook type to EventSystem, consistent with existing `on_pre_save`, `on_post_save`, and `on_error` patterns. The AutomationEngine integrates as a built-in consumer of this hook, but consumers can also register custom post-commit handlers.

## Consequences

### Positive

- **Consistency**: Same pattern as existing hooks; developers familiar with pre/post_save hooks understand post_commit immediately
- **Extensibility**: Consumers can add their own post-commit handlers (logging, metrics, notifications)
- **Testability**: Hooks can be mocked/stubbed in tests independent of automation
- **Separation**: Automation becomes one of potentially many post-commit handlers

### Negative

- **Ordering**: Multiple post-commit hooks execute in registration order; no priority mechanism
- **Isolation**: Hooks cannot communicate or depend on each other's results

### Implementation

```python
# events.py
PostCommitHook = (
    Callable[[SaveResult], None]
    | Callable[[SaveResult], Coroutine[Any, Any, None]]
)

class EventSystem:
    def __init__(self) -> None:
        self._post_commit_hooks: list[PostCommitHook] = []

    def register_post_commit(self, func: PostCommitHook) -> Callable[..., Any]:
        self._post_commit_hooks.append(func)
        return func

    async def emit_post_commit(self, result: SaveResult) -> None:
        for hook in self._post_commit_hooks:
            try:
                hook_result = hook(result)
                if asyncio.iscoroutine(hook_result):
                    await hook_result
            except Exception:
                pass  # Post-commit hooks cannot fail the commit
```

## References

- TDD-AUTOMATION-LAYER
- PRD-AUTOMATION-LAYER (FR-001, FR-002, NFR-003)
- DISCOVERY-AUTOMATION-LAYER (Section 1: SaveSession Extension Points)
- ADR-0041: Event Hook System (existing hook patterns)
