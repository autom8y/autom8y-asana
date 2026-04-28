"""Helpers for the Phase 1 ``/exports`` route handler.

Per TDD §3.4 + §8 + §9:
- ``attach_identity_complete`` is the SINGLE source-of-truth for the
  ``identity_complete`` boolean column (P1-C-05). Computed at extraction time,
  NOT in ``cascade_validator.py:185-191`` and NOT in
  ``cascade_resolver.py``.
- ``filter_incomplete_identity`` implements opt-in suppression via
  ``options.include_incomplete_identity=false`` (PRD AC-6). Default behavior
  retains null-key rows with ``identity_complete=false`` so SCAR-005/006
  transparency is preserved (PRD AC-5).
- ``dedupe_by_key`` provides the deterministic ``most-recent-by-modified_at``
  policy disposed in TDD §3.4 + DEFER-WATCH-1.
- ``apply_active_default_section_predicate`` injects an ACTIVE-only ``section``
  filter when (and only when) the caller's predicate omits ``section``
  entirely — TDD §9.3 + DEFER-WATCH-3 disposition.
- ``validate_section_values`` walks the predicate tree and rejects any
  ``section`` value not in ``PROCESS_PIPELINE_SECTIONS`` per PRD §9.2 +
  TDD §9.4.

All transforms operate on eager ``pl.DataFrame`` per P1-C-06 (no LazyFrame
consumer surface in Phase 1).
"""

from __future__ import annotations

from datetime import date as _date
from datetime import datetime as _datetime
from typing import Any

import polars as pl

from autom8y_log import get_logger

from autom8_asana.models.business.activity import PROCESS_PIPELINE_SECTIONS
from autom8_asana.query.models import (
    AndGroup,
    Comparison,
    NotGroup,
    Op,
    OrGroup,
    PredicateNode,
)
from autom8_asana.query.temporal import parse_date_or_relative

__all__ = [
    "ACTIVE_SECTIONS",
    "VALID_SECTIONS",
    "attach_identity_complete",
    "filter_incomplete_identity",
    "dedupe_by_key",
    "apply_active_default_section_predicate",
    "validate_section_values",
    "predicate_references_field",
    "translate_date_predicates",
    "DateTranslationResult",
    "InvalidSectionError",
]

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Section vocabulary (sourced from activity.py canonical map)
# ---------------------------------------------------------------------------


def _flatten_sections() -> set[str]:
    """Collect every admissible section name across PROCESS_PIPELINE_SECTIONS."""
    seen: set[str] = set()
    for class_map in PROCESS_PIPELINE_SECTIONS.values():
        for names in class_map.values():
            seen.update(names)
    return seen


def _flatten_active_sections() -> set[str]:
    """Collect ACTIVE-class section names — the Phase 1 default per TDD §9.3."""
    seen: set[str] = set()
    for class_map in PROCESS_PIPELINE_SECTIONS.values():
        seen.update(class_map.get("active", set()))
    return seen


VALID_SECTIONS: frozenset[str] = frozenset(_flatten_sections())
ACTIVE_SECTIONS: frozenset[str] = frozenset(_flatten_active_sections())


class InvalidSectionError(ValueError):
    """Raised when caller predicate references a section not in the canonical vocabulary.

    Surfaced at the route handler as HTTP 400 with ``error.code:
    "unknown_section_value"`` per PRD §9.2.
    """

    def __init__(self, value: str) -> None:
        super().__init__(
            f"Unknown section value: {value!r}. "
            f"Must be a member of PROCESS_PIPELINE_SECTIONS at activity.py:282."
        )
        self.value = value


# ---------------------------------------------------------------------------
# identity_complete column (TDD §8 — P1-C-05 source-of-truth)
# ---------------------------------------------------------------------------


