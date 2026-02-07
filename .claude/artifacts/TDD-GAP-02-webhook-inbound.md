# TDD-GAP-02: Webhook Inbound Event Handler

**Status**: APPROVED
**PRD**: PRD-GAP-02-webhook-inbound (approved)
**Complexity**: MODULE
**Author**: Architect
**Date**: 2026-02-07

---

## 1. Overview

### 1.1 Problem

autom8_asana has no way to react to real-time Asana task changes. The system can manage webhook subscriptions and verify signatures, but nothing listens. Every minute a task change goes unhandled is a minute of stale data and missed automation triggers.

### 1.2 Solution

Add a single POST endpoint (`/api/v1/webhooks/inbound`) that receives Asana Rules action payloads, verifies a URL token, parses the task JSON into the existing `Task` model, invalidates stale cache entries, and dispatches through a typed protocol seam. V1 uses Asana Rules (outbound HTTP actions configured in Asana UI). V2 will add Webhooks API support (handshake, HMAC, event envelopes).

### 1.3 Key Design Decisions

1. **Standalone cache invalidation function** -- not reusing `CacheInvalidator` (see ADR-GAP02-001)
2. **FastAPI `Depends()` for token verification** -- follows existing auth pattern conventions
3. **No new pip dependencies** -- uses stdlib `hmac.compare_digest` and FastAPI `BackgroundTasks`
4. **Dispatch protocol as a `typing.Protocol`** -- in the webhooks module itself for V1

---

## 2. Investigation Results

### 2.1 Cache Invalidation Wiring

**Files examined**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/cache_invalidator.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/mutation_invalidator.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/entry.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py`

**Findings**:

The project has **two** existing invalidation paths:

1. **`CacheInvalidator`** (`persistence/cache_invalidator.py`): Designed for `SaveSession` commits. Accepts `SaveResult` + `ActionResult` + `gid_to_entity_lookup`. Tightly coupled to the persistence layer's data structures.

2. **`MutationInvalidator`** (`cache/integration/mutation_invalidator.py`): Designed for REST route handlers. Accepts `MutationEvent` dataclasses. Supports fire-and-forget via `asyncio.create_task`. Has soft/hard invalidation config.

Both call the same underlying primitive: `CacheProvider.invalidate(key, entry_types)`. The `CacheProvider` protocol defines `invalidate(key: str, entry_types: list[EntryType] | None = None) -> None`.

The `_TASK_ENTRY_TYPES` constant in `MutationInvalidator` is exactly what we need: `[EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]`.

**Key insight**: The cache provider is obtained via `CacheProviderFactory.create()` (from `cache/integration/factory.py`) and stored on `app.state.mutation_invalidator` during startup. For the webhook handler, we can access the same cache provider through `app.state.mutation_invalidator._cache` or create a new one. However, the simplest approach is a standalone function that takes a `CacheProvider` and does the `modified_at` comparison + invalidation, since the webhook's needs are simpler than either existing invalidator.

**Decision**: Create a standalone `invalidate_stale_task_cache()` function (see ADR-GAP02-001). Does not reuse or extend either existing invalidator -- their interfaces are wrong for this use case.

### 2.2 Auth Patterns

**Files examined**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/dependencies.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/middleware.py`

**Findings**:

Authentication is implemented as **FastAPI dependency injection**, not middleware:
- `get_auth_context()` is a `Depends()` function that extracts Bearer tokens from `Authorization` header
- Routes requiring auth declare `auth_context: Annotated[AuthContext, Depends(get_auth_context)]`
- Routes NOT requiring auth simply do not declare this dependency (e.g., health routes have no auth dependency)

This means **there is no global auth middleware to exclude the webhook route from**. Auth is opt-in per route via `Depends()`. The webhook route simply needs to NOT use `get_auth_context` and instead use its own `verify_webhook_token` dependency.

The `RequestLoggingMiddleware` logs `request.url.path` (not query params), so URL tokens in query parameters are already safe from middleware logging. The middleware also applies to all routes, which is correct -- we want request logging on webhooks.

The `SENSITIVE_FIELDS` frozenset in middleware already includes `"token"`, so any structlog event containing a key with "token" in it will be redacted automatically.

**Decision**: Implement `verify_webhook_token()` as a FastAPI `Depends()` function, consistent with existing auth patterns. No middleware changes needed.

### 2.3 Route Patterns

