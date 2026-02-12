# Environment Variables

> Complete reference for autom8_asana environment variable configuration.

Last verified: 2026-02-12

## Quick Start

To make your first API call, set these three variables:

```bash
export ASANA_PAT="your_personal_access_token"
export ASANA_WORKSPACE_GID="1234567890123456"
export REDIS_HOST="localhost"  # Optional: enables Redis cache
```

Start the API server:

```bash
python -m autom8_asana.entrypoint
```

The server starts on `http://0.0.0.0:8000` by default.

## Core Asana

Basic Asana API connection settings.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ASANA_PAT` | string | - | No | Asana Personal Access Token. Required unless using provider-based auth. |
| `ASANA_WORKSPACE_GID` | string | - | Yes | Default workspace GID for operations |
| `ASANA_BASE_URL` | string | `https://app.asana.com/api/1.0` | No | Asana API base URL |
| `ASANA_STRICT_CONFIG` | boolean | `false` | No | Raise errors on invalid `ASANA_PROJECT_*` environment variables |
| `ASANA_ENVIRONMENT` | string | `development` | No | Environment name: `development`, `production`, `staging`, `test` |

## Cache Configuration

Master cache settings and general configuration.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ASANA_CACHE_ENABLED` | boolean | `true` | No | Master cache enable/disable |
| `ASANA_CACHE_PROVIDER` | string | auto-detect | No | Explicit provider: `memory`, `redis`, `tiered`, `none` |
| `ASANA_CACHE_TTL_DEFAULT` | integer | `300` | No | Default cache TTL in seconds |
| `ASANA_CACHE_MEMORY_MAX_SIZE` | integer | `10000` | No | Maximum entries in in-memory cache |
| `ASANA_CACHE_TTL_USER` | integer | `3600` | No | User metadata cache TTL (1 hour) |
| `ASANA_CACHE_TTL_CUSTOM_FIELD` | integer | `1800` | No | Custom field cache TTL (30 minutes) |
| `ASANA_CACHE_TTL_SECTION` | integer | `1800` | No | Section cache TTL (30 minutes) |
| `ASANA_CACHE_TTL_PROJECT` | integer | `900` | No | Project cache TTL (15 minutes) |
| `ASANA_CACHE_TTL_DETECTION` | integer | `300` | No | Entity detection cache TTL (5 minutes) |
| `ASANA_CACHE_TTL_DYNAMIC_INDEX` | integer | `3600` | No | Dynamic resolution index cache TTL (1 hour) |
| `ASANA_CACHE_MODIFICATION_CHECK_TTL` | float | `25.0` | No | Batch modification check TTL in seconds |
| `ASANA_CACHE_COALESCE_WINDOW_MS` | integer | `50` | No | Freshness coalescing window in milliseconds |
| `ASANA_CACHE_MAX_BATCH_SIZE` | integer | `100` | No | Maximum entries per batch freshness check |
| `ASANA_CACHE_DYNAMIC_INDEX_MAX_PER_ENTITY` | integer | `5` | No | Maximum dynamic indexes per entity (LRU eviction) |
| `ASANA_CACHE_REDIS_MAX_CONNECTIONS` | integer | `20` | No | Redis connection pool maximum size |
| `ASANA_CACHE_DF_COALESCER_MAX_WAIT` | float | `60.0` | No | DataFrame coalescer max wait seconds |
| `ASANA_CACHE_DF_CB_FAILURE_THRESHOLD` | integer | `3` | No | DataFrame circuit breaker failure threshold |
| `ASANA_CACHE_DF_CB_RESET_TIMEOUT` | integer | `60` | No | DataFrame circuit breaker reset timeout in seconds |
| `ASANA_CACHE_DF_CB_SUCCESS_THRESHOLD` | integer | `1` | No | DataFrame circuit breaker success threshold to close |

## S3 Cache Backend

S3-specific cache configuration.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ASANA_CACHE_S3_BUCKET` | string | `""` | Yes (for S3 cache) | S3 bucket name for cache storage |
| `ASANA_CACHE_S3_PREFIX` | string | `asana-cache` | No | S3 key prefix for cached objects |
| `ASANA_CACHE_S3_REGION` | string | `us-east-1` | No | AWS region for S3 bucket |
| `ASANA_CACHE_S3_ENDPOINT_URL` | string | - | No | Custom S3 endpoint (for LocalStack or S3-compatible storage) |

## Redis Backend

