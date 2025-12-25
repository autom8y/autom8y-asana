---
status: superseded
superseded_by: /docs/reference/REF-cache-architecture.md
superseded_date: 2025-12-24
---

# PRD-CACHE-INTEGRATION: Activate Dormant Cache Infrastructure

**Document ID**: PRD-CACHE-INTEGRATION
**Version**: 1.0
**Date**: 2025-12-22
**Status**: Draft
**Author**: Requirements Analyst
**Discovery**: [DISCOVERY-CACHE-INTEGRATION.md](../analysis/DISCOVERY-CACHE-INTEGRATION.md)

---

## 1. Problem Statement

### 1.1 Current State

The autom8_asana SDK contains approximately 4,000 lines of sophisticated caching infrastructure that is entirely dormant. The cache layer includes:
- 4 provider implementations (Null, InMemory, Redis, Tiered)
- Versioned operations with staleness detection
- TTL management with overflow protection
- Multiple entry types (TASK, SUBTASKS, DEPENDENCIES, etc.)

However, `AsanaClient.__init__()` defaults to `NullCacheProvider()` at line 125 of `client.py`, meaning:
- Every `TasksClient.get_async()` call hits the Asana API
- No cache hits occur regardless of access patterns
- Rate limit consumption is unnecessarily high
- Response latency is always network-bound

### 1.2 Impact

**Without caching enabled**:
- Repeated reads of the same task incur full API latency (~100-300ms per call)
- Rate limit of 1500 requests/minute consumed faster than necessary
- No benefit from the 4,000 lines of cache infrastructure already implemented
- Production workloads hitting Asana API for every operation

### 1.3 Desired Outcome

Enable the existing cache infrastructure by default with environment-aware provider selection:
- Development environments use InMemoryCacheProvider automatically
- Production environments auto-detect Redis availability
- Write operations invalidate cache entries to prevent stale reads
- Entity-type-aware TTLs optimize cache efficiency for Business model entities

### 1.4 Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cache hit rate (warm) | >80% for repeated reads | Cache metrics |
| Cache hit latency | <5ms | p99 latency measurement |
| API call reduction | >50% for typical workflows | Before/after comparison |
| Zero breaking changes | 100% existing tests pass | CI pipeline |

---

## 2. Scope

### 2.1 In Scope

| Capability | Description |
|------------|-------------|
| Default provider selection | Environment-aware automatic provider selection |
| TasksClient.get_async() caching | Cache check before HTTP, store on miss |
| SaveSession invalidation | Invalidate cache on successful mutations |
| Entity-type TTL | Different TTLs for Business, Contact, Unit, Offer, Process |
| CacheConfig in AsanaConfig | Nested configuration following existing patterns |
| Environment variable support | Override via ASANA_CACHE_* variables |
| DataFrame default caching | Enable existing DataFrameCacheIntegration |

### 2.2 Out of Scope

| Capability | Reason | Future Work |
|------------|--------|-------------|
| list_async() caching | Pagination complexity, invalidation unclear | Phase 2 |
| subtasks_async() caching | Requires parent-keyed entries | Phase 2 |
| Cascade invalidation | Business update invalidating all Units | Phase 3 |
| S3 cold tier activation | Requires AWS infrastructure decisions | Phase 3 |
| Cache warming strategies | Optimization, not core enablement | Phase 3 |
| Cross-process cache sharing | InMemory is process-local | Phase 3 |

### 2.3 Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| Existing CacheProvider protocol | Internal | Implemented |
| NullCacheProvider | Internal | Implemented |
| InMemoryCacheProvider | Internal | Implemented |
| RedisCacheProvider | Internal | Implemented |
| CacheEntry, EntryType | Internal | Implemented |
| TTLSettings, CacheSettings | Internal | Implemented |

---

## 3. Functional Requirements

### 3.1 Default Provider Selection (FR-DEFAULT-*)

---

**FR-DEFAULT-001**: AsanaClient uses environment-aware cache provider by default

When `AsanaClient()` is instantiated without explicit `cache_provider` parameter, the SDK selects a cache provider based on environment detection.

