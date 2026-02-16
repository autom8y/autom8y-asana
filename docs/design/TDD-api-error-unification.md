# TDD: API Error Unification

```yaml
id: TDD-API-ERR-UNIFY-001
initiative: I6
rite: 10x-dev
agent: architect
upstream: ADR-ASANA-004 (Error Handling and HTTP Mapping), api/errors.py
downstream: principal-engineer
date: 2026-02-15
status: ready-for-principal-engineer
```

---

## 1. Executive Summary

The API layer has **two orthogonal error-handling mechanisms** that overlap without clear boundaries:

1. **Centralized exception handlers** in `api/errors.py` -- 10 handlers registered via `register_exception_handlers()` that catch SDK exceptions (e.g., `NotFoundError`, `RateLimitError`) globally and produce structured `ErrorResponse` JSON with `request_id`, error codes, and appropriate HTTP headers.

2. **Inline `HTTPException` raises** across route files -- direct `raise HTTPException(status_code=..., detail=...)` calls that bypass the centralized handlers entirely.

The audit catalogs **75 distinct `HTTPException` sites** across **12 route files**. The core problem is not that inline raises exist -- many are correct and appropriate. The problem is that:

- Inline raises use **inconsistent `detail` formats**: some use structured `{"error": "CODE", "message": "..."}` dicts, some use plain strings, and some omit error codes entirely.
- Inline raises **never include `request_id`** in the response body, violating FR-ERR-008.
- Several inline raises **duplicate behavior** already provided by centralized handlers (e.g., catching `RateLimitError` and manually building a 429 response instead of letting the handler do it).
- The **boundary between the two mechanisms is undocumented**, so each route author makes ad-hoc decisions.

### Decision Summary

| Category | Count | Action |
|----------|------:|--------|
| KEEP (correct as-is) | 9 | No changes needed |
| MIGRATE (should use handler or consistent format) | 63 | Adopt `raise_api_error()` helper |
| REVIEW (needs user input) | 3 | Deferred to implementation |
| HANDLED-BY-CENTRALIZED (already correct) | -- | No changes -- routes let SDK exceptions propagate (users.py, workspaces.py, most of projects.py) |

---

## 2. Current Architecture

### 2.1 Centralized Handler Chain (api/errors.py)

Registered in order (most specific first):

| Exception | HTTP Status | Error Code | Headers |
|-----------|:-----------:|------------|---------|
| `NotFoundError` | 404 | RESOURCE_NOT_FOUND | -- |
| `AuthenticationError` | 401 | INVALID_CREDENTIALS | WWW-Authenticate: Bearer |
| `ForbiddenError` | 403 | FORBIDDEN | -- |
| `RateLimitError` | 429 | RATE_LIMITED | Retry-After |
| `GidValidationError` | 400 | VALIDATION_ERROR | -- |
| `ServerError` | 502 | UPSTREAM_ERROR | -- |
| `TimeoutError` | 504 | UPSTREAM_TIMEOUT | -- |
| `RequestError` (httpx) | 502 | UPSTREAM_ERROR | -- |
| `AsanaError` (catch-all) | 500 | INTERNAL_ERROR | -- |
| `Exception` (catch-all) | 500 | INTERNAL_ERROR | -- |

All handlers produce the `ErrorResponse` model:
```json
{
  "error": {"code": "...", "message": "...", "details": null},
  "meta": {"request_id": "...", "timestamp": "..."}
}
```

### 2.2 Service Error Pattern (services/errors.py)

Routes using `ServiceError` subclasses follow a consistent pattern:
```python
try:
    result = await some_service.do_thing(...)
except ServiceError as e:
    raise HTTPException(status_code=get_status_for_error(e), detail=e.to_dict())
```

The `to_dict()` format is: `{"error": "CODE", "message": "..."}` -- structurally compatible with the centralized handler format **but missing `meta.request_id`**.

### 2.3 Query Engine Error Pattern (query/errors.py)

Similar to ServiceError but uses dataclasses:
```python
except QueryEngineError as e:
    raise HTTPException(status_code=..., detail=e.to_dict())
```

Same format: `{"error": "CODE", "message": "..."}` without `request_id`.

---

## 3. Audit Matrix

### Legend

