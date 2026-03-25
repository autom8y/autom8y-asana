---
domain: feat/data-service-client
generated_at: "2026-03-18T12:39:28Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/clients/data/**/*.py"
  - "./src/autom8_asana/automation/workflows/insights_export.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "2c604fa"
confidence: 0.90
format_version: "1.0"
---

# autom8_data Satellite Service Client (Ad Performance Insights)

## Purpose and Design Rationale

### Problem This Feature Solves

`autom8_data` is a satellite microservice in the autom8y platform that provides ad campaign analytics -- spend, leads, appointments, campaign metrics, reconciliation data -- for businesses identified by phone number and vertical. `autom8_asana` is the primary Asana-facing SDK; it needs to surface those analytics inside Asana Offer tasks (as HTML report attachments) and within cross-service query joins. The `DataServiceClient` is the sole integration point for that satellite service.

Without this feature, the Asana automation layer would have no access to ad performance data. The feature solves the problem of reliably fetching analytics from an external microservice with production-grade resilience: circuit breaking, retry, stale-cache fallback, PII redaction in logs, and an emergency kill switch.

### Design Decisions and ADRs

| Reference | Decision |
|-----------|----------|
| TDD-INSIGHTS-001 | Primary TDD document. Specifies FR-001 through FR-006: config via env vars, async context manager protocol, per-factory endpoint, batch mode, DataFrame conversion, timeout hierarchy. |
| ADR-INS-002 | Response format: JSON with `dtype` metadata (Arrow format deferred). Column types travel in `metadata.columns[]` so the client can reconstruct Polars dtypes without schema negotiation. |
| ADR-INS-004 | Client-side insight caching with stale fallback. On 5xx failure: return cached response with `is_stale=True`. Default TTL 300s. |
| ADR-INS-005 | Circuit breaker composed from transport layer `CircuitBreaker` (from `autom8y_http`), not home-grown. |
| ADR-0028 | Polars is the primary DataFrame library; `to_dataframe()` returns `pl.DataFrame`. `to_pandas()` is a compatibility shim. |
| ADR-DSC-005 | Retry callbacks are built at call-site (not injected into the client), enabling per-request parameterization. |
| B4 Config Consolidation audit | `DataServiceConfig` subclasses intentionally do NOT inherit from the main `autom8_asana.config` equivalents. The data-service has smaller connection pools, fewer retries, 502 in retryable codes, and circuit breaker enabled by default. Unifying would silently change defaults for callers who rely on partial overrides. |

### Alternatives Rejected

- **Apache Arrow over the wire**: Deferred (ADR-INS-002). JSON + dtype metadata was chosen for simplicity and HTTP/1.1 compatibility. Arrow can be added later without changing the public API.
- **Unified config classes with `autom8_asana.config`**: Explicitly rejected (B4 audit). Separate classes preserve domain-specific defaults.
- **Re-using `BaseClient`**: Not used. `DataServiceClient` is a standalone class; it wraps `Autom8yHttpClient` (platform SDK) directly rather than inheriting from the Asana `BaseClient`. This is correct because `BaseClient` is an Asana resource client abstraction.

### Tradeoffs Accepted

- Stale cache fallback can serve up to TTL-old data during outages. This is preferable to surfacing errors in automated workflows that run on a schedule.
- The `max_batch_size` cap of 500 (server accepts up to 1000) exists because `DataServiceJoinFetcher` relies on no pre-chunking. Lowering this value requires adding chunking to the fetcher (documented at `src/autom8_asana/clients/data/config.py` line 256).
- Period normalization loses granularity: many client-side period strings (e.g., `t90`, `t180`) fall through to the `T30` default. This is an intentional backward-compat decision, not a bug.

---

## Conceptual Model

### Core Terminology

