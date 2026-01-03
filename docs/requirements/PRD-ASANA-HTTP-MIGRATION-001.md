---
artifact_id: PRD-asana-http-migration-001
title: "autom8_asana HTTP Layer Migration to autom8y-http Platform SDK"
created_at: "2026-01-03T14:00:00Z"
author: requirements-analyst
status: draft
complexity: MODULE
impact: high
impact_categories: [api_contract, cross_service]
success_criteria:
  - id: SC-001
    description: "Parallel fetches of 2614+ tasks complete without rate limit errors (no 429 responses)"
    testable: true
    priority: must-have
  - id: SC-002
    description: "Rate limiting is coordinated across all concurrent requests (single TokenBucketRateLimiter instance)"
    testable: true
    priority: must-have
  - id: SC-003
    description: "Existing public API consumers (AsanaClient, sub-clients) require no code changes"
    testable: true
    priority: must-have
  - id: SC-004
    description: "Retry warnings reduced from 80+ to fewer than 10 during parallel section fetch"
    testable: true
    priority: must-have
  - id: SC-005
    description: "All existing tests pass with no regression"
    testable: true
    priority: must-have
  - id: SC-006
    description: "Circuit breaker provides cascading failure protection for Asana API outages"
    testable: true
    priority: should-have
  - id: SC-007
    description: "autom8y-http is imported from CodeArtifact, not vendored"
    testable: true
    priority: must-have
related_adrs:
  - ADR-0048  # Circuit breaker pattern
  - ADR-0002  # Sync-in-async detection
stakeholders:
  - sdk-consumer
  - api-service-operator
  - platform-team
schema_version: "1.0"
---

# PRD: autom8_asana HTTP Layer Migration to autom8y-http Platform SDK

**PRD ID**: PRD-ASANA-HTTP-MIGRATION-001
**Version**: 1.0
**Date**: 2026-01-03
**TDD Reference**: TDD-ASANA-HTTP-MIGRATION-001 (to be created)

---

## Overview

This PRD defines requirements for migrating autom8_asana's custom HTTP transport layer to the autom8y-http platform SDK. The migration addresses thundering herd problems during parallel fetches and aligns autom8_asana with platform-wide HTTP infrastructure.

---

## Problem Statement

### User Pain Points

1. **Thundering Herd During Parallel Fetches**: When fetching 2614+ tasks via ParallelSectionFetcher, the system generates 80+ simultaneous retry warnings. The section-level semaphore (8 concurrent sections) does not constrain HTTP-level pagination, causing:
   - Uncoordinated bursts of requests
   - Rate limiter contention
   - Excessive retry backoff cascades

2. **Uncoordinated Rate Limiting**: Each `AsyncHTTPClient` instance manages its own `TokenBucketRateLimiter`. In concurrent scenarios, the aggregate request rate exceeds Asana's 1500 req/60s limit because limiters are not shared.

3. **Duplicated Infrastructure**: autom8_asana reimplements the same HTTP primitives (rate limiter, retry, circuit breaker) that autom8y-http provides. This creates:
   - Maintenance burden for two implementations
   - Inconsistent behavior across platform services
   - Missing features available in platform SDK (e.g., OpenTelemetry integration)

4. **No HTTP-Level Concurrency Control**: The httpx connection pool allows up to 100 concurrent connections, but the rate limiter operates per-request without awareness of in-flight requests. This creates bursts that overwhelm the token bucket.

### Technical Root Cause

The autom8_asana transport layer was developed before autom8y-http existed. Its architecture assumes a single-client usage pattern where one `AsyncHTTPClient` instance handles all requests sequentially. The parallel fetch pattern breaks this assumption by creating concurrent request flows that exceed the rate limiter's design capacity.

**Current Architecture**:
```
AsanaClient
    |
    +-- AsyncHTTPClient (per-client instance)
            |
            +-- TokenBucketRateLimiter (1500 tokens/60s)
            +-- RetryHandler
            +-- CircuitBreaker
            +-- httpx.AsyncClient (100 connections)
```

**Problem**: ParallelSectionFetcher creates 8+ concurrent section fetches, each triggering paginated requests. With 100+ pages across sections, the rate limiter sees bursts of 50+ concurrent requests.

---

## User Personas

### SDK Consumer

**Role**: Developer using autom8_asana to build automation scripts or analytics dashboards.

**Needs**:
- Reliable parallel fetches without rate limit failures
- Consistent performance regardless of batch size
- Clear error messages when rate limits are approached

**Pain Points**:
- 429 errors during large parallel operations
- Retry warnings obscure other log messages
- Unpredictable fetch times due to backoff cascades

