# Exceptions Reference

Exception hierarchy for the autom8_asana SDK.

## Overview

The SDK uses domain-specific exceptions to communicate errors. All exceptions inherit from either `AsanaError` (API and SDK-level errors) or `Autom8Error` (infrastructure errors). Service-layer exceptions inherit from `ServiceError`.

This reference documents all exception classes, when they are raised, and how to handle them.

## Exception Hierarchy

```
Exception (Python builtin)
│
├── AsanaError (base for API and SDK errors)
│   ├── AuthenticationError (401)
│   ├── ForbiddenError (403)
│   ├── NotFoundError (404)
│   ├── GoneError (410)
│   ├── RateLimitError (429)
│   ├── ServerError (5xx)
│   ├── TimeoutError
│   ├── ConfigurationError
│   ├── CircuitBreakerOpenError
│   ├── NameNotFoundError
│   ├── HydrationError
│   ├── ResolutionError
│   ├── InsightsError
│   │   ├── InsightsValidationError
│   │   ├── InsightsNotFoundError
│   │   └── InsightsServiceError
│   ├── ExportError
│   └── SaveOrchestrationError
│       ├── SessionClosedError
│       ├── CyclicDependencyError
│       ├── DependencyResolutionError
│       ├── PartialSaveError
│       ├── UnsupportedOperationError
│       ├── PositioningConflictError
│       ├── GidValidationError
│       │   └── ValidationError (deprecated)
│       └── SaveSessionError
│
├── Autom8Error (base for infrastructure errors)
│   ├── TransportError
│   │   ├── S3TransportError
│   │   └── RedisTransportError
│   ├── CacheError
│   │   └── CacheConnectionError
│   └── AutomationError
│       ├── RuleExecutionError
│       ├── SeedingError
│       └── PipelineActionError
│
├── ServiceError (base for service layer)
│   ├── EntityNotFoundError (404)
│   │   ├── UnknownEntityError
│   │   ├── UnknownSectionError
│   │   ├── TaskNotFoundError
│   │   └── EntityTypeMismatchError
│   ├── EntityValidationError (400/422)
│   │   ├── InvalidFieldError (422)
│   │   ├── InvalidParameterError (400)
│   │   └── NoValidFieldsError (422)
│   ├── CacheNotReadyError (503)
│   └── ServiceNotConfiguredError (503)
│
├── DataFrameError (base for dataframe operations)
│   ├── SchemaNotFoundError
│   ├── ExtractionError
│   ├── TypeCoercionError
│   ├── SchemaVersionError
│   └── ParallelFetchError
│
├── QueryEngineError (base for query engine)
│   ├── QueryTooComplexError
│   ├── UnknownFieldError
│   ├── InvalidOperatorError
│   ├── CoercionError
│   ├── UnknownSectionError
│   ├── AggregationError
│   ├── AggregateGroupLimitError
│   └── JoinError
│
├── BotPATError (auth configuration)
├── BudgetExhaustedError (resolution budget)
├── MissingConfigurationError (cache configuration)
└── RuntimeError (Python builtin)
    └── SyncInAsyncContextError
```

## Base Exceptions

### AsanaError

Base exception for all Asana API and SDK-level errors.

**Import:** `from autom8_asana.exceptions import AsanaError`

**Attributes:**
- `message` (str): Human-readable error description
- `status_code` (int | None): HTTP status code if from API response
- `response` (httpx.Response | None): Raw HTTP response object
- `errors` (list[dict]): Error details from Asana API

**Factory Method:**
```python
@classmethod
def from_response(cls, response: Response) -> AsanaError:
    """Create appropriate exception from httpx Response."""
```

Maps HTTP status codes to specific exception subclasses. Parses response body to extract error details and includes debugging context (request ID, status, body snippet).

### Autom8Error

Base exception for infrastructure-level errors (transport, cache, automation).

**Import:** `from autom8_asana.core.exceptions import Autom8Error`

**Attributes:**
- `message` (str): Human-readable error description
- `context` (dict): Structured metadata for logging and diagnostics
- `transient` (bool): Whether error is transient (class-level attribute)

**Constructor:**
```python
def __init__(
    self,
    message: str,
    *,
    context: dict[str, Any] | None = None,
    cause: Exception | None = None,
) -> None
```

