---
artifact_id: TDD-asana-http-migration-001
title: "autom8_asana HTTP Layer Migration to autom8y-http Platform SDK"
created_at: "2026-01-03T15:30:00Z"
author: architect
prd_ref: PRD-asana-http-migration-001
status: draft
components:
  - name: AsanaHttpClient
    type: module
    description: "Wrapper around Autom8yHttpClient providing Asana-specific response handling and backward-compatible API"
    dependencies:
      - name: Autom8yHttpClient
        type: external
        version: ">=0.2.0"
      - name: TokenBucketRateLimiter
        type: external
      - name: ExponentialBackoffRetry
        type: external
      - name: CircuitBreaker
        type: external
    interfaces:
      - name: get
        signature: "async def get(path: str, *, params: dict | None = None) -> dict"
      - name: post
        signature: "async def post(path: str, *, json: dict | None = None, params: dict | None = None) -> dict"
      - name: put
        signature: "async def put(path: str, *, json: dict | None = None) -> dict"
      - name: delete
        signature: "async def delete(path: str) -> dict"
      - name: get_paginated
        signature: "async def get_paginated(path: str, *, params: dict | None = None) -> tuple[list[dict], str | None]"
      - name: stream
        signature: "async def stream(method: str, path: str, **kwargs) -> AsyncContextManager[httpx.Response]"
      - name: post_multipart
        signature: "async def post_multipart(path: str, *, files: dict, data: dict | None = None) -> dict"
    files:
      - src/autom8_asana/transport/asana_http.py
  - name: ConfigTranslator
    type: module
    description: "Translates AsanaConfig to autom8y-http configuration classes"
    dependencies:
      - name: AsanaConfig
        type: internal
      - name: HttpClientConfig
        type: external
      - name: RateLimiterConfig
        type: external
      - name: RetryConfig
        type: external
      - name: CircuitBreakerConfig
        type: external
    interfaces:
      - name: translate
        signature: "def translate(asana_config: AsanaConfig) -> tuple[HttpClientConfig, RateLimiterConfig, RetryConfig, CircuitBreakerConfig]"
    files:
      - src/autom8_asana/transport/config_translator.py
  - name: AsanaResponseHandler
    type: module
    description: "Handles Asana-specific response unwrapping and error parsing"
    dependencies:
      - name: AsanaError
        type: internal
      - name: RateLimitError
        type: internal
      - name: ServerError
        type: internal
    interfaces:
      - name: unwrap_response
        signature: "def unwrap_response(response: httpx.Response) -> dict"
      - name: parse_error
        signature: "def parse_error(response: httpx.Response) -> AsanaError"
    files:
      - src/autom8_asana/transport/response_handler.py
api_contracts: []
data_models:
  - name: AsanaHttpClientConfig
    type: value_object
    fields:
      - name: base_url
        type: str
        required: true
        constraints: "Must be valid URL, defaults to Asana API"
      - name: auth_provider
        type: AuthProvider
        required: true
        constraints: "Must provide get_secret()"
      - name: rate_limiter
        type: RateLimiterProtocol
        required: false
        constraints: "If None, creates from config"
      - name: circuit_breaker
        type: CircuitBreakerProtocol
        required: false
        constraints: "If None, creates from config"
security_considerations:
  - "Auth token passed via Authorization header, never logged"
  - "Header redaction for all request logging"
  - "No secrets in error messages"
related_adrs:
  - ADR-0061
  - ADR-0062
  - ADR-0048
  - ADR-0002
schema_version: "1.0"
---

# TDD: autom8_asana HTTP Layer Migration to autom8y-http Platform SDK

**TDD ID**: TDD-ASANA-HTTP-MIGRATION-001
**Version**: 1.0
**Date**: 2026-01-03
**PRD Reference**: PRD-ASANA-HTTP-MIGRATION-001

---

## Overview

This TDD provides the technical design for migrating autom8_asana's custom HTTP transport layer to the autom8y-http platform SDK. The migration addresses the thundering herd problem during parallel section fetches by replacing per-instance rate limiters with a shared, coordinated rate limiter.

### Goals

1. Replace `AsyncHTTPClient` with a thin wrapper around `Autom8yHttpClient`
2. Eliminate per-instance rate limiters in favor of a shared limiter per `AsanaClient`
3. Preserve all existing public API contracts for backward compatibility
4. Reduce retry warnings from 80+ to fewer than 10 during parallel operations

