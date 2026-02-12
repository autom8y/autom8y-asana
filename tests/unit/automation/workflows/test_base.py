"""Tests for WorkflowAction protocol, WorkflowResult, WorkflowItemError, and WorkflowRegistry.

Per TDD-CONV-AUDIT-001 Section 10.1: Unit tests for pure data structures
and registry logic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from autom8_asana.automation.workflows.base import (
    WorkflowAction,
    WorkflowItemError,
    WorkflowResult,
)
from autom8_asana.automation.workflows.registry import WorkflowRegistry

# --- Concrete implementation for testing ---


class _StubWorkflow(WorkflowAction):
    """Minimal concrete implementation for testing."""

    def __init__(self, wid: str = "stub-workflow") -> None:
        self._wid = wid

    @property
    def workflow_id(self) -> str:
        return self._wid

    async def execute_async(self, params: dict[str, Any]) -> WorkflowResult:
        return WorkflowResult(
            workflow_id=self._wid,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            total=0,
            succeeded=0,
            failed=0,
            skipped=0,
        )

    async def validate_async(self) -> list[str]:
        return []


# --- WorkflowItemError Tests ---


class TestWorkflowItemError:
    """Tests for WorkflowItemError dataclass."""

    def test_creation_with_defaults(self) -> None:
        err = WorkflowItemError(
            item_id="task-123",
            error_type="export_failed",
            message="Export timed out",
        )
        assert err.item_id == "task-123"
        assert err.error_type == "export_failed"
        assert err.message == "Export timed out"
        assert err.recoverable is True  # default

    def test_creation_with_recoverable_false(self) -> None:
        err = WorkflowItemError(
            item_id="task-456",
            error_type="client_error",
            message="Bad request",
            recoverable=False,
        )
        assert err.recoverable is False


# --- WorkflowResult Tests ---


class TestWorkflowResult:
    """Tests for WorkflowResult dataclass and computed properties."""

    def _make_result(
        self,
        total: int = 10,
        succeeded: int = 7,
        failed: int = 2,
        skipped: int = 1,
        duration_seconds: float = 30.0,
    ) -> WorkflowResult:
        started = datetime(2026, 2, 10, 2, 0, 0, tzinfo=UTC)
        completed = started + timedelta(seconds=duration_seconds)
        return WorkflowResult(
            workflow_id="test-workflow",
            started_at=started,
            completed_at=completed,
            total=total,
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
        )

    def test_duration_seconds(self) -> None:
        result = self._make_result(duration_seconds=45.5)
        assert result.duration_seconds == 45.5

    def test_failure_rate(self) -> None:
        result = self._make_result(total=10, failed=2)
        assert result.failure_rate == pytest.approx(0.2)

    def test_failure_rate_zero_total(self) -> None:
        result = self._make_result(total=0, failed=0)
        assert result.failure_rate == 0.0

    def test_errors_default_empty(self) -> None:
        result = self._make_result()
        assert result.errors == []

    def test_metadata_default_empty(self) -> None:
        result = self._make_result()
        assert result.metadata == {}

    def test_errors_populated(self) -> None:
        started = datetime.now(UTC)
        result = WorkflowResult(
            workflow_id="test",
            started_at=started,
            completed_at=started + timedelta(seconds=1),
            total=1,
            succeeded=0,
            failed=1,
            skipped=0,
            errors=[
                WorkflowItemError(
                    item_id="task-1",
                    error_type="export_timeout",
                    message="timed out",
                )
            ],
        )
        assert len(result.errors) == 1
        assert result.errors[0].item_id == "task-1"

    def test_metadata_populated(self) -> None:
        started = datetime.now(UTC)
        result = WorkflowResult(
            workflow_id="test",
            started_at=started,
            completed_at=started + timedelta(seconds=1),
            total=5,
            succeeded=4,
            failed=0,
            skipped=1,
            metadata={"truncated_count": 2},
        )
        assert result.metadata["truncated_count"] == 2

    def test_to_response_dict_standard_fields(self) -> None:
        result = self._make_result(
            total=10, succeeded=7, failed=2, skipped=1, duration_seconds=30.0
        )
        d = result.to_response_dict()
        assert d == {
            "status": "completed",
            "workflow_id": "test-workflow",
            "total": 10,
            "succeeded": 7,
            "failed": 2,
            "skipped": 1,
            "duration_seconds": 30.0,
            "failure_rate": 0.2,
        }

    def test_to_response_dict_with_extra_metadata(self) -> None:
        started = datetime(2026, 2, 10, 2, 0, 0, tzinfo=UTC)
        result = WorkflowResult(
            workflow_id="test-workflow",
            started_at=started,
            completed_at=started + timedelta(seconds=10),
            total=5,
            succeeded=5,
            failed=0,
            skipped=0,
            metadata={"total_tables_succeeded": 50, "total_tables_failed": 0},
        )
        d = result.to_response_dict(
            extra_metadata_keys=["total_tables_succeeded", "total_tables_failed"],
        )
        assert d["total_tables_succeeded"] == 50
        assert d["total_tables_failed"] == 0

    def test_to_response_dict_missing_metadata_defaults_to_zero(self) -> None:
        result = self._make_result()
        d = result.to_response_dict(extra_metadata_keys=["nonexistent_key"])
        assert d["nonexistent_key"] == 0


# --- WorkflowRegistry Tests ---


class TestWorkflowRegistry:
    """Tests for WorkflowRegistry."""

    def test_register_and_get(self) -> None:
        registry = WorkflowRegistry()
        workflow = _StubWorkflow("my-workflow")
        registry.register(workflow)

        retrieved = registry.get("my-workflow")
        assert retrieved is workflow

    def test_get_unregistered_returns_none(self) -> None:
        registry = WorkflowRegistry()
        assert registry.get("nonexistent") is None

    def test_list_ids_sorted(self) -> None:
        registry = WorkflowRegistry()
        registry.register(_StubWorkflow("beta"))
        registry.register(_StubWorkflow("alpha"))
        registry.register(_StubWorkflow("gamma"))

        assert registry.list_ids() == ["alpha", "beta", "gamma"]

    def test_list_ids_empty(self) -> None:
        registry = WorkflowRegistry()
        assert registry.list_ids() == []

    def test_duplicate_registration_raises(self) -> None:
        registry = WorkflowRegistry()
        registry.register(_StubWorkflow("dup"))

        with pytest.raises(ValueError, match="already registered"):
            registry.register(_StubWorkflow("dup"))
