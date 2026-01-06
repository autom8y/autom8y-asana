"""FastAPI application factory with lifespan management.

This module provides the main FastAPI application factory with:
- Lifespan context manager for startup/shutdown
- CORS middleware (configurable)
- Rate limiting middleware (SlowAPI)
- Request ID middleware for correlation
- Request logging middleware
- Route registration
- Exception handler registration
- Entity resolver startup discovery

Per TDD-ASANA-SATELLITE:
- FR-SVC-001: FastAPI application factory with lifespan
- FR-SVC-002: Request ID middleware
- FR-SVC-003: Request logging middleware
- FR-SVC-004: CORS middleware with configurable origins
- FR-SVC-005: Service-level rate limiting via SlowAPI

Per TDD-entity-resolver:
- Entity resolver discovers project GIDs at startup
- Fail-fast if discovery fails
- Store EntityProjectRegistry in app.state

Per ADR-ASANA-007:
- SDK client lifecycle is per-request (via dependencies)
- No persistent client state in app.state

Design Principles:
- Thin API layer that delegates to SDK
- Request tracing via X-Request-ID header
- Centralized error handling
- Structured JSON logging
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from autom8y_log import get_logger

if TYPE_CHECKING:
    import polars as pl

    from autom8_asana.dataframes.persistence import DataFramePersistence
    from autom8_asana.services.gid_lookup import GidLookupIndex

from .config import get_settings
from .errors import register_exception_handlers
from .middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    configure_structlog,
)
from .rate_limit import limiter
from .routes import (
    dataframes_router,
    health_router,
    internal_router,
    projects_router,
    resolver_router,
    sections_router,
    tasks_router,
    users_router,
    workspaces_router,
)


def _initialize_dataframe_cache() -> None:
    """Initialize the DataFrameCache singleton for resolution strategies.

    Per TDD-DATAFRAME-CACHE-001 Phase 2:
    - Initializes DataFrameCache with Memory + S3 tiering
    - Used by @dataframe_cache decorator on Offer/Contact strategies
    - Graceful degradation if S3 not configured (logs warning, cache disabled)

    This is called during application startup, after entity project discovery.
    """
    from autom8_asana.cache.dataframe.factory import initialize_dataframe_cache

    cache = initialize_dataframe_cache()

    if cache is not None:
        logger.info(
            "dataframe_cache_ready",
            extra={
                "status": "initialized",
                "entity_types": ["unit", "offer", "contact"],
            },
        )
    else:
        logger.warning(
            "dataframe_cache_disabled",
            extra={
                "reason": "S3 not configured",
                "impact": "Unit/Offer/Contact resolution will build DataFrames on every request",
            },
        )

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle.

    Per FR-SVC-001: Application factory with lifespan context manager.

    Startup:
    - Configure structured logging
    - Log startup event
    - Entity resolver discovery (FR-004, FR-005 per TDD-entity-resolver)
    - DataFrame cache preload from S3 (FR-003 per sprint-materialization-002)

    Shutdown:
    - Log shutdown event
    - Clean up resources (if any)

    Per ADR-ASANA-007: SDK client lifecycle is per-request,
    so no persistent client initialization needed here.

    Per ADR-0060: Entity resolver discovers project GIDs at startup.

    Per sprint-materialization-002 FR-003, FR-004:
    - Pre-warm DataFrame cache before accepting traffic
    - Health check returns 503 until cache is ready

    Args:
        app: FastAPI application instance.

    Yields:
        None (no persistent state stored on app.state for SDK).
    """
    # Startup
    configure_structlog()
    settings = get_settings()

    logger.info(
        "api_starting",
        extra={
            "service": "autom8_asana",
            "log_level": settings.log_level,
            "debug": settings.debug,
            "rate_limit_rpm": settings.rate_limit_rpm,
        },
    )

    # Entity resolver startup discovery (FR-004, FR-005)
    try:
        await _discover_entity_projects(app)
    except Exception as e:
        logger.error(
            "entity_resolver_discovery_failed",
            extra={
                "error": str(e),
                "remediation": (
                    "Ensure workspace contains projects with names: "
                    "Business Units. Check ASANA_BOT_PAT is configured."
                ),
            },
        )
        # Per ADR-0060: Fail-fast on discovery failure
        raise RuntimeError(f"Entity resolver discovery failed: {e}") from e

    # Initialize DataFrameCache for Offer/Contact resolution strategies
    # Per TDD-DATAFRAME-CACHE-001: Provides tiered caching (Memory + S3)
    _initialize_dataframe_cache()

    # DataFrame cache preload (FR-003 per sprint-materialization-002)
    # Runs after entity discovery so we know which projects exist
    # Per progressive cache warming architecture: use progressive preload with
    # parallel project processing, resume capability, and heartbeat monitoring
    await _preload_dataframe_cache_progressive(app)

    yield

    # Shutdown
    logger.info(
        "api_stopping",
        extra={"service": "autom8_asana"},
    )


