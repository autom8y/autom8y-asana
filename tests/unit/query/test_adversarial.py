"""Adversarial tests for the query module.

These tests deliberately probe edge cases, boundary conditions, type coercion
failures, operator violations, depth attacks, null handling, and malformed
payloads to verify the implementation fails safely and predictably.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from pydantic import TypeAdapter, ValidationError

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.query.compiler import (
    PredicateCompiler,
    _coerce_scalar,
    _coerce_value,
    strip_section_predicates,
)
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import (
    CoercionError,
    InvalidOperatorError,
    QueryEngineError,
    QueryTooComplexError,
    UnknownFieldError,
    UnknownSectionError,
)
from autom8_asana.query.guards import QueryLimits, predicate_depth
from autom8_asana.query.models import (
    AndGroup,
    Comparison,
    NotGroup,
    Op,
    OrGroup,
    PredicateNode,
    RowsRequest,
)
from autom8_asana.services.query_service import EntityQueryService

_adapter = TypeAdapter(PredicateNode)
_leaf = {"field": "name", "op": "eq", "value": "x"}


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def full_schema() -> DataFrameSchema:
    """Schema with one column per dtype for comprehensive testing."""
    return DataFrameSchema(
        name="test",
        task_type="Test",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("section", "Utf8", nullable=True),
            ColumnDef("age", "Int64", nullable=True),
            ColumnDef("rank", "Int32", nullable=True),
            ColumnDef("score", "Float64", nullable=True),
            ColumnDef("amount", "Decimal", nullable=True),
            ColumnDef("is_active", "Boolean", nullable=False),
            ColumnDef("created_date", "Date", nullable=True),
            ColumnDef("created_at", "Datetime", nullable=True),
            ColumnDef("tags", "List[Utf8]", nullable=True),
        ],
    )


@pytest.fixture
def compiler() -> PredicateCompiler:
    return PredicateCompiler()


# ---------------------------------------------------------------------------
# 1. Type coercion edge cases
# ---------------------------------------------------------------------------


class TestCoercionEdgeCases:
    """Adversarial coercion inputs that should fail with COERCION_FAILED."""

    def test_not_a_number_to_float64(self) -> None:
        with pytest.raises(CoercionError) as exc:
            _coerce_scalar("not_a_number", "Float64", "score")
        assert exc.value.field == "score"
        assert exc.value.dtype == "Float64"

    def test_not_a_number_to_int64(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("not_a_number", "Int64", "age")

    def test_invalid_date_month_13(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("2024-13-45", "Date", "created_date")

    def test_invalid_date_day_45(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("2024-01-45", "Date", "created_date")

    def test_empty_string_to_int64(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("", "Int64", "age")

    def test_empty_string_to_int32(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("", "Int32", "rank")

    def test_empty_string_to_float64(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("", "Float64", "score")

    def test_none_to_int64(self) -> None:
        """None should fail coercion for scalar comparison."""
        with pytest.raises(CoercionError):
            _coerce_scalar(None, "Int64", "age")

    def test_none_to_float64(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar(None, "Float64", "score")

    def test_none_to_date(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar(None, "Date", "created_date")

    def test_none_to_boolean(self) -> None:
        """None is not a bool; coercion should fail."""
        with pytest.raises(CoercionError):
            _coerce_scalar(None, "Boolean", "is_active")

    def test_none_to_utf8(self) -> None:
        """None coerces to 'None' via str(). Documents this behavior."""
        result = _coerce_scalar(None, "Utf8", "name")
        assert result == "None"

    def test_none_to_datetime(self) -> None:
        """None is not a string; Datetime coercion should fail."""
        with pytest.raises(CoercionError):
            _coerce_scalar(None, "Datetime", "created_at")

    def test_nan_string_to_float64_succeeds(self) -> None:
        """Python float('nan') is valid -- verify it coerces."""
        result = _coerce_scalar("nan", "Float64", "score")
        assert math.isnan(result)

    def test_infinity_string_to_float64_succeeds(self) -> None:
        """float('inf') is valid Python -- verify coercion."""
        result = _coerce_scalar("inf", "Float64", "score")
        assert math.isinf(result)

    def test_negative_infinity_to_float64(self) -> None:
        result = _coerce_scalar("-inf", "Float64", "score")
        assert math.isinf(result) and result < 0

    def test_very_large_int_to_int32(self) -> None:
        """Python int() does not overflow, but Polars Int32 will.

        The coercion itself succeeds (Python int has no limit), but
        downstream Polars filtering may fail silently or error.
        This documents the boundary.
        """
        # 2^31 exceeds Int32 range
        result = _coerce_scalar(2**31, "Int32", "rank")
        assert result == 2**31  # Coercion succeeds; Polars may truncate

    def test_very_large_int_to_int64(self) -> None:
        """2^63 exceeds Int64 range. Python int() succeeds."""
        result = _coerce_scalar(2**63, "Int64", "age")
        assert result == 2**63  # Coercion succeeds; Polars overflow

    def test_float_to_int64_truncates(self) -> None:
        """float 3.7 -> int(3.7) = 3, lossy but allowed by Python int()."""
        result = _coerce_scalar(3.7, "Int64", "age")
        assert result == 3

    def test_boolean_true_to_int64(self) -> None:
        """bool is a subclass of int in Python: int(True) = 1."""
        result = _coerce_scalar(True, "Int64", "age")
        assert result == 1

    def test_string_true_to_boolean_rejected(self) -> None:
        """String 'true' is not a bool; must be actual boolean."""
        with pytest.raises(CoercionError):
            _coerce_scalar("true", "Boolean", "is_active")

    def test_string_false_to_boolean_rejected(self) -> None:
        """String 'false' is not a bool; must be actual boolean."""
        with pytest.raises(CoercionError):
            _coerce_scalar("false", "Boolean", "is_active")

    def test_int_1_to_boolean_rejected(self) -> None:
        """int(1) is not a bool literal; rejected."""
        with pytest.raises(CoercionError):
            _coerce_scalar(1, "Boolean", "is_active")

    def test_int_0_to_boolean_rejected(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar(0, "Boolean", "is_active")

    def test_unsupported_dtype_raises(self) -> None:
        """Unknown dtype string should raise CoercionError."""
        with pytest.raises(CoercionError) as exc:
            _coerce_scalar("x", "Unknown", "field")
        assert "unsupported dtype" in exc.value.reason

    def test_empty_string_to_date(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("", "Date", "created_date")

    def test_partial_iso_date(self) -> None:
        """'2024-01' is not a full ISO date."""
        with pytest.raises(CoercionError):
            _coerce_scalar("2024-01", "Date", "created_date")

    def test_malformed_date_feb_30(self) -> None:
        """Feb 30 does not exist."""
        with pytest.raises(CoercionError):
            _coerce_scalar("2026-02-30", "Date", "created_date")

    def test_malformed_datetime_hour_25(self) -> None:
        """Hour 25 is invalid."""
        with pytest.raises(CoercionError):
            _coerce_scalar("2026-02-03T25:00:00Z", "Datetime", "created_at")

    def test_datetime_missing_timezone(self) -> None:
        """Datetime without timezone -- fromisoformat accepts this in Python 3.11+."""
        # This should succeed (Python 3.11+ accepts naive datetimes)
        result = _coerce_scalar("2026-02-03T10:00:00", "Datetime", "created_at")
        assert isinstance(result, datetime)

    def test_datetime_with_bad_timezone(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("2024-01-15T10:30:00+99:99", "Datetime", "created_at")

    def test_date_not_a_date_string(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("not-a-date", "Date", "created_date")

    def test_datetime_not_a_datetime_string(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("not-a-datetime", "Datetime", "created_at")

    def test_unicode_to_utf8_coerces(self) -> None:
        """Unicode strings should coerce to Utf8 fine."""
        result = _coerce_scalar("\u00e9\u00e0\u00fc\u2603\U0001f600", "Utf8", "name")
        assert result == "\u00e9\u00e0\u00fc\u2603\U0001f600"

    def test_emoji_in_utf8_field(self) -> None:
        result = _coerce_scalar("\U0001f4a9", "Utf8", "name")
        assert result == "\U0001f4a9"

    def test_sql_injection_string_to_utf8(self) -> None:
        """SQL injection attempt just becomes a string literal."""
        result = _coerce_scalar("' OR '1'='1", "Utf8", "name")
        assert result == "' OR '1'='1"

    def test_xss_string_to_utf8(self) -> None:
        result = _coerce_scalar("<script>alert('xss')</script>", "Utf8", "name")
        assert result == "<script>alert('xss')</script>"

    def test_path_traversal_to_utf8(self) -> None:
        result = _coerce_scalar("../../../etc/passwd", "Utf8", "name")
        assert result == "../../../etc/passwd"

    def test_null_byte_to_utf8(self) -> None:
        result = _coerce_scalar("abc\x00def", "Utf8", "name")
        assert result == "abc\x00def"

    def test_nosql_injection_dict_to_int(self) -> None:
        """dict value should fail int coercion."""
        with pytest.raises(CoercionError):
            _coerce_scalar({"$gt": ""}, "Int64", "age")

    def test_nested_dict_as_value_to_utf8(self) -> None:
        """Nested object coerces to string repr for Utf8."""
        result = _coerce_scalar({"nested": True}, "Utf8", "name")
        assert isinstance(result, str)  # str({"nested": True})

    def test_nested_dict_as_value_to_int(self) -> None:
        """Nested object cannot coerce to int."""
        with pytest.raises(CoercionError):
            _coerce_scalar({"nested": True}, "Int64", "age")

    def test_list_as_value_to_int(self) -> None:
        """List cannot coerce to int for non-in ops."""
        with pytest.raises(CoercionError):
            _coerce_scalar([1, 2, 3], "Int64", "age")

    def test_coercion_error_to_dict_format(self) -> None:
        """Verify CoercionError.to_dict() output has all PRD-required keys."""
        err = CoercionError(field="age", dtype="Int64", value="abc", reason="bad")
        d = err.to_dict()
        assert d["error"] == "COERCION_FAILED"
        assert d["field"] == "age"
        assert d["field_dtype"] == "Int64"
        assert d["value"] == "abc"
        assert "Cannot coerce" in d["message"]


class TestCoercionInNotIn:
    """Edge cases for in/not_in list coercion."""

    def test_in_with_non_list_value(self) -> None:
        with pytest.raises(CoercionError) as exc:
            _coerce_value("scalar", "Int64", "age", Op.IN)
        assert "list" in exc.value.reason

    def test_not_in_with_non_list_value(self) -> None:
        with pytest.raises(CoercionError) as exc:
            _coerce_value(42, "Int64", "age", Op.NOT_IN)
        assert "list" in exc.value.reason

    def test_in_with_none_elements_stripped(self) -> None:
        """None elements in in/not_in lists are silently stripped."""
        result = _coerce_value([1, None, 3], "Int64", "age", Op.IN)
        assert result == [1, 3]

    def test_in_with_all_none_elements(self) -> None:
        """All-None list results in empty list."""
        result = _coerce_value([None, None], "Int64", "age", Op.IN)
        assert result == []

    def test_in_with_empty_list(self) -> None:
        result = _coerce_value([], "Int64", "age", Op.IN)
        assert result == []

    def test_in_with_bad_element(self) -> None:
        """One bad element in the list should fail entire coercion."""
        with pytest.raises(CoercionError):
            _coerce_value([1, "abc", 3], "Int64", "age", Op.IN)

    def test_in_with_mixed_types_for_utf8(self) -> None:
        """Mixed types coerce to string for Utf8."""
        result = _coerce_value([1, "hello", True], "Utf8", "name", Op.IN)
        assert result == ["1", "hello", "True"]

    def test_not_in_with_empty_list(self) -> None:
        """Empty list for not_in should return empty list."""
        result = _coerce_value([], "Utf8", "name", Op.NOT_IN)
        assert result == []


# ---------------------------------------------------------------------------
# 2. Operator x type violations -- exhaustive invalid cells
# ---------------------------------------------------------------------------


class TestOperatorTypeViolations:
    """Verify operator/dtype incompatibilities raise INVALID_OPERATOR."""

    def test_gt_on_boolean(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="is_active", op=Op.GT, value=True)
        with pytest.raises(InvalidOperatorError) as exc:
            compiler.compile(node, full_schema)
        assert exc.value.op == "gt"
        assert exc.value.dtype == "Boolean"

    def test_lt_on_boolean(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="is_active", op=Op.LT, value=False)
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_gte_on_boolean(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="is_active", op=Op.GTE, value=True)
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_lte_on_boolean(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="is_active", op=Op.LTE, value=True)
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_contains_on_boolean(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="is_active", op=Op.CONTAINS, value="true")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_starts_with_on_boolean(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="is_active", op=Op.STARTS_WITH, value="t")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_contains_on_float64(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="score", op=Op.CONTAINS, value="3.14")
        with pytest.raises(InvalidOperatorError) as exc:
            compiler.compile(node, full_schema)
        assert exc.value.dtype == "Float64"

    def test_starts_with_on_float64(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="score", op=Op.STARTS_WITH, value="3")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_starts_with_on_int64(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="age", op=Op.STARTS_WITH, value="3")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_contains_on_int64(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="age", op=Op.CONTAINS, value="3")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_contains_on_int32(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="rank", op=Op.CONTAINS, value="1")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_starts_with_on_int32(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="rank", op=Op.STARTS_WITH, value="1")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_contains_on_date(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="created_date", op=Op.CONTAINS, value="2024")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_starts_with_on_date(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="created_date", op=Op.STARTS_WITH, value="2024")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_starts_with_on_datetime(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="created_at", op=Op.STARTS_WITH, value="2024")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_contains_on_datetime(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="created_at", op=Op.CONTAINS, value="2024")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_contains_on_decimal(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="amount", op=Op.CONTAINS, value="100")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_starts_with_on_decimal(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="amount", op=Op.STARTS_WITH, value="1")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, full_schema)

    def test_any_operator_on_list_utf8(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """Every single operator should be rejected for List[Utf8]."""
        for op in Op:
            node = Comparison(field="tags", op=op, value="test")
            with pytest.raises(InvalidOperatorError):
                compiler.compile(node, full_schema)

    def test_invalid_operator_error_dict_has_supported_operators(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """Verify error serialization includes correct supported_operators list."""
        node = Comparison(field="is_active", op=Op.GT, value=True)
        with pytest.raises(InvalidOperatorError) as exc:
            compiler.compile(node, full_schema)
        d = exc.value.to_dict()
        assert d["error"] == "INVALID_OPERATOR"
        assert d["field"] == "is_active"
        assert d["field_dtype"] == "Boolean"
        assert d["operator"] == "gt"
        assert isinstance(d["supported_operators"], list)
        # Boolean supports eq, ne, in, not_in
        assert "eq" in d["supported_operators"]
        assert "ne" in d["supported_operators"]
        assert "in" in d["supported_operators"]
        assert "not_in" in d["supported_operators"]
        # Should NOT include orderable or string ops
        assert "gt" not in d["supported_operators"]
        assert "contains" not in d["supported_operators"]


# ---------------------------------------------------------------------------
# 3. Predicate depth attacks
# ---------------------------------------------------------------------------


def _build_deep_not_chain(depth: int) -> dict:
    """Build NOT(NOT(NOT(...(leaf)...))) at given depth."""
    node = _leaf
    for _ in range(depth - 1):
        node = {"not": node}
    return node


def _build_deep_and_chain(depth: int) -> dict:
    """Build AND(AND(AND(...(leaf)...))) at given depth."""
    node = _leaf
    for _ in range(depth - 1):
        node = {"and": [node]}
    return node


class TestDepthAttacks:
    """Attempt to bypass depth limits."""

    def test_depth_5_passes(self) -> None:
        """Exactly at limit -- should succeed."""
        node = _adapter.validate_python(_build_deep_and_chain(5))
        assert predicate_depth(node) == 5
        limits = QueryLimits()
        limits.check_depth(predicate_depth(node))  # no raise

    def test_depth_6_rejected(self) -> None:
        node = _adapter.validate_python(_build_deep_and_chain(6))
        assert predicate_depth(node) == 6
        limits = QueryLimits()
        with pytest.raises(QueryTooComplexError):
            limits.check_depth(predicate_depth(node))

    def test_deeply_nested_not_chain_5(self) -> None:
        """NOT(NOT(NOT(NOT(leaf)))) = depth 5, at limit."""
        node = _adapter.validate_python(_build_deep_not_chain(5))
        assert predicate_depth(node) == 5

    def test_deeply_nested_not_chain_6(self) -> None:
        """NOT chain exceeding limit."""
        node = _adapter.validate_python(_build_deep_not_chain(6))
        assert predicate_depth(node) == 6
        limits = QueryLimits()
        with pytest.raises(QueryTooComplexError):
            limits.check_depth(predicate_depth(node))

    def test_wide_tree_depth_2(self) -> None:
        """100 siblings at depth 2 -- wide but shallow, should pass."""
        children = [_leaf] * 100
        node = _adapter.validate_python({"and": children})
        assert predicate_depth(node) == 2  # depth is about nesting, not width
        limits = QueryLimits()
        limits.check_depth(predicate_depth(node))  # no raise

    def test_mixed_depth_tree(self) -> None:
        """Tree where one branch is deep and others are shallow."""
        deep_branch = _build_deep_and_chain(5)
        shallow_branch = _leaf
        node = _adapter.validate_python({"or": [deep_branch, shallow_branch]})
        # or -> deep_branch(5) => 1 + 5 = 6
        assert predicate_depth(node) == 6
        limits = QueryLimits()
        with pytest.raises(QueryTooComplexError):
            limits.check_depth(predicate_depth(node))

    def test_depth_10_rejected(self) -> None:
        """Extreme nesting."""
        node = _adapter.validate_python(_build_deep_and_chain(10))
        assert predicate_depth(node) == 10
        limits = QueryLimits()
        with pytest.raises(QueryTooComplexError):
            limits.check_depth(predicate_depth(node))

    def test_query_too_complex_to_dict(self) -> None:
        """Verify to_dict() serialization for QueryTooComplexError."""
        err = QueryTooComplexError(depth=7, max_depth=5)
        d = err.to_dict()
        assert d["error"] == "QUERY_TOO_COMPLEX"
        assert d["max_depth"] == 5
        assert "7" in d["message"]
        assert "5" in d["message"]


# ---------------------------------------------------------------------------
# 4. MAX_RESULT_ROWS enforcement
# ---------------------------------------------------------------------------


class TestMaxResultRows:
    """Verify row limit clamping."""

    def test_clamp_50000_to_10000(self) -> None:
        limits = QueryLimits()
        assert limits.clamp_limit(50_000) == 10_000

    def test_clamp_1_stays_1(self) -> None:
        limits = QueryLimits()
        assert limits.clamp_limit(1) == 1

    def test_clamp_negative_stays_negative(self) -> None:
        """clamp_limit does min(requested, max) -- negative passes through.

        This is fine because Pydantic ge=1 on RowsRequest.limit rejects it
        before it reaches the engine.
        """
        limits = QueryLimits()
        assert limits.clamp_limit(-1) == -1

    def test_clamp_zero(self) -> None:
        """Zero passes through clamp (Pydantic rejects before engine)."""
        limits = QueryLimits()
        assert limits.clamp_limit(0) == 0

    def test_pydantic_rejects_limit_zero(self) -> None:
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"limit": 0})

    def test_pydantic_rejects_limit_negative(self) -> None:
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"limit": -1})

    def test_pydantic_rejects_limit_above_1000(self) -> None:
        """RowsRequest caps at 1000 at the API layer."""
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"limit": 1001})

    def test_pydantic_allows_limit_1000(self) -> None:
        req = RowsRequest.model_validate({"limit": 1000})
        assert req.limit == 1000


# ---------------------------------------------------------------------------
# 5. Empty DataFrame handling
# ---------------------------------------------------------------------------


class TestEmptyDataFrame:
    """Query against empty or fully-filtered DataFrames."""

    @pytest.fixture
    def empty_df(self) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "gid": pl.Series([], dtype=pl.Utf8),
                "name": pl.Series([], dtype=pl.Utf8),
                "section": pl.Series([], dtype=pl.Utf8),
            }
        )

    @pytest.fixture
    def empty_engine(self, empty_df: pl.DataFrame) -> QueryEngine:
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=empty_df)  # type: ignore[method-assign]
        return QueryEngine(query_service=service)

    @pytest.fixture
    def empty_schema(self) -> DataFrameSchema:
        return DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
            ],
        )

    @pytest.mark.asyncio
    async def test_query_empty_df_no_filter(
        self, empty_engine: QueryEngine, empty_schema: DataFrameSchema
    ) -> None:
        request = RowsRequest.model_validate({})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = empty_schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await empty_engine.execute_rows(
                entity_type="test",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
            )
        assert result.meta.total_count == 0
        assert result.meta.returned_count == 0
        assert result.data == []

    @pytest.mark.asyncio
    async def test_query_all_filtered_out(self, empty_schema: DataFrameSchema) -> None:
        """DataFrame with data but filter matches nothing."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2"],
                "name": ["Alpha", "Beta"],
                "section": ["A", "B"],
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(query_service=service)

        request = RowsRequest.model_validate(
            {"where": {"field": "name", "op": "eq", "value": "Nonexistent"}}
        )
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = empty_schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await engine.execute_rows(
                entity_type="test",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
            )
        assert result.meta.total_count == 0
        assert result.data == []


