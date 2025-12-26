# TDD: Observability Enhancements

## Metadata
- **TDD ID**: TDD-0007
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-08
- **Last Updated**: 2025-12-08
- **PRD Reference**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md)
- **Related TDDs**: [TDD-0001](./TDD-0001-sdk-architecture.md), [TDD-0003](./TDD-0003-tier1-clients.md)
- **Related ADRs**: [ADR-0013](../decisions/ADR-0013-correlation-id-strategy.md)

## Overview

This design defines the observability layer for the autom8_asana SDK, implementing FR-SDK-044 (ErrorHandler decorator) and FR-SDK-045 (correlation ID logging). The design adds request tracing via SDK-generated correlation IDs, an `@error_handler` decorator for consistent error handling, and structured logging integration.

## Requirements Summary

From PRD-0001:
- **FR-SDK-044**: Provide ErrorHandler decorator for consistent handling
- **FR-SDK-045**: Log errors with correlation IDs

From FR-SDK-041-043 (already implemented):
- AsanaError base exception hierarchy exists
- Specific exceptions for common error cases exist
- Original Asana API error details preserved (X-Request-Id captured)

## System Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Client Application                               │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          AsanaClient Facade                              │
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │  TasksClient    │  │  ProjectsClient │  │  WebhooksClient │   ...    │
│  │  @error_handler │  │  @error_handler │  │  @error_handler │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
│           │                    │                    │                   │
│           └────────────────────┼────────────────────┘                   │
│                                │                                        │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    CorrelationContext                            │   │
│  │  - Generates SDK correlation IDs per operation                   │   │
│  │  - Provides context for logging and exception enrichment         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                │                                        │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                       AsyncHTTPClient                            │   │
│  │  - Includes correlation_id in logs                               │   │
│  │  - Captures X-Request-Id from Asana responses                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Design

### Component Architecture

| Component | Responsibility | Location |
|-----------|----------------|----------|
| `CorrelationContext` | Generate and manage correlation IDs | `autom8_asana/observability/correlation.py` |
| `error_handler` decorator | Wrap methods with consistent error handling | `autom8_asana/observability/decorators.py` |
| `ContextualLogProvider` | Log adapter that injects correlation context | `autom8_asana/observability/logging.py` |

### Data Model

#### Correlation ID Format

```
sdk-{timestamp_hex}-{random_hex}

Examples:
  sdk-192f3a1b-4c7e
  sdk-192f3a1c-8d2f
```

Components:
- `sdk-` prefix: Distinguishes SDK-generated IDs from Asana's X-Request-Id
- `timestamp_hex`: 8 hex chars, lower 32 bits of Unix timestamp (milliseconds)
- `random_hex`: 4 hex chars, random component for uniqueness

This format:
- Is short enough for log readability (19 characters)
- Encodes timestamp for rough ordering/debugging
- Has enough entropy to avoid collisions within a single process

#### CorrelationContext

```python
@dataclass(frozen=True)
class CorrelationContext:
    """Immutable context for a single SDK operation."""

    correlation_id: str
    """SDK-generated correlation ID for this operation."""

    operation: str
    """Operation name, e.g., 'TasksClient.get_async'."""

    started_at: float
    """Unix timestamp when operation started."""

    resource_gid: str | None = None
    """Optional GID of the resource being operated on."""

    asana_request_id: str | None = None
    """X-Request-Id from Asana response (set after request completes)."""
```

#### Enhanced AsanaError

The existing `AsanaError` will be extended to include correlation context:

```python
class AsanaError(Exception):
    # Existing fields...
    correlation_id: str | None = None
    """SDK correlation ID for tracing."""

    operation: str | None = None
    """Operation that failed, e.g., 'TasksClient.get_async'."""
```

### API Contracts

#### error_handler Decorator

```python
def error_handler(
    func: Callable[..., Awaitable[T]]
) -> Callable[..., Awaitable[T]]:
    """Decorator for consistent error handling on client methods.

    Provides:
    1. Correlation ID generation and propagation
    2. Consistent error logging with context
    3. Exception enrichment with correlation data
    4. Operation timing (debug level)

    Works with both sync and async methods.

    Example:
        class TasksClient(BaseClient):
            @error_handler
            async def get_async(self, task_gid: str) -> Task:
                ...
    """
```

Decorator behavior:

1. **Before operation**: Generate correlation ID, log operation start
2. **On success**: Log completion with duration (debug level)
3. **On error**: Log error with full context, enrich exception, re-raise

#### CorrelationContext API

```python
class CorrelationContext:
    @staticmethod
    def generate(operation: str, resource_gid: str | None = None) -> CorrelationContext:
        """Create new context with fresh correlation ID."""

    def with_asana_request_id(self, request_id: str) -> CorrelationContext:
        """Return new context with Asana request ID set."""

    def format_log_prefix(self) -> str:
        """Format prefix for log messages, e.g., '[sdk-abc123-4567]'."""
```

#### ContextualLogProvider