**Acceptance Criteria**:
- GIVEN no `cache_provider` argument is passed to `AsanaClient()`
- AND `ASANA_CACHE_ENABLED` is not set to "false"
- WHEN the client is instantiated
- THEN a cache provider is selected via auto-detection logic
- AND the provider is not NullCacheProvider (unless explicitly configured)

**Traceability**: Discovery Section C.3

---

**FR-DEFAULT-002**: Provider selection priority order

The SDK follows a strict priority order when selecting cache provider:
1. Explicit `cache_provider` parameter (highest)
2. `ASANA_CACHE_PROVIDER` environment variable
3. Auto-detection based on environment
4. InMemoryCacheProvider fallback (lowest)

**Acceptance Criteria**:
- GIVEN `cache_provider=MyProvider()` is passed to `AsanaClient()`
- WHEN the client is instantiated
- THEN MyProvider is used regardless of environment variables
- AND no auto-detection occurs

- GIVEN `ASANA_CACHE_PROVIDER=redis` environment variable is set
- AND no explicit `cache_provider` is passed
- WHEN the client is instantiated
- THEN RedisCacheProvider is used
- AND REDIS_HOST must be configured or error is raised

- GIVEN no `cache_provider` parameter
- AND no `ASANA_CACHE_PROVIDER` environment variable
- AND `ASANA_ENVIRONMENT=development`
- WHEN the client is instantiated
- THEN InMemoryCacheProvider is used

**Traceability**: Discovery Section C.1

---

**FR-DEFAULT-003**: ASANA_CACHE_PROVIDER environment variable values

The `ASANA_CACHE_PROVIDER` environment variable accepts specific string values to explicitly select a cache provider.

| Value | Provider | Requirements |
|-------|----------|--------------|
| `memory` | InMemoryCacheProvider | None |
| `redis` | RedisCacheProvider | REDIS_HOST must be set |
| `tiered` | TieredCacheProvider | REDIS_HOST must be set |
| `none` or `null` | NullCacheProvider | None |

**Acceptance Criteria**:
- GIVEN `ASANA_CACHE_PROVIDER=memory`
- WHEN `AsanaClient()` is instantiated
- THEN InMemoryCacheProvider is used
- AND no Redis configuration is required

- GIVEN `ASANA_CACHE_PROVIDER=redis`
- AND `REDIS_HOST` is not set
- WHEN `AsanaClient()` is instantiated
- THEN ConfigurationError is raised with message indicating REDIS_HOST is required

- GIVEN `ASANA_CACHE_PROVIDER=none`
- WHEN `AsanaClient()` is instantiated
- THEN NullCacheProvider is used
- AND caching is completely disabled

**Traceability**: Discovery Section C.2

---

**FR-DEFAULT-004**: ASANA_CACHE_ENABLED master switch

The `ASANA_CACHE_ENABLED` environment variable provides a master switch to disable all caching regardless of other configuration.

**Acceptance Criteria**:
- GIVEN `ASANA_CACHE_ENABLED=false`
- AND `ASANA_CACHE_PROVIDER=redis`
- WHEN `AsanaClient()` is instantiated
- THEN NullCacheProvider is used
- AND no Redis connection is attempted

- GIVEN `ASANA_CACHE_ENABLED=true` (or not set)
- WHEN `AsanaClient()` is instantiated
- THEN normal provider selection proceeds

**Traceability**: Discovery Section C.2

---

**FR-DEFAULT-005**: Production environment auto-detection

In production environments, the SDK auto-detects Redis availability and uses it when configured, falling back appropriately when not available.

**Acceptance Criteria**:
- GIVEN `ASANA_ENVIRONMENT=production`
- AND `REDIS_HOST=redis.example.com`
- AND no explicit `cache_provider` parameter
- WHEN `AsanaClient()` is instantiated
- THEN RedisCacheProvider is created with the specified host

- GIVEN `ASANA_ENVIRONMENT=production`
- AND `REDIS_HOST` is not set
- AND no explicit `cache_provider` parameter
- WHEN `AsanaClient()` is instantiated
- THEN a warning is logged indicating Redis is not configured
- AND InMemoryCacheProvider is used as fallback

**Traceability**: Discovery Section C.3

---

**FR-DEFAULT-006**: Development environment default behavior

In development environments (default), InMemoryCacheProvider is used automatically without requiring any configuration.

