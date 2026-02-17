"""Tests for EntityCreationService.

Coverage targets (per task spec):
- Template-based creation happy path
- Blank task fallback when template not found
- Name generation with placeholder replacement
- Auto-cascade: matching field cascades automatically
- Auto-cascade: exclusion prevents cascade
- Auto-cascade: computed field overrides source value
- Auto-cascade: precedence (Process > Unit > Business)
- Enum field GID resolution
- Duplicate detection: existing non-completed found -> skip creation
- Assignee resolution: stage-specific field used
- Assignee resolution: fallback to Unit.rep[0]
- Assignee resolution: fallback to Business.rep[0]
- Assignee resolution: none available -> warning
- Hierarchy placement via resolve_holder_async
- Due date calculation
- Section placement
- Error handling: creation failure -> error result with diagnostics
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.core.creation import generate_entity_name
from autom8_asana.lifecycle.config import (
    AssigneeConfig,
    SeedingConfig,
    StageConfig,
    TransitionConfig,
)
from autom8_asana.lifecycle.creation import CreationResult, EntityCreationService
from autom8_asana.lifecycle.seeding import AutoCascadeSeeder, SeedingResult

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_stage_config(**overrides: Any) -> StageConfig:
    """Create a minimal StageConfig for testing."""
    defaults = {
        "name": "onboarding",
        "project_gid": "proj_gid_123",
        "template_section": "TEMPLATE",
        "target_section": "OPPORTUNITY",
        "due_date_offset_days": 14,
        "transitions": TransitionConfig(converted="implementation"),
        "seeding": SeedingConfig(),
        "assignee": AssigneeConfig(),
    }
    defaults.update(overrides)
    return StageConfig(**defaults)


def _make_mock_client() -> MagicMock:
    """Build a mock AsanaClient with standard sub-clients."""
    client = MagicMock()

    # Tasks sub-client
    client.tasks = MagicMock()
    client.tasks.duplicate_async = AsyncMock()
    client.tasks.create_async = AsyncMock()
    client.tasks.add_to_project_async = AsyncMock()
    client.tasks.update_async = AsyncMock()
    client.tasks.set_assignee_async = AsyncMock()
    client.tasks.get_async = AsyncMock()

    # subtasks_async returns a page iterator with .collect()
    subtasks_iter = MagicMock()
    subtasks_iter.collect = AsyncMock(return_value=[])
    client.tasks.subtasks_async = MagicMock(return_value=subtasks_iter)

    # Sections sub-client
    client.sections = MagicMock()
    sections_iter = MagicMock()
    sections_iter.collect = AsyncMock(return_value=[])
    client.sections.list_for_project_async = MagicMock(
        return_value=sections_iter,
    )
    client.sections.add_task_async = AsyncMock()

    return client


def _make_mock_ctx(
    business: Any = None,
    unit: Any = None,
) -> AsyncMock:
    """Build a mock ResolutionContext."""
    if business is None:
        business = MagicMock()
        business.gid = "biz_gid"
        business.name = "Test Business"
        business.custom_fields = []
        business.rep = None

    if unit is None:
        unit = MagicMock()
        unit.gid = "unit_gid"
        unit.name = "Test Unit"
        unit.custom_fields = []
        unit.rep = None

    ctx = AsyncMock()
    ctx.business_async = AsyncMock(return_value=business)
    ctx.unit_async = AsyncMock(return_value=unit)
    ctx.cache_entity = MagicMock()
    ctx.resolve_holder_async = AsyncMock(return_value=None)
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


def _make_mock_process(**overrides: Any) -> MagicMock:
    """Build a mock Process entity."""
    process = MagicMock()
    process.gid = overrides.get("gid", "src_proc_gid")
    process.name = overrides.get("name", "Source Process")
    process.process_holder = overrides.get("process_holder", None)
    process.custom_fields = overrides.get("custom_fields", [])
    process.rep = overrides.get("rep", None)
    return process


def _make_mock_task(gid: str = "new_task_gid", name: str = "New Task") -> MagicMock:
    """Build a mock task object returned from Asana API."""
    task = MagicMock()
    task.gid = gid
    task.name = name
    task.custom_fields = []
    return task


# ------------------------------------------------------------------
# Template-Based Creation Happy Path
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_process_template_happy_path():
    """Template-based creation: template found, duplicated, configured."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    # Template discovery returns a template
    template_task = MagicMock()
    template_task.gid = "tmpl_gid"
    template_task.name = "Onboarding - [Business Name]"
    template_task.num_subtasks = 0  # IMP-13: subtask count from discovery

    new_task = _make_mock_task(gid="created_gid", name="Onboarding - Test Business")
    client.tasks.duplicate_async.return_value = new_task

    ctx = _make_mock_ctx()
    source_process = _make_mock_process()

    stage_config = _make_stage_config()

    with (
        patch("autom8_asana.lifecycle.creation.TemplateDiscovery") as MockTD,
        patch("autom8_asana.lifecycle.creation.AutoCascadeSeeder") as MockSeeder,
        patch("autom8_asana.lifecycle.creation.SubtaskWaiter"),
    ):
        MockTD.return_value.find_template_task_async = AsyncMock(
            return_value=template_task,
        )
        seeder_instance = MockSeeder.return_value
        seeder_instance.seed_async = AsyncMock(
            return_value=SeedingResult(
                fields_seeded=["Vertical", "Contact Phone"],
                fields_skipped=[],
            ),
        )

        result = await service.create_process_async(
            stage_config,
            ctx,
            source_process,
        )

    assert result.success is True
    assert result.entity_gid == "created_gid"
    assert result.entity_name == "Onboarding - Test Business"
    assert result.was_reopened is False
    assert "Vertical" in result.fields_seeded
    assert "Contact Phone" in result.fields_seeded

    # Template was duplicated
    client.tasks.duplicate_async.assert_called_once_with(
        "tmpl_gid",
        name="Onboarding - Test Business",
        include=["subtasks", "notes"],
    )
    # Added to project
    client.tasks.add_to_project_async.assert_called_once()
    # Context entity cached
    ctx.cache_entity.assert_called_once()


