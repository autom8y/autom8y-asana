# TDD: Cross-Tier Freshness Propagation

**TDD ID**: TDD-CROSS-TIER-FRESHNESS-001
**Version**: 1.0
**Date**: 2026-02-04
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: Architectural Opportunities Initiative, A2 (Wave 2)
**Spike References**: S0-001 (Cache Baseline), S0-004 (Stale-Data Analysis)
**Depends On**: TDD-CACHE-INVALIDATION-001 (Sprint 1, A1), TDD-ENTITY-REGISTRY-001 (Sprint 2, B1)

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Goals and Non-Goals](#goals-and-non-goals)
4. [Proposed Architecture](#proposed-architecture)
5. [Component Design: FreshnessStamp](#component-design-freshnessstamp)
6. [Component Design: FreshnessPolicy](#component-design-freshnesspolicy)
7. [Integration: CacheEntry Extension](#integration-cacheentry-extension)
8. [Integration: TieredCacheProvider](#integration-tieredcacheprovider)
9. [Integration: DataFrameCache](#integration-dataframecache)
10. [Integration: MutationInvalidator](#integration-mutationinvalidator)
11. [Backward Compatibility](#backward-compatibility)
12. [Data Flow Diagrams](#data-flow-diagrams)
13. [Non-Functional Considerations](#non-functional-considerations)
14. [Test Strategy](#test-strategy)
15. [Risk Assessment](#risk-assessment)
16. [ADRs](#adrs)
17. [Success Criteria](#success-criteria)

---

## Overview

Sprint 1 delivered the `MutationInvalidator` which provides binary cache invalidation: data is either cached or evicted. Sprint 2's `EntityRegistry` (B1) provides per-entity TTLs. This TDD specifies the **freshness metadata layer** that bridges the semantic gap between task-level freshness and DataFrame-level freshness, enabling consumers to make informed decisions about data age without requiring an API call.

The core insight is that the existing system has **two incompatible freshness models** (spike S0-001 Section 1.1 vs 1.2):

| Layer | Freshness Model | Granularity | Problem |
|-------|----------------|-------------|---------|
| **Task cache** | `FreshnessMode` (STRICT/EVENTUAL/IMMEDIATE) + Batch API `modified_at` validation | Per-task | Staleness detected at task level never propagates to DataFrames |
| **DataFrame cache** | `FreshnessStatus` (FRESH/STALE_SERVABLE/EXPIRED_SERVABLE) + TTL + SWR grace + watermark | Per-project + per-entity-type | No knowledge of constituent task freshness |

This TDD introduces a `FreshnessStamp` that travels with every cached entry through all tiers, and a `FreshnessPolicy` that uses the EntityRegistry to make O(1) freshness decisions. The MutationInvalidator gains a **soft invalidation** mode that marks entries as stale-but-available instead of evicting them, enabling graceful degradation.

### Solution Summary

| Component | Location | Purpose |
|-----------|----------|---------|
| `FreshnessStamp` | `cache/freshness_stamp.py` | Frozen dataclass carrying `last_verified_at`, `source`, and `staleness_hint` metadata |
| `FreshnessPolicy` | `cache/freshness_policy.py` | Stateless evaluator that classifies entries as FRESH/APPROACHING/STALE using EntityRegistry TTLs |
| `CacheEntry` extension | `cache/entry.py` | New optional `freshness_stamp` field on the frozen dataclass |
| `TieredCacheProvider` freshness-aware get | `cache/tiered.py` | Cross-tier freshness comparison during cold-to-hot promotion |
| `DataFrameCache` aggregate freshness | `cache/dataframe_cache.py` | Aggregate `FreshnessStamp` computed from section watermarks |
| `MutationInvalidator` soft invalidation | `cache/mutation_invalidator.py` | Marks entries stale instead of evicting (configurable per event) |

---

## Problem Statement

### Current State

The system has a freshness blind spot between cache tiers. Consider this scenario:

1. A task is updated via REST at T=0
2. `MutationInvalidator` evicts the task from Redis and S3
3. A reader fetches the task at T=1 -- cache miss, fresh data loaded into Redis and S3
4. Meanwhile, the DataFrame for the task's project was built at T=-60 and has TTL=900s
5. The DataFrame serves stale data for the task until T=840 (900 - 60 seconds)

The task cache knows the data is fresh (just fetched at T=1). The DataFrame cache does not know a constituent task was refreshed. These are two separate freshness universes.

### The Three Gaps

**Gap F1: No freshness metadata on CacheEntry.** The `CacheEntry` frozen dataclass has `cached_at` and `version` (modified_at), but no field indicating when the data was last **verified** as fresh. After `StalenessCheckCoordinator` extends a TTL, the entry's `cached_at` is reset but there is no record of the verification source (API batch check vs. mutation event vs. initial fetch).

**Gap F2: No cross-tier freshness comparison.** When `TieredCacheProvider` promotes an entry from S3 (cold) to Redis (hot), it uses `_promote_entry()` which sets `cached_at=now` and `ttl=promotion_ttl`. If Redis already had a staler version (expired but not yet evicted), there is no comparison -- the S3 version wins by default. Conversely, if the S3 entry is older than what Redis had before TTL expiry, S3 still wins.

**Gap F3: No aggregate freshness on DataFrames.** `DataFrameCache.CacheEntry` has a `watermark` (max modified_at from build time) and `created_at`, but no way to signal that some constituent sections were fresher than others. A DataFrame built from 10 sections has a single `created_at` even if 9 sections were served from cache and 1 was fetched fresh. The consumer has no visibility into this.

### Why Now

The EntityRegistry (B1) provides per-entity TTLs via `EntityDescriptor.default_ttl_seconds`. This is the prerequisite for freshness evaluation -- without canonical TTLs, a freshness policy has no baseline. With the registry in place, freshness evaluation becomes a simple comparison: `now - stamp.last_verified_at > registry.get_entity_ttl(entity_type)`.

---

## Goals and Non-Goals

### Goals

| ID | Goal | Gap Addressed |
|----|------|---------------|
| G1 | Every `CacheEntry` (task-level) carries a `FreshnessStamp` that records when the data was last verified as fresh and how it was verified | F1 |
| G2 | `FreshnessPolicy` classifies entries as FRESH, APPROACHING_STALE, or STALE using EntityRegistry TTLs with O(1) per-entry cost | F1 |
| G3 | `TieredCacheProvider` compares freshness stamps during cold-to-hot promotion and prefers the fresher copy | F2 |
| G4 | `DataFrameCache` entries carry an aggregate freshness stamp reflecting the oldest section's freshness | F3 |
| G5 | `MutationInvalidator` supports soft invalidation: marking entries stale-but-available instead of evicting | All |
| G6 | Consumers that do not check freshness are unaffected (backward compatible) | All |

### Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Replace the existing `FreshnessStatus` enum in `DataFrameCache` | That enum serves a different purpose (SWR state machine); freshness stamps are complementary metadata |
| NG2 | Implement active freshness push (event bus / pub-sub) | Would require infrastructure beyond current scope; passive propagation is sufficient |
| NG3 | Add freshness to DynamicIndexCache entries | DynamicIndexCache is slated for reorganization in B2; adding freshness now would be premature |
| NG4 | Replace `StalenessCheckCoordinator` | The coordinator performs batch API checks; freshness stamps record the results but do not replace the checking mechanism |
| NG5 | Implement freshness-based cache warming priority | Interesting optimization but outside this scope; can be built on top of the freshness metadata later |
| NG6 | Surface freshness to external API consumers via headers | This TDD provides the internal plumbing; API header integration is a separate concern |

---

## Proposed Architecture

### System Context

```
                    ┌───────────────────────────────────────────────────────────┐
                    │                   FRESHNESS LAYER                         │
                    │                                                           │
                    │  ┌────────────────┐    ┌──────────────────┐               │
                    │  │ FreshnessStamp │    │ FreshnessPolicy  │               │
                    │  │ (dataclass)    │    │ (evaluator)      │               │
                    │  │                │    │                  │               │
                    │  │ last_verified  │    │ evaluate(entry)  │               │
                    │  │ source         │◄───│   -> FreshClass  │               │
                    │  │ staleness_hint │    │                  │               │
                    │  └──────┬─────────┘    │ Uses:            │               │
                    │         │              │  EntityRegistry   │               │
                    │         │              │  .get_entity_ttl()│               │
                    │         │              └──────────────────┘               │
                    │         │                                                 │
                    └─────────┼─────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┬─────────────────┐
              │               │               │                 │
              ▼               ▼               ▼                 ▼
    ┌─────────────┐   ┌──────────────┐ ┌───────────────┐ ┌──────────────┐
    │ CacheEntry  │   │ TieredCache  │ │ DataFrame     │ │ Mutation     │
    │ (extended)  │   │ Provider     │ │ Cache         │ │ Invalidator  │
    │             │   │              │ │               │ │              │
    │ +freshness_ │   │ Compares     │ │ Aggregate     │ │ Soft-mark    │
    │  stamp      │   │ stamps on    │ │ freshness     │ │ entries as   │
    │             │   │ promotion    │ │ from sections │ │ stale (opt)  │
    └─────────────┘   └──────────────┘ └───────────────┘ └──────────────┘
```

### Key Design Decisions Summary

1. **Opt-in stamp** -- `CacheEntry.freshness_stamp` is `Optional[FreshnessStamp]` with default `None`. Existing code that creates CacheEntries without a stamp continues to work.
2. **Stateless policy** -- `FreshnessPolicy` is a pure function wrapper. No state, no side effects. Takes an entry and returns a classification.
3. **Registry-driven TTLs** -- All TTL lookups go through `EntityRegistry.get_entity_ttl()`. No hardcoded TTL values in the freshness layer.
4. **Soft invalidation as opt-in mode** -- `MutationInvalidator` defaults to hard eviction (current behavior). Soft invalidation is per-entity-kind configurable.

---

## Component Design: FreshnessStamp

### Dataclass Definition

```python
# src/autom8_asana/cache/freshness_stamp.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class VerificationSource(str, Enum):
    """How the data was verified as fresh.

    Tracking the source of a freshness verification allows
    downstream consumers to weight freshness differently.
    An API_FETCH is a strong signal; a MUTATION_EVENT is
    an inference (we know the mutation happened, so the data
    we just wrote must be current).
    """

    API_FETCH = "api_fetch"             # Data fetched fresh from Asana API
    BATCH_CHECK = "batch_check"         # StalenessCheckCoordinator batch modified_at
    MUTATION_EVENT = "mutation_event"    # Inferred fresh from MutationInvalidator
    CACHE_WARM = "cache_warm"           # Lambda cache warmer populated this entry
    PROMOTION = "promotion"             # Promoted from cold tier (inherits source)
    UNKNOWN = "unknown"                 # Legacy entries without freshness tracking


class FreshnessClassification(str, Enum):
    """Result of evaluating a FreshnessStamp against policy.

    Three-state classification enables graduated responses:
    - FRESH: Serve without concern
    - APPROACHING_STALE: Serve, but consider background refresh
    - STALE: Serve with degradation warning, or reject
    """

    FRESH = "fresh"
    APPROACHING_STALE = "approaching_stale"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class FreshnessStamp:
    """Freshness metadata attached to a cached entry.

    Frozen for thread safety and to maintain CacheEntry immutability.
    Created at cache-write time and propagated through tiers.

    Attributes:
        last_verified_at: UTC timestamp when data was last confirmed
            as current (from API fetch, batch check, or mutation event).
        source: How the freshness was established. Enables consumers
            to weight freshness signals differently.
        staleness_hint: If not None, indicates this entry has been
            soft-invalidated. The hint is a human-readable reason
            (e.g., "mutation:task:update:1234567890"). Entries with
            a staleness_hint are candidates for background refresh
            but can still be served.

    Example:
        >>> stamp = FreshnessStamp(
        ...     last_verified_at=datetime.now(UTC),
        ...     source=VerificationSource.API_FETCH,
        ... )
        >>> stamp.age_seconds()
        0.001
    """

    last_verified_at: datetime
    source: VerificationSource = VerificationSource.UNKNOWN
    staleness_hint: str | None = None

    def age_seconds(self, now: datetime | None = None) -> float:
        """Seconds since last verification.

        Args:
            now: Current time for comparison. Defaults to UTC now.

        Returns:
            Age in seconds as a float.
        """
        now = now or datetime.now(UTC)
        # Ensure timezone-aware comparison
        verified = self.last_verified_at
        if verified.tzinfo is None:
            verified = verified.replace(tzinfo=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return (now - verified).total_seconds()

    def is_soft_invalidated(self) -> bool:
        """True if this entry was soft-invalidated (stale but available)."""
        return self.staleness_hint is not None

    def with_staleness_hint(self, hint: str) -> FreshnessStamp:
        """Create a new stamp with a staleness hint applied.

        Does not mutate -- returns a new frozen instance.

        Args:
            hint: Reason for soft invalidation.

        Returns:
            New FreshnessStamp with the hint set.
        """
        return FreshnessStamp(
            last_verified_at=self.last_verified_at,
            source=self.source,
            staleness_hint=hint,
        )

    @classmethod
    def now(
        cls,
        source: VerificationSource = VerificationSource.UNKNOWN,
    ) -> FreshnessStamp:
        """Create a stamp verified at the current moment.

        Convenience factory for the common case of "data is fresh
        as of right now."

        Args:
            source: How freshness was established.

        Returns:
            New FreshnessStamp with last_verified_at=now.
        """
        return cls(
            last_verified_at=datetime.now(UTC),
            source=source,
        )
```

### Design Rationale

**Why a separate class instead of fields on CacheEntry?** CacheEntry already has 8 fields. Adding 3 more (last_verified_at, source, staleness_hint) would clutter the constructor signature. A nested frozen dataclass keeps freshness concerns grouped and is composable -- the same stamp structure can be used by both task-level CacheEntry and DataFrame-level CacheEntry.

**Why `staleness_hint` instead of a boolean `is_stale`?** A string hint carries diagnostic information. When an operator sees a stale entry, the hint tells them why: "mutation:task:update:1234567890" vs. "ttl_expired" vs. "schema_mismatch". This is strictly more useful than a boolean.

**Why `VerificationSource` instead of just timestamps?** Two entries verified 5 minutes ago have different reliability depending on source. An `API_FETCH` is definitive. A `MUTATION_EVENT` is an inference (we infer the data is fresh because we just triggered a cache write after a mutation). A `BATCH_CHECK` is a lightweight HEAD check that confirms `modified_at` has not changed but does not fetch the full payload. Future consumers can use this distinction for confidence-weighted serving.

---

## Component Design: FreshnessPolicy

### Policy Class

```python
# src/autom8_asana/cache/freshness_policy.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.cache.entry import CacheEntry
    from autom8_asana.cache.freshness_stamp import (
        FreshnessClassification,
        FreshnessStamp,
    )


# Threshold: entry is "approaching stale" when age exceeds
# this fraction of the entity's TTL. 0.75 means at 75% of TTL,
# the entry transitions from FRESH to APPROACHING_STALE.
_DEFAULT_APPROACHING_THRESHOLD = 0.75


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    """Stateless evaluator for freshness classification.

    Uses EntityRegistry TTLs to classify cache entries into
    three freshness states. The approaching_threshold controls
    when entries transition from FRESH to APPROACHING_STALE.

    Thread Safety: Frozen and stateless. Safe for concurrent use.

    Attributes:
        approaching_threshold: Fraction of TTL at which an entry
            transitions from FRESH to APPROACHING_STALE.
            Default 0.75 (75% of TTL).

    Example:
        >>> from autom8_asana.cache.freshness_policy import FreshnessPolicy
        >>> policy = FreshnessPolicy()
        >>> classification = policy.evaluate(entry)
        >>> if classification == FreshnessClassification.STALE:
        ...     trigger_refresh()
    """

    approaching_threshold: float = _DEFAULT_APPROACHING_THRESHOLD

    def evaluate(
        self,
        entry: CacheEntry,
        entity_type: str | None = None,
        now: datetime | None = None,
    ) -> FreshnessClassification:
        """Classify an entry's freshness.

        Decision tree:
        1. If entry has no freshness stamp -> STALE (legacy entry)
        2. If stamp has a staleness_hint -> STALE (soft-invalidated)
        3. If stamp age > entity TTL -> STALE
        4. If stamp age > entity TTL * approaching_threshold -> APPROACHING_STALE
        5. Otherwise -> FRESH

        Args:
            entry: Cache entry to evaluate.
            entity_type: Entity type name for TTL lookup. If None,
                falls back to the entry's metadata or DEFAULT_TTL.
            now: Current time for age calculation. Defaults to UTC now.

        Returns:
            FreshnessClassification enum value.
        """
        from autom8_asana.cache.freshness_stamp import FreshnessClassification

        stamp = entry.freshness_stamp
        if stamp is None:
            return FreshnessClassification.STALE

        if stamp.is_soft_invalidated():
            return FreshnessClassification.STALE

        ttl = self._get_ttl(entry, entity_type)
        age = stamp.age_seconds(now)

        if age > ttl:
            return FreshnessClassification.STALE

        if age > ttl * self.approaching_threshold:
            return FreshnessClassification.APPROACHING_STALE

        return FreshnessClassification.FRESH

    def evaluate_stamp(
        self,
        stamp: FreshnessStamp,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> FreshnessClassification:
        """Classify freshness from a stamp and explicit TTL.

        Lower-level method for callers that already know the TTL.
        Used by DataFrameCache for aggregate freshness evaluation
        where the TTL comes from the entity type, not the CacheEntry.

        Args:
            stamp: Freshness stamp to evaluate.
            ttl_seconds: TTL in seconds.
            now: Current time. Defaults to UTC now.

        Returns:
            FreshnessClassification enum value.
        """
        from autom8_asana.cache.freshness_stamp import FreshnessClassification

        if stamp.is_soft_invalidated():
            return FreshnessClassification.STALE

        age = stamp.age_seconds(now)

        if age > ttl_seconds:
            return FreshnessClassification.STALE

        if age > ttl_seconds * self.approaching_threshold:
            return FreshnessClassification.APPROACHING_STALE

        return FreshnessClassification.FRESH

    def _get_ttl(self, entry: CacheEntry, entity_type: str | None) -> int:
        """Resolve TTL from EntityRegistry.

        Falls back through: explicit entity_type -> entry metadata
        -> DEFAULT_TTL.

        Args:
            entry: Cache entry (may have project_gid or metadata hints).
            entity_type: Explicit entity type name.

        Returns:
            TTL in seconds.
        """
        from autom8_asana.config import DEFAULT_TTL
        from autom8_asana.core.entity_registry import get_registry

        registry = get_registry()

        # Try explicit entity_type parameter
        if entity_type:
            return registry.get_entity_ttl(entity_type, default=DEFAULT_TTL)

        # Try entry metadata
        et_from_meta = entry.metadata.get("entity_type")
        if et_from_meta:
            return registry.get_entity_ttl(et_from_meta, default=DEFAULT_TTL)

        # Fallback
        return entry.ttl or DEFAULT_TTL
```

### Design Rationale

**Why not merge with `_check_freshness` in DataFrameCache?** The existing `DataFrameCache._check_freshness()` is a 5-state machine (FRESH, STALE_SERVABLE, EXPIRED_SERVABLE, SCHEMA_MISMATCH, WATERMARK_STALE) that controls the SWR lifecycle. `FreshnessPolicy` is a simpler 3-state classification for individual cache entries. They serve different purposes: `_check_freshness` decides whether to serve and whether to trigger SWR; `FreshnessPolicy` classifies how confident we are in the data's currency. The two are complementary.

**Why three states instead of two?** APPROACHING_STALE enables proactive behavior. When a consumer sees APPROACHING_STALE, it can trigger a background refresh *before* the data becomes stale, reducing the window where stale data is served. This is similar to SWR but applies at the individual entry level rather than the DataFrame level.

**Why `approaching_threshold = 0.75`?** At 75% of TTL, there is still 25% of the TTL window remaining for a background refresh to complete. For a 300s TTL, that is 75 seconds. For a 900s TTL, that is 225 seconds. Both are comfortable margins for a single API fetch.

---

## Integration: CacheEntry Extension

### Change to `cache/entry.py`

The `CacheEntry` frozen dataclass gains an optional `freshness_stamp` field:

```python
# Modification to CacheEntry in cache/entry.py

@dataclass(frozen=True)
class CacheEntry:
    """Immutable cache entry with versioning and freshness metadata.

    Attributes:
        ... (existing fields unchanged) ...
        freshness_stamp: Optional freshness metadata. When present,
            indicates when and how the data was verified as fresh.
            When None, the entry is a legacy entry without freshness
            tracking (treated as STALE by FreshnessPolicy).
    """

    key: str
    data: dict[str, Any]
    entry_type: EntryType
    version: datetime
    cached_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    ttl: int | None = 300
    project_gid: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    freshness_stamp: FreshnessStamp | None = None  # NEW
```

### Backward Compatibility

The field has a default value of `None`. All existing code that constructs `CacheEntry` without providing `freshness_stamp` continues to work. The `FreshnessPolicy` treats `None` stamps as STALE, which is the conservative safe default -- legacy entries are never incorrectly classified as fresh.

### Serialization Impact

Both `RedisCacheProvider` and `S3CacheProvider` serialize CacheEntry to/from JSON. The `freshness_stamp` field must be added to serialization:

**Redis (`_serialize_entry` / `_deserialize_entry`):**
```python
# In _serialize_entry, add:
"freshness_stamp": json.dumps({
    "last_verified_at": format_version(entry.freshness_stamp.last_verified_at),
    "source": entry.freshness_stamp.source.value,
    "staleness_hint": entry.freshness_stamp.staleness_hint,
}) if entry.freshness_stamp else "",

# In _deserialize_entry, add:
stamp_str = data.get("freshness_stamp", "")
freshness_stamp = None
if stamp_str:
    stamp_data = json.loads(stamp_str)
    freshness_stamp = FreshnessStamp(
        last_verified_at=parse_version(stamp_data["last_verified_at"]),
        source=VerificationSource(stamp_data.get("source", "unknown")),
        staleness_hint=stamp_data.get("staleness_hint"),
    )
```

**S3 (`_serialize_entry` / `_deserialize_entry`):**
Same pattern -- the stamp is serialized as a nested dict within the JSON body.

**Key constraint**: An entry serialized without a stamp and deserialized by new code yields `freshness_stamp=None`. An entry serialized with a stamp and deserialized by old code (rollback scenario) ignores the unknown field in `json.loads`. Both directions are safe.

---

## Integration: TieredCacheProvider

### Freshness-Aware Promotion

Currently, `TieredCacheProvider._promote_entry()` unconditionally copies the S3 entry to Redis with a new `cached_at` and `promotion_ttl`. With freshness stamps, promotion should compare freshness between the promoted entry and any existing hot-tier entry:

```python
# Modified get_versioned in TieredCacheProvider

def get_versioned(
    self,
    key: str,
    entry_type: EntryType,
    freshness: Freshness | None = None,
) -> CacheEntry | None:
    if freshness is None:
        freshness = Freshness.EVENTUAL

    # Check hot tier first
    hot_entry = self._hot.get_versioned(key, entry_type, freshness)

    if hot_entry is not None:
        return hot_entry

    # S3 disabled -- return miss
    if not self.s3_enabled or self._cold is None:
        return None

    # Check cold tier
    try:
        cold_entry = self._cold.get_versioned(key, entry_type, freshness)
    except CACHE_TRANSIENT_ERRORS as e:
        logger.warning(
            "s3_get_versioned_failed",
            extra={"key": key, "entry_type": entry_type.value, "error": str(e)},
        )
        return None

    if cold_entry is None:
        return None

    # Promote to hot tier with freshness stamp propagation
    promoted = self._promote_entry(cold_entry)
    try:
        self._hot.set_versioned(key, promoted)
        self._metrics.record_promotion(key=key, entry_type=entry_type.value)
    except CACHE_TRANSIENT_ERRORS as e:
        logger.warning(
            "redis_promotion_failed",
            extra={"key": key, "error": str(e)},
        )

    return cold_entry
```

The `_promote_entry` method preserves the freshness stamp with updated source:

```python
def _promote_entry(self, entry: CacheEntry) -> CacheEntry:
    """Create a new entry with promotion TTL for hot tier.

    Preserves the original freshness stamp but updates its source
    to PROMOTION to indicate the data came from cold storage.
    """
    from autom8_asana.cache.freshness_stamp import (
        FreshnessStamp,
        VerificationSource,
    )

    promoted_stamp = None
    if entry.freshness_stamp is not None:
        promoted_stamp = FreshnessStamp(
            last_verified_at=entry.freshness_stamp.last_verified_at,
            source=VerificationSource.PROMOTION,
            staleness_hint=entry.freshness_stamp.staleness_hint,
        )

    return replace(
        entry,
        ttl=self._config.promotion_ttl,
        cached_at=datetime.now(UTC),
        freshness_stamp=promoted_stamp,
    )
```

### Cross-Tier Freshness Comparison

When both tiers have an entry, the current design always serves from the hot tier. This remains unchanged -- the hot tier is the fast path and is assumed to be the most recent write. The freshness stamp does not alter the read path; it provides metadata for downstream consumers to interpret.

However, the promotion path now preserves lineage. If an S3 entry was originally verified by an API fetch 30 minutes ago, the promoted entry's stamp still shows `last_verified_at` from 30 minutes ago with `source=PROMOTION`. A consumer can distinguish between "data fetched 1 second ago" (source=API_FETCH) and "data fetched 30 minutes ago, promoted from S3" (source=PROMOTION).

---

## Integration: DataFrameCache

### Aggregate Freshness

The `DataFrameCache.CacheEntry` (separate from the task-level CacheEntry) gains an optional `freshness_stamp` field that represents the **aggregate freshness** of the DataFrame:

```python
# Modification to DataFrameCache CacheEntry in dataframe_cache.py

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
    freshness_stamp: FreshnessStamp | None = None  # NEW

    def __post_init__(self) -> None:
        self.row_count = len(self.dataframe)
```

### Computing Aggregate Freshness on Build

When `DataFrameCache.put_async()` is called after a DataFrame build, the caller provides section-level freshness information. The aggregate stamp uses the **oldest** section's verification time:

```python
async def put_async(
    self,
    project_gid: str,
    entity_type: str,
    dataframe: pl.DataFrame,
    watermark: datetime,
    section_stamps: list[FreshnessStamp] | None = None,  # NEW
) -> None:
    """Store DataFrame in both tiers.

    Args:
        project_gid: Asana project GID.
        entity_type: Entity type.
        dataframe: Polars DataFrame to cache.
        watermark: Freshness watermark (based on max modified_at).
        section_stamps: Optional per-section freshness stamps.
            If provided, aggregate freshness is the OLDEST stamp.
            If None, a new stamp is created with source=API_FETCH.
    """
    from autom8_asana.cache.freshness_stamp import (
        FreshnessStamp,
        VerificationSource,
    )

    # Compute aggregate freshness
    if section_stamps:
        # Oldest section determines aggregate freshness
        oldest = min(section_stamps, key=lambda s: s.last_verified_at)
        aggregate_stamp = FreshnessStamp(
            last_verified_at=oldest.last_verified_at,
            source=oldest.source,
            staleness_hint=oldest.staleness_hint,
        )
    else:
        # Default: data is fresh as of now
        aggregate_stamp = FreshnessStamp.now(
            source=VerificationSource.API_FETCH
        )

    # ... rest of put_async unchanged, passing aggregate_stamp
    # to CacheEntry constructor ...
```

### Freshness in the Get Path

The existing `_check_freshness_and_serve` method remains the authority on whether to serve, trigger SWR, or reject. The freshness stamp provides *additional* metadata that flows to the `FreshnessInfo` side-channel:

```python
def _build_freshness_info(
    self,
    entry: CacheEntry,
    status: FreshnessStatus,
    cache_key: str,
) -> FreshnessInfo:
    """Build FreshnessInfo with stamp-aware age computation."""
    from autom8_asana.config import DEFAULT_ENTITY_TTLS, DEFAULT_TTL

    entity_ttl = DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)

    # If entry has a freshness stamp, use stamp age (more accurate)
    if entry.freshness_stamp is not None:
        age = entry.freshness_stamp.age_seconds()
    else:
        age = (datetime.now(UTC) - entry.created_at).total_seconds()

    info = FreshnessInfo(
        freshness=status.value,
        data_age_seconds=round(age, 1),
        staleness_ratio=round(age / entity_ttl, 2) if entity_ttl > 0 else 0.0,
    )
    self._last_freshness[cache_key] = info
    return info
```

---

## Integration: MutationInvalidator

### Soft Invalidation Mode

The `MutationInvalidator` currently performs hard eviction (delete from cache). Soft invalidation is an alternative that keeps the entry in cache but marks it with a `staleness_hint`. This enables graceful degradation: consumers can serve the stale entry with a warning while a background refresh runs.

```python
# Configuration for soft invalidation behavior

@dataclass
class SoftInvalidationConfig:
    """Controls when MutationInvalidator uses soft vs. hard invalidation.

    Soft invalidation marks entries stale without evicting. Useful when:
    - Background refresh will be triggered soon (SWR)
    - Stale data is better than no data (circuit breaker open)
    - High mutation throughput would cause thundering herd on eviction

    Hard invalidation (default) evicts entries immediately. Preferred when:
    - Data correctness is critical
    - Cache can be repopulated quickly
    - No SWR mechanism is in place

    Attributes:
        enabled: Master switch for soft invalidation.
        soft_entity_kinds: Entity kinds that use soft invalidation.
            Defaults to empty (all use hard invalidation).
        soft_mutation_types: Mutation types that use soft invalidation.
            Defaults to UPDATE only (creates/deletes should hard-evict).
    """

    enabled: bool = False
    soft_entity_kinds: frozenset[str] = frozenset()
    soft_mutation_types: frozenset[str] = frozenset({"update"})
```

The `MutationInvalidator` gains a `soft_invalidate` path in `_invalidate_entity_entries`:

```python
def _invalidate_entity_entries(self, gid: str, event: MutationEvent) -> None:
    """Invalidate or soft-mark TASK, SUBTASKS, DETECTION entries."""
    if self._should_soft_invalidate(event):
        self._soft_invalidate_entity_entries(gid, event)
    else:
        self._hard_invalidate_entity_entries(gid)

def _soft_invalidate_entity_entries(
    self, gid: str, event: MutationEvent
) -> None:
    """Mark entries stale without evicting.

    Reads each entry, applies a staleness hint to its stamp,
    and writes back. If the entry does not exist or has no stamp,
    falls back to hard invalidation.
    """
    hint = (
        f"mutation:{event.entity_kind.value}:"
        f"{event.mutation_type.value}:{event.entity_gid}"
    )

    for entry_type in _TASK_ENTRY_TYPES:
        try:
            entry = self._cache.get_versioned(gid, entry_type)
            if entry is None or entry.freshness_stamp is None:
                # No entry or legacy entry -- hard invalidate
                self._cache.invalidate(gid, [entry_type])
                continue

            # Apply staleness hint
            marked_stamp = entry.freshness_stamp.with_staleness_hint(hint)
            marked_entry = replace(entry, freshness_stamp=marked_stamp)
            self._cache.set_versioned(gid, marked_entry)

        except Exception as exc:
            logger.warning(
                "soft_invalidation_failed_falling_back",
                extra={
                    "gid": gid,
                    "entry_type": entry_type.value,
                    "error": str(exc),
                },
            )
            # Fallback: hard invalidate on any error
            try:
                self._cache.invalidate(gid, [entry_type])
            except Exception:
                pass
```

### Default Behavior Preservation

Soft invalidation is **disabled by default** (`SoftInvalidationConfig.enabled = False`). The existing hard-eviction behavior is unchanged unless an operator explicitly enables soft invalidation. This is a one-way door that should be enabled only after observing the freshness metadata in production.

---

## Backward Compatibility

### Compatibility Matrix

| Component | Behavior Before | Behavior After | Breaking? |
|-----------|----------------|----------------|-----------|
| `CacheEntry` construction without stamp | Works | Works (stamp=None) | No |
| `CacheEntry` serialized without stamp | Works | Deserialized with stamp=None | No |
| `CacheEntry` with stamp deserialized by old code | N/A | Old code ignores unknown JSON field | No |
| `TieredCacheProvider.get_versioned` | Returns entry | Returns entry (unchanged) | No |
| `TieredCacheProvider._promote_entry` | Sets cached_at, ttl | Also sets freshness_stamp | No |
| `DataFrameCache.put_async` without section_stamps | Works | Works (default stamp created) | No |
| `DataFrameCache._check_freshness` | 5-state machine | 5-state machine (unchanged) | No |
| `MutationInvalidator.fire_and_forget` | Hard eviction | Hard eviction (soft disabled by default) | No |
| `StalenessCheckCoordinator.check_and_get_async` | Extends TTL | Extends TTL + sets stamp | No (additive) |
| `FreshnessInfo.data_age_seconds` | Based on created_at | Based on stamp if available, else created_at | Cosmetic |

### Migration Path

**Phase 1: Introduce types (this sprint).** Add `FreshnessStamp`, `FreshnessPolicy`, extend `CacheEntry`. All new fields are optional with None defaults. No behavior changes.

**Phase 2: Stamp on write (this sprint).** Modify the write paths to attach stamps:
- `BaseClient._cache_response()` -> stamp with `API_FETCH`
- `StalenessCheckCoordinator._extend_ttl()` -> stamp with `BATCH_CHECK`
- `DataFrameCache.put_async()` -> aggregate stamp
- `TieredCacheProvider._promote_entry()` -> propagate stamp with `PROMOTION`

**Phase 3: Consume stamps (this sprint or next).** Modify read paths to use stamps:
- `DataFrameCache._build_freshness_info()` -> prefer stamp age over created_at
- API response headers -> optional freshness header
- Soft invalidation -> enabled per deployment

---

## Data Flow Diagrams

### Sequence: Task Fetch with Freshness Stamp

```
Client          BaseClient      CacheProvider     Asana API
  |                  |                |                |
  |  get_task(gid)   |                |                |
  |----------------->|                |                |
  |                  |  get_versioned |                |
  |                  |--------------->|                |
  |                  |   None (miss)  |                |
  |                  |<---------------|                |
  |                  |                |                |
  |                  |  fetch from API|                |
  |                  |------------------------------>  |
  |                  |   task_data    |                |
  |                  |<------------------------------  |
  |                  |                |                |
  |                  |  set_versioned |                |
  |                  |  (with stamp:  |                |
  |                  |   API_FETCH,   |                |
  |                  |   now)         |                |
  |                  |--------------->|                |
  |                  |                |                |
  |   task_data      |                |                |
  |<-----------------|                |                |
```

### Sequence: Mutation with Soft Invalidation

```
Client      Route Handler    MutationInvalidator   CacheProvider
  |              |                    |                   |
  | PUT /task/X  |                    |                   |
  |------------->|                    |                   |
  |              |  fire_and_forget   |                   |
  |              |  (soft=true)       |                   |
  |              |------------------->|                   |
  | 200 OK       |                    |                   |
  |<-------------|                    |                   |
  |              |                    |  get_versioned(X) |
  |              |                    |------------------>|
  |              |                    |  entry (has stamp)|
  |              |                    |<------------------|
  |              |                    |                   |
  |              |                    |  set_versioned(X, |
  |              |                    |   entry with      |
  |              |                    |   staleness_hint) |
  |              |                    |------------------>|
  |              |                    |                   |
```

### Sequence: Cross-Tier Promotion with Freshness

```
Reader       TieredCache      Redis(Hot)        S3(Cold)
  |              |                |                |
  | get_versioned|                |                |
  |------------->|                |                |
  |              | get_versioned  |                |
  |              |--------------->|                |
  |              | None (expired) |                |
  |              |<---------------|                |
  |              |                |                |
  |              | get_versioned  |                |
  |              |------------------------------>  |
  |              | entry (stamp:  |                |
  |              |  API_FETCH,    |                |
  |              |  T-1800s)      |                |
  |              |<------------------------------  |
  |              |                |                |
  |              | set_versioned  |                |
  |              | (stamp:        |                |
  |              |  PROMOTION,    |                |
  |              |  T-1800s)      |                |
  |              |--------------->|                |
  |              |                |                |
  |  entry       |                |                |
  |<-------------|                |                |
  |              |                |                |
  | (consumer evaluates stamp:                    |
  |  age=1800s, source=PROMOTION                  |
  |  -> FreshnessPolicy: STALE for 300s TTL)      |
```

### Sequence: DataFrame Build with Section Freshness

```
Builder       SectionPersistence    CacheProvider    DataFrameCache
  |                  |                    |                |
  | build sections   |                    |                |
  | for project P    |                    |                |
  |                  |                    |                |
  | section S1:      |                    |                |
  |  cached (stamp:  |                    |                |
  |   API_FETCH,     |                    |                |
  |   T-120s)        |                    |                |
  |                  |                    |                |
  | section S2:      |                    |                |
  |  miss -> fetch   |                    |                |
  |  (stamp:         |                    |                |
  |   API_FETCH,     |                    |                |
  |   T-0s)          |                    |                |
  |                  |                    |                |
  | section S3:      |                    |                |
  |  cached (stamp:  |                    |                |
  |   BATCH_CHECK,   |                    |                |
  |   T-600s)        |                    |                |
  |                  |                    |                |
  | put_async(       |                    |                |
  |  P, entity,      |                    |                |
  |  df, watermark,  |                    |                |
  |  stamps=[        |                    |                |
  |   S1@T-120,      |                    |                |
  |   S2@T-0,        |                    |                |
  |   S3@T-600])     |                    |                |
  |---------------------------------------------->|       |
  |                  |                    |        |       |
  |                  |                    | Aggregate:     |
  |                  |                    | oldest=S3@T-600|
  |                  |                    | source=BATCH   |
  |                  |                    |                |
```

---

## Non-Functional Considerations

### Performance

| Concern | Approach | Target |
|---------|----------|--------|
| FreshnessStamp construction | Frozen dataclass with slots; `datetime.now(UTC)` is ~0.5us | < 1us per stamp |
| FreshnessPolicy.evaluate | Dict lookup for TTL + timestamp subtraction | O(1), < 1us per evaluation |
| Serialization overhead | Stamp is 3 fields (~100 bytes JSON) | < 5% increase in CacheEntry size |
| Promotion freshness comparison | Single timestamp comparison | O(1), negligible |
| Aggregate freshness (DataFrame) | `min()` over section stamps (typically 5-20 sections) | O(n) where n is section count |

### Memory Impact

Each `FreshnessStamp` occupies ~64 bytes (datetime + enum + optional string, with slots). For 10,000 cached entries, this adds ~640KB. Negligible compared to the entry data payloads.

### Thread Safety

`FreshnessStamp` is `frozen=True` with `slots=True`. It is immutable and thread-safe without locks. `FreshnessPolicy` is stateless and thread-safe. The only mutable state is in existing components (CacheProvider storage), which already handle concurrency.

### Observability

New structured log events:

| Event | Level | Fields |
|-------|-------|--------|
| `freshness_stamp_created` | DEBUG | gid, entry_type, source, age_seconds |
| `freshness_soft_invalidation` | INFO | gid, entry_type, hint, previous_source |
| `freshness_promotion_propagated` | DEBUG | gid, original_source, original_age_seconds |
| `freshness_aggregate_computed` | DEBUG | project_gid, entity_type, oldest_age_seconds, section_count |
| `soft_invalidation_failed_falling_back` | WARNING | gid, entry_type, error |

---

## Test Strategy

### Unit Tests: FreshnessStamp

| Test | Validates |
|------|-----------|
| `test_stamp_age_seconds` | `age_seconds()` returns correct elapsed time |
| `test_stamp_age_seconds_with_explicit_now` | Deterministic testing with explicit `now` parameter |
| `test_stamp_is_soft_invalidated_false` | Default stamp has no hint |
| `test_stamp_is_soft_invalidated_true` | Stamp with hint returns True |
| `test_stamp_with_staleness_hint` | Creates new stamp, does not mutate original |
| `test_stamp_now_factory` | `FreshnessStamp.now()` creates stamp verified at current time |
| `test_stamp_frozen` | Cannot mutate fields after creation |
| `test_stamp_timezone_normalization` | Handles naive and aware datetimes correctly |

### Unit Tests: FreshnessPolicy

| Test | Validates |
|------|-----------|
| `test_evaluate_fresh` | Entry within TTL classified as FRESH |
| `test_evaluate_approaching_stale` | Entry at 76% of TTL classified as APPROACHING_STALE |
| `test_evaluate_stale_beyond_ttl` | Entry past TTL classified as STALE |
| `test_evaluate_no_stamp_is_stale` | Entry with `freshness_stamp=None` classified as STALE |
| `test_evaluate_soft_invalidated_is_stale` | Entry with staleness_hint classified as STALE |
| `test_evaluate_uses_registry_ttl` | TTL resolved from EntityRegistry via entity_type |
| `test_evaluate_fallback_ttl` | Unknown entity uses DEFAULT_TTL |
| `test_evaluate_stamp_direct` | `evaluate_stamp()` works with explicit TTL |
| `test_custom_approaching_threshold` | Non-default threshold value works |

### Unit Tests: CacheEntry Extension

| Test | Validates |
|------|-----------|
| `test_cache_entry_default_stamp_is_none` | Backward compat: no stamp by default |
| `test_cache_entry_with_stamp` | Can construct with freshness_stamp |
| `test_cache_entry_replace_preserves_stamp` | `dataclasses.replace` carries stamp |

### Unit Tests: Serialization

| Test | Validates |
|------|-----------|
| `test_redis_serialize_with_stamp` | Redis serialization includes stamp |
| `test_redis_serialize_without_stamp` | Redis serialization handles None stamp |
| `test_redis_deserialize_with_stamp` | Deserialization reconstructs stamp |
| `test_redis_deserialize_without_stamp` | Legacy data deserializes with stamp=None |
| `test_s3_serialize_with_stamp` | S3 serialization includes stamp |
| `test_s3_deserialize_legacy` | Legacy S3 data deserializes with stamp=None |

### Unit Tests: TieredCacheProvider

| Test | Validates |
|------|-----------|
| `test_promote_preserves_stamp` | Promoted entry has PROMOTION source |
| `test_promote_preserves_staleness_hint` | Staleness hint survives promotion |
| `test_promote_without_stamp` | Entry without stamp promotes with stamp=None |

### Unit Tests: MutationInvalidator Soft Mode

| Test | Validates |
|------|-----------|
| `test_soft_invalidation_marks_stamp` | Entry receives staleness_hint |
| `test_soft_invalidation_disabled_by_default` | Default config uses hard eviction |
| `test_soft_invalidation_fallback_on_error` | Falls back to hard eviction on failure |
| `test_soft_invalidation_fallback_no_stamp` | Legacy entry without stamp gets hard evicted |
| `test_soft_invalidation_config_entity_filter` | Only configured entity kinds get soft invalidation |

### Integration Tests

| Test | Validates |
|------|-----------|
| `test_end_to_end_stamp_through_tiers` | Write with stamp -> read from hot -> evict hot -> promote from cold -> stamp preserved |
| `test_dataframe_aggregate_freshness` | Build DataFrame with mixed section freshness -> aggregate uses oldest |
| `test_mutation_soft_then_read` | Soft invalidate -> read returns entry with hint -> FreshnessPolicy says STALE |
| `test_staleness_coordinator_sets_stamp` | StalenessCheckCoordinator extends TTL with BATCH_CHECK stamp |

### Test File Organization

```
tests/
  unit/
    cache/
      test_freshness_stamp.py           # FreshnessStamp unit tests
      test_freshness_policy.py          # FreshnessPolicy unit tests
      test_cache_entry_freshness.py     # CacheEntry extension tests
      test_tiered_freshness.py          # TieredCacheProvider stamp tests
      test_mutation_soft_invalidation.py # Soft invalidation tests
      test_redis_stamp_serialization.py # Redis serialization tests
      test_s3_stamp_serialization.py    # S3 serialization tests
  integration/
    cache/
      test_cross_tier_freshness.py      # End-to-end freshness propagation
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Serialization backward incompatibility** | Low | High (cache corruption) | New field defaults to None; deserialization ignores unknown fields; tested with round-trip serialization |
| **Import cycle from freshness_stamp -> entry** | Low | High (import failure) | FreshnessStamp has zero internal imports; CacheEntry imports FreshnessStamp at type-check only |
| **Soft invalidation read-modify-write race** | Medium | Low (harmless: double soft-mark or eviction) | Read-modify-write is not atomic but failure mode is benign: worst case, entry is hard-evicted instead of soft-marked |
| **EntityRegistry unavailable during evaluation** | Very Low | Medium (policy falls back to DEFAULT_TTL) | FreshnessPolicy catches KeyError and uses fallback TTL |
| **Performance regression from stamp serialization** | Very Low | Low (< 5% payload increase) | Stamp is 3 small fields; dominated by entry data payload |
| **Aggregate freshness misrepresents DataFrame age** | Low | Medium (consumer misinterprets) | Using oldest section is the conservative choice; documented behavior |

---

## ADRs

### ADR-001: FreshnessStamp as Optional Field (Not Required)

**Status**: Proposed

**Context**: Should `CacheEntry.freshness_stamp` be required or optional?

**Decision**: Optional with `None` default.

**Alternatives Considered**:
1. **Required field**: Every CacheEntry constructor call would need a stamp. This breaks ~40 test files and all existing write paths immediately. Migration cost is high for marginal benefit.
2. **Always-present with sentinel**: Default to a "zero" stamp (e.g., epoch). This is semantically dishonest -- an entry created before freshness tracking should not claim to have freshness metadata.

**Rationale**: Optional with None is the standard backward-compatible pattern used by `project_gid` and `metadata` fields already on CacheEntry. The `FreshnessPolicy` treats None stamps as STALE, which is the correct conservative default for legacy entries.

**Consequences**: Consumers must check for None before accessing stamp fields. This is enforced by the type system (`FreshnessStamp | None`).

### ADR-002: Three-State Classification (Not Five)

**Status**: Proposed

**Context**: The existing `FreshnessStatus` in DataFrameCache uses 5+ states. Should `FreshnessClassification` match it?

**Decision**: Three states: FRESH, APPROACHING_STALE, STALE.

**Alternatives Considered**:
1. **Five states matching FreshnessStatus**: FRESH, STALE_SERVABLE, EXPIRED_SERVABLE, SCHEMA_MISMATCH, WATERMARK_STALE. Rejected because FreshnessClassification operates on individual entries, not DataFrames. Schema and watermark checks are DataFrame-level concerns.
2. **Two states (FRESH/STALE)**: Simpler but loses the APPROACHING_STALE signal that enables proactive refresh.
3. **Numeric confidence score (0.0-1.0)**: Overly precise. Three states match the action space: serve (FRESH), serve-and-refresh (APPROACHING_STALE), refresh-or-reject (STALE).

**Rationale**: Three states map to three consumer actions. More states would not change what consumers do. Fewer states would lose the proactive refresh signal.

**Consequences**: `FreshnessClassification` and `FreshnessStatus` are independent enums. The DataFrameCache continues to use `FreshnessStatus` for its SWR state machine. `FreshnessClassification` is used by individual entry consumers. No ambiguity because they operate at different layers.

### ADR-003: Soft Invalidation Disabled by Default

**Status**: Proposed

**Context**: Soft invalidation (marking stale instead of evicting) is a powerful feature but changes the data correctness contract. Should it be the default?

**Decision**: Disabled by default. Enabled per-deployment via `SoftInvalidationConfig`.

**Alternatives Considered**:
1. **Enabled by default**: Would change existing behavior where mutations evict immediately. Could serve stale data in scenarios where the current system serves no data (cache miss -> API fetch). This is a correctness regression for consumers that expect mutations to clear cache.
2. **Enabled per entity kind**: More granular but same risk profile as option 1.

**Rationale**: Hard eviction is the simpler, safer contract. Soft invalidation is an optimization for specific use cases (high mutation throughput, SWR-enabled consumers, graceful degradation). It should be opt-in after operators observe the freshness metadata and understand the trade-offs.

**Consequences**: First deployment adds freshness metadata everywhere but does not change invalidation behavior. Soft invalidation can be enabled later with confidence because the freshness metadata provides observability into what would happen.

### ADR-004: Oldest Section Determines Aggregate Freshness

**Status**: Proposed

**Context**: A DataFrame is built from N sections. Each section may have a different freshness stamp. What is the aggregate freshness?

**Decision**: The oldest (least fresh) section determines the aggregate.

**Alternatives Considered**:
1. **Newest section**: Optimistic. Would claim the DataFrame is fresh when the majority of its data might be stale. Misleading.
2. **Weighted average**: Complex and hard to interpret. What does "average freshness" mean to a consumer?
3. **Per-section stamps stored on DataFrame**: Maximum information but high storage cost and complex consumer logic.

**Rationale**: The oldest section is the conservative choice. A DataFrame is only as fresh as its stalest data. This is analogous to the existing `watermark` field which uses `max(modified_at)` -- both use an extremum to represent the aggregate.

**Consequences**: A DataFrame with one stale section will be classified as stale even if 9 other sections are fresh. This is by design -- the stale section contains potentially incorrect data. Consumers who need per-section granularity should access sections directly.

---

## Success Criteria

### Quantitative

| Metric | Baseline | Target | How Measured |
|--------|----------|--------|-------------|
| CacheEntry freshness coverage | 0% (no stamps) | 100% of new writes carry stamps | Count entries with `freshness_stamp is not None` in cache stats |
| Freshness policy evaluation latency | N/A | < 1us per evaluation | Microbenchmark in test suite |
| Serialization overhead | 0 bytes | < 150 bytes per entry (stamp JSON) | Compare serialized sizes before/after |
| Backward compatibility test failures | 0 | 0 | Full test suite passes with no modifications to existing tests |
| Soft invalidation stale-serve count | N/A (disabled by default) | Measurable when enabled | New stat counter in MutationInvalidator |

### Qualitative

| Criterion | Validation |
|-----------|-----------|
| Consumer can determine data age without API call | `FreshnessPolicy.evaluate(entry)` returns classification without network I/O |
| Promoted entries retain lineage | Stamp source shows PROMOTION with original verification time preserved |
| DataFrame freshness reflects constituent quality | Aggregate stamp uses oldest section; documented and tested |
| Soft invalidation is reversible | Disable config flag -> hard eviction resumes; no migration needed |
| Design is observable | All freshness state changes emit structured log events |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| This TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-cross-tier-freshness.md` | Yes (written by architect) |
| Spike S0-001 (input) | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/spike-S0-001-cache-baseline.md` | Read |
| Spike S0-004 (input) | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/spike-S0-004-stale-data-analysis.md` | Read |
| Architectural opportunities (input) | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/architectural-opportunities.md` | Read |
| Sprint 1 TDD (structure ref) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-cache-invalidation-pipeline.md` | Read |
| B1 Entity Registry TDD (dependency) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-entity-knowledge-registry.md` | Read |
| MutationEvent | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/mutation_event.py` | Read |
| MutationInvalidator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/mutation_invalidator.py` | Read |
| TieredCacheProvider | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py` | Read |
| RedisCacheProvider | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py` | Read |
| S3CacheProvider | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py` | Read |
| EnhancedInMemoryCacheProvider | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py` | Read |
| DataFrameCache | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py` | Read |
| CacheProvider protocol | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py` | Read |
| CacheEntry / EntryType | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/entry.py` | Read |
| StalenessCheckCoordinator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/staleness_coordinator.py` | Read |