**Acceptance Criteria**:
- GIVEN `ASANA_ENVIRONMENT` is not set (defaults to "development")
- AND no `cache_provider` parameter
- AND no `ASANA_CACHE_PROVIDER` variable
- WHEN `AsanaClient()` is instantiated
- THEN InMemoryCacheProvider is used
- AND default_ttl is 300 seconds
- AND max_size is 10000 entries

**Traceability**: Discovery Section C.3

---

### 3.2 Client Cache Integration (FR-CLIENT-*)

---

**FR-CLIENT-001**: TasksClient.get_async() checks cache before HTTP request

The `TasksClient.get_async()` method checks the cache for an existing entry before making an HTTP request to the Asana API.

**Acceptance Criteria**:
- GIVEN a task with GID "1234567890" is cached
- AND the cached entry has not expired (within TTL)
- WHEN `client.tasks.get_async("1234567890")` is called
- THEN the cached Task is returned
- AND no HTTP request is made to `/tasks/1234567890`
- AND cache hit metric is incremented

- GIVEN a task with GID "1234567890" is not in cache
- WHEN `client.tasks.get_async("1234567890")` is called
- THEN an HTTP GET request is made to `/tasks/1234567890`
- AND the response is stored in cache
- AND cache miss metric is incremented
- AND the Task is returned

**Traceability**: Discovery Section B.2

---

**FR-CLIENT-002**: Cache key format uses task GID and EntryType.TASK

Cache entries for individual tasks use the task GID as the key with `EntryType.TASK` as the entry type.

**Acceptance Criteria**:
- GIVEN `client.tasks.get_async("1234567890")` is called
- WHEN the task is fetched and cached
- THEN `cache.set_versioned("1234567890", entry)` is called
- AND `entry.entry_type` equals `EntryType.TASK`
- AND `entry.key` equals "1234567890"

**Traceability**: Discovery Section A.2

---

**FR-CLIENT-003**: Cache stores versioned entry with modified_at

When storing a task in cache, the entry includes the task's `modified_at` timestamp as the version for staleness detection.

**Acceptance Criteria**:
- GIVEN an API response with `{"gid": "123", "modified_at": "2025-01-15T10:30:00Z"}`
- WHEN the response is cached
- THEN `entry.version` equals `datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)`
- AND `entry.cached_at` equals the current UTC time

**Traceability**: Discovery Section A.3

---

**FR-CLIENT-004**: Cache respects TTL expiration

Cached entries that have exceeded their TTL are treated as cache misses and trigger fresh API fetches.

**Acceptance Criteria**:
- GIVEN a cached task with `ttl=300` seconds
- AND the entry was cached 301 seconds ago
- WHEN `client.tasks.get_async(gid)` is called
- THEN the expired entry is not returned
- AND a fresh HTTP request is made
- AND the new response replaces the expired entry

**Traceability**: Discovery Section A.3

---

**FR-CLIENT-005**: TasksClient.get() sync wrapper uses caching

The synchronous `get()` method uses the same caching behavior as `get_async()`.

**Acceptance Criteria**:
- GIVEN a cached task with GID "123"
- WHEN `client.tasks.get("123")` is called (sync)
- THEN the cached Task is returned
- AND no HTTP request is made

**Traceability**: Discovery Section B.2

---

**FR-CLIENT-006**: Explicit NullCacheProvider disables caching

Passing `cache_provider=NullCacheProvider()` explicitly disables all caching for that client instance.

**Acceptance Criteria**:
- GIVEN `client = AsanaClient(cache_provider=NullCacheProvider())`
- WHEN `client.tasks.get_async("123")` is called twice
- THEN two HTTP requests are made
- AND no caching occurs

**Traceability**: Discovery Section G.1

---

**FR-CLIENT-007**: raw=True parameter returns cached dict

When `raw=True` is specified and a cache hit occurs, the cached dict is returned directly without Task model validation.

**Acceptance Criteria**:
- GIVEN a cached task entry with `data={"gid": "123", "name": "Test"}`
- WHEN `client.tasks.get_async("123", raw=True)` is called
- THEN `{"gid": "123", "name": "Test"}` dict is returned
- AND no `Task.model_validate()` is called

