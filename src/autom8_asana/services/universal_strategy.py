"""Universal resolution strategy for all entity types.

Per TDD-DYNAMIC-RESOLVER-001 / FR-005:
Single strategy class replacing UnitResolutionStrategy, BusinessResolutionStrategy,
OfferResolutionStrategy, and ContactResolutionStrategy.

This module provides schema-driven resolution using DynamicIndex for O(1) lookups.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS
from autom8_asana.core.string_utils import to_pascal_case
from autom8_asana.services.dynamic_index import DynamicIndex, DynamicIndexCache
from autom8_asana.services.resolution_result import ResolutionResult
from autom8_asana.settings import get_settings

logger = get_logger(__name__)

__all__ = [
    "UniversalResolutionStrategy",
]

# Exception tuples for narrowed exception handling
_INDEX_BUILD_ERRORS = CACHE_TRANSIENT_ERRORS + (RuntimeError,)
_DATAFRAME_BUILD_ERRORS = CACHE_TRANSIENT_ERRORS + (RuntimeError, ValueError)

# Cache TTL for shared dynamic index (1 hour)
# Balances memory vs. rebuild cost for entity resolution indexes
# Configurable via ASANA_CACHE_TTL_DYNAMIC_INDEX environment variable
DYNAMIC_INDEX_CACHE_TTL = get_settings().cache.ttl_dynamic_index

# Maximum concurrent index builds during batch resolution.
# Lower than builder's DEFAULT_MAX_CONCURRENT (25) because index builds
# are heavier (DataFrame fetch + DynamicIndex construction).
# Configurable if needed via future settings extension.
RESOLVE_MAX_CONCURRENT = 10

# Exception types caught per-criterion in _resolve_group.
# Combines data-operation errors (KeyError, ValueError, etc.) with
# transient cache/transport errors so a single lookup failure degrades
# gracefully without aborting sibling criteria.
# RuntimeError included: registry lookups and internal guards may raise it.
_LOOKUP_ERRORS: tuple[type[Exception], ...] = (
    KeyError,
    AttributeError,
    ValueError,
    TypeError,
    RuntimeError,
) + CACHE_TRANSIENT_ERRORS


# FACADE: Delegates to EntityRegistry. Preserves existing import path.
# See: src/autom8_asana/core/entity_registry.py for the single source of truth.
from autom8_asana.core.entity_registry import get_registry as _get_entity_registry

if TYPE_CHECKING:
    import polars as pl

    from autom8_asana.cache.integration.dataframe_cache import FreshnessInfo
    from autom8_asana.client import AsanaClient

DEFAULT_KEY_COLUMNS: dict[str, list[str]] = {
    d.name: list(d.key_columns)
    for d in _get_entity_registry().all_descriptors()
    if d.key_columns
}


@dataclass
class UniversalResolutionStrategy:
    """Schema-driven resolution for any entity type.

    Per FR-005: Replaces all per-entity strategies with a single
    universal strategy that derives lookup behavior from schemas.

    Attributes:
        entity_type: Entity type this strategy resolves (e.g., "unit").
        index_cache: Reference to DynamicIndexCache for index management.

    Key Features:
        - Dynamic criterion validation against schema
        - Arbitrary column combination lookups
        - Consistent multi-match handling for all entities
        - Legacy field mapping for backwards compatibility
        - Integrates with existing DataFrameCache

    Example:
        >>> strategy = UniversalResolutionStrategy(
        ...     entity_type="unit",
        ...     index_cache=DynamicIndexCache(),
        ... )
        >>>
        >>> results = await strategy.resolve(
        ...     criteria=[{"phone": "+15551234567", "vertical": "dental"}],
        ...     project_gid="1234567890",
        ...     client=asana_client,
        ... )
    """

    entity_type: str
    index_cache: DynamicIndexCache = field(default_factory=DynamicIndexCache)

    # Injected by @dataframe_cache decorator on cache hit (if decorated)
    _cached_dataframe: Any = field(default=None, repr=False)

    # Freshness info from last cache access
    _last_freshness_info: FreshnessInfo | None = field(default=None, repr=False)

    async def resolve(
        self,
        criteria: list[dict[str, Any]],
        project_gid: str,
        client: AsanaClient,
        requested_fields: list[str] | None = None,
    ) -> list[ResolutionResult]:
        """Resolve criteria to entity GIDs with optional field enrichment.

        Per FR-005: Schema-driven resolution for any entity type.
        Per TDD-FIELDS-ENRICHMENT-001: When requested_fields is provided,
        returns field values from the DataFrame for each matched GID via match_context.
        Per TDD-B03: Group-and-gather parallel execution for batch resolution.

        Resolution flow (3-phase):
        1. Validate + Group: Validate criteria, group by key_columns
        2. Parallel Index Build + Lookups: Build each distinct index once,
           execute groups concurrently via gather_with_limit
        3. Log + Return: Finalize results in input order

        Args:
            criteria: List of criterion dicts.
            project_gid: Target project GID.
            client: AsanaClient for DataFrame building.
            requested_fields: Optional list of field names to return.

        Returns:
            List of ResolutionResult in same order as input.
            If requested_fields provided, match_context contains field data.
        """
        start_time = time.monotonic()

        if not criteria:
            return []

        # --- Phase 1: Validate + Group ---
        # Import here to avoid circular imports
        from autom8_asana.services.resolver import validate_criterion_for_entity

        results: list[ResolutionResult | None] = [None] * len(criteria)
        groups: dict[tuple[str, ...], list[tuple[int, dict[str, Any]]]] = defaultdict(
            list
        )

        for i, criterion in enumerate(criteria):
            validation = validate_criterion_for_entity(self.entity_type, criterion)

            if not validation.is_valid:
                logger.warning(
                    "criterion_validation_failed",
                    extra={
                        "entity_type": self.entity_type,
                        "errors": validation.errors,
                    },
                )
                results[i] = ResolutionResult.error_result("INVALID_CRITERIA")
                continue

            normalized = validation.normalized_criterion
            key_columns = tuple(sorted(normalized.keys()))
            groups[key_columns].append((i, normalized))

        # --- Phase 2: Parallel Index Build + Lookups ---
        if groups:
            from autom8_asana.dataframes.builders.base import gather_with_limit

            coros = [
                self._resolve_group(
                    key_columns=list(kc),
                    entries=entries,
                    project_gid=project_gid,
                    client=client,
                    requested_fields=requested_fields,
                    results=results,
                )
                for kc, entries in groups.items()
            ]

            await gather_with_limit(coros, max_concurrent=RESOLVE_MAX_CONCURRENT)

        # --- Phase 3: Convert to final list ---
        # Any None slots are defensive (should not happen if logic is correct)
        final_results: list[ResolutionResult] = [
            r if r is not None else ResolutionResult.error_result("INTERNAL_ERROR")
            for r in results
        ]

        # Log batch completion
        elapsed_ms = (time.monotonic() - start_time) * 1000
        resolved_count = sum(
            1 for r in final_results if r.gid is not None and r.error is None
        )
        multi_match_count = sum(1 for r in final_results if r.is_ambiguous)

        logger.info(
            "universal_resolution_complete",
            extra={
                "entity_type": self.entity_type,
                "criteria_count": len(criteria),
                "resolved_count": resolved_count,
                "multi_match_count": multi_match_count,
                "duration_ms": round(elapsed_ms, 2),
                "project_gid": project_gid,
                "group_count": len(groups),
            },
        )

        return final_results

    async def _resolve_group(
        self,
        key_columns: list[str],
        entries: list[tuple[int, dict[str, Any]]],
        project_gid: str,
        client: AsanaClient,
        requested_fields: list[str] | None,
        results: list[ResolutionResult | None],
    ) -> None:
        """Resolve all criteria in a single key_columns group.

        Builds the index once, then runs O(1) lookups for each entry.
        Writes results directly into the shared results list by original index.

        Per TDD-B03: Each group builds its index once, then processes all
        criteria sharing those key_columns sequentially (lookups are O(1)).

        Args:
            key_columns: Column names for the index.
            entries: List of (original_index, normalized_criterion) pairs.
            project_gid: Target project GID.
            client: AsanaClient for DataFrame building.
            requested_fields: Optional list of field names to return.
            results: Shared results list for direct slot writes.
        """
        # Build index once for the group
        try:
            index = await self._get_or_build_index(
                project_gid=project_gid,
                key_columns=key_columns,
                client=client,
            )
        except _INDEX_BUILD_ERRORS as e:
            # Index build failure -> all criteria in this group get INDEX_UNAVAILABLE
            logger.warning(
                "group_index_build_failed",
                extra={
                    "entity_type": self.entity_type,
                    "key_columns": key_columns,
                    "error": str(e),
                    "criteria_count": len(entries),
                },
            )
            for original_idx, _normalized in entries:
                results[original_idx] = ResolutionResult.error_result(
                    "INDEX_UNAVAILABLE"
                )
            return

        if index is None:
            for original_idx, _normalized in entries:
                results[original_idx] = ResolutionResult.error_result(
                    "INDEX_UNAVAILABLE"
                )
            return

        # Process each criterion in the group (sync, O(1) each)
        for original_idx, normalized in entries:
            try:
                gids = index.lookup(normalized)

                # Enrich if fields requested and GIDs found
                context: list[dict[str, Any]] | None = None
                if requested_fields and gids:
                    df = (
                        self._cached_dataframe
                        if self._cached_dataframe is not None
                        else await self._get_dataframe(project_gid, client)
                    )
                    if df is not None:
                        context = self._enrich_from_dataframe(
                            df, gids, requested_fields
                        )

                results[original_idx] = ResolutionResult.from_gids(
                    gids, context=context
                )

            except _LOOKUP_ERRORS as e:  # NARROWED: per-criterion isolation
                logger.warning(
                    "resolution_lookup_failed",
                    extra={
                        "entity_type": self.entity_type,
                        "criterion_index": original_idx,
                        "error": str(e),
                    },
                )
                results[original_idx] = ResolutionResult.error_result("LOOKUP_ERROR")

    def validate_criterion(self, criterion: dict[str, Any]) -> list[str]:
        """Validate criterion fields against entity schema.

        Args:
            criterion: Dictionary of field -> value lookup criteria.

        Returns:
            List of error messages (empty if valid).
        """
        from autom8_asana.services.resolver import validate_criterion_for_entity

        validation = validate_criterion_for_entity(self.entity_type, criterion)
        return validation.errors

    def get_default_key_columns(self) -> list[str]:
        """Get default lookup columns for this entity type.

        Returns:
            List of default column names for lookup.
        """
        return DEFAULT_KEY_COLUMNS.get(self.entity_type, ["gid"])

    async def _get_or_build_index(
        self,
        project_gid: str,
        key_columns: list[str],
        client: AsanaClient,
    ) -> DynamicIndex | None:
        """Get index from cache or build from DataFrame.

        Args:
            project_gid: Project to fetch data from.
            key_columns: Columns for index key.
            client: AsanaClient for DataFrame building.

        Returns:
            DynamicIndex if available, None on failure.
        """
        # Try cache first
        index = self.index_cache.get(
            entity_type=self.entity_type,
            key_columns=key_columns,
        )

        if index is not None:
            return index

        # Cache miss - need to build index
        # Get DataFrame from DataFrameCache or injected _cached_dataframe
        df = await self._get_dataframe(project_gid, client)

        if df is None:
            return None

        # Build index
        try:
            index = DynamicIndex.from_dataframe(
                df=df,
                key_columns=key_columns,
                value_column="gid",
            )

            # Cache the index
            self.index_cache.put(
                entity_type=self.entity_type,
                key_columns=key_columns,
                index=index,
            )

            return index

        except KeyError as e:
            logger.error(
                "index_build_missing_columns",
                extra={
                    "entity_type": self.entity_type,
                    "key_columns": key_columns,
                    "error": str(e),
                },
            )
            return None

    def _enrich_from_dataframe(
        self,
        df: pl.DataFrame,
        gids: list[str],
        fields: list[str],
    ) -> list[dict[str, Any]]:
        """Extract requested field values from DataFrame for matched GIDs.

        Per TDD-FIELDS-ENRICHMENT-001:
        Post-lookup enrichment from DataFrame. Only runs when fields requested.
        Always includes 'gid' in returned data for correlation.

        Args:
            df: Entity DataFrame with all columns.
            gids: List of matched GIDs to enrich.
            fields: Requested field names to extract.

        Returns:
            List of dicts with field values, one per GID in same order.
            Each dict contains 'gid' plus requested fields.
            Returns empty list if no GIDs or DataFrame unavailable.

        Example:
            >>> context = strategy._enrich_from_dataframe(
            ...     df=unit_df,
            ...     gids=["123", "456"],
            ...     fields=["name", "vertical"],
            ... )
            >>> context
            [
                {"gid": "123", "name": "Acme Dental", "vertical": "dental"},
                {"gid": "456", "name": "Beta Medical", "vertical": "medical"},
            ]
        """
        if not gids or df is None:
            return []

        # Ensure gid is always included
        all_fields = list(set(["gid"] + fields))

        # Filter to only columns that exist in DataFrame
        available_columns = set(df.columns)
        valid_fields = [f for f in all_fields if f in available_columns]

        if "gid" not in valid_fields:
            # gid column must exist for filtering
            logger.warning(
                "enrichment_missing_gid_column",
                extra={"entity_type": self.entity_type},
            )
            return []

        try:
            # Filter DataFrame to matching GIDs
            gid_set = set(gids)
            filtered = df.filter(df["gid"].is_in(gid_set))

            # Select only requested fields
            selected = filtered.select(valid_fields)

            # Convert to list of dicts, maintaining GID order
            result_map = {
                row["gid"]: {k: v for k, v in row.items()}
                for row in selected.iter_rows(named=True)
            }

            # Return in same order as input GIDs
            return [result_map.get(gid, {"gid": gid}) for gid in gids]

        except (KeyError, AttributeError, TypeError) as e:
            logger.warning(
                "enrichment_extraction_failed",
                extra={
                    "entity_type": self.entity_type,
                    "error": str(e),
                    "gid_count": len(gids),
                },
            )
            return []

    async def _get_dataframe(
        self,
        project_gid: str,
        client: AsanaClient,
    ) -> pl.DataFrame | None:
        """Get DataFrame from cache, return None on miss.

        Uses injected _cached_dataframe if available (from @dataframe_cache decorator),
        otherwise attempts to retrieve from DataFrameCache.

        Note: DataFrame builds happen at warmup, not request-time.
        This method does NOT trigger builds on cache miss.

        Args:
            project_gid: Project GID.
            client: AsanaClient.

        Returns:
            Polars DataFrame or None if not cached.
        """
        # Use cached DataFrame from @dataframe_cache decorator if available
        if self._cached_dataframe is not None:
            logger.debug(
                "using_cached_dataframe",
                extra={
                    "entity_type": self.entity_type,
                    "project_gid": project_gid,
                    "row_count": len(self._cached_dataframe),
                },
            )
            df: pl.DataFrame | None = self._cached_dataframe
            return df

        # Try to get from DataFrameCache
        try:
            from autom8_asana.cache.dataframe.factory import (
                get_dataframe_cache_provider,
            )

            cache = get_dataframe_cache_provider()
            if cache is not None:
                entry = await cache.get_async(project_gid, self.entity_type)
                if entry is not None:
                    # Retrieve freshness info via typed public method
                    self._last_freshness_info = cache.get_freshness_info(
                        project_gid, self.entity_type
                    )
                    return entry.dataframe
        except CACHE_TRANSIENT_ERRORS as e:
            logger.warning(
                "dataframe_cache_fetch_failed",
                extra={
                    "entity_type": self.entity_type,
                    "project_gid": project_gid,
                    "error": str(e),
                },
            )

        return None

    async def _build_dataframe(
        self,
        project_gid: str,
        client: AsanaClient,
    ) -> tuple[Any, datetime]:
        """Build DataFrame for caching.

        Per TDD-DATAFRAME-CACHE-001: Build method for @dataframe_cache decorator.
        Returns (DataFrame, watermark) tuple for cache storage.

        Delegates to entity-specific builder based on entity_type.

        Args:
            project_gid: Project GID.
            client: AsanaClient for data fetching.

        Returns:
            Tuple of (Polars DataFrame, watermark datetime).
            DataFrame may be None on failure.
        """
        df = await self._build_entity_dataframe(project_gid, client)
        watermark = datetime.now(UTC)
        return df, watermark

    async def _build_entity_dataframe(
        self,
        project_gid: str,
        client: AsanaClient,
    ) -> pl.DataFrame | None:
        """Build entity-specific DataFrame.

        Routes to appropriate builder based on entity_type.

        Args:
            project_gid: Project GID.
            client: AsanaClient.

        Returns:
            Polars DataFrame or None on failure.
        """
        # Import builders and schemas based on entity type
        from autom8_asana.dataframes.builders import ProgressiveProjectBuilder
        from autom8_asana.dataframes.section_persistence import (
            create_section_persistence,
        )

        try:
            # Get schema for entity type
            schema = self._get_entity_schema()
            if schema is None:
                logger.warning(
                    "no_schema_for_entity",
                    extra={"entity_type": self.entity_type},
                )
                return None

            # Create persistence layer
            persistence = create_section_persistence()

            # Create resolver if needed (for custom fields)
            resolver = self._get_custom_field_resolver()

            # Build DataFrame using ProgressiveProjectBuilder
            async with persistence:
                from autom8_asana.services.gid_lookup import build_gid_index_data

                builder = ProgressiveProjectBuilder(
                    client=client,
                    project_gid=project_gid,
                    entity_type=self.entity_type,
                    schema=schema,
                    persistence=persistence,
                    resolver=resolver,
                    store=client.unified_store,
                    index_builder=build_gid_index_data,
                )

                result = await builder.build_progressive_async(resume=True)
                df = result.dataframe

            logger.info(
                "entity_dataframe_built",
                extra={
                    "entity_type": self.entity_type,
                    "project_gid": project_gid,
                    "row_count": len(df) if df is not None else 0,
                },
            )

            return df

        except _DATAFRAME_BUILD_ERRORS as e:
            logger.warning(
                "entity_dataframe_build_failed",
                extra={
                    "entity_type": self.entity_type,
                    "project_gid": project_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return None

    def _get_entity_schema(self) -> Any:
        """Get schema for entity type.

        Returns:
            DataFrameSchema for entity type, or base schema as fallback.
        """
        from autom8_asana.dataframes.models.registry import SchemaRegistry

        registry = SchemaRegistry.get_instance()
        schema_key = to_pascal_case(self.entity_type)  # "unit" -> "Unit"

        try:
            return registry.get_schema(schema_key)
        except (KeyError, RuntimeError):
            # Fall back to base schema
            logger.warning("Custom field resolver fallback", exc_info=True)
            return registry.get_schema("*")

    def _get_custom_field_resolver(self) -> Any:
        """Get custom field resolver for entity type.

        Returns:
            CustomFieldResolver instance or None.
        """
        if self.entity_type in ("unit", "business", "offer"):
            from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver

            return DefaultCustomFieldResolver()
        return None


# Singleton instance for shared index cache
_shared_index_cache: DynamicIndexCache | None = None


def get_shared_index_cache() -> DynamicIndexCache:
    """Get the shared DynamicIndexCache singleton.

    Returns:
        Shared DynamicIndexCache instance.
    """
    global _shared_index_cache
    if _shared_index_cache is None:
        _shared_index_cache = DynamicIndexCache(
            max_per_entity=5,
            ttl_seconds=DYNAMIC_INDEX_CACHE_TTL,
        )
    return _shared_index_cache


def reset_shared_index_cache() -> None:
    """Reset the shared index cache (for testing)."""
    global _shared_index_cache
    _shared_index_cache = None


def get_universal_strategy(entity_type: str) -> UniversalResolutionStrategy:
    """Get UniversalResolutionStrategy for entity type.

    Factory function that creates a UniversalResolutionStrategy
    with the shared index cache.

    Args:
        entity_type: Entity type identifier.

    Returns:
        UniversalResolutionStrategy instance.
    """
    return UniversalResolutionStrategy(
        entity_type=entity_type,
        index_cache=get_shared_index_cache(),
    )
