# PRD: Unified Progressive DataFrame Cache Architecture

## Metadata

| Field | Value |
|-------|-------|
| **PRD ID** | PRD-unified-progressive-cache |
| **Status** | Draft |
| **Created** | 2026-01-16 |
| **Author** | Requirements Analyst |
| **Impact** | high |
| **Impact Categories** | data_model, cross_service |

---

## Executive Summary

This PRD defines requirements for unifying two parallel S3 caching systems that evolved accidentally, creating storage duplication and a critical bug where self-refresh writes and query reads target different S3 locations.

**The Fix**: Delete S3Tier entirely. Replace it with a new ProgressiveTier that reads from the existing SectionPersistence storage structure.

---

## Problem Statement

### Root Cause Analysis

Two parallel S3 caching mechanisms evolved independently:

| System | Storage Location | Purpose | Features |
|--------|------------------|---------|----------|
| **SectionPersistence** | `dataframes/{project_gid}/` | Progressive cache warming | Resume capability, incremental refresh, manifest tracking, section-level persistence |
| **S3Tier** | `asana-cache/dataframes/{entity}:{project}.parquet` | Query-time cache reads | Simple flat file, TTL-based staleness, no resume |

### The Bug

When `EntityQueryService.query()` encounters a cache miss:

1. `UniversalResolutionStrategy._get_dataframe()` is called
2. On DataFrameCache miss, triggers build via `legacy_strategy.resolve()`
3. Build uses `ProgressiveProjectBuilder` which writes to **SectionPersistence location** (`dataframes/{project_gid}/dataframe.parquet`)
4. Build completes successfully
5. `DataFrameCache.get_async()` checks **S3Tier location** (`dataframes/{entity}:{project}.parquet`)
6. S3Tier returns miss (data is in different location)
7. Query returns `CACHE_NOT_WARMED` error despite fresh data existing in S3

**Consequence**: `/v1/query/offer` returns 503 `CACHE_NOT_WARMED` even after successful self-refresh build, because the two systems use incompatible storage locations.

### Code Flow Trace

```
EntityQueryService.query()
  └─> UniversalResolutionStrategy._get_dataframe()
        ├─> Check DataFrameCache.get_async() [reads from S3Tier @ {entity}:{project}.parquet]
        │     └─> MISS (even if data exists elsewhere)
        └─> Trigger legacy_strategy.resolve() [cache miss path]
              └─> ProgressiveProjectBuilder.build_with_parallel_fetch_async()
                    └─> SectionPersistence.write_final_artifacts_async()
                          └─> WRITES to dataframes/{project_gid}/dataframe.parquet
                          └─> DataFrameCache.put_async() NOT CALLED on this path
```

### Current Storage Layout

**SectionPersistence (The Good System)**:
```
s3://bucket/
  dataframes/
    {project_gid}/
      manifest.json       # Build state, schema version
      dataframe.parquet   # Final merged DataFrame
      watermark.json      # Freshness tracking
      index.json          # GidLookupIndex
      sections/           # Resume artifacts
        {section_gid}.parquet
```

**S3Tier (The Redundant System)**:
```
s3://bucket/
  asana-cache/
    dataframes/
      {entity}:{project}.parquet  # Flat file with metadata
```

---

## User Stories

### US-001: Consistent Cache Access

**As a** query service consumer
**I want** cache reads and writes to use the same storage location
**So that** self-refresh builds are immediately available to queries

**Acceptance Criteria**:
- [ ] Self-refresh writes via ProgressiveProjectBuilder are readable by DataFrameCache
- [ ] Cache warmer writes via CacheWarmer are readable by DataFrameCache
- [ ] Both paths write to identical S3 location
- [ ] No CACHE_NOT_WARMED errors after successful builds

### US-002: Resume Capability Preserved

**As a** system operator
**I want** the ability to resume interrupted cache warming operations
**So that** Lambda restarts don't require full rebuilds

**Acceptance Criteria**:
- [ ] Manifest-based resume continues to work
- [ ] Section-level persistence preserved
- [ ] Schema version compatibility checking preserved
- [ ] Incremental refresh with watermark filtering preserved

