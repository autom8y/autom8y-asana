"""Resolution result types.

Per TDD: Resolution Primitives -- ResolutionResult and ResolutionStatus.
Every resolution operation returns a typed result, never raw entities or None.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Generic, TypeVar

from autom8_asana.models.business.base import BusinessEntity

T = TypeVar("T", bound=BusinessEntity)


class ResolutionStatus(StrEnum):
    """Outcome of a resolution attempt."""

    RESOLVED = "resolved"  # Entity found with full confidence
    PARTIAL = "partial"  # Entity found but data may be incomplete
    FAILED = "failed"  # All strategies exhausted
    BUDGET_EXHAUSTED = "budget_exhausted"  # API call budget reached


@dataclass(frozen=True)
class ResolutionResult(Generic[T]):
    """Structured result of entity resolution.

    Attributes:
        status: Resolution outcome.
        entity: Resolved entity (None if failed).
        api_calls_used: Number of API calls consumed.
        strategy_used: Name of the strategy that resolved (or last attempted).
        diagnostics: Human-readable explanation of resolution path.
    """

    status: ResolutionStatus
    entity: T | None = None
    api_calls_used: int = 0
    strategy_used: str = ""
    diagnostics: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if entity was resolved (RESOLVED or PARTIAL)."""
        return self.status in (ResolutionStatus.RESOLVED, ResolutionStatus.PARTIAL)

    @staticmethod
    def resolved(
        entity: T,
        api_calls: int = 0,
        strategy: str = "",
    ) -> ResolutionResult[T]:
        """Factory for successful resolution."""
        return ResolutionResult(
            status=ResolutionStatus.RESOLVED,
            entity=entity,
            api_calls_used=api_calls,
            strategy_used=strategy,
        )

    @staticmethod
    def failed(
        diagnostics: list[str],
        api_calls: int = 0,
        strategy: str = "",
    ) -> ResolutionResult[Any]:
        """Factory for failed resolution."""
        return ResolutionResult[Any](
            status=ResolutionStatus.FAILED,
            api_calls_used=api_calls,
            strategy_used=strategy,
            diagnostics=diagnostics,
        )
