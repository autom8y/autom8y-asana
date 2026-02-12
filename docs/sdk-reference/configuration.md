# Configuration Reference

Complete reference for all configuration options in autom8_asana SDK.

## Overview

The SDK provides configuration through two mechanisms:

1. **Programmatic configuration**: Pass `AsanaConfig` to client constructor (takes precedence)
2. **Environment variables**: Set `ASANA_*` environment variables (loaded via settings)

All configuration uses dataclasses with sensible defaults. Override only what you need to change.

## Quick Start

Basic client initialization uses defaults:

```python
from autom8_asana import AsanaClient

# All defaults
client = AsanaClient()
```

Custom configuration:

```python
from autom8_asana.config import AsanaConfig, RateLimitConfig, CacheConfig

config = AsanaConfig(
    rate_limit=RateLimitConfig(max_requests=1000, window_seconds=60),
    cache=CacheConfig(enabled=True, provider="redis"),
)
client = AsanaClient(config=config)
```

From environment variables:

```python
import os
os.environ["ASANA_CACHE_ENABLED"] = "true"
os.environ["ASANA_CACHE_PROVIDER"] = "memory"

# Reads from environment
client = AsanaClient()
```

## AsanaConfig

Main configuration class for AsanaClient.

### Constructor Signature

```python
@dataclass
class AsanaConfig:
    base_url: str = "https://app.asana.com/api/1.0"
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    concurrency: ConcurrencyConfig = field(default_factory=ConcurrencyConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    dataframe: DataFrameConfig = field(default_factory=DataFrameConfig)
    automation: AutomationConfig = field(default_factory=AutomationConfig)
    token_key: str = "ASANA_PAT"
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | str | `https://app.asana.com/api/1.0` | Asana API base URL |
| `rate_limit` | RateLimitConfig | Default factory | Rate limiting configuration |
| `retry` | RetryConfig | Default factory | Retry behavior configuration |
| `concurrency` | ConcurrencyConfig | Default factory | Concurrency limits |
| `timeout` | TimeoutConfig | Default factory | HTTP timeout values |
| `connection_pool` | ConnectionPoolConfig | Default factory | Connection pool sizing |
| `circuit_breaker` | CircuitBreakerConfig | Default factory | Circuit breaker settings |
| `cache` | CacheConfig | Default factory | Cache configuration |
| `dataframe` | DataFrameConfig | Default factory | DataFrame operation settings |
| `automation` | AutomationConfig | Default factory | Automation layer settings |
| `token_key` | str | `ASANA_PAT` | Environment variable name for auth token |

### Example

```python
from autom8_asana.config import (
    AsanaConfig,
    RateLimitConfig,
    RetryConfig,
    CacheConfig,
)

config = AsanaConfig(
    base_url="https://app.asana.com/api/1.0",
    rate_limit=RateLimitConfig(max_requests=1200),
    retry=RetryConfig(max_retries=3),
    cache=CacheConfig(enabled=True, provider="memory"),
)
```

## RateLimitConfig

Controls rate limiting for Asana API requests.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_requests` | int | 1500 | Maximum requests per window (Asana's limit) |
| `window_seconds` | int | 60 | Time window in seconds |

### Validation

Raises `ConfigurationError` if:
- `max_requests <= 0`
- `window_seconds <= 0`

### Example

```python
from autom8_asana.config import RateLimitConfig

# Conservative rate limiting
rate_config = RateLimitConfig(
    max_requests=1000,
    window_seconds=60,
)
```

## RetryConfig

Configures retry behavior with exponential backoff.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_retries` | int | 5 | Maximum retry attempts |
| `base_delay` | float | 0.5 | Initial delay in seconds |
| `max_delay` | float | 60.0 | Maximum delay cap in seconds |
| `exponential_base` | float | 2.0 | Multiplier for exponential backoff |
| `jitter` | bool | True | Add random jitter to delays |
| `retryable_status_codes` | frozenset[int] | `{429, 503, 504}` | HTTP codes that trigger retry |

### Validation

Raises `ConfigurationError` if:
- `max_retries < 0`
- `base_delay < 0`
- `max_delay <= 0`
- `exponential_base < 1`

### Example

```python
from autom8_asana.config import RetryConfig

# Aggressive retry with longer delays
retry_config = RetryConfig(
    max_retries=10,
    base_delay=1.0,
    max_delay=120.0,
    exponential_base=2.0,
    jitter=True,
)
```

