"""DataFrame caching module for entity resolution.

Per TDD-DATAFRAME-CACHE-001: Provides tiered caching infrastructure
for DataFrame-backed entity resolution with Memory + S3 storage.

Components:
    - DataFrameCacheCoalescer: Build request coalescing (thundering herd prevention)
    - CircuitBreaker: Per-project failure isolation
    - dataframe_cache: Class decorator for resolution strategies
    - CacheWarmer: Priority-based pre-warming for Lambda deployment

Tiers:
    - MemoryTier: Hot cache with LRU eviction and heap-based limits
    - S3Tier: Cold storage with Parquet serialization

Example:
    >>> from autom8_asana.cache.dataframe import (
    ...     DataFrameCacheCoalescer,
    ...     CircuitBreaker,
    ...     dataframe_cache,
    ...     CacheWarmer,
    ...     WarmResult,
    ...     WarmStatus,
    ... )
    >>> from autom8_asana.cache.dataframe.tiers import MemoryTier, S3Tier
"""

from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker, CircuitState
from autom8_asana.cache.dataframe.decorator import dataframe_cache
from autom8_asana.cache.dataframe.warmer import CacheWarmer, WarmResult, WarmStatus

__all__ = [
    "DataFrameCacheCoalescer",
    "CircuitBreaker",
    "CircuitState",
    "dataframe_cache",
    "CacheWarmer",
    "WarmResult",
    "WarmStatus",
]