| Term | Meaning |
|------|---------|
| **Factory** | autom8_data's name for a data query type. Equivalent to "report type". Maps to a `frame_type` in the wire format. 14 factories exist (account, ads, adsets, campaigns, spend, leads, appts, assets, targeting, payments, business_offers, ad_questions, ad_tests, base). |
| **PVP** | `PhoneVerticalPair` -- the identity key for a business at autom8_data. A business is identified by its E.164 `office_phone` and `vertical` (e.g., "chiropractic"). |
| **canonical_key** | String key derived from PVP: `pv1:{office_phone}:{vertical}`. Used as dict keys in batch responses and as part of cache keys. |
| **period** | Time window for the query. Client-side values (e.g., `t30`, `lifetime`) are normalized to autom8_data uppercase format (`T30`, `LIFETIME`) before transmission. |
| **frame_type** | autom8_data's internal name for a factory. `FACTORY_TO_FRAME_TYPE` maps client factory names to wire frame_types (e.g., `"account"` -> `"ACCOUNT_PERFORMANCE"`). |
| **stale response** | Cached response returned when live fetch fails (5xx or timeout). Flagged with `is_stale=True` in `InsightsMetadata`. |
| **kill switch** | `AUTOM8Y_DATA_INSIGHTS_ENABLED` env var. When set to `false`/`0`/`no`, all insights methods raise `InsightsServiceError(reason="feature_disabled")` without making HTTP requests. |
| **request descriptor** | Frozen dataclass (`InsightsRequestDescriptor`, `BatchRequestDescriptor`, etc.) that bundles path, body, retry callbacks, and metadata for one HTTP call. Passed to `DefaultEndpointPolicy.execute()`. |
| **endpoint policy** | `DefaultEndpointPolicy` -- a generic class that owns the 8-step execution scaffold (S1-S8): pre-flight, circuit breaker check, client acquisition, request build, retry execution, elapsed time, error path, success path. |

### Key Abstractions

```
DataServiceClient
  ├── holds DataServiceConfig (frozen config dataclasses)
  ├── holds CircuitBreaker (from autom8y_http)
  ├── holds ExponentialBackoffRetry (from autom8y_http)
  ├── holds Autom8yHttpClient (lazy, created on first request)
  ├── holds CacheProvider | None
  ├── holds MetricsHook | None
  ├── holds AuthProvider | None
  └── dispatches via DefaultEndpointPolicy(...)
        └── delegates to _endpoints/{insights, batch, export, simple, reconciliation}.py
```

### Execution Scaffold (S1-S8)

Every endpoint follows the same 8-step pattern:

1. **S1 Pre-flight**: feature check, input validation, PII masking, logging, build request body.
2. **S2 Circuit breaker check**: fast-fail if open.
3. **S3 Acquire HTTP client**: lazy init via `_get_client()`.
4. **S4 Build request callable**: lambda wrapping `http_client.post/get(...)`.
5. **S5 Execute with retry**: `_execute_with_retry()` handles status-code retries and exponential backoff.
6. **S6 Error path**: status >= 400 -> `error_handler` -> raises domain exception or returns stale cache.
7. **S7-S8 Success path**: `success_handler` -> parse, record CB success, cache, emit metrics.

Steps S2-S8 are encapsulated in `DefaultEndpointPolicy`. Endpoint modules (`_endpoints/*.py`) provide pluggable behavior functions (`_cb_error_factory`, `_request_builder`, `_error_handler`, `_success_handler`).

### State Machine (Circuit Breaker)

```
CLOSED -> (5 failures in 60s) -> OPEN -> (30s recovery_timeout) -> HALF-OPEN -> (1 success) -> CLOSED
                                   |
                              fast-fail all requests
                              InsightsServiceError(reason="circuit_breaker")
```

### Relationship to Other Features

- **`InsightsExportWorkflow`** (`src/autom8_asana/automation/workflows/insights_export.py`): Consumes all 5 endpoint types (insights, batch not used here, appointments, leads, reconciliation) to build 12-table HTML reports uploaded as Asana attachments.
- **`DataServiceJoinFetcher`** (`src/autom8_asana/query/fetcher.py`): Uses `get_insights_batch_async()` to enrich entity query results with ad performance data (cross-service join).
- **`QueryEngine`** / **`JoinSpec`**: Extended with `source="data-service"`, `factory`, and `period` fields to route joins through `DataServiceJoinFetcher`.
- **`PhoneVerticalPair`** (`src/autom8_asana/models/contracts.py`): The PVP model used everywhere as the business identity key.
- **`CacheProvider` protocol** (`src/autom8_asana/protocols/cache.py`): Optional injection; the client uses `.set()` and `.get()` methods only.

