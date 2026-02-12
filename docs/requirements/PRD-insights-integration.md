# PRD: autom8_asana Insights Integration with autom8_data

**PRD ID**: PRD-INSIGHTS-001
**Status**: Draft
**Author**: Requirements Analyst (Claude Opus 4.5)
**Date**: 2025-12-30
**Parent Initiative**: autom8 Satellite Extraction (see `~/Code/autom8y/docs/spikes/SPIKE-AUTOM8-DATA-PVP-MODERNIZATION.md`)

---

## Executive Summary

This PRD defines the requirements for integrating autom8_asana with the autom8_data satellite service to consume analytics insights via REST API. This is a foundational step in the satellite extraction initiative, enabling autom8_asana to request business metrics (spend, leads, CPL, ROAS, etc.) from autom8_data without direct coupling to the legacy monolith's SQL layer.

**Key Outcome**: autom8_asana can request insights for a Business's phone/vertical pair and receive structured analytics data, enabling dashboard population, automation triggers, and business intelligence features.

---

## 1. Problem Statement

### 1.1 Current State

**autom8_asana (this codebase)**:
- Provides an SDK for Asana API interactions
- Manages Business entities with `office_phone` (TextField) and `vertical` (EnumField) custom fields
- Has no mechanism to fetch analytics/insights data (spend, leads, CPL, etc.)
- Uses Polars DataFrames internally for data extraction from Asana

**Legacy Monolith (autom8)**:
- Contains 14 InsightsFactory subclasses producing analytics DataFrames
- 52 unique metrics across factories (spend, leads, cpl, roas, scheds, etc.)
- `PhoneVerticalPair` namedtuple for business scoping (no validation)
- `default_pv_pairs` property creates hard coupling to Asana API layer

**autom8_data Satellite (in development)**:
- Exposing insights via `POST /api/v1/factory/{factory_name}` REST API
- Returns JSON with dtype metadata for DataFrame reconstruction
- S2S JWT authentication
- Performance target: P95 < 500ms

### 1.2 Gap Analysis

| Capability | autom8_asana | autom8 Monolith | autom8_data |
|------------|--------------|-----------------|-------------|
| Business entity access | Yes (via Asana API) | Yes (via DB) | No direct access |
| PhoneVerticalPair | Has data (office_phone, vertical) | Owns namedtuple | Will own Pydantic model |
| Insights/Analytics | **None** | Full factory system | API exposure |
| DataFrame handling | Polars | Pandas | JSON + metadata |

**Critical Gap**: autom8_asana has the business context (phone + vertical) but cannot access analytics. autom8_data has the analytics API but needs clients to call it.

### 1.3 Why Now?

1. **Satellite Extraction Phase 1**: autom8_data API is being built; autom8_asana is the first client
2. **Automation Opportunities**: autom8_asana's AutomationEngine could trigger on insights thresholds
3. **Decoupling**: Breaking the monolith dependency allows independent deployment
4. **Contract Establishment**: Early integration defines the cross-service contract

---

## 2. Stakeholders

| Stakeholder | Role | Interest |
|-------------|------|----------|
| **Platform Team** | Service owners | Integration patterns, API contract |
| **autom8_asana Consumers** | SDK users | Access to insights in business context |
| **autom8_data Team** | API providers | Client implementation validation |
| **Operations** | Monitoring | Performance, error rates, caching |

---

## 3. User Stories

### US-001: Request Insights for a Business
**As** an autom8_asana SDK consumer,
**I want** to request analytics insights for a Business entity,
**So that** I can display spend, leads, and performance metrics.

**Acceptance Criteria**:
- [ ] Can request insights using Business.office_phone and Business.vertical
- [ ] Response includes spend, leads, cpl, roas, scheds at minimum
- [ ] Request completes within 500ms (P95) for cached data
- [ ] Errors return structured failure response, not exceptions

### US-002: Batch Insights for Multiple Businesses
**As** an autom8_asana SDK consumer processing multiple businesses,
**I want** to request insights for multiple phone/vertical pairs in one call,
**So that** I minimize HTTP overhead and respect rate limits.

**Acceptance Criteria**:
- [ ] Can provide list of phone/vertical pairs
- [ ] Response groups results by canonical key
- [ ] Partial failures don't fail entire batch
- [ ] Total time scales sub-linearly (not N * single request time)

