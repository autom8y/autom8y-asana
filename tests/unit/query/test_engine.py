"""Tests for query/engine.py: QueryEngine with mocked services."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import (
    AggregationError,
    JoinError,
    QueryTooComplexError,
    UnknownFieldError,
    UnknownSectionError,
)
from autom8_asana.query.guards import QueryLimits
from autom8_asana.query.models import (
    AggregateRequest,
    RowsRequest,
)
from autom8_asana.services.query_service import EntityQueryService


@pytest.fixture
def test_schema() -> DataFrameSchema:
    """Minimal schema for engine tests."""
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("section", "Utf8", nullable=True),
            ColumnDef("mrr", "Utf8", nullable=True),
            ColumnDef("is_completed", "Boolean", nullable=False),
        ],
    )


@pytest.fixture
def sample_df() -> pl.DataFrame:
    """Sample DataFrame with known data."""
    return pl.DataFrame(
        {
            "gid": ["1", "2", "3", "4", "5"],
            "name": ["Acme", "Beta", "Gamma", "Delta", "Echo"],
            "section": ["Active", "Active", "Won", "Lost", "Active"],
            "mrr": ["100", "200", "300", "400", "500"],
            "is_completed": [False, False, True, True, False],
        }
    )


@pytest.fixture
def mock_query_service(sample_df: pl.DataFrame) -> EntityQueryService:
    """EntityQueryService with mocked get_dataframe."""
    service = EntityQueryService()
    service.get_dataframe = AsyncMock(return_value=sample_df)  # type: ignore[method-assign]
    return service


@pytest.fixture
def mock_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def engine(mock_query_service: EntityQueryService) -> QueryEngine:
    return QueryEngine(provider=mock_query_service)


class TestQueryEngineBasic:
    """Basic query execution."""

    async def test_no_filter(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """No where clause returns all rows."""
        request = RowsRequest.model_validate({})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert result.meta.total_count == 5
        assert result.meta.returned_count == 5
        assert result.meta.entity_type == "offer"
        assert result.meta.project_gid == "proj-123"
        assert len(result.data) == 5

    async def test_eq_filter(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """Simple eq filter reduces results."""
        request = RowsRequest.model_validate(
            {"where": {"field": "name", "op": "eq", "value": "Acme"}}
        )
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert result.meta.total_count == 1
        assert result.data[0]["name"] == "Acme"


class TestQueryEnginePagination:
    """Pagination (offset/limit)."""

    async def test_limit(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        request = RowsRequest.model_validate({"limit": 2})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert result.meta.total_count == 5  # total before pagination
        assert result.meta.returned_count == 2
        assert len(result.data) == 2

    async def test_offset(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        request = RowsRequest.model_validate({"offset": 3, "limit": 10})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert result.meta.returned_count == 2  # rows 4 and 5
        assert result.data[0]["name"] == "Delta"

    async def test_max_result_rows_clamping(
        self,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
        mock_query_service: EntityQueryService,
    ) -> None:
        """Limit is clamped to max_result_rows."""
        engine = QueryEngine(
            provider=mock_query_service,
            limits=QueryLimits(max_result_rows=3),
        )
        request = RowsRequest.model_validate({"limit": 1000})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert result.meta.limit == 3
        assert result.meta.returned_count == 3


class TestQueryEngineSection:
    """Section scoping."""

    async def test_section_filter(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """Section parameter filters by name."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-123"})

        request = RowsRequest.model_validate({"section": "Active"})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
                section_index=section_index,
            )

        assert result.meta.total_count == 3  # 3 Active rows
        for row in result.data:
            assert row["section"] == "Active"

    async def test_unknown_section(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """Unknown section raises UnknownSectionError."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-123"})

        request = RowsRequest.model_validate({"section": "Nonexistent"})
        with pytest.raises(UnknownSectionError) as exc_info:
            await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
                section_index=section_index,
            )
        assert exc_info.value.section == "Nonexistent"


class TestQueryEngineSelect:
    """Column selection."""

    async def test_select_fields(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """Select controls which columns appear."""
        request = RowsRequest.model_validate({"select": ["name", "mrr"]})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        # gid always included
        assert "gid" in result.data[0]
        assert "name" in result.data[0]
        assert "mrr" in result.data[0]
        assert "section" not in result.data[0]

    async def test_select_unknown_field_raises(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """Selecting a field not in schema raises UnknownFieldError."""
        request = RowsRequest.model_validate({"select": ["name", "nonexistent"]})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            with pytest.raises(UnknownFieldError) as exc_info:
                await engine.execute_rows(
                    entity_type="offer",
                    project_gid="proj-123",
                    client=mock_client,
                    request=request,
                )
            assert exc_info.value.field == "nonexistent"

    async def test_gid_always_included(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """gid is always in the response even if not in select."""
        request = RowsRequest.model_validate({"select": ["name"]})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert "gid" in result.data[0]


class TestQueryEngineMetadata:
    """Response metadata."""

    async def test_meta_fields(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        request = RowsRequest.model_validate({"limit": 2, "offset": 1})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert result.meta.total_count == 5
        assert result.meta.returned_count == 2
        assert result.meta.limit == 2
        assert result.meta.offset == 1
        assert result.meta.entity_type == "offer"
        assert result.meta.project_gid == "proj-123"
        assert result.meta.query_ms >= 0


# ---------------------------------------------------------------------------
# Join Engine Integration Tests (TC-EJ001 through TC-EJ010)
# ---------------------------------------------------------------------------


@pytest.fixture
def offer_schema_with_phone() -> DataFrameSchema:
    """Offer schema with office_phone for join tests."""
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("section", "Utf8", nullable=True),
            ColumnDef("office_phone", "Utf8", nullable=True),
            ColumnDef("mrr", "Utf8", nullable=True),
        ],
    )


@pytest.fixture
def business_schema() -> DataFrameSchema:
    """Business schema for join target."""
    return DataFrameSchema(
        name="business",
        task_type="Business",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("office_phone", "Utf8", nullable=True),
            ColumnDef("booking_type", "Utf8", nullable=True),
            ColumnDef("company_id", "Utf8", nullable=True),
        ],
    )


@pytest.fixture
def offer_df_with_phone() -> pl.DataFrame:
    """Offer DataFrame with office_phone for join tests."""
    return pl.DataFrame(
        {
            "gid": ["o1", "o2", "o3"],
            "name": ["Offer A", "Offer B", "Offer C"],
            "section": ["Active", "Active", "Won"],
            "office_phone": ["+1111", "+2222", "+3333"],
            "mrr": ["100", "200", "300"],
        }
    )


@pytest.fixture
def business_df() -> pl.DataFrame:
    """Business DataFrame for join target."""
    return pl.DataFrame(
        {
            "gid": ["b1", "b2"],
            "name": ["Biz A", "Biz B"],
            "office_phone": ["+1111", "+2222"],
            "booking_type": ["Online", "Phone"],
            "company_id": ["CMP-1", "CMP-2"],
        }
    )


def _make_schema_map(
    offer_schema: DataFrameSchema,
    business_schema: DataFrameSchema,
) -> dict[str, DataFrameSchema]:
    """Build a schema lookup map by task type."""
    return {
        "Offer": offer_schema,
        "Business": business_schema,
    }


class TestQueryEngineJoin:
    """Join integration tests for QueryEngine.execute_rows()."""

    async def test_tc_ej001_valid_join(
        self,
        mock_client: AsyncMock,
        offer_schema_with_phone: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df_with_phone: pl.DataFrame,
        business_df: pl.DataFrame,
    ) -> None:
        """TC-EJ001: /rows with valid join spec returns prefixed columns."""
        schema_map = _make_schema_map(offer_schema_with_phone, business_schema)

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            side_effect=[offer_df_with_phone, business_df]
        )
        engine = QueryEngine(provider=service)

        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj-123"

        request = RowsRequest.model_validate(
            {
                "select": ["name", "office_phone"],
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type"],
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.side_effect = lambda k: schema_map[k]
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
                entity_project_registry=mock_epr,
            )

        # Verify join columns present in response
        assert any("business_booking_type" in row for row in result.data)
        assert result.meta.join_entity == "business"
        assert result.meta.join_key == "office_phone"
        assert result.meta.join_matched == 2
        assert result.meta.join_unmatched == 1

    async def test_tc_ej002_join_with_filter(
        self,
        mock_client: AsyncMock,
        offer_schema_with_phone: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df_with_phone: pl.DataFrame,
        business_df: pl.DataFrame,
    ) -> None:
        """TC-EJ002: /rows with join + predicate filter."""
        schema_map = _make_schema_map(offer_schema_with_phone, business_schema)

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            side_effect=[offer_df_with_phone, business_df]
        )
        engine = QueryEngine(provider=service)

        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj-123"

        request = RowsRequest.model_validate(
            {
                "where": {"field": "name", "op": "eq", "value": "Offer A"},
                "select": ["name", "office_phone"],
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type"],
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.side_effect = lambda k: schema_map[k]
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
                entity_project_registry=mock_epr,
            )

        assert result.meta.total_count == 1
        assert result.data[0]["name"] == "Offer A"
        assert result.data[0]["business_booking_type"] == "Online"

    async def test_tc_ej004_unrelated_entity_type(
        self,
        mock_client: AsyncMock,
        offer_schema_with_phone: DataFrameSchema,
        offer_df_with_phone: pl.DataFrame,
    ) -> None:
        """TC-EJ004: /rows with join to unrelated entity type raises JoinError."""
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            return_value=offer_df_with_phone
        )
        engine = QueryEngine(provider=service)

        request = RowsRequest.model_validate(
            {
                "join": {
                    "entity_type": "contact",
                    "select": ["contact_email"],
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = offer_schema_with_phone
            mock_registry_cls.get_instance.return_value = mock_registry

            with pytest.raises(JoinError, match="No relationship"):
                await engine.execute_rows(
                    entity_type="offer",
                    project_gid="proj-123",
                    client=mock_client,
                    request=request,
                )

    async def test_tc_ej005_invalid_join_column(
        self,
        mock_client: AsyncMock,
        offer_schema_with_phone: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df_with_phone: pl.DataFrame,
    ) -> None:
        """TC-EJ005: /rows with join selecting invalid column raises UnknownFieldError."""
        schema_map = _make_schema_map(offer_schema_with_phone, business_schema)

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            return_value=offer_df_with_phone
        )
        engine = QueryEngine(provider=service)

        request = RowsRequest.model_validate(
            {
                "join": {
                    "entity_type": "business",
                    "select": ["nonexistent_col"],
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.side_effect = lambda k: schema_map[k]
            mock_registry_cls.get_instance.return_value = mock_registry

            with pytest.raises(UnknownFieldError) as exc_info:
                await engine.execute_rows(
                    entity_type="offer",
                    project_gid="proj-123",
                    client=mock_client,
                    request=request,
                )
            assert exc_info.value.field == "nonexistent_col"

    async def test_tc_ej006_no_project_for_target(
        self,
        mock_client: AsyncMock,
        offer_schema_with_phone: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df_with_phone: pl.DataFrame,
    ) -> None:
        """TC-EJ006: /rows with join, target project not configured raises JoinError."""
        schema_map = _make_schema_map(offer_schema_with_phone, business_schema)

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            return_value=offer_df_with_phone
        )
        engine = QueryEngine(provider=service)

        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = None

        request = RowsRequest.model_validate(
            {
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type"],
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.side_effect = lambda k: schema_map[k]
            mock_registry_cls.get_instance.return_value = mock_registry

            with pytest.raises(JoinError, match="No project configured"):
                await engine.execute_rows(
                    entity_type="offer",
                    project_gid="proj-123",
                    client=mock_client,
                    request=request,
                    entity_project_registry=mock_epr,
                )

    async def test_tc_ej007_join_meta_in_response(
        self,
        mock_client: AsyncMock,
        offer_schema_with_phone: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df_with_phone: pl.DataFrame,
        business_df: pl.DataFrame,
    ) -> None:
        """TC-EJ007: /rows with join includes join meta in response."""
        schema_map = _make_schema_map(offer_schema_with_phone, business_schema)

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            side_effect=[offer_df_with_phone, business_df]
        )
        engine = QueryEngine(provider=service)

        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj-123"

        request = RowsRequest.model_validate(
            {
                "select": ["name", "office_phone"],
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type"],
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.side_effect = lambda k: schema_map[k]
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
                entity_project_registry=mock_epr,
            )

        assert result.meta.join_entity == "business"
        assert result.meta.join_key == "office_phone"
        assert result.meta.join_matched is not None
        assert result.meta.join_unmatched is not None

    async def test_tc_ej008_no_join_backward_compat(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """TC-EJ008: /rows without join is identical to Sprint 1 behavior."""
        request = RowsRequest.model_validate({})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert result.meta.join_entity is None
        assert result.meta.join_key is None
        assert result.meta.join_matched is None
        assert result.meta.join_unmatched is None
        assert result.meta.total_count == 5

    async def test_tc_ej009_explicit_on_key(
        self,
        mock_client: AsyncMock,
        offer_schema_with_phone: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df_with_phone: pl.DataFrame,
        business_df: pl.DataFrame,
    ) -> None:
        """TC-EJ009: /rows with join and explicit on key uses specified key."""
        schema_map = _make_schema_map(offer_schema_with_phone, business_schema)

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            side_effect=[offer_df_with_phone, business_df]
        )
        engine = QueryEngine(provider=service)

        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj-123"

        request = RowsRequest.model_validate(
            {
                "select": ["name", "office_phone"],
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type"],
                    "on": "office_phone",
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.side_effect = lambda k: schema_map[k]
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
                entity_project_registry=mock_epr,
            )

        assert result.meta.join_key == "office_phone"
        assert result.meta.join_matched == 2

    async def test_tc_ej010_join_with_section(
        self,
        mock_client: AsyncMock,
        offer_schema_with_phone: DataFrameSchema,
        business_schema: DataFrameSchema,
        offer_df_with_phone: pl.DataFrame,
        business_df: pl.DataFrame,
    ) -> None:
        """TC-EJ010: /rows with join + section scoping."""
        schema_map = _make_schema_map(offer_schema_with_phone, business_schema)

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            side_effect=[offer_df_with_phone, business_df]
        )
        engine = QueryEngine(provider=service)

        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj-123"

        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-123"})

        request = RowsRequest.model_validate(
            {
                "section": "Active",
                "select": ["name", "office_phone"],
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type"],
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.side_effect = lambda k: schema_map[k]
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
                section_index=section_index,
                entity_project_registry=mock_epr,
            )

        # Only Active section rows (o1, o2)
        assert result.meta.total_count == 2
        assert result.meta.returned_count == 2
        # Join still works on filtered subset
        assert result.meta.join_entity == "business"
        assert result.meta.join_matched is not None


# ---------------------------------------------------------------------------
# Aggregate Engine Integration Tests (TC-EA001 through TC-EA020)
# ---------------------------------------------------------------------------


@pytest.fixture
def agg_schema() -> DataFrameSchema:
    """Schema with numeric columns for aggregate engine tests."""
    return DataFrameSchema(
        name="test_entity",
        task_type="TestEntity",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("vertical", "Utf8", nullable=True),
            ColumnDef("section", "Utf8", nullable=True),
            ColumnDef("amount", "Float64", nullable=True),
            ColumnDef("quantity", "Int64", nullable=True),
            ColumnDef("platforms", "List[Utf8]", nullable=True),
        ],
    )


@pytest.fixture
def agg_df() -> pl.DataFrame:
    """Sample DataFrame for aggregate tests."""
    return pl.DataFrame(
        {
            "gid": ["1", "2", "3", "4", "5", "6"],
            "name": ["A", "B", "C", "D", "E", "F"],
            "vertical": ["dental", "dental", "dental", "medical", "medical", "medical"],
            "section": ["Active", "Active", "Won", "Active", "Won", "Won"],
            "amount": [100.0, 200.0, 300.0, 150.0, 250.0, 350.0],
            "quantity": [10, 20, 30, 15, 25, 35],
            "platforms": [["fb"], ["google"], ["fb"], ["google"], ["fb"], ["google"]],
        }
    )


@pytest.fixture
def agg_mock_service(agg_df: pl.DataFrame) -> EntityQueryService:
    """EntityQueryService returning agg_df."""
    service = EntityQueryService()
    service.get_dataframe = AsyncMock(return_value=agg_df)  # type: ignore[method-assign]
    return service


@pytest.fixture
def agg_engine(agg_mock_service: EntityQueryService) -> QueryEngine:
    return QueryEngine(provider=agg_mock_service)


def _patch_schema(schema: DataFrameSchema):
    """Context manager to patch SchemaRegistry for aggregate tests."""
    return patch(
        "autom8_asana.query.engine.SchemaRegistry",
        **{
            "return_value.get_schema.return_value": schema,
            "get_instance.return_value.get_schema.return_value": schema,
        },
    )


class TestExecuteAggregate:
    """Integration tests for QueryEngine.execute_aggregate()."""

    async def test_tc_ea001_basic_group_by_sum(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA001: Basic group_by + sum produces correct grouped sums."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "amount", "agg": "sum", "alias": "total_amount"}],
            }
        )
        with _patch_schema(agg_schema):
            result = await agg_engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.meta.group_count == 2
        data_by_vert = {d["vertical"]: d for d in result.data}
        assert data_by_vert["dental"]["total_amount"] == 600.0
        assert data_by_vert["medical"]["total_amount"] == 750.0

    async def test_tc_ea002_multiple_aggregations(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA002: group_by + multiple aggregations returns all agg columns."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "sum", "alias": "total"},
                    {"column": "amount", "agg": "mean", "alias": "avg"},
                    {"column": "gid", "agg": "count", "alias": "cnt"},
                ],
            }
        )
        with _patch_schema(agg_schema):
            result = await agg_engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.meta.group_count == 2
        for row in result.data:
            assert "total" in row
            assert "avg" in row
            assert "cnt" in row

    async def test_tc_ea003_where_filter_before_grouping(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA003: WHERE filter applied before grouping."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "where": {"field": "section", "op": "eq", "value": "Active"},
            }
        )
        with _patch_schema(agg_schema):
            result = await agg_engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        # Only Active rows: dental(2), medical(1)
        data_by_vert = {d["vertical"]: d for d in result.data}
        assert data_by_vert["dental"]["cnt"] == 2
        assert data_by_vert["medical"]["cnt"] == 1

    async def test_tc_ea004_section_filter(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA004: section + group_by applies section filter before grouping."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-123"})

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "section": "Active",
            }
        )
        with _patch_schema(agg_schema):
            result = await agg_engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
                section_index=section_index,
            )

        data_by_vert = {d["vertical"]: d for d in result.data}
        assert data_by_vert["dental"]["cnt"] == 2
        assert data_by_vert["medical"]["cnt"] == 1

    async def test_tc_ea005_having_filter(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA005: group_by + HAVING filters groups post-aggregation."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "amount", "agg": "sum", "alias": "total"}],
                "having": {"field": "total", "op": "gt", "value": 700.0},
            }
        )
        with _patch_schema(agg_schema):
            result = await agg_engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        # dental total=600, medical total=750 -> only medical passes
        assert result.meta.group_count == 1
        assert result.data[0]["vertical"] == "medical"

    async def test_tc_ea006_full_pipeline(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA006: WHERE + section + group_by + HAVING full pipeline."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-123"})

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "amount", "agg": "sum", "alias": "total"}],
                "section": "Active",
                "where": {"field": "amount", "op": "gte", "value": 100.0},
                "having": {"field": "total", "op": "gte", "value": 200.0},
            }
        )
        with _patch_schema(agg_schema):
            result = await agg_engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
                section_index=section_index,
            )

        # Active rows: dental(100,200), medical(150)
        # After WHERE (>=100): all pass
        # dental total=300, medical total=150
        # HAVING (>=200): dental passes
        assert result.meta.group_count == 1
        assert result.data[0]["vertical"] == "dental"

    async def test_tc_ea007_group_by_nonexistent_column(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA007: group_by on non-existent column raises UnknownFieldError."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["nonexistent"],
                "aggregations": [{"column": "gid", "agg": "count"}],
            }
        )
        with _patch_schema(agg_schema):
            with pytest.raises(UnknownFieldError) as exc_info:
                await agg_engine.execute_aggregate(
                    entity_type="test_entity",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )
            assert exc_info.value.field == "nonexistent"

    async def test_tc_ea008_group_by_list_column(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA008: group_by on List[Utf8] column raises AggregationError."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["platforms"],
                "aggregations": [{"column": "gid", "agg": "count"}],
            }
        )
        with _patch_schema(agg_schema):
            with pytest.raises(AggregationError) as exc_info:
                await agg_engine.execute_aggregate(
                    entity_type="test_entity",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )
            assert "List" in str(exc_info.value.message)

    async def test_tc_ea009_sum_on_utf8_casts(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA009: sum on Utf8 column casts to Float64 (ADR-AGG-005)."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "name", "agg": "sum", "alias": "name_sum"}],
            }
        )
        with _patch_schema(agg_schema):
            result = await agg_engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )
        # Non-numeric strings cast to null via strict=False, sum of nulls = 0
        assert result.meta.group_count == 2
        for row in result.data:
            assert "name_sum" in row

    async def test_tc_ea010_empty_after_where(
        self,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA010: Empty DataFrame after WHERE filter returns empty data."""
        empty_df = pl.DataFrame(
            {
                "gid": pl.Series([], dtype=pl.Utf8),
                "name": pl.Series([], dtype=pl.Utf8),
                "vertical": pl.Series([], dtype=pl.Utf8),
                "section": pl.Series([], dtype=pl.Utf8),
                "amount": pl.Series([], dtype=pl.Float64),
                "quantity": pl.Series([], dtype=pl.Int64),
                "platforms": pl.Series([], dtype=pl.List(pl.Utf8)),
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=empty_df)  # type: ignore[method-assign]
        engine = QueryEngine(provider=service)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "amount", "agg": "sum", "alias": "total"}],
            }
        )
        with _patch_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.meta.group_count == 0
        assert result.data == []

    async def test_tc_ea011_single_group(
        self,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA011: Single group (all rows in one group) returns 1 entry."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", "B", "C"],
                "vertical": ["dental", "dental", "dental"],
                "section": ["Active", "Active", "Active"],
                "amount": [100.0, 200.0, 300.0],
                "quantity": [10, 20, 30],
                "platforms": [["fb"], ["google"], ["fb"]],
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(provider=service)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "amount", "agg": "sum", "alias": "total"}],
            }
        )
        with _patch_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.meta.group_count == 1
        assert result.data[0]["total"] == 600.0

    async def test_tc_ea012_null_values(
        self,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA012: Null values in aggregation column handled per Polars semantics."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", "B", "C"],
                "vertical": ["dental", "dental", "dental"],
                "section": ["Active", "Active", "Active"],
                "amount": [100.0, None, 300.0],
                "quantity": [10, 20, 30],
                "platforms": [["fb"], ["google"], ["fb"]],
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(provider=service)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "sum", "alias": "total"},
                    {"column": "amount", "agg": "count", "alias": "cnt"},
                ],
            }
        )
        with _patch_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.data[0]["total"] == 400.0  # sum ignores null
        assert result.data[0]["cnt"] == 2  # count excludes null

    async def test_tc_ea013_count_vs_count_distinct(
        self,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA013: count vs count_distinct produces different results with duplicates."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3", "4"],
                "name": ["A", "A", "B", "B"],
                "vertical": ["dental", "dental", "dental", "dental"],
                "section": ["Active", "Active", "Active", "Active"],
                "amount": [100.0, 200.0, 300.0, 400.0],
                "quantity": [10, 20, 30, 40],
                "platforms": [["fb"], ["google"], ["fb"], ["google"]],
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(provider=service)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "name", "agg": "count", "alias": "name_count"},
                    {"column": "name", "agg": "count_distinct", "alias": "name_uniq"},
                ],
            }
        )
        with _patch_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.data[0]["name_count"] == 4
        assert result.data[0]["name_uniq"] == 2

    async def test_tc_ea014_having_filters_all_groups(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA014: HAVING filters all groups returns empty data."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "amount", "agg": "sum", "alias": "total"}],
                "having": {"field": "total", "op": "gt", "value": 999999.0},
            }
        )
        with _patch_schema(agg_schema):
            result = await agg_engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.meta.group_count == 0
        assert result.data == []

    async def test_tc_ea015_multiple_group_by(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA015: Multiple group_by columns produces compound grouping."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical", "section"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            }
        )
        with _patch_schema(agg_schema):
            result = await agg_engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        # dental/Active=2, dental/Won=1, medical/Active=1, medical/Won=2
        assert result.meta.group_count == 4

    async def test_tc_ea016_depth_guard_where(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA016: Depth guard on WHERE raises QueryTooComplexError."""
        leaf = {"field": "name", "op": "eq", "value": "x"}
        deep = {"and": [{"or": [{"and": [{"not": {"and": [leaf]}}]}]}]}

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count"}],
                "where": deep,
            }
        )
        with _patch_schema(agg_schema):
            with pytest.raises(QueryTooComplexError):
                await agg_engine.execute_aggregate(
                    entity_type="test_entity",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )

    async def test_tc_ea017_depth_guard_having(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA017: Depth guard on HAVING raises QueryTooComplexError."""
        leaf = {"field": "cnt", "op": "gt", "value": 1}
        deep = {"and": [{"or": [{"and": [{"not": {"and": [leaf]}}]}]}]}

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "having": deep,
            }
        )
        with _patch_schema(agg_schema):
            with pytest.raises(QueryTooComplexError):
                await agg_engine.execute_aggregate(
                    entity_type="test_entity",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )

    async def test_tc_ea018_count_distinct_with_nulls(
        self,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA018: count_distinct with nulls counts null as distinct (Polars behavior)."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", None, "A"],
                "vertical": ["dental", "dental", "dental"],
                "section": ["Active", "Active", "Active"],
                "amount": [100.0, 200.0, 300.0],
                "quantity": [10, 20, 30],
                "platforms": [["fb"], ["google"], ["fb"]],
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(provider=service)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "name", "agg": "count_distinct", "alias": "uniq_names"},
                ],
            }
        )
        with _patch_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        # "A" and null = 2 distinct values (Polars n_unique counts null)
        assert result.data[0]["uniq_names"] == 2

    async def test_tc_ea019_meta_populated(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA019: AggregateMeta populated correctly."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            }
        )
        with _patch_schema(agg_schema):
            result = await agg_engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.meta.group_count == 2
        assert result.meta.aggregation_count == 1
        assert result.meta.group_by == ["vertical"]
        assert result.meta.entity_type == "test_entity"
        assert result.meta.project_gid == "proj-1"
        assert result.meta.query_ms >= 0

    async def test_tc_ea020_alias_avoids_collision(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA020: Two aggs on same column with different aliases avoid collision."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "sum", "alias": "amount_total"},
                    {"column": "amount", "agg": "mean", "alias": "amount_avg"},
                ],
            }
        )
        with _patch_schema(agg_schema):
            result = await agg_engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        for row in result.data:
            assert "amount_total" in row
            assert "amount_avg" in row

    async def test_tc_ea021_group_limit_guard(
        self,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA021: Group count exceeding max_aggregate_groups raises AggregateGroupLimitError."""
        from autom8_asana.query.errors import AggregateGroupLimitError

        # Each row has a unique gid, so group_by gid produces N groups
        df = pl.DataFrame(
            {
                "gid": [str(i) for i in range(5)],
                "name": ["A"] * 5,
                "vertical": [f"v{i}" for i in range(5)],
                "section": ["Active"] * 5,
                "amount": [100.0] * 5,
                "quantity": [10] * 5,
                "platforms": [["fb"]] * 5,
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        # Set max_aggregate_groups to 3 so 5 groups triggers the guard
        engine = QueryEngine(
            provider=service,
            limits=QueryLimits(max_aggregate_groups=3),
        )

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            }
        )
        with _patch_schema(agg_schema):
            with pytest.raises(AggregateGroupLimitError) as exc_info:
                await engine.execute_aggregate(
                    entity_type="test_entity",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )
            assert exc_info.value.group_count == 5
            assert exc_info.value.max_groups == 3

    async def test_tc_ea022_alias_collision_raises(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA022: Duplicate aliases raise AggregationError at engine level."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "sum", "alias": "total"},
                    {"column": "quantity", "agg": "sum", "alias": "total"},
                ],
            }
        )
        with _patch_schema(agg_schema):
            with pytest.raises(AggregationError, match="Duplicate alias"):
                await agg_engine.execute_aggregate(
                    entity_type="test_entity",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )

    async def test_tc_ea023_alias_collides_with_group_by(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA023: Alias colliding with group_by column raises AggregationError."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "sum", "alias": "vertical"},
                ],
            }
        )
        with _patch_schema(agg_schema):
            with pytest.raises(AggregationError, match="collides with group_by"):
                await agg_engine.execute_aggregate(
                    entity_type="test_entity",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )

    async def test_tc_ea024_utf8_financial_column_sum(
        self,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA024: Utf8 financial column sum via Float64 cast produces correct numeric sum.

        This is the primary use case: sum(mrr) where mrr is a Utf8 column
        containing string-encoded numbers. ADR-AGG-005.
        """
        # Build a schema that includes a Utf8 'mrr' column
        mrr_schema = DataFrameSchema(
            name="test_entity",
            task_type="TestEntity",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("vertical", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
                ColumnDef("mrr", "Utf8", nullable=True),
                ColumnDef("amount", "Float64", nullable=True),
                ColumnDef("quantity", "Int64", nullable=True),
                ColumnDef("platforms", "List[Utf8]", nullable=True),
            ],
        )
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3", "4"],
                "name": ["A", "B", "C", "D"],
                "vertical": ["dental", "dental", "medical", "medical"],
                "section": ["Active", "Active", "Active", "Active"],
                "mrr": ["100.50", "200.75", "300.00", "invalid"],
                "amount": [10.0, 20.0, 30.0, 40.0],
                "quantity": [1, 2, 3, 4],
                "platforms": [["fb"], ["g"], ["fb"], ["g"]],
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(provider=service)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "mrr", "agg": "sum", "alias": "total_mrr"},
                ],
            }
        )
        with _patch_schema(mrr_schema):
            result = await engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        data_by_vert = {d["vertical"]: d for d in result.data}
        # dental: "100.50" + "200.75" = 301.25  # noqa: ERA001
        assert data_by_vert["dental"]["total_mrr"] == pytest.approx(301.25)
        # medical: "300.00" + null (invalid cast) = 300.0
        assert data_by_vert["medical"]["total_mrr"] == pytest.approx(300.0)

    async def test_tc_ea025_having_references_nonexistent_alias(
        self,
        agg_engine: QueryEngine,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
    ) -> None:
        """TC-EA025: HAVING referencing non-existent alias raises UnknownFieldError."""
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "having": {"field": "nonexistent_alias", "op": "gt", "value": 1},
            }
        )
        with _patch_schema(agg_schema):
            with pytest.raises(UnknownFieldError) as exc_info:
                await agg_engine.execute_aggregate(
                    entity_type="test_entity",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )
            assert exc_info.value.field == "nonexistent_alias"

    async def test_tc_ea026_group_limit_guard_serialization(
        self,
    ) -> None:
        """TC-EA026: AggregateGroupLimitError serializes correctly."""
        from autom8_asana.query.errors import AggregateGroupLimitError

        err = AggregateGroupLimitError(group_count=15000, max_groups=10000)
        d = err.to_dict()
        assert d["error"] == "TOO_MANY_GROUPS"
        assert d["group_count"] == 15000
        assert d["max_groups"] == 10000
        assert "15000" in d["message"]
        assert "10000" in d["message"]


