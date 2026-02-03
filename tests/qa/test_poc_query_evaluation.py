"""POC Query Evaluation: Comprehensive adversarial validation of Dynamic Query Service.

This test suite exercises the full surface area of the query engine, compiler,
aggregator, guards, hierarchy, and join modules. Tests are organized by
business scenario categories and designed to break things, not just confirm
happy paths.

QA Adversary: Validates PRD-dynamic-query-service acceptance criteria.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.query.aggregator import (
    AGG_COMPATIBILITY,
    AggregationCompiler,
    build_post_agg_schema,
    validate_alias_uniqueness,
)
from autom8_asana.query.compiler import (
    OPERATOR_MATRIX,
    PredicateCompiler,
    strip_section_predicates,
)
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import (
    AggregateGroupLimitError,
    AggregationError,
    CoercionError,
    InvalidOperatorError,
    JoinError,
    QueryTooComplexError,
    UnknownFieldError,
    UnknownSectionError,
)
from autom8_asana.query.guards import QueryLimits, predicate_depth
from autom8_asana.query.hierarchy import (
    ENTITY_RELATIONSHIPS,
    find_relationship,
    get_join_key,
    get_joinable_types,
)
from autom8_asana.query.join import JoinSpec, execute_join
from autom8_asana.query.models import (
    AggFunction,
    AggregateRequest,
    AggregateMeta,
    AggregateResponse,
    AggSpec,
    AndGroup,
    Comparison,
    NotGroup,
    Op,
    OrGroup,
    RowsMeta,
    RowsRequest,
    RowsResponse,
)
from autom8_asana.services.query_service import EntityQueryService


# ============================================================================
# Shared Fixtures: realistic DataFrames mirroring actual entity schemas
# ============================================================================


@pytest.fixture
def offer_schema() -> DataFrameSchema:
    """Realistic offer schema matching production columns."""
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("type", "Utf8", nullable=False),
            ColumnDef("date", "Date", nullable=True),
            ColumnDef("created", "Datetime", nullable=False),
            ColumnDef("is_completed", "Boolean", nullable=False),
            ColumnDef("section", "Utf8", nullable=True),
            ColumnDef("tags", "List[Utf8]", nullable=False),
            ColumnDef("office_phone", "Utf8", nullable=True),
            ColumnDef("vertical", "Utf8", nullable=True),
            ColumnDef("mrr", "Utf8", nullable=True),
            ColumnDef("cost", "Utf8", nullable=True),
            ColumnDef("weekly_ad_spend", "Utf8", nullable=True),
            ColumnDef("language", "Utf8", nullable=True),
            ColumnDef("platforms", "List[Utf8]", nullable=True),
            ColumnDef("offer_id", "Utf8", nullable=True),
        ],
    )


@pytest.fixture
def business_schema() -> DataFrameSchema:
    """Realistic business schema matching production columns."""
    return DataFrameSchema(
        name="business",
        task_type="Business",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("type", "Utf8", nullable=False),
            ColumnDef("section", "Utf8", nullable=True),
            ColumnDef("tags", "List[Utf8]", nullable=False),
            ColumnDef("office_phone", "Utf8", nullable=True),
            ColumnDef("booking_type", "Utf8", nullable=True),
            ColumnDef("stripe_id", "Utf8", nullable=True),
            ColumnDef("company_id", "Utf8", nullable=True),
        ],
    )


@pytest.fixture
def offer_df() -> pl.DataFrame:
    """Realistic offer DataFrame with diverse data for BI queries."""
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    return pl.DataFrame(
        {
            "gid": [f"o{i}" for i in range(1, 11)],
            "name": [
                "Acme Dental SEO",
                "Beta Medical PPC",
                "Gamma Dental Social",
                "Delta Medical SEO",
                "Echo Dental PPC",
                "Foxtrot Ortho Social",
                "Golf Medical SEO",
                "Hotel Dental PPC",
                "India Ortho SEO",
                "Juliet Medical Social",
            ],
            "type": ["Offer"] * 10,
            "date": [date(2026, 1, i) for i in range(1, 11)],
            "created": [now] * 10,
            "is_completed": [
                False,
                False,
                True,
                False,
                False,
                True,
                False,
                False,
                True,
                False,
            ],
            "section": [
                "Active",
                "Active",
                "Won",
                "Active",
                "Active",
                "Lost",
                "Active",
                "Won",
                "Lost",
                "Active",
            ],
            "tags": [
                ["seo"],
                ["ppc"],
                ["social"],
                ["seo"],
                ["ppc"],
                ["social"],
                ["seo"],
                ["ppc"],
                ["seo"],
                ["social"],
            ],
            "office_phone": [
                "+1111",
                "+2222",
                "+1111",
                "+3333",
                "+2222",
                "+4444",
                "+3333",
                "+1111",
                "+4444",
                "+5555",
            ],
            "vertical": [
                "dental",
                "medical",
                "dental",
                "medical",
                "dental",
                "ortho",
                "medical",
                "dental",
                "ortho",
                "medical",
            ],
            "mrr": [
                "500",
                "1200",
                "300",
                "800",
                "600",
                "150",
                "900",
                "750",
                "200",
                "1100",
            ],
            "cost": [
                "50",
                "120",
                "30",
                "80",
                "60",
                "15",
                "90",
                "75",
                "20",
                "110",
            ],
            "weekly_ad_spend": [
                "100",
                "250",
                "75",
                "200",
                "150",
                "50",
                "180",
                "120",
                "40",
                "220",
            ],
            "language": [
                "en",
                "es",
                "en",
                "en",
                "es",
                "en",
                "es",
                "en",
                "en",
                "es",
            ],
            "platforms": [
                ["facebook"],
                ["google"],
                ["facebook", "instagram"],
                ["google"],
                ["facebook"],
                ["instagram"],
                ["google", "facebook"],
                ["facebook"],
                ["google"],
                ["instagram", "facebook"],
            ],
            "offer_id": [f"OFF-{i:03d}" for i in range(1, 11)],
        }
    )


@pytest.fixture
def business_df() -> pl.DataFrame:
    """Realistic business DataFrame for join tests."""
    return pl.DataFrame(
        {
            "gid": ["b1", "b2", "b3", "b4", "b5"],
            "name": ["Acme Corp", "Beta Inc", "Gamma LLC", "Delta Ltd", "Echo Co"],
            "type": ["business"] * 5,
            "section": ["Active", "Active", "Won", "Active", "Lost"],
            "tags": [["premium"], ["standard"], ["premium"], ["standard"], ["trial"]],
            "office_phone": ["+1111", "+2222", "+3333", "+4444", "+5555"],
            "booking_type": ["Online", "Phone", "Online", "Phone", "Online"],
            "stripe_id": ["str_1", "str_2", "str_3", None, "str_5"],
            "company_id": ["CMP-1", "CMP-2", "CMP-3", "CMP-4", "CMP-5"],
        }
    )


@pytest.fixture
def mock_client() -> AsyncMock:
    return AsyncMock()


def _mock_query_service(df: pl.DataFrame) -> EntityQueryService:
    """Create a query service returning the given DataFrame."""
    service = EntityQueryService()
    service.get_dataframe = AsyncMock(return_value=df)
    return service


def _mock_dual_query_service(
    primary_df: pl.DataFrame, target_df: pl.DataFrame
) -> EntityQueryService:
    """Create a query service returning different DFs for primary and target."""
    service = EntityQueryService()
    service.get_dataframe = AsyncMock(side_effect=[primary_df, target_df])
    return service


def _patch_schema_map(schema_map: dict[str, DataFrameSchema]):
    """Context manager to patch SchemaRegistry with a schema lookup map."""
    return patch(
        "autom8_asana.query.engine.SchemaRegistry",
        **{
            "get_instance.return_value.get_schema.side_effect": lambda k: schema_map[k],
        },
    )


def _patch_single_schema(schema: DataFrameSchema):
    """Context manager to patch SchemaRegistry with a single schema."""
    return patch(
        "autom8_asana.query.engine.SchemaRegistry",
        **{
            "get_instance.return_value.get_schema.return_value": schema,
        },
    )


# ============================================================================
# CATEGORY 1: Business Intelligence Queries
# ============================================================================


class TestCategory1BusinessIntelligence:
    """Queries a business analyst would actually run against offer data."""

    @pytest.mark.asyncio
    async def test_bi_active_offers_above_mrr_threshold(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """BI: Show me all offers in the Active section with MRR above 500.

        A common business query -- filter to a section, then apply a range condition
        on a financial column. Note that MRR is Utf8 (string-encoded), so the
        compiler must coerce the value to string for comparison. This tests
        whether the predicate engine handles Utf8 ordering correctly.
        """
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate(
            {
                "where": {
                    "and": [
                        {"field": "section", "op": "eq", "value": "Active"},
                        {"field": "mrr", "op": "gt", "value": "500"},
                    ]
                },
                "select": ["name", "mrr", "section", "vertical"],
            }
        )
        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        # Verify only Active rows returned
        for row in result.data:
            assert row["section"] == "Active"
        # All returned MRR values should be > "500" in string comparison
        assert result.meta.total_count > 0

    @pytest.mark.asyncio
    async def test_bi_count_offers_by_vertical(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """BI: Count offers by vertical.

        Fundamental aggregation -- one of the most common reporting queries.
        """
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "gid", "agg": "count", "alias": "offer_count"},
                ],
            }
        )
        with _patch_single_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        data_by_vert = {d["vertical"]: d for d in result.data}
        assert data_by_vert["dental"]["offer_count"] == 4
        assert data_by_vert["medical"]["offer_count"] == 4
        assert data_by_vert["ortho"]["offer_count"] == 2
        assert result.meta.group_count == 3

    @pytest.mark.asyncio
    async def test_bi_average_mrr_by_section(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """BI: Average MRR by section.

        Exercises Utf8 -> Float64 casting for mean aggregation (ADR-AGG-005).
        """
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["section"],
                "aggregations": [
                    {"column": "mrr", "agg": "mean", "alias": "avg_mrr"},
                    {"column": "gid", "agg": "count", "alias": "offer_count"},
                ],
            }
        )
        with _patch_single_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.meta.group_count == 3  # Active, Won, Lost
        for row in result.data:
            assert "avg_mrr" in row
            assert "offer_count" in row
            assert row["avg_mrr"] is not None  # Should have numeric values

    @pytest.mark.asyncio
    async def test_bi_list_businesses_filtered_by_booking_type(
        self,
        business_schema: DataFrameSchema,
        business_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """BI: List businesses filtered by booking_type = 'Online'.

        Simple equality filter on a categorical column.
        """
        engine = QueryEngine(query_service=_mock_query_service(business_df))
        request = RowsRequest.model_validate(
            {
                "where": {"field": "booking_type", "op": "eq", "value": "Online"},
                "select": ["name", "office_phone", "booking_type"],
            }
        )
        with _patch_single_schema(business_schema):
            result = await engine.execute_rows(
                entity_type="business",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.meta.total_count == 3  # Acme, Gamma, Echo
        for row in result.data:
            assert row["booking_type"] == "Online"

    @pytest.mark.asyncio
    async def test_bi_offers_enriched_with_business_booking_type(
        self,
        offer_schema: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        business_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """BI: Show offers enriched with parent business booking_type via join.

        Tests the join enrichment path: offer -> business via office_phone.
        """
        schema_map = {"Offer": offer_schema, "Business": business_schema}
        service = _mock_dual_query_service(offer_df, business_df)
        engine = QueryEngine(query_service=service)
        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj-1"

        request = RowsRequest.model_validate(
            {
                "select": ["name", "mrr", "office_phone"],
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type"],
                },
            }
        )

        with _patch_schema_map(schema_map):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
                entity_project_registry=mock_epr,
            )

        # Verify join enrichment columns are present
        for row in result.data:
            assert "business_booking_type" in row
        # Verify join meta is populated
        assert result.meta.join_entity == "business"
        assert result.meta.join_key == "office_phone"
        assert result.meta.join_matched is not None
        assert result.meta.join_unmatched is not None


# ============================================================================
# CATEGORY 2: Predicate Composition Depth
# ============================================================================


class TestCategory2PredicateComposition:
    """Test the full predicate tree expressiveness at the compiler level."""

    @pytest.fixture
    def compiler(self) -> PredicateCompiler:
        return PredicateCompiler()

    @pytest.fixture
    def simple_schema(self) -> DataFrameSchema:
        """Schema with diverse dtypes for operator testing."""
        return DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
                ColumnDef("count", "Int64", nullable=True),
                ColumnDef("amount", "Float64", nullable=True),
                ColumnDef("is_active", "Boolean", nullable=True),
                ColumnDef("date_field", "Date", nullable=True),
                ColumnDef("created", "Datetime", nullable=True),
                ColumnDef("tags", "List[Utf8]", nullable=True),
            ],
        )

    @pytest.fixture
    def test_df(self) -> pl.DataFrame:
        """DataFrame matching simple_schema for predicate evaluation."""
        return pl.DataFrame(
            {
                "gid": ["1", "2", "3", "4", "5"],
                "name": ["Alpha", "Bravo", "Charlie", "Delta", "Echo"],
                "section": ["Active", "Active", "Won", "Lost", "Active"],
                "count": [10, 20, 30, 40, 50],
                "amount": [1.5, 2.5, 3.5, 4.5, 5.5],
                "is_active": [True, True, False, False, True],
                "date_field": [date(2026, 1, i) for i in range(1, 6)],
                "created": [
                    datetime(2026, 1, i, tzinfo=timezone.utc) for i in range(1, 6)
                ],
                "tags": [["a"], ["b"], ["c"], ["d"], ["e"]],
            }
        )

    def test_simple_eq(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """Simple equality predicate: section = 'Active'."""
        node = Comparison(field="section", op=Op.EQ, value="Active")
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 3

    def test_simple_ne(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """Simple not-equal: section != 'Active'."""
        node = Comparison(field="section", op=Op.NE, value="Active")
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 2

    def test_and_composition(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """AND composition: section = Active AND count > 15."""
        node = AndGroup.model_validate(
            {
                "and": [
                    {"field": "section", "op": "eq", "value": "Active"},
                    {"field": "count", "op": "gt", "value": 15},
                ]
            }
        )
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 2  # rows 2(20) and 5(50)

    def test_or_composition(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """OR composition: section = Won OR section = Lost."""
        node = OrGroup.model_validate(
            {
                "or": [
                    {"field": "section", "op": "eq", "value": "Won"},
                    {"field": "section", "op": "eq", "value": "Lost"},
                ]
            }
        )
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 2

    def test_not_negation(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """NOT negation: NOT section = Active."""
        node = NotGroup.model_validate(
            {"not": {"field": "section", "op": "eq", "value": "Active"}}
        )
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 2  # Won, Lost

    def test_nested_and_containing_or(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """Nested: AND containing OR: (section=Active AND (count>25 OR amount<3))."""
        node = AndGroup.model_validate(
            {
                "and": [
                    {"field": "section", "op": "eq", "value": "Active"},
                    {
                        "or": [
                            {"field": "count", "op": "gt", "value": 25},
                            {"field": "amount", "op": "lt", "value": 3.0},
                        ]
                    },
                ]
            }
        )
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        # Active rows: 1(10,1.5), 2(20,2.5), 5(50,5.5)
        # (count>25 OR amount<3): row 1(amount<3), row 2(amount<3), row 5(count>25)
        # Intersection: rows 1, 2, 5
        assert len(result) == 3

    def test_deep_nesting_3_levels(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """Deep nesting: 3+ levels deep: AND(OR(NOT(eq), eq), eq)."""
        node = AndGroup.model_validate(
            {
                "and": [
                    {
                        "or": [
                            {
                                "not": {
                                    "field": "section",
                                    "op": "eq",
                                    "value": "Active",
                                }
                            },
                            {"field": "count", "op": "eq", "value": 10},
                        ]
                    },
                    {"field": "is_active", "op": "eq", "value": True},
                ]
            }
        )
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        # is_active=True: rows 1, 2, 5
        # (NOT section=Active OR count=10): NOT Active = Won/Lost; count=10 = row 1
        # From is_active=True set: row 1(count=10 passes OR), row 2(Active so NOT fails, count=20 not 10), row 5(same)
        assert len(result) == 1  # Only row 1

    @pytest.mark.parametrize(
        "op,value,expected_count",
        [
            (Op.GT, 25, 2),  # 30, 40, 50 -> but check: gt 25 = 30,40,50 = 3
            (Op.LT, 25, 2),  # 10, 20
            (Op.GTE, 30, 3),  # 30, 40, 50
            (Op.LTE, 20, 2),  # 10, 20
            (Op.EQ, 30, 1),  # 30
            (Op.NE, 30, 4),  # 10, 20, 40, 50
        ],
    )
    def test_numeric_operators_int64(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
        op: Op,
        value: int,
        expected_count: int,
    ) -> None:
        """Parametrized: all orderable operators on Int64 column."""
        node = Comparison(field="count", op=op, value=value)
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        if op == Op.GT and value == 25:
            assert len(result) == 3  # 30, 40, 50
        else:
            assert len(result) == expected_count

    def test_in_operator(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """IN operator: name in ['Alpha', 'Echo']."""
        node = Comparison(field="name", op=Op.IN, value=["Alpha", "Echo"])
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 2

    def test_not_in_operator(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """NOT_IN operator: section not_in ['Won', 'Lost']."""
        node = Comparison(field="section", op=Op.NOT_IN, value=["Won", "Lost"])
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 3  # Active rows

    def test_contains_operator(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """CONTAINS operator: name contains 'lph'."""
        node = Comparison(field="name", op=Op.CONTAINS, value="lph")
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 1
        assert result["name"][0] == "Alpha"

    def test_starts_with_operator(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """STARTS_WITH operator: name starts_with 'Ech'."""
        node = Comparison(field="name", op=Op.STARTS_WITH, value="Ech")
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 1
        assert result["name"][0] == "Echo"

    def test_boolean_eq(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """Boolean equality: is_active = True."""
        node = Comparison(field="is_active", op=Op.EQ, value=True)
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 3

    def test_date_comparison(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """Date comparison: date_field > '2026-01-03'."""
        node = Comparison(field="date_field", op=Op.GT, value="2026-01-03")
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 2  # Jan 4, Jan 5

    def test_datetime_comparison(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """Datetime comparison: created >= '2026-01-03T00:00:00Z'."""
        node = Comparison(field="created", op=Op.GTE, value="2026-01-03T00:00:00Z")
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 3  # Jan 3, 4, 5

    def test_empty_and_group(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """Empty AND group = identity (match all, per EC-005)."""
        node = AndGroup.model_validate({"and": []})
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 5

    def test_empty_or_group(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """Empty OR group = identity(false) (match none)."""
        node = OrGroup.model_validate({"or": []})
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 0

    def test_in_with_null_in_list(
        self,
        compiler: PredicateCompiler,
        simple_schema: DataFrameSchema,
        test_df: pl.DataFrame,
    ) -> None:
        """IN operator with null in list: null is ignored per EC-002."""
        node = Comparison(field="name", op=Op.IN, value=[None, "Alpha"])
        expr = compiler.compile(node, simple_schema)
        result = test_df.filter(expr)
        assert len(result) == 1
        assert result["name"][0] == "Alpha"


# ============================================================================
# CATEGORY 3: Aggregation Completeness
# ============================================================================


class TestCategory3AggregationCompleteness:
    """Exercise every aggregation function and combination."""

    @pytest.fixture
    def agg_schema(self) -> DataFrameSchema:
        return DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("vertical", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
                ColumnDef("amount", "Float64", nullable=True),
                ColumnDef("quantity", "Int64", nullable=True),
                ColumnDef("mrr", "Utf8", nullable=True),
                ColumnDef("date_col", "Date", nullable=True),
                ColumnDef("tags", "List[Utf8]", nullable=True),
            ],
        )

    @pytest.fixture
    def agg_df(self) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "gid": ["1", "2", "3", "4", "5", "6"],
                "name": ["A", "B", "A", "C", "B", "A"],
                "vertical": [
                    "dental",
                    "dental",
                    "medical",
                    "medical",
                    "dental",
                    "medical",
                ],
                "section": ["Active", "Active", "Active", "Won", "Won", "Won"],
                "amount": [100.0, 200.0, 300.0, 150.0, 250.0, None],
                "quantity": [10, 20, 30, 15, 25, 35],
                "mrr": ["500", "1000", "750", "invalid", "800", "1200"],
                "date_col": [date(2026, 1, i) for i in range(1, 7)],
                "tags": [["a"], ["b"], ["c"], ["d"], ["e"], ["f"]],
            }
        )

    @pytest.mark.asyncio
    async def test_sum_numeric(
        self, agg_schema: DataFrameSchema, agg_df: pl.DataFrame, mock_client: AsyncMock
    ) -> None:
        """Sum on Float64 column."""
        engine = QueryEngine(query_service=_mock_query_service(agg_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "amount", "agg": "sum", "alias": "total"}],
            }
        )
        with _patch_single_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        data_by_vert = {d["vertical"]: d for d in result.data}
        assert data_by_vert["dental"]["total"] == pytest.approx(550.0)
        # medical: 300 + 150 + None = 450
        assert data_by_vert["medical"]["total"] == pytest.approx(450.0)

    @pytest.mark.asyncio
    async def test_count(
        self, agg_schema: DataFrameSchema, agg_df: pl.DataFrame, mock_client: AsyncMock
    ) -> None:
        """Count on any column."""
        engine = QueryEngine(query_service=_mock_query_service(agg_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            }
        )
        with _patch_single_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        data_by_vert = {d["vertical"]: d for d in result.data}
        assert data_by_vert["dental"]["cnt"] == 3
        assert data_by_vert["medical"]["cnt"] == 3

    @pytest.mark.asyncio
    async def test_count_distinct(
        self, agg_schema: DataFrameSchema, agg_df: pl.DataFrame, mock_client: AsyncMock
    ) -> None:
        """Count distinct on categorical column."""
        engine = QueryEngine(query_service=_mock_query_service(agg_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "name", "agg": "count_distinct", "alias": "uniq"}
                ],
            }
        )
        with _patch_single_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        data_by_vert = {d["vertical"]: d for d in result.data}
        assert data_by_vert["dental"]["uniq"] == 2  # A, B
        assert data_by_vert["medical"]["uniq"] == 2  # A, C

    @pytest.mark.asyncio
    async def test_mean_numeric(
        self, agg_schema: DataFrameSchema, agg_df: pl.DataFrame, mock_client: AsyncMock
    ) -> None:
        """Mean on Float64 column (null excluded per Polars)."""
        engine = QueryEngine(query_service=_mock_query_service(agg_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "amount", "agg": "mean", "alias": "avg"}],
            }
        )
        with _patch_single_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        data_by_vert = {d["vertical"]: d for d in result.data}
        # dental: (100+200+250)/3
        assert data_by_vert["dental"]["avg"] == pytest.approx(550.0 / 3)
        # medical: (300+150+None)/2 non-null = 225
        assert data_by_vert["medical"]["avg"] == pytest.approx(225.0)

    @pytest.mark.asyncio
    async def test_min_max_numeric(
        self, agg_schema: DataFrameSchema, agg_df: pl.DataFrame, mock_client: AsyncMock
    ) -> None:
        """Min/max on Float64 column."""
        engine = QueryEngine(query_service=_mock_query_service(agg_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "min", "alias": "min_amt"},
                    {"column": "amount", "agg": "max", "alias": "max_amt"},
                ],
            }
        )
        with _patch_single_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        data_by_vert = {d["vertical"]: d for d in result.data}
        assert data_by_vert["dental"]["min_amt"] == 100.0
        assert data_by_vert["dental"]["max_amt"] == 250.0

    @pytest.mark.asyncio
    async def test_min_max_date(
        self, agg_schema: DataFrameSchema, agg_df: pl.DataFrame, mock_client: AsyncMock
    ) -> None:
        """Min/max on Date column."""
        engine = QueryEngine(query_service=_mock_query_service(agg_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "date_col", "agg": "min", "alias": "earliest"},
                    {"column": "date_col", "agg": "max", "alias": "latest"},
                ],
            }
        )
        with _patch_single_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        assert result.meta.group_count == 2
        for row in result.data:
            assert "earliest" in row
            assert "latest" in row

    @pytest.mark.asyncio
    async def test_multiple_aggregations_single_request(
        self,
        agg_schema: DataFrameSchema,
        agg_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Multiple aggs in one request: sum, count, mean, min, max."""
        engine = QueryEngine(query_service=_mock_query_service(agg_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "sum", "alias": "total"},
                    {"column": "gid", "agg": "count", "alias": "cnt"},
                    {"column": "amount", "agg": "mean", "alias": "avg"},
                    {"column": "amount", "agg": "min", "alias": "min_val"},
                    {"column": "amount", "agg": "max", "alias": "max_val"},
                ],
            }
        )
        with _patch_single_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        assert result.meta.aggregation_count == 5
        for row in result.data:
            for alias in ["total", "cnt", "avg", "min_val", "max_val"]:
                assert alias in row

    @pytest.mark.asyncio
    async def test_group_by_2_columns(
        self, agg_schema: DataFrameSchema, agg_df: pl.DataFrame, mock_client: AsyncMock
    ) -> None:
        """GROUP BY with 2 columns: vertical + section."""
        engine = QueryEngine(query_service=_mock_query_service(agg_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical", "section"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            }
        )
        with _patch_single_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        assert (
            result.meta.group_count == 4
        )  # dental/Active, dental/Won, medical/Active, medical/Won

    @pytest.mark.asyncio
    async def test_group_by_3_columns(
        self, agg_schema: DataFrameSchema, agg_df: pl.DataFrame, mock_client: AsyncMock
    ) -> None:
        """GROUP BY with 3 columns: vertical + section + name."""
        engine = QueryEngine(query_service=_mock_query_service(agg_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical", "section", "name"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            }
        )
        with _patch_single_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        assert result.meta.group_count == 6  # Each row is unique on 3 cols
        assert result.meta.group_by == ["vertical", "section", "name"]

    @pytest.mark.asyncio
    async def test_having_filter_on_aggregated_result(
        self,
        agg_schema: DataFrameSchema,
        agg_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """HAVING filter: only groups with total > 400."""
        engine = QueryEngine(query_service=_mock_query_service(agg_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "amount", "agg": "sum", "alias": "total"}],
                "having": {"field": "total", "op": "gt", "value": 400.0},
            }
        )
        with _patch_single_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        # dental total=550, medical total=450 -> both pass
        assert result.meta.group_count == 2

    @pytest.mark.asyncio
    async def test_having_with_nested_predicates(
        self,
        agg_schema: DataFrameSchema,
        agg_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """HAVING with AND predicate: total > 400 AND cnt > 2."""
        engine = QueryEngine(query_service=_mock_query_service(agg_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "sum", "alias": "total"},
                    {"column": "gid", "agg": "count", "alias": "cnt"},
                ],
                "having": {
                    "and": [
                        {"field": "total", "op": "gt", "value": 400.0},
                        {"field": "cnt", "op": "gte", "value": 3},
                    ]
                },
            }
        )
        with _patch_single_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        # Both groups have cnt=3 and total>400 -> both pass
        assert result.meta.group_count == 2

    @pytest.mark.asyncio
    async def test_aggregation_on_utf8_column(
        self,
        agg_schema: DataFrameSchema,
        agg_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """ADR-AGG-005: Sum on Utf8 column (mrr) casts to Float64."""
        engine = QueryEngine(query_service=_mock_query_service(agg_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "mrr", "agg": "sum", "alias": "total_mrr"}],
            }
        )
        with _patch_single_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        data_by_vert = {d["vertical"]: d for d in result.data}
        # dental: "500" + "1000" + "800" = 2300
        assert data_by_vert["dental"]["total_mrr"] == pytest.approx(2300.0)
        # medical: "750" + "invalid"(null) + "1200" = 1950
        assert data_by_vert["medical"]["total_mrr"] == pytest.approx(1950.0)