### Non-Goals

1. Distributed rate limiting (Redis-backed) - out of scope per PRD
2. WebSocket or GraphQL support
3. Changing authentication flow (handled by `auth_provider`)

---

## Architecture

### System Context

```
+-------------------+     +-------------------+     +-------------------+
|    AsanaClient    |---->|  AsanaHttpClient  |---->| Autom8yHttpClient |
+-------------------+     +-------------------+     +-------------------+
         |                        |                         |
         |                        |                         |
         v                        v                         v
+-------------------+     +-------------------+     +-------------------+
|   TasksClient     |     | ConfigTranslator  |     | TokenBucketRate   |
|   ProjectsClient  |     +-------------------+     |    Limiter        |
|   SectionsClient  |             |                 +-------------------+
|   ...             |             |                         ^
+-------------------+             v                         |
         |               +-------------------+              |
         |               | AsanaResponse     |              |
         +-------------->|    Handler        |              |
                         +-------------------+     (SHARED INSTANCE)
```

### Component Architecture

```
autom8_asana/transport/
    |
    +-- asana_http.py        # AsanaHttpClient wrapper (NEW)
    |       |
    |       +-- Wraps Autom8yHttpClient
    |       +-- Applies Asana response unwrapping
    |       +-- Provides backward-compatible API
    |
    +-- config_translator.py  # Config translation (NEW)
    |       |
    |       +-- AsanaConfig -> HttpClientConfig
    |       +-- RateLimitConfig -> RateLimiterConfig
    |       +-- RetryConfig -> RetryConfig
    |       +-- CircuitBreakerConfig -> CircuitBreakerConfig
    |
    +-- response_handler.py   # Response handling (NEW)
    |       |
    |       +-- {"data": ...} unwrapping
    |       +-- Error response parsing
    |       +-- Pagination extraction
    |
    +-- http.py              # AsyncHTTPClient (DEPRECATED)
    +-- rate_limiter.py      # TokenBucketRateLimiter (DEPRECATED)
    +-- retry.py             # RetryHandler (DEPRECATED)
    +-- circuit_breaker.py   # CircuitBreaker (DEPRECATED)
    +-- sync.py              # sync_wrapper (PRESERVED)
```

---

## Component Design

### FR-001: AsanaHttpClient Wrapper

The `AsanaHttpClient` class wraps `Autom8yHttpClient` to provide:

1. **Asana-specific response handling**: Unwraps `{"data": ...}` envelope
2. **Backward-compatible API**: Same method signatures as `AsyncHTTPClient`
3. **Shared policy injection**: Accepts rate limiter/circuit breaker instances

#### Interface Contract

```python
class AsanaHttpClient:
    """Asana HTTP client wrapping autom8y-http platform client.

    Per TDD-ASANA-HTTP-MIGRATION-001: Thin wrapper providing Asana-specific
    response handling while delegating HTTP operations to Autom8yHttpClient.
    """

    def __init__(
        self,
        config: AsanaConfig,
        auth_provider: AuthProvider,
        *,
        rate_limiter: RateLimiterProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
        logger: LogProvider | None = None,
    ) -> None:
        """Initialize Asana HTTP client.

        Args:
            config: Asana SDK configuration
            auth_provider: Authentication provider for API token
            rate_limiter: Shared rate limiter (created from config if None)
            circuit_breaker: Shared circuit breaker (created from config if None)
            logger: Optional logger for request logging

        Key behaviors:
        - If rate_limiter is None, creates one from config.rate_limit
        - If circuit_breaker is None, creates one from config.circuit_breaker
        - Rate limiter and circuit breaker are passed to Autom8yHttpClient
        """
        ...

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """GET request with Asana response unwrapping.

        Returns:
            Unwrapped response data (without {"data": ...} envelope)
        """
        ...

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST request with Asana response unwrapping."""
        ...

    async def put(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """PUT request with Asana response unwrapping."""
        ...

    async def delete(self, path: str) -> dict[str, Any]:
        """DELETE request with Asana response unwrapping."""
        ...

    async def get_paginated(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """GET with pagination support.

        Returns:
            Tuple of (data list, next_offset or None)
        """
        ...

    @asynccontextmanager
    async def stream(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> AsyncIterator[httpx.Response]:
        """Stream response for large downloads.

        Uses raw() escape hatch from Autom8yHttpClient.
        Rate limiting applied once per stream initiation.
        """
        ...

    async def post_multipart(
        self,
        path: str,
        *,
        files: dict[str, tuple[str, Any, str | None]],
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST with multipart/form-data for file uploads.

        Uses raw() escape hatch from Autom8yHttpClient.
        """
        ...

    async def close(self) -> None:
        """Close client and release resources."""
        ...
```

