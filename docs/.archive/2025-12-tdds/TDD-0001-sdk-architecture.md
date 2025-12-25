# TDD: autom8_asana SDK Architecture

## Metadata
- **TDD ID**: TDD-0001
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-08
- **Last Updated**: 2025-12-08
- **PRD Reference**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md)
- **Related TDDs**: None (initial design)
- **Related ADRs**:
  - [ADR-0001](../decisions/ADR-0001-protocol-extensibility.md) - Protocol-based extensibility
  - [ADR-0002](../decisions/ADR-0002-sync-wrapper-strategy.md) - Sync wrapper strategy
  - [ADR-0003](../decisions/ADR-0003-asana-sdk-integration.md) - Asana SDK integration approach
  - [ADR-0004](../decisions/ADR-0004-item-class-boundary.md) - Item class boundary
  - [ADR-0005](../decisions/ADR-0005-pydantic-model-config.md) - Pydantic model configuration

## Overview

The autom8_asana SDK extracts pure Asana API functionality from the autom8 monolith into a standalone, reusable package. The architecture follows a layered design with protocol-based dependency injection at the boundaries, enabling the SDK to operate independently while allowing autom8 to inject its infrastructure (secrets, caching, logging) at runtime. The transport layer uses httpx with async-first design, replacing the official Asana SDK's HTTP handling while retaining it for types and error parsing.

## Requirements Summary

This design addresses [PRD-0001](../requirements/PRD-0001-sdk-extraction.md), which defines:

- **68 functional requirements** across transport (FR-SDK-001-015), clients (FR-SDK-016-029), batch API (FR-SDK-030-035), models (FR-SDK-036-040), error handling (FR-SDK-041-045), boundary protocols (FR-BOUNDARY-001-007), and compatibility (FR-COMPAT-001-008)
- **8 non-functional requirements** covering package size (<5MB), import time (<500ms), test coverage (>=80%), Python version support (3.10, 3.11), type coverage (100% public API), and zero coupling to autom8 internals
- **Key constraint**: Zero imports from `sql/`, `contente_api/`, `aws_api/`

## System Context

The SDK sits between consuming applications and the Asana API, providing a clean abstraction over HTTP transport with protocol-based integration points.

```
+-------------------+       +-------------------+       +-------------------+
|                   |       |                   |       |                   |
|  autom8 Monolith  |       |  New Microservice |       |   CLI/Scripts     |
|                   |       |                   |       |                   |
+--------+----------+       +--------+----------+       +--------+----------+
         |                           |                           |
         | Injects providers         | Uses defaults             | Uses defaults
         |                           |                           |
         v                           v                           v
+------------------------------------------------------------------------+
|                                                                        |
|                         autom8_asana SDK                               |
|                                                                        |
|  +------------------+  +------------------+  +------------------+       |
|  | AuthProvider     |  | CacheProvider    |  | LogProvider      |       |
|  | (Protocol)       |  | (Protocol)       |  | (Protocol)       |       |
|  +------------------+  +------------------+  +------------------+       |
|                                                                        |
+------------------------------------------------------------------------+
                                    |
                                    | HTTP/TLS
                                    v
                         +-------------------+
                         |                   |
                         |    Asana API      |
                         |                   |
                         +-------------------+
```

### Integration Points

| Integration Point | Protocol | autom8 Implementation | Standalone Default |
|-------------------|----------|----------------------|-------------------|
| Authentication | `AuthProvider` | `ENV.SecretManager` wrapper | `EnvAuthProvider` (env vars) |
| Caching | `CacheProvider` | `TaskCache` (S3-backed) | `NullCacheProvider` (no-op) |
| Logging | `LogProvider` | `LOG` wrapper | `DefaultLogProvider` (stdlib) |

## Design

### Component Architecture

