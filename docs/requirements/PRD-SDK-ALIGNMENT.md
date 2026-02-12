# PRD: autom8_asana SDK Alignment & Operational Visibility

**PRD ID**: PRD-SDK-ALIGNMENT
**Version**: 1.0
**Date**: 2026-02-05
**Author**: Requirements Analyst
**Status**: DRAFT
**Initiative**: Initiative 3 -- autom8_asana SDK Alignment & Operational Visibility
**Task**: task-301

```yaml
impact: high
impact_categories: [security, api_contract]
```

---

## Executive Summary

This PRD scopes the exact changes required to align autom8_asana with the autom8y SDK ecosystem across three migration paths:

1. **Settings Migration** -- Migrate 8 settings classes from plain `pydantic.BaseSettings` to `Autom8yBaseSettings`, introduce `SecretStr` for `ASANA_PAT` and `REDIS_PASSWORD`, and verify compatibility with the `ConfigTranslator` transport layer.

2. **DataFrame Cache Disposition** -- After analysis of three convergence options, this PRD recommends **Option A: Intentionally Separate** with a documented revisit trigger. The autom8_asana DataFrame cache is a domain-specific subsystem (Polars DataFrames, watermark-based freshness, section persistence, build coordination, circuit breakers) that shares the caching *concept* but not the caching *contract* with the SDK's `CacheProvider` protocol. Convergence via adapter (Option B) gains observability metrics at the cost of impedance mismatch (sync protocol over async operations); full convergence (Option C) is not viable.

3. **Observability & Metrics** -- A dual-strategy approach: `autom8y-telemetry` with Prometheus for the ECS FastAPI service (already adopted via `instrument_app()`), and CloudWatch custom metrics for Lambda handlers (already implemented). The remaining gap is domain-specific business metrics (sync duration, cache hit rates, entity counts) that should be emitted as Prometheus gauges/histograms from the ECS service and as CloudWatch metrics from Lambda handlers.

---

## Background

### Prior Work

- **Sprint 1**: Gap inventory (`/Users/tomtenuta/Code/autom8y/docs/requirements/SDK-ADOPTION-GAP-INVENTORY.md`) identified autom8_asana's config/secrets as a Rank 4 migration path.
- **Sprint 1**: Migration guide PRD (`/Users/tomtenuta/Code/autom8y/docs/requirements/PRD-SDK-MIGRATION-GUIDE.md`) scoped Migration Path 4 for autom8_asana config/secrets at a high level.
- **Sprint 2**: autom8_data completed its config/secrets migration (base class swap + SecretStr), establishing the pattern.
- **autom8_asana transport layer**: The `ConfigTranslator` at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/config_translator.py` is the "success pattern" for SDK adoption -- pure function mapping from domain config to SDK primitives.

### The Success Pattern: ConfigTranslator

autom8_asana's transport layer demonstrates proven SDK integration. The `ConfigTranslator` class (lines 34-163 of `config_translator.py`) provides four static methods that map domain configuration dataclasses to SDK primitives:

| Method | Domain Source | SDK Target |
|--------|-------------|------------|
| `to_http_client_config()` | `AsanaConfig` | `HttpClientConfig` |
| `to_rate_limiter_config()` | `AsanaConfig.rate_limit` | `PlatformRateLimiterConfig` |
| `to_retry_config()` | `AsanaConfig.retry` | `PlatformRetryConfig` |
| `to_circuit_breaker_config()` | `AsanaConfig.circuit_breaker` | `PlatformCircuitBreakerConfig` |

This pattern works because it:
- Preserves domain vocabulary (the satellite never speaks SDK vocabulary in its own code)
- Is explicit, auditable, and side-effect-free
- Allows the satellite and SDK to evolve independently

The settings migration (Path 1) and observability (Path 3) should follow this same principle: adopt SDK infrastructure without contaminating domain logic.

---

## Migration Path 1: Settings to Autom8yBaseSettings

### Current State

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py`

Eight settings classes, all extending plain `pydantic_settings.BaseSettings`:

| Class | Lines | `env_prefix` | Purpose |
|-------|-------|-------------|---------|
| `AsanaSettings` | 78-108 | `ASANA_` | Core API config (PAT, workspace, base URL) |
| `CacheSettings` | 111-233 | `ASANA_CACHE_` | Cache TTL, provider selection, DataFrame limits |
| `RedisSettings` | 271-321 | `REDIS_` | Redis connection (host, port, password, SSL) |
| `EnvironmentSettings` | 324-356 | `ASANA_` | Environment detection (dev/prod/staging/test) |
| `S3Settings` | 359-388 | `ASANA_CACHE_S3_` | S3 cache backend (bucket, prefix, region, endpoint) |
| `PacingSettings` | 391-448 | `ASANA_PACING_` | Large fetch pacing (pages, delays, checkpoints) |
| `S3RetrySettings` | 451-529 | `ASANA_S3_` | S3 retry/circuit breaker config |
| `ProjectOverrideSettings` | 532-601 | (none) | Validation-only for ASANA_PROJECT_* env vars |