# ---------------------------------------------------------------------------
# 6. Section scoping edge cases
# ---------------------------------------------------------------------------


class TestSectionEdgeCases:
    """Adversarial section parameter inputs."""

    @pytest.fixture
    def section_schema(self) -> DataFrameSchema:
        return DataFrameSchema(
            name="offer",
            task_type="Offer",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
            ],
        )

    @pytest.fixture
    def section_df(self) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", "B", "C"],
                "section": ["Active", "Won", "Active"],
            }
        )

    @pytest.fixture
    def section_engine(self, section_df: pl.DataFrame) -> QueryEngine:
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=section_df)  # type: ignore[method-assign]
        return QueryEngine(query_service=service)

    @pytest.mark.asyncio
    async def test_nonexistent_section(
        self, section_engine: QueryEngine, section_schema: DataFrameSchema
    ) -> None:
        """Unknown section name raises UnknownSectionError."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-1"})
        request = RowsRequest.model_validate({"section": "Nonexistent"})
        with pytest.raises(UnknownSectionError) as exc:
            await section_engine.execute_rows(
                entity_type="offer",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
                section_index=section_index,
            )
        assert exc.value.section == "Nonexistent"

    @pytest.mark.asyncio
    async def test_empty_string_section(
        self, section_engine: QueryEngine, section_schema: DataFrameSchema
    ) -> None:
        """Empty string section should be rejected (not in index)."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-1"})
        request = RowsRequest.model_validate({"section": ""})
        with pytest.raises(UnknownSectionError):
            await section_engine.execute_rows(
                entity_type="offer",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
                section_index=section_index,
            )

    def test_section_index_case_insensitive(self) -> None:
        """SectionIndex.resolve is case-insensitive."""
        from autom8_asana.metrics.resolve import SectionIndex

        idx = SectionIndex(_name_to_gid={"active": "gid-1"})
        assert idx.resolve("Active") == "gid-1"
        assert idx.resolve("ACTIVE") == "gid-1"
        assert idx.resolve("active") == "gid-1"

    def test_section_error_serialization(self) -> None:
        err = UnknownSectionError(section="Bogus")
        d = err.to_dict()
        assert d["error"] == "UNKNOWN_SECTION"
        assert d["section"] == "Bogus"

    @pytest.mark.asyncio
    async def test_section_param_and_section_predicate_simultaneously(
        self, section_schema: DataFrameSchema
    ) -> None:
        """EC-006: Section param + section field in predicate.

        The engine should accept the section param and the caller (route handler)
        is responsible for stripping conflicting predicates. Here we test
        that if the predicate still contains a section comparison alongside
        the section_name_filter, the section param wins for filtering.
        """
        from autom8_asana.metrics.resolve import SectionIndex

        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", "B", "C"],
                "section": ["Active", "Won", "Active"],
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(query_service=service)

        # Request with section param AND a name predicate (section stripped already)
        section_index = SectionIndex(_name_to_gid={"active": "gid-1"})
        request = RowsRequest.model_validate(
            {
                "section": "Active",
                "where": {"field": "name", "op": "eq", "value": "A"},
            }
        )
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = section_schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
                section_index=section_index,
            )
        # Only row 1 matches (Active AND name=A)
        assert result.meta.total_count == 1
        assert result.data[0]["name"] == "A"
        assert result.data[0]["section"] == "Active"

    @pytest.mark.asyncio
    async def test_section_case_sensitive_filter(
        self, section_schema: DataFrameSchema
    ) -> None:
        """Section name filter on DataFrame is case-sensitive (per ADR-DQS-003)."""
        from autom8_asana.metrics.resolve import SectionIndex

        df = pl.DataFrame(
            {
                "gid": ["1", "2"],
                "name": ["A", "B"],
                "section": ["Active", "active"],
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(query_service=service)

        # SectionIndex resolves case-insensitively, but DataFrame filter is exact
        section_index = SectionIndex(_name_to_gid={"active": "gid-1"})
        request = RowsRequest.model_validate({"section": "Active"})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = section_schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
                section_index=section_index,
            )
        # Only "Active" matches, not "active"
        assert result.meta.total_count == 1
        assert result.data[0]["section"] == "Active"


# ---------------------------------------------------------------------------
# 7. Null values in filter columns
# ---------------------------------------------------------------------------


class TestNullPropagation:
    """Verify behavior when DataFrame columns contain null values."""

    def test_eq_with_nulls_excludes_nulls(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """Polars eq comparison: null != 'Acme', so null rows are excluded."""
        node = Comparison(field="name", op=Op.EQ, value="Acme")
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"name": ["Acme", None, "Beta"]})
        result = df.filter(expr)
        assert result["name"].to_list() == ["Acme"]

    def test_ne_with_nulls_excludes_nulls(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """Polars ne: null != 'Acme' is null (falsy), not True."""
        node = Comparison(field="name", op=Op.NE, value="Acme")
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"name": ["Acme", None, "Beta"]})
        result = df.filter(expr)
        # null rows are excluded (null is not True)
        assert result["name"].to_list() == ["Beta"]

    def test_gt_with_nulls_excludes_nulls(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="age", op=Op.GT, value=20)
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"age": [10, None, 30]})
        result = df.filter(expr)
        assert result["age"].to_list() == [30]

    def test_in_with_nulls(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.IN, value=["Acme", "Beta"])
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"name": ["Acme", None, "Beta", None]})
        result = df.filter(expr)
        assert len(result) == 2

    def test_not_with_nulls(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """NOT(eq) with nulls: NOT(null) is null, so null rows excluded."""
        node = NotGroup.model_validate(
            {"not": {"field": "name", "op": "eq", "value": "Acme"}}
        )
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"name": ["Acme", None, "Beta"]})
        result = df.filter(expr)
        # NOT(True)=False, NOT(null)=null(excluded), NOT(False)=True
        assert result["name"].to_list() == ["Beta"]

    def test_or_with_one_null_column(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """OR(name_match, age_match) where age has nulls."""
        node = _adapter.validate_python(
            {
                "or": [
                    {"field": "name", "op": "eq", "value": "Acme"},
                    {"field": "age", "op": "gt", "value": 25},
                ]
            }
        )
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame(
            {
                "name": ["Acme", "Beta", "Gamma"],
                "age": [None, 30, None],
            }
        )
        result = df.filter(expr)
        # Acme matches name (age null irrelevant), Beta matches age
        assert len(result) == 2

    def test_contains_with_nulls(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.CONTAINS, value="cm")
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"name": ["Acme", None, "Beta"]})
        result = df.filter(expr)
        assert result["name"].to_list() == ["Acme"]