# ------------------------------------------------------------------
# Blank Task Fallback
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_process_blank_fallback():
    """When template not found, create blank task with warning."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    blank_task = _make_mock_task(gid="blank_gid")
    client.tasks.create_async.return_value = blank_task

    ctx = _make_mock_ctx()
    source_process = _make_mock_process()

    stage_config = _make_stage_config()

    with (
        patch("autom8_asana.lifecycle.creation.TemplateDiscovery") as MockTD,
        patch("autom8_asana.lifecycle.creation.AutoCascadeSeeder") as MockSeeder,
        patch("autom8_asana.lifecycle.creation.SubtaskWaiter"),
    ):
        MockTD.return_value.find_template_task_async = AsyncMock(
            return_value=None,
        )
        MockSeeder.return_value.seed_async = AsyncMock(
            return_value=SeedingResult(),
        )

        result = await service.create_process_async(
            stage_config,
            ctx,
            source_process,
        )

    assert result.success is True
    assert result.entity_gid == "blank_gid"
    assert result.entity_name == "New Process"
    # Warning about template not found
    assert any("Template not found" in w for w in result.warnings)
    # create_async called (not duplicate_async)
    client.tasks.create_async.assert_called_once_with(name="New Process")
    client.tasks.duplicate_async.assert_not_called()


# ------------------------------------------------------------------
# Name Generation
# ------------------------------------------------------------------


def test_generate_name_business_placeholder():
    """[Business Name] replaced with business.name."""
    business = MagicMock()
    business.name = "Acme Corp"
    unit = MagicMock()
    unit.name = "Downtown"

    result = generate_entity_name(
        template_name="[Business Name] - Sales",
        business=business,
        unit=unit,
    )
    assert result == "Acme Corp - Sales"


def test_generate_name_unit_placeholder():
    """[Unit Name] replaced with unit.name."""
    business = MagicMock()
    business.name = "Acme Corp"
    unit = MagicMock()
    unit.name = "Downtown Office"

    result = generate_entity_name(
        template_name="[Unit Name] Onboarding",
        business=business,
        unit=unit,
    )
    assert result == "Downtown Office Onboarding"


def test_generate_name_both_placeholders():
    """Both [Business Name] and [Unit Name] replaced."""
    business = MagicMock()
    business.name = "Acme Corp"
    unit = MagicMock()
    unit.name = "Downtown"

    result = generate_entity_name(
        template_name="[Business Name] - [Unit Name]",
        business=business,
        unit=unit,
    )
    assert result == "Acme Corp - Downtown"


def test_generate_name_business_unit_name_variant():
    """[Business Unit Name] replaced with unit.name."""
    business = MagicMock()
    business.name = "Acme Corp"
    unit = MagicMock()
    unit.name = "Downtown"

    result = generate_entity_name(
        template_name="[Business Unit Name] Process",
        business=business,
        unit=unit,
    )
    assert result == "Downtown Process"


def test_generate_name_no_template():
    """None template_name returns default fallback 'New Process'."""
    result = generate_entity_name(
        template_name=None,
        business=MagicMock(),
        unit=MagicMock(),
    )
    assert result == "New Process"


def test_generate_name_case_insensitive():
    """Placeholder matching is case-insensitive."""
    business = MagicMock()
    business.name = "Acme"
    unit = MagicMock()
    unit.name = None

    result = generate_entity_name(
        template_name="[BUSINESS NAME] - Sales",
        business=business,
        unit=unit,
    )
    assert result == "Acme - Sales"


# ------------------------------------------------------------------
# Auto-Cascade Field Seeding
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_cascade_matching_field_cascades():
    """Fields with matching names on source and target cascade automatically."""
    client = _make_mock_client()

    # Target task has custom fields: Vertical, Contact Phone
    target_task = MagicMock()
    target_task.custom_fields = [
        {
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_options": [{"name": "Dental", "gid": "opt1"}],
        },
        {"name": "Contact Phone", "resource_subtype": "text"},
    ]
    client.tasks.get_async.return_value = target_task

    # Source process has matching fields
    source_process = _make_mock_process(
        custom_fields=[
            {
                "name": "Vertical",
                "resource_subtype": "enum",
                "enum_value": {"name": "Dental", "gid": "opt1"},
            },
            {
                "name": "Contact Phone",
                "resource_subtype": "text",
                "text_value": "555-1234",
            },
        ],
    )

    # Mock the FieldSeeder.write_fields_async call
    from autom8_asana.automation.seeding import WriteResult

    with patch("autom8_asana.lifecycle.seeding.FieldSeeder") as MockFS:
        mock_seeder_write = MockFS.return_value
        mock_seeder_write.write_fields_async = AsyncMock(
            return_value=WriteResult(
                success=True,
                fields_written=["Vertical", "Contact Phone"],
                fields_skipped=[],
            ),
        )

        seeder = AutoCascadeSeeder(client)
        result = await seeder.seed_async(
            target_task_gid="task_gid",
            business=None,
            unit=None,
            source_process=source_process,
        )

    assert "Vertical" in result.fields_seeded
    assert "Contact Phone" in result.fields_seeded
    assert len(result.fields_skipped) == 0


@pytest.mark.asyncio
async def test_auto_cascade_exclusion_prevents_cascade():
    """Excluded fields are not cascaded even if names match."""
    client = _make_mock_client()

    target_task = MagicMock()
    target_task.custom_fields = [
        {
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_options": [{"name": "Dental", "gid": "opt1"}],
        },
        {"name": "Internal Notes", "resource_subtype": "text"},
    ]
    client.tasks.get_async.return_value = target_task

    source_process = _make_mock_process(
        custom_fields=[
            {
                "name": "Vertical",
                "resource_subtype": "enum",
                "enum_value": {"name": "Dental", "gid": "opt1"},
            },
            {
                "name": "Internal Notes",
                "resource_subtype": "text",
                "text_value": "secret notes",
            },
        ],
    )

    from autom8_asana.automation.seeding import WriteResult

    with patch("autom8_asana.lifecycle.seeding.FieldSeeder") as MockFS:
        mock_seeder_write = MockFS.return_value
        mock_seeder_write.write_fields_async = AsyncMock(
            return_value=WriteResult(
                success=True,
                fields_written=["Vertical"],
                fields_skipped=[],
            ),
        )

        seeder = AutoCascadeSeeder(client)
        result = await seeder.seed_async(
            target_task_gid="task_gid",
            business=None,
            unit=None,
            source_process=source_process,
            exclude_fields=["Internal Notes"],
        )

    # Verify write was called with only Vertical (not Internal Notes)
    call_args = mock_seeder_write.write_fields_async.call_args
    fields_arg = call_args[0][1]  # second positional arg is fields dict
    assert "Vertical" in fields_arg
    assert "Internal Notes" not in fields_arg


@pytest.mark.asyncio
async def test_auto_cascade_computed_field_overrides():
    """Computed fields override source values."""
    client = _make_mock_client()

    target_task = MagicMock()
    target_task.custom_fields = [
        {"name": "Launch Date", "resource_subtype": "text"},
        {"name": "Status", "resource_subtype": "text"},
    ]
    client.tasks.get_async.return_value = target_task

    source_process = _make_mock_process(
        custom_fields=[
            {
                "name": "Launch Date",
                "resource_subtype": "text",
                "text_value": "2025-01-01",
            },
        ],
    )

    from autom8_asana.automation.seeding import WriteResult

    with patch("autom8_asana.lifecycle.seeding.FieldSeeder") as MockFS:
        mock_seeder_write = MockFS.return_value
        mock_seeder_write.write_fields_async = AsyncMock(
            return_value=WriteResult(
                success=True,
                fields_written=["Launch Date", "Status"],
                fields_skipped=[],
            ),
        )

        seeder = AutoCascadeSeeder(client)
        result = await seeder.seed_async(
            target_task_gid="task_gid",
            business=None,
            unit=None,
            source_process=source_process,
            computed_fields={
                "Launch Date": "today",
                "Status": "New",
            },
        )

    call_args = mock_seeder_write.write_fields_async.call_args
    fields_arg = call_args[0][1]
    # Computed "today" should override source's "2025-01-01"
    assert fields_arg["Launch Date"] == date.today().isoformat()
    assert fields_arg["Status"] == "New"


@pytest.mark.asyncio
async def test_auto_cascade_precedence_process_overrides_unit_overrides_business():
    """Precedence: Process > Unit > Business for same-named field."""
    client = _make_mock_client()

    target_task = MagicMock()
    target_task.custom_fields = [
        {"name": "Priority", "resource_subtype": "text"},
    ]
    client.tasks.get_async.return_value = target_task

    business = MagicMock()
    business.custom_fields = [
        {"name": "Priority", "resource_subtype": "text", "text_value": "Low"},
    ]

    unit = MagicMock()
    unit.custom_fields = [
        {"name": "Priority", "resource_subtype": "text", "text_value": "Medium"},
    ]

    source_process = _make_mock_process(
        custom_fields=[
            {"name": "Priority", "resource_subtype": "text", "text_value": "High"},
        ],
    )

    from autom8_asana.automation.seeding import WriteResult

    with patch("autom8_asana.lifecycle.seeding.FieldSeeder") as MockFS:
        mock_seeder_write = MockFS.return_value
        mock_seeder_write.write_fields_async = AsyncMock(
            return_value=WriteResult(
                success=True,
                fields_written=["Priority"],
                fields_skipped=[],
            ),
        )

        seeder = AutoCascadeSeeder(client)
        result = await seeder.seed_async(
            target_task_gid="task_gid",
            business=business,
            unit=unit,
            source_process=source_process,
        )

    call_args = mock_seeder_write.write_fields_async.call_args
    fields_arg = call_args[0][1]
    # Process value should win (layer 3 overrides layers 1 and 2)
    assert fields_arg["Priority"] == "High"


@pytest.mark.asyncio
async def test_auto_cascade_enum_field_gid_resolution():
    """Enum fields have names extracted, GID resolution happens at write time."""
    client = _make_mock_client()

    target_task = MagicMock()
    target_task.custom_fields = [
        {
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_options": [
                {"name": "Dental", "gid": "target_opt1"},
                {"name": "Medical", "gid": "target_opt2"},
            ],
        },
    ]
    client.tasks.get_async.return_value = target_task

    source_process = _make_mock_process(
        custom_fields=[
            {
                "name": "Vertical",
                "resource_subtype": "enum",
                "enum_value": {"name": "Dental", "gid": "source_opt1"},
            },
        ],
    )

    from autom8_asana.automation.seeding import WriteResult

    with patch("autom8_asana.lifecycle.seeding.FieldSeeder") as MockFS:
        mock_seeder_write = MockFS.return_value
        mock_seeder_write.write_fields_async = AsyncMock(
            return_value=WriteResult(
                success=True,
                fields_written=["Vertical"],
                fields_skipped=[],
            ),
        )

        seeder = AutoCascadeSeeder(client)
        result = await seeder.seed_async(
            target_task_gid="task_gid",
            business=None,
            unit=None,
            source_process=source_process,
        )

    call_args = mock_seeder_write.write_fields_async.call_args
    fields_arg = call_args[0][1]
    # Value passed as name string (FieldSeeder resolves to target GID)
    assert fields_arg["Vertical"] == "Dental"
    assert "Vertical" in result.fields_seeded


# ------------------------------------------------------------------
# Duplicate Detection
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_detected_skips_creation():
    """Existing non-completed process with same ProcessType skips creation."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    # Source process has a process_holder
    holder = MagicMock()
    holder.gid = "holder_gid"
    source_process = _make_mock_process(process_holder=holder)

    # Existing non-completed task in holder with matching ProcessType
    existing_task = MagicMock()
    existing_task.gid = "existing_gid"
    existing_task.completed = False
    existing_task.custom_fields = [
        {"name": "Process Type", "display_value": "onboarding"},
    ]

    subtask_iter = MagicMock()
    subtask_iter.collect = AsyncMock(return_value=[existing_task])
    client.tasks.subtasks_async.return_value = subtask_iter

    ctx = _make_mock_ctx()
    stage_config = _make_stage_config()

    result = await service.create_process_async(
        stage_config,
        ctx,
        source_process,
    )

    assert result.success is True
    assert result.entity_gid == "existing_gid"
    assert result.was_reopened is True
    # No template discovery or creation should have been called
    client.tasks.duplicate_async.assert_not_called()
    client.tasks.create_async.assert_not_called()