def _normalize_project_name(name: str) -> str:
    """Normalize project name for entity type matching.

    Handles common patterns:
    - "Business Units" -> "unit"
    - "Business Offers" -> "offer"
    - "Contacts" -> "contact"
    - "Business" -> "business"

    Args:
        name: Raw project name from Asana.

    Returns:
        Normalized name (lowercase, no "business " prefix, singularized).
    """
    normalized = name.lower().strip()
    # Check for standalone "Business" before stripping prefix
    # (This handles the edge case where project name IS "Business")
    if normalized == "business":
        return "business"
    # Strip common prefix
    normalized = normalized.removeprefix("business ")
    # Simple singularization (handles: units->unit, offers->offer, contacts->contact)
    if normalized.endswith("es") and len(normalized) > 3:
        # businesses -> business (but not "es" alone)
        normalized = normalized[:-2]
    elif normalized.endswith("s") and len(normalized) > 2:
        normalized = normalized[:-1]
    return normalized


def _match_entity_type(project_name: str, entity_types: list[str]) -> str | None:
    """Match a project name to an entity type.

    Args:
        project_name: Raw project name from Asana.
        entity_types: List of known entity types to match against.

    Returns:
        Matched entity type or None if no match.
    """
    normalized = _normalize_project_name(project_name)
    if normalized in entity_types:
        return normalized
    return None