---

## Implementation Map

### Package Structure

```
src/autom8_asana/clients/data/
├── __init__.py           # Public API re-exports
├── client.py             # DataServiceClient class (entry point)
├── config.py             # DataServiceConfig + sub-configs (frozen dataclasses)
├── models.py             # InsightsRequest, InsightsResponse, BatchInsightsResponse, ExportResult
├── _policy.py            # DefaultEndpointPolicy + request descriptors (private)
├── _cache.py             # build_cache_key, cache_response, get_stale_response (private)
├── _metrics.py           # emit_metric function (private)
├── _normalize.py         # normalize_period: client period -> autom8_data period (private)
├── _pii.py               # mask_phone_number, mask_canonical_key, mask_pii_in_string (private)
├── _response.py          # validate_factory, handle_error_response, parse_success_response (private)
├── _retry.py             # RetryCallbacks dataclass + build_retry_callbacks factory (private)
└── _endpoints/
    ├── __init__.py
    ├── insights.py        # execute_insights_request (POST /data-service/insights, single PVP)
    ├── batch.py           # execute_batch_request, build_entity_response (POST /data-service/insights, multi-PVP)
    ├── export.py          # get_export_csv (GET /messages/export)
    ├── simple.py          # get_appointments, get_leads (GET /appointments, /leads)
    └── reconciliation.py  # get_reconciliation (POST /insights/reconciliation/execute)
```

### Key Types

| Type | File | Role |
|------|------|------|
| `DataServiceClient` | `client.py` | Primary entry point. Context manager. Owns all state. |
| `DataServiceConfig` | `config.py` | Root config. `base_url`, `token_key`, timeout, pool, retry, circuit breaker, `cache_ttl`, `max_batch_size`. |
| `TimeoutConfig` | `config.py` | connect=5s, read=30s, write=30s, pool=5s |
| `RetryConfig` | `config.py` | max_retries=2, base_delay=1s, retryable={429,502,503,504} |
| `CircuitBreakerConfig` | `config.py` | enabled=True, failure_threshold=5, recovery_timeout=30s |
| `InsightsRequest` | `models.py` | Pydantic model for single-PVP request body |
| `InsightsResponse` | `models.py` | Response with `data`, `metadata`, `request_id`, `warnings`. Has `to_dataframe()`, `to_pandas()` |
| `InsightsMetadata` | `models.py` | Row/column counts, `cache_hit`, `is_stale`, `cached_at`, `sort_history` |
| `ColumnInfo` | `models.py` | `name`, `dtype`, `nullable` for DataFrame reconstruction |
| `BatchInsightsResponse` | `models.py` | `results: dict[str, BatchInsightsResult]`, success/failure counts, `to_dataframe()` |
| `BatchInsightsResult` | `models.py` | Per-PVP result with `pvp`, `response | None`, `error | None`, `success` computed field |
| `ExportResult` | `models.py` | Plain dataclass: `csv_content: bytes`, `row_count`, `truncated`, `office_phone`, `filename` |
| `DefaultEndpointPolicy[T, R]` | `_policy.py` | Generic execution scaffold S2-S8 |
| `RetryCallbacks` | `_retry.py` | Frozen dataclass: `on_retry`, `on_timeout_exhausted`, `on_http_error` |

### Public API Surface (`__all__` from `__init__.py`)

```python
from autom8_asana.clients.data import DataServiceClient
from autom8_asana.clients.data import (
    DataServiceConfig, TimeoutConfig, ConnectionPoolConfig, RetryConfig, CircuitBreakerConfig
)
from autom8_asana.clients.data import (
    InsightsRequest, InsightsResponse, InsightsMetadata, ColumnInfo,
    BatchInsightsResponse, BatchInsightsResult, ExportResult
)
```

### Primary Entry Point Methods on `DataServiceClient`

