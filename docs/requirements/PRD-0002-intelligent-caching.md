---
status: superseded
superseded_by: /docs/reference/REF-cache-architecture.md
superseded_date: 2025-12-24
---

# PRD: Intelligent Caching Layer

## Metadata
- **PRD ID**: PRD-0002
- **Status**: Superseded
- **Author**: Claude/Requirements Analyst
- **Created**: 2025-12-09
- **Last Updated**: 2025-12-09
- **Stakeholders**: autom8 team, SDK consumers, infrastructure team
- **Related PRDs**: [PRD-0001](PRD-0001-sdk-extraction.md) (SDK Extraction - prerequisite)

## Problem Statement

The autom8_asana SDK currently has a basic `CacheProvider` protocol with only three methods (`get`, `set`, `delete`) and no intelligent cache invalidation. The legacy autom8 codebase contains battle-tested caching patterns that dramatically reduce API calls through versioned entries, batch modification checking, and relationship caching, but these patterns are tightly coupled to S3 storage.

**Current State**:
- SDK has `CacheProvider` protocol with `get()`, `set()`, `delete()` only
- Default implementations: `NullCacheProvider` (no-op) and `InMemoryCacheProvider` (with TTL, LRU)
- No support for versioned cache entries
- No batch staleness checking
- No relationship caching (subtasks, dependencies, stories, etc.)
- No cache metrics or observability

**Legacy System (autom8)**:
- `modified_at` versioning per entry type (7 types)
- S3 cache structure with per-task, per-entry-type granularity
- Batch modification checking with 25s in-memory TTL to prevent API spam
- Thread-safe locks per task GID
- Proven to reduce API calls by >50% in production

**Impact of Not Solving**:
1. SDK consumers make redundant API calls, hitting Asana rate limits (1500 req/min)
2. Dataframe generation for large projects is prohibitively slow
3. No visibility into cache performance
4. Cannot migrate legacy autom8 caching logic to the extracted SDK
5. Multi-service deployments cannot share cache state

## Goals & Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cache hit rate | >= 80% | `cache_hits / (cache_hits + cache_misses)` from CacheMetrics |
| API call reduction | >= 50% vs. no caching | Compare API call count with/without caching for standard workflows |
| Section dataframe generation | < 5s for 100 tasks | Timed operation with warm cache |
| Project dataframe generation | < 30s for 1,000 tasks | Timed operation with warm cache |
| Cache-related race conditions | Zero | No data corruption or stale reads in concurrent test suite |
| Public API compatibility | 100% backward compatible | No breaking changes to existing `CacheProvider` consumers |
| Graceful degradation | Redis failures do not crash services | SDK continues operating with NullCacheProvider fallback |

## Scope

### In Scope

**Protocol Extension**:
- Extended `CacheProvider` protocol with versioned operations
- `CacheEntry` dataclass with entry_type, version, TTL metadata
- Freshness parameter (`strict` vs `eventual` consistency)
- Batch operations (`get_batch`, `set_batch`)
- Cache warming API (`warm()`)

**Redis Backend**:
- `RedisCacheProvider` implementation
- Structured key format: `asana:tasks:{gid}:{entry_type}`
- Version tracking via Redis hashes
- Atomic operations using WATCH/MULTI for race-free updates
- Connection pooling and TLS support

**Multi-Entry Caching**:
- 7 entry types: TASK, SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS, STRUC
- Per-entry-type versioning with `modified_at` tracking
- Struc keys include project context: `struc:{task_gid}:{project_gid}`

**Batch Modification Checking**:
- Batch API call to check 100+ tasks for staleness in single request
- 25-second in-memory TTL to prevent check spam
- ECS run isolation (checks not shared across Lambda invocations)

**Incremental Loading**:
- Story loading with `since` parameter for efficient updates
- Merge new stories with cached stories
- Atomic cache updates

**Dataframe Caching**:
- Cache computed struc (structural data) per task+project
- Automatic invalidation on task modification

**TTL Configuration**:
- Per-project TTL settings
- Global fallback (default 300s)
- Configurable via SDK settings

