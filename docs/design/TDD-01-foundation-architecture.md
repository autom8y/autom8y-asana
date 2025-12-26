# TDD-01: Foundation & SDK Architecture

> Consolidated Technical Design Document covering SDK extraction strategy and backward compatibility.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: TDD-SDK-FAMILY, TDD-0006
- **Related ADRs**: ADR-0029 (Foundation Architecture), ADR-0052 (Protocol Extensibility)

---

## Overview

The autom8_asana SDK provides an async-first Asana API client extracted from the autom8 monolith. The architecture enables standalone SDK usage while supporting gradual migration from existing autom8 integrations through backward-compatible import aliases and protocol-based dependency injection.

**Key outcomes**:
- Zero coupling between SDK and consumers via `typing.Protocol`
- Clean separation between SDK infrastructure and business domain logic
- Backward-compatible migration path with deprecation warnings
- Explicit public API surface with semantic versioning guarantees

---

## Design Goals

### From SDK Extraction (TDD-SDK-FAMILY)

1. **Async-first design**: All operations are `async` by default with sync wrappers for convenience
2. **Protocol-based extensibility**: Consumers inject auth, cache, and logging without inheritance
3. **Minimal entity boundary**: SDK provides `AsanaResource`; autom8 extends with business logic
4. **Production resilience**: Circuit breaker, rate limiting, retry with exponential backoff

### From Backward Compatibility (TDD-0006)

1. **Gradual migration**: Import aliases allow incremental adoption without breaking changes
2. **Clear deprecation**: Warnings guide users to canonical import paths
3. **Public API contract**: Explicit `__all__` exports with three-tier visibility model
4. **Standalone operation**: SDK works without autom8 dependencies

---

## Architecture

### Layered Structure

```
autom8_asana/
├── __init__.py               # Public API exports (Tier 1)
├── _compat.py                # Deprecated import aliases (removed in v1.0)
├── client.py                 # AsanaClient facade
├── config.py                 # Configuration dataclasses
├── exceptions.py             # Error hierarchy
│
├── transport/                # HTTP layer
│   ├── http.py               # AsyncHTTPClient (httpx-based)
│   ├── rate_limiter.py       # Token bucket at 1500 req/min
│   ├── retry.py              # Exponential backoff with jitter
│   └── sync.py               # Sync wrapper utilities
│
├── clients/                  # Resource-specific operations
│   ├── tasks.py              # TasksClient
│   ├── projects.py           # ProjectsClient
│   └── ... (13 clients total)
│
├── models/                   # Pydantic v2 models
│   ├── base.py               # AsanaResource base class
│   ├── tasks.py
│   └── ...
│
├── protocols/                # Boundary contracts
│   ├── auth.py               # AuthProvider
│   ├── cache.py              # CacheProvider
│   └── log.py                # LogProvider
│
├── _defaults/                # Default implementations (Tier 3)
│   ├── auth.py               # EnvVarAuthProvider
│   ├── cache.py              # NullCacheProvider, InMemoryCacheProvider
│   └── log.py                # DefaultLogProvider
│
└── examples/                 # Protocol adapter examples (documentation only)
    └── autom8_adapters.py
```

### Data Flow

**Standard Request**:
```
User Code -> AsanaClient -> TasksClient
  -> AsyncHTTPClient -> RateLimiter.acquire()
  -> httpx.AsyncClient -> Asana API
  -> Response -> Pydantic validation -> Task model
```

**Retry on 429**:
```
AsyncHTTPClient -> httpx.request()
  -> 429 + Retry-After: 30
  -> RetryHandler.should_retry(429) -> True
  -> wait(30s + jitter)
  -> httpx.request() (retry)
  -> 200 OK
```

---

## Implementation Details

### Protocol-Based Extensibility

The SDK uses `typing.Protocol` for all extensibility points, enabling structural subtyping without inheritance:

