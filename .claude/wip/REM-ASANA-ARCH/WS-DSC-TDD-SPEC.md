# TDD: WS-DSC -- DataServiceClient Execution Policy Abstraction

## Overview

Extract the repeated 8-step orchestration scaffold from the 5 DataServiceClient endpoint modules (`simple.py`, `batch.py`, `insights.py`, `export.py`, `reconciliation.py`) into a reusable `EndpointPolicy` protocol and `DefaultEndpointPolicy` implementation. This eliminates ~280 LOC of near-identical boilerplate while preserving every endpoint's behavioral contract (error types, metric tags, cache interactions, response shapes).

## Context

- **PRD/Initiative**: R-008 (Remediation -- DataServiceClient execution policy consolidation)
- **Prior Art**: `_retry.py` already extracted the retry *callback factory* (7 variation axes). This work extracts the *orchestration scaffold* that calls those callbacks.
- **System Context**: `system_context.py` uses a registration pattern (`register_reset()`). DSC singletons do not currently register; if they ever do, they should use `register_reset()` -- but that is out of scope here.
- **Guardrails**: See PROMPT_0.md items 1--9. Key constraints: do NOT modify `_retry.py` callback factory, do NOT change response shapes or error types, do NOT remove `client.py:_execute_with_retry()` until all endpoints migrate.

---

## 1. Orchestration Pattern Analysis

### 1.1 The 8-Step Pattern

Every endpoint in `_endpoints/` follows the same high-level scaffold. The steps are numbered below as they appear in the source code flow:

| # | Step | Description |
|---|------|-------------|
| S1 | **Pre-flight** | Feature check, request ID generation, PII masking, start logging |
| S2 | **Circuit breaker check** | `await client._circuit_breaker.check()` -- catch `SdkCircuitBreakerOpenError`, raise domain error |
| S3 | **Acquire HTTP client** | `http_client = await client._get_client()` |
| S4 | **Build retry callbacks** | `_retry_mod.build_retry_callbacks(...)` |
| S5 | **Execute with retry** | `await client._execute_with_retry(make_request, ...)` -- may catch service errors for stale fallback |
| S6 | **Handle error response** | `if response.status_code >= 400` -- delegate to error handler or inline error mapping |
| S7 | **Parse success response** | `client._parse_success_response(response, request_id)` or custom JSON parsing |
| S8 | **Record success + emit metrics** | `await client._circuit_breaker.record_success()`, log completion, emit metrics, cache response |

### 1.2 Per-Endpoint Variation Matrix

| Variation Axis | simple (appts) | simple (leads) | reconciliation | export | insights | batch |
|---|---|---|---|---|---|---|
| **S1: Pre-flight** | `_check_feature_enabled()`, uuid, mask | Same | Same | mask only (no feature check) | Feature check done by caller; receives request_id | No feature check; receives request_id |
| **S2: CB error class** | `InsightsServiceError` | Same | Same | `ExportError` | `InsightsServiceError` | Returns error results dict (no raise) |
| **S2: CB error kwargs** | `request_id=, reason=` | Same | Same | `office_phone=, reason=` | `request_id=, reason=` | N/A (builds error dict per PVP) |
| **S3: HTTP method** | GET | GET | POST (json body) | GET (Accept: text/csv) | POST (json body) | POST (json body) |
| **S4: Retry callback args** | Minimal (no log/metric) | Same | Same | Minimal (ExportError) | Full (log, metric, start_time) | Full (log, extra_log_context) |
| **S5: Execute-with-retry callbacks** | `on_timeout_exhausted`, `on_http_error` only | Same | Same | Same (no on_retry) | `on_retry`, `on_timeout_exhausted`, `on_http_error` | Same as insights + try/except for total failure |
| **S5: Stale cache fallback** | No | No | No | No | Yes (`_get_stale_response` in except) | No |
| **S6: Error handler** | `client._handle_error_response()` | Same | Same | Inline (ExportError raise) | `client._handle_error_response()` | Inline (batch error dict) |
| **S7: Response parser** | `client._parse_success_response()` | Same | Same | Custom (CSV headers) | `client._parse_success_response()` | Custom (batch JSON grouping) |
| **S8: Success metrics** | No explicit metrics | Same | Same | No explicit metrics | `_emit_metric()` x2 | Completion log only |
| **S8: Cache write** | No | No | No | No | `_cache_response()` | No |
| **S8: Log format** | Module-level `logger.info(event, **kwargs)` | Same | Same | `client._log.info(event, extra={})` | `client._log.info(event, extra={})` | `client._log.info(event, extra={})` |
| **Response type** | `InsightsResponse` | Same | Same | `ExportResult` | `InsightsResponse` | `dict[str, BatchInsightsResult]` |

