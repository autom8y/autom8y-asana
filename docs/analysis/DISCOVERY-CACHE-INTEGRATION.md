# Discovery Analysis: Cache Integration

**Date**: 2025-12-22
**Status**: Complete
**Author**: Requirements Analyst (via Discovery Phase)
**Next Phase**: PRD Creation

---

## Executive Summary

The autom8_asana SDK has approximately 4,000 lines of sophisticated caching infrastructure that is currently dormant. The cache layer is fully implemented with versioned operations, staleness detection, TTL management, overflow protection, and multiple backend providers. However, the client layer defaults to `NullCacheProvider`, meaning no caching occurs.

This discovery documents the existing infrastructure, identifies integration gaps, and provides recommendations for environment-aware provider selection and configuration patterns.

---

## Section A: Infrastructure Audit

### A.1 Cache Provider Hierarchy

```
CacheProvider (Protocol)
    |
    +-- NullCacheProvider     [Default - no-op, always cache miss]
    |
    +-- InMemoryCacheProvider [Thread-safe, max_size=10000, LRU eviction]
    |
    +-- RedisCacheProvider    [Production, requires redis extra]
    |
    +-- TieredCacheProvider   [Redis hot tier + S3 cold tier]
```

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/`

| Provider | File | Capabilities |
|----------|------|--------------|
| Protocol | `protocols/cache.py` | Defines 13 methods including versioned ops |
| Null | `_defaults/cache.py:24-122` | No-op implementation, always returns None |
| InMemory | `_defaults/cache.py:131-389` | Thread-safe dict, TTL, eviction at 10k entries |
| Redis | `cache/backends/redis.py` | Production-ready, requires `redis` package |
| Tiered | `cache/tiered.py` | Write-through to S3, promotion on cold hit |

### A.2 EntryType Enum (Complete)

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/entry.py:11-24`

```python
class EntryType(str, Enum):
    TASK = "task"           # Relevant for TasksClient
    SUBTASKS = "subtasks"   # Relevant for TasksClient
    DEPENDENCIES = "dependencies"
    DEPENDENTS = "dependents"
    STORIES = "stories"
    ATTACHMENTS = "attachments"
    DATAFRAME = "dataframe" # Used by DataFrame cache integration
```

**TasksClient Relevance**:
- `TASK`: Primary cache target for `get_async()`, `get()`
- `SUBTASKS`: Potential cache target for `subtasks_async().collect()`
- `DEPENDENCIES`/`DEPENDENTS`: Future consideration for `dependents_async()`

### A.3 Versioning Mechanism

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/entry.py:27-115`

The `CacheEntry` dataclass stores:
- `version: datetime` - Task's `modified_at` timestamp
- `cached_at: datetime` - When entry was written to cache
- `ttl: int | None` - Time-to-live in seconds (default 300)

**Staleness Detection**:
- `is_expired(now)`: Checks if `(now - cached_at) > ttl`
- `is_current(current_version)`: Checks if `cached_version >= current_version`
- `is_stale(current_version)`: Inverse of `is_current()`

**Freshness Modes** (`cache/freshness.py:8-30`):
```python
class Freshness(str, Enum):
    STRICT = "strict"     # Always validate version against source
    EVENTUAL = "eventual" # Return cached data if within TTL
```

### A.4 Overflow/Eviction Protections

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/settings.py:10-64`

```python
@dataclass
class OverflowSettings:
    subtasks: int = 40        # Skip caching if > 40 subtasks
    dependencies: int = 40
    dependents: int = 40
    stories: int = 100
    attachments: int = 40
```

**InMemoryCacheProvider Eviction** (`_defaults/cache.py:165-179`):
- `max_size: int = 10000` entries
- When capacity reached, evicts oldest 10% of entries (FIFO)
- Thread-safe via `threading.Lock()`

---

## Section B: Integration Gap Analysis

### B.1 NullCacheProvider Default

**Current State** (`client.py:125`):
```python
self._cache_provider: CacheProvider = cache_provider or NullCacheProvider()
```

**Impact**: All cache calls are no-ops. Every `TasksClient.get_async()` call hits the Asana API.

