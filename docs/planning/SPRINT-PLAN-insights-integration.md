# Sprint Plan: autom8_asana Insights Integration

**Initiative**: autom8_asana Insights Integration Architecture
**PRD Reference**: [PRD-INSIGHTS-001](../requirements/PRD-insights-integration.md)
**TDD Reference**: [TDD-INSIGHTS-001](../design/TDD-insights-integration.md)
**Created**: 2025-12-30

---

## Overview

This sprint plan breaks the TDD implementation phases into actionable stories with acceptance criteria. Total estimated effort: 3 sprints (15 dev days).

---

## Sprint 1: Foundation (Speed to Value)

**Goal**: Get `account` factory working end-to-end with cache fallback. Minimal scope for fast delivery.
**Feature Flag**: `AUTOM8_DATA_INSIGHTS_ENABLED=false` (default off)
**Priority**: Speed to value - defer batch, all factories, Business integration to Sprint 2+

### User Decisions Applied
- **Priority**: Speed to Value (account factory only)
- **Resilience**: Cache fallback using existing CacheProvider infrastructure
- **Testing**: Contract tests with OpenAPI mock server
- **Observability**: Full metrics (structured logs + Prometheus-style)

### Story 1.1: PhoneVerticalPair Model

**Description**: Create the Pydantic model for phone/vertical business identifiers.

**Package**: `autom8_asana/models/contracts/phone_vertical.py`

**Acceptance Criteria**:
- [ ] Pydantic BaseModel with `frozen=True` for immutability
- [ ] E.164 phone validation (regex: `^\+[1-9]\d{1,14}$`)
- [ ] `canonical_key` property returns `pv1:{phone}:{vertical}`
- [ ] `__iter__` and `__getitem__` for tuple unpacking backward compatibility
- [ ] `__hash__` implemented for use as dict key
- [ ] `from_business()` classmethod for Business entity integration
- [ ] Unit tests: validation, canonical_key, iteration, hashing

**Dependencies**: None

---

### Story 1.2: Exception Hierarchy

**Description**: Create structured exception classes for insights operations.

**Package**: `autom8_asana/exceptions.py` (append to existing)

**Acceptance Criteria**:
- [ ] `InsightsError` base class with `request_id` attribute
- [ ] `InsightsValidationError` with `field` attribute (400-level)
- [ ] `InsightsNotFoundError` (404-level)
- [ ] `InsightsServiceError` with `reason` attribute (500-level)
- [ ] All exceptions inherit from existing `AsanaError`
- [ ] Unit tests: exception instantiation, attribute access

**Dependencies**: None

---

### Story 1.3: DataServiceConfig

**Description**: Create configuration dataclasses for client settings.

**Package**: `autom8_asana/clients/data/config.py`

**Acceptance Criteria**:
- [ ] `TimeoutConfig` dataclass (connect, read, write, pool)
- [ ] `ConnectionPoolConfig` dataclass (max_connections, keepalive)
- [ ] `RetryConfig` dataclass (max_retries, base_delay, exponential_base)
- [ ] `CircuitBreakerConfig` dataclass (failure_threshold, recovery_timeout)
- [ ] `DataServiceConfig` main config with `from_env()` classmethod
- [ ] Default values per TDD specifications
- [ ] Unit tests: from_env loading, default values

**Dependencies**: None

---

### Story 1.4: InsightsResponse Models

**Description**: Create request/response Pydantic models with staleness support.

**Package**: `autom8_asana/clients/data/models.py`

**Acceptance Criteria**:
- [ ] `InsightsRequest` model with all query parameters
- [ ] `ColumnInfo` model for column metadata
- [ ] `InsightsMetadata` model with:
  - `factory`, `row_count`, `columns`, `cache_hit`, `duration_ms`
  - `is_stale: bool = False` (per ADR-INS-004 revision)
  - `cached_at: datetime | None = None` (per ADR-INS-004 revision)
- [ ] `InsightsResponse` model with `data`, `metadata`, `request_id`
- [ ] `to_dataframe()` returns Polars DataFrame with correct dtypes
- [ ] `to_pandas()` returns pandas DataFrame for backward compatibility
- [ ] Unit tests: model parsing, DataFrame conversion, staleness fields

**Dependencies**: Story 1.3 (config)

---

### Story 1.5: DataServiceClient Skeleton