**Traceability**: Discovery Section B.2

---

### 3.3 Write-Through Invalidation (FR-INVALIDATE-*)

---

**FR-INVALIDATE-001**: SaveSession.commit_async() invalidates cache for mutated entities

After successful CRUD operations in `SaveSession.commit_async()`, the cache entries for all successfully modified entities are invalidated.

**Acceptance Criteria**:
- GIVEN a cached task with GID "123"
- AND the task is tracked in SaveSession with modifications
- WHEN `await session.commit_async()` succeeds
- THEN `cache.invalidate("123", [EntryType.TASK])` is called
- AND subsequent `get_async("123")` fetches fresh data from API

**Traceability**: Discovery Section B.3

---

**FR-INVALIDATE-002**: UPDATE operations invalidate cache

When a task is updated via SaveSession, its cache entry is invalidated.

**Acceptance Criteria**:
- GIVEN a cached task with GID "123" and name "Old Name"
- AND `session.track(task)` followed by `task.name = "New Name"`
- WHEN `await session.commit_async()` succeeds
- THEN cache entry for "123" is invalidated
- AND next `get_async("123")` returns "New Name" from API

**Traceability**: Discovery Section B.3

---

**FR-INVALIDATE-003**: DELETE operations invalidate cache

When a task is deleted via SaveSession, its cache entry is invalidated.

**Acceptance Criteria**:
- GIVEN a cached task with GID "123"
- AND `session.delete(task)` is called
- WHEN `await session.commit_async()` succeeds
- THEN cache entry for "123" is invalidated

**Traceability**: Discovery Section B.3

---

**FR-INVALIDATE-004**: CREATE operations warm cache with new entity

When a new task is created via SaveSession, the response is stored in cache immediately.

**Acceptance Criteria**:
- GIVEN a new task with temp GID "temp_1"
- AND `session.track(new_task)` is called
- WHEN `await session.commit_async()` succeeds
- AND the API assigns real GID "999"
- THEN cache entry for "999" is created with the response data
- AND subsequent `get_async("999")` returns cached data

**Traceability**: Discovery Section B.3

---

**FR-INVALIDATE-005**: Batch invalidation efficiency

Cache invalidation for multiple entities in a single commit is performed in a single loop iteration, not per-operation.

**Acceptance Criteria**:
- GIVEN 10 tasks are tracked and modified in SaveSession
- WHEN `await session.commit_async()` succeeds for all 10
- THEN invalidation iterates once over `crud_result.succeeded`
- AND each GID is invalidated exactly once
- AND total invalidation overhead is O(n) not O(n^2)

**Traceability**: Discovery Section B.3

---

**FR-INVALIDATE-006**: Action operations invalidate affected tasks

Successful action operations (add_tag, move_to_section, etc.) invalidate the cache for the affected task.

**Acceptance Criteria**:
- GIVEN a cached task with GID "123"
- AND `session.add_tag(task, "tag_gid")` is called
- WHEN `await session.commit_async()` succeeds
- THEN cache entry for "123" is invalidated
- AND `action_result.action.task.gid` is used for invalidation key

**Traceability**: Discovery Section B.4

---

### 3.4 Entity-Type TTL (FR-TTL-*)

---

**FR-TTL-001**: Business entities use 3600 second TTL

Tasks identified as Business entities use a 1-hour (3600 second) TTL.

**Acceptance Criteria**:
- GIVEN a task that is detected as a Business entity
- WHEN the task is cached
- THEN `entry.ttl` equals 3600
- AND the entry remains valid for 1 hour

**Traceability**: Discovery Section E.1

---

**FR-TTL-002**: Contact and Unit entities use 900 second TTL

Tasks identified as Contact or Unit entities use a 15-minute (900 second) TTL.

**Acceptance Criteria**:
- GIVEN a task that is detected as a Contact entity
- WHEN the task is cached
- THEN `entry.ttl` equals 900

- GIVEN a task that is detected as a Unit entity
- WHEN the task is cached
- THEN `entry.ttl` equals 900

**Traceability**: Discovery Section E.1

---

**FR-TTL-003**: Offer entities use 180 second TTL

Tasks identified as Offer entities use a 3-minute (180 second) TTL due to frequent pipeline state changes.

