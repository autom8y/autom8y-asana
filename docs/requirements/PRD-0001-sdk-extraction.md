# PRD: autom8_asana SDK Extraction

## Metadata
- **PRD ID**: PRD-0001
- **Status**: Approved
- **Author**: Requirements Analyst
- **Created**: 2025-12-08
- **Last Updated**: 2025-12-08
- **Stakeholders**: autom8 team, SDK consumers
- **Related PRDs**: None (initial PRD)

## Problem Statement

The autom8 monolith contains a tightly coupled Asana API integration (~798 files) that mixes pure API operations with business logic, SQL integrations, and AWS caching. This coupling creates several problems:

1. **Reusability**: Other services cannot use Asana functionality without pulling in autom8's business logic, database dependencies, and AWS integrations.
2. **Testability**: Testing Asana operations requires mocking SQL, S3, and business-specific code paths.
3. **Maintainability**: Changes to Asana API handling risk breaking business logic, and vice versa.
4. **Deployment**: The monolith must be deployed as a unit even for Asana-only changes.

**Impact of not solving**: Continued tight coupling will slow feature development, increase test complexity, and prevent Asana functionality from being reused in new microservices.

## Goals & Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Import footprint | Zero imports from `sql/`, `contente_api/`, `aws_api/` | Static analysis of SDK package |
| Test coverage | >= 80% on core modules | pytest-cov report |
| API parity | All current asana_api operations supported | Feature matrix comparison |
| Migration path | autom8 can adopt incrementally without rewrites | Integration test suite |
| Package size | < 5MB wheel | `pip wheel` output |
| Cold import time | < 500ms | `python -c "import time; t=time.time(); import autom8_asana; print(time.time()-t)"` |

## Scope

### In Scope

**Moves to SDK (`autom8_asana` package)**:
- `clients/*` - All API client wrappers (Tasks, Projects, Sections, Webhooks, Users, Teams, Custom Fields, Attachments, Tags, Goals, Portfolios, Workspaces, Stories)
- `asana_utils/error.py, enums.py, converter.py` - Error handling, enums, data converters
- `objects/generics/base` - Base classes for Asana resources
- Core `Item` class (lazy loading hooks only, no business logic)
- `batch_api/*` - Batch operation support
- Transport layer (connection pooling, retry logic, rate limiting)
- Protocol definitions for AuthProvider, CacheProvider, LogProvider
- Default no-op implementations for all protocols

**Protocol contracts (boundary definitions)**:
- `AuthProvider` - Token/secret retrieval interface
- `CacheProvider` - Get/set/delete caching interface
- `LogProvider` - Python logging-compatible interface

**Backward compatibility layer**:
- Import aliases for gradual migration
- Same public API signatures where possible
- autom8 injects protocol implementations at runtime

### Out of Scope

**Stays in autom8 monolith**:
- `objects/task/models/*` - Domain-specific task types (Offer, Business, Unit, Contact, etc.)
- `objects/task/managers/*` - Ad managers, insights exporters, process managers
- `objects/project/models/*` - Project-specific business logic
- `objects/custom_field/models/*` - Custom field mappings to business concepts
- All SQL integrations (`sql/` imports)
- All AWS caching integrations (`aws_api/` imports)
- All content API integrations (`contente_api/` imports)
- Slack/OpenAI/Meta integrations triggered by Asana events
- Business-coupled parts of Item class (business model instantiation, domain validation)

**Explicitly not in this PRD**:
- Publishing to public PyPI (internal CodeArtifact only)
- Breaking changes to autom8's external API contracts
- Async-only API (sync wrappers required for compatibility)
- Custom HTTP client implementations (httpx is required)

## Requirements

### Functional Requirements - SDK Core (FR-SDK-*)

#### Transport Layer (FR-SDK-001 to FR-SDK-005)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SDK-001 | SDK shall provide connection pooling for HTTP requests | Must | Connection pool reuses connections across requests; configurable pool size |
| FR-SDK-002 | SDK shall use httpx as the HTTP client with async-first design | Must | All HTTP operations use httpx; async methods are primary API |
| FR-SDK-003 | SDK shall provide sync wrappers for all async operations | Must | Every async method has a corresponding sync wrapper; sync API is fully functional |
| FR-SDK-004 | SDK shall support SSL/TLS configuration | Must | SSL verification enabled by default; configurable cert paths |
| FR-SDK-005 | SDK shall support configurable timeouts | Must | Connect, read, and write timeouts independently configurable; sensible defaults |

