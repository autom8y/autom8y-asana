"""Entity Query Service for DataFrame cache queries.

Per TDD-entity-query-endpoint (Revised):
Provides query operations on the pre-warmed DataFrame cache via
UniversalResolutionStrategy._get_dataframe() for full cache lifecycle.

CRITICAL: Uses UniversalResolutionStrategy._get_dataframe() which provides:
- Layer 1: Decorator-injected cache check
- Layer 2: DataFrameCache singleton (Memory -> S3)
- Layer 3: Cache miss -> build fresh (self-refresh)
- Plus: Build lock, coalescing, circuit breaker

Does NOT use direct cache.get_async() - this would bypass self-refresh!

Components:
- CacheNotWarmError: Raised when DataFrame unavailable after self-refresh
- QueryResult: Result dataclass with data, total_count, project_gid
- EntityQueryService: Service wrapping strategy with Polars operations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any

import polars as pl
from autom8y_log import get_logger

from autom8_asana.cache.integration.dataframe_cache import FreshnessInfo
from autom8_asana.client import AsanaClient
from autom8_asana.metrics.resolve import SectionIndex
from autom8_asana.query.models import RowsRequest
from autom8_asana.services.universal_strategy import UniversalResolutionStrategy

__all__ = [
    "CacheNotWarmError",
    "QueryResult",
    "EntityQueryService",
    "resolve_section",
    "resolve_section_index",
    "strip_section_conflicts",
    "validate_fields",
]

logger = get_logger(__name__)


def validate_fields(
    fields: list[str],
    entity_type: str,
    field_type: str = "where",
) -> None:
    """Validate fields against entity schema.

    Looks up the entity's schema in SchemaRegistry, falling back to the
    wildcard ("*") schema if no entity-specific schema exists. Raises
    InvalidFieldError if any field is not present in the schema.

    Args:
        fields: Field names to validate.
        entity_type: Entity type for schema lookup (snake_case).
        field_type: Context label for error messages ("where" or "select").

    Raises:
        InvalidFieldError: If any field is not in the schema.
    """
    from autom8_asana.dataframes.exceptions import SchemaNotFoundError
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.services.errors import InvalidFieldError
    from autom8_asana.core.string_utils import to_pascal_case

    registry = SchemaRegistry.get_instance()
    schema_key = to_pascal_case(entity_type)

    try:
        schema = registry.get_schema(schema_key)
    except SchemaNotFoundError:
        schema = registry.get_schema("*")

    valid_fields = set(schema.column_names())
    invalid_fields = set(fields) - valid_fields

    if invalid_fields:
        raise InvalidFieldError(
            invalid_fields=sorted(invalid_fields),
            available_fields=sorted(valid_fields),
        )


async def resolve_section(
    section_name: str,
    entity_type: str,
    project_gid: str,
) -> str:
    """Validate section name and return canonical name for filtering.

    Resolution strategy:
    1. Try SectionIndex.from_manifest_async() using SectionPersistence
    2. Fall back to SectionIndex.from_enum_fallback(entity_type)
    3. If neither resolves, raise UnknownSectionError

    Args:
        section_name: Section name to validate.
        entity_type: Entity type for enum fallback.
        project_gid: Project GID for manifest lookup.

    Returns:
        The section name as provided (for direct DataFrame column match).

    Raises:
        UnknownSectionError: If section cannot be resolved.
    """
    from autom8_asana.core.exceptions import S3_TRANSPORT_ERRORS
    from autom8_asana.metrics.resolve import SectionIndex
    from autom8_asana.services.errors import UnknownSectionError

    # Try manifest-based resolution first
    try:
        from autom8_asana.dataframes.section_persistence import (
            create_section_persistence,
        )

        persistence = create_section_persistence()
        if persistence.is_available:
            async with persistence:
                index = await SectionIndex.from_manifest_async(persistence, project_gid)
                if index.resolve(section_name) is not None:
                    return section_name
    except S3_TRANSPORT_ERRORS:
        logger.debug(
            "manifest_section_resolution_failed",
            exc_info=True,
            extra={
                "section_name": section_name,
                "entity_type": entity_type,
                "project_gid": project_gid,
            },
        )

    # Enum fallback
    index = SectionIndex.from_enum_fallback(entity_type)
    if index.resolve(section_name) is not None:
        return section_name

    raise UnknownSectionError(section_name)


async def resolve_section_index(
    section_name: str | None,
    entity_type: str,
    project_gid: str,
) -> SectionIndex | None:
    """Build section index with manifest-first, enum-fallback strategy.

    Used by query.py endpoints to construct a SectionIndex for
    QueryEngine without duplicating the manifest/enum resolution pattern.

    Returns None if section_name is None.

    Args:
        section_name: Section name to build index for. None means no section filtering.
        entity_type: Entity type for enum fallback.
        project_gid: Project GID for manifest lookup.

    Returns:
        SectionIndex if section_name is provided, None otherwise.
    """
    if section_name is None:
        return None

    from autom8_asana.dataframes.section_persistence import create_section_persistence
    from autom8_asana.metrics.resolve import SectionIndex

    persistence = create_section_persistence()
    section_index = await SectionIndex.from_manifest_async(persistence, project_gid)
    if section_index.resolve(section_name) is None:
        section_index = SectionIndex.from_enum_fallback(entity_type)
    return section_index


def _has_section_pred(node: Any) -> bool:
    """Check if a predicate tree contains any section comparisons.

    Walks the predicate tree (Comparison, And, Or, Not nodes) looking
    for any Comparison with field == "section".

    Args:
        node: Root of the predicate tree.

    Returns:
        True if any section comparison found.
    """
    from autom8_asana.query.models import Comparison

    if isinstance(node, Comparison):
        return node.field == "section"
    if hasattr(node, "and_"):
        return any(_has_section_pred(c) for c in node.and_)
    if hasattr(node, "or_"):
        return any(_has_section_pred(c) for c in node.or_)
    if hasattr(node, "not_"):
        return _has_section_pred(node.not_)
    return False


def strip_section_conflicts(
    request_body: RowsRequest,
    section_name: str | None,
) -> RowsRequest:
    """Strip section predicates if section parameter conflicts.

    Per EC-006: When both ?section param and predicate tree contain
    section comparisons, the param wins and predicates are stripped.

    Returns the request unmodified if no conflict exists.

    Args:
        request_body: The RowsRequest containing optional predicate tree.
        section_name: The section query parameter (None if absent).

    Returns:
        The request, potentially with section predicates stripped from where clause.
    """
    if section_name is None or request_body.where is None:
        return request_body
    if not _has_section_pred(request_body.where):
        return request_body

    from autom8_asana.query.compiler import strip_section_predicates

    stripped = strip_section_predicates(request_body.where)
    return request_body.model_copy(update={"where": stripped})


class CacheNotWarmError(Exception):
    """Raised when DataFrame cache is not available after self-refresh attempt.

    This error indicates that:
    - The DataFrame was not found in any cache tier (Memory, S3)
    - Self-refresh via legacy strategy was attempted but failed
    - Possible causes: no legacy strategy exists, build failed, circuit breaker open

    Clients should handle this by:
    - Returning 503 to callers with retry guidance
    - Logging the event for monitoring
    """

    pass


@dataclass
class QueryResult:
    """Result of query operation.

    Attributes:
        data: List of matching records as dictionaries.
        total_count: Total matches before pagination.
        project_gid: Project GID used for query.
    """

    data: list[dict[str, Any]]
    total_count: int
    project_gid: str


@dataclass
class EntityQueryService:
    """Service for querying entities from DataFrame cache.

    Per TDD-entity-query-endpoint (Revised):
    - Uses UniversalResolutionStrategy._get_dataframe() for cache access
    - This ensures full cache lifecycle: check -> miss -> self-refresh
    - Validates fields against SchemaRegistry
    - Applies Polars filter/select/slice operations
    - Returns read-only results (no Asana API calls for queries)

    CRITICAL: Does NOT call cache.get_async() directly. Uses
    UniversalResolutionStrategy to get DataFrame, which provides:
    - Layered cache access (Memory -> S3)
    - Self-refresh on cache miss
    - Build lock acquisition (thundering herd prevention)
    - Request coalescing via @dataframe_cache decorator
    - Circuit breaker integration

    Attributes:
        strategy_factory: Factory function to create UniversalResolutionStrategy.
            Default: get_universal_strategy from services/universal_strategy.py

    Example:
        >>> service = EntityQueryService()
        >>> result = await service.query(
        ...     entity_type="offer",
        ...     project_gid="1143843662099250",
        ...     client=asana_client,
        ...     where={"section": "ACTIVE"},
        ...     select=["gid", "name", "office_phone"],
        ...     limit=100,
        ...     offset=0,
        ... )
        >>> result.total_count
        47
    """

    strategy_factory: Callable[[str], UniversalResolutionStrategy] | None = field(
        default=None
    )

    # Freshness info from last get_dataframe() call
    _last_freshness_info: FreshnessInfo | None = field(
        default=None, init=False, repr=False
    )

    @property
    def last_freshness_info(self) -> FreshnessInfo | None:
        """Public accessor for freshness info (DataFrameProvider protocol)."""
        return self._last_freshness_info

    def __post_init__(self) -> None:
        """Initialize default strategy factory."""
        if self.strategy_factory is None:
            from autom8_asana.services.universal_strategy import get_universal_strategy

            self.strategy_factory = get_universal_strategy

    async def query(
        self,
        entity_type: str,
        project_gid: str,
        client: AsanaClient,
        where: dict[str, Any],
        select: list[str] | None,
        limit: int,
        offset: int,
    ) -> QueryResult:
        """Query entities matching criteria with full cache lifecycle.

        CRITICAL: Uses UniversalResolutionStrategy._get_dataframe() which
        provides self-refresh on cache miss. This ensures:
        - Cache hit: Returns immediately from Memory/S3
        - Cache miss: Triggers build via legacy strategy + @dataframe_cache
        - Concurrent misses: Coalesced (first builds, others wait)
        - Repeated failures: Circuit breaker protects system

        Query flow:
        1. Create UniversalResolutionStrategy for entity_type
        2. Call strategy._get_dataframe(project_gid, client)
           - Checks decorator-injected cache
           - Checks DataFrameCache (Memory -> S3)
           - On miss: Triggers self-refresh via legacy strategy
        3. Apply filters, select, pagination
        4. Return results

        Args:
            entity_type: Entity type to query (e.g., "offer").
            project_gid: Project GID for cache key.
            client: AsanaClient for build operations (if cache miss).
            where: Filter criteria (AND semantics).
            select: Fields to include (None = default set).
            limit: Max results.
            offset: Skip N results.

        Returns:
            QueryResult with data and metadata.

        Raises:
            CacheNotWarmError: DataFrame unavailable after self-refresh attempt.
        """
        # Get strategy for entity type
        # Note: strategy_factory is always set by __post_init__
        assert self.strategy_factory is not None
        strategy = self.strategy_factory(entity_type)

        # Get DataFrame via strategy (full cache lifecycle)
        # This is the CRITICAL change from direct cache access
        df = await strategy._get_dataframe(project_gid, client)

        if df is None:
            # Cache miss even after self-refresh attempt
            # This can happen if:
            # - No legacy strategy exists for entity type
            # - Build failed (circuit breaker may be open)
            logger.warning(
                "query_cache_not_warm",
                extra={
                    "entity_type": entity_type,
                    "project_gid": project_gid,
                },
            )
            raise CacheNotWarmError(
                f"DataFrame unavailable for {entity_type}. "
                "Cache warming may be in progress or build failed."
            )

        # Apply filters
        filtered_df = self._apply_filters(df, where)

        # Get total count BEFORE pagination
        total_count = len(filtered_df)

        # Apply pagination
        paginated_df = self._apply_pagination(filtered_df, offset, limit)

        # Apply select
        select_fields = select or ["gid", "name", "section"]
        selected_df = self._apply_select(paginated_df, select_fields)

        # Convert to list of dicts
        data = selected_df.to_dicts()

        logger.debug(
            "query_executed",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
                "total_count": total_count,
                "result_count": len(data),
                "where_fields": list(where.keys()),
                "select_fields": select_fields,
            },
        )

        return QueryResult(
            data=data,
            total_count=total_count,
            project_gid=project_gid,
        )

    def _apply_filters(
        self,
        df: pl.DataFrame,
        where: dict[str, Any],
    ) -> pl.DataFrame:
        """Apply equality filters to DataFrame.

        Per PRD FR-007: Equality filtering only.
        Multiple fields are AND-ed together.
        Null values in filter column are excluded.

        Args:
            df: Source DataFrame.
            where: Field -> value equality filters.

        Returns:
            Filtered DataFrame.
        """
        for field_name, value in where.items():
            df = df.filter(pl.col(field_name) == value)
        return df

    def _apply_select(
        self,
        df: pl.DataFrame,
        select: list[str],
    ) -> pl.DataFrame:
        """Select only requested columns.

        Per PRD FR-002: gid always included regardless of select.

        Args:
            df: Source DataFrame.
            select: Columns to include.

        Returns:
            DataFrame with selected columns only.
        """
        # Ensure gid is always included
        columns = list(set(["gid"] + select))
        # Filter to only columns that exist in DataFrame
        available = set(df.columns)
        valid_columns = [c for c in columns if c in available]
        return df.select(valid_columns)

    def _apply_pagination(
        self,
        df: pl.DataFrame,
        offset: int,
        limit: int,
    ) -> pl.DataFrame:
        """Apply offset/limit pagination.

        Args:
            df: Source DataFrame.
            offset: Skip N rows.
            limit: Take N rows.

        Returns:
            Paginated DataFrame slice.
        """
        return df.slice(offset, limit)

    async def query_with_expr(
        self,
        entity_type: str,
        project_gid: str,
        client: AsanaClient,
        expr: pl.Expr | None,
        select: list[str],
        limit: int,
        offset: int,
    ) -> QueryResult:
        """Query with a compiled Polars expression.

        Same cache lifecycle as query(), but accepts a pre-compiled
        pl.Expr instead of a flat dict. Used by the /rows endpoint.

        Args:
            entity_type: Entity type to query (e.g., "offer").
            project_gid: Project GID for cache key.
            client: AsanaClient for build operations (if cache miss).
            expr: Compiled Polars expression (None = no filter).
            select: Fields to include in response.
            limit: Max results.
            offset: Skip N results.

        Returns:
            QueryResult with data and metadata.

        Raises:
            CacheNotWarmError: DataFrame unavailable after self-refresh.
        """
        assert self.strategy_factory is not None
        strategy = self.strategy_factory(entity_type)
        df = await strategy._get_dataframe(project_gid, client)

        if df is None:
            logger.warning(
                "query_cache_not_warm",
                extra={
                    "entity_type": entity_type,
                    "project_gid": project_gid,
                },
            )
            raise CacheNotWarmError(
                f"DataFrame unavailable for {entity_type}. "
                "Cache warming may be in progress or build failed."
            )

        # Apply expression filter
        if expr is not None:
            filtered_df = df.filter(expr)
        else:
            filtered_df = df

        total_count = len(filtered_df)

        # Apply pagination
        paginated_df = self._apply_pagination(filtered_df, offset, limit)

        # Apply select
        selected_df = self._apply_select(paginated_df, select)

        # Convert to list of dicts
        data = selected_df.to_dicts()

        logger.debug(
            "query_with_expr_executed",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
                "total_count": total_count,
                "result_count": len(data),
                "select_fields": select,
                "has_expr": expr is not None,
            },
        )

        return QueryResult(
            data=data,
            total_count=total_count,
            project_gid=project_gid,
        )

    async def get_dataframe(
        self,
        entity_type: str,
        project_gid: str,
        client: AsanaClient,
    ) -> pl.DataFrame:
        """Get the raw DataFrame for an entity type.

        Provides the same cache lifecycle as query() but returns the
        raw DataFrame for custom processing (e.g., QueryEngine).

        Per ADR-QE-004: wraps strategy._get_dataframe() so downstream
        callers do not touch the private API directly.

        Args:
            entity_type: Entity type (e.g., "offer").
            project_gid: Project GID for cache key.
            client: AsanaClient for build operations if cache miss.

        Returns:
            Polars DataFrame.

        Raises:
            CacheNotWarmError: DataFrame unavailable after self-refresh.
        """
        assert self.strategy_factory is not None
        strategy = self.strategy_factory(entity_type)
        df = await strategy._get_dataframe(project_gid, client)
        if df is None:
            raise CacheNotWarmError(f"DataFrame unavailable for {entity_type}.")
        # Propagate freshness info from strategy (typed attribute)
        self._last_freshness_info = strategy._last_freshness_info
        return df
