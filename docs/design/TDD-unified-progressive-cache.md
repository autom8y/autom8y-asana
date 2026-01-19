# TDD: Unified Progressive DataFrame Cache Architecture

**TDD ID**: TDD-UNIFIED-PROGRESSIVE-CACHE-001
**Version**: 1.0
**Date**: 2026-01-16
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: PRD-unified-progressive-cache

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

This TDD specifies the unification of two parallel S3 caching systems into a single consistent storage model. The design replaces `S3Tier` with a new `ProgressiveTier` that reads from the existing `SectionPersistence` storage structure, eliminating a critical bug where self-refresh writes and query reads target different S3 locations.

### Solution Summary

| Component | Action | Purpose |
|-----------|--------|---------|
| `S3Tier` | DELETE | Remove redundant caching system |
| `ProgressiveTier` | CREATE | New tier reading from SectionPersistence storage |
| `DataFrameCache` | MODIFY | Replace S3Tier reference with ProgressiveTier |
| `factory.py` | MODIFY | Update initialization to use ProgressiveTier |
| `tiers/__init__.py` | MODIFY | Export ProgressiveTier instead of S3Tier |

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage key format | `dataframes/{project_gid}/` | Align with existing SectionPersistence structure |
| Staleness detection | Watermark-based | More accurate than TTL for incremental builds |
| Write delegation | ProgressiveTier calls SectionPersistence | Consistent write path for all consumers |
| Index loading | Lazy-load on demand | Reduce read latency for simple cache hits |

---

## Problem Statement

### Root Cause

Two parallel S3 caching mechanisms evolved independently, creating storage duplication and a critical location mismatch bug:

| System | Storage Location | Write Source |
|--------|------------------|--------------|
| **SectionPersistence** | `dataframes/{project_gid}/dataframe.parquet` | ProgressiveProjectBuilder |
| **S3Tier** | `asana-cache/dataframes/{entity}:{project}.parquet` | DataFrameCache.put_async() |

### The Bug

When `EntityQueryService.query()` encounters a cache miss and triggers self-refresh:

```
EntityQueryService.query()
  |
  +-> UniversalResolutionStrategy._get_dataframe()
        |
        +-> Check DataFrameCache.get_async()
        |     |
        |     +-> S3Tier.get_async("unit:proj-123")
        |           |
        |           +-> READS from: asana-cache/dataframes/unit:proj-123.parquet
        |           +-> Returns: MISS (data doesn't exist here)
        |
        +-> Trigger legacy_strategy.resolve() [cache miss path]
              |
              +-> ProgressiveProjectBuilder.build_with_parallel_fetch_async()
                    |
                    +-> SectionPersistence.write_final_artifacts_async()
                          |
                          +-> WRITES to: dataframes/proj-123/dataframe.parquet
                          +-> Returns: SUCCESS (but wrong location!)
```

**Result**: Query returns `CACHE_NOT_WARMED` error despite fresh data existing in S3 at a different location.

### Impact

- 503 errors on `/v1/query/offer` after successful self-refresh builds
- Cache warmer writes are not visible to subsequent query reads
- Storage duplication wastes S3 space and costs
- Developer confusion maintaining two parallel systems

---

## Goals and Non-Goals

### Goals

| ID | Goal | Rationale |
|----|------|-----------|
| G1 | Single storage location for DataFrames | Eliminate location mismatch bug |
| G2 | Delete S3Tier entirely | Remove redundant code and confusion |
| G3 | Preserve SectionPersistence storage structure | Maintain resume and incremental capabilities |
| G4 | Transparent migration for consumers | DataFrameCache interface unchanged |
| G5 | Watermark-based freshness validation | More accurate than TTL for incremental data |

### Non-Goals

| ID | Non-Goal | Reason |
|----|----------|--------|
| NG1 | Migrate existing S3Tier data | Old data will naturally expire; migration adds complexity |
| NG2 | Backwards compatibility with S3Tier format | Clean break preferred over maintaining two formats |
| NG3 | New API surface for ProgressiveTier | Match existing S3Tier interface for drop-in replacement |
| NG4 | Multi-region S3 replication | Existing single-region pattern sufficient |

---

## Proposed Architecture