**Root composite**: `Settings` class (lines 604-655) aggregates all subsettings via `default_factory` pattern.

**Singleton pattern**: Module-level `_settings` with `get_settings()` / `reset_settings()` (lines 657-697).

### Secret-Bearing Fields

| Class | Field | Line | Current Type | Risk |
|-------|-------|------|-------------|------|
| `AsanaSettings` | `pat` | 100 | `str \| None` | Asana Personal Access Token -- leaked in repr/logging |
| `RedisSettings` | `password` | 302 | `str \| None` | Redis auth password -- leaked in repr/logging |

### Nested Settings Pattern -- Friction Analysis

autom8_asana uses a **composition via `default_factory`** pattern where the root `Settings` class instantiates each subsetting class independently:

```python
class Settings(BaseSettings):
    asana: AsanaSettings = Field(default_factory=AsanaSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    # ...
```

Each subsetting class has its own `model_config` with a distinct `env_prefix`. This is **different** from Pydantic's nested model pattern (which uses `env_nested_delimiter` to parse `PARENT__CHILD__FIELD`). Here, each subsetting reads its own env vars directly.

**Friction point**: `Autom8yBaseSettings` sets `env_nested_delimiter="__"` in its `model_config`. When a subsetting class inherits from `Autom8yBaseSettings`, Pydantic merges model_config with child taking precedence. Since each subsetting explicitly sets its own `env_prefix`, the `env_nested_delimiter` from the parent is additive, not conflicting. However, this must be verified per-class.

**Friction point**: `Autom8yBaseSettings` has a `model_validator(mode="before")` called `_resolve_secret_uris` that runs on raw field values. Since each subsetting is instantiated independently (via `default_factory`), the resolver runs on each subsetting class individually. This is the desired behavior -- secrets in any subsetting are resolved.

**Friction point**: The root `Settings` class has **no `env_prefix`**. If it inherits from `Autom8yBaseSettings`, the resolver will attempt to resolve secret URIs in the subsetting model dicts. Since subsettings are dicts at the "before" validation stage, `_resolve_secrets_recursive` handles this correctly (it recurses into dicts). No friction here.

### ConfigTranslator / Transport Layer Impact

The `ConfigTranslator` at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/config_translator.py` does **not** consume `settings.py` directly. It consumes `config.py` domain dataclasses (`AsanaConfig`, `RateLimitConfig`, etc.). The settings-to-config translation happens elsewhere (in `config.py` and client initialization).

The `autom8_adapter.py` at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/autom8_adapter.py` **does** consume `settings.py` directly:

- Line 133: `redis_settings = sdk_settings.redis`
- Line 144: `password = redis_password if redis_password is not None else redis_settings.password`

If `redis_settings.password` becomes `SecretStr`, line 144 will pass a `SecretStr` object to `RedisConfig.password` (which expects `str | None`). **This is a breaking change that must be addressed**: either `RedisConfig` accepts `SecretStr`, or the adapter calls `.get_secret_value()`.

Similarly, the `EnvironmentAuthProvider` at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/_defaults/auth.py`:

- Line 57: `if key == "ASANA_PAT" and settings.asana.pat:`
- Line 59: `if not settings.asana.pat.strip():`
- Line 63: `return settings.asana.pat`

If `settings.asana.pat` becomes `SecretStr`, the `.strip()` call (line 59) fails because `SecretStr` does not have a `.strip()` method. The return on line 63 returns a `SecretStr` object, but `get_secret()` returns `str`. **Both lines must be updated to use `.get_secret_value()`.**

The Redis connection code at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/connections/redis.py` line 208 and `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py` line 166 both pass `self._config.password` to the Redis client. These consume `RedisConfig` (a dataclass in the cache module), not `RedisSettings` directly. The pathway is: `settings.redis.password` -> `RedisConfig.password` -> redis client. If `RedisConfig.password` receives a `SecretStr`, the redis client will fail. The fix is to call `.get_secret_value()` at the settings-to-config translation boundary.

### Migration Steps

**Stage 1: Base Class Swap**

1. Add `autom8y-config` as a dependency in `pyproject.toml`
2. Change all 8 subsetting classes to inherit from `Autom8yBaseSettings` instead of `BaseSettings`
3. Change root `Settings` class to inherit from `Autom8yBaseSettings`
4. Verify each class's `model_config` merges correctly with parent (child `env_prefix` takes precedence)
5. Verify `get_settings()` / `reset_settings()` singleton works (module-level pattern is independent of base class)
6. Verify `ProjectOverrideSettings.validate_project_overrides` model_validator still fires (it uses `mode="after"`, which runs after `Autom8yBaseSettings._resolve_secret_uris` `mode="before"`)