def attach_identity_complete(df: "pl.DataFrame") -> "pl.DataFrame":
    """Attach the ``identity_complete`` boolean column.

    Definition (PRD §5.3):
        identity_complete := (office_phone IS NOT NULL) AND (vertical IS NOT NULL)

    This is the SINGLE source-of-truth for the column per P1-C-05 + TDD-AC-5.
    The column is computed at extraction time, NOT inside cascade_resolver or
    cascade_validator. AP-4 / AP-6 guards in the touchstones forbid touching
    those modules.

    If the input frame lacks ``office_phone`` or ``vertical`` columns, the
    helper sets ``identity_complete=False`` for every row (cannot prove
    completeness without the columns) and logs a warning.
    """
    has_phone = "office_phone" in df.columns
    has_vertical = "vertical" in df.columns

    if not has_phone or not has_vertical:
        logger.warning(
            "identity_complete_missing_source_columns",
            extra={
                "has_office_phone": has_phone,
                "has_vertical": has_vertical,
                "available_columns": df.columns,
            },
        )
        return df.with_columns(identity_complete=pl.lit(False))

    return df.with_columns(
        identity_complete=(
            pl.col("office_phone").is_not_null() & pl.col("vertical").is_not_null()
        )
    )


def filter_incomplete_identity(
    df: "pl.DataFrame",
    *,
    include: bool,
) -> "pl.DataFrame":
    """Drop rows with ``identity_complete=false`` when caller opts in.

    Default per PRD §3.1: ``include=True`` → null-key rows surface with the flag
    set false (SCAR-005/006 transparency invariant; AP-6 guard). ``include=False``
    is caller-elective suppression per PRD AC-6.
    """
    if include:
        return df
    if "identity_complete" not in df.columns:
        # Defensive: if attach_identity_complete was skipped upstream, do not
        # silently drop rows — return frame unchanged and log.
        logger.warning(
            "filter_incomplete_identity_called_without_identity_complete_column",
            extra={"available_columns": df.columns},
        )
        return df
    return df.filter(pl.col("identity_complete") == pl.lit(True))


def dedupe_by_key(
    df: "pl.DataFrame",
    *,
    keys: list[str],
) -> "pl.DataFrame":
    """Dedupe by ``keys`` using the most-recent-by-modified_at policy.

    Per TDD §3.4 + DEFER-WATCH-1: when multiple input rows collapse to the same
    dedupe key, the row with the most recent ``modified_at`` wins. If
    ``modified_at`` is unavailable, falls back to ``unique(keep="first")``
    (deterministic on stable input ordering).
    """
    if not keys:
        return df

    # Filter dedupe keys to those actually present (defensive — caller may pass
    # a key that is not in the projected schema; PRD AC-9 / DEFER-WATCH-1).
    available = [k for k in keys if k in df.columns]
    if not available:
        logger.warning(
            "dedupe_by_key_no_matching_columns",
            extra={"requested_keys": keys, "available_columns": df.columns},
        )
        return df

    if "modified_at" in df.columns:
        return df.sort("modified_at", descending=True, nulls_last=True).unique(
            subset=available, keep="first"
        )
    return df.unique(subset=available, keep="first")


# ---------------------------------------------------------------------------
# Section predicate handling (TDD §9 + PRD §4)
# ---------------------------------------------------------------------------


def predicate_references_field(node: PredicateNode | None, field_name: str) -> bool:
    """Return True if any leaf Comparison in ``node`` references ``field_name``."""
    if node is None:
        return False
    if isinstance(node, Comparison):
        return node.field == field_name
    if isinstance(node, AndGroup):
        return any(predicate_references_field(c, field_name) for c in node.and_)
    if isinstance(node, OrGroup):
        return any(predicate_references_field(c, field_name) for c in node.or_)
    if isinstance(node, NotGroup):
        return predicate_references_field(node.not_, field_name)
    return False