### System Diagram (After)

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
       |  +-----------+  +-------------+  +------------+  |
       |  |Coalescer  |  |CircuitBreaker| |Invalidator |  |
       |  +-----------+  +-------------+  +------------+  |
       |        |               |                         |
       |        v               v                         |
       |  +-------------------------------------------+   |
       |  |           Tier Manager                    |   |
       |  +-------------------------------------------+   |
       |        |                         |               |
       |        v                         v               |
       |  +-------------+         +-----------------+     |
       |  | MemoryTier  |         | ProgressiveTier |     |
       |  | (Hot Cache) |         | (SectionPersistence)|  |
       |  +-------------+         +-----------------+     |
       +--------------------------------------------------+
                                 |
                   (on miss: build via strategy)
                                 v
       +--------------------------------------------------+
       |       ProgressiveProjectBuilder                   |
       |               |                                   |
       |               v                                   |
       |       SectionPersistence                          |
       |               |                                   |
       |               v                                   |
       |       S3: dataframes/{project_gid}/              |
       |           ├── manifest.json                       |
       |           ├── dataframe.parquet  <-- SINGLE LOC   |
       |           ├── watermark.json                      |
       |           └── index.json                          |
       +--------------------------------------------------+
```

### Storage Layout (Unified)

```
s3://bucket/
  dataframes/
    {project_gid}/
      manifest.json       # Build state, schema version, resume tracking
      dataframe.parquet   # Final merged DataFrame (ProgressiveTier reads)
      watermark.json      # Freshness metadata (watermark, row_count, schema)
      index.json          # GidLookupIndex (optional, lazy-loaded)
      sections/           # Section-level artifacts for resume
        {section_gid}.parquet