## ConcurrencyConfig

Controls concurrent API request limits with adaptive behavior.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `read_limit` | int | 50 | Concurrent GET requests (AIMD ceiling) |
| `write_limit` | int | 15 | Concurrent mutation requests (AIMD ceiling) |
| `aimd_enabled` | bool | True | Enable adaptive concurrency (AIMD) |
| `aimd_floor` | int | 1 | Minimum concurrency (>= 1) |
| `aimd_multiplicative_decrease` | float | 0.5 | Decrease factor on 429 |
| `aimd_additive_increase` | float | 1.0 | Increase per success |
| `aimd_grace_period_seconds` | float | 5.0 | Suppress increases after decrease |
| `aimd_increase_interval_seconds` | float | 2.0 | Min time between increases |
| `aimd_cooldown_trigger` | int | 5 | Consecutive 429s for cooldown warning |
| `aimd_cooldown_duration_seconds` | float | 30.0 | Cooldown duration (unused in v1) |

### Validation

Raises `ConfigurationError` if:
- `read_limit <= 0`
- `write_limit <= 0`
- `aimd_floor < 1`
- `aimd_floor > read_limit` or `aimd_floor > write_limit`
- `aimd_multiplicative_decrease` not in (0, 1)

### AIMD Behavior

When `aimd_enabled=True`, the SDK uses Additive Increase Multiplicative Decrease (AIMD) for adaptive concurrency:
- On 429 rate limit: Halve concurrency
- On success: Increment concurrency by 1
- Grace period after decrease: No increases for 5 seconds

When `aimd_enabled=False`, uses fixed semaphore with static limits.

### Example

```python
from autom8_asana.config import ConcurrencyConfig

# Conservative concurrency with AIMD
concurrency_config = ConcurrencyConfig(
    read_limit=25,
    write_limit=10,
    aimd_enabled=True,
    aimd_floor=2,
)
```

## TimeoutConfig

HTTP timeout configuration.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `connect` | float | 5.0 | Timeout for establishing connection (seconds) |
| `read` | float | 30.0 | Timeout for reading response (seconds) |
| `write` | float | 30.0 | Timeout for sending request body (seconds) |
| `pool` | float | 10.0 | Timeout for acquiring connection from pool (seconds) |

### Validation

Raises `ConfigurationError` if any timeout value is not positive.

### Example

```python
from autom8_asana.config import TimeoutConfig

# Longer timeouts for slow networks
timeout_config = TimeoutConfig(
    connect=10.0,
    read=60.0,
    write=60.0,
    pool=15.0,
)
```

## ConnectionPoolConfig

HTTP connection pool sizing.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_connections` | int | 100 | Maximum total connections |
| `max_keepalive_connections` | int | 20 | Maximum keepalive connections |
| `keepalive_expiry` | float | 30.0 | Keepalive expiry time (seconds) |

### Validation

Raises `ConfigurationError` if any value is not positive.

### Example

```python
from autom8_asana.config import ConnectionPoolConfig

# Larger pool for high-throughput applications
pool_config = ConnectionPoolConfig(
    max_connections=200,
    max_keepalive_connections=50,
    keepalive_expiry=60.0,
)
```

## CircuitBreakerConfig

Circuit breaker for cascading failure prevention.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | False | Whether circuit breaker is active (opt-in) |
| `failure_threshold` | int | 5 | Consecutive failures before opening circuit |
| `recovery_timeout` | float | 60.0 | Seconds before half-open probe |
| `half_open_max_calls` | int | 1 | Successful probes required to close circuit |

### Validation

Raises `ConfigurationError` if:
- `failure_threshold < 1`
- `recovery_timeout <= 0`
- `half_open_max_calls < 1`

### Example

```python
from autom8_asana.config import CircuitBreakerConfig

