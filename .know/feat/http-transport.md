---
domain: feat/http-transport
generated_at: "2026-04-01T15:15:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/transport/**/*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# Asana HTTP Transport Layer

## Purpose and Design Rationale

The transport layer is the boundary between the `autom8_asana` SDK and the external Asana API. It occupies the lowest tier of the four-layer architecture (Infrastructure), is classified as a **leaf package** (no internal upward imports), and delegates all generic HTTP mechanics to the `autom8y-http` platform SDK. The layer owns exactly two concerns: Asana-specific protocol handling (response envelope unwrapping, error translation) and adaptive concurrency control (AIMD).

**Why it exists as a distinct layer.** The `clients/` package contains 13+ resource-specific clients, each of which would otherwise duplicate HTTP retry, rate-limit, circuit-breaker, and concurrency logic. The transport layer centralises those cross-cutting concerns behind `AsanaHttpClient` so that `BaseClient` at `src/autom8_asana/clients/base.py` receives a single injected transport and never touches HTTP primitives directly.

**The migration context matters.** The `__init__.py` docstring and every source file carry `Per TDD-ASANA-HTTP-MIGRATION-001` citations. The package is the result of a deliberate migration from a legacy `AsyncHTTPClient` to the `autom8y-http` platform SDK. The design explicitly preserves backward-compatibility: `AsanaHttpClient.request()` matches the old `AsyncHTTPClient.request()` signature so existing callers required no change.

**Key architectural decisions (from source references):**
- `ADR-0061`: Thin-wrapper pattern -- `AsanaHttpClient` is not a facade and not a direct replacement; it delegates HTTP to the platform client and intercepts only Asana-specific concerns.
- `ADR-0062`: Shared rate limiter injection -- a single `TokenBucketRateLimiter` instance is shared across all clients constructed by `ClientPool`, preventing the failure mode documented in the RUNBOOK where multiple independent instances each maintain separate token buckets and collectively exceed Asana's quota.
- `TDD-GAP-04 / ADR-GAP04-001`: AIMD concurrency control -- the `AsyncAdaptiveSemaphore` implements TCP-style Additive Increase / Multiplicative Decrease (AIMD) to dynamically respond to Asana 429 signals.
- `ADR-0002`: Sync-in-async context detection -- `sync_wrapper` raises `SyncInAsyncContextError` immediately when called from an event loop, corresponding to SCAR-009.

**What the layer does NOT own.** The `autom8y-http` platform SDK owns: the underlying `httpx` session lifecycle, TLS configuration, connection pool management (though pool size is configurable via `ConnectionPoolConfig`), and the concrete implementations of `TokenBucketRateLimiter`, `CircuitBreaker`, and `ExponentialBackoffRetry`. The transport layer provides configuration translation and policy injection, not policy implementation.

## Conceptual Model

The transport layer operates with two orthogonal control planes running simultaneously on every request:

**Rate plane (sustained throughput):** A `TokenBucketRateLimiter` limits the request rate to Asana's documented 1500 requests/60 seconds. Tokens are consumed before each request. The bucket drains at the configured `max_requests / window_seconds` rate (default: 25 tokens/second). When the bucket is empty, requests block until tokens refill. This plane is time-based.

**Concurrency plane (burst protection):** An `AsyncAdaptiveSemaphore` limits the number of in-flight requests simultaneously. Separate instances exist for read operations (GET, ceiling default 50) and write operations (POST/PUT/DELETE, ceiling default 15). The semaphore window shrinks multiplicatively on a 429 signal (default: halve) and grows additively on each success (default: +1 per 2 seconds after a 5-second grace period). This is not independent of the rate plane: both must be acquired before any request proceeds.

**Epoch coalescing:** The `Slot` mechanism prevents N simultaneous 429 responses from causing N halvings. When `slot.reject()` is called, `_handle_reject()` checks `slot_epoch < self._epoch`. If the window already decreased (epoch incremented) since this slot was acquired, the reject is ignored. Only the first 429 in any burst causes a halving. Subsequent 429s from the same burst carry stale epochs.