# ---------------------------------------------------------------------------
# 8. Field validation
# ---------------------------------------------------------------------------


class TestFieldValidation:
    """Unknown field references."""

    def test_unknown_field_in_where(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="nonexistent_field", op=Op.EQ, value="x")
        with pytest.raises(UnknownFieldError) as exc:
            compiler.compile(node, full_schema)
        assert exc.value.field == "nonexistent_field"
        assert "gid" in exc.value.available

    def test_unknown_field_error_serialization(self) -> None:
        err = UnknownFieldError(field="bogus", available=["gid", "name"])
        d = err.to_dict()
        assert d["error"] == "UNKNOWN_FIELD"
        assert "available_fields" in d
        assert d["available_fields"] == ["gid", "name"]  # sorted

    def test_empty_select_uses_defaults(self) -> None:
        """select=None means default columns are used."""
        req = RowsRequest.model_validate({"select": None})
        assert req.select is None

    @pytest.mark.asyncio
    async def test_unknown_field_in_select(self) -> None:
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
            ],
        )
        df = pl.DataFrame({"gid": ["1"], "name": ["A"], "section": ["S"]})
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(query_service=service)

        request = RowsRequest.model_validate({"select": ["name", "bogus"]})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = schema
            mock_reg_cls.get_instance.return_value = mock_reg

            with pytest.raises(UnknownFieldError) as exc:
                await engine.execute_rows(
                    entity_type="test",
                    project_gid="proj-1",
                    client=AsyncMock(),
                    request=request,
                )
            assert exc.value.field == "bogus"

    @pytest.mark.asyncio
    async def test_select_gid_only_no_duplication(self) -> None:
        """select: ['gid'] should not produce gid twice in output."""
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
            ],
        )
        df = pl.DataFrame({"gid": ["1"], "name": ["A"], "section": ["S"]})
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(query_service=service)

        request = RowsRequest.model_validate({"select": ["gid"]})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await engine.execute_rows(
                entity_type="test",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
            )
        # gid should appear exactly once
        assert list(result.data[0].keys()).count("gid") == 1

    @pytest.mark.asyncio
    async def test_predicate_field_in_schema_but_not_in_dataframe(self) -> None:
        """Column exists in schema but not in the actual DataFrame.

        This can happen if schema and data are out of sync. The expression
        will compile (schema says field exists), but Polars will raise
        during filter when the column is not in the DataFrame.
        """
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
                ColumnDef("phantom", "Utf8", nullable=True),
            ],
        )
        df = pl.DataFrame({"gid": ["1"], "name": ["A"], "section": ["S"]})
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(query_service=service)

        request = RowsRequest.model_validate(
            {"where": {"field": "phantom", "op": "eq", "value": "ghost"}}
        )
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = schema
            mock_reg_cls.get_instance.return_value = mock_reg

            # Polars raises ColumnNotFoundError when filtering by missing column
            with pytest.raises(Exception):
                await engine.execute_rows(
                    entity_type="test",
                    project_gid="proj-1",
                    client=AsyncMock(),
                    request=request,
                )


