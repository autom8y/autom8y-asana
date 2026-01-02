"""Abstract DataFrameBuilder for schema-driven DataFrame construction.

Per TDD-0009 Phase 4: Provides base builder with lazy/eager evaluation,
resolver lifecycle management, and extractor factory pattern.

Per TDD-0008 Session 4 Phase 4: Adds cache integration support with
async build methods and cache hit/miss flow.

Per TDD-CASCADING-FIELD-RESOLUTION-001: Added client parameter for
cascade: field resolution in extractors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import polars as pl

from autom8_asana.dataframes.extractors import (
    BaseExtractor,
    ContactExtractor,
    DefaultExtractor,
    UnitExtractor,
)
from autom8_asana.dataframes.models.schema import DataFrameSchema

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.dataframes.cache_integration import DataFrameCacheIntegration
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver
    from autom8_asana.models.task import Task


# Per ADR-0031: Threshold for automatic lazy evaluation selection
LAZY_THRESHOLD = 100


class DataFrameBuilder(ABC):
    """Abstract base builder for schema-driven DataFrame construction.

    Per TDD-0009 Phase 4: Provides template method pattern for building
    typed Polars DataFrames from Asana tasks.

    Per TDD-0008 Session 4 Phase 4: Adds cache integration with async
    build methods and schema-version-aware caching.

    Per TDD-CASCADING-FIELD-RESOLUTION-001: Added client parameter for
    cascade: field resolution in extractors.

    Features:
        - Automatic lazy/eager evaluation selection based on task count
        - Resolver lifecycle management with lazy initialization
        - Extractor factory pattern for type-specific extraction
        - Empty DataFrame handling with schema preservation
        - Optional cache integration with schema version tracking
        - Optional client for cascade: field resolution

    Subclasses implement:
        - get_tasks(): Returns list of tasks to extract
        - _get_project_gid(): Returns project context for section extraction
        - _get_extractor(): Returns appropriate extractor for task type

    Attributes:
        schema: DataFrameSchema defining columns to extract
        resolver: Optional CustomFieldResolver for custom fields
        client: Optional AsanaClient for cascade: field resolution
        lazy_threshold: Task count threshold for automatic lazy selection
        cache_integration: Optional cache integration for struc caching

    Example:
        >>> builder = ProjectDataFrameBuilder(project, "Unit", UNIT_SCHEMA, resolver)
        >>> df = builder.build()
        >>> df.schema
        {'gid': Utf8, 'name': Utf8, 'mrr': Decimal, ...}

        >>> # With caching:
        >>> df = builder.build(use_cache=True)

        >>> # Async with caching:
        >>> df = await builder.build_async(use_cache=True)

        >>> # With cascade: field support:
        >>> builder = ProjectDataFrameBuilder(project, "Unit", UNIT_SCHEMA, resolver, client=client)
        >>> df = await builder.build_async()  # Uses cascade resolution
    """

    def __init__(
        self,
        schema: DataFrameSchema,
        resolver: CustomFieldResolver | None = None,
        lazy_threshold: int = LAZY_THRESHOLD,
        cache_integration: DataFrameCacheIntegration | None = None,
        client: AsanaClient | None = None,
    ) -> None:
        """Initialize builder with schema and optional resolver.

        Args:
            schema: DataFrameSchema defining columns to extract
            resolver: Optional CustomFieldResolver for custom field extraction.
                      Will be initialized lazily on first task if provided.
            lazy_threshold: Task count threshold for automatic lazy evaluation.
                           Defaults to LAZY_THRESHOLD (100).
            cache_integration: Optional cache integration for struc caching.
                              When provided, build() can use cached rows.
            client: Optional AsanaClient for cascade: field resolution.
                   Required if schema contains cascade: sources.
        """
        self._schema = schema
        self._resolver = resolver
        self._lazy_threshold = lazy_threshold
        self._cache_integration = cache_integration
        self._client = client
        self._resolver_initialized = False
        self._extractor: BaseExtractor | None = None

    @property
    def schema(self) -> DataFrameSchema:
        """Get the schema used by this builder."""
        return self._schema

    @property
    def resolver(self) -> CustomFieldResolver | None:
        """Get the custom field resolver."""
        return self._resolver

    @property
    def lazy_threshold(self) -> int:
        """Get the lazy evaluation threshold."""
        return self._lazy_threshold

    @property
    def cache_integration(self) -> DataFrameCacheIntegration | None:
        """Get the cache integration instance."""
        return self._cache_integration

    @property
    def client(self) -> AsanaClient | None:
        """Get the Asana client for cascade resolution."""
        return self._client

    @abstractmethod
    def get_tasks(self) -> list[Task]:
        """Return list of tasks to extract.

        Subclasses implement this to provide tasks from their data source
        (project, section, etc.).

        Returns:
            List of Task objects to extract into DataFrame
        """
        ...

    @abstractmethod
    def _get_project_gid(self) -> str | None:
        """Return project GID for section extraction context.

        Used by extractors to filter task memberships when extracting
        section names.

        Returns:
            Project GID string or None if no project context
        """
        ...

    def build(
        self,
        tasks: list[Task] | None = None,
        lazy: bool | None = None,
        use_cache: bool = False,
    ) -> pl.DataFrame:
        """Build DataFrame from tasks using schema-driven extraction.

        Per FR-PROJECT-001: Primary build method with lazy/eager selection.
        Per TDD-0008 Session 4 Phase 4: Optional cache integration.

        Args:
            tasks: Optional list of tasks. If None, calls get_tasks().
            lazy: Evaluation mode override. None = auto-select based on threshold.
                  True = force lazy, False = force eager.
            use_cache: Whether to use cache integration for row caching.
                      Requires cache_integration to be configured.

        Returns:
            Polars DataFrame with schema-defined columns.

        Example:
            >>> df = builder.build()
            >>> df.columns
            ['gid', 'name', 'type', ...]

            >>> # With caching:
            >>> df = builder.build(use_cache=True)
        """
        # Get tasks if not provided
        if tasks is None:
            tasks = self.get_tasks()

        # Handle empty task list (FR-PROJECT-005)
        if not tasks:
            return self._build_empty()

        # Use cache flow if enabled and configured
        if use_cache and self._cache_integration is not None:
            return self._build_with_cache(tasks, lazy)

        # Determine evaluation mode
        use_lazy = self._should_use_lazy(len(tasks), lazy)

        # Build DataFrame using appropriate mode
        if use_lazy:
            return self._build_lazy(tasks)
        else:
            return self._build_eager(tasks)

    async def build_async(
        self,
        tasks: list[Task] | None = None,
        lazy: bool | None = None,
        use_cache: bool = False,
    ) -> pl.DataFrame:
        """Build DataFrame asynchronously with cache support.

        Per TDD-0008 Session 4 Phase 4: Async build with cache integration.

        Args:
            tasks: Optional list of tasks. If None, calls get_tasks().
            lazy: Evaluation mode override. None = auto-select based on threshold.
                  True = force lazy, False = force eager.
            use_cache: Whether to use cache integration for row caching.

        Returns:
            Polars DataFrame with schema-defined columns.

        Example:
            >>> df = await builder.build_async(use_cache=True)
        """
        # Get tasks if not provided
        if tasks is None:
            tasks = self.get_tasks()

        # Handle empty task list
        if not tasks:
            return self._build_empty()

        # Use async cache flow if enabled and configured
        if use_cache and self._cache_integration is not None:
            return await self._build_with_cache_async(tasks, lazy)

        # Non-cached build (sync code wrapped)
        use_lazy = self._should_use_lazy(len(tasks), lazy)

        if use_lazy:
            return self._build_lazy(tasks)
        else:
            return self._build_eager(tasks)

    def _ensure_resolver_initialized(self, task: Task) -> None:
        """Initialize resolver with task's custom fields if not already done.

        Per TDD-0009: Resolver is initialized lazily on first task to build
        the name->GID index from the task's custom_fields list.

        Args:
            task: Task with custom_fields for index building
        """
        if self._resolver is None:
            return

        if self._resolver_initialized:
            return

        # Build index from first task's custom fields
        if task.custom_fields:
            # Convert list[dict] to list[CustomField] if needed
            from autom8_asana.models.custom_field import CustomField

            custom_fields = [
                CustomField.model_validate(cf) if isinstance(cf, dict) else cf
                for cf in task.custom_fields
            ]
            self._resolver.build_index(custom_fields)

        self._resolver_initialized = True

    def _should_use_lazy(self, task_count: int, lazy: bool | None) -> bool:
        """Determine whether to use lazy evaluation.

        Per ADR-0031: Auto-select based on threshold (100 tasks),
        with explicit override support.

        Args:
            task_count: Number of tasks to process
            lazy: Override value. None = auto-select.

        Returns:
            True if lazy evaluation should be used
        """
        if lazy is not None:
            return lazy
        return task_count > self._lazy_threshold

    def _build_empty(self) -> pl.DataFrame:
        """Build empty DataFrame with schema-defined columns.

        Per FR-PROJECT-005: Returns empty DataFrame preserving schema
        when no tasks match filters.

        Returns:
            Empty Polars DataFrame with correct schema
        """
        return pl.DataFrame(schema=self._schema.to_polars_schema())

    def _build_eager(self, tasks: list[Task]) -> pl.DataFrame:
        """Build DataFrame using eager evaluation.

        Per ADR-0031: Used for small datasets (<=100 tasks by default).
        Extracts all rows to list[dict] then constructs DataFrame.

        Args:
            tasks: List of tasks to extract

        Returns:
            Polars DataFrame with extracted data
        """
        rows = [self._extract_row(task) for task in tasks]
        return pl.DataFrame(rows, schema=self._schema.to_polars_schema())

    def _build_lazy(self, tasks: list[Task]) -> pl.DataFrame:
        """Build DataFrame using lazy evaluation.

        Per ADR-0031: Used for large datasets (>100 tasks by default).
        Constructs LazyFrame then collects, allowing query optimization.

        Args:
            tasks: List of tasks to extract

        Returns:
            Polars DataFrame with extracted data (collected from LazyFrame)
        """
        rows = [self._extract_row(task) for task in tasks]
        lazy_frame = pl.LazyFrame(rows, schema=self._schema.to_polars_schema())
        return lazy_frame.collect()

    def _extract_row(self, task: Task) -> dict[str, Any]:
        """Extract a single row from a task.

        Handles resolver initialization on first call and delegates
        to the extractor for actual field extraction.

        Note: This sync method cannot handle cascade: sources.
        Use _extract_row_async() for schemas with cascade: fields.

        Args:
            task: Task to extract data from

        Returns:
            Dict mapping column names to extracted values
        """
        # Initialize resolver on first task
        self._ensure_resolver_initialized(task)

        # Get or create extractor
        if self._extractor is None:
            self._extractor = self._get_extractor()

        # Extract row using extractor
        project_gid = self._get_project_gid()
        row = self._extractor.extract(task, project_gid)

        return row.to_dict()

    async def _extract_row_async(self, task: Task) -> dict[str, Any]:
        """Extract a single row from a task asynchronously.

        Per TDD-CASCADING-FIELD-RESOLUTION-001: Async extraction supporting
        cascade: prefix for parent chain traversal.

        Handles resolver initialization on first call and delegates
        to the extractor's async extraction method.

        Args:
            task: Task to extract data from

        Returns:
            Dict mapping column names to extracted values
        """
        # Initialize resolver on first task
        self._ensure_resolver_initialized(task)

        # Get or create extractor
        if self._extractor is None:
            self._extractor = self._get_extractor()

        # Extract row using async extractor method
        project_gid = self._get_project_gid()
        row = await self._extractor.extract_async(task, project_gid)

        return row.to_dict()

    @abstractmethod
    def _get_extractor(self) -> BaseExtractor:
        """Return appropriate extractor for the task type.

        Subclasses implement this to create type-specific extractors
        based on their task_type configuration.

        Returns:
            BaseExtractor subclass instance (UnitExtractor, ContactExtractor, etc.)
        """
        ...

    def _create_extractor(self, task_type: str) -> BaseExtractor:
        """Factory method for creating type-specific extractors.

        Per TDD-0009: Creates extractor based on task type string.
        Per TDD-CASCADING-FIELD-RESOLUTION-001: Passes client for cascade: support.

        Subclasses can override for custom extractor selection logic.

        Args:
            task_type: Task type identifier ("Unit", "Contact", etc.)

        Returns:
            Appropriate BaseExtractor subclass instance

        Raises:
            SchemaNotFoundError: If no extractor exists for task_type
        """
        match task_type:
            case "Unit":
                return UnitExtractor(self._schema, self._resolver, client=self._client)
            case "Contact":
                return ContactExtractor(self._schema, self._resolver, client=self._client)
            case "*":
                return DefaultExtractor(self._schema, self._resolver, client=self._client)
            case _:
                # For unknown types, fall back to DefaultExtractor
                # This matches SchemaRegistry's fallback to BASE_SCHEMA
                return DefaultExtractor(self._schema, self._resolver, client=self._client)

    # =========================================================================
    # Cache Integration Methods
    # =========================================================================

    def _build_with_cache(
        self,
        tasks: list[Task],
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        """Build DataFrame with cache integration (sync).

        Per TDD-0008 Session 4 Phase 4: Cache-aware build flow.

        Flow:
        1. Check cache for each task row
        2. Extract rows for cache misses
        3. Cache newly extracted rows
        4. Build DataFrame from all rows

        Args:
            tasks: List of tasks to process.
            lazy: Evaluation mode override.

        Returns:
            Polars DataFrame with extracted data.
        """
        import asyncio

        return asyncio.run(self._build_with_cache_async(tasks, lazy))

    async def _build_with_cache_async(
        self,
        tasks: list[Task],
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        """Build DataFrame with cache integration (async).

        Per TDD-0008 Session 4 Phase 4: Async cache-aware build flow.

        Args:
            tasks: List of tasks to process.
            lazy: Evaluation mode override.

        Returns:
            Polars DataFrame with extracted data.
        """
        if self._cache_integration is None:
            # Fallback to non-cached build
            use_lazy = self._should_use_lazy(len(tasks), lazy)
            return self._build_lazy(tasks) if use_lazy else self._build_eager(tasks)

        project_gid = self._get_project_gid()
        schema_version = self._schema.version
        rows: list[dict[str, Any]] = []
        rows_to_cache: list[tuple[str, str, dict[str, Any], datetime | str]] = []

        for task in tasks:
            task_gid = task.gid
            task_modified_at = getattr(task, "modified_at", None)

            # Determine project_gid for this task
            task_project_gid = project_gid
            if task_project_gid is None:
                # Try to get from task memberships
                task_project_gid = self._get_task_project_gid(task)

            if task_project_gid is None:
                # Cannot cache without project context, extract directly
                # Per TDD-CASCADING-FIELD-RESOLUTION-001: Use async for cascade: sources
                row = await self._extract_row_async(task)
                rows.append(row)
                continue

            # Try to get from cache
            cached_row = await self._cache_integration.get_cached_row_async(
                task_gid=task_gid,
                project_gid=task_project_gid,
                schema_version=schema_version,
                current_modified_at=task_modified_at,
            )

            if cached_row is not None:
                # Cache hit - use cached data
                rows.append(cached_row.data)
            else:
                # Cache miss - extract and queue for caching
                # Per TDD-CASCADING-FIELD-RESOLUTION-001: Use async for cascade: sources
                row = await self._extract_row_async(task)
                rows.append(row)

                # Queue for caching if we have modified_at
                if task_modified_at is not None:
                    rows_to_cache.append(
                        (task_gid, task_project_gid, row, task_modified_at)
                    )

        # Cache newly extracted rows in batch
        if rows_to_cache:
            await self._cache_integration.cache_batch_async(
                rows=rows_to_cache,
                schema_version=schema_version,
            )

        # Build DataFrame
        if not rows:
            return self._build_empty()

        use_lazy = self._should_use_lazy(len(rows), lazy)
        if use_lazy:
            lazy_frame = pl.LazyFrame(rows, schema=self._schema.to_polars_schema())
            return lazy_frame.collect()
        else:
            return pl.DataFrame(rows, schema=self._schema.to_polars_schema())

    def _get_task_project_gid(self, task: Task) -> str | None:
        """Extract project GID from task memberships.

        Args:
            task: Task to extract project GID from.

        Returns:
            First project GID from memberships, or None.
        """
        if not task.memberships:
            return None

        for membership in task.memberships:
            project = membership.get("project", {})
            if isinstance(project, dict):
                project_gid = project.get("gid")
                if project_gid:
                    return str(project_gid)

        return None

    # =========================================================================
    # Export Methods
    # =========================================================================

    def to_parquet(self, path: str | Path, **kwargs: Any) -> Path:
        """Export DataFrame to Parquet file.

        Builds the DataFrame using current settings and writes it to a
        Parquet file at the specified path.

        Args:
            path: Output file path (string or Path object)
            **kwargs: Additional arguments passed to Polars write_parquet.
                     Common options include:
                     - compression: str ("zstd", "lz4", "snappy", "gzip", "uncompressed")
                     - compression_level: int
                     - statistics: bool

        Returns:
            Path to the written file

        Example:
            >>> builder = ProjectDataFrameBuilder(project, "Unit", UNIT_SCHEMA)
            >>> output_path = builder.to_parquet("output/units.parquet")
            >>> output_path
            PosixPath('output/units.parquet')
        """
        df = self.build()
        output_path = Path(path)
        df.write_parquet(output_path, **kwargs)
        return output_path

    def to_csv(self, path: str | Path, **kwargs: Any) -> Path:
        """Export DataFrame to CSV file.

        Builds the DataFrame using current settings and writes it to a
        CSV file at the specified path.

        Args:
            path: Output file path (string or Path object)
            **kwargs: Additional arguments passed to Polars write_csv.
                     Common options include:
                     - separator: str (default ",")
                     - include_header: bool (default True)
                     - null_value: str
                     - quote_char: str

        Returns:
            Path to the written file

        Example:
            >>> builder = ProjectDataFrameBuilder(project, "Unit", UNIT_SCHEMA)
            >>> output_path = builder.to_csv("output/units.csv")
            >>> output_path
            PosixPath('output/units.csv')
        """
        df = self.build()
        output_path = Path(path)
        df.write_csv(output_path, **kwargs)
        return output_path

    def to_json(self, path: str | Path, **kwargs: Any) -> Path:
        """Export DataFrame to JSON file.

        Builds the DataFrame using current settings and writes it to a
        JSON file at the specified path.

        Args:
            path: Output file path (string or Path object)
            **kwargs: Additional arguments passed to Polars write_json.
                     Common options include:
                     - row_oriented: bool (default False)

        Returns:
            Path to the written file

        Example:
            >>> builder = ProjectDataFrameBuilder(project, "Unit", UNIT_SCHEMA)
            >>> output_path = builder.to_json("output/units.json")
            >>> output_path
            PosixPath('output/units.json')
        """
        df = self.build()
        output_path = Path(path)
        df.write_json(output_path, **kwargs)
        return output_path