**Stage 2: SecretStr for Credential Fields**

| Class | Field | Change | Downstream Fixes Required |
|-------|-------|--------|--------------------------|
| `AsanaSettings` | `pat` | `str \| None` -> `SecretStr \| None` | `_defaults/auth.py` lines 57-63: use `.get_secret_value()` |
| `RedisSettings` | `password` | `str \| None` -> `SecretStr \| None` | `autom8_adapter.py` line 144: use `.get_secret_value()` |

Additional downstream fixes:
- Any code that passes `settings.asana.pat` to a string context (beyond `EnvironmentAuthProvider`) must use `.get_secret_value()`
- Any code that passes `settings.redis.password` to a Redis client config must use `.get_secret_value()`
- The `BotPATProvider` (if it accesses `settings.asana.pat` directly) must be checked

**Stage 3: SSM/SecretsManager Integration (Future)**

Zero code changes after Stage 1. Env var values change from:
```
ASANA_PAT=xoxp-12345
```
to:
```
ASANA_PAT=ssm:///prod/asana-pat
```

`Autom8yBaseSettings._resolve_secret_uris` handles resolution automatically.

### Acceptance Criteria -- Path 1

- [ ] AC-1.1: All 8 subsetting classes + root `Settings` inherit from `Autom8yBaseSettings`
- [ ] AC-1.2: `to_safe_dict()` on root `Settings` returns `***REDACTED***` for `asana.pat` and `redis.password`
- [ ] AC-1.3: `EnvironmentAuthProvider.get_secret("ASANA_PAT")` returns raw string value (not `SecretStr` wrapper)
- [ ] AC-1.4: `create_autom8_cache_provider()` creates Redis connection with raw password string
- [ ] AC-1.5: `reset_settings()` / `get_settings()` singleton pattern works with `Autom8yBaseSettings`
- [ ] AC-1.6: All existing tests pass without modification (aside from type assertions on `pat`/`password` fields)
- [ ] AC-1.7: Lambda cold start time delta < 50ms (verify: `_resolve_secret_uris` with no `ssm://` URIs is a string prefix check only)
- [ ] AC-1.8: `CacheSettings.parse_ttl_with_fallback` field_validator and `RedisSettings.parse_ssl` field_validator continue to work (these use `mode="before"`, same as `_resolve_secret_uris` -- Pydantic runs class validators in definition order, so parent's `_resolve_secret_uris` runs before child's field validators)
- [ ] AC-1.9: `ProjectOverrideSettings.validate_project_overrides` model_validator (`mode="after"`) fires correctly

---

## Migration Path 2: DataFrame Cache Disposition

### The Decision

The user requires an "intentional, future-proofed" decision about the relationship between autom8_asana's DataFrame cache and the SDK's `autom8y-cache` `TieredCacheProvider`. Three options were evaluated.

### Current Architecture

The autom8_asana DataFrame cache is a domain-specific subsystem spanning multiple files:

| Component | File | Purpose |
|-----------|------|---------|
| `DataFrameCache` | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/dataframe_cache.py` (lines 160-956) | Unified cache coordinating Memory + Progressive tiers, SWR, circuit breaker |
| `MemoryTier` | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/memory.py` (lines 60-268) | In-memory hot cache with LRU eviction, heap-based limits, thread-safe |
| `ProgressiveTier` | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/progressive.py` (lines 39-358) | S3 cold storage via SectionPersistence, async reads/writes |
| `DataFrameCacheEntry` | `dataframe_cache.py` (lines 73-157) | Entry holding `pl.DataFrame`, watermark, schema_version, build_quality |
| `DataFrameCacheCoalescer` | `cache/dataframe/coalescer.py` | Request deduplication for concurrent identical builds |
| `CircuitBreaker` | `cache/dataframe/circuit_breaker.py` | Per-project failure isolation |
| `autom8_adapter.py` | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/autom8_adapter.py` | Bridges cache to external Redis consumers (key-value, NOT DataFrame) |

### SDK TieredCacheProvider Architecture

**File**: `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/tiered.py`

The SDK's `TieredCacheProvider` (lines 39-471) coordinates a hot tier (Redis/InMemory) and cold tier (S3) for `dict[str, Any]` values:

- **Protocol**: `CacheProvider` -- synchronous `get()`/`set()`/`delete()` + versioned ops
- **Data format**: `dict[str, Any]` (JSON-serializable)
- **Tiered strategy**: Cache-aside with promotion, write-through
- **Metrics**: `CacheMetrics` with hits/misses/promotions