```python
from typing import Protocol

class AuthProvider(Protocol):
    """Protocol for authentication/secret retrieval."""
    def get_secret(self, key: str) -> str: ...

class CacheProvider(Protocol):
    """Protocol for caching operations."""
    def get(self, key: str) -> dict | None: ...
    def set(self, key: str, value: dict, ttl: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...

class LogProvider(Protocol):
    """Protocol for logging, compatible with Python logging.Logger."""
    def debug(self, msg: str, *args, **kwargs) -> None: ...
    def info(self, msg: str, *args, **kwargs) -> None: ...
    def warning(self, msg: str, *args, **kwargs) -> None: ...
    def error(self, msg: str, *args, **kwargs) -> None: ...
```

**Consumer integration** (no SDK inheritance required):
```python
# autom8 can inject without inheriting from Protocol
class Autom8AuthProvider:
    def get_secret(self, key: str) -> str:
        return ENV.SecretManager.get(key)

# SDK accepts it because it matches the Protocol structure
client = AsanaClient(auth_provider=Autom8AuthProvider())

# Python's logging.Logger already matches LogProvider
import logging
client = AsanaClient(log_provider=logging.getLogger("myapp"))
```

### Entity Model Boundary

**SDK layer** (`AsanaResource`):
```python
from pydantic import BaseModel, ConfigDict

class AsanaResource(BaseModel):
    """Base model for all Asana API resources.

    Provides common fields and serialization logic.
    Does NOT include: lazy loading, caching, business logic,
    or database integration.
    """
    model_config = ConfigDict(
        extra="ignore",      # Forward compatibility with API changes
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    gid: str
    resource_type: str

    def to_api_dict(self) -> dict:
        """Serialize to Asana API format."""
        return self.model_dump(exclude_none=True, by_alias=True)

    @classmethod
    def from_api_response(cls, data: dict) -> "AsanaResource":
        """Create instance from Asana API response."""
        return cls.model_validate(data)
```

**Monolith layer** (extends SDK):
```python
# In autom8 (NOT in SDK)
from autom8_asana.models import AsanaResource

class Item(AsanaResource):
    """Full Asana resource with autom8 business logic.

    Extends SDK's AsanaResource with lazy loading, TaskCache,
    business model instantiation, and domain validation.
    """
    _cache: TaskCache  # S3-backed cache
    _lazy_loader: LazyLoader
```

### Circuit Breaker Integration

```python
class AsyncHTTPClient:
    def __init__(self, config, auth_provider, logger, cache_provider):
        # Circuit breaker (opt-in)
        self._circuit_breaker = CircuitBreaker(
            config.circuit_breaker, logger
        ) if config.circuit_breaker.enabled else None

    async def request(self, method: str, path: str, ...) -> dict:
        # Check circuit breaker before request
        if self._circuit_breaker:
            await self._circuit_breaker.check()  # May raise CircuitBreakerOpenError

        attempt = 0
        while True:
            try:
                response = await client.request(...)
                if response.status_code < 400:
                    if self._circuit_breaker:
                        await self._circuit_breaker.record_success()
                    return self._parse_response(response)

                error = AsanaError.from_response(response)
                if self._circuit_breaker:
                    await self._circuit_breaker.record_failure(error)

                if self._retry_handler.should_retry(response.status_code, attempt):
                    await self._retry_handler.wait(attempt, ...)
                    attempt += 1
                    continue
                raise error
            except Exception as e:
                if self._circuit_breaker:
                    await self._circuit_breaker.record_failure(e)
                raise
```

**State Machine**:
```
    CLOSED  --[failure_threshold reached]-->  OPEN
       ^                                        |
       |                                        v
       +--[probe succeeds]-- HALF_OPEN <--[recovery_timeout elapsed]
                                 |
                                 +--[probe fails]--> OPEN (reset timer)
```

---

## API Surface

### Three-Tier Visibility Model

**Tier 1 - Public API** (exported from root, semantic versioning applies):

