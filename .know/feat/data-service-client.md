---
domain: feat/data-service-client
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/clients/data/"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.97
format_version: "1.0"
---

# autom8_data Satellite Service Client

## Purpose and Design Rationale

Cross-service HTTP client connecting `autom8_asana` to the `autom8_data` satellite service. Retrieves ad performance analytics (campaigns, spend, leads, appointments, assets, reconciliation) keyed by `PhoneVerticalPair` (PVP): `(office_phone, vertical)`.

**Problem solved**: `autom8_asana` models tasks and projects but has no native analytics data — ad spend, leads, appointments, campaign performance all live in `autom8_data`. The `DataServiceClient` bridges the two services for workflows like `InsightsExportWorkflow`, `ConversationAuditWorkflow`, and `ReconciliationWorkflow`.

**Primary consumers**:
- `InsightsExportWorkflow` (12-table concurrent fetch per Offer via Lambda `insights_export`)
- `ConversationAuditWorkflow` (CSV export via Lambda `conversation_audit`)
- `ReconciliationWorkflow` / `reconciliation_runner` Lambda (payment matching)
- `api/dependencies.py` — `DataServiceClient` injection into FastAPI DI

**Design decisions**:
- **ADR-INS-004**: Client-side stale cache fallback — on 5xx failures, return cached response with `is_stale=True` rather than propagating the error. Default TTL: 300s (5 minutes).
- **ADR-INS-005**: Composed `CircuitBreaker` and `ExponentialBackoffRetry` from `autom8y_http >= 0.3.0`; the platform client (`Autom8yHttpClient`) is created with `enable_retry=False, enable_circuit_breaker=False` to avoid double-applying policies.
- **ADR-0002**: Sync wrapper (`get_insights()`) uses `asyncio.run()` for sync callers; raises `SyncInAsyncContextError` if called from an async context (fail-fast guard).
- **ADR-CONV-003**: `ExportResult` is a plain `dataclass` (not Pydantic) because `csv_content: bytes` is not JSON-serializable.
- **ADR-0028**: Polars is the primary DataFrame library; `to_dataframe()` returns `pl.DataFrame`. `to_pandas()` is a compatibility shim over `to_dataframe().to_pandas()`.
- **Config isolation (B4 audit)**: `TimeoutConfig`, `ConnectionPoolConfig`, `RetryConfig`, `CircuitBreakerConfig` in `config.py` are kept separate from the top-level `autom8_asana.config` equivalents. The data-service defaults differ intentionally (smaller pool, fewer retries, 502 in retryable codes, circuit breaker enabled by default). Merging them would silently change defaults for callers that rely on partial construction.
- **WS-DSC TDD**: The 8-step orchestration scaffold (CB check → acquire client → time → build request → execute with retry → elapsed → error path → success path) is encapsulated in `DefaultEndpointPolicy` in `_policy.py`. All 5 endpoint sub-modules delegate S2–S8 to this policy.

**Rejected alternatives**: Inline retry/circuit-breaker logic inside each endpoint method (rejected: ~196 LOC duplication eliminated by `_retry.py` factory and `DefaultEndpointPolicy`). Using `autom8y_http` platform-level retry (rejected: double-application with domain retry).

**Tradeoffs accepted**:
- `_policy.py`, `_retry.py`, `_cache.py`, `_metrics.py`, `_response.py`, `_normalize.py`, `_pii.py` are all module-level private helpers (not part of public API). This decomposes the original monolith `client.py` but introduces a level of indirection.
- `max_batch_size` is capped at 500 (server accepts up to 1000). `DataServiceJoinFetcher` (Phase 1) relies on this being ≥ 500 to avoid pre-chunking; lowering it requires fetcher changes (REC-P3 in architecture-report.md).
- TENSION-006: `autom8y_interop` protocol coverage is ~30% — `get_reconciliation_async()` and `get_export_csv_async()` have no interop analogues. Requires upstream PRs (EC-005).

---

## Conceptual Model

### PVP as Join Key

`PhoneVerticalPair(office_phone, vertical)` is the canonical cross-service join key. Canonical format: `pv1:{phone}:{vertical}` (e.g., `pv1:+17705753103:chiropractic`). The PVP maps between Asana's entity model and autom8_data's analytics model.

### Factory as Query Dimension

14 named factories (`account`, `ads`, `adsets`, `campaigns`, `spend`, `leads`, `appts`, `assets`, `targeting`, `payments`, `business_offers`, `ad_questions`, `ad_tests`, `base`) map to one of four `frame_type` values via `FACTORY_TO_FRAME_TYPE`:

