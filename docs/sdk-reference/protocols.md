# Protocols Reference

> Python Protocol classes for dependency injection

## Overview

The SDK uses Python Protocol classes to define contracts for pluggable dependencies. Protocols enable dependency injection without tight coupling to concrete implementations.

All protocols are defined in `autom8_asana.protocols` and follow structural typing (duck typing with static type checking). Any class that implements the required methods satisfies the protocol.

## Available Protocols

| Protocol | Purpose | Default Implementation |
|----------|---------|----------------------|
| `AuthProvider` | Authentication and secret retrieval | `EnvAuthProvider` |
| `CacheProvider` | Response caching with versioning | `NullCacheProvider` |
| `LogProvider` | Structured logging | `DefaultLogProvider` |
| `ObservabilityHook` | Metrics and distributed tracing | `NullObservabilityHook` |
| `ItemLoader` | Lazy loading for business models | None (SDK does not provide) |

## AuthProvider

Authentication provider for retrieving secrets and tokens.

### Interface

```python
from autom8_asana.protocols import AuthProvider

class AuthProvider(Protocol):
    def get_secret(self, key: str) -> str:
        """Retrieve a secret value by key.

        Args:
            key: Secret identifier (e.g., "ASANA_PAT")

        Returns:
            Secret value as string

        Raises:
            AuthenticationError: If secret not found or invalid
        """
        ...
```

### Built-in Implementations

#### EnvAuthProvider (Default)

Reads secrets from environment variables. Uses Pydantic Settings for common keys (`ASANA_PAT`, `ASANA_WORKSPACE_GID`) with fallback to direct environment variable lookup.

```python
# Set environment variable
export ASANA_PAT=your_token_here

# Uses EnvAuthProvider by default
client = AsanaClient()
```

#### SecretsManagerAuthProvider

Fetches secrets from AWS Secrets Manager following the autom8y naming convention: `autom8y/{service}/{key}`.

```python
from autom8_asana._defaults.auth import SecretsManagerAuthProvider

# Standard usage
provider = SecretsManagerAuthProvider(service_name="asana")
client = AsanaClient(auth_provider=provider)

# Custom secret path pattern
provider = SecretsManagerAuthProvider(
    service_name="asana",
    secret_path_pattern="myorg/{service}/{key}"
)
```

Constructor parameters:
- `service_name`: Service name for secret path construction (default: "asana")
- `secret_path_pattern`: Pattern with `{service}` and `{key}` placeholders (default: "autom8y/{service}/{key}")
- `region`: AWS region (default: `AWS_REGION` env var or "us-east-1")
- `client`: Optional boto3 `SecretsManagerClient` for testing

Methods:
- `clear_cache()`: Clear in-memory secret cache after rotation

Requires `boto3` package: `pip install boto3`

#### NotConfiguredAuthProvider

Placeholder that always raises `AuthenticationError`. Used when neither `token` nor `auth_provider` is supplied.

### Custom Implementation Example

```python
from autom8_asana.protocols import AuthProvider
from autom8_asana.exceptions import AuthenticationError

class VaultAuthProvider:
    """Fetch secrets from HashiCorp Vault."""

    def __init__(self, vault_client):
        self.vault = vault_client

    def get_secret(self, key: str) -> str:
        try:
            result = self.vault.secrets.kv.v2.read_secret_version(
                path=f"asana/{key}"
            )
            return result["data"]["data"]["value"]
        except Exception as e:
            raise AuthenticationError(
                f"Failed to retrieve secret '{key}' from Vault: {e}"
            ) from e

# Use with client
provider = VaultAuthProvider(vault_client)
client = AsanaClient(auth_provider=provider)
```

## CacheProvider

Cache provider for Asana API responses with version tracking and batch operations.

### Interface

The protocol defines both simple key-value operations (backward compatible) and versioned operations for intelligent cache invalidation.

```python
from autom8_asana.protocols import CacheProvider, WarmResult
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness import Freshness
from autom8_asana.cache.models.metrics import CacheMetrics
from datetime import datetime

class CacheProvider(Protocol):
    # Simple key-value operations (backward compatible)
    def get(self, key: str) -> dict[str, Any] | None: ...
    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...

    # Versioned operations
    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: Freshness | None = None,
    ) -> CacheEntry | None: ...

    def set_versioned(self, key: str, entry: CacheEntry) -> None: ...

    # Batch operations
    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]: ...

    def set_batch(self, entries: dict[str, CacheEntry]) -> None: ...

    # Cache management
    def warm(
        self,
        gids: list[str],
        entry_types: list[EntryType] | None = None,
    ) -> WarmResult: ...

    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool: ...

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None: ...

    # Health and observability
    def is_healthy(self) -> bool: ...
    def get_metrics(self) -> CacheMetrics: ...
    def reset_metrics(self) -> None: ...
    def clear_all_tasks(self) -> int: ...
```