### ServiceError

Base exception for service-layer business logic errors.

**Import:** `from autom8_asana.services.errors import ServiceError`

**Attributes:**
- `message` (str): Human-readable error description
- `error_code` (str): Machine-readable error code (default: "SERVICE_ERROR")
- `status_hint` (int): Suggested HTTP status code (default: 500)

**Method:**
```python
def to_dict(self) -> dict[str, Any]:
    """Serialize to API error response format."""
```

Service-layer exceptions never import framework-specific HTTP errors. Route handlers catch `ServiceError` and map to HTTP responses via `get_status_for_error()`.

## HTTP Errors

### AuthenticationError

Authentication failed (HTTP 401).

**Import:** `from autom8_asana.exceptions import AuthenticationError`

**When raised:** Invalid or expired Personal Access Token, OAuth token validation failure.

**Handling:**
```python
try:
    task = await client.tasks.get_async("123")
except AuthenticationError:
    # Re-authenticate or refresh token
    pass
```

### ForbiddenError

Access denied (HTTP 403).

**Import:** `from autom8_asana.exceptions import ForbiddenError`

**When raised:** Insufficient permissions to access the resource. User may lack project membership or workspace access.

### NotFoundError

Resource not found (HTTP 404).

**Import:** `from autom8_asana.exceptions import NotFoundError`

**When raised:** Requested GID does not exist or user lacks permission to view it.

### GoneError

Resource permanently deleted (HTTP 410).

**Import:** `from autom8_asana.exceptions import GoneError`

**When raised:** Resource was deleted and cannot be recovered.

### RateLimitError

Rate limit exceeded (HTTP 429).

**Import:** `from autom8_asana.exceptions import RateLimitError`

**Attributes:**
- `retry_after` (int | None): Seconds to wait before retrying (from Retry-After header)

**When raised:** Asana API rate limit exceeded. Check `retry_after` to determine backoff duration.

**Handling:**
```python
try:
    tasks = await client.tasks.get_batch_async(gids)
except RateLimitError as e:
    if e.retry_after:
        await asyncio.sleep(e.retry_after)
        # Retry request
```

### ServerError

Server-side error (HTTP 5xx).

**Import:** `from autom8_asana.exceptions import ServerError`

**When raised:** Asana API returned 500, 502, 503, or 504. Indicates temporary service degradation.

**Handling:** Retry with exponential backoff.

### TimeoutError

Request timed out.

**Import:** `from autom8_asana.exceptions import TimeoutError`

**When raised:** HTTP request exceeded configured timeout.

## Client Errors

### ConfigurationError

SDK configuration error (not an API error).

**Import:** `from autom8_asana.exceptions import ConfigurationError`

**When raised:** Missing required configuration (e.g., PAT not set), invalid settings, or client initialization failure.

### SyncInAsyncContextError

Raised when sync wrapper is called from async context.

**Import:** `from autom8_asana.exceptions import SyncInAsyncContextError`

**When raised:** Attempting to call a sync method (e.g., `task.save()`) from async code. Per ADR-0002, sync wrappers fail fast to prevent deadlocks.

**Constructor:**
```python
def __init__(self, method_name: str, async_method_name: str) -> None
```

**Handling:** Use the async variant instead.
```python
# Wrong:
async def my_func():
    task.save()  # SyncInAsyncContextError

# Correct:
async def my_func():
    await task.save_async()
```

### CircuitBreakerOpenError

Circuit breaker is open due to service degradation.

**Import:** `from autom8_asana.exceptions import CircuitBreakerOpenError`

**Attributes:**
- `time_until_recovery` (float): Seconds until circuit breaker enters half-open state

**When raised:** Service appears degraded based on failure rate. Per ADR-0048, fail fast to prevent cascading failures.

**Handling:** Wait for `time_until_recovery` or check Asana status page.

### NameNotFoundError

Resource name cannot be resolved to a GID.

**Import:** `from autom8_asana.exceptions import NameNotFoundError`

**Attributes:**
- `resource_type` (str): Type of resource (e.g., "tag", "project", "user")
- `name` (str): Name that failed to resolve
- `scope` (str): Scope of search (workspace_gid, project_gid, etc.)
- `suggestions` (list[str]): Close matches (fuzzy matching)
- `available_names` (list[str]): All available names in scope

