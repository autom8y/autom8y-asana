"""Cache tier implementations for DataFrame caching.

Per TDD-DATAFRAME-CACHE-001 and TDD-UNIFIED-PROGRESSIVE-CACHE-001:
Provides tiered storage for DataFrames with Memory (hot) and
Progressive (cold) tiers.

Tiers:
    - MemoryTier: LRU cache with dynamic heap-based limits
    - ProgressiveTier: S3 storage via SectionPersistence (replaces S3Tier)

Example:
    >>> from autom8_asana.cache.dataframe.tiers import MemoryTier, ProgressiveTier
    >>> from autom8_asana.dataframes.section_persistence import SectionPersistence
    >>>
    >>> memory = MemoryTier(max_heap_percent=0.3)
    >>> persistence = SectionPersistence(bucket="cache-bucket")
    >>> progressive = ProgressiveTier(persistence=persistence)
"""

from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier

__all__ = [
    "MemoryTier",
    "ProgressiveTier",
]