### Option A: Intentionally Separate (RECOMMENDED)

**Keep the DataFrame cache as a domain-specific subsystem. Document the boundary and define when to revisit.**

**Technical rationale**:

1. **Data format impedance**: The SDK caches `dict[str, Any]` via the `CacheProvider` protocol (line 86 of `protocols/cache.py`: `def get(self, key: str) -> dict[str, Any] | None`). The DataFrame cache stores `pl.DataFrame` objects with `estimated_size()` for memory management (line 267 of `memory.py`). Converting DataFrames to dicts for SDK storage and back would lose schema information, watermark semantics, and memory estimation.

2. **Async/sync impedance**: The SDK `CacheProvider` protocol is entirely synchronous. The DataFrame cache's `ProgressiveTier` is entirely async (`get_async`, `put_async` -- lines 105, 206 of `progressive.py`). Wrapping async in sync (or vice versa) adds complexity and defeats the purpose of async I/O for S3 operations.

3. **Build coordination has no SDK analog**: The DataFrame cache coordinates multi-page section fetches via `DataFrameCacheCoalescer` and `CircuitBreaker`. These prevent duplicate builds when multiple concurrent requests need the same DataFrame. The SDK has no concept of "building" a cache entry from multiple API calls.

4. **Invalidation semantics differ**: The DataFrame cache invalidates by entity type + project GID + schema version (lines 573-636 of `dataframe_cache.py`). The SDK invalidates by key + entry type. Section-level invalidation, schema version bumps, and watermark-based freshness have no SDK equivalents.

5. **The existing `autom8_adapter.py` already bridges the boundary**: For key-value caching (task staleness checks, Redis-backed task metadata), `autom8_adapter.py` provides a `CacheProvider`-compatible interface via `create_autom8_cache_provider()`. This is the right integration surface -- simple key-value goes through SDK patterns, domain-specific DataFrame caching stays separate.

**What is gained**: Clean domain boundary. No migration risk. No test disruption. The DataFrame cache subsystem has extensive LocalStack S3 integration tests that would need rewriting under convergence.

**What is lost**: No SDK-level observability (CacheMetrics) for DataFrame cache operations. However, the DataFrame cache already has its own per-entity-type statistics (line 707-709 of `dataframe_cache.py`: `get_stats() -> dict[str, dict[str, int]]`) and the `ProgressiveTier` tracks reads/writes/errors/bytes independently (lines 335-342 of `progressive.py`).

**Revisit trigger**: Revisit this decision if the SDK adds:
- `SerializerProtocol` supporting pluggable binary serialization (DataFrame-aware)
- Async `CacheProvider` variant
- Build coordination / request coalescing as SDK-level utilities
- Section-aware invalidation strategies

**Effort**: None. Document the rationale.

### Option B: Converge via Adapter

**Make `DataFrameCache` implement the `CacheProvider` protocol as an adapter, gaining SDK observability.**

**Technical feasibility**: Partially viable. The adapter would need to:
- Serialize `pl.DataFrame` to `dict[str, Any]` for `get()` (losing type safety)
- Map cache keys from `"{entity_type}:{project_gid}"` to `CacheProvider`'s flat key space
- Wrap async operations in sync (since `CacheProvider` is sync)
- Fake or ignore versioned operations (`get_versioned`, `set_versioned`) that don't map to watermark-based freshness

**What is gained**: `CacheMetrics` integration, ability to use SDK cache middleware or monitoring.

**What is lost**: Type safety (DataFrames become dicts), async performance (forced sync), increased complexity in the adapter layer. The impedance mismatch would create a leaky abstraction where consumers must know whether they are getting a dict or a DataFrame.

**Impact on tests**: Existing LocalStack S3 integration tests (which test `ProgressiveTier` directly) would not be affected by the adapter itself, but any code path that uses the adapter instead of `DataFrameCache` directly would need new tests.

**Effort**: MEDIUM -- 2-3 days to build adapter, write tests, wire into existing code.

**Assessment**: The juice is not worth the squeeze. The adapter would be a wrapper that adds complexity without solving any actual problem. The DataFrame cache already has comprehensive statistics.

### Option C: Full Convergence

**Migrate entirely to `TieredCacheProvider` with a custom serializer.**

**Technical feasibility**: Not viable.

1. `TieredCacheProvider` stores `dict[str, Any]` values. Polars DataFrames cannot be losslessly round-tripped through JSON. Binary serialization (Parquet, Arrow IPC) is required for schema preservation.

2. `TieredCacheProvider` uses `CacheEntry` (from `autom8y-cache`) which has `data: dict[str, Any]`, `version: datetime`, `ttl: int | None`. The DataFrame cache's `DataFrameCacheEntry` has `dataframe: pl.DataFrame`, `watermark: datetime`, `schema_version: str`, `build_quality: Any` -- fundamentally different shape.