- **KEEP**: Direct HTTPException is the correct approach. The error is route-specific (input validation, precondition check) and no SDK exception applies.
- **MIGRATE**: Should adopt the `raise_api_error()` helper for consistent formatting (adds `request_id`, standardizes structure).
- **REVIEW**: Ambiguous -- may require user input on whether to change behavior.
- **HANDLER**: Route correctly lets SDK exceptions propagate to centralized handlers (no HTTPException raised -- included for completeness).

### 3.1 admin.py (3 sites)

| # | Line | Status | Detail Format | Category | Notes |
|---|-----:|--------|---------------|----------|-------|
| 1 | 408 | 400 | `{"error": "INVALID_ENTITY_TYPE", ...}` | MIGRATE | Input validation -- correct status but missing request_id |
| 2 | 423 | 503 | `{"error": "CACHE_NOT_INITIALIZED", ...}` | MIGRATE | Precondition check -- correct status but missing request_id |
| 3 | 435 | 503 | `{"error": "REGISTRY_NOT_READY", ...}` | MIGRATE | Precondition check -- correct status but missing request_id |

### 3.2 dataframes.py (3 sites)

| # | Line | Status | Detail Format | Category | Notes |
|---|-----:|--------|---------------|----------|-------|
| 4 | 199 | 400 | `e.to_dict()` (InvalidSchemaError) | MIGRATE | ServiceError subclass -- should use helper for request_id |
| 5 | 286 | 400 | `e.to_dict()` (InvalidSchemaError) | MIGRATE | Same as above |
| 6 | 297 | varies | `e.to_dict()` (EntityNotFoundError) | MIGRATE | Uses get_status_for_error() -- correct but missing request_id |

### 3.3 entity_write.py (10 sites)

| # | Line | Status | Detail Format | Category | Notes |
|---|-----:|--------|---------------|----------|-------|
| 7 | 147 | 503 | `{"error": "DISCOVERY_INCOMPLETE", ...}` | MIGRATE | Precondition -- missing request_id |
| 8 | 167 | 404 | `{"error": "UNKNOWN_ENTITY_TYPE", ...}` | MIGRATE | Input validation -- missing request_id |
| 9 | 191 | 503 | `{"error": "BOT_PAT_UNAVAILABLE", ...}` | MIGRATE | Infrastructure -- missing request_id |
| 10 | 214 | 404 | `{"error": "TASK_NOT_FOUND", ...}` | MIGRATE | Could let centralized NotFoundError handler catch, but TaskNotFoundError is a ServiceError, not SDK NotFoundError |
| 11 | 222 | 404 | `exc.to_dict()` (EntityTypeMismatchError) | MIGRATE | ServiceError -- missing request_id |
| 12 | 227 | 422 | `{"error": "NO_VALID_FIELDS", ...}` | MIGRATE | Validation -- missing request_id |
| 13 | 239 | 429 | `{"error": "RATE_LIMITED", ...}` | REVIEW | Duplicates centralized RateLimitError handler but adds custom detail; could let propagate but loses per-route logging. Route re-catches SDK exception to add entity_write-specific context. |
| 14 | 255 | 504 | `{"error": "ASANA_TIMEOUT", ...}` | REVIEW | Same -- duplicates centralized TimeoutError handler with entity_write-specific logging |
| 15 | 271 | 502 | `{"error": "ASANA_UPSTREAM_ERROR", ...}` | REVIEW | Same -- duplicates centralized ServerError handler with entity_write-specific logging |
| 16 | 290 | 502 | `{"error": "ASANA_UPSTREAM_ERROR", ...}` | MIGRATE | Catch-all boundary -- correct but missing request_id |

### 3.4 health.py (0 sites)

No HTTPException usage. Health endpoints return JSONResponse directly with status codes set inline. This is correct -- health checks follow a different contract.

### 3.5 internal.py (6 sites)

| # | Line | Status | Detail Format | Category | Notes |
|---|-----:|--------|---------------|----------|-------|
| 17 | 63 | 401 | `{"error": "MISSING_AUTH", ...}` | KEEP | Auth dependency -- correct and necessary; WWW-Authenticate header included |
| 18 | 73 | 401 | `{"error": "INVALID_SCHEME", ...}` | KEEP | Auth dependency -- correct |
| 19 | 82 | 401 | `{"error": "MISSING_TOKEN", ...}` | KEEP | Auth dependency -- correct |
| 20 | 121 | 401 | `{"error": "SERVICE_TOKEN_REQUIRED", ...}` | KEEP | Auth dependency -- correct; WWW-Authenticate header |
| 21 | 142 | 503 | `{"error": "S2S_NOT_CONFIGURED", ...}` | KEEP | Infrastructure check in auth dependency -- correct |
| 22 | 160 | 401 | `{"error": <dynamic>, ...}` | KEEP | JWT validation failure -- dynamic error code from library; correct |