### 1.3 Key Observations

1. **S2--S5 are nearly identical** across all 5 modules. The only variations are: (a) error class in the circuit breaker catch, (b) HTTP method/path/headers, (c) retry callback configuration, (d) whether `on_retry` is provided.

2. **S6 diverges significantly**: `simple` and `reconciliation` use the shared `_handle_error_response()`. `insights` uses the same but adds stale fallback. `export` and `batch` have completely custom error handling.

3. **S7 diverges completely** for `export` (CSV header parsing) and `batch` (multi-PVP JSON grouping). `simple`, `reconciliation`, and `insights` share `_parse_success_response()`.

4. **S1 and S8 are endpoint-specific bookends** (logging, metrics, caching) that vary by endpoint but are not part of the core orchestration.

5. **The core extractable scaffold is S2 through S5** -- the "circuit-breaker-check -> get-client -> build-callbacks -> execute-with-retry" sequence. S6-S7-S8 can be abstracted as pluggable post-execution strategies.

---

## 2. EndpointPolicy Protocol

### 2.1 Design Rationale

The protocol abstracts the orchestration scaffold (S2--S8) while leaving S1 (pre-flight) to each endpoint function. The caller provides:
- How to build the HTTP request (method, path, params/body, headers)
- How to build retry callbacks
- How to handle errors
- How to parse the success response

The policy owns:
- Circuit breaker check + error wrapping
- HTTP client acquisition
- Timing
- Retry execution loop
- Post-execution dispatch (error vs success path)
- Circuit breaker success recording

### 2.2 Protocol Definition

```python
"""Execution policy protocol for DataServiceClient endpoints.

Abstracts the 8-step orchestration scaffold into a reusable protocol.
"""
from __future__ import annotations

from typing import Generic, Protocol, TypeVar, runtime_checkable

T_contra = TypeVar("T_contra", contravariant=True)  # Request descriptor
R_co = TypeVar("R_co", covariant=True)              # Response type


@runtime_checkable
class EndpointPolicy(Protocol[T_contra, R_co]):
    """Protocol for endpoint execution policies.

    Encapsulates the circuit-breaker -> retry -> error-handling -> parse
    pipeline. Endpoints provide a request descriptor; the policy returns
    the parsed response.

    Type Parameters:
        T_contra: Request descriptor type (contravariant).
            Contains everything needed to build the HTTP request.
        R_co: Parsed response type (covariant).
            The final domain object returned to the caller.
    """

    async def execute(self, request: T_contra) -> R_co:
        """Execute the endpoint pipeline.

        Args:
            request: Endpoint-specific request descriptor.

        Returns:
            Parsed domain response.

        Raises:
            Domain-specific errors (InsightsServiceError, ExportError, etc.)
        """
        ...
```

### 2.3 Why Protocol (Not ABC)

| Criterion | Protocol | ABC |
|-----------|----------|-----|
| Structural typing | Yes -- no inheritance required | No -- forces class hierarchy |
| Testability | Mock anything matching the shape | Must subclass |
| Existing code | Endpoints are free functions, not classes | Would require wrapping |
| Python ecosystem | Matches `LogProvider`, `CacheProvider` pattern in this codebase | Foreign to this codebase's style |

**Decision**: Protocol. Consistent with existing codebase conventions (`protocols/` package).

---

## 3. Request Descriptor Types

Each endpoint needs a request descriptor that bundles everything the policy needs to build and execute the HTTP request. These are simple frozen dataclasses.

### 3.1 Common Fields (Not Extracted to Base)

Rather than a shared base descriptor, each endpoint defines its own descriptor. Rationale: the fields differ enough that a shared base would be mostly empty, adding inheritance without value.