**Files examined**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/__init__.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/health.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/tasks.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py`

**Findings**:

Route pattern is consistent:
1. Each route module defines `router = APIRouter(prefix="/...", tags=["..."])`
2. `routes/__init__.py` imports `router as {name}_router`
3. `main.py` imports from `routes` and calls `app.include_router(x_router)`

The `health.py` module demonstrates unauthenticated routes -- they simply do not declare any auth dependency. This confirms the approach from Investigation 2.

Route handlers return `JSONResponse` directly (health) or use response models (tasks). For the webhook endpoint, returning `JSONResponse({"status": "accepted"})` is appropriate.

### 2.4 Existing Models

**Files examined**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/base.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/webhook.py`

**Findings**:

The `Task` model is suitable for direct reuse:
- Extends `AsanaResource` which has `model_config = ConfigDict(extra="ignore")` -- unknown fields are silently ignored
- `AsanaResource` requires `gid: str` (non-optional) -- good for validation
- `Task` has `modified_at: str | None` -- needed for cache staleness comparison
- `Task` has `resource_type: str | None = Field(default="task")` -- good for logging

The `Webhook` model in `models/webhook.py` is for webhook subscription management (the existing CRUD operations), not for inbound event handling. It is a separate concern.

**Decision**: Reuse `Task.model_validate()` directly. No new task models. A thin `InboundTaskPayload` wrapper may be added later for V2 if Asana Rules sends metadata alongside the task, but V1 does not need it since the body IS the task JSON.

### 2.5 Settings Pattern

**Files examined**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/config.py`

**Findings**:

Two settings layers exist:
1. **SDK Settings** (`settings.py`): `Settings` class with nested `Autom8yBaseSettings` sub-models (e.g., `CacheSettings`, `RedisSettings`). Singleton via `get_settings()`.
2. **API Settings** (`api/config.py`): `ApiSettings` with `ASANA_API_` prefix. Singleton via `@lru_cache` `get_settings()`.

Convention for new settings: Add a new nested `Autom8yBaseSettings` sub-model to the SDK `Settings` class, OR a new section in `ApiSettings`. Since webhook configuration is API-layer-specific (endpoint auth), it belongs in `ApiSettings` OR as a standalone settings class.

However, since the webhook token is consumed only by the route module and does not need to be available to the SDK layer, the cleanest approach is a simple settings model in the webhooks route module itself. This follows the principle of locality -- the setting is defined next to the code that uses it.

**Decision**: Add `WebhookSettings` as a new nested sub-model on the SDK `Settings` class in `settings.py`, using `WEBHOOK_` env prefix. This keeps all settings in the centralized singleton and makes the token available during startup validation.

---

## 3. Architecture Decisions

### ADR-GAP02-001: Standalone Cache Invalidation Function

**Context**: The webhook handler needs to invalidate TASK, SUBTASKS, and DETECTION cache entries when inbound `modified_at` is newer than cached. Two existing invalidation services exist (`CacheInvalidator` for persistence, `MutationInvalidator` for REST mutations).

**Alternatives considered**:

| Option | Pros | Cons |
|--------|------|------|
| A. Reuse `CacheInvalidator` | Existing code | Requires `SaveResult`/`ActionResult` args we do not have |
| B. Extend `MutationInvalidator` | Shared invalidation | Requires `MutationEvent` which assumes outbound mutation; no `modified_at` comparison logic |
| C. Standalone function | Simple, testable, no coupling to persistence or mutation abstractions | New code, but minimal (~30 lines) |

**Decision**: Option C -- standalone function `invalidate_stale_task_cache()`.

**Rationale**:
- Both existing invalidators accept domain-specific input types (`SaveResult`, `MutationEvent`) that do not model "inbound webhook notification"
- Neither existing invalidator has `modified_at` comparison logic -- they invalidate unconditionally
- The webhook needs conditional invalidation: only delete if inbound is newer
- A 30-line function with clear inputs (`cache_provider`, `task_gid`, `inbound_modified_at`) is simpler and more testable than adapting either existing class
- The function calls the same `CacheProvider.invalidate()` primitive, maintaining consistency

**Consequences**:
- Third invalidation path in the codebase (acceptable -- each has a distinct trigger context)
- If the invalidation logic grows complex, consider extracting a shared `InvalidationPrimitive` in GAP-03

### ADR-GAP02-002: Token Auth as FastAPI Depends()

**Context**: The webhook endpoint needs URL token verification (`?token=<secret>`) but must not use the standard JWT/PAT auth.

**Decision**: Implement as a `Depends()` function `verify_webhook_token(token: str = Query(...))`.

**Rationale**:
- Auth in this codebase is dependency-based, not middleware-based
- No global auth middleware exists to "exclude" routes from
- `Depends()` is composable, testable, and follows existing patterns
- `Query(...)` extracts the `token` parameter from the URL query string
- Timing-safe comparison via `hmac.compare_digest` (stdlib)

### ADR-GAP02-003: Dispatch Protocol Location

**Context**: The PRD requires a typed dispatch seam where GAP-03 can plug in handlers.

**Decision**: Define `WebhookDispatcher` protocol in `src/autom8_asana/api/routes/webhooks.py` for V1. If GAP-03 needs it importable from elsewhere, move to `src/autom8_asana/protocols/` at that time.

**Rationale**:
- V1 dispatch is a no-op (log and discard)
- Placing the protocol in the route module avoids premature abstraction
- Moving a Protocol class is a backward-compatible change (imports can be aliased)

---

## 4. Component Design

### 4.1 New Files

#### 4.1.1 `src/autom8_asana/api/routes/webhooks.py`

The main route module. Contains the endpoint, auth dependency, dispatch protocol, cache invalidation function, and background task logic.

```python
"""Webhook inbound event handler.

Per TDD-GAP-02 / PRD-GAP-02-webhook-inbound:
- POST /api/v1/webhooks/inbound?token=<secret>
- V1: Asana Rules action payloads (full task JSON)
- V2 extension point: Asana Webhooks API (handshake, HMAC, event envelope)
"""

