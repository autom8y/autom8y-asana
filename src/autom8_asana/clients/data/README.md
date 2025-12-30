# Data Service Client

The `DataServiceClient` provides access to the autom8_data analytics insights API, enabling retrieval of business performance metrics for ad campaigns.

## Quick Start

### Async Usage (Recommended)

```python
from autom8_asana.clients.data import DataServiceClient

async with DataServiceClient() as client:
    response = await client.get_insights_async(
        factory="account",
        office_phone="+17705753103",
        vertical="chiropractic",
        period="t30",
    )

    # Convert to Polars DataFrame
    df = response.to_dataframe()
    print(f"Retrieved {response.metadata.row_count} rows")
```

### Sync Usage

```python
from autom8_asana.clients.data import DataServiceClient

with DataServiceClient() as client:
    response = client.get_insights(
        factory="account",
        office_phone="+17705753103",
        vertical="chiropractic",
        period="t30",
    )
    df = response.to_dataframe()
```

### From Business Model

```python
from autom8_asana.clients.data import DataServiceClient
from autom8_asana.models import Business

async with DataServiceClient() as data_client:
    business = await Business.from_gid_async(asana_client, gid)
    insights = await business.get_insights_async(
        data_client,
        factory="account",
        period="t30",
    )
```

### Batch Requests

```python
from autom8_asana.clients.data import DataServiceClient
from autom8_asana.models.contracts import PhoneVerticalPair

pairs = [
    PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic"),
    PhoneVerticalPair(office_phone="+14155551234", vertical="dental"),
]

async with DataServiceClient() as client:
    batch = await client.get_insights_batch_async(
        pairs,
        factory="account",
        period="t30",
    )

    print(f"Success: {batch.success_count}/{batch.total_count}")

    # Combined DataFrame with _pvp_key column for grouping
    df = batch.to_dataframe()
```

## Error Handling

The client raises specific exceptions for different error conditions:

```python
from autom8_asana.clients.data import DataServiceClient
from autom8_asana.exceptions import (
    InsightsValidationError,
    InsightsNotFoundError,
    InsightsServiceError,
)

async with DataServiceClient() as client:
    try:
        response = await client.get_insights_async(
            factory="account",
            office_phone="+17705753103",
            vertical="chiropractic",
        )
    except InsightsValidationError as e:
        # Invalid inputs (bad factory, phone format, period, etc.)
        print(f"Validation error: {e.message}")
        print(f"Field: {e.field}")
    except InsightsNotFoundError as e:
        # No data for the phone/vertical combination
        print(f"Not found: {e.message}")
        print(f"Request ID: {e.request_id}")
    except InsightsServiceError as e:
        # Upstream service failure (timeout, 5xx, circuit breaker)
        print(f"Service error: {e.message}")
        print(f"Reason: {e.reason}")  # timeout, circuit_breaker, server_error
        print(f"Request ID: {e.request_id}")
```

### Exception Hierarchy

```
InsightsError (base)
├── InsightsValidationError  # 400-level errors
├── InsightsNotFoundError    # 404 errors
└── InsightsServiceError     # 500-level errors, timeouts, circuit breaker
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTOM8_DATA_BASE_URL` | Base URL for autom8_data service | `https://data.autom8.io` |
| `AUTOM8_DATA_API_KEY` | JWT token for S2S authentication | None |
| `AUTOM8_DATA_INSIGHTS_ENABLED` | Emergency kill switch (see below) | `true` |

### Emergency Kill Switch

The `AUTOM8_DATA_INSIGHTS_ENABLED` environment variable serves as an **emergency kill switch** for the insights integration. This is NOT intended for A/B testing or gradual rollout - it exists solely for emergency disable scenarios.

**When to use:**
- Service causing widespread failures or degradation
- Critical bug discovered in production
- Upstream autom8_data service experiencing prolonged outage
- Need to disable without deploying new code

**How to disable:**
```bash
export AUTOM8_DATA_INSIGHTS_ENABLED=false
```

Valid disable values: `false`, `0`, `no` (case-insensitive)

**Behavior when disabled:**
- All insights methods raise `InsightsServiceError` with `reason="feature_disabled"`
- Error message explains how to re-enable
- No HTTP requests are made to autom8_data

**Re-enabling:**
```bash
unset AUTOM8_DATA_INSIGHTS_ENABLED
# or
export AUTOM8_DATA_INSIGHTS_ENABLED=true
```