```python
class ContextualLogProvider:
    """LogProvider adapter that injects correlation context into messages.

    Wraps an existing LogProvider and prepends correlation ID to all messages.
    """

    def __init__(
        self,
        delegate: LogProvider,
        context: CorrelationContext,
    ) -> None:
        """Initialize with delegate logger and correlation context."""

    # LogProvider interface methods delegate with prefix injection
```

### Data Flow

#### Successful Operation Flow

```
1. Client method called (e.g., tasks.get_async("123"))
   │
   ▼
2. @error_handler generates CorrelationContext
   correlation_id = "sdk-192f3a1b-4c7e"
   operation = "TasksClient.get_async"
   resource_gid = "123"
   │
   ▼
3. Log operation start (DEBUG)
   "[sdk-192f3a1b-4c7e] TasksClient.get_async(123) starting"
   │
   ▼
4. Execute actual method
   HTTP request made via AsyncHTTPClient
   │
   ▼
5. On success: Log completion (DEBUG)
   "[sdk-192f3a1b-4c7e] TasksClient.get_async(123) completed in 142ms"
   │
   ▼
6. Return result
```

#### Error Flow

```
1. Client method called
   │
   ▼
2. @error_handler generates CorrelationContext
   correlation_id = "sdk-192f3a1b-4c7e"
   │
   ▼
3. Log operation start (DEBUG)
   │
   ▼
4. Execute method, exception raised
   │
   ▼
5. Catch exception in decorator
   │
   ▼
6. Enrich exception with context
   error.correlation_id = "sdk-192f3a1b-4c7e"
   error.operation = "TasksClient.get_async"
   │
   ▼
7. Log error (ERROR level)
   "[sdk-192f3a1b-4c7e] TasksClient.get_async(123) failed: NotFoundError ..."
   "  Asana request_id: abc123-def456"
   │
   ▼
8. Re-raise enriched exception
```

### Log Format Specification

#### Standard Log Format

```
[{correlation_id}] {operation}({resource_gid}) {message}
```

Examples:
```
[sdk-192f3a1b-4c7e] TasksClient.get_async(1234567890) starting
[sdk-192f3a1b-4c7e] TasksClient.get_async(1234567890) completed in 142ms
[sdk-192f3a1b-4c7e] TasksClient.create_async() starting
[sdk-192f3a1b-4c7e] TasksClient.create_async() completed in 234ms
```

#### Error Log Format

```
[{correlation_id}] {operation}({resource_gid}) failed: {error_type}: {message}
  Asana request_id: {asana_request_id}
  Duration: {duration_ms}ms
```

Example:
```
[sdk-192f3a1b-4c7e] TasksClient.get_async(1234567890) failed: NotFoundError: No task found with that gid (HTTP 404, request_id=abc123)
  Asana request_id: abc123
  Duration: 89ms
```

#### Log Levels

| Event | Level | Condition |
|-------|-------|-----------|
| Operation start | DEBUG | Always |
| Operation success | DEBUG | Always |
| Retry attempt | WARNING | On retry |
| Rate limit wait | WARNING | On rate limit |
| Operation failure | ERROR | On exception |

### Integration Approach

#### Phase 1: Core Infrastructure

Create new `observability` module:

```
src/autom8_asana/observability/
├── __init__.py          # Public exports
├── correlation.py       # CorrelationContext
├── decorators.py        # @error_handler
└── logging.py           # ContextualLogProvider
```

#### Phase 2: BaseClient Integration

Update `BaseClient` to support correlation context:

```python
class BaseClient:
    def _create_context(
        self,
        operation: str,
        resource_gid: str | None = None
    ) -> CorrelationContext:
        """Create correlation context for an operation."""
        return CorrelationContext.generate(
            operation=f"{self.__class__.__name__}.{operation}",
            resource_gid=resource_gid,
        )

    def _contextual_log(self, context: CorrelationContext) -> ContextualLogProvider:
        """Get logger with correlation context injected."""
        if self._log is None:
            return NullLogger()
        return ContextualLogProvider(self._log, context)
```

#### Phase 3: Decorator Application

Apply `@error_handler` to all client methods. Two approaches available:

**Option A: Explicit decorator on each method**

```python
class TasksClient(BaseClient):
    @error_handler
    async def get_async(self, task_gid: str, ...) -> Task:
        ...
```

**Option B: Class decorator that wraps all public async methods**

```python
@error_handler_class
class TasksClient(BaseClient):
    async def get_async(self, task_gid: str, ...) -> Task:
        ...
```

Per ADR-0013, we choose **Option A** (explicit decorator) because:
- Explicit is better than implicit
- Not all methods need error handling (e.g., `_build_opt_fields`)
- Easier to understand and debug

#### Phase 4: Sync Wrapper Compatibility

The `@sync_wrapper` decorator (per ADR-0002) must work with `@error_handler`. The decorators should be applied in this order:

```python
class TasksClient(BaseClient):
    @error_handler
    async def get_async(self, task_gid: str, ...) -> Task:
        # Actual implementation
        ...

    @sync_wrapper("get_async")
    async def _get_sync(self, task_gid: str, ...) -> Task:
        # Delegates to get_async, which has error handling
        return await self.get_async(task_gid, ...)

    def get(self, task_gid: str, ...) -> Task:
        return self._get_sync(task_gid, ...)
```

