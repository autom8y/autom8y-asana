"""Section model for Asana API.

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


class Section(AsanaResource):
    """Asana Section resource model.

    Sections organize tasks within projects. Each section belongs to
    exactly one project.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> section = Section.model_validate(api_response)
        >>> print(f"Section '{section.name}' in project {section.project.gid}")
    """

    # Core identification
    resource_type: str | None = Field(default="section")

    # Basic section fields
    name: str | None = None

    # Relationships - typed with NameGid
    project: NameGid | None = None

    # Metadata
    created_at: str | None = Field(
        default=None, description="Created datetime (ISO 8601)"
    )

    # Tasks attribute for DataFrame building (populated externally)
    tasks: list[Any] | None = Field(default=None, exclude=True)

    def to_dataframe(
        self,
        task_type: str = "*",
        resolver: CustomFieldResolver | None = None,
        cache_integration: DataFrameCacheIntegration | None = None,
        use_cache: bool = True,
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        """Generate typed DataFrame from section tasks.

        Per TDD-0009 Phase 5: Public API for DataFrame extraction.

        Args:
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

        Example:
            >>> df = section.to_dataframe(task_type="Unit")
            >>> df.columns
            ['gid', 'name', 'type', 'mrr', ...]
        """
        return asyncio.run(
            self.to_dataframe_async(
                task_type=task_type,
                resolver=resolver,
                cache_integration=cache_integration,
                use_cache=use_cache,
                lazy=lazy,
            )
        )

    async def to_dataframe_async(
        self,
        task_type: str = "*",
        resolver: CustomFieldResolver | None = None,
        cache_integration: DataFrameCacheIntegration | None = None,
        use_cache: bool = True,
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        """Async variant of to_dataframe().

        Per TDD-0009 Phase 5: Async public API for DataFrame extraction.

        Args:
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

        Example:
            >>> df = await section.to_dataframe_async(task_type="Unit")
            >>> df.columns
            ['gid', 'name', 'type', 'mrr', ...]
        """
        from autom8_asana.dataframes.builders.section import SectionDataFrameBuilder
        from autom8_asana.dataframes.models.registry import SchemaRegistry

        schema = SchemaRegistry.get_instance().get_schema(task_type)
        builder = SectionDataFrameBuilder(
            section=self,
            task_type=task_type,
            schema=schema,
            resolver=resolver,
            cache_integration=cache_integration if use_cache else None,
        )
        return await builder.build_async(lazy=lazy, use_cache=use_cache)
