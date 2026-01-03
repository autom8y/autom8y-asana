---
artifact_id: PRD-unified-cache-001
title: "Unified Task Cache Architecture"
created_at: "2026-01-02T18:00:00Z"
author: requirements-analyst
status: draft
complexity: SERVICE
success_criteria:
  - id: SC-001
    description: "All SDK task data flows through a single UnifiedTaskStore with one cache entry per task GID"
    testable: true
    priority: must-have
  - id: SC-002
    description: "DataFrame builds complete without cold cache NOT_FOUND errors for valid phone/vertical pairs"
    testable: true
    priority: must-have
  - id: SC-003
    description: "Cascade field resolution (cascade: prefix) returns correct parent values using shared cache"
    testable: true
    priority: must-have
  - id: SC-004
    description: "Warm cache DataFrame builds execute in 1-2 API calls (down from 4-6)"
    testable: true
    priority: must-have
  - id: SC-005
    description: "Freshness mode configuration (STRICT/EVENTUAL/IMMEDIATE) controls validation behavior"
    testable: true
    priority: should-have
  - id: SC-006
    description: "Service recovery from cold start completes within acceptable latency using S3-backed storage"
    testable: true
    priority: should-have
  - id: SC-007
    description: "All existing tests pass with no regression in DataFrame build latency"
    testable: true
    priority: must-have
related_adrs:
  - ADR-UNIFIED-001
  - ADR-UNIFIED-002
  - ADR-UNIFIED-003
stakeholders:
  - sdk-consumer
  - api-service-operator
  - developer
schema_version: "1.0"
---

# PRD: Unified Task Cache Architecture

**PRD ID**: PRD-UNIFIED-CACHE-001
**Version**: 1.0
**Date**: 2026-01-02
**TDD Reference**: TDD-UNIFIED-CACHE-001

---

## Overview

This PRD defines requirements for consolidating the autom8_asana SDK's fragmented cache infrastructure into a unified task cache. The cache serves as the single source of truth for task data, enabling reliable entity resolution, predictable DataFrame builds, and reduced API overhead.

---

## Problem Statement

### User Pain Points

1. **Entity Resolver Failures**: The `/api/v1/internal/gid-lookup` service returns NOT_FOUND for valid phone/vertical pairs when the cache is cold. SDK consumers receive false negatives, causing downstream automation failures.

2. **Unpredictable DataFrame Builds**: DataFrame builders execute 4-6 redundant API calls per operation, leading to:
   - Inconsistent latency (cold vs. warm cache variance)
   - Rate limit pressure during batch operations
   - Increased API costs for high-volume consumers

3. **Cascade Field Inconsistency**: The `cascade:` syntax for parent field resolution uses a per-instance cache that does not share data with the main task cache. This causes:
   - Duplicate API calls to fetch the same parent tasks
   - Potential staleness when cascade cache diverges from task cache

4. **Cold Start Fragility**: Service restarts require full re-synchronization because cache layers do not share a durable backing store. Recovery time impacts service availability SLAs.

### Technical Root Cause

Five separate cache implementations have evolved incrementally:
- `TieredCacheProvider` (Redis + S3)
- `TaskCacheCoordinator` (DataFrame task cache)
- `DataFrameCacheIntegration` (extracted row cache)
- `StalenessCheckCoordinator` (TTL-based freshness)
- `CascadingFieldResolver._parent_cache` (per-instance parent cache)

Each layer uses different freshness semantics, creating inconsistent data views and redundant storage.

---

## User Personas

### SDK Consumer

**Role**: Developer building analytics dashboards or automation scripts using the autom8_asana SDK.

**Needs**:
- Reliable DataFrame builds that return complete, accurate data
- Predictable performance regardless of cache state
- Clear freshness guarantees for time-sensitive operations

**Pain Points**:
- NOT_FOUND errors for entities that should exist
- Variable latency making performance budgeting difficult
- Stale cascade field values causing incorrect business logic

### API Service Operator

**Role**: Engineer responsible for deploying and monitoring the autom8_asana API service.