| frame_type | factories |
|------------|-----------|
| `business` | account, payments |
| `offer` | ads, adsets, campaigns, spend, leads, appts, targeting, business_offers, ad_tests |
| `asset` | assets |
| `question` | ad_questions |
| `unit` | base |

### Four Request Shapes

| Shape | Path | Method | Use |
|-------|------|--------|-----|
| Single PVP insights | `/api/v1/data-service/insights` | POST | One business, one factory |
| Batch PVP insights | `/api/v1/data-service/insights` | POST | Multiple PVPs (1–1000) per chunk |
| Export CSV | `/api/v1/messages/export` | GET | Conversation audit CSV |
| Reconciliation | `/api/v1/insights/reconciliation/execute` | POST | Payment matching (InsightExecutor path) |
| Appointments | `/api/v1/appointments` | GET | Appointment detail rows |
| Leads | `/api/v1/leads` | GET | Lead detail rows |

Note: reconciliation uses a different backend path on autom8_data (`InsightExecutor`) distinct from the `InsightsService/FrameTypeMapper` path used by insights.

### Resilience Stack (Three Layers)

1. **Circuit breaker** (`CircuitBreaker` from `autom8y_http`): 5 consecutive failures → OPEN; 30s recovery timeout; 1 half-open probe call required to close. State exposed via `client.circuit_breaker` property.
2. **Retry with exponential backoff** (`ExponentialBackoffRetry`): max 2 retries; base 1.0s; max 10s; jitter enabled; retryable status codes: {429, 502, 503, 504}. Honors `Retry-After` header for 429 responses. Timeouts also retry (up to `max_retries`).
3. **Stale cache fallback** (ADR-INS-004): On 5xx error, `_cache.get_stale_response()` looks up cached entry; if found, returns `InsightsResponse(metadata.is_stale=True, metadata.cached_at=<datetime>, warnings=[...stale warning])`. Only insights (single PVP) path uses stale fallback; other endpoints do not.

### DefaultEndpointPolicy S2–S8 Scaffold

All endpoints delegate to `DefaultEndpointPolicy.execute()` which runs:
- **S2**: `circuit_breaker.check()` (raises / returns error dict for batch if open)
- **S3**: `_get_client()` (lazy double-checked lock init)
- **S4–S5**: `request_builder(http_client, descriptor)` → `execute_with_retry(make_request, callbacks)`
- **S6**: `error_handler` (status >= 400)
- **S7–S8**: `success_handler` (parse + record CB success + cache + metrics)
- **pre_execute_error_handler**: Insights-only stale cache fallback before re-raise.

Batch CB open is non-raising: returns `dict[canonical_key → BatchInsightsResult(error=...)]` for all PVPs.

### PII Contract (XR-003, SCAR-028)

Three functions in `_pii.py`:
- `mask_phone_number(phone)` — `+17705753103 → +1770***3103` (keep first 5 + last 4 digits)
- `mask_canonical_key(key)` — masks phone in `pv1:{phone}:{vertical}` canonical key
- `mask_pii_in_string(s)` — regex scan for E.164 pattern `\+\d{10,15}` then `mask_phone_number` via `re.sub`; applied to error messages, log fields, and error strings from batch exceptions

All log emission paths mask phone before output. Batch error strings are sanitized via `_mask_pii_in_string(str(exc))`.

### Period Normalization

`_normalize.normalize_period()` maps autom8_asana periods to autom8_data's uppercase enum format:
- `"lifetime" / None → "LIFETIME"`
- `"t7" / "l7" → "T7"`, `"t14" / "l14" → "T14"`, `"t30" / "l30" → "T30"`
- `"quarter" → "QUARTER"`, `"month" → "MONTH"`, `"week" → "WEEK"`
- Everything else → `"T30"` (backward-compatibility default)

### Emergency Kill Switch

`AUTOM8Y_DATA_INSIGHTS_ENABLED` env var (checked via `get_settings().data_service.insights_enabled`). Default: enabled. Set to `false/0/no` to disable without code deployment; raises `InsightsServiceError(reason="feature_disabled")` for all methods. Applied at the top of `get_insights_async`, `get_insights_batch_async`, `get_export_csv_async`, `get_appointments_async`, `get_leads_async`, `get_reconciliation_async`.

---

## Implementation Map

### Module Inventory (17 files in `src/autom8_asana/clients/data/`)