from __future__ import annotations

import hmac
from typing import Any, Protocol, runtime_checkable

from autom8y_log import get_logger
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from autom8_asana.cache.models.entry import EntryType
from autom8_asana.models.task import Task
from autom8_asana.settings import get_settings

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# Entry types invalidated for inbound task notifications
# Matches MutationInvalidator._TASK_ENTRY_TYPES
_TASK_ENTRY_TYPES = [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]


# ---------------------------------------------------------------------------
# Dispatch Protocol (GAP-03 seam)
# ---------------------------------------------------------------------------

@runtime_checkable
class WebhookDispatcher(Protocol):
    """Protocol for dispatching parsed webhook task payloads.

    V1: No-op implementation (log and discard).
    GAP-03 will provide a real implementation that routes
    events to AutomationEngine, external consumers, etc.

    WARNING: Implementations must be aware of loop risk --
    our outbound writes to Asana may trigger Asana Rules
    that POST back to this endpoint. Loop prevention is
    GAP-03 scope.
    """

    async def dispatch(self, task: Task) -> None:
        """Dispatch a parsed task payload.

        Args:
            task: Parsed Task model from inbound webhook.

        Raises:
            Should not raise -- dispatch errors are logged
            but must not affect the HTTP response.
        """
        ...


class NoOpDispatcher:
    """Default dispatcher that logs and discards.

    Deployed with V1 until GAP-03 provides a real implementation.
    """

    async def dispatch(self, task: Task) -> None:
        """Log task receipt and discard."""
        logger.info(
            "webhook_task_dispatched_noop",
            extra={
                "task_gid": task.gid,
                "resource_type": task.resource_type,
                "modified_at": task.modified_at,
            },
        )


# Module-level dispatcher instance. GAP-03 replaces this.
_dispatcher: WebhookDispatcher = NoOpDispatcher()


def set_dispatcher(dispatcher: WebhookDispatcher) -> None:
    """Replace the default no-op dispatcher.

    Called during app startup when GAP-03 is available.

    Args:
        dispatcher: Implementation of WebhookDispatcher protocol.
    """
    global _dispatcher
    _dispatcher = dispatcher


def get_dispatcher() -> WebhookDispatcher:
    """Get the current dispatcher instance."""
    return _dispatcher


# ---------------------------------------------------------------------------
# Token Verification Dependency
# ---------------------------------------------------------------------------

