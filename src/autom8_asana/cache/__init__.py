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

# autom8 integration adapter (ADR-0025)
from autom8_asana.cache.autom8_adapter import (
    MigrationResult,
    MissingConfigurationError,
    check_redis_health,
    create_autom8_cache_provider,
    migrate_task_collection_loading,
    warm_project_tasks,
)
from autom8_asana.cache.batch import (
    DEFAULT_MODIFICATION_CHECK_TTL,
    ModificationCheck,
    ModificationCheckCache,
    fetch_task_modifications,
    get_modification_cache,
    reset_modification_cache,
    ttl_cached_modifications,
)

# Lightweight staleness detection (TDD-CACHE-LIGHTWEIGHT-STALENESS)
from autom8_asana.cache.coalescer import RequestCoalescer

# Completeness tracking (TDD-CACHE-COMPLETENESS-001)
from autom8_asana.cache.completeness import (
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
from autom8_asana.cache.dataframes import (
    invalidate_dataframe,
    invalidate_task_dataframes,
    load_batch_dataframes_cached,
    load_dataframe_cached,
    make_dataframe_key,
    parse_dataframe_key,
)
from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.events import (
    create_metrics_callback,
    has_cache_logging,
    setup_cache_logging,
)
from autom8_asana.cache.freshness import Freshness

# Unified cache (TDD-UNIFIED-CACHE-001, MIGRATION-PLAN-legacy-cache-elimination RF-003)
from autom8_asana.cache.freshness_coordinator import FreshnessMode
from autom8_asana.cache.hierarchy import HierarchyIndex
from autom8_asana.cache.lightweight_checker import LightweightChecker
from autom8_asana.cache.loader import (
    load_batch_entries,
    load_task_entries,
    load_task_entry,
)
from autom8_asana.cache.metrics import CacheEvent, CacheMetrics
from autom8_asana.cache.settings import CacheSettings, OverflowSettings, TTLSettings
from autom8_asana.cache.staleness import (
    check_batch_staleness,
    check_entry_staleness,
    partition_by_staleness,
)
from autom8_asana.cache.staleness_settings import StalenessCheckSettings
from autom8_asana.cache.stories import (
    DEFAULT_STORY_TYPES,
    filter_relevant_stories,
    get_latest_story_timestamp,
    load_stories_incremental,
)

# Two-tier caching (ADR-0026)
from autom8_asana.cache.tiered import TieredCacheProvider, TieredConfig
from autom8_asana.cache.unified import UnifiedTaskStore
from autom8_asana.cache.versioning import (
    compare_versions,
    format_version,
    is_current,
    is_stale,
    parse_version,
)

# SDK Primitives (TDD-CACHE-SDK-PRIMITIVES-001)
# Re-export SDK HierarchyTracker for advanced use cases
# HOTFIX: Make import defensive for Lambda compatibility when autom8y_cache
# has missing modules (e.g., protocols.resolver in version mismatch scenarios)
try:
    from autom8y_cache import HierarchyTracker
except ImportError:
    HierarchyTracker = None  # type: ignore[misc, assignment]

# Completeness upgrader implementation
from autom8_asana.cache.upgrader import AsanaTaskUpgrader

__all__ = [
    # Entry types
    "CacheEntry",
    "EntryType",
    # Freshness modes
    "Freshness",
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
    "filter_relevant_stories",
    "get_latest_story_timestamp",
    "DEFAULT_STORY_TYPES",
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
]
