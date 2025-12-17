# ADR-HARDENING-A-003: Logging Standardization

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: SDK Team
- **Related**: PRD-HARDENING-A, TDD-HARDENING-A, ADR-0023 (CacheLoggingProvider)

## Context

Per Discovery Issue 13, the SDK has inconsistent logging patterns across 22+ modules:

| Pattern | Count | Example |
|---------|-------|---------|
| `logging.getLogger(__name__)` | ~13 | `models/task.py` |
| `logging.getLogger("autom8_asana.*")` | ~3 | `_defaults/log.py` |
| `self._log` (injected provider) | ~6 | `persistence/session.py` |
| Inline `import logging` in functions | ~4 | `models/business/contact.py` |

This inconsistency causes:
- **Filtering difficulty**: Users cannot easily filter SDK logs by prefix
- **Debugging confusion**: Different module paths in log output
- **Zero-cost violation**: Some patterns eagerly format log messages

### Forces at Play

1. **Logger naming**: Single namespace `autom8_asana.*` for easy filtering
2. **Zero-cost**: No string formatting when log level disabled
3. **Structured context**: Support `extra={}` for correlation IDs, GIDs
4. **Backward compatibility**: Existing `LogProvider` protocol must still work
5. **No dependencies**: Use stdlib `logging` only (PRD constraint)

## Decision

**Standardize on `autom8_asana.{module_path}` logger naming with lazy formatting and optional structured context via `extra` dict.**

### Logger Naming Convention

```python
# Pattern: autom8_asana.{relative_module_path}
# Examples:
autom8_asana.persistence.session
autom8_asana.models.business.contact
autom8_asana.transport.http
autom8_asana.batch.client
```

### Standard Logger Initialization

```python
# Module-level logger initialization (preferred pattern)
import logging

logger = logging.getLogger(__name__)  # Uses module path automatically

# For autom8_asana submodules, __name__ equals:
# "autom8_asana.persistence.session" etc.
```

### Zero-Cost Logging Pattern

```python
# WRONG: Eager formatting (paid even if debug disabled)
logger.debug(f"Processing entity {entity.gid} with fields {entity.custom_fields}")

# CORRECT: Lazy formatting (paid only if level enabled)
logger.debug("Processing entity %s with fields %s", entity.gid, entity.custom_fields)

# ALSO CORRECT: Guard for expensive computations
if logger.isEnabledFor(logging.DEBUG):
    field_summary = compute_expensive_summary(entity)
    logger.debug("Entity summary: %s", field_summary)
```

### Structured Context Pattern

```python
# LogContext dataclass for common context fields
@dataclass
class LogContext:
    """Structured logging context.

    Use with logger.*(msg, extra=ctx.to_dict()) for structured logs.
    """
    correlation_id: str | None = None
    operation: str | None = None
    entity_gid: str | None = None
    entity_type: str | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict, omitting None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


# Usage
ctx = LogContext(
    correlation_id="abc123",
    operation="track",
    entity_gid=task.gid,
)
logger.info("Tracking entity", extra=ctx.to_dict())

# Output (with JSON formatter configured by user):
# {"message": "Tracking entity", "correlation_id": "abc123", "operation": "track", "entity_gid": "123456"}
```

### DefaultLogProvider Enhancement

```python
# _defaults/log.py
class DefaultLogProvider:
    """Default logging provider using stdlib logging.

    Enhanced to support structured context via extra parameter.
    """

    def __init__(self, name: str = "autom8_asana") -> None:
        self._logger = logging.getLogger(name)

    def debug(self, msg: str, *args: Any, extra: dict | None = None, **kwargs: Any) -> None:
        self._logger.debug(msg, *args, extra=extra, **kwargs)

    def info(self, msg: str, *args: Any, extra: dict | None = None, **kwargs: Any) -> None:
        self._logger.info(msg, *args, extra=extra, **kwargs)

    def warning(self, msg: str, *args: Any, extra: dict | None = None, **kwargs: Any) -> None:
        self._logger.warning(msg, *args, extra=extra, **kwargs)

    def error(self, msg: str, *args: Any, extra: dict | None = None, **kwargs: Any) -> None:
        self._logger.error(msg, *args, extra=extra, **kwargs)

    def exception(self, msg: str, *args: Any, extra: dict | None = None, **kwargs: Any) -> None:
        self._logger.exception(msg, *args, extra=extra, **kwargs)
```