| File | Purpose | Key Exports |
|------|---------|-------------|
| `client.py` | `DataServiceClient` class — public API facade | `DataServiceClient` |
| `config.py` | Frozen dataclass config hierarchy | `DataServiceConfig`, `TimeoutConfig`, `ConnectionPoolConfig`, `RetryConfig`, `CircuitBreakerConfig` |
| `models.py` | Pydantic request/response models | `InsightsRequest`, `InsightsResponse`, `InsightsMetadata`, `ColumnInfo`, `BatchInsightsResult`, `BatchInsightsResponse`, `ExportResult` |
| `_pii.py` | PII masking primitives (XR-003) | `mask_phone_number`, `mask_canonical_key`, `mask_pii_in_string` |
| `_cache.py` | Cache read/write operations | `build_cache_key`, `cache_response`, `get_stale_response` |
| `_metrics.py` | Metrics emission | `MetricsHook` (type alias), `emit_metric` |
| `_normalize.py` | Period normalization | `normalize_period` |
| `_policy.py` | `DefaultEndpointPolicy` + request descriptors | `DefaultEndpointPolicy`, `EndpointPolicy`, `InsightsRequestDescriptor`, `BatchRequestDescriptor`, `ExportRequestDescriptor`, `ReconciliationRequestDescriptor`, `SimpleRequestDescriptor` |
| `_response.py` | HTTP response parsing + error mapping | `validate_factory`, `handle_error_response`, `parse_success_response` |
| `_retry.py` | Retry callback factory | `RetryCallbacks`, `build_retry_callbacks` |
| `_endpoints/insights.py` | `execute_insights_request` — single PVP POST | module-level function |
| `_endpoints/batch.py` | `execute_batch_request`, `build_entity_response` — multi-PVP POST | module-level functions |
| `_endpoints/export.py` | `get_export_csv` — conversation CSV GET | module-level function |
| `_endpoints/reconciliation.py` | `get_reconciliation` — reconciliation POST | module-level function |
| `_endpoints/simple.py` | `get_appointments`, `get_leads` — simple GET endpoints | module-level functions |
| `README.md` | Public developer documentation | — |

### Key Public Methods on `DataServiceClient`

| Method | Delegates to | Notes |
|--------|-------------|-------|
| `get_insights_async(factory, office_phone, vertical, *, period, start_date, end_date, ...)` | `_endpoints/insights.py:execute_insights_request` | Single PVP; validates factory, builds PVP, cache key |
| `get_insights(...)` | `get_insights_async` via `_run_sync` | Sync wrapper; raises `SyncInAsyncContextError` in async ctx |
| `get_insights_batch_async(pairs, *, factory, period, ...)` | `_endpoints/batch.py:execute_batch_request` | Chunks to 1000 PVPs; parallel via `gather_with_semaphore` for >1 chunk |
| `get_export_csv_async(office_phone, *, start_date, end_date)` | `_endpoints/export.py:get_export_csv` | Returns `ExportResult(csv_content: bytes, row_count, truncated, filename)` |
| `get_appointments_async(office_phone, *, days=90, limit=100)` | `_endpoints/simple.py:get_appointments` | GET `/api/v1/appointments` |
| `get_leads_async(office_phone, *, days=30, exclude_appointments=True, limit=100)` | `_endpoints/simple.py:get_leads` | GET `/api/v1/leads` |
| `get_reconciliation_async(office_phone, vertical, *, period, window_days)` | `_endpoints/reconciliation.py:get_reconciliation` | POST `/api/v1/insights/reconciliation/execute` |
| `is_healthy()` | `circuit_breaker.check()` | Raises `CircuitBreakerOpenError` if open |

### Cache Key Format

```
insights:{factory}:{pvp.canonical_key}
# e.g., insights:account:pv1:+17705753103:chiropractic
```

Note: cache keys use the raw (unmasked) canonical key for lookup but masked key in log output.

### Auth Flow

1. `_get_auth_token()` tries `auth_provider.get_secret(config.token_key)` first
2. Falls back to `resolve_secret_from_env(config.token_key)` (supports Lambda extension ARN resolution)
3. Token injected as `Authorization: Bearer {token}` header on HTTP client during lazy init (double-checked lock)
4. `AUTOM8Y_DATA_API_KEY` is the default `token_key` (env var name, not the value itself)
5. `ServiceTokenAuthProvider` is wired in `api/dependencies.py` (SCAR-012 fix)

