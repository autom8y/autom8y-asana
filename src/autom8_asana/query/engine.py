"""QueryEngine: orchestrates filtered row retrieval.

Composes cache access, schema validation, predicate compilation,
section scoping, and response shaping.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl
from autom8y_log import get_logger

from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.query.compiler import PredicateCompiler
from autom8_asana.query.errors import (
    AggregateGroupLimitError,
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
from autom8_asana.services.query_service import EntityQueryService
from autom8_asana.services.resolver import to_pascal_case

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.metrics.resolve import SectionIndex
    from autom8_asana.services.resolver import EntityProjectRegistry

logger = get_logger(__name__)


@dataclass
class QueryEngine:
    """Orchestrates filtered row retrieval.

    Composes cache access, schema validation, predicate compilation,
    section scoping, and response shaping.
    """

    query_service: EntityQueryService = field(default_factory=EntityQueryService)
    compiler: PredicateCompiler = field(default_factory=PredicateCompiler)
    limits: QueryLimits = field(default_factory=QueryLimits)

    async def execute_rows(
        self,
        entity_type: str,
        project_gid: str,
        client: AsanaClient,
        request: RowsRequest,
        section_index: SectionIndex | None = None,
        entity_project_registry: EntityProjectRegistry | None = None,
    ) -> RowsResponse:
        """Execute a /rows query.

        Flow:
        1. Validate predicate depth (fail-fast guard).
        2. Resolve section parameter to name filter.
        3. Load DataFrame via EntityQueryService.get_dataframe().
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
        start = time.monotonic()

        # 1. Depth guard (before any I/O)
        if request.where is not None:
            depth = predicate_depth(request.where)
            self.limits.check_depth(depth)

        # 2. Resolve section
        section_name_filter: str | None = None
        if request.section is not None:
            if section_index is None:
                # Caller should provide; fallback to enum
                from autom8_asana.metrics.resolve import SectionIndex as _SectionIndex

                section_index = _SectionIndex.from_enum_fallback(entity_type)
            resolved_gid = section_index.resolve(request.section)
            if resolved_gid is None:
                raise UnknownSectionError(section=request.section)
            # EC-010: DataFrame section column stores NAMES, not GIDs.
            # We filter by the parameter name directly.
            section_name_filter = request.section

        # 3. Load DataFrame
        df = await self.query_service.get_dataframe(
            entity_type,
            project_gid,
            client,
        )

        # 4. Get schema for validation
        registry = SchemaRegistry.get_instance()
        schema = registry.get_schema(to_pascal_case(entity_type))

        # 5. Build filter expression
        filter_expr: pl.Expr | None = None
        if request.where is not None:
            filter_expr = self.compiler.compile(request.where, schema)

        # 6. Apply section filter (ANDed with predicate)
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
            # Validate relationship exists
            rel = find_relationship(entity_type, request.join.entity_type)
            if rel is None:
                raise JoinError(
                    f"No relationship between '{entity_type}' and "
                    f"'{request.join.entity_type}'. "
                    f"Joinable types: {get_joinable_types(entity_type)}"
                )

            # Validate join target columns against target schema
            target_schema = registry.get_schema(
                to_pascal_case(request.join.entity_type)
            )
            for col_name in request.join.select:
                if target_schema.get_column(col_name) is None:
                    raise UnknownFieldError(
                        field=col_name,
                        available=target_schema.column_names(),
                    )

            # Determine join key
            join_key = get_join_key(
                entity_type,
                request.join.entity_type,
                request.join.on,
            )

            # Load target entity DataFrame
            if entity_project_registry is None:
                from autom8_asana.services.resolver import (
                    EntityProjectRegistry as _EPR,
                )

                entity_project_registry = _EPR.get_instance()

            target_project_gid = entity_project_registry.get_project_gid(
                request.join.entity_type
            )
            if target_project_gid is None:
                raise JoinError(
                    f"No project configured for join target: {request.join.entity_type}"
                )

            target_df = await self.query_service.get_dataframe(
                request.join.entity_type,
                target_project_gid,
                client,
            )

            # Execute join
            join_result = execute_join(
                primary_df=df,
                target_df=target_df,
                join_key=join_key,
                select_columns=request.join.select,
                target_entity_type=request.join.entity_type,
            )
            df = join_result.df
            join_meta = {
                "join_entity": request.join.entity_type,
                "join_key": join_result.join_key,
                "join_matched": join_result.matched_count,
                "join_unmatched": join_result.unmatched_count,
            }

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

        # Include join-enriched columns (prefixed with target entity type)
        if request.join is not None:
            for col_name in request.join.select:
                prefixed = f"{request.join.entity_type}_{col_name}"
                if prefixed not in columns:
                    columns.append(prefixed)

        available = set(df.columns)
        valid_columns = [c for c in columns if c in available]
        df = df.select(valid_columns)

        # 12. Build response
        elapsed_ms = (time.monotonic() - start) * 1000
        data = df.to_dicts()

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
                **join_meta,
            ),
        )

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
        4. Load DataFrame via EntityQueryService.get_dataframe().
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
        section_name_filter: str | None = None
        if request.section is not None:
            if section_index is None:
                from autom8_asana.metrics.resolve import SectionIndex as _SectionIndex

                section_index = _SectionIndex.from_enum_fallback(entity_type)
            resolved_gid = section_index.resolve(request.section)
            if resolved_gid is None:
                raise UnknownSectionError(section=request.section)
            section_name_filter = request.section

        # 4. Load DataFrame
        df = await self.query_service.get_dataframe(
            entity_type,
            project_gid,
            client,
        )

        # 5. Get schema for validation
        registry = SchemaRegistry.get_instance()
        schema = registry.get_schema(to_pascal_case(entity_type))

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
        data = result_df.to_dicts()

        return AggregateResponse(
            data=data,
            meta=AggregateMeta(
                group_count=group_count,
                aggregation_count=len(request.aggregations),
                group_by=request.group_by,
                entity_type=entity_type,
                project_gid=project_gid,
                query_ms=round(elapsed_ms, 2),
            ),
        )