**Needs**:
- Predictable resource utilization (API rate limits, memory)
- Fast service recovery after restarts
- Observable cache behavior for debugging

**Pain Points**:
- Rate limit exhaustion during bulk operations
- Long recovery times after cold starts
- Difficulty diagnosing cache inconsistencies across layers

### Developer

**Role**: Engineer integrating new entity types or cascade fields into the SDK.

**Needs**:
- Clear mental model for how caching works
- Single integration point for cache operations
- Preserved `cascade:` syntax compatibility

**Pain Points**:
- Multiple cache layers to understand and wire together
- Unclear which cache to use for new features
- Risk of introducing inconsistencies with existing caches

---

## User Stories

### US-001: Reliable Entity Resolution

**As a** SDK Consumer
**I want** entity resolution to return accurate results regardless of cache state
**So that** my automation scripts do not fail with false NOT_FOUND errors

**Acceptance Criteria**:
- [ ] Phone/vertical lookups return GIDs when entities exist in Asana
- [ ] Cold cache misses trigger API fetch and populate cache before returning
- [ ] Cache freshness is validated before returning potentially stale results
- [ ] Error responses distinguish "not found in Asana" from "cache miss"

### US-002: Predictable DataFrame Performance

**As a** SDK Consumer
**I want** DataFrame builds to complete with consistent latency
**So that** I can reliably budget performance for batch operations

**Acceptance Criteria**:
- [ ] Warm cache builds execute in 1-2 API calls (section enumeration + freshness check)
- [ ] Cold cache builds execute in predictable time proportional to data size
- [ ] No 4-6x variance between warm and cold paths
- [ ] Build latency meets or exceeds current warm-path performance

### US-003: Correct Cascade Field Resolution

**As a** Developer
**I want** cascade field resolution to use the same cache as task lookups
**So that** parent values are consistent with the rest of the DataFrame

**Acceptance Criteria**:
- [ ] `cascade:` prefix in schemas resolves using unified cache
- [ ] Parent tasks fetched for cascade resolution are cached for reuse
- [ ] No per-instance parent cache that diverges from main cache
- [ ] Existing `cascade:` syntax unchanged (backward compatible)

### US-004: Configurable Freshness Control

**As an** API Service Operator
**I want** to configure the tradeoff between consistency and performance
**So that** I can tune behavior for different use cases

**Acceptance Criteria**:
- [ ] STRICT mode: Always validate freshness against API before returning cached data
- [ ] EVENTUAL mode: Return cached data within TTL, validate lazily
- [ ] IMMEDIATE mode: Return cached data without validation (fastest)
- [ ] Freshness mode configurable per-request and as default

### US-005: Fast Cold Start Recovery

**As an** API Service Operator
**I want** the service to recover from restarts without full re-synchronization
**So that** downtime and startup latency are minimized

**Acceptance Criteria**:
- [ ] S3-backed cold storage provides 7-day retention
- [ ] Service startup loads hierarchy index from S3
- [ ] First request after restart does not require full project scan
- [ ] Recovery time under 30 seconds for typical dataset

### US-006: Reduced API Overhead

**As an** API Service Operator
**I want** to reduce API calls per operation
**So that** I have headroom under Asana's rate limits for concurrent users

**Acceptance Criteria**:
- [ ] Warm cache path: 1-2 API calls (down from 4-6)
- [ ] Cold cache path: Single batch fetch per missing task group
- [ ] Parent chain resolution uses cached data, not per-parent API calls
- [ ] Batch freshness checks via Asana Batch API (10 GIDs per request)

### US-007: Unified Caching Mental Model

**As a** Developer
**I want** a single cache component to integrate against
**So that** I do not need to understand multiple cache layers

**Acceptance Criteria**:
- [ ] `UnifiedTaskStore` is the single entry point for task caching
- [ ] Legacy `TaskCacheCoordinator` becomes thin wrapper (deprecation path)
- [ ] API documentation describes unified cache architecture
- [ ] Migration guide provided for internal consumers

---

## Functional Requirements

### Must Have

