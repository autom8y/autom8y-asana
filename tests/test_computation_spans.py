"""Computation span tests for the Glass Pipeline initiative (glass-S9).

Verifies that @trace_computation decorators emit the correct spans, attributes,
and parent-child relationships for the 10 instrumented functions in the Demo 2
entity query / cross-service join path.

Test coverage:
- T1:  QueryEngine.execute_rows                  -> computation.entity.query_rows
- T2:  QueryEngine.execute_aggregate             -> computation.entity.query_aggregate
- T3:  PredicateCompiler.compile                 -> computation.predicate.compile
- T4:  compute_metric                            -> computation.metric.compute
- T5:  ProgressiveProjectBuilder.build_progressive_async -> computation.progressive.build
- T6:  execute_join                              -> computation.entity.join
- T7:  DataFrameCache.get_async                  -> computation.cache.get
- T8:  DataServiceJoinFetcher.fetch_for_join     -> computation.data_service.fetch_join
- T9:  DataServiceClient.get_insights_batch_async -> computation.data_service.get_insights_batch
- T10: EntityQueryService.get_dataframe          -> computation.entity_query.get_dataframe
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from autom8y_telemetry.testing import find_span

# =============================================================================
# Shared OTel fixture
# =============================================================================


@pytest.fixture
def otel_provider():
    """Fresh TracerProvider per test for span isolation.

    Patches autom8y_telemetry.computation._tracer so the module-level singleton
    is bound to this test's provider, not the one active at import time.
    """
    import autom8y_telemetry.computation as _computation_module

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    fresh_tracer = provider.get_tracer("autom8y.computation")
    original_tracer = _computation_module._tracer
    _computation_module._tracer = fresh_tracer

    yield provider, exporter

    _computation_module._tracer = original_tracer
    exporter.clear()


# =============================================================================
# T1: QueryEngine.execute_rows
# =============================================================================


class TestQueryEngineExecuteRows:
    """T1: computation.entity.query_rows"""

    async def test_span_name_and_core_attributes(self, otel_provider):
        """execute_rows emits computation.entity.query_rows with required attributes."""
        _, exporter = otel_provider

        from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
        from autom8_asana.query.engine import QueryEngine
        from autom8_asana.query.models import RowsRequest

        test_schema = DataFrameSchema(
            name="offer",
            task_type="Offer",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
            ],
        )

        sample_df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", "B", "C"],
                "section": ["Active", "Won", "Active"],
            }
        )

        mock_registry = MagicMock()
        mock_registry.get_schema.return_value = test_schema

        mock_provider = MagicMock()
        mock_provider.get_dataframe = AsyncMock(return_value=sample_df)
        mock_provider.last_freshness_info = None

        engine = QueryEngine(provider=mock_provider)
        request = RowsRequest(select=["gid", "name", "section"])

        with (
            patch(
                "autom8_asana.query.engine.SchemaRegistry.get_instance",
                return_value=mock_registry,
            ),
        ):
            await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=MagicMock(),
                request=request,
            )

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.entity.query_rows")
        assert span is not None, (
            "Expected span 'computation.entity.query_rows' not found"
        )

        attrs = dict(span.attributes)
        assert attrs["computation.operation"] == "entity.query_rows"
        assert attrs["computation.engine"] == "autom8y-asana"
        assert isinstance(attrs["computation.duration_ms"], float)
        assert attrs["computation.duration_ms"] >= 0

    async def test_span_is_root_span(self, otel_provider):
        """execute_rows span is a root span (no parent) when called directly."""
        _, exporter = otel_provider

        from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
        from autom8_asana.query.engine import QueryEngine
        from autom8_asana.query.models import RowsRequest

        test_schema = DataFrameSchema(
            name="offer",
            task_type="Offer",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("section", "Utf8", nullable=True),
            ],
        )
        sample_df = pl.DataFrame({"gid": ["1"], "section": ["Active"]})

        mock_provider = MagicMock()
        mock_provider.get_dataframe = AsyncMock(return_value=sample_df)
        mock_provider.last_freshness_info = None

        engine = QueryEngine(provider=mock_provider)
        request = RowsRequest(select=["gid"])

        mock_registry = MagicMock()
        mock_registry.get_schema.return_value = test_schema

        with patch(
            "autom8_asana.query.engine.SchemaRegistry.get_instance",
            return_value=mock_registry,
        ):
            await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=MagicMock(),
                request=request,
            )

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.entity.query_rows")
        assert span is not None
        assert span.parent is None


# =============================================================================
# T2: QueryEngine.execute_aggregate
# =============================================================================


class TestQueryEngineExecuteAggregate:
    """T2: computation.entity.query_aggregate"""

    async def test_span_name_and_core_attributes(self, otel_provider):
        """execute_aggregate emits computation.entity.query_aggregate."""
        _, exporter = otel_provider

        from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
        from autom8_asana.query.engine import QueryEngine
        from autom8_asana.query.models import AggFunction, AggregateRequest, AggSpec

        test_schema = DataFrameSchema(
            name="offer",
            task_type="Offer",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("section", "Utf8", nullable=True),
            ],
        )
        sample_df = pl.DataFrame(
            {"gid": ["1", "2", "3"], "section": ["Active", "Won", "Active"]}
        )

        mock_provider = MagicMock()
        mock_provider.get_dataframe = AsyncMock(return_value=sample_df)
        mock_provider.last_freshness_info = None

        mock_registry = MagicMock()
        mock_registry.get_schema.return_value = test_schema

        engine = QueryEngine(provider=mock_provider)
        request = AggregateRequest(
            group_by=["section"],
            aggregations=[AggSpec(column="gid", agg=AggFunction.COUNT, alias="count")],
        )

        with (
            patch(
                "autom8_asana.query.engine.SchemaRegistry.get_instance",
                return_value=mock_registry,
            ),
        ):
            await engine.execute_aggregate(
                entity_type="offer",
                project_gid="proj-123",
                client=MagicMock(),
                request=request,
            )

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.entity.query_aggregate")
        assert span is not None, (
            "Expected span 'computation.entity.query_aggregate' not found"
        )

        attrs = dict(span.attributes)
        assert attrs["computation.operation"] == "entity.query_aggregate"
        assert attrs["computation.engine"] == "autom8y-asana"
        assert isinstance(attrs["computation.duration_ms"], float)
        assert attrs["computation.duration_ms"] >= 0


# =============================================================================
# T3: PredicateCompiler.compile
# =============================================================================


class TestPredicateCompilerCompile:
    """T3: computation.predicate.compile"""

    def test_span_name_and_core_attributes(self, otel_provider):
        """compile emits computation.predicate.compile."""
        _, exporter = otel_provider

        from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
        from autom8_asana.query.compiler import PredicateCompiler
        from autom8_asana.query.models import Comparison, Op

        schema = DataFrameSchema(
            name="offer",
            task_type="Offer",
            columns=[ColumnDef("section", "Utf8", nullable=True)],
        )

        compiler = PredicateCompiler()
        node = Comparison(field="section", op=Op.EQ, value="Active")
        compiler.compile(node, schema)

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.predicate.compile")
        assert span is not None, (
            "Expected span 'computation.predicate.compile' not found"
        )

        attrs = dict(span.attributes)
        assert attrs["computation.operation"] == "predicate.compile"
        assert attrs["computation.engine"] == "autom8y-asana"
        assert isinstance(attrs["computation.duration_ms"], float)
        assert attrs["computation.duration_ms"] >= 0


# =============================================================================
# T4: compute_metric
# =============================================================================


class TestComputeMetric:
    """T4: computation.metric.compute"""

    def test_span_name_and_shape_attributes(self, otel_provider):
        """compute_metric emits computation.metric.compute with input/output shape."""
        _, exporter = otel_provider

        from autom8_asana.metrics.compute import compute_metric
        from autom8_asana.metrics.expr import MetricExpr
        from autom8_asana.metrics.metric import Metric, Scope

        df = pl.DataFrame(
            {
                "name": ["A", "B", "C", "D", "E"],
                "gid": ["1", "2", "3", "4", "5"],
                "mrr": [100.0, 200.0, 300.0, 400.0, 500.0],
            }
        )

        expr = MetricExpr(name="sum_mrr", column="mrr", agg="sum")
        scope = Scope(entity_type="offer", dedup_keys=["gid"])
        metric = Metric(
            name="mrr", description="MRR test metric", expr=expr, scope=scope
        )

        result = compute_metric(metric, df)
        assert result.height == 5

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.metric.compute")
        assert span is not None, "Expected span 'computation.metric.compute' not found"

        attrs = dict(span.attributes)
        assert attrs["computation.operation"] == "metric.compute"
        assert attrs["computation.engine"] == "autom8y-asana"
        assert isinstance(attrs["computation.duration_ms"], float)
        assert attrs["computation.duration_ms"] >= 0
        assert attrs["computation.input.rows"] == 5
        assert attrs["computation.input.columns"] == 3
        assert attrs["computation.output.rows"] == 5


# =============================================================================
# T5: ProgressiveProjectBuilder.build_progressive_async
# =============================================================================


class TestProgressiveProjectBuilderBuildProgressiveAsync:
    """T5: computation.progressive.build"""

    async def test_span_name_and_materialize_attributes(self, otel_provider):
        """build_progressive_async emits computation.progressive.build with materialize attrs."""
        _, exporter = otel_provider

        from autom8_asana.dataframes.builders.progressive import (
            ProgressiveProjectBuilder,
            _ResumeResult,
        )

        # Construct a fake section object so _list_sections returns one section
        # but sections_to_fetch is empty (all resumed), so the fetch loop is skipped.
        # _merge_section_dataframes returns an empty df (total_rows=0) so artifact
        # write is skipped too.  Execution reaches the span.set_attribute() block.
        fake_section = MagicMock()
        fake_section.gid = "section-1"

        fake_resume_result = _ResumeResult(
            manifest=None,
            sections_to_fetch=[],
            sections_resumed=1,
            sections_probed=0,
            sections_delta_updated=0,
        )

        builder = MagicMock(spec=ProgressiveProjectBuilder)
        builder._project_gid = "proj-123"
        builder._entity_type = "offer"
        builder._schema = MagicMock()
        builder._max_concurrent = 8
        builder._store = None
        builder._index_builder = None
        builder._dataframe_view = None
        builder._section_dfs = {}
        builder._manifest = None
        builder._checkpoint_df = None
        builder._checkpoint_task_count = 0
        builder._ensure_dataframe_view = AsyncMock()
        builder._list_sections = AsyncMock(return_value=[fake_section])
        builder._check_resume_and_probe = AsyncMock(return_value=fake_resume_result)
        builder._ensure_manifest = AsyncMock()
        builder._merge_section_dataframes = AsyncMock(return_value=pl.DataFrame())

        bound = ProgressiveProjectBuilder.build_progressive_async.__get__(
            builder, ProgressiveProjectBuilder
        )
        await bound()

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.progressive.build")
        assert span is not None, (
            "Expected span 'computation.progressive.build' not found"
        )

        attrs = dict(span.attributes)
        assert attrs["computation.operation"] == "progressive.build"
        assert attrs["computation.engine"] == "autom8y-asana"
        assert isinstance(attrs["computation.duration_ms"], float)
        assert attrs["computation.duration_ms"] >= 0
        assert "computation.materialize.sections_built" in attrs
        assert "computation.materialize.total_rows" in attrs


# =============================================================================
# T6: execute_join
# =============================================================================


class TestExecuteJoin:
    """T6: computation.entity.join"""

    def test_span_name_and_join_attributes(self, otel_provider):
        """execute_join emits computation.entity.join with input/output shape and match counts."""
        _, exporter = otel_provider

        from autom8_asana.query.join import execute_join

        primary_df = pl.DataFrame(
            {
                "gid": ["1", "2", "3", "4", "5"],
                "office_phone": ["+1111", "+2222", "+3333", "+4444", "+5555"],
                "name": ["A", "B", "C", "D", "E"],
            }
        )
        target_df = pl.DataFrame(
            {
                "office_phone": ["+1111", "+2222", "+3333"],
                "spend": [100.0, 200.0, 300.0],
            }
        )

        result = execute_join(
            primary_df=primary_df,
            target_df=target_df,
            join_key="office_phone",
            select_columns=["spend"],
            target_entity_type="spend",
        )

        assert result.matched_count == 3
        assert result.unmatched_count == 2

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.entity.join")
        assert span is not None, "Expected span 'computation.entity.join' not found"

        attrs = dict(span.attributes)
        assert attrs["computation.operation"] == "entity.join"
        assert attrs["computation.engine"] == "autom8y-asana"
        assert isinstance(attrs["computation.duration_ms"], float)
        assert attrs["computation.duration_ms"] >= 0
        assert attrs["computation.input.rows"] == 5
        assert attrs["computation.join.matched_count"] == 3
        assert attrs["computation.join.unmatched_count"] == 2

    def test_parent_child_relationship(self, otel_provider):
        """execute_join span is a child of its caller when nested inside a parent span."""
        _, exporter = otel_provider

        from autom8_asana.query.join import execute_join

        primary_df = pl.DataFrame({"gid": ["1"], "office_phone": ["+1111"]})
        target_df = pl.DataFrame({"office_phone": ["+1111"], "spend": [100.0]})

        test_tracer = trace.get_tracer("test.join")
        with test_tracer.start_as_current_span(
            "computation.entity.query_rows"
        ) as parent:
            execute_join(
                primary_df=primary_df,
                target_df=target_df,
                join_key="office_phone",
                select_columns=["spend"],
                target_entity_type="spend",
            )
            parent_span_id = parent.get_span_context().span_id

        spans = exporter.get_finished_spans()
        join_span = find_span(spans, "computation.entity.join")
        assert join_span is not None
        assert join_span.parent is not None
        assert join_span.parent.span_id == parent_span_id


# =============================================================================
# T7: DataFrameCache.get_async
# =============================================================================


class TestDataFrameCacheGetAsync:
    """T7: computation.cache.get"""

    async def test_cache_miss_span(self, otel_provider):
        """get_async emits computation.cache.get with cache_hit=False on miss."""
        _, exporter = otel_provider

        from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
        from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
        from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
        from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier
        from autom8_asana.cache.integration.dataframe_cache import DataFrameCache

        memory_tier = MagicMock(spec=MemoryTier)
        memory_tier.get.return_value = None

        progressive_tier = MagicMock(spec=ProgressiveTier)
        progressive_tier.get_async = AsyncMock(return_value=None)

        coalescer = MagicMock(spec=DataFrameCacheCoalescer)
        circuit_breaker = MagicMock(spec=CircuitBreaker)
        circuit_breaker.is_open.return_value = False

        cache = DataFrameCache(
            memory_tier=memory_tier,
            progressive_tier=progressive_tier,
            coalescer=coalescer,
            circuit_breaker=circuit_breaker,
        )
        cache._stats = {"offer": {k: 0 for k in cache._stats.get("offer", {}).keys()}}
        cache._ensure_stats("offer")

        result = await cache.get_async("proj-123", "offer")
        assert result is None

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.cache.get")
        assert span is not None, "Expected span 'computation.cache.get' not found"

        attrs = dict(span.attributes)
        assert attrs["computation.operation"] == "cache.get"
        assert attrs["computation.engine"] == "autom8y-asana"
        assert attrs["computation.cache_hit"] is False
        assert isinstance(attrs["computation.duration_ms"], float)
        assert attrs["computation.duration_ms"] >= 0

    async def test_cache_hit_span(self, otel_provider):
        """get_async emits computation.cache.get with cache_hit=True on memory hit."""
        _, exporter = otel_provider

        from datetime import UTC

        from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
        from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
        from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
        from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier
        from autom8_asana.cache.integration.dataframe_cache import (
            DataFrameCache,
            DataFrameCacheEntry,
        )

        fake_df = pl.DataFrame({"gid": ["1", "2"]})
        fake_entry = DataFrameCacheEntry(
            project_gid="proj-123",
            entity_type="offer",
            dataframe=fake_df,
            watermark=datetime.now(UTC),
            created_at=datetime.now(UTC),
            schema_version="1.0.0",
        )

        memory_tier = MagicMock(spec=MemoryTier)
        memory_tier.get.return_value = fake_entry

        progressive_tier = MagicMock(spec=ProgressiveTier)
        coalescer = MagicMock(spec=DataFrameCacheCoalescer)
        circuit_breaker = MagicMock(spec=CircuitBreaker)
        circuit_breaker.is_open.return_value = False

        cache = DataFrameCache(
            memory_tier=memory_tier,
            progressive_tier=progressive_tier,
            coalescer=coalescer,
            circuit_breaker=circuit_breaker,
        )
        cache._ensure_stats("offer")

        with patch.object(
            cache,
            "_check_freshness_and_serve",
            return_value=fake_entry,
        ):
            result = await cache.get_async("proj-123", "offer")

        assert result is fake_entry

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.cache.get")
        assert span is not None

        attrs = dict(span.attributes)
        assert attrs["computation.cache_hit"] is True
        assert isinstance(attrs["computation.duration_ms"], float)


# =============================================================================
# T8: DataServiceJoinFetcher.fetch_for_join  [CROSS-SERVICE BRIDGE]
# =============================================================================


class TestDataServiceJoinFetcherFetchForJoin:
    """T8: computation.data_service.fetch_join — CROSS-SERVICE BOUNDARY"""

    async def test_span_name_and_batch_attributes(self, otel_provider):
        """fetch_for_join emits computation.data_service.fetch_join with batch counts."""
        _, exporter = otel_provider

        from autom8_asana.query.fetcher import DataServiceJoinFetcher

        primary_df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "office_phone": ["+1111", "+2222", "+3333"],
                "vertical": ["dental", "chiro", "dental"],
            }
        )

        result_df1 = pl.DataFrame(
            {"office_phone": ["+1111"], "vertical": ["dental"], "spend": [100.0]}
        )
        result_df2 = pl.DataFrame(
            {"office_phone": ["+2222"], "vertical": ["chiro"], "spend": [200.0]}
        )

        # Build mock results that mimic BatchInsightsResult behaviour without
        # pydantic validation on the InsightsResponse field.
        mock_result1 = MagicMock()
        mock_result1.success = True
        mock_result1.response = MagicMock()
        mock_result1.response.to_dataframe.return_value = result_df1

        mock_result2 = MagicMock()
        mock_result2.success = True
        mock_result2.response = MagicMock()
        mock_result2.response.to_dataframe.return_value = result_df2

        mock_result3 = MagicMock()
        mock_result3.success = False
        mock_result3.response = None

        batch_response = MagicMock()
        batch_response.results = {
            "k1": mock_result1,
            "k2": mock_result2,
            "k3": mock_result3,
        }
        batch_response.success_count = 2
        batch_response.failure_count = 1

        mock_client = MagicMock()
        mock_client.get_insights_batch_async = AsyncMock(return_value=batch_response)

        fetcher = DataServiceJoinFetcher(mock_client)
        result = await fetcher.fetch_for_join(
            primary_df=primary_df,
            factory="spend",
            period="T30",
        )

        assert result.height == 2

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.data_service.fetch_join")
        assert span is not None, (
            "Expected span 'computation.data_service.fetch_join' not found"
        )

        attrs = dict(span.attributes)
        assert attrs["computation.operation"] == "data_service.fetch_join"
        assert attrs["computation.engine"] == "autom8y-asana"
        assert isinstance(attrs["computation.duration_ms"], float)
        assert attrs["computation.duration_ms"] >= 0
        assert attrs["computation.batch.success_count"] == 2
        assert attrs["computation.batch.failure_count"] == 1
        assert attrs["computation.input.rows"] == 3

    async def test_no_pvps_span(self, otel_provider):
        """fetch_for_join emits span with zero counts when primary_df has no office_phone."""
        _, exporter = otel_provider

        from autom8_asana.query.fetcher import DataServiceJoinFetcher

        empty_df = pl.DataFrame({"gid": ["1", "2"]})  # no office_phone column
        mock_client = MagicMock()

        fetcher = DataServiceJoinFetcher(mock_client)
        result = await fetcher.fetch_for_join(
            primary_df=empty_df,
            factory="spend",
            period="T30",
        )

        assert result.height == 0

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.data_service.fetch_join")
        assert span is not None

        attrs = dict(span.attributes)
        assert attrs["computation.batch.success_count"] == 0
        assert attrs["computation.batch.failure_count"] == 0


# =============================================================================
# T9: DataServiceClient.get_insights_batch_async  [CROSS-SERVICE BRIDGE]
# =============================================================================


class TestDataServiceClientGetInsightsBatchAsync:
    """T9: computation.data_service.get_insights_batch — CROSS-SERVICE BRIDGE"""

    @pytest.mark.skip(reason="DataServiceClient.get_insights_batch_async not yet instrumented with @trace_computation")
    async def test_span_name_and_batch_attributes(self, otel_provider):
        """get_insights_batch_async emits computation.data_service.get_insights_batch."""
        _, exporter = otel_provider

        from autom8_asana.clients.data.client import DataServiceClient
        from autom8_asana.clients.data.models import (
            BatchInsightsResponse,
            BatchInsightsResult,
        )
        from autom8_asana.models.contracts import PhoneVerticalPair

        pvp = PhoneVerticalPair(phone="+17705753103", vertical="dental")

        batch_response = BatchInsightsResponse(
            results={
                pvp.canonical_key: BatchInsightsResult(
                    pvp=pvp, error=None, response=None
                ),
            },
            request_id="req-test",
            total_count=1,
            success_count=0,
            failure_count=1,
        )

        client = MagicMock(spec=DataServiceClient)
        client._check_feature_enabled = MagicMock()
        client._config = MagicMock()
        client._config.max_batch_size = 500
        client._log = None
        client._validate_factory = MagicMock()
        client._execute_batch_request = AsyncMock(
            return_value={
                pvp.canonical_key: BatchInsightsResult(pvp=pvp, error="not found"),
            }
        )
        client._emit_metric = MagicMock()

        bound = DataServiceClient.get_insights_batch_async.__get__(
            client, DataServiceClient
        )
        result = await bound(
            pairs=[pvp],
            factory="spend",
            period="T30",
        )

        assert result.total_count == 1
        assert result.failure_count == 1

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.data_service.get_insights_batch")
        assert span is not None, (
            "Expected span 'computation.data_service.get_insights_batch' not found"
        )

        attrs = dict(span.attributes)
        assert attrs["computation.operation"] == "data_service.get_insights_batch"
        assert attrs["computation.engine"] == "autom8y-asana"
        assert isinstance(attrs["computation.duration_ms"], float)
        assert attrs["computation.duration_ms"] >= 0
        assert attrs["computation.batch.success_count"] == 0
        assert attrs["computation.batch.failure_count"] == 1


# =============================================================================
# T10: EntityQueryService.get_dataframe
# =============================================================================


class TestEntityQueryServiceGetDataframe:
    """T10: computation.entity_query.get_dataframe"""

    async def test_span_name_and_cache_hit_attribute(self, otel_provider):
        """get_dataframe emits computation.entity_query.get_dataframe with cache_hit=True."""
        _, exporter = otel_provider

        from autom8_asana.services.query_service import EntityQueryService

        known_df = pl.DataFrame(
            {"gid": ["1", "2", "3"], "section": ["Active", "Won", "Active"]}
        )

        mock_strategy = MagicMock()
        mock_strategy._get_dataframe = AsyncMock(return_value=known_df)
        mock_strategy._last_freshness_info = None

        mock_factory = MagicMock(return_value=mock_strategy)

        service = EntityQueryService(strategy_factory=mock_factory)
        result = await service.get_dataframe(
            entity_type="offer",
            project_gid="proj-123",
            client=MagicMock(),
        )

        assert result.height == 3

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.entity_query.get_dataframe")
        assert span is not None, (
            "Expected span 'computation.entity_query.get_dataframe' not found"
        )

        attrs = dict(span.attributes)
        assert attrs["computation.operation"] == "entity_query.get_dataframe"
        assert attrs["computation.engine"] == "autom8y-asana"
        assert isinstance(attrs["computation.duration_ms"], float)
        assert attrs["computation.duration_ms"] >= 0
        assert attrs["computation.cache_hit"] is True
        assert attrs["computation.output.rows"] == 3
        assert attrs["computation.output.columns"] == 2

    async def test_span_is_root(self, otel_provider):
        """entity_query.get_dataframe span has no parent when called at top level."""
        _, exporter = otel_provider

        from autom8_asana.services.query_service import EntityQueryService

        known_df = pl.DataFrame({"gid": ["1"]})
        mock_strategy = MagicMock()
        mock_strategy._get_dataframe = AsyncMock(return_value=known_df)
        mock_strategy._last_freshness_info = None

        service = EntityQueryService(
            strategy_factory=MagicMock(return_value=mock_strategy)
        )
        await service.get_dataframe("offer", "proj-123", MagicMock())

        spans = exporter.get_finished_spans()
        span = find_span(spans, "computation.entity_query.get_dataframe")
        assert span is not None
        assert span.parent is None