#### Rate Limiting & Retry (FR-SDK-006 to FR-SDK-012)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SDK-006 | SDK shall implement token-bucket rate limiting at 1500 requests/minute | Must | Rate limiter prevents exceeding 1500 req/min per Asana API limits |
| FR-SDK-007 | SDK shall automatically retry on HTTP 429 (Too Many Requests) | Must | 429 responses trigger exponential backoff retry; max retries configurable |
| FR-SDK-008 | SDK shall automatically retry on HTTP 503 (Service Unavailable) | Must | 503 responses trigger retry with backoff |
| FR-SDK-009 | SDK shall automatically retry on HTTP 504 (Gateway Timeout) | Must | 504 responses trigger retry with backoff |
| FR-SDK-010 | SDK shall implement exponential backoff with jitter | Must | Retry delays follow exponential backoff with random jitter to prevent thundering herd |
| FR-SDK-011 | SDK shall respect Retry-After headers when present | Should | If Asana returns Retry-After, SDK waits at least that duration |
| FR-SDK-012 | SDK shall provide hooks for rate limit events | Should | Consumers can register callbacks for rate limit warnings/events |

#### Concurrency Control (FR-SDK-013 to FR-SDK-015)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SDK-013 | SDK shall limit concurrent read operations to 50 | Must | Semaphore limits concurrent GET requests to 50 |
| FR-SDK-014 | SDK shall limit concurrent write operations to 15 | Must | Semaphore limits concurrent POST/PUT/DELETE requests to 15 |
| FR-SDK-015 | SDK shall be thread-safe for concurrent access | Must | Multiple threads can safely share a single client instance |

#### Client Layer (FR-SDK-016 to FR-SDK-029)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SDK-016 | SDK shall provide TasksClient for task CRUD operations | Must | Create, read, update, delete, list tasks; search tasks; add/remove followers |
| FR-SDK-017 | SDK shall provide ProjectsClient for project operations | Must | Create, read, update, delete, list projects; manage project memberships |
| FR-SDK-018 | SDK shall provide SectionsClient for section operations | Must | Create, read, update, delete sections; move tasks between sections |
| FR-SDK-019 | SDK shall provide CustomFieldsClient for custom field operations | Must | Create, read, update custom fields; get custom field settings for projects |
| FR-SDK-020 | SDK shall provide WebhooksClient for webhook management | Must | Create, delete, list webhooks; webhook signature verification |
| FR-SDK-021 | SDK shall provide UsersClient for user operations | Must | Get user by ID; list users in workspace; get current user |
| FR-SDK-022 | SDK shall provide TeamsClient for team operations | Must | List teams; get team by ID; list team members |
| FR-SDK-023 | SDK shall provide AttachmentsClient for attachment operations | Must | Upload, download, delete attachments; list task attachments |
| FR-SDK-024 | SDK shall provide TagsClient for tag operations | Should | Create, read, update, delete tags; add/remove tags from tasks |
| FR-SDK-025 | SDK shall provide GoalsClient for goal operations | Should | Create, read, update goals; list goals; manage goal memberships |
| FR-SDK-026 | SDK shall provide PortfoliosClient for portfolio operations | Should | Create, read, update portfolios; add/remove projects from portfolios |
| FR-SDK-027 | SDK shall provide WorkspacesClient for workspace operations | Must | Get workspace by ID; list workspaces for user |
| FR-SDK-028 | SDK shall provide StoriesClient for story/comment operations | Should | Create comments; list stories on tasks |
| FR-SDK-029 | SDK shall provide a unified AsanaClient facade | Must | Single entry point that provides access to all resource clients |

#### Batch API (FR-SDK-030 to FR-SDK-035)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SDK-030 | SDK shall support Asana Batch API for bulk operations | Must | Batch multiple requests into single API call |
| FR-SDK-031 | SDK shall automatically chunk batch requests to Asana limits | Must | Batches exceeding Asana's limit are automatically split |
| FR-SDK-032 | SDK shall support batch create operations | Must | Create multiple tasks/resources in single batch |
| FR-SDK-033 | SDK shall support batch update operations | Must | Update multiple tasks/resources in single batch |
| FR-SDK-034 | SDK shall handle partial batch failures gracefully | Must | Individual failures in batch don't fail entire batch; failures reported per-item |
| FR-SDK-035 | SDK shall support automatic pagination for list operations | Must | Large result sets automatically paginated; iterator interface for results |

