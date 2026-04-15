"""Tests for AutomationDispatch."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.lifecycle.dispatch import AutomationDispatch
from autom8_asana.persistence.models import AutomationResult


async def test_dispatch_section_changed(mock_client, lifecycle_config):
    """Test dispatching section change event."""
    # Create mock engine
    mock_engine = MagicMock()
    mock_result = AutomationResult(
        rule_id="test",
        rule_name="Test",
        triggered_by_gid="12345",
        triggered_by_type="Process",
        success=True,
    )
    mock_engine.handle_transition_async = AsyncMock(return_value=mock_result)

    # Create dispatch
    dispatch = AutomationDispatch(mock_client, mock_engine)

    # Mock client.tasks.get_async
    mock_task = MagicMock()
    mock_task.gid = "12345"
    mock_task.model_dump = MagicMock(return_value={"gid": "12345", "name": "Test"})
    mock_client.tasks.get_async = AsyncMock(return_value=mock_task)

    # Create trigger
    trigger = {
        "id": "trigger1",
        "type": "section_changed",
        "task_gid": "12345",
        "section_name": "converted",
    }

    # Execute
    result = await dispatch.dispatch_async(trigger)

    # Verify
    assert result["success"] is True
    mock_engine.handle_transition_async.assert_called_once()


async def test_dispatch_circular_prevention(mock_client, lifecycle_config):
    """Test circular trigger prevention."""
    mock_engine = MagicMock()

    # Create dispatch
    dispatch = AutomationDispatch(mock_client, mock_engine)

    # Create trigger
    trigger = {"id": "trigger1", "type": "section_changed"}

    # Execute with same trigger in chain
    result = await dispatch.dispatch_async(trigger, trigger_chain=["trigger1"])

    # Verify circular detection
    assert result["success"] is False
    assert result["error"] == "circular_trigger"


async def test_dispatch_tag_trigger(mock_client, lifecycle_config):
    """Test dispatching tag-based trigger."""
    mock_engine = MagicMock()

    # Create dispatch
    dispatch = AutomationDispatch(mock_client, mock_engine)

    # Create trigger
    trigger = {
        "id": "trigger1",
        "type": "tag_added",
        "tag_name": "route_onboarding",
    }

    # Execute
    result = await dispatch.dispatch_async(trigger)

    # Verify routed
    assert result["success"] is True
    assert "lifecycle:onboarding" in result["routed_to"]


async def test_dispatch_unknown_trigger_type(mock_client, lifecycle_config):
    """Test unknown trigger type handling."""
    mock_engine = MagicMock()

    # Create dispatch
    dispatch = AutomationDispatch(mock_client, mock_engine)

    # Create trigger
    trigger = {"id": "trigger1", "type": "unknown_type"}

    # Execute
    result = await dispatch.dispatch_async(trigger)

    # Verify error
    assert result["success"] is False
    assert "unknown_trigger_type" in result["error"]
