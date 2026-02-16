"""Search service for cached project frames.

Per TDD-search-interface: Provides efficient GID retrieval from cached project
DataFrames using Polars filter expressions.

Design decisions (per ADR-SEARCH-001):
- Uses Polars filter expressions instead of separate inverted index
- Project-scoped search (requires project_gid)
- Async-first with sync wrappers
- Graceful degradation on errors

Integration points:
- DataFrameCacheIntegration: For cached DataFrame access
- ProjectDataFrameBuilder: For cache miss scenarios
- NameNormalizer: For field name normalization
"""

from __future__ import annotations

import asyncio
import time
from functools import reduce
from typing import TYPE_CHECKING

import polars as pl
from autom8y_log import get_logger

from autom8_asana.dataframes.resolver.normalizer import NameNormalizer
from autom8_asana.search.models import (
    FieldCondition,
    SearchCriteria,
    SearchHit,
    SearchResult,
)

if TYPE_CHECKING:
    from autom8_asana.dataframes.cache_integration import DataFrameCacheIntegration
    from autom8_asana.protocols.cache import CacheProvider

logger = get_logger(__name__)


class SearchService:
    """Search interface for cached project frames.

    Provides field-based GID lookup from cached Polars DataFrames.
    Uses Polars filter expressions for fast, vectorized search operations.

    Per TDD-search-interface:
    - Project-scoped search (requires project_gid)
    - Supports single-field and compound AND queries
    - Async-first with sync wrappers
    - Graceful degradation on cache misses and errors

    Attributes:
        cache: Cache provider for project DataFrame storage.
        dataframe_integration: Integration layer for DataFrame cache operations.

    Example:
        >>> # Via AsanaClient
        >>> result = await client.search.find_async(
        ...     "1143843662099250",
        ...     {"Office Phone": "555-1234", "Vertical": "Medical"}
        ... )
        >>> for hit in result.hits:
        ...     print(hit.gid)

        >>> # Convenience method
        >>> gids = await client.search.find_offers_async(
        ...     "1143843662099250",
        ...     office_phone="555-1234"
        ... )
    """

    # Default project DataFrame cache TTL (5 minutes)
    DEFAULT_PROJECT_DF_TTL: int = 300

    def __init__(
        self,
        cache: CacheProvider,
        dataframe_integration: DataFrameCacheIntegration | None = None,
    ) -> None:
        """Initialize SearchService.

        Args:
            cache: Cache provider for storage operations.
            dataframe_integration: Optional DataFrame cache integration.
                Used for row-level caching during DataFrame builds.
        """
        self._cache = cache
        self._df_integration = dataframe_integration
        # Project DataFrame cache: project_gid -> (DataFrame, cached_at)
        self._project_df_cache: dict[str, tuple[pl.DataFrame, float]] = {}

    # =========================================================================
    # Primary Async API
    # =========================================================================

    async def find_async(
        self,
        project_gid: str,
        criteria: dict[str, str] | SearchCriteria,
        *,
        entity_type: str | None = None,
        limit: int | None = None,
    ) -> SearchResult:
        """Find entities matching criteria.

        Searches within the specified project's cached DataFrame using
        Polars filter expressions for fast, vectorized matching.

        Args:
            project_gid: Project to search within.
            criteria: Field-value pairs for AND matching, or SearchCriteria
                for more complex queries.
            entity_type: Optional entity type filter (e.g., "Offer").
            limit: Maximum results to return.

        Returns:
            SearchResult with matching GIDs and metadata.

        Example:
            >>> result = await client.search.find_async(
            ...     "1143843662099250",
            ...     {"Office Phone": "555-1234", "Vertical": "Medical"}
            ... )
            >>> for hit in result.hits:
            ...     print(hit.gid)
        """
        start = time.perf_counter()

        # Normalize criteria to SearchCriteria
        if isinstance(criteria, dict):
            conditions = [
                FieldCondition(field=k, value=v, operator="eq")
                for k, v in criteria.items()
            ]
            search_criteria = SearchCriteria(
                conditions=conditions,
                project_gid=project_gid,
                entity_type=entity_type,
                limit=limit,
            )
        else:
            search_criteria = criteria
            # Override with explicit parameters if provided
            if entity_type is not None:
                search_criteria = search_criteria.model_copy(
                    update={"entity_type": entity_type}
                )
            if limit is not None:
                search_criteria = search_criteria.model_copy(update={"limit": limit})

        # Get or build project DataFrame
        df, from_cache = await self._get_project_df_async(project_gid)

        if df is None or df.is_empty():
            return SearchResult(
                hits=[],
                total_count=0,
                query_time_ms=(time.perf_counter() - start) * 1000,
                from_cache=from_cache,
            )

        try:
            # Build column index once and share across filter + extraction
            col_index = self._build_column_index(df)

            # Build filter expression
            filter_expr = self._build_filter_expr(
                search_criteria.conditions, df, col_index=col_index
            )

            if filter_expr is None:
                # No valid conditions - return empty
                logger.debug("no_valid_filter_conditions", project_gid=project_gid)
                return SearchResult(
                    hits=[],
                    total_count=0,
                    query_time_ms=(time.perf_counter() - start) * 1000,
                    from_cache=from_cache,
                )

            # Apply entity type filter if specified
            if search_criteria.entity_type:
                type_filter = self._build_entity_type_filter(
                    search_criteria.entity_type, df
                )
                if type_filter is not None:
                    filter_expr = filter_expr & type_filter

            # Execute filter
            filtered = df.filter(filter_expr)

            # Apply limit
            if search_criteria.limit:
                filtered = filtered.head(search_criteria.limit)

            # Extract results (reuse col_index -- filtered has same columns)
            hits = self._extract_hits(
                filtered, search_criteria.conditions, col_index=col_index
            )

            query_time_ms = (time.perf_counter() - start) * 1000

            logger.debug(
                "search_completed",
                project_gid=project_gid,
                conditions=len(search_criteria.conditions),
                hits=len(hits),
                query_time_ms=round(query_time_ms, 2),
                from_cache=from_cache,
            )

            return SearchResult(
                hits=hits,
                total_count=len(hits),
                query_time_ms=query_time_ms,
                from_cache=from_cache,
            )

        except (
            Exception
        ) as e:  # BROAD-CATCH: catch-all-and-degrade -- returns empty results on error
            # Graceful degradation - return empty results on error
            logger.warning(
                "search_error",
                project_gid=project_gid,
                error=str(e),
            )
            return SearchResult(
                hits=[],
                total_count=0,
                query_time_ms=(time.perf_counter() - start) * 1000,
                from_cache=from_cache,
            )

    async def find_one_async(
        self,
        project_gid: str,
        criteria: dict[str, str],
        *,
        entity_type: str | None = None,
    ) -> SearchHit | None:
        """Find single entity matching criteria.

        Returns first match or None if no match.

        Args:
            project_gid: Project to search within.
            criteria: Field-value pairs for AND matching.
            entity_type: Optional entity type filter.

        Returns:
            SearchHit if exactly one match, None if no match.

        Raises:
            ValueError: If multiple matches found (use find_async instead).

        Example:
            >>> hit = await client.search.find_one_async(
            ...     "1143843662099250",
            ...     {"Office Phone": "555-1234"}
            ... )
            >>> if hit:
            ...     print(hit.gid)
        """
        result = await self.find_async(
            project_gid,
            criteria,
            entity_type=entity_type,
            limit=2,  # Fetch 2 to detect multiple matches
        )

        if result.total_count == 0:
            return None

        if result.total_count > 1:
            raise ValueError(
                f"Multiple matches found ({result.total_count}). "
                "Use find_async() for queries with multiple results."
            )

        return result.hits[0]

    # =========================================================================
    # Convenience Methods (Typed Access)
    # =========================================================================

    async def find_offers_async(
        self,
        project_gid: str,
        **field_values: str,
    ) -> list[str]:
        """Find Offer GIDs matching field values.

        Convenience method that filters by entity_type="Offer" and
        returns only GIDs.

        Args:
            project_gid: Project to search within.
            **field_values: Field name/value pairs for matching.
                Field names are normalized (snake_case to Title Case).

        Returns:
            List of matching Offer GIDs.

        Example:
            >>> gids = await client.search.find_offers_async(
            ...     "1143843662099250",
            ...     office_phone="555-1234"
            ... )
        """
        # Convert kwargs to normalized criteria
        criteria = self._normalize_field_kwargs(field_values)
        result = await self.find_async(
            project_gid,
            criteria,
            entity_type="Offer",
        )
        return [hit.gid for hit in result.hits]

    async def find_units_async(
        self,
        project_gid: str,
        **field_values: str,
    ) -> list[str]:
        """Find Unit GIDs matching field values.

        Convenience method that filters by entity_type="Unit" and
        returns only GIDs.

        Args:
            project_gid: Project to search within.
            **field_values: Field name/value pairs for matching.

        Returns:
            List of matching Unit GIDs.

        Example:
            >>> gids = await client.search.find_units_async(
            ...     "1143843662099250",
            ...     vertical="Medical"
            ... )
        """
        criteria = self._normalize_field_kwargs(field_values)
        result = await self.find_async(
            project_gid,
            criteria,
            entity_type="Unit",
        )
        return [hit.gid for hit in result.hits]

    async def find_businesses_async(
        self,
        project_gid: str,
        **field_values: str,
    ) -> list[str]:
        """Find Business GIDs matching field values.

        Convenience method that filters by entity_type="Business" and
        returns only GIDs.

        Args:
            project_gid: Project to search within.
            **field_values: Field name/value pairs for matching.

        Returns:
            List of matching Business GIDs.
        """
        criteria = self._normalize_field_kwargs(field_values)
        result = await self.find_async(
            project_gid,
            criteria,
            entity_type="Business",
        )
        return [hit.gid for hit in result.hits]

    # =========================================================================
    # Sync Wrappers
    # =========================================================================

    def find(
        self,
        project_gid: str,
        criteria: dict[str, str] | SearchCriteria,
        *,
        entity_type: str | None = None,
        limit: int | None = None,
    ) -> SearchResult:
        """Sync wrapper for find_async.

        See find_async for full documentation.
        """
        return asyncio.run(
            self.find_async(
                project_gid,
                criteria,
                entity_type=entity_type,
                limit=limit,
            )
        )

    def find_one(
        self,
        project_gid: str,
        criteria: dict[str, str],
        *,
        entity_type: str | None = None,
    ) -> SearchHit | None:
        """Sync wrapper for find_one_async.

        See find_one_async for full documentation.
        """
        return asyncio.run(
            self.find_one_async(
                project_gid,
                criteria,
                entity_type=entity_type,
            )
        )

    def find_offers(
        self,
        project_gid: str,
        **field_values: str,
    ) -> list[str]:
        """Sync wrapper for find_offers_async.

        See find_offers_async for full documentation.
        """
        return asyncio.run(self.find_offers_async(project_gid, **field_values))

    def find_units(
        self,
        project_gid: str,
        **field_values: str,
    ) -> list[str]:
        """Sync wrapper for find_units_async.

        See find_units_async for full documentation.
        """
        return asyncio.run(self.find_units_async(project_gid, **field_values))

    def find_businesses(
        self,
        project_gid: str,
        **field_values: str,
    ) -> list[str]:
        """Sync wrapper for find_businesses_async.

        See find_businesses_async for full documentation.
        """
        return asyncio.run(self.find_businesses_async(project_gid, **field_values))

    # =========================================================================
    # DataFrame Cache Management
    # =========================================================================

    def set_project_dataframe(
        self,
        project_gid: str,
        df: pl.DataFrame,
    ) -> None:
        """Cache a project DataFrame for search.

        Allows pre-populating the search cache with an existing DataFrame,
        typically after it's been built by ProjectDataFrameBuilder.

        Args:
            project_gid: Project GID as cache key.
            df: Polars DataFrame to cache.

        Example:
            >>> # After building DataFrame via builder
            >>> result = await builder.build_progressive_async()
            >>> client.search.set_project_dataframe(project_gid, df)
        """
        self._project_df_cache[project_gid] = (df, time.time())
        logger.debug(
            "Cached project DataFrame",
            extra={
                "project_gid": project_gid,
                "row_count": len(df),
            },
        )

    def clear_project_cache(self, project_gid: str | None = None) -> None:
        """Clear cached project DataFrame(s).

        Args:
            project_gid: Specific project to clear, or None to clear all.
        """
        if project_gid is not None:
            self._project_df_cache.pop(project_gid, None)
            logger.debug("project_cache_cleared", project_gid=project_gid)
        else:
            self._project_df_cache.clear()
            logger.debug("all_project_caches_cleared")

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _get_project_df_async(
        self,
        project_gid: str,
    ) -> tuple[pl.DataFrame | None, bool]:
        """Get or build project DataFrame.

        Checks in-memory cache first, then attempts to build from
        DataFrameCacheIntegration if available.

        Args:
            project_gid: Project GID.

        Returns:
            Tuple of (DataFrame or None, from_cache bool).
        """
        # Check in-memory project DataFrame cache
        if project_gid in self._project_df_cache:
            df, cached_at = self._project_df_cache[project_gid]
            # Check TTL
            if (time.time() - cached_at) < self.DEFAULT_PROJECT_DF_TTL:
                return df, True
            else:
                # Expired - remove from cache
                del self._project_df_cache[project_gid]

        # No DataFrame integration - return empty
        if self._df_integration is None:
            logger.debug("no_dataframe_integration_available", project_gid=project_gid)
            return None, False

        # Note: Full DataFrame build would require ProjectDataFrameBuilder,
        # which requires project object, schema, etc. For search, we expect
        # the DataFrame to be pre-cached via set_project_dataframe() after
        # being built elsewhere in the application flow.
        logger.debug("no_cached_dataframe", project_gid=project_gid)
        return None, False

    def _build_filter_expr(
        self,
        conditions: list[FieldCondition],
        df: pl.DataFrame,
        *,
        col_index: dict[str, str] | None = None,
    ) -> pl.Expr | None:
        """Build Polars filter expression from conditions.

        Uses normalized field name matching to find columns in the DataFrame.

        Args:
            conditions: List of FieldCondition objects.
            df: DataFrame to search (for column name matching).
            col_index: Pre-computed column index. Built from df if not provided.

        Returns:
            Combined Polars expression, or None if no valid conditions.
        """
        if not conditions:
            return None

        # Use pre-computed column index or build one
        if col_index is None:
            col_index = self._build_column_index(df)

        exprs: list[pl.Expr] = []
        for condition in conditions:
            expr = self._condition_to_expr(condition, col_index)
            if expr is not None:
                exprs.append(expr)

        if not exprs:
            return None

        # Combine with AND (default)
        return reduce(lambda a, b: a & b, exprs)

    def _condition_to_expr(
        self,
        condition: FieldCondition,
        col_index: dict[str, str],
    ) -> pl.Expr | None:
        """Convert single condition to Polars expression.

        Args:
            condition: Field condition to convert.
            col_index: Normalized name -> actual column name mapping.

        Returns:
            Polars expression or None if field not found.
        """
        # Find matching column
        normalized = NameNormalizer.normalize(condition.field)
        col_name = col_index.get(normalized)

        if col_name is None:
            logger.debug(
                "field_not_found_in_dataframe",
                field=condition.field,
                normalized=normalized,
            )
            return None

        col = pl.col(col_name)

        match condition.operator:
            case "eq":
                if isinstance(condition.value, list):
                    # Multiple values with eq -> OR (is_in)
                    return col.is_in(condition.value)
                return col == condition.value

            case "contains":
                if isinstance(condition.value, list):
                    # Multiple contains -> OR
                    sub_exprs = [col.str.contains(v) for v in condition.value]
                    return reduce(lambda a, b: a | b, sub_exprs)
                return col.str.contains(condition.value)

            case "in":
                values = (
                    condition.value
                    if isinstance(condition.value, list)
                    else [condition.value]
                )
                return col.is_in(values)

            case _:
                logger.warning("unknown_operator", operator=condition.operator)
                return None

    def _build_entity_type_filter(
        self,
        entity_type: str,
        df: pl.DataFrame,
    ) -> pl.Expr | None:
        """Build filter expression for entity type.

        Looks for "type", "entity_type", or "resource_subtype" columns.

        Args:
            entity_type: Entity type to filter by.
            df: DataFrame to search.

        Returns:
            Polars expression or None if no type column found.
        """
        # Common column names for entity type
        type_cols = ["type", "entity_type", "resource_subtype"]

        for col_name in type_cols:
            if col_name in df.columns:
                return pl.col(col_name) == entity_type

        logger.debug("no_entity_type_column_found", tried_columns=type_cols)
        return None

    def _build_column_index(self, df: pl.DataFrame) -> dict[str, str]:
        """Build normalized name -> actual column name index.

        Args:
            df: DataFrame with columns to index.

        Returns:
            Dict mapping normalized names to actual column names.
        """
        return {NameNormalizer.normalize(col): col for col in df.columns}

    def _extract_hits(
        self,
        df: pl.DataFrame,
        conditions: list[FieldCondition],
        *,
        col_index: dict[str, str] | None = None,
    ) -> list[SearchHit]:
        """Extract SearchHit objects from filtered DataFrame.

        Args:
            df: Filtered DataFrame with matching rows.
            conditions: Original conditions (for matched_fields).
            col_index: Pre-computed column index. Built from df if not provided.

        Returns:
            List of SearchHit objects.
        """
        if df.is_empty():
            return []

        hits: list[SearchHit] = []
        if col_index is None:
            col_index = self._build_column_index(df)

        # Required columns
        gid_col = col_index.get(NameNormalizer.normalize("gid"), "gid")
        name_col = col_index.get(NameNormalizer.normalize("name"), "name")
        type_col = None
        for tc in ["type", "entity_type", "resource_subtype"]:
            if tc in df.columns:
                type_col = tc
                break

        # Iterate rows
        for row in df.iter_rows(named=True):
            gid = str(row.get(gid_col, ""))
            if not gid:
                continue

            name = row.get(name_col)
            entity_type = row.get(type_col) if type_col else None

            # Build matched_fields from conditions
            matched_fields: dict[str, str] = {}
            for condition in conditions:
                normalized = NameNormalizer.normalize(condition.field)
                actual_col = col_index.get(normalized)
                if actual_col and actual_col in row:
                    val = row[actual_col]
                    if val is not None:
                        matched_fields[condition.field] = str(val)

            hits.append(
                SearchHit(
                    gid=gid,
                    entity_type=str(entity_type) if entity_type else None,
                    name=str(name) if name else None,
                    matched_fields=matched_fields,
                )
            )

        return hits

    def _normalize_field_kwargs(
        self,
        field_values: dict[str, str],
    ) -> dict[str, str]:
        """Normalize field names from kwargs to Title Case.

        Converts snake_case kwargs to Title Case for Asana field matching.

        Args:
            field_values: Dict with snake_case field names.

        Returns:
            Dict with Title Case field names.

        Example:
            >>> _normalize_field_kwargs({"office_phone": "555"})
            {"Office Phone": "555"}
        """
        result: dict[str, str] = {}
        for key, value in field_values.items():
            # Convert snake_case to Title Case
            # "office_phone" -> "Office Phone"
            title_key = key.replace("_", " ").title()
            result[title_key] = value
        return result