```python
from dataclasses import dataclass
from typing import Any

from autom8_asana.clients.data._retry import RetryCallbacks


@dataclass(frozen=True, slots=True)
class SimpleRequestDescriptor:
    """Descriptor for simple GET endpoints (appointments, leads)."""
    path: str
    params: dict[str, str]
    request_id: str
    # For error handling:
    cache_key: str
    factory_label: str  # e.g., "appointments", "leads"
    # Pre-built by the endpoint function:
    retry_callbacks: RetryCallbacks


@dataclass(frozen=True, slots=True)
class InsightsRequestDescriptor:
    """Descriptor for POST /data-service/insights."""
    path: str
    request_body: dict[str, Any]
    request_id: str
    cache_key: str
    factory: str
    # Pre-built by the endpoint function:
    retry_callbacks: RetryCallbacks


@dataclass(frozen=True, slots=True)
class ExportRequestDescriptor:
    """Descriptor for GET /messages/export."""
    path: str
    params: dict[str, str]
    masked_phone: str
    # Pre-built by the endpoint function:
    retry_callbacks: RetryCallbacks


@dataclass(frozen=True, slots=True)
class BatchRequestDescriptor:
    """Descriptor for POST /data-service/insights (batch)."""
    path: str
    request_body: dict[str, Any]
    request_id: str
    pvp_list: list  # list[PhoneVerticalPair]
    pvp_by_key: dict[str, Any]  # dict[str, PhoneVerticalPair]
    # Pre-built by the endpoint function:
    retry_callbacks: RetryCallbacks
```

### 3.2 Why Retry Callbacks Are Pre-Built

The endpoint function builds `RetryCallbacks` via `_retry_mod.build_retry_callbacks()` before calling `policy.execute()`. This keeps the retry callback factory untouched (guardrail 6) and keeps endpoint-specific callback configuration (error messages, metric tags, log events) in the endpoint function where it belongs.

---

## 4. DefaultEndpointPolicy Implementation Strategy

### 4.1 Architecture

```
EndpointPolicy[T, R]          (Protocol -- in protocols/ or clients/data/)
    |
DefaultEndpointPolicy[T, R]   (Concrete -- in clients/data/_policy.py)
    |
    +-- __init__(circuit_breaker, get_client, execute_with_retry,
    |            cb_error_factory, request_builder, error_handler,
    |            success_handler)
    |
    +-- execute(request: T) -> R
            S2: circuit_breaker.check()  -- catch -> cb_error_factory(e, request)
            S3: get_client()
            start_time = monotonic()
            S4-S5: execute_with_retry(request_builder(client, request), callbacks)
            elapsed_ms = ...
            if error response:
                S6: return error_handler(response, request, elapsed_ms)
            S7-S8: return success_handler(response, request, elapsed_ms)
```

### 4.2 Constructor Parameters

```python
from __future__ import annotations

import time
from typing import Any, Callable, Generic, TypeVar

from autom8y_http import CircuitBreaker, CircuitBreakerOpenError, Response

T = TypeVar("T")  # Request descriptor
R = TypeVar("R")  # Response type


class DefaultEndpointPolicy(Generic[T, R]):
    """Default implementation of the endpoint execution policy.

    Encapsulates steps S2--S8 of the orchestration scaffold.
    Endpoint-specific behavior is injected via constructor callables.
    """

    def __init__(
        self,
        *,
        # Infrastructure (shared across all endpoints on one client)
        circuit_breaker: CircuitBreaker,
        get_client: Callable[[], Any],     # async () -> Autom8yHttpClient
        execute_with_retry: Callable[..., Any],  # client._execute_with_retry

        # Endpoint-specific pluggable behaviors
        cb_error_factory: Callable[[CircuitBreakerOpenError, T], Exception],
        request_builder: Callable[[Any, T], Any],  # (http_client, descriptor) -> coroutine
        error_handler: Callable[[Response, T, float], Any],   # async/sync
        success_handler: Callable[[Response, T, float], Any], # async/sync
    ) -> None:
        self._circuit_breaker = circuit_breaker
        self._get_client = get_client
        self._execute_with_retry = execute_with_retry
        self._cb_error_factory = cb_error_factory
        self._request_builder = request_builder
        self._error_handler = error_handler
        self._success_handler = success_handler

    async def execute(self, request: T) -> R:
        """Execute the endpoint pipeline."""
        # S2: Circuit breaker check
        try:
            await self._circuit_breaker.check()
        except CircuitBreakerOpenError as e:
            raise self._cb_error_factory(e, request) from e

        # S3: Acquire HTTP client
        http_client = await self._get_client()

        # Timing
        start_time = time.monotonic()

        # S4-S5: Execute with retry
        # request_builder returns the lambda for make_request
        # Callbacks are on the request descriptor
        response, _attempt = await self._execute_with_retry(
            self._request_builder(http_client, request),
            on_retry=getattr(request, 'retry_callbacks', None)
                     and request.retry_callbacks.on_retry,
            on_timeout_exhausted=request.retry_callbacks.on_timeout_exhausted,
            on_http_error=request.retry_callbacks.on_http_error,
        )

        elapsed_ms = (time.monotonic() - start_time) * 1000

        # S6: Error path
        if response.status_code >= 400:
            return await self._error_handler(response, request, elapsed_ms)

        # S7-S8: Success path
        return await self._success_handler(response, request, elapsed_ms)
```