# ---------------------------------------------------------------------------
# 9. Flat-array sugar edge cases
# ---------------------------------------------------------------------------


class TestFlatArraySugar:
    """Test the where: [...] -> AND group sugar."""

    def test_empty_array_becomes_none(self) -> None:
        req = RowsRequest.model_validate({"where": []})
        assert req.where is None

    def test_single_element_array(self) -> None:
        req = RowsRequest.model_validate(
            {"where": [{"field": "name", "op": "eq", "value": "x"}]}
        )
        assert isinstance(req.where, AndGroup)
        assert len(req.where.and_) == 1

    def test_nested_arrays_rejected(self) -> None:
        """Nested arrays should fail Pydantic validation."""
        with pytest.raises(ValidationError):
            RowsRequest.model_validate(
                {"where": [[{"field": "name", "op": "eq", "value": "x"}]]}
            )

    def test_array_of_non_predicates_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"where": ["not", "a", "predicate"]})

    def test_array_with_mixed_valid_predicates(self) -> None:
        req = RowsRequest.model_validate(
            {
                "where": [
                    {"field": "name", "op": "eq", "value": "x"},
                    {
                        "or": [
                            {"field": "age", "op": "gt", "value": 10},
                            {"field": "age", "op": "lt", "value": 5},
                        ]
                    },
                ]
            }
        )
        assert isinstance(req.where, AndGroup)
        assert len(req.where.and_) == 2
        assert isinstance(req.where.and_[1], OrGroup)

    def test_array_with_mixed_valid_and_invalid(self) -> None:
        """Array containing both valid predicates and invalid objects."""
        with pytest.raises(ValidationError):
            RowsRequest.model_validate(
                {
                    "where": [
                        {"field": "name", "op": "eq", "value": "x"},
                        {"totally": "bogus"},
                    ]
                }
            )


