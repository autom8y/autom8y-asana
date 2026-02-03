"""Adversarial tests for /aggregate endpoint (Sprint 2, Cycle 2).

QA Adversary validation: tests designed to break the aggregation pipeline
by exercising edge cases, boundary conditions, and error paths that a
malicious, impatient, confused, or unlucky user might trigger.

Test target areas:
1. AggSpec model edge cases
2. GROUP BY edge cases
3. HAVING edge cases
4. Aggregation compilation edge cases (numeric casting, nulls)
5. Engine integration adversarial
6. API endpoint edge cases
7. Numeric casting adversarial (ADR-AGG-005)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from pydantic import TypeAdapter, ValidationError

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.query.aggregator import (
    AGG_COMPATIBILITY,
    AggregationCompiler,
    build_post_agg_schema,
    validate_alias_uniqueness,
)
from autom8_asana.query.compiler import PredicateCompiler
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import (
    AggregateGroupLimitError,
    AggregationError,
    QueryTooComplexError,
    UnknownFieldError,
)
from autom8_asana.query.guards import QueryLimits
from autom8_asana.query.models import (
    AggFunction,
    AggregateRequest,
    AggSpec,
    PredicateNode,
)
from autom8_asana.services.query_service import EntityQueryService


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def offer_schema() -> DataFrameSchema:
    """Offer-like schema with Utf8 financial columns and List column."""
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("vertical", "Utf8", nullable=True),
            ColumnDef("section", "Utf8", nullable=True),
            ColumnDef("mrr", "Utf8", nullable=True),
            ColumnDef("cost", "Utf8", nullable=True),
            ColumnDef("amount", "Float64", nullable=True),
            ColumnDef("quantity", "Int64", nullable=True),
            ColumnDef("is_active", "Boolean", nullable=True),
            ColumnDef("created_date", "Date", nullable=True),
            ColumnDef("platforms", "List[Utf8]", nullable=True),
        ],
    )


@pytest.fixture
def mock_client() -> AsyncMock:
    return AsyncMock()


def _patch_schema(schema: DataFrameSchema):
    """Context manager to patch SchemaRegistry for tests."""
    return patch(
        "autom8_asana.query.engine.SchemaRegistry",
        **{
            "return_value.get_schema.return_value": schema,
            "get_instance.return_value.get_schema.return_value": schema,
        },
    )


def _make_engine(df: pl.DataFrame, **limits_kwargs) -> QueryEngine:
    """Build a QueryEngine with a mocked service returning the given DataFrame."""
    service = EntityQueryService()
    service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
    limits = QueryLimits(**limits_kwargs) if limits_kwargs else QueryLimits()
    return QueryEngine(query_service=service, limits=limits)


# ===========================================================================
# 1. AggSpec Model Edge Cases
# ===========================================================================


class TestAggSpecModelEdgeCases:
    """Adversarial tests for AggSpec and AggregateRequest Pydantic models."""

    def test_aggspec_empty_string_column(self) -> None:
        """AggSpec with empty string column name is accepted by Pydantic
        but should fail at compilation time (column not in schema)."""
        spec = AggSpec(column="", agg=AggFunction.SUM, alias="total")
        assert spec.column == ""

    def test_aggspec_alias_collides_with_group_by(self) -> None:
        """AggSpec alias that matches a group_by column is caught by validate_alias_uniqueness."""
        specs = [AggSpec(column="amount", agg=AggFunction.SUM, alias="vertical")]
        with pytest.raises(AggregationError, match="collides with group_by"):
            validate_alias_uniqueness(specs, ["vertical"])

    def test_duplicate_aliases_in_aggregation_list(self) -> None:
        """Duplicate explicit aliases are rejected."""
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM, alias="total"),
            AggSpec(column="cost", agg=AggFunction.SUM, alias="total"),
        ]
        with pytest.raises(AggregationError, match="Duplicate alias"):
            validate_alias_uniqueness(specs, ["vertical"])

    def test_duplicate_default_aliases_same_column_same_func(self) -> None:
        """Two AggSpecs on same column with same function produce colliding default aliases."""
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM),
            AggSpec(column="amount", agg=AggFunction.SUM),
        ]
        # Default alias for both: "sum_amount" -- should collide
        with pytest.raises(AggregationError, match="Duplicate alias"):
            validate_alias_uniqueness(specs, ["vertical"])

    def test_all_six_agg_functions_on_same_column(self, offer_schema: DataFrameSchema) -> None:
        """All 6 agg functions applied to a single Float64 column compiles successfully."""
        compiler = AggregationCompiler()
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM, alias="s"),
            AggSpec(column="amount", agg=AggFunction.COUNT, alias="c"),
            AggSpec(column="amount", agg=AggFunction.MEAN, alias="m"),
            AggSpec(column="amount", agg=AggFunction.MIN, alias="mn"),
            AggSpec(column="amount", agg=AggFunction.MAX, alias="mx"),
            AggSpec(column="amount", agg=AggFunction.COUNT_DISTINCT, alias="cd"),
        ]
        exprs = compiler.compile(specs, offer_schema)
        assert len(exprs) == 6

    def test_aggfunction_invalid_string_rejected(self) -> None:
        """AggFunction enum rejects invalid string values via Pydantic."""
        with pytest.raises(ValidationError):
            AggSpec.model_validate({"column": "amount", "agg": "median", "alias": "x"})

    def test_aggregate_request_empty_group_by_rejected(self) -> None:
        """AggregateRequest with empty group_by fails Pydantic min_length=1."""
        with pytest.raises(ValidationError, match="group_by"):
            AggregateRequest.model_validate({
                "group_by": [],
                "aggregations": [{"column": "gid", "agg": "count"}],
            })

    def test_aggregate_request_six_group_by_rejected(self) -> None:
        """AggregateRequest with 6 group_by columns fails Pydantic max_length=5."""
        with pytest.raises(ValidationError, match="group_by"):
            AggregateRequest.model_validate({
                "group_by": ["a", "b", "c", "d", "e", "f"],
                "aggregations": [{"column": "gid", "agg": "count"}],
            })

    def test_aggregate_request_empty_aggregations_rejected(self) -> None:
        """AggregateRequest with empty aggregations fails Pydantic min_length=1."""
        with pytest.raises(ValidationError, match="aggregations"):
            AggregateRequest.model_validate({
                "group_by": ["vertical"],
                "aggregations": [],
            })

    def test_aggregate_request_eleven_aggregations_rejected(self) -> None:
        """AggregateRequest with 11 aggregations fails Pydantic max_length=10."""
        aggs = [{"column": "gid", "agg": "count", "alias": f"a{i}"} for i in range(11)]
        with pytest.raises(ValidationError, match="aggregations"):
            AggregateRequest.model_validate({
                "group_by": ["vertical"],
                "aggregations": aggs,
            })

    def test_aggregate_request_extra_field_rejected(self) -> None:
        """AggregateRequest with extra fields rejected by extra='forbid'."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate({
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count"}],
                "surprise": True,
            })

    def test_aggspec_extra_field_rejected(self) -> None:
        """AggSpec with extra fields rejected by extra='forbid'."""
        with pytest.raises(ValidationError):
            AggSpec.model_validate({
                "column": "gid",
                "agg": "count",
                "alias": "x",
                "extra_param": 42,
            })


