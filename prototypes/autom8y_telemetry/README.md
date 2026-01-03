# autom8y-telemetry POC

**Status**: Prototype demonstrating feasibility
**Time-box**: 3-day equivalent (compressed to single session)
**Decision**: Go/No-go for production implementation

## What Was Built

A minimal working prototype demonstrating platform-level observability primitives:

1. **TokenBucketRateLimiter**: Extracted from autom8_asana, decoupled from SDK dependencies
2. **Protocol definitions**: `RateLimiterProtocol`, `TelemetryHookProtocol`, `LogProviderProtocol`
3. **OpenTelemetry wrapper**: One-line initialization (`init_telemetry()`)
4. **Instrumented HTTP client**: Auto-generates spans for requests
5. **Structlog processor**: Injects trace_id/span_id into logs

## Quick Start

### Run the Demo

```bash
# Install dependencies (if not already installed)
pip install opentelemetry-api opentelemetry-sdk httpx

# Run demo script
python prototypes/autom8y_telemetry/demo.py
```

The demo shows end-to-end integration:
1. Telemetry initialization
2. Rate limiter creation
3. Instrumented HTTP request
4. Console span output

### Code Example

```python
# Initialize telemetry (one-line setup)
from autom8y_telemetry import init_telemetry
init_telemetry("my-service")

# Use instrumented HTTP client
from autom8y_telemetry import TelemetryHTTPClient, TokenBucketRateLimiter

rate_limiter = TokenBucketRateLimiter(max_tokens=100, refill_period=60.0)

async with TelemetryHTTPClient(rate_limiter=rate_limiter) as client:
    response = await client.get("https://api.example.com/data")
    # Automatically creates span: "HTTP GET"
    # Records: method, url, status_code, duration_ms
```

## Usage Examples

### Example 1: Rate Limiter (Standalone)

```python
from autom8y_telemetry import TokenBucketRateLimiter

# Create rate limiter: 1500 requests per 60 seconds
limiter = TokenBucketRateLimiter(
    max_tokens=1500,
    refill_period=60.0,
)

# Acquire token before API call
await limiter.acquire()

# Check stats
stats = limiter.get_stats()
print(f"Available: {stats['available_tokens']}")
print(f"Utilization: {stats['utilization']:.1%}")
```

### Example 2: OpenTelemetry Integration

```python
from autom8y_telemetry import init_telemetry, start_span

# One-line setup
init_telemetry("autom8_asana")

# Create spans
with start_span("fetch_insights") as span:
    span.set_attribute("factory", "account")
    span.set_attribute("pvp_key", "pv1:+1234567890:chiropractic")

    # Nested span
    with start_span("http_request"):
        response = await client.post("/api/v1/factory/account", json=payload)

    span.set_attribute("row_count", len(response.json()["data"]))
```

### Example 3: Structlog + OTel (Log/Trace Correlation)

```python
import structlog
from autom8y_telemetry import init_telemetry, add_otel_trace_ids, start_span

# Configure structlog with OTel processor
structlog.configure(
    processors=[
        add_otel_trace_ids,  # Injects trace_id/span_id
        structlog.processors.JSONRenderer(),
    ]
)

# Initialize telemetry
init_telemetry("autom8_asana")

# Logs will include trace_id when inside span
log = structlog.get_logger()

with start_span("process_batch"):
    log.info("batch_started", batch_size=100)
    # Output: {"event": "batch_started", "batch_size": 100, "trace_id": "...", "span_id": "..."}
```

### Example 4: Instrumented HTTP Client

```python
from autom8y_telemetry import (
    init_telemetry,
    TelemetryHTTPClient,
    TokenBucketRateLimiter,
)

# Setup
init_telemetry("autom8_asana")
rate_limiter = TokenBucketRateLimiter(max_tokens=100, refill_period=60.0)

# Use context manager for resource cleanup
async with TelemetryHTTPClient(
    rate_limiter=rate_limiter,
    base_url="https://api.example.com",
) as client:
    # GET request (auto-instrumented)
    response = await client.get("/data")

    # POST request (auto-instrumented)
    response = await client.post("/data", json={"key": "value"})

    # Spans automatically include:
    # - http.method
    # - http.url
    # - http.status_code
    # - http.duration_ms
    # - http.response_content_length
```