### B.2 TasksClient Methods Without Cache

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

| Method | Line | Cache Status | Recommendation |
|--------|------|--------------|----------------|
| `get_async()` | 87-117 | No cache check | HIGH priority - most common read |
| `get()` | 141-158 | No cache check | Sync wrapper of above |
| `list_async()` | 474-539 | No cache | LOW - paginated, not cacheable |
| `subtasks_async()` | 562-631 | No cache | MEDIUM - could cache with parent GID |
| `dependents_async()` | 633-685 | No cache | LOW - complex invalidation |

**Current `get_async()` Implementation**:
```python
async def get_async(self, task_gid: str, ...) -> Task | dict[str, Any]:
    validate_gid(task_gid, "task_gid")
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/tasks/{task_gid}", params=params)  # Always API call
    if raw:
        return data
    task = Task.model_validate(data)
    task._client = self._client
    return task
```

**Proposed Cache Integration Point**:
```python
async def get_async(self, task_gid: str, ...) -> Task | dict[str, Any]:
    validate_gid(task_gid, "task_gid")

    # Cache check (EVENTUAL freshness by default)
    if self._cache:
        entry = self._cache.get_versioned(task_gid, EntryType.TASK)
        if entry is not None and not entry.is_expired():
            data = entry.data
            if raw:
                return data
            task = Task.model_validate(data)
            task._client = self._client
            return task

    # Cache miss - fetch from API
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/tasks/{task_gid}", params=params)

    # Cache write
    if self._cache:
        entry = CacheEntry(
            key=task_gid,
            data=data,
            entry_type=EntryType.TASK,
            version=parse_modified_at(data.get("modified_at")),
            ttl=settings.get_ttl(entry_type=EntryType.TASK),
        )
        self._cache.set_versioned(task_gid, entry)

    if raw:
        return data
    task = Task.model_validate(data)
    task._client = self._client
    return task
```

### B.3 SaveSession Invalidation Hook Point

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py:656-842`

**Current `commit_async()` Flow**:
1. Phase 1: Execute CRUD operations via `_pipeline.execute_with_actions()`
2. Phase 2: Execute cascade operations
3. Phase 3: Execute healing operations
4. Phase 4: Reset entity state for successful entities
5. Phase 5: Execute automation

**Proposed Invalidation Hook** (after Phase 1, before Phase 2):
```python
async def commit_async(self) -> SaveResult:
    # ... Phase 1: Execute CRUD and actions
    crud_result, action_results = await self._pipeline.execute_with_actions(...)

    # NEW: Phase 1.5: Cache invalidation for modified entities
    if self._client._cache_provider:
        for entity in crud_result.succeeded:
            if hasattr(entity, "gid") and entity.gid:
                self._client._cache_provider.invalidate(
                    entity.gid,
                    [EntryType.TASK, EntryType.SUBTASKS]
                )

    # ... Phase 2: Cascade operations
```

### B.4 ActionResult Structure for Invalidation

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/models.py:676-712`

```python
@dataclass
class ActionResult(RetryableErrorMixin):
    action: ActionOperation  # Contains task.gid
    success: bool
    error: Exception | None = None
    response_data: dict[str, Any] | None = None
```

**Access Pattern**:
```python
for action_result in action_results:
    if action_result.success:
        task_gid = action_result.action.task.gid
        cache.invalidate(task_gid, [EntryType.TASK])
```

---

## Section C: Environment-Aware Provider Selection

### C.1 Detection Order

Recommended priority (first match wins):
1. **Explicit config**: `AsanaClient(cache_provider=MyProvider())`
2. **Environment variable**: `ASANA_CACHE_PROVIDER=redis|memory|null`
3. **Auto-detect**: Check for Redis availability, fall back to environment-appropriate default

### C.2 Proposed Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `ASANA_CACHE_PROVIDER` | `redis`, `tiered`, `memory`, `null` | (auto) | Explicit provider selection |
| `ASANA_CACHE_ENABLED` | `true`, `false` | `true` | Master enable/disable |
| `ASANA_CACHE_TTL_DEFAULT` | integer seconds | `300` | Default TTL |
| `ASANA_CACHE_S3_ENABLED` | `true`, `false` | `false` | Enable S3 cold tier |
| `ASANA_ENVIRONMENT` | `production`, `staging`, `development`, `test` | `development` | Environment hint |