#### Models Layer (FR-SDK-036 to FR-SDK-040)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SDK-036 | SDK shall provide NameGid model for resource references | Must | Lightweight model with name and gid fields; used for relationship references |
| FR-SDK-037 | SDK shall provide base model class for all Asana resources | Must | Common fields (gid, resource_type) and serialization logic |
| FR-SDK-038 | SDK shall provide core Item class with lazy loading hooks | Must | Item class supports lazy loading via protocol; no business logic |
| FR-SDK-039 | SDK shall use Pydantic v2 for all models | Must | All models inherit from Pydantic BaseModel; validation on instantiation |
| FR-SDK-040 | SDK shall support model serialization to/from Asana API format | Must | Models can serialize to dict for API calls; can deserialize API responses |

#### Error Handling (FR-SDK-041 to FR-SDK-045)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SDK-041 | SDK shall define AsanaError base exception | Must | All SDK exceptions inherit from AsanaError |
| FR-SDK-042 | SDK shall define specific exceptions for common error cases | Must | RateLimitError, AuthenticationError, NotFoundError, ValidationError |
| FR-SDK-043 | SDK shall preserve original Asana API error details | Must | Exception includes HTTP status, error message, request ID from Asana |
| FR-SDK-044 | SDK shall provide ErrorHandler decorator for consistent handling | Should | Decorator that wraps API calls with standard error handling |
| FR-SDK-045 | SDK shall log errors with correlation IDs | Should | All errors logged with unique correlation ID for tracing |

### Functional Requirements - Boundary Protocols (FR-BOUNDARY-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-BOUNDARY-001 | SDK shall define AuthProvider protocol with get_secret method | Must | Protocol defines `get_secret(key: str) -> str` method signature |
| FR-BOUNDARY-002 | SDK shall define CacheProvider protocol with get method | Must | Protocol defines `get(key: str) -> Optional[T]` method signature |
| FR-BOUNDARY-003 | SDK shall define CacheProvider protocol with set method | Must | Protocol defines `set(key: str, value: T, ttl: Optional[int]) -> None` method signature |
| FR-BOUNDARY-004 | SDK shall define CacheProvider protocol with delete method | Must | Protocol defines `delete(key: str) -> None` method signature |
| FR-BOUNDARY-005 | SDK shall define LogProvider protocol compatible with Python logging | Must | Protocol matches Python logging.Logger interface (debug, info, warning, error, exception) |
| FR-BOUNDARY-006 | SDK shall provide default no-op AuthProvider implementation | Must | Default raises NotConfiguredError when token requested |
| FR-BOUNDARY-007 | SDK shall provide default no-op CacheProvider implementation | Must | Default returns None for get, no-op for set/delete |

### Functional Requirements - Backward Compatibility (FR-COMPAT-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-COMPAT-001 | SDK shall maintain same public API signatures for migrated functions | Must | Functions moved to SDK have identical signatures to autom8 originals |
| FR-COMPAT-002 | SDK shall provide import aliases for gradual migration | Must | Old import paths work via aliasing; deprecation warnings emitted |
| FR-COMPAT-003 | SDK shall allow autom8 to inject AuthProvider at runtime | Must | autom8 can provide its ENV.SecretManager-backed AuthProvider |
| FR-COMPAT-004 | SDK shall allow autom8 to inject CacheProvider at runtime | Must | autom8 can provide its S3-backed CacheProvider |
| FR-COMPAT-005 | SDK shall allow autom8 to inject LogProvider at runtime | Must | autom8 can provide its LOG-backed LogProvider |
| FR-COMPAT-006 | SDK shall work standalone without autom8 dependencies | Must | SDK can be imported and used without autom8 installed |
| FR-COMPAT-007 | SDK shall keep asana (official SDK) as a dependency | Must | asana 5.0.3+ listed in pyproject.toml dependencies |
| FR-COMPAT-008 | SDK shall not expose internal implementation details in public API | Should | Public API is stable; internal modules prefixed with underscore |

### Non-Functional Requirements (NFR-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-001 | Package size | < 5MB wheel | `pip wheel` output size |
| NFR-002 | Cold import time | < 500ms | Timed import in fresh Python process |
| NFR-003 | Test coverage | >= 80% on core modules | pytest-cov line coverage report |
| NFR-004 | Python version support | 3.10, 3.11 | CI matrix testing both versions |
| NFR-005 | Type coverage | 100% public API typed | mypy strict mode passes |
| NFR-006 | Documentation | Full API reference | All public classes/methods have docstrings |
| NFR-007 | Dependency count | Minimal (< 10 direct) | `pip show` dependency list |
| NFR-008 | Zero coupling to autom8 internals | No imports from sql/, contente_api/, aws_api/ | Static import analysis |

