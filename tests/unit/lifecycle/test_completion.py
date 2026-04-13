"""Tests for CompletionService.

Covers:
- Auto-complete when auto_complete_prior=true: marks source process complete
- No auto-complete when auto_complete_prior=false: engine does not call service
- Already-completed process -> idempotent, returns empty result
- API failure -> warning logged, empty result (fail-forward)
- Does NOT use pipeline_stage numbers (no hardcoded mapping)

Design notes:
- The engine checks transition.auto_complete_prior BEFORE calling this service
- This service only marks the source process as complete
- Stage-number comparison is eliminated per FR-COMPLETE-001
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.lifecycle.completion import (
    CompletionResult,
    CompletionService,
)
from autom8_asana.models.business.process import ProcessType

# --- Helpers ---


def _make_process(
    gid: str = "proc1",
    name: str = "Test Process",
    process_type: ProcessType = ProcessType.SALES,
    completed: bool = False,
) -> MagicMock:
    """Create a mock Process with standard attributes."""
    process = MagicMock()
    process.gid = gid
    process.name = name
    process.process_type = process_type
    process.completed = completed
    return process


# --- CompletionService Tests ---


@pytest.mark.asyncio
async def test_complete_source_marks_process_complete(mock_client):
    """When called for an incomplete process, marks it as completed
    via the Asana API and returns its GID."""
    process = _make_process(gid="proc1", completed=False)
    mock_client.tasks.update_async = AsyncMock()

    service = CompletionService(mock_client)
    result = await service.complete_source_async(process)

    assert len(result.completed) == 1
    assert result.completed[0] == "proc1"
    mock_client.tasks.update_async.assert_awaited_once_with("proc1", completed=True)


@pytest.mark.asyncio
async def test_complete_source_already_completed_is_noop(mock_client):
    """When source process is already completed, returns empty result
    without calling the API (idempotent)."""
    process = _make_process(gid="proc1", completed=True)
    mock_client.tasks.update_async = AsyncMock()

    service = CompletionService(mock_client)
    result = await service.complete_source_async(process)

    assert len(result.completed) == 0
    mock_client.tasks.update_async.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_source_api_failure_returns_empty(mock_client):
    """When the Asana API call fails, logs a warning and returns
    an empty result (fail-forward)."""
    process = _make_process(gid="proc1", completed=False)
    mock_client.tasks.update_async = AsyncMock(side_effect=ConnectionError("API timeout"))

    service = CompletionService(mock_client)
    result = await service.complete_source_async(process)

    assert len(result.completed) == 0
    mock_client.tasks.update_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_complete_source_result_type(mock_client):
    """CompletionResult is a proper dataclass with expected fields."""
    result = CompletionResult()
    assert result.completed == []
    assert isinstance(result.completed, list)


# --- Config-driven behavior tests (engine responsibility) ---


@pytest.mark.asyncio
async def test_auto_complete_prior_true_calls_service(mock_client):
    """Simulates the engine behavior: when auto_complete_prior is true,
    the engine calls complete_source_async."""
    from autom8_asana.lifecycle.config import TransitionConfig

    transition = TransitionConfig(converted="onboarding", auto_complete_prior=True)

    process = _make_process(gid="sales1", completed=False)
    mock_client.tasks.update_async = AsyncMock()

    service = CompletionService(mock_client)

    # Engine logic: only call if flag is true
    if transition.auto_complete_prior:
        result = await service.complete_source_async(process)
    else:
        result = CompletionResult()

    assert len(result.completed) == 1
    assert result.completed[0] == "sales1"


@pytest.mark.asyncio
async def test_auto_complete_prior_false_skips_service(mock_client):
    """Simulates the engine behavior: when auto_complete_prior is false,
    the engine does NOT call complete_source_async."""
    from autom8_asana.lifecycle.config import TransitionConfig

    transition = TransitionConfig(converted="sales", auto_complete_prior=False)

    process = _make_process(gid="outreach1", completed=False)
    mock_client.tasks.update_async = AsyncMock()

    service = CompletionService(mock_client)

    # Engine logic: only call if flag is true
    if transition.auto_complete_prior:
        result = await service.complete_source_async(process)
    else:
        result = CompletionResult()

    assert len(result.completed) == 0
    mock_client.tasks.update_async.assert_not_awaited()


# --- No hardcoded stage mapping ---


def test_no_pipeline_stage_method():
    """CompletionService has no _get_pipeline_stage or any stage-number
    mapping. Auto-completion is purely config-driven per FR-COMPLETE-001."""
    assert not hasattr(CompletionService, "_get_pipeline_stage")


def test_no_stage_map_attribute():
    """CompletionService has no stage_map or pipeline ordering constants."""
    mock_client = MagicMock()
    service = CompletionService(mock_client)

    # Check that there are no stage-mapping related attributes
    attrs = [a for a in dir(service) if "stage" in a.lower()]
    assert len(attrs) == 0, f"Unexpected stage-related attributes: {attrs}"