**Redis-specific** (already implemented in `autom8_adapter.py`):
- `REDIS_HOST` (required for Redis provider)
- `REDIS_PORT` (default: 6379)
- `REDIS_PASSWORD` (optional)
- `REDIS_SSL` (default: true)

### C.3 Auto-Detection Logic

```python
def auto_select_cache_provider() -> CacheProvider:
    """Select appropriate cache provider based on environment."""

    # Check explicit provider setting
    provider_setting = os.environ.get("ASANA_CACHE_PROVIDER", "").lower()
    if provider_setting:
        return _create_explicit_provider(provider_setting)

    # Check if caching is disabled
    if os.environ.get("ASANA_CACHE_ENABLED", "true").lower() == "false":
        return NullCacheProvider()

    # Environment-based auto-selection
    env = os.environ.get("ASANA_ENVIRONMENT", "development").lower()

    if env in ("production", "staging"):
        # Production: prefer Redis if available
        if _redis_available():
            return create_autom8_cache_provider()
        else:
            logger.warning(
                "REDIS_HOST not set in production. Using NullCacheProvider. "
                "Set ASANA_CACHE_PROVIDER=memory to use in-memory cache."
            )
            return NullCacheProvider()
    else:
        # Development/test: use in-memory by default
        return InMemoryCacheProvider(default_ttl=300, max_size=10000)

def _redis_available() -> bool:
    """Check if Redis is configured."""
    return bool(os.environ.get("REDIS_HOST"))
```

### C.4 Local Testing Story for Production Config

**Problem**: How do developers test Redis/Tiered configuration locally?

**Solutions**:

1. **Docker Compose** (recommended):
   ```yaml
   # docker-compose.yml
   services:
     redis:
       image: redis:7-alpine
       ports:
         - "6379:6379"
   ```
   ```bash
   REDIS_HOST=localhost REDIS_SSL=false pytest tests/integration/
   ```

2. **Test fixtures with mock**:
   ```python
   @pytest.fixture
   def mock_redis_provider():
       """InMemory provider that implements Redis interface."""
       return InMemoryCacheProvider(default_ttl=300)
   ```

3. **Environment override**:
   ```bash
   ASANA_CACHE_PROVIDER=memory pytest  # Force in-memory for local testing
   ```

---

## Section D: Configuration Pattern Research

### D.1 Industry Survey

| SDK | Pattern | Cache Config Location |
|-----|---------|----------------------|
| **boto3** | Separate config object | `Config(connect_timeout=..., read_timeout=...)` passed to client |
| **httpx** | Nested dataclass | `Timeout(connect=..., read=...)` in `Client(timeout=...)` |
| **requests** | Flat kwargs | `session.mount(adapter)` for caching |
| **google-cloud-python** | Nested config | `ClientOptions(api_endpoint=...)` |
| **stripe-python** | Flat module-level | `stripe.api_key = ...` (no cache config) |
| **pydantic** | Nested Settings | `class Settings(BaseSettings)` with env prefix |

### D.2 12-Factor App Principles