Redis connection settings for cache provider.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `REDIS_HOST` | string | - | Yes (for Redis cache) | Redis server hostname |
| `REDIS_PORT` | integer | `6379` | No | Redis server port |
| `REDIS_PASSWORD` | string | - | No | Redis authentication password |
| `REDIS_SSL` | boolean | `true` | No | Enable Redis SSL/TLS connection |
| `REDIS_SOCKET_TIMEOUT` | float | `2.0` | No | Redis socket timeout in seconds |
| `REDIS_CONNECT_TIMEOUT` | float | `5.0` | No | Redis connection timeout in seconds |

## Pacing

API rate management for large fetches.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ASANA_PACING_PAGES_PER_PAUSE` | integer | `25` | No | Pages to fetch before pausing |
| `ASANA_PACING_DELAY_SECONDS` | float | `2.0` | No | Seconds to sleep between page batches |
| `ASANA_PACING_CHECKPOINT_EVERY_N_PAGES` | integer | `50` | No | Pages between checkpoint writes to S3 |
| `ASANA_PACING_HIERARCHY_THRESHOLD` | integer | `100` | No | Parent GID count above which batched pacing activates |
| `ASANA_PACING_HIERARCHY_BATCH_SIZE` | integer | `50` | No | Parent GIDs per batch when pacing active |
| `ASANA_PACING_HIERARCHY_BATCH_DELAY` | float | `1.0` | No | Seconds to sleep between hierarchy batches |

## S3 Retry & Circuit Breaker

Resilience configuration for S3 DataFrame persistence.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ASANA_S3_RETRY_MAX_ATTEMPTS` | integer | `3` | No | Maximum retry attempts for S3 operations |
| `ASANA_S3_RETRY_BASE_DELAY` | float | `0.5` | No | Base delay for exponential backoff in seconds |
| `ASANA_S3_RETRY_MAX_DELAY` | float | `10.0` | No | Maximum delay cap in seconds |
| `ASANA_S3_BUDGET_PER_SUBSYSTEM_MAX` | integer | `20` | No | Per-subsystem retry budget |
| `ASANA_S3_BUDGET_GLOBAL_MAX` | integer | `50` | No | Global retry budget across all subsystems |
| `ASANA_S3_BUDGET_WINDOW_SECONDS` | float | `60.0` | No | Budget window in seconds |
| `ASANA_S3_CB_FAILURE_THRESHOLD` | integer | `5` | No | Consecutive failures before opening circuit |
| `ASANA_S3_CB_RECOVERY_TIMEOUT` | float | `60.0` | No | Seconds to wait before half-open probe |
| `ASANA_S3_CB_HALF_OPEN_MAX_PROBES` | integer | `2` | No | Successful probes required to close circuit |

## Webhooks

Inbound webhook authentication.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `WEBHOOK_INBOUND_TOKEN` | string | `""` | No | Shared secret for inbound webhook URL token verification. Endpoint returns 503 if empty. |
| `AUTH_JWKS_URL` | string | `https://auth.api.autom8y.io/.well-known/jwks.json` | No | JWKS endpoint for S2S JWT validation |
| `AUTH_ISSUER` | string | `auth.api.autom8y.io` | No | Expected JWT issuer for S2S authentication |
| `AUTH_DEV_MODE` | boolean | `false` | No | Bypass JWT validation in development |
| `AUTH_JWKS_CACHE_TTL` | integer | `300` | No | JWKS cache TTL in seconds |

## Events

Event subscription and routing configuration.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `EVENTS_ENABLED` | boolean | `false` | No | Master feature flag for event routing |
| `EVENTS_SQS_QUEUE_URL` | string | - | Yes (if events enabled) | SQS queue URL for event routing |
| `EVENTS_SUBSCRIPTIONS` | string | - | No | JSON array of subscription objects for advanced routing |

### Events Subscription Format

`EVENTS_SUBSCRIPTIONS` accepts a JSON array of subscription objects:

```json
[
  {
    "event_types": ["created", "updated"],
    "entity_types": ["Process", "Offer"],
    "destination": "https://sqs.us-east-1.amazonaws.com/123456789/queue-name"
  }
]
```

Fields:
- `event_types`: List of event types to match (empty = match all)
- `entity_types`: List of entity types to match (empty = match all)
- `destination`: Transport-specific destination (SQS queue URL)

## Data Service

Configuration for autom8_data satellite integration.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `AUTOM8_DATA_URL` | string | `http://localhost:8000` | No | Base URL for autom8_data service |
| `AUTOM8_DATA_API_KEY` | string | `AUTOM8_DATA_API_KEY` | No | Environment variable name for API key (not the key itself) |
| `AUTOM8_DATA_CACHE_TTL` | integer | `300` | No | Client-side insights cache TTL in seconds |
| `AUTOM8_DATA_INSIGHTS_ENABLED` | boolean | `true` | No | Emergency kill switch for insights integration |

