"""Tests for ResolutionResult and ResolutionStatus."""

from __future__ import annotations

import pytest

from autom8_asana.resolution.result import ResolutionResult, ResolutionStatus
from tests.unit.resolution.conftest import make_business_entity


class TestResolutionStatus:
    """Tests for ResolutionStatus enum."""

    def test_status_values(self) -> None:
        """Test status enum values."""
        assert ResolutionStatus.RESOLVED == "resolved"
        assert ResolutionStatus.PARTIAL == "partial"
        assert ResolutionStatus.FAILED == "failed"
        assert ResolutionStatus.BUDGET_EXHAUSTED == "budget_exhausted"


class TestResolutionResult:
    """Tests for ResolutionResult."""

    def test_resolved_factory(self) -> None:
        """Test resolved() factory method."""
        entity = make_business_entity("test-123", "Test Entity")
        result = ResolutionResult.resolved(
            entity=entity,
            api_calls=2,
            strategy="test_strategy",
        )

        assert result.status == ResolutionStatus.RESOLVED
        assert result.entity == entity
        assert result.api_calls_used == 2
        assert result.strategy_used == "test_strategy"
        assert result.success is True

    def test_failed_factory(self) -> None:
        """Test failed() factory method."""
        diagnostics = ["strategy1: no result", "strategy2: no result"]
        result = ResolutionResult.failed(
            diagnostics=diagnostics,
            api_calls=4,
            strategy="last_strategy",
        )

        assert result.status == ResolutionStatus.FAILED
        assert result.entity is None
        assert result.api_calls_used == 4
        assert result.strategy_used == "last_strategy"
        assert result.diagnostics == diagnostics
        assert result.success is False

    def test_success_property_resolved(self) -> None:
        """Test success property returns True for RESOLVED."""
        entity = make_business_entity("test-123", "Test")
        result = ResolutionResult(
            status=ResolutionStatus.RESOLVED,
            entity=entity,
        )
        assert result.success is True

    def test_success_property_partial(self) -> None:
        """Test success property returns True for PARTIAL."""
        entity = make_business_entity("test-123", "Test")
        result = ResolutionResult(
            status=ResolutionStatus.PARTIAL,
            entity=entity,
        )
        assert result.success is True

    def test_success_property_failed(self) -> None:
        """Test success property returns False for FAILED."""
        result = ResolutionResult(
            status=ResolutionStatus.FAILED,
        )
        assert result.success is False

    def test_success_property_budget_exhausted(self) -> None:
        """Test success property returns False for BUDGET_EXHAUSTED."""
        result = ResolutionResult(
            status=ResolutionStatus.BUDGET_EXHAUSTED,
        )
        assert result.success is False

    def test_frozen_dataclass(self) -> None:
        """Test that ResolutionResult is frozen."""
        result = ResolutionResult(status=ResolutionStatus.FAILED)
        with pytest.raises(Exception):  # FrozenInstanceError
            result.status = ResolutionStatus.RESOLVED

    def test_default_diagnostics(self) -> None:
        """Test default diagnostics is empty list."""
        result = ResolutionResult(status=ResolutionStatus.FAILED)
        assert result.diagnostics == []