## User Stories / Use Cases

### UC-1: New Microservice Uses Asana SDK

A developer building a new microservice needs to create tasks in Asana.

1. Developer adds `autom8_asana` to their project dependencies
2. Developer implements a simple AuthProvider that reads token from environment
3. Developer instantiates AsanaClient with their AuthProvider
4. Developer calls `client.tasks.create(...)` to create tasks
5. SDK handles rate limiting, retries, and error handling transparently

**Success**: New service interacts with Asana without any autom8 dependencies.

### UC-2: autom8 Migrates to SDK

The autom8 team incrementally migrates to the extracted SDK.

1. Team adds `autom8_asana` as a dependency alongside existing code
2. Team creates AuthProvider wrapping ENV.SecretManager
3. Team creates CacheProvider wrapping TaskCache (S3)
4. Team updates imports to use SDK classes with aliases
5. Team removes old code paths once SDK is validated
6. Old imports continue working during migration via aliases

**Success**: autom8 migrates without breaking existing functionality.

### UC-3: Batch Task Creation

A service needs to create 500 tasks efficiently.

1. Service builds list of 500 task creation requests
2. Service calls `client.batch.create_tasks(tasks)`
3. SDK automatically chunks into Asana-compliant batch sizes
4. SDK executes batches respecting rate limits
5. SDK returns results with per-task success/failure status

**Success**: 500 tasks created efficiently without manual batching logic.

### UC-4: Webhook Event Processing

A service receives Asana webhook events and needs to process them.

1. Service receives webhook POST from Asana
2. Service uses `client.webhooks.verify_signature(...)` to validate
3. Service deserializes event using SDK models
4. Service processes event (business logic in service, not SDK)

**Success**: Webhook handling is secure and model parsing is handled by SDK.

## Assumptions

| Assumption | Basis |
|------------|-------|
| Asana API remains stable at v1 | Asana's public commitment to API stability |
| Rate limits remain at 1500 req/min | Current documented Asana limits |
| Python 3.10+ is acceptable minimum | autom8 runtime constraint |
| Pydantic v2 is acceptable | autom8 already uses Pydantic |
| httpx is acceptable for HTTP | Modern async HTTP library; well-maintained |
| CodeArtifact for private publishing | Existing autom8 infrastructure |

## Dependencies

| Dependency | Owner | Notes |
|------------|-------|-------|
| Asana API | Asana | External API; SDK depends on API stability |
| asana (Python SDK) | Asana | Official SDK as foundation |
| httpx | Encode | HTTP client library |
| Pydantic v2 | Pydantic team | Model validation |
| CodeArtifact | autom8 team | Publishing infrastructure |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None | - | - | All key decisions resolved in User Decisions section |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-08 | Requirements Analyst | Initial PRD with 68 requirements |

---

## Appendix A: Current Source Code Structure with Extraction Mapping

```
autom8/apis/asana_api/
├── clients/                          --> autom8_asana.clients
│   ├── tasks.py                      --> autom8_asana.clients.tasks
│   ├── projects.py                   --> autom8_asana.clients.projects
│   ├── sections.py                   --> autom8_asana.clients.sections
│   ├── custom_fields.py              --> autom8_asana.clients.custom_fields
│   ├── webhooks.py                   --> autom8_asana.clients.webhooks
│   ├── users.py                      --> autom8_asana.clients.users
│   ├── teams.py                      --> autom8_asana.clients.teams
│   ├── attachments.py                --> autom8_asana.clients.attachments
│   ├── tags.py                       --> autom8_asana.clients.tags
│   ├── goals.py                      --> autom8_asana.clients.goals
│   ├── portfolios.py                 --> autom8_asana.clients.portfolios
│   ├── workspaces.py                 --> autom8_asana.clients.workspaces
│   └── stories.py                    --> autom8_asana.clients.stories
├── asana_utils/
│   ├── error.py                      --> autom8_asana.utils.error
│   ├── enums.py                      --> autom8_asana.utils.enums
│   └── converter.py                  --> autom8_asana.utils.converter
├── objects/
│   └── generics/
│       └── base.py                   --> autom8_asana.models.base
├── batch_api/                        --> autom8_asana.batch
│   ├── batch_client.py               --> autom8_asana.batch.client
│   └── batch_request.py              --> autom8_asana.batch.request
└── [transport layer - new]           --> autom8_asana.transport
    ├── client.py                     (new: connection pooling)
    ├── rate_limiter.py               (new: token bucket)
    └── retry.py                      (new: exponential backoff)
```