### US-003: Insights Period Selection
**As** an autom8_asana SDK consumer,
**I want** to specify the time period for insights (lifetime, T30, date range),
**So that** I can analyze performance across different windows.

**Acceptance Criteria**:
- [ ] Supports `lifetime`, `t7`, `t30`, `t90` period presets
- [ ] Supports custom date range (start_date, end_date)
- [ ] Invalid periods return validation error (not 500)

### US-004: Factory Selection
**As** an autom8_asana SDK consumer,
**I want** to specify which InsightsFactory to query (account, ads, assets, etc.),
**So that** I get the specific metrics I need.

**Acceptance Criteria**:
- [ ] Supports all 14 factory types (account, ads, adsets, campaigns, spend, leads, appts, assets, targeting, payments, business_offers, ad_questions, ad_tests, base)
- [ ] Default factory is `account` if not specified
- [ ] Invalid factory name returns validation error

### US-005: Graceful Degradation
**As** an autom8_asana SDK consumer,
**I want** insight requests to degrade gracefully when autom8_data is unavailable,
**So that** my application doesn't crash due to external service issues.

**Acceptance Criteria**:
- [ ] Circuit breaker prevents cascade failures
- [ ] Configurable fallback behavior (return None, return cached, raise)
- [ ] Failure metrics exposed for monitoring

---

## 4. Functional Requirements

### FR-001: DataServiceClient Class (MUST)

**Description**: A client class for communicating with autom8_data.

**Requirements**:
- **FR-001.1**: `DataServiceClient` class in `autom8_asana.clients` module
- **FR-001.2**: Constructor accepts `base_url` (default: from env `AUTOM8_DATA_URL`)
- **FR-001.3**: Constructor accepts optional `auth_provider` (reuses AuthProvider protocol)
- **FR-001.4**: Uses httpx for HTTP (consistent with existing transport layer)
- **FR-001.5**: Implements context manager protocol for connection lifecycle

```python
# Example usage pattern
from autom8_asana.clients import DataServiceClient

async with DataServiceClient() as client:
    insights = await client.get_insights_async(
        office_phone="+17705753103",
        vertical="chiropractic",
        factory="account",
        period="t30",
    )
```

### FR-002: PhoneVerticalPair Model (MUST)

**Description**: A Pydantic model for the phone/vertical identifier.

**Requirements**:
- **FR-002.1**: Pydantic BaseModel (frozen=True) for immutability
- **FR-002.2**: E.164 phone validation (`+` prefix, 1-15 digits)
- **FR-002.3**: `canonical_key` property: `pv1:{phone}:{vertical}`
- **FR-002.4**: Backward-compatible iteration (`__iter__`, `__getitem__`)
- **FR-002.5**: Located in `autom8_asana.models.common` (or new `contracts` module)

```python
class PhoneVerticalPair(BaseModel, frozen=True):
    office_phone: str  # E.164: +15551234567
    vertical: str      # Enum value: CHIROPRACTIC, DENTAL

    @field_validator('office_phone')
    @classmethod
    def validate_e164(cls, v: str) -> str:
        if not re.match(r'^\+[1-9]\d{1,14}$', v):
            raise ValueError(f"Invalid E.164 format: {v}")
        return v

    @property
    def canonical_key(self) -> str:
        return f"pv1:{self.office_phone}:{self.vertical}"
```

**Open Question**: Should autom8_asana own this model, or import from a shared `autom8y_core` package?

**Recommendation**: autom8_asana owns its own copy initially; extract to shared package if/when needed by 3+ services.

### FR-003: get_insights_async Method (MUST)

**Description**: Primary async method for fetching insights.

**Requirements**:
- **FR-003.1**: Method signature:
  ```python
  async def get_insights_async(
      self,
      office_phone: str,
      vertical: str,
      *,
      factory: str = "account",
      period: str | None = "lifetime",
      start_date: str | None = None,
      end_date: str | None = None,
      metrics: list[str] | None = None,
      dimensions: list[str] | None = None,
      refresh: bool = False,
  ) -> InsightsResponse:
  ```
- **FR-003.2**: Returns `InsightsResponse` model (not raw dict)
- **FR-003.3**: Raises `InsightsError` subclass on failure (not generic Exception)
- **FR-003.4**: Validates inputs before making HTTP request
- **FR-003.5**: Includes request_id for tracing in response