**When raised:** Name-based lookup failed. Per ADR-0060, name resolution uses per-SaveSession caching.

**Handling:**
```python
try:
    tag_gid = await session.resolve_tag_async("urgent")
except NameNotFoundError as e:
    if e.suggestions:
        # Did user mean "Urgent!" instead of "urgent"?
        print(f"Did you mean: {', '.join(e.suggestions)}")
```

## Hydration and Resolution Errors

### HydrationError

Hierarchy hydration operation failed.

**Import:** `from autom8_asana.exceptions import HydrationError`

**Attributes:**
- `entity_gid` (str): GID where hydration started or failed
- `entity_type` (str | None): Detected entity type
- `phase` (Literal["downward", "upward"]): Failure phase
- `partial_result` (HydrationResult | None): What succeeded before failure
- `cause` (Exception | None): Underlying exception

**When raised:** Per ADR-0070, raised during hierarchy hydration when `partial_ok=False` (default). Occurs during downward hydration (Business → children) or upward traversal (leaf → Business).

**Handling:**
```python
try:
    result = await client.hydrate_hierarchy_async(gid="123")
except HydrationError as e:
    if e.phase == "downward":
        # Handle downward hydration failure
        partial = e.partial_result  # Salvage what succeeded
```

### ResolutionError

Entity resolution operation failed.

**Import:** `from autom8_asana.exceptions import ResolutionError`

**Attributes:**
- `entity_gid` (str): GID of entity being resolved
- `strategies_tried` (list[str]): Strategy names attempted
- `cause` (Exception | None): Underlying exception

**When raised:** Per FR-AMBIG-003, raised when all resolution strategies fail with errors. Ambiguous results (multiple matches) are returned as `ResolutionResult` with `ambiguous=True`, not raised as exceptions.

## Insights API Exceptions

### InsightsError

Base exception for insights API errors.

**Import:** `from autom8_asana.exceptions import InsightsError`

**Attributes:**
- `request_id` (str | None): Request correlation ID for tracing through autom8_data

Per FR-008.1, inherits from AsanaError for consistency.

### InsightsValidationError

Invalid input for insights request (HTTP 400).

**Import:** `from autom8_asana.exceptions import InsightsValidationError`

**Attributes:**
- `field` (str | None): Field that failed validation

**When raised:** Request parameters failed validation (e.g., invalid factory, malformed phone number, invalid period format).

### InsightsNotFoundError

No insights data found (HTTP 404).

**Import:** `from autom8_asana.exceptions import InsightsNotFoundError`

**When raised:** No data exists for the specified PhoneVerticalPair and factory combination.

### InsightsServiceError

Upstream autom8_data service failure (HTTP 5xx).

**Import:** `from autom8_asana.exceptions import InsightsServiceError`

**Attributes:**
- `reason` (str | None): Failure reason (timeout, circuit_breaker, http_error)
- `status_code` (int | None): HTTP status code from upstream

**When raised:** autom8_data is unavailable, times out, or returns a server error.

## Export API Exceptions

### ExportError

Conversation export endpoint error.

**Import:** `from autom8_asana.exceptions import ExportError`

**Attributes:**
- `office_phone` (str): Phone number being exported
- `reason` (str): Error classification (default: "unknown")

**When raised:** Per TDD-CONV-AUDIT-001, raised by `DataServiceClient.get_export_csv_async()` on HTTP errors, circuit breaker open, or timeout.

## Persistence Errors

All save-related exceptions inherit from `SaveOrchestrationError`, which inherits from `AsanaError`. This allows catching all save-related errors with a single except clause.

### SaveOrchestrationError

Base exception for save orchestration errors.

**Import:** `from autom8_asana.persistence.exceptions import SaveOrchestrationError`

### SessionClosedError

Raised when operating on a closed session.

**Import:** `from autom8_asana.persistence.exceptions import SessionClosedError`

**When raised:** Per FR-UOW-006, prevents re-use after commit or context exit. Once a `SaveSession` exits its context manager, all operations fail with this exception.

**Handling:**
```python
async with client.save_session() as session:
    session.track(task)
# session is now closed

try:
    session.track(another_task)  # SessionClosedError
except SessionClosedError:
    # Create new session
    async with client.save_session() as new_session:
        new_session.track(another_task)
```

