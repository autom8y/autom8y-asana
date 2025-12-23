# Orchestrator Initialization: Cache Utilization Initiative

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`autom8-asana`** - SDK patterns, SaveSession, Business entities, cache infrastructure
  - Activates when: Working with cache providers, entity hierarchy, persistence layer

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

- **`prompting`** - Agent invocation patterns, workflow examples
  - Activates when: Invoking agents, structuring prompts

**How Skills Work**: Skills load automatically based on your current task. When you need template formats, the `documentation` skill activates. When you need SDK patterns, the `autom8-asana` skill activates.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, performance verification |

## The Mission: Fully Utilize Existing Cache Infrastructure Across All SDK Clients

The autom8_asana SDK has comprehensive caching infrastructure (`TieredCacheProvider`, `RedisCacheProvider`, `CacheMetrics`, entity-type TTLs, batch operations, `warm()` methods) that is **underutilized**. Currently only `TasksClient` uses caching. This initiative enables caching for Projects, Sections, Users, Custom Fields, and detection results while exposing cache observability.

### Why This Initiative?

- **Immediate Performance Gains**: Projects and Sections are fetched repeatedly without caching; caching them eliminates redundant API calls
- **Infrastructure ROI**: Redis/TieredCacheProvider exists but defaults to in-memory; production deployments should leverage tiered cache benefits
- **Observability Gap**: `CacheMetrics` tracks hits/misses/writes/errors but metrics are not exposed to observability layer
- **Batch Efficiency**: `set_batch()` exists but bulk fetch paths do not populate cache; single-task fetches lose batch benefits
- **Warming Capability**: `warm()` infrastructure exists across all providers but returns "skipped"; no implementation for pre-population

### Current State

**What Works (Cache Infrastructure Exists)**:
- `TieredCacheProvider`: Redis (hot) + S3 (cold) tiered storage implemented
- `RedisCacheProvider`: Full Redis backend with batch operations
- `InMemoryCacheProvider`: Default provider with complete API surface
- `CacheEntry` with versioning via `modified_at` timestamp
- `EntryType` enum: TASK, SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS, DATAFRAME
- `CacheSettings` with entity-type TTL configuration (tasks: 300s, subtasks: 600s, stories: 3600s, etc.)
- `CacheMetrics` dataclass tracking total_hits, total_misses, total_writes, total_errors, hit_rate
- `get_batch()` / `set_batch()` batch operations on all providers
- `warm()` method signature on all providers
- SaveSession post-commit cache invalidation (wired for TASK/SUBTASKS)

**What Does NOT Work (The Gaps)**:

1. **Only TasksClient Uses Cache**: `client.tasks.get_async()` checks cache; Projects, Sections, Users, Custom Fields do NOT
2. **Redis/Tiered Not Default**: `create_cache_provider()` defaults to `InMemoryCacheProvider`; tiered cache requires explicit REDIS_HOST env var
3. **Bulk Fetch Ignores Cache**: `list_async()` methods do not populate individual entity caches via `set_batch()`
4. **Metrics Not Exposed**: `CacheMetrics` exists on providers but not wired to SDK observability/logging
5. **warm() Returns "Skipped"**: All `warm()` implementations return `WarmResult(skipped=len(gids))` with no actual warming
6. **Entity TTLs Not Auto-Applied**: `CacheSettings` has per-type TTLs but clients don't use them (hardcoded 300s)
7. **Detection Results Not Cached**: `detect_entity_type()` makes repeated API calls for same task; results not cached
8. **Hydration Not Cached**: `_hydrate_entity()` paths fetch relations without cache checks

```
Current Flow (TasksClient only):
  client.tasks.get_async(gid)
    --> Check cache.get_versioned(gid, EntryType.TASK)
    --> On miss: fetch from API, cache.set_versioned()
    --> Return Task

Gap: ProjectsClient, SectionsClient, UsersClient, CustomFieldsClient
  client.projects.get_async(gid)
    --> Direct API call (no cache check)
    --> Return Project

Desired Flow (All Clients):
  client.{resource}.get_async(gid)
    --> Check cache with entity-type TTL
    --> On miss: fetch from API, cache with correct TTL
    --> Return typed model
```

### Cache Infrastructure Profile