3. `TieredCacheProvider.from_env()` creates Redis + S3 backends. The DataFrame cache's cold tier is not generic S3 -- it uses `SectionPersistence` which reads/writes to a specific S3 key structure (`dataframes/{project_gid}/`) with watermark files, manifest files, and section-level granularity.

4. Build coordination, request coalescing, and per-project circuit breaking would all need to be reimplemented outside the SDK, negating the benefit of using the SDK in the first place.

**What is gained**: Single caching abstraction across the platform.

**What is lost**: All domain-specific caching intelligence. Massive migration effort. Risk of regression in the cache warmer (Lambda), cache preload (ECS startup), and all API endpoints that serve DataFrames.

**Impact on tests**: All DataFrame cache tests (unit and integration) would need to be rewritten. The LocalStack S3 integration test suite tests `SectionPersistence` key structures that would not exist under `TieredCacheProvider`.

**Effort**: HIGH -- 2+ weeks, high risk.

**Assessment**: Not viable. The cost-benefit is strongly negative.

### Recommendation: Option A -- Intentionally Separate

The DataFrame cache is a domain subsystem, not a generic caching layer. The boundary is already clean:

- **Generic key-value caching** (task staleness, metadata): Goes through `autom8_adapter.py` -> Redis via `RedisCacheProvider` -> compatible with SDK patterns
- **Domain DataFrame caching** (entity resolution data): Goes through `DataFrameCache` -> Memory + Progressive (S3 via SectionPersistence) -> domain-specific, intentionally separate

This is the correct architecture. Document it as an ADR.

### Acceptance Criteria -- Path 2

- [ ] AC-2.1: ADR document produced with rationale for intentional separation
- [ ] AC-2.2: Revisit triggers documented (SerializerProtocol, async CacheProvider, SDK build coordination)
- [ ] AC-2.3: Boundary documented: key-value via SDK patterns, DataFrame via domain cache
- [ ] AC-2.4: No code changes required (documentation-only deliverable)

---

## Migration Path 3: Observability & Metrics

### Current Observability Landscape

autom8_asana runs in two distinct compute contexts with different observability characteristics:

#### ECS FastAPI Service

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py`

Already instrumented with `autom8y-telemetry` (lines 102-121):

```python
from autom8y_telemetry import InstrumentationConfig, instrument_app
instrument_app(app, InstrumentationConfig(service_name="asana"))
```

This provides:
- `autom8y_http_request_duration_seconds` Histogram (labels: service, method, path, status)
- `autom8y_http_requests_total` Counter (same labels)
- `autom8y_http_requests_in_flight` Gauge (label: service)
- `/metrics` endpoint for Prometheus scraping
- Optional OpenTelemetry tracing and log correlation

**What is missing**: Domain-specific business metrics. The platform observability covers HTTP request flow but not:
- Sync/build duration per entity type
- DataFrame cache hit/miss rates per entity type
- Entity counts per project after build
- Asana API call count and latency (via transport layer)
- SWR background refresh frequency and success rate

#### Lambda Handlers

**Files**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_warmer.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_invalidate.py`

Already instrumented with CloudWatch custom metrics (lines 191-243 of `cache_warmer.py`):

```python
def _emit_metric(metric_name, value, unit="Count", dimensions=None):
    client.put_metric_data(Namespace=CLOUDWATCH_NAMESPACE, ...)
```

Existing metrics emitted by `cache_warmer.py`:
- `WarmSuccess` (Counter, per entity_type)
- `WarmFailure` (Counter, per entity_type)
- `WarmDuration` (Milliseconds, per entity_type)
- `RowsWarmed` (Count, per entity_type)
- `TotalDuration` (Milliseconds)
- `CheckpointSaved`, `CheckpointResumed`, `SelfContinuationInvoked` (operational)

`cache_invalidate.py` has no metric emission currently.

### Evaluation: Lambda vs ECS Approach

| Dimension | Lambda (cache_warmer, cache_invalidate) | ECS (FastAPI API) |
|-----------|----------------------------------------|-------------------|
| Execution model | Ephemeral, cold starts, 15min max | Long-running, persistent process |
| Natural metrics target | CloudWatch (boto3 PutMetricData) | Prometheus (scrape endpoint) |
| Prometheus viability | Requires push gateway -- adds infra, latency | Native via `/metrics` endpoint (already exists) |
| autom8y-telemetry viability | Over-engineered for ephemeral functions | Already adopted (`instrument_app()`) |
| CloudWatch viability | Native, zero infra overhead | Redundant (Prometheus already scrapes) |