### CyclicDependencyError

Dependency graph contains cycles.

**Import:** `from autom8_asana.persistence.exceptions import CyclicDependencyError`

**Attributes:**
- `cycle` (list[AsanaResource]): Entities involved in the cycle

**When raised:** Per FR-DEPEND-003, cycles make it impossible to determine valid save order.

**Handling:** Review entity relationships and break the cycle.

### DependencyResolutionError

A dependency cannot be resolved.

**Import:** `from autom8_asana.persistence.exceptions import DependencyResolutionError`

**Attributes:**
- `entity` (AsanaResource): Entity that couldn't be saved
- `dependency` (AsanaResource): Dependency that failed
- `cause` (Exception): Underlying exception

**When raised:** Per FR-ERROR-006, raised when a dependent entity's save fails because its dependency failed. Enables cascading failure tracking in partial save scenarios.

### PartialSaveError

Some operations in a commit failed.

**Import:** `from autom8_asana.persistence.exceptions import PartialSaveError`

**Attributes:**
- `result` (SaveResult): Contains success and failure details
- `is_retryable` (bool): Whether any failures are retryable
- `retryable_count` (int): Count of retryable failures
- `non_retryable_count` (int): Count of non-retryable failures

**When raised:** Per FR-ERROR-004 and ADR-0079, raised by `SaveResult.raise_on_failure()` when caller wants exception-based error handling instead of inspecting the result directly.

**Handling:**
```python
try:
    result = await session.commit_async()
    result.raise_on_failure()
except PartialSaveError as e:
    if e.is_retryable:
        # Retry retryable failures
        for error in e.result.retryable_failures:
            print(f"Retryable: {error}")
    for error in e.result.non_retryable_failures:
        print(f"Permanent failure: {error}")
```

### UnsupportedOperationError

Field modification requires action endpoints.

**Import:** `from autom8_asana.persistence.exceptions import UnsupportedOperationError`

**Attributes:**
- `field_name` (str): Field that cannot be directly modified
- `suggested_methods` (list[str]): Methods to use instead

**When raised:** Per TDD-0011, certain fields (tags, projects, memberships, dependencies) cannot be modified via PUT/PATCH. They require dedicated action endpoints (addTag, removeTag, etc.).

**Handling:**
```python
try:
    task.tags = [new_tag]
    await task.save_async()
except UnsupportedOperationError as e:
    # Use suggested methods instead
    await task.add_tag_async(new_tag)
```

### PositioningConflictError

Both insert_before and insert_after specified.

**Import:** `from autom8_asana.persistence.exceptions import PositioningConflictError`

**Attributes:**
- `insert_before` (str): The insert_before value provided
- `insert_after` (str): The insert_after value provided

**When raised:** Per ADR-0047, fail-fast validation at queue time. Asana API does not support both positioning parameters simultaneously.

### GidValidationError

Entity GID validation failed.

**Import:** `from autom8_asana.persistence.exceptions import GidValidationError`

**When raised:** Per FR-VAL-001, raised when an entity fails GID format validation during tracking. Per TDD-HARDENING-A/FR-EXC-001, renamed from `ValidationError` to avoid conflict with `pydantic.ValidationError`.

### ValidationError (deprecated)

**Import:** `from autom8_asana.persistence.exceptions import ValidationError`

**Deprecation:** Use `GidValidationError` instead. This alias will be removed in v2.0.

Per FR-EXC-002, backward compatibility alias with deprecation warning (emitted once per session on first usage).

### SaveSessionError

SaveSession commit failed in a convenience method.

**Import:** `from autom8_asana.persistence.exceptions import SaveSessionError`

**Attributes:**
- `result` (SaveResult): Contains success/failure details

**When raised:** Per ADR-0065, raised by P1 convenience methods (`add_tag_async`, `remove_tag_async`, etc.) when the underlying SaveSession commit fails.

**Handling:**
```python
try:
    await task.add_tag_async(tag_gid)
except SaveSessionError as e:
    for error in e.result.failed:
        print(f"CRUD {error.operation} failed: {error.error}")
```

## Service Layer Errors

### EntityNotFoundError

Entity or resource not found (HTTP 404).

**Import:** `from autom8_asana.services.errors import EntityNotFoundError`