@pytest.mark.asyncio
async def test_duplicate_check_completed_tasks_skipped():
    """Completed tasks in holder are not considered duplicates."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    holder = MagicMock()
    holder.gid = "holder_gid"
    source_process = _make_mock_process(process_holder=holder)

    # Completed task with matching ProcessType -- should not be a duplicate
    completed_task = MagicMock()
    completed_task.gid = "completed_gid"
    completed_task.completed = True
    completed_task.custom_fields = [
        {"name": "Process Type", "display_value": "onboarding"},
    ]

    new_task = _make_mock_task()
    client.tasks.duplicate_async.return_value = new_task

    # subtasks_async is called twice:
    #   1) duplicate check on holder (returns completed task)
    #   2) template subtask count (returns empty)
    # IMP-13: subtasks_async now only called for holder duplicate check,
    # not for template subtask count (which uses num_subtasks from discovery).
    holder_iter = MagicMock()
    holder_iter.collect = AsyncMock(return_value=[completed_task])
    client.tasks.subtasks_async = MagicMock(return_value=holder_iter)

    ctx = _make_mock_ctx()
    stage_config = _make_stage_config()

    template_task = MagicMock()
    template_task.gid = "tmpl_gid"
    template_task.name = "Onboarding Template"
    template_task.num_subtasks = 0  # IMP-13: subtask count from discovery

    with (
        patch("autom8_asana.lifecycle.creation.TemplateDiscovery") as MockTD,
        patch("autom8_asana.lifecycle.creation.AutoCascadeSeeder") as MockSeeder,
        patch("autom8_asana.lifecycle.creation.SubtaskWaiter"),
    ):
        MockTD.return_value.find_template_task_async = AsyncMock(
            return_value=template_task,
        )
        MockSeeder.return_value.seed_async = AsyncMock(
            return_value=SeedingResult(),
        )

        result = await service.create_process_async(
            stage_config,
            ctx,
            source_process,
        )

    # Completed task not treated as duplicate => creation proceeds
    assert result.success is True
    assert result.entity_gid == "new_task_gid"
    assert result.was_reopened is False


# ------------------------------------------------------------------
# Assignee Resolution
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assignee_stage_specific_field():
    """Assignee from stage-specific field on source process."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    new_task = _make_mock_task()
    source_process = _make_mock_process()
    source_process.onboarding_specialist = [
        {"gid": "specialist_gid", "name": "Specialist"},
    ]

    unit = MagicMock()
    unit.rep = None
    business = MagicMock()
    business.rep = None

    assignee_config = AssigneeConfig(
        assignee_source="onboarding_specialist",
    )

    warning = await service._set_assignee_async(
        new_task,
        source_process,
        unit,
        business,
        assignee_config,
    )

    assert warning is None
    client.tasks.set_assignee_async.assert_called_once_with(
        "new_task_gid",
        "specialist_gid",
    )


