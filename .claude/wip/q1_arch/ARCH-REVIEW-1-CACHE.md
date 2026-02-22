# Architectural Review 1: Cache Topology

**Date**: 2026-02-18
**Scope**: Comprehensive cache subsystem analysis (~15,658 LOC in `cache/`, plus ~13,728 LOC DataFrame cache integration)
**Methodology**: Exploration agents 6-10 (cache layer, DataFrame cache, client TTL, warming, query/S3) + synthesis
**Review ID**: ARCH-REVIEW-1

---

## 1. Provider Hierarchy

### CacheProvider Protocol

**Source**: `src/autom8_asana/protocols/cache.py`

The `CacheProvider` protocol defines the cache abstraction boundary. All cache implementations conform to this protocol.

```
CacheProvider (Protocol)
    |
    +-- NullCacheProvider       # No-op (testing, disabled cache)
    +-- InMemoryCacheProvider   # Dict-based (testing, dev)
    +-- RedisCacheProvider      # Redis backend (production hot tier)
    +-- S3CacheProvider         # S3 backend (production cold tier)
    +-- TieredCacheProvider     # Coordinates Redis (hot) + S3 (cold)
```

**Source files**:
- `src/autom8_asana/cache/backends/base.py` -- Base provider
- `src/autom8_asana/cache/backends/memory.py` -- InMemory
- `src/autom8_asana/cache/backends/redis.py` -- Redis
- `src/autom8_asana/cache/backends/s3.py` -- S3
- `src/autom8_asana/cache/providers/tiered.py` -- Tiered (Redis+S3)
- `src/autom8_asana/cache/providers/unified.py` -- Unified provider

### Provider Selection

| Environment | Provider | Tiers |
|------------|----------|-------|
| Production (ECS) | `TieredCacheProvider` | Redis (hot) + S3 (cold) |
| Production (Lambda) | `TieredCacheProvider` | Redis (hot) + S3 (cold) |
| Development | `InMemoryCacheProvider` | Single tier |
| Testing | `NullCacheProvider` | No-op |

---

## 2. Entity Cache (Redis/S3 Tier)

### EntryType Enumeration

**Source**: `src/autom8_asana/cache/models/entry.py`

14 cacheable entry types:

| EntryType | Description | Cache Layer |
|-----------|-------------|-------------|
| `TASK_RAW` | Raw Asana task JSON | Entity |
| `TASK_PROCESSED` | Processed task with custom fields | Entity |
| `ENTITY_DETECTED` | Detection result | Entity |
| `ENTITY_HYDRATED` | Fully hydrated entity | Entity |
| `RELATIONSHIP` | Parent-child relationships | Entity |
| `DETECTION_CACHE` | Detection tier results | Entity |
| `PROJECT_TASKS` | Task GID list per project | Entity |
| `SECTION_TASKS` | Task GID list per section | Entity |
| `STORIES` | Task story/comment data | Entity |
| `MODIFICATION_TS` | Last modification timestamps | Entity |
| `BATCH_RESULT` | Batch API results | Entity |
| `INSIGHTS_RESULT` | Insights API results | Entity |
| `DATAFRAME_META` | DataFrame metadata | DataFrame |
| `CUSTOM_FIELDS` | Custom field definitions | Entity |

### Entity-Type-Specific TTLs

Per ADR-0119, TTLs are calibrated to entity volatility:

| Entity Type | TTL | Rationale |
|-------------|-----|-----------|
| Process | 1 minute | High-churn pipeline entities |
| Offer | 5 minutes | Moderate activity state changes |
| Contact | 15 minutes | Relatively stable |
| Unit | 15 minutes | Moderate stability |
| Business | 1 hour | Very stable root entity |
| Holders | 30 minutes | Container stability |
| Detection results | 1 hour | Structural, rarely changes |
| Relationships | 30 minutes | Parent-child links |

### Key Namespacing

Cache keys follow a structured namespace:

```
{prefix}:{workspace_gid}:{entry_type}:{entity_gid}
```

Example: `autom8:12345:task_raw:67890`

This enables per-workspace isolation and per-entry-type TTL management.

### 6-Step Read Pattern (ADR-0119)

Entity cache reads follow a 6-step resolution:

```
1. Check hot tier (Redis)
   |-- HIT: Return entry, check freshness
   |-- MISS: Continue to step 2
   |
2. Check cold tier (S3)
   |-- HIT: Promote to hot tier, return entry
   |-- MISS: Continue to step 3
   |
3. Fetch from Asana API
   |-- SUCCESS: Continue to step 4
   |-- FAILURE: Return degraded/error
   |
4. Process and validate
   |
5. Write to hot tier (Redis)
   |
6. Write-through to cold tier (S3)
   |
   Return entry
```

### Cache Entry Model

**Source**: `src/autom8_asana/cache/models/entry.py`