Base class for all service-layer 404 errors.

### UnknownEntityError

Entity type not resolvable via EntityRegistry.

**Import:** `from autom8_asana.services.errors import UnknownEntityError`

**Attributes:**
- `entity_type` (str): Requested entity type string
- `available` (list[str]): Sorted list of valid entity types

**When raised:** Requested entity type does not exist in the registry.

### UnknownSectionError

Section name not found in project manifest.

**Import:** `from autom8_asana.services.errors import UnknownSectionError`

**Attributes:**
- `section_name` (str): Requested section name
- `available_sections` (list[str]): Sorted list of valid section names

### TaskNotFoundError

Task GID does not exist in Asana.

**Import:** `from autom8_asana.services.errors import TaskNotFoundError`

**Attributes:**
- `gid` (str): Task GID that was not found

### EntityTypeMismatchError

Task exists but belongs to wrong project.

**Import:** `from autom8_asana.services.errors import EntityTypeMismatchError`

**Attributes:**
- `gid` (str): Task GID
- `expected_project` (str): Project GID the entity type requires
- `actual_projects` (list[str]): Project GIDs the task actually belongs to

### EntityValidationError

Validation error for entity operations (HTTP 400/422).

**Import:** `from autom8_asana.services.errors import EntityValidationError`

### InvalidFieldError

Field not valid for entity schema (HTTP 422).

**Import:** `from autom8_asana.services.errors import InvalidFieldError`

**Attributes:**
- `invalid_fields` (list[str]): Fields that failed validation
- `available_fields` (list[str]): Valid schema fields

### InvalidParameterError

Invalid request parameter (HTTP 400).

**Import:** `from autom8_asana.services.errors import InvalidParameterError`

### NoValidFieldsError

All fields failed resolution (HTTP 422).

**Import:** `from autom8_asana.services.errors import NoValidFieldsError`

**When raised:** Nothing to write after field resolution.

### CacheNotReadyError

Cache not warmed for requested entity (HTTP 503).

**Import:** `from autom8_asana.services.errors import CacheNotReadyError`

**Attributes:**
- `entity_type` (str | None): Entity type whose cache is not ready

### ServiceNotConfiguredError

Required service dependency not available (HTTP 503).

**Import:** `from autom8_asana.services.errors import ServiceNotConfiguredError`

## Transport Errors

### TransportError

Base exception for I/O transport failures.

**Import:** `from autom8_asana.core.exceptions import TransportError`

**Attributes:**
- `backend` (str): Backend name (e.g., "s3", "redis")
- `operation` (str): Operation that failed
- `transient` (bool): True (transport errors are transient by default)

Wraps vendor-specific exceptions from boto3, redis, etc. at the backend boundary. Upstream code catches `TransportError` instead of importing vendor types.

### S3TransportError

S3/boto3 transport failure.

**Import:** `from autom8_asana.core.exceptions import S3TransportError`

**Attributes:**
- `error_code` (str | None): AWS error code (e.g., "NoSuchKey", "AccessDenied")
- `bucket` (str | None): S3 bucket name
- `key` (str | None): S3 object key
- `transient` (bool): False for 4xx errors, True otherwise

**Factory Method:**
```python
@classmethod
def from_boto_error(
    cls,
    error: Exception,
    *,
    operation: str = "unknown",
    bucket: str | None = None,
    key: str | None = None,
) -> S3TransportError
```

### RedisTransportError

Redis transport failure.

**Import:** `from autom8_asana.core.exceptions import RedisTransportError`

**Factory Method:**
```python
@classmethod
def from_redis_error(
    cls,
    error: Exception,
    *,
    operation: str = "unknown",
) -> RedisTransportError
```

## Cache Errors

### CacheError

Base exception for cache subsystem semantic errors.

**Import:** `from autom8_asana.core.exceptions import CacheError`

**Attributes:**
- `cache_key` (str | None): Cache key that failed
- `transient` (bool): False (semantic errors are permanent by default)

Raised when a cache operation fails for reasons beyond raw transport (e.g., serialization failure, key format error). Transport failures within cache backends are raised as `TransportError` subclasses.

### CacheConnectionError

Cache backend is unavailable (used by degraded-mode logic).

**Import:** `from autom8_asana.core.exceptions import CacheConnectionError`

