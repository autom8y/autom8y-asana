# ADR-0123: Default Cache Provider Selection Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-22
- **Deciders**: SDK Team
- **Related**: [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md), [TDD-CACHE-INTEGRATION](../design/TDD-CACHE-INTEGRATION.md), ADR-0016, ADR-0017

## Context

The autom8_asana SDK has 4,000 lines of cache infrastructure that is currently dormant because `AsanaClient.__init__()` defaults to `NullCacheProvider()`. Every `TasksClient.get_async()` call hits the Asana API, even for repeated reads.

We need to enable caching by default while:
1. Maintaining backward compatibility for existing code
2. Selecting appropriate providers based on deployment environment
3. Supporting explicit configuration overrides
4. Failing gracefully when desired providers are unavailable

**The key question**: How should the SDK automatically select a cache provider when none is explicitly provided?

Forces at play:
- Development environments need zero-config caching (InMemory)
- Production environments should use Redis when available
- Explicit `cache_provider` parameter must always win (backward compat)
- Environment variables provide deployment-time configuration
- Missing Redis configuration in production should not crash the application
- Unit tests should not suddenly start caching unexpectedly

## Decision

We will use an **environment-aware detection chain** with the following priority order:

```python
Priority 1: Explicit cache_provider parameter (AsanaClient(cache_provider=X))
    |
    v (if None)
Priority 2: ASANA_CACHE_PROVIDER environment variable
    |
    v (if not set)
Priority 3: Environment-based auto-detection
    |
    +-- ASANA_ENVIRONMENT=production/staging + REDIS_HOST set --> RedisCacheProvider
    |
    +-- ASANA_ENVIRONMENT=production/staging + no REDIS_HOST --> InMemory + warning
    |
    +-- ASANA_ENVIRONMENT=development/test (or not set) --> InMemoryCacheProvider
    |
    v (fallback)
Priority 4: InMemoryCacheProvider (default)
```

The implementation uses a `CacheProviderFactory` class:

```python
class CacheProviderFactory:
    @staticmethod
    def create(config: CacheConfig) -> CacheProvider:
        # Master disable switch
        if not config.enabled:
            return NullCacheProvider()

        # Explicit provider from config/env
        if config.provider:
            return CacheProviderFactory._create_explicit(config.provider, config)

        # Auto-detect based on environment
        return CacheProviderFactory._auto_detect(config)
```

Integration point in `AsanaClient.__init__`:

```python
def __init__(self, ..., cache_provider: CacheProvider | None = None, ...):
    if cache_provider is not None:
        self._cache_provider = cache_provider  # Priority 1: explicit
    else:
        self._cache_provider = CacheProviderFactory.create(self._config.cache)
```

## Rationale

### Why Detection Chain Over Alternatives?

| Criterion | Static Default | Env Var Only | **Detection Chain** |
|-----------|---------------|--------------|---------------------|
| Zero-config DX | Poor (no cache) | Medium | **Good** |
| Production-ready | N/A | Good | **Good** |
| Test isolation | Good | Medium | **Good** |
| Backward compat | Good | Good | **Good** |
| Graceful degradation | N/A | Poor | **Good** |
| Complexity | Low | Low | **Medium** |

### Why Priority Order Matters

1. **Explicit parameter first**: This is the strongest signal of intent. If a user passes `cache_provider=NullCacheProvider()`, they explicitly want no caching. Existing code relying on this behavior must continue to work (NFR-COMPAT-004).

2. **Environment variable second**: This allows deployment-time configuration without code changes. Useful for CI/CD pipelines, Docker deployments, and testing different configurations.

3. **Auto-detection third**: This provides zero-configuration developer experience. A developer running locally gets InMemory caching automatically. Production deployments with Redis configured get Redis automatically.

4. **InMemory fallback last**: Rather than failing or disabling caching entirely, we fall back to InMemory with a logged warning. This ensures caching benefits without hard failures.

### Why Warn Instead of Fail in Production Without Redis?

Per NFR-DEGRADE-002, cache unavailability should not prevent the SDK from functioning. A production environment without Redis is not ideal, but:
- The application can still function with InMemory cache
- InMemory provides significant benefits (50%+ API call reduction)
- Forcing Redis would break existing deployments
- Warning logs alert operators to suboptimal configuration

