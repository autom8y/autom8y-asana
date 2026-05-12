---
domain: feat/sdk-client-facade
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/client.py"
  - "./src/autom8_asana/__init__.py"
  - "./README.md"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.97
format_version: "1.0"
---

# AsanaClient SDK Facade

## Purpose and Design Rationale

### Why This Feature Exists

`AsanaClient` is the primary public entry point for the `autom8_asana` SDK. Its purpose is to give SDK consumers a single object that aggregates all Asana API resource access, manages the lifecycle of shared infrastructure (HTTP transport, rate limiting, circuit breaking, caching), and hides the internal complexity of the multi-layer architecture.

Before `AsanaClient` existed as a unified facade, callers would have needed to independently instantiate and wire together 13+ resource-specific clients, a transport layer, auth and cache providers, and retry/rate-limit policies. The facade collapses that into one callable constructor.

### Design Decisions

**1. Lazy initialization with double-checked locking**

Every resource client property (`.tasks`, `.projects`, `.sections`, etc.) uses the double-checked locking pattern with a per-client `threading.Lock`. The reasoning is that most callers access only a small subset of the 16 available clients, and instantiating all clients eagerly at construction time would impose unnecessary memory and initialization cost. The double-check prevents races in multithreaded code without locking on the fast path.

**2. Single shared rate limiter, circuit breaker, and retry policy per `AsanaClient` instance**

Per `ADR-0062`, all resource clients that share one `AsanaClient` share a single `TokenBucketRateLimiter`, `CircuitBreaker`, and `ExponentialBackoffRetry`. This was a deliberate fix: previously, each client created its own rate limiter, causing separate token buckets that did not enforce the aggregate Asana rate limit (1500 req/60s). A single shared rate limiter per `AsanaClient` enforces the real limit.

**3. Protocol-based dependency injection for all providers**

`AsanaClient` accepts `auth_provider`, `cache_provider`, `log_provider`, and `observability_hook` as injectable interfaces from `src/autom8_asana/protocols/`. When `None`, it falls back to defaults from `src/autom8_asana/_defaults/`. This enables the SDK to be used standalone (environment variable auth, auto-detected cache) or integrated into the autom8y platform (injected providers).

**4. Sync/async dual-mode support**

The SDK is async-first: all resource clients expose `*_async()` methods. Synchronous wrappers are provided and fail fast with `SyncInAsyncContextError` if called from an already-running event loop, per `ADR-0002`.

**5. Environment-aware cache provider selection**

If no `cache_provider` is injected, `create_cache_provider()` in `src/autom8_asana/cache/integration/factory.py` applies a detection chain: explicit config provider name -> master enabled flag -> environment detection (`AUTOM8Y_ENV=production` prefers Redis if `REDIS_HOST` is set, otherwise `InMemoryCacheProvider`). Reference: `TDD-CACHE-INTEGRATION: FR-CLIENT-006, NFR-COMPAT-004`.

**6. Workspace GID resolution order**

`workspace_gid` resolves in priority order: explicit constructor parameter -> `ASANA_WORKSPACE_GID` env var -> auto-detection via sync HTTP call to `/users/me`. Auto-detection is skipped if an async event loop is already running (would raise `SyncInAsyncContextError`).

**7. Conditional AutomationEngine at init time**

If `config.automation.enabled` is `True`, `AutomationEngine` is instantiated in `__init__` and `setup_event_emission()` is called to register event rules from `EVENTS_*` env vars (GAP-03). If `enabled=False` (default), `_automation` stays `None` and the `automation` property returns `None`. This avoids APScheduler overhead for callers that don't need automation.

### Tradeoffs

| Decision | Benefit | Cost |
|----------|---------|------|
| Lazy init with per-property lock | No wasted allocation; thread-safe | Lock-per-property adds memory (16+ locks) |
| Shared rate limiter | Correct aggregate rate enforcement | All sub-clients contend on one limiter |
| AIMD adaptive semaphore | Responds to 429s dynamically | Complexity in transport layer |
| Dual legacy + unified cache (TENSION-001 variant) | Safe incremental migration | Two parallel invalidation paths |
| Protocol-based DI | Testable, injectable, platform-agnostic | Callers must know which protocol to implement |

