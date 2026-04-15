"""Unit tests for TemplateDiscovery.

Per TDD-AUTOMATION-LAYER Phase 2: Test template discovery with mocked client.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from autom8_asana.automation.templates import TemplateDiscovery


class MockSection:
    """Mock Section for testing."""

    def __init__(self, gid: str, name: str | None = None) -> None:
        self.gid = gid
        self.name = name


class MockTask:
    """Mock Task for testing."""

    def __init__(
        self,
        gid: str,
        name: str | None = None,
        notes: str | None = None,
    ) -> None:
        self.gid = gid
        self.name = name
        self.notes = notes


class MockPageIterator:
    """Mock PageIterator that returns items via collect()."""

    def __init__(self, items: list[Any]) -> None:
        self._items = items

    async def collect(self) -> list[Any]:
        """Return all items."""
        return self._items


def create_mock_client(
    sections: list[MockSection] | None = None,
    tasks: list[MockTask] | None = None,
) -> MagicMock:
    """Create mock AsanaClient with configured responses.

    Args:
        sections: Sections to return from list_for_project_async.
        tasks: Tasks to return from list_async.

    Returns:
        Mock AsanaClient.
    """
    client = MagicMock()

    # Mock sections client
    client.sections.list_for_project_async.return_value = MockPageIterator(sections or [])

    # Mock tasks client
    client.tasks.list_async.return_value = MockPageIterator(tasks or [])

    return client


class TestTemplateDiscovery:
    """Tests for TemplateDiscovery class."""

    def test_init(self) -> None:
        """Test TemplateDiscovery initialization."""
        client = create_mock_client()
        discovery = TemplateDiscovery(client)

        assert discovery._client is client
        assert "template" in discovery.TEMPLATE_PATTERNS
        assert "templates" in discovery.TEMPLATE_PATTERNS
        assert "template tasks" in discovery.TEMPLATE_PATTERNS


class TestFindTemplateSection:
    """Tests for find_template_section_async."""

    async def test_finds_template_section(self) -> None:
        """Test finding a section named 'Template'."""
        sections = [
            MockSection("section_1", "Active"),
            MockSection("section_2", "Template"),
            MockSection("section_3", "Completed"),
        ]
        client = create_mock_client(sections=sections)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_section_async("project_123")

        assert result is not None
        assert result.gid == "section_2"
        assert result.name == "Template"
        client.sections.list_for_project_async.assert_called_once_with("project_123")

    async def test_finds_templates_plural(self) -> None:
        """Test finding a section named 'Templates'."""
        sections = [
            MockSection("section_1", "Active"),
            MockSection("section_2", "Templates"),
        ]
        client = create_mock_client(sections=sections)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_section_async("project_123")

        assert result is not None
        assert result.gid == "section_2"

    async def test_finds_template_tasks_section(self) -> None:
        """Test finding a section named 'Template Tasks'."""
        sections = [
            MockSection("section_1", "Active"),
            MockSection("section_2", "Template Tasks"),
        ]
        client = create_mock_client(sections=sections)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_section_async("project_123")

        assert result is not None
        assert result.gid == "section_2"

    async def test_case_insensitive_matching(self) -> None:
        """Test case-insensitive template pattern matching."""
        sections = [
            MockSection("section_1", "Active"),
            MockSection("section_2", "TEMPLATE"),
        ]
        client = create_mock_client(sections=sections)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_section_async("project_123")

        assert result is not None
        assert result.gid == "section_2"

    async def test_finds_first_match(self) -> None:
        """Test that first matching section is returned."""
        sections = [
            MockSection("section_1", "My Template"),
            MockSection("section_2", "Another Template"),
        ]
        client = create_mock_client(sections=sections)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_section_async("project_123")

        assert result is not None
        assert result.gid == "section_1"

    async def test_returns_none_when_no_match(self) -> None:
        """Test returning None when no template section exists."""
        sections = [
            MockSection("section_1", "Active"),
            MockSection("section_2", "Completed"),
        ]
        client = create_mock_client(sections=sections)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_section_async("project_123")

        assert result is None

    async def test_returns_none_for_empty_project(self) -> None:
        """Test returning None when project has no sections."""
        client = create_mock_client(sections=[])
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_section_async("project_123")

        assert result is None

    async def test_skips_sections_with_none_name(self) -> None:
        """Test skipping sections with None name."""
        sections = [
            MockSection("section_1", None),
            MockSection("section_2", "Template"),
        ]
        client = create_mock_client(sections=sections)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_section_async("project_123")

        assert result is not None
        assert result.gid == "section_2"


class TestFindTemplateTask:
    """Tests for find_template_task_async."""

    async def test_finds_first_task_in_template_section(self) -> None:
        """Test finding first task in template section when no name specified."""
        sections = [MockSection("section_template", "Template")]
        tasks = [
            MockTask("task_1", "First Template"),
            MockTask("task_2", "Second Template"),
        ]
        client = create_mock_client(sections=sections, tasks=tasks)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_task_async("project_123")

        assert result is not None
        assert result.gid == "task_1"
        assert result.name == "First Template"

    async def test_finds_specific_template_by_name(self) -> None:
        """Test finding specific template task by name."""
        sections = [MockSection("section_template", "Template")]
        tasks = [
            MockTask("task_1", "Sales Template"),
            MockTask("task_2", "Onboarding Template"),
        ]
        client = create_mock_client(sections=sections, tasks=tasks)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_task_async(
            "project_123", template_name="Onboarding Template"
        )

        assert result is not None
        assert result.gid == "task_2"
        assert result.name == "Onboarding Template"

    async def test_case_insensitive_template_name_matching(self) -> None:
        """Test case-insensitive template name matching."""
        sections = [MockSection("section_template", "Template")]
        tasks = [MockTask("task_1", "My Template")]
        client = create_mock_client(sections=sections, tasks=tasks)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_task_async(
            "project_123", template_name="MY TEMPLATE"
        )

        assert result is not None
        assert result.gid == "task_1"

    async def test_returns_none_when_template_name_not_found(self) -> None:
        """Test returning None when specific template name not found."""
        sections = [MockSection("section_template", "Template")]
        tasks = [MockTask("task_1", "Sales Template")]
        client = create_mock_client(sections=sections, tasks=tasks)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_task_async(
            "project_123", template_name="Nonexistent Template"
        )

        assert result is None

    async def test_returns_none_when_no_template_section(self) -> None:
        """Test returning None when no template section exists."""
        sections = [MockSection("section_1", "Active")]
        client = create_mock_client(sections=sections)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_task_async("project_123")

        assert result is None

    async def test_returns_none_when_template_section_empty(self) -> None:
        """Test returning None when template section has no tasks."""
        sections = [MockSection("section_template", "Template")]
        client = create_mock_client(sections=sections, tasks=[])
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_task_async("project_123")

        assert result is None

    async def test_uses_correct_section_gid_for_task_listing(self) -> None:
        """Test that tasks are listed from correct section."""
        sections = [MockSection("template_section_gid", "Template")]
        tasks = [MockTask("task_1", "Template Task")]
        client = create_mock_client(sections=sections, tasks=tasks)
        discovery = TemplateDiscovery(client)

        await discovery.find_template_task_async("project_123")

        # Verify list_async was called with the template section GID
        client.tasks.list_async.assert_called_once_with(
            section="template_section_gid", opt_fields=None
        )


class TestTemplateSectionGidShortcut:
    """Tests for template_section_gid fast path (IMP-07)."""

    async def test_section_gid_skips_listing(self) -> None:
        """When template_section_gid is provided, skip section listing entirely."""
        client = create_mock_client()
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_section_async(
            "project_123", template_section_gid="pre_configured_gid"
        )

        assert result is not None
        assert result.gid == "pre_configured_gid"
        # Section listing should NOT have been called
        client.sections.list_for_project_async.assert_not_called()

    async def test_section_gid_uses_section_name_when_provided(self) -> None:
        """When both template_section_gid and section_name are provided."""
        client = create_mock_client()
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_section_async(
            "project_123",
            section_name="My Template Section",
            template_section_gid="pre_configured_gid",
        )

        assert result is not None
        assert result.gid == "pre_configured_gid"
        assert result.name == "My Template Section"

    async def test_section_gid_default_name(self) -> None:
        """When template_section_gid is provided without section_name."""
        client = create_mock_client()
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_section_async(
            "project_123", template_section_gid="pre_configured_gid"
        )

        assert result.name == "Template"

    async def test_task_with_section_gid_skips_section_listing(self) -> None:
        """find_template_task_async with template_section_gid skips section listing."""
        tasks = [MockTask("task_1", "Template Task")]
        client = create_mock_client(tasks=tasks)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_task_async(
            "project_123", template_section_gid="pre_configured_gid"
        )

        assert result is not None
        assert result.gid == "task_1"
        # Section listing should NOT have been called
        client.sections.list_for_project_async.assert_not_called()
        # But task listing should have been called with the pre-configured GID
        client.tasks.list_async.assert_called_once_with(
            section="pre_configured_gid", opt_fields=None
        )

    async def test_none_section_gid_falls_back_to_discovery(self) -> None:
        """When template_section_gid is None, fall back to normal discovery."""
        sections = [MockSection("section_2", "Template")]
        tasks = [MockTask("task_1", "Template Task")]
        client = create_mock_client(sections=sections, tasks=tasks)
        discovery = TemplateDiscovery(client)

        result = await discovery.find_template_task_async("project_123", template_section_gid=None)

        assert result is not None
        assert result.gid == "task_1"
        # Section listing SHOULD have been called (normal discovery)
        client.sections.list_for_project_async.assert_called_once()


class TestMatchesTemplatePattern:
    """Tests for _matches_template_pattern helper."""

    def test_matches_template(self) -> None:
        """Test matching 'template'."""
        client = create_mock_client()
        discovery = TemplateDiscovery(client)

        assert discovery._matches_template_pattern("Template") is True
        assert discovery._matches_template_pattern("template") is True
        assert discovery._matches_template_pattern("My Template") is True

    def test_matches_templates(self) -> None:
        """Test matching 'templates'."""
        client = create_mock_client()
        discovery = TemplateDiscovery(client)

        assert discovery._matches_template_pattern("Templates") is True
        assert discovery._matches_template_pattern("All Templates") is True

    def test_matches_template_tasks(self) -> None:
        """Test matching 'template tasks'."""
        client = create_mock_client()
        discovery = TemplateDiscovery(client)

        assert discovery._matches_template_pattern("Template Tasks") is True
        assert discovery._matches_template_pattern("template tasks") is True

    def test_no_match_unrelated(self) -> None:
        """Test no match for unrelated names."""
        client = create_mock_client()
        discovery = TemplateDiscovery(client)

        assert discovery._matches_template_pattern("Active") is False
        assert discovery._matches_template_pattern("Completed") is False
        assert discovery._matches_template_pattern("Backlog") is False