**Overflow Management**:
- Per-relationship thresholds for caching
- Configurable limits: subtasks=40, dependencies=40, dependents=40, stories=100, attachments=40
- Skip caching for tasks exceeding thresholds

**Observability**:
- Extended `LogProvider` with `log_cache_event()` method
- Event types: hit, miss, write, evict, expire
- `CacheMetrics` aggregation helper class

**Graceful Degradation**:
- Automatic fallback to `NullCacheProvider` on Redis failure
- Warning log on degradation
- Auto-reconnect attempt with configurable interval

### Out of Scope

- **S3 backend**: Dropped in favor of Redis-only (BREAKING CHANGE from legacy autom8)
- **Legacy autom8 migration**: Cache data migration is not included; this is a big-bang cutover accepting cache miss spike at deployment
- **Distributed locking**: Task-level locking stays in-process; distributed locks are not required
- **Cache warming scheduler**: SDK provides `warm()` API; scheduling is consumer responsibility (documentation provided)
- **Cross-region replication**: Single Redis cluster per deployment
- **Cache encryption at rest**: Relies on Redis/ElastiCache encryption settings

## Requirements

### Functional Requirements

#### Protocol Extension (FR-CACHE-001 to FR-CACHE-010)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-001 | SDK shall extend `CacheProvider` protocol with `get_versioned()` method | Must | Method signature: `get_versioned(key: str, entry_type: EntryType) -> CacheEntry | None` |
| FR-CACHE-002 | SDK shall extend `CacheProvider` protocol with `set_versioned()` method | Must | Method signature: `set_versioned(key: str, entry: CacheEntry) -> None` |
| FR-CACHE-003 | SDK shall provide `CacheEntry` dataclass with metadata fields | Must | Fields: `data`, `entry_type`, `version` (modified_at), `cached_at`, `ttl` |
| FR-CACHE-004 | SDK shall define `EntryType` enum with 7 types | Must | Types: TASK, SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS, STRUC |
| FR-CACHE-005 | SDK shall support freshness parameter on cache reads | Must | `get_versioned(..., freshness: Freshness)` where Freshness is `strict` or `eventual` |
| FR-CACHE-006 | SDK shall provide `get_batch()` method for bulk cache reads | Should | Method signature: `get_batch(keys: list[str]) -> dict[str, CacheEntry | None]` |
| FR-CACHE-007 | SDK shall provide `set_batch()` method for bulk cache writes | Should | Method signature: `set_batch(entries: dict[str, CacheEntry]) -> None` |
| FR-CACHE-008 | SDK shall provide `warm()` method for cache warming | Should | Method signature: `warm(gids: list[str], entry_types: list[EntryType]) -> WarmResult` |
| FR-CACHE-009 | SDK shall maintain backward compatibility with existing `get/set/delete` | Must | Existing consumers using basic methods continue to work unchanged |
| FR-CACHE-010 | SDK shall provide `check_freshness()` method to validate cached version | Must | Compare cached `modified_at` against API response; return staleness status |

#### Redis Backend (FR-CACHE-011 to FR-CACHE-020)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-011 | SDK shall provide `RedisCacheProvider` implementation | Must | Class implements extended `CacheProvider` protocol using Redis |
| FR-CACHE-012 | SDK shall use key structure `asana:tasks:{gid}:{entry_type}` | Must | Keys follow pattern; entry_type is lowercase enum value |
| FR-CACHE-013 | SDK shall store version metadata in Redis hash fields | Must | Hash keys: `data`, `version`, `cached_at`, `ttl` |
| FR-CACHE-014 | SDK shall use WATCH/MULTI for atomic read-modify-write | Must | No race conditions when concurrent writes to same key |
| FR-CACHE-015 | SDK shall support connection pooling | Must | Configurable pool size; connections reused across operations |
| FR-CACHE-016 | SDK shall support TLS connections to Redis | Must | TLS enabled by default; configurable cert verification |
| FR-CACHE-017 | SDK shall support Redis AUTH (password authentication) | Must | Password configurable via settings or environment |
| FR-CACHE-018 | SDK shall support Redis cluster mode | Should | Auto-discovery of cluster nodes; proper key hashing |
| FR-CACHE-019 | SDK shall implement configurable connection timeout | Must | Default 5s connect timeout; configurable |
| FR-CACHE-020 | SDK shall implement configurable operation timeout | Must | Default 1s operation timeout; configurable |

