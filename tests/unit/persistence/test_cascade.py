"""Tests for cascade operation infrastructure.

Per ADR-0054: Tests for CascadeOperation, CascadeResult, and CascadeExecutor.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from autom8_asana.models.business.business import Business
from autom8_asana.models.business.contact import Contact
from autom8_asana.models.business.unit import Unit
from autom8_asana.persistence.cascade import (
    CascadeExecutor,
    CascadeOperation,
    CascadeResult,
    cascade_field,
)


class TestCascadeOperation:
    """Tests for CascadeOperation dataclass."""

    def test_cascade_operation_creation(self) -> None:
        """CascadeOperation can be created with required fields."""
        business = Business(gid="123")
        op = CascadeOperation(
            source_entity=business,
            field_name="Office Phone",
        )
        assert op.source_entity is business
        assert op.field_name == "Office Phone"
        assert op.target_types is None

    def test_cascade_operation_with_target_types(self) -> None:
        """CascadeOperation can specify target types."""
        business = Business(gid="123")
        op = CascadeOperation(
            source_entity=business,
            field_name="Office Phone",
            target_types=(Unit, Contact),
        )
        assert op.target_types == (Unit, Contact)

    def test_cascade_operation_is_frozen(self) -> None:
        """CascadeOperation is immutable."""
        business = Business(gid="123")
        op = CascadeOperation(
            source_entity=business,
            field_name="Office Phone",
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            op.field_name = "Other Field"  # type: ignore


class TestCascadeResult:
    """Tests for CascadeResult dataclass."""

    def test_cascade_result_defaults(self) -> None:
        """CascadeResult has sensible defaults."""
        result = CascadeResult()
        assert result.operations_queued == 0
        assert result.operations_succeeded == 0
        assert result.operations_failed == 0
        assert result.entities_updated == []
        assert result.errors == []

    def test_cascade_result_success_property(self) -> None:
        """success returns True when no failures."""
        result = CascadeResult(
            operations_queued=5,
            operations_succeeded=5,
            operations_failed=0,
        )
        assert result.success is True

    def test_cascade_result_success_false_on_failures(self) -> None:
        """success returns False when there are failures."""
        result = CascadeResult(
            operations_queued=5,
            operations_succeeded=4,
            operations_failed=1,
        )
        assert result.success is False

    def test_cascade_result_partial_property(self) -> None:
        """partial returns True when some succeeded and some failed."""
        result = CascadeResult(
            operations_queued=5,
            operations_succeeded=3,
            operations_failed=2,
        )
        assert result.partial is True

    def test_cascade_result_partial_false_all_success(self) -> None:
        """partial returns False when all succeeded."""
        result = CascadeResult(
            operations_queued=5,
            operations_succeeded=5,
            operations_failed=0,
        )
        assert result.partial is False

    def test_cascade_result_partial_false_all_failed(self) -> None:
        """partial returns False when all failed."""
        result = CascadeResult(
            operations_queued=5,
            operations_succeeded=0,
            operations_failed=5,
        )
        assert result.partial is False


class TestCascadeFieldFactory:
    """Tests for cascade_field factory function."""

    def test_cascade_field_creates_operation(self) -> None:
        """cascade_field creates CascadeOperation."""
        business = Business(gid="123")
        op = cascade_field(business, "Office Phone")

        assert isinstance(op, CascadeOperation)
        assert op.source_entity is business
        assert op.field_name == "Office Phone"
        assert op.target_types is None

    def test_cascade_field_with_target_types(self) -> None:
        """cascade_field passes target_types."""
        business = Business(gid="123")
        op = cascade_field(business, "Office Phone", target_types=(Unit,))

        assert op.target_types == (Unit,)


class TestCascadeExecutor:
    """Tests for CascadeExecutor."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock AsanaClient."""
        client = MagicMock()
        return client

    @pytest.fixture
    def executor(self, mock_client: MagicMock) -> CascadeExecutor:
        """Create CascadeExecutor with mock client."""
        return CascadeExecutor(mock_client)

    @pytest.mark.asyncio
    async def test_execute_empty_operations(self, executor: CascadeExecutor) -> None:
        """execute with empty list returns empty result."""
        result = await executor.execute([])
        assert result.operations_queued == 0
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_returns_result(self, executor: CascadeExecutor) -> None:
        """execute returns CascadeResult."""
        business = Business(gid="123")
        op = CascadeOperation(
            source_entity=business,
            field_name="Office Phone",
        )

        result = await executor.execute([op])
        assert isinstance(result, CascadeResult)
        assert result.operations_queued == 1

    @pytest.mark.asyncio
    async def test_execute_handles_missing_field_def(
        self, executor: CascadeExecutor
    ) -> None:
        """execute handles missing cascading field definition."""
        business = Business(gid="123")
        op = CascadeOperation(
            source_entity=business,
            field_name="NonExistent Field",
        )

        result = await executor.execute([op])
        assert result.operations_failed == 1
        assert len(result.errors) == 1
        assert "NonExistent Field" in result.errors[0]