# ============================================================================
# CATEGORY 4: Join Enrichment
# ============================================================================


class TestCategory4JoinEnrichment:
    """Cross-entity join tests exercising the join module."""

    @pytest.mark.asyncio
    async def test_basic_join_offer_to_business(
        self,
        offer_schema: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        business_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Basic join: offer rows enriched with business columns."""
        schema_map = {"Offer": offer_schema, "Business": business_schema}
        service = _mock_dual_query_service(offer_df, business_df)
        engine = QueryEngine(query_service=service)
        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj"

        request = RowsRequest.model_validate(
            {
                "select": ["name", "office_phone"],
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type", "company_id"],
                },
            }
        )

        with _patch_schema_map(schema_map):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
                entity_project_registry=mock_epr,
            )

        for row in result.data:
            assert "business_booking_type" in row
            assert "business_company_id" in row
        assert result.meta.join_entity == "business"
        assert result.meta.join_matched is not None

    @pytest.mark.asyncio
    async def test_join_with_where_filter(
        self,
        offer_schema: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        business_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Join with WHERE filter on primary entity: only Active offers."""
        schema_map = {"Offer": offer_schema, "Business": business_schema}
        service = _mock_dual_query_service(offer_df, business_df)
        engine = QueryEngine(query_service=service)
        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj"

        request = RowsRequest.model_validate(
            {
                "where": {"field": "section", "op": "eq", "value": "Active"},
                "select": ["name", "section", "office_phone"],
                "join": {"entity_type": "business", "select": ["booking_type"]},
            }
        )

        with _patch_schema_map(schema_map):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
                entity_project_registry=mock_epr,
            )

        for row in result.data:
            assert row["section"] == "Active"
            assert "business_booking_type" in row

    @pytest.mark.asyncio
    async def test_join_with_section_scoping(
        self,
        offer_schema: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        business_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Join with section scoping: section='Active' param + join."""
        from autom8_asana.metrics.resolve import SectionIndex

        schema_map = {"Offer": offer_schema, "Business": business_schema}
        service = _mock_dual_query_service(offer_df, business_df)
        engine = QueryEngine(query_service=service)
        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj"
        section_index = SectionIndex(_name_to_gid={"active": "gid-123"})

        request = RowsRequest.model_validate(
            {
                "section": "Active",
                "select": ["name", "office_phone"],
                "join": {"entity_type": "business", "select": ["booking_type"]},
            }
        )

        with _patch_schema_map(schema_map):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
                section_index=section_index,
                entity_project_registry=mock_epr,
            )

        for row in result.data:
            assert "business_booking_type" in row

    @pytest.mark.asyncio
    async def test_join_to_unrelated_entity_raises(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Error: join to unrelated entity type raises JoinError."""
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate(
            {
                "join": {"entity_type": "asset_edit", "select": ["some_col"]},
            }
        )
        with _patch_single_schema(offer_schema):
            with pytest.raises(JoinError, match="No relationship"):
                await engine.execute_rows(
                    entity_type="offer",
                    project_gid="p1",
                    client=mock_client,
                    request=request,
                )

    @pytest.mark.asyncio
    async def test_join_selecting_nonexistent_column_raises(
        self,
        offer_schema: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Error: join selecting nonexistent column raises UnknownFieldError."""
        schema_map = {"Offer": offer_schema, "Business": business_schema}
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate(
            {
                "join": {"entity_type": "business", "select": ["totally_fake_column"]},
            }
        )
        with _patch_schema_map(schema_map):
            with pytest.raises(UnknownFieldError) as exc_info:
                await engine.execute_rows(
                    entity_type="offer",
                    project_gid="p1",
                    client=mock_client,
                    request=request,
                )
            assert exc_info.value.field == "totally_fake_column"


# ============================================================================
# CATEGORY 5: Pagination & Ordering
# ============================================================================


class TestCategory5PaginationOrdering:
    """Pagination, offset, and limit clamping."""

    @pytest.mark.asyncio
    async def test_default_pagination(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Default: offset=0, limit=100 returns all rows."""
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate({})
        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        assert result.meta.offset == 0
        assert result.meta.limit == 100
        assert result.meta.total_count == 10
        assert result.meta.returned_count == 10

    @pytest.mark.asyncio
    async def test_custom_offset_and_limit(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Custom offset=3, limit=4 returns rows 4-7."""
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate({"offset": 3, "limit": 4})
        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        assert result.meta.offset == 3
        assert result.meta.returned_count == 4
        assert result.meta.total_count == 10

    @pytest.mark.asyncio
    async def test_offset_beyond_total_returns_empty(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Offset beyond total rows returns empty data list."""
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate({"offset": 100})
        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        assert result.meta.total_count == 10
        assert result.meta.returned_count == 0
        assert result.data == []

    @pytest.mark.asyncio
    async def test_large_limit_clamped_by_guard(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Large limit clamped to max_result_rows."""
        engine = QueryEngine(
            query_service=_mock_query_service(offer_df),
            limits=QueryLimits(max_result_rows=5),
        )
        request = RowsRequest.model_validate({"limit": 1000})
        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        assert result.meta.limit == 5
        assert result.meta.returned_count == 5
        assert result.meta.total_count == 10

    def test_limit_pydantic_min_max(self) -> None:
        """Pydantic rejects limit < 1 or > 1000."""
        with pytest.raises(Exception):  # ValidationError
            RowsRequest.model_validate({"limit": 0})
        with pytest.raises(Exception):
            RowsRequest.model_validate({"limit": 1001})

    def test_offset_pydantic_min(self) -> None:
        """Pydantic rejects negative offset."""
        with pytest.raises(Exception):
            RowsRequest.model_validate({"offset": -1})


# ============================================================================
# CATEGORY 6: Section Scoping
# ============================================================================


class TestCategory6SectionScoping:
    """Section scoping resolution and filtering."""

    @pytest.mark.asyncio
    async def test_specific_section_name(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Query with specific section name: 'Active'."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-active"})
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate({"section": "Active"})

        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
                section_index=section_index,
            )

        for row in result.data:
            assert row["section"] == "Active"
        assert result.meta.total_count == 6  # 6 Active offers

    @pytest.mark.asyncio
    async def test_no_section_queries_all(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Query without section returns all rows."""
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate({})
        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        assert result.meta.total_count == 10

    @pytest.mark.asyncio
    async def test_nonexistent_section_raises(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Query with nonexistent section name raises UnknownSectionError."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-active"})
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate({"section": "Archived"})

        with pytest.raises(UnknownSectionError) as exc_info:
            await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
                section_index=section_index,
            )
        assert exc_info.value.section == "Archived"


# ============================================================================
# CATEGORY 7: Error Handling & Guards
# ============================================================================


class TestCategory7ErrorHandlingGuards:
    """Adversarial error paths and guard rail testing."""

    @pytest.fixture
    def simple_schema(self) -> DataFrameSchema:
        return DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
                ColumnDef("count", "Int64", nullable=True),
                ColumnDef("is_active", "Boolean", nullable=True),
                ColumnDef("tags", "List[Utf8]", nullable=True),
            ],
        )

    @pytest.fixture
    def simple_df(self) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "gid": ["1", "2"],
                "name": ["A", "B"],
                "section": ["Active", "Won"],
                "count": [10, 20],
                "is_active": [True, False],
                "tags": [["a"], ["b"]],
            }
        )

    def test_predicate_depth_exceeds_max(self) -> None:
        """Predicate depth exceeding MAX_PREDICATE_DEPTH raises QueryTooComplexError."""
        limits = QueryLimits(max_predicate_depth=3)
        # Build a depth-4 tree: AND(OR(NOT(AND(leaf))))
        deep_pred = AndGroup.model_validate(
            {
                "and": [
                    {
                        "or": [
                            {
                                "not": {
                                    "and": [{"field": "name", "op": "eq", "value": "x"}]
                                }
                            }
                        ]
                    }
                ]
            }
        )
        depth = predicate_depth(deep_pred)
        assert depth > 3
        with pytest.raises(QueryTooComplexError):
            limits.check_depth(depth)

    def test_unknown_column_in_where(self) -> None:
        """Unknown column in predicate raises UnknownFieldError."""
        compiler = PredicateCompiler()
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[ColumnDef("gid", "Utf8", nullable=False)],
        )
        node = Comparison(field="nonexistent", op=Op.EQ, value="x")
        with pytest.raises(UnknownFieldError) as exc_info:
            compiler.compile(node, schema)
        assert exc_info.value.field == "nonexistent"

    def test_type_mismatch_contains_on_int(self) -> None:
        """Contains on Int64 column raises InvalidOperatorError."""
        compiler = PredicateCompiler()
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[ColumnDef("count", "Int64", nullable=True)],
        )
        node = Comparison(field="count", op=Op.CONTAINS, value="5")
        with pytest.raises(InvalidOperatorError) as exc_info:
            compiler.compile(node, schema)
        assert exc_info.value.op == "contains"
        assert exc_info.value.dtype == "Int64"

    def test_type_mismatch_gt_on_boolean(self) -> None:
        """GT on Boolean column raises InvalidOperatorError."""
        compiler = PredicateCompiler()
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[ColumnDef("flag", "Boolean", nullable=True)],
        )
        node = Comparison(field="flag", op=Op.GT, value=True)
        with pytest.raises(InvalidOperatorError):
            compiler.compile(node, schema)

    def test_coercion_failure_string_to_int(self) -> None:
        """String 'abc' to Int64 raises CoercionError."""
        compiler = PredicateCompiler()
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[ColumnDef("count", "Int64", nullable=True)],
        )
        node = Comparison(field="count", op=Op.EQ, value="abc")
        with pytest.raises(CoercionError) as exc_info:
            compiler.compile(node, schema)
        assert exc_info.value.field == "count"
        assert exc_info.value.dtype == "Int64"

    def test_coercion_failure_invalid_date(self) -> None:
        """Invalid date string raises CoercionError."""
        compiler = PredicateCompiler()
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[ColumnDef("dt", "Date", nullable=True)],
        )
        node = Comparison(field="dt", op=Op.EQ, value="not-a-date")
        with pytest.raises(CoercionError):
            compiler.compile(node, schema)

    def test_coercion_failure_non_bool_to_boolean(self) -> None:
        """String to Boolean raises CoercionError."""
        compiler = PredicateCompiler()
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[ColumnDef("flag", "Boolean", nullable=True)],
        )
        node = Comparison(field="flag", op=Op.EQ, value="true")
        with pytest.raises(CoercionError):
            compiler.compile(node, schema)

    def test_list_dtype_has_no_allowed_operators(self) -> None:
        """List[Utf8] columns have no allowed operators in Sprint 1."""
        assert OPERATOR_MATRIX["List[Utf8]"] == frozenset()

    @pytest.mark.asyncio
    async def test_group_by_list_dtype_raises(
        self,
        simple_schema: DataFrameSchema,
        simple_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """GROUP BY on List-dtype column raises AggregationError."""
        engine = QueryEngine(query_service=_mock_query_service(simple_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["tags"],
                "aggregations": [{"column": "gid", "agg": "count"}],
            }
        )
        with _patch_single_schema(simple_schema):
            with pytest.raises(AggregationError, match="List"):
                await engine.execute_aggregate(
                    entity_type="test",
                    project_gid="p1",
                    client=mock_client,
                    request=request,
                )

    def test_exceeding_max_group_by_columns(self) -> None:
        """Exceeding MAX_GROUP_BY_COLUMNS raises AggregationError."""
        limits = QueryLimits(max_group_by_columns=2)
        schema = DataFrameSchema(
            name="t",
            task_type="T",
            columns=[
                ColumnDef("a", "Utf8"),
                ColumnDef("b", "Utf8"),
                ColumnDef("c", "Utf8"),
            ],
        )
        with pytest.raises(AggregationError, match="Too many group_by"):
            limits.check_group_by(["a", "b", "c"], schema)

    def test_exceeding_max_aggregations(self) -> None:
        """Exceeding MAX_AGGREGATIONS raises AggregationError."""
        limits = QueryLimits(max_aggregations=2)
        with pytest.raises(AggregationError, match="Too many"):
            limits.check_aggregations(3)

    def test_in_operator_non_list_value_raises(self) -> None:
        """IN operator with non-list value raises CoercionError."""
        compiler = PredicateCompiler()
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[ColumnDef("name", "Utf8", nullable=True)],
        )
        node = Comparison(field="name", op=Op.IN, value="not_a_list")
        with pytest.raises(CoercionError, match="must be a list"):
            compiler.compile(node, schema)

    def test_error_serialization_all_types(self) -> None:
        """All error types serialize to dict correctly."""
        errors = [
            QueryTooComplexError(depth=10, max_depth=5),
            UnknownFieldError(field="foo", available=["bar"]),
            InvalidOperatorError(
                field="f", dtype="Int64", op="contains", allowed=["eq"]
            ),
            CoercionError(field="f", dtype="Int64", value="abc", reason="bad"),
            UnknownSectionError(section="Archived"),
            AggregationError(message="test error"),
            AggregateGroupLimitError(group_count=100, max_groups=50),
            JoinError(message="no join"),
        ]
        for err in errors:
            d = err.to_dict()
            assert "error" in d
            assert "message" in d