@pytest.mark.asyncio
async def test_assignee_fixed_gid():
    """Assignee from fixed GID when stage-specific field is empty."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    new_task = _make_mock_task()
    source_process = _make_mock_process()
    unit = MagicMock()
    unit.rep = None
    business = MagicMock()
    business.rep = None

    assignee_config = AssigneeConfig(assignee_gid="fixed_gid_123")

    warning = await service._set_assignee_async(
        new_task,
        source_process,
        unit,
        business,
        assignee_config,
    )

    assert warning is None
    client.tasks.set_assignee_async.assert_called_once_with(
        "new_task_gid",
        "fixed_gid_123",
    )


@pytest.mark.asyncio
async def test_assignee_fallback_to_unit_rep():
    """Assignee falls back to Unit.rep[0]."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    new_task = _make_mock_task()
    source_process = _make_mock_process()
    unit = MagicMock()
    unit.rep = [{"gid": "unit_rep_gid", "name": "Unit Rep"}]
    business = MagicMock()
    business.rep = [{"gid": "biz_rep_gid", "name": "Biz Rep"}]

    assignee_config = AssigneeConfig()  # No source or fixed GID

    warning = await service._set_assignee_async(
        new_task,
        source_process,
        unit,
        business,
        assignee_config,
    )

    assert warning is None
    client.tasks.set_assignee_async.assert_called_once_with(
        "new_task_gid",
        "unit_rep_gid",
    )


