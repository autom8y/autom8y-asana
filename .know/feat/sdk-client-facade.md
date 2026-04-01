---
domain: feat/sdk-client-facade
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/client.py"
  - "./src/autom8_asana/__init__.py"
  - "./src/autom8_asana/config.py"
  - "./src/autom8_asana/protocols/**/*.py"
  - "./src/autom8_asana/_defaults/**/*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.92
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

**5. Environment-aware cache provider selection (ADR-0123)**

If no `cache_provider` is injected, `create_cache_provider()` in `src/autom8_asana/cache/integration/factory.py` applies a detection chain: explicit config provider name -> master enabled flag -> environment detection (`AUTOM8Y_ENV=production` prefers Redis if `REDIS_HOST` is set, otherwise `InMemoryCacheProvider`).

**6. Workspace GID resolution order**

`workspace_gid` resolves in priority order: explicit constructor parameter -> `ASANA_WORKSPACE_GID` env var -> auto-detection via sync HTTP call to `/users/me`.

### Tradeoffs

| Decision | Benefit | Cost |
|----------|---------|------|
| Lazy init with per-property lock | No wasted allocation; thread-safe | Lock-per-property adds memory (16 locks) |
| Shared rate limiter | Correct aggregate rate enforcement | All clients contend on one limiter |
| AIMD adaptive semaphore | Responds to 429s dynamically | Complexity in transport layer |
| Dual legacy + unified cache (TENSION-001) | Safe incremental migration | Two parallel invalidation paths |

## Conceptual Model

### Key Abstractions

**`AsanaClient`** (`src/autom8_asana/client.py`) -- The root facade. Has no business logic itself. Assembles infrastructure and delegates to resource clients.

**`AsanaConfig`** (`src/autom8_asana/config.py`) -- Master configuration dataclass. Composed of: `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig`, `CircuitBreakerConfig`, `CacheConfig`, `DataFrameConfig`, `AutomationConfig`.

**`AsanaHttpClient`** (`src/autom8_asana/transport/asana_http.py`) -- Transport wrapper around `autom8y-http`. Manages shared rate limiter/circuit breaker/retry policy, and owns AIMD adaptive semaphores.

**`BaseClient`** (`src/autom8_asana/clients/base.py`) -- Base class for all 13+ resource clients. Provides cache check-before-HTTP, store-on-miss pattern. All cache failures degrade gracefully per `NFR-DEGRADE-001` / `ADR-0127`.

**Protocol interfaces** (`src/autom8_asana/protocols/`) -- `AuthProvider`, `CacheProvider`, `LogProvider`, `ObservabilityHook`.

**`_TokenAuthProvider`** (private class in `src/autom8_asana/client.py`) -- Adapts the convenience `token=` constructor parameter to the `AuthProvider` protocol.

### State Lifecycle

```
AsanaClient.__init__()
  |-- Resolve auth provider (explicit > token > env)
  |-- create_cache_provider(config.cache) -> CacheProvider
  |-- Create shared: TokenBucketRateLimiter, CircuitBreaker, ExponentialBackoffRetry
  |-- AsanaHttpClient(config, auth, rate_limiter, circuit_breaker, retry_policy)
  |-- Resolve workspace_gid (explicit > env > auto-detect)
  |-- Initialize lazy slots (_tasks=None, _tasks_lock, ... x16)
  +-- [if automation.enabled] AutomationEngine + setup_event_emission()

  [First access of .tasks property]
  |-- Fast path: self._tasks is not None -> return
  +-- Slow path: acquire _tasks_lock, double-check, create TasksClient

  [Cleanup]
  async with AsanaClient() as client: -> __aexit__ -> close() -> http.close()
```

### ADR Cross-References

| ADR | Subject | Impact |
|-----|---------|--------|
| ADR-0002 | Sync-in-async fail-fast | `SyncInAsyncContextError` |
| ADR-0062 | Client-scoped shared rate limiter | Single limiter per AsanaClient |
| ADR-0123 | Cache provider detection chain | CacheProviderFactory priority |
| ADR-0127 | Graceful cache degradation | BaseClient catches CACHE_TRANSIENT_ERRORS |

## Implementation Map

### Files