**Rationale for KEEP**: These are auth dependency functions (`_extract_bearer_token`, `require_service_claims`) invoked via `Depends()`. They run before route logic and must fail fast with specific auth errors. The centralized handlers do not cover these cases because the exceptions are not SDK-level. Migrating these to `raise_api_error()` is acceptable for format consistency but the status codes and behavior are correct.

### 3.6 projects.py (1 site)

| # | Line | Status | Detail Format | Category | Notes |
|---|-----:|--------|---------------|----------|-------|
| 23 | 207 | 400 | `{"error": "INVALID_PARAMETER", ...}` | MIGRATE | Input validation -- missing request_id |

All other project endpoints (get, create, delete, list_sections, add/remove members) rely on the centralized handlers via SDK exception propagation. This is the gold standard pattern.

### 3.7 query.py (12 sites)

| # | Line | Status | Detail Format | Category | Notes |
|---|-----:|--------|---------------|----------|-------|
| 24 | 141 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 25 | 148 | 422 | `e.to_dict()` (InvalidFieldError) | MIGRATE | Validation -- missing request_id |
| 26 | 155 | 422 | `e.to_dict()` (InvalidFieldError) | MIGRATE | Validation -- missing request_id |
| 27 | 181 | 503 | `{"error": "CACHE_NOT_WARMED", ...}` | MIGRATE | Precondition -- missing request_id |
| 28 | 269 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 29 | 277 | 422 | `{"error": "UNKNOWN_SECTION", ...}` | MIGRATE | Validation -- missing request_id |
| 30 | 316 | 400 | `e.to_dict()` (QueryTooComplexError) | MIGRATE | Query error -- missing request_id |
| 31 | 318 | 422 | `e.to_dict()` (UnknownFieldError) | MIGRATE | Query error -- missing request_id |
| 32 | 320 | 422 | `e.to_dict()` (InvalidOperatorError) | MIGRATE | Query error -- missing request_id |
| 33 | 322 | 422 | `e.to_dict()` (CoercionError) | MIGRATE | Query error -- missing request_id |
| 34 | 324 | 422 | `e.to_dict()` (UnknownSectionError) | MIGRATE | Query error -- missing request_id |
| 35 | 326 | 503 | `{"error": "CACHE_NOT_WARMED", ...}` | MIGRATE | Precondition -- missing request_id |

### 3.8 query_v2.py (6 sites)

| # | Line | Status | Detail Format | Category | Notes |
|---|-----:|--------|---------------|----------|-------|
| 36 | 52 | varies | via `_error_to_response()` helper | MIGRATE | Good local pattern but detail lacks request_id |
| 37 | 70 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 38 | 90 | varies | via `_error_to_response()` | MIGRATE | Same as #36 |
| 39 | 92 | 503 | `{"error": "CACHE_NOT_WARMED", ...}` | MIGRATE | Precondition -- missing request_id |
| 40 | 135 | varies | `e.to_dict()` (ServiceError) | MIGRATE | Same as #37 |
| 41 | 154 | varies | via `_error_to_response()` | MIGRATE | Same as #36 |
| 42 | 156 | 503 | `{"error": "CACHE_NOT_WARMED", ...}` | MIGRATE | Same as #39 |

### 3.9 resolver.py (8 sites)