```
autom8_asana/
|
+-- __init__.py              # Public API exports
+-- client.py                # AsanaClient facade
+-- config.py                # Configuration dataclasses
+-- exceptions.py            # Error hierarchy
+-- _compat.py               # Import aliases for migration
|
+-- transport/               # HTTP Layer (FR-SDK-001-015)
|   +-- __init__.py
|   +-- http.py              # AsyncHTTPClient (httpx wrapper)
|   +-- rate_limiter.py      # TokenBucketRateLimiter
|   +-- retry.py             # RetryHandler with exponential backoff
|   +-- sync.py              # sync_wrapper decorator
|
+-- clients/                 # Resource Clients (FR-SDK-016-029)
|   +-- __init__.py
|   +-- base.py              # BaseClient abstract class
|   +-- tasks.py             # TasksClient
|   +-- projects.py          # ProjectsClient
|   +-- sections.py          # SectionsClient
|   +-- custom_fields.py     # CustomFieldsClient
|   +-- webhooks.py          # WebhooksClient
|   +-- users.py             # UsersClient
|   +-- teams.py             # TeamsClient
|   +-- attachments.py       # AttachmentsClient
|   +-- tags.py              # TagsClient
|   +-- goals.py             # GoalsClient
|   +-- portfolios.py        # PortfoliosClient
|   +-- workspaces.py        # WorkspacesClient
|   +-- stories.py           # StoriesClient
|
+-- batch/                   # Batch API (FR-SDK-030-035)
|   +-- __init__.py
|   +-- client.py            # BatchClient
|   +-- request.py           # BatchRequest builder
|
+-- models/                  # Data Models (FR-SDK-036-040)
|   +-- __init__.py
|   +-- base.py              # AsanaResource, NameGid
|   +-- common.py            # PageIterator, pagination helpers
|   +-- tasks.py             # Task model
|   +-- projects.py          # Project model
|   +-- users.py             # User model
|   +-- ... (other resources)
|
+-- protocols/               # Boundary Protocols (FR-BOUNDARY-001-007)
|   +-- __init__.py
|   +-- auth.py              # AuthProvider protocol
|   +-- cache.py             # CacheProvider protocol
|   +-- log.py               # LogProvider protocol
|
+-- _defaults/               # Default Implementations
|   +-- __init__.py
|   +-- auth.py              # EnvAuthProvider, NotConfiguredAuthProvider
|   +-- cache.py             # NullCacheProvider, InMemoryCacheProvider
|   +-- log.py               # DefaultLogProvider
|
+-- _internal/               # Internal Utilities (not public API)
|   +-- __init__.py
|   +-- concurrency.py       # Semaphores for read/write limits
|   +-- correlation.py       # Request correlation IDs
```

### Layer Responsibilities

| Layer | Responsibility | Key Classes |
|-------|---------------|-------------|
| **Transport** | HTTP communication, connection pooling, rate limiting, retry logic, sync wrappers | `AsyncHTTPClient`, `TokenBucketRateLimiter`, `RetryHandler` |
| **Clients** | Resource-specific API operations, request building, response parsing | `TasksClient`, `ProjectsClient`, etc. |
| **Batch** | Batch request composition, chunking, partial failure handling | `BatchClient`, `BatchRequest` |
| **Models** | Data validation, serialization, Asana API format conversion | `AsanaResource`, `Task`, `Project` |
| **Protocols** | Boundary contracts for DI | `AuthProvider`, `CacheProvider`, `LogProvider` |
| **Defaults** | Fallback implementations for standalone use | `EnvAuthProvider`, `NullCacheProvider` |

### Data Model

#### Core Models

```python
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class AsanaResource(BaseModel):
    """Base model for all Asana resources."""
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    gid: str
    resource_type: str

class NameGid(BaseModel):
    """Lightweight reference to an Asana resource."""
    model_config = ConfigDict(extra="ignore")

    gid: str
    name: str

class Task(AsanaResource):
    """Asana Task model."""
    resource_type: str = "task"
    name: str
    notes: Optional[str] = None
    completed: bool = False
    due_on: Optional[str] = None  # YYYY-MM-DD
    due_at: Optional[datetime] = None
    assignee: Optional[NameGid] = None
    projects: list[NameGid] = []
    parent: Optional[NameGid] = None
    custom_fields: list[dict] = []
    # ... additional fields
```

#### PageIterator