# ---------------------------------------------------------------------------
# 10. Malformed payloads -- discriminator adversarial
# ---------------------------------------------------------------------------


class TestMalformedPayloads:
    """Payloads that attempt to confuse the Pydantic model."""

    def test_missing_field_in_comparison(self) -> None:
        """Comparison requires field, op, value."""
        with pytest.raises(ValidationError):
            _adapter.validate_python({"op": "eq", "value": "x"})

    def test_missing_op_in_comparison(self) -> None:
        with pytest.raises(ValidationError):
            _adapter.validate_python({"field": "name", "value": "x"})

    def test_missing_value_in_comparison(self) -> None:
        with pytest.raises(ValidationError):
            _adapter.validate_python({"field": "name", "op": "eq"})

    def test_invalid_op_string(self) -> None:
        with pytest.raises(ValidationError):
            _adapter.validate_python({"field": "name", "op": "LIKE", "value": "%x%"})

    def test_extra_field_on_comparison(self) -> None:
        with pytest.raises(ValidationError):
            _adapter.validate_python(
                {"field": "name", "op": "eq", "value": "x", "extra": True}
            )

    def test_extra_field_on_and_group(self) -> None:
        with pytest.raises(ValidationError):
            _adapter.validate_python({"and": [], "bogus": True})

    def test_extra_field_on_or_group(self) -> None:
        with pytest.raises(ValidationError):
            _adapter.validate_python({"or": [], "bogus": True})

    def test_extra_field_on_not_group(self) -> None:
        with pytest.raises(ValidationError):
            _adapter.validate_python({"not": _leaf, "extra": True})

    def test_string_where_object_expected(self) -> None:
        with pytest.raises(ValidationError):
            _adapter.validate_python("not a predicate")

    def test_int_where_object_expected(self) -> None:
        with pytest.raises(ValidationError):
            _adapter.validate_python(42)

    def test_and_with_non_list(self) -> None:
        with pytest.raises(ValidationError):
            _adapter.validate_python({"and": "not a list"})

    def test_or_with_non_list(self) -> None:
        with pytest.raises(ValidationError):
            _adapter.validate_python({"or": "not a list"})

    def test_not_with_list(self) -> None:
        """not expects a single node, not a list."""
        with pytest.raises(ValidationError):
            _adapter.validate_python({"not": [_leaf, _leaf]})

    def test_empty_dict(self) -> None:
        """Empty dict matches 'comparison' discriminator but lacks fields."""
        with pytest.raises(ValidationError):
            _adapter.validate_python({})

    def test_null_predicate(self) -> None:
        with pytest.raises(ValidationError):
            _adapter.validate_python(None)

    def test_extra_field_on_rows_request(self) -> None:
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"unknown_param": "value"})

    def test_invalid_order_dir(self) -> None:
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"order_dir": "sideways"})

    def test_offset_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"offset": -5})

    def test_limit_float_rejected(self) -> None:
        """Float values for limit should be rejected or truncated."""
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"limit": 3.5})

    def test_ambiguous_dict_with_and_and_field(self) -> None:
        """Dict with both 'and' and 'field' -- discriminator picks 'and'.
        Should fail because extra='forbid' on AndGroup rejects 'field' key."""
        with pytest.raises(ValidationError):
            _adapter.validate_python(
                {"and": [_leaf], "field": "name", "op": "eq", "value": "x"}
            )

    def test_ambiguous_dict_with_or_and_field(self) -> None:
        """Dict with both 'or' and 'field' -- discriminator picks 'or'.
        Should fail because extra='forbid' on OrGroup rejects 'field' key."""
        with pytest.raises(ValidationError):
            _adapter.validate_python(
                {"or": [_leaf], "field": "name", "op": "eq", "value": "x"}
            )

    def test_ambiguous_dict_with_not_and_or(self) -> None:
        """Dict with both 'not' and 'or' -- discriminator checks 'and' first,
        then 'or', then 'not'. 'or' is found first, extra fields rejected."""
        with pytest.raises(ValidationError):
            _adapter.validate_python({"not": _leaf, "or": [_leaf]})

    def test_ambiguous_dict_with_and_and_or(self) -> None:
        """Dict with both 'and' and 'or' -- discriminator picks 'and'.
        'or' is extra field, rejected."""
        with pytest.raises(ValidationError):
            _adapter.validate_python({"and": [_leaf], "or": [_leaf]})

    def test_and_with_null_value(self) -> None:
        """'and': null should be rejected (expects list)."""
        with pytest.raises(ValidationError):
            _adapter.validate_python({"and": None})

    def test_or_with_null_value(self) -> None:
        """'or': null should be rejected (expects list)."""
        with pytest.raises(ValidationError):
            _adapter.validate_python({"or": None})

    def test_not_with_null_value(self) -> None:
        """'not': null should be rejected (expects PredicateNode)."""
        with pytest.raises(ValidationError):
            _adapter.validate_python({"not": None})

    def test_where_false(self) -> None:
        """where: false (boolean) should be rejected by RowsRequest."""
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"where": False})

    def test_where_zero(self) -> None:
        """where: 0 (int) should be rejected by RowsRequest."""
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"where": 0})

    def test_where_empty_string(self) -> None:
        """where: '' (empty string) should be rejected by RowsRequest."""
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"where": ""})

    def test_where_true(self) -> None:
        """where: true (boolean) should be rejected."""
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"where": True})

    def test_nested_object_as_comparison_value(self) -> None:
        """Value is a nested dict -- should parse (value: Any) but fail at coercion."""
        # Pydantic allows Any for value, so this parses
        node = _adapter.validate_python(
            {"field": "name", "op": "eq", "value": {"nested": True}}
        )
        assert isinstance(node, Comparison)
        assert node.value == {"nested": True}

    def test_no_recognized_keys(self) -> None:
        """Dict with no recognized keys falls through discriminator to comparison."""
        with pytest.raises(ValidationError):
            _adapter.validate_python({"foo": "bar", "baz": 42})


