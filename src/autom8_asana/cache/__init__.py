"""Intelligent caching layer for the autom8_asana SDK.

This module provides versioned caching with staleness detection,
configurable TTLs, and support for multiple backends (Redis, in-memory).

Public API:
    - CacheEntry: Immutable cache entry with version metadata
    - EntryType: Enum of cacheable entry types
    - Freshness: Enum for cache freshness modes (strict/eventual)
    - CacheSettings: Configuration for caching behavior
    - CacheMetrics: Thread-safe metrics aggregator
    - CacheEvent: Individual cache operation event

Multi-entry Loading:
    - load_task_entry: Load single cache entry with fetch-on-miss
    - load_task_entries: Load multiple entry types concurrently
    - load_batch_entries: Load entries for multiple tasks with batch fetch

Staleness Detection:
    - check_entry_staleness: Check if single entry is stale
    - check_batch_staleness: Check staleness for multiple tasks
    - partition_by_staleness: Split GIDs into stale/current lists

Batch Modification Checking:
    - ModificationCheckCache: TTL-cached modification timestamps
    - fetch_task_modifications: Fetch timestamps with caching
    - ttl_cached_modifications: Decorator for cached fetchers

Incremental Story Loading (ADR-0020):
    - load_stories_incremental: Load stories with 'since' parameter
    - filter_relevant_stories: Filter to dataframe-relevant story types
    - get_latest_story_timestamp: Get latest story timestamp

Dataframe Caching (ADR-0021):
    - make_dataframe_key: Create composite cache key for dataframe
    - load_dataframe_cached: Load dataframe with cache support
    - invalidate_dataframe: Invalidate dataframe for task+project
    - invalidate_task_dataframes: Invalidate dataframe across projects

Cache Event Integration (ADR-0023):
    - create_metrics_callback: Create callback for LogProvider
    - setup_cache_logging: Wire metrics to log provider
    - has_cache_logging: Check if provider supports cache logging

autom8 Integration (ADR-0025):
    - create_autom8_cache_provider: Create Redis provider for autom8
    - migrate_task_collection_loading: Migrate load_task_collection()
    - warm_project_tasks: Pre-warm cache for a project
    - check_redis_health: Check Redis connection health
    - MigrationResult: Result of migration operation

Two-Tier Caching (ADR-0026):
    - TieredCacheProvider: Coordinates Redis (hot) and S3 (cold) tiers
    - TieredConfig: Configuration for two-tier caching behavior

Example:
    >>> from autom8_asana.cache import (
    ...     CacheEntry,
    ...     EntryType,
    ...     Freshness,
    ...     CacheSettings,
    ... )
    >>> settings = CacheSettings()
    >>> settings.get_ttl(project_gid="123456")
    300
"""

# DataFrame entity caching (TDD-DATAFRAME-CACHE-001)
# Import subpackage to expose for test patching (e.g., autom8_asana.cache.dataframe.factory)
from autom8_asana.cache import dataframe  # noqa: F401

# --- Tier 3: Integration ---
from autom8_asana.cache.integration.autom8_adapter import (
    MigrationResult,
    MissingConfigurationError,
    check_redis_health,
    create_autom8_cache_provider,
    migrate_task_collection_loading,
    warm_project_tasks,
)
from autom8_asana.cache.integration.batch import (
    DEFAULT_MODIFICATION_CHECK_TTL,
    ModificationCheck,
    ModificationCheckCache,
    fetch_task_modifications,
    get_modification_cache,
    reset_modification_cache,
    ttl_cached_modifications,
)
from autom8_asana.cache.integration.dataframes import (
    invalidate_dataframe,
    invalidate_task_dataframes,
    load_batch_dataframes_cached,
    load_dataframe_cached,
    make_dataframe_key,
    parse_dataframe_key,
)
from autom8_asana.cache.integration.derived import (
    get_cached_timelines,
    make_derived_timeline_key,
    store_derived_timelines,
)

# --- Re-exports ---
# CacheProviderFactory and MutationInvalidator are public API surface of the cache package.
from autom8_asana.cache.integration.factory import CacheProviderFactory
from autom8_asana.cache.integration.freshness_coordinator import FreshnessMode
from autom8_asana.cache.integration.loader import (
    load_batch_entries,
    load_task_entries,
    load_task_entry,
)
from autom8_asana.cache.integration.mutation_invalidator import MutationInvalidator
from autom8_asana.cache.integration.stories import (
    DEFAULT_STORY_TYPES,
    filter_relevant_stories,
    get_latest_story_timestamp,
    load_stories_incremental,
    read_cached_stories,
    read_stories_batch,
)
from autom8_asana.cache.integration.upgrader import AsanaTaskUpgrader

# --- Tier 0: Models ---
from autom8_asana.cache.models.completeness import (
    FULL_FIELDS,
    MINIMAL_FIELDS,
    STANDARD_FIELDS,
    CompletenessLevel,
    create_completeness_metadata,
    get_entry_completeness,
    get_fields_for_level,
    infer_completeness_level,
    is_entry_sufficient,
)
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.events import (
    create_metrics_callback,
    has_cache_logging,
    setup_cache_logging,
)
from autom8_asana.cache.models.freshness import Freshness
from autom8_asana.cache.models.freshness_unified import FreshnessIntent, FreshnessState
from autom8_asana.cache.models.metrics import CacheEvent, CacheMetrics
from autom8_asana.cache.models.settings import (
    CacheSettings,
    OverflowSettings,
    TTLSettings,
)
from autom8_asana.cache.models.staleness_settings import StalenessCheckSettings
from autom8_asana.cache.models.versioning import (
    compare_versions,
    format_version,
    is_current,
    is_stale,
    parse_version,
)

