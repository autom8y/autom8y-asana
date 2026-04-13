"""Unit tests for PipelineConversionRule hierarchy placement.

Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT Phase 2: Test hierarchy placement.
Per FR-HIER-001: Discovers ProcessHolder from source_process.unit.process_holder.
Per FR-HIER-002: Uses set_parent() with insert_after=source_process for ordering.
Per FR-HIER-003: Graceful degradation if ProcessHolder missing or placement fails.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.pipeline import PipelineConversionRule
from autom8_asana.models.business.process import ProcessType


class MockProcessHolder:
    """Mock ProcessHolder for testing hierarchy placement."""

    def __init__(self, gid: str = "process_holder_123") -> None:
        self.gid = gid


class MockUnit:
    """Mock Unit entity for testing."""

    def __init__(
        self,
        gid: str = "unit_123",
        process_holder: MockProcessHolder | None = None,
    ) -> None:
        self.gid = gid
        self._process_holder = process_holder

    @property
    def process_holder(self) -> MockProcessHolder | None:
        return self._process_holder

    async def _fetch_holders_async(self, client: Any) -> None:
        """Mock holder fetch - does nothing by default."""
        pass


class MockProcess:
    """Mock Process entity for testing."""

    def __init__(
        self,
        gid: str = "process_123",
        name: str | None = None,
        process_type: ProcessType = ProcessType.SALES,
        unit: MockUnit | None = None,
        process_holder: MockProcessHolder | None = None,
    ) -> None:
        self.gid = gid
        self.name = name
        self.process_type = process_type
        self._unit = unit
        self._process_holder = process_holder

    @property
    def unit(self) -> MockUnit | None:
        return self._unit

    @property
    def business(self) -> Any:
        return None

    @property
    def process_holder(self) -> MockProcessHolder | None:
        return self._process_holder


class MockTask:
    """Mock Task for new task."""

    def __init__(self, gid: str = "new_task_123", name: str | None = None) -> None:
        self.gid = gid
        self.name = name


class MockSaveResult:
    """Mock SaveResult for SaveSession commit."""

    def __init__(self, success: bool = True, failed: list[Any] | None = None) -> None:
        self.success = success
        self.failed = failed or []


class TestPlaceInHierarchyAsync:
    """Tests for _place_in_hierarchy_async method."""

    @pytest.mark.asyncio
    async def test_places_task_under_process_holder_from_process(self) -> None:
        """Test placing task when ProcessHolder found via source_process."""
        rule = PipelineConversionRule()

        process_holder = MockProcessHolder("ph_123")
        source_process = MockProcess(
            gid="source_123",
            process_holder=process_holder,
        )
        new_task = MockTask("new_123")
        client = MagicMock()

        with patch("autom8_asana.automation.pipeline.SaveSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit_async = AsyncMock(return_value=MockSaveResult(success=True))
            mock_session.set_parent = MagicMock()
            mock_session_class.return_value = mock_session

            result = await rule._place_in_hierarchy_async(
                new_task=new_task,
                source_process=source_process,
                unit=None,
                client=client,
            )

        assert result is True
        mock_session.set_parent.assert_called_once_with(
            new_task,
            process_holder,
            insert_after=source_process,
        )

    @pytest.mark.asyncio
    async def test_places_task_under_process_holder_from_unit(self) -> None:
        """Test placing task when ProcessHolder found via unit."""
        rule = PipelineConversionRule()

        process_holder = MockProcessHolder("ph_123")
        unit = MockUnit(gid="unit_123", process_holder=process_holder)
        source_process = MockProcess(gid="source_123", unit=unit)
        new_task = MockTask("new_123")
        client = MagicMock()

        with patch("autom8_asana.automation.pipeline.SaveSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit_async = AsyncMock(return_value=MockSaveResult(success=True))
            mock_session.set_parent = MagicMock()
            mock_session_class.return_value = mock_session

            result = await rule._place_in_hierarchy_async(
                new_task=new_task,
                source_process=source_process,
                unit=unit,
                client=client,
            )

        assert result is True
        mock_session.set_parent.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_degradation_no_process_holder(self) -> None:
        """Test graceful degradation when no ProcessHolder available (FR-HIER-003)."""
        rule = PipelineConversionRule()

        source_process = MockProcess(gid="source_123")
        new_task = MockTask("new_123")
        client = MagicMock()

        with patch("autom8_asana.automation.pipeline.logger") as mock_logger:
            result = await rule._place_in_hierarchy_async(
                new_task=new_task,
                source_process=source_process,
                unit=None,
                client=client,
            )

        assert result is False
        mock_logger.warning.assert_called()
        # Implementation uses structured logging: logger.warning("pipeline_no_process_holder", ...)
        warning_call = str(mock_logger.warning.call_args)
        assert "pipeline_no_process_holder" in warning_call

    @pytest.mark.asyncio
    async def test_graceful_degradation_commit_fails(self) -> None:
        """Test graceful degradation when commit fails (FR-HIER-003)."""
        rule = PipelineConversionRule()

        process_holder = MockProcessHolder("ph_123")
        source_process = MockProcess(
            gid="source_123",
            process_holder=process_holder,
        )
        new_task = MockTask("new_123")
        client = MagicMock()

        with patch("autom8_asana.automation.pipeline.SaveSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            # Commit fails
            mock_session.commit_async = AsyncMock(
                return_value=MockSaveResult(success=False, failed=["error"])
            )
            mock_session.set_parent = MagicMock()
            mock_session_class.return_value = mock_session

            with patch("autom8_asana.automation.pipeline.logger") as mock_logger:
                result = await rule._place_in_hierarchy_async(
                    new_task=new_task,
                    source_process=source_process,
                    unit=None,
                    client=client,
                )

        assert result is False
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_graceful_degradation_exception(self) -> None:
        """Test graceful degradation when exception occurs (FR-HIER-003)."""
        rule = PipelineConversionRule()

        process_holder = MockProcessHolder("ph_123")
        source_process = MockProcess(
            gid="source_123",
            process_holder=process_holder,
        )
        new_task = MockTask("new_123")
        client = MagicMock()

        with patch("autom8_asana.automation.pipeline.SaveSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit_async = AsyncMock(side_effect=ConnectionError("API Error"))
            mock_session.set_parent = MagicMock()
            mock_session_class.return_value = mock_session

            with patch("autom8_asana.automation.pipeline.logger") as mock_logger:
                result = await rule._place_in_hierarchy_async(
                    new_task=new_task,
                    source_process=source_process,
                    unit=None,
                    client=client,
                )

        assert result is False
        mock_logger.warning.assert_called()
        warning_call = str(mock_logger.warning.call_args)
        assert "API Error" in warning_call

    @pytest.mark.asyncio
    async def test_graceful_degradation_when_no_hydrated_holder(self) -> None:
        """Test graceful degradation when ProcessHolder not available via public API.

        Verifies FR-HIER-003: when source_process.process_holder and unit.process_holder
        are both None, resolve_holder_async returns None and placement is skipped.
        No private attributes (_process_holder, _fetch_holders_async) are consulted.
        """
        rule = PipelineConversionRule()

        # Unit with no hydrated process_holder (public property returns None)
        unit = MockUnit(gid="unit_123", process_holder=None)
        source_process = MockProcess(gid="source_123", unit=unit)
        new_task = MockTask("new_123")
        client = MagicMock()

        with patch(
            "autom8_asana.resolution.context.ResolutionContext.resolve_holder_async",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch("autom8_asana.automation.pipeline.logger") as mock_logger:
                result = await rule._place_in_hierarchy_async(
                    new_task=new_task,
                    source_process=source_process,
                    unit=unit,
                    client=client,
                )

        assert result is False
        mock_logger.warning.assert_called()
        warning_call = str(mock_logger.warning.call_args)
        assert "pipeline_no_process_holder" in warning_call

    @pytest.mark.asyncio
    async def test_resolve_holder_async_used_as_fallback(self) -> None:
        """Test that resolve_holder_async is called as final fallback strategy.

        When source_process.process_holder and unit.process_holder are both None,
        resolve_holder_async(ProcessHolder) is called via ResolutionContext.
        This verifies the public API strategy chain mirrors lifecycle pattern.
        """
        rule = PipelineConversionRule()

        process_holder = MockProcessHolder("ph_456")
        unit = MockUnit(gid="unit_123", process_holder=None)
        source_process = MockProcess(gid="source_123", unit=unit)
        new_task = MockTask("new_123")
        client = MagicMock()

        with patch(
            "autom8_asana.resolution.context.ResolutionContext.resolve_holder_async",
            new_callable=AsyncMock,
            return_value=process_holder,
        ):
            with patch("autom8_asana.automation.pipeline.SaveSession") as mock_session_class:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session.commit_async = AsyncMock(return_value=MockSaveResult(success=True))
                mock_session.set_parent = MagicMock()
                mock_session_class.return_value = mock_session

                result = await rule._place_in_hierarchy_async(
                    new_task=new_task,
                    source_process=source_process,
                    unit=unit,
                    client=client,
                )

        assert result is True
        mock_session.set_parent.assert_called_once()
        call_args = mock_session.set_parent.call_args
        assert call_args[0][1] == process_holder

    @pytest.mark.asyncio
    async def test_disables_automation_in_nested_session(self) -> None:
        """Test that nested SaveSession has automation disabled to prevent loops."""
        rule = PipelineConversionRule()

        process_holder = MockProcessHolder("ph_123")
        source_process = MockProcess(
            gid="source_123",
            process_holder=process_holder,
        )
        new_task = MockTask("new_123")
        client = MagicMock()

        with patch("autom8_asana.automation.pipeline.SaveSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit_async = AsyncMock(return_value=MockSaveResult(success=True))
            mock_session.set_parent = MagicMock()
            mock_session_class.return_value = mock_session

            await rule._place_in_hierarchy_async(
                new_task=new_task,
                source_process=source_process,
                unit=None,
                client=client,
            )

        # Verify SaveSession was created with automation_enabled=False
        mock_session_class.assert_called_once_with(client, automation_enabled=False)
