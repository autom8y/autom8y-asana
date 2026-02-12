# ADR: DataFrame Cache Disposition -- Intentional Separation

**ADR ID**: ADR-DATAFRAME-CACHE-DISPOSITION
**Date**: 2026-02-05
**Status**: ACCEPTED
**Deciders**: Architect, Requirements Analyst
**PRD**: PRD-SDK-ALIGNMENT (Path 2)
**Task**: task-302

---

## Context

The autom8y platform provides a `TieredCacheProvider` in the `autom8y-cache` SDK package. autom8_asana has a domain-specific `DataFrameCache` subsystem that caches Polars DataFrames with tiered storage (Memory + S3 via `SectionPersistence`), request coalescing, per-project circuit breakers, watermark-based freshness, and SWR (stale-while-revalidate) background refresh.

During the SDK Alignment initiative (Initiative 3), we evaluated whether the `DataFrameCache` should converge with the SDK's `TieredCacheProvider`. Three options were analyzed in the PRD:

- **Option A**: Intentionally Separate -- Keep `DataFrameCache` as a domain subsystem, document the boundary
- **Option B**: Converge via Adapter -- Make `DataFrameCache` implement the `CacheProvider` protocol
- **Option C**: Full Convergence -- Migrate entirely to `TieredCacheProvider`

The evaluation surfaced five fundamental impedance mismatches between the systems:

### 1. Data Format Impedance

The SDK's `CacheProvider` protocol (line 86 of `autom8y-cache/protocols/cache.py`) operates on `dict[str, Any]`:

```python
def get(self, key: str) -> dict[str, Any] | None
def set(self, key: str, data: dict[str, Any], ...) -> None
```

The `DataFrameCache` stores `pl.DataFrame` objects with `estimated_size()` for heap-based memory management (line 267 of `memory.py`). Converting DataFrames to dicts for SDK storage and back would lose:
- Schema type information (Polars dtypes)
- Memory size estimation (critical for `MemoryTier` eviction)
- Watermark semantics (entity-aware freshness, not just TTL)

### 2. Async/Sync Impedance

The SDK `CacheProvider` protocol is entirely synchronous (`get()`, `set()`, `delete()`). The `DataFrameCache`'s `ProgressiveTier` is entirely async (`get_async`, `put_async` -- lines 105, 206 of `progressive.py`) because S3 I/O benefits from async execution. Wrapping async in sync would defeat the purpose of async I/O for S3 cold-tier operations.

### 3. Build Coordination Has No SDK Analog

The `DataFrameCache` coordinates multi-page section fetches via `DataFrameCacheCoalescer` (request deduplication) and `CircuitBreaker` (per-project failure isolation). When multiple concurrent API requests need the same DataFrame, only one build runs while others await. The SDK has no concept of "building" a cache entry from multiple upstream API calls.

### 4. Invalidation Semantics Differ

The `DataFrameCache` invalidates by `entity_type + project_gid + schema_version` (lines 573-636 of `dataframe_cache.py`). It supports section-level invalidation, schema version bumps, and watermark-based freshness. The SDK invalidates by flat key + entry type. These are fundamentally different invalidation models.

### 5. S3 Key Structure Is Domain-Specific

The `ProgressiveTier` uses `SectionPersistence` which reads/writes to a domain-specific S3 key structure (`dataframes/{project_gid}/`) with watermark files, manifest files, and section-level granularity. The SDK's S3 backend uses a generic key-value structure. The key spaces are incompatible.

---

## Decision

**The autom8_asana `DataFrameCache` remains intentionally separate from the SDK's `TieredCacheProvider`.** The two systems serve different purposes:

- **SDK `TieredCacheProvider`**: Generic key-value caching with dict serialization, hot/cold tiering, and version-based freshness. Appropriate for JSON-serializable domain objects.
- **autom8_asana `DataFrameCache`**: Domain-specific DataFrame caching with Polars binary storage, build coordination, per-project circuit breaking, and entity-aware freshness. Purpose-built for the entity resolution pipeline.

The existing integration surface is correct and sufficient:

| Caching Concern | Mechanism | Status |
|-----------------|-----------|--------|
| **Task staleness checks** (key-value) | `autom8_adapter.py` -> `RedisCacheProvider` | Already uses SDK-compatible patterns |
| **Task metadata** (key-value) | `autom8_adapter.py` -> Redis | Already uses SDK-compatible patterns |
| **Entity DataFrames** (domain-specific) | `DataFrameCache` -> Memory + Progressive S3 | Intentionally separate |

---

## Consequences

### Positive

1. **No migration risk.** The DataFrame cache subsystem has extensive LocalStack S3 integration tests (`ProgressiveTier`, `SectionPersistence`, checkpoint resume). No tests need rewriting.

