"""Universal resolution strategy for all entity types.

Per TDD-DYNAMIC-RESOLVER-001 / FR-005:
Single strategy class replacing UnitResolutionStrategy, BusinessResolutionStrategy,
OfferResolutionStrategy, and ContactResolutionStrategy.

This module provides schema-driven resolution using DynamicIndex for O(1) lookups.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.services.dynamic_index import DynamicIndex, DynamicIndexCache
from autom8_asana.services.resolution_result import ResolutionResult

if TYPE_CHECKING:
    import polars as pl

    from autom8_asana.client import AsanaClient

logger = get_logger(__name__)

__all__ = [
    "UniversalResolutionStrategy",
]


# Default key columns for backwards compatibility with existing entity strategies
DEFAULT_KEY_COLUMNS: dict[str, list[str]] = {
    "unit": ["office_phone", "vertical"],
    "business": ["office_phone", "vertical"],
    "offer": ["offer_id"],
    "contact": ["email"],
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

    async def resolve(
        self,
        criteria: list[dict[str, Any]],
        project_gid: str,
        client: "AsanaClient",
    ) -> list[ResolutionResult]:
        """Resolve criteria to entity GIDs.

        Per FR-005: Schema-driven resolution for any entity type.

        Resolution flow:
        1. Validate and normalize criteria against schema
        2. Get or build DynamicIndex for criterion columns
        3. Perform O(1) lookups for each criterion
        4. Return ResolutionResult with all matches

        Args:
            criteria: List of criterion dicts.
            project_gid: Target project GID.
            client: AsanaClient for DataFrame building.

        Returns:
            List of ResolutionResult in same order as input.
        """
        start_time = time.monotonic()

        if not criteria:
            return []

        results: list[ResolutionResult] = []

        for criterion in criteria:
            # Import here to avoid circular imports
            from autom8_asana.services.resolver import validate_criterion_for_entity

            # Validate criterion
            validation = validate_criterion_for_entity(self.entity_type, criterion)

            if not validation.is_valid:
                logger.warning(
                    "criterion_validation_failed",
                    extra={
                        "entity_type": self.entity_type,
                        "errors": validation.errors,
                    },
                )
                results.append(ResolutionResult.error_result("INVALID_CRITERIA"))
                continue

            # Get normalized criterion (with legacy field mapping applied)
            normalized = validation.normalized_criterion

            # Determine key columns from criterion fields
            key_columns = sorted(normalized.keys())

            try:
                # Get or build index for this column combination
                index = await self._get_or_build_index(
                    project_gid=project_gid,
                    key_columns=key_columns,
                    client=client,
                )

                if index is None:
                    results.append(
                        ResolutionResult.error_result("INDEX_UNAVAILABLE")
                    )
                    continue

                # Perform lookup
                gids = index.lookup(normalized)
                results.append(ResolutionResult.from_gids(gids))

            except Exception as e:
                logger.warning(
                    "resolution_lookup_failed",
                    extra={
                        "entity_type": self.entity_type,
                        "criterion": criterion,
                        "error": str(e),
                    },
                )
                results.append(ResolutionResult.error_result("LOOKUP_ERROR"))

        # Log batch completion
        elapsed_ms = (time.monotonic() - start_time) * 1000
        resolved_count = sum(1 for r in results if r.gid is not None and r.error is None)
        multi_match_count = sum(1 for r in results if r.is_ambiguous)

        logger.info(
            "universal_resolution_complete",
            extra={
                "entity_type": self.entity_type,
                "criteria_count": len(criteria),
                "resolved_count": resolved_count,
                "multi_match_count": multi_match_count,
                "duration_ms": round(elapsed_ms, 2),
                "project_gid": project_gid,
            },
        )

        return results

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
        client: "AsanaClient",
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

    async def _get_dataframe(
        self,
        project_gid: str,
        client: "AsanaClient",
    ) -> "pl.DataFrame | None":
        """Get DataFrame for entity type.

        Uses injected _cached_dataframe if available (from @dataframe_cache decorator),
        otherwise attempts to retrieve from DataFrameCache.

        Args:
            project_gid: Project GID.
            client: AsanaClient.

        Returns:
            Polars DataFrame or None.
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
            return self._cached_dataframe

        # Try to get from DataFrameCache
        try:
            from autom8_asana.cache.dataframe.factory import get_dataframe_cache_provider

            cache = get_dataframe_cache_provider()
            if cache is not None:
                entry = await cache.get_async(project_gid, self.entity_type)
                if entry is not None:
                    return entry.dataframe
        except Exception as e:
            logger.warning(
                "dataframe_cache_fetch_failed",
                extra={
                    "entity_type": self.entity_type,
                    "project_gid": project_gid,
                    "error": str(e),
                },
            )

        # Cache miss - trigger build via legacy strategy if available
        # This maintains compatibility with existing @dataframe_cache decorator pattern
        try:
            from autom8_asana.services.resolver import get_strategy

            legacy_strategy = get_strategy(self.entity_type)
            if legacy_strategy is not None:
                # Use strategy's resolve with empty criteria to trigger cache population
                # The @dataframe_cache decorator will build and cache the DataFrame
                await legacy_strategy.resolve([], project_gid, client)

                # Try cache again
                from autom8_asana.cache.dataframe.factory import (
                    get_dataframe_cache_provider,
                )

                cache = get_dataframe_cache_provider()
                if cache is not None:
                    entry = await cache.get_async(project_gid, self.entity_type)
                    if entry is not None:
                        return entry.dataframe
        except Exception as e:
            logger.warning(
                "legacy_strategy_build_failed",
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
        client: "AsanaClient",
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
        watermark = datetime.now(timezone.utc)
        return df, watermark

    async def _build_entity_dataframe(
        self,
        project_gid: str,
        client: "AsanaClient",
    ) -> "pl.DataFrame | None":
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
        from autom8_asana.dataframes.section_persistence import SectionPersistence

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
            persistence = SectionPersistence()

            # Create resolver if needed (for custom fields)
            resolver = self._get_custom_field_resolver()

            # Build DataFrame using ProgressiveProjectBuilder
            builder = ProgressiveProjectBuilder(
                client=client,
                project_gid=project_gid,
                entity_type=self.entity_type,
                schema=schema,
                persistence=persistence,
                resolver=resolver,
                store=client.unified_store,
            )

            df = await builder.build_with_parallel_fetch_async(
                project_gid=project_gid,
                schema=schema,
                resume=True,
                incremental=True,
            )

            logger.info(
                "entity_dataframe_built",
                extra={
                    "entity_type": self.entity_type,
                    "project_gid": project_gid,
                    "row_count": len(df),
                },
            )

            return df

        except Exception as e:
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
        schema_key = self.entity_type.title()  # "unit" -> "Unit"

        try:
            return registry.get_schema(schema_key)
        except Exception:
            # Fall back to base schema
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
            ttl_seconds=3600,  # 1 hour
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