**Attributes:**
- `transient` (bool): True

## Automation Errors

### AutomationError

Base exception for automation subsystem errors.

**Import:** `from autom8_asana.core.exceptions import AutomationError`

**Attributes:**
- `entity_gid` (str | None): GID of entity where automation failed

Covers pipeline execution, seeding, and rule evaluation.

### RuleExecutionError

A single automation rule failed during evaluation.

**Import:** `from autom8_asana.core.exceptions import RuleExecutionError`

### SeedingError

Seeding operation failed.

**Import:** `from autom8_asana.core.exceptions import SeedingError`

### PipelineActionError

A pipeline action (move, assign, comment, etc.) failed.

**Import:** `from autom8_asana.core.exceptions import PipelineActionError`

## DataFrame Errors

### DataFrameError

Base exception for all dataframe operations.

**Import:** `from autom8_asana.dataframes.exceptions import DataFrameError`

**Attributes:**
- `message` (str): Human-readable error description
- `context` (dict): Additional context for debugging

### SchemaNotFoundError

No schema registered for the specified task type.

**Import:** `from autom8_asana.dataframes.exceptions import SchemaNotFoundError`

**Attributes:**
- `task_type` (str): Task type that was not found

### ExtractionError

Field extraction failed for a task.

**Import:** `from autom8_asana.dataframes.exceptions import ExtractionError`

**Attributes:**
- `task_gid` (str): GID of the task that failed
- `field_name` (str): Name of the field that failed extraction
- `original_error` (Exception): The underlying exception

### TypeCoercionError

Type coercion failed for a field value.

**Import:** `from autom8_asana.dataframes.exceptions import TypeCoercionError`

**Attributes:**
- `field_name` (str): Name of the field
- `expected_type` (str): Expected Python/Polars type
- `actual_value` (Any): The value that could not be coerced

### SchemaVersionError

Schema version conflict or incompatibility.

**Import:** `from autom8_asana.dataframes.exceptions import SchemaVersionError`

**Attributes:**
- `schema_name` (str): Name of the schema
- `expected_version` (str): Expected schema version
- `actual_version` (str): Actual schema version found

### ParallelFetchError

Parallel section fetch failed.

**Import:** `from autom8_asana.dataframes.builders.parallel_fetch import ParallelFetchError`

**Attributes:**
- `errors` (list[Exception]): Exceptions from failed section fetches
- `section_gids` (list[str]): GIDs of sections that failed

**When raised:** Per FR-FALLBACK-004, one or more section fetches failed. Caller should fall back to serial project-level fetch.

## Query Engine Errors

### QueryEngineError

Base error for all query engine domain errors.

**Import:** `from autom8_asana.query.errors import QueryEngineError`

**Method:**
```python
def to_dict(self) -> dict[str, Any]:
    """Serialize to JSON-compatible dict for HTTP response."""
```

### QueryTooComplexError

Predicate tree exceeds max depth.

**Import:** `from autom8_asana.query.errors import QueryTooComplexError`

**Attributes:**
- `depth` (int): Actual predicate tree depth
- `max_depth` (int): Maximum allowed depth

### UnknownFieldError

Referenced field not in entity schema.

**Import:** `from autom8_asana.query.errors import UnknownFieldError`

**Attributes:**
- `field` (str): Field that was not found
- `available` (list[str]): Valid schema fields

### InvalidOperatorError

Operator incompatible with field dtype.

**Import:** `from autom8_asana.query.errors import InvalidOperatorError`

**Attributes:**
- `field` (str): Field name
- `dtype` (str): Field data type
- `op` (str): Operator that was used
- `allowed` (list[str]): Supported operators for this dtype

### CoercionError

Value cannot be coerced to field dtype.

**Import:** `from autom8_asana.query.errors import CoercionError`

**Attributes:**
- `field` (str): Field name
- `dtype` (str): Expected data type
- `value` (Any): Value that could not be coerced
- `reason` (str): Failure reason

### UnknownSectionError

Section name cannot be resolved.

**Import:** `from autom8_asana.query.errors import UnknownSectionError`

**Attributes:**
- `section` (str): Section name that was not found

### AggregationError

Aggregation-specific error (dtype mismatch, invalid group_by, etc.).

**Import:** `from autom8_asana.query.errors import AggregationError`