#### Multi-Entry Caching (FR-CACHE-021 to FR-CACHE-030)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-021 | SDK shall cache TASK entries with `modified_at` versioning | Must | Task data cached; invalidated when API returns newer `modified_at` |
| FR-CACHE-022 | SDK shall cache SUBTASKS entries separately from parent task | Must | Subtask list cached under `asana:tasks:{parent_gid}:subtasks` |
| FR-CACHE-023 | SDK shall cache DEPENDENCIES entries separately | Must | Dependencies cached under `asana:tasks:{gid}:dependencies` |
| FR-CACHE-024 | SDK shall cache DEPENDENTS entries separately | Must | Dependents cached under `asana:tasks:{gid}:dependents` |
| FR-CACHE-025 | SDK shall cache STORIES entries with incremental support | Must | Stories cached with `since` parameter for efficient updates |
| FR-CACHE-026 | SDK shall cache ATTACHMENTS entries separately | Must | Attachments cached under `asana:tasks:{gid}:attachments` |
| FR-CACHE-027 | SDK shall cache STRUC entries with project context in key | Must | Key format: `asana:struc:{task_gid}:{project_gid}` |
| FR-CACHE-028 | SDK shall invalidate dependent entries when parent modified | Should | When TASK modified, invalidate related STRUC entries |
| FR-CACHE-029 | SDK shall support entry-type-specific TTLs | Should | Different TTLs for TASK (300s) vs STORIES (600s) configurable |
| FR-CACHE-030 | SDK shall support selective entry type caching | Should | Consumer can enable/disable caching per entry type |

#### Batch Modification Checking (FR-CACHE-031 to FR-CACHE-040)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-031 | SDK shall provide batch staleness check for multiple GIDs | Must | Single API call checks `modified_at` for up to 100 tasks |
| FR-CACHE-032 | SDK shall maintain 25-second in-memory TTL for batch check results | Must | Same batch not re-checked within 25s; results cached in-process |
| FR-CACHE-033 | SDK shall isolate batch check cache per process | Must | ECS tasks / Lambda invocations do not share in-memory check cache |
| FR-CACHE-034 | SDK shall return list of stale GIDs from batch check | Must | Return type: `list[str]` containing GIDs with newer `modified_at` |
| FR-CACHE-035 | SDK shall automatically invalidate cache for stale GIDs | Should | Stale entries deleted from Redis after batch check identifies them |
| FR-CACHE-036 | SDK shall support configurable batch check TTL | Should | 25s default; configurable via settings |
| FR-CACHE-037 | SDK shall chunk batch checks to API limits | Must | If >100 GIDs, automatically split into multiple API calls |
| FR-CACHE-038 | SDK shall track batch check efficiency metrics | Should | Log ratio of stale vs fresh in batch checks |
| FR-CACHE-039 | SDK shall provide `check_batch_staleness()` public method | Must | Method signature: `check_batch_staleness(gids: list[str]) -> StalenessResult` |
| FR-CACHE-040 | SDK shall use thread-safe lock for in-memory batch check cache | Must | No race conditions in concurrent batch check access |

#### Incremental Loading (FR-CACHE-041 to FR-CACHE-050)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-041 | SDK shall support `since` parameter for story loading | Must | Only fetch stories created after cached `last_story_at` |
| FR-CACHE-042 | SDK shall merge new stories with cached stories | Must | Append new stories; maintain chronological order |
| FR-CACHE-043 | SDK shall update cache atomically after story merge | Must | No partial updates; use Redis transaction |
| FR-CACHE-044 | SDK shall store `last_story_at` metadata in cache entry | Must | Metadata field tracks newest story timestamp |
| FR-CACHE-045 | SDK shall handle story deletion gracefully | Should | If API indicates fewer stories, perform full refresh |
| FR-CACHE-046 | SDK shall support incremental loading for other paginated resources | Could | Pattern extensible to attachments, subtasks if needed |
| FR-CACHE-047 | SDK shall provide `refresh_stories()` method for forced full load | Should | Bypass incremental; fetch all stories |
| FR-CACHE-048 | SDK shall limit incremental story batch size | Should | Max 100 stories per incremental fetch |
| FR-CACHE-049 | SDK shall handle story API pagination in incremental mode | Must | Follow next_page tokens when incrementally loading |
| FR-CACHE-050 | SDK shall preserve story ordering in cache | Must | Stories stored in creation order (oldest first) |

