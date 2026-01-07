"""Cascade view plugin for resolving cascading fields via unified cache.

Per TDD-UNIFIED-CACHE-001 Component 5: Resolves cascading fields using
UnifiedTaskStore for parent chain traversal, replacing the per-instance
_parent_cache in CascadingFieldResolver.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.cache.completeness import CompletenessLevel
# Per TDD-registry-consolidation: Import from package to ensure bootstrap runs
from autom8_asana.models.business import (
    CascadingFieldDef,
    CascadingFieldEntry,
    EntityType,
    detect_entity_type,
    get_cascading_field,
    get_cascading_field_registry,
)

if TYPE_CHECKING:
    from autom8_asana.cache.unified import UnifiedTaskStore
    from autom8_asana.clients.tasks import TasksClient
    from autom8_asana.models.task import Task

logger = get_logger(__name__)


class CascadeViewPlugin:
    """Resolves cascading fields using unified cache.

    Per TDD-UNIFIED-CACHE-001 Goal G3: CascadingFieldResolver uses same
    cache as TaskCacheCoordinator. This plugin replaces the per-instance
    _parent_cache in CascadingFieldResolver.

    Uses UnifiedTaskStore.get_parent_chain_async() for parent traversal,
    ensuring shared cache utilization across all cascade resolutions.

    Attributes:
        store: UnifiedTaskStore for parent chain lookups.
        registry: Cascading field registry (uses default if None).

    Example:
        >>> plugin = CascadeViewPlugin(store=unified_store)
        >>> # Resolve Office Phone from Business ancestor
        >>> value = await plugin.resolve_async(unit_task, "Office Phone")
        >>> print(value)  # "555-123-4567"

        >>> # Prefetch parents for batch efficiency
        >>> await plugin.prefetch_parents_async(unit_tasks)
        >>> for task in unit_tasks:
        ...     value = await plugin.resolve_async(task, "Office Phone")
    """

    def __init__(
        self,
        store: "UnifiedTaskStore",
        registry: dict[str, CascadingFieldEntry] | None = None,
        tasks_client: "TasksClient | None" = None,
    ) -> None:
        """Initialize cascade plugin.

        Args:
            store: Unified task store for parent chain lookups.
            registry: Cascading field registry mapping normalized field names
                     to (owner_class, field_def) tuples. Uses default registry
                     built from Business and Unit CascadingFields if None.
            tasks_client: Optional TasksClient for cache upgrades when parent
                         chain entries have insufficient completeness.
                         Per TDD-CACHE-COMPLETENESS-001 Phase 3.
        """
        self._store = store
        self._registry = registry or get_cascading_field_registry()
        self._tasks_client = tasks_client

        # Statistics
        self._stats: dict[str, int] = {
            "resolve_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "field_found": 0,
            "field_not_found": 0,
            "prefetch_calls": 0,
            "upgrade_count": 0,
        }

    @property
    def store(self) -> "UnifiedTaskStore":
        """Get the unified task store."""
        return self._store

    @property
    def registry(self) -> dict[str, CascadingFieldEntry]:
        """Get the cascading field registry."""
        return self._registry

    async def resolve_async(
        self,
        task: "Task",
        field_name: str,
        max_depth: int = 5,
    ) -> Any:
        """Resolve cascading field value.

        Uses unified store for parent chain traversal. Result is cached
        in unified store for reuse by other resolutions.

        Per TDD-UNIFIED-CACHE-001: Uses store.get_parent_chain_async()
        for efficient parent retrieval from shared cache.

        Args:
            task: Starting task to resolve from.
            field_name: Field to resolve (e.g., "Office Phone").
            max_depth: Maximum parent chain depth (default 5).

        Returns:
            Field value from ancestor, or None if not found.

        Note:
            Returns None if:
            - Field is not in CASCADING_FIELD_REGISTRY
            - max_depth exceeded
            - Parent chain broken (no parent in cache)
            - Field not found in any ancestor
        """
        self._stats["resolve_calls"] += 1

        # Look up field in registry (use plugin's registry or global function)
        normalized_name = field_name.lower().strip()
        result = self._registry.get(normalized_name)
        if result is None:
            # Fallback to global registry function
            result = get_cascading_field(field_name)

        if result is None:
            logger.debug(
                "cascade_field_not_registered",
                extra={"field_name": field_name, "task_gid": task.gid},
            )
            self._stats["field_not_found"] += 1
            return None

        owner_class, field_def = result

        logger.debug(
            "cascade_view_resolve_start",
            extra={
                "task_gid": task.gid,
                "field_name": field_name,
                "owner_class": owner_class.__name__,
            },
        )

        # Check if task has local value and if override is allowed
        local_value = self._get_custom_field_value(task, field_def.name)
        if local_value is not None and field_def.allow_override:
            logger.debug(
                "cascade_view_local_override",
                extra={
                    "task_gid": task.gid,
                    "field_name": field_name,
                    "value": local_value,
                },
            )
            self._stats["field_found"] += 1
            return local_value

        # Traverse parent chain using unified store
        return await self._traverse_parent_chain(
            task=task,
            field_def=field_def,
            owner_class=owner_class,
            max_depth=max_depth,
        )

    async def _traverse_parent_chain(
        self,
        task: "Task",
        field_def: CascadingFieldDef,
        owner_class: type,
        max_depth: int,
    ) -> Any:
        """Traverse parent chain to find cascading field value.

        Per TDD-UNIFIED-CACHE-001: Uses UnifiedTaskStore.get_parent_chain_async()
        for efficient parent retrieval from shared cache.

        Per TDD-CACHE-COMPLETENESS-001 Phase 3: Uses get_with_upgrade_async()
        to ensure parent entries have STANDARD completeness (custom_fields).

        Args:
            task: Starting task.
            field_def: CascadingFieldDef with field configuration.
            owner_class: Entity class that owns this cascading field.
            max_depth: Maximum chain depth.

        Returns:
            Field value if found, None otherwise.
        """
        # Map owner class name to EntityType
        owner_type = self._class_to_entity_type(owner_class)

        # First check the starting task itself
        detection_result = detect_entity_type(task)
        if detection_result.entity_type == owner_type:
            value = self._get_custom_field_value(task, field_def.name)
            if value is not None:
                logger.debug(
                    "cascade_view_field_found_on_task",
                    extra={
                        "task_gid": task.gid,
                        "field_name": field_def.name,
                        "value": value,
                    },
                )
                self._stats["field_found"] += 1
                return value

        # Get parent chain from unified store using completeness-aware method
        # Per TDD-CACHE-COMPLETENESS-001 Section 8.3: Request STANDARD completeness
        parent_chain = await self._get_parent_chain_with_completeness_async(
            task.gid, max_depth=max_depth
        )

        if not parent_chain:
            # No parents in cache
            self._stats["cache_misses"] += 1
            logger.debug(
                "cascade_view_no_parent_chain",
                extra={
                    "task_gid": task.gid,
                    "field_name": field_def.name,
                },
            )
            # Check if starting task is root and owner is Business
            if owner_type == EntityType.BUSINESS:
                value = self._get_custom_field_value(task, field_def.name)
                if value is not None:
                    self._stats["field_found"] += 1
                    return value
            self._stats["field_not_found"] += 1
            return None

        self._stats["cache_hits"] += 1

        # Traverse parent chain looking for owner entity type
        for parent_data in parent_chain:
            # Create minimal task-like object for detection
            # parent_data is a dict from cache
            parent_entity_type = self._detect_entity_type_from_dict(parent_data)

            if parent_entity_type == owner_type:
                # Found the owner entity - extract field value
                value = self._get_custom_field_value_from_dict(
                    parent_data, field_def.name
                )
                if value is not None:
                    logger.debug(
                        "cascade_view_field_found",
                        extra={
                            "task_gid": task.gid,
                            "field_name": field_def.name,
                            "found_at_gid": parent_data.get("gid"),
                            "value": value,
                        },
                    )
                    self._stats["field_found"] += 1
                    return value

        # Check if last parent in chain is root (for Business owner type)
        if owner_type == EntityType.BUSINESS and parent_chain:
            last_parent = parent_chain[-1]
            # If we've reached root of chain, try extracting from it
            if last_parent.get("parent") is None:
                value = self._get_custom_field_value_from_dict(
                    last_parent, field_def.name
                )
                if value is not None:
                    logger.debug(
                        "cascade_view_field_found_at_root",
                        extra={
                            "task_gid": task.gid,
                            "field_name": field_def.name,
                            "root_gid": last_parent.get("gid"),
                            "value": value,
                        },
                    )
                    self._stats["field_found"] += 1
                    return value

        # Field not found
        logger.debug(
            "cascade_view_field_not_found",
            extra={
                "task_gid": task.gid,
                "field_name": field_def.name,
                "chain_length": len(parent_chain),
            },
        )
        self._stats["field_not_found"] += 1
        return None

    async def _get_parent_chain_with_completeness_async(
        self,
        gid: str,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        """Get parent chain with STANDARD completeness.

        Per TDD-CACHE-COMPLETENESS-001 Section 8.3: Ensures parent entries
        have sufficient completeness for custom_fields extraction.

        Uses get_with_upgrade_async() to automatically upgrade entries
        that have insufficient completeness.

        Args:
            gid: Starting task GID.
            max_depth: Maximum chain depth.

        Returns:
            List of parent task dicts with STANDARD completeness.
        """
        # Get hierarchy index to find ancestor GIDs
        hierarchy = self._store.get_hierarchy_index()
        ancestor_gids = hierarchy.get_ancestor_chain(gid, max_depth=max_depth)

        if not ancestor_gids:
            return []

        # Fetch each ancestor with STANDARD completeness
        # Using get_with_upgrade_async for automatic upgrade if needed
        chain: list[dict[str, Any]] = []
        for ancestor_gid in ancestor_gids:
            parent_data = await self._store.get_with_upgrade_async(
                ancestor_gid,
                required_level=CompletenessLevel.STANDARD,
                tasks_client=self._tasks_client,
            )
            if parent_data is not None:
                chain.append(parent_data)
                # Track upgrades in stats
                # Note: upgrade_count is tracked in UnifiedTaskStore, but we
                # also track locally for visibility
            else:
                # Stop at first missing/failed - can't continue chain
                logger.debug(
                    "parent_chain_incomplete_with_upgrade",
                    extra={
                        "gid": gid,
                        "missing_gid": ancestor_gid,
                        "found_count": len(chain),
                    },
                )
                break

        return chain

    async def prefetch_parents_async(
        self,
        tasks: list["Task"],
    ) -> None:
        """Prefetch parent chains for batch efficiency.

        Collects unique parent GIDs across all tasks and ensures they
        are cached in the unified store for efficient resolution.

        Per TDD-UNIFIED-CACHE-001: Optimizes cascade resolution by
        pre-loading parent chain into unified cache.

        Args:
            tasks: Tasks whose parents should be prefetched.

        Note:
            This method populates the UnifiedTaskStore cache with
            parent task data. Subsequent resolve_async() calls will
            benefit from cache hits.
        """
        self._stats["prefetch_calls"] += 1

        if not tasks:
            return

        # Collect unique parent GIDs
        parent_gids: set[str] = set()
        for task in tasks:
            if task.parent and task.parent.gid:
                parent_gids.add(task.parent.gid)

        if not parent_gids:
            logger.debug(
                "cascade_view_prefetch_no_parents",
                extra={"task_count": len(tasks)},
            )
            return

        # Trigger cache population by requesting parent chains
        # This causes the store to fetch any missing parents
        for task in tasks:
            if task.parent and task.parent.gid:
                # Just trigger the cache lookup - don't need the result
                await self._store.get_parent_chain_async(task.gid, max_depth=5)

        logger.debug(
            "cascade_view_prefetch_completed",
            extra={
                "task_count": len(tasks),
                "unique_parents": len(parent_gids),
            },
        )

    def _get_custom_field_value(self, task: "Task", field_name: str) -> Any:
        """Extract custom field value from task by name.

        Args:
            task: Task to extract field from.
            field_name: Custom field name to look up.

        Returns:
            Field value if found, None otherwise.
        """
        if task.custom_fields is None:
            return None

        # Normalize field name for comparison
        normalized_name = field_name.lower().strip()

        for cf in task.custom_fields:
            cf_name = cf.get("name") if isinstance(cf, dict) else getattr(cf, "name", None)
            if cf_name and cf_name.lower().strip() == normalized_name:
                return self._extract_field_value(cf)

        return None

    def _get_custom_field_value_from_dict(
        self, task_data: dict[str, Any], field_name: str
    ) -> Any:
        """Extract custom field value from task dict by name.

        Args:
            task_data: Task data dict (from cache).
            field_name: Custom field name to look up.

        Returns:
            Field value if found, None otherwise.
        """
        custom_fields = task_data.get("custom_fields")
        if not custom_fields:
            return None

        # Normalize field name for comparison
        normalized_name = field_name.lower().strip()

        for cf in custom_fields:
            if not isinstance(cf, dict):
                continue
            cf_name = cf.get("name")
            if cf_name and cf_name.lower().strip() == normalized_name:
                return self._extract_field_value(cf)

        return None

    def _extract_field_value(self, cf_data: dict[str, Any]) -> Any:
        """Extract raw value from custom field data.

        Handles different custom field types (text, number, enum, multi_enum, etc.).

        Args:
            cf_data: Custom field dict from Asana API.

        Returns:
            Extracted value based on resource_subtype.
        """
        if not isinstance(cf_data, dict):
            return None

        resource_subtype = cf_data.get("resource_subtype")

        match resource_subtype:
            case "text":
                return cf_data.get("text_value")
            case "number":
                return cf_data.get("number_value")
            case "enum":
                enum_value = cf_data.get("enum_value")
                if enum_value is None:
                    return None
                if isinstance(enum_value, dict):
                    return enum_value.get("name")
                return getattr(enum_value, "name", None)
            case "multi_enum":
                multi_values = cf_data.get("multi_enum_values") or []
                result: list[str] = []
                for opt in multi_values:
                    if isinstance(opt, dict):
                        name = opt.get("name")
                    else:
                        name = getattr(opt, "name", None)
                    if name:
                        result.append(name)
                return result if result else None
            case "date":
                date_value = cf_data.get("date_value")
                if isinstance(date_value, dict):
                    return date_value.get("date")
                return date_value
            case "people":
                people = cf_data.get("people_value") or []
                gids: list[str] = []
                for p in people:
                    if isinstance(p, dict):
                        gid = p.get("gid")
                    else:
                        gid = getattr(p, "gid", None)
                    if gid:
                        gids.append(gid)
                return gids if gids else None
            case _:
                # Fallback to display_value
                return cf_data.get("display_value")

    def _detect_entity_type_from_dict(self, task_data: dict[str, Any]) -> EntityType:
        """Detect entity type from task dict.

        Simplified detection for cached task data.

        Args:
            task_data: Task data dict from cache.

        Returns:
            EntityType enum value.
        """
        # Simple heuristics based on common patterns
        # Full detection would require more context
        # Root tasks (no parent) are likely Business
        if task_data.get("parent") is None:
            return EntityType.BUSINESS

        # Default to UNKNOWN for cached data
        return EntityType.UNKNOWN

    def _class_to_entity_type(self, cls: type) -> EntityType:
        """Map business model class to EntityType enum.

        Args:
            cls: Business model class (e.g., Business, Unit).

        Returns:
            Corresponding EntityType enum value.
        """
        class_name_map: dict[str, EntityType] = {
            "Business": EntityType.BUSINESS,
            "Unit": EntityType.UNIT,
            "Contact": EntityType.CONTACT,
            "ContactHolder": EntityType.CONTACT_HOLDER,
            "UnitHolder": EntityType.UNIT_HOLDER,
            "LocationHolder": EntityType.LOCATION_HOLDER,
            "OfferHolder": EntityType.OFFER_HOLDER,
            "ProcessHolder": EntityType.PROCESS_HOLDER,
            "Offer": EntityType.OFFER,
            "Process": EntityType.PROCESS,
            "Location": EntityType.LOCATION,
            "Hours": EntityType.HOURS,
        }

        return class_name_map.get(cls.__name__, EntityType.UNKNOWN)

    def get_stats(self) -> dict[str, int]:
        """Get plugin statistics.

        Returns:
            Dict with resolve_calls, cache_hits, cache_misses, etc.
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics to zero."""
        for key in self._stats:
            self._stats[key] = 0
