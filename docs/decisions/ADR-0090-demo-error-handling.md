# ADR-DEMO-003: Error Handling Strategy for Demo Scripts

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-12
- **Deciders**: SDK Team
- **Related**: PRD-SDKDEMO, TDD-SDKDEMO

## Context

The SDK Demonstration Suite (PRD-SDKDEMO) will encounter various error conditions:
- **API errors**: 4xx/5xx responses from Asana
- **Rate limiting**: 429 responses requiring backoff
- **Resolution failures**: Tag/user/section names not found
- **State restoration failures**: Cannot restore entity to initial state
- **Partial failures**: Some operations in SaveSession succeed, others fail

**Forces at play**:

1. **User experience**: Errors should be clear and actionable
2. **Demo continuity**: Non-fatal errors shouldn't abort entire demo
3. **State integrity**: Partial failures shouldn't leave orphaned changes
4. **Recoverability**: User should know how to manually fix issues
5. **Debugging**: Detailed error information for troubleshooting

**Key question**: When something fails, should the demo stop, skip, or continue?

## Decision

**Implement graceful degradation with manual recovery guidance.**

### Error Classification

| Error Type | Severity | Response |
|------------|----------|----------|
| Pre-flight check failure | Fatal | Abort with clear message |
| API error (4xx) | Operation | Log, skip operation, continue demo |
| API error (5xx) | Operation | Retry once, then skip with warning |
| Rate limit (429) | Transient | Wait `retry_after`, then retry |
| Name resolution miss | Soft | Warn, offer to create or skip |
| Partial SaveSession failure | Operation | Log failures, continue with succeeded |
| Restoration failure | Serious | Log, provide manual recovery commands |

### Error Handling Pattern

```python
@dataclass
class DemoError:
    """Structured error with recovery guidance."""
    category: str  # e.g., "tag_operation", "custom_field", "restoration"
    operation: str  # e.g., "add_tag", "set_field", "restore_notes"
    entity_gid: str
    message: str
    recovery_hint: str | None = None

class DemoRunner:
    """Orchestrates demo execution with error handling."""

    def __init__(self, client: AsanaClient):
        self.errors: list[DemoError] = []
        self.warnings: list[str] = []

    async def run_operation(
        self,
        name: str,
        operation: Callable[[], Coroutine[Any, Any, Any]],
        entity_gid: str,
        recovery_hint: str | None = None,
    ) -> bool:
        """Execute operation with error handling.

        Returns True if succeeded, False if failed (logged to errors).
        """
        try:
            await operation()
            return True
        except RateLimitError as e:
            await asyncio.sleep(e.retry_after or 60)
            return await self.run_operation(name, operation, entity_gid, recovery_hint)
        except AsanaAPIError as e:
            self.errors.append(DemoError(
                category="api",
                operation=name,
                entity_gid=entity_gid,
                message=str(e),
                recovery_hint=recovery_hint,
            ))
            return False
```

### Restoration Failure Recovery

When restoration fails, provide Asana-native recovery instructions:

```python
def generate_recovery_commands(errors: list[DemoError]) -> str:
    """Generate manual recovery instructions for failed restorations."""
    lines = ["## Manual Recovery Required", ""]
    for error in errors:
        if error.category == "restoration":
            lines.append(f"### {error.entity_gid}")
            lines.append(f"Failed: {error.message}")
            if error.recovery_hint:
                lines.append(f"To fix: {error.recovery_hint}")
            lines.append("")
    return "\n".join(lines)
```

## Rationale

1. **Graceful degradation maximizes demo value**: A single failed operation shouldn't prevent demonstrating other SDK capabilities.

2. **Manual recovery is acceptable for demo scripts**: Unlike production code, demo failure is not catastrophic. Clear instructions let user fix manually if needed.

3. **Rate limit handling is automatic**: Users shouldn't need to know about 429s; demo just waits and retries.

4. **Pre-flight failures are fatal**: If test entities don't exist, nothing will work. Fail fast with clear guidance.

5. **Structured errors enable reporting**: `DemoError` dataclass provides consistent format for logging and summary.

## Alternatives Considered

### Alternative 1: Fail-Fast on Any Error

- **Description**: Any error aborts the demo immediately
- **Pros**: No partial state, simple logic, obvious failure point
- **Cons**:
  - One API hiccup stops entire demo
  - User can't see any working functionality
  - Doesn't demonstrate SDK's partial failure handling
- **Why not chosen**: Too aggressive for demo context

### Alternative 2: Silent Error Swallowing

- **Description**: Log errors but always continue
- **Pros**: Demo always completes, user sees all categories
- **Cons**:
  - User may not notice failures
  - State may be inconsistent without warning
  - Recovery hints never shown
- **Why not chosen**: Hides important information from user

### Alternative 3: Automatic Rollback on Failure

- **Description**: Any failure triggers immediate restoration of all changes
- **Pros**: Guaranteed clean state, no manual recovery needed
- **Cons**:
  - Restoration itself may fail
  - Loses progress on multi-step demos
  - Complex rollback tracking
  - User loses visibility into what succeeded
- **Why not chosen**: Rollback complexity not justified for demo scripts

### Alternative 4: Transaction-Style All-or-Nothing

- **Description**: Preview all operations, execute only if all will succeed
- **Pros**: Clean semantics, no partial state
- **Cons**:
  - Can't know if operations will succeed without trying
  - Asana API doesn't support transactions
  - Defeats purpose of demonstrating SaveSession partial failures
- **Why not chosen**: Not technically feasible with Asana API

## Consequences

### Positive
- **Demo continues despite failures**: Users see working functionality
- **Clear error visibility**: Structured errors logged with context
- **Actionable recovery**: Manual steps provided for restoration failures
- **Rate limit transparency**: Automatic retry with user notification

### Negative
- **May accumulate multiple errors**: User needs to review error list at end
- **Partial state possible**: Some operations succeeded, others failed
- **Manual recovery required**: User must follow instructions if restoration fails

### Neutral
- **Error list grows during demo**: More operations = potentially more errors
- **Recovery hints are operation-specific**: Each operation type needs custom hint

## Compliance

Ensure this decision is followed by:
- All API calls wrapped in `run_operation()` or equivalent
- No bare `except:` clauses that swallow errors silently
- Pre-flight checks use `assert` or early return with message
- Restoration failures always provide `recovery_hint`
- Demo summary printed at end includes error count and recovery instructions