**The request lifecycle** for a single call through `AsanaHttpClient._request()`:
1. `circuit_breaker.check()` -- raises `CircuitBreakerOpenError` immediately if the circuit is open, without consuming rate or concurrency budget.
2. `semaphore.acquire()` -- blocks until a concurrency slot is available; returns a `Slot` context manager tied to the current epoch.
3. `rate_limiter.acquire()` -- consumes a token; blocks if the bucket is empty.
4. `platform_client._client.request(...)` -- bypasses the platform client's policy layer and calls the underlying httpx session directly. This is intentional: policies are managed externally to allow sharing.
5. On 429: `slot.reject()` triggers AIMD decrease, then retry loop continues.
6. On 5xx: `circuit_breaker.record_failure()` is called both before retry and before final raise.
7. On success: `slot.succeed()` triggers AIMD additive increase; `circuit_breaker.record_success()` is called.
8. `response_handler.unwrap_response()` strips the `{"data": ...}` envelope.

**The FixedSemaphoreAdapter** provides a structural kill switch. When `ConcurrencyConfig.aimd_enabled=False`, `AsanaHttpClient.__init__` constructs `FixedSemaphoreAdapter` instances instead of `AsyncAdaptiveSemaphore`. The `FixedSemaphoreAdapter` wraps `asyncio.Semaphore` and provides a `NoOpSlot` where `reject()` and `succeed()` are no-ops. This means `AsanaHttpClient._request()` uses a single code path regardless of AIMD mode -- the adapter pattern absorbs the conditional.

**Lazy client initialization** with double-checked locking (`_get_client()`): `_platform_client` starts as `None`. The first `await self._get_client()` acquires `_client_lock`, creates the `Autom8yHttpClient`, and directly mutates its internal `_client.headers` to inject the Authorization Bearer token. Subsequent calls take the fast path (no lock). This defers token acquisition until the first request.

**ConfigTranslator** is a stateless bridge with four static methods, each performing a one-way translation from an `AsanaConfig` sub-dataclass to a `autom8y-http` configuration class. Its existence makes the boundary explicit: no other module in the package knows the platform SDK's config field names.

## Implementation Map

| File | Class / Component | Role |
|------|-------------------|------|
| `src/autom8_asana/transport/__init__.py` | module exports | Re-exports all public components; also re-exports `CircuitState` from `autom8y_http.protocols` |
| `src/autom8_asana/transport/asana_http.py` | `AsanaHttpClient` | Primary transport class; owns the request loop, retry logic, AIMD feedback, and lazy client init |
| `src/autom8_asana/transport/adaptive_semaphore.py` | `AIMDConfig`, `Slot`, `NoOpSlot`, `FixedSemaphoreAdapter`, `AsyncAdaptiveSemaphore` | AIMD concurrency control primitives |
| `src/autom8_asana/transport/config_translator.py` | `ConfigTranslator` | Stateless translation: `AsanaConfig` -> platform SDK config classes |
| `src/autom8_asana/transport/response_handler.py` | `AsanaResponseHandler` | Envelope unwrapping; 429/error parsing with `Retry-After` extraction |
| `src/autom8_asana/transport/sync.py` | `sync_wrapper` | Decorator factory: generates sync wrappers that raise `SyncInAsyncContextError` from async context |

**Key methods:**

`AsanaHttpClient._request(method, path, ...)` -- inner loop for all non-streaming, non-multipart requests. All retry and AIMD feedback happens here. Lines 549-648.

`AsanaHttpClient._request_paginated(...)` -- identical structure to `_request` but calls `response_handler.unwrap_paginated_response()` and always uses `_read_semaphore`. Lines 649-737. Note: the loop body is structurally duplicated from `_request` -- this is a code smell but deliberate (avoids branching in the hot path).

`AsanaHttpClient.post_multipart(...)` -- uses the `raw()` escape hatch from `Autom8yHttpClient` to send `multipart/form-data`. Temporarily removes the `Content-Type` header so httpx auto-generates the boundary. Lines 378-486.

`AsanaHttpClient.stream(...)` -- context manager yielding raw `httpx.Response` for streaming downloads. Applies rate limiting once per initiation; no AIMD feedback (streaming duration is unbounded). Lines 342-376.

