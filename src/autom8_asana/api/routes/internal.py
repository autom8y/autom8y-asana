"""Internal routes for S2S communication.

Per TDD-DATA-SERVICE-CLIENT-001 WS2:
This module provides internal endpoints used by other autom8 services
to resolve phone/vertical pairs to Asana task GIDs.

Routes:
- POST /api/v1/internal/gid-lookup - Resolve phone/vertical pairs to task GIDs

Authentication:
- All routes require service token (S2S JWT) authentication
- PAT pass-through is NOT supported for internal routes

Implementation:
- Uses SearchService to query cached project DataFrames for GID lookup
- Queries Asana Unit tasks by Office Phone + Vertical custom fields
- Returns task GID from matching Unit tasks
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, field_validator

from autom8_asana.auth.dual_mode import AuthMode, detect_token_type
from autom8_asana.auth.jwt_validator import validate_service_token
from autom8_asana.models.contracts.phone_vertical import PhoneVerticalPair
from autom8_asana.services.gid_lookup import GidLookupIndex

logger = logging.getLogger("autom8_asana.api.internal")

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])

# --- Module-Level GidLookupIndex Cache ---
# Per task-003: TTL-based cache for O(1) lookups
# Key: unit_project_gid, Value: GidLookupIndex instance
_gid_index_cache: dict[str, GidLookupIndex] = {}

# Default TTL for index staleness check (1 hour)
_INDEX_TTL_SECONDS = 3600


# --- Request/Response Models ---


class PhoneVerticalInput(BaseModel):
    """Input model for phone/vertical pair.

    Attributes:
        phone: E.164 formatted phone number (e.g., +15551234567)
        vertical: Business vertical (e.g., dental, chiropractic)
    """

    model_config = ConfigDict(extra="forbid")

    phone: str
    vertical: str

    @field_validator("phone")
    @classmethod
    def validate_e164(cls, v: str) -> str:
        """Validate E.164 format.

        E.164 format: + followed by 1-15 digits, first digit non-zero.
        Example: +15551234567

        Raises:
            ValueError: If phone does not match E.164 format.
        """
        if not re.match(r"^\+[1-9]\d{1,14}$", v):
            raise ValueError(f"Invalid E.164 format: {v}")
        return v


class GidLookupRequest(BaseModel):
    """Request body for GID lookup.

    Attributes:
        phone_vertical_pairs: List of phone/vertical pairs to resolve.
            Maximum 1000 pairs per request (ADR-DATA-CLIENT-003).
    """

    model_config = ConfigDict(extra="forbid")

    phone_vertical_pairs: list[PhoneVerticalInput]

    @field_validator("phone_vertical_pairs")
    @classmethod
    def validate_batch_size(
        cls, v: list[PhoneVerticalInput]
    ) -> list[PhoneVerticalInput]:
        """Enforce batch size limit (ADR-DATA-CLIENT-003).

        Maximum 1000 pairs per request to prevent timeout and
        ensure efficient query execution.

        Raises:
            ValueError: If batch size exceeds 1000.
        """
        MAX_BATCH_SIZE = 1000
        if len(v) > MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size {len(v)} exceeds maximum {MAX_BATCH_SIZE}. "
                f"Please chunk requests."
            )
        return v


class GidMappingOutput(BaseModel):
    """Output model for single GID mapping.

    Attributes:
        phone: E.164 phone number from request
        vertical: Business vertical from request
        task_gid: Asana task GID or None if not found
    """

    model_config = ConfigDict(extra="forbid")

    phone: str
    vertical: str
    task_gid: str | None


class GidLookupResponse(BaseModel):
    """Response body for GID lookup.

    Attributes:
        mappings: List of GidMappingOutput in same order as input.
    """

    model_config = ConfigDict(extra="forbid")

    mappings: list[GidMappingOutput]


# --- Service Claims Model ---


class ServiceClaims(BaseModel):
    """Claims extracted from a validated service token.

    Attributes:
        sub: Subject (service identifier)
        service_name: Name of the calling service
        scope: Permission scope (e.g., multi-tenant)
    """

    sub: str
    service_name: str
    scope: str | None = None


# --- Authentication Dependencies ---


async def _extract_bearer_token(request: Request) -> str:
    """Extract Bearer token from Authorization header.

    Args:
        request: FastAPI request object.

    Returns:
        Token string (without Bearer prefix).

    Raises:
        HTTPException: 401 if header missing or invalid.
    """
    auth_header = request.headers.get("Authorization")

    if auth_header is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "MISSING_AUTH", "message": "Authorization header required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "INVALID_SCHEME", "message": "Bearer scheme required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]  # Remove "Bearer " prefix

    if not token:
        raise HTTPException(
            status_code=401,
            detail={"error": "MISSING_TOKEN", "message": "Token is required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


async def require_service_claims(request: Request) -> ServiceClaims:
    """Require valid service token (S2S) and return claims.

    This dependency is for internal routes that should ONLY be called
    by other autom8 services, not by end users with PAT tokens.

    Args:
        request: FastAPI request object.

    Returns:
        ServiceClaims with validated service information.

    Raises:
        HTTPException: 401 if token is missing, invalid, or not a JWT.
    """
    token = await _extract_bearer_token(request)
    request_id = getattr(request.state, "request_id", "unknown")

    # Check if this is a JWT (S2S) or PAT (user)
    auth_mode = detect_token_type(token)

    if auth_mode == AuthMode.PAT:
        # PAT tokens are not allowed for internal routes
        logger.warning(
            "internal_route_pat_rejected",
            extra={
                "request_id": request_id,
                "reason": "PAT tokens not allowed for internal routes",
            },
        )
        raise HTTPException(
            status_code=401,
            detail={
                "error": "SERVICE_TOKEN_REQUIRED",
                "message": "This endpoint requires service-to-service authentication. "
                "PAT tokens are not supported.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate JWT and extract claims
    try:
        claims = await validate_service_token(token)
    except ImportError as e:
        logger.error(
            "autom8y_auth_not_installed",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": "S2S_NOT_CONFIGURED",
                "message": "Service-to-service authentication is not available",
            },
        )
    except Exception as e:
        # Try to get error code from autom8y_auth exceptions
        error_code = getattr(e, "code", "UNKNOWN_ERROR")
        logger.warning(
            "s2s_jwt_validation_failed",
            extra={
                "request_id": request_id,
                "error_code": error_code,
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=401,
            detail={
                "error": error_code,
                "message": "JWT validation failed",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(
        "internal_route_authenticated",
        extra={
            "request_id": request_id,
            "caller_service": claims.service_name,
            "scope": claims.scope,
        },
    )

    return ServiceClaims(
        sub=claims.sub,
        service_name=claims.service_name,
        scope=claims.scope,
    )


# --- GID Resolution Logic ---


def _get_unit_project_gid() -> str | None:
    """Get Unit project GID from environment.

    Returns:
        Unit project GID if configured, None otherwise.
    """
    return os.environ.get("UNIT_PROJECT_GID")


async def resolve_gids(
    pairs: list[PhoneVerticalInput],
) -> list[GidMappingOutput]:
    """Resolve phone/vertical pairs to task GIDs.

    Query Strategy (per TDD-GID-DATAFLOW-FIX):
    - Uses SearchService to query cached project DataFrames
    - Looks up Unit tasks by Office Phone and Vertical custom fields
    - Returns task GID from matching Unit tasks
    - Preserves input order in response

    Implementation:
    - Gets AsanaClient with bot PAT for Asana API access
    - Uses SearchService.find_one_async for efficient lookups
    - Batch optimized: builds lookup dict from single DataFrame query

    Args:
        pairs: List of phone/vertical pairs to resolve.

    Returns:
        List of GidMappingOutput in same order as input.
    """
    if not pairs:
        return []

    unit_project_gid = _get_unit_project_gid()

    if unit_project_gid is None:
        logger.error(
            "unit_project_gid_not_configured",
            extra={
                "detail": "UNIT_PROJECT_GID environment variable not set",
                "pair_count": len(pairs),
            },
        )
        # Return None for all pairs when not configured
        return [
            GidMappingOutput(
                phone=pair.phone,
                vertical=pair.vertical,
                task_gid=None,
            )
            for pair in pairs
        ]

    try:
        # Import here to avoid circular imports and allow SDK optional
        from autom8_asana import AsanaClient
        from autom8_asana.auth.bot_pat import get_bot_pat, BotPATError

        # Get bot PAT for S2S Asana access
        try:
            bot_pat = get_bot_pat()
        except BotPATError as e:
            logger.error(
                "bot_pat_unavailable",
                extra={
                    "error": str(e),
                    "pair_count": len(pairs),
                },
            )
            return [
                GidMappingOutput(
                    phone=pair.phone,
                    vertical=pair.vertical,
                    task_gid=None,
                )
                for pair in pairs
            ]

        # Create client with bot PAT for Asana access
        async with AsanaClient(token=bot_pat) as client:
            return await _resolve_gids_with_client(client, pairs, unit_project_gid)

    except Exception as e:
        logger.exception(
            "resolve_gids_error",
            extra={
                "error": str(e),
                "pair_count": len(pairs),
            },
        )
        # Graceful degradation: return None for all pairs on error
        return [
            GidMappingOutput(
                phone=pair.phone,
                vertical=pair.vertical,
                task_gid=None,
            )
            for pair in pairs
        ]


async def _build_unit_dataframe(
    client: Any,
    unit_project_gid: str,
) -> Any:
    """Build Unit project DataFrame for GID lookups.

    Per task-003: Returns DataFrame for GidLookupIndex construction.
    Previously populated SearchService cache; now returns DataFrame directly.

    This function:
    1. Creates a minimal ProjectProxy with the Unit project GID
    2. Uses ProjectDataFrameBuilder to fetch and build the DataFrame
    3. Returns the DataFrame for index construction

    Args:
        client: AsanaClient with valid authentication.
        unit_project_gid: Asana project GID containing Unit tasks.

    Returns:
        Polars DataFrame with unit data, or None on failure.

    Note:
        Returns None on failure for graceful degradation.
    """
    # Import here to avoid circular imports
    from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
    from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA

    # Minimal project proxy - only needs gid attribute for builder
    class ProjectProxy:
        """Minimal project object for DataFrame builder."""

        def __init__(self, gid: str) -> None:
            self.gid = gid
            self.tasks: list[Any] = []  # Tasks fetched via parallel fetch

    try:
        project_proxy = ProjectProxy(unit_project_gid)

        builder = ProjectDataFrameBuilder(
            project=project_proxy,
            task_type="Unit",
            schema=UNIT_SCHEMA,
        )

        # Use parallel fetch for efficient DataFrame construction
        # This fetches tasks from Asana and builds the DataFrame
        df = await builder.build_with_parallel_fetch_async(client)

        logger.info(
            "unit_dataframe_built",
            extra={
                "project_gid": unit_project_gid,
                "row_count": len(df),
            },
        )

        return df

    except Exception as e:
        # Graceful degradation: log error and return None
        # Lookups will return None for all pairs
        logger.warning(
            "unit_dataframe_build_failed",
            extra={
                "project_gid": unit_project_gid,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return None


async def _get_or_build_index(
    client: Any,
    unit_project_gid: str,
) -> GidLookupIndex | None:
    """Get cached GidLookupIndex or build a new one.

    Per task-003: TTL-based caching with 1-hour staleness check.

    Args:
        client: AsanaClient with valid authentication.
        unit_project_gid: Asana project GID containing Unit tasks.

    Returns:
        GidLookupIndex if available, None on build failure.
    """
    global _gid_index_cache

    # Check for cached index
    cached_index = _gid_index_cache.get(unit_project_gid)

    if cached_index is not None and not cached_index.is_stale(_INDEX_TTL_SECONDS):
        logger.debug(
            "gid_index_cache_hit",
            extra={
                "project_gid": unit_project_gid,
                "index_size": len(cached_index),
                "age_seconds": (
                    datetime.now(timezone.utc) - cached_index.created_at
                ).total_seconds(),
            },
        )
        return cached_index

    # Cache miss or stale - rebuild index
    cache_status = "stale" if cached_index is not None else "miss"
    logger.info(
        "gid_index_cache_rebuild",
        extra={
            "project_gid": unit_project_gid,
            "reason": cache_status,
        },
    )

    # Build DataFrame
    df = await _build_unit_dataframe(client, unit_project_gid)

    if df is None:
        logger.warning(
            "gid_index_build_failed_no_dataframe",
            extra={"project_gid": unit_project_gid},
        )
        return None

    try:
        # Build index from DataFrame
        index = GidLookupIndex.from_dataframe(df)

        # Cache the new index
        _gid_index_cache[unit_project_gid] = index

        logger.info(
            "gid_index_built",
            extra={
                "project_gid": unit_project_gid,
                "index_size": len(index),
            },
        )

        return index

    except KeyError as e:
        logger.error(
            "gid_index_build_failed_missing_columns",
            extra={
                "project_gid": unit_project_gid,
                "error": str(e),
            },
        )
        return None


async def _resolve_gids_with_client(
    client: Any,  # AsanaClient - use Any to avoid import issues
    pairs: list[PhoneVerticalInput],
    unit_project_gid: str,
) -> list[GidMappingOutput]:
    """Resolve GIDs using provided AsanaClient.

    This is separated from resolve_gids to make testing easier
    and to allow async context management of the client.

    Strategy (per task-003):
    - Get or build GidLookupIndex with TTL-based caching
    - Convert PhoneVerticalInput list to PhoneVerticalPair list
    - Use index.get_gids() for O(1) batch lookup
    - Map results back to GidMappingOutput list

    Args:
        client: AsanaClient with valid authentication.
        pairs: List of phone/vertical pairs to resolve.
        unit_project_gid: Asana project GID containing Unit tasks.

    Returns:
        List of GidMappingOutput in same order as input.
    """
    # Get or build the lookup index
    index = await _get_or_build_index(client, unit_project_gid)

    if index is None:
        # Index build failed - return None for all pairs
        logger.warning(
            "gid_resolution_no_index",
            extra={
                "project_gid": unit_project_gid,
                "pair_count": len(pairs),
            },
        )
        return [
            GidMappingOutput(
                phone=pair.phone,
                vertical=pair.vertical,
                task_gid=None,
            )
            for pair in pairs
        ]

    # Convert PhoneVerticalInput to PhoneVerticalPair for index lookup
    # PhoneVerticalInput uses 'phone', PhoneVerticalPair uses 'office_phone'
    pvp_pairs: list[PhoneVerticalPair] = []
    for pair in pairs:
        try:
            pvp = PhoneVerticalPair(
                office_phone=pair.phone,
                vertical=pair.vertical,
            )
            pvp_pairs.append(pvp)
        except ValueError as e:
            # Validation failed - should not happen as PhoneVerticalInput validates
            logger.warning(
                "pvp_conversion_failed",
                extra={
                    "phone": pair.phone,
                    "vertical": pair.vertical,
                    "error": str(e),
                },
            )
            pvp_pairs.append(None)  # type: ignore[arg-type]

    # Batch lookup using index - O(N) for N pairs
    results: list[GidMappingOutput] = []

    for i, pair in enumerate(pairs):
        pvp = pvp_pairs[i]

        if pvp is None:
            # Conversion failed
            results.append(
                GidMappingOutput(
                    phone=pair.phone,
                    vertical=pair.vertical,
                    task_gid=None,
                )
            )
            continue

        # O(1) lookup
        task_gid = index.get_gid(pvp)

        results.append(
            GidMappingOutput(
                phone=pair.phone,
                vertical=pair.vertical,
                task_gid=task_gid,
            )
        )

        if task_gid:
            logger.debug(
                "gid_resolved",
                extra={
                    "phone": pair.phone,
                    "vertical": pair.vertical,
                    "task_gid": task_gid,
                },
            )

    # Log summary
    resolved_count = sum(1 for r in results if r.task_gid is not None)
    logger.info(
        "gid_resolution_batch_complete",
        extra={
            "pair_count": len(pairs),
            "resolved_count": resolved_count,
            "unresolved_count": len(pairs) - resolved_count,
            "project_gid": unit_project_gid,
            "lookup_method": "gid_index",
        },
    )

    return results


# --- Endpoints ---


@router.post("/gid-lookup", response_model=GidLookupResponse)
async def gid_lookup(
    request: GidLookupRequest,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> GidLookupResponse:
    """Resolve phone/vertical pairs to task GIDs.

    This internal endpoint is used by autom8_data and other services
    to resolve business identifiers to Asana task GIDs.

    Authentication:
        Requires valid service token (S2S JWT).
        PAT tokens are NOT supported.

    Request:
        POST /api/v1/internal/gid-lookup
        {
            "phone_vertical_pairs": [
                {"phone": "+15551234567", "vertical": "dental"},
                {"phone": "+15559876543", "vertical": "medical"}
            ]
        }

    Response:
        {
            "mappings": [
                {"phone": "+15551234567", "vertical": "dental", "task_gid": "1234567890123456"},
                {"phone": "+15559876543", "vertical": "medical", "task_gid": null}
            ]
        }

    Args:
        request: GidLookupRequest with phone/vertical pairs.
        claims: Validated service claims from JWT.

    Returns:
        GidLookupResponse with mappings in input order.
    """
    logger.info(
        "gid_lookup_request",
        extra={
            "caller_service": claims.service_name,
            "pair_count": len(request.phone_vertical_pairs),
        },
    )

    mappings = await resolve_gids(request.phone_vertical_pairs)

    # Count resolved vs unresolved for logging
    resolved_count = sum(1 for m in mappings if m.task_gid is not None)

    logger.info(
        "gid_lookup_complete",
        extra={
            "caller_service": claims.service_name,
            "pair_count": len(request.phone_vertical_pairs),
            "resolved_count": resolved_count,
            "unresolved_count": len(mappings) - resolved_count,
        },
    )

    return GidLookupResponse(mappings=mappings)


__all__ = [
    # Router
    "router",
    # Models
    "PhoneVerticalInput",
    "GidLookupRequest",
    "GidMappingOutput",
    "GidLookupResponse",
    "ServiceClaims",
    # Dependencies
    "require_service_claims",
    # Logic
    "resolve_gids",
    "_resolve_gids_with_client",  # Exposed for testing
    "_build_unit_dataframe",  # Exposed for testing
    "_get_or_build_index",  # Exposed for testing
    # Cache management
    "_gid_index_cache",  # Exposed for testing cache behavior
    "_INDEX_TTL_SECONDS",  # Exposed for testing TTL behavior
]