@pytest.mark.asyncio
async def test_assignee_fallback_to_business_rep():
    """Assignee falls back to Business.rep[0] when Unit.rep is empty."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    new_task = _make_mock_task()
    source_process = _make_mock_process()
    unit = MagicMock()
    unit.rep = None
    business = MagicMock()
    business.rep = [{"gid": "biz_rep_gid", "name": "Biz Rep"}]

    assignee_config = AssigneeConfig()

    warning = await service._set_assignee_async(
        new_task,
        source_process,
        unit,
        business,
        assignee_config,
    )

    assert warning is None
    client.tasks.set_assignee_async.assert_called_once_with(
        "new_task_gid",
        "biz_rep_gid",
    )


@pytest.mark.asyncio
async def test_assignee_none_available_returns_warning():
    """No assignee available produces warning."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    new_task = _make_mock_task()
    source_process = _make_mock_process()
    unit = MagicMock()
    unit.rep = None
    business = MagicMock()
    business.rep = None

    assignee_config = AssigneeConfig()

    warning = await service._set_assignee_async(
        new_task,
        source_process,
        unit,
        business,
        assignee_config,
    )

    assert warning is not None
    assert "No assignee found" in warning
    client.tasks.set_assignee_async.assert_not_called()


# ------------------------------------------------------------------
# Hierarchy Placement
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hierarchy_placement_via_process_holder():
    """When source has process_holder, use it directly (no resolution needed)."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    holder = MagicMock()
    holder.gid = "holder_gid"
    source_process = _make_mock_process(process_holder=holder)

    ctx = _make_mock_ctx()

    result = await service._resolve_holder_for_placement(
        ctx,
        "process_holder",
        source_process,
    )

    # Should use source_process.process_holder directly
    assert result is holder
    # resolve_holder_async should NOT be called since we got it from source
    ctx.resolve_holder_async.assert_not_called()


@pytest.mark.asyncio
async def test_hierarchy_placement_fallback_to_context():
    """When process_holder not on source, resolve via context."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    source_process = _make_mock_process(process_holder=None)

    resolved_holder = MagicMock()
    resolved_holder.gid = "resolved_holder_gid"

    ctx = _make_mock_ctx()
    ctx.resolve_holder_async = AsyncMock(return_value=resolved_holder)

    result = await service._resolve_holder_for_placement(
        ctx,
        "process_holder",
        source_process,
    )

    assert result is resolved_holder
    ctx.resolve_holder_async.assert_called_once()