### FR-004: get_insights Sync Wrapper (MUST)

**Description**: Synchronous wrapper following existing SDK pattern.

**Requirements**:
- **FR-004.1**: Follows ADR-0002 sync/async pattern (fail-fast in async context)
- **FR-004.2**: Uses `asyncio.run()` for clean execution
- **FR-004.3**: Raises `SyncInAsyncContextError` if called from async context

### FR-005: InsightsResponse Model (MUST)

**Description**: Typed response model for insights data.

**Requirements**:
- **FR-005.1**: Contains `data: list[dict[str, Any]]` (records format)
- **FR-005.2**: Contains `metadata: InsightsMetadata` with:
  - factory, row_count, column_count
  - columns (name, dtype, nullable)
  - cache_hit, duration_ms
  - sort_history (optional)
- **FR-005.3**: Contains `request_id: str` for correlation
- **FR-005.4**: `to_dataframe()` method for Polars conversion
- **FR-005.5**: `to_pandas()` method for Pandas conversion (backward compat)

### FR-006: Batch Insights (SHOULD)

**Description**: Request insights for multiple PVPs in one call.

**Requirements**:
- **FR-006.1**: `get_insights_batch_async(pairs: list[PhoneVerticalPair], ...)` method
- **FR-006.2**: Returns `BatchInsightsResponse` with keyed results
- **FR-006.3**: Partial failures included in response (not raised)
- **FR-006.4**: Maximum batch size: 50 pairs (configurable)

### FR-007: Business Integration (SHOULD)

**Description**: Convenience method on Business entity.

**Requirements**:
- **FR-007.1**: `Business.get_insights_async(client, factory, period)` method
- **FR-007.2**: Automatically extracts office_phone and vertical from self
- **FR-007.3**: Raises `InsightsError` if office_phone or vertical is None/missing
- **FR-007.4**: Returns `InsightsResponse` or None if business lacks PVP data

### FR-008: Error Handling (MUST)

**Description**: Structured error hierarchy for insights operations.

**Requirements**:
- **FR-008.1**: `InsightsError` base exception in `autom8_asana.exceptions`
- **FR-008.2**: `InsightsValidationError` for invalid inputs (400-level)
- **FR-008.3**: `InsightsNotFoundError` for no data (404-level)
- **FR-008.4**: `InsightsServiceError` for upstream failures (500-level)
- **FR-008.5**: All exceptions include `request_id` for tracing

### FR-009: Authentication (MUST)

**Description**: S2S authentication with autom8_data.

**Requirements**:
- **FR-009.1**: Reuses existing `AuthProvider` protocol
- **FR-009.2**: Supports JWT token acquisition from auth service
- **FR-009.3**: Token caching to avoid per-request auth overhead
- **FR-009.4**: Automatic token refresh on 401 response

---

## 5. Non-Functional Requirements

### NFR-001: Performance (MUST)

| Metric | Target | Measurement |
|--------|--------|-------------|
| P50 latency (cached) | < 100ms | Client-side timing |
| P95 latency (cached) | < 500ms | Client-side timing |
| P99 latency (any) | < 2000ms | Client-side timing |
| Connection pool | 10 connections | httpx config |
| Request timeout | 30s | httpx config |

### NFR-002: Reliability (MUST)

| Metric | Target | Implementation |
|--------|--------|----------------|
| Circuit breaker threshold | 5 failures in 60s | Trigger open state |
| Circuit breaker recovery | 30s half-open probe | Auto-recovery |
| Retry policy | 2 retries with exponential backoff | 1s, 2s delays |
| Retry conditions | 429, 502, 503, 504 only | Not 4xx client errors |

### NFR-003: Observability (MUST)

| Signal | Implementation |
|--------|----------------|
| Logging | Structured logs for request/response/error |
| Metrics | request_count, error_count, latency_histogram |
| Tracing | request_id propagation to/from autom8_data |
| Health | `/health` endpoint check before requests (optional) |

### NFR-004: Compatibility (MUST)

| Constraint | Requirement |
|------------|-------------|
| Python version | >= 3.11 (consistent with SDK) |
| httpx version | >= 0.27.0 (existing dependency) |
| Pydantic version | >= 2.0 (existing dependency) |
| Polars version | >= 1.0 (existing dependency) |

### NFR-005: Security (MUST)