| Category | Exports | Import Path |
|----------|---------|-------------|
| Main Client | `AsanaClient` | `from autom8_asana import AsanaClient` |
| Configuration | `AsanaConfig`, `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig` | `from autom8_asana import AsanaConfig` |
| Exceptions | `AsanaError`, `AuthenticationError`, `ForbiddenError`, `NotFoundError`, `GoneError`, `RateLimitError`, `ServerError`, `TimeoutError`, `ConfigurationError`, `SyncInAsyncContextError` | `from autom8_asana import AsanaError` |
| Protocols | `AuthProvider`, `CacheProvider`, `LogProvider`, `ItemLoader` | `from autom8_asana import AuthProvider` |
| Batch API | `BatchClient`, `BatchRequest`, `BatchResult`, `BatchSummary` | `from autom8_asana import BatchRequest` |
| Models | All models (Task, Project, User, etc.) | `from autom8_asana import Task` |

**Tier 2 - Semi-Public API** (stable signatures, new methods may be added in minor versions):

| Submodule | Exports | Use Case |
|-----------|---------|----------|
| `autom8_asana.clients` | Individual client classes | Custom client composition |
| `autom8_asana.models` | Individual model classes | Type annotations |
| `autom8_asana.protocols` | Protocol definitions | Custom implementations |
| `autom8_asana.transport` | `AsyncHTTPClient`, `TokenBucketRateLimiter`, `RetryHandler`, `sync_wrapper` | Advanced transport customization |

**Tier 3 - Internal API** (no guarantees, may change without notice):

| Module | Contents | Why Internal |
|--------|----------|--------------|
| `autom8_asana._defaults/` | Default provider implementations | Implementation detail |
| `autom8_asana._internal/` | Concurrency utils, correlation IDs | Implementation detail |
| `autom8_asana._compat.py` | Deprecated import aliases | Migration-only |

### Consistent Client Pattern

All resource clients follow the same structure for predictable usage:

```python
class {Resource}Client(BaseClient):
    """Client for {resource} operations."""

    # === Async primary methods ===
    async def get_async(
        self, {resource}_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None
    ) -> Model | dict[str, Any]: ...

    async def create_async(
        self, data: dict[str, Any], *, raw: bool = False
    ) -> Model | dict[str, Any]: ...

    async def update_async(
        self, {resource}_gid: str, data: dict[str, Any], *, raw: bool = False
    ) -> Model | dict[str, Any]: ...

    async def delete_async(self, {resource}_gid: str) -> None: ...

    # === Sync wrappers ===
    @sync_wrapper
    def get(self, {resource}_gid: str, **kwargs) -> Model | dict[str, Any]: ...

    # === List operations ===
    def list_async(self, *, limit: int = 100, offset: str | None = None) -> PageIterator[Model]: ...
```

---

## Migration & Compatibility

### Backward-Compatible Import Aliases

The `_compat.py` module provides deprecated import paths with clear migration guidance:

```python
"""Backward compatibility layer for gradual migration.

Migration Guide:
    # Old (deprecated):
    from autom8_asana.compat import Task
    from autom8_asana.compat import TasksClient

    # New (canonical):
    from autom8_asana import Task
    from autom8_asana.clients import TasksClient

This module will be removed in version 1.0.0.
"""

def __getattr__(name: str):
    """Lazy attribute access with deprecation warnings."""
    _model_aliases = {
        "Task": "autom8_asana.models.Task",
        "Project": "autom8_asana.models.Project",
        # ... all model aliases
    }

    _client_aliases = {
        "TasksClient": "autom8_asana.clients.TasksClient",
        # ... all client aliases
    }

    if name in all_aliases:
        new_path = all_aliases[name]
        warnings.warn(
            f"Importing '{name}' from 'autom8_asana.compat' is deprecated. "
            f"Use '{new_path}' instead. "
            f"This alias will be removed in version 1.0.0.",
            DeprecationWarning,
            stacklevel=3,  # Points to the actual import statement
        )
        # Perform the actual import...
```

