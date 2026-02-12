"""Entity write route -- PATCH /api/v1/entity/{entity_type}/{gid}.

Per TDD-ENTITY-WRITE-API Section 3.4:
    Thin route handler that validates input, constructs the write service,
    delegates to FieldWriteService.write_async(), and maps results to
    the HTTP response.

Authentication:
    S2S JWT only (require_service_claims dependency).
    PAT tokens are rejected with 401 SERVICE_TOKEN_REQUIRED.
"""

from __future__ import annotations

import time
from typing import Annotated, Any, Literal

from autom8y_log import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, model_validator

from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.exceptions import (
    RateLimitError,
    ServerError,
)
from autom8_asana.exceptions import (
    TimeoutError as AsanaTimeoutError,
)
from autom8_asana.services.errors import (
    EntityTypeMismatchError,
    NoValidFieldsError,
    TaskNotFoundError,
)
from autom8_asana.services.field_write_service import (
    FieldWriteService,
    WriteFieldsResult,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/entity", tags=["entity-write"], include_in_schema=False
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class EntityWriteRequest(BaseModel):
    """Request body for PATCH /api/v1/entity/{entity_type}/{gid}.

    Attributes:
        fields: Dict mapping field names to values. Accepts both
            Python descriptor names (weekly_ad_spend) and Asana
            display names ("Weekly Ad Spend"). Core fields (name,
            assignee, due_on, completed, notes) are also accepted.
        list_mode: How to handle list-type fields.
            "replace" (default): Replace entire field value.
            "append": Append to existing values (multi_enum, text lists).
    """

    fields: dict[str, Any]
    list_mode: Literal["replace", "append"] = "replace"

    @model_validator(mode="after")
    def validate_non_empty(self) -> EntityWriteRequest:
        if not self.fields:
            raise ValueError("fields must be non-empty")
        return self


class FieldWriteResult(BaseModel):
    """Per-field write result."""

    name: str
    status: Literal["written", "skipped", "error"]
    error: str | None = None
    suggestions: list[str] | None = None


class EntityWriteResponse(BaseModel):
    """Response for entity write endpoint."""

    gid: str
    entity_type: str
    fields_written: int
    fields_skipped: int
    field_results: list[FieldWriteResult]
    updated_fields: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.patch("/{entity_type}/{gid}")
async def write_entity_fields(
    entity_type: str,
    gid: str,
    body: EntityWriteRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    include_updated: bool = False,
) -> EntityWriteResponse:
    """Write fields to an Asana entity.

    Authentication: S2S JWT only (require_service_claims dependency).

    Path Parameters:
        entity_type: Entity type (offer, unit, business, etc.)
        gid: Asana task GID

    Query Parameters:
        include_updated: If true, re-fetch and return current field values.

    Request Body:
        EntityWriteRequest with fields dict and optional list_mode.

    Returns:
        EntityWriteResponse with per-field results.
    """
    start_time = time.monotonic()
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        "entity_write_request",
        extra={
            "request_id": request_id,
            "entity_type": entity_type,
            "gid": gid,
            "caller_service": claims.service_name,
            "field_count": len(body.fields),
            "list_mode": body.list_mode,
        },
    )

    # Get EntityWriteRegistry from app.state
    write_registry = getattr(request.app.state, "entity_write_registry", None)
    if write_registry is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "DISCOVERY_INCOMPLETE",
                "message": "Entity write registry not initialized. "
                "Please retry after service is fully initialized.",
            },
        )

    # Validate entity type is writable
    if not write_registry.is_writable(entity_type):
        available = write_registry.writable_types()
        logger.warning(
            "unknown_entity_type",
            extra={
                "request_id": request_id,
                "entity_type": entity_type,
                "available_types": available,
            },
        )
        raise HTTPException(
            status_code=404,
            detail={
                "error": "UNKNOWN_ENTITY_TYPE",
                "message": f"Unknown or non-writable entity type: {entity_type}. "
                f"Available types: {', '.join(available)}",
                "available_types": available,
            },
        )

    # Acquire bot PAT and create AsanaClient
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat

    try:
        bot_pat = get_bot_pat()
    except BotPATError as exc:
        logger.error(
            "bot_pat_unavailable",
            extra={
                "request_id": request_id,
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": "BOT_PAT_UNAVAILABLE",
                "message": "Bot PAT not configured for S2S Asana access.",
            },
        )

    # Get optional MutationInvalidator from app.state
    mutation_invalidator = getattr(request.app.state, "mutation_invalidator", None)

    try:
        async with AsanaClient(token=bot_pat) as client:
            service = FieldWriteService(client, write_registry)
            result: WriteFieldsResult = await service.write_async(
                entity_type=entity_type,
                gid=gid,
                fields=body.fields,
                list_mode=body.list_mode,
                include_updated=include_updated,
                mutation_invalidator=mutation_invalidator,
            )
    except TaskNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "TASK_NOT_FOUND",
                "message": f"Task not found: {gid}",
            },
        )
    except EntityTypeMismatchError as exc:
        raise HTTPException(
            status_code=404,
            detail=exc.to_dict(),
        )
    except NoValidFieldsError:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "NO_VALID_FIELDS",
                "message": "All fields failed resolution -- nothing to write.",
            },
        )
    except RateLimitError as exc:
        headers = {}
        if exc.retry_after is not None:
            headers["Retry-After"] = str(exc.retry_after)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "RATE_LIMITED",
                "message": "Rate limit exceeded. Please retry after backoff.",
            },
            headers=headers if headers else None,
        )
    except AsanaTimeoutError as exc:
        logger.warning(
            "entity_write_timeout",
            extra={
                "request_id": request_id,
                "gid": gid,
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=504,
            detail={
                "error": "ASANA_TIMEOUT",
                "message": "Asana API call timed out.",
            },
        )
    except ServerError as exc:
        logger.error(
            "entity_write_upstream_error",
            extra={
                "request_id": request_id,
                "gid": gid,
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=502,
            detail={
                "error": "ASANA_UPSTREAM_ERROR",
                "message": "Asana server error.",
            },
        )
    except HTTPException:
        raise
    except Exception as exc:  # BROAD-CATCH: boundary
        logger.exception(
            "entity_write_error",
            extra={
                "request_id": request_id,
                "entity_type": entity_type,
                "gid": gid,
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=502,
            detail={
                "error": "ASANA_UPSTREAM_ERROR",
                "message": "An unexpected error occurred during entity write.",
            },
        )

    # Build response
    field_results = [
        FieldWriteResult(
            name=rf.input_name,
            status="written" if rf.status == "resolved" else rf.status,
            error=rf.error,
            suggestions=rf.suggestions,
        )
        for rf in result.field_results
    ]

    response = EntityWriteResponse(
        gid=result.gid,
        entity_type=result.entity_type,
        fields_written=result.fields_written,
        fields_skipped=result.fields_skipped,
        field_results=field_results,
        updated_fields=result.updated_fields,
    )

    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "entity_write_complete",
        extra={
            "request_id": request_id,
            "entity_type": entity_type,
            "gid": gid,
            "fields_written": result.fields_written,
            "fields_skipped": result.fields_skipped,
            "duration_ms": round(elapsed_ms, 2),
            "caller_service": claims.service_name,
        },
    )

    return response
