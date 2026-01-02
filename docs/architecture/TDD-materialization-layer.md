# TDD: DataFrame Materialization Layer

## Overview

This design eliminates DataFrame cold-start latency and inefficient full-rebuild patterns by implementing a centralized WatermarkRepository with `modified_since` incremental sync. The architecture transforms request-time data construction (3-300 seconds) into startup-time preloading with sub-second incremental refreshes.

## Metadata

| Field | Value |
|-------|-------|
| Artifact ID | TDD-materialization-layer |
| Status | Draft |
| Author | Architect |
| Created | 2026-01-01 |
| Sprint | sprint-materialization-001 |
| PRD | docs/requirements/PRD-materialization-layer.md |
| Complexity | Medium-High |

---

## Context

### Input PRD

The PRD (`docs/requirements/PRD-materialization-layer.md`) defines 6 Must Have requirements (FR-001 to FR-006) targeting:

1. Centralized watermark tracking for incremental sync
2. `modified_since` parameter usage for efficient API calls
3. Startup preloading to eliminate cold-start latency
4. Health check enhancement for "warming" state
5. Resolver integration with incremental refresh
6. Delta merge logic for DataFrame updates

### Existing System Context

The infrastructure for this solution is 80% complete:

| Component | Location | Status |
|-----------|----------|--------|
| `_gid_index_cache` | `services/resolver.py:59` | Module-level dict cache |
| `GidLookupIndex` | `services/gid_lookup.py` | O(1) lookup with `is_stale(ttl)` |
| `ProjectDataFrameBuilder` | `dataframes/builders/project.py` | Parallel fetch implemented |
| `modified_since` parameter | `clients/tasks.py:582` | Exists but UNUSED |
| `modified_at` in opt_fields | `dataframes/builders/project.py:39` | Already fetched |
| `EntityProjectRegistry` | `services/resolver.py` | Singleton pattern |
| Lifespan startup | `api/main.py:69-133` | Discovery only |
| Health check | `api/routes/health.py` | Standard liveness |

### Constraints

- **In-memory only**: No Redis or external cache for Phase 1
- **S3 persistence deferred**: Phase 2 if restart frequency increases
- **Backward compatible**: Existing consumers unaffected
- **60-second startup budget**: Must fit within ECS health check timeout
- **Singleton consistency**: Match existing registry patterns

---

## System Design

### Architecture Diagram

```
                          Container Startup
                                 |
                                 v
                    +------------------------+
                    |    Lifespan Manager    |
                    |  (api/main.py:69-133)  |
                    +------------------------+
                                 |
          +----------------------+----------------------+
          |                      |                      |
          v                      v                      v
+------------------+  +--------------------+  +------------------+
| _discover_entity |  | _preload_dataframe |  | Set cache_ready  |
|     projects()   |  |      _cache()      |  |     = True       |
| [existing]       |  |     [NEW]          |  |    [NEW]         |
+------------------+  +--------------------+  +------------------+
                                 |
                                 v
                    +------------------------+
                    |  WatermarkRepository   |
                    |    (singleton)         |
                    +------------------------+
                    | - watermarks: dict     |
                    | - lock: threading.Lock |
                    +------------------------+
                                 |
                    +------------+------------+
                    |                         |
                    v                         v
          +------------------+      +------------------+
          |  Health Check    |      |  Resolver Cache  |
          |  /health         |      | _gid_index_cache |
          +------------------+      +------------------+
          | cache_ready?     |      | project_gid ->   |
          | 503 : 200        |      | GidLookupIndex   |
          +------------------+      +------------------+


                        Hourly Refresh Flow
                               |
                               v
                    +------------------------+
                    |   TTL Expiry Check     |
                    | index.is_stale(3600)   |
                    +------------------------+
                               |
                               v
                    +------------------------+
                    | WatermarkRepository    |
                    |   .get_watermark()     |
                    +------------------------+
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
    watermark is None                    watermark exists
    (first fetch)                        (incremental)
            |                                     |
            v                                     v
    +----------------+                  +--------------------+
    | Full Fetch     |                  | Incremental Fetch  |
    | tasks.list()   |                  | modified_since=wm  |
    +----------------+                  +--------------------+
            |                                     |
            +------------------+------------------+
                               |
                               v
                    +------------------------+
                    |   Delta Merge Logic    |
                    | _merge_deltas(df, new) |
                    +------------------------+
                               |
                               v
                    +------------------------+
                    |  Update Watermark      |
                    |  .set_watermark(now)   |
                    +------------------------+
```

### Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `WatermarkRepository` | Centralized per-project timestamp tracking | `dataframes/watermark.py` |
| `refresh_incremental()` | Fetch delta via `modified_since`, merge into DataFrame | `dataframes/builders/project.py` |
| `_preload_dataframe_cache()` | Warm cache at startup for all entity types | `api/main.py` |
| `_merge_deltas()` | Merge changed tasks into existing DataFrame | `dataframes/builders/project.py` |
| Health check enhancement | Return 503 until cache ready | `api/routes/health.py` |

