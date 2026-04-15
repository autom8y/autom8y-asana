"""Tests for reconciliation executor live execution wiring.

Per ADR-reconciliation-executor-materialization: Verifies that
execute_actions correctly delegates to task_service.move_to_section
when dry_run=False, validates dependency injection, and handles
section GID resolution failures and mixed success/failure scenarios.

Module: tests/unit/reconciliation/test_executor.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.reconciliation.executor import ExecutionResult, execute_actions
from autom8_asana.reconciliation.processor import ReconciliationAction


def _make_action(
    *,
    unit_gid: str = "unit_1",
    phone: str = "+1555***4567",
    vertical: str = "dental",
    current_section: str = "Onboarding",
    target_section: str = "Active",
    reason: str = "test action",
) -> ReconciliationAction:
    """Factory helper for ReconciliationAction instances."""
    return ReconciliationAction(
        unit_gid=unit_gid,
        phone=phone,
        vertical=vertical,
        current_section=current_section,
        target_section=target_section,
        reason=reason,
    )


SECTION_MAP = {
    "Active": "1201081073731612",
    "Onboarding": "1201081073731613",
    "Paused": "1201081073731620",
}

PROJECT_GID = "1201081073731555"


class TestExecutorDryRun:
    """Verify dry_run=True path is unchanged by executor wiring."""

    async def test_dry_run_skips_all_actions(self) -> None:
        """dry_run=True should skip all actions without calling task_service."""
        actions = [_make_action(), _make_action(unit_gid="unit_2")]
        result = await execute_actions(actions, dry_run=True)

        assert result.skipped == 2
        assert result.succeeded == 0
        assert result.failed == 0

    async def test_dry_run_ignores_injected_deps(self) -> None:
        """dry_run=True should not use task_service even if provided."""
        mock_ts = MagicMock()
        mock_client = MagicMock()
        actions = [_make_action()]

        result = await execute_actions(
            actions,
            dry_run=True,
            task_service=mock_ts,
            client=mock_client,
            project_gid=PROJECT_GID,
            section_name_to_gid=SECTION_MAP,
        )

        assert result.skipped == 1
        mock_ts.move_to_section.assert_not_called()

    async def test_empty_actions_returns_zero_counts(self) -> None:
        """Empty action list returns zero counts for both dry and live."""
        result = await execute_actions([], dry_run=True)
        assert result.skipped == 0
        assert result.succeeded == 0
        assert result.failed == 0


class TestExecutorLiveDependencyValidation:
    """Verify RuntimeError when required dependencies are missing."""

    async def test_missing_task_service_raises(self) -> None:
        """dry_run=False without task_service raises RuntimeError."""
        with pytest.raises(RuntimeError, match="task_service"):
            await execute_actions(
                [_make_action()],
                dry_run=False,
                client=MagicMock(),
                project_gid=PROJECT_GID,
                section_name_to_gid=SECTION_MAP,
            )

    async def test_missing_client_raises(self) -> None:
        """dry_run=False without client raises RuntimeError."""
        with pytest.raises(RuntimeError, match="client"):
            await execute_actions(
                [_make_action()],
                dry_run=False,
                task_service=MagicMock(),
                project_gid=PROJECT_GID,
                section_name_to_gid=SECTION_MAP,
            )

    async def test_missing_project_gid_raises(self) -> None:
        """dry_run=False without project_gid raises RuntimeError."""
        with pytest.raises(RuntimeError, match="project_gid"):
            await execute_actions(
                [_make_action()],
                dry_run=False,
                task_service=MagicMock(),
                client=MagicMock(),
                section_name_to_gid=SECTION_MAP,
            )

    async def test_missing_section_map_raises(self) -> None:
        """dry_run=False without section_name_to_gid raises RuntimeError."""
        with pytest.raises(RuntimeError, match="section_name_to_gid"):
            await execute_actions(
                [_make_action()],
                dry_run=False,
                task_service=MagicMock(),
                client=MagicMock(),
                project_gid=PROJECT_GID,
            )

    async def test_missing_all_deps_lists_all(self) -> None:
        """RuntimeError message lists all missing dependencies."""
        with pytest.raises(RuntimeError) as exc_info:
            await execute_actions(
                [_make_action()],
                dry_run=False,
            )
        msg = str(exc_info.value)
        assert "task_service" in msg
        assert "client" in msg
        assert "project_gid" in msg
        assert "section_name_to_gid" in msg

    async def test_empty_actions_skips_validation(self) -> None:
        """Empty action list returns immediately without checking deps."""
        result = await execute_actions([], dry_run=False)
        assert result.succeeded == 0
        assert result.failed == 0


class TestExecutorLiveExecution:
    """Verify live execution correctly calls task_service.move_to_section."""

    async def test_single_action_succeeds(self) -> None:
        """Single action calls move_to_section with resolved GID."""
        mock_ts = MagicMock()
        mock_ts.move_to_section = AsyncMock(return_value={"gid": "unit_1"})
        mock_client = MagicMock()

        action = _make_action(target_section="Active")
        result = await execute_actions(
            [action],
            dry_run=False,
            task_service=mock_ts,
            client=mock_client,
            project_gid=PROJECT_GID,
            section_name_to_gid=SECTION_MAP,
        )

        assert result.succeeded == 1
        assert result.failed == 0
        mock_ts.move_to_section.assert_awaited_once_with(
            mock_client,
            gid="unit_1",
            section_gid="1201081073731612",
            project_gid=PROJECT_GID,
        )

    async def test_multiple_actions_all_succeed(self) -> None:
        """Multiple successful actions increment succeeded count."""
        mock_ts = MagicMock()
        mock_ts.move_to_section = AsyncMock(return_value={"gid": "x"})
        mock_client = MagicMock()

        actions = [
            _make_action(unit_gid="u1", target_section="Active"),
            _make_action(unit_gid="u2", target_section="Onboarding"),
            _make_action(unit_gid="u3", target_section="Paused"),
        ]
        result = await execute_actions(
            actions,
            dry_run=False,
            task_service=mock_ts,
            client=mock_client,
            project_gid=PROJECT_GID,
            section_name_to_gid=SECTION_MAP,
        )

        assert result.succeeded == 3
        assert result.failed == 0
        assert mock_ts.move_to_section.await_count == 3

    async def test_api_error_records_failure_continues(self) -> None:
        """API exception records failure but does not abort remaining actions."""
        mock_ts = MagicMock()
        mock_ts.move_to_section = AsyncMock(
            side_effect=[
                {"gid": "u1"},
                Exception("Asana 429 rate limited"),
                {"gid": "u3"},
            ]
        )
        mock_client = MagicMock()

        actions = [
            _make_action(unit_gid="u1", target_section="Active"),
            _make_action(unit_gid="u2", target_section="Onboarding"),
            _make_action(unit_gid="u3", target_section="Paused"),
        ]
        result = await execute_actions(
            actions,
            dry_run=False,
            task_service=mock_ts,
            client=mock_client,
            project_gid=PROJECT_GID,
            section_name_to_gid=SECTION_MAP,
        )

        assert result.succeeded == 2
        assert result.failed == 1
        assert len(result.errors) == 1
        assert "u2" in result.errors[0]
        assert result.total_attempted == 3


class TestExecutorSectionResolution:
    """Verify section name -> GID resolution edge cases."""

    async def test_unresolvable_section_name_fails(self) -> None:
        """Action with unknown target_section records failure."""
        mock_ts = MagicMock()
        mock_ts.move_to_section = AsyncMock()
        mock_client = MagicMock()

        action = _make_action(target_section="NonExistentSection")
        result = await execute_actions(
            [action],
            dry_run=False,
            task_service=mock_ts,
            client=mock_client,
            project_gid=PROJECT_GID,
            section_name_to_gid=SECTION_MAP,
        )

        assert result.failed == 1
        assert result.succeeded == 0
        assert "NonExistentSection" in result.errors[0]
        mock_ts.move_to_section.assert_not_awaited()

    async def test_none_target_section_fails(self) -> None:
        """Action with target_section=None records failure."""
        mock_ts = MagicMock()
        mock_ts.move_to_section = AsyncMock()
        mock_client = MagicMock()

        action = _make_action(target_section=None)
        result = await execute_actions(
            [action],
            dry_run=False,
            task_service=mock_ts,
            client=mock_client,
            project_gid=PROJECT_GID,
            section_name_to_gid=SECTION_MAP,
        )

        assert result.failed == 1
        assert result.succeeded == 0

    async def test_mixed_resolvable_and_unresolvable(self) -> None:
        """Mix of resolvable and unresolvable sections counts correctly."""
        mock_ts = MagicMock()
        mock_ts.move_to_section = AsyncMock(return_value={"gid": "x"})
        mock_client = MagicMock()

        actions = [
            _make_action(unit_gid="u1", target_section="Active"),
            _make_action(unit_gid="u2", target_section="UnknownSection"),
            _make_action(unit_gid="u3", target_section="Paused"),
        ]
        result = await execute_actions(
            actions,
            dry_run=False,
            task_service=mock_ts,
            client=mock_client,
            project_gid=PROJECT_GID,
            section_name_to_gid=SECTION_MAP,
        )

        assert result.succeeded == 2
        assert result.failed == 1
        assert mock_ts.move_to_section.await_count == 2


class TestExecutionResultDataclass:
    """Verify ExecutionResult properties and defaults."""

    def test_default_values(self) -> None:
        result = ExecutionResult()
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.errors == []

    def test_total_attempted(self) -> None:
        result = ExecutionResult(succeeded=3, failed=2)
        assert result.total_attempted == 5