# ===========================================================================
# 2. GROUP BY Edge Cases
# ===========================================================================


class TestGroupByEdgeCases:
    """Adversarial tests for GROUP BY validation and execution."""

    def test_group_by_list_column_rejected(self, offer_schema: DataFrameSchema) -> None:
        """GROUP BY on a List[Utf8] column raises AggregationError."""
        limits = QueryLimits()
        with pytest.raises(AggregationError, match="List"):
            limits.check_group_by(["platforms"], offer_schema)

    def test_group_by_nonexistent_column_rejected(self, offer_schema: DataFrameSchema) -> None:
        """GROUP BY on column not in schema raises UnknownFieldError."""
        limits = QueryLimits()
        with pytest.raises(UnknownFieldError) as exc_info:
            limits.check_group_by(["does_not_exist"], offer_schema)
        assert exc_info.value.field == "does_not_exist"

    def test_group_by_exceeds_max_columns(self, offer_schema: DataFrameSchema) -> None:
        """GROUP BY with columns exceeding max_group_by_columns raises AggregationError."""
        limits = QueryLimits(max_group_by_columns=2)
        with pytest.raises(AggregationError, match="Too many group_by"):
            limits.check_group_by(["gid", "name", "vertical"], offer_schema)

    @pytest.mark.asyncio
    async def test_group_by_all_null_values_produces_single_null_group(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """GROUP BY on column where all values are null produces a single null group."""
        df = pl.DataFrame({
            "gid": ["1", "2", "3"],
            "name": [None, None, None],
            "vertical": [None, None, None],
            "section": ["A", "B", "C"],
            "mrr": ["100", "200", "300"],
            "cost": ["10", "20", "30"],
            "amount": [1.0, 2.0, 3.0],
            "quantity": [1, 2, 3],
            "is_active": [True, False, True],
            "created_date": [None, None, None],
            "platforms": [["fb"], ["g"], ["fb"]],
        })
        engine = _make_engine(df)

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
        })
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer", project_gid="proj-1",
                client=mock_client, request=request,
            )

        # All nulls -> single group with null key
        assert result.meta.group_count == 1
        assert result.data[0]["vertical"] is None
        assert result.data[0]["cnt"] == 3

    @pytest.mark.asyncio
    async def test_group_by_single_unique_value_produces_single_group(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """GROUP BY on column with single unique value produces one group."""
        df = pl.DataFrame({
            "gid": ["1", "2", "3"],
            "name": ["A", "B", "C"],
            "vertical": ["dental", "dental", "dental"],
            "section": ["A", "B", "C"],
            "mrr": ["100", "200", "300"],
            "cost": ["10", "20", "30"],
            "amount": [1.0, 2.0, 3.0],
            "quantity": [1, 2, 3],
            "is_active": [True, False, True],
            "created_date": [None, None, None],
            "platforms": [["fb"], ["g"], ["fb"]],
        })
        engine = _make_engine(df)

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
        })
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer", project_gid="proj-1",
                client=mock_client, request=request,
            )

        assert result.meta.group_count == 1
        assert result.data[0]["vertical"] == "dental"
        assert result.data[0]["cnt"] == 3

    @pytest.mark.asyncio
    async def test_group_by_exceeding_max_aggregate_groups_raises(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """GROUP BY producing groups > max_aggregate_groups triggers AggregateGroupLimitError."""
        # Each row has unique gid, so group_by gid produces N groups
        n = 15
        df = pl.DataFrame({
            "gid": [str(i) for i in range(n)],
            "name": [f"n{i}" for i in range(n)],
            "vertical": [f"v{i}" for i in range(n)],
            "section": ["A"] * n,
            "mrr": ["100"] * n,
            "cost": ["10"] * n,
            "amount": [1.0] * n,
            "quantity": [1] * n,
            "is_active": [True] * n,
            "created_date": [None] * n,
            "platforms": [["fb"]] * n,
        })
        engine = _make_engine(df, max_aggregate_groups=10)

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
        })
        with _patch_schema(offer_schema):
            with pytest.raises(AggregateGroupLimitError) as exc_info:
                await engine.execute_aggregate(
                    entity_type="offer", project_gid="proj-1",
                    client=mock_client, request=request,
                )
            assert exc_info.value.group_count == n
            assert exc_info.value.max_groups == 10


