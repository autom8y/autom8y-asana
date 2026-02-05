"""Progressive preload with parallel project processing.

Extracted from api/main.py per TDD-I5 (API Main Decomposition).
This module implements the progressive preload strategy that processes
projects in parallel with resume capability and heartbeat monitoring.

Note: bare-except sites are preserved as-is from main.py.
They are tagged for narrowing in I6 (Exception Narrowing).
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from autom8y_log import get_logger
from fastapi import FastAPI

from .constants import (
    HEARTBEAT_INTERVAL_SECONDS,
    PRELOAD_EXCLUDE_PROJECT_GIDS,
    PROJECT_CONCURRENCY,
)

if TYPE_CHECKING:
    import polars as pl

logger = get_logger(__name__)


def _invoke_cache_warmer_lambda_from_preload(
    function_arn: str, entity_types: list[str]
) -> None:
    """Invoke cache warmer Lambda for entities missing S3 data."""
    import json

    import boto3

    payload = {
        "entity_types": entity_types,
        "strict": False,
        "resume_from_checkpoint": False,
    }
    try:
        client = boto3.client("lambda")
        client.invoke(
            FunctionName=function_arn,
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        logger.info(
            "preload_lambda_invoked",
            extra={
                "function_arn": function_arn,
                "entity_types": entity_types,
            },
        )
    except Exception as e:  # BROAD-CATCH: degrade
        logger.error(
            "preload_lambda_invoke_failed",
            extra={
                "error": str(e),
                "entity_types": entity_types,
            },
        )


async def _preload_dataframe_cache_progressive(app: FastAPI) -> None:
    """Pre-warm DataFrame cache using progressive section writes.

    Per progressive cache warming architecture:
    - Processes projects in parallel (3 concurrent)
    - Writes section DataFrames progressively to S3
    - Resume capability from manifest on restart
    - 30-second heartbeats during long operations

    Args:
        app: FastAPI application instance (provides access to entity_project_registry)
    """
    import os
    import time

    from autom8_asana import AsanaClient
    from autom8_asana.api.routes.health import set_cache_ready
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
    from autom8_asana.cache.dataframe.factory import get_dataframe_cache
    from autom8_asana.dataframes.builders.progressive import (
        ProgressiveProjectBuilder,
    )
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
    from autom8_asana.dataframes.section_persistence import SectionPersistence
    from autom8_asana.dataframes.watermark import get_watermark_repo
    from autom8_asana.services.resolver import EntityProjectRegistry, to_pascal_case

    start_time = time.perf_counter()
    loaded_count = 0
    total_projects = 0
    total_rows = 0
    sections_fetched_total = 0
    sections_resumed_total = 0
    projects_in_progress: set[str] = set()
    projects_completed: set[str] = set()
    projects_needing_lambda: list[str] = []

    # Heartbeat state
    heartbeat_task: asyncio.Task[None] | None = None

    async def heartbeat_loop() -> None:
        """Log progress heartbeat every 30 seconds."""
        nonlocal projects_in_progress, projects_completed
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            elapsed = (time.perf_counter() - start_time) * 1000
            remaining = total_projects - len(projects_completed)

            logger.info(
                "preload_heartbeat",
                extra={
                    "projects_completed": len(projects_completed),
                    "projects_in_progress": len(projects_in_progress),
                    "projects_remaining": remaining,
                    "sections_fetched_total": sections_fetched_total,
                    "sections_resumed_total": sections_resumed_total,
                    "elapsed_ms": round(elapsed, 2),
                },
            )

    try:
        # Get registered projects from entity resolver
        entity_registry: EntityProjectRegistry | None = getattr(
            app.state, "entity_project_registry", None
        )

        if entity_registry is None or not entity_registry.is_ready():
            logger.warning(
                "progressive_preload_skipped",
                extra={"reason": "entity_registry_not_ready"},
            )
            set_cache_ready(True)
            return

        # Get all registered project GIDs with their entity types
        # Per DX improvement: Preload all registered projects by default, exclude-list for opt-out
        registered_types = entity_registry.get_all_entity_types()
        project_configs: list[tuple[str, str]] = []  # (project_gid, entity_type)
        excluded_count = 0
        for entity_type in registered_types:
            config = entity_registry.get_config(entity_type)
            if config and config.project_gid:
                if config.project_gid in PRELOAD_EXCLUDE_PROJECT_GIDS:
                    logger.debug(
                        "progressive_preload_project_excluded",
                        extra={
                            "entity_type": entity_type,
                            "project_gid": config.project_gid,
                        },
                    )
                    excluded_count += 1
                    continue
                project_configs.append((config.project_gid, entity_type))

        total_projects = len(project_configs)

        if not project_configs:
            logger.info(
                "progressive_preload_skipped",
                extra={
                    "reason": "no_registered_projects",
                    "excluded_count": excluded_count,
                },
            )
            set_cache_ready(True)
            return

        project_gids = [gid for gid, _ in project_configs]
        logger.info(
            "progressive_preload_starting",
            extra={
                "project_count": total_projects,
                "project_gids": project_gids,
                "project_concurrency": PROJECT_CONCURRENCY,
                "excluded_count": excluded_count,
            },
        )

        # Get bot PAT for API access
        try:
            bot_pat = get_bot_pat()
        except BotPATError:
            logger.warning(
                "progressive_preload_no_bot_pat",
                extra={"fallback": "cache_built_on_request"},
            )
            set_cache_ready(True)
            return

        workspace_gid = os.environ.get("ASANA_WORKSPACE_GID")
        if not workspace_gid:
            logger.warning(
                "progressive_preload_no_workspace",
                extra={"fallback": "cache_built_on_request"},
            )
            set_cache_ready(True)
            return

        # Initialize unified S3DataFrameStorage (Phase 2/3,
        # TDD-UNIFIED-DF-PERSISTENCE-001): single S3 backend with
        # RetryOrchestrator, shared by SectionPersistence and WatermarkRepo.
        from autom8_asana.config import S3LocationConfig
        from autom8_asana.dataframes.storage import (
            S3DataFrameStorage,
            create_s3_retry_orchestrator,
        )
        from autom8_asana.settings import get_settings as get_app_settings

        app_settings = get_app_settings()
        s3_location = S3LocationConfig(
            bucket=app_settings.s3.bucket or "",
            region=app_settings.s3.region,
            endpoint_url=app_settings.s3.endpoint_url,
        )
        df_storage: S3DataFrameStorage | None = None
        if s3_location.bucket:
            df_storage = S3DataFrameStorage(
                location=s3_location,
                retry_orchestrator=create_s3_retry_orchestrator(),
            )

        # Initialize section persistence with unified storage delegate
        if df_storage is None:
            logger.warning("progressive_preload_no_s3_storage")
            return
        persistence = SectionPersistence(storage=df_storage)

        # Create SHARED UnifiedTaskStore for cascade field resolution
        # Per cascade architecture: Business tasks must be available when Unit builds
        # Each AsanaClient creates its own store, but cascade needs cross-project access
        from autom8_asana.cache.integration.factory import CacheProviderFactory
        from autom8_asana.config import CacheConfig

        shared_store = CacheProviderFactory.create_unified_store(
            config=CacheConfig(enabled=True),
        )
        logger.info(
            "progressive_preload_shared_store_created",
            extra={"purpose": "cross_project_cascade_resolution"},
        )

        if not persistence.is_available:
            logger.warning(
                "progressive_preload_s3_unavailable",
                extra={
                    "detail": "S3 not available, falling back to legacy preload",
                },
            )
            # Fall back to existing preload (cross-module import within subpackage)
            from .legacy import _preload_dataframe_cache

            await _preload_dataframe_cache(app)
            return

        # Get watermark repository and DataFrameCache singleton
        watermark_repo = get_watermark_repo()
        # Wire unified storage into WatermarkRepository for write-through persistence.
        # Per TDD-UNIFIED-DF-PERSISTENCE-001 Phase 3: WatermarkRepository uses
        # S3DataFrameStorage via the DataFrameStorage protocol.
        if df_storage is not None:
            watermark_repo.set_persistence(df_storage)
        dataframe_cache = get_dataframe_cache()

        # Start heartbeat task
        heartbeat_task = asyncio.create_task(heartbeat_loop())

        # Process projects with bounded concurrency
        semaphore = asyncio.Semaphore(PROJECT_CONCURRENCY)

        async def process_project(project_gid: str, entity_type: str) -> bool:
            """Process a single project with progressive build."""
            nonlocal sections_fetched_total, sections_resumed_total

            async with semaphore:
                projects_in_progress.add(project_gid)

                try:
                    async with persistence:
                        async with AsanaClient(
                            token=bot_pat, workspace_gid=workspace_gid
                        ) as client:
                            task_type = to_pascal_case(entity_type)
                            schema = SchemaRegistry.get_instance().get_schema(task_type)
                            resolver = DefaultCustomFieldResolver()

                            builder = ProgressiveProjectBuilder(
                                client=client,
                                project_gid=project_gid,
                                entity_type=entity_type,
                                schema=schema,
                                persistence=persistence,
                                resolver=resolver,
                                store=shared_store,  # Use SHARED store for cascade resolution
                            )

                            # Check if manifest exists — if not, the
                            # progressive builder would do a full API fetch
                            # which risks OOM.  Instead, try loading
                            # dataframe.parquet that Lambda may have already
                            # written.  Only delegate to Lambda if no parquet
                            # exists either.
                            manifest = await persistence.get_manifest_async(project_gid)
                            if manifest is None:
                                # Try loading existing dataframe.parquet from
                                # S3 (Lambda writes this and deletes the
                                # manifest after a successful warm).
                                # Per TDD-UNIFIED-DF-PERSISTENCE-001:
                                # Use S3DataFrameStorage when available.
                                s3_df: pl.DataFrame | None = None
                                s3_watermark: datetime | None = None
                                if df_storage is not None:
                                    (
                                        s3_df,
                                        s3_watermark,
                                    ) = await df_storage.load_dataframe(project_gid)
                                else:
                                    # No storage available -- cannot load parquet
                                    s3_df = None
                                    s3_watermark = None

                                if s3_df is not None and len(s3_df) > 0:
                                    # Parquet exists — load directly into
                                    # memory cache (no API calls needed).
                                    logger.info(
                                        "progressive_preload_loaded_from_parquet",
                                        extra={
                                            "project_gid": project_gid,
                                            "entity_type": entity_type,
                                            "rows": len(s3_df),
                                            "watermark": (
                                                s3_watermark.isoformat()
                                                if s3_watermark
                                                else None
                                            ),
                                        },
                                    )
                                    if s3_watermark is not None:
                                        watermark_repo.set_watermark(
                                            project_gid, s3_watermark
                                        )
                                    if (
                                        dataframe_cache is not None
                                        and s3_watermark is not None
                                    ):
                                        await dataframe_cache.put_async(
                                            project_gid,
                                            entity_type,
                                            s3_df,
                                            s3_watermark,
                                        )
                                    return True

                                # No parquet either — delegate to Lambda
                                lambda_arn = os.environ.get("CACHE_WARMER_LAMBDA_ARN")
                                if lambda_arn:
                                    projects_needing_lambda.append(entity_type)
                                    logger.info(
                                        "progressive_preload_no_manifest_delegating",
                                        extra={
                                            "project_gid": project_gid,
                                            "entity_type": entity_type,
                                            "reason": "no manifest or parquet, delegating to Lambda",
                                        },
                                    )
                                    return False
                                else:
                                    logger.warning(
                                        "progressive_preload_no_manifest_no_lambda",
                                        extra={
                                            "project_gid": project_gid,
                                            "entity_type": entity_type,
                                            "reason": "no manifest or parquet, no Lambda ARN — skipping",
                                        },
                                    )
                                    return False

                            result = await builder.build_progressive_async(resume=True)

                            # Update totals
                            sections_fetched_total += result.sections_succeeded
                            sections_resumed_total += result.sections_resumed

                            if result.total_rows > 0:
                                # Store in watermark repo
                                watermark_repo.set_watermark(
                                    project_gid, result.watermark
                                )

                                # Store in DataFrameCache singleton
                                if (
                                    dataframe_cache is not None
                                    and result.dataframe is not None
                                ):
                                    await dataframe_cache.put_async(
                                        project_gid,
                                        entity_type,
                                        result.dataframe,
                                        result.watermark,
                                        build_result=result,
                                    )

                            return True

                except Exception as e:  # BROAD-CATCH: isolation
                    logger.error(
                        "progressive_preload_project_failed",
                        extra={
                            "project_gid": project_gid,
                            "entity_type": entity_type,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
                    return False

                finally:
                    projects_in_progress.discard(project_gid)
                    projects_completed.add(project_gid)

        # Process Business first for cascade dependencies
        # Unit cascade fields (office_phone, vertical) need Business data in store
        business_configs = [
            (gid, etype) for gid, etype in project_configs if etype == "business"
        ]
        other_configs = [
            (gid, etype) for gid, etype in project_configs if etype != "business"
        ]

        # Process Business project(s) first
        if business_configs:
            logger.info(
                "progressive_preload_business_first",
                extra={"business_count": len(business_configs)},
            )
            business_results = await asyncio.gather(
                *[
                    process_project(project_gid, entity_type)
                    for project_gid, entity_type in business_configs
                ],
                return_exceptions=True,
            )
            for result in business_results:
                if isinstance(result, bool) and result:
                    loaded_count += 1

        # Then process remaining projects in parallel
        if other_configs:
            other_results = await asyncio.gather(
                *[
                    process_project(project_gid, entity_type)
                    for project_gid, entity_type in other_configs
                ],
                return_exceptions=True,
            )
            for result in other_results:
                if isinstance(result, bool) and result:
                    loaded_count += 1

        # Invoke Lambda once for all entities missing S3 manifests
        if projects_needing_lambda:
            lambda_arn = os.environ.get("CACHE_WARMER_LAMBDA_ARN")
            if lambda_arn:
                _invoke_cache_warmer_lambda_from_preload(
                    lambda_arn, projects_needing_lambda
                )

    except Exception as e:  # BROAD-CATCH: degrade
        logger.error(
            "progressive_preload_failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

    finally:
        # Stop heartbeat
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        # Always set cache ready
        set_cache_ready(True)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "progressive_preload_complete",
            extra={
                "projects_loaded": loaded_count,
                "total_projects": total_projects,
                "total_rows": total_rows,
                "sections_fetched": sections_fetched_total,
                "sections_resumed": sections_resumed_total,
                "duration_ms": round(elapsed_ms, 2),
                "cold_start_target_met": elapsed_ms < 5000,
            },
        )