# ============================================================================
# CATEGORY 8: Response Shape Validation
# ============================================================================


class TestCategory8ResponseShape:
    """Validate response structure for every query type."""

    @pytest.mark.asyncio
    async def test_rows_response_shape(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Rows response has data (list of dicts) and meta with required fields."""
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate({"limit": 3})
        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
            )

        assert isinstance(result, RowsResponse)
        assert isinstance(result.data, list)
        assert isinstance(result.meta, RowsMeta)

        # Required meta fields
        assert result.meta.total_count >= 0
        assert result.meta.returned_count >= 0
        assert result.meta.limit > 0
        assert result.meta.offset >= 0
        assert result.meta.entity_type == "offer"
        assert result.meta.project_gid == "p1"
        assert result.meta.query_ms >= 0

        # Each data row is a dict
        for row in result.data:
            assert isinstance(row, dict)
            assert "gid" in row  # gid always included

    @pytest.mark.asyncio
    async def test_rows_response_select_limits_columns(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """When select is specified, only those columns (plus gid) appear."""
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate({"select": ["name", "mrr"]})
        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
            )

        for row in result.data:
            assert set(row.keys()) == {"gid", "name", "mrr"}

    @pytest.mark.asyncio
    async def test_aggregate_response_shape(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Aggregate response has data (list of dicts) and meta with group_count."""
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            }
        )
        with _patch_single_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
            )

        assert isinstance(result, AggregateResponse)
        assert isinstance(result.data, list)
        assert isinstance(result.meta, AggregateMeta)

        assert result.meta.group_count >= 0
        assert result.meta.aggregation_count >= 0
        assert result.meta.entity_type == "offer"
        assert result.meta.project_gid == "p1"
        assert result.meta.query_ms >= 0
        assert isinstance(result.meta.group_by, list)

        # Each row has group_by column + agg columns
        for row in result.data:
            assert "vertical" in row
            assert "cnt" in row

    @pytest.mark.asyncio
    async def test_join_prefixed_columns_in_response(
        self,
        offer_schema: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        business_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Join-prefixed columns appear correctly in response."""
        schema_map = {"Offer": offer_schema, "Business": business_schema}
        service = _mock_dual_query_service(offer_df, business_df)
        engine = QueryEngine(query_service=service)
        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj"

        request = RowsRequest.model_validate(
            {
                "select": ["name"],
                "join": {"entity_type": "business", "select": ["booking_type"]},
            }
        )

        with _patch_schema_map(schema_map):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
                entity_project_registry=mock_epr,
            )

        for row in result.data:
            assert "business_booking_type" in row
            # Primary columns are not prefixed
            assert "name" in row
            assert "gid" in row

    @pytest.mark.asyncio
    async def test_no_join_meta_null_when_no_join(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Without join, join meta fields are None."""
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate({})
        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
            )
        assert result.meta.join_entity is None
        assert result.meta.join_key is None
        assert result.meta.join_matched is None
        assert result.meta.join_unmatched is None