### 4.3 Pluggable Behavior Summary

| Plug Point | What It Does | Why Pluggable |
|------------|-------------|---------------|
| `cb_error_factory` | Converts `CircuitBreakerOpenError` to domain error | `InsightsServiceError` vs `ExportError` vs batch error-dict |
| `request_builder` | Builds `make_request` lambda from http_client + descriptor | GET vs POST, different paths/params/headers |
| `error_handler` | Maps error response to domain result | `_handle_error_response` vs inline `ExportError` vs batch error-dict |
| `success_handler` | Parses success response + records metrics/cache | `_parse_success_response` vs CSV header parsing vs batch JSON grouping |

### 4.4 Handling the Insights Stale-Fallback Special Case

The `insights` endpoint wraps the `execute_with_retry` call in a `try/except InsightsServiceError` to attempt stale cache fallback. This is the only endpoint with this behavior.

**Design**: The `execute_with_retry_wrapper` plug point (optional) allows insights to inject a wrapper around the S4-S5 call:

```python
# Option A (Recommended): Stale fallback in error_handler
# The error_handler for insights already receives the response. For the
# stale fallback case (where execute_with_retry raises before returning
# a response), we use a pre_execute_error_handler:

class DefaultEndpointPolicy(Generic[T, R]):
    def __init__(
        self,
        *,
        # ... existing params ...
        pre_execute_error_handler: Callable[[Exception, T], R | None] | None = None,
    ) -> None:
        # ...
        self._pre_execute_error_handler = pre_execute_error_handler

    async def execute(self, request: T) -> R:
        # S2, S3 as before...

        start_time = time.monotonic()

        # S4-S5: Execute with retry
        try:
            response, _attempt = await self._execute_with_retry(...)
        except Exception as e:
            if self._pre_execute_error_handler is not None:
                result = self._pre_execute_error_handler(e, request)
                if result is not None:
                    return result
            raise

        # S6, S7-S8 as before...
```

For insights, `pre_execute_error_handler` would be:

```python
def insights_stale_fallback(e: Exception, request: InsightsRequestDescriptor):
    if isinstance(e, InsightsServiceError):
        stale = client._get_stale_response(request.cache_key, request.request_id)
        if stale is not None:
            return stale
    return None  # re-raise
```

### 4.5 Handling the Batch Circuit-Breaker Special Case

The `batch` endpoint does NOT raise on circuit breaker open -- it returns an error dict for all PVPs. This is handled by `cb_error_factory` returning a sentinel or by restructuring:

**Design**: `cb_error_factory` for batch returns a `BatchCircuitBreakerResult` that `execute()` detects:

```python
# In batch's cb_error_factory:
def batch_cb_error_factory(e, request):
    # Return the error dict directly -- batch never raises on CB
    results = {}
    for pvp in request.pvp_list:
        results[pvp.canonical_key] = BatchInsightsResult(
            pvp=pvp,
            error=f"Circuit breaker open. Retry in {e.time_remaining:.1f}s.",
        )
    return _BatchShortCircuit(results)
```

However, raising from `cb_error_factory` is the normal path. For batch, we instead override the circuit breaker check behavior. Two options:

**Option A**: Batch provides its own `execute()` override (subclass or separate policy).
**Option B**: `cb_error_factory` is allowed to return a result (non-exception) that short-circuits.

**Decision**: Option B via a lightweight sentinel pattern. `cb_error_factory` returns `R | raises`. If it returns (rather than raising), `execute()` returns that value immediately:

```python
async def execute(self, request: T) -> R:
    try:
        await self._circuit_breaker.check()
    except CircuitBreakerOpenError as e:
        result_or_raise = self._cb_error_factory(e, request)
        # If cb_error_factory returns instead of raising, treat as early return
        return result_or_raise  # type: ignore[return-value]
    # ... rest of pipeline
```

For non-batch endpoints, `cb_error_factory` raises. For batch, it returns the error dict. This avoids subclassing.

---

## 5. Key Design Decisions (ADRs)

### ADR-DSC-001: Generic Type Parameters

**Context**: The 5 endpoints return different types (`InsightsResponse`, `ExportResult`, `dict[str, BatchInsightsResult]`). The policy must be type-safe.

**Decision**: Use `Generic[T, R]` where `T` is the request descriptor (contravariant in protocol) and `R` is the response type (covariant in protocol). Each endpoint instantiates the policy with concrete types.

**Alternatives Considered**:
- **A. Untyped `Any`**: Simple but loses type safety. Rejected: defeats purpose of protocol.
- **B. Union return type**: `InsightsResponse | ExportResult | dict`. Rejected: forces callers to narrow.
- **C. Generic[T, R]** (chosen): Each endpoint gets its own parameterized policy instance. Type-safe, no narrowing needed.

**Consequences**: Each endpoint needs its own descriptor dataclass. This is acceptable -- they already have unique parameter sets.

### ADR-DSC-002: Error Mapping Plugin Design

**Context**: Error handling diverges significantly across endpoints: `_handle_error_response()` (shared), inline `ExportError`, inline batch error-dict.

**Decision**: Two plug points: `error_handler` for HTTP error responses (status >= 400) and `pre_execute_error_handler` for exceptions raised during `execute_with_retry` (used only by insights for stale fallback).

**Alternatives Considered**:
- **A. Single error handler**: Cannot handle the insights stale-fallback case where `execute_with_retry` raises before returning a response.
- **B. Template method (override in subclass)**: Requires class hierarchy per endpoint. Rejected: endpoints are free functions.
- **C. Two handlers** (chosen): `error_handler` for response errors, `pre_execute_error_handler` for execution exceptions. Clean separation.

**Consequences**: `pre_execute_error_handler` is `None` for 4 of 5 endpoints. The `None` check adds ~2 LOC to `execute()`.

### ADR-DSC-003: Circuit Breaker Injection vs Inheritance

**Context**: Circuit breaker is always `client._circuit_breaker`. Should the policy own it or receive it?

**Decision**: Injection via constructor parameter. The policy receives the `CircuitBreaker` instance.

**Alternatives Considered**:
- **A. Policy accesses `client._circuit_breaker`**: Couples policy to client internals. Rejected.
- **B. Policy creates its own circuit breaker**: Wrong -- all endpoints share one circuit breaker per client. Rejected.
- **C. Injection** (chosen): Policy receives the instance. Enables testing with mock circuit breakers.

**Consequences**: Caller must pass circuit breaker at construction time. This is already the pattern in `build_retry_callbacks()`.

### ADR-DSC-004: Metrics Parameterization

**Context**: Only `insights` emits post-success metrics via `_emit_metric()`. `simple`, `reconciliation`, and `export` do not. Batch emits batch-level metrics in the caller.

**Decision**: Metrics emission is part of `success_handler`, not the policy. The `success_handler` callable for each endpoint includes whatever metric emission that endpoint needs.

**Alternatives Considered**:
- **A. Policy emits metrics with configurable tags**: Over-generalizes. Most endpoints don't emit metrics from the policy layer.
- **B. success_handler includes metrics** (chosen): Keeps metrics logic in the endpoint where it already lives. No abstraction tax for endpoints without metrics.

**Consequences**: The `success_handler` for insights is slightly larger than a pure parser. Acceptable -- it was already doing this work.

### ADR-DSC-005: Retry Configuration Surface

**Context**: Retry callbacks are already factored into `_retry.py`. The policy needs them but should not rebuild them.