**Acceptance Criteria**:
- GIVEN a task that is detected as an Offer entity
- WHEN the task is cached
- THEN `entry.ttl` equals 180

**Traceability**: Discovery Section E.1

---

**FR-TTL-004**: Process entities use 60 second TTL

Tasks identified as Process entities use a 1-minute (60 second) TTL due to very frequent state machine transitions.

**Acceptance Criteria**:
- GIVEN a task that is detected as a Process entity
- WHEN the task is cached
- THEN `entry.ttl` equals 60

**Traceability**: Discovery Section E.1

---

**FR-TTL-005**: Generic tasks use 300 second default TTL

Tasks that are not identified as Business model entities use the default 5-minute (300 second) TTL.

**Acceptance Criteria**:
- GIVEN a task that is not a Business, Contact, Unit, Offer, or Process
- WHEN the task is cached
- THEN `entry.ttl` equals 300

**Traceability**: Discovery Section E.1

---

**FR-TTL-006**: TTL resolution priority

TTL is resolved in priority order: explicit override > entity-type > default.

**Acceptance Criteria**:
- GIVEN a Business entity (normally 3600s)
- AND `CacheConfig.ttl.entity_type_ttls["business"] = 1800`
- WHEN the task is cached
- THEN `entry.ttl` equals 1800 (configured override)

- GIVEN `CacheConfig.ttl.default_ttl = 600`
- AND a generic task (not a known entity type)
- WHEN the task is cached
- THEN `entry.ttl` equals 600 (configured default)

**Traceability**: Discovery Section E.3

---

**FR-TTL-007**: Entity type detection for TTL selection

Entity type is determined from the Task model when available, or defaults to generic task.

**Acceptance Criteria**:
- GIVEN a Task instance with entity type detection available
- AND the task is detected as type "offer"
- WHEN TTL is resolved for caching
- THEN the Offer TTL (180s) is used

- GIVEN a raw dict response without entity type detection
- WHEN TTL is resolved for caching
- THEN the default TTL (300s) is used

**Traceability**: Discovery Section E.3

---

### 3.5 DataFrame Integration (FR-DF-*)

---

**FR-DF-001**: DataFrameCacheIntegration enabled by default

The existing DataFrameCacheIntegration is automatically enabled when the cache provider is active.

**Acceptance Criteria**:
- GIVEN `AsanaClient()` with default caching enabled
- WHEN DataFrame operations use caching
- THEN DataFrameCacheIntegration uses the client's cache provider
- AND no explicit instantiation is required

**Traceability**: Discovery Appendix (dataframes/cache_integration.py)

---

**FR-DF-002**: DataFrame caching opt-out via config

DataFrame caching can be disabled via configuration while leaving task caching enabled.

**Acceptance Criteria**:
- GIVEN `CacheConfig(dataframe_caching=False)`
- WHEN DataFrame operations execute
- THEN DataFrameCacheIntegration is not used
- AND task caching via TasksClient remains active

**Traceability**: Discovery Section D.3

---

### 3.6 Configuration (FR-CONFIG-*)

---

**FR-CONFIG-001**: CacheConfig nested in AsanaConfig

Cache configuration is nested within AsanaConfig following the existing pattern for RateLimitConfig, RetryConfig, etc.

**Acceptance Criteria**:
- GIVEN `config = AsanaConfig(cache=CacheConfig(enabled=True))`
- WHEN `AsanaClient(config=config)` is instantiated
- THEN the cache configuration is accessible via `config.cache`
- AND the pattern matches existing nested configs

**Traceability**: Discovery Section D.3

---

**FR-CONFIG-002**: CacheConfig fields

CacheConfig exposes the following configuration fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | True | Master enable/disable |
| `provider` | str or None | None | Explicit provider selection |
| `freshness` | Freshness | EVENTUAL | Default freshness mode |
| `ttl` | TTLSettings | (defaults) | TTL configuration |
| `overflow` | OverflowSettings | (defaults) | Overflow thresholds |

**Acceptance Criteria**:
- GIVEN `CacheConfig()` with no arguments
- THEN `enabled` equals True
- AND `provider` equals None (auto-detect)
- AND `freshness` equals `Freshness.EVENTUAL`
- AND `ttl.default_ttl` equals 300

