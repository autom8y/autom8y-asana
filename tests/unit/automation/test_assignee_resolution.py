"""Unit tests for assignee resolution in PipelineConversionRule.

Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT Phase 3: Test assignee from rep cascade.
Per ADR-0113: Rep Field Cascade Pattern (Unit.rep -> Business.rep).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.automation.pipeline import PipelineConversionRule
from autom8_asana.models.business.process import ProcessType


class MockTask:
    """Mock Task for testing."""

    def __init__(self, gid: str = "new_task_123") -> None:
        self.gid = gid


class MockProcess:
    """Mock Process entity for testing."""

    def __init__(
        self,
        gid: str = "process_123",
        name: str | None = "Test Process",
        process_type: ProcessType = ProcessType.SALES,
    ) -> None:
        self.gid = gid
        self.name = name
        self.process_type = process_type


class MockUnit:
    """Mock Unit entity for testing."""

    def __init__(self, rep: list[dict[str, Any]] | None = None) -> None:
        self._rep = rep
        self.gid = "unit_123"

    @property
    def rep(self) -> list[dict[str, Any]] | None:
        return self._rep


class MockBusiness:
    """Mock Business entity for testing."""

    def __init__(self, rep: list[dict[str, Any]] | None = None) -> None:
        self._rep = rep
        self.gid = "business_123"
        self.name = "Test Business"

    @property
    def rep(self) -> list[dict[str, Any]] | None:
        return self._rep


class TestSetAssigneeFromRepAsync:
    """Tests for _set_assignee_from_rep_async method."""

    @pytest.fixture
    def rule(self) -> PipelineConversionRule:
        """Create a PipelineConversionRule for testing."""
        return PipelineConversionRule()

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock client with tasks.set_assignee_async."""
        client = MagicMock()
        client.tasks = MagicMock()
        client.tasks.set_assignee_async = AsyncMock(return_value=MockTask())
        return client

    async def test_unit_rep_present_uses_unit_rep(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test FR-ASSIGN-002: Unit.rep takes precedence when present."""
        unit = MockUnit(rep=[{"gid": "unit_rep_123", "name": "Unit Rep"}])
        business = MockBusiness(rep=[{"gid": "business_rep_456", "name": "Business Rep"}])
        new_task = MockTask("new_task_gid")
        source_process = MockProcess()

        result = await rule._set_assignee_from_rep_async(
            new_task=new_task,
            source_process=source_process,
            unit=unit,
            business=business,
            client=mock_client,
        )

        assert result is True
        mock_client.tasks.set_assignee_async.assert_called_once_with("new_task_gid", "unit_rep_123")

    async def test_unit_rep_empty_fallback_to_business_rep(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test FR-ASSIGN-003: Fallback to Business.rep when Unit.rep is empty."""
        unit = MockUnit(rep=[])  # Empty list
        business = MockBusiness(rep=[{"gid": "business_rep_456", "name": "Business Rep"}])
        new_task = MockTask("new_task_gid")
        source_process = MockProcess()

        result = await rule._set_assignee_from_rep_async(
            new_task=new_task,
            source_process=source_process,
            unit=unit,
            business=business,
            client=mock_client,
        )

        assert result is True
        mock_client.tasks.set_assignee_async.assert_called_once_with(
            "new_task_gid", "business_rep_456"
        )

    async def test_unit_rep_none_fallback_to_business_rep(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test FR-ASSIGN-003: Fallback to Business.rep when Unit.rep is None."""
        unit = MockUnit(rep=None)
        business = MockBusiness(rep=[{"gid": "business_rep_456", "name": "Business Rep"}])
        new_task = MockTask("new_task_gid")
        source_process = MockProcess()

        result = await rule._set_assignee_from_rep_async(
            new_task=new_task,
            source_process=source_process,
            unit=unit,
            business=business,
            client=mock_client,
        )

        assert result is True
        mock_client.tasks.set_assignee_async.assert_called_once_with(
            "new_task_gid", "business_rep_456"
        )

    async def test_both_rep_empty_logs_warning_returns_false(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test FR-ASSIGN-005: Empty rep logs warning, continues without assignee."""
        unit = MockUnit(rep=[])
        business = MockBusiness(rep=[])
        new_task = MockTask("new_task_gid")
        source_process = MockProcess()

        result = await rule._set_assignee_from_rep_async(
            new_task=new_task,
            source_process=source_process,
            unit=unit,
            business=business,
            client=mock_client,
        )

        assert result is False
        mock_client.tasks.set_assignee_async.assert_not_called()

    async def test_unit_none_uses_business_rep(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test that when unit is None, Business.rep is used."""
        business = MockBusiness(rep=[{"gid": "business_rep_456", "name": "Business Rep"}])
        new_task = MockTask("new_task_gid")
        source_process = MockProcess()

        result = await rule._set_assignee_from_rep_async(
            new_task=new_task,
            source_process=source_process,
            unit=None,
            business=business,
            client=mock_client,
        )

        assert result is True
        mock_client.tasks.set_assignee_async.assert_called_once_with(
            "new_task_gid", "business_rep_456"
        )

    async def test_rep_list_with_multiple_users_uses_first(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test FR-ASSIGN-004: First user in rep list is used as assignee."""
        unit = MockUnit(
            rep=[
                {"gid": "first_rep_123", "name": "First Rep"},
                {"gid": "second_rep_456", "name": "Second Rep"},
                {"gid": "third_rep_789", "name": "Third Rep"},
            ]
        )
        new_task = MockTask("new_task_gid")
        source_process = MockProcess()

        result = await rule._set_assignee_from_rep_async(
            new_task=new_task,
            source_process=source_process,
            unit=unit,
            business=None,
            client=mock_client,
        )

        assert result is True
        mock_client.tasks.set_assignee_async.assert_called_once_with(
            "new_task_gid", "first_rep_123"
        )

    async def test_set_assignee_async_fails_logs_warning_continues(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test FR-ASSIGN-006: Graceful degradation when set_assignee_async fails."""
        mock_client.tasks.set_assignee_async = AsyncMock(
            side_effect=ConnectionError("API Error: User not found")
        )
        unit = MockUnit(rep=[{"gid": "unit_rep_123", "name": "Unit Rep"}])
        new_task = MockTask("new_task_gid")
        source_process = MockProcess()

        result = await rule._set_assignee_from_rep_async(
            new_task=new_task,
            source_process=source_process,
            unit=unit,
            business=None,
            client=mock_client,
        )

        # Should return False (graceful degradation), not raise
        assert result is False
        mock_client.tasks.set_assignee_async.assert_called_once()

    async def test_unit_and_business_none_returns_false(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test that when both unit and business are None, returns False."""
        new_task = MockTask("new_task_gid")
        source_process = MockProcess()

        result = await rule._set_assignee_from_rep_async(
            new_task=new_task,
            source_process=source_process,
            unit=None,
            business=None,
            client=mock_client,
        )

        assert result is False
        mock_client.tasks.set_assignee_async.assert_not_called()

    async def test_rep_dict_without_gid_skips_and_falls_back(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test handling of malformed rep dict without gid key."""
        unit = MockUnit(rep=[{"name": "No GID User"}])  # Missing 'gid' key
        business = MockBusiness(rep=[{"gid": "business_rep_456", "name": "Business Rep"}])
        new_task = MockTask("new_task_gid")
        source_process = MockProcess()

        result = await rule._set_assignee_from_rep_async(
            new_task=new_task,
            source_process=source_process,
            unit=unit,
            business=business,
            client=mock_client,
        )

        assert result is True
        # Should fall back to business rep since unit rep has no gid
        mock_client.tasks.set_assignee_async.assert_called_once_with(
            "new_task_gid", "business_rep_456"
        )