| # | Line | Status | Detail Format | Category | Notes |
|---|-----:|--------|---------------|----------|-------|
| 43 | 229 | 404 | `{"error": "UNKNOWN_ENTITY_TYPE", ...}` | MIGRATE | Input validation -- missing request_id |
| 44 | 252 | 503 | `{"error": "DISCOVERY_INCOMPLETE", ...}` | MIGRATE | Precondition -- missing request_id |
| 45 | 272 | 503 | `{"error": "PROJECT_NOT_CONFIGURED", ...}` | MIGRATE | Precondition -- missing request_id |
| 46 | 294 | 501 | `{"error": "STRATEGY_NOT_IMPLEMENTED", ...}` | MIGRATE | Only 501 in the codebase -- missing request_id |
| 47 | 309 | 422 | `{"error": "MISSING_REQUIRED_FIELD", ...}` | MIGRATE | Validation -- missing request_id |
| 48 | 323 | 422 | `{"error": "INVALID_FIELD", ...}` | MIGRATE | Validation -- missing request_id |
| 49 | 347 | 503 | `{"error": "BOT_PAT_UNAVAILABLE", ...}` | MIGRATE | Infrastructure -- missing request_id |
| 50 | 374 | 500 | `{"error": "RESOLUTION_ERROR", ...}` | MIGRATE | Catch-all boundary -- missing request_id |

### 3.10 resolver_schema.py (2 sites)

| # | Line | Status | Detail Format | Category | Notes |
|---|-----:|--------|---------------|----------|-------|
| 51 | 99 | 404 | `{"error": "UNKNOWN_ENTITY_TYPE", ...}` | MIGRATE | Validation -- missing request_id |
| 52 | 113 | 404 | `{"error": "SCHEMA_NOT_FOUND", ...}` | MIGRATE | Not found -- missing request_id |

### 3.11 sections.py (6 sites)

| # | Line | Status | Detail Format | Category | Notes |
|---|-----:|--------|---------------|----------|-------|
| 53 | 65 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 54 | 95 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 55 | 124 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 56 | 150 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 57 | 180 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 58 | 221 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |

### 3.12 tasks.py (14 sites)

| # | Line | Status | Detail Format | Category | Notes |
|---|-----:|--------|---------------|----------|-------|
| 59 | 110 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 60 | 157 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 61 | 198 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 62 | 239 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 63 | 266 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 64 | 306 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 65 | 353 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 66 | 392 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 67 | 424 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 68 | 453 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 69 | 487 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 70 | 516 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 71 | 545 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |
| 72 | 575 | varies | `e.to_dict()` (ServiceError) | MIGRATE | ServiceError -- missing request_id |

Note: tasks.py is the cleanest route file -- it delegates all business logic to `TaskService` and catches only `ServiceError`. The only issue is format consistency (missing request_id).

### 3.13 users.py (0 sites)

No HTTPException usage. All user endpoints delegate to SDK methods and rely entirely on centralized exception handlers. This is the ideal pattern for pass-through CRUD routes.

### 3.14 webhooks.py (3 HTTPException sites + 4 JSONResponse returns)

| # | Line | Status | Detail Format | Category | Notes |
|---|-----:|--------|---------------|----------|-------|
| 73 | 133 | 503 | `{"error": "WEBHOOK_NOT_CONFIGURED", ...}` | KEEP | Auth dependency -- correct |
| 74 | 146 | 401 | `{"error": "MISSING_TOKEN", ...}` | KEEP | Auth dependency -- correct |
| 75 | 159 | 401 | `{"error": "INVALID_TOKEN", ...}` | KEEP | Auth dependency -- correct |

Note: Lines 329, 339, 357, 373 use `return JSONResponse(status_code=400, ...)` directly instead of HTTPException. These are **not** HTTPException sites but they also lack request_id. The 400 returns for invalid JSON, empty body, missing GID, and invalid task are appropriate (webhook endpoint returns 200/400 directly without raising). These are discussed in Section 5.3.

### 3.15 workspaces.py (0 sites)

No HTTPException usage. Like users.py, relies entirely on centralized handlers. Ideal.

---

## 4. Convention ADR

### ADR-I6-001: API Error Response Convention

**Status**: Proposed

#### Context

The codebase has two error paths that produce different response formats:
1. Centralized handlers produce `ErrorResponse` with `request_id`
2. Inline HTTPException raises produce ad-hoc dicts without `request_id`

FR-ERR-008 requires all error responses include `request_id` for correlation. The current inline raises violate this requirement.

#### Decision

Establish three error-handling tiers with clear boundaries:

**Tier 1: Let SDK Exceptions Propagate (preferred for CRUD pass-through)**

Routes that call SDK methods directly (projects, users, workspaces) should NOT catch SDK exceptions. Let them propagate to the centralized handlers in `api/errors.py`.

```python
# CORRECT: Let SDK NotFoundError propagate to centralized handler
project = await client.projects.get_async(gid, raw=True)
```