def verify_webhook_token(
    token: str | None = Query(default=None),
) -> str:
    """Verify the inbound webhook URL token.

    Per FR-03: Timing-safe comparison of URL token against
    configured environment variable.

    Args:
        token: Token from ?token= query parameter.

    Returns:
        The verified token (unused by caller, but confirms auth).

    Raises:
        HTTPException: 401 if token is missing, empty, or incorrect.
        HTTPException: 503 if webhook token is not configured.
    """
    settings = get_settings()

    expected_token = settings.webhook.inbound_token
    if not expected_token:
        logger.error("webhook_token_not_configured")
        raise HTTPException(
            status_code=503,
            detail={"error": "WEBHOOK_NOT_CONFIGURED", "message": "Webhook endpoint is not configured"},
        )

    if not token:
        logger.warning(
            "webhook_token_missing",
            extra={"reason": "no token query parameter"},
        )
        raise HTTPException(
            status_code=401,
            detail={"error": "MISSING_TOKEN", "message": "Authentication required"},
        )

    if not hmac.compare_digest(token, expected_token):
        logger.warning(
            "webhook_token_invalid",
            extra={"reason": "token mismatch"},
        )
        raise HTTPException(
            status_code=401,
            detail={"error": "INVALID_TOKEN", "message": "Authentication failed"},
        )

    return token


# ---------------------------------------------------------------------------
# Cache Invalidation
# ---------------------------------------------------------------------------

def invalidate_stale_task_cache(
    task_gid: str,
    inbound_modified_at: str | None,
    cache_provider: Any,
) -> bool:
    """Delete stale cache entries if inbound task is newer.

    Per FR-10 / SC-007: Compare inbound modified_at against cached
    version. If inbound is newer, invalidate TASK, SUBTASKS, and
    DETECTION entries for the GID.

    Args:
        task_gid: The Asana task GID.
        inbound_modified_at: ISO 8601 modified_at from inbound payload.
            If None, skip invalidation (cannot compare).
        cache_provider: CacheProvider instance with get_versioned/invalidate.

    Returns:
        True if invalidation occurred, False if skipped.
    """
    if not inbound_modified_at:
        logger.warning(
            "webhook_cache_skip_no_modified_at",
            extra={"task_gid": task_gid},
        )
        return False

    if cache_provider is None:
        logger.debug(
            "webhook_cache_skip_no_provider",
            extra={"task_gid": task_gid},
        )
        return False

    try:
        # Check if cached entry exists and compare versions
        cached_entry = cache_provider.get_versioned(task_gid, EntryType.TASK)

        if cached_entry is None:
            logger.debug(
                "webhook_cache_skip_no_entry",
                extra={"task_gid": task_gid},
            )
            return False

        # Use CacheEntry.is_stale() which handles ISO parsing and TZ normalization
        if cached_entry.is_stale(inbound_modified_at):
            cache_provider.invalidate(task_gid, _TASK_ENTRY_TYPES)
            logger.info(
                "webhook_cache_invalidated",
                extra={
                    "task_gid": task_gid,
                    "inbound_modified_at": inbound_modified_at,
                },
            )
            return True
        else:
            logger.debug(
                "webhook_cache_skip_not_stale",
                extra={
                    "task_gid": task_gid,
                    "inbound_modified_at": inbound_modified_at,
                },
            )
            return False

    except Exception:
        # Per NFR-03: Cache failures must not affect response or dispatch
        logger.exception(
            "webhook_cache_invalidation_error",
            extra={"task_gid": task_gid},
        )
        return False


# ---------------------------------------------------------------------------
# Background Task
# ---------------------------------------------------------------------------

async def _process_inbound_task(task: Task, cache_provider: Any) -> None:
    """Background processing for accepted inbound webhook.

    Runs after the HTTP response is sent. Performs:
    1. Cache invalidation (conditional on modified_at)
    2. Dispatch to registered handler (no-op in V1)

    Per NFR-03: Exceptions here do not affect the HTTP response.

    Args:
        task: Parsed Task model.
        cache_provider: CacheProvider for cache invalidation.
    """
    # Step 1: Cache invalidation
    invalidate_stale_task_cache(
        task_gid=task.gid,
        inbound_modified_at=task.modified_at,
        cache_provider=cache_provider,
    )

    # Step 2: Dispatch (no-op in V1)
    try:
        await _dispatcher.dispatch(task)
    except Exception:
        # Per NFR-03: Dispatch errors logged but do not propagate
        logger.exception(
            "webhook_dispatch_error",
            extra={"task_gid": task.gid},
        )


