"""Query guard rails: depth limits and row count clamping.

Per FR-008: configurable limits to prevent abuse.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from autom8_asana.query.errors import QueryTooComplexError
from autom8_asana.query.models import (
    AndGroup,
    Comparison,
    NotGroup,
    OrGroup,
    PredicateNode,
)

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import DataFrameSchema

MAX_GROUP_BY_COLUMNS: int = 5
MAX_AGGREGATIONS: int = 10


def predicate_depth(node: PredicateNode) -> int:
    """Compute max nesting depth of a predicate tree.

    - Comparison leaf = 1
    - Group node = 1 + max(children depth)
    """
    if isinstance(node, Comparison):
        return 1
    if isinstance(node, (AndGroup, OrGroup)):
        children = node.and_ if isinstance(node, AndGroup) else node.or_
        if not children:
            return 1
        return 1 + max(predicate_depth(c) for c in children)
    if isinstance(node, NotGroup):
        return 1 + predicate_depth(node.not_)
    return 1  # unreachable


@dataclass(frozen=True)
class QueryLimits:
    """Configurable query limits per FR-008."""

    max_predicate_depth: int = 5
    max_result_rows: int = 10_000
    max_aggregate_groups: int = 10_000
    max_group_by_columns: int = MAX_GROUP_BY_COLUMNS
    max_aggregations: int = MAX_AGGREGATIONS

    def check_depth(self, depth: int) -> None:
        """Reject predicates exceeding max depth.

        Raises:
            QueryTooComplexError: If depth exceeds limit.
        """
        if depth > self.max_predicate_depth:
            raise QueryTooComplexError(
                depth=depth,
                max_depth=self.max_predicate_depth,
            )

    def clamp_limit(self, requested: int) -> int:
        """Clamp the requested row limit to max_result_rows.

        Does NOT reject -- silently clamps per TDD.
        """
        return min(requested, self.max_result_rows)

    def check_group_by(
        self,
        columns: list[str],
        schema: DataFrameSchema,
    ) -> None:
        """Validate group_by columns.

        Checks:
        1. Column count within limit (MAX_GROUP_BY_COLUMNS).
        2. Each column exists in schema.
        3. No column has List dtype (cannot group on list columns).

        Raises:
            AggregationError: If any validation fails.
        """
        from autom8_asana.query.errors import AggregationError, UnknownFieldError

        if len(columns) > self.max_group_by_columns:
            raise AggregationError(
                f"Too many group_by columns ({len(columns)}). "
                f"Maximum: {self.max_group_by_columns}"
            )

        for col_name in columns:
            col_def = schema.get_column(col_name)
            if col_def is None:
                raise UnknownFieldError(
                    field=col_name,
                    available=schema.column_names(),
                )
            if col_def.dtype.startswith("List"):
                raise AggregationError(
                    f"Cannot group by List-dtype column '{col_name}' "
                    f"(dtype: {col_def.dtype}). Use a scalar column."
                )

    def check_aggregations(self, count: int) -> None:
        """Validate aggregation spec count.

        Raises:
            AggregationError: If count exceeds limit.
        """
        from autom8_asana.query.errors import AggregationError

        if count > self.max_aggregations:
            raise AggregationError(
                f"Too many aggregation specs ({count}). "
                f"Maximum: {self.max_aggregations}"
            )