### Cache Keys

Cache keys follow the pattern: `{resource_type}:{gid}` (e.g., `"task:12345"`).

### Entry Types

The `EntryType` enum defines types of cached resources:

| EntryType | Description | Versioning |
|-----------|-------------|------------|
| `TASK` | Task entity | Uses task.modified_at |
| `SUBTASKS` | Task subtasks list | Uses parent task.modified_at |
| `DEPENDENCIES` | Task dependencies | Uses task.modified_at |
| `DEPENDENTS` | Task dependents | Uses task.modified_at |
| `STORIES` | Task comments/stories | Uses task.modified_at |
| `ATTACHMENTS` | Task attachments | Uses task.modified_at |
| `PROJECT` | Project entity | Uses project.modified_at |
| `SECTION` | Section entity | No versioning (no modified_at) |
| `USER` | User entity | No versioning (no modified_at) |
| `CUSTOM_FIELD` | Custom field entity | No versioning (no modified_at) |
| `DATAFRAME` | Polars DataFrame | Project-scoped |
| `INSIGHTS` | autom8_data insights | Configurable TTL |

### Built-in Implementations

#### NullCacheProvider (Default)

No-op cache provider. All operations succeed silently without storing data.

```python
from autom8_asana._defaults.cache import NullCacheProvider

# Explicitly disable caching
client = AsanaClient(
    token="...",
    cache_provider=NullCacheProvider()
)
```

#### InMemoryCacheProvider

Thread-safe in-memory cache with TTL support. Not recommended for production multi-process deployments.

```python
from autom8_asana._defaults.cache import InMemoryCacheProvider

# 5 minute default TTL, max 10,000 entries
cache = InMemoryCacheProvider(default_ttl=300, max_size=10000)
client = AsanaClient(cache_provider=cache)
```

Constructor parameters:
- `default_ttl`: Default TTL in seconds (None = no expiration)
- `max_size`: Maximum entries before eviction (default: 10000)

#### RedisCacheProvider

Production Redis backend with connection pooling. See `autom8_asana.cache.providers.redis` for implementation details.

### Custom Implementation Example

```python
from autom8_asana.protocols import CacheProvider, WarmResult
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness import Freshness
from autom8_asana.cache.models.metrics import CacheMetrics
from datetime import datetime
import memcache

class MemcachedProvider:
    """Memcached cache provider."""

    def __init__(self, servers: list[str]):
        self.mc = memcache.Client(servers)
        self._metrics = CacheMetrics()

    def get(self, key: str) -> dict[str, Any] | None:
        value = self.mc.get(key)
        if value:
            self._metrics.record_hit()
        else:
            self._metrics.record_miss()
        return value

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        self.mc.set(key, value, time=ttl or 0)
        self._metrics.record_write()

    def delete(self, key: str) -> None:
        self.mc.delete(key)

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: Freshness | None = None,
    ) -> CacheEntry | None:
        internal_key = f"{key}:{entry_type.value}"
        value = self.mc.get(internal_key)
        if value:
            self._metrics.record_hit()
            return CacheEntry(**value)
        self._metrics.record_miss()
        return None

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        internal_key = f"{key}:{entry.entry_type.value}"
        ttl = entry.ttl or 0
        self.mc.set(internal_key, entry.__dict__, time=ttl)
        self._metrics.record_write()

    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        internal_keys = [f"{k}:{entry_type.value}" for k in keys]
        results = self.mc.get_multi(internal_keys)
        return {
            k: CacheEntry(**v) if v else None
            for k, v in zip(keys, results.values())
        }

    def set_batch(self, entries: dict[str, CacheEntry]) -> None:
        mapping = {
            f"{k}:{e.entry_type.value}": e.__dict__
            for k, e in entries.items()
        }
        self.mc.set_multi(mapping)

    def warm(
        self,
        gids: list[str],
        entry_types: list[EntryType] | None = None,
    ) -> WarmResult:
        # Not implemented
        return WarmResult(skipped=len(gids))

    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool:
        entry = self.get_versioned(key, entry_type)
        return entry is not None and entry.version >= current_version

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        if entry_types is None:
            entry_types = list(EntryType)
        for et in entry_types:
            self.mc.delete(f"{key}:{et.value}")

    def is_healthy(self) -> bool:
        try:
            self.mc.set("__health_check__", "ok", time=1)
            return True
        except Exception:
            return False

    def get_metrics(self) -> CacheMetrics:
        return self._metrics

    def reset_metrics(self) -> None:
        self._metrics.reset()

    def clear_all_tasks(self) -> int:
        # Not implemented - memcached doesn't support key patterns
        return 0

# Use with client
cache = MemcachedProvider(servers=["127.0.0.1:11211"])
client = AsanaClient(cache_provider=cache)
```