# ---------------------------------------------------------------------------
# Route Handler
# ---------------------------------------------------------------------------

@router.post("/inbound")
async def receive_inbound_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    _token: str = Depends(verify_webhook_token),
) -> JSONResponse:
    """Receive Asana Rules action POST with full task JSON.

    Per PRD-GAP-02 / FR-01, FR-04, FR-05:
    1. Verify URL token (via Depends)
    2. Parse request body as Task
    3. Enqueue background processing
    4. Return 200 immediately

    Args:
        request: FastAPI request for raw body access.
        background_tasks: FastAPI BackgroundTasks for async processing.
        _token: Verified token (unused, presence confirms auth).

    Returns:
        200 with {"status": "accepted"} for valid payloads.
        400 for unparseable or invalid payloads.
        401 for auth failures (handled by Depends).
        503 if webhook not configured (handled by Depends).
    """
    # Parse body
    try:
        body = await request.json()
    except Exception:
        logger.warning(
            "webhook_body_parse_error",
            extra={"content_type": request.headers.get("content-type")},
        )
        return JSONResponse(
            status_code=400,
            content={"error": "INVALID_JSON", "message": "Request body must be valid JSON"},
        )

    # Handle empty body (per EC-10)
    if not body:
        logger.warning("webhook_empty_body")
        return JSONResponse(
            status_code=200,
            content={"status": "accepted", "detail": "empty payload ignored"},
        )

    # Validate task GID presence (per EC-12)
    if not isinstance(body, dict) or not body.get("gid"):
        logger.warning(
            "webhook_missing_gid",
            extra={"has_body": bool(body), "body_type": type(body).__name__},
        )
        return JSONResponse(
            status_code=400,
            content={"error": "MISSING_GID", "message": "Task payload must include 'gid' field"},
        )

    # Parse into Task model
    try:
        task = Task.model_validate(body)
    except Exception as exc:
        logger.warning(
            "webhook_task_validation_error",
            extra={"error": str(exc)},
        )
        return JSONResponse(
            status_code=400,
            content={"error": "INVALID_TASK", "message": "Payload does not conform to Task model"},
        )

    # Log accepted request (per FR-08 / SC-006)
    logger.info(
        "webhook_task_received",
        extra={
            "task_gid": task.gid,
            "resource_type": task.resource_type,
            "modified_at": task.modified_at,
        },
    )

    # Get cache provider from app state (may be None)
    mutation_invalidator = getattr(request.app.state, "mutation_invalidator", None)
    cache_provider = getattr(mutation_invalidator, "_cache", None) if mutation_invalidator else None

    # Enqueue background processing (per FR-05 / SC-004)
    background_tasks.add_task(_process_inbound_task, task, cache_provider)

    return JSONResponse(
        status_code=200,
        content={"status": "accepted"},
    )
```

**Note**: The `from fastapi import ... Depends` import and the `Depends(verify_webhook_token)` usage are shown in the route handler. The actual implementation file should import `Depends` from fastapi.

### 4.2 Modified Files

#### 4.2.1 `src/autom8_asana/settings.py`

Add `WebhookSettings` nested model and include it in `Settings`.

```python
class WebhookSettings(Autom8yBaseSettings):
    """Webhook configuration settings.

    Environment Variables:
        WEBHOOK_INBOUND_TOKEN: Shared secret for inbound webhook auth.

    Attributes:
        inbound_token: Shared secret for URL token verification.
    """

    model_config = SettingsConfigDict(
        env_prefix="WEBHOOK_",
        extra="ignore",
        case_sensitive=False,
    )

    inbound_token: str = Field(
        default="",
        description="Shared secret for inbound webhook URL token verification",
    )
```

In `Settings` class, add:

```python
    webhook: WebhookSettings = Field(default_factory=WebhookSettings)
```

#### 4.2.2 `src/autom8_asana/api/routes/__init__.py`

Add webhook router import and export.

```python
from .webhooks import router as webhooks_router

# Add to __all__
__all__ = [
    # ... existing ...
    "webhooks_router",
]
```

#### 4.2.3 `src/autom8_asana/api/main.py`

Add webhook router inclusion.

```python
from .routes import (
    # ... existing imports ...
    webhooks_router,
)

# In create_app(), after existing router inclusions:
    app.include_router(webhooks_router)