### Rejected Alternatives

No formal ADRs document rejected alternatives for the facade pattern itself. The rate limiter consolidation (ADR-0062) implies a rejected alternative: per-client rate limiters, which caused the bug described in SCAR-004's related pattern.

## Conceptual Model

### Key Abstractions

**`AsanaClient`** (`src/autom8_asana/client.py`) — The root facade. Has no business logic itself. Assembles infrastructure and delegates to resource clients. Is both a sync and async context manager.

**`AsanaConfig`** (`src/autom8_asana/config.py`) — Master configuration dataclass. Composed of: `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig`, `CircuitBreakerConfig`, `CacheConfig`, `DataFrameConfig`, `AutomationConfig`.

**`AsanaHttpClient`** (`src/autom8_asana/transport/asana_http.py`) — Transport wrapper around `autom8y-http`. Manages shared rate limiter/circuit breaker/retry policy, and owns AIMD adaptive semaphores. Exposed as `client.http` for internal collaborators (e.g., `HealingManager`).

**`BaseClient`** (`src/autom8_asana/clients/base.py`) — Base class for all 13+ resource clients. Provides cache check-before-HTTP, store-on-miss pattern. All cache failures degrade gracefully per `NFR-DEGRADE-001` / `ADR-0127`.

**Protocol interfaces** (`src/autom8_asana/protocols/`) — `AuthProvider`, `CacheProvider`, `LogProvider`, `ObservabilityHook`, `ItemLoader`, `DataFrameProvider`, `InsightsProvider`, `MetricsEmitter`.

**`_TokenAuthProvider`** (private class in `src/autom8_asana/client.py`) — Adapts the convenience `token=` constructor parameter to the `AuthProvider` protocol. Validates token is non-empty at construction time; raises `AuthenticationError` if empty/whitespace.

**`SaveSession`** (`src/autom8_asana/persistence/session.py`) — Unit of Work context manager. Created by `client.save_session(batch_size=10, max_concurrent=15)`. Handles deferred, dependency-ordered saves with partial failure handling. Available as both sync and async context manager.

**`SearchService`** (`src/autom8_asana/search/service.py`) — Field-based GID lookup from cached Polars DataFrames. Accessed via `client.search`. Lazy-initialized with a `DataFrameCacheIntegration` if a cache provider is present.

**`UnifiedTaskStore`** (`src/autom8_asana/cache/providers/unified.py`) — Single source of truth for task caching (MIGRATION-PLAN-legacy-cache-elimination). Accessed via `client.unified_store`. Returns `None` if cache is `NullCacheProvider`.

**`AutomationEngine`** (`src/autom8_asana/automation/engine.py`) — Rule-based automation. Accessed via `client.automation`. `None` when `config.automation.enabled=False`.

### Sub-client Tiers

**Tier 1** (core API resources): `tasks`, `projects`, `sections`, `custom_fields`, `users`, `workspaces`

**Tier 2** (secondary resources): `webhooks`, `teams`, `attachments`, `tags`, `goals`, `portfolios`, `stories`

**Specialized**: `batch` (bulk operations, auto-chunking at 10), `search` (DataFrame-backed field lookup)

### State Lifecycle

```
AsanaClient.__init__()
  |-- Resolve auth provider (explicit > token > env)
  |-- create_cache_provider(config.cache) -> CacheProvider
  |-- Create shared: TokenBucketRateLimiter, CircuitBreaker, ExponentialBackoffRetry
  |-- AsanaHttpClient(config, auth, rate_limiter, circuit_breaker, retry_policy)
  |-- Resolve workspace_gid (explicit > env > auto-detect)
  |   +-- auto-detect: sync HTTP call to /users/me (skipped if event loop running)
  |-- Initialize 16 lazy slots (_tasks=None, _tasks_lock, ... x16)
  +-- [if automation.enabled] AutomationEngine + setup_event_emission()

  [First access of .tasks property]
  |-- Fast path: self._tasks is not None -> return
  +-- Slow path: acquire _tasks_lock, double-check, create TasksClient(http, config, auth, cache, log, client=self)

  [Cache warming]
  warm_cache_async(gids, entry_type)
  |-- Filter already-cached GIDs via _cache_provider.get_versioned()
  +-- gather_with_semaphore(_warm_one, concurrency=20) -> WarmResult(warmed, failed, skipped)

  [Cleanup]
  async with AsanaClient() as client: -> __aexit__ -> close() -> http.close()
  with AsanaClient() as client: -> __exit__ -> asyncio.run(close()) [fails if event loop running]
```

