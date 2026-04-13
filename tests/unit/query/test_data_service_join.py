"""Tests for cross-service data-service join enrichment (Phase 1).

Covers:
- JoinSpec extension: source, factory, period fields + validation
- DataServiceJoinFetcher: PVP extraction + batch fetch + DataFrame assembly
- QueryEngine dispatch: data-service vs entity join routing
- Virtual entity registry: lookup and introspection
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from pydantic import ValidationError

from autom8_asana.query.data_service_entities import (
    DATA_SERVICE_ENTITIES,
    get_data_service_entity,
    list_data_service_entities,
)
from autom8_asana.query.errors import JoinError
from autom8_asana.query.fetcher import DataServiceJoinFetcher
from autom8_asana.query.join import JoinSpec, execute_join

# ---------------------------------------------------------------------------
# JoinSpec Extension Tests
# ---------------------------------------------------------------------------


class TestJoinSpecDataServiceFields:
    """Validate new source/factory/period fields on JoinSpec."""

    def test_default_source_is_entity(self) -> None:
        """Default source remains 'entity' for backward compatibility."""
        spec = JoinSpec(entity_type="business", select=["booking_type"])
        assert spec.source == "entity"
        assert spec.factory is None
        assert spec.period == "LIFETIME"

    def test_data_service_source_with_factory(self) -> None:
        """Data-service source parses correctly with factory."""
        spec = JoinSpec(
            entity_type="spend",
            select=["spend", "cps"],
            source="data-service",
            factory="spend",
            period="T30",
        )
        assert spec.source == "data-service"
        assert spec.factory == "spend"
        assert spec.period == "T30"

    def test_data_service_requires_factory(self) -> None:
        """Data-service source without factory raises validation error."""
        with pytest.raises(ValidationError, match="factory is required"):
            JoinSpec(
                entity_type="spend",
                select=["spend"],
                source="data-service",
            )

    def test_entity_source_rejects_factory(self) -> None:
        """Entity source with factory raises validation error."""
        with pytest.raises(ValidationError, match="factory is only valid"):
            JoinSpec(
                entity_type="business",
                select=["booking_type"],
                source="entity",
                factory="spend",
            )

    def test_data_service_default_period(self) -> None:
        """Data-service joins default to LIFETIME period."""
        spec = JoinSpec(
            entity_type="spend",
            select=["spend"],
            source="data-service",
            factory="spend",
        )
        assert spec.period == "LIFETIME"

    def test_data_service_explicit_on_key(self) -> None:
        """Data-service join with explicit on key."""
        spec = JoinSpec(
            entity_type="spend",
            select=["spend"],
            source="data-service",
            factory="spend",
            on="office_phone",
        )
        assert spec.on == "office_phone"

    def test_invalid_source_rejected(self) -> None:
        """Invalid source value raises validation error."""
        with pytest.raises(ValidationError):
            JoinSpec(
                entity_type="spend",
                select=["spend"],
                source="invalid",  # type: ignore[arg-type]
            )

    def test_existing_entity_validation_preserved(self) -> None:
        """Existing validations (empty select, max columns) still work."""
        with pytest.raises(ValidationError):
            JoinSpec(
                entity_type="spend",
                select=[],
                source="data-service",
                factory="spend",
            )
        with pytest.raises(ValidationError):
            JoinSpec(
                entity_type="spend",
                select=[f"col_{i}" for i in range(11)],
                source="data-service",
                factory="spend",
            )

    def test_extra_fields_still_rejected(self) -> None:
        """Extra fields are still rejected."""
        with pytest.raises(ValidationError):
            JoinSpec(
                entity_type="spend",
                select=["spend"],
                source="data-service",
                factory="spend",
                bogus="bad",  # type: ignore[call-arg]
            )

    def test_json_round_trip(self) -> None:
        """JoinSpec round-trips through JSON correctly."""
        spec = JoinSpec(
            entity_type="spend",
            select=["spend", "cps"],
            source="data-service",
            factory="spend",
            period="T30",
            on="office_phone",
        )
        data = spec.model_dump()
        restored = JoinSpec(**data)
        assert restored == spec


# ---------------------------------------------------------------------------
# DataServiceJoinFetcher Tests
# ---------------------------------------------------------------------------


@dataclass
class FakeInsightsResponse:
    """Minimal mock for InsightsResponse.to_dataframe()."""

    df: pl.DataFrame

    def to_dataframe(self) -> pl.DataFrame:
        return self.df


@dataclass
class FakeBatchResult:
    """Minimal mock for BatchInsightsResult."""

    response: FakeInsightsResponse | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.response is not None and self.error is None


@dataclass
class FakeBatchResponse:
    """Minimal mock for BatchInsightsResponse."""

    results: dict[str, FakeBatchResult]
    success_count: int = 0
    failure_count: int = 0


class TestDataServiceJoinFetcher:
    """Test PVP extraction and batch fetching."""

    @pytest.fixture
    def primary_df(self) -> pl.DataFrame:
        """Primary DataFrame with offer-like structure."""
        return pl.DataFrame(
            {
                "gid": ["1", "2", "3", "4"],
                "name": ["A", "B", "C", "D"],
                "office_phone": [
                    "+17175551111",
                    "+17175552222",
                    "+17175553333",
                    "+17175551111",
                ],
                "vertical": ["dental", "chiropractic", "dental", "dental"],
                "section": ["Active", "Active", "Won", "Active"],
            }
        )

    @pytest.fixture
    def spend_df(self) -> pl.DataFrame:
        """Simulated data-service spend response."""
        return pl.DataFrame(
            {
                "office_phone": ["+17175551111", "+17175552222", "+17175553333"],
                "vertical": ["dental", "chiropractic", "dental"],
                "spend": [1000.0, 2000.0, 1500.0],
                "cps": [100.0, 200.0, 150.0],
                "leads": [10, 10, 10],
            }
        )

    @pytest.mark.asyncio
    async def test_basic_fetch(self, primary_df: pl.DataFrame, spend_df: pl.DataFrame) -> None:
        """Successful batch fetch returns combined DataFrame."""
        mock_client = AsyncMock()
        mock_client.get_insights_batch_async = AsyncMock(
            return_value=FakeBatchResponse(
                results={
                    "pv1:+17175551111:dental": FakeBatchResult(
                        response=FakeInsightsResponse(
                            df=spend_df.filter(pl.col("office_phone") == "+17175551111")
                        )
                    ),
                    "pv1:+17175552222:chiropractic": FakeBatchResult(
                        response=FakeInsightsResponse(
                            df=spend_df.filter(pl.col("office_phone") == "+17175552222")
                        )
                    ),
                    "pv1:+17175553333:dental": FakeBatchResult(
                        response=FakeInsightsResponse(
                            df=spend_df.filter(pl.col("office_phone") == "+17175553333")
                        )
                    ),
                },
                success_count=3,
                failure_count=0,
            )
        )

        fetcher = DataServiceJoinFetcher(mock_client)
        result = await fetcher.fetch_for_join(
            primary_df=primary_df,
            factory="spend",
            period="T30",
        )

        assert result.height == 3
        assert "spend" in result.columns
        assert "cps" in result.columns
        mock_client.get_insights_batch_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_pvp_deduplication(self, primary_df: pl.DataFrame) -> None:
        """Duplicate phone/vertical pairs are deduplicated before fetch."""
        mock_client = AsyncMock()
        mock_client.get_insights_batch_async = AsyncMock(
            return_value=FakeBatchResponse(results={}, success_count=0, failure_count=0)
        )

        fetcher = DataServiceJoinFetcher(mock_client)
        await fetcher.fetch_for_join(primary_df=primary_df, factory="spend", period="T30")

        # Primary has 4 rows but only 3 unique (phone, vertical) pairs
        call_args = mock_client.get_insights_batch_async.call_args
        pairs = call_args.kwargs.get("pairs") or call_args.args[0]
        assert len(pairs) == 3

    @pytest.mark.asyncio
    async def test_empty_primary_returns_empty(self) -> None:
        """Empty primary DataFrame returns empty result without calling client."""
        mock_client = AsyncMock()
        fetcher = DataServiceJoinFetcher(mock_client)
        result = await fetcher.fetch_for_join(
            primary_df=pl.DataFrame({"gid": [], "office_phone": []}),
            factory="spend",
            period="T30",
        )
        assert result.height == 0
        mock_client.get_insights_batch_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_join_key_returns_empty(self) -> None:
        """Primary without join key column returns empty."""
        mock_client = AsyncMock()
        fetcher = DataServiceJoinFetcher(mock_client)
        result = await fetcher.fetch_for_join(
            primary_df=pl.DataFrame({"gid": ["1"], "name": ["A"]}),
            factory="spend",
            period="T30",
        )
        assert result.height == 0
        mock_client.get_insights_batch_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_failures_returns_empty(self, primary_df: pl.DataFrame) -> None:
        """All batch failures return empty DataFrame."""
        mock_client = AsyncMock()
        mock_client.get_insights_batch_async = AsyncMock(
            return_value=FakeBatchResponse(
                results={
                    "pv1:+17175551111:dental": FakeBatchResult(error="timeout"),
                    "pv1:+17175552222:chiropractic": FakeBatchResult(error="timeout"),
                    "pv1:+17175553333:dental": FakeBatchResult(error="timeout"),
                },
                success_count=0,
                failure_count=3,
            )
        )

        fetcher = DataServiceJoinFetcher(mock_client)
        result = await fetcher.fetch_for_join(
            primary_df=primary_df,
            factory="spend",
            period="T30",
        )
        assert result.height == 0

    @pytest.mark.asyncio
    async def test_partial_success(self, primary_df: pl.DataFrame) -> None:
        """Partial batch success returns available data."""
        success_df = pl.DataFrame(
            {
                "office_phone": ["+17175551111"],
                "vertical": ["dental"],
                "spend": [1000.0],
            }
        )
        mock_client = AsyncMock()
        mock_client.get_insights_batch_async = AsyncMock(
            return_value=FakeBatchResponse(
                results={
                    "pv1:+17175551111:dental": FakeBatchResult(
                        response=FakeInsightsResponse(df=success_df)
                    ),
                    "pv1:+17175552222:chiropractic": FakeBatchResult(error="not found"),
                },
                success_count=1,
                failure_count=1,
            )
        )

        fetcher = DataServiceJoinFetcher(mock_client)
        result = await fetcher.fetch_for_join(
            primary_df=primary_df,
            factory="spend",
            period="T30",
        )
        assert result.height == 1
        assert result["office_phone"][0] == "+17175551111"

    @pytest.mark.asyncio
    async def test_no_vertical_column_uses_unknown(self) -> None:
        """Primary without vertical column uses 'unknown' as default."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2"],
                "office_phone": ["+17175551111", "+17175552222"],
            }
        )
        mock_client = AsyncMock()
        mock_client.get_insights_batch_async = AsyncMock(
            return_value=FakeBatchResponse(results={}, success_count=0, failure_count=0)
        )

        fetcher = DataServiceJoinFetcher(mock_client)
        await fetcher.fetch_for_join(primary_df=df, factory="spend", period="T30")

        call_args = mock_client.get_insights_batch_async.call_args
        pairs = call_args.kwargs.get("pairs") or call_args.args[0]
        assert len(pairs) == 2
        for pair in pairs:
            assert pair.vertical == "unknown"

    @pytest.mark.asyncio
    async def test_null_phones_skipped(self) -> None:
        """Null phone values are filtered out during PVP extraction."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "office_phone": ["+17175551111", None, "+17175553333"],
                "vertical": ["dental", "dental", "dental"],
            }
        )
        mock_client = AsyncMock()
        mock_client.get_insights_batch_async = AsyncMock(
            return_value=FakeBatchResponse(results={}, success_count=0, failure_count=0)
        )

        fetcher = DataServiceJoinFetcher(mock_client)
        await fetcher.fetch_for_join(primary_df=df, factory="spend", period="T30")

        call_args = mock_client.get_insights_batch_async.call_args
        pairs = call_args.kwargs.get("pairs") or call_args.args[0]
        assert len(pairs) == 2


# ---------------------------------------------------------------------------
# End-to-End Join with execute_join Tests
# ---------------------------------------------------------------------------


class TestDataServiceJoinExecution:
    """Test that data-service DataFrames work with execute_join()."""

    def test_basic_data_service_join(self) -> None:
        """Data-service DataFrame joins onto primary correctly."""
        primary = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", "B", "C"],
                "office_phone": ["+17175551111", "+17175552222", "+17175553333"],
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+17175551111", "+17175552222"],
                "spend": [1000.0, 2000.0],
                "cps": [100.0, 200.0],
            }
        )

        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["spend", "cps"],
            target_entity_type="spend",
        )

        assert result.df.height == 3
        assert "spend_spend" in result.df.columns
        assert "spend_cps" in result.df.columns
        assert result.matched_count == 2
        assert result.unmatched_count == 1

    def test_factory_name_prefix(self) -> None:
        """Columns are prefixed with factory name, not 'data-service'."""
        primary = pl.DataFrame({"gid": ["1"], "office_phone": ["+17175551111"]})
        target = pl.DataFrame({"office_phone": ["+17175551111"], "leads": [10]})

        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["leads"],
            target_entity_type="leads",
        )
        assert "leads_leads" in result.df.columns


# ---------------------------------------------------------------------------
# Virtual Entity Registry Tests
# ---------------------------------------------------------------------------


class TestDataServiceEntityRegistry:
    """Virtual entity registry for data-service join targets."""

    def test_known_entities_registered(self) -> None:
        """All 14 factories are registered."""
        all_factories = [
            "spend",
            "leads",
            "appts",
            "campaigns",
            "base",
            "account",
            "ads",
            "adsets",
            "targeting",
            "payments",
            "business_offers",
            "ad_questions",
            "ad_tests",
            "assets",
        ]
        for name in all_factories:
            info = get_data_service_entity(name)
            assert info is not None, f"Missing entity: {name}"
            assert info.factory == name

    def test_unknown_entity_returns_none(self) -> None:
        """Unknown entity returns None."""
        assert get_data_service_entity("nonexistent") is None

    def test_entity_has_required_fields(self) -> None:
        """Each entity has factory, columns, and join_key."""
        for name, info in DATA_SERVICE_ENTITIES.items():
            assert info.factory, f"{name}: missing factory"
            assert info.columns, f"{name}: missing columns"
            assert info.join_key, f"{name}: missing join_key"

    def test_list_entities_returns_all(self) -> None:
        """list_data_service_entities returns all registered entries."""
        entities = list_data_service_entities()
        assert len(entities) == len(DATA_SERVICE_ENTITIES)
        names = {e["name"] for e in entities}
        assert names == set(DATA_SERVICE_ENTITIES.keys())

    def test_default_join_key_is_office_phone(self) -> None:
        """All registered entities default to office_phone join key."""
        for name, info in DATA_SERVICE_ENTITIES.items():
            assert info.join_key == "office_phone", f"{name}: unexpected join_key"


# ---------------------------------------------------------------------------
# QueryEngine Data-Service Dispatch Tests
# ---------------------------------------------------------------------------


class TestQueryEngineDataServiceDispatch:
    """Test that QueryEngine routes data-service joins correctly."""

    @pytest.fixture
    def offer_df(self) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "gid": ["1", "2"],
                "name": ["Acme", "Beta"],
                "section": ["Active", "Active"],
                "office_phone": ["+17175551111", "+17175552222"],
                "vertical": ["dental", "chiropractic"],
                "mrr": ["100", "200"],
                "is_completed": [False, False],
            }
        )

    @pytest.fixture
    def mock_provider(self, offer_df: pl.DataFrame) -> MagicMock:
        provider = MagicMock()
        provider.get_dataframe = AsyncMock(return_value=offer_df)
        provider.last_freshness_info = None
        return provider

    @pytest.fixture
    def mock_data_client(self) -> AsyncMock:
        """Mock DataServiceClient that returns spend data."""
        spend_df = pl.DataFrame(
            {
                "office_phone": ["+17175551111", "+17175552222"],
                "vertical": ["dental", "chiropractic"],
                "spend": [1000.0, 2000.0],
            }
        )

        client = AsyncMock()
        client.get_insights_batch_async = AsyncMock(
            return_value=FakeBatchResponse(
                results={
                    "pv1:+17175551111:dental": FakeBatchResult(
                        response=FakeInsightsResponse(
                            df=spend_df.filter(pl.col("office_phone") == "+17175551111")
                        )
                    ),
                    "pv1:+17175552222:chiropractic": FakeBatchResult(
                        response=FakeInsightsResponse(
                            df=spend_df.filter(pl.col("office_phone") == "+17175552222")
                        )
                    ),
                },
                success_count=2,
                failure_count=0,
            )
        )
        return client

    @pytest.mark.asyncio
    async def test_data_service_join_dispatches(
        self,
        mock_provider: MagicMock,
        mock_data_client: AsyncMock,
        offer_df: pl.DataFrame,
    ) -> None:
        """Data-service join request routes through DataServiceJoinFetcher."""
        from autom8_asana.query.engine import QueryEngine
        from autom8_asana.query.models import RowsRequest

        engine = QueryEngine(provider=mock_provider, data_client=mock_data_client)
        request = RowsRequest(
            select=["gid", "name", "office_phone"],
            join=JoinSpec(
                entity_type="spend",
                select=["spend"],
                source="data-service",
                factory="spend",
                period="T30",
            ),
        )

        test_schema = MagicMock()
        test_schema.get_column = MagicMock(return_value=MagicMock())
        test_schema.column_names = MagicMock(
            return_value=[
                "gid",
                "name",
                "office_phone",
                "section",
                "mrr",
                "vertical",
                "is_completed",
            ]
        )

        with patch("autom8_asana.query.engine.SchemaRegistry.get_instance") as mock_registry:
            mock_registry.return_value.get_schema.return_value = test_schema

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="123",
                client=AsyncMock(),
                request=request,
            )

        assert result.meta.join_entity == "data-service:spend"
        assert result.meta.join_key == "office_phone"
        assert result.meta.join_matched == 2
        assert result.meta.join_unmatched == 0
        # Verify spend column is present with factory prefix
        if result.data:
            assert "spend_spend" in result.data[0]

    @pytest.mark.asyncio
    async def test_data_service_join_requires_data_client(self, mock_provider: MagicMock) -> None:
        """Data-service join without data_client raises JoinError."""
        from autom8_asana.query.engine import QueryEngine
        from autom8_asana.query.models import RowsRequest

        engine = QueryEngine(provider=mock_provider)  # No data_client
        request = RowsRequest(
            join=JoinSpec(
                entity_type="spend",
                select=["spend"],
                source="data-service",
                factory="spend",
            ),
        )

        test_schema = MagicMock()
        test_schema.get_column = MagicMock(return_value=MagicMock())

        with (
            patch("autom8_asana.query.engine.SchemaRegistry.get_instance") as mock_registry,
            pytest.raises(JoinError, match="data_client is required"),
        ):
            mock_registry.return_value.get_schema.return_value = test_schema
            await engine.execute_rows(
                entity_type="offer",
                project_gid="123",
                client=AsyncMock(),
                request=request,
            )

    @pytest.mark.asyncio
    async def test_data_service_join_empty_target(self, mock_provider: MagicMock) -> None:
        """Data-service join with empty response returns primary data with null join cols."""
        from autom8_asana.query.engine import QueryEngine
        from autom8_asana.query.models import RowsRequest

        empty_client = AsyncMock()
        empty_client.get_insights_batch_async = AsyncMock(
            return_value=FakeBatchResponse(
                results={},
                success_count=0,
                failure_count=0,
            )
        )

        engine = QueryEngine(provider=mock_provider, data_client=empty_client)
        request = RowsRequest(
            select=["gid", "name"],
            join=JoinSpec(
                entity_type="spend",
                select=["spend"],
                source="data-service",
                factory="spend",
            ),
        )

        test_schema = MagicMock()
        test_schema.get_column = MagicMock(return_value=MagicMock())

        with patch("autom8_asana.query.engine.SchemaRegistry.get_instance") as mock_registry:
            mock_registry.return_value.get_schema.return_value = test_schema

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="123",
                client=AsyncMock(),
                request=request,
            )

        # Primary rows preserved, join shows 0 matched
        assert result.meta.total_count == 2
        assert result.meta.join_matched == 0
        assert result.meta.join_unmatched == 2
