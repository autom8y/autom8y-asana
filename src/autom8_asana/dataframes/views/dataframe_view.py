"""DataFrame view plugin for materializing DataFrames from unified cache.

Per TDD-UNIFIED-CACHE-001 Component 4: Materializes DataFrames from
UnifiedTaskStore, treating DataFrames as computed views rather than
stored data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger

from autom8_asana.cache.integration.freshness_coordinator import FreshnessMode
from autom8_asana.dataframes.builders.base import gather_with_limit
from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin

# Concurrency limit for parallel row extraction
# Per FR-EXTRACT-001: 50 concurrent extractions balances speed vs memory
ROW_EXTRACTION_CONCURRENCY = 50

if TYPE_CHECKING:
    from autom8_asana.cache.providers.unified import UnifiedTaskStore
    from autom8_asana.dataframes.cache_integration import DataFrameCacheIntegration
    from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver

logger = get_logger(__name__)


class DataFrameViewPlugin:
    """Materializes DataFrames from unified cache.

    Per TDD-UNIFIED-CACHE-001 Goal G2: DataFrames are derived views, not
    stored data. Extraction uses existing BaseExtractor infrastructure.

    This plugin fetches tasks from UnifiedTaskStore and extracts rows
    using the provided schema. Optional row-level caching is available
    as an optimization through DataFrameCacheIntegration.

    Attributes:
        store: UnifiedTaskStore for source task data.
        schema: DataFrameSchema defining extraction columns.
        resolver: Optional CustomFieldResolver for cf:/gid: fields.
        row_cache: Optional DataFrameCacheIntegration for row caching.
        cascade_plugin: CascadeViewPlugin for cascade: field resolution.

    Example:
        >>> plugin = DataFrameViewPlugin(
        ...     schema=UNIT_SCHEMA,
        ...     store=unified_store,
        ...     resolver=resolver,
        ... )
        >>> df = await plugin.materialize_async(
        ...     task_gids=["gid1", "gid2", "gid3"],
        ...     project_gid="project-123",
        ... )
        >>> print(df.shape)
        (3, 12)
    """

    def __init__(
        self,
        schema: DataFrameSchema,
        store: UnifiedTaskStore | None = None,
        resolver: CustomFieldResolver | None = None,
        row_cache: DataFrameCacheIntegration | None = None,
    ) -> None:
        """Initialize view plugin.

        Args:
            schema: Schema for extraction (defines columns and types).
            store: Unified task store for source data (optional for extraction-only use).
            resolver: Custom field resolver for cf:/gid: prefix fields.
            row_cache: Optional row cache for optimization.

        Note:
            When store is None, cascade field resolution will skip parent chain lookup
            and only use local custom field extraction. This mode is intended for
            progressive builders that don't have access to a unified store.
        """
        self._store = store
        self._schema = schema
        self._resolver = resolver
        self._row_cache = row_cache

        # Create cascade plugin for cascade: field resolution (if store available)
        self._cascade_plugin: CascadeViewPlugin | None = None
        if store is not None:
            self._cascade_plugin = CascadeViewPlugin(store=store)

        # Statistics
        self._stats: dict[str, int] = {
            "materialize_calls": 0,
            "tasks_fetched": 0,
            "rows_extracted": 0,
            "row_cache_hits": 0,
            "row_cache_misses": 0,
            "cascade_resolutions": 0,
        }

    @property
    def store(self) -> UnifiedTaskStore | None:
        """Get the unified task store (may be None for extraction-only mode)."""
        return self._store

    @property
    def schema(self) -> DataFrameSchema:
        """Get the extraction schema."""
        return self._schema

    @property
    def resolver(self) -> CustomFieldResolver | None:
        """Get the custom field resolver."""
        return self._resolver

    @property
    def cascade_plugin(self) -> CascadeViewPlugin | None:
        """Get the cascade view plugin."""
        return self._cascade_plugin

    async def materialize_async(
        self,
        task_gids: list[str],
        project_gid: str | None = None,
        freshness: FreshnessMode = FreshnessMode.EVENTUAL,
    ) -> pl.DataFrame:
        """Materialize DataFrame from cached tasks.

        Per TDD-UNIFIED-CACHE-001 Section 5.4:
        1. Fetch tasks from unified store (with freshness)
        2. Extract rows using schema
        3. Optionally cache extracted rows
        4. Build and return DataFrame

        Args:
            task_gids: Task GIDs to include in DataFrame.
            project_gid: Optional project context for section extraction.
            freshness: Freshness mode for cache lookups.

        Returns:
            Polars DataFrame with extracted data.

        Note:
            Tasks not found in cache (or stale with STRICT mode) will
            result in None values. The caller is responsible for fetching
            missing tasks before calling this method.
        """
        self._stats["materialize_calls"] += 1

        if not task_gids:
            return self._build_empty()

        # Fetch tasks from unified store
        assert self._store is not None  # Required for materialization
        task_data_map = await self._store.get_batch_async(
            task_gids, freshness=freshness
        )
        self._stats["tasks_fetched"] += len(task_data_map)

        # Filter to found tasks only
        found_tasks: list[dict[str, Any]] = []
        for gid in task_gids:
            task_data = task_data_map.get(gid)
            if task_data is not None:
                found_tasks.append(task_data)

        if not found_tasks:
            logger.debug(
                "dataframe_view_no_tasks_found",
                extra={
                    "requested_count": len(task_gids),
                    "freshness": freshness.value,
                },
            )
            return self._build_empty()

        # Extract rows
        rows = await self._extract_rows_async(found_tasks, project_gid)
        self._stats["rows_extracted"] += len(rows)

        # Build DataFrame
        if not rows:
            return self._build_empty()

        return pl.DataFrame(rows, schema=self._schema.to_polars_schema())

    async def materialize_incremental_async(
        self,
        existing_df: pl.DataFrame,
        watermark: datetime,
        project_gid: str,
    ) -> tuple[pl.DataFrame, datetime]:
        """Materialize delta updates since watermark.

        Per TDD-UNIFIED-CACHE-001 Section 5.4:
        1. Get changed GIDs from unified store (tasks with modified_at > watermark)
        2. Extract rows for changed tasks
        3. Merge with existing DataFrame
        4. Return updated DataFrame and new watermark

        Args:
            existing_df: Current DataFrame to update.
            watermark: Last sync timestamp.
            project_gid: Project context for filtering.

        Returns:
            Tuple of (updated DataFrame, new watermark).

        Note:
            This is a simplified implementation. Full incremental support
            requires integration with the Asana modified_since API parameter
            which is handled at the ProjectDataFrameBuilder level.
        """
        new_watermark = datetime.now(UTC)

        # For now, this method delegates to the full materialization
        # The real incremental logic involves:
        # 1. API query with modified_since=watermark
        # 2. Cache population with new/updated tasks
        # 3. Row extraction for changed tasks only
        # 4. Merge with existing DataFrame

        # Get all GIDs from existing DataFrame
        if "gid" not in existing_df.columns:
            logger.warning(
                "dataframe_view_incremental_no_gid_column",
                extra={"project_gid": project_gid},
            )
            return existing_df, watermark

        existing_gids = existing_df["gid"].to_list()

        # Materialize fresh data for existing GIDs
        # In full implementation, this would only fetch modified tasks
        updated_df = await self.materialize_async(
            task_gids=existing_gids,
            project_gid=project_gid,
            freshness=FreshnessMode.EVENTUAL,
        )

        return updated_df, new_watermark

    async def _extract_rows_async(
        self,
        tasks: list[dict[str, Any]],
        project_gid: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extract rows from task data dicts with parallel execution.

        Per TDD-UNIFIED-CACHE-001: Uses schema-driven extraction with
        cascade: prefix support via CascadeViewPlugin.

        Per FR-EXTRACT-001: Uses bounded parallelism (50 concurrent) to
        prevent timeout on large task sets. Sequential extraction of 2600+
        tasks at ~40ms each = 104s timeout. Parallel with 50 concurrent:
        2600 / 50 = 52 batches * ~40ms = ~2s.

        Args:
            tasks: List of task data dicts from cache.
            project_gid: Optional project context.

        Returns:
            List of extracted row dicts in original order.
        """
        if not tasks:
            return []

        # Parallel extraction with bounded concurrency
        # gather_with_limit maintains order, so results align with input tasks
        rows = await gather_with_limit(
            [self._extract_row_async(task_data, project_gid) for task_data in tasks],
            max_concurrent=ROW_EXTRACTION_CONCURRENCY,
        )

        return list(rows)

    async def _extract_row_async(
        self,
        task_data: dict[str, Any],
        project_gid: str | None = None,
    ) -> dict[str, Any]:
        """Extract a single row from task data dict.

        Processes schema columns and handles different source types:
        - None: Derived field (method call)
        - cascade: prefix: Cascade resolution via CascadeViewPlugin
        - cf:/gid: prefix: Custom field via resolver
        - Otherwise: Direct attribute access

        Args:
            task_data: Task data dict from cache.
            project_gid: Optional project context.

        Returns:
            Dict mapping column names to extracted values.
        """
        row: dict[str, Any] = {}

        for col in self._schema.columns:
            try:
                value = await self._extract_column_async(task_data, col, project_gid)
                row[col.name] = value
            except (KeyError, ValueError, TypeError) as e:
                # Log and continue with None
                logger.debug(
                    "dataframe_view_extraction_error",
                    extra={
                        "gid": task_data.get("gid"),
                        "column": col.name,
                        "error": str(e),
                    },
                )
                row[col.name] = None

        return row

    async def _extract_column_async(
        self,
        task_data: dict[str, Any],
        col: ColumnDef,
        project_gid: str | None = None,
    ) -> Any:
        """Extract a single column value from task data.

        Args:
            task_data: Task data dict from cache.
            col: Column definition.
            project_gid: Optional project context.

        Returns:
            Extracted value.
        """
        source = col.source

        # Derived field - use extraction method
        if source is None:
            # Per WS3-001: Some derived fields require async resolution
            async_result = await self._extract_derived_field_async(
                task_data, col.name, project_gid
            )
            if async_result is not None:
                return async_result
            return self._extract_derived_field(task_data, col.name, project_gid)

        # Cascade field - use cascade plugin
        if source.lower().startswith("cascade:"):
            field_name = source[8:]  # Strip "cascade:" prefix
            self._stats["cascade_resolutions"] += 1

            # Need to create a Task-like object for cascade resolution
            # For now, use a simplified approach
            return await self._resolve_cascade_from_dict(task_data, field_name)

        # Custom field via resolver
        if source.startswith("cf:") or source.startswith("gid:"):
            return self._extract_custom_field(task_data, source, col)

        # Direct attribute access
        return self._extract_attribute(task_data, source, col)

    async def _resolve_cascade_from_dict(
        self,
        task_data: dict[str, Any],
        field_name: str,
    ) -> Any:
        """Resolve cascade field from task data dict.

        This is a simplified cascade resolution that works directly
        with cached task data dicts.

        Per TDD-unit-cascade-resolution-fix: If parent_chain is empty but
        task has parent.gid, try direct fetch from cache as fallback.

        Args:
            task_data: Task data dict.
            field_name: Field name to resolve.

        Returns:
            Resolved field value or None.
        """
        # First try local extraction (if cascade plugin available)
        if self._cascade_plugin is not None:
            local_value = self._cascade_plugin._get_custom_field_value_from_dict(
                task_data, field_name
            )
            if local_value is not None:
                return local_value
        else:
            # Fallback: try to extract from custom_fields directly
            local_value = self._extract_custom_field_value_from_dict(
                task_data, field_name
            )
            if local_value is not None:
                return local_value

        # If no store available, we can only do local extraction
        if self._store is None:
            logger.debug(
                "cascade_resolution_no_store",
                extra={
                    "task_gid": task_data.get("gid"),
                    "field_name": field_name,
                },
            )
            return None

        # Get parent chain from unified store
        task_gid = task_data.get("gid")
        if not task_gid:
            return None

        parent_chain = await self._store.get_parent_chain_async(task_gid)

        # Per TDD-unit-cascade-resolution-fix Fix 3: Fallback when parent_chain
        # is empty but task has parent.gid - try direct fetch from cache
        if not parent_chain:
            # INFO-level logging when cascade resolution gets empty chain
            parent = task_data.get("parent")
            parent_gid_for_log = (
                parent.get("gid") if parent and isinstance(parent, dict) else None
            )
            logger.info(
                "cascade_resolution_empty_chain",
                extra={
                    "task_gid": task_gid,
                    "field_name": field_name,
                    "parent_gid": parent_gid_for_log,
                },
            )

            if parent and isinstance(parent, dict):
                parent_gid = parent.get("gid")
                if parent_gid:
                    logger.debug(
                        "cascade_fallback_direct_fetch",
                        extra={
                            "task_gid": task_gid,
                            "parent_gid": parent_gid,
                            "field_name": field_name,
                        },
                    )
                    # Try to get parent directly from cache with upgrade
                    from autom8_asana.cache.models.completeness import CompletenessLevel

                    parent_data = await self._store.get_with_upgrade_async(
                        parent_gid,
                        required_level=CompletenessLevel.STANDARD,
                        freshness=FreshnessMode.IMMEDIATE,
                    )
                    if parent_data:
                        parent_chain = [parent_data]

        if not parent_chain:
            return None

        # Search parent chain for field value
        if self._cascade_plugin is None:
            return None
        for parent_data in parent_chain:
            value = self._cascade_plugin._get_custom_field_value_from_dict(
                parent_data, field_name
            )
            if value is not None:
                return value

        return None

    def _extract_custom_field_value_from_dict(
        self, task_data: dict[str, Any], field_name: str
    ) -> Any:
        """Extract custom field value from task dict by name.

        Fallback method used when cascade_plugin is not available.

        Args:
            task_data: Task data dict.
            field_name: Custom field name to look up.

        Returns:
            Field value if found, None otherwise.

        Note:
            Priority order for extraction: number_value > text_value > enum_value >
            multi_enum_values > display_value. This ensures typed values are preferred
            over display_value which may contain formatted strings (e.g., "0%" instead
            of 0.0 for percentage fields).
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
                # Extract value based on field type - prioritize typed values
                # over display_value to avoid type mismatches (e.g., "0%" vs 0.0)
                if cf.get("number_value") is not None:
                    return cf.get("number_value")
                if cf.get("text_value") is not None:
                    return cf.get("text_value")
                if cf.get("enum_value") and isinstance(cf["enum_value"], dict):
                    return cf["enum_value"].get("name")
                if "multi_enum_values" in cf:
                    vals = cf.get("multi_enum_values") or []
                    return [v.get("name") for v in vals if v.get("name")]
                # Fallback to display_value for people/date/unknown fields
                return cf.get("display_value")

        return None

    def _extract_derived_field(
        self,
        task_data: dict[str, Any],
        field_name: str,
        project_gid: str | None = None,
    ) -> Any:
        """Extract derived field value.

        Args:
            task_data: Task data dict.
            field_name: Field name to extract.
            project_gid: Optional project context.

        Returns:
            Extracted value.
        """
        # Standard derived fields
        match field_name:
            case "gid":
                return task_data.get("gid", "")
            case "name":
                return task_data.get("name", "")
            case "type":
                return task_data.get("resource_subtype") or self._schema.task_type
            case "created":
                return self._parse_datetime(task_data.get("created_at"))
            case "last_modified":
                return self._parse_datetime(task_data.get("modified_at"))
            case "due_on" | "date":
                return self._parse_date(task_data.get("due_on"))
            case "is_completed":
                return bool(task_data.get("completed", False))
            case "completed_at":
                return self._parse_datetime(task_data.get("completed_at"))
            case "url":
                gid = task_data.get("gid", "")
                return f"https://app.asana.com/0/0/{gid}"
            case "section":
                return self._extract_section(task_data, project_gid)
            case "tags":
                return self._extract_tags(task_data)
            case _:
                return None

    async def _extract_derived_field_async(
        self,
        task_data: dict[str, Any],
        field_name: str,
        project_gid: str | None = None,
    ) -> Any:
        """Extract derived fields that require async resolution.

        Per WS3-001: The "office" field requires traversing the parent chain
        to the Business ancestor and returning its name. This needs async
        store access for parent chain lookup.

        Args:
            task_data: Task data dict from cache.
            field_name: Field name to extract.
            project_gid: Optional project context.

        Returns:
            Extracted value, or None if field is not async-resolvable
            (caller should fall through to sync _extract_derived_field).
        """
        if field_name == "office":
            return await self._resolve_office_from_dict(task_data)
        return None

    async def _resolve_office_from_dict(
        self,
        task_data: dict[str, Any],
    ) -> str | None:
        """Resolve office name by traversing parent chain to Business ancestor.

        Per WS3-001: The office name is the Business task's name. Traverses
        the parent chain using the unified store, detecting entity types to
        identify the Business ancestor.

        The hierarchy is: Unit -> parent(UnitHolder) -> parent(Business).
        When the Business ancestor is found, returns its "name" field.

        Args:
            task_data: Task data dict from cache.

        Returns:
            Business task name (the office name), or None if not resolvable.
        """
        if self._store is None:
            return None

        task_gid = task_data.get("gid")
        if not task_gid:
            return None

        parent_chain = await self._store.get_parent_chain_async(task_gid)

        # Fallback: try direct parent fetch if chain is empty
        if not parent_chain:
            parent = task_data.get("parent")
            if parent and isinstance(parent, dict):
                parent_gid = parent.get("gid")
                if parent_gid:
                    from autom8_asana.cache.models.completeness import CompletenessLevel

                    parent_data = await self._store.get_with_upgrade_async(
                        parent_gid,
                        required_level=CompletenessLevel.STANDARD,
                        freshness=FreshnessMode.IMMEDIATE,
                    )
                    if parent_data:
                        parent_chain = [parent_data]

        if not parent_chain:
            return None

        # Traverse parent chain to find Business ancestor.
        # The Business is the root of the hierarchy (no parent, or detected as BUSINESS).
        # Use entity type detection when available, fall back to root heuristic.
        from autom8_asana.models.business import (
            EntityType,
            detect_entity_type_from_dict,
        )

        for parent_data in parent_chain:
            entity_type_str = detect_entity_type_from_dict(parent_data)
            if entity_type_str == EntityType.BUSINESS.value:
                return parent_data.get("name")

        # If detection didn't find Business, use root fallback:
        # the last entry in the parent chain (farthest ancestor) is likely Business
        last_parent = parent_chain[-1]
        last_parent_parent = last_parent.get("parent")
        if last_parent_parent is None or (
            isinstance(last_parent_parent, dict)
            and last_parent_parent.get("gid") is None
        ):
            return last_parent.get("name")

        return None

    def _extract_custom_field(
        self,
        task_data: dict[str, Any],
        source: str,
        col: ColumnDef,
    ) -> Any:
        """Extract custom field value.

        Args:
            task_data: Task data dict.
            source: Source string (cf:Name or gid:GID).
            col: Column definition for type coercion.

        Returns:
            Extracted custom field value.
        """
        custom_fields = task_data.get("custom_fields")
        if not custom_fields:
            return None

        # Extract directly from task data when no resolver provided
        # or when task_data is a dict (not a Task object)
        if source.startswith("cf:"):
            field_name = source[3:]  # Strip "cf:" prefix
            raw = self._extract_custom_field_by_name(custom_fields, field_name)
        elif source.startswith("gid:"):
            field_gid = source[4:]  # Strip "gid:" prefix
            raw = self._extract_custom_field_by_gid(custom_fields, field_gid)
        else:
            return None

        if raw is None:
            return None

        # Apply schema-aware type coercion (multi_enum list→string, etc.)
        from autom8_asana.dataframes.resolver.coercer import coerce_value

        return coerce_value(raw, col.dtype)

    def _extract_custom_field_by_name(
        self,
        custom_fields: list[dict[str, Any]],
        field_name: str,
    ) -> Any:
        """Extract custom field value by name.

        Args:
            custom_fields: List of custom field dicts.
            field_name: Field name to find.

        Returns:
            Field value or None.
        """
        normalized = field_name.lower().strip()

        for cf in custom_fields:
            cf_name = cf.get("name", "")
            if cf_name.lower().strip() == normalized:
                return self._extract_cf_value(cf)

        return None

    def _extract_custom_field_by_gid(
        self,
        custom_fields: list[dict[str, Any]],
        field_gid: str,
    ) -> Any:
        """Extract custom field value by GID.

        Args:
            custom_fields: List of custom field dicts.
            field_gid: Field GID to find.

        Returns:
            Field value or None.
        """
        for cf in custom_fields:
            if cf.get("gid") == field_gid:
                return self._extract_cf_value(cf)

        return None

    def _extract_cf_value(self, cf: dict[str, Any]) -> Any:
        """Extract value from custom field dict.

        Args:
            cf: Custom field dict.

        Returns:
            Extracted value.

        Note:
            For unknown resource_subtype, we check typed value fields in order
            (number_value, text_value, enum_value, etc.) before falling back to
            display_value. This handles cases where resource_subtype is missing
            but the field has typed data (e.g., percentage fields with "0%" in
            display_value but 0.0 in number_value).
        """
        resource_subtype = cf.get("resource_subtype")

        match resource_subtype:
            case "text":
                return cf.get("text_value")
            case "number":
                return cf.get("number_value")
            case "enum":
                enum_val = cf.get("enum_value")
                if isinstance(enum_val, dict):
                    return enum_val.get("name")
                return None
            case "multi_enum":
                values = cf.get("multi_enum_values") or []
                return [v.get("name") for v in values if v.get("name")]
            case "date":
                date_val = cf.get("date_value")
                if isinstance(date_val, dict):
                    return date_val.get("date")
                return date_val
            case "people":
                people = cf.get("people_value") or []
                return [p.get("gid") for p in people if p.get("gid")]
            case _:
                # Fallback: check typed value fields before display_value
                # This handles fields with missing/unknown resource_subtype
                # Priority: number > text > enum > display_value
                if cf.get("number_value") is not None:
                    return cf.get("number_value")
                if cf.get("text_value") is not None:
                    return cf.get("text_value")
                enum_val = cf.get("enum_value")
                if enum_val is not None and isinstance(enum_val, dict):
                    return enum_val.get("name")
                return cf.get("display_value")

    def _extract_attribute(
        self,
        task_data: dict[str, Any],
        source: str,
        col: ColumnDef,
    ) -> Any:
        """Extract direct attribute from task data.

        Args:
            task_data: Task data dict.
            source: Attribute name.
            col: Column definition for type handling.

        Returns:
            Extracted value.
        """
        value = task_data.get(source)

        # Handle boolean fields
        if source == "completed":
            return bool(value) if value is not None else False

        # Handle tags
        if source == "tags" and value is not None:
            if isinstance(value, list):
                return [
                    t.get("name")
                    for t in value
                    if isinstance(t, dict) and t.get("name")
                ]
            return []

        # Parse datetime/date based on column dtype
        if value is not None and isinstance(value, str):
            if col.dtype == "Datetime":
                return self._parse_datetime(value)
            elif col.dtype == "Date":
                return self._parse_date(value)

        return value

    def _extract_section(
        self,
        task_data: dict[str, Any],
        project_gid: str | None = None,
    ) -> str | None:
        """Extract section name from task memberships.

        Args:
            task_data: Task data dict.
            project_gid: Optional project GID filter.

        Returns:
            Section name or None.
        """
        memberships = task_data.get("memberships")
        if not memberships:
            return None

        for membership in memberships:
            if not isinstance(membership, dict):
                continue

            # Filter by project if specified
            if project_gid:
                project = membership.get("project", {})
                if isinstance(project, dict) and project.get("gid") != project_gid:
                    continue

            # Extract section name
            section = membership.get("section")
            if section and isinstance(section, dict):
                section_name = section.get("name")
                if section_name is not None:
                    return str(section_name)

        return None

    def _extract_tags(self, task_data: dict[str, Any]) -> list[str]:
        """Extract tag names from task.

        Args:
            task_data: Task data dict.

        Returns:
            List of tag names.
        """
        tags = task_data.get("tags")
        if not tags:
            return []

        result: list[str] = []
        for tag in tags:
            if isinstance(tag, dict):
                name = tag.get("name")
                if name:
                    result.append(name)

        return result

    def _parse_datetime(self, value: str | None) -> datetime | None:
        """Parse ISO datetime string.

        Args:
            value: ISO datetime string or None.

        Returns:
            Parsed datetime or None.
        """
        if not value:
            return None

        # Handle Z suffix
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            return None

    def _parse_date(self, value: str | None) -> Any:
        """Parse date string.

        Args:
            value: Date string (YYYY-MM-DD) or None.

        Returns:
            Parsed date or None.
        """
        if not value:
            return None

        try:
            from datetime import date

            return date.fromisoformat(value)
        except ValueError:
            return None

    def _build_empty(self) -> pl.DataFrame:
        """Build empty DataFrame with schema columns.

        Returns:
            Empty Polars DataFrame with correct schema.
        """
        return pl.DataFrame(schema=self._schema.to_polars_schema())

    def get_stats(self) -> dict[str, int]:
        """Get plugin statistics.

        Returns:
            Dict with materialize_calls, tasks_fetched, rows_extracted, etc.
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics to zero."""
        for key in self._stats:
            self._stats[key] = 0