---

## Component Specifications

### FR-001: WatermarkRepository

**Location**: `src/autom8_asana/dataframes/watermark.py`

```python
"""Watermark repository for incremental sync tracking.

Per TDD-materialization-layer FR-001:
Centralized timestamp tracking for per-project modified_since sync.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import ClassVar

__all__ = ["WatermarkRepository", "get_watermark_repo"]


class WatermarkRepository:
    """Thread-safe singleton for per-project watermark tracking.

    Per FR-001: Tracks last successful sync timestamp per project.
    Used by incremental refresh to fetch only changed tasks.

    Thread safety: Uses threading.Lock for concurrent access.
    Singleton pattern: Consistent with EntityProjectRegistry.

    Attributes:
        _watermarks: Dict mapping project_gid to last sync datetime.
        _lock: Threading lock for thread-safe access.

    Example:
        >>> repo = WatermarkRepository.get_instance()
        >>> repo.set_watermark("123456", datetime.now(timezone.utc))
        >>> wm = repo.get_watermark("123456")
        >>> if wm is None:
        ...     # First sync - do full fetch
        ...     pass
    """

    _instance: ClassVar[WatermarkRepository | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls) -> WatermarkRepository:
        """Get or create singleton instance (thread-safe)."""
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._watermarks = {}
                instance._instance_lock = threading.Lock()
                cls._instance = instance
            return cls._instance

    @classmethod
    def get_instance(cls) -> WatermarkRepository:
        """Get singleton instance."""
        return cls()

    def get_watermark(self, project_gid: str) -> datetime | None:
        """Get last sync timestamp for project.

        Args:
            project_gid: Asana project GID.

        Returns:
            UTC datetime of last successful sync, or None if never synced.
        """
        with self._instance_lock:
            return self._watermarks.get(project_gid)

    def set_watermark(self, project_gid: str, timestamp: datetime) -> None:
        """Update watermark after successful sync.

        Args:
            project_gid: Asana project GID.
            timestamp: UTC datetime of successful sync completion.

        Raises:
            ValueError: If timestamp is not timezone-aware.
        """
        if timestamp.tzinfo is None:
            raise ValueError("Watermark timestamp must be timezone-aware")

        with self._instance_lock:
            self._watermarks[project_gid] = timestamp

    def get_all_watermarks(self) -> dict[str, datetime]:
        """Get all watermarks for observability.

        Returns:
            Copy of watermarks dict (project_gid -> datetime).
        """
        with self._instance_lock:
            return dict(self._watermarks)

    def clear_watermark(self, project_gid: str) -> None:
        """Clear watermark for project (forces full rebuild).

        Args:
            project_gid: Asana project GID.
        """
        with self._instance_lock:
            self._watermarks.pop(project_gid, None)

    @classmethod
    def reset(cls) -> None:
        """Reset singleton for testing."""
        with cls._lock:
            cls._instance = None


def get_watermark_repo() -> WatermarkRepository:
    """Module-level accessor for WatermarkRepository singleton.

    Returns:
        WatermarkRepository singleton instance.
    """
    return WatermarkRepository.get_instance()
```

**Design Decisions**:

1. **Thread-safe singleton**: Uses `threading.Lock` for both class-level singleton creation and instance-level watermark access
2. **Timezone-aware enforcement**: Rejects naive datetimes to prevent clock skew issues
3. **Consistent with existing patterns**: Matches `EntityProjectRegistry` singleton design
4. **Observable**: `get_all_watermarks()` enables metrics/debugging

---

### FR-002: Incremental DataFrame Refresh

**Location**: `src/autom8_asana/dataframes/builders/project.py`

Add method to `ProjectDataFrameBuilder`:

```python
async def refresh_incremental(
    self,
    client: AsanaClient,
    existing_df: pl.DataFrame | None,
    watermark: datetime | None,
) -> tuple[pl.DataFrame, datetime]:
    """Fetch only tasks modified since watermark and merge.

    Per FR-002: Uses modified_since parameter for efficient API calls.
    Per FR-006: Merges changed tasks into existing DataFrame.

    Behavior:
    - watermark is None: Full fetch (first sync)
    - watermark provided: Incremental fetch with modified_since
    - existing_df is None with watermark: Treated as first sync

    Args:
        client: AsanaClient for API calls.
        existing_df: Current DataFrame to merge into (None for first sync).
        watermark: Last sync timestamp (None for full fetch).

    Returns:
        Tuple of (merged DataFrame, new watermark for next refresh).

    Raises:
        No exceptions - falls back to full fetch on API errors.

    Example:
        >>> df, new_wm = await builder.refresh_incremental(client, old_df, wm)
        >>> watermark_repo.set_watermark(project_gid, new_wm)
    """
    import time
    from datetime import timezone

    project_gid = self._get_project_gid()
    if not project_gid:
        return self._build_empty(), datetime.now(timezone.utc)

    start_time = time.perf_counter()
    sync_start = datetime.now(timezone.utc)

    # Determine fetch strategy
    is_incremental = watermark is not None and existing_df is not None

    if is_incremental:
        # FR-002: Incremental fetch using modified_since
        try:
            modified_tasks = await self._fetch_modified_tasks(
                client, project_gid, watermark
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "incremental_fetch_completed",
                extra={
                    "project_gid": project_gid,
                    "modified_count": len(modified_tasks),
                    "watermark": watermark.isoformat(),
                    "duration_ms": round(elapsed_ms, 2),
                },
            )

            if not modified_tasks:
                # No changes - return existing DataFrame with updated watermark
                return existing_df, sync_start

            # FR-006: Merge deltas into existing DataFrame
            merged_df = self._merge_deltas(existing_df, modified_tasks)
            return merged_df, sync_start

        except Exception as e:
            # Fallback to full fetch on any error
            logger.warning(
                "incremental_fetch_fallback",
                extra={
                    "project_gid": project_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "fallback": "full_fetch",
                },
            )
            # Fall through to full fetch

    # Full fetch (first sync or fallback)
    df = await self.build_with_parallel_fetch_async(client)

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "full_fetch_completed",
        extra={
            "project_gid": project_gid,
            "task_count": len(df),
            "reason": "first_sync" if watermark is None else "fallback",
            "duration_ms": round(elapsed_ms, 2),
        },
    )

    return df, sync_start


async def _fetch_modified_tasks(
    self,
    client: AsanaClient,
    project_gid: str,
    watermark: datetime,
) -> list[Task]:
    """Fetch tasks modified since watermark.

    Args:
        client: AsanaClient for API calls.
        project_gid: Target project GID.
        watermark: Timestamp for modified_since filter.

    Returns:
        List of modified Task objects.
    """
    # Edge case: Watermark in future (clock skew)
    if watermark > datetime.now(timezone.utc):
        logger.warning(
            "watermark_future_detected",
            extra={
                "project_gid": project_gid,
                "watermark": watermark.isoformat(),
                "action": "full_rebuild",
            },
        )
        raise ValueError("Watermark in future - triggering full rebuild")

    # Use existing list_async with modified_since parameter
    tasks: list[Task] = await client.tasks.list_async(
        project=project_gid,
        modified_since=watermark.isoformat(),
        opt_fields=_BASE_OPT_FIELDS,
    ).collect()

    return tasks
```

---

### FR-006: Delta Merge Logic

**Location**: `src/autom8_asana/dataframes/builders/project.py`

Add method to `ProjectDataFrameBuilder`:

```python
def _merge_deltas(
    self,
    existing_df: pl.DataFrame,
    changed_tasks: list[Task],
) -> pl.DataFrame:
    """Merge changed tasks into existing DataFrame.

    Per FR-006: Delta merge strategy:
    1. Extract rows from changed tasks
    2. Remove existing rows with matching GIDs
    3. Append new/updated rows
    4. Return merged DataFrame

    Edge cases handled:
    - Task created: New GID appended to DataFrame
    - Task updated: Existing row replaced with new data
    - Task deleted: NOT detected by modified_since (acceptable staleness)

    Args:
        existing_df: Current DataFrame with existing task data.
        changed_tasks: List of modified Task objects from API.

    Returns:
        Merged DataFrame with updated task data.

    Note:
        Preserves schema and column order from existing DataFrame.
    """
    if not changed_tasks:
        return existing_df

    # Extract rows from changed tasks using existing extractor
    changed_rows: list[dict[str, Any]] = []
    for task in changed_tasks:
        row = self._extract_row(task)
        changed_rows.append(row)

    # Create DataFrame from changed tasks
    changed_df = pl.DataFrame(
        changed_rows,
        schema=self._schema.to_polars_schema(),
    )

    # Get GIDs to remove from existing
    changed_gids = set(changed_df["gid"].to_list())

    # Remove existing rows that will be replaced
    filtered_df = existing_df.filter(~existing_df["gid"].is_in(list(changed_gids)))

    # Concatenate: existing (minus changed) + changed
    merged_df = pl.concat([filtered_df, changed_df], how="vertical")

    logger.debug(
        "delta_merge_completed",
        extra={
            "existing_count": len(existing_df),
            "changed_count": len(changed_tasks),
            "merged_count": len(merged_df),
            "net_change": len(merged_df) - len(existing_df),
        },
    )

    return merged_df
```

---

### FR-003: Startup Preloading

**Location**: `src/autom8_asana/api/main.py`

Add to lifespan function after `_discover_entity_projects()`:

```python
async def _preload_dataframe_cache(app: FastAPI) -> None:
    """Pre-build GidLookupIndex for all registered entity types.

    Per FR-003: Warm cache at startup before accepting traffic.
    Per FR-008: Preload entity types in parallel for faster startup.

    This function:
    1. Gets all registered entity types from EntityProjectRegistry
    2. Builds GidLookupIndex for each in parallel
    3. Populates _gid_index_cache and WatermarkRepository
    4. Logs progress for observability

    Args:
        app: FastAPI application instance.

    Raises:
        RuntimeError: If critical entity types fail to preload.
    """
    import asyncio
    import time

    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import get_bot_pat
    from autom8_asana.dataframes.watermark import get_watermark_repo
    from autom8_asana.services.resolver import (
        EntityProjectRegistry,
        UnitResolutionStrategy,
        _gid_index_cache,
    )

    registry: EntityProjectRegistry = app.state.entity_project_registry
    watermark_repo = get_watermark_repo()

    if not registry.is_ready():
        logger.warning(
            "cache_preload_skipped",
            extra={"reason": "entity_registry_not_ready"},
        )
        return

    entity_types = registry.get_all_entity_types()
    if not entity_types:
        logger.info(
            "cache_preload_skipped",
            extra={"reason": "no_entity_types_registered"},
        )
        return

    start_time = time.perf_counter()
    logger.info(
        "cache_warming_started",
        extra={
            "entity_types": entity_types,
            "project_count": len(entity_types),
        },
    )

    # Get bot PAT for Asana API access
    bot_pat = get_bot_pat()
    workspace_gid = os.environ.get("ASANA_WORKSPACE_GID", "")

    async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
        # FR-008: Parallel preloading
        async def preload_entity(entity_type: str) -> tuple[str, int, float]:
            """Preload single entity type, return (type, count, duration_ms)."""
            entity_start = time.perf_counter()
            project_gid = registry.get_project_gid(entity_type)

            if not project_gid:
                logger.warning(
                    "cache_warming_entity_skipped",
                    extra={
                        "entity_type": entity_type,
                        "reason": "no_project_gid",
                    },
                )
                return entity_type, 0, 0.0

            try:
                # Use UnitResolutionStrategy's _get_or_build_index
                # This triggers full DataFrame build and index creation
                strategy = UnitResolutionStrategy()
                index = await strategy._get_or_build_index(project_gid, client)

                # Set initial watermark
                watermark_repo.set_watermark(
                    project_gid, datetime.now(timezone.utc)
                )

                duration_ms = (time.perf_counter() - entity_start) * 1000
                task_count = len(index) if index else 0

                logger.info(
                    "cache_warming_entity_complete",
                    extra={
                        "entity_type": entity_type,
                        "project_gid": project_gid,
                        "task_count": task_count,
                        "duration_ms": round(duration_ms, 2),
                    },
                )

                return entity_type, task_count, duration_ms

            except Exception as e:
                duration_ms = (time.perf_counter() - entity_start) * 1000
                logger.error(
                    "cache_warming_entity_failed",
                    extra={
                        "entity_type": entity_type,
                        "project_gid": project_gid,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "duration_ms": round(duration_ms, 2),
                    },
                )
                return entity_type, 0, duration_ms

        # Execute preloads in parallel
        results = await asyncio.gather(
            *[preload_entity(et) for et in entity_types],
            return_exceptions=True,
        )

        # Summarize results
        total_tasks = 0
        failed_types: list[str] = []

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Preload exception: {result}")
            else:
                entity_type, count, _ = result
                total_tasks += count
                if count == 0:
                    failed_types.append(entity_type)

        total_duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "cache_warming_complete",
            extra={
                "total_duration_ms": round(total_duration_ms, 2),
                "entity_count": len(entity_types),
                "task_count": total_tasks,
                "failed_types": failed_types,
            },
        )
```