### ADR Cross-References

| ADR | Subject | Impact |
|-----|---------|--------|
| ADR-0002 | Sync-in-async fail-fast | `SyncInAsyncContextError` on sync wrappers in async context |
| ADR-0062 | Client-scoped shared rate limiter | Single `TokenBucketRateLimiter` per `AsanaClient` |
| ADR-0127 | Graceful cache degradation | `BaseClient` catches `CACHE_TRANSIENT_ERRORS`; no cache failure propagates to caller |
| ADR-VAULT-001 | AWS Secrets Manager auth | `SecretsManagerAuthProvider` exported at root level |
| TDD-CACHE-INTEGRATION | Cache provider factory | `FR-CLIENT-006`, `NFR-COMPAT-004` |
| TDD-HARDENING-A/FR-OBS-011 | Observability hook | `NullObservabilityHook` default |

## Implementation Map

### Files

| File | Role |
|------|------|
| `src/autom8_asana/client.py` | `AsanaClient` class (~1063 lines), `_TokenAuthProvider` |
| `src/autom8_asana/__init__.py` | Public API surface; lazy-loads DataFrame exports via `__getattr__` |
| `src/autom8_asana/config.py` | `AsanaConfig`, all sub-configs, `DEFAULT_ENTITY_TTLS` |
| `src/autom8_asana/errors.py` | `AsanaError` hierarchy (14 exception types including `GidValidationError`) |
| `src/autom8_asana/protocols/auth.py` | `AuthProvider` protocol |
| `src/autom8_asana/protocols/cache.py` | `CacheProvider` protocol, `WarmResult` |
| `src/autom8_asana/protocols/observability.py` | `ObservabilityHook` protocol |
| `src/autom8_asana/_defaults/auth.py` | `EnvAuthProvider`, `SecretsManagerAuthProvider` |
| `src/autom8_asana/_defaults/cache.py` | `NullCacheProvider`, `InMemoryCacheProvider` |
| `src/autom8_asana/_defaults/log.py` | `DefaultLogProvider` |
| `src/autom8_asana/_defaults/observability.py` | `NullObservabilityHook` |
| `src/autom8_asana/cache/integration/factory.py` | `create_cache_provider()`, `CacheProviderFactory.create_unified_store()` |
| `src/autom8_asana/transport/asana_http.py` | `AsanaHttpClient` — HTTP transport with shared rate limiter/CB/retry |
| `src/autom8_asana/transport/config_translator.py` | `ConfigTranslator` — converts `AsanaConfig` to `autom8y_http` config types |
| `src/autom8_asana/persistence/session.py` | `SaveSession` — Unit of Work context manager |
| `src/autom8_asana/search/` | `SearchService` — field-based GID lookup |
| `src/autom8_asana/automation/engine.py` | `AutomationEngine` (conditional init) |

### Constructor Signature

```python
AsanaClient(
    token: str | None = None,
    *,
    workspace_gid: str | None = None,
    auth_provider: AuthProvider | None = None,
    cache_provider: CacheProvider | None = None,
    log_provider: LogProvider | None = None,
    config: AsanaConfig | None = None,
    observability_hook: ObservabilityHook | None = None,
)
```

### Public API Surface (from `__init__.py`)

**Main client**: `AsanaClient`

**Configuration** (6 types): `AsanaConfig`, `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig`

**Exceptions** (14 types): `AsanaError`, `AuthenticationError`, `ForbiddenError`, `GidValidationError`, `GoneError`, `HydrationError`, `NotFoundError`, `RateLimitError`, `ServerError`, `TimeoutError`, `ConfigurationError`, `SyncInAsyncContextError`

