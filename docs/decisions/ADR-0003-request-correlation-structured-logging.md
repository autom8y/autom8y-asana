# ADR-0003: Request Correlation and Structured Logging

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0013 (Correlation ID Strategy), ADR-0086 (Logging Standardization)
- **Related**: reference/OBSERVABILITY.md, ADR-0001 (Protocol Extensibility), ADR-0004 (Observability Hooks)

## Context

The SDK requires traceability for debugging and operational visibility. Engineers need to follow a single SDK operation through all its activity (cache hits, API calls, retries, errors). Additionally, log output must be filterable, structured, and zero-cost when disabled.

Two interrelated challenges:

**Tracing challenge**: Asana's `X-Request-Id` is insufficient because it only appears after HTTP requests complete, changes on each retry, and generates multiple IDs for paginated operations. The SDK needs consistent correlation across all activity within a single operation.

**Logging challenge**: Inconsistent patterns across 22+ SDK modules made filtering difficult:
- Mixed use of `logging.getLogger(__name__)`, inline imports, and custom providers
- Eager string formatting (f-strings) created overhead even when logging disabled
- No standardized approach for structured context (correlation IDs, entity GIDs, timing)

## Decision

**Implement SDK-generated correlation IDs using `sdk-{timestamp_hex}-{random_hex}` format, combined with hierarchical logger naming (`autom8_asana.*`) and lazy formatting for zero-cost structured logging.**

### Correlation ID Design

Generate correlation IDs per top-level SDK operation:
- Format: `sdk-{timestamp_hex}-{random_hex}` (18 characters total)
- Timestamp: Lower 32 bits of Unix milliseconds as 8 hex characters
- Random suffix: 4 hex characters (16 bits) for collision avoidance
- Scope: One ID per operation; shared across retries, pagination, and cache lookups
- Injection: `@error_handler` decorator on client methods

### Logger Naming Convention

```python
# Pattern: autom8_asana.{module_path}
# Uses __name__ for automatic hierarchical namespacing

import logging
logger = logging.getLogger(__name__)  # Automatically uses module path

# Examples:
# autom8_asana.transport.http
# autom8_asana.persistence.session
# autom8_asana.models.business.contact
```

### Zero-Cost Logging Pattern

```python
# WRONG: Eager formatting (string created even if debug disabled)
logger.debug(f"Processing entity {gid} with {len(fields)} fields")

# CORRECT: Lazy formatting (zero overhead when disabled)
logger.debug("Processing entity %s with %s fields", gid, len(fields))

# For expensive computations, guard with level check
if logger.isEnabledFor(logging.DEBUG):
    summary = compute_expensive_summary(entity)
    logger.debug("Entity summary: %s", summary)
```

### Structured Context

```python
from dataclasses import dataclass, asdict

@dataclass
class LogContext:
    """Structured logging context via extra parameter."""
    correlation_id: str | None = None
    operation: str | None = None
    entity_gid: str | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict, omitting None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}

# Usage
ctx = LogContext(
    correlation_id="sdk-abc123-def4",
    operation="track",
    entity_gid=task.gid,
)
logger.info("Tracking entity", extra=ctx.to_dict())
```

## Rationale

### Correlation ID Rationale

**Why SDK-generated IDs?**
Asana's X-Request-Id only exists after requests complete and changes on retries. SDK-generated IDs are:
- Available before any HTTP request
- Consistent across retries and pagination
- Present even when requests fail before reaching Asana

**Why timestamp + random format?**
Balances multiple concerns:

| Approach | Pros | Cons |
|----------|------|------|
| UUID v4 | Very unique | 36 chars, no temporal ordering |
| Counter | Ordered, short | Requires shared state, thread-safety issues |
| Timestamp only | Ordered, short | Collisions within same millisecond |
| Timestamp + random | Ordered, unique enough, readable | Small collision risk (~1/65536 per ms) |

The chosen format:
- Short enough for readable logs (18 characters vs. 36 for UUID)
- Temporally ordered for debugging (earlier operations sort first)
- Unique enough for tracing (collision requires same ms + same random)
- Fast to generate (no locks, no I/O)

**Why decorator-based injection?**
Explicit `@error_handler` decorator makes correlation clear in code, works with type checkers, and follows standard Python patterns. Alternatives (class decorators, `__getattribute__` magic, contextvars) were rejected for being too implicit or complex.

### Logging Rationale

**Why hierarchical `__name__` pattern?**
- Automatic namespacing: Module `autom8_asana/foo/bar.py` has `__name__ = "autom8_asana.foo.bar"`
- Standard Python convention used by most libraries
- Hierarchical filtering: Set level for `autom8_asana` (all) or `autom8_asana.transport` (specific)
- No magic strings to maintain

**Why lazy formatting?**
Performance benchmark with debug disabled:
```python
f"Entity {gid}"           # 0.5 µs - string always created
"Entity %s" % (gid,)      # 0.02 µs - string created
logger.debug("%s", gid)   # 0.01 µs - string never created when disabled
```

