"""Entity Resolver service for generalized GID resolution.

Per TDD-entity-resolver Phase 1:
This module provides the Entity Resolver system for resolving entity identifiers
to Asana task GIDs. The system supports multiple entity types with pluggable
resolution strategies.

Phase 1 implements:
- EntityProjectRegistry singleton for entity_type -> project_gid mapping
- ResolutionStrategy protocol for strategy dispatch
- UnitResolutionStrategy using GidLookupIndex O(1) lookup

Components:
- EntityProjectConfig: Configuration for a single entity type's project mapping
- EntityProjectRegistry: Singleton registry populated at startup
- ResolutionStrategy: Protocol for entity-specific resolution logic
- UnitResolutionStrategy: Phone/vertical O(1) lookup via GidLookupIndex

Per ADR-0060: Project GIDs discovered at startup via WorkspaceProjectRegistry.
Per TDD: Module-level cache dict for GidLookupIndex per project.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, runtime_checkable

from autom8_asana.models.contracts.phone_vertical import PhoneVerticalPair
from autom8_asana.services.gid_lookup import GidLookupIndex

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

__all__ = [
    "EntityProjectConfig",
    "EntityProjectRegistry",
    "ResolutionStrategy",
    "UnitResolutionStrategy",
    "BusinessResolutionStrategy",
    "OfferResolutionStrategy",
    "ContactResolutionStrategy",
    "ResolutionResult",
    "get_strategy",
    "register_strategies",
    "RESOLUTION_STRATEGIES",
    "_gid_index_cache",
    "_INDEX_TTL_SECONDS",
    "filter_result_fields",
]

logger = logging.getLogger(__name__)

# --- Module-Level GidLookupIndex Cache ---
# Per TDD: TTL-based cache for O(1) lookups
# Key: project_gid, Value: GidLookupIndex instance
_gid_index_cache: dict[str, GidLookupIndex] = {}

# Default TTL for index staleness check (1 hour)
_INDEX_TTL_SECONDS = 3600


# --- Data Models ---


@dataclass(frozen=True, slots=True)
class EntityProjectConfig:
    """Configuration for a single entity type's project mapping.

    Per TDD: Immutable dataclass for thread-safe access.

    Attributes:
        entity_type: Entity type identifier (e.g., "unit", "business")
        project_gid: Asana project GID
        project_name: Human-readable name (for logging)
        schema_task_type: SchemaRegistry key (e.g., "Unit", "Contact")
    """

    entity_type: str
    project_gid: str
    project_name: str
    schema_task_type: str | None = None


@dataclass
class ResolutionResult:
    """Single resolution result.

    Per TDD: Result of a single criterion resolution.

    Attributes:
        gid: Resolved task GID or None if not found
        error: Error code if resolution failed (e.g., "NOT_FOUND")
        multiple: True if contact returned multiple matches (Phase 2)
    """

    gid: str | None
    error: str | None = None
    multiple: bool | None = None


# --- EntityProjectRegistry ---


class EntityProjectRegistry:
    """Singleton registry mapping entity_type -> project configuration.

    Per TDD: Populated at startup via WorkspaceProjectRegistry discovery.
    Thread-safe via immutable design (populated once, read-only after).

    Per ADR-0060: Startup discovery with fail-fast on missing projects.

    Usage:
        # Get singleton instance
        registry = EntityProjectRegistry.get_instance()

        # Check readiness
        if not registry.is_ready():
            raise RuntimeError("Discovery not complete")

        # Get project GID for entity type
        gid = registry.get_project_gid("unit")

    Testing:
        # Reset for test isolation
        EntityProjectRegistry.reset()
    """

    _instance: ClassVar[EntityProjectRegistry | None] = None

    # Instance attributes
    _configs: dict[str, EntityProjectConfig]
    _initialized: bool

    def __new__(cls) -> EntityProjectRegistry:
        """Get or create singleton instance.

        Returns:
            The singleton EntityProjectRegistry instance.
        """
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._configs = {}
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initialize instance attributes (only runs once due to singleton)."""
        # Attributes are set in __new__ to avoid re-initialization
        pass

    @classmethod
    def get_instance(cls) -> EntityProjectRegistry:
        """Get the singleton instance.

        Returns:
            The singleton EntityProjectRegistry instance.
        """
        return cls()

    def register(
        self,
        entity_type: str,
        project_gid: str,
        project_name: str,
        schema_task_type: str | None = None,
    ) -> None:
        """Register an entity type to project mapping.

        Args:
            entity_type: Entity type identifier (e.g., "unit")
            project_gid: Asana project GID
            project_name: Human-readable project name
            schema_task_type: SchemaRegistry key (optional)
        """
        # Derive schema_task_type from entity_type if not provided
        if schema_task_type is None:
            schema_task_type = entity_type.title()  # "unit" -> "Unit"

        config = EntityProjectConfig(
            entity_type=entity_type,
            project_gid=project_gid,
            project_name=project_name,
            schema_task_type=schema_task_type,
        )

        self._configs[entity_type] = config
        self._initialized = True

        logger.debug(
            "entity_type_registered",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
                "project_name": project_name,
            },
        )

    def get_project_gid(self, entity_type: str) -> str | None:
        """Get project GID for entity type. O(1).

        Args:
            entity_type: Entity type identifier

        Returns:
            Project GID if registered, None otherwise.
        """
        config = self._configs.get(entity_type)
        return config.project_gid if config else None

    def get_config(self, entity_type: str) -> EntityProjectConfig | None:
        """Get full config for entity type. O(1).

        Args:
            entity_type: Entity type identifier

        Returns:
            EntityProjectConfig if registered, None otherwise.
        """
        return self._configs.get(entity_type)

    def is_ready(self) -> bool:
        """True if startup discovery completed successfully.

        Returns:
            True if at least one entity type is registered.
        """
        return self._initialized and len(self._configs) > 0

    def get_all_entity_types(self) -> list[str]:
        """Get all registered entity types.

        Returns:
            List of registered entity type identifiers.
        """
        return list(self._configs.keys())

    @classmethod
    def reset(cls) -> None:
        """Reset for testing.

        Clears the singleton instance so next access creates a fresh registry.
        """
        cls._instance = None
        logger.debug("EntityProjectRegistry reset")