```

---

## Component Designs

### 5.1 ProgressiveTier

**Location**: `src/autom8_asana/cache/dataframe/tiers/progressive.py`

#### Class Design

```python
@dataclass
class ProgressiveTier:
    """S3 tier using SectionPersistence storage structure.

    Replaces S3Tier to use the same storage location as
    ProgressiveProjectBuilder, eliminating the dual-location bug.

    Key format translation:
      "{entity_type}:{project_gid}" -> "dataframes/{project_gid}/"

    Read path:
      1. Parse cache key to extract project_gid
      2. Read dataframes/{project_gid}/dataframe.parquet
      3. Read dataframes/{project_gid}/watermark.json for metadata
      4. Construct CacheEntry with DataFrame and metadata

    Write path:
      1. Delegate to SectionPersistence.write_final_artifacts_async()
      2. Ensures consistency with ProgressiveProjectBuilder writes

    Attributes:
        persistence: SectionPersistence instance for S3 operations.
        _stats: Operation statistics (reads, writes, errors, etc.).
    """

    persistence: SectionPersistence
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize statistics."""
        self._stats = {
            "reads": 0,
            "writes": 0,
            "read_errors": 0,
            "write_errors": 0,
            "bytes_read": 0,
            "bytes_written": 0,
            "not_found": 0,
        }
```

#### Interface Methods

```python
async def get_async(self, key: str) -> CacheEntry | None:
    """Get entry from progressive storage location.

    Args:
        key: Cache key in format "{entity_type}:{project_gid}".

    Returns:
        CacheEntry if found and readable, None otherwise.

    Algorithm:
        1. Parse key: "unit:1234567890" -> project_gid="1234567890"
        2. Read dataframe: dataframes/1234567890/dataframe.parquet
        3. Read watermark: dataframes/1234567890/watermark.json
        4. Construct CacheEntry with metadata from watermark
        5. Return None on any error (graceful degradation)
    """

async def put_async(self, key: str, entry: CacheEntry) -> bool:
    """Store entry to progressive storage location.

    Args:
        key: Cache key in format "{entity_type}:{project_gid}".
        entry: CacheEntry containing DataFrame and metadata.

    Returns:
        True if written successfully, False on error.

    Algorithm:
        1. Parse key to extract project_gid
        2. Serialize DataFrame to parquet bytes
        3. Call persistence.write_final_artifacts_async()
        4. Return success/failure
    """

async def exists_async(self, key: str) -> bool:
    """Check if entry exists.

    Args:
        key: Cache key in format "{entity_type}:{project_gid}".

    Returns:
        True if dataframe.parquet exists for project.
    """

async def delete_async(self, key: str) -> bool:
    """Delete entry (dataframe + watermark, not sections).

    Args:
        key: Cache key in format "{entity_type}:{project_gid}".

    Returns:
        True if deleted or didn't exist.
    """

def get_stats(self) -> dict[str, int]:
    """Get tier statistics."""
```

#### Key Parsing

```python
def _parse_key(self, key: str) -> tuple[str, str]:
    """Parse cache key into entity_type and project_gid.

    Args:
        key: Cache key in format "{entity_type}:{project_gid}".

    Returns:
        Tuple of (entity_type, project_gid).

    Raises:
        ValueError: If key format is invalid.

    Examples:
        "unit:1234567890" -> ("unit", "1234567890")
        "offer:9876543210" -> ("offer", "9876543210")
        "asset_edit:5555555555" -> ("asset_edit", "5555555555")
    """
    parts = key.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid cache key format: {key}")
    return parts[0], parts[1]
```

### 5.2 DataFrameCache Changes

**Location**: `src/autom8_asana/cache/dataframe_cache.py`

#### Attribute Rename

```python
# Before
@dataclass
class DataFrameCache:
    memory_tier: "MemoryTier"
    s3_tier: "S3Tier"  # <-- DELETE
    ...

# After
@dataclass
class DataFrameCache:
    memory_tier: "MemoryTier"
    progressive_tier: "ProgressiveTier"  # <-- REPLACE
    ...
```

#### Method Updates

No method signature changes required. Internal references update from `self.s3_tier` to `self.progressive_tier`:

```python
# In get_async():
# Before
entry = await self.s3_tier.get_async(cache_key)

# After
entry = await self.progressive_tier.get_async(cache_key)

# In put_async():
# Before
await self.s3_tier.put_async(cache_key, entry)

# After
await self.progressive_tier.put_async(cache_key, entry)
```

#### Validation Change: Watermark-Based vs TTL-Based

The existing `_is_valid()` method already supports watermark-based validation. No changes needed since ProgressiveTier provides `watermark` metadata in the CacheEntry.

```python
def _is_valid(
    self,
    entry: CacheEntry,
    current_watermark: datetime | None,
) -> bool:
    """Check if entry is valid (not stale, correct schema).

    Validation order:
    1. Schema version check (via SchemaRegistry lookup)
    2. TTL check (entry.is_stale())
    3. Watermark check (if current_watermark provided)
    """
    # No changes needed - existing implementation handles watermark
```

### 5.3 Factory Updates

**Location**: `src/autom8_asana/cache/dataframe/factory.py`

```python
def initialize_dataframe_cache() -> "DataFrameCache | None":
    """Initialize the singleton DataFrameCache with ProgressiveTier.

    Changes from S3Tier initialization:
    - Uses SectionPersistence instead of direct S3 client
    - No prefix configuration needed (uses SectionPersistence defaults)
    """
    from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
    from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
    from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
    from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier
    from autom8_asana.cache.dataframe_cache import (
        DataFrameCache,
        get_dataframe_cache as _get_cache,
        set_dataframe_cache,
    )
    from autom8_asana.dataframes.section_persistence import SectionPersistence
    from autom8_asana.settings import get_settings

    # Check if already initialized
    existing = _get_cache()
    if existing is not None:
        return existing

    settings = get_settings()

    # Check if S3 is configured
    if not settings.s3.bucket:
        logger.warning("dataframe_cache_s3_not_configured")
        return None

    # Create tiers
    memory_tier = MemoryTier(
        max_heap_percent=0.3,
        max_entries=100,
    )

    # Create SectionPersistence (handles its own S3 client)
    persistence = SectionPersistence(
        bucket=settings.s3.bucket,
        prefix="dataframes/",  # Standard prefix
    )

    progressive_tier = ProgressiveTier(
        persistence=persistence,
    )

    # Create coalescer and circuit breaker (unchanged)
    coalescer = DataFrameCacheCoalescer(max_wait_seconds=60.0)
    circuit_breaker = CircuitBreaker(
        failure_threshold=3,
        reset_timeout_seconds=60,
        success_threshold=1,
    )

    cache = DataFrameCache(
        memory_tier=memory_tier,
        progressive_tier=progressive_tier,  # Changed from s3_tier
        coalescer=coalescer,
        circuit_breaker=circuit_breaker,
        ttl_hours=12,
    )

    set_dataframe_cache(cache)

    logger.info(
        "dataframe_cache_initialized",
        extra={
            "tier_type": "progressive",
            "s3_bucket": settings.s3.bucket,
            "ttl_hours": 12,
        },
    )

    return cache
```

### 5.4 Tiers Module Updates

**Location**: `src/autom8_asana/cache/dataframe/tiers/__init__.py`

```python
"""Cache tier implementations for DataFrame caching.