# ===========================================================================
# 3. HAVING Edge Cases
# ===========================================================================


class TestHavingEdgeCases:
    """Adversarial tests for HAVING clause."""

    @pytest.mark.asyncio
    async def test_having_nonexistent_alias_raises(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """HAVING referencing alias not in agg output raises UnknownFieldError."""
        df = pl.DataFrame({
            "gid": ["1", "2"],
            "name": ["A", "B"],
            "vertical": ["dental", "medical"],
            "section": ["A", "B"],
            "mrr": ["100", "200"],
            "cost": ["10", "20"],
            "amount": [1.0, 2.0],
            "quantity": [1, 2],
            "is_active": [True, False],
            "created_date": [None, None],
            "platforms": [["fb"], ["g"]],
        })
        engine = _make_engine(df)

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            "having": {"field": "nonexistent_alias", "op": "gt", "value": 0},
        })
        with _patch_schema(offer_schema):
            with pytest.raises(UnknownFieldError) as exc_info:
                await engine.execute_aggregate(
                    entity_type="offer", project_gid="proj-1",
                    client=mock_client, request=request,
                )
            assert exc_info.value.field == "nonexistent_alias"

    @pytest.mark.asyncio
    async def test_having_complex_nested_predicates(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """HAVING with AND/OR nested predicates works correctly."""
        df = pl.DataFrame({
            "gid": ["1", "2", "3", "4", "5", "6"],
            "name": ["A", "B", "C", "D", "E", "F"],
            "vertical": ["dental", "dental", "medical", "medical", "vet", "vet"],
            "section": ["A"] * 6,
            "mrr": ["100"] * 6,
            "cost": ["10"] * 6,
            "amount": [100.0, 200.0, 50.0, 60.0, 1000.0, 2000.0],
            "quantity": [1, 2, 3, 4, 5, 6],
            "is_active": [True] * 6,
            "created_date": [None] * 6,
            "platforms": [["fb"]] * 6,
        })
        engine = _make_engine(df)

        # HAVING: (total > 200 AND cnt >= 2) OR vertical = "vet"
        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [
                {"column": "amount", "agg": "sum", "alias": "total"},
                {"column": "gid", "agg": "count", "alias": "cnt"},
            ],
            "having": {
                "or": [
                    {
                        "and": [
                            {"field": "total", "op": "gt", "value": 200.0},
                            {"field": "cnt", "op": "gte", "value": 2},
                        ]
                    },
                    {"field": "vertical", "op": "eq", "value": "vet"},
                ]
            },
        })
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer", project_gid="proj-1",
                client=mock_client, request=request,
            )

        verts = {d["vertical"] for d in result.data}
        # dental: total=300, cnt=2 -> passes AND
        # medical: total=110, cnt=2 -> fails total > 200
        # vet: total=3000, cnt=2 -> passes both branches
        assert "dental" in verts
        assert "vet" in verts
        assert "medical" not in verts

    @pytest.mark.asyncio
    async def test_having_filters_all_groups_returns_empty(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """HAVING that filters out ALL groups returns empty data."""
        df = pl.DataFrame({
            "gid": ["1", "2"],
            "name": ["A", "B"],
            "vertical": ["dental", "medical"],
            "section": ["A", "B"],
            "mrr": ["100", "200"],
            "cost": ["10", "20"],
            "amount": [1.0, 2.0],
            "quantity": [1, 2],
            "is_active": [True, False],
            "created_date": [None, None],
            "platforms": [["fb"], ["g"]],
        })
        engine = _make_engine(df)

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            "having": {"field": "cnt", "op": "gt", "value": 999999},
        })
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer", project_gid="proj-1",
                client=mock_client, request=request,
            )

        assert result.data == []
        assert result.meta.group_count == 0

    @pytest.mark.asyncio
    async def test_having_on_group_by_column_works(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """HAVING on a group_by column (not an aggregation alias) works."""
        df = pl.DataFrame({
            "gid": ["1", "2", "3"],
            "name": ["A", "B", "C"],
            "vertical": ["dental", "dental", "medical"],
            "section": ["A", "B", "C"],
            "mrr": ["100", "200", "300"],
            "cost": ["10", "20", "30"],
            "amount": [1.0, 2.0, 3.0],
            "quantity": [1, 2, 3],
            "is_active": [True, False, True],
            "created_date": [None, None, None],
            "platforms": [["fb"], ["g"], ["fb"]],
        })
        engine = _make_engine(df)

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            "having": {"field": "vertical", "op": "eq", "value": "dental"},
        })
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer", project_gid="proj-1",
                client=mock_client, request=request,
            )

        assert result.meta.group_count == 1
        assert result.data[0]["vertical"] == "dental"
        assert result.data[0]["cnt"] == 2

    @pytest.mark.asyncio
    async def test_having_numeric_comparison_on_count(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """HAVING with numeric comparison on count result works."""
        df = pl.DataFrame({
            "gid": ["1", "2", "3", "4", "5"],
            "name": ["A", "B", "C", "D", "E"],
            "vertical": ["dental", "dental", "dental", "medical", "medical"],
            "section": ["A"] * 5,
            "mrr": ["100"] * 5,
            "cost": ["10"] * 5,
            "amount": [1.0] * 5,
            "quantity": [1] * 5,
            "is_active": [True] * 5,
            "created_date": [None] * 5,
            "platforms": [["fb"]] * 5,
        })
        engine = _make_engine(df)

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            "having": {"field": "cnt", "op": "gte", "value": 3},
        })
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer", project_gid="proj-1",
                client=mock_client, request=request,
            )

        # dental=3, medical=2 -> only dental passes cnt >= 3
        assert result.meta.group_count == 1
        assert result.data[0]["vertical"] == "dental"

    def test_having_flat_array_sugar_wraps_to_and(self) -> None:
        """HAVING provided as flat array is auto-wrapped to AND group."""
        req = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            "having": [
                {"field": "cnt", "op": "gt", "value": 1},
                {"field": "cnt", "op": "lt", "value": 100},
            ],
        })
        # Should parse without error; having is an AndGroup
        assert req.having is not None

    def test_having_empty_array_becomes_none(self) -> None:
        """HAVING provided as empty array becomes None."""
        req = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            "having": [],
        })
        assert req.having is None

    @pytest.mark.asyncio
    async def test_having_depth_guard(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """HAVING predicate exceeding max depth raises QueryTooComplexError."""
        df = pl.DataFrame({
            "gid": ["1"],
            "name": ["A"],
            "vertical": ["dental"],
            "section": ["A"],
            "mrr": ["100"],
            "cost": ["10"],
            "amount": [1.0],
            "quantity": [1],
            "is_active": [True],
            "created_date": [None],
            "platforms": [["fb"]],
        })
        engine = _make_engine(df)

        leaf = {"field": "cnt", "op": "gt", "value": 1}
        deep = {"and": [{"or": [{"and": [{"not": {"and": [leaf]}}]}]}]}  # depth=6

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            "having": deep,
        })
        with _patch_schema(offer_schema):
            with pytest.raises(QueryTooComplexError):
                await engine.execute_aggregate(
                    entity_type="offer", project_gid="proj-1",
                    client=mock_client, request=request,
                )