```python
# Insights (single PVP)
async def get_insights_async(self, *, factory: str, office_phone: str, vertical: str,
    period: str = "lifetime", start_date=None, end_date=None, metrics=None,
    dimensions=None, groups=None, break_down=None, refresh=False,
    include_unused=False) -> InsightsResponse

def get_insights(self, **kwargs) -> InsightsResponse  # sync wrapper

# Batch (multiple PVPs)
async def get_insights_batch_async(self, pairs: list[PhoneVerticalPair], *,
    factory: str, period: str = "lifetime", refresh: bool = False) -> BatchInsightsResponse

# Export (conversation CSV)
async def get_export_csv_async(self, office_phone: str, *,
    start_date=None, end_date=None) -> ExportResult

# Appointments
async def get_appointments_async(self, office_phone: str, *,
    days: int, limit: int) -> InsightsResponse

# Leads
async def get_leads_async(self, office_phone: str, *,
    days: int, exclude_appointments: bool, limit: int) -> InsightsResponse

# Reconciliation
async def get_reconciliation_async(self, office_phone: str, vertical: str, *,
    period=None, window_days=None) -> InsightsResponse
```

### Wire Protocol

- **Insights / Batch**: `POST /api/v1/data-service/insights`
  - Body: `{ "frame_type": str, "phone_vertical_pairs": [...], "period": str, ... }`
  - Response: `{ "data": [...], "metadata": {...}, "warnings": [...] }`
  - Partial success (batch): HTTP 207 with `{ "data": [...], "errors": [...] }`
- **Export**: `GET /api/v1/messages/export?office_phone=...&start_date=...&end_date=...`
  - Response: `text/csv` body, row count in `X-Export-Row-Count`, `X-Export-Truncated` header.
- **Appointments**: `GET /api/v1/appointments?office_phone=...&days=...&limit=...`
- **Leads**: `GET /api/v1/leads?office_phone=...&days=...&limit=...`
- **Reconciliation**: `POST /api/v1/insights/reconciliation/execute`
  - Body: `{ "business": office_phone, "vertical": str, "period"?: str, "window_days"?: int }`

### FACTORY_TO_FRAME_TYPE Mapping

14 mappings in `DataServiceClient.FACTORY_TO_FRAME_TYPE`:

```python
"account"         -> "ACCOUNT_PERFORMANCE"
"ads"             -> "ADS_PERFORMANCE"
"adsets"          -> "ADSETS_PERFORMANCE"
"campaigns"       -> "CAMPAIGNS_PERFORMANCE"
"spend"           -> "SPEND_BREAKDOWN"
"leads"           -> "LEADS_METRICS"
"appts"           -> "APPOINTMENTS_METRICS"
"assets"          -> "ASSETS_PERFORMANCE"
"targeting"       -> "TARGETING_METRICS"
"payments"        -> "PAYMENTS_METRICS"
"business_offers" -> "BUSINESS_OFFERS"
"ad_questions"    -> "AD_QUESTIONS"
"ad_tests"        -> "AD_TESTS"
"base"            -> "BASE_METRICS"
```

### Data Flow

```
Caller (InsightsExportWorkflow / DataServiceJoinFetcher)
    |
    v
DataServiceClient.get_insights_async(factory, office_phone, vertical, period)
    |
    +- _check_feature_enabled() -> raises InsightsServiceError(reason="feature_disabled") if kill switch set
    +- _validate_factory() -> raises InsightsValidationError if factory not in VALID_FACTORIES
    +- build InsightsRequest (Pydantic), build cache_key
    +- check cache hit (CacheProvider.get) -> return cached InsightsResponse if fresh
    |
    +- execute_insights_request(client, factory, request, request_id, cache_key)
          |
          +- DefaultEndpointPolicy.execute(InsightsRequestDescriptor)
                +- S2: circuit_breaker.check() -> InsightsServiceError(reason="circuit_breaker") if open
                +- S3: _get_client() -> lazy init Autom8yHttpClient (once)
                +- S4-S5: _execute_with_retry(POST /api/v1/data-service/insights, ...)
                |     +- on_retry: log + record CB
                |     +- on_timeout_exhausted: emit metric, record CB failure, raise
                |     +- on_http_error: emit metric, record CB failure, raise
                +- S6 (status >= 400): handle_error_response()
                |     +- 400 -> InsightsValidationError (no stale fallback)
                |     +- 404 -> InsightsNotFoundError (no stale fallback)
                |     +- 5xx -> record CB failure, try stale cache, raise InsightsServiceError if miss
                +- S7-S8 (success): parse_success_response()
                      +- record CB success
                      +- cache_response(cache_key, response, TTL)
                      +- emit metrics (total, latency)
```

