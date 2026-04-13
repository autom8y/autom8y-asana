"""Cascading field resolver for parent chain traversal.

Per TDD-CASCADING-FIELD-RESOLUTION-001: Resolves field values by traversing
the parent task chain, using CASCADING_FIELD_REGISTRY to find field definitions
and respecting CascadingFieldDef rules (target_types, allow_override).

Per TDD-UNIFIED-CACHE-001 Phase 3: Adds optional CascadeViewPlugin delegation
for unified cache integration.

Per TDD-GID-RESOLUTION-SERVICE: Adds HierarchyAwareResolver integration for
batch parent fetching with concurrency control, eliminating N+1 API calls.

This resolver bridges the DataFrame extraction layer to the business model layer's
CascadingFieldDef system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

# Optional imports - fall back to None if not available in installed version
try:
    from autom8y_cache import HierarchyAwareResolver
except ImportError:
    HierarchyAwareResolver = None  # type: ignore[assignment, misc]

from autom8_asana.core.errors import S3_TRANSPORT_ERRORS
from autom8_asana.dataframes.views.cf_utils import (
    class_to_entity_type,
    get_custom_field_value,
    get_field_value,
)

# Per TDD-registry-consolidation: Import from package to ensure bootstrap runs
from autom8_asana.models.business import (
    STANDARD_TASK_OPT_FIELDS,
    CascadingFieldDef,
    EntityType,
    detect_entity_type,
    get_cascading_field,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin
    from autom8_asana.models.task import Task


logger = get_logger(__name__)


class TaskParentFetcher:
    """HierarchyResolverProtocol implementation for Asana task parents.

    Per TDD-GID-RESOLUTION-SERVICE: Implements batch fetching of parent tasks
    for use with HierarchyAwareResolver, eliminating N+1 API calls during
    parent chain traversal.

    Example:
        >>> fetcher = TaskParentFetcher(client)
        >>> resolver = HierarchyAwareResolver(fetcher=fetcher)
        >>> parents = await resolver.resolve_with_ancestors(
        ...     keys={"task-1", "task-2"},
        ...     max_depth=5,
        ... )
    """

    def __init__(self, client: AsanaClient) -> None:
        """Initialize fetcher with Asana client.

        Args:
            client: AsanaClient for fetching tasks.
        """
        self._client = client

    async def fetch_batch(self, keys: set[str]) -> dict[str, Task]:
        """Fetch multiple tasks by GID.

        Per TDD-GID-RESOLUTION-SERVICE: Fetches tasks in batch using
        parallel API calls. Future optimization: use Asana batch API.

        Args:
            keys: Set of task GIDs to fetch.

        Returns:
            Dict mapping GIDs to Task objects.
            Missing keys are omitted from result.
        """
        import asyncio

        results: dict[str, Task] = {}

        async def fetch_one(gid: str) -> tuple[str, Task | None]:
            try:
                task = await self._client.tasks.get_async(
                    gid,
                    opt_fields=list(STANDARD_TASK_OPT_FIELDS),
                )
                return (gid, task)
            except S3_TRANSPORT_ERRORS as e:
                logger.warning(
                    "task_fetch_error",
                    extra={"task_gid": gid, "error": str(e)},
                )
                return (gid, None)

        # Fetch all in parallel (concurrency bounded by caller's controller)
        fetched = await asyncio.gather(*[fetch_one(gid) for gid in keys])

        for gid, task in fetched:
            if task is not None:
                results[gid] = task

        return results

    def get_parent_key(self, item: Task) -> str | None:
        """Extract parent GID from task.

        Args:
            item: Task to extract parent from.

        Returns:
            Parent GID if task has parent, None otherwise.
        """
        if item.parent is None:
            return None
        return item.parent.gid


class CascadingFieldResolver:
    """Resolves field values by traversing parent task chain.

    Uses CASCADING_FIELD_REGISTRY to find field definitions and
    respects CascadingFieldDef rules (target_types, allow_override).

    Per TDD-CASCADING-FIELD-RESOLUTION-001: Bridges DataFrame extraction
    layer to business model layer's CascadingFieldDef system.

    Per TDD-UNIFIED-CACHE-001 Phase 3: Supports optional CascadeViewPlugin
    delegation for unified cache integration. When cascade_plugin is provided,
    resolve_async() delegates to it instead of using the local _parent_cache.

    Per TDD-GID-RESOLUTION-SERVICE: Adds HierarchyAwareResolver integration
    for batch parent fetching with bounded concurrency. When hierarchy_resolver
    is provided, uses pre-warmed parent cache instead of individual API calls.

    Example:
        >>> # Traditional usage
        >>> resolver = CascadingFieldResolver(client=client)
        >>> value = await resolver.resolve_async(unit_task, "Office Phone")

        >>> # Unified cache integration
        >>> from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin
        >>> cascade_plugin = CascadeViewPlugin(store=unified_store)
        >>> resolver = CascadingFieldResolver(client=client, cascade_plugin=cascade_plugin)
        >>> value = await resolver.resolve_async(unit_task, "Office Phone")  # Delegates to plugin

        >>> # Batch-optimized with HierarchyAwareResolver
        >>> fetcher = TaskParentFetcher(client)
        >>> hierarchy_resolver = HierarchyAwareResolver(fetcher=fetcher)
        >>> resolver = CascadingFieldResolver(client=client, hierarchy_resolver=hierarchy_resolver)
        >>> # Pre-warm parents for batch processing
        >>> await resolver.warm_parents(tasks)
        >>> for task in tasks:
        ...     value = await resolver.resolve_async(task, "Office Phone")

    Attributes:
        _client: AsanaClient for fetching parent tasks.
        _cascade_plugin: Optional CascadeViewPlugin for unified cache delegation.
        _hierarchy_resolver: Optional HierarchyAwareResolver for batch parent fetching.
        _parent_cache: Local cache of pre-fetched parent tasks.
    """

    def __init__(
        self,
        client: AsanaClient,
        cascade_plugin: CascadeViewPlugin | None = None,
        hierarchy_resolver: Any | None = None,
    ) -> None:
        """Initialize resolver with Asana client.

        Args:
            client: AsanaClient for fetching parent tasks.
            cascade_plugin: Optional CascadeViewPlugin for unified cache delegation.
                           Per TDD-UNIFIED-CACHE-001 Phase 3: When provided, resolve_async()
                           delegates to cascade_plugin.resolve_async().
            hierarchy_resolver: Optional HierarchyAwareResolver for batch parent
                           fetching. Per TDD-GID-RESOLUTION-SERVICE: When provided,
                           enables batch pre-warming of parent chains.
        """
        self._client = client
        self._cascade_plugin = cascade_plugin
        self._hierarchy_resolver = hierarchy_resolver
        # Local cache of pre-fetched parents (populated by warm_parents or on-demand)
        self._parent_cache: dict[str, Task] = {}

    async def resolve_async(
        self,
        task: Task,
        field_name: str,
        max_depth: int = 5,
    ) -> Any:
        """Traverse parent chain to find field value.

        Per FR-CASCADE-RESOLVE-002: Traverses parent chain until field
        is found or max_depth is reached.

        Per TDD-UNIFIED-CACHE-001 Phase 3: When cascade_plugin is provided,
        delegates to cascade_plugin.resolve_async() for unified cache usage.

        Args:
            task: Starting task to resolve from.
            field_name: Custom field name (e.g., "Office Phone").
            max_depth: Maximum parent levels to traverse (default 5).

        Returns:
            Field value from ancestor, or None if not found.

        Note:
            Returns None if:
            - Field is not in CASCADING_FIELD_REGISTRY
            - max_depth exceeded
            - Parent chain broken (no parent)
            - Field not found in any ancestor
        """
        # TDD-UNIFIED-CACHE-001 Phase 3: Delegate to cascade_plugin if provided
        if self._cascade_plugin is not None:
            return await self._cascade_plugin.resolve_async(
                task=task,
                field_name=field_name,
                max_depth=max_depth,
            )

        # Look up field in registry
        result = get_cascading_field(field_name)
        if result is None:
            logger.debug(
                "cascade_field_not_registered",
                extra={"field_name": field_name, "task_gid": task.gid},
            )
            return None

        owner_class, field_def = result

        logger.debug(
            "cascade_traversal_start",
            extra={
                "task_gid": task.gid,
                "field_name": field_name,
                "owner_class": owner_class.__name__,
            },
        )

        # Check if task has local value and if override is allowed
        local_value = get_custom_field_value(task, field_def.name)
        if local_value is not None and field_def.allow_override:
            logger.debug(
                "cascade_local_override",
                extra={
                    "task_gid": task.gid,
                    "field_name": field_name,
                    "value": local_value,
                },
            )
            return local_value

        # Traverse parent chain
        return await self._traverse_parent_chain(
            task=task,
            field_def=field_def,
            owner_class=owner_class,
            max_depth=max_depth,
        )

    async def _traverse_parent_chain(
        self,
        task: Task,
        field_def: CascadingFieldDef,
        owner_class: type,
        max_depth: int,
    ) -> Any:
        """Traverse parent chain to find cascading field value.

        Traverses upward through the parent chain looking for the field owner.
        When entity type detection returns UNKNOWN (e.g., project not registered),
        continues traversing to ROOT and extracts field from root if owner is Business.

        This fallback behavior ensures cascading works even when projects aren't
        registered in ProjectTypeRegistry, which is common during DataFrame extraction.

        Args:
            task: Current task in traversal.
            field_def: CascadingFieldDef with field configuration.
            owner_class: Entity class that owns this cascading field.
            max_depth: Maximum remaining depth to traverse.

        Returns:
            Field value if found, None otherwise.
        """
        visited: set[str] = set()
        current = task
        depth = 0

        # Map owner class name to EntityType
        owner_type = class_to_entity_type(owner_class)

        while depth < max_depth:
            # Check for circular reference
            if current.gid in visited:
                logger.error(
                    "cascade_loop_detected",
                    extra={
                        "task_gid": task.gid,
                        "field_name": field_def.name,
                        "visited_gids": list(visited),
                    },
                )
                return None

            visited.add(current.gid)

            # Check if we've reached the owner entity type
            detection_result = detect_entity_type(current)
            current_type = detection_result.entity_type

            if current_type == owner_type:
                # Found the owner entity - extract field value
                # Per TDD-WS3: Use get_field_value to check source_field first
                value = get_field_value(current, field_def)
                logger.debug(
                    "cascade_field_found",
                    extra={
                        "task_gid": task.gid,
                        "field_name": field_def.name,
                        "found_at_gid": current.gid,
                        "depth": depth,
                        "value": value,
                        "detection_method": "entity_type",
                    },
                )
                return value

            # Move to parent
            parent_gid = self._get_parent_gid(current)
            if parent_gid is None:
                # Reached ROOT of parent chain (no more parents)
                # If owner is Business and detection failed, treat ROOT as Business
                # This handles the case where project isn't registered in ProjectTypeRegistry
                if owner_type == EntityType.BUSINESS:
                    # Per TDD-WS3: Use get_field_value to check source_field first
                    value = get_field_value(current, field_def)
                    if value is not None:
                        logger.debug(
                            "cascade_field_found_at_root",
                            extra={
                                "task_gid": task.gid,
                                "field_name": field_def.name,
                                "root_gid": current.gid,
                                "depth": depth,
                                "value": value,
                                "detection_method": "root_fallback",
                            },
                        )
                        return value

                logger.debug(
                    "cascade_chain_exhausted",
                    extra={
                        "task_gid": task.gid,
                        "field_name": field_def.name,
                        "root_gid": current.gid,
                        "depth": depth,
                        "owner_type": owner_type.value,
                    },
                )
                return None

            # Fetch parent task (use cache if available)
            parent = await self._fetch_parent_async(parent_gid)
            if parent is None:
                logger.warning(
                    "cascade_parent_fetch_failed",
                    extra={
                        "task_gid": task.gid,
                        "field_name": field_def.name,
                        "parent_gid": parent_gid,
                    },
                )
                return None

            current = parent
            depth += 1

        # Max depth exceeded
        logger.info(
            "cascade_max_depth_exceeded",
            extra={
                "task_gid": task.gid,
                "field_name": field_def.name,
                "max_depth": max_depth,
            },
        )
        return None

    async def warm_parents(
        self,
        tasks: list[Task],
        max_depth: int = 5,
    ) -> None:
        """Pre-fetch all parent chains for a batch of tasks.

        Per TDD-GID-RESOLUTION-SERVICE: Collects all parent GIDs from tasks
        and fetches them in batch using HierarchyAwareResolver, populating
        the local cache. Subsequent resolve_async calls will use cached parents.

        Args:
            tasks: Tasks to pre-fetch parent chains for.
            max_depth: Maximum depth for ancestor traversal (default 5).

        Example:
            >>> await resolver.warm_parents(tasks)
            >>> for task in tasks:
            ...     value = await resolver.resolve_async(task, "Office Phone")
        """
        # Collect all parent GIDs from tasks
        parent_gids: set[str] = set()
        for task in tasks:
            parent_gid = self._get_parent_gid(task)
            if parent_gid is not None:
                parent_gids.add(parent_gid)

        if not parent_gids:
            logger.debug("warm_parents_no_parents", extra={"task_count": len(tasks)})
            return

        # Get or create hierarchy resolver
        hierarchy_resolver = self._get_hierarchy_resolver()

        # Fetch all parents with their ancestor chains
        logger.info(
            "warm_parents_start",
            extra={
                "task_count": len(tasks),
                "parent_gid_count": len(parent_gids),
                "max_depth": max_depth,
            },
        )

        assert hierarchy_resolver is not None  # Already checked above
        resolved = await hierarchy_resolver.resolve_with_ancestors(
            keys=parent_gids,
            max_depth=max_depth,
        )

        # Populate local cache (filter out errors)
        for gid, task_or_error in resolved.items():
            if not hasattr(task_or_error, "key"):  # Not a ResolveError
                self._parent_cache[gid] = task_or_error

        logger.info(
            "warm_parents_complete",
            extra={
                "requested": len(parent_gids),
                "cached": len(self._parent_cache),
            },
        )

    def _get_hierarchy_resolver(self) -> Any | None:
        """Get or create hierarchy resolver for batch parent fetching.

        Per TDD-GID-RESOLUTION-SERVICE: Lazy initialization of hierarchy
        resolver with concurrency control.

        Returns:
            HierarchyAwareResolver configured with TaskParentFetcher,
            or None if HierarchyAwareResolver is not available.
        """
        if HierarchyAwareResolver is None:
            return None
        if self._hierarchy_resolver is None:
            fetcher = TaskParentFetcher(self._client)
            self._hierarchy_resolver = HierarchyAwareResolver(fetcher=fetcher)
        return self._hierarchy_resolver

    async def _fetch_parent_async(self, parent_gid: str) -> Task | None:
        """Fetch parent task from cache, cascade plugin, or API.

        Per TDD-GID-RESOLUTION-SERVICE: First checks local parent cache
        (populated by warm_parents), then falls back to cascade plugin
        or direct API call.

        Args:
            parent_gid: GID of parent task to fetch.

        Returns:
            Parent Task if found, None on error.
        """
        # Per TDD-GID-RESOLUTION-SERVICE: Check local cache first
        if parent_gid in self._parent_cache:
            logger.debug(
                "cascade_parent_cache_hit",
                extra={"parent_gid": parent_gid},
            )
            return self._parent_cache[parent_gid]

        # If cascade_plugin is configured, delegate to it
        if self._cascade_plugin is not None:
            # Cascade plugin handles its own caching
            try:
                logger.debug(
                    "cascade_parent_fetch_via_plugin",
                    extra={"parent_gid": parent_gid},
                )
                parent = await self._client.tasks.get_async(
                    parent_gid,
                    opt_fields=list(STANDARD_TASK_OPT_FIELDS),
                )
                # Cache for future lookups
                if parent is not None:
                    self._parent_cache[parent_gid] = parent
                return parent
            except S3_TRANSPORT_ERRORS as e:
                logger.warning(
                    "cascade_parent_fetch_error",
                    extra={"parent_gid": parent_gid, "error": str(e)},
                )
                return None

        # No cascade_plugin - use hierarchy resolver for on-demand fetch
        hierarchy_resolver = self._get_hierarchy_resolver()
        if hierarchy_resolver is None:
            return None
        try:
            logger.debug(
                "cascade_parent_fetch_via_resolver",
                extra={"parent_gid": parent_gid},
            )
            resolved = await hierarchy_resolver.resolve_batch(keys={parent_gid})
            fetched_parent: Task | None = resolved.get(parent_gid)
            if fetched_parent is not None:
                self._parent_cache[parent_gid] = fetched_parent
            return fetched_parent
        except S3_TRANSPORT_ERRORS as e:
            logger.warning(
                "cascade_parent_fetch_error",
                extra={"parent_gid": parent_gid, "error": str(e)},
            )
            return None

    def get_cache_size(self) -> int:
        """Get the number of cached parent tasks.

        Returns:
            Number of tasks in the parent cache.
        """
        return len(self._parent_cache)

    def _get_parent_gid(self, task: Task) -> str | None:
        """Extract parent GID from task.

        Args:
            task: Task to get parent GID from.

        Returns:
            Parent GID if available, None otherwise.
        """
        if task.parent is None:
            return None
        return task.parent.gid
