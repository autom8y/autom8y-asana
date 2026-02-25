"""Unit tests for PipelineConversionRule.

Per TDD-AUTOMATION-LAYER Phase 2: Test rule matching and execution.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.automation.config import AutomationConfig, PipelineStage
from autom8_asana.automation.context import AutomationContext
from autom8_asana.automation.events.types import EventType
from autom8_asana.automation.pipeline import PipelineConversionRule
from autom8_asana.core.creation import generate_entity_name
from autom8_asana.models.business.process import ProcessSection, ProcessType


class MockProcessType(Enum):
    """Mock ProcessType for testing (matches real enum values)."""

    SALES = "sales"
    ONBOARDING = "onboarding"
    GENERIC = "generic"


class MockProcessSection(Enum):
    """Mock ProcessSection for testing."""

    CONVERTED = "converted"
    ACTIVE = "active"


class MockProcess:
    """Mock Process entity for testing execute_async (named MockProcess)."""

    def __init__(
        self,
        gid: str = "process_123",
        name: str | None = None,
        process_type: ProcessType | MockProcessType = ProcessType.SALES,
        business: Any = None,
        unit: Any = None,
        notes: str | None = None,
    ) -> None:
        self.gid = gid
        self.name = name
        self.process_type = process_type
        self._business = business
        self._unit = unit
        self.notes = notes

    @property
    def business(self) -> Any:
        return self._business

    @property
    def unit(self) -> Any:
        return self._unit


# Class named "Process" for TriggerCondition matching tests
class Process(MockProcess):
    """Mock entity with class name 'Process' for TriggerCondition tests."""

    pass


class MockTask:
    """Mock Task for template task."""

    def __init__(
        self,
        gid: str = "template_123",
        name: str | None = None,
        notes: str | None = None,
        num_subtasks: int | None = None,
    ) -> None:
        self.gid = gid
        self.name = name
        self.notes = notes
        self.num_subtasks = num_subtasks


class MockSection:
    """Mock Section for template section."""

    def __init__(self, gid: str = "section_123", name: str | None = None) -> None:
        self.gid = gid
        self.name = name


class MockPageIterator:
    """Mock PageIterator that returns items via collect()."""

    def __init__(self, items: list[Any]) -> None:
        self._items = items

    async def collect(self) -> list[Any]:
        return self._items


class MockOffer:
    """Mock Offer entity for testing wrong entity type."""

    def __init__(self, gid: str = "offer_123") -> None:
        self.gid = gid


class MockSubtask:
    """Mock Subtask for template subtasks."""

    def __init__(self, gid: str = "subtask_123") -> None:
        self.gid = gid


def create_mock_context(
    pipeline_stages: dict[str, PipelineStage] | None = None,
    template_section: MockSection | None = None,
    template_task: MockTask | None = None,
    created_task: MockTask | None = None,
    template_subtasks: list[MockSubtask] | None = None,
    target_sections: list[MockSection] | None = None,
) -> AutomationContext:
    """Create mock AutomationContext with configured client.

    Args:
        pipeline_stages: Map of process type to PipelineStage.
        template_section: Template section to return.
        template_task: Template task to return.
        created_task: Task returned from duplicate_async.
        template_subtasks: Subtasks of the template (for subtask count).
        target_sections: Sections in target project (for section placement).

    Returns:
        Configured AutomationContext.
    """
    # Create config
    config = AutomationConfig(
        enabled=True,
        max_cascade_depth=5,
        pipeline_stages=pipeline_stages or {},
    )

    # Create mock client
    client = MagicMock()

    # Mock sections client - supports both template discovery and target section lookup
    # Template section is used first for discovery, then target sections for placement
    all_sections = []
    if template_section:
        all_sections.append(template_section)
    if target_sections:
        all_sections.extend(target_sections)
    client.sections.list_for_project_async.return_value = MockPageIterator(all_sections)

    # Mock sections.add_task_async for section placement
    client.sections.add_task_async = AsyncMock(return_value=None)

    # Mock tasks client
    # IMP-13: Set num_subtasks on template task from template_subtasks count
    # so pipeline can use template_task.num_subtasks instead of subtasks_async.
    if template_task and template_subtasks is not None:
        template_task.num_subtasks = len(template_subtasks)
    tasks = [template_task] if template_task else []
    client.tasks.list_async.return_value = MockPageIterator(tasks)

    # Mock subtasks_async for SubtaskWaiter polling (waits for subtasks on NEW task).
    # IMP-13: No longer used for template subtask counting, but SubtaskWaiter
    # still calls subtasks_async to verify subtask availability after duplication.
    subtasks = template_subtasks or []
    client.tasks.subtasks_async.return_value = MockPageIterator(subtasks)

    # Mock duplicate_async (replaces create_async)
    client.tasks.duplicate_async = AsyncMock(
        return_value=created_task or MockTask("new_task_123", "New Task")
    )

    # Mock add_to_project_async
    client.tasks.add_to_project_async = AsyncMock(
        return_value=created_task or MockTask("new_task_123", "New Task")
    )

    # Mock update_async for due date setting
    client.tasks.update_async = AsyncMock(return_value=None)

    # Mock stories client for onboarding comment creation
    client.stories.create_comment_async = AsyncMock(return_value=None)

    # Mock tasks.get_async for seeding (field write needs to fetch target task)
    client.tasks.get_async = AsyncMock(return_value=MagicMock(custom_fields=[]))

    # Mock tasks.set_assignee_async for assignee setting
    client.tasks.set_assignee_async = AsyncMock(return_value=None)

    return AutomationContext(
        client=client,
        config=config,
        depth=0,
        visited=set(),
    )


class TestPipelineConversionRuleInit:
    """Tests for PipelineConversionRule initialization."""

    def test_default_values(self) -> None:
        """Test default initialization values."""
        rule = PipelineConversionRule()

        assert rule._source_type == ProcessType.SALES
        assert rule._target_type == ProcessType.ONBOARDING
        assert rule._trigger_section == ProcessSection.CONVERTED

    def test_custom_values(self) -> None:
        """Test custom initialization values."""
        rule = PipelineConversionRule(
            source_type=ProcessType.OUTREACH,
            target_type=ProcessType.IMPLEMENTATION,
            trigger_section=ProcessSection.SCHEDULED,
        )

        assert rule._source_type == ProcessType.OUTREACH
        assert rule._target_type == ProcessType.IMPLEMENTATION
        assert rule._trigger_section == ProcessSection.SCHEDULED


class TestPipelineConversionRuleProperties:
    """Tests for rule property getters."""

    def test_id_property(self) -> None:
        """Test id property returns correct format."""
        rule = PipelineConversionRule()

        assert rule.id == "pipeline_sales_to_onboarding"

    def test_id_property_custom(self) -> None:
        """Test id property with custom types."""
        rule = PipelineConversionRule(
            source_type=ProcessType.OUTREACH,
            target_type=ProcessType.IMPLEMENTATION,
        )

        assert rule.id == "pipeline_outreach_to_implementation"

    def test_name_property(self) -> None:
        """Test name property returns correct format."""
        rule = PipelineConversionRule()

        assert rule.name == "Pipeline: Sales to Onboarding"

    def test_trigger_property(self) -> None:
        """Test trigger property returns TriggerCondition."""
        rule = PipelineConversionRule()
        trigger = rule.trigger

        assert trigger.entity_type == "Process"
        assert trigger.event == EventType.SECTION_CHANGED
        assert trigger.filters["process_type"] == "sales"
        assert trigger.filters["section"] == "converted"


class TestShouldTrigger:
    """Tests for should_trigger method."""

    def test_triggers_for_matching_process(self) -> None:
        """Test triggering for matching Process and event."""
        rule = PipelineConversionRule()
        # Use Process class (not MockProcess) so type(entity).__name__ == "Process"
        process = Process(process_type=ProcessType.SALES)
        context = {"section": "converted", "process_type": "sales"}

        result = rule.should_trigger(process, EventType.SECTION_CHANGED, context)

        assert result is True

    def test_no_trigger_wrong_entity_type(self) -> None:
        """Test no trigger for wrong entity type."""
        rule = PipelineConversionRule()
        offer = MockOffer()
        context = {"section": "converted"}

        result = rule.should_trigger(offer, EventType.SECTION_CHANGED, context)

        assert result is False

    def test_no_trigger_wrong_event(self) -> None:
        """Test no trigger for wrong event."""
        rule = PipelineConversionRule()
        process = MockProcess(process_type=ProcessType.SALES)
        context = {"section": "converted"}

        result = rule.should_trigger(process, EventType.CREATED, context)

        assert result is False

    def test_no_trigger_wrong_section(self) -> None:
        """Test no trigger for wrong section."""
        rule = PipelineConversionRule()
        process = MockProcess(process_type=ProcessType.SALES)
        context = {"section": "active", "process_type": "sales"}

        result = rule.should_trigger(process, EventType.SECTION_CHANGED, context)

        assert result is False

    def test_no_trigger_wrong_process_type(self) -> None:
        """Test no trigger for wrong process type."""
        rule = PipelineConversionRule()
        process = MockProcess(process_type=ProcessType.ONBOARDING)
        context = {"section": "converted", "process_type": "onboarding"}

        result = rule.should_trigger(process, EventType.SECTION_CHANGED, context)

        assert result is False

    def test_no_trigger_unknown_process(self) -> None:
        """Test no trigger for unknown process type."""
        rule = PipelineConversionRule()
        process = MockProcess(process_type=ProcessType.UNKNOWN)
        context = {"section": "converted", "process_type": "unknown"}

        result = rule.should_trigger(process, EventType.SECTION_CHANGED, context)

        assert result is False


class TestExecuteAsync:
    """Tests for execute_async method."""

    @pytest.mark.asyncio
    async def test_successful_execution(self) -> None:
        """Test successful pipeline conversion."""
        rule = PipelineConversionRule()

        # Setup mock context with template
        template_section = MockSection("section_123", "Template")
        template_task = MockTask(
            "template_123", "Onboarding Template", "Template notes"
        )
        created_task = MockTask("new_task_123", "Sales Lead")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
            created_task=created_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Sales Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert result.rule_id == "pipeline_sales_to_onboarding"
        assert result.triggered_by_gid == "process_123"
        assert result.triggered_by_type == "Process"
        assert "lookup_target_project" in result.actions_executed
        assert "discover_template" in result.actions_executed
        assert "duplicate_task" in result.actions_executed
        assert "add_to_project" in result.actions_executed
        assert "new_task_123" in result.entities_created
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_fails_when_no_target_project_configured(self) -> None:
        """Test failure when target project not in config."""
        rule = PipelineConversionRule()
        context = create_mock_context(pipeline_stages={})  # No onboarding project

        process = MockProcess(
            gid="process_123",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is False
        assert "No target project configured" in result.error
        assert result.triggered_by_gid == "process_123"

    @pytest.mark.asyncio
    async def test_fails_when_no_template_found(self) -> None:
        """Test failure when no template in target project."""
        rule = PipelineConversionRule()
        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            # No template section or task
        )

        process = MockProcess(
            gid="process_123",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is False
        assert "No template found" in result.error
        # Note: lookup_target_project is added before template discovery fails
        # discover_template is not in actions because we failed during that step
        assert "discover_template" not in result.actions_executed

    @pytest.mark.asyncio
    async def test_fails_for_wrong_entity_type(self) -> None:
        """Test failure when entity is not a Process."""
        rule = PipelineConversionRule()
        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
        )

        offer = MockOffer(gid="offer_123")

        result = await rule.execute_async(offer, context)

        assert result.success is False
        assert "Expected Process" in result.error
        assert result.triggered_by_type == "MockOffer"

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self) -> None:
        """Test graceful handling of exceptions."""
        rule = PipelineConversionRule()

        # Create context that will raise an exception
        config = AutomationConfig(
            enabled=True,
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
        )
        client = MagicMock()
        client.sections.list_for_project_async.side_effect = ConnectionError(
            "API Error"
        )

        context = AutomationContext(
            client=client,
            config=config,
            depth=0,
            visited=set(),
        )

        process = MockProcess(
            gid="process_123",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is False
        assert "API Error" in result.error
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_uses_template_name_with_placeholder_replacement(self) -> None:
        """Test that new task uses template name with bracketed placeholder replacement."""
        rule = PipelineConversionRule()

        template_section = MockSection("section_123", "Template")
        # Template has bracketed "[Business Name]" placeholder
        template_task = MockTask(
            "template_123", "Onboarding Process - [Business Name]", "Notes"
        )

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
        )

        # Create mock business with name
        mock_business = MagicMock()
        mock_business.name = "Nation of Wellness"

        process = MockProcess(
            gid="process_123",
            name="Sales Process - Nation of Wellness",  # This should NOT be used
            process_type=ProcessType.SALES,
            business=mock_business,
        )

        await rule.execute_async(process, context)

        # Verify duplicate_async was called with template name + replaced placeholder
        context.client.tasks.duplicate_async.assert_called_once()
        call_kwargs = context.client.tasks.duplicate_async.call_args.kwargs
        assert call_kwargs["name"] == "Onboarding Process - Nation of Wellness"

    @pytest.mark.asyncio
    async def test_uses_default_name_when_template_has_none(self) -> None:
        """Test default name when template task has no name."""
        rule = PipelineConversionRule()

        template_section = MockSection("section_123", "Template")
        template_task = MockTask("template_123", None, "Notes")  # No template name

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Sales Lead",
            process_type=ProcessType.SALES,
        )

        await rule.execute_async(process, context)

        call_kwargs = context.client.tasks.duplicate_async.call_args.kwargs
        assert call_kwargs["name"] == "New Onboarding"

    @pytest.mark.asyncio
    async def test_copies_subtasks_with_duplicate(self) -> None:
        """Test that duplicate_async is called with include=['subtasks', 'notes']."""
        rule = PipelineConversionRule()

        template_section = MockSection("section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")
        template_subtasks = [MockSubtask("subtask_1"), MockSubtask("subtask_2")]

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
            template_subtasks=template_subtasks,
        )

        process = MockProcess(
            gid="process_123",
            name="Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True

        # Verify duplicate_async was called with correct include
        context.client.tasks.duplicate_async.assert_called_once()
        call_kwargs = context.client.tasks.duplicate_async.call_args.kwargs
        assert call_kwargs["include"] == ["subtasks", "notes"]

        # Verify template GID was used
        call_args = context.client.tasks.duplicate_async.call_args.args
        assert call_args[0] == "template_123"

    @pytest.mark.asyncio
    async def test_adds_to_target_project(self) -> None:
        """Test that new task is added to target project after duplication."""
        rule = PipelineConversionRule()

        template_section = MockSection("section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")
        created_task = MockTask("new_task_123", "Lead")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
            created_task=created_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert "add_to_project" in result.actions_executed

        # Verify add_to_project_async was called with correct args
        context.client.tasks.add_to_project_async.assert_called_once_with(
            "new_task_123",
            "onboarding_project_123",
        )


class TestElapsedMs:
    """Tests for elapsed_ms timing utility."""

    def test_calculates_elapsed_time(self) -> None:
        """Test elapsed time calculation."""
        import time

        from autom8_asana.core.timing import elapsed_ms

        start = time.perf_counter()

        # Small delay
        time.sleep(0.001)

        elapsed = elapsed_ms(start)

        assert elapsed > 0
        assert elapsed < 1000  # Should be well under 1 second


class TestGenerateTaskName:
    """Tests for generate_entity_name shared helper (extracted from pipeline/creation)."""

    def test_replaces_business_name_placeholder(self) -> None:
        """Test [Business Name] placeholder is replaced."""
        mock_business = MagicMock()
        mock_business.name = "Nation of Wellness"

        result = generate_entity_name(
            template_name="Onboarding Process - [Business Name]",
            business=mock_business,
            unit=None,
        )

        assert result == "Onboarding Process - Nation of Wellness"

    def test_replaces_business_name_case_insensitive(self) -> None:
        """Test [Business Name] placeholder replacement is case-insensitive inside brackets."""
        mock_business = MagicMock()
        mock_business.name = "Acme Corp"

        # Lowercase variant
        result = generate_entity_name(
            template_name="Process for [business name]",
            business=mock_business,
            unit=None,
        )
        assert result == "Process for Acme Corp"

        # Mixed case variant
        result = generate_entity_name(
            template_name="Process for [BUSINESS NAME]",
            business=mock_business,
            unit=None,
        )
        assert result == "Process for Acme Corp"

    def test_replaces_unit_name_placeholder(self) -> None:
        """Test [Unit Name] placeholder is replaced."""
        mock_unit = MagicMock()
        mock_unit.name = "Downtown Location"

        result = generate_entity_name(
            template_name="Setup - [Unit Name]",
            business=None,
            unit=mock_unit,
        )

        assert result == "Setup - Downtown Location"

    def test_replaces_business_unit_name_placeholder(self) -> None:
        """Test [Business Unit Name] placeholder is replaced with unit name."""
        mock_unit = MagicMock()
        mock_unit.name = "Main Office"

        result = generate_entity_name(
            template_name="Onboarding - [Business Unit Name]",
            business=None,
            unit=mock_unit,
        )

        assert result == "Onboarding - Main Office"

    def test_replaces_multiple_placeholders(self) -> None:
        """Test multiple bracketed placeholders are replaced."""
        mock_business = MagicMock()
        mock_business.name = "Acme Corp"
        mock_unit = MagicMock()
        mock_unit.name = "West Division"

        result = generate_entity_name(
            template_name="[Business Name] - [Unit Name] Onboarding",
            business=mock_business,
            unit=mock_unit,
        )

        assert result == "Acme Corp - West Division Onboarding"

    def test_returns_default_when_template_name_is_none(self) -> None:
        """Test fallback to default name when template name is None."""
        # pipeline.py passes fallback_name=f"New {target_type.value.title()}"
        result = generate_entity_name(
            template_name=None,
            business=None,
            unit=None,
            fallback_name="New Onboarding",
        )

        assert result == "New Onboarding"

    def test_returns_default_when_template_name_is_empty(self) -> None:
        """Test fallback to default name when template name is empty string."""
        result = generate_entity_name(
            template_name="",
            business=None,
            unit=None,
            fallback_name="New Onboarding",
        )

        assert result == "New Onboarding"

    def test_preserves_template_name_without_placeholders(self) -> None:
        """Test template name is preserved when no bracketed placeholders match."""
        mock_business = MagicMock()
        mock_business.name = "Test Corp"

        result = generate_entity_name(
            template_name="Standard Onboarding Process",
            business=mock_business,
            unit=None,
        )

        assert result == "Standard Onboarding Process"

    def test_handles_none_business_gracefully(self) -> None:
        """Test bracketed placeholder preserved when business is None."""
        result = generate_entity_name(
            template_name="Onboarding - [Business Name]",
            business=None,
            unit=None,
        )

        # Placeholder should remain since business is None
        assert result == "Onboarding - [Business Name]"

    def test_handles_business_without_name_attribute(self) -> None:
        """Test bracketed placeholder preserved when business has no name."""
        mock_business = MagicMock(spec=[])  # No attributes

        result = generate_entity_name(
            template_name="Onboarding - [Business Name]",
            business=mock_business,
            unit=None,
        )

        # Placeholder should remain since business.name doesn't exist
        assert result == "Onboarding - [Business Name]"

    def test_handles_business_with_none_name(self) -> None:
        """Test bracketed placeholder preserved when business.name is None."""
        mock_business = MagicMock()
        mock_business.name = None

        result = generate_entity_name(
            template_name="Onboarding - [Business Name]",
            business=mock_business,
            unit=None,
        )

        # Placeholder should remain since business.name is None
        assert result == "Onboarding - [Business Name]"

    def test_handles_whitespace_variants_in_placeholder(self) -> None:
        """Test placeholders with optional whitespace inside brackets are replaced."""
        mock_business = MagicMock()
        mock_business.name = "Test Corp"

        # No space variant
        result = generate_entity_name(
            template_name="Process - [BusinessName]",
            business=mock_business,
            unit=None,
        )

        assert result == "Process - Test Corp"

    def test_custom_target_type_in_fallback(self) -> None:
        """Test custom fallback_name parameter is returned when template_name is None."""
        result = generate_entity_name(
            template_name=None,
            business=None,
            unit=None,
            fallback_name="New Implementation",
        )

        assert result == "New Implementation"

    def test_unbracketed_text_not_replaced(self) -> None:
        """Test that unbracketed 'Business Name' text is NOT replaced."""
        mock_business = MagicMock()
        mock_business.name = "Test Corp"

        # Without brackets, should NOT be replaced
        result = generate_entity_name(
            template_name="Onboarding Process - Business Name",
            business=mock_business,
            unit=None,
        )

        # Unbracketed text should remain unchanged
        assert result == "Onboarding Process - Business Name"

    def test_entire_bracket_removed_on_replacement(self) -> None:
        """Test that entire [placeholder] including brackets is replaced."""
        mock_business = MagicMock()
        mock_business.name = "Acme"

        result = generate_entity_name(
            template_name="[Business Name] Onboarding",
            business=mock_business,
            unit=None,
        )

        # No leftover brackets
        assert result == "Acme Onboarding"
        assert "[" not in result
        assert "]" not in result


class TestSectionPlacement:
    """Tests for section placement functionality (G3 Gap Fix)."""

    @pytest.mark.asyncio
    async def test_task_moved_to_target_section(self) -> None:
        """Test task is moved to target section after creation."""
        rule = PipelineConversionRule()

        # Setup: Template section and Opportunity section
        template_section = MockSection("template_section_123", "Template")
        opportunity_section = MockSection("opportunity_section_456", "Opportunity")
        template_task = MockTask("template_123", "Onboarding Template", "Notes")
        created_task = MockTask("new_task_123", "Lead")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(
                    project_gid="onboarding_project_123",
                    template_section="Template",
                    target_section="Opportunity",
                )
            },
            template_section=template_section,
            template_task=template_task,
            created_task=created_task,
            target_sections=[opportunity_section],
        )

        process = MockProcess(
            gid="process_123",
            name="Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert "section_placement" in result.actions_executed
        assert result.enhancement_results.get("section_placement") is True

        # Verify add_task_async was called with correct section and task
        context.client.sections.add_task_async.assert_called_once_with(
            "opportunity_section_456",
            task="new_task_123",
        )

    @pytest.mark.asyncio
    async def test_section_placement_case_insensitive(self) -> None:
        """Test section name matching is case-insensitive."""
        rule = PipelineConversionRule()

        # Section name is "opportunity" (lowercase), config has "Opportunity"
        template_section = MockSection("template_section_123", "Template")
        opportunity_section = MockSection("opportunity_section_456", "opportunity")
        template_task = MockTask("template_123", "Template", "Notes")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(
                    project_gid="onboarding_project_123",
                    target_section="OPPORTUNITY",  # Uppercase in config
                )
            },
            template_section=template_section,
            template_task=template_task,
            target_sections=[opportunity_section],
        )

        process = MockProcess(
            gid="process_123",
            name="Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert "section_placement" in result.actions_executed

    @pytest.mark.asyncio
    async def test_section_not_found_graceful_degradation(self) -> None:
        """Test graceful handling when target section not found."""
        rule = PipelineConversionRule()

        # Only Template section exists, no Opportunity section
        template_section = MockSection("template_section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(
                    project_gid="onboarding_project_123",
                    target_section="NonExistent",  # Section doesn't exist
                )
            },
            template_section=template_section,
            template_task=template_task,
            # No target_sections - section won't be found
        )

        process = MockProcess(
            gid="process_123",
            name="Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        # Conversion should still succeed (graceful degradation)
        assert result.success is True
        # But section_placement should not be in actions
        assert "section_placement" not in result.actions_executed
        assert result.enhancement_results.get("section_placement") is False

        # add_task_async should NOT be called
        context.client.sections.add_task_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_default_target_section_is_opportunity(self) -> None:
        """Test that default target section is 'Opportunity'."""
        # Verify PipelineStage default
        stage = PipelineStage(project_gid="123")
        assert stage.target_section == "Opportunity"

    @pytest.mark.asyncio
    async def test_pipeline_stages_with_default_section(self) -> None:
        """Test pipeline_stages without target_section uses default Opportunity."""
        rule = PipelineConversionRule()

        template_section = MockSection("template_section_123", "Template")
        opportunity_section = MockSection("opportunity_section_456", "Opportunity")
        template_task = MockTask("template_123", "Template", "Notes")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
            target_sections=[opportunity_section],
        )

        process = MockProcess(
            gid="process_123",
            name="Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        # Should use default "Opportunity" section
        assert "section_placement" in result.actions_executed

        context.client.sections.add_task_async.assert_called_once_with(
            "opportunity_section_456",
            task="new_task_123",
        )


class TestDueDateHandling:
    """Tests for due date handling functionality (G4 Gap Fix)."""

    @pytest.mark.asyncio
    async def test_due_date_set_when_configured(self) -> None:
        """Test due date is set when due_date_offset_days is configured."""
        from datetime import date, timedelta

        rule = PipelineConversionRule()

        template_section = MockSection("template_section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")
        created_task = MockTask("new_task_123", "Lead")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(
                    project_gid="onboarding_project_123",
                    target_section="Opportunity",
                    due_date_offset_days=7,  # Due in 7 days
                )
            },
            template_section=template_section,
            template_task=template_task,
            created_task=created_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert "set_due_date" in result.actions_executed
        assert result.enhancement_results.get("due_date_set") is True

        # Verify update_async was called with correct due_on
        expected_due_date = (date.today() + timedelta(days=7)).isoformat()
        context.client.tasks.update_async.assert_called_once_with(
            "new_task_123",
            due_on=expected_due_date,
        )

    @pytest.mark.asyncio
    async def test_due_date_not_set_when_none(self) -> None:
        """Test due date is not set when due_date_offset_days is None."""
        rule = PipelineConversionRule()

        template_section = MockSection("template_section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")
        created_task = MockTask("new_task_123", "Lead")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(
                    project_gid="onboarding_project_123",
                    target_section="Opportunity",
                    # due_date_offset_days not set (None)
                )
            },
            template_section=template_section,
            template_task=template_task,
            created_task=created_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert "set_due_date" not in result.actions_executed
        assert "due_date_set" not in result.enhancement_results

        # Verify update_async was NOT called
        context.client.tasks.update_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_due_date_offset_zero_is_today(self) -> None:
        """Test offset 0 sets due date to today."""
        from datetime import date

        rule = PipelineConversionRule()

        template_section = MockSection("template_section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")
        created_task = MockTask("new_task_123", "Lead")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(
                    project_gid="onboarding_project_123",
                    due_date_offset_days=0,  # Due today
                )
            },
            template_section=template_section,
            template_task=template_task,
            created_task=created_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert "set_due_date" in result.actions_executed

        # Verify today's date
        expected_due_date = date.today().isoformat()
        context.client.tasks.update_async.assert_called_once_with(
            "new_task_123",
            due_on=expected_due_date,
        )

    @pytest.mark.asyncio
    async def test_due_date_negative_offset_is_past(self) -> None:
        """Test negative offset sets due date in the past."""
        from datetime import date, timedelta

        rule = PipelineConversionRule()

        template_section = MockSection("template_section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")
        created_task = MockTask("new_task_123", "Lead")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(
                    project_gid="onboarding_project_123",
                    due_date_offset_days=-3,  # Due 3 days ago
                )
            },
            template_section=template_section,
            template_task=template_task,
            created_task=created_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert "set_due_date" in result.actions_executed

        # Verify past date
        expected_due_date = (date.today() + timedelta(days=-3)).isoformat()
        context.client.tasks.update_async.assert_called_once_with(
            "new_task_123",
            due_on=expected_due_date,
        )

    @pytest.mark.asyncio
    async def test_due_date_api_failure_graceful_degradation(self) -> None:
        """Test graceful handling when due date API call fails."""
        rule = PipelineConversionRule()

        template_section = MockSection("template_section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")
        created_task = MockTask("new_task_123", "Lead")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(
                    project_gid="onboarding_project_123",
                    due_date_offset_days=7,
                )
            },
            template_section=template_section,
            template_task=template_task,
            created_task=created_task,
        )

        # Make update_async raise an exception
        context.client.tasks.update_async.side_effect = ConnectionError("API Error")

        process = MockProcess(
            gid="process_123",
            name="Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        # Conversion should still succeed (graceful degradation)
        assert result.success is True
        # But set_due_date should not be in actions
        assert "set_due_date" not in result.actions_executed
        assert result.enhancement_results.get("due_date_set") is False

    @pytest.mark.asyncio
    async def test_default_due_date_offset_is_none(self) -> None:
        """Test that default due_date_offset_days is None."""
        stage = PipelineStage(project_gid="123")
        assert stage.due_date_offset_days is None

    @pytest.mark.asyncio
    async def test_pipeline_stages_no_due_date_when_not_configured(self) -> None:
        """Test pipeline_stages without due_date_offset_days skips due date."""
        rule = PipelineConversionRule()

        template_section = MockSection("template_section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Lead",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        # No due date set when not configured
        assert "set_due_date" not in result.actions_executed
        context.client.tasks.update_async.assert_not_called()


class TestValidationParameters:
    """Tests for validation parameter initialization."""

    def test_default_no_required_fields(self) -> None:
        """Test default has no required fields."""
        rule = PipelineConversionRule()
        assert rule._required_source_fields == []

    def test_default_validate_mode_is_warn(self) -> None:
        """Test default validate_mode is 'warn'."""
        rule = PipelineConversionRule()
        assert rule._validate_mode == "warn"

    def test_custom_required_fields(self) -> None:
        """Test custom required_source_fields are stored."""
        rule = PipelineConversionRule(
            required_source_fields=["deal_value", "close_date"],
        )
        assert rule._required_source_fields == ["deal_value", "close_date"]

    def test_validate_mode_block(self) -> None:
        """Test validate_mode='block' is stored."""
        rule = PipelineConversionRule(validate_mode="block")
        assert rule._validate_mode == "block"

    def test_none_required_fields_becomes_empty_list(self) -> None:
        """Test None required_source_fields becomes empty list."""
        rule = PipelineConversionRule(required_source_fields=None)
        assert rule._required_source_fields == []


class TestPreTransitionValidation:
    """Tests for _validate_pre_transition method."""

    def test_no_required_fields_returns_success(self) -> None:
        """Test validation succeeds when no required fields configured."""
        rule = PipelineConversionRule()
        process = MockProcess(gid="process_123")

        result = rule._validate_pre_transition(process)

        assert result.valid is True
        assert result.errors == []

    def test_present_required_field_returns_success(self) -> None:
        """Test validation succeeds when required field is present."""
        rule = PipelineConversionRule(required_source_fields=["name"])
        process = MockProcess(gid="process_123", name="Test Process")

        result = rule._validate_pre_transition(process)

        assert result.valid is True
        assert result.errors == []

    def test_missing_required_field_returns_failure(self) -> None:
        """Test validation fails when required field is missing."""
        rule = PipelineConversionRule(required_source_fields=["nonexistent_field"])
        process = MockProcess(gid="process_123", name="Test Process")

        result = rule._validate_pre_transition(process)

        assert result.valid is False
        assert "Missing required field: nonexistent_field" in result.errors

    def test_empty_string_required_field_returns_failure(self) -> None:
        """Test validation fails when required field is empty string."""
        rule = PipelineConversionRule(required_source_fields=["name"])
        process = MockProcess(gid="process_123", name="   ")

        result = rule._validate_pre_transition(process)

        assert result.valid is False
        assert "Empty required field: name" in result.errors

    def test_none_required_field_returns_failure(self) -> None:
        """Test validation fails when required field is None."""
        rule = PipelineConversionRule(required_source_fields=["name"])
        process = MockProcess(gid="process_123", name=None)

        result = rule._validate_pre_transition(process)

        assert result.valid is False
        assert "Missing required field: name" in result.errors

    def test_multiple_missing_fields(self) -> None:
        """Test validation reports all missing fields."""
        rule = PipelineConversionRule(
            required_source_fields=["field1", "field2", "field3"]
        )
        process = MockProcess(gid="process_123")

        result = rule._validate_pre_transition(process)

        assert result.valid is False
        assert len(result.errors) == 3
        assert "Missing required field: field1" in result.errors
        assert "Missing required field: field2" in result.errors
        assert "Missing required field: field3" in result.errors


class TestPostTransitionValidation:
    """Tests for _validate_post_transition method."""

    def test_no_required_fields_returns_success(self) -> None:
        """Test post-validation succeeds when no required fields configured."""
        rule = PipelineConversionRule()
        process = MockProcess(gid="process_123")
        target = MockTask(gid="new_task_123")

        result = rule._validate_post_transition(process, target, None)

        assert result.valid is True
        assert result.warnings == []

    def test_seeded_fields_match_returns_success(self) -> None:
        """Test post-validation succeeds when seeded fields include required."""
        rule = PipelineConversionRule(required_source_fields=["deal_value"])
        process = MockProcess(gid="process_123")
        target = MockTask(gid="new_task_123")
        seeded_fields = {"deal_value": 5000}

        result = rule._validate_post_transition(process, target, seeded_fields)

        assert result.valid is True
        assert result.warnings == []

    def test_no_seeded_fields_with_required_warns(self) -> None:
        """Test post-validation warns when no fields seeded but required configured."""
        rule = PipelineConversionRule(required_source_fields=["deal_value"])
        process = MockProcess(gid="process_123")
        target = MockTask(gid="new_task_123")

        result = rule._validate_post_transition(process, target, None)

        assert result.valid is True  # Post-validation is advisory
        assert "No fields were seeded" in result.warnings[0]

    def test_missing_seeded_field_warns(self) -> None:
        """Test post-validation warns when required field not in seeded."""
        rule = PipelineConversionRule(required_source_fields=["deal_value"])
        process = MockProcess(gid="process_123")
        target = MockTask(gid="new_task_123")
        seeded_fields = {"other_field": "value"}

        result = rule._validate_post_transition(process, target, seeded_fields)

        assert result.valid is True  # Post-validation is advisory
        assert "deal_value" in result.warnings[0]


class TestPreValidationInExecuteAsync:
    """Tests for pre-validation integration in execute_async."""

    @pytest.mark.asyncio
    async def test_pre_validation_executed_when_configured(self) -> None:
        """Test pre_validation is performed when required_source_fields set."""
        rule = PipelineConversionRule(
            required_source_fields=["name"],
        )

        template_section = MockSection("section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Test Process",  # Required field present
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert "pre_validation" in result.actions_executed
        assert result.pre_validation is not None
        assert result.pre_validation.valid is True

    @pytest.mark.asyncio
    async def test_pre_validation_warn_mode_continues_on_failure(self) -> None:
        """Test transition continues when validate_mode='warn' and validation fails."""
        rule = PipelineConversionRule(
            required_source_fields=["nonexistent_field"],
            validate_mode="warn",  # Default
        )

        template_section = MockSection("section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Test Process",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        # Transition should still succeed despite validation failure
        assert result.success is True
        assert "pre_validation" in result.actions_executed
        assert result.pre_validation is not None
        assert result.pre_validation.valid is False  # Validation failed
        assert "duplicate_task" in result.actions_executed  # But transition continued

    @pytest.mark.asyncio
    async def test_pre_validation_block_mode_stops_on_failure(self) -> None:
        """Test transition stops when validate_mode='block' and validation fails."""
        rule = PipelineConversionRule(
            required_source_fields=["nonexistent_field"],
            validate_mode="block",
        )

        template_section = MockSection("section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Test Process",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        # Transition should fail
        assert result.success is False
        assert "Pre-transition validation failed" in result.error
        assert "pre_validation" in result.actions_executed
        assert result.pre_validation is not None
        assert result.pre_validation.valid is False
        # Transition should NOT have continued
        assert "duplicate_task" not in result.actions_executed

    @pytest.mark.asyncio
    async def test_pre_validation_block_mode_continues_on_success(self) -> None:
        """Test transition continues when validate_mode='block' and validation passes."""
        rule = PipelineConversionRule(
            required_source_fields=["name"],  # Will be present
            validate_mode="block",
        )

        template_section = MockSection("section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Test Process",  # Required field present
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        # Transition should succeed
        assert result.success is True
        assert "pre_validation" in result.actions_executed
        assert result.pre_validation is not None
        assert result.pre_validation.valid is True
        assert "duplicate_task" in result.actions_executed

    @pytest.mark.asyncio
    async def test_no_validation_when_no_required_fields(self) -> None:
        """Test pre_validation not in actions when no required fields."""
        rule = PipelineConversionRule()  # No required_source_fields

        template_section = MockSection("section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Test Process",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert "pre_validation" not in result.actions_executed
        assert result.pre_validation is None


class TestPostValidationInExecuteAsync:
    """Tests for post-validation integration in execute_async."""

    @pytest.mark.asyncio
    async def test_post_validation_executed_when_configured(self) -> None:
        """Test post_validation is performed when required_source_fields set."""
        rule = PipelineConversionRule(
            required_source_fields=["name"],
        )

        template_section = MockSection("section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Test Process",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert "post_validation" in result.actions_executed
        assert result.post_validation is not None
        assert result.post_validation.valid is True  # Post-validation always valid

    @pytest.mark.asyncio
    async def test_no_post_validation_when_no_required_fields(self) -> None:
        """Test post_validation not in actions when no required fields."""
        rule = PipelineConversionRule()  # No required_source_fields

        template_section = MockSection("section_123", "Template")
        template_task = MockTask("template_123", "Template", "Notes")

        context = create_mock_context(
            pipeline_stages={
                "onboarding": PipelineStage(project_gid="onboarding_project_123")
            },
            template_section=template_section,
            template_task=template_task,
        )

        process = MockProcess(
            gid="process_123",
            name="Test Process",
            process_type=ProcessType.SALES,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert "post_validation" not in result.actions_executed
        assert result.post_validation is None


class TestOnboardingToImplementationTransition:
    """Tests for Onboarding -> Implementation pipeline transition.

    Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT: Second transition path.
    """

    def test_onboarding_to_implementation_rule_id(self) -> None:
        """Test rule id for Onboarding -> Implementation."""
        rule = PipelineConversionRule(
            source_type=ProcessType.ONBOARDING,
            target_type=ProcessType.IMPLEMENTATION,
        )

        assert rule.id == "pipeline_onboarding_to_implementation"

    def test_onboarding_to_implementation_rule_name(self) -> None:
        """Test rule name for Onboarding -> Implementation."""
        rule = PipelineConversionRule(
            source_type=ProcessType.ONBOARDING,
            target_type=ProcessType.IMPLEMENTATION,
        )

        assert rule.name == "Pipeline: Onboarding to Implementation"

    def test_onboarding_to_implementation_trigger(self) -> None:
        """Test trigger condition for Onboarding -> Implementation."""
        rule = PipelineConversionRule(
            source_type=ProcessType.ONBOARDING,
            target_type=ProcessType.IMPLEMENTATION,
            trigger_section=ProcessSection.CONVERTED,
        )

        trigger = rule.trigger
        assert trigger.entity_type == "Process"
        assert trigger.event == EventType.SECTION_CHANGED
        assert trigger.filters["process_type"] == "onboarding"
        assert trigger.filters["section"] == "converted"

    def test_onboarding_to_implementation_with_validation(self) -> None:
        """Test rule with validation for Onboarding -> Implementation."""
        rule = PipelineConversionRule(
            source_type=ProcessType.ONBOARDING,
            target_type=ProcessType.IMPLEMENTATION,
            trigger_section=ProcessSection.CONVERTED,
            required_source_fields=["go_live_date", "onboarding_specialist"],
            validate_mode="warn",
        )

        assert rule._source_type == ProcessType.ONBOARDING
        assert rule._target_type == ProcessType.IMPLEMENTATION
        assert rule._required_source_fields == ["go_live_date", "onboarding_specialist"]
        assert rule._validate_mode == "warn"

    @pytest.mark.asyncio
    async def test_onboarding_to_implementation_execution(self) -> None:
        """Test execution of Onboarding -> Implementation transition."""
        rule = PipelineConversionRule(
            source_type=ProcessType.ONBOARDING,
            target_type=ProcessType.IMPLEMENTATION,
        )

        template_section = MockSection("section_123", "Template")
        template_task = MockTask("template_123", "Implementation Template", "Notes")
        created_task = MockTask("new_task_123", "New Implementation")

        context = create_mock_context(
            pipeline_stages={
                "implementation": PipelineStage(
                    project_gid="impl_project_123",
                    template_section="Template",
                    target_section="Opportunity",
                )
            },
            template_section=template_section,
            template_task=template_task,
            created_task=created_task,
        )

        # Note: MockProcess process_type is set but should_trigger won't match
        # because type(entity).__name__ is "MockProcess" not "Process"
        # This test verifies execute_async works for the flow
        process = MockProcess(
            gid="onboarding_123",
            name="Onboarding - Test",
            process_type=ProcessType.ONBOARDING,
        )

        result = await rule.execute_async(process, context)

        assert result.success is True
        assert result.rule_id == "pipeline_onboarding_to_implementation"
        assert "lookup_target_project" in result.actions_executed
        assert "discover_template" in result.actions_executed
        assert "duplicate_task" in result.actions_executed
