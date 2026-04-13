"""DataFrame build service.

Extracts schema resolution, opt_fields management, and DataFrame
construction from route handlers into a testable service.

Per TDD-SERVICE-LAYER-001 v2.0 Phase 4.

Two build paths are deliberately kept separate:
- Project path: async via DataFrameViewPlugin._extract_rows_async()
- Section path: sync via SectionDataFrameBuilder.build()

Both return DataFrameResult as the common abstraction boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

import polars as pl
from autom8y_log import get_logger

from autom8_asana.dataframes.builders import (
    ProgressiveProjectBuilder,
    SectionDataFrameBuilder,
)
from autom8_asana.dataframes.models.registry import SchemaRegistry, get_schema
from autom8_asana.dataframes.section_persistence import create_section_persistence
from autom8_asana.services.errors import EntityNotFoundError, InvalidParameterError

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.dataframes.cache_integration import DataFrameCacheIntegration
    from autom8_asana.dataframes.models.schema import DataFrameSchema
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver
    from autom8_asana.models.project import Project
    from autom8_asana.models.section import Section

logger = get_logger(__name__)


class InvalidSchemaError(InvalidParameterError):
    """Schema name not found in SchemaRegistry.

    Attributes:
        schema_name: The requested schema name.
        valid_schemas: Sorted list of valid schema names.
    """

    def __init__(self, schema_name: str, valid_schemas: list[str]) -> None:
        self.schema_name = schema_name
        self.valid_schemas = valid_schemas
        super().__init__(
            f"Unknown schema '{schema_name}'. Valid schemas: {', '.join(valid_schemas)}"
        )

    @property
    def error_code(self) -> str:
        return "INVALID_SCHEMA"

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error_code,
            "message": self.message,
            "valid_schemas": self.valid_schemas,
        }


@dataclass(frozen=True)
class DataFrameResult:
    """Result of a DataFrame build operation.

    Attributes:
        dataframe: The built Polars DataFrame.
        has_more: Whether more pages are available.
        next_offset: Pagination cursor for the next page, or None.
    """

    dataframe: pl.DataFrame
    has_more: bool
    next_offset: str | None


class DataFrameService:
    """DataFrame build operations.

    Extracts schema resolution, opt_fields construction, and DataFrame
    assembly from route handlers. Handles both project-scoped and
    section-scoped builds via separate methods.

    Thread Safety: Stateless. Safe for concurrent use.
    """

    # Standard opt_fields for task fetch -- single source of truth.
    # Was duplicated in both route endpoints prior to extraction.
    TASK_OPT_FIELDS: ClassVar[list[str]] = [
        "gid",
        "name",
        "resource_type",
        "completed",
        "completed_at",
        "created_at",
        "modified_at",
        "notes",
        "assignee",
        "assignee.name",
        "due_on",
        "due_at",
        "start_on",
        "memberships.section.name",
        "memberships.project.gid",
        # Parent reference for cascade: field resolution.
        # Per TDD-cascade-warming-api-path: Required to build hierarchy
        # for cascade field resolution on the API endpoint path.
        "parent",
        "parent.gid",
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

    def get_schema(self, schema_name: str) -> DataFrameSchema:
        """Resolve schema name to DataFrameSchema.

        Handles normalization, wildcard blocking, and fallback to base.

        Args:
            schema_name: Schema name from API request (case-insensitive).

        Returns:
            DataFrameSchema from registry.

        Raises:
            InvalidSchemaError: Schema name not found or wildcard used directly.
        """
        mapping, valid_schemas = self._get_schema_mapping()

        if not schema_name or not schema_name.strip():
            return get_schema("*")

        normalized = schema_name.lower().strip()

        if normalized == "*":
            raise InvalidSchemaError("*", valid_schemas)

        task_type = mapping.get(normalized)
        if task_type is None:
            raise InvalidSchemaError(schema_name, valid_schemas)

        return get_schema(task_type)

    async def build_project_dataframe(
        self,
        client: AsanaClient,
        project_gid: str,
        schema: DataFrameSchema,
        limit: int,
        offset: str | None,
    ) -> DataFrameResult:
        """Build DataFrame for project tasks.

        Uses DataFrameViewPlugin._extract_rows_async() for async
        extraction with UnifiedTaskStore backing.

        Args:
            client: AsanaClient for API calls.
            project_gid: Asana project GID.
            schema: Resolved DataFrameSchema.
            limit: Page size (already validated by route).
            offset: Pagination cursor.

        Returns:
            DataFrameResult with DataFrame and pagination info.
        """
        from autom8_asana._defaults.cache import InMemoryCacheProvider
        from autom8_asana.cache.providers.unified import UnifiedTaskStore
        from autom8_asana.dataframes import DefaultCustomFieldResolver
        from autom8_asana.dataframes.views.dataframe_view import (
            DataFrameViewPlugin,
        )

        params: dict[str, Any] = {
            "project": project_gid,
            "limit": limit,
            "opt_fields": ",".join(self.TASK_OPT_FIELDS),
        }
        if offset:
            params["offset"] = offset

        data, next_offset = await client._http.get_paginated("/tasks", params=params)

        resolver = DefaultCustomFieldResolver()
        unified_store = UnifiedTaskStore(cache=InMemoryCacheProvider())

        # Warm cascade store for schemas with cascade: columns.
        # Per TDD-cascade-warming-api-path: pre-fetch parent chains
        # so cascade resolution finds ancestor custom field values.
        await self._warm_cascade_store(client, unified_store, data, schema)

        view_plugin = DataFrameViewPlugin(
            schema=schema,
            store=unified_store,
            resolver=resolver,
        )

        from autom8_asana.dataframes.builders.fields import safe_dataframe_construct
        from autom8_asana.dataframes.errors import DataFrameConstructionError

        rows = await view_plugin._extract_rows_async(data, project_gid=project_gid)
        try:
            if rows:
                df = safe_dataframe_construct(rows, schema)
            else:
                df = pl.DataFrame(schema=schema.to_polars_schema())
        except DataFrameConstructionError as exc:
            raise InvalidParameterError(
                f"DataFrame construction failed for schema '{schema.name}': {exc.original_error}"
            ) from exc

        return DataFrameResult(
            dataframe=df,
            has_more=next_offset is not None,
            next_offset=next_offset,
        )

    async def build_section_dataframe(
        self,
        client: AsanaClient,
        section_gid: str,
        schema: DataFrameSchema,
        limit: int,
        offset: str | None,
    ) -> tuple[DataFrameResult, str]:
        """Build DataFrame for section tasks.

        Uses SectionDataFrameBuilder.build() for synchronous extraction
        with Task model conversion.

        Args:
            client: AsanaClient for API calls.
            section_gid: Asana section GID.
            schema: Resolved DataFrameSchema.
            limit: Page size (already validated by route).
            offset: Pagination cursor.

        Returns:
            Tuple of (DataFrameResult, project_gid). The project_gid
            is returned because it is resolved during the section
            fetch and the route may need it for response metadata.

        Raises:
            EntityNotFoundError: Section not found or has no parent project.
        """
        from autom8_asana.dataframes import (
            DefaultCustomFieldResolver,
            SectionDataFrameBuilder,
        )
        from autom8_asana.models.task import Task

        # Fetch section to get parent project GID
        section_data = await client._http.get(
            f"/sections/{section_gid}",
            params={"opt_fields": "project.gid"},
        )
        project_data = section_data.get("project") or {}
        project_gid = project_data.get("gid") if isinstance(project_data, dict) else None

        if not project_gid:
            raise EntityNotFoundError("Section not found or has no parent project")

        # Fetch section tasks
        params: dict[str, Any] = {
            "section": section_gid,
            "limit": limit,
            "opt_fields": ",".join(self.TASK_OPT_FIELDS),
        }
        if offset:
            params["offset"] = offset

        data, next_offset = await client._http.get_paginated("/tasks", params=params)

        # Convert to Task models for SectionDataFrameBuilder
        tasks = [Task.model_validate(t) for t in data]

        resolver = DefaultCustomFieldResolver()

        # SectionDataFrameBuilder expects a section-like object
        section_proxy = _SectionProxy(section_gid, project_gid, tasks)

        from autom8_asana.dataframes.errors import DataFrameConstructionError

        builder = SectionDataFrameBuilder(
            section=section_proxy,
            task_type="*",
            schema=schema,
            resolver=resolver,
        )
        try:
            df = builder.build(tasks=tasks)
        except DataFrameConstructionError as exc:
            raise InvalidParameterError(
                f"DataFrame construction failed for schema '{schema.name}': {exc.original_error}"
            ) from exc

        return (
            DataFrameResult(
                dataframe=df,
                has_more=next_offset is not None,
                next_offset=next_offset,
            ),
            project_gid,
        )

    async def _warm_cascade_store(
        self,
        client: AsanaClient,
        store: Any,
        tasks: list[dict[str, Any]],
        schema: DataFrameSchema,
    ) -> None:
        """Warm cascade store with parent chain data for resolution.

        Pre-populates the per-request ``UnifiedTaskStore`` by storing
        fetched task dicts and triggering hierarchy warming.  Only
        executes when the schema has ``cascade:`` columns.  Bounded by
        ``MAX_CASCADE_PARENTS`` to prevent runaway API calls.

        Per TDD-cascade-warming-api-path.
        """
        MAX_CASCADE_PARENTS = 50

        if not schema.has_cascade_columns():
            return

        if not tasks:
            return

        parent_gids: set[str] = set()
        for task in tasks:
            parent = task.get("parent")
            if parent and isinstance(parent, dict):
                pgid = parent.get("gid")
                if pgid:
                    parent_gids.add(pgid)

        if len(parent_gids) > MAX_CASCADE_PARENTS:
            logger.warning(
                "cascade_warming_parent_limit_exceeded",
                extra={
                    "unique_parents": len(parent_gids),
                    "limit": MAX_CASCADE_PARENTS,
                    "action": "warming_skipped",
                },
            )
            return

        try:
            await store.put_batch_async(
                tasks,
                opt_fields=self.TASK_OPT_FIELDS,
                tasks_client=client.tasks,
                warm_hierarchy=True,
            )
            logger.info(
                "cascade_warming_complete",
                extra={
                    "task_count": len(tasks),
                    "unique_parents": len(parent_gids),
                    "schema": schema.name,
                },
            )
        except Exception:
            logger.warning(
                "cascade_warming_failed",
                extra={
                    "task_count": len(tasks),
                    "schema": schema.name,
                },
                exc_info=True,
            )

    @staticmethod
    def _get_schema_mapping() -> tuple[dict[str, str], list[str]]:
        """Get schema name -> task_type mapping.

        Uses module-level cache for thread-safe lazy initialization.
        See TDD Decision #4 for rationale on keeping module-level cache.
        """
        return _get_schema_mapping_cached()


async def build_for_project(
    project: Project,
    *,
    task_type: str = "*",
    sections: list[str] | None = None,
    resolver: CustomFieldResolver | None = None,
    cache_integration: DataFrameCacheIntegration | None = None,
    use_cache: bool = True,
    lazy: bool | None = None,
    client: AsanaClient,
    max_concurrent_sections: int = 5,
) -> pl.DataFrame:
    """Build a DataFrame from project tasks.

    Extracted from Project.to_dataframe_async() / Project.to_dataframe_parallel_async().
    Preserves identical behavior; moves deferred imports to module level.

    Args:
        project: Project model instance.
        task_type: Task type filter ("Unit", "Contact", "*" for base).
        sections: Optional list of section names to filter by.
        resolver: Optional custom field resolver for dynamic fields.
        cache_integration: Optional cache integration for dataframe caching.
        use_cache: Whether to use caching (maps to resume parameter).
        lazy: If True, force lazy evaluation. If False, force eager.
              If None, auto-select based on task count threshold.
        client: AsanaClient for API calls (required).
        max_concurrent_sections: Max parallel section fetches (default 5).

    Returns:
        Polars DataFrame with extracted task data.

    Raises:
        SchemaNotFoundError: If task_type has no registered schema.
        ExtractionError: If extraction fails for any task.
        ValueError: If client is None.
    """
    schema = get_schema(task_type)
    entity_type = task_type.lower() if task_type != "*" else "task"

    persistence = create_section_persistence()

    async with persistence:
        from autom8_asana.services.gid_lookup import build_gid_index_data

        builder = ProgressiveProjectBuilder(
            client=client,
            project_gid=project.gid,
            entity_type=entity_type,
            schema=schema,
            persistence=persistence,
            resolver=resolver,
            store=client.unified_store,
            max_concurrent_sections=max_concurrent_sections,
            index_builder=build_gid_index_data,
        )

        result = await builder.build_progressive_async(resume=use_cache)
        assert result.dataframe is not None, "Build produced no DataFrame"
        df: pl.DataFrame = result.dataframe
        return df


async def build_for_section(
    section: Section,
    *,
    task_type: str = "*",
    resolver: CustomFieldResolver | None = None,
    cache_integration: DataFrameCacheIntegration | None = None,
    use_cache: bool = True,
    lazy: bool | None = None,
) -> pl.DataFrame:
    """Build a DataFrame from section tasks.

    Extracted from Section.to_dataframe_async().
    Preserves identical behavior; moves deferred imports to module level.

    Args:
        section: Section model instance.
        task_type: Task type filter ("Unit", "Contact", "*" for base).
        resolver: Optional custom field resolver for dynamic fields.
        cache_integration: Optional cache integration for dataframe caching.
        use_cache: Whether to use caching (default True, requires cache_integration).
        lazy: If True, force lazy evaluation. If False, force eager.
              If None, auto-select based on task count threshold.

    Returns:
        Polars DataFrame with extracted task data.

    Raises:
        SchemaNotFoundError: If task_type has no registered schema.
        ExtractionError: If extraction fails for any task.
    """
    schema = get_schema(task_type)
    builder = SectionDataFrameBuilder(
        section=section,
        task_type=task_type,
        schema=schema,
        resolver=resolver,
        cache_integration=cache_integration if use_cache else None,
    )
    return await builder.build_async(lazy=lazy, use_cache=use_cache)


class _SectionProxy:
    """Adapter for SectionDataFrameBuilder's section interface.

    SectionDataFrameBuilder expects a section object with .gid,
    .project (dict with 'gid'), and .tasks attributes. This provides
    that interface from primitive values.

    This replaces the inline class definition that was in dataframes.py.
    """

    __slots__ = ("gid", "project", "tasks")

    def __init__(self, gid: str, project_gid: str, tasks: list[Any]) -> None:
        self.gid = gid
        self.project = {"gid": project_gid}
        self.tasks = tasks


# Module-level cached schema mapping (thread-safe via CPython GIL).
# See TDD Decision #4 for rationale on keeping this at module level.
_schema_mapping_cache: dict[str, str] | None = None
_valid_schemas_cache: list[str] | None = None


def _get_schema_mapping_cached() -> tuple[dict[str, str], list[str]]:
    """Get cached schema mapping, building it if necessary.

    Thread-safe: SchemaRegistry._ensure_initialized() uses locking.
    The global assignment is atomic in CPython.
    """
    global _schema_mapping_cache, _valid_schemas_cache

    if _schema_mapping_cache is None:
        registry = SchemaRegistry.get_instance()
        mapping = {"base": "*"}
        for task_type in registry.list_task_types():
            schema = registry.get_schema(task_type)
            mapping[schema.name] = task_type

        _schema_mapping_cache = mapping
        _valid_schemas_cache = sorted(mapping.keys())

    assert _valid_schemas_cache is not None
    return _schema_mapping_cache, _valid_schemas_cache


def reset_schema_cache() -> None:
    """Reset the module-level schema mapping cache.

    For use in test fixtures when SchemaRegistry is reset.
    """
    global _schema_mapping_cache, _valid_schemas_cache
    _schema_mapping_cache = None
    _valid_schemas_cache = None


__all__ = [
    "DataFrameResult",
    "DataFrameService",
    "InvalidSchemaError",
    "build_for_project",
    "build_for_section",
    "reset_schema_cache",
]