## LogProvider

Logging provider compatible with Python's `logging.Logger`.

### Interface

```python
from autom8_asana.protocols import LogProvider

class LogProvider(Protocol):
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
```

Any `logging.Logger` instance automatically satisfies this protocol.

### CacheLoggingProvider Extension

Extended protocol for cache event logging:

```python
from autom8_asana.protocols.log import CacheLoggingProvider, CacheEventType

class CacheLoggingProvider(Protocol):
    def log_cache_event(
        self,
        event_type: CacheEventType,  # "hit" | "miss" | "write" | "evict" | "expire" | "error" | "overflow_skip"
        key: str,
        entry_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...
```

### Built-in Implementation

#### DefaultLogProvider

Uses Python's `logging` module with structured logging support via the `extra` parameter.

```python
from autom8_asana._defaults.log import DefaultLogProvider
import logging

# Basic usage
log = DefaultLogProvider(level=logging.INFO)
client = AsanaClient(log_provider=log)

# With structured context
from autom8_asana.observability import LogContext

ctx = LogContext(correlation_id="abc123", operation="track")
log.info("Processing entity %s", entity.gid, extra=ctx.to_dict())

# Disable cache event logging
log = DefaultLogProvider(enable_cache_logging=False)
```

Constructor parameters:
- `level`: Logging level (default: `logging.INFO`)
- `enable_cache_logging`: Whether to log cache events (default: `True`)
- `name`: Logger name (default: "autom8_asana")

Methods:
- Standard logging methods: `debug`, `info`, `warning`, `error`, `exception`
- `isEnabledFor(level)`: Check if logger would emit at given level
- `log_cache_event(...)`: Log cache events (CacheLoggingProvider extension)

### Using Standard Library Logger

```python
import logging

# Standard library logger works directly
logger = logging.getLogger("my_app")
logger.setLevel(logging.DEBUG)
client = AsanaClient(log_provider=logger)
```

### Custom Implementation Example

```python
from autom8_asana.protocols import LogProvider
import structlog

class StructlogProvider:
    """Structured logging with structlog."""

    def __init__(self):
        self.log = structlog.get_logger()

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        extra = kwargs.pop("extra", {})
        self.log.debug(msg % args if args else msg, **extra)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        extra = kwargs.pop("extra", {})
        self.log.info(msg % args if args else msg, **extra)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        extra = kwargs.pop("extra", {})
        self.log.warning(msg % args if args else msg, **extra)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        extra = kwargs.pop("extra", {})
        self.log.error(msg % args if args else msg, **extra)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        extra = kwargs.pop("extra", {})
        self.log.exception(msg % args if args else msg, **extra)

# Use with client
log = StructlogProvider()
client = AsanaClient(log_provider=log)
```

## ObservabilityHook

Protocol for metrics collection and distributed tracing integration.

### Interface

All methods are async to support non-blocking telemetry backends.

```python
from autom8_asana.protocols import ObservabilityHook

class ObservabilityHook(Protocol):
    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None: ...

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None: ...

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None: ...

    async def on_rate_limit(self, retry_after_seconds: int) -> None: ...

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None: ...

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None: ...
```

### Built-in Implementation

#### NullObservabilityHook (Default)

No-op hook that returns immediately. Used when no custom hook is provided.

```python
from autom8_asana._defaults.observability import NullObservabilityHook

# These are equivalent:
client = AsanaClient(token="...")
client = AsanaClient(token="...", observability_hook=NullObservabilityHook())
```

### Custom Implementation Example