| Attribute | Value |
|-----------|-------|
| Cache Providers | InMemoryCacheProvider (default), RedisCacheProvider, TieredCacheProvider, S3CacheProvider |
| Entry Types | TASK, SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS, DATAFRAME |
| Default TTL | 300 seconds (5 minutes) |
| Configured TTLs | tasks: 300s, subtasks: 600s, stories: 3600s, attachments: 3600s |
| Batch Operations | `get_batch()`, `set_batch()` on all providers |
| Warming | `warm()` method exists but not implemented |
| Metrics | `CacheMetrics` dataclass (hits, misses, writes, errors, hit_rate) |
| Redis Config | `RedisConfig` with host, port, password, ssl, db, timeouts, retry settings |
| S3 Config | `S3CacheConfig` with bucket, prefix, region |

### Target Architecture

```
User: client.projects.get_async(gid)
           |
           v
+------------------------------------------+
|   CLIENT LAYER (Projects, Sections,      |  <-- NEW: Cache integration
|   Users, CustomFields)                   |
|   1. Check cache with entity-type TTL    |
|   2. On miss: fetch from API             |
|   3. Populate cache via set_versioned()  |
+------------------------------------------+
           |
           v
+------------------------------------------+
|   BULK FETCH PATH                        |  <-- NEW: Batch cache population
|   list_async() results                   |
|   --> set_batch() for all entities       |
|   --> Individual cache entries           |
+------------------------------------------+
           |
           v
+------------------------------------------+
|   CACHE PROVIDER (TIERED)                |  <-- ENHANCE: Enable by default
|   Redis (hot) + S3 (cold)                |
|   Metrics exposed to observability       |
+------------------------------------------+
           |
           v
+------------------------------------------+
|   WARM() IMPLEMENTATION                  |  <-- NEW: Actual warming logic
|   Pre-populate high-traffic entities     |
|   Background refresh for stale entries   |
+------------------------------------------+
```

### Key Constraints

- **Backward Compatibility**: No breaking changes to existing client APIs
- **Zero Configuration for Basic Cache**: In-memory cache must work without Redis
- **Opt-In for Redis/Tiered**: Redis requires explicit configuration (env var or config)
- **Graceful Degradation**: Cache failures must not fail API operations
- **Async-First**: All cache operations must be async-compatible
- **Respect Entity TTLs**: Different entity types have different staleness tolerances

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Add cache integration to ProjectsClient.get_async() | P0 (Must) |
| Add cache integration to SectionsClient.get_async() | P0 (Must) |
| Wire bulk fetch paths to set_batch() for cache population | P0 (Must) |
| Enable tiered cache (Redis+S3) as default when REDIS_HOST set | P0 (Must) |
| Expose CacheMetrics to SDK observability layer | P1 (Should) |
| Add cache integration to UsersClient.get_async() | P1 (Should) |
| Add cache integration to CustomFieldsClient.get_async() | P1 (Should) |
| Implement warm() for cache pre-population | P2 (Could) |
| Cache detection results (detect_entity_type) | P1 (Should) |
| Cache hydration path results | P2 (Could) |
| Apply entity-type TTLs from CacheSettings automatically | P1 (Should) |

### Success Criteria

1. **Project/Section Caching**: `client.projects.get_async()` and `client.sections.get_async()` use cache
2. **Batch Population**: `list_async()` calls populate individual entity caches via `set_batch()`
3. **Tiered Cache Default**: When `REDIS_HOST` is set, tiered cache is automatically used
4. **Metrics Observability**: Cache hit/miss rates visible in SDK logs or callbacks
5. **Detection Caching**: Repeated `detect_entity_type()` calls for same GID use cache
6. **Entity TTLs Applied**: Different entity types use configured TTLs from `CacheSettings`
7. **Warm Implementation**: `warm()` actually populates cache (not just "skipped")
8. **No Regressions**: All existing tests pass; no performance degradation

### Performance Targets