**Protocols** (4 types): `AuthProvider`, `CacheProvider`, `ItemLoader`, `LogProvider`, `ObservabilityHook`

**Auth providers**: `EnvAuthProvider`, `SecretsManagerAuthProvider`

**Observability**: `CorrelationContext`, `error_handler`, `generate_correlation_id`

**Batch API** (4 types): `BatchClient`, `BatchRequest`, `BatchResult`, `BatchSummary`

**Models** (20 types): `Task`, `Project`, `Section`, `User`, `Workspace`, `CustomField`, `CustomFieldEnumOption`, `CustomFieldSetting`, `Goal`, `GoalMembership`, `GoalMetric`, `NameGid`, `PageIterator`, `Portfolio`, `Story`, `Tag`, `Team`, `TeamMembership`, `Webhook`, `WebhookFilter`, `Attachment`, `AsanaResource`

**DataFrame exports** (25+ symbols, lazy-loaded via `__getattr__` to avoid pulling in polars for core-API-only consumers)

### Public Methods Beyond Properties

| Method | Mode | Description |
|--------|------|-------------|
| `save_session(batch_size, max_concurrent)` | sync factory | Returns `SaveSession` context manager |
| `warm_cache_async(gids, entry_type)` | async | Pre-populates cache; returns `WarmResult` |
| `warm_cache(gids, entry_type)` | sync wrapper | Delegates to `warm_cache_async`; raises `SyncInAsyncContextError` if in async context |
| `close()` / `aclose()` | async | Closes HTTP client resources |
| `__aenter__` / `__aexit__` | async context | Preferred cleanup pattern |
| `__enter__` / `__exit__` | sync context | Works only when no event loop is running |

### Test Locations

| Test file | Covers |
|-----------|--------|
| `tests/unit/clients/test_client.py` | `AsanaClient` init, auth resolution, workspace GID resolution |
| `tests/unit/clients/test_client_warm_cache.py` | `warm_cache_async`, `WarmResult` |
| `tests/unit/clients/test_tier1_clients.py` | Tier 1 lazy init (tasks, projects, sections, custom_fields, users, workspaces) |
| `tests/unit/clients/test_tier2_clients.py` | Tier 2 lazy init (webhooks, teams, attachments, tags, goals, portfolios, stories) |
| `tests/unit/clients/test_batch.py` | `BatchClient` via `client.batch` |

## Boundaries and Failure Modes

### What This Feature Does NOT Do

- `AsanaClient` does not implement any Asana API business logic — all logic lives in `BaseClient` subclasses
- Does not enforce workspace-GID correctness on individual API calls — the workspace GID on `client.default_workspace_gid` is advisory; sub-clients pass it where needed
- Does not manage connection pooling directly — `AsanaHttpClient` via `autom8y_http` owns pooling
- Does not provide schema-based DataFrame operations — `client.search` and `DataFrameService` (service layer) handle that
- Does not support OAuth flows — only PAT and platform (secrets manager) auth

### Active Structural Tensions

**TENSION-001 (dual cache paths)**: `AsanaClient` has two cache entry points: `_cache_provider` (legacy, used by all sub-clients via `BaseClient`) and `_unified_store` (`UnifiedTaskStore`, tiered). `MIGRATION-PLAN-legacy-cache-elimination` is referenced in code but not complete. Both paths must remain consistent for cache coherence.

**SCAR-004 (cache split, resolved)**: Historic failure where each `AsanaClient` auto-detected its own `InMemoryCacheProvider`, making warm-up writes invisible to request handlers. Fixed: single shared `CacheProvider` on `app.state`. `DEF-005` comments reference this fix. No isolated regression test exists for this scar (per scar-tissue.md).

**SCAR-009 (workspace auto-detect in wrong context, historical)**: Tests missing `ASANA_WORKSPACE_GID` triggered sync auto-detection that failed in async test contexts. The fix: auto-detect is skipped when `asyncio.get_running_loop()` succeeds. Now guarded by the async-loop check in `__init__`.