# ===========================================================================
# 4. Aggregation Compilation Edge Cases
# ===========================================================================


class TestAggregationCompilationEdgeCases:
    """Adversarial tests for AggregationCompiler edge cases."""

    def test_sum_on_boolean_rejected(self, offer_schema: DataFrameSchema) -> None:
        """sum on Boolean column raises AggregationError."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="is_active", agg=AggFunction.SUM)
        with pytest.raises(AggregationError, match="Boolean"):
            compiler.compile([spec], offer_schema)

    def test_mean_on_boolean_rejected(self, offer_schema: DataFrameSchema) -> None:
        """mean on Boolean column raises AggregationError."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="is_active", agg=AggFunction.MEAN)
        with pytest.raises(AggregationError, match="Boolean"):
            compiler.compile([spec], offer_schema)

    def test_sum_on_date_rejected(self, offer_schema: DataFrameSchema) -> None:
        """sum on Date column raises AggregationError."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="created_date", agg=AggFunction.SUM)
        with pytest.raises(AggregationError, match="Date"):
            compiler.compile([spec], offer_schema)

    def test_mean_on_date_rejected(self, offer_schema: DataFrameSchema) -> None:
        """mean on Date column raises AggregationError."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="created_date", agg=AggFunction.MEAN)
        with pytest.raises(AggregationError, match="Date"):
            compiler.compile([spec], offer_schema)

    def test_any_agg_on_list_utf8_rejected(self, offer_schema: DataFrameSchema) -> None:
        """All aggregation functions on List[Utf8] column are rejected."""
        compiler = AggregationCompiler()
        for func in AggFunction:
            spec = AggSpec(column="platforms", agg=func, alias=f"test_{func.value}")
            with pytest.raises(AggregationError):
                compiler.compile([spec], offer_schema)

    def test_sum_utf8_all_nulls_returns_zero(self, offer_schema: DataFrameSchema) -> None:
        """sum on Utf8 column where all values are null returns 0.0."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total_mrr")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame({
            "vertical": ["dental", "dental"],
            "mrr": [None, None],
        })
        result = df.group_by("vertical").agg(exprs)
        # Polars sum of nulls after cast = 0.0
        assert result["total_mrr"].to_list() == [0.0]

    def test_count_all_nulls_returns_zero(self, offer_schema: DataFrameSchema) -> None:
        """count on column with all null values returns 0."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.COUNT, alias="cnt")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame({
            "vertical": ["dental", "dental"],
            "mrr": [None, None],
        })
        result = df.group_by("vertical").agg(exprs)
        assert result["cnt"].to_list() == [0]

    def test_count_distinct_with_nulls(self, offer_schema: DataFrameSchema) -> None:
        """count_distinct on column with nulls: Polars n_unique counts null as a distinct value."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.COUNT_DISTINCT, alias="uniq")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame({
            "vertical": ["dental", "dental", "dental"],
            "mrr": ["100", "100", None],
        })
        result = df.group_by("vertical").agg(exprs)
        # "100" and null = 2 distinct values
        assert result["uniq"].to_list() == [2]

    def test_mean_on_empty_df(self, offer_schema: DataFrameSchema) -> None:
        """mean on empty DataFrame produces empty result, not an error."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="amount", agg=AggFunction.MEAN, alias="avg")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame({
            "vertical": pl.Series([], dtype=pl.Utf8),
            "amount": pl.Series([], dtype=pl.Float64),
        })
        result = df.group_by("vertical").agg(exprs)
        assert len(result) == 0

    def test_empty_string_column_not_in_schema(self, offer_schema: DataFrameSchema) -> None:
        """AggSpec with empty string column name fails at compile time."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="", agg=AggFunction.SUM, alias="total")
        with pytest.raises(AggregationError, match="Unknown column"):
            compiler.compile([spec], offer_schema)


# ===========================================================================
# 5. Engine Integration Adversarial
# ===========================================================================


class TestEngineIntegrationAdversarial:
    """Adversarial tests for QueryEngine.execute_aggregate()."""

    @pytest.mark.asyncio
    async def test_full_pipeline_where_section_having(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """Full pipeline: WHERE + section + GROUP BY + HAVING."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-123"})

        df = pl.DataFrame({
            "gid": ["1", "2", "3", "4", "5"],
            "name": ["A", "B", "C", "D", "E"],
            "vertical": ["dental", "dental", "medical", "medical", "dental"],
            "section": ["Active", "Active", "Active", "Won", "Active"],
            "mrr": ["100", "200", "300", "400", "500"],
            "cost": ["10", "20", "30", "40", "50"],
            "amount": [100.0, 200.0, 300.0, 400.0, 500.0],
            "quantity": [1, 2, 3, 4, 5],
            "is_active": [True, True, False, True, True],
            "created_date": [None] * 5,
            "platforms": [["fb"]] * 5,
        })
        engine = _make_engine(df)

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [
                {"column": "amount", "agg": "sum", "alias": "total"},
            ],
            "section": "Active",
            "where": {"field": "is_active", "op": "eq", "value": True},
            "having": {"field": "total", "op": "gte", "value": 500.0},
        })
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer", project_gid="proj-1",
                client=mock_client, request=request,
                section_index=section_index,
            )

        # Active section: gid 1,2,3,5
        # WHERE is_active=True: gid 1,2,5 (dental: 100+200+500=800)
        # medical gid 3 has is_active=False so excluded
        # HAVING total >= 500: dental=800 passes
        assert result.meta.group_count == 1
        assert result.data[0]["vertical"] == "dental"
        assert result.data[0]["total"] == 800.0

    @pytest.mark.asyncio
    async def test_where_depth_guard(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """WHERE predicate exceeding max depth raises QueryTooComplexError."""
        df = pl.DataFrame({
            "gid": ["1"],
            "name": ["A"],
            "vertical": ["dental"],
            "section": ["A"],
            "mrr": ["100"],
            "cost": ["10"],
            "amount": [1.0],
            "quantity": [1],
            "is_active": [True],
            "created_date": [None],
            "platforms": [["fb"]],
        })
        engine = _make_engine(df)

        leaf = {"field": "name", "op": "eq", "value": "x"}
        deep = {"and": [{"or": [{"and": [{"not": {"and": [leaf]}}]}]}]}  # depth=6

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            "where": deep,
        })
        with _patch_schema(offer_schema):
            with pytest.raises(QueryTooComplexError):
                await engine.execute_aggregate(
                    entity_type="offer", project_gid="proj-1",
                    client=mock_client, request=request,
                )

    @pytest.mark.asyncio
    async def test_alias_collision_at_engine_level(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """Duplicate aliases detected at engine level before compilation."""
        df = pl.DataFrame({
            "gid": ["1"],
            "name": ["A"],
            "vertical": ["dental"],
            "section": ["A"],
            "mrr": ["100"],
            "cost": ["10"],
            "amount": [1.0],
            "quantity": [1],
            "is_active": [True],
            "created_date": [None],
            "platforms": [["fb"]],
        })
        engine = _make_engine(df)

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [
                {"column": "amount", "agg": "sum", "alias": "total"},
                {"column": "quantity", "agg": "sum", "alias": "total"},
            ],
        })
        with _patch_schema(offer_schema):
            with pytest.raises(AggregationError, match="Duplicate alias"):
                await engine.execute_aggregate(
                    entity_type="offer", project_gid="proj-1",
                    client=mock_client, request=request,
                )

    @pytest.mark.asyncio
    async def test_alias_collides_with_group_by_column_at_engine(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """Alias colliding with group_by column detected at engine level."""
        df = pl.DataFrame({
            "gid": ["1"],
            "name": ["A"],
            "vertical": ["dental"],
            "section": ["A"],
            "mrr": ["100"],
            "cost": ["10"],
            "amount": [1.0],
            "quantity": [1],
            "is_active": [True],
            "created_date": [None],
            "platforms": [["fb"]],
        })
        engine = _make_engine(df)

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [
                {"column": "amount", "agg": "sum", "alias": "vertical"},
            ],
        })
        with _patch_schema(offer_schema):
            with pytest.raises(AggregationError, match="collides with group_by"):
                await engine.execute_aggregate(
                    entity_type="offer", project_gid="proj-1",
                    client=mock_client, request=request,
                )

    @pytest.mark.asyncio
    async def test_response_format_data_is_list_of_dicts(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """Response data is a list of dicts with correct keys."""
        df = pl.DataFrame({
            "gid": ["1", "2", "3"],
            "name": ["A", "B", "C"],
            "vertical": ["dental", "dental", "medical"],
            "section": ["A", "B", "C"],
            "mrr": ["100", "200", "300"],
            "cost": ["10", "20", "30"],
            "amount": [1.0, 2.0, 3.0],
            "quantity": [1, 2, 3],
            "is_active": [True, False, True],
            "created_date": [None, None, None],
            "platforms": [["fb"], ["g"], ["fb"]],
        })
        engine = _make_engine(df)

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [
                {"column": "amount", "agg": "sum", "alias": "total"},
                {"column": "gid", "agg": "count", "alias": "cnt"},
            ],
        })
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer", project_gid="proj-1",
                client=mock_client, request=request,
            )

        assert isinstance(result.data, list)
        for row in result.data:
            assert isinstance(row, dict)
            assert "vertical" in row
            assert "total" in row
            assert "cnt" in row

        assert result.meta.group_count == len(result.data)
        assert result.meta.aggregation_count == 2

    @pytest.mark.asyncio
    async def test_meta_has_group_count(
        self, mock_client: AsyncMock, offer_schema: DataFrameSchema,
    ) -> None:
        """AggregateMeta includes group_count matching actual data length."""
        df = pl.DataFrame({
            "gid": ["1", "2"],
            "name": ["A", "B"],
            "vertical": ["dental", "medical"],
            "section": ["A", "B"],
            "mrr": ["100", "200"],
            "cost": ["10", "20"],
            "amount": [1.0, 2.0],
            "quantity": [1, 2],
            "is_active": [True, False],
            "created_date": [None, None],
            "platforms": [["fb"], ["g"]],
        })
        engine = _make_engine(df)

        request = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
        })
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer", project_gid="proj-1",
                client=mock_client, request=request,
            )

        assert result.meta.group_count == 2
        assert result.meta.group_count == len(result.data)
        assert result.meta.query_ms >= 0
        assert result.meta.entity_type == "offer"
        assert result.meta.project_gid == "proj-1"