| Scenario | Current | Target |
|----------|---------|--------|
| Project fetch (cached) | ~200ms (API) | <5ms |
| Section fetch (cached) | ~200ms (API) | <5ms |
| Detection (cached) | ~200ms (API) | <5ms |
| Bulk list cache population | N/A | <10ms per 100 entities |
| Cache warm (1000 entities) | "skipped" | <100ms |
| Cache hit rate (steady state) | Unknown | >90% |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Cache utilization gap analysis - current client patterns, integration points, TTL configuration |
| **2: Requirements** | Requirements Analyst | PRD-CACHE-UTILIZATION with acceptance criteria per client and feature |
| **3: Architecture** | Architect | TDD-CACHE-UTILIZATION + ADRs for client caching pattern, tiered default, metrics exposure |
| **4: Implementation P1** | Principal Engineer | ProjectsClient and SectionsClient cache integration |
| **5: Implementation P2** | Principal Engineer | Bulk fetch batch population, tiered cache default |
| **6: Implementation P3** | Principal Engineer | Metrics exposure, warm() implementation, detection caching |
| **7: Validation** | QA/Adversary | Cache hit rate verification, performance benchmarks, failure mode testing |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Client Layer Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/clients/tasks.py` | How is cache integration done? Pattern to replicate? |
| `src/autom8_asana/clients/projects.py` | Where to inject cache check? What versioning field exists? |
| `src/autom8_asana/clients/sections.py` | Does Section have modified_at? How to version? |
| `src/autom8_asana/clients/users.py` | Is User cacheable? What's the staleness tolerance? |
| `src/autom8_asana/clients/custom_fields.py` | Is CustomField cacheable? Workspace-scoped? |
| `src/autom8_asana/clients/base.py` | Can cache injection be done in base class? |

### Cache Infrastructure Analysis

| Component | Questions |
|-----------|-----------|
| `CacheSettings` entity_ttls | What TTLs are configured? Are they appropriate? |
| `CacheFactory.create_cache_provider()` | How is provider selection done? How to make tiered default? |
| `TieredCacheProvider` | What's the promotion/demotion logic? Is it production-ready? |
| `CacheMetrics` | What metrics exist? How to expose to observability? |
| `warm()` implementations | Why do they return "skipped"? What's missing? |
| `set_batch()` | How to efficiently populate from list results? |

### Detection and Hydration Analysis

| Area | Questions |
|------|-----------|
| `detect_entity_type()` | Where is it called? How often? Cache key structure? |
| Entity hydration | Which paths make repeated fetches? Cache opportunity? |
| Business entity hierarchy | Can hierarchy traversal benefit from caching? |
| Detection result structure | What fields need caching? TTL for detection? |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Client Caching Questions

1. **Versioning field for Sections**: Sections don't have `modified_at`; what version field to use?
2. **User caching scope**: Users rarely change; should TTL be longer (1 hour+)?
3. **CustomField caching**: Are custom fields workspace-scoped or global? Cache key structure?
4. **Cache key prefix**: Should entity type be part of key? (e.g., `project:{gid}` vs `{gid}`)

### Tiered Cache Questions

5. **Default provider logic**: When REDIS_HOST is set, auto-enable tiered? Or require explicit config?
6. **S3 cold tier**: Is S3 tier needed for this initiative or can it be deferred?
7. **Memory cache size**: What's the max entries for in-memory tier? LRU eviction configured?
8. **Redis connection pooling**: Is connection pool properly configured? Max connections?

### Metrics Questions

9. **Metrics exposure method**: Logging? Callback? Prometheus-style endpoint?
10. **Per-entity metrics**: Track hit/miss per entity type or aggregate only?
11. **Metrics interval**: Real-time or periodic snapshot?
12. **Error categorization**: What errors to track? Network? Serialization? TTL?

### Bulk Operations Questions

13. **List pagination caching**: Should paginated results populate individual caches?
14. **Batch size limits**: What's the optimal batch size for `set_batch()`?
15. **Async batch**: Is `set_batch()` async? Does it block?
16. **Partial failure**: If batch set fails for some entries, how to handle?

### Warming Questions

17. **Warm trigger**: Manual API? Startup hook? Background job?
18. **Warm scope**: Which entities to warm? Project-level? Workspace-level?
19. **Warm concurrency**: How many parallel fetches during warm?
20. **Warm vs. fetch**: Should warm() fetch from API or only check cache presence?

## Exploration Context Summary

This initiative builds on the successful Watermark Cache Performance Initiative (Sessions 1-7) which achieved:
- Parallel section fetch reducing DataFrame latency from 52s to <10s
- Batch cache operations wired into DataFrame builder
- SaveSession post-commit invalidation for tasks

### Key Insight from Prior Work

> **"The cache infrastructure is mature. The utilization is incomplete."**

The prior initiative confirmed that the caching architecture is correct:
- Per-task granularity with project context
- Single logical cache level (no multi-level hierarchy)
- Tiered storage (Redis hot + S3 cold)
- Batch operations for efficiency

What's missing is **breadth**: extending this pattern to all resource types.

### Preserved Decisions from Prior Work

- Per-entity cache granularity (not aggregate caching)
- Eventual consistency via TTL for external changes
- Immediate consistency for self-writes via SaveSession invalidation
- Batch operations for efficiency

### What NOT to Build (Explicitly Rejected in Prior Work)

| Feature | Reason |
|---------|--------|
| Section-level aggregate cache | Invalidation cost exceeds benefit; no `modified_at` on sections |
| Project-level aggregate cache | Cache thrashing under write patterns |
| Multi-level cache hierarchy | Over-engineering; "ghost reference problem" |
| Search API for staleness | Premium-only; cannot detect removals |

## Your First Task

Confirm understanding by:

1. Summarizing the Cache Utilization goal in 2-3 sentences (focus on **breadth of utilization**, not infrastructure changes)
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step before requirements
4. Confirming which clients/systems must be analyzed before PRD-CACHE-UTILIZATION
5. Listing which open questions you need answered before Session 2
6. Acknowledging the "what NOT to build" list from prior exploration

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Cache Utilization Discovery

Work with the @requirements-analyst agent to analyze client caching patterns and cache infrastructure utilization gaps.

**Goals:**
1. Map current TasksClient cache integration pattern
2. Identify cache integration points in ProjectsClient, SectionsClient
3. Analyze UserClient and CustomFieldsClient for caching feasibility
4. Document CacheSettings entity TTLs and applicability
5. Understand CacheMetrics structure and exposure options
6. Analyze warm() method signatures and implementation gaps
7. Identify bulk fetch paths suitable for batch cache population

**Files to Analyze:**
- `src/autom8_asana/clients/tasks.py` - Current cache pattern
- `src/autom8_asana/clients/projects.py` - Cache integration point
- `src/autom8_asana/clients/sections.py` - Versioning challenge
- `src/autom8_asana/clients/users.py` - Long TTL candidate
- `src/autom8_asana/clients/custom_fields.py` - Workspace-scoped caching
- `src/autom8_asana/cache/factory.py` - Provider selection logic
- `src/autom8_asana/cache/settings.py` - TTL configuration
- `src/autom8_asana/cache/metrics.py` - Metrics structure

**Cache Components to Audit:**
- TieredCacheProvider configuration and defaults
- RedisCacheProvider connection handling
- InMemoryCacheProvider LRU behavior
- set_batch() efficiency and error handling
- warm() method implementations across providers

**Deliverable:**
A discovery document with:
- Current vs. desired cache utilization matrix
- Client-by-client integration feasibility
- Entity-type TTL recommendations
- Metrics exposure approach options
- warm() implementation requirements
- Risk assessment for cache extension
- Resolved vs. unresolved open questions

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Cache Utilization Requirements Definition

Work with the @requirements-analyst agent to create PRD-CACHE-UTILIZATION.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define client cache integration requirements (FR-CLIENT-*)
2. Define batch population requirements (FR-BATCH-*)
3. Define tiered cache default requirements (FR-TIERED-*)
4. Define metrics exposure requirements (FR-METRICS-*)
5. Define warm implementation requirements (FR-WARM-*)
6. Define detection caching requirements (FR-DETECT-*)
7. Define acceptance criteria for each requirement

**Key Questions to Address:**
- What is the exact cache integration pattern per client?
- How does batch population work for list operations?
- When should tiered cache auto-enable?
- How are metrics exposed to consumers?

**PRD Organization:**
- FR-CLIENT-*: Per-client cache integration
- FR-BATCH-*: Bulk fetch batch population
- FR-TIERED-*: Tiered cache default behavior
- FR-METRICS-*: Cache metrics observability
- FR-WARM-*: Cache warming implementation
- FR-DETECT-*: Detection result caching
- NFR-*: Performance targets, backward compatibility

**Explicit OUT of Scope (from prior exploration):**
- Section-level aggregate caching
- Project-level aggregate caching
- Multi-level cache hierarchy
- Search API integration

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Cache Utilization Architecture Design

Work with the @architect agent to create TDD-CACHE-UTILIZATION and foundational ADRs.

**Prerequisites:**
- PRD-CACHE-UTILIZATION approved

**Goals:**
1. Design client cache integration pattern (replicable across clients)
2. Design batch population flow for list operations
3. Design tiered cache auto-enablement logic
4. Design metrics exposure via observability layer
5. Design warm() implementation strategy
6. Design detection result cache structure
7. Document module structure for changes

**Required ADRs:**
- ADR-NNNN: Client Cache Integration Pattern
- ADR-NNNN: Batch Cache Population on Bulk Fetch
- ADR-NNNN: Tiered Cache Default Behavior
- ADR-NNNN: Cache Metrics Observability Strategy
- ADR-NNNN: Cache Warming Implementation

**Architecture Constraints (from prior exploration):**
- Per-entity cache granularity (not aggregate)
- Eventual consistency via TTL
- Immediate consistency for self-writes via invalidation
- Single logical cache level

**Component Changes:**

```
src/autom8_asana/
+-- clients/
|   +-- base.py             # UPDATE: Add cache integration mixin
|   +-- projects.py         # UPDATE: Add cache to get_async()
|   +-- sections.py         # UPDATE: Add cache to get_async()
|   +-- users.py            # UPDATE: Add cache to get_async()
|   +-- custom_fields.py    # UPDATE: Add cache to get_async()
+-- cache/
|   +-- factory.py          # UPDATE: Tiered default when Redis available
|   +-- metrics.py          # UPDATE: Expose to observability
|   +-- settings.py         # VERIFY: TTL configuration
+-- observability/
|   +-- __init__.py         # UPDATE: Cache metrics integration
+-- detection/
|   +-- __init__.py         # UPDATE: Detection result caching
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Core Client Caching