## Workflow Features

Feature flags for workflow automation.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `AUTOM8_AUDIT_ENABLED` | boolean | `true` | No | Enable conversation audit workflow |

## DataFrame

DataFrame build and caching controls.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `DATAFRAME_CACHE_BYPASS` | boolean | `false` | No | Bypass DataFrame caching (for testing) |
| `SECTION_FRESHNESS_PROBE` | boolean | `true` | No | Enable section freshness checks. Set to `0` to disable. |
| `CONTAINER_MEMORY_MB` | integer | auto-detect | No | Container memory limit in MB. Overrides cgroup detection. |

## AWS Infrastructure

AWS service discovery and runtime detection. These are typically set by AWS, not manually.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `AWS_REGION` | string | `us-east-1` | No | AWS region for Secrets Manager and other services |
| `AWS_LAMBDA_RUNTIME_API` | string | - | No | Lambda runtime API endpoint. Presence indicates Lambda mode. |
| `ECS_CONTAINER_METADATA_URI_V4` | string | - | No | ECS container metadata endpoint (set by ECS) |
| `ECS_TASK_ID` | string | - | No | ECS task identifier (set by ECS) |

## API Server

API server configuration (ECS mode only).

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `API_HOST` | string | `0.0.0.0` | No | API server bind host |
| `API_PORT` | integer | `8000` | No | API server bind port |
| `ASANA_API_CORS_ALLOWED_ORIGINS` | string | `""` | No | Comma-separated list of allowed CORS origins |
| `ASANA_API_RATE_LIMIT_RPM` | integer | `100` | No | API rate limit in requests per minute per client |
| `ASANA_API_LOG_LEVEL` | string | `INFO` | No | API logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ASANA_API_DEBUG` | boolean | `false` | No | Enable debug mode (verbose logging, stack traces) |

## CloudWatch

Metrics emission for Lambda handlers.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CLOUDWATCH_NAMESPACE` | string | `autom8/lambda` | No | CloudWatch namespace for metrics |
| `ENVIRONMENT` | string | `staging` | No | Environment dimension for metrics: `staging`, `production` |

## Lambda

Lambda-specific configuration.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CACHE_WARMER_LAMBDA_ARN` | string | - | No | ARN of the cache warmer Lambda function for async invocation |

## Dynamic Projects

Entity-type-specific project GID overrides. Use this pattern for any entity type:

```bash
export ASANA_PROJECT_UNIT="1234567890123456"
export ASANA_PROJECT_OFFER="2345678901234567"
export ASANA_PROJECT_BUSINESS="3456789012345678"
export ASANA_PROJECT_CONTACT="4567890123456789"
```

| Variable Pattern | Type | Default | Required | Description |
|------------------|------|---------|----------|-------------|
| `ASANA_PROJECT_*` | string | - | No | Project GID override for entity type (e.g., `ASANA_PROJECT_UNIT`). Must be 10+ digit numeric string. |

Validation:
- GIDs must be numeric strings with 10+ digits
- Empty values are allowed (use class defaults)
- Invalid GIDs trigger warnings (or errors if `ASANA_STRICT_CONFIG=true`)

## Notes

### Environment Detection

Cache provider auto-detection follows this priority:

1. Explicit `ASANA_CACHE_PROVIDER` value
2. Environment detection:
   - Production/staging: Redis (requires `REDIS_HOST`)
   - Development: Memory cache (no external dependencies)

### Deployment Modes

The service supports two deployment modes:

**ECS Mode** (absence of `AWS_LAMBDA_RUNTIME_API`):
- Starts uvicorn API server
- Uses `API_HOST` and `API_PORT` for binding
- Supports all endpoints

**Lambda Mode** (presence of `AWS_LAMBDA_RUNTIME_API`):
- Invokes handler via awslambdaric
- Handler passed as command-line argument
- Limited to specific handler endpoints

### Security

Secrets should be injected via:
- AWS Secrets Manager (recommended for production)
- ECS task definition secrets
- Environment variables (development only)

Never commit secrets to version control.

## See Also

- [Installation Guide](../installation.md) - Setup instructions
- [API Reference](../api-reference/endpoints/entity-write.md) - API endpoint documentation
- [Cache Configuration](../cache-configuration.md) - Detailed cache configuration guide
