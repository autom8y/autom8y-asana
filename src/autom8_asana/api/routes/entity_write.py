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
from typing import Annotated, Any, Literal, Never, cast

from autom8y_log import get_logger
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from autom8_asana.api.dependencies import (  # noqa: TC001 — FastAPI resolves these at runtime
    AuthContextDep,
    EntityWriteRegistryDep,
    MutationInvalidatorDep,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error
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

    model_config = ConfigDict(extra="forbid")

    fields: dict[str, Any] = Field(
        description="Mapping of field names to values. Accepts Python descriptor names and Asana display names.",
    )
    list_mode: Literal["replace", "append"] = Field(
        default="replace",
        description="How to handle list-type fields: 'replace' replaces entire value, 'append' adds to existing.",
    )

    @model_validator(mode="after")
    def validate_non_empty(self) -> EntityWriteRequest:
        if not self.fields:
            raise ValueError("fields must be non-empty")
        return self


class FieldWriteResult(BaseModel):
    """Per-field write result."""

    name: str = Field(description="Input field name as provided in the request.")
    status: Literal["written", "skipped", "error"] = Field(
        description="Outcome of the write: 'written' if successful, 'skipped' if filtered, 'error' if failed.",
    )
    error: str | None = Field(
        default=None,
        description="Error message if the field write failed.",
    )
    suggestions: list[str] | None = Field(
        default=None,
        description="Suggested valid field names when the input name was not recognized.",
    )


class EntityWriteResponse(BaseModel):
    """Response for entity write endpoint."""

    gid: str = Field(description="Asana task GID that was written to.")
    entity_type: str = Field(description="Entity type of the written task.")
    fields_written: int = Field(description="Number of fields successfully written.")
    fields_skipped: int = Field(
        description="Number of fields skipped due to errors or filtering."
    )
    field_results: list[FieldWriteResult] = Field(
        description="Per-field write outcomes."
    )
    updated_fields: dict[str, Any] | None = Field(
        default=None,
        description="Current field values after write (only when include_updated=true).",
    )


# ---------------------------------------------------------------------------
# Error-to-status mapping (canonical pattern per D-004)
# ---------------------------------------------------------------------------

_WRITE_ERROR_STATUS: dict[type[Exception], tuple[int, str, str]] = {
    TaskNotFoundError: (404, "TASK_NOT_FOUND", "Task not found."),
    NoValidFieldsError: (
        422,
        "NO_VALID_FIELDS",
        "All fields failed resolution -- nothing to write.",
    ),
}


def _raise_write_error(
    request_id: str,
    gid: str,
    exc: Exception,
) -> Never:
    """Map a write-service exception to an HTTPException with request_id.

    Per ADR-I6-001 / D-004: Consolidates common per-type status mapping.
    RateLimitError and EntityTypeMismatchError are handled at the call site
    due to extra headers / structured details.
    """
    if isinstance(exc, AsanaTimeoutError):
        logger.warning(
            "entity_write_timeout",
            extra={
                "request_id": request_id,
                "gid": gid,
                "error": str(exc),
            },
        )
        raise_api_error(request_id, 504, "ASANA_TIMEOUT", "Asana API call timed out.")

    if isinstance(exc, ServerError):
        logger.error(
            "entity_write_upstream_error",
            extra={
                "request_id": request_id,
                "gid": gid,
                "error": str(exc),
            },
        )
        raise_api_error(request_id, 502, "ASANA_UPSTREAM_ERROR", "Asana server error.")

    mapping = _WRITE_ERROR_STATUS.get(type(exc))
    if mapping is not None:
        status, code, message = mapping
        raise_api_error(request_id, status, code, message)

    # Unreachable in normal flow; callers must handle remaining exception types.
    raise exc  # pragma: no cover


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.patch("/{entity_type}/{gid}")
async def write_entity_fields(
    entity_type: str,
    gid: str,
    body: EntityWriteRequest,
    request_id: RequestId,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    auth_context: AuthContextDep,
    mutation_invalidator: MutationInvalidatorDep,
    write_registry: EntityWriteRegistryDep,
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

    # Get EntityWriteRegistry from app.state (via DI)
    if write_registry is None:
        raise_api_error(
            request_id,
            503,
            "DISCOVERY_INCOMPLETE",
            "Entity write registry not initialized. "
            "Please retry after service is fully initialized.",
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
        raise_api_error(
            request_id,
            404,
            "UNKNOWN_ENTITY_TYPE",
            f"Unknown or non-writable entity type: {entity_type}. "
            f"Available types: {', '.join(available)}",
            details={"available_types": available},
        )

    # Use bot PAT from auth context and create AsanaClient
    from autom8_asana import AsanaClient

    try:
        async with AsanaClient(token=auth_context.asana_pat) as client:
            service = FieldWriteService(client, write_registry)
            result: WriteFieldsResult = await service.write_async(
                entity_type=entity_type,
                gid=gid,
                fields=body.fields,
                list_mode=body.list_mode,
                include_updated=include_updated,
                mutation_invalidator=mutation_invalidator,
            )
    except EntityTypeMismatchError as exc:
        raise_api_error(
            request_id,
            404,
            exc.error_code,
            exc.message,
            details={
                "expected_project": exc.expected_project,
                "actual_projects": exc.actual_projects,
            },
        )
    except RateLimitError as exc:
        headers: dict[str, str] | None = None
        if exc.retry_after is not None:
            headers = {"Retry-After": str(exc.retry_after)}
        raise_api_error(
            request_id,
            429,
            "RATE_LIMITED",
            "Rate limit exceeded. Please retry after backoff.",
            headers=headers,
        )
    except HTTPException:
        raise
    except (
        TaskNotFoundError,
        NoValidFieldsError,
        AsanaTimeoutError,
        ServerError,
    ) as exc:
        _raise_write_error(request_id, gid, exc)
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
        raise_api_error(
            request_id,
            502,
            "ASANA_UPSTREAM_ERROR",
            "An unexpected error occurred during entity write.",
        )

    # Build response
    field_results = [
        FieldWriteResult(
            name=rf.input_name,
            status=cast(
                "Literal['written', 'skipped', 'error']",
                "written" if rf.status == "resolved" else rf.status,
            ),
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