**When to use**: Route is a thin wrapper around an SDK call with no additional error semantics.

**Tier 2: Catch ServiceError/QueryEngineError and Convert (preferred for service-layer delegation)**

Routes that delegate to service objects should catch `ServiceError` (or `QueryEngineError`) and convert via the new `raise_api_error()` helper.

```python
# CORRECT: Service error with consistent format
try:
    result = await task_service.get_task(client, gid)
except ServiceError as e:
    raise_api_error(request, get_status_for_error(e), e.error_code, e.message)
```

**When to use**: Route delegates to a service layer that raises domain exceptions.

**Tier 3: Direct HTTPException with raise_api_error() (for route-specific validation)**

Routes that perform input validation or precondition checks before calling any service should use the `raise_api_error()` helper directly.

```python
# CORRECT: Input validation with consistent format
if body.entity_type not in VALID_ENTITY_TYPES:
    raise_api_error(request, 400, "INVALID_ENTITY_TYPE", f"Invalid: {body.entity_type}")
```

**When to use**: Error is route-layer logic (input validation, precondition check, auth guard) where no service exception applies.

**Tier 4: Auth Dependencies (KEEP as-is)**

Auth dependency functions (`_extract_bearer_token`, `require_service_claims`, `verify_webhook_token`) may continue raising `HTTPException` directly. These functions do not have access to structured request state in all cases, and they are security boundaries where simplicity outweighs format consistency. However, if the implementation chooses to add request_id to these as well, that is acceptable.

#### Alternatives Considered

**Option A: Register More Exception Handlers (rejected)**

Add centralized handlers for `ServiceError`, `QueryEngineError`, `CacheNotWarmError`, etc., so routes never raise `HTTPException`.

- Pros: No inline raises at all; maximum consistency
- Cons: Loses per-route context (entity_type, operation name in logs); handler registration order becomes complex; `ServiceError` hierarchy intersects with SDK hierarchy causing ambiguity; large blast radius
- Rejected because: The service error hierarchy is route-contextual. A `TaskNotFoundError` from `entity_write` needs different context than one from `tasks`. Centralizing all error mapping would strip context that routes currently log.

**Option B: Do Nothing (rejected)**

Document the current state and accept inconsistency.

- Pros: Zero risk, no code changes
- Cons: FR-ERR-008 violation persists; every new route must guess the pattern; debugging production issues without request_id in error responses is harder
- Rejected because: The request_id gap is a real operational problem for cross-service debugging.

**Option C: Full ErrorResponse Model Everywhere (rejected)**

Replace all `raise HTTPException(detail=...)` with `return JSONResponse(content=ErrorResponse(...).model_dump(), status_code=...)`.

- Pros: Complete format control
- Cons: Loses FastAPI's built-in exception handling; every route must import and construct ErrorResponse manually; test assertions need updating
- Rejected because: HTTPException is the idiomatic FastAPI pattern and the test infrastructure is built around it.

#### Rationale

Option: **Thin helper function** (`raise_api_error`) that wraps `HTTPException` with consistent `detail` formatting. This achieves format consistency with minimal code changes, preserves the HTTPException flow that tests expect, and lets routes keep their per-operation context logging.

#### Consequences

**Positive**:
- All error responses include `request_id` (FR-ERR-008 compliance)
- Consistent `{"error": "CODE", "message": "...", "request_id": "..."}` format
- No new abstraction layers or exception types
- Routes remain readable

**Negative**:
- Response format for inline errors still differs slightly from centralized handler format (flat dict vs nested ErrorResponse). Full alignment is a future option.
- 63+ call sites to update (mechanical but tedious)

**Neutral**:
- Auth dependency HTTPException raises optionally updated (KEEP is acceptable)
- webhook JSONResponse returns are a separate concern (see Section 5.3)

---

## 5. Migration Design

### 5.1 The Helper Function

Add a single function to `api/errors.py`:

```python
from fastapi import HTTPException, Request

def raise_api_error(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Never:
    """Raise HTTPException with consistent error format.

    Ensures all route-level error responses include:
    - Machine-readable error code
    - Human-readable message
    - request_id for correlation (per FR-ERR-008)

    Args:
        request: FastAPI request (for request_id extraction).
        status_code: HTTP status code.
        code: Machine-readable error code (e.g., "INVALID_ENTITY_TYPE").
        message: Human-readable error description.
        details: Additional structured context (optional).
        headers: Additional HTTP headers (e.g., Retry-After).

    Raises:
        HTTPException: Always raised, never returns.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    detail: dict[str, Any] = {
        "error": code,
        "message": message,
        "request_id": request_id,
    }
    if details:
        detail.update(details)
    raise HTTPException(
        status_code=status_code,
        detail=detail,
        headers=headers,
    )
```

