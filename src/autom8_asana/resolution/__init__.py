"""Resolution primitives for entity resolution.

Per TDD: Resolution Primitives -- Package exports.
"""

from __future__ import annotations

from autom8_asana.resolution.budget import ApiBudget, BudgetExhaustedError
from autom8_asana.resolution.context import ResolutionContext, ResolutionError
from autom8_asana.resolution.result import ResolutionResult, ResolutionStatus
from autom8_asana.resolution.selection import (
    CompoundPredicate,
    EntitySelector,
    FieldPredicate,
    NewestActivePredicate,
    ProcessSelector,
    SelectionPredicate,
)
from autom8_asana.resolution.strategies import (
    BUSINESS_CHAIN,
    DEFAULT_CHAIN,
    DependencyShortcutStrategy,
    HierarchyTraversalStrategy,
    NavigationRefStrategy,
    ResolutionStrategy,
    SessionCacheStrategy,
)

__all__ = [
    # Budget
    "ApiBudget",
    "BudgetExhaustedError",
    # Context
    "ResolutionContext",
    "ResolutionError",
    # Result
    "ResolutionResult",
    "ResolutionStatus",
    # Selection
    "CompoundPredicate",
    "EntitySelector",
    "FieldPredicate",
    "NewestActivePredicate",
    "ProcessSelector",
    "SelectionPredicate",
    # Strategies
    "BUSINESS_CHAIN",
    "DEFAULT_CHAIN",
    "DependencyShortcutStrategy",
    "HierarchyTraversalStrategy",
    "NavigationRefStrategy",
    "ResolutionStrategy",
    "SessionCacheStrategy",
]