**Decision**: Retry callbacks are pre-built by the endpoint function and placed on the request descriptor. The policy reads `request.retry_callbacks` to wire into `execute_with_retry`.

**Alternatives Considered**:
- **A. Policy builds callbacks internally**: Violates guardrail 6 (do not modify `_retry.py`). Also couples policy to callback factory signature.
- **B. Callbacks passed as separate execute() args**: Less cohesive -- callbacks are request-scoped, not call-scoped.
- **C. Callbacks on descriptor** (chosen): Natural home. Built by endpoint function, consumed by policy. Zero changes to `_retry.py`.

**Consequences**: Every descriptor type must have a `retry_callbacks: RetryCallbacks` field. This is enforced by convention (not type-checked by the policy protocol). A `HasRetryCallbacks` protocol could enforce this if desired.

---

## 6. File Layout

```
src/autom8_asana/clients/data/
    _policy.py                    # NEW: DefaultEndpointPolicy + descriptors
    _retry.py                     # UNCHANGED (guardrail 6)
    _endpoints/
        __init__.py               # UNCHANGED
        simple.py                 # MODIFIED: uses policy
        reconciliation.py         # MODIFIED: uses policy
        export.py                 # MODIFIED: uses policy
        insights.py               # MODIFIED: uses policy
        batch.py                  # MODIFIED: uses policy (last)
    client.py                     # _execute_with_retry RETAINED (guardrail 9)
```

The protocol definition (`EndpointPolicy`) goes in `_policy.py` alongside the implementation, NOT in `protocols/`. Rationale: this protocol is private to `clients/data/` and not consumed outside the package.

---

## 7. Migration Order Rationale

### 7.1 Order: simple -> reconciliation -> export -> insights -> batch

| Order | Endpoint | Why This Position |
|-------|----------|-------------------|
| 1 | **simple** (appointments + leads) | Textbook 8-step pattern. No custom error handling, no custom parsing, no metrics, no cache. Two functions share identical structure -- perfect for validating the policy works. |
| 2 | **reconciliation** | Nearly identical to simple. POST instead of GET. Validates HTTP method variation. |
| 3 | **export** | Different error class (`ExportError`), different response type (`ExportResult`), custom response parsing (CSV headers). Tests that the policy handles non-InsightsResponse return types and custom error mapping. |
| 4 | **insights** | Adds stale cache fallback (`pre_execute_error_handler`), metrics emission, cache write. Most complex use of shared infrastructure. Tests the optional plug points. |
| 5 | **batch** | Most divergent endpoint. Circuit breaker returns error dict (no raise). Custom error handling (batch partial failures, HTTP 207). Custom response parsing (multi-PVP JSON grouping). PII masking in error paths. Migrated last because it may require policy refinements discovered during 1--4. |

### 7.2 Difficulty Progression

| Endpoint | Difficulty | New Policy Features Exercised |
|----------|-----------|-------------------------------|
| simple | Low | Core pipeline only |
| reconciliation | Low | POST body variation |
| export | Medium | Different error class, custom response parser, different return type |
| insights | Medium-High | pre_execute_error_handler, metrics, caching |
| batch | High | Non-raising CB handler, batch error aggregation, HTTP 207, PII masking |

---

## 8. Before/After LOC Estimates

### 8.1 Current Orchestration LOC (S2--S8 only, excluding S1 pre-flight)

| Endpoint | File | Orchestration LOC | Notes |
|----------|------|------------------:|-------|
| simple (get_appointments) | simple.py:68--126 | 58 | S2-S8 |
| simple (get_leads) | simple.py:174--234 | 60 | S2-S8 (nearly identical) |
| reconciliation | reconciliation.py:70--133 | 63 | S2-S8 |
| export | export.py:73--173 | 100 | S2-S8 + custom error/parse |
| insights | insights.py:67--219 | 152 | S2-S8 + stale fallback + metrics + cache |
| batch | batch.py:69--261 | 192 | S2-S8 + batch error handling + JSON grouping |
| **Total** | | **625** | |

### 8.2 Post-Migration LOC