# ===========================================================================
# 6. API Endpoint Edge Cases (via model validation, no TestClient needed)
# ===========================================================================


class TestAPIEndpointEdgeCases:
    """Adversarial tests for the aggregate API request validation layer."""

    def test_empty_body_rejected(self) -> None:
        """POST /aggregate with empty body fails Pydantic validation (missing required fields)."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate({})

    def test_valid_entity_type_invalid_aggregations(self) -> None:
        """Valid entity_type but invalid agg function rejected."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate({
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "INVALID_FUNC"}],
            })

    def test_where_flat_array_sugar(self) -> None:
        """WHERE provided as flat array is auto-wrapped to AND group."""
        req = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count"}],
            "where": [
                {"field": "name", "op": "eq", "value": "test"},
            ],
        })
        assert req.where is not None

    def test_where_empty_array_becomes_none(self) -> None:
        """WHERE provided as empty array becomes None."""
        req = AggregateRequest.model_validate({
            "group_by": ["vertical"],
            "aggregations": [{"column": "gid", "agg": "count"}],
            "where": [],
        })
        assert req.where is None

    def test_aggregate_request_missing_group_by(self) -> None:
        """Missing group_by field rejected."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate({
                "aggregations": [{"column": "gid", "agg": "count"}],
            })

    def test_aggregate_request_missing_aggregations(self) -> None:
        """Missing aggregations field rejected."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate({
                "group_by": ["vertical"],
            })


