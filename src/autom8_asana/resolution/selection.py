"""Entity selection predicates and selectors.

Per TDD: Resolution Primitives -- SelectionPredicate and selection strategies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.models.business.base import BusinessEntity
    from autom8_asana.models.business.process import Process, ProcessType


class SelectionPredicate(ABC):
    """Predicate for selecting entities within a holder."""

    @abstractmethod
    def matches(self, entity: BusinessEntity) -> bool:
        """Return True if entity matches this predicate."""
        ...


@dataclass(frozen=True)
class FieldPredicate(SelectionPredicate):
    """Match entity by custom field value.

    Example:
        FieldPredicate("position", "Owner")  # Contact where position == "Owner"
    """

    field_name: str
    expected_value: Any

    def matches(self, entity: BusinessEntity) -> bool:
        actual = entity.custom_fields_editor().get(self.field_name)
        if isinstance(actual, dict):
            actual = actual.get("name", actual.get("display_value"))
        return bool(actual == self.expected_value)


@dataclass(frozen=True)
class CompoundPredicate(SelectionPredicate):
    """AND/OR composition of predicates.

    Example:
        CompoundPredicate(
            operator="and",
            predicates=[
                FieldPredicate("position", "Owner"),
                FieldPredicate("status", "Active"),
            ],
        )
    """

    operator: str  # "and" | "or"
    predicates: list[SelectionPredicate]

    def matches(self, entity: BusinessEntity) -> bool:
        if self.operator == "and":
            return all(p.matches(entity) for p in self.predicates)
        return any(p.matches(entity) for p in self.predicates)


@dataclass(frozen=True)
class NewestActivePredicate(SelectionPredicate):
    """Select newest non-completed entity, or newest overall.

    Business rule: If newer entity is completed and older is incomplete,
    the incomplete one wins (represents active work).

    Used for ProcessHolder selection (most complex case).
    """

    process_type: str | None = None  # Filter by ProcessType if set

    def matches(self, entity: BusinessEntity) -> bool:
        # This predicate is used by selection strategies, not for filtering
        # The selection strategy handles ordering logic
        return True


class EntitySelector:
    """Selects entity from holder children based on predicate.

    Implements selection strategies per holder type:
    - ContactHolder: top-level default, custom field override
    - ProcessHolder: newest-active with ProcessType filter
    - OfferHolder: offer_id match, top-level fallback
    - LocationHolder: type-based (Location vs Hours)
    """

    def select(
        self,
        children: list[BusinessEntity],
        predicate: SelectionPredicate | None = None,
    ) -> BusinessEntity | None:
        """Select single entity from children.

        Args:
            children: List of holder children.
            predicate: Selection criteria. If None, returns first child.

        Returns:
            Selected entity, or None if no match.
        """
        if not children:
            return None

        if predicate is None:
            return children[0]  # top-level default

        matching = [c for c in children if predicate.matches(c)]
        return matching[0] if matching else None

    def select_all(
        self,
        children: list[BusinessEntity],
        predicate: SelectionPredicate | None = None,
    ) -> list[BusinessEntity]:
        """Select all matching entities from children.

        For multi-result selection (e.g., "all contacts except Owner").

        Args:
            children: List of holder children.
            predicate: Selection criteria. If None, returns all.

        Returns:
            List of matching entities.
        """
        if predicate is None:
            return list(children)
        return [c for c in children if predicate.matches(c)]


class ProcessSelector:
    """Specialized selection for ProcessHolder children.

    Handles the most complex selection: newest created_at with
    completion-status override (incomplete beats newer completed).
    """

    def select_current(
        self,
        processes: list[Process],
        process_type: ProcessType | None = None,
    ) -> Process | None:
        """Select current active process.

        Algorithm:
        1. Filter by process_type if specified
        2. Sort by created_at descending (newest first)
        3. If newest is completed and older is incomplete, prefer incomplete
        """
        candidates = processes
        if process_type is not None:
            candidates = [p for p in candidates if p.process_type == process_type]

        if not candidates:
            return None

        # Sort newest first
        sorted_procs = sorted(
            candidates,
            key=lambda p: p.created_at or "",
            reverse=True,
        )

        # Check completion status: incomplete beats newer completed
        newest = sorted_procs[0]
        if newest.completed and len(sorted_procs) > 1:
            for older in sorted_procs[1:]:
                if not older.completed:
                    return older

        return newest
