"""Legacy preload functions for DataFrame cache warming.

Extracted from api/main.py per TDD-I5 (API Main Decomposition).
These functions implement the original preload strategy with
incremental catch-up and full rebuild capabilities.

Note: 12 bare-except sites are preserved as-is from main.py.
They are tagged for narrowing in I6 (Exception Narrowing).
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autom8y_log import get_logger
from fastapi import FastAPI

if TYPE_CHECKING:
    import polars as pl

    from autom8_asana.dataframes.persistence import DataFramePersistence
    from autom8_asana.services.gid_lookup import GidLookupIndex

logger = get_logger(__name__)


async def _preload_dataframe_cache(app: FastAPI) -> None:
    """Pre-warm DataFrame cache before accepting traffic with incremental catch-up.

    Per sprint-materialization-002 FR-003:
    - Attempts to load persisted DataFrames from S3 for all registered projects
    - Populates WatermarkRepository with loaded watermarks
    - Populates GidLookupIndex cache with loaded DataFrames
    - Sets health check to ready after preload completes

    Per sprint-materialization-003 Task 3:
    - Loads persisted GidLookupIndex from S3 (before building new indices)
    - Runs incremental catch-up (fetch only tasks modified since watermark)
    - Falls back to full build when no persisted state
    - Persists updated state after catch-up
    - Logs timing metrics for cold start (target: <5s with persisted state)

    Per sprint-materialization-003 Task 4:
    - Loads watermarks FIRST from S3 before loading DataFrames
    - Configures WatermarkRepository with persistence for write-through

    Per FR-004:
    - Health check returns 503 during preload
    - Health check returns 200 after preload completes

    Graceful Degradation:
    - S3 unavailable: Logs warning, continues startup (cache will be built on first request)
    - Load error for specific project: Logs warning, continues with other projects
    - Always sets cache_ready to True at end (service can function without warm cache)

    Args:
        app: FastAPI application instance (provides access to entity_project_registry)
    """
    import time

    from autom8_asana.api.routes.health import set_cache_ready
    from autom8_asana.cache.dataframe.factory import get_dataframe_cache
    from autom8_asana.dataframes.persistence import DataFramePersistence
    from autom8_asana.dataframes.watermark import get_watermark_repo
    from autom8_asana.services.gid_lookup import GidLookupIndex
    from autom8_asana.services.resolver import EntityProjectRegistry

    start_time = time.perf_counter()
    loaded_count = 0
    total_projects = 0
    total_rows = 0
    watermarks_loaded = 0
    incremental_catchups = 0
    full_rebuilds = 0
    indices_loaded_from_s3 = 0
    cache_puts = 0  # DataFrameCache singleton puts

    try:
        # Get registered projects from entity resolver
        entity_registry: EntityProjectRegistry | None = getattr(
            app.state, "entity_project_registry", None
        )

        if entity_registry is None or not entity_registry.is_ready():
            logger.warning(
                "dataframe_preload_skipped",
                extra={"reason": "entity_registry_not_ready"},
            )
            set_cache_ready(True)
            return

        # Get all registered project GIDs with their entity types
        registered_types = entity_registry.get_all_entity_types()
        project_configs: list[tuple[str, str]] = []  # (project_gid, entity_type)
        for entity_type in registered_types:
            config = entity_registry.get_config(entity_type)
            if config and config.project_gid:
                project_configs.append((config.project_gid, entity_type))

        total_projects = len(project_configs)

        if not project_configs:
            logger.info(
                "dataframe_preload_skipped",
                extra={"reason": "no_registered_projects"},
            )
            set_cache_ready(True)
            return

        project_gids = [gid for gid, _ in project_configs]
        logger.info(
            "dataframe_preload_starting",
            extra={
                "project_count": total_projects,
                "project_gids": project_gids,
            },
        )

        # Initialize persistence layer
        persistence = DataFramePersistence()

        if not persistence.is_available:
            logger.warning(
                "dataframe_preload_s3_unavailable",
                extra={
                    "detail": "S3 persistence not available, cache will be built on first request",
                },
            )
            set_cache_ready(True)
            return

        # Get watermark repository and configure persistence for write-through
        watermark_repo = get_watermark_repo()
        watermark_repo.set_persistence(persistence)

        # Get DataFrameCache singleton for @dataframe_cache decorator coordination
        # Per TDD-DATAFRAME-CACHE-001: Preload must populate the cache singleton
        # so @dataframe_cache decorator finds cache hits instead of rebuilding
        dataframe_cache = get_dataframe_cache()

        # Load all watermarks FIRST from S3 (sprint-materialization-003 Task 4)
        # This bulk load is more efficient than per-project loads
        watermarks_loaded = await watermark_repo.load_from_persistence(persistence)

        logger.info(
            "dataframe_preload_watermarks_restored",
            extra={
                "watermarks_loaded": watermarks_loaded,
            },
        )

        # Process each project with incremental catch-up strategy
        for project_gid, entity_type in project_configs:
            project_start = time.perf_counter()

            try:
                # Step 1: Try loading persisted index from S3
                index = await persistence.load_index(project_gid)
                df, persisted_watermark = await persistence.load_dataframe(project_gid)
                watermark = watermark_repo.get_watermark(project_gid)

                # Use persisted watermark if in-memory is missing
                if watermark is None and persisted_watermark is not None:
                    watermark = persisted_watermark
                    watermark_repo.set_watermark(project_gid, watermark)

                # CRITICAL: If DataFrame exists but index doesn't, rebuild index from
                # DataFrame in memory (milliseconds) instead of triggering full API rebuild.
                # This handles the case where index failed to persist/load but DataFrame is intact.
                if index is None and df is not None and watermark is not None:
                    logger.info(
                        "dataframe_preload_index_recovery",
                        extra={
                            "project_gid": project_gid,
                            "entity_type": entity_type,
                            "dataframe_rows": len(df),
                            "reason": "index_missing_but_df_exists",
                        },
                    )
                    try:
                        index = GidLookupIndex.from_dataframe(df)
                        # Persist the recovered index for next startup
                        await persistence.save_index(project_gid, index)
                        logger.info(
                            "dataframe_preload_index_recovered",
                            extra={
                                "project_gid": project_gid,
                                "entity_type": entity_type,
                                "index_entries": len(index),
                            },
                        )
                    except Exception as e:
                        logger.warning(
                            "dataframe_preload_index_recovery_failed",
                            extra={
                                "project_gid": project_gid,
                                "entity_type": entity_type,
                                "error": str(e),
                            },
                        )
                        # index remains None, will fall through to full rebuild

                if index is not None and df is not None and watermark is not None:
                    # Have persisted state - do incremental catch-up
                    indices_loaded_from_s3 += 1

                    logger.info(
                        "dataframe_preload_incremental_start",
                        extra={
                            "project_gid": project_gid,
                            "entity_type": entity_type,
                            "persisted_rows": len(df),
                            "persisted_index_entries": len(index),
                            "watermark": watermark.isoformat(),
                        },
                    )

                    # Perform incremental catch-up
                    (
                        updated_df,
                        new_watermark,
                        was_incremental,
                    ) = await _do_incremental_catchup(
                        project_gid=project_gid,
                        entity_type=entity_type,
                        existing_df=df,
                        existing_index=index,
                        watermark=watermark,
                        persistence=persistence,
                    )

                    if was_incremental:
                        incremental_catchups += 1
                    else:
                        full_rebuilds += 1

                    # Check if DataFrame changed (need to rebuild index)
                    if updated_df is not df:
                        # DataFrame was updated - rebuild index
                        try:
                            index = GidLookupIndex.from_dataframe(updated_df)
                        except KeyError as e:
                            logger.warning(
                                "dataframe_preload_index_rebuild_failed",
                                extra={
                                    "project_gid": project_gid,
                                    "error": str(e),
                                },
                            )
                            # Use persisted index as fallback
                            pass

                        # Persist updated state
                        # Note: For incremental deltas (was_incremental=True),
                        # builder._merge_deltas_async does NOT auto-persist.
                        # For full rebuild fallback (was_incremental=False),
                        # builder already persisted via _persist_dataframe_async.
                        if was_incremental:
                            await persistence.save_dataframe(
                                project_gid, updated_df, new_watermark
                            )
                        await persistence.save_index(project_gid, index)
                        watermark_repo.set_watermark(project_gid, new_watermark)

                    # Store in DataFrameCache singleton for @dataframe_cache decorator
                    # This ensures decorator finds cache hit instead of rebuilding
                    if dataframe_cache is not None:
                        await dataframe_cache.put_async(
                            project_gid, entity_type, updated_df, new_watermark
                        )
                        cache_puts += 1

                    loaded_count += 1
                    total_rows += len(updated_df)

                    project_elapsed = (time.perf_counter() - project_start) * 1000
                    logger.info(
                        "dataframe_preload_project_complete",
                        extra={
                            "project_gid": project_gid,
                            "entity_type": entity_type,
                            "row_count": len(updated_df),
                            "index_entries": len(index),
                            "strategy": "incremental" if was_incremental else "full",
                            "duration_ms": round(project_elapsed, 2),
                        },
                    )

                else:
                    # No persisted state - full rebuild required
                    logger.info(
                        "dataframe_preload_full_rebuild_start",
                        extra={
                            "project_gid": project_gid,
                            "entity_type": entity_type,
                            "has_index": index is not None,
                            "has_df": df is not None,
                            "has_watermark": watermark is not None,
                        },
                    )

                    # Full rebuild
                    new_df, new_watermark = await _do_full_rebuild(
                        project_gid=project_gid,
                        entity_type=entity_type,
                        persistence=persistence,
                    )
                    full_rebuilds += 1

                    if new_df is not None and len(new_df) > 0:
                        try:
                            new_index = GidLookupIndex.from_dataframe(new_df)

                            # Persist new index (DataFrame saved by builder)
                            await persistence.save_index(project_gid, new_index)
                            watermark_repo.set_watermark(project_gid, new_watermark)

                            # Store in DataFrameCache singleton for @dataframe_cache decorator
                            # This ensures decorator finds cache hit instead of rebuilding
                            if dataframe_cache is not None:
                                await dataframe_cache.put_async(
                                    project_gid, entity_type, new_df, new_watermark
                                )
                                cache_puts += 1

                            loaded_count += 1
                            total_rows += len(new_df)

                            project_elapsed = (
                                time.perf_counter() - project_start
                            ) * 1000
                            logger.info(
                                "dataframe_preload_project_complete",
                                extra={
                                    "project_gid": project_gid,
                                    "entity_type": entity_type,
                                    "row_count": len(new_df),
                                    "index_entries": len(new_index),
                                    "strategy": "full_rebuild",
                                    "duration_ms": round(project_elapsed, 2),
                                },
                            )

                        except KeyError as e:
                            logger.warning(
                                "dataframe_preload_index_build_failed",
                                extra={
                                    "project_gid": project_gid,
                                    "error": str(e),
                                },
                            )
                    else:
                        logger.debug(
                            "dataframe_preload_no_data",
                            extra={"project_gid": project_gid},
                        )

            except Exception as e:
                # Graceful degradation - continue with other projects
                logger.warning(
                    "dataframe_preload_project_failed",
                    extra={
                        "project_gid": project_gid,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

    except Exception as e:
        # Graceful degradation - log and continue
        logger.error(
            "dataframe_preload_failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

    finally:
        # Always set cache ready at end (service can function without warm cache)
        set_cache_ready(True)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "dataframe_preload_complete",
            extra={
                "projects_loaded": loaded_count,
                "total_projects": total_projects,
                "total_rows": total_rows,
                "watermarks_loaded": watermarks_loaded,
                "indices_loaded_from_s3": indices_loaded_from_s3,
                "incremental_catchups": incremental_catchups,
                "full_rebuilds": full_rebuilds,
                "cache_puts": cache_puts,  # DataFrameCache singleton entries
                "duration_ms": round(elapsed_ms, 2),
                "cold_start_target_met": elapsed_ms < 5000,  # Target: <5s
            },
        )


async def _do_incremental_catchup(
    project_gid: str,
    entity_type: str,
    existing_df: "pl.DataFrame",
    existing_index: "GidLookupIndex",
    watermark: "datetime",
    persistence: "DataFramePersistence | None" = None,
) -> tuple["pl.DataFrame", "datetime", bool]:
    """Perform incremental catch-up for a project.

    Fetches only tasks modified since the watermark and merges them
    into the existing DataFrame.

    Args:
        project_gid: Asana project GID.
        entity_type: Entity type (e.g., "unit").
        existing_df: Persisted DataFrame.
        existing_index: Persisted GidLookupIndex.
        watermark: Last sync timestamp.
        persistence: Optional DataFramePersistence (legacy, unused).

    Returns:
        Tuple of (updated_df, new_watermark, was_incremental).
        was_incremental is True if we did incremental sync, False if we fell back.
    """
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
    from autom8_asana.dataframes.builders import ProgressiveProjectBuilder
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
    from autom8_asana.dataframes.section_persistence import SectionPersistence
    from autom8_asana.services.resolver import to_pascal_case

    # Get bot PAT for API access
    try:
        bot_pat = get_bot_pat()
    except BotPATError:
        logger.warning(
            "incremental_catchup_no_bot_pat",
            extra={"project_gid": project_gid},
        )
        # Return existing state unchanged
        return existing_df, watermark, False

    import os

    workspace_gid = os.environ.get("ASANA_WORKSPACE_GID")
    if not workspace_gid:
        logger.warning(
            "incremental_catchup_no_workspace",
            extra={"project_gid": project_gid},
        )
        return existing_df, watermark, False

    try:
        async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
            # Select schema based on entity type (falls back to BASE_SCHEMA)
            task_type = to_pascal_case(entity_type)  # "unit" -> "Unit"
            schema = SchemaRegistry.get_instance().get_schema(task_type)

            resolver = DefaultCustomFieldResolver()
            section_persistence = SectionPersistence()

            async with section_persistence:
                builder = ProgressiveProjectBuilder(
                    client=client,
                    project_gid=project_gid,
                    entity_type=entity_type,
                    schema=schema,
                    persistence=section_persistence,
                    resolver=resolver,
                    store=client.unified_store,
                )

                build_result = await builder.build_progressive_async(resume=True)
                updated_df = build_result.dataframe
                new_watermark = build_result.watermark

            # Check if DataFrame actually changed
            was_incremental = True
            if len(updated_df) == len(existing_df):
                # May be the same - compare row counts as heuristic
                logger.debug(
                    "incremental_catchup_completed",
                    extra={
                        "project_gid": project_gid,
                        "rows": len(updated_df),
                    },
                )

            return updated_df, new_watermark, was_incremental

    except Exception as e:
        logger.warning(
            "incremental_catchup_failed",
            extra={
                "project_gid": project_gid,
                "error": str(e),
                "error_type": type(e).__name__,
                "fallback": "return_existing",
            },
        )
        # Return existing state unchanged
        return existing_df, watermark, False


async def _do_full_rebuild(
    project_gid: str,
    entity_type: str,
    persistence: "DataFramePersistence | None" = None,
) -> tuple["pl.DataFrame | None", "datetime"]:
    """Perform full DataFrame rebuild for a project.

    Fetches all tasks from the project and builds a new DataFrame.

    Args:
        project_gid: Asana project GID.
        entity_type: Entity type (e.g., "unit").
        persistence: Optional DataFramePersistence (legacy, unused).

    Returns:
        Tuple of (new_df, new_watermark). new_df may be None on failure.
    """
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
    from autom8_asana.dataframes.builders import ProgressiveProjectBuilder
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
    from autom8_asana.dataframes.section_persistence import SectionPersistence
    from autom8_asana.services.resolver import to_pascal_case

    now = datetime.now(UTC)

    # Get bot PAT for API access
    try:
        bot_pat = get_bot_pat()
    except BotPATError:
        logger.warning(
            "full_rebuild_no_bot_pat",
            extra={"project_gid": project_gid},
        )
        return None, now

    import os

    workspace_gid = os.environ.get("ASANA_WORKSPACE_GID")
    if not workspace_gid:
        logger.warning(
            "full_rebuild_no_workspace",
            extra={"project_gid": project_gid},
        )
        return None, now

    try:
        async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
            # Select schema based on entity type (falls back to BASE_SCHEMA)
            task_type = to_pascal_case(entity_type)  # "unit" -> "Unit"
            schema = SchemaRegistry.get_instance().get_schema(task_type)

            resolver = DefaultCustomFieldResolver()
            section_persistence = SectionPersistence()

            async with section_persistence:
                builder = ProgressiveProjectBuilder(
                    client=client,
                    project_gid=project_gid,
                    entity_type=entity_type,
                    schema=schema,
                    persistence=section_persistence,
                    resolver=resolver,
                    store=client.unified_store,
                )

                # Full fetch with resume=False to force fresh build
                result = await builder.build_progressive_async(resume=False)

                return result.dataframe, result.watermark

    except Exception as e:
        logger.warning(
            "full_rebuild_failed",
            extra={
                "project_gid": project_gid,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return None, now