**Traceability**: Discovery Section D.3

---

**FR-CONFIG-003**: CacheConfig.from_env() class method

CacheConfig provides a `from_env()` class method to create configuration from environment variables.

**Acceptance Criteria**:
- GIVEN `ASANA_CACHE_ENABLED=false` in environment
- WHEN `CacheConfig.from_env()` is called
- THEN `config.enabled` equals False

- GIVEN `ASANA_CACHE_TTL_DEFAULT=600` in environment
- WHEN `CacheConfig.from_env()` is called
- THEN `config.ttl.default_ttl` equals 600

**Traceability**: Discovery Section D.3

---

**FR-CONFIG-004**: Programmatic override capability

Configuration can be fully specified programmatically, overriding any environment variables.

**Acceptance Criteria**:
- GIVEN `ASANA_CACHE_ENABLED=false` in environment
- AND `AsanaClient(config=AsanaConfig(cache=CacheConfig(enabled=True)))`
- WHEN the client is instantiated
- THEN caching is enabled (programmatic wins over env var)

**Traceability**: Discovery Section D.3

---

### 3.7 Environment Variable Support (FR-ENV-*)

---

**FR-ENV-001**: ASANA_CACHE_ENABLED environment variable

The `ASANA_CACHE_ENABLED` variable controls the master enable/disable switch.

| Value | Effect |
|-------|--------|
| `true`, `1`, `yes` (or not set) | Caching enabled |
| `false`, `0`, `no` | Caching disabled (NullCacheProvider) |

**Acceptance Criteria**:
- GIVEN `ASANA_CACHE_ENABLED=false`
- WHEN `AsanaClient()` is instantiated
- THEN NullCacheProvider is used

**Traceability**: Discovery Section C.2

---

**FR-ENV-002**: ASANA_CACHE_PROVIDER environment variable

The `ASANA_CACHE_PROVIDER` variable explicitly selects a cache provider.

| Value | Provider |
|-------|----------|
| `memory` | InMemoryCacheProvider |
| `redis` | RedisCacheProvider |
| `tiered` | TieredCacheProvider |
| `none`, `null` | NullCacheProvider |

**Acceptance Criteria**:
- GIVEN `ASANA_CACHE_PROVIDER=memory`
- WHEN `AsanaClient()` is instantiated
- THEN InMemoryCacheProvider is used

**Traceability**: Discovery Section C.2

---

**FR-ENV-003**: ASANA_CACHE_TTL_DEFAULT environment variable

The `ASANA_CACHE_TTL_DEFAULT` variable sets the default TTL in seconds.

**Acceptance Criteria**:
- GIVEN `ASANA_CACHE_TTL_DEFAULT=600`
- WHEN `AsanaClient()` is instantiated
- THEN default TTL is 600 seconds (not 300)

**Traceability**: Discovery Section C.2

---

**FR-ENV-004**: ASANA_ENVIRONMENT environment variable

The `ASANA_ENVIRONMENT` variable hints the deployment environment for auto-detection.

| Value | Behavior |
|-------|----------|
| `production`, `staging` | Prefer Redis, warn if unavailable |
| `development`, `test` (or not set) | Use InMemory by default |

**Acceptance Criteria**:
- GIVEN `ASANA_ENVIRONMENT=production`
- AND `REDIS_HOST` is not set
- WHEN `AsanaClient()` is instantiated
- THEN a warning is logged
- AND InMemoryCacheProvider is used as fallback

**Traceability**: Discovery Section C.3

---

**FR-ENV-005**: Redis-specific environment variables