# Enable circuit breaker with custom thresholds
cb_config = CircuitBreakerConfig(
    enabled=True,
    failure_threshold=10,
    recovery_timeout=120.0,
    half_open_max_calls=2,
)
```

## CacheConfig

Cache behavior configuration with provider selection.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | True | Whether caching is enabled |
| `provider` | str \| None | None | Explicit provider ("memory", "redis", "tiered", "none") or auto-detect |
| `dataframe_caching` | bool | True | Enable DataFrame-specific caching |
| `entity_ttls` | dict[str, int] | See below | Entity-type-specific TTL overrides (seconds) |
| `ttl` | TTLSettings | Default factory | TTL configuration settings |
| `overflow` | OverflowSettings | Default factory | Overflow threshold settings |
| `freshness` | Freshness | `Freshness.EVENTUAL` | Default freshness mode |

### Entity-Specific TTLs

Default `entity_ttls` values:

| Entity Type | Default TTL | Rationale |
|-------------|-------------|-----------|
| `business` | 3600s (1 hour) | Rarely changes |
| `contact` | 900s (15 min) | Occasional updates |
| `unit` | 900s (15 min) | Occasional updates |
| `offer` | 180s (3 min) | Frequently updated |
| `process` | 60s (1 min) | Pipeline state changes often |
| `address` | 3600s (1 hour) | Rarely changes |
| `hours` | 3600s (1 hour) | Rarely changes |
| (default) | 300s (5 min) | Fallback for unknown types |

### Methods

#### `get_entity_ttl(entity_type: str) -> int`

Get TTL for entity type with fallback to default. Case-insensitive.

```python
config = CacheConfig()
ttl = config.get_entity_ttl("business")  # Returns 3600
ttl = config.get_entity_ttl("unknown")   # Returns 300
```

#### `from_env() -> CacheConfig`

Create configuration from environment variables.

```python
import os
os.environ["ASANA_CACHE_ENABLED"] = "true"
os.environ["ASANA_CACHE_PROVIDER"] = "redis"
os.environ["ASANA_CACHE_TTL_DEFAULT"] = "600"

config = CacheConfig.from_env()
```

### Example

```python
from autom8_asana.config import CacheConfig
from autom8_asana.cache.models.settings import TTLSettings
from autom8_asana.cache.models.freshness import Freshness

# Custom cache configuration
cache_config = CacheConfig(
    enabled=True,
    provider="redis",
    entity_ttls={
        "business": 7200,  # 2 hours
        "offer": 300,      # 5 minutes
    },
    freshness=Freshness.EVENTUAL,
)

# Or from environment
cache_config = CacheConfig.from_env()
```

### TTLSettings

Nested TTL configuration with project and entry-type overrides.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_ttl` | int | 300 | Default TTL in seconds |
| `project_ttls` | dict[str, int] | `{}` | Per-project TTL overrides keyed by project GID |
| `entry_type_ttls` | dict[str, int] | `{}` | Per-entry-type TTL overrides |

### OverflowSettings

Per-relationship overflow thresholds. When exceeded, data is not cached.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `subtasks` | int | 40 | Maximum subtasks before skipping cache |
| `dependencies` | int | 40 | Maximum dependencies before skipping cache |
| `dependents` | int | 40 | Maximum dependents before skipping cache |
| `stories` | int | 100 | Maximum stories before skipping cache |
| `attachments` | int | 40 | Maximum attachments before skipping cache |

### Freshness Modes

Cache freshness controls validation behavior:

| Mode | Value | Behavior |
|------|-------|----------|
| `STRICT` | `"strict"` | Always validate version against source |
| `EVENTUAL` | `"eventual"` | Return cached if within TTL |
| `IMMEDIATE` | `"immediate"` | Return cached without validation |

## DataFrameConfig

Configuration for DataFrame operations.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `parallel_fetch_enabled` | bool | True | Enable parallel section fetch |
| `max_concurrent_sections` | int | 8 | Maximum concurrent section fetches (1-20) |
| `cache_enabled` | bool | True | Enable automatic DataFrame caching |

### Validation

Raises `ConfigurationError` if `max_concurrent_sections` not in range 1-20.

### Example

```python
from autom8_asana.config import DataFrameConfig

# Conservative parallel fetch
df_config = DataFrameConfig(
    parallel_fetch_enabled=True,
    max_concurrent_sections=4,
    cache_enabled=True,
)
```

## AutomationConfig

Configuration for automation layer.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | True | Master switch for automation |
| `max_cascade_depth` | int | 5 | Maximum nested automation depth |
| `rules_source` | str | `"inline"` | Where to load rules ("inline", "file", "api") |
| `pipeline_templates` | dict[str, str] | `{}` | ProcessType to project GID mapping (legacy) |
| `pipeline_stages` | dict[str, PipelineStage] | `{}` | ProcessType to PipelineStage mapping (preferred) |

### Validation

Raises `ConfigurationError` if:
- `max_cascade_depth < 1`
- `rules_source` not in ("inline", "file", "api")