#### Dataframe Caching (FR-CACHE-051 to FR-CACHE-060)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-051 | SDK shall cache computed struc data per task+project | Must | Struc cached with composite key including project GID |
| FR-CACHE-052 | SDK shall invalidate struc cache when task is modified | Must | Struc entry deleted when task `modified_at` changes |
| FR-CACHE-053 | SDK shall invalidate struc cache when project custom fields change | Should | Struc depends on project context; invalidate on field changes |
| FR-CACHE-054 | SDK shall support batch struc retrieval | Should | `get_batch_struc(task_gids, project_gid)` for efficient dataframe building |
| FR-CACHE-055 | SDK shall track struc computation timestamp | Must | `computed_at` metadata for debugging cache freshness |
| FR-CACHE-056 | SDK shall support struc cache bypass for debugging | Should | `force_recompute=True` parameter to skip cache |
| FR-CACHE-057 | SDK shall limit struc cache size per project | Should | Configurable max entries per project (default 10,000) |
| FR-CACHE-058 | SDK shall provide struc cache statistics | Should | Hit rate, entry count, avg age per project |
| FR-CACHE-059 | SDK shall support struc cache warmup for project | Should | `warm_struc(project_gid, task_gids)` method |
| FR-CACHE-060 | SDK shall handle struc schema evolution | Should | Version struc format; invalidate on schema change |

#### TTL Configuration (FR-CACHE-061 to FR-CACHE-070)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-061 | SDK shall support per-project TTL configuration | Must | TTL can be set per project GID |
| FR-CACHE-062 | SDK shall provide global TTL fallback | Must | Default 300s when no project-specific TTL configured |
| FR-CACHE-063 | SDK shall support TTL configuration via SDK settings | Must | `CacheSettings(default_ttl=300, project_ttls={...})` |
| FR-CACHE-064 | SDK shall support per-entry-type TTL overrides | Should | TASK TTL different from STORIES TTL |
| FR-CACHE-065 | SDK shall support runtime TTL updates | Should | Change TTL without SDK restart |
| FR-CACHE-066 | SDK shall log TTL decisions at debug level | Should | Log which TTL was applied and why |
| FR-CACHE-067 | SDK shall support TTL=0 to disable caching for project | Should | Explicit opt-out for specific projects |
| FR-CACHE-068 | SDK shall support TTL=None for no expiration | Should | Entries never expire (manual invalidation only) |
| FR-CACHE-069 | SDK shall validate TTL values on configuration | Must | Reject negative TTLs; warn on excessively long TTLs (>1 hour) |
| FR-CACHE-070 | SDK shall expose active TTL configuration via API | Should | `cache.get_ttl_config()` returns current settings |

#### Overflow Management (FR-CACHE-071 to FR-CACHE-080)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-071 | SDK shall define per-relationship overflow thresholds | Must | Configurable limits per entry type |
| FR-CACHE-072 | SDK shall use default thresholds: subtasks=40, dependencies=40, dependents=40, stories=100, attachments=40 | Must | Defaults match legacy autom8 behavior |
| FR-CACHE-073 | SDK shall skip caching when relationship count exceeds threshold | Must | Log warning; proceed without caching |
| FR-CACHE-074 | SDK shall support configurable thresholds via settings | Must | `OverflowSettings(subtasks=40, stories=100, ...)` |
| FR-CACHE-075 | SDK shall track overflow occurrences in metrics | Should | Count of skipped cache writes due to overflow |
| FR-CACHE-076 | SDK shall support threshold=None to disable overflow check | Should | Cache all entries regardless of count |
| FR-CACHE-077 | SDK shall check overflow before API call when possible | Should | If cache entry has count, skip fetch for known-overflow tasks |
| FR-CACHE-078 | SDK shall support per-project overflow overrides | Could | Higher thresholds for specific high-activity projects |
| FR-CACHE-079 | SDK shall warn on first overflow for a task | Should | Single warning per task per session; not spam |
| FR-CACHE-080 | SDK shall provide overflow statistics | Should | `cache.get_overflow_stats()` returns counts by type |

