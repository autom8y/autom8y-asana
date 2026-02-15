"""Tests for PipelineTransitionWorkflow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.workflows.pipeline_transition import (
    PipelineTransitionWorkflow,
)
from autom8_asana.models.business.process import ProcessType
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

    # Mock empty project
    mock_client.tasks.list_async.return_value = _AsyncIterator([])

    # Execute
    result = await workflow.execute_async(
        {"pipeline_project_gids": ["1200944186565610"]}
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

    # Mock tasks in CONVERTED section
    task1 = _make_task("task1", "Sales Process - Business A", "CONVERTED")
    task2 = _make_task("task2", "Sales Process - Business B", "CONVERTED")

    mock_client.tasks.list_async.return_value = _AsyncIterator(
        [task1, task2]
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

        # Execute
        result = await workflow.execute_async(
            {"pipeline_project_gids": ["1200944186565610"], "max_concurrency": 2}
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

    # Mock tasks in DID NOT CONVERT section
    task1 = _make_task("task1", "Sales Process - Business A", "DID NOT CONVERT")

    mock_client.tasks.list_async.return_value = _AsyncIterator([task1])

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

        # Execute
        result = await workflow.execute_async(
            {"pipeline_project_gids": ["1200944186565610"]}
        )

        # Verify
        assert result.total == 1
        assert result.succeeded == 1
        assert result.failed == 0


@pytest.mark.asyncio
async def test_execute_async_mixed_sections(lifecycle_config, mock_client):
    """Test execution with processes in mixed sections."""
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Mock tasks in various sections
    task1 = _make_task("task1", "Sales Process - Business A", "CONVERTED")
    task2 = _make_task("task2", "Sales Process - Business B", "DID NOT CONVERT")
    task3 = _make_task("task3", "Sales Process - Business C", "OPPORTUNITY")
    task4 = _make_task(
        "task4", "Sales Process - Business D", "CONVERTED", completed=True
    )

    mock_client.tasks.list_async.return_value = _AsyncIterator(
        [task1, task2, task3, task4]
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

        # Execute
        result = await workflow.execute_async(
            {"pipeline_project_gids": ["1200944186565610"]}
        )

        # Verify - only task1 and task2 should be processed
        # (task3 is not terminal, task4 is completed)
        assert result.total == 2
        assert result.succeeded == 2


@pytest.mark.asyncio
async def test_execute_async_transition_failure(lifecycle_config, mock_client):
    """Test execution when transition fails."""
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Mock task
    task1 = _make_task("task1", "Sales Process - Business A", "CONVERTED")

    mock_client.tasks.list_async.return_value = _AsyncIterator([task1])

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

        # Execute
        result = await workflow.execute_async(
            {"pipeline_project_gids": ["1200944186565610"]}
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
    task1 = _make_task("task1", "Sales Process - Business A", "CONVERTED")

    mock_client.tasks.list_async.return_value = _AsyncIterator([task1])

    # Mock engine with exception
    with patch("autom8_asana.lifecycle.engine.LifecycleEngine") as MockEngine:
        mock_engine = MockEngine.return_value
        mock_engine.handle_transition_async = AsyncMock(
            side_effect=Exception("Network error")
        )

        # Execute
        result = await workflow.execute_async(
            {"pipeline_project_gids": ["1200944186565610"]}
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
    task1 = _make_task("task1", "Sales Process", "CONVERTED")
    task2 = _make_task("task2", "Onboarding Process", "CONVERTED")

    def mock_list(*, project=None, **kwargs):
        if project == "1200944186565610":
            return _AsyncIterator([task1])
        elif project == "1201319387632570":
            return _AsyncIterator([task2])
        return _AsyncIterator([])

    mock_client.tasks.list_async = mock_list

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

        # Execute
        result = await workflow.execute_async(
            {
                "pipeline_project_gids": [
                    "1200944186565610",
                    "1201319387632570",
                ]
            }
        )

        # Verify
        assert result.total == 2
        assert result.succeeded == 2
        assert result.metadata["projects_scanned"] == 2


@pytest.mark.asyncio
async def test_execute_async_enumerate_error(lifecycle_config, mock_client):
    """Test execution when enumeration fails for a project."""
    workflow = PipelineTransitionWorkflow(mock_client, lifecycle_config)

    # Mock client to raise exception for first project, succeed for second
    task1 = _make_task("task1", "Sales Process", "CONVERTED")

    def mock_list(*, project=None, **kwargs):
        if project == "1200944186565610":
            raise Exception("Project not found")
        elif project == "1201319387632570":
            return _AsyncIterator([task1])
        return _AsyncIterator([])

    mock_client.tasks.list_async = mock_list

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

        # Execute - should continue despite first project error
        result = await workflow.execute_async(
            {
                "pipeline_project_gids": [
                    "1200944186565610",
                    "1201319387632570",
                ]
            }
        )

        # Verify - should process task from second project
        assert result.total == 1
        assert result.succeeded == 1