| Requirement | Implementation |
|-------------|----------------|
| Token storage | Never log tokens; use auth_provider secret management |
| PII handling | office_phone may be PII; redact in error messages |
| TLS | HTTPS required for production (http allowed for localhost) |

---

## 6. Edge Cases and Failure Modes

### EC-001: Business with Missing office_phone
- **Behavior**: `Business.get_insights_async()` raises `InsightsValidationError`
- **Message**: "Cannot request insights: office_phone is required"

### EC-002: Business with Missing vertical
- **Behavior**: `Business.get_insights_async()` raises `InsightsValidationError`
- **Message**: "Cannot request insights: vertical is required"

### EC-003: Empty Response from autom8_data
- **Behavior**: Return `InsightsResponse` with `data=[]`, `row_count=0`
- **Not**: Raise exception (empty is a valid response)

### EC-004: autom8_data Returns 404
- **Behavior**: Raise `InsightsNotFoundError`
- **Message**: Include factory name and PVP canonical key

### EC-005: autom8_data Returns 500
- **Behavior**: Raise `InsightsServiceError` after retries exhausted
- **Include**: request_id, upstream error message (if safe)

### EC-006: autom8_data Timeout
- **Behavior**: Raise `InsightsServiceError` with "timeout" reason
- **Circuit breaker**: Increment failure count

### EC-007: Invalid Period Format
- **Behavior**: Raise `InsightsValidationError` before HTTP request
- **Validation**: period must match `lifetime|t\d+|l\d+|date|week|month|quarter|year`

### EC-008: Circuit Breaker Open
- **Behavior**: Raise `InsightsServiceError` immediately (no HTTP)
- **Message**: "Circuit breaker open; insights temporarily unavailable"

### EC-009: Concurrent Requests to Same PVP
- **Behavior**: Both requests proceed (no request coalescing in v1)
- **Future**: Consider request coalescing for duplicate suppression

---

## 7. Migration Strategy

### Phase 1: Foundation (Sprint 1)

**Scope**:
- DataServiceClient with single factory support (`account`)
- PhoneVerticalPair model
- Basic error handling
- Feature flag: `AUTOM8_DATA_INSIGHTS_ENABLED=false` (default off)

**Success Criteria**:
- [ ] Can call `get_insights_async()` with hardcoded URL
- [ ] Response parses to InsightsResponse model
- [ ] Unit tests with mocked HTTP responses pass
- [ ] Integration test against staging autom8_data passes

### Phase 2: Hardening (Sprint 2)

**Scope**:
- All 14 factories supported
- Batch insights method
- Circuit breaker implementation
- Observability hooks
- Feature flag default: `true`

**Success Criteria**:
- [ ] All factory types return valid responses
- [ ] Batch requests work for up to 50 PVPs
- [ ] Circuit breaker trips after 5 failures
- [ ] Metrics emitted to observability hook

### Phase 3: Integration (Sprint 3)

**Scope**:
- Business.get_insights_async() convenience method
- Shadow mode validation (compare with monolith if available)
- Performance benchmarking
- Documentation

**Success Criteria**:
- [ ] Business entity can fetch its own insights
- [ ] Parity with monolith data (if shadow mode enabled)
- [ ] P95 < 500ms in production load test
- [ ] SDK documentation updated

---

## 8. Out of Scope

The following are explicitly **NOT** in scope for this PRD:

| Item | Reason |
|------|--------|
| autom8_data API implementation | Owned by autom8_data team |
| PhoneVerticalPair modernization in monolith | Covered by parent spike |
| Cache layer (Redis/DuckDB) | Client delegates to autom8_data caching |
| Arrow/Parquet transport | JSON is sufficient for v1; future optimization |
| Streaming responses | Insights responses are < 10MB; pagination sufficient |
| Multi-tenant support | Single-tenant for now; `pv2:` prefix reserved for future |
| Webhook notifications for insights updates | Future feature |

---

## 9. Dependencies

### Upstream Dependencies

| Dependency | Owner | Status | Risk |
|------------|-------|--------|------|
| autom8_data `/api/v1/factory/{name}` endpoint | autom8_data team | In Development | Medium - API may change |
| Auth service JWT tokens | Platform team | Available | Low |
| autom8y_core HTTP client (optional) | Platform team | Available | Low |

### Downstream Dependencies