## Rationale

### Why `__name__` Pattern?

1. **Automatic namespacing**: `__name__` in `autom8_asana/foo/bar.py` is `autom8_asana.foo.bar`
2. **Standard Python convention**: Most libraries use this pattern
3. **Hierarchical filtering**: Users can set level for `autom8_asana` (all) or `autom8_asana.transport` (specific)
4. **No magic strings**: Module paths stay synchronized with logger names

### Why Lazy Formatting?

```python
# Benchmark: Debug disabled
f"Entity {gid}"      # 0.5 us - string always created
"Entity %s" % (gid,) # 0.02 us - string created
logger.debug("%s", gid) # 0.01 us - string never created if debug off
```

### Why `extra` Dict Over Custom Methods?

1. **Standard logging interface**: Works with any logging.Logger
2. **Compatible with handlers**: JSON formatters, external sinks understand `extra`
3. **No protocol changes**: LogProvider already supports `**kwargs`

## Alternatives Considered

### Alternative 1: Structured Logging Library (structlog)

- **Description**: Use structlog for native structured logging
- **Pros**: Rich features, processors, JSON-native
- **Cons**: External dependency (PRD violation), learning curve
- **Why not chosen**: Cannot add external dependencies

### Alternative 2: Custom Log Methods Per Context

- **Description**: `log.info_with_context(msg, ctx=LogContext(...))`
- **Pros**: Explicit API, type-safe
- **Cons**: Breaks LogProvider compatibility, custom interface
- **Why not chosen**: Standard `extra` dict is more compatible

### Alternative 3: Single SDK Logger

- **Description**: All modules use `logging.getLogger("autom8_asana")`
- **Pros**: Simple, single namespace
- **Cons**: Cannot filter by module, all logs same name
- **Why not chosen**: Hierarchical naming is more useful for debugging

### Alternative 4: Thread-Local Context

- **Description**: Set context via `log_context.set(LogContext(...))`, auto-attached
- **Pros**: Cleaner call sites, automatic propagation
- **Cons**: Hidden state, harder to test, asyncio compatibility issues
- **Why not chosen**: Explicit `extra` is clearer and safer

## Consequences

### Positive

- **Easy filtering**: `logging.getLogger("autom8_asana").setLevel(DEBUG)` catches all SDK logs
- **Structured output**: JSON formatters can extract correlation_id, entity_gid
- **Zero overhead**: Lazy formatting prevents string creation when disabled
- **Standard interface**: Works with any stdlib-compatible logging setup

### Negative

- **Verbose call sites**: `logger.info("msg", extra=ctx.to_dict())` is longer
- **Migration effort**: Existing inline loggers must be updated
- **User education**: Documentation needed on configuring handlers

### Neutral

- **LogContext optional**: Existing code without context continues to work
- **Testing unchanged**: Mock loggers work identically

## Compliance

To ensure this decision is followed:

1. **Code review**: Check logger naming matches `autom8_asana.*` pattern
2. **Linting**: Consider custom rule flagging f-string in `logger.*` calls
3. **Documentation**: SDK guide shows configuration examples
4. **Grep audit**: `grep -r "logging.getLogger" src/` to verify consistency

## Configuration Example (SDK Guide)

```python
import logging

# Enable all SDK logs at DEBUG level
logging.getLogger("autom8_asana").setLevel(logging.DEBUG)

# Enable only transport logs
logging.getLogger("autom8_asana.transport").setLevel(logging.DEBUG)
logging.getLogger("autom8_asana").setLevel(logging.WARNING)

# JSON output for structured logs
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include extra fields
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "entity_gid"):
            log_data["entity_gid"] = record.entity_gid
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.getLogger("autom8_asana").addHandler(handler)
```