### PipelineStage

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_gid` | str | Required | Target Asana project GID |
| `template_section` | str | `"Template"` | Section containing template tasks |
| `target_section` | str | `"Opportunity"` | Section to place new tasks |
| `due_date_offset_days` | int \| None | None | Days from today for due date |
| `assignee_gid` | str \| None | None | Fixed assignee GID |
| `business_cascade_fields` | list[str] \| None | None | Fields to cascade from Business |
| `unit_cascade_fields` | list[str] \| None | None | Fields to cascade from Unit |
| `process_carry_through_fields` | list[str] \| None | None | Fields to carry from source Process |
| `field_name_mapping` | dict[str, str] | `{}` | Map source to target field names |

### Example

```python
from autom8_asana.config import AutomationConfig, PipelineStage

automation_config = AutomationConfig(
    enabled=True,
    max_cascade_depth=3,
    pipeline_stages={
        "onboarding": PipelineStage(
            project_gid="1234567890123",
            template_section="Template",
            target_section="Opportunity",
            due_date_offset_days=7,
            assignee_gid="9876543210987",
        ),
    },
)
```

## Environment Variables

All configuration can be set via environment variables with `ASANA_` prefix.

### Authentication

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ASANA_PAT` | str | None | Personal Access Token for API authentication |
| `ASANA_WORKSPACE_GID` | str | None | Default workspace GID |
| `ASANA_BASE_URL` | str | `https://app.asana.com/api/1.0` | API base URL |
| `ASANA_STRICT_CONFIG` | bool | False | Enable strict validation mode |
| `ASANA_ENVIRONMENT` | str | `development` | Environment (development, production, staging, test) |

### Cache Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ASANA_CACHE_ENABLED` | bool | True | Master enable/disable for caching |
| `ASANA_CACHE_PROVIDER` | str | None | Explicit provider ("memory", "redis", "tiered", "none") |
| `ASANA_CACHE_TTL_DEFAULT` | int | 300 | Default cache TTL in seconds |
| `ASANA_CACHE_MEMORY_MAX_SIZE` | int | 10000 | Max entries in in-memory cache |
| `ASANA_CACHE_S3_BUCKET` | str | Empty | S3 bucket name for cache storage |
| `ASANA_CACHE_S3_PREFIX` | str | `asana-cache` | S3 key prefix for cached objects |
| `ASANA_CACHE_S3_REGION` | str | `us-east-1` | AWS region for S3 bucket |
| `ASANA_CACHE_S3_ENDPOINT_URL` | str | None | Custom S3 endpoint (LocalStack) |

### Entity-Specific Cache TTLs

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ASANA_CACHE_TTL_USER` | int | 3600 | User metadata cache TTL (seconds) |
| `ASANA_CACHE_TTL_CUSTOM_FIELD` | int | 1800 | Custom field cache TTL (seconds) |
| `ASANA_CACHE_TTL_SECTION` | int | 1800 | Section cache TTL (seconds) |
| `ASANA_CACHE_TTL_PROJECT` | int | 900 | Project cache TTL (seconds) |
| `ASANA_CACHE_TTL_DETECTION` | int | 300 | Detection result cache TTL (seconds) |
| `ASANA_CACHE_TTL_DYNAMIC_INDEX` | int | 3600 | Dynamic index cache TTL (seconds) |

### Cache Operational Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ASANA_CACHE_MODIFICATION_CHECK_TTL` | float | 25.0 | Batch modification check TTL (seconds) |
| `ASANA_CACHE_COALESCE_WINDOW_MS` | int | 50 | Freshness coalescing window (milliseconds) |
| `ASANA_CACHE_MAX_BATCH_SIZE` | int | 100 | Max entries per batch freshness check |
| `ASANA_CACHE_DYNAMIC_INDEX_MAX_PER_ENTITY` | int | 5 | Max dynamic indexes per entity (LRU) |
| `ASANA_CACHE_REDIS_MAX_CONNECTIONS` | int | 20 | Redis adapter max connections |
| `ASANA_CACHE_DF_COALESCER_MAX_WAIT` | float | 60.0 | DataFrame coalescer max wait (seconds) |
| `ASANA_CACHE_DF_CB_FAILURE_THRESHOLD` | int | 3 | DataFrame circuit breaker failures |
| `ASANA_CACHE_DF_CB_RESET_TIMEOUT` | int | 60 | DataFrame circuit breaker reset (seconds) |
| `ASANA_CACHE_DF_CB_SUCCESS_THRESHOLD` | int | 1 | DataFrame circuit breaker successes |