# ============================================================================
# CATEGORY 9: End-to-End Composition
# ============================================================================


class TestCategory9EndToEndComposition:
    """Complex real-world queries combining multiple features."""

    @pytest.mark.asyncio
    async def test_where_section_join_pagination(
        self,
        offer_schema: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        business_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """WHERE + section + join + pagination: the full monty for /rows."""
        from autom8_asana.metrics.resolve import SectionIndex

        schema_map = {"Offer": offer_schema, "Business": business_schema}
        service = _mock_dual_query_service(offer_df, business_df)
        engine = QueryEngine(query_service=service)
        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj"
        section_index = SectionIndex(_name_to_gid={"active": "gid-1"})

        request = RowsRequest.model_validate(
            {
                "where": {"field": "vertical", "op": "eq", "value": "dental"},
                "section": "Active",
                "select": ["name", "mrr", "office_phone"],
                "join": {"entity_type": "business", "select": ["booking_type"]},
                "limit": 2,
                "offset": 0,
            }
        )

        with _patch_schema_map(schema_map):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
                section_index=section_index,
                entity_project_registry=mock_epr,
            )

        assert result.meta.returned_count <= 2
        for row in result.data:
            assert "business_booking_type" in row
            assert "gid" in row

    @pytest.mark.asyncio
    async def test_where_group_by_having_multiple_aggs(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """WHERE + GROUP BY + HAVING + multiple aggregations."""
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = AggregateRequest.model_validate(
            {
                "where": {"field": "section", "op": "eq", "value": "Active"},
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "mrr", "agg": "sum", "alias": "total_mrr"},
                    {"column": "gid", "agg": "count", "alias": "offer_count"},
                    {"column": "cost", "agg": "mean", "alias": "avg_cost"},
                ],
                "having": {"field": "offer_count", "op": "gte", "value": 2},
            }
        )
        with _patch_single_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
            )

        # Active offers by vertical: dental(o1, o5)=2, medical(o2, o4, o7, o10)=4
        # HAVING offer_count >= 2: both pass
        for row in result.data:
            assert row["offer_count"] >= 2
            assert "total_mrr" in row
            assert "avg_cost" in row

    @pytest.mark.asyncio
    async def test_nested_predicates_section_select_subset(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Nested predicates + section + select subset."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-1"})
        engine = QueryEngine(query_service=_mock_query_service(offer_df))

        request = RowsRequest.model_validate(
            {
                "section": "Active",
                "where": {
                    "or": [
                        {"field": "vertical", "op": "eq", "value": "dental"},
                        {
                            "and": [
                                {"field": "vertical", "op": "eq", "value": "medical"},
                                {"field": "language", "op": "eq", "value": "en"},
                            ]
                        },
                    ]
                },
                "select": ["name", "vertical", "language", "mrr"],
            }
        )

        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
                section_index=section_index,
            )

        for row in result.data:
            assert set(row.keys()) == {"gid", "name", "vertical", "language", "mrr"}

    @pytest.mark.asyncio
    async def test_flat_array_sugar_works_end_to_end(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Flat array sugar (FR-001) auto-wraps to AND at engine level."""
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate(
            {
                "where": [
                    {"field": "section", "op": "eq", "value": "Active"},
                    {"field": "vertical", "op": "eq", "value": "dental"},
                ],
                "select": ["name", "section", "vertical"],
            }
        )

        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
            )

        for row in result.data:
            assert row["section"] == "Active"
            assert row["vertical"] == "dental"

    @pytest.mark.asyncio
    async def test_empty_array_sugar_returns_all_rows(
        self,
        offer_schema: DataFrameSchema,
        offer_df: pl.DataFrame,
        mock_client: AsyncMock,
    ) -> None:
        """Empty array [] sugar = no filter (EC-005)."""
        engine = QueryEngine(query_service=_mock_query_service(offer_df))
        request = RowsRequest.model_validate({"where": []})

        with _patch_single_schema(offer_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="p1",
                client=mock_client,
                request=request,
            )

        assert result.meta.total_count == 10


# ============================================================================
# CATEGORY 10: Hierarchy & Relationship Registry
# ============================================================================


class TestCategory10HierarchyRegistry:
    """Validate entity relationship registry correctness."""

    def test_offer_to_business_relationship_exists(self) -> None:
        """Offer -> Business relationship exists via office_phone."""
        rel = find_relationship("offer", "business")
        assert rel is not None
        assert rel.default_join_key == "office_phone"

    def test_business_to_offer_bidirectional(self) -> None:
        """Relationship lookup is bidirectional."""
        rel = find_relationship("business", "offer")
        assert rel is not None

    def test_unrelated_entity_types_return_none(self) -> None:
        """Unrelated entity types return None."""
        assert find_relationship("offer", "asset_edit") is None

    def test_joinable_types_for_offer(self) -> None:
        """Offer can join to business and unit."""
        joinable = get_joinable_types("offer")
        assert "business" in joinable
        assert "unit" in joinable

    def test_joinable_types_for_business(self) -> None:
        """Business can join to unit, contact, and offer."""
        joinable = get_joinable_types("business")
        assert "unit" in joinable
        assert "contact" in joinable
        assert "offer" in joinable

    def test_explicit_join_key_overrides_default(self) -> None:
        """Explicit join key overrides the default from hierarchy."""
        key = get_join_key("offer", "business", explicit_key="custom_key")
        assert key == "custom_key"

    def test_default_join_key_when_no_explicit(self) -> None:
        """Default join key used when no explicit key provided."""
        key = get_join_key("offer", "business")
        assert key == "office_phone"


# ============================================================================
# CATEGORY 11: Model Validation (Pydantic)
# ============================================================================


class TestCategory11ModelValidation:
    """Pydantic model validation: extra fields, type errors, edge cases."""

    def test_rows_request_extra_field_rejected(self) -> None:
        """RowsRequest with extra='forbid' rejects unknown fields."""
        with pytest.raises(Exception):
            RowsRequest.model_validate({"unknown_field": "value"})

    def test_aggregate_request_extra_field_rejected(self) -> None:
        """AggregateRequest with extra='forbid' rejects unknown fields."""
        with pytest.raises(Exception):
            AggregateRequest.model_validate(
                {
                    "group_by": ["a"],
                    "aggregations": [{"column": "a", "agg": "count"}],
                    "rogue_field": True,
                }
            )

    def test_agg_spec_extra_field_rejected(self) -> None:
        """AggSpec with extra='forbid' rejects unknown fields."""
        with pytest.raises(Exception):
            AggSpec.model_validate({"column": "a", "agg": "count", "bad": True})

    def test_join_spec_extra_field_rejected(self) -> None:
        """JoinSpec with extra='forbid' rejects unknown fields."""
        with pytest.raises(Exception):
            JoinSpec.model_validate({"entity_type": "b", "select": ["x"], "extra": 1})

    def test_aggregate_request_min_group_by(self) -> None:
        """AggregateRequest requires at least 1 group_by column."""
        with pytest.raises(Exception):
            AggregateRequest.model_validate(
                {
                    "group_by": [],
                    "aggregations": [{"column": "a", "agg": "count"}],
                }
            )

    def test_aggregate_request_max_group_by(self) -> None:
        """AggregateRequest max 5 group_by columns."""
        with pytest.raises(Exception):
            AggregateRequest.model_validate(
                {
                    "group_by": ["a", "b", "c", "d", "e", "f"],
                    "aggregations": [{"column": "a", "agg": "count"}],
                }
            )

    def test_aggregate_request_min_aggregations(self) -> None:
        """AggregateRequest requires at least 1 aggregation."""
        with pytest.raises(Exception):
            AggregateRequest.model_validate(
                {
                    "group_by": ["a"],
                    "aggregations": [],
                }
            )

    def test_aggregate_request_max_aggregations(self) -> None:
        """AggregateRequest max 10 aggregations."""
        specs = [{"column": "a", "agg": "count", "alias": f"c{i}"} for i in range(11)]
        with pytest.raises(Exception):
            AggregateRequest.model_validate(
                {
                    "group_by": ["a"],
                    "aggregations": specs,
                }
            )

    def test_join_spec_min_select(self) -> None:
        """JoinSpec requires at least 1 select column."""
        with pytest.raises(Exception):
            JoinSpec.model_validate({"entity_type": "business", "select": []})

    def test_agg_spec_resolved_alias_default(self) -> None:
        """AggSpec.resolved_alias generates default from agg + column."""
        spec = AggSpec(column="mrr", agg=AggFunction.SUM)
        assert spec.resolved_alias == "sum_mrr"

    def test_agg_spec_resolved_alias_custom(self) -> None:
        """AggSpec.resolved_alias returns custom alias when set."""
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total_revenue")
        assert spec.resolved_alias == "total_revenue"

    def test_op_enum_values(self) -> None:
        """All expected Op enum values exist."""
        expected = {
            "eq",
            "ne",
            "gt",
            "lt",
            "gte",
            "lte",
            "in",
            "not_in",
            "contains",
            "starts_with",
        }
        actual = {op.value for op in Op}
        assert actual == expected

    def test_agg_function_enum_values(self) -> None:
        """All expected AggFunction enum values exist."""
        expected = {"sum", "count", "mean", "min", "max", "count_distinct"}
        actual = {f.value for f in AggFunction}
        assert actual == expected

    def test_predicate_discriminator_and_group(self) -> None:
        """Discriminator correctly parses AND group."""
        node = AndGroup.model_validate(
            {"and": [{"field": "a", "op": "eq", "value": 1}]}
        )
        assert isinstance(node, AndGroup)
        assert len(node.and_) == 1

    def test_predicate_discriminator_or_group(self) -> None:
        """Discriminator correctly parses OR group."""
        node = OrGroup.model_validate({"or": [{"field": "a", "op": "eq", "value": 1}]})
        assert isinstance(node, OrGroup)
        assert len(node.or_) == 1

    def test_predicate_discriminator_not_group(self) -> None:
        """Discriminator correctly parses NOT group."""
        node = NotGroup.model_validate({"not": {"field": "a", "op": "eq", "value": 1}})
        assert isinstance(node, NotGroup)
        assert isinstance(node.not_, Comparison)


# ============================================================================
# CATEGORY 12: Section Predicate Stripping (EC-006)
# ============================================================================


class TestCategory12SectionPredicateStripping:
    """EC-006: strip_section_predicates when section param and predicate both exist."""

    def test_strip_simple_section_comparison(self) -> None:
        """Strip a single section comparison."""
        node = Comparison(field="section", op=Op.EQ, value="Active")
        result = strip_section_predicates(node)
        assert result is None

    def test_strip_section_from_and_group(self) -> None:
        """Strip section from AND group, preserving other predicates."""
        node = AndGroup.model_validate(
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

    def test_strip_all_section_from_and_returns_none(self) -> None:
        """Strip all section predicates from AND returns None."""
        node = AndGroup.model_validate(
            {
                "and": [
                    {"field": "section", "op": "eq", "value": "Active"},
                    {"field": "section", "op": "eq", "value": "Won"},
                ]
            }
        )
        result = strip_section_predicates(node)
        assert result is None

    def test_strip_preserves_non_section_in_or(self) -> None:
        """Strip section from OR group."""
        node = OrGroup.model_validate(
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

    def test_strip_from_not_group(self) -> None:
        """Strip section from NOT group."""
        node = NotGroup.model_validate(
            {"not": {"field": "section", "op": "eq", "value": "Active"}}
        )
        result = strip_section_predicates(node)
        assert result is None

    def test_non_section_comparison_preserved(self) -> None:
        """Non-section comparison is preserved."""
        node = Comparison(field="name", op=Op.EQ, value="Acme")
        result = strip_section_predicates(node)
        assert result is not None
        assert result.field == "name"


# ============================================================================
# CATEGORY 13: Aggregator Module Direct Tests
# ============================================================================


class TestCategory13AggregatorModule:
    """Direct tests of the AggregationCompiler and helpers."""

    @pytest.fixture
    def agg_compiler(self) -> AggregationCompiler:
        return AggregationCompiler()

    @pytest.fixture
    def agg_schema(self) -> DataFrameSchema:
        return DataFrameSchema(
            name="t",
            task_type="T",
            columns=[
                ColumnDef("gid", "Utf8"),
                ColumnDef("amount", "Float64"),
                ColumnDef("name", "Utf8"),
                ColumnDef("tags", "List[Utf8]"),
                ColumnDef("flag", "Boolean"),
                ColumnDef("dt", "Date"),
            ],
        )

    def test_sum_on_list_dtype_raises(
        self, agg_compiler: AggregationCompiler, agg_schema: DataFrameSchema
    ) -> None:
        """Sum on List[Utf8] raises AggregationError."""
        specs = [AggSpec(column="tags", agg=AggFunction.SUM)]
        with pytest.raises(AggregationError):
            agg_compiler.compile(specs, agg_schema)

    def test_mean_on_boolean_raises(
        self, agg_compiler: AggregationCompiler, agg_schema: DataFrameSchema
    ) -> None:
        """Mean on Boolean raises AggregationError."""
        specs = [AggSpec(column="flag", agg=AggFunction.MEAN)]
        with pytest.raises(AggregationError):
            agg_compiler.compile(specs, agg_schema)

    def test_sum_on_date_raises(
        self, agg_compiler: AggregationCompiler, agg_schema: DataFrameSchema
    ) -> None:
        """Sum on Date raises AggregationError."""
        specs = [AggSpec(column="dt", agg=AggFunction.SUM)]
        with pytest.raises(AggregationError):
            agg_compiler.compile(specs, agg_schema)

    def test_validate_alias_uniqueness_duplicate(self) -> None:
        """Duplicate aliases raise AggregationError."""
        specs = [
            AggSpec(column="a", agg=AggFunction.SUM, alias="total"),
            AggSpec(column="b", agg=AggFunction.SUM, alias="total"),
        ]
        with pytest.raises(AggregationError, match="Duplicate"):
            validate_alias_uniqueness(specs, [])

    def test_validate_alias_group_by_collision(self) -> None:
        """Alias matching group_by column raises AggregationError."""
        specs = [AggSpec(column="amount", agg=AggFunction.SUM, alias="name")]
        with pytest.raises(AggregationError, match="collides"):
            validate_alias_uniqueness(specs, ["name"])

    def test_build_post_agg_schema_has_correct_columns(
        self, agg_schema: DataFrameSchema
    ) -> None:
        """build_post_agg_schema generates correct synthetic schema."""
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM, alias="total"),
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="cnt"),
        ]
        post_schema = build_post_agg_schema(
            group_by_columns=["name"],
            agg_specs=specs,
            source_schema=agg_schema,
        )
        names = post_schema.column_names()
        assert "name" in names
        assert "total" in names
        assert "cnt" in names

    def test_agg_compatibility_matrix_completeness(self) -> None:
        """AGG_COMPATIBILITY covers all dtypes in OPERATOR_MATRIX."""
        for dtype in OPERATOR_MATRIX:
            assert dtype in AGG_COMPATIBILITY, (
                f"Missing agg compatibility for dtype: {dtype}"
            )


# ============================================================================
# CATEGORY 14: Predicate Depth Calculation
# ============================================================================


class TestCategory14PredicateDepthCalculation:
    """Edge cases in predicate depth measurement."""

    def test_single_comparison_depth_1(self) -> None:
        node = Comparison(field="a", op=Op.EQ, value=1)
        assert predicate_depth(node) == 1

    def test_and_with_single_child_depth_2(self) -> None:
        node = AndGroup.model_validate(
            {"and": [{"field": "a", "op": "eq", "value": 1}]}
        )
        assert predicate_depth(node) == 2

    def test_not_with_comparison_depth_2(self) -> None:
        node = NotGroup.model_validate({"not": {"field": "a", "op": "eq", "value": 1}})
        assert predicate_depth(node) == 2

    def test_deeply_nested_depth_calculation(self) -> None:
        """Depth 5: AND(OR(NOT(AND(OR(leaf)))))."""
        node = AndGroup.model_validate(
            {
                "and": [
                    {
                        "or": [
                            {
                                "not": {
                                    "and": [
                                        {"or": [{"field": "a", "op": "eq", "value": 1}]}
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        )
        assert predicate_depth(node) == 6  # Exceeds default max of 5

    def test_empty_and_depth_1(self) -> None:
        node = AndGroup.model_validate({"and": []})
        assert predicate_depth(node) == 1

    def test_wide_shallow_tree(self) -> None:
        """Wide tree with many children at depth 2."""
        children = [{"field": "a", "op": "eq", "value": i} for i in range(10)]
        node = AndGroup.model_validate({"and": children})
        assert predicate_depth(node) == 2  # Only 2 levels deep regardless of width