### API Service Operator

**Role**: Engineer operating the autom8_asana-based API service in production.

**Needs**:
- Predictable rate limit utilization
- Circuit breaker protection against Asana outages
- Observability into HTTP-layer behavior

**Pain Points**:
- Rate limit exhaustion during bulk sync operations
- No circuit breaker to prevent cascading failures
- Difficulty correlating log messages to specific request flows

### Platform Team

**Role**: Engineer maintaining autom8y platform SDK libraries.

**Needs**:
- Adoption of shared HTTP primitives across services
- Reduced maintenance of duplicated implementations
- Consistent observability (OpenTelemetry traces)

**Pain Points**:
- Duplicate implementations diverging over time
- Feature requests requiring changes in multiple codebases
- Inconsistent logging formats across services

---

## User Stories

### US-001: Coordinated Rate Limiting

**As a** SDK Consumer
**I want** rate limiting to coordinate across all concurrent requests
**So that** parallel fetches complete without 429 errors

**Acceptance Criteria**:
- [ ] Single TokenBucketRateLimiter shared across all HTTP requests
- [ ] Parallel section fetches (8+ concurrent) stay within 1500 req/60s
- [ ] No 429 responses during 2614-task parallel fetch

### US-002: Reduced Retry Noise

**As an** API Service Operator
**I want** retry warnings reduced to only actionable events
**So that** logs remain useful for debugging

**Acceptance Criteria**:
- [ ] Retry warnings reduced from 80+ to fewer than 10 per bulk operation
- [ ] Proactive rate limiting prevents retries rather than reactive backoff
- [ ] Jitter in backoff prevents synchronized retry storms

### US-003: Circuit Breaker Protection

**As an** API Service Operator
**I want** requests to fail fast when Asana is unavailable
**So that** my service does not cascade failures to its consumers

**Acceptance Criteria**:
- [ ] Circuit breaker opens after consecutive server errors (5xx)
- [ ] Open circuit rejects new requests immediately
- [ ] Half-open state probes for recovery before closing

### US-004: Platform SDK Adoption

**As a** Platform Team Member
**I want** autom8_asana to use autom8y-http for HTTP operations
**So that** platform-wide improvements benefit all services

**Acceptance Criteria**:
- [ ] autom8y-http imported as dependency from CodeArtifact
- [ ] No vendored copies of rate limiter, retry, or circuit breaker
- [ ] HttpClientConfig configures platform client behavior

### US-005: Backward-Compatible Migration

**As a** SDK Consumer
**I want** the migration to be transparent
**So that** I do not need to change my code

**Acceptance Criteria**:
- [ ] AsanaClient API unchanged
- [ ] Sub-client APIs (TasksClient, etc.) unchanged
- [ ] AsanaConfig parameters honored with translation to platform config

### US-006: Escape Hatch for Streaming

**As a** SDK Consumer
**I want** access to streaming responses for large downloads
**So that** I can download attachments without loading into memory

**Acceptance Criteria**:
- [ ] `raw()` escape hatch available for streaming operations
- [ ] Multipart upload still supported
- [ ] Stream response pagination preserved

---

## Functional Requirements

### Must Have

#### FR-001: Replace AsyncHTTPClient with Autom8yHttpClient

The system shall replace `autom8_asana/transport/http.py:AsyncHTTPClient` with a wrapper around `autom8y_http.Autom8yHttpClient`.

The wrapper shall:
- Translate AsanaConfig to HttpClientConfig
- Handle Asana-specific response unwrapping (`{"data": ...}`)
- Preserve the existing public API (`get`, `post`, `put`, `delete`, `get_paginated`)

#### FR-002: Shared Rate Limiter Instance

The system shall use a single `TokenBucketRateLimiter` instance for all HTTP requests within an `AsanaClient` instance.

Configuration:
- max_tokens: 1500 (Asana limit)
- refill_period: 60.0 seconds

#### FR-003: Use Platform Retry Handler

The system shall use `autom8y_http.ExponentialBackoffRetry` for retry logic.

Behavior preserved:
- Retry on status codes: 429, 503, 504
- Exponential backoff with jitter
- Respect Retry-After header

#### FR-004: Use Platform Circuit Breaker

The system shall use `autom8y_http.CircuitBreaker` for cascading failure protection.

Configuration from existing `CircuitBreakerConfig`:
- failure_threshold: 5
- recovery_timeout: 60.0 seconds
- half_open_max_calls: 1

#### FR-005: Preserve Asana Response Handling