### Pacing Configuration

Controls rate limiting for large section and hierarchy fetches.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ASANA_PACING_PAGES_PER_PAUSE` | int | 25 | Pages fetched before pausing |
| `ASANA_PACING_DELAY_SECONDS` | float | 2.0 | Sleep between page batches (seconds) |
| `ASANA_PACING_CHECKPOINT_EVERY_N_PAGES` | int | 50 | Pages between checkpoint writes |
| `ASANA_PACING_HIERARCHY_THRESHOLD` | int | 100 | Parent GIDs for batched pacing activation |
| `ASANA_PACING_HIERARCHY_BATCH_SIZE` | int | 50 | Parent GIDs per batch |
| `ASANA_PACING_HIERARCHY_BATCH_DELAY` | float | 1.0 | Sleep between hierarchy batches (seconds) |

### S3 Resilience Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ASANA_S3_RETRY_MAX_ATTEMPTS` | int | 3 | S3 retry max attempts |
| `ASANA_S3_RETRY_BASE_DELAY` | float | 0.5 | S3 retry base delay (seconds) |
| `ASANA_S3_RETRY_MAX_DELAY` | float | 10.0 | S3 retry max delay (seconds) |
| `ASANA_S3_BUDGET_PER_SUBSYSTEM_MAX` | int | 20 | S3 retry budget per subsystem |
| `ASANA_S3_BUDGET_GLOBAL_MAX` | int | 50 | S3 retry budget global max |
| `ASANA_S3_BUDGET_WINDOW_SECONDS` | float | 60.0 | S3 retry budget window (seconds) |
| `ASANA_S3_CB_FAILURE_THRESHOLD` | int | 5 | S3 circuit breaker failure threshold |
| `ASANA_S3_CB_RECOVERY_TIMEOUT` | float | 60.0 | S3 circuit breaker recovery timeout (seconds) |
| `ASANA_S3_CB_HALF_OPEN_MAX_PROBES` | int | 2 | S3 circuit breaker half-open probes |

### Redis Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REDIS_HOST` | str | None | Redis host for cache (required for Redis provider) |
| `REDIS_PORT` | int | 6379 | Redis port |
| `REDIS_PASSWORD` | str | None | Redis password (optional) |
| `REDIS_SSL` | bool | True | Enable Redis SSL/TLS |
| `REDIS_SOCKET_TIMEOUT` | float | 2.0 | Redis socket timeout (seconds) |
| `REDIS_CONNECT_TIMEOUT` | float | 5.0 | Redis connection timeout (seconds) |

### Webhook Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `WEBHOOK_INBOUND_TOKEN` | str | Empty | Shared secret for inbound webhook auth |

## Configuration Hierarchy

When both programmatic config and environment variables are set, programmatic config takes precedence:

```python
import os
from autom8_asana import AsanaClient
from autom8_asana.config import AsanaConfig, CacheConfig

# Environment says disabled
os.environ["ASANA_CACHE_ENABLED"] = "false"

# Programmatic config overrides
config = AsanaConfig(
    cache=CacheConfig(enabled=True)  # Takes precedence
)

client = AsanaClient(config=config)  # Cache is enabled
```

## Provider Auto-Detection

When `CacheConfig.provider` is None, the SDK auto-detects based on environment:

1. Check `ASANA_CACHE_PROVIDER` environment variable
2. If `REDIS_HOST` is set, use "redis"
3. If `ASANA_ENVIRONMENT` is "production", use "tiered" (memory + S3)
4. Otherwise use "memory"

Explicit provider selection overrides auto-detection:

```python
from autom8_asana.config import CacheConfig

# Force memory cache even in production
config = CacheConfig(provider="memory")
```

## Validation

All config classes validate on initialization. Invalid values raise `ConfigurationError`:

```python
from autom8_asana.config import RateLimitConfig
from autom8_asana.exceptions import ConfigurationError

try:
    config = RateLimitConfig(max_requests=-1)
except ConfigurationError as e:
    print(f"Invalid config: {e}")
    # Output: max_requests must be positive, got -1
```

## See Also

- [Installation Guide](../getting-started/installation.md) - Setup and authentication
- [Caching Guide](caching.md) - Cache provider configuration and behavior
- [API Reference](api-reference.md) - Client methods and usage patterns