**Note:** Under normal operation, this flag should not be set. The integration is stable and has been validated with comprehensive testing (485 client tests, P95 < 2ms overhead).

### Programmatic Configuration

```python
from autom8_asana.clients.data import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig

config = DataServiceConfig(
    base_url="https://data.autom8.io",
    token_key="AUTOM8_DATA_API_KEY",
    cache_ttl=300,  # 5 minutes
)

client = DataServiceClient(config=config)
```

### Timeout Configuration

```python
from autom8_asana.clients.data.config import DataServiceConfig, TimeoutConfig

config = DataServiceConfig(
    timeout=TimeoutConfig(
        connect=5.0,   # Connection timeout (seconds)
        read=30.0,     # Read timeout (seconds)
        write=10.0,    # Write timeout (seconds)
        pool=5.0,      # Pool timeout (seconds)
    )
)
```

### Cache Provider

For resilience, configure a cache provider for stale fallback on service failures:

```python
from autom8_asana.clients.data import DataServiceClient

client = DataServiceClient(
    cache_provider=my_cache,  # Must implement CacheProvider protocol
)

# On service failure, client returns stale cached data with:
# - response.metadata.is_stale = True
# - response.metadata.cached_at = datetime when originally cached
# - Warning message in response.warnings
```

### Metrics Hook

Integrate with your observability stack:

```python
def emit_metric(name: str, value: float, tags: dict[str, str]) -> None:
    # Send to Prometheus, DataDog, CloudWatch, etc.
    statsd.gauge(name, value, tags=tags)

client = DataServiceClient(metrics_hook=emit_metric)

# Emitted metrics:
# - insights_request_total (counter)
# - insights_request_latency_ms (histogram)
# - insights_request_error_total (counter)
# - insights_batch_total (counter)
# - insights_batch_size (gauge)
```

## Valid Factory Names

The client supports 14 factory types:

| Factory | Description |
|---------|-------------|
| `account` | Aggregated account metrics |
| `ads` | Individual ad performance |
| `adsets` | Ad set level metrics |
| `campaigns` | Campaign level metrics |
| `spend` | Spend breakdown |
| `leads` | Lead generation metrics |
| `appts` | Appointment metrics |
| `assets` | Creative asset metrics |
| `targeting` | Audience targeting metrics |
| `payments` | Payment/billing metrics |
| `business_offers` | Offer metrics |
| `ad_questions` | Ad question responses |
| `ad_tests` | A/B test results |
| `base` | Base/raw metrics |

## Valid Period Values

| Period | Description |
|--------|-------------|
| `lifetime` | All time (default) |
| `t30` | Trailing 30 days |
| `t7` | Trailing 7 days |
| `l7` | Last 7 days |
| `l30` | Last 30 days |
| `day`, `week`, `month`, `quarter`, `year` | Calendar periods |

## Response Structure

```python
response = await client.get_insights_async(...)

# Access raw data
response.data  # list[dict[str, Any]]

# Metadata
response.metadata.factory      # "account"
response.metadata.row_count    # 100
response.metadata.column_count # 10
response.metadata.cache_hit    # True/False
response.metadata.is_stale     # True if served from stale cache
response.metadata.cached_at    # datetime if stale

# Request tracing
response.request_id  # UUID for correlation

# Warnings
response.warnings  # list[str] of any warnings

# DataFrame conversion
df = response.to_dataframe()  # Polars DataFrame with correct dtypes
pdf = response.to_pandas()    # pandas DataFrame
```

## Circuit Breaker

The client includes a circuit breaker to prevent cascade failures:

```python
async with DataServiceClient() as client:
    # Monitor circuit state
    print(f"Circuit state: {client.circuit_breaker.state}")
    print(f"Failure count: {client.circuit_breaker.failure_count}")

    # When circuit opens, requests fail fast with InsightsServiceError
    # with reason="circuit_breaker"
```

## Retry Behavior

The client automatically retries transient failures:

- **Retryable status codes**: 429, 502, 503, 504
- **Retries on**: Timeout errors
- **Max retries**: 2 (configurable)
- **Backoff**: Exponential (1s, 2s)
- **Honors**: `Retry-After` header for 429 responses
- **Does NOT retry**: 4xx client errors (except 429)
