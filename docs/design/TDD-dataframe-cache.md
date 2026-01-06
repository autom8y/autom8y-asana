# TDD: DataFrame Caching Architecture

**TDD ID**: TDD-DATAFRAME-CACHE-001
**Version**: 1.0
**Date**: 2026-01-06
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: N/A (Technical initiative from stakeholder interview)

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Goals and Non-Goals](#goals-and-non-goals)
4. [Proposed Architecture](#proposed-architecture)
5. [Component Designs](#component-designs)
6. [Interface Contracts](#interface-contracts)
7. [Data Flow Diagrams](#data-flow-diagrams)
8. [Non-Functional Considerations](#non-functional-considerations)
9. [Migration Strategy](#migration-strategy)
10. [Test Strategy](#test-strategy)
11. [Implementation Phases](#implementation-phases)
12. [Risk Assessment](#risk-assessment)
13. [ADRs](#adrs)
14. [Success Criteria](#success-criteria)

---

## Overview

This TDD specifies a unified DataFrame caching architecture that provides consistent, performant entity resolution across all four entity types (Unit, Business, Offer, Contact). The design introduces tiered caching (Memory + S3 with Parquet format), a class decorator pattern for resolution strategies, and comprehensive observability.

### Solution Summary

| Component | Purpose |
|-----------|---------|
| `DataFrameCache` | Main cache manager with tiered storage orchestration |
| `@dataframe_cache` | Class decorator for resolution strategies |
| `MemoryTier` | Hot cache with dynamic heap-based limits and LRU eviction |
| `S3Tier` | Cold storage with Parquet serialization (source of truth) |
| `RequestCoalescer` | Thundering herd prevention via first-request-builds pattern |
| `CircuitBreaker` | Per-project failure isolation |
| `CacheWarmer` | Priority-based pre-warming for Lambda deployment |

---

## Problem Statement

### Current State

The Entity Resolver system (per TDD-entity-resolver) has inconsistent caching across entity types:

| Entity Type | Current Cache Strategy | Performance |
|-------------|------------------------|-------------|
| Unit | `_gid_index_cache` with TTL (resolver.py:60-63) | O(1) via GidLookupIndex |
| Business | Delegates to Unit + parent navigation | O(1) + API call |
| Offer | **NO CACHING** - full DataFrame rebuild every request | O(n) per request |
| Contact | **NO CACHING** - full DataFrame rebuild every request | O(n) per request |

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py`

```python
# Lines 57-63: Current module-level cache (Unit only)
_gid_index_cache: dict[str, GidLookupIndex] = {}
_INDEX_TTL_SECONDS = 3600
```

**Problem**: Offer and Contact resolution strategies call `_build_offer_dataframe()` and `_build_contact_dataframe()` on EVERY request. For projects with 10-50K tasks, this means:
- 2-10 second latency per request
- Unnecessary Asana API load
- Poor user experience for batch operations

### Gap Analysis

| Capability | Unit/Business | Offer/Contact | Target |
|------------|---------------|---------------|--------|
| Memory caching | Yes (1hr TTL) | No | All entity types |
| Persistent storage | No | No | S3 Parquet |
| Watermark-based freshness | Yes (incremental) | No | All entity types |
| Cache warming | Manual | N/A | Lambda pre-deploy |
| Observability | Basic logging | None | Full metrics |

---

## Goals and Non-Goals

### Goals

| ID | Goal | Rationale |
|----|------|-----------|
| G1 | Unified caching for all 4 entity types | Eliminate per-strategy inconsistency |
| G2 | Tiered storage (Memory + S3) | Hot cache for speed, S3 for durability |
| G3 | Replace `_gid_index_cache` completely | Single cache abstraction |
| G4 | Request coalescing for thundering herd | Prevent duplicate builds |
| G5 | Circuit breaker per-project | Isolate failures |
| G6 | Lambda warm-up integration | Pre-deploy cache hydration |
| G7 | Comprehensive observability | Hit/miss rates, latencies, sizes |

### Non-Goals

| ID | Non-Goal | Reason |
|----|----------|--------|
| NG1 | Redis integration | Deferred to future phase |
| NG2 | Query-level caching | Cache at DataFrame level only |
| NG3 | Row-level caching | DataFrame-level granularity |
| NG4 | Local CLI warming | Lambda-only warming |
| NG5 | Partial data acceptance | All-or-nothing cache entries |

---

## Proposed Architecture

### System Diagram

```
                           Resolution Request
                                   |
                                   v
         +--------------------------------------------------+
         |            Resolution Strategy                    |
         |           (with @dataframe_cache)                |
         +--------------------------------------------------+
                                   |
                                   v
         +--------------------------------------------------+
         |               DataFrameCache                      |
         |                                                   |
         |  +-------------+  +-------------+  +----------+  |
         |  |RequestCoales|  |CircuitBreaker| |Invalidator| |
         |  +-------------+  +-------------+  +----------+  |
         |         |                |                       |
         |         v                v                       |
         |  +-------------------------------------------+   |
         |  |             CacheTierManager              |   |
         |  +-------------------------------------------+   |
         |         |                        |               |
         |         v                        v               |
         |  +-------------+         +-------------+         |
         |  | MemoryTier  |         |   S3Tier    |         |
         |  | (Hot Cache) |         | (Parquet)   |         |
         |  +-------------+         +-------------+         |
         +--------------------------------------------------+
                                   |
                     (on miss: async build)
                                   v
         +--------------------------------------------------+
         |          ProjectDataFrameBuilder                  |
         |         (existing infrastructure)                 |
         +--------------------------------------------------+
                                   |
                                   v
         +--------------------------------------------------+
         |                  Asana API                        |
         +--------------------------------------------------+
```

### Cache Tier Flow

```
GET Request:
  1. Check MemoryTier (hot cache)
     - Hit: Return DataFrame, record metric
     - Miss: Continue to step 2

  2. Check S3Tier (cold storage)
     - Hit: Load Parquet, hydrate MemoryTier, return DataFrame
     - Miss: Continue to step 3

  3. RequestCoalescer
     - If build in progress: Wait for completion
     - Else: Trigger async build via Lambda, return 503

PUT Flow (after build):
  1. Write to S3Tier (Parquet format)
  2. Write to MemoryTier
  3. Update watermark
```

---

## Component Designs

### 5.1 DataFrameCache

**Module**: `src/autom8_asana/cache/dataframe_cache.py`

The main cache manager orchestrating tiered storage, coalescing, and circuit breaking.

```python
"""DataFrame caching with tiered storage for entity resolution.

Per TDD-DATAFRAME-CACHE-001: Provides unified caching for all entity types
with Memory + S3 tiering, request coalescing, and circuit breaker patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import polars as pl
from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.cache.dataframe.coalescer import RequestCoalescer
    from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
    from autom8_asana.cache.dataframe.tiers import MemoryTier, S3Tier

logger = get_logger(__name__)


@runtime_checkable
class DataFrameProvider(Protocol):
    """Protocol for DataFrame-backed caching.

    Default implementation uses Polars. Satellites may provide
    alternative implementations (e.g., for testing).
    """

    def to_bytes(self, df: pl.DataFrame) -> bytes:
        """Serialize DataFrame to bytes (Parquet format)."""
        ...

    def from_bytes(self, data: bytes) -> pl.DataFrame:
        """Deserialize bytes to DataFrame."""
        ...


@dataclass
class CacheEntry:
    """Single DataFrame cache entry with metadata."""

    project_gid: str
    entity_type: str
    dataframe: pl.DataFrame
    watermark: datetime
    created_at: datetime
    schema_version: str
    row_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.row_count = len(self.dataframe)

    def is_stale(self, ttl_seconds: int) -> bool:
        """Check if entry has exceeded TTL."""
        age = datetime.now(timezone.utc) - self.created_at
        return age.total_seconds() > ttl_seconds

    def is_fresh_by_watermark(self, current_watermark: datetime) -> bool:
        """Check if entry is fresh based on watermark comparison."""
        return self.watermark >= current_watermark


@dataclass
class DataFrameCache:
    """Unified DataFrame cache with tiered storage.

    Per TDD-DATAFRAME-CACHE-001:
    - Memory tier for hot cache (sub-millisecond access)
    - S3 tier for cold storage (source of truth, Parquet format)
    - Request coalescing to prevent thundering herd
    - Circuit breaker for failure isolation

    Attributes:
        memory_tier: Hot cache with dynamic heap-based limits.
        s3_tier: Cold storage with Parquet serialization.
        coalescer: Request coalescing for build deduplication.
        circuit_breaker: Per-project failure isolation.
        ttl_hours: Default TTL in hours (12-24 configurable).
        schema_version: Current schema version for invalidation.

    Example:
        >>> cache = DataFrameCache(
        ...     memory_tier=MemoryTier(max_heap_percent=0.3),
        ...     s3_tier=S3Tier(bucket="cache-bucket", prefix="dataframes/"),
        ...     ttl_hours=12,
        ... )
        >>>
        >>> # Get DataFrame (tries memory, then S3, then builds)
        >>> df = await cache.get_async("project-123", "unit")
        >>>
        >>> # Store after build
        >>> await cache.put_async("project-123", "unit", df, watermark)
    """

    memory_tier: "MemoryTier"
    s3_tier: "S3Tier"
    coalescer: "RequestCoalescer"
    circuit_breaker: "CircuitBreaker"
    ttl_hours: int = 12
    schema_version: str = "1.0.0"

    # Statistics
    _stats: dict[str, dict[str, int]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize per-entity-type statistics."""
        for entity_type in ["unit", "business", "offer", "contact"]:
            self._stats[entity_type] = {
                "memory_hits": 0,
                "memory_misses": 0,
                "s3_hits": 0,
                "s3_misses": 0,
                "builds_triggered": 0,
                "builds_coalesced": 0,
                "circuit_breaks": 0,
                "invalidations": 0,
            }

    async def get_async(
        self,
        project_gid: str,
        entity_type: str,
        current_watermark: datetime | None = None,
    ) -> CacheEntry | None:
        """Get cached DataFrame entry.

        Lookup order:
        1. Memory tier (hot cache)
        2. S3 tier (cold storage)
        3. Return None (caller should trigger build)

        Args:
            project_gid: Asana project GID.
            entity_type: Entity type (unit, business, offer, contact).
            current_watermark: Optional watermark for freshness check.

        Returns:
            CacheEntry if found and fresh, None otherwise.
        """
        cache_key = self._build_key(project_gid, entity_type)

        # Check circuit breaker
        if self.circuit_breaker.is_open(project_gid):
            self._stats[entity_type]["circuit_breaks"] += 1
            logger.warning(
                "dataframe_cache_circuit_open",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                },
            )
            return None

        # Try memory tier first
        entry = self.memory_tier.get(cache_key)
        if entry is not None:
            # Validate freshness
            if self._is_valid(entry, current_watermark):
                self._stats[entity_type]["memory_hits"] += 1
                logger.debug(
                    "dataframe_cache_memory_hit",
                    extra={
                        "project_gid": project_gid,
                        "entity_type": entity_type,
                        "row_count": entry.row_count,
                    },
                )
                return entry
            else:
                # Stale - remove from memory
                self.memory_tier.remove(cache_key)

        self._stats[entity_type]["memory_misses"] += 1

        # Try S3 tier
        entry = await self.s3_tier.get_async(cache_key)
        if entry is not None:
            if self._is_valid(entry, current_watermark):
                self._stats[entity_type]["s3_hits"] += 1
                # Hydrate memory tier
                self.memory_tier.put(cache_key, entry)
                logger.info(
                    "dataframe_cache_s3_hit",
                    extra={
                        "project_gid": project_gid,
                        "entity_type": entity_type,
                        "row_count": entry.row_count,
                    },
                )
                return entry

        self._stats[entity_type]["s3_misses"] += 1
        return None

    async def put_async(
        self,
        project_gid: str,
        entity_type: str,
        dataframe: pl.DataFrame,
        watermark: datetime,
    ) -> None:
        """Store DataFrame in both tiers.

        Write order:
        1. S3 tier (source of truth)
        2. Memory tier (hot cache)

        Args:
            project_gid: Asana project GID.
            entity_type: Entity type.
            dataframe: Polars DataFrame to cache.
            watermark: Freshness watermark (modified_at based).
        """
        cache_key = self._build_key(project_gid, entity_type)

        entry = CacheEntry(
            project_gid=project_gid,
            entity_type=entity_type,
            dataframe=dataframe,
            watermark=watermark,
            created_at=datetime.now(timezone.utc),
            schema_version=self.schema_version,
        )

        # Write to S3 first (source of truth)
        await self.s3_tier.put_async(cache_key, entry)

        # Then memory tier
        self.memory_tier.put(cache_key, entry)

        # Clear circuit breaker on successful write
        self.circuit_breaker.close(project_gid)

        logger.info(
            "dataframe_cache_put",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type,
                "row_count": entry.row_count,
                "watermark": watermark.isoformat(),
            },
        )

    def invalidate(
        self,
        project_gid: str,
        entity_type: str | None = None,
    ) -> None:
        """Invalidate cache entries.

        Args:
            project_gid: Project to invalidate.
            entity_type: Optional specific entity type. If None, all types.
        """
        entity_types = (
            [entity_type] if entity_type else
            ["unit", "business", "offer", "contact"]
        )

        for et in entity_types:
            cache_key = self._build_key(project_gid, et)
            self.memory_tier.remove(cache_key)
            # Note: S3 entries not deleted, just superseded on next write
            self._stats[et]["invalidations"] += 1

        logger.info(
            "dataframe_cache_invalidate",
            extra={
                "project_gid": project_gid,
                "entity_types": entity_types,
            },
        )

    def invalidate_on_schema_change(self, new_version: str) -> None:
        """Invalidate all entries when schema version changes.

        Per TDD: Auto-invalidate on version bump.

        Args:
            new_version: New schema version string.
        """
        if new_version != self.schema_version:
            logger.info(
                "dataframe_cache_schema_invalidation",
                extra={
                    "old_version": self.schema_version,
                    "new_version": new_version,
                },
            )
            self.memory_tier.clear()
            self.schema_version = new_version

    async def acquire_build_lock_async(
        self,
        project_gid: str,
        entity_type: str,
    ) -> bool:
        """Attempt to acquire build lock via coalescer.

        Returns True if this request should perform the build.
        Returns False if another request is building (wait for it).

        Args:
            project_gid: Project to build.
            entity_type: Entity type to build.

        Returns:
            True if caller should build, False if should wait.
        """
        cache_key = self._build_key(project_gid, entity_type)
        acquired = await self.coalescer.try_acquire_async(cache_key)

        if acquired:
            self._stats[entity_type]["builds_triggered"] += 1
        else:
            self._stats[entity_type]["builds_coalesced"] += 1

        return acquired

    async def release_build_lock_async(
        self,
        project_gid: str,
        entity_type: str,
        success: bool,
    ) -> None:
        """Release build lock and notify waiters.

        Args:
            project_gid: Project that was built.
            entity_type: Entity type that was built.
            success: Whether build succeeded.
        """
        cache_key = self._build_key(project_gid, entity_type)
        await self.coalescer.release_async(cache_key, success)

        if not success:
            self.circuit_breaker.record_failure(project_gid)

    async def wait_for_build_async(
        self,
        project_gid: str,
        entity_type: str,
        timeout_seconds: float = 30.0,
    ) -> CacheEntry | None:
        """Wait for in-progress build to complete.

        Args:
            project_gid: Project being built.
            entity_type: Entity type being built.
            timeout_seconds: Maximum wait time.

        Returns:
            CacheEntry if build succeeded, None on timeout/failure.
        """
        cache_key = self._build_key(project_gid, entity_type)
        success = await self.coalescer.wait_async(cache_key, timeout_seconds)

        if success:
            return await self.get_async(project_gid, entity_type)
        return None

    def get_stats(self) -> dict[str, dict[str, int]]:
        """Get per-entity-type cache statistics."""
        return {k: dict(v) for k, v in self._stats.items()}

    def reset_stats(self) -> None:
        """Reset all statistics to zero."""
        for stats in self._stats.values():
            for key in stats:
                stats[key] = 0

    def _build_key(self, project_gid: str, entity_type: str) -> str:
        """Build cache key from project and entity type."""
        return f"{entity_type}:{project_gid}"

    def _is_valid(
        self,
        entry: CacheEntry,
        current_watermark: datetime | None,
    ) -> bool:
        """Check if entry is valid (not stale, correct schema)."""
        # Schema version check
        if entry.schema_version != self.schema_version:
            return False

        # TTL check
        ttl_seconds = self.ttl_hours * 3600
        if entry.is_stale(ttl_seconds):
            return False

        # Watermark check (if provided)
        if current_watermark is not None:
            if not entry.is_fresh_by_watermark(current_watermark):
                return False

        return True
```

### 5.2 @dataframe_cache Decorator

**Module**: `src/autom8_asana/cache/dataframe/decorator.py`

Class decorator for resolution strategies enabling transparent caching.

```python
"""Class decorator for DataFrame caching on resolution strategies.

Per TDD-DATAFRAME-CACHE-001: Decorator pattern for transparent caching
with cache miss -> 503 response behavior.
"""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from autom8y_log import get_logger
from fastapi import HTTPException

if TYPE_CHECKING:
    from autom8_asana.cache.dataframe_cache import DataFrameCache

logger = get_logger(__name__)

T = TypeVar("T")


def dataframe_cache(
    cache_provider: Callable[[], "DataFrameCache"],
    entity_type: str,
    build_method: str = "_build_dataframe",
) -> Callable[[type[T]], type[T]]:
    """Class decorator adding DataFrame caching to resolution strategies.

    Wraps the strategy's resolve() method to:
    1. Check cache before building DataFrame
    2. Return 503 on cache miss (trigger async build)
    3. Update cache after successful build

    Args:
        cache_provider: Callable returning DataFrameCache instance.
        entity_type: Entity type for cache key (unit, offer, contact).
        build_method: Name of method that builds the DataFrame.

    Returns:
        Decorated class with caching behavior.

    Example:
        >>> @dataframe_cache(
        ...     cache_provider=lambda: get_dataframe_cache(),
        ...     entity_type="offer",
        ... )
        ... class OfferResolutionStrategy:
        ...     async def resolve(self, criteria, project_gid, client):
        ...         # DataFrame access is cached transparently
        ...         ...
    """
    def decorator(cls: type[T]) -> type[T]:
        original_resolve = cls.resolve

        @wraps(original_resolve)
        async def cached_resolve(
            self: T,
            criteria: list[Any],
            project_gid: str,
            client: Any,
        ) -> list[Any]:
            cache = cache_provider()

            # Try to get cached DataFrame
            entry = await cache.get_async(project_gid, entity_type)

            if entry is not None:
                # Cache hit - inject DataFrame and resolve
                self._cached_dataframe = entry.dataframe
                return await original_resolve(self, criteria, project_gid, client)

            # Cache miss - check if build is in progress
            acquired = await cache.acquire_build_lock_async(
                project_gid, entity_type
            )

            if not acquired:
                # Another request is building - wait for it
                entry = await cache.wait_for_build_async(
                    project_gid, entity_type,
                    timeout_seconds=30.0,
                )

                if entry is not None:
                    self._cached_dataframe = entry.dataframe
                    return await original_resolve(
                        self, criteria, project_gid, client
                    )

                # Timeout or failure
                logger.warning(
                    "dataframe_cache_wait_timeout",
                    extra={
                        "project_gid": project_gid,
                        "entity_type": entity_type,
                    },
                )
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "CACHE_BUILD_IN_PROGRESS",
                        "message": "DataFrame build in progress, retry shortly",
                    },
                )

            # This request should build
            try:
                # Call the original build method
                build_func = getattr(self, build_method)
                df, watermark = await build_func(project_gid, client)

                if df is None:
                    raise HTTPException(
                        status_code=503,
                        detail={
                            "error": "DATAFRAME_BUILD_FAILED",
                            "message": "Failed to build DataFrame",
                        },
                    )

                # Store in cache
                await cache.put_async(
                    project_gid, entity_type, df, watermark
                )

                # Release lock with success
                await cache.release_build_lock_async(
                    project_gid, entity_type, success=True
                )

                # Resolve with fresh DataFrame
                self._cached_dataframe = df
                return await original_resolve(
                    self, criteria, project_gid, client
                )

            except Exception as e:
                # Release lock with failure
                await cache.release_build_lock_async(
                    project_gid, entity_type, success=False
                )

                logger.error(
                    "dataframe_cache_build_failed",
                    extra={
                        "project_gid": project_gid,
                        "entity_type": entity_type,
                        "error": str(e),
                    },
                )
                raise

        cls.resolve = cached_resolve
        return cls

    return decorator
```

### 5.3 MemoryTier

**Module**: `src/autom8_asana/cache/dataframe/tiers/memory.py`

Hot cache with dynamic heap-based limits and LRU/staleness-based eviction.

```python
"""Memory tier for DataFrame hot cache.

Per TDD-DATAFRAME-CACHE-001: Dynamic heap-based limits with LRU/staleness eviction.
"""

from __future__ import annotations

import sys
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.cache.dataframe_cache import CacheEntry

logger = get_logger(__name__)


@dataclass
class MemoryTier:
    """Memory tier with LRU eviction and heap-based limits.

    Per TDD-DATAFRAME-CACHE-001:
    - Dynamic memory limit based on heap percentage
    - LRU + staleness-based eviction via evict_stale()
    - Thread-safe access

    Attributes:
        max_heap_percent: Maximum heap percentage to use (0.0-1.0).
        max_entries: Maximum number of entries (backup limit).

    Example:
        >>> tier = MemoryTier(max_heap_percent=0.3, max_entries=100)
        >>> tier.put("key", entry)
        >>> entry = tier.get("key")  # Moves to front of LRU
    """

    max_heap_percent: float = 0.3
    max_entries: int = 100

    # Internal state
    _cache: OrderedDict[str, "CacheEntry"] = field(
        default_factory=OrderedDict, init=False
    )
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)
    _current_bytes: int = field(default=0, init=False)

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._stats = {
            "gets": 0,
            "puts": 0,
            "evictions_lru": 0,
            "evictions_staleness": 0,
            "evictions_memory": 0,
        }

    def get(self, key: str) -> "CacheEntry | None":
        """Get entry and move to front of LRU.

        Args:
            key: Cache key.

        Returns:
            CacheEntry if found, None otherwise.
        """
        with self._lock:
            self._stats["gets"] += 1

            if key not in self._cache:
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return self._cache[key]

    def put(self, key: str, entry: "CacheEntry") -> None:
        """Store entry with LRU tracking.

        Args:
            key: Cache key.
            entry: CacheEntry to store.
        """
        with self._lock:
            self._stats["puts"] += 1

            # Remove existing if present
            if key in self._cache:
                old_entry = self._cache.pop(key)
                self._current_bytes -= self._estimate_size(old_entry)

            # Check memory limit before adding
            entry_size = self._estimate_size(entry)
            while self._should_evict(entry_size):
                self._evict_one()

            # Check entry limit
            while len(self._cache) >= self.max_entries:
                self._evict_one()

            # Add new entry
            self._cache[key] = entry
            self._current_bytes += entry_size

    def remove(self, key: str) -> bool:
        """Remove entry by key.

        Args:
            key: Cache key.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._current_bytes -= self._estimate_size(entry)
                return True
            return False

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._cache.clear()
            self._current_bytes = 0

    def evict_stale(self, max_age_seconds: int) -> int:
        """Evict entries older than max_age_seconds.

        Per TDD: LRU/staleness-based eviction.

        Args:
            max_age_seconds: Maximum age in seconds.

        Returns:
            Number of entries evicted.
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            cutoff = now.timestamp() - max_age_seconds

            stale_keys = [
                key for key, entry in self._cache.items()
                if entry.created_at.timestamp() < cutoff
            ]

            for key in stale_keys:
                entry = self._cache.pop(key)
                self._current_bytes -= self._estimate_size(entry)
                self._stats["evictions_staleness"] += 1

            return len(stale_keys)

    def get_stats(self) -> dict[str, int]:
        """Get tier statistics."""
        with self._lock:
            return {
                **self._stats,
                "entry_count": len(self._cache),
                "current_bytes": self._current_bytes,
                "max_bytes": self._get_max_bytes(),
            }

    def _should_evict(self, new_entry_size: int) -> bool:
        """Check if eviction needed for new entry."""
        if len(self._cache) == 0:
            return False

        max_bytes = self._get_max_bytes()
        return (self._current_bytes + new_entry_size) > max_bytes

    def _evict_one(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Pop from front (least recently used)
        key, entry = self._cache.popitem(last=False)
        self._current_bytes -= self._estimate_size(entry)
        self._stats["evictions_lru"] += 1

        logger.debug(
            "memory_tier_evict_lru",
            extra={"key": key, "row_count": entry.row_count},
        )

    def _get_max_bytes(self) -> int:
        """Calculate maximum bytes based on heap percentage."""
        # Get total memory (simplified - in production use psutil)
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        if soft == resource.RLIM_INFINITY:
            # Fallback: assume 4GB
            total_memory = 4 * 1024 * 1024 * 1024
        else:
            total_memory = soft

        return int(total_memory * self.max_heap_percent)

    def _estimate_size(self, entry: "CacheEntry") -> int:
        """Estimate entry size in bytes."""
        # Polars DataFrame memory usage
        return entry.dataframe.estimated_size()
```

### 5.4 S3Tier

**Module**: `src/autom8_asana/cache/dataframe/tiers/s3.py`

Cold storage with Parquet serialization.

```python
"""S3 tier for DataFrame cold storage with Parquet format.

Per TDD-DATAFRAME-CACHE-001: S3 as source of truth with Parquet serialization.
Schema evolution: superset OK (new columns acceptable).
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import polars as pl
from autom8y_log import get_logger

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
    from autom8_asana.cache.dataframe_cache import CacheEntry

logger = get_logger(__name__)


@dataclass
class S3Tier:
    """S3 tier with Parquet serialization.

    Per TDD-DATAFRAME-CACHE-001:
    - Parquet format for efficient columnar storage
    - Schema evolution: new columns acceptable (superset OK)
    - Strict startup: fail if S3 read fails

    Attributes:
        bucket: S3 bucket name.
        prefix: Key prefix for DataFrame storage.
        s3_client: boto3 S3 client (injected for testing).

    Example:
        >>> tier = S3Tier(
        ...     bucket="autom8-cache",
        ...     prefix="dataframes/v1/",
        ...     s3_client=boto3.client("s3"),
        ... )
        >>> await tier.put_async("unit:proj-123", entry)
        >>> entry = await tier.get_async("unit:proj-123")
    """

    bucket: str
    prefix: str = "dataframes/"
    s3_client: "S3Client | None" = None

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._stats = {
            "reads": 0,
            "writes": 0,
            "read_errors": 0,
            "write_errors": 0,
            "bytes_read": 0,
            "bytes_written": 0,
        }

        if self.s3_client is None:
            import boto3
            self.s3_client = boto3.client("s3")

    async def get_async(self, key: str) -> "CacheEntry | None":
        """Get entry from S3.

        Args:
            key: Cache key (entity_type:project_gid).

        Returns:
            CacheEntry if found, None on error or not found.

        Raises:
            RuntimeError: On startup if strict mode and S3 unavailable.
        """
        from autom8_asana.cache.dataframe_cache import CacheEntry

        s3_key = f"{self.prefix}{key}.parquet"

        try:
            self._stats["reads"] += 1

            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=s3_key,
            )

            # Read Parquet bytes
            body = response["Body"].read()
            self._stats["bytes_read"] += len(body)

            # Parse DataFrame
            df = pl.read_parquet(io.BytesIO(body))

            # Extract metadata from S3 object metadata
            metadata = response.get("Metadata", {})

            entry = CacheEntry(
                project_gid=metadata.get("project_gid", key.split(":")[-1]),
                entity_type=metadata.get("entity_type", key.split(":")[0]),
                dataframe=df,
                watermark=datetime.fromisoformat(
                    metadata.get("watermark", datetime.now(timezone.utc).isoformat())
                ),
                created_at=datetime.fromisoformat(
                    metadata.get("created_at", datetime.now(timezone.utc).isoformat())
                ),
                schema_version=metadata.get("schema_version", "unknown"),
            )

            logger.debug(
                "s3_tier_get_success",
                extra={
                    "key": key,
                    "row_count": entry.row_count,
                    "bytes": len(body),
                },
            )

            return entry

        except self.s3_client.exceptions.NoSuchKey:
            logger.debug("s3_tier_not_found", extra={"key": key})
            return None

        except Exception as e:
            self._stats["read_errors"] += 1
            logger.warning(
                "s3_tier_get_error",
                extra={"key": key, "error": str(e)},
            )
            return None

    async def put_async(
        self,
        key: str,
        entry: "CacheEntry",
    ) -> bool:
        """Store entry in S3.

        Args:
            key: Cache key.
            entry: CacheEntry to store.

        Returns:
            True on success, False on failure.
        """
        s3_key = f"{self.prefix}{key}.parquet"

        try:
            self._stats["writes"] += 1

            # Serialize DataFrame to Parquet bytes
            buffer = io.BytesIO()
            entry.dataframe.write_parquet(buffer)
            body = buffer.getvalue()

            self._stats["bytes_written"] += len(body)

            # Store with metadata
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=body,
                ContentType="application/x-parquet",
                Metadata={
                    "project_gid": entry.project_gid,
                    "entity_type": entry.entity_type,
                    "watermark": entry.watermark.isoformat(),
                    "created_at": entry.created_at.isoformat(),
                    "schema_version": entry.schema_version,
                    "row_count": str(entry.row_count),
                },
            )

            logger.info(
                "s3_tier_put_success",
                extra={
                    "key": key,
                    "row_count": entry.row_count,
                    "bytes": len(body),
                },
            )

            return True

        except Exception as e:
            self._stats["write_errors"] += 1
            logger.error(
                "s3_tier_put_error",
                extra={"key": key, "error": str(e)},
            )
            return False

    async def exists_async(self, key: str) -> bool:
        """Check if entry exists in S3."""
        s3_key = f"{self.prefix}{key}.parquet"

        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except self.s3_client.exceptions.ClientError:
            return False

    def get_stats(self) -> dict[str, int]:
        """Get tier statistics."""
        return dict(self._stats)
```

### 5.5 RequestCoalescer

**Module**: `src/autom8_asana/cache/dataframe/coalescer.py`

Thundering herd prevention via first-request-builds pattern.

```python
"""Request coalescing for DataFrame build deduplication.

Per TDD-DATAFRAME-CACHE-001: First request builds, others wait.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict

from autom8y_log import get_logger

logger = get_logger(__name__)


class BuildStatus(Enum):
    """Status of a build operation."""
    BUILDING = "building"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class BuildState:
    """State for an in-progress build."""
    status: BuildStatus
    started_at: datetime
    event: asyncio.Event
    waiter_count: int = 0


@dataclass
class RequestCoalescer:
    """Coalesces concurrent build requests for the same cache key.

    Per TDD-DATAFRAME-CACHE-001:
    - First request acquires lock and builds
    - Subsequent requests wait for first to complete
    - All waiters get notified on completion

    Attributes:
        max_wait_seconds: Maximum time waiters will wait.

    Example:
        >>> coalescer = RequestCoalescer()
        >>>
        >>> # First request acquires
        >>> acquired = await coalescer.try_acquire_async("key")  # True
        >>>
        >>> # Second request waits
        >>> acquired = await coalescer.try_acquire_async("key")  # False
        >>> success = await coalescer.wait_async("key", timeout=30)
        >>>
        >>> # First request completes
        >>> await coalescer.release_async("key", success=True)
    """

    max_wait_seconds: float = 60.0

    # Internal state
    _builds: Dict[str, BuildState] = field(default_factory=dict, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._stats = {
            "acquires": 0,
            "waits": 0,
            "wait_timeouts": 0,
            "completions_success": 0,
            "completions_failure": 0,
        }

    async def try_acquire_async(self, key: str) -> bool:
        """Attempt to acquire build lock.

        Args:
            key: Cache key to build.

        Returns:
            True if caller should build, False if build in progress.
        """
        async with self._lock:
            if key in self._builds:
                state = self._builds[key]
                if state.status == BuildStatus.BUILDING:
                    return False

            # Acquire lock
            self._builds[key] = BuildState(
                status=BuildStatus.BUILDING,
                started_at=datetime.now(timezone.utc),
                event=asyncio.Event(),
            )
            self._stats["acquires"] += 1

            logger.debug(
                "coalescer_acquire",
                extra={"key": key},
            )

            return True

    async def wait_async(
        self,
        key: str,
        timeout_seconds: float | None = None,
    ) -> bool:
        """Wait for in-progress build to complete.

        Args:
            key: Cache key being built.
            timeout_seconds: Maximum wait time.

        Returns:
            True if build succeeded, False on timeout/failure.
        """
        timeout = timeout_seconds or self.max_wait_seconds

        async with self._lock:
            if key not in self._builds:
                return False

            state = self._builds[key]
            state.waiter_count += 1

        self._stats["waits"] += 1

        try:
            await asyncio.wait_for(
                state.event.wait(),
                timeout=timeout,
            )

            return state.status == BuildStatus.SUCCESS

        except asyncio.TimeoutError:
            self._stats["wait_timeouts"] += 1
            logger.warning(
                "coalescer_wait_timeout",
                extra={"key": key, "timeout": timeout},
            )
            return False

        finally:
            async with self._lock:
                if key in self._builds:
                    self._builds[key].waiter_count -= 1

    async def release_async(self, key: str, success: bool) -> None:
        """Release build lock and notify waiters.

        Args:
            key: Cache key that was built.
            success: Whether build succeeded.
        """
        async with self._lock:
            if key not in self._builds:
                return

            state = self._builds[key]
            state.status = BuildStatus.SUCCESS if success else BuildStatus.FAILURE
            state.event.set()

            if success:
                self._stats["completions_success"] += 1
            else:
                self._stats["completions_failure"] += 1

            logger.debug(
                "coalescer_release",
                extra={
                    "key": key,
                    "success": success,
                    "waiter_count": state.waiter_count,
                },
            )

            # Cleanup after a delay (let waiters read status)
            asyncio.create_task(self._cleanup_after_delay(key, delay=5.0))

    async def _cleanup_after_delay(self, key: str, delay: float) -> None:
        """Remove build state after delay."""
        await asyncio.sleep(delay)
        async with self._lock:
            if key in self._builds:
                state = self._builds[key]
                if state.waiter_count == 0:
                    del self._builds[key]

    def is_building(self, key: str) -> bool:
        """Check if build is in progress for key."""
        return (
            key in self._builds and
            self._builds[key].status == BuildStatus.BUILDING
        )

    def get_stats(self) -> dict[str, int]:
        """Get coalescer statistics."""
        return dict(self._stats)
```

### 5.6 CircuitBreaker

**Module**: `src/autom8_asana/cache/dataframe/circuit_breaker.py`

Per-project failure isolation.

```python
"""Circuit breaker for per-project failure isolation.

Per TDD-DATAFRAME-CACHE-001: Circuit breaker with per-project granularity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict

from autom8y_log import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class ProjectCircuit:
    """Circuit state for a single project."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure: datetime | None = None
    last_success: datetime | None = None


@dataclass
class CircuitBreaker:
    """Circuit breaker with per-project granularity.

    Per TDD-DATAFRAME-CACHE-001:
    - Per-project circuit state
    - Opens after threshold failures
    - Half-open after reset timeout

    Attributes:
        failure_threshold: Failures before opening circuit.
        reset_timeout_seconds: Time before trying half-open.
        success_threshold: Successes in half-open to close.

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=3)
        >>>
        >>> # Record failures
        >>> breaker.record_failure("project-123")  # count=1
        >>> breaker.record_failure("project-123")  # count=2
        >>> breaker.record_failure("project-123")  # count=3, opens
        >>>
        >>> # Check state
        >>> breaker.is_open("project-123")  # True
        >>>
        >>> # After reset timeout, transitions to half-open
        >>> breaker.is_open("project-123")  # False (half-open allows)
    """

    failure_threshold: int = 3
    reset_timeout_seconds: int = 60
    success_threshold: int = 1

    # Internal state
    _circuits: Dict[str, ProjectCircuit] = field(default_factory=dict, init=False)

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._stats = {
            "failures_recorded": 0,
            "successes_recorded": 0,
            "circuits_opened": 0,
            "circuits_closed": 0,
            "requests_rejected": 0,
        }

    def is_open(self, project_gid: str) -> bool:
        """Check if circuit is open (rejecting requests).

        Also handles state transitions:
        - OPEN -> HALF_OPEN after reset timeout

        Args:
            project_gid: Project to check.

        Returns:
            True if requests should be rejected.
        """
        circuit = self._circuits.get(project_gid)

        if circuit is None:
            return False

        if circuit.state == CircuitState.CLOSED:
            return False

        if circuit.state == CircuitState.HALF_OPEN:
            return False  # Allow test request

        # OPEN state - check if reset timeout elapsed
        if circuit.last_failure is not None:
            elapsed = datetime.now(timezone.utc) - circuit.last_failure
            if elapsed.total_seconds() >= self.reset_timeout_seconds:
                # Transition to half-open
                circuit.state = CircuitState.HALF_OPEN
                logger.info(
                    "circuit_breaker_half_open",
                    extra={"project_gid": project_gid},
                )
                return False

        # Still open
        self._stats["requests_rejected"] += 1
        return True

    def record_failure(self, project_gid: str) -> None:
        """Record a failure for project.

        Args:
            project_gid: Project that failed.
        """
        self._stats["failures_recorded"] += 1

        if project_gid not in self._circuits:
            self._circuits[project_gid] = ProjectCircuit()

        circuit = self._circuits[project_gid]
        circuit.failure_count += 1
        circuit.last_failure = datetime.now(timezone.utc)

        # Check if should open circuit
        if (
            circuit.state != CircuitState.OPEN and
            circuit.failure_count >= self.failure_threshold
        ):
            circuit.state = CircuitState.OPEN
            self._stats["circuits_opened"] += 1
            logger.warning(
                "circuit_breaker_opened",
                extra={
                    "project_gid": project_gid,
                    "failure_count": circuit.failure_count,
                },
            )

        # In half-open, a failure reopens
        elif circuit.state == CircuitState.HALF_OPEN:
            circuit.state = CircuitState.OPEN
            logger.info(
                "circuit_breaker_reopened",
                extra={"project_gid": project_gid},
            )

    def close(self, project_gid: str) -> None:
        """Close circuit (record success).

        Args:
            project_gid: Project that succeeded.
        """
        self._stats["successes_recorded"] += 1

        if project_gid not in self._circuits:
            return

        circuit = self._circuits[project_gid]
        circuit.last_success = datetime.now(timezone.utc)

        if circuit.state == CircuitState.HALF_OPEN:
            circuit.state = CircuitState.CLOSED
            circuit.failure_count = 0
            self._stats["circuits_closed"] += 1
            logger.info(
                "circuit_breaker_closed",
                extra={"project_gid": project_gid},
            )

        elif circuit.state == CircuitState.CLOSED:
            circuit.failure_count = 0

    def get_state(self, project_gid: str) -> CircuitState:
        """Get current circuit state."""
        circuit = self._circuits.get(project_gid)
        return circuit.state if circuit else CircuitState.CLOSED

    def reset(self, project_gid: str) -> None:
        """Reset circuit to closed state."""
        if project_gid in self._circuits:
            del self._circuits[project_gid]

    def get_stats(self) -> dict[str, int]:
        """Get breaker statistics."""
        return {
            **self._stats,
            "open_circuits": sum(
                1 for c in self._circuits.values()
                if c.state == CircuitState.OPEN
            ),
        }
```

### 5.7 CacheWarmer

**Module**: `src/autom8_asana/cache/dataframe/warmer.py`

Priority-based pre-warming for Lambda deployment.

```python
"""Cache warmer for Lambda pre-deployment warming.

Per TDD-DATAFRAME-CACHE-001:
- Priority order: Offer -> Unit -> Business -> Contact (configurable)
- No limit on warm budget
- Partial warm not acceptable (all must succeed)
- Lambda-only (not local CLI)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Callable

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.cache.dataframe_cache import DataFrameCache
    from autom8_asana.client import AsanaClient

logger = get_logger(__name__)


class WarmResult(Enum):
    """Result of a warm operation."""
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


@dataclass
class WarmStatus:
    """Status of entity type warming."""
    entity_type: str
    result: WarmResult
    project_gid: str | None = None
    row_count: int = 0
    duration_ms: float = 0
    error: str | None = None


@dataclass
class CacheWarmer:
    """Pre-deployment cache warmer for Lambda.

    Per TDD-DATAFRAME-CACHE-001:
    - Priority: Offer -> Unit -> Business -> Contact (configurable)
    - All entity types must warm successfully (no partial)
    - Lambda invocation only (not local CLI)

    Attributes:
        cache: DataFrameCache to warm.
        priority: Entity type warm order.
        strict: If True, fail on any warm failure.

    Example:
        >>> warmer = CacheWarmer(cache=cache)
        >>>
        >>> # Warm all entity types in priority order
        >>> results = await warmer.warm_all_async(client)
        >>>
        >>> if all(r.result == WarmResult.SUCCESS for r in results):
        ...     print("Cache warm complete")
    """

    cache: "DataFrameCache"
    priority: list[str] = field(
        default_factory=lambda: ["offer", "unit", "business", "contact"]
    )
    strict: bool = True

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._stats = {
            "warm_attempts": 0,
            "warm_successes": 0,
            "warm_failures": 0,
            "total_rows_warmed": 0,
        }

    async def warm_all_async(
        self,
        client: "AsanaClient",
        project_gid_provider: Callable[[str], str | None],
    ) -> list[WarmStatus]:
        """Warm all entity types in priority order.

        Args:
            client: AsanaClient for building DataFrames.
            project_gid_provider: Function to get project GID for entity type.

        Returns:
            List of WarmStatus for each entity type.

        Raises:
            RuntimeError: If strict mode and any warm fails.
        """
        import time

        results: list[WarmStatus] = []

        for entity_type in self.priority:
            self._stats["warm_attempts"] += 1
            start = time.monotonic()

            project_gid = project_gid_provider(entity_type)

            if project_gid is None:
                status = WarmStatus(
                    entity_type=entity_type,
                    result=WarmResult.SKIPPED,
                    error="No project GID configured",
                )
                results.append(status)

                logger.warning(
                    "cache_warm_skipped",
                    extra={
                        "entity_type": entity_type,
                        "reason": "no_project_gid",
                    },
                )
                continue

            try:
                status = await self._warm_entity_type_async(
                    entity_type=entity_type,
                    project_gid=project_gid,
                    client=client,
                )

                elapsed_ms = (time.monotonic() - start) * 1000
                status.duration_ms = elapsed_ms

                results.append(status)

                if status.result == WarmResult.SUCCESS:
                    self._stats["warm_successes"] += 1
                    self._stats["total_rows_warmed"] += status.row_count
                else:
                    self._stats["warm_failures"] += 1

                    if self.strict:
                        raise RuntimeError(
                            f"Cache warm failed for {entity_type}: {status.error}"
                        )

            except Exception as e:
                self._stats["warm_failures"] += 1

                status = WarmStatus(
                    entity_type=entity_type,
                    result=WarmResult.FAILURE,
                    project_gid=project_gid,
                    error=str(e),
                )
                results.append(status)

                logger.error(
                    "cache_warm_error",
                    extra={
                        "entity_type": entity_type,
                        "project_gid": project_gid,
                        "error": str(e),
                    },
                )

                if self.strict:
                    raise

        # Log summary
        success_count = sum(
            1 for r in results if r.result == WarmResult.SUCCESS
        )

        logger.info(
            "cache_warm_complete",
            extra={
                "total": len(results),
                "success": success_count,
                "total_rows": self._stats["total_rows_warmed"],
            },
        )

        return results

    async def _warm_entity_type_async(
        self,
        entity_type: str,
        project_gid: str,
        client: "AsanaClient",
    ) -> WarmStatus:
        """Warm a single entity type.

        Args:
            entity_type: Entity type to warm.
            project_gid: Project GID for entity type.
            client: AsanaClient for building.

        Returns:
            WarmStatus indicating result.
        """
        from autom8_asana.services.resolver import get_strategy

        logger.info(
            "cache_warm_start",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
            },
        )

        # Get strategy and trigger build
        strategy = get_strategy(entity_type)

        if strategy is None:
            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.FAILURE,
                project_gid=project_gid,
                error="No strategy registered",
            )

        # Build DataFrame (strategy's _build method)
        build_method = getattr(strategy, "_build_dataframe", None)
        if build_method is None:
            build_method = getattr(strategy, f"_build_{entity_type}_dataframe", None)

        if build_method is None:
            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.FAILURE,
                project_gid=project_gid,
                error="No build method found",
            )

        df, watermark = await build_method(project_gid, client)

        if df is None:
            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.FAILURE,
                project_gid=project_gid,
                error="DataFrame build returned None",
            )

        # Store in cache
        await self.cache.put_async(
            project_gid=project_gid,
            entity_type=entity_type,
            dataframe=df,
            watermark=watermark,
        )

        return WarmStatus(
            entity_type=entity_type,
            result=WarmResult.SUCCESS,
            project_gid=project_gid,
            row_count=len(df),
        )

    def get_stats(self) -> dict[str, int]:
        """Get warmer statistics."""
        return dict(self._stats)
```

---

## Interface Contracts

### 6.1 DataFrameCache Public API

| Method | Signature | Returns | Async |
|--------|-----------|---------|-------|
| `get_async` | `(project_gid: str, entity_type: str, current_watermark: datetime \| None = None) -> CacheEntry \| None` | CacheEntry or None | Yes |
| `put_async` | `(project_gid: str, entity_type: str, dataframe: DataFrame, watermark: datetime) -> None` | None | Yes |
| `invalidate` | `(project_gid: str, entity_type: str \| None = None) -> None` | None | No |
| `invalidate_on_schema_change` | `(new_version: str) -> None` | None | No |
| `acquire_build_lock_async` | `(project_gid: str, entity_type: str) -> bool` | True if should build | Yes |
| `release_build_lock_async` | `(project_gid: str, entity_type: str, success: bool) -> None` | None | Yes |
| `wait_for_build_async` | `(project_gid: str, entity_type: str, timeout_seconds: float = 30.0) -> CacheEntry \| None` | CacheEntry or None | Yes |
| `get_stats` | `() -> dict[str, dict[str, int]]` | Per-entity statistics | No |

### 6.2 @dataframe_cache Decorator Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cache_provider` | `Callable[[], DataFrameCache]` | Yes | Factory for cache instance |
| `entity_type` | `str` | Yes | Entity type identifier |
| `build_method` | `str` | No | Name of build method (default: `_build_dataframe`) |

### 6.3 S3 Parquet Format

**Key Format**: `{prefix}{entity_type}:{project_gid}.parquet`

**Metadata (S3 Object Metadata)**:

| Key | Type | Description |
|-----|------|-------------|
| `project_gid` | string | Asana project GID |
| `entity_type` | string | Entity type |
| `watermark` | ISO datetime | Freshness watermark |
| `created_at` | ISO datetime | Cache entry creation time |
| `schema_version` | string | Schema version for invalidation |
| `row_count` | string | Number of rows (for observability) |

### 6.4 Admin API Endpoints

**Endpoint**: `GET /cache/status`

**Authentication**: Admin auth required (per design decision)

**Response**:

```json
{
  "status": "healthy",
  "entity_types": {
    "unit": {
      "memory_hits": 1234,
      "memory_misses": 56,
      "s3_hits": 23,
      "s3_misses": 5,
      "cached_projects": 12,
      "total_rows": 45000
    },
    "offer": { ... },
    "contact": { ... },
    "business": { ... }
  },
  "memory_tier": {
    "entry_count": 48,
    "current_bytes": 234567890,
    "max_bytes": 1073741824
  },
  "circuit_breakers": {
    "open_circuits": 0,
    "half_open_circuits": 1
  }
}
```

---

## Data Flow Diagrams

### 7.1 Cache Hit (Memory Tier)

```
┌──────────────┐    ┌─────────────────┐    ┌─────────────┐
│   Request    │───▶│ @dataframe_cache │───▶│ MemoryTier  │
│              │    │                  │    │   .get()    │
└──────────────┘    └─────────────────┘    └──────┬──────┘
                                                   │
                           ┌───────────────────────┘
                           │ CacheEntry found
                           ▼
                    ┌─────────────────┐
                    │   Inject DF     │
                    │   to Strategy   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Resolve Query  │───▶ Response
                    └─────────────────┘
```

### 7.2 Cache Miss (S3 Fallback)

```
┌──────────────┐    ┌─────────────────┐    ┌─────────────┐
│   Request    │───▶│ @dataframe_cache │───▶│ MemoryTier  │
│              │    │                  │    │   .get()    │
└──────────────┘    └─────────────────┘    └──────┬──────┘
                                                   │
                           ┌───────────────────────┘
                           │ None (miss)
                           ▼
                    ┌─────────────────┐
                    │    S3Tier       │
                    │   .get_async()  │
                    └────────┬────────┘
                             │ CacheEntry
                             ▼
                    ┌─────────────────┐
                    │  Hydrate Memory │
                    │      Tier       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Resolve Query  │───▶ Response
                    └─────────────────┘
```

### 7.3 Cache Miss (Build Required)

```
┌──────────────┐    ┌─────────────────┐    ┌─────────────┐
│   Request    │───▶│ @dataframe_cache │───▶│ Both Tiers  │
│              │    │                  │    │   Miss      │
└──────────────┘    └─────────────────┘    └──────┬──────┘
                                                   │
                           ┌───────────────────────┘
                           │ acquire_build_lock
                           ▼
                    ┌─────────────────┐
                    │ RequestCoalescer│
                    │ .try_acquire()  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │ acquired=True               │ acquired=False
              ▼                             ▼
       ┌─────────────────┐          ┌─────────────────┐
       │ Build DataFrame │          │   Wait for      │
       │ via Builder     │          │   Completion    │
       └────────┬────────┘          └────────┬────────┘
                │                            │
                ▼                            │
       ┌─────────────────┐                   │
       │ Store in Cache  │                   │
       │ (S3 + Memory)   │                   │
       └────────┬────────┘                   │
                │                            │
                │ release_lock(success=true) │
                ▼                            │
       ┌─────────────────┐                   │
       │ Notify Waiters  │◀──────────────────┘
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │  Resolve Query  │───▶ Response
       └─────────────────┘
```

---

## Non-Functional Considerations

### 8.1 Performance Targets

| Metric | Target | Approach |
|--------|--------|----------|
| Memory tier lookup | <1ms | In-memory dict with LRU |
| S3 tier lookup | <200ms | Parquet streaming, regional S3 |
| DataFrame build (10K tasks) | <5s | Parallel fetch, existing builder |
| Cache miss response | 503 + async build | Lambda trigger, client retry |
| Memory usage | <30% heap | Dynamic heap-based limits |

### 8.2 Observability

**Metrics (per entity type)**:

| Metric | Type | Description |
|--------|------|-------------|
| `dataframe_cache_hits_total{tier, entity_type}` | Counter | Cache hits by tier |
| `dataframe_cache_misses_total{entity_type}` | Counter | Cache misses |
| `dataframe_cache_build_duration_seconds{entity_type}` | Histogram | Build latency |
| `dataframe_cache_size_bytes{entity_type}` | Gauge | Cached DataFrame sizes |
| `dataframe_cache_row_count{entity_type}` | Gauge | Cached row counts |
| `dataframe_cache_circuit_breaks_total{project_gid}` | Counter | Circuit breaks |

**Logging**:

| Event | Level | When |
|-------|-------|------|
| `dataframe_cache_memory_hit` | DEBUG | Memory tier hit |
| `dataframe_cache_s3_hit` | INFO | S3 tier hit (less frequent) |
| `dataframe_cache_miss` | INFO | Both tiers miss |
| `dataframe_cache_build_start` | INFO | Build triggered |
| `dataframe_cache_build_complete` | INFO | Build finished |
| `dataframe_cache_circuit_open` | WARN | Circuit opened |

### 8.3 Security

| Concern | Mitigation |
|---------|------------|
| S3 bucket access | IAM role with least privilege |
| Admin endpoint | Admin auth required |
| Cache poisoning | Schema version validation |
| PII in Parquet | Encryption at rest (S3 default) |

---

## Migration Strategy

### 9.1 Phased Migration

**Phase 1: Infrastructure (Week 1)**

- [ ] Create `cache/dataframe/` module structure
- [ ] Implement `MemoryTier` and `S3Tier`
- [ ] Implement `RequestCoalescer` and `CircuitBreaker`
- [ ] Implement `DataFrameCache` orchestrator
- [ ] Unit tests for all components

**Phase 2: Decorator Integration (Week 2)**

- [ ] Implement `@dataframe_cache` decorator
- [ ] Apply to `OfferResolutionStrategy`
- [ ] Apply to `ContactResolutionStrategy`
- [ ] Integration tests with mocked S3

**Phase 3: Unit/Business Migration (Week 3)**

- [ ] Migrate Unit strategy (replace `_gid_index_cache`)
- [ ] Update Business strategy (uses Unit cache)
- [ ] Remove module-level `_gid_index_cache` from resolver.py
- [ ] Performance benchmarks

**Phase 4: Lambda Integration (Week 4)**

- [ ] Implement `CacheWarmer`
- [ ] Lambda warm-up handler
- [ ] Deploy pipeline integration
- [ ] Monitoring dashboards

### 9.2 Replacing _gid_index_cache

**Current** (`resolver.py:57-63`):

```python
_gid_index_cache: dict[str, GidLookupIndex] = {}
_INDEX_TTL_SECONDS = 3600
```

**Migration Steps**:

1. Add `@dataframe_cache` decorator to `UnitResolutionStrategy`
2. Modify `_get_or_build_index()` to use `_cached_dataframe` injected by decorator
3. Remove module-level `_gid_index_cache` and `_INDEX_TTL_SECONDS`
4. Update Business strategy to work with cached Unit lookups

**Before**:

```python
class UnitResolutionStrategy:
    async def resolve(self, criteria, project_gid, client):
        index = await self._get_or_build_index(project_gid, client)
        # ... use index
```

**After**:

```python
@dataframe_cache(
    cache_provider=get_dataframe_cache,
    entity_type="unit",
)
class UnitResolutionStrategy:
    async def resolve(self, criteria, project_gid, client):
        # _cached_dataframe injected by decorator
        index = GidLookupIndex.from_dataframe(self._cached_dataframe)
        # ... use index
```

### 9.3 Backward Compatibility

| Change | Breaking? | Mitigation |
|--------|-----------|------------|
| Add decorator to strategies | No | Additive, existing behavior preserved |
| Remove `_gid_index_cache` | Yes (internal) | Export removed from `__all__` |
| S3 dependency | No | Graceful fallback if S3 unavailable |
| 503 on cache miss | Yes (API) | Document in API changelog |

---

## Test Strategy

### 10.1 Unit Tests

**Module**: `tests/unit/cache/dataframe/`

```python
"""Unit tests for DataFrame caching."""

import pytest
import polars as pl
from datetime import datetime, timezone

from autom8_asana.cache.dataframe_cache import DataFrameCache, CacheEntry
from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
from autom8_asana.cache.dataframe.coalescer import RequestCoalescer


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_is_stale_within_ttl(self):
        """Entry within TTL is not stale."""
        entry = CacheEntry(
            project_gid="proj-1",
            entity_type="unit",
            dataframe=pl.DataFrame({"gid": ["1", "2"]}),
            watermark=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            schema_version="1.0.0",
        )

        assert not entry.is_stale(ttl_seconds=3600)

    def test_is_stale_beyond_ttl(self):
        """Entry beyond TTL is stale."""
        from datetime import timedelta

        entry = CacheEntry(
            project_gid="proj-1",
            entity_type="unit",
            dataframe=pl.DataFrame({"gid": ["1", "2"]}),
            watermark=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            schema_version="1.0.0",
        )

        assert entry.is_stale(ttl_seconds=3600)


class TestMemoryTier:
    """Tests for memory tier."""

    def test_put_and_get(self):
        """Basic put and get."""
        tier = MemoryTier(max_entries=10)
        entry = self._make_entry("proj-1")

        tier.put("key-1", entry)
        result = tier.get("key-1")

        assert result is not None
        assert result.project_gid == "proj-1"

    def test_lru_eviction(self):
        """LRU eviction when at capacity."""
        tier = MemoryTier(max_entries=2)

        tier.put("key-1", self._make_entry("proj-1"))
        tier.put("key-2", self._make_entry("proj-2"))
        tier.get("key-1")  # Access key-1, making key-2 LRU
        tier.put("key-3", self._make_entry("proj-3"))

        assert tier.get("key-1") is not None
        assert tier.get("key-2") is None  # Evicted
        assert tier.get("key-3") is not None

    def _make_entry(self, project_gid: str) -> CacheEntry:
        return CacheEntry(
            project_gid=project_gid,
            entity_type="unit",
            dataframe=pl.DataFrame({"gid": ["1"]}),
            watermark=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            schema_version="1.0.0",
        )


class TestRequestCoalescer:
    """Tests for request coalescing."""

    @pytest.mark.asyncio
    async def test_first_request_acquires(self):
        """First request acquires lock."""
        coalescer = RequestCoalescer()

        acquired = await coalescer.try_acquire_async("key-1")

        assert acquired is True

    @pytest.mark.asyncio
    async def test_second_request_waits(self):
        """Second request does not acquire while first building."""
        coalescer = RequestCoalescer()

        await coalescer.try_acquire_async("key-1")
        acquired = await coalescer.try_acquire_async("key-1")

        assert acquired is False

    @pytest.mark.asyncio
    async def test_waiter_notified_on_success(self):
        """Waiters notified when build completes."""
        import asyncio

        coalescer = RequestCoalescer()
        await coalescer.try_acquire_async("key-1")

        async def wait_and_check():
            return await coalescer.wait_async("key-1", timeout_seconds=1.0)

        async def release():
            await asyncio.sleep(0.1)
            await coalescer.release_async("key-1", success=True)

        wait_task = asyncio.create_task(wait_and_check())
        release_task = asyncio.create_task(release())

        await release_task
        result = await wait_task

        assert result is True
```

### 10.2 Integration Tests

**Module**: `tests/integration/cache/`

```python
"""Integration tests for DataFrame caching."""

import pytest
import polars as pl
from moto import mock_aws

from autom8_asana.cache.dataframe_cache import DataFrameCache
from autom8_asana.cache.dataframe.tiers.s3 import S3Tier


@pytest.fixture
def mock_s3():
    """Mock S3 for testing."""
    with mock_aws():
        import boto3

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")

        yield s3


class TestS3TierIntegration:
    """Integration tests for S3 tier."""

    @pytest.mark.asyncio
    async def test_put_and_get_parquet(self, mock_s3):
        """Round-trip through S3 with Parquet."""
        tier = S3Tier(
            bucket="test-bucket",
            prefix="dataframes/",
            s3_client=mock_s3,
        )

        df = pl.DataFrame({
            "gid": ["1", "2", "3"],
            "name": ["A", "B", "C"],
        })

        from autom8_asana.cache.dataframe_cache import CacheEntry
        from datetime import datetime, timezone

        entry = CacheEntry(
            project_gid="proj-1",
            entity_type="unit",
            dataframe=df,
            watermark=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            schema_version="1.0.0",
        )

        await tier.put_async("unit:proj-1", entry)
        result = await tier.get_async("unit:proj-1")

        assert result is not None
        assert result.row_count == 3
        assert result.dataframe["gid"].to_list() == ["1", "2", "3"]
```

### 10.3 Test Bypass Flag

Per design decision, tests can bypass caching:

```python
@dataframe_cache(
    cache_provider=get_dataframe_cache,
    entity_type="unit",
    # Test bypass via environment variable
    bypass_env_var="DATAFRAME_CACHE_BYPASS",
)
class UnitResolutionStrategy:
    ...
```

---

## Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Infrastructure** | 5 days | MemoryTier, S3Tier, DataFrameCache, Coalescer, CircuitBreaker |
| **Phase 2: Decorator** | 3 days | @dataframe_cache, Offer/Contact integration |
| **Phase 3: Migration** | 3 days | Unit/Business migration, remove _gid_index_cache |
| **Phase 4: Lambda** | 2 days | CacheWarmer, deploy pipeline, monitoring |
| **Phase 5: QA** | 2 days | Performance testing, documentation |

**Total**: 15 days (3 weeks)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| S3 latency spikes | Medium | Medium | Memory tier as primary, S3 as fallback |
| Memory pressure | Medium | High | Dynamic heap limits, LRU eviction |
| Parquet schema drift | Low | Medium | Schema version validation, superset OK |
| Lambda cold start | Medium | Medium | Keep-warm pings, VPC optimization |
| Thundering herd | Low | High | Request coalescing, circuit breaker |
| 503 response handling | Medium | Medium | Clear error message, retry guidance |

---

## ADRs

### ADR-DATAFRAME-CACHE-001: Cache at DataFrame Level

**Context**: Should we cache at DataFrame, row, or query level?

**Decision**: Cache at DataFrame level.

**Rationale**:
- Entity resolution needs the full DataFrame for index building
- Row-level caching adds complexity without clear benefit
- Query-level caching has poor hit rates for varied criteria
- DataFrame-level aligns with existing GidLookupIndex pattern

**Consequences**:
- Simpler invalidation (per-project, per-entity-type)
- Higher memory usage than row-level
- Fast local lookups after initial load

### ADR-DATAFRAME-CACHE-002: 503 on Cache Miss

**Context**: What should happen when cache misses and build is required?

**Decision**: Return 503 with retry guidance, trigger async Lambda build.

**Rationale**:
- Avoids blocking requests during builds (2-10 seconds)
- Clients can implement exponential backoff
- Lambda handles build without blocking API pods
- Partial data not acceptable (all-or-nothing per design)

**Consequences**:
- Clients must handle 503 responses
- First requests after cold start see 503
- Lambda integration required for production

### ADR-DATAFRAME-CACHE-003: Request Coalescing Strategy

**Context**: How to prevent thundering herd on cache miss?

**Decision**: First request builds, others wait up to 30 seconds.

**Rationale**:
- Simple to implement and reason about
- Avoids duplicate Asana API load
- Waiters get cached result immediately after build
- Timeout prevents indefinite blocking

**Consequences**:
- First request bears full build latency
- Waiters may timeout if build exceeds 30 seconds
- Requires proper lock cleanup on failure

---

## Success Criteria

### Quantitative

| Metric | Target | Measurement |
|--------|--------|-------------|
| Memory tier hit rate | >90% | Prometheus metrics |
| Cache miss latency (503) | <100ms | Response time P99 |
| Build latency (10K tasks) | <5s | Lambda duration |
| Memory usage | <30% heap | Memory metrics |
| All entity types cached | 4/4 | Integration tests |

### Qualitative

| Criterion | Validation |
|-----------|------------|
| Unified caching for all entity types | Code review, no per-strategy divergence |
| Clean migration from _gid_index_cache | Module-level cache removed |
| Observable cache behavior | Dashboard with hit/miss/latency |
| Documented failure modes | ADRs and error handling |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD Document | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-dataframe-cache.md` | Pending |

---

## Appendix A: File Structure

```
src/autom8_asana/cache/
├── __init__.py
├── dataframe_cache.py              # Main orchestrator
└── dataframe/
    ├── __init__.py
    ├── decorator.py                # @dataframe_cache
    ├── coalescer.py               # RequestCoalescer
    ├── circuit_breaker.py         # CircuitBreaker
    ├── warmer.py                  # CacheWarmer
    └── tiers/
        ├── __init__.py
        ├── memory.py              # MemoryTier
        └── s3.py                  # S3Tier
```

## Appendix B: Current _gid_index_cache Reference

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py`

```python
# Lines 57-63
_gid_index_cache: dict[str, GidLookupIndex] = {}
_INDEX_TTL_SECONDS = 3600

# Usage in UnitResolutionStrategy._get_or_build_index()
# Lines 414-524
async def _get_or_build_index(self, project_gid, client):
    global _gid_index_cache
    cached_index = _gid_index_cache.get(project_gid)
    if cached_index is not None and not cached_index.is_stale(_INDEX_TTL_SECONDS):
        return cached_index
    # ... build and cache ...
    _gid_index_cache[project_gid] = index
```

This pattern will be replaced by the `@dataframe_cache` decorator in Phase 3.

## Appendix C: Existing Patterns Referenced

| Pattern | Location | Usage in Design |
|---------|----------|-----------------|
| SchemaRegistry singleton | `dataframes/models/registry.py` | Thread-safe lazy init pattern |
| UnifiedTaskStore | `cache/unified.py` | Tiered caching with completeness tracking |
| FreshnessCoordinator | `cache/freshness_coordinator.py` | Batch staleness checks |
| HierarchyIndex | `cache/hierarchy.py` | Parent-child relationship tracking |
| ProjectDataFrameBuilder | `dataframes/builders/project.py` | DataFrame construction |