### Data Flow (Single PVP Insights)

```
client.get_insights_async(factory, phone, vertical, period)
  → _check_feature_enabled()
  → validate_factory(factory_normalized)
  → PhoneVerticalPair(phone, vertical)  [validates E.164]
  → InsightsRequest(office_phone, vertical, period, ...)
  → build_cache_key(factory, pvp)
  → _execute_insights_request(factory, request, request_id, cache_key)
      → _endpoints/insights.py:execute_insights_request(client, ...)
          → FACTORY_TO_FRAME_TYPE[factory] → frame_type
          → normalize_period(request.insights_period) → "T30" etc.
          → build request_body dict {frame_type, phone_vertical_pairs, period, ...}
          → build_retry_callbacks(circuit_breaker, InsightsServiceError, ...)
          → DefaultEndpointPolicy.execute(InsightsRequestDescriptor)
              → circuit_breaker.check()  [raises InsightsServiceError(circuit_breaker) if open]
              → _get_client()  [lazy init with auth headers]
              → _execute_with_retry(POST /api/v1/data-service/insights)
                  → on success: parse_success_response → cache_response → emit metrics → return InsightsResponse
                  → on 5xx: handle_error_response → try get_stale_response
                                → if stale: return InsightsResponse(is_stale=True)
                                → else: raise InsightsServiceError
                  → on 400: raise InsightsValidationError
                  → on 404: raise InsightsNotFoundError
```

### Batch PVP Flow Variation

For batches > 1000 PVPs: chunked via `gather_with_semaphore(concurrency=max_concurrency)`. Each chunk calls `_execute_batch_request()`. HTTP 207 (partial success) is handled in the success path: `data[]` rows grouped by PVP canonical key, `errors[]` per-entity failures. Remaining PVPs not in either list are marked `error="No data returned for this PVP"`.

### Test Coverage Locations

- `tests/unit/clients/data/` — unit tests for all `clients/data/` modules
- `tests/integration/clients/data/` (if present) — integration tests
- 485 client tests per README (P95 < 2ms overhead)
- `AsyncMock(spec=DataServiceClient)` context-manager teardown patterns documented in `.know/scar-tissue.md:119`

---

## Boundaries and Failure Modes

### Explicit Scope

- `DataServiceClient` wraps **only** the autom8_data satellite service. It does not wrap Asana API calls (those are in `clients/tasks.py`, `clients/projects.py`, etc.).
- It does **not** implement server-side caching; it relies on the `CacheProvider` protocol injected at construction time. If no `cache_provider` is given, `has_cache=False` and all stale-fallback logic silently no-ops.
- It does **not** implement rate limiting. Rate limiting is handled at the FastAPI layer (SlowAPI middleware) for inbound requests; outbound retry honors `Retry-After`.
- `ExportResult.csv_content` is raw `bytes`. The client does **not** parse the CSV; it hands bytes directly to `AttachmentsClient.upload_async`.

### TENSION-006: autom8y_interop Protocol Coverage Gap

Only ~30% of `DataServiceClient` methods have analogues in `autom8y_interop`. Specifically:
- `get_reconciliation_async()` — no interop analogue (documented gap in `automation/workflows/protocols.py:32-61`)
- `get_export_csv_async()` — no interop analogue
- Both documented as bridge-specific gaps requiring upstream PRs (EC-005). `bridge_base.py:29-38` documents the missing methods.

### Known Failure Modes

**SCAR-012**: Client constructed without `auth_provider` — all joins returned zero results. Fix: explicit `ServiceTokenAuthProvider` injection in `api/dependencies.py`. Defense: `_get_auth_token()` gracefully falls back to env var if provider fails.

**SCAR-028**: PII leakage in error logs — `office_phone` values appeared unmasked in error log output. Fix: `mask_pii_in_string()` in `_pii.py` applied at all log emission sites. Pattern: `+17705753103 → +1770***3103`. Defense-in-depth: `mask_canonical_key` applied to PVP strings at all log sites.

**Env Var Naming**: `AUTOM8Y_DATA_API_KEY` — must include the `Y` suffix (`AUTOM8Y_`, not `AUTOM8_`). Missing `Y` causes silent auth failure (no token found, requests return 401). Default `token_key = "AUTOM8Y_DATA_API_KEY"` is hardcoded correctly in `config.py:231`.

**OpenAPI contract discrepancy** (undocumented in scar tissue, observed in source): The OpenAPI spec references `/api/v1/factory/{name}` but the actual implementation uses `/api/v1/data-service/insights` for all insights requests (single and batch). The `factory` name appears in the request body as `frame_type`, not the URL path.

