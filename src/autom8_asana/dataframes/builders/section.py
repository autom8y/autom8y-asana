"""SectionDataFrameBuilder for section-scoped DataFrame construction.

Per TDD-0009 Phase 4: Provides section-level DataFrame building with
project context for cache keys and section extraction.

Per TDD-0008 Session 4 Phase 4: Adds cache integration support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.dataframes.builders.base import LAZY_THRESHOLD, DataFrameBuilder
from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.schema import DataFrameSchema

if TYPE_CHECKING:
    from autom8_asana.dataframes.cache_integration import DataFrameCacheIntegration
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver
    from autom8_asana.models.task import Task

# Type alias for Section - using Any since Section is not defined in this package
# and we want to accept any object with the required attributes
Section = Any


class SectionDataFrameBuilder(DataFrameBuilder):
    """Builder for section-scoped DataFrame extraction.

    Per FR-SECTION-001-005: Section-level extraction with project context
    for proper section name extraction and cache key generation.

    Per TDD-0008 Session 4 Phase 4: Adds cache integration support.

    This builder extracts tasks from a single section within a project,
    using the section's tasks and the parent project's GID for context.

    Attributes:
        section: Section object containing tasks to extract
        task_type: Task type filter ("Unit", "Contact", etc.)

    Example:
        >>> from autom8_asana.dataframes.schemas import UNIT_SCHEMA
        >>> builder = SectionDataFrameBuilder(
        ...     section=section,
        ...     task_type="Unit",
        ...     schema=UNIT_SCHEMA,
        ...     resolver=resolver,
        ... )
        >>> df = builder.build()
        >>> df.columns
        ['gid', 'name', 'type', 'mrr', ...]

        >>> # With caching:
        >>> df = builder.build(use_cache=True)
    """

    def __init__(
        self,
        section: Section,
        task_type: str,
        schema: DataFrameSchema,
        resolver: CustomFieldResolver | None = None,
        lazy_threshold: int = LAZY_THRESHOLD,
        cache_integration: DataFrameCacheIntegration | None = None,
    ) -> None:
        """Initialize section builder.

        Args:
            section: Section object containing tasks. Expected to have:
                     - tasks: list[Task] attribute or method
                     - project: NameGid or dict with 'gid' for project context
            task_type: Task type to filter and extract ("Unit", "Contact")
            schema: DataFrameSchema for extraction
            resolver: Optional CustomFieldResolver for custom fields
            lazy_threshold: Task count threshold for lazy evaluation
            cache_integration: Optional cache integration for struc caching
        """
        super().__init__(schema, resolver, lazy_threshold, cache_integration)
        self._section = section
        self._task_type = task_type

    @property
    def section(self) -> Section:
        """Get the section being built from."""
        return self._section

    @property
    def task_type(self) -> str:
        """Get the task type filter."""
        return self._task_type

    def get_tasks(self) -> list[Task]:
        """Get tasks from section.

        Per FR-SECTION-001: Returns tasks from the section.
        Tasks are expected to be pre-filtered by task_type at the
        section/API level.

        Returns:
            List of Task objects from the section
        """
        # Handle section.tasks as attribute or method
        tasks = self._section.tasks
        if callable(tasks):
            tasks = tasks()

        return tasks if tasks else []

    def _get_project_gid(self) -> str | None:
        """Get project GID from section's parent project.

        Per FR-SECTION-005: Uses parent project GID for section
        extraction context and cache key generation.

        Returns:
            Project GID string or None
        """
        # Try to get project from section
        project = getattr(self._section, "project", None)
        if project is None:
            return None

        # Handle NameGid object
        if hasattr(project, "gid"):
            gid: str | None = project.gid
            return gid

        # Handle dict
        if isinstance(project, dict):
            return project.get("gid")

        return None

    def _get_extractor(self) -> BaseExtractor:
        """Get extractor for section's task type.

        Returns:
            Appropriate BaseExtractor subclass for task_type
        """
        return self._create_extractor(self._task_type)