# ---------------------------------------------------------------------------
# 11. Strip section predicates
# ---------------------------------------------------------------------------


class TestStripSectionPredicates:
    """Adversarial tests for section predicate stripping (EC-006)."""

    def test_strip_section_from_and(self) -> None:
        """Section comparison inside AND is removed."""
        node = _adapter.validate_python(
            {
                "and": [
                    {"field": "section", "op": "eq", "value": "Active"},
                    {"field": "name", "op": "eq", "value": "Acme"},
                ]
            }
        )
        result = strip_section_predicates(node)
        assert isinstance(result, Comparison)
        assert result.field == "name"

    def test_strip_all_section_returns_none(self) -> None:
        """If entire tree is section predicates, returns None."""
        node = _adapter.validate_python(
            {"field": "section", "op": "eq", "value": "Active"}
        )
        result = strip_section_predicates(node)
        assert result is None

    def test_strip_section_from_or(self) -> None:
        node = _adapter.validate_python(
            {
                "or": [
                    {"field": "section", "op": "eq", "value": "Active"},
                    {"field": "name", "op": "eq", "value": "Acme"},
                ]
            }
        )
        result = strip_section_predicates(node)
        assert isinstance(result, Comparison)
        assert result.field == "name"

    def test_strip_section_from_not(self) -> None:
        node = _adapter.validate_python(
            {"not": {"field": "section", "op": "eq", "value": "Active"}}
        )
        result = strip_section_predicates(node)
        assert result is None

    def test_strip_preserves_non_section(self) -> None:
        node = _adapter.validate_python(
            {
                "and": [
                    {"field": "name", "op": "eq", "value": "Acme"},
                    {"field": "age", "op": "gt", "value": 20},
                ]
            }
        )
        result = strip_section_predicates(node)
        assert isinstance(result, AndGroup)
        assert len(result.and_) == 2

    def test_strip_deep_nested_section(self) -> None:
        """Section predicate deeply nested inside AND->OR->AND."""
        node = _adapter.validate_python(
            {
                "and": [
                    {"field": "name", "op": "eq", "value": "Acme"},
                    {
                        "or": [
                            {"field": "section", "op": "eq", "value": "Active"},
                            {"field": "age", "op": "gt", "value": 20},
                        ]
                    },
                ]
            }
        )
        result = strip_section_predicates(node)
        assert isinstance(result, AndGroup)
        # The OR should have had section removed, leaving just age
        assert len(result.and_) == 2
        # Second child was OR with section removed -> just the age comparison
        assert isinstance(result.and_[1], Comparison)
        assert result.and_[1].field == "age"

    def test_strip_multiple_section_predicates(self) -> None:
        """Multiple section comparisons in different positions."""
        node = _adapter.validate_python(
            {
                "and": [
                    {"field": "section", "op": "eq", "value": "Active"},
                    {"field": "name", "op": "eq", "value": "Acme"},
                    {"field": "section", "op": "in", "value": ["Active", "Won"]},
                ]
            }
        )
        result = strip_section_predicates(node)
        assert isinstance(result, Comparison)
        assert result.field == "name"


# ---------------------------------------------------------------------------
# 12. Error serialization completeness
# ---------------------------------------------------------------------------


