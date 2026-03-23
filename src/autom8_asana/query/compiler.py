"""PredicateCompiler: AST to pl.Expr with operator x dtype matrix + coercion.

The compiler is stateless and reusable. Schema is passed per-call so the same
compiler instance can serve multiple entity types.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime
from functools import reduce
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_telemetry import trace_computation

from autom8_asana.query.errors import (
    CoercionError,
    InvalidOperatorError,
    UnknownFieldError,
)
from autom8_asana.query.models import (
    AndGroup,
    Comparison,
    NotGroup,
    Op,
    OrGroup,
    PredicateNode,
)

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import DataFrameSchema

__all__ = [
    "PredicateCompiler",
    "OPERATOR_MATRIX",
    "strip_section_predicates",
]

# ---------------------------------------------------------------------------
# Operator groups
# ---------------------------------------------------------------------------

_ORDERABLE_OPS = frozenset({Op.GT, Op.LT, Op.GTE, Op.LTE})
_STRING_OPS = frozenset({Op.CONTAINS, Op.STARTS_WITH})
_UNIVERSAL_OPS = frozenset({Op.EQ, Op.NE, Op.IN, Op.NOT_IN})

# Dtypes that support ordering
_ORDERABLE_DTYPES = frozenset(
    {"Utf8", "Int64", "Int32", "Float64", "Date", "Datetime", "Decimal"}
)

# Complete compatibility matrix: dtype -> frozenset of allowed ops
OPERATOR_MATRIX: dict[str, frozenset[Op]] = {
    "Utf8": _UNIVERSAL_OPS | _ORDERABLE_OPS | _STRING_OPS,
    "Int64": _UNIVERSAL_OPS | _ORDERABLE_OPS,
    "Int32": _UNIVERSAL_OPS | _ORDERABLE_OPS,
    "Float64": _UNIVERSAL_OPS | _ORDERABLE_OPS,
    "Boolean": _UNIVERSAL_OPS,
    "Date": _UNIVERSAL_OPS | _ORDERABLE_OPS,
    "Datetime": _UNIVERSAL_OPS | _ORDERABLE_OPS,
    "Decimal": _UNIVERSAL_OPS | _ORDERABLE_OPS,
    "List[Utf8]": frozenset(),  # No operators in Sprint 1
}


# ---------------------------------------------------------------------------
# Value coercion
# ---------------------------------------------------------------------------


def _coerce_value(value: Any, dtype: str, field_name: str, op: Op) -> Any:
    """Coerce a JSON value to the target Polars dtype.

    For in/not_in operators, coerces each element in the list.

    Raises:
        CoercionError: If value cannot be coerced.
    """
    if op in (Op.IN, Op.NOT_IN):
        if not isinstance(value, list):
            raise CoercionError(
                field_name, dtype, value, "value must be a list for in/not_in"
            )
        return [_coerce_scalar(v, dtype, field_name) for v in value if v is not None]

    return _coerce_scalar(value, dtype, field_name)


def _coerce_scalar(value: Any, dtype: str, field_name: str) -> Any:
    """Coerce a single scalar value to the target dtype."""
    try:
        if dtype == "Utf8":
            return str(value)
        if dtype in ("Int64", "Int32"):
            return int(value)
        if dtype in ("Float64", "Decimal"):
            return float(value)
        if dtype == "Boolean":
            if not isinstance(value, bool):
                raise ValueError("expected boolean")
            return value
        if dtype == "Date":
            if isinstance(value, str):
                return date.fromisoformat(value)
            raise ValueError("expected ISO 8601 date string")
        if dtype == "Datetime":
            if isinstance(value, str):
                # Handle trailing Z (common in JSON)
                normalized = value.replace("Z", "+00:00")
                return datetime.fromisoformat(normalized)
            raise ValueError("expected ISO 8601 datetime string")
    except (ValueError, TypeError, OverflowError) as e:
        raise CoercionError(field_name, dtype, value, str(e)) from e

    raise CoercionError(field_name, dtype, value, f"unsupported dtype: {dtype}")


# ---------------------------------------------------------------------------
# Expression building
# ---------------------------------------------------------------------------


def _build_expr(field: str, op: Op, value: Any) -> pl.Expr:
    """Build a pl.Expr from a validated comparison."""
    col = pl.col(field)

    match op:
        case Op.EQ:
            return col == value  # type: ignore[no-any-return]
        case Op.NE:
            return col != value  # type: ignore[no-any-return]
        case Op.GT:
            return col > value  # type: ignore[no-any-return]
        case Op.LT:
            return col < value  # type: ignore[no-any-return]
        case Op.GTE:
            return col >= value  # type: ignore[no-any-return]
        case Op.LTE:
            return col <= value  # type: ignore[no-any-return]
        case Op.IN:
            return col.is_in(value)
        case Op.NOT_IN:
            return ~col.is_in(value)
        case Op.CONTAINS:
            return col.str.contains(value, literal=True)
        case Op.STARTS_WITH:
            return col.str.starts_with(value)

    # Unreachable if Op enum is exhaustive, but be explicit
    raise ValueError(f"Unknown operator: {op}")  # pragma: no cover


# ---------------------------------------------------------------------------
# PredicateCompiler
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PredicateCompiler:
    """Compiles a PredicateNode AST into a pl.Expr.

    Stateless, reusable. Schema is passed per-call so the same compiler
    instance can serve multiple entity types.
    """

    @trace_computation("predicate.compile", engine="autom8y-asana")
    def compile(
        self,
        node: PredicateNode,
        schema: DataFrameSchema,
    ) -> pl.Expr:
        """Compile a predicate tree to a Polars expression.

        Args:
            node: Root of the predicate tree.
            schema: Entity schema for field/dtype validation.

        Returns:
            A single pl.Expr that can be passed to df.filter().

        Raises:
            UnknownFieldError: Field not in schema.
            InvalidOperatorError: Op incompatible with field dtype.
            CoercionError: Value cannot be coerced to field dtype.
        """
        from opentelemetry import trace as _otel_trace

        _span = _otel_trace.get_current_span()
        start = time.perf_counter()
        result = self._compile_node(node, schema)
        _span.set_attribute(
            "computation.duration_ms", (time.perf_counter() - start) * 1000
        )
        return result

    def _compile_node(self, node: PredicateNode, schema: DataFrameSchema) -> pl.Expr:
        """Recursively compile any predicate node."""
        if isinstance(node, Comparison):
            return self._compile_comparison(node, schema)
        if isinstance(node, AndGroup):
            exprs = [self._compile_node(c, schema) for c in node.and_]
            if not exprs:
                return pl.lit(True)  # Identity element of AND (EC-005)
            return reduce(lambda a, b: a & b, exprs)
        if isinstance(node, OrGroup):
            exprs = [self._compile_node(c, schema) for c in node.or_]
            if not exprs:
                return pl.lit(False)  # Identity element of OR
            return reduce(lambda a, b: a | b, exprs)
        if isinstance(node, NotGroup):
            return ~self._compile_node(node.not_, schema)
        raise ValueError(f"Unknown node type: {type(node)}")  # pragma: no cover

    def _compile_comparison(
        self,
        node: Comparison,
        schema: DataFrameSchema,
    ) -> pl.Expr:
        """Compile a leaf comparison to pl.Expr.

        Validation order: field -> operator -> coercion -> expression.
        """
        # 1. Validate field
        col_def = schema.get_column(node.field)
        if col_def is None:
            raise UnknownFieldError(
                field=node.field,
                available=schema.column_names(),
            )

        # 2. Validate operator
        allowed_ops = OPERATOR_MATRIX.get(col_def.dtype, frozenset())
        if node.op not in allowed_ops:
            raise InvalidOperatorError(
                field=node.field,
                dtype=col_def.dtype,
                op=node.op.value,
                allowed=sorted(o.value for o in allowed_ops),
            )

        # 3. Coerce value
        coerced = _coerce_value(node.value, col_def.dtype, node.field, node.op)

        # 4. Build expression
        return _build_expr(node.field, node.op, coerced)


# ---------------------------------------------------------------------------
# Section conflict detection (EC-006)
# ---------------------------------------------------------------------------


def strip_section_predicates(node: PredicateNode) -> PredicateNode | None:
    """Recursively remove ComparisonPredicate nodes where field == "section".

    Used for EC-006: when both ``section`` parameter and ``section`` predicates
    exist in the tree, the parameter wins and predicate-level section clauses
    are stripped.

    Args:
        node: Root of the predicate tree.

    Returns:
        The pruned tree, or ``None`` if the entire tree was section-only.
    """
    if isinstance(node, Comparison):
        if node.field == "section":
            return None
        return node

    if isinstance(node, AndGroup):
        children = [strip_section_predicates(c) for c in node.and_]
        kept = [c for c in children if c is not None]
        if not kept:
            return None
        if len(kept) == 1:
            return kept[0]
        return AndGroup.model_validate({"and": [_to_raw(c) for c in kept]})

    if isinstance(node, OrGroup):
        children = [strip_section_predicates(c) for c in node.or_]
        kept = [c for c in children if c is not None]
        if not kept:
            return None
        if len(kept) == 1:
            return kept[0]
        return OrGroup.model_validate({"or": [_to_raw(c) for c in kept]})

    if isinstance(node, NotGroup):
        inner = strip_section_predicates(node.not_)
        if inner is None:
            return None
        return NotGroup.model_validate({"not": _to_raw(inner)})

    return node  # pragma: no cover


def _to_raw(node: PredicateNode) -> dict[str, Any]:
    """Serialize a PredicateNode back to dict for model_validate round-trip."""
    if isinstance(node, Comparison):
        return {"field": node.field, "op": node.op.value, "value": node.value}
    if isinstance(node, AndGroup):
        return {"and": [_to_raw(c) for c in node.and_]}
    if isinstance(node, OrGroup):
        return {"or": [_to_raw(c) for c in node.or_]}
    if isinstance(node, NotGroup):
        return {"not": _to_raw(node.not_)}
    raise ValueError(f"Unknown node type: {type(node)}")  # pragma: no cover