## Documented Shortcuts

This is prototype code - the following shortcuts were taken for speed:

### 1. Console Exporter Only
- **Shortcut**: Uses `ConsoleSpanExporter` (prints to stdout)
- **Production**: Would use OTLP exporter for sending to collector/backend
- **Impact**: Traces visible locally but not aggregated/queryable

### 2. Hardcoded Configuration
- **Shortcut**: No environment variable configuration
- **Production**: Would support `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, etc.
- **Impact**: Not configurable without code changes

### 3. No Retry/Circuit Breaker Integration
- **Shortcut**: `TelemetryHTTPClient` doesn't integrate with retry/circuit breaker
- **Production**: Would instrument retry loops and circuit breaker state changes
- **Impact**: Missing visibility into resilience patterns

### 4. Minimal Error Handling
- **Shortcut**: Errors raise immediately without graceful degradation
- **Production**: Would handle telemetry failures silently (no impact on business logic)
- **Impact**: Telemetry failures could break requests

### 5. Single Test Per Component
- **Shortcut**: Only basic happy-path tests
- **Production**: Would have comprehensive test coverage (edge cases, error paths)
- **Impact**: No confidence in error scenarios

### 6. No Resource Attributes
- **Shortcut**: Only sets `service.name` on traces
- **Production**: Would include `service.version`, `deployment.environment`, etc.
- **Impact**: Limited trace filtering/grouping

### 7. Generic Exceptions
- **Shortcut**: Uses `RuntimeError` instead of custom exception types
- **Production**: Would use `ConfigurationError`, `TelemetryError`, etc.
- **Impact**: Less specific error messages

## Performance Measurement

### Latency Overhead

**Not measured in POC** - would require:
1. Baseline: HTTP request without instrumentation
2. Instrumented: Same request with span creation
3. Calculate overhead: `(instrumented - baseline) / baseline * 100%`

**Expected overhead**: <5ms per request (based on OTel benchmarks)

## Success Criteria

- [x] TokenBucketRateLimiter works standalone (no autom8_asana imports)
- [x] Single HTTP request generates valid OTel span
- [x] Logs include trace_id when in span context
- [x] Type checker would pass with protocols (structure correct)
- [x] README shows working usage example

## What Didn't Work

**No major blockers encountered.**

Minor issues:
1. OpenTelemetry SDK has verbose initialization - wrapper helps
2. Console exporter output is noisy - OTLP would batch/export cleanly
3. Protocol runtime checking requires `@runtime_checkable` decorator

## Recommendation: PROCEED TO PRODUCTION

**Reasoning:**
1. Extraction pattern works - no autom8_asana dependencies in primitives
2. OTel integration is straightforward (thin wrapper)
3. Protocol-based design enables flexible composition
4. Rate limiter + HTTP client demonstrate real integration
5. No technical blockers discovered

**Estimated production effort:** 4-5 weeks (as per Integration Researcher)

**Next steps:**
1. Create `autom8y_telemetry` package skeleton
2. Implement OTLP exporter configuration
3. Add comprehensive test suite
4. Integrate with autom8_asana retry/circuit breaker
5. Add metrics hooks (Prometheus/DataDog/CloudWatch)

## Files Created

```
prototypes/autom8y_telemetry/
├── __init__.py                  # Public API exports
├── protocols.py                 # Protocol definitions
├── rate_limiter.py             # TokenBucketRateLimiter (extracted)
├── telemetry.py                # OTel initialization wrapper
├── http_client.py              # Instrumented HTTP client
├── structlog_processor.py      # Trace ID injection for structlog
├── demo.py                     # End-to-end demo script
├── README.md                   # This file
└── tests/
    └── test_rate_limiter.py    # Basic test coverage (archived)

# Working test suite
prototypes/test_autom8y_telemetry_poc.py  # 4 tests passing
```

## Dependencies

**Required for POC:**
- `opentelemetry-api` (core OTel API)
- `opentelemetry-sdk` (SDK implementation)
- `httpx` (async HTTP client)
- `structlog` (structured logging, optional for processor)

**Production additions:**
- `opentelemetry-exporter-otlp` (OTLP exporter)
- `opentelemetry-instrumentation-httpx` (upstream httpx instrumentation)
- Additional exporters as needed (Prometheus, Jaeger, etc.)