Work with the @principal-engineer agent to implement cache integration for core clients.

**Prerequisites:**
- PRD-CACHE-UTILIZATION approved
- TDD-CACHE-UTILIZATION approved
- ADRs documented

**Phase 1 Scope:**
1. Add cache integration to ProjectsClient.get_async()
2. Add cache integration to SectionsClient.get_async()
3. Implement cache key generation per entity type
4. Apply entity-type TTLs from CacheSettings
5. Add unit tests for client cache integration
6. Verify SaveSession invalidation compatibility

**Hard Constraints:**
- No breaking changes to client public APIs
- Cache miss must fall through to API call transparently
- Cache failures must not fail operations (graceful degradation)
- All existing client tests must pass

**Explicitly OUT of Phase 1:**
- Bulk fetch batch population (Phase 2)
- Tiered cache default enablement (Phase 2)
- Metrics exposure (Phase 3)
- warm() implementation (Phase 3)

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Batch Population & Tiered Default

Work with the @principal-engineer agent to implement batch cache population and tiered defaults.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Wire list_async() results to set_batch() for cache population
2. Implement tiered cache auto-enablement when REDIS_HOST is set
3. Add cache integration to UsersClient.get_async()
4. Add cache integration to CustomFieldsClient.get_async()
5. Verify batch population works with pagination
6. Add integration tests for batch population flow