### Error Paths

| Condition | Exception |
|-----------|-----------|
| Empty or whitespace token passed to `_TokenAuthProvider` | `AuthenticationError` |
| Token env var not set (`EnvAuthProvider` fallback) | `AuthenticationError` |
| 0 workspaces found during auto-detect | `ConfigurationError` |
| Multiple workspaces, none specified | `ConfigurationError` |
| `warm_cache()` called from async context | `SyncInAsyncContextError` |
| `__exit__` called from async context | `ConfigurationError` |
| `_auto_detect_workspace` HTTPError (invalid token / unreachable) | Returns `None` (silent, no raise) |
| API 429 | `RateLimitError` (with `retry_after`) |
| Circuit breaker open | `CircuitBreakerOpenError` (from `autom8y_http`) |
| Cache backend transient error | warn + continue (no raise per `ADR-0127`) |
| `setup_event_emission` `ValueError` (bad EVENTS_* config) | Re-raised from `__init__` |
| `warm_cache_async` with unsupported `EntryType` | `ValueError` |

### Inter-Feature Relationships

**Consumed by**:
- `api/lifespan.py` — creates single `ClientPool` (per-token resilience, `DEF-005`); each pool entry is an `AsanaClient`
- `api/dependencies.py` — `get_auth_context()` and service DI inject `AsanaClient` into route handlers
- Lambda handlers (`lambda_handlers/*/`) — each creates its own `AsanaClient` per invocation

**Provides to**:
- `save_session()` returns `SaveSession` which calls back into resource clients via `client.tasks`, `client.projects`, etc.
- `client.http` exposed as public property for `persistence/session.py` (`HealingManager`) to access transport without private attribute access
- `client.automation` provides `AutomationEngine` access for rule registration

**Sibling features**:
- `http-transport` — `AsanaHttpClient` is instantiated inside `AsanaClient.__init__`; shared rate limiter/CB/retry injected at construction
- `cache-subsystem` — `create_cache_provider()` factory called at init; `unified_store` property wraps `CacheProviderFactory.create_unified_store()`
- `batch-api-client` — `BatchClient` lazy-initialized via `client.batch`
- `save-session` — `SaveSession` factory method on `AsanaClient`
- `automation-engine` — conditionally instantiated at init time

### Configuration Boundaries

| Config key | Effect |
|-----------|--------|
| `config.automation.enabled` | Controls whether `AutomationEngine` is created at init |
| `config.token_key` | The secret key name `_TokenAuthProvider` and `EnvAuthProvider` look up |
| `config.cache.*` | Passed to `create_cache_provider()` factory for backend selection |
| `ASANA_PAT` / `ASANA_TOKEN_KEY` | Env vars for token resolution |
| `ASANA_WORKSPACE_GID` / `ASANA_WORKSPACE_KEY` | Env vars for workspace resolution |
| `AUTOM8Y_ENV=production` + `REDIS_HOST` | Triggers Redis cache backend in factory detection chain |

### Known Gaps (carried from prior generation)

1. **`SearchService` internals** (`src/autom8_asana/search/`): Implementation not read.
2. **`UnifiedTaskStore` implementation** (`src/autom8_asana/cache/providers/unified.py`): Factory path not traced.
3. **`ClientPool` wiring** (`src/autom8_asana/api/client_pool.py`): Token-keyed pool mechanics not fully traced.
4. **`InMemoryCacheProvider` TTL behavior**: Exact eviction mechanics not read.
5. **Integration test coverage depth**: Test files identified but not read for assertion coverage.

```metadata
confidence: 0.97
prior_source_hash: "c213958"
refresh_trigger: "source_hash mismatch — prior hash not in current git history"
source_files_changed: false
content_drift_detected: false
primary_changes: "frontmatter update (generated_at, source_hash, confidence); added explicit save_session/warm_cache method table; clarified _TokenAuthProvider validation; added conditional AutomationEngine design decision; expanded error path for setup_event_emission; confirmed test file inventory unchanged; no source code changes detected between prior and current HEAD"
```