#### Observability (FR-CACHE-081 to FR-CACHE-090)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-081 | SDK shall extend `LogProvider` protocol with `log_cache_event()` | Must | New method for structured cache event logging |
| FR-CACHE-082 | SDK shall emit events for cache hit, miss, write, evict, expire | Must | Each operation type has distinct event |
| FR-CACHE-083 | SDK shall include event metadata: key, entry_type, latency_ms | Must | Structured data for each cache event |
| FR-CACHE-084 | SDK shall provide `CacheMetrics` aggregation helper | Should | Accumulates hit/miss counts, latencies over time window |
| FR-CACHE-085 | SDK shall support callback registration for cache events | Must | Consumer registers callback via `on_cache_event(callback)` |
| FR-CACHE-086 | SDK shall provide hit rate calculation helper | Should | `metrics.hit_rate()` returns percentage |
| FR-CACHE-087 | SDK shall support periodic metrics emission | Should | Configurable interval for metrics summary log |
| FR-CACHE-088 | SDK shall include correlation ID in cache events | Should | Link cache events to originating API request |
| FR-CACHE-089 | SDK shall support metrics reset | Should | `metrics.reset()` for fresh window |
| FR-CACHE-090 | SDK shall provide cache size estimation | Should | Approximate memory/storage usage |

#### Graceful Degradation (FR-CACHE-091 to FR-CACHE-100)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-091 | SDK shall fallback to `NullCacheProvider` on Redis connection failure | Must | Operations continue; all reads return cache miss |
| FR-CACHE-092 | SDK shall log warning when degrading to no-cache mode | Must | Single warning log, not per-operation |
| FR-CACHE-093 | SDK shall attempt auto-reconnect to Redis | Must | Configurable reconnect interval (default 30s) |
| FR-CACHE-094 | SDK shall restore full caching on successful reconnect | Must | Automatic promotion from NullCacheProvider back to Redis |
| FR-CACHE-095 | SDK shall not throw exceptions on cache failures | Must | Cache errors caught; operation proceeds without cache |
| FR-CACHE-096 | SDK shall track degradation events in metrics | Should | Count of degradation occurrences |
| FR-CACHE-097 | SDK shall support manual cache disable | Should | `cache.disable()` / `cache.enable()` API |
| FR-CACHE-098 | SDK shall support health check endpoint | Should | `cache.is_healthy()` returns bool |
| FR-CACHE-099 | SDK shall emit event on degradation state change | Should | Callback notified on degrade/restore |
| FR-CACHE-100 | SDK shall respect circuit breaker pattern | Could | After N failures, stop attempting for cooldown period |

### Non-Functional Requirements

#### Performance (NFR-PERF-001 to NFR-PERF-010)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-PERF-001 | Cache hit rate | >= 80% for warm cache | CacheMetrics.hit_rate() over 1-hour window |
| NFR-PERF-002 | Redis read latency | < 5ms p99 | Measured via cache event latency_ms |
| NFR-PERF-003 | Redis write latency | < 10ms p99 | Measured via cache event latency_ms |
| NFR-PERF-004 | Batch modification check | < 500ms for 100 GIDs | End-to-end including API call |
| NFR-PERF-005 | Cache warm operation | < 1s per 100 entries | Bulk population time |
| NFR-PERF-006 | Memory overhead | < 50MB for 10,000 entries | In-memory index/metadata size |
| NFR-PERF-007 | Connection pool efficiency | < 10 connections for typical workload | Redis connection count |
| NFR-PERF-008 | Batch get throughput | >= 1,000 keys/second | Sequential batch operations |
| NFR-PERF-009 | Struc computation with cache | < 50ms per task | Cached struc retrieval |
| NFR-PERF-010 | Cold start penalty | < 2s for cache initialization | Time from import to first operation |