**Integration Points:**
- list_async() results -> set_batch() on cache provider
- Environment variable detection -> tiered cache selection
- Per-entity TTL application in batch population

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Metrics, Warming, Detection

Work with the @principal-engineer agent to complete metrics exposure, warming, and detection caching.

**Prerequisites:**
- Phase 2 complete and tested

**Phase 3 Scope:**
1. Expose CacheMetrics to SDK observability layer
2. Implement warm() method for actual cache pre-population
3. Add detection result caching in detect_entity_type()
4. Add configuration options for metrics verbosity
5. Document cache utilization patterns for SDK consumers
6. Integration tests for metrics and warming

**Metrics Structure:**

```python
class CacheObservability:
    """Expose cache metrics to SDK observability."""

    def get_metrics_snapshot(self) -> CacheMetrics:
        """Return current cache metrics."""
        ...

    def register_callback(self, callback: Callable[[CacheMetrics], None]) -> None:
        """Register callback for periodic metrics reporting."""
        ...

    def log_metrics(self, logger: Logger) -> None:
        """Log current metrics to provided logger."""
        ...
```

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Cache Utilization Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation phases complete

**Goals:**

**Part 1: Cache Hit Rate Validation**
- Project fetch hit rate after warm: >90%
- Section fetch hit rate after warm: >90%
- User fetch hit rate (long TTL): >95%
- Detection hit rate for repeated calls: 100%