**Conclusion**: Lambda and ECS SHOULD use different approaches. This is not an inconsistency -- it reflects the execution model.

- **Lambda**: Continue with CloudWatch custom metrics via `_emit_metric()`. This is the existing pattern, works well, and avoids adding push gateway infrastructure.
- **ECS**: Use Prometheus via `autom8y-telemetry` for HTTP metrics (already done) and add domain-specific Prometheus metrics for business observability.

### Proposed Domain Metrics (ECS)

These should be registered as Prometheus metrics in a new module and exposed via the existing `/metrics` endpoint:

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `asana_dataframe_build_duration_seconds` | Histogram | `entity_type`, `project_gid` | DataFrameCache.put_async timing |
| `asana_dataframe_cache_operations_total` | Counter | `entity_type`, `tier` (memory/s3), `result` (hit/miss/error) | DataFrameCache.get_async flow |
| `asana_dataframe_rows_cached` | Gauge | `entity_type` | DataFrameCache.put_async row_count |
| `asana_dataframe_swr_refreshes_total` | Counter | `entity_type`, `result` (success/failure) | DataFrameCache._swr_refresh_async |
| `asana_dataframe_circuit_breaker_state` | Gauge | `project_gid` | CircuitBreaker state (0=closed, 1=open, 2=half_open) |
| `asana_api_calls_total` | Counter | `method`, `path`, `status_code` | Transport layer / Autom8yHttpClient |
| `asana_api_call_duration_seconds` | Histogram | `method`, `path` | Transport layer timing |

### Proposed Domain Metrics (Lambda)

Extend the existing `_emit_metric()` pattern in `cache_invalidate.py`:

| Metric | Unit | Dimensions | Trigger |
|--------|------|-----------|---------|
| `InvalidateSuccess` | Count | `type` (tasks/dataframes) | Successful invalidation |
| `InvalidateFailure` | Count | `type` (tasks/dataframes) | Failed invalidation |
| `InvalidateDuration` | Milliseconds | (none) | Total execution time |
| `KeysCleared` | Count | `tier` (redis/s3) | Per-tier clear count |

### autom8y-telemetry Suitability

`autom8y-telemetry` (at `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-telemetry/`) provides:

1. **`instrument_app()`** (lines 23-105 of `instrument.py`): One-liner FastAPI setup for HTTP request metrics, `/metrics` endpoint, tracing, log correlation. **Already adopted by autom8_asana** (line 105 of `main.py`).

2. **`get_or_create_metrics()`** (lines 27-72 of `metrics.py`): Creates standard HTTP metrics (`autom8y_http_*`). These are generic HTTP metrics, not domain-specific.

3. **`TelemetryConfig`** (lines 15-133 of `config.py`): OpenTelemetry configuration with OTEL_* env var support.

4. **`InstrumentationConfig`** (lines 13-46 of `fastapi/config.py`): Controls `instrument_app()` behavior (service name, excluded paths, histogram buckets, tracing toggle).

**Assessment for ECS**: `autom8y-telemetry` is appropriate for HTTP-level metrics and is already in place. Domain-specific metrics (DataFrame build duration, cache hit rates, entity counts) should be registered directly with `prometheus_client` in a new `autom8_asana/api/metrics.py` module. The `/metrics` endpoint (provided by `instrument_app()`) will serve both SDK and domain metrics from the same Prometheus registry.

**Assessment for Lambda**: `autom8y-telemetry` is NOT appropriate for Lambda handlers. `instrument_app()` requires a FastAPI app. The tracing and metrics infrastructure assumes a long-running process with a scrape endpoint. Lambda handlers should continue using CloudWatch via `_emit_metric()`.

### Implementation Approach

**New file**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/metrics.py`

This module should:
1. Define domain-specific Prometheus metrics using `prometheus_client` directly
2. Provide helper functions for recording metrics from domain code
3. Be imported during app startup to register metrics before first scrape
4. Use the same `prometheus_client.REGISTRY` that `autom8y-telemetry` uses (default registry)

**Integration points** (no changes to autom8y-telemetry needed):
- `DataFrameCache.put_async()`: Record build duration and row count after successful write
- `DataFrameCache.get_async()`: Record cache hit/miss per tier
- `DataFrameCache._swr_refresh_async()`: Record SWR refresh outcomes
- Transport layer (Autom8yHttpClient): Record API call count and latency (likely via the existing callback/hook mechanism)

**For cache_invalidate.py**: Add `_emit_metric()` calls at existing logging points (lines 132-143, 155-173).

### Acceptance Criteria -- Path 3

- [ ] AC-3.1: New `api/metrics.py` module defines domain Prometheus metrics (build duration, cache ops, SWR, entity counts)
- [ ] AC-3.2: `/metrics` endpoint serves both `autom8y_http_*` (SDK) and `asana_*` (domain) metrics
- [ ] AC-3.3: `cache_invalidate.py` emits CloudWatch metrics (`InvalidateSuccess`, `InvalidateFailure`, `InvalidateDuration`)
- [ ] AC-3.4: Domain metrics have appropriate labels (entity_type, tier, result) for Grafana dashboarding
- [ ] AC-3.5: No Prometheus push gateway infrastructure required for Lambda
- [ ] AC-3.6: `instrument_app()` continues to work unmodified (domain metrics are additive)

---

## Constraints & Non-Goals

### Constraints

1. **ConfigTranslator boundary**: The `ConfigTranslator` pattern must remain clean. Settings changes (Path 1) affect the settings -> config translation boundary. The config -> SDK translation (ConfigTranslator) is unaffected.

2. **Lambda cold start budget**: Any import added to settings.py increases Lambda cold start time. `Autom8yBaseSettings` imports `SecretResolver`, which lazily imports boto3 only when `ssm://` or `secretsmanager://` URIs are encountered. With env-var-only secrets, the overhead is a string prefix check per field value.

