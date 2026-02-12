# AsanaClient Reference

> Main entry point for the autom8_asana SDK

## Overview

`AsanaClient` is the primary facade for interacting with the Asana API. It provides access to all resource clients (tasks, projects, users, etc.) and supports both synchronous and asynchronous operations.

The client handles authentication, rate limiting, circuit breaking, retry logic, and optional caching. Resource clients are lazy-initialized on first access.

## Constructor

```python
AsanaClient(
    token: str | None = None,
    *,
    workspace_gid: str | None = None,
    auth_provider: AuthProvider | None = None,
    cache_provider: CacheProvider | None = None,
    log_provider: LogProvider | None = None,
    config: AsanaConfig | None = None,
    observability_hook: ObservabilityHook | None = None,
) -> AsanaClient
```

### Parameters

- **token**: Asana Personal Access Token (convenience parameter)
- **workspace_gid**: Workspace GID. Resolution order:
  1. Explicit parameter (if provided)
  2. `ASANA_WORKSPACE_GID` environment variable
  3. Auto-detection (if exactly one workspace exists)
- **auth_provider**: Custom auth provider (overrides token)
- **cache_provider**: Custom cache provider. If None, uses environment-aware auto-selection based on config. Pass `NullCacheProvider()` explicitly to disable all caching.
- **log_provider**: Custom log provider (default: `DefaultLogProvider`)
- **config**: SDK configuration (default: `AsanaConfig()`)
- **observability_hook**: Custom observability hook for metrics/tracing (default: `NullObservabilityHook`)

### Raises

- **ConfigurationError**: If workspace_gid not provided and zero or multiple workspaces are available

## Resource Clients

All resource clients are lazy-initialized properties. They share the same rate limiter, circuit breaker, and retry policy.

### Tier 1 Clients

- **tasks**: `TasksClient` - Task operations
- **projects**: `ProjectsClient` - Project operations
- **sections**: `SectionsClient` - Section operations
- **custom_fields**: `CustomFieldsClient` - Custom field operations
- **users**: `UsersClient` - User operations
- **workspaces**: `WorkspacesClient` - Workspace operations

### Tier 2 Clients

- **webhooks**: `WebhooksClient` - Webhook operations
- **teams**: `TeamsClient` - Team operations
- **attachments**: `AttachmentsClient` - Attachment operations
- **tags**: `TagsClient` - Tag operations
- **goals**: `GoalsClient` - Goal operations
- **portfolios**: `PortfoliosClient` - Portfolio operations
- **stories**: `StoriesClient` - Story (comment) operations

### Specialized Clients

- **batch**: `BatchClient` - Batch API operations for bulk requests
- **search**: `SearchService` - Field-based GID lookup from cached Polars DataFrames

## Properties

### automation

```python
@property
def automation(self) -> AutomationEngine | None
```

Access automation engine for rule registration. Returns `AutomationEngine` if automation is enabled, None otherwise.

### observability

```python
@property
def observability(self) -> ObservabilityHook
```

Observability hook for metrics and tracing. Returns `NullObservabilityHook` if none was configured.

### cache_metrics

```python
@property
def cache_metrics(self) -> CacheMetrics | None
```

Access cache metrics for observability. Returns `CacheMetrics` if caching is enabled, None otherwise.

### unified_store

```python
@property
def unified_store(self) -> UnifiedTaskStore | None
```

Access unified task store for cache operations. Returns `UnifiedTaskStore` if caching enabled, None otherwise.

## Methods

### save_session()

```python
def save_session(
    self,
    batch_size: int = 10,
    max_concurrent: int = 15,
) -> SaveSession
```

Create a `SaveSession` for batched operations. Returns a context manager that enables deferred, batched saves with automatic dependency ordering and partial failure handling.

**Parameters:**
- **batch_size**: Maximum operations per batch (default: 10, Asana limit)
- **max_concurrent**: Maximum concurrent batch requests (default: 15)

**Returns:** `SaveSession` instance (context manager)

### warm_cache_async()

```python
async def warm_cache_async(
    self,
    gids: list[str],
    entry_type: EntryType,
) -> WarmResult
```

Pre-populate cache for specified GIDs. Fetches resources from the API and stores them in cache for subsequent fast access. Skips GIDs that are already cached.

**Parameters:**
- **gids**: List of GIDs to warm
- **entry_type**: Type of entries to warm (TASK, PROJECT, SECTION, USER, CUSTOM_FIELD)

**Returns:** `WarmResult` with counts (warmed, failed, skipped)

### warm_cache()

```python
def warm_cache(
    self,
    gids: list[str],
    entry_type: EntryType,
) -> WarmResult
```

Synchronous wrapper for `warm_cache_async()`.

**Raises:** `SyncInAsyncContextError` if called from an async context

### close()

```python
async def close(self) -> None
```

Close client and release resources. Call when done with the client, or use as context manager.

### aclose()

```python
async def aclose(self) -> None
```

Alias for `close()` for naming consistency with httpx.

## Context Manager Support

AsanaClient supports both sync and async context managers for automatic cleanup.

**Async context manager:**
```python
async with AsanaClient(token="...") as client:
    task = await client.tasks.get_async("task_gid")
```

**Sync context manager:**
```python
with AsanaClient(token="...") as client:
    task = client.tasks.get("task_gid")
```

Note: Sync context manager raises `ConfigurationError` if called from an async context.

## Examples

### Basic Usage

```python
# Set ASANA_PAT environment variable
client = AsanaClient()
task = client.tasks.get("task_gid")
```

### Explicit Token

```python
client = AsanaClient(token="your_pat_here")
task = await client.tasks.get_async("task_gid")
```

### Specify Workspace

```python
# From environment variable
# export ASANA_WORKSPACE_GID=1234567890123456
client = AsanaClient(token="...")

# Explicit (overrides env var)
client = AsanaClient(token="...", workspace_gid="1234567890123456")
```

### Custom Providers

```python
client = AsanaClient(
    auth_provider=MyAuthProvider(),
    cache_provider=MyCacheProvider(),
    log_provider=MyLogProvider(),
)
```

### SaveSession

```python
async with client.save_session() as session:
    session.track(task)
    task.name = "Updated"
    result = await session.commit_async()
```

### Cache Warming

```python
result = await client.warm_cache_async(
    gids=["123", "456", "789"],
    entry_type=EntryType.TASK,
)
print(f"Warmed: {result.warmed}, Skipped: {result.skipped}")
```

### Automation Engine

```python
if client.automation:
    client.automation.register(PipelineConversionRule())
    client.automation.register(MyCustomRule())
```

### Cache Metrics

```python
if client.cache_metrics:
    print(f"Hit rate: {client.cache_metrics.hit_rate_percent:.1f}%")
    print(f"API calls saved: {client.cache_metrics.api_calls_saved}")
```