#### FR-001: Single Source of Truth

The system shall maintain exactly one cache entry per task GID, keyed by `task_gid` (not composite keys like `task_gid:project_gid`).

#### FR-002: Unified Task Store Interface

The system shall provide a `UnifiedTaskStore` component with:
- `get_async(gid, freshness)` - Single task lookup
- `get_batch_async(gids, freshness)` - Batch lookup with single freshness check
- `put_async(task, ttl)` - Store task with hierarchy indexing
- `get_parent_chain_async(gid, max_depth)` - Ancestor chain for cascade resolution
- `invalidate(gid, cascade)` - Invalidate task and optionally descendants

#### FR-003: Hierarchy Index

The system shall track parent-child relationships to enable:
- Cascade invalidation (invalidate parent cascades to children)
- Efficient parent chain retrieval for cascade field resolution
- Root entity identification for hierarchy-aware freshness checks

#### FR-004: Freshness Modes

The system shall support three freshness modes:

| Mode | Behavior |
|------|----------|
| STRICT | Always fetch `modified_at` from API and compare before returning |
| EVENTUAL | Return cached if TTL valid; fetch `modified_at` if TTL expired |
| IMMEDIATE | Return cached without validation |

#### FR-005: Batch Freshness Checks

The system shall validate freshness for multiple GIDs in a single API operation using Asana Batch API (chunked by 10 per Asana limit).

#### FR-006: S3 Cold Storage

The system shall persist cache entries to S3 with:
- 7-day retention
- Compression for storage efficiency
- Promotion to Redis hot tier on access

#### FR-007: DataFrame as Materialized View

The system shall derive DataFrame rows from cached task data on-demand, rather than caching both raw tasks and extracted rows independently.

#### FR-008: Cascade Resolution Integration

The system shall provide parent chain resolution for `CascadingFieldResolver` through the unified store, eliminating the per-instance `_parent_cache`.

### Should Have

#### FR-009: Progressive TTL Extension

The system shall extend TTL for stable data (no changes detected) to reduce unnecessary revalidation.

#### FR-010: Request Coalescing

The system shall coalesce concurrent freshness check requests for the same GIDs to reduce API calls.

#### FR-011: Deprecation Warnings

The system shall emit deprecation warnings for direct usage of legacy cache components (`TaskCacheCoordinator`, `DataFrameCacheIntegration`).

### Could Have

#### FR-012: Hierarchy-Aware Bulk Freshness

The system may validate entire entity hierarchies with a single root `modified_at` check, based on the insight that child modifications update parent timestamps in Asana.

---

## Non-Functional Requirements

### NFR-001: Performance

| Metric | Target |
|--------|--------|
| Warm cache single task lookup | < 5ms |
| Warm cache batch lookup (100 tasks) | < 50ms |
| Warm cache DataFrame build (100 tasks) | < 200ms |
| Cold cache DataFrame build (100 tasks) | < 5000ms |
| Batch freshness check (100 GIDs) | < 500ms |

### NFR-002: Reliability

| Metric | Target |
|--------|--------|
| Cache hit rate (warm cache) | > 95% |
| False NOT_FOUND rate | < 0.1% |
| Service recovery time (cold start) | < 30 seconds |

### NFR-003: Scalability

| Metric | Target |
|--------|--------|
| Hierarchy index memory | < 100MB for 100K tasks |
| Concurrent request handling | 50 requests/second |
| Asana API budget | < 1500 requests/minute (within rate limit) |

### NFR-004: Observability

| Metric | Type |
|--------|------|
| `cache_hit_rate` | Gauge |
| `cache_miss_count` | Counter |
| `freshness_check_latency_ms` | Histogram |
| `api_calls_per_operation` | Histogram |
| `hierarchy_index_size` | Gauge |