# ===========================================================================
# 7. Numeric Casting Adversarial (ADR-AGG-005)
# ===========================================================================


class TestNumericCastingAdversarial:
    """Adversarial tests for Utf8 -> Float64 casting in aggregation."""

    def test_utf8_mix_numeric_and_nonnumeric(self, offer_schema: DataFrameSchema) -> None:
        """Utf8 column with mix of numeric and non-numeric strings:
        non-numeric become null, sum ignores nulls."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame({
            "vertical": ["dental", "dental", "dental"],
            "mrr": ["100.5", "not_a_number", "200.5"],
        })
        result = df.group_by("vertical").agg(exprs)
        # "not_a_number" -> null via strict=False, sum ignores null
        assert result["total"].to_list() == [pytest.approx(301.0)]

    def test_utf8_all_nonnumeric_strings(self, offer_schema: DataFrameSchema) -> None:
        """Utf8 column with ALL non-numeric strings: sum produces 0.0."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame({
            "vertical": ["dental", "dental"],
            "mrr": ["abc", "def"],
        })
        result = df.group_by("vertical").agg(exprs)
        # All cast to null, sum of nulls = 0.0
        assert result["total"].to_list() == [0.0]

    def test_utf8_empty_strings_become_null(self, offer_schema: DataFrameSchema) -> None:
        """Utf8 column with empty strings: empty strings become null after cast."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame({
            "vertical": ["dental", "dental", "dental"],
            "mrr": ["", "100", ""],
        })
        result = df.group_by("vertical").agg(exprs)
        # "" -> null via Float64 cast, sum = 100.0
        assert result["total"].to_list() == [100.0]

    def test_utf8_mean_with_nonnumeric(self, offer_schema: DataFrameSchema) -> None:
        """mean on Utf8 column with non-numeric strings: nulls ignored in mean."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.MEAN, alias="avg")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame({
            "vertical": ["dental", "dental", "dental"],
            "mrr": ["100", "bad", "200"],
        })
        result = df.group_by("vertical").agg(exprs)
        # mean of [100.0, null, 200.0] = 150.0 (null excluded)
        assert result["avg"].to_list() == [150.0]

    def test_utf8_min_max_with_nonnumeric(self, offer_schema: DataFrameSchema) -> None:
        """min/max on Utf8 column with non-numeric strings: nulls ignored."""
        compiler = AggregationCompiler()
        spec_min = AggSpec(column="mrr", agg=AggFunction.MIN, alias="min_mrr")
        spec_max = AggSpec(column="mrr", agg=AggFunction.MAX, alias="max_mrr")
        exprs = compiler.compile([spec_min, spec_max], offer_schema)

        df = pl.DataFrame({
            "vertical": ["dental", "dental", "dental"],
            "mrr": ["100", "bad", "300"],
        })
        result = df.group_by("vertical").agg(exprs)
        assert result["min_mrr"].to_list() == [100.0]
        assert result["max_mrr"].to_list() == [300.0]

    def test_utf8_count_does_not_cast(self, offer_schema: DataFrameSchema) -> None:
        """count on Utf8 column does NOT cast -- counts all non-null values including non-numeric."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.COUNT, alias="cnt")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame({
            "vertical": ["dental", "dental", "dental"],
            "mrr": ["100", "bad", None],
        })
        result = df.group_by("vertical").agg(exprs)
        # count counts non-null: "100" and "bad" are non-null, None is excluded
        assert result["cnt"].to_list() == [2]

    def test_utf8_count_distinct_does_not_cast(self, offer_schema: DataFrameSchema) -> None:
        """count_distinct on Utf8 column does NOT cast -- counts unique string values."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.COUNT_DISTINCT, alias="uniq")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame({
            "vertical": ["dental", "dental", "dental", "dental"],
            "mrr": ["100", "100", "bad", None],
        })
        result = df.group_by("vertical").agg(exprs)
        # "100", "bad", null = 3 distinct
        assert result["uniq"].to_list() == [3]

    def test_utf8_sum_preserves_decimal_precision(self, offer_schema: DataFrameSchema) -> None:
        """Utf8 sum preserves decimal precision within Float64 limits."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame({
            "vertical": ["dental", "dental"],
            "mrr": ["0.1", "0.2"],
        })
        result = df.group_by("vertical").agg(exprs)
        # Float64 addition: 0.1 + 0.2 ~ 0.3 (within floating point tolerance)
        assert result["total"].to_list() == [pytest.approx(0.3)]


# ===========================================================================
# 8. Error Serialization
# ===========================================================================


class TestErrorSerialization:
    """Verify error classes serialize to expected JSON shapes."""

    def test_aggregation_error_to_dict(self) -> None:
        """AggregationError serializes with correct error code."""
        err = AggregationError(message="test error")
        d = err.to_dict()
        assert d["error"] == "AGGREGATION_ERROR"
        assert d["message"] == "test error"

    def test_aggregate_group_limit_error_to_dict(self) -> None:
        """AggregateGroupLimitError serializes with group_count and max_groups."""
        err = AggregateGroupLimitError(group_count=20000, max_groups=10000)
        d = err.to_dict()
        assert d["error"] == "TOO_MANY_GROUPS"
        assert d["group_count"] == 20000
        assert d["max_groups"] == 10000
        assert "20000" in d["message"]
        assert "10000" in d["message"]

    def test_aggregation_error_is_query_engine_error(self) -> None:
        """AggregationError is a subclass of QueryEngineError."""
        from autom8_asana.query.errors import QueryEngineError

        err = AggregationError(message="test")
        assert isinstance(err, QueryEngineError)

    def test_aggregate_group_limit_error_is_query_engine_error(self) -> None:
        """AggregateGroupLimitError is a subclass of QueryEngineError."""
        from autom8_asana.query.errors import QueryEngineError

        err = AggregateGroupLimitError(group_count=1, max_groups=1)
        assert isinstance(err, QueryEngineError)


# ===========================================================================
# 9. Post-Aggregation Schema Adversarial
# ===========================================================================


class TestPostAggSchemaAdversarial:
    """Adversarial tests for build_post_agg_schema edge cases."""

    def test_schema_includes_all_group_by_and_agg_columns(
        self, offer_schema: DataFrameSchema,
    ) -> None:
        """Post-agg schema includes both group_by columns and all agg aliases."""
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM, alias="total"),
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="cnt"),
            AggSpec(column="amount", agg=AggFunction.MEAN, alias="avg"),
        ]
        schema = build_post_agg_schema(
            group_by_columns=["vertical", "section"],
            agg_specs=specs,
            source_schema=offer_schema,
        )
        col_names = schema.column_names()
        assert "vertical" in col_names
        assert "section" in col_names
        assert "total" in col_names
        assert "cnt" in col_names
        assert "avg" in col_names

    def test_post_agg_schema_sum_int64_infers_int64(
        self, offer_schema: DataFrameSchema,
    ) -> None:
        """sum on Int64 column infers Int64 output (not Float64)."""
        spec = AggSpec(column="quantity", agg=AggFunction.SUM, alias="total_qty")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=offer_schema,
        )
        col = schema.get_column("total_qty")
        assert col is not None
        assert col.dtype == "Int64"

    def test_post_agg_schema_sum_utf8_infers_float64(
        self, offer_schema: DataFrameSchema,
    ) -> None:
        """sum on Utf8 column (financial) infers Float64 output."""
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total_mrr")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=offer_schema,
        )
        col = schema.get_column("total_mrr")
        assert col is not None
        assert col.dtype == "Float64"

    def test_post_agg_schema_min_date_retains_date(
        self, offer_schema: DataFrameSchema,
    ) -> None:
        """min on Date column retains Date output dtype."""
        spec = AggSpec(column="created_date", agg=AggFunction.MIN, alias="earliest")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=offer_schema,
        )
        col = schema.get_column("earliest")
        assert col is not None
        assert col.dtype == "Date"

    def test_post_agg_schema_all_agg_columns_are_nullable(
        self, offer_schema: DataFrameSchema,
    ) -> None:
        """All aggregation output columns in post-agg schema are nullable."""
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM, alias="total"),
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="cnt"),
        ]
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=specs,
            source_schema=offer_schema,
        )
        for spec in specs:
            col = schema.get_column(spec.resolved_alias)
            assert col is not None
            assert col.nullable is True