#### Reliability (NFR-REL-001 to NFR-REL-010)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-REL-001 | Graceful degradation | 100% availability during Redis outage | Service continues operating |
| NFR-REL-002 | No data loss on write failure | Zero lost writes | Retry or log; never silent failure |
| NFR-REL-003 | Auto-reconnect success | Within 30s of Redis recovery | Time to restore caching |
| NFR-REL-004 | Cache consistency | No stale reads in strict mode | Validation via freshness check |
| NFR-REL-005 | Thread safety | Zero race conditions | Concurrent test suite passes |
| NFR-REL-006 | Connection resilience | Survive network blips < 5s | No degradation for transient issues |
| NFR-REL-007 | Idempotent operations | Safe to retry any operation | No side effects from retries |
| NFR-REL-008 | Crash recovery | No corruption after process crash | Redis data remains valid |
| NFR-REL-009 | Memory leak prevention | Stable memory over 24h run | No unbounded growth |
| NFR-REL-010 | Error rate | < 0.1% cache operation failures | Excluding intentional degradation |

#### Compatibility (NFR-COMPAT-001 to NFR-COMPAT-010)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-COMPAT-001 | Backward compatible CacheProvider | Existing consumers work unchanged | No API breaks |
| NFR-COMPAT-002 | Public SDK API stability | No breaking changes | Semantic versioning compliance |
| NFR-COMPAT-003 | Python version support | 3.12+ | CI matrix testing |
| NFR-COMPAT-004 | Redis version support | 6.x, 7.x | Tested against both versions |
| NFR-COMPAT-005 | AWS ElastiCache compatibility | Works with ElastiCache Redis | Tested in AWS environment |
| NFR-COMPAT-006 | AWS Valkey compatibility | Works with ElastiCache Valkey | Tested in AWS environment |
| NFR-COMPAT-007 | Optional Redis dependency | SDK works without redis-py | Redis features disabled gracefully |
| NFR-COMPAT-008 | Protocol extension additive | New methods don't break old implementations | Default implementations provided |
| NFR-COMPAT-009 | Settings backward compatible | Old settings continue working | Deprecation warnings for removed |
| NFR-COMPAT-010 | Serialization format stable | Cache readable across SDK versions | Version field in cache entries |

#### Security (NFR-SEC-001 to NFR-SEC-010)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-SEC-001 | TLS encryption | Enabled by default for Redis | Connection uses TLS 1.2+ |
| NFR-SEC-002 | No secrets in cache keys | Keys contain only GIDs | Code review / static analysis |
| NFR-SEC-003 | Redis AUTH support | Password authentication supported | Configurable credentials |
| NFR-SEC-004 | No credential logging | Passwords never logged | Log audit |
| NFR-SEC-005 | Secure defaults | TLS on, AUTH required in production | Default configuration |
| NFR-SEC-006 | Connection string safety | No credentials in connection URLs | Use separate auth parameter |
| NFR-SEC-007 | Cache data sensitivity | Asana data classified appropriately | Data handling policy compliance |
| NFR-SEC-008 | Audit logging | Cache access logged with identity | LogProvider integration |
| NFR-SEC-009 | Rate limiting bypass prevention | Cache cannot be used to bypass Asana limits | Still respect API limits |
| NFR-SEC-010 | Input validation | Cache keys sanitized | No injection vulnerabilities |

## User Stories / Use Cases

### US-1: Developer Configures Per-Project TTLs

As a developer, I want to configure different cache TTLs for different projects so that high-traffic projects invalidate faster while stable projects retain cache longer.

**Scenario**:
1. Developer identifies project "Marketing Campaign" (GID: 123) has frequent updates
2. Developer configures TTL of 60s for project 123, default 300s for others
3. SDK uses 60s TTL for all cache entries related to project 123
4. Other projects use 300s default TTL
5. Marketing team sees fresher data; other teams benefit from longer cache

