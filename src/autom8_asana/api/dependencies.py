"""FastAPI dependency injection for the API layer.

This module provides dependency factories for:
- Dual-mode authentication (JWT + PAT)
- Per-request AsanaClient instantiation
- Request ID access

Per TDD-S2S-001 Section 5.4:
- AuthContext provides unified auth result for both modes
- get_auth_context() is the primary auth dependency
- get_asana_pat() provides backward compatibility

Per ADR-ASANA-002: PAT Pass-Through Authentication
- Extract PAT from Authorization: Bearer header
- Validate token format (non-empty, minimum length)
- Create per-request SDK client

Per ADR-ASANA-007: SDK Client Lifecycle
- Per-request instantiation for user isolation
- Clean error boundaries
- No connection pooling across requests
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from autom8y_log import get_logger
from fastapi import Depends, Header, HTTPException, Request

from autom8_asana import AsanaClient
from autom8_asana.cache.integration.mutation_invalidator import MutationInvalidator

from ..auth.bot_pat import BotPATError, get_bot_pat
from ..auth.dual_mode import AuthMode, detect_token_type

logger = get_logger("autom8_asana.api")


class AuthContext:
    """Authentication context for the current request.

    Provides the PAT to use for Asana API calls, regardless of
    how the request was authenticated.

    Attributes:
        mode: How the request was authenticated (jwt or pat)
        asana_pat: The PAT to use for Asana API calls
        caller_service: Service name from JWT (None for PAT mode)
    """

    __slots__ = ("mode", "asana_pat", "caller_service")

    def __init__(
        self,
        mode: AuthMode,
        asana_pat: str,
        caller_service: str | None = None,
    ) -> None:
        """Initialize auth context.

        Args:
            mode: Authentication mode (JWT or PAT)
            asana_pat: PAT to use for Asana API calls
            caller_service: Service name (JWT mode only)
        """
        self.mode = mode
        self.asana_pat = asana_pat
        self.caller_service = caller_service


async def _extract_bearer_token(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Extract and validate Bearer token from Authorization header.

    Args:
        authorization: Authorization header value.

    Returns:
        Extracted token string.

    Raises:
        HTTPException: 401 if header missing, wrong scheme, or invalid format.
    """
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "MISSING_AUTH",
                "message": "Authorization header required",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "INVALID_SCHEME", "message": "Bearer scheme required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    if not token:
        raise HTTPException(
            status_code=401,
            detail={"error": "MISSING_TOKEN", "message": "Token is required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if len(token) < 10:
        raise HTTPException(
            status_code=401,
            detail={"error": "INVALID_TOKEN", "message": "Invalid token format"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


async def get_auth_context(
    request: Request,
    token: Annotated[str, Depends(_extract_bearer_token)],
) -> AuthContext:
    """Get authentication context for the current request.

    This is the primary auth dependency for route handlers.
    It detects the token type, validates JWTs, and provides
    the appropriate PAT for Asana API calls.

    For JWT auth (S2S):
        1. Validate JWT with autom8y-auth SDK
        2. Return bot PAT for Asana calls

    For PAT auth (user):
        1. Pass through user's PAT unchanged

    Args:
        request: FastAPI request (for logging context)
        token: Bearer token from Authorization header

    Returns:
        AuthContext with mode, asana_pat, and optional caller info

    Raises:
        HTTPException: 401 for invalid JWT, 503 for bot PAT misconfiguration
    """
    request_id = getattr(request.state, "request_id", "unknown")
    auth_mode = detect_token_type(token)

    if auth_mode == AuthMode.PAT:
        # PAT pass-through: user's token goes directly to Asana
        logger.info(
            "auth_mode_pat",
            extra={
                "request_id": request_id,
                "auth_mode": "pat",
            },
        )
        return AuthContext(mode=auth_mode, asana_pat=token)

    # JWT mode: validate token, then use bot PAT
    try:
        # Lazy import to avoid loading SDK when not needed
        from ..auth.jwt_validator import validate_service_token

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
        # Import the error base class for type checking
        try:
            from autom8y_auth import AuthError

            if isinstance(e, AuthError):
                logger.warning(
                    "s2s_jwt_validation_failed",
                    extra={
                        "request_id": request_id,
                        "error_code": e.code,
                        "error_message": str(e),
                    },
                )
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": e.code,
                        "message": "JWT validation failed",
                    },
                )
        except ImportError:
            pass

        # Re-raise unexpected errors
        logger.exception(
            "s2s_jwt_validation_unexpected_error",
            extra={"request_id": request_id},
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "Authentication error",
            },
        )

    try:
        bot_pat = get_bot_pat()
    except BotPATError as e:
        logger.error(
            "bot_pat_unavailable",
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

    logger.info(
        "auth_mode_jwt",
        extra={
            "request_id": request_id,
            "auth_mode": "jwt",
            "caller_service": claims.service_name,
            "scope": claims.scope,
        },
    )

    return AuthContext(
        mode=auth_mode,
        asana_pat=bot_pat,
        caller_service=claims.service_name,
    )


async def get_asana_pat(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Extract and validate PAT from Authorization header.

    DEPRECATED: Use get_auth_context() for dual-mode support.
    This function is maintained for backward compatibility with
    existing route handlers that expect only PAT authentication.

    Per ADR-ASANA-002:
    - Requires Bearer scheme
    - Validates non-empty token
    - Token must be at least 10 characters

    Args:
        authorization: Authorization header value.

    Returns:
        Extracted PAT token.

    Raises:
        HTTPException: 401 if header missing, wrong scheme, or invalid format.
    """
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization scheme. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if len(token) < 10:
        raise HTTPException(
            status_code=401,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


async def get_asana_client(
    pat: Annotated[str, Depends(get_asana_pat)],
) -> AsyncGenerator[AsanaClient, None]:
    """Create per-request AsanaClient with provided PAT.

    DEPRECATED for new routes: Use get_asana_client_from_context() instead
    for dual-mode support.

    Per ADR-ASANA-007:
    - Each request gets a fresh client instance
    - Complete user isolation (no shared state)
    - Clean error boundaries
    - Garbage collection handles cleanup

    Args:
        pat: Personal Access Token from Authorization header.

    Yields:
        AsanaClient instance configured with the provided PAT.
    """
    client = AsanaClient(token=pat)
    try:
        yield client
    finally:
        # Explicit cleanup if SDK supports async close
        if hasattr(client, "aclose"):
            await client.aclose()


async def get_asana_client_from_context(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
) -> AsyncGenerator[AsanaClient, None]:
    """Create per-request AsanaClient from auth context.

    Supports both JWT (S2S) and PAT (user) authentication modes.
    The client is configured with the appropriate PAT based on auth mode:
    - JWT mode: Uses bot PAT
    - PAT mode: Uses user's PAT

    Per ADR-ASANA-007:
    - Each request gets a fresh client instance
    - Complete user isolation (no shared state)
    - Clean error boundaries
    - Garbage collection handles cleanup

    Args:
        auth_context: Authentication context with PAT for Asana calls.

    Yields:
        AsanaClient instance configured with the appropriate PAT.
    """
    client = AsanaClient(token=auth_context.asana_pat)
    try:
        yield client
    finally:
        if hasattr(client, "aclose"):
            await client.aclose()


def get_mutation_invalidator(request: Request) -> MutationInvalidator:
    """Get the shared MutationInvalidator from app state.

    Per TDD-CACHE-INVALIDATION-001: The MutationInvalidator is created
    once during app startup and stored on app.state. This dependency
    provides access to it for route handlers.

    Args:
        request: FastAPI request (for app state access).

    Returns:
        MutationInvalidator instance, or a no-op instance if not initialized.
    """
    invalidator = getattr(request.app.state, "mutation_invalidator", None)
    if invalidator is None:
        # Graceful degradation: return a no-op invalidator
        # This happens during testing or when cache is disabled
        logger.warning("mutation_invalidator_not_initialized")
        from autom8_asana._defaults.cache import NullCacheProvider
        from autom8_asana.cache.integration.mutation_invalidator import MutationInvalidator as MI

        return MI(cache_provider=NullCacheProvider())
    return invalidator


def get_request_id(request: Request) -> str:
    """Get request ID from request state.

    The request_id is set by RequestIDMiddleware and is available
    on request.state for all downstream handlers.

    Args:
        request: FastAPI request object.

    Returns:
        16-character hex request ID, or "unknown" if not set.
    """
    return getattr(request.state, "request_id", "unknown")


# Type aliases for cleaner route signatures
AsanaPAT = Annotated[str, Depends(get_asana_pat)]
AsanaClientDep = Annotated[AsanaClient, Depends(get_asana_client)]
AsanaClientDualMode = Annotated[AsanaClient, Depends(get_asana_client_from_context)]
AuthContextDep = Annotated[AuthContext, Depends(get_auth_context)]
MutationInvalidatorDep = Annotated[
    MutationInvalidator, Depends(get_mutation_invalidator)
]
RequestId = Annotated[str, Depends(get_request_id)]


# --- Service Factories (I2 additions) ---


def get_entity_service(request: Request) -> "EntityService":
    """Get EntityService singleton from app state.

    Lazy initialization: creates on first access, stores on app.state.
    EntityService wraps singleton registries (EntityRegistry,
    EntityProjectRegistry) and has no per-request state.

    Per TDD-I2-SERVICE-WIRING-001: EntityService is a singleton.

    Args:
        request: FastAPI request (for app state access).

    Returns:
        EntityService instance.
    """
    entity_service = getattr(request.app.state, "entity_service", None)
    if entity_service is None:
        from autom8_asana.core.entity_registry import get_registry
        from autom8_asana.services.entity_service import EntityService
        from autom8_asana.services.resolver import EntityProjectRegistry

        entity_service = EntityService(
            entity_registry=get_registry(),
            project_registry=EntityProjectRegistry.get_instance(),
        )
        request.app.state.entity_service = entity_service
    return entity_service


def get_task_service(
    invalidator: MutationInvalidatorDep,
) -> "TaskService":
    """Get TaskService with MutationInvalidator.

    Per TDD-I2-SERVICE-WIRING-001: TaskService is per-request,
    receiving the MutationInvalidator via FastAPI's DI chain.

    Args:
        invalidator: MutationInvalidator from DI.

    Returns:
        TaskService instance.
    """
    from autom8_asana.services.task_service import TaskService

    return TaskService(invalidator=invalidator)


def get_section_service(
    invalidator: MutationInvalidatorDep,
) -> "SectionService":
    """Get SectionService with MutationInvalidator.

    Per TDD-I2-SERVICE-WIRING-001: SectionService is per-request,
    receiving the MutationInvalidator via FastAPI's DI chain.

    Args:
        invalidator: MutationInvalidator from DI.

    Returns:
        SectionService instance.
    """
    from autom8_asana.services.section_service import SectionService

    return SectionService(invalidator=invalidator)


# Import types for Annotated aliases (lazy to avoid cycles)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.services.entity_service import EntityService
    from autom8_asana.services.section_service import SectionService
    from autom8_asana.services.task_service import TaskService

EntityServiceDep = Annotated["EntityService", Depends(get_entity_service)]
TaskServiceDep = Annotated["TaskService", Depends(get_task_service)]
SectionServiceDep = Annotated["SectionService", Depends(get_section_service)]


__all__ = [
    # Auth context (new dual-mode)
    "AuthContext",
    "get_auth_context",
    "get_asana_client_from_context",
    # Cache invalidation
    "get_mutation_invalidator",
    "MutationInvalidatorDep",
    # Service factories (I2)
    "get_entity_service",
    "get_task_service",
    "get_section_service",
    "EntityServiceDep",
    "TaskServiceDep",
    "SectionServiceDep",
    # Legacy dependencies (backward compatibility)
    "get_asana_client",
    "get_asana_pat",
    "get_request_id",
    # Type aliases
    "AsanaClientDep",
    "AsanaClientDualMode",
    "AsanaPAT",
    "AuthContextDep",
    "RequestId",
]