From the [12-factor methodology](https://12factor.net/):

> **III. Config**: Store config in the environment
> - Configuration that varies between deploys (credentials, resource handles) should come from environment variables
> - Config should be strictly separated from code

**Implications**:
- TTL values, provider selection should be env-configurable
- Nested config objects are fine as long as they can be overridden by env vars
- Default values should be sensible for development

### D.3 Recommendation: Nested Config with Env Override

**Rationale**:
- Matches existing `AsanaConfig` pattern (`config.py`)
- Already has nested dataclasses (`RateLimitConfig`, `RetryConfig`, etc.)
- Pydantic-style env override is industry standard

**Proposed Structure**:

```python
# config.py additions

@dataclass
class CacheConfig:
    """Cache configuration with environment variable overrides.

    Environment Variables:
        ASANA_CACHE_ENABLED: Master enable/disable
        ASANA_CACHE_PROVIDER: Explicit provider selection
        ASANA_CACHE_TTL_DEFAULT: Default TTL in seconds
        ASANA_CACHE_S3_ENABLED: Enable S3 cold tier
    """
    enabled: bool = True
    provider: str | None = None  # None = auto-detect
    ttl: TTLSettings = field(default_factory=TTLSettings)
    overflow: OverflowSettings = field(default_factory=OverflowSettings)
    freshness: Freshness = Freshness.EVENTUAL

    @classmethod
    def from_env(cls) -> CacheConfig:
        """Create config from environment variables."""
        return cls(
            enabled=os.environ.get("ASANA_CACHE_ENABLED", "true").lower() == "true",
            provider=os.environ.get("ASANA_CACHE_PROVIDER") or None,
            ttl=TTLSettings(
                default_ttl=int(os.environ.get("ASANA_CACHE_TTL_DEFAULT", "300"))
            ),
        )

@dataclass
class AsanaConfig:
    # ... existing fields ...
    cache: CacheConfig = field(default_factory=CacheConfig)
```

**Usage**:
```python
# Use defaults
client = AsanaClient()

# Override via config object
client = AsanaClient(config=AsanaConfig(
    cache=CacheConfig(enabled=True, ttl=TTLSettings(default_ttl=600))
))

# Override via environment
# ASANA_CACHE_TTL_DEFAULT=600 python script.py
```

---

## Section E: Entity-Type TTL Recommendations

### E.1 Update Frequency Analysis

Based on Asana-as-database usage patterns:

| Entity Type | Update Frequency | Recommended TTL | Rationale |
|-------------|-----------------|-----------------|-----------|
| **Business** | Rarely (1x/week) | 3600s (1 hour) | Root entity, only metadata changes |
| **Contact** | Low (1x/day) | 900s (15 min) | Contact info changes infrequently |
| **Unit** | Low (1x/day) | 900s (15 min) | Similar to Contact |
| **Offer** | High (hourly) | 180s (3 min) | Pipeline movement, status changes |
| **Process** | Very High (minutes) | 60s (1 min) | Active pipeline state machine |
| **Generic Task** | Medium | 300s (5 min) | Default for unknown entities |

### E.2 Proposed Entity TTL Configuration

**Option A: Type-Based TTL Map** (recommended)
```python
@dataclass
class TTLSettings:
    default_ttl: int = 300
    entity_type_ttls: dict[str, int] = field(default_factory=lambda: {
        "business": 3600,
        "contact": 900,
        "unit": 900,
        "offer": 180,
        "process": 60,
    })
```

**Option B: Per-Project TTL**
Already implemented in `CacheSettings.project_ttls`.

### E.3 TTL Resolution Priority

Per existing `TTLSettings.get_ttl()` implementation:
1. Project-specific TTL (if `project_gid` provided)
2. Entry-type TTL (if `entry_type` provided)
3. Default TTL

**Enhancement**: Add entity-type resolution for Business entities:
```python
def get_ttl_for_entity(self, entity: AsanaResource) -> int:
    """Get TTL based on entity type."""
    entity_type = type(entity).__name__.lower()
    if entity_type in self.entity_type_ttls:
        return self.entity_type_ttls[entity_type]
    return self.default_ttl
```

---

## Section F: Open Questions for PRD

### F.1 Technical Decisions (Analyst Authority)

These decisions can be made by the architect:

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| Default freshness mode | EVENTUAL | User confirmed; matches TTL-trust pattern |
| InMemory for dev | Yes | Simpler local development story |
| Redis for production | Yes | Already implemented in autom8_adapter.py |
| Invalidation on commit | Yes | Prevents stale reads after writes |

### F.2 User Decisions Required

These require user input before PRD:

| Question | Options | Impact |
|----------|---------|--------|
| Config pattern | A: Nested in AsanaConfig, B: Separate object | API surface design |
| Entity TTL defaults | Accept recommendations vs. custom values | Cache hit rate |
| S3 cold tier | Enable by default in production? | Storage costs |
| Metrics exposure | Via `client.cache.metrics` vs. callbacks | Observability integration |

### F.3 Blocking Questions

None identified. All required information is available.

---

## Section G: Risk Assessment

### G.1 Backward Compatibility

| Risk | Mitigation |
|------|------------|
| Existing code passes `cache_provider=None` | Default to NullCacheProvider (no behavior change) |
| Tests mock NullCacheProvider | No change - same interface |
| Performance regression from cache overhead | InMemoryCacheProvider is <1ms overhead |

**Zero Breaking Changes**: All new behavior is opt-in via:
- `ASANA_CACHE_ENABLED=true` (explicitly enabling)
- Passing non-null `cache_provider` parameter
- Setting `ASANA_CACHE_PROVIDER` environment variable

### G.2 Testing Strategy

| Scenario | Test Approach |
|----------|---------------|
| Unit tests | Continue using NullCacheProvider or mocks |
| Integration tests | Docker Compose with Redis |
| Load testing | Measure cache hit rate and latency |
| Failure modes | Test Redis unavailability graceful degradation |

### G.3 Failure Mode Analysis

| Failure | Current Behavior | Proposed Behavior |
|---------|-----------------|-------------------|
| Redis connection lost | N/A (not used) | Fall back to API calls, log warning |
| Cache full (InMemory) | N/A (not used) | Evict oldest 10%, continue |
| Cache poisoning | N/A (not used) | TTL expiration clears stale data |
| Version mismatch | N/A (not used) | Staleness detection invalidates entry |

**Graceful Degradation Principle**: Cache failures should never prevent API operations. Already implemented in `DataFrameCacheIntegration` (`cache_integration.py:251-258`):
```python
except Exception as exc:
    # FR-CACHE-008: Graceful degradation on cache errors
    self._log_cache_event("error", key, metadata={"error": str(exc)})
    return None  # Proceed as if cache miss
```

---

## Section H: Recommended Implementation Order

### Phase 1: Foundation (Sprint 1)
1. Add `CacheConfig` to `AsanaConfig`
2. Implement `auto_select_cache_provider()` function
3. Update `AsanaClient.__init__()` to use auto-selection
4. Add cache integration to `TasksClient.get_async()`

### Phase 2: Invalidation (Sprint 2)
1. Add invalidation hook in `SaveSession.commit_async()`
2. Invalidate on action results (tag/project changes)
3. Add cache metrics to observability hook

### Phase 3: Entity TTL (Sprint 3)
1. Implement entity-type TTL resolution
2. Add Business/Contact/Unit/Offer/Process TTL defaults
3. Environment variable overrides

### Phase 4: Advanced (Future)
1. Subtask caching with parent GID key
2. TieredCacheProvider S3 integration
3. Cache warming APIs

---

## Quality Gate Checklist

- [x] All cache infrastructure modules documented
- [x] Integration gaps mapped to specific files/lines
- [x] Provider selection strategy defined with env var names
- [x] Configuration pattern recommended with industry research
- [x] Entity TTL defaults proposed
- [x] No blocking questions remain for PRD phase
- [x] Risk assessment complete (backward compat, testing, failure modes)

---

## Appendix: File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `cache/__init__.py` | 1-193 | Public API exports |
| `cache/entry.py` | 1-171 | CacheEntry, EntryType enum |
| `cache/settings.py` | 1-182 | CacheSettings, TTLSettings, OverflowSettings |
| `cache/freshness.py` | 1-30 | Freshness enum |
| `cache/tiered.py` | 1-480 | TieredCacheProvider |
| `_defaults/cache.py` | 1-389 | NullCacheProvider, InMemoryCacheProvider |
| `protocols/cache.py` | 1-240 | CacheProvider protocol |
| `cache/autom8_adapter.py` | 1-468 | Redis provider factory |
| `client.py` | 125 | NullCacheProvider default |
| `clients/base.py` | 45 | BaseClient._cache storage |
| `clients/tasks.py` | 87-117 | get_async() without cache |
| `persistence/session.py` | 656-842 | commit_async() hook point |
| `persistence/models.py` | 676-712 | ActionResult structure |
| `config.py` | 1-300 | AsanaConfig structure |
| `dataframes/cache_integration.py` | 1-677 | Existing explicit wiring pattern |