| Dependency | Impact |
|------------|--------|
| SDK consumers | Breaking change if response schema changes |
| Automation rules | May need insights data for triggers |
| Dashboard clients | Will call get_insights for metrics display |

---

## 10. Success Criteria

### Sprint 1 Definition of Done

- [ ] `DataServiceClient` class implemented with `get_insights_async`
- [ ] `PhoneVerticalPair` model with E.164 validation and canonical_key
- [ ] `InsightsResponse` model with `to_dataframe()` method
- [ ] Unit tests: >= 90% coverage of new code
- [ ] Integration test: successful call to staging autom8_data
- [ ] Error handling: all 5 error types defined and tested
- [ ] Feature flag: `AUTOM8_DATA_INSIGHTS_ENABLED` controls activation
- [ ] Documentation: docstrings on all public methods

### Measurable Outcomes (30 days post-launch)

| Metric | Target |
|--------|--------|
| Error rate | < 1% of requests |
| P95 latency | < 500ms |
| Adoption | >= 3 internal consumers using SDK |
| Uptime | 99.9% (no client-side outages) |

---

## 11. Open Questions

| # | Question | Owner | Target Date |
|---|----------|-------|-------------|
| OQ-1 | Should PhoneVerticalPair live in autom8_asana or shared package? | Architect | TDD phase |
| OQ-2 | What auth flow to use? S2S JWT or API key? | Platform team | Sprint 1 |
| OQ-3 | Should we support Polars-native response (Arrow)? | Architect | Sprint 2 |
| OQ-4 | Cache-Control header handling on client side? | Architect | Sprint 2 |

---

## 12. Appendix

### A. InsightsFactory Catalog

From parent spike (`INTEGRATE-INSIGHTS-API.md`):

| Factory | Frame Type | Metrics | Dimensions |
|---------|------------|---------|------------|
| AccountInsights | ACCOUNT_INSIGHTS | 42 | 7 |
| AdsInsights | ADS_INSIGHTS | 36 | 14 |
| AdsetsInsights | ADSETS_INSIGHTS | 36 | 10 |
| CampaignsInsights | CAMPAIGN_INSIGHTS | 36 | 9 |
| SpendInsights | RECONCILIATIONS | 18 | 6 |
| LeadInsights | LEADS | 5 | 11 |
| ApptInsights | APPOINTMENTS | 8 | 11 |
| AssetInsights | ASSETS_INSIGHTS | 27 | 17 |
| TargetingInsights | TARGETING | 25 | 13 |
| PaymentsInsights | PAYMENTS | 6 | 12 |
| BusinessOfferInsights | BUSINESS_OFFERS | 27 | 10 |
| AdQuestionInsights | QUESTIONS | 22 | 4 |
| AdTestInsights | AD_TESTS | 16 | 5 |

### B. autom8_asana Existing Patterns

**Custom Field Descriptors**: Business.office_phone and Unit.vertical are TextField and EnumField descriptors that read from Asana custom fields. Integration should use these directly.

**Polars DataFrame**: The dataframes module uses Polars for task extraction. InsightsResponse.to_dataframe() should return Polars (not Pandas) for consistency.

**AsyncHTTPClient**: Located at `autom8_asana.transport.http`. DataServiceClient should follow similar patterns but may use a separate connection pool.

### C. Related Documents

| Document | Path |
|----------|------|
| Parent R&D Spike | `~/Code/autom8y/docs/spikes/SPIKE-AUTOM8-DATA-PVP-MODERNIZATION.md` |
| Insights API Spec | `~/Code/autom8y/docs/research/INTEGRATE-INSIGHTS-API.md` |
| Dependency Break Strategy | `~/Code/autom8y/docs/research/INTEGRATION-MAP-DEFAULT-PV-PAIRS-001.md` |
| POC Scope | `~/Code/autom8y/docs/prototypes/POC-AUTOM8-SATELLITE-EXTRACTION.md` |

---

## Artifact Verification

| Artifact | Absolute Path | Status |
|----------|---------------|--------|
| This PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-insights-integration.md` | Created |

---

**Handoff**: Route to **Architect** for TDD creation covering:
1. DataServiceClient architecture and transport layer integration
2. PhoneVerticalPair ownership decision (OQ-1)
3. InsightsResponse DataFrame conversion design
4. Circuit breaker and retry implementation details
5. Feature flag mechanism
