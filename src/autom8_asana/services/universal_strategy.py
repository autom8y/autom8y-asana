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
from autom8y_telemetry import get_tracer
from opentelemetry.trace import StatusCode

from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS
from autom8_asana.core.string_utils import to_pascal_case
from autom8_asana.models.business.activity import (
    ACTIVITY_PRIORITY,
    AccountActivity,
    get_classifier,
)
from autom8_asana.services.dynamic_index import DynamicIndex, DynamicIndexCache
from autom8_asana.services.resolution_result import ResolutionResult
from autom8_asana.settings import get_settings

logger = get_logger(__name__)
_tracer = get_tracer(__name__)

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

# Per TDD-STATUS-AWARE-RESOLUTION / FR-1:
# Statuses included in active_only=True results.
_ACTIVE_STATUSES: frozenset[str] = frozenset(
    {AccountActivity.ACTIVE.value, AccountActivity.ACTIVATING.value}
)

# Per TDD-STATUS-AWARE-RESOLUTION / FR-8:
# Priority ordering for sort. Lower index = higher priority.
# None (UNKNOWN) sorts after all known statuses.
_PRIORITY_MAP: dict[str | None, int] = {
    activity.value: idx for idx, activity in enumerate(ACTIVITY_PRIORITY)
}
_UNKNOWN_PRIORITY: int = len(ACTIVITY_PRIORITY)


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
        active_only: bool = True,
    ) -> list[ResolutionResult]:
        """Resolve criteria to entity GIDs with optional field enrichment.

        Per FR-005: Schema-driven resolution for any entity type.
        Per TDD-FIELDS-ENRICHMENT-001: When requested_fields is provided,
        returns field values from the DataFrame for each matched GID via match_context.
        Per TDD-B03: Group-and-gather parallel execution for batch resolution.
        Per TDD-STATUS-AWARE-RESOLUTION / FR-1: When active_only=True (default),
        results are filtered to ACTIVE + ACTIVATING statuses only.

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
            active_only: Per FR-1, SD-1. Filter to active statuses only.

        Returns:
            List of ResolutionResult in same order as input.
            If requested_fields provided, match_context contains field data.
        """
        start_time = time.monotonic()

        if not criteria:
            return []

        with _tracer.start_as_current_span("strategy.resolution.resolve") as span:
            span.set_attribute("strategy.entity_type", self.entity_type)
            span.set_attribute("strategy.criteria_count", len(criteria))
            span.set_attribute("strategy.project_gid", project_gid)

            # --- Phase 1: Validate + Group ---
            # Import here to avoid circular imports
            from autom8_asana.services.resolver import validate_criterion_for_entity

            results: list[ResolutionResult | None] = [None] * len(criteria)
            groups: dict[tuple[str, ...], list[tuple[int, dict[str, Any]]]] = (
                defaultdict(list)
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
                        active_only=active_only,
                    )
                    for kc, entries in groups.items()
                ]

                await gather_with_limit(coros, max_concurrent=RESOLVE_MAX_CONCURRENT)

            # --- Phase 3: Convert to final list ---
            # Any None slots are defensive (should not happen if logic is correct).
            # Per ADR-error-taxonomy-resolution / FIND-002: log each null slot
            # with criterion_index and entity_type for diagnostics.
            null_slot_count = 0
            final_results: list[ResolutionResult] = []
            for i, r in enumerate(results):
                if r is not None:
                    final_results.append(r)
                else:
                    logger.error(
                        "resolution_null_slot",
                        extra={
                            "criterion_index": i,
                            "entity_type": self.entity_type,
                        },
                    )
                    span.add_event(
                        "resolution.null_slot",
                        attributes={
                            "strategy.criterion_index": i,
                            "strategy.entity_type": self.entity_type,
                        },
                    )
                    null_slot_count += 1
                    final_results.append(
                        ResolutionResult.error_result("RESOLUTION_NULL_SLOT")
                    )

            # Log batch completion
            elapsed_ms = (time.monotonic() - start_time) * 1000
            resolved_count = sum(
                1 for r in final_results if r.gid is not None and r.error is None
            )
            multi_match_count = sum(1 for r in final_results if r.is_ambiguous)

            span.set_attribute("strategy.resolved_count", resolved_count)
            span.set_attribute("strategy.group_count", len(groups))
            span.set_attribute("strategy.null_slot_count", null_slot_count)

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
        active_only: bool = True,
    ) -> None:
        """Resolve all criteria in a single key_columns group.

        Builds the index once, then runs O(1) lookups for each entry.
        Writes results directly into the shared results list by original index.

        Per TDD-B03: Each group builds its index once, then processes all
        criteria sharing those key_columns sequentially (lookups are O(1)).
        Per TDD-STATUS-AWARE-RESOLUTION: After lookup, classifies GIDs by
        status, filters by active_only, and sorts by ACTIVITY_PRIORITY.

        Args:
            key_columns: Column names for the index.
            entries: List of (original_index, normalized_criterion) pairs.
            project_gid: Target project GID.
            client: AsanaClient for DataFrame building.
            requested_fields: Optional list of field names to return.
            results: Shared results list for direct slot writes.
            active_only: Per FR-1, SD-1. Filter to active statuses only.
        """
        with _tracer.start_as_current_span("strategy.resolution.resolve_group") as span:
            span.set_attribute("strategy.entity_type", self.entity_type)
            span.set_attribute("strategy.key_columns", ",".join(key_columns))
            span.set_attribute("strategy.group_criteria_count", len(entries))
            span.set_attribute("strategy.project_gid", project_gid)

            lookup_error_count = 0

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
                span.set_attribute("strategy.error_code", "INDEX_UNAVAILABLE")
                span.set_attribute("error.type", type(e).__name__)
                span.record_exception(e)
                span.set_status(StatusCode.ERROR, description="INDEX_UNAVAILABLE")
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

            # Per TDD-STATUS-AWARE-RESOLUTION / FR-2, FR-7:
            # Obtain classifier once per group for efficiency.
            classifier = get_classifier(self.entity_type)

            # Get DataFrame for classification and enrichment
            df = (
                self._cached_dataframe
                if self._cached_dataframe is not None
                else await self._get_dataframe(project_gid, client)
            )

            # Process each criterion in the group (sync, O(1) each)
            for original_idx, normalized in entries:
                try:
                    gids = index.lookup(normalized)

                    # Per TDD-STATUS-AWARE-RESOLUTION / FR-2:
                    # Classification step -- only when classifier exists and GIDs found
                    if gids and classifier is not None and df is not None:
                        classified = self._classify_gids(df, gids, self.entity_type)
                        total_count = len(classified)

                        # Per TDD-STATUS-AWARE-RESOLUTION / FR-1:
                        # Filter to active statuses when active_only=True
                        if active_only:
                            classified = [
                                (g, s) for g, s in classified if s in _ACTIVE_STATUSES
                            ]

                        # Per TDD-STATUS-AWARE-RESOLUTION / FR-8:
                        # Sort by ACTIVITY_PRIORITY (stable sort)
                        classified.sort(
                            key=lambda pair: _PRIORITY_MAP.get(
                                pair[1], _UNKNOWN_PRIORITY
                            )
                        )

                        sorted_gids = [g for g, _s in classified]
                        annotations = [s for _g, s in classified]

                        # Enrich if fields requested (existing, unchanged)
                        context: list[dict[str, Any]] | None = None
                        if requested_fields and sorted_gids:
                            context = self._enrich_from_dataframe(
                                df, sorted_gids, requested_fields
                            )

                        # Per TDD-STATUS-AWARE-RESOLUTION / FR-9, EC-1:
                        # Empty after filtering -> NOT_FOUND
                        results[original_idx] = ResolutionResult.from_gids_with_status(
                            sorted_gids,
                            status_annotations=annotations,
                            context=context,
                            total_match_count=(total_count if active_only else None),
                        )
                    else:
                        # Per TDD-STATUS-AWARE-RESOLUTION / FR-7:
                        # No classifier or no gids: existing behavior, no status
                        context = None
                        if requested_fields and gids and df is not None:
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
                    span.add_event(
                        "resolution.lookup_failed",
                        attributes={
                            "strategy.criterion_index": original_idx,
                            "error.type": type(e).__name__,
                        },
                    )
                    lookup_error_count += 1
                    results[original_idx] = ResolutionResult.error_result(
                        "LOOKUP_ERROR"
                    )

            span.set_attribute("strategy.lookup_error_count", lookup_error_count)

    def _classify_gids(
        self,
        df: pl.DataFrame,
        gids: list[str],
        entity_type: str,
    ) -> list[tuple[str, str | None]]:
        """Classify matched GIDs by AccountActivity status.

        Per TDD-STATUS-AWARE-RESOLUTION / FR-2, FR-5, FR-6:
        Uses SectionClassifier for O(1) per-GID classification.
        is_completed=True overrides section classification (SD-6).
        Null section maps to None (UNKNOWN) per SCAR-005/006.

        Args:
            df: Entity DataFrame with 'gid', 'section', 'is_completed' columns.
            gids: List of matched GID strings.
            entity_type: Entity type for classifier lookup.

        Returns:
            List of (gid, status_string_or_None) tuples.
            status_string is AccountActivity.value ("active", "activating", etc.)
            or None for UNKNOWN (null section, unrecognized section).
        """
        classifier = get_classifier(entity_type)

        # Per TDD-STATUS-AWARE-RESOLUTION / FR-7:
        # No classifier -> return all as UNKNOWN (None)
        if classifier is None:
            return [(gid, None) for gid in gids]

        # Filter DataFrame to matching GIDs (one-time Polars op per group)
        gid_set = set(gids)
        available_columns = set(df.columns)

        # Determine which columns we can access
        has_section = "section" in available_columns
        has_completed = "is_completed" in available_columns

        # Build gid -> (section, is_completed) lookup dict from filtered rows
        gid_data: dict[str, tuple[str | None, bool]] = {}
        if has_section or has_completed:
            select_cols = ["gid"]
            if has_section:
                select_cols.append("section")
            if has_completed:
                select_cols.append("is_completed")

            filtered = df.filter(df["gid"].is_in(gid_set)).select(select_cols)
            for row in filtered.iter_rows(named=True):
                section = row.get("section") if has_section else None
                completed = row.get("is_completed", False) if has_completed else False
                gid_data[row["gid"]] = (section, bool(completed))

        # Classify each GID
        result: list[tuple[str, str | None]] = []
        for gid in gids:
            if gid not in gid_data:
                # Per SCAR-005/006: GID not in DataFrame -> UNKNOWN
                result.append((gid, None))
                continue

            section, is_completed = gid_data[gid]

            # Per SD-6: is_completed=True is terminal override -> INACTIVE
            if is_completed:
                result.append((gid, AccountActivity.INACTIVE.value))
                continue

            # Per SD-5, SCAR-005/006: null section -> UNKNOWN
            if section is None:
                result.append((gid, None))
                continue

            # Per FR-2: classify via SectionClassifier (O(1) dict lookup)
            activity = classifier.classify(section)
            if activity is None:
                # Per EC-9: unrecognized section name -> UNKNOWN
                result.append((gid, None))
            else:
                result.append((gid, activity.value))

        return result

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

        Raises:
            CascadeNotReadyError: If cascade-sourced key columns exceed the
                null rate error threshold (20%).
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

        # Cascade health gate: reject degraded DataFrames before index build
        self._check_cascade_health(df, project_gid)

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

    def _check_cascade_health(
        self,
        df: pl.DataFrame,
        project_gid: str,
    ) -> None:
        """Gate resolution against degraded cascade data.

        Raises CascadeNotReadyError if any cascade-sourced key column
        exceeds the null rate error threshold.

        Only runs when:
        - Entity descriptor is available with key_columns
        - Schema is available for this entity type
        - Entity has cascade-sourced key columns
        Silently passes otherwise (safe degradation).

        Args:
            df: Post-build DataFrame to check.
            project_gid: Project GID for error context.

        Raises:
            CascadeNotReadyError: If cascade-sourced key columns are degraded.
        """
        from autom8_asana.core.entity_registry import get_registry
        from autom8_asana.dataframes.builders.cascade_validator import (
            check_cascade_health,
        )

        desc = get_registry().get(self.entity_type)
        if desc is None or not desc.key_columns:
            return

        schema = self._get_entity_schema()
        if schema is None:
            return

        result = check_cascade_health(
            df=df,
            entity_type=self.entity_type,
            schema=schema,
            key_columns=desc.key_columns,
        )

        if not result.healthy:
            from autom8_asana.services.errors import CascadeNotReadyError

            raise CascadeNotReadyError(
                entity_type=self.entity_type,
                project_gid=project_gid,
                degraded_columns=result.degraded_columns,
                max_null_rate=result.max_null_rate,
            )

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

        Per ADR-omniscience-descriptor-driven-resolver: Resolves the
        custom field resolver class from EntityDescriptor.custom_field_resolver_class_path
        instead of hardcoding entity type checks.

        Returns:
            CustomFieldResolver instance or None.
        """
        from autom8_asana.core.entity_registry import get_registry

        descriptor = get_registry().get(self.entity_type)
        if descriptor and descriptor.custom_field_resolver_class_path:
            module_path, class_name = (
                descriptor.custom_field_resolver_class_path.rsplit(".", 1)
            )
            import importlib

            module = importlib.import_module(module_path)
            return getattr(module, class_name)()
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