```

---

## 5. Sequence Diagrams

### 5.1 Happy Path: Accepted Task Payload

```
Asana Rules                     FastAPI                      BackgroundTask
    |                              |                              |
    |-- POST /inbound?token=X ---->|                              |
    |                              |                              |
    |                     verify_webhook_token()                  |
    |                     (timing-safe compare)                   |
    |                              |                              |
    |                     request.json()                          |
    |                     Task.model_validate(body)               |
    |                              |                              |
    |                     logger.info("webhook_task_received")    |
    |                              |                              |
    |                     background_tasks.add_task(...)          |
    |                              |                              |
    |<-- 200 {"status":"accepted"} |                              |
    |                              |                              |
    |                              |-- _process_inbound_task() -->|
    |                              |                              |
    |                              |   invalidate_stale_task_cache()
    |                              |     cache.get_versioned(gid, TASK)
    |                              |     cached_entry.is_stale(modified_at)?
    |                              |       YES: cache.invalidate(gid, [TASK, SUBTASKS, DETECTION])
    |                              |       NO:  skip
    |                              |                              |
    |                              |   dispatcher.dispatch(task)  |
    |                              |     (V1: NoOpDispatcher -> log and discard)
```

### 5.2 Auth Failure

```
Client                          FastAPI
    |                              |
    |-- POST /inbound (no token) ->|
    |                              |
    |                     verify_webhook_token()
    |                     token is None -> 401
    |                              |
    |<-- 401 {"error":"MISSING_TOKEN"} |
```

### 5.3 Cache Invalidation Decision Tree

```
inbound_modified_at is None?
  YES -> skip (log warning)
  NO  -> cache_provider is None?
           YES -> skip (log debug)
           NO  -> cached_entry = cache.get_versioned(gid, TASK)
                  cached_entry is None?
                    YES -> skip (nothing to invalidate)
                    NO  -> cached_entry.is_stale(inbound_modified_at)?
                           YES -> cache.invalidate(gid, [TASK, SUBTASKS, DETECTION])
                           NO  -> skip (cache is current or newer)
```

---

## 6. Data Flow

### 6.1 Inbound Payload -> Cache Deletion

```
1. Asana Rules fires POST with full task JSON body
2. FastAPI extracts ?token= query param, calls verify_webhook_token()
3. Raw body parsed as JSON dict
4. Dict validated: must be non-empty and contain "gid"
5. Task.model_validate(body) parses into typed Task model
6. HTTP 200 returned to Asana Rules
7. BackgroundTask runs:
   a. Extract task.gid and task.modified_at
   b. Get CacheProvider from app.state.mutation_invalidator._cache
   c. cache_provider.get_versioned(task.gid, EntryType.TASK) -> CacheEntry | None
   d. If CacheEntry exists and CacheEntry.is_stale(task.modified_at):
      cache_provider.invalidate(task.gid, [TASK, SUBTASKS, DETECTION])
   e. dispatcher.dispatch(task) -> NoOpDispatcher logs and returns
