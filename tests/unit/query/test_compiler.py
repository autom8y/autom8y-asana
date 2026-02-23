"""Tests for query/compiler.py: Operator x dtype matrix, coercion, expression assembly."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime

import polars as pl
import pytest
from pydantic import TypeAdapter

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.query.compiler import (
    OPERATOR_MATRIX,
    PredicateCompiler,
    _coerce_scalar,
    _coerce_value,
    strip_section_predicates,
)
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
    PredicateNode,
)

_adapter = TypeAdapter(PredicateNode)


@pytest.fixture
def test_schema() -> DataFrameSchema:
    """Schema with one column per dtype for compiler tests."""
    return DataFrameSchema(
        name="test",
        task_type="Test",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("age", "Int64", nullable=True),
            ColumnDef("score", "Float64", nullable=True),
            ColumnDef("is_active", "Boolean", nullable=False),
            ColumnDef("created_date", "Date", nullable=True),
            ColumnDef("created_at", "Datetime", nullable=True),
            ColumnDef("amount", "Decimal", nullable=True),
            ColumnDef("rank", "Int32", nullable=True),
            ColumnDef("tags", "List[Utf8]", nullable=True),
        ],
    )


@pytest.fixture
def compiler() -> PredicateCompiler:
    return PredicateCompiler()


# ---------------------------------------------------------------------------
# Comparison operators on Utf8
# ---------------------------------------------------------------------------


class TestCompilerUtf8:
    """Utf8 supports all 10 operators."""

    def test_eq(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.EQ, value="Acme")
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta", "Acme"]})
        assert df.filter(expr)["name"].to_list() == ["Acme", "Acme"]

    def test_ne(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.NE, value="Acme")
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta"]})
        assert df.filter(expr)["name"].to_list() == ["Beta"]

    def test_contains(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.CONTAINS, value="cm")
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta", "Acme Dental"]})
        assert len(df.filter(expr)) == 2

    def test_starts_with(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.STARTS_WITH, value="Ac")
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta", "Acrobat"]})
        assert df.filter(expr)["name"].to_list() == ["Acme", "Acrobat"]

    def test_in(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.IN, value=["Acme", "Beta"])
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta", "Gamma"]})
        assert len(df.filter(expr)) == 2

    def test_not_in(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.NOT_IN, value=["Acme"])
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta", "Gamma"]})
        assert len(df.filter(expr)) == 2

    def test_gt(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.GT, value="B")
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta", "Gamma"]})
        assert df.filter(expr)["name"].to_list() == ["Beta", "Gamma"]

    def test_number_coerced_to_string(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        """EC-007: numeric value permissive coercion to Utf8."""
        node = Comparison(field="name", op=Op.EQ, value=123)
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["123", "456"]})
        assert df.filter(expr)["name"].to_list() == ["123"]


# ---------------------------------------------------------------------------
# Boolean dtype
# ---------------------------------------------------------------------------


class TestCompilerBoolean:
    """Boolean supports eq, ne, in, not_in only."""

    def test_eq_true(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="is_active", op=Op.EQ, value=True)
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"is_active": [True, False, True]})
        assert len(df.filter(expr)) == 2

    def test_gt_rejected(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="is_active", op=Op.GT, value=True)
        with pytest.raises(InvalidOperatorError) as exc_info:
            compiler.compile(node, test_schema)
        assert exc_info.value.field == "is_active"
        assert exc_info.value.dtype == "Boolean"

    def test_contains_rejected(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="is_active", op=Op.CONTAINS, value="true")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, test_schema)


# ---------------------------------------------------------------------------
# Int64 dtype
# ---------------------------------------------------------------------------


class TestCompilerInt64:
    """Int64 supports universal + orderable, not string ops."""

    def test_eq(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="age", op=Op.EQ, value=30)
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"age": [25, 30, 35]})
        assert df.filter(expr)["age"].to_list() == [30]

    def test_gt(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="age", op=Op.GT, value=30)
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"age": [25, 30, 35]})
        assert df.filter(expr)["age"].to_list() == [35]

    def test_contains_rejected(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="age", op=Op.CONTAINS, value="3")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, test_schema)

    def test_string_coercion(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="age", op=Op.EQ, value="30")
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"age": [25, 30, 35]})
        assert df.filter(expr)["age"].to_list() == [30]

    def test_in_list(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="age", op=Op.IN, value=[25, 35])
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"age": [25, 30, 35]})
        assert df.filter(expr)["age"].to_list() == [25, 35]


# ---------------------------------------------------------------------------
# Date dtype
# ---------------------------------------------------------------------------


class TestCompilerDate:
    """Date supports universal + orderable, not string ops."""

    def test_eq(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="created_date", op=Op.EQ, value="2026-01-15")
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"created_date": [date(2026, 1, 15), date(2026, 2, 1)]})
        assert len(df.filter(expr)) == 1

    def test_gt(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="created_date", op=Op.GT, value="2026-01-15")
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"created_date": [date(2026, 1, 15), date(2026, 2, 1)]})
        assert len(df.filter(expr)) == 1


# ---------------------------------------------------------------------------
# Datetime dtype
# ---------------------------------------------------------------------------


class TestCompilerDatetime:
    """Datetime supports universal + orderable, not string ops."""

    def test_eq_with_z_suffix(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="created_at", op=Op.EQ, value="2026-01-15T10:30:00Z")
        expr = compiler.compile(node, test_schema)
        dt_val = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        df = pl.DataFrame({"created_at": [dt_val]})
        assert len(df.filter(expr)) == 1


# ---------------------------------------------------------------------------
# List[Utf8] dtype -- no operators in Sprint 1
# ---------------------------------------------------------------------------


class TestCompilerListUtf8:
    """List[Utf8] supports no operators."""

    def test_eq_rejected(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="tags", op=Op.EQ, value="foo")
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, test_schema)


# ---------------------------------------------------------------------------
# Unknown field
# ---------------------------------------------------------------------------


class TestCompilerUnknownField:
    def test_unknown_field_raises(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="nonexistent", op=Op.EQ, value="x")
        with pytest.raises(UnknownFieldError) as exc_info:
            compiler.compile(node, test_schema)
        assert exc_info.value.field == "nonexistent"
        assert "gid" in exc_info.value.available


# ---------------------------------------------------------------------------
# Coercion failures
# ---------------------------------------------------------------------------


class TestCoercionFailures:
    def test_abc_to_int(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("abc", "Int64", "age")

    def test_non_iso_date(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("not-a-date", "Date", "created_date")

    def test_non_bool_to_boolean(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar("true", "Boolean", "is_active")

    def test_int_to_date(self) -> None:
        with pytest.raises(CoercionError):
            _coerce_scalar(12345, "Date", "created_date")

    def test_in_requires_list(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = Comparison(field="age", op=Op.IN, value=30)
        with pytest.raises(CoercionError) as exc_info:
            compiler.compile(node, test_schema)
        assert "list" in exc_info.value.reason


# ---------------------------------------------------------------------------
# Group compilation
# ---------------------------------------------------------------------------


class TestGroupCompilation:
    """Test AND, OR, NOT expression assembly."""

    def test_and_combines(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = _adapter.validate_python(
            {
                "and": [
                    {"field": "name", "op": "eq", "value": "Acme"},
                    {"field": "age", "op": "gt", "value": 25},
                ]
            }
        )
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["Acme", "Acme", "Beta"], "age": [20, 30, 30]})
        result = df.filter(expr)
        assert len(result) == 1
        assert result["age"].to_list() == [30]

    def test_or_combines(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = _adapter.validate_python(
            {
                "or": [
                    {"field": "name", "op": "eq", "value": "Acme"},
                    {"field": "name", "op": "eq", "value": "Beta"},
                ]
            }
        )
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta", "Gamma"]})
        assert len(df.filter(expr)) == 2

    def test_not_inverts(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = _adapter.validate_python(
            {"not": {"field": "name", "op": "eq", "value": "Acme"}}
        )
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta", "Gamma"]})
        assert df.filter(expr)["name"].to_list() == ["Beta", "Gamma"]

    def test_empty_and_returns_true(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = _adapter.validate_python({"and": []})
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta"]})
        assert len(df.filter(expr)) == 2

    def test_empty_or_returns_false(
        self, compiler: PredicateCompiler, test_schema: DataFrameSchema
    ) -> None:
        node = _adapter.validate_python({"or": []})
        expr = compiler.compile(node, test_schema)
        df = pl.DataFrame({"name": ["Acme", "Beta"]})
        assert len(df.filter(expr)) == 0


# ---------------------------------------------------------------------------
# Operator matrix completeness
# ---------------------------------------------------------------------------


class TestOperatorMatrix:
    """Verify matrix has entries for all expected dtypes."""

    EXPECTED_DTYPES = {
        "Utf8",
        "Int64",
        "Int32",
        "Float64",
        "Boolean",
        "Date",
        "Datetime",
        "Decimal",
        "List[Utf8]",
    }

    def test_all_dtypes_present(self) -> None:
        assert set(OPERATOR_MATRIX.keys()) == self.EXPECTED_DTYPES

    def test_boolean_no_orderable(self) -> None:
        bool_ops = OPERATOR_MATRIX["Boolean"]
        assert Op.GT not in bool_ops
        assert Op.LT not in bool_ops
        assert Op.GTE not in bool_ops
        assert Op.LTE not in bool_ops

    def test_utf8_has_string_ops(self) -> None:
        utf8_ops = OPERATOR_MATRIX["Utf8"]
        assert Op.CONTAINS in utf8_ops
        assert Op.STARTS_WITH in utf8_ops

    def test_int64_no_string_ops(self) -> None:
        int_ops = OPERATOR_MATRIX["Int64"]
        assert Op.CONTAINS not in int_ops
        assert Op.STARTS_WITH not in int_ops

    def test_list_utf8_empty(self) -> None:
        assert OPERATOR_MATRIX["List[Utf8]"] == frozenset()


# ---------------------------------------------------------------------------
# Coercion edge cases (merged from test_adversarial.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def full_schema_for_coercion() -> DataFrameSchema:
    """Schema with one column per dtype for comprehensive coercion testing."""
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


class TestNullPropagation:
    """Verify behavior when DataFrame columns contain null values."""

    def test_eq_with_nulls_excludes_nulls(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        """Polars eq comparison: null != 'Acme', so null rows are excluded."""
        node = Comparison(field="name", op=Op.EQ, value="Acme")
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"name": ["Acme", None, "Beta"]})
        result = df.filter(expr)
        assert result["name"].to_list() == ["Acme"]

    def test_ne_with_nulls_excludes_nulls(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        """Polars ne: null != 'Acme' is null (falsy), not True."""
        node = Comparison(field="name", op=Op.NE, value="Acme")
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"name": ["Acme", None, "Beta"]})
        result = df.filter(expr)
        # null rows are excluded (null is not True)
        assert result["name"].to_list() == ["Beta"]

    def test_gt_with_nulls_excludes_nulls(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        node = Comparison(field="age", op=Op.GT, value=20)
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"age": [10, None, 30]})
        result = df.filter(expr)
        assert result["age"].to_list() == [30]

    def test_in_with_nulls(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.IN, value=["Acme", "Beta"])
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"name": ["Acme", None, "Beta", None]})
        result = df.filter(expr)
        assert len(result) == 2

    def test_not_with_nulls(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        """NOT(eq) with nulls: NOT(null) is null, so null rows excluded."""
        node = NotGroup.model_validate(
            {"not": {"field": "name", "op": "eq", "value": "Acme"}}
        )
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"name": ["Acme", None, "Beta"]})
        result = df.filter(expr)
        # NOT(True)=False, NOT(null)=null(excluded), NOT(False)=True
        assert result["name"].to_list() == ["Beta"]

    def test_or_with_one_null_column(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
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
        expr = compiler.compile(node, full_schema_for_coercion)
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
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.CONTAINS, value="cm")
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"name": ["Acme", None, "Beta"]})
        result = df.filter(expr)
        assert result["name"].to_list() == ["Acme"]


class TestCompilerPolarsExecution:
    """Verify compiled expressions actually work against Polars DataFrames."""

    def test_contains_regex_special_chars(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        """Contains uses literal=True, so regex special chars are safe."""
        node = Comparison(field="name", op=Op.CONTAINS, value="(.*)")
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"name": ["test(.*)", "normal", "(.*)start"]})
        result = df.filter(expr)
        assert len(result) == 2  # literal match, not regex

    def test_starts_with_regex_special_chars(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.STARTS_WITH, value="^abc")
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"name": ["^abc123", "abc123", "^abc"]})
        result = df.filter(expr)
        assert len(result) == 2  # literal match

    def test_in_empty_list_matches_nothing(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.IN, value=[])
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"name": ["Acme", "Beta"]})
        assert len(df.filter(expr)) == 0

    def test_not_in_empty_list_matches_everything(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        node = Comparison(field="name", op=Op.NOT_IN, value=[])
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"name": ["Acme", "Beta"]})
        assert len(df.filter(expr)) == 2

    def test_eq_with_nan_float(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        """Polars treats NaN == NaN as True (unlike IEEE 754).

        This is documented Polars behavior, not a bug. Users filtering with
        NaN will match NaN values in the DataFrame.
        """
        node = Comparison(field="score", op=Op.EQ, value="nan")
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"score": [1.0, float("nan"), 3.0]})
        result = df.filter(expr)
        # Polars: NaN == NaN is True (diverges from IEEE 754)
        assert len(result) == 1

    def test_gt_with_nan_float(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        """NaN comparisons are always false."""
        node = Comparison(field="score", op=Op.GT, value="nan")
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"score": [1.0, 100.0, float("nan")]})
        result = df.filter(expr)
        assert len(result) == 0  # nothing is > NaN

    def test_empty_string_contains(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        """Every string contains the empty string."""
        node = Comparison(field="name", op=Op.CONTAINS, value="")
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"name": ["Acme", "Beta", ""]})
        assert len(df.filter(expr)) == 3

    def test_empty_string_starts_with(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        """Every string starts with the empty string."""
        node = Comparison(field="name", op=Op.STARTS_WITH, value="")
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"name": ["Acme", "Beta"]})
        assert len(df.filter(expr)) == 2

    def test_boolean_eq_with_polars_df(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        """Boolean eq with actual boolean value against DataFrame."""
        node = Comparison(field="is_active", op=Op.EQ, value=True)
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"is_active": [True, False, True, False]})
        assert len(df.filter(expr)) == 2

    def test_date_gte_with_polars_df(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        """Date gte comparison against DataFrame."""
        node = Comparison(field="created_date", op=Op.GTE, value="2026-01-15")
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame(
            {"created_date": [date(2026, 1, 14), date(2026, 1, 15), date(2026, 1, 16)]}
        )
        assert len(df.filter(expr)) == 2

    def test_in_with_all_none_list_matches_nothing(
        self, compiler: PredicateCompiler, full_schema_for_coercion: DataFrameSchema
    ) -> None:
        """in with [null, null] -- nulls stripped, becomes empty list."""
        node = Comparison(field="name", op=Op.IN, value=[None, None])
        expr = compiler.compile(node, full_schema_for_coercion)
        df = pl.DataFrame({"name": ["Acme", "Beta"]})
        # Coercion strips nulls -> empty list -> matches nothing
        assert len(df.filter(expr)) == 0


class TestStripSectionPredicates:
    """Tests for section predicate stripping (EC-006)."""

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