def apply_active_default_section_predicate(
    predicate: PredicateNode | None,
) -> tuple[PredicateNode | None, bool]:
    """Inject the ACTIVE-only ``section`` filter when caller omits ``section``.

    Per TDD §9.3 + DEFER-WATCH-3 disposition (RESOLVE-WITH-DEFAULT-FLAGGED-FOR-VINCE):
    the engineering default is ACTIVE-only; ACTIVATING is caller-elective; the
    server NEVER injects ACTIVATING / INACTIVE / IGNORED.

    Returns ``(new_predicate, default_applied)`` so the caller can echo the
    fact in response meta (PRD §4.3 transparency).
    """
    if predicate_references_field(predicate, "section"):
        return predicate, False

    active_filter = Comparison(
        field="section",
        op=Op.IN,
        value=sorted(ACTIVE_SECTIONS),
    )
    if predicate is None:
        return active_filter, True
    return AndGroup(and_=[active_filter, predicate]), True  # type: ignore[arg-type]


def validate_section_values(node: PredicateNode | None) -> None:
    """Raise ``InvalidSectionError`` for any ``section`` value not in vocabulary.

    Per TDD §9.4 + PRD §9.2 ``unknown_section_value`` failure mode. Walks the
    full predicate tree and inspects every Comparison with ``field="section"``.
    """
    if node is None:
        return
    if isinstance(node, Comparison):
        if node.field != "section":
            return
        values: list[Any]
        if node.op in (Op.IN, Op.NOT_IN):
            if not isinstance(node.value, (list, tuple)):
                # Malformed: surface upstream, not an unknown-section error.
                return
            values = list(node.value)
        else:
            values = [node.value]
        for v in values:
            if not isinstance(v, str) or v not in VALID_SECTIONS:
                raise InvalidSectionError(str(v))
        return
    if isinstance(node, AndGroup):
        for child in node.and_:
            validate_section_values(child)
        return
    if isinstance(node, OrGroup):
        for child in node.or_:
            validate_section_values(child)
        return
    if isinstance(node, NotGroup):
        validate_section_values(node.not_)


# ---------------------------------------------------------------------------
# ESC-1 resolution: Date operator translation (TDD §5.3 + §15.1)
# ---------------------------------------------------------------------------


class DateTranslationResult:
    """Outcome of pre-engine date-op translation.

    Attributes:
        cleaned_predicate: The PredicateNode with all date-op Comparisons
            stripped — passes through to ``PredicateCompiler`` cleanly.
        date_filter_expr: The combined Polars expression representing every
            date Comparison that was extracted, AND-merged. ``None`` if no date
            ops were present.
    """

    __slots__ = ("cleaned_predicate", "date_filter_expr")

    def __init__(
        self,
        cleaned_predicate: PredicateNode | None,
        date_filter_expr: "pl.Expr | None",
    ) -> None:
        self.cleaned_predicate = cleaned_predicate
        self.date_filter_expr = date_filter_expr


def _is_date_op(op: Op) -> bool:
    return op in (Op.BETWEEN, Op.DATE_GTE, Op.DATE_LTE)


def _coerce_date_value(value: Any) -> _date:
    """Coerce a date scalar (ISO string, relative, date, datetime) to ``date``.

    Per TDD §5.3: date string parsing reuses ``temporal.parse_date_or_relative``.
    """
    if isinstance(value, _date) and not isinstance(value, _datetime):
        return value
    if isinstance(value, _datetime):
        return value.date()
    if isinstance(value, str):
        return parse_date_or_relative(value)
    raise ValueError(
        f"Date predicate value must be ISO date string, relative duration, "
        f"date, or datetime; got {type(value).__name__}: {value!r}"
    )


def _build_date_expr(comparison: Comparison) -> "pl.Expr":
    """Translate a single date-op Comparison into a Polars filter expression.

    BETWEEN: value is ``[lo, hi]`` (inclusive both bounds).
    DATE_GTE: value is a single date string (``>=``).
    DATE_LTE: value is a single date string (``<=``).
    """
    col_expr = pl.col(comparison.field)
    if comparison.op == Op.BETWEEN:
        if not isinstance(comparison.value, (list, tuple)) or len(comparison.value) != 2:
            raise ValueError(
                f"BETWEEN requires a [low, high] list of length 2; "
                f"got {comparison.value!r}"
            )
        lo = _coerce_date_value(comparison.value[0])
        hi = _coerce_date_value(comparison.value[1])
        return col_expr.is_between(pl.lit(lo), pl.lit(hi), closed="both")
    if comparison.op == Op.DATE_GTE:
        return col_expr >= pl.lit(_coerce_date_value(comparison.value))
    if comparison.op == Op.DATE_LTE:
        return col_expr <= pl.lit(_coerce_date_value(comparison.value))
    raise ValueError(f"Not a date operator: {comparison.op!r}")