async def _discover_entity_projects(app: FastAPI) -> None:
    """Discover and register entity type project mappings.

    Per TDD-entity-resolver: Startup discovery populates EntityProjectRegistry.
    Per ADR-0060: Uses WorkspaceProjectRegistry for discovery.

    Discovery flow:
    1. Get bot PAT for Asana API access
    2. Use WorkspaceProjectRegistry to discover workspace projects
    3. Match project names to entity types via pattern matching
    4. Register matches in EntityProjectRegistry
    5. Store registry in app.state for request access

    Args:
        app: FastAPI application instance

    Raises:
        Exception: If discovery fails (fail-fast per ADR-0060)
    """
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
    from autom8_asana.models.business.registry import get_workspace_registry
    from autom8_asana.services.resolver import EntityProjectRegistry

    # Get bot PAT for S2S Asana access
    try:
        bot_pat = get_bot_pat()
    except BotPATError as e:
        logger.warning(
            "entity_resolver_no_bot_pat",
            extra={
                "error": str(e),
                "detail": "Entity resolver will not be available without bot PAT",
            },
        )
        # Create empty registry - endpoint will return 503
        entity_registry = EntityProjectRegistry.get_instance()
        app.state.entity_project_registry = entity_registry
        return

    # Get workspace GID from environment
    import os

    workspace_gid = os.environ.get("ASANA_WORKSPACE_GID")

    if not workspace_gid:
        logger.warning(
            "entity_resolver_no_workspace",
            extra={
                "detail": "ASANA_WORKSPACE_GID not set, entity resolver discovery skipped",
            },
        )
        entity_registry = EntityProjectRegistry.get_instance()
        app.state.entity_project_registry = entity_registry
        return

    async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
        # Use existing WorkspaceProjectRegistry discovery
        workspace_registry = get_workspace_registry()
        await workspace_registry.discover_async(client)

        # Map discovered projects to entity resolver registry
        entity_registry = EntityProjectRegistry.get_instance()

        # Known entity types to discover
        ENTITY_TYPES: list[str] = ["unit", "business", "offer", "contact"]

        # Match projects to entity types via normalized name matching
        # Handles: "Business Units" -> unit, "Offers" -> offer, etc.
        for project_name, project_gid in workspace_registry.get_all_projects().items():
            entity_type = _match_entity_type(project_name, ENTITY_TYPES)
            if entity_type:
                entity_registry.register(
                    entity_type=entity_type,
                    project_gid=project_gid,
                    project_name=project_name,
                )
                logger.info(
                    "entity_project_registered",
                    extra={
                        "entity_type": entity_type,
                        "project_gid": project_gid,
                        "project_name": project_name,
                    },
                )

        # Log any entity types not found
        registered = set(entity_registry.get_all_entity_types())
        for entity_type in ENTITY_TYPES:
            if entity_type not in registered:
                logger.warning(
                    "entity_project_not_found",
                    extra={"entity_type": entity_type},
                )

        # Store registry in app.state for request access
        app.state.entity_project_registry = entity_registry

        logger.info(
            "entity_resolver_discovery_complete",
            extra={
                "registered_types": entity_registry.get_all_entity_types(),
                "is_ready": entity_registry.is_ready(),
            },
        )


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
        entity_registry: EntityProjectRegistry = getattr(
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
                    updated_df, new_watermark, was_incremental = (
                        await _do_incremental_catchup(
                            project_gid=project_gid,
                            entity_type=entity_type,
                            existing_df=df,
                            existing_index=index,
                            watermark=watermark,
                            persistence=persistence,
                        )
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

                            project_elapsed = (time.perf_counter() - project_start) * 1000
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

    Returns:
        Tuple of (updated_df, new_watermark, was_incremental).
        was_incremental is True if we did incremental sync, False if we fell back.
    """
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
    from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver

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

    # Minimal project proxy for builder
    class ProjectProxy:
        def __init__(self, gid: str) -> None:
            self.gid = gid
            self.tasks: list = []

    try:
        async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
            # Select schema based on entity type (falls back to BASE_SCHEMA)
            task_type = entity_type.title()  # "unit" -> "Unit"
            schema = SchemaRegistry.get_instance().get_schema(task_type)

            resolver = DefaultCustomFieldResolver()
            project_proxy = ProjectProxy(project_gid)

            builder = ProjectDataFrameBuilder(
                project=project_proxy,
                task_type=task_type,
                schema=schema,
                resolver=resolver,
                client=client,
                unified_store=client.unified_store,
                persistence=persistence,
            )

            # Use incremental refresh
            updated_df, new_watermark = await builder.refresh_incremental(
                client=client,
                existing_df=existing_df,
                watermark=watermark,
            )

            # Check if DataFrame actually changed
            was_incremental = True
            if updated_df is existing_df:
                # No changes detected
                logger.debug(
                    "incremental_catchup_no_changes",
                    extra={"project_gid": project_gid},
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

    Returns:
        Tuple of (new_df, new_watermark). new_df may be None on failure.
    """
    from datetime import timezone

    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
    from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver

    now = datetime.now(timezone.utc)

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

    # Minimal project proxy for builder
    class ProjectProxy:
        def __init__(self, gid: str) -> None:
            self.gid = gid
            self.tasks: list = []

    try:
        async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
            # Select schema based on entity type (falls back to BASE_SCHEMA)
            task_type = entity_type.title()  # "unit" -> "Unit"
            schema = SchemaRegistry.get_instance().get_schema(task_type)

            resolver = DefaultCustomFieldResolver()
            project_proxy = ProjectProxy(project_gid)

            builder = ProjectDataFrameBuilder(
                project=project_proxy,
                task_type=task_type,
                schema=schema,
                resolver=resolver,
                client=client,
                unified_store=client.unified_store,
                persistence=persistence,
            )

            # Full fetch
            df = await builder.build_with_parallel_fetch_async(client)

            return df, datetime.now(timezone.utc)

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


# ========== Progressive Preload with Parallel Projects ==========

# Concurrency limit for parallel project processing
# Per progressive cache warming architecture: 3 concurrent projects
PROJECT_CONCURRENCY = 3

# Heartbeat interval for preload monitoring
HEARTBEAT_INTERVAL_SECONDS = 30


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
    from autom8_asana.dataframes.builders.progressive import ProgressiveProjectBuilder
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
    from autom8_asana.dataframes.section_persistence import SectionPersistence
    from autom8_asana.dataframes.watermark import get_watermark_repo
    from autom8_asana.services.gid_lookup import GidLookupIndex
    from autom8_asana.services.resolver import EntityProjectRegistry

    start_time = time.perf_counter()
    loaded_count = 0
    total_projects = 0
    total_rows = 0
    sections_fetched_total = 0
    sections_resumed_total = 0
    projects_in_progress: set[str] = set()
    projects_completed: set[str] = set()

    # Heartbeat state
    heartbeat_task: asyncio.Task | None = None

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
        entity_registry: EntityProjectRegistry = getattr(
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
        registered_types = entity_registry.get_all_entity_types()
        project_configs: list[tuple[str, str]] = []  # (project_gid, entity_type)
        for entity_type in registered_types:
            config = entity_registry.get_config(entity_type)
            if config and config.project_gid:
                project_configs.append((config.project_gid, entity_type))

        total_projects = len(project_configs)

        if not project_configs:
            logger.info(
                "progressive_preload_skipped",
                extra={"reason": "no_registered_projects"},
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

        # Initialize section persistence
        persistence = SectionPersistence()

        if not persistence.is_available:
            logger.warning(
                "progressive_preload_s3_unavailable",
                extra={
                    "detail": "S3 not available, falling back to legacy preload",
                },
            )
            # Fall back to existing preload
            await _preload_dataframe_cache(app)
            return

        # Get watermark repository and DataFrameCache singleton
        watermark_repo = get_watermark_repo()
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
                            task_type = entity_type.title()
                            schema = SchemaRegistry.get_instance().get_schema(task_type)
                            resolver = DefaultCustomFieldResolver()

                            builder = ProgressiveProjectBuilder(
                                client=client,
                                project_gid=project_gid,
                                entity_type=entity_type,
                                schema=schema,
                                persistence=persistence,
                                resolver=resolver,
                                store=client.unified_store,
                            )

                            result = await builder.build_progressive_async(resume=True)

                            # Update totals
                            sections_fetched_total += result.sections_fetched
                            sections_resumed_total += result.sections_resumed

                            if result.total_rows > 0:
                                # Store in watermark repo
                                watermark_repo.set_watermark(
                                    project_gid, result.watermark
                                )

                                # Store in DataFrameCache singleton
                                if dataframe_cache is not None:
                                    await dataframe_cache.put_async(
                                        project_gid,
                                        entity_type,
                                        result.df,
                                        result.watermark,
                                    )

                            return True

                except Exception as e:
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

        # Launch all projects with bounded concurrency
        results = await asyncio.gather(
            *[
                process_project(project_gid, entity_type)
                for project_gid, entity_type in project_configs
            ],
            return_exceptions=True,
        )

        # Count successes
        for result in results:
            if isinstance(result, bool) and result:
                loaded_count += 1

    except Exception as e:
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


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application with:
        - Lifespan context manager
        - CORS middleware (if configured)
        - Rate limiting middleware
        - Request ID middleware
        - Request logging middleware
        - Health route
        - Exception handlers

    Per TDD-ASANA-SATELLITE:
    - Middleware stack order matters for proper execution
    - Exception handlers map SDK errors to HTTP responses
    """
    settings = get_settings()

    app = FastAPI(
        title="autom8_asana API",
        description="REST API for Asana integration via autom8_asana SDK",
        version="0.1.0",
        lifespan=lifespan,
        # Disable automatic docs in production
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # --- Middleware Stack ---
    # Starlette executes middleware in reverse order of addition.
    # Outer to inner execution order:
    # 1. CORSMiddleware - handle preflight (outermost)
    # 2. SlowAPIMiddleware - rate limiting
    # 3. RequestLoggingMiddleware - log all requests
    # 4. RequestIDMiddleware - set request_id (innermost)

    # CORS (if configured) - MUST be outermost to handle preflight OPTIONS
    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )
        logger.info(
            "cors_enabled",
            extra={"allowed_origins": settings.cors_origins_list},
        )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Request logging (before RequestID so it has access to request_id)
    app.add_middleware(RequestLoggingMiddleware)

    # Request ID (innermost - runs first, sets request_id for others)
    app.add_middleware(RequestIDMiddleware)

    # --- Routes ---
    app.include_router(health_router)
    app.include_router(users_router)
    app.include_router(workspaces_router)
    app.include_router(dataframes_router)
    app.include_router(tasks_router)
    app.include_router(projects_router)
    app.include_router(sections_router)
    app.include_router(internal_router)
    app.include_router(resolver_router)

    # --- Exception Handlers ---
    register_exception_handlers(app)

    return app


# Allow running directly with uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "autom8_asana.api.main:create_app",
        host="0.0.0.0",
        port=8000,
        factory=True,
        reload=True,
    )