### 5.2 Migration Convenience for ServiceError / QueryEngineError

For the common pattern of catching `ServiceError` and converting, add a second convenience:

```python
def raise_service_error(
    request: Request,
    error: ServiceError,
    *,
    headers: dict[str, str] | None = None,
) -> Never:
    """Raise HTTPException from a ServiceError with consistent format.

    Args:
        request: FastAPI request (for request_id).
        error: ServiceError instance with error_code, message, and to_dict().
        headers: Additional HTTP headers.

    Raises:
        HTTPException: Always raised.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    detail = error.to_dict()
    detail["request_id"] = request_id
    raise HTTPException(
        status_code=get_status_for_error(error),
        detail=detail,
        headers=headers,
    )
```

This means the common pattern changes from:
```python
# Before
except ServiceError as e:
    raise HTTPException(status_code=get_status_for_error(e), detail=e.to_dict())

# After
except ServiceError as e:
    raise_service_error(request, e)
```

A similar helper for `QueryEngineError` can be added if desired, or the generic `raise_api_error` can be used with `e.to_dict()` unpacking.

### 5.3 Webhook JSONResponse Returns (Out of Scope)

The webhook `receive_inbound_webhook` endpoint uses `return JSONResponse(status_code=400, ...)` for parse errors. These are NOT `HTTPException` raises -- they are direct returns. This is an intentional design choice: the webhook endpoint must return 200/400 reliably without exception propagation overhead.

**Recommendation**: Leave these as-is. They are a single endpoint with a unique contract (Asana Rules action receiver). If request_id is desired in webhook error responses, add it to the JSONResponse content dict directly during a future webhook-specific pass.

### 5.4 entity_write.py REVIEW Items (Sites #13, #14, #15)

These three sites catch SDK exceptions (`RateLimitError`, `AsanaTimeoutError`, `ServerError`) that the centralized handlers would also catch. The routes re-catch them to add entity_write-specific logging before raising HTTPException.

**Two valid approaches**:

A. **Remove the re-catches; let propagate**: The centralized handlers will produce the correct response. The per-route logging is lost, but the centralized handlers log equivalent information (request_id, error type).

B. **Keep the re-catches but use raise_api_error()**: Preserves the per-route logging context. The response format becomes consistent. The trade-off is duplicated error handling.

**Recommendation**: Option B (keep re-catches, use helper) because the per-route logging adds `gid`, `entity_type`, and `caller_service` context that the centralized handlers do not have. This is a write endpoint where audit trail matters.

---

## 6. Implementation Guidance

### 6.1 File Changes

| File | Sites | Change Type |
|------|------:|-------------|
| `api/errors.py` | 0 | Add `raise_api_error()` and `raise_service_error()` |
| `api/routes/admin.py` | 3 | Convert to `raise_api_error()` |
| `api/routes/dataframes.py` | 3 | Convert to `raise_service_error()` or `raise_api_error()` |
| `api/routes/entity_write.py` | 10 | Convert to `raise_api_error()` / `raise_service_error()` |
| `api/routes/internal.py` | 6 | KEEP (auth dependency -- optionally convert) |
| `api/routes/projects.py` | 1 | Convert to `raise_api_error()` |
| `api/routes/query.py` | 12 | Convert to `raise_api_error()` / `raise_service_error()` |
| `api/routes/query_v2.py` | 6 | Convert `_error_to_response()` + inline raises |
| `api/routes/resolver.py` | 8 | Convert to `raise_api_error()` |
| `api/routes/resolver_schema.py` | 2 | Convert to `raise_api_error()` |
| `api/routes/sections.py` | 6 | Convert to `raise_service_error()` |
| `api/routes/tasks.py` | 14 | Convert to `raise_service_error()` |
| `api/routes/webhooks.py` | 3 | KEEP (auth dependency) |

### 6.2 Migration Order (Recommended)