# --- Tier 1: Policies ---
from autom8_asana.cache.policies.coalescer import RequestCoalescer
from autom8_asana.cache.policies.hierarchy import HierarchyIndex
from autom8_asana.cache.policies.lightweight_checker import LightweightChecker
from autom8_asana.cache.policies.staleness import (
    check_batch_staleness,
    check_entry_staleness,
    partition_by_staleness,
)

# --- Tier 2: Providers ---
from autom8_asana.cache.providers.tiered import TieredCacheProvider, TieredConfig
from autom8_asana.cache.providers.unified import UnifiedTaskStore

# IMPORTANT: register_asana_schemas is defined via __getattr__ below to avoid circular import
# (schema_providers -> dataframes -> models.business -> cache)

# SDK Primitives (TDD-CACHE-SDK-PRIMITIVES-001)
# Re-export SDK HierarchyTracker for advanced use cases
# HOTFIX: Make import defensive for Lambda compatibility when autom8y_cache
# has missing modules (e.g., protocols.resolver in version mismatch scenarios)
try:
    from autom8y_cache import HierarchyTracker
except ImportError:
    HierarchyTracker = None  # type: ignore[misc, assignment]

__all__ = [
    # Entry types
    "CacheEntry",
    "EntryType",
    # Freshness modes
    "Freshness",
    "FreshnessIntent",
    "FreshnessState",
    # Settings
    "CacheSettings",
    "TTLSettings",
    "OverflowSettings",
    # Metrics
    "CacheMetrics",
    "CacheEvent",
    # Versioning utilities
    "compare_versions",
    "parse_version",
    "format_version",
    "is_stale",
    "is_current",
    # Staleness detection
    "check_entry_staleness",
    "check_batch_staleness",
    "partition_by_staleness",
    # Multi-entry loading
    "load_task_entry",
    "load_task_entries",
    "load_batch_entries",
    # Batch modification checking
    "ModificationCheck",
    "ModificationCheckCache",
    "fetch_task_modifications",
    "get_modification_cache",
    "reset_modification_cache",
    "ttl_cached_modifications",
    "DEFAULT_MODIFICATION_CHECK_TTL",
    # Incremental story loading (ADR-0020)
    "load_stories_incremental",
    "read_cached_stories",
    "read_stories_batch",
    "filter_relevant_stories",
    "get_latest_story_timestamp",
    "DEFAULT_STORY_TYPES",
    # Derived timeline cache (TDD-SECTION-TIMELINE-REMEDIATION)
    "make_derived_timeline_key",
    "get_cached_timelines",
    "store_derived_timelines",
    # Dataframe caching (ADR-0021)
    "make_dataframe_key",
    "parse_dataframe_key",
    "load_dataframe_cached",
    "load_batch_dataframes_cached",
    "invalidate_dataframe",
    "invalidate_task_dataframes",
    # Cache event integration (ADR-0023)
    "create_metrics_callback",
    "setup_cache_logging",
    "has_cache_logging",
    # autom8 integration adapter (ADR-0025)
    "create_autom8_cache_provider",
    "migrate_task_collection_loading",
    "warm_project_tasks",
    "check_redis_health",
    "MigrationResult",
    "MissingConfigurationError",
    # Two-tier caching (ADR-0026)
    "TieredCacheProvider",
    "TieredConfig",
    # Lightweight staleness detection (TDD-CACHE-LIGHTWEIGHT-STALENESS)
    "StalenessCheckSettings",
    "LightweightChecker",
    "RequestCoalescer",
    # Unified cache (TDD-UNIFIED-CACHE-001, MIGRATION-PLAN-legacy-cache-elimination RF-003)
    "UnifiedTaskStore",
    "FreshnessMode",
    "HierarchyIndex",
    # Completeness tracking (TDD-CACHE-COMPLETENESS-001)
    "CompletenessLevel",
    "MINIMAL_FIELDS",
    "STANDARD_FIELDS",
    "FULL_FIELDS",
    "infer_completeness_level",
    "get_entry_completeness",
    "is_entry_sufficient",
    "create_completeness_metadata",
    "get_fields_for_level",
    # SDK Primitives (TDD-CACHE-SDK-PRIMITIVES-001)
    "HierarchyTracker",
    "AsanaTaskUpgrader",
    # Re-exports for Read-Only Zone (api/main.py)
    "CacheProviderFactory",
    "MutationInvalidator",
    "register_asana_schemas",
]


def __getattr__(name: str) -> object:
    """Lazy import to avoid circular dependency with schema_providers.

    schema_providers -> dataframes -> models.business -> cache

    By deferring the import until first access, we break the cycle.
    """
    if name == "register_asana_schemas":
        from autom8_asana.cache.integration.schema_providers import (
            register_asana_schemas,
        )

        return register_asana_schemas
    elif name == "dataframe_cache":
        # Provide the moved module for backward compatibility
        from autom8_asana.cache.integration import dataframe_cache

        return dataframe_cache
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
