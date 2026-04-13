"""Tests for PipelineTransitionWorkflow.

Per TDD-ENTITY-SCOPE-001: Tests migrated to enumerate_async + execute_async
pattern. Uses _enumerate_and_execute helper to simulate handler factory
orchestration.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from autom8_asana.automation.workflows.pipeline_transition import (
    PipelineTransitionWorkflow,
)
from autom8_asana.core.scope import EntityScope
from autom8_asana.persistence.models import AutomationResult


class _AsyncIterator:
    """Async iterator for mock page iterators."""

    def __init__(self, items):
        self._items = items
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item

    async def collect(self):
        return self._items


def _make_task(
    gid: str,
    name: str,
    section_name: str | None = None,
    completed: bool = False,
):
    """Create a task dict that can be used in tests.

    Returns a dict-like object with attribute access for convenience.
    Process.model_validate can handle this since it accepts dicts.
    """
    memberships = []
    if section_name:
        memberships = [
            {
                "project": {"gid": "1200944186565610", "name": "Sales Pipeline"},
                "section": {"gid": "sec1", "name": section_name},
            }
        ]

    # Create a simple object with attributes that also supports dict conversion
    class TaskDict(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.__dict__.update(kwargs)

    return TaskDict(
        gid=gid,
        name=name,
        resource_type="task",
        completed=completed,
        custom_fields=[],
        memberships=memberships,
    )


def _make_section_mock(gid: str, name: str) -> MagicMock:
    """Create a mock section object with gid and name attributes."""
    section = MagicMock()
    section.gid = gid
    section.name = name
    return section


def _setup_section_targeted_mocks(
    mock_client: MagicMock,
    section_tasks: dict[str, list] | None = None,
):
    """Configure mock_client for section-targeted fetch (primary path).

    Sets up sections.list_for_project_async to return CONVERTED and DID NOT
    CONVERT sections, and tasks.list_async to dispatch by section= kwarg.

    Args:
        mock_client: The mock AsanaClient.
        section_tasks: Optional mapping of section GID -> task list.
            Defaults to empty lists for both sections.
    """
    mock_sections = [
        _make_section_mock("sec-converted", "CONVERTED"),
        _make_section_mock("sec-dnc", "DID NOT CONVERT"),
        _make_section_mock("sec-other", "IN PROGRESS"),
    ]
    mock_client.sections.list_for_project_async.return_value = _AsyncIterator(mock_sections)

    if section_tasks is None:
        section_tasks = {"sec-converted": [], "sec-dnc": []}

    def side_effect_list_async(**kwargs):
        section_gid = kwargs.get("section")
        if section_gid and section_gid in section_tasks:
            return _AsyncIterator(section_tasks[section_gid])
        return _AsyncIterator([])

    mock_client.tasks.list_async.side_effect = side_effect_list_async


# --- Helpers ---


def _default_scope() -> EntityScope:
    """Default scope for full enumeration."""
    return EntityScope()


async def _enumerate_and_execute(
    wf: PipelineTransitionWorkflow,
    params: dict[str, Any] | None = None,
    scope: EntityScope | None = None,
    project_gids: list[str] | None = None,
) -> Any:
    """Helper: call enumerate_async then execute_async.

    Per TDD-ENTITY-SCOPE-001: The handler factory orchestrates
    enumerate -> execute. This helper simulates that for tests.

    Args:
        wf: The workflow instance.
        params: Execution params (passed to execute_async).
        scope: EntityScope (default: full enumeration).
        project_gids: Project GIDs to use for enumeration.
            Patches _default_project_gids when provided.
    """
    s = scope or _default_scope()
    p = params or {"pipeline_project_gids": ["1200944186565610"]}

    if project_gids is not None:
        with patch.object(
            type(wf),
            "_default_project_gids",
            new_callable=PropertyMock,
            return_value=project_gids,
        ):
            entities = await wf.enumerate_async(s)
    else:
        entities = await wf.enumerate_async(s)

    return await wf.execute_async(entities, p)


# --- Tests ---


@pytest.mark.asyncio
async def test_workflow_id(lifecycle_config, mock_client):
    """Test workflow_id property."""
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)
    assert workflow.workflow_id == "pipeline-transition"


@pytest.mark.asyncio
async def test_validate_async_success(lifecycle_config, mock_client):
    """Test validation passes with valid config."""
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    errors = await workflow.validate_async()

    assert errors == []


@pytest.mark.asyncio
async def test_validate_async_no_config(mock_client):
    """Test validation fails with no config."""
    workflow = PipelineTransitionWorkflow(mock_client, None)

    errors = await workflow.validate_async()

    assert len(errors) > 0
    assert "LifecycleConfig not provided" in errors[0]


@pytest.mark.asyncio
async def test_execute_async_no_processes(lifecycle_config, mock_client):
    """Test execution with no processes to transition."""
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Mock section-targeted fetch with empty sections
    _setup_section_targeted_mocks(mock_client)

    # Execute via enumerate -> execute
    result = await _enumerate_and_execute(
        workflow,
        params={"pipeline_project_gids": ["1200944186565610"]},
        project_gids=["1200944186565610"],
    )

    # Verify
    assert result.workflow_id == "pipeline-transition"
    assert result.total == 0
    assert result.succeeded == 0
    assert result.failed == 0
    assert result.skipped == 0


@pytest.mark.asyncio
async def test_execute_async_converted_processes(lifecycle_config, mock_client):
    """Test execution with processes in CONVERTED section."""
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Mock tasks in CONVERTED section (section-targeted path)
    task1 = _make_task("task1", "Sales Process - Business A")
    task2 = _make_task("task2", "Sales Process - Business B")

    _setup_section_targeted_mocks(
        mock_client,
        section_tasks={"sec-converted": [task1, task2], "sec-dnc": []},
    )

    # Mock engine
    mock_result = AutomationResult(
        rule_id="lifecycle_sales_to_onboarding",
        rule_name="Lifecycle: Sales to Onboarding",
        triggered_by_gid="task1",
        triggered_by_type="Process",
        actions_executed=["create_process"],
        entities_created=["new123"],
        entities_updated=["offer1"],
        success=True,
        execution_time_ms=100.0,
    )

    with patch("autom8_asana.lifecycle.engine.LifecycleEngine") as MockEngine:
        mock_engine = MockEngine.return_value
        mock_engine.handle_transition_async = AsyncMock(return_value=mock_result)

        # Execute via enumerate -> execute
        result = await _enumerate_and_execute(
            workflow,
            params={
                "pipeline_project_gids": ["1200944186565610"],
                "max_concurrency": 2,
            },
            project_gids=["1200944186565610"],
        )

        # Verify
        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0
        assert result.skipped == 0
        assert mock_engine.handle_transition_async.call_count == 2


@pytest.mark.asyncio
async def test_execute_async_did_not_convert_processes(lifecycle_config, mock_client):
    """Test execution with processes in DID NOT CONVERT section."""
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Mock tasks in DID NOT CONVERT section (section-targeted path)
    task1 = _make_task("task1", "Sales Process - Business A")

    _setup_section_targeted_mocks(
        mock_client,
        section_tasks={"sec-converted": [], "sec-dnc": [task1]},
    )

    # Mock engine
    mock_result = AutomationResult(
        rule_id="lifecycle_sales_to_outreach",
        rule_name="Lifecycle: Sales to Outreach",
        triggered_by_gid="task1",
        triggered_by_type="Process",
        actions_executed=["create_process"],
        entities_created=["new123"],
        success=True,
        execution_time_ms=100.0,
    )

    with patch("autom8_asana.lifecycle.engine.LifecycleEngine") as MockEngine:
        mock_engine = MockEngine.return_value
        mock_engine.handle_transition_async = AsyncMock(return_value=mock_result)

        # Execute via enumerate -> execute
        result = await _enumerate_and_execute(
            workflow,
            params={"pipeline_project_gids": ["1200944186565610"]},
            project_gids=["1200944186565610"],
        )

        # Verify
        assert result.total == 1
        assert result.succeeded == 1
        assert result.failed == 0


@pytest.mark.asyncio
async def test_execute_async_mixed_sections(lifecycle_config, mock_client):
    """Test execution with processes in mixed sections.

    On the primary section-targeted path, only CONVERTED and DID NOT CONVERT
    sections are fetched. Tasks in other sections (OPPORTUNITY) are never
    retrieved. Completed tasks are filtered out.
    """
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Only tasks in target sections are fetched on primary path
    task1 = _make_task("task1", "Sales Process - Business A")
    task2 = _make_task("task2", "Sales Process - Business B")
    task4 = _make_task("task4", "Sales Process - Business D", completed=True)

    _setup_section_targeted_mocks(
        mock_client,
        section_tasks={
            "sec-converted": [task1, task4],  # task4 is completed, filtered out
            "sec-dnc": [task2],
        },
    )

    # Mock engine
    mock_result = AutomationResult(
        rule_id="lifecycle_sales_to_onboarding",
        rule_name="Lifecycle: Sales to Onboarding",
        triggered_by_gid="task1",
        triggered_by_type="Process",
        actions_executed=["create_process"],
        success=True,
        execution_time_ms=100.0,
    )

    with patch("autom8_asana.lifecycle.engine.LifecycleEngine") as MockEngine:
        mock_engine = MockEngine.return_value
        mock_engine.handle_transition_async = AsyncMock(return_value=mock_result)

        # Execute via enumerate -> execute
        result = await _enumerate_and_execute(
            workflow,
            params={"pipeline_project_gids": ["1200944186565610"]},
            project_gids=["1200944186565610"],
        )

        # Verify - only task1 and task2 should be processed
        # (task3 not in target sections, task4 is completed)
        assert result.total == 2
        assert result.succeeded == 2


@pytest.mark.asyncio
async def test_execute_async_transition_failure(lifecycle_config, mock_client):
    """Test execution when transition fails."""
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Mock task
    task1 = _make_task("task1", "Sales Process - Business A")

    _setup_section_targeted_mocks(
        mock_client,
        section_tasks={"sec-converted": [task1], "sec-dnc": []},
    )

    # Mock engine with failure
    mock_result = AutomationResult(
        rule_id="lifecycle_error",
        rule_name="Lifecycle Error",
        triggered_by_gid="task1",
        triggered_by_type="Process",
        actions_executed=[],
        success=False,
        error="Template not found",
        execution_time_ms=50.0,
    )

    with patch("autom8_asana.lifecycle.engine.LifecycleEngine") as MockEngine:
        mock_engine = MockEngine.return_value
        mock_engine.handle_transition_async = AsyncMock(return_value=mock_result)

        # Execute via enumerate -> execute
        result = await _enumerate_and_execute(
            workflow,
            params={"pipeline_project_gids": ["1200944186565610"]},
            project_gids=["1200944186565610"],
        )

        # Verify
        assert result.total == 1
        assert result.succeeded == 0
        assert result.failed == 1
        assert len(result.errors) == 1
        assert result.errors[0].item_id == "task1"
        assert "Template not found" in result.errors[0].message


@pytest.mark.asyncio
async def test_execute_async_transition_exception(lifecycle_config, mock_client):
    """Test execution when transition raises exception."""
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Mock task
    task1 = _make_task("task1", "Sales Process - Business A")

    _setup_section_targeted_mocks(
        mock_client,
        section_tasks={"sec-converted": [task1], "sec-dnc": []},
    )

    # Mock engine with exception
    with patch("autom8_asana.lifecycle.engine.LifecycleEngine") as MockEngine:
        mock_engine = MockEngine.return_value
        mock_engine.handle_transition_async = AsyncMock(side_effect=Exception("Network error"))

        # Execute via enumerate -> execute
        result = await _enumerate_and_execute(
            workflow,
            params={"pipeline_project_gids": ["1200944186565610"]},
            project_gids=["1200944186565610"],
        )

        # Verify - exception should be caught and recorded
        assert result.total == 1
        assert result.succeeded == 0
        assert result.failed == 1
        assert len(result.errors) == 1
        assert "Network error" in result.errors[0].message


@pytest.mark.asyncio
async def test_execute_async_multiple_projects(lifecycle_config, mock_client):
    """Test execution with multiple projects."""
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Mock tasks in different projects
    task1 = _make_task("task1", "Sales Process")
    task2 = _make_task("task2", "Onboarding Process")

    # Section resolution returns matching sections for all projects
    mock_sections = [
        _make_section_mock("sec-converted", "CONVERTED"),
        _make_section_mock("sec-dnc", "DID NOT CONVERT"),
    ]
    mock_client.sections.list_for_project_async.return_value = _AsyncIterator(mock_sections)

    # Dispatch tasks by section GID; project 1 task in converted, project 2 in converted
    # Since both projects resolve the same section GIDs, we need to track
    # call count to alternate tasks per project.
    call_count = {"n": 0}

    def side_effect_list_async(**kwargs):
        section_gid = kwargs.get("section")
        if section_gid == "sec-converted":
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _AsyncIterator([task1])
            else:
                return _AsyncIterator([task2])
        return _AsyncIterator([])

    mock_client.tasks.list_async.side_effect = side_effect_list_async

    # Mock engine
    mock_result = AutomationResult(
        rule_id="lifecycle_transition",
        rule_name="Lifecycle Transition",
        triggered_by_gid="task1",
        triggered_by_type="Process",
        actions_executed=["create_process"],
        success=True,
        execution_time_ms=100.0,
    )

    with patch("autom8_asana.lifecycle.engine.LifecycleEngine") as MockEngine:
        mock_engine = MockEngine.return_value
        mock_engine.handle_transition_async = AsyncMock(return_value=mock_result)

        # Execute via enumerate -> execute
        result = await _enumerate_and_execute(
            workflow,
            params={
                "pipeline_project_gids": [
                    "1200944186565610",
                    "1201319387632570",
                ],
            },
            project_gids=[
                "1200944186565610",
                "1201319387632570",
            ],
        )

        # Verify
        assert result.total == 2
        assert result.succeeded == 2
        assert result.metadata["projects_scanned"] == 2


@pytest.mark.asyncio
async def test_execute_async_enumerate_error(lifecycle_config, mock_client):
    """Test execution when enumeration fails for a project.

    First project's section resolution raises, triggering fallback. The
    fallback also raises (project-level fetch fails), which is caught by
    the outer per-project exception handler. Second project succeeds via
    section-targeted path.
    """
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    task1 = _make_task("task1", "Sales Process", "CONVERTED")

    # Section resolution: first call raises, second returns sections
    mock_sections = [
        _make_section_mock("sec-converted", "CONVERTED"),
        _make_section_mock("sec-dnc", "DID NOT CONVERT"),
    ]

    call_count = {"sections": 0}

    def sections_side_effect(project_gid):
        call_count["sections"] += 1
        if call_count["sections"] == 1:
            raise ConnectionError("Section API unavailable")
        return _AsyncIterator(mock_sections)

    mock_client.sections.list_for_project_async.side_effect = sections_side_effect

    # Task fetch: first project fallback raises, second project section fetch works
    def tasks_side_effect(**kwargs):
        if kwargs.get("project") == "1200944186565610":
            raise ConnectionError("Project not found")
        if kwargs.get("section") == "sec-converted":
            return _AsyncIterator([task1])
        return _AsyncIterator([])

    mock_client.tasks.list_async.side_effect = tasks_side_effect

    # Mock engine
    mock_result = AutomationResult(
        rule_id="lifecycle_transition",
        rule_name="Lifecycle Transition",
        triggered_by_gid="task1",
        triggered_by_type="Process",
        actions_executed=["create_process"],
        success=True,
        execution_time_ms=100.0,
    )

    with patch("autom8_asana.lifecycle.engine.LifecycleEngine") as MockEngine:
        mock_engine = MockEngine.return_value
        mock_engine.handle_transition_async = AsyncMock(return_value=mock_result)

        # Execute via enumerate -> execute - should continue despite first project error
        result = await _enumerate_and_execute(
            workflow,
            params={
                "pipeline_project_gids": [
                    "1200944186565610",
                    "1201319387632570",
                ],
            },
            project_gids=[
                "1200944186565610",
                "1201319387632570",
            ],
        )

        # Verify - should process task from second project
        assert result.total == 1
        assert result.succeeded == 1


# ---------------------------------------------------------------------------
# New tests: section-targeted enumeration behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enumerate_section_targeted_happy_path(lifecycle_config, mock_client):
    """Primary path: section resolution succeeds, tasks fetched per section.

    Verifies correct outcome tagging (converted vs did_not_convert) based
    on which section GID the tasks were fetched from.
    """
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    task_conv = _make_task("task-c1", "Converted Process")
    task_dnc = _make_task("task-d1", "DNC Process")

    _setup_section_targeted_mocks(
        mock_client,
        section_tasks={
            "sec-converted": [task_conv],
            "sec-dnc": [task_dnc],
        },
    )

    # Mock engine
    mock_result = AutomationResult(
        rule_id="lifecycle_transition",
        rule_name="Lifecycle Transition",
        triggered_by_gid="task-c1",
        triggered_by_type="Process",
        actions_executed=["create_process"],
        success=True,
        execution_time_ms=50.0,
    )

    with patch("autom8_asana.lifecycle.engine.LifecycleEngine") as MockEngine:
        mock_engine = MockEngine.return_value
        mock_engine.handle_transition_async = AsyncMock(return_value=mock_result)

        result = await _enumerate_and_execute(
            workflow,
            params={"pipeline_project_gids": ["proj-1"]},
            project_gids=["proj-1"],
        )

        assert result.total == 2
        assert result.succeeded == 2

        # Verify outcome tagging by inspecting engine call args
        calls = mock_engine.handle_transition_async.call_args_list
        outcomes = {c.args[1] for c in calls}
        assert outcomes == {"converted", "did_not_convert"}


@pytest.mark.asyncio
async def test_enumerate_fallback_on_section_resolution_failure(lifecycle_config, mock_client):
    """Fallback: section resolution raises, falls back to project-level fetch.

    Verifies that tasks.list_async is called with project= kwarg (not section=).
    """
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Section resolution fails
    mock_client.sections.list_for_project_async.side_effect = ConnectionError("Sections API down")

    # Fallback: project-level fetch with membership data
    task1 = _make_task("task1", "Sales Process", "CONVERTED")
    mock_client.tasks.list_async.return_value = _AsyncIterator([task1])
    # Clear side_effect so return_value is used
    mock_client.tasks.list_async.side_effect = None

    result = await _enumerate_and_execute(
        workflow,
        params={"pipeline_project_gids": ["proj-1"]},
        project_gids=["proj-1"],
    )

    # Verify fallback was used: tasks.list_async called with project= kwarg
    call_kwargs = mock_client.tasks.list_async.call_args.kwargs
    assert "project" in call_kwargs
    assert "section" not in call_kwargs

    # Task should still be enumerated via fallback
    assert result.total == 1


@pytest.mark.asyncio
async def test_enumerate_fallback_on_empty_resolution(lifecycle_config, mock_client):
    """Fallback: section resolution returns empty dict (no matching sections).

    Verifies that project-level fallback is used when no target sections
    are found in the project's section list.
    """
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Sections exist but none match CONVERTED / DID NOT CONVERT
    mock_sections = [
        _make_section_mock("sec-opp", "OPPORTUNITY"),
        _make_section_mock("sec-active", "ACTIVE"),
    ]
    mock_client.sections.list_for_project_async.return_value = _AsyncIterator(mock_sections)

    # Fallback path: project-level fetch
    task1 = _make_task("task1", "Sales Process", "CONVERTED")
    mock_client.tasks.list_async.return_value = _AsyncIterator([task1])

    result = await _enumerate_and_execute(
        workflow,
        params={"pipeline_project_gids": ["proj-1"]},
        project_gids=["proj-1"],
    )

    # Verify fallback was used: tasks.list_async called with project= kwarg
    call_kwargs = mock_client.tasks.list_async.call_args.kwargs
    assert "project" in call_kwargs
    assert "section" not in call_kwargs

    assert result.total == 1


@pytest.mark.asyncio
async def test_enumerate_section_targeted_one_section_missing(lifecycle_config, mock_client):
    """Primary path with partial resolution: only CONVERTED section exists.

    When DID NOT CONVERT section is missing, resolution returns only the
    CONVERTED mapping. Only converted tasks are fetched; no DNC tasks.
    """
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Only CONVERTED section exists
    mock_sections = [
        _make_section_mock("sec-converted", "CONVERTED"),
        _make_section_mock("sec-opp", "OPPORTUNITY"),
    ]
    mock_client.sections.list_for_project_async.return_value = _AsyncIterator(mock_sections)

    task_conv = _make_task("task-c1", "Converted Process")

    def side_effect_list_async(**kwargs):
        if kwargs.get("section") == "sec-converted":
            return _AsyncIterator([task_conv])
        return _AsyncIterator([])

    mock_client.tasks.list_async.side_effect = side_effect_list_async

    # Mock engine
    mock_result = AutomationResult(
        rule_id="lifecycle_transition",
        rule_name="Lifecycle Transition",
        triggered_by_gid="task-c1",
        triggered_by_type="Process",
        actions_executed=["create_process"],
        success=True,
        execution_time_ms=50.0,
    )

    with patch("autom8_asana.lifecycle.engine.LifecycleEngine") as MockEngine:
        mock_engine = MockEngine.return_value
        mock_engine.handle_transition_async = AsyncMock(return_value=mock_result)

        result = await _enumerate_and_execute(
            workflow,
            params={"pipeline_project_gids": ["proj-1"]},
            project_gids=["proj-1"],
        )

        assert result.total == 1
        assert result.succeeded == 1

        # Verify only "converted" outcome was used
        call_args = mock_engine.handle_transition_async.call_args
        assert call_args.args[1] == "converted"


@pytest.mark.asyncio
async def test_enumerate_per_project_fallback_isolation(lifecycle_config, mock_client):
    """Per-project fallback isolation: project 1 resolves, project 2 falls back.

    Verifies that a resolution failure in one project does not affect the
    section-targeted path of another project.
    """
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    task1 = _make_task("task1", "Converted Process P1")
    task2 = _make_task("task2", "Converted Process P2", "CONVERTED")

    # Section resolution: project 1 succeeds, project 2 fails
    mock_sections = [
        _make_section_mock("sec-converted", "CONVERTED"),
        _make_section_mock("sec-dnc", "DID NOT CONVERT"),
    ]

    call_count = {"sections": 0}

    def sections_side_effect(project_gid):
        call_count["sections"] += 1
        if project_gid == "proj-2":
            raise ConnectionError("Section API unavailable for proj-2")
        return _AsyncIterator(mock_sections)

    mock_client.sections.list_for_project_async.side_effect = sections_side_effect

    # Task fetch: section-targeted for proj-1, project-level fallback for proj-2
    def tasks_side_effect(**kwargs):
        if kwargs.get("section") == "sec-converted":
            return _AsyncIterator([task1])
        if kwargs.get("section") == "sec-dnc":
            return _AsyncIterator([])
        if kwargs.get("project") == "proj-2":
            return _AsyncIterator([task2])
        return _AsyncIterator([])

    mock_client.tasks.list_async.side_effect = tasks_side_effect

    # Mock engine
    mock_result = AutomationResult(
        rule_id="lifecycle_transition",
        rule_name="Lifecycle Transition",
        triggered_by_gid="task1",
        triggered_by_type="Process",
        actions_executed=["create_process"],
        success=True,
        execution_time_ms=50.0,
    )

    with patch("autom8_asana.lifecycle.engine.LifecycleEngine") as MockEngine:
        mock_engine = MockEngine.return_value
        mock_engine.handle_transition_async = AsyncMock(return_value=mock_result)

        result = await _enumerate_and_execute(
            workflow,
            params={"pipeline_project_gids": ["proj-1", "proj-2"]},
            project_gids=["proj-1", "proj-2"],
        )

        # Both projects contribute one task each
        assert result.total == 2
        assert result.succeeded == 2