**Attributes:**
- `message` (str): Error description

### AggregateGroupLimitError

Aggregation produced too many groups.

**Import:** `from autom8_asana.query.errors import AggregateGroupLimitError`

**Attributes:**
- `group_count` (int): Actual number of groups produced
- `max_groups` (int): Maximum allowed groups

### JoinError

Cross-entity join failed.

**Import:** `from autom8_asana.query.errors import JoinError`

**Attributes:**
- `message` (str): Error description

## Other Errors

### BotPATError

Bot PAT configuration error.

**Import:** `from autom8_asana.auth.bot_pat import BotPATError`

**When raised:** ASANA_PAT environment variable is missing or invalid. Indicates a deployment configuration issue.

### BudgetExhaustedError

API call budget is exhausted.

**Import:** `from autom8_asana.resolution.budget import BudgetExhaustedError`

**When raised:** Resolution chain exceeded maximum API calls. Prevents unbounded API call chains.

### MissingConfigurationError

Required configuration is missing.

**Import:** `from autom8_asana.cache.integration.autom8_adapter import MissingConfigurationError`

**When raised:** Cache configuration is incomplete or invalid.

## Transport Error Tuples

For convenience at catch sites, the SDK provides pre-defined error tuples. These are used during migration while backends are being wrapped. Once all backends wrap at the boundary, upstream code catches `TransportError`/`CacheError` instead.

**Import:** `from autom8_asana.core.exceptions import *`

### S3_TRANSPORT_ERRORS

Tuple of S3/boto3 transport errors.

```python
S3_TRANSPORT_ERRORS: tuple[type[Exception], ...] = (
    S3TransportError,
    BotoCoreError,     # if botocore is available
    ClientError,       # if botocore is available
    ConnectionError,   # Python builtin
    TimeoutError,      # Python builtin
    OSError,           # Python builtin
)
```

### REDIS_TRANSPORT_ERRORS

Tuple of Redis transport errors.

```python
REDIS_TRANSPORT_ERRORS: tuple[type[Exception], ...] = (
    RedisTransportError,
    RedisError,  # if redis is available
)
```

### ALL_TRANSPORT_ERRORS

Union of S3 and Redis transport errors.

```python
ALL_TRANSPORT_ERRORS: tuple[type[Exception], ...] = (
    S3_TRANSPORT_ERRORS + REDIS_TRANSPORT_ERRORS
)
```

### CACHE_TRANSIENT_ERRORS

All transient cache errors (transport + semantic).

```python
CACHE_TRANSIENT_ERRORS: tuple[type[Exception], ...] = (
    ALL_TRANSPORT_ERRORS + (CacheConnectionError,)
)
```

**Usage:**
```python
from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS

try:
    value = await cache.get_async(key)
except CACHE_TRANSIENT_ERRORS:
    # Handle transient cache errors
    # Fall back to API or degrade gracefully
    pass
```

## Exception Mapping Reference