class TestErrorSerialization:
    """Verify all error types serialize to well-formed dicts."""

    def test_query_too_complex_error(self) -> None:
        err = QueryTooComplexError(depth=10, max_depth=5)
        d = err.to_dict()
        assert d["error"] == "QUERY_TOO_COMPLEX"
        assert d["max_depth"] == 5
        assert "10" in d["message"]

    def test_unknown_field_error(self) -> None:
        err = UnknownFieldError(field="bogus", available=["c", "a", "b"])
        d = err.to_dict()
        assert d["error"] == "UNKNOWN_FIELD"
        assert d["available_fields"] == ["a", "b", "c"]  # sorted

    def test_invalid_operator_error(self) -> None:
        err = InvalidOperatorError(
            field="age", dtype="Int64", op="contains", allowed=["eq", "gt"]
        )
        d = err.to_dict()
        assert d["error"] == "INVALID_OPERATOR"
        assert d["field"] == "age"
        assert d["operator"] == "contains"

    def test_coercion_error(self) -> None:
        err = CoercionError(field="age", dtype="Int64", value="abc", reason="bad")
        d = err.to_dict()
        assert d["error"] == "COERCION_FAILED"
        assert d["value"] == "abc"

    def test_unknown_section_error(self) -> None:
        err = UnknownSectionError(section="Bogus")
        d = err.to_dict()
        assert d["error"] == "UNKNOWN_SECTION"
        assert d["section"] == "Bogus"

    def test_all_errors_are_query_engine_error_subclasses(self) -> None:
        """Verify error hierarchy: all errors inherit from QueryEngineError."""
        assert issubclass(QueryTooComplexError, QueryEngineError)
        assert issubclass(UnknownFieldError, QueryEngineError)
        assert issubclass(InvalidOperatorError, QueryEngineError)
        assert issubclass(CoercionError, QueryEngineError)
        assert issubclass(UnknownSectionError, QueryEngineError)

    def test_query_engine_error_base_to_dict_raises(self) -> None:
        """Base QueryEngineError.to_dict() raises NotImplementedError."""
        # QueryEngineError is a dataclass, so instantiate without fields
        # Actually it has no fields besides what Exception gives it
        err = QueryEngineError()
        with pytest.raises(NotImplementedError):
            err.to_dict()

    def test_error_instances_are_exceptions(self) -> None:
        """All error instances can be raised and caught as exceptions."""
        errors = [
            QueryTooComplexError(depth=10, max_depth=5),
            UnknownFieldError(field="x", available=["y"]),
            InvalidOperatorError(field="x", dtype="Int64", op="gt", allowed=["eq"]),
            CoercionError(field="x", dtype="Int64", value="abc", reason="bad"),
            UnknownSectionError(section="Bogus"),
        ]
        for err in errors:
            assert isinstance(err, Exception)
            assert isinstance(err, QueryEngineError)


# ---------------------------------------------------------------------------
# 13. Pagination edge cases
# ---------------------------------------------------------------------------