2. **Clean domain boundary.** The separation makes the architecture self-documenting: key-value caching flows through SDK patterns, domain DataFrame caching stays in the domain layer.

3. **Independent evolution.** The SDK's `TieredCacheProvider` and the `DataFrameCache` can evolve independently. Neither is constrained by the other's protocol.

4. **Zero effort.** This is a documentation-only deliverable. No code changes, no test changes, no deployment risk.

### Negative

1. **No unified observability.** The SDK's `CacheMetrics` does not cover DataFrame cache operations. However, the `DataFrameCache` already has its own per-entity-type statistics (`get_stats()` at line 711 of `dataframe_cache.py`) and the `ProgressiveTier` tracks reads/writes/errors/bytes independently (lines 335-342 of `progressive.py`). The observability gap is addressed separately in Path 3 (Prometheus domain metrics).

2. **Two caching mental models.** Engineers working on autom8_asana must understand both the SDK cache (for key-value) and the domain cache (for DataFrames). The `autom8_adapter.py` module serves as the bridge and documentation of the boundary.

3. **Potential future duplication.** If other satellites develop similar DataFrame caching needs, the pattern would be re-implemented rather than shared. This is acceptable because domain-specific caching is inherently domain-specific.

### Neutral

1. **`autom8_adapter.py` continues as the integration surface.** The `create_autom8_cache_provider()` function already provides SDK-compatible Redis cache access for key-value data. This adapter does not need to grow to cover DataFrames.

---

## Alternatives Considered

### Option B: Converge via Adapter (REJECTED)

Make `DataFrameCache` implement the `CacheProvider` protocol, gaining SDK `CacheMetrics` integration.

**Why rejected**: The adapter would need to:
- Serialize `pl.DataFrame` to `dict[str, Any]` for `get()`, losing type safety and memory estimation
- Wrap async operations in sync, defeating async I/O benefits
- Fake versioned operations (`get_versioned`, `set_versioned`) that do not map to watermark-based freshness

The impedance mismatch would create a leaky abstraction. Estimated effort: 2-3 days with ongoing maintenance burden. The observability benefit (SDK `CacheMetrics`) is addressed more cleanly by Path 3 Prometheus metrics.

### Option C: Full Convergence (REJECTED -- NOT VIABLE)

Migrate entirely to `TieredCacheProvider` with a custom serializer.

**Why rejected**: Not technically viable.
- `TieredCacheProvider` stores `dict[str, Any]`. Polars DataFrames cannot be losslessly round-tripped through JSON.
- `CacheEntry.data: dict[str, Any]` versus `DataFrameCacheEntry.dataframe: pl.DataFrame` -- fundamentally different shapes.
- Build coordination, request coalescing, and per-project circuit breaking would all need reimplementation outside the SDK.
- All DataFrame cache tests (unit and integration) would need rewriting.

Estimated effort: 2+ weeks with high regression risk. The cost-benefit is strongly negative.

---

## Revisit Triggers

Revisit this decision if the SDK adds any of the following capabilities:

| Trigger | What It Enables | Likelihood |
|---------|----------------|------------|
| **`SerializerProtocol`** supporting pluggable binary serialization | DataFrame-aware cache entries without dict conversion | Medium (requires SDK design decision) |
| **Async `CacheProvider` variant** | Eliminates sync/async impedance for S3 cold tier | Medium (requested by multiple consumers) |
| **Build coordination / request coalescing** as SDK-level utilities | Eliminates the primary reason DataFrameCache exists as a separate subsystem | Low (highly domain-specific) |
| **Section-aware invalidation strategies** | Eliminates custom invalidation logic | Low (very domain-specific) |

If all four triggers are satisfied simultaneously, full convergence becomes viable. Until then, the separation is the correct architectural choice.

---

## Related Documents

| Document | Path |
|----------|------|
| PRD-SDK-ALIGNMENT (Path 2 analysis) | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-SDK-ALIGNMENT.md` |
| TDD-SDK-ALIGNMENT | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-SDK-ALIGNMENT.md` |
| SDK Adoption Gap Inventory (Section 7) | `/Users/tomtenuta/Code/autom8y/docs/requirements/SDK-ADOPTION-GAP-INVENTORY.md` |
| DataFrameCache implementation | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/dataframe_cache.py` |
| autom8_adapter.py (integration surface) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/autom8_adapter.py` |
| SDK CacheProvider protocol | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/protocols/cache.py` |
| SDK TieredCacheProvider | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/tiered.py` |
| MemoryTier | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/memory.py` |
| ProgressiveTier | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/progressive.py` |