The system shall preserve Asana-specific response processing:
- Unwrap `{"data": ...}` envelope
- Parse error responses into domain exceptions (`RateLimitError`, `ServerError`, etc.)
- Extract pagination `next_page.offset`

#### FR-006: Preserve Multipart Upload

The system shall preserve multipart/form-data upload capability for attachment creation.

#### FR-007: Preserve Stream Response

The system shall preserve streaming response capability via escape hatch for:
- Large file downloads
- Attachment content streaming

#### FR-008: Config Translation Layer

The system shall translate existing AsanaConfig hierarchy to platform config:

| AsanaConfig | HttpClientConfig |
|-------------|------------------|
| rate_limit.max_requests | RateLimiterConfig.max_tokens |
| rate_limit.window_seconds | RateLimiterConfig.refill_period |
| retry.max_retries | RetryConfig.max_retries |
| retry.base_delay | RetryConfig.base_delay |
| retry.max_delay | RetryConfig.max_delay |
| retry.exponential_base | RetryConfig.exponential_base |
| retry.jitter | RetryConfig.jitter |
| circuit_breaker.enabled | HttpClientConfig.enable_circuit_breaker |
| circuit_breaker.failure_threshold | CircuitBreakerConfig.failure_threshold |
| circuit_breaker.recovery_timeout | CircuitBreakerConfig.recovery_timeout |
| timeout.* | HttpClientConfig.timeout |
| connection_pool.max_connections | HttpClientConfig.max_connections |

### Should Have

#### FR-009: HTTP-Level Concurrency Control

The system should limit concurrent in-flight HTTP requests to prevent overwhelming the rate limiter.

Suggested approach:
- Use httpx connection pool limits as implicit concurrency control
- Or introduce an HTTP-level semaphore aligned with rate limiter token capacity

#### FR-010: Deprecation Warnings for Direct Transport Access

The system should emit deprecation warnings if external code directly imports from `autom8_asana.transport`.

Exception: `sync_wrapper` remains public utility.

#### FR-011: Observability Integration

The system should preserve logging behavior:
- Request method and path
- Response status codes
- Retry attempts and delays
- Circuit breaker state transitions

### Could Have

#### FR-012: OpenTelemetry Trace Propagation

The system may enable W3C Trace Context propagation via autom8y-http's InstrumentedTransport.

Benefit: End-to-end request tracing from consumer through Asana API.

---

## Non-Functional Requirements

### NFR-001: Performance

| Metric | Target | Current |
|--------|--------|---------|
| Parallel fetch (2614 tasks) | < 30s, no 429s | 45-60s with 429s |
| Single task lookup | < 100ms | < 100ms (no regression) |
| Rate limit utilization | > 90% of 1500/min | ~60% with bursts |

### NFR-002: Reliability

| Metric | Target |
|--------|--------|
| 429 errors during parallel fetch | 0 |
| Retry warnings per bulk operation | < 10 |
| Circuit breaker activation on Asana outage | Within 5 failed requests |

### NFR-003: Compatibility

| Aspect | Requirement |
|--------|-------------|
| AsanaClient public API | 100% compatible |
| Sub-client public APIs | 100% compatible |
| Existing tests | All pass |
| Error exception types | Preserved |

### NFR-004: Dependencies

| Dependency | Requirement |
|------------|-------------|
| autom8y-http | >= 0.2.0 via CodeArtifact |
| httpx | Transitive via autom8y-http |
| Python | >= 3.11 (match existing) |

---

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| autom8y-http not installed | ImportError with clear message |
| Rate limiter exhausted during parallel fetch | Wait for tokens, no immediate retry |
| Circuit breaker opens mid-fetch | Reject remaining requests, fast-fail |
| Retry-After header exceeds max_delay | Cap at max_delay |
| Stream response rate limited | Apply rate limiting per chunk request |
| Concurrent AsanaClient instances | Each has own rate limiter (per-client isolation) |
| Auth token refresh during request | Handled by auth_provider, not HTTP layer |

---

## Success Criteria

- [ ] **SC-001**: Parallel fetch test with 2614 tasks completes with 0 rate limit errors
- [ ] **SC-002**: Single rate limiter instance verified via dependency injection test
- [ ] **SC-003**: Existing integration tests pass without modification
- [ ] **SC-004**: Retry warning count measured via log capture during parallel fetch
- [ ] **SC-005**: `pytest` full suite passes
- [ ] **SC-006**: Circuit breaker integration test simulates Asana outage
- [ ] **SC-007**: `pyproject.toml` lists autom8y-http as dependency

---

## Out of Scope