### US-003: Single Source of Truth

**As a** developer maintaining the caching system
**I want** a single storage system for DataFrames
**So that** I don't have to maintain two parallel implementations

**Acceptance Criteria**:
- [ ] S3Tier class deleted from codebase
- [ ] All cache reads flow through ProgressiveTier
- [ ] No redundant storage locations
- [ ] Clear ownership of cache storage pattern

---

## Functional Requirements

### Must Have

#### FR-001: Delete S3Tier

The system shall remove the `S3Tier` class (`cache/dataframe/tiers/s3.py`) entirely.

**Rationale**: S3Tier duplicates functionality provided by SectionPersistence with an incompatible storage layout. Its continued existence causes the location mismatch bug.

#### FR-002: Create ProgressiveTier

The system shall create a new `ProgressiveTier` class that:

1. Reads from the SectionPersistence storage structure (`dataframes/{project_gid}/`)
2. Implements the same async interface as the former S3Tier:
   - `get_async(key: str) -> CacheEntry | None`
   - `put_async(key: str, entry: CacheEntry) -> bool`
   - `exists_async(key: str) -> bool`
   - `delete_async(key: str) -> bool`
3. Translates cache keys (`{entity_type}:{project_gid}`) to S3 paths (`dataframes/{project_gid}/`)

**Storage Structure Read by ProgressiveTier**:
```
dataframes/{project_gid}/
  dataframe.parquet   # Final DataFrame (ProgressiveTier reads this)
  watermark.json      # Metadata (watermark, row_count, schema_version)
  manifest.json       # Build state (for resume capability)
```

#### FR-003: Update DataFrameCache Composition

The system shall update `DataFrameCache` initialization to use `ProgressiveTier` instead of `S3Tier`:

```python
# Before
DataFrameCache(
    memory_tier=MemoryTier(...),
    s3_tier=S3Tier(bucket=..., prefix="dataframes/"),  # Wrong prefix!
    ...
)

# After
DataFrameCache(
    memory_tier=MemoryTier(...),
    progressive_tier=ProgressiveTier(persistence=SectionPersistence(...)),
    ...
)
```

#### FR-004: ProgressiveTier Write Delegation

When `ProgressiveTier.put_async()` is called:

1. Serialize DataFrame to parquet bytes
2. Write to `dataframes/{project_gid}/dataframe.parquet` via SectionPersistence
3. Write watermark metadata to `dataframes/{project_gid}/watermark.json`
4. Return success/failure

**Note**: ProgressiveTier writes use the same format as ProgressiveProjectBuilder, ensuring compatibility.

#### FR-005: ProgressiveTier Read Logic

When `ProgressiveTier.get_async()` is called:

1. Parse cache key to extract project_gid: `{entity_type}:{project_gid}` -> `project_gid`
2. Read `dataframes/{project_gid}/dataframe.parquet`
3. Read `dataframes/{project_gid}/watermark.json` for metadata
4. Construct and return `CacheEntry` with DataFrame and metadata
5. Return `None` if files don't exist

#### FR-006: CacheWarmer Uses Consistent Path

The `CacheWarmer._warm_entity_type_async()` method shall write via `DataFrameCache.put_async()` which now uses ProgressiveTier, ensuring cache warmer and self-refresh use identical storage.

**Current (Broken)**:
```
CacheWarmer -> strategy._build_dataframe() -> ProgressiveProjectBuilder -> SectionPersistence
            -> cache.put_async() -> S3Tier (DIFFERENT LOCATION!)
```

**After Fix**:
```
CacheWarmer -> strategy._build_dataframe() -> ProgressiveProjectBuilder -> SectionPersistence
            -> cache.put_async() -> ProgressiveTier -> SectionPersistence (SAME!)
```

#### FR-007: Query Service Self-Refresh Writes to Cache

After `UniversalResolutionStrategy._get_dataframe()` builds a fresh DataFrame, it shall:

1. Write to DataFrameCache via `cache.put_async()` (which uses ProgressiveTier)
2. Subsequent reads find the data at the same location