# --- Resolution Strategies ---


@runtime_checkable
class ResolutionStrategy(Protocol):
    """Protocol for entity-specific resolution logic.

    Per TDD: Strategy pattern for entity-specific resolution.
    Each strategy implements resolution logic for one entity type.
    """

    async def resolve(
        self,
        criteria: list[Any],  # ResolutionCriterion from routes
        project_gid: str,
        client: "AsanaClient",
    ) -> list[ResolutionResult]:
        """Resolve criteria to entity GIDs.

        Args:
            criteria: List of resolution criteria
            project_gid: Target project GID
            client: AsanaClient for Asana API access

        Returns:
            List of ResolutionResult in same order as input criteria.
        """
        ...

    def validate_criterion(self, criterion: Any) -> str | None:
        """Return error message if criterion invalid, None if valid.

        Args:
            criterion: Single resolution criterion

        Returns:
            Error message string if invalid, None if valid.
        """
        ...


class UnitResolutionStrategy:
    """Unit resolution via GidLookupIndex O(1) lookup.

    Per TDD Phase 1: Implements Unit resolution using existing GidLookupIndex.
    Uses phone/vertical pairs for O(1) dictionary lookup.

    Resolution flow:
    1. Get or build GidLookupIndex from cached DataFrame
    2. Convert criteria to PhoneVerticalPair instances
    3. Batch lookup via index.get_gids()
    4. Return ResolutionResult for each criterion
    """

    async def resolve(
        self,
        criteria: list[Any],
        project_gid: str,
        client: "AsanaClient",
    ) -> list[ResolutionResult]:
        """Resolve phone/vertical pairs to Unit task GIDs.

        Args:
            criteria: List of ResolutionCriterion with phone and vertical
            project_gid: Unit project GID
            client: AsanaClient for DataFrame building

        Returns:
            List of ResolutionResult in same order as input criteria.
        """
        start_time = time.monotonic()

        if not criteria:
            return []

        # Get or build the lookup index
        index = await self._get_or_build_index(project_gid, client)

        if index is None:
            # Index build failed - return NOT_FOUND for all
            logger.warning(
                "unit_resolution_no_index",
                extra={
                    "project_gid": project_gid,
                    "criteria_count": len(criteria),
                },
            )
            return [
                ResolutionResult(gid=None, error="INDEX_UNAVAILABLE")
                for _ in criteria
            ]

        # Convert criteria to PhoneVerticalPair and resolve
        results: list[ResolutionResult] = []

        for criterion in criteria:
            # Validate criterion has required fields
            validation_error = self.validate_criterion(criterion)
            if validation_error:
                results.append(ResolutionResult(gid=None, error="INVALID_CRITERIA"))
                continue

            try:
                pvp = PhoneVerticalPair(
                    office_phone=criterion.phone,
                    vertical=criterion.vertical,
                )
                gid = index.get_gid(pvp)
                results.append(
                    ResolutionResult(
                        gid=gid,
                        error="NOT_FOUND" if gid is None else None,
                    )
                )
            except ValueError as e:
                # PhoneVerticalPair validation failed
                logger.warning(
                    "pvp_conversion_failed",
                    extra={
                        "phone": getattr(criterion, "phone", None),
                        "vertical": getattr(criterion, "vertical", None),
                        "error": str(e),
                    },
                )
                results.append(ResolutionResult(gid=None, error="INVALID_CRITERIA"))

        # Log batch completion
        elapsed_ms = (time.monotonic() - start_time) * 1000
        resolved_count = sum(1 for r in results if r.gid is not None)

        logger.info(
            "entity_resolution_batch_complete",
            extra={
                "entity_type": "unit",
                "criteria_count": len(criteria),
                "resolved_count": resolved_count,
                "unresolved_count": len(criteria) - resolved_count,
                "duration_ms": round(elapsed_ms, 2),
                "cache_hit": index is not None,
                "project_gid": project_gid,
            },
        )

        return results

    def validate_criterion(self, criterion: Any) -> str | None:
        """Validate that criterion has phone and vertical.

        Args:
            criterion: ResolutionCriterion to validate

        Returns:
            Error message if invalid, None if valid.
        """
        phone = getattr(criterion, "phone", None)
        vertical = getattr(criterion, "vertical", None)

        if not phone or not vertical:
            return "phone and vertical required for unit resolution"

        return None

    async def _get_or_build_index(
        self,
        project_gid: str,
        client: "AsanaClient",
    ) -> GidLookupIndex | None:
        """Get cached GidLookupIndex or build a new one.

        Per TDD: TTL-based caching with 1-hour staleness check.
        Uses module-level _gid_index_cache.

        Args:
            project_gid: Unit project GID
            client: AsanaClient for DataFrame building

        Returns:
            GidLookupIndex if available, None on build failure.
        """
        global _gid_index_cache

        # Check for cached index
        cached_index = _gid_index_cache.get(project_gid)

        if cached_index is not None and not cached_index.is_stale(_INDEX_TTL_SECONDS):
            logger.debug(
                "gid_index_cache_hit",
                extra={
                    "project_gid": project_gid,
                    "index_size": len(cached_index),
                    "age_seconds": (
                        datetime.now(timezone.utc) - cached_index.created_at
                    ).total_seconds(),
                },
            )
            return cached_index

        # Cache miss or stale - rebuild index
        cache_status = "stale" if cached_index is not None else "miss"
        logger.info(
            "gid_index_cache_rebuild",
            extra={
                "project_gid": project_gid,
                "reason": cache_status,
            },
        )

        # Build DataFrame
        df = await self._build_dataframe(project_gid, client)

        if df is None:
            logger.warning(
                "gid_index_build_failed_no_dataframe",
                extra={"project_gid": project_gid},
            )
            return None

        try:
            # Build index from DataFrame
            index = GidLookupIndex.from_dataframe(df)

            # Cache the new index
            _gid_index_cache[project_gid] = index

            logger.info(
                "gid_index_built",
                extra={
                    "project_gid": project_gid,
                    "index_size": len(index),
                },
            )

            return index

        except KeyError as e:
            logger.error(
                "gid_index_build_failed_missing_columns",
                extra={
                    "project_gid": project_gid,
                    "error": str(e),
                },
            )
            return None

    async def _build_dataframe(
        self,
        project_gid: str,
        client: "AsanaClient",
    ) -> Any:
        """Build Unit project DataFrame for GID lookups.

        Uses ProjectDataFrameBuilder with parallel fetch for efficient
        DataFrame construction.

        Args:
            project_gid: Unit project GID
            client: AsanaClient with valid authentication

        Returns:
            Polars DataFrame with unit data, or None on failure.
        """
        # Import here to avoid circular imports
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
        from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
        from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA

        # Minimal project proxy - only needs gid attribute for builder
        class ProjectProxy:
            """Minimal project object for DataFrame builder."""

            def __init__(self, gid: str) -> None:
                self.gid = gid
                self.tasks: list[Any] = []

        try:
            project_proxy = ProjectProxy(project_gid)

            # Create resolver for custom field extraction (office_phone, vertical)
            resolver = DefaultCustomFieldResolver()

            builder = ProjectDataFrameBuilder(
                project=project_proxy,
                task_type="Unit",
                schema=UNIT_SCHEMA,
                resolver=resolver,
            )

            # Use parallel fetch for efficient DataFrame construction
            df = await builder.build_with_parallel_fetch_async(client)

            logger.info(
                "unit_dataframe_built",
                extra={
                    "project_gid": project_gid,
                    "row_count": len(df),
                },
            )

            return df

        except Exception as e:
            logger.warning(
                "unit_dataframe_build_failed",
                extra={
                    "project_gid": project_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return None


class BusinessResolutionStrategy:
    """Business resolution: Unit lookup + parent navigation.

    Per TDD Phase 2: Resolves business entities by:
    1. First resolving phone/vertical to Unit GID via UnitResolutionStrategy
    2. Fetching the Unit task to get its parent (Business) GID

    The Unit task's parent reference contains the Business GID.
    """

    def __init__(self, unit_strategy: UnitResolutionStrategy) -> None:
        """Initialize with Unit strategy for delegation.

        Args:
            unit_strategy: UnitResolutionStrategy for phone/vertical lookup.
        """
        self._unit_strategy = unit_strategy

    async def resolve(
        self,
        criteria: list[Any],
        project_gid: str,
        client: "AsanaClient",
    ) -> list[ResolutionResult]:
        """Resolve phone/vertical pairs to Business task GIDs.

        For each criterion:
        1. Resolve to Unit GID using UnitResolutionStrategy
        2. If Unit found, fetch task to get parent (Business) GID
        3. Return Business GID or error if no parent

        Args:
            criteria: List of ResolutionCriterion with phone and vertical
            project_gid: Business project GID (used for logging, not lookup)
            client: AsanaClient for task fetching

        Returns:
            List of ResolutionResult with Business GIDs.
        """
        start_time = time.monotonic()

        if not criteria:
            return []

        # Get unit project GID for delegation
        unit_project_gid = self._get_unit_project_gid()
        if unit_project_gid is None:
            logger.warning(
                "business_resolution_no_unit_project",
                extra={"business_project_gid": project_gid},
            )
            return [
                ResolutionResult(gid=None, error="UNIT_PROJECT_UNAVAILABLE")
                for _ in criteria
            ]

        # First resolve to units
        unit_results = await self._unit_strategy.resolve(
            criteria=criteria,
            project_gid=unit_project_gid,
            client=client,
        )

        # Navigate to parent for each resolved unit
        results: list[ResolutionResult] = []

        for i, unit_result in enumerate(unit_results):
            if unit_result.gid is None:
                # Unit not found - pass through the error
                results.append(unit_result)
                continue

            # Fetch unit task to get parent GID
            try:
                business_gid = await self._get_parent_gid(unit_result.gid, client)
                if business_gid is not None:
                    results.append(ResolutionResult(gid=business_gid))
                else:
                    # Unit exists but has no parent
                    logger.warning(
                        "business_resolution_no_parent",
                        extra={
                            "unit_gid": unit_result.gid,
                            "criterion_index": i,
                        },
                    )
                    results.append(
                        ResolutionResult(gid=None, error="NO_PARENT_BUSINESS")
                    )
            except Exception as e:
                logger.warning(
                    "business_resolution_parent_fetch_failed",
                    extra={
                        "unit_gid": unit_result.gid,
                        "error": str(e),
                    },
                )
                results.append(
                    ResolutionResult(gid=None, error="PARENT_FETCH_FAILED")
                )

        # Log batch completion
        elapsed_ms = (time.monotonic() - start_time) * 1000
        resolved_count = sum(1 for r in results if r.gid is not None)

        logger.info(
            "entity_resolution_batch_complete",
            extra={
                "entity_type": "business",
                "criteria_count": len(criteria),
                "resolved_count": resolved_count,
                "unresolved_count": len(criteria) - resolved_count,
                "duration_ms": round(elapsed_ms, 2),
                "project_gid": project_gid,
            },
        )

        return results

    def validate_criterion(self, criterion: Any) -> str | None:
        """Validate that criterion has phone and vertical (same as Unit).

        Args:
            criterion: ResolutionCriterion to validate

        Returns:
            Error message if invalid, None if valid.
        """
        return self._unit_strategy.validate_criterion(criterion)

    def _get_unit_project_gid(self) -> str | None:
        """Get Unit project GID from EntityProjectRegistry.

        Returns:
            Unit project GID if registered, None otherwise.
        """
        registry = EntityProjectRegistry.get_instance()
        return registry.get_project_gid("unit")

    async def _get_parent_gid(
        self,
        unit_gid: str,
        client: "AsanaClient",
    ) -> str | None:
        """Fetch unit task and extract parent (Business) GID.

        Args:
            unit_gid: Unit task GID
            client: AsanaClient for task fetching

        Returns:
            Business GID if parent exists, None otherwise.
        """
        # Fetch task with parent field
        task = await client.tasks.get_async(
            unit_gid,
            opt_fields=["parent.gid"],
        )

        if task.parent is not None:
            return task.parent.gid

        return None


class OfferResolutionStrategy:
    """Offer resolution via offer_id or phone/vertical + offer_name.

    Per TDD Phase 2: Supports two resolution modes:
    1. Primary: Direct lookup by offer_id custom field
    2. Secondary: Composite lookup via phone/vertical + offer_name discriminator

    Uses DataFrame scan for custom field lookups.
    """

    async def resolve(
        self,
        criteria: list[Any],
        project_gid: str,
        client: "AsanaClient",
    ) -> list[ResolutionResult]:
        """Resolve offer criteria to Offer task GIDs.

        Supports two modes per criterion:
        - offer_id: Direct custom field lookup
        - phone + vertical + offer_name: Composite lookup

        Args:
            criteria: List of ResolutionCriterion with offer fields
            project_gid: Offer project GID
            client: AsanaClient for DataFrame building

        Returns:
            List of ResolutionResult with Offer GIDs.
        """
        start_time = time.monotonic()

        if not criteria:
            return []

        # Build DataFrame for lookups
        df = await self._build_offer_dataframe(project_gid, client)

        if df is None:
            logger.warning(
                "offer_resolution_no_dataframe",
                extra={"project_gid": project_gid},
            )
            return [
                ResolutionResult(gid=None, error="DATAFRAME_UNAVAILABLE")
                for _ in criteria
            ]

        results: list[ResolutionResult] = []

        for criterion in criteria:
            # Validate criterion first
            validation_error = self.validate_criterion(criterion)
            if validation_error:
                results.append(ResolutionResult(gid=None, error="INVALID_CRITERIA"))
                continue

            # Try offer_id lookup first (primary)
            offer_id = getattr(criterion, "offer_id", None)
            if offer_id:
                gid = self._lookup_by_offer_id(df, offer_id)
                results.append(
                    ResolutionResult(
                        gid=gid,
                        error="NOT_FOUND" if gid is None else None,
                    )
                )
                continue

            # Secondary: phone + vertical + offer_name
            phone = getattr(criterion, "phone", None)
            vertical = getattr(criterion, "vertical", None)
            offer_name = getattr(criterion, "offer_name", None)

            gid = self._lookup_by_composite(df, phone, vertical, offer_name)
            results.append(
                ResolutionResult(
                    gid=gid,
                    error="NOT_FOUND" if gid is None else None,
                )
            )

        # Log batch completion
        elapsed_ms = (time.monotonic() - start_time) * 1000
        resolved_count = sum(1 for r in results if r.gid is not None)

        logger.info(
            "entity_resolution_batch_complete",
            extra={
                "entity_type": "offer",
                "criteria_count": len(criteria),
                "resolved_count": resolved_count,
                "unresolved_count": len(criteria) - resolved_count,
                "duration_ms": round(elapsed_ms, 2),
                "project_gid": project_gid,
            },
        )

        return results

    def validate_criterion(self, criterion: Any) -> str | None:
        """Validate offer resolution criterion.

        Valid combinations:
        - offer_id only
        - phone + vertical + offer_name (all three required)

        Args:
            criterion: ResolutionCriterion to validate

        Returns:
            Error message if invalid, None if valid.
        """
        offer_id = getattr(criterion, "offer_id", None)
        phone = getattr(criterion, "phone", None)
        vertical = getattr(criterion, "vertical", None)
        offer_name = getattr(criterion, "offer_name", None)

        # Primary: offer_id
        if offer_id:
            return None

        # Secondary: all three required
        if phone and vertical and offer_name:
            return None

        return (
            "offer resolution requires either offer_id, "
            "or (phone + vertical + offer_name)"
        )

    def _lookup_by_offer_id(self, df: Any, offer_id: str) -> str | None:
        """Lookup Offer GID by offer_id custom field.

        Args:
            df: Polars DataFrame with offer data
            offer_id: Offer identifier to search for

        Returns:
            Task GID if found, None otherwise.
        """
        try:
            # Filter by offer_id column
            if "offer_id" not in df.columns:
                logger.warning("offer_dataframe_missing_offer_id_column")
                return None

            filtered = df.filter(df["offer_id"] == offer_id)
            if len(filtered) > 0:
                gid: str = filtered["gid"][0]
                return gid
            return None
        except Exception as e:
            logger.warning(
                "offer_lookup_by_id_failed",
                extra={"offer_id": offer_id, "error": str(e)},
            )
            return None

    def _lookup_by_composite(
        self,
        df: Any,
        phone: str | None,
        vertical: str | None,
        offer_name: str | None,
    ) -> str | None:
        """Lookup Offer GID by phone/vertical + offer_name.

        Args:
            df: Polars DataFrame with offer data
            phone: Office phone number
            vertical: Business vertical
            offer_name: Offer name discriminator

        Returns:
            Task GID if found, None otherwise.
        """
        try:
            # Check required columns exist
            required_cols = ["office_phone", "vertical", "name", "gid"]
            for col in required_cols:
                if col not in df.columns:
                    logger.warning(
                        "offer_dataframe_missing_column",
                        extra={"column": col},
                    )
                    return None

            # Filter by all three criteria
            filtered = df.filter(
                (df["office_phone"] == phone)
                & (df["vertical"] == vertical)
                & (df["name"] == offer_name)
            )

            if len(filtered) > 0:
                gid: str = filtered["gid"][0]
                return gid
            return None
        except Exception as e:
            logger.warning(
                "offer_lookup_by_composite_failed",
                extra={
                    "phone": phone,
                    "vertical": vertical,
                    "offer_name": offer_name,
                    "error": str(e),
                },
            )
            return None

    async def _build_offer_dataframe(
        self,
        project_gid: str,
        client: "AsanaClient",
    ) -> Any:
        """Build Offer project DataFrame for lookups.

        Args:
            project_gid: Offer project GID
            client: AsanaClient for data fetching

        Returns:
            Polars DataFrame with offer data, or None on failure.
        """
        # Import here to avoid circular imports
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
        from autom8_asana.dataframes.schemas.base import BASE_SCHEMA

        # Minimal project proxy
        class ProjectProxy:
            def __init__(self, gid: str) -> None:
                self.gid = gid
                self.tasks: list[Any] = []

        try:
            project_proxy = ProjectProxy(project_gid)

            # Use base schema since Offer schema not defined yet
            # Include offer_id, office_phone, vertical columns
            builder = ProjectDataFrameBuilder(
                project=project_proxy,
                task_type="Offer",
                schema=BASE_SCHEMA,
            )

            df = await builder.build_with_parallel_fetch_async(client)

            logger.info(
                "offer_dataframe_built",
                extra={
                    "project_gid": project_gid,
                    "row_count": len(df),
                },
            )

            return df

        except Exception as e:
            logger.warning(
                "offer_dataframe_build_failed",
                extra={
                    "project_gid": project_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return None


class ContactResolutionStrategy:
    """Contact resolution via email or phone with multiple matches support.

    Per TDD Phase 2: Looks up contacts by contact_email or contact_phone.
    Returns ALL matches with multiple=true flag when more than one found.
    """

    async def resolve(
        self,
        criteria: list[Any],
        project_gid: str,
        client: "AsanaClient",
    ) -> list[ResolutionResult]:
        """Resolve contact criteria to Contact task GIDs.

        Supports lookup by:
        - contact_email: Email address
        - contact_phone: Phone number

        Per PRD: Returns ALL matches with multiple=true flag.

        Args:
            criteria: List of ResolutionCriterion with contact fields
            project_gid: Contact project GID
            client: AsanaClient for DataFrame building

        Returns:
            List of ResolutionResult with Contact GIDs.
            When multiple matches exist, returns first GID with multiple=true.
        """
        start_time = time.monotonic()

        if not criteria:
            return []

        # Build DataFrame for lookups
        df = await self._build_contact_dataframe(project_gid, client)

        if df is None:
            logger.warning(
                "contact_resolution_no_dataframe",
                extra={"project_gid": project_gid},
            )
            return [
                ResolutionResult(gid=None, error="DATAFRAME_UNAVAILABLE")
                for _ in criteria
            ]

        results: list[ResolutionResult] = []

        for criterion in criteria:
            # Validate criterion first
            validation_error = self.validate_criterion(criterion)
            if validation_error:
                results.append(ResolutionResult(gid=None, error="INVALID_CRITERIA"))
                continue

            # Try email lookup
            contact_email = getattr(criterion, "contact_email", None)
            if contact_email:
                gids = self._lookup_by_email(df, contact_email)
                results.append(self._build_result(gids))
                continue

            # Try phone lookup
            contact_phone = getattr(criterion, "contact_phone", None)
            if contact_phone:
                gids = self._lookup_by_phone(df, contact_phone)
                results.append(self._build_result(gids))
                continue

            # Should not reach here if validation is correct
            results.append(ResolutionResult(gid=None, error="INVALID_CRITERIA"))

        # Log batch completion
        elapsed_ms = (time.monotonic() - start_time) * 1000
        resolved_count = sum(1 for r in results if r.gid is not None)
        multiple_count = sum(1 for r in results if r.multiple is True)

        logger.info(
            "entity_resolution_batch_complete",
            extra={
                "entity_type": "contact",
                "criteria_count": len(criteria),
                "resolved_count": resolved_count,
                "unresolved_count": len(criteria) - resolved_count,
                "multiple_match_count": multiple_count,
                "duration_ms": round(elapsed_ms, 2),
                "project_gid": project_gid,
            },
        )

        return results

    def validate_criterion(self, criterion: Any) -> str | None:
        """Validate contact resolution criterion.

        Valid combinations:
        - contact_email only
        - contact_phone only

        Args:
            criterion: ResolutionCriterion to validate

        Returns:
            Error message if invalid, None if valid.
        """
        contact_email = getattr(criterion, "contact_email", None)
        contact_phone = getattr(criterion, "contact_phone", None)

        if contact_email or contact_phone:
            return None

        return "contact resolution requires either contact_email or contact_phone"

    def _build_result(self, gids: list[str]) -> ResolutionResult:
        """Build ResolutionResult from list of matching GIDs.

        Args:
            gids: List of matching task GIDs

        Returns:
            ResolutionResult with first GID and multiple flag if applicable.
        """
        if not gids:
            return ResolutionResult(gid=None, error="NOT_FOUND")

        if len(gids) == 1:
            return ResolutionResult(gid=gids[0])

        # Multiple matches - return first with flag
        return ResolutionResult(gid=gids[0], multiple=True)

    def _lookup_by_email(self, df: Any, email: str) -> list[str]:
        """Lookup Contact GIDs by contact_email.

        Args:
            df: Polars DataFrame with contact data
            email: Email address to search for

        Returns:
            List of matching task GIDs (may be empty).
        """
        try:
            if "contact_email" not in df.columns:
                logger.warning("contact_dataframe_missing_email_column")
                return []

            filtered = df.filter(df["contact_email"] == email)
            result: list[str] = filtered["gid"].to_list()
            return result
        except Exception as e:
            logger.warning(
                "contact_lookup_by_email_failed",
                extra={"email": email, "error": str(e)},
            )
            return []

    def _lookup_by_phone(self, df: Any, phone: str) -> list[str]:
        """Lookup Contact GIDs by contact_phone.

        Args:
            df: Polars DataFrame with contact data
            phone: Phone number to search for

        Returns:
            List of matching task GIDs (may be empty).
        """
        try:
            if "contact_phone" not in df.columns:
                logger.warning("contact_dataframe_missing_phone_column")
                return []

            filtered = df.filter(df["contact_phone"] == phone)
            result: list[str] = filtered["gid"].to_list()
            return result
        except Exception as e:
            logger.warning(
                "contact_lookup_by_phone_failed",
                extra={"phone": phone, "error": str(e)},
            )
            return []

    async def _build_contact_dataframe(
        self,
        project_gid: str,
        client: "AsanaClient",
    ) -> Any:
        """Build Contact project DataFrame for lookups.

        Args:
            project_gid: Contact project GID
            client: AsanaClient for data fetching

        Returns:
            Polars DataFrame with contact data, or None on failure.
        """
        # Import here to avoid circular imports
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
        from autom8_asana.dataframes.schemas.contact import CONTACT_SCHEMA

        # Minimal project proxy
        class ProjectProxy:
            def __init__(self, gid: str) -> None:
                self.gid = gid
                self.tasks: list[Any] = []

        try:
            project_proxy = ProjectProxy(project_gid)

            builder = ProjectDataFrameBuilder(
                project=project_proxy,
                task_type="Contact",
                schema=CONTACT_SCHEMA,
            )

            df = await builder.build_with_parallel_fetch_async(client)

            logger.info(
                "contact_dataframe_built",
                extra={
                    "project_gid": project_gid,
                    "row_count": len(df),
                },
            )

            return df

        except Exception as e:
            logger.warning(
                "contact_dataframe_build_failed",
                extra={
                    "project_gid": project_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return None


# --- Field Filtering ---


def filter_result_fields(
    result: dict[str, Any],
    requested_fields: list[str] | None,
    entity_type: str,
) -> dict[str, Any]:
    """Filter result to requested fields only with SchemaRegistry validation.

    Per TDD: Validates requested fields against SchemaRegistry schema.
    Always includes 'gid' field regardless of request.

    Args:
        result: Full result dict with all available fields
        requested_fields: List of field names to include (None = gid only)
        entity_type: Entity type for schema lookup (e.g., "unit")

    Returns:
        Filtered dict with only requested fields + gid.

    Raises:
        ValueError: If requested field not in schema (INVALID_FIELD error).
    """
    if not requested_fields:
        # Default: gid only
        return {"gid": result.get("gid")}

    # Validate fields against schema
    from autom8_asana.dataframes.models.registry import SchemaRegistry

    registry = SchemaRegistry.get_instance()

    # Convert entity_type to schema key (e.g., "unit" -> "Unit")
    schema_key = entity_type.title()

    try:
        schema = registry.get_schema(schema_key)
        valid_fields = {col.name for col in schema.columns}
    except Exception:
        # Fall back to base schema if entity-specific not found
        schema = registry.get_schema("*")
        valid_fields = {col.name for col in schema.columns}

    # Check for invalid fields
    invalid = set(requested_fields) - valid_fields - {"gid"}
    if invalid:
        raise ValueError(
            f"Invalid fields: {sorted(invalid)}. "
            f"Available: {sorted(valid_fields)}"
        )

    # Always include gid
    fields_to_include = set(requested_fields) | {"gid"}

    return {k: v for k, v in result.items() if k in fields_to_include}


# --- Strategy Dispatch ---

# Strategy registry dict - simple dispatch without over-engineering
RESOLUTION_STRATEGIES: dict[str, ResolutionStrategy] = {}


def get_strategy(entity_type: str) -> ResolutionStrategy | None:
    """Get resolution strategy for entity type.

    Args:
        entity_type: Entity type identifier (e.g., "unit")

    Returns:
        ResolutionStrategy if registered, None otherwise.
    """
    return RESOLUTION_STRATEGIES.get(entity_type)


def register_strategies() -> None:
    """Register all resolution strategies.

    Called at module load time to populate RESOLUTION_STRATEGIES.
    Phase 1: UnitResolutionStrategy
    Phase 2: Business, Offer, Contact strategies
    """
    global RESOLUTION_STRATEGIES

    # Phase 1: Unit resolution
    unit_strategy = UnitResolutionStrategy()
    RESOLUTION_STRATEGIES["unit"] = unit_strategy

    # Phase 2: Business resolution (delegates to Unit + parent navigation)
    business_strategy = BusinessResolutionStrategy(unit_strategy)
    RESOLUTION_STRATEGIES["business"] = business_strategy

    # Phase 2: Offer resolution (offer_id or phone/vertical/offer_name)
    offer_strategy = OfferResolutionStrategy()
    RESOLUTION_STRATEGIES["offer"] = offer_strategy

    # Phase 2: Contact resolution (email or phone, with multiple flag)
    contact_strategy = ContactResolutionStrategy()
    RESOLUTION_STRATEGIES["contact"] = contact_strategy

    logger.debug(
        "resolution_strategies_registered",
        extra={"strategies": list(RESOLUTION_STRATEGIES.keys())},
    )


# Register strategies on module import
register_strategies()
