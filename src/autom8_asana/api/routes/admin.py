"""Admin routes for cache management.

Provides operational endpoints for manual cache control.
Authentication: Service token (S2S JWT) required.

Per TDD-cache-freshness-remediation Fix 4:
- POST /v1/admin/cache/refresh for manual cache invalidation and rebuild
- S2S JWT auth via require_service_claims
- Async background execution (202 Accepted)
"""

from __future__ import annotations

import uuid

from autom8y_log import get_logger
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel

from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims
from autom8_asana.core.entity_types import ENTITY_TYPES

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/admin", tags=["admin"], include_in_schema=False)

VALID_ENTITY_TYPES = set(ENTITY_TYPES)


class CacheRefreshRequest(BaseModel):
    """Request body for cache refresh endpoint.

    Attributes:
        entity_type: Specific entity type to refresh. If None, refresh all.
        force_full_rebuild: If True, delete manifests and rebuild from scratch.
    """

    entity_type: str | None = None
    force_full_rebuild: bool = False


class CacheRefreshResponse(BaseModel):
    """Response body for cache refresh endpoint.

    Attributes:
        status: Always "accepted" for 202 responses.
        message: Human-readable description of the action taken.
        entity_types: List of entity types being refreshed.
        refresh_id: Unique identifier for this refresh operation.
        force_full_rebuild: Whether full rebuild was requested.
    """

    status: str = "accepted"
    message: str
    entity_types: list[str]
    refresh_id: str
    force_full_rebuild: bool


async def _perform_cache_refresh(
    entity_types: list[str],
    force_full_rebuild: bool,
    refresh_id: str,
) -> None:
    """Background task to perform cache refresh.

    For force_full_rebuild=True: Deletes all cached data (memory, S3 manifests,
    S3 section parquets) and optionally triggers Lambda cache warmer. This avoids
    OOM kills from in-process builds that exceed the 1024MB container limit.

    For force_full_rebuild=False: Incremental rebuild via progressive builder
    (lightweight — resumes from existing manifests).

    Args:
        entity_types: Entity types to refresh.
        force_full_rebuild: Whether to delete all cached data and delegate rebuild.
        refresh_id: Unique identifier for logging correlation.
    """
    logger.info(
        "cache_refresh_started",
        extra={
            "refresh_id": refresh_id,
            "entity_types": entity_types,
            "force_full_rebuild": force_full_rebuild,
        },
    )

    if force_full_rebuild:
        await _perform_force_rebuild(entity_types, refresh_id)
    else:
        await _perform_incremental_rebuild(entity_types, refresh_id)

    logger.info(
        "cache_refresh_complete",
        extra={
            "refresh_id": refresh_id,
            "entity_types": entity_types,
        },
    )