# ------------------------------------------------------------------
# Due Date
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_due_date_calculation():
    """Due date = today + offset_days from stage config."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    new_task = _make_mock_task()
    source_process = _make_mock_process()
    business = MagicMock()
    business.custom_fields = []
    business.rep = None
    unit = MagicMock()
    unit.custom_fields = []
    unit.rep = None

    stage_config = _make_stage_config(due_date_offset_days=14)
    ctx = _make_mock_ctx(business=business, unit=unit)

    with (
        patch("autom8_asana.lifecycle.creation.AutoCascadeSeeder") as MockSeeder,
        patch("autom8_asana.lifecycle.creation.SubtaskWaiter"),
    ):
        MockSeeder.return_value.seed_async = AsyncMock(
            return_value=SeedingResult(),
        )

        warnings, _, _ = await service._configure_async(
            new_task,
            stage_config,
            ctx,
            source_process,
            business,
            unit,
            0,
        )

    expected_due = (date.today() + timedelta(days=14)).isoformat()
    client.tasks.update_async.assert_called_once_with(
        "new_task_gid",
        due_on=expected_due,
    )


@pytest.mark.asyncio
async def test_merged_due_date_and_assignee_single_call():
    """R1 boy-scout: due_date + assignee merged into single update_async call."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    new_task = _make_mock_task()
    source_process = _make_mock_process()
    business = MagicMock()
    business.custom_fields = []
    business.rep = None
    unit = MagicMock()
    unit.custom_fields = []
    unit.rep = [{"gid": "unit_rep_gid", "name": "Unit Rep"}]

    stage_config = _make_stage_config(due_date_offset_days=7)
    ctx = _make_mock_ctx(business=business, unit=unit)

    with (
        patch("autom8_asana.lifecycle.creation.AutoCascadeSeeder") as MockSeeder,
        patch("autom8_asana.lifecycle.creation.SubtaskWaiter"),
    ):
        MockSeeder.return_value.seed_async = AsyncMock(
            return_value=SeedingResult(),
        )

        warnings, _, _ = await service._configure_async(
            new_task,
            stage_config,
            ctx,
            source_process,
            business,
            unit,
            0,
        )

    expected_due = (date.today() + timedelta(days=7)).isoformat()
    # Single update_async call with both fields (R1 boy-scout)
    client.tasks.update_async.assert_called_once_with(
        "new_task_gid",
        due_on=expected_due,
        assignee="unit_rep_gid",
    )
    # set_assignee_async is NOT called (merged into update)
    client.tasks.set_assignee_async.assert_not_called()


