"""Cache data models, enums, and value objects.

LAYER RULE: models/ must NOT import from policies/, providers/, or integration/.
It may import from stdlib, autom8y_cache, autom8y_log, and autom8_asana.core.
"""

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
from autom8_asana.cache.models.entry import (
    CacheEntry,
    DataFrameMetaCacheEntry,
    DetectionCacheEntry,
    EntityCacheEntry,
    EntryType,
    RelationshipCacheEntry,
)
from autom8_asana.cache.models.errors import (
    DegradedModeMixin,
    is_connection_error,
    is_s3_not_found_error,
    is_s3_retryable_error,
)
from autom8_asana.cache.models.events import (
    create_metrics_callback,
    has_cache_logging,
    setup_cache_logging,
)
from autom8_asana.cache.models.freshness import Freshness
from autom8_asana.cache.models.freshness_stamp import (
    FreshnessClassification,
    FreshnessStamp,
    VerificationSource,
)
from autom8_asana.cache.models.metrics import CacheEvent, CacheMetrics
from autom8_asana.cache.models.mutation_event import (
    EntityKind,
    MutationEvent,
    MutationType,
)
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

__all__ = [
    "CacheEntry",
    "EntityCacheEntry",
    "RelationshipCacheEntry",
    "DataFrameMetaCacheEntry",
    "DetectionCacheEntry",
    "EntryType",
    "Freshness",
    "FreshnessStamp",
    "FreshnessClassification",
    "VerificationSource",
    "MutationEvent",
    "EntityKind",
    "MutationType",
    "CacheMetrics",
    "CacheEvent",
    "DegradedModeMixin",
    "is_connection_error",
    "is_s3_not_found_error",
    "is_s3_retryable_error",
    "CacheSettings",
    "TTLSettings",
    "OverflowSettings",
    "StalenessCheckSettings",
    "CompletenessLevel",
    "MINIMAL_FIELDS",
    "STANDARD_FIELDS",
    "FULL_FIELDS",
    "infer_completeness_level",
    "get_entry_completeness",
    "is_entry_sufficient",
    "create_completeness_metadata",
    "get_fields_for_level",
    "compare_versions",
    "parse_version",
    "format_version",
    "is_stale",
    "is_current",
    "create_metrics_callback",
    "setup_cache_logging",
    "has_cache_logging",
]