def _split_date_predicates(
    node: PredicateNode | None,
) -> tuple[PredicateNode | None, list["pl.Expr"]]:
    """Walk ``node``, extract date-op Comparisons, return (cleaned, exprs).

    Per TDD §5.3 ESC-1 resolution: the route handler translates date operators
    BEFORE the engine call so the engine compile path
    (``compiler.py:53-63,192-241``) is untouched (P1-C-04). Only AND-grouped or
    free-standing date Comparisons are extracted; date Comparisons buried under
    OR / NOT semantics raise ``ValueError`` because their semantics cannot be
    AND-merged into a separate expression without altering boolean semantics.
    """
    if node is None:
        return None, []

    if isinstance(node, Comparison):
        if _is_date_op(node.op):
            return None, [_build_date_expr(node)]
        return node, []

    if isinstance(node, AndGroup):
        survivors: list[PredicateNode] = []
        exprs: list["pl.Expr"] = []
        for child in node.and_:
            child_clean, child_exprs = _split_date_predicates(child)
            exprs.extend(child_exprs)
            if child_clean is not None:
                survivors.append(child_clean)
        if not survivors:
            return None, exprs
        if len(survivors) == 1:
            return survivors[0], exprs
        return AndGroup(and_=survivors), exprs  # type: ignore[arg-type]

    if isinstance(node, OrGroup):
        # OR / NOT semantics: refuse to split — boolean structure is load-bearing.
        for child in node.or_:
            if _contains_date_op(child):
                raise ValueError(
                    "Date operators (BETWEEN, DATE_GTE, DATE_LTE) under an OR "
                    "group are not supported in Phase 1. ESC-1 (TDD §15.1) "
                    "translates date predicates as AND-merged filter expressions "
                    "only. Restructure the predicate or use the standard GTE/LTE "
                    "operators with explicit date string handling."
                )
        return node, []

    if isinstance(node, NotGroup):
        if _contains_date_op(node.not_):
            raise ValueError(
                "Date operators (BETWEEN, DATE_GTE, DATE_LTE) under a NOT group "
                "are not supported in Phase 1 (ESC-1)."
            )
        return node, []

    return node, []


def _contains_date_op(node: PredicateNode | None) -> bool:
    if node is None:
        return False
    if isinstance(node, Comparison):
        return _is_date_op(node.op)
    if isinstance(node, AndGroup):
        return any(_contains_date_op(c) for c in node.and_)
    if isinstance(node, OrGroup):
        return any(_contains_date_op(c) for c in node.or_)
    if isinstance(node, NotGroup):
        return _contains_date_op(node.not_)
    return False


def translate_date_predicates(
    predicate: PredicateNode | None,
) -> DateTranslationResult:
    """ESC-1 resolution entry point: split date predicates from AST.

    Per TDD §5.3 + §15.1: extracts BETWEEN / DATE_GTE / DATE_LTE Comparisons
    from the predicate tree, returning a ``(cleaned_predicate, date_filter_expr)``
    pair. The cleaned predicate flows through ``PredicateCompiler`` unchanged;
    the date filter expression is composed AFTER the engine call by the
    ``/exports`` handler. This preserves P1-C-04 (zero modifications to
    ``compiler.py:53-63`` or ``compiler.py:192-241``).
    """
    cleaned, exprs = _split_date_predicates(predicate)
    if not exprs:
        return DateTranslationResult(cleaned_predicate=cleaned, date_filter_expr=None)
    combined: pl.Expr = exprs[0]
    for extra in exprs[1:]:
        combined = combined & extra
    return DateTranslationResult(cleaned_predicate=cleaned, date_filter_expr=combined)