**Description**: Create the HTTP client class with context manager and cache support.

**Package**: `autom8_asana/clients/data/client.py`

**Acceptance Criteria**:
- [ ] `DataServiceClient` class with httpx.AsyncClient
- [ ] Constructor accepts `config`, `auth_provider`, `logger`
- [ ] Constructor accepts `cache_provider: CacheProvider | None` (per ADR-INS-004)
- [ ] Constructor accepts `staleness_settings: StalenessCheckSettings | None`
- [ ] `__aenter__` / `__aexit__` for async context manager
- [ ] `close()` method for resource cleanup
- [ ] `_get_client()` creates httpx client with config (connection pool, timeouts)
- [ ] `_get_auth_token()` retrieves JWT from auth_provider or env
- [ ] Unit tests: context manager lifecycle, client creation, cache injection

**Dependencies**: Story 1.3 (config), Story 1.2 (exceptions)

---

### Story 1.6: get_insights_async Implementation (Account Factory Only)

**Description**: Implement the primary insights fetching method for account factory.

**Package**: `autom8_asana/clients/data/client.py`

**Acceptance Criteria**:
- [ ] `get_insights_async()` method with full signature per TDD
- [ ] Factory validation (**account only** in Sprint 1 - other factories return clear error)
- [ ] PhoneVerticalPair construction and validation
- [ ] HTTP POST to `/api/v1/factory/{factory_name}`
- [ ] Error response mapping (400→ValidationError, 404→NotFoundError, 500→ServiceError)
- [ ] Success response parsing to InsightsResponse
- [ ] Request ID generation and inclusion in headers
- [ ] Contract tests with OpenAPI mock server (respx)
- [ ] Integration test: one successful call to staging (account factory)

**Dependencies**: Story 1.1 (PVP), Story 1.4 (models), Story 1.5 (skeleton)

---

### Story 1.7: Feature Flag

**Description**: Add environment variable control for feature activation.

**Acceptance Criteria**:
- [ ] Check `AUTOM8_DATA_INSIGHTS_ENABLED` env var in client
- [ ] Default value: `false` (disabled)
- [ ] If disabled, `get_insights_async()` raises `InsightsServiceError` with `reason="feature_disabled"`
- [ ] Clear error message instructing how to enable
- [ ] Unit test: disabled behavior, enabled behavior

**Dependencies**: Story 1.6

---

### Story 1.8: Cache Integration (ADR-INS-004)

**Description**: Integrate DataServiceClient with existing CacheProvider for fallback.

**Package**: `autom8_asana/clients/data/client.py`, `autom8_asana/cache/entry.py`

**Acceptance Criteria**:
- [ ] Add `EntryType.INSIGHTS` to `autom8_asana/cache/entry.py`
- [ ] Add `AUTOM8_DATA_CACHE_TTL` env var (default: 300s for live analytics)
- [ ] Cache key format: `insights:{factory}:{canonical_key}`
- [ ] On successful response: store in cache via `set_versioned()`
- [ ] On service failure: check cache for stale entry
- [ ] Return stale response with `is_stale=True`, `cached_at` populated
- [ ] Graceful degradation: cache failures don't break requests
- [ ] Unit tests: cache hit, cache miss, stale fallback, cache failure

**Dependencies**: Story 1.5 (skeleton), Story 1.6 (get_insights_async)

---

### Story 1.9: Observability (Full Metrics)

**Description**: Add structured logging and Prometheus-style metrics.

**Package**: `autom8_asana/clients/data/client.py`

**Acceptance Criteria**:
- [ ] Request logging: factory, period, pvp_canonical_key, request_id
- [ ] Response logging: request_id, row_count, cache_hit, is_stale, duration_ms
- [ ] Error logging: request_id, status_code, error_type
- [ ] PII redaction: phone numbers masked in logs
- [ ] Metrics hooks: request_total, error_total, latency_histogram
- [ ] Unit tests: verify log structure, verify metrics emission

**Dependencies**: Story 1.6 (get_insights_async)

---

### Sprint 1 Definition of Done

- [ ] All stories (1.1-1.9) completed with passing tests
- [ ] Unit test coverage >= 90% on new code
- [ ] Contract tests with OpenAPI mock server passing
- [ ] One successful integration test against staging autom8_data (account factory)
- [ ] Cache fallback working with stale data transparency
- [ ] Structured logging and metrics emitting
- [ ] PR created and reviewed
- [ ] Feature flag controls activation (default off)