**Note**: The existing self-refresh path already calls `ProgressiveProjectBuilder.write_final_artifacts_async()`. The fix ensures DataFrameCache reads from the same location.

### Should Have

#### FR-008: Statistics and Observability

`ProgressiveTier` shall maintain statistics consistent with the former S3Tier:
- `reads`: Total read attempts
- `writes`: Total write attempts
- `read_errors`: Failed reads
- `write_errors`: Failed writes
- `bytes_read`: Total bytes read
- `bytes_written`: Total bytes written
- `not_found`: Cache misses

#### FR-009: Graceful Degradation

If SectionPersistence operations fail (S3 unavailable), ProgressiveTier shall:
- Return `None` from `get_async()` (allowing memory tier to serve if populated)
- Return `False` from `put_async()` (allowing graceful degradation)
- Log warning with S3 error details
- Not raise exceptions to caller

### Could Have

#### FR-010: Legacy Location Migration

Optionally, the system could migrate existing data from the S3Tier location (`dataframes/{entity}:{project}.parquet`) to the ProgressiveTier location (`dataframes/{project_gid}/`).

**Deferred**: Migration is out of scope for this PRD. Stale data in the old location will naturally expire or be ignored.

#### FR-011: Watermark Validation on Read

ProgressiveTier could validate that `watermark.json` schema_version matches current SchemaRegistry version before returning data.

**Deferred**: Let DataFrameCache._is_valid() handle schema validation as it does today.

---

## Non-Functional Requirements

### NFR-001: Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Read latency (S3 cache hit) | < 500ms | Comparable to former S3Tier |
| Write latency | < 1000ms | Acceptable for build completion |
| Memory overhead | No increase | Streaming parquet reads |
| API call overhead | 0 additional | No Asana API calls for cache ops |

### NFR-002: Reliability

| Metric | Target |
|--------|--------|
| Cache consistency | 100% | Reads find writes immediately |
| Resume capability | 100% | Existing manifests continue to work |
| Build idempotency | 100% | Repeated builds produce same result |

### NFR-003: Storage

| Metric | Target |
|--------|--------|
| Storage reduction | ~50% | Eliminating duplicate S3 location |
| S3 key format | `dataframes/{project_gid}/*` | Single consistent pattern |

### NFR-004: Observability

Structured logging with:
- `progressive_tier_read`: Read attempts with timing
- `progressive_tier_write`: Write attempts with timing
- `progressive_tier_miss`: Cache misses
- `progressive_tier_error`: S3 errors with details

---

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Read before any write | Return `None` (cache miss) |
| Concurrent reads | Both succeed (S3 supports concurrent reads) |
| Concurrent writes | Last writer wins (acceptable for cache) |
| Partial write failure | Return `False`, subsequent read returns stale or `None` |
| Missing watermark.json | Read dataframe.parquet, use current time as watermark |
| Corrupted parquet file | Return `None`, log error, allow rebuild |
| S3 unavailable | Return `None`/`False`, rely on memory tier |
| Schema version mismatch | DataFrameCache._is_valid() handles invalidation |
| Entity type not in key | Parse error, return `None`, log warning |

---

## Success Criteria

- [ ] **SC-001**: `POST /v1/query/offer` returns data after cache warm (no CACHE_NOT_WARMED)
- [ ] **SC-002**: Self-refresh build makes data available to subsequent queries
- [ ] **SC-003**: CacheWarmer and self-refresh write to same S3 location
- [ ] **SC-004**: `S3Tier` class deleted from codebase
- [ ] **SC-005**: `ProgressiveTier` class created with full test coverage
- [ ] **SC-006**: All existing cache tests pass (test suite green)
- [ ] **SC-007**: Resume capability verified (manifest-based resume works)
- [ ] **SC-008**: No duplicate DataFrame storage in S3

---

## Out of Scope

| Item | Rationale |
|------|-----------|
| Migration of old S3Tier data | Stale data will naturally expire; migration adds complexity |
| Backwards compatibility with S3Tier format | Clean break preferred over maintaining two formats |
| Preserving S3Tier class interface exactly | ProgressiveTier may have simplified interface |
| Multi-region S3 replication | Existing single-region pattern sufficient |
| Real-time cache invalidation | Existing TTL/schema-version pattern sufficient |