| Component | LOC | Notes |
|-----------|----:|-------|
| `_policy.py` (policy + descriptors) | ~120 | DefaultEndpointPolicy (~60) + 4 descriptors (~15 each) |
| simple (get_appointments) | ~25 | S1 + build descriptor + `policy.execute()` + completion log |
| simple (get_leads) | ~28 | Same pattern |
| reconciliation | ~28 | Same pattern |
| export | ~45 | S1 + descriptor + policy + custom success_handler definition |
| insights | ~55 | S1 + descriptor + policy + stale fallback + metrics/cache handlers |
| batch | ~100 | S1 + descriptor + policy + batch-specific handlers (grouping, 207) |
| **Total** | **~401** | |

### 8.3 Net Reduction

| Metric | Value |
|--------|------:|
| Before (orchestration only) | 625 LOC |
| After (policy + migrated endpoints) | ~401 LOC |
| **Net reduction** | **~224 LOC (36%)** |
| New abstraction overhead (_policy.py) | ~120 LOC |
| Net endpoint LOC reduction | ~344 LOC |

The real value is not raw LOC reduction but **duplication elimination** -- the 5 copies of S2-S5 become 1.

---

## 9. Test Strategy

### 9.1 Policy Unit Tests (New: `tests/unit/clients/data/test_policy.py`)

Test `DefaultEndpointPolicy` in isolation with mock plug points:

| Test Case | Description |
|-----------|-------------|
| `test_execute_happy_path` | Mock CB passes, mock execute_with_retry returns 200, success_handler called |
| `test_execute_circuit_breaker_open_raises` | CB check raises, cb_error_factory raises domain error |
| `test_execute_circuit_breaker_open_returns` | CB check raises, cb_error_factory returns (batch case) |
| `test_execute_error_response` | execute_with_retry returns 500, error_handler called |
| `test_execute_pre_execute_error_handler_returns` | execute_with_retry raises, pre_execute_error_handler returns stale |
| `test_execute_pre_execute_error_handler_none_reraises` | pre_execute_error_handler returns None, original error re-raised |
| `test_execute_timing` | Verify elapsed_ms passed to handlers is reasonable |

### 9.2 Migrated Endpoint Tests (Modify Existing)

Existing test files in `tests/unit/clients/data/` already cover endpoint behavior:
- `test_client.py` -- general client tests
- `test_insights.py` -- insights-specific tests
- `test_batch.py` -- batch-specific tests
- `test_export.py` -- export-specific tests
- `test_circuit_breaker.py` -- CB integration
- `test_retry.py` -- retry behavior
- `test_cache.py` -- cache fallback

**Migration verification approach**:
1. Run ALL existing tests before migration -- record pass count.
2. After each endpoint migration, run ALL existing tests -- same pass count, zero regressions.
3. Do NOT modify existing test assertions. If a test breaks, the migration introduced a behavior change.

### 9.3 Integration Smoke Test

After all 5 endpoints are migrated, add one integration-level test that:
1. Creates a `DataServiceClient` with mock HTTP responses.
2. Calls each of the 5 endpoint methods.
3. Verifies the response shape is unchanged.
4. Verifies circuit breaker interactions are unchanged.

---

## 10. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | Batch endpoint is too divergent for the policy | Medium | Medium | Batch is migrated last. If the policy cannot accommodate it cleanly, batch keeps its current implementation (policy covers 4/5 endpoints, still a win). |
| R2 | `_execute_with_retry` callback wiring breaks subtly | Low | High | Existing tests cover all callback paths. Zero changes to `_execute_with_retry` or `_retry.py`. |
| R3 | Type annotations become unwieldy with generics | Medium | Low | Descriptors are simple frozen dataclasses. If types become too complex, relax to `Any` at the policy boundary (internal module, not public API). |
| R4 | Pre-execute error handler (stale fallback) is hard to test | Low | Medium | Dedicated test case in policy unit tests. Existing `test_cache.py` covers the stale fallback behavior end-to-end. |
| R5 | Performance regression from indirection | Very Low | Low | Single async call overhead is negligible vs HTTP round-trip. No measurable impact. |
| R6 | Circular imports between `_policy.py` and `client.py` | Medium | Medium | Policy receives callables (lambdas/bound methods) at construction time, not module imports. Descriptor types import only from `_retry.py` (already imported by all endpoints). |
| R7 | Future endpoints don't fit the policy | Low | Low | Policy is opt-in. New endpoints can use it or not. The protocol is flexible enough for most patterns. |