#### Implementation Notes

1. **Response Unwrapping**: Asana wraps all responses in `{"data": ...}`. The wrapper extracts this before returning.

2. **Error Translation**: Parse Asana error responses into domain exceptions:
   - 429 -> `RateLimitError` with `retry_after`
   - 5xx -> `ServerError`
   - 4xx -> Specific error types

3. **Escape Hatch**: For streaming and multipart, use `Autom8yHttpClient.raw()` which bypasses retry/circuit breaker but still logs.

### FR-002: Shared Rate Limiter Strategy

Per ADR-0061: The rate limiter is shared at the `AsanaClient` scope, not globally.

#### Injection Pattern

```python
# In AsanaClient.__init__()

# Create shared rate limiter once
self._shared_rate_limiter = TokenBucketRateLimiter(
    config=RateLimiterConfig(
        max_tokens=config.rate_limit.max_requests,
        refill_period=config.rate_limit.window_seconds,
    ),
    logger=self._log_provider,
)

# Create shared circuit breaker once
self._shared_circuit_breaker = CircuitBreaker(
    config=CircuitBreakerConfig(
        enabled=config.circuit_breaker.enabled,
        failure_threshold=config.circuit_breaker.failure_threshold,
        recovery_timeout=config.circuit_breaker.recovery_timeout,
        half_open_max_calls=config.circuit_breaker.half_open_max_calls,
    ),
    logger=self._log_provider,
)

# Create HTTP client with shared instances
self._http = AsanaHttpClient(
    config=config,
    auth_provider=self._auth_provider,
    rate_limiter=self._shared_rate_limiter,
    circuit_breaker=self._shared_circuit_breaker,
    logger=self._log_provider,
)
```

#### Rate Limiter Scope Diagram

```
AsanaClient (instance scope)
    |
    +-- _shared_rate_limiter: TokenBucketRateLimiter (1 per AsanaClient)
    |       |
    |       +-- max_tokens=1500, refill_period=60s
    |
    +-- AsanaHttpClient
    |       |
    |       +-- Uses _shared_rate_limiter
    |       +-- All requests go through same limiter
    |
    +-- TasksClient
    |       |
    |       +-- Uses AsanaHttpClient
    |       +-- ParallelSectionFetcher uses same limiter
    |
    +-- SectionsClient (uses same limiter)
    +-- ProjectsClient (uses same limiter)
    +-- ...
```

### FR-003: Config Translation Layer

Translates autom8_asana configuration to autom8y-http configuration.

