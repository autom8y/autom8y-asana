"""API call budget tracking and enforcement.

Per TDD: Resolution Primitives -- ApiBudget and BudgetExhaustedError.
Prevents unbounded API call chains.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ApiBudget:
    """Tracks and enforces API call budget for a resolution chain.

    Attributes:
        max_calls: Maximum API calls allowed.
        used: Number of API calls consumed so far.
    """

    max_calls: int = 8
    used: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.max_calls - self.used)

    @property
    def exhausted(self) -> bool:
        return self.used >= self.max_calls

    def consume(self, count: int = 1) -> None:
        """Record API calls consumed.

        Args:
            count: Number of API calls to record.

        Raises:
            BudgetExhaustedError: If budget is already exhausted.
        """
        if self.exhausted:
            raise BudgetExhaustedError(
                f"API budget exhausted: {self.used}/{self.max_calls} calls used"
            )
        self.used += count


class BudgetExhaustedError(Exception):
    """Raised when API call budget is exhausted."""