# ------------------------------------------------------------------
# Section Placement
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_section_placement_case_insensitive():
    """Section found by case-insensitive name match."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    # Sections available in project
    section_obj = MagicMock()
    section_obj.name = "opportunity"  # lowercase
    section_obj.gid = "section_gid"

    sections_iter = MagicMock()
    sections_iter.collect = AsyncMock(return_value=[section_obj])
    client.sections.list_for_project_async.return_value = sections_iter

    result = await service._move_to_section_async(
        "task_gid",
        "proj_gid",
        "OPPORTUNITY",  # uppercase
    )

    assert result is True
    client.sections.add_task_async.assert_called_once_with(
        "section_gid",
        task="task_gid",
    )


@pytest.mark.asyncio
async def test_section_placement_not_found():
    """Returns False when section not found."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    sections_iter = MagicMock()
    sections_iter.collect = AsyncMock(return_value=[])
    client.sections.list_for_project_async.return_value = sections_iter

    result = await service._move_to_section_async(
        "task_gid",
        "proj_gid",
        "NONEXISTENT",
    )

    assert result is False
    client.sections.add_task_async.assert_not_called()


# ------------------------------------------------------------------
# Error Handling
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_creation_failure_returns_error_result():
    """Exception during creation returns error result with diagnostics."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    ctx = _make_mock_ctx()
    # Make business_async raise to simulate resolution failure
    ctx.business_async = AsyncMock(
        side_effect=ConnectionError("Network down"),
    )

    source_process = _make_mock_process()
    stage_config = _make_stage_config()

    result = await service.create_process_async(
        stage_config,
        ctx,
        source_process,
    )

    assert result.success is False
    assert result.error is not None
    assert "Network down" in result.error
    assert result.entity_gid is None


@pytest.mark.asyncio
async def test_seeding_failure_non_fatal():
    """Field seeding failure is non-fatal -- creation still succeeds."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    new_task = _make_mock_task()
    client.tasks.duplicate_async.return_value = new_task

    ctx = _make_mock_ctx()
    source_process = _make_mock_process()
    stage_config = _make_stage_config()

    template_task = MagicMock()
    template_task.gid = "tmpl_gid"
    template_task.name = "Template"
    template_task.num_subtasks = 0  # IMP-13: subtask count from discovery

    with (
        patch("autom8_asana.lifecycle.creation.TemplateDiscovery") as MockTD,
        patch("autom8_asana.lifecycle.creation.AutoCascadeSeeder") as MockSeeder,
        patch("autom8_asana.lifecycle.creation.SubtaskWaiter"),
    ):
        MockTD.return_value.find_template_task_async = AsyncMock(
            return_value=template_task,
        )
        # Seeder raises an error
        MockSeeder.return_value.seed_async = AsyncMock(
            side_effect=ConnectionError("Seeding API down"),
        )

        result = await service.create_process_async(
            stage_config,
            ctx,
            source_process,
        )

    # Creation should still succeed
    assert result.success is True
    assert result.entity_gid == "new_task_gid"
    # Warning about seeding failure
    assert any("Field seeding failed" in w for w in result.warnings)


# ------------------------------------------------------------------
# CreationResult is frozen
# ------------------------------------------------------------------


def test_creation_result_is_frozen():
    """CreationResult is a frozen (immutable) dataclass."""
    result = CreationResult(success=True, entity_gid="gid1")
    with pytest.raises(AttributeError):
        result.success = False  # type: ignore[misc]