```python
from autom8_asana.protocols import ObservabilityHook
from datadog import statsd
import ddtrace

class DatadogHook:
    """Datadog APM and metrics integration."""

    def __init__(self):
        self.tracer = ddtrace.tracer
        self.span = None

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        self.span = self.tracer.trace("asana.request")
        self.span.set_tag("http.method", method)
        self.span.set_tag("http.path", path)
        self.span.set_tag("correlation_id", correlation_id)

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        if self.span:
            self.span.set_tag("http.status_code", status)
            self.span.finish()
        statsd.histogram("asana.request.duration", duration_ms)
        statsd.increment("asana.request.count", tags=[f"status:{status}"])

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None:
        if self.span:
            self.span.set_error(error)
            self.span.finish()
        statsd.increment("asana.request.error", tags=[f"error_type:{type(error).__name__}"])

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        statsd.increment("asana.rate_limit")
        statsd.gauge("asana.rate_limit.retry_after", retry_after_seconds)

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        statsd.event(
            title="Asana Circuit Breaker State Change",
            text=f"{old_state} -> {new_state}",
            alert_type="warning" if new_state == "open" else "info",
        )

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None:
        statsd.increment("asana.retry", tags=[f"attempt:{attempt}"])

# Use with client
hook = DatadogHook()
client = AsanaClient(
    token="...",
    observability_hook=hook
)
```

## ItemLoader

Protocol for lazy loading additional resource data. The SDK provides the protocol but no implementation.

### Interface

```python
from autom8_asana.protocols import ItemLoader
from autom8_asana.models.base import AsanaResource

class ItemLoader(Protocol):
    async def load_async(
        self,
        resource: AsanaResource,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Load additional data for a resource.

        Args:
            resource: Resource with gid and resource_type
            fields: Optional specific fields to load (None = all)

        Returns:
            Dict containing loaded field values

        Raises:
            NotFoundError: If resource doesn't exist
            AsanaError: On API/cache errors
        """
        ...

    def load(
        self,
        resource: AsanaResource,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sync version of load_async."""
        ...
```

### Purpose

The `ItemLoader` protocol enables lazy loading behavior in business models. The SDK provides the hook but does not implement it. Consumers (like the autom8 monolith) implement this protocol to add lazy loading to their business models.

### Implementation Example

```python
from autom8_asana.protocols import ItemLoader
from autom8_asana.models.base import AsanaResource
from typing import Any

class Autom8ItemLoader:
    """Lazy loader using cache and client."""

    def __init__(self, cache, client):
        self._cache = cache
        self._client = client

    async def load_async(
        self,
        resource: AsanaResource,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        # Check cache first
        cached = self._cache.get(resource.gid)
        if cached and (fields is None or all(f in cached for f in fields)):
            return cached

        # Fetch from API
        if resource.resource_type == "task":
            data = await self._client.tasks.get_async(
                resource.gid,
                opt_fields=fields,
                raw=True,
            )
        else:
            raise NotImplementedError(f"Unsupported resource type: {resource.resource_type}")

        # Update cache
        self._cache.set(resource.gid, data)
        return data

    def load(
        self,
        resource: AsanaResource,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        import asyncio
        return asyncio.run(self.load_async(resource, fields))

# Use in business model
class Item(AsanaResource):
    _loader: ItemLoader | None = None

    def __getattr__(self, name: str) -> Any:
        if self._loader and name in self._lazy_fields:
            data = self._loader.load(self, [name])
            return data.get(name)
        raise AttributeError(name)
```

## Passing Providers to AsanaClient

All providers are passed as constructor parameters:

```python
from autom8_asana import AsanaClient

client = AsanaClient(
    token="...",                         # Or auth_provider=...
    cache_provider=my_cache,
    log_provider=my_logger,
    observability_hook=my_telemetry,
)
```

Cross-reference: See [AsanaClient Reference](client.md) for constructor details.

## Protocol Verification

Protocols use structural typing. To verify a class satisfies a protocol at runtime:

```python
from autom8_asana.protocols import ObservabilityHook
import isinstance

hook = MyCustomHook()
if isinstance(hook, ObservabilityHook):
    print("Hook satisfies protocol")
```

Note: `ObservabilityHook` is decorated with `@runtime_checkable` to enable runtime verification. Other protocols use static type checking only.

## See Also

- [AsanaClient Reference](client.md) - Client constructor and provider configuration
- [Configuration Guide](../guides/configuration.md) - Environment-based configuration
- [Cache Configuration](../guides/caching.md) - Cache TTLs and versioning strategies