**Circuit breaker open**: `is_healthy()` raises `CircuitBreakerOpenError`. `get_insights_async()` raises `InsightsServiceError(reason="circuit_breaker")`. Batch path does NOT raise — returns all PVPs as `BatchInsightsResult(error=...)` (non-raising CB factory).

**Batch HTTP 207**: Partial success. `_success_handler` in `batch.py` groups `data[]` by PVP canonical key (using `office_phone` + `vertical` fields in each row), then parses `errors[]` for per-entity failures. Any PVP not in either list is marked with `error="No data returned for this PVP"`.

**Batch chunk failures**: If an entire chunk fails (exception from `execute_with_retry`), `_make_pre_execute_error_handler` catches `InsightsServiceError | InsightsError` and marks all PVPs in that chunk as errored with a sanitized (PII-masked) error string. Does not propagate exception.

**Sync in async context**: `_run_sync()` detects a running event loop via `asyncio.get_running_loop()` and raises `SyncInAsyncContextError`. This is the fail-fast guard per ADR-0002.

### Configuration Boundaries

| Env Var | Default | Effect |
|---------|---------|--------|
| `AUTOM8Y_DATA_URL` | `http://localhost:8000` (via `settings.data_service.url`) | Base URL for all requests |
| `AUTOM8Y_DATA_API_KEY` | (none) | Token key name for auth provider lookup |
| `AUTOM8Y_DATA_CACHE_TTL` | 300 | Client-side cache TTL in seconds |
| `AUTOM8Y_DATA_INSIGHTS_ENABLED` | `true` | Emergency kill switch; `false/0/no` disables |

**max_batch_size** must be 1–1000 (enforced in `DataServiceConfig.__post_init__`). Default: 500. Lowering below 500 requires `DataServiceJoinFetcher` changes (REC-P3).

**Timeout defaults**: connect=5s, read=30s, write=30s, pool=5s. These are larger than typical API clients due to analytics query latency.

**Connection pool defaults**: max_connections=10, max_keepalive=5, keepalive_expiry=30s. Intentionally smaller than main client pool (100 connections) since autom8_data is a single satellite.

### Inter-Feature Interaction Points

- **`cache/`** subsystem: `CacheProvider` protocol injected optionally. `_cache.py` calls `cache.set()` and `cache.get()`. Cache failures are caught and logged; they never propagate (graceful degradation).
- **`protocols/auth.py`**: `AuthProvider.get_secret(key)` used for token retrieval. SCAR-012 established `ServiceTokenAuthProvider` as the correct implementation.
- **`protocols/cache.py`**: `CacheProvider` protocol for cache operations.
- **`api/dependencies.py`**: Wires `ServiceTokenAuthProvider` and `DataServiceClient` into FastAPI DI.
- **`automation/workflows/`**: `bridge_base.py` and `protocols.py` consume `DataServiceClient` for insights; TENSION-006 limits coverage.
- **`lambda_handlers/insights_export.py`**, **`lambda_handlers/conversation_audit.py`**, **`lambda_handlers/reconciliation_runner.py`**: All construct `DataServiceClient` independently in their Lambda handler scope.
- **`core/concurrency.py`**: `gather_with_semaphore` used in `get_insights_batch_async` for multi-chunk parallel execution.

```metadata
{
  "slug": "data-service-client",
  "category": "Infrastructure",
  "complexity": "HIGH",
  "confidence": 0.97,
  "status": "EXISTING",
  "previous_confidence": 0.82,
  "gaps_resolved": ["_policy.py DefaultEndpointPolicy internals", "_response.py error mapping", "_cache.py key format and TTL", "batch chunking across partial failures", "_pii.py full function inventory", "_normalize.py period mapping", "_retry.py callback factory", "_endpoints/* all 5 sub-modules"],
  "remaining_gaps": [],
  "key_adrs": ["ADR-INS-004", "ADR-INS-005", "ADR-0002", "ADR-CONV-003", "ADR-0028"],
  "key_scars": ["SCAR-012", "SCAR-028"],
  "key_tensions": ["TENSION-006"],
  "env_vars": ["AUTOM8Y_DATA_URL", "AUTOM8Y_DATA_API_KEY", "AUTOM8Y_DATA_CACHE_TTL", "AUTOM8Y_DATA_INSIGHTS_ENABLED"]
}
```