| Item | Rationale |
|------|-----------|
| WebSocket support | Asana API is REST-only |
| GraphQL transport | Not needed for current use cases |
| Multiple rate limiter pools | Single-client pattern sufficient |
| Distributed rate limiting (Redis) | Single-instance deployment |
| OAuth token refresh | Handled by auth_provider, orthogonal to transport |
| Custom DNS resolution | Not required by current infrastructure |

---

## Migration Phases

### Phase 1: Infrastructure Setup
- Add autom8y-http dependency to pyproject.toml
- Configure CodeArtifact access in CI

### Phase 2: Transport Wrapper
- Create `AsanaHttpClient` wrapper around `Autom8yHttpClient`
- Implement config translation layer
- Preserve Asana response unwrapping

### Phase 3: Integration
- Wire `AsanaHttpClient` into `AsanaClient.__init__`
- Update sub-clients to use shared HTTP instance
- Verify ParallelSectionFetcher uses coordinated rate limiting

### Phase 4: Validation
- Run parallel fetch benchmark (2614 tasks)
- Measure retry warning count
- Execute full test suite

### Phase 5: Deprecation
- Add deprecation warnings to direct transport imports
- Update documentation
- Archive replaced transport modules

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| autom8y-http >= 0.2.0 | Available | CodeArtifact registry |
| TokenBucketRateLimiter | In autom8y-http | Platform implementation |
| ExponentialBackoffRetry | In autom8y-http | Platform implementation |
| CircuitBreaker | In autom8y-http | Platform implementation |
| HttpClientConfig | In autom8y-http | Pydantic Settings config |
| AsanaConfig | Existing | Translation layer needed |
| ParallelSectionFetcher | Existing | Validates rate limit coordination |

---

## Open Questions

| Question | Status | Resolution |
|----------|--------|------------|
| Should transport.py be deleted or deprecated? | Resolved | Deprecate with warning, then delete in next major version |
| Per-client or global rate limiter? | Resolved | Per-client (AsanaClient instance scope) |
| How to handle Asana-specific error parsing? | Resolved | Wrapper layer handles response transformation |

---

## Appendix A: Component Mapping

### Current Components (autom8_asana/transport/)

| Component | Role | Platform Replacement |
|-----------|------|---------------------|
| `http.py:AsyncHTTPClient` | HTTP requests | `Autom8yHttpClient` |
| `rate_limiter.py:TokenBucketRateLimiter` | Rate limiting | `autom8y_http.TokenBucketRateLimiter` |
| `retry.py:RetryHandler` | Retry with backoff | `autom8y_http.ExponentialBackoffRetry` |
| `circuit_breaker.py:CircuitBreaker` | Failure protection | `autom8y_http.CircuitBreaker` |
| `sync.py:sync_wrapper` | Sync/async bridge | Preserved (utility) |

### New Wrapper Component

```
autom8_asana/transport/asana_http.py
    |
    +-- AsanaHttpClient
            |
            +-- Wraps Autom8yHttpClient
            +-- Handles {"data": ...} unwrapping
            +-- Parses Asana error responses
            +-- Provides get_paginated() method
```

---

## Appendix B: Config Translation Example

```python
# Current AsanaConfig usage
config = AsanaConfig(
    rate_limit=RateLimitConfig(max_requests=1200, window_seconds=60),
    retry=RetryConfig(max_retries=5, jitter=True),
    circuit_breaker=CircuitBreakerConfig(enabled=True),
)

# Translated to platform config
http_config = HttpClientConfig(
    base_url="https://app.asana.com/api/1.0",
    timeout=30.0,
    max_connections=100,
    enable_rate_limiting=True,
    enable_retry=True,
    enable_circuit_breaker=True,
)

rate_config = RateLimiterConfig(
    max_tokens=1200,
    refill_period=60.0,
)

retry_config = RetryConfig(
    max_retries=5,
    jitter=True,
)
```

---

## Appendix C: Parallel Fetch Flow (After Migration)

```
ParallelSectionFetcher.fetch_all()
    |
    +-- asyncio.Semaphore(8)  # Section-level concurrency
    |
    +-- Section 1-8 (concurrent)
            |
            +-- TasksClient.list_async()
                    |
                    +-- AsanaHttpClient.get_paginated()
                            |
                            +-- Autom8yHttpClient._request()
                                    |
                                    +-- TokenBucketRateLimiter.acquire()  # SHARED
                                    +-- ExponentialBackoffRetry.wait()
                                    +-- CircuitBreaker.check()
                                    +-- httpx.AsyncClient.request()
```

**Key Difference**: Single `TokenBucketRateLimiter` shared across all paginated requests prevents burst accumulation.

---

**End of PRD**