---

## Sprint 2: Hardening

**Goal**: Add robustness features (retry, circuit breaker, batch) and all factory support.
**Feature Flag**: `AUTOM8_DATA_INSIGHTS_ENABLED=true` (default on)

### Story 2.1: All 14 Factories

**Description**: Validate and document all factory types.

**Acceptance Criteria**:
- [ ] `VALID_FACTORIES` frozenset with all 14 factory names
- [ ] Validation error message lists valid factories
- [ ] Unit tests for each factory type name
- [ ] Documentation of factory→frame_type mapping

**Dependencies**: Sprint 1

---

### Story 2.2: Retry Handler Integration

**Description**: Add exponential backoff retry for transient failures.

**Acceptance Criteria**:
- [ ] Integrate existing `RetryHandler` from transport layer
- [ ] Retry on status codes: 429, 502, 503, 504
- [ ] Do NOT retry 4xx client errors (except 429)
- [ ] Respect `Retry-After` header for 429
- [ ] Maximum 2 retries with exponential backoff (1s, 2s)
- [ ] Unit tests: retry behavior, retry exhaustion

**Dependencies**: Sprint 1

---

### Story 2.3: Circuit Breaker Integration

**Description**: Add circuit breaker to prevent cascade failures.

**Acceptance Criteria**:
- [ ] Integrate existing `CircuitBreaker` from transport layer
- [ ] Configure: 5 failures in 60s triggers open state
- [ ] Recovery timeout: 30s before half-open
- [ ] Half-open: 1 probe request before closing
- [ ] Record success/failure on each request
- [ ] When open, raise `InsightsServiceError` immediately (no HTTP)
- [ ] Unit tests: closed→open transition, half-open probe, recovery

**Dependencies**: Sprint 1

---

### Story 2.4: Batch Insights

**Description**: Implement bulk insights fetching for multiple PVPs.

**Package**: `autom8_asana/clients/data/client.py` (add method)
**Package**: `autom8_asana/clients/data/models.py` (add models)

**Acceptance Criteria**:
- [ ] `BatchInsightsResult` model (pvp, response, error, success property)
- [ ] `BatchInsightsResponse` model (results dict, counts)
- [ ] `get_insights_batch_async()` method
- [ ] Concurrent requests with semaphore (max_concurrency=10)
- [ ] Maximum batch size: 50 (configurable)
- [ ] Partial failures captured in response (not raised)
- [ ] `to_dataframe()` concatenates all successful results
- [ ] Unit tests: partial failure, max size, concurrency

**Dependencies**: Story 2.2, 2.3

---

### Story 2.5: Observability

**Description**: Add structured logging and metrics hooks.

**Acceptance Criteria**:
- [ ] Request logging: factory, period, pvp_canonical_key, request_id
- [ ] Response logging: request_id, row_count, cache_hit, duration_ms
- [ ] Error logging: request_id, status_code, error_type
- [ ] PII redaction: phone numbers masked in logs
- [ ] Metrics emitted via hook: request_total, error_total, latency_histogram
- [ ] Circuit breaker state exposed as metric

**Dependencies**: Sprint 1

---

### Story 2.6: Sync Wrapper

**Description**: Add synchronous wrapper method.

**Acceptance Criteria**:
- [ ] `get_insights()` sync method wrapping `get_insights_async()`
- [ ] Uses existing `run_sync()` helper
- [ ] Raises `SyncInAsyncContextError` if called from async context
- [ ] ADR-0002 compliant
- [ ] Unit test: sync behavior, async context detection

**Dependencies**: Sprint 1

---

### Story 2.7: Feature Flag Default Change

**Description**: Enable feature by default.

**Acceptance Criteria**:
- [ ] Change `AUTOM8_DATA_INSIGHTS_ENABLED` default to `true`
- [ ] Update documentation
- [ ] Announce change in PR description

**Dependencies**: All Sprint 2 stories

---

### Sprint 2 Definition of Done

- [ ] All stories completed with passing tests
- [ ] All 14 factories callable
- [ ] Batch requests working (up to 50 PVPs)
- [ ] Circuit breaker tripping after 5 failures
- [ ] Retry with exponential backoff verified
- [ ] Structured logging emitted
- [ ] Feature flag default changed to `true`
- [ ] PR created and reviewed