| File | Role |
|------|------|
| `src/autom8_asana/client.py` | `AsanaClient` class (~1066 lines), `_TokenAuthProvider` |
| `src/autom8_asana/__init__.py` | Public API surface; lazy-loads DataFrame exports via `__getattr__` |
| `src/autom8_asana/config.py` | `AsanaConfig`, all sub-configs, `DEFAULT_ENTITY_TTLS` |
| `src/autom8_asana/exceptions.py` | `AsanaError` hierarchy (14 exception types) |
| `src/autom8_asana/settings.py` | Pydantic `BaseSettings` singleton (`get_settings()`) |
| `src/autom8_asana/protocols/auth.py` | `AuthProvider` protocol |
| `src/autom8_asana/protocols/cache.py` | `CacheProvider` protocol |
| `src/autom8_asana/_defaults/auth.py` | `EnvAuthProvider`, `SecretsManagerAuthProvider` |
| `src/autom8_asana/_defaults/cache.py` | `NullCacheProvider`, `InMemoryCacheProvider` |
| `src/autom8_asana/cache/integration/factory.py` | `CacheProviderFactory.create()` |

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
**Configuration**: `AsanaConfig`, `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig`
**Exceptions** (14 types): `AsanaError`, `AuthenticationError`, `ForbiddenError`, `NotFoundError`, `RateLimitError`, `ServerError`, `TimeoutError`, `ConfigurationError`, `SyncInAsyncContextError`, etc.
**Protocols**: `AuthProvider`, `CacheProvider`, `ItemLoader`, `LogProvider`, `ObservabilityHook`
**Auth providers**: `EnvAuthProvider`, `SecretsManagerAuthProvider`
**Models** (20 types): `Task`, `Project`, `Section`, `User`, `Workspace`, `CustomField`, etc.
**DataFrame exports** (25 symbols, lazy-loaded via `__getattr__`)

### Test Locations

| Test file | Covers |
|-----------|--------|
| `tests/unit/clients/test_client.py` | AsanaClient init, auth resolution |
| `tests/unit/clients/test_client_warm_cache.py` | warm_cache_async |
| `tests/unit/clients/test_tier1_clients.py` | Tier 1 lazy init |
| `tests/unit/clients/test_tier2_clients.py` | Tier 2 lazy init |

## Boundaries and Failure Modes

### Active Structural Tensions

**TENSION-001: Dual cache paths** -- `AsanaClient` has two separate cache entry points: `_cache_provider` (legacy) and `_unified_store` (`UnifiedTaskStore`, tiered). `MIGRATION-PLAN-legacy-cache-elimination` is referenced but not complete.

**SCAR-004: Isolated cache providers (fixed)** -- Historic failure where each `AsanaClient` auto-detected its own `InMemoryCacheProvider`, making warm-up writes invisible to request handlers. Fixed: single shared `CacheProvider` on `app.state`.

### Error Paths

| Condition | Exception |
|-----------|-----------|
| Empty or whitespace token | `AuthenticationError` |
| Token env var not set | `AuthenticationError` |
| 0 workspaces found | `ConfigurationError` |
| Multiple workspaces, none specified | `ConfigurationError` |
| `warm_cache()` called from async context | `SyncInAsyncContextError` |
| `__exit__` called from async context | `ConfigurationError` |
| API 429 | `RateLimitError` (with `retry_after`) |
| Circuit breaker open | `CircuitBreakerOpenError` |
| Cache backend failure | warn + continue (no raise) |

### Inter-Feature Relationships

- Used by `api/lifespan.py` via `ClientPool` (shared instance per user token)
- `save_session()` returns `SaveSession` which calls back into resource clients
- `_http` exposed as public property for `persistence/session.py` (HealingManager)
- `automation` property wires to `AutomationEngine` (when enabled)

## Knowledge Gaps

1. **`SearchService` internals** (`src/autom8_asana/search/`): Implementation not read.
2. **`UnifiedTaskStore` implementation** (`src/autom8_asana/cache/providers/unified.py`): Factory path not read.
3. **`ClientPool` wiring** (`src/autom8_asana/api/client_pool.py`): Token-keyed pool mechanics not fully traced.
4. **`InMemoryCacheProvider` TTL behavior**: Exact eviction mechanics not read.
5. **Integration test coverage**: Test files identified but not read for coverage depth.