Redis configuration uses existing environment variables from autom8_adapter.py.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_HOST` | Yes (for redis) | None | Redis server hostname |
| `REDIS_PORT` | No | 6379 | Redis server port |
| `REDIS_PASSWORD` | No | None | Redis authentication |
| `REDIS_SSL` | No | true | Enable TLS |

**Acceptance Criteria**:
- GIVEN `ASANA_CACHE_PROVIDER=redis`
- AND `REDIS_HOST=cache.example.com`
- AND `REDIS_PORT=6380`
- AND `REDIS_SSL=false`
- WHEN RedisCacheProvider is created
- THEN it connects to `cache.example.com:6380` without TLS

**Traceability**: Discovery Section C.2

---

## 4. Non-Functional Requirements

### 4.1 Performance (NFR-PERF-*)

---

**NFR-PERF-001**: Cache hit latency under 5ms

Cache hit operations complete within 5 milliseconds at p99.

**Acceptance Criteria**:
- GIVEN 1000 consecutive cache hit operations
- WHEN latency is measured
- THEN p99 latency is less than 5ms
- AND mean latency is less than 1ms

**Measurement**: Benchmark test with InMemoryCacheProvider

---

**NFR-PERF-002**: Cache miss overhead under 10ms

The overhead of checking cache before making an API call adds less than 10ms to cache miss scenarios.

**Acceptance Criteria**:
- GIVEN a cache miss scenario
- WHEN comparing total time to baseline (no cache check)
- THEN overhead is less than 10ms

**Measurement**: Benchmark test comparing cached client vs NullCacheProvider client

---

**NFR-PERF-003**: Warm entity access 10x improvement

Accessing a cached entity is at least 10x faster than fetching from API.

**Acceptance Criteria**:
- GIVEN API latency of 100ms (typical)
- AND cache hit latency of 5ms
- WHEN comparing cached vs uncached access
- THEN cached access is at least 10x faster (100ms / 5ms = 20x)

**Measurement**: Integration test with real API comparison

---

**NFR-PERF-004**: Memory bounded eviction

InMemoryCacheProvider enforces maximum entry count and evicts when full.

**Acceptance Criteria**:
- GIVEN `max_size=10000` (default)
- AND 10001 entries are written
- WHEN eviction triggers
- THEN oldest 10% (1000 entries) are removed
- AND total entries remain at or below 10000

**Measurement**: Unit test verifying eviction behavior

---

### 4.2 Backward Compatibility (NFR-COMPAT-*)

---

**NFR-COMPAT-001**: Existing consumer code unchanged

Code using `AsanaClient()` without cache configuration continues to work identically.

**Acceptance Criteria**:
- GIVEN existing code: `client = AsanaClient(token="...")`
- WHEN upgraded to new SDK version
- THEN code executes without modification
- AND behavior is enhanced with caching (not broken)

---

**NFR-COMPAT-002**: All existing tests pass

The complete test suite passes without modification.

**Acceptance Criteria**:
- GIVEN the current test suite (~500 tests)
- WHEN run against the new implementation
- THEN 100% of tests pass
- AND no tests require modification

---

**NFR-COMPAT-003**: Public API signatures preserved

All public method signatures remain unchanged.

**Acceptance Criteria**:
- GIVEN `TasksClient.get_async(task_gid, *, raw=False, opt_fields=None)`
- WHEN the new implementation is deployed
- THEN the signature is identical
- AND return type is unchanged (`Task | dict[str, Any]`)

---

**NFR-COMPAT-004**: Opt-out always available

Users can completely disable caching via explicit NullCacheProvider.

**Acceptance Criteria**:
- GIVEN `client = AsanaClient(cache_provider=NullCacheProvider())`
- WHEN any operation is performed
- THEN no caching occurs
- AND behavior matches pre-integration behavior exactly

---

### 4.3 Graceful Degradation (NFR-DEGRADE-*)

---

**NFR-DEGRADE-001**: Cache failures log warnings without raising

Cache operation failures are logged but do not raise exceptions to callers.

**Acceptance Criteria**:
- GIVEN Redis is configured but unreachable
- WHEN `client.tasks.get_async("123")` is called
- THEN the API is called directly (fallback)
- AND a warning is logged: "Cache operation failed, proceeding without cache"
- AND no exception propagates to caller

**Traceability**: Discovery Section G.3

---

**NFR-DEGRADE-002**: Redis unavailable falls back gracefully

When Redis becomes unavailable, operations continue using API directly.

**Acceptance Criteria**:
- GIVEN RedisCacheProvider is configured
- AND Redis connection is lost mid-operation
- WHEN `client.tasks.get_async("123")` is called
- THEN the API call succeeds
- AND cache miss is recorded
- AND no exception is raised

**Traceability**: Discovery Section G.3

---

**NFR-DEGRADE-003**: Corrupt cache entry treated as miss

Entries that fail to deserialize are treated as cache misses.

**Acceptance Criteria**:
- GIVEN a cache entry with corrupted data
- WHEN `get_versioned()` attempts to read it
- THEN None is returned (cache miss)
- AND a warning is logged
- AND the corrupt entry is invalidated

**Traceability**: Discovery Section G.3

---

**NFR-DEGRADE-004**: Operation succeeds even if caching fails

Core SDK operations succeed regardless of cache state.

**Acceptance Criteria**:
- GIVEN cache write fails (e.g., Redis full)
- WHEN `client.tasks.get_async("123")` completes
- THEN the Task is returned successfully
- AND a warning is logged about cache write failure
- AND no exception propagates

**Traceability**: Discovery Section G.3

---

### 4.4 Testability (NFR-TEST-*)

---

**NFR-TEST-001**: Unit tests use NullCacheProvider by default

Existing unit tests continue to use NullCacheProvider to avoid cache-related side effects.

**Acceptance Criteria**:
- GIVEN a unit test that does not specify cache configuration
- WHEN the test runs
- THEN NullCacheProvider is used
- AND test behavior is unchanged

---

**NFR-TEST-002**: Cache behavior testable via InMemoryCacheProvider

Tests can verify caching behavior using InMemoryCacheProvider without external dependencies.

**Acceptance Criteria**:
- GIVEN `client = AsanaClient(cache_provider=InMemoryCacheProvider())`
- WHEN cache behavior is tested
- THEN all cache operations work in-process
- AND no external Redis is required

---

**NFR-TEST-003**: Docker Compose available for Redis integration tests

Integration tests can use Docker Compose to spin up Redis for testing.

**Acceptance Criteria**:
- GIVEN `docker-compose.test.yml` with Redis service
- WHEN `REDIS_HOST=localhost pytest tests/integration/` runs
- THEN Redis-based tests execute successfully

---

---

## 5. Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Cache hit rate (warm workload) | >80% | `cache.get_metrics().hit_rate` |
| p99 cache hit latency | <5ms | Benchmark test |
| API calls reduction | >50% for repeated access patterns | Before/after monitoring |
| Zero breaking changes | 100% existing tests pass | CI pipeline |
| Memory usage (InMemory) | <100MB for 10k entries | Profiling |

---

## 6. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Cache invalidation race conditions | Medium | Medium | Invalidate aggressively; stale reads resolve at TTL |
| Memory growth (InMemory) | Low | Medium | max_size eviction enforced at 10k entries |
| Redis dependency in production | Low | High | Graceful degradation, InMemory fallback |
| Entity type detection failures | Low | Low | Default to generic TTL (300s) |
| Test suite disruption | Low | High | NullCacheProvider default for tests |

---

## 7. Dependencies

### 7.1 Internal Dependencies

| Component | Status | Notes |
|-----------|--------|-------|
| CacheProvider protocol | Implemented | `protocols/cache.py` |
| InMemoryCacheProvider | Implemented | `_defaults/cache.py` |
| RedisCacheProvider | Implemented | `cache/backends/redis.py` |
| TieredCacheProvider | Implemented | `cache/tiered.py` |
| CacheEntry, EntryType | Implemented | `cache/entry.py` |
| TTLSettings | Implemented | `cache/settings.py` |
| Entity type detection | Implemented | `models/business/detection/` |

### 7.2 External Dependencies

| Component | Required For | Notes |
|-----------|-------------|-------|
| redis Python package | RedisCacheProvider | Optional extra |
| boto3 | TieredCacheProvider (S3) | Optional extra |

---

## 8. Glossary

| Term | Definition |
|------|------------|
| Cache hit | Requested data found in cache and returned without API call |
| Cache miss | Requested data not in cache; API call required |
| TTL | Time-to-live; duration a cache entry remains valid |
| Invalidation | Removing or expiring a cache entry after mutation |
| EVENTUAL freshness | Trust TTL without version validation |
| STRICT freshness | Validate version against source before returning cached data |

---

## 9. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-22 | Requirements Analyst | Initial PRD based on Discovery |

---

## 10. Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | | | |
| Tech Lead | | | |
| QA Lead | | | |
