"""Tests for SaveSession self-healing integration.

Per TDD-DETECTION/ADR-0095: Self-healing adds missing project memberships
to entities detected via fallback tiers (2-5) instead of deterministic Tier 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models import Task
from autom8_asana.persistence.models import (
    HealingReport,
    HealingResult,
    SaveResult,
)
from autom8_asana.persistence.session import SaveSession

# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def create_mock_client() -> MagicMock:
    """Create a mock AsanaClient with mock batch client and http client."""
    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_batch.execute_async = AsyncMock(return_value=[])
    mock_client.batch = mock_batch
    mock_client._log = None

    mock_http = AsyncMock()
    mock_http.request = AsyncMock(return_value={"data": {}})
    mock_client._http = mock_http

    return mock_client


@dataclass
class MockDetectionResult:
    """Mock detection result for testing healing logic."""

    tier_used: int
    needs_healing: bool
    expected_project_gid: str | None


def create_entity_with_detection(
    gid: str,
    name: str,
    tier_used: int = 2,
    needs_healing: bool = True,
    expected_project_gid: str | None = "proj_123",
) -> Task:
    """Create a Task with a mock _detection_result attached."""
    task = Task(gid=gid, name=name)
    task._detection_result = MockDetectionResult(  # type: ignore[attr-defined]
        tier_used=tier_used,
        needs_healing=needs_healing,
        expected_project_gid=expected_project_gid,
    )
    return task


# ---------------------------------------------------------------------------
# HealingResult Model Tests
# ---------------------------------------------------------------------------


class TestHealingResultModel:
    """Tests for HealingResult dataclass."""

    def test_healing_result_success(self) -> None:
        """HealingResult captures successful healing."""
        result = HealingResult(
            entity_gid="123",
            entity_type="Contact",
            project_gid="proj_456",
            success=True,
            error=None,
        )

        assert result.entity_gid == "123"
        assert result.entity_type == "Contact"
        assert result.project_gid == "proj_456"
        assert result.success is True
        assert result.error is None

    def test_healing_result_failure(self) -> None:
        """HealingResult captures failed healing with error."""
        result = HealingResult(
            entity_gid="123",
            entity_type="Contact",
            project_gid="proj_456",
            success=False,
            error="Not found",
        )

        assert result.success is False
        assert result.error == "Not found"

    def test_healing_result_immutable(self) -> None:
        """HealingResult is immutable (frozen dataclass)."""
        result = HealingResult(
            entity_gid="123",
            entity_type="Contact",
            project_gid="proj_456",
            success=True,
        )

        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]

    def test_healing_result_repr(self) -> None:
        """HealingResult has informative repr."""
        result = HealingResult(
            entity_gid="123",
            entity_type="Contact",
            project_gid="proj_456",
            success=True,
        )

        repr_str = repr(result)
        assert "Contact" in repr_str
        assert "123" in repr_str
        assert "proj_456" in repr_str
        assert "success" in repr_str


# ---------------------------------------------------------------------------
# HealingReport Model Tests
# ---------------------------------------------------------------------------


class TestHealingReportModel:
    """Tests for HealingReport dataclass."""

    def test_healing_report_defaults(self) -> None:
        """HealingReport has sensible defaults."""
        report = HealingReport()

        assert report.attempted == 0
        assert report.succeeded == 0
        assert report.failed == 0
        assert report.results == []

    def test_healing_report_all_succeeded_true(self) -> None:
        """all_succeeded is True when all heal operations succeed."""
        report = HealingReport(attempted=3, succeeded=3, failed=0)

        assert report.all_succeeded is True

    def test_healing_report_all_succeeded_false_on_failure(self) -> None:
        """all_succeeded is False when any heal operation fails."""
        report = HealingReport(attempted=3, succeeded=2, failed=1)

        assert report.all_succeeded is False

    def test_healing_report_all_succeeded_false_on_empty(self) -> None:
        """all_succeeded is False when no operations were attempted."""
        report = HealingReport(attempted=0, succeeded=0, failed=0)

        assert report.all_succeeded is False

    def test_healing_report_with_results(self) -> None:
        """HealingReport can hold multiple HealingResult entries."""
        results = [
            HealingResult("123", "Contact", "proj_1", True),
            HealingResult("456", "Unit", "proj_2", False, "Error"),
        ]
        report = HealingReport(
            attempted=2,
            succeeded=1,
            failed=1,
            results=results,
        )

        assert len(report.results) == 2
        assert report.results[0].success is True
        assert report.results[1].success is False

    def test_healing_report_repr(self) -> None:
        """HealingReport has informative repr."""
        report = HealingReport(attempted=5, succeeded=3, failed=2)

        repr_str = repr(report)
        assert "attempted=5" in repr_str
        assert "succeeded=3" in repr_str
        assert "failed=2" in repr_str


# ---------------------------------------------------------------------------
# SaveSession auto_heal Parameter Tests
# ---------------------------------------------------------------------------


class TestAutoHealParameter:
    """Tests for SaveSession auto_heal parameter."""

    def test_auto_heal_defaults_to_false(self) -> None:
        """auto_heal is disabled by default."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        # Per TDD-TECH-DEBT-REMEDIATION: auto_heal is managed by HealingManager
        assert session._healing_manager.auto_heal is False
        # Public property also works
        assert session.auto_heal is False

    def test_auto_heal_can_be_enabled(self) -> None:
        """auto_heal can be enabled via constructor."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        # Per TDD-TECH-DEBT-REMEDIATION: auto_heal is managed by HealingManager
        assert session._healing_manager.auto_heal is True
        # Public property also works
        assert session.auto_heal is True

    def test_healing_queue_initialized(self) -> None:
        """Healing queue is initialized in constructor."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        # Per TDD-TECH-DEBT-REMEDIATION: healing queue is managed by HealingManager
        assert hasattr(session, "_healing_manager")
        assert session._healing_manager.queue == []
        # Public property also works
        assert session.healing_queue == []

    def test_entity_heal_flags_initialized(self) -> None:
        """Per-entity heal flags dict is initialized."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        # Per TDD-TECH-DEBT-REMEDIATION: entity heal flags are managed by HealingManager
        assert hasattr(session._healing_manager, "_entity_heal_flags")
        assert session._healing_manager._entity_heal_flags == {}


# ---------------------------------------------------------------------------
# should_heal() Method Tests (via HealingManager)
# ---------------------------------------------------------------------------


class TestShouldHeal:
    """Tests for HealingManager.should_heal() method (accessed via SaveSession)."""

    def test_should_heal_false_when_auto_heal_disabled(self) -> None:
        """Returns False when auto_heal=False and no override."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=False)

        entity = create_entity_with_detection("123", "Test", tier_used=2)

        # Per TDD-TECH-DEBT-REMEDIATION: should_heal is in HealingManager
        assert session._healing_manager.should_heal(entity, None) is False

    def test_should_heal_true_when_auto_heal_enabled(self) -> None:
        """Returns True when auto_heal=True and conditions met."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection(
            "123",
            "Test",
            tier_used=2,
            needs_healing=True,
            expected_project_gid="proj_456",
        )

        assert session._healing_manager.should_heal(entity, None) is True

    def test_should_heal_override_true_forces_healing(self) -> None:
        """heal=True override enables healing even with auto_heal=False."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=False)

        entity = create_entity_with_detection("123", "Test", tier_used=2)

        assert session._healing_manager.should_heal(entity, True) is True

    def test_should_heal_override_false_prevents_healing(self) -> None:
        """heal=False override disables healing even with auto_heal=True."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=2)

        assert session._healing_manager.should_heal(entity, False) is False

    def test_should_heal_false_without_detection_result(self) -> None:
        """Returns False if entity has no _detection_result."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = Task(gid="123", name="Test")  # No detection result

        assert session._healing_manager.should_heal(entity, None) is False

    def test_should_heal_false_for_tier_1(self) -> None:
        """Returns False if entity was detected via Tier 1 (deterministic)."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection(
            "123",
            "Test",
            tier_used=1,  # Tier 1 = already in correct project
            needs_healing=False,
        )

        assert session._healing_manager.should_heal(entity, None) is False

    def test_should_heal_true_for_tier_2(self) -> None:
        """Returns True if entity was detected via Tier 2."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=2)

        assert session._healing_manager.should_heal(entity, None) is True

    def test_should_heal_true_for_tier_3(self) -> None:
        """Returns True if entity was detected via Tier 3."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=3)

        assert session._healing_manager.should_heal(entity, None) is True

    def test_should_heal_true_for_tier_4(self) -> None:
        """Returns True if entity was detected via Tier 4."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=4)

        assert session._healing_manager.should_heal(entity, None) is True

    def test_should_heal_true_for_tier_5(self) -> None:
        """Returns True if entity was detected via Tier 5 (with expected project)."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=5)

        assert session._healing_manager.should_heal(entity, None) is True

    def test_should_heal_false_without_expected_project(self) -> None:
        """Returns False if expected_project_gid is None."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection(
            "123",
            "Test",
            tier_used=2,
            needs_healing=True,
            expected_project_gid=None,
        )

        assert session._healing_manager.should_heal(entity, None) is False

    def test_should_heal_false_when_needs_healing_false(self) -> None:
        """Returns False if needs_healing flag is False."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection(
            "123",
            "Test",
            tier_used=2,
            needs_healing=False,  # Already healthy
            expected_project_gid="proj_123",
        )

        assert session._healing_manager.should_heal(entity, None) is False


# ---------------------------------------------------------------------------
# track() with heal Parameter Tests
# ---------------------------------------------------------------------------


class TestTrackWithHeal:
    """Tests for track() method with heal parameter."""

    def test_track_stores_heal_override(self) -> None:
        """track() stores per-entity heal override in HealingManager._entity_heal_flags."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        entity = Task(gid="123", name="Test")
        session.track(entity, heal=True)

        # Per TDD-TECH-DEBT-REMEDIATION: entity heal flags are managed by HealingManager
        assert session._healing_manager._entity_heal_flags.get("123") is True

    def test_track_stores_heal_false_override(self) -> None:
        """track() stores heal=False override."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        entity = Task(gid="123", name="Test")
        session.track(entity, heal=False)

        assert session._healing_manager._entity_heal_flags.get("123") is False

    def test_track_queues_healing_when_should_heal(self) -> None:
        """track() queues entity for healing when should_heal returns True."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=2)
        session.track(entity)

        # Per TDD-TECH-DEBT-REMEDIATION: queue is managed by HealingManager
        queue = session._healing_manager.queue
        assert len(queue) == 1
        queued_entity, project_gid = queue[0]
        assert queued_entity.gid == "123"
        assert project_gid == "proj_123"

    def test_track_does_not_queue_duplicates(self) -> None:
        """track() does not queue same entity twice."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=2)
        session.track(entity)
        session.track(entity)

        assert len(session._healing_manager.queue) == 1

    def test_track_does_not_queue_when_auto_heal_false(self) -> None:
        """track() does not queue when auto_heal=False and no override."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=False)

        entity = create_entity_with_detection("123", "Test", tier_used=2)
        session.track(entity)

        assert len(session._healing_manager.queue) == 0

    def test_track_with_force_heal_override(self) -> None:
        """track() with heal=True queues even when auto_heal=False."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=False)

        entity = create_entity_with_detection("123", "Test", tier_used=2)
        session.track(entity, heal=True)

        assert len(session._healing_manager.queue) == 1


# ---------------------------------------------------------------------------
# Healing Execution Tests
# ---------------------------------------------------------------------------


class TestHealingExecution:
    """Tests for healing execution during commit."""

    @pytest.mark.asyncio
    async def test_healing_executed_on_commit(self) -> None:
        """Healing is executed during commit_async()."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=2)
        session.track(entity)

        result = await session.commit_async()

        # HTTP request made for healing (add_to_project)
        mock_client._http.request.assert_called_once()
        call_args = mock_client._http.request.call_args
        assert call_args[0][0] == "POST"
        assert "/tasks/123/addProject" in call_args[0][1]

        # Healing report populated
        assert result.healing_report is not None
        assert result.healing_report.attempted == 1
        assert result.healing_report.succeeded == 1
        assert result.healing_report.failed == 0

    @pytest.mark.asyncio
    async def test_healing_report_on_success(self) -> None:
        """Successful healing populates HealingReport correctly."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Contact", tier_used=2)
        session.track(entity)

        result = await session.commit_async()

        assert result.healing_report is not None
        report = result.healing_report
        assert report.all_succeeded is True
        assert len(report.results) == 1

        healing_result = report.results[0]
        assert healing_result.entity_gid == "123"
        assert healing_result.entity_type == "Task"  # Type is determined at runtime
        assert healing_result.project_gid == "proj_123"
        assert healing_result.success is True
        assert healing_result.error is None

    @pytest.mark.asyncio
    async def test_healing_failure_non_blocking(self) -> None:
        """Healing failures are non-blocking - commit still succeeds."""
        mock_client = create_mock_client()
        mock_client._http.request = AsyncMock(side_effect=ConnectionError("API Error"))
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=2)
        session.track(entity)

        result = await session.commit_async()

        # Commit completes (does not raise)
        assert result.healing_report is not None
        assert result.healing_report.attempted == 1
        assert result.healing_report.succeeded == 0
        assert result.healing_report.failed == 1

        # Error captured in result
        healing_result = result.healing_report.results[0]
        assert healing_result.success is False
        assert "API Error" in str(healing_result.error)

    @pytest.mark.asyncio
    async def test_healing_queue_cleared_after_commit(self) -> None:
        """Healing queue is cleared after commit."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=2)
        session.track(entity)

        # Per TDD-TECH-DEBT-REMEDIATION: queue is managed by HealingManager
        assert len(session._healing_manager.queue) == 1

        await session.commit_async()

        assert len(session._healing_manager.queue) == 0

    @pytest.mark.asyncio
    async def test_healing_queue_cleared_even_on_failure(self) -> None:
        """Healing queue is cleared even when healing fails."""
        mock_client = create_mock_client()
        mock_client._http.request = AsyncMock(side_effect=ConnectionError("API Error"))
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=2)
        session.track(entity)

        await session.commit_async()

        # Per TDD-TECH-DEBT-REMEDIATION: queue is managed by HealingManager
        assert len(session._healing_manager.queue) == 0

    @pytest.mark.asyncio
    async def test_no_healing_when_queue_empty(self) -> None:
        """No healing HTTP calls when queue is empty."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        # Track entity without detection result (not queued for healing)
        entity = Task(gid="123", name="Test")
        session.track(entity)
        entity.name = "Modified"

        await session.commit_async()

        # No healing calls (only batch call for CRUD)
        # The _http.request is only for healing; batch.execute_async for CRUD
        mock_client._http.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_healing_report_none_when_no_healing(self) -> None:
        """healing_report is None when no healing was queued."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=False)

        entity = Task(gid="123", name="Test")
        session.track(entity)
        entity.name = "Modified"

        # Need to mock batch to return success
        from autom8_asana.batch.models import BatchResult

        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=200, body={"data": {"gid": "123"}}, request_index=0
                )
            ]
        )

        result = await session.commit_async()

        assert result.healing_report is None

    @pytest.mark.asyncio
    async def test_multiple_entities_healed(self) -> None:
        """Multiple entities can be healed in one commit."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity1 = create_entity_with_detection(
            "111", "Test1", tier_used=2, expected_project_gid="proj_1"
        )
        entity2 = create_entity_with_detection(
            "222", "Test2", tier_used=3, expected_project_gid="proj_2"
        )
        entity3 = create_entity_with_detection(
            "333", "Test3", tier_used=4, expected_project_gid="proj_3"
        )

        session.track(entity1)
        session.track(entity2)
        session.track(entity3)

        result = await session.commit_async()

        assert result.healing_report is not None
        assert result.healing_report.attempted == 3
        assert result.healing_report.succeeded == 3
        assert mock_client._http.request.call_count == 3

    @pytest.mark.asyncio
    async def test_partial_healing_failure(self) -> None:
        """Some healings succeed, some fail - all are reported."""
        mock_client = create_mock_client()

        # First call succeeds, second fails
        call_count = 0

        async def selective_failure(*args: Any, **kwargs: Any) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"data": {}}
            raise ConnectionError("API Error")

        mock_client._http.request = AsyncMock(side_effect=selective_failure)
        session = SaveSession(mock_client, auto_heal=True)

        entity1 = create_entity_with_detection("111", "Test1", tier_used=2)
        entity2 = create_entity_with_detection("222", "Test2", tier_used=2)

        session.track(entity1)
        session.track(entity2)

        result = await session.commit_async()

        assert result.healing_report is not None
        assert result.healing_report.attempted == 2
        assert result.healing_report.succeeded == 1
        assert result.healing_report.failed == 1
        assert result.healing_report.all_succeeded is False


# ---------------------------------------------------------------------------
# SaveResult Integration Tests
# ---------------------------------------------------------------------------


class TestSaveResultHealing:
    """Tests for SaveResult.healing_report integration."""

    def test_save_result_healing_report_default(self) -> None:
        """SaveResult.healing_report defaults to None."""
        result = SaveResult()

        assert result.healing_report is None

    def test_save_result_can_hold_healing_report(self) -> None:
        """SaveResult can store HealingReport."""
        report = HealingReport(attempted=2, succeeded=1, failed=1)
        result = SaveResult(healing_report=report)

        assert result.healing_report is report
        assert result.healing_report.attempted == 2

    @pytest.mark.asyncio
    async def test_save_result_populated_after_commit(self) -> None:
        """SaveResult.healing_report is populated after commit with healing."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=2)
        session.track(entity)

        result = await session.commit_async()

        assert result.healing_report is not None
        assert isinstance(result.healing_report, HealingReport)


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestHealingEdgeCases:
    """Edge case tests for self-healing."""

    @pytest.mark.asyncio
    async def test_healing_only_commit(self) -> None:
        """Commit with only healing (no CRUD or actions) works."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=2)
        # Manually queue healing without tracking for CRUD
        # Per TDD-TECH-DEBT-REMEDIATION: queue is managed by HealingManager
        session._healing_manager._queue.append((entity, "proj_123"))

        result = await session.commit_async()

        assert result.healing_report is not None
        assert result.healing_report.succeeded == 1

    @pytest.mark.asyncio
    async def test_healing_with_crud_and_actions(self) -> None:
        """Healing works alongside CRUD and action operations."""
        mock_client = create_mock_client()
        from autom8_asana.batch.models import BatchResult

        mock_client.batch.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=200,
                    body={"data": {"gid": "123456789"}},
                    request_index=0,
                )
            ]
        )
        session = SaveSession(mock_client, auto_heal=True)

        # Entity for CRUD + healing
        entity = create_entity_with_detection("123456789", "Test", tier_used=2)
        session.track(entity)
        entity.name = "Modified"

        # Action operation (use valid numeric GID)
        session.add_tag(entity, "987654321")

        result = await session.commit_async()

        # All three phases executed
        assert len(result.succeeded) == 1  # CRUD
        assert len(result.action_results) == 1  # Action
        assert result.healing_report is not None  # Healing
        assert result.healing_report.succeeded == 1

    def test_detection_result_without_expected_project(self) -> None:
        """Entity with detection but no expected_project_gid is not healed."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection(
            "123",
            "Test",
            tier_used=5,  # Unknown
            needs_healing=True,
            expected_project_gid=None,  # No known project
        )
        session.track(entity)

        # Per TDD-TECH-DEBT-REMEDIATION: queue is managed by HealingManager
        assert len(session._healing_manager.queue) == 0

    @pytest.mark.asyncio
    async def test_session_with_logging(self) -> None:
        """Session with logging enabled logs healing events."""
        mock_client = create_mock_client()
        mock_log = MagicMock()
        mock_client._log = mock_log

        session = SaveSession(mock_client, auto_heal=True)

        entity = create_entity_with_detection("123", "Test", tier_used=2)
        session.track(entity)

        await session.commit_async()

        # Check that logging was called
        assert mock_log.debug.called or mock_log.info.called
