"""Builder package for schema-driven DataFrame construction.

Per TDD-0009 Phase 4: Provides builders that transform Asana tasks
into typed Polars DataFrames using schema-driven extraction.

Per TDD-WATERMARK-CACHE Phase 1: Adds parallel section fetch support.

Public API:
    - DataFrameBuilder: Abstract base with lazy/eager evaluation
    - ProjectDataFrameBuilder: Project-scoped extraction with section filtering
    - SectionDataFrameBuilder: Section-scoped extraction with project context
    - LAZY_THRESHOLD: Default threshold for automatic lazy evaluation (100)
    - ParallelSectionFetcher: Coordinates parallel task fetching across sections
    - FetchResult: Result container for parallel fetch operations
    - ParallelFetchError: Error raised when parallel fetch fails

Example:
    >>> from autom8_asana.dataframes.builders import ProjectDataFrameBuilder
    >>> from autom8_asana.dataframes.schemas import UNIT_SCHEMA
    >>> from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
    >>>
    >>> resolver = DefaultCustomFieldResolver()
    >>> builder = ProjectDataFrameBuilder(
    ...     project=project,
    ...     task_type="Unit",
    ...     schema=UNIT_SCHEMA,
    ...     resolver=resolver,
    ... )
    >>> df = builder.build()
    >>> df.shape
    (500, 23)

Example (parallel fetch):
    >>> df = await builder.build_with_parallel_fetch_async(client)
"""

from autom8_asana.dataframes.builders.base import (
    LAZY_THRESHOLD,
    DataFrameBuilder,
)
from autom8_asana.dataframes.builders.parallel_fetch import (
    FetchResult,
    ParallelFetchError,
    ParallelSectionFetcher,
)
from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
from autom8_asana.dataframes.builders.section import SectionDataFrameBuilder

__all__ = [
    # Constants
    "LAZY_THRESHOLD",
    # Abstract base
    "DataFrameBuilder",
    # Concrete builders
    "ProjectDataFrameBuilder",
    "SectionDataFrameBuilder",
    # Parallel fetch
    "FetchResult",
    "ParallelFetchError",
    "ParallelSectionFetcher",
]