```

### 6.2 Cache Provider Access

The cache provider is accessed through the existing `MutationInvalidator` which is already initialized during app startup and stored on `app.state.mutation_invalidator`. The webhook handler accesses it as:

```python
mutation_invalidator = getattr(request.app.state, "mutation_invalidator", None)
cache_provider = getattr(mutation_invalidator, "_cache", None) if mutation_invalidator else None
```

This is a pragmatic approach for V1. If a dedicated cache provider dependency is needed in V2, it can be added as a proper FastAPI `Depends()`.

---

## 7. Error Handling

| Scenario | HTTP Status | Response Body | Side Effects |
|----------|-------------|---------------|--------------|
| Missing `?token=` param | 401 | `{"error": "MISSING_TOKEN", ...}` | Log warning |
| Wrong token value | 401 | `{"error": "INVALID_TOKEN", ...}` | Log warning |
| Token not configured (env var empty) | 503 | `{"error": "WEBHOOK_NOT_CONFIGURED", ...}` | Log error |
| Non-JSON body | 400 | `{"error": "INVALID_JSON", ...}` | Log warning |
| Empty JSON body | 200 | `{"status": "accepted", "detail": "empty payload ignored"}` | Log warning, no dispatch |
| JSON without `gid` | 400 | `{"error": "MISSING_GID", ...}` | Log warning |
| Valid JSON, Task validation fails | 400 | `{"error": "INVALID_TASK", ...}` | Log warning |
| Valid task, cache invalidation fails | 200 | `{"status": "accepted"}` | Log exception, dispatch continues |
| Valid task, dispatch fails | 200 | `{"status": "accepted"}` | Log exception |
| Valid task, happy path | 200 | `{"status": "accepted"}` | Log info, bg invalidation + dispatch |

---

## 8. Security Considerations

### 8.1 Token Handling

- Token is read from `WEBHOOK_INBOUND_TOKEN` env var via `WebhookSettings`
- Comparison uses `hmac.compare_digest()` (constant-time) to prevent timing attacks
- Token value is never logged -- `SENSITIVE_FIELDS` in `middleware.py` already includes `"token"` and `"secret"`
- The `verify_webhook_token` dependency extracts from `Query()`, not from request body -- this prevents the token from being parsed/logged as payload data

### 8.2 No Secrets in Logs (NFR-04)

- `RequestLoggingMiddleware` logs `request.url.path` (not query string) -- token not exposed
- All structured log events use field names like `task_gid`, `modified_at`, `resource_type` -- no raw request bodies
- The `_filter_sensitive_data` structlog processor redacts any log field whose key contains "token"

### 8.3 Attack Surface

- This is the first public POST endpoint (all others require JWT/PAT Bearer auth)
- Global SlowAPI rate limiting applies (100 RPM default via `ASANA_API_RATE_LIMIT_RPM`)
- The handler performs no business logic -- it parses, validates, enqueues, and returns
- `Task.model_validate()` with `extra="ignore"` safely discards unexpected fields
- No database writes, no outbound API calls in the request path

### 8.4 Body Size

- FastAPI/Starlette default body size limit applies (no custom override needed)
- Large payloads (hundreds of custom fields) are handled by Pydantic parsing
- Per EC-04: Could add a configurable size threshold for warning logs in V2

---

## 9. Non-Functional Requirements

| NFR | Target | Approach |
|-----|--------|----------|
| Response latency (NFR-01) | < 1 second | All processing in BackgroundTasks; only JSON parse + validate in request path |
| Failure isolation (NFR-03) | Background failures never affect response | try/except in `_process_inbound_task` + `invalidate_stale_task_cache` |
| No secrets in logs (NFR-04) | Token never in logs | Structlog `SENSITIVE_FIELDS` filter + path-only request logging |
| Test coverage | ~80% | Unit tests for each function; integration test for full flow |

---

## 10. Test Strategy

### 10.1 Test File

`tests/unit/api/routes/test_webhooks.py`

### 10.2 Test Categories

#### Token Verification Tests

```python
class TestVerifyWebhookToken:
    def test_valid_token_returns_token(self)
    def test_missing_token_raises_401(self)
    def test_empty_token_raises_401(self)
    def test_wrong_token_raises_401(self)
    def test_unconfigured_token_raises_503(self)
    def test_timing_safe_comparison_used(self)  # verify hmac.compare_digest call
```

#### Cache Invalidation Tests

```python
class TestInvalidateStaleCacheTask:
    def test_invalidates_when_inbound_newer(self)
    def test_skips_when_inbound_older(self)
    def test_skips_when_inbound_equal(self)
    def test_skips_when_no_cached_entry(self)
    def test_skips_when_modified_at_none(self)
    def test_skips_when_cache_provider_none(self)
    def test_invalidates_correct_entry_types(self)  # TASK, SUBTASKS, DETECTION
    def test_cache_error_does_not_propagate(self)
```

#### Endpoint Integration Tests

```python
class TestReceiveInboundWebhook:
    def test_happy_path_returns_200(self)
    def test_missing_token_returns_401(self)
    def test_wrong_token_returns_401(self)
    def test_non_json_body_returns_400(self)
    def test_empty_body_returns_200_with_warning(self)
    def test_missing_gid_returns_400(self)
    def test_task_validation_error_returns_400(self)
    def test_background_task_enqueued(self)
    def test_structured_log_emitted_on_accept(self)
    def test_cache_invalidation_called_in_background(self)
    def test_dispatcher_called_in_background(self)
    def test_unknown_fields_ignored(self)  # extra="ignore"
```

#### Dispatch Protocol Tests

```python
class TestNoOpDispatcher:
    async def test_dispatch_logs_task_gid(self)
    async def test_dispatch_does_not_raise(self)

