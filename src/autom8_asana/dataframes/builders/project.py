"""ProjectDataFrameBuilder for project-scoped DataFrame construction.

Per TDD-0009 Phase 4: Provides project-level DataFrame building with
optional section filtering via task memberships.

Per TDD-0008 Session 4 Phase 4: Adds cache integration support.

Per TDD-WATERMARK-CACHE Phase 1: Adds parallel section fetch via build_async().
Per TDD-WATERMARK-CACHE Phase 2: Adds batch cache integration for get/set operations.
Per TDD-CACHE-PERF-FETCH-PATH: Adds Task-level cache for <1s warm cache latency.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger

from autom8_asana.cache.dataframes import make_dataframe_key
from autom8_asana.dataframes.builders.base import LAZY_THRESHOLD, DataFrameBuilder
from autom8_asana.dataframes.builders.task_cache import (
    TaskCacheCoordinator,
    TaskCacheResult,
)
from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.schema import DataFrameSchema

# Base opt_fields required for DataFrame extraction
# These fields are needed to populate the 12 base TaskRow fields
_BASE_OPT_FIELDS: list[str] = [
    "gid",
    "name",
    "resource_subtype",
    "completed",
    "completed_at",
    "created_at",
    "modified_at",
    "due_on",
    "tags",
    "tags.name",
    "memberships.section.name",
    "memberships.project.gid",
    # Parent reference required for cascade: field resolution
    # Per TDD-CASCADING-FIELD-RESOLUTION-001: CascadingFieldResolver needs parent.gid
    # to traverse the parent chain and resolve fields from ancestor tasks
    "parent",
    "parent.gid",
    # Custom fields required for resolver-based extraction (cf:* sources)
    # Per TDD-0009.1: DefaultCustomFieldResolver needs custom_fields to build
    # the name->GID index and extract values for office_phone, vertical, etc.
    "custom_fields",
    "custom_fields.gid",
    "custom_fields.name",
    "custom_fields.resource_subtype",
    "custom_fields.display_value",
    "custom_fields.enum_value",
    "custom_fields.enum_value.name",
    "custom_fields.multi_enum_values",
    "custom_fields.multi_enum_values.name",
    "custom_fields.number_value",
    "custom_fields.text_value",
]

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.dataframes.cache_integration import DataFrameCacheIntegration
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver
    from autom8_asana.models.task import Task
    from autom8_asana.protocols.cache import CacheProvider

logger = get_logger(__name__)

# Type alias for Project - using Any since Project is not defined in this package
# and we want to accept any object with the required attributes
Project = Any


class ProjectDataFrameBuilder(DataFrameBuilder):
    """Builder for project-scoped DataFrame extraction.

    Per FR-PROJECT-001-013: Project-level extraction with support for:
    - Task type filtering
    - Section filtering via task memberships
    - Lazy/eager evaluation selection
    - Optional cache integration (TDD-0008)

    This builder extracts tasks from a project, optionally filtering
    by section names through task membership inspection.

    Attributes:
        project: Project object containing tasks to extract
        task_type: Task type filter ("Unit", "Contact", etc.)
        sections: Optional list of section names to filter by

    Example:
        >>> from autom8_asana.dataframes.schemas import UNIT_SCHEMA
        >>> builder = ProjectDataFrameBuilder(
        ...     project=project,
        ...     task_type="Unit",
        ...     schema=UNIT_SCHEMA,
        ...     sections=["Active", "In Progress"],
        ...     resolver=resolver,
        ... )
        >>> df = builder.build()
        >>> df.columns
        ['gid', 'name', 'type', 'mrr', ...]

        >>> # With caching:
        >>> df = builder.build(use_cache=True)
    """

    def __init__(
        self,
        project: Project,
        task_type: str,
        schema: DataFrameSchema,
        sections: list[str] | None = None,
        resolver: CustomFieldResolver | None = None,
        lazy_threshold: int = LAZY_THRESHOLD,
        cache_integration: DataFrameCacheIntegration | None = None,
        client: AsanaClient | None = None,
    ) -> None:
        """Initialize project builder.

        Args:
            project: Project object containing tasks. Expected to have:
                     - gid: str attribute for project identifier
                     - tasks: list[Task] attribute or method
            task_type: Task type to filter and extract ("Unit", "Contact")
            schema: DataFrameSchema for extraction
            sections: Optional list of section names to filter by.
                      If provided, only tasks in these sections are included.
            resolver: Optional CustomFieldResolver for custom fields
            lazy_threshold: Task count threshold for lazy evaluation
            cache_integration: Optional cache integration for struc caching
            client: Optional AsanaClient for cascade: field resolution.
                   Required if schema contains cascade: sources.
        """
        super().__init__(schema, resolver, lazy_threshold, cache_integration, client)
        self._project = project
        self._task_type = task_type
        self._sections = sections

    @property
    def project(self) -> Project:
        """Get the project being built from."""
        return self._project

    @property
    def task_type(self) -> str:
        """Get the task type filter."""
        return self._task_type

    @property
    def sections(self) -> list[str] | None:
        """Get the section filter list."""
        return self._sections

    def get_tasks(self) -> list[Task]:
        """Get tasks from project with optional section filtering.

        Per FR-PROJECT-001, FR-PROJECT-010: Returns tasks from project,
        filtered by sections if specified. Tasks are expected to be
        pre-filtered by task_type at the project/API level.

        Returns:
            List of Task objects from the project
        """
        # Handle project.tasks as attribute or method
        tasks = self._project.tasks
        if callable(tasks):
            tasks = tasks()

        if not tasks:
            return []

        # Apply section filtering if sections specified
        if self._sections:
            tasks = [
                task for task in tasks if self._task_in_sections(task, self._sections)
            ]

        # Cast to list[Task] for type checker since tasks comes from Any
        result: list[Task] = tasks
        return result

    def _get_project_gid(self) -> str | None:
        """Get project GID for section extraction context.

        Per FR-PROJECT-001: Uses project GID for section extraction
        and cache key generation.

        Returns:
            Project GID string or None
        """
        return getattr(self._project, "gid", None)

    def _get_extractor(self) -> BaseExtractor:
        """Get extractor for project's task type.

        Returns:
            Appropriate BaseExtractor subclass for task_type
        """
        return self._create_extractor(self._task_type)

    def _task_in_sections(self, task: Task, sections: list[str]) -> bool:
        """Check if task belongs to any of the specified sections.

        Per FR-PROJECT-010: Section filtering via task memberships.
        Inspects task.memberships to find section names.

        Args:
            task: Task to check
            sections: List of section names to match against

        Returns:
            True if task is in any of the specified sections
        """
        if not task.memberships:
            return False

        for membership in task.memberships:
            section = membership.get("section", {})
            if isinstance(section, dict):
                section_name = section.get("name")
                if section_name in sections:
                    return True

        return False

    # =========================================================================
    # Parallel Fetch Methods (Phase 1 & 2: TDD-WATERMARK-CACHE)
    # =========================================================================

    async def build_with_parallel_fetch_async(
        self,
        client: AsanaClient,
        *,
        use_parallel_fetch: bool = True,
        use_cache: bool = True,
        max_concurrent_sections: int | None = None,
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        """Build DataFrame with parallel section fetch and cache integration.

        Per FR-FETCH-001: Async method for parallel section fetch.
        Per FR-CONFIG-002: Opt-out via use_parallel_fetch=False.
        Per FR-CONFIG-004: Cache bypass via use_cache=False.
        Per FR-FALLBACK-001: Falls back to serial on parallel fetch failure.
        Per FR-CACHE-001: Cache lookup before fetch via get_batch().
        Per FR-CACHE-005: Cache population after fetch via set_batch().
        Per TDD-CACHE-PERF-FETCH-PATH: Two-phase Task cache strategy.

        When use_cache=True (default):
        1. Enumerate section task GIDs (lightweight)
        2. Batch lookup tasks in cache via TaskCacheCoordinator
        3. If all tasks cached -> skip API fetch
        4. If partial/none cached -> fetch missing from API
        5. Populate cache with newly fetched tasks
        6. Build DataFrame from merged task list
        7. Cache extracted rows (existing row cache behavior)

        When use_cache=False:
        - Bypasses both Task cache and row cache

        Args:
            client: AsanaClient for API calls and cache access.
            use_parallel_fetch: Enable parallel section fetch (default True).
                Set False to use serial project-level fetch.
            use_cache: Enable cache lookup and population (default True).
                Set False to bypass cache entirely.
            max_concurrent_sections: Override default concurrency limit.
                Defaults to 8.
            lazy: Evaluation mode override. None = auto-select based on threshold.

        Returns:
            Polars DataFrame with extracted task data.

        Raises:
            No exceptions - falls back to serial on parallel fetch failure.

        Example:
            >>> builder = ProjectDataFrameBuilder(project, "Unit", schema)
            >>> df = await builder.build_with_parallel_fetch_async(client)
            >>> df = await builder.build_with_parallel_fetch_async(
            ...     client, use_parallel_fetch=False
            ... )
            >>> df = await builder.build_with_parallel_fetch_async(
            ...     client, use_cache=False
            ... )
        """
        import time

        from autom8_asana.dataframes.builders.parallel_fetch import (
            ParallelFetchError,
            ParallelSectionFetcher,
        )

        project_gid = self._get_project_gid()
        if not project_gid:
            # No project GID - fall back to existing build method
            return await super().build_async(lazy=lazy)

        # Determine concurrency limit
        max_concurrent = max_concurrent_sections or 8

        # Determine if row cache is available and should be used
        row_cache_available = use_cache and self._cache_integration is not None
        schema_version = self._schema.version

        # Get Task-level cache provider from client (if available)
        task_cache_provider = self._get_task_cache_provider(client) if use_cache else None
        task_cache_coordinator = TaskCacheCoordinator(task_cache_provider)

        # TDD-CACHE-PERF-FETCH-PATH: Structured logging - build started
        start_time = time.perf_counter()
        logger.info(
            "dataframe_build_started",
            extra={
                "project_gid": project_gid,
                "use_parallel_fetch": use_parallel_fetch,
                "use_cache": use_cache,
                "task_cache_enabled": task_cache_provider is not None,
                "max_concurrent_sections": max_concurrent,
            },
        )

        # Track metrics for logging
        fetch_strategy = "parallel" if use_parallel_fetch else "serial"
        sections_fetched = 0
        task_count = 0
        task_cache_result: TaskCacheResult | None = None

        # Try parallel fetch if enabled
        if use_parallel_fetch:
            try:
                fetcher = ParallelSectionFetcher(
                    sections_client=client.sections,
                    tasks_client=client.tasks,
                    project_gid=project_gid,
                    max_concurrent=max_concurrent,
                    opt_fields=_BASE_OPT_FIELDS,
                    cache_provider=task_cache_provider,  # Per ADR-0131: GID enumeration caching
                )

                # TDD-CACHE-PERF-FETCH-PATH: Two-phase cache strategy
                if task_cache_provider is not None:
                    # Phase 1: Enumerate GIDs (lightweight)
                    gid_enum_start = time.perf_counter()
                    section_gids_map = await fetcher.fetch_section_task_gids_async()
                    gid_enum_time_ms = (time.perf_counter() - gid_enum_start) * 1000

                    logger.debug(
                        "section_gid_enumeration_completed",
                        extra={
                            "project_gid": project_gid,
                            "section_count": len(section_gids_map),
                            "enumeration_time_ms": round(gid_enum_time_ms, 2),
                        },
                    )

                    if not section_gids_map:
                        # No sections - fall back to serial
                        logger.debug(
                            "No sections found for project %s, using serial fetch",
                            project_gid,
                        )
                        fetch_strategy = "serial"
                        df, task_cache_result = await self._build_serial_with_task_cache_async(
                            client,
                            task_cache_coordinator,
                            lazy=lazy,
                            use_row_cache=row_cache_available,
                        )
                        task_count = len(df)
                    else:
                        sections_fetched = len(section_gids_map)

                        # Flatten and deduplicate GIDs (preserving section order)
                        all_task_gids = self._flatten_section_gids(section_gids_map)

                        # Phase 2: Batch cache lookup
                        cache_lookup_start = time.perf_counter()
                        cached_tasks_map = await task_cache_coordinator.lookup_tasks_async(
                            all_task_gids
                        )
                        cache_lookup_time_ms = (time.perf_counter() - cache_lookup_start) * 1000

                        # Partition into hits and misses
                        cached_tasks: dict[str, Task] = {}
                        miss_gids: list[str] = []
                        for gid in all_task_gids:
                            task = cached_tasks_map.get(gid)
                            if task is not None:
                                cached_tasks[gid] = task
                            else:
                                miss_gids.append(gid)

                        # FR-OBS-001: Log cache lookup results
                        hit_count = len(cached_tasks)
                        miss_count = len(miss_gids)
                        hit_rate = hit_count / len(all_task_gids) if all_task_gids else 0.0
                        logger.info(
                            "task_cache_lookup_completed",
                            extra={
                                "project_gid": project_gid,
                                "hit_count": hit_count,
                                "miss_count": miss_count,
                                "hit_rate": round(hit_rate, 3),
                                "lookup_time_ms": round(cache_lookup_time_ms, 2),
                            },
                        )

                        # Phase 3: Fetch missing tasks from API
                        fetched_tasks: list[Task] = []
                        api_fetch_time_ms = 0.0
                        cache_populate_time_ms = 0.0
                        fetch_path = "none"

                        if miss_gids:
                            # Per ADR-0130/TDD-CACHE-OPT-P2: Targeted fetch for misses only
                            # Cold cache (0% hit): use fetch_all() for efficiency
                            # Partial cache: use fetch_by_gids() for targeted fetch
                            is_cold_cache = len(cached_tasks) == 0
                            api_fetch_start = time.perf_counter()
                            try:
                                if is_cold_cache:
                                    # Cold cache: fetch all tasks in one pass
                                    fetch_path = "cold"
                                    result = await fetcher.fetch_all()
                                    fetched_tasks = result.tasks
                                else:
                                    # Partial cache: fetch only missing GIDs
                                    fetch_path = "partial"
                                    result = await fetcher.fetch_by_gids(
                                        miss_gids, section_gid_map=section_gids_map
                                    )
                                    fetched_tasks = result.tasks
                            except ParallelFetchError:
                                # Fallback: fetch all and filter to miss GIDs
                                fetch_path = "fallback"
                                logger.debug(
                                    "fetch_by_gids failed, falling back to fetch_all"
                                )
                                result = await fetcher.fetch_all()
                                miss_gid_set = set(miss_gids)
                                fetched_tasks = [
                                    t for t in result.tasks if t.gid in miss_gid_set
                                ]
                            api_fetch_time_ms = (time.perf_counter() - api_fetch_start) * 1000

                            # FR-OBS-002: Log path selection and fetch timing
                            logger.info(
                                "api_fetch_completed",
                                extra={
                                    "project_gid": project_gid,
                                    "fetch_path": fetch_path,
                                    "tasks_fetched": len(fetched_tasks),
                                    "fetch_time_ms": round(api_fetch_time_ms, 2),
                                },
                            )

                            # Phase 4: Populate cache with newly fetched (ADR-0130)
                            cache_populate_start = time.perf_counter()
                            try:
                                populated_count = await task_cache_coordinator.populate_tasks_async(
                                    fetched_tasks
                                )
                                cache_populate_time_ms = (
                                    time.perf_counter() - cache_populate_start
                                ) * 1000
                                logger.info(
                                    "task_cache_population_completed",
                                    extra={
                                        "project_gid": project_gid,
                                        "populated_count": populated_count,
                                        "populate_time_ms": round(cache_populate_time_ms, 2),
                                    },
                                )
                            except Exception as e:
                                cache_populate_time_ms = (
                                    time.perf_counter() - cache_populate_start
                                ) * 1000
                                # Graceful degradation on cache population failure
                                logger.warning(
                                    "task_cache_population_failed",
                                    extra={
                                        "error_type": type(e).__name__,
                                        "error_message": str(e),
                                        "task_count": len(fetched_tasks),
                                    },
                                )
                        else:
                            # 100% cache hit - no API fetch needed
                            fetch_path = "warm"
                            logger.info(
                                "cache_hit_skip_api_fetch",
                                extra={
                                    "project_gid": project_gid,
                                    "cached_task_count": len(cached_tasks),
                                },
                            )

                        # Phase 5: Merge results
                        task_cache_result = task_cache_coordinator.merge_results(
                            all_task_gids, cached_tasks, fetched_tasks
                        )
                        tasks = task_cache_result.all_tasks

                        # Apply section filtering if specified
                        if self._sections:
                            tasks = [
                                t for t in tasks
                                if self._task_in_sections(t, self._sections)
                            ]

                        task_count = len(tasks)

                        # Build DataFrame with row cache integration
                        df = await self._build_from_tasks_with_cache(
                            tasks=tasks,
                            project_gid=project_gid,
                            cache_available=row_cache_available,
                            schema_version=schema_version,
                            lazy=lazy,
                        )
                else:
                    # No Task cache - use original parallel fetch path
                    result = await fetcher.fetch_all()
                    sections_fetched = result.sections_fetched

                    if result.sections_fetched == 0:
                        logger.debug(
                            "No sections found for project %s, using serial fetch",
                            project_gid,
                        )
                        fetch_strategy = "serial"
                        df = await self._build_serial_async(
                            client, lazy=lazy, use_cache=use_cache
                        )
                        task_count = len(df)
                    else:
                        tasks = result.tasks

                        if self._sections:
                            tasks = [
                                t for t in tasks
                                if self._task_in_sections(t, self._sections)
                            ]

                        task_count = len(tasks)
                        df = await self._build_from_tasks_with_cache(
                            tasks=tasks,
                            project_gid=project_gid,
                            cache_available=row_cache_available,
                            schema_version=schema_version,
                            lazy=lazy,
                        )

            except ParallelFetchError as e:
                # FR-FALLBACK-001: Fall back to serial fetch
                logger.warning(
                    "dataframe_fallback_triggered",
                    extra={
                        "project_gid": project_gid,
                        "reason": str(e),
                        "error_type": "ParallelFetchError",
                    },
                )
                fetch_strategy = "serial"
                df = await self._build_serial_async(
                    client, lazy=lazy, use_cache=use_cache
                )
                task_count = len(df)

            except Exception as e:
                # Catch any unexpected exceptions and fall back
                import traceback
                tb = traceback.format_exc()
                logger.warning(
                    "dataframe_fallback_triggered",
                    extra={
                        "project_gid": project_gid,
                        "reason": str(e),
                        "error_type": type(e).__name__,
                        "traceback": tb,
                    },
                )
                fetch_strategy = "serial"
                try:
                    df = await self._build_serial_async(
                        client, lazy=lazy, use_cache=use_cache
                    )
                    task_count = len(df)
                except Exception as serial_e:
                    # Serial fallback also failed - log and re-raise
                    serial_tb = traceback.format_exc()
                    logger.error(
                        "dataframe_serial_fallback_failed",
                        extra={
                            "project_gid": project_gid,
                            "original_error": str(e),
                            "serial_error": str(serial_e),
                            "traceback": serial_tb,
                        },
                    )
                    raise

        else:
            # use_parallel_fetch=False: Use serial fetch
            df = await self._build_serial_async(client, lazy=lazy, use_cache=use_cache)
            task_count = len(df)

        # TDD-CACHE-PERF-FETCH-PATH: Structured logging - build completed
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Extract cache metrics
        task_cache_hits = task_cache_result.cache_hits if task_cache_result else 0
        task_cache_misses = task_cache_result.cache_misses if task_cache_result else 0
        task_cache_hit_rate = task_cache_result.hit_rate if task_cache_result else 0.0
        tasks_fetched_from_api = len(task_cache_result.fetched_tasks) if task_cache_result else 0

        logger.info(
            "dataframe_build_completed",
            extra={
                "project_gid": project_gid,
                "task_count": task_count,
                "fetch_strategy": fetch_strategy,
                "fetch_time_ms": round(elapsed_ms, 2),
                "sections_fetched": sections_fetched,
                # Task cache metrics (TDD-CACHE-PERF-FETCH-PATH)
                "task_cache_hits": task_cache_hits,
                "task_cache_misses": task_cache_misses,
                "task_cache_hit_rate": round(task_cache_hit_rate, 3),
                "tasks_fetched_from_api": tasks_fetched_from_api,
            },
        )

        return df

    def _get_task_cache_provider(self, client: AsanaClient) -> CacheProvider | None:
        """Get Task-level cache provider from client.

        Per TDD-CACHE-PERF-FETCH-PATH: Access cache provider for Task objects.
        Uses the same cache provider as TasksClient.get_async().

        Args:
            client: AsanaClient instance.

        Returns:
            CacheProvider if available, None otherwise.
        """
        try:
            # Access cache provider from client's tasks client
            return getattr(client.tasks, "_cache", None)
        except AttributeError:
            return None

    def _flatten_section_gids(
        self, section_gids_map: dict[str, list[str]]
    ) -> list[str]:
        """Flatten section GID mapping to ordered, deduplicated list.

        Per TDD-CACHE-PERF-FETCH-PATH: Preserves section order while
        deduplicating multi-homed tasks.

        Args:
            section_gids_map: Dict mapping section_gid -> list of task_gids.

        Returns:
            Ordered list of unique task GIDs.
        """
        seen: set[str] = set()
        result: list[str] = []
        for gids in section_gids_map.values():
            for gid in gids:
                if gid not in seen:
                    seen.add(gid)
                    result.append(gid)
        return result

    async def _build_serial_with_task_cache_async(
        self,
        client: AsanaClient,
        task_cache_coordinator: TaskCacheCoordinator,
        *,
        lazy: bool | None = None,
        use_row_cache: bool = True,
    ) -> tuple[pl.DataFrame, TaskCacheResult | None]:
        """Build DataFrame using serial fetch with Task cache integration.

        Args:
            client: AsanaClient for API calls.
            task_cache_coordinator: Coordinator for Task-level cache.
            lazy: Evaluation mode override.
            use_row_cache: Enable row-level cache.

        Returns:
            Tuple of (DataFrame, TaskCacheResult or None).
        """
        project_gid = self._get_project_gid()
        if not project_gid:
            return self._build_empty(), None

        # Fetch all tasks via project-level query
        tasks: list[Task] = await client.tasks.list_async(
            project=project_gid,
            opt_fields=_BASE_OPT_FIELDS,
        ).collect()

        if not tasks:
            return self._build_empty(), None

        # Populate Task cache (no lookup for serial - we already have the data)
        await task_cache_coordinator.populate_tasks_async(tasks)

        # Apply section filtering
        if self._sections:
            tasks = [t for t in tasks if self._task_in_sections(t, self._sections)]

        # Build result (all fetched, no cache hits)
        task_cache_result = TaskCacheResult(
            cached_tasks=[],
            fetched_tasks=tasks,
            cache_hits=0,
            cache_misses=len(tasks),
            all_tasks=tasks,
        )

        schema_version = self._schema.version
        df = await self._build_from_tasks_with_cache(
            tasks=tasks,
            project_gid=project_gid,
            cache_available=use_row_cache and self._cache_integration is not None,
            schema_version=schema_version,
            lazy=lazy,
        )

        return df, task_cache_result

    async def _build_serial_async(
        self,
        client: AsanaClient,
        lazy: bool | None = None,
        use_cache: bool = True,
    ) -> pl.DataFrame:
        """Build DataFrame using serial project-level fetch.

        Per FR-FALLBACK-001: Fallback to project-level list_async.

        Args:
            client: AsanaClient for API calls.
            lazy: Evaluation mode override.
            use_cache: Enable cache lookup and population.

        Returns:
            Polars DataFrame with extracted task data.
        """
        project_gid = self._get_project_gid()
        if not project_gid:
            return self._build_empty()

        # Fetch all tasks via project-level query with required fields
        tasks: list[Task] = await client.tasks.list_async(
            project=project_gid,
            opt_fields=_BASE_OPT_FIELDS,
        ).collect()

        # Apply section filtering if specified
        if self._sections:
            tasks = [
                task for task in tasks if self._task_in_sections(task, self._sections)
            ]

        # Determine if cache is available and should be used
        cache_available = use_cache and self._cache_integration is not None
        schema_version = self._schema.version

        # Build DataFrame with cache integration if available
        return await self._build_from_tasks_with_cache(
            tasks=tasks,
            project_gid=project_gid,
            cache_available=cache_available,
            schema_version=schema_version,
            lazy=lazy,
        )

    async def _build_from_tasks(
        self,
        tasks: list[Task],
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        """Build DataFrame from a list of tasks.

        Per TDD-CASCADING-FIELD-RESOLUTION-001: Uses async extraction to support
        cascade: sources that require parent chain traversal.

        Args:
            tasks: List of Task objects to extract.
            lazy: Evaluation mode override.

        Returns:
            Polars DataFrame with extracted task data.
        """
        if not tasks:
            return self._build_empty()

        # Determine evaluation mode
        use_lazy = self._should_use_lazy(len(tasks), lazy)

        # Build DataFrame using async mode for cascade: support
        if use_lazy:
            return await self._build_lazy_async(tasks)
        else:
            return await self._build_eager_async(tasks)

    # =========================================================================
    # Cache Integration Methods (Phase 2: TDD-WATERMARK-CACHE)
    # =========================================================================

    async def _build_from_tasks_with_cache(
        self,
        tasks: list[Task],
        project_gid: str,
        cache_available: bool,
        schema_version: str,
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        """Build DataFrame with cache integration.

        Per FR-CACHE-001: Cache lookup before extraction via get_batch().
        Per FR-CACHE-004: Partial cache - extract only missing tasks.
        Per FR-CACHE-005: Cache population after extraction via set_batch().
        Per FR-CACHE-006: Use task.modified_at as version.
        Per FR-CACHE-008: Graceful degradation on cache failures.

        Args:
            tasks: List of Task objects (already fetched).
            project_gid: Project GID for cache key generation.
            cache_available: Whether cache is enabled and configured.
            schema_version: Schema version for cache entries.
            lazy: Evaluation mode override.

        Returns:
            Polars DataFrame with extracted task data.
        """
        if not tasks:
            return self._build_empty()

        # If cache not available, use standard build (async for cascade: support)
        if not cache_available or self._cache_integration is None:
            return await self._build_from_tasks(tasks, lazy=lazy)

        # Build task map for efficient lookup
        task_map: dict[str, Task] = {task.gid: task for task in tasks}
        task_gids = list(task_map.keys())

        # FR-CACHE-001: Check cache for existing entries
        cached_rows: dict[str, dict[str, Any]] = {}
        cache_misses: list[Task] = []

        try:
            # FR-CACHE-002: Use get_batch for efficient bulk retrieval
            # Build list of (task_gid, project_gid) pairs
            task_project_pairs = [(gid, project_gid) for gid in task_gids]

            # FR-CACHE-006: Build modifications dict with task.modified_at
            modifications: dict[str, datetime | str] = {}
            for task in tasks:
                if task.modified_at:
                    modifications[task.gid] = task.modified_at

            # Batch cache lookup
            cache_results = await self._cache_integration.get_cached_batch_async(
                task_project_pairs=task_project_pairs,
                schema_version=schema_version,
                modifications=modifications,
            )

            # Partition into hits and misses
            for task_gid in task_gids:
                # FR-CACHE-003: Key format matches make_dataframe_key()
                cache_key = make_dataframe_key(task_gid, project_gid)
                cached_row = cache_results.get(cache_key)

                if cached_row is not None:
                    # Cache hit - use cached data
                    cached_rows[task_gid] = cached_row.data
                else:
                    # Cache miss - need to extract
                    cache_misses.append(task_map[task_gid])

            logger.debug(
                "Cache lookup for project %s: %d hits, %d misses",
                project_gid,
                len(cached_rows),
                len(cache_misses),
            )

        except Exception as e:
            # FR-CACHE-008: Graceful degradation on cache failure
            logger.warning(
                "Cache lookup failed for project %s, proceeding without cache: %s",
                project_gid,
                str(e),
            )
            # Treat all as cache misses
            cached_rows = {}
            cache_misses = tasks

        # Extract rows for cache misses using async extraction
        # Per TDD-CASCADING-FIELD-RESOLUTION-001: Must use async for cascade: sources
        extracted_rows: list[tuple[str, dict[str, Any], datetime | str | None]] = []
        for task in cache_misses:
            row = await self._extract_row_async(task)
            modified_at = getattr(task, "modified_at", None)
            extracted_rows.append((task.gid, row, modified_at))

        # FR-CACHE-005: Populate cache with newly extracted rows
        if extracted_rows and self._cache_integration is not None:
            try:
                rows_to_cache: list[
                    tuple[str, str, dict[str, Any], datetime | str]
                ] = []
                for task_gid, row, modified_at in extracted_rows:
                    if modified_at is not None:
                        rows_to_cache.append(
                            (task_gid, project_gid, row, modified_at)
                        )

                if rows_to_cache:
                    await self._cache_integration.cache_batch_async(
                        rows=rows_to_cache,
                        schema_version=schema_version,
                    )
                    logger.debug(
                        "Cached %d rows for project %s",
                        len(rows_to_cache),
                        project_gid,
                    )

            except Exception as e:
                # FR-CACHE-008: Graceful degradation on cache write failure
                logger.warning(
                    "Cache write failed for project %s: %s",
                    project_gid,
                    str(e),
                )

        # Combine cached rows with extracted rows, preserving task order
        all_rows: list[dict[str, Any]] = []
        extracted_map = {gid: row for gid, row, _ in extracted_rows}

        for task in tasks:
            if task.gid in cached_rows:
                all_rows.append(cached_rows[task.gid])
            elif task.gid in extracted_map:
                all_rows.append(extracted_map[task.gid])

        # Build DataFrame
        if not all_rows:
            return self._build_empty()

        use_lazy = self._should_use_lazy(len(all_rows), lazy)
        if use_lazy:
            lazy_frame = pl.LazyFrame(all_rows, schema=self._schema.to_polars_schema())
            return lazy_frame.collect()
        else:
            return pl.DataFrame(all_rows, schema=self._schema.to_polars_schema())

    # =========================================================================
    # Incremental Refresh Methods (FR-002, FR-006: TDD-materialization-layer)
    # =========================================================================

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

        # Determine fetch strategy - use explicit None checks for type narrowing
        if watermark is not None and existing_df is not None:
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
                # Per TDD-CASCADING-FIELD-RESOLUTION-001: Use async for cascade: sources
                merged_df = await self._merge_deltas_async(existing_df, modified_tasks)
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

        Per FR-002: Uses modified_since parameter for efficient API calls.

        Args:
            client: AsanaClient for API calls.
            project_gid: Target project GID.
            watermark: Timestamp for modified_since filter.

        Returns:
            List of modified Task objects.

        Raises:
            ValueError: If watermark is in the future (clock skew).
        """
        from datetime import timezone

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

    async def _merge_deltas_async(
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

        Per TDD-CASCADING-FIELD-RESOLUTION-001: Async for cascade: sources.

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

        # Extract rows from changed tasks using async extractor
        # Per TDD-CASCADING-FIELD-RESOLUTION-001: Must use async for cascade: sources
        changed_rows: list[dict[str, Any]] = []
        for task in changed_tasks:
            row = await self._extract_row_async(task)
            changed_rows.append(row)

        # Create DataFrame from changed tasks
        changed_df = pl.DataFrame(
            changed_rows,
            schema=self._schema.to_polars_schema(),
        )

        # Get GIDs of changed tasks for filtering
        changed_gids = changed_df["gid"].to_list()

        # Remove existing rows with matching GIDs (will be replaced)
        unchanged_df = existing_df.filter(~pl.col("gid").is_in(changed_gids))

        # Concatenate unchanged rows with updated rows
        merged_df = pl.concat([unchanged_df, changed_df])

        return merged_df