```
CacheEntry (base)
    |
    +-- EntityCacheEntry      # Entity data with type-specific TTL
    +-- DetectionCacheEntry   # Detection results with confidence
    +-- RelationshipCacheEntry  # Parent-child links
    +-- DataFrameMetaCacheEntry  # DataFrame metadata
```

Each entry carries version metadata for staleness detection.

---

## 3. DataFrame Cache (Memory + Progressive/S3 Tier)

### Two-Tier Architecture

The DataFrame cache operates independently from the entity cache:

```
DataFrame Cache
    |
    +-- MemoryTier (LRU)
    |     +-- Container-aware sizing
    |     +-- LRU eviction policy
    |     +-- Per-section cached DataFrames
    |
    +-- ProgressiveTier (S3)
          +-- S3 Parquet storage
          +-- Section-level granularity
          +-- SectionManifest checkpoint resume
```

### MemoryTier

- **LRU eviction**: Least-recently-used cache eviction
- **Container-aware sizing**: Detects ECS container memory limits and sizes cache accordingly
- **Per-section granularity**: Each section's DataFrame cached independently
- **Thread-safe**: Concurrent access via locking

### ProgressiveTier (S3)

- **Parquet format**: DataFrames stored as Parquet files in S3
- **Section-level persistence**: Each section persisted independently
- **SectionManifest**: Tracks which sections have been successfully built and persisted
- **Checkpoint-resume**: Lambda warmer can resume from last successful section

### 6 Freshness States

The DataFrame cache recognizes 6 distinct freshness states for cached data:

| State | Meaning | Action |
|-------|---------|--------|
| FRESH | Within TTL, not modified | Serve directly |
| STALE_SERVABLE | Past TTL, but servable | Serve + trigger background refresh |
| STALE_REFRESHING | Being refreshed in background | Serve stale while refreshing |
| EXPIRED | Past max-stale window | Must refresh before serving |
| MISSING | Not in cache | Must build from source |
| ERROR | Cache read failed | Fall back to source or degrade |

### Stale-While-Revalidate (SWR) Implementation

The DataFrame cache implements SWR semantics:

1. If entry is FRESH: serve directly
2. If entry is STALE_SERVABLE: serve stale data immediately, trigger background revalidation
3. If entry is EXPIRED or MISSING: block on fresh build
4. If revalidation succeeds: promote new data to cache
5. If revalidation fails: extend stale TTL (degraded mode)

This ensures consumers always get data (possibly stale) while fresh data is prepared.

---

## 4. Invalidation Paths

### TTL-Based (Passive)

Every cache entry has a type-specific TTL. Expired entries are evicted on read (lazy expiration) or by Redis TTL mechanisms.

### MutationInvalidator (Fire-and-Forget)

When the SDK mutates data through the Asana API (e.g., `tasks.update_async`), the `MutationInvalidator` fires invalidation for affected cache entries. This is fire-and-forget -- invalidation failures are logged but do not block the mutation.

### CacheInvalidator on SaveSession Commit

**Source**: `src/autom8_asana/persistence/session.py`

When `SaveSession.commit_async()` executes:
1. CRUD operations execute against Asana API
2. `CacheInvalidator` invalidates affected entries in both hot and cold tiers
3. Cascade operations may trigger additional invalidations
4. Automation rules fire after commit (may create new entities)

### The Client Mutation Gap

**Critical finding**: When external clients (not going through the SDK) mutate data directly in Asana, no invalidation occurs. The only protection is TTL expiration. This means:

- Data modified directly in Asana UI may be stale for up to the entity's TTL
- Business entities (1h TTL) could be stale for up to 1 hour after direct modification
- Process entities (1m TTL) recover quickly
- No webhook or event-driven invalidation from Asana API changes

This is a known architectural trade-off: the system assumes most mutations flow through the SDK.

---

## 5. Cache Warming

### Lambda Warmer

**Source**: `src/autom8_asana/lambda_handlers/cache_warmer.py`

The Lambda cache warmer pre-populates caches on a schedule:

**Priority order**:
1. Entity cache (Redis/S3) -- most critical for API response times
2. DataFrame cache (Memory/S3) -- needed for query operations
3. Hierarchy cache -- entity relationship tree

**Features**:
- **Checkpoint resume**: Uses `SectionManifest` to resume from last successful point
- **Timeout self-continuation**: When Lambda approaches timeout limit, triggers a continuation invocation with checkpoint state
- **Priority-ordered warming**: Warms highest-value entities first
- **Per-project isolation**: Each project warmed independently

### Hierarchy Warmer

A specialized warmer that builds the entity hierarchy tree (Business -> Units -> Contacts/Offers/Processes) for each project, ensuring relationship caches are populated.

### APScheduler (Dev Mode)

In development (ECS), cache warming runs via APScheduler as periodic background tasks rather than Lambda invocations.