3. **Existing test suite**: autom8_asana has extensive tests, including LocalStack S3 integration tests for the DataFrame cache. Path 2 (cache disposition) must not require test changes.

4. **Observability budget**: Domain Prometheus metrics (Path 3) must not degrade API latency. All metric recording should be fire-and-forget with no synchronous I/O. Prometheus client library operations are in-memory counters/histograms, so this is inherent.

5. **`env_prefix` diversity**: The 8 settings classes use 6 different `env_prefix` values (`ASANA_`, `ASANA_CACHE_`, `REDIS_`, `ASANA_PACING_`, `ASANA_S3_`, `ASANA_CACHE_S3_`). Each must be tested individually after base class swap.

### Non-Goals

| Item | Reason |
|------|--------|
| Migrate DataFrame cache to SDK `TieredCacheProvider` | Option C rejected; domain-specific concerns |
| Add Prometheus push gateway for Lambda | Over-engineered; CloudWatch is natural for Lambda |
| Replace CloudWatch metrics in cache_warmer with Prometheus | Would require push gateway infra |
| Migrate `autom8_adapter.py` Redis cache to SDK `autom8y-cache` | Already serves its purpose; different concern than DataFrame cache |
| Add tracing spans to DataFrame cache | Out of scope for this initiative; consider in future observability sprint |
| Migrate `config.py` domain dataclasses to Pydantic settings | Domain dataclasses are intentionally separate from env-var-loaded settings |
| Remove `PacingSettings` or `S3RetrySettings` | These are valid operational knobs; not dead code |

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| `model_config` merge conflict between `Autom8yBaseSettings` and subsetting `env_prefix` | Low | Medium | Test each of 8 classes individually; Pydantic docs confirm child precedence |
| `SecretStr` propagation breaks Redis connection | Medium | High | Identify all `.password` consumers before migration; add `.get_secret_value()` at translation boundaries |
| `SecretStr` breaks `EnvironmentAuthProvider.get_secret()` | High (certain) | High | Lines 57-63 of `_defaults/auth.py` must be updated; this is known and scoped |
| Lambda cold start regression from `Autom8yBaseSettings` import | Low | Medium | `SecretResolver.__init__` is cheap; boto3 import is lazy; benchmark with `time.monotonic()` before/after |
| Domain Prometheus metrics create label cardinality explosion | Low | Medium | Limit `project_gid` label to top-N projects or use histogram without project dimension |
| `_resolve_secret_uris` validator order conflict with `CacheSettings.parse_ttl_with_fallback` | Low | Low | Both use `mode="before"`; Pydantic runs class validators before field validators; parent's model_validator runs before child's field_validator |

---

## User Stories

**US-1**: As a platform engineer, I want autom8_asana settings to inherit from `Autom8yBaseSettings` so that `to_safe_dict()` prevents credential leakage in logs and SSM/SecretsManager integration is available when infrastructure supports it.

**US-2**: As an SRE, I want the DataFrame cache separation documented with clear rationale so that there is no ambiguity about convergence expectations and future teams know when to revisit.

**US-3**: As an SRE, I want domain-specific Prometheus metrics (build duration, cache hit rates, entity counts) exposed on the existing `/metrics` endpoint so that I can build Grafana dashboards for autom8_asana operational health.

**US-4**: As an SRE, I want `cache_invalidate.py` to emit CloudWatch metrics so that invalidation operations are visible in CloudWatch dashboards alongside existing `cache_warmer` metrics.

---

## Priority (MoSCoW)