```python
class ConfigTranslator:
    """Translates AsanaConfig to autom8y-http configuration."""

    @staticmethod
    def to_http_client_config(asana_config: AsanaConfig) -> HttpClientConfig:
        """Translate to HttpClientConfig.

        Mapping:
        - base_url: asana_config.base_url
        - timeout: asana_config.timeout.read (use read timeout as primary)
        - max_connections: asana_config.connection_pool.max_connections
        - enable_rate_limiting: True (always, we inject shared limiter)
        - enable_retry: True (always, use platform retry)
        - enable_circuit_breaker: asana_config.circuit_breaker.enabled
        """
        return HttpClientConfig(
            base_url=asana_config.base_url,
            timeout=asana_config.timeout.read,
            max_connections=asana_config.connection_pool.max_connections,
            enable_rate_limiting=False,  # We inject our own
            enable_retry=False,          # We inject our own
            enable_circuit_breaker=False,  # We inject our own
        )

    @staticmethod
    def to_rate_limiter_config(asana_config: AsanaConfig) -> RateLimiterConfig:
        """Translate to RateLimiterConfig.

        Mapping:
        - max_tokens: asana_config.rate_limit.max_requests
        - refill_period: asana_config.rate_limit.window_seconds
        """
        return RateLimiterConfig(
            max_tokens=asana_config.rate_limit.max_requests,
            refill_period=float(asana_config.rate_limit.window_seconds),
        )

    @staticmethod
    def to_retry_config(asana_config: AsanaConfig) -> RetryConfig:
        """Translate to RetryConfig.

        Mapping:
        - max_retries: asana_config.retry.max_retries
        - base_delay: asana_config.retry.base_delay
        - max_delay: asana_config.retry.max_delay
        - exponential_base: asana_config.retry.exponential_base
        - jitter: asana_config.retry.jitter
        - retryable_status_codes: asana_config.retry.retryable_status_codes
        """
        return RetryConfig(
            max_retries=asana_config.retry.max_retries,
            base_delay=asana_config.retry.base_delay,
            max_delay=asana_config.retry.max_delay,
            exponential_base=asana_config.retry.exponential_base,
            jitter=asana_config.retry.jitter,
            retryable_status_codes=asana_config.retry.retryable_status_codes,
        )

    @staticmethod
    def to_circuit_breaker_config(asana_config: AsanaConfig) -> CircuitBreakerConfig:
        """Translate to CircuitBreakerConfig.

        Mapping:
        - enabled: asana_config.circuit_breaker.enabled
        - failure_threshold: asana_config.circuit_breaker.failure_threshold
        - recovery_timeout: asana_config.circuit_breaker.recovery_timeout
        - half_open_max_calls: asana_config.circuit_breaker.half_open_max_calls
        """
        return CircuitBreakerConfig(
            enabled=asana_config.circuit_breaker.enabled,
            failure_threshold=asana_config.circuit_breaker.failure_threshold,
            recovery_timeout=asana_config.circuit_breaker.recovery_timeout,
            half_open_max_calls=asana_config.circuit_breaker.half_open_max_calls,
        )
```

### FR-004: Response Handler

Handles Asana-specific response processing.

```python
class AsanaResponseHandler:
    """Handles Asana-specific response processing."""

    @staticmethod
    def unwrap_response(response: httpx.Response) -> dict[str, Any]:
        """Unwrap Asana response envelope.

        Asana wraps all responses in {"data": ...}. This method:
        1. Parses JSON
        2. Extracts "data" key
        3. Returns data or raises error

        Raises:
            AsanaError: If JSON parsing fails
            RateLimitError: If 429 response
            ServerError: If 5xx response
        """
        if response.status_code >= 400:
            raise AsanaResponseHandler.parse_error(response)

        try:
            result = response.json()
        except json.JSONDecodeError as e:
            request_id = response.headers.get("X-Request-Id", "unknown")
            body_snippet = response.text[:200] if response.text else "(empty)"
            raise AsanaError(
                f"Invalid JSON response (HTTP {response.status_code}, "
                f"request_id={request_id}): {e}. Body: {body_snippet}"
            ) from e

        if isinstance(result, dict) and "data" in result:
            return result["data"]
        return result

    @staticmethod
    def unwrap_paginated_response(
        response: httpx.Response,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Unwrap paginated Asana response.

        Returns:
            Tuple of (data list, next_offset or None)
        """
        if response.status_code >= 400:
            raise AsanaResponseHandler.parse_error(response)

        try:
            result = response.json()
        except json.JSONDecodeError as e:
            request_id = response.headers.get("X-Request-Id", "unknown")
            raise AsanaError(
                f"Invalid JSON response (HTTP {response.status_code}, "
                f"request_id={request_id}): {e}"
            ) from e

        data: list[dict[str, Any]] = []
        next_offset: str | None = None

        if isinstance(result, dict):
            data = result.get("data", [])
            next_page = result.get("next_page")
            if next_page and isinstance(next_page, dict):
                next_offset = next_page.get("offset")

        return data, next_offset

    @staticmethod
    def parse_error(response: httpx.Response) -> AsanaError:
        """Parse error response into domain exception.

        Returns:
            Appropriate AsanaError subclass based on status code
        """
        status_code = response.status_code

        # Try to parse error body
        try:
            body = response.json()
            errors = body.get("errors", [])
            message = errors[0].get("message", str(body)) if errors else str(body)
        except (json.JSONDecodeError, IndexError, KeyError):
            message = response.text or f"HTTP {status_code}"

        # Rate limit error
        if status_code == 429:
            retry_after = None
            if "Retry-After" in response.headers:
                try:
                    retry_after = int(response.headers["Retry-After"])
                except ValueError:
                    pass
            return RateLimitError(message, retry_after=retry_after)

        # Server errors
        if status_code >= 500:
            return ServerError(message, status_code=status_code)

        # Client errors
        return AsanaError.from_response(response)
```

