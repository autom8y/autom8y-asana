"""QueryEngine: orchestrates filtered row retrieval.

Composes cache access, schema validation, predicate compilation,
section scoping, and response shaping.

Per R-010 (WS-QUERY): Accepts a DataFrameProvider protocol instead of
importing EntityQueryService directly, decoupling the query engine
(computational) from the services layer (orchestration).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger
from autom8y_telemetry import trace_computation

from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.query.compiler import PredicateCompiler
from autom8_asana.query.errors import (
    AggregateGroupLimitError,
    ClassificationError,
    JoinError,
    UnknownFieldError,
    UnknownSectionError,
)
from autom8_asana.query.guards import QueryLimits, predicate_depth
from autom8_asana.query.hierarchy import (
    find_relationship,
    get_join_key,
    get_joinable_types,
)
from autom8_asana.query.join import execute_join
from autom8_asana.query.models import (
    AggregateMeta,
    AggregateRequest,
    AggregateResponse,
    RowsMeta,
    RowsRequest,
    RowsResponse,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.metrics.resolve import SectionIndex
    from autom8_asana.protocols.dataframe_provider import DataFrameProvider

logger = get_logger(__name__)


def _to_pascal_case(s: str) -> str:
    """Convert snake_case to PascalCase for schema key lookup."""
    return "".join(word.capitalize() for word in s.split("_"))


@dataclass
class QueryEngine:
    """Orchestrates filtered row retrieval.

    Composes cache access, schema validation, predicate compilation,
    section scoping, and response shaping.

    Per R-010 (WS-QUERY): Accepts a DataFrameProvider protocol for
    DataFrame retrieval, decoupling from the services layer.
    """

    provider: DataFrameProvider
    compiler: PredicateCompiler = field(default_factory=PredicateCompiler)
    limits: QueryLimits = field(default_factory=QueryLimits)
    data_client: DataServiceClient | None = None  # For cross-service joins

    @trace_computation("entity.query_rows", record_dataframe_shape=True, engine="autom8y-asana")
    async def execute_rows(
        self,
        entity_type: str,
        project_gid: str,
        client: AsanaClient,
        request: RowsRequest,
        section_index: SectionIndex | None = None,
        entity_project_registry: Any = None,
    ) -> RowsResponse:
        """Execute a /rows query.

        Flow:
        1. Validate predicate depth (fail-fast guard).
        2. Resolve section parameter to name filter.
        3. Load DataFrame via DataFrameProvider.get_dataframe().
        4. Compile predicate AST to pl.Expr.
        5. Apply section filter + predicate filter.
        6. Apply pagination (offset/limit clamped to MAX_RESULT_ROWS).
        7. Select columns (gid always included).
        8. Build response with metadata.

        Args:
            entity_type: Entity type to query.
            project_gid: Project GID for cache lookup.
            client: AsanaClient for potential cache build.
            request: Validated RowsRequest.
            section_index: Pre-built section index (optional, built if needed).

        Returns:
            RowsResponse with data and metadata.

        Raises:
            QueryEngineError subclass for all domain errors.
            CacheNotWarmError if DataFrame unavailable.
        """
        from opentelemetry import trace as _otel_trace

        _span = _otel_trace.get_current_span()
        start = time.monotonic()

        # 1. Depth guard (before any I/O)
        if request.where is not None:
            depth = predicate_depth(request.where)
            self.limits.check_depth(depth)

        # 2. Resolve classification to section IN predicate
        classification_sections = self._resolve_classification(
            request.classification, entity_type
        )

        # 3. Resolve section
        section_name_filter = self._resolve_section(
            request.section, entity_type, section_index
        )

        # 4. Load DataFrame
        df = await self.provider.get_dataframe(
            entity_type,
            project_gid,
            client,
        )

        # 5. Get schema for validation
        registry = SchemaRegistry.get_instance()
        schema = registry.get_schema(_to_pascal_case(entity_type))

        # 6. Build filter expression
        filter_expr: pl.Expr | None = None
        if request.where is not None:
            filter_expr = self.compiler.compile(request.where, schema)

        # 7. Apply classification filter (case-insensitive IN predicate)
        if classification_sections is not None:
            classification_expr = (
                pl.col("section")
                .str.to_lowercase()
                .is_in(list(classification_sections))
            )
            if filter_expr is not None:
                filter_expr = classification_expr & filter_expr
            else:
                filter_expr = classification_expr

        # 7.5. Apply section filter (ANDed with predicate)
        if section_name_filter is not None:
            section_expr = pl.col("section") == section_name_filter
            if filter_expr is not None:
                filter_expr = section_expr & filter_expr
            else:
                filter_expr = section_expr

        # 7. Apply filter
        if filter_expr is not None:
            df = df.filter(filter_expr)

        # 7.5 Join enrichment (after filter, before pagination)
        join_meta: dict[str, object] = {}
        if request.join is not None:
            if request.join.source == "data-service":
                # Cross-service join via DataServiceClient
                df, join_meta = await self._execute_data_service_join(df, request.join)
            else:
                # Entity join (existing path)
                df, join_meta = await self._execute_entity_join(
                    df,
                    request.join,
                    entity_type,
                    registry,
                    client,
                    entity_project_registry,
                )

        # 8. Total count (before pagination)
        total_count = len(df)

        # 9. Clamp limit to MAX_RESULT_ROWS
        effective_limit = self.limits.clamp_limit(request.limit)

        # 10. Pagination
        df = df.slice(request.offset, effective_limit)

        # 11. Select columns (gid always included per PRD)
        select_fields = request.select or ["gid", "name", "section"]

        # Validate select fields against schema
        for col_name in select_fields:
            if schema.get_column(col_name) is None:
                raise UnknownFieldError(
                    field=col_name,
                    available=schema.column_names(),
                )

        columns = list(dict.fromkeys(["gid"] + select_fields))  # dedupe, preserve order

        # Include join-enriched columns (prefixed with target entity type or factory)
        if request.join is not None:
            # Data-service joins use factory as prefix; entity joins use entity_type
            prefix = (
                request.join.factory
                if request.join.source == "data-service"
                else request.join.entity_type
            )
            for col_name in request.join.select:
                prefixed = f"{prefix}_{col_name}"
                if prefixed not in columns:
                    columns.append(prefixed)

        available = set(df.columns)
        valid_columns = [c for c in columns if c in available]
        df = df.select(valid_columns)

        # 12. Build response
        elapsed_ms = (time.monotonic() - start) * 1000
        _span.set_attribute("computation.duration_ms", elapsed_ms)
        data = df.to_dicts()

        # Read freshness info from query_service side-channel
        freshness_meta = self._get_freshness_meta()

        return RowsResponse(
            data=data,
            meta=RowsMeta(
                total_count=total_count,
                returned_count=len(data),
                limit=effective_limit,
                offset=request.offset,
                entity_type=entity_type,
                project_gid=project_gid,
                query_ms=round(elapsed_ms, 2),
                **join_meta,  # type: ignore[arg-type]
                **freshness_meta,  # type: ignore[arg-type]
            ),
        )

    @trace_computation("entity.query_aggregate", record_dataframe_shape=True, engine="autom8y-asana")
    async def execute_aggregate(
        self,
        entity_type: str,
        project_gid: str,
        client: AsanaClient,
        request: AggregateRequest,
        section_index: SectionIndex | None = None,
    ) -> AggregateResponse:
        """Execute an /aggregate query.

        Flow:
        1. Validate predicate depth for WHERE (fail-fast guard).
        2. Validate predicate depth for HAVING (fail-fast guard).
        3. Resolve section parameter to name filter.
        4. Load DataFrame via DataFrameProvider.get_dataframe().
        5. Get schema, validate group_by columns exist + not List dtype.
        6. Validate aggregation specs (column existence + dtype compatibility).
        7. Apply WHERE filter (reuse PredicateCompiler).
        8. Execute group_by().agg() with compiled expressions.
        9. Apply HAVING filter (PredicateCompiler on post-agg schema).
        10. Build response with metadata.

        Args:
            entity_type: Entity type to query.
            project_gid: Project GID for cache lookup.
            client: AsanaClient for potential cache build.
            request: Validated AggregateRequest.
            section_index: Pre-built section index (optional).

        Returns:
            AggregateResponse with grouped data and metadata.

        Raises:
            QueryEngineError subclass for all domain errors.
            CacheNotWarmError if DataFrame unavailable.
        """
        from opentelemetry import trace as _otel_trace

        _span = _otel_trace.get_current_span()
        start = time.monotonic()

        # 1. Depth guard for WHERE
        if request.where is not None:
            depth = predicate_depth(request.where)
            self.limits.check_depth(depth)

        # 2. Depth guard for HAVING
        if request.having is not None:
            depth = predicate_depth(request.having)
            self.limits.check_depth(depth)

        # 3. Resolve section (same pattern as execute_rows)
        section_name_filter = self._resolve_section(
            request.section, entity_type, section_index
        )

        # 4. Load DataFrame
        df = await self.provider.get_dataframe(
            entity_type,
            project_gid,
            client,
        )

        # 5. Get schema for validation
        registry = SchemaRegistry.get_instance()
        schema = registry.get_schema(_to_pascal_case(entity_type))

        # 6. Validate group_by columns
        self.limits.check_group_by(request.group_by, schema)

        # 7. Compile and apply WHERE filter
        filter_expr: pl.Expr | None = None
        if request.where is not None:
            filter_expr = self.compiler.compile(request.where, schema)

        if section_name_filter is not None:
            section_expr = pl.col("section") == section_name_filter
            if filter_expr is not None:
                filter_expr = section_expr & filter_expr
            else:
                filter_expr = section_expr

        if filter_expr is not None:
            df = df.filter(filter_expr)

        # 8. Validate alias uniqueness and compile aggregation expressions
        from autom8_asana.query.aggregator import (
            AggregationCompiler,
            build_post_agg_schema,
            validate_alias_uniqueness,
        )

        validate_alias_uniqueness(request.aggregations, request.group_by)
        agg_compiler = AggregationCompiler()
        agg_exprs = agg_compiler.compile(request.aggregations, schema)

        # 9. Execute group_by().agg()
        result_df = df.group_by(request.group_by).agg(agg_exprs)

        # 10. Apply HAVING filter
        if request.having is not None:
            post_agg_schema = build_post_agg_schema(
                group_by_columns=request.group_by,
                agg_specs=request.aggregations,
                source_schema=schema,
            )
            having_expr = self.compiler.compile(request.having, post_agg_schema)
            result_df = result_df.filter(having_expr)

        # 11. Check group count guard (ADR-AGG-006, after HAVING)
        group_count = len(result_df)
        if group_count > self.limits.max_aggregate_groups:
            raise AggregateGroupLimitError(
                group_count=group_count,
                max_groups=self.limits.max_aggregate_groups,
            )

        # 12. Build response
        elapsed_ms = (time.monotonic() - start) * 1000
        _span.set_attribute("computation.duration_ms", elapsed_ms)
        data = result_df.to_dicts()

        # Read freshness info from query_service side-channel
        freshness_meta = self._get_freshness_meta()

        return AggregateResponse(
            data=data,
            meta=AggregateMeta(
                group_count=group_count,
                aggregation_count=len(request.aggregations),
                group_by=request.group_by,
                entity_type=entity_type,
                project_gid=project_gid,
                query_ms=round(elapsed_ms, 2),
                **freshness_meta,  # type: ignore[arg-type]
            ),
        )

    def _resolve_classification(
        self,
        classification: str | None,
        entity_type: str,
    ) -> frozenset[str] | None:
        """Resolve classification parameter to a set of section names.

        Uses SectionClassifier to expand a classification value (e.g., "active")
        into the set of section names belonging to that classification group.

        Returns:
            Frozenset of lowercase section names if classification was provided,
            None otherwise.

        Raises:
            ClassificationError: If no classifier exists for entity_type or
                classification is not a valid AccountActivity value.
        """
        if classification is None:
            return None

        from autom8_asana.models.business.activity import (
            CLASSIFIERS,
            AccountActivity,
        )

        classifier = CLASSIFIERS.get(entity_type)
        if classifier is None:
            available = sorted(CLASSIFIERS.keys())
            raise ClassificationError(
                f"No classifier registered for entity type '{entity_type}'. "
                f"Classification filtering is available for: {available}"
            )

        try:
            activity = AccountActivity(classification.lower())
        except ValueError:
            valid_values = [a.value for a in AccountActivity]
            raise ClassificationError(
                f"Invalid classification value: '{classification}'. "
                f"Valid values: {valid_values}"
            ) from None

        sections = classifier.sections_for(activity)
        if not sections:
            logger.warning(
                "classification_empty_sections",
                extra={
                    "entity_type": entity_type,
                    "classification": classification,
                },
            )

        return sections

    def _resolve_section(
        self,
        section: str | None,
        entity_type: str,
        section_index: SectionIndex | None,
    ) -> str | None:
        """Resolve section parameter to section name filter.

        Returns:
            Section name string if section was provided, None otherwise.

        Raises:
            UnknownSectionError: If section cannot be resolved.
        """
        if section is None:
            return None
        if section_index is None:
            from autom8_asana.metrics.resolve import SectionIndex as _SectionIndex

            section_index = _SectionIndex.from_enum_fallback(entity_type)
        resolved_gid = section_index.resolve(section)
        if resolved_gid is None:
            raise UnknownSectionError(section=section)
        return section

    def _get_freshness_meta(self) -> dict[str, object]:
        """Read freshness info from the DataFrameProvider."""
        freshness_info = self.provider.last_freshness_info
        if freshness_info is None:
            return {}
        return {
            "freshness": freshness_info.freshness,
            "data_age_seconds": freshness_info.data_age_seconds,
            "staleness_ratio": freshness_info.staleness_ratio,
        }

    async def _execute_entity_join(
        self,
        df: pl.DataFrame,
        join_spec: Any,
        entity_type: str,
        registry: SchemaRegistry,
        client: AsanaClient,
        entity_project_registry: Any,
    ) -> tuple[pl.DataFrame, dict[str, object]]:
        """Execute a same-service entity join (existing behavior).

        Returns:
            Tuple of (enriched DataFrame, join metadata dict).
        """
        # Validate relationship exists
        rel = find_relationship(entity_type, join_spec.entity_type)
        if rel is None:
            raise JoinError(
                f"No relationship between '{entity_type}' and "
                f"'{join_spec.entity_type}'. "
                f"Joinable types: {get_joinable_types(entity_type)}"
            )

        # Validate join target columns against target schema
        target_schema = registry.get_schema(_to_pascal_case(join_spec.entity_type))
        for col_name in join_spec.select:
            if target_schema.get_column(col_name) is None:
                raise UnknownFieldError(
                    field=col_name,
                    available=target_schema.column_names(),
                )

        # Determine join key
        join_key = get_join_key(
            entity_type,
            join_spec.entity_type,
            join_spec.on,
        )

        # Load target entity DataFrame
        if entity_project_registry is None:
            raise JoinError("entity_project_registry is required for join operations")

        target_project_gid = entity_project_registry.get_project_gid(
            join_spec.entity_type
        )
        if target_project_gid is None:
            raise JoinError(
                f"No project configured for join target: {join_spec.entity_type}"
            )

        target_df = await self.provider.get_dataframe(
            join_spec.entity_type,
            target_project_gid,
            client,
        )

        if join_key is None:
            raise JoinError(
                f"No join key found between {entity_type} and {join_spec.entity_type}"
            )

        # Execute join
        join_result = execute_join(
            primary_df=df,
            target_df=target_df,
            join_key=join_key,
            select_columns=join_spec.select,
            target_entity_type=join_spec.entity_type,
        )
        return join_result.df, {
            "join_entity": join_spec.entity_type,
            "join_key": join_result.join_key,
            "join_matched": join_result.matched_count,
            "join_unmatched": join_result.unmatched_count,
        }

    async def _execute_data_service_join(
        self,
        df: pl.DataFrame,
        join_spec: Any,
    ) -> tuple[pl.DataFrame, dict[str, object]]:
        """Execute a cross-service join via DataServiceClient.

        Fetches analytics metrics from autom8y-data and joins them onto
        the primary entity DataFrame.

        Returns:
            Tuple of (enriched DataFrame, join metadata dict).

        Raises:
            JoinError: If no DataServiceClient is configured or join key
                is not found in the primary DataFrame.
        """
        if self.data_client is None:
            raise JoinError(
                "data_client is required for data-service joins. "
                "Ensure DataServiceClient is configured."
            )

        from autom8_asana.query.data_service_entities import (
            get_data_service_entity,
        )
        from autom8_asana.query.fetcher import DataServiceJoinFetcher

        # Resolve join key (explicit or default from virtual entity registry)
        join_key = join_spec.on
        if join_key is None:
            entity_info = get_data_service_entity(join_spec.entity_type)
            join_key = entity_info.join_key if entity_info else "office_phone"

        # Validate select columns against virtual entity registry (advisory)
        entity_info = get_data_service_entity(join_spec.entity_type)
        if entity_info is not None and entity_info.columns:
            for col_name in join_spec.select:
                if col_name not in entity_info.columns:
                    logger.warning(
                        "data_service_join_unknown_column",
                        extra={
                            "column": col_name,
                            "entity_type": join_spec.entity_type,
                            "known_columns": entity_info.columns,
                        },
                    )

        # Fetch target DataFrame from data service
        fetcher = DataServiceJoinFetcher(self.data_client)
        target_df = await fetcher.fetch_for_join(
            primary_df=df,
            factory=join_spec.factory,
            period=join_spec.period,
            join_key=join_key,
        )

        if target_df.height == 0:
            logger.warning(
                "data_service_join_empty_target",
                extra={
                    "factory": join_spec.factory,
                    "period": join_spec.period,
                },
            )
            return df, {
                "join_entity": f"data-service:{join_spec.factory}",
                "join_key": join_key,
                "join_matched": 0,
                "join_unmatched": len(df),
            }

        # Use factory name as the entity type prefix for column naming
        target_entity_label = join_spec.factory

        # Execute join (same machinery as entity joins)
        join_result = execute_join(
            primary_df=df,
            target_df=target_df,
            join_key=join_key,
            select_columns=join_spec.select,
            target_entity_type=target_entity_label,
        )
        return join_result.df, {
            "join_entity": f"data-service:{join_spec.factory}",
            "join_key": join_result.join_key,
            "join_matched": join_result.matched_count,
            "join_unmatched": join_result.unmatched_count,
        }
