"""Tests for query/compiler.py: Operator x dtype matrix, coercion, expression assembly."""

from __future__ import annotations

from datetime import date, datetime, timezone

import polars as pl
import pytest

from pydantic import TypeAdapter

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.query.compiler import (
    OPERATOR_MATRIX,
    PredicateCompiler,
    _coerce_scalar,
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
    OrGroup,
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
        dt_val = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
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
