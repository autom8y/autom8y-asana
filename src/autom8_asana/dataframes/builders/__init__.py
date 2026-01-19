"""Builder package for schema-driven DataFrame construction.

Per TDD-0009 Phase 4: Provides builders that transform Asana tasks
into typed Polars DataFrames using schema-driven extraction.

Per TDD-WATERMARK-CACHE Phase 1: Adds parallel section fetch support.

Per TDD-DATAFRAME-BUILDER-WATERMARK-001: Adds ProgressiveProjectBuilder with
incremental watermark-based filtering and compatibility shim.

Public API:
    - DataFrameBuilder: Abstract base with lazy/eager evaluation
    - ProgressiveProjectBuilder: Progressive builder with S3 persistence and incremental support
    - SectionDataFrameBuilder: Section-scoped extraction with project context
    - BuildProgress: Progress reporting dataclass for incremental builds
    - LAZY_THRESHOLD: Default threshold for automatic lazy evaluation (100)
    - BASE_OPT_FIELDS: Consolidated opt_fields for task fetching
    - ParallelSectionFetcher: Coordinates parallel task fetching across sections
    - FetchResult: Result container for parallel fetch operations
    - ParallelFetchError: Error raised when parallel fetch fails
    - create_dataframe_builder: Factory function for creating DataFrame builder

Example:
    >>> from autom8_asana.dataframes.builders import ProgressiveProjectBuilder
    >>> from autom8_asana.dataframes.section_persistence import SectionPersistence
    >>>
    >>> persistence = SectionPersistence()
    >>> builder = ProgressiveProjectBuilder(
    ...     client=client,
    ...     project_gid="123",
    ...     entity_type="offer",
    ...     schema=schema,
    ...     persistence=persistence,
    ... )
    >>> result = await builder.build_progressive_async()
    >>> result.df.shape
    (500, 23)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.dataframes.builders.base import (
    LAZY_THRESHOLD,
    DataFrameBuilder,
)
from autom8_asana.dataframes.builders.fields import BASE_OPT_FIELDS
from autom8_asana.dataframes.builders.parallel_fetch import (
    FetchResult,
    ParallelFetchError,
    ParallelSectionFetcher,
)
from autom8_asana.dataframes.builders.progressive import (
    BuildProgress,
    ProgressiveBuildResult,
    ProgressiveProjectBuilder,
)
from autom8_asana.dataframes.builders.section import SectionDataFrameBuilder


if TYPE_CHECKING:
    from autom8_asana.cache.unified import UnifiedTaskStore
    from autom8_asana.clients.tasks import TasksClient


def create_dataframe_builder(
    tasks_client: "TasksClient",
    unified_store: "UnifiedTaskStore",
    *,
    enable_persistence: bool = True,
) -> ProgressiveProjectBuilder:
    """Factory function for creating DataFrame builder.

    Per TDD-DATAFRAME-BUILDER-WATERMARK-001: Creates a ProgressiveProjectBuilder
    with appropriate configuration for the given parameters.

    This factory simplifies builder creation by automatically configuring
    persistence from environment settings when enable_persistence=True.

    Args:
        tasks_client: TasksClient for API calls.
        unified_store: UnifiedTaskStore for cache integration.
        enable_persistence: If True, configure S3 persistence from environment.
            Defaults to True.

    Returns:
        Configured ProgressiveProjectBuilder instance.

    Example:
        >>> from autom8_asana.dataframes.builders import create_dataframe_builder
        >>> builder = create_dataframe_builder(
        ...     tasks_client=client.tasks,
        ...     unified_store=store,
        ... )
        >>> # Builder is ready for use with build_with_parallel_fetch_async()
    """
    # Note: This factory requires an AsanaClient to be constructed properly.
    # For now, we raise an error since we can't construct a full client from just tasks_client.
    # The caller should use ProgressiveProjectBuilder directly with full configuration.
    raise NotImplementedError(
        "create_dataframe_builder requires full AsanaClient. "
        "Use ProgressiveProjectBuilder directly instead."
    )


__all__ = [
    # Constants
    "LAZY_THRESHOLD",
    "BASE_OPT_FIELDS",
    # Abstract base
    "DataFrameBuilder",
    # Concrete builders
    "ProgressiveProjectBuilder",
    "SectionDataFrameBuilder",
    # Progressive builder results
    "BuildProgress",
    "ProgressiveBuildResult",
    # Parallel fetch
    "FetchResult",
    "ParallelFetchError",
    "ParallelSectionFetcher",
    # Factory
    "create_dataframe_builder",
]
