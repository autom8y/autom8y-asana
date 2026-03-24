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
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from autom8_asana.api.dependencies import get_request_id
from autom8_asana.api.errors import raise_api_error
from autom8_asana.cache.models.entry import EntryType
from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS
from autom8_asana.models.task import Task
from autom8_asana.settings import get_settings

logger = get_logger(__name__)

# Combined error tuple for except clauses (star-unpacking not supported by mypy)
_WEBHOOK_CACHE_ERRORS: tuple[type[Exception], ...] = (
    *CACHE_TRANSIENT_ERRORS,
    ValueError,
    RuntimeError,
)

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
    request_id: str = Depends(get_request_id),
    token: str | None = Query(default=None),
) -> str:
    """Verify the inbound webhook URL token.

    Per FR-03: Timing-safe comparison of URL token against
    configured environment variable.

    Args:
        request_id: Request ID for error correlation (via get_request_id dependency).
        token: Token from ?token= query parameter.

    Returns:
        The verified token (unused by caller, but confirms auth).

    Raises:
        HTTPException: 401 with request_id if token is missing, empty, or incorrect.
        HTTPException: 503 with request_id if webhook token is not configured.
    """
    settings = get_settings()

    expected_token = settings.webhook.inbound_token
    if not expected_token:
        logger.error("webhook_token_not_configured")
        raise_api_error(
            request_id,
            503,
            "WEBHOOK_NOT_CONFIGURED",
            "Webhook endpoint is not configured",
        )

    if not token:
        logger.warning(
            "webhook_token_missing",
            extra={"reason": "no token query parameter"},
        )
        raise_api_error(
            request_id,
            401,
            "MISSING_TOKEN",
            "Authentication required",
        )

    if not hmac.compare_digest(token, expected_token):
        logger.warning(
            "webhook_token_invalid",
            extra={"reason": "token mismatch"},
        )
        raise_api_error(
            request_id,
            401,
            "INVALID_TOKEN",
            "Authentication failed",
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

    except _WEBHOOK_CACHE_ERRORS:
        # Per NFR-03: Cache failures must not affect response or dispatch
        # ValueError can come from timestamp parsing in is_stale()
        # RuntimeError can come from cache.invalidate() operations
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
    except (ConnectionError, TimeoutError, OSError, RuntimeError):
        # Per NFR-03: Dispatch errors logged but do not propagate
        logger.exception(
            "webhook_dispatch_error",
            extra={"task_gid": task.gid},
        )


# ---------------------------------------------------------------------------
# Route Handler
# ---------------------------------------------------------------------------


@router.post(
    "/inbound",
    summary="Receive an inbound webhook event from Asana",
    response_description="Accepted status for valid payloads",
)
async def receive_inbound_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    _token: str = Depends(verify_webhook_token),
) -> JSONResponse:
    """Receive an Asana Rules action POST containing a full task JSON payload.

    This endpoint is designed to be registered as an Asana Rules action
    target. Asana POSTs the full task JSON when a rule fires. The endpoint
    accepts the payload, enqueues background processing, and returns 200
    immediately so Asana does not retry.

    **Authentication**: URL token via ``?token=<secret>`` query parameter.
    The token is verified with a timing-safe comparison against
    ``ASANA_WEBHOOK_INBOUND_TOKEN``. Requests without a valid token receive
    401.

    **Background processing** (after response is sent):
    1. Cache invalidation — evicts stale TASK/SUBTASKS/DETECTION entries
       if the inbound ``modified_at`` is newer than the cached version.
    2. Dispatch — routes the parsed task to the registered handler
       (no-op in V1; GAP-03 provides a real implementation).

    Per PRD-GAP-02:
    - Empty bodies are accepted (200) and silently ignored.
    - Payloads without a ``gid`` field return 400.
    - Dispatch errors do not affect the HTTP response.

    Args:
        request: FastAPI request for raw body access.
        background_tasks: FastAPI BackgroundTasks for async processing.
        _token: Verified URL token (presence confirms authentication).

    Returns:
        - 200: ``{"status": "accepted"}`` — payload received and enqueued.
        - 400: Malformed JSON or missing ``gid`` field.
        - 401: Missing or invalid URL token.
        - 503: Webhook endpoint not configured (token env var absent).
    """
    # Parse body
    try:
        body = await request.json()
    except (ValueError, UnicodeDecodeError):
        logger.warning(
            "webhook_body_parse_error",
            extra={"content_type": request.headers.get("content-type")},
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "INVALID_JSON",
                "message": "Request body must be valid JSON",
            },
        )

    # Handle empty body (per EC-10)
    if not body:
        logger.warning("webhook_empty_body")
        return JSONResponse(
            status_code=200,
            content={"status": "accepted", "detail": "empty payload ignored"},
        )

    # Validate task GID presence (per EC-12)
    # Note: str.strip() guards against whitespace-only GIDs that would pass
    # the truthiness check but get stripped to "" by Pydantic's str_strip_whitespace.
    raw_gid = body.get("gid") if isinstance(body, dict) else None
    if (
        not isinstance(body, dict)
        or not raw_gid
        or (isinstance(raw_gid, str) and not raw_gid.strip())
    ):
        logger.warning(
            "webhook_missing_gid",
            extra={"has_body": bool(body), "body_type": type(body).__name__},
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "MISSING_GID",
                "message": "Task payload must include 'gid' field",
            },
        )

    # Parse into Task model
    try:
        task = Task.model_validate(body)
    except (
        ValidationError,
        ValueError,
    ) as exc:  # NARROW: Pydantic model_validate raises ValidationError; ValueError for malformed data
        logger.warning(
            "webhook_task_validation_error",
            extra={"error": str(exc)},
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "INVALID_TASK",
                "message": "Payload does not conform to Task model",
            },
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
    cache_provider = (
        getattr(mutation_invalidator, "_cache", None) if mutation_invalidator else None
    )

    # Enqueue background processing (per FR-05 / SC-004)
    background_tasks.add_task(_process_inbound_task, task, cache_provider)

    return JSONResponse(
        status_code=200,
        content={"status": "accepted"},
    )