**Lifespan Integration**:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle."""
    # ... existing startup code ...

    # Entity resolver startup discovery (FR-004, FR-005)
    try:
        await _discover_entity_projects(app)
    except Exception as e:
        # ... existing error handling ...
        raise RuntimeError(f"Entity resolver discovery failed: {e}") from e

    # FR-003: Preload DataFrame cache
    try:
        await _preload_dataframe_cache(app)
    except Exception as e:
        logger.error(
            "cache_preload_failed",
            extra={"error": str(e)},
        )
        # Non-fatal: service can still work with lazy loading

    # FR-004: Mark cache ready for health check
    app.state.cache_ready = True

    yield

    # Shutdown
    logger.info("api_stopping", extra={"service": "autom8_asana"})
```

---

### FR-004: Health Check Enhancement

**Location**: `src/autom8_asana/api/routes/health.py`

Modify `health_check()` function:

```python
@router.get("/health")
async def health_check(request: Request) -> JSONResponse:
    """Liveness probe with cache warming awareness.

    Per FR-004: Returns 503 until cache warming is complete.
    Per US-001, US-005: Prevents traffic routing during startup.

    Returns:
        - 503 with {"status": "warming"} during cache warm-up
        - 200 with {"status": "healthy"} when ready
    """
    # Check cache readiness (set by lifespan after preload)
    cache_ready = getattr(request.app.state, "cache_ready", False)

    if not cache_ready:
        return JSONResponse(
            content={
                "status": "warming",
                "version": API_VERSION,
                "message": "Cache warming in progress",
            },
            status_code=503,
        )

    return JSONResponse(
        content={"status": "healthy", "version": API_VERSION},
        status_code=200,
    )


@router.get("/health/detailed")
async def detailed_health_check(request: Request) -> JSONResponse:
    """Detailed health check with cache status.

    Per FR-010: Reports warming progress for observability.

    Returns:
        JSON with cache status, watermarks, and entity counts.
    """
    from autom8_asana.dataframes.watermark import get_watermark_repo
    from autom8_asana.services.resolver import (
        EntityProjectRegistry,
        _gid_index_cache,
    )

    cache_ready = getattr(request.app.state, "cache_ready", False)
    registry = getattr(request.app.state, "entity_project_registry", None)
    watermark_repo = get_watermark_repo()

    # Build cache status
    cache_status: dict[str, Any] = {}
    if registry and registry.is_ready():
        for entity_type in registry.get_all_entity_types():
            project_gid = registry.get_project_gid(entity_type)
            if project_gid:
                index = _gid_index_cache.get(project_gid)
                watermark = watermark_repo.get_watermark(project_gid)
                cache_status[entity_type] = {
                    "project_gid": project_gid,
                    "cached": index is not None,
                    "task_count": len(index) if index else 0,
                    "watermark": watermark.isoformat() if watermark else None,
                    "stale": index.is_stale(3600) if index else True,
                }

    status = "healthy" if cache_ready else "warming"
    http_status = 200 if cache_ready else 503

    return JSONResponse(
        content={
            "status": status,
            "version": API_VERSION,
            "cache_ready": cache_ready,
            "entity_cache": cache_status,
        },
        status_code=http_status,
    )
```

---

### FR-005: Resolver Integration

**Location**: `src/autom8_asana/services/resolver.py`

Modify `UnitResolutionStrategy._get_or_build_index()`:

```python
async def _get_or_build_index(
    self,
    project_gid: str,
    client: "AsanaClient",
) -> GidLookupIndex | None:
    """Get cached GidLookupIndex or build with incremental refresh.

    Per FR-005: Uses incremental sync instead of full rebuild on TTL expiry.
    Per TDD: TTL-based caching with 1-hour staleness check.

    Flow:
    1. Check cache for non-stale index -> return immediately
    2. Get watermark from WatermarkRepository
    3. If watermark exists: incremental refresh
    4. If no watermark: full fetch
    5. Update cache and watermark
    6. Return new index

    Args:
        project_gid: Unit project GID
        client: AsanaClient for DataFrame building

    Returns:
        GidLookupIndex if available, None on build failure.
    """
    global _gid_index_cache

    from autom8_asana.dataframes.watermark import get_watermark_repo

    watermark_repo = get_watermark_repo()

    # Check for cached index
    cached_index = _gid_index_cache.get(project_gid)

    if cached_index is not None and not cached_index.is_stale(_INDEX_TTL_SECONDS):
        logger.debug(
            "gid_index_cache_hit",
            extra={
                "project_gid": project_gid,
                "index_size": len(cached_index),
                "age_seconds": (
                    datetime.now(timezone.utc) - cached_index.created_at
                ).total_seconds(),
            },
        )
        return cached_index

    # Cache miss or stale - use incremental refresh
    cache_status = "stale" if cached_index is not None else "miss"
    watermark = watermark_repo.get_watermark(project_gid)

    logger.info(
        "gid_index_cache_rebuild",
        extra={
            "project_gid": project_gid,
            "reason": cache_status,
            "has_watermark": watermark is not None,
            "strategy": "incremental" if watermark else "full",
        },
    )

    # Get existing DataFrame if we have a cached index
    existing_df = None
    if cached_index is not None and watermark is not None:
        # Reconstruct DataFrame from cache or re-fetch
        # For Phase 1: We need to store DataFrame alongside index
        # Simplified: always rebuild DataFrame on stale
        pass

    # Build or refresh DataFrame
    try:
        # Import here to avoid circular imports
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
        from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
        from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA

        class ProjectProxy:
            def __init__(self, gid: str) -> None:
                self.gid = gid
                self.tasks: list[Any] = []

        project_proxy = ProjectProxy(project_gid)
        resolver = DefaultCustomFieldResolver()

        builder = ProjectDataFrameBuilder(
            project=project_proxy,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=resolver,
        )

        # Use incremental refresh
        df, new_watermark = await builder.refresh_incremental(
            client=client,
            existing_df=existing_df,
            watermark=watermark,
        )

        if df is None or len(df) == 0:
            logger.warning(
                "gid_index_build_empty_dataframe",
                extra={"project_gid": project_gid},
            )
            # Still update watermark to prevent immediate retry
            watermark_repo.set_watermark(project_gid, new_watermark)
            return None

        # Build index from DataFrame
        index = GidLookupIndex.from_dataframe(df)

        # Update cache and watermark
        _gid_index_cache[project_gid] = index
        watermark_repo.set_watermark(project_gid, new_watermark)

        logger.info(
            "gid_index_built",
            extra={
                "project_gid": project_gid,
                "index_size": len(index),
                "watermark": new_watermark.isoformat(),
            },
        )

        return index

    except KeyError as e:
        logger.error(
            "gid_index_build_failed_missing_columns",
            extra={
                "project_gid": project_gid,
                "error": str(e),
            },
        )
        return None
    except Exception as e:
        logger.error(
            "gid_index_build_failed",
            extra={
                "project_gid": project_gid,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return None
```

---

## Sequence Diagrams

### Startup Preload Flow

```
Container Start
      |
      v
+------------------+
|   FastAPI App    |
|    lifespan()    |
+--------+---------+
         |
         v
+-------------------+
| configure_structlog|
| log: api_starting |
+--------+----------+
         |
         v
+------------------------+
| _discover_entity_      |
| projects(app)          |
| [existing]             |
+--------+---------------+
         |
         v
+------------------------+
| _preload_dataframe_    |
| cache(app)     [NEW]   |
+--------+---------------+
         |
         | For each entity_type in parallel:
         +----------------------------------------+
         |                                        |
         v                                        v
+------------------+                    +------------------+
| preload_entity() |                    | preload_entity() |
| entity_type="unit"|                   | entity_type=...  |
+--------+---------+                    +--------+---------+
         |                                        |
         v                                        v
+------------------------+              +------------------------+
| strategy._get_or_      |              | strategy._get_or_      |
| build_index()          |              | build_index()          |
+--------+---------------+              +--------+---------------+
         |                                        |
         v                                        v
+------------------------+              +------------------------+
| builder.refresh_       |              | builder.refresh_       |
| incremental()          |              | incremental()          |
| watermark=None         |              | watermark=None         |
| -> FULL FETCH          |              | -> FULL FETCH          |
+--------+---------------+              +--------+---------------+
         |                                        |
         v                                        v
+------------------------+              +------------------------+
| watermark_repo.set_    |              | watermark_repo.set_    |
| watermark(project_gid, |              | watermark(project_gid, |
|   datetime.now())      |              |   datetime.now())      |
+--------+---------------+              +--------+---------------+
         |                                        |
         +----------------------------------------+
                            |
                            v
              +---------------------------+
              | app.state.cache_ready=True|
              +---------------------------+
                            |
                            v
              +---------------------------+
              | /health returns 200       |
              | status: "healthy"         |
              +---------------------------+
                            |
                            v
              +---------------------------+
              | ECS routes traffic        |
              +---------------------------+
```

### Incremental Refresh Flow (TTL Expiry)

```
Request: POST /v1/resolve/unit
         |
         v
+------------------------+
| UnitResolutionStrategy |
|       .resolve()       |
+--------+---------------+
         |
         v
+------------------------+
| _get_or_build_index()  |
+--------+---------------+
         |
         v
+------------------------+
| cached_index =         |
| _gid_index_cache.get() |
+--------+---------------+
         |
         v
    is_stale(3600)?
    /            \
   NO            YES
   |              |
   v              v
Return        +------------------------+
cached        | watermark_repo.get_    |
index         | watermark(project_gid) |
              +--------+---------------+
                       |
                       v
                  watermark?
                  /        \
             None           datetime
              |               |
              v               v
        FULL FETCH      +------------------------+
                        | builder.refresh_       |
                        | incremental()          |
                        +--------+---------------+
                                 |
                                 v
                        +------------------------+
                        | tasks.list_async(      |
                        |   project=gid,         |
                        |   modified_since=wm)   |
                        +--------+---------------+
                                 |
                                 v
                        modified_tasks?
                        /            \
                    empty         has tasks
                      |               |
                      v               v
              Return existing   +------------------------+
              DF unchanged      | _merge_deltas(         |
                               |   existing_df,          |
                               |   modified_tasks)       |
                               +--------+---------------+
                                        |
                                        v
                               +------------------------+
                               | Remove GIDs from       |
                               | existing that are in   |
                               | modified set           |
                               +------------------------+
                                        |
                                        v
                               +------------------------+
                               | Append modified rows   |
                               | to filtered DF         |
                               +------------------------+
                                        |
                                        v
                               +------------------------+
                               | GidLookupIndex.        |
                               | from_dataframe(merged) |
                               +------------------------+
                                        |
                                        v
                               +------------------------+
                               | _gid_index_cache       |
                               | [project_gid] = index  |
                               +------------------------+
                                        |
                                        v
                               +------------------------+
                               | watermark_repo.set_    |
                               | watermark(gid, now)    |
                               +------------------------+
                                        |
                                        v
                               Return index
```

---

## Non-Functional Considerations

### Performance

| Metric | Target | Implementation Approach |
|--------|--------|------------------------|
| First request latency | <500ms | Startup preloading via `_preload_dataframe_cache()` |
| Incremental refresh | <5s | `modified_since` parameter + delta merge |
| Health check response | <10ms | Simple attribute check (`cache_ready`) |
| Cache lookup | <1ms | O(1) dictionary lookup in `GidLookupIndex` |
| Startup time | <60s | Parallel entity preloading |

**Caching Strategy**:
- Module-level `_gid_index_cache` dict for in-memory storage
- 1-hour TTL (`_INDEX_TTL_SECONDS = 3600`)
- Watermark-based incremental refresh avoids full rebuilds

### Concurrency

**Thread Safety Requirements**:

| Component | Concurrency Pattern | Implementation |
|-----------|--------------------|--------------------|
| `WatermarkRepository` | Singleton + Lock | `threading.Lock` for all operations |
| `_gid_index_cache` | Dict + Atomic swap | Python GIL protects dict assignment |
| `GidLookupIndex` | Immutable after creation | No concurrent modification |

**Concurrent Refresh Handling**:

Problem: Multiple requests hitting stale cache simultaneously could trigger duplicate rebuilds.

Solution: Use a per-project lock or asyncio.Event for deduplication:

```python
# Future enhancement: Per-project refresh coordination
_refresh_locks: dict[str, asyncio.Lock] = {}

async def _get_or_build_index_with_dedup(...):
    """Get or build index with concurrent request deduplication."""
    if project_gid not in _refresh_locks:
        _refresh_locks[project_gid] = asyncio.Lock()

    async with _refresh_locks[project_gid]:
        # Re-check cache after acquiring lock
        cached = _gid_index_cache.get(project_gid)
        if cached and not cached.is_stale(_INDEX_TTL_SECONDS):
            return cached
        # Proceed with refresh...
```

**Phase 1 Simplification**: Accept potential duplicate refreshes since they are idempotent and relatively rare (hourly TTL).

### Reliability

**Failure Modes and Recovery**:

| Failure Mode | Detection | Recovery |
|--------------|-----------|----------|
| Asana API timeout during warming | Startup timeout | Retry 3x with exponential backoff, then fail startup |
| Incremental sync API error | Exception catch | Fallback to full rebuild |
| Watermark corruption (future date) | `watermark > now` check | Log warning, force full rebuild |
| Empty project response | `len(df) == 0` check | Set watermark anyway, return None |
| Container killed mid-refresh | N/A (no persistence) | Next startup does full rebuild |

**Graceful Degradation**:
- Cache preload failure is non-fatal (lazy loading still works)
- Incremental refresh failure falls back to full fetch
- Individual entity type failures don't block other entity types

### Observability

**Structured Log Events**:

| Event | Level | Fields |
|-------|-------|--------|
| `cache_warming_started` | INFO | entity_types, project_count |
| `cache_warming_entity_complete` | INFO | entity_type, project_gid, task_count, duration_ms |
| `cache_warming_complete` | INFO | total_duration_ms, entity_count, task_count |
| `incremental_fetch_completed` | INFO | project_gid, modified_count, watermark, duration_ms |
| `full_fetch_completed` | INFO | project_gid, task_count, reason, duration_ms |
| `delta_merge_completed` | DEBUG | existing_count, changed_count, merged_count |
| `incremental_fetch_fallback` | WARN | project_gid, error, fallback |
| `watermark_future_detected` | WARN | project_gid, watermark, action |

---

## Implementation Guidance

### File Organization

```
src/autom8_asana/
    dataframes/
        watermark.py           # NEW: WatermarkRepository
        builders/
            project.py         # MODIFY: Add refresh_incremental(), _merge_deltas()
    api/
        main.py                # MODIFY: Add _preload_dataframe_cache(), cache_ready
        routes/
            health.py          # MODIFY: Add warming state, detailed endpoint
    services/
        resolver.py            # MODIFY: Integrate incremental refresh
```

### Implementation Order

1. **Day 1**: Create `WatermarkRepository` class with tests
2. **Day 1**: Add `_preload_dataframe_cache()` to startup
3. **Day 2**: Implement `refresh_incremental()` in builder
4. **Day 2**: Add `_merge_deltas()` for DataFrame updates
5. **Day 3**: Wire incremental sync into resolver
6. **Day 3**: Update health check for "warming" state
7. **Day 4**: Integration testing, staging deployment

### Recommended Libraries

- **polars**: DataFrame manipulation (already in use)
- **threading.Lock**: Thread-safe watermark access (stdlib)
- **asyncio.gather**: Parallel entity preloading (stdlib)

### Migration Path

**Deployment Strategy**: Blue-green with gradual rollout

1. Deploy new version with preloading disabled (feature flag)
2. Enable preloading in staging, verify health check behavior
3. Enable in production with monitoring
4. No rollback needed - changes are additive

**Backward Compatibility**:
- Existing `_get_or_build_index()` behavior preserved for first sync
- Health check returns 200 immediately if preloading skipped
- No API contract changes

**Rollback Plan**:
- Remove watermark usage, revert to full rebuild pattern
- Set `cache_ready = True` immediately in lifespan
- All changes are 2-way doors

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Startup time exceeds 60s | Medium | High | Parallel preloading, timeout monitoring, fail-fast on slow entity |
| Incremental sync misses deleted tasks | Low | Low | Acceptable staleness until next full rebuild (hourly) |
| Memory growth with large DataFrames | Low | Medium | Monitor memory per project, consider S3 offload in Phase 2 |
| Clock skew causes watermark issues | Low | Low | Future watermark detection triggers full rebuild |
| Concurrent refresh race conditions | Low | Low | Idempotent operations, accept duplicate work in Phase 1 |

---

## ADRs

### ADR-0062: WatermarkRepository Singleton Pattern

**Status**: Proposed

**Context**: Need centralized watermark tracking accessible from multiple resolver strategies and startup code.

**Decision**: Implement `WatermarkRepository` as a thread-safe singleton consistent with `EntityProjectRegistry` pattern.

**Rationale**:
- Singleton provides single source of truth for watermarks
- Thread-safe design supports concurrent request handling
- Matches existing codebase patterns for registries

**Consequences**:
- Positive: Simple, consistent API
- Negative: Global state (acceptable for caching infrastructure)

### ADR-0063: Health Check 503 During Warming

**Status**: Proposed

**Context**: ECS/ALB routes traffic based on health check response. Need to prevent traffic during cache warming.

**Decision**: Return 503 with `{"status": "warming"}` until `app.state.cache_ready = True`.

**Rationale**:
- 503 prevents ALB from routing traffic
- Explicit status makes debugging easier
- Consistent with ECS health check expectations

**Consequences**:
- Positive: No cold-start latency for users
- Negative: Slightly longer deployment time (acceptable)

### ADR-0064: Incremental Refresh Fallback Strategy

**Status**: Proposed

**Context**: Incremental refresh may fail due to API errors, clock skew, or corrupted watermarks.

**Decision**: Always fall back to full rebuild on any incremental refresh failure.

**Rationale**:
- Full rebuild is always correct (if slow)
- Simplifies error handling
- Matches PRD requirement for reliability

**Consequences**:
- Positive: Robust error recovery
- Negative: Occasional full rebuilds on transient errors

---

## Test Boundaries

### Unit Tests

| Component | Test Focus | Mocking Strategy |
|-----------|-----------|------------------|
| `WatermarkRepository` | Thread safety, singleton, timezone validation | None (pure unit) |
| `_merge_deltas()` | DataFrame merge correctness, edge cases | Mock DataFrame creation |
| `refresh_incremental()` | Strategy selection, fallback, watermark update | Mock API client |
| Health check | Status codes, cache_ready flag | Mock app.state |

### Integration Tests

| Scenario | Setup | Verification |
|----------|-------|--------------|
| Startup preload | Real Asana API (test workspace) | Cache populated, watermarks set |
| Incremental refresh | Modify task in Asana, wait for refresh | Only changed task fetched |
| Health check warming | Start container | 503 -> 200 transition |
| Concurrent requests | Parallel requests during refresh | All get valid response |

### Load Tests

| Metric | Target | Test Method |
|--------|--------|-------------|
| First request P95 | <500ms | Measure after health check 200 |
| Incremental refresh P95 | <5s | Measure during TTL expiry |
| Concurrent request handling | No degradation | 10 concurrent requests |

---

## Open Items

1. **DataFrame storage for incremental merge**: Current design rebuilds DataFrame from scratch even for incremental. Phase 2 could store DataFrame alongside index for true delta merge.

2. **Concurrent refresh deduplication**: Phase 1 accepts duplicate refreshes. Phase 2 could add per-project locks.

3. **S3 baseline persistence**: Phase 2 feature for restart resilience.

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/architecture/TDD-materialization-layer.md` | Pending |
| PRD (input) | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-materialization-layer.md` | Read |

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-01 | 1.0 | Architect | Initial TDD |