1. **Add helpers** to `api/errors.py` (zero behavioral change)
2. **Migrate tasks.py** first -- 15 sites, all identical pattern, best candidate for mechanical find-and-replace. Run tests.
3. **Migrate sections.py** -- 6 sites, same pattern as tasks.py. Run tests.
4. **Migrate query.py and query_v2.py** -- 18 sites total. query_v2.py has the `_error_to_response()` helper which should be replaced or made to call `raise_api_error()` internally. Run tests.
5. **Migrate resolver.py and resolver_schema.py** -- 10 sites. Run tests.
6. **Migrate admin.py, dataframes.py, entity_write.py, projects.py** -- remaining 16 sites. Run tests.
7. **Optionally migrate internal.py and webhooks.py** auth guards -- 9 sites, KEEP is acceptable.

### 6.3 Request Dependency

Many MIGRATE sites need `request: Request` to extract `request_id`. Check that each route handler already has a `request` parameter or can obtain request_id from the existing `RequestId` dependency.

Routes that currently lack `request` parameter:
- **dataframes.py**: Uses `RequestId` (Annotated dependency) -- request_id is available but `Request` object is not. The `raise_api_error()` helper needs either `Request` or a raw `request_id` string. **Design note**: Add an overload or accept `request_id: str` as an alternative parameter.
- **sections.py**: Some endpoints do not have `request: Request` -- they use `RequestId`. Same concern.

**Resolution**: The helper should accept either `Request` or `str` for the request_id:

```python
def raise_api_error(
    request_or_id: Request | str,
    status_code: int,
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Never:
    if isinstance(request_or_id, str):
        request_id = request_or_id
    else:
        request_id = getattr(request_or_id.state, "request_id", "unknown")
    ...
```

### 6.4 Test Impact

Existing tests assert on `HTTPException.detail` content. The migration adds a `request_id` field to every `detail` dict. Tests that do:
```python
assert exc.detail == {"error": "...", "message": "..."}
```
will need updating to either:
- Include `request_id` in the expected dict
- Assert only on `detail["error"]` and `detail["message"]` (preferred -- more resilient)

**Estimated test changes**: ~50-80 test assertions across route test files.

---

## 7. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|:----------:|:------:|------------|
| Test assertions break on detail format change | HIGH | LOW | Mechanical updates; grep for `detail=` in test files |
| External consumers parse error detail format | LOW | MEDIUM | Adding fields is backward-compatible; no existing fields removed |
| request_id not available in some contexts | LOW | LOW | Helper falls back to "unknown" if request.state.request_id missing |
| Large PR with 63+ sites changes | MEDIUM | LOW | Split into 6 ordered PRs per Section 6.2 migration order |
| entity_write REVIEW items (#13-15) change behavior | LOW | MEDIUM | Keep re-catches per Section 5.4 recommendation |

---

## 8. Success Criteria

- [ ] All error responses from route files include `request_id` (FR-ERR-008)
- [ ] All error responses use `{"error": "CODE", "message": "...", "request_id": "..."}` format
- [ ] No new exception classes introduced
- [ ] No new centralized exception handlers registered
- [ ] All existing tests pass (with updated assertions)
- [ ] Auth dependency raises (internal.py, webhooks.py) are documented as KEEP
- [ ] `raise_api_error()` and `raise_service_error()` are the only new functions added

---

## 9. Non-Functional Considerations

### 9.1 Performance

Zero impact. The helper function adds one `getattr()` call and one dict merge per error path. Error paths are by definition not hot paths.

### 9.2 Security

No change to error information exposure. The `request_id` is already present in response headers (set by middleware) -- adding it to the error body is consistent, not a new disclosure.

### 9.3 Observability

Improved. Every error response now carries `request_id` in the body, enabling consumers to correlate errors with server-side logs without parsing response headers.

---

## 10. Open Items

| Item | Owner | Status |
|------|-------|--------|
| entity_write.py sites #13-15: keep re-catches or let propagate? | Architect | Recommended: keep (Section 5.4) -- confirm with user |
| Should internal.py auth dependency raises also use helper? | Architect | Recommended: KEEP for now, optional future pass |
| query_v2.py `_error_to_response()` helper: replace or wrap? | Principal Engineer | Implementation choice -- either is acceptable |
| Full ErrorResponse model alignment (nested vs flat format) | Future | Deferred -- flat format with request_id is sufficient for I6 |