---

## 11. Implementation Sequence (Per-Session Plan)

### Session 2: Scaffold + Simple Migration
1. Create `_policy.py` with `DefaultEndpointPolicy` and `SimpleRequestDescriptor`.
2. Migrate `simple.py` (both `get_appointments` and `get_leads`).
3. Run all tests -- zero regressions.

### Session 3: Reconciliation + Export Migration
1. Add `ReconciliationRequestDescriptor` (or reuse `SimpleRequestDescriptor` -- same shape).
2. Migrate `reconciliation.py`.
3. Add `ExportRequestDescriptor`.
4. Migrate `export.py` with custom success_handler.
5. Run all tests -- zero regressions.

### Session 4: Insights Migration
1. Add `InsightsRequestDescriptor`.
2. Implement `pre_execute_error_handler` for stale fallback.
3. Migrate `insights.py`.
4. Run all tests -- zero regressions.

### Session 5: Batch Migration
1. Add `BatchRequestDescriptor`.
2. Implement non-raising `cb_error_factory`.
3. Migrate `batch.py` with custom error/success handlers.
4. Run all tests -- zero regressions.
5. Integration smoke test.

### Session 6: Cleanup
1. Verify `_execute_with_retry` has no direct callers outside migrated endpoints.
2. If safe, add deprecation comment to `_execute_with_retry` (do NOT remove per guardrail 9).
3. Final test pass.

---

## 12. Guardrail Compliance Matrix

| Guardrail | Compliant | Notes |
|-----------|-----------|-------|
| G1: Do NOT decompose SaveSession | Yes | SaveSession not touched |
| G2: Do NOT re-open cache divergence | Yes | Cache behavior unchanged |
| G3: Do NOT pursue full pipeline consolidation | Yes | Scope limited to execution policy |
| G4: Do NOT convert deferred imports wholesale | Yes | Deferred import pattern preserved |
| G5: Do NOT modify automation/seeding.py | Yes | Not touched |
| G6: Do NOT change _retry.py callback factory | Yes | `_retry.py` unchanged; callbacks pre-built by endpoints |
| G7: Do NOT modify circuit breaker logic | Yes | CB only invoked, not modified |
| G8: Do NOT change response shapes or error types | Yes | All return types and exception types preserved |
| G9: Do NOT remove _execute_with_retry during transition | Yes | Retained; deprecation comment only after full migration |

---

## Checkpoint WS-DSC Session 1 [2026-02-23]

**Completed**:
- Full source analysis of all 5 endpoint modules, `_retry.py`, `client.py`, supporting modules
- 8-step orchestration pattern identification and documentation
- Per-endpoint variation matrix (12 axes x 6 endpoints)
- `EndpointPolicy` protocol design with generic type parameters
- `DefaultEndpointPolicy` implementation strategy with 5 plug points
- Request descriptor types for all 5 endpoints
- 5 ADRs: generic params, error mapping, CB injection, metrics, retry config
- Migration order rationale with difficulty progression
- Before/after LOC estimates (625 -> ~401, 36% reduction)
- Test strategy (policy unit tests + regression verification + smoke test)
- Risk register (7 risks with mitigations)
- 5-session implementation plan
- Guardrail compliance matrix (all 9 guardrails verified)

**Remaining**:
- Implementation Sessions 2--6 (principal-engineer scope)
- Policy unit test implementation
- Integration smoke test
- Deprecation comment on `_execute_with_retry` (post-migration)

**Decisions**:
- **Protocol over ABC**: Matches codebase conventions (`protocols/` package pattern). Structural typing.
- **Generic[T, R] over Union/Any**: Type-safe per-endpoint parameterization.
- **Pre-built retry callbacks on descriptor**: Zero changes to `_retry.py`, callbacks stay in endpoint scope.
- **Two error handlers (response + pre-execute)**: Cleanly handles insights stale fallback without overcomplicating the 4 endpoints that don't need it.
- **Non-raising cb_error_factory for batch**: Avoids subclassing; sentinel return pattern.
- **Policy in `_policy.py` (private)**: Not in `protocols/` -- internal to `clients/data/` package.
- **Migration order simple -> recon -> export -> insights -> batch**: Simplest-first validates core; most complex last benefits from refinements.
