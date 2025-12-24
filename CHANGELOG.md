# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