Tiers:
    - MemoryTier: LRU cache with dynamic heap-based limits
    - ProgressiveTier: S3 storage via SectionPersistence (replaces S3Tier)
"""

from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier

__all__ = [
    "MemoryTier",
    "ProgressiveTier",
]
```

---

## Interface Contracts

### 6.1 ProgressiveTier <-> SectionPersistence

```python
# ProgressiveTier reads these SectionPersistence methods:

async def read_dataframe_async(project_gid: str) -> pl.DataFrame | None:
    """Read final merged DataFrame for project.

    Note: This method doesn't exist yet. ProgressiveTier will read
    directly via S3 client using the key pattern:
      dataframes/{project_gid}/dataframe.parquet
    """

async def read_watermark_async(project_gid: str) -> dict | None:
    """Read watermark metadata for project.

    Returns:
        Dict with keys: project_gid, watermark, row_count, columns, saved_at
        None if watermark doesn't exist.

    Note: This method doesn't exist yet. ProgressiveTier will read
    directly via S3 client using the key pattern:
      dataframes/{project_gid}/watermark.json
    """

# ProgressiveTier writes via existing method:

async def write_final_artifacts_async(
    project_gid: str,
    df: pl.DataFrame,
    watermark: datetime,
    index_data: dict | None = None,
) -> bool:
    """Write final artifacts atomically.

    Already implemented in SectionPersistence.
    """
```

### 6.2 Implementation Detail: Direct S3 Reads

Since SectionPersistence doesn't have granular read methods for DataFrame and watermark, ProgressiveTier will use the underlying AsyncS3Client directly for reads:

```python
async def get_async(self, key: str) -> CacheEntry | None:
    """Get entry from progressive storage."""
    entity_type, project_gid = self._parse_key(key)

    self._stats["reads"] += 1

    # Read DataFrame parquet
    df_key = f"{self.persistence._config.prefix}{project_gid}/dataframe.parquet"
    df_result = await self.persistence._s3_client.get_object_async(df_key)

    if not df_result.success:
        if df_result.not_found:
            self._stats["not_found"] += 1
            return None
        self._stats["read_errors"] += 1
        logger.warning("progressive_tier_read_error", extra={"key": key, "error": df_result.error})
        return None

    # Parse DataFrame
    try:
        df = pl.read_parquet(io.BytesIO(df_result.data))
        self._stats["bytes_read"] += len(df_result.data)
    except Exception as e:
        self._stats["read_errors"] += 1
        logger.warning("progressive_tier_parse_error", extra={"key": key, "error": str(e)})
        return None

    # Read watermark metadata
    wm_key = f"{self.persistence._config.prefix}{project_gid}/watermark.json"
    wm_result = await self.persistence._s3_client.get_object_async(wm_key)

    if wm_result.success:
        try:
            watermark_data = json.loads(wm_result.data.decode("utf-8"))
            watermark = datetime.fromisoformat(watermark_data["watermark"])
            schema_version = watermark_data.get("schema_version", "unknown")
        except Exception:
            # Fallback to current time if watermark parsing fails
            watermark = datetime.now(timezone.utc)
            schema_version = "unknown"
    else:
        # No watermark file - use current time
        watermark = datetime.now(timezone.utc)
        schema_version = "unknown"

    return CacheEntry(
        project_gid=project_gid,
        entity_type=entity_type,
        dataframe=df,
        watermark=watermark,
        created_at=watermark,  # Use watermark as created_at for consistency
        schema_version=schema_version,
    )
```

### 6.3 DataFrameCache <-> ProgressiveTier

Interface unchanged from S3Tier:

```python
# DataFrameCache calls these ProgressiveTier methods:

async def get_async(key: str) -> CacheEntry | None
async def put_async(key: str, entry: CacheEntry) -> bool
async def exists_async(key: str) -> bool
async def delete_async(key: str) -> bool
def get_stats() -> dict[str, int]
```

---

## Data Flow Diagrams

### 7.1 Cache Hit Flow (After)

```
Query Request
     |
     v
DataFrameCache.get_async("unit:proj-123")
     |
     +---> MemoryTier.get("unit:proj-123")
     |          |
     |          +---> HIT: Return entry directly
     |          |
     |          +---> MISS: Continue to ProgressiveTier
     |
     +---> ProgressiveTier.get_async("unit:proj-123")
                |
                +---> Parse key: project_gid = "proj-123"
                |
                +---> Read: dataframes/proj-123/dataframe.parquet
                |
                +---> Read: dataframes/proj-123/watermark.json
                |
                +---> Construct CacheEntry
                |
                +---> Hydrate MemoryTier
                |
                +---> Return entry
```

### 7.2 Cache Miss + Self-Refresh Flow (After)

```
Query Request
     |
     v
DataFrameCache.get_async("unit:proj-123")
     |
     +---> MemoryTier: MISS
     |
     +---> ProgressiveTier: MISS (no dataframe.parquet)
     |
     +---> Return None (cache miss)
     |
     v
UniversalResolutionStrategy._get_dataframe()
     |
     +---> Trigger legacy_strategy.resolve()
                |
                v
          ProgressiveProjectBuilder.build_with_parallel_fetch_async()
                |
                +---> Fetch sections from Asana API
                |
                +---> Write: dataframes/proj-123/sections/*.parquet
                |
                +---> Merge sections
                |
                +---> SectionPersistence.write_final_artifacts_async()
                          |
                          +---> Write: dataframes/proj-123/dataframe.parquet
                          +---> Write: dataframes/proj-123/watermark.json
                          +---> Write: dataframes/proj-123/index.json
     |
     v
DataFrameCache.put_async("unit:proj-123", entry)
     |
     +---> ProgressiveTier.put_async("unit:proj-123", entry)
     |          |
     |          +---> WRITES to: dataframes/proj-123/dataframe.parquet
     |          +---> SAME LOCATION as builder! (bug fixed)
     |
     +---> MemoryTier.put("unit:proj-123", entry)
     |
     v
Subsequent get_async() finds data at correct location
```

### 7.3 CacheWarmer Flow (After)

```
Lambda Pre-Deploy Warm
     |
     v
CacheWarmer.warm_all_async()
     |
     +---> For each entity_type in priority:
                |
                +---> strategy._build_dataframe(project_gid, client)
                |          |
                |          +---> ProgressiveProjectBuilder.build_...()
                |          |
                |          +---> Writes to: dataframes/{project_gid}/
                |
                +---> DataFrameCache.put_async(project_gid, entity_type, df, watermark)
                           |
                           +---> ProgressiveTier.put_async()
                           |          |
                           |          +---> SAME LOCATION (no duplication!)
                           |
                           +---> MemoryTier.put()
```

---

## Non-Functional Considerations

### 8.1 Performance

| Metric | Target | Approach |
|--------|--------|----------|
| Read latency (S3 hit) | < 500ms | Streaming parquet reads via polars |
| Write latency | < 1000ms | Async S3 writes via aioboto3 |
| Memory overhead | No increase | Same CacheEntry structure |
| Additional API calls | 0 | No Asana API calls in cache ops |

### 8.2 Reliability

| Metric | Target | Approach |
|--------|--------|----------|
| Cache consistency | 100% | Single storage location |
| Resume capability | 100% | Manifest-based tracking preserved |
| Build idempotency | 100% | Same content produces same result |
| Graceful degradation | Full | Return None on S3 errors |

### 8.3 Observability

Structured logging events:

| Event | Level | Extra Fields |
|-------|-------|--------------|
| `progressive_tier_read_success` | DEBUG | key, row_count, bytes_read, duration_ms |
| `progressive_tier_read_miss` | DEBUG | key |
| `progressive_tier_read_error` | WARNING | key, error, error_type |
| `progressive_tier_write_success` | INFO | key, row_count, bytes_written |
| `progressive_tier_write_error` | ERROR | key, error, error_type |

### 8.4 Storage

| Metric | Target | Notes |
|--------|--------|-------|
| Storage reduction | ~50% | Eliminating duplicate S3Tier location |
| S3 key pattern | `dataframes/{project_gid}/*` | Single consistent pattern |

---

## Migration Strategy

### 9.1 Clean Break Approach

Per PRD decision: No backwards compatibility with S3Tier format. Migration involves:

1. **Deploy new code**: ProgressiveTier replaces S3Tier
2. **Old data ignored**: S3Tier location (`asana-cache/dataframes/`) not accessed
3. **Fresh builds on miss**: First request after deploy rebuilds from Asana API
4. **Natural cleanup**: Old S3 objects can be deleted via lifecycle policy

### 9.2 Deployment Steps

1. **Pre-deploy**: Run cache warmer to populate SectionPersistence location
2. **Deploy**: New code reads/writes only to SectionPersistence location
3. **Verify**: Confirm query endpoints return data (no CACHE_NOT_WARMED)
4. **Cleanup** (optional): Delete objects under `asana-cache/dataframes/`

### 9.3 Rollback Plan

If issues discovered:
1. Revert to previous code (S3Tier)
2. Cache warmer will repopulate S3Tier location
3. System returns to pre-migration state

---

## Test Strategy

### 10.1 Unit Tests for ProgressiveTier

**Location**: `tests/unit/cache/dataframe/test_progressive_tier.py`

```python
class TestProgressiveTier:
    """Unit tests for ProgressiveTier."""

    async def test_get_async_reads_from_correct_location(self):
        """Get reads dataframe.parquet from project directory."""

    async def test_get_async_parses_key_format(self):
        """Get correctly parses entity_type:project_gid key."""

    async def test_get_async_returns_none_on_missing(self):
        """Get returns None when dataframe.parquet doesn't exist."""

    async def test_get_async_handles_missing_watermark(self):
        """Get uses fallback watermark when watermark.json missing."""

    async def test_get_async_handles_corrupted_parquet(self):
        """Get returns None on parquet parse error."""

    async def test_put_async_delegates_to_persistence(self):
        """Put calls write_final_artifacts_async correctly."""

    async def test_put_async_returns_false_on_error(self):
        """Put returns False when S3 write fails."""

    async def test_exists_async_checks_dataframe_file(self):
        """Exists checks for dataframe.parquet presence."""

    async def test_delete_async_removes_artifacts(self):
        """Delete removes dataframe and watermark files."""

    def test_stats_tracking(self):
        """Stats correctly track reads, writes, errors."""

    def test_key_parsing_valid(self):
        """Key parsing handles valid formats."""

    def test_key_parsing_invalid(self):
        """Key parsing raises on invalid formats."""