`AsyncAdaptiveSemaphore._handle_reject(slot_epoch)` -- synchronous (no await points); epoch check then multiplicative decrease; logs `aimd_decrease` at info or warning depending on whether the floor was reached. Lines 308-364.

`AsyncAdaptiveSemaphore._handle_success(slot_epoch)` -- synchronous; three guard checks: stale epoch, grace period, increase interval throttle. Additive increase only after all guards pass. Lines 365-422.

`AsanaResponseHandler._parse_rate_limit_error(response)` -- extracts `Retry-After` header with `contextlib.suppress(ValueError)` to handle malformed header values gracefully. Lines 178-216.

**Configuration surface** (in `src/autom8_asana/config.py`):
- `RateLimitConfig`: `max_requests=1500`, `window_seconds=60`
- `ConcurrencyConfig`: `read_limit=50`, `write_limit=15`, `aimd_enabled=True`, plus 7 AIMD tuning parameters
- `RetryConfig`: `max_retries=5`, `base_delay=0.5`, `max_delay=60`, retryable codes `{429, 503, 504}`
- `CircuitBreakerConfig`: `enabled=False` by default (opt-in), `failure_threshold=5`, `recovery_timeout=60`
- `TimeoutConfig`: `connect=5.0`, `read=30.0`
- `ConnectionPoolConfig`: `max_connections=100`

**Test coverage** (`tests/unit/transport/`): 7 dedicated test files (adaptive_semaphore, aimd_integration, aimd_simulation, asana_http, config_translator, response_handler, sync_wrapper). This is unusually thorough test coverage for the transport layer relative to other packages.

**External dependencies:** The transport layer imports from `autom8y_http` (platform SDK) and `autom8y_log`. It does NOT import `httpx` directly (TID251 lint ban enforced). Internal imports are limited to `autom8_asana.exceptions` (error hierarchy) and `autom8_asana.config` (type-checked only, via `TYPE_CHECKING`).

## Boundaries and Failure Modes

**Inbound boundary (callers):**
- `src/autom8_asana/clients/base.py` -- `BaseClient` accepts an injected `AsanaHttpClient` instance. All 13+ resource clients inherit from `BaseClient` and call `self._http.get()`, `post()`, etc.
- `AsanaClient` (`client.py`) -- constructs `AsanaHttpClient` with shared rate limiter and circuit breaker instances that are then distributed to all `BaseClient` subclasses via the `ClientPool`.

**Outbound boundary (dependencies):**
- `autom8y_http.Autom8yHttpClient` -- the underlying HTTP client. The transport layer bypasses the platform client's policy layer by calling `platform_client._client.request(...)` directly (accessing a private `_client` attribute of the platform SDK). This coupling to the platform SDK's internal structure is a documented tradeoff.
- `api.asana.com` -- the Asana API itself, accessed via the base URL from `AsanaConfig.base_url`.

**Failure modes and their handling:**

| Condition | Transport handling | Downstream effect |
|-----------|-------------------|-------------------|
| HTTP 429 from Asana | `slot.reject()`, AIMD halves window, exponential backoff retry (up to `max_retries`) | `RateLimitError` raised after exhaustion |
| HTTP 5xx from Asana | `circuit_breaker.record_failure()`, exponential backoff retry | `ServerError` raised after exhaustion; CB may open |
| `TimeoutException` | `circuit_breaker.record_failure()`, retry up to `max_retries` | `AsanaError.TimeoutError` raised after exhaustion |
| `HTTPError` (network error) | `circuit_breaker.record_failure()`, NOT retried | `AsanaError` raised immediately |
| Circuit breaker open | `circuit_breaker.check()` raises before slot acquire | `CircuitBreakerOpenError` (no rate/concurrency budget consumed) |
| AIMD at floor | `aimd_at_minimum` warning logged, concurrency stays at 1 | Requests serialized until 429s stop |
| 5 consecutive 429s | `aimd_cooldown_threshold_reached` warning logged | No automatic cooldown in v1 -- FR-008 stub only |
| Invalid JSON response | `json.JSONDecodeError` caught in `unwrap_response` | `AsanaError` with body snippet and request ID |
| Malformed `Retry-After` header | `contextlib.suppress(ValueError)` | `retry_after=None`; backoff uses exponential delay only |
| Multipart upload with no `content-type` backup | `finally` block restores header | No leak of modified header state |

