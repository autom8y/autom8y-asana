"""Project model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0002/ADR-0006: Uses NameGid for typed resource references.
Per TDD-0009 Phase 5: Adds to_dataframe() public API methods.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import polars as pl
from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid

if TYPE_CHECKING:
    from autom8_asana.dataframes.cache_integration import DataFrameCacheIntegration
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver


class Project(AsanaResource):
    """Asana Project resource model.

    Uses NameGid for typed resource references (owner, team, workspace).
    Custom fields and complex nested structures remain as dicts.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> project = Project.model_validate(api_response)
        >>> if project.owner:
        ...     print(f"Owned by {project.owner.name}")
    """

    # Core identification
    resource_type: str | None = Field(default="project")

    # Basic project fields
    name: str | None = None
    notes: str | None = None
    html_notes: str | None = None

    # Status
    archived: bool | None = None
    public: bool | None = None
    color: str | None = Field(
        default=None,
        description="Color of the project (dark-pink, dark-green, etc.)",
    )

    # Dates
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")
    modified_at: str | None = Field(default=None, description="Modified datetime (ISO 8601)")
    due_on: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    due_at: str | None = Field(default=None, description="Due datetime (ISO 8601)")
    start_on: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")

    # Relationships - typed with NameGid
    owner: NameGid | None = None
    team: NameGid | None = None
    workspace: NameGid | None = None
    current_status: NameGid | None = None
    current_status_update: NameGid | None = None

    # Collections
    members: list[NameGid] | None = None
    followers: list[NameGid] | None = None
    custom_fields: list[dict[str, Any]] | None = None  # Complex structure
    custom_field_settings: list[dict[str, Any]] | None = None  # Complex structure

    # Project properties
    default_view: str | None = Field(
        default=None,
        description="Default view (list, board, calendar, timeline)",
    )
    default_access_level: str | None = Field(
        default=None,
        description="Default access for new members (admin, editor, commenter, viewer)",
    )
    minimum_access_level_for_customization: str | None = None
    minimum_access_level_for_sharing: str | None = None
    is_template: bool | None = None
    completed: bool | None = None
    completed_at: str | None = None
    completed_by: NameGid | None = None
    created_from_template: NameGid | None = None

    # Layout-specific
    icon: str | None = None
    permalink_url: str | None = None

    # Privacy
    privacy_setting: str | None = Field(
        default=None,
        description="Privacy setting (public_to_workspace, private_to_team, private)",
    )

    # Tasks attribute for DataFrame building (populated externally)
    tasks: list[Any] | None = Field(default=None, exclude=True)

    def to_dataframe(
        self,
        task_type: str = "*",
        sections: list[str] | None = None,
        resolver: CustomFieldResolver | None = None,
        cache_integration: DataFrameCacheIntegration | None = None,
        use_cache: bool = True,
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        """Generate typed DataFrame from project tasks.

        Per TDD-0009 Phase 5: Public API for DataFrame extraction.

        Args:
            task_type: Task type filter ("Unit", "Contact", "*" for base).
            sections: Optional list of section names to filter by.
            resolver: Optional custom field resolver for dynamic fields.
            cache_integration: Optional cache integration for struc caching.
            use_cache: Whether to use caching (default True, requires cache_integration).
            lazy: If True, force lazy evaluation. If False, force eager.
                  If None, auto-select based on task count threshold.

        Returns:
            Polars DataFrame with extracted task data.

        Raises:
            SchemaNotFoundError: If task_type has no registered schema.
            ExtractionError: If extraction fails for any task.

        Example:
            >>> df = project.to_dataframe(task_type="Unit")
            >>> df.columns
            ['gid', 'name', 'type', 'mrr', ...]
        """
        return asyncio.run(
            self.to_dataframe_async(
                task_type=task_type,
                sections=sections,
                resolver=resolver,
                cache_integration=cache_integration,
                use_cache=use_cache,
                lazy=lazy,
            )
        )

    async def to_dataframe_async(
        self,
        task_type: str = "*",
        sections: list[str] | None = None,
        resolver: CustomFieldResolver | None = None,
        cache_integration: DataFrameCacheIntegration | None = None,
        use_cache: bool = True,
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        """Async variant of to_dataframe().

        Per TDD-0009 Phase 5: Async public API for DataFrame extraction.

        Args:
            task_type: Task type filter ("Unit", "Contact", "*" for base).
            sections: Optional list of section names to filter by.
            resolver: Optional custom field resolver for dynamic fields.
            cache_integration: Optional cache integration for struc caching.
            use_cache: Whether to use caching (default True, requires cache_integration).
            lazy: If True, force lazy evaluation. If False, force eager.
                  If None, auto-select based on task count threshold.

        Returns:
            Polars DataFrame with extracted task data.

        Raises:
            SchemaNotFoundError: If task_type has no registered schema.
            ExtractionError: If extraction fails for any task.

        Example:
            >>> df = await project.to_dataframe_async(task_type="Unit")
            >>> df.columns
            ['gid', 'name', 'type', 'mrr', ...]
        """
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
        from autom8_asana.dataframes.models.registry import SchemaRegistry

        schema = SchemaRegistry.get_instance().get_schema(task_type)
        builder = ProjectDataFrameBuilder(
            project=self,
            task_type=task_type,
            schema=schema,
            sections=sections,
            resolver=resolver,
            cache_integration=cache_integration if use_cache else None,
        )
        return await builder.build_async(lazy=lazy, use_cache=use_cache)

    def struc(
        self,
        task_type: str = "*",
        sections: list[str] | None = None,
        resolver: CustomFieldResolver | None = None,
        cache_integration: DataFrameCacheIntegration | None = None,
        use_cache: bool = True,
        lazy: bool | None = None,
    ) -> Any:
        """[DEPRECATED] Generate pandas DataFrame from project tasks.

        .. deprecated:: 1.0.0
           Use :meth:`to_dataframe()` instead. struc() returns pandas
           DataFrames for backward compatibility, but to_dataframe()
           returns more efficient Polars DataFrames.

        Args:
            task_type: Task type filter ("Unit", "Contact", "*" for base).
            sections: Optional list of section names to filter by.
            resolver: Optional custom field resolver for dynamic fields.
            cache_integration: Optional cache integration for struc caching.
            use_cache: Whether to use caching (default True).
            lazy: If True, force lazy evaluation. If False, force eager.

        Returns:
            Pandas DataFrame with extracted task data.
        """
        from autom8_asana.dataframes.deprecation import struc_project

        return struc_project(
            self,
            task_type=task_type,
            sections=sections,
            resolver=resolver,
            cache_integration=cache_integration,
            use_cache=use_cache,
            lazy=lazy,
        )