```python
from typing import TypeVar, Generic, AsyncIterator, Callable, Awaitable

T = TypeVar("T")

class PageIterator(Generic[T], AsyncIterator[T]):
    """Async iterator for paginated Asana API responses.

    Usage:
        async for task in client.tasks.list(project="123"):
            print(task.name)

        # Or collect all:
        tasks = [t async for t in client.tasks.list(project="123")]
    """

    def __init__(
        self,
        fetch_page: Callable[[str | None], Awaitable[tuple[list[T], str | None]]],
        page_size: int = 100,
    ):
        self._fetch_page = fetch_page
        self._page_size = page_size
        self._buffer: list[T] = []
        self._next_page: str | None = None
        self._exhausted = False
        self._started = False

    def __aiter__(self) -> "PageIterator[T]":
        return self

    async def __anext__(self) -> T:
        if not self._buffer and not self._exhausted:
            await self._fetch_next_page()

        if not self._buffer:
            raise StopAsyncIteration

        return self._buffer.pop(0)

    async def _fetch_next_page(self) -> None:
        if self._exhausted:
            return

        items, next_page = await self._fetch_page(
            self._next_page if self._started else None
        )
        self._started = True
        self._buffer.extend(items)
        self._next_page = next_page

        if next_page is None:
            self._exhausted = True
```

### API Contracts

#### AsanaClient Facade

```python
class AsanaClient:
    """Main entry point for the autom8_asana SDK.

    Example:
        # Standalone usage
        client = AsanaClient(token="xoxp-...")

        # With custom providers (autom8 integration)
        client = AsanaClient(
            auth_provider=MyAuthProvider(),
            cache_provider=MyCacheProvider(),
            log_provider=MyLogProvider(),
        )

        # Async usage
        async with client:
            task = await client.tasks.get_async("task_gid")

        # Sync usage
        task = client.tasks.get("task_gid")
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        auth_provider: AuthProvider | None = None,
        cache_provider: CacheProvider | None = None,
        log_provider: LogProvider | None = None,
        config: AsanaConfig | None = None,
    ) -> None: ...

    # Resource clients (lazy-initialized)
    @property
    def tasks(self) -> TasksClient: ...

    @property
    def projects(self) -> ProjectsClient: ...

    @property
    def sections(self) -> SectionsClient: ...

    @property
    def custom_fields(self) -> CustomFieldsClient: ...

    @property
    def webhooks(self) -> WebhooksClient: ...

    @property
    def users(self) -> UsersClient: ...

    @property
    def teams(self) -> TeamsClient: ...

    @property
    def attachments(self) -> AttachmentsClient: ...

    @property
    def tags(self) -> TagsClient: ...

    @property
    def goals(self) -> GoalsClient: ...

    @property
    def portfolios(self) -> PortfoliosClient: ...

    @property
    def workspaces(self) -> WorkspacesClient: ...

    @property
    def stories(self) -> StoriesClient: ...

    @property
    def batch(self) -> BatchClient: ...

    # Context manager for connection lifecycle
    async def __aenter__(self) -> "AsanaClient": ...
    async def __aexit__(self, *args) -> None: ...

    # Sync context manager
    def __enter__(self) -> "AsanaClient": ...
    def __exit__(self, *args) -> None: ...
```

#### TasksClient Example

```python
class TasksClient(BaseClient):
    """Client for Asana Task operations."""

    # Async methods (primary API)
    async def get_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
    ) -> Task: ...

    async def create_async(
        self,
        *,
        name: str,
        projects: list[str] | None = None,
        assignee: str | None = None,
        notes: str | None = None,
        due_on: str | None = None,
        parent: str | None = None,
        custom_fields: dict[str, str] | None = None,
        **kwargs,
    ) -> Task: ...

    async def update_async(
        self,
        task_gid: str,
        *,
        name: str | None = None,
        completed: bool | None = None,
        notes: str | None = None,
        due_on: str | None = None,
        assignee: str | None = None,
        **kwargs,
    ) -> Task: ...

    async def delete_async(self, task_gid: str) -> None: ...

    def list(
        self,
        *,
        project: str | None = None,
        section: str | None = None,
        assignee: str | None = None,
        workspace: str | None = None,
        opt_fields: list[str] | None = None,
    ) -> PageIterator[Task]: ...

    async def search_async(
        self,
        workspace: str,
        *,
        text: str | None = None,
        assignee: str | None = None,
        projects: list[str] | None = None,
        completed: bool | None = None,
        **kwargs,
    ) -> list[Task]: ...

    # Sync wrappers (convenience API)
    def get(self, task_gid: str, **kwargs) -> Task: ...
    def create(self, **kwargs) -> Task: ...
    def update(self, task_gid: str, **kwargs) -> Task: ...
    def delete(self, task_gid: str) -> None: ...
    def search(self, workspace: str, **kwargs) -> list[Task]: ...
```