### FR-005: Deprecation of Legacy Transport

The legacy transport modules will be deprecated with warnings:

```python
# In autom8_asana/transport/__init__.py

import warnings
from typing import TYPE_CHECKING

# Re-export sync_wrapper (not deprecated)
from autom8_asana.transport.sync import sync_wrapper

if TYPE_CHECKING:
    from autom8_asana.transport.http import AsyncHTTPClient as _AsyncHTTPClient
    from autom8_asana.transport.rate_limiter import TokenBucketRateLimiter as _TokenBucketRateLimiter
    from autom8_asana.transport.retry import RetryHandler as _RetryHandler
    from autom8_asana.transport.circuit_breaker import CircuitBreaker as _CircuitBreaker


def __getattr__(name: str):
    """Emit deprecation warnings for legacy transport access."""
    deprecated = {
        "AsyncHTTPClient": "autom8_asana.transport.http",
        "TokenBucketRateLimiter": "autom8_asana.transport.rate_limiter",
        "RetryHandler": "autom8_asana.transport.retry",
        "CircuitBreaker": "autom8_asana.transport.circuit_breaker",
    }

    if name in deprecated:
        module = deprecated[name]
        warnings.warn(
            f"{name} is deprecated. The transport layer now uses autom8y-http. "
            f"Direct access to {module} will be removed in v2.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        import importlib
        mod = importlib.import_module(module)
        return getattr(mod, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

---

## Sequence Diagrams

### Parallel Section Fetch (After Migration)

```
ParallelSectionFetcher          TasksClient       AsanaHttpClient     TokenBucketRateLimiter    Autom8yHttpClient
        |                           |                   |                      |                       |
        |-- fetch_all() ----------->|                   |                      |                       |
        |                           |                   |                      |                       |
        |  [Section 1-8 concurrent] |                   |                      |                       |
        |                           |                   |                      |                       |
        |                           |-- list_async() -->|                      |                       |
        |                           |                   |                      |                       |
        |                           |                   |-- acquire() -------->|                       |
        |                           |                   |                      |                       |
        |                           |                   |<-- (wait if needed) -|                       |
        |                           |                   |                      |                       |
        |                           |                   |-- get() ------------------------------------->|
        |                           |                   |                      |                       |
        |                           |                   |<-- Response ----------------------------------|
        |                           |                   |                      |                       |
        |                           |                   |-- unwrap_response() |                       |
        |                           |                   |                      |                       |
        |                           |<-- [Task, ...] ---|                      |                       |
        |                           |                   |                      |                       |
        |<-- FetchResult -----------|                   |                      |                       |
```

**Key Difference**: All 8 concurrent section fetches share the **same** `TokenBucketRateLimiter`, preventing burst accumulation.

### Rate Limiter Coordination

```
Section Fetch 1  Section Fetch 2  Section Fetch 3    TokenBucketRateLimiter
      |                |                |                     |
      |-- acquire() --------------------------->              |
      |                |                |           [tokens: 1500]
      |<-- granted (1 token) ----------------------           |
      |                |                |           [tokens: 1499]
      |                |-- acquire() ------------>            |
      |                |                |           [tokens: 1498]
      |                |<-- granted -----------------         |
      |                |                |                     |
      |                |                |-- acquire() ------->|
      |                |                |           [tokens: 1497]
      |                |                |<-- granted ---------|
      |                |                |                     |
      |  [All proceed concurrently, tokens decrease together] |
      |                |                |                     |
      |  [If tokens < needed, wait until refill]              |