class TestSetDispatcher:
    def test_replaces_global_dispatcher(self)
    def test_get_dispatcher_returns_current(self)
```

### 10.3 Test Fixtures

```python
@pytest.fixture
def webhook_token():
    """Set WEBHOOK_INBOUND_TOKEN env var for testing."""
    with patch.dict(os.environ, {"WEBHOOK_INBOUND_TOKEN": "test-secret-token"}):
        reset_settings()
        yield "test-secret-token"
        reset_settings()

@pytest.fixture
def sample_task_payload():
    """Full Asana task JSON equivalent to GET /tasks/{gid}."""
    return {
        "gid": "1234567890",
        "resource_type": "task",
        "name": "Test Task",
        "modified_at": "2026-02-07T15:30:00.000Z",
        "assignee": {"gid": "111", "name": "User"},
        "projects": [{"gid": "222", "name": "Project"}],
        "custom_fields": [],
    }

@pytest.fixture
def mock_cache_provider():
    """Mock CacheProvider for cache invalidation tests."""
    provider = MagicMock()
    provider.get_versioned.return_value = None
    return provider
```

### 10.4 Coverage Targets

| Component | Target | Method |
|-----------|--------|--------|
| `verify_webhook_token()` | 100% | Unit tests with parametrized token scenarios |
| `invalidate_stale_task_cache()` | 100% | Unit tests with mock CacheProvider |
| `receive_inbound_webhook()` | ~80% | FastAPI TestClient integration tests |
| `NoOpDispatcher.dispatch()` | 100% | Simple async test |
| `_process_inbound_task()` | ~80% | Test via endpoint integration + mock verification |

---

## 11. V2 Extension Points

The V1 design explicitly accommodates V2 (Asana Webhooks API) without requiring V1 refactoring:

| V2 Feature | Extension Point | V1 Preparation |
|------------|-----------------|----------------|
| Handshake protocol | New route (`POST /inbound` checks `X-Hook-Secret` header before processing) | Route handler can add header check at top of function |
| HMAC verification | Replace `verify_webhook_token` with `verify_webhook_signature` dependency | `Depends()` pattern makes swapping trivial |
| Event envelope | Parse `events[]` array before dispatching individual tasks | Dispatch protocol accepts `Task`; V2 can parse envelope and call `dispatch()` per event |
| Secret storage | Replace `WebhookSettings.inbound_token` with pluggable secret backend | Settings model can be extended without route changes |
| Multiple webhooks | Route parameter for webhook ID (`/inbound/{webhook_id}`) | Current path is a prefix; adding sub-paths is additive |

---

## 12. File Attestation

| File | Path | Status |
|------|------|--------|
| PRD-GAP-02 | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-GAP-02-webhook-inbound.md` | Read, verified |
| Task model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` | Read, verified |
| AsanaResource base | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/base.py` | Read, verified |
| Webhook model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/webhook.py` | Read, verified |
| CacheInvalidator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/cache_invalidator.py` | Read, verified |
| MutationInvalidator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/mutation_invalidator.py` | Read, verified |
| CacheProvider protocol | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py` | Read, verified |
| CacheEntry model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/entry.py` | Read, verified |
| UnifiedTaskStore | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/providers/unified.py` | Read, verified |
| API dependencies | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/dependencies.py` | Read, verified |
| API middleware | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/middleware.py` | Read, verified |
| API main | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Read, verified |
| API config | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/config.py` | Read, verified |
| Routes init | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/__init__.py` | Read, verified |
| Health routes | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/health.py` | Read, verified |
| Tasks routes | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/tasks.py` | Read, verified |
| Settings | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py` | Read, verified |
| API lifespan | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/lifespan.py` | Read, verified |
| API startup | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/startup.py` | Read, verified |

---

## 13. Handoff Checklist

- [x] TDD covers all PRD requirements (FR-01 through FR-10, NFR-01 through NFR-04)
- [x] Component boundaries and responsibilities are clear
- [x] Data model reuses existing Task model
- [x] API contract specified (endpoint, auth, request/response shapes)
- [x] Key flows have sequence diagrams
- [x] NFRs have concrete approaches (not just targets)
- [x] ADRs document all significant decisions (3 ADRs)
- [x] Risks identified with mitigations (from PRD, carried forward)
- [x] Principal Engineer can implement without architectural questions
- [x] All source files verified via Read tool
- [x] Attestation table included with absolute paths
