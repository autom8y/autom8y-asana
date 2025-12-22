"""ProjectDataFrameBuilder for project-scoped DataFrame construction.

Per TDD-0009 Phase 4: Provides project-level DataFrame building with
optional section filtering via task memberships.

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

# Type alias for Project - using Any since Project is not defined in this package
# and we want to accept any object with the required attributes
Project = Any


class ProjectDataFrameBuilder(DataFrameBuilder):
    """Builder for project-scoped DataFrame extraction.

    Per FR-PROJECT-001-013: Project-level extraction with support for:
    - Task type filtering
    - Section filtering via task memberships
    - Lazy/eager evaluation selection
    - Optional cache integration (TDD-0008)

    This builder extracts tasks from a project, optionally filtering
    by section names through task membership inspection.

    Attributes:
        project: Project object containing tasks to extract
        task_type: Task type filter ("Unit", "Contact", etc.)
        sections: Optional list of section names to filter by

    Example:
        >>> from autom8_asana.dataframes.schemas import UNIT_SCHEMA
        >>> builder = ProjectDataFrameBuilder(
        ...     project=project,
        ...     task_type="Unit",
        ...     schema=UNIT_SCHEMA,
        ...     sections=["Active", "In Progress"],
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
        project: Project,
        task_type: str,
        schema: DataFrameSchema,
        sections: list[str] | None = None,
        resolver: CustomFieldResolver | None = None,
        lazy_threshold: int = LAZY_THRESHOLD,
        cache_integration: DataFrameCacheIntegration | None = None,
    ) -> None:
        """Initialize project builder.

        Args:
            project: Project object containing tasks. Expected to have:
                     - gid: str attribute for project identifier
                     - tasks: list[Task] attribute or method
            task_type: Task type to filter and extract ("Unit", "Contact")
            schema: DataFrameSchema for extraction
            sections: Optional list of section names to filter by.
                      If provided, only tasks in these sections are included.
            resolver: Optional CustomFieldResolver for custom fields
            lazy_threshold: Task count threshold for lazy evaluation
            cache_integration: Optional cache integration for struc caching
        """
        super().__init__(schema, resolver, lazy_threshold, cache_integration)
        self._project = project
        self._task_type = task_type
        self._sections = sections

    @property
    def project(self) -> Project:
        """Get the project being built from."""
        return self._project

    @property
    def task_type(self) -> str:
        """Get the task type filter."""
        return self._task_type

    @property
    def sections(self) -> list[str] | None:
        """Get the section filter list."""
        return self._sections

    def get_tasks(self) -> list[Task]:
        """Get tasks from project with optional section filtering.

        Per FR-PROJECT-001, FR-PROJECT-010: Returns tasks from project,
        filtered by sections if specified. Tasks are expected to be
        pre-filtered by task_type at the project/API level.

        Returns:
            List of Task objects from the project
        """
        # Handle project.tasks as attribute or method
        tasks = self._project.tasks
        if callable(tasks):
            tasks = tasks()

        if not tasks:
            return []

        # Apply section filtering if sections specified
        if self._sections:
            tasks = [
                task for task in tasks if self._task_in_sections(task, self._sections)
            ]

        # Cast to list[Task] for type checker since tasks comes from Any
        result: list[Task] = tasks
        return result

    def _get_project_gid(self) -> str | None:
        """Get project GID for section extraction context.

        Per FR-PROJECT-001: Uses project GID for section extraction
        and cache key generation.

        Returns:
            Project GID string or None
        """
        return getattr(self._project, "gid", None)

    def _get_extractor(self) -> BaseExtractor:
        """Get extractor for project's task type.

        Returns:
            Appropriate BaseExtractor subclass for task_type
        """
        return self._create_extractor(self._task_type)

    def _task_in_sections(self, task: Task, sections: list[str]) -> bool:
        """Check if task belongs to any of the specified sections.

        Per FR-PROJECT-010: Section filtering via task memberships.
        Inspects task.memberships to find section names.

        Args:
            task: Task to check
            sections: List of section names to match against

        Returns:
            True if task is in any of the specified sections
        """
        if not task.memberships:
            return False

        for membership in task.memberships:
            section = membership.get("section", {})
            if isinstance(section, dict):
                section_name = section.get("name")
                if section_name in sections:
                    return True

        return False