class TestPaginationEdgeCases:
    """Adversarial offset/limit combinations."""

    @pytest.fixture
    def small_df(self) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", "B", "C"],
                "section": ["X", "X", "X"],
            }
        )

    @pytest.fixture
    def small_schema(self) -> DataFrameSchema:
        return DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
            ],
        )

    @pytest.fixture
    def small_engine(self, small_df: pl.DataFrame) -> QueryEngine:
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=small_df)  # type: ignore[method-assign]
        return QueryEngine(query_service=service)

    @pytest.mark.asyncio
    async def test_offset_beyond_dataset(
        self, small_engine: QueryEngine, small_schema: DataFrameSchema
    ) -> None:
        """Offset past all rows returns empty result."""
        request = RowsRequest.model_validate({"offset": 100, "limit": 10})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = small_schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await small_engine.execute_rows(
                entity_type="test",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
            )
        assert result.meta.total_count == 3
        assert result.meta.returned_count == 0
        assert result.data == []

    @pytest.mark.asyncio
    async def test_offset_equals_total(
        self, small_engine: QueryEngine, small_schema: DataFrameSchema
    ) -> None:
        """Offset exactly at total count returns empty."""
        request = RowsRequest.model_validate({"offset": 3, "limit": 10})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = small_schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await small_engine.execute_rows(
                entity_type="test",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
            )
        assert result.meta.returned_count == 0

    @pytest.mark.asyncio
    async def test_limit_1_returns_one(
        self, small_engine: QueryEngine, small_schema: DataFrameSchema
    ) -> None:
        request = RowsRequest.model_validate({"limit": 1})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = small_schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await small_engine.execute_rows(
                entity_type="test",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
            )
        assert result.meta.returned_count == 1

    @pytest.mark.asyncio
    async def test_offset_plus_limit_exceeds_total(
        self, small_engine: QueryEngine, small_schema: DataFrameSchema
    ) -> None:
        """offset=2, limit=100 on 3-row df returns 1 row."""
        request = RowsRequest.model_validate({"offset": 2, "limit": 100})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = small_schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await small_engine.execute_rows(
                entity_type="test",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
            )
        assert result.meta.returned_count == 1

    @pytest.mark.asyncio
    async def test_limit_clamped_by_max_result_rows(self) -> None:
        """limit: 50000 with MAX_RESULT_ROWS=10000 is clamped."""
        # RowsRequest caps at 1000, but QueryLimits clamps further
        # Test the engine-level clamping
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
            ],
        )
        df = pl.DataFrame(
            {"gid": ["1", "2"], "name": ["A", "B"], "section": ["S", "S"]}
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        # Use custom limits with low max to test clamping
        engine = QueryEngine(
            query_service=service,
            limits=QueryLimits(max_result_rows=1),
        )

        request = RowsRequest.model_validate({"limit": 1000})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await engine.execute_rows(
                entity_type="test",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
            )
        assert result.meta.limit == 1
        assert result.meta.returned_count == 1
        assert result.meta.total_count == 2  # total before pagination


# ---------------------------------------------------------------------------
# 14. Compiler with real DataFrame execution
# ---------------------------------------------------------------------------


class TestCompilerPolarsExecution:
    """Verify compiled expressions actually work against Polars DataFrames."""

    def test_contains_regex_special_chars(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """Contains uses literal=True, so regex special chars are safe."""
        node = Comparison(field="name", op=Op.CONTAINS, value="(.*)")
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"name": ["test(.*)", "normal", "(.*)start"]})
        result = df.filter(expr)
        assert len(result) == 2  # literal match, not regex

    def test_starts_with_regex_special_chars(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.STARTS_WITH, value="^abc")
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"name": ["^abc123", "abc123", "^abc"]})
        result = df.filter(expr)
        assert len(result) == 2  # literal match

    def test_in_empty_list_matches_nothing(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.IN, value=[])
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta"]})
        assert len(df.filter(expr)) == 0

    def test_not_in_empty_list_matches_everything(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.NOT_IN, value=[])
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta"]})
        assert len(df.filter(expr)) == 2

    def test_eq_with_nan_float(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """Polars treats NaN == NaN as True (unlike IEEE 754).

        This is documented Polars behavior, not a bug. Users filtering with
        NaN will match NaN values in the DataFrame.
        """
        node = Comparison(field="score", op=Op.EQ, value="nan")
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"score": [1.0, float("nan"), 3.0]})
        result = df.filter(expr)
        # Polars: NaN == NaN is True (diverges from IEEE 754)
        assert len(result) == 1

    def test_gt_with_nan_float(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """NaN comparisons are always false."""
        node = Comparison(field="score", op=Op.GT, value="nan")
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"score": [1.0, 100.0, float("nan")]})
        result = df.filter(expr)
        assert len(result) == 0  # nothing is > NaN

    def test_empty_string_contains(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """Every string contains the empty string."""
        node = Comparison(field="name", op=Op.CONTAINS, value="")
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta", ""]})
        assert len(df.filter(expr)) == 3

    def test_empty_string_starts_with(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """Every string starts with the empty string."""
        node = Comparison(field="name", op=Op.STARTS_WITH, value="")
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta"]})
        assert len(df.filter(expr)) == 2

    def test_boolean_eq_with_polars_df(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """Boolean eq with actual boolean value against DataFrame."""
        node = Comparison(field="is_active", op=Op.EQ, value=True)
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"is_active": [True, False, True, False]})
        assert len(df.filter(expr)) == 2

    def test_date_gte_with_polars_df(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """Date gte comparison against DataFrame."""
        node = Comparison(field="created_date", op=Op.GTE, value="2026-01-15")
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame(
            {"created_date": [date(2026, 1, 14), date(2026, 1, 15), date(2026, 1, 16)]}
        )
        assert len(df.filter(expr)) == 2

    def test_in_with_all_none_list_matches_nothing(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """in with [null, null] -- nulls stripped, becomes empty list."""
        node = Comparison(field="name", op=Op.IN, value=[None, None])
        expr = compiler.compile(node, full_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta"]})
        # Coercion strips nulls -> empty list -> matches nothing
        assert len(df.filter(expr)) == 0


# ---------------------------------------------------------------------------
# 15. Operator matrix completeness check
# ---------------------------------------------------------------------------


class TestOperatorMatrixExhaustive:
    """Verify every INVALID cell in the operator x dtype matrix fires correctly."""

    INVALID_CELLS = [
        # (dtype, field_name, op, value) -- every invalid combination
        ("Int64", "age", Op.CONTAINS, "3"),
        ("Int64", "age", Op.STARTS_WITH, "3"),
        ("Int32", "rank", Op.CONTAINS, "1"),
        ("Int32", "rank", Op.STARTS_WITH, "1"),
        ("Float64", "score", Op.CONTAINS, "3"),
        ("Float64", "score", Op.STARTS_WITH, "3"),
        ("Boolean", "is_active", Op.GT, True),
        ("Boolean", "is_active", Op.LT, True),
        ("Boolean", "is_active", Op.GTE, True),
        ("Boolean", "is_active", Op.LTE, True),
        ("Boolean", "is_active", Op.CONTAINS, "true"),
        ("Boolean", "is_active", Op.STARTS_WITH, "t"),
        ("Date", "created_date", Op.CONTAINS, "2024"),
        ("Date", "created_date", Op.STARTS_WITH, "2024"),
        ("Datetime", "created_at", Op.CONTAINS, "2024"),
        ("Datetime", "created_at", Op.STARTS_WITH, "2024"),
        ("Decimal", "amount", Op.CONTAINS, "100"),
        ("Decimal", "amount", Op.STARTS_WITH, "1"),
    ]

    @pytest.mark.parametrize("dtype,field_name,op,value", INVALID_CELLS)
    def test_invalid_operator_dtype_cell(
        self,
        compiler: PredicateCompiler,
        full_schema: DataFrameSchema,
        dtype: str,
        field_name: str,
        op: Op,
        value: object,
    ) -> None:
        """Each invalid cell in the operator x dtype matrix must raise InvalidOperatorError."""
        node = Comparison(field=field_name, op=op, value=value)
        with pytest.raises(InvalidOperatorError) as exc:
            compiler.compile(node, full_schema)
        assert exc.value.field == field_name
        assert exc.value.dtype == dtype

    def test_list_utf8_all_ops_invalid(
        self, compiler: PredicateCompiler, full_schema: DataFrameSchema
    ) -> None:
        """All 10 operators are invalid for List[Utf8] in Sprint 1."""
        for op in Op:
            node = Comparison(field="tags", op=op, value="x")
            with pytest.raises(InvalidOperatorError):
                compiler.compile(node, full_schema)


# ---------------------------------------------------------------------------
# 16. Engine integration adversarial (mocked EntityQueryService)
# ---------------------------------------------------------------------------


class TestEngineIntegrationAdversarial:
    """Adversarial engine tests with mocked service."""

    @pytest.fixture
    def engine_schema(self) -> DataFrameSchema:
        return DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
                ColumnDef("score", "Float64", nullable=True),
            ],
        )

    def _make_engine(self, df: pl.DataFrame) -> QueryEngine:
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        return QueryEngine(query_service=service)

    @pytest.mark.asyncio
    async def test_response_query_ms_positive(
        self, engine_schema: DataFrameSchema
    ) -> None:
        """query_ms in response metadata should be >= 0."""
        df = pl.DataFrame(
            {"gid": ["1"], "name": ["A"], "section": ["S"], "score": [1.0]}
        )
        engine = self._make_engine(df)
        request = RowsRequest.model_validate({})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = engine_schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await engine.execute_rows(
                entity_type="test",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
            )
        assert result.meta.query_ms >= 0

    @pytest.mark.asyncio
    async def test_depth_guard_fires_before_io(
        self, engine_schema: DataFrameSchema
    ) -> None:
        """Depth guard should reject BEFORE loading DataFrame (fail-fast)."""
        service = EntityQueryService()
        service.get_dataframe = AsyncMock()  # type: ignore[method-assign]
        engine = QueryEngine(query_service=service)

        deep_pred = _build_deep_and_chain(6)
        request = RowsRequest.model_validate({"where": deep_pred})

        with pytest.raises(QueryTooComplexError):
            await engine.execute_rows(
                entity_type="test",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
            )
        # get_dataframe should NOT have been called
        service.get_dataframe.assert_not_called()

    @pytest.mark.asyncio
    async def test_default_select_includes_gid_name_section(
        self, engine_schema: DataFrameSchema
    ) -> None:
        """Default select (None) returns gid, name, section."""
        df = pl.DataFrame(
            {"gid": ["1"], "name": ["A"], "section": ["S"], "score": [1.0]}
        )
        engine = self._make_engine(df)
        request = RowsRequest.model_validate({})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = engine_schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await engine.execute_rows(
                entity_type="test",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
            )
        assert "gid" in result.data[0]
        assert "name" in result.data[0]
        assert "section" in result.data[0]
        # score should NOT be in default select
        assert "score" not in result.data[0]
