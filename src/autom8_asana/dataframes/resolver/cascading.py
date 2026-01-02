"""Cascading field resolver for parent chain traversal.

Per TDD-CASCADING-FIELD-RESOLUTION-001: Resolves field values by traversing
the parent task chain, using CASCADING_FIELD_REGISTRY to find field definitions
and respecting CascadingFieldDef rules (target_types, allow_override).

This resolver bridges the DataFrame extraction layer to the business model layer's
CascadingFieldDef system.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from autom8_asana.models.business.detection import EntityType, detect_entity_type
from autom8_asana.models.business.fields import (
    STANDARD_TASK_OPT_FIELDS,
    CascadingFieldDef,
    get_cascading_field,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task


logger = logging.getLogger(__name__)


class CascadingFieldResolver:
    """Resolves field values by traversing parent task chain.

    Uses CASCADING_FIELD_REGISTRY to find field definitions and
    respects CascadingFieldDef rules (target_types, allow_override).

    Per TDD-CASCADING-FIELD-RESOLUTION-001: Bridges DataFrame extraction
    layer to business model layer's CascadingFieldDef system.

    Example:
        >>> resolver = CascadingFieldResolver(client=client)
        >>> # Resolve Office Phone from Business ancestor
        >>> value = await resolver.resolve_async(unit_task, "Office Phone")

    Attributes:
        _client: AsanaClient for fetching parent tasks.
        _parent_cache: Cache of gid -> parent Task for batch efficiency.
    """

    def __init__(self, client: AsanaClient) -> None:
        """Initialize resolver with Asana client.

        Args:
            client: AsanaClient for fetching parent tasks when not cached.
        """
        self._client = client
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
        local_value = self._get_custom_field_value(task, field_def.name)
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

            # Map owner class name to EntityType
            owner_type = self._class_to_entity_type(owner_class)

            if current_type == owner_type:
                # Found the owner entity - extract field value
                value = self._get_custom_field_value(current, field_def.name)
                logger.debug(
                    "cascade_field_found",
                    extra={
                        "task_gid": task.gid,
                        "field_name": field_def.name,
                        "found_at_gid": current.gid,
                        "depth": depth,
                        "value": value,
                    },
                )
                return value

            # Move to parent
            parent_gid = self._get_parent_gid(current)
            if parent_gid is None:
                logger.debug(
                    "cascade_chain_broken",
                    extra={
                        "task_gid": task.gid,
                        "field_name": field_def.name,
                        "stopped_at_gid": current.gid,
                        "depth": depth,
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

    async def _fetch_parent_async(self, parent_gid: str) -> Task | None:
        """Fetch parent task, using cache if available.

        Per FR-CASCADE-RESOLVE-004: Cache fetched parent tasks.

        Args:
            parent_gid: GID of parent task to fetch.

        Returns:
            Parent Task if found, None on error.
        """
        # Check cache first
        if parent_gid in self._parent_cache:
            logger.debug(
                "cascade_parent_fetch",
                extra={"parent_gid": parent_gid, "cache_hit": True},
            )
            return self._parent_cache[parent_gid]

        # Fetch from API
        try:
            logger.debug(
                "cascade_parent_fetch",
                extra={"parent_gid": parent_gid, "cache_hit": False},
            )
            parent = await self._client.tasks.get_async(
                parent_gid,
                opt_fields=list(STANDARD_TASK_OPT_FIELDS),
            )
            # Cache the result
            self._parent_cache[parent_gid] = parent
            return parent
        except Exception as e:
            logger.warning(
                "cascade_parent_fetch_error",
                extra={"parent_gid": parent_gid, "error": str(e)},
            )
            return None

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

    def _get_custom_field_value(self, task: Task, field_name: str) -> Any:
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

    def _class_to_entity_type(self, cls: type) -> EntityType:
        """Map business model class to EntityType enum.

        Args:
            cls: Business model class (e.g., Business, Unit).

        Returns:
            Corresponding EntityType enum value.
        """
        # Map class names to EntityType
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

    def clear_cache(self) -> None:
        """Clear the parent task cache.

        Per FR-CASCADE-RESOLVE-004: Provide cache invalidation for testing.
        """
        self._parent_cache.clear()
        logger.debug("cascade_cache_cleared")

    def get_cache_size(self) -> int:
        """Get current cache size for monitoring.

        Returns:
            Number of cached parent tasks.
        """
        return len(self._parent_cache)
