"""Template discovery for automation rules.

Per FR-004: Template discovery with fuzzy matching.
Per ADR-0106: Template Discovery Pattern.

Template discovery finds template sections and tasks within target projects
for pipeline conversion. Templates are identified by name patterns like
"template", "templates", or "template tasks" (case-insensitive).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.core import Section, Task


class TemplateDiscovery:
    """Discovers template sections and tasks in target projects.

    Per FR-004: Provides fuzzy matching for template discovery.

    Template sections are identified by checking if the section name
    contains any of the defined template patterns (case-insensitive).

    Example:
        discovery = TemplateDiscovery(client)

        # Find template section in project
        section = await discovery.find_template_section_async("project_gid")
        if section:
            print(f"Found template section: {section.name}")

        # Find specific template task
        task = await discovery.find_template_task_async(
            "project_gid",
            template_name="Sales Template"
        )
    """

    # Patterns to match for template sections (case-insensitive)
    TEMPLATE_PATTERNS: list[str] = ["template", "templates", "template tasks"]

    def __init__(self, client: AsanaClient) -> None:
        """Initialize TemplateDiscovery.

        Args:
            client: AsanaClient for API operations.
        """
        self._client = client

    async def find_template_section_async(
        self,
        project_gid: str,
        section_name: str | None = None,
        template_section_gid: str | None = None,
    ) -> Section | None:
        """Find template section by exact name or pattern match.

        Per FR-004: Searches project sections for template pattern match.

        If template_section_gid is provided, returns a lightweight Section
        object directly (skips sections listing API call entirely).
        If section_name is provided, performs case-insensitive exact match.
        Otherwise, searches for sections containing any of the TEMPLATE_PATTERNS.

        Args:
            project_gid: GID of the project to search.
            section_name: Optional exact section name to find (case-insensitive).
            template_section_gid: Optional pre-configured section GID from YAML.
                When provided, skips runtime section discovery entirely.

        Returns:
            First matching Section, or None if no template section found.

        Example:
            # Find by pattern (default behavior)
            section = await discovery.find_template_section_async("123456")

            # Find by exact name
            section = await discovery.find_template_section_async(
                "123456", section_name="Template"
            )

            # Skip discovery entirely with pre-configured GID
            section = await discovery.find_template_section_async(
                "123456", template_section_gid="1234567890"
            )
        """
        # Fast path: pre-configured section GID skips discovery
        if template_section_gid:
            from autom8_asana.models.section import Section

            return Section(gid=template_section_gid, name=section_name or "Template")

        # List all sections in the project
        sections = await self._client.sections.list_for_project_async(
            project_gid
        ).collect()

        # If exact name provided, find exact match (case-insensitive)
        if section_name:
            section_name_lower = section_name.lower()
            for section in sections:
                if section.name and section.name.lower() == section_name_lower:
                    return section
            return None

        # Otherwise, search for template pattern match
        for section in sections:
            if section.name and self._matches_template_pattern(section.name):
                return section

        return None

    async def find_template_task_async(
        self,
        project_gid: str,
        template_name: str | None = None,
        template_section: str | None = None,
        template_section_gid: str | None = None,
    ) -> Task | None:
        """Find template task to clone.

        Per FR-004: Discovers template task for pipeline conversion.

        If template_name is provided, searches for an exact match (case-insensitive).
        Otherwise, returns the first task in the template section.

        Args:
            project_gid: GID of the project to search.
            template_name: Optional specific template name to find.
            template_section: Optional section name to search in (case-insensitive).
                If not provided, uses pattern matching to find template section.
            template_section_gid: Optional pre-configured section GID from YAML.
                When provided, skips section discovery entirely and lists tasks
                from this section directly.

        Returns:
            Matching Task, or None if no template found.

        Example:
            # Find any template task
            task = await discovery.find_template_task_async("123456")

            # Find specific template by name
            task = await discovery.find_template_task_async(
                "123456",
                template_name="Onboarding Template"
            )

            # Find template in specific section
            task = await discovery.find_template_task_async(
                "123456",
                template_section="Template"
            )

            # Skip section discovery with pre-configured GID
            task = await discovery.find_template_task_async(
                "123456",
                template_section_gid="1234567890"
            )
        """
        # First find the template section
        section = await self.find_template_section_async(
            project_gid,
            section_name=template_section,
            template_section_gid=template_section_gid,
        )
        if section is None:
            return None

        # List tasks in the template section
        tasks = await self._client.tasks.list_async(section=section.gid).collect()

        if not tasks:
            return None

        # If specific name requested, search for match
        if template_name:
            template_name_lower = template_name.lower()
            for task in tasks:
                if task.name and task.name.lower() == template_name_lower:
                    return task
            # No exact match found
            return None

        # Return first task as default template
        return tasks[0]

    def _matches_template_pattern(self, name: str) -> bool:
        """Check if name matches any template pattern.

        Args:
            name: Section or task name to check.

        Returns:
            True if name contains any template pattern (case-insensitive).
        """
        name_lower = name.lower()
        return any(pattern in name_lower for pattern in self.TEMPLATE_PATTERNS)