#### Protocol Definitions

```python
from typing import Protocol, TypeVar

T = TypeVar("T")

class AuthProvider(Protocol):
    """Protocol for authentication/secret retrieval."""

    def get_secret(self, key: str) -> str:
        """Retrieve a secret value by key.

        Args:
            key: Secret identifier (e.g., "ASANA_PAT")

        Returns:
            Secret value as string

        Raises:
            AuthenticationError: If secret not found
        """
        ...


class CacheProvider(Protocol):
    """Protocol for caching operations."""

    def get(self, key: str) -> dict | None:
        """Retrieve value from cache."""
        ...

    def set(self, key: str, value: dict, ttl: int | None = None) -> None:
        """Store value in cache."""
        ...

    def delete(self, key: str) -> None:
        """Remove value from cache."""
        ...


class LogProvider(Protocol):
    """Protocol for logging, compatible with Python logging.Logger."""

    def debug(self, msg: str, *args, **kwargs) -> None: ...
    def info(self, msg: str, *args, **kwargs) -> None: ...
    def warning(self, msg: str, *args, **kwargs) -> None: ...
    def error(self, msg: str, *args, **kwargs) -> None: ...
    def exception(self, msg: str, *args, **kwargs) -> None: ...
```

### Data Flow

#### Standard Request Flow

```
User Code                AsanaClient              Transport              Asana API
    |                         |                       |                      |
    | tasks.get_async("123")  |                       |                      |
    |------------------------>|                       |                      |
    |                         | build_request()       |                      |
    |                         |---+                   |                      |
    |                         |   |                   |                      |
    |                         |<--+                   |                      |
    |                         |                       |                      |
    |                         | http.request()        |                      |
    |                         |---------------------->|                      |
    |                         |                       | rate_limit.acquire() |
    |                         |                       |---+                  |
    |                         |                       |<--+                  |
    |                         |                       |                      |
    |                         |                       | GET /tasks/123      |
    |                         |                       |--------------------->|
    |                         |                       |                      |
    |                         |                       | 200 OK + JSON       |
    |                         |                       |<---------------------|
    |                         |                       |                      |
    |                         | Task.model_validate() |                      |
    |                         |<----------------------|                      |
    |                         |                       |                      |
    | Task                    |                       |                      |
    |<------------------------|                       |                      |
```

#### Retry Flow (429 Rate Limited)

```
Transport                RateLimiter              RetryHandler              Asana API
    |                         |                       |                         |
    | request()               |                       |                         |
    |------------------------>|                       |                         |
    |                         | acquire()             |                         |
    |                         |---+                   |                         |
    |                         |<--+                   |                         |
    |                         |                       |                         |
    |                         | GET /tasks/...        |                         |
    |                         |------------------------------------------------>|
    |                         |                       |                         |
    |                         | 429 + Retry-After: 30 |                         |
    |                         |<------------------------------------------------|
    |                         |                       |                         |
    |                         | should_retry(429)     |                         |
    |                         |---------------------->|                         |
    |                         |                       | True                    |
    |                         |<----------------------|                         |
    |                         |                       |                         |
    |                         | wait(30s + jitter)    |                         |
    |                         |---+                   |                         |
    |                         |<--+ (sleep)           |                         |
    |                         |                       |                         |
    |                         | GET /tasks/... (retry)|                         |
    |                         |------------------------------------------------>|
    |                         |                       |                         |
    |                         | 200 OK                |                         |
    |                         |<------------------------------------------------|
```

#### Sync Wrapper Flow