The sync path goes: `get()` -> `_get_sync()` -> `get_async()` with `@error_handler`
The async path goes: `get_async()` with `@error_handler`

Both paths get error handling via `get_async`.

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Correlation ID generation | SDK-generated with timestamp+random | Short, debuggable, no external dependencies | ADR-0013 |
| Decorator placement | Explicit on async methods only | Explicit > implicit; avoids double-decoration on sync wrappers | ADR-0013 |
| Log format | Bracketed prefix with operation | Consistent, grep-able, minimal overhead | ADR-0013 |
| Context propagation | Per-operation, not global | Thread-safe, no contextvars complexity | ADR-0013 |

## Complexity Assessment

**Level: Module**

Justification:
- Single concern (observability)
- No external dependencies beyond existing LogProvider protocol
- Clean API surface with decorator and context classes
- Minimal internal structure (3 files)
- Does not warrant service-level complexity

## Implementation Plan

### Phases

| Phase | Deliverable | Dependencies | Estimate |
|-------|-------------|--------------|----------|
| 1 | `CorrelationContext` class with ID generation | None | 0.5 day |
| 2 | `@error_handler` decorator with tests | Phase 1 | 1 day |
| 3 | `ContextualLogProvider` adapter | Phase 1 | 0.5 day |
| 4 | Apply decorator to Tier 1 clients (Tasks, Projects, Sections) | Phases 1-3 | 0.5 day |
| 5 | Apply decorator to remaining clients | Phase 4 | 0.5 day |
| 6 | Update documentation, verify integration | Phase 5 | 0.5 day |

**Total: ~3.5 days**

### Migration Strategy

This is additive functionality. No breaking changes to existing API.

1. Add observability module with new components
2. Update BaseClient with helper methods
3. Apply decorator to client methods incrementally
4. Existing tests should continue passing
5. Add new tests for observability behavior

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Performance overhead from correlation ID generation | Low | Low | ID generation is O(1) with minimal allocations; timestamp from system, random from urandom |
| Decorator order issues with sync_wrapper | Medium | Medium | Document correct order; add integration test that exercises both paths |
| Log verbosity concerns | Low | Medium | Default to DEBUG for start/success; users control log level |
| Correlation ID collision | Low | Very Low | 4 hex chars = 65536 combinations; combined with timestamp, collision requires same ms + same random |

## Observability

This TDD *is* the observability design. After implementation:

### Metrics (Future Enhancement)
- Operation count by client and method
- Operation duration histogram
- Error count by type

### Logging
- All operations logged with correlation ID
- Error details preserved including Asana request_id
- Duration tracking for performance analysis

### Alerting (Consumer Responsibility)
- SDK provides structured logs
- Consumers can alert on error rates, latency

## Testing Strategy

### Unit Tests

```python
# test_correlation.py
def test_correlation_id_format():
    ctx = CorrelationContext.generate("TestClient.method")
    assert ctx.correlation_id.startswith("sdk-")
    assert len(ctx.correlation_id) == 18  # sdk-{8}-{4}

def test_correlation_context_immutable():
    ctx = CorrelationContext.generate("TestClient.method")
    ctx2 = ctx.with_asana_request_id("abc123")
    assert ctx.asana_request_id is None
    assert ctx2.asana_request_id == "abc123"

# test_decorators.py
async def test_error_handler_logs_success():
    log = MockLogProvider()
    client = make_test_client(log_provider=log)

    await client.get_async("123")

    assert any("[sdk-" in msg for msg in log.debug_messages)
    assert any("completed" in msg for msg in log.debug_messages)

async def test_error_handler_enriches_exception():
    client = make_failing_client()

    with pytest.raises(NotFoundError) as exc_info:
        await client.get_async("nonexistent")

    assert exc_info.value.correlation_id is not None
    assert exc_info.value.correlation_id.startswith("sdk-")
    assert exc_info.value.operation == "TasksClient.get_async"

async def test_error_handler_logs_error():
    log = MockLogProvider()
    client = make_failing_client(log_provider=log)

    with pytest.raises(NotFoundError):
        await client.get_async("nonexistent")

    assert any("[sdk-" in msg for msg in log.error_messages)
    assert any("failed" in msg for msg in log.error_messages)
```

### Integration Tests

```python
async def test_sync_and_async_paths_both_get_correlation():
    """Verify both sync and async paths get error handling."""
    log = MockLogProvider()
    client = make_real_client(log_provider=log)

    # Async path
    async_result = await client.tasks.get_async("123")
    async_logs = list(log.debug_messages)
    log.clear()

    # Sync path
    sync_result = client.tasks.get("123")
    sync_logs = list(log.debug_messages)

    # Both should have correlation IDs
    assert any("[sdk-" in msg for msg in async_logs)
    assert any("[sdk-" in msg for msg in sync_logs)
```

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None | - | - | Design is complete |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-08 | Architect | Initial TDD for observability enhancements |