### Protocol Adapter Examples

Example adapters for autom8 integration are provided in `examples/autom8_adapters.py` (documentation only, not shipped in package):

```python
class SecretManagerAuthProvider:
    """AuthProvider adapter wrapping autom8's ENV.SecretManager."""

    def get_secret(self, key: str) -> str:
        value = ENV.SecretManager.get(key)
        if value is None:
            raise AuthenticationError(f"Secret '{key}' not found")
        return value


class S3CacheProvider:
    """CacheProvider adapter wrapping autom8's TaskCache (S3-backed)."""

    def get(self, key: str) -> dict[str, Any] | None:
        return self._cache.get(self._prefixed_key(key))

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        self._cache.set(self._prefixed_key(key), value, ttl=ttl)


# Convenience function for full autom8 integration
def create_autom8_client(**config_overrides):
    return AsanaClient(
        auth_provider=SecretManagerAuthProvider(),
        cache_provider=S3CacheProvider(),
        log_provider=LogAdapter(),
        config=AsanaConfig(**config_overrides) if config_overrides else None,
    )
```

### Migration Timeline

| Phase | Duration | Actions |
|-------|----------|---------|
| **Deprecation** | SDK Release to v0.9 | Deprecation warnings on legacy imports |
| **Migration** | 6 months recommended | Teams update to canonical import paths |
| **Removal** | v1.0.0 | `_compat.py` module removed |

---

## Testing Strategy

### Unit Testing

- Test each protocol implementation matches expected interface
- Test deprecation warnings are emitted with correct message and stacklevel
- Test `__all__` includes all expected names across all public modules
- Test circuit breaker state transitions
- Test rate limiter acquires and releases correctly

### Integration Testing

- Test autom8 adapter examples compile (without autom8 dependencies)
- Test SDK works standalone without autom8
- Test asana package is importable alongside SDK
- Test real Asana API calls via demo suite

### Architecture Testing

```python
def test_no_internal_imports_in_public_modules():
    """Verify public modules don't expose internal imports."""
    import ast
    for module in PUBLIC_MODULES:
        tree = ast.parse(open(module).read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("autom8_asana._")

def test_asana_resource_has_no_business_imports():
    """Verify SDK models don't import business modules."""
    # Block any business logic in SDK models
    ...
```

---

## Cross-References

### Related TDDs

| TDD | Relationship |
|-----|--------------|
| TDD-02 (SaveSession) | Uses protocols for persistence operations |
| TDD-03 (Caching) | Extends CacheProvider protocol with versioning |
| TDD-04 (Custom Fields) | Models follow AsanaResource patterns |

### Related ADRs

| ADR | Decision |
|-----|----------|
| [ADR-0029](../decisions/ADR-0029-foundation-architecture.md) | Foundation architecture (protocol DI, entity boundary, API surface) |
| [ADR-0052](../decisions/ADR-0052-protocol-extensibility.md) | Protocol patterns for cache, observability, automation |
| [ADR-0039](../decisions/ADR-0039-api-design-surface-control.md) | API surface control and deprecation handling |

### Archived Source Documents

| Original | Archive Location |
|----------|------------------|
| TDD-0001-sdk-architecture.md | `docs/.archive/2025-12-tdds/TDD-0001-sdk-architecture.md` |
| TDD-0006-backward-compatibility.md | Superseded by this document |
| TDD-0012-sdk-functional-parity.md | `docs/.archive/2025-12-tdds/TDD-0012-sdk-functional-parity.md` |
| TDD-0014-sdk-ga-readiness.md | `docs/.archive/2025-12-tdds/TDD-0014-sdk-ga-readiness.md` |
| TDD-0029-sdk-demo.md | `docs/.archive/2025-12-tdds/TDD-0029-sdk-demo.md` |

---

**Last Updated**: 2025-12-25 (Consolidation from TDD-SDK-FAMILY and TDD-0006)