```

### 10.2 Integration Tests

**Location**: `tests/integration/test_progressive_cache_e2e.py`

```python
class TestProgressiveCacheIntegration:
    """End-to-end tests for unified cache."""

    async def test_cache_miss_triggers_build_to_correct_location(self):
        """Verify cache miss -> build -> subsequent hit."""

    async def test_cache_warmer_writes_readable_by_query(self):
        """Verify warmer writes are readable by DataFrameCache."""

    async def test_self_refresh_writes_readable_by_cache(self):
        """Verify self-refresh writes are readable (bug fix verification)."""

    async def test_resume_capability_preserved(self):
        """Verify manifest-based resume still works."""
```

### 10.3 Tests to Update

The following test files mock S3Tier and need updates:

| File | Change Required |
|------|-----------------|
| `tests/unit/cache/dataframe/test_s3_tier.py` | DELETE (S3Tier removed) |
| `tests/unit/cache/dataframe/test_dataframe_cache.py` | Update `s3_tier` -> `progressive_tier` mocks |
| `tests/integration/test_s3_persistence_e2e.py` | Update to test ProgressiveTier path |

### 10.4 Test Coverage Targets

| Component | Line Coverage | Branch Coverage |
|-----------|---------------|-----------------|
| ProgressiveTier | >= 90% | >= 85% |
| DataFrameCache (updated) | >= 90% | >= 85% |
| Factory (updated) | >= 80% | >= 75% |

---

## Implementation Phases

### Phase 1: ProgressiveTier Implementation (Day 1)

1. Create `src/autom8_asana/cache/dataframe/tiers/progressive.py`
2. Implement `get_async()` with parquet reading
3. Implement `put_async()` delegating to SectionPersistence
4. Implement `exists_async()`, `delete_async()`, `get_stats()`
5. Write unit tests

### Phase 2: DataFrameCache Integration (Day 1-2)

1. Update `dataframe_cache.py`: rename `s3_tier` -> `progressive_tier`
2. Update type hints and imports
3. Update `factory.py` initialization
4. Update `tiers/__init__.py` exports

### Phase 3: Test Updates (Day 2)

1. Delete `test_s3_tier.py`
2. Update `test_dataframe_cache.py` mocks
3. Create `test_progressive_tier.py`
4. Update integration tests

### Phase 4: S3Tier Removal (Day 2)

1. Delete `src/autom8_asana/cache/dataframe/tiers/s3.py`
2. Remove S3Tier imports from all files
3. Verify no remaining references

### Phase 5: Verification (Day 3)

1. Run full test suite
2. Deploy to staging
3. Verify cache warmer success
4. Verify query endpoints return data
5. Monitor for CACHE_NOT_WARMED errors

---

## Risk Assessment

### 12.1 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Parquet format incompatibility | Low | High | Use same polars version; test with production data |
| Watermark schema mismatch | Low | Medium | Fallback to current time on parse failure |
| S3 permission issues | Low | High | Test with production IAM roles before deploy |
| Memory pressure on large DataFrames | Medium | Medium | Streaming reads; same limits as S3Tier |
| Resume capability regression | Low | High | Explicit integration tests for resume |

### 12.2 Rollback Triggers

- CACHE_NOT_WARMED errors increase after deploy
- Latency regression > 50% on cache operations
- Memory exhaustion in Lambda
- Resume capability broken (manifest reads fail)

---

## ADRs

### ADR-001: Storage Key Structure

**Status**: Accepted

**Context**: Should the cache key structure be `{entity}/{project}/` or keep `{project}/` with entity in manifest?

**Decision**: Keep `{project}/` structure, entity type in watermark metadata.

**Rationale**:
- Maintains compatibility with existing SectionPersistence structure
- Avoids migration of existing data
- Entity type already tracked in manifest.json and watermark.json
- Simplifies key parsing (only project_gid needed from cache key)

**Consequences**:
- Single project directory contains data for one entity type (current behavior)
- Entity type must be extracted from cache key for CacheEntry construction
- Multiple entity types for same project would need separate directories (not current use case)

---

### ADR-002: Watermark Staleness Threshold

**Status**: Accepted

**Context**: Should watermark staleness threshold be configurable or hardcoded?

**Decision**: Use existing TTL-based staleness check (12-24 hours, configurable via `ttl_hours`).

**Rationale**:
- TTL staleness check already exists in DataFrameCache._is_valid()
- Watermark comparison is for freshness (has source data changed?)
- TTL handles age-based staleness (force refresh after N hours)
- No need for separate watermark staleness threshold

**Consequences**:
- Keep existing `ttl_hours` configuration
- Watermark in CacheEntry used for incremental comparison, not age staleness
- Consistent behavior with existing caching pattern

---

### ADR-003: Index Loading Strategy

**Status**: Accepted

**Context**: Should ProgressiveTier lazy-load index.json or always load with DataFrame?

**Decision**: Do not load index.json in ProgressiveTier.

**Rationale**:
- GidLookupIndex is built from DataFrame, not stored index.json
- index.json is written by ProgressiveProjectBuilder for external consumers
- DataFrameCache returns CacheEntry with DataFrame; index built on demand
- Loading index.json adds latency without benefit for cache operations

**Consequences**:
- ProgressiveTier.get_async() reads only dataframe.parquet and watermark.json
- DynamicIndex/GidLookupIndex built from DataFrame as needed
- index.json remains available for external tools that need it

---

## Success Criteria

| ID | Criterion | Verification Method |
|----|-----------|---------------------|
| SC-001 | `POST /v1/query/offer` returns data after cache warm | Integration test + manual verification |
| SC-002 | Self-refresh build makes data available to subsequent queries | Integration test simulating cache miss -> build -> query |
| SC-003 | CacheWarmer and self-refresh write to same S3 location | Verify S3 paths in logs |
| SC-004 | `S3Tier` class deleted from codebase | `git grep S3Tier` returns no results |
| SC-005 | `ProgressiveTier` class created with full test coverage | Coverage report >= 90% |
| SC-006 | All existing cache tests pass | `pytest tests/unit/cache/` green |
| SC-007 | Resume capability verified | Integration test for manifest-based resume |
| SC-008 | No duplicate DataFrame storage in S3 | S3 listing shows single location |

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD (source) | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-unified-progressive-cache.md` | Read |
| S3Tier (to delete) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/s3.py` | Read |
| SectionPersistence | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | Read |
| DataFrameCache | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py` | Read |
| Factory | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/factory.py` | Read |
| UniversalResolutionStrategy | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py` | Read |
| CacheWarmer | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/warmer.py` | Read |
| ProgressiveProjectBuilder | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py` | Read |
| S3Tier tests (to delete) | `/Users/tomtenuta/Code/autom8_asana/tests/unit/cache/dataframe/test_s3_tier.py` | Read |
| Tiers __init__ | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/__init__.py` | Read |