# ------------------------------------------------------------------
# Full Integration-Style Test
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_creation_flow_with_all_configure_steps():
    """End-to-end: template found, section placed, due date set,
    fields seeded, assignee set, hierarchy placed."""
    client = _make_mock_client()
    config = MagicMock()
    service = EntityCreationService(client, config)

    # Template
    template_task = MagicMock()
    template_task.gid = "tmpl_gid"
    template_task.name = "Onboarding - [Business Name]"
    template_task.num_subtasks = 0  # IMP-13: subtask count from discovery

    new_task = _make_mock_task(gid="created_gid")
    client.tasks.duplicate_async.return_value = new_task

    # Section
    section_obj = MagicMock()
    section_obj.name = "Opportunity"
    section_obj.gid = "section_gid"
    sections_iter = MagicMock()
    sections_iter.collect = AsyncMock(return_value=[section_obj])
    client.sections.list_for_project_async.return_value = sections_iter

    # Business + Unit
    business = MagicMock()
    business.gid = "biz_gid"
    business.name = "Acme Corp"
    business.custom_fields = []
    business.rep = [{"gid": "biz_rep_gid", "name": "Biz Rep"}]

    unit = MagicMock()
    unit.gid = "unit_gid"
    unit.name = "Downtown"
    unit.custom_fields = []
    unit.rep = [{"gid": "unit_rep_gid", "name": "Unit Rep"}]

    ctx = _make_mock_ctx(business=business, unit=unit)

    source_process = _make_mock_process(process_holder=None)

    stage_config = _make_stage_config(
        due_date_offset_days=14,
        assignee=AssigneeConfig(),
    )

    with (
        patch("autom8_asana.lifecycle.creation.TemplateDiscovery") as MockTD,
        patch("autom8_asana.lifecycle.creation.AutoCascadeSeeder") as MockSeeder,
        patch("autom8_asana.lifecycle.creation.SubtaskWaiter"),
    ):
        MockTD.return_value.find_template_task_async = AsyncMock(
            return_value=template_task,
        )
        MockSeeder.return_value.seed_async = AsyncMock(
            return_value=SeedingResult(
                fields_seeded=["Vertical"],
                fields_skipped=["Internal Notes"],
            ),
        )

        result = await service.create_process_async(
            stage_config,
            ctx,
            source_process,
        )

    assert result.success is True
    assert result.entity_gid == "created_gid"
    assert result.entity_name == "Onboarding - Acme Corp"
    assert "Vertical" in result.fields_seeded
    assert "Internal Notes" in result.fields_skipped
    # R1 boy-scout: Due date + assignee merged into single update call
    expected_due = (date.today() + timedelta(days=14)).isoformat()
    client.tasks.update_async.assert_called_once_with(
        "created_gid",
        due_on=expected_due,
        assignee="unit_rep_gid",
    )
    # set_assignee_async is NOT called separately (merged into update)
    client.tasks.set_assignee_async.assert_not_called()
    # Section placement
    client.sections.add_task_async.assert_called_once_with(
        "section_gid",
        task="created_gid",
    )


# ------------------------------------------------------------------
# _matches_process_type helper
# ------------------------------------------------------------------


def test_matches_process_type_dict_format():
    """ProcessType matching with dict custom fields."""
    task = MagicMock()
    task.custom_fields = [
        {"name": "Process Type", "display_value": "onboarding"},
    ]
    assert EntityCreationService._matches_process_type(task, "onboarding") is True
    assert EntityCreationService._matches_process_type(task, "sales") is False


def test_matches_process_type_case_insensitive():
    """ProcessType matching is case-insensitive."""
    task = MagicMock()
    task.custom_fields = [
        {"name": "Process Type", "display_value": "Onboarding"},
    ]
    assert EntityCreationService._matches_process_type(task, "ONBOARDING") is True


# ------------------------------------------------------------------
# _extract_user_gid / _extract_first_rep helpers
# ------------------------------------------------------------------


def test_extract_user_gid_list_of_dicts():
    """Extract GID from list of user dicts."""
    field_val = [{"gid": "user1", "name": "John"}]
    assert EntityCreationService._extract_user_gid(field_val) == "user1"


def test_extract_user_gid_single_dict():
    """Extract GID from a single user dict."""
    field_val = {"gid": "user2", "name": "Jane"}
    assert EntityCreationService._extract_user_gid(field_val) == "user2"


def test_extract_user_gid_none():
    """Returns None when field value is None."""
    assert EntityCreationService._extract_user_gid(None) is None


def test_extract_first_rep():
    """Extract first rep GID from entity."""
    entity = MagicMock()
    entity.rep = [{"gid": "rep_gid", "name": "Rep"}]
    assert EntityCreationService._extract_first_rep(entity) == "rep_gid"


def test_extract_first_rep_empty():
    """Returns None when rep list is empty."""
    entity = MagicMock()
    entity.rep = []
    assert EntityCreationService._extract_first_rep(entity) is None


def test_extract_first_rep_none():
    """Returns None when rep is None."""
    entity = MagicMock()
    entity.rep = None
    assert EntityCreationService._extract_first_rep(entity) is None