---

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Task deleted from Asana | Return NOT_FOUND, invalidate cache entry |
| Task moved between projects | Update project membership in metadata |
| Parent task deleted | Handle orphaned hierarchy gracefully |
| Concurrent cache writes for same GID | Last-write-wins with version check |
| S3 unavailable at startup | Fall back to empty cache, log warning |
| Redis unavailable | Fall back to S3-only mode, degraded performance |
| Batch size exceeds Asana limit (10) | Chunk requests automatically |
| Circular parent references | Detect and break cycle at max_depth |
| Schema change requires re-extraction | Invalidate row cache, keep task cache |

---

## Success Criteria

- [ ] SC-001: Single cache entry per task GID verified by integration test
- [ ] SC-002: Entity resolver cold cache test passes (no false NOT_FOUND)
- [ ] SC-003: Cascade resolution test passes with parent values from unified cache
- [ ] SC-004: API call count measured at 1-2 for warm cache path
- [ ] SC-005: Freshness mode behavior verified by unit tests
- [ ] SC-006: Cold start recovery time measured under 30 seconds
- [ ] SC-007: All existing tests pass, latency benchmarks met

---

## Out of Scope

| Item | Rationale |
|------|-----------|
| Real-time sync via webhooks | Polling-based freshness sufficient for current use cases |
| Multi-instance cache coherence | Single-instance deployment; distributed cache deferred |
| Schema migration automation | Explicit cache invalidation on schema change is acceptable |
| Custom field definition caching | Focus on task data; custom fields are project-level metadata |
| GraphQL cache layer | REST-based cache sufficient for SDK consumers |

---

## Open Questions

*All questions resolved. Ready for Architecture handoff.*

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| TieredCacheProvider | Implemented | Redis + S3 backend (preserved) |
| RedisCacheProvider | Implemented | Hot tier (preserved) |
| S3CacheProvider | Implemented | Cold tier (preserved) |
| CacheEntry schema | Implemented | Extended with hierarchy metadata |
| CascadingFieldRegistry | Implemented | Preserved, wired to unified cache |
| Asana Batch API | Available | For batch `modified_at` checks |
| ProjectDataFrameBuilder | Implemented | Modified to use DataFrameViewPlugin |
| CascadingFieldResolver | Implemented | Modified to use CascadeViewPlugin |

---

## Appendix A: Goal to Requirement Mapping

| TDD Goal | User Outcome | Requirement |
|----------|--------------|-------------|
| G1: Single source of truth | Reliable data consistency | FR-001, SC-001 |
| G2: DataFrame as materialized view | Predictable DataFrame builds | FR-007, US-002 |
| G3: Unified parent chain cache | Correct cascade resolution | FR-008, SC-003 |
| G4: Batch freshness checks | Reduced API latency | FR-005, US-006 |
| G5: Configurable freshness | Control over tradeoff | FR-004, US-004 |
| G6: S3-backed cold storage | Fast recovery | FR-006, US-005 |
| G7: Preserve cascade tooling | Backward compatibility | FR-008, US-003 |
| G8: API call reduction | Cost savings, rate limit headroom | SC-004, US-006 |

---

## Appendix B: API Call Comparison

### Before (Current Architecture)

| Step | Calls | Description |
|------|-------|-------------|
| Section enumeration | 1 | List sections for project |
| Task batch fetch | 1+ | Paginated task fetch |
| Parent fetch (cascade) | 1-3 per parent | Individual parent lookups |
| Freshness check | N | Per-task staleness check |
| **Total (warm)** | **4-6** | |

### After (Unified Architecture)

| Step | Calls | Description |
|------|-------|-------------|
| Section enumeration | 1 | List sections (cached) |
| Batch freshness check | 1 | Single batch `modified_at` via Batch API |
| Fetch stale/missing | 0-N | Only for stale entries |
| **Total (warm)** | **1-2** | |

---

## Appendix C: Constraint Summary

| Constraint | Value | Source |
|------------|-------|--------|
| Deployment model | Single instance | Current infrastructure |
| Asana rate limit | 1500 req/min | Asana API documentation |
| S3 cold storage tier | Required | Existing TieredCacheProvider |
| Cascade syntax | `cascade:` prefix | Existing schema syntax |
| Batch API chunk size | 10 GIDs | Asana Batch API limit |

---

**End of PRD**