---

## 6. Watermark System

### Schema

**Source**: `src/autom8_asana/dataframes/watermark.py`

```python
class WatermarkRepository:
    """Thread-safe watermark management for incremental sync."""

    _watermarks: dict[str, datetime]  # project_gid -> last_sync_timestamp
    _lock: threading.Lock
    _storage: DataFrameStorage | None  # Optional S3 persistence
```

### Lifecycle

1. **Startup**: `load_from_persistence()` hydrates watermarks from S3
2. **Sync**: `get_watermark(project_gid)` returns last sync timestamp
3. **Query**: Use watermark as `modified_since` parameter for Asana API
4. **Update**: `set_watermark(project_gid, timestamp)` persists write-through to S3
5. **Full sync**: `None` watermark triggers full data fetch

### Comparison

When deciding whether to do a full or incremental sync:

```
watermark = repo.get_watermark(project_gid)
if watermark is None:
    # Full sync (first time or reset)
    tasks = await client.tasks.get_all_async(project_gid)
else:
    # Incremental sync (only modified tasks)
    tasks = await client.tasks.get_all_async(
        project_gid, modified_since=watermark.isoformat()
    )
```

---

## 7. S3 Retry and Circuit Breaker

### S3 Retry Configuration

S3 operations use retry policies for transient failures:

- **Retryable errors**: Defined in `CACHE_TRANSIENT_ERRORS` (`src/autom8_asana/core/exceptions.py`)
- **S3-specific errors**: `S3_TRANSPORT_ERRORS` tuple
- **Max retries**: Configurable per operation type
- **Backoff**: Exponential backoff with jitter

### Circuit Breaker

Per-project circuit breakers protect against S3 outages:

- **State machine**: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
- **Open threshold**: Configurable failure count
- **Half-open probe**: Periodic test request to check recovery
- **Scope**: Per-project isolation prevents one project's S3 issues from affecting others

**Note**: Circuit breaker thread safety was flagged as a concern in the straw-man analysis (see STRAW-MAN document).

---

## 8. Completeness Tracking

### 4 Levels

**Source**: `src/autom8_asana/cache/models/completeness.py`

| Level | Fields | Use Case |
|-------|--------|----------|
| `MINIMAL` | `MINIMAL_FIELDS` | GID + name only, for listings |
| `STANDARD` | `STANDARD_FIELDS` | Common fields, for most operations |
| `FULL` | `FULL_FIELDS` | All fields including custom, for detailed views |
| `CUSTOM` | Dynamic | Caller-specified field set |

### Transparent Upgrade

When a cache entry is at `MINIMAL` completeness but the caller needs `STANDARD`:

1. Serve the MINIMAL data immediately (if acceptable)
2. Trigger background upgrade to STANDARD
3. Next read gets STANDARD data

This prevents repeated full fetches when partial data suffices temporarily.

### Completeness Metadata

```python
def create_completeness_metadata(
    level: CompletenessLevel,
    fields: frozenset[str],
) -> dict[str, Any]:
    """Create metadata dict for cache entry completeness tracking."""
```

Each cache entry carries completeness metadata enabling the upgrade path.

---

## 9. End-to-End Data Flow

```
                    +------------------+
                    |    Asana API     |
                    +--------+---------+
                             |
                    +--------v---------+
                    | AsanaClient      |
                    | (facade)         |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+        +----------v---------+
    | Entity Pipeline   |        | DataFrame Pipeline |
    +-------------------+        +--------------------+
    |                   |        |                    |
    | 1. Fetch raw      |        | 1. Fetch tasks     |
    | 2. Detect type    |        | 2. Extract rows    |
    | 3. Hydrate model  |        | 3. Build DataFrame |
    | 4. Cache (Redis)  |        | 4. Cache (Memory)  |
    | 5. Write-through  |        | 5. Persist (S3)    |
    |    (S3)           |        |                    |
    +--------+----------+        +--------+-----------+
             |                            |
    +--------v----------+        +--------v-----------+
    | Entity Cache      |        | DataFrame Cache    |
    +-------------------+        +--------------------+
    | Hot: Redis        |        | Hot: Memory (LRU)  |
    | Cold: S3          |        | Cold: S3 (Parquet) |
    | TTL: per-entity   |        | Freshness: 6-state |
    | Freshness: 3-mode |        | SWR semantics      |
    +--------+----------+        +--------+-----------+
             |                            |
             +------------+---------------+
                          |
                 +--------v---------+
                 | Query Engine     |
                 +------------------+
                 | Predicate AST    |
                 | -> Polars Expr   |
                 | Section scoping  |
                 | Cross-entity join|
                 +--------+---------+
                          |
                 +--------v---------+
                 | API / Automation |
                 +------------------+
                 | FastAPI routes   |
                 | Pipeline rules   |
                 | Lifecycle engine |
                 +--------+---------+
                          |
                 +--------v---------+
                 | SaveSession      |
                 +------------------+
                 | Phase-based UoW  |
                 | CRUD + cascades  |
                 | Invalidation     |
                 +------------------+
```