```

---

## Migration Sequence

### Phase 1: Infrastructure Setup

1. **Add autom8y-http dependency**
   ```toml
   # pyproject.toml
   [project.dependencies]
   autom8y-http = ">=0.2.0"
   ```

2. **Configure CodeArtifact access**
   - CI/CD pipeline already has AWS credentials
   - pip configured via `PIP_EXTRA_INDEX_URL`

### Phase 2: Transport Wrapper Implementation

1. **Create new modules**
   - `transport/config_translator.py`
   - `transport/response_handler.py`
   - `transport/asana_http.py`

2. **Unit test new modules**
   - Test config translation
   - Test response unwrapping
   - Test error parsing

### Phase 3: Integration

1. **Update AsanaClient initialization**
   - Create shared rate limiter
   - Create shared circuit breaker
   - Replace `AsyncHTTPClient` with `AsanaHttpClient`

2. **Verify backward compatibility**
   - All existing tests pass
   - Public API unchanged

### Phase 4: Validation

1. **Run parallel fetch benchmark**
   ```bash
   pytest tests/integration/test_parallel_fetch_benchmark.py -v
   ```

2. **Measure retry warnings**
   - Capture logs during 2614-task parallel fetch
   - Verify < 10 retry warnings

3. **Verify rate limit coordination**
   - Single rate limiter instance check
   - No 429 errors in parallel operations

### Phase 5: Deprecation

1. **Add deprecation warnings**
   - `AsyncHTTPClient` direct import
   - `TokenBucketRateLimiter` direct import
   - `RetryHandler` direct import
   - `CircuitBreaker` direct import

2. **Update documentation**
   - Migration guide for direct transport users
   - Note in CHANGELOG

---

## Error Handling

### Error Translation Matrix

| Platform Error | Asana Domain Error | Retry Behavior |
|----------------|-------------------|----------------|
| `CircuitBreakerOpenError` | `CircuitBreakerOpenError` | No retry, fast-fail |
| `httpx.TimeoutException` | `TimeoutError` | Retry with backoff |
| `httpx.HTTPError` | `AsanaError` | Depends on status |
| 429 Response | `RateLimitError` | Retry with Retry-After |
| 5xx Response | `ServerError` | Retry with backoff |
| 4xx Response | Specific error type | No retry |

### Retry-After Handling

```python
async def _handle_request(self, method: str, path: str, **kwargs):
    """Handle request with Asana-specific retry logic."""
    attempt = 0
    max_attempts = self._retry_policy.max_attempts

    while True:
        try:
            response = await self._platform_client.request(method, path, **kwargs)

            # Check for rate limit
            if response.status_code == 429:
                if attempt < max_attempts:
                    error = self._response_handler.parse_error(response)
                    await self._retry_policy.wait(attempt, error.retry_after)
                    attempt += 1
                    continue

            # Check for retryable server error
            if self._retry_policy.should_retry(response.status_code, attempt):
                await self._retry_policy.wait(attempt)
                attempt += 1
                continue

            return self._response_handler.unwrap_response(response)

        except httpx.TimeoutException as e:
            if attempt < max_attempts:
                await self._retry_policy.wait(attempt)
                attempt += 1
                continue
            raise TimeoutError(f"Request timed out: {path}") from e