**Part 2: Performance Validation**
- Cached project fetch: <5ms (from ~200ms)
- Cached section fetch: <5ms (from ~200ms)
- Batch population for 100 entities: <10ms
- Cache warm for 1000 entities: <100ms

**Part 3: Functional Validation**
- All client cache integrations work correctly
- Batch population occurs on list_async() calls
- Tiered cache auto-enables when REDIS_HOST set
- Metrics exposed and accessible
- warm() actually populates cache

**Part 4: Failure Mode Testing**
- Redis unavailable -> Falls back to in-memory
- Cache provider failure -> Operations succeed (no cache)
- Batch population failure -> Individual operations succeed
- Metrics collection failure -> No impact on operations

**Part 5: Backward Compatibility**
- Existing consumer code works without changes
- All existing tests pass
- No new required configuration
- In-memory cache remains default when Redis not configured

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Client Layer:**

- [ ] `src/autom8_asana/clients/tasks.py` - Current cache integration pattern
- [ ] `src/autom8_asana/clients/projects.py` - Integration point identification
- [ ] `src/autom8_asana/clients/sections.py` - Versioning field analysis
- [ ] `src/autom8_asana/clients/users.py` - Long TTL candidate
- [ ] `src/autom8_asana/clients/custom_fields.py` - Workspace-scoped caching
- [ ] `src/autom8_asana/clients/base.py` - Base class patterns

**Cache Infrastructure:**

- [ ] `src/autom8_asana/cache/factory.py` - Provider selection logic
- [ ] `src/autom8_asana/cache/settings.py` - Entity TTL configuration
- [ ] `src/autom8_asana/cache/metrics.py` - Metrics structure
- [ ] `src/autom8_asana/cache/tiered.py` - Tiered provider implementation
- [ ] `src/autom8_asana/cache/backends/redis.py` - Redis implementation
- [ ] `src/autom8_asana/cache/backends/memory.py` - In-memory implementation
- [ ] `src/autom8_asana/cache/entry.py` - Entry structure and types

**Detection & Hydration:**

- [ ] `src/autom8_asana/detection/` - Detection implementation
- [ ] Entity hydration paths - Which paths fetch relations?

**Prior Work Reference:**

- [ ] `docs/requirements/PROMPT-0-WATERMARK-CACHE.md` - Prior initiative context
- [ ] `docs/analysis/multi-level-cache-hierarchy-analysis.md` - Architecture decisions

---

# Appendix: Cache Infrastructure Summary

## Entry Types (from cache/entry.py)

| EntryType | Description | Recommended TTL |
|-----------|-------------|-----------------|
| TASK | Individual task data | 300s (5 min) |
| SUBTASKS | Task's subtask list | 600s (10 min) |
| DEPENDENCIES | Task dependencies | 600s (10 min) |
| DEPENDENTS | Task dependents | 600s (10 min) |
| STORIES | Task comments/history | 3600s (1 hour) |
| ATTACHMENTS | Task attachments | 3600s (1 hour) |
| DATAFRAME | Extracted DataFrame row | 300s (5 min) |

**NEW Types Needed:**
- PROJECT: Project metadata
- SECTION: Section metadata
- USER: User data (long TTL - rarely changes)
- CUSTOM_FIELD: Custom field definition (workspace-scoped)
- DETECTION: Detection result

## Provider Capabilities

| Provider | get | set | get_batch | set_batch | warm | metrics |
|----------|-----|-----|-----------|-----------|------|---------|
| InMemoryCacheProvider | Yes | Yes | Yes | Yes | Stub | Yes |
| RedisCacheProvider | Yes | Yes | Yes | Yes | Stub | Yes |
| TieredCacheProvider | Yes | Yes | Yes | Yes | Delegates | Yes |
| S3CacheProvider | Yes | Yes | Yes | Yes | Stub | Yes |

## Current CacheSettings TTLs (from settings.py)

```python
entity_ttls: dict[EntryType, int] = {
    EntryType.TASK: 300,      # 5 minutes
    EntryType.SUBTASKS: 600,  # 10 minutes
    EntryType.STORIES: 3600,  # 1 hour
    # ... others
}
```

## Metrics Available (from CacheMetrics)

- `total_hits`: Number of cache hits
- `total_misses`: Number of cache misses
- `total_writes`: Number of cache writes
- `total_errors`: Number of cache errors
- `hit_rate`: Computed hit rate (hits / (hits + misses))
