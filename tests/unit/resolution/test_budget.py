"""Tests for ApiBudget."""

from __future__ import annotations

import pytest

from autom8_asana.resolution.budget import ApiBudget, BudgetExhaustedError


class TestApiBudget:
    """Tests for ApiBudget."""

    def test_default_max_calls(self) -> None:
        """Test default max_calls is 8."""
        budget = ApiBudget()
        assert budget.max_calls == 8
        assert budget.used == 0

    def test_custom_max_calls(self) -> None:
        """Test custom max_calls."""
        budget = ApiBudget(max_calls=5)
        assert budget.max_calls == 5

    def test_remaining(self) -> None:
        """Test remaining property."""
        budget = ApiBudget(max_calls=10)
        assert budget.remaining == 10

        budget.used = 3
        assert budget.remaining == 7

        budget.used = 10
        assert budget.remaining == 0

    def test_remaining_negative_clamp(self) -> None:
        """Test remaining is clamped to 0."""
        budget = ApiBudget(max_calls=5)
        budget.used = 10  # Over budget
        assert budget.remaining == 0

    def test_exhausted(self) -> None:
        """Test exhausted property."""
        budget = ApiBudget(max_calls=5)
        assert budget.exhausted is False

        budget.used = 4
        assert budget.exhausted is False

        budget.used = 5
        assert budget.exhausted is True

        budget.used = 10
        assert budget.exhausted is True

    def test_consume_increments_used(self) -> None:
        """Test consume() increments used."""
        budget = ApiBudget(max_calls=10)
        budget.consume(1)
        assert budget.used == 1

        budget.consume(2)
        assert budget.used == 3

    def test_consume_default_count(self) -> None:
        """Test consume() defaults to 1."""
        budget = ApiBudget()
        budget.consume()
        assert budget.used == 1

    def test_consume_raises_when_exhausted(self) -> None:
        """Test consume() raises BudgetExhaustedError when exhausted."""
        budget = ApiBudget(max_calls=2)
        budget.used = 2

        with pytest.raises(BudgetExhaustedError) as exc_info:
            budget.consume(1)

        assert "API budget exhausted" in str(exc_info.value)
        assert "2/2" in str(exc_info.value)

    def test_consume_allows_reaching_limit(self) -> None:
        """Test consume() allows reaching but not exceeding limit."""
        budget = ApiBudget(max_calls=5)
        budget.consume(3)
        budget.consume(2)  # Should succeed, reaching exactly 5
        assert budget.used == 5
        assert budget.exhausted is True

        # Next consume should fail
        with pytest.raises(BudgetExhaustedError):
            budget.consume(1)