### Test Coverage

Tests are primarily in `tests/unit/query/test_data_service_join.py` (covers `DataServiceJoinFetcher`, `JoinSpec` extensions, virtual entity registry). No dedicated unit test directory was found under `tests/unit/clients/data/`. The README references "485 client tests, P95 < 2ms overhead" but dedicated test files were not located in the `tests/` tree under `clients/` paths matching the search pattern.

---

## Boundaries and Failure Modes

### Scope Limitations

- `DataServiceClient` does **not** handle Asana API calls. It is an isolated satellite client.
- Batch requests are limited to 500 PVPs by default (`max_batch_size=500`). The server accepts up to 1000. Lowering this below 500 requires adding chunking to `DataServiceJoinFetcher` (see `config.py:256`).
- `ExportResult.csv_content` is raw bytes (UTF-8 with BOM). The client does not parse CSV; callers pass bytes directly to `AttachmentsClient.upload_async()`.
- Export endpoint has a server-side 10K row cap. Check `ExportResult.truncated == True` to detect this.
- Reconciliation data may contain rows from multiple businesses when upstream returns cross-business data. `InsightsExportWorkflow` applies phone filtering in `_fetch_table()` (D-02 decision).

### Error Hierarchy

```
InsightsError (base)
├── InsightsValidationError  # 400 -- invalid factory, bad phone format, bad period, etc.
│   attrs: field (str), request_id (str)
├── InsightsNotFoundError    # 404 -- no data for this phone/vertical
│   attrs: request_id (str)
├── InsightsServiceError     # 5xx, timeout, circuit breaker
│   attrs: request_id (str), reason (str), status_code (int | None)
│   reasons: "server_error", "timeout", "circuit_breaker", "http_error", "feature_disabled", "parse_error"
ExportError                  # all export endpoint errors
SyncInAsyncContextError      # sync method called from async context
```

**Important**: `InsightsValidationError` and `InsightsNotFoundError` do NOT trigger stale cache fallback. Only `InsightsServiceError` does.

### Edge Cases and Known Pitfalls

**Period normalization loss**: Periods `t90`, `t180`, `t365`, `l24h`, etc. are not mapped and fall through to `T30` default. This is silent -- no warning is logged. Agents adding new period types must extend `_normalize.py`.

**Batch partial failure (HTTP 207)**: `BatchInsightsResponse.results` contains a mix of succeeded and failed entries. Callers must check `result.success` per entry. The failure of one PVP does not raise an exception.

**Batch circuit breaker behavior differs from single**: When the circuit breaker is open, single-PVP calls raise `InsightsServiceError`. Batch calls return a `BatchInsightsResponse` where every PVP has `error=circuit_breaker_message` -- no exception is raised.

**Auth failure (SCAR-012)**: If `AUTOM8Y_DATA_API_KEY` env var is unset and no `auth_provider` is injected, requests will fail authentication. Use `ServiceTokenAuthProvider` from `src/autom8_asana/auth/service_token.py`. Never pass raw API keys as Bearer tokens.

**Sync context manager**: `DataServiceClient.__enter__` and `__exit__` run the async `close()` via `_run_sync()`. If called from an async context (any running event loop detected), `SyncInAsyncContextError` is raised. Always use `async with` in async code.

**HTTP client double-policy**: `_get_client()` builds `Autom8yHttpClient` with `enable_circuit_breaker=False` to avoid double-applying policies. The client's own `CircuitBreaker` and `ExponentialBackoffRetry` instances manage resilience.