---

## Open Questions

*All questions resolved - ready for Architecture handoff.*

1. ~~Should ProgressiveTier maintain its own watermark or read from SectionPersistence?~~ **Resolved**: Read from `watermark.json` written by SectionPersistence to avoid duplication.

2. ~~Should we support both storage locations during migration?~~ **Resolved**: No, clean break preferred. Old location data will be ignored.

3. ~~What happens to existing tests that mock S3Tier?~~ **Resolved**: Update tests to mock ProgressiveTier with same interface.

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| SectionPersistence | Implemented | `dataframes/section_persistence.py` |
| DataFrameCache | Implemented | `cache/dataframe_cache.py` |
| ProgressiveProjectBuilder | Implemented | `dataframes/builders/progressive.py` |
| CacheWarmer | Implemented | `cache/dataframe/warmer.py` |
| EntityQueryService | Implemented | `services/query_service.py` |
| UniversalResolutionStrategy | Implemented | `services/universal_strategy.py` |

---

## Appendix A: Storage Location Comparison

### Before (Two Locations)

```
s3://bucket/
  asana-cache/
    dataframes/
      unit:1234567890.parquet      # S3Tier writes here
      offer:9876543210.parquet     # DataFrameCache reads from here
  dataframes/
    1234567890/                    # SectionPersistence writes here
      manifest.json
      dataframe.parquet            # ProgressiveProjectBuilder writes here
      watermark.json
      sections/
        section1.parquet
    9876543210/
      manifest.json
      dataframe.parquet
      watermark.json
```

### After (Single Location)

```
s3://bucket/
  dataframes/
    1234567890/                    # ALL writes go here
      manifest.json
      dataframe.parquet            # ProgressiveTier reads/writes
      watermark.json               # ProgressiveTier reads metadata
      index.json
      sections/
        section1.parquet
    9876543210/
      manifest.json
      dataframe.parquet
      watermark.json
```

---

## Appendix B: Key File Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `cache/dataframe/tiers/s3.py` | DELETE | Remove S3Tier class |
| `cache/dataframe/tiers/progressive.py` | CREATE | New ProgressiveTier class |
| `cache/dataframe/tiers/__init__.py` | MODIFY | Export ProgressiveTier |
| `cache/dataframe_cache.py` | MODIFY | Replace S3Tier with ProgressiveTier |
| `cache/dataframe/factory.py` | MODIFY | Update cache initialization |
| `services/universal_strategy.py` | NO CHANGE | Reads via DataFrameCache unchanged |
| `services/query_service.py` | NO CHANGE | Reads via strategy unchanged |
| `dataframes/section_persistence.py` | NO CHANGE | Continue as storage layer |
| `dataframes/builders/progressive.py` | NO CHANGE | Continue using SectionPersistence |

---

## Appendix C: ProgressiveTier Interface

```python
@dataclass
class ProgressiveTier:
    """S3 tier using SectionPersistence storage structure.

    Replaces S3Tier to use the same storage location as
    ProgressiveProjectBuilder, eliminating the dual-location bug.

    Key format translation:
      "{entity_type}:{project_gid}" -> "dataframes/{project_gid}/"
    """

    persistence: SectionPersistence

    async def get_async(self, key: str) -> CacheEntry | None:
        """Get entry from progressive storage location."""
        ...

    async def put_async(self, key: str, entry: CacheEntry) -> bool:
        """Store entry to progressive storage location."""
        ...

    async def exists_async(self, key: str) -> bool:
        """Check if entry exists."""
        ...

    async def delete_async(self, key: str) -> bool:
        """Delete entry."""
        ...

    def get_stats(self) -> dict[str, int]:
        """Get tier statistics."""
        ...
```

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| S3Tier (to delete) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/s3.py` | Read |
| SectionPersistence | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | Read |
| DataFrameCache | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py` | Read |
| UniversalResolutionStrategy | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py` | Read |
| CacheWarmer | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/warmer.py` | Read |
| QueryService | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py` | Read |
| ProgressiveProjectBuilder | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py` | Read |