async def _perform_force_rebuild(
    entity_types: list[str],
    refresh_id: str,
) -> None:
    """Delete all cached data and optionally trigger Lambda rebuild.

    This is lightweight — no in-process DataFrame builds. Cache is rebuilt
    either by the Lambda cache warmer or on next container restart.

    Args:
        entity_types: Entity types to purge and rebuild.
        refresh_id: Unique identifier for logging correlation.
    """
    import os

    from autom8_asana.cache.dataframe.factory import get_dataframe_cache
    from autom8_asana.dataframes.section_persistence import create_section_persistence
    from autom8_asana.services.resolver import EntityProjectRegistry

    registry = EntityProjectRegistry.get_instance()
    dataframe_cache = get_dataframe_cache()
    persistence = create_section_persistence()

    for entity_type in entity_types:
        try:
            project_gid = registry.get_project_gid(entity_type)
            if not project_gid:
                logger.warning(
                    "cache_refresh_no_project_gid",
                    extra={
                        "refresh_id": refresh_id,
                        "entity_type": entity_type,
                    },
                )
                continue

            # 1. Invalidate memory cache
            if dataframe_cache is not None:
                try:
                    dataframe_cache.invalidate(project_gid, entity_type)
                except Exception as e:  # BROAD-CATCH: degrade
                    logger.warning(
                        "cache_refresh_invalidate_failed",
                        extra={
                            "refresh_id": refresh_id,
                            "entity_type": entity_type,
                            "error": str(e),
                        },
                    )

            # 2. Delete S3 manifest, section parquets, AND merged artifacts
            try:
                async with persistence:
                    await persistence.delete_manifest_async(project_gid)
                    await persistence.delete_section_files_async(project_gid)
                    # Per ADR-HOTFIX-002: Also delete merged dataframe.parquet
                    # and watermark.json to prevent ProgressiveTier from
                    # re-hydrating stale data into the memory tier.
                    await persistence.storage.delete_dataframe(project_gid)
                logger.info(
                    "cache_refresh_s3_purged",
                    extra={
                        "refresh_id": refresh_id,
                        "entity_type": entity_type,
                        "project_gid": project_gid,
                    },
                )
            except Exception as e:  # BROAD-CATCH: degrade
                logger.warning(
                    "cache_refresh_s3_purge_failed",
                    extra={
                        "refresh_id": refresh_id,
                        "entity_type": entity_type,
                        "error": str(e),
                    },
                )

        except Exception as e:  # BROAD-CATCH: isolation
            logger.error(
                "cache_refresh_entity_failed",
                extra={
                    "refresh_id": refresh_id,
                    "entity_type": entity_type,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

    # 3. Trigger Lambda cache warmer if configured
    lambda_arn = os.environ.get("CACHE_WARMER_LAMBDA_ARN")
    if lambda_arn:
        _invoke_cache_warmer_lambda(lambda_arn, entity_types, refresh_id)
    else:
        logger.info(
            "no_lambda_arn_configured",
            extra={
                "refresh_id": refresh_id,
                "message": "cache will rebuild on next restart",
            },
        )


async def _perform_incremental_rebuild(
    entity_types: list[str],
    refresh_id: str,
) -> None:
    """Incremental rebuild via progressive builder (resumes from manifests).

    This is lightweight — only fetches changed sections since last manifest.

    Args:
        entity_types: Entity types to incrementally refresh.
        refresh_id: Unique identifier for logging correlation.
    """
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
    from autom8_asana.cache.dataframe.factory import get_dataframe_cache
    from autom8_asana.config import get_workspace_gid
    from autom8_asana.dataframes.builders.progressive import ProgressiveProjectBuilder
    from autom8_asana.dataframes.models.registry import get_schema
    from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
    from autom8_asana.dataframes.section_persistence import create_section_persistence
    from autom8_asana.dataframes.watermark import get_watermark_repo
    from autom8_asana.services.resolver import EntityProjectRegistry, to_pascal_case

    try:
        bot_pat = get_bot_pat()
    except BotPATError as e:
        logger.error(
            "cache_refresh_no_bot_pat",
            extra={"refresh_id": refresh_id, "error": str(e)},
        )
        return

    workspace_gid = get_workspace_gid()
    if not workspace_gid:
        logger.error(
            "cache_refresh_no_workspace",
            extra={"refresh_id": refresh_id},
        )
        return

    registry = EntityProjectRegistry.get_instance()
    dataframe_cache = get_dataframe_cache()
    watermark_repo = get_watermark_repo()
    persistence = create_section_persistence()

    for entity_type in entity_types:
        try:
            project_gid = registry.get_project_gid(entity_type)
            if not project_gid:
                logger.warning(
                    "cache_refresh_no_project_gid",
                    extra={
                        "refresh_id": refresh_id,
                        "entity_type": entity_type,
                    },
                )
                continue

            # Invalidate existing cache entry
            if dataframe_cache is not None:
                try:
                    dataframe_cache.invalidate(project_gid, entity_type)
                except Exception as e:  # BROAD-CATCH: degrade
                    logger.warning(
                        "cache_refresh_invalidate_failed",
                        extra={
                            "refresh_id": refresh_id,
                            "entity_type": entity_type,
                            "error": str(e),
                        },
                    )

            # Incremental rebuild via parallel fetch (resumes from manifest)
            async with AsanaClient(
                token=bot_pat, workspace_gid=workspace_gid
            ) as client:
                task_type = to_pascal_case(entity_type)
                schema = get_schema(task_type)
                resolver = DefaultCustomFieldResolver()

                async with persistence:
                    from autom8_asana.services.gid_lookup import build_gid_index_data

                    builder = ProgressiveProjectBuilder(
                        client=client,
                        project_gid=project_gid,
                        entity_type=entity_type,
                        schema=schema,
                        persistence=persistence,
                        resolver=resolver,
                        store=client.unified_store,
                        index_builder=build_gid_index_data,
                    )

                    build_result = await builder.build_progressive_async(resume=True)
                    df = build_result.dataframe
                    watermark = build_result.watermark

                # Update cache and watermark
                if dataframe_cache is not None and df is not None and len(df) > 0:
                    await dataframe_cache.put_async(
                        project_gid, entity_type, df, watermark
                    )
                watermark_repo.set_watermark(project_gid, watermark)

                logger.info(
                    "cache_refresh_entity_complete",
                    extra={
                        "refresh_id": refresh_id,
                        "entity_type": entity_type,
                        "project_gid": project_gid,
                        "rows": len(df) if df is not None else 0,
                    },
                )

        except Exception as e:  # BROAD-CATCH: isolation
            logger.error(
                "cache_refresh_entity_failed",
                extra={
                    "refresh_id": refresh_id,
                    "entity_type": entity_type,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )


def _invoke_cache_warmer_lambda(
    function_arn: str,
    entity_types: list[str],
    refresh_id: str,
) -> None:
    """Invoke cache warmer Lambda asynchronously (fire-and-forget).

    Args:
        function_arn: ARN of the Lambda function to invoke.
        entity_types: Entity types to rebuild.
        refresh_id: Unique identifier for logging correlation.
    """
    import json

    import boto3

    client = boto3.client("lambda")
    payload = {
        "entity_types": entity_types,
        "strict": False,
        "resume_from_checkpoint": False,
    }
    try:
        client.invoke(
            FunctionName=function_arn,
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        logger.info(
            "cache_warmer_lambda_invoked",
            extra={
                "function_arn": function_arn,
                "entity_types": entity_types,
                "refresh_id": refresh_id,
            },
        )
    except Exception as e:  # BROAD-CATCH: degrade
        logger.error(
            "cache_warmer_lambda_invoke_failed",
            extra={
                "error": str(e),
                "refresh_id": refresh_id,
            },
        )


@router.post(
    "/cache/refresh",
    response_model=CacheRefreshResponse,
    status_code=202,
)
async def refresh_cache(
    request: Request,
    body: CacheRefreshRequest,
    background_tasks: BackgroundTasks,
    claims: ServiceClaims = Depends(require_service_claims),  # noqa: B008
) -> CacheRefreshResponse:
    """Trigger cache refresh for one or all entity types.

    Requires S2S JWT authentication. Kicks off a background task and
    returns 202 Accepted immediately.

    Args:
        request: FastAPI request object.
        body: Cache refresh request parameters.
        background_tasks: FastAPI background tasks.
        claims: Validated service claims from S2S JWT.

    Returns:
        CacheRefreshResponse with refresh details.

    Raises:
        HTTPException: 400 for invalid entity type, 503 for cache not ready.
    """
    from autom8_asana.cache.dataframe.factory import get_dataframe_cache
    from autom8_asana.services.resolver import EntityProjectRegistry

    request_id = getattr(request.state, "request_id", "unknown")

    # Validate entity type
    if body.entity_type is not None and body.entity_type not in VALID_ENTITY_TYPES:
        raise_api_error(
            request_id,
            400,
            "INVALID_ENTITY_TYPE",
            f"Invalid entity_type: '{body.entity_type}'. "
            f"Valid types: {sorted(VALID_ENTITY_TYPES)}",
        )

    # Check cache system is initialized
    cache = get_dataframe_cache()
    if cache is None:
        raise_api_error(
            request_id,
            503,
            "CACHE_NOT_INITIALIZED",
            "Cache system is not initialized. Try again later.",
        )

    # Check registry is ready
    registry = EntityProjectRegistry.get_instance()
    if not registry.is_ready():
        raise_api_error(
            request_id,
            503,
            "REGISTRY_NOT_READY",
            "Entity project registry is not initialized.",
        )

    # Determine entity types to refresh
    if body.entity_type is not None:
        entity_types = [body.entity_type]
    else:
        entity_types = sorted(VALID_ENTITY_TYPES)

    refresh_id = str(uuid.uuid4())

    logger.info(
        "cache_refresh_requested",
        extra={
            "refresh_id": refresh_id,
            "entity_types": entity_types,
            "force_full_rebuild": body.force_full_rebuild,
            "caller_service": claims.service_name,
        },
    )

    # Schedule background task
    background_tasks.add_task(
        _perform_cache_refresh,
        entity_types=entity_types,
        force_full_rebuild=body.force_full_rebuild,
        refresh_id=refresh_id,
    )

    entity_list = ", ".join(entity_types)
    message = f"Cache refresh initiated for entity_type={entity_list}"
    if body.force_full_rebuild:
        message += " (force full rebuild)"

    return CacheRefreshResponse(
        status="accepted",
        message=message,
        entity_types=entity_types,
        refresh_id=refresh_id,
        force_full_rebuild=body.force_full_rebuild,
    )