### Files Staying in autom8 (Not Extracted)

```
autom8/apis/asana_api/
├── objects/
│   ├── task/
│   │   ├── models/                   STAYS (Offer, Business, Unit, Contact, etc.)
│   │   └── managers/                 STAYS (ad managers, insights)
│   ├── project/
│   │   └── models/                   STAYS (business-specific project types)
│   └── custom_field/
│       └── models/                   STAYS (business concept mappings)
└── [files with sql/, aws_api/, contente_api/ imports]  STAYS
```

## Appendix B: Coupling Analysis Summary

Analysis of the source codebase revealed the following coupling that prevents direct extraction:

| Coupling Type | File Count | Example Imports |
|---------------|------------|-----------------|
| SQL/Database | 74 files | `from sql.models import ...`, `from sql.connection import ...` |
| Content API | 100 files | `from contente_api import ...`, `from contente_api.client import ...` |
| AWS API | 20 files | `from aws_api.s3 import ...`, `from aws_api.secrets import ...` |
| **Total Coupled** | ~194 files | (some files have multiple coupling types) |

### Decoupling Strategy

1. **SQL coupling**: Replaced by CacheProvider protocol (for caching) and removed (for business data)
2. **Content API coupling**: Not needed in SDK; stays in autom8 business logic
3. **AWS coupling**: Replaced by AuthProvider (secrets) and CacheProvider (S3 cache) protocols

## Appendix C: Draft Protocol Definitions

### AuthProvider Protocol

```python
from typing import Protocol

class AuthProvider(Protocol):
    """Protocol for authentication/secret retrieval.

    Implementations:
    - autom8: Wraps ENV.SecretManager
    - standalone: Reads from environment variables
    - testing: Returns mock tokens
    """

    def get_secret(self, key: str) -> str:
        """Retrieve a secret value by key.

        Args:
            key: Secret identifier (e.g., "ASANA_PAT")

        Returns:
            Secret value as string

        Raises:
            AuthenticationError: If secret not found or retrieval fails
        """
        ...
```

### CacheProvider Protocol

```python
from typing import Protocol, TypeVar, Optional

T = TypeVar("T")

class CacheProvider(Protocol):
    """Protocol for caching operations.

    Implementations:
    - autom8: Wraps TaskCache (S3-backed)
    - standalone: In-memory LRU cache
    - testing: Dict-based mock cache
    """

    def get(self, key: str) -> Optional[T]:
        """Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        ...

    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None for default)
        """
        ...

    def delete(self, key: str) -> None:
        """Remove value from cache.

        Args:
            key: Cache key to delete
        """
        ...
```

### LogProvider Protocol

```python
from typing import Protocol

class LogProvider(Protocol):
    """Protocol for logging operations.

    Compatible with Python's logging.Logger interface.

    Implementations:
    - autom8: Wraps LOG instance
    - standalone: Python logging.getLogger()
    - testing: Captures logs for assertions
    """

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log debug message."""
        ...

    def info(self, msg: str, *args, **kwargs) -> None:
        """Log info message."""
        ...

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log warning message."""
        ...

    def error(self, msg: str, *args, **kwargs) -> None:
        """Log error message."""
        ...

    def exception(self, msg: str, *args, **kwargs) -> None:
        """Log exception with traceback."""
        ...
```

### Default No-Op Implementations

```python
class DefaultAuthProvider:
    """Default AuthProvider that raises when token is needed.

    Used when SDK is instantiated without explicit auth configuration.
    Forces consumers to provide authentication rather than silently failing.
    """

    def get_secret(self, key: str) -> str:
        raise NotConfiguredError(
            f"No AuthProvider configured. Cannot retrieve secret '{key}'. "
            "Provide an AuthProvider when creating AsanaClient."
        )


class DefaultCacheProvider:
    """Default no-op CacheProvider.

    Caching is disabled by default. All gets return None,
    all sets are no-ops. SDK functions correctly without caching.
    """

    def get(self, key: str) -> None:
        return None

    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        pass

    def delete(self, key: str) -> None:
        pass


class DefaultLogProvider:
    """Default LogProvider using Python standard logging.

    Creates a logger named 'autom8_asana' using Python's logging module.
    """

    def __init__(self):
        import logging
        self._logger = logging.getLogger("autom8_asana")

    def debug(self, msg: str, *args, **kwargs) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self._logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        self._logger.exception(msg, *args, **kwargs)
```