### Cache Read Sequence (Entity)

```
Client Request
    |
    v
QueryEngine / API Route
    |
    v
EntityCacheProvider.get()
    |
    +-- Redis HIT? --> check freshness --> serve
    |
    +-- Redis MISS --> S3 HIT? --> promote to Redis --> serve
    |
    +-- S3 MISS --> Asana API fetch --> detect --> hydrate
                          |
                          v
                    Write Redis (hot)
                    Write S3 (cold, write-through)
                          |
                          v
                    Return to caller
```

### Cache Read Sequence (DataFrame)

```
Query Request
    |
    v
DataFrameCacheIntegration.get()
    |
    +-- Memory HIT? --> check freshness state
    |     |
    |     +-- FRESH: serve
    |     +-- STALE_SERVABLE: serve + background refresh
    |     +-- EXPIRED: block on refresh
    |
    +-- Memory MISS --> S3 HIT? --> load Parquet --> promote to Memory --> serve
    |
    +-- S3 MISS --> build from entity data --> cache Memory --> persist S3 --> serve
```

---

## 10. Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `cache/__init__.py` | ~60 | Public API, ADR references |
| `cache/backends/base.py` | -- | Base provider |
| `cache/backends/redis.py` | -- | Redis backend |
| `cache/backends/s3.py` | -- | S3 backend |
| `cache/backends/memory.py` | -- | Memory backend |
| `cache/providers/tiered.py` | -- | TieredCacheProvider (ADR-0026) |
| `cache/providers/unified.py` | -- | Unified provider |
| `cache/models/entry.py` | -- | CacheEntry, EntryType (14 types) |
| `cache/models/freshness.py` | ~36 | Freshness enum (STRICT/EVENTUAL/IMMEDIATE) |
| `cache/models/completeness.py` | -- | CompletenessLevel (4 levels) |
| `cache/models/metrics.py` | -- | CacheMetrics aggregator |
| `cache/models/errors.py` | -- | DegradedModeMixin, error classification |
| `cache/policies/` | -- | Cache policies |
| `cache/integration/` | -- | Integration modules |
| `cache/dataframe/` | -- | DataFrame cache tier |
| `protocols/cache.py` | -- | CacheProvider protocol, WarmResult |
| `core/exceptions.py` | ~322 | S3_TRANSPORT_ERRORS, REDIS_TRANSPORT_ERRORS, CACHE_TRANSIENT_ERRORS, ASANA_API_ERRORS |
| `dataframes/cache_integration.py` | -- | DataFrameCacheIntegration |
| `dataframes/section_persistence.py` | -- | SectionManifest, checkpoint resume |
| `dataframes/watermark.py` | ~200 | WatermarkRepository |
| `lambda_handlers/cache_warmer.py` | -- | Lambda warmer with priority + self-continuation |
| `persistence/session.py` | 1,853 | SaveSession with CacheInvalidator |

---

## 11. ADR and Design Document References

| Reference | Topic |
|-----------|-------|
| ADR-0020 | Incremental story loading |
| ADR-0021 | DataFrame caching |
| ADR-0023 | Cache event integration |
| ADR-0025 | autom8 integration, Redis provider |
| ADR-0026 | Two-tier caching (Redis+S3) |
| ADR-0119 | Entity-type-specific TTLs, 6-step read pattern |
| TDD-materialization-layer | Watermark system, incremental sync |
| TDD-WS2-CACHE-RELIABILITY | Cache reliability hardening (WS2) |

---

## 12. Caching Concepts Inventory

The cache subsystem employs 31 distinct concepts (see PHILOSOPHY document for cognitive load analysis):

| Category | Concepts | Count |
|----------|----------|-------|
| Freshness modes | STRICT, EVENTUAL, IMMEDIATE | 3 |
| Freshness states | FRESH, STALE_SERVABLE, STALE_REFRESHING, EXPIRED, MISSING, ERROR | 6 |
| Cache tiers | Redis hot, S3 cold, Memory LRU, S3 Parquet | 4 |
| Providers | Null, InMemory, Redis, S3, Tiered | 5 |
| Entry types | 14 entry types | 14 |
| Completeness levels | MINIMAL, STANDARD, FULL, CUSTOM | 4 |
| Invalidation | TTL passive, MutationInvalidator, CacheInvalidator, watermark | 4 |
| Patterns | SWR, write-through, cache-aside, promotion | 4 |
| Protection | Circuit breaker, retry, degraded mode | 3 |

Some concepts span categories. The 31-concept count represents the minimum a developer must understand to work effectively across both cache systems.