**Why `extra` dict for structured context?**
- Standard `logging` interface (no custom methods needed)
- Compatible with JSON formatters and log aggregation systems
- Works with existing LogProvider protocol (supports `**kwargs`)
- No protocol changes or external dependencies required

## Alternatives Considered

### Alternative 1: OpenTelemetry Integration
- **Description**: Integrate OpenTelemetry for distributed tracing and structured logging
- **Pros**: Industry standard, rich ecosystem, automatic instrumentation
- **Cons**: Heavy dependency, requires infrastructure (collector), overkill for SDK needs
- **Why not chosen**: Violates minimal dependency principle. Consumers can integrate OTel at their level using correlation IDs.

### Alternative 2: Caller-Provided Correlation IDs
- **Description**: Require callers to generate and pass correlation IDs to SDK methods
- **Pros**: Caller controls ID format, can integrate with existing tracing
- **Cons**: Burdens all callers, easy to forget, inconsistent when optional
- **Why not chosen**: SDK should be easy to use; tracing should be automatic.

### Alternative 3: Contextvars for Implicit Propagation
- **Description**: Store correlation ID in contextvars for automatic propagation
- **Pros**: No explicit parameter passing, works across async boundaries
- **Cons**: Magic (implicit state), harder to test, potential thread pool issues
- **Why not chosen**: Explicit is better than implicit for SDK design.

### Alternative 4: Structured Logging Library (structlog)
- **Description**: Use structlog for native structured logging support
- **Pros**: Rich features, processors, JSON-native output
- **Cons**: External dependency (violates PRD constraint), learning curve
- **Why not chosen**: Cannot add external dependencies. Standard `logging` + `extra` dict is sufficient.

### Alternative 5: Thread-Local Context for Logging
- **Description**: Set context via thread-local storage, automatically attached to logs
- **Pros**: Cleaner call sites, automatic propagation
- **Cons**: Hidden state, harder to test, asyncio compatibility issues
- **Why not chosen**: Explicit `extra` parameter is clearer and safer.

## Consequences

### Positive
- **Consistent tracing**: Every SDK operation traceable by correlation ID across cache, API, retries
- **No caller burden**: SDK generates IDs automatically; no additional parameters required
- **Debuggable**: Timestamp prefix enables temporal ordering in logs
- **Low overhead**: ID generation is fast; lazy logging is zero-cost when disabled
- **Easy filtering**: `logging.getLogger("autom8_asana").setLevel(DEBUG)` captures all SDK logs
- **Structured output**: JSON formatters can extract correlation_id, entity_gid, duration_ms
- **Standard interface**: Works with any stdlib-compatible logging setup

### Negative
- **Collision risk**: Small chance (~1/65536 per ms) of ID collision; acceptable for debugging
- **Not externally correlated**: SDK IDs don't automatically link to caller's tracing; callers must log both
- **Decorator overhead**: Small runtime cost for decorator invocation on every operation
- **Verbose call sites**: `logger.info("msg", extra=ctx.to_dict())` is longer than simple strings
- **Migration effort**: Existing code with f-strings must be updated

### Neutral
- **Asana X-Request-Id still useful**: Captured and logged alongside SDK ID for complementary purposes
- **LogContext optional**: Existing code without structured context continues to work
- **Consumers can override**: Advanced consumers can wrap clients for custom correlation schemes

## Compliance

How we ensure this decision is followed:

**Code Review Checklist**:
- All public async client methods have `@error_handler` decorator
- All loggers use `logging.getLogger(__name__)` pattern
- No f-strings in logger calls (use lazy formatting: `logger.debug("msg %s", arg)`)
- Structured context uses `extra` dict parameter

**Verification Commands**:
```bash
# Verify @error_handler on client methods
grep -r "async def.*_async" --include="*.py" src/autom8_asana/clients/ -B1 | grep -c "@error_handler"

# Verify logger naming consistency
grep -r "logging.getLogger" --include="*.py" src/ | grep -v "__name__"

# Find f-strings in logger calls (potential violations)
grep -rE 'logger\.(debug|info|warning|error)\s*\(\s*f"' --include="*.py" src/
```

**Testing Requirements**:
- Unit tests verify correlation ID generation and format
- Unit tests verify correlation ID propagation through decorators
- Unit tests verify lazy formatting (mock logger, verify format string vs. f-string)
- Integration tests verify correlation IDs appear in logs for multi-step operations

**User Configuration Example**:
```python
import logging

# Enable all SDK logs at DEBUG level
logging.getLogger("autom8_asana").setLevel(logging.DEBUG)

# Enable only specific subsystem
logging.getLogger("autom8_asana.transport").setLevel(logging.DEBUG)
logging.getLogger("autom8_asana").setLevel(logging.WARNING)

# JSON formatter for structured logs
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Extract structured fields from extra
        for field in ["correlation_id", "entity_gid", "operation", "duration_ms"]:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.getLogger("autom8_asana").addHandler(handler)
```