| Requirement | Priority | Rationale |
|-------------|----------|-----------|
| Path 1 Stage 1: Base class swap | Must | Enables `to_safe_dict()` immediately; prerequisite for Stage 2 |
| Path 1 Stage 2: SecretStr for pat/password | Must | Security hygiene; known plaintext credential fields |
| Path 2: ADR for cache disposition | Must | Eliminates ambiguity; prevents scope creep toward convergence |
| Path 3: ECS domain Prometheus metrics | Should | High observability value; builds on existing `instrument_app()` |
| Path 3: Lambda cache_invalidate metrics | Should | Parity with cache_warmer; low effort |
| Path 1 Stage 3: SSM/SecretsManager integration | Could | Depends on infrastructure provisioning; zero code change |

---

## Dependency Map

```
Path 1 Stage 1 (base class swap)
    |
    v
Path 1 Stage 2 (SecretStr)
    |
    v
Path 1 Stage 3 (SSM/SM integration) -- infrastructure dependency

Path 2 (ADR) -- independent, no code changes

Path 3 (metrics) -- independent, can proceed in parallel with Path 1
```

---

## Related Documents

| Document | Path |
|----------|------|
| SDK Adoption Gap Inventory | `/Users/tomtenuta/Code/autom8y/docs/requirements/SDK-ADOPTION-GAP-INVENTORY.md` |
| SDK Migration Guide PRD | `/Users/tomtenuta/Code/autom8y/docs/requirements/PRD-SDK-MIGRATION-GUIDE.md` |
| autom8y-config base_settings | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-config/src/autom8y_config/base_settings.py` |
| autom8y-cache CacheProvider protocol | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/protocols/cache.py` |
| autom8y-cache TieredCacheProvider | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/tiered.py` |
| autom8y-telemetry instrument_app | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-telemetry/src/autom8y_telemetry/fastapi/instrument.py` |
| autom8y-telemetry metrics | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-telemetry/src/autom8y_telemetry/fastapi/metrics.py` |
| autom8_asana settings.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py` |
| autom8_asana config.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` |
| autom8_asana ConfigTranslator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/config_translator.py` |
| autom8_asana autom8_adapter.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/autom8_adapter.py` |
| autom8_asana EnvironmentAuthProvider | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/_defaults/auth.py` |
| autom8_asana MemoryTier | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/memory.py` |
| autom8_asana ProgressiveTier | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/progressive.py` |
| autom8_asana DataFrameCache | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/dataframe_cache.py` |
| autom8_asana cache_warmer Lambda | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_warmer.py` |
| autom8_asana cache_invalidate Lambda | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_invalidate.py` |
| autom8_asana FastAPI main | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` |

---

## Artifact Attestation

| # | Artifact | Absolute Path | Verified |
|---|----------|---------------|----------|
| 1 | autom8_asana settings.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py` | Read |
| 2 | autom8_asana config.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` | Read |
| 3 | autom8_asana config_translator.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/config_translator.py` | Read |
| 4 | autom8_asana autom8_adapter.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/autom8_adapter.py` | Read |
| 5 | autom8_asana MemoryTier | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/memory.py` | Read |
| 6 | autom8_asana ProgressiveTier | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/progressive.py` | Read |
| 7 | autom8_asana DataFrameCache | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/dataframe_cache.py` | Read |
| 8 | autom8_asana cache_warmer.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_warmer.py` | Read |
| 9 | autom8_asana cache_invalidate.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_invalidate.py` | Read |
| 10 | autom8_asana FastAPI main.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Read |
| 11 | autom8_asana _defaults/auth.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/_defaults/auth.py` | Read (via grep) |
| 12 | autom8y-config base_settings.py | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-config/src/autom8y_config/base_settings.py` | Read |
| 13 | autom8y-cache CacheProvider protocol | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/protocols/cache.py` | Read |
| 14 | autom8y-cache TieredCacheProvider | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/tiered.py` | Read |
| 15 | autom8y-telemetry instrument.py | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-telemetry/src/autom8y_telemetry/fastapi/instrument.py` | Read |
| 16 | autom8y-telemetry metrics.py | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-telemetry/src/autom8y_telemetry/fastapi/metrics.py` | Read |
| 17 | autom8y-telemetry config.py | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-telemetry/src/autom8y_telemetry/config.py` | Read |
| 18 | autom8y-telemetry InstrumentationConfig | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-telemetry/src/autom8y_telemetry/fastapi/config.py` | Read |
| 19 | SDK Adoption Gap Inventory | `/Users/tomtenuta/Code/autom8y/docs/requirements/SDK-ADOPTION-GAP-INVENTORY.md` | Read |
| 20 | SDK Migration Guide PRD | `/Users/tomtenuta/Code/autom8y/docs/requirements/PRD-SDK-MIGRATION-GUIDE.md` | Read |
| 21 | PRD (this document) | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-SDK-ALIGNMENT.md` | Written |
