---
artifact_id: ADR-0061
title: "Thin Wrapper Strategy for autom8y-http Migration"
created_at: "2026-01-03T15:45:00Z"
author: architect
status: accepted
context: "autom8_asana needs to migrate from custom HTTP transport primitives to the autom8y-http platform SDK. The migration must preserve backward compatibility while eliminating duplicated infrastructure and enabling coordinated rate limiting."
decision: "Use a thin wrapper (AsanaHttpClient) around Autom8yHttpClient that handles only Asana-specific response transformation, delegating all HTTP policy enforcement to the platform client."
consequences:
  - type: positive
    description: "Minimal maintenance burden - Asana-specific logic isolated to one module"
  - type: positive
    description: "Platform improvements automatically benefit autom8_asana"
  - type: positive
    description: "Clear separation between protocol (HTTP) and application (Asana API) concerns"
  - type: positive
    description: "Backward compatibility preserved through interface parity"
  - type: negative
    description: "One additional layer of indirection in request path"
    mitigation: "Overhead is negligible (single function call) compared to network latency"
  - type: negative
    description: "Platform SDK version must be pinned and tested with each upgrade"
    mitigation: "Include autom8y-http version in integration test matrix"
  - type: neutral
    description: "Deprecation warnings for direct transport access may require consumer updates"
related_artifacts:
  - PRD-asana-http-migration-001
  - TDD-asana-http-migration-001
  - ADR-0062
tags:
  - transport
  - migration
  - platform-sdk
  - architecture
schema_version: "1.0"
---

# ADR-0061: Thin Wrapper Strategy for autom8y-http Migration

## Context

The autom8_asana SDK has a custom HTTP transport layer implementing:
- Token bucket rate limiting
- Exponential backoff retry with jitter
- Circuit breaker for cascading failure prevention
- Connection pool management

These components duplicate functionality now available in the autom8y-http platform SDK. The parallel section fetch pattern exposes a critical flaw: each `AsyncHTTPClient` instance has its own rate limiter, causing uncoordinated request bursts during concurrent operations.

Three migration strategies were considered:

1. **Direct Replacement**: Replace `AsyncHTTPClient` entirely with `Autom8yHttpClient`
2. **Facade Pattern**: Create adapter implementing `AsyncHTTPClient` interface, delegating to `Autom8yHttpClient`
3. **Thin Wrapper**: Create new `AsanaHttpClient` class wrapping `Autom8yHttpClient` with Asana-specific logic only

## Decision

We will use the **Thin Wrapper** strategy, creating `AsanaHttpClient` that:

1. **Delegates all HTTP operations** to `Autom8yHttpClient`
2. **Handles only Asana-specific concerns**:
   - Response envelope unwrapping (`{"data": ...}`)
   - Error response parsing (429, 5xx, 4xx -> domain exceptions)
   - Pagination extraction (`next_page.offset`)
3. **Accepts injected policies** (rate limiter, circuit breaker) rather than creating its own
4. **Exposes backward-compatible interface** matching `AsyncHTTPClient` method signatures

### Why Not Direct Replacement?

Direct replacement would require:
- Modifying all call sites to handle `httpx.Response` instead of unwrapped data
- Losing Asana-specific error translation
- Significant breaking changes to public API

### Why Not Facade Pattern?

Facade pattern would:
- Preserve `AsyncHTTPClient` as the public type (tight coupling)
- Make it harder to deprecate legacy code
- Conflate "old API preserved" with "new implementation"

### Why Thin Wrapper?

Thin wrapper provides:
- Clean break from legacy types (new class, new module)
- Minimal code in wrapper (just transformation, no policy)
- Clear ownership: platform owns HTTP, wrapper owns Asana
- Easy to test wrapper logic in isolation

## Implementation

```python
# src/autom8_asana/transport/asana_http.py

class AsanaHttpClient:
    """Asana HTTP client wrapping autom8y-http platform client.

    This is a thin wrapper that:
    1. Delegates all HTTP operations to Autom8yHttpClient
    2. Unwraps Asana response envelope {"data": ...}
    3. Translates errors to domain exceptions
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
        # Translate config
        http_config = ConfigTranslator.to_http_client_config(config)

        # Create platform client with injected policies
        self._platform_client = Autom8yHttpClient(
            config=http_config,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            logger=logger,
        )

        self._response_handler = AsanaResponseHandler()

    async def get(self, path: str, *, params: dict | None = None) -> dict:
        response = await self._platform_client.get(path, params=params)
        return self._response_handler.unwrap_response(response)

    # ... similar for post, put, delete, get_paginated
```

## Consequences

### Positive

1. **Minimal maintenance**: The wrapper contains only ~200 lines of Asana-specific transformation logic. All HTTP complexity lives in the platform SDK.

2. **Automatic platform upgrades**: When autom8y-http adds features (e.g., OpenTelemetry tracing), autom8_asana benefits without code changes.

3. **Clear separation of concerns**: HTTP protocol handling (timeouts, retries, rate limiting) is platform responsibility. Asana API semantics (response format, error codes) is wrapper responsibility.

4. **Backward compatibility**: Method signatures match `AsyncHTTPClient`, enabling drop-in replacement in `AsanaClient`.

### Negative

1. **Additional indirection**: Each request passes through wrapper before platform client. Mitigation: Overhead is a single function call, negligible compared to network RTT.

2. **Version coupling**: autom8_asana depends on specific autom8y-http version. Mitigation: Pin version in pyproject.toml, test upgrades in CI.

### Neutral

1. **Deprecation warnings**: Existing code importing `AsyncHTTPClient` directly will see warnings. This is intentional to guide migration.

## Alternatives Considered

### Alternative A: Direct Replacement

Replace all uses of `AsyncHTTPClient` with `Autom8yHttpClient`.

**Rejected because**:
- Breaking change to public API (consumers expect unwrapped data)
- Loses Asana-specific error translation
- No clear path to deprecate old code

### Alternative B: Facade Pattern

Create `AsyncHTTPClient` facade delegating to `Autom8yHttpClient`.

**Rejected because**:
- Preserves legacy type as public API
- Harder to communicate "this is new implementation"
- Conflates interface preservation with implementation change

## References

- PRD-ASANA-HTTP-MIGRATION-001: Requirements for migration
- TDD-ASANA-HTTP-MIGRATION-001: Technical design
- ADR-0062: Rate limiter coordination approach (companion decision)
- autom8y-http documentation
