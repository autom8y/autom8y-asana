"""Builder package for schema-driven DataFrame construction.

Per TDD-0009 Phase 4: Provides builders that transform Asana tasks
into typed Polars DataFrames using schema-driven extraction.

Per TDD-WATERMARK-CACHE Phase 1: Adds parallel section fetch support.

Per TDD-DATAFRAME-BUILDER-WATERMARK-001: Adds ProgressiveProjectBuilder with
incremental watermark-based filtering.

Public API:
    - DataFrameBuilder: Abstract base with lazy/eager evaluation
    - ProgressiveProjectBuilder: Progressive builder with S3 persistence and incremental support
    - SectionDataFrameBuilder: Section-scoped extraction with project context
    - LAZY_THRESHOLD: Default threshold for automatic lazy evaluation (100)
    - BASE_OPT_FIELDS: Consolidated opt_fields for task fetching
    - ParallelSectionFetcher: Coordinates parallel task fetching across sections
    - FetchResult: Result container for parallel fetch operations
    - ParallelFetchError: Error raised when parallel fetch fails

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
    >>> result.dataframe.shape
    (500, 23)
"""

from __future__ import annotations

from autom8_asana.dataframes.builders.base import (
    LAZY_THRESHOLD,
    DataFrameBuilder,
)
from autom8_asana.dataframes.builders.build_result import (
    BuildQuality,
    BuildResult,
    BuildStatus,
    SectionOutcome,
    SectionResult,
)
from autom8_asana.dataframes.builders.fields import BASE_OPT_FIELDS
from autom8_asana.dataframes.builders.parallel_fetch import (
    FetchResult,
    ParallelFetchError,
    ParallelSectionFetcher,
)
from autom8_asana.dataframes.builders.progressive import (
    ProgressiveProjectBuilder,
)
from autom8_asana.dataframes.builders.section import SectionDataFrameBuilder

__all__ = [
    # Constants
    "LAZY_THRESHOLD",
    "BASE_OPT_FIELDS",
    # Abstract base
    "DataFrameBuilder",
    # Concrete builders
    "ProgressiveProjectBuilder",
    "SectionDataFrameBuilder",
    # Build result types (C2)
    "BuildResult",
    "BuildStatus",
    "BuildQuality",
    "SectionResult",
    "SectionOutcome",
    # Parallel fetch
    "FetchResult",
    "ParallelFetchError",
    "ParallelSectionFetcher",
]