The warning message:
```
"Production environment without REDIS_HOST configured. Using InMemoryCacheProvider as fallback."
```

### Why Not Default to NullCacheProvider for Tests?

Unit tests using `AsanaClient()` with mocked HTTP will now get InMemoryCacheProvider. This is intentional:
- Tests should test the real caching behavior
- Existing tests that mock HTTP responses will still work
- Tests that explicitly need no caching can pass `cache_provider=NullCacheProvider()`
- Integration tests benefit from testing cache behavior

For test isolation concerns, we provide explicit opt-out:
```python
client = AsanaClient(cache_provider=NullCacheProvider())  # Test without caching
```

## Alternatives Considered

### Alternative 1: Static Default (Always InMemory)

- **Description**: Change line 125 of `client.py` from `NullCacheProvider()` to `InMemoryCacheProvider()`.
- **Pros**:
  - Simplest change (1 line)
  - Immediate cache benefits
- **Cons**:
  - No environment awareness
  - Production should use Redis, not InMemory
  - No configuration override mechanism
- **Why not chosen**: Does not distinguish between development and production environments. Production workloads need distributed caching (Redis) for multi-process deployments.

### Alternative 2: Environment Variable Only

- **Description**: Read `ASANA_CACHE_PROVIDER` env var, default to NullCacheProvider if not set.
- **Pros**:
  - Simple implementation
  - Explicit configuration
  - No magic behavior
- **Cons**:
  - Requires configuration for every environment
  - Zero-config development is lost
  - Existing code with no env var gets no caching
- **Why not chosen**: Violates the principle of sensible defaults. Developers should get caching benefits without configuration in development.

### Alternative 3: Auto-Detect Only (No Explicit Config)

- **Description**: Always auto-detect based on environment, ignore explicit config.
- **Pros**:
  - Simplest mental model
  - Always environment-appropriate
- **Cons**:
  - Cannot override for testing
  - Cannot disable caching when needed
  - Breaks existing code using explicit NullCacheProvider
- **Why not chosen**: Breaks backward compatibility (NFR-COMPAT-004). Explicit configuration must always take precedence.

### Alternative 4: Configuration File (.asana.yaml)

- **Description**: Load cache configuration from a config file in the project root.
- **Pros**:
  - Rich configuration options
  - Checked into source control
  - Environment-specific configs possible
- **Cons**:
  - Adds file I/O to client initialization
  - New dependency pattern for SDK
  - Increases complexity significantly
- **Why not chosen**: Over-engineering for the problem. Environment variables are the 12-factor app standard for deployment configuration.

## Consequences

### Positive

- **Zero-config development**: Developers get caching without any configuration
- **Production-aware**: Auto-detects Redis in production environments
- **Backward compatible**: Explicit `cache_provider` parameter behavior unchanged
- **Graceful degradation**: Missing Redis falls back with warning, not error
- **Testable**: Can explicitly disable caching for specific tests
- **12-factor compliant**: Configuration via environment variables

### Negative

- **Increased complexity**: Factory pattern adds ~120 lines of code
- **Implicit behavior**: Cache is enabled by default (may surprise some users)
- **Environment variable proliferation**: Adds 4 new ASANA_CACHE_* variables
- **Test behavior change**: Tests without explicit provider now get InMemory cache

### Neutral

- **Warning noise**: Production without Redis generates warning logs
- **Documentation required**: New behavior must be documented
- **Migration path needed**: Existing users should review caching behavior

## Compliance

How do we ensure this decision is followed?

1. **Priority order enforcement**: Unit tests verify selection priority
2. **Backward compat verification**: Test suite passes without modification
3. **Environment detection tests**: Test all environment combinations
4. **Warning assertion**: Tests verify warning is logged in production without Redis

## Implementation Checklist

- [ ] Create `cache/factory.py` with CacheProviderFactory
- [ ] Add CacheConfig to config.py
- [ ] Integrate factory in AsanaClient.__init__
- [ ] Add environment detection tests
- [ ] Add backward compatibility tests
- [ ] Update documentation with new defaults