**Acceptance**: Per-project TTL configuration works; observable via cache event logs.

### US-2: Operator Monitors Cache Hit Rate

As an operations engineer, I want cache metrics exposed via callbacks so I can send them to CloudWatch and set up alerts for degraded cache performance.

**Scenario**:
1. Operator registers callback with `on_cache_event()`
2. Callback transforms events to CloudWatch metric format
3. CloudWatch receives hit/miss/latency metrics
4. Operator creates alarm for hit rate < 70%
5. Alert fires when cache degradation detected

**Acceptance**: Cache events contain sufficient metadata for CloudWatch integration.

### US-3: Application Handles Redis Outage

As an application developer, I want the SDK to gracefully degrade when Redis is unavailable so my service continues operating without crashing.

**Scenario**:
1. Application running with RedisCacheProvider
2. Redis cluster experiences outage
3. SDK logs warning, switches to NullCacheProvider
4. Application continues operating with cache misses
5. Redis recovers; SDK auto-reconnects within 30s
6. Full caching restored without restart

**Acceptance**: No exceptions thrown during outage; automatic recovery on Redis restore.

### US-4: Service Builds Large Dataframe Efficiently

As a data analyst, I want project dataframe generation to be fast so I can iterate quickly on reports.

**Scenario**:
1. Analyst requests dataframe for 1,000-task project
2. First request takes ~30s (cold cache)
3. Second request takes <5s (warm cache)
4. Tasks modified in Asana are detected via batch check
5. Only modified tasks re-fetched; others served from cache

**Acceptance**: 1,000-task dataframe < 30s cold, < 10s warm with >=80% hit rate.

### US-5: Service Avoids Caching Overflow Tasks

As a developer, I want the SDK to skip caching for tasks with excessive subtasks/stories so Redis memory is not wasted on rarely-reused data.

**Scenario**:
1. Task has 500 subtasks (exceeds threshold of 40)
2. SDK detects overflow on fetch
3. SDK logs warning, skips caching subtasks for this task
4. Task data (TASK entry type) still cached
5. Memory conserved for typical tasks

**Acceptance**: Overflow tasks logged; cache memory bounded.

### US-6: Developer Warms Cache Before Batch Processing

As a developer, I want to pre-warm the cache before batch processing so subsequent operations have maximum cache hits.

**Scenario**:
1. Developer has list of 500 task GIDs to process
2. Developer calls `cache.warm(gids, [EntryType.TASK, EntryType.SUBTASKS])`
3. SDK fetches all 500 tasks and subtasks in optimal batches
4. Cache populated before main processing loop
5. Processing loop achieves ~99% hit rate

**Acceptance**: `warm()` populates cache; documented for consumer scheduling.

## Assumptions

| Assumption | Basis |
|------------|-------|
| Redis/Valkey cluster will be provisioned (ElastiCache) | Infrastructure team confirmed willingness to provision |
| Existing S3 cache data can be discarded | User confirmed big-bang migration acceptable; cache miss spike at deployment |
| autom8 team approves dropping S3 backend | User decision: Redis-only is acceptable breaking change |
| 25-second batch check TTL is appropriate | Matches legacy autom8 behavior; tunable if needed |
| Overflow thresholds from legacy are appropriate | Subtasks=40, stories=100, etc. based on production data |
| Python 3.12+ is minimum version | Project already requires 3.12+ per PRD-0001 |
| redis-py is acceptable dependency | Standard Redis client for Python |
| Cache consistency is eventually consistent by default | Strict mode available for sensitive operations |

## Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| PRD-0001 SDK Extraction | autom8 team | Complete | Caching builds on extracted SDK |
| Redis infrastructure (ElastiCache) | Infrastructure team | Required | Must be provisioned before Session 6 |
| redis-py library | Redis community | Available | Add to pyproject.toml dependencies |
| LogProvider extension | SDK team | Required | Must extend protocol for cache events |
| CacheSettings dataclass | SDK team | Required | New configuration model |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| (All 8 design questions resolved) | - | - | See User Decisions below |

### User Decisions (Resolved)

The following 8 questions were resolved by the user prior to PRD creation:

1. **TTL Configuration**: Per-project + global fallback
2. **Cache Warming**: Hybrid (manual `warm()` API + scheduling documentation)
3. **Backend Strategy**: Redis only (S3 dropped) - BREAKING CHANGE from legacy
4. **Migration Strategy**: Big-bang cutover (accept cache miss spike)
5. **Metrics Destination**: Consumer callback via LogProvider protocol extension
6. **Staleness Window**: Freshness parameter (`strict` vs `eventual`)
7. **Overflow Thresholds**: Per-relationship (subtasks=40, stories=100, etc.)
8. **Struc Context Key**: `struc:{task_gid}:{project_gid}` (varies by project custom fields)

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-09 | Claude/Requirements Analyst | Initial draft with 100 functional requirements, 40 NFRs |

---

## Appendix A: Entry Type Definitions

| Entry Type | Description | Cache Key Pattern | Version Field |
|------------|-------------|-------------------|---------------|
| TASK | Core task data | `asana:tasks:{gid}:task` | `modified_at` |
| SUBTASKS | List of subtask references | `asana:tasks:{gid}:subtasks` | Parent `modified_at` |
| DEPENDENCIES | List of dependency references | `asana:tasks:{gid}:dependencies` | Task `modified_at` |
| DEPENDENTS | List of dependent references | `asana:tasks:{gid}:dependents` | Task `modified_at` |
| STORIES | Comments and activity | `asana:tasks:{gid}:stories` | `last_story_at` |
| ATTACHMENTS | File attachments | `asana:tasks:{gid}:attachments` | Task `modified_at` |
| STRUC | Computed structural data | `asana:struc:{task_gid}:{project_gid}` | Task `modified_at` |

## Appendix B: Redis Key Structure

```
asana:tasks:{gid}:task
    ├── data: <JSON blob>
    ├── version: <modified_at timestamp>
    ├── cached_at: <cache write timestamp>
    └── ttl: <TTL in seconds>

asana:tasks:{gid}:stories
    ├── data: <JSON array of stories>
    ├── version: <last_story_at timestamp>
    ├── cached_at: <cache write timestamp>
    ├── ttl: <TTL in seconds>
    └── last_story_at: <newest story timestamp>

asana:struc:{task_gid}:{project_gid}
    ├── data: <computed struc JSON>
    ├── version: <task modified_at>
    ├── cached_at: <computation timestamp>
    └── ttl: <TTL in seconds>
```

## Appendix C: CacheEntry Dataclass (Draft)

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

class EntryType(Enum):
    TASK = "task"
    SUBTASKS = "subtasks"
    DEPENDENCIES = "dependencies"
    DEPENDENTS = "dependents"
    STORIES = "stories"
    ATTACHMENTS = "attachments"
    STRUC = "struc"

class Freshness(Enum):
    STRICT = "strict"      # Validate version before returning
    EVENTUAL = "eventual"  # Return cached without validation

@dataclass
class CacheEntry:
    data: dict[str, Any]
    entry_type: EntryType
    version: datetime       # modified_at or equivalent
    cached_at: datetime
    ttl: int | None        # TTL in seconds, None for no expiration

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return (datetime.utcnow() - self.cached_at).total_seconds() > self.ttl
```

## Appendix D: Success Criteria Traceability

| Success Criterion | Requirement IDs |
|-------------------|-----------------|
| Cache hit rate >= 80% | NFR-PERF-001, FR-CACHE-085, FR-CACHE-086 |
| 50% API call reduction | FR-CACHE-031, FR-CACHE-041, FR-CACHE-051 |
| Section dataframe < 5s | NFR-PERF-009, FR-CACHE-054 |
| Project dataframe < 30s | NFR-PERF-009, FR-CACHE-054, FR-CACHE-059 |
| No race conditions | NFR-REL-005, FR-CACHE-014, FR-CACHE-040 |
| Backward compatible | NFR-COMPAT-001, NFR-COMPAT-002, FR-CACHE-009 |
| Graceful degradation | NFR-REL-001, FR-CACHE-091 through FR-CACHE-100 |