**Cache serialization**: `_cache.py:cache_response` serializes `InsightsResponse` via `model_dump(mode="json")`. Cache failures are swallowed (logged as warning). Stale reconstruction from cache rebuilds the full Pydantic model from dict, including `ColumnInfo` objects.

**PII redaction contract (XR-003)**: Phone numbers are masked (`+17705753103` -> `+1770***3103`) before logging and in all error messages. `mask_pii_in_string` applies to any freeform string that could echo upstream PII. Agents must not log `office_phone` raw.

### Configuration Boundaries

| Env Var | Read By | Default | Notes |
|---------|---------|---------|-------|
| `AUTOM8Y_DATA_BASE_URL` | README; actual var is `AUTOM8Y_DATA_URL` in config | `http://localhost:8000` (from settings) | Production should be `https://data.autom8.io` |
| `AUTOM8Y_DATA_API_KEY` | `config.token_key` | None | Token is resolved via `resolve_secret_from_env` or `auth_provider.get_secret` |
| `AUTOM8Y_DATA_INSIGHTS_ENABLED` | `_check_feature_enabled()` | `true` | Kill switch. `false`/`0`/`no` disables all methods |
| `AUTOM8Y_DATA_CACHE_TTL` | `DataServiceConfig.from_env()` | 300 | Seconds |

### Interaction Points with External Systems

1. **`autom8y_http`** (platform SDK): Provides `Autom8yHttpClient`, `CircuitBreaker`, `ExponentialBackoffRetry`, `HTTPError`, `TimeoutException`, `CircuitBreakerOpenError`.
2. **`autom8y_config.lambda_extension`**: `resolve_secret_from_env` for API key lookup.
3. **`autom8y_log`**: Structured logger via `get_logger(__name__)`.
4. **`autom8y_telemetry`**: `trace_computation` (imported in `client.py`).
5. **`CacheProvider` protocol**: Optional external cache (Redis in production, in-memory in tests).
6. **`AuthProvider` (optional)**: `ServiceTokenAuthProvider` in production. If absent, falls back to `resolve_secret_from_env`.

### Known Test Gaps

- No dedicated test directory found for `tests/unit/clients/data/`. The README claims 485 client tests, but these were not located via glob search. They may exist under a path not matched by the `*data*` glob or may have been removed/reorganized.
- `DataServiceJoinFetcher` tests are in `tests/unit/query/test_data_service_join.py` -- this covers the integration seam but not the HTTP execution paths.
- Stale cache reconstruction path (`get_stale_response` in `_cache.py`) is exercised through integration but the standalone unit test presence is unconfirmed.

---

## Knowledge Gaps

1. **Test file location**: The README claims 485 client tests with P95 < 2ms overhead. These tests were not found under `tests/unit/clients/data/` or matching the `*data*` glob. The test suite may be organized differently (possibly under an integration directory) or may have been deleted during a refactor. Agents should search `tests/` more broadly before concluding coverage is absent.

2. **`trace_computation` usage**: `autom8y_telemetry.trace_computation` is imported in `client.py` but was not observed in the method stubs extracted. It may be used as a decorator on `get_insights_async` or other methods in the full file body. The distributed tracing integration path is unknown.

3. **`AUTOM8Y_DATA_BASE_URL` vs `AUTOM8Y_DATA_URL`**: The README documents `AUTOM8Y_DATA_BASE_URL`; `config.py` uses `get_settings().data_service.url` which likely reads `AUTOM8Y_DATA_URL`. The mapping from env var name to settings field is not directly observable without reading `src/autom8_asana/settings.py`.

4. **Batch chunking behavior**: `get_insights_batch_async` splits pairs into chunks of `max_batch_size` (500) and executes concurrently. The chunking logic and chunk-level error aggregation is in `client.py` but was not fully traced. The exact behavior when one chunk fails while others succeed may not be symmetric.

5. **Virtual entity registry**: `DataServiceJoinFetcher` uses `DATA_SERVICE_ENTITIES` from `src/autom8_asana/query/data_service_entities.py` -- not read. This file defines which factory/period combinations are available as virtual entities in the query system.