| Exception | Trigger Scenario | HTTP Status | Recommended Handling |
|-----------|------------------|-------------|---------------------|
| `AuthenticationError` | Invalid/expired PAT or OAuth token | 401 | Re-authenticate or refresh token |
| `ForbiddenError` | Insufficient permissions | 403 | Request access or check workspace membership |
| `NotFoundError` | Resource GID does not exist | 404 | Verify GID or handle missing resource |
| `GoneError` | Resource permanently deleted | 410 | Remove reference from application |
| `RateLimitError` | API rate limit exceeded | 429 | Check `retry_after` and backoff |
| `ServerError` | Asana API server error | 5xx | Retry with exponential backoff |
| `TimeoutError` | Request timeout | - | Retry or increase timeout |
| `ConfigurationError` | Missing/invalid SDK config | - | Check environment variables and settings |
| `SyncInAsyncContextError` | Sync method in async context | - | Use async variant (`await method_async()`) |
| `CircuitBreakerOpenError` | Service degraded | - | Wait for recovery or check status page |
| `NameNotFoundError` | Name cannot resolve to GID | - | Check spelling or use suggestions |
| `HydrationError` | Hierarchy hydration failed | - | Check `partial_result` or set `partial_ok=True` |
| `ResolutionError` | All resolution strategies failed | - | Review input data or check logs |
| `InsightsValidationError` | Invalid insights request params | 400 | Validate input parameters |
| `InsightsNotFoundError` | No insights data found | 404 | Check phone/vertical pair exists |
| `InsightsServiceError` | autom8_data unavailable | 5xx | Retry or check service status |
| `ExportError` | Export endpoint failed | - | Check logs and retry |
| `SessionClosedError` | Operating on closed session | - | Create new SaveSession |
| `CyclicDependencyError` | Dependency graph cycle | - | Break cycle in entity relationships |
| `DependencyResolutionError` | Dependency failed | - | Fix dependency or remove relationship |
| `PartialSaveError` | Some operations failed | - | Inspect `result`, retry retryable failures |
| `UnsupportedOperationError` | Direct field modification | - | Use suggested action methods |
| `PositioningConflictError` | Both insert_before/after set | - | Choose one positioning parameter |
| `GidValidationError` | Invalid GID format | - | Validate GID format before tracking |
| `SaveSessionError` | Convenience method commit failed | - | Inspect `result` for failure details |
| `UnknownEntityError` | Entity type not in registry | 404 | Check `available` types |
| `UnknownSectionError` | Section name not found | 404 | Check `available_sections` |
| `TaskNotFoundError` | Task GID not found | 404 | Verify GID exists in Asana |
| `EntityTypeMismatchError` | Task in wrong project | 404 | Verify task belongs to correct project |
| `InvalidFieldError` | Invalid schema field | 422 | Check `available_fields` |
| `InvalidParameterError` | Invalid request parameter | 400 | Validate request parameters |
| `NoValidFieldsError` | All fields failed resolution | 422 | Review field names and values |
| `CacheNotReadyError` | Cache not warmed | 503 | Trigger cache warm or retry later |
| `ServiceNotConfiguredError` | Service dependency missing | 503 | Check service configuration |
| `S3TransportError` | S3 I/O failure | - | Check `transient` property, retry if True |
| `RedisTransportError` | Redis I/O failure | - | Retry or fall back to API |
| `CacheError` | Cache semantic error | - | Check logs for serialization/key errors |
| `CacheConnectionError` | Cache backend unavailable | - | Degrade gracefully or retry |
| `AutomationError` | Automation subsystem error | - | Check logs for rule/pipeline details |
| `RuleExecutionError` | Automation rule failed | - | Review rule logic |
| `SeedingError` | Seeding operation failed | - | Check seed data and retry |
| `PipelineActionError` | Pipeline action failed | - | Check action parameters |
| `SchemaNotFoundError` | Task type schema missing | - | Register schema or check task type |
| `ExtractionError` | Field extraction failed | - | Check field extractor logic |
| `TypeCoercionError` | Type coercion failed | - | Validate field value type |
| `SchemaVersionError` | Schema version mismatch | - | Update schema or migrate data |
| `ParallelFetchError` | Parallel fetch failed | - | Fall back to serial fetch |
| `QueryTooComplexError` | Predicate tree too deep | 400 | Simplify query |
| `UnknownFieldError` | Field not in schema | 400 | Check `available` fields |
| `InvalidOperatorError` | Operator/dtype incompatible | 400 | Check `allowed` operators |
| `CoercionError` | Value cannot be coerced | 400 | Validate value type |
| `AggregationError` | Aggregation failed | 400 | Review aggregation parameters |
| `AggregateGroupLimitError` | Too many groups | 400 | Reduce group_by cardinality |
| `JoinError` | Cross-entity join failed | 400 | Check join conditions |
| `BotPATError` | Bot PAT configuration error | - | Set ASANA_PAT environment variable |
| `BudgetExhaustedError` | API call budget exhausted | - | Increase budget or simplify resolution |
| `MissingConfigurationError` | Cache config missing | - | Provide required configuration |

## Design References

- Exception hierarchy: `docs/design/TDD-exception-hierarchy.md`
- Error handling patterns: `docs/decisions/ADR-0036-error-classification-handling.md`
- Partial failure patterns: `docs/decisions/ADR-0037-partial-failure-result-patterns.md`
- SaveSession error handling: `docs/decisions/ADR-0042-savesession-error-handling.md`
- Resilience hook patterns: `docs/decisions/ADR-0057-resilience-hook-patterns.md`
