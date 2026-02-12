# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-31

### Breaking Changes

- **Platform Primitive Migration**: Transport layer now delegates to `autom8y-*` packages
  - `autom8y-config>=0.1.0` - Configuration primitives
  - `autom8y-http>=0.1.0` - HTTP transport primitives (rate limiter, retry, circuit breaker)
  - `autom8y-log>=0.1.0` - Logging primitives
  - **Python 3.11+ required** (upgraded from 3.10)

- **Transport Layer Refactored**: Components now wrap platform primitives
  - `TokenBucketRateLimiter` wraps `autom8y_http.TokenBucketRateLimiter`
  - `RetryHandler` wraps `autom8y_http.ExponentialBackoffRetry`
  - `CircuitBreaker` wraps `autom8y_http.CircuitBreaker`
  - `sync_wrapper` wraps `autom8y_http.sync_wrapper`
  - Backward compatibility maintained via wrapper classes

### Added

- **LogProviderAdapter** (`autom8_asana.compat.log_adapter`): Bridges printf-style `LogProvider` to structured `LoggerProtocol`
- **Platform config imports**: Transport configs available from `autom8y_http`

### Migration Notes

Existing code using `autom8_asana.transport.*` continues to work unchanged. The wrappers maintain the original API signatures while delegating to platform primitives internally.

For new code, consider importing directly from platform primitives:
```python
# New pattern (recommended for new code)
from autom8y_http import TokenBucketRateLimiter, ExponentialBackoffRetry

# Old pattern (still works, maintained for backward compatibility)
from autom8_asana.transport import TokenBucketRateLimiter, RetryHandler
```

### Technical Details

- TDD: `docs/architecture/TDD-PRIMITIVE-MIGRATION-001.md`
- Spike: `docs/spikes/SPIKE-AUTOM8-ASANA-PRIMITIVE-ADOPTION.md` (in autom8y)
- Validation: `docs/testing/VALIDATION-PRIMITIVE-MIGRATION-001.md`

---

## [Unreleased]

### Added

- **Search Interface v2.0**: Field-based entity lookup with Polars-backed performance
  - `SearchService.find_async()` and `find()` for flexible multi-field queries
  - `SearchService.find_one_async()` for single-entity lookups (raises on multiple matches)
  - Convenience methods: `find_offers_async()`, `find_units_async()`, `find_businesses_async()`
  - Automatic field name normalization (snake_case kwargs to Title Case column names)
  - Polars filter expressions for sub-millisecond query performance on cached DataFrames
  - `SearchCriteria` model with `eq`, `contains`, and `in` operators
  - `FieldCondition` for building explicit query conditions
  - AND/OR combinator support for complex compound queries
  - Entity type filtering via `entity_type` parameter
  - Result limiting via `limit` parameter
  - `SearchResult` with hits, total_count, query_time_ms, and cache status
  - `SearchHit` with GID, entity_type, name, and matched_fields
  - Async-first API design with sync wrappers for all methods
  - Automatic DataFrame caching with 5-minute TTL (300 seconds)
  - Graceful degradation: returns empty results on errors instead of raising
  - See [Search Query Builder Guide](docs/guides/search-query-builder.md)

- **Cache Optimization Phase 2: Task-Level Cache Integration** (TDD-CACHE-PERF-FETCH-PATH)
  - Implemented two-phase cache strategy for DataFrame fetch path:
    1. Lightweight GID enumeration via `fetch_section_task_gids_async()`
    2. Batch cache lookup before API fetch
    3. Targeted fetch for cache misses only (cold/partial/warm paths)
    4. Cache population after fetch with entity-type TTL
  - New `TaskCacheCoordinator` class for Task-level cache operations
  - Smart path selection: cold (0% hit), partial, warm (100% hit)
  - `fetch_by_gids()` method for efficient targeted task fetch
  - Structured logging with detailed cache metrics:
    - Cache lookup timing and hit/miss counts
    - API fetch path selection and timing
    - Cache population counts and timing
  - Integration test suite for cache lifecycle validation
  - Demo script enhancements with `--metrics` flag for detailed output

  **Performance Impact**: Achieves <1s warm cache latency (down from 11.56s baseline) with >90% cache hit rate on repeated fetches.

### Removed

- **Credential Vault integration removed** (ADR-VAULT-001)
  - Deleted `autom8_asana._defaults.vault_auth` module
  - Removed `CredentialVaultAuthProvider` from public API
  - Removed `[vault]` optional dependency group
  - Removed `autom8y-auth` dependency and CodeArtifact index configuration

  **Migration**: Use Bot PAT authentication via environment variables or AWS Secrets Manager instead of the Credential Vault. The vault feature has been mothballed per ADR-VAULT-001.