---

## Sprint 3: Integration

**Goal**: Business entity integration, performance validation, documentation.
**Feature Flag**: Consider removing (always enabled)

### Story 3.1: Business.get_insights_async

**Description**: Add convenience method to Business entity.

**Package**: `autom8_asana/models/business/business.py`

**Acceptance Criteria**:
- [ ] `get_insights_async(client, factory, period, **kwargs)` method
- [ ] Uses `self.office_phone` and `self.vertical`
- [ ] Raises `InsightsValidationError` if office_phone or vertical is None
- [ ] Returns `InsightsResponse`
- [ ] Docstring with usage example
- [ ] Unit test: valid business, missing phone, missing vertical

**Dependencies**: Sprint 2

---

### Story 3.2: Performance Benchmarking

**Description**: Validate P95 < 500ms target.

**Acceptance Criteria**:
- [ ] Create benchmark script for load testing
- [ ] Test against staging autom8_data
- [ ] Measure: P50, P95, P99 latencies
- [ ] Test scenarios: single request, batch (10, 50 PVPs)
- [ ] Document results in benchmark report
- [ ] P95 < 500ms achieved

**Dependencies**: Sprint 2

---

### Story 3.3: Shadow Mode (Optional)

**Description**: Compare results with monolith for parity validation.

**Acceptance Criteria**:
- [ ] If enabled, fetch from both autom8_data and monolith
- [ ] Compare row counts, column presence, key metrics
- [ ] Log discrepancies without failing
- [ ] Feature flag: `AUTOM8_DATA_SHADOW_MODE=false`
- [ ] Unit test: comparison logic

**Dependencies**: Sprint 2 (may be deferred)

---

### Story 3.4: SDK Documentation

**Description**: Document all public APIs.

**Acceptance Criteria**:
- [ ] Docstrings on all public methods (Google style)
- [ ] Usage examples in docstrings
- [ ] README section for insights integration
- [ ] Error handling guide
- [ ] Migration guide from monolith (if applicable)

**Dependencies**: Sprint 2

---

### Story 3.5: Examples

**Description**: Create working code examples.

**Package**: `examples/insights/` directory

**Acceptance Criteria**:
- [ ] `single_request.py`: Basic get_insights_async usage
- [ ] `batch_request.py`: Batch insights for multiple businesses
- [ ] `business_integration.py`: Business.get_insights_async usage
- [ ] `error_handling.py`: Proper exception handling
- [ ] All examples runnable with staging credentials

**Dependencies**: Sprint 2

---

### Story 3.6: Feature Flag Cleanup (Optional)

**Description**: Remove feature flag if confident in stability.

**Acceptance Criteria**:
- [ ] Remove `AUTOM8_DATA_INSIGHTS_ENABLED` check from code
- [ ] Update documentation
- [ ] Verify no external dependencies on flag

**Dependencies**: All Sprint 3 stories (defer to post-launch if uncertain)

---

### Sprint 3 Definition of Done

- [ ] All stories completed with passing tests
- [ ] Business.get_insights_async() working
- [ ] P95 < 500ms validated in benchmark
- [ ] SDK documentation complete
- [ ] Examples created and tested
- [ ] PR created and reviewed

---

## Rollout Plan

| Phase | Duration | Scope |
|-------|----------|-------|
| **Internal Testing** | 1 week | Platform team only |
| **Beta** | 1 week | 2-3 internal consumers |
| **GA** | Ongoing | All SDK consumers |

### Rollback Plan

1. Set `AUTOM8_DATA_INSIGHTS_ENABLED=false` in environment
2. Deploy affected services
3. Verify insights calls return feature_disabled error
4. Investigate root cause
5. Fix and re-enable

---

## Success Metrics (30 days post-GA)

| Metric | Target |
|--------|--------|
| Error rate | < 1% |
| P95 latency | < 500ms |
| Adoption | >= 3 consumers |
| Circuit breaker trips | < 5/day |

---

## Artifact Verification

| Artifact | Absolute Path | Status |
|----------|---------------|--------|
| This Sprint Plan | `/Users/tomtenuta/Code/autom8_asana/docs/planning/SPRINT-PLAN-insights-integration.md` | Created |
| PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-insights-integration.md` | Exists |
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-insights-integration.md` | Exists |