# ---------------------------------------------------------------------------
# R-010: DataFrameProvider protocol decoupling tests
# ---------------------------------------------------------------------------


class TestQueryEngineWithMockProvider:
    """Verify QueryEngine works with a pure mock DataFrameProvider (no EntityQueryService)."""

    async def test_mock_provider_rows(
        self,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
        sample_df: pl.DataFrame,
    ) -> None:
        """QueryEngine works with a bare mock implementing DataFrameProvider."""
        mock_provider = AsyncMock()
        mock_provider.get_dataframe = AsyncMock(return_value=sample_df)
        mock_provider.last_freshness_info = None

        engine = QueryEngine(provider=mock_provider)

        request = RowsRequest.model_validate({})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert result.meta.total_count == 5
        assert result.meta.returned_count == 5
        mock_provider.get_dataframe.assert_awaited_once_with("offer", "proj-123", mock_client)

    async def test_mock_provider_aggregate(
        self,
        mock_client: AsyncMock,
        agg_schema: DataFrameSchema,
        agg_df: pl.DataFrame,
    ) -> None:
        """QueryEngine aggregate works with a bare mock DataFrameProvider."""
        mock_provider = AsyncMock()
        mock_provider.get_dataframe = AsyncMock(return_value=agg_df)
        mock_provider.last_freshness_info = None

        engine = QueryEngine(provider=mock_provider)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "amount", "agg": "sum", "alias": "total"}],
            }
        )
        with _patch_schema(agg_schema):
            result = await engine.execute_aggregate(
                entity_type="test_entity",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.meta.group_count == 2
        mock_provider.get_dataframe.assert_awaited_once()

    async def test_mock_provider_freshness_passthrough(
        self,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
        sample_df: pl.DataFrame,
    ) -> None:
        """Freshness metadata from provider flows through to response."""
        from autom8_asana.cache.integration.dataframe_cache import FreshnessInfo

        freshness = FreshnessInfo(
            freshness="fresh",
            data_age_seconds=10.0,
            staleness_ratio=0.1,
        )
        mock_provider = AsyncMock()
        mock_provider.get_dataframe = AsyncMock(return_value=sample_df)
        mock_provider.last_freshness_info = freshness

        engine = QueryEngine(provider=mock_provider)

        request = RowsRequest.model_validate({})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = test_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert result.meta.freshness == "fresh"
        assert result.meta.data_age_seconds == 10.0
        assert result.meta.staleness_ratio == 0.1