**Known architectural friction points:**

1. **`platform_client._client` private access** -- `asana_http.py` line 583 calls `platform_client._client.request(...)`, bypassing the platform client's public API. This is the cost of managing policies externally. If `autom8y-http` renames or restructures `_client`, the transport layer breaks silently at runtime.

2. **`_request` / `_request_paginated` structural duplication** -- The two inner loops are nearly identical (same retry/AIMD/circuit-breaker logic). A bug fix in one must be applied to both. The runbook documents the same pattern at the hierarchy warming level.

3. **`CircuitBreakerConfig.enabled=False` default** -- The circuit breaker is disabled by default for backward compatibility. The `_request` loop calls `self._circuit_breaker.check()` and `record_failure()` unconditionally, but the `CircuitBreaker` implementation from `autom8y-http` must handle `enabled=False` as a no-op. If the platform SDK changes this behavior, all circuit-breaker calls in the transport become no-ops silently.

4. **`cooldown_duration_seconds` is unused in v1** -- `AIMDConfig` documents this as a placeholder. The cooldown warning fires at 5 consecutive 429s but does not reduce throughput further. The comment notes `"cooldown_not_active_in_v1"` -- operators seeing this warning have no further automatic protection beyond the AIMD window halving.

5. **`get_stream_url` and `stream` skip AIMD** -- Both streaming methods call `rate_limiter.acquire()` but do not use the semaphore. Long-running streaming operations do not consume a concurrency slot, so `in_flight` undercounts actual API connections during streaming.

6. **`_should_retry` off-by-one semantics** -- The condition is `attempt >= max_attempts - 1`. `max_attempts` is read from `retry_policy.max_attempts`, which from `PlatformRetryConfig` maps from `RetryConfig.max_retries=5`. Whether `max_attempts` equals `max_retries` or `max_retries + 1` is not visible within the transport layer itself and depends on the platform SDK's interpretation.

## Knowledge Gaps

1. **`autom8y-http` internal API stability** -- The transport accesses `platform_client._client` (a private attribute) and injects headers via `_client.headers.update(...)`. The autom8y-http SDK source is not available in this codebase. If the SDK encapsulates or renames this attribute in a future version, the transport breaks. No contract test guards this.

2. **`ExponentialBackoffRetry.max_attempts` vs. `RetryConfig.max_retries`** -- `_should_retry` uses `self._retry_policy.max_attempts`. Whether this equals `max_retries` or `max_retries + 1` (initial attempt counted) is not verifiable from the source here. The test files may clarify but were not read.

3. **`CircuitBreaker.check()` behavior when `enabled=False`** -- The transport calls `await self._circuit_breaker.check()` unconditionally. Whether the platform SDK `CircuitBreaker` treats `enabled=False` as a no-op or requires a null check is not visible in this codebase. No defensive guard exists in the transport code.

4. **`ConfigTranslator.to_http_client_config` timeout mapping** -- Only `asana_config.timeout.connect` is passed as `timeout` to `HttpClientConfig`. The read, write, and pool timeout values from `TimeoutConfig` are not translated. Whether `HttpClientConfig.timeout` is a scalar or a structured type is platform-SDK-internal. If it is scalar, `read`, `write`, and `pool` timeouts are lost.

5. **`get_stream_url` return type annotation** -- The method is annotated `-> AsyncIterator[bytes]` but the function body uses `async for chunk in response.aiter_bytes(): yield chunk`, making it an async generator (not an `AsyncIterator` returned as a value). The function is not decorated with `@asynccontextmanager` like `stream()`, so callers cannot use it as an async context manager. This may be intentional but the relationship between `stream()` and `get_stream_url()` is not documented.

6. **Thread-safety of `AsyncAdaptiveSemaphore._handle_reject` / `_handle_success`** -- Both methods are documented as "synchronous -- no await points." This is safe for asyncio's single-threaded concurrency model, but if `AsanaHttpClient` is ever used from multiple threads (e.g., via `asyncio.run()` in a thread pool), the semaphore state could be corrupted. The scar-tissue doc (SCAR-010/010b) shows prior threading issues in the persistence layer; the transport has no equivalent lock.