```

---

## Observability

### Logging Points

| Event | Level | Fields |
|-------|-------|--------|
| Request start | DEBUG | method, path |
| Response received | DEBUG | method, path, status_code |
| Rate limit wait | INFO/WARN | wait_seconds, needed_tokens |
| Retry attempt | WARN | attempt, max_retries, delay_seconds |
| Circuit breaker state | INFO | old_state, new_state |
| Error response | ERROR | method, path, status_code, error_type |

### Metrics (via ObservabilityHook)

```python
# Existing observability hook events preserved
observability_hook.on_cache_hit(...)
observability_hook.on_cache_miss(...)
observability_hook.on_api_request(method, path, status_code, duration_ms)
```

---

## Testing Strategy

### Unit Tests

1. **ConfigTranslator**
   - Translation of each config field
   - Default value handling
   - Edge cases (zero values, negative values)

2. **AsanaResponseHandler**
   - Successful response unwrapping
   - Error response parsing (429, 5xx, 4xx)
   - Invalid JSON handling
   - Pagination extraction

3. **AsanaHttpClient**
   - Request delegation to platform client
   - Response handling
   - Streaming and multipart via raw()
   - Shared rate limiter usage

### Integration Tests

1. **Parallel Fetch Validation**
   ```python
   async def test_parallel_fetch_no_429():
       """Verify parallel fetch completes without rate limit errors."""
       client = AsanaClient(token=...)

       # Fetch 2614 tasks via parallel section fetch
       df_builder = ProjectDataFrameBuilder(...)
       result = await df_builder.build_async(project_gid)

       assert result.row_count >= 2614
       # Check logs for 429 errors
       assert log_capture.count("429") == 0
   ```

2. **Shared Rate Limiter Verification**
   ```python
   async def test_shared_rate_limiter():
       """Verify single rate limiter instance across all requests."""
       client = AsanaClient(token=...)

       # Access internal rate limiter
       rate_limiter_1 = client._shared_rate_limiter

       # Make requests via different clients
       await client.tasks.get_async("123")
       await client.projects.get_async("456")

       # Verify same instance
       rate_limiter_2 = client._http._rate_limiter
       assert rate_limiter_1 is rate_limiter_2
   ```

3. **Retry Warning Count**
   ```python
   async def test_retry_warnings_reduced():
       """Verify retry warnings < 10 during parallel fetch."""
       with log_capture() as logs:
           client = AsanaClient(token=...)
           df_builder = ProjectDataFrameBuilder(...)
           await df_builder.build_async(project_gid)

       retry_warnings = [l for l in logs if "retry" in l.lower()]
       assert len(retry_warnings) < 10
   ```

---

## Rollback Plan

If issues arise during migration:

1. **Feature Flag**: Introduce `ASANA_USE_LEGACY_TRANSPORT=true` environment variable
2. **Gradual Rollout**: Deploy to staging first, monitor for 24 hours
3. **Quick Revert**: If issues, revert to `AsyncHTTPClient` by setting flag

```python
# In AsanaClient.__init__()
import os

if os.environ.get("ASANA_USE_LEGACY_TRANSPORT", "").lower() == "true":
    # Use legacy transport
    self._http = AsyncHTTPClient(config=config, auth_provider=auth_provider, logger=logger)
else:
    # Use new transport
    self._http = AsanaHttpClient(config=config, auth_provider=auth_provider, ...)
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API incompatibility in autom8y-http | Low | High | Pin to specific version, integration tests |
| Performance regression | Medium | Medium | Benchmark comparison, feature flag rollback |
| Subtle behavior differences | Medium | Medium | Comprehensive test coverage, canary deployment |
| Rate limiter contention | Low | Medium | Proper lock implementation in platform SDK |
| Circuit breaker false positives | Low | Low | Conservative thresholds, monitoring |

---

## Success Criteria Traceability

| PRD Criterion | TDD Coverage |
|---------------|--------------|
| SC-001: 2614+ tasks without 429s | FR-002, Integration Test |
| SC-002: Single shared rate limiter | FR-002, Rate limiter scope diagram |
| SC-003: Backward-compatible API | FR-001, Interface contract |
| SC-004: Retry warnings < 10 | FR-002, FR-003, Integration test |
| SC-005: All tests pass | Testing strategy section |
| SC-006: Circuit breaker protection | FR-003, Config translation |
| SC-007: autom8y-http from CodeArtifact | Phase 1 infrastructure |

---

## Appendix A: Full File Inventory

### New Files

| File | Purpose |
|------|---------|
| `src/autom8_asana/transport/asana_http.py` | AsanaHttpClient wrapper |
| `src/autom8_asana/transport/config_translator.py` | Config translation |
| `src/autom8_asana/transport/response_handler.py` | Response handling |
| `tests/unit/transport/test_asana_http.py` | Unit tests |
| `tests/unit/transport/test_config_translator.py` | Unit tests |
| `tests/unit/transport/test_response_handler.py` | Unit tests |
| `tests/integration/test_parallel_fetch_validation.py` | Integration tests |

### Modified Files

| File | Change |
|------|--------|
| `src/autom8_asana/client.py` | Use AsanaHttpClient, shared rate limiter |
| `src/autom8_asana/transport/__init__.py` | Deprecation warnings |
| `pyproject.toml` | Add autom8y-http dependency |

### Deprecated Files (No Changes)

| File | Status |
|------|--------|
| `src/autom8_asana/transport/http.py` | Deprecated, not modified |
| `src/autom8_asana/transport/rate_limiter.py` | Deprecated, not modified |
| `src/autom8_asana/transport/retry.py` | Deprecated, not modified |
| `src/autom8_asana/transport/circuit_breaker.py` | Deprecated, not modified |

---

**End of TDD**