```
User Code                  sync_wrapper              asyncio
    |                           |                       |
    | tasks.get("123")          |                       |
    |-------------------------->|                       |
    |                           |                       |
    |                           | get_running_loop()    |
    |                           |---------------------->|
    |                           |                       |
    |                           | RuntimeError: no loop |
    |                           |<----------------------|
    |                           |                       |
    |                           | asyncio.run(          |
    |                           |   tasks.get_async()   |
    |                           | )                     |
    |                           |---------------------->|
    |                           |                       |
    |                           | Task                  |
    |                           |<----------------------|
    |                           |                       |
    | Task                      |                       |
    |<--------------------------|                       |


# If called from async context:

User Code                  sync_wrapper              asyncio
    |                           |                       |
    | tasks.get("123")          |                       |
    |-------------------------->|                       |
    |                           |                       |
    |                           | get_running_loop()    |
    |                           |---------------------->|
    |                           |                       |
    |                           | <loop object>         |
    |                           |<----------------------|
    |                           |                       |
    | RuntimeError: Cannot call |                       |
    | sync from async context   |                       |
    |<--------------------------|                       |
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Extensibility mechanism | `typing.Protocol` | Structural subtyping allows any compatible class without inheritance | [ADR-0001](../decisions/ADR-0001-protocol-extensibility.md) |
| Sync wrapper behavior | Fail-fast in async context | Prevents deadlocks and accidental blocking | [ADR-0002](../decisions/ADR-0002-sync-wrapper-strategy.md) |
| Asana SDK usage | Replace HTTP, keep types/errors | Better control over transport while leveraging existing type definitions | [ADR-0003](../decisions/ADR-0003-asana-sdk-integration.md) |
| Item class boundary | Minimal `AsanaResource` in SDK | Avoids coupling SDK to business domain; autom8 keeps full Item | [ADR-0004](../decisions/ADR-0004-item-class-boundary.md) |
| Pydantic configuration | `extra="ignore"` | Forward compatibility with API changes; SDK ignores unknown fields | [ADR-0005](../decisions/ADR-0005-pydantic-model-config.md) |

## Complexity Assessment

**Level**: SERVICE

**Justification**:
- Multiple layers with explicit contracts (transport, clients, models, protocols)
- Dependency injection through protocols
- Configuration management for timeouts, rate limits, retry behavior
- Observability requirements (logging, metrics, correlation IDs)
- Thread safety requirements for concurrent access
- Not a full platform (no multi-service orchestration, no infrastructure provisioning)

This complexity level is appropriate because:
1. The SDK is a reusable library consumed by multiple services
2. It has production operational requirements (rate limiting, retry, logging)
3. It must be backward-compatible with existing autom8 code
4. It requires explicit boundary definitions for clean separation

## Implementation Plan

### Phase 1: Foundation (Days 1-2)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Package structure and `pyproject.toml` | None | 2h |
| Protocol definitions (`protocols/`) | None | 2h |
| Default implementations (`_defaults/`) | Protocols | 3h |
| Configuration dataclasses (`config.py`) | None | 2h |
| Exception hierarchy (`exceptions.py`) | None | 2h |

**Exit Criteria**: Package installs, protocols defined, basic structure in place.

### Phase 2: Transport Layer (Days 3-4)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `AsyncHTTPClient` with httpx | Config | 4h |
| `TokenBucketRateLimiter` | None | 3h |
| `RetryHandler` with exponential backoff | None | 3h |
| `sync_wrapper` decorator | None | 2h |
| Concurrency semaphores (`_internal/`) | None | 2h |

**Exit Criteria**: HTTP requests work with rate limiting and retry. Sync wrappers functional.

### Phase 3: Models & Base Client (Days 5-6)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `AsanaResource` and `NameGid` base models | Pydantic | 2h |
| `PageIterator` | None | 3h |
| `BaseClient` abstract class | Transport | 3h |
| Core resource models (Task, Project, User) | Base models | 4h |

**Exit Criteria**: Models validate Asana responses. BaseClient provides common functionality.

### Phase 4: Resource Clients (Days 7-9)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `TasksClient` | BaseClient, Task model | 4h |
| `ProjectsClient` | BaseClient, Project model | 3h |
| `SectionsClient` | BaseClient | 2h |
| `CustomFieldsClient` | BaseClient | 3h |
| `WebhooksClient` (with signature verification) | BaseClient | 4h |
| Remaining clients (Users, Teams, etc.) | BaseClient | 6h |
| `BatchClient` | BaseClient | 4h |

**Exit Criteria**: All 13 resource clients implemented with full CRUD operations.

### Phase 5: Integration & Polish (Days 10-12)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `AsanaClient` facade | All clients | 3h |
| Import aliases (`_compat.py`) | All modules | 2h |
| Public API exports (`__init__.py`) | All modules | 2h |
| Integration tests with Asana API | All components | 8h |
| Documentation and type stubs | All components | 4h |

**Exit Criteria**: Full SDK functional. Integration tests pass. Public API stable.

### Migration Strategy

The SDK enables incremental migration from autom8:

1. **Day 1**: autom8 adds `autom8_asana` dependency
2. **Week 1**: autom8 implements protocol adapters:
   ```python
   # autom8/asana_adapters.py
   from autom8_asana.protocols import AuthProvider, CacheProvider

   class Autom8AuthProvider:
       def get_secret(self, key: str) -> str:
           return ENV.SecretManager.get(key)

   class Autom8CacheProvider:
       def get(self, key: str) -> dict | None:
           return TaskCache.get(key)
       # ...
   ```
3. **Week 2-4**: Replace client imports one at a time:
   ```python
   # Before
   from apis.asana_api.clients.tasks import TasksClient

   # After
   from autom8_asana import AsanaClient
   client = AsanaClient(auth_provider=Autom8AuthProvider())
   ```
4. **Week 5+**: Remove old code as SDK adoption completes

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Asana API changes break SDK | High | Low | `extra="ignore"` in Pydantic; version pin in deps; integration tests |
| Performance regression vs. current code | Medium | Medium | Benchmark critical paths; connection pooling; async by default |
| autom8 migration introduces bugs | High | Medium | Incremental migration; feature flags; parallel running period |
| Rate limiting logic differs from current | Medium | Low | Port exact algorithm; integration tests against live API |
| Type definitions drift from Asana SDK | Low | Medium | Generate types from OpenAPI spec; periodic sync checks |

## Observability

### Logging
All operations log at appropriate levels:
- **DEBUG**: Request/response details, cache hits/misses
- **INFO**: API calls made, batch operations started/completed
- **WARNING**: Rate limit approached, retry attempted, cache miss on expected hit
- **ERROR**: Request failed after retries, authentication failure

Log format includes:
- Correlation ID (for request tracing)
- Operation name (e.g., `tasks.create`)
- Duration (ms)
- Response status code

### Metrics
Expose metrics for:
- `asana_requests_total` (counter, labels: method, resource, status)
- `asana_request_duration_seconds` (histogram, labels: method, resource)
- `asana_rate_limit_remaining` (gauge)
- `asana_retry_total` (counter, labels: reason)
- `asana_cache_hit_total` / `asana_cache_miss_total` (counters)

### Alerting Triggers
- Rate limit utilization > 80%
- Error rate > 5% over 5 minutes
- P95 latency > 2s

## Testing Strategy

### Unit Testing (Target: 90% coverage)
- Protocol implementations
- Rate limiter token bucket logic
- Retry handler decision logic
- Sync wrapper behavior
- Model validation
- PageIterator edge cases

### Integration Testing (Target: 80% coverage)
- End-to-end flows with httpx mock server
- Pagination across multiple pages
- Batch operations with partial failures
- Retry behavior with simulated 429/503/504

### Contract Testing
- Validate SDK models against Asana API responses
- Snapshot tests for API response parsing

### Performance Testing
- Cold import time measurement
- Connection pool efficiency
- Rate limiter throughput under load
- Memory usage with large paginated results

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should we expose metrics as Prometheus format or generic interface? | Architect | Before Phase 5 | TBD |
| What's the minimum Python version for type syntax (`list[str]` vs `List[str]`)? | Engineer | Before Phase 1 | Assume 3.10+ per PRD |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-08 | Architect | Initial design |
